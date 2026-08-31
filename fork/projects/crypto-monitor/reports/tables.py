#!/usr/bin/env python3
"""
Discord box-drawing table generator.

Generates Unicode box-drawing tables for Discord code blocks.
No emoji inside tables — they break monospace alignment.

Usage:
    from tables import box_table
    print(box_table(
        headers=["Coin", "Price", "24h"],
        rows=[["BTC", "$67,356", "-2.6%"], ["ETH", "$1,949", "-3.8%"]],
        aligns=["l", "r", "r"],
    ))
"""


def box_table(
    headers: list[str],
    rows: list[list[str]],
    aligns: list[str] | None = None,
    min_widths: list[int] | None = None,
) -> str:
    """Generate a Unicode box-drawing table.

    Args:
        headers: Column header strings.
        rows: List of rows, each a list of cell strings.
        aligns: Per-column alignment: 'l' (left) or 'r' (right).
                Default: first column left, rest right.
        min_widths: Minimum column widths (optional).

    Returns:
        Complete table string (without code block fences).
    """
    ncols = len(headers)
    if aligns is None:
        aligns = ["l"] + ["r"] * (ncols - 1)

    # Compute column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row[:ncols]):
            widths[i] = max(widths[i], len(cell))
    if min_widths:
        for i, mw in enumerate(min_widths[:ncols]):
            widths[i] = max(widths[i], mw)

    def _cell(text: str, col: int) -> str:
        w = widths[col]
        if aligns[col] == "r":
            return text.rjust(w)
        return text.ljust(w)

    def _border(left: str, mid: str, right: str, fill: str = "─") -> str:
        parts = [left]
        for i, w in enumerate(widths):
            parts.append(fill * (w + 2))
            parts.append(mid if i < ncols - 1 else right)
        return "".join(parts)

    def _row(cells: list[str]) -> str:
        parts = ["│"]
        for i, cell in enumerate(cells[:ncols]):
            parts.append(f" {_cell(cell, i)} ")
            parts.append("│")
        return "".join(parts)

    lines = []
    lines.append(_border("┌", "┬", "┐"))
    lines.append(_row(headers))
    lines.append(_border("├", "┼", "┤"))
    for row in rows:
        # Pad row if shorter than headers
        padded = list(row) + [""] * (ncols - len(row))
        lines.append(_row(padded))
    lines.append(_border("└", "┴", "┘"))

    return "\n".join(lines)


def box_table_with_separator(
    headers: list[str],
    rows: list[list[str]],
    separator_before: int = -1,
    aligns: list[str] | None = None,
    min_widths: list[int] | None = None,
) -> str:
    """Like box_table but inserts a ├──┼──┤ separator before a specific row index.

    Useful for summary/total rows at the bottom.
    """
    ncols = len(headers)
    if aligns is None:
        aligns = ["l"] + ["r"] * (ncols - 1)

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row[:ncols]):
            widths[i] = max(widths[i], len(cell))
    if min_widths:
        for i, mw in enumerate(min_widths[:ncols]):
            widths[i] = max(widths[i], mw)

    def _cell(text: str, col: int) -> str:
        w = widths[col]
        if aligns[col] == "r":
            return text.rjust(w)
        return text.ljust(w)

    def _border(left: str, mid: str, right: str) -> str:
        parts = [left]
        for i, w in enumerate(widths):
            parts.append("─" * (w + 2))
            parts.append(mid if i < ncols - 1 else right)
        return "".join(parts)

    def _row(cells: list[str]) -> str:
        parts = ["│"]
        for i, cell in enumerate(cells[:ncols]):
            parts.append(f" {_cell(cell, i)} ")
            parts.append("│")
        return "".join(parts)

    # Handle negative index
    if separator_before < 0:
        separator_before = len(rows) + separator_before

    lines = []
    lines.append(_border("┌", "┬", "┐"))
    lines.append(_row(headers))
    lines.append(_border("├", "┼", "┤"))
    for idx, row in enumerate(rows):
        if idx == separator_before:
            lines.append(_border("├", "┼", "┤"))
        padded = list(row) + [""] * (ncols - len(row))
        lines.append(_row(padded))
    lines.append(_border("└", "┴", "┘"))

    return "\n".join(lines)


def dual_column_table(
    left_header: str,
    right_header: str,
    left_items: list[str],
    right_items: list[str],
    col_width: int = 15,
) -> str:
    """Two-column side-by-side table (e.g. Gainers | Losers)."""
    max_rows = max(len(left_items), len(right_items))
    left_items = left_items + [""] * (max_rows - len(left_items))
    right_items = right_items + [""] * (max_rows - len(right_items))

    lw = max(col_width, len(left_header), *(len(x) for x in left_items))
    rw = max(col_width, len(right_header), *(len(x) for x in right_items))

    def _border(l, m, r):
        return f"{l}{'─' * (lw + 2)}{m}{'─' * (rw + 2)}{r}"

    lines = []
    lines.append(_border("┌", "┬", "┐"))
    lines.append(f"│ {left_header.ljust(lw)} │ {right_header.ljust(rw)} │")
    lines.append(_border("├", "┼", "┤"))
    for l, r in zip(left_items, right_items):
        lines.append(f"│ {l.ljust(lw)} │ {r.ljust(rw)} │")
    lines.append(_border("└", "┴", "┘"))

    return "\n".join(lines)


if __name__ == "__main__":
    # Demo
    print("=== Price Table ===")
    print(box_table(
        headers=["Coin", "Price", "24h"],
        rows=[
            ["BTC", "$67,356", "-2.6%"],
            ["ETH", "$1,949", "-3.8%"],
            ["SOL", "$79.69", "-4.4%"],
        ],
        aligns=["l", "r", "r"],
    ))

    print("\n=== Exchange Flows ===")
    print(box_table_with_separator(
        headers=["Exchange", "BTC", "ETH"],
        rows=[
            ["Binance", "-234 BTC <-", "+1200 ETH ->"],
            ["Coinbase", "-89 BTC <-", "-456 ETH <-"],
            ["Kraken", "+12 BTC ->", "-78 ETH <-"],
            ["Net", "-311 BTC <-", "+666 ETH ->"],
        ],
        separator_before=-1,
        aligns=["l", "r", "r"],
    ))

    print("\n=== Top Movers ===")
    print(dual_column_table(
        "Gainers", "Losers",
        ["HYPE   +25.1%", "RAIN   +15.3%", "CC     +14.2%"],
        ["SOL     -4.4%", "XMR     -3.8%", "BTC     -2.6%"],
    ))
