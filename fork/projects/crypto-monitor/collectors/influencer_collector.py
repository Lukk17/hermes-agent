#!/usr/bin/env python3
"""
Influencer Collector v2
Tracks crypto influencer activity from:
1. RSS feeds (blogs, news)
2. On-chain (known wallets - exchanges, VCs, notable)

Provides: coin mentions, topic analysis, wallet activity
"""

import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
SETTINGS_FILE = PROJECT_ROOT / "config" / "settings.json"

DATA_DIR = PROJECT_ROOT / "data" / "influencers"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load config
def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return {}

SETTINGS = load_settings()
API_ENDPOINTS = SETTINGS.get("api_endpoints", {})

CONFIG_FILE = PROJECT_ROOT / "config" / "influencers.json"

# Keywords for topic extraction
TOPIC_KEYWORDS = {
    "ETF": ["etf", "spot etf", "bitcoin etf", "eth etf"],
    "Institutional": ["institutional", "blackrock", "fidelity", "wall street", "treasury"],
    "DeFi": ["defi", "lending", "borrowing", "uniswap", "aave", "compound"],
    "L2": ["layer 2", "l2", "arbitrum", "optimism", "base", "polygon", "matic"],
    "RWA": ["rwa", "real world", "tokenization", "treasury"],
    "AI": ["ai", "artificial intelligence", "neural", "machine learning"],
    "Meme": ["meme", "dogecoin", "shib", "pepe", "wif", "bonk"],
    "Regulation": ["sec", "regulation", "lawsuit", "ban", "crackdown"],
    "Mining": ["mining", "hashrate", "reward", "halving"],
    "Staking": ["staking", "liquid staking", "eth2", "pos"]
}

COIN_KEYWORDS = [
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT", "LINK", "DOGE",
    "MATIC", "ARB", "OP", "ATOM", "UNI", "AAVE", "MKR", "CRV", "LDO", "NEAR",
    "SUI", "APT", "PEPE", "SHIB", "WIF", "INJ", "IMX", "REND", "RNDR", "GRT",
    "FIL", "ALGO", "STX", "AKT", "POL", "TRUMP", "MELANIA"
]


class InfluencerCollector:
    def __init__(self):
        self.results = {}
        self._headers = {"User-Agent": "Mozilla/5.0"}
        self.wallets = {}
        self.blogs = []
        self.news = []
        self._load_config()
    
    def _load_config(self):
        """Load config."""
        if not CONFIG_FILE.exists():
            print(f"[InfluencerCollector] Config not found")
            return
        
        try:
            data = json.loads(CONFIG_FILE.read_text())
            
            # Load blogs
            for b in data.get("sources", {}).get("blogs", []):
                self.blogs.append(b)
            
            # Load news
            for n in data.get("sources", {}).get("news_rss", []):
                self.news.append(n)
            
            # Load wallets by category
            wallets = data.get("wallets", {})
            for category, entries in wallets.items():
                for name, info in entries.items():
                    addr = info.get("address", "").lower()
                    if addr:
                        self.wallets[addr] = {
                            "name": info.get("name", name),
                            "category": category,
                            "display_name": name
                        }
            
            print(f"[InfluencerCollector] Loaded {len(self.blogs)} blogs, {len(self.news)} news, {len(self.wallets)} wallets")
        except Exception as e:
            print(f"[InfluencerCollector] Config error: {e}")
    
    def _fetch_rss(self, url: str) -> list:
        """Fetch RSS feed."""
        try:
            req = urllib.request.Request(url, headers=self._headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode()
            
            posts = []
            try:
                root = ElementTree.fromstring(data)
                for item in root.findall(".//item")[:10]:
                    title = item.find("title")
                    desc = item.find("description")
                    posts.append({
                        "title": title.text if title is not None else "",
                        "description": desc.text if desc is not None else ""
                    })
            except:
                pass
            return posts
        except:
            return []
    
    def _extract_coins(self, text: str) -> list:
        """Extract coin mentions."""
        text = re.sub(r'<[^>]+>', ' ', text)  # Strip HTML
        coins = set()
        for coin in COIN_KEYWORDS:
            if re.search(r'\b' + coin + r'\b', text, re.IGNORECASE):
                coins.add(coin)
        return list(coins)
    
    def _extract_topics(self, text: str) -> list:
        """Extract topics/themes."""
        text = re.sub(r'<[^>]+>', ' ', text).lower()
        topics = set()
        for topic, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    topics.add(topic)
                    break
        return list(topics)
    
    def _track_wallet(self, addr: str, info: dict) -> dict:
        """Track single wallet via Blockscout."""
        try:
            base_url = API_ENDPOINTS.get("blockscout", "https://eth.blockscout.com/api/v2")
            url = f"{base_url}/addresses/{addr}/transactions?limit=5"
            req = urllib.request.Request(url, headers=self._headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                items = data.get("items", [])
                
                if not items:
                    return None
                
                # Calculate recent activity
                in_count = sum(1 for t in items if t.get("to") == addr.lower())
                out_count = len(items) - in_count
                
                return {
                    "name": info.get("display_name"),
                    "category": info.get("category"),
                    "tx_count": len(items),
                    "incoming": in_count,
                    "outgoing": out_count,
                    "direction": "accumulating" if in_count > out_count else "distributing"
                }
        except:
            return None
    
    def fetch_all(self):
        """Fetch all data."""
        print("[InfluencerCollector] Fetching...")
        
        all_posts = []
        coin_mentions = {}
        topic_counts = {}
        
        # Fetch blogs
        for source in self.blogs:
            posts = self._fetch_rss(source.get("url", ""))
            for p in posts:
                p["source"] = source.get("name", "unknown")
                p["type"] = "blog"
                all_posts.append(p)
                
                text = (p.get("title", "") + " " + p.get("description", ""))
                for coin in self._extract_coins(text):
                    coin_mentions[coin] = coin_mentions.get(coin, 0) + 1
                for topic in self._extract_topics(text):
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Fetch news
        for source in self.news:
            posts = self._fetch_rss(source.get("url", ""))
            for p in posts:
                p["source"] = source.get("name", "unknown")
                p["type"] = "news"
                all_posts.append(p)
                
                text = (p.get("title", "") + " " + p.get("description", ""))
                for coin in self._extract_coins(text):
                    coin_mentions[coin] = coin_mentions.get(coin, 0) + 1
                for topic in self._extract_topics(text):
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Track wallets (sample first 3 due to API limits)
        wallet_activity = []
        for addr, info in list(self.wallets.items())[:5]:
            result = self._track_wallet(addr, info)
            if result:
                wallet_activity.append(result)
        
        # Calculate percentages
        total = sum(coin_mentions.values())
        coin_pct = {}
        for coin, count in coin_mentions.items():
            coin_pct[coin] = {"count": count, "pct": round(count/total*100, 1) if total else 0}
        
        total_topics = sum(topic_counts.values())
        topic_pct = {}
        for topic, count in topic_counts.items():
            topic_pct[topic] = {"count": count, "pct": round(count/total_topics*100, 1) if total_topics else 0}
        
        # Sort
        sorted_coins = sorted(coin_pct.items(), key=lambda x: x[1]["count"], reverse=True)
        sorted_topics = sorted(topic_pct.items(), key=lambda x: x[1]["count"], reverse=True)
        
        self.results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "posts": all_posts[:30],
            "coins": dict(sorted_coins[:10]),
            "topics": dict(sorted_topics[:8]),
            "wallet_activity": wallet_activity,
        }
        
        print(f"  Posts: {len(all_posts)}")
        print(f"  Coins: {coin_pct}")
        print(f"  Topics: {topic_pct}")
        print(f"  Wallets tracked: {len(wallet_activity)}")
        
        self._save()
        return self.results
    
    def _save(self):
        """Save to JSON."""
        # Write latest
        with open(DATA_DIR / "influencers_latest.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Update history
        history_file = DATA_DIR / "influencers_history.json"
        today = datetime.now().strftime("%Y-%m-%d")
        
        if history_file.exists():
            history = json.loads(history_file.read_text())
        else:
            history = {}
        
        # Use date as key (overwrites if exists)
        history[today] = self.results
        
        history["last_updated"] = datetime.now().isoformat()
        
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
        
        print(f"[InfluencerCollector] Saved")


if __name__ == "__main__":
    collector = InfluencerCollector()
    collector.fetch_all()
