# Phase 1 Context: Project Foundation

## Decisions
- **Python Dependency Manager**: `pip` (using a standard `requirements.txt`).
- **Supabase Client**: Direct REST API calls via `httpx` (ensures fully async communication without wrapper library friction).
- **GCP Authentication (BigQuery)**: Service Account JSON key via `.env` (matches standard production approach).

## Phase Boundaries
- **In Scope**: Scaffold the FastAPI app, set up the directory structure (`app/bundle`, `app/narrative`, `app/renderers`, `app/templates`), configure environment variables, and establish connectivity tests for BigQuery and Supabase.
- **Out of Scope**: We are not building out the bundle assembly, narrative generation, or rendering logic yet—only the foundation and connectivity they rely on.

## Canonical Refs
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
