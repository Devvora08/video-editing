#!/usr/bin/env python3
"""clean-audio.py: only the voice gets through. Speech isolation (DeepFilterNet) and a light polish, for any recording.

A phone or a lav mic in a real room records the room too: fans, wind, hiss, hum. This removes it and then makes the
voice clearer, in two stages:
  1. isolate   DeepFilterNet (deep-filter.exe, CPU, 48 kHz full band) separates speech from everything else.
               --strength is how many dB the noise is pushed down. 30 is the house setting: the room is gone to the ear
               and the voice keeps its body. 100 removes everything it can and starts to sound processed.
  2. polish    a low cut at 80 Hz (rumble, handling thumps), a small cut around 250 Hz (boxiness), a de-esser,
               a presence lift around 3.5 kHz (clarity: the "sharper" voice), gentle 2.5:1 compression so quiet
               words do not fall away, then level to --lufs with a true-peak ceiling.

Usage:
  python clean-audio.py --in voiceover.m4a --out voiceover-clean.wav            (audio in, audio out)
  python clean-audio.py --in face.mp4 --out face-clean.wav                      (takes the sound of a video)
  options: --strength 30   --no-polish   --lufs -16   --presence 2.5 (dB)
prep.py runs this on every input by default. It cannot repair clipping (a mic too close or too hot) or wind
hitting the capsule directly: those are distortion, not noise. Fix them at the source (gain down, a foam windscreen).
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import tool, ffmpeg


def deep_filter():
    env = os.environ.get("DEEP_FILTER_PATH")
    for cand in (env, shutil.which("deep-filter"), r"D:\devtools\deepfilter\deep-filter.exe"):
        if cand and os.path.exists(cand):
            return cand
    return None


def floor_and_speech(path):
    """(room floor, speech level) in dBFS from 10 ms frames: the 8th and 90th percentile."""
    import numpy as np
    w = wave.open(path)
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    if w.getnchannels() > 1:
        x = x.reshape(-1, w.getnchannels()).mean(axis=1)
    fr = w.getframerate() // 100
    n = len(x) // fr
    r = np.sqrt((x[: n * fr].reshape(n, fr) ** 2).mean(axis=1)) + 1e-9
    db = lambda v: 20 * np.log10(v / 32768.0)
    return float(db(np.percentile(r, 8))), float(db(np.percentile(r, 90)))


def clean(src, out, strength=30.0, polish=True, lufs=-16.0, presence=2.5, t0=None, t1=None, quiet=False):
    """Clean one file (optionally only [t0, t1] of it) into a 48 kHz stereo WAV. Returns a small report dict."""
    exe = deep_filter()
    tmp = tempfile.mkdtemp(prefix="se-clean-", dir=os.path.dirname(os.path.abspath(out)) or ".")
    try:
        raw = os.path.join(tmp, "in.wav")
        cut = (["-ss", "%.3f" % t0] if t0 is not None else []) + (["-t", "%.3f" % (t1 - t0)] if t1 is not None and t0 is not None else [])
        ffmpeg(cut + ["-i", src, "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", raw])
        before = floor_and_speech(raw)
        iso = raw
        if exe:
            od = os.path.join(tmp, "df")
            r = subprocess.run([exe, "-D", "-a", "%g" % strength, "-o", od, raw], capture_output=True, text=True, encoding="utf-8", errors="replace")
            cand = os.path.join(od, "in.wav")
            if r.returncode or not os.path.exists(cand):
                print("WARN deep-filter failed, falling back to the FFmpeg denoiser: %s" % (r.stderr or r.stdout)[-300:])
                exe = None
            else:
                iso = cand
        chain = []
        if not exe:      # no DeepFilterNet on this machine: the FFT denoiser is weaker but better than nothing
            chain.append("afftdn=nr=12:nf=-40")
        if polish:
            chain += ["highpass=f=80", "equalizer=f=250:t=q:w=1.0:g=-2", "deesser=i=0.35:m=0.5:f=0.5",
                      "equalizer=f=3500:t=q:w=1.2:g=%.1f" % presence, "acompressor=threshold=-21dB:ratio=2.5:attack=8:release=140:makeup=1"]
        pre = ",".join(chain) + "," if chain else ""
        m = subprocess.run([tool("ffmpeg"), "-hide_banner", "-nostats", "-i", iso, "-af", pre + "loudnorm=I=%.1f:TP=-1.5:LRA=11:print_format=json" % lufs,
                            "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        j = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", m.stderr, re.S)
        ms = json.loads(j.group(0)) if j else None
        norm = "anull"
        if ms and ms["input_i"] not in ("-inf", "inf"):
            norm = ("loudnorm=I=%.1f:TP=-1.5:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true"
                    % (lufs, ms["input_i"], ms["input_tp"], ms["input_lra"], ms["input_thresh"], ms["target_offset"]))
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        ffmpeg(["-i", iso, "-af", pre + norm + ",alimiter=limit=0.84:level=disabled", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", out])
        after = floor_and_speech(out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    rep = {"engine": "DeepFilterNet" if exe else "ffmpeg afftdn (DeepFilterNet not installed)", "strength": strength,
           "floor_before": round(before[0], 1), "speech_before": round(before[1], 1), "floor_after": round(after[0], 1), "speech_after": round(after[1], 1)}
    if not quiet:
        print("%s -> %s  [%s, strength %g dB]" % (os.path.basename(src), out, rep["engine"], strength))
        print("  room under the voice: %.0f dB before, %.0f dB after   (voice %.0f dB above the room -> %.0f dB above)"
              % (before[0], after[0], before[1] - before[0], after[1] - after[0]))
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strength", type=float, default=30.0, help="dB of noise reduction (30 = house setting, 100 = everything)")
    ap.add_argument("--no-polish", action="store_true")
    ap.add_argument("--lufs", type=float, default=-16.0)
    ap.add_argument("--presence", type=float, default=2.5)
    a = ap.parse_args()
    if not deep_filter():
        print("NOTE DeepFilterNet is not installed (expected D:\\devtools\\deepfilter\\deep-filter.exe, or set DEEP_FILTER_PATH): using the weaker FFmpeg denoiser")
    clean(a.src, a.out, a.strength, not a.no_polish, a.lufs, a.presence)
