"""
Section: Prices table (top 10 coins by market cap, no stablecoins).
"""

from reports.sections._base import SectionRenderer

STABLECOINS = {"tether", "usd-coin", "dai", "binance-usd", "trueusd",
               "first-digital-usd", "usdd", "pax-dollar", "frax", "tusd"}


class SectionPrices(SectionRenderer):

    def render(self) -> str:
        prices = self.data.get("prices", {}) or {}
        coin_list = prices.get("coins", [])

        if not coin_list:
            return ""

        non_stable = [c for c in coin_list if c.get("id") not in STABLECOINS]
        non_stable.sort(key=lambda x: x.get("market_cap", 0), reverse=True)
        top10 = non_stable[:10]

        rows = []
        for c in top10:
            change = c.get("change_24h") or 0
            rows.append([c.get("symbol", ""), self.fmt_price(c.get("price", 0)), f"{change:+.1f}%"])

        table = self.box_table(
            headers=["Coin", "Price", "24h"],
            rows=rows,
            aligns=["l", "r", "r"],
        )
        return f"```\n{table}\n```"


def render(data: dict) -> str:
    return SectionPrices(data).render()
