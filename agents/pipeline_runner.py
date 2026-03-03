"""
Pipeline Runner — Week 2 walking skeleton.

Chains 8 agents in sequence. No LangGraph, no DB writes, no LLM calls.

Usage (run from repo root):
  python -m agents.pipeline_runner
  python -m agents.pipeline_runner --stages 3
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path

import structlog

from agents.common.event_envelope import EventEnvelope
from agents.demand_analysis.agent import DemandAnalysisAgent
from agents.analytics.agent import AnalyticsAgent
from agents.enrichment.agent import EnrichmentAgent
from agents.ingestion.agent import IngestionAgent
from agents.normalization.agent import NormalizationAgent
from agents.orchestration.agent import OrchestrationAgent
from agents.skills_extraction.agent import SkillsExtractionAgent
from agents.visualization.agent import VisualizationAgent

log = structlog.get_logger()

DEFAULT_FIXTURE = Path(__file__).resolve().parent / "data" / "fixtures" / "fallback_scrape_sample.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "output" / "pipeline_run.json"


def _default_agents() -> list[tuple]:
    """Return the canonical 8-agent chain as (agent, phase2) tuples."""
    return [
        (IngestionAgent(), False),
        (NormalizationAgent(), False),
        (SkillsExtractionAgent(), False),
        (EnrichmentAgent(), False),
        (AnalyticsAgent(), False),
        (VisualizationAgent(), False),
        (OrchestrationAgent(), False),
        (DemandAnalysisAgent(), True),
    ]


def _serialize_event(envelope: EventEnvelope) -> dict:
    """Convert EventEnvelope to a JSON-serializable dict."""
    return {
        "event_id": envelope.event_id,
        "correlation_id": envelope.correlation_id,
        "agent_id": envelope.agent_id,
        "timestamp": envelope.timestamp.isoformat(),
        "schema_version": envelope.schema_version,
        "payload": envelope.payload,
    }


def _serialize_phase2_skipped(
    correlation_id: str, agent_id: str, event_id: str, timestamp: str
) -> dict:
    """Build envelope-shaped dict for Phase 2 skipped entry (all six fields)."""
    return {
        "event_id": event_id,
        "correlation_id": correlation_id,
        "agent_id": agent_id,
        "timestamp": timestamp,
        "schema_version": "1.0",
        "payload": {"phase2_skipped": True},
    }


def _health_check(agent_list: list[tuple]) -> list[str]:
    """
    Run health_check on all agents.
    Phase 1: status != 'ok' -> add to failing, abort.
    Phase 2: status != 'ok' -> log warning only.
    Returns list of Phase 1 agent_ids that failed.
    """
    failing = []
    for agent, is_phase2 in agent_list:
        result = agent.health_check()
        status = result.get("status", "down")
        agent_id = result.get("agent", getattr(agent, "agent_id", "unknown"))
        if is_phase2:
            if status != "ok":
                log.warning("phase2_agent_degraded", agent_id=agent_id, status=status)
            continue
        if status != "ok":
            failing.append(agent_id)
    return failing


def run_pipeline(records: list[dict], agent_list: list[tuple]) -> list[dict]:
    """
    Run the pipeline for each record through all agents.

    Args:
        records: List of raw job postings (dicts).
        agent_list: List of (agent, phase2) tuples in execution order.

    Returns:
        run_log: List of serializable dicts (emitted events + Phase2 skipped envelope-shaped entries).
    """
    run_log: list[dict] = []

    for posting in records:
        correlation_id = str(uuid.uuid4())
        envelope = EventEnvelope(
            correlation_id=correlation_id,
            agent_id="pipeline_runner",
            payload=posting if isinstance(posting, dict) else {"posting": posting},
        )

        for agent, _is_phase2 in agent_list:
            out = agent.process(envelope)
            if out is not None:
                log.info(
                    "event_emitted",
                    agent_id=out.agent_id,
                    event_id=out.event_id,
                    correlation_id=out.correlation_id,
                    timestamp=out.timestamp.isoformat(),
                )
                run_log.append(_serialize_event(out))
                envelope = out
            else:
                agent_id = getattr(agent, "agent_id", "unknown")
                if not _is_phase2:
                    raise SystemExit(
                        f"Phase 1 agent returned None: agent_id={agent_id}, correlation_id={correlation_id}"
                    )
                event_id = str(uuid.uuid4())
                timestamp = datetime.utcnow().isoformat()
                entry = _serialize_phase2_skipped(
                    correlation_id=correlation_id,
                    agent_id=agent_id,
                    event_id=event_id,
                    timestamp=timestamp,
                )
                log.info(
                    "phase2_skipped",
                    agent_id=agent_id,
                    event_id=event_id,
                    correlation_id=correlation_id,
                    timestamp=timestamp,
                )
                run_log.append(entry)

    return run_log


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stages", type=int, default=None, help="Run only the first N agents (default: all 8)")
    args = parser.parse_args()

    with open(DEFAULT_FIXTURE, encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list):
        records = [records]

    agent_list = _default_agents()
    if args.stages is not None:
        agent_list = agent_list[: args.stages]
    failing = _health_check(agent_list)
    if failing:
        raise SystemExit(
            f"Pipeline aborted: Phase 1 agent(s) health_check failed: {', '.join(failing)}"
        )

    run_log = run_pipeline(records, agent_list)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(run_log, f, indent=2)

    log.info("pipeline_complete", output_path=str(OUTPUT_PATH), entry_count=len(run_log))


if __name__ == "__main__":
    main()
