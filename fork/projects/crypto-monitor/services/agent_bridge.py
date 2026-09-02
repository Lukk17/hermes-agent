"""
services/agent_bridge.py - see services/__init__.py for scope.

This module contains ONLY the calls that leave our Python process.
Do not add Python-library wrappers here. Call `requests`, `urllib`,
`subprocess`, etc. directly from the file that needs them.

Public surface:

  post_to_discord(message_text, *, files=None, thread_name=None,
                  outbox_path=None) -> Path
      Queue a Discord message via the outbox. Long messages split into
      1900-char chunks. Files attach to chunk 1 only.

  publish_daily_report(report_path, *, chart_paths=None) -> Path
      High-level: build the full daily Discord sequence from
      report_latest.json + charts.

  consume_outbox(outbox) -> dict | None
      Read and clear the outbox. Used by the host-side poster to drain
      queued messages and forward them via `hermes send`.

  OUTBOX_PATH
      Default outbox location (data/reports/discord_outbox.json).
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.paths import REPORTS_DIR  # noqa: E402

DISCORD_MAX_MSG_LEN = 1900  # Headroom under Discord's 2000-char limit.
OUTBOX_PATH = REPORTS_DIR / "discord_outbox.json"


def _log(prefix: str, msg: str) -> None:
    print(f"[agent_bridge] {prefix} {msg}", file=sys.stderr)


@dataclass
class DiscordMessage:
    content: str
    files: list[str] = field(default_factory=list)
    thread_name: str | None = None

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "files": self.files,
            "thread_name": self.thread_name,
        }


def _split_for_discord(text: str, max_len: int = DISCORD_MAX_MSG_LEN) -> list[str]:
    """Split long text into Discord-safe chunks. Splits on newlines first,
    then on spaces if a single line is too long. Preserves order."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        candidate = (current + "\n" + line) if current else line
        if len(candidate) <= max_len:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(line) > max_len:
            for i in range(0, len(line), max_len):
                chunks.append(line[i : i + max_len])
        else:
            current = line
    if current:
        chunks.append(current)
    return chunks


def post_to_discord(
    message_text: str,
    *,
    files: list[str] | None = None,
    thread_name: str | None = None,
    outbox_path: Path | None = None,
) -> Path:
    """Queue a Discord message via the outbox file.

    Why an outbox file: there is no agent-callable `send_message` tool in
    this container (see /opt/hermes/tools/send_message_tool.py line 2276
    - intentionally not registered). The host-side poster script
    (`scripts/post_to_discord.py`) drains the outbox and forwards each
    chunk via `hermes send`.

    Long messages are split into 1900-char chunks. Files attach to the
    FIRST chunk only - attaching to every chunk spams the channel.

    Returns the outbox path so callers can verify the write landed.
    """
    target = Path(outbox_path) if outbox_path else OUTBOX_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    chunks = _split_for_discord(message_text)
    messages: list[dict] = []
    for i, chunk in enumerate(chunks):
        msg = DiscordMessage(content=chunk, thread_name=thread_name)
        if i == 0 and files:
            msg.files = [str(Path(f).resolve()) for f in files if Path(f).exists()]
        messages.append(msg.to_dict())

    payload = {
        "queued_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "message_count": len(messages),
        "messages": messages,
    }

    # Atomic write: write to .tmp then rename.
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(target)
    _log(
        "post_to_discord",
        f"queued {len(messages)} message(s) to {target} (files={len(messages[0]['files']) if messages else 0})",
    )
    return target


def publish_daily_report(
    report_path: Path | str,
    *,
    chart_paths: list[str] | None = None,
) -> Path:
    """High-level: take report_latest.json + chart PNGs and build a
    Discord-ready sequence via the outbox.

    Section order follows USER_REQUIREMENTS.md: title -> gauges -> tables
    -> narratives -> summary -> links.
    """
    report_path = Path(report_path)
    if not report_path.exists():
        _log("publish_daily_report", f"report not found: {report_path}")
        return post_to_discord(
            f":warning: crypto-monitor: report_latest.json missing at "
            f"{report_path}. Pipeline may have failed."
        )

    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        _log("publish_daily_report", f"report JSON decode error: {e}")
        return post_to_discord(
            f":warning: crypto-monitor: report_latest.json is malformed ({e})."
        )

    sections = data.get("sections") or {}
    charts = data.get("charts") or {}

    chart_order = [
        "gauge_fng",
        "gauge_cycle",
        "gauge_sentiment",
        "trending_narratives",
        "coin_sentiment",
        "btc_dominance",
        "btc_price",
        "gas_history",
    ]
    first_chunk_files: list[str] = []
    if chart_paths:
        first_chunk_files = [str(Path(p).resolve()) for p in chart_paths if Path(p).exists()]
    else:
        for key in chart_order:
            p = charts.get(key)
            if p and Path(p).exists():
                first_chunk_files.append(str(Path(p).resolve()))

    body_parts: list[str] = []
    if sections.get("title"):
        body_parts.append(sections["title"])
    for key in (
        "prices",
        "movers",
        "indicators",
        "sectors",
        "breadth",
        "etf",
        "stablecoins",
        "funding",
        "flows",
        "whales",
        "news",
        "airdrops",
        "summary",
        "links",
    ):
        val = sections.get(key)
        if val:
            body_parts.append(val)

    full_text = "\n".join(body_parts) if body_parts else "(report has no sections)"

    return post_to_discord(full_text, files=first_chunk_files or None)


def consume_outbox(outbox: Path | str) -> dict | None:
    """Read and clear the outbox. Returns the queued payload, or None if
    nothing was queued. Used by `scripts/post_to_discord.py` on the host.
    """
    outbox = Path(outbox)
    if not outbox.exists():
        return None
    try:
        payload = json.loads(outbox.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        _log("consume_outbox", f"outbox JSON decode error: {outbox}")
        return None
    outbox.unlink()
    return payload
