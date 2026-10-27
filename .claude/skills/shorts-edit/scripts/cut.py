#!/usr/bin/env python3
"""cut.py: the cut stage in two commands, with Checkpoint A between them.

  python cut.py plan  videos/<p>     transcribe the source, find where you speak, write cut-list.json + PAPER-CUT.md
  ... read PAPER-CUT.md; fix misreads with hand-cut.py / patch-cut.py; the creator says yes (Checkpoint A) ...
  python cut.py apply videos/<p>     tighten, audit every edge by the audio, encode the flat cut, re-transcribe,
                                     remove dead air until none is left, then prove no kept word was lost

plan runs the paper cut once per recorded input (prep.py's source-map.json), so a face-cam line is never mistaken
for a retake of a voiceover line. apply runs the same chain the long-form kit runs by hand:
tighten-cut -> sliver --fix -> edge-audit --fix -> edge-audit (0 issues) -> apply-cut -> transcribe -> dead-air
-> patch-cut --drop-flat -> edge-audit -> apply-cut -> transcribe -> ... until dead-air proposes nothing.

Options for apply:
  --keep-pause T     flat-cut time of a pause to leave alone (a deliberate beat); repeatable
  --maxgap 0.30      the longest inner silence tighten-cut leaves inside a kept stretch
  --max-pause 0.45 / --max-sentence 0.40 / --target 0.30    the dead-air limits (Shorts run tight; raise for a calm piece)
  --rounds 4         dead-air passes at most
Writes: public/input-video.mp4, cut-map.json, audio.wav, transcript.json (flat-cut time), spans.json (cam / vo), CUT-REPORT.md
"""
import argparse, difflib, json, os, re, shutil, subprocess, sys, tempfile, wave
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import tool, tool_env, ffmpeg, load, save, words_of, spans_from_maps, duration

ap = argparse.ArgumentParser()
ap.add_argument("stage", choices=["plan", "apply"])
ap.add_argument("folder")
ap.add_argument("--keep-pause", type=float, action="append", default=[])
ap.add_argument("--maxgap", type=float, default=0.30)
ap.add_argument("--max-pause", type=float, default=0.45)
ap.add_argument("--max-sentence", type=float, default=0.40)
ap.add_argument("--target", type=float, default=0.30)
ap.add_argument("--rounds", type=int, default=4)
ap.add_argument("--no-dead-air", action="store_true")
args = ap.parse_args()

W = args.folder
P = lambda *a: os.path.join(W, *a)
ENV = tool_env()
SRC = P("source.mp4")
if not os.path.exists(SRC):
    sys.exit("no %s: run prep.py first" % SRC)


def py(script, *a, check=True, quiet=False):
    r = subprocess.run([sys.executable, os.path.join(HERE, script)] + [str(x) for x in a], env=ENV, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    if not quiet and out.strip():
        print("\n".join("    " + l for l in out.strip().splitlines()[-12:]))
    if check and r.returncode:
        sys.exit("%s failed (exit %d)" % (script, r.returncode))
    return r.returncode, out


def step(msg):
    print("== " + msg, flush=True)


# ============================================================ plan ============================================
if args.stage == "plan":
    D = duration(SRC)
    if not os.path.exists(P("audio-raw.wav")):
        ffmpeg(["-i", SRC, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", P("audio-raw.wav")])
    if not os.path.exists(P("transcript-raw.json")) or os.path.getmtime(P("transcript-raw.json")) < os.path.getmtime(SRC):
        step("transcribing the source (Parakeet)")
        py("transcribe.py", "--audio", P("audio-raw.wav"), "--out", P("transcript-raw.json"))
    step("finding speech by the audio (auto-editor)")
    ae = shutil.which("auto-editor") or "auto-editor"
    r = subprocess.run([ae, SRC, "--edit", "audio:-30dB", "--margin", "0.12s,0.35s", "--export", "v1", "-o", P("speech.v1")],
                       env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not os.path.exists(P("speech.v1")):
        sys.exit("auto-editor failed: pip install auto-editor\n" + (r.stderr or "")[-400:])

    words = load(P("transcript-raw.json"))
    words = words["words"] if isinstance(words, dict) else words
    smap = load(P("source-map.json")) if os.path.exists(P("source-map.json")) else {
        "segments": [{"kind": "cam", "file": "source.mp4", "start": 0.0, "end": D}]}
    kept, removed, md = [], [], ["# Paper cut", ""]
    step("paper cut, one pass per recorded input")
    for i, seg in enumerate(smap["segments"]):
        sub = [w for w in words if seg["start"] - 0.05 <= float(w["start"]) < seg["end"] - 0.05]
        head = "## %d. %s  %s  (source %.2f to %.2f s)" % (i + 1, seg["kind"], os.path.basename(seg["file"]), seg["start"], seg["end"])
        if not sub:
            md += [head, "", "(no speech found)", ""]
            continue
        tmp = tempfile.mkdtemp(prefix="se-pc-", dir=W)
        try:
            save(os.path.join(tmp, "t.json"), sub)
            py("paper-cut.py", "--transcript", os.path.join(tmp, "t.json"), "--duration", "%.3f" % seg["end"],
               "--out-dir", tmp, "--speech", P("speech.v1"), quiet=True)
            cl = load(os.path.join(tmp, "cut-list.json"))
            body = open(os.path.join(tmp, "PAPER-CUT.md"), encoding="utf-8").read().split("\n", 2)[-1].strip()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        for k in cl["kept"]:
            a, b = max(k["start"], seg["start"]), min(k["end"], seg["end"])
            if b - a >= 0.2:
                kept.append({"start": round(a, 3), "end": round(b, 3)})
        removed += cl["removed"]
        md += [head, "", body, ""]
    kept.sort(key=lambda k: k["start"])
    total = sum(k["end"] - k["start"] for k in kept)
    save(P("cut-list.json"), {"source_duration": round(D, 3), "kept_seconds": round(total, 2), "kept": kept,
                              "removed": sorted(removed, key=lambda r: r["start"])})
    md.insert(2, "Source %.1f s -> kept %.1f s in %d stretches. ~~Struck through~~ = removed, with the reason in brackets.\n"
                 "Times are source seconds. Fix a misread with hand-cut.py (--keep A-B per kept line) or patch-cut.py (--add / --drop).\n"
              % (D, total, len(kept)))
    with open(P("PAPER-CUT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("CHECKPOINT A: read %s (kept %.1f s of %.1f s). Then: python cut.py apply %s" % (P("PAPER-CUT.md"), total, D, W))
    if total > 180:
        print("WARN the kept speech runs %.0f s: a Short is 3 minutes at most" % total)
    sys.exit(0)

# ============================================================ apply ===========================================
for need in ("cut-list.json", "transcript-raw.json", "audio-raw.wav"):
    if not os.path.exists(P(need)):
        sys.exit("no %s: run `cut.py plan` first" % P(need))
os.makedirs(P("public"), exist_ok=True)
report = ["# Cut report", ""]


def room_floor(path):
    """The level of the room between words (10 ms RMS, 16-bit): the 8th percentile of the whole file."""
    import numpy as np
    w = wave.open(path)
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    fr = w.getframerate() // 100
    n = len(x) // fr
    return float(np.percentile(np.sqrt((x[: n * fr].reshape(n, fr) ** 2).mean(axis=1)), 8)) if n else 0.0


# The audio checks were tuned on a quiet studio (room floor ~5 RMS). A phone in a real room sits at 100 to 400 even after
# the denoise, and at the stock thresholds every frame counts as "sound": nothing is tightened and every edge "starts mid-word".
# So the thresholds follow the room that was actually recorded.
FLOOR = room_floor(P("audio-raw.wav"))
TH_TIGHT = max(40.0, FLOOR * 1.6)
TH_QUIET = max(80.0, FLOOR * 1.5)
TH_SPEECH = max(300.0, FLOOR * 4.0)
print("room floor %.0f RMS -> sound over %.0f, quiet under %.0f, speech over %.0f" % (FLOOR, TH_TIGHT, TH_QUIET, TH_SPEECH))
report += ["Room floor %.0f RMS (thresholds: sound %.0f, quiet %.0f, speech %.0f)." % (FLOOR, TH_TIGHT, TH_QUIET, TH_SPEECH), ""]


def audit():
    py("sliver.py", "--cut-list", P("cut-list.json"), "--audio", P("audio-raw.wav"), "--fix", quiet=True)
    py("edge-audit.py", "--audio", P("audio-raw.wav"), "--cut-list", P("cut-list.json"), "--transcript", P("transcript-raw.json"),
       "--threshold", "%.0f" % TH_SPEECH, "--fix", quiet=True, check=False)
    _, out = py("edge-audit.py", "--audio", P("audio-raw.wav"), "--cut-list", P("cut-list.json"), "--transcript", P("transcript-raw.json"),
                "--threshold", "%.0f" % TH_SPEECH, quiet=True, check=False)
    m = re.search(r"(\d+) issues?", out)
    n = int(m.group(1)) if m else -1
    return n, out


def encode():
    code, out = py("apply-cut.py", "--input", SRC, "--cut-list", P("cut-list.json"), "--out", P("public", "input-video.mp4"), check=False)
    if code == 2:
        sys.exit("apply-cut reported DRIFT: do not dress this file. Re-run prep.py (the source must be constant 30 fps).")
    if code:
        sys.exit("apply-cut failed")
    ffmpeg(["-i", P("public", "input-video.mp4"), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", P("audio.wav")])
    py("transcribe.py", "--audio", P("audio.wav"), "--out", P("transcript.json"), quiet=True)


step("tighten by the sound")
py("tighten-cut.py", "--audio", P("audio-raw.wav"), "--cut-list", P("cut-list.json"), "--out", P("cut-list.json"),
   "--maxgap", args.maxgap, "--threshold", "%.0f" % TH_TIGHT, quiet=True)
step("audit every edge by the audio")
n_issues, audit_out = audit()
print("    edge audit: %s" % ("0 issues" if n_issues == 0 else audit_out.strip().splitlines()[-1] if audit_out.strip() else "?"))
step("encode the flat cut and transcribe it")
encode()

rounds = 0
if not args.no_dead_air:
    while rounds < args.rounds:
        a = ["dead-air.py", W, "--plan", "--max", args.max_pause, "--max-sentence", args.max_sentence, "--target", args.target,
             "--speech", "%.0f" % TH_SPEECH, "--quiet", "%.0f" % TH_QUIET]
        for k in args.keep_pause:
            a += ["--keep", k]
        _, out = py(*a, quiet=True, check=False)
        plan = re.search(r"^PLAN (.*)$", out, re.M)
        drops = re.findall(r"--drop-flat ([\d.]+-[\d.]+)", plan.group(1)) if plan else []
        if not drops:
            break
        rounds += 1
        step("dead air, pass %d: %d pause(s) to shorten" % (rounds, len(drops)))
        pa = ["patch-cut.py", "--cut-list", P("cut-list.json"), "--cut-map", P("cut-map.json")]
        for d in drops:
            pa += ["--drop-flat", d]
        py(*pa, quiet=True)
        n_issues, audit_out = audit()
        encode()
    _, out = py("dead-air.py", W, "--max", args.max_pause, "--max-sentence", args.max_sentence, "--target", args.target,
                "--speech", "%.0f" % TH_SPEECH, "--quiet", "%.0f" % TH_QUIET, quiet=True, check=False)
    first = out.strip().splitlines()[0] if out.strip() else ""
    print("    " + first)
    report += ["Dead air: %d pass(es). %s" % (rounds, first), ""]

# ---- spans: where the face is on screen, in flat-cut time -------------------------------------------------
cm = load(P("cut-map.json"))
if os.path.exists(P("source-map.json")):
    spans = spans_from_maps(load(P("source-map.json")), cm)
else:
    spans = [{"kind": "cam", "start": 0.0, "end": cm["flat_duration"]}]
save(P("spans.json"), spans)

# ---- proof: every word the cut meant to keep is still said ------------------------------------------------
norm = lambda s: re.sub(r"[^a-z0-9$%']+", "", s.lower())
raw = words_of(P("transcript-raw.json"))
cl = load(P("cut-list.json"))
def is_kept(w):   # by overlap, not by start: Parakeet marks a phrase start up to 0.4 s early and stretches a last word into the pause
    need = min(0.05, 0.4 * max(0.02, w["end"] - w["start"]))
    return any(min(w["end"], k["end"]) - max(w["start"], k["start"]) >= need for k in cl["kept"])
meant = [norm(w["text"]) for w in raw if is_kept(w)]
flat = words_of(P("transcript.json"))
got = [norm(w["text"]) for w in flat]
meant, got_n = [m for m in meant if m], [g for g in got if g]
lost, extra, differ = [], [], []
for op, i0, i1, j0, j1 in difflib.SequenceMatcher(None, meant, got_n, autojunk=False).get_opcodes():
    if op == "delete" or (op == "replace" and i1 - i0 > j1 - j0):
        lost.append(" ".join(meant[i0:i1]) + (" (heard: %s)" % " ".join(got_n[j0:j1]) if op == "replace" else ""))
    elif op == "replace":
        differ.append("%s -> %s" % (" ".join(meant[i0:i1]), " ".join(got_n[j0:j1])))
    elif op == "insert":
        extra.append(" ".join(got_n[j0:j1]))
# the same 3 or 4 word phrase twice within 7 s: a retake said without a pause that the paper cut could not see
rep = []
for n in (4, 3):
    seen = {}
    for i in range(len(flat) - n + 1):
        key = " ".join(norm(w["text"]) for w in flat[i:i + n])
        t = flat[i]["start"]
        if key in seen and 0.3 < t - seen[key] < 7.0 and not any(abs(t - r[0]) < 1.5 for r in rep):
            rep.append((t, key))
        seen[key] = t

D = cm["flat_duration"]
report += ["Flat cut: %.2f s, %d jump cuts. Edge audit: %s." % (D, len(cm["cuts"]), "0 issues" if n_issues == 0 else "%d issue(s), listen to them" % n_issues), "",
           "Spans: " + ", ".join("%s %.2f-%.2f" % (s["kind"], s["start"], s["end"]) for s in spans), ""]
if lost:
    report += ["## Words the cut meant to keep that the flat cut does not say (check each join by ear)", ""] + ["- " + l for l in lost] + [""]
if rep:
    report += ["## The same phrase twice within 7 s (a retake without a pause? remove the earlier one with patch-cut --drop-flat)", ""] + \
              ["- %.2f s  \"%s\"" % r for r in sorted(rep)] + [""]
if differ:
    report += ["## Transcribed differently in the flat cut (listed, not a failure; fix the spelling in captions.replace)", ""] + ["- " + e for e in differ] + [""]
if extra:
    report += ["## Heard in the flat cut but not counted as kept (usually the first word after a pause, which Parakeet times early; a word you did NOT mean to keep here is a leaked retake)", ""] + ["- " + e for e in extra] + [""]
with open(P("CUT-REPORT.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(report) + "\n")

print("flat cut: %s  %.2f s, %d jump cuts, %d words" % (P("public", "input-video.mp4"), D, len(cm["cuts"]), len(flat)))
print("spans: " + ", ".join("%s %.1f-%.1f" % (s["kind"], s["start"], s["end"]) for s in spans))
print("edge audit: %s | lost words: %d | repeated phrases: %d  -> %s" % ("0 issues" if n_issues == 0 else "%d ISSUES" % n_issues,
                                                                       len(lost), len(rep), P("CUT-REPORT.md")))
if D > 180:
    print("WARN %.0f s: a Short is 3 minutes at most" % D)
if n_issues or lost or rep:
    sys.exit(3)
