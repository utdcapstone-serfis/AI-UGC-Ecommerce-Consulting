"""Orchestrator: posts a QC-approved video to each requested platform,
verifies it went live, and notifies the client POC.

Matches the Distribution Agent prompt in agent-prompts.md — this module
is the actual implementation of that spec.

Posting is never automatic: distribute() asks for explicit human
approval, per platform, before it uploads anything. No approval means
no post — there is no flag to skip this.
"""

import sys
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from quality_control_agent.clearance import QCClearance

from .adapters import ADAPTERS
from .adapters.base import VideoAsset
from .notifier import notify_poc

ApprovalCallback = Callable[[str, VideoAsset], bool]


def cli_approval(platform: str, asset: VideoAsset) -> bool:
    """Default approval gate: asks on the terminal. Refuses (returns
    False) whenever a real answer can't be read — stdin isn't a TTY, or
    `input()` hits EOF because there's nothing to read from it anyway —
    rather than assuming consent. A non-interactive run (a cron job, a
    CI step) must pass its own `approve` callback wired to a real human
    decision instead; the failure mode here is always "no post", never
    a crash or a silent yes.
    """
    if not sys.stdin.isatty():
        return False
    caption_preview = (asset.caption or "").strip()[:60]
    prompt = f"Post \"{caption_preview}\" to {platform}? [y/N] "
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


@dataclass
class DistributionRecord:
    platform: str
    approved: bool
    post_id: Optional[str] = None
    url: Optional[str] = None
    is_live: bool = False
    poc_notified: bool = False


def distribute(
    asset: VideoAsset,
    platforms: Iterable[str],
    poc_email: Optional[str] = None,
    approve: ApprovalCallback = cli_approval,
    *,
    clearance: QCClearance,
) -> list[DistributionRecord]:
    """Post `asset` to each platform in `platforms`, verify it's live, and
    email `poc_email` per platform once confirmed.

    `clearance` is required: it's the proof, from
    `quality_control_agent.clear_for_distribution()`, that this exact
    file was confirmed as the final draft and passed QC. It's checked
    against `asset.local_path` before anything else happens (before any
    approval prompt, adapter, or credential), and a mismatch raises
    `ClearanceMismatch`. Set `asset.local_path` even when a platform
    also needs `public_url`; the public copy is assumed to be the same file.

    `approve(platform, asset)` is called before every single upload and
    must return True for that platform's post to happen; a platform that
    isn't approved is skipped (recorded with approved=False) and no
    adapter call — no credentials touched, no API request made — happens
    for it. Pass a custom `approve` to wire this to a real approval UI
    (a dashboard button, a Slack confirmation) instead of the terminal
    prompt default.
    """
    if not isinstance(clearance, QCClearance):
        raise TypeError(
            "distribute() needs a QCClearance from clear_for_distribution(); "
            "only a confirmed final draft that passed QC can be distributed."
        )
    clearance.ensure_matches(asset.local_path)

    records = []

    for platform in platforms:
        adapter_cls = ADAPTERS.get(platform)
        if adapter_cls is None:
            raise ValueError(f"Unknown platform: {platform!r}. Known platforms: {sorted(ADAPTERS)}")

        if not approve(platform, asset):
            records.append(DistributionRecord(platform=platform, approved=False))
            continue

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
                approved=True,
                post_id=result.post_id,
                url=result.url,
                is_live=is_live,
                poc_notified=poc_notified,
            )
        )

    return records
