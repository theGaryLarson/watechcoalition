from __future__ import annotations

"""
IngestionAgent stub for the Job Intelligence Engine walking skeleton.

This agent is responsible for ingesting raw job postings from external sources
and emitting an EventEnvelope that downstream agents can consume. In the Week 2
walking skeleton, this implementation loads no external data and simply echoes
the inbound event metadata while confirming required fixture files exist.
"""

import json
from pathlib import Path

import structlog

from agents.common.base_agent import BaseAgent
from agents.common.event_envelope import EventEnvelope


log = structlog.get_logger()


class IngestionAgent(BaseAgent):
    """Stub implementation of the Ingestion Agent for the walking skeleton."""

    def __init__(self) -> None:
        """Initialize the ingestion agent with its canonical identifier."""
        super().__init__(agent_id="ingestion")
        self._fixtures_dir = (
            Path(__file__).resolve().parent.parent / "data" / "fixtures"
        )
        self._sample_fixture = self._fixtures_dir / "fallback_scrape_sample.json"

    def health_check(self) -> dict:
        """
        Validate that required local fixtures exist and return agent health.

        The ingestion agent verifies that the fixture directory and a sample
        scrape fixture file are present on disk. This provides a real check
        that the development environment is correctly configured, rather than
        blindly returning an "ok" status.
        """
        fixtures_ok = self._fixtures_dir.exists() and self._sample_fixture.exists()

        if fixtures_ok:
            status = "ok"
            log.info(
                "ingestion_health_ok",
                agent=self.agent_id,
                fixtures_dir=str(self._fixtures_dir),
                sample_fixture=str(self._sample_fixture),
            )
        else:
            status = "down"
            log.error(
                "ingestion_health_failed",
                agent=self.agent_id,
                fixtures_dir=str(self._fixtures_dir),
                sample_fixture=str(self._sample_fixture),
                fixtures_dir_exists=self._fixtures_dir.exists(),
                sample_fixture_exists=self._sample_fixture.exists(),
            )

        return {
            "status": status,
            "agent": self.agent_id,
            "last_run": None,
            "metrics": {},
        }

    def process(self, event: EventEnvelope) -> EventEnvelope:
        """
        Consume an inbound event and emit a stub ingestion event.

        The walking-skeleton implementation does not perform real ingestion;
        instead, it echoes the inbound correlation_id and wraps a minimal
        payload that records that ingestion has been invoked.
        """
        log.info(
            "ingestion_process_called",
            agent=self.agent_id,
            correlation_id=event.correlation_id,
        )

        payload = {
            "stage": "ingestion_complete",
            "source_event": {
                "event_id": event.event_id,
                "agent_id": event.agent_id,
            },
        }

        # Optionally load a small sample fixture to prove filesystem access.
        if self._sample_fixture.exists():
            try:
                payload["sample_raw_record"] = json.loads(
                    self._sample_fixture.read_text(encoding="utf-8")
                )
            except json.JSONDecodeError:
                log.warning(
                    "ingestion_sample_fixture_invalid_json",
                    fixture=str(self._sample_fixture),
                )

        outbound = EventEnvelope(
            correlation_id=event.correlation_id,
            agent_id=self.agent_id,
            payload=payload,
        )

        log.info(
            "ingestion_process_complete",
            agent=self.agent_id,
            correlation_id=outbound.correlation_id,
            outbound_event_id=outbound.event_id,
        )

        return outbound

