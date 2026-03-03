from __future__ import annotations

"""
NormalizationAgent stub for the Job Intelligence Engine walking skeleton.

This agent is responsible for transforming raw ingested job postings into a
canonical JobRecord shape. In the Week 2 walking skeleton, this implementation
performs no real normalization logic and instead passes through the inbound
payload while confirming that shared fixture assets are present.
"""

from pathlib import Path

import structlog

from agents.common.base_agent import BaseAgent
from agents.common.event_envelope import EventEnvelope


log = structlog.get_logger()


class NormalizationAgent(BaseAgent):
    """Stub implementation of the Normalization Agent for the walking skeleton."""

    def __init__(self) -> None:
        """Initialize the normalization agent with its canonical identifier."""
        super().__init__(agent_id="normalization")
        self._fixtures_dir = (
            Path(__file__).resolve().parent.parent / "data" / "fixtures"
        )

    def health_check(self) -> dict:
        """
        Validate that the shared fixtures directory exists and return health.

        The normalization agent verifies that the common fixtures directory is
        available on disk, ensuring that the environment has been set up with
        the expected sample data files.
        """
        fixtures_ok = self._fixtures_dir.exists()

        if fixtures_ok:
            status = "ok"
            log.info(
                "normalization_health_ok",
                agent=self.agent_id,
                fixtures_dir=str(self._fixtures_dir),
            )
        else:
            status = "down"
            log.error(
                "normalization_health_failed",
                agent=self.agent_id,
                fixtures_dir=str(self._fixtures_dir),
                fixtures_dir_exists=self._fixtures_dir.exists(),
            )

        return {
            "status": status,
            "agent": self.agent_id,
            "last_run": None,
            "metrics": {},
        }

    def process(self, event: EventEnvelope) -> EventEnvelope:
        """
        Consume an inbound event and emit a stub normalization event.

        The walking-skeleton implementation simply forwards the inbound payload
        and annotates it with a lightweight marker indicating that the record
        has passed through the normalization stage.
        """
        log.info(
            "normalization_process_called",
            agent=self.agent_id,
            correlation_id=event.correlation_id,
        )

        payload = {
            "stage": "normalization_complete",
            "normalized_record": event.payload,
        }

        outbound = EventEnvelope(
            correlation_id=event.correlation_id,
            agent_id=self.agent_id,
            payload=payload,
        )

        log.info(
            "normalization_process_complete",
            agent=self.agent_id,
            correlation_id=outbound.correlation_id,
            outbound_event_id=outbound.event_id,
        )

        return outbound

