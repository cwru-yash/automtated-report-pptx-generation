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


class ChartGenerator:
    def _save_to_bytes(self, fig) -> bytes:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)
        return buf.read()

    def _label_for_item(self, item: dict) -> str:
        return str(
            item.get("label")
            or item.get("activity_code")
            or item.get("brand_name")
            or item.get("brand_id")
            or ""
        )

    def _score_for_link(self, link: dict) -> float | None:
        for key in ("score", "brand_score", "satisfaction_index", "industry_avg"):
            value = link.get(key)
            if value is not None:
                return float(value)
        return None

    def render_industry_curve(self, analysis_result: dict) -> bytes | None:
        result_data = analysis_result.get("result", {})
        activities = result_data.get("activities", [])
        if activities:
            return self.render_activity_curve(activities)

        brands = result_data.get("brands", [])
        if not brands:
            return None

        industry_avg = result_data.get("industry_avg", 0)

        fig, ax = plt.subplots(figsize=SIZE_WIDE)
        apply_brand_style(ax)

        labels = []
        scores = []
        colors = []
        line_widths = []

        for b in brands:
            labels.append(b.get("brand_id", "").replace("brand-", "").title())
            scores.append(b.get("satisfaction_index", 0))
            if b.get("brand_id") == "brand-ceragem":
                colors.append(COLOR_PRIMARY)
                line_widths.append(2.5)
            else:
                colors.append(BRAND_COLORS.get(b.get("brand_id"), COLOR_PRIMARY))
                line_widths.append(1.5)

        # Draw the points and lines connecting them to make a "curve"
        ax.plot(labels, scores, marker="o", linestyle="-", color="#7f8c8d", linewidth=1.5, zorder=1)
        
        # Highlight focus brand with a scatter on top
        for idx, (lbl, scr, clr, lw) in enumerate(zip(labels, scores, colors, line_widths)):
            ax.scatter([lbl], [scr], color=clr, s=lw * 30, zorder=2)

        ax.axhline(y=industry_avg, color="#e74c3c", linestyle="--", alpha=0.7, label=f"Industry Avg: {industry_avg}")
        
        ax.set_ylim(0, 100)
        ax.set_title("Industry Average Curve", fontsize=FONT_SIZE_TITLE, pad=15)
        ax.set_ylabel("Satisfaction Index", fontsize=FONT_SIZE_LABEL)
        ax.legend()
        
        return self._save_to_bytes(fig)

    def render_activity_curve(self, activities: list[dict]) -> bytes | None:
        points = [
            item
            for item in activities
            if item.get("activity_code") and item.get("industry_avg") is not None
        ]
        if not points:
            return None

        labels = [str(item["activity_code"]) for item in points]
        industry_scores = [float(item["industry_avg"]) for item in points]
        x = np.arange(len(labels))

        fig, ax = plt.subplots(figsize=SIZE_WIDE)
        apply_brand_style(ax)

        ax.plot(
            x,
            industry_scores,
            marker="o",
            linestyle="-",
            color=COLOR_PRIMARY,
            linewidth=1.8,
            markersize=4,
            label="Industry average",
        )

        if any(item.get("industry_avg_excl_niche") is not None for item in points):
            excl_scores = [
                float(item.get("industry_avg_excl_niche") or item["industry_avg"])
                for item in points
            ]
            ax.plot(
                x,
                excl_scores,
                marker="o",
                linestyle="--",
                color=COLOR_ACCENT,
                linewidth=1.4,
                markersize=3,
                label="Industry avg excl. niche",
            )

        ax.set_ylim(0, 100)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_title("Industry Average Curve", fontsize=FONT_SIZE_TITLE, pad=15)
        ax.set_ylabel("Satisfaction Index", fontsize=FONT_SIZE_LABEL)
        ax.legend()

        return self._save_to_bytes(fig)

    def render_horizontal_bar(self, analysis_result: dict, color: str, title: str) -> bytes | None:
        result_data = analysis_result.get("result", {})
        links = result_data.get("links", [])
        if not links:
            return None
        
        # Sort by score ascending for horizontal bar (highest on top)
        links = sorted(links, key=lambda x: self._score_for_link(x) or 0)
        
        labels = [self._label_for_item(link) for link in links]
        scores = [self._score_for_link(link) or 0 for link in links]
        if not any(labels) or not any(scores):
            return None

        fig, ax = plt.subplots(figsize=SIZE_WIDE)
        apply_brand_style(ax)
        
        ax.grid(axis="x", color="#e0e0e0", linestyle="--", alpha=0.7)
        ax.grid(axis="y", visible=False)

        bars = ax.barh(labels, scores, color=color, height=0.6)
        
        # Add value annotations
        for bar in bars:
            width = bar.get_width()
            ax.annotate(
                f'{width:.1f}',
                xy=(width, bar.get_y() + bar.get_height() / 2),
                xytext=(3, 0),
                textcoords="offset points",
                ha='left', va='center', fontsize=FONT_SIZE_LABEL
            )

        industry_values = [
            float(link["industry_avg"])
            for link in links
            if link.get("industry_avg") is not None
        ]
        if industry_values:
            industry_avg = sum(industry_values) / len(industry_values)
            ax.axvline(
                industry_avg,
                color=COLOR_ACCENT,
                linestyle="--",
                linewidth=1.2,
                label=f"Industry avg {industry_avg:.1f}",
            )
            ax.legend()
            
        ax.set_xlim(0, 100)
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, pad=15)
        ax.set_xlabel("Score", fontsize=FONT_SIZE_LABEL)
        
        return self._save_to_bytes(fig)

    def render_sr_ranking(self, analysis_result: dict) -> bytes:
        # Placeholder for Type 4
        # Since it is skipped in the mock, we can just return a simple error image or skip
        fig, ax = plt.subplots(figsize=SIZE_SQUARE)
        apply_brand_style(ax)
        ax.text(0.5, 0.5, 'S&R Ranking Not Available', ha='center', va='center', fontsize=FONT_SIZE_TITLE)
        ax.axis('off')
        return self._save_to_bytes(fig)

    def render_grouped_bar(self, analysis_result: dict, title: str) -> bytes:
        result_data = analysis_result.get("result", {})
        
        fig, ax = plt.subplots(figsize=SIZE_WIDE)
        apply_brand_style(ax)
        
        if title == "Breakdown":
            segments = result_data.get("segments", [])
            # Group by segment_value, series by brand_id
            groups = sorted(list(set(s.get("segment_value") for s in segments)))
            brands = sorted(list(set(s.get("brand_id") for s in segments)))
            
            x = np.arange(len(groups))
            width = 0.8 / len(brands) if brands else 0.8
            
            for i, brand in enumerate(brands):
                brand_scores = []
                for g in groups:
                    score = next((s.get("satisfaction_index", 0) for s in segments if s.get("segment_value") == g and s.get("brand_id") == brand), 0)
                    brand_scores.append(score)
                
                color = BRAND_COLORS.get(brand, COLOR_PRIMARY)
                label = brand.replace("brand-", "").title()
                offset = (i - len(brands)/2 + 0.5) * width
                ax.bar(x + offset, brand_scores, width, label=label, color=color)
                
            ax.set_xticks(x)
            ax.set_xticklabels(groups)
            ax.set_ylim(0, 100)
            ax.legend(loc='upper right')
            
        elif title == "Best of Best" and result_data.get("activities"):
            activities = result_data.get("activities", [])[:12]
            labels = [str(item.get("activity_code", "")) for item in activities]
            x = np.arange(len(labels))
            width = 0.35
            best_scores = [float(item.get("best_score") or 0) for item in activities]
            focus_scores = [
                float(item.get("focus_brand_score") or 0)
                for item in activities
            ]

            ax.bar(x - width / 2, focus_scores, width, label="Focus brand", color=COLOR_PRIMARY)
            ax.bar(x + width / 2, best_scores, width, label="Best brand", color=COLOR_ACCENT)
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=45, ha="right")
            ax.set_ylim(0, 100)
            ax.legend(loc='upper right')

        elif title == "Best of Best":
            rankings = result_data.get("rankings", [])
            if not rankings:
                plt.close(fig)
                return None
            # Group by brand, show top activity
            brands = sorted(list(set(r.get("brand_id") for r in rankings)))
            
            for i, brand in enumerate(brands):
                r = next((x for x in rankings if x.get("brand_id") == brand), None)
                if r:
                    label = brand.replace("brand-", "").title()
                    color = BRAND_COLORS.get(brand, COLOR_PRIMARY)
                    bar = ax.bar(i, r.get("score", 0), 0.6, color=color)
                    ax.annotate(
                        r.get("label", ""),
                        xy=(i, r.get("score", 0) / 2),
                        ha='center', va='center', color='white', rotation=90
                    )
                    ax.annotate(
                        f'{r.get("score", 0):.1f}',
                        xy=(i, r.get("score", 0)),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom'
                    )
                    
            ax.set_xticks(np.arange(len(brands)))
            ax.set_xticklabels([b.replace("brand-", "").title() for b in brands])
            ax.set_ylim(0, 100)
            
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, pad=15)
        
        return self._save_to_bytes(fig)

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
            return self.render_horizontal_bar(analysis, COLOR_NEGATIVE, "Achilles Heel")
        elif atype == 7:
            return self.render_grouped_bar(analysis, "Best of Best")
        elif atype == 8:
            return self.render_grouped_bar(analysis, "Breakdown")
            
        return None

    def render_all(self, wave_data: dict) -> dict[int, bytes]:
        charts = {}
        for analysis in wave_data.get("analyses", []):
            try:
                png_bytes = self.render_for_analysis(analysis)
                if png_bytes:
                    charts[analysis.get("analysis_type")] = png_bytes
            except Exception as e:
                logger.exception(f"Failed to render chart for analysis {analysis.get('analysis_type')}: {e}")
        return charts
