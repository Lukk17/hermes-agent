"""
Section: Trending News (top 10 articles).
"""

from datetime import datetime, timedelta
from reports.sections._base import SectionRenderer


class SectionNews(SectionRenderer):

    def render(self) -> str:
        news = self.data.get("news", {})
        if not news:
            return "## 📰 Trending News\n\n_No news data._"

        if news.get("status") == "error":
            error_msg = news.get("error", "Unknown error")
            return f"## 📰 News\n\n⚠️ **NEWS FETCH FAILED: {error_msg}**\n\n_Last successful fetch may be old._"

        articles = news.get("articles") or []
        if not articles:
            return "## 📰 Trending News\n\n_No articles._"

        # Check if data is stale (>24h old)
        news_timestamp = news.get("timestamp", "")
        if news_timestamp:
            try:
                ts = datetime.fromisoformat(news_timestamp.replace("Z", "+00:00"))
                age = datetime.now(ts.tzinfo) - ts
                if age > timedelta(hours=24):
                    return f"## 📰 News\n\n⚠️ **News data is {age.days} days old**\n\n_Last successful fetch: {news_timestamp[:10]}_"
            except Exception:
                pass

        lines = []
        for i, article in enumerate(articles[:10], 1):
            title = (article.get("title") or "")[:80]
            summary = (article.get("summary") or article.get("description") or "")[:100]
            url = article.get("url", "")
            lines.append(f"**{i}.** {title}")
            if summary:
                lines.append(f"   {summary}")
            if url:
                lines.append(f"   <{url}>")

        return "\n".join(lines)


def render(data: dict) -> str:
    return SectionNews(data).render()
