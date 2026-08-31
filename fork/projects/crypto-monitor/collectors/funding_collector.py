#!/usr/bin/env python3
"""
Funding Rates Collector
Tracks perpetual futures funding rates across exchanges.

Source: Bybit API (free, no key needed)
Positive = Longs pay shorts (bullish)
Negative = Shorts pay longs (bearish)
"""

import json
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.json"

DATA_DIR = PROJECT_ROOT / "data" / "funding"
HISTORY_FILE = DATA_DIR / "funding_history.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})


def load_history():
    """Load funding history."""
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except:
            return {}
    return {}


def save_history(history: dict):
    """Save funding history."""
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def update_history(data: dict):
    """Update history with today's data."""
    today = datetime.now().strftime("%Y-%m-%d")
    history = load_history()
    history[today] = data
    save_history(history)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT"]


class FundingCollector:
    def __init__(self):
        self.results = {}
        self._headers = {"User-Agent": "Mozilla/5.0"}
    
    def _get(self, url: str) -> dict:
        try:
            req = urllib.request.Request(url, headers=self._headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"status": "ok", "data": json.loads(resp.read())}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def fetch_funding(self):
        """Fetch funding rates from Bybit."""
        results = []
        bybit_url = API_ENDPOINTS.get("bybit", "https://api.bybit.com/v5/market/tickers")
        
        for symbol in SYMBOLS:
            url = f"{bybit_url}?category=linear&symbol={symbol}"
            result = self._get(url)
            
            if result["status"] == "ok":
                data = result["data"]
                items = data.get("result", {}).get("list", [])
                
                if items:
                    item = items[0]
                    funding_rate = item.get("fundingRate", "0")
                    try:
                        funding_pct = float(funding_rate) * 100
                    except:
                        funding_pct = 0
                    
                    # Get coin name
                    coin = symbol.replace("USDT", "")
                    
                    results.append({
                        "symbol": coin,
                        "funding_rate_pct": round(funding_pct, 4),
                        "direction": "longs_pay" if funding_pct > 0 else "shorts_pay" if funding_pct < 0 else "neutral"
                    })
        
        return results
    
    def fetch_all(self):
        print("[Funding] Fetching from Bybit...")
        
        funding_data = self.fetch_funding()
        
        if funding_data:
            # Calculate overall sentiment
            positive = sum(1 for f in funding_data if f["funding_rate_pct"] > 0)
            negative = sum(1 for f in funding_data if f["funding_rate_pct"] < 0)
            
            if positive > negative:
                sentiment = "bullish"
            elif negative > positive:
                sentiment = "bearish"
            else:
                sentiment = "neutral"
            
            # Average funding
            avg_funding = sum(f["funding_rate_pct"] for f in funding_data) / len(funding_data)
            
            self.results = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "rates": funding_data,
                "avg_funding": round(avg_funding, 4),
                "sentiment": sentiment,
                "positive_count": positive,
                "negative_count": negative,
            }
            
            for f in funding_data:
                print(f"  {f['symbol']}: {f['funding_rate_pct']:+.4f}%")
            
            print(f"  Avg: {avg_funding:+.4f}% ({sentiment})")
        else:
            self.results = {"error": "Failed to fetch funding data"}
        
        self._save()
        return self.results
    
    def _save(self):
        # Write latest
        with open(DATA_DIR / "funding_latest.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Update history
        history_file = DATA_DIR / "funding_history.json"
        today = datetime.now().strftime("%Y-%m-%d")
        
        if history_file.exists():
            history = json.loads(history_file.read_text())
        else:
            history = {}
        
        # Use date as key (overwrites if exists)
        history[today] = self.results
        
        history["last_updated"] = datetime.now().isoformat()
        
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
        
        print(f"[Funding] Saved")


if __name__ == "__main__":
    collector = FundingCollector()
    collector.fetch_all()
