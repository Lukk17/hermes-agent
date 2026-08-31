"""
Section: Spot ETF Flows.
"""

from reports.sections._base import SectionRenderer


class SectionEtf(SectionRenderer):

    def render(self) -> str:
        etf = self.data.get("etf", {})
        if not etf:
            return ""

        btc = etf.get("btc", {})
        eth = etf.get("eth", {})

        if not btc and not eth:
            return ""

        lines = ["## 📈 Spot ETF Flows"]

        if btc:
            btc_last = btc.get("latest_total", 0)
            btc_date = btc.get("latest_date", "")
            btc_7d = btc.get("recent_7d_total", 0)
            btc_dir = btc.get("direction", "neutral")
            arrow = "⬆️" if btc_dir == "inflow" else "⬇️" if btc_dir == "outflow" else "➡️"
            lines.append(f"**BTC:** {arrow} ${btc_last:.1f}M ({btc_date}) | 7d: ${btc_7d:.1f}M")

        if eth:
            eth_last = eth.get("latest_total", 0)
            eth_date = eth.get("latest_date", "")
            eth_7d = eth.get("recent_7d_total", 0)
            eth_dir = eth.get("direction", "neutral")
            arrow = "⬆️" if eth_dir == "inflow" else "⬇️" if eth_dir == "outflow" else "➡️"
            lines.append(f"**ETH:** {arrow} ${eth_last:.1f}M ({eth_date}) | 7d: ${eth_7d:.1f}M")

        return "\n".join(lines)


def render(data: dict) -> str:
    return SectionEtf(data).render()
