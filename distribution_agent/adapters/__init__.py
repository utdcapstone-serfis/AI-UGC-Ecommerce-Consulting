from .base import PlatformAdapter, PostResult, VideoAsset
from .instagram import InstagramAdapter
from .facebook import FacebookAdapter
from .threads import ThreadsAdapter
from .youtube import YouTubeAdapter
from .reddit import RedditAdapter
from .bluesky import BlueskyAdapter
from .pinterest import PinterestAdapter
from .x import XAdapter
from .uploadpost import LinkedInAdapter, TikTokAdapter, UploadPostAdapter

ADAPTERS: dict[str, type[PlatformAdapter]] = {
    "instagram": InstagramAdapter,
    "facebook": FacebookAdapter,
    "threads": ThreadsAdapter,
    "youtube": YouTubeAdapter,
    "reddit": RedditAdapter,
    "bluesky": BlueskyAdapter,
    "pinterest": PinterestAdapter,
    "x": XAdapter,
    "linkedin": LinkedInAdapter,
    "tiktok": TikTokAdapter,
}

__all__ = [
    "PlatformAdapter",
    "PostResult",
    "VideoAsset",
    "InstagramAdapter",
    "FacebookAdapter",
    "ThreadsAdapter",
    "YouTubeAdapter",
    "RedditAdapter",
    "BlueskyAdapter",
    "PinterestAdapter",
    "XAdapter",
    "UploadPostAdapter",
    "LinkedInAdapter",
    "TikTokAdapter",
    "ADAPTERS",
]
