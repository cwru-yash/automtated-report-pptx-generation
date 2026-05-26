import logging
from typing import Any

from app.bundle.schema import AnalysisBundle
from app.config import settings

logger = logging.getLogger(__name__)


class BundleAssembler:
    def __init__(self):
        self.client = None

    async def build_bundle(
        self,
        wave_id: str,
        language: str,
        wave_data: dict[str, Any] | None = None,
    ) -> AnalysisBundle:
        """
        Assemble the small narrative bundle used by renderers.

        Prefer the already-loaded provider payload so one request has one
        source of truth. If that is unavailable, fall back to a read-only
        BigQuery aggregate query through ADC. Mock data is the final fallback.
        """
        metrics: dict[str, float] = {}
        analysis_results: dict[str, Any] = {}

        if wave_data:
            metrics = self._metrics_from_wave_data(wave_data)
            analysis_results = self._analysis_results_from_wave_data(wave_data)
            if metrics or analysis_results:
                return AnalysisBundle(
                    wave_id=wave_id,
                    language=language,
                    metrics=metrics,
                    analysis_results=analysis_results,
                )

        try:
            metrics = self._metrics_from_bigquery(wave_id)
        except Exception as exc:
            logger.error("Error fetching from BigQuery: %s", exc)

        if not metrics and not analysis_results:
            logger.info("Using mocked bundle data")
            metrics = {"nps": 45.5, "brand_awareness": 82.1, "cvc_score": 4.2}
            analysis_results = {
                "weak_links": ["Customer service response time", "Pricing perception"],
                "takeaways": ["Invest in CX training", "Launch promotional campaign"],
            }

        return AnalysisBundle(
            wave_id=wave_id,
            language=language,
            metrics=metrics,
            analysis_results=analysis_results,
        )

    def _metrics_from_wave_data(self, wave_data: dict[str, Any]) -> dict[str, float]:
        metrics: dict[str, float] = {}
        quality = wave_data.get("quality") or {}

        weighted_score = self._float_or_none(quality.get("weighted_score"))
        if weighted_score is not None:
            metrics["weighted_score"] = weighted_score
            metrics["cvc_score"] = weighted_score

        concept_points = self._float_or_none(quality.get("concept_points"))
        if concept_points is not None:
            metrics["concept_points"] = concept_points

        briefing_adherence = self._float_or_none(quality.get("briefing_adherence_pct"))
        if briefing_adherence is not None:
            metrics["briefing_adherence_pct"] = briefing_adherence

        gold_rows = (wave_data.get("gold") or {}).get("activity") or []
        satisfaction_values = [
            value
            for row in gold_rows
            if (value := self._float_or_none(row.get("satisfaction_index"))) is not None
        ]
        if satisfaction_values:
            metrics["average_satisfaction_index"] = round(
                sum(satisfaction_values) / len(satisfaction_values),
                2,
            )

        review_counts = [
            value
            for row in gold_rows
            if (value := self._float_or_none(row.get("review_count"))) is not None
        ]
        if review_counts:
            metrics["total_review_count"] = float(sum(review_counts))

        return metrics

    def _analysis_results_from_wave_data(self, wave_data: dict[str, Any]) -> dict[str, Any]:
        results: dict[str, Any] = {}
        weak_links: list[str] = []
        strong_links: list[str] = []

        for analysis in wave_data.get("analyses") or []:
            analysis_type = analysis.get("analysis_type")
            status = analysis.get("status")
            key = f"analysis_{analysis_type}"
            results[key] = {
                "name": analysis.get("analysis_name"),
                "status": status,
                "result": analysis.get("result") or {},
            }
            if analysis.get("commentary"):
                results[key]["commentary"] = analysis["commentary"]

            if status != "complete":
                continue

            links = (analysis.get("result") or {}).get("links") or []
            labels = [
                label
                for link in links
                if (label := self._link_label(link))
            ]
            if analysis_type in (3, 6):
                weak_links.extend(labels)
            elif analysis_type in (2, 5):
                strong_links.extend(labels)

        commentary = wave_data.get("commentary") or {}
        if commentary:
            results["commentary"] = commentary

        if weak_links:
            results["weak_links"] = weak_links
        if strong_links:
            results["strong_links"] = strong_links

        return results

    @staticmethod
    def _link_label(link: dict[str, Any]) -> str:
        return str(
            link.get("label")
            or link.get("activity_code")
            or link.get("macro_activity")
            or ""
        )

    def _metrics_from_bigquery(self, wave_id: str) -> dict[str, float]:
        from google.cloud import bigquery

        client = self._get_bq_client()
        table = f"`{settings.GCP_PROJECT}.{settings.BQ_GOLD_DATASET}.activity`"
        query = f"""
            SELECT
              AVG(satisfaction_index) AS average_satisfaction_index,
              SUM(review_count) AS total_review_count
            FROM {table}
            WHERE CAST(wave_id AS STRING) = @wave_id
              AND segment_dimension IS NULL
        """
        job = client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("wave_id", "STRING", wave_id),
                ],
            ),
        )
        rows = list(job.result())
        if not rows:
            return {}

        row = rows[0]
        metrics: dict[str, float] = {}
        avg_satisfaction = self._float_or_none(row.get("average_satisfaction_index"))
        if avg_satisfaction is not None:
            metrics["average_satisfaction_index"] = round(avg_satisfaction, 2)

        total_reviews = self._float_or_none(row.get("total_review_count"))
        if total_reviews is not None:
            metrics["total_review_count"] = total_reviews

        return metrics

    def _get_bq_client(self):
        if self.client is None:
            from app.core.bigquery import get_bq_client

            self.client = get_bq_client(project=settings.GCP_PROJECT)
        return self.client

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
