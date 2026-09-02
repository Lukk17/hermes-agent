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
│    ask_agent(prompt, ...)    -> runs `hermes -z`, returns generated text    │
│    send_message(text, ...)   -> runs `hermes send`, delivers the message    │
│                                                                             │
│  The pipeline calls both. See "Publish to Discord" below.                   │
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
| funding | funding_latest.json | funding_history.json | funding_collector.py | daily_report.py |
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
| news_summary.md | Agent | AI-generated news summary |
| market_summary.md | Agent | AI-generated market summary |
| gauge_fng.png, gauge_cycle.png, gauge_sentiment.png, trending_narratives.png, coin_sentiment.png | report_builder.py via charts.py | See "Charts Directory" below |

`discord_messages.json` and `discord_outbox.json` are both gone. There is no
outbox: `scripts/post_to_discord.py` publishes directly through the seam in the
same pipeline run that produced the report.

### Charts Directory

| Chart | Written to | Generated By | Source Data |
|-------|------------|--------------|-------------|
| gauge_fng.png | data/reports/ | report_builder.py via charts.py | fear_greed from external_indices |
| gauge_cycle.png | data/reports/ | report_builder.py via charts.py | cycle data |
| gauge_sentiment.png | data/reports/ | report_builder.py via charts.py | sentiment data |
| trending_narratives.png | data/reports/ | report_builder.py via charts.py | trends categories |
| coin_sentiment.png | data/reports/ | report_builder.py via charts.py | per-coin sentiment |
| btc_dominance_2y.png | data/dominance/charts/ | dominance_chart.py | dominance_history.json |
| btc_price_2y.png | data/btc_price/ | btc_price_chart.py | prices_history.json |
| gas_history_1y.png | data/gas/charts/ | gas_collector.py | gas_history.json |

Only the first five are under `data/reports/`. There are no `table_*.png`
files: table rendering was removed in a refactor (see the note at the end of
`build_charts()` in `reports/report_builder.py`) and the tables are sent as
text instead.

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
| funding_collector.py | funding_latest.json | Bybit. Runs in the pipeline; the Funding Rates section is rendered. |
| gas_collector.py | gas_latest.json | BlockNative (`blocknative_gas` in config/settings.json) |
| influencer_collector.py | influencers_latest.json | RSS feeds |
| index_scraper.py | external_indices_latest.json | alternative.me, CoinGecko |
| market_breadth_collector.py | market_breadth_latest.json | CoinGecko |
| sector_collector.py | sectors_latest.json | CoinGecko |
| stablecoin_collector.py | stablecoins_latest.json | CoinGecko |
| whale_alert_collector.py | whale_alerts_latest.json | WhaleAlert API |
| whale_discovery.py | whales_latest.json | Blockscout |

**Note:** `news_collector.py` exists and IS part of the pipeline. It is
invoked from `scripts/report_generator.py` and produces
`data/news/news_latest.json`, which the daily workflow requires for the news
summary. Do not remove it.

`price_fetcher.py` and `whale_tracker.py` do not exist. Prices come from
`btc_price_chart.py`, whales from the `whale_tracker_*` collectors.

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
| report_generator.py | Runs all collectors/analyzers via its own `run_script()` helper (one subprocess per step, per-step timeout, a failing step never crashes the pipeline), creates report_latest.json |
| generate_summaries.py | Calls `ask_agent()` twice, writes news_summary.md and market_summary.md |
| post_to_discord.py | In-container publisher: builds the delivery sequence via `build_delivery()` and sends it through `send_message()`. The pipeline's final step. |

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
| container process environment | API keys (`BLOCKSCOUT_API_KEY`, `ALCHEMY_API_KEY`, `CRYPTOPANIC_API_KEY`), injected by `docker-compose.override.yml` from the gitignored repo-root `.env` on the host. There is no `.env` inside this project and there must never be one. |
| config/settings.json | Main configuration (API endpoints, thresholds, chart settings, external links) |
| config/influencers.json | Influencer RSS sources and wallet addresses |
| config/whale_registry.json | Known whale addresses |
| config/exchange_wallets.json | Exchange wallet addresses for flow tracking |

---

## Report Generation Flow

### 1. Cron triggers at 10:00 UTC
```
Cron → /opt/data/scripts/crypto-monitor-daily.sh (wrapper)
         → /opt/projects/crypto-monitor/daily_report_pipeline.sh
```

The job is `no_agent: true` with no `deliver` and no `prompt`. Cron runs the
script and nothing else, so the pipeline's exit code is the only signal. The
wrapper exists because `cron/scheduler.py:4289-4300` refuses any `script` path
resolving outside `/opt/data/scripts`.

### 2. Run pipeline
```
report_generator.py
  ├── Collectors (16 scripts) → data/*_latest.json
  ├── Analyzers (5 scripts) → data/*_latest.json  
  └── daily_report.py → data/reports/report_latest.json
```

### 3. Pipeline asks the agent for two sections
```
scripts/generate_summaries.py
  ├── ask_agent(NEWS_PROMPT,   context=news_latest.json)  → news_summary.md
  └── ask_agent(MARKET_PROMPT, context=SUMMARY_GUIDE.md + report_latest.json)
                                                          → market_summary.md
```

Both files are body text only, no headings. `reports/report_builder.py` supplies
the headers and substitutes them for the data-rendered `news` and `summary`
sections rather than adding them alongside.

### 4. Publish to Discord

The pipeline publishes. The agent does not, and there is no agent turn in the
scheduled path at all.

```
scripts/post_to_discord.py
  ├── build_delivery(report_latest.json)  (reports/report_builder.py)
  │     └── title, then 8 charts, then up to 15 text sections
  └── send_message(text, platform=..., conversation=..., attachments=[...])
        └── services/agent_bridge.py → `hermes send`
```

The delivery target comes from `config/settings.json` under `delivery`
(`platform`, `conversation`, `thread`), not from a literal in code.

`services/agent_bridge.py` is the project's ports-and-adapters seam, the one
place the project crosses out of its own process. It is deliberate and it stays,
so the project remains portable to another agent runtime. Its whole public
surface is `check_available()`, `ask_agent()`, `send_message()`, and six
exception types. There is no outbox: `discord_outbox.json`, `consume_outbox()`
and `publish_daily_report()` were removed, because producer and consumer ran
seconds apart in the same invocation, the file was a single slot any second
writer overwrote, and the drain unlinked before sending so the retry it appeared
to enable could not happen.

Do NOT add Python-library wrappers to `agent_bridge` - call `requests`,
`urllib.request`, `subprocess`, etc. directly from the file that needs them.

There is still no agent-callable Discord send tool. `tools/discord_tool.py`
registers `discord` (read and moderate) and `discord_admin` only, and
`send_message` is deliberately not registered as a model tool. The seam reaches
delivery by shelling out to the CLI, not by calling a tool.

### The `hermes send` contract

`send_message()` shells out to the `hermes` binary resolved from `PATH`, never by
absolute path, so the privilege-drop shim at `/opt/hermes/bin/hermes` wins
resolution. The invocation is:

```
hermes send --json --to <platform>:<chat_id> <message>
```

The message is a POSITIONAL argument. Attachments are not a flag: they ride as
`MEDIA:` lines carrying an absolute path inside the message text.

Two flags the previous code reached for and got wrong, both worth knowing before
you reach for them again: `--content` does not exist, and `--file` is the message
BODY read from a path, not an attachment. `hermes_cli/send_cmd.py:453` says so in
its own help text, and the parser epilog gives the `MEDIA:` form as the
attachment example.

`publish_pipeline.sh`, `discord_messages_generator.py`, `publish_report.py`,
`data/reports/discord_messages.json` and `data/reports/discord_outbox.json` do
not exist.

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
17. Funding Rates (text)
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
