#!/usr/bin/env python3
"""
Sentiment Analyzer — Crypto-specific NLP sentiment analysis.

Features:
  - Weighted lexicon scoring (crypto-tuned)
  - Negation detection (flips polarity)
  - Intensity modifiers (amplify/dampen)
  - Per-coin sentiment aggregation
  - Historical sentiment tracking
  - Price correlation analysis
  - Market-wide sentiment index

No external dependencies — pure Python.

Usage:
  python3 analyzers/sentiment.py              # Full analysis
  python3 analyzers/sentiment.py --quick      # Quick (latest data only, no correlation)
  python3 analyzers/sentiment.py --coin BTC   # Single coin deep dive
"""

import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Optional: VADER for general-purpose sentiment baseline
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = SentimentIntensityAnalyzer()
    HAS_VADER = True
except ImportError:
    _VADER = None
    HAS_VADER = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "sentiment"
NEWS_DIR = BASE_DIR / "data" / "news"
PRICES_DIR = BASE_DIR / "data" / "prices"
CYCLE_DIR = BASE_DIR / "data" / "cycle"

# ---------------------------------------------------------------------------
# Coin recognition — maps mentions to canonical symbols
# ---------------------------------------------------------------------------

COIN_ALIASES = {
    "BTC": ["bitcoin", "btc", "₿", "sats", "satoshi"],
    "ETH": ["ethereum", "eth", "ether", "vitalik"],
    "SOL": ["solana", "sol"],
    "BNB": ["binance coin", "bnb", "binance"],
    "XRP": ["xrp", "ripple"],
    "ADA": ["cardano", "ada"],
    "AVAX": ["avalanche", "avax"],
    "DOT": ["polkadot", "dot"],
    "LINK": ["chainlink", "link"],
    "DOGE": ["dogecoin", "doge"],
    "MATIC": ["polygon", "matic", "pol"],
    "ATOM": ["cosmos", "atom"],
    "UNI": ["uniswap", "uni"],
    "ARB": ["arbitrum", "arb"],
    "OP": ["optimism"],
    "SUI": ["sui"],
    "APT": ["aptos", "apt"],
    "SEI": ["sei"],
    "TIA": ["celestia", "tia"],
    "JUP": ["jupiter", "jup"],
    "PEPE": ["pepe"],
    "WIF": ["dogwifhat", "wif"],
    "BONK": ["bonk"],
    "SHIB": ["shiba", "shib"],
    "FET": ["fetch.ai", "fet", "artificial superintelligence"],
    "RENDER": ["render", "rndr"],
    "TAO": ["bittensor", "tao"],
    "INJ": ["injective", "inj"],
    "STX": ["stacks", "stx"],
    "DOT": ["polkadot", "dot"],
}

# Reverse lookup: alias → symbol
_ALIAS_MAP = {}
for symbol, aliases in COIN_ALIASES.items():
    for alias in aliases:
        _ALIAS_MAP[alias.lower()] = symbol
    _ALIAS_MAP[symbol.lower()] = symbol


# CoinGecko ID → symbol mapping
COINGECKO_MAP = {
    "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL",
    "binancecoin": "BNB", "ripple": "XRP", "cardano": "ADA",
    "avalanche-2": "AVAX", "polkadot": "DOT", "chainlink": "LINK",
    "dogecoin": "DOGE",
}

# ---------------------------------------------------------------------------
# Sentiment lexicon — weighted scores (-1.0 to +1.0)
# ---------------------------------------------------------------------------

# Positive (bullish)
BULLISH_LEXICON = {
    # Strong bullish (+0.7 to +1.0)
    "surge": 0.8, "surges": 0.8, "surging": 0.8,
    "soar": 0.9, "soars": 0.9, "soaring": 0.9,
    "skyrocket": 1.0, "skyrockets": 1.0,
    "moon": 0.9, "mooning": 0.9,
    "all-time high": 1.0, "ath": 1.0, "record high": 1.0, "new high": 0.9,
    "breakout": 0.8, "breakthrough": 0.8, "breaks out": 0.8,
    "parabolic": 0.9,
    "euphoria": 0.7,

    # Medium bullish (+0.4 to +0.7)
    "rally": 0.7, "rallies": 0.7, "rallying": 0.7,
    "pump": 0.6, "pumping": 0.6, "pumps": 0.6,
    "bull": 0.6, "bullish": 0.7,
    "gain": 0.5, "gains": 0.5, "gaining": 0.5,
    "recovery": 0.5, "recovers": 0.5, "recovering": 0.5,
    "rebound": 0.6, "rebounds": 0.6, "bounces": 0.5,
    "jump": 0.5, "jumps": 0.5, "jumping": 0.5,
    "climb": 0.5, "climbs": 0.5, "climbing": 0.5,
    "rise": 0.5, "rises": 0.5, "rising": 0.5,
    "outperform": 0.6, "outperforms": 0.6,
    "upgrade": 0.5,

    # Mild bullish (+0.2 to +0.4)
    "buy": 0.4, "buying": 0.4, "accumulate": 0.4, "accumulation": 0.4,
    "adopt": 0.3, "adoption": 0.4,
    "approve": 0.5, "approved": 0.6, "approval": 0.5,
    "etf approved": 0.9, "spot etf": 0.6,
    "institutional": 0.4, "institution": 0.3,
    "inflow": 0.5, "inflows": 0.5,
    "partnership": 0.4, "integration": 0.3,
    "launch": 0.3, "launches": 0.3, "mainnet": 0.4,
    "upgrade": 0.3, "upgrades": 0.3,
    "support": 0.2, "holds": 0.2,
    "buy the dip": 0.5,
    "strong": 0.3, "strength": 0.3,
    "growth": 0.4, "growing": 0.3,
    "positive": 0.3, "optimistic": 0.4, "optimism": 0.4,
    "milestone": 0.4,
    "win": 0.4, "winning": 0.4, "wins": 0.4,
    "beat": 0.4, "beats": 0.4, "exceeds": 0.4,
    "record": 0.3,
}

# Negative (bearish)
BEARISH_LEXICON = {
    # Strong bearish (-0.7 to -1.0)
    "crash": -0.9, "crashes": -0.9, "crashing": -0.9,
    "collapse": -1.0, "collapses": -1.0,
    "plunge": -0.8, "plunges": -0.8, "plunging": -0.8,
    "tank": -0.8, "tanks": -0.8, "tanking": -0.8,
    "capitulation": -0.9, "capitulate": -0.9,
    "liquidation": -0.8, "liquidated": -0.8, "liquidations": -0.8,
    "rug": -1.0, "rugpull": -1.0, "rug pull": -1.0, "rugged": -1.0,
    "hack": -0.9, "hacked": -0.9, "exploit": -0.8, "exploited": -0.8,
    "scam": -1.0, "fraud": -1.0, "ponzi": -1.0,
    "dead": -0.8, "death cross": -0.7,

    # Medium bearish (-0.4 to -0.7)
    "dump": -0.7, "dumps": -0.7, "dumping": -0.7,
    "bear": -0.6, "bearish": -0.7,
    "sell": -0.4, "selling": -0.5, "selloff": -0.7, "sell-off": -0.7,
    "decline": -0.5, "declines": -0.5, "declining": -0.5,
    "drop": -0.5, "drops": -0.5, "dropping": -0.5,
    "sink": -0.6, "sinks": -0.6, "sinking": -0.6,
    "fall": -0.5, "falls": -0.5, "falling": -0.5,
    "plummet": -0.8, "plummets": -0.8,
    "fear": -0.5, "fud": -0.6, "panic": -0.7,
    "outflow": -0.5, "outflows": -0.5,
    "downgrade": -0.5, "underperform": -0.5,
    "bubble": -0.5,
    "lost": -0.4, "loss": -0.4, "losses": -0.5,
    "dip": -0.3, "dips": -0.3,

    # Mild bearish (-0.2 to -0.4)
    "sec": -0.3, "lawsuit": -0.5, "sued": -0.5,
    "ban": -0.6, "banned": -0.6, "crackdown": -0.5,
    "regulation": -0.2, "regulatory": -0.2,
    "warning": -0.4, "warns": -0.4,
    "risk": -0.3, "risky": -0.3,
    "withdraw": -0.3, "withdrawals": -0.3,
    "concern": -0.3, "concerns": -0.3, "worried": -0.3,
    "delay": -0.3, "delayed": -0.3,
    "struggle": -0.4, "struggles": -0.4, "struggling": -0.4,
    "weak": -0.3, "weakness": -0.3,
    "uncertain": -0.3, "uncertainty": -0.3,
    "volatile": -0.2, "volatility": -0.2,
    "down": -0.2,
}

# Combine into one dict
LEXICON = {}
LEXICON.update(BULLISH_LEXICON)
LEXICON.update(BEARISH_LEXICON)

# ---------------------------------------------------------------------------
# Negation & intensity modifiers
# ---------------------------------------------------------------------------

NEGATION_WORDS = {
    "not", "no", "never", "neither", "nor", "nobody", "nothing",
    "nowhere", "hardly", "barely", "scarcely", "don't", "doesn't",
    "didn't", "isn't", "wasn't", "aren't", "weren't", "won't",
    "wouldn't", "shouldn't", "couldn't", "can't", "cannot",
    "without", "despite", "fails", "failed", "unlikely",
}

AMPLIFIERS = {
    "very": 1.3, "extremely": 1.5, "incredibly": 1.5,
    "massive": 1.4, "huge": 1.3, "major": 1.2,
    "significant": 1.2, "substantially": 1.3,
    "dramatically": 1.4, "sharply": 1.3,
    "absolutely": 1.4, "completely": 1.3,
    "record": 1.2, "historic": 1.3,
    "unprecedented": 1.4,
}

DAMPENERS = {
    "slightly": 0.6, "somewhat": 0.7, "marginally": 0.5,
    "barely": 0.4, "little": 0.5, "small": 0.6,
    "minor": 0.5, "modest": 0.6,
    "could": 0.7, "may": 0.7, "might": 0.6,
    "possibly": 0.6, "potentially": 0.7,
}


# ---------------------------------------------------------------------------
# Tokenizer & scoring engine
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list:
    """Simple word tokenizer."""
    text = text.lower().strip()
    # Keep hyphens in compound words, split rest
    tokens = re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*|[₿$%]", text)
    return tokens


def score_text_crypto(text: str) -> dict:
    """Score text using crypto-specific lexicon with negation + intensity.

    Returns:
        compound: normalized score (-1.0 to +1.0)
        positive: sum of positive scores
        negative: sum of negative scores (absolute)
        signals: list of matched terms with scores
    """
    tokens = tokenize(text)
    if not tokens:
        return {"compound": 0.0, "positive": 0.0, "negative": 0.0, "signals": []}

    signals = []
    pos_sum = 0.0
    neg_sum = 0.0

    seen_terms = set()
    for i, token in enumerate(tokens):
        # Check trigram first, then bigram, then unigram
        score = None
        matched_term = None

        if i + 2 < len(tokens):
            trigram = f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}"
            if trigram in LEXICON and trigram not in seen_terms:
                score = LEXICON[trigram]
                matched_term = trigram
                seen_terms.add(trigram)

        if score is None and i + 1 < len(tokens):
            bigram = f"{tokens[i]} {tokens[i+1]}"
            if bigram in LEXICON and bigram not in seen_terms:
                score = LEXICON[bigram]
                matched_term = bigram
                seen_terms.add(bigram)

        if score is None:
            if token in LEXICON and token not in seen_terms:
                score = LEXICON[token]
                matched_term = token
                seen_terms.add(token)

        if score is None:
            continue

        # Check for negation in preceding 3 words
        negated = False
        start = max(0, i - 3)
        for j in range(start, i):
            if tokens[j] in NEGATION_WORDS:
                negated = True
                break

        if negated:
            score *= -0.75  # flip and slightly dampen

        # Check for intensity modifiers in preceding 2 words
        modifier = 1.0
        start = max(0, i - 2)
        for j in range(start, i):
            if tokens[j] in AMPLIFIERS:
                modifier = AMPLIFIERS[tokens[j]]
                break
            elif tokens[j] in DAMPENERS:
                modifier = DAMPENERS[tokens[j]]
                break

        score *= modifier

        if score > 0:
            pos_sum += score
        else:
            neg_sum += abs(score)

        signals.append({
            "term": matched_term,
            "raw_score": round(score, 3),
            "negated": negated,
            "modifier": modifier,
        })

    # Normalize compound score to [-1, 1] using VADER-style normalization
    raw = pos_sum - neg_sum
    alpha = 15  # normalization constant
    compound = raw / math.sqrt(raw * raw + alpha)

    return {
        "compound": round(compound, 4),
        "positive": round(pos_sum, 3),
        "negative": round(neg_sum, 3),
        "signals": signals,
    }


def score_text_vader(text: str) -> dict:
    """Score text using VADER (general-purpose English sentiment)."""
    if not HAS_VADER:
        return {"compound": 0.0, "positive": 0.0, "negative": 0.0}

    vs = _VADER.polarity_scores(text)
    return {
        "compound": vs["compound"],
        "positive": vs["pos"],
        "negative": vs["neg"],
    }


def score_text(text: str) -> dict:
    """Combined sentiment scoring: crypto lexicon (60%) + VADER (40%).

    VADER handles general English sentiment well but misses crypto jargon.
    Our lexicon catches domain terms but can miss nuanced phrasing.
    Combining both gives the best of both worlds.

    Returns:
        compound: blended normalized score (-1.0 to +1.0)
        positive/negative: from crypto lexicon
        signals: matched crypto terms
        vader: VADER scores (if available)
        engine: which engines contributed
    """
    crypto = score_text_crypto(text)

    if HAS_VADER:
        vader = score_text_vader(text)

        # Weighted blend: crypto 60%, VADER 40%
        # Crypto lexicon gets more weight because it knows domain terms
        blended = crypto["compound"] * 0.6 + vader["compound"] * 0.4

        return {
            "compound": round(blended, 4),
            "positive": crypto["positive"],
            "negative": crypto["negative"],
            "signals": crypto["signals"],
            "vader": {
                "compound": round(vader["compound"], 4),
                "positive": round(vader["positive"], 3),
                "negative": round(vader["negative"], 3),
            },
            "engine": "crypto+vader",
        }
    else:
        crypto["engine"] = "crypto_only"
        return crypto


def classify_score(compound: float) -> str:
    """Classify compound score into sentiment label."""
    if compound >= 0.3:
        return "bullish"
    elif compound >= 0.1:
        return "slightly_bullish"
    elif compound > -0.1:
        return "neutral"
    elif compound > -0.3:
        return "slightly_bearish"
    else:
        return "bearish"


# ---------------------------------------------------------------------------
# Coin mention detection
# ---------------------------------------------------------------------------

def detect_coins(text: str) -> list:
    """Detect which coins are mentioned in text."""
    text_lower = text.lower()
    found = set()

    # Check all aliases
    for alias, symbol in _ALIAS_MAP.items():
        # Use word boundary matching for short aliases
        if len(alias) <= 4:
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, text_lower):
                found.add(symbol)
        else:
            if alias in text_lower:
                found.add(symbol)

    return sorted(found)


# ---------------------------------------------------------------------------
# Article analysis
# ---------------------------------------------------------------------------

def analyze_article(article: dict) -> dict:
    """Analyze a single article's sentiment."""
    title = article.get("title", "")
    desc = article.get("description", "")

    # Score title (weighted heavier) and description
    title_score = score_text(title)
    desc_score = score_text(desc) if desc else {"compound": 0.0, "positive": 0.0, "negative": 0.0, "signals": []}

    # Weighted combination: title 70%, description 30%
    if desc:
        compound = title_score["compound"] * 0.7 + desc_score["compound"] * 0.3
    else:
        compound = title_score["compound"]

    # Detect mentioned coins
    full_text = f"{title} {desc}"
    coins = detect_coins(full_text)

    # If CryptoPanic pre-tagged, boost confidence in that direction
    cp_sentiment = article.get("cryptopanic_sentiment")
    if cp_sentiment:
        cp_boost = 0.3 if cp_sentiment == "bullish" else -0.3 if cp_sentiment == "bearish" else 0.0
        compound = compound * 0.6 + cp_boost * 0.4

    label = classify_score(compound)

    return {
        "article_id": article.get("id", "?"),
        "title": title[:100],
        "source": article.get("blog") or article.get("source", "?"),
        "published": article.get("published", ""),
        "compound": round(compound, 4),
        "label": label,
        "coins": coins,
        "title_signals": title_score["signals"],
        "desc_signals": desc_score["signals"],
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_by_coin(analyses: list) -> dict:
    """Aggregate sentiment scores per coin."""
    coin_data = defaultdict(lambda: {
        "scores": [],
        "bullish": 0,
        "bearish": 0,
        "neutral": 0,
        "article_count": 0,
        "articles": [],
    })

    for a in analyses:
        coins = a.get("coins", [])
        if not coins:
            coins = ["MARKET"]  # general market news

        for coin in coins:
            cd = coin_data[coin]
            cd["scores"].append(a["compound"])
            cd["article_count"] += 1

            if a["label"] in ("bullish", "slightly_bullish"):
                cd["bullish"] += 1
            elif a["label"] in ("bearish", "slightly_bearish"):
                cd["bearish"] += 1
            else:
                cd["neutral"] += 1

            cd["articles"].append({
                "title": a["title"][:80],
                "compound": a["compound"],
                "label": a["label"],
                "source": a["source"],
            })

    # Calculate aggregates
    result = {}
    for coin, data in coin_data.items():
        scores = data["scores"]
        avg = sum(scores) / len(scores) if scores else 0

        # Sentiment ratio
        total = data["bullish"] + data["bearish"] + data["neutral"]
        bull_pct = (data["bullish"] / total * 100) if total else 0
        bear_pct = (data["bearish"] / total * 100) if total else 0

        # Overall label for coin
        if avg >= 0.2:
            overall = "bullish"
        elif avg >= 0.05:
            overall = "slightly_bullish"
        elif avg > -0.05:
            overall = "neutral"
        elif avg > -0.2:
            overall = "slightly_bearish"
        else:
            overall = "bearish"

        result[coin] = {
            "avg_score": round(avg, 4),
            "overall": overall,
            "article_count": data["article_count"],
            "bullish": data["bullish"],
            "bearish": data["bearish"],
            "neutral": data["neutral"],
            "bull_pct": round(bull_pct, 1),
            "bear_pct": round(bear_pct, 1),
            "strongest": max(scores) if scores else 0,
            "weakest": min(scores) if scores else 0,
            "top_articles": sorted(
                data["articles"],
                key=lambda x: abs(x["compound"]),
                reverse=True
            )[:5],
        }

    return dict(sorted(result.items(), key=lambda x: x[1]["article_count"], reverse=True))


def compute_market_sentiment(coin_sentiments: dict, analyses: list) -> dict:
    """Compute overall market sentiment index."""
    if not analyses:
        return {"index": 50, "label": "neutral", "signal": "no_data"}

    all_scores = [a["compound"] for a in analyses]
    avg = sum(all_scores) / len(all_scores)

    bullish = sum(1 for a in analyses if a["label"] in ("bullish", "slightly_bullish"))
    bearish = sum(1 for a in analyses if a["label"] in ("bearish", "slightly_bearish"))
    neutral = sum(1 for a in analyses if a["label"] == "neutral")
    total = len(analyses)

    # Market sentiment index: 0-100 (like Fear & Greed but from news)
    # Map compound [-1, 1] to [0, 100]
    index = round((avg + 1) * 50, 1)
    index = max(0, min(100, index))

    if index >= 70:
        label = "very_bullish"
        emoji = "🟢🟢"
    elif index >= 58:
        label = "bullish"
        emoji = "🟢"
    elif index >= 45:
        label = "neutral"
        emoji = "⚪"
    elif index >= 32:
        label = "bearish"
        emoji = "🔴"
    else:
        label = "very_bearish"
        emoji = "🔴🔴"

    return {
        "index": index,
        "avg_compound": round(avg, 4),
        "label": label,
        "emoji": emoji,
        "total_articles": total,
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
        "bull_ratio": round(bullish / total * 100, 1) if total else 0,
        "bear_ratio": round(bearish / total * 100, 1) if total else 0,
    }


# ---------------------------------------------------------------------------
# Price correlation
# ---------------------------------------------------------------------------

def load_price_data() -> Optional[dict]:
    """Load latest price data."""
    latest = PRICES_DIR / "prices_latest.json"
    if not latest.exists():
        return None
    with open(latest) as f:
        data = json.load(f)
    return data.get("data", {})


def correlate_with_prices(coin_sentiments: dict) -> dict:
    """Compare sentiment with recent price movements."""
    prices = load_price_data()
    if not prices:
        return {}

    correlations = {}
    symbol_to_gecko = {v: k for k, v in COINGECKO_MAP.items()}

    for symbol, sentiment in coin_sentiments.items():
        if symbol == "MARKET":
            continue

        gecko_id = symbol_to_gecko.get(symbol)
        if not gecko_id or gecko_id not in prices:
            continue

        price_data = prices[gecko_id]
        price_usd = price_data.get("usd", 0)
        change_24h = price_data.get("usd_24h_change")

        if change_24h is None:
            continue

        sent_score = sentiment["avg_score"]

        # Check alignment: positive sentiment + positive price = aligned
        sent_direction = "positive" if sent_score > 0.05 else "negative" if sent_score < -0.05 else "neutral"
        price_direction = "positive" if change_24h > 1 else "negative" if change_24h < -1 else "neutral"

        if sent_direction == price_direction:
            alignment = "aligned"
        elif sent_direction == "neutral" or price_direction == "neutral":
            alignment = "neutral"
        else:
            alignment = "divergent"  # potential signal

        correlations[symbol] = {
            "price_usd": price_usd,
            "price_change_24h": round(change_24h, 2),
            "sentiment_score": sent_score,
            "sentiment_label": sentiment["overall"],
            "price_direction": price_direction,
            "sent_direction": sent_direction,
            "alignment": alignment,
        }

    return correlations


# ---------------------------------------------------------------------------
# Historical tracking
# ---------------------------------------------------------------------------

def load_historical_sentiments(days: int = 7) -> list:
    """Load past sentiment snapshots."""
    if not DATA_DIR.exists():
        return []

    files = sorted(DATA_DIR.glob("sentiment_*.json"), reverse=True)
    history = []

    for f in files[:days * 6]:  # ~6 snapshots per day max
        try:
            with open(f) as fh:
                data = json.load(fh)
                history.append({
                    "timestamp": data.get("timestamp"),
                    "market_sentiment": data.get("market_sentiment", {}),
                    "file": f.name,
                })
        except (json.JSONDecodeError, KeyError):
            continue

    return history


def compute_sentiment_trend(history: list) -> dict:
    """Analyze sentiment trend from historical data."""
    if len(history) < 2:
        return {"trend": "insufficient_data", "samples": len(history)}

    indices = [h["market_sentiment"].get("index", 50) for h in history if h.get("market_sentiment")]

    if not indices:
        return {"trend": "no_data", "samples": 0}

    current = indices[0]
    avg = sum(indices) / len(indices)

    # Split into halves
    mid = len(indices) // 2
    if mid > 0:
        recent_avg = sum(indices[:mid]) / mid
        older_avg = sum(indices[mid:]) / len(indices[mid:])
        change = recent_avg - older_avg

        if change > 5:
            trend = "improving"
        elif change > 2:
            trend = "slightly_improving"
        elif change > -2:
            trend = "stable"
        elif change > -5:
            trend = "slightly_worsening"
        else:
            trend = "worsening"
    else:
        trend = "stable"
        change = 0

    return {
        "trend": trend,
        "current": current,
        "average": round(avg, 1),
        "change": round(change, 1),
        "samples": len(indices),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: dict):
    """Print formatted sentiment report."""
    market = result.get("market_sentiment", {})
    coins = result.get("coin_sentiments", {})
    correlations = result.get("correlations", {})
    trend = result.get("trend", {})

    print("\n" + "=" * 60)
    print("🧠 SENTIMENT ANALYSIS REPORT")
    print(f"📅 {result.get('timestamp', 'N/A')}")
    print("=" * 60)

    # Market sentiment index
    if market:
        idx = market.get("index", 50)
        bar_len = 30
        filled = int(idx / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)

        print(f"\n{market.get('emoji', '⚪')} Market Sentiment Index: {idx}/100 — {market['label'].upper().replace('_', ' ')}")
        print(f"[{bar}]")
        print(f"  Articles analyzed: {market.get('total_articles', 0)}")
        print(f"  🟢 Bullish: {market.get('bullish', 0)} ({market.get('bull_ratio', 0):.0f}%)")
        print(f"  🔴 Bearish: {market.get('bearish', 0)} ({market.get('bear_ratio', 0):.0f}%)")
        print(f"  ⚪ Neutral: {market.get('neutral', 0)}")

    # Trend
    if trend and trend.get("trend") != "insufficient_data":
        trend_emoji = {
            "improving": "📈", "slightly_improving": "↗️",
            "stable": "➡️",
            "slightly_worsening": "↘️", "worsening": "📉",
        }.get(trend["trend"], "❓")
        print(f"\n  Trend: {trend_emoji} {trend['trend'].replace('_', ' ').title()} "
              f"(avg: {trend.get('average', '?')}, Δ: {trend.get('change', '?'):+.1f}, "
              f"{trend.get('samples', 0)} samples)")

    # Per-coin sentiment
    if coins:
        print(f"\n{'─' * 60}")
        print(f"{'COIN':<10} {'SCORE':>7} {'LABEL':<18} {'BULL':>5} {'BEAR':>5} {'#':>4}")
        print(f"{'─' * 60}")

        for coin, data in coins.items():
            if coin == "MARKET":
                continue
            score = data["avg_score"]
            label = data["overall"]
            bull = data["bullish"]
            bear = data["bearish"]
            count = data["article_count"]

            emoji = "🟢" if score > 0.1 else "🔴" if score < -0.1 else "⚪"
            print(f"  {emoji} {coin:<7} {score:>+.4f}  {label:<18} {bull:>4} {bear:>5} {count:>4}")

        # General market articles
        if "MARKET" in coins:
            m = coins["MARKET"]
            print(f"  ⚪ {'GENERAL':<7} {m['avg_score']:>+.4f}  {m['overall']:<18} "
                  f"{m['bullish']:>4} {m['bearish']:>5} {m['article_count']:>4}")

    # Price correlation
    if correlations:
        print(f"\n{'─' * 60}")
        print("📊 Sentiment vs Price (24h)")
        print(f"{'─' * 60}")
        print(f"  {'COIN':<7} {'SENT':>8} {'PRICE':>10} {'24H':>8} {'ALIGNMENT':<12}")

        for coin, corr in correlations.items():
            sent = corr["sentiment_score"]
            price = corr["price_usd"]
            change = corr["price_change_24h"]
            alignment = corr["alignment"]

            align_emoji = "✅" if alignment == "aligned" else "⚠️" if alignment == "divergent" else "➖"

            price_str = f"${price:,.0f}" if price > 100 else f"${price:.2f}"
            print(f"  {coin:<7} {sent:>+.4f} {price_str:>10} {change:>+.1f}% {align_emoji} {alignment}")

        # Divergent signals (potential opportunities)
        divergent = {k: v for k, v in correlations.items() if v["alignment"] == "divergent"}
        if divergent:
            print(f"\n  ⚠️  Divergent signals (sentiment ≠ price):")
            for coin, corr in divergent.items():
                if corr["sent_direction"] == "positive":
                    print(f"    {coin}: Bullish sentiment but price down → potential buy signal?")
                else:
                    print(f"    {coin}: Bearish sentiment but price up → potential sell signal?")

    # Top bullish/bearish articles
    all_articles = []
    for coin, data in coins.items():
        all_articles.extend(data.get("top_articles", []))

    if all_articles:
        # Deduplicate
        seen = set()
        unique = []
        for a in all_articles:
            key = a["title"][:50]
            if key not in seen:
                seen.add(key)
                unique.append(a)

        most_bullish = sorted(unique, key=lambda x: x["compound"], reverse=True)[:5]
        most_bearish = sorted(unique, key=lambda x: x["compound"])[:5]

        if most_bullish and most_bullish[0]["compound"] > 0:
            print(f"\n{'─' * 60}")
            print("🟢 Most Bullish Headlines")
            for a in most_bullish:
                if a["compound"] <= 0:
                    break
                print(f"  {a['compound']:>+.3f} [{a['source'][:10]:<10}] {a['title'][:55]}...")

        if most_bearish and most_bearish[0]["compound"] < 0:
            print(f"\n🔴 Most Bearish Headlines")
            for a in most_bearish:
                if a["compound"] >= 0:
                    break
                print(f"  {a['compound']:>+.3f} [{a['source'][:10]:<10}] {a['title'][:55]}...")

    print("\n" + "=" * 60)
    print("✅ Sentiment analysis complete")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Deep dive for single coin
# ---------------------------------------------------------------------------

def coin_deep_dive(symbol: str, analyses: list) -> dict:
    """Deep dive into a single coin's sentiment."""
    symbol = symbol.upper()
    coin_articles = [a for a in analyses if symbol in a.get("coins", [])]

    if not coin_articles:
        print(f"⚠️  No articles found mentioning {symbol}")
        return {}

    print(f"\n{'=' * 60}")
    print(f"🔍 DEEP DIVE: {symbol}")
    print(f"{'=' * 60}")
    print(f"  Articles: {len(coin_articles)}")

    scores = [a["compound"] for a in coin_articles]
    avg = sum(scores) / len(scores)
    label = classify_score(avg)

    bullish = [a for a in coin_articles if a["label"] in ("bullish", "slightly_bullish")]
    bearish = [a for a in coin_articles if a["label"] in ("bearish", "slightly_bearish")]

    print(f"  Avg Score: {avg:+.4f} ({label})")
    print(f"  Bullish: {len(bullish)} | Bearish: {len(bearish)}")
    print(f"  Range: {min(scores):+.4f} to {max(scores):+.4f}")

    print(f"\n  All articles:")
    for a in sorted(coin_articles, key=lambda x: x["compound"], reverse=True):
        emoji = "🟢" if a["compound"] > 0.1 else "🔴" if a["compound"] < -0.1 else "⚪"
        print(f"    {emoji} {a['compound']:>+.4f} [{a['source'][:10]:<10}] {a['title'][:50]}...")
        if a.get("title_signals"):
            terms = ", ".join(s["term"] for s in a["title_signals"][:3])
            print(f"             Signals: {terms}")

    return {
        "symbol": symbol,
        "article_count": len(coin_articles),
        "avg_score": round(avg, 4),
        "label": label,
        "bullish": len(bullish),
        "bearish": len(bearish),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_news() -> list:
    """Load latest news articles."""
    latest = NEWS_DIR / "news_latest.json"
    if not latest.exists():
        print("⚠️  No news data found. Run news_collector.py first.")
        return []

    with open(latest) as f:
        data = json.load(f)

    articles = data.get("articles", [])
    print(f"  Loaded {len(articles)} articles from news_latest.json")
    print(f"  News timestamp: {data.get('timestamp', 'N/A')}")
    return articles


def run_analysis(quick: bool = False, coin: str = None) -> dict:
    """Run full sentiment analysis."""
    print("=" * 60)
    print("🧠 SENTIMENT ANALYZER")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    engine = "Crypto Lexicon + VADER" if HAS_VADER else "Crypto Lexicon (VADER not installed)"
    print(f"⚙️  Engine: {engine}")
    print("=" * 60)

    # 1. Load news data
    print("\n📰 Loading news data...")
    articles = load_news()
    if not articles:
        return {}

    # 2. Analyze each article
    print(f"\n🔍 Analyzing {len(articles)} articles...")
    analyses = [analyze_article(a) for a in articles]

    # 3. Single coin deep dive
    if coin:
        return coin_deep_dive(coin, analyses)

    # 4. Aggregate by coin
    print("\n📊 Aggregating by coin...")
    coin_sentiments = aggregate_by_coin(analyses)

    # 5. Market-wide sentiment
    market_sentiment = compute_market_sentiment(coin_sentiments, analyses)

    # 6. Price correlation
    correlations = {}
    if not quick:
        print("\n💰 Correlating with prices...")
        correlations = correlate_with_prices(coin_sentiments)

    # 7. Historical trend
    trend = {}
    if not quick:
        print("\n📈 Checking historical trend...")
        history = load_historical_sentiments()
        trend = compute_sentiment_trend(history)

    # Build result
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "market_sentiment": market_sentiment,
        "coin_sentiments": coin_sentiments,
        "correlations": correlations,
        "trend": trend,
        "article_count": len(analyses),
    }

    # Save
    save_result(result)

    # Display
    print_report(result)

    return result


def save_result(result: dict):
    """Save analysis result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Trim articles from coin_sentiments for saved file (keep top 3 per coin)
    save_data = json.loads(json.dumps(result))
    for coin, data in save_data.get("coin_sentiments", {}).items():
        if "top_articles" in data:
            data["top_articles"] = data["top_articles"][:3]
    
    # Write latest
    latest = DATA_DIR / "sentiment_latest.json"
    with open(latest, "w") as f:
        json.dump(save_data, f, indent=2)
    
    # Update history
    history_file = DATA_DIR / "sentiment_history.json"
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    quick = "--quick" in sys.argv
    coin = None

    for i, arg in enumerate(sys.argv):
        if arg == "--coin" and i + 1 < len(sys.argv):
            coin = sys.argv[i + 1]

    run_analysis(quick=quick, coin=coin)
