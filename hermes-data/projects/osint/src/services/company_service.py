from src.services.base_service import BaseService, raise_if_intervention
from src.models import ServiceResult
from src.ascend_client import HumanInterventionNeeded, ascend_client
import asyncio


class CompanyService(BaseService):

    async def search_courts(self, query: str, court_system: str = "all") -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                court_url = "https://orzeczenia.ms.gov.pl/search"
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                }
                data = {"q": query, f"court[0]": court_system}
                r = requests.post(court_url, data=data, headers=headers, timeout=20)
                return r.text
            text = await loop.run_in_executor(None, run_sync)
            if text:
                links = []
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if "orzeczenia" in href.lower():
                            full = "https://orzeczenia.ms.gov.pl" + href if href.startswith("/") else href
                            links.append(full)
                except Exception:
                    pass
                return ServiceResult(source="courts", success=True, data={"query": query, "raw_snippet": text[:3000], "links": links[:20]})
            return ServiceResult(source="courts", success=False, error="Empty response")
        except Exception as e:
            return ServiceResult(source="courts", success=False, error=str(e))

    async def scrape_ceidg(self, nip: str) -> ServiceResult:
        try:
            ceidg_url = f"https://aplikacja.ceidg.gov.pl/ceidg/ceidg.public.ui/Search.aspx?Nip={nip}"
            result = await ascend_client.scrape(ceidg_url)
            content = result.get("content", "")
            parsed = {}
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, "html.parser")
                for td in soup.find_all("td"):
                    label = td.get_text(strip=True)
                    next_td = td.find_next_sibling("td")
                    if next_td and label:
                        parsed[label] = next_td.get_text(strip=True)
            except Exception:
                pass
            return ServiceResult(source="ceidg", success=True, data={"parsed": parsed, "raw_snippet": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except Exception as e:
            return ServiceResult(source="ceidg", success=False, error=str(e))

    async def search_ekrs_json(self, krs: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                base_url = "https://ekrs.ms.gov.pl"
                search_url = f"{base_url}/web/wyszukiwarka-krs"
                rdf_url = f"{base_url}/rdf/pd/search_df"
                session = requests.Session()
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                }
                session.get(search_url, headers=headers, timeout=15)
                form_data = {"krs": krs, "rejestr": "0"}
                rdf_headers = {
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/xml",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": search_url,
                }
                resp = session.post(rdf_url, data=form_data, headers=rdf_headers, timeout=20)
                return resp.text
            text = await loop.run_in_executor(None, run_sync)
            if text and "<" in text and not text.strip().startswith("<!doctype"):
                return ServiceResult(source="ekrs_json", success=True, data={"raw_xml": text[:5000]})
            return ServiceResult(source="ekrs_json", success=False, error="eKRS requires JavaScript session")
        except Exception as e:
            return ServiceResult(source="ekrs_json", success=False, error=str(e))

    async def scrape_ekrs(self, krs: str) -> ServiceResult:
        try:
            ekrs_url = f"https://ekrs.ms.gov.pl/web/wyszukiwarka-krs/{krs}"
            result = await ascend_client.scrape(ekrs_url)
            content = result.get("content", "")
            return ServiceResult(source="ekrs", success=True, data={"raw_snippet": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except Exception as e:
            return ServiceResult(source="ekrs", success=False, error=str(e))

    async def scrape_vat_registry(self, nip: str) -> ServiceResult:
        try:
            vat_url = "https://www.podatki.gov.pl/wykaz-podatnikow-vat-wyszukiwarka"
            result = await ascend_client.scrape(vat_url)
            content = result.get("content", "")
            return ServiceResult(source="vat_registry", success=True, data={"raw_snippet": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except Exception as e:
            return ServiceResult(source="vat_registry", success=False, error=str(e))

    async def search_opencorporates(self, company_name: str) -> ServiceResult:
        """OpenCorporates company search. Requires API key (no free tier).
        
        Register at https://opencorporates.com/api/signup to get an API key.
        Add OPENCORPORATES_API_KEY to your environment.
        """
        try:
            url = f"https://api.opencorporates.com/v0.4.8/companies/search?q={company_name}"
            data = await self._get(url)
            return ServiceResult(source="opencorporates", success=True, data=data)
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "Unauthorized" in err_str:
                return ServiceResult(source="opencorporates", success=False, error="No API key: OpenCorporates has no free tier. Register at opencorporates.com/api for an API key, then set OPENCORPORATES_API_KEY")
            return ServiceResult(source="opencorporates", success=False, error=err_str)

    async def search_sec_edgar(self, company_name: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                url = f"https://efts.sec.gov/LATEST/search-index?q={company_name}&dateRange=custom"
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; OSINT-Tool/1.0)",
                    "Accept": "application/json",
                }
                r = requests.get(url, headers=headers, timeout=15)
                r.raise_for_status()
                return r.json()
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="sec_edgar", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="sec_edgar", success=False, error=str(e))

    async def search_companies_house(self, company_name: str) -> ServiceResult:
        try:
            api_key = self.get_env("COMPANIES_HOUSE_API_KEY")
            if not api_key:
                return ServiceResult(source="companies_house", success=False, error="COMPANIES_HOUSE_API_KEY not set")
            url = f"https://api.companyhouse.gov.uk/search/companies?q={company_name}"
            auth = (api_key, "")
            data = await self._get(url, auth=auth)
            return ServiceResult(source="companies_house", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="companies_house", success=False, error=str(e))

    async def check_vies_vat(self, vat_number: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import zeep
                client = zeep.Client("https://ec.europa.eu/taxation_customs/vies/services/checkVatService")
                country = vat_number[:2]
                number = vat_number[2:].replace(" ", "")
                result = client.service.checkVat(country_code=country, vat_number=number)
                return {"valid": result.valid, "name": result.name, "address": result.address, "country": country}
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="vies_vat", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="vies_vat", success=False, error=str(e))

    async def search_by_nip(self, nip: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.scrape_ceidg(nip),
            self.scrape_vat_registry(nip),
            return_exceptions=True,
        )
        raise_if_intervention(results)
        return results

    async def search_by_krs(self, krs: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.search_ekrs_json(krs),
            self.scrape_ekrs(krs),
            return_exceptions=True,
        )
        raise_if_intervention(results)
        return results

    async def search_by_company_name(self, name: str) -> list[ServiceResult]:
        # Import here to avoid circular dependency
        from src.services.polish_gov_service import PolishGovService
        polish = PolishGovService()
        gov_results = await polish.search_by_name(name)
        court_result = await self.search_courts(name)
        api_results = await asyncio.gather(
            self.search_sec_edgar(name),
            self.search_companies_house(name),
            return_exceptions=True,
        )
        all_results = [court_result] + gov_results + api_results
        return all_results
