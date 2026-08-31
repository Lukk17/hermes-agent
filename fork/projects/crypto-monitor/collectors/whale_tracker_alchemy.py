#!/usr/bin/env python3
"""
ETH Whale Tracker - uses Alchemy API for ETH whale balance tracking.

Only fetches current balance per whale - simple and efficient.

Usage: python3 whale_tracker_alchemy.py
"""

import json
import time
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import error_collector
from src.exceptions import APIKeyMissingError
from src.file_utils import write_json_atomic, load_json_safe
from src.paths import WHALE_REGISTRY_FILE, latest_file


WHALE_DATA_FILE = latest_file("whales", "whales")
WHALE_HISTORY_FILE = PROJECT_ROOT / "data" / "whales" / "whales_history.json"
REQUEST_DELAY = 0.1


def get_alchemy_api_key() -> str:
    """Get Alchemy API key from settings."""
    from src.config import load_config
    config = load_config()
    return config.get("api_keys", {}).get("alchemy", "")


def alchemy_call(method: str, params: list = None) -> dict:
    """Make a single Alchemy JSON-RPC call."""
    if not ALCHEMY_API_KEY:
        raise APIKeyMissingError(
            "Alchemy",
            "ALCHEMY_API_KEY",
            "https://alchemy.com/api"
        )

    base_url = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}

    try:
        req = Request(
            base_url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            if "error" in result:
                return {"error": result["error"]}
            return {"status": "ok", "data": result.get("result", {})}
    except HTTPError as e:
        if e.code == 401 or e.code == 403:
            raise APIKeyMissingError(
                "Alchemy",
                "ALCHEMY_API_KEY",
                "https://alchemy.com/api"
            )
        return {"error": f"HTTP {e.code}"}
    except URLError as e:
        return {"error": f"URL error: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def get_eth_balance(address: str) -> float:
    """Get ETH balance for an address - single API call."""
    result = alchemy_call("eth_getBalance", [address, "latest"])
    if "error" in result:
        return 0.0
    balance_wei = int(result["data"], 16) if result["data"] else 0
    return balance_wei / 1e18


def fetch_eth_price() -> float:
    """Fetch ETH price from CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("ethereum", {}).get("usd", 3500)
    except Exception:
        return 3500


def track_eth_whales():
    """Track ETH whale balances - ONE API CALL PER WHALE."""
    global ALCHEMY_API_KEY
    
    print("=" * 50)
    print("🐋 ETH WHALE TRACKER (Alchemy)")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 50)

    # Load API key from settings
    ALCHEMY_API_KEY = get_alchemy_api_key()

    eth_price = fetch_eth_price()
    print(f"  💰 ETH: ${eth_price:,.2f}")

    registry = load_json_safe(WHALE_REGISTRY_FILE) or {}
    eth_addresses = registry.get("ethereum", {})
    print(f"  📋 {len(eth_addresses)} ETH addresses")
    print()

    eth_whales = []
    date_key = datetime.utcnow().strftime("%Y-%m-%d")

    for addr, metadata in list(eth_addresses.items()):
        label = metadata.get("label", addr[:16])
        try:
            balance = get_eth_balance(addr)
            time.sleep(REQUEST_DELAY)
        except APIKeyMissingError as e:
            print(f"  {label}: {e}")
            raise e

        whale = {
            "label": label,
            "address": addr,
            "chain": "ethereum",
            "balance_eth": balance,
            "balance_usd": balance * eth_price,
            "category": metadata.get("category", "unknown"),
            "checked_at": datetime.utcnow().isoformat()
        }
        eth_whales.append(whale)
        print(f"  {label}: {balance:,.2f} ETH")

    # Sort by balance
    eth_whales.sort(key=lambda x: x.get("balance_eth", 0), reverse=True)

    # Merge with existing whale data (keep BTC from other trackers)
    existing = load_json_safe(WHALE_DATA_FILE) or {
        "bitcoin": [],
        "ethereum": [],
        "timestamp": ""
    }
    existing["ethereum"] = eth_whales
    existing["timestamp"] = datetime.utcnow().isoformat()
    write_json_atomic(WHALE_DATA_FILE, existing)

    # Update history (everlasting)
    history = load_json_safe(WHALE_HISTORY_FILE) or {}
    history[date_key] = {"ethereum": eth_whales, "timestamp": datetime.utcnow().isoformat()}
    history["last_updated"] = datetime.utcnow().isoformat()
    write_json_atomic(WHALE_HISTORY_FILE, history)

    print(f"\n✅ Tracked {len(eth_whales)} ETH whales")
    print(f"   Total API calls: {len(eth_addresses)} (1 per whale)")


if __name__ == "__main__":
    global ALCHEMY_API_KEY
    ALCHEMY_API_KEY = get_alchemy_api_key()
    
    if not ALCHEMY_API_KEY:
        e = APIKeyMissingError(
            "Alchemy",
            "ALCHEMY_API_KEY",
            "https://alchemy.com/api"
        )
        print(str(e))
        error_collector.add_error("whale_tracker_alchemy", str(e), "warning")
    else:
        try:
            track_eth_whales()
        except APIKeyMissingError as e:
            error_collector.add_error("whale_tracker_alchemy", str(e), "warning")
