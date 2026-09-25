"""UploadPost.com-backed adapter — shared by LinkedIn and TikTok.

Both platforms are gated behind an approval process we can't clear
ourselves in reasonable time: LinkedIn requires applying for their
Marketing/Community Management partner API, and TikTok requires a
formal Content Posting API audit. UploadPost already holds an approved
app for both — connecting an account is "click Connect, approve" in
their dashboard (see SETUP.md), no app review of our own required.

One shared implementation serves both platforms, since UploadPost
exposes the identical endpoint and multipart shape for each — only the
`platform` field value and a couple of platform-specific optional
fields (not set here) differ. LinkedInAdapter and TikTokAdapter below
are thin subclasses that exist only so ADAPTERS can register a
zero-argument constructor for each platform key, same as every other
adapter in this package.

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


class LinkedInAdapter(UploadPostAdapter):
    def __init__(self) -> None:
        super().__init__("linkedin")


class TikTokAdapter(UploadPostAdapter):
    def __init__(self) -> None:
        super().__init__("tiktok")
