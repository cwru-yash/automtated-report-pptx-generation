try:
    from google.cloud import bigquery
except ImportError as exc:
    bigquery = None
    _BIGQUERY_IMPORT_ERROR = exc
else:
    _BIGQUERY_IMPORT_ERROR = None


def get_bq_client():
    """
    Initialize and return a BigQuery client.
    Expects GOOGLE_APPLICATION_CREDENTIALS to be set in the environment.
    """
    if bigquery is None:
        raise RuntimeError(
            "google-cloud-bigquery is not installed in this Python environment. "
            "Install dependencies with: pip install -r requirements.txt"
        ) from _BIGQUERY_IMPORT_ERROR
    return bigquery.Client()
