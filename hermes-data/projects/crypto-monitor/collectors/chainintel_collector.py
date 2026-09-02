#!/usr/bin/env python3
"""
ChainIntel.io Collector — scrapes free whale tracker for BTC top-50 addresses.

Source: https://chainintel.io/whale-tracker
- Free, no registration, no API key
- Top 50 BTC addresses by balance
- Labels (exchange, whale, hack, government, etc.)
- 7d and 30d movement data
- Active/dormant/watching status

Outputs:
  - data/chainintel/chainintel_latest.json (active whales with movements)
  - Auto-adds new labeled BTC addresses to whale_registry.json

Usage:
  python3 collectors/chainintel_collector.py
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config" / "settings.json"
DATA_DIR = BASE_DIR / "data" / "chainintel"
REGISTRY_FILE = BASE_DIR / "config" / "whale_registry.json"

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})

# Using our self-hosted scraper
SCRAPER_URL = API_ENDPOINTS.get("ascend_web_read", "http://host.docker.internal:7021/api/v1/web/read")
WHALE_TRACKER_URL = API_ENDPOINTS.get("chainintel", "https://chainintel.io/whale-tracker")


def scrape_whale_tracker() -> list:
    """Scrape ChainIntel whale tracker page."""
    url = f"{SCRAPER_URL}?url={WHALE_TRACKER_URL}"
    req = Request(url, headers={"Accept": "application/json"})
    
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            content = data.get("content", {}).get("content", "")
    except Exception as e:
        print(f"  ❌ Scrape failed: {e}")
        return []
    
    if not content:
        print("  ❌ Empty content")
        return []
    
    # Parse the markdown table
    whales = []
    lines = content.split("\n")
    
    for line in lines:
        if not line.startswith("#") or "|" not in line:
            continue
        
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 7:
            continue
        
        try:
            rank_str = parts[0].replace("#", "").strip()
            rank = int(rank_str)
        except ValueError:
            continue
        
        address = parts[1].strip()
        entity_raw = parts[2].strip()
        balance_raw = parts[3].strip()
        status = parts[5].strip()
        movement = parts[6].strip()
        
        # Parse entity name (remove emoji categories)
        entity = re.sub(r'[🏦💀🐋🏛💵❓🔒]\s*\w+$', '', entity_raw).strip()
        if entity.endswith("-"):
            entity = entity[:-1].strip()
        
        # Parse category from emoji
        category = "unknown"
        if "🏦" in entity_raw:
            category = "exchange"
        elif "💀" in entity_raw:
            category = "hack"
        elif "🐋" in entity_raw:
            category = "whale"
        elif "🏛" in entity_raw:
            category = "government"
        elif "💵" in entity_raw:
            category = "stablecoin"
        elif "🔒" in entity_raw:
            category = "locked"
        
        # Parse balance
        btc_match = re.search(r'([\d,]+(?:\.\d+)?)\s*BTC', balance_raw)
        usd_match = re.search(r'\$([\d,]+(?:\.\d+)?)', balance_raw)
        
        balance_btc = float(btc_match.group(1).replace(",", "")) if btc_match else 0
        balance_usd = float(usd_match.group(1).replace(",", "")) if usd_match else 0
        
        # Parse movement (7d and 30d)
        move_7d = 0
        move_30d = 0
        has_movement = movement != "No recent movement"
        
        m7d = re.search(r'7d:\s*([+-]?[\d,.]+)\s*BTC', movement)
        m30d = re.search(r'30d:\s*([+-]?[\d,.]+)\s*BTC', movement)
        
        if m7d:
            move_7d = float(m7d.group(1).replace(",", ""))
        if m30d:
            move_30d = float(m30d.group(1).replace(",", ""))
        
        whales.append({
            "rank": rank,
            "address": address,
            "entity": entity,
            "category": category,
            "balance_btc": balance_btc,
            "balance_usd": balance_usd,
            "status": status,
            "has_movement": has_movement,
            "move_7d_btc": move_7d,
            "move_30d_btc": move_30d,
            "movement_raw": movement,
        })
    
    return whales


def find_active_moves(whales: list) -> list:
    """Filter to whales with actual movements, sorted by 7d abs change."""
    active = [w for w in whales if w["has_movement"]]
    # Sort by absolute 7d movement (or 30d if no 7d)
    active.sort(key=lambda w: abs(w["move_7d_btc"]) or abs(w["move_30d_btc"]), reverse=True)
    return active


def auto_add_to_registry(whales: list) -> int:
    """Add newly discovered labeled addresses to whale registry."""
    if not REGISTRY_FILE.exists():
        return 0
    
    registry = json.loads(REGISTRY_FILE.read_text())
    btc_reg = registry.setdefault("bitcoin", {})
    
    added = 0
    for w in whales:
        addr = w["address"]
        entity = w["entity"]
        
        if not entity or entity == "Unknown":
            continue
        if addr in btc_reg:
            continue
        
        btc_reg[addr] = {
            "label": entity,
            "category": w["category"],
            "source": "chainintel_auto",
            "rank": w["rank"],
            "discovered": datetime.utcnow().strftime("%Y-%m-%d"),
            "verified": False,
        }
        added += 1
        print(f"  + [BTC #{w['rank']}] {entity} ({addr[:12]}...)")
    
    if added:
        registry["_updated"] = datetime.utcnow().strftime("%Y-%m-%d")
        REGISTRY_FILE.write_text(json.dumps(registry, indent=2))
    
    return added


def main():
    print("=" * 60)
    print("🔗 CHAININTEL COLLECTOR")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)
    
    print("\n📡 Scraping ChainIntel whale tracker...")
    whales = scrape_whale_tracker()
    
    if not whales:
        print("  ❌ No data retrieved")
        return
    
    print(f"  Found {len(whales)} addresses")
    
    # Active moves
    active = find_active_moves(whales)
    print(f"\n📊 Active whales with movement: {len(active)}")
    
    for w in active[:10]:
        move_parts = []
        if w["move_7d_btc"]:
            move_parts.append(f"7d: {w['move_7d_btc']:+,.0f} BTC")
        if w["move_30d_btc"]:
            move_parts.append(f"30d: {w['move_30d_btc']:+,.0f} BTC")
        move_str = " | ".join(move_parts) if move_parts else "?"
        print(f"  #{w['rank']:>2} {w['entity'][:20]:<20} {move_str}")
    
    # Auto-discover new addresses
    print(f"\n🔍 Checking for new addresses...")
    added = auto_add_to_registry(whales)
    if added:
        print(f"  ✅ Added {added} new addresses to registry")
    else:
        print("  All addresses already in registry")
    
    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "source": "chainintel.io/whale-tracker",
        "total_addresses": len(whales),
        "active_count": len(active),
        "top_moves": [
            {
                "rank": w["rank"],
                "entity": w["entity"],
                "category": w["category"],
                "address": w["address"],
                "balance_btc": w["balance_btc"],
                "move_7d_btc": w["move_7d_btc"],
                "move_30d_btc": w["move_30d_btc"],
                "status": w["status"],
            }
            for w in active[:15]
        ],
        "all_whales": whales,
        "new_addresses_added": added,
    }
    
    # Write latest
    with open(DATA_DIR / "chainintel_latest.json", "w") as f:
        json.dump(result, f, indent=2)
    
    # Update history
    history_file = DATA_DIR / "chainintel_history.json"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    if history_file.exists():
        history = json.loads(history_file.read_text())
    else:
        history = {}
    
    # Remove timestamp from result, use date as key
    result_for_history = {k: v for k, v in result.items() if k != "timestamp"}
    result_for_history["date"] = today
    
    # Add/update with date key (overwrites if exists)
    history[today] = result_for_history
    
    history["last_updated"] = datetime.utcnow().isoformat()
    
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)
    
    print(f"\n💾 Saved to data/chainintel/")
    print(f"✅ Done — {len(active)} active moves tracked")


if __name__ == "__main__":
    main()
