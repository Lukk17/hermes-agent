# OSINT project conventions

This file is read by the hermes agent when its working directory is `/opt/projects/osint/`. It layers on top of `/opt/projects/AGENTS.md`. When the two conflict, the project-specific instruction here wins.

## Skill usage in this project

This project does open-source intelligence gathering. The mandatory skill set:

- `python-patterns` for any edit to `src/` Python code (cascade engine, tool integrations, services)
- `coding-standards` for style/quality reviews
- `docker-patterns` when adjusting the cron pipeline or env wiring (rare for this project since OSINT is manual-only)
- `observability-and-logging` for adding metrics or structured logs to investigations
- `review-duplication` before merging changes that span multiple services
- `security-review` for any change that handles API keys, breach data, or PII
- `finance-billing-ops` (or `finance-*`) for paid OSINT API cost accounting

Run `skills list` mentally before each turn and pull in every skill that fits.

## What lives here

Source code (tracked):

- `README.md` — original OpenClaw project docs (setup, requirements, install steps, blocked services). Path references are OpenClaw-specific and have to be read as historical context only.
- `SETUP.md` — step-by-step OpenClaw install. Skip for hermes; this project is now bootstrapped by copying files into `/opt/projects/osint/`.
- `free_with_api.md` — catalog of free and paid OSINT APIs. Useful reference for what the agent can do per API key in `.env`.
- `leaks_dbs.md` — list of known leak search databases. The agent uses `data/leaks/` to cache results.
- `ARCHITECTURE.md` — cascade engine overview. OpenClaw terminology, but the engine design carries over to hermes.
- `TODO.md` — pending work.
- `pyproject.toml` — Python project config. Use `uv` rather than `pip` to manage the venv.
- `src/main.py` — CLI entry point. The hermes agent invokes this via `python3 src/main.py --query "<entity>" [...]`.
- `src/ascend_client.py` — wraps the ascend scraper for web fetches.
- `src/cascade.py` — cascade engine that follows connections up to depth 3.
- `src/services/`` — per-service code: `breach_service.py`, `people_service.py`, `spiderfoot_service.py`, `recon_service.py`, `local_leak_service.py`, etc.
- `src/captcha_handler.py` — helper for asking the user to resolve CAPTCHAs in Discord.
- `src/theHarvester/` — third-party tool, vendored. Run via the project venv.
- `Amass/` — third-party tool, vendored. Run via the project venv.
- `bin/` — vendored binaries (subfinder, httpx, amass, naabu, mosint).
- `tests/` — pytest test suite (some files like `test_system.py` come from OpenClaw).
- `data/leaks/` — cached leak database output (gitignored at runtime; tracked only as `data/leaks/.gitkeep`).
- `reports/` — generated markdown reports per investigation.

Runtime state (gitignored via `fork/projects/.gitignore`):

- `.venv/` — Python virtualenv. Built once per machine via `uv venv .venv --python python3.12` (the OSINT stack pulls in tools that need 3.11+, hermes container has 3.13 but `.venv` is independent).
- `data/` — all investigation data, including `data/leaks/`.
- `logs/` — investigation logs.
- `*.csv` — ad-hoc exports.
- `reports/` — generated markdown reports.

## Per-investigation workflow

The agent must NEVER start an investigation without the user's explicit authorization in the same channel. The workflow:

1. User types: `investigate <entity> depth <1|2|3> format <markdown|json>`.
2. Agent confirms the target, depth, and format. Asks for clarification if any field is missing.
3. Agent runs:
    ```
    cd /opt/projects/osint && source .venv/bin/activate
    python3 src/main.py --query "<entity>" [--no-cascade] [--format markdown|json]
    ```
4. Agent reads the produced report from `reports/`.
5. Agent posts a Discord-friendly summary to `#hermes-osint`. Optionally attaches the full markdown as a file.
6. Agent always cites the source tool for each finding.

## Polish naming convention

- For Polish targets (names, companies), pass the name as-is to the cascade engine.
- For Polish sole proprietors (JDG), the cascade engine extracts the person name from GitHub profile data and appends it to the company name for search (e.g. "RevDev Lukukkawska Sarna" not just "RevDev"). The agent does NOT pre-format that for it.

## Cascade engine rules

- Auto-follows subject-owned connections: own emails, domains, profiles, companies.
- Up to depth 3 with max 5 connections per search.
- Does NOT follow coworker or social-media subdomain links.
- Skip amass/subfinder against social media domains.

## Blocked services

These need manual workarounds, not the agent:

- rejestr.io — CAPTCHA
- CEIDG / KRS Online — JS rendering required
- eKRS — CAPTCHA
- LinkedIn, Twitter/X — blocks scrapers

For blocked services, suggest the user opens the URL in their browser manually or use Maigret/Sherlock instead. The `captcha_handler.py` module sends the user a Discord DM with a link and asks them to paste the result back.

## Tool conventions

- For ALL web scraping, use the ascend scraper (`src/ascend_client.py`, via `$ASCEND_SCRAPPER_URL`). NEVER use Playwright or Selenium in this project.
- For Polish JDG companies, the cascade engine handles the name extraction automatically.
- For blocked services, suggest manual workarounds via `captcha_handler.py`.

## Available data sources

From `.env`:

- `HUNTER_API_KEY` — email lookup
- `SHODAN_API_KEY` — IP/host intel
- `VIRUSTOTAL_API_KEY` — file/URL/IP hash lookup
- `GITHUB_TOKEN` — GitHub user/repo enrichment
- `ABSTRACT_API_KEY` — email/phone validation
- `CENSYS_API_KEY` + `CENSYS_SECRET` — host/cert intel
- `BREACHDIRECTORY_VIA_RAPIDAPI_API_KEY` — credential leaks
- `ABUSEIPDB_API_KEY` — IP abuse reports
- `URLSCAN_API_KEY` — URL scans
- `OTX_API_KEY` — AlienVault OTX threat intel
- `DEHASHED_API_KEY` — breach data
- `NUMVERIFY_API_KEY` — phone validation
- `IPQS_API_KEY` — IP quality score

## First-time setup

```bash
cd /opt/projects/osint
uv venv .venv --python python3.12
source .venv/bin/activate
uv pip install -e .   # or: uv pip install -r requirements.txt if you have one
# Smoke test
python3 src/main.py --query "test@example.com" --no-cascade --format markdown
```

## Known paths to update

The Python code in `src/` is currently in transition from OpenClaw paths to hermes paths. Before this project is fully production-ready on hermes, the following hardcoded references must be reviewed and updated by the agent:

- `src/services/breach_service.py` — hardcodes `/home/node/.openclaw/workspace/osint/.venv/bin/python3` for spawning h8mail / holehe subprocesses. Replace with `/opt/projects/osint/.venv/bin/python3` or a derived path.
- `src/services/people_service.py` — hardcodes `/home/node/.openclaw/workspace/osint/.venv/bin/python3` and `/home/node/.openclaw/workspace/osint/data` output paths. Replace.
- `src/services/recon_service.py` — hardcodes `.venv/bin/python3` and `theHarvester` paths. Replace.
- `src/services/spiderfoot_service.py` — hardcodes `.venv/bin/python3`. Replace.
- `src/services/local_leak_service.py` — hardcodes `data/leaks`. Relative path is fine.
- `src/captcha_handler.py` — uses `["openclaw", "message", "send", ...]` shell-out pattern. Replace with the `discord.send` gateway tool path or a simpler approach.

Run `grep -rn '.openclaw\|/home/node' .` from the project root to find every hardcoded reference. Replace each with paths derived from `os.path.dirname(__file__)` or the project env.

## What this project is NOT

- It is NOT automated reconnaissance. Every investigation starts with the user's explicit authorization.
- It is NOT the OpenClaw project. The OpenClaw version lives at `\\wsl$\Ubuntu\home\lukk\.openclaw\workspace\osint\`. Hermes reads from `/opt/projects/osint/`, not the OpenClaw path.
- It is NOT the gateway config. Channel behavior, API keys, and Discord settings live in `hermes-data/config.yaml` and `.env`.