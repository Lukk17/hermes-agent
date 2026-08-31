"""
Section: Top Movers (gainers vs losers, 24h change).
"""

from reports.sections._base import SectionRenderer

STABLECOINS = {"tether", "usd-coin", "dai", "binance-usd", "trueusd",
               "first-digital-usd", "usdd", "pax-dollar", "frax", "tusd"}


class SectionMovers(SectionRenderer):

    def render(self) -> str:
        prices = self.data.get("prices", {}) or {}
        coin_list = prices.get("coins", [])

        if not coin_list:
            return ""

        non_stable = [c for c in coin_list if c.get("id") not in STABLECOINS]

        gainers = [
            f"{c.get('symbol', ''):<5} {(c.get('change_24h') or 0):+.1f}%"
            for c in non_stable
            if (c.get("change_24h") or 0) > 0
        ]
        losers = [
            f"{c.get('symbol', ''):<5} {(c.get('change_24h') or 0):+.1f}%"
            for c in non_stable
            if (c.get("change_24h") or 0) < 0
        ]
        losers = list(reversed(sorted(losers)))[:5]

        if not gainers and not losers:
            return ""

        table = self.dual_column_table("Gainers (24h)", "Losers (24h)", gainers[:5], losers)
        return f"```\n{table}\n```"


def render(data: dict) -> str:
    return SectionMovers(data).render()
