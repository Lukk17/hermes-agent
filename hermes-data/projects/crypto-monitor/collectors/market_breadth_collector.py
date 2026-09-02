#!/usr/bin/env python3
"""
Market Breadth Collector
Tracks BTC dominance, altcoin performance vs BTC, market health indicators.

Uses daily history cache to avoid redundant API calls.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cache_manager import get_coingecko_cache, get_daily_data

DATA_DIR = PROJECT_ROOT / "data" / "market_breadth"
HISTORY_FILE = DATA_DIR / "market_breadth_history.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_breadth() -> dict:
    """Calculate market breadth metrics using cached data."""
    cache = get_coingecko_cache()
    
    # Get global data (cached)
    global_result = cache.get_global()
    if global_result["status"] != "ok":
        return {"error": global_result.get("error")}
    
    global_data = global_result["data"]["data"]
    
    # Get BTC and ETH prices (cached via markets)
    markets_result = cache.get_markets(vs_currency="usd", order="market_cap_desc",
                                       per_page=10, page=1)
    
    btc_price = 0
    eth_price = 0
    if markets_result["status"] == "ok":
        for coin in markets_result["data"]:
            if coin.get("id") == "bitcoin":
                btc_price = coin.get("current_price", 0)
            elif coin.get("id") == "ethereum":
                eth_price = coin.get("current_price", 0)
    
    btc_dominance = global_data.get("market_cap_percentage", {}).get("btc", 0)
    eth_dominance = global_data.get("market_cap_percentage", {}).get("eth", 0)
    active_cryptocurrencies = global_data.get("active_cryptocurrencies", 0)
    markets = global_data.get("markets", 0)
    
    # Calculate ETH/BTC ratio
    eth_btc_ratio = eth_price / btc_price if btc_price > 0 else 0
    
    # Market health based on dominance
    if btc_dominance > 50:
        health = "BTC heavy"
    elif btc_dominance > 40:
        health = "Neutral"
    else:
        health = "Altseason"
    
    return {
        "btc_dominance": btc_dominance,
        "eth_dominance": eth_dominance,
        "eth_btc_ratio": eth_btc_ratio,
        "active_cryptocurrencies": active_cryptocurrencies,
        "markets": markets,
        "health": health,
    }


def save_breadth(data: dict):
    """Save breadth to latest file."""
    with open(DATA_DIR / "market_breadth_latest.json", "w") as f:
        json.dump(data, f, indent=2)


def main():
    print("[Market Breadth] Fetching market breadth...")
    
    # Use daily cache
    data = get_daily_data("MarketBreadth", fetch_breadth, HISTORY_FILE)
    
    if "error" not in data:
        save_breadth(data)
        print(f"  BTC Dominance: {data.get('btc_dominance', 0):.1f}%")
        print(f"  ETH Dominance: {data.get('eth_dominance', 0):.1f}%")
        print(f"  ETH/BTC Ratio: {data.get('eth_btc_ratio', 0):.4f}")
    else:
        print(f"[Market Breadth] Error: {data.get('error')}")


if __name__ == "__main__":
    main()