"""Instagram adapter (Meta Graph API — Content Publishing).

Setup required before this works (see SETUP.md):
  1. Convert the target account to a Business or Creator account.
  2. Link it to a Facebook Page.
  3. Create a Meta Developer App with the Instagram Graph API product.
  4. Generate a long-lived access token with instagram_basic and
     instagram_content_publish scopes.

Requires IG_ACCESS_TOKEN and IG_BUSINESS_ACCOUNT_ID in the environment.
"""

import requests

from ..config import require_env
from .base import PlatformAdapter, PostResult, VideoAsset, poll_until

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class InstagramAdapter(PlatformAdapter):
    platform_name = "instagram"

    def __init__(self) -> None:
        self.access_token = require_env("IG_ACCESS_TOKEN")
        self.ig_user_id = require_env("IG_BUSINESS_ACCOUNT_ID")

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
