"""Animate the approved freeze frame into the 4-second Scene 1 clip with Seedance 2.5 image-to-video.

Why Seedance and not Kling: Seedance 2.5 has a 4 s minimum duration and generates audio with the video
(generate_audio=true); Kling 3.0 Turbo image-to-video has no sound field. Price (Oct 2026 estimate):
about $0.46 per second at 720p, so ~$1.85 for this clip.   Output: media/scene1-bar/ad_scene1_clip_v1.mp4
Known gaps in the result: the glass is never clearly set down on the counter; ~8 visible patrons, not 12-18.
"""
from hf_common import ROOT, collect, resume, submit, upload, wants_resume

DIR = ROOT / "media" / "scene1-bar"
OUT = DIR / "ad_scene1_clip_v1.mp4"

PROMPT = """Single continuous shot, no cuts, vertical 9:16, photorealistic cinematic lifestyle commercial, shot on a 35mm cinema lens with shallow depth of field. Smooth stable camera, a very slow steady dolly-in toward the seated man; no handheld shake, no sudden zoom.
0 to 1 second: medium-wide view along the bar, the bar interior alive behind him. 1 to 2.5 seconds: he lifts the crystal tumbler, takes one small natural sip, lowers it and sets it gently on the black marble counter, with a quiet glass-on-stone contact at about 2.7 seconds and a faint ice clink. 2.5 to 4 seconds: the camera settles into a medium close-up from mid-chest up with the glass visible at the lower edge of the frame; he glances down at his drink, then looks toward the room without turning to the camera, with a natural blink and subtle breathing, calm contemplative expression. Keep open space on the right side of the frame.
Background people move subtly and independently and stay visible the whole time: the two men talk quietly at the bar, the couple gestures and smiles, the bartender pours and hands over a drink, the friends chat and one briefly raises a glass. Nobody looks at the camera and nobody notices him. Keep his face, hair, suit and tie identical to the first frame, with realistic hand and glass handling.
Audio: soft mellow instrumental jazz lounge music (piano chords, gentle upright bass, brushed percussion) under a low continuous murmur of overlapping, unintelligible conversations; occasional delicate glass clinks, light pouring and soft shaker sounds; room ambience. No narration, no dialogue, no subtitles, no logos, no text."""

if wants_resume():
    resume("scene1_clip_v1", OUT, "video")
else:
    body = {"prompt": PROMPT, "image_url": upload(DIR / "ad_scene1_freeze_v1.png", "image/png"),
            "duration": 4, "resolution": "720p", "generate_audio": True}
    collect(submit("bytedance/seedance-2.5/image-to-video", body, "scene1_clip_v1"), OUT, "video")
