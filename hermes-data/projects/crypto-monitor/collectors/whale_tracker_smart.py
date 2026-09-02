#!/usr/bin/env python3
"""
Smart Whale Tracker - fetches balance, detects changes, analyzes transactions only when needed.

Flow:
1. Fetch all balances (1 call per whale)
2. Compare to yesterday's balances
3. If balance changed → fetch & analyze transactions → generate signal
4. If no change → skip (save API calls)

Usage: python3 whale_tracker_smart.py
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request

PROJECT_ROOT = Path(__file__).parent.parent
SETTINGS_FILE = PROJECT_ROOT / "config" / "settings.json"
REGISTRY_FILE = PROJECT_ROOT / "config" / "whale_registry.json"
WHALE_DATA_FILE = PROJECT_ROOT / "data" / "whales" / "whales_latest.json"
WHALE_HISTORY_FILE = PROJECT_ROOT / "data" / "whales" / "whales_history.json"
WHALE_CHANGES_FILE = PROJECT_ROOT / "data" / "whales" / "whale_changes_latest.json"
REQUEST_DELAY = 0.2

ALCHEMY_API_KEY = os.environ.get("ALCHEMY_API_KEY", "")
ALCHEMY_BASE_URL = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
BLOCKSCOUT_API_KEY = os.environ.get("BLOCKSCOUT_API_KEY", "")
BLOCKSCOUT_BASE = "https://eth.blockscout.com/api/v2"
MEMPOOL_BASE = "https://mempool.space/api"

# Known exchange addresses for destination analysis
EXCHANGE_ADDRESSES = {
    # Binance
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance",
    "0x56eddb7aa87536c09ccc2793473599fd21a8b17f": "Binance",
    "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8": "Binance",
    "0xF977814e90dA44bFA03b6295A0616a897441aceC": "Binance",
    # Coinbase
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase",
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": "Coinbase",
    "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740": "Coinbase",
    # Kraken
    "0x2910543af39aba0cd09dbb2d50200b3e800a63d2": "Kraken",
    "0x9f1799fb47b1514f453bcebbc37ecfe883756e83": "Kraken",
    "0x8d05d9924fe935bd533a844271a1b2078eae6fcf": "Kraken",
    # Bybit
    "0xf89d7b9c864f589bbf53a82105107622b35eaa40": "Bybit",
    "0xee5b5b923ffce93a870b3104b7ca09c3db80047a": "Bybit",
    # OKX
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX",
}


def load_json(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


# ============ API CALLS ============

def alchemy_call(method: str, params: list = None) -> dict:
    if not ALCHEMY_API_KEY:
        return {"error": "No Alchemy API key"}
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    try:
        req = Request(ALCHEMY_BASE_URL, data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return {"status": "ok", "data": result.get("result", {})}
    except Exception as e:
        return {"error": str(e)}


def get_alchemy_balance(address: str) -> float:
    result = alchemy_call("eth_getBalance", [address, "latest"])
    if "error" in result:
        return 0.0
    balance_wei = int(result["data"], 16) if result["data"] else 0
    return balance_wei / 1e18


def get_alchemy_transactions(address: str, days: int = 1) -> list:
    """Get recent transactions using Alchemy's getAssetTransfers."""
    # Calculate block number for X days ago (approx 12 sec blocks)
    blocks_per_day = 7200
    from_block = hex(max(1, 20000000 - (blocks_per_day * days)))  # rough estimate

    params = {
        "fromBlock": from_block,
        "toBlock": "latest",
        "category": ["coin"],
        "withMetadata": True,
        "excludeZeroValue": True,
        "maxCount": "0x3e8",
    }

    all_txs = []

    # Check both directions
    for direction in ["fromAddress", "toAddress"]:
        params[direction] = address
        page_key = None

        while True:
            query_params = {**params}
            if page_key:
                query_params["pageKey"] = page_key

            result = alchemy_call("alchemy_getAssetTransfers", [query_params])
            if "error" in result:
                break

            transfers = result.get("data", {}).get("transfers", [])
            if not transfers:
                break

            for tx in transfers:
                value_eth = int(tx.get("value", "0"), 16) / 1e18 if tx.get("value") else 0
                all_txs.append({
                    "hash": tx.get("hash"),
                    "from": tx.get("from"),
                    "to": tx.get("to"),
                    "value_eth": value_eth,
                    "timestamp": tx.get("metadata", {}).get("blockTimestamp"),
                })

            page_key = result.get("data", {}).get("pageKey")
            if not page_key:
                break

            time.sleep(REQUEST_DELAY)

        time.sleep(REQUEST_DELAY)

    return all_txs


def get_blockscout_balance(address: str) -> float:
    if not BLOCKSCOUT_API_KEY:
        return 0.0
    try:
        url = f"{BLOCKSCOUT_BASE}/addresses/{address}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0", "x-api-key": BLOCKSCOUT_API_KEY})
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return int(data.get("coin_balance", "0") or 0) / 1e18
    except:
        return 0.0


def get_blockscout_transactions(address: str, days: int = 1) -> list:
    """Get recent transactions from Blockscout."""
    all_txs = []
    page = 1

    while page <= 5:  # Limit pages for API efficiency
        try:
            url = f"{BLOCKSCOUT_BASE}/addresses/{address}/transactions?limit=50&page={page}"
            req = Request(url, headers={"User-Agent": "Mozilla/5.0", "x-api-key": BLOCKSCOUT_API_KEY})
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                items = data.get("items", [])
                if not items:
                    break

                for tx in items:
                    value_eth = int(tx.get("value", 0)) / 1e18
                    all_txs.append({
                        "hash": tx.get("hash"),
                        "from": tx.get("from", {}).get("hash") if isinstance(tx.get("from"), dict) else tx.get("from"),
                        "to": tx.get("to", {}).get("hash") if isinstance(tx.get("to"), dict) else tx.get("to"),
                        "value_eth": value_eth,
                        "timestamp": tx.get("timestamp"),
                    })

                if not data.get("next_page_params"):
                    break
                page += 1
                time.sleep(REQUEST_DELAY)
        except:
            break

    return all_txs


def get_mempool_balance(address: str) -> float:
    try:
        url = f"{MEMPOOL_BASE}/address/{address}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            funded = data.get("chain_stats", {}).get("funded_txo_sum", 0)
            spent = data.get("chain_stats", {}).get("spent_txo_sum", 0)
            return (funded - spent) / 100_000_000
    except:
        return 0.0


def fetch_eth_price() -> float:
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("ethereum", {}).get("usd", 3500)
    except:
        return 3500


def fetch_btc_price() -> float:
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("bitcoin", {}).get("usd", 65000)
    except:
        return 65000


# ============ ANALYSIS ============

def analyze_transactions(txs: list, whale_address: str, direction: str, balance_change: float) -> dict:
    """Analyze transactions to determine what happened."""
    if not txs:
        return {"signal": "unknown", "summary": "No transactions found"}

    # Filter relevant txs (significant value)
    significant_txs = [tx for tx in txs if tx.get("value_eth", 0) > abs(balance_change) * 0.1]
    if not significant_txs:
        significant_txs = txs[:5]  # Use first 5 if nothing significant

    # Analyze direction and destination
    if direction == "outflow":
        # Whale is SELLING/DISTRIBUTING
        largest_out = max(significant_txs, key=lambda x: x.get("value_eth", 0))
        dest = largest_out.get("to", "")

        if dest in EXCHANGE_ADDRESSES:
            exchange = EXCHANGE_ADDRESSES[dest]
            signal = "distributing_to_exchange"
            emoji = "🔴"
            summary = f"Dumped {abs(balance_change):,.0f} ETH → {exchange}"
        elif dest.startswith("0x"):
            signal = "distributing_to_wallet"
            emoji = "🟡"
            summary = f"Moved {abs(balance_change):,.0f} ETH → unknown wallet"
        else:
            signal = "distributing"
            emoji = "🟡"
            summary = f"Distributed {abs(balance_change):,.0f} ETH"

    else:  # inflow
        largest_in = max(significant_txs, key=lambda x: x.get("value_eth", 0))
        source = largest_in.get("from", "")

        if source in EXCHANGE_ADDRESSES:
            exchange = EXCHANGE_ADDRESSES[source]
            signal = "accumulating_from_exchange"
            emoji = "🟢"
            summary = f"Accumulated +{balance_change:,.0f} ETH from {exchange}"
        elif source.startswith("0x"):
            signal = "accumulating_from_wallet"
            emoji = "🟢"
            summary = f"Accumulated +{balance_change:,.0f} ETH from unknown"
        else:
            signal = "accumulating"
            emoji = "🟢"
            summary = f"Accumulated +{balance_change:,.0f} ETH"

    return {
        "signal": signal,
        "emoji": emoji,
        "summary": summary,
        "direction": direction,
        "change_abs": abs(balance_change),
        "top_tx": {
            "hash": largest_out.get("hash") if direction == "outflow" else largest_in.get("hash"),
            "value_eth": largest_out.get("value_eth") if direction == "outflow" else largest_in.get("value_eth"),
            "to": largest_out.get("to") if direction == "outflow" else None,
            "from": largest_in.get("from") if direction == "inflow" else None,
        },
        "tx_count": len(txs)
    }


# ============ MAIN TRACKER ============

def track_whales():
    print("=" * 60)
    print("🐋 SMART WHALE TRACKER")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    eth_price = fetch_eth_price()
    btc_price = fetch_btc_price()
    print(f"  💰 ETH: ${eth_price:,.2f} | BTC: ${btc_price:,.0f}")
    print()

    registry = load_json(REGISTRY_FILE)
    btc_addresses = registry.get("bitcoin", {})
    eth_addresses = registry.get("ethereum", {})

    # Load yesterday's data for comparison
    history = load_json(WHALE_HISTORY_FILE)
    yesterday_key = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_data = history.get(yesterday_key, {})

    prev_btc = {w["address"]: w["balance_btc"] for w in yesterday_data.get("bitcoin", [])}
    prev_eth = {w["address"]: w["balance_eth"] for w in yesterday_data.get("ethereum", [])}

    whales_data = {"bitcoin": [], "ethereum": [], "changes": [], "timestamp": datetime.utcnow().isoformat()}
    changes_data = {"bitcoin": [], "ethereum": [], "timestamp": datetime.utcnow().isoformat()}

    total_calls = 0
    changed_count = 0

    # ============ BTC WHALES ============
    print("  ₿ BTC WHALES:")
    for addr, metadata in list(btc_addresses.items()):
        label = metadata.get("label", addr[:16])
        balance = get_mempool_balance(addr)
        time.sleep(REQUEST_DELAY)
        total_calls += 1

        prev_balance = prev_btc.get(addr, balance)
        change = balance - prev_balance
        change_pct = (change / prev_balance * 100) if prev_balance > 0 else 0

        whale = {
            "label": label,
            "address": addr,
            "chain": "bitcoin",
            "balance_btc": balance,
            "balance_usd": balance * btc_price,
            "prev_balance_btc": prev_balance,
            "change_btc": change,
            "change_pct": change_pct,
            "checked_at": datetime.utcnow().isoformat()
        }
        whales_data["bitcoin"].append(whale)

        # Check if changed
        if abs(change) > 1:  # More than 1 BTC change
            changed_count += 1
            direction = "inflow" if change > 0 else "outflow"
            emoji = "🟢" if change > 0 else "🔴"
            print(f"    {emoji} {label}: {balance:,.2f} BTC ({change_pct:+.1f}%) - CHANGED")

            whale["status"] = "changed"
            whale["signal"] = f"{direction}" if direction == "inflow" else f"distributed"
            whale["signal_emoji"] = emoji
            whale["change_summary"] = f"{emoji} {label}: {'+' if change > 0 else ''}{change:,.2f} BTC"

            changes_data["bitcoin"].append({
                "label": label,
                "address": addr,
                "balance": balance,
                "change": change,
                "change_pct": change_pct,
                "direction": direction
            })
        else:
            whale["status"] = "stable"
            whale["signal"] = "stable"
            whale["signal_emoji"] = "➖"
            print(f"    ➖ {label}: {balance:,.2f} BTC - stable")

    print()

    # ============ ETH WHALES ============
    print("  ⟽ ETH WHALES:")
    for addr, metadata in list(eth_addresses.items()):
        label = metadata.get("label", addr[:16])
        balance = get_alchemy_balance(addr) if ALCHEMY_API_KEY else get_blockscout_balance(addr)
        time.sleep(REQUEST_DELAY)
        total_calls += 1

        prev_balance = prev_eth.get(addr, balance)
        change = balance - prev_balance
        change_pct = (change / prev_balance * 100) if prev_balance > 0 else 0

        whale = {
            "label": label,
            "address": addr,
            "chain": "ethereum",
            "balance_eth": balance,
            "balance_usd": balance * eth_price,
            "prev_balance_eth": prev_balance,
            "change_eth": change,
            "change_pct": change_pct,
            "category": metadata.get("category", "unknown"),
            "checked_at": datetime.utcnow().isoformat()
        }
        whales_data["ethereum"].append(whale)

        # Check if changed significantly (more than 10 ETH or 1%)
        if abs(change) > 10 or abs(change_pct) > 1:
            changed_count += 1
            direction = "inflow" if change > 0 else "outflow"
            emoji = "🟢" if change > 0 else "🔴"
            print(f"    {emoji} {label}: {balance:,.2f} ETH ({change_pct:+.1f}%) - FETCHING TXS...")

            # Fetch and analyze transactions
            if ALCHEMY_API_KEY:
                txs = get_alchemy_transactions(addr, days=1)
            else:
                txs = get_blockscout_transactions(addr, days=1)
            total_calls += 1

            analysis = analyze_transactions(txs, addr, direction, change)

            whale["status"] = "changed"
            whale["signal"] = analysis["signal"]
            whale["signal_emoji"] = analysis["emoji"]
            whale["change_summary"] = f"{analysis['emoji']} {label}: {analysis['summary']}"
            whale["tx_analysis"] = analysis

            changes_data["ethereum"].append({
                "label": label,
                "address": addr,
                "balance": balance,
                "change": change,
                "change_pct": change_pct,
                "direction": direction,
                "signal": analysis["signal"],
                "summary": analysis["summary"]
            })
        else:
            whale["status"] = "stable"
            whale["signal"] = "stable"
            whale["signal_emoji"] = "➖"
            print(f"    ➖ {label}: {balance:,.2f} ETH - stable")

    # Sort by balance
    whales_data["bitcoin"].sort(key=lambda x: x.get("balance_btc", 0), reverse=True)
    whales_data["ethereum"].sort(key=lambda x: x.get("balance_eth", 0), reverse=True)

    # Save data
    save_json(WHALE_DATA_FILE, whales_data)
    save_json(WHALE_CHANGES_FILE, changes_data)

    # Update history (everlasting)
    date_key = datetime.utcnow().strftime("%Y-%m-%d")
    history[date_key] = {
        "bitcoin": whales_data["bitcoin"],
        "ethereum": whales_data["ethereum"],
        "timestamp": datetime.utcnow().isoformat()
    }
    history["last_updated"] = datetime.utcnow().isoformat()
    save_json(WHALE_HISTORY_FILE, history)

    # Summary
    print()
    print("=" * 60)
    print("📊 SUMMARY")
    print(f"  Total whales: {len(btc_addresses)} BTC + {len(eth_addresses)} ETH")
    print(f"  Changed: {changed_count} whales")
    print(f"  Total API calls: {total_calls}")
    print("=" * 60)

    if changes_data["bitcoin"] or changes_data["ethereum"]:
        print("\n🚨 WHALE ACTIVITY ALERTS:")
        for w in (changes_data["bitcoin"] + changes_data["ethereum"]):
            emoji = "🟢" if w["change"] > 0 else "🔴"
            print(f"  {emoji} {w['label']}: {'+' if w['change'] > 0 else ''}{w['change']:,.2f} | {w.get('summary', w['direction'])}")

    print("\n✅ Done!")


if __name__ == "__main__":
    track_whales()