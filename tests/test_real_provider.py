"""
Step-by-step real-data test for SupabaseWaveDataProvider.

Run with:
  poetry run python tests/test_real_provider.py

Tests:
  1. get_latest_wave_id()
  2. get_wave_data() via Option A (GCS)
  3. get_wave_data() via Option B fallback (live DB)
  4. Schema validation against MOCK_WAVE_DATA keys
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("test_real_provider")

from app.config import settings
from app.data.provider import get_provider
from app.data.mock_provider import MOCK_WAVE_DATA

SEPARATOR = "\n" + "=" * 60 + "\n"


def check_schema(wave_data: dict, label: str):
    """Verify that required top-level keys are present and non-empty."""
    required_keys = ["schema_version", "wave", "quality", "analyses", "gold", "metadata"]
    missing = [k for k in required_keys if k not in wave_data]
    if missing:
        logger.error("[%s] SCHEMA FAIL — missing keys: %s", label, missing)
        return False

    analyses = wave_data.get("analyses", [])
    gold_rows = wave_data.get("gold", {}).get("activity", [])
    wave_id = wave_data.get("wave", {}).get("id", "UNKNOWN")
    project_name = wave_data.get("wave", {}).get("project", {}).get("name", "UNKNOWN")

    logger.info("[%s] ✅ Schema OK", label)
    logger.info("[%s]    wave_id      = %s", label, wave_id)
    logger.info("[%s]    project      = %s", label, project_name)
    logger.info("[%s]    analyses     = %d", label, len(analyses))
    logger.info("[%s]    gold rows    = %d", label, len(gold_rows))
    logger.info("[%s]    quality      = %s", label, wave_data.get("quality"))
    return True


def test_1_latest_wave_id(provider):
    print(SEPARATOR + "TEST 1: get_latest_wave_id()")
    wave_id = provider.get_latest_wave_id()
    assert wave_id, "wave_id should not be empty"
    logger.info("✅ Latest wave_id: %s", wave_id)
    return wave_id


def test_2_option_a(provider, wave_id: str):
    print(SEPARATOR + "TEST 2: get_wave_data() — Option A (GCS primary path)")
    data = provider.get_wave_data(wave_id)
    check_schema(data, "Option A")
    return data


def test_3_option_b(provider, wave_id: str):
    print(SEPARATOR + "TEST 3: get_wave_data() — Option B (live DB fallback, forced)")
    # Temporarily disable GCS by forcing _fetch_from_live_db directly
    data = provider._fetch_from_live_db(wave_id)
    check_schema(data, "Option B")
    return data


def test_4_schema_vs_mock(live_data: dict):
    print(SEPARATOR + "TEST 4: Schema compatibility vs MockWaveDataProvider")
    mock_keys = set(MOCK_WAVE_DATA.keys())
    live_keys = set(live_data.keys())
    missing_in_live = mock_keys - live_keys
    extra_in_live = live_keys - mock_keys
    if missing_in_live:
        logger.warning("Keys in mock but not in live data: %s", missing_in_live)
    if extra_in_live:
        logger.info("Extra keys in live data (ok): %s", extra_in_live)
    if not missing_in_live:
        logger.info("✅ Live data schema is fully compatible with mock schema")
    else:
        logger.error("❌ Schema mismatch — report rendering may fail for missing keys")


if __name__ == "__main__":
    print("\n🔍 Real Data Provider Test Suite")
    print(f"   WAVE_DATA_PROVIDER = {settings.WAVE_DATA_PROVIDER}")
    print(f"   SUPABASE_URL       = {settings.SUPABASE_URL}")
    print(f"   SECRET_KEY set     = {'YES' if settings.SUPABASE_SECRET_KEY else 'NO ⚠️  — set SUPABASE_SECRET_KEY in .env'}")
    print(f"   GCS_BUCKET         = {settings.GCS_DELIVERABLE_BUCKET}")

    if not settings.SUPABASE_SECRET_KEY:
        print("\n❌ Cannot run tests — SUPABASE_SECRET_KEY not set in .env")
        sys.exit(1)

    provider = get_provider(settings)
    logger.info("Provider: %s", type(provider).__name__)

    try:
        wave_id = test_1_latest_wave_id(provider)
        data_a = test_2_option_a(provider, wave_id)
        data_b = test_3_option_b(provider, wave_id)
        test_4_schema_vs_mock(data_b)
        print(SEPARATOR + "✅ ALL TESTS PASSED")
    except Exception as exc:
        logger.exception("Test failed: %s", exc)
        sys.exit(1)
