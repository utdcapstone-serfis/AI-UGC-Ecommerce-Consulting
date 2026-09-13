"""Facebook adapter (Meta Graph API — Page video upload).

Uses the same Meta Developer App as Instagram; needs a Page access
token with pages_manage_posts and pages_read_engagement scopes.

Requires FB_PAGE_ACCESS_TOKEN and FB_PAGE_ID in the environment.
"""

import requests

from ..config import require_env
from .base import PlatformAdapter, PostResult, VideoAsset

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class FacebookAdapter(PlatformAdapter):
    platform_name = "facebook"

    def __init__(self) -> None:
        self.access_token = require_env("FB_PAGE_ACCESS_TOKEN")
        self.page_id = require_env("FB_PAGE_ID")

    def upload(self, asset: VideoAsset) -> PostResult:
        data = {"description": asset.caption, "access_token": self.access_token}
        files = None

        if asset.public_url:
            data["file_url"] = asset.public_url
        elif asset.local_path:
            files = {"source": open(asset.local_path, "rb")}
        else:
            raise ValueError("Facebook upload needs asset.local_path or asset.public_url")

        try:
            resp = requests.post(f"{GRAPH_API_BASE}/{self.page_id}/videos", data=data, files=files, timeout=120)
        finally:
            if files:
                files["source"].close()

        resp.raise_for_status()
        video_id = resp.json()["id"]
        return PostResult(platform=self.platform_name, post_id=video_id, url=None)

    def verify_live(self, post_id: str) -> bool:
        resp = requests.get(
            f"{GRAPH_API_BASE}/{post_id}",
            params={"fields": "permalink_url,status", "access_token": self.access_token},
            timeout=15,
        )
        if not resp.ok:
            return False
        status = resp.json().get("status", {})
        return status.get("video_status") == "ready"
