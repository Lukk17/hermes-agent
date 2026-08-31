"""
Section: ETH Gas prices.
"""

from pathlib import Path
from reports.sections._base import SectionRenderer

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"


class SectionGas(SectionRenderer):

    def render(self) -> str:
        gas = self.data.get("gas", {})
        if not gas or gas.get("status") == "error":
            return ""

        current = gas.get("current", {})
        if not current:
            return ""

        gas_fast = current.get("fast", 0) or 0
        gas_normal = current.get("normal", 0) or 0
        gas_slow = current.get("slow", 0) or 0

        lines = ["## ⛽ ETH Gas"]

        lines.append(f"**Now:** Fast {gas_fast} | Norm {gas_normal} | Slow {gas_slow}")

        # Load 12M high/low from gas_history.json
        history_path = DATA_DIR / "gas" / "gas_history.json"
        if history_path.exists():
            try:
                import json
                history = json.loads(history_path.read_text())
                all_fast = []
                for date_key, entry in history.items():
                    if date_key == "last_updated":
                        continue
                    if isinstance(entry, dict):
                        f = entry.get("fast") or entry.get("normal") or 0
                        if f:
                            all_fast.append(f)
                if all_fast:
                    high_12m = max(all_fast)
                    low_12m = min(all_fast)
                    lines.append(f"**12M High:** {high_12m} 📈")
                    lines.append(f"**12M Low:** {low_12m} 📉")
            except Exception:
                pass

        return "\n".join(lines)


def render(data: dict) -> str:
    return SectionGas(data).render()
