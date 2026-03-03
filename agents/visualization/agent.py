from __future__ import annotations

"""
VisualizationAgent stub for the Job Intelligence Engine walking skeleton.

This agent is responsible for generating dashboards and export artifacts from
analytics outputs. In the Week 2 walking skeleton, this implementation does
not render any real artifacts; it simply echoes the inbound payload while
confirming that shared fixture assets are present.
"""

from pathlib import Path

import structlog

from agents.common.base_agent import BaseAgent
from agents.common.event_envelope import EventEnvelope


log = structlog.get_logger()


class VisualizationAgent(BaseAgent):
    """Stub implementation of the Visualization Agent for the walking skeleton."""

    def __init__(self) -> None:
        """Initialize the visualization agent with its canonical identifier."""
        super().__init__(agent_id="visualization")
        self._fixtures_dir = (
            Path(__file__).resolve().parent.parent / "data" / "fixtures"
        )

    def health_check(self) -> dict:
        """
        Validate that the shared fixtures directory exists and return health.

        The visualization agent relies on upstream agents producing events
        consistent with the documented fixture payloads. This method verifies
        that the fixtures directory is present on disk.
        """
        fixtures_ok = self._fixtures_dir.exists()

        if fixtures_ok:
            status = "ok"
            log.info(
                "visualization_health_ok",
                agent=self.agent_id,
                fixtures_dir=str(self._fixtures_dir),
            )
        else:
            status = "down"
            log.error(
                "visualization_health_failed",
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
        Consume an inbound event and emit a stub render-complete event.

        The walking-skeleton implementation passes through the inbound payload
        and annotates it with a marker indicating that visualization has been
        invoked. No real rendering is performed at this stage.
        """
        log.info(
            "visualization_process_called",
            agent=self.agent_id,
            correlation_id=event.correlation_id,
        )

        payload = {
            "stage": "render_complete",
            "render_source": event.payload,
        }

        outbound = EventEnvelope(
            correlation_id=event.correlation_id,
            agent_id=self.agent_id,
            payload=payload,
        )

        log.info(
            "visualization_process_complete",
            agent=self.agent_id,
            correlation_id=outbound.correlation_id,
            outbound_event_id=outbound.event_id,
        )

        return outbound

