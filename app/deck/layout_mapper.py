from __future__ import annotations

import re
from uuid import uuid4

from app.deck.schema import DeckPlan, DeckSlide
from app.deck.layout_schema import (
    ContentBlock,
    DeckColumn,
    DeckDocument,
    DeckSlideDocument,
    DeckTheme,
)


ACTIVITY_CODE_RE = re.compile(r"\b[A-Z]{1,4}-?\d{1,4}\b")


class DeckLayoutMapper:
    """Convert a validated DeckPlan into editable recursive deck JSON."""

    def from_deck_plan(self, deck_plan: DeckPlan, *, deck_id: str | None = None) -> DeckDocument:
        slides = [
            self._title_slide(deck_plan),
            self._executive_summary_slide(deck_plan),
        ]
        for slide in deck_plan.slides:
            if slide.slide_type == "title":
                continue
            slides.append(self._map_slide(slide))

        return DeckDocument(
            deck_id=deck_id or f"deck_{uuid4()}",
            title=deck_plan.deck_title,
            source_wave_id=deck_plan.source_wave_id,
            source_project=deck_plan.source_project,
            theme=DeckTheme(),
            slides=slides,
            metadata={
                "audience": deck_plan.audience,
                "tone": deck_plan.tone,
                "validation_warnings": deck_plan.validation_warnings,
                "source": "deck_plan",
            },
        )

    def demo_deck(self) -> DeckDocument:
        return DeckDocument(
            deck_id="demo_recursive_deck",
            title="Evidence-Backed Report Deck",
            source_wave_id="demo-wave",
            source_project="Demo Project",
            slides=[
                DeckSlideDocument(
                    id="slide_demo_title",
                    type="title",
                    title="Evidence-Backed Report Deck",
                    speaker_notes="Demo deck showing recursive editable layout blocks.",
                    content=[
                        self._heading("block_demo_h1", "Evidence-Backed Report Deck", level=1),
                        self._paragraph(
                            "block_demo_p1",
                            "A recursive JSON deck rendered by the editable slide canvas.",
                        ),
                    ],
                ),
                DeckSlideDocument(
                    id="slide_demo_finding",
                    type="finding",
                    title="Weak-link evidence should drive the first remediation priority",
                    content=[
                        self._two_column(
                            "block_demo_columns",
                            left=[
                                self._chart("block_demo_chart", "chart_6", "Achilles heel chart"),
                                self._metric("block_demo_metric", "Focus score", "56.25", "Source: analysis_6"),
                            ],
                            right=[
                                self._heading("block_demo_h2", "Analyst interpretation", level=2),
                                self._bullets(
                                    "block_demo_bullets",
                                    [
                                        "Treat the weakest activity as the first operating question.",
                                        "Use the evidence registry before adding new numeric claims.",
                                        "Keep recommendations tied to source analyses.",
                                    ],
                                ),
                                self._source("block_demo_source", "Source: demo recursive deck fixture."),
                            ],
                        )
                    ],
                ),
            ],
        )

    def _title_slide(self, deck_plan: DeckPlan) -> DeckSlideDocument:
        return DeckSlideDocument(
            id="slide_title",
            type="title",
            title=deck_plan.deck_title,
            speaker_notes="Open with the business question and explain the evidence standard.",
            content=[
                self._heading("block_title_heading", deck_plan.deck_title, level=1),
                self._paragraph("block_title_subtitle", deck_plan.subtitle),
                self._source(
                    "block_title_source",
                    f"Source wave: {deck_plan.source_wave_id}",
                ),
            ],
        )

    def _executive_summary_slide(self, deck_plan: DeckPlan) -> DeckSlideDocument:
        finding_slides = [slide for slide in deck_plan.slides if slide.slide_type == "finding"]
        recommendation = next(
            (slide for slide in deck_plan.slides if slide.slide_type == "recommendation"),
            None,
        )
        metrics = [
            self._metric(
                f"block_summary_metric_{index}",
                item.label,
                str(item.value),
                item.source,
            )
            for index, item in enumerate(deck_plan.evidence_registry[:3], start=1)
        ]
        if not metrics:
            metrics = [
                self._metric(
                    "block_summary_metric_1",
                    "Evidence status",
                    deck_plan.validation_status,
                    "Deck validation",
                )
            ]

        return DeckSlideDocument(
            id="slide_executive_summary",
            type="executive_summary",
            title="Executive summary: what the evidence says",
            speaker_notes="Summarize the decision logic before going into findings.",
            content=[
                self._two_column(
                    "block_summary_columns",
                    left=metrics,
                    right=[
                        self._heading("block_summary_heading", "Top analyst takeaways", level=2),
                        self._bullets(
                            "block_summary_bullets",
                            [
                                self._takeaway_title(slide)
                                for slide in finding_slides[:3]
                            ]
                            or ["No finding slides were generated."],
                        ),
                        self._bullets(
                            "block_summary_recommendations",
                            recommendation.bullets[:3] if recommendation else ["No recommendations generated."],
                        ),
                    ],
                )
            ],
        )

    def _map_slide(self, slide: DeckSlide) -> DeckSlideDocument:
        title = self._takeaway_title(slide)
        if slide.slide_type == "finding":
            content = [
                self._two_column(
                    f"block_{slide.slide_number}_columns",
                    left=self._finding_left_blocks(slide),
                    right=self._finding_right_blocks(slide),
                )
            ]
        elif slide.slide_type == "recommendation":
            content = [
                self._heading(f"block_{slide.slide_number}_heading", title, level=2),
                self._bullets(f"block_{slide.slide_number}_bullets", slide.bullets),
                self._source(f"block_{slide.slide_number}_source", "Generated from validated findings."),
            ]
        elif slide.slide_type == "data_quality":
            content = [
                self._heading(f"block_{slide.slide_number}_heading", title, level=2),
                self._bullets(f"block_{slide.slide_number}_bullets", slide.bullets),
                *[
                    self._metric(
                        f"block_{slide.slide_number}_evidence_{index}",
                        f"Evidence {index}",
                        evidence,
                        "Data quality gate",
                    )
                    for index, evidence in enumerate(slide.evidence[:3], start=1)
                ],
            ]
        else:
            content = [
                self._heading(f"block_{slide.slide_number}_heading", title, level=2),
                self._bullets(f"block_{slide.slide_number}_bullets", slide.bullets),
            ]

        return DeckSlideDocument(
            id=f"slide_{slide.slide_number}",
            type=self._slide_type(slide),
            title=title,
            speaker_notes=slide.speaker_notes,
            content=content,
            source_refs=slide.source_refs,
        )

    def _finding_left_blocks(self, slide: DeckSlide) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        if slide.chart_refs:
            blocks.append(
                self._chart(
                    f"block_{slide.slide_number}_chart",
                    slide.chart_refs[0],
                    slide.title,
                )
            )
        for index, evidence in enumerate(slide.evidence[:3], start=1):
            blocks.append(
                self._metric(
                    f"block_{slide.slide_number}_metric_{index}",
                    f"Evidence {index}",
                    evidence,
                    "Validated deck plan",
                )
            )
        if not blocks:
            blocks.append(
                self._source(
                    f"block_{slide.slide_number}_source_left",
                    "No chart or metric evidence attached to this slide.",
                )
            )
        return blocks

    def _finding_right_blocks(self, slide: DeckSlide) -> list[ContentBlock]:
        bullets = [item for item in slide.bullets if item not in slide.evidence]
        return [
            self._heading(f"block_{slide.slide_number}_insight_heading", "Analyst interpretation", level=2),
            self._bullets(f"block_{slide.slide_number}_insight_bullets", bullets[:3] or slide.bullets[:3]),
            self._source(
                f"block_{slide.slide_number}_source",
                ", ".join(slide.source_refs) if slide.source_refs else "Source: validated deck plan.",
            ),
        ]

    @staticmethod
    def _slide_type(slide: DeckSlide):
        if slide.slide_type == "overview":
            return "context"
        if slide.slide_type == "data_quality":
            return "context"
        if slide.slide_type == "conclusion":
            return "appendix"
        return slide.slide_type

    def _takeaway_title(self, slide: DeckSlide) -> str:
        if slide.slide_type != "finding":
            return slide.title
        text = " ".join([slide.title, *slide.bullets, *slide.evidence])
        code = self._first_activity_code(text)
        lower = slide.title.lower()
        if code and "achilles" in lower:
            return f"{code} is the clearest execution gap and should be remediated first"
        if code and "best of best" in lower:
            return f"{code} anchors the largest benchmark gap to close"
        if "industry curve" in lower or "category curve" in lower:
            return "The category curve shows where performance is structurally uneven"
        if "quality" in lower:
            return "The source wave is strong enough for client-facing synthesis"
        if "experience baseline" in lower:
            return "Customer experience has a measurable baseline for prioritization"
        return slide.title

    @staticmethod
    def _first_activity_code(text: str) -> str:
        match = ACTIVITY_CODE_RE.search(text)
        return match.group(0) if match else ""

    @staticmethod
    def _heading(block_id: str, text: str, *, level: int) -> ContentBlock:
        return ContentBlock(id=block_id, type="heading", level=level, text=text)

    @staticmethod
    def _paragraph(block_id: str, text: str) -> ContentBlock:
        return ContentBlock(id=block_id, type="paragraph", text=text)

    @staticmethod
    def _bullets(block_id: str, items: list[str]) -> ContentBlock:
        clean_items = [item for item in items if item]
        return ContentBlock(id=block_id, type="bullet_list", items=clean_items or ["No bullets generated."])

    @staticmethod
    def _metric(block_id: str, label: str, value: str | int | float, helper: str = "") -> ContentBlock:
        return ContentBlock(
            id=block_id,
            type="metric_card",
            label=label,
            value=value,
            helper=helper,
        )

    @staticmethod
    def _chart(block_id: str, chart_ref: str, title: str) -> ContentBlock:
        return ContentBlock(
            id=block_id,
            type="chart_placeholder",
            chart_ref=chart_ref,
            title=title,
        )

    @staticmethod
    def _source(block_id: str, text: str) -> ContentBlock:
        return ContentBlock(id=block_id, type="source_note", text=text)

    @staticmethod
    def _two_column(
        block_id: str,
        *,
        left: list[ContentBlock],
        right: list[ContentBlock],
    ) -> ContentBlock:
        return ContentBlock(
            id=block_id,
            type="two_column",
            columns=[
                DeckColumn(width=48, content=left),
                DeckColumn(width=52, content=right),
            ],
        )
