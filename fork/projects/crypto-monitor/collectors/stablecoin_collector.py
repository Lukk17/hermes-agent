#!/usr/bin/env python3
"""
Stablecoin Flows Collector
Tracks stablecoin market cap changes (mint/burn proxy).

Uses daily history cache to avoid redundant API calls.
Source: CoinGecko API (free)
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cache_manager import get_coingecko_cache, get_daily_data

DATA_DIR = PROJECT_ROOT / "data" / "stablecoins"
HISTORY_FILE = DATA_DIR / "stablecoins_history.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STABLECOINS = [
    {"id": "tether", "symbol": "USDT", "name": "Tether"},
    {"id": "usd-coin", "symbol": "USDC", "name": "USD Coin"},
    {"id": "dai", "symbol": "DAI", "name": "Dai"},
    {"id": "frax", "symbol": "FRAX", "name": "Frax"},
    {"id": "true-usd", "symbol": "TUSD", "name": "TrueUSD"},
    {"id": "binance-usd", "symbol": "BUSD", "name": "Binance USD"},
    {"id": "pax-dollar", "symbol": "USDP", "name": "Pax Dollar"},
    {"id": "first-digital-usd", "symbol": "FDUSD", "name": "First Digital USD"},
]


def fetch_stablecoins() -> dict:
    """Fetch stablecoin market caps."""
    cache = get_coingecko_cache()
    
    coin_ids = [c["id"] for c in STABLECOINS]
    result = cache.get_markets(vs_currency="usd", order="market_cap_desc",
                              per_page=100, page=1, price_change_percentage="24h")
    
    mcaps = {}
    if result["status"] == "ok":
        for coin in result["data"]:
            if coin["id"] in coin_ids:
                mcaps[coin["id"]] = {
                    "symbol": coin["symbol"].upper(),
                    "name": coin["name"],
                    "market_cap": coin.get("market_cap", 0),
                }
    
    return {
        "mcaps": mcaps,
        "timestamp": datetime.now().isoformat()
    }


def calculate_changes(history: dict, mcaps: dict) -> list:
    """Calculate 7d changes from history."""
    results = []
    
    for coin in STABLECOINS:
        coin_id = coin["id"]
        if coin_id not in mcaps:
            continue
        
        current_mcap = mcaps[coin_id]["market_cap"]
        change_7d = 0.0
        
        # Get historical snapshot for 7 days ago
        target_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        if coin_id in history:
            snapshots = history[coin_id].get("snapshots", {})
            if target_date in snapshots:
                old_mcap = snapshots[target_date]
                if old_mcap > 0:
                    change_7d = ((current_mcap - old_mcap) / old_mcap) * 100
        
        results.append({
            "symbol": mcaps[coin_id]["symbol"],
            "name": mcaps[coin_id]["name"],
            "current_mcap": current_mcap,
            "7d_change_pct": round(change_7d, 2),
        })
    
    return results


def save_stablecoins(data: dict):
    """Save stablecoin data to latest file."""
    with open(DATA_DIR / "stablecoins_latest.json", "w") as f:
        json.dump(data, f, indent=2)


def main():
    print("[Stablecoins] Fetching stablecoin data...")
    
    # Use daily cache
    raw_data = get_daily_data("Stablecoins", fetch_stablecoins, HISTORY_FILE)
    
    if "error" in raw_data:
        print(f"[Stablecoins] Error: {raw_data.get('error')}")
        return
    
    mcaps = raw_data.get("mcaps", {})
    
    # Load history for change calculation
    history = {}
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text())
        except:
            pass
    
    results = calculate_changes(history, mcaps)
    
    if results:
        total_mcap = sum(r["current_mcap"] for r in results)
        
        output = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "coins": results,
            "total_mcap": total_mcap,
        }
        
        for r in results:
            print(f"  {r['symbol']}: ${r['current_mcap']/1e9:.1f}B ({r['7d_change_pct']:+.2f}%)")
        
        save_stablecoins(output)
    else:
        print("[Stablecoins] No data")


if __name__ == "__main__":
    main()