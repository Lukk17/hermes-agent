# Crypto Monitor

Automated crypto market data collection, analysis, and Discord reporting.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAILY PIPELINE                                │
│                                                                  │
│  1. scripts/report_generator.py                                  │
│     └─→ Runs all collectors (prefetch cache first)              │
│     └─→ Runs all analyzers                                       │
│     └─→ Builds report_latest.json + charts                       │
│                                                                  │
│  2. freshness check (refuse to publish a stale report)           │
│                                                                  │
│  3. scripts/generate_summaries.py                                │
│     └─→ asks the agent for news_summary.md + market_summary.md   │
│                                                                  │
│  4. scripts/post_to_discord.py                                   │
│     └─→ assembles the fixed sequence and publishes it            │
└─────────────────────────────────────────────────────────────────┘
```

## Pipeline Flow

```
scripts/report_generator.py (main orchestrator)
    │
    ├─→ Prefetch CoinGecko data (shared cache for all collectors)
    │
    ├─→ COLLECTORS (15 scripts - fetch raw data)
    │   └─→ Saved to data/{category}/*.json
    │
    ├─→ ANALYZERS (5 scripts - process and enrich data)
    │   └─→ Saved to data/{category}/*.json
    │
    └─→ reports/daily_report.py (generates the report payload)
        └─→ data/reports/report_latest.json
        └─→ data/reports/*.png (gauges, tables)
```

## API Keys Required

### Environment Variables (via Docker Compose)

API keys are configured in Docker Compose environment:

```yaml
environment:
  - ALCHEMY_API_KEY=your_alchemy_key
  - CRYPTOPANIC_API_KEY=your_cryptopanic_key
```

Never create a `.env` file inside this project. Keys reach the container
process environment from the gitignored repo-root `.env` on the host, wired
through the `gateway.environment:` block of `docker-compose.override.yml`.
Code reads them with `os.getenv("KEY")`.

One exception matters for the pipeline. Hermes strips provider and messaging
credentials from every subprocess it spawns, so `DISCORD_BOT_TOKEN` and
`MINIMAX_API_KEY` must ALSO be present in `hermes-data/.env`, which every hermes
child loads at startup. Without that the publish step dies with
`Platform 'discord' is not configured`. Every other key in this project's list
survives the strip. Both files are gitignored.

### Free APIs (no key needed):
- CoinGecko (rate limited)
- alternative.me (Fear & Greed)
- BlockNative (ETH Gas)
- Mempool.space (BTC data)
- Blockscout (ETH data)
- Farside (ETF flows)
- Bybit (funding rates)

---

## Collectors (Data Fetching)

### CoinGecko-Based (Shared Cache)

These collectors share a common cache to minimize API calls:

| Script | Data | API Calls | Output |
|--------|------|-----------|--------|
| `coin_prices_collector.py` | Top 10 coins by market cap | 0* | `data/coin_prices/` |
| `sector_collector.py` | Sector performance | 0* | `data/sectors/` |
| `stablecoin_collector.py` | Stablecoin mcap + 7d change | 0* | `data/stablecoins/` |
| `defi_tvl_collector.py` | DeFi total market cap | 0* | `data/defi/` |
| `market_breadth_collector.py` | BTC/ETH dominance, ratios | 0* | `data/market_breadth/` |

\* First run: 3 API calls (get_markets, get_global). Subsequent runs same day: 0 calls (uses cache).

### Price & Chart Data

| Script | Data | API Calls | Output |
|--------|------|-----------|--------|
| `btc_price_chart.py` | BTC price history (1Y) | ~1 | `data/btc_price/` |
| `dominance_chart.py` | BTC dominance history | ~1 | `data/dominance/` |

### External Data

| Script | Data | API Calls | Output |
|--------|------|-----------|--------|
| `fear_greed_collector.py` | Fear & Greed Index | ~1/day | `data/fear_greed/` |
| `gas_collector.py` | ETH gas prices (Fast/Norm/Slow) | ~1/day | `data/gas/` |
| `etf_flow_collector.py` | BTC/ETH ETF flows | ~2/day | `data/etf_flows/` |
| `exchange_flow_tracker.py` | Exchange wallets flow | ~10/day | `data/exchange_flows/` |
| `funding_collector.py` | Funding rates (Bybit) | ~1/day | `data/funding/` |
| `index_scraper.py` | External indices (F&G, dominance) | ~3/day | `data/external_indices/` |

### Whale Tracking

| Script | Data | API Calls | Output |
|--------|------|-----------|--------|
| `whale_tracker_blockscout.py` | BTC + ETH whale balances | 74 (35 BTC + 39 ETH) | `data/whales/` |
| `whale_tracker_alchemy.py` | ETH whale balances | 39 ETH | `data/whales/` |
| `whale_tracker_smart.py` | Same, only if changed | 0 if stable | `data/whales/` |

### News & Social

| Script | Data | API Calls | Output |
|--------|------|-----------|--------|
| `news_collector.py` | Crypto news headlines | ~5/day | `data/news/` |
| `influencer_collector.py` | Social metrics | ~1/day | `data/influencers/` |

---

## Analyzers (Data Processing)

| Script | Function | Output |
|--------|----------|--------|
| `cycle_analyzer.py` | Cycle score (0-100), RSI, MA cross, Pi Cycle | `data/cycle/` |
| `sentiment.py` | Market sentiment analysis | `data/sentiment/` |
| `trend_detector.py` | Trend detection | `data/trends/` |
| `whale_signals.py` | Whale movement signals | `data/whale_signals/` |
| `airdrop_tracker.py` | Airdrop opportunities | `data/airdrops/` |

---

## API Calls Per Report

### First Run (Cold Cache)
| Provider | Calls |
|---------|-------|
| CoinGecko | 3-5 (prefetch + collectors) |
| alternative.me | 1 |
| BlockNative | 1 |
| Mempool.space | 35 |
| Blockscout | 39 |
| Bybit | 1 |
| Farside | 2 |
| Other | ~5 |
| **Total** | **~90 API calls** |

### Subsequent Runs Same Day
| Provider | Calls |
|---------|-------|
| CoinGecko | 0 (cached) |
| Whale trackers | 0 (if balances stable) |
| Other | ~10-15 |
| **Total** | **~15-20 API calls** |

---

## Data Storage

### History Files

Each collector saves data to `data/{category}/` folder:

```
data/
├── coin_prices/
│   ├── coin_prices_latest.json     # Current data
│   └── coin_prices_history.json    # Daily snapshots (everlasting)
├── cycle/
│   ├── cycle_latest.json           # Current cycle analysis
│   └── cycle_history.json          # Daily snapshots
├── whales/
│   ├── whales_latest.json          # Current whale balances
│   ├── whales_history.json         # Daily snapshots (everlasting)
│   └── whale_changes_latest.json   # Only changed whales
├── sectors/
│   ├── sectors_latest.json
│   └── sectors_history.json
├── stablecoins/
│   ├── stablecoins_latest.json
│   └── stablecoins_history.json     # Has snapshots for 7d+ lookback
├── _cache/                          # Shared API cache (TTL-based)
│   ├── markets_*.json
│   ├── global_*.json
│   └── simple_*.json
└── reports/
    ├── report_latest.json          # Full report data
    ├── pipeline_errors_<date>.json # Steps that failed on that run
    ├── gauge_fng.png
    ├── gauge_cycle.png
    ├── gauge_sentiment.png
    ├── trending_narratives.png
    └── coin_sentiment.png
```

`btc_dominance_2y.png`, `btc_price_2y.png` and `gas_history_1y.png` live under
`data/dominance/charts/`, `data/btc_price/` and `data/gas/charts/`
respectively, NOT under `data/reports/`.

---

## Config Files

### `config/settings.json`
API endpoints and configuration:
```json
{
  "api_endpoints": {
    "coingecko": "https://api.coingecko.com/api/v3",
    "fear_greed": "https://api.alternative.me/fng/",
    "blockscout": "https://eth.blockscout.com/api/v2",
    "alchemy": "https://eth-mainnet.g.alchemy.com/v2",
    ...
  }
}
```

### `config/whale_registry.json`
Whale wallet addresses to track:
```json
{
  "bitcoin": {
    "bc1q...": { "label": "Binance Cold", "category": "exchange" },
    ...
  },
  "ethereum": {
    "0x28c6...": { "label": "Binance", "category": "exchange" },
    ...
  }
}
```

### `config/exchange_wallets.json`
Exchange wallet addresses for flow tracking.

### `config/influencers.json`
Crypto influencer Twitter handles to track.

### `config/airdrop_opportunities.json`
Known airdrop opportunities to track.

---

## Caching Strategy

### Daily Cache (`get_daily_data()`)
- If today's data exists in history → use it (no API call)
- If not → fetch fresh data, save to history
- Key: `data/{category}/{category}_history.json`

### TTL Cache (`CoinGeckoCache`)
- Shared across all CoinGecko collectors
- TTL: 5 minutes for markets data
- Reduces redundant API calls within same pipeline run

### Prefetch
Pipeline starts with `prefetch_coingecko_data()` which calls:
1. `get_global()` - global market data
2. `get_markets(100)` - top 100 coins
3. `get_markets(10)` - top 10 coins

Then all collectors share this cache.

---

## Report Generation

### `reports/daily_report.py`
1. Loads all data from `data/*/ *_latest.json`
2. Generates text sections (indicators, prices, etc.)
3. Renders the gauge, narrative and coin-sentiment PNGs into `data/reports/`
4. Saves `report_latest.json`, which `scripts/post_to_discord.py` turns into the delivery sequence

### Market Indicators Table (10 items)
Calculated automatically:
1. BTC Dominance
2. Fear & Greed
3. Cycle Score
4. Hash Rate 7d
5. 50d/200d MA (Death/Golden Cross)
6. MA Spread % (with emoji)
7. Price/MA200 Ratio
8. Pi Cycle Top (Safe/Danger)
9. BTC RSI(14) (from CoinGecko OHLC)
10. MCap vs ATH

---

## Running the Pipeline

### Manual Run

The whole pipeline, exactly as cron runs it:

```bash
cd /opt/data/projects/crypto-monitor && ./daily_report_pipeline.sh
```

That publishes. To rebuild the data without publishing, run the first step alone:

```bash
cd /opt/data/projects/crypto-monitor && ./.venv/bin/python scripts/report_generator.py
```

Exit codes from the pipeline: `0` published, `2` bad usage or the venv Python is
missing, `3` the report generator failed, `4` the report was not rewritten this
run, `5` publishing failed, `6` the summaries could not be written.

### Cron Job

Runs daily at 10:00 UTC as job `crypto-monitor-daily`, with `no_agent: true`, so
cron runs the script and nothing else.

```bash
hermes cron list
```

`hermes cron run crypto-monitor-daily` is NOT a dry run. It fires the real job,
which publishes to Discord.

---

## File Structure

```
crypto-monitor/
├── collectors/           # 20+ data fetching scripts
├── analyzers/           # 5 data processing scripts
├── reports/             # Report generation
├── scripts/             # Pipeline orchestration
├── data/                # All collected data
│   ├── _cache/          # Shared API cache
│   ├── reports/          # Generated reports
│   └── {category}/      # Per-source data
├── config/              # Configuration files
├── pyproject.toml       # Python dependencies
└── .venv/               # Python environment (gitignored)
```

---

## Dependencies

`.venv/` is gitignored and is NOT in the image, so it must be built once per
machine before the pipeline will run at all. Without it the pipeline exits 2.

```bash
cd /opt/data/projects/crypto-monitor && uv venv .venv --python python3.11 && uv pip install --python ./.venv/bin/python -e .
```

Declared in `pyproject.toml`, installed into `.venv/`:
- matplotlib (charts)
- numpy (data processing)
- Pillow (image post-processing)
- urllib from the standard library (API calls)

`requires-python = ">=3.11,<3.12"`. The container's own hermes runtime is
Python 3.13.5; this project's `.venv/` is independent and is built against
the pyenv-provided 3.11.

---

## Troubleshooting

### Rate Limits
- CoinGecko: ~10-50 calls/minute on free tier
- If rate limited, data uses cached values or falls back

### Missing Data
Check `data/{category}/*.json` files exist and have content

### Whale Data Wrong
Ensure `whales_latest.json` (not `whale_status_latest.json`) is being written

### Report Errors
Run manually to see specific errors:
```bash
./.venv/bin/python reports/daily_report.py
```
