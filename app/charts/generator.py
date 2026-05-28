import io
import logging
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.charts.styles import (
    apply_brand_style,
    BRAND_COLORS,
    COLOR_PRIMARY,
    COLOR_ACCENT,
    COLOR_POSITIVE,
    COLOR_NEGATIVE,
    DPI,
    SIZE_WIDE,
    SIZE_SQUARE,
    FONT_SIZE_TITLE,
    FONT_SIZE_LABEL,
)

logger = logging.getLogger(__name__)

# Decomposer real data field priority order for each context
_LINK_SCORE_KEYS = (
    "brand_score",
    "focus_brand_score",
    "best_score",
    "industry_score",
    "score",
    "satisfaction_index",
    "industry_avg",
)
_LINK_LABEL_KEYS = ("label", "activity_code", "macro_activity", "brand_name", "brand_id")


class ChartGenerator:
    def _save_to_bytes(self, fig) -> bytes:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)
        return buf.read()

    def _no_data_image(self, title: str = "No data available") -> bytes:
        fig, ax = plt.subplots(figsize=SIZE_WIDE)
        apply_brand_style(ax)
        ax.text(
            0.5, 0.5, title,
            ha="center", va="center",
            fontsize=FONT_SIZE_TITLE,
            color="#aaaaaa",
            transform=ax.transAxes,
        )
        ax.axis("off")
        return self._save_to_bytes(fig)

    def _label_for_item(self, item: dict) -> str:
        for key in _LINK_LABEL_KEYS:
            v = item.get(key)
            if v:
                return str(v)
        return ""

    def _score_for_link(self, link: dict) -> float | None:
        for key in _LINK_SCORE_KEYS:
            value = link.get(key)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
        return None

    # ------------------------------------------------------------------
    # Analysis 1: Industry Average Curve
    # ------------------------------------------------------------------

    def render_industry_curve(self, analysis_result: dict) -> bytes | None:
        result_data = analysis_result.get("result") or {}

        # Real schema: result.activities[].{activity_code, industry_avg, industry_avg_excl_niche}
        activities = result_data.get("activities") or []
        if activities:
            return self.render_activity_curve(activities)

        # Legacy schema: result.brands[]
        brands = result_data.get("brands") or []
        if brands:
            return self._render_brand_curve(brands, result_data)

        return self._no_data_image("Industry Average Curve — No data")

    def render_activity_curve(self, activities: list[dict]) -> bytes | None:
        points = [
            item for item in activities
            if item.get("activity_code") and item.get("industry_avg") is not None
        ]
        if not points:
            return self._no_data_image("Industry Average Curve — No activities")

        # Limit to top 20 for readability
        points = points[:20]
        labels = [str(item["activity_code"]) for item in points]
        industry_scores = [float(item["industry_avg"]) for item in points]
        x = np.arange(len(labels))

        fig, ax = plt.subplots(figsize=SIZE_WIDE)
        apply_brand_style(ax)

        ax.plot(
            x, industry_scores,
            marker="o", linestyle="-",
            color=COLOR_PRIMARY, linewidth=2.0, markersize=5,
            label="Industry average",
        )

        # excl niche line if present
        excl_scores = [
            float(item.get("industry_avg_excl_niche") or item["industry_avg"])
            for item in points
        ]
        if excl_scores != industry_scores:
            ax.plot(
                x, excl_scores,
                marker="s", linestyle="--",
                color=COLOR_ACCENT, linewidth=1.5, markersize=4,
                label="Industry avg excl. niche",
            )

        ax.set_ylim(0, 100)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_title("Industry Average Curve", fontsize=FONT_SIZE_TITLE, pad=15)
        ax.set_ylabel("Satisfaction Index", fontsize=FONT_SIZE_LABEL)
        ax.legend()

        return self._save_to_bytes(fig)

    def _render_brand_curve(self, brands: list[dict], result_data: dict) -> bytes:
        industry_avg = result_data.get("industry_avg", 0)
        focus_brand = result_data.get("focus_brand_id", "")

        labels = [b.get("brand_id", "").replace("brand-", "").title() for b in brands]
        scores = [b.get("satisfaction_index", 0) for b in brands]

        fig, ax = plt.subplots(figsize=SIZE_WIDE)
        apply_brand_style(ax)
        ax.plot(labels, scores, marker="o", linestyle="-", color="#7f8c8d", linewidth=1.5, zorder=1)
        for lbl, scr, b in zip(labels, scores, brands):
            clr = COLOR_PRIMARY if b.get("brand_id") == focus_brand else BRAND_COLORS.get(b.get("brand_id"), COLOR_ACCENT)
            ax.scatter([lbl], [scr], color=clr, s=60, zorder=2)
        if industry_avg:
            ax.axhline(y=industry_avg, color=COLOR_NEGATIVE, linestyle="--", alpha=0.7, label=f"Industry Avg: {industry_avg:.1f}")
        ax.set_ylim(0, 100)
        ax.set_title("Industry Average Curve", fontsize=FONT_SIZE_TITLE, pad=15)
        ax.set_ylabel("Satisfaction Index", fontsize=FONT_SIZE_LABEL)
        ax.legend()
        return self._save_to_bytes(fig)

    # ------------------------------------------------------------------
    # Analysis 2/3 (industry) and 5/6 (brand): horizontal bar
    # ------------------------------------------------------------------

    def render_horizontal_bar(self, analysis_result: dict, color: str, title: str) -> bytes | None:
        result_data = analysis_result.get("result") or {}
        links = [lnk for lnk in (result_data.get("links") or []) if lnk]  # skip empty dicts

        if not links:
            return self._no_data_image(f"{title} — No links data")

        # Sort ascending so highest ends up on top of horizontal bar
        links = sorted(links, key=lambda x: self._score_for_link(x) or 0)

        labels = [self._label_for_item(lnk) for lnk in links]
        scores = [self._score_for_link(lnk) or 0 for lnk in links]

        if not any(labels) and not any(scores):
            return self._no_data_image(f"{title} — No values")

        # Replace missing labels with index
        labels = [lbl or f"Item {i+1}" for i, lbl in enumerate(labels)]

        fig, ax = plt.subplots(figsize=(SIZE_WIDE[0], max(3.0, len(labels) * 0.45 + 1.5)))
        apply_brand_style(ax)
        ax.grid(axis="x", color="#e0e0e0", linestyle="--", alpha=0.7)
        ax.grid(axis="y", visible=False)

        bars = ax.barh(labels, scores, color=color, height=0.65)

        for bar in bars:
            width = bar.get_width()
            if width:
                ax.annotate(
                    f"{width:.1f}",
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(4, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=FONT_SIZE_LABEL,
                )

        # Industry average reference line
        industry_values = [
            float(lnk["industry_avg"]) for lnk in links if lnk.get("industry_avg") is not None
        ]
        if industry_values:
            ind_avg = sum(industry_values) / len(industry_values)
            ax.axvline(ind_avg, color=COLOR_ACCENT, linestyle="--", linewidth=1.5,
                       label=f"Industry avg {ind_avg:.1f}")
            ax.legend()

        ax.set_xlim(0, 100)
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, pad=15)
        ax.set_xlabel("Score", fontsize=FONT_SIZE_LABEL)

        return self._save_to_bytes(fig)

    # ------------------------------------------------------------------
    # Analysis 4: S&R Ranking (skipped in MVP)
    # ------------------------------------------------------------------

    def render_sr_ranking(self, analysis_result: dict) -> bytes:
        return self._no_data_image("S&R Index Ranking — Survey data required (MVP)")

    # ------------------------------------------------------------------
    # Analysis 7: Best of Best
    # ------------------------------------------------------------------

    def render_best_of_best(self, analysis_result: dict) -> bytes | None:
        result_data = analysis_result.get("result") or {}
        activities = result_data.get("activities") or []
        if not activities and result_data.get("rankings"):
            return self.render_horizontal_bar(
                {"result": {"links": result_data.get("rankings") or []}},
                COLOR_ACCENT,
                "Best of Best",
            )
        if not activities:
            return self._no_data_image("Best of Best — No activities data")

        activities = activities[:12]
        labels = [str(item.get("activity_code") or f"Act{i+1}") for i, item in enumerate(activities)]
        x = np.arange(len(labels))
        width = 0.38

        focus_scores = [float(item.get("focus_brand_score") or 0) for item in activities]
        best_scores = [float(item.get("best_score") or 0) for item in activities]

        fig, ax = plt.subplots(figsize=SIZE_WIDE)
        apply_brand_style(ax)

        ax.bar(x - width / 2, focus_scores, width, label="Focus brand", color=COLOR_PRIMARY, alpha=0.9)
        ax.bar(x + width / 2, best_scores, width, label="Best brand", color=COLOR_ACCENT, alpha=0.9)

        for i, (fs, bs) in enumerate(zip(focus_scores, best_scores)):
            if fs:
                ax.text(i - width / 2, fs + 0.5, f"{fs:.0f}", ha="center", va="bottom", fontsize=7)
            if bs:
                ax.text(i + width / 2, bs + 0.5, f"{bs:.0f}", ha="center", va="bottom", fontsize=7)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_ylim(0, 110)
        ax.set_title("Best of Best", fontsize=FONT_SIZE_TITLE, pad=15)
        ax.set_ylabel("Satisfaction Index", fontsize=FONT_SIZE_LABEL)
        ax.legend(loc="upper right")

        return self._save_to_bytes(fig)

    # ------------------------------------------------------------------
    # Analysis 8: Breakdown
    # ------------------------------------------------------------------

    def render_breakdown(self, analysis_result: dict) -> bytes | None:
        result_data = analysis_result.get("result") or {}
        segments = result_data.get("segments") or []
        if not segments:
            return self._no_data_image("Breakdown — No segment data")

        groups = sorted(list({s.get("segment_value") for s in segments if s.get("segment_value")}))
        brands = sorted(list({s.get("brand_id") for s in segments if s.get("brand_id")}))
        if not groups or not brands:
            return self._no_data_image("Breakdown — Incomplete segment data")

        x = np.arange(len(groups))
        width = 0.8 / len(brands)

        fig, ax = plt.subplots(figsize=SIZE_WIDE)
        apply_brand_style(ax)

        for i, brand in enumerate(brands):
            brand_scores = [
                next((s.get("satisfaction_index", 0) for s in segments
                      if s.get("segment_value") == g and s.get("brand_id") == brand), 0)
                for g in groups
            ]
            color = BRAND_COLORS.get(brand, COLOR_PRIMARY)
            label = brand.replace("brand-", "").title()
            offset = (i - len(brands) / 2 + 0.5) * width
            ax.bar(x + offset, brand_scores, width, label=label, color=color)

        ax.set_xticks(x)
        ax.set_xticklabels(groups)
        ax.set_ylim(0, 100)
        ax.legend(loc="upper right")
        ax.set_title("Breakdown by Segment", fontsize=FONT_SIZE_TITLE, pad=15)
        ax.set_ylabel("Satisfaction Index", fontsize=FONT_SIZE_LABEL)

        return self._save_to_bytes(fig)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def render_for_analysis(self, analysis: dict) -> bytes | None:
        if analysis.get("status") != "complete":
            return None
        atype = analysis.get("analysis_type")
        if atype == 1:
            return self.render_industry_curve(analysis)
        elif atype == 2:
            return self.render_horizontal_bar(analysis, COLOR_POSITIVE, "Strong Links — Industry")
        elif atype == 3:
            return self.render_horizontal_bar(analysis, COLOR_NEGATIVE, "Weak Links — Industry")
        elif atype == 4:
            return self.render_sr_ranking(analysis)
        elif atype == 5:
            return self.render_horizontal_bar(analysis, COLOR_POSITIVE, "Strong Links — Brand")
        elif atype == 6:
            return self.render_horizontal_bar(analysis, COLOR_NEGATIVE, "Achilles Heel — Brand")
        elif atype == 7:
            return self.render_best_of_best(analysis)
        elif atype == 8:
            return self.render_breakdown(analysis)
        return None

    def has_plot_points(self, analysis: dict) -> bool:
        if analysis.get("status") != "complete":
            return False

        result_data = analysis.get("result") or {}
        atype = analysis.get("analysis_type")

        if atype == 1:
            activities = result_data.get("activities") or []
            if any(item.get("activity_code") and item.get("industry_avg") is not None for item in activities):
                return True
            brands = result_data.get("brands") or []
            return any(item.get("brand_id") and item.get("satisfaction_index") is not None for item in brands)

        if atype in (2, 3, 5, 6):
            return any(self._label_for_item(link) and self._score_for_link(link) is not None for link in result_data.get("links") or [])

        if atype == 7:
            activities = result_data.get("activities") or result_data.get("rankings") or []
            return any(item.get("activity_code") and self._score_for_link(item) is not None for item in activities)

        if atype == 8:
            return any(
                segment.get("segment_value")
                and segment.get("brand_id")
                and segment.get("satisfaction_index") is not None
                for segment in result_data.get("segments") or []
            )

        return False

    def render_all(self, wave_data: dict, *, skip_empty: bool = False) -> dict[int, bytes]:
        charts = {}
        for analysis in wave_data.get("analyses", []):
            try:
                if skip_empty and not self.has_plot_points(analysis):
                    continue
                png_bytes = self.render_for_analysis(analysis)
                if png_bytes:
                    charts[analysis.get("analysis_type")] = png_bytes
            except Exception as e:
                logger.exception("Failed to render chart for analysis %s: %s", analysis.get("analysis_type"), e)
        return charts
