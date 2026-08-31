"""
Section: Whale Activity (known whales + movements).
"""

from reports.sections._base import SectionRenderer

BASE_DIR = __import__("pathlib").Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"


class SectionWhales(SectionRenderer):

    def render(self) -> str:
        whales = self.data.get("whales", {})
        if not whales:
            return ""

        whale_lines = []

        # Known Whales table
        btc_whales = whales.get("bitcoin", [])
        if btc_whales:
            whale_lines.append("## 🐋 Known Whales")
            rows = []
            for w in btc_whales[:18]:
                label = (w.get("label") or "")[:12]
                balance = w.get("balance_btc", 0) or 0
                chain = w.get("chain", "BTC")[:3]
                rows.append([label, f"{balance:,.2f} BTC", chain])

            table = self.box_table(
                headers=["Label", "Balance", "Chain"],
                rows=rows,
                aligns=["l", "r", "l"],
            )
            whale_lines.append(f"```\n{table}\n```")

        # Whale Moves - from whale_signals or whales data
        whale_signals = self.data.get("whale_signals", {}) or {}
        signals = whale_signals.get("signals", []) or []

        if signals:
            whale_lines.append("## 🐋 Whale Moves")
            moves = []
            for sig in signals[:10]:
                entity = (sig.get("entity") or sig.get("address", "Unknown"))[:12]
                amount = sig.get("amount_btc", 0) or 0
                direction = sig.get("direction", "unknown")
                dir_arrow = "BUY" if direction == "inflow" else "SELL"
                moves.append([entity, f"{amount:+.0f} BTC", dir_arrow])

            if moves:
                table = self.box_table(
                    headers=["Entity", "Amount", "Dir"],
                    rows=moves,
                    aligns=["l", "r", "l"],
                )
                whale_lines.append(f"```\n{table}\n```")
        else:
            whale_lines.append("## 🐋 Whale Moves")
            whale_lines.append("No significant whale movements since last report.")

        return "\n".join(whale_lines)


def render(data: dict) -> str:
    return SectionWhales(data).render()
