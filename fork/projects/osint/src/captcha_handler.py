"""Human intervention handler for OSINT pipeline.

When a scraper hits captcha/login, sends VNC URL to Discord and waits for user
to solve it before continuing.
"""

import asyncio
import json
import subprocess
import time


# Channel ID for osint - #claw-osint
OSINT_CHANNEL_ID = "1470798594163478632"
# Bot username to filter out
BOT_USERNAME = "AscendClaw"


async def send_captcha_to_discord(
    vnc_url: str,
    url: str,
    intervention_type: str,
    channel_id: str = None,
) -> None:
    """Send captcha notification to Discord."""
    channel = channel_id or OSINT_CHANNEL_ID

    message = (
        f"Captcha required to continue OSINT scan.\n\n"
        f"URL: {url}\n"
        f"Type: {intervention_type}\n\n"
        f"Click here to solve: {vnc_url}\n\n"
        f"Once solved, reply with just the word **done** to continue."
    )

    # Run in thread to avoid blocking event loop
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: subprocess.run(
            ["openclaw", "message", "send",
             "--channel", "discord",
             "--target", f"channel:{channel}",
             "--message", message],
            capture_output=True,
            text=True,
            timeout=30,
        )
    )


def _read_messages_sync(channel: str, limit: int = 10) -> list:
    """Read messages from Discord channel synchronously."""
    try:
        result = subprocess.run(
            ["openclaw", "message", "read",
             "--channel", "discord",
             "--target", f"channel:{channel}",
             "--limit", str(limit),
             "--json"],
            capture_output=True,
            text=True,
            timeout=30,  # Allow up to 30s for slow --json reads
        )

        if result.returncode == 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
                return data.get("payload", {}).get("messages", [])
            except (json.JSONDecodeError, Exception):
                pass
    except subprocess.TimeoutExpired:
        pass

    return []


async def wait_for_user_confirmation(
    channel_id: str = None,
    timeout_seconds: float = 600.0,
) -> bool:
    """Wait for user to say 'done' in Discord.

    Returns True if user confirmed, False if timeout.
    Ignores messages from the bot itself.
    """
    channel = channel_id or OSINT_CHANNEL_ID
    start_time = time.time()
    poll_interval = 5.0  # seconds between polls (openclaw read is slow)

    while True:
        elapsed = time.time() - start_time

        # Overall timeout check
        if elapsed >= timeout_seconds:
            return False

        # Run Discord read in executor to avoid blocking
        loop = asyncio.get_running_loop()
        messages = await loop.run_in_executor(
            None, _read_messages_sync, channel, 10
        )

        # Check for "done" from user
        for msg in messages:
            author = msg.get("author", {})
            username = author.get("username", "")
            if username == BOT_USERNAME:
                continue
            content = msg.get("content", "").lower().strip()
            if content == "done":
                return True

        # Sleep before next iteration
        await asyncio.sleep(poll_interval)


class CaptchaHandler:
    """Manages captcha resolution flow across the pipeline."""

    def __init__(self, discord_channel_id: str = None):
        self.discord_channel_id = discord_channel_id or OSINT_CHANNEL_ID

    async def handle_intervention(self, exception, url: str) -> None:
        """Handle a HumanInterventionNeeded exception.

        Sends VNC URL to Discord and waits for user confirmation.
        """
        await send_captcha_to_discord(
            exception.vnc_url,
            url,
            exception.intervention_type,
            self.discord_channel_id,
        )

        confirmed = await wait_for_user_confirmation(self.discord_channel_id)
        if not confirmed:
            raise CaptchaTimeout(f"User did not resolve captcha for {url}")


class CaptchaTimeout(Exception):
    """Raised when user doesn't resolve captcha within timeout."""
    pass


# Module-level singleton
_default_handler = None


def get_captcha_handler(channel_id: str = None) -> CaptchaHandler:
    global _default_handler
    if _default_handler is None:
        _default_handler = CaptchaHandler(discord_channel_id=channel_id)
    return _default_handler