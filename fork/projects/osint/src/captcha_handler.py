"""Human intervention handler for the OSINT pipeline.

When a scraper hits a captcha or login wall, this module delivers the VNC
link to the project channel and raises HumanInterventionPending. It never
waits for the answer: the pipeline runs inside the agent's own turn, so a
human reply cannot reach this process until the turn ends. The agent owns
the wait (its `clarify` tool) and re-invokes `main.py --resume <token>`.
"""

import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import agent_bridge  # noqa: E402
from src.paths import SETTINGS_FILE  # noqa: E402

DEFAULT_PLATFORM = "discord"


class HumanInterventionPending(Exception):
    """Raised after the intervention prompt is delivered and a human is needed.

    Carries everything the caller must persist and print so the agent can
    resume the run once the captcha is solved.
    """

    def __init__(
        self,
        resume_token: str,
        vnc_url: str,
        url: str,
        intervention_type: str = "captcha",
        message: str = "",
        delivery_error: str = None,
    ):
        self.resume_token = resume_token
        self.vnc_url = vnc_url
        self.url = url
        self.intervention_type = intervention_type
        self.message = message
        self.delivery_error = delivery_error
        super().__init__(
            f"Human intervention required ({intervention_type}) for {url}; "
            f"resume with token {resume_token}"
        )

    def to_dict(self) -> dict:
        return {
            "resume_token": self.resume_token,
            "vnc_url": self.vnc_url,
            "url": self.url,
            "intervention_type": self.intervention_type,
            "message": self.message,
            "prompt_delivered": self.delivery_error is None,
            "delivery_error": self.delivery_error,
        }


def load_channel_id(settings_file: Path | None = None) -> str:
    """Read the project channel id from config/settings.json.

    Raises:
        FileNotFoundError: when the settings file is missing.
        KeyError: when discord.channel_id is not configured.
    """
    path = Path(settings_file) if settings_file else SETTINGS_FILE
    settings = json.loads(path.read_text(encoding="utf-8"))
    channel_id = settings.get("discord", {}).get("channel_id")
    if not channel_id:
        raise KeyError(f"discord.channel_id is not set in {path}")
    return str(channel_id)


def build_captcha_message(vnc_url: str, url: str, intervention_type: str, resume_token: str) -> str:
    return (
        f"Captcha required to continue the OSINT scan.\n\n"
        f"URL: {url}\n"
        f"Type: {intervention_type}\n\n"
        f"Solve it here: {vnc_url}\n\n"
        f"When it is solved, resume with: --resume {resume_token}"
    )


def send_captcha_prompt(
    vnc_url: str,
    url: str,
    intervention_type: str,
    resume_token: str,
    channel_id: str = None,
) -> None:
    """Deliver the captcha prompt to the project channel.

    Raises:
        agent_bridge.AgentBridgeError: when the prompt could not be delivered.
    """
    channel = channel_id or load_channel_id()
    agent_bridge.send_message(
        build_captcha_message(vnc_url, url, intervention_type, resume_token),
        platform=DEFAULT_PLATFORM,
        conversation=channel,
    )


class CaptchaHandler:
    """Turns a scraper's intervention request into a delivered prompt plus a resume token."""

    def __init__(self, discord_channel_id: str = None):
        # Resolved at delivery time, so a broken settings.json is reported as a
        # delivery failure instead of crashing the pause path.
        self.discord_channel_id = discord_channel_id

    def handle_intervention(self, exception, url: str) -> None:
        """Deliver the prompt for a HumanInterventionNeeded and hand control back to the agent.

        A failed delivery does not change the outcome, the run is paused either
        way, so it is reported on the raised exception instead of replacing it.

        Raises:
            HumanInterventionPending: always.
        """
        resume_token = uuid4().hex[:12]
        delivery_error = None

        try:
            send_captcha_prompt(
                exception.vnc_url,
                url,
                exception.intervention_type,
                resume_token,
                self.discord_channel_id,
            )
        except (agent_bridge.AgentBridgeError, OSError, KeyError, ValueError) as exc:
            delivery_error = str(exc)
            print(f"[captcha_handler] prompt delivery failed: {exc}", file=sys.stderr)

        raise HumanInterventionPending(
            resume_token=resume_token,
            vnc_url=exception.vnc_url,
            url=url,
            intervention_type=exception.intervention_type,
            message=exception.message,
            delivery_error=delivery_error,
        )


# Module-level singleton
_default_handler = None


def get_captcha_handler(channel_id: str = None) -> CaptchaHandler:
    global _default_handler
    if _default_handler is None:
        _default_handler = CaptchaHandler(discord_channel_id=channel_id)
    return _default_handler
