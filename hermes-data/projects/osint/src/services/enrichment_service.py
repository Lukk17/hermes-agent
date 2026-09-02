from src.services.base_service import BaseService
from src.models import ServiceResult
import asyncio


class EnrichmentService(BaseService):

    async def check_hunter_domain(self, domain: str) -> ServiceResult:
        try:
            api_key = self.get_env("HUNTER_API_KEY")
            if not api_key:
                return ServiceResult(source="hunter_domain", success=False, error="HUNTER_API_KEY not set")
            url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
            data = await self._get(url)
            return ServiceResult(source="hunter_domain", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="hunter_domain", success=False, error=str(e))

    async def check_ipqs_email(self, email: str) -> ServiceResult:
        try:
            api_key = self.get_env("IPQS_API_KEY")
            if not api_key:
                return ServiceResult(source="ipqs_email", success=False, error="IPQS_API_KEY not set")
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                r = requests.get(
                    f"https://ipqualityscore.com/api/json/email/{api_key}/{email}?strictness=1",
                    timeout=10,
                )
                return r.json()
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="ipqs_email", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="ipqs_email", success=False, error=str(e))

    async def check_ipqs_phone(self, phone: str) -> ServiceResult:
        try:
            api_key = self.get_env("IPQS_API_KEY")
            if not api_key:
                return ServiceResult(source="ipqs_phone", success=False, error="IPQS_API_KEY not set")
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                r = requests.get(
                    f"https://ipqualityscore.com/api/json/phone/{api_key}/{phone}?strictness=1",
                    timeout=10,
                )
                return r.json()
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="ipqs_phone", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="ipqs_phone", success=False, error=str(e))

    async def search_by_email(self, email: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.check_ipqs_email(email),
            return_exceptions=True,
        )
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="enrichment", success=False, error=str(r)))
            else:
                final.append(r)
        return final

    async def search_by_domain(self, domain: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.check_hunter_domain(domain),
            return_exceptions=True,
        )
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="enrichment", success=False, error=str(r)))
            else:
                final.append(r)
        return final