#!/usr/bin/env python3
"""
BTC Dominance Chart Generator
Creates a BTC dominance chart using historical data from dominance_history.json.
Fetches only current dominance from CoinGecko and appends to history.
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

DATA_DIR = PROJECT_ROOT / "data" / "dominance"
HISTORY_FILE = DATA_DIR / "dominance_history.json"
CHART_DIR = DATA_DIR / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})


def load_history() -> dict:
    """Load dominance history from file."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_history(history: dict):
    """Save dominance history to file."""
    history["last_updated"] = datetime.now().isoformat()
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def fetch_current_dominance() -> dict:
    """Fetch current BTC dominance (vs ALL crypto) from CoinGecko global."""
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Check if global data was already fetched by index_scraper (runs before this in pipeline)
    global_file = PROJECT_ROOT / "data" / "global_market" / "global_market_latest.json"
    if global_file.exists():
        try:
            data = json.loads(global_file.read_text())
            global_data = data.get("data", {})
            btc_dom = global_data.get("market_cap_percentage", {}).get("btc", 0)
            eth_dom = global_data.get("market_cap_percentage", {}).get("eth", 0)
            return {"btc_dominance": btc_dom, "eth_dominance": eth_dom, "source": "cache"}
        except:
            pass
    
    # Fallback: fetch from API
    try:
        url = API_ENDPOINTS.get("coingecko_global", "https://api.coingecko.com/api/v3/global")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        
        global_data = data.get("data", {})
        btc_dom = global_data.get("market_cap_percentage", {}).get("btc", 0)
        eth_dom = global_data.get("market_cap_percentage", {}).get("eth", 0)
        
        return {"btc_dominance": btc_dom, "eth_dominance": eth_dom}
        
    except Exception as e:
        print(f"[BTC dominance] Error fetching: {e}")
        return None


def generate_chart(history: dict):
    """Generate BTC dominance chart from history."""
    # Get date-keyed entries (skip last_updated)
    dates = [k for k in history.keys() if k != "last_updated" and k.startswith("20")]
    
    if not dates:
        print("[BTC dominance] No history data")
        return None
    
    # Sort by date properly (not alphabetically!) and get last 730 days
    sorted_dates = sorted(dates, key=lambda x: datetime.fromisoformat(x) if x.startswith("20") else datetime.min)
    if len(sorted_dates) > 730:
        sorted_dates = sorted_dates[-730:]
    
    timestamps = []
    btc_dominances = []
    eth_dominances = []
    
    for date_str in sorted_dates:
        entry = history.get(date_str, {})
        
        # Handle both old format and new format
        btc = entry.get("btc_dominance") or entry.get("current_btc")
        eth = entry.get("eth_dominance") or entry.get("current_eth")
        
        if btc and eth:
            try:
                timestamps.append(datetime.fromisoformat(date_str))
                btc_dominances.append(float(btc))
                eth_dominances.append(float(eth))
            except:
                pass
    
    if not timestamps:
        print("[BTC dominance] No valid data")
        return None
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 5), dpi=300)
    
    # Plot BTC dominance
    ax.plot(timestamps, btc_dominances, color='#F7931A', linewidth=2, label='BTC Dominance %')
    ax.fill_between(timestamps, btc_dominances, alpha=0.15, color='#F7931A')
    
    # Current BTC marker
    if timestamps and btc_dominances:
        ax.scatter([timestamps[-1]], [btc_dominances[-1]], color='#F7931A', s=80, zorder=5)
        ax.annotate(f'{btc_dominances[-1]:.1f}%', 
                   xy=(timestamps[-1], btc_dominances[-1]),
                   xytext=(10, 0), textcoords='offset points',
                   fontsize=16, fontweight='bold', color='#F7931A',
                   va='center')
    
    # ETH dominance line (not shown in legend)
    eth_line = [eth_dominances[-1]] * len(timestamps)
    ax.plot(timestamps, eth_line, color='#627EEA', linewidth=1.5, 
            linestyle='--', alpha=0.7)
    
    # Formatting - matching Coin Sentiment graph style
    ax.set_xlabel('Date', fontsize=24, color='gray')
    ax.set_ylabel('Dominance %', fontsize=24, color='gray')
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45, fontsize=20)
    plt.yticks(fontsize=20)
    
    # Set axis limits - full range for dominance (0-100%)
    ax.set_ylim(0, 100)
    ax.set_xlim(timestamps[0], timestamps[-1])
    
    ax.legend(loc='upper right', fontsize=16)
    ax.grid(True, alpha=0.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    chart_path = CHART_DIR / "btc_dominance_2y.png"
    plt.savefig(chart_path, dpi=300, facecolor='#1a1a1a', edgecolor='none')
    plt.close()
    
    print(f"[BTC dominance] Saved: {chart_path}")
    return chart_path


def main():
    print("[BTC dominance] Loading history...")
    history = load_history()
    
    # Fetch current dominance
    print("[BTC dominance] Fetching current dominance...")
    current = fetch_current_dominance()
    
    if current and current.get("btc_dominance"):
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Add/update today's entry
        history[today] = current
        save_history(history)
        print(f"[BTC dominance] Added {today}: BTC {current['btc_dominance']:.1f}%, ETH {current['eth_dominance']:.1f}%")
    else:
        print("[BTC dominance] Could not fetch current dominance")
    
    # Generate chart
    chart_path = generate_chart(history)
    if chart_path:
        print(f"[BTC dominance] Done: {chart_path}")


if __name__ == "__main__":
    main()
