#!/usr/bin/env python3
"""
Cycle Analyzer — Bull/bear market detection and cycle positioning.

Combines multiple indicators into a composite Cycle Score (0-100):
  0-20:  Deep bear / capitulation
  20-40: Late bear / accumulation
  40-60: Transition / early recovery
  60-80: Bull market
  80-100: Euphoria / cycle top risk

Data sources (all free, no API keys):
  - CoinGecko: historical prices, market data, BTC dominance
  - alternative.me: Fear & Greed Index (historical)
  - blockchain.com: BTC hash rate, difficulty
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from typing import Optional

# Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config" / "settings.json"
DATA_DIR = BASE_DIR / "data" / "cycle"
PRICES_DIR = BASE_DIR / "data" / "prices"

# Load config
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

CONFIG = load_config()
API_ENDPOINTS = CONFIG.get("api_endpoints", {})

# APIs
COINGECKO_BASE = API_ENDPOINTS.get("coingecko", "https://api.coingecko.com/api/v3")
FEAR_GREED_API = API_ENDPOINTS.get("fear_greed", "https://api.alternative.me/fng/")
BLOCKCHAIN_API = API_ENDPOINTS.get("blockchain_info", "https://api.blockchain.info")

# Rate limiting
REQUEST_DELAY = 1.5


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def api_get(url: str, timeout: int = 30) -> Optional[dict]:
    """GET JSON from URL with error handling."""
    req = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "crypto-monitor/1.0"
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"  ❌ HTTP {e.code}: {url[:80]}")
        return None
    except URLError as e:
        print(f"  ❌ URL error: {e.reason}")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None
    finally:
        time.sleep(REQUEST_DELAY)


def coingecko(endpoint: str, params: dict = None) -> Optional[dict]:
    """CoinGecko API request."""
    url = f"{COINGECKO_BASE}{endpoint}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    return api_get(url)


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

def fetch_historical_prices(coin_id: str = "bitcoin", days: int = 365) -> Optional[list]:
    """Fetch daily historical prices from CoinGecko.
    Returns list of [timestamp_ms, price] pairs.
    """
    print(f"  📈 Fetching {days}d history for {coin_id}...")
    data = coingecko(f"/coins/{coin_id}/market_chart", {
        "vs_currency": "usd",
        "days": str(days),
        "interval": "daily"
    })
    if data and "prices" in data:
        return data["prices"]
    return None


def fetch_market_top(limit: int = 50) -> Optional[list]:
    """Fetch top N coins by market cap with performance data."""
    print(f"  🏆 Fetching top {limit} coins...")
    data = coingecko("/coins/markets", {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": str(limit),
        "page": "1",
        "sparkline": "false",
        "price_change_percentage": "30d,90d"
    })
    return data if isinstance(data, list) else None


def fetch_global_data() -> Optional[dict]:
    """Fetch global market data (BTC dominance etc)."""
    print("  🌍 Fetching global market data...")
    data = coingecko("/global")
    return data.get("data") if data else None


def fetch_fear_greed(days: int = 30) -> Optional[list]:
    """Fetch Fear & Greed Index history."""
    print(f"  😱 Fetching {days}d Fear & Greed history...")
    data = api_get(f"{FEAR_GREED_API}?limit={days}&format=json")
    if data and "data" in data:
        return data["data"]
    return None


def fetch_btc_hashrate() -> Optional[dict]:
    """Fetch BTC hash rate from blockchain.com."""
    print("  ⛏️  Fetching BTC hash rate...")
    data = api_get(f"{BLOCKCHAIN_API}/charts/hash-rate?timespan=60days&format=json")
    return data


def fetch_btc_difficulty() -> Optional[dict]:
    """Fetch BTC mining difficulty."""
    print("  🔧 Fetching BTC difficulty...")
    data = api_get(f"{BLOCKCHAIN_API}/charts/difficulty?timespan=180days&format=json")
    return data


def fetch_ohlc_data(coin_id: str = "bitcoin", days: int = 14) -> Optional[list]:
    """Fetch OHLC data from CoinGecko for RSI calculation.
    Returns list of [timestamp, open, high, low, close] pairs.
    """
    print(f"  📊 Fetching OHLC for {coin_id} ({days}d)...")
    data = coingecko(f"/coins/{coin_id}/ohlc", {
        "vs_currency": "usd",
        "days": str(days)
    })
    if data and isinstance(data, list) and len(data) > 0:
        return data
    return None


def calc_rsi(ohlc_data: list, period: int = 14) -> Optional[dict]:
    """Calculate RSI from OHLC data.
    Returns RSI value and signal (oversold/neutral/overbought).
    """
    if not ohlc_data or len(ohlc_data) < period + 1:
        return None
    
    # Extract closing prices
    closes = [candle[4] for candle in ohlc_data]
    
    # Calculate price changes
    deltas = []
    for i in range(1, len(closes)):
        deltas.append(closes[i] - closes[i-1])
    
    if not deltas:
        return None
    
    # Separate gains and losses
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    # Calculate initial averages
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    # Signal
    if rsi < 30:
        signal = "oversold"
    elif rsi > 70:
        signal = "overbought"
    else:
        signal = "neutral"
    
    return {
        "value": round(rsi, 1),
        "signal": signal,
        "period": period
    }


# ---------------------------------------------------------------------------
# Indicator calculations
# ---------------------------------------------------------------------------

def calc_moving_average(prices: list, window: int) -> Optional[float]:
    """Calculate simple moving average from [timestamp, price] pairs.
    Uses the last `window` data points.
    """
    if not prices or len(prices) < window:
        return None
    recent = [p[1] for p in prices[-window:]]
    return sum(recent) / len(recent)


def calc_ma_cross(prices: list) -> dict:
    """Calculate 50/200 MA cross status.
    Returns current MAs and cross signal.
    """
    ma50 = calc_moving_average(prices, 50)
    ma200 = calc_moving_average(prices, 200)

    if ma50 is None or ma200 is None:
        return {"ma50": None, "ma200": None, "signal": "insufficient_data"}

    # Check if recently crossed
    signal = "golden_cross" if ma50 > ma200 else "death_cross"

    # Distance between MAs (strength of signal)
    spread_pct = ((ma50 - ma200) / ma200) * 100

    return {
        "ma50": round(ma50, 2),
        "ma200": round(ma200, 2),
        "signal": signal,
        "spread_pct": round(spread_pct, 2)
    }


def calc_pi_cycle(prices: list) -> dict:
    """Pi Cycle Top Indicator.
    111-day MA crossing above 350-day MA × 2 signals cycle top.
    """
    ma111 = calc_moving_average(prices, 111)
    ma350x2 = calc_moving_average(prices, 350)

    if ma111 is None or ma350x2 is None:
        return {"ma111": None, "ma350x2": None, "signal": "insufficient_data"}

    ma350x2_val = ma350x2 * 2
    distance_pct = ((ma350x2_val - ma111) / ma350x2_val) * 100

    signal = "cycle_top_risk" if ma111 >= ma350x2_val else "safe"

    return {
        "ma111": round(ma111, 2),
        "ma350x2": round(ma350x2_val, 2),
        "distance_pct": round(distance_pct, 2),
        "signal": signal
    }


def calc_price_vs_ma200(prices: list) -> dict:
    """Price position relative to 200-day MA.
    Acts as rough MVRV proxy — how extended price is from its mean.
    """
    if not prices or len(prices) < 200:
        return {"ratio": None, "signal": "insufficient_data"}

    current_price = prices[-1][1]
    ma200 = calc_moving_average(prices, 200)

    ratio = current_price / ma200
    deviation_pct = (ratio - 1) * 100

    if ratio < 0.7:
        signal = "deep_undervalued"
    elif ratio < 0.9:
        signal = "undervalued"
    elif ratio < 1.1:
        signal = "fair_value"
    elif ratio < 1.4:
        signal = "overvalued"
    else:
        signal = "highly_overvalued"

    return {
        "current_price": round(current_price, 2),
        "ma200": round(ma200, 2),
        "ratio": round(ratio, 3),
        "deviation_pct": round(deviation_pct, 2),
        "signal": signal
    }


def calc_fear_greed_trend(fg_data: list) -> dict:
    """Analyze Fear & Greed trend over time."""
    if not fg_data:
        return {"current": None, "avg_30d": None, "trend": "unknown"}

    values = [int(d["value"]) for d in fg_data]
    current = values[0]  # most recent first
    avg = sum(values) / len(values)

    # Trend: compare first half vs second half
    mid = len(values) // 2
    if mid > 0:
        recent_avg = sum(values[:mid]) / mid
        older_avg = sum(values[mid:]) / len(values[mid:])
        trend = "improving" if recent_avg > older_avg else "worsening"
    else:
        trend = "stable"

    # Classification
    if current <= 20:
        zone = "extreme_fear"
    elif current <= 40:
        zone = "fear"
    elif current <= 60:
        zone = "neutral"
    elif current <= 80:
        zone = "greed"
    else:
        zone = "extreme_greed"

    return {
        "current": current,
        "classification": fg_data[0].get("value_classification", zone),
        "avg_30d": round(avg, 1),
        "trend": trend,
        "zone": zone
    }


def calc_btc_dominance(global_data: dict) -> dict:
    """Analyze BTC dominance for altseason detection."""
    if not global_data:
        return {"dominance": None, "signal": "unknown"}

    mcap_pct = global_data.get("market_cap_percentage", {})
    btc_dom = mcap_pct.get("btc", 0)
    eth_dom = mcap_pct.get("eth", 0)

    # Altseason thresholds
    if btc_dom > 60:
        signal = "btc_season"
    elif btc_dom > 50:
        signal = "btc_leaning"
    elif btc_dom > 40:
        signal = "transitioning"
    else:
        signal = "altseason"

    return {
        "btc_dominance": round(btc_dom, 2),
        "eth_dominance": round(eth_dom, 2),
        "alt_dominance": round(100 - btc_dom - eth_dom, 2),
        "signal": signal
    }


def calc_altseason_index(market_data: list) -> dict:
    """Calculate altseason index.
    % of top 50 altcoins outperforming BTC over 90 days.
    75%+ = altseason, 25%- = bitcoin season.

    Uses current_price vs ath_change + 30d change as proxy when 90d is unavailable.
    Falls back to 30d performance comparison.
    """
    if not market_data:
        return {"index": None, "signal": "unknown"}

    # Find BTC performance — try 90d, fallback to 30d
    btc_perf = None
    perf_key = "price_change_percentage_90d_in_currency"
    fallback_key = "price_change_percentage_30d_in_currency"
    used_period = "90d"

    alts = []
    stablecoins = {"tether", "usd-coin", "dai", "trueusd", "first-digital-usd",
                   "ethena-usde", "usds", "binance-peg-busd"}

    # Check if 90d data is available
    has_90d = any(c.get(perf_key) is not None for c in market_data)
    if not has_90d:
        perf_key = fallback_key
        used_period = "30d"

    for coin in market_data:
        coin_id = coin.get("id", "")
        perf = coin.get(perf_key)

        if perf is None:
            continue

        if coin_id == "bitcoin":
            btc_perf = perf
        elif coin_id not in stablecoins and not coin_id.startswith("wrapped-"):
            alts.append({
                "id": coin_id,
                "symbol": coin.get("symbol", "?"),
                "perf": perf
            })

    if btc_perf is None or not alts:
        return {"index": None, "signal": "insufficient_data"}

    outperforming = [a for a in alts if a["perf"] > btc_perf]
    index = (len(outperforming) / len(alts)) * 100

    if index >= 75:
        signal = "altseason"
    elif index >= 50:
        signal = "alt_leaning"
    elif index >= 25:
        signal = "btc_leaning"
    else:
        signal = "bitcoin_season"

    # Top/bottom performers
    sorted_alts = sorted(alts, key=lambda x: x["perf"], reverse=True)
    top3 = sorted_alts[:3]
    bottom3 = sorted_alts[-3:]

    return {
        "index": round(index, 1),
        "period": used_period,
        "btc_change": round(btc_perf, 2),
        "alts_counted": len(alts),
        "outperforming_btc": len(outperforming),
        "signal": signal,
        "top_performers": [{
            "symbol": a["symbol"],
            "change": round(a["perf"], 2)
        } for a in top3],
        "worst_performers": [{
            "symbol": a["symbol"],
            "change": round(a["perf"], 2)
        } for a in bottom3]
    }


def calc_hashrate_trend(hr_data: dict) -> dict:
    """Analyze hash rate trend (miner confidence)."""
    if not hr_data or "values" not in hr_data:
        return {"trend": "unknown", "signal": "unknown"}

    values = hr_data["values"]
    if len(values) < 14:
        return {"trend": "unknown", "signal": "insufficient_data"}

    # Recent 7d vs previous 7d
    recent = [v["y"] for v in values[-7:]]
    older = [v["y"] for v in values[-14:-7]]

    avg_recent = sum(recent) / len(recent)
    avg_older = sum(older) / len(older)

    change_pct = ((avg_recent - avg_older) / avg_older) * 100

    if change_pct > 5:
        signal = "strong_growth"
    elif change_pct > 0:
        signal = "growing"
    elif change_pct > -5:
        signal = "stable"
    else:
        signal = "declining"

    # All-time context
    all_vals = [v["y"] for v in values]
    current = all_vals[-1]
    peak = max(all_vals)
    from_peak_pct = ((current - peak) / peak) * 100

    # blockchain.com returns in TH/s already for some endpoints,
    # or raw hashes — normalize to EH/s for readability
    if current > 1e9:
        display = round(current / 1e6, 1)  # Convert to EH/s if in TH/s
        unit = "EH/s"
    elif current > 1e6:
        display = round(current / 1e3, 1)
        unit = "PH/s"
    else:
        display = round(current, 1)
        unit = "TH/s"

    return {
        "current": display,
        "unit": unit,
        "change_7d_pct": round(change_pct, 2),
        "from_peak_pct": round(from_peak_pct, 2),
        "signal": signal
    }


def calc_market_cap_vs_ath(global_data: dict) -> dict:
    """Estimate cycle position from total market cap.
    Uses rough ATH reference (~3.9T Nov 2021 cycle, ~3.8T Dec 2024).
    """
    if not global_data:
        return {"signal": "unknown"}

    total_mcap = global_data.get("total_market_cap", {}).get("usd", 0)
    # Approximate historical ATH for total crypto market cap
    # Late 2024 peak was ~3.8T, Nov 2021 was ~3T
    ATH_REFERENCE = 3.9e12

    ratio = total_mcap / ATH_REFERENCE if ATH_REFERENCE else 0
    pct_of_ath = ratio * 100

    if pct_of_ath >= 95:
        signal = "at_ath"
    elif pct_of_ath >= 80:
        signal = "near_ath"
    elif pct_of_ath >= 60:
        signal = "recovery"
    elif pct_of_ath >= 40:
        signal = "mid_cycle"
    elif pct_of_ath >= 20:
        signal = "bear_market"
    else:
        signal = "deep_bear"

    return {
        "total_mcap_usd": round(total_mcap / 1e9, 2),
        "ath_reference_usd": round(ATH_REFERENCE / 1e9, 2),
        "pct_of_ath": round(pct_of_ath, 1),
        "signal": signal
    }


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------

def compute_cycle_score(indicators: dict) -> dict:
    """Compute composite Cycle Score (0-100) from all indicators.

    Weights:
      MA cross position:     20%
      Price vs 200d MA:      15%
      Fear & Greed:          15%
      BTC dominance:         10%
      Altseason index:       10%
      Hash rate trend:       10%
      Market cap vs ATH:     10%
      Pi Cycle:              10%
    """
    scores = {}
    weights = {}

    # 1. MA Cross (20%)
    ma = indicators.get("ma_cross", {})
    if ma.get("spread_pct") is not None:
        spread = ma["spread_pct"]
        # Spread of +20% = very bullish (90), 0 = neutral (50), -20% = bearish (10)
        score = max(0, min(100, 50 + spread * 2))
        scores["ma_cross"] = score
        weights["ma_cross"] = 0.20

    # 2. Price vs 200d MA (15%)
    pma = indicators.get("price_vs_ma200", {})
    if pma.get("ratio") is not None:
        ratio = pma["ratio"]
        # ratio 0.5 = 0, ratio 1.0 = 50, ratio 1.5 = 100
        score = max(0, min(100, (ratio - 0.5) * 100))
        scores["price_vs_ma200"] = score
        weights["price_vs_ma200"] = 0.15

    # 3. Fear & Greed (15%)
    fg = indicators.get("fear_greed", {})
    if fg.get("current") is not None:
        # Direct mapping: FG 0-100 → score 0-100
        scores["fear_greed"] = fg["current"]
        weights["fear_greed"] = 0.15

    # 4. BTC Dominance (10%) — inverted: high dominance = less alt risk appetite
    dom = indicators.get("btc_dominance", {})
    if dom.get("btc_dominance") is not None:
        btc_d = dom["btc_dominance"]
        # High BTC dom (>65) = risk-off (lower score ~30)
        # Low BTC dom (<40) = risk-on (higher score ~80)
        score = max(0, min(100, (65 - btc_d) * 2.5 + 50))
        scores["btc_dominance"] = score
        weights["btc_dominance"] = 0.10

    # 5. Altseason Index (10%)
    alt = indicators.get("altseason", {})
    if alt.get("index") is not None:
        scores["altseason"] = alt["index"]
        weights["altseason"] = 0.10

    # 6. Hash Rate (10%)
    hr = indicators.get("hashrate", {})
    if hr.get("change_7d_pct") is not None:
        change = hr["change_7d_pct"]
        from_peak = hr.get("from_peak_pct", 0)
        # Growing hash rate = bullish, near peak = extra bullish
        score = max(0, min(100, 60 + change * 2 + (100 + from_peak) * 0.2))
        scores["hashrate"] = score
        weights["hashrate"] = 0.10

    # 7. Market Cap vs ATH (10%)
    mcap = indicators.get("market_cap_vs_ath", {})
    if mcap.get("pct_of_ath") is not None:
        scores["market_cap_vs_ath"] = mcap["pct_of_ath"]
        weights["market_cap_vs_ath"] = 0.10

    # 8. Pi Cycle (10%)
    pi = indicators.get("pi_cycle", {})
    if pi.get("distance_pct") is not None:
        dist = pi["distance_pct"]
        # distance > 30% = safe (score ~60), < 5% = danger (score ~90 euphoria)
        # But also far below = early cycle
        if pi["signal"] == "cycle_top_risk":
            score = 95
        else:
            score = max(0, min(100, 80 - dist * 0.5))
        scores["pi_cycle"] = score
        weights["pi_cycle"] = 0.10

    # Weighted composite
    if not scores:
        return {"score": None, "phase": "unknown", "components": {}}

    total_weight = sum(weights.values())
    weighted_sum = sum(scores[k] * weights[k] for k in scores)
    composite = weighted_sum / total_weight

    # Phase classification
    if composite <= 20:
        phase = "capitulation"
        emoji = "💀"
        desc = "Deep bear — extreme fear, capitulation likely"
    elif composite <= 35:
        phase = "accumulation"
        emoji = "🧊"
        desc = "Late bear — smart money accumulating"
    elif composite <= 50:
        phase = "recovery"
        emoji = "🌱"
        desc = "Early recovery — trend shifting"
    elif composite <= 65:
        phase = "expansion"
        emoji = "📈"
        desc = "Bull market — growing momentum"
    elif composite <= 80:
        phase = "bull_market"
        emoji = "🐂"
        desc = "Strong bull — broad market rally"
    elif composite <= 90:
        phase = "euphoria"
        emoji = "🚀"
        desc = "Euphoria — high risk of local top"
    else:
        phase = "cycle_top"
        emoji = "🔴"
        desc = "Extreme euphoria — cycle top risk very high"

    return {
        "score": round(composite, 1),
        "phase": phase,
        "emoji": emoji,
        "description": desc,
        "components": {k: round(v, 1) for k, v in scores.items()},
        "weights": weights
    }


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run_analysis(quick: bool = False) -> dict:
    """Run full cycle analysis."""
    print("=" * 60)
    print("🔄 CYCLE ANALYZER")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    indicators = {}

    # 1. Historical BTC prices (need 365d for Pi Cycle)
    days_needed = 200 if quick else 365
    print(f"\n📊 Fetching data ({days_needed}d history)...")
    btc_prices = fetch_historical_prices("bitcoin", days_needed)

    # Fallback to shorter range if rate-limited
    if btc_prices is None and days_needed > 200:
        print("  ⚠️  Retrying with 200d...")
        btc_prices = fetch_historical_prices("bitcoin", 200)

    if btc_prices and len(btc_prices) >= 50:
        indicators["ma_cross"] = calc_ma_cross(btc_prices)
        indicators["price_vs_ma200"] = calc_price_vs_ma200(btc_prices)
        indicators["pi_cycle"] = calc_pi_cycle(btc_prices)
    else:
        print("  ⚠️  Insufficient price history")
    
    # RSI calculation
    ohlc_data = fetch_ohlc_data("bitcoin", 14)
    if ohlc_data:
        rsi = calc_rsi(ohlc_data, 14)
        if rsi:
            indicators["rsi"] = rsi
            print(f"  📊 BTC RSI(14): {rsi['value']} ({rsi['signal']})")

    # 2. Fear & Greed
    fg_data = fetch_fear_greed(30)
    if fg_data:
        indicators["fear_greed"] = calc_fear_greed_trend(fg_data)

    # 3. Global data (BTC dominance + market cap)
    global_data = fetch_global_data()
    if global_data:
        indicators["btc_dominance"] = calc_btc_dominance(global_data)
        indicators["market_cap_vs_ath"] = calc_market_cap_vs_ath(global_data)

    # 4. Altseason index (top 50 coins)
    if not quick:
        market_data = fetch_market_top(50)
        if market_data:
            indicators["altseason"] = calc_altseason_index(market_data)

    # 5. Hash rate
    if not quick:
        hr_data = fetch_btc_hashrate()
        if hr_data:
            indicators["hashrate"] = calc_hashrate_trend(hr_data)

    # Compute composite score
    print("\n🧮 Computing cycle score...")
    cycle = compute_cycle_score(indicators)

    # Build result
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "cycle_score": cycle,
        "indicators": indicators
    }

    # Save
    save_result(result)

    # Display
    print_report(result)

    return result


def save_result(result: dict):
    """Save analysis result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write latest
    latest = DATA_DIR / "cycle_latest.json"
    with open(latest, "w") as f:
        json.dump(result, f, indent=2)
    
    # Update history
    history_file = DATA_DIR / "cycle_history.json"
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


def print_report(result: dict):
    """Print formatted analysis report."""
    cycle = result["cycle_score"]
    indicators = result["indicators"]

    print("\n" + "=" * 60)
    print("📊 CYCLE ANALYSIS REPORT")
    print("=" * 60)

    # Cycle score
    score = cycle.get("score")
    if score is not None:
        bar_len = 30
        filled = int(score / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\n{cycle['emoji']} Cycle Score: {score}/100 — {cycle['phase'].upper()}")
        print(f"[{bar}]")
        print(f"  {cycle['description']}")
    else:
        print("\n⚠️  Could not compute cycle score (insufficient data)")

    # Component scores
    if cycle.get("components"):
        print(f"\n{'COMPONENT':<22} {'SCORE':>6} {'WEIGHT':>7}")
        print("-" * 38)
        for comp, score in sorted(cycle["components"].items(),
                                   key=lambda x: cycle["weights"].get(x[0], 0),
                                   reverse=True):
            weight = cycle["weights"].get(comp, 0)
            print(f"  {comp:<20} {score:>5.1f}  ({weight*100:.0f}%)")

    # Moving Averages
    ma = indicators.get("ma_cross", {})
    if ma.get("ma50"):
        print(f"\n📈 Moving Averages")
        signal_emoji = "🟢" if ma["signal"] == "golden_cross" else "🔴"
        print(f"  50d MA:  ${ma['ma50']:,.0f}")
        print(f"  200d MA: ${ma['ma200']:,.0f}")
        print(f"  Signal:  {signal_emoji} {ma['signal'].replace('_', ' ').title()} (spread: {ma['spread_pct']:+.1f}%)")

    # Price vs 200d MA
    pma = indicators.get("price_vs_ma200", {})
    if pma.get("ratio"):
        print(f"\n💰 Price vs 200d MA")
        print(f"  Current: ${pma['current_price']:,.0f}")
        print(f"  Ratio:   {pma['ratio']:.3f}x ({pma['deviation_pct']:+.1f}%)")
        print(f"  Signal:  {pma['signal'].replace('_', ' ').title()}")

    # Pi Cycle
    pi = indicators.get("pi_cycle", {})
    if pi.get("ma111"):
        print(f"\n🥧 Pi Cycle Top Indicator")
        print(f"  111d MA:     ${pi['ma111']:,.0f}")
        print(f"  350d MA × 2: ${pi['ma350x2']:,.0f}")
        print(f"  Distance:    {pi['distance_pct']:.1f}%")
        danger = "🔴 DANGER" if pi["signal"] == "cycle_top_risk" else "🟢 Safe"
        print(f"  Signal:      {danger}")

    # Fear & Greed
    fg = indicators.get("fear_greed", {})
    if fg.get("current") is not None:
        print(f"\n😱 Fear & Greed Index")
        fg_val = fg["current"]
        fg_bar_len = 20
        fg_filled = int(fg_val / 100 * fg_bar_len)
        fg_bar = "█" * fg_filled + "░" * (fg_bar_len - fg_filled)
        print(f"  Current:  {fg_val}/100 — {fg.get('classification', fg['zone'])}")
        print(f"  [{fg_bar}]")
        print(f"  30d Avg:  {fg['avg_30d']}")
        print(f"  Trend:    {fg['trend'].title()}")

    # BTC Dominance
    dom = indicators.get("btc_dominance", {})
    if dom.get("btc_dominance"):
        print(f"\n👑 Market Dominance")
        print(f"  BTC: {dom['btc_dominance']:.1f}%  |  ETH: {dom['eth_dominance']:.1f}%  |  Alts: {dom['alt_dominance']:.1f}%")
        print(f"  Signal: {dom['signal'].replace('_', ' ').title()}")

    # Altseason
    alt = indicators.get("altseason", {})
    if alt.get("index") is not None:
        period = alt.get("period", "90d")
        print(f"\n🌈 Altseason Index ({period})")
        print(f"  Score: {alt['index']:.0f}/100 ({alt['outperforming_btc']}/{alt['alts_counted']} alts beating BTC)")
        print(f"  BTC {period}: {alt['btc_change']:+.1f}%")
        print(f"  Signal:  {alt['signal'].replace('_', ' ').title()}")
        if alt.get("top_performers"):
            tops = ", ".join(f"{p['symbol'].upper()} ({p['change']:+.0f}%)" for p in alt["top_performers"])
            print(f"  Top 3:   {tops}")
        if alt.get("worst_performers"):
            bots = ", ".join(f"{p['symbol'].upper()} ({p['change']:+.0f}%)" for p in alt["worst_performers"])
            print(f"  Bottom:  {bots}")

    # Hash Rate
    hr = indicators.get("hashrate", {})
    if hr.get("current"):
        print(f"\n⛏️  BTC Hash Rate")
        print(f"  Current:    {hr['current']} {hr.get('unit', 'TH/s')}")
        print(f"  7d Change:  {hr['change_7d_pct']:+.1f}%")
        print(f"  From Peak:  {hr['from_peak_pct']:+.1f}%")
        print(f"  Signal:     {hr['signal'].replace('_', ' ').title()}")

    # Market Cap
    mcap = indicators.get("market_cap_vs_ath", {})
    if mcap.get("total_mcap_usd"):
        print(f"\n🏦 Total Market Cap")
        print(f"  Current: ${mcap['total_mcap_usd']:.0f}B")
        print(f"  vs ATH:  {mcap['pct_of_ath']:.1f}% of ${mcap['ath_reference_usd']:.0f}B")
        print(f"  Signal:  {mcap['signal'].replace('_', ' ').title()}")

    print("\n" + "=" * 60)
    print("✅ Analysis complete")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    quick = "--quick" in sys.argv
    run_analysis(quick=quick)
