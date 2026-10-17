# Project status: where every ad stands (2026-10-17)

| Ad | Status | Final / key files |
|---|---|---|
| **Veeza AI**, 30 s wedding / honeymoon comedy | Finished | `media/veeza/veeza_FULL_STITCHED.mp4` (silent) and `veeza_FULL_STITCHED_audio.mp4` (music and sound effects from `media/audio/veeza-sfx/`) |
| **Quippy AI**, two 7 s ads (first date; meeting the parents) | Finished | `media/quippy/quippy_ad_7s.mp4`, `quippy_parents_ad_7s.mp4` |
| **Scuba travel** shot | Finished | `media/scuba/dive_ad_7s.mp4` (3-beat cut), `dive_solo_7s.mp4`, `dive_solo_5s_fish.mp4` (single take) |
| **Roma AI**, 30 s fruit characters (3D cartoon), 6 scenes | **Paused** after Scene 4 (2026-10-02, "put a pin in this") | see below |
| **Bar / tuxedo ad**, Scene 1 + the friend scene | In progress | `media/scene1-bar/`, `media/tuxedo-scene/` |

## Roma AI: how to resume
- **Locked, do not regenerate:** characters `roma_strawberry_MASTER.png`, `roma_banana_reference_v3.png`, `roma_orange_reference_v1.png`,
  `roma_apple_reference_v1.png` (watermelon and pineapple v1 as crowd filler); backgrounds `roma_bg_soccerfield_MASTER.png`,
  `roma_bg_dorm_MASTER.png` (empty, bed-framed), `roma_bg_stadium_MASTER.png`; the PIL-built app screen `roma_app_mockup.png`.
- **Done:** Scene 1 `roma_scene1_v1.mp4`; Scene 2 `roma_scene2a_v1.mp4` + `roma_scene2b_v2.mp4`; Scene 3 `roma_scene3_v1.mp4`; Scene 4
  `roma_scene4_pan_v1.mp4` (worried face -> pan to the phone press -> happy), **not yet approved**: confirm it first.
- **Remaining:** Scene 5 (practice montage + game, plan: consolidate into about 2 clips), Scene 6 (goal, celebration, Roma logo end card).
  Dialogue is not generated: no Higgsfield model does scripted lip-sync, so use sync.so or captions later. Music and effects not added.
- Brief: `briefs/roma-ai-30s-fruit-soccer.md`.

## Bar / tuxedo ad
- **Scene 1 (the bar), 4 s:** `ad_scene1_clip_v1.mp4` from freeze frame v1 (he is seated; the owner decided he only stands when his friend walks up).
  Known gaps: the glass is never clearly set down at 2.7 s; about 8 patrons instead of 12-18; right side of the frame not fully clear for the friend.
  v2 (background standing) is unused; v3 (everyone standing) left the left-hand couple seated.
- **Friend scene:** three clips from the Higgsfield app joined looked choppy; fixed by extending clips 1+2 with Seedance video-extend
  (`ad_extend_v1.mp4`) and joining them (`ad_fluid_v1.mp4`, 13 s). Remaining roughness: the friend's arrival (about 5.5-8 s) moves about twice as
  fast as the rest and stutters about once a second; an estimated ~$2.50 fix is to build it with extend too. Audio dips about 5 dB at the joins.
  Resolution is 496x864 (480p tier); a 720p final would cost about twice as much.
- **Audio files** in `media/tuxedo-scene/audio/` (`hf_..._.mp3`, `start_again_clip_1/2.mp3`) were found in Downloads next to these clips and look like
  audio for this scene; they were included without being listened to.
- Freesound sound effects in `media/audio/veeza-sfx/` may need attribution depending on each file's license; check before any public use.

## Spend
Unknown overall. The Higgsfield MCP balance tool showed a different account (10 credits, no transactions) than the API key in `.env`, so only
console.higgsfield.ai is authoritative. Prices seen are in `WORKFLOW_NOTES.md`.
