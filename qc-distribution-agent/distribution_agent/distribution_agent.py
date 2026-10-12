"""Orchestrator: posts a QC-approved video to each requested platform,
verifies it went live, and notifies the client POC.

Matches the Distribution Agent prompt in agent-prompts.md — this module
is the actual implementation of that spec.

Posting is never automatic: distribute() shows the user the full list of
platforms and waits for an explicit answer before it uploads anything.
All platforms are preselected, so one confirmation approves them all, and
the user can narrow the list. No answer means no post — there is no flag
to skip this.

This is the development-time approval step. The final product may be
fully automated; see OPEN_QUESTIONS.md.
"""

import sys
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from quality_control_agent.clearance import QCClearance

from .adapters import ADAPTERS
from .adapters.base import VideoAsset
from .notifier import notify_poc

# approve(platforms, asset) -> the platforms the user approved (a subset).
ApprovalCallback = Callable[[list[str], VideoAsset], Iterable[str]]

_ALL_WORDS = {"", "y", "yes", "all"}
_NONE_WORDS = {"n", "no", "none", "cancel"}


def parse_platform_selection(answer: str, platforms: list[str]) -> Optional[list[str]]:
    """Turns the user's answer into the approved platforms, or None if the
    answer can't be understood (the caller must then treat it as no).

    - Enter, "y", "yes", "all": every listed platform.
    - "n", "no", "none", "cancel": no platform.
    - Numbers or names ("1 3", "youtube, x"): only those platforms.
    - Numbers or names with a leading dash ("-2", "-x"): all except those.
    Mixing the last two forms, or naming something not listed, is invalid.
    """
    text = answer.strip().lower()
    if text in _ALL_WORDS:
        return list(platforms)
    if text in _NONE_WORDS:
        return []

    names = {p.lower(): p for p in platforms}
    tokens = [t for t in text.replace(",", " ").split() if t]
    excluding = [t.startswith("-") for t in tokens]
    if any(excluding) and not all(excluding):
        return None

    chosen = []
    for token in tokens:
        token = token.lstrip("-")
        if token.isdigit() and 1 <= int(token) <= len(platforms):
            chosen.append(platforms[int(token) - 1])
        elif token in names:
            chosen.append(names[token])
        else:
            return None
    if not chosen:
        return None
    if all(excluding):
        return [p for p in platforms if p not in chosen]
    return [p for p in platforms if p in chosen]


def cli_approval(platforms: list[str], asset: VideoAsset) -> list[str]:
    """Default approval step: lists every platform, all preselected, and
    asks on the terminal. Enter approves them all; typing numbers or names
    posts only to those, and a leading dash removes platforms ("-2").

    Fails safe: returns [] (no post) whenever a real answer can't be read —
    stdin isn't a TTY, `input()` hits EOF, or the answer is not understood
    after three tries. A non-interactive run must pass its own `approve`
    callback wired to a real human decision instead.
    """
    if not sys.stdin.isatty():
        return []
    caption_preview = (asset.caption or "").strip()[:60]
    print(f'Video: "{caption_preview}"')
    print("Post to these platforms:")
    for number, platform in enumerate(platforms, start=1):
        print(f"  {number}. {platform}")
    prompt = (
        'Press Enter to post to ALL, type numbers or names for only those '
        '(e.g. "1 3"), "-2" to leave one out, or "n" to cancel: '
    )
    for _ in range(3):
        try:
            selected = parse_platform_selection(input(prompt), platforms)
        except EOFError:
            return []
        if selected is not None:
            return selected
        print("Sorry, I didn't understand that.")
    return []


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

    `approve(platforms, asset)` is called once, with the full list of
    platforms, before anything is uploaded. It returns the platforms the
    user approved. The default shows all platforms preselected: Enter
    approves them all, and the user can narrow the list. A platform that
    isn't approved is skipped (recorded with approved=False) and no
    adapter call — no credentials touched, no API request made — happens
    for it. Pass a custom `approve` to wire this to a real approval UI
    (a dashboard button, a Slack confirmation) instead of the terminal.
    A callback that returns a bool is rejected: it is the old
    per-platform signature, and silently treating it as "approve all"
    would be unsafe.
    """
    if not isinstance(clearance, QCClearance):
        raise TypeError(
            "distribute() needs a QCClearance from clear_for_distribution(); "
            "only a confirmed final draft that passed QC can be distributed."
        )
    clearance.ensure_matches(asset.local_path)

    requested = list(dict.fromkeys(platforms))  # keep order, drop duplicates
    for platform in requested:
        if platform not in ADAPTERS:
            raise ValueError(f"Unknown platform: {platform!r}. Known platforms: {sorted(ADAPTERS)}")

    answer = approve(requested, asset)
    if isinstance(answer, bool):
        raise TypeError(
            "approve() must return the list of approved platforms, not a bool. "
            "Per-platform approve(platform, asset) callbacks are no longer supported."
        )
    approved = set(answer)  # anything not in `requested` is ignored below

    records = []

    for platform in requested:
        if platform not in approved:
            records.append(DistributionRecord(platform=platform, approved=False))
            continue

        adapter_cls = ADAPTERS[platform]

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
