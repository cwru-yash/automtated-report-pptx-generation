from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SlideType = Literal[
    "title",
    "overview",
    "context",
    "data_quality",
    "finding",
    "recommendation",
    "limitation",
    "conclusion",
]


class DeckDataQualityError(ValueError):
    """Raised when source wave data is not strong enough for a client deck."""


class DeckValidationError(ValueError):
    """Raised when a planned deck makes claims unsupported by the evidence."""


class EvidenceItem(BaseModel):
    label: str
    value: float | int | str
    source: str


class Finding(BaseModel):
    title: str
    finding: str
    evidence: list[str] = Field(default_factory=list)
    why_it_matters: str
    confidence: Literal["high", "medium", "low"] = "medium"
    chart_refs: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class DeckSlide(BaseModel):
    slide_number: int
    slide_type: SlideType
    title: str
    subtitle: str = ""
    bullets: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    chart_refs: list[str] = Field(default_factory=list)
    speaker_notes: str = ""
    source_refs: list[str] = Field(default_factory=list)


class DeckPlan(BaseModel):
    deck_title: str
    subtitle: str
    audience: str = "executive stakeholders"
    tone: str = "consulting"
    source_wave_id: str
    source_project: str = ""
    validation_status: Literal["valid", "invalid"] = "valid"
    validation_warnings: list[str] = Field(default_factory=list)
    evidence_registry: list[EvidenceItem] = Field(default_factory=list)
    slides: list[DeckSlide] = Field(default_factory=list)

    def as_sections(self) -> dict[str, str]:
        """Map the richer slide plan into the current five-section HTML/PPT slots."""
        finding_slides = [
            slide for slide in self.slides if slide.slide_type == "finding"
        ]
        first_finding = finding_slides[0] if finding_slides else None
        weak_link_finding = next(
            (slide for slide in finding_slides if "achilles" in slide.title.lower()),
            first_finding,
        )
        recommendation = next(
            (slide for slide in self.slides if slide.slide_type == "recommendation"),
            None,
        )
        data_quality = next(
            (slide for slide in self.slides if slide.slide_type == "data_quality"),
            None,
        )
        overview = next(
            (slide for slide in self.slides if slide.slide_type == "overview"),
            None,
        )

        return {
            "exec_summary": self._slide_summary(first_finding)
            or f"{self.deck_title}: {self.subtitle}",
            "methodology": self._slide_summary(data_quality)
            or "Generated from completed wave data and approved analysis outputs.",
            "brand_health": self._slide_summary(overview)
            or "The deck is grounded in the completed analytical wave.",
            "weak_links": self._slide_summary(weak_link_finding)
            or "No weak-link slide was generated.",
            "takeaways": self._slide_summary(recommendation)
            or "Review the evidence-backed findings and next steps.",
        }

    @staticmethod
    def _slide_summary(slide: DeckSlide | None) -> str:
        if slide is None:
            return ""
        parts = [slide.title]
        if slide.bullets:
            parts.append("; ".join(slide.bullets[:3]))
        if slide.evidence:
            parts.append("Evidence: " + "; ".join(slide.evidence[:2]))
        return ". ".join(part for part in parts if part)


class FindingsContext(BaseModel):
    wave_id: str
    project_name: str = ""
    study_name: str = ""
    industry_name: str = ""
    reference_period: dict[str, Any] = Field(default_factory=dict)
    quality_summary: dict[str, Any] = Field(default_factory=dict)
    gold_row_count: int = 0
    complete_analysis_count: int = 0
    findings: list[Finding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_registry: list[EvidenceItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
