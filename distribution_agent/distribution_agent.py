"""Orchestrator: posts a QC-approved video to each requested platform,
verifies it went live, and notifies the client POC.

Matches the Distribution Agent prompt in agent-prompts.md — this module
is the actual implementation of that spec.
"""

from dataclasses import dataclass
from typing import Iterable, Optional

from .adapters import ADAPTERS
from .adapters.base import VideoAsset
from .notifier import notify_poc


@dataclass
class DistributionRecord:
    platform: str
    post_id: str
    url: Optional[str]
    is_live: bool
    poc_notified: bool


def distribute(
    asset: VideoAsset,
    platforms: Iterable[str],
    poc_email: Optional[str] = None,
) -> list[DistributionRecord]:
    """Post `asset` to each platform in `platforms`, verify it's live, and
    email `poc_email` per platform once confirmed. Only pass a video here
    that has already passed the Quality Control Agent.
    """
    records = []

    for platform in platforms:
        adapter_cls = ADAPTERS.get(platform)
        if adapter_cls is None:
            raise ValueError(f"Unknown platform: {platform!r}. Known platforms: {sorted(ADAPTERS)}")

        adapter = adapter_cls()
        result = adapter.upload(asset)
        is_live = adapter.verify_live(result.post_id)

        poc_notified = False
        if is_live and poc_email:
            notify_poc(poc_email, platform, result.url or result.post_id)
            poc_notified = True

        records.append(
            DistributionRecord(
                platform=platform,
                post_id=result.post_id,
                url=result.url,
                is_live=is_live,
                poc_notified=poc_notified,
            )
        )

    return records
