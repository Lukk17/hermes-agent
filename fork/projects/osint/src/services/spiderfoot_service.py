from src.models import ServiceResult
import asyncio
import concurrent.futures
import subprocess
import json
import os
import time


class SpiderFootService:

    _sf_python = "/home/node/.openclaw/workspace/osint/.venv/bin/python3"
    _sf_cli = "/tmp/spiderfoot/sf.py"
    _env = {**os.environ, "PYTHONPATH": "/tmp/spiderfoot"}
    _executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="sf")

    async def spiderfoot_name_lookup(self, name: str) -> ServiceResult:
        return await self._sf_scan(name, "INTERNET_NAME",
            "sfp_names,sfp_socialprofiles,sfp_twitter,sfp_github")

    async def spiderfoot_email_lookup(self, email: str) -> ServiceResult:
        return await self._sf_scan(email, "EMAILADDR",
            "sfp_hunter,sfp_twitter,sfp_github,sfp_clearbit,sfp_haveibeenpwned,sfp_breachcheck")

    async def spiderfoot_domain_lookup(self, domain: str) -> ServiceResult:
        return await self._sf_scan(domain, "DOMAIN_NAME",
            "sfp_crt,sfp_whois,sfp_dnsbrute,sfp_hunter,sfp_github,sfp_socialprofiles")

    def _run_sync(self, target: str, target_type: str, modules: str) -> list[dict]:
        args = [
            self._sf_python, self._sf_cli,
            "-s", target,
            "-t", target_type,
            "-m", modules,
            "-o", "json",
        ]
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=self._env,
        )
        for _ in range(120):
            time.sleep(0.5)
            if proc.poll() is not None:
                break
        if proc.returncode is None:
            proc.kill()
            proc.wait()
            return []
        buf = b""
        if proc.stdout:
            while True:
                chunk = proc.stdout.read1(4096) if hasattr(proc.stdout, "read1") else proc.stdout.read(4096)
                if not chunk:
                    break
                buf += chunk
        if not buf:
            return []
        skip_types = {
            "ROOT", "BASIC_GEOINFO", "IP_ADDRESS", "DOMAIN_NAME",
            "EMAILADDR", "EMAILDOMAIN", "PROXY", "VPN", "RAW_DNS_RR",
            "LINKED_URL_INTERNAL", "SOCIAL_MEDIA_PROFILE", "USERNAME",
            "HASH", "INTERNET_NAME", "INTERNET_NAME_WILDCARD",
            "PHONE_NUMBER", "PEOPLE", "RAW_RIR_DATA", "HUMAN_NAME",
        }
        results = []
        for line in buf.decode("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, dict) and item.get("type") not in skip_types:
                            results.append({
                                "type": item.get("type", ""),
                                "data": item.get("data", ""),
                                "source": item.get("module", ""),
                            })
                elif isinstance(obj, dict) and obj.get("type") not in skip_types:
                    results.append({
                        "type": obj.get("type", ""),
                        "data": obj.get("data", ""),
                        "source": obj.get("module", ""),
                    })
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
        return results

    async def _sf_scan(self, target: str, target_type: str, modules: str = "") -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            results = await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._run_sync, target, target_type, modules),
                timeout=90.0,
            )
            return ServiceResult(source="spiderfoot", success=True, data={"results": results})
        except asyncio.TimeoutError:
            return ServiceResult(source="spiderfoot", success=False, error="Timeout after 90s")
        except Exception as e:
            return ServiceResult(source="spiderfoot", success=False, error=str(e))
