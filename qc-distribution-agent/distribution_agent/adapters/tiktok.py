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
from pathlib import Path

import requests

from ..config import require_env
from .base import PlatformAdapter, PostResult, VideoAsset, poll_until

API_BASE = "https://open.tiktokapis.com/v2"
SINGLE_CHUNK_MAX_BYTES = 60 * 1024 * 1024  # upload as one chunk below this size
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MiB per chunk above that


class TikTokAdapter(PlatformAdapter):
    platform_name = "tiktok"

    def __init__(self) -> None:
        self.access_token = require_env("TIKTOK_ACCESS_TOKEN")

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
