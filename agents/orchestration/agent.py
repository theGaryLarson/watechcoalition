"""
Orchestration Agent — Sprint 1 walking skeleton.

Passes through inbound payload unchanged. No scheduling, retries, or routing yet.
"""

from __future__ import annotations

from agents.common.base_agent import BaseAgent
from agents.common.event_envelope import EventEnvelope

AGENT_ID = "orchestration_agent"


class OrchestrationAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_id=AGENT_ID)

    def health_check(self) -> dict:
        return {"status": "ok", "agent": self.agent_id, "last_run": None, "metrics": {}}

    def process(self, event: EventEnvelope) -> EventEnvelope | None:
        return EventEnvelope(
            correlation_id=event.correlation_id,
            agent_id=self.agent_id,
            payload=event.payload,
        )
