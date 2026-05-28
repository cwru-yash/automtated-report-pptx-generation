from __future__ import annotations

from app.bundle.schema import AnalysisBundle
from app.deck.ai_outline import AIOutlineError, DeckOutline, validate_outline_evidence
from app.deck.evidence import EvidenceRegistry
from app.deck.schema import DeckPlan, DeckSlide, EvidenceItem, Finding, FindingsContext, SlideType


def accepted_outline_to_deck_plan(
    outline: DeckOutline,
    context: FindingsContext,
    bundle: AnalysisBundle,
    *,
    audience: str = "executive stakeholders",
    tone: str = "consulting",
) -> DeckPlan:
    """
    Convert a human-approved outline into a deterministic DeckPlan.

    AI is allowed to influence the outline order and wording. The persisted
    recursive deck is still generated from our own DeckPlan/LayoutMapper path.
    """
    if outline.source_wave_id != context.wave_id:
        raise AIOutlineError(
            "Accepted outline source_wave_id must match requested wave_id."
        )

    validate_outline_evidence(outline, context)

    slides: list[DeckSlide] = [
        DeckSlide(
            slide_number=1,
            slide_type="title",
            title=outline.deck_title,
            subtitle=outline.objective,
            speaker_notes=(
                "Open with the human-approved outline objective and evidence standard."
            ),
        ),
        DeckSlide(
            slide_number=2,
            slide_type="overview",
            title="Accepted Outline Objective",
            bullets=[
                outline.objective,
                _project_context(context),
                f"Audience: {outline.audience or audience}.",
            ],
            speaker_notes=(
                "Explain that AI suggested the outline, but deck generation remains deterministic."
            ),
        ),
    ]

    slide_number = 3
    for outline_slide in outline.slides:
        if outline_slide.suggested_visual_type == "title":
            continue

        evidence, source_refs, chart_refs = _resolve_outline_evidence(
            outline_slide.evidence_refs,
            context,
        )
        slides.append(
            DeckSlide(
                slide_number=slide_number,
                slide_type=_slide_type_for_visual(outline_slide.suggested_visual_type),
                title=outline_slide.title,
                bullets=_slide_bullets(outline_slide.key_message, outline_slide.purpose, evidence),
                evidence=evidence,
                chart_refs=chart_refs,
                speaker_notes=(
                    "Generated from a human-approved AI outline; stay within the "
                    "validated evidence refs attached to this slide."
                ),
                source_refs=source_refs or outline_slide.evidence_refs,
            )
        )
        slide_number += 1

    if context.limitations:
        slides.append(
            DeckSlide(
                slide_number=slide_number,
                slide_type="limitation",
                title="Limitations and Guardrails",
                bullets=context.limitations[:5],
                speaker_notes="Use this slide to keep the deck honest about evidence limits.",
            )
        )
        slide_number += 1

    if context.recommendations:
        slides.append(
            DeckSlide(
                slide_number=slide_number,
                slide_type="recommendation",
                title="Recommended Next Steps",
                bullets=context.recommendations[:5],
                speaker_notes="Translate the accepted outline into practical next moves.",
            )
        )

    deck_plan = DeckPlan(
        deck_title=outline.deck_title,
        subtitle=outline.objective,
        audience=outline.audience or audience,
        tone=tone,
        source_wave_id=context.wave_id,
        source_project=context.project_name,
        validation_warnings=[*context.warnings, *outline.warnings],
        evidence_registry=context.evidence_registry,
        slides=slides,
    )
    EvidenceRegistry.from_bundle(bundle, context.evidence_registry).validate_deck_plan(deck_plan)
    return deck_plan


def _slide_type_for_visual(visual_type: str) -> SlideType:
    if visual_type == "recommendation_slide":
        return "recommendation"
    if visual_type == "appendix":
        return "limitation"
    if visual_type in {"executive_summary", "section_divider"}:
        return "context"
    return "finding"


def _resolve_outline_evidence(
    refs: list[str],
    context: FindingsContext,
) -> tuple[list[str], list[str], list[str]]:
    finding_by_ref = {
        f"finding_{index}": finding
        for index, finding in enumerate(context.findings, start=1)
    }
    registry_by_ref = _registry_lookup(context.evidence_registry)
    evidence: list[str] = []
    source_refs: list[str] = []
    chart_refs: list[str] = []

    for ref in refs:
        finding = finding_by_ref.get(ref)
        if finding is not None:
            evidence.extend(finding.evidence[:3])
            source_refs.extend(finding.source_refs)
            chart_refs.extend(finding.chart_refs)
            continue

        evidence_item = registry_by_ref.get(ref)
        if evidence_item is not None:
            evidence.append(f"{evidence_item.label}: {evidence_item.value}")
            source_refs.append(evidence_item.source)
            continue

        if _is_chart_ref(ref, context.findings):
            chart_refs.append(ref)
        source_refs.append(ref)

    return _dedupe(evidence), _dedupe(source_refs), _dedupe(chart_refs)


def _registry_lookup(items: list[EvidenceItem]) -> dict[str, EvidenceItem]:
    lookup: dict[str, EvidenceItem] = {}
    for item in items:
        if item.label:
            lookup[item.label] = item
        if item.source:
            lookup[item.source] = item
    return lookup


def _is_chart_ref(ref: str, findings: list[Finding]) -> bool:
    return any(ref in finding.chart_refs for finding in findings)


def _slide_bullets(key_message: str, purpose: str, evidence: list[str]) -> list[str]:
    return [
        item
        for item in [
            key_message,
            purpose,
            *evidence[:2],
        ]
        if item
    ][:5]


def _project_context(context: FindingsContext) -> str:
    parts = [
        part
        for part in (
            context.project_name,
            context.study_name,
            context.industry_name,
        )
        if part
    ]
    if parts:
        return "Context: " + " | ".join(parts) + "."
    return "Context comes from the completed wave metadata."


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
