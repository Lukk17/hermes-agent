"""
Report Builder - orchestrator that generates report sections and charts.

Calls each section renderer, assembles sections dict and charts dict.
Single responsibility: build the report data structure.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = DATA_DIR / "reports"
sys.path.insert(0, str(BASE_DIR))

from reports.sections import (
    render_prices, render_movers, render_indicators, render_sectors,
    render_gas, render_breadth, render_etf, render_stablecoins,
    render_funding, render_flows, render_whales, render_news,
    render_airdrops, render_summary, render_links,
)


# Delivery order. Charts lead because the owner reads the graphs first.
CHART_ORDER = (
    "gauge_fng",
    "gauge_cycle",
    "gauge_sentiment",
    "trending_narratives",
    "coin_sentiment",
    "btc_dominance",
    "btc_price",
    "gas_history",
)

SECTION_ORDER = (
    "prices",
    "movers",
    "news",
    "indicators",
    "breadth",
    "sectors",
    "gas",
    "etf",
    "stablecoins",
    "funding",
    "flows",
    "whales",
    "airdrops",
    "summary",
    "links",
)

# Sections a model writes, keyed by the section they replace. The file holds body
# text only, so the header lives here.
MODEL_WRITTEN_SECTIONS = {
    "news": ("news_summary.md", "## 📰 Trending News"),
    "summary": ("market_summary.md", "## 📋 Market Summary"),
}

BRAILLE_SPACER = "⠀"

# Data file paths
PRICES_FILE = DATA_DIR / "coin_prices" / "coin_prices_latest.json"
FEAR_GREED_FILE = DATA_DIR / "fear_greed" / "fear_greed_latest.json"
GLOBAL_FILE = DATA_DIR / "global_market" / "global_market_latest.json"
TRENDING_FILE = DATA_DIR / "trending" / "trending_latest.json"
CYCLE_FILE = DATA_DIR / "cycle" / "cycle_latest.json"
SENTIMENT_FILE = DATA_DIR / "sentiment" / "sentiment_latest.json"
TRENDS_FILE = DATA_DIR / "trends" / "trends_latest.json"
WHALE_SIGNALS_FILE = DATA_DIR / "whale_signals" / "whale_signals_latest.json"
WHALES_FILE = DATA_DIR / "whales" / "whales_latest.json"
AIRDROP_FILE = DATA_DIR / "airdrops" / "airdrops_latest.json"
EXCHANGE_FLOWS_FILE = DATA_DIR / "exchange_flows" / "exchange_flows_latest.json"
EXTERNAL_INDICES_FILE = DATA_DIR / "external_indices" / "external_indices_latest.json"
SECTORS_FILE = DATA_DIR / "sectors" / "sectors_latest.json"
GAS_FILE = DATA_DIR / "gas" / "gas_latest.json"
ETF_FILE = DATA_DIR / "etf_flows" / "etf_flows_latest.json"
STABLECOIN_FILE = DATA_DIR / "stablecoins" / "stablecoins_latest.json"
INFLUENCERS_FILE = DATA_DIR / "influencers" / "influencers_latest.json"
MARKET_BREADTH_FILE = DATA_DIR / "market_breadth" / "market_breadth_latest.json"
FUNDING_FILE = DATA_DIR / "funding" / "funding_latest.json"


def load_json(path: Path):
    """Load JSON safely."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def generate_sections(data: dict) -> dict:
    """Generate all text sections. Returns dict of name -> markdown."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    sections = {
        "title": f"# 📊 Daily Crypto Report\n{now}",
    }

    # Map section renderers to keys
    sections["prices"] = render_prices(data)
    sections["movers"] = render_movers(data)
    sections["indicators"] = render_indicators(data)
    sections["sectors"] = render_sectors(data)
    sections["gas"] = render_gas(data)
    sections["breadth"] = render_breadth(data)
    sections["etf"] = render_etf(data)
    sections["stablecoins"] = render_stablecoins(data)
    sections["funding"] = render_funding(data)
    sections["flows"] = render_flows(data)
    sections["whales"] = render_whales(data)
    sections["news"] = render_news(data)
    sections["airdrops"] = render_airdrops(data)
    sections["summary"] = render_summary(data)
    sections["links"] = render_links(data)

    # Add braille spacer after each section that has content
    BRAILLE = "⠀"
    for key in sections:
        if key != "title" and sections[key]:
            sections[key] = f"{sections[key]}\n{BRAILLE}"

    return sections


def generate_charts(data: dict) -> dict:
    """Generate chart images. Returns dict of name -> path."""
    sys.path.insert(0, str(BASE_DIR / "reports"))
    from charts import render_gauge, render_trending_narratives, render_coin_sentiment
    from tables import box_table

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    charts = {}

    cycle = data.get("cycle", {}) or {}
    cs = cycle.get("cycle_score", {})
    sentiment = data.get("sentiment", {}) or {}
    ms = sentiment.get("market_sentiment", {})
    fg = cycle.get("indicators", {}).get("fear_greed", {})

    # Fear & Greed gauge
    try:
        p = REPORT_DIR / "gauge_fng.png"
        fng_data = data.get("fear_greed", {})
        fng_val = fng_data.get("data", {}).get("alternative_me", {}).get("value")
        fng_label = "Neutral"
        if fng_val is not None:
            if fng_val <= 25:
                fng_label = "Extreme Fear"
            elif fng_val <= 45:
                fng_label = "Fear"
            elif fng_val <= 55:
                fng_label = "Neutral"
            elif fng_val <= 75:
                fng_label = "Greed"
            else:
                fng_label = "Extreme Greed"
        if fng_val is None:
            fng_val = 50
            fng_label = "No Data"
        render_gauge(fng_val, "Fear & Greed", fng_label, p,
                     left_label="FEAR", right_label="GREED")
        charts["gauge_fng"] = p
    except Exception as e:
        print(f"  ❌ gauge_fng: {e}")

    # Cycle Score gauge
    try:
        p = REPORT_DIR / "gauge_cycle.png"
        cycle_val = cs.get("score") if cs.get("score") is not None else 50
        cycle_label = (cs.get("phase") or "No Data").replace("_", " ").title()
        render_gauge(cycle_val, "Cycle Score", cycle_label, p,
                     left_label="BEARISH", right_label="BULLISH")
        charts["gauge_cycle"] = p
    except Exception as e:
        print(f"  ❌ gauge_cycle: {e}")

    # Sentiment gauge
    try:
        p = REPORT_DIR / "gauge_sentiment.png"
        sent_val = ms.get("index") if ms.get("index") is not None else 50
        sent_label = (ms.get("label") or "No Data").replace("_", " ").title()
        render_gauge(sent_val, "News Sentiment", sent_label, p,
                     left_label="NEGATIVE", right_label="POSITIVE")
        charts["gauge_sentiment"] = p
    except Exception as e:
        print(f"  ❌ gauge_sentiment: {e}")

    # Trending Narratives
    trends = data.get("trends", {}) or {}
    cats = trends.get("categories", {})
    if cats:
        try:
            p = REPORT_DIR / "trending_narratives.png"
            render_trending_narratives(cats, p)
            charts["trending_narratives"] = p
        except Exception as e:
            print(f"  ❌ trending_narratives: {e}")

    # Coin Sentiment
    coin_sents = sentiment.get("coin_sentiments", {})
    if coin_sents:
        try:
            p = REPORT_DIR / "coin_sentiment.png"
            render_coin_sentiment(coin_sents, p)
            charts["coin_sentiment"] = p
        except Exception as e:
            print(f"  ❌ coin_sentiment: {e}")

    # BTC Dominance chart
    btc_dom_chart = DATA_DIR / "dominance" / "charts" / "btc_dominance_2y.png"
    if btc_dom_chart.exists():
        charts["btc_dominance"] = btc_dom_chart

    # BTC Price chart
    btc_price_chart = DATA_DIR / "btc_price" / "btc_price_2y.png"
    if btc_price_chart.exists():
        charts["btc_price"] = btc_price_chart

    # Gas history chart
    gas_chart_path = DATA_DIR / "gas" / "charts" / "gas_history_1y.png"
    if gas_chart_path.exists():
        charts["gas_history"] = gas_chart_path

    # Note: table_prices, table_movers, table_whales chart generation
    # was removed during refactor - tables are sent as text in Discord messages
    # If tables as images are needed later, they require passing headers+rows
    # arrays to render_table(), not markdown text

    return charts


def build_message_sequence(sections: dict, charts: dict) -> list:
    """Build the fixed delivery sequence: title, then every chart, then the text.

    The order is the same every run. A missing chart or section drops out without
    shifting anything that survives.
    """
    messages = [(sections.get("title", ""), None)]
    messages.extend((None, charts[name]) for name in CHART_ORDER if charts.get(name))
    messages.extend((sections[key], None) for key in SECTION_ORDER if sections.get(key))

    return messages


class DeliveryItem(NamedTuple):
    text: str
    image: Path | None


def build_delivery(report_path: Path | str) -> list[DeliveryItem]:
    """Load a saved report and return the ordered messages to deliver.

    Raises:
        OSError: the report cannot be read.
        json.JSONDecodeError: the report is not valid JSON.
    """
    report_path = Path(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    sections = _with_model_written_sections(
        report.get("sections") or {}, report_path.parent
    )
    charts = {name: Path(path) for name, path in (report.get("charts") or {}).items()}

    return [
        DeliveryItem(text or "", Path(image) if image else None)
        for text, image in build_message_sequence(sections, charts)
    ]


def build_report(text_only: bool = False) -> dict:
    """Load all data, generate sections and charts, return full report dict."""
    print("=" * 60)
    print("📊 DAILY REPORT GENERATOR v2")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    print("\n📦 Loading data...")
    data = {
        "prices": load_json(PRICES_FILE),
        "coin_prices": load_json(PRICES_FILE),
        "fear_greed": load_json(FEAR_GREED_FILE),
        "global": load_json(GLOBAL_FILE),
        "trending": load_json(TRENDING_FILE),
        "cycle": load_json(CYCLE_FILE),
        "sentiment": load_json(SENTIMENT_FILE),
        "trends": load_json(TRENDS_FILE),
        "whale_signals": load_json(WHALE_SIGNALS_FILE),
        "whales": load_json(WHALES_FILE),
        "airdrops": load_json(AIRDROP_FILE),
        "exchange_flows": load_json(EXCHANGE_FLOWS_FILE),
        "external_indices": load_json(EXTERNAL_INDICES_FILE),
        "sectors": load_json(SECTORS_FILE),
        "gas": load_json(GAS_FILE),
        "etf": load_json(ETF_FILE),
        "stablecoins": load_json(STABLECOIN_FILE),
        "influencers": load_json(INFLUENCERS_FILE),
        "market_breadth": load_json(MARKET_BREADTH_FILE),
        "funding": load_json(FUNDING_FILE),
    }
    for k, v in data.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print("\n📝 Generating sections...")
    sections = generate_sections(data)
    for name, content in sections.items():
        preview = (content or "")[:60].replace("\n", " ")
        print(f"  {'✅' if content else '⬜'} {name}: {preview}")

    charts = {}
    if not text_only:
        print("\n📊 Generating charts...")
        charts = generate_charts(data)
        for name in charts:
            print(f"  ✅ {name}")

    print("\n📋 Building message sequence...")
    messages = build_message_sequence(sections, charts)
    for i, (text, img) in enumerate(messages, 1):
        t_preview = (text or "")[:50].replace("\n", " ")
        i_name = img.name if img else "none"
        print(f"  {i}. text={t_preview!r}... img={i_name}")

    # Save report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "version": 2,
        "sections": sections,
        "charts": {k: str(v) for k, v in charts.items()},
        "message_count": len(messages),
    }
    with open(REPORT_DIR / f"report_{ts}.json", "w") as f:
        json.dump(report, f, indent=2)
    with open(REPORT_DIR / "report_latest.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ Report ready - {len(messages)} messages, {len(charts)} charts")
    return {"sections": sections, "charts": charts, "messages": messages}


def _with_model_written_sections(sections: dict, report_dir: Path) -> dict:
    merged = dict(sections)
    for key, (filename, header) in MODEL_WRITTEN_SECTIONS.items():
        body = _read_optional_text(report_dir / filename)
        if body:
            merged[key] = f"{header}\n{body}\n{BRAILLE_SPACER}"

    return merged


def _read_optional_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
