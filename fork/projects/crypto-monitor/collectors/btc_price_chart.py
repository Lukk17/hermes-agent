#!/usr/bin/env python3
"""
BTC Price Chart Generator
Creates a BTC price chart using historical data from prices_history.json.
Fetches only current price from CoinGecko and appends to history.
"""

import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.json"

CHART_DIR = PROJECT_ROOT / "data" / "btc_price"
HISTORY_FILE = PROJECT_ROOT / "data" / "btc_price" / "btc_price_history.json"
CHART_DIR.mkdir(parents=True, exist_ok=True)

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})


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


def get_btc_price_from_coin_prices() -> dict:
    """Get BTC price from coin_prices_latest.json (already fetched by coin_prices_collector)."""
    try:
        coin_prices_file = PROJECT_ROOT / "data" / "coin_prices" / "coin_prices_latest.json"
        if not coin_prices_file.exists():
            print("[BTC price] coin_prices_latest.json not found, falling back to API")
            return fetch_current_price_from_api()
        
        with open(coin_prices_file) as f:
            data = json.load(f)
        
        coins = data.get("coins", [])
        btc = next((c for c in coins if c.get("id") == "bitcoin"), None)
        
        if btc and btc.get("price"):
            print(f"[BTC price] Got BTC price from coin_prices: ${btc['price']:,}")
            return {"price": btc["price"], "timestamp": data.get("timestamp", datetime.now().isoformat())}
        else:
            print("[BTC price] BTC not in coin_prices, falling back to API")
            return fetch_current_price_from_api()
            
    except Exception as e:
        print(f"[BTC price] Error reading coin_prices: {e}, falling back to API")
        return fetch_current_price_from_api()


def fetch_current_price_from_api() -> dict:
    """Fetch current BTC price from CoinGecko API (fallback only)."""
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        url = API_ENDPOINTS.get("coingecko_simple_price", "https://api.coingecko.com/api/v3/simple/price") + "?ids=bitcoin&vs_currencies=usd"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        
        btc_price = data.get("bitcoin", {}).get("usd", 0)
        return {"price": btc_price, "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        print(f"[BTC price] Error fetching current price: {e}")
        return None


def generate_chart(history: dict):
    """Generate BTC price chart from history."""
    btc_prices = history.get("btc_prices", {})
    
    if not btc_prices:
        print("[BTC price] No BTC price history")
        return None
    
    # Sort by date properly (not alphabetically!) and get last 730 days
    sorted_dates = sorted(btc_prices.keys(), key=lambda x: datetime.fromisoformat(x) if x.startswith("20") else datetime.min)
    if len(sorted_dates) > 730:
        sorted_dates = sorted_dates[-730:]
    
    timestamps = []
    prices = []
    
    for date_str in sorted_dates:
        price = btc_prices.get(date_str)
        if price:
            timestamps.append(datetime.fromisoformat(date_str))
            prices.append(price)
    
    if not timestamps:
        print("[BTC price] No valid price data")
        return None
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 5), dpi=300)
    
    # Title - only BTC price chart should have header
    ax.set_title('BTC Price (2Y)', fontsize=28, fontweight='bold', color='#e6edf3', pad=20)
    
    ax.plot(timestamps, prices, color='#F7931A', linewidth=2)
    ax.fill_between(timestamps, prices, alpha=0.15, color='#F7931A')
    
    if timestamps and prices:
        ax.scatter([timestamps[-1]], [prices[-1]], color='#F7931A', s=80, zorder=5)
        ax.annotate(f'${prices[-1]:,.0f}', 
                   xy=(timestamps[-1], prices[-1]),
                   xytext=(10, 0), textcoords='offset points',
                   fontsize=16, fontweight='bold', color='#F7931A',
                   va='center')
    
    # Formatting - matching Coin Sentiment graph style
    ax.set_xlabel('Date', fontsize=24, color='gray')
    ax.set_ylabel('Price (USD)', fontsize=24, color='gray')
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45, fontsize=20)
    plt.yticks(fontsize=20)
    
    ax.grid(True, alpha=0.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    chart_path = CHART_DIR / "btc_price_2y.png"
    plt.savefig(chart_path, dpi=300, facecolor='#1a1a1a', edgecolor='none')
    plt.close()
    
    print(f"[BTC price] Saved: {chart_path}")
    return chart_path


def main():
    print("[BTC price] Loading history...")
    history = load_history()
    
    # Ensure btc_prices key exists
    if "btc_prices" not in history:
        history["btc_prices"] = {}
    
    # Get BTC price from coin_prices_latest.json (already fetched by coin_prices_collector)
    print("[BTC price] Getting BTC price from coin_prices...")
    current = get_btc_price_from_coin_prices()
    
    if current and current.get("price"):
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Add/update today's price in history
        history["btc_prices"][today] = current["price"]
        save_history(history)
        print(f"[BTC price] Added {today}: ${current['price']:,}")
        
        # Also save latest
        latest_file = HISTORY_FILE.parent / "btc_price_latest.json"
        with open(latest_file, "w") as f:
            json.dump({"price": current["price"], "timestamp": current["timestamp"]}, f, indent=2)
    else:
        print("[BTC price] Could not fetch current price")
    
    # Generate chart
    chart_path = generate_chart(history)
    if chart_path:
        print(f"[BTC price] Done: {chart_path}")


if __name__ == "__main__":
    main()
