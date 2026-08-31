import asyncio
from src.services.base_service import BaseService
from src.models import ServiceResult


class PhoneService(BaseService):

    async def check_numverify(self, phone: str) -> ServiceResult:
        try:
            api_key = self.get_env("NUMVERIFY_API_KEY")
            if not api_key:
                return ServiceResult(source="numverify", success=False, error="NUMVERIFY_API_KEY not set")
            url = f"http://apilayer.net/api/validate?access_key={api_key}&number={phone}"
            data = await self._get(url)
            return ServiceResult(source="numverify", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="numverify", success=False, error=str(e))

    async def check_abstract_phone(self, phone: str) -> ServiceResult:
        try:
            api_key = self.get_env("ABSTRACT_API_KEY")
            if not api_key:
                return ServiceResult(source="abstract_phone", success=False, error="ABSTRACT_API_KEY not set")
            url = f"https://phonevalidation.abstractapi.com/v1/?api_key={api_key}&number={phone}"
            data = await self._get(url)
            return ServiceResult(source="abstract_phone", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="abstract_phone", success=False, error=str(e))

    async def check_ipqs_phone(self, phone: str) -> ServiceResult:
        try:
            api_key = self.get_env("IPQS_API_KEY")
            if not api_key:
                return ServiceResult(source="ipqs_phone", success=False, error="IPQS_API_KEY not set")
            url = f"https://ipqualityscore.com/api/json/phone/{api_key}/{phone}?strictness=1"
            data = await self._get(url)
            return ServiceResult(source="ipqs_phone", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="ipqs_phone", success=False, error=str(e))

    async def search_by_phone(self, phone: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.check_numverify(phone),
            self.check_abstract_phone(phone),
            self.check_ipqs_phone(phone),
            return_exceptions=True,
        )
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="phone", success=False, error=str(r)))
            else:
                final.append(r)
        return final