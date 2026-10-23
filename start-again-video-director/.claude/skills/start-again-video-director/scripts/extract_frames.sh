#!/usr/bin/env bash
# Extract evidence frames from a generated video so a failure can be diagnosed
# from what is actually on screen. Read-only on the video; writes only to OUTDIR.
#
# Usage: extract_frames.sh <video> <outdir> [fps]
#   fps defaults to 1 (one frame per second). Use 4 to inspect a short clip.
# Output: <outdir>/f_001.jpg ...  and  <outdir>/sheet_1.jpg, sheet_2.jpg ...
#         (each sheet is 5 columns x 3 rows = 15 frames, read left-to-right, top-to-bottom)
set -euo pipefail

video="${1:-}"; outdir="${2:-}"; fps="${3:-1}"
if [ -z "$video" ] || [ -z "$outdir" ]; then
  echo "Usage: $0 <video> <outdir> [fps]" >&2; exit 2
fi
[ -f "$video" ] || { echo "Video not found: $video" >&2; exit 2; }

# Locate ffmpeg: PATH first, then a copy bundled with the imageio_ffmpeg Python package.
ff="$(command -v ffmpeg || true)"
if [ -z "$ff" ]; then
  for c in "$HOME"/Library/Python/*/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-* \
           "$(cd "$(dirname "$0")/../../../.." 2>/dev/null && pwd)"/venv/lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg-*; do
    [ -x "$c" ] && { ff="$c"; break; }
  done
fi
[ -n "$ff" ] || { echo "ffmpeg not found (install it, or pip install imageio-ffmpeg)." >&2; exit 3; }

mkdir -p "$outdir"
echo "ffmpeg: $ff"
echo "--- stream info"
"$ff" -hide_banner -i "$video" 2>&1 | grep -E "Duration|Stream" || true

"$ff" -v error -y -i "$video" -vf "fps=$fps,scale=480:-1" "$outdir/f_%03d.jpg"
n=$(ls "$outdir"/f_*.jpg | wc -l | tr -d ' ')
echo "--- extracted $n frames at ${fps} fps"

per=15; sheets=$(( (n + per - 1) / per ))
for k in $(seq 1 "$sheets"); do
  start=$(( (k - 1) * per + 1 ))
  "$ff" -v error -y -start_number "$start" -i "$outdir/f_%03d.jpg" -frames:v 1 \
        -vf "scale=300:-1,tile=5x3" "$outdir/sheet_$k.jpg" 2>/dev/null || true
  [ -f "$outdir/sheet_$k.jpg" ] && echo "sheet_$k.jpg = frames $start-$(( start + per - 1 < n ? start + per - 1 : n )) (time = (frame-1)/$fps s)"
done
