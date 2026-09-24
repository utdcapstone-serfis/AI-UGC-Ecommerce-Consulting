"""Bluesky adapter (AT Protocol).

Setup required before this works (see SETUP.md):
  1. In the Bluesky app: Settings > App Passwords > create one. This is
     not your account password — it's scoped and revocable on its own.
  2. That's it. No developer app registration, no review process,
     unlike every other adapter in this package.

Requires BLUESKY_IDENTIFIER (handle or email) and BLUESKY_APP_PASSWORD
in the environment. BLUESKY_SERVICE is optional (defaults to the
public bsky.social PDS; override it if posting through a self-hosted
Personal Data Server).

Video posting on AT Protocol needs a separate processing step (the
video service transcodes it before it can be attached to a post), so
upload() is a three-step flow: get a scoped service-auth token, upload
the raw video and poll until processing finishes, then create the post
referencing the resulting blob.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from ..config import require_env
from .base import PlatformAdapter, PostResult, VideoAsset, poll_until

DEFAULT_SERVICE = "https://bsky.social"
VIDEO_SERVICE = "https://video.bsky.app"


class BlueskyAdapter(PlatformAdapter):
    platform_name = "bluesky"

    def __init__(self) -> None:
        self.identifier = require_env("BLUESKY_IDENTIFIER")
        self.app_password = require_env("BLUESKY_APP_PASSWORD")
        self.service = os.environ.get("BLUESKY_SERVICE", DEFAULT_SERVICE)
        self.access_jwt, self.did = self._create_session()

    def _create_session(self) -> tuple[str, str]:
        resp = requests.post(
            f"{self.service}/xrpc/com.atproto.server.createSession",
            json={"identifier": self.identifier, "password": self.app_password},
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()
        return body["accessJwt"], body["did"]

    def _auth_header(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def upload(self, asset: VideoAsset) -> PostResult:
        if not asset.local_path:
            raise ValueError("Bluesky upload requires a local file path (asset.local_path)")

        blob = self._upload_video(asset.local_path)

        record = {
            "$type": "app.bsky.feed.post",
            "text": asset.caption or "",
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "embed": {"$type": "app.bsky.embed.video", "video": blob, "alt": ""},
        }
        resp = requests.post(
            f"{self.service}/xrpc/com.atproto.repo.createRecord",
            headers=self._auth_header(self.access_jwt),
            json={"repo": self.did, "collection": "app.bsky.feed.post", "record": record},
            timeout=30,
        )
        resp.raise_for_status()
        uri = resp.json()["uri"]  # at://<did>/app.bsky.feed.post/<rkey>
        rkey = uri.rsplit("/", 1)[-1]
        url = f"https://bsky.app/profile/{self.did}/post/{rkey}"
        return PostResult(platform=self.platform_name, post_id=uri, url=url)

    def _upload_video(self, local_path: Path) -> dict:
        # The video service is a separate host, so it needs its own
        # short-lived, method-scoped auth token rather than access_jwt.
        service_token = self._get_service_auth("app.bsky.video.uploadVideo")

        with open(local_path, "rb") as f:
            video_bytes = f.read()

        resp = requests.post(
            f"{VIDEO_SERVICE}/xrpc/app.bsky.video.uploadVideo",
            params={"did": self.did, "name": Path(local_path).name},
            headers={**self._auth_header(service_token), "Content-Type": "video/mp4"},
            data=video_bytes,
            timeout=120,
        )
        resp.raise_for_status()
        job_id = resp.json()["jobStatus"]["jobId"]

        blob = {}

        def check_job() -> bool:
            status_resp = requests.get(
                f"{VIDEO_SERVICE}/xrpc/app.bsky.video.getJobStatus",
                params={"jobId": job_id},
                timeout=15,
            )
            status_resp.raise_for_status()
            status = status_resp.json()["jobStatus"]
            if status["state"] == "JOB_STATE_FAILED":
                raise RuntimeError(f"Bluesky video processing failed: {status.get('error', 'unknown error')}")
            if status["state"] == "JOB_STATE_COMPLETED":
                blob.update(status["blob"])
                return True
            return False

        ready = poll_until(check_job, timeout_s=180, interval_s=5)
        if not ready or not blob:
            raise TimeoutError(f"Bluesky video job {job_id} did not finish processing in time")

        return blob

    def _get_service_auth(self, lxm: str) -> str:
        resp = requests.get(
            f"{self.service}/xrpc/com.atproto.server.getServiceAuth",
            params={"aud": "did:web:video.bsky.app", "lxm": lxm},
            headers=self._auth_header(self.access_jwt),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["token"]

    def verify_live(self, post_id: str) -> bool:
        # post_id is the at:// URI: at://<did>/<collection>/<rkey>
        _, _, did, collection, rkey = post_id.split("/", 4)
        resp = requests.get(
            f"{self.service}/xrpc/com.atproto.repo.getRecord",
            params={"repo": did, "collection": collection, "rkey": rkey},
            timeout=15,
        )
        return resp.ok and "value" in resp.json()
