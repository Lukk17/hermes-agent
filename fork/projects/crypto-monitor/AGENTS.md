# Crypto Monitor project conventions

This file is read by the hermes agent when its working directory is `/opt/projects/crypto-monitor/`. It layers on top of `/opt/projects/AGENTS.md`. When the two conflict, the project-specific instruction here wins.

## What lives here

Source code (tracked):

- `daily_report_pipeline.sh` — runs `scripts/report_generator.py` (collectors + analyzers + chart generation). Outputs to `data/reports/report_latest.json` and chart PNGs in `data/reports/`.
- `scripts/report_generator.py`, `scripts/<collector>.py`, `scripts/<analyzer>.py` — Python source.
- `requirements.txt` — Python deps for the project's venv (NOT a system install).
- `AGENT.md` — the original OpenClaw project instructions for the agent. Read on every daily report run.
- `USER_REQUIREMENTS.md` — chart dimensions, section ordering, emoji headers, braille blank rules. Follow for any report composition.
- `SUMMARY_GUIDE.md` — indicator interpretations (Fear and Greed buckets, Cycle Score phases, RSI ranges, MA Cross signals, Pi Cycle, BTC Dominance thresholds). Use to interpret every number.
- `data/news/news_latest.json` — news input to the daily pipeline.

Runtime state (gitignored):

- `venv/` — Python virtualenv. Built once per machine.
- `data/reports/` — generated reports and chart PNGs.
- `data/cache/` — any cached API responses.
- `logs/` — pipeline logs.

## Daily report workflow

When triggered (either by the `crypto-monitor-daily` cron job or by a manual user message in `#hermes-crypto-monitor`):

1. `cd /opt/projects/crypto-monitor`
2. Run `./daily_report_pipeline.sh` (uses the project's venv).
3. Read `data/reports/report_latest.json` and `data/news/news_latest.json`.
4. Generate two files, NO HEADER, just content per `AGENT.md`:
    - `data/reports/news_summary.md`
    - `data/reports/market_summary.md`
5. Post a Discord-friendly summary to `#hermes-crypto-monitor` via the `discord.send` tool. Attach the PNG charts that exist (gauge_*,`, ` table_*,`, ` trending_*,`, ` coin_sentiment*,`, ` btc_dominance*`). Follow section ordering and emoji headers from `USER_REQUIREMENTS.md`.

NEVER run `publish_pipeline.sh`, `scripts/publish_report.py`, or `scripts/discord_messages_generator.py`. Those are OpenClaw remnants. The `discord.send` gateway tool replaces them.

## Available data sources

From `.env`:

- `BLOCKSCOUT_API_KEY` — on-chain via blockscout
- `ALCHEMY_API_KEY` — on-chain via Alchemy
- `CRYPTOPANIC_API_KEY` — news via cryptopanic

Keyless:

- CoinGecko (price)
- Mempool.space (Bitcoin mempool)
- Bybit (derivatives)
- Farside (ETF flows)
- alternative.me (Fear and Greed)

## Schedule

Cron entry `crypto-monitor-daily` in `/opt/data/cron/jobs.json` fires daily at 10:00 UTC, cron expression `0 10 * * *`, container timezone UTC. The job runs as the hermes container user, so it can call `./daily_report_pipeline.sh` directly.

## What this project is NOT

- It is not a trading system. The agent does NOT execute trades, place orders, or move funds. Observation only.
- It is not the OpenClaw project. The OpenClaw version of this same content lives at `\\wsl$\Ubuntu\home\lukk\.openclaw\workspace\crypto-monitor\`. Hermes reads from `/opt/projects/crypto-monitor/`, not the OpenClaw path.
- It is not the gateway config. Channel behavior, API keys, and Discord settings live in `hermes-data/config.yaml` and `.env`.