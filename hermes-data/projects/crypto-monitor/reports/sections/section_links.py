"""
Section: Quick Links.
"""

from reports.sections._base import SectionRenderer


class SectionLinks(SectionRenderer):

    def render(self) -> str:
        links = [
            "https://cryptobubbles.net",
            "https://www.coingecko.com",
            "https://coinmarketcap.com",
            "https://defillama.com",
        ]
        lines = ["## 🔗 Quick Links"]
        lines.extend(f"<{url}>" for url in links)

        return "\n".join(lines)


def render(data: dict) -> str:
    return SectionLinks(data).render()
