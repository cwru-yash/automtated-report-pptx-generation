from __future__ import annotations

from app.bundle.schema import AnalysisBundle
from app.deck.evidence import EvidenceRegistry
from app.deck.schema import DeckPlan, DeckSlide, FindingsContext


class SlidePlanner:
    """Build a deterministic consulting-style slide plan from extracted findings."""

    def create_plan(
        self,
        context: FindingsContext,
        bundle: AnalysisBundle,
        *,
        audience: str = "executive stakeholders",
        tone: str = "consulting",
    ) -> DeckPlan:
        title = self._deck_title(context)
        slides: list[DeckSlide] = []

        slides.append(
            DeckSlide(
                slide_number=1,
                slide_type="title",
                title=title,
                subtitle="Evidence-backed findings, recommendations, and next steps",
                bullets=[],
                speaker_notes="Introduce the completed wave and explain that all claims are evidence-backed.",
            )
        )
        slides.append(
            DeckSlide(
                slide_number=2,
                slide_type="overview",
                title="Analysis Objective",
                bullets=[
                    "Translate the completed analytical wave into an executive-ready deck.",
                    self._project_context(context),
                    "Focus on findings that have direct evidence in the approved bundle.",
                ],
                speaker_notes="Set the expectation that this is an interpretation of completed analysis outputs.",
            )
        )
        slides.append(
            DeckSlide(
                slide_number=3,
                slide_type="data_quality",
                title="Data Quality Gate",
                bullets=[
                    f"Gold activity rows: {context.gold_row_count}.",
                    f"Completed analyses with results: {context.complete_analysis_count}.",
                    self._quality_line(context),
                    "Empty or skipped analyses are excluded from generated charts.",
                ],
                evidence=[
                    f"Gold activity rows: {context.gold_row_count}.",
                    f"Completed analyses with results: {context.complete_analysis_count}.",
                ],
                speaker_notes="Explain why the generator blocks weak waves instead of making fake charts.",
            )
        )

        slide_number = 4
        for index, finding in enumerate(context.findings[:6], start=1):
            slides.append(
                DeckSlide(
                    slide_number=slide_number,
                    slide_type="finding",
                    title=f"Finding {index}: {finding.title}",
                    bullets=[
                        finding.finding,
                        finding.why_it_matters,
                        *finding.evidence[:3],
                    ][:5],
                    evidence=finding.evidence,
                    chart_refs=finding.chart_refs,
                    speaker_notes=(
                        "Stay close to the evidence listed on this slide; avoid adding "
                        "unsupported interpretation."
                    ),
                    source_refs=finding.source_refs,
                )
            )
            slide_number += 1

        slides.append(
            DeckSlide(
                slide_number=slide_number,
                slide_type="recommendation",
                title="Recommended Next Steps",
                bullets=context.recommendations[:5],
                speaker_notes="Frame these as the next analysis and operating decisions, not causal proof.",
            )
        )
        slide_number += 1

        slides.append(
            DeckSlide(
                slide_number=slide_number,
                slide_type="limitation",
                title="Limitations",
                bullets=context.limitations[:5],
                speaker_notes="Be explicit about what the current wave can and cannot prove.",
            )
        )
        slide_number += 1

        slides.append(
            DeckSlide(
                slide_number=slide_number,
                slide_type="conclusion",
                title="Executive Close",
                bullets=[
                    "The deck is grounded in completed wave evidence.",
                    "The strongest recommendations come from repeatable activity-level signals.",
                    "The next step is to validate root causes for the highest-priority gaps.",
                ],
                speaker_notes="Close by moving from evidence to practical action.",
            )
        )

        deck_plan = DeckPlan(
            deck_title=title,
            subtitle="Consulting-style summary generated from a completed analytical wave",
            audience=audience,
            tone=tone,
            source_wave_id=context.wave_id,
            source_project=context.project_name,
            validation_warnings=context.warnings,
            evidence_registry=context.evidence_registry,
            slides=slides,
        )
        EvidenceRegistry.from_bundle(bundle, context.evidence_registry).validate_deck_plan(deck_plan)
        return deck_plan

    @staticmethod
    def _deck_title(context: FindingsContext) -> str:
        if context.project_name:
            return f"{context.project_name} Evidence-Backed Report"
        return "Evidence-Backed Wave Report"

    @staticmethod
    def _project_context(context: FindingsContext) -> str:
        parts = [
            part for part in (
                context.project_name,
                context.study_name,
                context.industry_name,
            )
            if part
        ]
        if parts:
            return "Context: " + " | ".join(parts) + "."
        return "Context comes from the completed wave metadata."

    @staticmethod
    def _quality_line(context: FindingsContext) -> str:
        quality = context.quality_summary
        concept = quality.get("concept")
        weighted_score = quality.get("weighted_score")
        if concept and weighted_score is not None:
            return f"Quality concept: {concept}; weighted score: {weighted_score}."
        if concept:
            return f"Quality concept: {concept}."
        if weighted_score is not None:
            return f"Weighted score: {weighted_score}."
        return "Quality metadata is present in the source wave."
