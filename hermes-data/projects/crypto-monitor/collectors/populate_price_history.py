#!/usr/bin/env python3
"""
One-time: Populate BTC Price History using Yahoo Finance
Fetches ~2 years of BTC price history and saves to prices_history.json.
Uses Yahoo Finance (no rate limits for this volume).

This script is important - it populates the historical data that btc_price_chart.py 
uses to generate charts. Run this once to get full 2-year history, then btc_price_chart.py
will only fetch current price each run.

Usage: python3 populate_price_history.py
"""

import json
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
HISTORY_FILE = PROJECT_ROOT / "data" / "btc_price" / "btc_price_history.json"


def load_history() -> dict:
    """Load prices history from file."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"fear_greed": [], "global": [], "prices": [], "trending": [], "btc_prices": {}, "last_updated": None}


def save_history(history: dict):
    """Save prices history to file."""
    history["last_updated"] = datetime.now().isoformat()
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def fetch_yahoo_btc() -> dict:
    """Fetch BTC price history from Yahoo Finance."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?range=2y&interval=1d"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    
    result = data.get('chart', {}).get('result', [])
    if not result:
        return None
    
    ts = result[0].get('timestamp', [])
    close_prices = result[0].get('indicators', {}).get('quote', [{}])[0].get('close', [])
    
    prices = {}
    for i, timestamp in enumerate(ts):
        if close_prices[i] is not None:
            date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            prices[date_str] = close_prices[i]
    
    return prices


def main():
    print("=" * 50)
    print("POPULATING BTC PRICE HISTORY (Yahoo Finance)")
    print("=" * 50)
    
    history = load_history()
    
    if "btc_prices" not in history:
        history["btc_prices"] = {}
    
    existing_count = len(history["btc_prices"])
    print(f"Existing prices: {existing_count}")
    
    print("\nFetching BTC price history from Yahoo Finance...")
    btc_prices = fetch_yahoo_btc()
    
    if not btc_prices:
        print("Error: Could not fetch data")
        return
    
    print(f"Got {len(btc_prices)} price points from Yahoo")
    
    added = 0
    for date_str, price in btc_prices.items():
        if date_str not in history["btc_prices"]:
            history["btc_prices"][date_str] = price
            added += 1
    
    print(f"Added {added} new prices")
    
    save_history(history)
    print(f"\nTotal prices now: {len(history['btc_prices'])}")
    print("Done!")
    
    print("\n" + "=" * 50)
    print("HOW THIS WORKS:")
    print("=" * 50)
    print("""
This one-time script fetches 2 years of BTC price history from Yahoo Finance.

After running this:
- btc_price_chart.py loads prices from prices_history.json
- It fetches ONLY today's price (1 API call)
- Adds it to history
- Generates chart from local history

This way we don't hit rate limits on every report.
Keep this script - it's needed if we ever need to repopulate history.
""")


if __name__ == "__main__":
    main()
