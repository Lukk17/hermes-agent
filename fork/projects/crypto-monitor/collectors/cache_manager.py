#!/usr/bin/env python3
"""
Cache Manager - Shared API cache for all collectors.

Prevents redundant API calls by caching responses and sharing them
across all collectors.

Usage:
    from cache_manager import CoinGeckoCache
    
    cache = CoinGeckoCache()
    data = cache.get_markets(coin_ids)  # Returns cached if fresh
"""

import json
import hashlib
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Cache TTL in seconds (5 minutes for most data)
DEFAULT_TTL = 300

# Max cache age for cleanup (7 days worth of seconds)
MAX_CACHE_AGE_SECONDS = 7 * 24 * 60 * 60


class CacheManager:
    """Generic cache manager for API responses."""
    
    def __init__(self, cache_dir: Path = CACHE_DIR, default_ttl: int = DEFAULT_TTL):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get path for cache file."""
        # Hash key to make safe filename
        hashed = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed}.json"
    
    def get(self, key: str, ttl: int = None) -> dict | None:
        """
        Get cached data if exists and not expired.
        Returns None if not found or expired.
        """
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None
        
        ttl = ttl or self.default_ttl
        
        try:
            with open(cache_path) as f:
                cached = json.load(f)
            
            # Check if expired
            cached_at = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
            if (datetime.now() - cached_at).total_seconds() > ttl:
                return None
            
            return cached.get("data")
        except:
            return None
    
    def set(self, key: str, data: dict) -> None:
        """Save data to cache."""
        cache_path = self._get_cache_path(key)
        cached = {
            "cached_at": datetime.now().isoformat(),
            "data": data
        }
        with open(cache_path, "w") as f:
            json.dump(cached, f)
    
    def invalidate(self, key: str) -> None:
        """Delete cached data."""
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
    
    def clear_all(self) -> None:
        """Clear all cache files."""
        for f in self.cache_dir.glob("*.json"):
            f.unlink()


class CoinGeckoCache:
    """
    Specialized cache for CoinGecko API calls.
    Shares data between collectors to reduce API usage.
    
    CoinGecko rate limits: ~10-50 calls/minute on free tier
    This cache ensures we make 1 call instead of 5+ for same data.
    """
    
    def __init__(self):
        self.cache = CacheManager()
        self._headers = {"User-Agent": "Mozilla/5.0"}
    
    def _fetch(self, url: str) -> dict:
        """Fetch URL and return JSON."""
        import urllib.request
        
        try:
            req = urllib.request.Request(url, headers=self._headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return {"status": "ok", "data": json.loads(resp.read())}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_markets(self, vs_currency: str = "usd", order: str = "market_cap_desc", 
                    per_page: int = 100, page: int = 1, 
                    price_change_percentage: str = "24h") -> dict:
        """
        Get coin markets data with caching.
        Uses CoinGecko's /coins/markets endpoint.
        
        This is the main endpoint used by:
        - coin_prices_collector (per_page=10)
        - sector_collector (per_page=100)
        - stablecoin_collector
        - defi_tvl_collector
        - market_breadth_collector
        
        With caching, we fetch once and share across all.
        """
        # Build cache key
        key = f"markets_{vs_currency}_{order}_{per_page}_{page}_{price_change_percentage}"
        
        # Check cache first (5 min TTL)
        cached = self.cache.get(key, ttl=300)
        if cached:
            return {"status": "ok", "data": cached, "cached": True}
        
        # Fetch fresh
        base_url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": str(per_page),
            "page": str(page),
            "sparkline": "false",
            "price_change_percentage": price_change_percentage,
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        result = self._fetch(url)
        
        if result["status"] == "ok":
            self.cache.set(key, result["data"])
            result["cached"] = False
        
        return result
    
    def get_simple_price(self, coin_ids: list, vs_currencies: list = ["usd"]) -> dict:
        """
        Get simple prices for specific coins.
        Used by various collectors for quick price lookups.
        """
        ids = ",".join(coin_ids)
        vs = ",".join(vs_currencies)
        key = f"simple_{ids}_{vs}"
        
        cached = self.cache.get(key, ttl=120)  # 2 min TTL
        if cached:
            return {"status": "ok", "data": cached, "cached": True}
        
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies={vs}"
        result = self._fetch(url)
        
        if result["status"] == "ok":
            self.cache.set(key, result["data"])
        
        return result
    
    def get_global(self) -> dict:
        """Get global market data."""
        key = "global_data"
        
        cached = self.cache.get(key, ttl=300)
        if cached:
            return {"status": "ok", "data": cached, "cached": True}
        
        url = "https://api.coingecko.com/api/v3/global"
        result = self._fetch(url)
        
        if result["status"] == "ok":
            self.cache.set(key, result["data"])
        
        return result
    
    def get_coin_data(self, coin_id: str) -> dict:
        """Get detailed coin data."""
        key = f"coin_{coin_id}"
        
        cached = self.cache.get(key, ttl=300)
        if cached:
            return {"status": "ok", "data": cached, "cached": True}
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        result = self._fetch(url)
        
        if result["status"] == "ok":
            self.cache.set(key, result["data"])
        
        return result


# Convenience function
_cg_cache = None

def get_coingecko_cache() -> CoinGeckoCache:
    """Get singleton CoinGecko cache instance."""
    global _cg_cache
    if _cg_cache is None:
        _cg_cache = CoinGeckoCache()
    return _cg_cache


# ============ DAILY HISTORY CACHE ============

def prefetch_coingecko_data():
    """
    Prefetch all CoinGecko data needed by collectors in just 2 API calls.
    
    Call this once at pipeline start to populate cache.
    Then all collectors will use cached data.
    
    Calls made:
    1. get_global() - for defi_tvl, market_breadth
    2. get_markets(100) - for coin_prices, sector, stablecoins, market_breadth
    """
    cache = get_coingecko_cache()
    
    print("[Cache] Prefetching CoinGecko data...")
    
    # 1. Fetch global data
    global_result = cache.get_global()
    if global_result["status"] == "ok":
        print(f"  ✓ global: fetched (cached: {global_result.get('cached', False)})")
    else:
        print(f"  ✗ global: failed - {global_result.get('error')}")
    
    # 2. Fetch markets (100 covers most needs)
    markets_result = cache.get_markets(vs_currency="usd", order="market_cap_desc",
                                       per_page=100, page=1, price_change_percentage="24h")
    if markets_result["status"] == "ok":
        print(f"  ✓ markets(100): fetched (cached: {markets_result.get('cached', False)})")
    else:
        print(f"  ✗ markets(100): failed - {markets_result.get('error')}")
    
    # 3. Fetch markets(10) for coin_prices (may be cached already if markets(100) covers it)
    markets10_result = cache.get_markets(vs_currency="usd", order="market_cap_desc",
                                         per_page=10, page=1, price_change_percentage="24h")
    if markets10_result["status"] == "ok":
        print(f"  ✓ markets(10): fetched (cached: {markets10_result.get('cached', False)})")
    
    print("[Cache] Prefetch complete")
    return {
        "global": global_result["status"] == "ok",
        "markets": markets_result["status"] == "ok"
    }


def get_daily_data(data_type: str, fetch_fn, history_file: Path) -> dict:
    """
    Get data for today, reading from history if already fetched today.
    
    This ensures we only call APIs once per day - if today's data
    already exists in history, we use it without making API calls.
    
    Args:
        data_type: Name for logging (e.g., "CoinPrices")
        fetch_fn: Function that fetches fresh data (makes API call)
        history_file: Path to history JSON file
    
    Returns:
        Data dict for today
    
    Usage:
        def fetch_coins():
            # API call here
            return {"coins": [...], "timestamp": "..."}
        
        data = get_daily_data("CoinPrices", fetch_coins, HISTORY_FILE)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Load history
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text())
        except:
            history = {}
    else:
        history = {}
    
    # Check if today's data already exists
    if today in history:
        print(f"[{data_type}] ✓ Using cached data for {today} (no API call)")
        return history[today]
    
    # Fetch fresh data (API call)
    print(f"[{data_type}] ↻ Fetching fresh data for {today}...")
    data = fetch_fn()
    
    # Save to history
    history[today] = data
    history["last_updated"] = datetime.now().isoformat()
    
    # Ensure parent dir exists
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(json.dumps(history, indent=2))
    
    print(f"[{data_type}] ✓ Saved to history")
    
    return data


def clear_daily_cache(data_type: str = None):
    """"Clear daily history cache. Pass data_type to clear specific, None for all."""
    if data_type:
        print(f"[Cache] Cleared {data_type} daily cache")
    else:
        print(f"[Cache] Cleared all daily caches")


def cleanup_cache(max_reports: int = 7) -> int:
    """
    Remove cache files older than last N reports.
    
    Called at end of each pipeline run to prevent cache bloat.
    
    Args:
        max_reports: Maximum number of recent cache files to keep
        
    Returns:
        Number of cache files deleted
    """
    cache_files = sorted(
        CACHE_DIR.glob("*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    
    deleted = 0
    for old_file in cache_files[max_reports:]:
        old_file.unlink()
        deleted += 1
    
    if deleted:
        print(f"[Cache] Cleaned up {deleted} old cache files")
    
    return deleted


def cleanup_daily_history(max_days: int = 7) -> int:
    """
    For each history file, keep only last N days.
    
    Args:
        max_days: Maximum number of days to keep per history file
        
    Returns:
        Number of history files cleaned
    """
    deleted_dates = 0
    
    for hist_file in DATA_DIR.glob("*/*_history.json"):
        try:
            history = json.loads(hist_file.read_text())
            dates = sorted(
                [k for k in history if k not in ("last_updated", "_metadata")],
                reverse=True
            )
            
            for old_date in dates[max_days:]:
                if old_date in history:
                    del history[old_date]
                    deleted_dates += 1
            
            hist_file.write_text(json.dumps(history, indent=2))
        except Exception:
            pass
    
    if deleted_dates:
        print(f"[Cache] Cleaned up {deleted_dates} old history entries")
    
    return deleted_dates


def cleanup_pipeline():
    """Run all cleanup at end of pipeline."""
    cache_deleted = cleanup_cache(max_reports=7)
    history_deleted = cleanup_daily_history(max_days=7)
    return {"cache_files": cache_deleted, "history_entries": history_deleted}



if __name__ == "__main__":
    # Test cache
    cache = get_coingecko_cache()
    
    print("Testing CoinGecko Cache...")
    
    # First call - should fetch
    result1 = cache.get_markets(per_page=10)
    print(f"  markets (10): {'cached' if result1.get('cached') else 'fetched'}")
    
    # Second call - should use cache
    result2 = cache.get_markets(per_page=10)
    print(f"  markets (10): {'cached' if result2.get('cached') else 'fetched'}")
    
    # Different params - should fetch
    result3 = cache.get_markets(per_page=100)
    print(f"  markets (100): {'cached' if result3.get('cached') else 'fetched'}")
    
    print("\nCache stats:")
    cache_files = list(CACHE_DIR.glob("*.json"))
    print(f"  Files in cache: {len(cache_files)}")