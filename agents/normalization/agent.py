"""
Normalization Agent — Sprint 1 walking skeleton.

Consumes IngestBatch payload; minimal deterministic transform (strip whitespace).
No LLM, no DB writes, no cross-agent calls.
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.common.base_agent import BaseAgent
from agents.common.event_envelope import EventEnvelope

AGENT_ID = "normalization_agent"
REQUIRED_POSTING_KEYS = ("posting_id", "raw_text")
FIXTURE_PATH = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "fallback_scrape_sample.json"


def _has_required_fields(payload: dict) -> bool:
    """True if payload has postings and each has posting_id and raw_text."""
    postings = payload.get("postings")
    if not isinstance(postings, list):
        return False
    for p in postings:
        if not isinstance(p, dict):
            return False
        if not all(k in p for k in REQUIRED_POSTING_KEYS):
            return False
    return True


def _normalize_posting(posting: dict) -> dict:
    """Minimal transform: strip whitespace from string fields."""
    out = dict(posting)
    for key in ("raw_text", "title", "company", "location", "source", "url"):
        if key in out and isinstance(out[key], str):
            out[key] = out[key].strip()
    return out


class NormalizationAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_id=AGENT_ID)

    def health_check(self) -> dict:
        try:
            if not FIXTURE_PATH.exists():
                return {"status": "down", "agent": self.agent_id, "last_run": None, "metrics": {}}
            with open(FIXTURE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            payload = {"postings": data} if isinstance(data, list) else data
            if not _has_required_fields(payload):
                return {"status": "down", "agent": self.agent_id, "last_run": None, "metrics": {}}
            return {"status": "ok", "agent": self.agent_id, "last_run": None, "metrics": {}}
        except (OSError, json.JSONDecodeError):
            return {"status": "down", "agent": self.agent_id, "last_run": None, "metrics": {}}

    def process(self, event: EventEnvelope) -> EventEnvelope | None:
        payload = event.payload
        postings = payload.get("postings", [])
        normalized = [_normalize_posting(p) for p in postings if isinstance(p, dict)]
        return EventEnvelope(
            correlation_id=event.correlation_id,
            agent_id=self.agent_id,
            payload={"postings": normalized},
        )
