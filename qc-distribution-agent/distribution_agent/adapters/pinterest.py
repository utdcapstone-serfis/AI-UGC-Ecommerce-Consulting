"""Pinterest adapter (Pinterest API v5).

Setup required before this works (see SETUP.md):
  1. Create a Pinterest Developer app at https://developers.pinterest.com.
  2. Run the OAuth flow yourself, granting pins:write and boards:read,
     to get an access token.
  3. Find the target board's id (GET /v5/boards, or from the board's URL).

Requires PINTEREST_ACCESS_TOKEN and PINTEREST_BOARD_ID in the environment.

Sandbox mode (for apps that only have Trial access, where the real API refuses to
create Pins with HTTP 403): pass sandbox=True, or set PINTEREST_SANDBOX=true. The
adapter then talks to api-sandbox.pinterest.com and needs PINTEREST_SANDBOX_ACCESS_TOKEN
(from `get_pinterest_token.py --sandbox`) and PINTEREST_SANDBOX_BOARD_ID. Sandbox tokens,
boards and Pins are separate from production ones and visible only to your own account,
so nothing posted in Sandbox is public. Checked on 2026-10-23: a video Pin was created.

A video Pin needs a cover image. Rather than requiring the caller to
host one separately, this adapter grabs the video's own first frame
with OpenCV and sends it inline as base64 — no extra public URL needed.
"""

import base64
import os
from pathlib import Path

import cv2
import requests

from ..config import require_env
from .base import PlatformAdapter, PostResult, VideoAsset, poll_until

API_BASE = "https://api.pinterest.com/v5"
SANDBOX_API_BASE = "https://api-sandbox.pinterest.com/v5"


class PinterestAdapter(PlatformAdapter):
    platform_name = "pinterest"

    def __init__(self, sandbox: bool | None = None) -> None:
        if sandbox is None:
            sandbox = os.environ.get("PINTEREST_SANDBOX", "").strip().lower() in ("1", "true", "yes")
        self.sandbox = sandbox
        self.api_base = SANDBOX_API_BASE if sandbox else API_BASE
        if sandbox:
            self.access_token = require_env("PINTEREST_SANDBOX_ACCESS_TOKEN")
            self.board_id = require_env("PINTEREST_SANDBOX_BOARD_ID")
        else:
            self.access_token = require_env("PINTEREST_ACCESS_TOKEN")
            self.board_id = require_env("PINTEREST_BOARD_ID")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    def upload(self, asset: VideoAsset) -> PostResult:
        if not asset.local_path:
            raise ValueError("Pinterest upload requires a local file path (asset.local_path)")

        media_id = self._upload_video(asset.local_path)
        cover_b64 = self._first_frame_base64(asset.local_path)

        resp = requests.post(
            f"{self.api_base}/pins",
            headers=self._headers(),
            json={
                "board_id": self.board_id,
                "title": (asset.caption or "")[:100],
                "description": asset.caption or "",
                "media_source": {
                    "source_type": "video_id",
                    "media_id": media_id,
                    "cover_image_content_type": "image/jpeg",
                    "cover_image_data": cover_b64,
                },
            },
            timeout=30,
        )
        resp.raise_for_status()
        pin_id = resp.json()["id"]
        # A Sandbox Pin is visible only to its creator, so it gets no public link.
        url = None if self.sandbox else f"https://www.pinterest.com/pin/{pin_id}/"
        return PostResult(platform=self.platform_name, post_id=pin_id, url=url)

    def _upload_video(self, local_path: Path) -> str:
        register = requests.post(
            f"{self.api_base}/media",
            headers=self._headers(),
            json={"media_type": "video"},
            timeout=15,
        )
        register.raise_for_status()
        body = register.json()
        media_id = body["media_id"]

        with open(local_path, "rb") as f:
            upload_resp = requests.post(
                body["upload_url"],
                data=body["upload_parameters"],
                files={"file": f},
                timeout=180,
            )
        upload_resp.raise_for_status()

        ready = poll_until(lambda: self._media_status(media_id) == "succeeded", timeout_s=120, interval_s=5)
        if not ready:
            status = self._media_status(media_id)
            raise RuntimeError(f"Pinterest media {media_id} did not finish processing (last status: {status})")

        return media_id

    def _media_status(self, media_id: str) -> str:
        resp = requests.get(f"{self.api_base}/media/{media_id}", headers=self._headers(), timeout=15)
        resp.raise_for_status()
        status = resp.json().get("status", "")
        if status == "failed":
            raise RuntimeError(f"Pinterest media {media_id} failed processing")
        return status

    def _first_frame_base64(self, local_path: Path) -> str:
        cap = cv2.VideoCapture(str(local_path))
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            raise RuntimeError(f"Could not read a cover frame from: {local_path}")
        success, buf = cv2.imencode(".jpg", frame)
        if not success:
            raise RuntimeError("Could not encode cover frame as JPEG")
        return base64.b64encode(buf.tobytes()).decode("ascii")

    def verify_live(self, post_id: str) -> bool:
        resp = requests.get(f"{self.api_base}/pins/{post_id}", headers=self._headers(), timeout=15)
        return resp.ok and "id" in resp.json()
