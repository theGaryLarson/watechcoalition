# Architecture Orientation — Job Intelligence Engine

Short reference for all eight agents: Phase 1 scope, event flow, and Phase 1 vs Phase 2 boundary.  
**Source of truth:** `docs/planning/ARCHITECTURE_DEEP.md`. Agents communicate via events only; no direct calls.

---

## 1. Ingestion Agent

**Phase 1:** Polls JSearch via httpx and scrapes via Crawl4AI; fingerprints each record, deduplicates against staging, and writes to `raw_ingested_jobs` with provenance (source, external_id, ingestion_run_id). It is **deterministic** (no LLM). It **consumes** no pipeline events (triggered by schedule). It **emits** `IngestBatch` (consumed by Normalization and Orchestrator); on source unreachable after retries it emits `SourceFailure` to Orchestrator only. **Phase 1 boundary:** Full ingestion, dedup, and staging are Phase 1; there is no Phase 2 implementation for this agent in the spec.

---

## 2. Normalization Agent

**Phase 1:** Maps source payloads to the canonical `JobRecord` via per-source field mappers, standardizes dates (ISO 8601), salaries, locations, and employment types, and validates with Pydantic; violations are quarantined. It is **deterministic**. It **consumes** `IngestBatch` (from Ingestion). It **emits** `NormalizationComplete` (consumed by Skills Extraction and Orchestrator); on batch failure it emits `NormalizationFailed` to Orchestrator only. **Phase 1 boundary:** All normalization and quarantine logic is Phase 1; the spec does not assign Phase 2 work to this agent.

---

## 3. Skills Extraction Agent

**Phase 1:** Uses LLM inference over title, description, requirements, and responsibilities to produce `SkillRecord`s; links to the taxonomy (exact match → normalized → embedding ≥ 0.92 → O*NET → else raw_skill) and logs every LLM call to `llm_audit_log`. It is **LLM required** for extraction. It **consumes** `NormalizationComplete` (from Normalization). It **emits** `SkillsExtracted` (consumed by Enrichment and Orchestrator). **Phase 1 boundary:** Taxonomy linking and raw_skill emission are Phase 1; resolution of raw_skill to alternative taxonomies is Enrichment Phase 2, not Skills Extraction.

---

## 4. Enrichment Agent

**Phase 1 (lite):** Classifies role and seniority; computes quality score and spam score; resolves `company_id` and `location_id`; maps `sector_id`; writes to `job_postings` only when `company_id` is resolved; applies spam tiers (proceed / flag / auto-reject per IC #8). It is **LLM optional** (classifiers may be rule-based or LLM). It **consumes** `SkillsExtracted` (from Skills Extraction). It **emits** `RecordEnriched` (consumed by Analytics, by Demand Analysis in Phase 2, and by Orchestrator). **Phase 1 boundary:** Role/seniority/quality/spam, company/location/sector resolution, and write to `job_postings` are Phase 1; company/geo/labor-market enrichment, raw_skill resolution, SOC/NOC, prevailing wage, and composite enrichment quality are Phase 2.

---

## 5. Analytics Agent

**Phase 1:** Builds aggregates (skill, role, industry, region, experience level, company size); salary distributions; co-occurrence matrices; posting lifecycle metrics; weekly insight summaries (LLM with template fallback); and text-to-SQL with guardrails. It is **LLM optional** (template fallback when LLM unavailable). It **consumes** `RecordEnriched` (from Enrichment); in Phase 2 it may also consume `DemandSignalsUpdated`. It **emits** `AnalyticsRefreshed` (consumed by Visualization and Orchestrator). **Phase 1 boundary:** All aggregate and query features above are Phase 1; consumption of demand signals is Phase 2.

---

## 6. Visualization Agent

**Phase 1:** Serves dashboard pages (Ingestion Overview, Normalization Quality, Skill Taxonomy Coverage, Weekly Insights, Ask the Data, Operations & Alerts) and exports (PDF, CSV, JSON); uses a read-only DB and TTL cache; never serves a blank page (stale data with banner if needed). It is **deterministic** for rendering (LLM-backed content comes from Analytics). It **consumes** `AnalyticsRefreshed` (from Analytics); in Phase 2 it also consumes `DemandSignalsUpdated`. It **emits** `RenderComplete` (to Orchestrator); on failure it may emit `RenderFailed` and on stale data `VisualizationDegraded` (both to Orchestrator only). **Phase 1 boundary:** All dashboard and export behavior above is Phase 1; consuming `DemandSignalsUpdated` is Phase 2.

---

## 7. Orchestration Agent

**Phase 1:** Runs the master schedule (e.g. APScheduler), routes events via LangGraph StateGraph, applies retry policies with back-off, and maintains a structured audit log (100% completeness). It is **deterministic**. It **consumes** all pipeline events for coordination and monitoring; critically, it is the **sole consumer** of every event whose type ends with `Failed` or `Alert` (e.g. `SourceFailure`, `NormalizationFailed`, `RenderFailed`, `VisualizationDegraded`, and any other `*Failed` / `*Alert`). No other agent may consume Failed or Alert events. It **emits** trigger and retry signals (not listed as a separate event type in the Event Catalog). **Phase 1 boundary:** Scheduling, routing, retries, alerting tiers, and audit are Phase 1; circuit breaker, saga, compensating flows, and admin API are Phase 2.

---

## 8. Demand Analysis Agent (Phase 2 only)

**Phase 2 only:** Not implemented in Phase 1; directory is scaffold only. When implemented, it will consume `RecordEnriched`, produce time-series and demand signals, and emit `DemandSignalsUpdated` (consumed by Analytics and Visualization and Orchestrator) and `DemandAnomaly` (consumed by Orchestrator only). It is **LLM optional** per spec (time-series and forecasting). **Phase 1 boundary:** No Phase 1 implementation; entire agent is Phase 2.

---

## Single job posting flow

One job posting moves as follows:

1. **Ingestion** produces **`IngestBatch`** (payload includes the batch of raw records). **Normalization** consumes `IngestBatch`.
2. **Normalization** produces **`NormalizationComplete`** (payload includes normalized JobRecords). **Skills Extraction** consumes `NormalizationComplete`.
3. **Skills Extraction** produces **`SkillsExtracted`** (payload includes records with skills attached). **Enrichment** consumes `SkillsExtracted`.

The spec does not define ordering or delivery guarantees (e.g. exactly-once, in-order delivery) for these events; such behavior is not specified in ARCHITECTURE_DEEP.md.

---

## Self-verification checklist

- [ ] **Orchestration is the sole consumer of Failed and Alert events:** No agent other than Orchestration may consume any event whose type ends with `Failed` or `Alert`; all such events are consumed only by the Orchestration Agent.
- [ ] **Phase 2 is not mixed into Phase 1 summaries:** Each agent section describes only Phase 1 behavior and explicitly calls out the Phase 1 vs Phase 2 boundary; Phase 2 work (Demand Analysis, circuit breaker, saga, admin API, full enrichment, demand signals consumption) is not summarized as Phase 1.
- [ ] **Only events from ARCHITECTURE_DEEP.md are used:** All event names and producer/consumer relationships match the Event Catalog and agent specs in ARCHITECTURE_DEEP.md; no events were invented.
- [ ] **Event ownership and direction are explicit:** For each agent, the doc states which events it consumes and which it emits, and for Failed/Alert events it states that only Orchestration consumes them.
- [ ] **Single job flow and guarantees:** The Single job posting flow section traces Ingestion → Normalization → Skills Extraction with correct event names and consumers, and states that ordering/delivery guarantees are not specified in the spec where they are not given.
