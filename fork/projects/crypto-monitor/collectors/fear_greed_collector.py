#!/usr/bin/env python3
"""
Fear & Greed Collector - fetches Fear & Greed index from alternative.me.

Usage: python3 fear_greed_collector.py
"""

import json
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.json"

DATA_DIR = PROJECT_ROOT / "data" / "fear_greed"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})


def fetch_fear_greed() -> dict:
    """Fetch Fear & Greed index from alternative.me."""
    url = API_ENDPOINTS.get("fear_greed_limit", "https://api.alternative.me/fng/?limit=1")

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
    except Exception as e:
        error_msg = str(e)
        print(f"[FearGreed] ERROR: {error_msg}")
        return {
            "status": "error",
            "error": error_msg,
            "value": None,
            "classification": None,
            "timestamp": datetime.now().isoformat(),
        }


def save(data: dict):
    """Save to files."""
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
