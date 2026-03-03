from __future__ import annotations

"""
Pipeline runner for the Job Intelligence Engine walking skeleton.

This module wires together the eight agent stubs into a linear pipeline:

    Ingestion → Normalization → Skills Extraction → Enrichment →
    Analytics → Visualization → Orchestration → Demand Analysis

For each of the first ten records in `agents/data/fixtures/fallback_scrape_sample.json`,
the runner creates an initial EventEnvelope and passes it through all eight
agents in sequence, enforcing invariant correlation identifiers and collecting
every emitted event into a run log written to
`agents/data/output/pipeline_run.json`.
"""

import json
from pathlib import Path
from typing import Iterable, List
import secrets

import structlog

from agents.analytics.agent import AnalyticsAgent
from agents.common.event_envelope import EventEnvelope
from agents.demand_analysis.agent import DemandAnalysisAgent
from agents.enrichment.agent import EnrichmentAgent
from agents.ingestion.agent import IngestionAgent
from agents.normalization.agent import NormalizationAgent
from agents.orchestration.agent import OrchestrationAgent
from agents.skills_extraction.agent import SkillsExtractionAgent
from agents.visualization.agent import VisualizationAgent


log = structlog.get_logger()


def _uuid4_str() -> str:
    """
    Generate a UUID4-compatible string without importing the stdlib uuid module.

    This avoids interference from a project-local `platform` package that would
    otherwise be imported by the uuid module, while still producing identifiers
    that conform to the UUID v4 bit layout.
    """
    random_bytes = bytearray(secrets.token_bytes(16))
    random_bytes[6] = (random_bytes[6] & 0x0F) | 0x40  # version 4
    random_bytes[8] = (random_bytes[8] & 0x3F) | 0x80  # variant 10xx
    hexed = random_bytes.hex()
    return (
        f"{hexed[0:8]}-"
        f"{hexed[8:12]}-"
        f"{hexed[12:16]}-"
        f"{hexed[16:20]}-"
        f"{hexed[20:32]}"
    )


def _load_input_records(fixture_path: Path, limit: int = 10) -> list[dict]:
    """
    Load raw input records from the fallback scrape fixture.

    Parameters
    ----------
    fixture_path:
        Path to the JSON fixture containing raw scraped job records.
    limit:
        Maximum number of records to load from the fixture.

    Returns
    -------
    list[dict]
        A list of raw record dictionaries limited to the specified count.
    """
    raw_text = fixture_path.read_text(encoding="utf-8")
    data = json.loads(raw_text)

    if not isinstance(data, list):
        raise ValueError(
            f"Expected list of records in fixture, found {type(data).__name__}"
        )

    records = data[:limit]
    log.info(
        "pipeline_loaded_input_records",
        fixture=str(fixture_path),
        requested_limit=limit,
        actual_count=len(records),
    )
    return records


def _run_health_checks(
    phase1_agents: Iterable[object],
    demand_agent: DemandAnalysisAgent,
) -> bool:
    """
    Execute health checks for all agents and decide whether to proceed.

    Phase 1 agents must report status == "ok" or the pipeline aborts. The
    Phase 2 DemandAnalysisAgent is allowed to return a non-ok status; this is
    logged as a warning but does not abort the run.

    Parameters
    ----------
    phase1_agents:
        Iterable of Phase 1 agent instances to check.
    demand_agent:
        The Phase 2 DemandAnalysisAgent instance.

    Returns
    -------
    bool
        True if the pipeline may proceed; False if it must abort.
    """
    ok_to_proceed = True

    for agent in phase1_agents:
        result = agent.health_check()
        status = result.get("status")
        agent_id = result.get("agent")
        if status == "ok":
            log.info(
                "pipeline_health_ok",
                agent=agent_id,
                status=status,
            )
        else:
            ok_to_proceed = False
            log.error(
                "pipeline_health_failed",
                agent=agent_id,
                status=status,
            )

    demand_result = demand_agent.health_check()
    demand_status = demand_result.get("status")
    log_level = log.warning if demand_status != "ok" else log.info
    log_level(
        "pipeline_health_phase2",
        agent=demand_result.get("agent"),
        status=demand_status,
    )

    return ok_to_proceed


def _log_event(envelope: EventEnvelope) -> None:
    """
    Emit a structured log entry for a single event envelope.

    Parameters
    ----------
    envelope:
        The EventEnvelope to log.
    """
    log.info(
        "pipeline_event_emitted",
        agent_id=envelope.agent_id,
        event_id=envelope.event_id,
        correlation_id=envelope.correlation_id,
        timestamp=envelope.timestamp.isoformat(),
    )


def run_pipeline() -> None:
    """
    Execute the walking-skeleton pipeline across a small set of fixture records.

    The runner performs the following steps:

    1. Instantiate all eight agent stubs.
    2. Run health_check() on all agents, aborting on any Phase 1 failure.
    3. Load up to 10 raw records from the fallback scrape fixture.
    4. For each record, generate a correlation_id, create an initial
       EventEnvelope, and pass it through all eight agents in sequence.
    5. Collect every emitted event into a run log and persist it to disk.
    """
    base_dir = Path(__file__).resolve().parent
    fixtures_dir = base_dir / "data" / "fixtures"
    output_dir = base_dir / "data" / "output"

    fixture_path = fixtures_dir / "fallback_scrape_sample.json"
    output_path = output_dir / "pipeline_run.json"

    ingress = IngestionAgent()
    normalization = NormalizationAgent()
    skills = SkillsExtractionAgent()
    enrichment = EnrichmentAgent()
    analytics = AnalyticsAgent()
    visualization = VisualizationAgent()
    orchestration = OrchestrationAgent()
    demand = DemandAnalysisAgent()

    phase1_agents: List[object] = [
        ingress,
        normalization,
        skills,
        enrichment,
        analytics,
        visualization,
        orchestration,
    ]

    if not _run_health_checks(phase1_agents=phase1_agents, demand_agent=demand):
        log.error("pipeline_aborted_due_to_health_check_failure")
        return

    records = _load_input_records(fixture_path=fixture_path, limit=10)

    agents_in_order = [
        ingress,
        normalization,
        skills,
        enrichment,
        analytics,
        visualization,
        orchestration,
        demand,
    ]

    run_log: list[dict] = []

    for record in records:
        correlation_id = _uuid4_str()
        envelope = EventEnvelope(
            correlation_id=correlation_id,
            agent_id="pipeline_runner",
            payload=record,
        )

        for agent in agents_in_order:
            result = agent.process(envelope)

            if result is None:
                # Phase 2 DemandAnalysisAgent returns None; record a skipped
                # event while keeping the last valid envelope for invariants.
                log.info(
                    "pipeline_phase2_skipped",
                    agent=getattr(agent, "agent_id", "unknown"),
                    correlation_id=envelope.correlation_id,
                )
                synthetic = EventEnvelope(
                    correlation_id=envelope.correlation_id,
                    agent_id=getattr(agent, "agent_id", "demand_analysis"),
                    payload={
                        "stage": "demand_analysis_skipped",
                        "reason": "phase2_not_implemented",
                    },
                )
                _log_event(synthetic)
                # Use Pydantic's JSON-safe dump mode to convert datetimes to strings
                # so the final run_log is JSON-serializable by the stdlib json module.
                run_log.append(synthetic.model_dump(mode="json"))
                continue

            if result.correlation_id != envelope.correlation_id:
                raise ValueError(
                    "Agent altered correlation_id; this violates pipeline invariants."
                )

            envelope = result
            _log_event(envelope)
            # model_dump(mode="json") converts datetime fields to ISO strings
            # which avoids TypeError: Object of type datetime is not JSON serializable
            run_log.append(envelope.model_dump(mode="json"))

    if len(run_log) != 80:
        log.warning(
            "pipeline_run_log_unexpected_length",
            expected=80,
            actual=len(run_log),
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(run_log, indent=2), encoding="utf-8")

    log.info(
        "pipeline_run_complete",
        output_path=str(output_path),
        event_count=len(run_log),
    )


if __name__ == "__main__":
    run_pipeline()

