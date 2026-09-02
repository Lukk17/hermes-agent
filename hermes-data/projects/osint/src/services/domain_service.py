from src.services.base_service import BaseService
from src.models import ServiceResult
from src.ascend_client import HumanInterventionNeeded, ascend_client
import asyncio


class DomainService(BaseService):

    async def check_certspotter(self, domain: str) -> ServiceResult:
        try:
            url = f"https://api.certspotter.com/v1/issuances?domain={domain}&include_subdomains=true&expand=dns_names"
            data = await self._get(url)
            if isinstance(data, list):
                certs = []
                seen = set()
                for entry in data[:50]:
                    for name in entry.get("dns_names", []):
                        if name not in seen and domain in name:
                            seen.add(name)
                            certs.append({
                                "name": name,
                                "issuer": entry.get("issuer", {}).get("name", ""),
                                "date": entry.get("not_before", "")[:10] if entry.get("not_before") else "",
                            })
                return ServiceResult(source="certspotter", success=True, data={"certificates": certs})
            return ServiceResult(source="certspotter", success=True, data={"certificates": []})
        except Exception as e:
            return ServiceResult(source="certspotter", success=False, error=str(e))

    async def check_virustotal(self, domain: str) -> ServiceResult:
        try:
            api_key = self.get_env("VIRUSTOTAL_API_KEY")
            if not api_key:
                return ServiceResult(source="virustotal", success=False, error="VIRUSTOTAL_API_KEY not set")
            url = f"https://www.virustotal.com/api/v3/domains/{domain}"
            headers = {"x-apikey": api_key}
            data = await self._get(url, headers=headers)
            return ServiceResult(source="virustotal", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="virustotal", success=False, error=str(e))

    async def scrape_domain(self, domain: str) -> ServiceResult:
        try:
            result = await ascend_client.scrape(f"https://{domain}", include_links=True, heavy_mode=True)
            content = result.get("content", "")
            return ServiceResult(source="domain_scrape", success=True, data={"raw_content": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except Exception as e:
            return ServiceResult(source="domain_scrape", success=False, error=str(e))

    async def search_by_domain(self, domain: str) -> list[ServiceResult]:
        certspotter_task = asyncio.create_task(self.check_certspotter(domain))
        virustotal_task = asyncio.create_task(self.check_virustotal(domain))
        scrape_task = asyncio.create_task(self.scrape_domain(domain))
        
        done, pending = await asyncio.wait(
            [certspotter_task, virustotal_task, scrape_task],
            timeout=12,
            return_when=asyncio.ALL_COMPLETED,
        )
        for task in pending:
            task.cancel()
        
        results = []
        for task in [certspotter_task, virustotal_task, scrape_task]:
            if task in done:
                try:
                    results.append(task.result())
                except HumanInterventionNeeded:
                    raise
                except Exception as e:
                    results.append(ServiceResult(source="domain", success=False, error=str(e)))
            else:
                results.append(ServiceResult(source="domain", success=False, error="Timeout after 12s"))
        return results