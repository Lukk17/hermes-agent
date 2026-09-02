"""
Section: Airdrops table.
"""

import json
from pathlib import Path
from reports.sections._base import SectionRenderer

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"


class SectionAirdrops(SectionRenderer):

    def render(self) -> str:
        airdrops = self.data.get("airdrops", {}) or {}

        # Try latest first
        ranked = airdrops.get("ranked_airdrops", [])
        urgent = airdrops.get("urgent", []) or []
        opportunities = airdrops.get("total_opportunities", 0)

        # Fall back to history if latest is empty
        if not ranked:
            history_path = DATA_DIR / "airdrops" / "airdrops_history.json"
            if history_path.exists():
                try:
                    history = json.loads(history_path.read_text())
                    dates = sorted([k for k in history.keys() if k != "last_updated"])
                    if dates:
                        latest = history.get(dates[-1], {})
                        ranked = latest.get("ranked_airdrops", [])
                        urgent = latest.get("urgent", []) or []
                        opportunities = latest.get("total_opportunities", 0)
                except Exception:
                    pass

        lines = ["## 🪂 Airdrops"]

        # Show urgent airdrops with URLs
        if urgent:
            urls = []
            for a in urgent[:5]:
                name = a.get("name", "Unknown")
                url = a.get("url") or ""
                tier = a.get("tier_emoji", "")
                lines.append(f"{tier} {name}")
                if url:
                    urls.append(f"<{url}>")
            if urls:
                lines.append(" ".join(urls))

        # Show ranked table if we have data
        if ranked:
            rows = []
            for a in ranked[:8]:
                name = (a.get("name") or "")[:18]
                tier = a.get("tier", "?")[:3]
                tier_emoji = a.get("tier_emoji", "")
                prob = (a.get("probability", "?") or "").replace("_", " ")[:8]
                cost = a.get("cost", "?")[:8]
                rows.append([f"{tier_emoji}{name}", f"{tier}", f"{prob}", f"{cost}"])

            table = self.box_table(
                headers=["Airdrop", "Tier", "Prob", "Cost"],
                rows=rows,
                aligns=["l", "l", "l", "l"],
            )
            lines.append(f"```\n{table}\n```")
        elif opportunities > 0:
            lines.append(f"**Total opportunities:** {opportunities}")
        else:
            return ""

        return "\n".join(lines) if len(lines) > 1 else ""


def render(data: dict) -> str:
    return SectionAirdrops(data).render()
