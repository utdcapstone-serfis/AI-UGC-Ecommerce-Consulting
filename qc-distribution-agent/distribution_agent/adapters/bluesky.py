"""Bluesky adapter (AT Protocol).

Setup required before this works (see SETUP.md):
  1. In the Bluesky app: Settings > App Passwords > create one. This is
     not your account password — it's scoped and revocable on its own.
  2. Confirm the account's email address (Settings > Email). Video
     upload specifically requires this — an unconfirmed email fails
     with a 401 "unconfirmed_email" from the video service, discovered
     by actually running this against a real account, not documented
     anywhere obvious up front.
  3. No developer app registration, no review process beyond that,
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
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

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
        self.access_jwt, self.did, self.pds_did = self._create_session()

    def _create_session(self) -> tuple[str, str, str]:
        resp = requests.post(
            f"{self.service}/xrpc/com.atproto.server.createSession",
            json={"identifier": self.identifier, "password": self.app_password},
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()
        return body["accessJwt"], body["did"], self._pds_did_from(body)

    @staticmethod
    def _pds_did_from(session_body: dict) -> str:
        """The account's home Personal Data Server, as its own did:web —
        NOT a fixed value: AT Protocol is federated, so different
        accounts live on different PDS hosts (this account's is
        *.host.bsky.network, not bsky.social itself, even though that's
        where we authenticated). service-auth tokens for the video
        service must be scoped to this exact DID as their audience, or
        the video service rejects them with a 401 naming the DID it
        expected — that's how this was discovered and fixed.
        """
        services = session_body.get("didDoc", {}).get("service", [])
        pds = next((s for s in services if s.get("id") == "#atproto_pds"), None)
        if not pds:
            raise RuntimeError("createSession response had no #atproto_pds service entry to derive the PDS DID from")
        host = urlparse(pds["serviceEndpoint"]).hostname
        return f"did:web:{host}"

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
        # The scope must be "com.atproto.repo.uploadBlob" — the service
        # rejects a token scoped for the (more obviously-named)
        # "app.bsky.video.uploadVideo" with a 401 naming this method
        # instead; found by reading the actual rejection body, not docs.
        service_token = self._get_service_auth("com.atproto.repo.uploadBlob")

        with open(local_path, "rb") as f:
            video_bytes = f.read()

        resp = requests.post(
            f"{VIDEO_SERVICE}/xrpc/app.bsky.video.uploadVideo",
            params={"did": self.did, "name": Path(local_path).name},
            headers={**self._auth_header(service_token), "Content-Type": "video/mp4"},
            data=video_bytes,
            timeout=120,
        )
        # Unlike getJobStatus below, this response is FLAT (jobId at the
        # top level, not nested under "jobStatus") — confirmed by reading
        # the real response, not assumed from docs. Bluesky also dedupes
        # by video content hash: re-uploading identical bytes returns
        # 409 "already_exists" with a still-usable jobId rather than a
        # real error, so that's treated as success too.
        body = resp.json() if resp.content else {}
        if resp.status_code == 409 and body.get("error") == "already_exists" and body.get("jobId"):
            job_id = body["jobId"]
        else:
            resp.raise_for_status()
            job_id = body["jobId"]

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
            params={"aud": self.pds_did, "lxm": lxm},
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
