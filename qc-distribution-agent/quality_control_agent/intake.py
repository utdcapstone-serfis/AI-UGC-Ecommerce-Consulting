"""Intake guard: the QC Agent only ever receives a video the user has
explicitly declared to be their final draft.

Generation tools produce many intermediate videos and frames. None of
them should reach QC (it costs review time and pollutes the dashboard),
so QC analysis functions accept a `FinalDraft`, never a bare path. The
only way to get one is `confirm_final_draft()`, which asks the user.

Same fail-safe shape as the Distribution Agent's approval gate: anything
short of an explicit yes means no, including a non-interactive terminal,
silence, or EOF. There is no flag that skips the question.

The confirmation is tied to the exact file: it records a SHA-256 of the
bytes, and `FinalDraft.ensure_unchanged()` refuses a file that was
re-rendered or edited after the user said "final". Re-render means
confirm again.

This guards against accidents (a pipeline passing every generated clip
to QC). It is not a security boundary against code that deliberately
works around it.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

FinalConfirmCallback = Callable[[Path, str], bool]

_ISSUER = object()  # private sentinel: only confirm_final_draft() holds it


class FinalDraftNotConfirmed(Exception):
    """The user did not confirm this video as the final draft."""


class FinalDraftChanged(Exception):
    """The file changed after the user confirmed it as final."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class FinalDraft:
    """Proof that the user confirmed this exact file as their final draft.
    Create one only through `confirm_final_draft()`."""

    video_path: Path
    title: str
    sha256: str
    confirmed_at: str  # UTC, ISO 8601
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            raise FinalDraftNotConfirmed(
                "A FinalDraft can only be created by confirm_final_draft(), "
                "which asks the user to confirm this is the final video."
            )

    def ensure_unchanged(self) -> None:
        if not self.video_path.is_file() or _sha256(self.video_path) != self.sha256:
            raise FinalDraftChanged(
                f"{self.video_path} changed after it was confirmed as final. "
                "Confirm the new version with confirm_final_draft() before QC."
            )


def cli_final_confirmation(video_path: Path, title: str) -> bool:
    """Default confirmation: asks on the terminal. Returns False whenever
    a real answer can't be read (stdin isn't a TTY, or EOF), never True
    by default. A non-interactive run must pass its own `confirm`
    callback wired to a real human decision."""
    if not sys.stdin.isatty():
        return False
    label = title or video_path.name
    prompt = f'Is "{label}" your FINAL draft? Only final drafts are sent to QC. [y/N] '
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def confirm_final_draft(
    video_path: Path | str,
    title: str = "",
    confirm: FinalConfirmCallback = cli_final_confirmation,
) -> FinalDraft:
    """Ask the user whether `video_path` is the final draft. Returns a
    `FinalDraft` only on an explicit yes; otherwise raises
    `FinalDraftNotConfirmed` and nothing is sent to QC.

    `confirm(video_path, title)` must return True. Pass your own to wire
    this to a dashboard button or a chat message instead of the terminal.
    """
    path = Path(video_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No video file at {path}")

    if not confirm(path, title):
        raise FinalDraftNotConfirmed(
            f"{path.name} was not confirmed as the final draft, so it was not sent to QC."
        )

    return FinalDraft(
        video_path=path,
        title=title,
        sha256=_sha256(path),
        confirmed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        _issuer=_ISSUER,
    )
