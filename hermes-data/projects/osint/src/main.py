import asyncio
import argparse
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # secrets come from container env (fork repo .env), not workspace .env

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import OsintQuery, OsintResponse, ServiceResult
from src.ascend_client import HumanInterventionNeeded
from src.captcha_handler import HumanInterventionPending, get_captcha_handler
from src.paths import INTERVENTIONS_DIR
from src.report_renderer import renderer
from src.services.email_service import EmailService
from src.services.phone_service import PhoneService
from src.services.people_service import PeopleService
from src.services.company_service import CompanyService
from src.services.domain_service import DomainService
from src.services.breach_service import BreachService
from src.services.social_service import SocialService
from src.services.github_service import GitHubService
from src.services.local_leak_service import local_leak_service
from src.services.hunter_service import HunterService
from src.services.enrichment_service import EnrichmentService
from src.services.infra_service import InfraService
from src.services.recon_service import ReconService
from src.services.social_extra_service import SocialExtraService
from src.services.darkweb_service import DarkWebService

EXIT_HUMAN_INTERVENTION = 3


class ResumeStateMissing(FileNotFoundError):
    """No paused run was persisted under the given resume token."""


class InterventionRequired(Exception):
    """A captcha wall paused the run; carries everything main() must persist."""

    def __init__(self, needed: HumanInterventionNeeded, query: OsintQuery, partial_results: list):
        self.needed = needed
        self.query = query
        self.partial_results = partial_results
        super().__init__(str(needed))


async def run_email_search(email: str) -> list[ServiceResult]:
    from src.services.email_service import EmailService
    from src.services.spiderfoot_service import SpiderFootService
    from src.services.breach_service import BreachService
    from src.services.enrichment_service import EnrichmentService
    from src.services.gotools_service import GoToolsService
    service = EmailService()
    breach = BreachService()
    enrich = EnrichmentService()
    gotools = GoToolsService()
    sf = SpiderFootService()
    results = await service.search_by_email(email)
    results.extend(await breach.search_by_email(email))
    results.extend(await enrich.search_by_email(email))
    results.append(await sf.spiderfoot_email_lookup(email))
    results.append(await gotools.mosint_lookup(email))
    return results


async def run_phone_search(phone: str) -> list[ServiceResult]:
    service = PhoneService()
    return await service.search_by_phone(phone)


async def run_name_search(name: str, location: str = None) -> list[ServiceResult]:
    from src.services.spiderfoot_service import SpiderFootService
    results = []
    people = PeopleService()
    social = SocialService()
    social_extra = SocialExtraService()
    github = GitHubService()
    company = CompanyService()
    recon = ReconService()
    sf = SpiderFootService()
    results.extend(await people.search_by_name(name))
    results.extend(await social.search_by_name(name, location))
    results.extend(await github.search_users(name))
    results.append(await company.search_courts(name))
    results.append(await sf.spiderfoot_name_lookup(name))
    return results


async def run_linkedin_search(linkedin_url: str) -> list[ServiceResult]:
    service = SocialService()
    username_match = linkedin_url.split("linkedin.com/in/")[-1].split("/")[0].split("?")[0]
    return await service.search_by_username(username_match)


async def run_nip_search(nip: str) -> list[ServiceResult]:
    service = CompanyService()
    results = await service.search_by_nip(nip)
    results.append(await service.search_courts(nip))
    return results


async def run_krs_search(krs: str) -> list[ServiceResult]:
    service = CompanyService()
    results = await service.search_by_krs(krs)
    results.append(await service.search_courts(krs))
    return results


async def run_domain_search(domain: str) -> list[ServiceResult]:
    results = []
    domain_svc = DomainService()
    github = GitHubService()
    infra = InfraService()
    recon = ReconService()
    hunter = HunterService()
    gotools = GoToolsService()

    domain_task = asyncio.create_task(domain_svc.search_by_domain(domain))
    github_task = asyncio.create_task(github.search_by_domain(domain))
    infra_task = asyncio.create_task(infra.search_by_domain(domain))
    recon_task = asyncio.create_task(recon.search_by_domain(domain))
    hunter_task = asyncio.create_task(hunter.search_by_domain(domain))
    amass_task = asyncio.create_task(gotools.amass_passive(domain))
    subfinder_task = asyncio.create_task(gotools.subfinder(domain))
    dnsrecon_task = asyncio.create_task(gotools.dnsrecon_enum(domain))

    all_tasks = [domain_task, github_task, infra_task, recon_task, hunter_task, amass_task, subfinder_task, dnsrecon_task]
    done, pending = await asyncio.wait(all_tasks, timeout=25, return_when=asyncio.ALL_COMPLETED)
    for t in pending:
        t.cancel()

    task_map = {
        domain_task: "domain_svc", github_task: "github", infra_task: "infra",
        recon_task: "recon", hunter_task: "hunter", amass_task: "amass",
        subfinder_task: "subfinder", dnsrecon_task: "dnsrecon",
    }
    for t in all_tasks:
        if t in done:
            try:
                results.extend(t.result())
            except Exception as e:
                results.append(ServiceResult(source=task_map[t], success=False, error=str(e)))
        else:
            results.append(ServiceResult(source=task_map[t], success=False, error=f"{task_map[t]} timeout after 25s"))

    # httpx probe on subdomains found by Amass/Subfinder
    all_subdomains = set()
    for r in results:
        if r.success and isinstance(r.data, dict):
            subs = r.data.get("subdomains", [])
            for s in subs:
                if not s.startswith("http"):
                    s = "https://" + s
                all_subdomains.add(s)
    if all_subdomains:
        httpx_result = await gotools.httpx_probe(list(all_subdomains)[:50])
        results.append(httpx_result)

    return results


async def run_breach_search(email: str) -> list[ServiceResult]:
    service = BreachService()
    enrichment = EnrichmentService()
    results = await service.search_by_email(email)
    results.extend(await enrichment.search_by_email(email))
    local_result = local_leak_service.search_by_email(email)
    results.append(local_result)
    return results


async def run_github_search(github_input: str) -> list[ServiceResult]:
    service = GitHubService()
    if "/" in github_input and not github_input.startswith("http"):
        return await service.search_by_org(github_input)
    return await service.search_users(github_input)


async def dispatch_queries(query: OsintQuery) -> OsintResponse:
    response = OsintResponse(query=query)
    tasks = []

    if query.email:
        tasks.append(("email", run_email_search(query.email)))
        tasks.append(("breach", run_breach_search(query.email)))

    if query.phone:
        tasks.append(("phone", run_phone_search(query.phone)))
        local_result = local_leak_service.search_by_phone(query.phone)
        response.results.append(local_result)

    if query.name:
        tasks.append(("people", run_name_search(query.name, query.location)))

    if query.nip:
        tasks.append(("company_nip", run_nip_search(query.nip)))

    if query.krs:
        tasks.append(("company_krs", run_krs_search(query.krs)))

    if query.domain:
        tasks.append(("domain", run_domain_search(query.domain)))
        tasks.append(("github", run_github_search(query.domain)))

    if query.linkedin:
        tasks.append(("linkedin", run_linkedin_search(query.linkedin)))

    intervention = None

    try:
        if tasks:
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            task_names = [name for name, _ in tasks]
            for i, result in enumerate(results):
                task_name = task_names[i]
                if isinstance(result, HumanInterventionNeeded):
                    intervention = intervention or result
                elif isinstance(result, Exception):
                    response.errors.append(f"{task_name}: {str(result)}")
                elif isinstance(result, list):
                    for item in result:
                        if isinstance(item, ServiceResult):
                            response.results.append(item)
                elif isinstance(result, ServiceResult):
                    response.results.append(result)
    finally:
        from src.ascend_client import ascend_client
        await ascend_client.close()

    if intervention is not None:
        intervention.partial_results = [r.model_dump() for r in response.results]
        raise intervention

    return response


def parse_raw_input(raw: str) -> OsintQuery:
    fields = {
        "email": None,
        "phone": None,
        "name": None,
        "location": None,
        "nip": None,
        "pesel": None,
        "krs": None,
        "domain": None,
        "linkedin": None,
        "ceidg_url": None,
        "plate": None,
        "vin": None,
    }

    import re
    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    phone_pattern = re.compile(r"^\+?[0-9]{9,15}$")
    nip_pattern = re.compile(r"^\d{10}$")
    krs_pattern = re.compile(r"^\d{10}$")
    vin_pattern = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$", re.IGNORECASE)
    plate_pattern = re.compile(r"^[A-Z]{2}[0-9]{4,5}[A-Z]{0,2}$", re.IGNORECASE)
    domain_pattern = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$", re.IGNORECASE)
    linkedin_pattern = re.compile(r"linkedin\.com/in/([^/\?]+)")

    tokens = [t.strip() for t in raw.split() if t.strip()]
    label_map_upper = {"NIP": "nip", "KRS": "krs", "PESEL": "pesel", "VIN": "vin", "PLATE": "plate", "TEL": "phone", "PHONE": "phone", "NAME": "name", "DOMAIN": "domain", "LINKEDIN": "linkedin"}

    skip_indices: set[int] = set()
    assigned_values: set[str] = set()

    for i, token in enumerate(tokens):
        if ":" in token:
            key, val = token.split(":", 1)
            if key.upper() not in label_map_upper:
                continue
            field_name = label_map_upper[key.upper()]
            if field_name == "email" and email_pattern.match(val):
                fields["email"] = val
                assigned_values.add(val)
            elif field_name == "phone" and phone_pattern.match(val):
                fields["phone"] = val
                assigned_values.add(val)
            elif field_name == "nip" and nip_pattern.match(val):
                fields["nip"] = val
                assigned_values.add(val)
            elif field_name == "krs" and krs_pattern.match(val):
                fields["krs"] = val
                assigned_values.add(val)
            elif field_name == "vin" and vin_pattern.match(val):
                fields["vin"] = val
                assigned_values.add(val)
            elif field_name == "plate" and plate_pattern.match(val):
                fields["plate"] = val
                assigned_values.add(val)
            elif field_name == "name":
                parts = [val]
                skip_indices.add(i)
                for j in range(i + 1, len(tokens)):
                    t = tokens[j]
                    if t.upper() in label_map_upper or ":" in t:
                        break
                    parts.append(t)
                    skip_indices.add(j)
                fields["name"] = " ".join(parts)
            elif field_name == "domain":
                fields["domain"] = val
                assigned_values.add(val)
            elif field_name == "linkedin":
                fields["linkedin"] = val if val.startswith("http") else f"https://www.linkedin.com/in/{val}"
                assigned_values.add(val)
            continue
            field_name = label_map_upper[key.upper()]
            if field_name == "phone" and phone_pattern.match(val):
                fields["phone"] = val
                assigned_values.add(val)
            elif field_name == "nip" and nip_pattern.match(val):
                fields["nip"] = val
                assigned_values.add(val)
            elif field_name == "krs" and krs_pattern.match(val):
                fields["krs"] = val
                assigned_values.add(val)
            elif field_name == "vin" and vin_pattern.match(val):
                fields["vin"] = val
                assigned_values.add(val)
            elif field_name == "plate" and plate_pattern.match(val):
                fields["plate"] = val
                assigned_values.add(val)
            elif field_name == "name":
                parts = [val]
                skip_indices.add(i)
                for j in range(i + 1, len(tokens)):
                    t = tokens[j]
                    if t.upper() in label_map_upper or ":" in t:
                        break
                    parts.append(t)
                    skip_indices.add(j)
                fields["name"] = " ".join(parts)
            elif field_name == "domain":
                fields["domain"] = val
                assigned_values.add(val)
            elif field_name == "linkedin":
                fields["linkedin"] = val if val.startswith("http") else f"https://www.linkedin.com/in/{val}"
                assigned_values.add(val)
            continue

        token_upper = token.upper()
        if token_upper in label_map_upper and i + 1 < len(tokens):
            next_token = tokens[i + 1]
            if next_token in skip_indices:
                continue
            field_name = label_map_upper[token_upper]
            if field_name == "phone" and phone_pattern.match(next_token):
                fields["phone"] = next_token
                assigned_values.add(next_token)
                skip_indices.add(i + 1)
            elif field_name == "nip" and nip_pattern.match(next_token):
                fields["nip"] = next_token
                assigned_values.add(next_token)
                skip_indices.add(i + 1)
            elif field_name == "krs" and krs_pattern.match(next_token):
                fields["krs"] = next_token
                assigned_values.add(next_token)
                skip_indices.add(i + 1)
            elif field_name == "vin" and vin_pattern.match(next_token):
                fields["vin"] = next_token
                assigned_values.add(next_token)
                skip_indices.add(i + 1)
            elif field_name == "plate" and plate_pattern.match(next_token):
                fields["plate"] = next_token
                assigned_values.add(next_token)
                skip_indices.add(i + 1)
            elif field_name == "name":
                parts = [next_token]
                skip_indices.add(i + 1)
                for j in range(i + 2, len(tokens)):
                    t = tokens[j]
                    if t.upper() in label_map_upper or ":" in t:
                        break
                    parts.append(t)
                    skip_indices.add(j)
                fields["name"] = " ".join(parts)
            continue

        if i in skip_indices:
            continue
        if token in assigned_values:
            continue
        if email_match := email_pattern.search(token):
            fields["email"] = email_match.group(0)
            assigned_values.add(token)
        elif linkedin_match := linkedin_pattern.search(token):
            fields["linkedin"] = token if token.startswith("http") else f"https://www.linkedin.com/in/{linkedin_match.group(1)}"
            assigned_values.add(token)
        elif token.startswith("http://") or token.startswith("https://"):
            if "ceidg" in token:
                fields["ceidg_url"] = token
            elif "linkedin" in token:
                fields["linkedin"] = token
            elif domain_pattern.match(token):
                fields["domain"] = token
            assigned_values.add(token)
        elif plate_pattern.match(token) and fields["plate"] is None:
            fields["plate"] = token
            assigned_values.add(token)
        elif vin_pattern.match(token) and fields["vin"] is None:
            fields["vin"] = token
            assigned_values.add(token)
        elif domain_pattern.match(token) and fields["domain"] is None:
            fields["domain"] = token
            assigned_values.add(token)
        elif nip_pattern.match(token) and fields["nip"] is None:
            fields["nip"] = token
            assigned_values.add(token)
        elif krs_pattern.match(token) and fields["krs"] is None:
            fields["krs"] = token
            assigned_values.add(token)
        elif phone_pattern.match(token) and fields["phone"] is None:
            fields["phone"] = token
            assigned_values.add(token)
        elif token.lower() in ("and", "or", "the", "of"):
            continue
        else:
            if fields["name"] is None:
                fields["name"] = token
            else:
                fields["name"] += " " + token

    return OsintQuery(**{k: v for k, v in fields.items() if v is not None})


def state_file(resume_token: str) -> Path:
    return INTERVENTIONS_DIR / f"{resume_token}.json"


def load_resume_state(resume_token: str) -> dict:
    """Load the state persisted when a run paused for a human.

    Raises:
        ResumeStateMissing: when no run was paused under that token.
    """
    path = state_file(resume_token)
    if not path.exists():
        raise ResumeStateMissing(f"No paused run for token {resume_token} ({path})")
    return json.loads(path.read_text(encoding="utf-8"))


def save_resume_state(pending: HumanInterventionPending, paused: "InterventionRequired") -> Path:
    """Persist the paused run so `--resume <token>` can continue it."""
    path = state_file(pending.resume_token)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "intervention": pending.to_dict(),
        "query": paused.query.model_dump(),
        "partial_results": paused.partial_results,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


async def main_async(args: argparse.Namespace) -> tuple:
    resumed_results: list[ServiceResult] = []

    if args.resume:
        state = load_resume_state(args.resume)
        query = OsintQuery(**state["query"])
        resumed_results = [ServiceResult(**r) for r in state.get("partial_results", [])]
    elif args.input:
        query_dict = json.loads(args.input)
        query = OsintQuery(**query_dict)
    elif args.query:
        query = parse_raw_input(args.query)
    else:
        print("Error: Provide --query, --input or --resume", file=sys.stderr)
        sys.exit(1)

    try:
        if getattr(args, "no_cascade", False):
            response = await dispatch_queries(query)
            cascade_results = None
        else:
            response, cascade_results = await dispatch_queries_cascade(query)
    except HumanInterventionNeeded as exc:
        carried = [r.model_dump() for r in resumed_results] + exc.partial_results
        raise InterventionRequired(exc, query, carried) from exc

    response.results = resumed_results + response.results
    return response, cascade_results


def flatten_cascade(cascade_results: list) -> list[ServiceResult]:
    """Flatten cascade results into ServiceResults tagged with their cascade origin."""
    flattened = []
    for cr in cascade_results:
        for service_result in cr.results:
            service_result.data = service_result.data or {}
            service_result.data["_cascade_depth"] = cr.depth
            service_result.data["_cascade_data_type"] = cr.data_type
            service_result.data["_cascade_data_value"] = cr.data_value
            flattened.append(service_result)
    return flattened


async def dispatch_queries_cascade(query: OsintQuery) -> tuple:
    from src.cascade_engine import CascadeEngine
    engine = CascadeEngine(query, max_depth=3)

    try:
        cascade_results = await engine.run()
    except HumanInterventionNeeded as exc:
        exc.partial_results = [r.model_dump() for r in flatten_cascade(engine.cascade_results)]
        raise
    finally:
        from src.ascend_client import ascend_client
        await ascend_client.close()

    response = OsintResponse(query=query)
    response.results.extend(flatten_cascade(cascade_results))

    return response, cascade_results


def pause_for_human(paused: InterventionRequired) -> dict:
    """Deliver the captcha prompt, persist the run, and describe how to resume it.

    Runs outside the event loop: delivery shells out to the agent runtime.
    """
    pending = None
    try:
        get_captcha_handler().handle_intervention(paused.needed, paused.needed.url)
    except HumanInterventionPending as exc:
        pending = exc

    if pending is None:
        raise RuntimeError("handle_intervention returned without pausing the run")

    state_path = save_resume_state(pending, paused)
    record = {
        "status": "human_intervention_required",
        "resume_command": f"src/main.py --resume {pending.resume_token}",
        "state_file": str(state_path),
        "partial_result_count": len(paused.partial_results),
    }
    record.update(pending.to_dict())
    return record


def main():
    parser = argparse.ArgumentParser(description="OSINT Runner")
    parser.add_argument("--query", type=str, help="Raw query string to parse")
    parser.add_argument("--input", type=str, help="JSON input for structured query")
    parser.add_argument("--type", type=str, choices=["email", "phone", "person", "nip", "krs", "domain"], help="Query type hint")
    parser.add_argument("--location", type=str, help="Location for person search")
    parser.add_argument("--format", type=str, default="json", choices=["json", "markdown"], help="Output format")
    parser.add_argument("--no-cascade", action="store_true", help="Disable cascade search (one-shot mode)")
    parser.add_argument("--resume", type=str, metavar="TOKEN", help="Resume a run paused for human captcha solving")
    args = parser.parse_args()

    try:
        response, cascade_results = asyncio.run(main_async(args))
    except InterventionRequired as paused:
        print(json.dumps(pause_for_human(paused), indent=2))
        sys.exit(EXIT_HUMAN_INTERVENTION)
    except ResumeStateMissing as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.format == "markdown":
        if cascade_results:
            print(renderer.render_cascade(cascade_results, response.query))
        else:
            print(renderer.render(response))
    else:
        print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
