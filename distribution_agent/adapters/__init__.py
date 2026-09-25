from .base import PlatformAdapter, PostResult, VideoAsset
from .instagram import InstagramAdapter
from .facebook import FacebookAdapter
from .youtube import YouTubeAdapter
from .reddit import RedditAdapter
from .bluesky import BlueskyAdapter
from .pinterest import PinterestAdapter
from .uploadpost import LinkedInAdapter, TikTokAdapter, UploadPostAdapter

ADAPTERS: dict[str, type[PlatformAdapter]] = {
    "instagram": InstagramAdapter,
    "facebook": FacebookAdapter,
    "youtube": YouTubeAdapter,
    "reddit": RedditAdapter,
    "bluesky": BlueskyAdapter,
    "pinterest": PinterestAdapter,
    "linkedin": LinkedInAdapter,
    "tiktok": TikTokAdapter,
}

__all__ = [
    "PlatformAdapter",
    "PostResult",
    "VideoAsset",
    "InstagramAdapter",
    "FacebookAdapter",
    "YouTubeAdapter",
    "RedditAdapter",
    "BlueskyAdapter",
    "PinterestAdapter",
    "UploadPostAdapter",
    "LinkedInAdapter",
    "TikTokAdapter",
    "ADAPTERS",
]
