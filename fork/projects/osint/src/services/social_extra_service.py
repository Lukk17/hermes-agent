from src.services.base_service import BaseService, raise_if_intervention
from src.models import ServiceResult
from src.ascend_client import HumanInterventionNeeded, ascend_client
import asyncio
from urllib.parse import quote


def normalize_polish(text: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class SocialExtraService(BaseService):

    async def reddit_user(self, username: str) -> ServiceResult:
        try:
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                r = requests.get(
                    f"https://www.reddit.com/user/{username}/about.json",
                    headers={"User-Agent": "OSINT-Tool/1.0"},
                    timeout=10,
                )
                return r.json()
            data = await loop.run_in_executor(None, run_sync)
            if "data" in data:
                d = data["data"]
                return ServiceResult(source="reddit_user", success=True, data={
                    "name": d.get("name"),
                    "created_utc": d.get("created_utc"),
                    "karma": d.get("karma"),
                    "link_karma": d.get("link_karma"),
                    "comment_karma": d.get("comment_karma"),
                    "over_18": d.get("over_18"),
                    "subreddit": d.get("subreddit", {}).get("title", ""),
                    "icon_img": d.get("icon_img", ""),
                })
            return ServiceResult(source="reddit_user", success=False, error="No data")
        except Exception as e:
            return ServiceResult(source="reddit_user", success=False, error=str(e))

    async def reddit_user_posts(self, username: str, limit: int = 10) -> ServiceResult:
        try:
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                r = requests.get(
                    f"https://www.reddit.com/user/{username}.json?limit={limit}",
                    headers={"User-Agent": "OSINT-Tool/1.0"},
                    timeout=10,
                )
                return r.json()
            data = await loop.run_in_executor(None, run_sync)
            posts = []
            if isinstance(data, dict) and "data" in data:
                for child in data["data"].get("children", []):
                    post = child.get("data", {})
                    posts.append({
                        "title": post.get("title", ""),
                        "subreddit": post.get("subreddit", ""),
                        "created_utc": post.get("created_utc", ""),
                        "score": post.get("score", 0),
                        "url": post.get("url", ""),
                        "selftext": post.get("selftext", ""),
                    })
            return ServiceResult(source="reddit_posts", success=True, data={"posts": posts})
        except Exception as e:
            return ServiceResult(source="reddit_posts", success=False, error=str(e))

    async def reddit_search(self, query: str, subreddit: str = None) -> ServiceResult:
        try:
            import requests
            loop = asyncio.get_running_loop()
            def run_sync():
                if subreddit:
                    url = f"https://www.reddit.com/r/{subreddit}/search.json?q={query}&restrict_sr=1"
                else:
                    url = f"https://www.reddit.com/search.json?q={query}"
                r = requests.get(url, headers={"User-Agent": "OSINT-Tool/1.0"}, timeout=10)
                return r.json()
            data = await loop.run_in_executor(None, run_sync)
            results = []
            if isinstance(data, dict):
                for child in data.get("data", {}).get("children", []):
                    post = child.get("data", {})
                    results.append({
                        "title": post.get("title", ""),
                        "subreddit": post.get("subreddit", ""),
                        "author": post.get("author", ""),
                        "created_utc": post.get("created_utc", ""),
                        "url": post.get("url", ""),
                        "selftext": post.get("selftext", "")[:500],
                    })
            return ServiceResult(source="reddit_search", success=True, data={"results": results})
        except Exception as e:
            return ServiceResult(source="reddit_search", success=False, error=str(e))

    async def search_castrickclues(self, username: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                r = requests.get(
                    f"https://api.castrickclues.com/search?username={username}",
                    headers={"User-Agent": "OSINT-Tool/1.0"},
                    timeout=10,
                )
                if r.status_code == 200:
                    return r.json()
                return {"found": False, "status": r.status_code}
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="castrickclues", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="castrickclues", success=False, error=str(e))

    async def search_socialsearcher(self, query: str) -> ServiceResult:
        try:
            result = await ascend_client.scrape(
                    f"https://www.social-searcher.com/search-social/?q={quote(query)}&search=people",
                    include_links=True,
                    heavy_mode=True,
            )
            content = result.get("content", "")
            return ServiceResult(source="socialsearcher", success=True, data={"raw_content": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except asyncio.TimeoutError:
            return ServiceResult(source="socialsearcher", success=False, error="Timeout after 8s")
        except Exception as e:
            return ServiceResult(source="socialsearcher", success=False, error=str(e))

    async def search_tiktok(self, username: str) -> ServiceResult:
        try:
            result = await ascend_client.scrape(
                    f"https://www.tiktok.com/@{username}",
                    include_links=True,
                    heavy_mode=True,
            )
            content = result.get("content", "")
            return ServiceResult(source="tiktok", success=True, data={"raw_content": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except asyncio.TimeoutError:
            return ServiceResult(source="tiktok", success=False, error="Timeout after 8s")
        except Exception as e:
            return ServiceResult(source="tiktok", success=False, error=str(e))

    async def search_threads(self, username: str) -> ServiceResult:
        try:
            result = await ascend_client.scrape(
                    f"https://www.threads.net/@{username}",
                    include_links=True,
                    heavy_mode=True,
            )
            content = result.get("content", "")
            return ServiceResult(source="threads", success=True, data={"raw_content": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except asyncio.TimeoutError:
            return ServiceResult(source="threads", success=False, error="Timeout after 8s")
        except Exception as e:
            return ServiceResult(source="threads", success=False, error=str(e))

    async def search_wayback(self, url: str) -> ServiceResult:
        try:
            loop = asyncio.get_running_loop()
            def run_sync():
                import requests
                # Get latest snapshot
                api_url = f"http://archive.org/wayback/available?url={url}"
                r = requests.get(api_url, timeout=10)
                data = r.json()
                if data.get("archived_snapshots", {}).get("closest"):
                    snapshot = data["archived_snapshots"]["closest"]
                    return {
                        "available": True,
                        "url": snapshot.get("url", ""),
                        "timestamp": snapshot.get("timestamp", ""),
                        "original": url,
                    }
                return {"available": False, "original": url}
            data = await loop.run_in_executor(None, run_sync)
            return ServiceResult(source="wayback", success=True, data=data)
        except Exception as e:
            return ServiceResult(source="wayback", success=False, error=str(e))

    async def search_by_username(self, username: str) -> list[ServiceResult]:
        results = await asyncio.gather(
            self.reddit_user(username),
            self.search_castrickclues(username),
            self.search_tiktok(username),
            self.search_threads(username),
            return_exceptions=True,
        )
        raise_if_intervention(results)
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ServiceResult(source="social_extra", success=False, error=str(r)))
            else:
                final.append(r)
        return final
