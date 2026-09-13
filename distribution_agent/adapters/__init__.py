from .base import PlatformAdapter, PostResult, VideoAsset
from .instagram import InstagramAdapter
from .facebook import FacebookAdapter
from .youtube import YouTubeAdapter
from .reddit import RedditAdapter

ADAPTERS: dict[str, type[PlatformAdapter]] = {
    "instagram": InstagramAdapter,
    "facebook": FacebookAdapter,
    "youtube": YouTubeAdapter,
    "reddit": RedditAdapter,
}

__all__ = [
    "PlatformAdapter",
    "PostResult",
    "VideoAsset",
    "InstagramAdapter",
    "FacebookAdapter",
    "YouTubeAdapter",
    "RedditAdapter",
    "ADAPTERS",
]
