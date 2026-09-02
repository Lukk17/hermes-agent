#!/usr/bin/env python3
"""
ETH Gas Collector
Tracks ETH gas fees.

Source: BlockNative API (free, no key needed)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.json"

DATA_DIR = PROJECT_ROOT / "data" / "gas"
CHART_DIR = DATA_DIR / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})

# Import matplotlib for charts
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


class GasCollector:
    def __init__(self):
        self.results = {}
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def _get(self, url: str, timeout: int = 10) -> dict:
        """Make GET request."""
        try:
            import urllib.request
            req = urllib.request.Request(url, headers=self._headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                return {"status": "ok", "data": data}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def fetch_current(self):
        """Fetch current ETH gas from BlockNative."""
        url = API_ENDPOINTS.get("blocknative_gas", "https://api.blocknative.com/gasprices/blockprices")
        result = self._get(url)
        
        if result["status"] == "ok":
            data = result["data"]
            
            # Extract gas prices
            block_prices = data.get("blockPrices", [{}])[0]
            estimated = block_prices.get("estimatedPrices", [{}])[0]
            
            # Get different confidence levels
            prices_99 = next((p for p in block_prices.get("estimatedPrices", []) 
                            if p.get("confidence") == 99), {})
            prices_95 = next((p for p in block_prices.get("estimatedPrices", []) 
                            if p.get("confidence") == 95), {})
            prices_70 = next((p for p in block_prices.get("estimatedPrices", []) 
                            if p.get("confidence") == 70), {})
            
            base_fee = block_prices.get("baseFeePerGas", 0)
            
            # Convert to Gwei
            fast_gas = prices_99.get("price", 0)
            normal_gas = prices_95.get("price", 0)
            slow_gas = prices_70.get("price", 0)
            
            return {
                "status": "ok",
                "error": None,
                "source": "blocknative",
                "fast": round(fast_gas, 2),
                "normal": round(normal_gas, 2),
                "slow": round(slow_gas, 2),
                "base_fee": round(base_fee, 2),
                "unit": "gwei",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time": datetime.now().strftime("%H:%M"),
            }
        
        error_msg = result.get("error", "Unknown error")
        print(f"[GasCollector] ERROR: {error_msg}")
        return {"status": "error", "error": error_msg, "source": "blocknative"}
    
    def fetch_all(self):
        """Fetch all gas data."""
        print("[GasCollector] Fetching ETH gas from BlockNative...")
        
        gas_data = self.fetch_current()
        
        if gas_data.get("status") == "ok":
            self.results = {
                "status": "ok",
                "error": None,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "current": gas_data
            }
            print(f"  Fast: {gas_data['fast']} gwei")
            print(f"  Normal: {gas_data['normal']} gwei")
            print(f"  Slow: {gas_data['slow']} gwei")
        else:
            error_msg = gas_data.get("error", "Unknown error")
            print(f"[GasCollector] ERROR: {error_msg}")
            self.results = {"status": "error", "error": error_msg}
        
        self._save()
        return self.results
    
    def _save(self):
        """Save results to JSON."""
        # Write latest
        latest_path = DATA_DIR / "gas_latest.json"
        with open(latest_path, "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Update history
        history_file = DATA_DIR / "gas_history.json"
        today = datetime.now().strftime("%Y-%m-%d")
        
        if history_file.exists():
            history = json.loads(history_file.read_text())
        else:
            history = {}
        
        new_entry = {
            "fast": self.results.get("current", {}).get("fast", 0),
            "normal": self.results.get("current", {}).get("normal", 0),
            "slow": self.results.get("current", {}).get("slow", 0),
            "base_fee": self.results.get("current", {}).get("base_fee", 0),
        }
        
        history[today] = new_entry
        history["last_updated"] = datetime.now().isoformat()
        
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
        
        print(f"[GasCollector] Saved")
    
    def get_current_text(self) -> str:
        """Get current gas as text for report."""
        current = self.results.get("current", {})
        if self.results.get("status") == "error":
            return f"⚠️ **Gas data unavailable: {self.results.get('error', 'Unknown error')}**"
        
        if current.get("status") != "ok":
            return "⚠️ **Gas data unavailable**"
        
        return f"**Fast:** {current['fast']} gwei | **Normal:** {current['normal']} gwei | **Slow:** {current['slow']} gwei"


def generate_gas_chart() -> str:
    """Generate 1-year ETH gas history chart. Returns chart path or None."""
    history_path = DATA_DIR / "gas_history.json"
    
    if not history_path.exists():
        print("[GasChart] No history data yet")
        return None
    
    try:
        history_data = json.loads(history_path.read_text())
        history = history_data.get("records", [])
        if not history:
            for date, entry in history_data.items():
                if date not in ["last_updated", "timestamp"] and isinstance(entry, dict):
                    history.append(entry)
    except:
        print("[GasChart] Failed to read history")
        return None
    
    if len(history) < 2:
        print(f"[GasChart] Not enough data points: {len(history)}")
        return None
    
    # Calculate 12-month max/min
    fast_values = [h.get('fast', 0) + h.get('base_fee', 0) for h in history]
    max_gas = max(fast_values) if fast_values else 0
    min_gas = min(fast_values) if fast_values else 0
    
    # Save for report
    with open(DATA_DIR / "gas_stats.json", "w") as f:
        json.dump({
            "max_12m": round(max_gas, 2),
            "min_12m": round(min_gas, 2),
            "current": round(fast_values[-1], 2) if fast_values else 0
        }, f)
    
    print(f"[GasChart] 12m range: {min_gas:.2f} - {max_gas:.2f} gwei")
    
    # Parse dates and values
    dates = []
    fast_gas = []
    normal_gas = []
    slow_gas = []
    
    for entry in history:
        try:
            dates.append(datetime.strptime(entry.get("date", ""), "%Y-%m-%d"))
            base = entry.get("base_fee", 0)
            fast_gas.append(base + entry.get("fast", 0))
            normal_gas.append(base + entry.get("normal", 0))
            slow_gas.append(base + entry.get("slow", 0))
        except:
            continue
    
    if not dates:
        print("[GasChart] No valid data points")
        return None
    
    BG = "#0d1117"
    CARD = "#161b22"
    TEXT = "#ffffff"
    MUTED = "#8b949e"
    BLUE = "#58a6ff"
    GREEN = "#7ee787"
    ORANGE = "#f0883e"
    
    fig, ax = plt.subplots(figsize=(12, 4), facecolor=BG)
    ax.set_facecolor(CARD)
    
    ax.set_title("ETH Gas History (1Y)", color=TEXT, fontsize=14, fontweight="bold", pad=12)
    
    ax.plot(dates, fast_gas, color=ORANGE, linewidth=1.5, label="Fast", alpha=0.8)
    ax.plot(dates, normal_gas, color=BLUE, linewidth=1.5, label="Normal", alpha=0.8)
    ax.plot(dates, slow_gas, color=GREEN, linewidth=1.5, label="Slow", alpha=0.8)
    
    ax.set_ylabel("Gas (Gwei)", color=MUTED, fontsize=10)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.spines["left"].set_color(MUTED)
    
    ax.legend(facecolor=CARD, edgecolor=MUTED, labelcolor=MUTED, fontsize=9)
    
    if fast_gas:
        ax.annotate(f"Current: {fast_gas[-1]:.1f} gwei", 
                   xy=(dates[-1], fast_gas[-1]),
                   xytext=(10, 0), textcoords="offset points",
                   color=ORANGE, fontsize=9)
    
    fig.tight_layout()
    
    chart_path = CHART_DIR / "gas_history_1y.png"
    fig.savefig(chart_path, dpi=150, facecolor=BG)
    plt.close(fig)
    
    print(f"[GasChart] Saved to {chart_path}")
    return str(chart_path)


if __name__ == "__main__":
    collector = GasCollector()
    collector.fetch_all()
    print("\n[GasCollector] Current:", collector.get_current_text())
    
    print("\n[GasChart] Generating chart...")
    generate_gas_chart()