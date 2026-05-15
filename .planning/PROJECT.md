# Automated Report & PPT Generation Platform

## What This Is

A multi-format deliverable generation platform that consumes validated analytical data from the Decomposer Platform (BigQuery Gold layer + Analysis Results) and produces branded PowerPoint presentations, HTML reports, and PDF documents. Designed as a downstream consumer of the Decomposer Pipeline — it narrates and renders, never recomputes. Serves the internal analytics team and their clients across Brazil, North America, Hispanic markets, China, and South Korea.

## Core Value

Given a completed Wave's analysis data, produce a publication-ready, branded PPT deck and report in the client's language — with every number traceable back to the source data and no LLM-invented metrics.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] REQ-01: Bundle Assembler reads Gold Activity + Analysis Results from Decomposer's BigQuery and assembles a canonical Analysis Bundle JSON
- [ ] REQ-02: LangGraph-based narrative engine generates section text (executive summary, methodology, brand health, weak links, takeaways) in the requested language
- [ ] REQ-03: PPT renderer fills named placeholders in `.pptx` master templates with narrated content blocks and chart images
- [ ] REQ-04: HTML/PDF renderer produces styled reports from the same content blocks using Jinja2 + WeasyPrint
- [ ] REQ-05: Template registry supports multiple `.pptx` and HTML templates with placeholder schema definitions
- [ ] REQ-06: Multi-language support — LLM generates text in requested language; static labels from locale JSON files (pt-BR, en-US at POC; es-MX, ko-KR, zh-CN at MVP)
- [ ] REQ-07: Chart generator reads B1's `wave_data` JSON and renders fresh charts (matplotlib/plotly) sized for PPT placeholders with client-specific branding
- [ ] REQ-08: Fact guardrail — every narrative block must cite approved bundle metrics; uncitable text is rejected
- [ ] REQ-09: Template guardrail — pre-render validation checks placeholder overflow, missing assets, wrong-brand logos, broken footnotes
- [ ] REQ-10: Job API — POST /api/v1/jobs accepts `wave_id`, `template_id`, `language` and returns job status with artifact download URLs
- [ ] REQ-11: Webhook integration — receives POST from Decomposer's Wave Orchestrator when a deliverable bundle completes
- [ ] REQ-12: Write-back — inserts new `deliverable_bundles` rows in Decomposer's Supabase with GCS paths to PPT/PDF artifacts
- [ ] REQ-13: Provenance tracking — every generated artifact embeds `gold_activity_version_id`, `analysis_run_id`, `quality_record_id` for full lineage
- [ ] REQ-14: Retry logic — failed jobs retry up to 3x with exponential backoff; partial failures are recoverable

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- **R analytics layer** — Decomposer's Python/Airflow pipeline is the analytics engine; this system consumes its output, not recomputes it
- **Dashboard Materializer** — Decomposer already has admin dashboard pages reading Supabase mirrors of Gold data
- **Temporal orchestration** — Deferred to Final Product stage; POC/MVP use asyncio + Postgres job queue
- **RAG indexing / chatbot** — Deferred to Final Product stage; build after PPT/report quality is validated
- **Client self-service portal** — Deferred; internal-only usage for POC/MVP
- **Survey / Union / Pain Points pipelines** — These are Decomposer Pipeline features, not Report Platform features

## Context

### The Decomposer Platform (Reference System)

The Report Platform integrates with an existing operational platform (cloned at `decomposer-platform/`) that handles the full data pipeline: scraping consumer reviews → scoring with LLMs → computing quality metrics → running 8 analysis types → generating basic HTML/Excel/JSON deliverables.

**Integration contract — 4 read points, 1 write-back:**

| Direction | Source/Target | Data |
|-----------|---------------|------|
| READ | `decomposer_gold.activity` (BigQuery) | Satisfaction indices per (brand × activity × segment) |
| READ | `decomposer_gold.analysis_results` (BigQuery) | Analyses 1–8 output (rankings, comparisons, breakdowns) |
| READ | Supabase `quality_records` | Quality concept (OURO/PRATA/BRONZE) + briefing adherence |
| READ | Supabase `waves` + `projects` + `studies` + `briefings` | Wave metadata, brand hierarchy, period, client context |
| WRITE | Supabase `deliverable_bundles` | New bundle row with GCS paths to PPT/PDF artifacts |

The Decomposer Platform's existing `dcmp_deliverable_bundle_v1` DAG continues producing HTML + Excel + JSON. This system produces **additional** artifacts (PPT, enhanced PDF) from the same source data.

### Architecture Principles

1. **Compute once in Decomposer, narrate many times in AI** — The LLM never invents numbers
2. **Canonical Analysis Bundle** — Single JSON contract is the system of record for all renderers
3. **Same truth, different wrappers** — PPT gets 20-word headlines; reports get 180-word sections; both cite the same metrics
4. **Monolith first, split at bottlenecks** — One FastAPI service scales to 50 reports/batch; Temporal comes at 500+

### Scaling Characteristics

- LLM API calls dominate job time (~30s of ~50s per job)
- Single FastAPI instance with 5 async workers handles 50 reports/batch in ~8 minutes
- Horizontal scaling = add instances behind a load balancer (same code, shared Postgres)
- Temporal becomes justified at 500+ reports/batch or cross-service human-in-loop workflows

## Constraints

- **Integration**: Must not modify Decomposer Platform code — read-only consumer of its data
- **Auth**: API key auth pattern mirrors Decomposer's B2 design (`sk_<env>_<prefix>_<random>`)
- **Storage**: Use GCS (same bucket strategy as Decomposer) for generated artifacts
- **AI Provider**: Anthropic (Claude) for narrative generation — consistent with Decomposer's LLM usage
- **No Data Duplication**: Never copy Gold data into a local database — always read from BigQuery at assembly time
- **Fact Integrity**: LLM-generated text must cite bundle metrics; uncitable content is rejected by guardrails

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Consume Decomposer Gold, don't recompute in R | Avoids maintaining two analytics engines; inherits quality gates + audit trails | — Pending |
| FastAPI monolith for POC/MVP | 9 services is over-engineering for 30-50 reports/batch; split only at bottlenecks | — Pending |
| Multi-template registry from POC | User needs multiple deck layouts; designers control PowerPoint, code fills placeholders | — Pending |
| Language as job parameter, not system config | Clients span 5+ markets; locale files + LLM prompt parameterization | — Pending |
| Hybrid chart strategy | Read B1's wave_data JSON (data), render own charts (styling) — avoids tight coupling to B1's HTML while reusing its structured data | — Pending |
| No Temporal until Final Product | asyncio → Dramatiq → Temporal progression matches volume growth without premature complexity | — Pending |
| Dashboard Materializer not needed | Decomposer already has admin dashboard pages reading Supabase Gold mirrors | ✓ Good |

---
*Last updated: 2026-04-26 after Phase 1*
