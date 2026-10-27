#!/usr/bin/env python3
"""prep.py: turn whatever was recorded into ONE vertical source file the cut stage can work on.

A Short is built from face-cam clips ("cam") and voiceover audio ("vo"), in the order they play. This joins them
into W/source.mp4: 9:16, 30 fps constant (phones record variable frame rate, which breaks frame-exact cuts), a
keyframe every second, the voice polished and level-matched across every input so a phone mic and a desk mic
sit at the same loudness. A voiceover becomes black picture under its audio: the composer covers those stretches
with full-frame scenes, and knows where they are from source-map.json.

Usage:
  python prep.py --out videos/<p> --in cam:raw/face.mp4 --in vo:raw/narration.m4a --in cam:raw/outro.mp4
  an input may carry a window in seconds:  cam:raw/face.mp4@12.5-48     (use only that part)
Options:
  --res auto|1080|2160   auto keeps 4K (2160x3840) when every cam clip is at least 2160 wide, else 1080x1920
  --focus 0.5            where the face sits across a LANDSCAPE clip (0 left, 1 right) when it is cropped to 9:16
  (default)              every input's sound goes through clean-audio.py first: DeepFilterNet speech isolation, then the
                         voice polish, levelled to the same loudness. Only the voice gets through.
  --strength 30          dB of noise reduction (30 = house setting; raise if the room is still audible, lower if the voice sounds processed)
  --no-clean             skip the isolation (studio audio); the old light chain applies instead (--denoise adds an FFT denoise)
  --no-polish            leave the audio alone entirely (already mastered)
Writes: W/source.mp4, W/source-map.json, W/audio-raw.wav (16 kHz mono, for the transcriber and the edge checks).
"""
import argparse, importlib.util, json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import tool, ffmpeg, probe, vstream, astream, display_size, save

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True, help="the video's working folder (videos/<project>)")
ap.add_argument("--in", dest="inputs", action="append", required=True, help="cam:FILE or vo:FILE, optionally @start-end")
ap.add_argument("--res", default="auto", choices=["auto", "1080", "2160"])
ap.add_argument("--focus", type=float, default=0.5)
ap.add_argument("--denoise", action="store_true")
ap.add_argument("--no-polish", action="store_true")
ap.add_argument("--no-clean", action="store_true")
ap.add_argument("--strength", type=float, default=30.0)
ap.add_argument("--target", type=float, default=-16.0, help="LUFS each input is levelled to (finish.py brings the master to -14)")
ap.add_argument("--crf", type=int, default=14)
args = ap.parse_args()

items = []
for spec in args.inputs:
    m = re.match(r"^(cam|vo):(.+?)(?:@([\d.]+)-([\d.]+))?$", spec)
    if not m:
        sys.exit('bad --in "%s": write cam:FILE or vo:FILE, optionally @start-end' % spec)
    kind, path, a, b = m.group(1), m.group(2), m.group(3), m.group(4)
    if not os.path.exists(path):
        sys.exit("no such file: %s" % path)
    info = probe(path)
    vs, as_ = vstream(info), astream(info)
    if as_ is None:
        sys.exit("%s has no audio track: the cut follows the voice, so every input needs one" % path)
    if kind == "cam" and vs is None:
        sys.exit("%s is marked cam but has no picture; mark it vo:" % path)
    full = float(info["format"]["duration"])
    t0 = float(a) if a else 0.0
    t1 = min(float(b), full) if b else full
    items.append({"kind": kind, "file": path, "t0": t0, "t1": t1, "vs": vs if kind == "cam" else None})

# ---- output size --------------------------------------------------------------------------------------
cams = [it for it in items if it["kind"] == "cam"]
if args.res == "auto":
    short_sides = [min(display_size(it["vs"])) for it in cams]
    res = 2160 if short_sides and min(short_sides) >= 2160 else 1080
else:
    res = int(args.res)
W, H = res, res * 16 // 9

# ---- loudness: measure each input once, then apply a linear gain (two-pass loudnorm) --------------------
def measure(it, chain):
    r = subprocess.run([tool("ffmpeg"), "-hide_banner", "-nostats", "-ss", "%.3f" % it["t0"], "-t", "%.3f" % (it["t1"] - it["t0"]),
                        "-i", it["file"], "-vn", "-af", chain + "loudnorm=I=%.1f:TP=-1.5:LRA=11:print_format=json" % args.target,
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    return json.loads(m.group(0)) if m else None

CLEAN = not (args.no_clean or args.no_polish)
if CLEAN:
    spec_ = importlib.util.spec_from_file_location("clean_audio", os.path.join(os.path.dirname(os.path.abspath(__file__)), "clean-audio.py"))
    clean_audio = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(clean_audio)
    os.makedirs(os.path.join(args.out, "_clean"), exist_ok=True)
    if not clean_audio.deep_filter():
        print("NOTE DeepFilterNet is not installed: the weaker FFmpeg denoiser is used (see SKILL.md, Setup check)")
pre = "highpass=f=70," + ("afftdn=nr=10:nf=-40," if args.denoise else "")
for n_, it in enumerate(items):
    if CLEAN:       # isolate the voice of exactly the window this input contributes, already levelled to the target
        it["clean"] = os.path.join(args.out, "_clean", "in%02d.wav" % n_)
        rep = clean_audio.clean(it["file"], it["clean"], strength=args.strength, lufs=args.target, t0=it["t0"], t1=it["t1"], quiet=True)
        it["af"], it["clean_report"] = "anull", rep
        print("  cleaned %s %.1f-%.1f s [%s]: voice %.0f dB above the room -> %.0f dB" % (os.path.basename(it["file"]), it["t0"], it["t1"], rep["engine"],
              rep["speech_before"] - rep["floor_before"], rep["speech_after"] - rep["floor_after"]))
        continue
    if args.no_polish:
        it["af"] = "anull"
        continue
    ms = measure(it, pre)
    if not ms or ms.get("input_i") in ("-inf", "inf"):
        it["af"] = pre.rstrip(",") or "anull"       # silence or unreadable: leave the level alone
        print("  %s: could not measure loudness, level left alone" % os.path.basename(it["file"]))
        continue
    it["lufs_in"] = float(ms["input_i"])
    it["af"] = (pre + "loudnorm=I=%.1f:TP=-1.5:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true"
                % (args.target, ms["input_i"], ms["input_tp"], ms["input_lra"], ms["input_thresh"], ms["target_offset"]))

# ---- one filter graph, one encode -----------------------------------------------------------------------
cmd, chain, parts, segs = [], [], [], []
t = 0.0
n_in = 0
for i, it in enumerate(items):
    d = it["t1"] - it["t0"]
    cmd += ["-ss", "%.3f" % it["t0"], "-t", "%.3f" % d, "-i", it["file"]]
    ai = n_in; n_in += 1
    if it["kind"] == "cam":
        vs = it["vs"]
        dw, dh = display_size(vs)
        # fill 9:16: a vertical clip is scaled, a landscape one is cropped around --focus
        fx = "(iw-%d)*%.3f" % (W, args.focus)
        vf = "scale=%d:%d:force_original_aspect_ratio=increase:flags=lanczos,crop=%d:%d:%s:(ih-%d)/2" % (W, H, W, H, fx, H)
        hdr = vs.get("color_transfer") in ("arib-std-b67", "smpte2084")
        if hdr:   # phone HDR (HLG / PQ) looks grey and washed out when it is treated as SDR: tone-map it to BT.709 first
            vf = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
                  "zscale=t=bt709:m=bt709:r=tv,format=yuv420p," + vf)
            print("  %s is HDR (%s): tone-mapped to SDR" % (os.path.basename(it["file"]), vs.get("color_transfer")))
        chain.append("[%d:v]%s,fps=30,setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v%d]" % (ai, vf, i))
    else:
        cmd += ["-f", "lavfi", "-t", "%.3f" % d, "-i", "color=c=black:s=%dx%d:r=30" % (W, H)]
        chain.append("[%d:v]setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v%d]" % (n_in, i)); n_in += 1
    asrc = ai
    if it.get("clean"):                       # the cleaned sound replaces the input's own audio
        cmd += ["-i", it["clean"]]
        asrc = n_in; n_in += 1
    chain.append("[%d:a]aresample=48000,aformat=channel_layouts=stereo,%s,apad,atrim=0:%.3f,asetpts=PTS-STARTPTS[a%d]" % (asrc, it["af"], d, i))
    parts.append("[v%d][a%d]" % (i, i))
    segs.append({"kind": it["kind"], "file": it["file"].replace("\\", "/"), "start": round(t, 3), "end": round(t + d, 3),
                 "src_in": round(it["t0"], 3), "src_out": round(it["t1"], 3), "lufs_in": it.get("lufs_in"), "clean": it.get("clean_report")})
    t += d
chain.append("".join(parts) + "concat=n=%d:v=1:a=1[v][a]" % len(parts))

os.makedirs(args.out, exist_ok=True)
out = os.path.join(args.out, "source.mp4")
ffmpeg(cmd + ["-filter_complex", ";".join(chain), "-map", "[v]", "-map", "[a]", "-r", "30", "-fps_mode", "cfr",
              "-c:v", "libx264", "-preset", "fast", "-crf", str(args.crf), "-g", "30", "-keyint_min", "30", "-pix_fmt", "yuv420p",
              "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
              "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart+write_colr", out])
ffmpeg(["-i", out, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", os.path.join(args.out, "audio-raw.wav")])

real = float(probe(out)["format"]["duration"])
save(os.path.join(args.out, "source-map.json"), {"width": W, "height": H, "fps": 30, "duration": round(real, 3), "segments": segs})
kinds = sorted(set(s["kind"] for s in segs))
mode = "hybrid" if len(kinds) == 2 else ("animated" if kinds == ["vo"] else "cam")
print("wrote %s: %dx%d, %.2f s, %d input(s), mode %s" % (out, W, H, real, len(segs), mode))
for s in segs:
    print("  %-3s %7.2f - %7.2f  %s%s" % (s["kind"], s["start"], s["end"], os.path.basename(s["file"]),
                                          "  (%.1f LUFS in)" % s["lufs_in"] if s.get("lufs_in") is not None else ""))
if abs(real - t) > 0.1:
    print("WARN the file is %.2f s but the inputs add up to %.2f s: check source-map.json before cutting" % (real, t))
