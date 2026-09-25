"""Threads adapter (Meta Threads API — separate from the Instagram
Graph API, though tied to the same Instagram professional account).

Setup required before this works (see SETUP.md):
  1. In the same Meta Developer App used for Facebook/Instagram, add
     the Threads API product.
  2. Run the OAuth flow yourself, granting threads_basic and
     threads_content_publish, to get an access token scoped to Threads.
  3. Fill in THREADS_ACCESS_TOKEN and THREADS_USER_ID (the Threads
     user id, not the Instagram Business Account id — a separate id
     even though the underlying account is the same).

Requires THREADS_ACCESS_TOKEN and THREADS_USER_ID in the environment.

Endpoint/field names confirmed against Meta's current Threads API docs
(developers.facebook.com/docs/threads) before writing this — not
guessed — but not yet exercised against a live account in this
codebase. Container status values per Meta's docs: IN_PROGRESS, ERROR,
FINISHED, PUBLISHED, EXPIRED (a container expires if not published
within 24h of creation). Meta recommends polling status once per
minute for up to 5 minutes rather than more aggressively.
"""

import requests

from ..config import require_env
from .base import PlatformAdapter, PostResult, VideoAsset, poll_until

GRAPH_API_BASE = "https://graph.threads.net/v1.0"


class ThreadsAdapter(PlatformAdapter):
    platform_name = "threads"

    def __init__(self) -> None:
        self.access_token = require_env("THREADS_ACCESS_TOKEN")
        self.user_id = require_env("THREADS_USER_ID")

    def upload(self, asset: VideoAsset) -> PostResult:
        if not asset.public_url:
            raise ValueError(
                "Threads requires a publicly reachable video URL (asset.public_url) "
                "— the API fetches the video from that URL itself, same as Instagram."
            )

        container = requests.post(
            f"{GRAPH_API_BASE}/{self.user_id}/threads",
            data={
                "media_type": "VIDEO",
                "video_url": asset.public_url,
                "text": asset.caption or "",
                "access_token": self.access_token,
            },
            timeout=30,
        )
        container.raise_for_status()
        creation_id = container.json()["id"]

        ready = poll_until(
            lambda: self._container_status(creation_id) == "FINISHED",
            timeout_s=300,
            interval_s=60,
        )
        if not ready:
            status = self._container_status(creation_id)
            raise RuntimeError(f"Threads container {creation_id} did not finish processing (last status: {status})")

        publish = requests.post(
            f"{GRAPH_API_BASE}/{self.user_id}/threads_publish",
            data={"creation_id": creation_id, "access_token": self.access_token},
            timeout=30,
        )
        publish.raise_for_status()
        media_id = publish.json()["id"]

        return PostResult(platform=self.platform_name, post_id=media_id, url=None)

    def _container_status(self, creation_id: str) -> str:
        resp = requests.get(
            f"{GRAPH_API_BASE}/{creation_id}",
            params={"fields": "status,error_message", "access_token": self.access_token},
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()
        status = body.get("status", "")
        if status == "ERROR":
            raise RuntimeError(f"Threads container {creation_id} failed processing: {body.get('error_message', 'unknown error')}")
        if status == "EXPIRED":
            raise RuntimeError(f"Threads container {creation_id} expired before it was published (24h limit)")
        return status

    def verify_live(self, post_id: str) -> bool:
        resp = requests.get(
            f"{GRAPH_API_BASE}/{post_id}",
            params={"fields": "permalink", "access_token": self.access_token},
            timeout=15,
        )
        return resp.ok and "permalink" in resp.json()
