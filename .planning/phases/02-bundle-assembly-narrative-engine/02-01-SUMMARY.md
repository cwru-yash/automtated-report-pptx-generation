---
phase: 2
plan: 01
subsystem: bundle-assembly-narrative-engine
tags: [bundle, narrative, queue, guardrails]
requires: [Phase 1 Database]
provides: [AnalysisBundle Schema, BundleAssembler, PostgresJobQueue, Narrative Graph Engine]
affects: [app/queue, app/bundle, app/narrative]
tech-stack.added: [langgraph, litellm, sqlalchemy, asyncpg]
key-files.created:
  - app/core/database.py
  - app/queue/postgres_queue.py
  - app/bundle/schema.py
  - app/bundle/assembler.py
  - app/narrative/nodes.py
  - app/narrative/guardrails.py
  - app/narrative/graph.py
key-decisions:
  - Use SQLAlchemy and Postgres table for job queue.
  - Implement Generator-Evaluator pattern for the FactGuardrail.
  - StateGraph to parallelize narrative generation nodes.
requirements-completed: [REQ-01, REQ-02, REQ-08]
duration: 10 min
completed: 2026-04-27T18:33:00Z
---

# Phase 2 Plan 01: Bundle Assembly & Narrative Engine Summary

Implemented the core data pipeline for Phase 2. The `BundleAssembler` retrieves Decomposer data from BigQuery and formats it into the canonical `AnalysisBundle` Pydantic model. We established a parallel LangGraph `StateGraph` that triggers the writing of five narrative sections simultaneously, drastically improving overall latency. The outputs are piped directly into `FactGuardrail`, which detects hallucinations and loops errors back for regeneration if numbers deviate from the raw data.

## Authentication Gates
None

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## Self-Check: PASSED
Ready for next step.
