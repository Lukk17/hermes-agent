#!/usr/bin/env python3
"""Style 3 refined: Horizontal bar gauge with proper anti-aliasing."""

import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Honor the project layout via src.paths instead of a hardcoded openclaw path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.paths import REPORTS_DIR as OUT  # noqa: E402

BG = (13, 17, 23)
WHITE = (255, 255, 255)
MUTED = (139, 148, 158)
DARK_TRACK = (30, 35, 42)

GRADIENT = [
    (0.0, (248, 81, 73)),
    (0.25, (219, 109, 40)),
    (0.5, (210, 153, 34)),
    (0.75, (126, 231, 135)),
    (1.0, (63, 185, 80)),
]


def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _grad(pct):
    pct = max(0, min(1, pct))
    for i in range(len(GRADIENT) - 1):
        p1, c1 = GRADIENT[i]
        p2, c2 = GRADIENT[i + 1]
        if pct <= p2:
            t = (pct - p1) / (p2 - p1) if p2 > p1 else 0
            return _lerp(c1, c2, t)
    return GRADIENT[-1][1]


def _font(size, bold=False):
    try:
        return ImageFont.truetype(
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf", size)
    except:
        return ImageFont.load_default()


def _mono(size, bold=False):
    try:
        return ImageFont.truetype(
            f"/usr/share/fonts/truetype/dejavu/DejaVuSansMono{'-Bold' if bold else ''}.ttf", size)
    except:
        return ImageFont.load_default()


def _center(draw, xy, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((xy[0] - tw // 2, xy[1] - th // 2), text, fill=fill, font=font)


def render_bar_gauge(value, title, sublabel, path,
                     left_label="FEAR", right_label="GREED",
                     left_color=(248, 81, 73), right_color=(63, 185, 80)):
    """Render horizontal bar gauge at 4K resolution.

    Draws at 2x internal resolution, downscales with LANCZOS for smooth AA.
    Final output: 3840 x 720 PNG.
    """
    FW, FH = 3840, 1920
    S = 2
    W, H = FW * S, FH * S

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Layout (all at S scale)
    pad_x = 500 * S
    bar_w = W - 2 * pad_x
    bar_h = 260 * S
    bar_y = 1100 * S

    # --- Title ---
    _center(draw, (W // 2, 200 * S), title, _font(140 * S, True), WHITE)

    # --- Value ---
    if value is not None:
        v_color = _grad(value / 100)
        _center(draw, (W // 2, 560 * S), f"{value:.0f}", _mono(320 * S, True), v_color)
        if sublabel and sublabel != "N/A":
            _center(draw, (W // 2, 850 * S), sublabel.upper(), _font(80 * S, True), MUTED)
    else:
        _center(draw, (W // 2, 560 * S), "N/A", _mono(200 * S, True), MUTED)

    # --- Left/Right labels ---
    _center(draw, (pad_x + 140 * S, bar_y - 60 * S),
            left_label, _font(56 * S, True), left_color)
    _center(draw, (pad_x + bar_w - 140 * S, bar_y - 60 * S),
            right_label, _font(56 * S, True), right_color)

    # --- Background track ---
    draw.rectangle([pad_x, bar_y, pad_x + bar_w, bar_y + bar_h], fill=DARK_TRACK)

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
                        mx + lw // 2, bar_y + bar_h + 28 * S], fill=WHITE)

        tri_top = bar_y + bar_h + 36 * S
        tri_h = 60 * S
        tri_half = 48 * S
        draw.polygon([
            (mx, tri_top),
            (mx - tri_half, tri_top + tri_h),
            (mx + tri_half, tri_top + tri_h),
        ], fill=WHITE)

    # --- Scale ---
    scale_y = bar_y + bar_h + 120 * S
    for val_n, label in [(0, "0"), (25, "25"), (50, "50"), (75, "75"), (100, "100")]:
        sx = pad_x + int(bar_w * val_n / 100)
        _center(draw, (sx, scale_y), label, _mono(60 * S), MUTED)

    # Downscale
    img = img.resize((FW, FH), Image.LANCZOS)
    img.save(str(path), "PNG", quality=95)


if __name__ == "__main__":
    print("Generating refined bar gauges...")

    render_bar_gauge(5, "Fear & Greed", "Extreme Fear",
                     OUT / "proposal_3a_bar.png",
                     left_label="FEAR", right_label="GREED")
    print("  ✅ F&G (value=5)")

    render_bar_gauge(39, "Cycle Score", "Recovery",
                     OUT / "proposal_3b_cycle.png",
                     left_label="BEARISH", right_label="BULLISH")
    print("  ✅ Cycle (value=39)")

    render_bar_gauge(51, "News Sentiment", "Neutral",
                     OUT / "proposal_3c_sentiment.png",
                     left_label="NEGATIVE", right_label="POSITIVE")

    print("Done!")
