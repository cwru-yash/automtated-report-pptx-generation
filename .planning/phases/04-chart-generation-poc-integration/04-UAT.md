# Phase 4 UAT (Chart Generation & POC Integration)

## Test Scenarios

### Test 1: Wave Data Provider Abstraction
- **Criteria:** `app/data/provider.py` exists and correctly returns `MockWaveDataProvider` matching the `dcmp_deliverable_bundle_v1.py` schema.
- **Status:** ❌ **FAILED**
- **Notes:** `app/data/` directory does not exist. `app/main.py` is bypassing the provider and reading data differently.

### Test 2: Chart Generator (matplotlib)
- **Criteria:** `app/charts/generator.py` exists and can render Industry Curve, Horizontal Bars, S&R Ranking, and Grouped Bars to PNG bytes.
- **Status:** ❌ **FAILED**
- **Notes:** `app/charts/` directory does not exist. No chart generation code has been implemented.

### Test 3: End-to-End POC Job Endpoint
- **Criteria:** `POST /api/v1/jobs` accepts `{template_id, language, wave_id}`, runs bundle -> narrative -> charts -> HTML/PPT/PDF and returns artifact paths with provenance.
- **Status:** ⚠️ **PARTIAL**
- **Notes:** The endpoint exists and runs `bundle -> narrative -> HTML/PPT/PDF`, but it completely skips chart generation. Provenance IDs from `wave_data` are not being extracted.

## Diagnosis
Phase 4 was planned (plans `04-01`, `04-02`, `04-03` exist) but **never executed**. The current `POST /api/v1/jobs` implementation was built independently (likely as part of another task or spike) and does not include the Phase 4 chart generation logic.

## Recommended Action
Execute Phase 4 to build the missing data provider and chart generator, and integrate them into the existing `execute_report_job` flow.
