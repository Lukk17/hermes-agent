# Leak Databases — Downloadable & Web Searchable

These are databases of breached data that can be downloaded for local searching, or web-based services that provide similar search capabilities.

## Web Searchable Leak Databases (Free / Freemium)

These sites allow you to search for emails/usernames/passwords in breach data without downloading anything.

### HaveIBeenPwned
Most well-known breach database. Search by email, domain, or password. Free. Shows breach names and dates.
https://haveibeenpwned.com

### BreachDirectory
Free tier. Check if email/username appears in breaches. Shows partial password hash.
https://breachdirectory.org

### LeakCheck
Free tier available. Search by email, username, domain. Shows breach names, dates, data types.
https://leakcheck.io

### GhostProject
Free. Search emails in breach data. Sometimes shows password.
https://ghostproject.fr

### IntelX
Free tier powerful. Search across multiple breach databases, paste sites, dark web. Email, domain, IP, name searches.
https://intelx.io

### DeHashed
Free tier very limited. Comprehensive breach search — email, username, phone, IP, password hash.
https://dehashed.com

### Snusbase
Free tier limited. Search by email, username, IP, hash. Paid plans from ~$5/month.
https://www.snusbase.com

### LeakPeek
Free tier. Breach lookup by email or domain. Paid from ~$10/month.
https://leakpeek.com

### Scylla
Free tier. Aggregate breach search, credential lookup.
https://scylla.sh

### Hive Systems
Free tier. Breach lookup by email. Shows password complexity analysis.
https://haveibeenpwned.com (also maps to HIBP)

### Leak-Lookup
Free and paid tiers. Search across breach databases.
https://leak-lookup.com

### Snitch
Free tier. Search for emails in breach data.
https://snitch.net

---

## Downloadable Breach Collections

Large datasets you download and search locally. Store in `data/leaks/` directory.

**WARNING:** These files are LARGE (10GB to 100GB+). Make sure you have adequate storage before downloading.

### Collection #1 (2018)
~87GB compressed, 773 million email addresses, 21 million unique passwords.
Source: Public torrent (search "Collection #1 2018 torrent")
Note: Many emails from older breaches (LinkedIn 2012, MySpace 2016, etc.)

### Collection #2 (2019)
~50GB, hundreds of millions of records from multiple breaches.
Source: Public torrent (search "Collection #2 2019 torrent")

### Collection #3-5 (2019)
Multiple large collections. Combined 100GB+.
Source: Public torrent (search "Collection 3 4 5 torrent")

### BreachCompilation (2017)
~1.4 billion credentials from multiple breaches. Organized by service/website.
Source: Public torrent (search "BreachCompilation torrent")
Note: One of the most comprehensive early compilations

### Exploit.in Combo List
Large combo list of email:password pairs from multiple breaches. Used for credential stuffing.
Source: Public torrent (search "exploit.in combo list torrent")
Note: Often contains fresh, high-value credentials

### Anti Public Combo List
~800 million email:password pairs from multiple breaches.
Source: Public torrent (search "Anti Public Combo List torrent")

### Anti Public #2
Additional large combo list.
Source: Public torrent (search "Anti Public 2 leak torrent")

### Rulit Database
Various breach dumps from Russian-speaking hacker communities.
Source: Public torrent (search "Rulit database leak torrent")

### LeakBase
Historical breach database collection. Was a paid service, now datasets available.
Source: Public torrent (search "LeakBase dump torrent")

### LeakedSource
Historical breach database. Was online service, now defunct. Dumps available.
Source: Public torrent (search "LeakedSource dump torrent")

### Zelda Collection
Database backups and leaks from various sources.
Source: Public torrent (search "Zelda database leak torrent")

### Onliner Spambot
German-language spam list with email and credentials.
Source: Public torrent (search "Onliner Spambot database torrent")

### Bitnodes
Bitcoin-related breach data, node IP addresses.
Source: Public torrent (search "Bitnodes leak torrent")

### Various Specific Breaches (Individual Downloads)

#### LinkedIn (2012) — 165M records
One of the largest public breach dumps. Contains email, password (SHA1).
Torrent: Search "LinkedIn 2012 breach 165M torrent"

#### MySpace (2016) — 360M records
Source: Search "MySpace breach 360M torrent"

#### Adobe (2013) — 153M records
Source: Search "Adobe breach 153M torrent"

#### DropBox (2012) — 68M records
Source: Search "DropBox breach 2012 torrent"

#### Badoo (2013) — 112M records
Source: Search "Badoo breach 112M torrent"

#### Tumblr (2013) — 65M records
Source: Search "Tumblr breach 2013 torrent"

#### VK.com (2012) — 93M records
Source: Search "VK.com breach 2012 torrent"

#### Clan (2016) — 8M Polish users
Polish gaming community breach.
Source: Search "Clan.pl breach 8M torrent"

#### Polish paste sites (direct downloads):
- Pastebin.pl dumps: https://pastebin.com/archive
- Various Polish forums and services

---

## Polish-Specific Resources

### Polish Paste Sites
Search these for Polish data leaks:
- https://pastebin.pl (search by email/domain)
- https://hastebin.com (search via Google dorking)
- https://dpaste.org
- https://controlpaste.com

Google dorking examples:
```
site:pastebin.pl "target@email.com"
site:hastebin.com "target"
site:dpaste.org "target@wp.pl"
```

### Polish Breach Dumps
Search for "polish breach dump" or "polska baza danych leak" via torrent search engines.

### REGON/NIP Lookups (Official)
Polish business registries — see `docs/public-registers-pl.md`

---

## Dark Web Resources

### Search Engines (Clearnet)
- **The Hidden Wiki** — https://thehiddenwiki.org
- **Dark.fail** — https://dark.fail (uptime monitor for popular onion sites)
- **Fresh onions** — https://github.com

### Dark Web Search (Tor Required)
- **Torch** — http://cnkj6nippubxycyn.onion
- **Ahmia** — http://msydqstkz2curtyc.onion
- **DarkSearch** — http://darksearchqelmoc.onion
- **OnionLand Search** — http://3bbaaacxczamd55.onion

Note: Access dark web sites via Tor Browser. We document for OSINT awareness.

### Dark Web Marketplaces (Historical Reference Only)
These are documented for awareness of what exists. Do not access for illegal purposes.

---

## Searching Locally

Once downloaded to `data/leaks/`, search with:

```bash
# Create leaks directory
mkdir -p data/leaks/

# Grep for email in all text files
grep -r "target@email.com" data/leaks/

# Search for username
grep -r "target_username" data/leaks/

# Search for password hash (MD5 example)
grep -r "5f4dcc3b5aa765d61d8327deb882cf99" data/leaks/

# Use grep with regex for partial matches
grep -rE "target.*@gmail.com" data/leaks/

# Count lines in large files
wc -l data/leaks/*.txt

# Search for domain in all files
grep -r "example.com" data/leaks/

# Find all unique emails in a file
grep -oE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' data/leaks/*.txt | sort -u > emails_found.txt
```

### Python Tools for Local Search

```bash
# h8mail - breach hunting tool
pip install h8mail
h8mail -t target@email.com -l /path/to/leaks/

# Custom Python search script
python3 << 'EOF'
import os
import re

def search_leaks(query, leaks_dir="data/leaks/"):
    for root, dirs, files in os.walk(leaks_dir):
        for f in files:
            path = os.path.join(root, f)
            if f.endswith(('.txt', '.csv', '.log')):
                try:
                    with open(path, 'r', errors='ignore') as fh:
                        for i, line in enumerate(fh):
                            if query.lower() in line.lower():
                                print(f"{path}:{i+1}: {line.strip()[:200]}")
                except Exception as e:
                    print(f"Error reading {path}: {e}")

search_leaks("target@email.com")
EOF
```

---

## Recommended Directory Structure

```
data/
└── leaks/
    ├── README.md              # This file
    ├── Collection1/
    │   └── emails.txt
    ├── LinkedIn_2012/
    │   └── linkedin.txt
    └── [other collections...]
```

---

## Legal Note

Breach data often contains illegally obtained information.

Using this data for:
- Account takeover (illegal everywhere)
- Credential stuffing (illegal)
- Fraud (illegal)
- Unauthorized access (illegal)

Using this data for:
- Security research (arguably protected in some jurisdictions)
- Personal data breach notifications (legitimate)
- OSINT investigations where you have authorization (context-dependent)
- Password breach awareness for your own accounts (legitimate)

**Always consult local laws. This documentation is for research and security awareness only.**
