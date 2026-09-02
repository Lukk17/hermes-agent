import asyncio
import requests
import os
from collections.abc import Iterable

from src.ascend_client import HumanInterventionNeeded


def get_env(key: str) -> str | None:
    return os.environ.get(key)


def raise_if_intervention(results: Iterable[object]) -> None:
    """Re-raise the captcha wall that `asyncio.gather(return_exceptions=True)` turned into a result.

    Raises:
        HumanInterventionNeeded: when any gathered coroutine hit a captcha wall.
    """
    for result in results:
        if isinstance(result, HumanInterventionNeeded):
            raise result


class BaseService:
    def __init__(self):
        pass

    def get_env(self, key: str) -> str | None:
        return os.environ.get(key)

    async def _get(self, url: str, **kwargs) -> dict:
        loop = asyncio.get_running_loop()
        def blocking_get():
            kwargs.setdefault("timeout", 20)
            for attempt in range(4):
                try:
                    r = requests.get(url, **kwargs)
                    if r.status_code == 429 or r.status_code >= 500:
                        if attempt < 3:
                            delay = 2 ** attempt
                            import time
                            time.sleep(delay)
                        r.raise_for_status()
                    else:
                        r.raise_for_status()
                    return r.json()
                except requests.exceptions.HTTPError as e:
                    if attempt < 3 and e.response.status_code in (429, 500, 502, 503, 504):
                        delay = 2 ** attempt
                        import time
                        time.sleep(delay)
                        continue
                    raise
            raise Exception("Max retries exceeded")
        return await loop.run_in_executor(None, blocking_get)

    async def _post(self, url: str, **kwargs) -> dict:
        loop = asyncio.get_running_loop()
        def blocking_post():
            kwargs.setdefault("timeout", 20)
            for attempt in range(4):
                try:
                    r = requests.post(url, **kwargs)
                    if r.status_code == 429 or r.status_code >= 500:
                        if attempt < 3:
                            delay = 2 ** attempt
                            import time
                            time.sleep(delay)
                        r.raise_for_status()
                    else:
                        r.raise_for_status()
                    return r.json()
                except requests.exceptions.HTTPError as e:
                    if attempt < 3 and e.response.status_code in (429, 500, 502, 503, 504):
                        delay = 2 ** attempt
                        import time
                        time.sleep(delay)
                        continue
                    raise
            raise Exception("Max retries exceeded")
        return await loop.run_in_executor(None, blocking_post)