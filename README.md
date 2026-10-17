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

---

# Allison - Higgsfield branch: how this branch is organized

This branch holds **everything related to Higgsfield and AI video/image generation** and nothing from the lead-gen
agents or dashboard (that work lives on the `lead-gen-agent` branch). **Keep the repository private**: some early Veeza
experiments started from watermarked stock-site photos, and the videos contain AI-generated people.

| Path | What it is |
|---|---|
| `.claude/skills/higgsfield/` | The Claude Code skill: auth, the submit-then-poll lifecycle, and the rule to confirm each model's own schema |
| `briefs/` | The six briefs, verbatim (Veeza, Roma, Quippy x2, Scuba, **Scene 1: The Bar**) |
| `media/veeza`, `roma`, `quippy`, `scuba` | The earlier ads and everything made along the way (see the table above) |
| `media/scene1-bar/` | Scene 1 of the bar ad: the freeze frames `ad_scene1_freeze_v1..v3.png` and the 4 s clip `ad_scene1_clip_v1.mp4` |
| `media/tuxedo-scene/` | The three source clips (`source/`), the first joined attempt `ad_combined_v1.mp4`, the Seedance extension `ad_extend_v1.mp4`, and the final `ad_fluid_v1.mp4` |
| `higgsfield/scripts/` | The generation scripts that produced the Scene 1 and tuxedo-scene files (shared helper in `hf_common.py`) |
| `higgsfield/WORKFLOW_NOTES.md` | Costs, what worked, what to watch for |

## The October 2026 bar / tuxedo ad (in order)
1. `briefs/scene1-the-bar-4s.md`: Allison's Scene 1 script.
2. `generate_freeze_frame.py` -> `edit_freeze_frame.py` (two edits) -> `animate_frame_seedance.py`: freeze frame, approval, then the clip.
3. Three clips made in the Higgsfield app (man alone, friend walks up, the two talk) were joined, looked choppy, and were fixed with
   `extend_video_seedance.py` + `combine_clips.py` (details and measurements in `WORKFLOW_NOTES.md`).

## Running the scripts
`pip install python-dotenv requests imageio-ffmpeg`, copy `.env.example` to `.env` and fill in the two Higgsfield values, then for example
`python higgsfield/scripts/animate_frame_seedance.py` (add `resume` to collect an existing request without paying again).
Each script saves its request id in `higgsfield/runs/`.

**Not preserved:** the character sheet image and the three reference crops (`ref_front_head.png`, `ref_34left_head.png`,
`ref_front_body.png`) that `generate_freeze_frame.py` expects in `media/scene1-bar/references/` were not saved. Recreate them by cropping a
character sheet, or point the script at any 2-3 reference images.
