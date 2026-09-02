from src.services.base_service import BaseService
from src.models import ServiceResult
from src.ascend_client import HumanInterventionNeeded, ascend_client
import asyncio


class GitHubService(BaseService):

    async def get_user(self, username: str) -> ServiceResult:
        try:
            api_key = self.get_env("GITHUB_TOKEN")
            headers = {"Accept": "application/vnd.github.v3+json"}
            if api_key:
                headers["Authorization"] = f"token {api_key}"
            url = f"https://api.github.com/users/{username}"
            data = await self._get(url, headers=headers)
            if "login" in data:
                return ServiceResult(source="github_user", success=True, data=data)
            return ServiceResult(source="github_user", success=False, error=data.get("message", "Not found"))
        except Exception as e:
            return ServiceResult(source="github_user", success=False, error=str(e))

    async def search_users(self, query: str) -> ServiceResult:
        try:
            api_key = self.get_env("GITHUB_TOKEN")
            headers = {"Accept": "application/vnd.github.v3+json"}
            if api_key:
                headers["Authorization"] = f"token {api_key}"
            url = f"https://api.github.com/search/users?q={query}"
            data = await self._get(url, headers=headers)
            if "items" in data:
                return ServiceResult(source="github_user_search", success=True, data={
                    "users": data.get("items", []),
                    "total_count": data.get("total_count", 0),
                })
            return ServiceResult(source="github_user_search", success=False, error="No results")
        except Exception as e:
            return ServiceResult(source="github_user_search", success=False, error=str(e))

    async def get_org(self, org: str) -> ServiceResult:
        try:
            api_key = self.get_env("GITHUB_TOKEN")
            headers = {"Accept": "application/vnd.github.v3+json"}
            if api_key:
                headers["Authorization"] = f"token {api_key}"
            url = f"https://api.github.com/orgs/{org}"
            data = await self._get(url, headers=headers)
            if "login" in data:
                return ServiceResult(source="github_org", success=True, data=data)
            return ServiceResult(source="github_org", success=False, error=data.get("message", "Not found"))
        except Exception as e:
            return ServiceResult(source="github_org", success=False, error=str(e))

    async def get_repo(self, owner: str, repo: str) -> ServiceResult:
        try:
            api_key = self.get_env("GITHUB_TOKEN")
            headers = {"Accept": "application/vnd.github.v3+json"}
            if api_key:
                headers["Authorization"] = f"token {api_key}"
            url = f"https://api.github.com/repos/{owner}/{repo}"
            data = await self._get(url, headers=headers)
            if "full_name" in data:
                return ServiceResult(source="github_repo", success=True, data=data)
            return ServiceResult(source="github_repo", success=False, error=data.get("message", "Not found"))
        except Exception as e:
            return ServiceResult(source="github_repo", success=False, error=str(e))

    async def search_by_domain(self, domain: str) -> ServiceResult:
        try:
            result = await ascend_client.scrape(f"https://github.com/search?q={domain}&type=organizations", include_links=True, heavy_mode=True
            )
            content = result.get("content", "")
            return ServiceResult(source="github_org_search", success=True, data={"raw_content": content[:3000]})
        except HumanInterventionNeeded:
            raise
        except asyncio.TimeoutError:
            return ServiceResult(source="github_org_search", success=False, error="Scraper timeout (10s)")
        except Exception as e:
            return ServiceResult(source="github_org_search", success=False, error=str(e))

    async def get_commit_by_email(self, email: str) -> ServiceResult:
        try:
            api_key = self.get_env("GITHUB_TOKEN")
            headers = {"Accept": "application/vnd.github.cloudscout+json"}
            if api_key:
                headers["Authorization"] = f"token {api_key}"
            url = f"https://api.github.com/search/commits?q={email}+author-date%3E2020-01-01"
            data = await self._get(url, headers=headers)
            if "items" in data:
                commits = []
                for item in data["items"][:10]:
                    commits.append({
                        "sha": item.get("sha", "")[:7],
                        "message": item.get("commit", {}).get("message", "").split("\n")[0],
                        "author": item.get("commit", {}).get("author", {}).get("name", ""),
                        "date": item.get("commit", {}).get("author", {}).get("date", "")[:10],
                        "url": item.get("html_url", ""),
                    })
                return ServiceResult(source="github_commits", success=True, data={"commits": commits, "total": data.get("total_count", 0)})
            return ServiceResult(source="github_commits", success=False, error="No results")
        except Exception as e:
            return ServiceResult(source="github_commits", success=False, error=str(e))
