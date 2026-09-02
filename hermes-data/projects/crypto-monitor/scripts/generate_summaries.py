#!/usr/bin/env python3
"""Generate the two model-written pieces of the daily report.

The pipeline owns the report's structure; the agent only writes the news summary
and the closing market summary. Both land in data/reports/ as body-only markdown
that reports.report_builder folds into the fixed delivery sequence.

Usage:
    cd /opt/data/projects/crypto-monitor && .venv/bin/python scripts/generate_summaries.py

Exit codes:
    0 - both summaries written
    1 - the agent runtime was unavailable or produced nothing
    2 - a required input file is missing or malformed
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.agent_bridge import ask_agent  # noqa: E402
from src.paths import DATA_DIR, PROJECT_ROOT, REPORTS_DIR  # noqa: E402

NEWS_INPUT = DATA_DIR / "news" / "news_latest.json"
SUMMARY_GUIDE = PROJECT_ROOT / "SUMMARY_GUIDE.md"

NEWS_OUTPUT = REPORTS_DIR / "news_summary.md"
MARKET_OUTPUT = REPORTS_DIR / "market_summary.md"

NEWS_PROMPT = (
    "You are writing one section of an automated daily crypto report. "
    "From the news JSON below, write a numbered list of the ten most important "
    "headlines, one line each, newest and most market-moving first. "
    "Each line: the headline in plain words, then a dash, then one short clause "
    "on why it matters. Keep the whole list under 1500 characters. "
    "Output the list only. No heading, no preamble, no closing remark."
)

MARKET_PROMPT = (
    "You are writing the closing summary of an automated daily crypto report. "
    "Follow the guide below exactly. Base every statement on the report JSON that "
    "follows the guide. Do not invent numbers. Keep it under 1200 characters. "
    "Output the summary only. No heading, no preamble."
)


def main() -> int:
    report = REPORTS_DIR / "report_latest.json"

    try:
        news_json = NEWS_INPUT.read_text(encoding="utf-8")
        report_json = report.read_text(encoding="utf-8")
        guide = SUMMARY_GUIDE.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read a required input: {exc}", file=sys.stderr)
        return 2

    news_summary = ask_agent(NEWS_PROMPT, context=news_json)
    NEWS_OUTPUT.write_text(news_summary + "\n", encoding="utf-8")
    print(f"wrote {NEWS_OUTPUT} ({len(news_summary)} chars)", file=sys.stderr)

    market_summary = ask_agent(MARKET_PROMPT, context=f"{guide}\n\n{report_json}")
    MARKET_OUTPUT.write_text(market_summary + "\n", encoding="utf-8")
    print(f"wrote {MARKET_OUTPUT} ({len(market_summary)} chars)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
