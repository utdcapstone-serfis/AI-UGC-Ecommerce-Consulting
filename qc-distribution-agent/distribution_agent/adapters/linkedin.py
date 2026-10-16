"""LinkedIn adapter — native, via the Videos API + Posts API.

Posts to a personal profile (w_member_social scope), not a Company Page —
see CURRENT_OBSTACLES.md for why: creating a Company Page requires a
LinkedIn-side connections/profile-strength threshold this account hadn't
cleared, and a LinkedIn developer app can't even be created without a
Page attached to it either way. Personal-profile posting has no such
gate.

Setup required before this works (see SETUP.md):
  1. Create a LinkedIn developer app at linkedin.com/developers/apps
     (needs a LinkedIn Page to attach to, even for member-scope posting).
  2. Request the "Share on LinkedIn" product (self-serve, no partner
     review — confirmed via developer.linkedin.com/documents/share-api).
  3. Run the OAuth 2.0 three-legged flow yourself, granting
     w_member_social (and openid/profile if you want this script to
     resolve your own person ID automatically rather than hardcoding
     it).
  4. Fill in LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET,
     LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_ID.

Endpoint/field names confirmed against LinkedIn's current Videos API and
Posts API docs (learn.microsoft.com/en-us/linkedin/marketing/community-
management/shares/{videos-api,posts-api}) before writing this, not
guessed — same discipline as Threads/X, after Bluesky's guessed field
names turned out wrong twice in a row.

Access tokens from this flow are valid ~60 days per LinkedIn's docs.
Refreshing requires LinkedIn's separate "Programmatic refresh tokens"
product (its own approval, not assumed granted here), so this adapter
doesn't attempt a refresh — a token expiring means re-running the OAuth
flow manually, same category of gap as Instagram's 60-day token.
"""

import os
import warnings
from pathlib import Path

import requests

from ..config import require_env
from .base import PlatformAdapter, PostResult, VideoAsset, poll_until

API_BASE = "https://api.linkedin.com/rest"
LINKEDIN_VERSION = "202609"
CHUNK_SIZE = 4 * 1024 * 1024 - 1  # LinkedIn's own "split -b 4194303" sizing


class LinkedInAdapter(PlatformAdapter):
    platform_name = "linkedin"

    def __init__(self) -> None:
        self.access_token = require_env("LINKEDIN_ACCESS_TOKEN")
        self.person_id = require_env("LINKEDIN_PERSON_ID")
        self.author_urn = f"urn:li:person:{self.person_id}"
        self._created_post_ids: set[str] = set()

    def _headers(self, content_type: str = "application/json") -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Linkedin-Version": LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": content_type,
        }

    def upload(self, asset: VideoAsset) -> PostResult:
        if not asset.local_path:
            raise ValueError("LinkedIn upload requires a local file path (asset.local_path)")

        video_bytes = Path(asset.local_path).read_bytes()
        video_urn = self._upload_video(video_bytes)

        post_resp = requests.post(
            f"{API_BASE}/posts",
            headers=self._headers(),
            json={
                "author": self.author_urn,
                "commentary": asset.caption or "",
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "content": {"media": {"id": video_urn}},
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            },
            timeout=30,
        )
        post_resp.raise_for_status()
        post_id = post_resp.headers["x-restli-id"]
        self._created_post_ids.add(post_id)

        return PostResult(
            platform=self.platform_name,
            post_id=post_id,
            url=f"https://www.linkedin.com/feed/update/{post_id}/",
        )

    def _upload_video(self, video_bytes: bytes) -> str:
        init_resp = requests.post(
            f"{API_BASE}/videos?action=initializeUpload",
            headers=self._headers(),
            json={
                "initializeUploadRequest": {
                    "owner": self.author_urn,
                    "fileSizeBytes": len(video_bytes),
                    "uploadCaptions": False,
                    "uploadThumbnail": False,
                }
            },
            timeout=30,
        )
        init_resp.raise_for_status()
        init_body = init_resp.json()["value"]
        video_urn = init_body["video"]
        upload_instructions = init_body["uploadInstructions"]
        upload_token = init_body.get("uploadToken", "")

        uploaded_part_ids = []
        for part in upload_instructions:
            chunk = video_bytes[part["firstByte"] : part["lastByte"] + 1]
            part_resp = requests.put(
                part["uploadUrl"],
                headers={"Content-Type": "application/octet-stream"},
                data=chunk,
                timeout=120,
            )
            part_resp.raise_for_status()
            etag = part_resp.headers["etag"].strip('"')
            uploaded_part_ids.append(etag)

        finalize_resp = requests.post(
            f"{API_BASE}/videos?action=finalizeUpload",
            headers=self._headers(),
            json={
                "finalizeUploadRequest": {
                    "video": video_urn,
                    "uploadToken": upload_token,
                    "uploadedPartIds": uploaded_part_ids,
                }
            },
            timeout=30,
        )
        finalize_resp.raise_for_status()

        self._wait_for_processing(video_urn)
        return video_urn

    def _wait_for_processing(self, video_urn: str) -> None:
        def check() -> bool:
            status = self._video_status(video_urn)
            if status == "PROCESSING_FAILED":
                raise RuntimeError(f"LinkedIn video {video_urn} failed processing")
            return status == "AVAILABLE"

        ready = poll_until(check, timeout_s=300, interval_s=5)
        if not ready:
            raise RuntimeError(f"LinkedIn video {video_urn} did not finish processing in time")

    def _video_status(self, video_urn: str) -> str:
        resp = requests.get(
            f"{API_BASE}/videos/{requests.utils.quote(video_urn, safe='')}",
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("status", "")

    def verify_live(self, post_id: str) -> bool:
        """Re-fetch the post and check it is PUBLISHED.

        Reading a post back needs LinkedIn's separate `r_member_social`
        permission (a restricted product), which this app does not have: with
        only `w_member_social` the read returns HTTP 403 even for a post that
        is live (seen 2026-10-16). In that case, and only for a post this
        adapter created itself in this run, LinkedIn's own acceptance of the
        create call (HTTP 201 with the post's id, after the video finished
        processing) is the evidence, so this warns and returns True. For any
        other post id, a refused read means "not verified" (False).
        """
        resp = requests.get(
            f"{API_BASE}/posts/{requests.utils.quote(post_id, safe='')}",
            headers=self._headers(),
            timeout=15,
        )
        if resp.ok:
            return resp.json().get("lifecycleState") == "PUBLISHED"
        if resp.status_code in (401, 403) and post_id in self._created_post_ids:
            warnings.warn(
                "LinkedIn refused to read the post back (no r_member_social); treating it as live "
                "because LinkedIn accepted the create call. Check the profile once to confirm.",
                stacklevel=2,
            )
            return True
        return False
