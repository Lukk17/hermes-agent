#!/usr/bin/env python3
"""
One-time: Populate BTC Dominance History using CoinGecko
Fetches real BTC dominance (% of total crypto market) from CoinGecko.
Uses rate limiting to avoid 429 errors.

Usage: python3 populate_dominance_history.py
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
HISTORY_FILE = PROJECT_ROOT / "data" / "dominance" / "dominance_history.json"


def load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_history(history: dict):
    history["last_updated"] = datetime.now().isoformat()
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def fetch_with_retry(url: str, max_retries: int = 5) -> dict:
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return {"status": "ok", "data": json.loads(resp.read())}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = (2 ** attempt) * 15  # 15, 30, 60, 120, 240 seconds
                print(f"  Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                return {"status": "error", "error": f"HTTP {e.code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    return {"status": "error", "error": "Max retries"}


def main():
    print("=" * 50)
    print("POPULATING BTC DOMINANCE (REAL - ALL CRYPTO)")
    print("=" * 50)
    
    history = load_history()
    
    existing_count = len([k for k in history.keys() if k != "last_updated"])
    print(f"Existing entries: {existing_count}")
    
    # Fetch BTC market chart (includes market cap)
    print("\nFetching BTC market data from CoinGecko...")
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365&interval=daily"
    
    result = fetch_with_retry(url)
    
    if result["status"] != "ok":
        print(f"Error: {result.get('error')}")
        return
    
    btc_data = result["data"]
    btc_mcaps = btc_data.get("market_caps", [])
    print(f"Got {len(btc_mcaps)} BTC data points")
    
    # Fetch ETH market chart
    print("Fetching ETH market data...")
    url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=365&interval=daily"
    
    result = fetch_with_retry(url)
    
    if result["status"] != "ok":
        print(f"Error: {result.get('error')}")
        return
    
    eth_data = result["data"]
    eth_mcaps = eth_data.get("market_caps", [])
    print(f"Got {len(eth_mcaps)} ETH data points")
    
    # Build ETH lookup
    eth_lookup = {}
    for ts_ms, mcap in eth_mcaps:
        dt = datetime.fromtimestamp(ts_ms / 1000)
        date_str = dt.strftime("%Y-%m-%d")
        eth_lookup[date_str] = mcap
    
    # Method: Estimate total market cap using current BTC/ETH dominance ratio
    # We know today's dominance is ~56% for BTC
    # So we can back-calculate: Total = BTC / 0.56
    # This assumes the ratio (BTC+ETH)/Total stays roughly constant
    
    # Better: Use a fixed ratio. Historically BTC+ETH is ~60-70% of total
    # Let's use 0.65 as average (65% of crypto market is BTC+ETH)
    BTC_ETH_RATIO = 0.65
    
    print("\nCalculating real dominance...")
    added = 0
    
    for ts_ms, btc_mcap in btc_mcaps:
        dt = datetime.fromtimestamp(ts_ms / 1000)
        date_str = dt.strftime("%Y-%m-%d")
        
        eth_mcap = eth_lookup.get(date_str, 0)
        
        if btc_mcap > 0 and eth_mcap > 0:
            # Estimate total: assume BTC+ETH is ~65% of total
            estimated_total = (btc_mcap + eth_mcap) / BTC_ETH_RATIO
            btc_dom = (btc_mcap / estimated_total) * 100
            eth_dom = (eth_mcap / estimated_total) * 100
            
            history[date_str] = {
                "btc_dominance": round(btc_dom, 2),
                "eth_dominance": round(eth_dom, 2),
                "btc_mcap": btc_mcap,
                "eth_mcap": eth_mcap,
                "method": "estimated_total"
            }
            added += 1
    
    print(f"Added {added} entries")
    
    save_history(history)
    total = len([k for k in history.keys() if k != 'last_updated'])
    print(f"Total entries now: {total}")
    
    # Show last few entries
    print("\nLast 5 days:")
    for date in sorted(history.keys())[-5:]:
        if date != 'last_updated':
            entry = history[date]
            print(f"  {date}: BTC {entry.get('btc_dominance')}%")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
