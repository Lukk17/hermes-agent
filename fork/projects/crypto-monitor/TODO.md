# Crypto Monitor - TODO

## Completed ✅

### Fixed Issues
- Fear & Greed Index - FIXED
- BTC Price Graph - FIXED (header added)
- External Indices - REMOVED duplicate section
- Spot ETF Flows - FIXED (ascend-web API v2)
- Message consolidation - combined text sections, auto-split long messages
- CoinGecko /global calls - consolidated to 1 call (was 5)

---

## Pending

### 1. Whale Tracking (ChainIntel broken)
- ChainIntel returns 404 - site broken
- Replace with: Blockscout API (key now available) + Mempool (free)
- Update chainintel_collector.py or create new whale tracker

### 1b. ETH Whales - Alchemy Implementation ✅
- Created `whale_tracker_alchemy.py` using Alchemy API
- Alchemy provides deeper historical data (no 90-day limit)
- History is now everlasting - appends to whales_history.json by date
- Works with existing whale_registry.json
- Test passed: 20 ETH whales tracked successfully

### 2. API Caching ✅
- Created `cache_manager.py` - shared cache for all collectors
- `CoinGeckoCache` class provides cached access to CoinGecko API
- Added `get_daily_data()` - only calls API if today's data not in history

**Refactored collectors to use cache:**
- `coin_prices_collector.py` ✓
- `sector_collector.py` ✓
- `stablecoin_collector.py` ✓
- `defi_tvl_collector.py` ✓
- `market_breadth_collector.py` ✓

**Usage in collectors:**
```python
from collectors.cache_manager import get_daily_data

def fetch_data():
    # API call here
    return {"data": [...]}

data = get_daily_data("MyCollector", fetch_data, HISTORY_FILE)
```

**Result:**
```
[CoinPrices] ✓ Using cached data for 2026-03-30 (no API call)
[SectorCollector] ✓ Using cached data for 2026-03-30 (no API call)
[MarketBreadth] ✓ Using cached data for 2026-03-30 (no API call)
```

### 3. Combine CoinGecko /coins/markets ✅
- Added `prefetch_coingecko_data()` - fetches all data in 2-3 calls
- Pipeline runs prefetch once at start, then all collectors use cache
- Before: 5+ API calls per run | After: 2-3 API calls (first run only)
- Subsequent runs: **0 API calls** (all use cached data)

---

## Fixed Minor Issues
- matplotlib installed in venv ✅
- gas_collector.py color values fixed ✅
- dominance_chart.py now works ✅  
- daily_report.py NoneType error fixed ✅

---

## Ideas

### API Rate Limiting
- Add retry logic with backoff
- Consider queuing requests across collectors

### Data Freshness
- Track last successful fetch per data source
- Alert if data stale (>24h)
