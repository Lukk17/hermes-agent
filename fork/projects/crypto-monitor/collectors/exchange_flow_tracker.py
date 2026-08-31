#!/usr/bin/env python3
"""
Exchange Flow Tracker — monitor exchange wallet balances and compute net flows.

Tracks BTC + ETH balances for top 5 exchanges (Binance, Coinbase, Kraken, Bybit, OKX).
Compares to previous snapshot to detect inflows/outflows.

Balance increase → inflow (coins deposited, bearish — potential sell pressure)
Balance decrease → outflow (coins withdrawn, bullish — accumulation)

Usage:
  python3 collectors/exchange_flow_tracker.py          # Full run
  python3 collectors/exchange_flow_tracker.py --quick   # Skip slow endpoints
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"
CONFIG_FILE = BASE_DIR / "config" / "exchange_wallets.json"
DATA_DIR = BASE_DIR / "data" / "exchange_flows"

# Load config
def load_config() -> dict:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})

# APIs (no keys needed)
MEMPOOL_API = API_ENDPOINTS.get("mempool", "https://mempool.space/api")
BLOCKSCOUT_ETH_API = API_ENDPOINTS.get("blockscout", "https://eth.blockscout.com/api/v2")

REQUEST_DELAY = 0.3  # Be polite


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _fetch(url: str, timeout: int = 20) -> dict | None:
    """Fetch JSON from URL with rate limiting."""
    req = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "CryptoMonitor/2.0"
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"    ❌ HTTP {e.code}: {url[:60]}...")
        return None
    except (URLError, Exception) as e:
        print(f"    ❌ {e}: {url[:60]}...")
        return None
    finally:
        time.sleep(REQUEST_DELAY)


def btc_balance(address: str) -> float | None:
    """Get BTC balance via mempool.space."""
    data = _fetch(f"{MEMPOOL_API}/address/{address}")
    if not data:
        return None
    chain = data.get("chain_stats", {})
    mempool = data.get("mempool_stats", {})
    funded = chain.get("funded_txo_sum", 0) + mempool.get("funded_txo_sum", 0)
    spent = chain.get("spent_txo_sum", 0) + mempool.get("spent_txo_sum", 0)
    return (funded - spent) / 1e8


def eth_balance(address: str) -> float | None:
    """Get ETH balance via Blockscout."""
    data = _fetch(f"{BLOCKSCOUT_ETH_API}/addresses/{address}")
    if not data or "coin_balance" not in data:
        return None
    return int(data["coin_balance"]) / 1e18


def btc_price() -> float | None:
    """Get current BTC price."""
    data = _fetch(f"{MEMPOOL_API}/v1/prices")
    return data.get("USD") if data else None


def eth_price() -> float | None:
    """Get current ETH price from Blockscout (any address lookup includes it)."""
    # Use a known address to get exchange rate
    data = _fetch(f"{BLOCKSCOUT_ETH_API}/addresses/0x0000000000000000000000000000000000000000")
    if data:
        return float(data.get("exchange_rate", 0))
    return None


# ---------------------------------------------------------------------------
# Load config + previous snapshot
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_previous() -> dict | None:
    """Load most recent snapshot for delta comparison."""
    latest = DATA_DIR / "exchange_flows_latest.json"
    if latest.exists():
        try:
            with open(latest) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return None


def save_snapshot(data: dict):
    """Save current snapshot."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write latest
    with open(DATA_DIR / "exchange_flows_latest.json", "w") as f:
        json.dump(data, f, indent=2)
    
    # Update history
    history_file = DATA_DIR / "exchange_flows_history.json"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    if history_file.exists():
        history = json.loads(history_file.read_text())
    else:
        history = {}
    
    # Use date as key (overwrites if exists)
    history[today] = data
    
    history["last_updated"] = datetime.utcnow().isoformat()
    
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)


# ---------------------------------------------------------------------------
# Main tracking
# ---------------------------------------------------------------------------

def track_exchange_balances(quick: bool = False) -> dict:
    """Fetch all exchange wallet balances."""
    print("=" * 60)
    print("🏦 EXCHANGE FLOW TRACKER")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    config = load_config()
    exchanges = config.get("exchanges", {})

    # Prices
    print("\n📈 Fetching prices...")
    btc_usd = btc_price()
    eth_usd = eth_price()
    print(f"  BTC: ${btc_usd:,.0f}" if btc_usd else "  BTC: ❌")
    print(f"  ETH: ${eth_usd:,.0f}" if eth_usd else "  ETH: ❌")

    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
        "prices": {"btc_usd": btc_usd, "eth_usd": eth_usd},
        "exchanges": {},
    }

    for name, chains in exchanges.items():
        print(f"\n🏛  {name}")
        ex_data = {"bitcoin": {}, "ethereum": {}}

        # --- BTC wallets ---
        btc_wallets = chains.get("bitcoin", [])
        btc_total = 0
        btc_ok = 0
        for w in btc_wallets:
            addr = w["address"]
            bal = btc_balance(addr)
            if bal is not None:
                btc_total += bal
                btc_ok += 1
                print(f"    ₿ {w['label']}: {bal:,.4f} BTC")
            else:
                print(f"    ₿ {w['label']}: ❌ failed")

        ex_data["bitcoin"] = {
            "total_btc": btc_total,
            "total_usd": btc_total * btc_usd if btc_usd else None,
            "wallets_ok": btc_ok,
            "wallets_total": len(btc_wallets),
        }

        # --- ETH wallets ---
        eth_wallets = chains.get("ethereum", [])
        eth_total = 0
        eth_ok = 0
        for w in eth_wallets:
            addr = w["address"]
            bal = eth_balance(addr)
            if bal is not None:
                eth_total += bal
                eth_ok += 1
                print(f"    ⟠ {w['label']}: {bal:,.2f} ETH")
            else:
                print(f"    ⟠ {w['label']}: ❌ failed")

        ex_data["ethereum"] = {
            "total_eth": eth_total,
            "total_usd": eth_total * eth_usd if eth_usd else None,
            "wallets_ok": eth_ok,
            "wallets_total": len(eth_wallets),
        }

        snapshot["exchanges"][name] = ex_data

    # --- Compute deltas ---
    prev = load_previous()
    snapshot["flows"] = compute_flows(snapshot, prev)

    # --- Print summary ---
    print_summary(snapshot)

    # --- Save ---
    save_snapshot(snapshot)
    print(f"\n💾 Saved to data/exchange_flows/")
    return snapshot


def compute_flows(current: dict, previous: dict | None) -> dict:
    """Compute per-exchange flow deltas vs previous snapshot."""
    flows = {}
    if not previous:
        return flows

    prev_ts = previous.get("timestamp", "?")
    print(f"\n📊 Computing deltas vs {prev_ts[:19]}")

    for name, cur_data in current.get("exchanges", {}).items():
        prev_data = previous.get("exchanges", {}).get(name, {})
        ex_flows = {}

        for chain, unit in [("bitcoin", "BTC"), ("ethereum", "ETH")]:
            cur_chain = cur_data.get(chain, {})
            prev_chain = prev_data.get(chain, {})

            cur_total = cur_chain.get(f"total_{unit.lower()}", 0)
            prev_total = prev_chain.get(f"total_{unit.lower()}", 0)

            if prev_total > 0 and cur_total > 0:
                delta = cur_total - prev_total
                pct = (delta / prev_total * 100) if prev_total else 0
                # Positive delta = balance grew = inflow (bearish)
                # Negative delta = balance shrunk = outflow (bullish)
                signal = "bearish" if delta > 0 else "bullish" if delta < 0 else "neutral"
                ex_flows[chain] = {
                    "delta": delta,
                    "delta_pct": pct,
                    "signal": signal,
                    "unit": unit,
                    "current": cur_total,
                    "previous": prev_total,
                }

        flows[name] = ex_flows

    return flows


def print_summary(snapshot: dict):
    """Print human-readable summary."""
    flows = snapshot.get("flows", {})
    if not flows:
        print("\n⚠️  No previous snapshot — first run, deltas will appear next time")
        return

    print("\n" + "=" * 60)
    print("📊 EXCHANGE FLOW SUMMARY")
    print("=" * 60)

    for name, chains in flows.items():
        print(f"\n  {name}:")
        for chain, f in chains.items():
            delta = f["delta"]
            unit = f["unit"]
            signal = f["signal"]
            arrow = "→ IN" if delta > 0 else "← OUT" if delta < 0 else "  --"
            emoji = "🔴" if signal == "bearish" else "🟢" if signal == "bullish" else "⚪"
            print(f"    {emoji} {unit}: {delta:+,.4f} {unit} ({f['delta_pct']:+.2f}%) {arrow}")

    # Aggregate
    print(f"\n  Aggregate:")
    for chain, unit in [("bitcoin", "BTC"), ("ethereum", "ETH")]:
        total_delta = sum(
            f.get(chain, {}).get("delta", 0)
            for f in flows.values()
        )
        if total_delta != 0:
            direction = "INFLOW (bearish)" if total_delta > 0 else "OUTFLOW (bullish)"
            print(f"    Net {unit}: {total_delta:+,.4f} {unit} — {direction}")


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    track_exchange_balances(quick)
