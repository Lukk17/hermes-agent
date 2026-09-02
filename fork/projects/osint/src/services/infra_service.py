from src.services.base_service import BaseService
from src.models import ServiceResult
from src.ascend_client import HumanInterventionNeeded, ascend_client
import asyncio


class InfraService(BaseService):

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

    async def check_urlscan(self, domain: str) -> ServiceResult:
        try:
            api_key = self.get_env("URLSCAN_API_KEY")
            if not api_key:
                return ServiceResult(source="urlscan", success=False, error="URLSCAN_API_KEY not set")
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                resp = requests.post(
                    "https://urlscan.io/api/v1/scan/",
                    json={"url": f"https://{domain}", "visibility": "public"},
                    headers={"API-Key": api_key, "Content-Type": "application/json"},
                    timeout=30,
                )
                return resp.json()
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="urlscan", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="urlscan", success=False, error=str(e))

    async def check_otx(self, domain: str) -> ServiceResult:
        try:
            api_key = self.get_env("OTX_API_KEY")
            if not api_key:
                return ServiceResult(source="otx", success=False, error="OTX_API_KEY not set")
            url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/general"
            headers = {"X-OTX-API-KEY": api_key}
            data = await self._get(url, headers=headers)
            return ServiceResult(source="otx", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="otx", success=False, error=str(e))

    async def check_greynoise(self, ip: str) -> ServiceResult:
        try:
            api_key = self.get_env("GREYNOISE_API_KEY")
            if not api_key:
                return ServiceResult(source="greynoise", success=False, error="GREYNOISE_API_KEY not set")
            url = f"https://api.greynoise.io/v3/community/{ip}"
            headers = {"key": api_key}
            data = await self._get(url, headers=headers)
            return ServiceResult(source="greynoise", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="greynoise", success=False, error=str(e))

    async def check_abuseipdb(self, ip: str) -> ServiceResult:
        try:
            api_key = self.get_env("ABUSEIPDB_API_KEY")
            if not api_key:
                return ServiceResult(source="abuseipdb", success=False, error="ABUSEIPDB_API_KEY not set")
            url = f"https://api.abuseipdb.com/api/v2/check"
            params = {"ipAddress": ip, "maxAgeInDays": 90}
            headers = {"Key": api_key, "Accept": "application/json"}
            data = await self._get(url, params=params, headers=headers)
            return ServiceResult(source="abuseipdb", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="abuseipdb", success=False, error=str(e))

    async def check_censys(self, domain: str) -> ServiceResult:
        try:
            api_key = self.get_env("CENSYS_API_KEY")
            if not api_key:
                return ServiceResult(source="censys", success=False, error="CENSYS_API_KEY not set")
            import base64
            creds = f"{api_key}:"
            token = base64.b64encode(creds.encode()).decode()
            headers = {"Authorization": f"Basic {token}"}
            url = f"https://search.censys.io/api/v1/search/shodan"
            params = {"q": domain}
            data = await self._get(url, params=params, headers=headers)
            return ServiceResult(source="censys", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="censys", success=False, error=str(e))

    async def check_binaryedge(self, domain: str) -> ServiceResult:
        try:
            api_key = self.get_env("BINARY_EDGE_API_KEY")
            if not api_key:
                return ServiceResult(source="binaryedge", success=False, error="BINARY_EDGE_API_KEY not set")
            url = f"https://api.binaryedge.io/v2/query/domains/{domain}"
            headers = {"X-Key": api_key}
            data = await self._get(url, headers=headers)
            return ServiceResult(source="binaryedge", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="binaryedge", success=False, error=str(e))

    async def check_ipqs(self, domain_or_ip: str) -> ServiceResult:
        try:
            api_key = self.get_env("IPQS_API_KEY")
            if not api_key:
                return ServiceResult(source="ipqs", success=False, error="IPQS_API_KEY not set")
            url = f"https://ipqualityscore.com/api/json/url/{api_key}/{domain_or_ip}"
            params = {"strictness": 1, "allow_malicious": True}
            data = await self._get(url, params=params)
            return ServiceResult(source="ipqs", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="ipqs", success=False, error=str(e))

    async def check_securitytrails(self, domain: str) -> ServiceResult:
        try:
            api_key = self.get_env("SECURITYTRAILS_API_KEY")
            if not api_key:
                return ServiceResult(source="securitytrails", success=False, error="SECURITYTRAILS_API_KEY not set")
            url = f"https://api.securitytrails.com/v1/domain/{domain}/subdomains"
            headers = {"apikey": api_key}
            data = await self._get(url, headers=headers)
            return ServiceResult(source="securitytrails", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="securitytrails", success=False, error=str(e))

    async def check_whoisxml(self, domain: str) -> ServiceResult:
        try:
            api_key = self.get_env("WHOISXML_API_KEY")
            if not api_key:
                return ServiceResult(source="whoisxml", success=False, error="WHOISXML_API_KEY not set")
            url = f"https://www.whoisxmlapi.com/whoisserver/WhoisService?apiKey={api_key}&domainName={domain}&outputFormat=json"
            data = await self._get(url)
            return ServiceResult(source="whoisxml", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="whoisxml", success=False, error=str(e))

    async def check_shodan(self, query: str) -> ServiceResult:
        try:
            api_key = self.get_env("SHODAN_API_KEY")
            if not api_key:
                return ServiceResult(source="shodan", success=False, error="SHODAN_API_KEY not set")
            url = f"https://api.shodan.io/shodan/host/search?key={api_key}&query={query}"
            data = await self._get(url)
            return ServiceResult(source="shodan", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="shodan", success=False, error=str(e))

    async def check_crtsh(self, domain: str) -> ServiceResult:
        try:
            # Try CertSpotter first (free, no key)
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
            # Fall back to crt.sh
            try:
                url = f"https://crt.sh/?q=%.{domain}&output=json"
                data = await self._get(url)
                if isinstance(data, list):
                    certs = []
                    for entry in data[:50]:
                        name = entry.get("name_value", "")
                        if domain in name:
                            certs.append({
                                "name": name,
                                "issuer": entry.get("issuer_name", ""),
                                "date": entry.get("not_before", "")[:10],
                            })
                    return ServiceResult(source="crtsh", success=True, data={"certificates": certs})
                return ServiceResult(source="crtsh", success=True, data={"certificates": []})
            except Exception:
                return ServiceResult(source="certspotter", success=False, error=f"Both CT services failed: {e}")

    async def scrape_dnsdumpster(self, domain: str) -> ServiceResult:
        try:
            result = await ascend_client.scrape(f"https://dnsdumpster.com/", include_links=True, heavy_mode=True)
            content = result.get("content", "")
            return ServiceResult(source="dnsdumpster", success=True, data={"raw_content": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except Exception as e:
            return ServiceResult(source="dnsdumpster", success=False, error=str(e))

    async def whois_lookup(self, domain: str) -> ServiceResult:
        try:
            import whois
            loop = asyncio.get_running_loop()
            def run_sync():
                return whois.whois(domain)
            data = await loop.run_in_executor(None, run_sync)
            if data:
                return ServiceResult(source="whois", success=True, data=dict(data))
            return ServiceResult(source="whois", success=False, error="No WHOIS data")
        except Exception as e:
            return ServiceResult(source="whois", success=False, error=str(e))

    async def dns_lookup(self, domain: str, record_type: str = "A") -> ServiceResult:
        try:
            import dns.resolver
            loop = asyncio.get_running_loop()
            def run_sync():
                resolver = dns.resolver.Resolver()
                resolver.lifetime = 5.0
                resolver.timeout = 3.0
                answers = resolver.resolve(domain, record_type)
                return [str(rdata) for rdata in answers]
            records = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="dns", success=True, data={record_type: records})
        except Exception as e:
            return ServiceResult(source="dns", success=False, error=str(e))

    async def search_by_domain(self, domain: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.check_crtsh(domain),
            self.check_virustotal(domain),
            self.check_otx(domain),
            self.whois_lookup(domain),
            self.dns_lookup(domain),
            return_exceptions=True,
        )
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="infra", success=False, error=str(r)))
            else:
                final.append(r)
        return final
    async def ip_api_lookup(self, ip: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                r = requests.get(f'http://ip-api.com/json/{ip}', timeout=8)
                return r.json()
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source='ip-api', success=True, data=data)
        except Exception as e:
            return ServiceResult(source='ip-api', success=False, error=str(e))
