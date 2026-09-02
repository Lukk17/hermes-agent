"""
services/agent_bridge.py - see services/__init__.py for scope.

This module contains ONLY the calls that leave our Python process.
Do not add Python-library wrappers here. Call `requests`, `urllib`,
`subprocess`, etc. directly from the file that needs them.

Public surface:

  check_available() -> None
      Raise AgentRuntimeUnavailable when the agent runtime CLI is not
      on PATH. Callers use this to fail loudly instead of degrading.

  send_message(text, *, platform, conversation, thread=None,
               attachments=None, timeout=60.0, dry_run=False) -> None
      Deliver a message to a chat platform. Long text is split into
      chunks; attachments ride the FIRST chunk as MEDIA: lines.
      Returns None on success and raises on every failure mode.

  AgentBridgeError
      Base class. AgentRuntimeUnavailable / AttachmentRejected /
      DeliveryFailed are the concrete failures a caller can act on.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

AGENT_CLI = "hermes"
MAX_MESSAGE_LEN = 1900  # Headroom under Discord's 2000-char limit.


class AgentBridgeError(RuntimeError):
    """Base class for every failure crossing the agent-runtime boundary."""


class AgentRuntimeUnavailable(AgentBridgeError):
    """The agent runtime CLI is not installed or not on PATH."""


class AttachmentRejected(AgentBridgeError):
    """An attachment cannot be delivered and the send was not attempted."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"attachment rejected: {path} ({reason})")


class DeliveryFailed(AgentBridgeError):
    """The runtime was invoked but the message was not delivered."""

    def __init__(self, message: str, *, delivered: int, total: int, detail: str) -> None:
        self.delivered = delivered
        self.total = total
        self.detail = detail
        super().__init__(f"{message} (delivered {delivered}/{total} chunk(s)): {detail}")


def _log(prefix: str, msg: str) -> None:
    print(f"[agent_bridge] {prefix} {msg}", file=sys.stderr)


def check_available() -> None:
    """Verify the agent runtime CLI is reachable.

    Raises:
        AgentRuntimeUnavailable: when the CLI is not on PATH.
    """
    if shutil.which(AGENT_CLI) is None:
        raise AgentRuntimeUnavailable(
            f"{AGENT_CLI!r} is not on PATH; this project must run inside the agent container"
        )


def _build_target(platform: str, conversation: str, thread: str | None) -> str:
    """Build the runtime's `platform:chat_id[:thread_id]` target string."""
    parts = {"platform": platform, "conversation": conversation}
    if thread is not None:
        parts["thread"] = thread

    for label, value in parts.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be a non-empty string")
        if ":" in value or any(c.isspace() for c in value):
            raise ValueError(f"{label} must not contain ':' or whitespace: {value!r}")

    target = f"{platform}:{conversation}"
    if thread is not None:
        target = f"{target}:{thread}"
    return target


def _resolve_attachments(attachments: list[Path] | None) -> list[Path]:
    """Resolve attachment paths to absolute files the runtime can read.

    Raises:
        AttachmentRejected: when a path is missing, is not a file, or holds a line break.
    """
    if not attachments:
        return []

    resolved: list[Path] = []
    for raw in attachments:
        path = Path(raw).expanduser().resolve()
        if "\n" in str(path) or "\r" in str(path):
            raise AttachmentRejected(path, "path contains a line break")
        if not path.exists():
            raise AttachmentRejected(path, "file does not exist")
        if not path.is_file():
            raise AttachmentRejected(path, "path is not a regular file")
        resolved.append(path)
    return resolved


def _split_for_delivery(text: str, max_len: int) -> list[str]:
    """Split text into chunks of at most max_len, on newlines where possible."""
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


def _build_chunks(text: str, attachments: list[Path]) -> list[str]:
    """Split text and append the MEDIA block to the first chunk.

    The MEDIA lines must stay plain text: the gateway masks code blocks,
    inline backticks and blockquotes before scanning for them, so a MEDIA
    line inside any of those is silently dropped.

    Raises:
        AttachmentRejected: when the MEDIA block alone exceeds one message.
    """
    media_block = "\n".join(f"MEDIA:{path}" for path in attachments)
    reserved = len(media_block) + 1 if media_block else 0
    if reserved >= MAX_MESSAGE_LEN:
        raise AttachmentRejected(attachments[-1], "attachment list does not fit in one message")

    chunks = _split_for_delivery(text, MAX_MESSAGE_LEN - reserved)
    if media_block:
        chunks[0] = f"{chunks[0]}\n{media_block}"
    return chunks


def _parse_result(stdout: str) -> dict:
    """Parse the runtime's --json payload.

    Raises:
        ValueError: when stdout is not the single JSON object the CLI promises.
    """
    payload = json.loads(stdout.strip())
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object, got {type(payload).__name__}")
    return payload


def _deliver_chunk(target: str, chunk: str, timeout: float, index: int, total: int) -> None:
    """Send one chunk and verify the runtime actually delivered it.

    Raises:
        AgentRuntimeUnavailable: when the CLI disappeared between check and call.
        DeliveryFailed: on timeout, non-zero exit, unparsable output, or a
            payload reporting an error, a skip, or anything but success.
    """
    command = [AGENT_CLI, "send", "--json", "--to", target, chunk]

    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise AgentRuntimeUnavailable(f"{AGENT_CLI!r} disappeared from PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise DeliveryFailed(
            "agent runtime timed out",
            delivered=index,
            total=total,
            detail=f"no answer after {timeout}s",
        ) from exc

    try:
        payload = _parse_result(completed.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        raise DeliveryFailed(
            "agent runtime returned unreadable output",
            delivered=index,
            total=total,
            detail=(
                f"{exc}; stdout={completed.stdout.strip()[:400]!r} "
                f"stderr={completed.stderr.strip()[:400]!r}"
            ),
        ) from exc

    # A skipped send exits 0, so the exit code alone would report an
    # undelivered message as delivered.
    if payload.get("error"):
        raise DeliveryFailed(
            "agent runtime reported an error",
            delivered=index,
            total=total,
            detail=str(payload["error"]),
        )
    if payload.get("skipped"):
        raise DeliveryFailed(
            "agent runtime skipped the message",
            delivered=index,
            total=total,
            detail=json.dumps(payload),
        )
    if payload.get("success") is not True:
        raise DeliveryFailed(
            "agent runtime did not confirm delivery",
            delivered=index,
            total=total,
            detail=json.dumps(payload),
        )
    if completed.returncode != 0:
        raise DeliveryFailed(
            "agent runtime exited non-zero",
            delivered=index,
            total=total,
            detail=f"exit={completed.returncode}; stderr={completed.stderr.strip()[:400]!r}",
        )


def send_message(
    text: str,
    *,
    platform: str,
    conversation: str,
    thread: str | None = None,
    attachments: list[Path] | None = None,
    timeout: float = 60.0,
    dry_run: bool = False,
) -> None:
    """Deliver `text` to a chat platform through the agent runtime.

    Args:
        conversation: chat id or `#channel-name`, never a full target string.
        timeout: seconds allowed per chunk, not for the whole message.

    Raises:
        ValueError: on an empty message or a malformed platform/conversation/thread.
        AgentRuntimeUnavailable: when the runtime CLI is not on PATH.
        AttachmentRejected: when an attachment cannot be delivered.
        DeliveryFailed: when a chunk was not confirmed as delivered.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError(f"timeout must be a positive number, got {timeout!r}")

    target = _build_target(platform, conversation, thread)
    resolved = _resolve_attachments(attachments)
    chunks = _build_chunks(text, resolved)

    check_available()

    if dry_run:
        for i, chunk in enumerate(chunks, start=1):
            _log("dry_run", f"would send chunk {i}/{len(chunks)} to {target} ({len(chunk)} chars)")
        return

    for index, chunk in enumerate(chunks):
        _deliver_chunk(target, chunk, timeout, index, len(chunks))

    _log("send_message", f"delivered {len(chunks)} chunk(s) to {target} (files={len(resolved)})")
