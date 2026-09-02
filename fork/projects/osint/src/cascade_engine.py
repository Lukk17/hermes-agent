from collections import deque
import asyncio
from dataclasses import dataclass, field
from typing import Optional

from src.models import OsintQuery, ServiceResult
from src.connections import Connection
from src.services.base_service import raise_if_intervention
from src.services.email_service import EmailService
from src.services.phone_service import PhoneService
from src.services.people_service import PeopleService
from src.services.company_service import CompanyService
from src.services.domain_service import DomainService
from src.services.github_service import GitHubService
from src.services.social_service import SocialService
from src.services.spiderfoot_service import SpiderFootService
from src.services.breach_service import BreachService
from src.services.enrichment_service import EnrichmentService
from src.services.gotools_service import GoToolsService


@dataclass
class CascadeResult:
    subject_type: str
    depth: int
    data_type: str
    data_value: str
    results: list = field(default_factory=list)
    connections: list = field(default_factory=list)
    passive_data: list = field(default_factory=list)


class CascadeEngine:
    def __init__(self, query: OsintQuery, max_depth: int = 3):
        self.query = query
        self.max_depth = max_depth
        self.subject_type = self._detect_subject_type()
        self.queue: deque[tuple[dict, int]] = deque()
        self.visited: set[tuple] = set()
        self.cascade_results: list[CascadeResult] = []
        self._services_inited = False

    def _detect_subject_type(self) -> str:
        if self.query.nip or self.query.krs or self.query.ceidg_url:
            return "company"
        return "person"

    def _subject_terms(self) -> set[str]:
        terms = set()
        if self.query.name:
            for word in self.query.name.lower().split():
                if len(word) > 2:
                    terms.add(word)
        if self.query.email:
            local = self.query.email.split("@")[0] if "@" in self.query.email else ""
            if local:
                terms.add(local.lower())
        return terms

    def _is_own_data(self, conn: Connection) -> bool:
        terms = self._subject_terms()
        val_lower = conn.value.lower() if conn.value else ""
        label_lower = conn.label.lower() if conn.label else ""
        for term in terms:
            if term in val_lower or term in label_lower:
                return False
        return True

    def _mark_visited(self, item: dict):
        parts = []
        for k in sorted(item.keys()):
            if item[k]:
                parts.append(f"{k}={item[k]}")
        if parts:
            self.visited.add(tuple(parts))

    def _is_visited(self, item: dict) -> bool:
        parts = []
        for k in sorted(item.keys()):
            if item[k]:
                parts.append(f"{k}={item[k]}")
        return tuple(parts) in self.visited

    def _queue_item(self, item: dict, depth: int):
        if not self._is_visited(item):
            self.queue.append((item, depth))

    async def run(self) -> list[CascadeResult]:
        initial = {}
        if self.query.name:
            initial = {"name": self.query.name}
        elif self.query.email:
            initial = {"email": self.query.email}
        elif self.query.phone:
            initial = {"phone": self.query.phone}
        elif self.query.nip:
            initial = {"nip": self.query.nip}
        elif self.query.krs:
            initial = {"krs": self.query.krs}
        elif self.query.domain:
            initial = {"domain": self.query.domain}
        elif self.query.linkedin:
            initial = {"linkedin": self.query.linkedin}

        if initial:
            self._queue_item(initial, 0)

        email_svc = EmailService()
        phone_svc = PhoneService()
        people_svc = PeopleService()
        company_svc = CompanyService()
        domain_svc = DomainService()
        github_svc = GitHubService()
        social_svc = SocialService()
        breach_svc = BreachService()
        enrich_svc = EnrichmentService()
        spiderfoot_svc = SpiderFootService()
        gotools_svc = GoToolsService()

        # Process by depth level - all items at depth 0 first, then depth 1, etc.
        while self.queue:
            # Collect all items at current depth
            current_depth = self.queue[0][1] if self.queue else 0
            depth_items = []
            while self.queue and self.queue[0][1] == current_depth:
                depth_items.append(self.queue.popleft())

            # Filter and prepare items
            valid_items = []
            for current, depth in depth_items:
                if depth > self.max_depth:
                    continue
                if not current:
                    continue
                if self._is_visited(current):
                    continue
                self._mark_visited(current)
                valid_items.append((current, depth))

            if not valid_items:
                continue

            # Process all items at this depth in parallel
            tasks = []
            for current, depth in valid_items:
                if current.get("name"):
                    tasks.append(self._search_name(
                        current["name"], depth,
                        people_svc, social_svc, github_svc,
                        company_svc, email_svc, spiderfoot_svc,
                    ))
                elif current.get("email"):
                    tasks.append(self._search_email(
                        current["email"], depth,
                        email_svc, social_svc, github_svc,
                        company_svc, breach_svc, enrich_svc,
                        spiderfoot_svc, gotools_svc,
                    ))
                elif current.get("phone"):
                    tasks.append(self._search_phone(
                        current["phone"], depth,
                        phone_svc, email_svc, social_svc,
                    ))
                elif current.get("nip"):
                    tasks.append(self._search_nip(
                        current["nip"], depth,
                        company_svc, domain_svc, github_svc,
                    ))
                elif current.get("krs"):
                    tasks.append(self._search_krs(
                        current["krs"], depth,
                        company_svc, domain_svc, github_svc,
                    ))
                elif current.get("company_name"):
                    tasks.append(self._search_company_name(
                        current["company_name"], depth,
                        company_svc, github_svc,
                        person_name=current.get("person_name"),
                    ))
                elif current.get("domain"):
                    tasks.append(self._search_domain(
                        current["domain"], depth,
                        domain_svc, github_svc, gotools_svc,
                    ))
                elif current.get("linkedin"):
                    tasks.append(self._search_linkedin(
                        current["linkedin"], depth,
                        social_svc, company_svc, email_svc,
                    ))
                elif current.get("profile_url"):
                    tasks.append(self._search_profile(
                        current["profile_url"], depth,
                        social_svc, github_svc,
                    ))

            # Run all tasks concurrently for this depth
            if tasks:
                outcomes = await asyncio.gather(*tasks, return_exceptions=True)
                raise_if_intervention(outcomes)

        return self.cascade_results

    async def _search_name(self, name: str, depth: int, people, social, github, company, email, spiderfoot_svc):
        # Run all 4 searches concurrently
        results = await asyncio.gather(
            people.search_by_name(name),
            social.search_by_name(name),
            github.search_users(name),
            spiderfoot_svc.spiderfoot_name_lookup(name),
            return_exceptions=True,
        )

        name_results = results[0] if isinstance(results[0], list) else []
        social_results = results[1] if isinstance(results[1], list) else []
        gh_result = results[2] if not isinstance(results[2], Exception) else None
        sf_result = results[3] if not isinstance(results[3], Exception) else None

        all_results = list(name_results) + list(social_results)
        if gh_result and gh_result.success and gh_result.data:
            all_results.append(gh_result)
        if sf_result and sf_result.success:
            all_results.append(sf_result)

        conns, passive = self._extract_name_connections_from_results(all_results)
        conns = conns[:5]

        for c in conns:
            if self._is_own_data(c):
                self._queue_item(self._conn_to_item(c), depth + 1)

        self.cascade_results.append(CascadeResult(
            subject_type=self.subject_type,
            depth=depth,
            data_type="name",
            data_value=name,
            results=all_results,
            connections=conns,
            passive_data=passive,
        ))
        raise_if_intervention(results)

    async def _search_email(self, email_addr: str, depth: int, email_svc, social, github, company, breach_svc, enrich_svc, spiderfoot_svc, gotools):
        from src.main import run_email_search
        results = await run_email_search(email_addr)

        conns = []
        passive = []

        for r in results:
            if not r.success or not r.data:
                continue
            if r.source == "haveibeenpwned" and r.data.get("breaches"):
                for b in r.data["breaches"][:5]:
                    if b.get("Name"):
                        passive.append(Connection(
                            conn_type="other_profile",
                            value=b["Name"],
                            source_service="hibp_breach",
                            passive=True,
                            label=f"Found in breach: {b['Name']}",
                        ))
            if r.source == "epieos":
                if r.data.get("email"):
                    conns.append(Connection(
                        conn_type="person_email",
                        value=r.data["email"],
                        source_service="epieos",
                    ))
                if r.data.get("github"):
                    conns.append(Connection(
                        conn_type="person_profile",
                        value=r.data["github"],
                        source_service="epieos",
                        label="GitHub from EPIEOS",
                    ))
                if r.data.get("twitter"):
                    conns.append(Connection(
                        conn_type="person_profile",
                        value=r.data["twitter"],
                        source_service="epieos",
                        label="Twitter from EPIEOS",
                    ))

        for c in conns:
            if self._is_own_data(c):
                self._queue_item(self._conn_to_item(c), depth + 1)

        self.cascade_results.append(CascadeResult(
            subject_type=self.subject_type,
            depth=depth,
            data_type="email",
            data_value=email_addr,
            results=results,
            connections=conns,
            passive_data=passive,
        ))

    async def _search_phone(self, phone: str, depth: int, phone_svc, email_svc, social):
        results = await phone_svc.search_by_phone(phone)
        self.cascade_results.append(CascadeResult(
            subject_type=self.subject_type,
            depth=depth,
            data_type="phone",
            data_value=phone,
            results=results,
        ))

    async def _search_nip(self, nip: str, depth: int, company_svc, domain_svc, github):
        results = await company_svc.search_by_nip(nip)
        conns, passive = self._extract_company_connections(results, domain_svc, github)
        for c in conns:
            if self._is_own_data(c):
                self._queue_item(self._conn_to_item(c), depth + 1)
        self.cascade_results.append(CascadeResult(
            subject_type=self.subject_type,
            depth=depth,
            data_type="nip",
            data_value=nip,
            results=results,
            connections=conns,
            passive_data=passive,
        ))

    async def _search_krs(self, krs: str, depth: int, company_svc, domain_svc, github):
        results = await company_svc.search_by_krs(krs)
        conns, passive = self._extract_company_connections(results, domain_svc, github)
        for c in conns:
            if self._is_own_data(c):
                self._queue_item(self._conn_to_item(c), depth + 1)
        self.cascade_results.append(CascadeResult(
            subject_type=self.subject_type,
            depth=depth,
            data_type="krs",
            data_value=krs,
            results=results,
            connections=conns,
            passive_data=passive,
        ))

    async def _search_domain(self, domain: str, depth: int, domain_svc, github, gotools_svc):
        results = await domain_svc.search_by_domain(domain)
        gh_results = await github.search_by_domain(domain)
        if gh_results:
            results.append(gh_results)

        # Go tools subdomain enum - run concurrently
        import asyncio
        from src.services.gotools_service import GoToolsService
        gotools = GoToolsService()
        amass_task = asyncio.create_task(gotools.amass_passive(domain))
        sf_task = asyncio.create_task(gotools.subfinder(domain))
        await asyncio.gather(amass_task, sf_task, return_exceptions=True)

        conns, passive = self._extract_domain_connections(results)
        for c in conns:
            if self._is_own_data(c):
                self._queue_item(self._conn_to_item(c), depth + 1)
        self.cascade_results.append(CascadeResult(
            subject_type=self.subject_type,
            depth=depth,
            data_type="domain",
            data_value=domain,
            results=results,
            connections=conns,
            passive_data=passive,
        ))

    async def _search_linkedin(self, url: str, depth: int, social, company, email):
        username = url.split("linkedin.com/in/")[-1].split("/")[0].split("?")[0]
        results = await social.search_by_username(username)
        conns, passive = self._extract_social_connections(results, company, email)
        for c in conns:
            if self._is_own_data(c):
                self._queue_item(self._conn_to_item(c), depth + 1)
        conns = conns[:5]
        passive = passive[:10]
        self.cascade_results.append(CascadeResult(
            subject_type=self.subject_type,
            depth=depth,
            data_type="linkedin",
            data_value=url,
            results=results,
            connections=conns,
            passive_data=passive,
        ))

    async def _search_profile(self, url: str, depth: int, social, github):
        results = []
        url_lower = url.lower()

        if "linkedin.com/in/" in url_lower:
            username = url.split("linkedin.com/in/")[-1].split("/")[0].split("?")[0]
            results.extend(await social.search_by_username(username))
            conns, passive = self._extract_social_connections(results, None, None)
        elif "github.com/" in url_lower:
            username = url.split("github.com/")[-1].split("/")[0].split("?")[0]
            gh_result = await github.get_user(username)
            results.append(gh_result)
            conns, passive = self._extract_github_connections([gh_result])
        elif "facebook.com/" in url_lower or "fb.com/" in url_lower:
            fb = await social.scrape_facebook(url)
            if fb:
                results.append(fb)
            conns, passive = self._extract_social_connections(results, None, None)
        elif "instagram.com/" in url_lower:
            ig = await social.scrape_instagram(url)
            if ig:
                results.append(ig)
            conns, passive = self._extract_social_connections(results, None, None)
        elif "tiktok.com/" in url_lower:
            tt = await social.scrape_tiktok(url)
            if tt:
                results.append(tt)
            conns, passive = self._extract_social_connections(results, None, None)
        else:
            # For other URLs, scrape as generic profile (boardgamegeek, reddit, etc.)
            fb = await social.scrape_facebook(url)
            if fb:
                results.append(fb)
            conns, passive = self._extract_social_connections(results, None, None)

        for c in conns:
            if self._is_own_data(c):
                self._queue_item(self._conn_to_item(c), depth + 1)
        conns = conns[:5]
        passive = passive[:10]

        self.cascade_results.append(CascadeResult(
            subject_type=self.subject_type,
            depth=depth,
            data_type="profile",
            data_value=url,
            results=results,
            connections=conns,
            passive_data=passive,
        ))

    async def _search_company_name(self, company_name: str, depth: int, company_svc, github, person_name: str = None):
        full_company_name = company_name
        if person_name:
            full_company_name = f"{company_name} {person_name}"
        results = await company_svc.search_by_company_name(full_company_name)
        conns, passive = self._extract_company_connections(results, None, github)
        for c in conns:
            if self._is_own_data(c):
                self._queue_item(self._conn_to_item(c), depth + 1)
        self.cascade_results.append(CascadeResult(
            subject_type=self.subject_type,
            depth=depth,
            data_type="company_name",
            data_value=company_name,
            results=results,
            connections=conns,
            passive_data=passive,
        ))

    def _conn_to_item(self, conn: Connection) -> dict:
        if conn.conn_type in ("person_email", "person_phone", "person_name"):
            if "@" in conn.value:
                return {"email": conn.value}
            if conn.conn_type == "person_phone":
                return {"phone": conn.value}
            return {"name": conn.value}
        if conn.conn_type in ("company_name", "company_domain", "company_nip", "company_krs"):
            if conn.conn_type == "company_domain":
                return {"domain": conn.value}
            if conn.conn_type == "company_nip":
                return {"nip": conn.value}
            if conn.conn_type == "company_krs":
                return {"krs": conn.value}
            return {"company_name": conn.value}
        if conn.conn_type in ("social_profile", "github_repo", "other_profile", "github_blog"):
            if "linkedin.com/in/" in conn.value:
                return {"linkedin": conn.value}
            return {"profile_url": conn.value}
        if conn.conn_type == "github_company":
            # Pass person_name from meta so _search_company_name uses Polish JDG naming
            item = {"company_name": conn.value}
            if conn.meta and conn.meta.get("person_name"):
                item["person_name"] = conn.meta["person_name"]
            return item
        if conn.conn_type == "domain":
            return {"domain": conn.value}
        return {"profile_url": conn.value}

    def _extract_name_connections_from_results(self, results: list) -> tuple:
        conns = []
        passive = []
        for r in results:
            if not r or not r.success:
                continue
            data = r.data if hasattr(r, "data") else {}
            if isinstance(data, dict):
                if data.get("connections"):
                    for c in data["connections"]:
                        if isinstance(c, Connection):
                            conns.append(c)
                        elif isinstance(c, dict):
                            conns.append(Connection(**c))
                if data.get("profiles"):
                    for p in data["profiles"]:
                        if isinstance(p, str):
                            if p.startswith("http"):
                                conns.append(Connection(
                                    conn_type="social_profile",
                                    value=p,
                                    source_service=r.source,
                                ))
                        elif isinstance(p, dict):
                            url = p.get("url", "") or p.get("profile_url", "")
                            if url:
                                conns.append(Connection(
                                    conn_type="social_profile",
                                    value=url,
                                    source_service=r.source,
                                    label=p.get("site", "") or p.get("platform", ""),
                                ))
            if r.source == "github_user_search" and hasattr(r, "data"):
                for user in r.data.get("users", [])[:5]:
                    gh_url = user.get("html_url", "")
                    if gh_url:
                        conns.append(Connection(
                            conn_type="github_repo",
                            value=gh_url,
                            source_service="github",
                            label=f"GitHub: {user.get('login', '')}",
                        ))
        return conns, passive

    def _extract_social_connections(self, results: list, company_svc, email_svc) -> tuple:
        conns = []
        for r in results:
            if not r or not r.success:
                continue
            data = r.data if hasattr(r, "data") else {}
            if isinstance(data, dict):
                if data.get("profiles"):
                    for p in data["profiles"]:
                        if isinstance(p, str):
                            if p.startswith("http"):
                                conns.append(Connection(
                                    conn_type="social_profile",
                                    value=p,
                                    source_service=r.source,
                                ))
                        elif isinstance(p, dict):
                            url = p.get("url", "") or p.get("profile_url", "")
                            if url:
                                conns.append(Connection(
                                    conn_type="social_profile",
                                    value=url,
                                    source_service=r.source,
                                    label=p.get("site", "") or p.get("platform", ""),
                                ))
                if data.get("connections"):
                    for c in data["connections"]:
                        if isinstance(c, Connection):
                            conns.append(c)
                        elif isinstance(c, dict):
                            conns.append(Connection(**c))
        return conns, []

    def _extract_github_connections(self, results: list) -> tuple:
        conns = []
        for r in results:
            if not r or not r.success:
                continue
            data = r.data if hasattr(r, "data") else {}
            if isinstance(data, dict):
                # Extract company (company_name connection)
                company = data.get("company")
                if company and isinstance(company, str) and company.strip():
                    # Attach person_name so _search_company_name can use Polish JDG naming
                    person_name = data.get("name", "")
                    conns.append(Connection(
                        conn_type="github_company",
                        value=company.strip(),
                        source_service="github",
                        label=f"GitHub org: {company.strip()}",
                        meta={"person_name": person_name} if person_name else {},
                    ))

                # Extract blog/website (domain or linkedin connection)
                blog = data.get("blog", "") or data.get("html_url", "")
                if blog and isinstance(blog, str) and blog.strip():
                    blog_lower = blog.lower()
                    if "linkedin.com/in/" in blog_lower:
                        conns.append(Connection(
                            conn_type="github_blog",
                            value=blog.strip(),
                            source_service="github",
                            label="GitHub blog (LinkedIn)",
                        ))
                    elif blog_lower.startswith("http"):
                        conns.append(Connection(
                            conn_type="github_blog",
                            value=blog.strip(),
                            source_service="github",
                            label="GitHub blog",
                        ))

                # Extract repos (existing behaviour)
                repos = data.get("repos", []) or data.get("public_repos", [])
                if isinstance(repos, list):
                    for repo in repos[:5]:
                        if isinstance(repo, dict):
                            repo_url = repo.get("html_url", "")
                            if repo_url:
                                conns.append(Connection(
                                    conn_type="github_repo",
                                    value=repo_url,
                                    source_service="github",
                                    label=repo.get("full_name", ""),
                                ))
        return conns, []

    def _extract_company_connections(self, results: list, domain_svc, github) -> tuple:
        conns = []
        passive = []
        for r in results:
            if not r or not r.success:
                continue
            data = r.data if hasattr(r, "data") else {}
            if isinstance(data, dict):
                if data.get("domain"):
                    conns.append(Connection(
                        conn_type="company_domain",
                        value=data["domain"],
                        source_service=r.source,
                    ))
                if data.get("nip"):
                    conns.append(Connection(
                        conn_type="company_nip",
                        value=data["nip"],
                        source_service=r.source,
                    ))
                if data.get("krs"):
                    conns.append(Connection(
                        conn_type="company_krs",
                        value=data["krs"],
                        source_service=r.source,
                    ))
                if data.get("name"):
                    conns.append(Connection(
                        conn_type="company_name",
                        value=data["name"],
                        source_service=r.source,
                    ))
        return conns, passive

    def _extract_domain_connections(self, results: list) -> tuple:
        conns = []
        for r in results:
            if not r or not r.success:
                continue
            data = r.data if hasattr(r, "data") else {}
            if isinstance(data, dict):
                if data.get("subdomains"):
                    for sd in data["subdomains"][:10]:
                        conns.append(Connection(
                            conn_type="domain",
                            value=sd if isinstance(sd, str) else sd.get("domain", ""),
                            source_service=r.source,
                            passive=True,
                        ))
        return conns, []