"""Distribution clearance: proof that a specific video file passed QC.

The Distribution Agent only runs on a video that (1) the user confirmed
as their final draft (see intake.py) and (2) passed QC. `QCClearance`
is that proof, and `distribute()` refuses to start without one.

A clearance is issued only by `clear_for_distribution()`, which checks
that the evaluation is a real PASS: both hard gates (duration, aspect
ratio) were actually evaluated and passed, and the verdict is PASS. It is
tied to the file's SHA-256, so it covers that exact video and nothing
else. A re-rendered or edited file needs a new confirmation and a new QC
pass.

The user's approval to post is separate and still required per platform
(`approve` callback in `distribute()`); a clearance never replaces it.

This guards against accidents, not against code that deliberately works
around it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .intake import FinalDraft, _sha256
from .models import HARD_GATE_METRICS, QCEvaluation, Verdict

_ISSUER = object()  # private sentinel: only clear_for_distribution() holds it


class QCNotPassed(Exception):
    """The evaluation is not a complete QC pass, so no clearance is issued."""


class ClearanceMismatch(Exception):
    """The video being distributed is not the one that passed QC."""


@dataclass(frozen=True)
class QCClearance:
    """Proof that this exact file passed QC. Create one only through
    `clear_for_distribution()`."""

    sha256: str
    title: str
    composite: Optional[float]
    verdict: str
    issued_at: str  # UTC, ISO 8601
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            raise QCNotPassed(
                "A QCClearance can only be created by clear_for_distribution(), "
                "from a passing QC evaluation of a confirmed final draft."
            )

    def ensure_matches(self, video_path: Path | str | None) -> None:
        """Raise unless `video_path` is byte-for-byte the file that passed QC."""
        if video_path is None:
            raise ClearanceMismatch(
                "The asset needs local_path set so the file can be checked "
                "against the QC clearance. Set it even if public_url is also used."
            )
        path = Path(video_path)
        if not path.is_file() or _sha256(path) != self.sha256:
            raise ClearanceMismatch(
                f"{path} is not the video that passed QC (it changed or is a "
                "different file). Confirm it as the final draft and run QC again."
            )


def clear_for_distribution(draft: FinalDraft, evaluation: QCEvaluation) -> QCClearance:
    """Issue a clearance for `draft` if `evaluation` is a complete QC pass.

    Raises `QCNotPassed` when a hard gate is missing or failed, the
    composite is below the pass threshold, or there is no score at all.
    Raises `FinalDraftChanged` if the file changed since it was confirmed.
    """
    if not isinstance(draft, FinalDraft):
        raise TypeError("clear_for_distribution() needs a FinalDraft from confirm_final_draft().")
    draft.ensure_unchanged()

    for gate in HARD_GATE_METRICS:
        result = evaluation.metrics.get(gate)
        if result is None or result.verdict != Verdict.PASS:
            raise QCNotPassed(
                f"Hard gate '{gate}' was not evaluated and passed, so this video "
                "is not cleared for distribution."
            )

    verdict = evaluation.final_verdict()
    if verdict != "PASS":
        raise QCNotPassed(
            f"QC verdict is {verdict} (composite {evaluation.composite_score()}), "
            "so this video is not cleared for distribution."
        )

    return QCClearance(
        sha256=draft.sha256,
        title=evaluation.video_title,
        composite=evaluation.composite_score(),
        verdict=verdict,
        issued_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        _issuer=_ISSUER,
    )
