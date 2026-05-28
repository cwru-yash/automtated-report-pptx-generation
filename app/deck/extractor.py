from __future__ import annotations

from typing import Any

from app.bundle.schema import AnalysisBundle
from app.deck.schema import (
    DeckDataQualityError,
    EvidenceItem,
    Finding,
    FindingsContext,
)


class FindingExtractor:
    """Extract deterministic, evidence-backed findings from a completed wave."""

    def extract(
        self,
        bundle: AnalysisBundle,
        wave_data: dict[str, Any],
        *,
        allow_partial: bool = False,
    ) -> FindingsContext:
        gold_rows = (wave_data.get("gold") or {}).get("activity") or []
        complete_analyses = self._complete_analyses_with_results(wave_data)

        if not gold_rows and not allow_partial:
            raise DeckDataQualityError(
                "Deck generation blocked: the wave has no gold activity rows."
            )
        if not complete_analyses and not allow_partial:
            raise DeckDataQualityError(
                "Deck generation blocked: the wave has no completed analysis results."
            )
        if not bundle.analysis_results and not allow_partial:
            raise DeckDataQualityError(
                "Deck generation blocked: the assembled analysis bundle is empty."
            )

        wave = wave_data.get("wave") or {}
        project = wave.get("project") or {}
        study = wave.get("study") or {}
        industry = wave.get("industry") or {}
        quality = wave_data.get("quality") or {}

        context = FindingsContext(
            wave_id=bundle.wave_id,
            project_name=str(project.get("name") or ""),
            study_name=str(study.get("name") or ""),
            industry_name=str(industry.get("name") or ""),
            reference_period=wave.get("reference_period") or {},
            quality_summary=quality,
            gold_row_count=len(gold_rows),
            complete_analysis_count=len(complete_analyses),
            evidence_registry=self._evidence_items(
                bundle,
                wave_data,
                len(gold_rows),
                len(complete_analyses),
            ),
            warnings=self._analysis_warnings(wave_data),
        )

        context.findings.extend(self._baseline_findings(bundle))
        context.findings.extend(self._industry_curve_findings(bundle))
        context.findings.extend(self._achilles_findings(bundle))
        context.findings.extend(self._best_of_best_findings(bundle))
        context.findings.extend(self._strong_link_findings(bundle))
        context.recommendations = self._recommendations(bundle, context.findings)
        context.limitations = [
            "The deck is descriptive and does not prove causality.",
            "Charts and claims are limited to completed analyses with real result data.",
            "Skipped or empty analyses are excluded instead of being approximated.",
        ]

        if not context.findings and not allow_partial:
            raise DeckDataQualityError(
                "Deck generation blocked: no evidence-backed findings could be extracted."
            )

        return context

    def _baseline_findings(self, bundle: AnalysisBundle) -> list[Finding]:
        avg_satisfaction = bundle.metrics.get("average_satisfaction_index")
        review_count = bundle.metrics.get("total_review_count")
        quality_score = bundle.metrics.get("weighted_score") or bundle.metrics.get("cvc_score")

        findings: list[Finding] = []
        if avg_satisfaction is not None:
            evidence = [f"Average satisfaction index is {self._fmt(avg_satisfaction)}."]
            if review_count is not None:
                evidence.append(f"Total review count is {self._fmt(review_count)}.")
            findings.append(
                Finding(
                    title="Experience Baseline",
                    finding=(
                        "The completed wave provides a measurable customer experience "
                        "baseline for the focus brand and category."
                    ),
                    evidence=evidence,
                    why_it_matters=(
                        "This gives the deck a real performance anchor before moving "
                        "into activity-level diagnosis."
                    ),
                    confidence="high",
                    source_refs=["metrics.average_satisfaction_index"],
                )
            )

        if quality_score is not None:
            findings.append(
                Finding(
                    title="Quality Gate",
                    finding="The source wave passed the quality threshold for reporting.",
                    evidence=[f"Weighted quality score is {self._fmt(quality_score)}."],
                    why_it_matters=(
                        "A quality-approved wave is safer to promote from analysis output "
                        "into a client-facing presentation."
                    ),
                    confidence="high",
                    source_refs=["metrics.weighted_score"],
                )
            )

        return findings

    def _industry_curve_findings(self, bundle: AnalysisBundle) -> list[Finding]:
        result = self._analysis_result(bundle, "analysis_1")
        activities = result.get("activities") or []
        scored = [
            item for item in activities
            if item.get("activity_code") and self._float_or_none(item.get("industry_avg")) is not None
        ]

        if not scored and result.get("brands"):
            brands = [
                item for item in result.get("brands") or []
                if item.get("brand_id") and self._float_or_none(item.get("satisfaction_index")) is not None
            ]
            if brands:
                peak = max(brands, key=lambda item: self._float_or_none(item.get("satisfaction_index")) or 0)
                low = min(brands, key=lambda item: self._float_or_none(item.get("satisfaction_index")) or 0)
                return [
                    Finding(
                        title="Category Curve",
                        finding="Category performance is uneven across the observed brands.",
                        evidence=[
                            f"{peak.get('brand_id')} scores {self._fmt(peak.get('satisfaction_index'))}.",
                            f"{low.get('brand_id')} scores {self._fmt(low.get('satisfaction_index'))}.",
                        ],
                        why_it_matters=(
                            "The spread shows where the category has room for a more "
                            "specific competitive diagnosis."
                        ),
                        confidence="medium",
                        chart_refs=["chart_1"],
                        source_refs=["analysis_1.result.brands"],
                    )
                ]
            return []

        if not scored:
            return []

        peak = max(scored, key=lambda item: self._float_or_none(item.get("industry_avg")) or 0)
        low = min(scored, key=lambda item: self._float_or_none(item.get("industry_avg")) or 0)
        return [
            Finding(
                title="Industry Curve",
                finding="The industry curve shows clear high and low activity zones.",
                evidence=[
                    f"{peak.get('activity_code')} has industry average {self._fmt(peak.get('industry_avg'))}.",
                    f"{low.get('activity_code')} has industry average {self._fmt(low.get('industry_avg'))}.",
                ],
                why_it_matters=(
                    "The highest and lowest activity areas help separate category-wide "
                    "expectations from brand-specific execution gaps."
                ),
                confidence="high",
                chart_refs=["chart_1"],
                source_refs=["analysis_1.result.activities"],
            )
        ]

    def _achilles_findings(self, bundle: AnalysisBundle) -> list[Finding]:
        result = self._analysis_result(bundle, "analysis_6")
        links = [
            item for item in result.get("links") or []
            if item.get("activity_code") and self._score_for_item(item) is not None
        ]
        if not links:
            return []

        primary = sorted(
            links,
            key=lambda item: abs(self._float_or_none(item.get("delta")) or 0),
            reverse=True,
        )[0]
        evidence = [f"{primary.get('activity_code')} scores {self._fmt(self._score_for_item(primary))}."]
        if primary.get("industry_avg") is not None:
            evidence.append(f"Industry average is {self._fmt(primary.get('industry_avg'))}.")
        if primary.get("delta") is not None:
            evidence.append(f"Gap is {self._fmt(primary.get('delta'))}.")

        return [
            Finding(
                title="Achilles Heel",
                finding=(
                    f"{primary.get('activity_code')} is the clearest focus-brand "
                    "vulnerability in the completed analysis."
                ),
                evidence=evidence,
                why_it_matters=(
                    "This is the first activity to inspect because it connects a weak "
                    "brand score to a concrete operational area."
                ),
                confidence="high",
                chart_refs=["chart_6"],
                source_refs=["analysis_6.result.links"],
            )
        ]

    def _best_of_best_findings(self, bundle: AnalysisBundle) -> list[Finding]:
        result = self._analysis_result(bundle, "analysis_7")
        activities = result.get("activities") or result.get("rankings") or []
        if not activities:
            return []

        with_gap = [
            item for item in activities
            if item.get("activity_code") and self._float_or_none(item.get("gap")) is not None
        ]
        if with_gap:
            top = sorted(with_gap, key=lambda item: self._float_or_none(item.get("gap")) or 0, reverse=True)[:3]
            evidence = [
                f"{item.get('activity_code')} gap is {self._fmt(item.get('gap'))}."
                for item in top
            ]
            finding = "The largest Best of Best gaps reveal where leaders set a higher bar."
        else:
            scored = [
                item for item in activities
                if item.get("activity_code") and self._score_for_item(item) is not None
            ]
            if not scored:
                return []
            top = sorted(scored, key=lambda item: self._score_for_item(item) or 0, reverse=True)[:3]
            evidence = [
                f"{item.get('activity_code')} score is {self._fmt(self._score_for_item(item))}."
                for item in top
            ]
            finding = "The Best of Best analysis identifies benchmark activity strengths."

        return [
            Finding(
                title="Best of Best Gap",
                finding=finding,
                evidence=evidence,
                why_it_matters=(
                    "Benchmark gaps are useful because they turn competitive comparison "
                    "into a prioritized improvement sequence."
                ),
                confidence="high",
                chart_refs=["chart_7"],
                source_refs=["analysis_7.result.activities"],
            )
        ]

    def _strong_link_findings(self, bundle: AnalysisBundle) -> list[Finding]:
        result = self._analysis_result(bundle, "analysis_5") or self._analysis_result(bundle, "analysis_2")
        links = [
            item for item in result.get("links") or []
            if item.get("activity_code") and self._score_for_item(item) is not None
        ]
        if not links:
            return []

        top = sorted(links, key=lambda item: self._score_for_item(item) or 0, reverse=True)[:3]
        return [
            Finding(
                title="Strengths to Protect",
                finding="The completed analysis also shows activities worth protecting.",
                evidence=[
                    f"{item.get('activity_code')} scores {self._fmt(self._score_for_item(item))}."
                    for item in top
                ],
                why_it_matters=(
                    "A credible action plan should improve weak areas without eroding "
                    "the activities already working well."
                ),
                confidence="medium",
                chart_refs=["chart_5"] if self._analysis_result(bundle, "analysis_5") else ["chart_2"],
                source_refs=["analysis_5.result.links"],
            )
        ]

    def _recommendations(self, bundle: AnalysisBundle, findings: list[Finding]) -> list[str]:
        recommendations = [
            "Prioritize the weakest activity before broad brand-level initiatives.",
            "Use the Best of Best comparison to define what good performance looks like.",
            "Keep strong-link activities stable while improvement work is underway.",
            "Validate operational root causes before committing major budget.",
        ]

        achilles = next((finding for finding in findings if finding.title == "Achilles Heel"), None)
        if achilles:
            activity = self._first_activity_code(achilles.finding)
            if activity:
                recommendations[0] = f"Prioritize {activity} remediation before broader initiatives."

        best = next((finding for finding in findings if finding.title == "Best of Best Gap"), None)
        if best and best.evidence:
            codes = [
                code for text in best.evidence
                if (code := self._first_activity_code(text))
            ][:3]
            if codes:
                recommendations[1] = "Benchmark the largest gaps: " + ", ".join(codes) + "."

        if self._analysis_result(bundle, "analysis_8"):
            recommendations.append("Use segment breakdowns to target the next diagnostic pass.")

        return recommendations

    def _evidence_items(
        self,
        bundle: AnalysisBundle,
        wave_data: dict[str, Any],
        gold_row_count: int,
        complete_analysis_count: int,
    ) -> list[EvidenceItem]:
        items = [
            EvidenceItem(
                label="Gold activity rows",
                value=gold_row_count,
                source="wave_data.gold.activity",
            ),
            EvidenceItem(
                label="Completed analyses with results",
                value=complete_analysis_count,
                source="wave_data.analyses",
            ),
        ]
        for key, value in bundle.metrics.items():
            if isinstance(value, int | float):
                items.append(EvidenceItem(label=key, value=value, source=f"metrics.{key}"))

        quality = wave_data.get("quality") or {}
        for key in ("weighted_score", "concept_points", "briefing_adherence_pct"):
            value = quality.get(key)
            if self._float_or_none(value) is not None:
                items.append(EvidenceItem(label=key, value=value, source=f"quality.{key}"))

        return items

    @staticmethod
    def _analysis_result(bundle: AnalysisBundle, key: str) -> dict[str, Any]:
        analysis = bundle.analysis_results.get(key) or {}
        if not isinstance(analysis, dict):
            return {}
        return analysis.get("result") or {}

    @staticmethod
    def _complete_analyses_with_results(wave_data: dict[str, Any]) -> list[dict[str, Any]]:
        complete = []
        for analysis in wave_data.get("analyses") or []:
            result = analysis.get("result") or {}
            if analysis.get("status") == "complete" and result and any(result.values()):
                complete.append(analysis)
        return complete

    @staticmethod
    def _analysis_warnings(wave_data: dict[str, Any]) -> list[str]:
        warnings = []
        for analysis in wave_data.get("analyses") or []:
            if analysis.get("status") == "skipped":
                name = analysis.get("analysis_name") or analysis.get("analysis_type")
                reason = analysis.get("skip_reason") or "skipped"
                warnings.append(f"{name} skipped: {reason}")
        return warnings

    @staticmethod
    def _score_for_item(item: dict[str, Any]) -> float | None:
        for key in (
            "brand_score",
            "focus_brand_score",
            "score",
            "satisfaction_index",
            "industry_avg",
            "best_score",
        ):
            value = FindingExtractor._float_or_none(item.get(key))
            if value is not None:
                return value
        return None

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _fmt(value: Any) -> str:
        number = FindingExtractor._float_or_none(value)
        if number is None:
            return str(value)
        if number.is_integer():
            return str(int(number))
        return f"{number:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _first_activity_code(text: str) -> str:
        for token in text.replace(".", " ").replace(",", " ").split():
            if any(char.isdigit() for char in token) and any(char.isalpha() for char in token):
                return token
        return ""
