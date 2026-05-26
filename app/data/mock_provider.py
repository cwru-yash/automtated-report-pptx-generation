import logging
from app.data.provider import WaveDataProvider

logger = logging.getLogger(__name__)

MOCK_WAVE_DATA = {
    "schema_version": "1.0",
    "generated_at": "2026-05-14T00:00:00Z",
    "assets": {"brand_logo_data_url": ""},
    "wave": {
        "id": "DEMO_WAVE_001",
        "reference_period": {"start": "2026-01-01", "end": "2026-03-31"},
        "project": {"id": "proj-001", "name": "Ceragem Brasil Q1 2026"},
        "study": {"id": "study-001", "name": "Brand Health Study", "cvc_id": "CVC-BR-001"},
        "country_iso_code": "BR",
        "industry": {"id": "ind-001", "name": "Health & Wellness"},
        "brand_hierarchy": {"focus": "brand-ceragem"},
    },
    "quality": {
        "concept": "APROVADO",
        "concept_points": 82,
        "weighted_score": 78.5,
        "briefing_adherence_pct": 0.91,
    },
    "analyses": [
        {
            "analysis_type": 1,
            "analysis_name": "Industry Average Curve",
            "status": "complete",
            "result": {
                "brands": [
                    {"brand_id": "brand-ceragem", "satisfaction_index": 72.4},
                    {"brand_id": "brand-competitor-a", "satisfaction_index": 65.1},
                    {"brand_id": "brand-competitor-b", "satisfaction_index": 58.3},
                    {"brand_id": "brand-competitor-c", "satisfaction_index": 61.8},
                ],
                "industry_avg": 64.4,
            },
        },
        {
            "analysis_type": 2,
            "analysis_name": "Strong Links — Industry",
            "status": "complete",
            "result": {
                "links": [
                    {"activity_code": "ACT-001", "label": "Product Quality", "score": 88.2},
                    {"activity_code": "ACT-002", "label": "Brand Reputation", "score": 84.7},
                    {"activity_code": "ACT-003", "label": "Customer Service", "score": 81.3},
                    {"activity_code": "ACT-004", "label": "Value for Money", "score": 79.1},
                    {"activity_code": "ACT-005", "label": "Innovation", "score": 76.5},
                ]
            },
        },
        {
            "analysis_type": 3,
            "analysis_name": "Weak Links — Industry",
            "status": "complete",
            "result": {
                "links": [
                    {"activity_code": "ACT-010", "label": "Delivery Speed", "score": 41.2},
                    {"activity_code": "ACT-011", "label": "Online Presence", "score": 45.8},
                    {"activity_code": "ACT-012", "label": "Price Competitiveness", "score": 48.3},
                    {"activity_code": "ACT-013", "label": "After-Sales Support", "score": 51.7},
                ]
            },
        },
        {
            "analysis_type": 4,
            "analysis_name": "S&R Index Ranking",
            "status": "skipped",
            "skip_reason": "NO_NPS",
            "skip_message": "S&R Index requires NPS data. Survey module not active for this Wave.",
        },
        {
            "analysis_type": 5,
            "analysis_name": "Strong Links — Brand",
            "status": "complete",
            "result": {
                "brand_id": "brand-ceragem",
                "links": [
                    {"activity_code": "ACT-001", "label": "Product Quality", "score": 91.4},
                    {"activity_code": "ACT-006", "label": "Warranty & Support", "score": 87.2},
                    {"activity_code": "ACT-007", "label": "Store Experience", "score": 83.9},
                ],
            },
        },
        {
            "analysis_type": 6,
            "analysis_name": "Achilles Heel — Brand",
            "status": "complete",
            "result": {
                "brand_id": "brand-ceragem",
                "links": [
                    {"activity_code": "ACT-010", "label": "Delivery Speed", "score": 38.1},
                    {"activity_code": "ACT-011", "label": "Online Presence", "score": 42.6},
                ],
            },
        },
        {
            "analysis_type": 7,
            "analysis_name": "Best of Best",
            "status": "complete",
            "result": {
                "rankings": [
                    {"brand_id": "brand-ceragem", "activity_code": "ACT-001", "label": "Product Quality", "score": 91.4},
                    {"brand_id": "brand-competitor-a", "activity_code": "ACT-002", "label": "Brand Reputation", "score": 88.0},
                    {"brand_id": "brand-competitor-b", "activity_code": "ACT-008", "label": "Social Media", "score": 84.2},
                ]
            },
        },
        {
            "analysis_type": 8,
            "analysis_name": "Breakdown",
            "status": "complete",
            "result": {
                "segments": [
                    {"segment_dimension": "age_group", "segment_value": "18-34", "brand_id": "brand-ceragem", "satisfaction_index": 74.1},
                    {"segment_dimension": "age_group", "segment_value": "35-54", "brand_id": "brand-ceragem", "satisfaction_index": 71.8},
                    {"segment_dimension": "age_group", "segment_value": "55+", "brand_id": "brand-ceragem", "satisfaction_index": 68.9},
                    {"segment_dimension": "age_group", "segment_value": "18-34", "brand_id": "brand-competitor-a", "satisfaction_index": 63.2},
                    {"segment_dimension": "age_group", "segment_value": "35-54", "brand_id": "brand-competitor-a", "satisfaction_index": 66.7},
                    {"segment_dimension": "age_group", "segment_value": "55+", "brand_id": "brand-competitor-a", "satisfaction_index": 64.9},
                ]
            },
        },
    ],
    "gold": {
        "activity": [
            {"activity_code": "ACT-001", "brand_id": "brand-ceragem", "satisfaction_index": 72.4, "review_count": 1240, "source_type": "reviews", "segment_dimension": None, "segment_value": None},
            {"activity_code": "ACT-001", "brand_id": "brand-competitor-a", "satisfaction_index": 65.1, "review_count": 980, "source_type": "reviews", "segment_dimension": None, "segment_value": None},
            {"activity_code": "ACT-001", "brand_id": "brand-competitor-b", "satisfaction_index": 58.3, "review_count": 720, "source_type": "reviews", "segment_dimension": None, "segment_value": None},
            {"activity_code": "ACT-001", "brand_id": "brand-competitor-c", "satisfaction_index": 61.8, "review_count": 810, "source_type": "reviews", "segment_dimension": None, "segment_value": None},
        ]
    },
    "metadata": {
        "deliverable_bundle_id": "bundle-demo-001",
        "commentary_agent_version_id": "cav-demo-001",
        "gold_activity_version_id": "gold-ver-demo-001",
        "quality_record_id": "qr-demo-001",
        "analysis_run_id": "ar-demo-001",
    },
}

class MockWaveDataProvider(WaveDataProvider):
    def get_wave_data(self, wave_id: str) -> dict:
        logger.info(f"Returning mock data for wave_id: {wave_id}")
        return MOCK_WAVE_DATA

    def get_latest_wave_id(self) -> str:
        return "DEMO_WAVE_001"
