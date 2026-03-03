"""
Skills Extraction Agent — Sprint 1 walking skeleton.

Loads fixture_skills_extracted.json; selects records by posting_id from inbound payload.
No real LLM calls, no DB writes.
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.common.base_agent import BaseAgent
from agents.common.event_envelope import EventEnvelope

AGENT_ID = "skills_extraction_agent"
FIXTURE_PATH = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "fixture_skills_extracted.json"


class SkillsExtractionAgent(BaseAgent):
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
            fixture_list = json.load(f)
        by_id = {p["posting_id"]: p for p in fixture_list if isinstance(p, dict) and "posting_id" in p}
        postings = event.payload.get("postings", [])
        out = []
        for p in postings:
            if not isinstance(p, dict):
                continue
            pid = p.get("posting_id")
            if pid in by_id:
                out.append(by_id[pid])
        return EventEnvelope(
            correlation_id=event.correlation_id,
            agent_id=self.agent_id,
            payload={"postings": out},
        )
