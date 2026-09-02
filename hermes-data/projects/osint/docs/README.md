# OSINT Sources — Documentation

## Categories

### Source Docs (docs/)
- `email.md` — Email OSINT and verification
- `phone.md` — Phone number OSINT and lookup
- `people-intl.md` — International people search engines
- `business-intl.md` — International company/business research
- `social-media.md` — Social media platform OSINT
- `web-infra.md` — Web infrastructure and domain analysis
- `domains.md` — DNS and WHOIS research
- `public-registers-pl.md` — Polish public registers and databases
- `vehicles.md` — Vehicle registration and history (Poland + international)
- `tenders-pl.md` — Public procurement (Poland)
- `data-aggregators.md` — Aggregated business data services
- `data-leaks.md` — Data breach and leak databases (web-searchable)
- `darkweb.md` — Dark web and deep web OSINT
- `geo.md` — Geolocation, mapping, and satellite imagery
- `crypto.md` — Cryptocurrency blockchain OSINT
- `osint-tools.md` — General-purpose OSINT frameworks and tools
- `code-hubs.md` — GitHub, GitLab, DockerHub, npm, PyPI, Thingiverse, etc.
- `polish-courts.md` — Polish court portals and legal databases

## File Format

Each source doc follows this format:
```
## Category

### Free

#### Source Name
Description
Link

---

#### Another Source
Description
Link

---

### Paid

#### Source Name
Description
Link

---

(More sources...)
```

Sources sorted by usefulness within each tier. Paid sources include approximate pricing when known.

## Reference
- `leaks_dbs.md` — Downloadable breach database guide
- `free_with_api.md` — Services with free API tiers (add keys to `.env`)
- `ARCHITECTURE.md` — System architecture and flow diagrams

## Investigation Workflow

### Person
1. People search: Maigret, Sherlock (`people-intl.md`)
2. Social media: platform-specific searches (`social-media.md`)
3. Email: HaveIBeenPwned, EPIEOS (`email.md`)
4. Phone: PhoneInfoga, Truecaller (`phone.md`)
5. Breaches: BreachDirectory, LeakCheck (`data-leaks.md`)
6. Geolocation: from photos (`geo.md`)

### Company (Poland)
1. eKRS, CEIDG, REGON (`public-registers-pl.md`)
2. Financial documents: eKRS RDF (`public-registers-pl.md`)
3. Aggregators: Rejestr.io, iMSiG (`data-aggregators.md`)
4. Tenders: e-Zamówienia, KIO (`tenders-pl.md`)
5. VAT: Biała Lista VAT (`public-registers-pl.md`)
6. Courts: PRS, Orzeczenia (`polish-courts.md`)

### Company (International)
1. OpenCorporates, Crunchbase (`business-intl.md`)
2. LinkedIn, web presence
3. Web infra: BuiltWith, crt.sh (`web-infra.md`)
4. WHOIS/DNS: SecurityTrails, DNSDumpster (`domains.md`)

### Domain/Website
1. crt.sh, VirusTotal, BuiltWith, Shodan (`web-infra.md`)
2. WHOIS/DNS records (`domains.md`)
3. Code: GitHub org search (`code-hubs.md`)
4. Historical: Wayback Machine
5. Breaches: domain in leak DBs (`leaks_dbs.md`)

### Input Types → Parsed Fields
| Input | Parsed As |
|-------|-----------|
| email@domain.com | `email` |
| +48123456789 | `phone` |
| Jan Kowalski | `name` |
| NIP 5252341234 | `nip` |
| KRS 0000123456 | `krs` |
| PESEL 99010101234 | `pesel` |
| linkedin.com/in/xyz | `linkedin` |
| ceidg.gov.pl URL | `ceidg_url` |
| example.com | `domain` |
| AB1234CD | `plate` |
| WVWZZZ3CZWE123456 | `vin` |
