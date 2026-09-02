# Free Services with API Access

Services that have a free tier or free API key registration.

## Setup

Never create a `.env` in this project. Add the key to the gitignored `.env` at
the repo root ON THE HOST, then add a matching `- KEY=${KEY}` line under
`gateway.environment:` in `docker-compose.override.yml`, then recreate the
gateway. Both are user actions. The code reads the value with
`os.getenv("KEY")`.

## Environment Variables Reference

The block below is a reference list of key names, not a file to create.

```bash
# ===== Email Discovery & Validation =====
HUNTER_API_KEY=           # hunter.io - 25 searches/month
HIBP_API_KEY=             # haveibeenpwned.com - free, get from https://haveibeenpwned.com/api
EMAIL_HIPPO_API_KEY=      # emailhippo.com - limited free lookups
ABSTRACT_EMAIL_API_KEY=   # abstractapi.com - 100/month email validation
ZEROBOUNCE_API_KEY=       # zerobounce.net - 100/month
EMAILREP_API_KEY=         # emailrep.io - free, no key needed for basic

# ===== Phone Validation =====
NUMVERIFY_API_KEY=        # numverify.com - 100/month
ABSTRACT_PHONE_API_KEY=   # abstractapi.com - 100/month phone validation

# ===== People Search =====
SNOV_API_KEY=             # snov.io - 50 credits/month email finder
CLEARBIT_API_KEY=         # clearbit.com - 5000/month enrichment
FULLCONTACT_API_KEY=      # fullcontact.com - limited free tier

# ===== Domain & Infrastructure =====
SHODAN_API_KEY=           # shodan.io - very limited free tier
SECURITYTRAILS_API_KEY=   # securitytrails.com - limited free
WHOISXML_API_KEY=         # whoisxmlapi.com - limited free
VIRUSTOTAL_API_KEY=       # virustotal.com - limited free
URLSCAN_API_KEY=          # urlscan.io - free tier
OTX_API_KEY=              # alienvault.com - free tier
GREYNOISE_API_KEY=        # greynoise.io - 100 queries/day
ABUSEIPDB_API_KEY=        # abuseipdb.com - 1000 lookups/day
RISKIQ_API_KEY=           # riskiq.com - community edition limited
BINARY_EDGE_API_KEY=      # binaryedge.io - limited free
CENSYS_API_KEY=           # censys.io - limited free

# ===== Breach & Leak Databases =====
LEAKCHECK_API_KEY=        # leakcheck.io - limited free
DEHASHED_API_KEY=         # dehashed.com - very limited free
SNUSBASE_API_KEY=         # snusbase.com - limited free
BREACHDIRECTORY_API_KEY=  # breachdirectory.org - limited free

# ===== GitHub & Code Search =====
GITHUB_TOKEN=             # github.com - optional, increases rate limit
GREP_APP_API_KEY=         # grep.app - limited free code search

# ===== Social Media & Username =====
SNCAST_API_KEY=           # sncast.py四 - optional

# ===== Misc =====
IPQS_API_KEY=             # ipqualityscore.com - 5000/month
CRXCAVATOR_API_KEY=       # crxcavator.io - limited
```

---

## Email Discovery & Validation

### Hunter.io
**Purpose:** Email pattern finder for domains, email verifier, source finder
**Free tier:** 25 searches/month (domain search), 50 verifications/month
**API Key:** `HUNTER_API_KEY`
**Signup:** https://hunter.io/api
**Docs:** https://hunter.io/api/docs

### HaveIBeenPwned
**Purpose:** Check if email/phone appears in data breaches
**Free tier:** Full email search (rate limited), password search via k-Anonymity (free)
**API Key:** `HIBP_API_KEY` (free, get from https://haveibeenpwned.com/api)
**Note:** Requires User-Agent header. Paid tier for advanced queries.

### Email Hippo
**Purpose:** Email validation and verification
**Free tier:** Limited free lookups
**API Key:** `EMAIL_HIPPO_API_KEY`
**Signup:** https://emailhippo.com

### Abstract API — Email Validation
**Purpose:** Email validation service
**Free tier:** 100 requests/month
**API Key:** `ABSTRACT_EMAIL_API_KEY`
**Signup:** https://app.abstractapi.com/api/email-validation-validation-api

### ZeroBounce
**Purpose:** Email validation with bounce scoring
**Free tier:** 100 requests/month
**API Key:** `ZEROBOUNCE_API_KEY`
**Signup:** https://www.zerobounce.net

### EmailRep
**Purpose:** Email reputation and suspicious indicator scoring
**Free tier:** Free, no key required (but rate limited)
**No API key needed** — uses `https://emailrep.io/{email}`
**Signup:** https://emailrep.io

### Snov.io
**Purpose:** Email finder and verifier, domain to emails
**Free tier:** 50 credits/month
**API Key:** `SNOV_API_KEY`
**Signup:** https://snov.io

---

## Phone Validation

### NumVerify
**Purpose:** Phone number validation and geolocation
**Free tier:** 100 requests/month via public API (no key required for limited)
**API Key:** `NUMVERIFY_API_KEY`
**Signup:** https://numverify.com

### Abstract API — Phone Validation
**Purpose:** International phone number validation
**Free tier:** 100 requests/month
**API Key:** `ABSTRACT_PHONE_API_KEY`
**Signup:** https://app.abstractapi.com/api/phone-number-validation-and-lookup-api

---

## People Search & Enrichment

### Clearbit
**Purpose:** Email to person/company enrichment, logo, social links
**Free tier:** 5,000 requests/month via RapidAPI
**API Key:** `CLEARBIT_API_KEY`
**Signup:** https://clearbit.com

### FullContact
**Purpose:** Email to social profiles, company enrichment, name normalization
**Free tier:** Limited free lookups
**API Key:** `FULLCONTACT_API_KEY`
**Signup:** https://www.fullcontact.com

### FastPeopleSearch
**Purpose:** Free people lookup (US focused)
**Scrape via ascend scrapper:** `https://www.fastpeoplesearch.com/name-lookup`
**Free tier:** Yes, limited

### TruePeopleSearch
**Purpose:** Free people search by name, phone, address
**Scrape via ascend:** `https://www.truepeoplesearch.com/results?name=...`
**Free tier:** Yes, limited

### ThatsThem.com
**Purpose:** Free email/phone/address lookup
**Scrape via ascend:** `https://thatsthem.com/`
**Free tier:** Yes

---

## Domain & Infrastructure Recon

### Shodan
**Purpose:** Internet scanner, port enumeration, SSL data, vulnerability detection
**Free tier:** Very limited (100 results, no API access for some features)
**API Key:** `SHODAN_API_KEY`
**Signup:** https://account.shodan.io/register

### SecurityTrails
**Purpose:** Historical DNS, WHOIS history, subdomain enumeration
**Free tier:** Limited DNS queries
**API Key:** `SECURITYTRAILS_API_KEY`
**Signup:** https://securitytrails.com

### WhoisXML API
**Purpose:** WHOIS database, historical WHOIS, DNS data
**Free tier:** Limited lookups
**API Key:** `WHOISXML_API_KEY`
**Signup:** https://www.whoisxmlapi.com

### VirusTotal
**Purpose:** Domain/IP reputation, malware scanning, URL analysis
**Free tier:** Limited lookups (4 lookups/min, 500/day), no bulk
**API Key:** `VIRUSTOTAL_API_KEY`
**Signup:** https://www.virustotal.com/gui/join-us

### URLScan
**Purpose:** Website scanning and analysis, screenshot, DOM extraction
**Free tier:** Available, requires registration
**API Key:** `URLSCAN_API_KEY`
**Signup:** https://urlscan.io

### AlienVault OTX
**Purpose:** Threat intelligence, pulse sharing, IP/reputation data
**Free tier:** Full access for individuals
**API Key:** `OTX_API_KEY`
**Signup:** https://otx.alienvault.com/api

### GreyNoise
**Purpose:** Internet background noise, bot detection, scanner classification
**Free tier:** 100 queries/day
**API Key:** `GREYNOISE_API_KEY`
**Signup:** https://www.greynoise.io

### AbuseIPDB
**Purpose:** IP reputation, abuse reporting, geographic data
**Free tier:** 1,000 lookups/day
**API Key:** `ABUSEIPDB_API_KEY`
**Signup:** https://www.abuseipdb.com

### RiskIQ / PassiveTotal
**Purpose:** Passive DNS, WHOIS history, threat intel, SSL certificates
**Free tier:** Community edition limited
**API Key:** `RISKIQ_API_KEY`
**Signup:** https://community.riskiq.com

### Binary Edge
**Purpose:** Internet scanning, vulnerability detection, exposed database search
**Free tier:** Limited
**API Key:** `BINARY_EDGE_API_KEY`
**Signup:** https://www.binaryedge.io

### Censys
**Purpose:** Internet scan data, SSL certificates, host characterization
**Free tier:** Limited (basic queries)
**API Key:** `CENSYS_API_KEY`
**Signup:** https://search.censys.io

### DNSdumpster
**Purpose:** Domain to DNS map, reverse DNS, subdomains, email discovery
**Free tier:** Free (web-based, can scrape)
**No API key needed** — scrape `https://dnsdumpster.com/`
**Signup:** https://dnsdumpster.com

### SpyOnWeb
**Purpose:** Reverse DNS, same-owner domains, DNS history
**Free tier:** Limited free web access
**Scrape:** `http://spyonweb.com/`
**No API key**

### ViewDNS.info
**Purpose:** Reverse IP, Whois history, IP location, DNS lookup
**Free tier:** Multiple free tools at web interface
**Scrape:** `https://viewdns.info/`
**No API key**

### IPQualityScore
**Purpose:** Email/phone/IP reputation scoring, fraud detection, bot detection
**Free tier:** 5,000 requests/month
**API Key:** `IPQS_API_KEY`
**Signup:** https://www.ipqualityscore.com

---

## Breach & Leak Databases

### LeakCheck
**Purpose:** Breach database search by email, username, domain
**Free tier:** Limited
**API Key:** `LEAKCHECK_API_KEY`
**Signup:** https://leakcheck.io

### DeHashed
**Purpose:** Comprehensive breach search — email, username, phone, IP, password hash
**Free tier:** Very limited
**API Key:** `DEHASHED_API_KEY`
**Signup:** https://dehashed.com

### Snusbase
**Purpose:** Breach database search by email, username, IP, hash
**Free tier:** Limited
**API Key:** `SNUSBASE_API_KEY`
**Signup:** https://www.snusbase.com

### BreachDirectory
**Purpose:** Breach lookup by email/username/phone/IP
**Free tier:** Limited
**API Key:** `BREACHDIRECTORY_API_KEY`
**Signup:** https://breachdirectory.org

### GhostProject
**Purpose:** Free breach search, sometimes reveals passwords
**Free tier:** Yes
**Web:** https://ghostproject.fr

### IntelX
**Purpose:** Search across multiple breach databases, paste sites, dark web
**Free tier:** Powerful free tier
**Web:** https://intelx.io

### Scylla
**Purpose:** Aggregate breach search, credential lookup
**Free tier:** Limited
**Web:** https://scylla.sh

### LeakPeek
**Purpose:** Breach lookup by email or domain
**Free tier:** Limited
**Web:** https://leakpeek.com

---

## GitHub & Code Search

### GitHub API
**Purpose:** Code search, user/org lookup, commit history by email, repository data
**Free tier:** 60 requests/hour unauthenticated, 5,000/hour authenticated
**API Key:** `GITHUB_TOKEN` (optional, get at https://github.com/settings/tokens)
**Signup:** https://github.com/settings/tokens
**Note:** No key needed for basic usage but recommended for higher rate limits

### Grep App
**Purpose:** Search code, repositories, paste sites across GitHub, GitLab, etc.
**Free tier:** Limited
**API Key:** `GREP_APP_API_KEY`
**Signup:** https://grep.app

---

## Company & Business Data

### OpenCorporates
**Purpose:** Global company data from 140+ jurisdictions
**Free tier:** Limited API (request counter)
**API:** https://api.opencorporates.com
**Signup:** https://opencorporates.com

### SEC EDGAR
**Purpose:** US company filings, annual reports, officer names, business addresses
**Free tier:** Completely free, no API key needed
**API:** `https://efts.sec.gov/LATEST/search-index?q={query}&dateRange=custom`
**Docs:** https://www.sec.gov/edgar/search-and-view-media
**Note:** Rate limited. Use `https://efts.sec.gov/LATEST/search-index?q=` for REST API

### Companies House UK
**Purpose:** UK company data, officers, filing history
**Free tier:** Free API with registration (5000 requests/hour)
**API Key:** `COMPANIES_HOUSE_API_KEY`
**Signup:** https://developer.companyhouse.gov.uk/
**API:** `https://api.companyhouse.gov.uk/`

### GLEIF (Global Legal Entity Identifier)
**Purpose:** Official entity identifiers (LEI) for companies worldwide
**Free tier:** Free API, no key needed
**API:** `https://api.gleif.org/api/v1/`
**Docs:** https://www.gleif.org/en/lei-data/gleif-api

### VIES (EU VAT Verification)
**Purpose:** Verify EU VAT numbers against official EU registry
**Free tier:** Free SOAP/REST API, no key needed
**API:** `https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl`
**Web:** https://ec.europa.eu/taxation_customs/vies/

### GUS (Glowny Urzad Statystyczny) - Poland
**Purpose:** Polish REGON numbers, business statistics
**Free tier:** Limited public access
**API:** https://api.stat.gov.pl
**Note:** Requires registration for full API access

---

## Social Media & Username Search

### Reddit JSON API
**Purpose:** Reddit user profiles, post history, subreddit data
**Free tier:** Completely free, no key needed
**No API key** — `https://www.reddit.com/user/{username}/about.json`
**Note:** Rate limited (~60 requests/min)

### Social Searcher
**Purpose:** Real-time social media post search across platforms
**Free tier:** Limited searches per day
**Web:** https://www.social-searcher.com
**No API key needed for basic web use**

### Namechk
**Purpose:** Check username availability across 100+ websites
**Free tier:** Limited web access
**Web:** https://namechk.com
**Scrape via ascend**

### InstantUsername
**Purpose:** Check username availability across platforms
**Free tier:** Limited
**Web:** https://instantusername.com
**Scrape via ascend**

---

## Dark Web Search

### Ahmia.fi
**Purpose:** Search engine for .onion sites (clearnet index)
**Free tier:** Free web interface
**URL:** https://ahmia.fi
**No API key**

### Torch (Search Engine)
**Purpose:** Dark web search engine (onion crawler)
**Free tier:** Free web interface
**URL:** http://cnkj6nippubxycyn.onion (Tor) or https://torchhs2h42zkel.onion (alternatives)
**No API key**

### DarkSearch
**Purpose:** Free dark web search engine
**Free tier:** Free
**URL:** http://darksearchqelmoc.onion (Tor)
**No API key**

### OnionLand Search
**Purpose:** Another dark web search engine
**Free tier:** Free
**URL:** http://3bbaaacxczamd55.onion (Tor)
**No API key**

### The Hidden Wiki
**Purpose:** Curated directory of onion links and dark web resources
**Free tier:** Free
**URL:** https://thehiddenwiki.org
**No API key**

### Dark.fail
**Purpose:** Uptime monitor for popular onion services
**Free tier:** Free
**URL:** https://dark.fail
**No API key**

---

## NOT Free (No Free Tier)

- **PhantomBuster** — No free tier. Trial discontinued. ~€99/month. Social media extraction.
- **SpyCloud** — Enterprise only, pricing on request
- **Pipl** — Paid only, pricing on request
- **BeenVerified** — Paid only, ~$20/month
- **Instant Checkmate** — Paid only, ~$25/month
- **Radaris** — Paid only
- **PeekYou** — Paid only
