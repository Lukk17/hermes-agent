"""Ascend web scraper client with built-in captcha handling."""

import aiohttp
import asyncio


class HumanInterventionNeeded(Exception):
    """Raised when scraper hits captcha/login wall and needs human resolution."""

    def __init__(self, vnc_url: str, url: str, intervention_type: str = "captcha", message: str = ""):
        self.vnc_url = vnc_url
        self.url = url
        self.intervention_type = intervention_type
        self.message = message
        super().__init__(f"Human intervention required ({intervention_type}): {vnc_url}")


class AscendClient:
    def __init__(self, base_url: str = "http://host.docker.internal:7021"):
        self.base_url = base_url
        self.api_endpoint = f"{self.base_url}/api/v2/web/read"
        self._session = None
        self._captcha_handler = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=90, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _get_captcha_handler(self):
        if self._captcha_handler is None:
            from src.captcha_handler import get_captcha_handler
            self._captcha_handler = get_captcha_handler()
        return self._captcha_handler

    async def scrape(
        self,
        url: str,
        include_links: bool = True,
        heavy_mode: bool = True,
        link_filter: str = None,
    ) -> dict:
        """Scrape a URL with automatic captcha handling.

        Returns dict with keys:
        - status: "success" | "error" | "human_intervention_required"
        - content: page text (on success)
        - links: dict of anchor text -> URL (when include_links=True)
        - error: present on error status
        """
        handler = await self._get_captcha_handler()

        while True:
            result = await self._scrape_raw(url, include_links, heavy_mode, link_filter)

            if result.get("status") == "human_intervention_required":
                e = HumanInterventionNeeded(
                    vnc_url=result.get("vnc_url", ""),
                    url=url,
                    intervention_type=result.get("intervention_type", "captcha"),
                    message=result.get("message", ""),
                )
                await handler.handle_intervention(e, url)
                # Loop and retry after user resolves
                continue

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
