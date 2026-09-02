"""
Section: Stablecoin Supply changes.
"""

from reports.sections._base import SectionRenderer


class SectionStablecoins(SectionRenderer):

    def render(self) -> str:
        stablecoins = self.data.get("stablecoins", {})
        if not stablecoins:
            return ""

        coins = stablecoins.get("coins", [])
        if not coins:
            return ""

        lines = ["## 💵 Stablecoin Supply"]

        for entry in coins:
            symbol = entry.get("symbol", "")
            change = entry.get("7d_change_pct", 0) or 0
            arrow = "⬆️" if change > 0 else "⬇️" if change < 0 else "➡️"
            lines.append(f"{symbol} {arrow}{change:+.1f}%")

        total = stablecoins.get("total_mcap", 0)
        if total:
            total_change = stablecoins.get("total_7d_change", 0)
            direction = stablecoins.get("direction", "stable")
            dir_emoji = "📈" if direction == "expanding" else "📉" if direction == "contracting" else "➡️"
            lines.append(f"**Total:** ${total/1e9:.1f}B ({dir_emoji} ${total_change/1e6:+.0f}M/7d)")

        return "\n".join(lines)


def render(data: dict) -> str:
    return SectionStablecoins(data).render()
