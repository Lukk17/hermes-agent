from src.models import ServiceResult
import asyncio


class DarkWebService:

    async def check_tor(self) -> ServiceResult:
        try:
            import stem.control
            c = stem.control.Controller.from_port(port=9051)
            c.authenticate()
            version = str(c.get_version())
            c.close()
            return ServiceResult(source="tor", success=True, data={"status": "running", "version": version})
        except Exception as e:
            return ServiceResult(source="tor", success=False, error=f"Tor/stem not available: {e}")

    async def search_onionsearch(self, query: str) -> ServiceResult:
        try:
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                r = requests.get(
                    "https://onionsearch.com/search/",
                    params={"q": query},
                    headers={"User-Agent": "OSINT-Tool"},
                    timeout=15,
                )
                return {"content": r.text[:3000], "status": r.status_code}
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="onionsearch", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="onionsearch", success=False, error=str(e))

    async def search_ahmia(self, query: str) -> ServiceResult:
        try:
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                r = requests.get(
                    "https://ahmia.fi/search/",
                    params={"q": query},
                    headers={"User-Agent": "OSINT-Tool"},
                    timeout=15,
                )
                return r.text[:3000]
            content = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="ahmia", success=True, data={"raw_content": content})
        except Exception as e:
            return ServiceResult(source="ahmia", success=False, error=str(e))

    async def fetch_onion(self, onion_url: str) -> ServiceResult:
        try:
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                session = requests.Session()
                session.proxies = {"http": "socks5h://localhost:9050", "https": "socks5h://localhost:9050"}
                r = session.get(onion_url, timeout=20)
                return r.text[:5000]
            content = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="onion_fetch", success=True, data={"raw_content": content})
        except Exception as e:
            return ServiceResult(source="onion_fetch", success=False, error=str(e))

    async def darksearch_lookup(self, query: str) -> ServiceResult:
        try:
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                session = requests.Session()
                session.proxies = {"http": "socks5h://localhost:9050", "https": "socks5h://localhost:9050"}
                r = session.get(f"http://darksearchqelmoc.onion/search?q={query}", timeout=20)
                return r.text[:3000]
            content = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="darksearch", success=True, data={"raw_content": content})
        except Exception as e:
            return ServiceResult(source="darksearch", success=False, error=str(e))

    async def hiddenwiki_list(self) -> ServiceResult:
        try:
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                r = requests.get("https://thehiddenwiki.org", timeout=15, headers={"User-Agent": "OSINT-Tool"})
                return r.text[:5000]
            content = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="hiddenwiki", success=True, data={"raw_content": content})
        except Exception as e:
            return ServiceResult(source="hiddenwiki", success=False, error=str(e))

    async def tor_search(self, query: str) -> ServiceResult:
        try:
            import stem.control
            import requests
            loop = asyncio.get_running_loop()
            def run():
                c = stem.control.Controller.from_port(port=9051)
                c.authenticate()
                session = requests.Session()
                session.proxies = {
                    'http': 'socks5://127.0.0.1:9050',
                    'https': 'socks5://127.0.0.1:9050',
                }
                # Ahmia over Tor
                r = session.get(f'https://ahmia.fi/search/', params={'q': query}, timeout=20)
                c.close()
                return r.text[:3000]
            content = await loop.run_in_executor(None, run)
            return ServiceResult(source='tor_ahmia', success=True, data={'raw_content': content})
        except Exception as e:
            return ServiceResult(source='tor_ahmia', success=False, error=str(e))

    async def search_by_query(self, query: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.search_ahmia(query),
            self.search_onionsearch(query),
            self.tor_search(query),
            self.check_tor(),
            return_exceptions=True,
        )
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="darkweb", success=False, error=str(r)))
            else:
                final.append(r)
        return final



