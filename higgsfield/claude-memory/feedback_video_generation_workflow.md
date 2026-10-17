---
name: feedback-video-generation-workflow
description: "How this user wants AI video/image work run: cost discipline, one-shot accuracy, brand-mark checks, per-shot approval"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 528d3730-76b1-471e-b993-d48272f6e383
  modified: 2026-10-02T19:57:36.129Z
---

Get each generation right on the first try; the user repeatedly got frustrated ("you are wasting money") when I iterated blindly.

**Why:** Every Higgsfield request bills real money and the user is paying out of pocket. In the Roma ad, ~8 of the early generations were wasted re-fixing brand logos and misread shot requests.

**How to apply:**
- Use `resolution: "1k"` for stills (final video is 720p, 2k was wasted). Prefer 5s or shorter clips, consolidate montage beats into fewer clips, and use free local tools (PIL mockups, ffmpeg) instead of paid generation where they can do the job.
- Image models inject real brand marks on athletic gear (Nike swoosh, Adidas three-stripe, Puma, AS Roma crest, Apple logo on laptops) even when told not to. Put "no logos, no stripes, no swoosh, no brand marks" in every prompt, make shoes/shorts solid single-color, never put a real club name on a jersey, and zoom into shoes/shorts/laptop/phone back to check before showing the user. The wording "biting her lip" next to "chest" tripped the NSFW filter on a cartoon character, so avoid it.
- AI text is unreliable. For any readable UI, build the real screen with PIL and pass it as an image reference.
- A phone screen cannot face both the character and the camera in one static angle. A single medium shot with the screen tilted toward camera, animated with a camera push/pull, worked; the user rejected aerial and back-of-phone versions of that beat.
- Build one shot at a time, show frames or a clip, and wait for approval before the next. Read the user's wording literally and ask once if a shot description is ambiguous, rather than guessing and regenerating.
- If a poll times out client-side, re-poll the same request id; do not resubmit.
