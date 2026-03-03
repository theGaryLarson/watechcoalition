"""
Ingestion Agent — Sprint 1 walking skeleton.

Reads fallback_scrape_sample.json, wraps in EventEnvelope.
No LLM calls, no DB writes, no cross-agent calls.
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.common.base_agent import BaseAgent
from agents.common.event_envelope import EventEnvelope

AGENT_ID = "ingestion_agent"
FIXTURE_PATH = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "fallback_scrape_sample.json"


class IngestionAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_id=AGENT_ID)

    def health_check(self) -> dict:
        try:
            if not FIXTURE_PATH.exists():
                return {"status": "down", "agent": self.agent_id, "last_run": None, "metrics": {}}
            with open(FIXTURE_PATH, encoding="utf-8") as f:
                json.load(f)
            return {"status": "ok", "agent": self.agent_id, "last_run": None, "metrics": {}}
        except (OSError, json.JSONDecodeError):
            return {"status": "down", "agent": self.agent_id, "last_run": None, "metrics": {}}

    def process(self, event: EventEnvelope) -> EventEnvelope | None:
        with open(FIXTURE_PATH, encoding="utf-8") as f:
            postings = json.load(f)
        return EventEnvelope(
            correlation_id=event.correlation_id,
            agent_id=self.agent_id,
            payload={"postings": postings},
        )
