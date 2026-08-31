import sys
import os
import asyncio
from src.services.base_service import BaseService
from src.models import ServiceResult
from src.ascend_client import ascend_client


class ReconService(BaseService):

    async def wappalyzer_scan(self, url: str) -> ServiceResult:
        try:
            from wappalyzer import analyze
            loop = asyncio.get_running_loop()
            def run_sync():
                return analyze(url, scan_type='basic', threads=3)
            techs = await asyncio.wait_for(loop.run_in_executor(None, run_sync), timeout=10)
            return ServiceResult(source="wappalyzer", success=True, data={"technologies": techs})
        except asyncio.TimeoutError:
            return ServiceResult(source="wappalyzer", success=False, error="Timeout after 10s")
        except Exception as e:
            return ServiceResult(source="wappalyzer", success=False, error=str(e))

    async def sublist3r_enum(self, domain: str) -> ServiceResult:
        try:
            import concurrent.futures
            loop = asyncio.get_running_loop()

            def run_sync():
                import subprocess
                import shlex
                venv_py = "/home/node/.openclaw/workspace/osint/.venv/bin/python3"
                cmd = f"{venv_py} -m sublist3r -d {domain} -o /tmp/sublist3r_{os.getpid()}.txt"
                proc = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                for _ in range(24):
                    import time
                    if proc.poll() is not None:
                        break
                    time.sleep(0.5)
                if proc.returncode is None:
                    proc.kill()
                    proc.wait()
                try:
                    with open(f"/tmp/sublist3r_{os.getpid()}.txt") as f:
                        return [line.strip() for line in f if line.strip()]
                except FileNotFoundError:
                    return []

            subdomains = await asyncio.wait_for(loop.run_in_executor(None, run_sync), timeout=15)
            return ServiceResult(source="sublist3r", success=True, data={"subdomains": subdomains})
        except asyncio.TimeoutError:
            return ServiceResult(source="sublist3r", success=False, error="Timeout after 15s")
        except Exception as e:
            return ServiceResult(source="sublist3r", success=False, error=str(e))
        except Exception as e:
            return ServiceResult(source="sublist3r", success=False, error=str(e))

    async def photon_crawl(self, url: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import photon.photon as p
                results = p.crawl(url, delay=0, timeout=10, level=2, threads=2, only_urls=False)
                return {
                    "internal": results.get("internal", [])[:50],
                    "external": results.get("external", [])[:100],
                    "files": results.get("files", [])[:50],
                    "intel": results.get("intel", [])[:50],
                    "endpoints": results.get("endpoints", [])[:50],
                }
            data = await asyncio.wait_for(loop.run_in_executor(None, run_sync), timeout=15)
            return ServiceResult(source="photon", success=True, data=data)
        except asyncio.TimeoutError:
            return ServiceResult(source="photon", success=False, error="Timeout after 15s")
        except Exception as e:
            return ServiceResult(source="photon", success=False, error=str(e))

    async def ghunt_lookup(self, email: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import ghunt
                parser = ghunt.emails.Email(email)
                creds = ghunt.config.Credentials()
                results = ghunt.emails.email_lookup(parser, creds)
                return results
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="ghunt", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="ghunt", success=False, error=str(e))

    async def theharvester_search(self, domain: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import subprocess
                import os
                env = os.environ.copy()
                env['PYTHONPATH'] = '/home/node/.openclaw/workspace/osint/theHarvester'
                result = subprocess.run(
                    [
                        '/home/node/.openclaw/workspace/osint/.venv/bin/python3',
                        '/home/node/.openclaw/workspace/osint/theHarvester/bin/theHarvester',
                        '-d', domain,
                        '-b', 'google,bing',
                        '-f', '/tmp/th_out.json',
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                )
                return result.stdout + result.stderr
            output = await loop.run_in_executor(None, run_sync)
            try:
                import json
                with open("/tmp/th_out.json") as f:
                    data = json.load(f)
                return ServiceResult(source="theharvester", success=True, data=data)
            except Exception:
                return ServiceResult(source="theharvester", success=True, data={"raw": output[:2000]})
        except Exception as e:
            return ServiceResult(source="theharvester", success=False, error=str(e))

    async def socid_extract(self, url: str) -> ServiceResult:
        try:
            import socid_extractor
            loop = asyncio.get_running_loop()
            def run_sync():
                return socid_extractor.extract(url)
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="socid", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="socid", success=False, error=str(e))

    async def search_by_url(self, url: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.wappalyzer_scan(url),
            self.socid_extract(url),
            return_exceptions=True,
        )
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="recon", success=False, error=str(r)))
            else:
                final.append(r)
        return final

    async def search_by_domain(self, domain: str) -> list[ServiceResult]:
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(self.sublist3r_enum(domain)),
                asyncio.create_task(self.theharvester_search(domain)),
                asyncio.create_task(self.wappalyzer_scan(f"https://{domain}")),
            ],
            timeout=15,
            return_when=asyncio.ALL_COMPLETED,
        )
        for task in pending:
            task.cancel()
        results = []
        for task in done:
            try:
                results.append(task.result())
            except Exception as e:
                results.append(ServiceResult(source="recon", success=False, error=str(e)))
        return results
