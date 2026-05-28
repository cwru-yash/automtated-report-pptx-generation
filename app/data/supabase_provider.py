"""
SupabaseWaveDataProvider
========================
Primary strategy  : Fetch pre-computed JSON from Google Cloud Storage
                    (produced by dcmp_deliverable_bundle_v1 Airflow DAG).
Fallback strategy : Re-execute all raw Supabase REST + BigQuery queries
                    inline when no completed bundle / GCS object is found.

This dual-path design keeps reports fast when Airflow has already run,
but stays resilient when a bundle hasn't been generated yet.

It also serves as the foundation for the future standalone data provider
capable of connecting to any database, warehouse, or flat-file source.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from app.data.provider import WaveDataProvider

logger = logging.getLogger(__name__)

ANALYSIS_NAMES = {
    1: "Industry Average Curve",
    2: "Strong Links — Industry",
    3: "Weak Links — Industry",
    4: "S&R Index Ranking",
    5: "Strong Links — Brand",
    6: "Achilles Heel — Brand",
    7: "Best of Best",
    8: "Breakdown",
}


class SupabaseWaveDataProvider(WaveDataProvider):
    """
    Implements WaveDataProvider against the live Decomposer Platform data.

    Requires:
        config.SUPABASE_URL          — Supabase project URL
        config.SUPABASE_SECRET_KEY   — service-role key (bypasses RLS)
        config.GCP_PROJECT           — GCP project ID
        config.BQ_GOLD_DATASET       — BigQuery gold dataset name
        config.GCS_DELIVERABLE_BUCKET — GCS bucket for pre-computed bundles
        config.GCS_DELIVERABLE_PREFIX — GCS prefix inside the bucket
    """

    def __init__(self, config):
        self.config = config
        self._supabase_url = config.SUPABASE_URL.rstrip("/")
        self._supabase_key = config.SUPABASE_SECRET_KEY or config.SUPABASE_KEY
        self._gcp_project = config.GCP_PROJECT
        self._bq_dataset = config.BQ_GOLD_DATASET
        self._gcs_bucket = config.GCS_DELIVERABLE_BUCKET
        self._gcs_prefix = config.GCS_DELIVERABLE_PREFIX

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_latest_wave_id(self) -> str:
        """
        Return the wave_id of the most recently completed, fully-analysed wave.
        Prefers waves where analysis_types_completed has the most entries (real waves),
        falling back to the most recent completed run if none have multi-type results.
        """
        rows = self._supabase_get(
            "/rest/v1/analysis_runs"
            "?status=in.(complete,partial_complete)"
            "&select=wave_id,finished_at,analysis_types_completed"
            "&order=finished_at.desc"
            "&limit=20"
        )
        if not rows:
            raise RuntimeError(
                "No completed analysis_runs found in Supabase. "
                "Run dcmp_analyses_runner_v1 first."
            )
        # Prefer runs that actually completed multiple analyses (real production waves)
        real_runs = [r for r in rows if len(r.get("analysis_types_completed") or []) > 0]
        best = real_runs[0] if real_runs else rows[0]
        wave_id = best["wave_id"]
        logger.info(
            "get_latest_wave_id → %s (analyses_completed=%s)",
            wave_id,
            best.get("analysis_types_completed"),
        )
        return wave_id

    def get_wave_data(self, wave_id: str) -> dict:
        """
        Fetch the full wave data dictionary for the given wave_id.

        Strategy:
          1. Look for a completed deliverable_bundle with a gcs_json_path.
          2. If found, download the pre-computed JSON from GCS.
          3. If not found (or GCS fetch fails), fall back to live queries.
        """
        logger.info("[get_wave_data] wave_id=%s — trying Option A (GCS)…", wave_id)

        bundle = self._find_completed_bundle(wave_id)
        if bundle and bundle.get("gcs_json_path"):
            try:
                data = self._fetch_gcs_json(bundle["gcs_json_path"])
                logger.info(
                    "[get_wave_data] Option A success — bundle=%s", bundle["id"]
                )
                return data
            except Exception as exc:
                logger.warning(
                    "[get_wave_data] Option A failed (%s); falling back to live queries.", exc
                )

        logger.info("[get_wave_data] wave_id=%s — falling back to Option B (live DB)…", wave_id)
        return self._fetch_from_live_db(wave_id)

    # ------------------------------------------------------------------
    # Option A: GCS pre-computed JSON
    # ------------------------------------------------------------------

    def _find_completed_bundle(self, wave_id: str) -> dict | None:
        """Find the most recent completed deliverable_bundle for this wave."""
        path = (
            "/rest/v1/deliverable_bundles"
            f"?wave_id=eq.{urllib.parse.quote(wave_id)}"
            "&status=eq.complete"
            "&select=id,wave_id,gcs_json_path,created_at"
            "&order=created_at.desc"
            "&limit=1"
        )
        rows = self._supabase_get(path)
        return rows[0] if rows else None

    def _fetch_gcs_json(self, gcs_uri: str) -> dict:
        """Download and parse JSON from a GCS URI like gs://bucket/path/data.json."""
        from google.cloud import storage

        # Parse gs://bucket/path
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Expected gs:// URI, got: {gcs_uri}")
        without_scheme = gcs_uri[5:]
        bucket_name, _, object_path = without_scheme.partition("/")

        logger.info("[GCS] downloading %s", gcs_uri)
        client = storage.Client(project=self._gcp_project)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_path)
        raw = blob.download_as_text(encoding="utf-8")
        data = json.loads(raw)
        logger.info("[GCS] downloaded %d bytes", len(raw))
        return data

    # ------------------------------------------------------------------
    # Option B: Live Supabase + BigQuery queries
    # ------------------------------------------------------------------

    def _fetch_from_live_db(self, wave_id: str) -> dict:
        """
        Re-construct the full wave_data dictionary from live sources.
        Mirrors the logic in dcmp_deliverable_bundle_v1._load_inputs().
        """
        logger.info("[Option B] Building wave_data from live DB for %s", wave_id)

        # --- Supabase metadata ---
        wave = self._select_wave(wave_id)
        if not wave:
            raise RuntimeError(f"Wave {wave_id} not found in Supabase")

        project = self._select_project(wave["project_id"]) or {}
        study = self._select_study(project["study_id"]) if project.get("study_id") else None
        quality_record = self._select_final_wave_quality_record(wave_id) or {}

        # --- Analysis versions (metadata from Supabase) ---
        analysis_run = self._select_latest_analysis_run(wave_id)
        analysis_run_id = analysis_run["id"] if analysis_run else None
        av_rows = self._select_final_analysis_versions(wave_id)
        if analysis_run_id:
            av_rows = [a for a in av_rows if a.get("analysis_run_id") == analysis_run_id]

        # --- BigQuery: analysis results & gold activity ---
        bq_by_type: dict[int, dict] = {}
        gold_rows: list[dict] = []

        if analysis_run_id:
            bq_by_type = self._load_analysis_results(analysis_run_id)

        gold_version = self._select_final_gold(wave_id)
        if gold_version:
            gold_rows = self._load_gold_rows(gold_version["id"])

        # --- Assemble analyses list ---
        analyses: list[dict[str, Any]] = []
        for av in av_rows:
            atype = int(av.get("analysis_type", 0))
            status = av.get("status")
            analysis: dict[str, Any] = {
                "analysis_type": atype,
                "analysis_name": ANALYSIS_NAMES.get(atype, f"Analysis {atype}"),
                "status": status,
                "analysis_version_id": av.get("id"),
            }
            if status == "complete":
                bq_row = bq_by_type.get(atype) or {}
                analysis["result"] = bq_row.get("result") or {}
                analysis["parameters_used"] = bq_row.get("parameters_used") or {}
            elif status == "skipped":
                analysis["skip_reason"] = av.get("skip_reason")
                if atype == 4 and av.get("skip_reason") == "NO_NPS":
                    analysis["skip_message"] = (
                        "S&R Index requires NPS data. Survey module not active for this Wave."
                    )
                else:
                    analysis["skip_message"] = av.get("skip_reason") or "skipped"
            elif status == "failed":
                analysis["error_message"] = av.get("error_message") or "unknown error"
            analyses.append(analysis)
        analyses.sort(key=lambda x: x["analysis_type"])

        # --- Assemble final wave_data (matches mock_provider schema) ---
        wave_data: dict[str, Any] = {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "assets": {"brand_logo_data_url": ""},
            "wave": {
                "id": wave["id"],
                "code": wave.get("code"),
                "reference_period": {
                    "start": wave.get("reference_start_date"),
                    "end": wave.get("reference_end_date"),
                },
                "project": {
                    "id": project.get("id"),
                    "name": project.get("name"),
                },
                "study": {
                    "id": study.get("id") if study else None,
                    "name": study.get("name") if study else None,
                    "cvc_id": study.get("cvc_id") if study else None,
                },
                "country_iso_code": None,   # stored on briefing, not wave
                "industry": {"id": None, "name": None},
                "brand_hierarchy": {},
            },
            "quality": {
                "concept": quality_record.get("concept"),
                "concept_points": quality_record.get("concept_points"),
                "weighted_score": quality_record.get("weighted_score"),
                "briefing_adherence_pct": quality_record.get("briefing_adherence_pct"),
            },
            "analyses": analyses,
            "gold": {"activity": gold_rows},
            "metadata": {
                "deliverable_bundle_id": None,
                "commentary_agent_version_id": None,
                "gold_activity_version_id": gold_version["id"] if gold_version else None,
                "quality_record_id": quality_record.get("id"),
                "analysis_run_id": analysis_run_id,
            },
        }

        logger.info(
            "[Option B] Built wave_data: %d analyses, %d gold rows",
            len(analyses),
            len(gold_rows),
        )
        return wave_data

    # ------------------------------------------------------------------
    # Supabase helpers
    # ------------------------------------------------------------------

    def _supabase_get(self, path: str) -> list[dict]:
        url = f"{self._supabase_url}{path}"
        headers = {
            "apikey": self._supabase_key,
            "Authorization": f"Bearer {self._supabase_key}",
            "Accept": "application/json",
        }
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read()) or []
        except urllib.error.HTTPError as exc:
            logger.error("Supabase GET %s → HTTP %s: %s", path, exc.code, exc.read().decode())
            raise

    def _select_wave(self, wave_id: str) -> dict | None:
        # waves doesn't have country_iso_code or industry_id directly;
        # those come from the briefing. Fetch what's available on waves.
        rows = self._supabase_get(
            f"/rest/v1/waves?id=eq.{urllib.parse.quote(wave_id)}"
            "&select=id,project_id,reference_start_date,reference_end_date,"
            "current_briefing_id,current_study_dictionary_version_id,code"
        )
        return rows[0] if rows else None

    def _select_project(self, project_id: str) -> dict | None:
        rows = self._supabase_get(
            f"/rest/v1/projects?id=eq.{urllib.parse.quote(project_id)}"
            "&select=id,name,study_id"
        )
        return rows[0] if rows else None

    def _select_study(self, study_id: str) -> dict | None:
        rows = self._supabase_get(
            f"/rest/v1/studies?id=eq.{urllib.parse.quote(study_id)}"
            "&select=id,name,cvc_id"
        )
        return rows[0] if rows else None

    def _select_industry(self, industry_id: str | None) -> dict | None:
        if not industry_id:
            return None
        rows = self._supabase_get(
            f"/rest/v1/industries?id=eq.{urllib.parse.quote(industry_id)}"
            "&select=id,name"
        )
        return rows[0] if rows else None

    def _select_final_gold(self, wave_id: str) -> dict | None:
        rows = self._supabase_get(
            "/rest/v1/gold_activity_versions"
            f"?wave_id=eq.{urllib.parse.quote(wave_id)}"
            "&is_final=eq.true"
            "&select=id,source_type"
            "&limit=1"
        )
        return rows[0] if rows else None

    def _select_final_wave_quality_record(self, wave_id: str) -> dict | None:
        rows = self._supabase_get(
            "/rest/v1/quality_records"
            f"?wave_id=eq.{urllib.parse.quote(wave_id)}"
            "&evaluation_moment=eq.wave"
            "&is_final=eq.true"
            "&select=id,concept,concept_points,weighted_score,briefing_adherence_pct"
            "&limit=1"
        )
        return rows[0] if rows else None

    def _select_latest_analysis_run(self, wave_id: str) -> dict | None:
        rows = self._supabase_get(
            "/rest/v1/analysis_runs"
            f"?wave_id=eq.{urllib.parse.quote(wave_id)}"
            "&status=in.(complete,partial_complete)"
            "&select=id,status,finished_at,gold_activity_version_id"
            "&order=finished_at.desc"
            "&limit=1"
        )
        return rows[0] if rows else None

    def _select_final_analysis_versions(self, wave_id: str) -> list[dict]:
        return self._supabase_get(
            "/rest/v1/analysis_versions"
            f"?wave_id=eq.{urllib.parse.quote(wave_id)}"
            "&is_final=eq.true"
            "&select=id,analysis_run_id,analysis_type,status,skip_reason,error_message"
        )

    # ------------------------------------------------------------------
    # BigQuery helpers
    # ------------------------------------------------------------------

    def _bq_client(self):
        from google.cloud import bigquery
        return bigquery.Client(project=self._gcp_project)

    def _load_gold_rows(self, gold_activity_version_id: str) -> list[dict]:
        from google.cloud import bigquery

        client = self._bq_client()
        sql = f"""
            SELECT wave_id, activity_code, brand_id, satisfaction_index,
                   review_count, source_type, segment_dimension, segment_value
            FROM `{self._gcp_project}.{self._bq_dataset}.activity`
            WHERE gold_activity_version_id = @v
              AND segment_dimension IS NULL
        """
        job = client.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("v", "STRING", gold_activity_version_id)
                ]
            ),
        )
        out = []
        for row in job.result():
            out.append({
                "wave_id": str(row["wave_id"]) if row.get("wave_id") else None,
                "activity_code": row.get("activity_code"),
                "brand_id": row.get("brand_id"),
                "satisfaction_index": float(row["satisfaction_index"]) if row.get("satisfaction_index") is not None else None,
                "review_count": int(row["review_count"]) if row.get("review_count") else 0,
                "source_type": row.get("source_type"),
                "segment_dimension": row.get("segment_dimension"),
                "segment_value": row.get("segment_value"),
            })
        logger.info("[BQ] loaded %d gold activity rows", len(out))
        return out

    def _load_analysis_results(self, analysis_run_id: str) -> dict[int, dict]:
        from google.cloud import bigquery

        client = self._bq_client()
        sql = f"""
            SELECT analysis_type, analysis_version_id, result, parameters_used, computed_at
            FROM `{self._gcp_project}.{self._bq_dataset}.analysis_results`
            WHERE analysis_run_id = @r
        """
        job = client.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("r", "STRING", analysis_run_id)
                ]
            ),
        )
        out: dict[int, dict] = {}
        for row in job.result():
            atype = int(row["analysis_type"]) if row.get("analysis_type") is not None else None
            if atype is None:
                continue
            result_field = row.get("result")
            if isinstance(result_field, str):
                try:
                    result_field = json.loads(result_field)
                except json.JSONDecodeError:
                    pass
            params_used = row.get("parameters_used")
            if isinstance(params_used, str):
                try:
                    params_used = json.loads(params_used)
                except json.JSONDecodeError:
                    pass
            out[atype] = {
                "analysis_version_id": str(row["analysis_version_id"]),
                "result": result_field,
                "parameters_used": params_used,
                "computed_at": row.get("computed_at"),
            }
        logger.info("[BQ] loaded analysis results for %d analysis types", len(out))
        return out
