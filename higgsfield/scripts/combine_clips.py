"""Join clips into one video with ffmpeg (no Higgsfield call, no cost).

Re-encodes every clip to the same size / 24 fps / audio format first (xfade and concat both need
a constant frame rate), then concatenates with a 20 ms audio fade-in per clip so joins do not click.
The final "fluid" version of the tuxedo scene was:  clip 1 + clip 2 + the video-extend result.

Usage: python combine_clips.py OUT.mp4 clip1.mp4 clip2.mp4 [clip3.mp4 ...]
"""
import subprocess
import sys

import imageio_ffmpeg

out, clips = sys.argv[1], sys.argv[2:]
fc = ""
for i in range(len(clips)):
    fc += f"[{i}:v]fps=24,scale=496:864:flags=lanczos,setsar=1,format=yuv420p[v{i}];"
    fc += f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,afade=t=in:d=0.02[a{i}];"
fc += "".join(f"[v{i}][a{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=1[v][a]"
inputs = [arg for c in clips for arg in ("-i", c)]
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
                "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], check=True)
print("wrote", out)
