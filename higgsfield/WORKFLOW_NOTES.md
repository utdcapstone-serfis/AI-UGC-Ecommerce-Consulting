# Higgsfield workflow notes (what we learned, so nobody repeats the expensive mistakes)

## How we work
- **One approved still before any video.** Generate a 1k freeze frame, show it, wait for approval, only then animate.
  Build one shot at a time and get approval per shot; read the brief literally and ask once if a shot is ambiguous.
- **Stills at 1k** (final video is 720p; 2k stills were wasted money). Prefer clips of 5 s or less.
- **Free price check first:** `POST https://api.higgsfield.ai/estimate/<endpoint-id>` with the same body returns the cost
  (or a pricing description for video-input models). Failed and moderated (`nsfw`) requests are not charged; a request can only
  be cancelled while still queued.
- **If polling times out, re-poll the same request id** (`python <script> resume`). Resubmitting bills again.
- **Download outputs**: Higgsfield keeps them for at least 7 days.
- **Upload inputs** with the presigned-URL flow (`hf_common.upload`); send only the returned headers to the storage URL,
  never the API credentials.

## Pricing seen (Oct 2026, 16:9-equivalent pixel count; 9:16 costs the same)
| Model | Cost |
|---|---|
| Seedance 2.5 image-to-video (with audio) | ~$0.46 per second at 720p (min 4 s) -> ~$1.85 for the 4 s Scene 1 clip |
| Seedance 2.5 video-extend | ~$0.123 per second at 480p, ~$0.277 at 720p; **source + new seconds are both billed** |
| Kling 3.0 Turbo image-to-video, 4 s, 720p | ~$0.45; **no sound field** |
| Grok Imagine Image 2.0, 1k | one image per request; `quality` low or medium only |

## What worked
- **Character consistency:** crop the character sheet into a front headshot, a 3/4 headshot and a full-body shot and pass them as
  `image_urls` to Grok Imagine Image 2.0. Cropping beat passing the whole contact sheet.
- **Video that flows:** separately generated clips look choppy when joined (camera angle and light reset at each join, and a model
  may insert its own hard cut). **Continue the video with Seedance 2.5 video-extend** instead of generating the next clip from scratch.
  Measured with a frame-difference score: the extension splice scored 1.8 vs ~4.5 for normal motion; the old cut scored 58.9.
- **ffmpeg joins:** re-encode every clip to the same size and a constant 24 fps before concatenating or cross-fading.

## What to watch for
- **Brand marks:** image models inject real logos on gear, glassware and screens even when told not to. Put "no logos, no brand marks,
  no readable text" in every prompt and zoom into labels before showing anyone. AI text is unreliable: build any readable UI with
  PIL and pass it in as an image.
- **Edits keep the scene, not every detail.** In the all-standing edit the couple at the low round table stayed seated because the
  table stayed. Name what must change AND what must stay.
- **Models make their own cuts and skip beats.** Scene 1's clip never clearly sets the glass down at 2.7 s and shows ~8 patrons, not 12-18.
- **Generated audio is quiet and unverified:** about -30 dB average on Scene 1. Listen before relying on it.
- Some Seedance clips fade to black in their last half second; that is in the output, not added later.
- NSFW filter false positives happen on innocent wording (a phrase next to "chest" tripped it on a cartoon prompt).
