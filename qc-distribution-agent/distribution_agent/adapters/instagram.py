"""Instagram adapter (Instagram API with Instagram Login — Content Publishing).

Setup required before this works (see SETUP.md):
  1. Convert the target account to a Business or Creator account.
  2. Link it to a Facebook Page.
  3. Create a Meta Developer App, add the Instagram API use case, and
     complete "API setup with Instagram login" (not the older
     Facebook-Login-linked flow).
  4. Generate an access token via that Instagram login consent screen,
     granting instagram_business_basic and
     instagram_business_content_publish.

Requires IG_ACCESS_TOKEN and IG_BUSINESS_ACCOUNT_ID in the environment.
Uses graph.instagram.com, not graph.facebook.com — tokens from Instagram
Login are only valid against that host, confirmed by testing against a
live account (2026-09-28).
"""

import os
import warnings
from datetime import date
from pathlib import Path

import requests

from ..config import persist_env_value, require_env
from .base import PlatformAdapter, PostResult, VideoAsset, poll_until

GRAPH_API_BASE = "https://graph.instagram.com/v22.0"
REFRESH_URL = "https://graph.instagram.com/refresh_access_token"
REFRESH_AFTER_DAYS = 30  # long-lived tokens last 60 days; refresh well before that
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class InstagramAdapter(PlatformAdapter):
    platform_name = "instagram"

    def __init__(self, auto_refresh: bool = True) -> None:
        self.access_token = require_env("IG_ACCESS_TOKEN")
        self.ig_user_id = require_env("IG_BUSINESS_ACCOUNT_ID")
        if auto_refresh:
            self.refresh_credentials()

    def _refresh_due(self) -> bool:
        last = os.environ.get("IG_TOKEN_REFRESHED_AT")
        if not last:
            return True  # age unknown: try; a too-young token just fails harmlessly
        try:
            return (date.today() - date.fromisoformat(last)).days >= REFRESH_AFTER_DAYS
        except ValueError:
            return True

    def refresh_credentials(self, force: bool = False) -> bool:
        """Renews the long-lived token for another 60 days (Instagram's
        refresh_access_token endpoint, confirmed against Meta's docs). The
        token must be at least 24 hours old and not yet expired; one that has
        already expired cannot be refreshed and needs a new sign-in.

        The refresh date is kept in IG_TOKEN_REFRESHED_AT, so by default this
        only refreshes when REFRESH_AFTER_DAYS have passed. Returns True if it
        refreshed. Never raises on a failed refresh: it warns and keeps the
        existing token. A refresh only happens when this adapter is created or
        refresh_tokens.py is run, so run that script at least every 60 days.
        """
        if not force and not self._refresh_due():
            return False

        try:
            resp = requests.get(
                REFRESH_URL,
                params={"grant_type": "ig_refresh_token", "access_token": self.access_token},
                timeout=15,
            )
            body = resp.json()
        except Exception as exc:  # type only: messages can contain the request URL
            warnings.warn(
                f"Instagram token refresh could not be completed ({type(exc).__name__}); "
                "keeping the existing token.",
                RuntimeWarning,
                stacklevel=2,
            )
            return False

        if resp.status_code != 200 or "access_token" not in body:
            err = body.get("error") if isinstance(body, dict) else None
            code = err.get("code", resp.status_code) if isinstance(err, dict) else resp.status_code
            warnings.warn(
                f"Instagram token refresh failed (error {code}); keeping the existing token. "
                "A token under 24 hours old cannot be refreshed yet; one that has expired "
                "needs a new sign-in (see SETUP.md).",
                RuntimeWarning,
                stacklevel=2,
            )
            return False

        new_token = body["access_token"]
        if new_token != self.access_token:
            self.access_token = new_token
            persist_env_value("IG_ACCESS_TOKEN", new_token, ENV_PATH)
        persist_env_value("IG_TOKEN_REFRESHED_AT", date.today().isoformat(), ENV_PATH, critical=False)
        return True

    def upload(self, asset: VideoAsset) -> PostResult:
        if not asset.public_url:
            raise ValueError(
                "Instagram requires a publicly reachable video URL (asset.public_url) "
                "— Graph API cannot accept a local file directly."
            )

        container = requests.post(
            f"{GRAPH_API_BASE}/{self.ig_user_id}/media",
            data={
                "media_type": "REELS",
                "video_url": asset.public_url,
                "caption": asset.caption,
                "access_token": self.access_token,
            },
            timeout=30,
        )
        container.raise_for_status()
        creation_id = container.json()["id"]

        ready = poll_until(lambda: self._container_status(creation_id) == "FINISHED", timeout_s=120, interval_s=5)
        if not ready:
            status = self._container_status(creation_id)
            raise RuntimeError(f"Instagram container {creation_id} did not finish processing (last status: {status})")

        publish = requests.post(
            f"{GRAPH_API_BASE}/{self.ig_user_id}/media_publish",
            data={"creation_id": creation_id, "access_token": self.access_token},
            timeout=30,
        )
        publish.raise_for_status()
        media_id = publish.json()["id"]

        return PostResult(platform=self.platform_name, post_id=media_id, url=None)

    def _container_status(self, creation_id: str) -> str:
        resp = requests.get(
            f"{GRAPH_API_BASE}/{creation_id}",
            params={"fields": "status_code", "access_token": self.access_token},
            timeout=15,
        )
        resp.raise_for_status()
        status = resp.json().get("status_code", "")
        if status == "ERROR":
            raise RuntimeError(f"Instagram container {creation_id} failed processing")
        return status

    def verify_live(self, post_id: str) -> bool:
        resp = requests.get(
            f"{GRAPH_API_BASE}/{post_id}",
            params={"fields": "permalink", "access_token": self.access_token},
            timeout=15,
        )
        return resp.ok and "permalink" in resp.json()
