# SOP: Taking a video from final draft to posted

Written 2026-10-11. Follow this every time a video is published. For how each
agent works, see `QC_AGENT.md` and `DISTRIBUTION_AGENT.md`; for credentials,
see `SETUP.md`; for what is currently blocked, see `CURRENT_OBSTACLES.md`.

## Rules that never bend
- Only a video the user has confirmed as the final draft goes to QC. Never
  send intermediate generations or their frames.
- Only a video that passed QC can be distributed.
- Every post needs the user's explicit confirmation of the platform list (all
  preselected, narrowable). No answer means no post.
- Never read, print or paste credentials. The user edits `.env`. Never commit `.env`.
- Never submit a paid generation without approval of that exact generation.
- Confirm before any git change or outward-facing action.

## Who does what
- **User:** declares the final draft, approves each post, edits `.env`.
- **Claude:** runs QC, writes the evaluation, issues the clearance, runs distribution after approval.

## Steps

### 1. Declare the final draft
1. Finish editing. Export one video file.
2. The user says it is the final draft.
3. Run `confirm_final_draft("<video path>", title="<title>")` from `quality_control_agent`.
   It asks "Is this your FINAL draft?" and only a yes continues.
4. If the file changes afterwards (re-render, edit), repeat this step. The old
   confirmation is void for the changed file.

### 2. Run QC
1. Check the hard gates. Both must pass, or the video is rejected and never scored:
   - Duration 15 to 30 seconds.
   - 9:16 vertical, at least 1080×1920.
2. Run `analyze_technical_quality(draft)` for blur, noise and blockiness.
3. Score the rest from sampled frames of the final draft: hook, captions,
   branding and consistency, safe zone, audio, call-to-action, pacing, voice/tone.
   Use N/A for metrics that don't apply (for example voice/tone with no narration).
4. Build the `QCEvaluation`. Pass mark is a composite of 7.0 or higher with both
   hard gates passed.
5. Write the result to the QC Review Desk database (collection `qc_evaluations`)
   so the dashboard updates.

### 3. If QC fails
1. Give the user the failed metrics and the reviewer notes.
2. The user revises the video. Go back to step 1 with the new file.
3. Do not distribute. A failed video can't get a clearance.

### 4. If QC passes: get the clearance
1. Run `clear_for_distribution(draft, evaluation)`. It checks that both hard
   gates were evaluated and passed and that the verdict is PASS, and ties the
   clearance to the file's SHA-256.
2. If it raises `QCNotPassed` or `FinalDraftChanged`, stop and go back to the
   step it names.

### 5. Prepare the post
1. Decide the platforms and the caption.
2. Build the `VideoAsset`:
   - Set `local_path` always (needed to check the clearance).
   - Also set `public_url` for Instagram and Threads, and optionally Facebook.
3. Check each target platform's status in `CURRENT_OBSTACLES.md`.
   Don't try a platform that is marked blocked or has an expired token.

### 6. Get approval and post
1. Run `distribute(asset, platforms=[...], poc_email="...", clearance=clearance)`.
2. It lists every platform with all of them preselected. The user presses Enter to
   post to all, types numbers or names to post to only those ("1 3"), uses a leading
   dash to leave one out ("-2"), or types "n" to cancel. Platforms not approved are
   skipped with no upload and no credentials touched.
3. Never answer on the user's behalf, and never pass an `approve` function that
   approves platforms automatically. This approval step is for development; the final
   automated pipeline may handle it differently (see `OPEN_QUESTIONS.md`).

### 7. Confirm it is live and notify
1. `distribute()` re-checks each post on the platform itself. `is_live` is set only
   after that check.
2. When live, it emails the client contact (needs the SMTP settings in `.env`).
3. To send one summary email with the video attached, build a draft with
   `draft_distribution_email()` and `save_draft()` (see `SETUP.md`). It is only a
   draft. The user opens it, reviews it and sends it.
4. Read the returned records: platform, approved, post id, URL, `is_live`,
   `poc_notified`. Tell the user which posts went out and which were skipped or failed.

### 8. Record it
1. Update `CURRENT_OBSTACLES.md` if a platform's status changed
   (token expired, post failed, approval came through).
2. Commit doc changes only after the user says to, on the user's own branch.

## When something goes wrong
| Problem | What to do |
|---|---|
| User did not confirm final draft | Nothing goes to QC. Ask again, or stop. |
| `FinalDraftChanged` or `ClearanceMismatch` | The file changed after confirmation. Confirm the new file and run QC again. |
| QC fails | Step 3. Never distribute. |
| Token expired (Facebook, TikTok, Instagram about every 60 days, LinkedIn about every 60 days, YouTube 7 days in Testing mode) | The user generates a new token and puts it in `.env`. Don't read or paste it. |
| Platform marked blocked (Reddit, Pinterest, Threads, LinkedIn) | Skip it. Do not try workarounds or other accounts. |
| Upload fails | Report the platform's error text. Don't retry in a loop, and never post a duplicate. |
| Post uploaded but `is_live` is False | Tell the user. Don't email the client until it is confirmed live. |

## Checklist
- [ ] User declared the final draft
- [ ] Hard gates passed
- [ ] QC composite 7.0 or higher, evaluation saved to the dashboard
- [ ] Clearance issued
- [ ] `local_path` set (and `public_url` where needed)
- [ ] User confirmed the platform list (or narrowed it)
- [ ] Each post confirmed live
- [ ] Client contact notified
- [ ] Docs updated if a platform's status changed
