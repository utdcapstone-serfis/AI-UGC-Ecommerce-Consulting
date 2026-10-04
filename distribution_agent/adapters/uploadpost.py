"""UploadPost.com-backed adapter — fallback for LinkedIn and TikTok.

Superseded 2026-10-01 by native adapters (`linkedin.py`, `tiktok.py`) —
see CURRENT_OBSTACLES.md for why native was pursued instead. This class
is kept as a fallback path (not registered in ADAPTERS by default): if
either native integration proves blocked long-term, instantiate
`UploadPostAdapter("linkedin")` or `UploadPostAdapter("tiktok")`
directly rather than resurrecting the thin per-platform subclasses that
used to live here.

Endpoint and field names are per https://docs.upload-post.com (checked
Sep 2026) — unverified against a live account/API key in this codebase.
Confirm against current docs before relying on this in production, the
same caveat already flagged on the Reddit adapter for its own API.

Requires UPLOADPOST_API_KEY and UPLOADPOST_USER in the environment.

Note: UploadPost's docs don't show a get-post/status endpoint, so
verify_live() here can only trust upload()'s own success response —
a real, weaker guarantee than the native adapters, which always
re-fetch the post from the platform's own API directly.
"""

import requests

from ..config import require_env
from .base import PlatformAdapter, PostResult, VideoAsset

API_URL = "https://api.upload-post.com/api/uploadposts/api/upload"


class UploadPostAdapter(PlatformAdapter):
    def __init__(self, platform_name: str) -> None:
        self.platform_name = platform_name
        self.api_key = require_env("UPLOADPOST_API_KEY")
        self.user = require_env("UPLOADPOST_USER")

    def upload(self, asset: VideoAsset) -> PostResult:
        if not asset.local_path:
            raise ValueError(f"{self.platform_name} (via UploadPost) requires a local file path (asset.local_path)")

        caption_field = "text" if self.platform_name == "linkedin" else "caption"

        with open(asset.local_path, "rb") as f:
            resp = requests.post(
                API_URL,
                headers={"Authorization": f"Apikey {self.api_key}"},
                data={"platform": self.platform_name, "user": self.user, caption_field: asset.caption or ""},
                files={"file": f},
                timeout=180,
            )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise RuntimeError(f"UploadPost {self.platform_name} post failed: {body}")

        return PostResult(platform=self.platform_name, post_id=body["post_id"], url=body.get("url"))

    def verify_live(self, post_id: str) -> bool:
        return bool(post_id)
