"""Common interface every platform adapter implements.

Each adapter takes a QC-approved video and:
  1. uploads/publishes it to the platform
  2. re-checks the platform to confirm the post is actually live

This is what lets the Distribution Agent orchestrator treat every
platform the same way instead of branching on platform-specific logic.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VideoAsset:
    """A video ready for distribution.

    Some platforms (Instagram, optionally Facebook) require a publicly
    reachable URL rather than a local file; others (YouTube, Reddit)
    upload the local file directly. Adapters raise a clear error if the
    field they need wasn't provided.
    """

    caption: str
    local_path: Optional[Path] = None
    public_url: Optional[str] = None


@dataclass
class PostResult:
    platform: str
    post_id: str
    url: Optional[str]


class PlatformAdapter(ABC):
    platform_name: str

    @abstractmethod
    def upload(self, asset: VideoAsset) -> PostResult:
        """Publish the video and return its platform-assigned id/url."""

    @abstractmethod
    def verify_live(self, post_id: str) -> bool:
        """Re-fetch the post from the platform to confirm it's actually live."""


def poll_until(check: "callable[[], bool]", timeout_s: int = 60, interval_s: int = 3) -> bool:
    """Call `check()` repeatedly until it returns True or timeout_s elapses."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(interval_s)
    return False
