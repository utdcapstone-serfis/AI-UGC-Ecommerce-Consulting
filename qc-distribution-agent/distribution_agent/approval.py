"""Chat-widget approval: carries the user's click in the approval widget
into `distribute()`.

Flow (development-time; see OPEN_QUESTIONS.md question 1):
  1. The agent creates an `ApprovalRequest` for one video and a platform list
     and shows the approval widget (approval_widget.html) with its request id.
  2. The user ticks platforms (all ticked by default) and clicks Approve
     selected or Deny all. The widget sends one chat message with the decision.
  3. The agent passes that message to `request.approver(text)` and uses the
     result as `distribute(..., approve=...)`.

Fail-safe, like `cli_approval`: anything it cannot confirm means no post. The
decision text must carry this request's id, the video file must be the one the
request was made for, the platform list must be the one shown, every approved
platform must have been on that list, and a decision works once. The widget
message only counts when it arrives from the user in chat; the agent must
never write or paste one itself.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional

from .adapters.base import VideoAsset

_ID_RE = re.compile(r"\[REQ-([0-9a-f]{8})\]")
_APPROVED_RE = re.compile(r"APPROVED for ([^.]*)\.")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_decision(text: str, request_id: str, requested: Iterable[str]) -> list[str]:
    """Returns the approved platforms (a subset of `requested`, in request
    order), or [] if the text is not a valid approval for this request.
    Never raises on bad input."""
    requested = list(requested)
    text = text or ""
    found = _ID_RE.search(text)
    if not found or found.group(1) != request_id:
        return []
    if "DENIED" in text:
        return []
    match = _APPROVED_RE.search(text)
    if not match:
        return []
    names = [name.strip().lower() for name in match.group(1).split(",") if name.strip()]
    if not names or any(name not in requested for name in names):
        return []
    return [platform for platform in requested if platform in names]


@dataclass
class ApprovalRequest:
    """One approval for one exact video and platform list."""

    title: str
    video_sha256: str
    platforms: list[str]
    qc_score: Optional[float] = None
    request_id: str = field(default_factory=lambda: secrets.token_hex(4))
    _used: bool = field(default=False, repr=False)

    @classmethod
    def create(cls, title: str, asset: VideoAsset, platforms: Iterable[str], qc_score: Optional[float] = None) -> "ApprovalRequest":
        if not asset.local_path:
            raise ValueError("asset.local_path is required so the approval is tied to the exact file.")
        return cls(
            title=title,
            video_sha256=_sha256(asset.local_path),
            platforms=list(dict.fromkeys(platforms)),
            qc_score=qc_score,
        )

    def widget_config(self) -> dict:
        """What the approval widget needs: shown on screen, plus the id the
        widget puts in its decision message."""
        return {
            "request_id": f"REQ-{self.request_id}",
            "title": self.title,
            "qc_score": self.qc_score,
            "platforms": self.platforms,
        }

    def approver(self, decision_text: str) -> Callable[[list[str], VideoAsset], list[str]]:
        """Builds the `approve` callback for `distribute()` from the user's
        widget message. Valid once; a second call approves nothing."""

        def approve(platforms: list[str], asset: VideoAsset) -> list[str]:
            if self._used:
                return []
            self._used = True  # a decision is spent even if it is then rejected
            if list(platforms) != self.platforms:
                return []
            if not asset.local_path or _sha256(asset.local_path) != self.video_sha256:
                return []
            return parse_decision(decision_text, self.request_id, self.platforms)

        return approve

    def pending_record(self) -> dict:
        """The document the agent stores for the dashboard (collection
        `approval_requests`, document id = request id) so an editor can approve
        it there. The dashboard shows it until a decision document exists."""
        return {
            "request_id": f"REQ-{self.request_id}",
            "title": self.title,
            "qc_score": self.qc_score,
            "platforms": self.platforms,
            "video_sha256": self.video_sha256[:12],
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "pending",
        }

    def decision_text_from_record(self, record: dict, max_age_hours: float = 24) -> str:
        """Turns a decision document from the dashboard (collection
        `distribution_decisions`) into the same text `approver()` takes, or ""
        if the record can't be trusted. The dashboard only lets people with
        edit access write that collection (a database rule), so the record is
        only as trustworthy as that rule: still check it here. It must name this
        request, carry who decided (`decided_by`), be recent, and approve only
        platforms that were on the request."""
        try:
            if record.get("request_id") != f"REQ-{self.request_id}":
                return ""
            if not record.get("decided_by"):
                return ""
            decided = datetime.fromisoformat(str(record.get("decided_at")))
            if decided.tzinfo is None:
                decided = decided.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - decided).total_seconds() / 3600
            if age < 0 or age > max_age_hours:
                return ""
            if record.get("status") == "denied":
                return f'Approval decision [REQ-{self.request_id}] for "{self.title}": DENIED.'
            if record.get("status") not in ("approved", "partial"):
                return ""
            approved = record.get("approved")
            if not isinstance(approved, list) or not approved:
                return ""
            return f'Approval decision [REQ-{self.request_id}] for "{self.title}": APPROVED for {", ".join(str(p) for p in approved)}.'
        except (TypeError, ValueError, AttributeError):
            return ""

    def approver_from_record(self, record: dict, max_age_hours: float = 24) -> Callable[[list[str], VideoAsset], list[str]]:
        """`approve` argument for `distribute()` from a dashboard decision record.
        Same checks and single use as `approver()`."""
        return self.approver(self.decision_text_from_record(record, max_age_hours))

    def log_record(self, decision_text: str) -> dict:
        """The shape stored for the QC Review Desk dashboard (collection
        `distribution_decisions`, document id = request id). Reflects what the
        decision text says, whether or not distribute() then used it."""
        approved = parse_decision(decision_text, self.request_id, self.platforms)
        if not approved:
            status = "denied"
        elif len(approved) == len(self.platforms):
            status = "approved"
        else:
            status = "partial"
        return {
            "request_id": f"REQ-{self.request_id}",
            "title": self.title,
            "video_sha256": self.video_sha256[:12],
            "qc_score": self.qc_score,
            "requested": self.platforms,
            "approved": approved,
            "not_approved": [p for p in self.platforms if p not in approved],
            "status": status,
            "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
