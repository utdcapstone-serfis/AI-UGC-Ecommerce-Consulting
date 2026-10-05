"""Technical/perceptual video quality — blur, noise, and compression
blockiness — measured directly via OpenCV, not judged by eye.

Fills a real gap the rest of the rubric doesn't cover: a video can be
visibly blurry, noisy, or over-compressed and still pass every other
metric (hook, branding, CTA...) since none of those are about pixel-
level quality. This module is adapted from the metric formulas in
https://github.com/MeaCuulpa/video_quality_analyzer, cleaned up to fix
real bugs found there (see below) and to return a single composite
MetricResult instead of an unused-metrics CSV.

Bugs found in the source and fixed here:
  - Its "jerkiness" metric always computed to 0.0 for every video (it
    read frame 0's motion value, which its own code hardcodes to 0,
    instead of the full per-frame motion series). Not reused here.
  - Its Good/Bad classification used only mean colorfulness and
    silently ignored the blur/noise/blockiness scores it computed.
    Here, all three measured checks actually feed the verdict.

Thresholds below are heuristics tuned to catch egregious cases
(obviously blurry, grainy, or block-compressed footage), not a
precise perceptual quality benchmark — same spirit as the other
"measured" checks in this package: transparent about what they
actually detect rather than overclaiming precision.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .models import MetricResult, Verdict

NORMALIZED_WIDTH = 640  # resize before scoring so thresholds don't depend on source resolution

# Laplacian-variance blur thresholds (higher variance = sharper).
BLUR_SHARP = 150.0
BLUR_BLURRY = 40.0

# Immerkær (1996) fast noise-estimate thresholds (sigma; higher = noisier).
NOISE_CLEAN = 2.0
NOISE_NOISY = 8.0

# 8x8 block-boundary-vs-interior difference (higher = more visible compression blocking).
BLOCK_CLEAN = 1.0
BLOCK_BLOCKY = 6.0


def _normalize(gray: np.ndarray) -> np.ndarray:
    h, w = gray.shape
    if w == NORMALIZED_WIDTH:
        return gray
    scale = NORMALIZED_WIDTH / w
    return cv2.resize(gray, (NORMALIZED_WIDTH, max(1, int(h * scale))), interpolation=cv2.INTER_AREA)


def _blur_score(gray: np.ndarray) -> float:
    """Laplacian variance. Higher = sharper."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _noise_sigma(gray: np.ndarray) -> float:
    """Fast noise estimate (Immerkær, 1996): convolve with a
    Laplacian-of-Gaussian-like mask that cancels out smooth image
    structure, leaving mostly sensor/compression noise behind.
    """
    h, w = gray.shape
    mask = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float64)
    conv = cv2.filter2D(gray.astype(np.float64), -1, mask, borderType=cv2.BORDER_REPLICATE)
    sigma = np.sqrt(np.pi / 2) * np.sum(np.abs(conv)) / (6 * (w - 2) * (h - 2))
    return float(sigma)


def _blockiness_score(gray: np.ndarray) -> float:
    """Mean abs difference across 8-pixel block boundaries, minus the
    mean abs difference between other adjacent pixels. A video with
    visible 8x8 DCT compression blocking scores well above zero here;
    a clean image scores near zero.
    """
    g = gray.astype(np.float64)

    col_diffs = np.abs(np.diff(g, axis=1))
    boundary_cols = col_diffs[:, 7::8]
    interior_cols = np.delete(col_diffs, np.arange(7, col_diffs.shape[1], 8), axis=1)

    row_diffs = np.abs(np.diff(g, axis=0))
    boundary_rows = row_diffs[7::8, :]
    interior_rows = np.delete(row_diffs, np.arange(7, row_diffs.shape[0], 8), axis=0)

    boundary_mean = float(np.concatenate([boundary_cols.ravel(), boundary_rows.ravel()]).mean())
    interior_mean = float(np.concatenate([interior_cols.ravel(), interior_rows.ravel()]).mean())

    return max(0.0, boundary_mean - interior_mean)


def _scale(value: float, good_at: float, bad_at: float) -> float:
    """Linearly map value to a 0-10 score. `good_at` is the value that
    scores 10; `bad_at` is the value that scores 0. Works whether
    higher-is-better (good_at > bad_at) or lower-is-better (good_at <
    bad_at); clamps to [0, 10] outside that range.
    """
    if good_at == bad_at:
        return 10.0
    t = (value - bad_at) / (good_at - bad_at)
    return round(max(0.0, min(10.0, t * 10.0)), 1)


def _sample_frames(video_path: Path, sample_count: int) -> list[np.ndarray]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video for technical quality analysis: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        raise RuntimeError(f"Video reports no frames: {video_path}")

    indices = np.linspace(0, total_frames - 1, num=min(sample_count, total_frames), dtype=int)

    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok and frame is not None:
            frames.append(frame)
    cap.release()

    if not frames:
        raise RuntimeError(f"Could not decode any frames from: {video_path}")
    return frames


def analyze_technical_quality(video_path: Path | str, sample_count: int = 10) -> MetricResult:
    """Samples `sample_count` frames evenly across the video and scores
    blur, noise, and compression blockiness. Returns a single
    MetricResult (verdict + 0-10 score + a note naming the actual
    measured values) ready to drop into QCEvaluation.metrics under the
    key "technical_quality".
    """
    video_path = Path(video_path)
    frames = _sample_frames(video_path, sample_count)

    blur_vals, noise_vals, block_vals = [], [], []
    for frame in frames:
        gray = _normalize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        blur_vals.append(_blur_score(gray))
        noise_vals.append(_noise_sigma(gray))
        block_vals.append(_blockiness_score(gray))

    blur = float(np.median(blur_vals))
    noise = float(np.median(noise_vals))
    block = float(np.median(block_vals))

    blur_score = _scale(blur, good_at=BLUR_SHARP, bad_at=BLUR_BLURRY)
    noise_score = _scale(noise, good_at=NOISE_CLEAN, bad_at=NOISE_NOISY)
    block_score = _scale(block, good_at=BLOCK_CLEAN, bad_at=BLOCK_BLOCKY)

    overall = round((blur_score + noise_score + block_score) / 3, 1)

    if overall >= 7.0:
        verdict = Verdict.PASS
    elif overall >= 4.0:
        verdict = Verdict.FLAG
    else:
        verdict = Verdict.FAIL

    note = (
        f"Measured across {len(frames)} sampled frames — "
        f"blur (Laplacian var) {blur:.0f} → {blur_score}/10, "
        f"noise (sigma) {noise:.2f} → {noise_score}/10, "
        f"blockiness {block:.2f} → {block_score}/10"
    )

    return MetricResult(verdict=verdict, score=overall, note=note)
