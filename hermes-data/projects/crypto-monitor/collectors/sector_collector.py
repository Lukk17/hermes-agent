#!/usr/bin/env python3
"""
Crypto Sector Collector
Simplified version - calculates sector performance from top coins.

Uses daily history cache to avoid redundant API calls.

Usage: python3 sector_collector.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cache_manager import get_coingecko_cache, get_daily_data

DATA_DIR = PROJECT_ROOT / "data" / "sectors"
HISTORY_FILE = DATA_DIR / "sectors_history.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_sectors() -> dict:
    """Fetch and calculate sector data."""
    cache = get_coingecko_cache()
    result = cache.get_markets(vs_currency="usd", order="market_cap_desc",
                               per_page=100, page=1, price_change_percentage="24h")
    
    if result["status"] != "ok":
        error_msg = result.get("error", "API error")
        print(f"[SectorCollector] ERROR: {error_msg}")
        return {"status": "error", "error": error_msg, "sectors": [], "timestamp": datetime.now().isoformat()}
    
    coins = result["data"]
    
    # Group by sector/category
    sectors = {}
    
    for coin in coins:
        name = coin.get("name", "").lower()
        change = coin.get("price_change_percentage_24h", 0) or 0
        
        # Simple categorization based on name
        sector = "Other"
        if any(x in name for x in ["bitcoin", "btc"]):
            sector = "Bitcoin"
        elif any(x in name for x in ["ethereum", "eth"]):
            sector = "Ethereum"
        elif any(x in name for x in ["solana", "sol"]):
            sector = "L1"
        elif any(x in name for x in ["bnb", "binance"]):
            sector = "Exchange"
        elif any(x in name for x in ["chainlink", "uniswap", "aave", "maker", "compound"]):
            sector = "DeFi"
        elif any(x in name for x in ["doge", "shiba", "pepe", "floki", "bonk"]):
            sector = "Meme"
        elif any(x in name for x in ["render", "fetch", "ocean", "singularity"]):
            sector = "AI"
        elif any(x in name for x in ["arbitrum", "optimism", "base", "avalanche", "polygon", "matic", "zk"]):
            sector = "L2"
        
        if sector not in sectors:
            sectors[sector] = {"changes": [], "count": 0}
        sectors[sector]["changes"].append(change)
        sectors[sector]["count"] += 1
    
    # Calculate average change per sector
    sector_list = []
    for name, data in sectors.items():
        avg_change = sum(data["changes"]) / len(data["changes"]) if data["changes"] else 0
        sector_list.append({
            "name": name,
            "full_name": name,
            "change_24h": round(avg_change, 1),
            "change_7d": 0.0,
        })
    
    sector_list.sort(key=lambda x: x.get("count", 0), reverse=True)
    
    return {
        "status": "ok",
        "error": None,
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "sectors": sector_list[:8]
    }


def save_sectors(data: dict):
    """Save sectors to latest file."""
    with open(DATA_DIR / "sectors_latest.json", "w") as f:
        json.dump(data, f, indent=2)


def main():
    print("[SectorCollector] Fetching sectors...")
    
    # Use daily cache - only calls API if today's data not saved yet
    data = get_daily_data("SectorCollector", fetch_sectors, HISTORY_FILE)
    
    if data.get("status") == "error":
        print(f"[SectorCollector] ERROR: {data.get('error', 'Unknown error')} - Data may be stale")
    elif data.get("sectors"):
        save_sectors(data)
        sectors = data.get("sectors", [])
        print(f"[SectorCollector] Found {len(sectors)} sectors: {[s['name'] for s in sectors]}")
    else:
        print(f"[SectorCollector] WARNING: No sectors fetched")


if __name__ == "__main__":
    main()