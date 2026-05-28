from __future__ import annotations

import json
import os
import re
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.config import settings
from app.deck.schema import FindingsContext


SuggestedVisualType = Literal[
    "title",
    "executive_summary",
    "section_divider",
    "line_chart",
    "bar_chart",
    "stacked_bar",
    "table",
    "metric_cards",
    "comparison_matrix",
    "journey_map",
    "quadrant",
    "waterfall",
    "quote_callout",
    "insight_slide",
    "recommendation_slide",
    "appendix",
]


class AIOutlineError(ValueError):
    """Raised when AI outline generation cannot safely produce a validated outline."""


class AIOutlineProviderNotConfigured(AIOutlineError):
    """Raised when the AI outline provider is disabled or missing credentials."""


class DeckOutlineSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    purpose: str
    key_message: str
    evidence_refs: list[str] = Field(default_factory=list)
    suggested_visual_type: SuggestedVisualType = "insight_slide"

    @model_validator(mode="after")
    def require_content(self) -> "DeckOutlineSlide":
        if not self.title.strip():
            raise ValueError("slide title is required")
        if not self.purpose.strip():
            raise ValueError("slide purpose is required")
        if not self.key_message.strip():
            raise ValueError("slide key_message is required")
        return self


class DeckOutline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deck_title: str
    audience: str = "executive stakeholders"
    objective: str
    source_wave_id: str
    slides: list[DeckOutlineSlide] = Field(default_factory=list, min_length=1)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_title_and_objective(self) -> "DeckOutline":
        if not self.deck_title.strip():
            raise ValueError("deck_title is required")
        if not self.objective.strip():
            raise ValueError("objective is required")
        return self


class AIOutlineProvider(Protocol):
    async def generate_outline(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return raw provider output. Caller validates it before use."""


class DisabledAIOutlineProvider:
    async def generate_outline(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise AIOutlineProviderNotConfigured(
            "AI outline provider is not configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable it."
        )


class LiteLLMAIOutlineProvider:
    async def generate_outline(self, payload: dict[str, Any]) -> dict[str, Any]:
        from litellm import acompletion

        model = _litellm_model(settings.LLM_MODEL)
        completion_kwargs: dict[str, Any] = {
            "model": model,
            "messages": _outline_messages(payload),
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "timeout": settings.LLM_TIMEOUT_SECONDS,
        }
        if model.startswith("anthropic/") and settings.ANTHROPIC_API_KEY:
            completion_kwargs["api_key"] = settings.ANTHROPIC_API_KEY
        elif model.lower().startswith(("gpt-", "o1", "o3", "o4", "openai/")) and settings.OPENAI_API_KEY:
            completion_kwargs["api_key"] = settings.OPENAI_API_KEY
        if settings.LLM_API_BASE:
            completion_kwargs["api_base"] = settings.LLM_API_BASE
        elif model.startswith("anthropic/"):
            completion_kwargs["api_base"] = "https://api.anthropic.com"

        response = await acompletion(**completion_kwargs)
        content = response.choices[0].message.content
        return _json_from_text(content)


def get_ai_outline_provider() -> AIOutlineProvider:
    if not _llm_configured(settings.LLM_MODEL):
        return DisabledAIOutlineProvider()
    return LiteLLMAIOutlineProvider()


async def generate_ai_outline(
    context: FindingsContext,
    *,
    provider: AIOutlineProvider | None = None,
    audience: str = "executive stakeholders",
) -> DeckOutline:
    selected_provider = provider or get_ai_outline_provider()
    payload = _outline_payload(context, audience=audience)
    try:
        raw = await selected_provider.generate_outline(payload)
        outline = DeckOutline.model_validate(raw)
    except AIOutlineProviderNotConfigured:
        raise
    except ValidationError as exc:
        raise AIOutlineError(f"AI outline output failed schema validation: {exc}") from exc
    except Exception as exc:
        raise AIOutlineError(f"AI outline generation failed: {exc}") from exc

    validate_outline_evidence(outline, context)
    return outline


def validate_outline_evidence(outline: DeckOutline, context: FindingsContext) -> DeckOutline:
    """Re-check outline evidence refs against the extracted findings context."""
    _validate_outline_evidence(outline, context)
    return outline


def _validate_outline_evidence(outline: DeckOutline, context: FindingsContext) -> None:
    allowed_refs = _allowed_evidence_refs(context)
    warnings = list(outline.warnings)
    invalid_refs: list[str] = []
    missing_ref_slides: list[str] = []

    for slide in outline.slides:
        if slide.suggested_visual_type != "title" and not slide.evidence_refs:
            missing_ref_slides.append(slide.title)
        for ref in slide.evidence_refs:
            if ref not in allowed_refs:
                invalid_refs.append(ref)

    if invalid_refs:
        refs = ", ".join(sorted(set(invalid_refs)))
        raise AIOutlineError(f"AI outline referenced evidence not present in findings context: {refs}")
    if missing_ref_slides:
        warnings.append(
            "Slides missing evidence refs: " + ", ".join(missing_ref_slides)
        )
    outline.warnings = warnings


def _allowed_evidence_refs(context: FindingsContext) -> set[str]:
    refs = {context.wave_id}
    for index, finding in enumerate(context.findings, start=1):
        refs.add(f"finding_{index}")
        refs.update(finding.source_refs)
        refs.update(finding.chart_refs)
    for item in context.evidence_registry:
        refs.add(item.source)
        refs.add(item.label)
    return {ref for ref in refs if ref}


def _outline_payload(context: FindingsContext, *, audience: str) -> dict[str, Any]:
    return {
        "wave_id": context.wave_id,
        "project_name": context.project_name,
        "study_name": context.study_name,
        "industry_name": context.industry_name,
        "audience": audience,
        "available_evidence_refs": sorted(_allowed_evidence_refs(context)),
        "findings": [
            {
                "id": f"finding_{index}",
                "title": finding.title,
                "finding": finding.finding,
                "evidence": finding.evidence,
                "why_it_matters": finding.why_it_matters,
                "source_refs": finding.source_refs,
                "chart_refs": finding.chart_refs,
            }
            for index, finding in enumerate(context.findings, start=1)
        ],
        "recommendations": context.recommendations,
        "limitations": context.limitations,
    }


def _outline_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You create executive deck outlines from validated analytical findings. "
                "Return only JSON matching the requested schema. Do not invent evidence refs."
            ),
        },
        {
            "role": "user",
            "content": (
                "Create a deck outline using this schema: "
                "{deck_title, audience, objective, source_wave_id, slides, warnings}. "
                "Each slide must have title, purpose, key_message, evidence_refs, suggested_visual_type. "
                "Use only available_evidence_refs for evidence_refs. Do not create slide layout blocks.\n\n"
                f"Context:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def _llm_configured(model: str) -> bool:
    lowered = model.lower()
    if "claude" in lowered or "anthropic" in lowered:
        return bool(settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY"))
    if lowered.startswith(("gpt-", "o1", "o3", "o4", "openai/")):
        return bool(settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"))
    return bool(
        settings.ANTHROPIC_API_KEY
        or settings.OPENAI_API_KEY
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )


def _litellm_model(model: str) -> str:
    lowered = model.lower()
    if "/" in model:
        return model
    if "claude" in lowered:
        return f"anthropic/{model}"
    return model


def _json_from_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    return json.loads(cleaned)
