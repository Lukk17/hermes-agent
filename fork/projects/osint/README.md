# OSINT Research Tool

Automated OSINT runner for person and company investigations with cascade mode. Takes structured input, queries multiple sources in parallel, follows connections, outputs a markdown report.

Tested subject: **Łukasz Sarna** (Warsaw, Java Developer, RevDev JDG owner)

---

## Quick Start

The project venv is gitignored and is NOT in the image. Build it once per
machine, then call its interpreter directly. Do not `source
.venv/bin/activate`: every tool call is its own shell, so the activation is
gone by the next command.

```bash
cd /opt/projects/osint
```

Build the venv if `.venv/` is missing:

```bash
uv venv .venv --python python3.12 && uv pip install --python ./.venv/bin/python -e .
```

Then:

```bash
# Cascade mode (auto-follows connections up to depth 3)
./.venv/bin/python src/main.py --query "Łukasz Sarna" --format markdown

# One-shot mode (no cascade)
./.venv/bin/python src/main.py --query "Łukasz Sarna" --no-cascade

# Resume a run that paused for a CAPTCHA
./.venv/bin/python src/main.py --resume <resume_token>

# Specific types
./.venv/bin/python src/main.py --query "email:target@gmail.com"
./.venv/bin/python src/main.py --query "NIP:5261040828"
./.venv/bin/python src/main.py --query "KRS:0000123456"
./.venv/bin/python src/main.py --query "domain:example.com"
./.venv/bin/python src/main.py --query "linkedin:https://linkedin.com/in/target"

# Output formats
./.venv/bin/python src/main.py --query "Łukasz Sarna" --format json
```

---

## Input Types (auto-detected)

- **Name** — `Jan Kowalski` or `name:Jan Kowalski` (multi-word)
- **Email** — `jan@example.com` or `email:jan@example.com`
- **Phone** — `+48123456789` or `phone:+48123456789`
- **NIP** — `5252341234` or `NIP:5252341234`
- **KRS** — `0000123456` or `KRS:0000123456`
- **Domain** — `example.com` or `domain:example.com`
- **LinkedIn** — full URL or `linkedin:username`
- **Plate** — `AB1234CD` (Polish)
- **VIN** — `WVWZZZ3CZWE123456`

---

## Cascade Engine

The cascade engine automatically follows connections discovered during search:

```
Depth 0: Search "Łukasz Sarna" by name
         → Found: GitHub profile (Lukk17, RevDev company), BoardGameGeek

Depth 1: Scrape GitHub profile
         → Found: company "RevDev", blog "www.linkedin.com/in/luksarna/"

Depth 2: Search company "RevDev Łukasz Sarna" (Polish JDG naming)
         → Found: court cases, SEC EDGAR (0 hits), KRS, CEIDG, opencorporates

Depth 2: Search domain "www.linkedin.com/in/luksarna/"
         → Skipped (Go tools: social media blocks enumeration)
```

Rules:
- Only follows **subject-owned** connections (own emails, domains, profiles)
- **Coworkers/employees** are listed passively but NOT searched
- Max 3 depth levels, max 5 connections per search
- Go tools (amass/subfinder) are skipped for social media domains (LinkedIn, Facebook, Twitter, Instagram, TikTok)

### Polish JDG Naming

In Poland, sole proprietors (JDG - Jednoosobowa Działalność Gospodarcza) are registered under a combination of:
- Company name (often a brand/name) + person name and surname
- Example: "RevDev Łukasz Sarna" not just "RevDev"

The cascade engine extracts the person name from GitHub profile data and passes it to company search as "RevDev Łukasz Sarna" for better accuracy.

---

## Installed Tools

### Python 3.12 Tools (pip / .venv)

```
maigret             — Username search across 1000+ sites
sherlock-project    — Username search (alternative)
holehe              — Check if email is registered on platforms
socialscan          — Username availability check
sublist3r           — Subdomain enumeration
photon              — Web crawler + OSINT (images, docs, URLs)
wappalyzer          — Web technology fingerprinting
ghunt               — Google account OSINT (email → profiles, photos)
h8mail              — Breach hunting (local files + remote APIs)
stem                — Tor controller (dark web)
torrequest          — HTTP over Tor
scapy               — Network packet crafting
dnspython           — DNS queries
python-whois        — WHOIS lookups
maxminddb           — GeoIP database
pdfminer.six        — PDF metadata extraction
cloudscraper        — Cloudflare bypass
aiohttp             — Async HTTP
censys              — Censys.io certificates
shodan              — Shodan API
playwright          — Browser automation (NOT USED - use ascend scraper instead)
uvloop              — Fast async event loop
```

### Go Tools (compiled, in `bin/`)

```
amass               — Passive subdomain enumeration (OWASP)
subfinder           — Fast subdomain discovery (ProjectDiscovery)
httpx               — HTTP probing / tech detection
naabu               — Port scanning
mosint              — Email OSINT aggregator
```

### Manually Installed

```
theHarvester/       — Email enumeration from 50+ sources
recon-ng/           — Full recon framework
```

---

## Project Structure

```
osint/
├── src/
│   ├── main.py              — CLI entry point
│   ├── models.py            — Data models
│   ├── cascade_engine.py    — Cascade search engine (auto-follow connections)
│   ├── connections.py       — Connection type definitions
│   ├── ascend_client.py     — Web scraper (ascend service, $ASCEND_SCRAPPER_URL)
│   ├── report_renderer.py   — Markdown/JSON output
│   └── services/
│       ├── base_service.py   — Shared async HTTP
│       ├── email_service.py  — Email discovery services
│       ├── phone_service.py  — Phone lookup services
│       ├── people_service.py — Maigret, Sherlock
│       ├── company_service.py — Company registries (Polish JDG, SEC EDGAR, etc.)
│       ├── polish_gov_service.py — CEIDG, KRS, eKRS, REGON, KRD, rejestr.io
│       ├── domain_service.py  — Domain WHOIS, SSL certs, DNS
│       ├── github_service.py  — GitHub API
│       ├── gotools_service.py — Amass, Subfinder, httpx, naabu, mosint
│       ├── breach_service.py  — Breach lookup services
│       ├── social_service.py  — Social media scraping
│       ├── spiderfoot_service.py — SpiderFoot integration
│       ├── infra_service.py   — IP/WHOIS/DNS
│       ├── recon_service.py   — Photon, Sublist3r, theHarvester
│       └── darkweb_service.py — Ahmia, OnionSearch
├── bin/                     — Go tool binaries
├── data/leaks/              — Downloaded breach databases
├── theHarvester/            — Email enumeration
├── recon-ng/                — Recon framework
├── pyproject.toml           — Python dependencies
├── .venv/                   — Python 3.12 virtual environment
└── .env.example             — API key template
```

---

## Environment Variables (API Keys)

NEVER create a `.env` in this directory. Keys arrive in the container's process
environment: the gitignored repo-root `.env` on the host feeds
`docker-compose.override.yml`, which passes each key through under
`gateway.environment:`. The code reads them with `os.getenv("KEY")`.
`.env.example` here is a reference list of key names, nothing more.

Key names the code actually reads:

```
HUNTER_API_KEY           # hunter.io (domain → email search)
SHODAN_API_KEY           # shodan.io (infra, IP)
VIRUSTOTAL_API_KEY       # virustotal.com (domains, IPs)
GITHUB_TOKEN             # github.com (rate limit boost)
ABSTRACT_API_KEY         # abstractapi.com (email + phone verification)
CENSYS_API_KEY           # censys.io (SSL certificates)
BREACHDIRECTORY_VIA_RAPIDAPI_API_KEY  # breachdirectory.org via RapidAPI
ABUSEIPDB_API_KEY        # abuseipdb.com (IP reputation)
URLSCAN_API_KEY          # urlscan.io (domain analysis)
OTX_API_KEY              # alienvault.com (threat intel)
DEHASHED_API_KEY         # dehashed.com (breach search)
OPENCORPORATES_API_KEY   # opencorporates.com (company search, no free tier)
COMPANIES_HOUSE_API_KEY  # companieshouse.gov.uk (UK companies)
NUMVERIFY_API_KEY        # numverify.com (phone validation)
IPQS_API_KEY             # ipqualityscore.com (phone/email)
```

Of those, the override currently passes through `HUNTER_API_KEY`,
`ABSTRACT_API_KEY`, `EMAILREP_API_KEY`, `NUMVERIFY_API_KEY`,
`VIRUSTOTAL_API_KEY`, `URLSCAN_API_KEY`, `OTX_API_KEY`, `ABUSEIPDB_API_KEY`,
`CENSYS_API_KEY`, `IPQS_API_KEY`, `DEHASHED_API_KEY` and
`BREACHDIRECTORY_VIA_RAPIDAPI_API_KEY`. The rest are unset in the container and
their services are skipped.

There is no `CENSYS_SECRET`. `infra_service.py` authenticates with
`CENSYS_API_KEY` alone.

### Check which keys are set

```bash
env | grep -E "HUNTER|SHODAN|VIRUSTOTAL|GITHUB|ABSTRACT|CENSYS|BREACH|ABUSE|URLSCAN|OTX|DEHASHED|OPENCORP|COMPANIES|NUMVERIFY|IPQS" | sed 's/=.*/=<SET>/'
```

---

## Service Status

### Working Services

| Service | Type | Status | Notes |
|---------|------|--------|-------|
| Maigret | Username | WORKING | 1000+ sites |
| Sherlock | Username | WORKING | Alternative username search |
| SpiderFoot | Multi-source | WORKING | 200+ modules |
| GitHub User Search | Username | WORKING | Finds user data + company |
| GitHub User Profile | Username | WORKING | Full profile data (name, bio, blog, followers) |
| Domain WHOIS | Domain | WORKING | Domain ownership |
| Domain SSL Certs | Domain | WORKING | crt.sh, Censys |
| VirusTotal | Domain/IP | WORKING | With API key |
| Hunter.io | Domain/Email | WORKING | With API key |
| Shodan | IP | WORKING | With API key |
| CertSpotter | Domain | WORKING | SSL certificate search |
| BreachDirectory | Email | WORKING | With API key |
| AbuseIPDB | IP | WORKING | With API key |
| URLScan | Domain | WORKING | With API key |
| OTX (AlienVault) | Domain | WORKING | With API key |
| theHarvester | Email | WORKING | DuckDuckGo, Google, Baidu |
| Photon | Domain | WORKING | Crawls site for emails, URLs, files |
| Sublist3r | Domain | WORKING | Subdomain enumeration |
| Amass | Domain | WORKING | Passive subdomain enum (skipped for social media) |
| Subfinder | Domain | WORKING | Fast subdomain discovery |
| Courts (MS Gov PL) | Company | WORKING | Polish court case search (searches "RevDev Łukasz Sarna") |
| SEC EDGAR | Company | WORKING | US company filings search |

### Blocked Services (Access/Environment)

| Service | Root Cause | Workaround |
|---------|-----------|-----------|
| rejestr.io | `api.rejestr.io` returns CAPTCHA even from host machine | Access manually via browser |
| OpenCorporates | No free tier - API requires key | Add `OPENCORPORATES_API_KEY` |
| CEIDG | Requires ASP.NET ViewState form POST (JS rendering) | Browser automation or API |
| KRS Online | Requires JS rendering for search results | Browser automation or API |
| eKRS | Returns CAPTCHA via ascend scraper | Manual resolution via VNC |
| LinkedIn | Blocks all scrapers, needs official API | Use Maigret/Sherlock instead |
| Google Social Search | CAPTCHA | Use Maigret/Sherlock instead |
| Twitter/X Advanced | Requires JavaScript | Use Maigret/Sherlock instead |
| CertSpotter (on LinkedIn URLs) | HTTP 403 | Skip - social domain blocked by design |
| TruePeopleSearch | CAPTCHA | Use Maigret instead |
| FastPeopleSearch | CAPTCHA | Use Maigret instead |

### Blocked Services (Missing/Invalid API Keys)

| Service | Status | Fix |
|---------|--------|-----|
| HIBP | Needs paid key or `breachdirectory` | Use BreachDirectory instead |
| Abstract API | Key returns 401 | Verify key is correct |
| EmailRep | DNS cannot resolve `api.emailrep.io` | Network issue |
| Hudson Rock | DNS cannot resolve host | Network issue |
| EPIEOS | API returns 403/404 | Service may be down |

---

## Cascade Engine Details

### Connection Types

The cascade engine recognizes these connection types and follows them:

**Subject-owned (follows automatically):**
- `person_email` — Own email addresses
- `person_company` — Own company affiliations (from GitHub profile)
- `person_domain` — Own blog/website
- `person_phone` — Own phone numbers
- `person_profile` — Own social profiles

**Company-owned (follows automatically):**
- `company_domain` — Company website domain
- `company_subdomain` — Company subdomains
- `company_nip` — Company NIP (tax ID)
- `company_krs` — Company KRS number
- `company_github_org` — Company GitHub organization

**Passive only (listed, not searched):**
- `other_profile` — Other profiles found (repos, etc.)
- `coworker` — Colleagues/employees (not searched)

### Polish JDG Search Fix

When a GitHub profile contains a company field, the cascade engine:
1. Extracts the person name from the GitHub profile (e.g., "Łukasz Sarna")
2. Appends it to the company name for Polish company search (e.g., "RevDev Łukasz Sarna")
3. This produces more accurate results for Polish sole proprietors (JDG)

---

## System Dependencies

### Python 3.12
Provided by pyenv inside the container (`PYENV_ROOT=/opt/pyenv`, on `PATH` via
`/opt/pyenv/shims`). The Dockerfile installs the latest 3.11 and 3.12 patch
releases, so do not hardcode a patch number. Build this project's venv against
3.12: `uv venv .venv --python python3.12`.

### Ascend Web Scraper (PRIMARY SCRAPING TOOL)

`src/ascend_client.py` reads the base URL from the `ASCEND_SCRAPPER_URL`
environment variable and falls back to `http://host.docker.internal:7021` when
it is unset. The endpoint it calls is `<base>/api/v2/web/read`. All web
scraping goes through this client.

Never use Playwright or Selenium for scraping in this project - always use ascend_client.

If the scraper hits a CAPTCHA or login wall, `src/main.py` exits **3** and prints a `human_intervention_required` JSON record to stdout with `vnc_url` and `resume_token`. Open the `vnc_url`, solve it, then continue the same run:

```bash
./.venv/bin/python src/main.py --resume <resume_token>
```

The partial results are persisted, so this resumes rather than restarts.

### Go Tools

Located in `bin/`:
```
amass v3.23.3       # Passive subdomain enum
subfinder v2.5.2    # Active subdomain discovery  
httpx v1.2.6        # HTTP probing
naabu v2.1.4        # Port scanning
mosint              # Email OSINT
```

---

## Troubleshooting

### "Command not found" errors
```bash
./.venv/bin/python --version
```

Expect a 3.12 build. If the venv is missing, rebuild it with the Quick Start
commands above.

### "API key not set" warnings
These are expected if keys aren't configured. Services using those keys will be skipped.

### Polish company search returns empty results
CEIDG, KRS Online, and eKRS require JavaScript rendering (ASP.NET ViewState form POST). The ascend scraper accesses them but cannot submit search forms without CAPTCHA resolution. These services work when the ascend scraper successfully resolves CAPTCHA, otherwise they return the landing page.

Court case search (MS Gov PL) works reliably as an alternative for finding Polish company information.

### Go tools skip on LinkedIn
This is intentional. LinkedIn blocks subdomain enumeration tools.

---

## Free API Services Guide

See `free_with_api.md` for 50+ free API services with setup instructions.

## Breach Database Downloads

See `leaks_dbs.md` for downloadable breach databases to search locally with `h8mail`.

## Architecture

See `ARCHITECTURE.md` for system diagram and component overview.

---

## Legal Notice

For authorized security research and OSINT investigations only. Ensure proper authorization before investigating any target. Always comply with applicable laws and source terms of service.
