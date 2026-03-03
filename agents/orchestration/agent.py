from __future__ import annotations

"""
OrchestrationAgent stub for the Job Intelligence Engine walking skeleton.

This agent is responsible for scheduling, monitoring, and coordinating the
pipeline. In the Week 2 walking skeleton, this implementation does not perform
real orchestration; it simply annotates events to prove that the orchestration
stage is wired into the pipeline.
"""

from pathlib import Path

import structlog

from agents.common.base_agent import BaseAgent
from agents.common.event_envelope import EventEnvelope


log = structlog.get_logger()


class OrchestrationAgent(BaseAgent):
    """Stub implementation of the Orchestration Agent for the walking skeleton."""

    def __init__(self) -> None:
        """Initialize the orchestration agent with its canonical identifier."""
        super().__init__(agent_id="orchestration")
        self._fixtures_dir = (
            Path(__file__).resolve().parent.parent / "data" / "fixtures"
        )

    def health_check(self) -> dict:
        """
        Validate that the shared fixtures directory exists and return health.

        The orchestration agent depends transitively on all other agents being
        able to read their fixture payloads. As a minimal real check in the
        walking skeleton, it verifies that the shared fixtures directory is
        present on disk.
        """
        fixtures_ok = self._fixtures_dir.exists()

        if fixtures_ok:
            status = "ok"
            log.info(
                "orchestration_health_ok",
                agent=self.agent_id,
                fixtures_dir=str(self._fixtures_dir),
            )
        else:
            status = "down"
            log.error(
                "orchestration_health_failed",
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
        Consume an inbound event and emit a stub orchestration event.

        The walking-skeleton implementation wraps the inbound payload in a
        simple envelope that records that orchestration has observed the event.
        """
        log.info(
            "orchestration_process_called",
            agent=self.agent_id,
            correlation_id=event.correlation_id,
        )

        payload = {
            "stage": "orchestration_observed",
            "observed_payload": event.payload,
        }

        outbound = EventEnvelope(
            correlation_id=event.correlation_id,
            agent_id=self.agent_id,
            payload=payload,
        )

        log.info(
            "orchestration_process_complete",
            agent=self.agent_id,
            correlation_id=outbound.correlation_id,
            outbound_event_id=outbound.event_id,
        )

        return outbound

