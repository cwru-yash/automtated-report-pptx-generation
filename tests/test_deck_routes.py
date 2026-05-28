import os
from copy import deepcopy

from fastapi.testclient import TestClient

os.environ.setdefault("WAVE_DATA_PROVIDER", "mock")

from app.config import settings
from app.data.mock_provider import MOCK_WAVE_DATA
from app.main import app
import app.deck.routes as deck_routes


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
