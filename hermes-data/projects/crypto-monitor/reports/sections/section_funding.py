"""
Section: Funding Rates.
"""

from reports.sections._base import SectionRenderer


class SectionFunding(SectionRenderer):

    def render(self) -> str:
        funding = self.data.get("funding", {})
        if not funding:
            return ""

        rates = funding.get("rates", [])
        if not rates:
            return ""

        lines = ["## 💰 Funding Rates"]

        avg = funding.get("avg_funding", 0)
        avg_pct = avg * 100
        sentiment = funding.get("sentiment", "neutral")
        emoji = "🟢" if sentiment == "bullish" else "🔴" if sentiment == "bearish" else "⚪"
        lines.append(f"**Avg 8h rate:** {emoji} {avg_pct:+.4f}% | {sentiment.title()}")

        # Top by absolute rate
        sorted_rates = sorted(rates, key=lambda x: abs(x.get("funding_rate_pct", 0)), reverse=True)[:6]
        for r in sorted_rates:
            pct = r.get("funding_rate_pct", 0) * 100
            direction = r.get("direction", "")
            arrow = "🟢" if direction == "longs_pay" else "🔴"
            lines.append(f"{arrow} {r.get('symbol', ''):5s} {pct:+.4f}%")

        return "\n".join(lines)


def render(data: dict) -> str:
    return SectionFunding(data).render()
