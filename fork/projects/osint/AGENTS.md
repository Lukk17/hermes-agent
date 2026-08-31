# OSINT project conventions

This file is read by the hermes agent when its working directory is `/opt/projects/osint/`. It layers on top of `/opt/projects/AGENTS.md`. When the two conflict, the project-specific instruction here wins.

## What lives here

Source code (tracked):

- `README.md` — original OpenClaw project docs (setup, requirements, install steps, blocked services).
- `ARCHITECTURE.md` — agent overview, cascade engine, naming conventions.
- `TODO.md` — pending work for the project.
- `src/main.py` — main entry point. CLI invocation.
- `src/ascend_client.py` — wraps the ascend scraper for web fetches.
- `src/cascade.py` — cascade engine that follows connections up to depth 3.
- `src/<tool>.py` — per-tool integrations (hunter_io, virustotal, maigret, sherlock, etc.).
- `tests/` — pytest test suite.

Runtime state (gitignored):

- `.venv/` — Python virtualenv. Built once per machine. Use `python3` from inside this venv.
- `reports/` — generated markdown reports per investigation.
- `cache/` — cached API responses.
- `logs/` — pipeline logs.

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

For blocked services, suggest the user opens the URL in their browser manually or use Maigret/Sherlock instead.

## Tooling

- For ALL web scraping, use the ascend scraper (`src/ascend_client.py`, via `$ASCEND_SCRAPPER_URL`). NEVER use Playwright or Selenium in this project.
- For Polish JDG companies, the cascade engine handles the name extraction automatically.
- For blocked services, suggest manual workarounds.

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

## What this project is NOT

- It is NOT automated reconnaissance. Every investigation starts with the user's explicit authorization.
- It is NOT the OpenClaw project. The OpenClaw version lives at `\\wsl$\Ubuntu\home\lukk\.openclaw\workspace\osint\`. Hermes reads from `/opt/projects/osint/`, not the OpenClaw path.
- It is NOT the gateway config. Channel behavior, API keys, and Discord settings live in `hermes-data/config.yaml` and `.env`.