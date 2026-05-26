# Real Data Provider Implementation

We are ready to swap out the `MockWaveDataProvider` and connect the Automated Report Platform to your live production data.

## Option A vs Option B Analysis

As requested, here is an investigation into where **Option A** (fetching pre-computed JSON from Google Cloud Storage) could fail us, especially regarding the vision of a standalone reporting platform:

1. **Stale Data & DAG Dependency**: Option A relies entirely on the Airflow DAG (`dcmp_deliverable_bundle_v1`) finishing successfully. If the DAG fails, hangs, or hasn't run yet, the reporting app cannot generate a report—even if the raw data in BigQuery/Supabase is completely ready.
2. **Zero Dynamic Interactivity**: A static JSON file cannot be interactively filtered. If you later want users to be able to say *"Show me this report but only for the 18-24 age group"*, Option A fails. Connecting directly to the database allows you to push these dynamic queries down to BigQuery.
3. **Coupled Architecture**: Option A tightly couples this app to the exact output schema of `decomposer-platform`'s Airflow pipelines. This breaks the vision of having a standalone, data-source-agnostic reporting platform that can hook into any data warehouse.

**Decision**: Because you want this to eventually be a standalone service capable of connecting to diverse databases and warehouses, we will proceed with **Option B**. We will implement the raw queries directly in the Python app. This guarantees real-time data access and sets the architectural foundation for a standalone platform.

## Proposed Changes

### Data Provider
#### [MODIFY] [app/data/supabase_provider.py](file:///Users/yashm/Documents/automated-report-ppt-generation/app/data/supabase_provider.py)
- **`__init__`**: Initialize `httpx.Client` (for Supabase REST API) and `bigquery.Client()` (for BigQuery).
- **`get_latest_wave_id()`**: Query Supabase for the most recent `wave_id` that has a completed `analysis_runs` record.
- **`get_wave_data()`**: Execute the data aggregation logic dynamically:
  1. Fetch Wave, Project, Study, and Industry metadata via Supabase REST.
  2. Fetch `quality_records` via Supabase REST.
  3. Fetch `analysis_results` from the `decomposer_gold` BigQuery dataset.
  4. Fetch `activity` (gold rows) from the `decomposer_gold` BigQuery dataset.
  5. Assemble the results into the exact dictionary schema required by the PPTX generation engine.

## Verification Plan

### Automated Tests
- Run the python test script to verify that `SupabaseWaveDataProvider.get_wave_data(latest_wave_id)` successfully returns a fully hydrated dictionary matching the schema of `MOCK_WAVE_DATA`.

### Manual Verification
- We will boot up the FastAPI server, hit the data provider endpoint, and verify it correctly returns live production records without errors.
