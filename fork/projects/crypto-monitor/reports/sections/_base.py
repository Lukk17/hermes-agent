"""
Base class for section renderers.
Provides shared helpers used across all sections.
"""

from pathlib import Path
from typing import Optional

from reports.tables import box_table, dual_column_table


class SectionRenderer:
    """Base class for all section renderers."""

    def __init__(self, data: dict):
        self.data = data

    def load_json(self, path: Path) -> Optional[dict]:
        """Load JSON file safely, returns None if missing."""
        if not path.exists():
            return None
        try:
            import json
            return json.loads(path.read_text())
        except Exception:
            return None

    def fmt_price(self, p: float) -> str:
        """Format price with appropriate precision."""
        if p >= 1000:
            return f"${p:,.0f}"
        elif p >= 1:
            return f"${p:,.2f}"
        elif p >= 0.01:
            return f"${p:.4f}"
        else:
            return f"${p:.6f}"

    def get_price(self, symbol: str) -> float:
        """Get price from coin_prices data by symbol."""
        coin_list = self.data.get("coin_prices", {}).get("coins", [])
        for c in coin_list:
            if c.get("symbol", "").upper() == symbol.upper():
                return c.get("price", 0) or 0
        return 0

    def box_table(self, headers, rows, aligns=None):
        """Proxy to reports.tables.box_table."""
        return box_table(headers, rows, aligns)

    def dual_column_table(self, left_title, right_title, left_items, right_items):
        """Proxy to reports.tables.dual_column_table."""
        return dual_column_table(left_title, right_title, left_items, right_items)

    def render(self, data: dict) -> str:
        """Override in subclass. Returns markdown content."""
        raise NotImplementedError
