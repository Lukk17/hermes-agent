# OSINT Runner — Setup Guide

This project uses a layered approach:
1. **Python packages** via pip (listed in `pyproject.toml`)
2. **Git clone tools** for tools not on PyPI (theHarvester, Amass)
3. **System tools** for things that need OS-level install

## Quick Install

```bash
cd /opt/projects/osint

# Build the venv once per machine (it is gitignored and not in the image)
uv venv .venv --python python3.12

# Install Python dependencies from pyproject.toml
uv pip install --python ./.venv/bin/python -e .
```

Invoke the venv interpreter directly (`./.venv/bin/python`). Do not rely on
`source .venv/bin/activate`: each tool call is its own shell, so the
activation does not survive to the next command.

## Tools not on PyPI

Both are ALREADY vendored in this repo. Nothing to clone.

### theHarvester
Email enumeration from 50+ sources. Vendored at `theHarvester/` (project root,
not under `src/`). It carries its own `pyproject.toml`; run it with the project
venv and its own directory on `PYTHONPATH`:

```bash
PYTHONPATH=/opt/projects/osint/theHarvester /opt/projects/osint/.venv/bin/python /opt/projects/osint/theHarvester/bin/theHarvester --help
```

### OWASP Amass
Subdomain enumeration. The Go source is vendored at `Amass/`, and a compiled
binary ships in `bin/`:

```bash
/opt/projects/osint/bin/amass -help
```

### Metagoofil
Not vendored and not currently used. Skip it.

## System-Level Tools

System packages come from `Dockerfile.fork`, which already installs the OSINT
apt dependencies (libxml2, libxslt, libpcap, nmap, masscan, tor, golang-go and
the rest). Do NOT `sudo apt install` inside the container: it runs as an
unprivileged user and anything installed at runtime is lost on the next
recreate. A missing package is a `Dockerfile.fork` change plus a rebuild, and
both are user actions.

Check what is present:

```bash
which tor nmap masscan go
```

## API Keys

There is NO `.env` file in this project and there must never be one. Anything
under `/opt/projects/` is reachable by every skill, subagent and sandbox, so a
key written there leaks across contexts.

Keys reach the code through the container's process environment:

1. The value is written to the gitignored `.env` at the repo root ON THE HOST.
2. `docker-compose.override.yml` passes it through under `gateway.environment:`
   as `- KEY=${KEY}`.
3. The code reads it with `os.getenv("KEY")`.

Adding a new key means editing both the host `.env` and the override, then
recreating the gateway. Both are user actions.

`.env.example` in this directory is a REFERENCE LIST of the key names the code
looks for. Do not copy it to `.env`.

Keys currently passed through to the container (from
`docker-compose.override.yml`):

```
HUNTER_API_KEY
ABSTRACT_API_KEY
EMAILREP_API_KEY
NUMVERIFY_API_KEY
VIRUSTOTAL_API_KEY
URLSCAN_API_KEY
OTX_API_KEY
ABUSEIPDB_API_KEY
CENSYS_API_KEY
IPQS_API_KEY
DEHASHED_API_KEY
BREACHDIRECTORY_VIA_RAPIDAPI_API_KEY
```

The code also looks for `SHODAN_API_KEY`, `GITHUB_TOKEN`,
`OPENCORPORATES_API_KEY`, `COMPANIES_HOUSE_API_KEY`, `GREYNOISE_API_KEY`,
`SECURITYTRAILS_API_KEY`, `WHOISXML_API_KEY` and `BINARY_EDGE_API_KEY`. None of
those are wired through the override today, so the services that need them are
skipped.

## Downloadable Breach Databases

See `leaks_dbs.md` for full list with torrent links.

Quick start:
```bash
mkdir -p /opt/projects/osint/data/leaks

# Common large dumps (search via torrent):
# - Collection #1 (2018) ~87GB
# - BreachCompilation (2017) ~1.4B records
# - LinkedIn 2012 (165M records)
# - Anti Public Combo List (~800M records)

# After download, search:
grep -r "target@email.com" data/leaks/
```

## Verify Installation

```bash
cd /opt/projects/osint

# Check all tools
./.venv/bin/python -c "import maigret; print('maigret OK')"
./.venv/bin/python -c "import sublist3r; print('sublist3r OK')"
./.venv/bin/python -c "import h8mail; print('h8mail OK')"
./.venv/bin/python -c "import holehe; print('holehe OK')"
./.venv/bin/python -c "import socialscan; print('socialscan OK')"
./.venv/bin/python -c "import ghunt; print('ghunt OK')"
./.venv/bin/python -c "import photon; print('photon OK')"
./.venv/bin/python -c "import wappalyzer; print('wappalyzer OK')"
./.venv/bin/python -c "import stem; print('stem OK')"
./.venv/bin/python -c "import requests; print('requests OK')"
./.venv/bin/python -c "import aiohttp; print('aiohttp OK')"
./.venv/bin/python -c "import scapy; print('scapy OK')"
./.venv/bin/python -c "import dns; print('dnspython OK')"

# Check git clone tools
ls theHarvester/ 2>/dev/null && echo "theHarvester cloned OK"
ls Amass/ 2>/dev/null && echo "Amass cloned OK"

# Check system tools
which tor && echo "tor OK"
which nmap && echo "nmap OK"
```

## Running the OSINT Runner

```bash
cd /opt/projects/osint

# Basic cascade (auto-follows connections)
./.venv/bin/python src/main.py --query "Jan Kowalski"

# One-shot (no cascade)
./.venv/bin/python src/main.py --query "Jan Kowalski" --no-cascade

# Specific search
./.venv/bin/python src/main.py --query "email:target@gmail.com"
./.venv/bin/python src/main.py --query "NIP:5261040828"
./.venv/bin/python src/main.py --query "KRS:0000123456"
./.venv/bin/python src/main.py --query "domain:example.com"

# Markdown output
./.venv/bin/python src/main.py --query "Jan Kowalski" --format markdown
```

## Project Structure

```
osint/
├── src/
│   ├── main.py              # CLI entry point
│   ├── models.py            # Pydantic models
│   ├── cascade_engine.py    # Cascade search engine
│   ├── connections.py       # Connection types
│   ├── ascend_client.py     # Web scraper wrapper
│   ├── report_renderer.py   # Report output
│   └── services/            # All API services
│       ├── base_service.py
│       ├── email_service.py
│       ├── phone_service.py
│       ├── people_service.py
│       ├── company_service.py
│       ├── domain_service.py
│       ├── github_service.py
│       ├── breach_service.py
│       ├── social_service.py
│       └── local_leak_service.py
├── docs/                    # Source documentation
├── data/leaks/              # Downloaded breach DBs
├── theHarvester/            # Git cloned: email enum
├── Amass/                   # Git cloned: subdomain enum
├── pyproject.toml           # Python dependencies
├── .env.example             # Reference list of key names (never copied to .env)
└── .venv/                   # Python 3.12 venv (gitignored, built per machine)
```
