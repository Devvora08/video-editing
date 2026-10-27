#!/bin/bash
# Render chapters one at a time (never two at once on this 8 GB machine).
#   render.sh edited_videos/<video> 1080|4k  0 1 2 ...   -> <video>/_work/renders/<res>/chN.mp4
# 1080p measured ~3.5 s of render per 1 s of video. Render 4K only when the creator asks for it.
export npm_config_cache=/d/devtools/npm-cache HYPERFRAMES_NO_TELEMETRY=1 HYPERFRAMES_NO_UPDATE_CHECK=1 TEMP=/d/devtools/tmp TMP=/d/devtools/tmp FFMPEG_ENCODE_TIMEOUT_MS=3600000
V="$(cd "$1" && pwd)"; RES=$2; shift 2
OUT="$V/_work/renders/$RES"; mkdir -p "$OUT"
for n in "$@"; do
  ( cd "$V/_work/build/ch$n" && if [ "$RES" = 4k ]; then npx hyperframes render -f 30 -q delivery -w 1 --resolution landscape-4k -o "$OUT/ch$n.mp4"; else npx hyperframes render -f 30 -q delivery -w 1 -o "$OUT/ch$n.mp4"; fi ) 2>&1 | grep -E "MB ·|rror" | sed "s/^/ch$n: /"
done
