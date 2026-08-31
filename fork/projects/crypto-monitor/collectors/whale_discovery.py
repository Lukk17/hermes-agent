#!/usr/bin/env python3
"""
Whale Discovery — find and suggest new whale addresses from public sources.

Scrapes:
  - Etherscan top accounts (ETH)
  - BitInfoCharts rich lists (BTC)
  - Known exchange PoR pages

Compares against existing whale_registry.json and suggests new addresses
worth tracking.

Usage:
  python3 collectors/whale_discovery.py              # Full discovery
  python3 collectors/whale_discovery.py --btc-only    # BTC only
  python3 collectors/whale_discovery.py --eth-only    # ETH only

Run weekly via cron to catch new whales.
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"
REGISTRY_FILE = BASE_DIR / "config" / "whale_registry.json"
REPORT_FILE = BASE_DIR / "data" / "whale_discovery_report.json"

# Load config
def load_config() -> dict:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})
THRESHOLDS = CONFIG.get("thresholds", {}).get("whale_discovery", {})

REQUEST_DELAY = 0.5

# Minimum balance to consider tracking
MIN_BTC_BALANCE = THRESHOLDS.get("min_btc_balance", 1000)
MIN_ETH_BALANCE = THRESHOLDS.get("min_eth_balance", 50000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_text(url: str, timeout: int = 20) -> str:
    """Fetch URL and return text content."""
    req = Request(url, headers={
        "Accept": "text/html,application/json",
        "User-Agent": "CryptoMonitor/2.0"
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, Exception) as e:
        print(f"  ❌ {e}")
        return ""
    finally:
        time.sleep(REQUEST_DELAY)


def _fetch_json(url: str, timeout: int = 20) -> dict | None:
    """Fetch URL and return JSON."""
    req = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "CryptoMonitor/2.0"
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (HTTPError, URLError, Exception) as e:
        print(f"  ❌ {e}")
        return None
    finally:
        time.sleep(REQUEST_DELAY)


def load_registry() -> dict:
    """Load existing whale registry."""
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    return {}


def is_known(address: str, chain: str, registry: dict) -> bool:
    """Check if address is already in registry."""
    chain_reg = registry.get(chain, {})
    if address in chain_reg:
        return True
    # Case-insensitive for ETH
    if chain == "ethereum":
        for reg_addr in chain_reg:
            if reg_addr.lower() == address.lower():
                return True
    return False


# ---------------------------------------------------------------------------
# Discovery sources
# ---------------------------------------------------------------------------

def discover_eth_whales(registry: dict) -> list:
    """Discover ETH whale addresses from Blockscout top accounts."""
    print("\n🔍 Discovering ETH whales...")
    discovered = []

    # Blockscout top addresses API
    print("  📡 Blockscout top addresses...")
    blockscout_url = API_ENDPOINTS.get("blockscout_addresses", "https://eth.blockscout.com/api/v2/addresses")
    data = _fetch_json(f"{blockscout_url}?sort=balance&order=desc")
    if data and "items" in data:
        for item in data["items"]:
            address = item.get("hash", "")
            balance = int(item.get("coin_balance", "0")) / 1e18
            is_contract = item.get("is_contract", False)
            name = item.get("name") or item.get("implementation_name") or ""

            if balance < MIN_ETH_BALANCE:
                continue
            if is_known(address, "ethereum", registry):
                continue

            discovered.append({
                "address": address,
                "chain": "ethereum",
                "balance": balance,
                "balance_fmt": f"{balance:,.0f} ETH",
                "label": name or f"ETH Whale ({address[:8]}...)",
                "is_contract": is_contract,
                "source": "blockscout",
            })

    print(f"  Found {len(discovered)} new ETH addresses")
    return discovered


def discover_btc_whales(registry: dict) -> list:
    """Discover BTC whale addresses from mempool.space and public lists."""
    print("\n🔍 Discovering BTC whales...")
    discovered = []

    # mempool.space doesn't have a "top addresses" API, so we search known sources
    # Check a few known large BTC addresses that might not be in our registry
    known_large = [
        ("bc1qa5wkgaew2dkv56kfvj49j0av5nml45x9ek9hz6", "Silk Road (FBI)"),
        ("385cR5DM96n1HvBDMzLHPYcw89fZAXULJP", "iFinex (Bitfinex parent)"),
        ("12ib7dApVFvg82TXKycWBNpN8kFyiAN1dr", "BTC Rich List #4"),
        ("12tkqA9xSoowkzoERHMWNKsTey55YEBqkv", "BTC Rich List #5"),
    ]

    for address, name in known_large:
        if is_known(address, "bitcoin", registry):
            continue

        # Check balance
        mempool_url = API_ENDPOINTS.get("mempool", "https://mempool.space/api")
        data = _fetch_json(f"{mempool_url}/address/{address}")
        if not data:
            continue

        chain = data.get("chain_stats", {})
        funded = chain.get("funded_txo_sum", 0)
        spent = chain.get("spent_txo_sum", 0)
        balance = (funded - spent) / 1e8

        if balance < MIN_BTC_BALANCE:
            continue

        discovered.append({
            "address": address,
            "chain": "bitcoin",
            "balance": balance,
            "balance_fmt": f"{balance:,.0f} BTC",
            "label": name,
            "tx_count": chain.get("tx_count", 0),
            "source": "mempool.space",
        })

    print(f"  Found {len(discovered)} new BTC addresses")
    return discovered


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_discovery(btc_only: bool = False, eth_only: bool = False) -> dict:
    """Run whale discovery and generate report."""
    print("=" * 60)
    print("🔍 WHALE DISCOVERY")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    registry = load_registry()
    btc_known = len(registry.get("bitcoin", {}))
    eth_known = len(registry.get("ethereum", {}))
    print(f"  Registry: {btc_known} BTC + {eth_known} ETH addresses")

    all_discovered = []

    if not eth_only:
        all_discovered.extend(discover_btc_whales(registry))
    if not btc_only:
        all_discovered.extend(discover_eth_whales(registry))

    # Sort by balance descending
    all_discovered.sort(key=lambda x: x.get("balance", 0), reverse=True)

    # Report
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "registry_size": {"bitcoin": btc_known, "ethereum": eth_known},
        "discovered": all_discovered,
        "count": len(all_discovered),
    }

    # Print results
    print(f"\n{'=' * 60}")
    print(f"📊 DISCOVERY RESULTS: {len(all_discovered)} new addresses")
    print("=" * 60)

    if all_discovered:
        for d in all_discovered[:20]:
            chain = "₿" if d["chain"] == "bitcoin" else "⟠"
            contract = " (contract)" if d.get("is_contract") else ""
            print(f"  {chain} {d['label']:35s} {d['balance_fmt']:>15s}{contract}")
            print(f"    {d['address']}")

        print(f"\n💡 To add to registry, update config/whale_registry.json")
    else:
        print("  No new whale addresses found. Registry is up to date.")

    # Save report
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n💾 Report saved to {REPORT_FILE.relative_to(BASE_DIR)}")

    return report


if __name__ == "__main__":
    btc_only = "--btc-only" in sys.argv
    eth_only = "--eth-only" in sys.argv
    run_discovery(btc_only=btc_only, eth_only=eth_only)
