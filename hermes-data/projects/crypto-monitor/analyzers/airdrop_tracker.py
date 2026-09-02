#!/usr/bin/env python3
"""
Airdrop Tracker — Priority scoring, farming progress, and deadline monitoring.

Features:
  - Priority scoring (probability × expected ROI ÷ cost)
  - Status classification and timeline estimation
  - Per-wallet farming progress tracking (user-editable JSON)
  - Action checklists per airdrop
  - Category analysis (which sectors have most opportunity)
  - ROI estimation from historical airdrop data
  - Deadline/urgency detection
  - Scam red flag checking

Usage:
  python3 analyzers/airdrop_tracker.py              # Full analysis + recommendations
  python3 analyzers/airdrop_tracker.py --quick      # Quick priority ranking only
  python3 analyzers/airdrop_tracker.py --progress   # Show farming progress
  python3 analyzers/airdrop_tracker.py --category   # Category breakdown
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = BASE_DIR / "config" / "settings.json"
DATA_DIR = BASE_DIR / "data" / "airdrops"
PROGRESS_FILE = DATA_DIR / "farming_progress.json"

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
THRESHOLDS = CONFIG.get("thresholds", {}).get("airdrop", {})

# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

PROBABILITY_SCORES = THRESHOLDS.get("probability_scores", {
    "very_high": 95,
    "high": 75,
    "medium": 50,
    "low_to_medium": 35,
    "low": 20,
    "unknown": 30,
})

COST_SCORES = {
    "free": 100,          # zero cost = max score
    "very_low": 90,
    "low": 75,
    "low_to_medium": 60,
    "medium": 45,
    "medium_to_high": 30,
    "high": 15,
    "very_high": 5,
}

STATUS_URGENCY = {
    "confirmed_airdrop": 95,   # confirmed = do it NOW
    "ongoing": 80,             # active campaign
    "potential_airdrop": 60,   # likely but unconfirmed
    "upcoming": 50,            # not live yet
    "ended": 0,                # done
}

# Historical average airdrop values for ROI estimation
HISTORICAL_AVG_VALUES = THRESHOLDS.get("historical_avg_values", {
    "layer2_networks": 2500,
    "defi_protocols": 5000,
    "dex_trading": 3000,
    "bitcoin_ecosystem": 1500,
    "ai_and_compute": 2000,
    "testnets": 800,
    "social_and_identity": 500,
})

COST_ESTIMATES = THRESHOLDS.get("cost_estimates", {
    "free": 0,
    "very_low": 10,
    "low": 25,
    "low_to_medium": 75,
    "medium": 150,
    "medium_to_high": 400,
    "high": 1000,
    "very_high": 3000,
})


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_airdrop_config() -> dict:
    """Load airdrop opportunities config."""
    config_path = CONFIG_DIR / "airdrop_opportunities.json"
    if not config_path.exists():
        print("⚠️  airdrop_opportunities.json not found")
        return {}
    with open(config_path) as f:
        return json.load(f)


def load_farming_progress() -> dict:
    """Load user's farming progress tracking."""
    if not PROGRESS_FILE.exists():
        return {}
    with open(PROGRESS_FILE) as f:
        return json.load(f)


def save_farming_progress(progress: dict):
    """Save farming progress."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def init_farming_progress(airdrops: list) -> dict:
    """Initialize farming progress template for all airdrops."""
    progress = load_farming_progress()

    for airdrop in airdrops:
        name = airdrop["name"]
        if name not in progress:
            metrics = airdrop.get("tracking_metrics", [])
            progress[name] = {
                "status": "not_started",  # not_started, in_progress, completed, skipped
                "wallets": [],
                "started_date": None,
                "last_activity": None,
                "notes": "",
                "metrics": {m: 0 for m in metrics},
                "estimated_cost_usd": 0,
                "tasks_completed": [],
            }

    save_farming_progress(progress)
    return progress


# ---------------------------------------------------------------------------
# Flatten all airdrops from nested config
# ---------------------------------------------------------------------------

def flatten_airdrops(config: dict) -> list:
    """Flatten all airdrops from categorized config into a single list."""
    airdrops = []
    hp = config.get("high_priority_airdrops", {})

    for category, items in hp.items():
        for item in items:
            item["_category"] = category
            airdrops.append(item)

    return airdrops


# ---------------------------------------------------------------------------
# Priority scoring
# ---------------------------------------------------------------------------

def score_airdrop(airdrop: dict) -> dict:
    """Score a single airdrop opportunity.

    Priority Score = (Probability × 0.35) + (Cost Efficiency × 0.25) +
                     (Status Urgency × 0.20) + (Est. ROI × 0.20)

    Returns airdrop dict enriched with scoring data.
    """
    name = airdrop.get("name", "Unknown")
    probability = airdrop.get("probability", "medium")
    cost = airdrop.get("cost", "medium")
    status = airdrop.get("status", "potential_airdrop")
    category = airdrop.get("_category", "unknown")

    # Component scores
    prob_score = PROBABILITY_SCORES.get(probability, 30)
    cost_score = COST_SCORES.get(cost, 45)
    urgency_score = STATUS_URGENCY.get(status, 50)

    # ROI estimation
    est_value = HISTORICAL_AVG_VALUES.get(category, 1500)
    est_cost = COST_ESTIMATES.get(cost, 150)

    if est_cost > 0:
        roi_ratio = est_value / est_cost
        roi_score = min(100, roi_ratio * 5)  # cap at 100
    else:
        roi_ratio = float("inf")
        roi_score = 100  # free = perfect ROI

    # Weighted composite
    priority = (
        prob_score * 0.35 +
        cost_score * 0.25 +
        urgency_score * 0.20 +
        roi_score * 0.20
    )

    # Tier classification
    if priority >= 80:
        tier = "S"
        tier_emoji = "🔥"
        tier_label = "Must Do"
    elif priority >= 65:
        tier = "A"
        tier_emoji = "⭐"
        tier_label = "High Priority"
    elif priority >= 50:
        tier = "B"
        tier_emoji = "📊"
        tier_label = "Worth Considering"
    elif priority >= 35:
        tier = "C"
        tier_emoji = "📎"
        tier_label = "Low Priority"
    else:
        tier = "D"
        tier_emoji = "⏭️"
        tier_label = "Skip Unless Free"

    return {
        "name": name,
        "category": category,
        "status": status,
        "probability": probability,
        "cost": cost,
        "priority_score": round(priority, 1),
        "tier": tier,
        "tier_emoji": tier_emoji,
        "tier_label": tier_label,
        "components": {
            "probability": prob_score,
            "cost_efficiency": cost_score,
            "urgency": urgency_score,
            "roi": round(roi_score, 1),
        },
        "roi_estimate": {
            "expected_value_usd": est_value,
            "estimated_cost_usd": est_cost,
            "roi_ratio": round(roi_ratio, 1) if roi_ratio != float("inf") else "∞",
        },
        "actions": airdrop.get("actions", []),
        "why_likely": airdrop.get("why_likely", ""),
        "tracking_metrics": airdrop.get("tracking_metrics", []),
        "url": airdrop.get("url", ""),
    }


def rank_airdrops(airdrops: list) -> list:
    """Score and rank all airdrops."""
    scored = [score_airdrop(a) for a in airdrops]
    scored.sort(key=lambda x: x["priority_score"], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Category analysis
# ---------------------------------------------------------------------------

def analyze_categories(scored: list) -> dict:
    """Analyze opportunities by category."""
    categories = defaultdict(lambda: {
        "airdrops": [],
        "avg_priority": 0,
        "total_expected_value": 0,
        "total_estimated_cost": 0,
        "best": None,
    })

    for a in scored:
        cat = a["category"]
        categories[cat]["airdrops"].append(a)
        categories[cat]["total_expected_value"] += a["roi_estimate"]["expected_value_usd"]
        categories[cat]["total_estimated_cost"] += a["roi_estimate"]["estimated_cost_usd"]

    result = {}
    for cat, data in categories.items():
        airdrops = data["airdrops"]
        avg_priority = sum(a["priority_score"] for a in airdrops) / len(airdrops)
        best = max(airdrops, key=lambda x: x["priority_score"])

        ev = data["total_expected_value"]
        cost = data["total_estimated_cost"]

        result[cat] = {
            "count": len(airdrops),
            "avg_priority": round(avg_priority, 1),
            "total_expected_value": ev,
            "total_estimated_cost": cost,
            "net_expected": ev - cost,
            "best_opportunity": best["name"],
            "best_score": best["priority_score"],
        }

    return dict(sorted(result.items(), key=lambda x: x[1]["avg_priority"], reverse=True))


# ---------------------------------------------------------------------------
# Urgency detection
# ---------------------------------------------------------------------------

def detect_urgency(scored: list) -> list:
    """Flag time-sensitive opportunities."""
    urgent = []

    for a in scored:
        urgency_reasons = []

        if a["status"] == "confirmed_airdrop":
            urgency_reasons.append("⚡ Airdrop CONFIRMED — farm immediately")
        if a["status"] == "ongoing":
            urgency_reasons.append("🏃 Active campaign — don't miss window")
        if a["probability"] == "very_high" and a["cost"] == "free":
            urgency_reasons.append("💎 Free + very high probability — no-brainer")
        if a["tier"] == "S":
            urgency_reasons.append("🔥 S-tier opportunity")

        if urgency_reasons:
            urgent.append({
                "name": a["name"],
                "tier": a["tier"],
                "tier_emoji": a["tier_emoji"],
                "priority_score": a["priority_score"],
                "reasons": urgency_reasons,
            })

    return urgent


# ---------------------------------------------------------------------------
# Recommendations engine
# ---------------------------------------------------------------------------

def generate_recommendations(
    scored: list,
    progress: dict,
    config: dict,
) -> list:
    """Generate personalized recommendations."""
    recs = []

    # 1. Best opportunities not yet started
    not_started = [
        a for a in scored
        if progress.get(a["name"], {}).get("status") in ("not_started", None)
        and a["tier"] in ("S", "A")
    ]
    if not_started:
        top = not_started[0]
        recs.append({
            "type": "start_farming",
            "priority": "high",
            "emoji": "🚀",
            "message": f"Start farming {top['name']} — {top['tier_emoji']} Tier {top['tier']} "
                       f"(score: {top['priority_score']}, est. value: ${top['roi_estimate']['expected_value_usd']:,})",
            "actions": top["actions"][:3],
        })

    # 2. Free opportunities not being farmed
    free_ops = [
        a for a in scored
        if a["cost"] == "free"
        and progress.get(a["name"], {}).get("status") in ("not_started", None)
    ]
    if free_ops:
        names = ", ".join(a["name"] for a in free_ops[:3])
        recs.append({
            "type": "free_opportunities",
            "priority": "medium",
            "emoji": "🆓",
            "message": f"Free airdrops available: {names} — zero cost, just time",
        })

    # 3. In-progress reminders
    in_progress = [
        (name, data) for name, data in progress.items()
        if data.get("status") == "in_progress"
    ]
    if in_progress:
        for name, data in in_progress:
            last = data.get("last_activity")
            if last:
                try:
                    last_dt = datetime.fromisoformat(last)
                    days_since = (datetime.utcnow() - last_dt).days
                    if days_since > 7:
                        recs.append({
                            "type": "activity_reminder",
                            "priority": "medium",
                            "emoji": "⏰",
                            "message": f"{name}: No activity in {days_since} days — "
                                       f"keep farming to maintain eligibility",
                        })
                except ValueError:
                    pass

    # 4. Strategy suggestions based on portfolio
    strategies = config.get("farming_strategies", [])
    recommended = [s for s in strategies if s.get("recommended")]
    if recommended:
        strat = recommended[0]
        recs.append({
            "type": "strategy",
            "priority": "info",
            "emoji": "📋",
            "message": f"Recommended strategy: {strat['strategy']} — {strat['description']}",
        })

    # 5. Diversification check
    if progress:
        categories_farmed = set()
        for name, data in progress.items():
            if data.get("status") == "in_progress":
                # Find category from scored
                match = next((a for a in scored if a["name"] == name), None)
                if match:
                    categories_farmed.add(match["category"])

        all_cats = set(a["category"] for a in scored)
        missing = all_cats - categories_farmed
        if missing and len(categories_farmed) > 0:
            recs.append({
                "type": "diversification",
                "priority": "info",
                "emoji": "🎯",
                "message": f"Consider diversifying into: {', '.join(c.replace('_', ' ').title() for c in list(missing)[:3])}",
            })

    return recs


# ---------------------------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------------------------

def compute_portfolio_summary(scored: list, progress: dict) -> dict:
    """Compute farming portfolio summary."""
    total_expected = 0
    total_cost = 0
    farming_count = 0
    completed_count = 0
    skipped_count = 0

    for a in scored:
        name = a["name"]
        p = progress.get(name, {})
        status = p.get("status", "not_started")

        if status == "in_progress":
            farming_count += 1
            total_expected += a["roi_estimate"]["expected_value_usd"]
            total_cost += p.get("estimated_cost_usd", a["roi_estimate"]["estimated_cost_usd"])
        elif status == "completed":
            completed_count += 1
            total_expected += a["roi_estimate"]["expected_value_usd"]
            total_cost += p.get("estimated_cost_usd", a["roi_estimate"]["estimated_cost_usd"])
        elif status == "skipped":
            skipped_count += 1

    return {
        "total_opportunities": len(scored),
        "farming": farming_count,
        "completed": completed_count,
        "skipped": skipped_count,
        "not_started": len(scored) - farming_count - completed_count - skipped_count,
        "total_expected_value": total_expected,
        "total_estimated_cost": total_cost,
        "net_expected_profit": total_expected - total_cost,
        "portfolio_roi": round(total_expected / total_cost, 1) if total_cost > 0 else "∞",
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: dict):
    """Print formatted airdrop tracker report."""
    scored = result.get("ranked_airdrops", [])
    categories = result.get("categories", {})
    urgent = result.get("urgent", [])
    recs = result.get("recommendations", [])
    portfolio = result.get("portfolio", {})
    progress = result.get("progress", {})

    print("\n" + "=" * 60)
    print("🪂 AIRDROP TRACKER REPORT")
    print(f"📅 {result.get('timestamp', 'N/A')}")
    print("=" * 60)

    # Portfolio summary
    if portfolio:
        print(f"\n💼 PORTFOLIO SUMMARY")
        print(f"{'─' * 60}")
        print(f"  Opportunities:    {portfolio['total_opportunities']}")
        print(f"  Farming:          {portfolio['farming']}")
        print(f"  Completed:        {portfolio['completed']}")
        print(f"  Not Started:      {portfolio['not_started']}")
        if portfolio["farming"] or portfolio["completed"]:
            print(f"  Expected Value:   ${portfolio['total_expected_value']:,}")
            print(f"  Estimated Cost:   ${portfolio['total_estimated_cost']:,}")
            print(f"  Net Expected:     ${portfolio['net_expected_profit']:,}")
            print(f"  Portfolio ROI:    {portfolio['portfolio_roi']}x")

    # Urgent actions
    if urgent:
        print(f"\n🚨 URGENT — ACT NOW")
        print(f"{'─' * 60}")
        for u in urgent:
            print(f"  {u['tier_emoji']} {u['name']} (score: {u['priority_score']})")
            for reason in u["reasons"]:
                print(f"    {reason}")

    # Priority ranking
    if scored:
        print(f"\n📊 PRIORITY RANKING")
        print(f"{'─' * 60}")
        print(f"  {'#':<3} {'TIER':<4} {'SCORE':>6} {'NAME':<24} {'PROB':<10} {'COST':<12} {'EST.VALUE':>10}")
        print(f"  {'─' * 57}")

        for i, a in enumerate(scored, 1):
            prob = a["probability"].replace("_", " ")
            cost = a["cost"].replace("_", " ")
            ev = f"${a['roi_estimate']['expected_value_usd']:,}"
            status_tag = ""
            p = progress.get(a["name"], {})
            if p.get("status") == "in_progress":
                status_tag = " 🔄"
            elif p.get("status") == "completed":
                status_tag = " ✅"
            elif p.get("status") == "skipped":
                status_tag = " ⏭️"

            print(f"  {i:<3} {a['tier_emoji']}{a['tier']:<3} {a['priority_score']:>5.1f} "
                  f"{a['name']:<24} {prob:<10} {cost:<12} {ev:>10}{status_tag}")

    # Category analysis
    if categories:
        print(f"\n📂 CATEGORY ANALYSIS")
        print(f"{'─' * 60}")
        print(f"  {'CATEGORY':<25} {'#':>3} {'AVG':>5} {'EXP.VALUE':>10} {'EST.COST':>10} {'BEST':>15}")

        for cat, data in categories.items():
            cat_label = cat.replace("_", " ").title()[:24]
            print(f"  {cat_label:<25} {data['count']:>3} {data['avg_priority']:>5.1f} "
                  f"${data['total_expected_value']:>8,} ${data['total_estimated_cost']:>8,} "
                  f"{data['best_opportunity'][:15]:>15}")

    # Recommendations
    if recs:
        print(f"\n💡 RECOMMENDATIONS")
        print(f"{'─' * 60}")
        for r in recs:
            print(f"  {r['emoji']} [{r['priority'].upper()}] {r['message']}")
            if r.get("actions"):
                for action in r["actions"]:
                    print(f"     → {action}")

    # Top 3 detailed action plans
    top3 = [a for a in scored if a["tier"] in ("S", "A")][:3]
    if top3:
        print(f"\n🎯 TOP ACTION PLANS")
        print(f"{'─' * 60}")
        for a in top3:
            print(f"\n  {a['tier_emoji']} {a['name']} (Tier {a['tier']}, score: {a['priority_score']})")
            print(f"     Why: {a['why_likely'][:80]}")
            print(f"     Cost: ~${a['roi_estimate']['estimated_cost_usd']} | Expected: ~${a['roi_estimate']['expected_value_usd']:,}")
            print(f"     Actions:")
            for action in a["actions"]:
                p = progress.get(a["name"], {})
                done = "✅" if action in p.get("tasks_completed", []) else "⬜"
                print(f"       {done} {action}")
            if a["tracking_metrics"]:
                metrics = ", ".join(a["tracking_metrics"][:4])
                print(f"     Track: {metrics}")

    print("\n" + "=" * 60)
    print("✅ Airdrop analysis complete")
    print("=" * 60)


def print_progress(scored: list, progress: dict):
    """Print detailed farming progress."""
    print("\n" + "=" * 60)
    print("📋 FARMING PROGRESS")
    print("=" * 60)

    for a in scored:
        name = a["name"]
        p = progress.get(name, {})
        status = p.get("status", "not_started")

        status_emoji = {
            "not_started": "⬜",
            "in_progress": "🔄",
            "completed": "✅",
            "skipped": "⏭️",
        }.get(status, "❓")

        print(f"\n{status_emoji} {name} [{a['tier_emoji']} Tier {a['tier']}]")
        print(f"  Status: {status.replace('_', ' ').title()}")

        if p.get("wallets"):
            print(f"  Wallets: {len(p['wallets'])}")
        if p.get("started_date"):
            print(f"  Started: {p['started_date']}")
        if p.get("last_activity"):
            print(f"  Last Activity: {p['last_activity']}")
        if p.get("estimated_cost_usd"):
            print(f"  Cost So Far: ${p['estimated_cost_usd']}")
        if p.get("notes"):
            print(f"  Notes: {p['notes']}")

        # Metrics
        metrics = p.get("metrics", {})
        non_zero = {k: v for k, v in metrics.items() if v}
        if non_zero:
            print(f"  Metrics:")
            for k, v in non_zero.items():
                print(f"    {k}: {v}")

        # Tasks
        tasks = a.get("actions", [])
        completed = p.get("tasks_completed", [])
        if tasks:
            done = len(completed)
            total = len(tasks)
            bar_len = 15
            filled = int(done / total * bar_len) if total else 0
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"  Progress: [{bar}] {done}/{total}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_analysis(
    quick: bool = False,
    show_progress: bool = False,
    category_only: bool = False,
) -> dict:
    """Run full airdrop analysis."""
    print("=" * 60)
    print("🪂 AIRDROP TRACKER")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    # 1. Load config
    print("\n📦 Loading airdrop config...")
    config = load_airdrop_config()
    if not config:
        return {}

    airdrops = flatten_airdrops(config)
    print(f"  Found {len(airdrops)} airdrop opportunities across {len(config.get('high_priority_airdrops', {}))} categories")

    # 2. Score and rank
    print("\n📊 Scoring airdrops...")
    scored = rank_airdrops(airdrops)

    # 3. Load/init farming progress
    progress = init_farming_progress(airdrops)
    print(f"  Farming progress loaded ({sum(1 for p in progress.values() if p.get('status') == 'in_progress')} active)")

    if show_progress:
        print_progress(scored, progress)
        return {"ranked_airdrops": scored, "progress": progress}

    # 4. Category analysis
    print("\n📂 Analyzing categories...")
    categories = analyze_categories(scored)

    if category_only:
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "ranked_airdrops": scored,
            "categories": categories,
            "progress": progress,
            "portfolio": compute_portfolio_summary(scored, progress),
        }
        save_result(result)
        print_report(result)
        return result

    # 5. Urgency detection
    print("\n🚨 Checking urgency...")
    urgent = detect_urgency(scored)

    # 6. Recommendations
    recs = []
    if not quick:
        print("\n💡 Generating recommendations...")
        recs = generate_recommendations(scored, progress, config)

    # 7. Portfolio summary
    portfolio = compute_portfolio_summary(scored, progress)

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "ranked_airdrops": scored,
        "categories": categories,
        "urgent": urgent,
        "recommendations": recs,
        "portfolio": portfolio,
        "progress": progress,
        "total_opportunities": len(scored),
    }

    save_result(result)
    print_report(result)
    return result


def save_result(result: dict):
    """Save analysis result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Don't save full progress in snapshot (it's in farming_progress.json)
    save_data = {k: v for k, v in result.items() if k != "progress"}
    
    # Write latest
    latest = DATA_DIR / "airdrops_latest.json"
    with open(latest, "w") as f:
        json.dump(save_data, f, indent=2)
    
    # Update history
    history_file = DATA_DIR / "airdrops_history.json"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    if history_file.exists():
        history = json.loads(history_file.read_text())
    else:
        history = {}
    
    # Use date as key (overwrites if exists)
    history[today] = save_data
    
    history["last_updated"] = datetime.utcnow().isoformat()
    
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)
    
    print(f"\n💾 Saved")


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    show_progress = "--progress" in sys.argv
    category_only = "--category" in sys.argv
    run_analysis(quick=quick, show_progress=show_progress, category_only=category_only)
