import json
import os
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("WAVE_DATA_PROVIDER", "mock")

from app.config import settings
from app.deck.ai_outline import DisabledAIOutlineProvider
from app.data.mock_provider import MOCK_WAVE_DATA
from app.main import app
import app.deck.routes as deck_routes


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "canonical_deck_document.json"


def test_validate_deck_accepts_demo_deck():
    with TestClient(app) as client:
        demo = client.get("/api/v1/decks/demo")
        assert demo.status_code == 200

        response = client.post(
            "/api/v1/decks/validate",
            json={"deck": demo.json()["deck_json"]},
        )

    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_save_requires_token_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "secret")

    with TestClient(app) as client:
        demo = client.get("/api/v1/decks/demo").json()["deck_json"]
        response = client.put(
            f"/api/v1/decks/{demo['deck_id']}",
            json={"deck": demo},
        )

    assert response.status_code == 401


def test_from_wave_creates_persisted_deck(monkeypatch):
    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(settings, "WAVE_DATA_PROVIDER", "mock")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/decks/from-wave",
            json={"wave_id": "DEMO_WAVE_001"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["deck_json"]["source_wave_id"] == "DEMO_WAVE_001"
    assert payload["deck_json"]["slides"]
    with TestClient(app) as client:
        fetched = client.get(f"/api/v1/decks/{payload['id']}")
    assert fetched.status_code == 200


def test_ai_outline_from_wave_returns_validated_outline(monkeypatch):
    class ValidOutlineProvider:
        async def generate_outline(self, payload: dict) -> dict:
            return {
                "deck_title": "AI Suggested Evidence Outline",
                "audience": payload["audience"],
                "objective": "Turn validated findings into an executive outline.",
                "source_wave_id": payload["wave_id"],
                "slides": [
                    {
                        "title": "Title",
                        "purpose": "Open the deck.",
                        "key_message": "The deck is based on validated wave evidence.",
                        "evidence_refs": [],
                        "suggested_visual_type": "title",
                    },
                    {
                        "title": "Finding priority",
                        "purpose": "Focus the audience on the first evidence-backed finding.",
                        "key_message": "The first validated finding should anchor the story.",
                        "evidence_refs": ["finding_1"],
                        "suggested_visual_type": "insight_slide",
                    },
                ],
            }

    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(settings, "WAVE_DATA_PROVIDER", "mock")
    monkeypatch.setattr(deck_routes, "get_ai_outline_provider", lambda: ValidOutlineProvider())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/decks/from-wave/outline/ai",
            json={"wave_id": "DEMO_WAVE_001"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "ai"
    assert payload["outline"]["deck_title"] == "AI Suggested Evidence Outline"
    assert payload["outline"]["source_wave_id"] == "DEMO_WAVE_001"
    assert payload["outline"]["slides"][1]["evidence_refs"] == ["finding_1"]


def test_ai_outline_malformed_provider_output_returns_422(monkeypatch):
    class MalformedOutlineProvider:
        async def generate_outline(self, payload: dict) -> dict:
            return {
                "deck_title": "Missing required fields",
                "source_wave_id": payload["wave_id"],
                "slides": [],
            }

    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(settings, "WAVE_DATA_PROVIDER", "mock")
    monkeypatch.setattr(deck_routes, "get_ai_outline_provider", lambda: MalformedOutlineProvider())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/decks/from-wave/outline/ai",
            json={"wave_id": "DEMO_WAVE_001"},
        )

    assert response.status_code == 422
    assert "schema validation" in response.json()["detail"]


def test_ai_outline_disabled_provider_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(settings, "WAVE_DATA_PROVIDER", "mock")
    monkeypatch.setattr(deck_routes, "get_ai_outline_provider", lambda: DisabledAIOutlineProvider())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/decks/from-wave/outline/ai",
            json={"wave_id": "DEMO_WAVE_001"},
        )

    assert response.status_code == 503
    assert "AI outline provider is not configured" in response.json()["detail"]


def test_ai_outline_invalid_evidence_ref_returns_422(monkeypatch):
    class InvalidEvidenceProvider:
        async def generate_outline(self, payload: dict) -> dict:
            return {
                "deck_title": "Unsupported Evidence Outline",
                "audience": payload["audience"],
                "objective": "Use only valid evidence refs.",
                "source_wave_id": payload["wave_id"],
                "slides": [
                    {
                        "title": "Unsupported claim",
                        "purpose": "Exercise evidence validation.",
                        "key_message": "This slide references evidence outside the context.",
                        "evidence_refs": ["not_in_context"],
                        "suggested_visual_type": "insight_slide",
                    }
                ],
            }

    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(settings, "WAVE_DATA_PROVIDER", "mock")
    monkeypatch.setattr(deck_routes, "get_ai_outline_provider", lambda: InvalidEvidenceProvider())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/decks/from-wave/outline/ai",
            json={"wave_id": "DEMO_WAVE_001"},
        )

    assert response.status_code == 422
    assert "not_in_context" in response.json()["detail"]


def _valid_ai_outline_payload() -> dict:
    return {
        "deck_title": "Accepted AI Outline Deck",
        "audience": "executive stakeholders",
        "objective": "Convert the approved outline into an editable evidence-backed deck.",
        "source_wave_id": "DEMO_WAVE_001",
        "warnings": [],
        "slides": [
            {
                "title": "Title",
                "purpose": "Open the deck.",
                "key_message": "The deck is based on validated wave evidence.",
                "evidence_refs": [],
                "suggested_visual_type": "title",
            },
            {
                "title": "Priority finding",
                "purpose": "Explain the highest-priority validated finding.",
                "key_message": "The first validated finding should anchor the story.",
                "evidence_refs": ["finding_1"],
                "suggested_visual_type": "insight_slide",
            },
        ],
    }


def test_accept_ai_outline_creates_persisted_deck(monkeypatch):
    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(settings, "WAVE_DATA_PROVIDER", "mock")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/decks/from-wave/outline/accept",
            json={
                "wave_id": "DEMO_WAVE_001",
                "outline": _valid_ai_outline_payload(),
            },
        )
        assert response.status_code == 200
        payload = response.json()
        fetched = client.get(f"/api/v1/decks/{payload['id']}")

    assert payload["deck_json"]["source_wave_id"] == "DEMO_WAVE_001"
    assert payload["deck_json"]["title"] == "Accepted AI Outline Deck"
    assert payload["deck_json"]["slides"]
    assert payload["outline_json"]["source"] == "accepted_ai_outline"
    assert fetched.status_code == 200
    assert fetched.json()["deck_json"]["title"] == "Accepted AI Outline Deck"


def test_accept_ai_outline_invalid_evidence_ref_returns_422(monkeypatch):
    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(settings, "WAVE_DATA_PROVIDER", "mock")
    outline = _valid_ai_outline_payload()
    outline["slides"][1]["evidence_refs"] = ["not_in_context"]

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/decks/from-wave/outline/accept",
            json={
                "wave_id": "DEMO_WAVE_001",
                "outline": outline,
            },
        )

    assert response.status_code == 422
    assert "not_in_context" in response.json()["detail"]


def test_accept_ai_outline_does_not_call_ai_provider(monkeypatch):
    def fail_if_called():
        raise AssertionError("accept endpoint must not call the AI outline provider")

    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(settings, "WAVE_DATA_PROVIDER", "mock")
    monkeypatch.setattr(deck_routes, "get_ai_outline_provider", fail_if_called)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/decks/from-wave/outline/accept",
            json={
                "wave_id": "DEMO_WAVE_001",
                "outline": _valid_ai_outline_payload(),
            },
        )

    assert response.status_code == 200


def test_updated_deck_document_is_saved_and_reloaded(monkeypatch):
    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(settings, "WAVE_DATA_PROVIDER", "mock")

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/decks/from-wave",
            json={"wave_id": "DEMO_WAVE_001"},
        )
        assert created.status_code == 200
        deck_id = created.json()["id"]
        deck = created.json()["deck_json"]
        deck["title"] = "Edited Evidence Deck"
        deck["slides"][0]["content"][0]["text"] = "Edited Evidence Deck"
        deck["metadata"]["edited_by_test"] = True

        saved = client.put(
            f"/api/v1/decks/{deck_id}",
            json={"deck": deck},
        )
        assert saved.status_code == 200

        reloaded = client.get(f"/api/v1/decks/{deck_id}")

    assert reloaded.status_code == 200
    payload = reloaded.json()
    assert payload["title"] == "Edited Evidence Deck"
    assert payload["deck_json"]["title"] == "Edited Evidence Deck"
    assert payload["deck_json"]["slides"][0]["content"][0]["text"] == "Edited Evidence Deck"
    assert payload["deck_json"]["metadata"]["edited_by_test"] is True


def test_created_deck_can_export_pptx(monkeypatch):
    pytest.importorskip("pptx")
    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(settings, "WAVE_DATA_PROVIDER", "mock")

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/decks/from-wave",
            json={"wave_id": "DEMO_WAVE_001"},
        )
        assert created.status_code == 200
        deck_id = created.json()["id"]

        exported = client.get(f"/api/v1/decks/{deck_id}/export/pptx")

    assert exported.status_code == 200
    assert exported.content.startswith(b"PK")
    assert "presentation" in exported.headers["content-type"]


def test_persisted_deck_can_preview_semantic_html(monkeypatch):
    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(settings, "WAVE_DATA_PROVIDER", "mock")

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/decks/from-wave",
            json={"wave_id": "DEMO_WAVE_001"},
        )
        assert created.status_code == 200
        deck_id = created.json()["id"]

        deck = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        deck["deck_id"] = deck_id
        deck["slides"][0]["content"][1]["text"] = "Escaped <script>alert(1)</script>"
        saved = client.put(f"/api/v1/decks/{deck_id}", json={"deck": deck})
        assert saved.status_code == 200

        preview = client.get(f"/api/v1/decks/{deck_id}/preview/html")

    assert preview.status_code == 200
    assert "text/html" in preview.headers["content-type"]
    html = preview.text
    assert "Canonical Evidence Deck" in html
    assert "Evidence score" in html
    assert "56.25" in html
    assert "<th>Activity</th>" in html
    assert "<td>US10</td>" in html
    assert "Chart placeholder:" in html
    assert "chart_6" in html
    assert "Callout:" in html
    assert "Any new numeric claim must be present in the evidence registry." in html
    assert "Source Note:" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_missing_deck_html_preview_returns_404():
    with TestClient(app) as client:
        response = client.get("/api/v1/decks/missing_deck_for_html_preview/preview/html")

    assert response.status_code == 404
    assert response.json()["detail"] == "Deck not found"


def test_invalid_deck_update_is_rejected_visibly(monkeypatch):
    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")

    with TestClient(app) as client:
        demo = client.get("/api/v1/decks/demo").json()["deck_json"]
        demo["slides"][0]["content"][0]["type"] = "not_a_real_block"
        response = client.put(
            f"/api/v1/decks/{demo['deck_id']}",
            json={"deck": demo},
        )

    assert response.status_code == 422
    assert "not_a_real_block" in response.text


def test_from_wave_blocks_bad_data_with_visible_error(monkeypatch):
    class NoGoldRowsProvider:
        def get_wave_data(self, wave_id: str) -> dict:
            wave_data = deepcopy(MOCK_WAVE_DATA)
            wave_data["wave"]["id"] = wave_id
            wave_data["gold"]["activity"] = []
            return wave_data

        def get_latest_wave_id(self) -> str:
            return "BAD_WAVE"

    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(deck_routes, "get_provider", lambda config: NoGoldRowsProvider())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/decks/from-wave",
            json={"wave_id": "BAD_WAVE"},
        )

    assert response.status_code == 422
    assert "no gold activity rows" in response.json()["detail"]


def test_from_wave_blocks_empty_completed_analysis_results(monkeypatch):
    class EmptyAnalysisResultsProvider:
        def get_wave_data(self, wave_id: str) -> dict:
            wave_data = deepcopy(MOCK_WAVE_DATA)
            wave_data["wave"]["id"] = wave_id
            for analysis in wave_data["analyses"]:
                if analysis.get("status") == "complete":
                    analysis["result"] = {}
            return wave_data

        def get_latest_wave_id(self) -> str:
            return "EMPTY_ANALYSIS_WAVE"

    monkeypatch.setattr(settings, "DECK_EDITOR_TOKEN", "")
    monkeypatch.setattr(deck_routes, "get_provider", lambda config: EmptyAnalysisResultsProvider())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/decks/from-wave",
            json={"wave_id": "EMPTY_ANALYSIS_WAVE"},
        )

    assert response.status_code == 422
    assert "no completed analysis results" in response.json()["detail"]
