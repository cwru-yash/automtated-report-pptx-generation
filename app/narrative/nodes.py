import json
import logging
import os
import re
from typing import Any, Dict

from app.bundle.schema import AnalysisBundle
from app.config import settings
from app.narrative.guardrails import FactGuardrail

logger = logging.getLogger(__name__)


SECTION_SPECS: Dict[str, Dict[str, str]] = {
    "exec_summary": {
        "title": "Executive Summary",
        "job": "Synthesize the strongest business implication across all available metrics.",
    },
    "methodology": {
        "title": "Methodology",
        "job": "Explain that this is generated from the canonical Decomposer analysis bundle without inventing new calculations.",
    },
    "brand_health": {
        "title": "Brand Health",
        "job": "Interpret awareness and NPS as an overall read on brand performance.",
    },
    "weak_links": {
        "title": "Weak Links",
        "job": "Identify the practical friction points and connect them to the CVC score.",
    },
    "takeaways": {
        "title": "Key Takeaways",
        "job": "Turn the findings into crisp next actions for a client-facing discussion.",
    },
}

LANGUAGE_NAMES = {
    "en-US": "English",
    "pt-BR": "Brazilian Portuguese",
    "es-MX": "Mexican Spanish",
    "ko-KR": "Korean",
    "zh-CN": "Simplified Chinese",
}


def _language_name(language: str) -> str:
    return LANGUAGE_NAMES.get(language, language)


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


def _json_from_text(text: str) -> Dict[str, str]:
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    return json.loads(cleaned)


def _bundle_context(bundle: AnalysisBundle) -> str:
    return json.dumps(
        {
            "wave_id": bundle.wave_id,
            "language": bundle.language,
            "metrics": bundle.metrics,
            "analysis_results": bundle.analysis_results,
        },
        ensure_ascii=False,
        indent=2,
    )


def _metric_summary(bundle: AnalysisBundle) -> str:
    labels = {
        "nps": "NPS",
        "brand_awareness": "brand awareness",
        "cvc_score": "CVC score",
        "weighted_score": "weighted score",
        "concept_points": "quality concept points",
        "briefing_adherence_pct": "briefing adherence",
        "average_satisfaction_index": "average satisfaction index",
        "total_review_count": "total review count",
    }
    parts = [
        f"{labels.get(key, key.replace('_', ' '))} {value}"
        for key, value in bundle.metrics.items()
    ]
    return ", ".join(parts) or "the approved qualitative analysis outputs"


def _analysis_result(bundle: AnalysisBundle, key: str) -> Dict[str, Any]:
    analysis = bundle.analysis_results.get(key) or {}
    result = analysis.get("result") if isinstance(analysis, dict) else {}
    return result or {}


def _top_best_of_best_gaps(bundle: AnalysisBundle, limit: int = 3) -> list[dict]:
    activities = _analysis_result(bundle, "analysis_7").get("activities") or []
    return sorted(
        [item for item in activities if item.get("gap") is not None],
        key=lambda item: item.get("gap", 0),
        reverse=True,
    )[:limit]


def _achilles_links(bundle: AnalysisBundle) -> list[dict]:
    return _analysis_result(bundle, "analysis_6").get("links") or []


def _industry_curve_extremes(bundle: AnalysisBundle) -> tuple[dict | None, dict | None]:
    activities = _analysis_result(bundle, "analysis_1").get("activities") or []
    scored = [item for item in activities if item.get("industry_avg") is not None]
    if not scored:
        return None, None
    return (
        max(scored, key=lambda item: item.get("industry_avg", 0)),
        min(scored, key=lambda item: item.get("industry_avg", 0)),
    )


def _fallback_section(section_key: str, bundle: AnalysisBundle) -> Dict[str, str]:
    metric_summary = _metric_summary(bundle)
    cvc = bundle.metrics.get("cvc_score")
    avg_satisfaction = bundle.metrics.get("average_satisfaction_index")
    quality_points = bundle.metrics.get("concept_points")
    review_count = bundle.metrics.get("total_review_count")
    weak_links = ", ".join(bundle.analysis_results.get("weak_links", [])) or "known friction points"
    strong_links = ", ".join(bundle.analysis_results.get("strong_links", [])) or "the strongest completed analyses"
    takeaways = ", ".join(bundle.analysis_results.get("takeaways", [])) or "prioritized action planning"
    best_gaps = _top_best_of_best_gaps(bundle)
    achilles = _achilles_links(bundle)
    strongest_activity, weakest_activity = _industry_curve_extremes(bundle)

    if best_gaps:
        takeaways = ", ".join(str(item.get("activity_code")) for item in best_gaps)

    if achilles:
        weak_links = ", ".join(str(item.get("activity_code")) for item in achilles)

    brand_health_text = (
        f"Brand Health: The approved metrics currently available are {metric_summary}. "
        "This means the brand health read should stay anchored to the quality record "
        "and completed analysis outputs, rather than inventing missing survey metrics."
    )
    brand_health_ppt = f"Brand health is grounded in {metric_summary}."
    if avg_satisfaction is not None:
        review_clause = f" across {int(review_count)} reviews" if review_count else ""
        quality_clause = f" with quality points at {quality_points}" if quality_points is not None else ""
        brand_health_text = (
            f"Brand Health: Average satisfaction index is {avg_satisfaction}{review_clause}{quality_clause}. "
            "This gives the report a real experience baseline to interpret alongside "
            "the quality record and the completed analysis outputs."
        )
        brand_health_ppt = f"Average satisfaction index is {avg_satisfaction}."

    if strongest_activity and weakest_activity:
        curve_sentence = (
            f"The industry curve peaks at {strongest_activity.get('activity_code')} "
            f"({strongest_activity.get('industry_avg')}) and bottoms at "
            f"{weakest_activity.get('activity_code')} ({weakest_activity.get('industry_avg')})."
        )
    else:
        curve_sentence = "The completed analyses identify where the value chain performs strongest and weakest."

    if achilles:
        primary = achilles[0]
        weak_links_report = (
            f"Weak Links: {primary.get('activity_code')} is the clearest vulnerability. "
            f"The focus brand scores {primary.get('brand_score')} against an industry average "
            f"of {primary.get('industry_avg')}, a gap of {primary.get('delta')}. "
            "This is the first operational area to inspect before broadening the improvement plan."
        )
        weak_links_ppt = (
            f"{primary.get('activity_code')}: focus brand {primary.get('brand_score')} "
            f"vs industry {primary.get('industry_avg')}."
        )
    else:
        weak_links_report = (
            f"Weak Links: The highest-priority friction areas are {weak_links}. "
            "These are the operational points most likely to suppress satisfaction "
            "or weaken the customer's experience across the value chain."
        )
        weak_links_ppt = (
            f"CVC {cvc} points to friction around {weak_links}."
            if cvc is not None
            else f"Weak-link evidence points to friction around {weak_links}."
        )

    if best_gaps:
        gap_text = ", ".join(
            f"{item.get('activity_code')} gap {item.get('gap')}"
            for item in best_gaps
        )
        takeaways_report = (
            f"Key Takeaways: Prioritize closing the largest Best of Best gaps: {gap_text}. "
            "These activities show where the category leader is setting a higher bar than "
            "the focus brand, and they give the team a practical sequence for improvement."
        )
        takeaways_ppt = f"Close the largest gaps first: {gap_text}."
    else:
        takeaways_report = (
            f"Key Takeaways: The recommended actions are {takeaways}. The strongest "
            f"positive evidence is {strong_links}, while the weak-link evidence shows "
            "where execution should improve first."
        )
        takeaways_ppt = f"Prioritize {takeaways} while protecting {strong_links}."

    fallback = {
        "exec_summary": {
            "report_text": (
                f"Executive Summary: The wave's approved metrics are {metric_summary}. "
                f"{curve_sentence} The most actionable weakness is {weak_links}, while "
                "the Best of Best comparison shows where the focus brand can close the "
                "largest competitive experience gaps."
            ),
            "ppt_text": f"Avg satisfaction {avg_satisfaction}; priority gap area: {weak_links}.",
        },
        "methodology": {
            "report_text": (
                "Methodology: This report was assembled from the canonical analysis bundle. "
                f"The narrative uses only approved bundle metrics such as {metric_summary}, "
                "plus completed analysis results and provenance metadata from the source data."
            ),
            "ppt_text": f"Generated from approved bundle metrics: {metric_summary}.",
        },
        "brand_health": {
            "report_text": brand_health_text,
            "ppt_text": brand_health_ppt,
        },
        "weak_links": {
            "report_text": weak_links_report,
            "ppt_text": weak_links_ppt,
        },
        "takeaways": {
            "report_text": takeaways_report,
            "ppt_text": takeaways_ppt,
        },
    }
    return fallback[section_key]


async def _call_llm(section_key: str, bundle: AnalysisBundle, retry_note: str = "") -> Dict[str, str]:
    from litellm import acompletion

    spec = SECTION_SPECS[section_key]
    language = _language_name(bundle.language)
    metric_values = ", ".join(str(value) for value in bundle.metrics.values())
    retry_clause = f"\nValidation feedback to fix: {retry_note}" if retry_note else ""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior analytics storyteller generating client-ready report copy. "
                "Use only facts present in the provided analysis bundle. Do not invent metrics, "
                "percentages, rankings, dates, sample sizes, or claims."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Write the {spec['title']} section in {language}.\n"
                f"Section job: {spec['job']}\n"
                f"Return only valid JSON with exactly these keys: report_text, ppt_text.\n"
                "report_text must be 80-120 words. ppt_text must be a single slide-ready "
                "sentence under 28 words.\n"
                f"If you use numbers, use only these exact numeric values: {metric_values}.\n"
                "Keep numeric formatting exactly as provided, even in non-English languages.\n"
                "Do not use markdown or bullet points.\n"
                f"{retry_clause}\n\n"
                f"Analysis bundle:\n{_bundle_context(bundle)}"
            ),
        },
    ]

    litellm_model = _litellm_model(settings.LLM_MODEL)
    completion_kwargs: Dict[str, Any] = {
        "model": litellm_model,
        "messages": messages,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "timeout": settings.LLM_TIMEOUT_SECONDS,
    }
    if litellm_model.startswith("anthropic/") and settings.ANTHROPIC_API_KEY:
        completion_kwargs["api_key"] = settings.ANTHROPIC_API_KEY
    elif lowered := litellm_model.lower():
        if lowered.startswith(("gpt-", "o1", "o3", "o4", "openai/")) and settings.OPENAI_API_KEY:
            completion_kwargs["api_key"] = settings.OPENAI_API_KEY
    if settings.LLM_API_BASE:
        completion_kwargs["api_base"] = settings.LLM_API_BASE
    elif litellm_model.startswith("anthropic/"):
        completion_kwargs["api_base"] = "https://api.anthropic.com"

    response = await acompletion(**completion_kwargs)
    content = response.choices[0].message.content
    parsed = _json_from_text(content)
    return {
        "report_text": str(parsed["report_text"]).strip(),
        "ppt_text": str(parsed["ppt_text"]).strip(),
    }


async def generate_section(section_key: str, state: dict) -> dict:
    bundle: AnalysisBundle = state["bundle"]
    use_llm = state.get("use_llm", True)
    require_llm = state.get("require_llm", False)
    errors = []
    metadata: Dict[str, Any] = {
        "mode": "fallback",
        "model": settings.LLM_MODEL if use_llm else None,
        "language": bundle.language,
    }

    pair: Dict[str, str]
    if use_llm and _llm_configured(settings.LLM_MODEL):
        try:
            pair = await _call_llm(section_key, bundle)
            valid_report, report_error = FactGuardrail.evaluate(pair["report_text"], bundle)
            valid_ppt, ppt_error = FactGuardrail.evaluate(pair["ppt_text"], bundle)
            if not (valid_report and valid_ppt):
                retry_note = "; ".join(error for error in [report_error, ppt_error] if error)
                pair = await _call_llm(section_key, bundle, retry_note=retry_note)
            metadata["mode"] = "llm"
        except Exception as exc:
            logger.warning("LLM generation failed for section %s: %s", section_key, exc)
            metadata["mode"] = "error" if require_llm else "fallback"
            if require_llm:
                return {
                    "sections": {section_key: ""},
                    "ppt_sections": {section_key: ""},
                    "errors": [{section_key: f"LLM generation failed: {exc}"}],
                    "llm_metadata": {section_key: metadata},
                }
            errors.append({section_key: f"LLM fallback used: {exc}"})
            pair = _fallback_section(section_key, bundle)
    else:
        if require_llm:
            return {
                "sections": {section_key: ""},
                "ppt_sections": {section_key: ""},
                "errors": [
                    {
                        section_key: (
                            "LLM generation required but no compatible API key is configured "
                            f"for model '{settings.LLM_MODEL}'."
                        )
                    }
                ],
                "llm_metadata": {section_key: metadata},
            }
        pair = _fallback_section(section_key, bundle)

    for target_key in ("report_text", "ppt_text"):
        is_valid, error_msg = FactGuardrail.evaluate(pair[target_key], bundle)
        if not is_valid:
            errors.append({section_key: f"{target_key} failed fact guardrail: {error_msg}"})

    return {
        "sections": {section_key: pair["report_text"]},
        "ppt_sections": {section_key: pair["ppt_text"]},
        "errors": errors,
        "llm_metadata": {section_key: metadata},
    }


async def generate_exec_summary(state: dict):
    return await generate_section("exec_summary", state)


async def generate_methodology(state: dict):
    return await generate_section("methodology", state)


async def generate_brand_health(state: dict):
    return await generate_section("brand_health", state)


async def generate_weak_links(state: dict):
    return await generate_section("weak_links", state)


async def generate_takeaways(state: dict):
    return await generate_section("takeaways", state)
