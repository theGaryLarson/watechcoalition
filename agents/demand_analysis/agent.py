"""
Demand Analysis Agent — Phase 2 only (scaffold).

This agent is not implemented in Phase 1. Time series, forecasting, and
DemandSignalsUpdated emission are deferred to Phase 2.
"""

from __future__ import annotations

from agents.common.base_agent import BaseAgent
from agents.common.event_envelope import EventEnvelope

AGENT_ID = "demand_analysis_agent"


class DemandAnalysisAgent(BaseAgent):
    """Phase 2 only. Consumes RecordEnriched; emits DemandSignalsUpdated. Not implemented."""

    def __init__(self) -> None:
        super().__init__(agent_id=AGENT_ID)

    def health_check(self) -> dict:
        return {"status": "degraded", "agent": self.agent_id, "last_run": None, "metrics": {}}

    def process(self, event: EventEnvelope) -> EventEnvelope | None:
        return None
