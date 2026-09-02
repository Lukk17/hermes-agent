#!/usr/bin/env python3
"""
External Index Scraper
Compares our calculated values against established external sources.

Sources:
- alternative.me (Fear & Greed Index) - has free API
- coinglass (Fear & Greed, Cycle indicators)
- blockchaincenter (Bull/Bear, Altseason)
- coinmarketcap (BTC dominance)
- coingecko (BTC dominance)
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.json"

DATA_DIR = PROJECT_ROOT / "data" / "external_indices"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})

# ascend-web service for JS-rendered pages
ASCEND_WEB = API_ENDPOINTS.get("ascend_web", "http://host.docker.internal:7021")


class IndexScraper:
    def __init__(self):
        self.results = {}
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    
    def _scrape(self, url: str) -> dict:
        """Scrape using ascend-web (Playwright) for JS-rendered pages."""
        try:
            import urllib.parse
            api_url = f"{ASCEND_WEB}/api/v1/web/read?url={urllib.parse.quote(url)}"
            req = urllib.request.Request(api_url, headers=self._headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                if data.get("content", {}).get("status") == "success":
                    return {"status": "ok", "data": data["content"]["content"]}
                return {"status": "error", "error": "scrape failed"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _get(self, url: str, timeout: int = 10) -> dict:
        """Make GET request using urllib."""
        try:
            req = urllib.request.Request(url, headers=self._headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                return {"status": "ok", "data": data}
        except urllib.error.HTTPError as e:
            return {"status": "error", "error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return {"status": "error", "error": f"URL error: {e.reason}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def fetch_fear_greed_alternative_me(self):
        """Fetch Fear & Greed Index from alternative.me (free API)."""
        url = API_ENDPOINTS.get("fear_greed", "https://api.alternative.me/fng/")
        result = self._get(url)
        
        if result["status"] == "ok":
            data = result["data"]
            if data.get("data"):
                latest = data["data"][0]
                value = int(latest["value"])
                classification = latest["value_classification"]
                timestamp = int(latest["timestamp"])
                date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                
                return {
                    "source": "alternative.me",
                    "value": value,
                    "classification": classification,
                    "date": date,
                    "status": "ok"
                }
        
        return {"source": "alternative.me", "status": result.get("status", "error"), 
                "error": result.get("error", "no_data")}
    
    def fetch_fear_greed_coinglass(self):
        """Fetch Fear & Greed Index from coinglass.
        
        NOTE: fapi.coinglass.io DNS resolution fails from container.
        Keeping method for reference - returns error with explanation.
        """
        # Try alternate URL
        url = API_ENDPOINTS.get("coinglass", "https://www.coinglass.com/api/proxy/index/FearGreed")
        result = self._get(url)
        
        if result["status"] == "ok":
            data = result["data"]
            try:
                value = data.get("data", [{}])[0].get("fgi") or data.get("fgi")
                if value is not None:
                    return {
                        "source": "coinglass",
                        "value": int(value),
                        "classification": self._classify_fg(int(value)),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "status": "ok"
                    }
            except:
                pass
        
        return {"source": "coinglass", "status": "error",
                "error": "DNS failed: fapi.coinglass.io unreachable from container. Try alternative.me."}
    
    def fetch_btc_dominance_coingecko(self):
        """Fetch BTC dominance from CoinGecko."""
        url = API_ENDPOINTS.get("coingecko_global", "https://api.coingecko.com/api/v3/global")
        result = self._get(url)
        
        if result["status"] == "ok":
            data = result["data"]
            btc_dom = data.get("data", {}).get("market_cap_percentage", {}).get("btc")
            if btc_dom:
                return {
                    "source": "coingecko",
                    "value": round(btc_dom, 1),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "status": "ok"
                }
        
        return {"source": "coingecko", "status": result.get("status", "error"),
                "error": result.get("error", "no_data")}
    
    def fetch_altseason_blockchaincenter(self):
        """Fetch Altseason Index from blockchaincenter using ascend-web."""
        url = API_ENDPOINTS.get("blockchaincenter_altseason", "https://www.blockchaincenter.net/en/altcoin-season-index/")
        result = self._scrape(url)
        
        if result["status"] == "ok":
            data = result["data"]
            # Look for the main index number (e.g., "53" in "It is not Altcoin Season! 53")
            match = re.search(r'(?:not Altcoin Season!|Altcoin Season Index)\s*(\d+)', data)
            if match:
                value = int(match.group(1))
                return {
                    "source": "blockchaincenter",
                    "value": value,
                    "classification": "Altseason" if value > 75 else "Bitcoin Season" if value < 25 else "Neutral",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "status": "ok"
                }
        
        return {"source": "blockchaincenter", "status": "error",
                "error": result.get("error", "failed to extract altseason")}
    
    def fetch_bull_bear_blockchaincenter(self):
        """Fetch Bull/Bear Index from blockchaincenter using ascend-web.
        
        NOTE: The bull/bear page is now a crowdsourced poll, not a numerical index.
        """
        # Try the crowdsourced sentiment page
        url = API_ENDPOINTS.get("blockchaincenter_bullbear", "https://www.blockchaincenter.net/en/bull-bear-sentiment/")
        result = self._scrape(url)
        
        if result["status"] == "ok":
            data = result["data"]
            # This is now a crowdsourced poll, no numerical index
            # Return a note that this is crowdsourced
            return {
                "source": "blockchaincenter",
                "status": "error",
                "error": "Site now uses crowdsourced poll (no numerical index). Use alternative.me F&G."
            }
        
        return {"source": "blockchaincenter", "status": "error",
                "error": result.get("error", "scrape failed")}
    
    def fetch_cbbi_index(self):
        """Fetch Colin Talks Crypto Bull/Bear Index using ascend-web.
        
        NOTE: CBBI has disabled some metrics, but may still have a score.
        """
        url = API_ENDPOINTS.get("coinbase_cbbi", "https://colintalkscrypto.com/cbbi/")
        result = self._scrape(url)
        
        if result["status"] == "ok":
            data = result["data"]
            # Look for confidence score or "we are at the peak" value
            match = re.search(r'(?:WE ARE AT THE PEAK|confidence|score)[\s:]*(\d+)', data, re.IGNORECASE)
            if match and match.group(1) != "--":
                return {
                    "source": "colintalkscrypto",
                    "value": int(match.group(1)),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "status": "ok"
                }
            # Check if disabled
            if "metrics are disabled" in data.lower():
                return {"source": "colintalkscrypto", "status": "error",
                        "error": "CBBI metrics currently disabled."}
        
        return {"source": "colintalkscrypto", "status": "error",
                "error": result.get("error", "scrape failed")}
    
    def _classify_fg(self, value):
        """Classify Fear & Greed value."""
        if value <= 25:
            return "Extreme Fear"
        elif value <= 45:
            return "Fear"
        elif value <= 55:
            return "Neutral"
        elif value <= 75:
            return "Greed"
        else:
            return "Extreme Greed"
    
    def fetch_all(self):
        """Fetch all external indices."""
        print("[IndexScraper] Fetching external indices...")
        
        # Fear & Greed - alternative.me (free API, works)
        print("  - Fear & Greed (alternative.me)...")
        self.results["fear_greed"] = {
            "alternative_me": self.fetch_fear_greed_alternative_me(),
        }
        
        # Coinglass - DNS fails from container, skip
        # print("  - Fear & Greed (coinglass)...")
        # self.results["fear_greed"]["coinglass"] = self.fetch_fear_greed_coinglass()
        
        # BTC Dominance - coingecko (works)
        print("  - BTC Dominance...")
        self.results["btc_dominance"] = self.fetch_btc_dominance_coingecko()
        
        # Altseason - blockchaincenter via ascend-web (works)
        print("  - Altseason Index...")
        self.results["altseason"] = self.fetch_altseason_blockchaincenter()
        
        # Bull/Bear - no reliable source (crowdsourced poll, no CBBI data)
        # Skip - F&G is sufficient for sentiment
        
        # CBBI - metrics disabled
        # Skip - no reliable alternative
        
        self._save()
        return self.results
    
    def _save(self):
        """Save results to JSON - split into separate folders."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Fear & Greed
        fg_data = self.results.get("fear_greed", {})
        self._save_to_folder("fear_greed", fg_data, "fear_greed_latest.json")
        
        # Global Market
        global_data = self.results.get("global", {})
        self._save_to_folder("global_market", global_data, "global_market_latest.json")
        
        # Trending
        trending_data = self.results.get("trending", {})
        self._save_to_folder("trending", trending_data, "trending_latest.json")
        
        # BTC Dominance (already in dominance folder)
        btc_dom_data = {"btc_dominance": self.results.get("btc_dominance")}
        self._save_to_folder("dominance", btc_dom_data, "dominance_latest.json")
        
        # Also save combined external_indices to single file for report
        ext_folder = PROJECT_ROOT / "data" / "external_indices"
        ext_folder.mkdir(parents=True, exist_ok=True)
        ext_path = ext_folder / "external_indices_latest.json"
        with open(ext_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "data": self.results  # Use "data" key for report compatibility
            }, f, indent=2)
        
        print(f"[IndexScraper] Saved to separate folders")
    
    def _save_to_folder(self, folder_name: str, data: dict, latest_filename: str):
        """Save data to separate folder."""
        folder = PROJECT_ROOT / "data" / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        
        # Save latest
        latest_path = folder / latest_filename
        with open(latest_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "data": data
            }, f, indent=2)
        
        # Update history
        history_file = folder / f"{folder_name}_history.json"
        today = datetime.now().strftime("%Y-%m-%d")
        
        if history_file.exists():
            history = json.loads(history_file.read_text())
        else:
            history = {}
        
        history[today] = data
        history["last_updated"] = datetime.now().isoformat()
        
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
    
    def get_comparison_table(self, our_values: dict = None):
        """Generate comparison table: our values vs external sources."""
        table_lines = [
            "┌──────────────────────┬───────────┬───────────┬────────┐",
            "│ Indicator            │    Ours   │ External  │  Diff  │",
            "├──────────────────────┼───────────┼───────────┼────────┤",
        ]
        
        # Fear & Greed comparison
        if "fear_greed" in self.results:
            alt_me = self.results["fear_greed"].get("alternative_me", {})
            
            if alt_me.get("status") == "ok":
                ext_val = alt_me.get("value", "N/A")
                our_fg = our_values.get("fear_greed") if our_values else None
                
                if our_fg is not None:
                    diff = our_fg - ext_val
                    diff_str = f"{diff:+.0f}" if isinstance(diff, (int, float)) else "N/A"
                    table_lines.append(
                        f"│ Fear & Greed (alt.me)│ {our_fg:>9} │ {ext_val:>9} │ {diff_str:>6} │"
                    )
                else:
                    table_lines.append(
                        f"│ Fear & Greed (alt.me)│      N/A │ {ext_val:>9} │    N/A │"
                    )
        
        # BTC Dominance comparison
        if "btc_dominance" in self.results:
            btc_dom = self.results["btc_dominance"]
            if btc_dom.get("status") == "ok":
                ext_val = btc_dom.get("value", "N/A")
                our_btc = our_values.get("btc_dominance") if our_values else None
                
                if our_btc is not None:
                    diff = our_btc - ext_val
                    diff_str = f"{diff:+.1f}%" if isinstance(diff, (int, float)) else "N/A"
                    table_lines.append(
                        f"│ BTC Dominance        │   {our_btc:>6.1f}% │   {ext_val:>6.1f}% │ {diff_str:>6} │"
                    )
                else:
                    table_lines.append(
                        f"│ BTC Dominance        │     N/A │   {ext_val:>6.1f}% │    N/A │"
                    )
        
        # Altseason comparison
        if "altseason" in self.results:
            altseason = self.results["altseason"]
            if altseason.get("status") == "ok":
                ext_val = altseason.get("value", "N/A")
                ext_class = altseason.get("classification", "")
                our_alt = our_values.get("altseason") if our_values else None
                
                if our_alt is not None:
                    diff = our_alt - ext_val
                    diff_str = f"{diff:+.0f}" if isinstance(diff, (int, float)) else "N/A"
                    table_lines.append(
                        f"│ Altseason (BC)       │ {our_alt:>9} │ {ext_val:>9} │ {diff_str:>6} │"
                    )
                else:
                    table_lines.append(
                        f"│ Altseason (BC) [{ext_class[:6]:>6}]│      N/A │ {ext_val:>9} │    N/A │"
                    )
        
        table_lines.append("└──────────────────────┴───────────┴───────────┴────────┘")
        
        return "\n".join(table_lines)
    
    def get_summary(self) -> dict:
        """Get a summary dict for use in reports."""
        summary = {}
        
        # Fear & Greed - take average of available sources
        fg_values = []
        if "fear_greed" in self.results:
            for source, data in self.results["fear_greed"].items():
                if data.get("status") == "ok" and data.get("value") is not None:
                    fg_values.append(data["value"])
        
        if fg_values:
            summary["fear_greed"] = {
                "value": round(sum(fg_values) / len(fg_values)),
                "sources": len(fg_values),
                "classification": self._classify_fg(round(sum(fg_values) / len(fg_values)))
            }
        
        # BTC Dominance
        if "btc_dominance" in self.results:
            btc = self.results["btc_dominance"]
            if btc.get("status") == "ok":
                summary["btc_dominance"] = btc.get("value")
        
        # Altseason
        if "altseason" in self.results:
            alt = self.results["altseason"]
            if alt.get("status") == "ok":
                summary["altseason"] = {
                    "value": alt.get("value"),
                    "classification": alt.get("classification")
                }
        
        # Bull/Bear
        if "bull_bear" in self.results:
            bb = self.results["bull_bear"]
            if bb.get("status") == "ok":
                summary["bull_bear"] = bb.get("value")
        
        return summary


def main():
    scraper = IndexScraper()
    results = scraper.fetch_all()
    
    print("\n[IndexScraper] Results:")
    print(json.dumps(results, indent=2))
    
    # Print comparison table
    print("\n[IndexScraper] Comparison Table:")
    print(scraper.get_comparison_table())
    
    # Print summary
    print("\n[IndexScraper] Summary:")
    print(json.dumps(scraper.get_summary(), indent=2))
    
    return results


if __name__ == "__main__":
    main()
