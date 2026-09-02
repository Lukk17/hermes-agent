#!/usr/bin/env python3
"""Publish the latest report to the chat configured in config/settings.json.

Runs inside the agent runtime container, which is the only place the runtime CLI
exists. The host is Windows and cannot run this.

Usage:
    cd /opt/projects/crypto-monitor && .venv/bin/python scripts/post_to_discord.py

Exit codes:
    0 - every message delivered
    1 - the runtime was unavailable or a message was not delivered
    2 - the delivery target or the report is missing or malformed
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from reports.report_builder import build_delivery  # noqa: E402
from services.agent_bridge import check_available, send_message  # noqa: E402
from src.config import load_config  # noqa: E402
from src.paths import REPORTS_DIR  # noqa: E402

REPORT_PATH = REPORTS_DIR / "report_latest.json"


def main() -> int:
    delivery = load_config().get("delivery") or {}
    platform = str(delivery.get("platform") or "").strip()
    conversation = str(delivery.get("conversation") or "").strip()
    thread = delivery.get("thread")

    if not platform or not conversation:
        print(
            "delivery target missing: set delivery.platform and delivery.conversation "
            "in config/settings.json",
            file=sys.stderr,
        )
        return 2

    try:
        items = build_delivery(REPORT_PATH)
    except OSError as exc:
        print(f"cannot read {REPORT_PATH}: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"{REPORT_PATH} is malformed: {exc}", file=sys.stderr)
        return 2

    check_available()

    published = 0
    for item in items:
        if not item.text.strip() and item.image is None:
            continue

        send_message(
            item.text,
            platform=platform,
            conversation=conversation,
            thread=str(thread) if thread else None,
            attachments=[item.image] if item.image else None,
        )
        published += 1

    print(
        f"published {published}/{len(items)} message(s) to {platform}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
