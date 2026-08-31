#!/usr/bin/env python3
"""
Daily Report - entry point.

Loads data, builds report via report_builder, and sends to Discord.
Single responsibility: orchestrate generation and delivery.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from reports.report_builder import build_report


if __name__ == "__main__":
    text_only = "--text-only" in sys.argv
    build_report(text_only=text_only)
