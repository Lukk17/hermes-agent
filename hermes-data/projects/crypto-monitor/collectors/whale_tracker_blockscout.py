#!/usr/bin/env python3
"""
Whale Tracker - uses Blockscout API for whale balance tracking.

BTC: Mempool.space API (free, no key)
ETH: Blockscout API (1 call per whale for balance)

Usage: python3 whale_tracker_blockscout.py
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
REQUEST_DELAY = 0.3

MEMPOOL_BASE = "https://mempool.space/api"
BLOCKSCOUT_BASE = "https://eth.blockscout.com/api/v2"

# Will be loaded from settings in main()
BLOCKSCOUT_API_KEY = ""


def get_blockscout_api_key() -> str:
    """Get Blockscout API key from settings."""
    from src.config import load_config
    config = load_config()
    return config.get("api_keys", {}).get("blockscout", "")


def get_mempool_balance(addr: str) -> float:
    """Get BTC balance from Mempool - 1 API call."""
    try:
        url = f"{MEMPOOL_BASE}/address/{addr}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            funded = data.get("chain_stats", {}).get("funded_txo_sum", 0)
            spent = data.get("chain_stats", {}).get("spent_txo_sum", 0)
            return (funded - spent) / 100_000_000  # sats to BTC
    except Exception as e:
        return 0.0


def get_blockscout_balance(addr: str) -> float:
    """Get ETH balance from Blockscout - 1 API call."""
    if not BLOCKSCOUT_API_KEY:
        raise APIKeyMissingError(
            "Blockscout",
            "BLOCKSCOUT_API_KEY",
            "https://blockscout.com/apis"
        )
    try:
        url = f"{BLOCKSCOUT_BASE}/addresses/{addr}"
        req = Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "x-api-key": BLOCKSCOUT_API_KEY}
        )
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            balance_wei = int(data.get("coin_balance", "0") or 0)
            return balance_wei / 1e18
    except HTTPError as e:
        if e.code == 401 or e.code == 403:
            raise APIKeyMissingError(
                "Blockscout",
                "BLOCKSCOUT_API_KEY",
                "https://blockscout.com/apis"
            )
        return 0.0
    except URLError:
        return 0.0
    except Exception:
        return 0.0


def fetch_eth_price() -> float:
    """Fetch ETH price from CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("ethereum", {}).get("usd", 3500)
    except Exception:
        return 3500


def track_whales():
    """Track whale balances - 1 API call per whale."""
    global BLOCKSCOUT_API_KEY
    
    print("=" * 50)
    print("🐋 WHALE TRACKER (Blockscout)")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 50)

    # Load API key from settings
    BLOCKSCOUT_API_KEY = get_blockscout_api_key()

    eth_price = fetch_eth_price()
    btc_price = eth_price * 30  # rough estimate
    print(f"  💰 ETH: ${eth_price:,.2f} | BTC: ${btc_price:,.0f}")

    registry = load_json_safe(WHALE_REGISTRY_FILE) or {}
    btc_addresses = registry.get("bitcoin", {})
    eth_addresses = registry.get("ethereum", {})
    print(f"  📋 {len(btc_addresses)} BTC + {len(eth_addresses)} ETH addresses")
    print()

    btc_whales = []
    eth_whales = []
    date_key = datetime.utcnow().strftime("%Y-%m-%d")

    # BTC whales
    print("  ₿ BTC:")
    for addr, metadata in list(btc_addresses.items()):
        label = metadata.get("label", addr[:16])
        balance = get_mempool_balance(addr)
        time.sleep(REQUEST_DELAY)

        btc_whales.append({
            "label": label,
            "address": addr,
            "chain": "bitcoin",
            "balance_btc": balance,
            "balance_usd": balance * btc_price,
            "checked_at": datetime.utcnow().isoformat()
        })
        print(f"    {label}: {balance:,.2f} BTC")

    # ETH whales
    print("\n  ⟽ ETH:")
    eth_success = True
    for addr, metadata in list(eth_addresses.items()):
        label = metadata.get("label", addr[:16])
        try:
            balance = get_blockscout_balance(addr)
            time.sleep(REQUEST_DELAY)
            eth_whales.append({
                "label": label,
                "address": addr,
                "chain": "ethereum",
                "balance_eth": balance,
                "balance_usd": balance * eth_price,
                "category": metadata.get("category", "unknown"),
                "checked_at": datetime.utcnow().isoformat()
            })
            print(f"    {label}: {balance:,.2f} ETH")
        except APIKeyMissingError as e:
            print(f"    {label}: {e}")
            eth_success = False
            continue

    # Sort by balance
    btc_whales.sort(key=lambda x: x.get("balance_btc", 0), reverse=True)
    eth_whales.sort(key=lambda x: x.get("balance_eth", 0), reverse=True)

    # Save latest
    whales_data = {
        "bitcoin": btc_whales,
        "ethereum": eth_whales,
        "timestamp": datetime.utcnow().isoformat()
    }
    write_json_atomic(WHALE_DATA_FILE, whales_data)

    # Update history (everlasting)
    history = load_json_safe(WHALE_HISTORY_FILE) or {}
    history[date_key] = {
        "bitcoin": btc_whales,
        "ethereum": eth_whales,
        "timestamp": datetime.utcnow().isoformat()
    }
    history["last_updated"] = datetime.utcnow().isoformat()
    write_json_atomic(WHALE_HISTORY_FILE, history)

    total_calls = len(btc_addresses) + len(eth_addresses)
    print(f"\n✅ BTC: {len(btc_whales)} | ETH: {len(eth_whales)} whales")
    print(f"   Total API calls: {total_calls} (1 per whale)")


if __name__ == "__main__":
    try:
        track_whales()
    except APIKeyMissingError as e:
        print(str(e))
        error_collector.add_error("whale_tracker_blockscout", str(e), "warning")
