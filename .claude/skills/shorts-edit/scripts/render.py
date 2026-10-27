#!/usr/bin/env python3
"""render.py: lint -> render -> finish -> verify -> deliver, in one command.

  python render.py --project videos/<p> [--res 4k|1080] [--draft] [--music auto|none|jazzy|calm|upbeat|tense|FILE] [--music-level -25] [--deliver DIR]

  lint     `hyperframes lint` must report 0 errors (its warnings about file size and nesting are expected here)
  render   1080x1920, or 2160x3840 with --res 4k (the same composition at 2x). The frame cache goes next to the
           project, never to the system temp folder (a full C: drive kills a render halfway)
  finish   the voice is brought to -14 LUFS (true peak under -1 dB), full BT.709 tags are written (the render leaves two
           of them "unknown" and faces then look darker and redder), and the music bed is laid far behind the voice:
           synthesised by music.py to the exact length (the storyboard's "music" key, or --music), or a file you supply,
           set to a fixed loudness 20 LU under the voice and dipped a little more while you speak
  verify   the FILE is checked: size, duration against the composition, picture and sound the same length, colour tags,
           loudness, black frames while the face cam or a scene should be showing. Any FAIL = do not deliver
  deliver  edited_videos/<video>/<video>-v<N>.mp4 + captions .srt + VERIFY.md, next to the creator's own files
           (version numbers keep counting up; --deliver DIR sends it elsewhere)

--draft renders 1080 at draft quality for a fast look at motion and timing; it is never delivered.
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import npx, ffmpeg, tool, probe, vstream, astream, load

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--res", default="1080", choices=["1080", "4k"])
ap.add_argument("--draft", action="store_true")
ap.add_argument("--workers", default="2", help="render workers; 1 on a machine with 8 GB of RAM or when a render paints black")
ap.add_argument("--gpu", action="store_true", help="hardware encoder (give it a bitrate: it ignores quality settings)")
ap.add_argument("--music", help="auto (from the storyboard), none, jazzy, calm, upbeat, tense, or a file you have the rights to")
ap.add_argument("--music-level", type=float, help="loudness of the bed in LUFS (default -25: 11 LU under the voice)")
ap.add_argument("--loudness", type=float, default=-14.0)
ap.add_argument("--deliver", help="folder the finished file is copied to (default: the video's own folder, next to its _work)")
ap.add_argument("--skip-render", action="store_true", help="finish and verify the existing raw render again")
args = ap.parse_args()

P = args.project
pub = os.path.join(P, "public")
# the house layout: edited_videos/<video>/_work is the project; the final cut is delivered into edited_videos/<video>/
IN_WORK = os.path.basename(os.path.abspath(P)) == "_work"
name = os.path.basename(os.path.dirname(os.path.abspath(P))) if IN_WORK else os.path.basename(os.path.abspath(P))
raw = os.path.join(P, "render-draft.mp4" if args.draft else "render-raw.mp4")
index = open(os.path.join(pub, "index.html"), encoding="utf-8").read()
D = float(re.search(r'id="stage"[^>]*data-duration="([\d.]+)"', index).group(1))
want = (1080, 1920) if (args.res == "1080" or args.draft) else (2160, 3840)

# ---- lint ---------------------------------------------------------------------------------------------------
r = npx(["hyperframes", "lint", pub], capture_output=True, text=True, encoding="utf-8", errors="replace")
out = re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout or "") + (r.stderr or ""))
m = re.search(r"(\d+) error\(s\)", out)
if m and int(m.group(1)) > 0:
    print("\n".join(l for l in out.splitlines() if "✗" in l or "Fix:" in l))
    sys.exit("lint: %s error(s). Fix the storyboard or the format, then compose again." % m.group(1))
print("lint: 0 errors")

# ---- render -------------------------------------------------------------------------------------------------
if not args.skip_render:
    cache = os.path.abspath(os.path.join(P, "_cache", "frames"))
    os.makedirs(cache, exist_ok=True)
    cmd = ["hyperframes", "render", pub, "-o", raw, "--workers", str(args.workers), "--frames-cache-dir", cache,
           "--resolution", "portrait-4k" if want[0] == 2160 else "portrait", "--quiet"]
    if args.draft:
        cmd += ["--quality", "draft"]
    elif args.gpu:
        cmd += ["--gpu", "--video-bitrate", "45M" if want[0] == 2160 else "16M"]
    else:
        cmd += ["--crf", "16"]
    t0 = time.time()
    print("rendering %dx%d, %.1f s of video, %s worker(s) ..." % (want[0], want[1], D, args.workers), flush=True)
    env = dict(os.environ, NODE_OPTIONS="--max-old-space-size=4096")
    from common import tool_env
    env.update({k: v for k, v in tool_env().items() if k in ("PATH", "HYPERFRAMES_NO_TELEMETRY", "HYPERFRAMES_NO_UPDATE_CHECK")})
    r = npx(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not os.path.exists(raw):
        sys.exit("render failed:\n" + re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout or "") + (r.stderr or ""))[-1500:])
    print("rendered in %.0f s" % (time.time() - t0))
if args.draft:
    print("draft: %s (look at motion and timing; not for delivery)" % raw)
    sys.exit(0)

# ---- finish: loudness, colour tags, optional music -------------------------------------------------------------
def loud(path, extra=""):
    r = subprocess.run([tool("ffmpeg"), "-hide_banner", "-nostats", "-i", path, "-vn", "-af", extra + "loudnorm=I=%.1f:TP=-1.5:LRA=11:print_format=json" % args.loudness,
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    return json.loads(m.group(0)) if m else None


ms = loud(raw)
final = os.path.join(P, "final.mp4")
norm = "anull"
if ms and ms["input_i"] not in ("-inf", "inf"):
    norm = ("loudnorm=I=%.1f:TP=-1.5:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true"
            % (args.loudness, ms["input_i"], ms["input_tp"], ms["input_lra"], ms["input_thresh"], ms["target_offset"]))
tags = ["-c:v", "copy", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart+write_colr"]
# which bed: --music wins, then the storyboard's "music" key, then a bed matched to the storyboard's mood
sb_path = os.path.join(P, "storyboard.json")
SB = load(sb_path) if os.path.exists(sb_path) else {}
mus = args.music if args.music else SB.get("music", "auto")
mcfg = mus if isinstance(mus, dict) else {}
choice = mcfg.get("file") or mcfg.get("mood") or (mus if isinstance(mus, str) else ("none" if mus is False else "auto"))
if choice == "auto":
    choice = "jazzy"                 # the house bed: fun and jazzy whatever the sound-effect mood; other beds only by name
level = args.music_level if args.music_level is not None else float(mcfg.get("level", -25.0))
bed = None
if choice in ("jazzy", "calm", "upbeat", "tense"):
    # a new tune for every video: the seed comes from the video itself (its name and every word said in it)
    cap = os.path.join(P, "captions.srt")
    said = open(cap, encoding="utf-8").read() if os.path.exists(cap) else ""
    seed = int(mcfg.get("seed", zlib.crc32((name + "|" + str(SB.get("id", "")) + "|" + said).encode("utf-8")) % 100000))
    # ... and it follows the edit: the band's beats are fitted to the moments things arrive on screen
    mo = os.path.join(P, "moments.json")
    hits = sorted(set(round(b["in"] + 0.2, 2) for b in load(mo).get("beats", []))) if os.path.exists(mo) else []
    bed = os.path.join(P, "music.wav")
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "music.py"), "--out", bed,
                        "--duration", "%.3f" % D, "--mood", choice, "--seed", str(seed), "--hits", ",".join("%.2f" % h for h in hits)],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("music.py failed: " + (r.stderr or "")[-400:])
    print("music: " + " | ".join(r.stdout.strip().splitlines()))
elif choice not in ("none", "", None):
    if not os.path.exists(choice):
        sys.exit("no such music file: %s (or use jazzy, calm, upbeat, tense, none)" % choice)
    bed = choice
    print("music: %s" % bed)
else:
    print("music: none")
if bed:
    mm = loud(bed)
    gain = level - float(mm["input_i"]) if mm and mm["input_i"] not in ("-inf", "inf") else -24.0
    # the bed sits at a fixed loudness far under the voice, and dips a little further while the voice is speaking
    fc = ("[0:a]%s,asplit=2[voice][sc];[1:a]aresample=48000,equalizer=f=2600:t=q:w=0.9:g=-5,volume=%.2fdB,afade=t=in:d=1.2,afade=t=out:st=%.2f:d=1.8[bed];"
          "[bed][sc]sidechaincompress=threshold=0.05:ratio=2:attack=20:release=300[duck];"
          "[voice][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89:level=disabled[a]" % (norm, gain, max(0.0, D - 1.8)))
    ffmpeg(["-i", raw, "-stream_loop", "-1", "-i", bed, "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-t", "%.3f" % D] + tags + [final])
    print("music level: %.0f LUFS (voice %.0f)" % (level, args.loudness))
else:
    ffmpeg(["-i", raw, "-map", "0:v", "-map", "0:a", "-af", norm] + tags + [final])

# ---- verify the file ----------------------------------------------------------------------------------------
rows, fails = [], 0


def check(label, ok, got, need):
    global fails
    fails += 0 if ok else 1
    rows.append("| %s | %s | %s | %s |" % (label, "pass" if ok else "**FAIL**", got, need))


info = probe(final)
vs, as_ = vstream(info), astream(info)
vd = float(vs.get("duration") or info["format"]["duration"])
ad = float(as_["duration"]) if as_ and as_.get("duration") else None
check("Size", (int(vs["width"]), int(vs["height"])) == want, "%sx%s" % (vs["width"], vs["height"]), "%dx%d" % want)
check("Duration", abs(vd - D) <= 1.5 / 30, "%.3f s" % vd, "%.3f s ± 1 frame" % D)
check("Length for a Short", vd <= 180.0, "%.1f s" % vd, "180 s at most")
check("Picture vs sound", ad is not None and abs(vd - ad) <= 0.12, "%.3f / %s" % (vd, "%.3f" % ad if ad else "no audio"), "within 0.12 s")
check("Colour tags", all(vs.get(k) == "bt709" for k in ("color_primaries", "color_transfer", "color_space")),
      "/".join(str(vs.get(k)) for k in ("color_primaries", "color_transfer", "color_space")), "bt709 x3")
after = loud(final)
li = float(after["input_i"]) if after and after["input_i"] not in ("-inf", "inf") else None
if bed:
    vo = loud(raw, norm + ",")                      # the voice alone, levelled the same way: the bed may add almost nothing to it
    vi = float(vo["input_i"]) if vo and vo["input_i"] not in ("-inf", "inf") else None
    check("Music under the voice", level <= args.loudness - 9 and vi is not None and li is not None and li - vi <= 1.0,
          "bed %.0f LUFS; the mix is %+.2f LU against the voice alone" % (level, (li - vi) if (li is not None and vi is not None) else 0),
          "bed at least 9 LU under the voice, and adding 1.0 LU at most")
check("Loudness", li is not None and abs(li - args.loudness) <= 1.2, "%s LUFS, peak %s dB" % (li, after["input_tp"] if after else "?"), "%.0f LUFS ± 1.2" % args.loudness)
r = subprocess.run([tool("ffmpeg"), "-hide_banner", "-nostats", "-i", final, "-map", "0:v:0", "-vf", "scale=180:-2,blackdetect=d=0.06:pix_th=0.08",
                    "-an", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
blacks = [(float(a), float(b)) for a, b in re.findall(r"black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)", r.stderr)]
check("Black frames", not blacks, "%d run(s)%s" % (len(blacks), "" if not blacks else ": " + ", ".join("%.2f-%.2f" % b for b in blacks[:6])),
      "none (a voiceover stretch with no scene, or a render that painted black)")

# a sheet from the rendered file at the storyboard moments: what was delivered, not what was planned
mp = os.path.join(P, "moments.json")
ts = [m["t"] for m in load(mp)["moments"]] if os.path.exists(mp) else [D * k / 12 for k in range(12)]
ts = ts[:: max(1, len(ts) // 18)][:18]
tmp = os.path.join(P, "_sheet")
shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
for i, t in enumerate(ts):
    ffmpeg(["-ss", "%.3f" % t, "-i", final, "-frames:v", "1", "-vf", "scale=270:480", os.path.join(tmp, "f_%03d.png" % i)], check=False)
n = len(glob.glob(os.path.join(tmp, "f_*.png")))
if n:
    ffmpeg(["-start_number", "0", "-i", os.path.join(tmp, "f_%03d.png"), "-frames:v", "1", "-vf", "tile=6x%d:padding=6" % ((n + 5) // 6),
            os.path.join(P, "render-sheet.png")], check=False)
shutil.rmtree(tmp, ignore_errors=True)

md = ["# Verify: %s" % name, "", "| Check | Result | Got | Needs |", "|---|---|---|---|"] + rows + ["", "Sheet from the rendered file: render-sheet.png", ""]
with open(os.path.join(P, "VERIFY.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print("\n".join(rows))
if fails:
    sys.exit("VERIFY: %d FAIL. Not delivered. See %s" % (fails, os.path.join(P, "VERIFY.md")))

# ---- deliver ------------------------------------------------------------------------------------------------
dest = args.deliver if args.deliver else (os.path.dirname(os.path.abspath(P)) if IN_WORK else os.path.join("renders", name))
os.makedirs(dest, exist_ok=True)
v = 1 + max([int(m.group(1)) for f in os.listdir(dest) for m in [re.search(r"-v(\d+)\.mp4$", f)] if m] or [0])
out_mp4 = os.path.join(dest, "%s-v%d.mp4" % (name, v))
shutil.copyfile(final, out_mp4)
# The .srt never sits next to the MP4: media players auto-load a subtitle file with the video's name and draw it over the
# captions already burnt into the picture (the creator saw "two captions" on the first delivery). It goes in extras/.
extras = os.path.join(dest, "extras")
os.makedirs(extras, exist_ok=True)
for src, ext in ((os.path.join(P, "captions.srt"), ".captions.srt"), (os.path.join(P, "VERIFY.md"), ".verify.md")):
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(extras, "%s-v%d%s" % (name, v, ext)))
print("DELIVERED %s  (%.1f MB, %dx%d, %.1f s)" % (out_mp4, os.path.getsize(out_mp4) / 1e6, want[0], want[1], vd))
