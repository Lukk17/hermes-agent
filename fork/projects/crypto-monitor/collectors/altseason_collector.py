#!/usr/bin/env python3
"""
Altseason Index Collector - fetches Altseason index from blockchaincenter.

Usage: python3 altseason_collector.py
"""

import json
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.json"

DATA_DIR = PROJECT_ROOT / "data" / "altseason"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})


def fetch_altseason() -> dict:
    """Fetch Altseason index from blockchaincenter.net."""
    url = API_ENDPOINTS.get("blockchaincenter_api", "https://blockchaincenter.net/api/altseason")
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CryptoMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        
        # Parse response
        if "altseason" in data:
            return {"value": data["altseason"], "source": "blockchaincenter"}
        return None
    except Exception as e:
        print(f"[Altseason] Error: {e}")
        return None


def save(data: dict):
    """Save to files."""
    latest_file = DATA_DIR / "altseason_latest.json"
    with open(latest_file, "w") as f:
        json.dump(data, f, indent=2)
    
    # Update history
    history_file = DATA_DIR / "altseason_history.json"
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
    print("[Altseason] Fetching...")
    data = fetch_altseason()
    if data:
        save(data)
        print(f"[Altseason] Saved: {data.get('value')}")
    else:
        print("[Altseason] Failed")


if __name__ == "__main__":
    main()
