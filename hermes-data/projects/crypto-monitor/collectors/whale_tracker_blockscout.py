#!/usr/bin/env python3
"""
Whale Tracker - uses Blockscout API for whale balance tracking.

BTC: Mempool.space API (free, no key)
ETH: Blockscout API (1 call per whale for balance)

Usage: python3 whale_tracker_blockscout.py
"""

import json
import os
import time
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import error_collector
from src.exceptions import APIKeyMissingError, RateLimitedError
from src.file_utils import write_json_atomic, load_json_safe
from src.paths import WHALE_REGISTRY_FILE, latest_file


WHALE_DATA_FILE = latest_file("whales", "whales")
WHALE_HISTORY_FILE = PROJECT_ROOT / "data" / "whales" / "whales_history.json"
REQUEST_DELAY = 0.3
REQUEST_TIMEOUT = 10
# Kept under report_generator.py's 60s per-step kill so a slow run still writes what it has.
DEADLINE_SECONDS = 45

MEMPOOL_BASE = "https://mempool.space/api"
BLOCKSCOUT_BASE = "https://eth.blockscout.com/api/v2"

BLOCKSCOUT_API_KEY = ""


def get_blockscout_api_key() -> str:
    """Get Blockscout API key from the environment."""
    return os.environ.get("BLOCKSCOUT_API_KEY", "")


def get_mempool_balance(addr: str) -> float | None:
    """Get BTC balance from Mempool, None when the address could not be read.

    Raises:
        RateLimitedError: mempool.space refused the request with HTTP 429.
    """
    try:
        url = f"{MEMPOOL_BASE}/address/{addr}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except HTTPError as e:
        if e.code == 429:
            raise RateLimitedError("mempool.space") from e
        return None
    except (URLError, OSError, ValueError):
        return None

    funded = data.get("chain_stats", {}).get("funded_txo_sum", 0)
    spent = data.get("chain_stats", {}).get("spent_txo_sum", 0)

    return (funded - spent) / 100_000_000  # sats to BTC


def get_blockscout_balance(addr: str) -> float | None:
    """Get ETH balance from Blockscout, None when the address could not be read.

    Raises:
        APIKeyMissingError: the key is unset or Blockscout rejected it.
        RateLimitedError: Blockscout refused the request with HTTP 429.
    """
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
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except HTTPError as e:
        if e.code in (401, 403):
            raise APIKeyMissingError(
                "Blockscout",
                "BLOCKSCOUT_API_KEY",
                "https://blockscout.com/apis"
            ) from e
        if e.code == 429:
            raise RateLimitedError("blockscout") from e
        return None
    except (URLError, OSError, ValueError):
        return None

    return int(data.get("coin_balance", "0") or 0) / 1e18


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
    unchecked = []
    date_key = datetime.utcnow().strftime("%Y-%m-%d")
    deadline = time.monotonic() + DEADLINE_SECONDS

    # BTC whales
    print("  ₿ BTC:")
    for index, (addr, metadata) in enumerate(list(btc_addresses.items())):
        label = metadata.get("label", addr[:16])
        remaining = len(btc_addresses) - index

        if time.monotonic() >= deadline:
            unchecked.append(f"deadline reached, {remaining} BTC addresses not checked")
            break

        try:
            balance = get_mempool_balance(addr)
        except RateLimitedError as e:
            unchecked.append(f"{e}, {remaining} BTC addresses not checked")
            break

        time.sleep(REQUEST_DELAY)

        if balance is None:
            print(f"    {label}: unavailable")
            continue

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
    for index, (addr, metadata) in enumerate(list(eth_addresses.items())):
        label = metadata.get("label", addr[:16])
        remaining = len(eth_addresses) - index

        if time.monotonic() >= deadline:
            unchecked.append(f"deadline reached, {remaining} ETH addresses not checked")
            break

        try:
            balance = get_blockscout_balance(addr)
        except (APIKeyMissingError, RateLimitedError) as e:
            unchecked.append(f"{e}, {remaining} ETH addresses not checked")
            break

        time.sleep(REQUEST_DELAY)

        if balance is None:
            print(f"    {label}: unavailable")
            continue

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

    # Sort by balance
    btc_whales.sort(key=lambda x: x.get("balance_btc", 0), reverse=True)
    eth_whales.sort(key=lambda x: x.get("balance_eth", 0), reverse=True)

    for note in unchecked:
        print(f"  WARNING: {note}")
        error_collector.add_error("whale_tracker_blockscout", note, "warning")

    if not btc_whales and not eth_whales:
        note = "no balances collected, previous whale data kept"
        print(f"  WARNING: {note}")
        error_collector.add_error("whale_tracker_blockscout", note, "warning")

        return

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
