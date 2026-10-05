"""X (Twitter) adapter — native, via X API v2.

Setup required before this works (see SETUP.md):
  1. Create a confidential ("Web App, Automated App or Bot") client at
     https://developer.x.com — this needs a funded credit balance
     (pay-per-usage, no subscription; see CURRENT_OBSTACLES.md for the
     full pricing breakdown and the native-vs-UploadPost comparison
     that led here).
  2. Run get_x_token.py yourself to get a refresh token via OAuth 2.0
     Authorization Code + PKCE (scopes: tweet.write, media.write,
     offline.access).
  3. Fill in X_CLIENT_ID, X_CLIENT_SECRET, X_REFRESH_TOKEN.

Endpoint/field names confirmed against X's current docs (docs.x.com)
before writing this, not guessed — same discipline as Threads, after
Bluesky's guessed field names turned out wrong twice in a row.

Refresh token rotation: X's docs don't explicitly say whether a
refresh_token is single-use (rotating) or reusable. Handled
defensively either way — if a refresh response includes a new
refresh_token, it's written back into .env automatically via
python-dotenv's set_key(), so a rotating token doesn't silently break
the next run. If X's tokens turn out not to rotate, this is a no-op.
"""

import base64
import os
from pathlib import Path

import requests
from dotenv import set_key

from ..config import require_env
from .base import PlatformAdapter, PostResult, VideoAsset, poll_until

API_BASE = "https://api.x.com/2"
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MiB
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class XAdapter(PlatformAdapter):
    platform_name = "x"

    def __init__(self) -> None:
        self.client_id = require_env("X_CLIENT_ID")
        self.client_secret = require_env("X_CLIENT_SECRET")
        self.refresh_token = require_env("X_REFRESH_TOKEN")

    def _basic_auth_header(self) -> dict:
        token = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    def _get_access_token(self) -> str:
        resp = requests.post(
            f"{API_BASE}/oauth2/token",
            headers={**self._basic_auth_header(), "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "refresh_token", "refresh_token": self.refresh_token, "client_id": self.client_id},
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()

        new_refresh = body.get("refresh_token")
        if new_refresh and new_refresh != self.refresh_token:
            self.refresh_token = new_refresh
            if ENV_PATH.exists():
                set_key(str(ENV_PATH), "X_REFRESH_TOKEN", new_refresh)
                os.environ["X_REFRESH_TOKEN"] = new_refresh

        return body["access_token"]

    def upload(self, asset: VideoAsset) -> PostResult:
        if not asset.local_path:
            raise ValueError("X upload requires a local file path (asset.local_path)")

        access_token = self._get_access_token()
        media_id = self._upload_video(asset.local_path, access_token)

        resp = requests.post(
            f"{API_BASE}/tweets",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"text": asset.caption or "", "media": {"media_ids": [media_id]}},
            timeout=30,
        )
        resp.raise_for_status()
        post_id = resp.json()["data"]["id"]

        return PostResult(platform=self.platform_name, post_id=post_id, url=f"https://x.com/i/web/status/{post_id}")

    def _upload_video(self, local_path: Path, access_token: str) -> str:
        video_bytes = Path(local_path).read_bytes()
        auth_header = {"Authorization": f"Bearer {access_token}"}

        init_resp = requests.post(
            f"{API_BASE}/media/upload/initialize",
            headers={**auth_header, "Content-Type": "application/json"},
            json={"media_type": "video/mp4", "media_category": "tweet_video", "total_bytes": len(video_bytes)},
            timeout=15,
        )
        init_resp.raise_for_status()
        media_id = init_resp.json()["data"]["id"]

        for i, offset in enumerate(range(0, len(video_bytes), CHUNK_SIZE)):
            chunk = video_bytes[offset : offset + CHUNK_SIZE]
            append_resp = requests.post(
                f"{API_BASE}/media/upload/{media_id}/append",
                headers=auth_header,
                data={"segment_index": str(i)},
                files={"media": ("chunk", chunk, "application/octet-stream")},
                timeout=60,
            )
            append_resp.raise_for_status()

        finalize_resp = requests.post(
            f"{API_BASE}/media/upload/{media_id}/finalize",
            headers=auth_header,
            timeout=30,
        )
        finalize_resp.raise_for_status()
        finalize_body = finalize_resp.json()["data"]

        if "processing_info" in finalize_body:
            self._wait_for_processing(media_id, access_token)

        return media_id

    def _wait_for_processing(self, media_id: str, access_token: str) -> None:
        def check() -> bool:
            status = self._media_status(media_id, access_token)
            if status["state"] == "failed":
                raise RuntimeError(f"X media {media_id} failed processing: {status}")
            return status["state"] == "succeeded"

        ready = poll_until(check, timeout_s=300, interval_s=5)
        if not ready:
            status = self._media_status(media_id, access_token)
            raise RuntimeError(f"X media {media_id} did not finish processing in time (last status: {status})")

    def _media_status(self, media_id: str, access_token: str) -> dict:
        resp = requests.get(
            f"{API_BASE}/media/upload",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"media_id": media_id, "command": "STATUS"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["data"].get("processing_info", {"state": "succeeded"})

    def verify_live(self, post_id: str) -> bool:
        access_token = self._get_access_token()
        resp = requests.get(
            f"{API_BASE}/tweets/{post_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        return resp.ok and "data" in resp.json()
