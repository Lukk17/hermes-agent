"""Ascend web scraper client.

A captcha wall is not recoverable inside this process: the scan must stop,
tell the agent what a human has to solve, and be resumed afterwards. So
`scrape` raises HumanInterventionNeeded and lets it travel up to main.py.
"""

import os

import aiohttp
import asyncio

DEFAULT_BASE_URL = "http://host.docker.internal:7021"
API_PATH = "/api/v2/web/read"


class HumanInterventionNeeded(Exception):
    """Raised when the scraper hits a captcha/login wall and needs a human."""

    def __init__(self, vnc_url: str, url: str, intervention_type: str = "captcha", message: str = ""):
        self.vnc_url = vnc_url
        self.url = url
        self.intervention_type = intervention_type
        self.message = message
        # Whatever the pipeline had collected when the wall was hit, filled in
        # by the caller that owns those results so main.py can persist them.
        self.partial_results: list = []
        super().__init__(f"Human intervention required ({intervention_type}): {vnc_url}")


def resolve_base_url(base_url: str = None) -> str:
    """Resolve the scraper base URL from the argument, the environment, then the default.

    ASCEND_SCRAPPER_URL is documented as a base URL but is deployed holding
    the full endpoint, so a trailing API path is stripped rather than doubled.
    """
    raw = (base_url or os.getenv("ASCEND_SCRAPPER_URL") or DEFAULT_BASE_URL).strip().rstrip("/")
    if raw.endswith(API_PATH):
        raw = raw[: -len(API_PATH)].rstrip("/")
    return raw or DEFAULT_BASE_URL


class AscendClient:
    def __init__(self, base_url: str = None):
        self.base_url = resolve_base_url(base_url)
        self.api_endpoint = f"{self.base_url}{API_PATH}"
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=90, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def scrape(
        self,
        url: str,
        include_links: bool = True,
        heavy_mode: bool = True,
        link_filter: str = None,
    ) -> dict:
        """Scrape a URL.

        Returns dict with keys:
        - status: "success" | "error"
        - content: page text (on success)
        - links: dict of anchor text -> URL (when include_links=True)
        - error: present on error status

        Raises:
            HumanInterventionNeeded: when the page is behind a captcha or login wall.
        """
        result = await self._scrape_raw(url, include_links, heavy_mode, link_filter)

        if result.get("status") == "human_intervention_required":
            raise HumanInterventionNeeded(
                vnc_url=result.get("vnc_url", ""),
                url=url,
                intervention_type=result.get("intervention_type", "captcha"),
                message=result.get("message", ""),
            )

        return result

    async def _scrape_raw(
        self,
        url: str,
        include_links: bool = True,
        heavy_mode: bool = True,
        link_filter: str = None,
    ) -> dict:
        """Raw scrape without captcha handling."""
        session = await self._get_session()
        payload = {
            "url": url,
            "include_links": include_links,
            "heavy_mode": heavy_mode,
        }
        if link_filter:
            payload["link_filter"] = link_filter

        try:
            async with session.post(self.api_endpoint, json=payload) as response:
                data = await response.json()
        except asyncio.TimeoutError:
            return {"status": "error", "error": "Scraper timeout"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

        return data

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


ascend_client = AscendClient()
