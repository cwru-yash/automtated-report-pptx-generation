import logging
import os

from app.bundle.schema import AnalysisBundle
from app.config import settings

logger = logging.getLogger(__name__)


class BundleAssembler:
    def __init__(self):
        self.client = None
        try:
            if not settings.GOOGLE_APPLICATION_CREDENTIALS and not os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS"
            ):
                raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS is not configured")
            from app.core.bigquery import get_bq_client

            self.client = get_bq_client()
        except Exception as exc:
            logger.warning(
                "Could not initialize BigQuery client, continuing with mocked data: %s",
                exc,
            )

    async def build_bundle(self, wave_id: str, language: str) -> AnalysisBundle:
        """
        Fetches data from BigQuery decomposer_gold tables and assembles the AnalysisBundle.
        Falls back to mocked data if BigQuery client is not available or query fails.
        """
        metrics = {}
        analysis_results = {}

        if self.client:
            try:
                query_activity = f"""
                    SELECT metric_name, metric_value
                    FROM `decomposer_gold.activity`
                    WHERE wave_id = '{wave_id}'
                """
                query_job = self.client.query(query_activity)
                for row in query_job.result():
                    metrics[row.metric_name] = row.metric_value

                query_analysis = f"""
                    SELECT analysis_type, findings
                    FROM `decomposer_gold.analysis_results`
                    WHERE wave_id = '{wave_id}'
                """
                query_job2 = self.client.query(query_analysis)
                for row in query_job2.result():
                    analysis_results[row.analysis_type] = row.findings
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
