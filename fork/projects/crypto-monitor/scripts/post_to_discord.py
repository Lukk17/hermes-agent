#!/usr/bin/env python3
"""
Host-side Discord poster.

Reads data/reports/discord_outbox.json (written by
services.agent_bridge.post_to_discord during the pipeline run) and
forwards each message chunk via `hermes send`.

This script runs on the HOST (the cron job), not inside the hermes container,
because `hermes` CLI is only available there. Inside the container, callers
should never invoke this directly - they go through services.external.

Usage:
    /opt/projects/crypto-monitor/.venv/bin/python /opt/projects/crypto-monitor/scripts/post_to_discord.py

Exit codes:
    0 - posted (or outbox empty)
    1 - hermes send failed for at least one chunk
    2 - outbox malformed

Cron wiring (host):
    Run daily_report_pipeline.sh, then this script.
    Add to the cron prompt: "...then run scripts/post_to_discord.py".

Falls back to a dry-run if HERMES_BIN is unset or hermes is not on PATH -
useful for local development and CI. In dry-run the script just prints the
outbox payload to stdout.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Project layout - this script runs on the host, so use absolute paths.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.agent_bridge import consume_outbox, OUTBOX_PATH  # noqa: E402

HERMES_BIN = os.environ.get("HERMES_BIN") or shutil.which("hermes")
TARGET = os.environ.get("CRYPTO_MONITOR_DISCORD_TARGET", "discord:1470798593118965956:1543645766076342312")


def _post_one(content: str, files: list[str]) -> bool:
    """Send one message + files via `hermes send`. Returns True on success."""
    if not HERMES_BIN:
        print(f"[dry-run] would post ({len(content)} chars, {len(files)} files):", file=sys.stderr)
        print("---", file=sys.stderr)
        print(content, file=sys.stderr)
        for f in files:
            print(f"[dry-run] file: {f}", file=sys.stderr)
        print("---", file=sys.stderr)
        return True

    cmd = [
        HERMES_BIN,
        "send",
        "--to", TARGET,
        "--content", content,
    ]
    for f in files:
        cmd.extend(["--file", f])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print(f"hermes send timed out", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"hermes binary not found at {HERMES_BIN}", file=sys.stderr)
        return False

    if result.returncode != 0:
        print(f"hermes send failed (rc={result.returncode}): {(result.stderr or result.stdout).strip()}", file=sys.stderr)
        return False

    print(f"posted ({len(content)} chars, {len(files)} files)", file=sys.stderr)
    return True


def main() -> int:
    payload = consume_outbox(OUTBOX_PATH)
    if payload is None:
        print(f"outbox empty at {OUTBOX_PATH}; nothing to post", file=sys.stderr)
        return 0

    messages = payload.get("messages") or []
    if not isinstance(messages, list) or not messages:
        print(f"outbox malformed: no 'messages' array at {OUTBOX_PATH}", file=sys.stderr)
        return 2

    failed = 0
    for i, msg in enumerate(messages, start=1):
        content = msg.get("content", "")
        files = msg.get("files") or []
        ok = _post_one(content, files)
        if not ok:
            failed += 1

    if failed:
        print(f"{failed}/{len(messages)} chunks failed to post", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
