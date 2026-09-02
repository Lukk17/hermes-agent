from src.services.base_service import BaseService, raise_if_intervention
from src.models import ServiceResult
from src.ascend_client import HumanInterventionNeeded, ascend_client
import asyncio
import re


class PolishGovService(BaseService):

    async def search_krs_online(self, query: str) -> ServiceResult:
        """Polish KRS (National Court Register) - via ascend scraper."""
        try:
            result = await ascend_client.scrape(
                    f"https://www.krs-online.com.pl/?search={query}",
                    include_links=True,
                    heavy_mode=True,
            )
            content = result.get("content", "")
            # Extract company links from the content
            links = []
            for match in re.finditer(r'href="(/firma/[^"]+)"[^>]*>([^<]+)</a>', content):
                href = match.group(1)
                text = match.group(2).strip()
                if text and len(text) > 2:
                    links.append(f"{text}: https://www.krs-online.com.pl{href}")
            return ServiceResult(source="krs_online", success=True, data={
                "raw_content": content[:3000],
                "company_links": links[:20],
            })
        except HumanInterventionNeeded:
            raise
        except asyncio.TimeoutError:
            return ServiceResult(source="krs_online", success=False, error="Timeout after 15s")
        except Exception as e:
            return ServiceResult(source="krs_online", success=False, error=str(e))

    async def search_rejestr_io(self, query: str) -> ServiceResult:
        """Polish business registry - free API at api.rejestr.io.
        
        Note: api.rejestr.io DNS fails specifically from this machine (returns NXDOMAIN),
        while other domains resolve fine. This is a domain-level block or the domain
        may be unreachable from this IP. Try from a browser on the host machine.
        """
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                try:
                    r = requests.get(
                        f"https://api.rejestr.io/api/v1/search",
                        params={"q": query},
                        headers={"User-Agent": "OSINT-Tool/1.0"},
                        timeout=10,
                    )
                    r.raise_for_status()
                    return r.json()
                except requests.exceptions.ConnectionError as e:
                    return {"error": f"Connection failed: {e}"}
                except requests.exceptions.HTTPError as e:
                    return {"error": f"HTTP {e.response.status_code}: {e}"}
                except Exception as e:
                    return {"error": str(e)}
            data = await loop.run_in_executor(None, run_sync)
            if "error" in data:
                return ServiceResult(source="rejestr_io", success=False, error=data["error"])
            return ServiceResult(source="rejestr_io", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="rejestr_io", success=False, error=str(e))

    async def search_ekrs(self, krs: str = None, name: str = None) -> ServiceResult:
        """Polish eKRS - via ascend scraper."""
        try:
            url = "https://ekrs.ms.gov.pl/web/wyszukiwarka-krs"
            result = await ascend_client.scrape(url, include_links=True, heavy_mode=True
            )
            content = result.get("content", "")
            return ServiceResult(source="ekrs", success=True, data={"raw_content": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except asyncio.TimeoutError:
            return ServiceResult(source="ekrs", success=False, error="Timeout after 15s")
        except Exception as e:
            return ServiceResult(source="ekrs", success=False, error=str(e))

    async def search_ceidg(self, nip: str = None, name: str = None) -> ServiceResult:
        """Polish CEIDG (Centralna Ewidencja i Informacja o Działalności Gospodarczej) - via ascend scraper."""
        try:
            params = {}
            if nip:
                params["Nip"] = nip
            if name:
                params["NazwiskaImie"] = name
            query_str = "&".join(f"{k}={v}" for k, v in params.items())
            url = "https://aplikacja.ceidg.gov.pl/ceidg/ceidg.public.ui/Search.aspx"
            if query_str:
                url += "?" + query_str
            result = await ascend_client.scrape(url, include_links=True, heavy_mode=True
            )
            content = result.get("content", "")
            return ServiceResult(source="ceidg", success=True, data={"raw_content": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except asyncio.TimeoutError:
            return ServiceResult(source="ceidg", success=False, error="Timeout after 15s")
        except Exception as e:
            return ServiceResult(source="ceidg", success=False, error=str(e))

    async def search_regon(self, nip: str = None, name: str = None) -> ServiceResult:
        """Polish REGON (National Business Registry Number) - via ascend scraper."""
        try:
            url = "https://wyszukiwarkaregon.stat.gov.pl/appBIR/index.aspx"
            result = await ascend_client.scrape(url, include_links=True, heavy_mode=True
            )
            content = result.get("content", "")
            return ServiceResult(source="regon", success=True, data={"raw_content": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except asyncio.TimeoutError:
            return ServiceResult(source="regon", success=False, error="Timeout after 15s")
        except Exception as e:
            return ServiceResult(source="regon", success=False, error=str(e))

    async def search_vat_registry(self, nip: str) -> ServiceResult:
        """Polish VAT taxpayers registry - via ascend scraper."""
        try:
            result = await ascend_client.scrape(
                    "https://www.podatki.gov.pl/wykaz-podatnikow-vat-wyszukiwarka",
                    include_links=True,
                    heavy_mode=True,
            )
            content = result.get("content", "")
            return ServiceResult(source="vat_registry", success=True, data={"raw_content": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except asyncio.TimeoutError:
            return ServiceResult(source="vat_registry", success=False, error="Timeout after 15s")
        except Exception as e:
            return ServiceResult(source="vat_registry", success=False, error=str(e))

    async def search_krd(self, query: str) -> ServiceResult:
        """Polish KRD (Credit Bureau) - via ascend scraper."""
        try:
            result = await ascend_client.scrape(
                    f"https://krd.pl/",
                    include_links=True,
                    heavy_mode=True,
            )
            content = result.get("content", "")
            return ServiceResult(source="krd", success=True, data={"raw_content": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except asyncio.TimeoutError:
            return ServiceResult(source="krd", success=False, error="Timeout after 15s")
        except Exception as e:
            return ServiceResult(source="krd", success=False, error=str(e))

    async def search_by_name(self, name: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.search_rejestr_io(name),
            self.search_krs_online(name),
            self.search_ekrs(name=name),
            self.search_ceidg(name=name),
            self.search_krd(name),
            return_exceptions=True,
        )
        raise_if_intervention(results)
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="polish_gov", success=False, error=str(r)))
            else:
                final.append(r)
        return final

    async def search_by_nip(self, nip: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.search_ceidg(nip=nip),
            self.search_vat_registry(nip),
            return_exceptions=True,
        )
        raise_if_intervention(results)
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="polish_gov", success=False, error=str(r)))
            else:
                final.append(r)
        return final
