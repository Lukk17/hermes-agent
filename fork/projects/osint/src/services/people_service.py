from src.models import ServiceResult
import asyncio
import subprocess
import threading
import json
import os
import re
import shlex
import time as time_module

_VENV_PY = "/home/node/.openclaw/workspace/osint/.venv/bin/python3"


def normalize_polish(text: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def safe_filename(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '_', text)


class PeopleService:

    async def search_sherlock(self, name: str, timeout: int = 8) -> ServiceResult:
        try:
            out_file = f"/tmp/sherlock_out_{os.getpid()}_{safe_filename(name)}.txt"
            loop = asyncio.get_running_loop()

            def run_sync() -> str:
                cmd = f"{_VENV_PY} -m sherlock_project {shlex.quote(name)} --print-found --no-color --timeout {timeout} > {out_file} 2>&1"
                proc = subprocess.Popen(
                    cmd,
                    shell=True,
                )
                for _ in range(timeout * 4):
                    if proc.poll() is not None:
                        break
                    time_module.sleep(0.25)
                if proc.returncode is None:
                    proc.kill()
                    proc.wait()
                try:
                    with open(out_file) as f:
                        return f.read()
                except FileNotFoundError:
                    return ""

            output = await loop.run_in_executor(None, run_sync)
            try:
                os.unlink(out_file)
            except Exception:
                pass
            profiles = []
            for match in re.findall(r"\[\+\+?\]\s+([^:]+):\s*(https?://\S+)", output):
                site, url = match
                profiles.append({"site": site.strip(), "url": url.strip()})
            if profiles:
                return ServiceResult(source="sherlock", success=True, data={"profiles": profiles, "query": name})
            else:
                return ServiceResult(source="sherlock", success=False, error="No accounts found")
        except Exception as e:
            return ServiceResult(source="sherlock", success=False, error=str(e))

    async def search_maigret(self, name: str, timeout: int = 10) -> ServiceResult:
        try:
            safe_name = safe_filename(name)
            out_folder = "/home/node/.openclaw/workspace/osint/data"
            out_file = f"{out_folder}/maigret_{safe_name}.json"
            reports_dir = "/home/node/.openclaw/workspace/osint/reports"
            loop = asyncio.get_running_loop()

            def run_sync():
                cmd = [
                    _VENV_PY, "-m", "maigret", name,
                    "-J", "simple",
                    "--no-progressbar",
                    "--top-sites", "10",
                    "-fo", out_folder,
                ]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                for _ in range(timeout * 3):
                    if proc.poll() is not None:
                        break
                    time_module.sleep(0.4)
                if proc.returncode is None:
                    proc.kill()
                    proc.wait()

            await loop.run_in_executor(None, run_sync)
            candidates = [
                out_file,
                f"{reports_dir}/report_{safe_name}_simple.json",
                f"{out_folder}/report_{safe_name}_simple.json",
            ]
            data = None
            for path in candidates:
                try:
                    with open(path) as f:
                        data = json.load(f)
                    break
                except (FileNotFoundError, json.JSONDecodeError):
                    pass
            if data:
                try:
                    os.unlink(out_file)
                except Exception:
                    pass
                return ServiceResult(source="maigret", success=True, data={"profiles": data, "query": name})
            else:
                return ServiceResult(source="maigret", success=False, error="No results found")
        except Exception as e:
            return ServiceResult(source="maigret", success=False, error=str(e))

    async def search_by_name(self, name: str) -> list[ServiceResult]:
        ascii_name = normalize_polish(name)
        all_tasks = [
            asyncio.create_task(self.search_sherlock(name, timeout=8)),
            asyncio.create_task(self.search_maigret(name, timeout=10)),
        ]
        if ascii_name != name:
            all_tasks.extend([
                asyncio.create_task(self.search_sherlock(ascii_name, timeout=8)),
                asyncio.create_task(self.search_maigret(ascii_name, timeout=10)),
            ])
        done, pending = await asyncio.wait(all_tasks, timeout=20)
        results = []
        for t in done:
            results.append(t.result())
        for t in pending:
            t.cancel()
        return results