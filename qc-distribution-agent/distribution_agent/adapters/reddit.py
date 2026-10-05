"""Reddit adapter (PRAW).

Setup required before this works (see SETUP.md):
  1. Register an app at https://www.reddit.com/prefs/apps (type: "script").
  2. Note: Reddit has been tightening password-grant OAuth for third-party
     apps — check current Reddit API docs before relying on this if the
     script-app + username/password flow below stops working, and switch
     to the web-app OAuth code flow if needed.

Requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME,
REDDIT_PASSWORD, REDDIT_USER_AGENT, REDDIT_SUBREDDIT in the environment.
"""

import praw

from ..config import require_env
from .base import PlatformAdapter, PostResult, VideoAsset


class RedditAdapter(PlatformAdapter):
    platform_name = "reddit"

    def __init__(self) -> None:
        self.subreddit_name = require_env("REDDIT_SUBREDDIT")
        self.reddit = praw.Reddit(
            client_id=require_env("REDDIT_CLIENT_ID"),
            client_secret=require_env("REDDIT_CLIENT_SECRET"),
            username=require_env("REDDIT_USERNAME"),
            password=require_env("REDDIT_PASSWORD"),
            user_agent=require_env("REDDIT_USER_AGENT"),
        )

    def upload(self, asset: VideoAsset) -> PostResult:
        if not asset.local_path:
            raise ValueError("Reddit upload requires a local file path (asset.local_path)")

        subreddit = self.reddit.subreddit(self.subreddit_name)
        submission = subreddit.submit_video(title=asset.caption or "Video", video_path=str(asset.local_path))
        return PostResult(
            platform=self.platform_name,
            post_id=submission.id,
            url=f"https://reddit.com{submission.permalink}",
        )

    def verify_live(self, post_id: str) -> bool:
        submission = self.reddit.submission(id=post_id)
        submission._fetch()
        return bool(submission.is_video) and not submission.removed_by_category
