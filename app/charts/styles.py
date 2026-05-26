# Brand palette
COLOR_PRIMARY   = "#1a2b4a"   # dark navy
COLOR_ACCENT    = "#e8b84b"   # gold
COLOR_SECONDARY = "#4a90d9"   # blue
COLOR_POSITIVE  = "#2ecc71"   # green for strong links
COLOR_NEGATIVE  = "#e74c3c"   # red for weak links / achilles heel
COLOR_NEUTRAL   = "#95a5a6"   # grey for competitors

BRAND_COLORS = {
    "brand-ceragem":      COLOR_PRIMARY,
    "brand-competitor-a": COLOR_SECONDARY,
    "brand-competitor-b": COLOR_NEUTRAL,
    "brand-competitor-c": "#7f8c8d",
}

DPI = 300

# PPT-appropriate sizes in inches
SIZE_WIDE   = (10.0, 5.5)    # for bar/line charts spanning full slide width
SIZE_SQUARE = (5.0, 5.0)     # for compact/single-metric charts

FONT_FAMILY = "DejaVu Sans"
FONT_SIZE_TITLE  = 13
FONT_SIZE_LABEL  = 9
FONT_SIZE_TICK   = 8
FONT_SIZE_LEGEND = 9

def apply_brand_style(ax):
    """Applies the brand visual style to a matplotlib axes."""
    ax.set_facecolor("#f9f9f9")
    
    # Hide top and right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    # Lighten remaining spines
    ax.spines["bottom"].set_color("#cccccc")
    ax.spines["left"].set_color("#cccccc")
    
    # Configure grid
    ax.grid(axis="y", color="#e0e0e0", linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)
    
    # Configure tick parameters
    ax.tick_params(axis="both", colors="#333333", labelsize=FONT_SIZE_TICK)
