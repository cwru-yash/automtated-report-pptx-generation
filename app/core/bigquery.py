try:
    from google.cloud import bigquery
except ImportError as exc:
    bigquery = None
    _BIGQUERY_IMPORT_ERROR = exc
else:
    _BIGQUERY_IMPORT_ERROR = None


def get_bq_client(project: str | None = None):
    """
    Initialize and return a BigQuery client.

    google-cloud-bigquery automatically uses Application Default Credentials,
    so this works with either GOOGLE_APPLICATION_CREDENTIALS or local ADC from
    `gcloud auth application-default login`.
    """
    if bigquery is None:
        raise RuntimeError(
            "google-cloud-bigquery is not installed in this Python environment. "
            "Install dependencies with: pip install -r requirements.txt"
        ) from _BIGQUERY_IMPORT_ERROR
    return bigquery.Client(project=project)
