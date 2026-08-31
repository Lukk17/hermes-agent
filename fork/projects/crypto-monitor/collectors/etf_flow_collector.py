#!/usr/bin/env python3
"""
ETF Flows Collector
Tracks Bitcoin Spot ETF inflows/outflows.

Source: Farside Investors (farside.co.uk) - scraped via ascend-web
"""

import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.json"

DATA_DIR = PROJECT_ROOT / "data" / "etf_flows"
HISTORY_FILE = DATA_DIR / "etf_flows_history.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})


def load_history():
    """Load ETF history."""
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except:
            return {}
    return {}


def save_history(history: dict):
    """Save ETF history."""
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def update_history(data: dict):
    """Update history with today's data."""
    today = datetime.now().strftime("%Y-%m-%d")
    history = load_history()
    history[today] = data
    save_history(history)


class ETFFlowCollector:
    def __init__(self):
        self.results = {}
        self._headers = {"User-Agent": "Mozilla/5.0"}
    
    def _scrape(self, url: str) -> str:
        """Scrape using ascend-web (v2 POST API)."""
        try:
            ascend_web = API_ENDPOINTS.get("ascend_web", "http://host.docker.internal:7021")
            api_url = f"{ascend_web}/api/v2/web/read"
            
            # POST request with JSON body
            req = urllib.request.Request(
                api_url,
                data=json.dumps({"url": url}).encode("utf-8"),
                headers={**self._headers, "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                # Handle response format
                content = data
                if isinstance(data, dict):
                    if data.get("content"):
                        if isinstance(data["content"], str):
                            content = data["content"]
                        elif isinstance(data["content"], dict):
                            content = data["content"].get("content", str(data))
                    else:
                        content = str(data)
                return content if isinstance(content, str) else str(content)
        except Exception as e:
            print(f"Scrape error: {e}")
        return ""
    
    def _parse_flows(self, content: str, etfs: list) -> list:
        """Parse ETF flows from HTML content."""
        daily_flows = []
        
        # Pattern: date like "05 Feb 2026" followed by numbers
        # Values in parentheses are negative
        date_pattern = r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})'
        
        # Find all dates and their associated values
        matches = re.finditer(date_pattern, content)
        
        for match in matches:
            date_str = match.group(1)
            # Get content after the date
            start_pos = match.end()
            
            # Find next date or section header
            next_match = re.search(date_pattern, content[start_pos:])
            if next_match:
                end_pos = start_pos + next_match.start()
            else:
                end_pos = min(start_pos + 200, len(content))
            
            row_content = content[start_pos:end_pos]
            
            # Extract all numbers (including negative in parentheses)
            numbers = re.findall(r'[\(\-]?(\d+\.?\d*)[\)]?', row_content)
            
            # Filter to get meaningful values (not just small numbers)
            values = []
            for n in numbers:
                try:
                    val = float(n)
                    # Check if preceding char was ( or -
                    idx = row_content.find(n)
                    if idx > 0 and (row_content[idx-1] == '(' or row_content[idx-1] == '-'):
                        val = -val
                    # Check if followed by )
                    if idx + len(n) < len(row_content) and row_content[idx + len(n)] == ')':
                        val = -val
                    values.append(val)
                except:
                    continue
            
            # We expect: values for each ETF + total
            if len(values) >= len(etfs) + 1:
                flows = {}
                total = 0
                for i, etf in enumerate(etfs):
                    if i < len(values):
                        flows[etf] = values[i]
                        total += values[i]
                
                daily_flows.append({
                    "date": date_str,
                    "flows": flows,
                    "total": total
                })
        
        return daily_flows
    
    def _calculate_stats(self, daily_flows: list) -> dict:
        """Calculate stats from daily flows."""
        if not daily_flows:
            return {}
        
        # Get latest (may not be today)
        latest = daily_flows[-1]
        latest_date = latest.get("date", "N/A")
        latest_total = latest.get("total", 0)
        
        # Calculate stats (exclude zeros - not updated yet)
        valid_flows = [d for d in daily_flows if d.get("total", 0) != 0]
        total_inflow = sum(d["total"] for d in valid_flows)
        avg_daily = total_inflow / len(valid_flows) if valid_flows else 0
        
        direction = "inflow" if latest_total > 0 else "outflow" if latest_total < 0 else "neutral"
        
        return {
            "latest_total": latest_total,
            "latest_date": latest_date,
            "direction": direction,
            "recent_7d_total": round(total_inflow, 1),
            "recent_7d_avg": round(avg_daily, 1),
        }
    
    def fetch_etf_flows(self):
        """Fetch BTC and ETH ETF flows from Farside."""
        print("[ETFFlows] Fetching from Farside Investors...")
        
        # BTC ETF tickers (in order from the table)
        btc_etfs = ["IBIT", "FBTC", "BITB", "ARKB", "BTCO", "EZBC", "BRRR", "HODL", "BTCW", "GBTC", "BTC"]
        
        # ETH ETF tickers
        eth_etfs = ["ETHA", "FETH", "ETHW", "TETH", "ETHV", "QETH", "EZET", "ETHE", "ETH"]
        
        result = {
            "source": "farside.co.uk",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "btc": {},
            "eth": {}
        }
        
        # Fetch BTC
        farside_btc = API_ENDPOINTS.get("farside_btc", "https://farside.co.uk/btc/")
        content = self._scrape(farside_btc)
        if content and len(content) > 100:
            btc_flows = self._parse_flows(content, btc_etfs)
            if btc_flows:
                btc_stats = self._calculate_stats(btc_flows)
                result["btc"] = btc_stats
                print(f"  BTC: {btc_stats.get('latest_date')} - ${btc_stats.get('latest_total', 0):.1f}M ({btc_stats.get('direction')})")
            else:
                print("  BTC: No flows parsed")
        else:
            print("  BTC: No content")
        
        # Fetch ETH
        farside_eth = API_ENDPOINTS.get("farside_eth", "https://farside.co.uk/eth/")
        content = self._scrape(farside_eth)
        if content and len(content) > 100:
            eth_flows = self._parse_flows(content, eth_etfs)
            if eth_flows:
                eth_stats = self._calculate_stats(eth_flows)
                result["eth"] = eth_stats
                print(f"  ETH: {eth_stats.get('latest_date')} - ${eth_stats.get('latest_total', 0):.1f}M ({eth_stats.get('direction')})")
            else:
                print("  ETH: No flows parsed")
        else:
            print("  ETH: No content")
        
        return result
    
    def fetch_all(self):
        """Fetch all ETF data."""
        data = self.fetch_etf_flows()
        
        self.results = data
        
        # Write latest
        with open(DATA_DIR / "etf_flows_latest.json", "w") as f:
            json.dump(data, f, indent=2)
        
        # Update history
        today = datetime.now().strftime("%Y-%m-%d")
        
        if HISTORY_FILE.exists():
            history = json.loads(HISTORY_FILE.read_text())
        else:
            history = {}
        
        # Use date as key (overwrites if exists)
        history[today] = data
        
        history["last_updated"] = datetime.now().isoformat()
        
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
        
        print(f"[ETFFlows] Saved")


if __name__ == "__main__":
    collector = ETFFlowCollector()
    collector.fetch_all()
