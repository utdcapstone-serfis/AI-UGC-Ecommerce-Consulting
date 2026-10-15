"""Sends the "your video is live" confirmation email to a client POC.

Requires SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
SMTP_FROM_ADDRESS in the environment.
"""

import mimetypes
import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional

from .config import require_env

if TYPE_CHECKING:
    from .adapters.base import VideoAsset
    from .approval import ApprovalRequest
    from .distribution_agent import DistributionRecord

MAX_ATTACHMENT_MB = 20  # most mail providers reject messages over about 25 MB

_DISPLAY_NAMES = {"youtube": "YouTube", "tiktok": "TikTok", "linkedin": "LinkedIn", "x": "X"}


def _display(platform: str) -> str:
    return _DISPLAY_NAMES.get(platform, platform.title())


def notify_poc(poc_email: str, platform: str, post_url: str) -> None:
    message = EmailMessage()
    message["Subject"] = f"Your video is live on {platform.title()}"
    message["From"] = require_env("SMTP_FROM_ADDRESS")
    message["To"] = poc_email
    message.set_content(
        f"Your video has been posted and verified live on {platform.title()}.\n\n{post_url or '(no direct link available)'}"
    )

    host = require_env("SMTP_HOST")
    port = int(require_env("SMTP_PORT"))
    username = require_env("SMTP_USERNAME")
    password = require_env("SMTP_PASSWORD")

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)


def draft_distribution_email(
    records: "Iterable[DistributionRecord]",
    asset: "VideoAsset",
    poc_email: str,
    video_title: str = "",
    qc_score: Optional[float] = None,
    attach_video: bool = True,
) -> EmailMessage:
    """Builds ONE summary email for a distribution run: the video passed QC
    and is live on these platforms, with the video attached. It only builds
    the message. Nothing is sent, and no SMTP settings are needed.

    Only platforms confirmed live (`is_live`) are listed. Raises ValueError
    if none are, or if the video is too large to attach (pass
    `attach_video=False` to leave it off and rely on the links).
    """
    live = [r for r in records if r.is_live]
    if not live:
        raise ValueError("No platform is confirmed live, so there is nothing to put in the email.")

    label = video_title or (asset.local_path.name if asset.local_path else "your video")
    names = ", ".join(_display(r.platform) for r in live)

    lines = [
        "Hi,",
        "",
        f'Your video "{label}" has been approved and is now live on: {names}.',
        "",
    ]
    if qc_score is not None:
        lines.append(f"It passed quality control with a score of {qc_score}/10.")
        lines.append("")
    lines.append("Where to watch it:")
    for record in live:
        lines.append(f"- {_display(record.platform)}: {record.url or '(no direct link available)'}")
    lines += ["", "The video is attached for your records.", "", "Thank you."]

    message = EmailMessage()
    message["Subject"] = f'Your video "{label}" is live on {names}'
    message["From"] = os.environ.get("SMTP_FROM_ADDRESS", "")
    message["To"] = poc_email
    message["X-Unsent"] = "1"  # mail apps such as Outlook open this as an unsent draft
    message.set_content("\n".join(lines))

    if attach_video:
        path = asset.local_path
        if path is None or not Path(path).is_file():
            raise ValueError("asset.local_path must point to the video file to attach it.")
        size_mb = Path(path).stat().st_size / (1024 * 1024)
        if size_mb > MAX_ATTACHMENT_MB:
            raise ValueError(
                f"{Path(path).name} is {size_mb:.0f} MB, over the {MAX_ATTACHMENT_MB} MB attachment "
                "limit. Use attach_video=False and rely on the links."
            )
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        maintype, _, subtype = mime.partition("/")
        message.add_attachment(
            Path(path).read_bytes(), maintype=maintype, subtype=subtype or "octet-stream",
            filename=Path(path).name,
        )

    return message


def save_draft(message: EmailMessage, drafts_dir: Path | str = "drafts") -> Path:
    """Writes the draft to an .eml file (open it in a mail app to review and
    send). The `drafts/` folder is gitignored because it holds the video."""
    folder = Path(drafts_dir)
    folder.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", message["Subject"].lower()).strip("-")[:60] or "draft"
    path = folder / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}.eml"
    path.write_bytes(bytes(message))
    return path


def draft_review_email(
    request: "ApprovalRequest",
    asset: "VideoAsset",
    to_email: str,
    dashboard_url: str,
    attach_video: bool = True,
) -> EmailMessage:
    """Builds the "ready for review" email sent after a video passes QC: what
    passed, where it would be posted, the video, and a link to the dashboard
    where someone with edit access approves or denies. It only builds the
    message; sending is `send_message()`, which asks first. The email itself
    approves nothing: replying to it or forwarding it has no effect.
    """
    if not to_email or "@" not in to_email:
        raise ValueError("to_email must be an email address.")
    if not str(dashboard_url).startswith("https://"):
        raise ValueError("dashboard_url must be the dashboard's https:// link.")

    platforms = ", ".join(_display(p) for p in request.platforms)
    score = f" with a score of {request.qc_score}/10" if request.qc_score is not None else ""
    lines = [
        "Hi,",
        "",
        f'"{request.title}" passed quality control{score} and is ready to post.',
        "",
        f"It would be posted to: {platforms}.",
        "",
        "Nothing is posted until someone with edit access approves it on the dashboard. "
        "Open it to choose the platforms and approve, or deny:",
        dashboard_url,
        "",
        f"Request: REQ-{request.request_id}. It expires after 24 hours.",
        "Replying to this email does not approve anything.",
    ]
    if attach_video:
        lines += ["", "The video is attached for your review."]

    message = EmailMessage()
    message["Subject"] = f'Review needed: "{request.title}" is ready to post'
    message["From"] = os.environ.get("SMTP_FROM_ADDRESS", "")
    message["To"] = to_email
    message.set_content(chr(10).join(lines))

    if attach_video:
        path = asset.local_path
        if path is None or not Path(path).is_file():
            raise ValueError("asset.local_path must point to the video file to attach it.")
        size_mb = Path(path).stat().st_size / (1024 * 1024)
        if size_mb > MAX_ATTACHMENT_MB:
            raise ValueError(
                f"{Path(path).name} is {size_mb:.0f} MB, over the {MAX_ATTACHMENT_MB} MB attachment "
                "limit. Use attach_video=False; the dashboard link is enough."
            )
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        maintype, _, subtype = mime.partition("/")
        message.add_attachment(
            Path(path).read_bytes(), maintype=maintype, subtype=subtype or "octet-stream", filename=Path(path).name
        )
    return message


def cli_send_confirmation(message: EmailMessage) -> bool:
    """Default confirmation before an email goes out: asks on the terminal and
    refuses (False) without a terminal or on EOF, never assuming consent."""
    import sys

    if not sys.stdin.isatty():
        return False
    try:
        return input(f'Send "{message["Subject"]}" to {message["To"]}? [y/N] ').strip().lower() in ("y", "yes")
    except EOFError:
        return False


def send_message(message: EmailMessage, confirm=cli_send_confirmation) -> bool:
    """Sends a built message over SMTP (SMTP_HOST, SMTP_PORT, SMTP_USERNAME,
    SMTP_PASSWORD, SMTP_FROM_ADDRESS from .env) only if `confirm(message)`
    returns True. Returns False, and touches neither credentials nor network,
    if it declines. The agent passes its own `confirm` only after the user has
    said yes in chat to that exact email. Raises ConfigError if a setting is
    missing, before any connection is made.
    """
    if not confirm(message):
        return False
    from_address = require_env("SMTP_FROM_ADDRESS")
    host = require_env("SMTP_HOST")
    port = int(require_env("SMTP_PORT"))
    username = require_env("SMTP_USERNAME")
    password = require_env("SMTP_PASSWORD")
    if not message["From"]:
        message["From"] = from_address
    if "X-Unsent" in message:
        del message["X-Unsent"]
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)
    return True
