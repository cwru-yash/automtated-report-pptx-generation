# Phase 4 Context: Chart Generation & POC Integration

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Source:** discuss-phase conversation + Decomposer codebase research

<domain>
## Phase Boundary

Complete the v0.1 POC milestone. Build a chart generator that renders matplotlib PNGs from real `wave_data` structure, implement a swappable `WaveDataProvider` abstraction (mock now, Supabase in Phase 6), and wire everything into a single `POST /api/v1/jobs` endpoint that produces PPT + HTML + PDF from a `wave_id`.
</domain>

<decisions>
## Implementation Decisions

### WaveDataProvider Pattern
- Abstract base class `WaveDataProvider` with one method: `get_wave_data(wave_id: str) -> dict`
- `MockWaveDataProvider` returns a hardcoded fixture matching the exact `wave_data` schema from `dcmp_deliverable_bundle_v1.py`
- Auto-selection: if `SUPABASE_URL` is set in `.env` → use `SupabaseWaveDataProvider` (stubbed); else → `MockWaveDataProvider`
- Mock fixture wave_id = `"DEMO_WAVE_001"` — no user input needed
- When Phase 6 arrives, only `SupabaseWaveDataProvider` changes — zero changes to chart generator, renderers, or API

### wave_data Schema (from Decomposer codebase)
```
wave_data = {
    "schema_version": "1.0",
    "wave": { "id", "reference_period": {"start","end"}, "project": {"id","name"},
              "study": {"id","name","cvc_id"}, "country_iso_code", "industry": {"id","name"} },
    "quality": { "concept", "weighted_score", "briefing_adherence_pct" },
    "analyses": [
        { "analysis_type": int, "analysis_name": str, "status": "complete"|"skipped"|"failed",
          "result": { ... type-specific payload ... } }
    ],
    "gold": { "activity": [
        { "activity_code", "brand_id", "satisfaction_index": float, "review_count": int,
          "segment_dimension": null|str, "segment_value": null|str }
    ]},
    "metadata": { "gold_activity_version_id", "analysis_run_id", "deliverable_bundle_id" }
}
```

### Analysis Types → Charts (from ANALYSIS_NAMES + analyses_runner)
| Type | Name | Chart |
|------|------|-------|
| 1 | Industry Average Curve | Line chart — satisfaction_index per brand |
| 2 | Strong Links — Industry | Horizontal bar — top activity codes |
| 3 | Weak Links — Industry | Horizontal bar — bottom activity codes |
| 4 | S&R Index Ranking | Vertical bar — composite score (auto-skip if no NPS) |
| 5 | Strong Links — Brand | Horizontal bar — focus brand's strongest |
| 6 | Achilles Heel — Brand | Horizontal bar — focus brand's weakest |
| 7 | Best of Best | Grouped bar — top performers across brands |
| 8 | Breakdown | Grouped bar — segmented by segment_dimension |

### Chart Styling
- All charts: 300 DPI, brand palette (#1a2b4a primary, #e8b84b accent, #4a90d9 secondary)
- PPT-appropriate: 10" × 5.5" for wide placeholders, 5" × 5" for square
- Font: DejaVu Sans (matplotlib default, no network needed)
- Output: PNG bytes (in-memory, no temp files)

### Provenance
- `wave_data.metadata.gold_activity_version_id` and `analysis_run_id` are already in the payload — no separate fetch needed
- Embed both in every generated artifact's metadata dict

### API Design
- `POST /api/v1/jobs` accepts: `{ "template_id": str, "language": str, "wave_id": str | null }`
- `wave_id` is optional — if omitted, uses mock fixture's default wave_id
- Returns: `{ "job_id", "status": "processing", "wave_id", "artifacts": [] }`
- `GET /api/v1/jobs/{job_id}` returns status + artifact download info

### POC Scope (Phase 4)
- Synchronous job execution (no background worker yet — that's Phase 5)
- Artifacts written to local `output/` directory
- No GCS upload (Phase 8)
- Supabase write-back stubbed (Phase 6)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read before implementing:**
- `app/bundle/schema.py` — `AnalysisBundle` model
- `app/narrative/graph.py` — `run_narrative_engine()` and `NarrativeState`
- `app/renderers/__init__.py` — renderer exports
- `app/templates/registry.py` — `registry`, `init_registry`
- `app/config.py` — `Settings` (add `WAVE_DATA_PROVIDER`, `OUTPUT_DIR`)
- `decomposer-platform/pipelines/dags/dcmp_deliverable_bundle_v1.py` lines 643–683 — exact wave_data schema
- `decomposer-platform/pipelines/dags/dcmp_analyses_runner_v1.py` lines 67–76 — ANALYSIS_NAMES
</canonical_refs>

<deferred>
## Deferred to Later Phases
- Real Supabase integration (Phase 6)
- Background job workers / async processing (Phase 5)
- GCS artifact upload (Phase 8)
- Chart caching (Phase 8)
- Per-brand NPS data for Analysis 4 (Phase 6 — requires company NPS rows)
</deferred>
