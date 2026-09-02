from src.services.base_service import BaseService
from src.models import ServiceResult
from src.paths import LEAKS_DIR, VENV_PY, scratch_file
import asyncio
import subprocess


def normalize_polish(text: str) -> str:
    """Convert Polish letters to ASCII equivalents."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class BreachService(BaseService):

    async def check_whatsmyname(self, email: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                r = requests.get(
                    f"https://whatsmyname.app/api/search/",
                    params={"target": email},
                    headers={"User-Agent": "OSINT-Tool/1.0"},
                    timeout=15,
                )
                if r.status_code == 200:
                    data = r.json()
                    return {"found": True, "sites": data.get("results", [])}
                return {"found": False, "status": r.status_code}
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="whatsmyname", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="whatsmyname", success=False, error=str(e))

    async def check_intelx(self, email: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                r = requests.post(
                    "https://intelx.io/intelligent/search",
                    json={"term": email, "maxresults": 10, "media": 0, "target": 0},
                    headers={"User-Agent": "OSINT-Tool/1.0", "Content-Type": "application/json"},
                    timeout=20,
                )
                if r.status_code == 200:
                    data = r.json()
                    results = []
                    for hit in data.get("results", [])[:10]:
                        results.append({
                            "type": hit.get("type"),
                            "text": hit.get("text", "")[:200],
                            "url": hit.get("url", ""),
                        })
                    return {"found": True, "results": results}
                return {"found": False, "status": r.status_code}
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="intelx", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="intelx", success=False, error=str(e))

    async def check_breachdirectory(self, email: str) -> ServiceResult:
        try:
            api_key = self.get_env("BREACHDIRECTORY_VIA_RAPIDAPI_API_KEY")
            if not api_key:
                return ServiceResult(source="breachdirectory", success=False, error="BREACHDIRECTORY_VIA_RAPIDAPI_API_KEY not set")
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                url = "https://breachdirectory.p.rapidapi.com/api/"
                headers = {
                    "X-RapidAPI-Key": api_key,
                    "X-RapidAPI-Host": "breachdirectory.p.rapidapi.com",
                }
                params = {"func": "auto", "term": email}
                r = requests.get(url, headers=headers, params=params, timeout=15)
                r.raise_for_status()
                return r.json()
            data = await loop.run_in_executor(None, run_sync)
            if isinstance(data, dict):
                return ServiceResult(source="breachdirectory", success=True, data=data)
            return ServiceResult(source="breachdirectory", success=True, data={"result": data})
        except Exception as e:
            return ServiceResult(source="breachdirectory", success=False, error=str(e))

    async def check_dehashed(self, email: str) -> ServiceResult:
        try:
            api_key = self.get_env("DEHASHED_API_KEY")
            if not api_key:
                return ServiceResult(source="dehashed", success=False, error="DEHASHED_API_KEY not set")
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                url = "https://api.dehashed.com/search"
                headers = {"Authorization": f"Bearer {api_key}"}
                params = {"query": f"email:{email}", "size": 100}
                r = requests.get(url, headers=headers, params=params, timeout=15)
                r.raise_for_status()
                return r.json()
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="dehashed", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="dehashed", success=False, error=str(e))

    async def check_h8mail(self, email: str) -> ServiceResult:
        try:
            out_path = scratch_file("h8mail_out.json")
            loop = asyncio.get_running_loop()
            def run_sync():
                result = subprocess.run(
                    [str(VENV_PY), "-m", "h8mail", "-t", email, "-o", str(out_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                try:
                    import json
                    with open(out_path) as f:
                        return json.load(f)
                except Exception:
                    return {"raw": result.stdout + result.stderr}
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="h8mail", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="h8mail", success=False, error=str(e))

    async def check_holehe(self, email: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                result = subprocess.run(
                    [str(VENV_PY), "-m", "holehe", email, "--only-used", "-NP", "-T", "5"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
                # Filter out BTC donations and GitHub links (holehe dev info)
                # Lines that look like "site : username"
                found = []
                for line in lines:
                    if " : " in line and "BTC" not in line and "github.com/megadose" not in line and "Donation" not in line and "1FHDM" not in line:
                        found.append(line)
                return {"output": found, "total_checked": 117}
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="holehe", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="holehe", success=False, error=str(e))

    async def check_ghostproject(self, email: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                r = requests.get(
                    f"https://ghostproject.fr/",
                    params={"q": email},
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=10,
                )
                if r.status_code == 200:
                    content = r.text
                    # Parse out breach info from HTML
                    found = "found" in content.lower() or "breach" in content.lower()
                    return {"found": found, "content": content[:500]}
                return {"found": False, "status": r.status_code}
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="ghostproject", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="ghostproject", success=False, error=str(e))

    async def check_spiderfoot(self, target: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                result = subprocess.run(
                    ["python3", "-m", "spiderfoot", "-s", target, "-l", "127.0.0.1", "-p", "5555"],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                return {"output": result.stdout[:1000] + result.stderr[:500]}
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="spiderfoot", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="spiderfoot", success=False, error=str(e))

    async def search_local_db(self, email: str) -> ServiceResult:
        try:
            if not LEAKS_DIR.is_dir():
                return ServiceResult(source="local_leak_db", success=True, data={"found": False, "reason": "No data/leaks directory"})
            result = subprocess.run(
                ["grep", "-r", email, str(LEAKS_DIR)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            matches = []
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                matches = [line[:500] for line in lines[:100]]
            return ServiceResult(
                source="local_leak_db",
                success=True,
                data={"found": len(matches) > 0, "matches": matches, "count": len(matches)},
            )
        except Exception as e:
            return ServiceResult(source="local_leak_db", success=False, error=str(e))

    async def search_by_email(self, email: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.check_holehe(email),
            self.check_ghostproject(email),
            self.check_whatsmyname(email),
            self.check_intelx(email),
            self.check_breachdirectory(email),
            self.check_dehashed(email),
            self.check_h8mail(email),
            self.search_local_db(email),
            return_exceptions=True,
        )
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="breach", success=False, error=str(r)))
            else:
                final.append(r)
        return final