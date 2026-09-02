from src.services.base_service import BaseService
from src.models import ServiceResult
import asyncio


class HunterService(BaseService):

    async def domain_search(self, domain: str) -> ServiceResult:
        try:
            api_key = self.get_env("HUNTER_API_KEY")
            if not api_key:
                return ServiceResult(source="hunter_domain", success=False, error="HUNTER_API_KEY not set")
            url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
            data = await self._get(url)
            emails = data.get("data", {}).get("emails", [])
            return ServiceResult(source="hunter_domain", success=True, data={
                "emails": emails,
                "total": data.get("data", {}).get("total"),
            })
        except Exception as e:
            return ServiceResult(source="hunter_domain", success=False, error=str(e))

    async def email_finder(self, first: str, last: str, domain: str) -> ServiceResult:
        try:
            api_key = self.get_env("HUNTER_API_KEY")
            if not api_key:
                return ServiceResult(source="hunter_finder", success=False, error="HUNTER_API_KEY not set")
            url = f"https://api.hunter.io/v2/email-finder?first_name={first}&last_name={last}&domain={domain}&api_key={api_key}"
            data = await self._get(url)
            return ServiceResult(source="hunter_finder", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="hunter_finder", success=False, error=str(e))

    async def email_verifier(self, email: str) -> ServiceResult:
        try:
            api_key = self.get_env("HUNTER_API_KEY")
            if not api_key:
                return ServiceResult(source="hunter_verify", success=False, error="HUNTER_API_KEY not set")
            url = f"https://api.hunter.io/v2/email-verifier/{email}?api_key={api_key}"
            data = await self._get(url)
            return ServiceResult(source="hunter_verify", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="hunter_verify", success=False, error=str(e))

    async def search_by_domain(self, domain: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.domain_search(domain),
            return_exceptions=True,
        )
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="hunter", success=False, error=str(r)))
            else:
                final.append(r)
        return final
