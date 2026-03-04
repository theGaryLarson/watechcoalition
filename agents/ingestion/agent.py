"""
Ingestion Agent — Week 3 Implementation.

Fetches job postings from JSearch API and/or Crawl4AI (with fixture fallback),
deduplicates, stages in ``dbo.raw_ingested_jobs``, and emits an ``IngestBatch``
event with the list of staged record IDs.

Agent ID (canonical): ingestion-agent
Emits:    IngestBatch | SourceFailure
Consumes: trigger event with {source, limit, query, location}

CLI usage (from repo root):
    python -m agents.ingestion.agent --source crawl4ai --limit 10 --migrate
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import structlog

from agents.common.base_agent import BaseAgent
from agents.common.data_store.database import check_db_connection, session_scope
from agents.common.data_store.models import JobIngestionRun, RawIngestedJob
from agents.common.event_envelope import EventEnvelope
from agents.ingestion.deduplicator import deduplicate_batch
from agents.ingestion.sources.jsearch_adapter import JSearchAdapter
from agents.ingestion.sources.scraper_adapter import ScraperAdapter

log = structlog.get_logger()

_DEAD_LETTER_DIR = Path(__file__).parent.parent / "data" / "dead_letter"
_FALLBACK_SCRAPE = Path(__file__).parent.parent / "data" / "fixtures" / "fallback_scrape_sample.json"


class IngestionAgent(BaseAgent):
    """
    Fetches, deduplicates, and stages job postings from external sources.

    Batch-oriented: receives a trigger event with source/limit/query/location,
    fetches from adapters, deduplicates, writes to DB, emits IngestBatch.
    """

    def __init__(self) -> None:
        super().__init__(agent_id="ingestion-agent")
        self._jsearch = JSearchAdapter()
        self._scraper = ScraperAdapter()

    def health_check(self) -> dict:
        """Check DB connectivity and fixture file availability."""
        db_ok = check_db_connection()
        fixture_ok = _FALLBACK_SCRAPE.exists()

        if db_ok and fixture_ok:
            status = "ok"
        elif db_ok or fixture_ok:
            status = "degraded"
        else:
            status = "down"

        return {
            "status": status,
            "agent": self.agent_id,
            "last_run": None,
            "metrics": {"db_connected": db_ok, "fixture_available": fixture_ok},
        }

    def process(self, event: EventEnvelope) -> EventEnvelope:
        """Run a full ingestion batch.

        Expected payload keys:
            source: "jsearch" | "crawl4ai" | "all"
            limit:  int (default 50)
            query:  str (default "software engineer")
            location: str (default "Washington state")
        """
        payload = event.payload
        source = payload.get("source", "all")
        limit = payload.get("limit", 50)
        query = payload.get("query", "software engineer")
        location = payload.get("location", "Washington state")

        run_id = str(uuid.uuid4())

        log.info(
            "ingestion_start",
            run_id=run_id,
            source=source,
            limit=limit,
            correlation_id=event.correlation_id,
        )

        # Create run tracking record
        with session_scope() as session:
            run_record = JobIngestionRun(
                run_id=run_id,
                source=source,
                status="running",
                config_snapshot={"source": source, "limit": limit, "query": query, "location": location},
            )
            session.add(run_record)

        # Fetch from source adapters
        try:
            raw_records = asyncio.run(
                self._fetch_from_sources(source=source, limit=limit, query=query, location=location)
            )
        except Exception as exc:
            log.error("ingestion_fetch_failed", run_id=run_id, error=str(exc))
            self._update_run(run_id, status="failed", error=str(exc))
            return EventEnvelope(
                correlation_id=event.correlation_id,
                agent_id=self.agent_id,
                payload={
                    "event_type": "SourceFailure",
                    "run_id": run_id,
                    "source": source,
                    "error": str(exc),
                },
            )

        if not raw_records:
            log.warning("ingestion_no_records", run_id=run_id, source=source)
            self._update_run(run_id, status="completed", total_fetched=0)
            return EventEnvelope(
                correlation_id=event.correlation_id,
                agent_id=self.agent_id,
                payload={
                    "event_type": "IngestBatch",
                    "batch_id": run_id,
                    "source": source,
                    "total_fetched": 0,
                    "duplicates_skipped": 0,
                    "records_staged": 0,
                    "dead_letter_count": 0,
                    "staged_record_ids": [],
                },
            )

        # Deduplicate
        with session_scope() as session:
            dedup_result = deduplicate_batch(raw_records, session)

        # Stage new records
        staged_ids: list[int] = []
        dead_letter_count = 0

        with session_scope() as session:
            for record in dedup_result.new_records:
                try:
                    row = RawIngestedJob(
                        ingestion_run_id=run_id,
                        source=record["source"],
                        external_id=record["external_id"],
                        raw_payload_hash=record["raw_payload_hash"],
                        title=record.get("title", ""),
                        company=record.get("company", ""),
                        location=record.get("location"),
                        url=record.get("url"),
                        date_posted=record.get("date_posted"),
                        raw_text=record.get("raw_text"),
                        raw_payload=record.get("raw_payload"),
                        status="staged",
                    )
                    session.add(row)
                    session.flush()
                    staged_ids.append(row.id)
                except Exception as exc:
                    log.warning(
                        "ingestion_stage_failed",
                        external_id=record.get("external_id"),
                        error=str(exc),
                    )
                    dead_letter_count += 1
                    self._quarantine(run_id, record, str(exc))

        # Update run tracking
        self._update_run(
            run_id,
            status="completed",
            total_fetched=len(raw_records),
            duplicates_skipped=dedup_result.duplicates_skipped,
            records_staged=len(staged_ids),
            dead_letter_count=dead_letter_count,
        )

        log.info(
            "ingestion_complete",
            run_id=run_id,
            total_fetched=len(raw_records),
            duplicates_skipped=dedup_result.duplicates_skipped,
            records_staged=len(staged_ids),
            dead_letter_count=dead_letter_count,
        )

        return EventEnvelope(
            correlation_id=event.correlation_id,
            agent_id=self.agent_id,
            payload={
                "event_type": "IngestBatch",
                "batch_id": run_id,
                "source": source,
                "total_fetched": len(raw_records),
                "duplicates_skipped": dedup_result.duplicates_skipped,
                "records_staged": len(staged_ids),
                "dead_letter_count": dead_letter_count,
                "staged_record_ids": staged_ids,
            },
        )

    async def _fetch_from_sources(
        self, *, source: str, limit: int, query: str, location: str
    ) -> list[dict]:
        """Fetch records from the requested source(s)."""
        records: list[dict] = []

        if source in ("jsearch", "all"):
            records.extend(await self._jsearch.fetch(limit=limit, query=query, location=location))

        if source in ("crawl4ai", "all"):
            remaining = max(0, limit - len(records))
            if remaining > 0 or source == "crawl4ai":
                fetch_limit = limit if source == "crawl4ai" else remaining
                records.extend(await self._scraper.fetch(limit=fetch_limit, query=query, location=location))

        return records

    def _update_run(self, run_id: str, *, status: str, **kwargs: object) -> None:
        """Update the run tracking record."""
        try:
            with session_scope() as session:
                run = session.query(JobIngestionRun).filter_by(run_id=run_id).first()
                if run:
                    run.status = status
                    run.completed_at = datetime.now(UTC)
                    for key, value in kwargs.items():
                        if hasattr(run, key):
                            setattr(run, key, value)
        except Exception as exc:
            log.warning("ingestion_run_update_failed", run_id=run_id, error=str(exc))

    def _quarantine(self, run_id: str, record: dict, error: str) -> None:
        """Write a failed record to the dead letter directory."""
        _DEAD_LETTER_DIR.mkdir(parents=True, exist_ok=True)
        external_id = record.get("external_id", "unknown")
        path = _DEAD_LETTER_DIR / f"{run_id}_{external_id}.json"
        try:
            path.write_text(
                json.dumps({"record": record, "error": error, "run_id": run_id}, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as exc:
            log.warning("dead_letter_write_failed", path=str(path), error=str(exc))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _cli() -> None:
    """CLI for running the Ingestion Agent standalone."""
    import argparse

    parser = argparse.ArgumentParser(description="Run the Ingestion Agent")
    parser.add_argument("--source", choices=["jsearch", "crawl4ai", "all"], default="all")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--query", default="software engineer")
    parser.add_argument("--location", default="Washington state")
    parser.add_argument("--migrate", action="store_true", help="Run DB migrations before ingestion")
    args = parser.parse_args()

    if args.migrate:
        from agents.common.data_store.database import get_engine
        from agents.common.data_store.migrations import run_migrations
        run_migrations(get_engine())

    agent = IngestionAgent()

    health = agent.health_check()
    log.info("health_check", **health)

    trigger = EventEnvelope(
        correlation_id=str(uuid.uuid4()),
        agent_id="cli",
        payload={
            "source": args.source,
            "limit": args.limit,
            "query": args.query,
            "location": args.location,
        },
    )

    result = agent.process(trigger)
    log.info("ingestion_result", **result.payload)


if __name__ == "__main__":
    _cli()
