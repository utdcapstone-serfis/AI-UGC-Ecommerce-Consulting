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
| Branding & consistency | 15% | Logo/colors/watermark presence, plus consistent wording, font, and background/foreground/middle-ground treatment throughout the clip |
| Safe zone | 10% | Key text/branding must clear platform UI overlays (top ~10%, bottom ~15–20%, sides ~5%) |
| Voice/tone | 10% | Matches brand voice guide; N/A for non-verbal content |
| Audio quality | 10% | Target -14 LUFS ±2, no clipping, no dead air >1.5s |
| Pacing | 10% | No single static/held shot longer than 8s |
| Call-to-action | 10% | Present in the final 3–5s, legible without sound |

Composite score = weighted average over metrics that actually have a
numeric score. N/A and unmeasured metrics are excluded — not counted
against the video — and the remaining weights re-normalize over what's
left (`composite_score()` in `models.py`). **Pass threshold: ≥7.0/10**
(`PASS_THRESHOLD` in `models.py`).

## What's actually measured vs. judged

- **Measured directly**, via `ffmpeg`/`ffprobe` — not eyeballed:
  duration, resolution/aspect ratio, integrated loudness (LUFS, via
  the `ebur128` filter), peak level (via `volumedetect`, to catch
  clipping).
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
- No code-level enforcement that the Distribution Agent only ever
  receives videos that actually passed this agent — that hand-off is
  currently a process convention, not an automated check.

## Related files

- Prompt spec: `agent-prompts.md` (section 1)
- Implementation: `quality_control_agent/`
- Dashboard: QC Review Desk (link above)
