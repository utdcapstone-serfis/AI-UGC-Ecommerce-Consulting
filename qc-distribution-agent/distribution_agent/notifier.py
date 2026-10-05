"""Sends the "your video is live" confirmation email to a client POC.

Requires SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
SMTP_FROM_ADDRESS in the environment.
"""

import smtplib
from email.message import EmailMessage

from .config import require_env


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
