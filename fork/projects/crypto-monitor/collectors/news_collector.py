#!/usr/bin/env python3
"""
News Collector - fetches crypto news from RSS feeds.

Uses free RSS feeds - no API key needed.

Usage: python3 news_collector.py
"""

import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "news"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RSS_FEEDS = [
    {"name": "CoinTelegraph", "url": "https://cointelegraph.com/rss"},
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
    {"name": "Decrypt", "url": "https://decrypt.co/feed"},
]


def fetch_rss(url: str) -> list:
    """Fetch and parse RSS feed. Returns list of articles."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read().decode("utf-8")

        root = ET.fromstring(xml_data)
        channel = root.find("channel")

        articles = []
        for item in channel.findall("item")[:10]:
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            description = item.findtext("description", "").strip()

            # Clean HTML from description
            import re
            description = re.sub(r'<[^>]+>', '', description)
            description = description.strip()

            if title:
                articles.append({
                    "title": title,
                    "link": link,
                    "published": pub_date,
                    "description": description[:200] if description else "",
                })

        return articles

    except Exception as e:
        print(f"[RSS] Error fetching {url}: {e}")
        return []


def fetch_all_news() -> dict:
    """Fetch from all RSS feeds."""
    all_articles = []
    errors = []

    for feed in RSS_FEEDS:
        print(f"[News] Fetching {feed['name']}...")
        articles = fetch_rss(feed["url"])
        if articles:
            # Add source to articles
            for a in articles:
                a["source"] = feed["name"]
            all_articles.extend(articles)
        else:
            errors.append(f"{feed['name']} failed")

    if not all_articles:
        return {
            "status": "error",
            "error": "All RSS feeds failed",
            "articles": [],
            "source": "rss",
        }

    # Sort by date (most recent first)
    # Note: Some dates may not parse, so we keep original order as fallback
    return {
        "status": "ok",
        "error": None,
        "articles": all_articles,
        "source": "rss",
        "feeds_used": [f["name"] for f in RSS_FEEDS],
        "errors": errors if errors else None,
    }


def save_news(data: dict):
    """Save news to file."""
    latest_file = DATA_DIR / "news_latest.json"
    with open(latest_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[News] Saved {len(data.get('articles', []))} articles")


def main():
    print("[News] Fetching crypto news from RSS feeds...")

    result = fetch_all_news()

    if result.get("status") == "ok":
        print(f"[News] Got {len(result.get('articles', []))} articles from {len(result.get('feeds_used', []))} feeds")
    else:
        print(f"[News] ERROR: {result.get('error', 'Unknown error')}")

    save_news(result)


if __name__ == "__main__":
    main()
