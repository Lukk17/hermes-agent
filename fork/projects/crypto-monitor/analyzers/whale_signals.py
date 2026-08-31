#!/usr/bin/env python3
"""
Whale Signals — Movement pattern analysis and signal generation.

Layers intelligence on top of whale_tracker.py data:
  - Balance change detection (accumulation vs distribution)
  - Exchange flow analysis (net flows = selling/buying pressure)
  - Activity scoring (who's moving, how much, how often)
  - Transaction pattern classification (DCA, dump, shuffle, dormant)
  - Smart money scoring (rank whales by signal quality)
  - Price correlation (whale moves vs price action)

Usage:
  python3 analyzers/whale_signals.py              # Full analysis
  python3 analyzers/whale_signals.py --quick      # Latest snapshot only
  python3 analyzers/whale_signals.py --flows      # Exchange flow focus
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config" / "settings.json"
DATA_DIR = BASE_DIR / "data" / "whale_signals"
WHALE_DIR = BASE_DIR / "data" / "whales"
PRICES_DIR = BASE_DIR / "data" / "prices"
CYCLE_DIR = BASE_DIR / "data" / "cycle"

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
THRESHOLDS = CONFIG.get("thresholds", {}).get("whale_signals", {})

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Minimum movement to count as significant (in native units)
MIN_BTC_MOVE = THRESHOLDS.get("min_btc_move", 1.0)
MIN_ETH_MOVE = THRESHOLDS.get("min_eth_move", 10.0)
MIN_SOL_MOVE = THRESHOLDS.get("min_sol_move", 100.0)

# Large movement thresholds
LARGE_BTC = 100.0        # 100 BTC
LARGE_ETH = 1000.0       # 1000 ETH
LARGE_SOL = 10000.0      # 10k SOL

# Balance change thresholds (percentage)
ACCUMULATION_PCT = 2.0    # >2% increase = accumulating
DISTRIBUTION_PCT = -2.0   # >2% decrease = distributing

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_whale_snapshots() -> list:
    """Load all whale tracker snapshots, newest first."""
    if not WHALE_DIR.exists():
        return []

    files = sorted(WHALE_DIR.glob("whale_status_2*.json"), reverse=True)
    snapshots = []

    for f in files:
        try:
            with open(f) as fh:
                data = json.load(fh)
                data["_file"] = f.name
                snapshots.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    return snapshots


def load_latest_whale_data() -> Optional[dict]:
    """Load latest whale tracker snapshot."""
    latest = WHALE_DIR / "whale_status_latest.json"
    if not latest.exists():
        print("⚠️  No whale data. Run whale_tracker.py first.")
        return None

    with open(latest) as f:
        return json.load(f)


def load_price_data() -> Optional[dict]:
    """Load latest price data."""
    latest = PRICES_DIR / "prices_latest.json"
    if not latest.exists():
        return None
    with open(latest) as f:
        data = json.load(f)
    return data.get("data", {})


# ---------------------------------------------------------------------------
# Balance change detection
# ---------------------------------------------------------------------------

def compare_snapshots(current: dict, previous: dict) -> dict:
    """Compare two whale snapshots to detect balance changes."""
    changes = {
        "bitcoin": [],
        "ethereum": [],
        "solana": [],
        "summary": {
            "accumulators": 0,
            "distributors": 0,
            "unchanged": 0,
            "new_wallets": 0,
        },
    }

    for chain, balance_key, unit in [
        ("bitcoin", "balance_btc", "BTC"),
        ("ethereum", "balance_eth", "ETH"),
        ("solana", "balance_sol", "SOL"),
    ]:
        current_wallets = {w["address"]: w for w in current.get(chain, []) if w.get("address")}
        previous_wallets = {w["address"]: w for w in previous.get(chain, []) if w.get("address")}

        for addr, curr in current_wallets.items():
            curr_bal = curr.get(balance_key)
            if curr_bal is None:
                continue

            prev = previous_wallets.get(addr)
            if prev is None:
                changes["summary"]["new_wallets"] += 1
                continue

            prev_bal = prev.get(balance_key)
            if prev_bal is None or prev_bal == 0:
                continue

            abs_change = curr_bal - prev_bal
            pct_change = (abs_change / prev_bal) * 100

            min_move = {"BTC": MIN_BTC_MOVE, "ETH": MIN_ETH_MOVE, "SOL": MIN_SOL_MOVE}[unit]

            if abs(abs_change) < min_move:
                changes["summary"]["unchanged"] += 1
                continue

            if pct_change > ACCUMULATION_PCT:
                pattern = "accumulating"
                emoji = "🟢"
                changes["summary"]["accumulators"] += 1
            elif pct_change < DISTRIBUTION_PCT:
                pattern = "distributing"
                emoji = "🔴"
                changes["summary"]["distributors"] += 1
            else:
                pattern = "minor_change"
                emoji = "⚪"
                changes["summary"]["unchanged"] += 1
                continue  # skip minor

            # Include total portfolio value change (ETH + tokens) if available
            curr_total = curr.get("total_usd", 0)
            prev_total = prev.get("total_usd", 0)

            changes[chain].append({
                "label": curr.get("label", "Unknown"),
                "address": addr,
                "previous_balance": round(prev_bal, 4),
                "current_balance": round(curr_bal, 4),
                "abs_change": round(abs_change, 4),
                "pct_change": round(pct_change, 2),
                "pattern": pattern,
                "emoji": emoji,
                "unit": unit,
                "total_usd": curr_total,
                "total_usd_change": curr_total - prev_total if curr_total and prev_total else None,
            })

        # Sort by absolute change magnitude
        changes[chain].sort(key=lambda x: abs(x["abs_change"]), reverse=True)

    return changes


# ---------------------------------------------------------------------------
# Exchange flow analysis
# ---------------------------------------------------------------------------

def analyze_exchange_flows(data: dict) -> dict:
    """Deep analysis of exchange flows from whale data."""
    flows = data.get("exchange_flows", {})
    prices = load_price_data()

    btc_price = prices.get("bitcoin", {}).get("usd", 0) if prices else 0
    eth_price = prices.get("ethereum", {}).get("usd", 0) if prices else 0

    analysis = {
        "bitcoin": _analyze_chain_flows(flows.get("bitcoin", {}), btc_price, "BTC"),
        "ethereum": _analyze_chain_flows(flows.get("ethereum", {}), eth_price, "ETH"),
        "overall_signal": "neutral",
        "interpretation": "",
    }

    # Overall signal from combined flows
    btc_sig = analysis["bitcoin"]["signal"]
    eth_sig = analysis["ethereum"]["signal"]

    bearish_count = sum(1 for s in [btc_sig, eth_sig] if s == "bearish")
    bullish_count = sum(1 for s in [btc_sig, eth_sig] if s == "bullish")

    if bearish_count > bullish_count:
        analysis["overall_signal"] = "bearish"
        analysis["interpretation"] = "Net exchange inflows — whales moving to exchanges (potential sell pressure)"
    elif bullish_count > bearish_count:
        analysis["overall_signal"] = "bullish"
        analysis["interpretation"] = "Net exchange outflows — whales withdrawing to cold storage (accumulation)"
    else:
        analysis["overall_signal"] = "neutral"
        analysis["interpretation"] = "Mixed exchange flows — no clear directional bias"

    return analysis


def _analyze_chain_flows(chain_flows: dict, price: float, unit: str) -> dict:
    """Analyze flows for a single chain."""
    inflows = chain_flows.get("inflows", [])
    outflows = chain_flows.get("outflows", [])

    net_key = f"net_{unit.lower()}"
    net_amount = chain_flows.get(net_key, 0)
    net_usd = net_amount * price if price else 0

    # Aggregate by exchange
    exchange_inflows = defaultdict(float)
    exchange_outflows = defaultdict(float)

    for f in inflows:
        exchange_inflows[f.get("exchange", "Unknown")] += f.get("amount", 0)
    for f in outflows:
        exchange_outflows[f.get("exchange", "Unknown")] += f.get("amount", 0)

    # Signal
    if net_amount > 0:
        signal = "bearish"
        direction = "to_exchange"
    elif net_amount < 0:
        signal = "bullish"
        direction = "from_exchange"
    else:
        signal = "neutral"
        direction = "balanced"

    return {
        "inflow_count": len(inflows),
        "outflow_count": len(outflows),
        "net_amount": round(net_amount, 4),
        "net_usd": round(net_usd, 2),
        "unit": unit,
        "signal": signal,
        "direction": direction,
        "by_exchange_in": dict(exchange_inflows),
        "by_exchange_out": dict(exchange_outflows),
    }


# ---------------------------------------------------------------------------
# Transaction pattern classification
# ---------------------------------------------------------------------------

def classify_tx_patterns(data: dict) -> dict:
    """Classify transaction patterns for each tracked wallet."""
    patterns = {
        "bitcoin": [],
        "ethereum": [],
    }

    for chain, balance_key, unit, large_threshold in [
        ("bitcoin", "balance_btc", "BTC", LARGE_BTC),
        ("ethereum", "balance_eth", "ETH", LARGE_ETH),
    ]:
        for wallet in data.get(chain, []):
            label = wallet.get("label", "Unknown")
            large_txs = wallet.get("recent_large_txs", [])
            exchange_flows = wallet.get("exchange_flows", [])
            balance = wallet.get(balance_key)

            if not large_txs and not exchange_flows:
                pattern = "dormant"
                description = "No significant recent activity"
                emoji = "😴"
            elif len(large_txs) >= 3:
                # Multiple large transactions
                directions = [tx["direction"] for tx in large_txs]
                out_count = directions.count("OUT")
                in_count = directions.count("IN")

                if out_count > in_count * 2:
                    pattern = "heavy_distribution"
                    description = f"Aggressive selling — {out_count} large outflows"
                    emoji = "🔴"
                elif in_count > out_count * 2:
                    pattern = "heavy_accumulation"
                    description = f"Aggressive buying — {in_count} large inflows"
                    emoji = "🟢"
                else:
                    pattern = "active_trading"
                    description = f"Active both directions — {in_count} in, {out_count} out"
                    emoji = "🔄"
            elif len(large_txs) == 1:
                tx = large_txs[0]
                if tx["direction"] == "OUT":
                    pattern = "single_distribution"
                    description = "One large outflow"
                    emoji = "🟡"
                else:
                    pattern = "single_accumulation"
                    description = "One large inflow"
                    emoji = "🟢"
            elif exchange_flows:
                deposits = sum(1 for f in exchange_flows if f.get("flow_type") == "deposit" or f.get("direction") == "OUT")
                withdrawals = len(exchange_flows) - deposits
                if deposits > withdrawals:
                    pattern = "exchange_deposit"
                    description = f"Moving to exchanges ({deposits} deposits)"
                    emoji = "🔴"
                else:
                    pattern = "exchange_withdrawal"
                    description = f"Withdrawing from exchanges ({withdrawals} withdrawals)"
                    emoji = "🟢"
            else:
                pattern = "low_activity"
                description = "Minor transactions only"
                emoji = "⚪"

            # Calculate activity score (0-100)
            activity_score = min(100, (
                len(large_txs) * 20 +
                len(exchange_flows) * 15 +
                (10 if balance and balance > 0 else 0)
            ))

            patterns[chain].append({
                "label": label,
                "address": wallet.get("address", ""),
                "balance": balance,
                "unit": unit,
                "pattern": pattern,
                "description": description,
                "emoji": emoji,
                "large_tx_count": len(large_txs),
                "exchange_flow_count": len(exchange_flows),
                "activity_score": activity_score,
            })

        # Sort by activity score
        patterns[chain].sort(key=lambda x: x["activity_score"], reverse=True)

    return patterns


# ---------------------------------------------------------------------------
# Smart money scoring
# ---------------------------------------------------------------------------

def compute_smart_money_scores(data: dict, changes: Optional[dict] = None) -> dict:
    """Score each wallet as 'smart money' based on behavior signals.

    Factors:
      - Balance size (bigger = more influential)
      - Activity level (active > dormant)
      - Exchange flow direction (withdrawals = bullish conviction)
      - Accumulation during fear (contrarian = smart)
    """
    scores = {"bitcoin": [], "ethereum": []}

    # Load cycle data for fear/greed context
    cycle_data = _load_cycle_context()
    market_phase = cycle_data.get("phase", "unknown") if cycle_data else "unknown"
    fear_greed = cycle_data.get("fear_greed", 50) if cycle_data else 50

    for chain, balance_key, unit in [
        ("bitcoin", "balance_btc", "BTC"),
        ("ethereum", "balance_eth", "ETH"),
    ]:
        for wallet in data.get(chain, []):
            label = wallet.get("label", "Unknown")
            balance = wallet.get(balance_key, 0) or 0
            large_txs = wallet.get("recent_large_txs", [])
            exchange_flows = wallet.get("exchange_flows", [])

            score = 50  # baseline

            # Balance weight (log scale, bigger wallets more weight)
            if balance > 0:
                import math
                if unit == "BTC":
                    score += min(15, math.log10(max(balance, 1)) * 5)
                else:
                    score += min(15, math.log10(max(balance, 1)) * 3)

            # Activity bonus
            if large_txs:
                score += min(10, len(large_txs) * 3)

            # Exchange flow signals
            for flow in exchange_flows:
                flow_type = flow.get("flow_type") or ("deposit" if flow.get("direction") == "OUT" else "withdrawal")
                if flow_type == "withdrawal":
                    score += 5  # withdrawing = conviction
                elif flow_type == "deposit":
                    score -= 5  # depositing = potential sell

            # Contrarian bonus: accumulating during extreme fear
            if changes:
                chain_changes = changes.get(chain, [])
                wallet_change = next(
                    (c for c in chain_changes if c.get("address") == wallet.get("address")),
                    None
                )
                if wallet_change:
                    if wallet_change["pattern"] == "accumulating" and fear_greed < 25:
                        score += 15  # buying during extreme fear = very smart
                    elif wallet_change["pattern"] == "distributing" and fear_greed > 75:
                        score += 10  # selling during extreme greed = smart
                    elif wallet_change["pattern"] == "accumulating" and fear_greed > 75:
                        score -= 10  # buying during euphoria = risky
                    elif wallet_change["pattern"] == "distributing" and fear_greed < 25:
                        score -= 10  # selling during fear = panic

            score = max(0, min(100, score))

            # Label
            if score >= 80:
                tier = "🏆 Elite"
            elif score >= 65:
                tier = "🥇 Smart"
            elif score >= 50:
                tier = "📊 Average"
            elif score >= 35:
                tier = "⚠️ Questionable"
            else:
                tier = "🔴 Weak"

            scores[chain].append({
                "label": label,
                "address": wallet.get("address", ""),
                "score": round(score, 1),
                "tier": tier,
                "balance": balance,
                "unit": unit,
            })

        scores[chain].sort(key=lambda x: x["score"], reverse=True)

    return scores


def _load_cycle_context() -> Optional[dict]:
    """Load latest cycle analysis for context."""
    latest = CYCLE_DIR / "cycle_latest.json"
    if not latest.exists():
        return None

    try:
        with open(latest) as f:
            data = json.load(f)

        cycle = data.get("cycle_score", {})
        fg = data.get("indicators", {}).get("fear_greed", {})

        return {
            "phase": cycle.get("phase", "unknown"),
            "score": cycle.get("score", 50),
            "fear_greed": fg.get("current", 50),
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Signal generation
# ---------------------------------------------------------------------------

def generate_signals(
    data: dict,
    changes: Optional[dict],
    flow_analysis: dict,
    patterns: dict,
) -> list:
    """Generate actionable signals from all whale analysis."""
    signals = []

    # 1. Exchange flow signals
    overall = flow_analysis.get("overall_signal", "neutral")
    if overall != "neutral":
        strength = "strong" if abs(flow_analysis.get("bitcoin", {}).get("net_amount", 0)) > 50 else "moderate"
        signals.append({
            "type": "exchange_flow",
            "direction": "bearish" if overall == "bearish" else "bullish",
            "strength": strength,
            "message": flow_analysis.get("interpretation", ""),
            "emoji": "🔴" if overall == "bearish" else "🟢",
        })

    # 2. Large movement alerts
    for chain in ["bitcoin", "ethereum"]:
        for wallet in data.get(chain, []):
            for tx in wallet.get("recent_large_txs", []):
                value = tx.get("value_btc", tx.get("value_eth", 0))
                unit = "BTC" if chain == "bitcoin" else "ETH"
                threshold = LARGE_BTC if chain == "bitcoin" else LARGE_ETH

                if value >= threshold * 5:
                    strength = "critical"
                elif value >= threshold * 2:
                    strength = "strong"
                else:
                    strength = "moderate"

                direction = tx.get("direction", "?")
                exchange = tx.get("exchange") or tx.get("counterparty_label")

                msg = f"{wallet['label']}: {value:,.0f} {unit} {direction}"
                if exchange:
                    msg += f" → {exchange}"

                signals.append({
                    "type": "large_movement",
                    "chain": chain,
                    "direction": "bearish" if direction == "OUT" and exchange else "bullish" if direction == "IN" else "neutral",
                    "strength": strength,
                    "message": msg,
                    "emoji": "🐋",
                    "age": tx.get("age", "?"),
                })

    # 3. Accumulation/distribution signals
    if changes:
        accumulators = changes["summary"].get("accumulators", 0)
        distributors = changes["summary"].get("distributors", 0)

        if accumulators > distributors * 2 and accumulators >= 2:
            signals.append({
                "type": "accumulation_trend",
                "direction": "bullish",
                "strength": "strong",
                "message": f"{accumulators} whales accumulating vs {distributors} distributing",
                "emoji": "🟢",
            })
        elif distributors > accumulators * 2 and distributors >= 2:
            signals.append({
                "type": "distribution_trend",
                "direction": "bearish",
                "strength": "strong",
                "message": f"{distributors} whales distributing vs {accumulators} accumulating",
                "emoji": "🔴",
            })

    # 4. Pattern-based signals
    for chain in ["bitcoin", "ethereum"]:
        heavy_dist = [p for p in patterns.get(chain, []) if p["pattern"] == "heavy_distribution"]
        heavy_acc = [p for p in patterns.get(chain, []) if p["pattern"] == "heavy_accumulation"]

        if heavy_dist:
            labels = ", ".join(p["label"] for p in heavy_dist[:3])
            signals.append({
                "type": "pattern",
                "chain": chain,
                "direction": "bearish",
                "strength": "strong",
                "message": f"Heavy distribution detected: {labels}",
                "emoji": "⚠️",
            })
        if heavy_acc:
            labels = ", ".join(p["label"] for p in heavy_acc[:3])
            signals.append({
                "type": "pattern",
                "chain": chain,
                "direction": "bullish",
                "strength": "strong",
                "message": f"Heavy accumulation detected: {labels}",
                "emoji": "💪",
            })

    # Sort: critical first, then strong, then moderate
    strength_order = {"critical": 0, "strong": 1, "moderate": 2}
    signals.sort(key=lambda x: strength_order.get(x.get("strength", "moderate"), 3))

    return signals


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: dict):
    """Print formatted whale signals report."""
    signals = result.get("signals", [])
    flow_analysis = result.get("flow_analysis", {})
    patterns = result.get("patterns", {})
    changes = result.get("balance_changes")
    smart_money = result.get("smart_money", {})

    print("\n" + "=" * 60)
    print("🐋 WHALE SIGNALS REPORT")
    print(f"📅 {result.get('timestamp', 'N/A')}")
    print("=" * 60)

    # Signals summary
    if signals:
        bullish = sum(1 for s in signals if s["direction"] == "bullish")
        bearish = sum(1 for s in signals if s["direction"] == "bearish")
        neutral = len(signals) - bullish - bearish

        if bullish > bearish:
            overall_emoji = "🟢"
            overall = "BULLISH"
        elif bearish > bullish:
            overall_emoji = "🔴"
            overall = "BEARISH"
        else:
            overall_emoji = "⚪"
            overall = "MIXED"

        print(f"\n{overall_emoji} Overall Whale Signal: {overall}")
        print(f"  🟢 Bullish: {bullish} | 🔴 Bearish: {bearish} | ⚪ Neutral: {neutral}")

        print(f"\n{'─' * 60}")
        print("📡 SIGNALS")
        print(f"{'─' * 60}")
        for s in signals:
            strength = s.get("strength", "?")
            strength_tag = {"critical": "🚨", "strong": "❗", "moderate": "ℹ️"}.get(strength, "")
            dir_emoji = "🟢" if s["direction"] == "bullish" else "🔴" if s["direction"] == "bearish" else "⚪"
            age = f" ({s['age']})" if s.get("age") else ""
            print(f"  {strength_tag} {s['emoji']} {dir_emoji} {s['message']}{age}")
    else:
        print("\n⚪ No significant whale signals detected")

    # Exchange flows
    if flow_analysis:
        print(f"\n{'─' * 60}")
        print("🏦 EXCHANGE FLOWS")
        print(f"{'─' * 60}")

        for chain_name, chain_key in [("Bitcoin", "bitcoin"), ("Ethereum", "ethereum")]:
            cf = flow_analysis.get(chain_key, {})
            if cf.get("inflow_count", 0) or cf.get("outflow_count", 0):
                net = cf.get("net_amount", 0)
                unit = cf.get("unit", "?")
                net_usd = cf.get("net_usd", 0)
                signal = cf.get("signal", "neutral")

                sig_emoji = "🔴" if signal == "bearish" else "🟢" if signal == "bullish" else "⚪"
                direction = "→ Exchanges" if net > 0 else "← Cold Storage" if net < 0 else "Balanced"

                print(f"\n  {chain_name}:")
                print(f"    Deposits:    {cf.get('inflow_count', 0)}")
                print(f"    Withdrawals: {cf.get('outflow_count', 0)}")
                print(f"    Net:         {abs(net):,.4f} {unit} (~${abs(net_usd):,.0f}) {direction}")
                print(f"    Signal:      {sig_emoji} {signal.title()}")

                # Per-exchange breakdown
                for exch, amount in cf.get("by_exchange_in", {}).items():
                    print(f"      ↗️ {exch}: {amount:,.2f} {unit} in")
                for exch, amount in cf.get("by_exchange_out", {}).items():
                    print(f"      ↙️ {exch}: {amount:,.2f} {unit} out")

    # Balance changes
    if changes:
        has_changes = any(changes.get(c) for c in ["bitcoin", "ethereum", "solana"])
        if has_changes:
            print(f"\n{'─' * 60}")
            print("📊 BALANCE CHANGES (vs previous snapshot)")
            print(f"{'─' * 60}")

            summary = changes.get("summary", {})
            print(f"  🟢 Accumulating: {summary.get('accumulators', 0)} | "
                  f"🔴 Distributing: {summary.get('distributors', 0)} | "
                  f"⚪ Unchanged: {summary.get('unchanged', 0)}")

            for chain in ["bitcoin", "ethereum", "solana"]:
                chain_changes = changes.get(chain, [])
                if not chain_changes:
                    continue

                chain_label = {"bitcoin": "₿ BTC", "ethereum": "⟠ ETH", "solana": "◎ SOL"}[chain]
                print(f"\n  {chain_label}:")

                for c in chain_changes[:5]:
                    print(f"    {c['emoji']} {c['label']}: {c['abs_change']:+,.4f} {c['unit']} "
                          f"({c['pct_change']:+.2f}%) → {c['pattern']}")

    # Transaction patterns
    if patterns:
        has_patterns = any(patterns.get(c) for c in ["bitcoin", "ethereum"])
        if has_patterns:
            print(f"\n{'─' * 60}")
            print("🔄 TRANSACTION PATTERNS")
            print(f"{'─' * 60}")

            for chain in ["bitcoin", "ethereum"]:
                chain_patterns = patterns.get(chain, [])
                if not chain_patterns:
                    continue

                chain_label = {"bitcoin": "₿ BTC", "ethereum": "⟠ ETH"}[chain]
                print(f"\n  {chain_label}:")

                for p in chain_patterns:
                    balance_str = f"{p['balance']:,.2f} {p['unit']}" if p.get("balance") else "?"
                    print(f"    {p['emoji']} {p['label']:<25} {p['pattern']:<22} ({balance_str})")
                    if p["pattern"] != "dormant":
                        print(f"       {p['description']}")

    # Smart money rankings
    if smart_money:
        has_rankings = any(smart_money.get(c) for c in ["bitcoin", "ethereum"])
        if has_rankings:
            print(f"\n{'─' * 60}")
            print("🏆 SMART MONEY RANKINGS")
            print(f"{'─' * 60}")

            for chain in ["bitcoin", "ethereum"]:
                rankings = smart_money.get(chain, [])
                if not rankings:
                    continue

                chain_label = {"bitcoin": "₿ BTC", "ethereum": "⟠ ETH"}[chain]
                print(f"\n  {chain_label}:")
                print(f"  {'RANK':<5} {'SCORE':>6} {'TIER':<16} {'WALLET':<25} {'BALANCE':>12}")

                for i, r in enumerate(rankings, 1):
                    balance_str = f"{r['balance']:,.2f} {r['unit']}" if r.get("balance") else "N/A"
                    print(f"  {i:<5} {r['score']:>5.1f} {r['tier']:<16} {r['label']:<25} {balance_str:>12}")

    print("\n" + "=" * 60)
    print("✅ Whale signal analysis complete")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_analysis(quick: bool = False, flows_only: bool = False) -> dict:
    """Run full whale signal analysis."""
    print("=" * 60)
    print("🐋 WHALE SIGNALS ANALYZER")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    # 1. Load latest whale data
    print("\n📦 Loading whale data...")
    data = load_latest_whale_data()
    if not data:
        return {}

    ts = data.get("timestamp", "?")
    btc_count = len(data.get("bitcoin", []))
    eth_count = len(data.get("ethereum", []))
    sol_count = len(data.get("solana", []))
    print(f"  Snapshot: {ts}")
    print(f"  Wallets: {btc_count} BTC, {eth_count} ETH, {sol_count} SOL")

    # 2. Exchange flow analysis
    print("\n🏦 Analyzing exchange flows...")
    flow_analysis = analyze_exchange_flows(data)

    if flows_only:
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "flow_analysis": flow_analysis,
            "signals": generate_signals(data, None, flow_analysis, {}),
        }
        save_result(result)
        print_report(result)
        return result

    # 3. Transaction pattern classification
    print("\n🔄 Classifying transaction patterns...")
    patterns = classify_tx_patterns(data)

    # 4. Balance change detection (needs historical)
    changes = None
    if not quick:
        print("\n📊 Comparing with previous snapshots...")
        snapshots = load_whale_snapshots()
        if len(snapshots) >= 2:
            current = snapshots[0]
            previous = snapshots[1]
            changes = compare_snapshots(current, previous)
            print(f"  Comparing {current.get('_file', '?')} vs {previous.get('_file', '?')}")
        else:
            print("  ⚠️  Only 1 snapshot available — need 2+ for comparison")

    # 5. Smart money scoring
    print("\n🏆 Computing smart money scores...")
    smart_money = compute_smart_money_scores(data, changes)

    # 6. Generate signals
    print("\n📡 Generating signals...")
    signals = generate_signals(data, changes, flow_analysis, patterns)

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "data_timestamp": ts,
        "wallet_counts": {"btc": btc_count, "eth": eth_count, "sol": sol_count},
        "signals": signals,
        "flow_analysis": flow_analysis,
        "patterns": patterns,
        "balance_changes": changes,
        "smart_money": smart_money,
        "signal_summary": {
            "total": len(signals),
            "bullish": sum(1 for s in signals if s["direction"] == "bullish"),
            "bearish": sum(1 for s in signals if s["direction"] == "bearish"),
        },
    }

    save_result(result)
    print_report(result)
    return result


def save_result(result: dict):
    """Save analysis result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write latest
    latest = DATA_DIR / "whale_signals_latest.json"
    with open(latest, "w") as f:
        json.dump(result, f, indent=2)
    
    # Update history
    history_file = DATA_DIR / "whale_signals_history.json"
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
    
    print(f"\n💾 Saved")


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    flows_only = "--flows" in sys.argv
    run_analysis(quick=quick, flows_only=flows_only)
