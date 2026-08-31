"""
reports/sections/ - Individual report section renderers.

Each module contains one section's rendering logic.
All return markdown string content.
"""

from reports.sections.section_prices import render as render_prices
from reports.sections.section_movers import render as render_movers
from reports.sections.section_indicators import render as render_indicators
from reports.sections.section_sectors import render as render_sectors
from reports.sections.section_gas import render as render_gas
from reports.sections.section_breadth import render as render_breadth
from reports.sections.section_etf import render as render_etf
from reports.sections.section_stablecoins import render as render_stablecoins
from reports.sections.section_funding import render as render_funding
from reports.sections.section_flows import render as render_flows
from reports.sections.section_whales import render as render_whales
from reports.sections.section_news import render as render_news
from reports.sections.section_airdrops import render as render_airdrops
from reports.sections.section_summary import render as render_summary
from reports.sections.section_links import render as render_links

__all__ = [
    "render_prices",
    "render_movers",
    "render_indicators",
    "render_sectors",
    "render_gas",
    "render_breadth",
    "render_etf",
    "render_stablecoins",
    "render_funding",
    "render_flows",
    "render_whales",
    "render_news",
    "render_airdrops",
    "render_summary",
    "render_links",
]
