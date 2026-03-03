from __future__ import annotations

"""
EnrichmentAgent stub for the Job Intelligence Engine walking skeleton.

This agent is responsible for classifying roles, seniority, quality, and spam,
and for resolving company and sector metadata. In the Week 2 walking skeleton,
this implementation loads a static fixture payload representing an enriched
record.
"""

import json
from pathlib import Path

import structlog

from agents.common.base_agent import BaseAgent
from agents.common.event_envelope import EventEnvelope


log = structlog.get_logger()


class EnrichmentAgent(BaseAgent):
    """Stub implementation of the Enrichment Agent for the walking skeleton."""

    def __init__(self) -> None:
        """Initialize the enrichment agent with its canonical identifier."""
        super().__init__(agent_id="enrichment")
        self._fixtures_dir = (
            Path(__file__).resolve().parent.parent / "data" / "fixtures"
        )
        self._fixture_path = self._fixtures_dir / "fixture_enriched.json"

    def _fixture_exists(self) -> bool:
        """Return True if the enrichment fixture file is present."""
        return self._fixtures_dir.exists() and self._fixture_path.exists()

    def health_check(self) -> dict:
        """
        Validate that the enrichment fixture exists and return health.

        The enrichment agent relies on a JSON fixture that represents a
        canonical `RecordEnriched` payload. This method ensures that the file
        is present on disk so the walking skeleton can exercise a realistic
        code path when loading it during processing.
        """
        fixtures_ok = self._fixture_exists()

        if fixtures_ok:
            status = "ok"
            log.info(
                "enrichment_health_ok",
                agent=self.agent_id,
                fixture=str(self._fixture_path),
            )
        else:
            status = "down"
            log.error(
                "enrichment_health_failed",
                agent=self.agent_id,
                fixtures_dir=str(self._fixtures_dir),
                fixture=str(self._fixture_path),
                fixtures_dir_exists=self._fixtures_dir.exists(),
                fixture_exists=self._fixture_path.exists(),
            )

        return {
            "status": status,
            "agent": self.agent_id,
            "last_run": None,
            "metrics": {},
        }

    def process(self, event: EventEnvelope) -> EventEnvelope:
        """
        Consume an inbound event and emit a stub record-enriched event.

        The walking-skeleton implementation loads and returns the payload from
        `agents/data/fixtures/fixture_enriched.json`, while preserving the
        original correlation identifier.
        """
        log.info(
            "enrichment_process_called",
            agent=self.agent_id,
            correlation_id=event.correlation_id,
        )

        if not self._fixture_exists():
            log.error(
                "enrichment_fixture_missing_during_process",
                agent=self.agent_id,
                fixture=str(self._fixture_path),
            )
            payload: dict = {
                "stage": "enrichment_failed",
                "reason": "fixture_missing",
            }
        else:
            try:
                raw = json.loads(self._fixture_path.read_text(encoding="utf-8"))
                # Fixture is a list — wrap it in a dict so EventEnvelope
                # payload validation passes (payload must be a dict)
                payload = {"enriched_records": raw} if isinstance(raw, list) else raw
            except json.JSONDecodeError:
                log.error(
                    "enrichment_fixture_invalid_json",
                    agent=self.agent_id,
                    fixture=str(self._fixture_path),
                )
                payload = {
                    "stage": "enrichment_failed",
                    "reason": "invalid_fixture_json",
                }

        outbound = EventEnvelope(
            correlation_id=event.correlation_id,
            agent_id=self.agent_id,
            payload=payload,
        )

        log.info(
            "enrichment_process_complete",
            agent=self.agent_id,
            correlation_id=outbound.correlation_id,
            outbound_event_id=outbound.event_id,
        )

        return outbound
