import asyncio
import subprocess
import os
from src.models import ServiceResult


BIN_DIR = "/home/node/.openclaw/workspace/osint/bin"
VENV_PY = "/home/node/.openclaw/workspace/osint/.venv/bin/python3"


class GoToolsService:

    def _bin_path(self, name: str) -> str:
        path = os.path.join(BIN_DIR, name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Binary not found: {path}")
        return path

    async def amass_passive(self, domain: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run():
                result = subprocess.run(
                    [self._bin_path("amass"), "enum", "-passive", "-silent",
                     "-d", domain, "-o", "/tmp/amass_out.txt"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                try:
                    with open("/tmp/amass_out.txt") as f:
                        subdomains = [l.strip() for l in f if l.strip()]
                except FileNotFoundError:
                    subdomains = [l.strip() for l in result.stdout.split("\n") if l.strip()]
                return subdomains
            subdomains = await loop.run_in_executor(None, run)
            return ServiceResult(source="amass", success=True, data={"subdomains": subdomains})
        except asyncio.TimeoutError:
            return ServiceResult(source="amass", success=False, error="Timeout after 15s")
        except Exception as e:
            return ServiceResult(source="amass", success=False, error=str(e))

    async def subfinder(self, domain: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run():
                result = subprocess.run(
                    [self._bin_path("subfinder"), "-d", domain, "-silent",
                     "-sources", "publicwww", "-o", "/tmp/sf_out.txt"],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                try:
                    with open("/tmp/sf_out.txt") as f:
                        subdomains = [l.strip() for l in f if l.strip()]
                except FileNotFoundError:
                    subdomains = [l.strip() for l in result.stdout.split("\n") if l.strip()]
                return subdomains
            subdomains = await loop.run_in_executor(None, run)
            return ServiceResult(source="subfinder", success=True, data={"subdomains": subdomains})
        except asyncio.TimeoutError:
            return ServiceResult(source="subfinder", success=False, error="Timeout after 20s")
        except Exception as e:
            return ServiceResult(source="subfinder", success=False, error=str(e))

    async def dnsrecon_enum(self, domain: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run():
                import json
                result = subprocess.run(
                    [VENV_PY, "-m", "dnsrecon",
                     "-d", domain, "-j", "/tmp/dnsrecon_out.json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                try:
                    with open("/tmp/dnsrecon_out.json") as f:
                        raw = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    raw = result.stdout[:2000]
                if isinstance(raw, list):
                    records = {}
                    for entry in raw:
                        rec_type = entry.get("type", "unknown")
                        if rec_type not in records:
                            records[rec_type] = []
                        if rec_type == "A":
                            records[rec_type].append({"host": entry.get("name"), "ip": entry.get("address")})
                        elif rec_type == "NS":
                            records[rec_type].append({"name": entry.get("name"), "target": entry.get("target")})
                        elif rec_type == "MX":
                            records[rec_type].append({"name": entry.get("name"), "target": entry.get("exchange")})
                        elif rec_type == "TXT":
                            records[rec_type].append({"name": entry.get("name"), "txt": entry.get("strings")})
                        else:
                            records[rec_type].append(entry)
                    return records
                elif isinstance(raw, dict):
                    return raw
                else:
                    return {"raw": str(raw)[:2000]}
            data = await loop.run_in_executor(None, run)
            return ServiceResult(source="dnsrecon", success=True, data=data)
        except asyncio.TimeoutError:
            return ServiceResult(source="dnsrecon", success=False, error="Timeout after 30s")
        except Exception as e:
            return ServiceResult(source="dnsrecon", success=False, error=str(e))

    async def httpx_probe(self, hosts: list[str]) -> ServiceResult:
        if not hosts:
            return ServiceResult(source="httpx", success=True, data={"probed": []})
        try:
            loop = asyncio.get_running_loop()
            def run():
                with open("/tmp/httpx_hosts.txt", "w") as f:
                    for h in hosts:
                        f.write(h + "\n")
                result = subprocess.run(
                    [self._bin_path("httpx"), "-list", "/tmp/httpx_hosts.txt",
                     "-silent", "-status-code"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
                return lines
            data = await loop.run_in_executor(None, run)
            return ServiceResult(source="httpx", success=True, data={"probed": data})
        except asyncio.TimeoutError:
            return ServiceResult(source="httpx", success=False, error="Timeout after 30s")
        except Exception as e:
            return ServiceResult(source="httpx", success=False, error=str(e))

    async def naabu_scan(self, host: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run():
                result = subprocess.run(
                    [self._bin_path("naabu"), "-host", host, "-silent", "-rate", "100"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
                return lines
            ports = await loop.run_in_executor(None, run)
            return ServiceResult(source="naabu", success=True, data={"open_ports": ports})
        except asyncio.TimeoutError:
            return ServiceResult(source="naabu", success=False, error="Timeout after 30s")
        except Exception as e:
            return ServiceResult(source="naabu", success=False, error=str(e))

    async def mosint_lookup(self, email: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run():
                config_content = """
smtp:
  host: localhost
  port: 1025
hunter_api_key: ""
emailfetcher_api_key: ""
freekey: ""
docker: false
"""
                with open("/tmp/.mosint.yaml", "w") as f:
                    f.write(config_content)
                result = subprocess.run(
                    [self._bin_path("mosint"), email, "-s", "-o", "/tmp/mosint_out.json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={**os.environ, "HOME": "/tmp"},
                )
                return {"stdout": result.stdout[:2000], "stderr": result.stderr[:500], "rc": result.returncode}
            data = await loop.run_in_executor(None, run)
            return ServiceResult(source="mosint", success=True, data=data)
        except asyncio.TimeoutError:
            return ServiceResult(source="mosint", success=False, error="Timeout after 30s")
        except Exception as e:
            return ServiceResult(source="mosint", success=False, error=str(e))
