"""TikTok adapter — native, via the Content Posting API (Direct Post).

Setup required before this works (see SETUP.md):
  1. Create an organization and app at developers.tiktok.com, add the
     Content Posting API product with Direct Post enabled, and the
     Login Kit product (a required dependency — Content Posting API's
     OAuth authorization flow runs through it even for posting to your
     own account).
  2. Submit for app review, which requires a demo video of the full
     flow working against the Sandbox environment first — see
     CURRENT_OBSTACLES.md. Until approved, this only works against
     Sandbox target accounts, not real public TikTok.
  3. Run the OAuth 2.0 flow yourself (scopes: user.info.basic,
     video.publish, video.upload) and fill in TIKTOK_CLIENT_KEY,
     TIKTOK_CLIENT_SECRET, TIKTOK_ACCESS_TOKEN.

Endpoint/field names confirmed against TikTok's current Content Posting
API docs (developers.tiktok.com/doc/content-posting-api-reference-
direct-post and .../get-video-status) before writing this, not guessed —
same discipline as Threads/X/LinkedIn, after Bluesky's guessed field
names turned out wrong twice in a row.

Privacy level defaults to SELF_ONLY — unaudited apps are restricted by
TikTok to private/self-visible posts regardless of what's requested
(confirmed in the App Review flow's own guidance), so this isn't
optional until the app is actually approved. Change the default once
that happens, not before — setting anything else against an unaudited
app risks the post being rejected outright rather than just scoped down.
"""

import math
import os
import warnings
from pathlib import Path

import requests

from ..config import persist_env_value, require_env
from .base import PlatformAdapter, PostResult, VideoAsset, poll_until

API_BASE = "https://open.tiktokapis.com/v2"
SINGLE_CHUNK_MAX_BYTES = 60 * 1024 * 1024  # upload as one chunk below this size
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MiB per chunk above that
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class TikTokAdapter(PlatformAdapter):
    platform_name = "tiktok"

    def __init__(self, auto_refresh: bool = True) -> None:
        self.access_token = require_env("TIKTOK_ACCESS_TOKEN")
        if auto_refresh:
            self.refresh_credentials()

    def refresh_credentials(self) -> bool:
        """Swaps TIKTOK_REFRESH_TOKEN for a fresh access token (TikTok access
        tokens last 24 hours; the refresh token lasts 365 days). Endpoint and
        fields confirmed against TikTok's token-management docs.

        TikTok says the returned refresh token "may be different", so a new one
        is saved (see persist_env_value). The new access token is kept in memory
        only; the TIKTOK_ACCESS_TOKEN line in .env goes stale and is not used
        while a refresh token is set. Returns True if refreshed. Never raises
        on a failed refresh: it warns and keeps the existing access token.
        """
        refresh_token = os.environ.get("TIKTOK_REFRESH_TOKEN")
        client_key = os.environ.get("TIKTOK_CLIENT_KEY")
        client_secret = os.environ.get("TIKTOK_CLIENT_SECRET")
        if not (refresh_token and client_key and client_secret):
            return False  # nothing to refresh with: use the access token as given

        try:
            resp = requests.post(
                f"{API_BASE}/oauth/token/",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": client_key,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                timeout=15,
            )
            body = resp.json()
        except Exception as exc:  # type only: messages can contain request details
            warnings.warn(
                f"TikTok token refresh could not be completed ({type(exc).__name__}); using "
                "TIKTOK_ACCESS_TOKEN from .env, which may be expired.",
                RuntimeWarning,
                stacklevel=2,
            )
            return False

        if resp.status_code != 200 or "access_token" not in body:
            warnings.warn(
                f"TikTok token refresh failed ({body.get('error', resp.status_code)}); using "
                "TIKTOK_ACCESS_TOKEN from .env, which may be expired. If the refresh token "
                "itself has expired or been revoked, re-run get_tiktok_token.py.",
                RuntimeWarning,
                stacklevel=2,
            )
            return False

        self.access_token = body["access_token"]
        new_refresh = body.get("refresh_token")
        if new_refresh and new_refresh != refresh_token:
            persist_env_value("TIKTOK_REFRESH_TOKEN", new_refresh, ENV_PATH)
        return True

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def upload(self, asset: VideoAsset) -> PostResult:
        if not asset.local_path:
            raise ValueError("TikTok upload requires a local file path (asset.local_path)")

        video_bytes = Path(asset.local_path).read_bytes()
        publish_id, upload_url = self._init_upload(video_bytes, asset.caption or "")
        self._upload_video(upload_url, video_bytes)
        self._wait_for_publish(publish_id)

        return PostResult(platform=self.platform_name, post_id=publish_id, url=None)

    def _init_upload(self, video_bytes: bytes, caption: str) -> tuple[str, str]:
        total_bytes = len(video_bytes)
        if total_bytes <= SINGLE_CHUNK_MAX_BYTES:
            chunk_size = total_bytes
            total_chunk_count = 1
        else:
            chunk_size = CHUNK_SIZE
            total_chunk_count = math.ceil(total_bytes / CHUNK_SIZE)

        resp = requests.post(
            f"{API_BASE}/post/publish/video/init/",
            headers=self._headers(),
            json={
                "post_info": {
                    "title": caption,
                    "privacy_level": "SELF_ONLY",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": total_bytes,
                    "chunk_size": chunk_size,
                    "total_chunk_count": total_chunk_count,
                },
            },
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("error", {}).get("code") not in (None, "ok"):
            raise RuntimeError(f"TikTok init upload failed: {body['error']}")

        data = body["data"]
        return data["publish_id"], data["upload_url"]

    def _upload_video(self, upload_url: str, video_bytes: bytes) -> None:
        total_bytes = len(video_bytes)
        chunk_size = total_bytes if total_bytes <= SINGLE_CHUNK_MAX_BYTES else CHUNK_SIZE

        for offset in range(0, total_bytes, chunk_size):
            chunk = video_bytes[offset : offset + chunk_size]
            last_byte = offset + len(chunk) - 1
            resp = requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{last_byte}/{total_bytes}",
                },
                data=chunk,
                timeout=120,
            )
            resp.raise_for_status()

    def _wait_for_publish(self, publish_id: str) -> None:
        def check() -> bool:
            status = self._publish_status(publish_id)
            if status.get("status") == "FAILED":
                raise RuntimeError(f"TikTok publish {publish_id} failed: {status.get('fail_reason')}")
            return status.get("status") == "PUBLISH_COMPLETE"

        ready = poll_until(check, timeout_s=180, interval_s=5)
        if not ready:
            status = self._publish_status(publish_id)
            raise RuntimeError(f"TikTok publish {publish_id} did not complete in time (last status: {status})")

    def _publish_status(self, publish_id: str) -> dict:
        resp = requests.post(
            f"{API_BASE}/post/publish/status/fetch/",
            headers=self._headers(),
            json={"publish_id": publish_id},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("data", {})

    def verify_live(self, post_id: str) -> bool:
        status = self._publish_status(post_id)
        return status.get("status") == "PUBLISH_COMPLETE"
