#!/usr/bin/env python3
"""
Fear & Greed Collector - fetches Fear & Greed index from alternative.me.

Usage: python3 fear_greed_collector.py
"""

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import error_collector, load_config  # noqa: E402
from src.paths import data_subdir  # noqa: E402

DATA_DIR = data_subdir("fear_greed")

DEFAULT_ENDPOINT = "https://api.alternative.me/fng/?limit=1"


def endpoint() -> str:
    endpoints = load_config().get("api_endpoints", {})
    return endpoints.get("fear_greed_limit", DEFAULT_ENDPOINT)


def fetch_fear_greed() -> dict:
    """Fetch Fear & Greed index from alternative.me."""
    url = endpoint()

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CryptoMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        latest = data["data"][0]
        return {
            "status": "ok",
            "error": None,
            "value": int(latest["value"]),
            "classification": latest["value_classification"],
            "timestamp": latest["timestamp"],
        }
    except (OSError, ValueError, KeyError, IndexError) as e:
        error_msg = str(e)
        print(f"[FearGreed] ERROR: {error_msg}")
        error_collector.add_error("fear_greed", f"{url}: {error_msg}", "error")
        return {
            "status": "error",
            "error": error_msg,
            "value": None,
            "classification": None,
            "timestamp": datetime.now().isoformat(),
        }


def save(data: dict):
    """Save to files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    latest_file = DATA_DIR / "fear_greed_latest.json"
    with open(latest_file, "w") as f:
        json.dump(data, f, indent=2)

    # Update history
    history_file = DATA_DIR / "fear_greed_history.json"
    today = datetime.now().strftime("%Y-%m-%d")

    if history_file.exists():
        history = json.loads(history_file.read_text())
    else:
        history = {}

    history[today] = data
    history["last_updated"] = datetime.now().isoformat()

    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)


def main():
    print("[FearGreed] Fetching...")
    data = fetch_fear_greed()
    if data.get("status") == "ok":
        save(data)
        print(f"[FearGreed] Saved: {data['value']} ({data['classification']})")
    else:
        save(data)  # Save error state
        print(f"[FearGreed] ERROR: {data.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
