#!/usr/bin/env python3
"""
DeFi TVL Collector
Tracks Total Value Locked in DeFi from CoinGecko.

Uses daily history cache to avoid redundant API calls.
Source: CoinGecko API (free)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cache_manager import get_coingecko_cache, get_daily_data

DATA_DIR = PROJECT_ROOT / "data" / "defi"
HISTORY_FILE = DATA_DIR / "defi_history.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_tvl() -> dict:
    """Fetch DeFi data from CoinGecko."""
    cache = get_coingecko_cache()
    result = cache.get_global()
    
    if result["status"] != "ok":
        error_msg = result.get("error", "API error")
        print(f"[DeFi TVL] ERROR: {error_msg}")
        return {"status": "error", "error": error_msg, "total_defi_mcap": 0, "defi_vs_eth_ratio": 0}
    
    global_data = result["data"]["data"]
    defi_data = global_data.get("defi_data", {})
    
    return {
        "status": "ok",
        "error": None,
        "total_defi_mcap": defi_data.get("defi_market_cap", 0),
        "defi_vs_eth_ratio": defi_data.get("defi_to_eth_ratio", 0),
    }


def save_tvl(data: dict):
    """Save TVL to latest file."""
    with open(DATA_DIR / "defi_latest.json", "w") as f:
        json.dump(data, f, indent=2)


def main():
    print("[DeFi TVL] Fetching DeFi data...")
    
    # Use daily cache
    tvl_data = get_daily_data("DeFiTVL", fetch_tvl, HISTORY_FILE)
    
    if tvl_data.get("status") == "error":
        print(f"[DeFi TVL] ERROR: {tvl_data.get('error', 'Unknown error')} - Data may be stale")
    else:
        save_tvl(tvl_data)
        print(f"  DeFi MCap: ${tvl_data.get('total_defi_mcap', 0)/1e9:.1f}B")
        print(f"  DeFi/ETH Ratio: {tvl_data.get('defi_vs_eth_ratio', 0):.4f}")


if __name__ == "__main__":
    main()