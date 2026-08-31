# OSINT Runner — Setup Guide

This project uses a layered approach:
1. **Python packages** via pip (listed in `pyproject.toml`)
2. **Git clone tools** for tools not on PyPI (theHarvester, Amass)
3. **System tools** for things that need OS-level install

## Quick Install

```bash
cd /home/node/.openclaw/workspace/osint

# Install Python dependencies from pyproject.toml
.venv/bin/pip install -e .

# Or use the lock file approach
pip install pip-tools
pip-compile pyproject.toml
pip-sync
```

## Manual Installs (Required — Not on PyPI)

### theHarvester
Email enumeration from 50+ sources (Google, Bing, LinkedIn, etc.)
```bash
git clone https://github.com/laramies/theHarvester.git
cd theHarvester
pip install -r requirements.txt
python theHarvester.py --help
```
Location in project: `./theHarvester/`

### OWASP Amass
Comprehensive subdomain enumeration (active + passive)
```bash
git clone https://github.com/OWASP/Amass.git
cd Amass
# Requires Go to build: https://go.dev/doc/install
go build ./...
# Binary: ./amass
```
Location in project: `./Amass/`

### Metagoofil (Optional/Old)
Document metadata extractor
```bash
git clone https://github.com/opsdisk/metagoofil.git
cd metagoofil
pip install -r requirements.txt
python metagoofil.py --help
```

## System-Level Tools (Recommended)

```bash
# Install via apt (Debian/Ubuntu/WSL)
sudo apt install golang-go    # For Amass build
sudo apt install tor          # For dark web
sudo apt install nmap         # For port scanning
sudo apt install masscan      # For fast port scanning
sudo apt install theHarvester  # Sometimes available via apt
sudo apt install recon-ng     # Recon framework (if available)

# For WSL2 with Kali/Parrot
# Add Kali repo and: sudo apt install amass theharvester recon-ng
```

## API Keys to Collect

Copy `.env.example` from `free_with_api.md` and fill in:

```bash
# Create .env file
cat > /home/node/.openclaw/workspace/osint/.env << 'EOF'
# Email Discovery & Validation
HUNTER_API_KEY=
HIBP_API_KEY=
EMAIL_HIPPO_API_KEY=
ABSTRACT_EMAIL_API_KEY=
ZEROBOUNCE_API_KEY=

# Phone Validation
NUMVERIFY_API_KEY=
ABSTRACT_PHONE_API_KEY=

# People Search
SNOV_API_KEY=
CLEARBIT_API_KEY=
FULLCONTACT_API_KEY=

# Infrastructure
SHODAN_API_KEY=
SECURITYTRAILS_API_KEY=
WHOISXML_API_KEY=
VIRUSTOTAL_API_KEY=
URLSCAN_API_KEY=
OTX_API_KEY=
GREYNOISE_API_KEY=
ABUSEIPDB_API_KEY=
RISKIQ_API_KEY=
BINARY_EDGE_API_KEY=
CENSYS_API_KEY=

# Breach Data
LEAKCHECK_API_KEY=
DEHASHED_API_KEY=
SNUSBASE_API_KEY=
BREACHDIRECTORY_API_KEY=

# Code Search
GITHUB_TOKEN=
GREP_APP_API_KEY=
EOF
```

## Downloadable Breach Databases

See `leaks_dbs.md` for full list with torrent links.

Quick start:
```bash
mkdir -p /home/node/.openclaw/workspace/osint/data/leaks

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
cd /home/node/.openclaw/workspace/osint

# Check all tools
.venv/bin/python3 -c "import maigret; print('maigret OK')"
.venv/bin/python3 -c "import sublist3r; print('sublist3r OK')"
.venv/bin/python3 -c "import h8mail; print('h8mail OK')"
.venv/bin/python3 -c "import holehe; print('holehe OK')"
.venv/bin/python3 -c "import socialscan; print('socialscan OK')"
.venv/bin/python3 -c "import ghunt; print('ghunt OK')"
.venv/bin/python3 -c "import photon; print('photon OK')"
.venv/bin/python3 -c "import wappalyzer; print('wappalyzer OK')"
.venv/bin/python3 -c "import stem; print('stem OK')"
.venv/bin/python3 -c "import requests; print('requests OK')"
.venv/bin/python3 -c "import aiohttp; print('aiohttp OK')"
.venv/bin/python3 -c "import scapy; print('scapy OK')"
.venv/bin/python3 -c "import dns; print('dnspython OK')"

# Check git clone tools
ls theHarvester/ 2>/dev/null && echo "theHarvester cloned OK"
ls Amass/ 2>/dev/null && echo "Amass cloned OK"

# Check system tools
which tor && echo "tor OK"
which nmap && echo "nmap OK"
```

## Running the OSINT Runner

```bash
cd /home/node/.openclaw/workspace/osint

# Basic cascade (auto-follows connections)
.venv/bin/python3 src/main.py --query "Jan Kowalski"

# One-shot (no cascade)
.venv/bin/python3 src/main.py --query "Jan Kowalski" --no-cascade

# Specific search
.venv/bin/python3 src/main.py --query "email:target@gmail.com"
.venv/bin/python3 src/main.py --query "NIP:5261040828"
.venv/bin/python3 src/main.py --query "KRS:0000123456"
.venv/bin/python3 src/main.py --query "domain:example.com"

# Markdown output
.venv/bin/python3 src/main.py --query "Jan Kowalski" --format markdown
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
└── .env                     # API keys (create from free_with_api.md)
```
