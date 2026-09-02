#!/usr/bin/env python3
"""
Exchange Wallet Address Verifier — checks all configured wallet addresses
for validity, balance, and staleness.

Usage:
  python3 tools/verify_wallets.py              # Full check
  python3 tools/verify_wallets.py --quick      # Skip balance lookups, just validate format
  python3 tools/verify_wallets.py --json       # Output JSON report

Purpose:
  Run periodically (monthly or after suspecting stale data) to ensure
  exchange_wallets.json addresses are still valid and holding meaningful
  balances. Flags:
    - Invalid address formats
    - Zero/near-zero balances (likely wrong wallet)
    - API failures (endpoint issues)
    - Missing chains (exchange with no BTC or no ETH addresses)

Sources for finding replacement addresses:
  - Etherscan top accounts: https://etherscan.io/accounts
  - Etherscan label cloud: https://etherscan.io/labelcloud
  - BitInfoCharts wallets: https://bitinfocharts.com/bitcoin/wallet/<EXCHANGE>
  - Exchange PoR pages (Binance, OKX, Bybit, Kraken publish wallet lists)
  - Arkham Intelligence: https://platform.arkhamintelligence.com
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
CONFIG_FILE = BASE_DIR / "config" / "exchange_wallets.json"
REPORT_FILE = BASE_DIR / "data" / "wallet_verification_report.json"

# Load config
def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return {}

SETTINGS = load_settings()
API_ENDPOINTS = SETTINGS.get("api_endpoints", {})
THRESHOLDS = SETTINGS.get("thresholds", {}).get("verify_wallets", {})

MEMPOOL_API = API_ENDPOINTS.get("mempool", "https://mempool.space/api")
BLOCKSCOUT_ETH_API = API_ENDPOINTS.get("blockscout", "https://eth.blockscout.com/api/v2")

REQUEST_DELAY = 0.4  # Be polite

# Minimum balance thresholds — below this, flag as "suspicious"
MIN_BTC_BALANCE = THRESHOLDS.get("min_btc_balance", 0.01)
MIN_ETH_BALANCE = THRESHOLDS.get("min_eth_balance", 0.1)

# Address format patterns
BTC_PATTERNS = [
    re.compile(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$'),           # Legacy / P2SH
    re.compile(r'^bc1q[a-z0-9]{38,58}$'),                         # Bech32
    re.compile(r'^bc1p[a-z0-9]{58}$'),                            # Bech32m (Taproot)
]

ETH_PATTERN = re.compile(r'^0x[a-fA-F0-9]{40}$')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch(url: str, timeout: int = 20) -> dict | None:
    req = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "CryptoMonitor/2.0"
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        return {"_error": f"HTTP {e.code}"}
    except (URLError, Exception) as e:
        return {"_error": str(e)}
    finally:
        time.sleep(REQUEST_DELAY)


def validate_btc_format(address: str) -> bool:
    return any(p.match(address) for p in BTC_PATTERNS)


def validate_eth_format(address: str) -> bool:
    return bool(ETH_PATTERN.match(address))


def get_btc_balance(address: str) -> dict:
    """Check BTC address — returns balance or error."""
    if not validate_btc_format(address):
        return {"status": "INVALID_FORMAT", "balance": None}

    data = _fetch(f"{MEMPOOL_API}/address/{address}")
    if not data:
        return {"status": "API_ERROR", "balance": None, "error": "no response"}
    if "_error" in data:
        return {"status": "API_ERROR", "balance": None, "error": data["_error"]}

    chain = data.get("chain_stats", {})
    mempool = data.get("mempool_stats", {})
    funded = chain.get("funded_txo_sum", 0) + mempool.get("funded_txo_sum", 0)
    spent = chain.get("spent_txo_sum", 0) + mempool.get("spent_txo_sum", 0)
    balance = (funded - spent) / 1e8

    tx_count = chain.get("tx_count", 0)

    status = "OK"
    if balance < MIN_BTC_BALANCE:
        status = "LOW_BALANCE"
    if balance == 0 and tx_count == 0:
        status = "EMPTY_NEVER_USED"

    return {
        "status": status,
        "balance": balance,
        "tx_count": tx_count,
        "unit": "BTC",
    }


def get_eth_balance(address: str) -> dict:
    """Check ETH address — returns balance or error."""
    if not validate_eth_format(address):
        return {"status": "INVALID_FORMAT", "balance": None}

    data = _fetch(f"{BLOCKSCOUT_ETH_API}/addresses/{address}")
    if not data:
        return {"status": "API_ERROR", "balance": None, "error": "no response"}
    if "_error" in data:
        return {"status": "API_ERROR", "balance": None, "error": data["_error"]}

    coin_balance = data.get("coin_balance")
    if coin_balance is None:
        return {"status": "API_ERROR", "balance": None, "error": "no coin_balance field"}

    balance = int(coin_balance) / 1e18
    is_contract = data.get("is_contract", False)

    status = "OK"
    if balance < MIN_ETH_BALANCE:
        status = "LOW_BALANCE"
    if balance == 0:
        status = "EMPTY"

    return {
        "status": status,
        "balance": balance,
        "is_contract": is_contract,
        "unit": "ETH",
    }


# ---------------------------------------------------------------------------
# Main verification
# ---------------------------------------------------------------------------

def verify_all(quick: bool = False) -> dict:
    print("=" * 60)
    print("🔍 EXCHANGE WALLET VERIFIER")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    exchanges = config.get("exchanges", {})
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "config_updated": config.get("_updated", "?"),
        "exchanges": {},
        "summary": {"total": 0, "ok": 0, "warnings": 0, "errors": 0},
    }

    for name, chains in exchanges.items():
        print(f"\n🏛  {name}")
        ex_report = {"bitcoin": [], "ethereum": []}

        # --- BTC ---
        btc_wallets = chains.get("bitcoin", [])
        if not btc_wallets:
            print(f"  ⚠️  No BTC addresses configured!")
            report["summary"]["warnings"] += 1

        for w in btc_wallets:
            addr = w["address"]
            label = w.get("label", "?")
            report["summary"]["total"] += 1

            if quick:
                valid = validate_btc_format(addr)
                result = {"status": "FORMAT_OK" if valid else "INVALID_FORMAT"}
                icon = "✅" if valid else "❌"
                print(f"  {icon} ₿ {label}: format {'valid' if valid else 'INVALID'}")
            else:
                result = get_btc_balance(addr)
                if result["status"] == "OK":
                    report["summary"]["ok"] += 1
                    print(f"  ✅ ₿ {label}: {result['balance']:,.4f} BTC")
                elif result["status"] == "LOW_BALANCE":
                    report["summary"]["warnings"] += 1
                    print(f"  ⚠️  ₿ {label}: {result['balance']:,.4f} BTC — LOW BALANCE")
                else:
                    report["summary"]["errors"] += 1
                    print(f"  ❌ ₿ {label}: {result['status']} — {result.get('error', '')}")

            ex_report["bitcoin"].append({
                "address": addr,
                "label": label,
                "type": w.get("type", "?"),
                **result,
            })

        # --- ETH ---
        eth_wallets = chains.get("ethereum", [])
        if not eth_wallets:
            print(f"  ⚠️  No ETH addresses configured!")
            report["summary"]["warnings"] += 1

        for w in eth_wallets:
            addr = w["address"]
            label = w.get("label", "?")
            report["summary"]["total"] += 1

            if quick:
                valid = validate_eth_format(addr)
                result = {"status": "FORMAT_OK" if valid else "INVALID_FORMAT"}
                icon = "✅" if valid else "❌"
                print(f"  {icon} ⟠ {label}: format {'valid' if valid else 'INVALID'}")
            else:
                result = get_eth_balance(addr)
                if result["status"] == "OK":
                    report["summary"]["ok"] += 1
                    print(f"  ✅ ⟠ {label}: {result['balance']:,.2f} ETH")
                elif result["status"] == "LOW_BALANCE":
                    report["summary"]["warnings"] += 1
                    print(f"  ⚠️  ⟠ {label}: {result['balance']:,.2f} ETH — LOW BALANCE")
                else:
                    report["summary"]["errors"] += 1
                    print(f"  ❌ ⟠ {label}: {result['status']} — {result.get('error', '')}")

            ex_report["ethereum"].append({
                "address": addr,
                "label": label,
                "type": w.get("type", "?"),
                **result,
            })

        report["exchanges"][name] = ex_report

    # --- Summary ---
    s = report["summary"]
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print(f"  Total addresses: {s['total']}")
    print(f"  ✅ OK: {s['ok']}")
    print(f"  ⚠️  Warnings: {s['warnings']}")
    print(f"  ❌ Errors: {s['errors']}")

    if s["warnings"] > 0 or s["errors"] > 0:
        print("\n💡 Addresses with issues may need replacement.")
        print("   Sources:")
        print("   - Etherscan: https://etherscan.io/accounts")
        print("   - BitInfoCharts: https://bitinfocharts.com/bitcoin/wallet/<EXCHANGE>")
        print("   - Exchange PoR pages")

    # Save report
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n💾 Report saved to {REPORT_FILE.relative_to(BASE_DIR)}")

    return report


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    output_json = "--json" in sys.argv

    result = verify_all(quick=quick)

    if output_json:
        print("\n" + json.dumps(result, indent=2))
