"""Make separately generated clips flow as ONE shot: continue them with Seedance 2.5 video-extend.

Problem this solved: three separately generated clips (a man alone at his table -> a friend walks up ->
the two talk) looked choppy when concatenated: the camera angle and light reset at each join, and the third
clip made its own hard cut (a jump of 58.9 on a frame-difference score vs ~4.5 normal motion).
Fix: keep clips 1 + 2 (they already flow) and replace clip 3 with an extension of them.
The result contains ONLY the new seconds, so combine_clips.py joins it to the source afterwards.

Pricing: about $0.12 per second (480p) of source + new video combined (both are billable), so
8 s of source + 5 s new is ~$1.60. The splice measured 1.79 vs ~4.5 normal motion, i.e. invisible.
Output: media/tuxedo-scene/ad_extend_v1.mp4
"""
import subprocess

import imageio_ffmpeg

from hf_common import ROOT, collect, resume, submit, upload, wants_resume

DIR = ROOT / "media" / "tuxedo-scene"
SRC = DIR / "source"
OUT = DIR / "ad_extend_v1.mp4"
CLIP1 = SRC / "hf_20261012_234244_5970663a-2adc-44c7-bab9-98080150e305.mp4"   # man alone at his table
CLIP2 = SRC / "hf_20261012_234753_4a6fb4db-b400-49cc-9e96-683f32989b87.mp4"   # his friend walks up

PROMPT = """Continue this exact same continuous shot with no cuts. The two men in tuxedos are seated across from each other at the small marble-top table in the upscale bar, the friend has just sat down after greeting him. They settle in and talk warmly with relaxed smiles and small natural gestures, one briefly lifts his glass. The camera keeps its smooth, steady cinematic movement and slowly pushes in from the two-shot toward the man in the foreground, ending in a gentle medium close-up of him smiling, with his friend at the edge of the frame. Keep the same faces, hair, tuxedos, bow ties, table, bar, city windows, lighting and color grade as the source video. No cut, no change of angle or location, no sudden camera swing. The audio continues seamlessly from the source: the same soft lounge music, low crowd murmur, delicate glass clinks. No narration, no subtitles, no text, no logos."""

if wants_resume():
    resume("tuxedo_extend_v1", OUT, "video")
else:
    joined = DIR / "source_1_2.mp4"
    fc = ("[0:v]fps=24,setsar=1,format=yuv420p[v0];[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];"
          "[1:v]fps=24,setsar=1,format=yuv420p[v1];[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];"
          "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(CLIP1), "-i", str(CLIP2), "-filter_complex", fc,
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    str(joined)], check=True, capture_output=True)
    body = {"prompt": PROMPT, "video_url": upload(joined, "video/mp4"), "duration": 5, "resolution": "480p", "generate_audio": True}
    collect(submit("bytedance/seedance-2.5/video-extend", body, "tuxedo_extend_v1"), OUT, "video")
