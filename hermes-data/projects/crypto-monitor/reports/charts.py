#!/usr/bin/env python3
"""
Chart generators v3 — bar gauge + matplotlib bar charts.

Gauges: Pillow-based horizontal bar gauge (4K, LANCZOS downscale)
Bar charts: matplotlib with proper styling

Kept:
  - Gauge (F&G, Cycle, Sentiment) — Pillow bar gauge
  - Trending Narratives (horizontal bar)
  - Coin Sentiment (horizontal bar)
"""

import json
from pathlib import Path
from typing import Optional

# Load config
CONFIG_FILE = Path(__file__).parent.parent / "config" / "settings.json"

def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
CHART_SETTINGS = CONFIG.get("chart_settings", {})

# ---------------------------------------------------------------------------
# Pillow-based bar gauge renderer
# ---------------------------------------------------------------------------

from PIL import Image, ImageDraw, ImageFont

# Colors
_BG = (13, 17, 23)         # #0d1117
_WHITE = (255, 255, 255)
_MUTED = (139, 148, 158)   # #8b949e
_DARK_TRACK = (30, 35, 42)

# Gradient stops for the bar fill
_GRADIENT = [
    (0.0,  (248, 81, 73)),    # red
    (0.25, (219, 109, 40)),   # orange
    (0.5,  (210, 153, 34)),   # yellow
    (0.75, (126, 231, 135)),  # light green
    (1.0,  (63, 185, 80)),    # green
]


def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _grad(pct):
    pct = max(0, min(1, pct))
    for i in range(len(_GRADIENT) - 1):
        p1, c1 = _GRADIENT[i]
        p2, c2 = _GRADIENT[i + 1]
        if pct <= p2:
            t = (pct - p1) / (p2 - p1) if p2 > p1 else 0
            return _lerp(c1, c2, t)
    return _GRADIENT[-1][1]


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf", size)
    except (OSError, IOError):
        return ImageFont.load_default()


def _get_mono_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(
            f"/usr/share/fonts/truetype/dejavu/DejaVuSansMono{'-Bold' if bold else ''}.ttf", size)
    except (OSError, IOError):
        return ImageFont.load_default()


def _center(draw, xy, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((xy[0] - tw // 2, xy[1] - th // 2), text, fill=fill, font=font)


def render_gauge(value: Optional[float], title: str, sublabel: str, path: Path,
                 left_label: str = "FEAR", right_label: str = "GREED",
                 left_color: tuple = (248, 81, 73), right_color: tuple = (63, 185, 80)):
    """Render horizontal bar gauge at 4K resolution.

    Draws at 2x internal resolution, downscales with LANCZOS for smooth AA.
    Final output: 3840 x 1920 PNG.
    """
    # Handle None or invalid values - render with 50 (middle) as default
    if value is None or not isinstance(value, (int, float)):
        value = 50
        sublabel = "No Data"
    FW, FH = 3840, 1920
    S = 2
    W, H = FW * S, FH * S

    img = Image.new("RGB", (W, H), _BG)
    draw = ImageDraw.Draw(img)

    # Layout (all at S scale)
    pad_x = 500 * S
    bar_w = W - 2 * pad_x
    bar_h = 260 * S
    bar_y = 1100 * S

    # --- Title ---
    _center(draw, (W // 2, 200 * S), title, _get_font(140 * S, True), _WHITE)

    # --- Value ---
    if value is not None:
        v_color = _grad(value / 100)
        _center(draw, (W // 2, 560 * S), f"{value:.0f}", _get_mono_font(320 * S, True), v_color)
        if sublabel and sublabel != "N/A":
            _center(draw, (W // 2, 850 * S), sublabel.upper(), _get_font(80 * S, True), _MUTED)
    else:
        _center(draw, (W // 2, 560 * S), "N/A", _get_mono_font(200 * S, True), _MUTED)

    # --- Left/Right labels ---
    _center(draw, (pad_x + 140 * S, bar_y - 60 * S),
            left_label, _get_font(56 * S, True), left_color)
    _center(draw, (pad_x + bar_w - 140 * S, bar_y - 60 * S),
            right_label, _get_font(56 * S, True), right_color)

    # --- Background track ---
    draw.rectangle([pad_x, bar_y, pad_x + bar_w, bar_y + bar_h], fill=_DARK_TRACK)

    # --- Gradient fill ---
    for x in range(bar_w):
        pct = x / bar_w
        color = _grad(pct)
        draw.line([(pad_x + x, bar_y), (pad_x + x, bar_y + bar_h)], fill=color)

    # --- Marker ---
    if value is not None:
        v = max(0, min(100, value))
        mx = pad_x + int(bar_w * v / 100)

        lw = 14 * S
        draw.rectangle([mx - lw // 2, bar_y - 28 * S,
                        mx + lw // 2, bar_y + bar_h + 28 * S], fill=_WHITE)

        tri_top = bar_y + bar_h + 36 * S
        tri_h = 60 * S
        tri_half = 48 * S
        draw.polygon([
            (mx, tri_top),
            (mx - tri_half, tri_top + tri_h),
            (mx + tri_half, tri_top + tri_h),
        ], fill=_WHITE)

    # --- Scale ---
    scale_y = bar_y + bar_h + 120 * S
    for val_n, label in [(0, "0"), (25, "25"), (50, "50"), (75, "75"), (100, "100")]:
        sx = pad_x + int(bar_w * val_n / 100)
        _center(draw, (sx, scale_y), label, _get_mono_font(60 * S), _MUTED)

    # Downscale with LANCZOS for smooth anti-aliasing
    img = img.resize((FW, FH), Image.LANCZOS)
    img.save(str(path), "PNG", quality=95)


# ---------------------------------------------------------------------------
# Matplotlib charts (bar charts only)
# ---------------------------------------------------------------------------

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLORS = CHART_SETTINGS.get("colors", {})
BG = COLORS.get("bg", "#0d1117")
CARD = COLORS.get("card", "#161b22")
TEXT = COLORS.get("text", "#e6edf3")
GREEN = COLORS.get("green", "#3fb950")
RED = COLORS.get("red", "#f85149")
YELLOW = COLORS.get("yellow", "#d29922")
ORANGE = COLORS.get("orange", "#db6d28")
BLUE = COLORS.get("blue", "#58a6ff")
PURPLE = COLORS.get("purple", "#bc8cff")
GRAY = COLORS.get("gray", "#484f58")
MUTED = COLORS.get("muted", "#8b949e")

DPI = CHART_SETTINGS.get("dpi", 300)
FONT = CHART_SETTINGS.get("font", "DejaVu Sans")


def _save(fig, path):
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=fig.get_facecolor(),
                pad_inches=0.25)
    plt.close(fig)


def render_trending_narratives(categories: dict, path: Path):
    """Horizontal bar chart of trending narrative categories."""
    cats = {k: v for k, v in categories.items()
            if k != "_uncategorized" and isinstance(v, dict)}
    sorted_cats = sorted(cats.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:8]

    if not sorted_cats:
        return

    # Compact figure - more height per bar, but readable
    fig, ax = plt.subplots(figsize=(18, max(6, len(sorted_cats) * 1.5)),
                           facecolor=BG)
    ax.set_facecolor(CARD)

    ax.set_title("Trending Narratives", color=TEXT, fontsize=48,
                  fontweight="bold", pad=12, family=FONT)

    labels = [k for k, _ in sorted_cats]
    counts = [v.get("count", 0) for _, v in sorted_cats]
    y = np.arange(len(labels))

    palette = [BLUE, PURPLE, "#7ee787", ORANGE, YELLOW, "#f778ba", "#79c0ff", "#d2a8ff"]
    colors = [palette[i % len(palette)] for i in range(len(labels))]

    bars = ax.barh(y, counts, color=colors, height=0.9, alpha=0.85, edgecolor="none")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, color=TEXT, fontsize=20, fontweight="medium", family=FONT)
    ax.invert_yaxis()

    max_count = max(counts) if counts else 1
    for i, (bar, count) in enumerate(zip(bars, counts)):
        pct = sorted_cats[i][1].get("pct", 0)
        ax.text(bar.get_width() + max_count * 0.02, i,
                f"{pct:.0f}%)",
                va="center", color=MUTED, fontsize=32, family="DejaVu Sans Mono")

    ax.set_xlim(0, max_count * 1.35)
    ax.tick_params(axis="x", colors=GRAY, labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(GRAY)
    ax.spines["left"].set_color(GRAY)
    ax.set_xlabel("Article Count", color=MUTED, fontsize=24, family=FONT)

    fig.tight_layout()
    _save(fig, path)


def render_coin_sentiment(coin_sentiments: dict, path: Path):
    """Horizontal bar chart of per-coin sentiment scores."""
    items = [(k, v) for k, v in coin_sentiments.items()
             if k != "MARKET" and v.get("article_count", 0) >= 1]
    items.sort(key=lambda x: x[1]["avg_score"], reverse=True)
    items = items[:8]

    if not items:
        return

    fig_height = max(3.5, len(items) * 0.7 + 2)
    fig, ax = plt.subplots(figsize=(12, fig_height), facecolor=BG)
    ax.set_facecolor(CARD)

    ax.set_title("Coin Sentiment", color=TEXT, fontsize=32,
                  fontweight="bold", pad=16, family=FONT)

    labels = [k for k, _ in items]
    scores = [v["avg_score"] for _, v in items]
    y = np.arange(len(labels))
    colors = [GREEN if s > 0.05 else RED if s < -0.05 else YELLOW for s in scores]

    bars = ax.barh(y, scores, color=colors, height=0.5, alpha=0.85, edgecolor="none")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, color=TEXT, fontsize=20, fontweight="bold",
                       family="DejaVu Sans Mono")
    ax.invert_yaxis()
    ax.axvline(x=0, color=GRAY, linewidth=0.5, alpha=0.5)

    max_abs = max(abs(s) for s in scores) if scores else 0.1
    padding = max_abs * 0.15

    for i, (bar, score) in enumerate(zip(bars, scores)):
        cnt = items[i][1].get("article_count", 0)
        if score >= 0:
            x_pos = bar.get_width() + padding
            ha = "left"
        else:
            x_pos = bar.get_width() - padding
            ha = "right"
        ax.text(x_pos, i, f"{score:+.3f} ({cnt})",
                va="center", ha=ha,
                color=MUTED, fontsize=24, family="DejaVu Sans Mono")

    ax.set_xlim(-max_abs * 2.0, max_abs * 1.6)
    ax.tick_params(axis="x", colors=GRAY, labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(GRAY)
    ax.spines["left"].set_color(GRAY)
    ax.set_xlabel("Sentiment Score", color=MUTED, fontsize=24, family=FONT)

    fig.tight_layout()
    _save(fig, path)


# ---------------------------------------------------------------------------
# Table renderer (PIL-based for clean, readable tables)
# ---------------------------------------------------------------------------

def render_table(headers: list, rows: list, title: str = "", path: Path = None, min_width: int = 0, row_colors: list = None):
    """Render a table as PNG image using PIL - content-proportional, centered."""
    # Handle empty data - create placeholder
    if not headers:
        headers = ["No Data"]
    if not rows:
        rows = [["-"]]
    
    from PIL import Image, ImageDraw, ImageFont
    
    # Settings
    BG = (13, 17, 23)
    HEADER_BG = (22, 27, 34)
    BORDER = (48, 54, 64)
    TEXT = (255, 255, 255)
    GREEN = (34, 197, 94)   # Green for positive
    RED = (239, 68, 68)     # Red for negative
    
    # Calculate column widths (in characters)
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Font sizes
    font_size_title = 42
    font_size_header = 32
    font_size = 28
    
    # Cell dimensions
    char_w = 24
    cell_h = 56
    padding = 28
    header_h = 64
    title_h = 54
    
    # Calculate width based on content only
    cell_widths = [col_widths[i] * char_w + 28 for i in range(len(col_widths))]
    table_w = sum(cell_widths)
    actual_w = table_w + padding * 2
    
    num_rows = len(rows)
    # Only add title height if there's a title
    title_space = title_h + 16 if title else 10
    total_h = (num_rows + 1) * cell_h + header_h + padding + title_space
    
    # Create image
    img = Image.new("RGB", (actual_w, total_h), BG)
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size_title)
        font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", font_size_header)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_size)
    except:
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font = ImageFont.load_default()
    
    # Draw title centered (or skip if no title)
    title_y = 20 if not title else padding
    if title:
        bbox = draw.textbbox((0, 0), title, font=font_title)
        title_w = bbox[2] - bbox[0]
        title_x = (actual_w - title_w) // 2
        draw.text((title_x, title_y), title, font=font_title, fill=TEXT)
        title_y = padding
    
    # Draw header
    header_y = title_y + (title_h if title else 20)
    col_x = padding
    for i, h in enumerate(headers):
        draw.rectangle([col_x, header_y, col_x + cell_widths[i], header_y + header_h], fill=HEADER_BG, outline=BORDER, width=3)
        bbox = draw.textbbox((0, 0), str(h), font=font_header)
        text_w = bbox[2] - bbox[0]
        text_x = col_x + (cell_widths[i] - text_w) // 2
        draw.text((text_x, header_y + 14), str(h), font=font_header, fill=TEXT)
        col_x += cell_widths[i] + 4
    
    # Draw rows
    row_y = header_y + header_h
    for idx, row in enumerate(rows):
        col_x = padding
        row_color = None
        if row_colors and idx < len(row_colors):
            row_color = row_colors[idx]
        
        for i, cell in enumerate(row):
            if i < len(col_widths):
                # Determine cell background color
                fill = BG if (idx % 2 == 0) else (20, 22, 27)
                
                # If row has a color override (green/red), use it
                if row_color == "green":
                    fill = (20, 50, 30)  # Dark green bg
                elif row_color == "red":
                    fill = (50, 20, 20)  # Dark red bg
                
                # Determine text color - NO automatic font coloring, only background
                cell_text = str(cell)
                text_color = TEXT
                
                draw.rectangle([col_x, row_y, col_x + cell_widths[i], row_y + cell_h], fill=fill, outline=BORDER, width=2)
                bbox = draw.textbbox((0, 0), cell_text[:col_widths[i]], font=font)
                text_w = bbox[2] - bbox[0]
                text_x = col_x + (cell_widths[i] - text_w) // 2
                draw.text((text_x, row_y + 12), cell_text[:col_widths[i]], font=font, fill=text_color)
                col_x += cell_widths[i] + 4
        row_y += cell_h
    
    if path:
        img.save(path, "PNG", quality=95)
    
    return img
    
    return img
