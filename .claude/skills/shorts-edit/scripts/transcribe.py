#!/usr/bin/env python3
"""transcribe.py: word-level transcript with Parakeet, safe on long takes.

Parakeet (through `npx hyperframes transcribe --engine parakeet`) can drop whole sentences on audio much over a
couple of minutes, and a raw take with retakes easily runs that long. So audio over --single seconds is split
into windows of about --window seconds, each cut in the middle of a real silence (never inside a word), each
transcribed on its own, and the word times shifted back and merged.

Usage:
  python transcribe.py --audio videos/<p>/audio-raw.wav --out videos/<p>/transcript-raw.json
  python transcribe.py --audio videos/<p>/audio.wav     --out videos/<p>/transcript.json
The engine is always Parakeet, named explicitly: with "auto" a missing model falls back to whisper without a word.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import tool, ffmpeg, npx, duration, save, load

ap = argparse.ArgumentParser()
ap.add_argument("--audio", required=True, help="a 16 kHz mono WAV (prep.py and the cut stage write these)")
ap.add_argument("--out", required=True)
ap.add_argument("--single", type=float, default=100.0, help="transcribe in one go up to this many seconds")
ap.add_argument("--window", type=float, default=40.0)
args = ap.parse_args()

D = duration(args.audio)


def run(wav, workdir):
    r = npx(["hyperframes", "transcribe", wav, "-d", workdir, "--engine", "parakeet", "--json"], capture_output=True, text=True,
            encoding="utf-8", errors="replace")
    tp = os.path.join(workdir, "transcript.json")
    if r.returncode or not os.path.exists(tp):
        sys.exit("transcription failed (is Parakeet installed? npx hyperframes models install parakeet)\n" + (r.stderr or r.stdout)[-600:])
    raw = load(tp)
    return raw["words"] if isinstance(raw, dict) and "words" in raw else raw


def silences():
    r = subprocess.run([tool("ffmpeg"), "-hide_banner", "-nostats", "-i", args.audio, "-af", "silencedetect=noise=-32dB:d=0.28",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return [(a + b) / 2.0 for a, b in zip(st, en)]


tmp = tempfile.mkdtemp(prefix="se-tr-", dir=os.path.dirname(os.path.abspath(args.out)))
try:
    if D <= args.single:
        local = os.path.join(tmp, "a.wav"); shutil.copy(args.audio, local)
        words = run(local, tmp)
        n_win = 1
    else:
        mids = silences()
        cuts, t = [0.0], 0.0
        while D - t > args.window * 1.4:
            lo, hi = t + args.window * 0.6, t + args.window * 1.3
            cand = [m for m in mids if lo <= m <= hi]
            nxt = min(cand, key=lambda m: abs(m - (t + args.window))) if cand else t + args.window   # no silence: cut anyway
            cuts.append(nxt); t = nxt
        cuts.append(D)
        words = []
        for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
            wd = os.path.join(tmp, "w%02d" % i); os.makedirs(wd)
            wav = os.path.join(wd, "a.wav")
            ffmpeg(["-ss", "%.3f" % a, "-t", "%.3f" % (b - a), "-i", args.audio, "-ar", "16000", "-ac", "1", wav])
            for w in run(wav, wd):
                words.append({"text": w["text"], "start": round(float(w["start"]) + a, 3), "end": round(float(w["end"]) + a, 3)})
            print("  window %d/%d  %.1f-%.1f s" % (i + 1, len(cuts) - 1, a, b))
        n_win = len(cuts) - 1
finally:
    shutil.rmtree(tmp, ignore_errors=True)

words = [{"id": "w%d" % i, "text": w["text"], "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)}
         for i, w in enumerate(sorted(words, key=lambda w: float(w["start"])))]
save(args.out, words)
print("wrote %s: %d words over %.1f s (%d window%s)" % (args.out, len(words), D, n_win, "" if n_win == 1 else "s"))
if words and D - words[-1]["end"] > 20:
    print("WARN nothing transcribed after %.1f s of %.1f s: listen to the end of the file" % (words[-1]["end"], D))
