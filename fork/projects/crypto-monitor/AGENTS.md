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

- `daily_report_pipeline.sh` — runs `scripts/report_generator.py` (collectors + analyzers + chart generation). Outputs to `data/reports/report_latest.json` and chart PNGs in `data/reports/`. **Paths inside this script are hardcoded to `/opt/projects/crypto-monitor/`** (hermes layout), NOT to OpenClaw paths.
- `scripts/report_generator.py` — main orchestrator. Runs prefetch, collectors, analyzers, daily report generator.
- `scripts/report_generator.py` calls into `collectors/`, `analyzers/`, and `reports/daily_report.py` (a sub-module of `scripts/`).
- `collectors/` — 20+ Python scripts that fetch raw data (CoinGecko shared cache, BTC/ETH whale trackers, Fear & Greed, ETF flows, news, influencers, gas prices, sector performance, etc.). Saves to `data/<category>/`.
- `analyzers/` — 5 Python scripts that process raw data. Cycle score, sentiment, trend detection, whale signals, airdrop tracker. Saves to `data/<category>/`.
- `reports/daily_report.py` (submodule of `scripts/`) — renders the daily Discord messages. Produces `data/reports/report_latest.json` and chart PNGs.
- `tools/verify_wallets.py` — one-off wallet verification helper.
- `config/` — JSON config: API endpoints (`settings.json`), whale registry (`whale_registry.json`), exchange wallets (`exchange_wallets.json`), influencer Twitter handles (`influencers.json`), airdrop opportunities (`airdrop_opportunities.json`).
- `requirements.txt` — Python deps for the project's venv (NOT a system install).
- `AGENT.md` — the original OpenClaw daily-task instructions. Path references are OpenClaw-specific (`/home/node/.openclaw/workspace/crypto-monitor`). **Read for context only**. The authoritative instructions are in this AGENTS.md plus the channel_prompts in `fork/hermes-config/config.yaml` (bind-mounted at `/opt/data/config.yaml` inside the container).
- `USER_REQUIREMENTS.md` — chart dimensions, section ordering, emoji headers, braille blank rules. Follow for any report composition.
- `SUMMARY_GUIDE.md` — indicator interpretations (Fear and Greed buckets, Cycle Score phases, RSI ranges, MA Cross signals, Pi Cycle, BTC Dominance thresholds). Use to interpret every number.
- `README.md` — OpenClaw-era project overview, API key list, collector/analyzer inventory. Most of it is still relevant for hermes; the few OpenClaw-specific lines are noted inline.
- `ARCHITECTURE.md` — full data flow diagram and caching strategy. OpenClaw terminology, but the data flow is the same.
- `TODO.md` — pending work.

Runtime state (gitignored via `fork/projects/.gitignore`):

- `.venv/` — Python virtualenv (with leading dot, gitignored). Built once per machine via `uv venv .venv --python python3.11` then then `./.venv/bin/pip install -r requirements.txt`.
- `data/reports/` — generated reports and chart PNGs.
- `data/_cache/` — shared API cache (TTL-based).
- `data/news/news_latest.json` — news input to the daily pipeline (gitignored; reproduced from `data/news/news_<date>.json` snapshots).
- `data/<category>/_latest.json` and `<category>_history.json` — per-collector/analyzer output (gitignored).
- `logs/` — pipeline logs.

## Daily report workflow

When triggered (either by the `crypto-monitor-daily` cron job or by a manual user message in `#hermes-crypto-monitor`):

1. `cd /opt/projects/crypto-monitor`
2. Run `./daily_report_pipeline.sh` (uses the project's venv).
3. Read `data/reports/report_latest.json` and `data/news/news_latest.json`.
4. Generate two files, NO HEADER, just content per `AGENT.md`:
    - `data/reports/news_summary.md`
    - `data/reports/market_summary.md`
5. Post a Discord-friendly summary to `#hermes-crypto-monitor` via the `discord.send` tool. Attach the PNG charts that exist (`gauge_*`, `table_*`, `trending_*`, `coin_sentiment*`, `btc_dominance*`). Follow section ordering and emoji headers from `USER_REQUIREMENTS.md`.

NEVER run `publish_pipeline.sh`, `scripts/publish_report.py`, or `scripts/discord_messages_generator.py`. Those are OpenClaw remnants and were removed when the project moved to hermes. The `discord.send` gateway tool replaces them.

## Available data sources

From `.env`:

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

Cron entry `crypto-monitor-daily` in `fork/hermes-config/cron/jobs.json` (bind-mounted at `/opt/data/cron/jobs.json`) fires daily at 10:00 UTC, cron expression `0 10 * * *`, container timezone UTC. The job runs as the hermes container user, so it can call `./daily_report_pipeline.sh` directly.

## First-time setup

```bash
cd /opt/projects/crypto-monitor
uv venv .venv --python python3.11
./.venv/bin/pip install -r requirements.txt
# Smoke test
./.venv/bin/python scripts/report_generator.py
```

If collectors fail with import errors, add the missing packages to `requirements.txt` and re-install. Re-run `hermes cron run crypto-monitor-daily` (dry-run) to verify end-to-end.

## Known paths to update

The Python code in `collectors/`, `analyzers/`, `scripts/`, and `reports/` is currently in transition from OpenClaw paths to hermes paths. Before this project is fully production-ready on hermes, the following hardcoded references must be reviewed and updated by the agent:

- `tools/verify_wallets.py` may reference absolute paths under `/home/node/.openclaw/`.
- `config/settings.json` may point at an OpenClaw-specific API endpoint.
- A handful of remaining collectors (altseason, defi_tvl, etf_flow,
  exchange_flow_tracker, gas, funding, dominance, whale_* etc.) still
  import `requests`/`urllib.request` directly. Migrate them to
  `fetch_json`/`fetch_text` from `services/external.py` as you touch
  them.

Run `grep -rn '.openclaw\|/home/node' .` from the project root to find
every hardcoded reference. Replace each with a path derived from
`os.path.dirname(__file__)` or imported from `src.paths`.

The pipeline currently runs from the project root via
`daily_report_pipeline.sh`, so most relative paths work. The grep is
mostly to catch absolute paths that were left over from the OpenClaw
layout.

## What this project is NOT

- It is not a trading system. The agent does NOT execute trades, place orders, or move funds. Observation only.
- It is not the OpenClaw project. The OpenClaw version of this same content lives at `\\wsl$\Ubuntu\home\lukk\.openclaw\workspace\crypto-monitor\`. Hermes reads from `/opt/projects/crypto-monitor/`, not the OpenClaw path.
- It is not the gateway config. Channel behavior, API keys, and Discord settings live in `fork/hermes-config/config.yaml` and `.env`.