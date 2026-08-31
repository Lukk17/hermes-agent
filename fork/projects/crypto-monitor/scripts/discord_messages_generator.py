#!/usr/bin/env python3
"""
Discord Messages Generator
Reads report JSON and AI summaries, outputs messages to discord_messages.json.

Each message is a dict with "text" and optional "image" path.
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path("/home/node/.openclaw/workspace/crypto-monitor")
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.json"
REPORT_DIR = PROJECT_ROOT / "data" / "reports"
OUTPUT_FILE = REPORT_DIR / "discord_messages.json"

MAX_TEXT_LENGTH = 1900

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
EXTERNAL_LINKS = CONFIG.get("external_links", {})

# Braille blank for empty lines - actual unicode character
BRAILLE = "\u2800\n"


def load_json(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def load_markdown(path):
    if path.exists():
        return path.read_text().strip()
    return ""


def split_text_if_needed(text, max_len=MAX_TEXT_LENGTH):
    """Split text into chunks of max_len chars, return list of chunks."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    while len(text) > max_len:
        # Find a good split point (newline preferred)
        chunk = text[:max_len]
        last_newline = chunk.rfind('\n')
        if last_newline > max_len // 2:
            chunk = text[:last_newline]
            text = text[last_newline+1:]
        else:
            # No good newline, split at max_len
            text = text[max_len:]
        chunks.append(chunk)
    if text:
        chunks.append(text)
    return chunks


def main():
    print("Loading report...")

    report = load_json(REPORT_DIR / "report_latest.json")
    sections = report.get("sections", {})
    charts = report.get("charts", {})
    timestamp = report.get("timestamp", "")

    # Load AI summaries
    news_summary = load_markdown(REPORT_DIR / "news_summary.md")
    market_summary = load_markdown(REPORT_DIR / "market_summary.md")

    # Clean market_summary - remove "# Market Summary" header if present
    if market_summary:
        market_summary = re.sub(r'^#\s*Market\s+Summary\s*\n*', '', market_summary, flags=re.IGNORECASE).strip()

    # Replace placeholders
    if news_summary and "AI_SUMMARIZE_THIS" not in news_summary:
        sections["news_summary"] = news_summary
    if market_summary and "AI_SUMMARIZE_THIS" not in market_summary:
        sections["market_summary"] = market_summary

    # Quick links
    quick_links_list = EXTERNAL_LINKS.get("quick_links", [
        "https://cryptobubbles.net/",
        "https://alternative.me/crypto/fear-and-greed-index/",
        "https://www.blockchaincenter.net/en/altcoin-season-index/",
        "https://www.blockchaincenter.net/en/bitcoin-rainbow-chart/"
    ])
    quick_links = "\n".join(quick_links_list)

    # Airdrop links
    airdrop_links_list = EXTERNAL_LINKS.get("airdrop_links", [
        "https://app.getgrass.io",
        "https://monad.xyz",
        "https://berachain.com",
        "https://fuel.network",
        "https://scroll.io"
    ])
    airdrop_links = "\n".join(airdrop_links_list)

    # Build message list
    output = []

    # 1. Title header
    output.append({"text": "# 📊 Daily Crypto Report", "image": None})

    # 2. Timestamp
    output.append({"text": "\t" + timestamp, "image": None})

    # 3. Braille + gauge_fng
    output.append({"text": BRAILLE, "image": charts.get("gauge_fng")})

    # 4. Braille + gauge_cycle
    output.append({"text": BRAILLE, "image": charts.get("gauge_cycle")})

    # 5. Braille + gauge_sentiment
    output.append({"text": BRAILLE, "image": charts.get("gauge_sentiment")})

    # 6. Prices - text section + image
    prices_text = sections.get("prices", "")
    if prices_text:
        output.append({"text": BRAILLE + "## 💰 Prices\n" + prices_text, "image": None})
    else:
        output.append({"text": BRAILLE + "## 💰 Prices\n⚠️ No price data\n", "image": None})

    # 6b. BTC Price chart
    output.append({"text": BRAILLE, "image": charts.get("btc_price")})

    # 7. Movers - text section
    movers_text = sections.get("movers", "")
    if movers_text:
        output.append({"text": BRAILLE + "## 📈 Top Movers\n" + movers_text, "image": None})
    else:
        output.append({"text": BRAILLE + "## 📈 Top Movers\n⚠️ No mover data\n", "image": None})

    # 8. Trending - braille + header + image
    output.append({"text": BRAILLE + "## 📰 Trending Narratives\n", "image": charts.get("trending_narratives")})

    # 9. Coin Sentiment - braille + header + image
    output.append({"text": BRAILLE + "## 💭 Coin Sentiment\n", "image": charts.get("coin_sentiment")})

    # 10. Indicators - text section
    indicators_text = sections.get("indicators", "")
    if indicators_text:
        output.append({"text": BRAILLE + "## 📉 Market Indicators\n" + indicators_text, "image": None})
    else:
        output.append({"text": BRAILLE + "## 📉 Market Indicators\n⚠️ No indicator data\n", "image": None})

    # 11. BTC Dominance - braille + header + image
    output.append({"text": BRAILLE + "## 📊 BTC Dominance\n", "image": charts.get("btc_dominance")})

    # 12. Sectors - text section
    sectors_text = sections.get("sectors", "")
    if sectors_text:
        output.append({"text": BRAILLE + "## 🏭 Crypto Sectors\n" + sectors_text, "image": None})
    else:
        output.append({"text": BRAILLE + "## 🏭 Crypto Sectors\n⚠️ No sector data\n", "image": None})

    # (External Indices - REMOVED - duplicate of gauges)

    # === COMBINED: ETH Gas + ETF Flows + Stablecoin Supply + Funding Rates (text sections) ===
    # Note: each section already contains its own header (## ⛽ ETH Gas, ## 📈 Spot ETF Flows, etc.)
    combined_text_sections = (
        sections.get("gas", "") + "\n" +
        sections.get("etf", "") + "\n" +
        sections.get("stablecoins", "") + "\n" +
        sections.get("funding", "")
    )
    # Split if too long
    for chunk in split_text_if_needed(combined_text_sections):
        output.append({"text": chunk, "image": None})

    # 13. Exchange Holdings - text section
    flows_text = sections.get("flows", "")
    if flows_text:
        output.append({"text": BRAILLE + flows_text, "image": None})
    else:
        output.append({"text": BRAILLE + "## 🏦 Exchange Holdings\n⚠️ No flow data\n", "image": None})

    # 14. Whales - braille + whale section text + image
    whale_text = sections.get("whales", "")
    whale_chart = charts.get("table_whales")
    if whale_text:
        # whale_text already contains full section with headers
        for chunk in split_text_if_needed(BRAILLE + whale_text):
            output.append({"text": chunk, "image": None})
    else:
        output.append({"text": BRAILLE + "## 🐋 Whale Activity\n⚠️ No whale data available\n", "image": whale_chart})

    # 15. News Summary - split if needed
    news_text = BRAILLE + "## 📰 News Summary\n" + sections.get("news_summary", "")
    for chunk in split_text_if_needed(news_text):
        output.append({"text": chunk, "image": None})

    # 16. Airdrops + Quick Links (combined)
    airdrop_quick_combined = BRAILLE + "## 🪂 Airdrops\n" + airdrop_links + "\n" + BRAILLE + "## 🔗 Quick Links\n" + quick_links
    for chunk in split_text_if_needed(airdrop_quick_combined):
        output.append({"text": chunk, "image": None})

    # 17. Market Summary - split if needed
    market_text = BRAILLE + "## 📋 Market Summary\n" + sections.get("market_summary", "")
    for chunk in split_text_if_needed(market_text):
        output.append({"text": chunk, "image": None})

    # Build final output with numbers
    output_messages = []
    for i, msg in enumerate(output, 1):
        if msg["text"] or msg["image"]:
            output_messages.append({
                "number": len(output_messages) + 1,
                "text": msg["text"],
                "image": msg["image"]
            })

    # Save to JSON file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_messages, f, indent=2)

    print(f"Generated {len(output_messages)} messages")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
