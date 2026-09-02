#!/usr/bin/env python3
"""
Whale Alert Collector — pulls large transactions from Whale Alert free API (v1).

Free plan: 10 req/min, min $500k, 1-month history, deprecated but functional.
No API key needed for the deprecated endpoint (but rate-limited).

Outputs:
  - data/whale_alerts/whale_alerts_latest.json  (today's large transactions)
  - Auto-adds newly labeled addresses to config/whale_registry.json

Usage:
  python3 collectors/whale_alert_collector.py
  python3 collectors/whale_alert_collector.py --hours 24
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

BASE_DIR = Path(__file__).parent.parent
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"
DATA_DIR = BASE_DIR / "data" / "whale_alerts"
REGISTRY_FILE = BASE_DIR / "config" / "whale_registry.json"

# Load config
def load_config() -> dict:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})

# Whale Alert free (deprecated) API v1
# Free plan: 10 req/min, min_value $500k
WHALE_ALERT_BASE = API_ENDPOINTS.get("whale_alert", "https://api.whale-alert.io/v1")

# We'll also scrape their public feed as backup (no API key needed)
WHALE_ALERT_PUBLIC = API_ENDPOINTS.get("whale_alert_public", "https://whale-alert.io")


def api_request(url: str, timeout: int = 15) -> dict:
    """Make API request with error handling."""
    req = Request(url, headers={
        "User-Agent": "CryptoMonitor/2.0",
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"  ❌ HTTP {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def load_registry() -> dict:
    """Load whale registry."""
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {"bitcoin": {}, "ethereum": {}, "solana": {}}


def save_registry(registry: dict):
    """Save whale registry."""
    registry["_updated"] = datetime.utcnow().strftime("%Y-%m-%d")
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2))


def fetch_whale_alert_transactions(hours: int = 24, min_value: int = 1000000, api_key: str = None) -> list:
    """Fetch large transactions from Whale Alert free API.
    
    Free plan constraints:
    - Min value: $500,000 (we default to $1M for signal quality)
    - Rate limit: 10 req/min
    - Max 100 results per request
    - History: ~30 days
    """
    start_time = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
    
    all_txs = []
    cursor = None
    page = 0
    max_pages = 5  # Safety limit
    
    while page < max_pages:
        # Build URL
        url = f"{WHALE_ALERT_BASE}/transactions?start={start_time}&min_value={min_value}"
        if api_key:
            url += f"&api_key={api_key}"
        if cursor:
            url += f"&cursor={cursor}"
        
        print(f"  Fetching page {page + 1}...")
        result = api_request(url)
        
        if not result or result.get("result") != "success":
            error = result.get("message", "Unknown error") if result else "No response"
            print(f"  ⚠️  Whale Alert API: {error}")
            break
        
        txs = result.get("transactions", [])
        if not txs:
            break
            
        all_txs.extend(txs)
        cursor = result.get("cursor")
        page += 1
        
        print(f"    Got {len(txs)} transactions (total: {len(all_txs)})")
        
        # Don't hit rate limit
        if cursor and page < max_pages:
            time.sleep(7)  # 10 req/min = 1 per 6s, be safe
    
    return all_txs


def parse_transactions(raw_txs: list) -> list:
    """Parse and enrich raw Whale Alert transactions."""
    parsed = []
    
    for tx in raw_txs:
        blockchain = tx.get("blockchain", "?")
        symbol = tx.get("symbol", "?").upper()
        amount = tx.get("amount", 0)
        amount_usd = tx.get("amount_usd", 0)
        tx_type = tx.get("transaction_type", "transfer")
        timestamp = tx.get("timestamp", 0)
        tx_hash = tx.get("hash", "?")
        
        from_info = tx.get("from", {})
        to_info = tx.get("to", {})
        
        from_owner = from_info.get("owner", "unknown")
        from_type = from_info.get("owner_type", "unknown")
        to_owner = to_info.get("owner", "unknown")
        to_type = to_info.get("owner_type", "unknown")
        from_addr = from_info.get("address", "?")
        to_addr = to_info.get("address", "?")
        
        # Classify the move
        if tx_type == "mint":
            move_type = "MINT"
            description = f"{amount:,.0f} {symbol} minted at {to_owner}"
        elif tx_type == "burn":
            move_type = "BURN"
            description = f"{amount:,.0f} {symbol} burned at {from_owner}"
        elif from_type == "exchange" and to_type == "exchange":
            move_type = "EXCHANGE_TRANSFER"
            description = f"{amount:,.0f} {symbol}: {from_owner} → {to_owner}"
        elif from_type == "exchange" and to_type != "exchange":
            move_type = "WITHDRAWAL"
            description = f"{amount:,.0f} {symbol} withdrawn from {from_owner}"
        elif from_type != "exchange" and to_type == "exchange":
            move_type = "DEPOSIT"
            description = f"{amount:,.0f} {symbol} deposited to {to_owner}"
        else:
            move_type = "TRANSFER"
            from_label = from_owner if from_owner != "unknown" else f"{from_addr[:8]}..."
            to_label = to_owner if to_owner != "unknown" else f"{to_addr[:8]}..."
            description = f"{amount:,.0f} {symbol}: {from_label} → {to_label}"
        
        parsed.append({
            "blockchain": blockchain,
            "symbol": symbol,
            "amount": amount,
            "amount_usd": amount_usd,
            "type": tx_type,
            "move_type": move_type,
            "description": description,
            "from_owner": from_owner,
            "from_type": from_type,
            "from_address": from_addr,
            "to_owner": to_owner,
            "to_type": to_type,
            "to_address": to_addr,
            "hash": tx_hash,
            "timestamp": timestamp,
            "time_str": datetime.fromtimestamp(timestamp).strftime("%H:%M UTC") if timestamp else "?",
        })
    
    # Sort by USD value descending
    parsed.sort(key=lambda x: x.get("amount_usd", 0), reverse=True)
    return parsed


def discover_new_addresses(transactions: list, registry: dict) -> list:
    """Find labeled addresses from Whale Alert that aren't in our registry."""
    chain_map = {
        "bitcoin": "bitcoin",
        "ethereum": "ethereum",
        "solana": "solana",
    }
    
    new_addresses = []
    seen = set()
    
    for tx in transactions:
        blockchain = tx.get("blockchain")
        chain_key = chain_map.get(blockchain)
        if not chain_key:
            continue
        
        for side in ("from", "to"):
            addr = tx.get(f"{side}_address", "")
            owner = tx.get(f"{side}_owner", "unknown")
            owner_type = tx.get(f"{side}_type", "unknown")
            
            if owner == "unknown" or addr in ("?", "Multiple Addresses"):
                continue
            
            addr_lower = addr.lower()
            
            # Check if already in registry
            if addr_lower in registry.get(chain_key, {}):
                continue
            # Also check original case
            if addr in registry.get(chain_key, {}):
                continue
            
            key = f"{chain_key}:{addr_lower}"
            if key in seen:
                continue
            seen.add(key)
            
            new_addresses.append({
                "chain": chain_key,
                "address": addr,
                "owner": owner,
                "owner_type": owner_type,
                "usd_value": tx.get("amount_usd", 0),
            })
    
    return new_addresses


def auto_add_to_registry(new_addresses: list, registry: dict) -> int:
    """Auto-add newly discovered labeled addresses to registry."""
    added = 0
    for entry in new_addresses:
        chain = entry["chain"]
        addr = entry["address"]
        
        # Use lowercase for ETH addresses
        if chain == "ethereum" and addr.startswith("0x"):
            addr = addr.lower()
        
        if addr in registry.get(chain, {}):
            continue
        
        registry.setdefault(chain, {})[addr] = {
            "label": entry["owner"],
            "category": entry["owner_type"],
            "source": "whale_alert_auto",
            "discovered": datetime.utcnow().strftime("%Y-%m-%d"),
            "verified": False,
        }
        added += 1
        print(f"  + [{chain[:3].upper()}] {entry['owner']} ({addr[:12]}...)")
    
    return added


def main():
    print("=" * 60)
    print("🐋 WHALE ALERT COLLECTOR")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)
    
    # Parse args
    hours = 24
    if "--hours" in sys.argv:
        idx = sys.argv.index("--hours")
        if idx + 1 < len(sys.argv):
            hours = int(sys.argv[idx + 1])
    
    # Check for API key in env
    api_key = os.environ.get("WHALE_ALERT_API_KEY", "")
    
    if not api_key:
        print("  ⚠️  No WHALE_ALERT_API_KEY in environment")
        print("  Get free key at: https://developer.whale-alert.io")
        print("  Set env var: WHALE_ALERT_API_KEY=your_key_here")
        print("  Skipping external whale alerts (balance-diff tracking still works)")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "transactions": [],
            "top_moves": [],
            "status": "no_api_key",
        }
        with open(DATA_DIR / "whale_alerts_latest.json", "w") as f:
            json.dump(result, f, indent=2)
        return

    print(f"\n📡 Fetching large transactions (last {hours}h, >$1M)...")
    raw_txs = fetch_whale_alert_transactions(hours=hours, min_value=1000000, api_key=api_key)
    
    if not raw_txs:
        print("  No transactions found (API may require key)")
        print("  Falling back to balance-diff tracking only")
        # Save empty result
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "hours_checked": hours,
            "transactions": [],
            "top_moves": [],
            "new_addresses": [],
            "source": "whale_alert_v1_free",
            "status": "no_data",
        }
        with open(DATA_DIR / "whale_alerts_latest.json", "w") as f:
            json.dump(result, f, indent=2)
        print("✅ Saved (empty)")
        return
    
    print(f"\n📊 Parsing {len(raw_txs)} transactions...")
    transactions = parse_transactions(raw_txs)
    
    # Filter to top 10 most significant moves
    # Prioritize: mints/burns > exchange deposits/withdrawals > transfers
    priority = {"MINT": 5, "BURN": 5, "DEPOSIT": 3, "WITHDRAWAL": 3,
                "EXCHANGE_TRANSFER": 1, "TRANSFER": 2}
    
    scored = []
    for tx in transactions:
        score = tx["amount_usd"] * priority.get(tx["move_type"], 1)
        scored.append((score, tx))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    top_moves = [tx for _, tx in scored[:10]]
    
    print(f"\n🔝 Top 10 Moves:")
    for i, tx in enumerate(top_moves, 1):
        print(f"  {i}. ${tx['amount_usd']:,.0f} — {tx['description']}")
    
    # Discover new addresses
    print(f"\n🔍 Checking for new labeled addresses...")
    registry = load_registry()
    new_addresses = discover_new_addresses(transactions, registry)
    
    if new_addresses:
        print(f"  Found {len(new_addresses)} new addresses!")
        added = auto_add_to_registry(new_addresses, registry)
        if added > 0:
            save_registry(registry)
            print(f"  ✅ Added {added} to whale registry")
    else:
        print("  No new addresses found")
    
    # Save results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "hours_checked": hours,
        "transaction_count": len(transactions),
        "top_moves": top_moves,
        "new_addresses": [
            {"chain": a["chain"], "owner": a["owner"], "address": a["address"][:16] + "..."}
            for a in new_addresses
        ],
        "source": "whale_alert_v1_free",
        "status": "ok",
    }
    
    # Write latest
    with open(DATA_DIR / "whale_alerts_latest.json", "w") as f:
        json.dump(result, f, indent=2)
    
    # Update history
    history_file = DATA_DIR / "whale_alerts_history.json"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    if history_file.exists():
        history = json.loads(history_file.read_text())
    else:
        history = {}
    
    # Use date as key (overwrites if exists)
    history[today] = result
    
    history["last_updated"] = datetime.utcnow().isoformat()
    
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)
    
    print(f"\n💾 Saved to data/whale_alerts/")
    print(f"✅ Done — {len(transactions)} transactions, top {len(top_moves)} moves")


if __name__ == "__main__":
    main()
