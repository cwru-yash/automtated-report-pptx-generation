# Roadmap: Automated Report & PPT Generation Platform

## Overview

Build a multi-format deliverable generation platform in three stages: POC validates that Decomposer Gold → LangGraph narrative → PPT/HTML produces acceptable quality; MVP adds production reliability with job queuing, webhook integration, and write-back to Decomposer; Final Product adds Temporal orchestration, RAG indexing, chatbot, and batch scale. Each stage is additive — no rewrites between stages.

## Milestones

- 🚧 **v0.1 POC** — Phases 1-4 (in progress)
- 📋 **v1.0 MVP** — Phases 5-8 (planned)
- 📋 **v2.0 Final Product** — Phases 9-12 (planned)

## Phases

- [x] **Phase 1: Project Foundation** - FastAPI app scaffold, config, project structure, Decomposer data connectivity
- [x] **Phase 2: Bundle Assembly & Narrative Engine** - Bundle Assembler reads BigQuery Gold + LangGraph narrative compiler with fact guardrails
- [x] **Phase 3: Renderers & Template Registry** - PPT renderer (python-pptx), HTML/PDF renderer (Jinja2 + WeasyPrint), multi-template support
- [x] **Phase 4: Chart Generation & POC Integration** - matplotlib chart generator consuming B1 wave_data, end-to-end POC validation
- [ ] **Phase 5: Job Queue & API** - Postgres-backed job queue, status tracking, retry logic, structured logging
- [ ] **Phase 6: Decomposer Integration** - Webhook receiver, write-back to deliverable_bundles, API key auth
- [ ] **Phase 7: Multi-Language & Template Expansion** - es-MX/ko-KR/zh-CN locale files, template upload API, template guardrails
- [ ] **Phase 8: MVP Hardening** - Data quality guardrail, regression guardrail, GCS storage, observability
- [ ] **Phase 9: Temporal Orchestration** - Temporal workflow engine, worker pools, batch fan-out
- [ ] **Phase 10: RAG & Intelligence** - Index final artifacts into Qdrant, chatbot API (Analyst Copilot mode)
- [ ] **Phase 11: Advanced Chatbot & Portal** - 4 chatbot modes, internal ops dashboard, human approval gate
- [ ] **Phase 12: Platform Features** - Brand/style packs, template A/B testing, cross-report comparison, batch scheduling

## Phase Details

### Phase 1: Project Foundation
**Goal**: FastAPI application scaffold with working connectivity to Decomposer's BigQuery and Supabase
**Depends on**: Nothing (first phase)
**Requirements**: REQ-01 (partial — connectivity only)
**Success Criteria** (what must be TRUE):
  1. FastAPI app starts and serves `/health` endpoint
  2. BigQuery client successfully queries `decomposer_gold.activity` and returns rows
  3. Supabase client successfully reads wave metadata for a known `wave_id`
  4. Project structure matches the defined layout (bundle/, narrative/, renderers/, templates/)
  5. Environment configuration loads from `.env` with clear documentation
**Plans**: TBD

### Phase 2: Bundle Assembly & Narrative Engine
**Goal**: Bundle Assembler reads Decomposer data and produces a canonical Analysis Bundle JSON; LangGraph graph generates narrative content blocks with fact checking
**Depends on**: Phase 1
**Requirements**: REQ-01, REQ-02, REQ-08
**Success Criteria** (what must be TRUE):
  1. Bundle Assembler produces a valid Analysis Bundle JSON from a real Wave's BigQuery data
  2. LangGraph graph generates narrative text for all 5 section types (executive summary, methodology, brand health, weak links, takeaways)
  3. Fact guardrail rejects narrative blocks that reference metrics not in the bundle
  4. Narrative generation works in both pt-BR and en-US
  5. Bundle JSON schema is validated by Pydantic models
**Plans**: TBD

### Phase 3: Renderers & Template Registry
**Goal**: PPT and HTML/PDF renderers produce publication-ready output from content blocks; template registry supports multiple master decks
**Depends on**: Phase 2
**Requirements**: REQ-03, REQ-04, REQ-05, REQ-06 (partial — pt-BR + en-US)
**Success Criteria** (what must be TRUE):
  1. PPT renderer fills named placeholders in a `.pptx` template with text blocks and chart images
  2. HTML renderer produces a styled report using Jinja2 templates
  3. PDF renderer converts HTML to PDF via WeasyPrint
  4. Template registry loads multiple templates and validates placeholder schemas
  5. Output files open correctly in PowerPoint / browser / PDF viewer
**Plans**: TBD

### Phase 4: Chart Generation & POC Integration
**Goal**: Charts render fresh from B1's wave_data with PPT-appropriate styling; end-to-end pipeline works from wave_id to finished artifacts
**Depends on**: Phase 3
**Requirements**: REQ-07, REQ-13 (partial — provenance in bundle)
**Success Criteria** (what must be TRUE):
  1. Chart generator reads B1's `wave_data` JSON from GCS and produces high-DPI PNGs
  2. Charts are correctly sized for PPT slide placeholders
  3. End-to-end: `POST /api/v1/jobs` with a `wave_id` produces a complete PPT + HTML + PDF
  4. Generated artifacts embed provenance metadata (gold_version_id, analysis_run_id)
  5. Stakeholder review of output quality passes acceptance threshold
**Plans**: TBD

### Phase 5: Job Queue & API
**Goal**: Production-ready job management with queuing, status tracking, retries, and structured logging
**Depends on**: Phase 4
**Requirements**: REQ-10, REQ-14
**Success Criteria** (what must be TRUE):
  1. Jobs persist in Postgres with status transitions (queued → assembling → narrating → rendering → complete/failed)
  2. Failed jobs retry up to 3x with exponential backoff
  3. GET /api/v1/jobs/:id returns current status + artifact download URLs on completion
  4. Structured JSON logging captures job lifecycle events
  5. Concurrent job processing works without race conditions
**Plans**: TBD

### Phase 6: Decomposer Integration
**Goal**: Bidirectional integration with Decomposer — receive webhooks, write back artifact metadata, share auth
**Depends on**: Phase 5
**Requirements**: REQ-11, REQ-12
**Success Criteria** (what must be TRUE):
  1. Webhook endpoint receives POST from Decomposer's Wave Orchestrator and triggers a job
  2. Completed jobs write back a new `deliverable_bundles` row to Decomposer's Supabase
  3. API key auth validates against the same pattern as Decomposer's B2 (`sk_<env>_<prefix>_<random>`)
  4. Write-back includes correct GCS paths, bundle_type, and lineage FKs
**Plans**: TBD

### Phase 7: Multi-Language & Template Expansion
**Goal**: Full multi-language support and template management API
**Depends on**: Phase 6
**Requirements**: REQ-06 (full), REQ-09
**Success Criteria** (what must be TRUE):
  1. Locale files exist for es-MX, ko-KR, zh-CN with all section titles and labels
  2. LLM generates narrative text correctly in all 5 supported languages
  3. Template upload API accepts new `.pptx` files with placeholder schema validation
  4. Template guardrail catches placeholder overflow, missing assets, and wrong-brand logos pre-render
**Plans**: TBD

### Phase 8: MVP Hardening
**Goal**: Production-grade guardrails, storage, and observability
**Depends on**: Phase 7
**Requirements**: REQ-08 (hardened), REQ-09 (hardened), REQ-13 (full)
**Success Criteria** (what must be TRUE):
  1. Data quality guardrail blocks generation when source analyses are missing, empty, or quality = REPROVADO
  2. Regression guardrail flags >20% metric shift vs. prior Wave without corresponding data change
  3. All artifacts stored in GCS with signed download URLs
  4. Lineage guardrail embeds full provenance chain in every artifact
  5. Observability: job latency, LLM cost, error rate metrics available
**Plans**: TBD

### Phase 9: Temporal Orchestration
**Goal**: Replace asyncio/Dramatiq with Temporal for durable, resumable workflows at batch scale
**Depends on**: Phase 8
**Requirements**: (Scale requirement — no new functional requirements)
**Success Criteria** (what must be TRUE):
  1. Temporal workflow engine processes batch jobs (50+ reports)
  2. Failed individual reports are retryable without re-running the entire batch
  3. Worker pools can be scaled independently
  4. Job state survives process crashes and resumes automatically
**Plans**: TBD

### Phase 10: RAG & Intelligence
**Goal**: Index final artifacts into a vector store; expose chatbot API for analyst queries
**Depends on**: Phase 9
**Requirements**: (New — not in POC/MVP scope)
**Success Criteria** (what must be TRUE):
  1. Final report text, slide text, and chart metadata indexed in Qdrant
  2. Chatbot API answers analyst questions with citations to specific report sections
  3. Tenant isolation enforced — no cross-client data retrieval
  4. Analyst Copilot mode works: "Explain this weak link for Ceragem"
**Plans**: TBD

### Phase 11: Advanced Chatbot & Portal
**Goal**: Full chatbot surface with 4 modes + internal ops dashboard
**Depends on**: Phase 10
**Requirements**: (New — not in POC/MVP scope)
**Success Criteria** (what must be TRUE):
  1. 4 chatbot modes operational: Analyst Copilot, Client Q&A, Ops Agent, Template Agent
  2. Ops dashboard shows job queue, failures, retries, artifact status, model cost
  3. Human-in-the-loop approval gate optionally blocks publish until reviewed
**Plans**: TBD

### Phase 12: Platform Features
**Goal**: Self-serve template management, brand packs, comparative analytics
**Depends on**: Phase 11
**Requirements**: (New — not in POC/MVP scope)
**Success Criteria** (what must be TRUE):
  1. Brand/style packs customize chart colors, fonts, and PPT themes per client
  2. Template A/B testing tracks which template variant gets better stakeholder feedback
  3. Cross-report comparison: overlay two Waves' metrics for trend analysis
  4. Batch scheduling: configure nightly/weekly report generation per study
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 (POC) → 5 → 6 → 7 → 8 (MVP) → 9 → 10 → 11 → 12 (Final)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Project Foundation | v0.1 POC | Complete | Done | 2026-04-26 |
| 2. Bundle Assembly & Narrative Engine | v0.1 POC | Complete | Done | 2026-05-18 |
| 3. Renderers & Template Registry | v0.1 POC | Complete | Done | 2026-05-18 |
| 4. Chart Generation & POC Integration | v0.1 POC | Complete | Done | 2026-05-18 |
| 5. Job Queue & API | v1.0 MVP | 0/TBD | Not started | - |
| 6. Decomposer Integration | v1.0 MVP | 0/TBD | Not started | - |
| 7. Multi-Language & Template Expansion | v1.0 MVP | 0/TBD | Not started | - |
| 8. MVP Hardening | v1.0 MVP | 0/TBD | Not started | - |
| 9. Temporal Orchestration | v2.0 Final | 0/TBD | Not started | - |
| 10. RAG & Intelligence | v2.0 Final | 0/TBD | Not started | - |
| 11. Advanced Chatbot & Portal | v2.0 Final | 0/TBD | Not started | - |
| 12. Platform Features | v2.0 Final | 0/TBD | Not started | - |
