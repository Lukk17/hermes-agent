"""
Section: Market Summary (per-indicator breakdown).
"""

from reports.sections._base import SectionRenderer


class SectionSummary(SectionRenderer):

    def render(self) -> str:
        cycle = self.data.get("cycle", {}) or {}
        sentiment = self.data.get("sentiment", {}) or {}
        whale = self.data.get("whale_signals", {}) or {}
        whales = self.data.get("whales", {}) or {}

        fg_data = self.data.get("fear_greed", {})
        fg_val = fg_data.get("data", {}).get("alternative_me", {}).get("value")

        cs = cycle.get("cycle_score", {})
        cycle_score = cs.get("score") if cs else None
        cycle_phase = (cs.get("phase") or "").replace("_", " ") if cs else None

        ms = sentiment.get("market_sentiment", {})
        sent_val = ms.get("index") if ms else None

        whale_dir = None
        bc_summary = whales.get("balance_changes", {}).get("summary", {}) if whales else {}
        bullish = bc_summary.get("accumulators", 0)
        bearish = bc_summary.get("distributors", 0)
        if bullish or bearish:
            whale_dir = "BULLISH" if bullish > bearish else "BEARISH" if bearish > bullish else "MIXED"

        summary_lines = ["## 📋 Market Summary"]

        # Fear & Greed
        if fg_val is not None:
            if fg_val <= 10:
                summary_lines.append(f"**Fear & Greed: {fg_val:.0f} - Extreme Fear**")
            elif fg_val <= 25:
                summary_lines.append(f"**Fear & Greed: {fg_val:.0f} - Extreme Fear**")
            elif fg_val <= 45:
                summary_lines.append(f"**Fear & Greed: {fg_val:.0f} - Fear**")
            elif fg_val <= 55:
                summary_lines.append(f"**Fear & Greed: {fg_val:.0f} - Neutral**")
            elif fg_val <= 75:
                summary_lines.append(f"**Fear & Greed: {fg_val:.0f} - Greed**")
            else:
                summary_lines.append(f"**Fear & Greed: {fg_val:.0f} - Extreme Greed**")

        # Cycle Score
        if cycle_score is not None:
            phase_str = f" - {cycle_phase}" if cycle_phase else ""
            summary_lines.append(f"**Cycle Score: {cycle_score:.0f}/100{phase_str}**")

        # Sentiment
        if sent_val is not None:
            summary_lines.append(f"**Sentiment: {sent_val:.0f}/100**")

        # Whale direction
        if whale_dir:
            summary_lines.append(f"**Whale Signal: {whale_dir}** ({bullish} buying / {bearish} selling)")

        return "\n".join(summary_lines) if len(summary_lines) > 1 else ""


def render(data: dict) -> str:
    return SectionSummary(data).render()
