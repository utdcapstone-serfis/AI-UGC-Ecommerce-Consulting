from .base import PlatformAdapter, PostResult, VideoAsset
from .instagram import InstagramAdapter
from .facebook import FacebookAdapter
from .youtube import YouTubeAdapter
from .reddit import RedditAdapter
from .bluesky import BlueskyAdapter

ADAPTERS: dict[str, type[PlatformAdapter]] = {
    "instagram": InstagramAdapter,
    "facebook": FacebookAdapter,
    "youtube": YouTubeAdapter,
    "reddit": RedditAdapter,
    "bluesky": BlueskyAdapter,
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
    "ADAPTERS",
]
