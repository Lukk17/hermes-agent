from src.services.base_service import BaseService
from src.models import ServiceResult
import asyncio


def normalize_polish(text: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class EmailService(BaseService):

    async def check_emailrep(self, email: str) -> ServiceResult:
        try:
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                r = requests.get(
                    f"https://api.emailrep.io/{email}",
                    headers={"User-Agent": "OSINT-Tool"},
                    timeout=10,
                )
                return r.json()
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="emailrep", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="emailrep", success=False, error=str(e))

    async def check_hunter_verify(self, email: str) -> ServiceResult:
        try:
            api_key = self.get_env("HUNTER_API_KEY")
            if not api_key:
                return ServiceResult(source="hunter_verify", success=False, error="HUNTER_API_KEY not set")
            url = f"https://api.hunter.io/v2/email-verifier/{email}?api_key={api_key}"
            data = await self._get(url)
            return ServiceResult(source="hunter_verify", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="hunter_verify", success=False, error=str(e))

    async def check_ghostproject(self, email: str) -> ServiceResult:
        try:
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                r = requests.get(
                    f"https://ghostproject.fr/?q={email}",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=10,
                )
                if r.status_code == 200:
                    return {"found": True, "content": r.text[:500]}
                return {"found": False, "status": r.status_code}
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="ghostproject", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="ghostproject", success=False, error=str(e))

    async def search_by_email(self, email: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.check_emailrep(email),
            self.check_hunter_verify(email),
            self.check_ghostproject(email),
            return_exceptions=True,
        )
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="email", success=False, error=str(r)))
            else:
                final.append(r)
        return final