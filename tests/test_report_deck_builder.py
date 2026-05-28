import pytest

from app.data.mock_provider import MockWaveDataProvider
from app.deck.builder import ReportDeckBuilder
from app.deck.layout_schema import DeckDocument


@pytest.mark.asyncio
async def test_report_deck_builder_creates_persisted_recursive_deck():
    result = await ReportDeckBuilder(provider=MockWaveDataProvider()).build_from_wave(
        wave_id="DEMO_WAVE_001",
        language="en-US",
        audience="executive stakeholders",
        tone="consulting",
    )

    parsed = DeckDocument.model_validate(result.row.deck_json)

    assert parsed.deck_id == result.row.id
    assert parsed.source_wave_id == "DEMO_WAVE_001"
    assert parsed.slides
    assert result.deck_plan.slides
    assert result.findings_context.findings
    assert result.bundle.gold_activity_version_id == "gold-ver-demo-001"
    assert result.bundle.analysis_run_id == "ar-demo-001"
