"""
Section: Crypto Sectors performance table.
"""

from reports.sections._base import SectionRenderer


class SectionSectors(SectionRenderer):

    def render(self) -> str:
        sectors = self.data.get("sectors", {})
        if not sectors or sectors.get("status") == "error":
            return ""

        sector_list = sectors.get("sectors", [])
        if not sector_list:
            return ""

        sorted_sectors = sorted(sector_list, key=lambda x: x.get("change_7d", 0) or 0, reverse=True)

        rows = []
        for s in sorted_sectors[:10]:
            name = (s.get("name") or s.get("full_name") or "")[:20]
            change_7d = s.get("change_7d", 0) or 0
            change_30d = s.get("change_30d", 0) or 0
            rows.append([name, f"{change_7d:+.1f}%", f"{change_30d:+.1f}%"])

        if not rows:
            return ""

        table = self.box_table(
            headers=["Sector", "7d", "30d"],
            rows=rows,
            aligns=["l", "r", "r"],
        )
        return f"```\n{table}\n```"


def render(data: dict) -> str:
    return SectionSectors(data).render()
