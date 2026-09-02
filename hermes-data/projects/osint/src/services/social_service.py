from src.models import ServiceResult
from src.ascend_client import HumanInterventionNeeded, ascend_client
from bs4 import BeautifulSoup
import re


class SocialService:

    async def scrape_facebook(self, profile_url: str) -> ServiceResult:
        try:
            result = await ascend_client.scrape(profile_url, include_links=True, heavy_mode=True)
            content = result.get("content", "")
            links = result.get("links", {})
            parsed = self._parse_facebook(content)
            parsed["links"] = links
            parsed["profile_url"] = profile_url
            return ServiceResult(source="facebook_scrape", success=True, data=parsed)
        except HumanInterventionNeeded:
            raise
        except Exception as e:
            return ServiceResult(source="facebook_scrape", success=False, error=str(e))

    def _parse_facebook(self, html: str) -> dict:
        data = {}
        if not html:
            return data
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("title")
        if title:
            data["name"] = title.get_text(strip=True).replace(" | Facebook", "").replace("Facebook — ", "")
        name_elem = soup.find(attrs={"data-ad-preview": "message"})
        if name_elem:
            data["name"] = name_elem.get_text(strip=True)
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            data["bio"] = meta_desc["content"].strip()
        followers_match = re.search(r'"entity_count_text">([^<]+)', html)
        if followers_match:
            data["followers"] = followers_match.group(1).strip()
        about_section = soup.find(string=re.compile(r"(About|O nas)", re.IGNORECASE))
        if about_section:
            parent = about_section.find_parent()
            if parent:
                data["about"] = parent.get_text(strip=True)[:300]
        categories = re.findall(r'"category">([^<]+)', html)
        if categories:
            data["category"] = categories[0]
        social_links = re.findall(r'href="(https?://(?:www\.)?(?:instagram\.com|twitter\.com|linkedin\.com|youtube\.com)/(?:[^"]+))"', html)
        if social_links:
            data["social_links"] = social_links[:10]
        return data

    async def scrape_instagram(self, profile_url: str) -> ServiceResult:
        try:
            result = await ascend_client.scrape(profile_url, include_links=True, heavy_mode=True)
            content = result.get("content", "")
            links = result.get("links", {})
            parsed = self._parse_instagram(content)
            parsed["links"] = links
            parsed["profile_url"] = profile_url
            return ServiceResult(source="instagram_scrape", success=True, data=parsed)
        except HumanInterventionNeeded:
            raise
        except Exception as e:
            return ServiceResult(source="instagram_scrape", success=False, error=str(e))

    def _parse_instagram(self, html: str) -> dict:
        data = {}
        if not html:
            return data
        soup = BeautifulSoup(html, "html.parser")
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            data["name"] = og_title["content"].strip().replace(" on Instagram", "")
        og_description = soup.find("meta", property="og:description")
        if og_description and og_description.get("content"):
            data["bio"] = og_description["content"].strip()
        followers_match = re.search(r'"follower_count":(\d+)', html)
        if followers_match:
            data["followers"] = f"{int(followers_match.group(1)):,}"
        following_match = re.search(r'"following_count":(\d+)', html)
        if following_match:
            data["following"] = f"{int(following_match.group(1)):,}"
        posts_match = re.search(r'"media_count":(\d+)', html)
        if posts_match:
            data["posts"] = f"{int(posts_match.group(1)):,}"
        return data

    async def scrape_tiktok(self, profile_url: str) -> ServiceResult:
        try:
            result = await ascend_client.scrape(profile_url, include_links=True, heavy_mode=True)
            content = result.get("content", "")
            links = result.get("links", {})
            parsed = self._parse_tiktok(content)
            parsed["links"] = links
            parsed["profile_url"] = profile_url
            return ServiceResult(source="tiktok_scrape", success=True, data=parsed)
        except HumanInterventionNeeded:
            raise
        except Exception as e:
            return ServiceResult(source="tiktok_scrape", success=False, error=str(e))

    def _parse_tiktok(self, html: str) -> dict:
        data = {}
        if not html:
            return data
        soup = BeautifulSoup(html, "html.parser")
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            data["name"] = og_title["content"].strip().replace(" | TikTok", "")
        og_description = soup.find("meta", property="og:description")
        if og_description and og_description.get("content"):
            data["bio"] = og_description["content"].strip()
        followers_match = re.search(r'"followerCount"\s*:\s*(\d+)', html)
        if followers_match:
            data["followers"] = f"{int(followers_match.group(1)):,}"
        likes_match = re.search(r'"likeCount"\s*:\s*(\d+)', html)
        if likes_match:
            data["likes"] = f"{int(likes_match.group(1)):,}"
        return data

    async def search_google_social(self, name: str, platform: str = "all") -> ServiceResult:
        return ServiceResult(
            source=f"google_social_{platform}",
            success=False,
            error="Search engine scraping blocked by captcha. Use Maigret/Sherlock for username discovery.",
        )

    async def search_twitter_advanced(self, name: str, location: str = None) -> ServiceResult:
        return ServiceResult(
            source="twitter_advanced",
            success=False,
            error="Twitter/X requires JavaScript. Use Maigret/Sherlock for Twitter discovery.",
        )

    async def search_by_name(self, name: str, location: str = None) -> list[ServiceResult]:
        return [await self.search_google_social(name), await self.search_twitter_advanced(name, location)]

    async def search_by_username(self, username: str) -> list[ServiceResult]:
        return [
            await self.scrape_facebook(f"https://www.facebook.com/{username}"),
            await self.scrape_instagram(f"https://www.instagram.com/{username}"),
            await self.scrape_tiktok(f"https://www.tiktok.com/@{username}"),
            await self.search_twitter_advanced(username),
        ]
