"""
Section: Market Breadth indicators.
"""

from reports.sections._base import SectionRenderer


class SectionBreadth(SectionRenderer):

    def render(self) -> str:
        breadth = self.data.get("market_breadth", {})
        if not breadth:
            return ""

        btc_dom = breadth.get("btc_dominance", 0) or 0
        eth_dom = breadth.get("eth_dominance", 0) or 0
        total_alt = 100 - btc_dom - eth_dom

        lines = [
            f"**BTC Dominance:** {btc_dom:.1f}%",
            f"**ETH Dominance:** {eth_dom:.1f}%",
            f"**Alt Dominance:** {total_alt:.1f}%",
        ]

        health = breadth.get("health", {})
        if health and isinstance(health, dict):
            score = health.get("score") or health.get("value")
            if score is not None:
                lines.append(f"**Market Health:** {score:.0f}/100")

        return " | ".join(lines)


def render(data: dict) -> str:
    return SectionBreadth(data).render()
