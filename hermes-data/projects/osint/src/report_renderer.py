from src.models import OsintQuery, OsintResponse, ServiceResult
from src.cascade_engine import CascadeResult
from src.connections import Connection, CONNECTION_TYPES
from typing import Optional
from datetime import datetime


class ReportRenderer:
    def render(self, response: OsintResponse) -> str:
        lines = []
        lines.append(f"# OSINT Report")
        lines.append(f"")
        lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"")

        query = response.query
        sections = []

        if query.email:
            sections.append(self._render_email_section(response))

        if query.phone:
            sections.append(self._render_phone_section(response))

        if query.name:
            sections.append(self._render_name_section(response))

        if query.linkedin:
            sections.append(self._render_linkedin_section(response))

        if query.nip:
            sections.append(self._render_nip_section(response))

        if query.krs:
            sections.append(self._render_krs_section(response))

        if query.domain:
            sections.append(self._render_domain_section(response))

        if query.vin:
            sections.append(self._render_vin_section(response))

        if query.plate:
            sections.append(self._render_plate_section(response))

        if query.ceidg_url:
            sections.append(self._render_ceidg_section(response))

        if query.nip or query.krs or query.name:
            court_results = [r for r in response.results if r.source == "courts"]
            if court_results:
                sections.append(self._render_courts_section(response))

        if sections:
            for section in sections:
                lines.extend(section)
                lines.append("")
        else:
            lines.append("*No data found.*")

        if response.errors:
            lines.append("")
            lines.append("## Errors")
            for err in response.errors:
                lines.append(f"- {err}")

        return "\n".join(lines)

    def _section(self, title: str, results: list[ServiceResult]) -> tuple[list[str], list[str]]:
        positive = []
        negative = []
        for r in results:
            if r.success and r.data:
                positive.append(r)
            else:
                negative.append(r)
        return positive, negative

    def _result_block(self, source: str, data: dict, indent: int = 0) -> list[str]:
        pad = "  " * indent
        lines = []
        if data.get("name"):
            lines.append(f"{pad}- **Name:** {data['name']}")
        if data.get("followers"):
            lines.append(f"{pad}- **Followers:** {data['followers']}")
        if data.get("bio"):
            bio = data["bio"][:500] + "..." if len(data["bio"]) > 500 else data["bio"]
            lines.append(f"{pad}- **Bio:** {bio}")
        if data.get("location"):
            lines.append(f"{pad}- **Location:** {data['location']}")
        if data.get("company"):
            lines.append(f"{pad}- **Company:** {data['company']}")
        if data.get("email"):
            lines.append(f"{pad}- **Email:** {data['email']}")
        if data.get("phone"):
            lines.append(f"{pad}- **Phone:** {data['phone']}")
        if data.get("profile_url"):
            lines.append(f"{pad}- **URL:** {data['profile_url']}")
        if data.get("html_url"):
            lines.append(f"{pad}- **URL:** {data['html_url']}")
        if data.get("blog"):
            lines.append(f"{pad}- **Blog:** {data['blog']}")
        if data.get("public_repos"):
            lines.append(f"{pad}- **Public Repos:** {data['public_repos']}")
        if data.get("followers") and "github" in source.lower():
            pass
        if data.get("repos"):
            lines.append(f"{pad}- **Repositories:** {len(data['repos'])} found")
            for repo in data["repos"][:5]:
                lines.append(f"{pad}  - [{repo.get('name','?')}]({repo.get('html_url','')}) — ★{repo.get('stargazers_count',0)}")
        if data.get("users"):
            lines.append(f"{pad}- **Users:** {data.get('total_count','?')} total found")
            for user in data["users"][:10]:
                lines.append(f"{pad}  - [{user.get('login','?')}]({user.get('html_url','')}) — {user.get('type','?')}")
        if data.get("commits"):
            lines.append(f"{pad}- **Commits:** {len(data['commits'])} found")
            for commit in data["commits"][:5]:
                lines.append(f"{pad}  - `{commit.get('sha','')[:7]}` — {commit.get('author','?')} on {commit.get('date','')[:10]}: {commit.get('message','')[:80]}")
        if data.get("certificates"):
            lines.append(f"{pad}- **SSL Certificates:** {len(data['certificates'])} found")
            for cert in data["certificates"][:10]:
                name = cert.get("name","").replace("\n"," ")
                lines.append(f"{pad}  - {name[:100]}")
        if data.get("breaches"):
            lines.append(f"{pad}- **Breaches:** {len(data['breaches'])} found")
            for b in data["breaches"][:10]:
                lines.append(f"{pad}  - **{b.get('Name', b.get('Title', 'Unknown'))}** — {b.get('BreachDate','').split('T')[0] if b.get('BreachDate') else '?'}")
                if b.get("DataClasses"):
                    lines.append(f"{pad}    Data: {', '.join(b['DataClasses'])}")
        if data.get("found") is not None:
            if data["found"]:
                lines.append(f"{pad}- **Found in leak DB:** Yes ({data['count']} occurrences)")
            else:
                lines.append(f"{pad}- **Found in leak DB:** No")
        if data.get("error"):
            lines.append(f"{pad}- **Error:** {data['error']}")
        if data.get("message") and not data.get("name"):
            lines.append(f"{pad}- **Info:** {data['message'][:200]}")
        if not lines:
            for k, v in data.items():
                if v and k not in ("results_snippet", "links"):
                    lines.append(f"{pad}- **{k}:** {str(v)[:200]}")
            if not lines:
                lines.append(f"{pad}- (no structured data)")
        return lines

    def _render_result_data(self, lines: list, result: ServiceResult, indent: str) -> None:
        """Render a single successful ServiceResult's data into lines list."""
        data = result.data or {}
        source = result.source
        pad = indent
        subpad = indent + "  "

        # GitHub user data (single user)
        if data.get("login") or (data.get("name") and data.get("html_url")):
            if data.get("name"):
                lines.append(f"{pad}- **Name:** {data['name']}")
            if data.get("login"):
                lines.append(f"{pad}- **Login:** {data['login']}")
            if data.get("company"):
                lines.append(f"{pad}- **Company:** {data['company']}")
            if data.get("location"):
                lines.append(f"{pad}- **Location:** {data['location']}")
            if data.get("blog"):
                lines.append(f"{pad}- **Blog:** {data['blog']}")
            if data.get("bio"):
                bio = data["bio"][:300] + "..." if len(data["bio"]) > 300 else data["bio"]
                lines.append(f"{pad}- **Bio:** {bio}")
            if data.get("html_url"):
                lines.append(f"{pad}- **Profile:** {data['html_url']}")
            if data.get("followers"):
                lines.append(f"{pad}- **Followers:** {data['followers']} | **Following:** {data.get('following', '?')}")
            if data.get("public_repos"):
                lines.append(f"{pad}- **Public Repos:** {data['public_repos']}")
            if data.get("twitter_username"):
                lines.append(f"{pad}- **Twitter:** @{data['twitter_username']}")
            if data.get("hireable"):
                lines.append(f"{pad}- **Hireable:** {data['hireable']}")
            if data.get("created_at"):
                lines.append(f"{pad}- **GitHub since:** {data['created_at'][:10]}")
            return

        # GitHub user search results (list of users)
        if data.get("users") and isinstance(data["users"], list):
            total = data.get("total_count", len(data["users"]))
            lines.append(f"{pad}- **GitHub users found:** {total}")
            for u in data["users"][:10]:
                login = u.get("login", u.get("username", "?"))
                url = u.get("html_url", u.get("url", ""))
                user_type = u.get("type", "User")
                lines.append(f"{subpad}- [{login}]({url}) ({user_type})")
            return

        # Sherlock / maigret profiles
        if data.get("profiles"):
            count = len(data["profiles"]) if isinstance(data["profiles"], list) else len(data["profiles"])
            lines.append(f"{pad}- **Profiles found:** {count}")
            if isinstance(data["profiles"], list):
                for p in data["profiles"][:10]:
                    if isinstance(p, dict):
                        site = p.get("site", "?")
                        url = p.get("url_user", p.get("url", ""))
                        lines.append(f"{subpad}- [{site}] {url}")
            else:
                for site, info in list(data["profiles"].items())[:10]:
                    if isinstance(info, dict):
                        url = info.get("url_user", info.get("url", ""))
                        lines.append(f"{subpad}- [{site}] {url}")
            return

        # Breach data
        if data.get("breaches"):
            lines.append(f"{pad}- **Breaches:** {len(data['breaches'])}")
            for b in data["breaches"][:5]:
                name = b.get("Name", b.get("Title", "?"))
                date = b.get("BreachDate", "?")[:10] if b.get("BreachDate") else "?"
                lines.append(f"{subpad}- **{name}** ({date})")
            return

        # Subdomains / enumerated data
        if data.get("subdomains"):
            subs = data["subdomains"]
            lines.append(f"{pad}- **Subdomains ({len(subs)}):**")
            for s in subs[:20]:
                lines.append(f"{subpad}- {s}")
            return

        # Domain scrape / HTML content
        if data.get("raw_content") and len(data["raw_content"]) > 50:
            content = data["raw_content"][:400].replace('\n', ' ')
            lines.append(f"{pad}- **Content preview:** {content}...")
            return

        # Courts result - show clean data not raw HTML
        if data.get("links") and data.get("query"):
            lines.append(f"{pad}- **Query:** {data['query']}")
            links = data["links"]
            lines.append(f"{pad}- **Court case links found:** {len(links)}")
            for link in links[:10]:
                lines.append(f"{subpad}- {link}")
            if data.get("raw_snippet"):
                snippet = data["raw_snippet"][:300].replace('\n', ' ')
                lines.append(f"{pad}- **Snippet:** {snippet}...")
            return

        # Company / rejestr data
        if data.get("results"):
            results_list = data["results"]
            if isinstance(results_list, list) and len(results_list) > 0:
                lines.append(f"{pad}- **Results:** {len(results_list)} entries")
                for entry in results_list[:5]:
                    if isinstance(entry, dict):
                        name = entry.get("name", entry.get("company_name", entry.get("title", "?")))
                        if name:
                            lines.append(f"{subpad}- {name}")
            return

        # Generic fallbacks - show key fields
        key_fields = (
            "name", "login", "company", "location", "email", "phone",
            "bio", "blog", "html_url", "profile_url", "followers",
            "public_repos", "repos", "users", "total_count",
            "found", "count", "message"
        )
        shown = False
        for k in key_fields:
            if k in data and data[k] and data[k] != "?":
                val = data[k]
                if isinstance(val, str) and len(val) > 200:
                    val = val[:200] + "..."
                lines.append(f"{pad}- **{k}:** {val}")
                shown = True
        if not shown:
            # Last resort: show raw snippet
            for k, v in data.items():
                if k.startswith("_"):
                    continue
                if isinstance(v, str) and len(v) > 50:
                    lines.append(f"{pad}- **{k}:** {v[:200]}...")
                elif v:
                    lines.append(f"{pad}- **{k}:** {v}")

    def _render_email_section(self, response: OsintResponse) -> list[str]:
        lines = ["## Email Investigation"]
        results = [r for r in response.results if r.source in ("haveibeenpwned", "epieos", "breachdirectory", "leakcheck", "local_leak_db")]
        pos, neg = self._section("Email", results)
        if pos:
            lines.append("")
            lines.append("### Findings")
            for r in pos:
                lines.extend(self._result_block(r.source, r.data))
        return lines

    def _render_phone_section(self, response: OsintResponse) -> list[str]:
        lines = ["## Phone Investigation"]
        results = [r for r in response.results if r.source in ("phoneinfoga", "numverify", "local_leak_db")]
        pos, neg = self._section("Phone", results)
        if pos:
            lines.append("")
            lines.append("### Findings")
            for r in pos:
                lines.extend(self._result_block(r.source, r.data))
        return lines

    def _render_name_section(self, response: OsintResponse) -> list[str]:
        lines = ["## Person Investigation"]
        name_results = [r for r in response.results if r.source in ("sherlock", "maigret", "github_user_search")]
        social_results = [r for r in response.results if r.source.startswith("google_social") or r.source == "twitter_advanced"]
        scrape_results = [r for r in response.results if r.source in ("facebook_scrape", "instagram_scrape", "tiktok_scrape")]
        if name_results:
            lines.append("")
            lines.append("### Username Accounts Found")
            found_any = False
            for r in name_results:
                if r.data.get("profiles"):
                    profiles = r.data["profiles"]
                    if isinstance(profiles, list):
                        for entry in profiles[:50]:
                            site = entry.get("site", "") if isinstance(entry, dict) else str(entry)
                            url = entry.get("url", "") if isinstance(entry, dict) else ""
                            if url:
                                lines.append(f"- **{site}:** {url}")
                                found_any = True
                    elif isinstance(profiles, dict):
                        for site, info in profiles.items():
                            if isinstance(info, dict) and info.get("exists"):
                                url = info.get("url", "")
                                lines.append(f"- **{site}:** {url}")
                                found_any = True
                if r.data.get("users"):
                    for user in r.data["users"][:10]:
                        lines.append(f"- **GitHub:** [{user.get('login','')}]({user.get('html_url','')})")
                        found_any = True
                if r.error and not found_any:
                    lines.append(f"- **{r.source}:** Error — {r.error[:100]}")
            if not found_any:
                lines.append("_No accounts found or services encountered errors._")
        if scrape_results:
            lines.append("")
            lines.append("### Social Profiles (Scraped)")
            for r in scrape_results:
                if r.data.get("name") or r.data.get("bio"):
                    lines.append(f"#### {r.source.replace('_scrape', '').title()}")
                    if r.data.get("name"):
                        lines.append(f"- **Name:** {r.data['name']}")
                    if r.data.get("followers"):
                        lines.append(f"- **Followers:** {r.data['followers']}")
                    if r.data.get("bio"):
                        lines.append(f"- **Bio:** {r.data['bio'][:200]}")
                    if r.data.get("profile_url"):
                        lines.append(f"- **URL:** {r.data['profile_url']}")
                elif r.error:
                    lines.append(f"- **{r.source}:** {r.error[:100]}")
        if social_results:
            lines.append("")
            lines.append("### Social Media Search Results")
            for r in social_results:
                lines.append(f"#### {r.source.replace('google_social_', 'Google: ').replace('twitter_advanced', 'Twitter/X')}")
                if r.data.get("query"):
                    lines.append(f"- **Query:** `{r.data['query']}`")
                if r.data.get("results_snippet"):
                    snippet = r.data["results_snippet"][:500].replace("\n", " ")
                    lines.append(f"- **Results:** {snippet}...")
                if r.data.get("links") and len(r.data["links"]) > 0:
                    count = len(r.data["links"]) if isinstance(r.data["links"], (list, dict)) else "?"
                    lines.append(f"- **Links found:** {count}")
                if r.error:
                    lines.append(f"- **Error:** {r.error[:100]}")
        return lines

    def _render_linkedin_section(self, response: OsintResponse) -> list[str]:
        lines = ["## LinkedIn / Social Profile Investigation"]
        results = [r for r in response.results if r.source in ("facebook_scrape", "instagram_scrape", "tiktok_scrape", "twitter_advanced")]
        pos, neg = self._section("Social", results)
        if pos:
            lines.append("")
            lines.append("### Findings")
            for r in pos:
                platform = r.source.replace("_scrape", "").title()
                lines.append(f"#### {platform}")
                found = False
                for field, label in [("name", "Name"), ("followers", "Followers"), ("following", "Following"), ("bio", "Bio"), ("about", "About"), ("category", "Category"), ("likes", "Likes"), ("posts", "Posts")]:
                    if r.data.get(field):
                        lines.append(f"- **{label}:** {r.data[field]}")
                        found = True
                social = r.data.get("social_links", [])
                if social:
                    lines.append(f"- **Other social links:** {len(social)} found")
                    for link in social[:5]:
                        lines.append(f"  - {link}")
                if r.data.get("profile_url"):
                    lines.append(f"- **URL:** {r.data['profile_url']}")
                if r.error:
                    lines.append(f"- **Error:** {r.error[:100]}")
                if not found and not r.error:
                    lines.append("_No structured data extracted._")
        return lines

    def _render_nip_section(self, response: OsintResponse) -> list[str]:
        lines = ["## Company Investigation (NIP)"]
        results = [r for r in response.results if r.source in ("ceidg", "vat_registry")]
        pos, neg = self._section("NIP", results)
        if pos:
            for r in pos:
                source_label = r.source.upper()
                lines.append(f"\n### {source_label}")
                parsed = r.data.get("parsed", {})
                if parsed:
                    field_map = {
                        "nazwa": "Nazwa firmy",
                        "nip": "NIP",
                        "regon": "REGON",
                        "adres": "Adres",
                        "address": "Adres",
                        "status": "Status VAT",
                        "bank_account": "Rachunek bankowy",
                        "formaprawna": "Forma prawna",
                        "siedziba": "Siedziba",
                    }
                    for key, label in field_map.items():
                        if parsed.get(key):
                            lines.append(f"- **{label}:** {parsed[key]}")
                    if not any(parsed.get(k) for k in field_map):
                        lines.append(f"- _No structured fields found. Raw: {list(parsed.values())[0] if parsed else 'empty'}_")
                else:
                    snippet = r.data.get("raw_snippet", "")
                    if snippet:
                        lines.append(f"- _No structured data extracted. Raw: {snippet[:300]}..._")
        if neg:
            for r in neg:
                lines.append(f"\n### {r.source.upper()}")
                lines.append(f"- **Error:** {r.error}")
        return lines

    def _render_krs_section(self, response: OsintResponse) -> list[str]:
        lines = ["## Company Investigation (KRS)"]
        results = [r for r in response.results if r.source in ("ekrs_json", "ekrs")]
        pos, neg = self._section("KRS", results)
        if pos:
            for r in pos:
                source_label = r.source.upper().replace("EKRS_JSON", "eKRS API").replace("EKRS", "eKRS Web")
                lines.append(f"\n### {source_label}")
                parsed = r.data
                field_map = {
                    "krs": "KRS",
                    "nazwa": "Nazwa",
                    "formaprawna": "Forma prawna",
                    "siedziba": "Siedziba",
                    "adres": "Adres",
                    "nip": "NIP",
                    "regon": "REGON",
                }
                for key, label in field_map.items():
                    val = parsed.get(key)
                    if val and key != "raw_snippet":
                        lines.append(f"- **{label}:** {val}")
                raw_snippet = parsed.get("raw_snippet", "")
                has_structured = any(parsed.get(k) for k in field_map)
                if not has_structured and raw_snippet:
                    lines.append(f"- _No structured data extracted. Raw: {raw_snippet[:300]}..._")
        if neg:
            for r in neg:
                lines.append(f"\n### {r.source.upper()}")
                lines.append(f"- **Error:** {r.error}")
        return lines

    def _render_domain_section(self, response: OsintResponse) -> list[str]:
        lines = ["## Domain / Website Investigation"]
        infra_results = [r for r in response.results if r.source in ("crtsh", "virustotal", "shodan", "builtwith", "github_org", "github_repo_search")]
        pos, neg = self._section("Domain", infra_results)
        if pos:
            lines.append("")
            lines.append("### Infrastructure")
            for r in pos:
                lines.append(f"")
                lines.append(f"#### {r.source}")
                lines.extend(self._result_block(r.source, r.data, indent=1))
        return lines

    def _render_vin_section(self, response: OsintResponse) -> list[str]:
        return ["## Vehicle Investigation (VIN)", "- VIN lookup not yet fully implemented. Sources: CEPiK (Poland), CARFAX, AutoCheck."]

    def _render_plate_section(self, response: OsintResponse) -> list[str]:
        return ["## Vehicle Investigation (Plate)", "- Plate lookup not yet fully implemented. Source: CEPiK (Poland)."]

    def _render_ceidg_section(self, response: OsintResponse) -> list[str]:
        lines = ["## CEIDG Investigation"]
        results = [r for r in response.results if r.source == "ceidg"]
        if results:
            lines.append("")
            lines.append("### Findings")
            for r in results:
                lines.extend(self._result_block(r.source, r.data, indent=1))
        return lines

    def _render_courts_section(self, response: OsintResponse) -> list[str]:
        lines = ["## Polish Courts (Orzeczenia MS)"]
        results = [r for r in response.results if r.source == "courts"]
        pos, neg = self._section("Courts", results)
        if pos:
            for r in pos:
                lines.append(f"\n### Query: {r.data.get('query', '')}")
                snippet = r.data.get("raw_snippet", "")
                if snippet:
                    lines.append(f"- **Content preview:** {snippet[:500]}...")
                links = r.data.get("links", [])
                if links:
                    lines.append(f"- **Case links found:** {len(links)}")
                    for link in links[:10]:
                        lines.append(f"  - {link}")
        if neg:
            for r in neg:
                lines.append(f"- **{r.source}:** Error — {r.error}")
        return lines

    def render_cascade(self, cascade_results: list[CascadeResult], query: OsintQuery) -> str:
        lines = []
        lines.append(f"# OSINT Report (Cascade)")
        lines.append(f"")
        lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"**Subject:** {self._subject_label(query)}")
        lines.append(f"**Subject type:** {cascade_results[0].subject_type if cascade_results else 'unknown'}")
        lines.append(f"")

        by_depth = {}
        for cr in cascade_results:
            by_depth.setdefault(cr.depth, []).append(cr)

        for depth in sorted(by_depth.keys()):
            crs = by_depth[depth]
            indent = "  " * depth
            prefix = "└─" if depth > 0 else ""
            lines.append(f"{indent}## Depth {depth}")

            for cr in crs:
                lines.append(f"{indent}### {prefix}{cr.data_type.upper()}: {cr.data_value}")

                if cr.results:
                    successful = [r for r in cr.results if r.success]
                    failed = [r for r in cr.results if not r.success]
                    if successful:
                        lines.append(f"{indent}  **Services:** {', '.join(set(r.source for r in successful))}")
                        # Show actual data from successful results
                        for r in successful:
                            self._render_result_data(lines, r, indent + "  ")
                    if failed:
                        for r in failed:
                            lines.append(f"{indent}  - [{r.source}] {r.error[:80] if r.error else 'failed'}")

                if cr.connections:
                    lines.append(f"{indent}  **Connections (follow):**")
                    for c in cr.connections:
                        type_label = CONNECTION_TYPES.get(c.conn_type, c.conn_type)
                        lines.append(f"{indent}    - [{type_label}] {c.value} ({c.source_service})")

                if cr.passive_data:
                    lines.append(f"{indent}  **Passive data (list only):**")
                    for c in cr.passive_data:
                        type_label = CONNECTION_TYPES.get(c.conn_type, c.conn_type)
                        lines.append(f"{indent}    - [{type_label}] {c.value}")

                if not cr.results and not cr.connections and not cr.passive_data:
                    lines.append(f"{indent}  _(no data)_")

                lines.append("")

        return "\n".join(lines)

    def _subject_label(self, query: OsintQuery) -> str:
        if query.name:
            return query.name
        if query.email:
            return query.email
        if query.phone:
            return query.phone
        if query.nip:
            return f"NIP: {query.nip}"
        if query.krs:
            return f"KRS: {query.krs}"
        if query.domain:
            return query.domain
        if query.linkedin:
            return query.linkedin
        return "Unknown"


renderer = ReportRenderer()
