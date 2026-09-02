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

- `README.md` — project docs: tool inventory, service status table, blocked services, env key names.
- `SETUP.md` — install and verification steps for the container layout.
- `free_with_api.md` — catalog of free and paid OSINT APIs. Reference for what each key unlocks.
- `leaks_dbs.md` — list of known leak search databases. The agent uses `data/leaks/` to cache results.
- `ARCHITECTURE.md` — cascade engine overview.
- `TODO.md` — pending work.
- `pyproject.toml` — Python project config. Use `uv` rather than `pip` to manage the venv.
- `src/main.py` — CLI entry point. Three entry forms: `--query "<entity>"`, `--input '<json>'`, and `--resume <token>` to continue a run that paused for a CAPTCHA. Invoke it as `./.venv/bin/python src/main.py ...`.
- `src/ascend_client.py` — wraps the ascend scraper for web fetches.
- `src/cascade_engine.py` — cascade engine that follows connections up to depth 3.
- `src/services/` — per-service code: `breach_service.py`, `people_service.py`, `spiderfoot_service.py`, `recon_service.py`, `local_leak_service.py`, `gotools_service.py`, `infra_service.py`, and the rest.
- `src/captcha_handler.py` — builds the `human_intervention_required` record and persists the paused run so `--resume` can continue it.
- `src/paths.py` — the single source of truth for project paths (`PROJECT_ROOT`, `BIN_DIR`, `VENV_PY`, data and report dirs). Import from here rather than writing an absolute path or recomputing a relative one.
- `config/settings.json` — project configuration.
- `services/agent_bridge.py` — the ports-and-adapters seam for calls that leave this process.
- `theHarvester/` — third-party tool, vendored at the PROJECT ROOT (not under `src/`). Run via the project venv.
- `Amass/` — third-party tool, vendored at the project root. Run via the project venv.
- `bin/` — vendored binaries (subfinder, httpx, amass, naabu, mosint).
- `test_system.py` — smoke test at the project root. There is no `tests/` directory.
- `data/leaks/` — cached leak database output. The directory exists but is empty and has no `.gitkeep`; nothing in it is tracked.
- `reports/` — generated markdown reports per investigation.

Runtime state (gitignored via `fork/projects/.gitignore`):

- `.venv/` — Python virtualenv. NOT present in a fresh checkout or in the image; build it once per machine via `uv venv .venv --python python3.12` then `uv pip install --python ./.venv/bin/python -e .`. The hermes runtime is Python 3.13.5; this venv is independent and pyenv supplies 3.12.
- `data/` — all investigation data, including `data/leaks/`.
- `logs/` — investigation logs.
- `*.csv` — ad-hoc exports.
- `reports/` — generated markdown reports.

## Per-investigation workflow

The agent must NEVER start an investigation without the user's explicit authorization in the same channel. The workflow:

1. User types: `investigate <entity> depth <1|2|3> format <markdown|json>`.
2. Agent confirms the target, depth, and format. Asks for clarification if any field is missing.
3. Agent makes sure the venv exists, once per machine. `.venv/` is gitignored and is not in the image, so on a fresh machine it has to be built:
    ```
    cd /opt/projects/osint && test -x ./.venv/bin/python || (uv venv .venv --python python3.12 && uv pip install --python ./.venv/bin/python -e .)
    ```
4. Agent runs the query with the venv interpreter directly. Do NOT `source .venv/bin/activate`: a tool call is not a persistent interactive shell, so the activation is gone by the next command.
    ```
    cd /opt/projects/osint && ./.venv/bin/python src/main.py --query "<entity>" [--no-cascade] [--format markdown|json]
    ```
   Exit 3 means the run paused for human intervention. Handle it as described under "Blocked services", then resume with `--resume <token>` rather than starting over.
5. Agent reads the produced report from `reports/`.
6. Agent writes the Discord-friendly summary as the FINAL RESPONSE of the turn. There is no Discord send tool: the gateway delivers the final response to the channel the turn came from. To attach the full markdown, add a line of the form `MEDIA:` followed by the report's absolute path, in plain text outside any code block, inline backticks or blockquote.
7. Agent always cites the source tool for each finding.

## Polish naming convention

- For Polish targets (names, companies), pass the name as-is to the cascade engine.
- For Polish sole proprietors (JDG), the cascade engine extracts the person name from GitHub profile data and appends it to the company name for search (e.g. "RevDev Lukukkawska Sarna" not just "RevDev"). The agent does NOT pre-format that for it.

## Cascade engine rules

Domain investigations work now. `cascade_engine.py` previously called two methods that did not exist, so a domain query returned nothing and never cascaded from a domain. Fixed: domain searches return certificate-transparency and GitHub organisation results and follow the connections they discover.

Local leak search is also fixed. `local_leak_service` passed the query to `grep` as a regular expression rather than a literal, so a dot in a domain matched any character. It now uses `grep -F`.

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

When a run hits a CAPTCHA or login wall it does NOT ask the user to "reply done in Discord". `src/main.py` exits **3** and prints a `human_intervention_required` JSON record to stdout carrying `vnc_url` and `resume_token`. The agent's job is:

1. Show the user the `vnc_url` and say what needs solving.
2. Wait with `clarify` until the user confirms they have solved it.
3. Re-invoke with the token: `./.venv/bin/python src/main.py --resume <resume_token>`.

The paused run's partial results are persisted, so `--resume` continues rather than restarting.

## Tool conventions

- For ALL web scraping, use the ascend scraper via `src/ascend_client.py`. It reads its base URL from the `ASCEND_SCRAPPER_URL` environment variable and falls back to `http://host.docker.internal:7021` when the variable is unset. NEVER use Playwright or Selenium in this project.
- For Polish JDG companies, the cascade engine handles the name extraction automatically.
- For blocked services, suggest manual workarounds via `captcha_handler.py`.

## Available data sources

Read from the container process environment (injected by `docker-compose.override.yml` from the gitignored repo-root `.env` on the host). Never create a `.env` inside this project.

Passed through to the container today:

- `HUNTER_API_KEY` — email lookup
- `VIRUSTOTAL_API_KEY` — file/URL/IP hash lookup
- `ABSTRACT_API_KEY` — email/phone validation
- `EMAILREP_API_KEY` — email reputation
- `CENSYS_API_KEY` — host/cert intel (there is no `CENSYS_SECRET`; `infra_service.py` uses the key alone)
- `BREACHDIRECTORY_VIA_RAPIDAPI_API_KEY` — credential leaks
- `ABUSEIPDB_API_KEY` — IP abuse reports
- `URLSCAN_API_KEY` — URL scans
- `OTX_API_KEY` — AlienVault OTX threat intel
- `DEHASHED_API_KEY` — breach data
- `NUMVERIFY_API_KEY` — phone validation
- `IPQS_API_KEY` — IP quality score

Read by the code but NOT wired through the override, so unset in the container and their services are skipped: `SHODAN_API_KEY`, `GITHUB_TOKEN`, `OPENCORPORATES_API_KEY`, `COMPANIES_HOUSE_API_KEY`, `GREYNOISE_API_KEY`, `SECURITYTRAILS_API_KEY`, `WHOISXML_API_KEY`, `BINARY_EDGE_API_KEY`.

## First-time setup

```bash
cd /opt/projects/osint
uv venv .venv --python python3.12
uv pip install --python ./.venv/bin/python -e .
# Smoke test
./.venv/bin/python src/main.py --query "test@example.com" --no-cascade --format markdown
```

Dependencies come from `pyproject.toml`. There is no `requirements.txt`.

## Hardcoded interpreter and data paths in `src/`

These seven files carried absolute paths from the previous runtime. All seven are
now migrated to paths derived from the file's own location via `src/paths.py`.
Keep the list as the record of what had to change, and do not reintroduce an
absolute path in any of them:

- `src/services/breach_service.py` — interpreter path for the h8mail / holehe subprocesses, plus the leaks directory.
- `src/services/people_service.py` — interpreter path, plus the data and reports output directories.
- `src/services/recon_service.py` — interpreter path, plus `PYTHONPATH` and the `theHarvester` binary path.
- `src/services/spiderfoot_service.py` — interpreter path.
- `src/services/gotools_service.py` — `BIN_DIR` and the interpreter path.
- `src/services/local_leak_service.py` — leaks directory.
- `src/captcha_handler.py` — shelled out to a CLI that does not exist here. Replaced: it now returns a `human_intervention_required` record with a `vnc_url` and a `resume_token`, and the agent surfaces the link and resumes the run.

Import paths from `src/paths.py` (`PROJECT_ROOT`, `BIN_DIR`, `VENV_PY`, the data and report dirs) rather than writing an absolute path or recomputing a relative one.

To check for regressions, run this from the project root:

```
grep -rn "/home/node" src/
```

## What this project is NOT

- It is NOT automated reconnaissance. Every investigation starts with the user's explicit authorization.
- It is NOT the gateway config. Channel behavior, API keys, and Discord settings live in `fork/hermes-config/config.yaml` on the host and in the repo-root `.env`.