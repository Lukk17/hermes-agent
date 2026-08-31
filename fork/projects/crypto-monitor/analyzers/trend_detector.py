#!/usr/bin/env python3
"""
Trend Detector — Emerging narrative and category detection.

Features:
  - TF-IDF keyword extraction from news corpus
  - Category classification (DeFi, AI, L2, memes, regulation, etc.)
  - Emerging narrative detection (new/accelerating topics)
  - Cross-source trend comparison (RSS vs CryptoPanic)
  - Historical trend shift analysis
  - Coin momentum scoring

Usage:
  python3 analyzers/trend_detector.py              # Full analysis
  python3 analyzers/trend_detector.py --quick      # Quick (skip historical comparison)
  python3 analyzers/trend_detector.py --category   # Category breakdown only
"""

import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Optional: sklearn for TF-IDF
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "trends"
NEWS_DIR = BASE_DIR / "data" / "news"
SENTIMENT_DIR = BASE_DIR / "data" / "sentiment"

# ---------------------------------------------------------------------------
# Category taxonomy — maps keywords to narratives/sectors
# ---------------------------------------------------------------------------

CATEGORIES = {
    "DeFi": {
        "keywords": [
            "defi", "decentralized finance", "dex", "amm", "liquidity",
            "yield", "farming", "staking", "lending", "borrowing",
            "swap", "uniswap", "aave", "compound", "curve", "maker",
            "tvl", "total value locked", "liquidity pool", "impermanent loss",
            "flash loan", "vault", "protocol", "restaking", "eigenlayer",
            "pendle", "lido", "jito", "marinade",
        ],
        "emoji": "🏦",
    },
    "AI & Crypto": {
        "keywords": [
            "ai", "artificial intelligence", "machine learning",
            "gpt", "llm", "neural", "deep learning",
            "fetch.ai", "singularitynet", "ocean protocol",
            "render", "bittensor", "tao", "ai agent", "ai agents",
            "depin", "decentralized ai", "inference",
        ],
        "emoji": "🤖",
    },
    "Layer 2": {
        "keywords": [
            "layer 2", "l2", "rollup", "rollups", "zk-rollup", "optimistic rollup",
            "arbitrum", "optimism", "base", "zksync", "starknet",
            "polygon", "scroll", "linea", "blast", "manta", "mantle",
            "scaling", "throughput", "tps",
        ],
        "emoji": "⚡",
    },
    "Memecoins": {
        "keywords": [
            "meme", "memecoin", "memecoins", "doge", "dogecoin", "shib",
            "shiba", "pepe", "bonk", "wif", "dogwifhat", "floki",
            "pump.fun", "pumpfun", "fair launch", "presale",
            "rug", "rugpull", "moon", "100x", "1000x",
        ],
        "emoji": "🐸",
    },
    "Regulation": {
        "keywords": [
            "regulation", "regulatory", "sec", "cftc", "congress",
            "legislation", "bill", "law", "legal", "court",
            "compliance", "kyc", "aml", "sanctions",
            "ban", "crackdown", "enforcement", "subpoena",
            "gary gensler", "gensler", "elizabeth warren",
            "mica", "eu regulation", "framework",
        ],
        "emoji": "⚖️",
    },
    "ETF & Institutional": {
        "keywords": [
            "etf", "spot etf", "bitcoin etf", "ethereum etf",
            "institutional", "institution", "hedge fund",
            "blackrock", "fidelity", "grayscale", "ark invest",
            "microstrategy", "strategy", "mstr", "saylor",
            "custody", "fund", "asset manager", "wall street",
            "pension", "endowment", "sovereign wealth",
        ],
        "emoji": "🏛️",
    },
    "NFT & Gaming": {
        "keywords": [
            "nft", "nfts", "non-fungible", "opensea", "blur",
            "gaming", "gamefi", "play-to-earn", "p2e",
            "metaverse", "virtual world", "digital collectible",
            "ordinals", "inscription", "brc-20",
        ],
        "emoji": "🎮",
    },
    "Bitcoin Ecosystem": {
        "keywords": [
            "lightning", "lightning network", "taproot",
            "ordinals", "brc-20", "runes", "bitcoin l2",
            "stacks", "stx", "rgb", "bitcoin defi",
            "halving", "mining", "miner", "miners",
            "hash rate", "hashrate", "difficulty",
            "mempool", "block reward",
        ],
        "emoji": "₿",
    },
    "Stablecoins": {
        "keywords": [
            "stablecoin", "stablecoins", "usdt", "tether",
            "usdc", "circle", "dai", "frax", "ust",
            "depeg", "peg", "reserve", "backing",
            "cbdc", "digital dollar", "digital euro",
        ],
        "emoji": "💵",
    },
    "Security & Hacks": {
        "keywords": [
            "hack", "hacked", "exploit", "exploited", "vulnerability",
            "breach", "stolen", "theft", "drain", "drained",
            "phishing", "scam", "fraud", "rug pull",
            "audit", "security", "bug bounty",
            "quantum", "quantum computing",
        ],
        "emoji": "🔓",
    },
    "Macro & Economy": {
        "keywords": [
            "fed", "federal reserve", "interest rate", "rate cut",
            "inflation", "cpi", "gdp", "employment", "jobs",
            "recession", "economy", "macro", "treasury",
            "dollar", "dxy", "bond", "yield curve",
            "tariff", "tariffs", "trade war", "geopolitical",
        ],
        "emoji": "🌍",
    },
    "Airdrops & Launches": {
        "keywords": [
            "airdrop", "airdrops", "token launch", "tge",
            "testnet", "mainnet launch", "genesis",
            "points", "farming", "retroactive",
            "claim", "snapshot", "eligibility",
        ],
        "emoji": "🪂",
    },
    "RWA & Tokenization": {
        "keywords": [
            "rwa", "real world asset", "tokenization", "tokenized",
            "treasury bonds", "tokenized bonds", "ondo",
            "real estate", "commodities", "gold token",
        ],
        "emoji": "🏠",
    },
    "Privacy": {
        "keywords": [
            "privacy", "zero knowledge", "zk", "zk-proof",
            "monero", "zcash", "tornado cash", "mixer",
            "anonymous", "anonymity", "confidential",
        ],
        "emoji": "🕵️",
    },
}

# Build reverse index: keyword → category
_KEYWORD_CATEGORY = {}
for cat, info in CATEGORIES.items():
    for kw in info["keywords"]:
        _KEYWORD_CATEGORY[kw.lower()] = cat

# ---------------------------------------------------------------------------
# Stopwords for keyword extraction (crypto-aware)
# ---------------------------------------------------------------------------

STOPWORDS = {
    # Standard English
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "must",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those", "what", "which", "who", "whom",
    "where", "when", "why", "how", "all", "each", "every", "both",
    "few", "more", "most", "other", "some", "such", "no", "not",
    "only", "own", "same", "so", "than", "too", "very",
    "and", "but", "or", "nor", "for", "yet", "with", "about",
    "against", "between", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "in", "out",
    "on", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "just", "also", "now", "new", "says", "said",
    "according", "report", "reports", "amid", "per", "via",
    "still", "even", "much", "many", "well", "back", "get", "got",
    "make", "made", "take", "took", "come", "came", "see", "seen",
    "know", "known", "think", "thought", "look", "like", "want",
    "give", "use", "find", "tell", "ask", "work", "call", "try",
    "need", "become", "leave", "put", "mean", "keep", "let", "begin",
    "seem", "help", "show", "hear", "play", "run", "move", "live",
    "as", "at", "of", "by", "if", "go", "do", "an", "be", "we",
    "it", "am", "so", "us", "no", "he", "or", "re", "vs",
    "its", "set", "big", "old", "low", "top", "end", "key", "way",
    "bit", "add", "eye", "eyes", "full", "half", "high", "long",
    "goes", "into", "over", "says", "data", "five", "four", "week",
    "will", "hits", "after", "before", "while", "since", "until",
    "amid", "near", "between", "despite",
    # Crypto-generic (too common to be meaningful)
    "crypto", "cryptocurrency", "token", "coin", "market", "price",
    "trading", "trader", "traders", "trade", "trades",
    "blockchain", "network", "platform", "project",
    "million", "billion", "trillion",
    "says", "could", "may", "week", "today", "year", "day",
    "first", "last", "next", "two", "three", "one",
}

# ---------------------------------------------------------------------------
# Text processing
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Clean and normalize text for analysis."""
    text = text.lower().strip()
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[^\w\s-]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_tokens(text: str) -> list:
    """Extract meaningful tokens (unigrams + bigrams)."""
    text = clean_text(text)
    words = text.split()
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]

    # Add bigrams
    bigrams = []
    for i in range(len(words) - 1):
        bigrams.append(f"{words[i]} {words[i+1]}")

    return words + bigrams


# ---------------------------------------------------------------------------
# TF-IDF keyword extraction
# ---------------------------------------------------------------------------

def extract_keywords_tfidf(articles: list, top_n: int = 40) -> list:
    """Extract top keywords using TF-IDF."""
    if not HAS_SKLEARN or not articles:
        return extract_keywords_frequency(articles, top_n)

    # Build corpus from titles + descriptions
    corpus = []
    for a in articles:
        text = f"{a.get('title', '')} {a.get('description', '')}"
        corpus.append(clean_text(text))

    if not corpus:
        return []

    vectorizer = TfidfVectorizer(
        max_features=200,
        stop_words=list(STOPWORDS),
        ngram_range=(1, 3),
        min_df=2,            # must appear in at least 2 docs
        max_df=0.8,          # ignore if in 80%+ of docs (too common)
        token_pattern=r'(?u)\b[a-z][a-z0-9]+\b',
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        return extract_keywords_frequency(articles, top_n)

    feature_names = vectorizer.get_feature_names_out()

    # Sum TF-IDF scores across all documents per term
    scores = tfidf_matrix.sum(axis=0).A1
    ranked = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)

    results = []
    for term, score in ranked[:top_n]:
        # Count how many articles mention this term
        doc_count = sum(1 for doc in corpus if term in doc)
        results.append({
            "term": term,
            "tfidf_score": round(float(score), 4),
            "doc_count": doc_count,
            "doc_pct": round(doc_count / len(corpus) * 100, 1),
        })

    return results


def extract_keywords_frequency(articles: list, top_n: int = 40) -> list:
    """Fallback: extract keywords by frequency (no sklearn)."""
    counter = Counter()
    total_docs = len(articles)

    for a in articles:
        text = f"{a.get('title', '')} {a.get('description', '')}"
        tokens = set(extract_tokens(text))  # unique per doc
        counter.update(tokens)

    results = []
    for term, count in counter.most_common(top_n * 2):
        if count < 2:
            break
        results.append({
            "term": term,
            "tfidf_score": round(count / total_docs, 4),
            "doc_count": count,
            "doc_pct": round(count / total_docs * 100, 1),
        })

    return results[:top_n]


# ---------------------------------------------------------------------------
# Category classification
# ---------------------------------------------------------------------------

def classify_article(article: dict) -> list:
    """Classify article into categories."""
    text = f"{article.get('title', '')} {article.get('description', '')}".lower()
    matches = {}

    for cat, info in CATEGORIES.items():
        score = 0
        matched_kws = []
        for kw in info["keywords"]:
            if len(kw) <= 3:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, text):
                    score += 1
                    matched_kws.append(kw)
            else:
                if kw in text:
                    score += 1
                    matched_kws.append(kw)

        if score > 0:
            matches[cat] = {
                "score": score,
                "keywords": matched_kws,
            }

    return sorted(matches.items(), key=lambda x: x[1]["score"], reverse=True)


def aggregate_categories(articles: list) -> dict:
    """Aggregate category counts across all articles."""
    cat_data = defaultdict(lambda: {
        "count": 0,
        "articles": [],
        "keyword_hits": Counter(),
    })

    uncategorized = 0

    for a in articles:
        cats = classify_article(a)
        if not cats:
            uncategorized += 1
            continue

        for cat_name, match_info in cats:
            cd = cat_data[cat_name]
            cd["count"] += 1
            cd["articles"].append({
                "title": a.get("title", "")[:80],
                "source": a.get("blog") or a.get("source", "?"),
                "matched": match_info["keywords"],
            })
            for kw in match_info["keywords"]:
                cd["keyword_hits"][kw] += 1

    # Sort by count
    result = {}
    for cat in sorted(cat_data, key=lambda c: cat_data[c]["count"], reverse=True):
        cd = cat_data[cat]
        info = CATEGORIES[cat]
        top_kws = cd["keyword_hits"].most_common(5)
        result[cat] = {
            "emoji": info["emoji"],
            "count": cd["count"],
            "pct": round(cd["count"] / len(articles) * 100, 1),
            "top_keywords": [{"term": k, "count": c} for k, c in top_kws],
            "sample_titles": [a["title"] for a in cd["articles"][:3]],
        }

    result["_uncategorized"] = uncategorized
    return result


# ---------------------------------------------------------------------------
# Emerging narrative detection
# ---------------------------------------------------------------------------

def detect_emerging(current_keywords: list, historical: list) -> list:
    """Detect emerging narratives by comparing current vs historical keywords."""
    if not historical:
        # No history — mark high-frequency current terms as "new"
        return [{
            "term": kw["term"],
            "current_score": kw["tfidf_score"],
            "velocity": "new",
            "signal": "first_seen",
        } for kw in current_keywords[:15]]

    # Build historical average scores
    hist_scores = defaultdict(list)
    for snapshot in historical:
        for kw in snapshot.get("keywords", []):
            hist_scores[kw["term"]].append(kw.get("tfidf_score", 0))

    hist_avg = {t: sum(s) / len(s) for t, s in hist_scores.items()}

    emerging = []
    for kw in current_keywords:
        term = kw["term"]
        current = kw["tfidf_score"]
        previous = hist_avg.get(term)

        if previous is None:
            # Completely new term
            if current > 0.05:
                emerging.append({
                    "term": term,
                    "current_score": current,
                    "previous_avg": 0,
                    "velocity": "new",
                    "signal": "🆕 first_seen",
                })
        elif previous > 0:
            change = (current - previous) / previous
            if change > 0.5:
                emerging.append({
                    "term": term,
                    "current_score": current,
                    "previous_avg": round(previous, 4),
                    "change_pct": round(change * 100, 1),
                    "velocity": "accelerating",
                    "signal": "🔥 accelerating",
                })

    # Sort by novelty/acceleration
    emerging.sort(key=lambda x: x.get("current_score", 0), reverse=True)
    return emerging[:20]


# ---------------------------------------------------------------------------
# Cross-source comparison
# ---------------------------------------------------------------------------

def compare_sources(articles: list) -> dict:
    """Compare trending topics across different sources."""
    source_articles = defaultdict(list)
    for a in articles:
        source = a.get("blog") or a.get("source", "unknown")
        # Group into broad source types
        if source in ("blogwatcher",):
            for blog in ["Cointelegraph", "CoinDesk", "Decrypt", "Bitcoin Magazine"]:
                if a.get("blog") == blog:
                    source_articles[blog].append(a)
                    break
            else:
                source_articles["RSS"].append(a)
        elif source == "cryptopanic":
            source_articles["CryptoPanic"].append(a)
        else:
            source_articles[source].append(a)

    result = {}
    for source, arts in source_articles.items():
        if len(arts) < 3:
            continue

        cats = aggregate_categories(arts)
        top_cats = [(k, v) for k, v in cats.items() if k != "_uncategorized"][:3]

        kws = extract_keywords_tfidf(arts, top_n=10)
        top_kws = [k["term"] for k in kws[:5]]

        result[source] = {
            "article_count": len(arts),
            "top_categories": [{
                "name": c,
                "emoji": d["emoji"],
                "count": d["count"],
            } for c, d in top_cats],
            "top_keywords": top_kws,
        }

    return result


# ---------------------------------------------------------------------------
# Coin momentum (which coins are getting the most attention)
# ---------------------------------------------------------------------------

# Reuse coin aliases from sentiment analyzer
COIN_ALIASES = {
    "BTC": ["bitcoin", "btc"], "ETH": ["ethereum", "eth", "ether"],
    "SOL": ["solana", "sol"], "BNB": ["binance", "bnb"],
    "XRP": ["xrp", "ripple"], "ADA": ["cardano", "ada"],
    "AVAX": ["avalanche", "avax"], "DOT": ["polkadot", "dot"],
    "LINK": ["chainlink", "link"], "DOGE": ["dogecoin", "doge"],
    "MATIC": ["polygon", "matic"], "ARB": ["arbitrum", "arb"],
    "OP": ["optimism"], "SUI": ["sui"], "APT": ["aptos"],
    "INJ": ["injective"], "STX": ["stacks"],
    "PEPE": ["pepe"], "WIF": ["dogwifhat", "wif"],
    "BONK": ["bonk"], "SHIB": ["shiba", "shib"],
    "RENDER": ["render", "rndr"], "TAO": ["bittensor", "tao"],
    "FET": ["fetch.ai", "artificial superintelligence"],
}

_COIN_LOOKUP = {}
for sym, aliases in COIN_ALIASES.items():
    for a in aliases:
        _COIN_LOOKUP[a.lower()] = sym
    _COIN_LOOKUP[sym.lower()] = sym


def compute_coin_momentum(articles: list) -> dict:
    """Calculate mention momentum per coin."""
    mentions = Counter()

    for a in articles:
        text = f"{a.get('title', '')} {a.get('description', '')}".lower()
        found = set()
        for alias, symbol in _COIN_LOOKUP.items():
            if len(alias) <= 3:
                if re.search(r'\b' + re.escape(alias) + r'\b', text):
                    found.add(symbol)
            else:
                if alias in text:
                    found.add(symbol)
        for coin in found:
            mentions[coin] += 1

    total = len(articles)
    result = {}
    for coin, count in mentions.most_common(20):
        result[coin] = {
            "mentions": count,
            "pct": round(count / total * 100, 1),
            "intensity": "🔥" if count / total > 0.3 else "📊" if count / total > 0.1 else "📎",
        }

    return result


# ---------------------------------------------------------------------------
# Historical
# ---------------------------------------------------------------------------

def load_historical_trends(days: int = 7) -> list:
    """Load past trend snapshots."""
    if not DATA_DIR.exists():
        return []

    files = sorted(DATA_DIR.glob("trends_*.json"), reverse=True)
    history = []

    for f in files[:days * 4]:
        try:
            with open(f) as fh:
                data = json.load(fh)
                history.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    return history


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: dict):
    """Print formatted trend report."""
    categories = result.get("categories", {})
    keywords = result.get("keywords", [])
    emerging = result.get("emerging", [])
    coin_momentum = result.get("coin_momentum", {})
    sources = result.get("source_comparison", {})

    print("\n" + "=" * 60)
    print("🔍 TREND DETECTION REPORT")
    print(f"📅 {result.get('timestamp', 'N/A')}")
    engine = "TF-IDF (sklearn)" if HAS_SKLEARN else "Frequency (fallback)"
    print(f"⚙️  Keyword engine: {engine}")
    print("=" * 60)

    # Category breakdown
    if categories:
        uncat = categories.pop("_uncategorized", 0)
        print(f"\n📂 NARRATIVE CATEGORIES")
        print(f"{'─' * 60}")

        for cat, data in categories.items():
            emoji = data["emoji"]
            count = data["count"]
            pct = data["pct"]
            bar_len = min(20, max(1, int(pct / 5)))
            bar = "█" * bar_len

            print(f"  {emoji} {cat:<22} {count:>3} articles ({pct:>4.1f}%) {bar}")

            if data.get("top_keywords"):
                kw_str = ", ".join(f"{k['term']}({k['count']})" for k in data["top_keywords"][:3])
                print(f"     Top terms: {kw_str}")

        if uncat:
            print(f"  ❓ Uncategorized          {uncat:>3} articles")

    # Top keywords (TF-IDF)
    if keywords:
        print(f"\n🔑 TOP KEYWORDS (TF-IDF)")
        print(f"{'─' * 60}")
        print(f"  {'TERM':<30} {'SCORE':>7} {'DOCS':>5} {'%':>6}")

        for kw in keywords[:20]:
            print(f"  {kw['term']:<30} {kw['tfidf_score']:>7.4f} {kw['doc_count']:>5} {kw['doc_pct']:>5.1f}%")

    # Emerging narratives
    if emerging:
        print(f"\n🆕 EMERGING NARRATIVES")
        print(f"{'─' * 60}")

        for e in emerging[:10]:
            signal = e.get("signal", "?")
            term = e["term"]
            score = e["current_score"]
            prev = e.get("previous_avg", 0)
            change = e.get("change_pct", "")
            change_str = f" (+{change}%)" if change else ""

            print(f"  {signal} {term:<28} score: {score:.4f}{change_str}")

    # Coin momentum
    if coin_momentum:
        print(f"\n💰 COIN MENTION MOMENTUM")
        print(f"{'─' * 60}")
        print(f"  {'COIN':<8} {'MENTIONS':>9} {'%':>6} {'HEAT'}")

        for coin, data in coin_momentum.items():
            print(f"  {coin:<8} {data['mentions']:>8} {data['pct']:>5.1f}% {data['intensity']}")

    # Source comparison
    if sources:
        print(f"\n📡 SOURCE COMPARISON")
        print(f"{'─' * 60}")

        for source, data in sources.items():
            cats = ", ".join(
                f"{c['emoji']}{c['name']}({c['count']})"
                for c in data.get("top_categories", [])
            )
            kws = ", ".join(data.get("top_keywords", [])[:4])
            print(f"  {source} ({data['article_count']} articles)")
            if cats:
                print(f"    Categories: {cats}")
            if kws:
                print(f"    Keywords:   {kws}")

    print("\n" + "=" * 60)
    print("✅ Trend detection complete")
    print("=" * 60)


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


def run_analysis(quick: bool = False, category_only: bool = False) -> dict:
    """Run full trend detection analysis."""
    print("=" * 60)
    print("🔍 TREND DETECTOR")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    # 1. Load news
    print("\n📰 Loading news data...")
    articles = load_news()
    if not articles:
        return {}

    # 2. Category classification
    print(f"\n📂 Classifying into categories...")
    categories = aggregate_categories(articles)

    if category_only:
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "categories": categories,
            "article_count": len(articles),
        }
        save_result(result)
        print_report(result)
        return result

    # 3. Keyword extraction (TF-IDF)
    print(f"\n🔑 Extracting keywords...")
    keywords = extract_keywords_tfidf(articles, top_n=40)

    # 4. Coin momentum
    print(f"\n💰 Computing coin momentum...")
    coin_momentum = compute_coin_momentum(articles)

    # 5. Source comparison
    print(f"\n📡 Comparing sources...")
    sources = compare_sources(articles)

    # 6. Emerging narrative detection
    emerging = []
    if not quick:
        print(f"\n🆕 Detecting emerging narratives...")
        history = load_historical_trends()
        emerging = detect_emerging(keywords, history)

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "article_count": len(articles),
        "categories": categories,
        "keywords": keywords,
        "emerging": emerging,
        "coin_momentum": coin_momentum,
        "source_comparison": sources,
    }

    save_result(result)
    print_report(result)
    return result


def save_result(result: dict):
    """Save analysis result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Trim article lists in categories for storage
    save_data = json.loads(json.dumps(result))
    for cat, data in save_data.get("categories", {}).items():
        if isinstance(data, dict) and "sample_titles" in data:
            data["sample_titles"] = data["sample_titles"][:3]
    
    # Write latest
    latest = DATA_DIR / "trends_latest.json"
    with open(latest, "w") as f:
        json.dump(save_data, f, indent=2)
    
    # Update history
    history_file = DATA_DIR / "trends_history.json"
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
    category_only = "--category" in sys.argv
    run_analysis(quick=quick, category_only=category_only)
