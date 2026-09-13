"""YouTube adapter (YouTube Data API v3 — resumable upload).

Setup required before this works (see SETUP.md):
  1. Create a Google Cloud project, enable the YouTube Data API v3.
  2. Create an OAuth 2.0 client (Desktop or Web type).
  3. Run the OAuth consent flow once (google-auth-oauthlib) with the
     youtube.upload scope to obtain a refresh token.

Requires YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN in the environment.
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from ..config import require_env
from .base import PlatformAdapter, PostResult, VideoAsset

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeAdapter(PlatformAdapter):
    platform_name = "youtube"

    def __init__(self) -> None:
        credentials = Credentials(
            token=None,
            refresh_token=require_env("YT_REFRESH_TOKEN"),
            client_id=require_env("YT_CLIENT_ID"),
            client_secret=require_env("YT_CLIENT_SECRET"),
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES,
        )
        self.youtube = build("youtube", "v3", credentials=credentials)

    def upload(self, asset: VideoAsset) -> PostResult:
        if not asset.local_path:
            raise ValueError("YouTube upload requires a local file path (asset.local_path)")

        body = {
            "snippet": {
                "title": (asset.caption or "Untitled")[:100],
                "description": asset.caption,
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }
        media = MediaFileUpload(str(asset.local_path), chunksize=-1, resumable=True, mimetype="video/*")
        request = self.youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            _status, response = request.next_chunk()

        video_id = response["id"]
        return PostResult(platform=self.platform_name, post_id=video_id, url=f"https://youtube.com/shorts/{video_id}")

    def verify_live(self, post_id: str) -> bool:
        resp = self.youtube.videos().list(part="status,processingDetails", id=post_id).execute()
        items = resp.get("items", [])
        if not items:
            return False

        status = items[0].get("status", {})
        processing = items[0].get("processingDetails", {})
        return status.get("uploadStatus") == "processed" or processing.get("processingStatus") == "succeeded"
