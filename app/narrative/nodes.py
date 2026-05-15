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


def _fallback_section(section_key: str, bundle: AnalysisBundle) -> Dict[str, str]:
    nps = bundle.metrics.get("nps", 0)
    awareness = bundle.metrics.get("brand_awareness", 0)
    cvc = bundle.metrics.get("cvc_score", 0)
    weak_links = ", ".join(bundle.analysis_results.get("weak_links", [])) or "known friction points"
    takeaways = ", ".join(bundle.analysis_results.get("takeaways", [])) or "prioritized action planning"

    fallback = {
        "exec_summary": {
            "report_text": (
                f"Executive Summary: The wave shows NPS at {nps}, brand awareness at "
                f"{awareness}, and CVC score at {cvc}. The pattern suggests a brand with "
                "solid visibility but clear room to convert that visibility into stronger "
                "customer advocacy."
            ),
            "ppt_text": f"NPS {nps}, awareness {awareness}, CVC {cvc}: visibility is ahead of advocacy.",
        },
        "methodology": {
            "report_text": (
                f"Methodology: This report was assembled from the canonical analysis bundle "
                f"for wave {bundle.wave_id}. The narrative uses only approved bundle metrics "
                f"such as NPS {nps}, awareness {awareness}, and CVC {cvc}."
            ),
            "ppt_text": f"Generated from wave {bundle.wave_id} using approved bundle metrics only.",
        },
        "brand_health": {
            "report_text": (
                f"Brand Health: Awareness is {awareness}, while NPS is {nps}. This indicates "
                "that recognition is present, but the experience still needs to create more "
                "active recommendation and loyalty."
            ),
            "ppt_text": f"Awareness {awareness} is stronger than advocacy at NPS {nps}.",
        },
        "weak_links": {
            "report_text": (
                f"Weak Links: With CVC at {cvc}, the highest-priority friction areas are "
                f"{weak_links}. These are the operational points most likely to suppress "
                "conversion from awareness into stronger satisfaction."
            ),
            "ppt_text": f"CVC {cvc} points to friction around {weak_links}.",
        },
        "takeaways": {
            "report_text": (
                f"Key Takeaways: The recommended actions are {takeaways}. The immediate goal "
                f"is to protect awareness at {awareness} while improving NPS {nps} through "
                "more consistent customer experience execution."
            ),
            "ppt_text": f"Prioritize {takeaways} to turn awareness {awareness} into NPS {nps} gains.",
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
