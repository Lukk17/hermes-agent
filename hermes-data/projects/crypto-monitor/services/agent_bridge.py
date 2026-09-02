"""Driven adapter for the agent runtime.

The only place this project leaves its own process. Everything specific to the
Hermes CLI lives here, so moving the project to another runtime means rewriting
this file and nothing else. No domain logic, no path constants, no library
wrappers.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

DISCORD_MAX_MSG_LEN = 1900  # Headroom under Discord's 2000-char limit.

# Linux caps one argv entry at 128 KiB (MAX_ARG_STRLEN); stay well under it.
PROMPT_MAX_CHARS = 60_000

_RUNTIME_BIN = "hermes"

# Narrowest toolset in the runtime's catalog: it resolves to zero tools, so the
# model cannot reach anything that would make one day's report differ from the next.
_NO_TOOLS_TOOLSET = "context_engine"

# Mirrors the runtime's own media denylist, so it can drift when upstream adds a prefix.
_DENIED_PATH_PREFIXES = (
    "/etc",
    "/proc",
    "/sys",
    "/dev",
    "/root",
    "/boot",
    "/var/log",
    "/var/lib",
    "/var/run",
)

_DENIED_HOME_SUBPATHS = (
    ".ssh",
    ".aws",
    ".gnupg",
    ".kube",
    ".docker",
    ".config",
    ".azure",
    ".gcloud",
)


class AgentBridgeError(RuntimeError):
    """Base class for every failure raised while crossing the process boundary."""


class AgentRuntimeUnavailable(AgentBridgeError):
    """The agent runtime this adapter shells out to is not installed."""


class AttachmentRejected(AgentBridgeError):
    """An attachment cannot be delivered, so nothing at all was sent."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"attachment rejected: {path} ({reason})")
        self.path = path
        self.reason = reason


class PromptTooLarge(AgentBridgeError):
    """The prompt exceeds what the runtime can accept as a single argument."""

    def __init__(self, size: int, limit: int) -> None:
        super().__init__(
            f"prompt is {size} characters, limit is {limit}; "
            "split the input or teach the adapter to pass it by file"
        )
        self.size = size
        self.limit = limit


class GenerationFailed(AgentBridgeError):
    """The runtime ran but produced no usable text."""

    def __init__(self, message: str, *, detail: str) -> None:
        super().__init__(f"{message}: {detail}")
        self.detail = detail


class DeliveryFailed(AgentBridgeError):
    """A message was only partly delivered. The adapter never retries on its own."""

    def __init__(
        self, message: str, *, delivered: int, total: int, detail: str
    ) -> None:
        super().__init__(f"{message}: {delivered}/{total} chunk(s) delivered: {detail}")
        self.delivered = delivered
        self.total = total
        self.detail = detail


def _log(message: str) -> None:
    print(f"[agent_bridge] {message}", file=sys.stderr)


def check_available() -> None:
    """Verify the agent runtime can be invoked at all.

    Raises:
        AgentRuntimeUnavailable: the runtime executable is not on PATH.
    """
    if shutil.which(_RUNTIME_BIN) is None:
        raise AgentRuntimeUnavailable(
            f"{_RUNTIME_BIN!r} is not on PATH; "
            "this code must run inside the agent runtime"
        )


def ask_agent(
    prompt: str, *, context: str | None = None, timeout: float = 300.0
) -> str:
    """Ask the agent runtime for generated text and return its final response.

    Runs with no tools and inherits the caller's working directory, so the runtime
    picks up that directory's agent instructions.

    Raises:
        ValueError: blank prompt.
        PromptTooLarge: the composed prompt exceeds PROMPT_MAX_CHARS.
        AgentRuntimeUnavailable: the runtime executable is not on PATH.
        GenerationFailed: the runtime errored, timed out, or returned nothing.
    """
    if not prompt.strip():
        raise ValueError("prompt must not be blank")

    composed = prompt.strip()
    if context and context.strip():
        composed = f"{composed}\n\n{context.strip()}"

    if len(composed) > PROMPT_MAX_CHARS:
        raise PromptTooLarge(len(composed), PROMPT_MAX_CHARS)

    check_available()

    command = [_RUNTIME_BIN, "-z", composed, "--toolsets", _NO_TOOLS_TOOLSET]

    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError as exc:
        raise AgentRuntimeUnavailable(f"{_RUNTIME_BIN!r} is not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise GenerationFailed(
            "runtime timed out", detail=f"no result after {timeout}s"
        ) from exc

    if completed.returncode != 0:
        raise GenerationFailed(
            f"runtime exited {completed.returncode}",
            detail=(completed.stderr or completed.stdout).strip()[:500],
        )

    generated = completed.stdout.strip()
    if not generated:
        raise GenerationFailed(
            "runtime returned no text", detail=completed.stderr.strip()[:500]
        )

    _log(f"generated {len(generated)} characters")

    return generated


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
    """Deliver one message in platform-sized chunks, attachments on the first chunk.

    Everything is validated before the first chunk leaves, so a rejected attachment can
    never leave a half-posted report. That pre-flight is the only guarantee attachments
    are delivered: the runtime's success payload carries no attachment count. Blank text
    is allowed when attachments are given, and the body is then the MEDIA lines alone.

    Raises:
        ValueError: blank platform or conversation, or blank text with no attachments.
        AttachmentRejected: an attachment is not an absolute, deliverable file.
        AgentRuntimeUnavailable: the runtime executable is not on PATH.
        DeliveryFailed: a chunk was refused, skipped, or not confirmed delivered.
    """
    if not platform.strip():
        raise ValueError("platform must not be blank")
    if not conversation.strip():
        raise ValueError("conversation must not be blank")

    media_lines = [f"MEDIA:{_validated_attachment(Path(a))}" for a in attachments or []]

    body = text.strip()
    if not body and not media_lines:
        raise ValueError("nothing to deliver: empty text and no attachments")

    target = f"{platform.strip()}:{conversation.strip()}"
    if thread and thread.strip():
        target = f"{target}:{thread.strip()}"

    chunks = _split_for_discord(body) if body else []
    chunks = _attach_media(chunks, media_lines)

    if dry_run:
        _log(
            f"dry run: {len(chunks)} chunk(s) to {target} "
            f"with {len(media_lines)} attachment(s)"
        )
        for chunk in chunks:
            _log(f"dry run chunk:\n{chunk}")
        return

    check_available()

    for index, chunk in enumerate(chunks):
        _deliver_chunk(
            chunk, target=target, timeout=timeout, delivered=index, total=len(chunks)
        )

    _log(f"delivered {len(chunks)} chunk(s) to {target}")


def _attach_media(chunks: list[str], media_lines: list[str]) -> list[str]:
    if not media_lines:
        return chunks
    if not chunks:
        return ["\n".join(media_lines)]

    # Plain text only: the runtime blanks out fenced, backticked and quoted spans
    # before scanning for MEDIA: tags, and would silently drop the attachment.
    return ["\n".join([chunks[0], "", *media_lines]), *chunks[1:]]


def _validated_attachment(raw: Path) -> str:
    if not raw.is_absolute():
        raise AttachmentRejected(raw, "path is not absolute")

    resolved = raw.resolve()
    if not resolved.is_file():
        raise AttachmentRejected(raw, "not an existing regular file")
    if _is_denied(resolved):
        raise AttachmentRejected(raw, "under a path the runtime refuses to deliver")

    return str(resolved)


def _is_denied(path: Path) -> bool:
    denied = [Path(prefix) for prefix in _DENIED_PATH_PREFIXES]
    denied.extend(Path.home() / sub for sub in _DENIED_HOME_SUBPATHS)
    return any(path == entry or entry in path.parents for entry in denied)


def _deliver_chunk(
    chunk: str,
    *,
    target: str,
    timeout: float,
    delivered: int,
    total: int,
) -> None:
    command = [_RUNTIME_BIN, "send", "--json", "--to", target, chunk]

    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError as exc:
        raise AgentRuntimeUnavailable(f"{_RUNTIME_BIN!r} is not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise DeliveryFailed(
            "runtime timed out",
            delivered=delivered,
            total=total,
            detail=f"no result after {timeout}s",
        ) from exc

    output = (completed.stderr or completed.stdout).strip()

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DeliveryFailed(
            "runtime returned no JSON result",
            delivered=delivered,
            total=total,
            detail=output[:500],
        ) from exc

    if not isinstance(payload, dict):
        raise DeliveryFailed(
            "runtime returned an unexpected JSON result",
            delivered=delivered,
            total=total,
            detail=output[:500],
        )

    if completed.returncode != 0:
        raise DeliveryFailed(
            f"runtime exited {completed.returncode}",
            delivered=delivered,
            total=total,
            detail=str(payload.get("error") or output[:500]),
        )
    if payload.get("error"):
        raise DeliveryFailed(
            "runtime reported an error",
            delivered=delivered,
            total=total,
            detail=str(payload["error"]),
        )
    # A skipped send exits 0, so an exit-code-only check would count an
    # undelivered message as delivered.
    if payload.get("skipped"):
        raise DeliveryFailed(
            "runtime skipped the message",
            delivered=delivered,
            total=total,
            detail=str(payload["skipped"]),
        )
    if payload.get("success") is not True:
        raise DeliveryFailed(
            "runtime did not confirm delivery",
            delivered=delivered,
            total=total,
            detail=json.dumps(payload)[:500],
        )


def _split_for_discord(text: str, max_len: int = DISCORD_MAX_MSG_LEN) -> list[str]:
    """Split long text into Discord-safe chunks. Splits on newlines first,
    then on spaces if a single line is too long. Preserves order."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= max_len:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""
        if len(line) <= max_len:
            current = line
            continue

        pieces = _split_on_spaces(line, max_len)
        chunks.extend(pieces[:-1])
        current = pieces[-1]

    if current:
        chunks.append(current)

    return chunks


def _split_on_spaces(line: str, max_len: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for word in line.split(" "):
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_len:
            current = candidate
            continue

        if current:
            pieces.append(current)
            current = ""
        while len(word) > max_len:
            pieces.append(word[:max_len])
            word = word[max_len:]
        current = word

    if current:
        pieces.append(current)

    return pieces or [""]
