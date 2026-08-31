"""
Section: Market Indicators table.
"""

from reports.sections._base import SectionRenderer


class SectionIndicators(SectionRenderer):

    def render(self) -> str:
        cycle = self.data.get("cycle", {}) or {}
        indicators = cycle.get("indicators", {}) or {}
        rows = []

        # Fear & Greed - from data.alternative_me.value
        fg_data = self.data.get("fear_greed", {})
        fg_nested = fg_data.get("data", {}).get("alternative_me", {})
        fg_val = fg_nested.get("value") or fg_data.get("value")
        if fg_val is not None:
            fg_class = ("Extreme Fear" if fg_val <= 25 else "Fear" if fg_val <= 45 else
                        "Neutral" if fg_val <= 55 else "Greed" if fg_val <= 75 else "Extreme Greed")
            rows.append(["Fear & Greed", f"{fg_val:.0f}", fg_class])

        # Cycle Score
        cs = cycle.get("cycle_score", {})
        if cs:
            score = cs.get("score")
            phase = (cs.get("phase") or "").replace("_", " ")
            if score is not None:
                rows.append(["Cycle Score", f"{score:.0f}/100", phase[:25]])

        # RSI
        rsi = indicators.get("rsi", {})
        if rsi:
            rsi_val = rsi.get("value")
            if rsi_val is not None:
                rows.append(["BTC RSI(14)", f"{rsi_val:.0f}",
                             "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"])

        # MA Cross (MA50 vs MA200)
        ma_cross = indicators.get("ma_cross", {})
        if ma_cross:
            ma_state = ma_cross.get("state") or ma_cross.get("signal") or ""
            if ma_state:
                rows.append(["MA Cross", ma_state[:20], ""])

        # Price vs MA200
        price_vs_ma = indicators.get("price_vs_ma200", {})
        if price_vs_ma:
            pct = price_vs_ma.get("pct_deviation") or price_vs_ma.get("value") or 0
            if pct:
                rows.append(["Price vs MA200", f"{pct:+.1f}%", ""])

        # Pi Cycle
        pi = indicators.get("pi_cycle", {})
        if pi:
            pi_signal = pi.get("signal") or pi.get("state") or ""
            if pi_signal:
                rows.append(["Pi Cycle", pi_signal[:20], ""])

        # Hashrate
        hashrate = indicators.get("hashrate", {})
        if hashrate:
            hr_val = hashrate.get("value") or hashrate.get("hashrate") or 0
            if hr_val:
                rows.append(["Hashrate", f"{hr_val:.0f}%", ""])

        if not rows:
            return ""

        table = self.box_table(
            headers=["Indicator", "Value", "Signal"],
            rows=rows,
            aligns=["l", "r", "l"],
        )
        return f"```\n{table}\n```"


def render(data: dict) -> str:
    return SectionIndicators(data).render()
