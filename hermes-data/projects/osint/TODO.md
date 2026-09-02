# OSINT Runner — TODO

## Status (2026-05-07)

### Pipeline Test for "Łukasz Sarna"
- Full cascade (Depth 0 → Depth 1 → Depth 2) RUNNING
- GitHub profile data RENDERING correctly
- BoardGameGeek profile RENDERING correctly
- Go tools (amass/subfinder) SKIPPING social media domains correctly
- SEC EDGAR FIXED (proper User-Agent)
- Polish JDG naming FIXED (searches "RevDev Łukasz Sarna" not just "RevDev")
- OpenCorporates API version FIXED (was `v0.04`, now `v0.4.8`)

### Recently Fixed

- Domain investigations: `cascade_engine.py` called two methods that do not exist, so a domain query produced no results and never cascaded. Domain searches now return certificate-transparency and GitHub organisation results.
- Local leak search: the query was passed to `grep` as a regex rather than a literal, so a dot in a domain matched any character. Now uses `grep -F`.
- CAPTCHA handling: replaced the old "reply done in Discord" flow with exit 3 plus a `human_intervention_required` record and a `--resume <token>` continuation.

### Services Still Failing

| Service | Status | Next Action |
|---------|--------|-------------|
| rejestr_io | DNS blocked in container | Host-only; add note to README |
| opencorporates | 401 no API key | Add clearer message + check for key |
| CEIDG | Needs a JS-rendered form POST; ascend scraper returns the landing page | No browser automation in this project; find an API or do it manually |
| KRS Online | Needs JS rendering for search results | Same as CEIDG |
| eKRS | HTTP timeout (8s) | Try longer timeout |
| OpenCorporates | No free tier | Add API key check |

### Completed

- [ ] Python 3.12 venv — `.venv/` is gitignored and is NOT in the image. It has to be built once per machine: `uv venv .venv --python python3.12 && uv pip install --python ./.venv/bin/python -e .`
- [x] All pip tools installed
- [x] All Go tools in bin/
- [x] Cascade engine with Go tools
- [x] Markdown report renderer
- [x] GitHub profile data rendering
- [x] Polish JDG naming (person name passed through)
- [x] SEC EDGAR User-Agent fix
- [x] OpenCorporates API version fix
- [x] README.md comprehensive documentation
- [x] Go tools skip for social media domains

---

## Remaining Issues to Investigate

### 1. eKRS Timeout
eKRS search times out after 8 seconds. Could try:
- Increase timeout to 15s
- Try POST-based search instead of GET
- Use ascend scraper with longer timeout

### 2. Polish Government Sites
All blocked by:
- CAPTCHA (rejestr.io via ascend)
- JavaScript rendering and ASP.NET ViewState form POSTs (CEIDG, KRS, eKRS)

Options:
- Let the ascend scraper's CAPTCHA escalation resolve it, then retry
- Ask the user to open the URL in their own browser and paste the result back
- Find an alternative API (GUS REGON has one, but it requires registration)

Playwright is NOT an option. This project bans Playwright and Selenium
outright; ascend is the only scraping path.

### 3. OpenCorporates
No free tier. Options:
- Add API key (register at opencorporates.com)
- Use alternative: Crunchbase (paid), Companies House (UK only), SEC EDGAR (US only)

---

## Go Tools Usage

```bash
# Amass — passive subdomain enum
/opt/data/projects/osint/bin/amass enum -passive -silent -d example.com -o /tmp/amass_out.txt

# Subfinder — fast subdomain discovery
HOME=/tmp /opt/data/projects/osint/bin/subfinder -d example.com -silent -sources publicwww -o /tmp/sf_out.txt

# httpx — HTTP probing
echo "http://example.com" > /tmp/hosts.txt && /opt/data/projects/osint/bin/httpx -list /tmp/hosts.txt -silent

# Mosint — email OSINT (needs config at $HOME/.mosint.yaml; HOME is /opt/data)
/opt/data/projects/osint/bin/mosint test@gmail.com -s -o /tmp/out.json

# Naabu — port scan
/opt/data/projects/osint/bin/naabu -host example.com -silent -rate 100
```

## theHarvester Usage
```bash
PYTHONPATH=/opt/data/projects/osint/theHarvester /opt/data/projects/osint/.venv/bin/python /opt/data/projects/osint/theHarvester/bin/theHarvester -d example.com -b duckduckgo -f /tmp/out.json
```

## Recon-ng Usage
```bash
PYTHONPATH=/tmp/recon-ng /opt/data/projects/osint/.venv/bin/python /tmp/recon-ng/recon-cli
```

recon-ng is not vendored in this repo and `/tmp/recon-ng` does not exist in a
fresh container. Clone it first, or skip it.

---

## System Dependencies

System packages are baked into the image by `Dockerfile.fork`, not installed at
runtime. The container runs as an unprivileged user and any `apt-get install`
inside it is lost on the next recreate, so a missing package is a Dockerfile
change plus a rebuild, both user actions.

There is no outstanding system dependency. The old libasound2 entry existed
only for Playwright chromium, and Playwright is banned in this project.
