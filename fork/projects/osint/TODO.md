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

### Services Still Failing

| Service | Status | Next Action |
|---------|--------|-------------|
| rejestr_io | DNS blocked in container | Host-only; add note to README |
| opencorporates | 401 no API key | Add clearer message + check for key |
| CEIDG | Playwright fails (libasound2 missing) | System dep; document |
| KRS Online | Playwright fails (libasound2 missing) | System dep; document |
| eKRS | HTTP timeout (8s) | Try longer timeout |
| OpenCorporates | No free tier | Add API key check |

### Completed

- [x] Python 3.12.13 venv
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
- JavaScript rendering (CEIDG, KRS, eKRS via Playwright)
- Missing system library (Playwright chromium)

Options:
- Install libasound2 on host (needs root)
- Use host machine with browser access
- Find alternative API (GUS REGON has API but requires registration)

### 3. OpenCorporates
No free tier. Options:
- Add API key (register at opencorporates.com)
- Use alternative: Crunchbase (paid), Companies House (UK only), SEC EDGAR (US only)

---

## Go Tools Usage

```bash
# Amass — passive subdomain enum
/home/node/.openclaw/workspace/osint/bin/amass enum -passive -silent -d example.com -o /tmp/amass_out.txt

# Subfinder — fast subdomain discovery
HOME=/tmp /home/node/.openclaw/workspace/osint/bin/subfinder -d example.com -silent -sources publicwww -o /tmp/sf_out.txt

# httpx — HTTP probing
echo "http://example.com" > /tmp/hosts.txt && /home/node/.openclaw/workspace/osint/bin/httpx -list /tmp/hosts.txt -silent

# Mosint — email OSINT (needs config at $HOME/.mosint.yaml)
/home/node/.openclaw/workspace/osint/bin/mosint test@gmail.com -s -o /tmp/out.json

# Naabu — port scan
/home/node/.openclaw/workspace/osint/bin/naabu -host example.com -silent -rate 100
```

## theHarvester Usage
```bash
PYTHONPATH=/home/node/.openclaw/workspace/osint/theHarvester \
  /home/node/.openclaw/workspace/osint/.venv/bin/python3 \
  /home/node/.openclaw/workspace/osint/theHarvester/bin/theHarvester \
  -d example.com -b duckduckgo -f /tmp/out.json
```

## Recon-ng Usage
```bash
PYTHONPATH=/tmp/recon-ng \
  /home/node/.openclaw/workspace/osint/.venv/bin/python3 \
  /tmp/recon-ng/recon-cli
```

---

## System Dependencies Missing

### libasound2 (alsa sound library)
Required by: Playwright chromium browser

Error: "libasound.so.2: cannot open shared object file"

Fix: Install on host system (needs root)
```bash
sudo apt-get install libasound2
```

Without this, Playwright-based services (CEIDG, KRS, eKRS via browser) will fail.
