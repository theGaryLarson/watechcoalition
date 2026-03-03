from __future__ import annotations

"""
DemandAnalysisAgent stub for the Job Intelligence Engine walking skeleton.

This Phase 2 agent will be responsible for computing demand signals and
forecasts from enriched job records. In the Week 2 walking skeleton, the agent
is intentionally not implemented and therefore does not emit any outbound
events, but it exposes a health_check that reports a degraded status so the
pipeline does not abort.
"""

from pathlib import Path

import structlog

from agents.common.base_agent import BaseAgent
from agents.common.event_envelope import EventEnvelope


log = structlog.get_logger()


class DemandAnalysisAgent(BaseAgent):
    """Stub implementation of the Phase 2 Demand Analysis Agent."""

    def __init__(self) -> None:
        """Initialize the demand analysis agent with its canonical identifier."""
        super().__init__(agent_id="demand_analysis")
        self._fixtures_dir = (
            Path(__file__).resolve().parent.parent / "data" / "fixtures"
        )

    def health_check(self) -> dict:
        """
        Report a degraded status while validating basic environment readiness.

        Demand analysis is a Phase 2 concern and is not yet implemented in the
        walking skeleton. This method checks that the shared fixtures directory
        exists to confirm the environment is reasonably configured, but always
        returns a "degraded" status so that the pipeline runner treats this as
        a warning rather than aborting.
        """
        fixtures_ok = self._fixtures_dir.exists()

        if fixtures_ok:
            log.info(
                "demand_analysis_health_degraded",
                agent=self.agent_id,
                fixtures_dir=str(self._fixtures_dir),
            )
        else:
            log.warning(
                "demand_analysis_health_degraded_missing_fixtures",
                agent=self.agent_id,
                fixtures_dir=str(self._fixtures_dir),
                fixtures_dir_exists=self._fixtures_dir.exists(),
            )

        return {
            "status": "degraded",
            "agent": self.agent_id,
            "last_run": None,
            "metrics": {},
        }

    def process(self, event: EventEnvelope) -> None:
        """
        Accept an inbound event but do not emit any outbound events.

        Demand analysis is not part of the Phase 1 implementation, so this
        method returns None to indicate that no further processing occurs at
        this stage. The pipeline runner is expected to handle this gracefully.
        """
        log.info(
            "demand_analysis_process_noop",
            agent=self.agent_id,
            correlation_id=event.correlation_id,
        )
        return None

