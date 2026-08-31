#!/usr/bin/env python3
"""
Coin Prices Collector - fetches top 10 coins by market cap.

Uses daily history cache to avoid redundant API calls.

Saves to data/coin_prices/coin_prices_latest.json

Usage: python3 coin_prices_collector.py
"""

import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cache_manager import get_coingecko_cache, get_daily_data
from src import DATA_DIR, write_json_atomic, error_collector
from src.paths import data_subdir


HISTORY_FILE = data_subdir("coin_prices") / "coin_prices_history.json"


def fetch_top_coins() -> dict:
    """Fetch top 10 coins by market cap from CoinGecko."""
    cache = get_coingecko_cache()
    result = cache.get_markets(
        vs_currency="usd",
        order="market_cap_desc",
        per_page=10,
        page=1,
        price_change_percentage="24h"
    )
    
    if result["status"] != "ok":
        error_msg = result.get("error", "API error")
        return {
            "status": "error",
            "error": error_msg,
            "coins": [],
            "timestamp": datetime.now().isoformat()
        }
    
    coins = []
    for c in result["data"]:
        coins.append({
            "id": c.get("id"),
            "symbol": c.get("symbol", "").upper(),
            "name": c.get("name", ""),
            "price": c.get("current_price", 0),
            "change_24h": c.get("price_change_percentage_24h", 0),
            "market_cap": c.get("market_cap", 0),
            "volume": c.get("total_volume", 0),
        })
    
    return {
        "status": "ok",
        "error": None,
        "coins": coins,
        "timestamp": datetime.now().isoformat()
    }


def main():
    print("[CoinPrices] Fetching top 10 coins...")
    
    try:
        # Use daily cache - only calls API if today's data not saved yet
        data = get_daily_data("CoinPrices", fetch_top_coins, HISTORY_FILE)
        
        if data.get("status") == "error":
            error_msg = data.get("error", "Unknown error")
            print(f"[CoinPrices] ERROR: {error_msg} - Data may be stale")
            error_collector.add_error("coin_prices", error_msg, "warning")
        
        elif data.get("coins"):
            latest_file = data_subdir("coin_prices") / "coin_prices_latest.json"
            write_json_atomic(latest_file, data)
            coins = data["coins"]
            print(f"[CoinPrices] Done! Top: {coins[0]['symbol']} @ ${coins[0]['price']:,}")
        else:
            print("[CoinPrices] WARNING: No coins fetched")
    
    except Exception as e:
        error_msg = str(e)
        print(f"[CoinPrices] ERROR: {error_msg}")
        error_collector.add_error("coin_prices", error_msg, "error")


if __name__ == "__main__":
    main()
