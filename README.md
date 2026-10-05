# Serfis ad content

Generated video ads and the briefs they came from. Kept separate from the
`serfis-leadgen` code repo because the media is large (~430 MB).

**Keep this repo private.** Some early Veeza experiments started from reference
photos taken from stock sites (watermarked previews), and the videos contain
AI-generated people.

## What is here

| Folder | Project | Final files |
|---|---|---|
| `media/veeza/` | Veeza AI, 30s wedding / honeymoon comedy | `veeza_FULL_STITCHED.mp4` (silent), `veeza_FULL_STITCHED_audio.mp4` (with music and SFX) |
| `media/roma/` | Roma AI, 30s fruit characters (paused after Scene 4) | locked characters `roma_*_MASTER.png`, backgrounds `roma_bg_*_MASTER.png`, scene clips `roma_scene1_v1.mp4` ... `roma_scene4_pan_v1.mp4` (Scene 4 not yet approved) |
| `media/quippy/` | Quippy AI, two 7s ads | `quippy_ad_7s.mp4` (first date), `quippy_parents_ad_7s.mp4` (meeting the parents) |
| `media/scuba/` | Scuba travel shot | `dive_ad_7s.mp4` (3-beat cut), `dive_solo_7s.mp4` and `dive_solo_5s_fish.mp4` (single take, no cuts) |
| `briefs/` | The five briefs, verbatim | one file per project |

Files with `_v1`, `_v2`... are earlier attempts kept for reference; the other
files in each folder are stills, frame checks and mockups used along the way.
Scene numbers on the unprefixed `scene*` files belong to Veeza.

## How they were made

- **Video and images:** Higgsfield API. Kling 3.0 Turbo image-to-video for all
  clips; Grok Imagine Image 2.0 (`xai/grok-imagine-image-2.0`) for stills built
  from reference images; Z-Image Turbo for backgrounds and first character sheets.
- **Anything with readable text** (phone screens, thought bubbles, end cards,
  calendar) was built locally with PIL and passed in as an image or overlaid with
  ffmpeg, because video models garble text.
- **Assembly:** ffmpeg crossfades, trims and audio mixing.
- **Lessons that cost money:** image models add real brand marks to athletic gear
  (Nike, Adidas stripes, Puma, a club crest, an Apple logo) even when told not to,
  so check shoes, shorts and laptops up close; a phone screen cannot face both the
  character and the camera in one static angle; Kling sometimes inserts its own
  cuts or lets subjects pass through each other, so inspect frames before using a
  clip.

## Audio credits (Veeza ad)

Sound effects and music from Pixabay (royalty-free, no attribution required):
haruudu "high heels walking on tiles", freesound_community "yay", "male ahhhh" and
"wine glass clink", universfield "funny dramatic gasp", fluffy_marry "joyful messy
piano", shut_up_ghost "cartoon kiss". The audio files themselves are not stored here.
