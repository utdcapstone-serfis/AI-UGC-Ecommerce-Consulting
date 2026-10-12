# Quality Control Agent — Source of Truth

The single reference for what this agent actually does today. If this
file and the code ever disagree, **the code is right** — update this
file to match, not the reverse.

## Scope

Short-form, vertical, sound-off-by-default feed video only: IG
Reels/Shorts, YouTube Shorts, Facebook Reels, Reddit video. A
traditional 16:9 broadcast/pre-roll spot is a different content
category and is explicitly **out of scope** — it's rejected at the
aspect-ratio hard gate, not scored against this rubric at all.

## The one invariant: QC only sees a declared final draft

Generation tools produce many intermediate videos and frames; none of
them go to QC. A video enters QC only after the user explicitly says it
is their final draft.

- `confirm_final_draft(video_path, title)` in
  `quality_control_agent/intake.py` asks the user and returns a
  `FinalDraft`. Anything short of an explicit "y" (no terminal, silence,
  EOF) raises `FinalDraftNotConfirmed` and nothing is analyzed.
- QC code takes a `FinalDraft`, never a path or frames.
  `analyze_technical_quality()` raises `TypeError` for anything else,
  and a `FinalDraft` can't be built by hand.
- The confirmation is tied to the exact file (SHA-256). If the file is
  re-rendered or edited afterwards, `FinalDraftChanged` is raised and the
  user has to confirm the new version.
- To confirm from something other than a terminal prompt (a dashboard
  button, a chat message), pass `confirm=(video_path, title) -> bool`.
- The visual review (hook, branding, safe zone, pacing, CTA) is done by
  Claude, so code can't enforce it. Rule for that part: never review or
  score a video the user hasn't called final, and never pull sampled
  frames from intermediate generations.
- This stops accidents. It isn't a security boundary against code that
  deliberately works around it.

## Hard gates (auto-reject, never scored)

| Gate | Requirement |
|---|---|
| Duration | 15–30 seconds |
| Aspect ratio / resolution | 9:16 vertical, minimum 1080×1920 |

A hard-gate failure always overrides the composite score, regardless
of how well everything else scored — see `final_verdict()` in
`quality_control_agent/models.py`.

## Weighted metrics (composite score, 0–10)

| Metric | Weight | Why this weight |
|---|---|---|
| Hook (first 3s) | 20% | Most scroll-away happens in the first 3s, and it has to work muted |
| Captions | 15% | Feed viewing defaults to sound off; N/A (not scored) for genuinely non-verbal content |
| Branding & consistency | 15% | The advertised company's own logo/colors/watermark presence in the video as made (QC checks it; neither QC nor the pipeline adds any), plus consistent wording, font, and background/foreground/middle-ground treatment throughout the clip |
| Technical quality | 10% | Blur, sensor/compression noise, and blocking artifacts — measured directly via OpenCV, not judged by eye |
| Safe zone | 10% | Key text/branding must clear platform UI overlays (top ~10%, bottom ~15–20%, sides ~5%) |
| Audio quality | 10% | Target -14 LUFS ±2, no clipping, no dead air >1.5s |
| Call-to-action | 10% | Present in the final 3–5s, legible without sound |
| Pacing | 5% | No single static/held shot longer than 8s |
| Voice/tone | 5% | Matches brand voice guide; N/A for non-verbal content |

Pacing and voice/tone were trimmed from 10% to 5% each to make room for
Technical Quality's 10% — CTA was left untouched given its direct link
to conversion, and voice/tone and pacing were already the two weakest
signals in practice (voice/tone is frequently N/A, and pacing is
currently a visual judgment call, not a measurement).

Composite score = weighted average over metrics that actually have a
numeric score. N/A and unmeasured metrics are excluded — not counted
against the video — and the remaining weights re-normalize over what's
left (`composite_score()` in `models.py`). **Pass threshold: ≥7.0/10**
(`PASS_THRESHOLD` in `models.py`).

## What's actually measured vs. judged

- **Measured directly**, via `ffmpeg`/`ffprobe`/OpenCV — not
  eyeballed: duration, resolution/aspect ratio, integrated loudness
  (LUFS, via the `ebur128` filter), peak level (via `volumedetect`, to
  catch clipping), and technical quality — blur (Laplacian variance),
  noise (Immerkær fast estimate), and compression blockiness (8×8
  block-boundary differences), via `quality_control_agent.technical_quality.analyze_technical_quality()`.
  Requires a local video file; unmeasured for anything only reviewed
  via streaming/browser playback.
- **Visual judgment call**, from sampled frames — no automated
  computer vision yet: hook strength, branding/consistency, safe-zone
  placement, pacing/cut frequency, CTA presence.
- **Assumed, not confirmed by ear**: whether a video has spoken
  dialogue at all — this drives the Captions/Voice-tone N/A exemption
  for non-verbal content, and should be flagged explicitly in
  `reviewer_notes` whenever it's an assumption rather than a
  confirmed fact.

## Data model & output

Implemented in `quality_control_agent/models.py`:

- `MetricResult(verdict, score, note)` — `verdict` is one of `pass`,
  `fail`, `flag`, `unmeasured`, `n/a`.
- `QCEvaluation(video_title, video_url, video_source, metrics,
  reviewer_notes)` — methods: `.hard_gates_pass()`,
  `.composite_score()`, `.final_verdict()`, `.doc_id()`, `.to_dict()`.
- `report.render_table_html()` / `render_standalone_report()` — HTML
  table rendering.
- `report.to_db_records()` — shapes a list of evaluations into
  `{doc_id, data}` pairs ready for a database batch write.
- `technical_quality.analyze_technical_quality(draft)` — takes a `FinalDraft`
  (see the invariant above), not a path. Samples
  frames via OpenCV and returns a single `MetricResult` for blur/
  noise/blockiness. Adapted from the metric formulas in
  [MeaCuulpa/video_quality_analyzer](https://github.com/MeaCuulpa/video_quality_analyzer),
  with two real bugs from that source fixed rather than carried over:
  its "jerkiness" metric always computed to `0.0` (it read a
  hardcoded-zero value instead of the actual per-frame motion series),
  and its own Good/Bad classification ignored the blur/noise/
  blockiness scores it computed, deciding purely on mean colorfulness.
  Both are corrected here — all three measured checks actually feed
  the verdict.

## Where results live

Every real evaluation is written to the **QC Review Desk** dashboard's
shared database (collection `qc_evaluations`) — that's what makes the
dashboard auto-update with no republish needed.

Dashboard: https://claude.ai/artifact/WfSG1dqhwF2ZUjwvrEnnrM

Demo/fixture evaluations used to exercise `report.py` live in
`quality_control_agent/examples.py` — these are illustrative sample
data, not live production evaluations.

## Known gaps / not yet built

- No automated computer-vision hook/pacing/safe-zone detection —
  every real evaluation today is a human-in-the-loop (Claude) visual
  review of sampled frames, not a fully automated pipeline.
- No automated speech-detection — the non-verbal assumption for
  Captions/Voice-tone is inferred from loudness profile and content
  style, not confirmed by listening.
- The hand-off is enforced in code: `distribute()` requires a
  `QCClearance` from `clear_for_distribution()`, which exists only for a
  confirmed final draft with a real PASS, tied to that file's SHA-256
  (see `DISTRIBUTION_AGENT.md`). Gap: `QCEvaluation.hard_gates_pass()`
  returns True when a gate metric is missing, so `final_verdict()` alone
  can say PASS without the gates being evaluated. The clearance check
  requires both gates present and passing; the model itself is unchanged.
- Technical Quality's blur threshold was calibrated on typical camera
  footage. First real run against an AI-generated video scored blur
  at 0/10 (Laplacian variance 32, against a 40 "blurry" floor) while
  noise and blockiness both scored a clean 10/10 — plausible (AI-video
  output and its compression can genuinely soften edges), but not yet
  validated against enough AI-generated samples to know if the
  threshold needs a separate calibration for that content type. Worth
  a human sanity check whenever this metric flags AI-generated footage
  specifically.

## Related files

- Prompt spec: `agent-prompts.md` (section 1)
- Implementation: `quality_control_agent/`
- Dashboard: QC Review Desk (link above)
