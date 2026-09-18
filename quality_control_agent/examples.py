"""Demo QCEvaluation fixtures from the two videos manually reviewed in
the design session — useful as usage examples and for exercising
report.py without needing a real video pipeline yet.
"""

from __future__ import annotations

from .models import MetricResult, QCEvaluation, Verdict

BURGER_REELS = QCEvaluation(
    video_title="Burger Making Reels",
    video_url="https://youtube.com/shorts/nqS6yQRHGD8",
    video_source="Circle Digital Marketing Agency",
    metrics={
        "duration": MetricResult(Verdict.PASS, note="24.5s — within the 15-30s window"),
        "aspect_ratio": MetricResult(Verdict.PASS, note="9:16 vertical"),
        "hook": MetricResult(Verdict.PASS, score=6, note="Motion present (patty on grill) but no text/question overlay; works fine muted"),
        "captions": MetricResult(Verdict.FLAG, score=3, note="No captions, but also no dialogue to caption — rubric gap for non-verbal content"),
        "safe_zone": MetricResult(Verdict.PASS, score=8, note="Agency tag sits top-left, clear of the right-edge like/comment/share rail"),
        "branding": MetricResult(Verdict.PASS, score=9, note="Agency watermark throughout + client logo card at close; consistent dark moody backdrop and food-macro framing across sampled frames, no wording/font mismatches observed"),
        "voice_tone": MetricResult(Verdict.NOT_APPLICABLE, note="No narration/dialogue — instrumental music only"),
        "audio_quality": MetricResult(Verdict.UNMEASURED, note="Needs LUFS/clipping analysis on the actual file"),
        "pacing": MetricResult(Verdict.PASS, score=8, note="At least 3 distinct shots across 24s"),
        "cta": MetricResult(Verdict.FAIL, score=2, note="Ends on a static logo card, no action verb"),
    },
)

MCDONALDS_SELF_CONTROL = QCEvaluation(
    video_title="Self Control Who I McDonald's",
    video_url="https://youtu.be/79phlhutGLg",
    video_source="McDonald's",
    metrics={
        "duration": MetricResult(Verdict.PASS, note="15.04s — right at the floor of the window"),
        "aspect_ratio": MetricResult(Verdict.FAIL, note="854x480 = 16:9 landscape. Out of scope for this agent — a traditional broadcast/pre-roll spot, not short-form vertical content — rejected at intake, not scored"),
        "hook": MetricResult(Verdict.PASS, score=8, note="Extreme close-up of fries with visible steam/motion"),
        "captions": MetricResult(Verdict.FAIL, score=2, note="No captions despite spoken dialogue — genuine miss, not a rubric gap"),
        "safe_zone": MetricResult(Verdict.NOT_APPLICABLE, note="Landscape broadcast spot — vertical in-feed UI safe zones don't apply"),
        "branding": MetricResult(Verdict.PASS, score=9, note="Consistent arches/colors, clean end card; single close-up food-styling look and one font on the end-card CTA, no shot mismatches in the frames sampled"),
        "voice_tone": MetricResult(Verdict.FLAG, score=6, note="Narration present; a top comment calls out an odd tonal shift at the end"),
        "audio_quality": MetricResult(Verdict.UNMEASURED, note="Needs LUFS/clipping analysis on the actual file"),
        "pacing": MetricResult(Verdict.FLAG, score=6, note="Couldn't fully verify cut frequency from sampled frames alone"),
        "cta": MetricResult(Verdict.PASS, score=9, note="Explicit 'Order ahead on the app' end card with logo"),
    },
)

ALL_EXAMPLES = [BURGER_REELS, MCDONALDS_SELF_CONTROL]
