"""Data model for a Quality Control Agent evaluation.

Mirrors the metrics table in agent-prompts.md: two hard gates (duration,
aspect ratio) plus seven weighted, scored metrics that combine into a
composite score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    FLAG = "flag"  # passed, but worth a human's attention
    UNMEASURED = "unmeasured"  # couldn't be checked with available tooling
    NOT_APPLICABLE = "n/a"  # metric doesn't apply to this piece of content


# Relative weight of each scored metric in the composite score.
# Duration and aspect_ratio are hard gates, not weighted — see hard_gates_pass().
# Skewed toward what decides survival in a short-form, sound-off-by-default
# feed: hook and captions outweigh audio quality, unlike a traditional ad.
METRIC_WEIGHTS = {
    "hook": 0.20,
    "captions": 0.15,
    "branding": 0.15,
    "safe_zone": 0.10,
    "voice_tone": 0.10,
    "audio_quality": 0.10,
    "pacing": 0.10,
    "cta": 0.10,
}

HARD_GATE_METRICS = ("duration", "aspect_ratio")

PASS_THRESHOLD = 7.0


@dataclass
class MetricResult:
    verdict: Verdict
    score: Optional[float] = None  # 0-10; None for hard gates, UNMEASURED, or NOT_APPLICABLE
    note: str = ""


@dataclass
class QCEvaluation:
    video_title: str
    video_url: str = ""
    metrics: dict[str, MetricResult] = field(default_factory=dict)
    reviewer_notes: str = ""

    def hard_gates_pass(self) -> bool:
        return all(
            self.metrics[gate].verdict == Verdict.PASS
            for gate in HARD_GATE_METRICS
            if gate in self.metrics
        )

    def composite_score(self) -> Optional[float]:
        """Weighted average over scored metrics only, re-normalized to
        whichever metrics actually have a score (some may be N/A or
        unmeasured for a given video).
        """
        scored = [
            (METRIC_WEIGHTS[key], result.score)
            for key, result in self.metrics.items()
            if key in METRIC_WEIGHTS and result.score is not None
        ]
        if not scored:
            return None
        total_weight = sum(weight for weight, _ in scored)
        return round(sum(weight * score for weight, score in scored) / total_weight, 1)

    def final_verdict(self) -> str:
        if not self.hard_gates_pass():
            return "FAIL (hard gate)"
        score = self.composite_score()
        if score is None:
            return "INCOMPLETE"
        return "PASS" if score >= PASS_THRESHOLD else "FAIL"
