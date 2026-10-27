#!/usr/bin/env python3
"""snap.py: a still of every moment that matters, tiled into one contact sheet (Checkpoint B).

compose.py writes moments.json: every beat a second after it enters, every state inside a beat (each list item,
a count landing, a typed line, a scroll), and a spread of captions. This takes them all in ONE browser session
and tiles them, each tile stamped with its time and label. A snapshot is seconds; a render is minutes. Read the
sheet before rendering, and open any single frame at full size when something looks off.

Usage:
  python snap.py --project videos/<p> [--at 12.3 --at 20] [--only-at] [--cols 6]
Writes <p>/snaps/at-<t>.png (1080x1920) and <p>/snaps/sheet.png (sheet-2.png ... when there are many).
"""
import argparse, glob, math, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import npx, ffmpeg, load, tool

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--at", action="append", default=[], type=float)
ap.add_argument("--only-at", action="store_true", help="only the --at times (a fix round)")
ap.add_argument("--cols", type=int, default=6)
ap.add_argument("--per-sheet", type=int, default=24)
args = ap.parse_args()

P = args.project
pub = os.path.join(P, "public")
mp = os.path.join(P, "moments.json")
M = load(mp) if os.path.exists(mp) else {"duration": 1e9, "moments": []}
moments = [] if args.only_at else list(M["moments"])
moments += [{"t": round(t, 2), "label": "asked"} for t in args.at]
moments = sorted({m["t"]: m for m in moments}.values(), key=lambda m: m["t"])
if not moments:
    sys.exit("nothing to snapshot: run compose.py first, or pass --at")

snapdir = os.path.join(P, "snaps")
os.makedirs(snapdir, exist_ok=True)
if not args.only_at:
    for f in glob.glob(os.path.join(snapdir, "*.png")):
        os.remove(f)
tmp = os.path.join(P, "snaps", "_raw")
shutil.rmtree(tmp, ignore_errors=True)

r = npx(["hyperframes", "snapshot", pub, "--at", ",".join("%.2f" % m["t"] for m in moments), "--no-end", "--describe", "false", "-o", tmp],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
shots = sorted(glob.glob(os.path.join(tmp, "*.png")))
if r.returncode or not shots:
    sys.exit("snapshot failed:\n" + ((r.stdout or "") + (r.stderr or ""))[-1200:])


def at_of(path):       # frame-03-at-8.5s.png
    m = re.search(r"-at-([\d.]+)s", os.path.basename(path))
    return float(m.group(1)) if m else None


by_t = {}
for s in shots:
    t = at_of(s)
    if t is not None:
        by_t[round(t, 2)] = s
outs = []
for i, m in enumerate(moments):
    src = by_t.get(m["t"]) or (shots[i] if i < len(shots) else None)
    if not src:
        print("no frame for %.2f s" % m["t"]); continue
    dst = os.path.join(snapdir, "at-%06.2f.png" % m["t"])
    shutil.copyfile(src, dst)
    outs.append((dst, m))
shutil.rmtree(tmp, ignore_errors=True)

# ---- contact sheets: 270x480 tiles, time and label burnt in --------------------------------------------------
font = next((f for f in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
                         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") if os.path.exists(f)), None)
tiles = os.path.join(snapdir, "_tiles")
os.makedirs(tiles, exist_ok=True)
for i, (png, m) in enumerate(outs):
    vf = "scale=270:480"
    if font:
        label = re.sub(r"[^A-Za-z0-9 ._-]", "", "%.2fs %s" % (m["t"], m["label"]))[:30]
        fpath = font.replace("\\", "/").replace(":", "\\:")
        vf += ",drawtext=fontfile='%s':text='%s':x=8:y=8:fontsize=17:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=5" % (fpath, label)
    ffmpeg(["-i", png, "-vf", vf, os.path.join(tiles, "t_%03d.png" % i)])
n = len(outs)
sheets = []
for k in range(0, n, args.per_sheet):
    cnt = min(args.per_sheet, n - k)
    rows = math.ceil(cnt / args.cols)
    out = os.path.join(snapdir, "sheet.png" if k == 0 else "sheet-%d.png" % (k // args.per_sheet + 1))
    ffmpeg(["-start_number", str(k), "-i", os.path.join(tiles, "t_%03d.png"), "-frames:v", "1",
            "-vf", "tile=%dx%d:padding=6:color=0x222222" % (min(args.cols, cnt), rows), out])
    sheets.append(out)
shutil.rmtree(tiles, ignore_errors=True)
print("%d frames -> %s" % (n, ", ".join(sheets)))
print("CHECKPOINT B: read the sheet(s). Full-size frames: %s" % os.path.join(snapdir, "at-<t>.png"))
