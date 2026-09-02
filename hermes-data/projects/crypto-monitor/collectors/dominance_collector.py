#!/usr/bin/env python3
"""
BTC Dominance Collector - fetches BTC dominance from CoinGecko.

Usage: python3 dominance_collector.py
"""

import json
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.json"

DATA_DIR = PROJECT_ROOT / "data" / "dominance"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})


def fetch_dominance() -> dict:
    """Fetch BTC and ETH dominance from CoinGecko."""
    url = API_ENDPOINTS.get("coingecko_global", "https://api.coingecko.com/api/v3/global")
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CryptoMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        
        btc = data["data"]["market_cap_percentage"]["btc"]
        eth = data["data"]["market_cap_percentage"]["eth"]
        
        return {
            "btc": btc,
            "eth": eth,
        }
    except Exception as e:
        print(f"[Dominance] Error: {e}")
        return None


def save(data: dict):
    """Save to files."""
    latest_file = DATA_DIR / "dominance_latest.json"
    with open(latest_file, "w") as f:
        json.dump(data, f, indent=2)
    
    # Update history
    history_file = DATA_DIR / "dominance_history.json"
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
    print("[Dominance] Fetching...")
    data = fetch_dominance()
    if data:
        save(data)
        print(f"[Dominance] Saved: BTC {data['btc']}%, ETH {data['eth']}%")
    else:
        print("[Dominance] Failed")


if __name__ == "__main__":
    main()
