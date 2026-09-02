# Crypto Monitor project conventions

This file is read by the hermes agent when its working directory is `/opt/projects/crypto-monitor/`. It layers on top of `/opt/projects/AGENTS.md`. When the two conflict, the project-specific instruction here wins.

## Skill usage in this project

This project routinely touches data collection pipelines, daily report generation, indicator interpretation, and Discord publishing. The mandatory skill set for any non-trivial task:

- `python-patterns` for any edit to `collectors/`, `analyzers/`, `scripts/`, or `reports/`
- `coding-standards` for style/quality reviews of the Python code
- `docker-patterns` when adjusting the cron pipeline, paths, or env wiring
- `observability-and-logging` when adding metrics, log lines, or alerts to the pipeline
- `review-duplication` before merging changes that touch multiple collectors
- `security-review` for any change that handles API keys or `data/news/`
- `finance-billing-ops` (or `finance-*`) for indicator interpretation logic

Run `skills list` mentally before each turn and pull in every skill that fits.

## What lives here

Source code (tracked):

- `daily_report_pipeline.sh` — runs `scripts/report_generator.py` (collectors + analyzers + chart generation). Outputs `data/reports/report_latest.json` plus the chart PNGs listed under "Daily report workflow". **Paths inside this script are hardcoded to `/opt/projects/crypto-monitor/`**, the container layout.
- `scripts/report_generator.py` — runs prefetch, collectors, analyzers, then the report builder. Writes `data/reports/report_latest.json` and the chart PNGs.
- `scripts/generate_summaries.py` — calls the agent twice through the seam and writes `data/reports/news_summary.md` and `data/reports/market_summary.md`.
- `scripts/post_to_discord.py` — assembles the fixed message sequence and publishes it. This is the pipeline's final step, not something the agent runs.
- `services/agent_bridge.py` — the ports-and-adapters seam, the one place the project crosses out of its own process. Two public functions, `ask_agent()` and `send_message()`, plus `check_available()` and six exception types.
- `collectors/` — 20+ Python scripts that fetch raw data (CoinGecko shared cache, BTC/ETH whale trackers, Fear & Greed, ETF flows, news, influencers, gas prices, sector performance, etc.). Saves to `data/<category>/`.
- `analyzers/` — 5 Python scripts that process raw data. Cycle score, sentiment, trend detection, whale signals, airdrop tracker. Saves to `data/<category>/`.
- `reports/report_builder.py` — builds the report payload and the charts, and owns `CHART_ORDER`, `SECTION_ORDER`, `build_message_sequence()` and `build_delivery()`. This is where the delivery order is defined.
- `tools/verify_wallets.py` — one-off wallet verification helper.
- `config/` — JSON config: API endpoints (`settings.json`), whale registry (`whale_registry.json`), exchange wallets (`exchange_wallets.json`), influencer Twitter handles (`influencers.json`), airdrop opportunities (`airdrop_opportunities.json`).
- `pyproject.toml` — Python deps for the project's venv (NOT a system install). `requires-python = ">=3.11,<3.12"`, dependencies `matplotlib`, `numpy`, `Pillow`. There is no `requirements.txt`.
- `USER_REQUIREMENTS.md` — chart dimensions, section ordering, emoji headers, braille blank rules. Follow for any report composition.
- `SUMMARY_GUIDE.md` — indicator interpretations (Fear and Greed buckets, Cycle Score phases, RSI ranges, MA Cross signals, Pi Cycle, BTC Dominance thresholds). Use to interpret every number.
- `README.md` — project overview, API key list, collector/analyzer inventory.
- `ARCHITECTURE.md` — full data flow diagram and caching strategy.
- `TODO.md` — pending work.

Runtime state (gitignored via `fork/projects/.gitignore`):

- `.venv/` — Python virtualenv (with leading dot, gitignored). Built once per machine via `uv venv .venv --python python3.11` then `uv pip install --python ./.venv/bin/python -e .`.
- `data/reports/` — generated report payload plus the gauge, narrative and coin-sentiment PNGs.
- `data/_cache/` — shared API cache (TTL-based).
- `data/news/news_latest.json` — news input to the daily pipeline (gitignored; reproduced from `data/news/news_<date>.json` snapshots).
- `data/<category>/_latest.json` and `<category>_history.json` — per-collector/analyzer output (gitignored).
- `data/reports/pipeline_errors_<date>.json` — one file per pipeline run listing the steps that failed. There is no `logs/` directory.

## Daily report workflow

**The pipeline is the orchestrator and the agent is a subroutine inside it.** The
report must look identical every morning, so the pipeline owns the structure and
calls the agent only for the two pieces that genuinely need a model. The agent
does not compose the post and does not publish it.

`./daily_report_pipeline.sh` runs these steps in order and stops at the first
failure:

1. `scripts/report_generator.py` — collectors, analyzers, charts, writes `data/reports/report_latest.json`.
2. A freshness assertion: if `report_latest.json` was not rewritten by this run, the pipeline refuses to publish.
3. `scripts/generate_summaries.py` — calls `ask_agent()` twice and writes `data/reports/news_summary.md` and `data/reports/market_summary.md`, body text only with no headings.
4. `scripts/post_to_discord.py` — assembles the fixed sequence and publishes it through `send_message()`.

Exit codes: `0` published, `2` bad usage or the venv Python is missing, `3` the
report generator failed, `4` the report was not rewritten this run, `5`
publishing failed, `6` the summaries could not be written.

### What the agent is asked for

Only two things, both plain text with no heading, no preamble and no closing
remark, because `reports/report_builder.py` supplies the headers:

- `news_summary.md` — a numbered list of the ten most important headlines, each with one short clause on why it matters. It REPLACES the data-rendered `news` section rather than sitting beside it, under the header `## 📰 Trending News`.
- `market_summary.md` — the closing summary, written to `SUMMARY_GUIDE.md`. It REPLACES the data-rendered `summary` section, under the header `## 📋 Market Summary`.

`ask_agent()` shells out to `hermes -z`, the one-shot mode that prints only the
final response with no banner and no session line. It is pinned to the
`context_engine` toolset, the one toolset in the catalog that resolves to zero
tools, so the summariser has no tool surface at all. It inherits the fork's model
config, so no provider credentials are duplicated into the project. Memory is
loaded for one-shot runs and cannot be suppressed without an upstream change, but
the tool surface is empty and the prompts are self-contained, so the variance is
phrasing rather than structure.

### Delivery order

Title first, then every chart, then the text sections. Fixed every run. A missing
chart or section drops out without shifting anything that survives
(`reports/report_builder.py`, `CHART_ORDER` and `SECTION_ORDER`).

1. The title and timestamp.
2. Eight charts, in this order: `gauge_fng`, `gauge_cycle`, `gauge_sentiment`, `trending_narratives`, `coin_sentiment`, `btc_dominance`, `btc_price`, `gas_history`.
3. Up to fifteen text sections: prices, movers, news, indicators, breadth, sectors, gas, etf, stablecoins, funding, flows, whales, airdrops, summary, links.

That is 24 messages at most, and a typical run delivers about 22 because a
couple of sections have no data on any given day. Which two vary, so the count
is NOT the contract. The order is.

Chart files, three of which are NOT under `data/reports/`:

- `data/reports/gauge_fng.png`, `gauge_cycle.png`, `gauge_sentiment.png`, `trending_narratives.png`, `coin_sentiment.png`
- `data/dominance/charts/btc_dominance_2y.png`
- `data/btc_price/btc_price_2y.png`
- `data/gas/charts/gas_history_1y.png`

There are no `table_*.png` files. Table rendering was removed in a refactor and
the tables are sent as text.

The delivery target lives in `config/settings.json` under `delivery`
(`platform`, `conversation`, `thread`), not as a literal in code.

`publish_pipeline.sh`, `scripts/publish_report.py` and
`scripts/discord_messages_generator.py` do not exist.

## Available data sources

Read from the container process environment (injected by `docker-compose.override.yml` from the gitignored repo-root `.env` on the host, never from a `.env` inside this project):

- `BLOCKSCOUT_API_KEY` — on-chain via blockscout
- `ALCHEMY_API_KEY` — on-chain via Alchemy
- `CRYPTOPANIC_API_KEY` — news via cryptopanic

Keyless (used directly by collectors):

- CoinGecko (price)
- Mempool.space (Bitcoin mempool)
- Bybit (derivatives)
- Farside (ETF flows)
- alternative.me (Fear and Greed)
- BlockNative (ETH gas)

## Schedule

Cron entry `crypto-monitor-daily` in `fork/hermes-config/cron/jobs.json`
(bind-mounted at `/opt/data/cron/jobs.json`) fires daily at 10:00 UTC, cron
expression `0 10 * * *`, container timezone UTC.

The job is `no_agent: true` with no `deliver` and no `prompt`. Cron runs the
script and nothing else, so the pipeline's exit code is the only signal. There is
no agent turn in the scheduled path at all.

The `script` field is the bare basename `crypto-monitor-daily.sh`, and it
resolves through a two-file pair:

- `fork/hermes-config/scripts/crypto-monitor-daily.sh` is a small wrapper, bind-mounted at `/opt/data/scripts/crypto-monitor-daily.sh`. It does nothing but `exec bash /opt/projects/crypto-monitor/daily_report_pipeline.sh`.
- `fork/projects/crypto-monitor/daily_report_pipeline.sh` is the real pipeline.

The wrapper is not pointless indirection. `cron/scheduler.py:4289-4300` refuses
any `script` path that resolves outside `$HERMES_HOME/scripts`, which is
`/opt/data/scripts`. Putting the pipeline's absolute path back into `jobs.json`
re-breaks the job, and it breaks it silently: the scheduler folds the block into
the prompt under a `## Script Error` heading and the job still records
`last_status: ok`.

Both `DISCORD_BOT_TOKEN` and `MINIMAX_API_KEY` must also be present in
`hermes-data/.env`, not only in the compose passthrough. Hermes strips those two
from every subprocess environment, so the pipeline's `hermes send` and
`hermes -z` calls cannot see them otherwise. See the credentials section of
`fork/NOTE-5-operations.md`.

## First-time setup

```bash
cd /opt/projects/crypto-monitor
uv venv .venv --python python3.11
uv pip install --python ./.venv/bin/python -e .
# Smoke test
./.venv/bin/python scripts/report_generator.py
```

If collectors fail with import errors, add the missing packages to the `dependencies` list in `pyproject.toml` and re-install.

`hermes cron run crypto-monitor-daily` is NOT a dry run. It triggers a real run of the job, including delivery to the Discord channel. Use it only when a real post is wanted.

## Path conventions in the Python code

Paths are derived from the file's own location, not hardcoded. `src/paths.py` is the single source of truth: `PROJECT_ROOT`, `DATA_DIR`, `REPORTS_DIR`, `CACHE_DIR`, `CONFIG_DIR`, `PYTHON_BIN`. Import from there rather than recomputing a relative path or writing an absolute one.

The pipeline runs from the project root via `daily_report_pipeline.sh`, so relative paths resolve correctly.

## What this project is NOT

- It is not a trading system. The agent does NOT execute trades, place orders, or move funds. Observation only.
- It is not the gateway config. Channel behavior, API keys, and Discord settings live in `fork/hermes-config/config.yaml` on the host and in the repo-root `.env`.