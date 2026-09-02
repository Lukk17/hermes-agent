# Crypto Monitor Architecture

## Project Overview

Automated cryptocurrency monitoring system that generates daily reports and publishes them to Discord.

---

## Data Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  CoinGecko API          → Collectors (current data)                       │
│  Yahoo Finance          → One-time scripts (historical data)               │
│  External APIs           → Various collectors (whale alerts, etc)          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COLLECTORS (data/*_latest.json)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Each collector fetches current data and saves to:                        │
│    - <folder>_latest.json  (most recent snapshot)                         │
│    - <folder>_history.json (historical by date key)                      │
│                                                                             │
│  Rate limiting: Most use CoinGecko free API (limited calls)               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ANALYZERS                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Process collector data, generate insights:                                 │
│    - cycle_analyzer.py    → cycle_latest.json                            │
│    - sentiment.py          → sentiment_latest.json                         │
│    - trend_detector.py    → trends_latest.json                            │
│    - whale_signals.py     → whale_signals_latest.json                    │
│    - airdrop_tracker.py   → airdrops_latest.json                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        REPORTS                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  daily_report.py     → Reads all *_latest.json, creates report_latest.json│
│                                                                             │
│  External-process seam: services/agent_bridge.py                           │
│    Bridges from our Python into OUTSIDE systems only. No Python-library     │
│    wrappers (requests/urllib/subprocess are called directly by the file    │
│    that needs them; do not add wrappers here).                             │
│                                                                             │
│    post_to_discord() / publish_daily_report()                               │
│      └─> writes data/reports/discord_outbox.json                          │
│                                                                             │
│  Host-side cron then runs:                                                  │
│    scripts/post_to_discord.py                                              │
│      └─> consumes outbox, calls `hermes send` per chunk                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## One-Time Scripts (Important!)

These scripts populate historical data needed for charts. Run once or when repopulating history.

### populate_price_history.py
- **Source:** Yahoo Finance (no rate limits)
- **Output:** `data/prices/prices_history.json` (btc_prices key)
- **Data:** ~732 days (2 years) of BTC prices
- **Usage:** Run once to populate history, then btc_price_chart.py handles daily updates

### populate_dominance_history.py
- **Source:** Yahoo Finance (no rate limits)
- **Output:** `data/dominance/dominance_history.json`
- **Data:** ~732 days (2 years) of BTC/ETH dominance (calculated from price ratio)
- **Usage:** Run once to populate history, then dominance_chart.py handles daily updates

**Why these scripts exist:**
- CoinGecko free API limits historical data to 365 days
- Yahoo Finance provides 2 years of data
- Running these once populates full history, then daily scripts only fetch current price (1 API call)

---

## Data Files Structure

### data/*/ (Collected Data)

| Folder | Latest File | History File | Source | Used By |
|--------|-------------|--------------|--------|---------|
| airdrops | airdrops_latest.json | airdrops_history.json | airdrop_tracker.py | daily_report.py |
| chainintel | chainintel_latest.json | chainintel_history.json | chainintel_collector.py | daily_report.py |
| cycle | cycle_latest.json | cycle_history.json | cycle_analyzer.py | daily_report.py |
| defi | defi_latest.json | defi_history.json | defi_tvl_collector.py | daily_report.py |
| dominance | dominance_latest.json | dominance_history.json | dominance_chart.py | daily_report.py |
| etf_flows | etf_flows_latest.json | etf_flows_history.json | etf_flow_collector.py | daily_report.py |
| exchange_flows | exchange_flows_latest.json | exchange_flows_history.json | exchange_flow_tracker.py | daily_report.py |
| external_indices | external_indices_latest.json | external_indices_history.json | index_scraper.py | daily_report.py |
| funding | funding_latest.json | funding_history.json | funding_collector.py | **NOT USED** - Bybit API broken |
| gas | gas_latest.json | gas_history.json | gas_collector.py | daily_report.py |
| influencers | influencers_latest.json | influencers_history.json | influencer_collector.py | daily_report.py |
| market_breadth | market_breadth_latest.json | market_breadth_history.json | market_breadth_collector.py | daily_report.py |
| news | news_latest.json | news_history.json | news_collector.py | daily_report.py |
| prices | prices_latest.json | prices_history.json | btc_price_chart.py | daily_report.py |
| sectors | sectors_latest.json | sectors_history.json | sector_collector.py | daily_report.py |
| sentiment | sentiment_latest.json | sentiment_history.json | sentiment.py | daily_report.py |
| stablecoins | stablecoins_latest.json | stablecoins_history.json | stablecoin_collector.py | daily_report.py |
| trends | trends_latest.json | trends_history.json | trend_detector.py | daily_report.py |
| whale_alerts | whale_alerts_latest.json | whale_alerts_history.json | whale_alert_collector.py | daily_report.py |
| whale_signals | whale_signals_latest.json | whale_signals_history.json | whale_signals.py | daily_report.py |
| whales | whales_latest.json | whales_history.json | whale_discovery.py | daily_report.py |

### data/reports/ (Generated Output)

| File | Generated By | Description |
|------|--------------|-------------|
| report_latest.json | daily_report.py | Full report data with placeholders |
| discord_outbox.json | services.external.post_to_discord | Queued Discord chunks (consumed by host-side poster) |
| news_summary.md | Agent | AI-generated news summary |
| market_summary.md | Agent | AI-generated market summary |
| *.png (charts) | charts.py, dominance_chart.py, btc_price_chart.py | Various charts |

The OpenClaw-era `discord_messages.json` artifact is gone. The seam writes
`discord_outbox.json` directly via `services.external.post_to_discord(...)`.

### Charts Directory

| Chart | Generated By | Source Data |
|-------|--------------|-------------|
| btc_dominance_2y.png | dominance_chart.py | dominance_history.json |
| btc_price_2y.png | btc_price_chart.py | prices_history.json |
| gauge_fng.png | charts.py | fear_greed from external_indices |
| gauge_cycle.png | charts.py | cycle data |
| gauge_sentiment.png | charts.py | sentiment data |
| table_*.png | charts.py | Various tables |

---

## Script Inventory

### collectors/ (16 scripts)

| Script | Creates | API Source |
|--------|---------|------------|
| btc_price_chart.py | prices_latest.json, btc_price_2y.png | CoinGecko (current), Yahoo (populate) |
| dominance_chart.py | dominance_latest.json, btc_dominance_2y.png | CoinGecko (current), Yahoo (populate) |
| chainintel_collector.py | chainintel_latest.json | chainintel.io |
| defi_tvl_collector.py | defi_latest.json | CoinGecko |
| etf_flow_collector.py | etf_flows_latest.json | Farside Investors |
| exchange_flow_tracker.py | exchange_flows_latest.json | Blockscout |
| funding_collector.py | funding_latest.json | **NOT USED** - Bybit API broken |
| gas_collector.py | gas_latest.json | Etherscan |
| influencer_collector.py | influencers_latest.json | RSS feeds |
| index_scraper.py | external_indices_latest.json | alternative.me, CoinGecko |
| market_breadth_collector.py | market_breadth_latest.json | CoinGecko |
| sector_collector.py | sectors_latest.json | CoinGecko |
| stablecoin_collector.py | stablecoins_latest.json | CoinGecko |
| whale_alert_collector.py | whale_alerts_latest.json | WhaleAlert API |
| whale_discovery.py | whales_latest.json | Blockscout |

**Note:** Some collectors are called in report_generator.py but files don't exist:
- price_fetcher.py (not needed - prices come from btc_price_chart.py)
- news_collector.py (not needed - news comes from other sources)
- whale_tracker.py (not needed - whales come from whale_discovery.py)

**Active collectors (called in pipeline):**
- market_breadth_collector.py - IS USED, working (report_generator.py line 65)

### analyzers/ (5 scripts)

| Script | Creates | Input |
|--------|---------|-------|
| airdrop_tracker.py | airdrops_latest.json | Manual/API |
| cycle_analyzer.py | cycle_latest.json | Prices, Fear & Greed |
| sentiment.py | sentiment_latest.json | News data |
| trend_detector.py | trends_latest.json | News data |
| whale_signals.py | whale_signals_latest.json | Whale data, prices |

### scripts/ (2 scripts)

| Script | Purpose |
|--------|---------|
| report_generator.py | Runs all collectors/analyzers via services.external.run_step, creates report_latest.json |
| post_to_discord.py | Host-side poster: reads discord_outbox.json, forwards via `hermes send` |

### One-Time Scripts

| Script | Purpose |
|--------|---------|
| populate_price_history.py | Populates 2 years BTC history from Yahoo Finance |
| populate_dominance_history.py | Populates 2 years dominance history from Yahoo Finance |

---

## History File Format

All history files use the same format:

```json
{
  "2026-02-25": { ...data... },
  "2026-02-26": { ...data... },
  "last_updated": "2026-02-26T10:00:00"
}
```

- Keys are dates in `YYYY-MM-DD` format
- Each date key contains that day's data
- `last_updated` tracks when file was modified
- Scripts overwrite if same date exists (no duplicates)

---

## Configuration Files

| File | Purpose |
|------|---------|
| .env | API keys (CRYPTOPANIC_API_KEY, WHALE_ALERT_API_KEY, etc) |
| config/settings.json | Main configuration (API endpoints, thresholds, chart settings, external links) |
| config/influencers.json | Influencer RSS sources and wallet addresses |
| config/whale_registry.json | Known whale addresses |
| config/exchange_wallets.json | Exchange wallet addresses for flow tracking |

---

## Report Generation Flow

### 1. Cron triggers at 10:00 Warsaw
```
Cron → Agent → AGENT.md instructions
```

### 2. Run pipeline
```
report_generator.py
  ├── Collectors (16 scripts) → data/*_latest.json
  ├── Analyzers (5 scripts) → data/*_latest.json  
  └── daily_report.py → data/reports/report_latest.json
```

### 3. Agent generates summaries
```
Agent reads AGENT.md
  ├── Reads news_latest.json → news_summary.md
  └── Reads report data → market_summary.md
```

### 4. Publish to Discord
```
Agent (or local dev)
  └── services.agent_bridge.publish_daily_report(report_latest.json)
        └── post_to_discord() → data/reports/discord_outbox.json

Cron (host)
  └── scripts/post_to_discord.py
        └── consumes outbox → `hermes send --to discord:<id>:<channel>` per chunk
```

`agent_bridge` contains ONLY calls that cross out of our Python process
into external systems (currently: the Discord gateway via outbox +
host-side poster). Do NOT add Python-library wrappers there - call
`requests`, `urllib.request`, `subprocess`, etc. directly from the file
that needs them.

The OpenClaw-era `publish_pipeline.sh` / `discord_messages_generator.py`
/ `publish_report.py` are gone. The OpenClaw-era
`data/reports/discord_messages.json` artifact is also gone - the seam
writes `discord_outbox.json` directly.

---

## Message Sequence (Discord)

1. Header: # 📊 Daily Crypto Report
2. Timestamp
3. Fear & Greed gauge
4. Cycle gauge
5. Sentiment gauge
6. Prices table
7. Top Movers
8. Trending Narratives
9. Coin Sentiment
10. Market Indicators
11. BTC Dominance chart
12. Crypto Sectors
13. ETH Gas (text)
14. Market Breadth (text)
15. Spot ETF Flows (text)
16. Stablecoin Supply (text)
17. ~~Funding Rates (text)~~ - REMOVED (API broken)
18. Exchange Holdings
19. Whale Activity
20. Airdrops
21. Airdrop links
22. Market Summary
23. Quick Links

---

## API Sources

| Service | Used By | Purpose |
|---------|---------|---------|
| CoinGecko | Most collectors | Crypto prices, market data |
| Yahoo Finance | populate_* scripts | Historical data (2 years) |
| Blockscout | exchange_flow_tracker, whale_discovery | On-chain data |
| WhaleAlert API | whale_alert_collector | Large transactions |
| Alternative.me | index_scraper | Fear & Greed index |
| Farside Investors | etf_flow_collector | ETF flow data |
| RSS Feeds | influencer_collector | News/blogs |

---

## Constants

- **Discord Channel:** #hermes-crypto-monitor (ID: 1543645766076342312 in guild 1470798593118965956)
- **Report Time:** Daily 10:00 UTC (cron entry `crypto-monitor-daily`)
- **Braille Blank:** \u2800 (for empty lines)
- **External seam:** `services/agent_bridge.py` - external-process calls only (Discord gateway); no Python-library wrappers here
- **Cron Job ID:** see `fork/hermes-config/cron/jobs.json`
