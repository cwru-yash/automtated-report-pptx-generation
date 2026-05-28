import asyncio
from copy import deepcopy

import pytest

from app.bundle.assembler import BundleAssembler
from app.data.mock_provider import MOCK_WAVE_DATA
from app.deck.evidence import EvidenceRegistry
from app.deck.extractor import FindingExtractor
from app.deck.planner import SlidePlanner
from app.deck.schema import DeckDataQualityError, DeckValidationError


def build_bundle(wave_data: dict):
    return asyncio.run(
        BundleAssembler().build_bundle(
            wave_data["wave"]["id"],
            "en-US",
            wave_data=wave_data,
        )
    )


def build_plan(wave_data: dict):
    bundle = build_bundle(wave_data)
    context = FindingExtractor().extract(bundle, wave_data)
    plan = SlidePlanner().create_plan(context, bundle)
    return bundle, context, plan


def test_good_wave_produces_valid_deck_plan():
    wave_data = deepcopy(MOCK_WAVE_DATA)

    bundle, context, plan = build_plan(wave_data)

    assert context.gold_row_count == 4
    assert context.complete_analysis_count >= 1
    assert context.findings
    assert plan.validation_status == "valid"
    assert plan.slides[0].slide_type == "title"
    assert any(slide.slide_type == "finding" for slide in plan.slides)

    EvidenceRegistry.from_bundle(bundle, context.evidence_registry).validate_deck_plan(plan)


def test_wave_with_no_gold_rows_is_blocked():
    wave_data = deepcopy(MOCK_WAVE_DATA)
    wave_data["gold"]["activity"] = []
    bundle = build_bundle(wave_data)

    with pytest.raises(DeckDataQualityError, match="no gold activity rows"):
        FindingExtractor().extract(bundle, wave_data)


def test_wave_with_empty_analysis_results_is_blocked():
    wave_data = deepcopy(MOCK_WAVE_DATA)
    for analysis in wave_data["analyses"]:
        if analysis.get("status") == "complete":
            analysis["result"] = {}
    bundle = build_bundle(wave_data)

    with pytest.raises(DeckDataQualityError, match="no completed analysis results"):
        FindingExtractor().extract(bundle, wave_data)


def test_deck_plan_rejects_numeric_claim_not_in_bundle():
    wave_data = deepcopy(MOCK_WAVE_DATA)
    bundle, context, plan = build_plan(wave_data)
    plan.slides[0].bullets.append("Unsupported satisfaction score is 999.")

    with pytest.raises(DeckValidationError, match="999"):
        EvidenceRegistry.from_bundle(bundle, context.evidence_registry).validate_deck_plan(plan)


def test_activity_codes_like_us10_are_not_numeric_claims():
    wave_data = deepcopy(MOCK_WAVE_DATA)
    bundle, context, plan = build_plan(wave_data)
    plan.slides[0].bullets.append("US10 is a priority activity code.")

    EvidenceRegistry.from_bundle(bundle, context.evidence_registry).validate_deck_plan(plan)
