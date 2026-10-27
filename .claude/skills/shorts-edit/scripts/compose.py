#!/usr/bin/env python3
"""compose.py: storyboard.json -> public/index.html, a 1080x1920 HyperFrames composition for a YouTube Short.

The storyboard is the review artifact AND the source of truth. Times are written as the WORDS they belong to:
any time field takes a number (seconds in the flat cut) or a spoken phrase, which is looked up in transcript.json.
  "in":  "three things"     the beat enters LEAD (0.20 s) before the first word of the phrase
  "out": "real product"     ... and leaves 0.45 s after the last word of this phrase;  "+4.5" = 4.5 s after "in"
  items: ["A mobile app", "first a mobile app"]     [text, phrase or seconds]; the item lands on that word
  "phrase#2" picks the second time it is said. Inside a beat, phrases are searched from the beat's "in" onward.

Usage:
  python compose.py --project videos/<p> [--shared videos/_shared]
Reads  <p>/storyboard.json, <p>/transcript.json, <p>/spans.json, <p>/cut-map.json
Writes <p>/public/index.html (+ fonts, vendor, sfx, img), <p>/captions.json, <p>/captions.srt, <p>/moments.json

storyboard.json
{
  "id": "day-07", "world": {"theme": "paper", "chrome": {"left": "Day 07", "right": "$0 → $1K MRR"}},
  "mood": "balanced",                      calm | balanced | punchy : how much sound, and how loud
  "overlay_top": 150,                      where cards sit over the face cam (the free space above the head)
  "frame": {"scale": 1.0, "y": 0, "origin": "50% 34%"},   base framing of the face cam; the camera zooms around origin
  "camera": "auto" | [["punch", t, 1.12], ["creep", t0, t1, 1.08], ["set", t, 1.0], ["release", t, 0.4]],
  "captions": { ... see CAPTIONS below ... },
  "beats": [ ... ],
  "cues": [["riser", "big reveal", 0.10]],              extra sounds: [name, time or phrase, volume]
  "raw_css": "", "raw_html": "", "raw_js": ""
}

OVERLAYS (sit over the face cam; ink cards, top of frame)        every beat: type, id, in, out, anchor (defaults to "in")
  {"type":"chip","text":"Day 07 · Building in public","dot":true}
  {"type":"title","lines":["From *$0*","to $1K a month"],"size":112}
  {"type":"card","kicker":"Who","title":"Dev Vora","sub":"Full-stack developer","icon":"code"}
  {"type":"list","kicker":"This week","items":[["A mobile app","mobile app"],["A backend","a backend"]],"marker":"dot|check|number"}
  {"type":"stat","kicker":"MRR goal","value":1000,"prefix":"$","sub":"a month","at":"one thousand"}
  {"type":"progress","label":"MRR","value":0,"goal":1000,"prefix":"$","goal_label":"$1K","day":7}
  {"type":"logo","src":"img/n8n.svg"}
  {"type":"pills","items":[["Next.js","next"],["Postgres","postgres"]]}
  {"type":"subscribe","title":"Follow the journey","sub":"A new build every day","tap":"subscribe","bell":"channel"}
SCENES (full frame, on paper or ink; they cover voiceover stretches and work as cutaways over the face cam)
  {"type":"statement","kicker":"Week one","lines":[["I shipped","i shipped"],["*three* things","three things"]],"sub":"..."}
  {"type":"number","kicker":"Backend","value":30,"suffix":"+","label":"microservices","at":"thirty"}
  {"type":"steps","kicker":"What shipped","items":[{"title":"Mobile app","sub":"iOS + Android","at":"mobile app"}, ...],"marker":"number|check"}
  {"type":"flow","nodes":[{"label":"Trigger","sub":"New order","icon":"bolt","at":"..."},{"label":"Paid","icon":"money","at":"...","payoff":true}]}
  {"type":"bars","title":"Hours a week","rows":[{"label":"By hand","value":10,"text":"10 h","at":".."},{"label":"Automated","value":0.5,"text":"30 min","hi":true,"at":".."}]}
  {"type":"browser","src":"img/site.png","domain":"filehubs.app","frame":"browser|phone","scroll":600,"callout":{"x":80,"y":300,"w":400,"h":120,"at":".."}}
  {"type":"terminal","title":"deploy","lines":[{"text":"$ npm run deploy","at":"..","type":true},{"text":"✓ 30 services live","at":"..","tone":"good"}]}
  {"type":"clip","src":"broll/desk.mp4","media_start":0,"label":"..."}        a video cutaway (stock, screen recording, a piece of the face cam)
  {"type":"image","src":"img/app.png","fit":"cover|card","label":"..."}
  {"type":"cta","photo":"img/profile.png","lines":["Got something","to *build?*"],"url":"devvora.dev","chips":["Inquiry","Discovery call"]}
  {"type":"raw","full":true,"theme":"paper","html":"...","js":"...","times":{"a":"phrase"}}     a scene built by hand (see SKILL.md)
  Scenes take "theme": "paper" | "ink" and "transition": "wipe" | "cut" | "none" (default: wipe when the look underneath differs).
  Any beat takes "sfx": false | "name" | {"name":..,"vol":..} to silence or replace its sound.

CAPTIONS (always on; built from transcript.json)
  {"style":"pill|bare", "y":1400, "max_chars":18, "max_words":4, "size":58, "case":"as-is|upper|lower",
   "replace":[{"say":"dev vora","show":"Dev Vora"}],            fix what the transcriber misheard, or merge words ("zero dollars" -> "$0")
   "emphasis":[{"say":"three things","color":"accent|money|good","italic":true}],   words that stay highlighted
   "breaks":["a real product"],  start a new caption at this phrase     "hide":[[t0,t1]]   no captions in this window
   "moves":[[t0,t1,1180]]}       move the caption line for a window (a card sits low)
"""
import argparse, glob, html as H, json, math, os, re, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import load, save, words_of

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True, help="the video's folder: videos/<project>")
ap.add_argument("--spec", help="storyboard file (default: <project>/storyboard.json)")
ap.add_argument("--shared", default="", help="a folder of reusable assets: img/* and sfx/* are copied into public/")
ap.add_argument("--lead", type=float, default=0.20, help="how far ahead of its word a beat enters")
args = ap.parse_args()

P = args.project
SKILL = os.path.dirname(HERE)
OUT = os.path.join(P, "public")
S = load(args.spec or os.path.join(P, "storyboard.json"))
os.makedirs(OUT, exist_ok=True)
CW, CH = 1080, 1920
warnings, errors = [], []


def warn(m): warnings.append(m)
def err(m): errors.append(m)


# ============================================================ style tokens (STYLE-GUIDE.md mirrors these) =====
TOKENS = {
    "paper": {"bg": "#f5f2ec", "card": "#fbf9f5", "raised": "#ece7dd", "fg": "#15130f", "soft": "#5b564c", "faint": "#8a8578",
              "line": "rgba(21,19,16,0.14)", "accent": "#1d2f6f", "accent-soft": "#e6e9f4", "on-accent": "#f5f2ec",
              "money": "#a8710a", "good": "#2f8f5b", "bad": "#b8402f",
              "accent2": "#1d2f6f", "panel": "rgba(21,19,15,.93)", "glow": "rgba(21,19,15,.12)", "b1": "transparent", "b2": "transparent", "b3": "transparent"},
    "ink":   {"bg": "#15130f", "card": "#1d1a15", "raised": "#2a2620", "fg": "#f0ede4", "soft": "#a7a297", "faint": "#726d62",
              "line": "rgba(240,237,228,0.16)", "accent": "#9fb0f0", "accent-soft": "rgba(159,176,240,0.16)", "on-accent": "#15130f",
              "money": "#ecb850", "good": "#62c890", "bad": "#f08070",
              "accent2": "#9fb0f0", "panel": "rgba(21,19,15,.93)", "glow": "rgba(0,0,0,.35)", "b1": "transparent", "b2": "transparent", "b3": "transparent"},
    # ---- the glass looks: a deep or bright field, three slow light blobs drifting behind frosted cards, gradient accents
    "aurora": {"bg": "#0a0720", "card": "rgba(255,255,255,.07)", "raised": "rgba(255,255,255,.12)", "fg": "#f6f3ff", "soft": "#beb6e0", "faint": "#7f76a8",
               "line": "rgba(255,255,255,.16)", "accent": "#ffffff", "accent2": "#e4dcff", "accent-soft": "rgba(255,255,255,.16)", "on-accent": "#14082a", "pop": "#e5368f",
               "money": "#ffd36e", "good": "#6ff0b4", "bad": "#ff6b7f", "panel": "rgba(18,11,46,.62)", "glow": "rgba(124,72,255,.35)",
               "b1": "#6a3cff", "b2": "#ff4fa3", "b3": "#13c3e8"},
    "dusk":   {"bg": "#170b12", "card": "rgba(255,240,230,.07)", "raised": "rgba(255,240,230,.12)", "fg": "#fff4ea", "soft": "#e2c4b6", "faint": "#9c7a70",
               "line": "rgba(255,230,210,.17)", "accent": "#ffffff", "accent2": "#ffe6cf", "accent-soft": "rgba(255,255,255,.16)", "on-accent": "#1f0d10", "pop": "#f0640f",
               "money": "#ffd36e", "good": "#8ef0a8", "bad": "#ff6b6b", "panel": "rgba(38,14,22,.62)", "glow": "rgba(255,94,126,.30)",
               "b1": "#ff5e3a", "b2": "#c2187a", "b3": "#ffb03b"},
    "bloom":  {"bg": "#fff5ee", "card": "rgba(255,255,255,.62)", "raised": "rgba(255,255,255,.8)", "fg": "#221238", "soft": "#5f4f78", "faint": "#a596bd",
               "line": "rgba(60,30,110,.13)", "accent": "#7b3dff", "accent2": "#ff4f8b", "accent-soft": "rgba(123,61,255,.12)", "on-accent": "#ffffff",
               "money": "#c27a00", "good": "#11a06a", "bad": "#e0384f", "panel": "rgba(255,255,255,.66)", "glow": "rgba(123,61,255,.22)",
               "b1": "#ffb3d1", "b2": "#bfa8ff", "b3": "#9ff0dc"},
}
GLASS = {"aurora", "dusk", "bloom"}
LIVE = "#ff5a4f"
FONT_DISPLAY = '"Fraunces", serif'
FONT_BODY = '"Geist", sans-serif'
FONT_MONO = '"Geist Mono", monospace'
EASE = "expo.out"            # the site's cubic-bezier(.16,1,.3,1): fast in, long settle
for theme, over in (S.get("tokens") or {}).items():
    TOKENS.setdefault(theme, {}).update(over)

# sound: what each kind of event plays by default, and how loud (0..1) before the mood scales it
SFX = {"wipe": ("whoosh-short", 0.13), "pop": ("pop", 0.20), "item": ("click-soft", 0.15), "land": ("ping", 0.12),
       "type": ("typing", 0.16), "tap": ("click", 0.22), "bell": ("notification", 0.12), "payoff": ("chime", 0.13),
       "hit": ("impact-bass-1", 0.16), "error": ("error", 0.12), "card": ("whoosh-short", 0.07), "line": ("click-soft", 0.09),
       "grow": ("sparkle", 0.06)}
MOODS = {"calm": (0.7, {"item", "card", "line"}), "balanced": (1.0, set()), "punchy": (1.15, set())}     # (volume scale, events dropped)

# ============================================================ inputs ==========================================
tpath = os.path.join(P, "transcript.json")
WORDS = words_of(tpath) if os.path.exists(tpath) else []
D = float(S.get("duration") or 0)
cm_path = os.path.join(P, "cut-map.json")
CUTMAP = load(cm_path) if os.path.exists(cm_path) else None
if not D:
    D = float(CUTMAP["flat_duration"]) if CUTMAP else (WORDS[-1]["end"] + 0.5 if WORDS else 0)
if not D:
    sys.exit('give "duration" in the storyboard (no cut-map.json or transcript.json to read it from)')
sp_path = os.path.join(P, "spans.json")
SPANS = load(sp_path) if os.path.exists(sp_path) else [{"kind": "vo" if S.get("mode") == "animated" else "cam", "start": 0.0, "end": D}]
SPANS[-1]["end"] = max(SPANS[-1]["end"], D)
VO = [(s["start"], s["end"]) for s in SPANS if s["kind"] == "vo"]
in_vo = lambda t: any(a - 1e-3 <= t < b - 1e-3 for a, b in VO)
WORLD = (S.get("world") or {}).get("theme", "aurora")
if WORLD not in TOKENS:
    print("ERROR world.theme %r: use %s" % (WORLD, ", ".join(TOKENS))); sys.exit(1)
# overlays over the face cam take the look's own frosted panel; the devvora looks keep their ink card
OVL = (S.get("world") or {}).get("overlay", WORLD if WORLD in GLASS else "ink")

# ---- screen layout: where the face cam sits and where the animations play -----------------------------------
#   full  : the face cam fills the frame, cards float above the head (the default)
#   split : animations on top, the face cam fills the bottom part edge to edge        (layout2.png)
#   inset : animations fill the screen, the face cam is a rounded card at the bottom  (layout1.png)
_L = S.get("layout") or "full"
_L = {"mode": _L} if isinstance(_L, str) else dict(_L)
LAYOUT = _L.get("mode", "full")
if LAYOUT not in ("full", "split", "inset"):
    print("ERROR layout %r: use full, split or inset" % LAYOUT); sys.exit(1)
if LAYOUT == "split":
    CAM = {"x": 0, "y": int(_L.get("top", 880)), "w": 1080, "h": 1920 - int(_L.get("top", 880)), "r": 0}
elif LAYOUT == "inset":
    _h = int(_L.get("height", 700))
    CAM = {"x": 56, "y": 1920 - _h - int(_L.get("bottom", 70)), "w": 968, "h": _h, "r": int(_L.get("radius", 44))}
else:
    CAM = {"x": 0, "y": 0, "w": 1080, "h": 1920, "r": 0}
# the animation area above the face cam: scene content is fitted inside it (the chrome line stays at the top)
AREA_TOP, AREA_BOT = 230, (CAM["y"] - (150 if LAYOUT == "inset" else 40))

norm = lambda s: re.sub(r"[^a-z0-9$%' ]+", " ", str(s).lower().replace("’", "'")).split()
FLAT = []      # (token, start, end, word index)
for wi, w in enumerate(WORDS):
    toks = norm(w["text"])
    for tk in toks:
        FLAT.append((tk, w["start"], w["end"], wi))


def find(phrase, after=0.0):
    """(start of the first word, end of the last word) of a spoken phrase; "phrase#2" = its second occurrence."""
    m = re.match(r"^(.*?)#(\d+)$", phrase.strip())
    nth = int(m.group(2)) if m else None
    p = norm(m.group(1) if m else phrase)
    if not p:
        return None
    hits = []
    for i in range(len(FLAT) - len(p) + 1):
        if all(FLAT[i + k][0] == p[k] for k in range(len(p))):
            hits.append((FLAT[i][1], FLAT[i + len(p) - 1][2]))
    if nth:
        return hits[nth - 1] if len(hits) >= nth else None
    later = [h for h in hits if h[0] >= after - 0.05]
    return later[0] if later else (hits[-1] if hits else None)


def isnum(x):
    if isinstance(x, (int, float)):
        return True
    return isinstance(x, str) and re.match(r"^\s*-?\d+(\.\d+)?\s*$", x) is not None


def when(spec, role="at", after=0.0, base=None, what=""):
    """Resolve a time field. role: in (lead ahead of the word), at (on the word), out (after the phrase ends)."""
    if spec is None:
        return None
    if isnum(spec):
        return float(spec)
    spec = str(spec)
    if spec.startswith("+") and base is not None and isnum(spec[1:]):
        return base + float(spec[1:])
    hit = find(spec, after)
    if hit is None:
        err('%s: "%s" is not said in the transcript%s' % (what, spec, "" if WORDS else " (no transcript.json)"))
        return after
    if role == "in":
        return max(0.0, hit[0] - args.lead)
    if role == "out":
        return min(D, hit[1] + 0.45)
    return max(0.0, hit[0] - 0.05)


esc = lambda s: H.escape(str(s), quote=True)


def mk(text):
    """Escape, then *word* -> an accent word (italic display face where the format uses it)."""
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", esc(text))


def fit(lines, base, width=936.0, ratio=0.5, floor=56):
    """A font size at which the longest line fits the width (ratio = average glyph width in em)."""
    longest = max((len(re.sub(r"[*]", "", l)) for l in lines), default=1)
    return int(max(floor, min(base, width / (max(longest, 1) * ratio))))


ICONS = {
    "doc": "M16 6h24l10 10v42H16z M40 6v10h10 M23 30h20 M23 39h20 M23 48h13",
    "browser": "M6 12h52v40H6z M6 22h52 M12 17h1 M18 17h1 M24 17h1",
    "bolt": "M36 4 14 36h16l-4 24 22-32H32z",
    "chat": "M8 12h48v30H26l-12 10V42H8z",
    "money": "M32 6a26 26 0 1 0 .01 0z M40 23c-2-3-5-4-8-4-5 0-8 2-8 6 0 8 16 5 16 13 0 4-3 6-8 6-4 0-7-1-9-4 M32 13v6 M32 43v7",
    "check": "M32 6a26 26 0 1 0 .01 0z M20 33l8 8 16-17",
    "user": "M32 8a11 11 0 1 0 .01 0z M12 56c2-12 10-18 20-18s18 6 20 18",
    "code": "M22 18 8 32l14 14 M42 18l14 14-14 14 M36 12 28 52",
    "video": "M6 12h52v40H6z M27 23v18l15-9z",
    "mail": "M6 14h52v36H6z M6 16l26 20 26-20",
    "gear": "M32 22a10 10 0 1 0 .01 0z M32 4v8 M32 52v8 M4 32h8 M52 32h8 M12 12l6 6 M46 46l6 6 M52 12l-6 6 M18 46l-6 6",
    "chart": "M8 56h48 M16 48V34 M28 48V22 M40 48V28 M52 48V10",
    "search": "M27 8a19 19 0 1 0 .01 0z M41 41l15 15",
    "shield": "M32 6 52 13v17c0 13-9 22-20 28C21 52 12 43 12 30V13z",
    "lock": "M18 28h28v26H18z M24 28v-8a8 8 0 0 1 16 0v8 M32 38v8",
    "robot": "M16 22h32v26H16z M32 22v-8 M32 8a3 3 0 1 0 .01 0z M25 33h1 M38 33h1 M26 41h12 M10 30v10 M54 30v10",
    "globe": "M32 6a26 26 0 1 0 .01 0z M6 32h52 M32 6c-9 8-9 44 0 52 M32 6c9 8 9 44 0 52",
    "cloud": "M20 46h26a10 10 0 0 0 0-20 14 14 0 0 0-27-3A11 11 0 0 0 20 46z",
    "key": "M22 16a10 10 0 1 0 .01 0z M29 33l25 25 M46 50l6-6 M52 56l5-5",
    "alert": "M32 8 58 54H6z M32 26v14 M32 47v1",
    "folder": "M6 16h20l6 6h26v32H6z",
    "eye": "M4 32c8-12 17-18 28-18s20 6 28 18c-8 12-17 18-28 18S12 44 4 32z M32 24a8 8 0 1 0 .01 0z",
    "chip": "M18 18h28v28H18z M26 26h12v12H26z M24 10v8 M32 10v8 M40 10v8 M24 46v8 M32 46v8 M40 46v8 M10 24h8 M10 32h8 M10 40h8 M46 24h8 M46 32h8 M46 40h8",
    "phone": "M20 6h24v52H20z M29 50h6",
    "db": "M12 14c0-5 40-5 40 0v36c0 5-40 5-40 0z M12 14c0 5 40 5 40 0 M12 26c0 5 40 5 40 0 M12 38c0 5 40 5 40 0",
    "api": "M10 32h14 M40 32h14 M24 22h16v20H24z M30 16v6 M34 16v6 M30 42v6 M34 42v6",
    "bell": "M32 8c-9 0-14 7-14 16v10l-6 10h40l-6-10V24c0-9-5-16-14-16z M26 50a6 6 0 0 0 12 0",
    "play": "M6 12h52v40H6z M26 22v20l18-10z",
    "clock": "M32 6a26 26 0 1 0 .01 0z M32 16v16l11 7",
    "rocket": "M32 6c10 6 14 18 12 32H20C18 24 22 12 32 6z M20 38l-8 10h12 M44 38l8 10H40 M27 50l5 8 5-8 M32 20a4 4 0 1 0 .01 0z",
    "heart": "M32 54C14 40 6 30 6 20a12 12 0 0 1 26-6 12 12 0 0 1 26 6c0 10-8 20-26 34z",
    "star": "M32 6l8 17 18 2-13 13 3 19-16-9-16 9 3-19L6 25l18-2z",
    "arrow": "M8 32h46 M38 16l16 16-16 16",
    "layers": "M32 8 58 22 32 36 6 22z M6 32l26 14 26-14 M6 42l26 14 26-14",
}


def icon(name, size=64, cls="icn"):
    if not name:
        return ""
    if name not in ICONS:
        err("unknown icon %r (one of: %s)" % (name, " ".join(sorted(ICONS))))
        return ""
    return '<svg class="%s" viewBox="0 0 64 64" width="%d" height="%d"><path d="%s"/></svg>' % (cls, size, size, ICONS[name])


CHECK = ('<svg class="mk" viewBox="0 0 44 44" width="52" height="52"><circle class="ring" cx="22" cy="22" r="19"/>'
         '<path class="tick" d="M13 22.5 L19.5 29 L31 16" pathLength="1" style="stroke-dasharray:1;stroke-dashoffset:1"/></svg>')


def image_size(path):
    try:
        with open(path, "rb") as f:
            head = f.read(26)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", head[16:24])
            if head[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    m = f.read(4)
                    if len(m) < 4 or m[0] != 0xFF:
                        break
                    if m[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        h, w = struct.unpack(">HH", f.read(5)[1:5])
                        return w, h
                    f.seek(struct.unpack(">H", m[2:4])[0] - 2, 1)
    except OSError:
        pass
    return None


# ============================================================ assets ==========================================
def stage(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src) or os.path.getsize(dst) != os.path.getsize(src):
        shutil.copyfile(src, dst)


for f in glob.glob(os.path.join(SKILL, "assets", "fonts", "*.woff2")):
    stage(f, os.path.join(OUT, "fonts", os.path.basename(f)))
stage(os.path.join(SKILL, "assets", "vendor", "gsap.min.js"), os.path.join(OUT, "vendor", "gsap.min.js"))
if args.shared:
    for sub in ("img", "sfx", "broll"):
        for f in glob.glob(os.path.join(args.shared, sub, "**", "*"), recursive=True):
            if os.path.isfile(f):
                stage(f, os.path.join(OUT, sub, os.path.relpath(f, os.path.join(args.shared, sub))))
SFX_MAN = load(os.path.join(SKILL, "assets", "sfx", "manifest.json"))


def asset(rel, what):
    if rel and not os.path.exists(os.path.join(OUT, rel)):
        err("%s: %s is not in %s (put it there, or in --shared)" % (what, rel, OUT))
    return rel


# ============================================================ page parts ======================================
html_parts, video_parts, js_parts, audio_parts, moments = [], [], [], [], []
tracks = {}          # track index -> end time of the last clip on it
cues = []            # (time, name, volume, priority)


def js(s): js_parts.append(s)


def track_for(t0, t1, base=3):
    k = base
    while tracks.get(k, -1.0) > t0 - 0.02:
        k += 1
    tracks[k] = t1
    return k


MOOD = S.get("mood", "balanced")
if MOOD not in MOODS:
    err('mood "%s": use calm, balanced or punchy' % MOOD)
    MOOD = "balanced"


def cue(event, t, beat=None, vol=None, name=None, prio=1):
    """Queue a sound for an on-screen event, unless the beat or the mood silences it."""
    if S.get("sfx") is False:
        return
    over = (beat or {}).get("sfx", None)
    if over is False:
        return
    scale, dropped = MOODS[MOOD]
    n, v = SFX.get(event, (event, 0.15))
    if isinstance(over, str):
        n = over
    elif isinstance(over, dict):
        n, v = over.get("name", n), float(over.get("vol", v))
    elif event in dropped:
        return
    if name:
        n = name
    if vol is not None:
        v = vol
    cues.append((max(0.0, t), n, round(min(1.0, v * scale), 3), prio))


def host(bid, t0, t1, inner, anchor, cls="", z=10, base=3):
    a = ' data-unanchored="1"' if anchor in ("-", None, "") else ' data-anchor="%s"' % esc(anchor)
    html_parts.append('    <div class="card-host clip %s" id="h-%s" data-card-id="%s" data-start="%.3f" data-duration="%.3f" data-track-index="%d"%s '
                      'style="z-index:%d">\n      %s\n    </div>\n' % (cls, bid, bid, t0, max(0.1, t1 - t0), track_for(t0, t1, base), a, z, inner))


MESH = '<div class="mesh"><i class="m1"></i><i class="m2"></i><i class="m3"></i></div>'
_mesh_n = [0]


def mesh(theme):
    return MESH if theme in GLASS else ""


def drift(sel, t0, t1):
    """The light blobs of a glass look wander slowly for the whole life of the frame: on the one timeline, so any frame renders the same."""
    _mesh_n[0] += 1
    k = _mesh_n[0]
    dur = max(0.5, t1 - t0)
    for j, (dx, dy, sc) in enumerate([(160, 120, 1.25), (-180, 140, 0.85), (120, -170, 1.18)]):
        sx, sy = (-1) ** (k + j), (-1) ** (k // 2 + j)
        js("tl.fromTo('%s .m%d', { x: %d, y: %d, scale: 1 }, { x: %d, y: %d, scale: %.2f, duration: %.2f, ease: 'sine.inOut' }, %.3f);"
           % (sel, j + 1, -sx * dx // 2, -sy * dy // 2, sx * dx // 2, sy * dy // 2, sc, dur, t0))


INSET_HIDE_UP, INSET_SHOW, INSET_HIDE_DOWN = "inset(100% 0% 0% 0%)", "inset(0% 0% 0% 0%)", "inset(0% 0% 100% 0%)"
WIPE = 0.45

# ============================================================ world: the paper behind every voiceover stretch ===
chrome = (S.get("world") or {}).get("chrome") or {}
CHROME_L = ('<div class="chrome"><div class="kicker">%s</div><div class="chrome-r">%s</div></div><div class="chrome-line"></div>'
            % (mk(chrome.get("left", "")), mk(chrome.get("right", "")))) if chrome else ""
for i, (a, b) in enumerate(VO):
    t0 = max(0.0, a - WIPE) if a > 0.05 else 0.0
    t1 = min(D, b + WIPE) if b < D - 0.05 else D
    ch = ('<div class="chrome"><div class="kicker">%s</div><div class="chrome-r">%s</div></div><div class="chrome-line"></div>'
          % (mk(chrome.get("left", "")), mk(chrome.get("right", "")))) if chrome else ""
    host("world%d" % i, t0, t1, '<div class="sc t-%s world" id="world%d">%s<div class="grain"></div>%s</div>' % (WORLD, i, mesh(WORLD), ch), "-", "full", z=5, base=2)
    if WORLD in GLASS:
        drift("#world%d" % i, t0, t1)
    if a > 0.05:
        js("tl.fromTo('#world%d', { clipPath: '%s' }, { clipPath: '%s', duration: %.2f, ease: 'power4.inOut' }, %.3f);" % (i, INSET_HIDE_UP, INSET_SHOW, WIPE, t0))
        cue("wipe", t0 + 0.05)
    if b < D - 0.05:
        js("tl.to('#world%d', { clipPath: '%s', duration: %.2f, ease: 'power4.inOut' }, %.3f);" % (i, INSET_HIDE_DOWN, WIPE, b))
        cue("wipe", b + 0.02)

if LAYOUT != "full":
    host("worldL", 0.0, D, '<div class="sc t-%s world" id="worldL">%s<div class="grain"></div>%s</div>' % (WORLD, mesh(WORLD), CHROME_L), "-", "full", z=4, base=2)
    if WORLD in GLASS:
        drift("#worldL", 0.0, D)
    # over a voiceover stretch the source picture is black: the face cam card steps away and the scenes take the frame
    for a, b in VO:
        if a > 0.05:
            js("tl.to('#video-wrap', { autoAlpha: 0, scale: 0.94, duration: 0.35, ease: 'power2.in' }, %.3f);" % max(0.0, a - 0.3))
        else:
            js("tl.set('#video-wrap', { autoAlpha: 0 }, 0);")
        if b < D - 0.05:
            js("tl.fromTo('#video-wrap', { autoAlpha: 0, scale: 0.94 }, { autoAlpha: 1, scale: 1, duration: 0.45, ease: '%s', immediateRender: false }, %.3f);" % (EASE, b))

# ============================================================ beats ===========================================
SCENES = {"statement", "number", "steps", "flow", "bars", "browser", "terminal", "clip", "image", "cta",
          "slots", "versus", "stamp", "strike", "receipt", "gauge"}
OVERLAYS = {"chip", "title", "card", "list", "stat", "progress", "logo", "pills", "subscribe"}
OTOP = int(S.get("overlay_top", 150 if LAYOUT == "full" else 270))      # in a layout the chrome line owns the top
beats = S.get("beats", [])
ids = set()
for n, b in enumerate(beats):
    b.setdefault("id", "%s%d" % (b.get("type", "beat"), n + 1))
    if b["id"] in ids:
        err("two beats share the id %r" % b["id"])
    ids.add(b["id"])
    if not re.match(r"^[A-Za-z][\w-]*$", b["id"]):
        err("beat id %r: letters, digits, - and _ only, starting with a letter" % b["id"])
    b["_full"] = b.get("type") in SCENES or (b.get("type") == "raw" and b.get("full", True))
    if "in" not in b and "anchor" in b:
        b["in"] = b["anchor"]
    if "in" not in b:
        err("beat %s has no \"in\" (a spoken phrase or seconds)" % b["id"])
        b["in"] = 0
    if "anchor" not in b:
        b["anchor"] = b["in"] if not isnum(b["in"]) else "-"
    b["_in"] = when(b["in"], "in", 0.0, what="beat %s in" % b["id"])
order = sorted(beats, key=lambda b: b["_in"])
for b in order:
    nxt_same = [o["_in"] for o in order if o["_in"] > b["_in"] + 0.3 and o["_full"] == b["_full"]]
    if b.get("out") is not None:
        b["_out"] = when(b["out"], "out", b["_in"], base=b["_in"], what="beat %s out" % b["id"])
    elif b["_full"]:
        span_end = next((e for a, e in VO if a - 0.5 <= b["_in"] < e), None)
        b["_out"] = min([x for x in (nxt_same[0] if nxt_same else None, span_end, b["_in"] + 9.0, D) if x is not None])
    else:
        b["_out"] = min([x for x in ((nxt_same[0] - 0.12) if nxt_same else None, b["_in"] + 4.5, D) if x is not None])
    b["_out"] = min(D, max(b["_out"], b["_in"] + 0.6))
    if b["_full"] and nxt_same and b["_out"] > nxt_same[0] + 0.01:      # one scene at a time: the next one takes the frame
        b["_out"] = max(b["_in"] + 0.4, nxt_same[0])


def under(t):
    """What a scene would be laid over at time t: 'cam', or the theme of the world behind a voiceover."""
    return WORLD if in_vo(t) else "cam"


def theme_of(b):
    return "clip" if b.get("type") == "clip" else b.get("theme", "ink" if b.get("type") == "image" and b.get("fit", "cover") == "cover" else WORLD)


CHROME = ""
if chrome:
    CHROME = ('<div class="chrome"><div class="kicker">%s</div><div class="chrome-r">%s</div></div><div class="chrome-line"></div>'
              % (mk(chrome.get("left", "")), mk(chrome.get("right", ""))))


def scene(b, body, cls=""):
    """Wrap a full-frame scene: its own background, and a wipe wherever the look it replaces differs.
    One scene hands over to the next without a gap, so only ONE of them moves at a join: the incoming scene wipes in
    over a different look, or (same look) the outgoing content fades and the new content rises on the same paper."""
    bid, t0, t1, theme = b["id"], b["_in"], b["_out"], theme_of(b)
    fulls_ = [o for o in order if o["_full"] and o is not b]
    prev = next((o for o in fulls_ if o["_in"] < t0 and o["_out"] >= t0 - 0.25), None)
    nxt = next((o for o in fulls_ if abs(o["_in"] - t1) < 0.25), None)
    tr = b.get("transition")
    before = theme_of(prev) if prev else (WORLD if LAYOUT != "full" else under(t0 + 0.02))
    wipe_in = tr == "wipe" or (tr is None and before != theme)
    after = WORLD if LAYOUT != "full" else under(min(D - 0.01, t1 + 0.02))
    wipe_out = nxt is None and t1 < D - 0.05 and (tr == "wipe" or (tr is None and after != theme))
    end = min(D, t1 + WIPE) if wipe_out else t1          # the wipe out STARTS at t1: the face cam is already live underneath
    lay = LAYOUT != "full" and not in_vo(t0 + 0.3)
    ch = CHROME if (b.get("chrome", True) and (in_vo(t0 + 0.3) or lay)) else ""
    if lay:
        cls += " lay"
        body = '<div class="layfit">%s</div>' % body      # the fit lives on a wrapper: the body's own tweens set its transform
    host(bid, t0, end, '<div class="sc t-%s %s" id="%s">%s<div class="grain"></div>%s%s</div>' % (theme, cls, bid, mesh(theme), ch, body), b["anchor"], "full", z=8)
    if theme in GLASS:
        drift("#" + bid, t0, end)
        # glass looks: the content arrives out of focus and settles sharp, a breath slower than the wipe
        js("tl.fromTo('#%s .body', { filter: 'blur(18px)', scale: 1.04 }, { filter: 'blur(0px)', scale: 1, duration: 0.8, ease: '%s' }, %.3f);"
           % (bid, EASE, t0 + (0.22 if wipe_in else 0.0)))
    if wipe_in:
        js("tl.fromTo('#%s', { clipPath: '%s' }, { clipPath: '%s', duration: %.2f, ease: 'power4.inOut' }, %.3f);" % (bid, INSET_HIDE_UP, INSET_SHOW, WIPE, t0))
        cue("wipe", t0 + 0.05, b)
    if wipe_out:
        js("tl.to('#%s', { clipPath: '%s', duration: %.2f, ease: 'power4.inOut' }, %.3f);" % (bid, INSET_HIDE_DOWN, WIPE, t1))
        if not (in_vo(t1 - 0.1) and not in_vo(t1 + 0.02)):     # at the end of a voiceover the world's own wipe already sounds
            cue("wipe", t1 + 0.03, b)
    else:
        js("tl.to('#%s .body', { opacity: 0, y: -24, duration: 0.26, ease: 'power2.in' }, %.3f);" % (bid, t1 - 0.28))
    return t0 + (0.30 if wipe_in else 0.0)       # when the content may start moving


def overlay(b, inner, cls="ocard"):
    bid, t0, t1 = b["id"], b["_in"], b["_out"]
    top = int(b.get("top", OTOP))
    style = "top:%dpx;" % top
    if b.get("width"):
        style += "width:%dpx;%s" % (int(b["width"]), "left:auto;right:60px;" if b.get("align") == "right" else "right:auto;")
    if in_vo(t0 + 0.3) and b.get("type") != "raw":
        warn("%s (%s) enters during a voiceover stretch: overlays are designed for the face cam; use a scene" % (bid, b["type"]))
    host(bid, t0, t1, '<div class="%s t-%s" id="%s" style="%s">%s</div>' % (cls, OVL, bid, style, inner), b["anchor"], z=12)
    js("tl.fromTo('#%s', { opacity: 0, y: -28 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, t0))
    js("tl.to('#%s', { opacity: 0, y: -18, duration: 0.26, ease: 'power2.in' }, %.3f);" % (bid, t1 - 0.28))
    cue("card", t0 + 0.02, b, prio=0)


def items_of(b, key="items"):
    """Normalise list items to dicts with a resolved time: [text, when] or {"text"/"title"/"label":.., "at":..}."""
    out = []
    for i, it in enumerate(b.get(key, [])):
        d = dict(it) if isinstance(it, dict) else {"text": it[0], "at": it[1] if len(it) > 1 else None}
        text = d.get("title") or d.get("label") or d.get("text") or ""
        spec = d.get("at")
        if spec is None:
            spec = re.sub(r"[*]", "", text)
        d["_t"] = max(b["_in"] + 0.05, when(spec, "at", b["_in"], what="%s item %d" % (b["id"], i + 1)))
        d["_anchor"] = spec if not isnum(spec) else "-"
        d["_text"] = text
        out.append(d)
        moments.append((d["_t"] + 0.55, "%s item %d" % (b["id"], i + 1)))
    return out


def item_attr(d):
    a = ' data-unanchored="1"' if d["_anchor"] == "-" else ' data-anchor="%s"' % esc(d["_anchor"])
    return ' data-at="%.3f"%s' % (d["_t"], a)


def kicker(b, key="kicker"):
    return '<div class="kicker">%s</div>' % mk(b[key]) if b.get(key) else ""


for b in order:
    t, bid, t0, t1 = b.get("type"), b["id"], b["_in"], b["_out"]
    moments.append((min(t1 - 0.15, t0 + 0.95), bid))

    # ---------------------------------------------------------------- overlays over the face cam
    if t == "chip":
        dot = '<span class="dot"></span>' if b.get("dot", True) else ""
        top = int(b.get("top", OTOP))
        host(bid, t0, t1, '<div class="chip t-%s %s" id="%s" style="top:%dpx">%s<span>%s</span></div>'
             % (OVL, "right" if b.get("align") == "right" else "", bid, top, dot, mk(b["text"])), b["anchor"], z=12)
        js("tl.fromTo('#%s', { opacity: 0, scale: 0.82 }, { opacity: 1, scale: 1, duration: 0.36, ease: 'back.out(1.8)' }, %.3f);" % (bid, t0))
        js("tl.to('#%s', { opacity: 0, duration: 0.24, ease: 'power2.in' }, %.3f);" % (bid, t1 - 0.26))
        cue("pop", t0 + 0.04, b)

    elif t == "title":
        lines = [l if isinstance(l, str) else l[0] for l in b["lines"]]
        size = int(b.get("size") or fit(lines, 124, 960, 0.5))
        spans = "".join('<span class="ln"><span>%s</span></span>' % mk(l) for l in lines)
        host(bid, t0, t1, '<div class="otitle t-%s disp" id="%s" style="top:%dpx;font-size:%dpx">%s</div>' % (OVL, bid, int(b.get("top", OTOP)), size, spans),
             b["anchor"], z=12)
        for i, l in enumerate(b["lines"]):
            lt = t0 + 0.09 * i if isinstance(l, str) or len(l) < 2 else max(t0, when(l[1], "at", t0, what="%s line %d" % (bid, i + 1)))
            js("tl.fromTo('#%s .ln:nth-child(%d) > span', { yPercent: 112 }, { yPercent: 0, duration: 0.62, ease: '%s' }, %.3f);" % (bid, i + 1, EASE, lt))
        js("tl.to('#%s', { opacity: 0, y: -18, duration: 0.26, ease: 'power2.in' }, %.3f);" % (bid, t1 - 0.28))

    elif t == "card":
        ic = '<div class="ic-box">%s</div>' % icon(b.get("icon"), 60) if b.get("icon") else ""
        sub = '<div class="sub">%s</div>' % mk(b["sub"]) if b.get("sub") else ""
        overlay(b, '%s<div class="row">%s<div><div class="ttl disp">%s</div>%s</div></div>' % (kicker(b), ic, mk(b.get("title", "")), sub))

    elif t == "list":
        its = items_of(b)
        marker = b.get("marker", "dot")
        rows = ""
        for i, d in enumerate(its):
            m = CHECK if marker == "check" else ('<span class="num">%02d</span>' % (i + 1) if marker == "number" else '<span class="d"></span>')
            rows += '<div class="item" id="%s-i%d"%s>%s<div class="t">%s</div></div>' % (bid, i, item_attr(d), m, mk(d["_text"]))
        overlay(b, kicker(b) + '<div class="items">%s</div>' % rows, "ocard olist")
        for i, d in enumerate(its):
            js("tl.set('#%s-i%d', { display: 'flex' }, %.3f);" % (bid, i, d["_t"]))
            js("tl.fromTo('#%s-i%d', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.42, ease: '%s' }, %.3f);" % (bid, i, EASE, d["_t"]))
            if marker == "check":
                js("checkIn('#%s-i%d', %.3f);" % (bid, i, d["_t"] + 0.2))
            cue("item", d["_t"] + 0.03, b)

    elif t == "stat":
        at = max(t0 + 0.1, when(b.get("at"), "at", t0, what="%s at" % bid) if b.get("at") is not None else t0 + 0.2)
        sub = '<div class="sub">%s</div>' % mk(b["sub"]) if b.get("sub") else ""
        overlay(b, '%s<div class="big disp" id="%s-v"></div>%s' % (kicker(b), bid, sub), "ocard ostat")
        js("count('#%s-v', %s, %s, %.3f, %.2f, %s);" % (bid, json.dumps(b.get("from", 0)), json.dumps(b["value"]), at, float(b.get("count", 1.0)),
                                                         json.dumps({"prefix": b.get("prefix", ""), "suffix": b.get("suffix", ""), "dec": int(b.get("decimals", 0))})))
        cue("land", at + float(b.get("count", 1.0)) - 0.05, b)
        moments.append((at + float(b.get("count", 1.0)) + 0.2, bid + " landed"))

    elif t == "progress":
        val, goal = float(b.get("value", 0)), float(b.get("goal", 1000))
        pct = max(0.0, min(1.0, val / goal if goal else 0))
        at = max(t0 + 0.1, when(b.get("at"), "at", t0, what="%s at" % bid) if b.get("at") is not None else t0 + 0.25)
        pre, suf = b.get("prefix", "$"), b.get("suffix", "")
        head = '<div class="kicker">%s</div>' % mk(b["kicker"] if b.get("kicker") else ("Day %02d · %s" % (int(b["day"]), b.get("label", "MRR")) if b.get("day") is not None else b.get("label", "MRR")))
        overlay(b, '%s<div class="prow"><div class="big disp" id="%s-v"></div><div class="goal">of <b>%s</b></div></div>'
                   '<div class="ptrack"><div class="pfill" id="%s-f"></div><div class="ppin" id="%s-p" style="left:%.2f%%"></div><div class="pflag"></div></div>'
                % (head, bid, mk(b.get("goal_label", "%s%s%s" % (pre, "{:,.0f}".format(goal), suf))), bid, bid, pct * 100), "ocard oprog")
        js("count('#%s-v', 0, %s, %.3f, 0.9, %s);" % (bid, json.dumps(val), at, json.dumps({"prefix": pre, "suffix": suf, "dec": 0})))
        js("tl.fromTo('#%s-f', { scaleX: 0 }, { scaleX: %.4f, duration: 1.0, ease: '%s' }, %.3f);" % (bid, max(pct, 0.012), EASE, at))
        js("tl.fromTo('#%s-p', { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: 0.4, ease: 'back.out(2)' }, %.3f);" % (bid, at + 0.55))
        cue("land", at + 0.6, b)

    elif t == "logo":
        asset(b["src"], bid)
        top = int(b.get("top", OTOP))
        host(bid, t0, t1, '<div class="plate %s" id="%s" style="top:%dpx"><img src="%s" alt=""></div>' % ("right" if b.get("align") == "right" else "", bid, top, esc(b["src"])),
             b["anchor"], z=12)
        js("tl.fromTo('#%s', { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.38, ease: 'back.out(1.7)' }, %.3f);" % (bid, t0))
        js("tl.to('#%s', { opacity: 0, duration: 0.24, ease: 'power2.in' }, %.3f);" % (bid, t1 - 0.26))
        cue("pop", t0 + 0.04, b)

    elif t == "pills":
        its = items_of(b)
        pills = "".join('<div class="pill t-%s %s" id="%s-i%d"%s>%s<span>%s</span></div>'
                        % (OVL, d.get("tone", ""), bid, i, item_attr(d), icon(d.get("icon"), 40), mk(d["_text"])) for i, d in enumerate(its))
        host(bid, t0, t1, '<div class="pills" id="%s" style="top:%dpx">%s</div>' % (bid, int(b.get("top", OTOP)), pills), b["anchor"], z=12)
        for i, d in enumerate(its):
            js("tl.fromTo('#%s-i%d', { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.34, ease: 'back.out(1.8)' }, %.3f);" % (bid, i, d["_t"]))
            cue("pop", d["_t"] + 0.03, b, vol=0.16)
        js("tl.to('#%s', { opacity: 0, duration: 0.24, ease: 'power2.in' }, %.3f);" % (bid, t1 - 0.26))

    elif t == "subscribe":
        tap = max(t0 + 0.5, when(b.get("tap"), "at", t0, what="%s tap" % bid) if b.get("tap") is not None else t0 + 1.2)
        bell = max(tap + 0.3, when(b.get("bell"), "at", t0, what="%s bell" % bid) if b.get("bell") is not None else tap + 0.7)
        sub = '<div class="sub">%s</div>' % mk(b["sub"]) if b.get("sub") else ""
        overlay(b, '<div class="row"><div class="yt">%s</div><div class="grow"><div class="ttl disp">%s</div>%s</div></div>'
                   '<div class="row2"><div class="sbtn" id="%s-b"><span class="s0">Subscribe</span><span class="s1">Subscribed ✓</span></div>'
                   '<div class="bell" id="%s-bell">%s</div></div>'
                % (icon("play", 56), mk(b.get("title", "Follow the journey")), sub, bid, bid, icon("bell", 52)), "ocard osub")
        js("tl.to('#%s-b', { scale: 0.93, duration: 0.09, ease: 'power2.in' }, %.3f);" % (bid, tap))
        js("tl.to('#%s-b', { scale: 1, backgroundColor: '%s', color: '%s', duration: 0.3, ease: 'back.out(2)' }, %.3f);" % (bid, "#15102a" if OVL in ("aurora", "dusk") else TOKENS[OVL]["raised"], "#ffffff" if OVL in ("aurora", "dusk") else TOKENS[OVL]["fg"], tap + 0.09))
        js("tl.set('#%s-b .s0', { display: 'none' }, %.3f); tl.set('#%s-b .s1', { display: 'inline' }, %.3f);" % (bid, tap + 0.09, bid, tap + 0.09))
        js("tl.to('#%s-bell', { color: '%s', duration: 0.2 }, %.3f);" % (bid, TOKENS[OVL]["accent"], bell))
        js("tl.fromTo('#%s-bell', { rotation: 0 }, { keyframes: [{ rotation: 18, duration: 0.08 }, { rotation: -14, duration: 0.1 }, { rotation: 9, duration: 0.1 }, { rotation: 0, duration: 0.12 }], ease: 'power1.inOut' }, %.3f);" % (bid, bell))
        cue("tap", tap + 0.02, b); cue("bell", bell + 0.02, b)
        moments += [(tap + 0.45, bid + " tapped"), (bell + 0.5, bid + " bell")]

    # ---------------------------------------------------------------- full-frame scenes
    elif t == "statement":
        raw_lines = b["lines"]
        lines = [l if isinstance(l, str) else l[0] for l in raw_lines]
        size = int(b.get("size") or fit(lines, 176, 930, 0.47, 72))
        spans = "".join('<span class="ln"><span>%s</span></span>' % mk(l) for l in lines)
        sub = '<div class="ssub" id="%s-sub">%s</div>' % (bid, mk(b["sub"])) if b.get("sub") else ""
        go = scene(b, '<div class="body st-body">%s<div class="disp st-lines" style="font-size:%dpx">%s</div>%s</div>' % (kicker(b), size, spans, sub))
        if b.get("kicker"):
            js("tl.fromTo('#%s .kicker', { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, go))
        last = go
        for i, l in enumerate(raw_lines):
            lt = go + 0.08 + 0.10 * i if isinstance(l, str) or len(l) < 2 else max(go, when(l[1], "at", t0, what="%s line %d" % (bid, i + 1)))
            js("tl.fromTo('#%s .ln:nth-child(%d) > span', { yPercent: 112 }, { yPercent: 0, duration: 0.66, ease: '%s' }, %.3f);" % (bid, i + 1, EASE, lt))
            last = max(last, lt)
            if not isinstance(l, str) and len(l) > 1:
                moments.append((lt + 0.7, "%s line %d" % (bid, i + 1)))
                cue("line", lt + 0.12, b, prio=0)        # a line that lands on its own word gets a soft tick
        cue("line", go + 0.2, b, prio=0)
        if b.get("sub"):
            st = max(last + 0.35, when(b.get("sub_at"), "at", t0, what="%s sub" % bid) if b.get("sub_at") is not None else 0)
            js("tl.fromTo('#%s-sub', { opacity: 0, y: 22 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, st))
            moments.append((st + 0.6, bid + " sub"))
        if b.get("hit"):
            cue("hit", last + 0.05, b, prio=2)

    elif t == "number":
        at = max(t0 + 0.1, when(b.get("at"), "at", t0, what="%s at" % bid) if b.get("at") is not None else t0 + 0.3)
        dur = float(b.get("count", 1.1))
        shown = "%s%s%s" % (b.get("prefix", ""), "{:,.{d}f}".format(float(b["value"]), d=int(b.get("decimals", 0))), b.get("suffix", ""))
        size = int(b.get("size") or fit([shown], 380, 900, 0.56, 150))
        lab = '<div class="nlabel" id="%s-l">%s</div>' % (bid, mk(b["label"])) if b.get("label") else ""
        sub = '<div class="ssub" id="%s-sub">%s</div>' % (bid, mk(b["sub"])) if b.get("sub") else ""
        go = scene(b, '<div class="body nb-body">%s<div class="disp nbig" id="%s-v" style="font-size:%dpx"></div><div class="nrule" id="%s-r"></div>%s%s</div>'
                   % (kicker(b), bid, size, bid, lab, sub))
        at = max(at, go)
        js("tl.fromTo('#%s .kicker', { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, go))
        js("tl.fromTo('#%s-v', { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, at - 0.05))
        js("count('#%s-v', %s, %s, %.3f, %.2f, %s);" % (bid, json.dumps(b.get("from", 0)), json.dumps(b["value"]), at, dur,
                                                         json.dumps({"prefix": b.get("prefix", ""), "suffix": b.get("suffix", ""), "dec": int(b.get("decimals", 0))})))
        js("tl.fromTo('#%s-r', { scaleX: 0 }, { scaleX: 1, duration: 0.7, ease: '%s' }, %.3f);" % (bid, EASE, at + dur - 0.25))
        if b.get("label"):
            lt = max(at + 0.25, when(b.get("label_at"), "at", t0, what="%s label" % bid) if b.get("label_at") is not None else at + dur - 0.35)
            js("tl.fromTo('#%s-l', { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, lt))
        if b.get("sub"):
            js("tl.fromTo('#%s-sub', { opacity: 0, y: 22 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, at + dur + 0.1))
        cue("land", at + dur - 0.06, b, prio=2)
        moments.append((at + dur + 0.45, bid + " landed"))

    elif t == "steps":
        its = items_of(b)
        marker = b.get("marker", "number")
        rows = ""
        for i, d in enumerate(its):
            m = CHECK if marker == "check" else '<div class="idx disp">%02d</div>' % (i + 1)
            sub = '<div class="s">%s</div>' % mk(d["sub"]) if d.get("sub") else ""
            rows += '<div class="step" id="%s-i%d"%s>%s<div class="tx"><div class="t">%s</div>%s</div></div>' % (bid, i, item_attr(d), m, mk(d["_text"]), sub)
        ttl = '<div class="disp sttl">%s</div>' % mk(b["title"]) if b.get("title") else ""
        go = scene(b, '<div class="body sp-body">%s%s<div class="steps n%d">%s</div></div>' % (kicker(b), ttl, len(its), rows))
        js("tl.fromTo('#%s .kicker, #%s .sttl', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s', stagger: 0.08 }, %.3f);" % (bid, bid, EASE, go))
        for i, d in enumerate(its):
            ti = max(go, d["_t"])
            js("tl.fromTo('#%s-i%d', { opacity: 0, x: -36 }, { opacity: 1, x: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, i, EASE, ti))
            if i:
                js("tl.to('#%s-i%d', { opacity: 0.42, duration: 0.35, ease: 'power2.out' }, %.3f);" % (bid, i - 1, ti))
            if marker == "check":
                js("checkIn('#%s-i%d', %.3f);" % (bid, i, ti + 0.25))
            cue("item", ti + 0.03, b)
        if b.get("recap", True) and len(its) > 1:
            rt = max(max(d["_t"] for d in its) + 1.2, t1 - 1.1)
            if rt < t1 - 0.4:
                js("tl.to('#%s .step', { opacity: 1, duration: 0.4, ease: 'power2.out' }, %.3f);" % (bid, rt))

    elif t == "flow":
        nodes = items_of(b, "nodes")
        n = len(nodes)
        nh = 190 if n <= 3 else (164 if n == 4 else 138)
        gap = 66 if n <= 4 else 44
        body = ""
        for i, d in enumerate(nodes):
            if i:
                body += '<div class="conn" id="%s-c%d" style="height:%dpx"><div class="shaft"></div><div class="pk"></div></div>' % (bid, i, gap)
            sub = '<div class="s">%s</div>' % mk(d["sub"]) if d.get("sub") else ""
            body += ('<div class="node %s" id="%s-i%d" style="height:%dpx"%s><div class="ic-box">%s</div><div class="tx"><div class="t">%s</div>%s</div></div>'
                     % ("payoff" if d.get("payoff") else "", bid, i, nh, item_attr(d), icon(d.get("icon") or "arrow", 56), mk(d["_text"]), sub))
        ttl = '<div class="disp sttl">%s</div>' % mk(b["title"]) if b.get("title") else ""
        go = scene(b, '<div class="body fl-body">%s%s<div class="flowcol">%s</div></div>' % (kicker(b), ttl, body))
        js("tl.fromTo('#%s .kicker, #%s .sttl', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s', stagger: 0.08 }, %.3f);" % (bid, bid, EASE, go))
        for i, d in enumerate(nodes):
            ti = max(go, d["_t"])
            if i:
                js("tl.fromTo('#%s-c%d .shaft', { scaleY: 0 }, { scaleY: 1, duration: 0.3, ease: 'power2.inOut' }, %.3f);" % (bid, i, ti - 0.22))
                js("tl.fromTo('#%s-c%d .pk', { opacity: 0, y: 0 }, { keyframes: [{ opacity: 1, duration: 0.05 }, { y: %d, duration: 0.28, ease: 'power1.in' }, { opacity: 0, duration: 0.06 }] }, %.3f);" % (bid, i, gap - 14, ti - 0.2))
            js("tl.fromTo('#%s-i%d', { opacity: 0, y: 30, scale: 0.97 }, { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: '%s' }, %.3f);" % (bid, i, EASE, ti))
            cue("payoff" if d.get("payoff") else "item", ti + 0.04, b, prio=2 if d.get("payoff") else 1)

    elif t == "bars":
        rows_in = items_of(b, "rows")
        mx = max(float(d["value"]) for d in rows_in) or 1.0
        rows = ""
        for i, d in enumerate(rows_in):
            rows += ('<div class="brow %s" id="%s-i%d"%s><div class="bl"><span>%s</span><b>%s</b></div><div class="btrack"><div class="bfill" id="%s-f%d"></div></div></div>'
                     % ("hi" if d.get("hi") else "", bid, i, item_attr(d), mk(d["_text"]), mk(d.get("text", "{:,g}".format(float(d["value"])))), bid, i))
        ttl = '<div class="disp sttl">%s</div>' % mk(b["title"]) if b.get("title") else ""
        go = scene(b, '<div class="body br-body">%s%s<div class="bars">%s</div></div>' % (kicker(b), ttl, rows))
        js("tl.fromTo('#%s .kicker, #%s .sttl', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s', stagger: 0.08 }, %.3f);" % (bid, bid, EASE, go))
        for i, d in enumerate(rows_in):
            ti = max(go, d["_t"])
            frac = max(0.02, float(d["value"]) / mx)
            js("tl.fromTo('#%s-i%d', { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.45, ease: '%s' }, %.3f);" % (bid, i, EASE, ti))
            js("tl.fromTo('#%s-f%d', { scaleX: 0 }, { scaleX: %.4f, duration: %.2f, ease: '%s' }, %.3f);" % (bid, i, frac, 0.5 + 0.5 * frac, EASE, ti + 0.1))
            cue("item", ti + 0.03, b)
            if d.get("hi"):
                cue("grow", ti + 0.35, b)

    elif t == "browser":
        asset(b["src"], bid)
        phone = b.get("frame") == "phone"
        fw, fh = (540, 1040) if phone else (936, 900)
        bar = 0 if phone else 66
        size = image_size(os.path.join(OUT, b["src"]))
        disp_h = fw * size[1] / size[0] if size else fh
        maxscroll = max(0.0, disp_h - (fh - bar))
        scroll = min(float(b.get("scroll", 0)), maxscroll)
        if float(b.get("scroll", 0)) > maxscroll + 1:
            warn("%s: scroll %s is past the end of the page (%.0f px shown); clamped" % (bid, b["scroll"], maxscroll))
        chrome_bar = "" if phone else ('<div class="bbar"><i></i><i></i><i></i><div class="url">%s</div></div>' % esc(b.get("domain", "")))
        call = ""
        if b.get("callout"):
            c = b["callout"]
            call = '<div class="callout" id="%s-co" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"></div>' % (bid, c["x"], c["y"], c["w"], c["h"])
        lab = '<div class="slabel" id="%s-lab">%s</div>' % (bid, mk(b["label"])) if b.get("label") else ""
        go = scene(b, '<div class="body bw-body">%s<div class="win %s" id="%s-w" style="width:%dpx;height:%dpx">%s<div class="pagewrap" style="top:%dpx">'
                      '<div class="pg" id="%s-pg"><img src="%s" alt="" style="width:%dpx">%s</div></div></div>%s</div>'
                   % (kicker(b), "phone" if phone else "", bid, fw, fh, chrome_bar, bar, bid, esc(b["src"]), fw, call, lab))
        js("tl.fromTo('#%s .kicker', { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, go))
        js("tl.fromTo('#%s-w', { opacity: 0, y: 70, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.7, ease: '%s' }, %.3f);" % (bid, EASE, go))
        cue("card", go + 0.03, b, prio=0)
        if scroll > 0:
            s0 = max(go + 0.7, when(b.get("scroll_at"), "at", t0, what="%s scroll" % bid) if b.get("scroll_at") is not None else go + 0.9)
            sd = max(0.8, min(t1 - s0 - 0.5, float(b.get("scroll_dur", 2.4))))
            js("tl.to('#%s-pg', { y: %.1f, duration: %.2f, ease: 'power2.inOut' }, %.3f);" % (bid, -scroll, sd, s0))
            moments.append((s0 + sd + 0.2, bid + " scrolled"))
        if b.get("callout"):
            ct = max(go + 0.6, when(b["callout"].get("at"), "at", t0, what="%s callout" % bid) if b["callout"].get("at") is not None else go + 1.2)
            js("tl.fromTo('#%s-co', { opacity: 0, scale: 1.25 }, { opacity: 1, scale: 1, duration: 0.45, ease: '%s' }, %.3f);" % (bid, EASE, ct))
            cue("land", ct + 0.05, b)
            moments.append((ct + 0.6, bid + " callout"))
        if b.get("label"):
            js("tl.fromTo('#%s-lab', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, go + 0.5))

    elif t == "terminal":
        lines = items_of(b, "lines")
        rows = ""
        for i, d in enumerate(lines):
            rows += '<div class="tl %s" id="%s-i%d"%s data-text="%s"></div>' % (d.get("tone", ""), bid, i, item_attr(d), esc(d["_text"]))
        go = scene(b, '<div class="body tm-body">%s<div class="term" id="%s-w"><div class="tbar"><i></i><i></i><i></i><span>%s</span></div><div class="tlines">%s</div></div></div>'
                   % (kicker(b), bid, esc(b.get("title", "terminal")), rows))
        js("tl.fromTo('#%s .kicker', { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, go))
        js("tl.fromTo('#%s-w', { opacity: 0, y: 60, scale: 0.97 }, { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: '%s' }, %.3f);" % (bid, EASE, go))
        for i, d in enumerate(lines):
            ti = max(go + 0.3, d["_t"])
            js("tl.set('#%s-i%d', { display: 'block' }, %.3f);" % (bid, i, ti))
            if d.get("type"):
                td = max(0.35, min(2.2, len(d["_text"]) / float(d.get("cps", 22))))
                js("typeIn('#%s-i%d', %.3f, %.3f);" % (bid, i, ti, ti + td))
                k = 0
                while k * 1.5 < td - 0.05:        # the typing file is 1.5 s: repeat it for exactly the typing time
                    cue("type", ti + k * 1.5, b, prio=2); k += 1
                moments.append((ti + td + 0.15, "%s line %d typed" % (bid, i + 1)))
            else:
                js("showText('#%s-i%d');" % (bid, i))
                js("tl.fromTo('#%s-i%d', { opacity: 0 }, { opacity: 1, duration: 0.18 }, %.3f);" % (bid, i, ti))
                if d.get("tone") == "good":
                    cue("payoff", ti + 0.03, b, prio=2)
                elif d.get("tone") == "bad":
                    cue("error", ti + 0.03, b, prio=2)

    elif t == "clip":
        asset(b["src"], bid)
        a = ' data-unanchored="1"' if b["anchor"] == "-" else ' data-anchor="%s"' % esc(b["anchor"])
        video_parts.append('    <video class="cutaway-video clip" id="%s" src="%s" muted playsinline data-start="%.3f" data-duration="%.3f" data-media-start="%.3f" data-track-index="%d"%s></video>\n'
                           % (bid, esc(b["src"]), t0, t1 - t0, float(b.get("media_start", 0)), track_for(t0, t1), a))
        if b.get("drift", True):
            js("tl.fromTo('#%s', { scale: 1.0 }, { scale: %.3f, duration: %.3f, ease: 'none' }, %.3f);" % (bid, float(b.get("push", 1.05)), t1 - t0, t0))
        if b.get("label"):
            host(bid + "-over", t0, t1, '<div class="cliplabel" id="%s-lab">%s</div>' % (bid, mk(b["label"])), "-", "full", z=9)
            js("tl.fromTo('#%s-lab', { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, t0 + 0.25))
            js("tl.to('#%s-lab', { opacity: 0, duration: 0.24, ease: 'power2.in' }, %.3f);" % (bid, t1 - 0.26))

    elif t == "image":
        asset(b["src"], bid)
        lab = '<div class="slabel" id="%s-lab">%s</div>' % (bid, mk(b["label"])) if b.get("label") else ""
        if b.get("fit", "cover") == "card":
            go = scene(b, '<div class="body im-body">%s<div class="imcard" id="%s-w"><img src="%s" alt=""></div>%s</div>' % (kicker(b), bid, esc(b["src"]), lab))
            js("tl.fromTo('#%s .kicker', { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, go))
            js("tl.fromTo('#%s-w', { opacity: 0, y: 60, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.7, ease: '%s' }, %.3f);" % (bid, EASE, go))
            js("tl.fromTo('#%s-w img', { scale: 1.0 }, { scale: 1.05, duration: %.2f, ease: 'none' }, %.3f);" % (bid, t1 - t0, t0))
        else:
            go = scene(b, '<img class="imfull" id="%s-im" src="%s" alt=""><div class="imshade"></div><div class="body im-cover">%s</div>' % (bid, esc(b["src"]), lab))
            js("tl.fromTo('#%s-im', { scale: 1.0 }, { scale: %.3f, duration: %.2f, ease: 'none' }, %.3f);" % (bid, float(b.get("push", 1.07)), t1 - t0, t0))
        if b.get("label"):
            js("tl.fromTo('#%s-lab', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, go + 0.4))

    elif t == "cta":
        if b.get("photo"):
            asset(b["photo"], bid)
        lines = b.get("lines", ["Got something", "to *build?*"])
        size = int(b.get("size") or fit(lines, 138, 930, 0.47, 72))
        spans = "".join('<span class="ln"><span>%s</span></span>' % mk(l) for l in lines)
        photo = '<div class="cphoto" id="%s-ph"><img src="%s" alt=""></div>' % (bid, esc(b["photo"])) if b.get("photo") else ""
        url = ('<div class="curl" id="%s-url"><span>%s</span><i id="%s-ul"></i></div>' % (bid, esc(b["url"]), bid)) if b.get("url") else ""
        chips = "".join('<div class="cchip">%s</div>' % mk(c) for c in b.get("chips", []))
        go = scene(b, '<div class="body ct-body">%s%s<div class="disp st-lines" style="font-size:%dpx">%s</div>%s<div class="cchips">%s</div></div>'
                   % (photo, kicker(b), size, spans, url, chips))
        if b.get("photo"):
            js("tl.fromTo('#%s-ph', { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.5, ease: 'back.out(1.6)' }, %.3f);" % (bid, go))
        js("tl.fromTo('#%s .kicker', { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, go + 0.1))
        js("tl.fromTo('#%s .ln > span', { yPercent: 112 }, { yPercent: 0, duration: 0.66, ease: '%s', stagger: 0.1 }, %.3f);" % (bid, EASE, go + 0.18))
        ut = max(go + 0.6, when(b.get("url_at"), "at", t0, what="%s url" % bid) if b.get("url_at") is not None else go + 0.75)
        if b.get("url"):
            js("tl.fromTo('#%s-url', { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, ut))
            js("tl.fromTo('#%s-ul', { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: 'power2.inOut' }, %.3f);" % (bid, ut + 0.3))
            moments.append((ut + 1.0, bid + " url"))
        if b.get("url"):
            cue("pop", ut + 0.05, b, vol=0.14)
        if chips:
            js("tl.fromTo('#%s .cchip', { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.4, ease: '%s', stagger: 0.09 }, %.3f);" % (bid, EASE, ut + 0.45))

    # ---- action scenes (ideas from Nate Herk's card library): each one changes state on a spoken word ----------
    elif t == "slots":
        # the open loop made visible: every slot is planted empty at the start, each fills on its word
        its = items_of(b)
        empty = int(b.get("empty", 0))
        rows = ""
        for i in range(len(its) + empty):
            d = its[i] if i < len(its) else None
            sub = '<div class="s">%s</div>' % mk(d["sub"]) if d and d.get("sub") else ""
            fill = '<div class="sl-fill"><div class="t">%s</div>%s</div>' % (mk(d["_text"]), sub) if d else ""
            rows += '<div class="slot" id="%s-i%d"%s><div class="sl-n disp">%02d</div><div class="sl-q">?</div>%s</div>' % (bid, i, item_attr(d) if d else "", i + 1, fill)
        ttl = '<div class="disp sttl">%s</div>' % mk(b["title"]) if b.get("title") else ""
        go = scene(b, '<div class="body sl-body">%s%s<div class="slots n%d">%s</div></div>' % (kicker(b), ttl, len(its) + empty, rows))
        js("tl.fromTo('#%s .kicker, #%s .sttl', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s', stagger: 0.08 }, %.3f);" % (bid, bid, EASE, go))
        js("tl.fromTo('#%s .slot', { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.45, ease: '%s', stagger: 0.07 }, %.3f);" % (bid, EASE, go + 0.15))
        cue("card", go + 0.15, b, prio=0)
        for i, d in enumerate(its):
            ti = max(go + 0.5, d["_t"])
            js("tl.to('#%s-i%d .sl-q', { opacity: 0, scale: 0.6, duration: 0.18, ease: 'power2.in' }, %.3f);" % (bid, i, ti))
            js("tl.set('#%s-i%d', { attr: { class: 'slot on' } }, %.3f);" % (bid, i, ti + 0.05))
            js("tl.fromTo('#%s-i%d .sl-fill', { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.45, ease: '%s' }, %.3f);" % (bid, i, EASE, ti + 0.05))
            js("tl.fromTo('#%s-i%d', { scale: 0.97 }, { scale: 1, duration: 0.4, ease: 'back.out(2)' }, %.3f);" % (bid, i, ti + 0.05))
            last = i == len(its) - 1 and not empty
            cue("payoff" if last else "item", ti + 0.06, b, prio=2 if last else 1)

    elif t == "versus":
        sides = {}
        for k in ("left", "right"):
            d = dict(b.get(k) or {})
            spec = d.get("at")
            if spec is None:
                spec = re.sub(r"[*]", "", d.get("title", ""))
            d["_t"] = max(t0 + 0.05, when(spec, "at", t0, what="%s %s" % (bid, k)))
            moments.append((d["_t"] + 0.6, "%s %s" % (bid, k)))
            sides[k] = d
        win = b.get("winner", "right")
        vt = max(max(s["_t"] for s in sides.values()) + 0.6,
                 when(b.get("verdict"), "at", t0, what="%s verdict" % bid) if b.get("verdict") is not None else 0)
        cols = ""
        for k, d in sides.items():
            sub = '<div class="s">%s</div>' % mk(d["sub"]) if d.get("sub") else ""
            val = '<div class="v disp">%s</div>' % mk(d["value"]) if d.get("value") else ""
            cols += ('<div class="vs-col %s" id="%s-%s"><div class="kicker">%s</div><div class="t">%s</div>%s%s<div class="vs-x"></div><div class="vs-ok">%s</div></div>'
                     % (k, bid, k, mk(d.get("label", "Before" if k == "left" else "After")), mk(d.get("title", "")), val, sub, CHECK))
        ttl = '<div class="disp sttl">%s</div>' % mk(b["title"]) if b.get("title") else ""
        go = scene(b, '<div class="body vs-body">%s%s<div class="vs">%s<div class="vs-mid disp">vs</div></div></div>' % (kicker(b), ttl, cols))
        js("tl.fromTo('#%s > .body > .kicker, #%s .sttl', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s', stagger: 0.08 }, %.3f);" % (bid, bid, EASE, go))
        for k, d in sides.items():
            ti = max(go, d["_t"])
            js("tl.fromTo('#%s-%s', { opacity: 0, x: %d }, { opacity: 1, x: 0, duration: 0.55, ease: '%s' }, %.3f);" % (bid, k, -60 if k == "left" else 60, EASE, ti))
            cue("item", ti + 0.03, b)
        js("tl.fromTo('#%s .vs-mid', { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.4, ease: 'back.out(2)' }, %.3f);" % (bid, max(go, sides["right"]["_t"]) + 0.1))
        lose = "left" if win == "right" else "right"
        vt = max(go + 0.8, vt)
        js("tl.to('#%s-%s', { opacity: 0.45, scale: 0.95, duration: 0.4, ease: 'power2.out' }, %.3f);" % (bid, lose, vt))
        js("tl.fromTo('#%s-%s .vs-x', { scaleX: 0 }, { scaleX: 1, duration: 0.35, ease: 'power2.inOut' }, %.3f);" % (bid, lose, vt))
        js("tl.set('#%s-%s', { attr: { class: 'vs-col %s win' } }, %.3f);" % (bid, win, win, vt))
        js("tl.fromTo('#%s-%s', { scale: 1 }, { keyframes: [{ scale: 1.05, duration: 0.18 }, { scale: 1.02, duration: 0.3 }], ease: 'power2.out' }, %.3f);" % (bid, win, vt))
        js("checkIn('#%s-%s .vs-ok', %.3f);" % (bid, win, vt + 0.15))
        cue("payoff", vt + 0.05, b, prio=2)
        moments.append((vt + 0.7, bid + " verdict"))

    elif t == "stamp":
        # a claim on a card, then the verdict slams onto it
        at = max(t0 + 0.6, when(b.get("at"), "at", t0, what="%s at" % bid) if b.get("at") is not None else t0 + 1.2)
        sub = '<div class="s">%s</div>' % mk(b["sub"]) if b.get("sub") else ""
        go = scene(b, '<div class="body sm-body"><div class="sm-card" id="%s-c">%s<div class="disp t">%s</div>%s</div>'
                      '<div class="sm-stamp %s" id="%s-s"><span>%s</span></div></div>'
                   % (bid, kicker(b), mk(b.get("title", "")), sub, b.get("tone", "good"), bid, esc(b.get("stamp", "Done"))))
        at = max(at, go + 0.6)
        js("tl.fromTo('#%s-c', { opacity: 0, y: 50, rotation: -1.5 }, { opacity: 1, y: 0, rotation: 0, duration: 0.6, ease: '%s' }, %.3f);" % (bid, EASE, go))
        cue("card", go + 0.03, b, prio=0)
        js("tl.fromTo('#%s-s', { opacity: 0, scale: 2.4, rotation: -4 }, { opacity: 1, scale: 1, rotation: -9, duration: 0.22, ease: 'power4.in' }, %.3f);" % (bid, at - 0.22))
        js("tl.fromTo('#%s-c', { x: 0 }, { keyframes: [{ x: -8, y: 6, duration: 0.05 }, { x: 6, y: -3, duration: 0.06 }, { x: 0, y: 0, duration: 0.1 }] }, %.3f);" % (bid, at))
        cue("hit", at, b, prio=2)
        moments.append((at + 0.5, bid + " stamped"))

    elif t == "strike":
        # the wrong idea is crossed out, the right one is written under it
        at = max(t0 + 0.6, when(b.get("at"), "at", t0, what="%s at" % bid) if b.get("at") is not None else t0 + 1.2)
        nt = max(at + 0.35, when(b.get("new_at"), "at", t0, what="%s new_at" % bid) if b.get("new_at") is not None else at + 0.45)
        old = [b["old"]] if isinstance(b.get("old"), str) else b.get("old", [])
        new = [b["new"]] if isinstance(b.get("new"), str) else b.get("new", [])
        size = int(b.get("size") or fit(old + new, 150, 930, 0.47, 72))
        olds = "".join('<div class="sk-line"><span class="ln"><span>%s</span></span><i class="sk-bar"></i></div>' % mk(l) for l in old)
        news = "".join('<span class="ln"><span>%s</span></span>' % mk(l) for l in new)
        go = scene(b, '<div class="body sk-body">%s<div class="disp sk-old" id="%s-o" style="font-size:%dpx">%s</div>'
                      '<div class="disp sk-new" id="%s-n" style="font-size:%dpx">%s</div></div>' % (kicker(b), bid, size, olds, bid, size, news))
        at, nt = max(at, go + 0.5), max(nt, go + 0.85)
        js("tl.fromTo('#%s .kicker', { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, go))
        js("tl.fromTo('#%s-o .ln > span', { yPercent: 112 }, { yPercent: 0, duration: 0.62, ease: '%s', stagger: 0.09 }, %.3f);" % (bid, EASE, go + 0.05))
        js("tl.fromTo('#%s-o .sk-bar', { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: 'power3.inOut', stagger: 0.12 }, %.3f);" % (bid, at))
        js("tl.to('#%s-o .ln', { opacity: 0.4, duration: 0.3, ease: 'power2.out' }, %.3f);" % (bid, at + 0.2))
        js("tl.fromTo('#%s-n .ln > span', { yPercent: 112 }, { yPercent: 0, duration: 0.66, ease: '%s', stagger: 0.09 }, %.3f);" % (bid, EASE, nt))
        cue("line", go + 0.1, b, prio=0)
        cue("error", at + 0.05, b, prio=2)
        cue("payoff", nt + 0.1, b, prio=2)
        moments += [(at + 0.45, bid + " struck"), (nt + 0.7, bid + " new")]

    elif t == "receipt":
        # costs print one line at a time, then the total counts up: "it all adds up"
        rows_in = items_of(b, "rows")
        pre, suf, dec = b.get("prefix", "$"), b.get("suffix", ""), int(b.get("decimals", 0))
        total = float(b["total"]) if b.get("total") is not None else sum(float(d.get("value", 0)) for d in rows_in)
        rows = ""
        for i, d in enumerate(rows_in):
            v = d.get("text") or "%s%s%s" % (pre, "{:,.{d}f}".format(float(d.get("value", 0)), d=dec), suf)
            rows += '<div class="rc-row" id="%s-i%d"%s><span>%s</span><b>%s</b></div>' % (bid, i, item_attr(d), mk(d["_text"]), mk(v))
        tt = max(max([d["_t"] for d in rows_in] or [t0]) + 0.6,
                 when(b.get("total_at"), "at", t0, what="%s total" % bid) if b.get("total_at") is not None else 0)
        go = scene(b, '<div class="body rc-body">%s<div class="rc" id="%s-w"><div class="rc-h">%s</div><div class="rc-rows">%s</div>'
                      '<div class="rc-tot" id="%s-t"><span>%s</span><b class="disp" id="%s-v"></b></div></div></div>'
                   % (kicker(b), bid, mk(b.get("title", "Receipt")), rows, bid, mk(b.get("total_label", "Total")), bid))
        js("tl.fromTo('#%s .kicker', { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, go))
        js("tl.fromTo('#%s-w', { opacity: 0, y: -60 }, { opacity: 1, y: 0, duration: 0.6, ease: '%s' }, %.3f);" % (bid, EASE, go))
        cue("card", go + 0.03, b, prio=0)
        for i, d in enumerate(rows_in):
            ti = max(go + 0.4, d["_t"])
            js("tl.fromTo('#%s-i%d', { opacity: 0, y: -14 }, { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' }, %.3f);" % (bid, i, ti))
            cue("item", ti + 0.02, b)
        tt = max(tt, go + 0.8)
        js("tl.fromTo('#%s-t', { opacity: 0 }, { opacity: 1, duration: 0.3 }, %.3f);" % (bid, tt - 0.05))
        js("count('#%s-v', 0, %s, %.3f, 0.9, %s);" % (bid, json.dumps(total), tt, json.dumps({"prefix": pre, "suffix": suf, "dec": dec})))
        cue("land", tt + 0.85, b, prio=2)
        moments.append((tt + 1.2, bid + " total"))

    elif t == "gauge":
        # a needle swings from where it was to where it is: a score, a speed, a risk
        lo, hi = float(b.get("min", 0)), float(b.get("max", 100))
        val, frm = float(b["value"]), float(b.get("from", lo))
        frac = lambda v: max(0.0, min(1.0, (v - lo) / (hi - lo) if hi != lo else 0))
        at = max(t0 + 0.3, when(b.get("at"), "at", t0, what="%s at" % bid) if b.get("at") is not None else t0 + 0.6)
        dur = float(b.get("count", 1.3))
        R = 360
        L = math.pi * R
        lab = '<div class="nlabel ga-lab" id="%s-l">%s</div>' % (bid, mk(b["label"])) if b.get("label") else ""
        ends = '<div class="ga-ends"><span>%s</span><span>%s</span></div>' % (mk(b.get("min_label", "{:,g}".format(lo))), mk(b.get("max_label", "{:,g}".format(hi))))
        svg = ('<svg class="ga" viewBox="0 0 800 440" width="800" height="440">'
               '<path class="ga-trk" d="M 40 400 A %d %d 0 0 1 760 400"/>'
               '<path class="ga-fill" id="%s-f" d="M 40 400 A %d %d 0 0 1 760 400" stroke-dasharray="%.1f" stroke-dashoffset="%.1f"/>'
               '<g id="%s-n" class="ga-ndl"><line x1="400" y1="400" x2="400" y2="96"/><circle cx="400" cy="400" r="24"/></g></svg>'
               % (R, R, bid, R, R, L, L, bid))
        go = scene(b, '<div class="body ga-body">%s%s%s<div class="disp nbig ga-v" id="%s-v"></div>%s</div>' % (kicker(b), svg, ends, bid, lab))
        at = max(at, go + 0.4)
        js("tl.fromTo('#%s .kicker', { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, go))
        js("tl.fromTo('#%s .ga, #%s .ga-ends', { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.55, ease: '%s' }, %.3f);" % (bid, bid, EASE, go))
        js("tl.fromTo('#%s-n', { rotation: %.2f, svgOrigin: '400 400' }, { rotation: %.2f, svgOrigin: '400 400', duration: %.2f, ease: 'elastic.out(1, 0.55)' }, %.3f);" % (bid, -90 + 180 * frac(frm), -90 + 180 * frac(val), dur, at))
        js("tl.fromTo('#%s-f', { strokeDashoffset: %.1f }, { strokeDashoffset: %.1f, duration: %.2f, ease: '%s' }, %.3f);" % (bid, L * (1 - frac(frm)), L * (1 - frac(val)), dur * 0.8, EASE, at))
        js("count('#%s-v', %s, %s, %.3f, %.2f, %s);" % (bid, json.dumps(frm), json.dumps(val), at, dur * 0.8,
                                                         json.dumps({"prefix": b.get("prefix", ""), "suffix": b.get("suffix", ""), "dec": int(b.get("decimals", 0))})))
        if b.get("label"):
            js("tl.fromTo('#%s-l', { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.5, ease: '%s' }, %.3f);" % (bid, EASE, at + dur * 0.7))
        cue("grow", at + 0.05, b)
        cue("land", at + dur * 0.75, b, prio=2)
        moments.append((at + dur + 0.3, bid + " landed"))

    elif t == "raw":
        times = {k: when(v, "at", t0, what="%s times.%s" % (bid, k)) for k, v in (b.get("times") or {}).items()}
        for k, v in times.items():
            moments.append((v + 0.6, "%s %s" % (bid, k)))
        if b["_full"]:
            go = scene(b, '<div class="body">%s</div>' % b.get("html", ""))
        else:
            host(bid, t0, t1, '<div class="t-%s rawo" id="%s">%s</div>' % (OVL, bid, b.get("html", "")), b["anchor"], z=12)
            go = t0
        # the hand-written timeline: T0/T1 = the beat's window, GO = when content may move (after a wipe), AT = resolved "times",
        # $ = a selector scoped to this beat. Helpers: rise, maskIn, pop, count, typeIn, draw, fadeOut, checkIn (see SKILL.md).
        js("(function (T0, T1, GO, AT, $) {\n%s\n        })(%.3f, %.3f, %.3f, %s, function (s) { return '#%s ' + s; });"
           % (b.get("js", ""), t0, t1, go, json.dumps(times), bid))

    else:
        err("beat %s: unknown type %r (overlays: %s; scenes: %s; or raw)" % (bid, t, " ".join(sorted(OVERLAYS)), " ".join(sorted(SCENES))))

# ---- voiceover stretches need something on screen: paper alone is a hole ------------------------------------
fulls = sorted((b["_in"], b["_out"], b["id"]) for b in beats if b["_full"])
for a, e in VO:
    t = a
    for f0, f1, _ in fulls:
        if f1 <= t or f0 >= e:
            continue
        if f0 - t > 1.2:
            warn("voiceover %.1f-%.1f s has no scene (only paper and captions): add a beat" % (t, f0))
        t = max(t, f1)
    if e - t > 1.2:
        warn("voiceover %.1f-%.1f s has no scene (only paper and captions): add a beat" % (t, e))
# two overlays in the same place at once
ovs = sorted((b["_in"], b["_out"], b["id"], int(b.get("top", OTOP))) for b in beats if not b["_full"])
for (a0, a1, ia, ta), (b0, b1, ib, tb) in zip(ovs, ovs[1:]):
    if b0 < a1 - 0.3 and abs(ta - tb) < 120:
        warn("overlays %s and %s overlap in time and place (%.1f-%.1f s): end one earlier or give one a different \"top\"" % (ia, ib, b0, a1))
seq = [b["type"] for b in order if b["type"] not in ("chip", "clip")]
for (x, y), bb in zip(zip(seq, seq[1:]), [b for b in order if b["type"] not in ("chip", "clip")][1:]):
    if x == y:
        warn("the same format twice in a row: %s at %.1f s (vary the device)" % (y, bb["_in"]))

# ============================================================ camera ==========================================
frame = S.get("frame") or {}
BASE = float(frame.get("scale", 1.0))
cam_js = []
cam = S.get("camera", "auto")
jump_cuts = [c for c in (CUTMAP["cuts"] if CUTMAP else []) if not in_vo(c) and not in_vo(c - 0.05)]
if cam == "auto":
    # jump cuts read as mistakes at one framing and as intent at two: alternate a small punch-in at cuts at least 1.4 s apart
    ops, tight, last = [], False, -9.0
    for c in jump_cuts:
        if c - last >= 1.4:
            tight = not tight
            ops.append(["set", c, round(BASE * (1.085 if tight else 1.0), 4)])
            last = c
    cam = ops
elif cam in (None, "none", False):
    cam = []
for op in cam:
    kind = op[0]
    tt = when(op[1], "at", 0.0, what="camera %s" % kind)
    if kind == "set":
        near = [c for c in jump_cuts if abs(c - tt) < 0.12]       # a reset belongs on the jump frame itself, a hair early
        tt = (near[0] if near else tt) - 0.003
        cam_js.append("tl.set('#video-zoom', { scale: %.4f }, %.4f);" % (float(op[2]), max(0.0, tt)))
    elif kind == "creep":
        t2 = when(op[2], "out", tt, base=tt, what="camera creep end")
        cam_js.append("tl.to('#video-zoom', { scale: %.4f, duration: %.3f, ease: 'power1.inOut' }, %.3f);" % (float(op[3]), max(0.3, t2 - tt), tt))
    elif kind == "punch":
        cam_js.append("tl.to('#video-zoom', { scale: %.4f, duration: 0.32, ease: 'power2.out' }, %.3f);" % (float(op[2]), tt))
    elif kind == "release":
        cam_js.append("tl.to('#video-zoom', { scale: %.4f, duration: %.3f, ease: 'power2.inOut' }, %.3f);" % (BASE, float(op[2]) if len(op) > 2 else 0.45, tt))
    else:
        err("camera op %r: use set, creep, punch or release" % kind)
if BASE < 1.0:
    err("frame.scale under 1.0 would show the edge of the footage")

# ============================================================ captions ========================================
C = S.get("captions") or {}
CAP_Y = int(C.get("y", {"full": 1400, "split": CAM["y"] + 65, "inset": CAM["y"] - 80}[LAYOUT]))     # split: on the seam, above the head, never over the mouth
CAP_SIZE = int(C.get("size", 58))
CAP_STYLE = C.get("style", "pill")
MAXC, MAXW = int(C.get("max_chars", 18)), int(C.get("max_words", 4))
CASE = C.get("case", "as-is")


def phrase_hits(phrase):
    """Every place a phrase is said, as (first word index, last word index)."""
    p = norm(phrase)
    out = []
    for i in range(len(FLAT) - len(p) + 1):
        if p and all(FLAT[i + k][0] == p[k] for k in range(len(p))):
            out.append((FLAT[i][3], FLAT[i + len(p) - 1][3]))
    return out


# display words: start from the transcript, then apply "replace" (fix a mishearing, or merge several words into one)
disp = [{"text": w["text"], "start": w["start"], "end": w["end"], "i": [i]} for i, w in enumerate(WORDS)]
for r in C.get("replace", []):
    hits = phrase_hits(r["say"])
    if not hits:
        warn('captions.replace: "%s" is not said' % r["say"])
    show = str(r["show"]).split(" ")
    for a, b_ in reversed(hits):
        ia = next((k for k, d in enumerate(disp) if a in d["i"]), None)
        ib = next((k for k, d in enumerate(disp) if b_ in d["i"]), None)
        if ia is None or ib is None:
            continue
        chunk = disp[ia:ib + 1]
        tail = re.search(r"[.,!?;:]+$", chunk[-1]["text"])
        tail = tail.group(0) if tail and not re.search(r"[.,!?;:]$", show[-1]) else ""
        if len(show) == len(chunk):
            new = [dict(c, text=s) for c, s in zip(chunk, show)]
        else:                                   # a different word count: one caption word spanning the whole phrase
            new = [{"text": " ".join(show), "start": chunk[0]["start"], "end": chunk[-1]["end"], "i": [x for c in chunk for x in c["i"]]}]
        new[-1]["text"] += tail
        disp[ia:ib + 1] = new
emph = {}
for e in C.get("emphasis", []):
    hits = phrase_hits(e["say"])
    if not hits:
        warn('captions.emphasis: "%s" is not said' % e["say"])
    if e.get("nth"):
        hits = hits[int(e["nth"]) - 1:int(e["nth"])]
    for a, b_ in hits:
        for k in range(a, b_ + 1):
            emph[k] = e
break_at = set()
for ph in C.get("breaks", []):
    for a, _ in phrase_hits(ph):
        break_at.add(a)
hide = [(float(a), float(b_)) for a, b_ in C.get("hide", [])]


def cap_text(s):
    s = re.sub(r"[,;:]+$", "", s)                 # commas and full stops clutter a caption; ? and ! carry tone
    s = re.sub(r"\.+$", "", s)
    return s.upper() if CASE == "upper" else (s.lower() if CASE == "lower" else s)


groups, cur = [], []


def flush():
    global cur
    if cur:
        groups.append(cur)
    cur = []


for k, d in enumerate(disp):
    txt = cap_text(d["text"])
    if not txt:
        continue
    d = dict(d, show=txt, end_sentence=bool(re.search(r"[.!?]$", d["text"])), comma=bool(re.search(r"[,;:]$", d["text"])))
    if cur:
        length = sum(len(x["show"]) for x in cur) + len(cur) + len(txt)
        gap = d["start"] - cur[-1]["end"]
        if (length > MAXC or len(cur) >= MAXW or cur[-1]["end_sentence"] or gap > 0.5 or d["i"][0] in break_at
                or (cur[-1]["comma"] and len(cur) >= 2)):
            flush()
    cur.append(d)
flush()
# a lone short word at the end of a sentence reads as a stutter: pull it back into the caption before it when it fits
merged = []
for g in groups:
    if (merged and len(g) == 1 and len(g[0]["show"]) <= 6 and not merged[-1][-1]["end_sentence"] and g[0]["start"] - merged[-1][-1]["end"] < 0.35
            and sum(len(x["show"]) for x in merged[-1]) + len(merged[-1]) + len(g[0]["show"]) <= MAXC + 6 and len(merged[-1]) < MAXW + 1
            and g[0]["i"][0] not in break_at):
        merged[-1].append(g[0])
    else:
        merged.append(g)
groups = merged

cap_html, cap_js, cap_json, srt = [], [], [], []
TI = dict(TOKENS[OVL] if OVL in GLASS and not OVL == "bloom" else TOKENS["ink"])
TI["accent"] = TI.get("pop", TI["accent"])      # captions: dark pill; glass looks lend their accents
EM_COL = {"accent": TI["accent"], "money": TI["money"], "good": TI["good"], "bad": TI["bad"], "paper": TI["fg"]}
for gi, g in enumerate(groups):
    s = max(0.0, g[0]["start"] - 0.03)
    nxt = groups[gi + 1][0]["start"] - 0.03 if gi + 1 < len(groups) else D
    e = min(nxt - 0.02, g[-1]["end"] + 0.5, D)
    if e - s < 0.12:
        e = min(D, s + 0.12)
    if any(a <= s < b_ for a, b_ in hide):
        continue
    y = CAP_Y
    for mv in C.get("moves", []):
        if float(mv[0]) <= s < float(mv[1]):
            y = int(mv[2])
    spans = []
    for wi, d in enumerate(g):
        e_ = next((emph[i] for i in d["i"] if i in emph), None)
        base = EM_COL.get((e_ or {}).get("color", "accent"), TI["accent"]) if e_ else TI["fg"]
        cls = "cw" + (" em" if e_ else "") + (" it" if e_ and e_.get("italic") else "")
        spans.append('<span class="%s" id="cw%d-%d" style="color:%s">%s</span>' % (cls, gi, wi, base, esc(d["show"]).replace(" ", "&nbsp;")))
        on = max(s, d["start"] - 0.02)
        off = min(e, g[wi + 1]["start"] - 0.02) if wi + 1 < len(g) else e
        hl = base if e_ else TI["fg"]
        cap_js.append("tl.set('#cw%d-%d', { backgroundColor: '%s', color: '%s' }, %.3f);" % (gi, wi, hl, TI["bg"], on))
        if wi + 1 < len(g):
            cap_js.append("tl.set('#cw%d-%d', { backgroundColor: 'rgba(0,0,0,0)', color: '%s' }, %.3f);" % (gi, wi, base, off))
    cap_html.append('      <div class="cg %s" id="cg%d" style="top:%dpx">%s</div>' % (CAP_STYLE, gi, y, " ".join(spans)))
    cap_js.append("tl.set('#cg%d', { visibility: 'visible' }, %.3f);" % (gi, s))
    cap_js.append("tl.fromTo('#cg%d', { scale: 0.93 }, { scale: 1, duration: 0.16, ease: 'back.out(2.2)' }, %.3f);" % (gi, s))
    cap_js.append("tl.set('#cg%d', { visibility: 'hidden' }, %.3f);" % (gi, e))
    text = " ".join(d["show"] for d in g)
    cap_json.append({"n": gi, "start": round(s, 3), "end": round(e, 3), "text": text,
                     "words": [{"text": d["show"], "start": round(d["start"], 3), "end": round(d["end"], 3)} for d in g]})
    stamp = lambda x: "%02d:%02d:%02d,%03d" % (int(x // 3600), int(x % 3600 // 60), int(x % 60), int(round((x - int(x)) * 1000)) % 1000)
    srt.append("%d\n%s --> %s\n%s\n" % (len(srt) + 1, stamp(s), stamp(e), text))
save(os.path.join(P, "captions.json"), cap_json)
with open(os.path.join(P, "captions.srt"), "w", encoding="utf-8") as f:
    f.write("\n".join(srt))
if not WORDS:
    warn("no transcript.json: the video has NO captions (captions are mandatory on a Short)")
wide = [c for c in cap_json if len(c["text"]) > MAXC + 8]
for c in wide[:5]:
    warn('caption "%s" is long (%d characters): add a captions.breaks phrase inside it' % (c["text"], len(c["text"])))

# ============================================================ sound ===========================================
for c in S.get("cues", []):
    name = c[0]
    tt = when(c[1], "at", 0.0, what="cue %s" % name)
    if name == "riser":
        tt = max(0.0, tt - float(SFX_MAN.get("riser", {}).get("duration", 10.0)))      # a riser crests at its END: start it that much early
    cues.append((tt, name, float(c[2]) if len(c) > 2 else 0.15, 3))
cues.sort(key=lambda c: (c[0], -c[3]))
kept = []
for c in cues:
    if c[1] not in SFX_MAN:
        err("sound %r is not in the library (%s)" % (c[1], " ".join(sorted(SFX_MAN))))
        continue
    if kept and c[0] - kept[-1][0] < 0.09:        # two sounds on the same frame smear: keep the more important one
        if c[3] > kept[-1][3]:
            kept[-1] = c
        continue
    kept.append(c)
atracks = {}
for n, (tt, name, vol, _) in enumerate(kept):
    dur = min(float(SFX_MAN[name]["duration"]), max(0.1, D - tt))
    k = 40
    while atracks.get(k, -1.0) > tt - 0.02:
        k += 1
    atracks[k] = tt + dur
    stage(os.path.join(SKILL, "assets", "sfx", SFX_MAN[name]["file"]), os.path.join(OUT, "sfx", SFX_MAN[name]["file"]))
    audio_parts.append('    <audio id="sfx-%d" src="sfx/%s" data-start="%.3f" data-duration="%.3f" data-track-index="%d" data-volume="%.3f"></audio>\n'
                       % (n, SFX_MAN[name]["file"], tt, dur, k, vol))
for i in range(0, int(D) + 1, 10):
    n = sum(1 for c in kept if i <= c[0] < i + 10 and c[3] >= 1)      # the soft under-layer (cards, lines) is not counted
    if n > 7:
        warn("%d sounds between %d and %d s: that is busy. Silence a beat with \"sfx\": false, or set \"mood\": \"calm\"" % (n, i, i + 10))

if errors:
    print("COMPOSE FAILED: %d problem(s)" % len(errors))
    for e in errors:
        print("  ERROR " + e)
    sys.exit(1)

# ============================================================ css =============================================
def theme_css(name):
    return ".t-%s { %s }" % (name, " ".join("--%s:%s;" % kv for kv in TOKENS[name].items()))


CSS = """
  @font-face { font-family:"Fraunces"; src:url("fonts/Fraunces-opsz.woff2") format("woff2"); font-weight:100 900; font-style:normal; font-display:block; }
  @font-face { font-family:"Fraunces"; src:url("fonts/Fraunces-opsz-italic.woff2") format("woff2"); font-weight:100 900; font-style:italic; font-display:block; }
  @font-face { font-family:"Geist"; src:url("fonts/Geist-wght.woff2") format("woff2"); font-weight:100 900; font-display:block; }
  @font-face { font-family:"Geist Mono"; src:url("fonts/GeistMono-wght.woff2") format("woff2"); font-weight:100 900; font-display:block; }
  * { box-sizing:border-box; }
  html, body { margin:0; padding:0; width:100%; height:100%; overflow:hidden; background:#000; font-family:FONT_BODY; }
  #stage { position:relative; width:1080px; height:1920px; overflow:hidden; background:#000; }
  THEMES
  .video-wrapper { position:absolute; left:0; top:0; width:1080px; height:1920px; overflow:hidden; }
  #video-zoom { position:absolute; inset:0; transform-origin:ORIGIN; will-change:transform; }
  #video-zoom video { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; display:block; }
  #cam-shade { position:absolute; inset:0; z-index:3; pointer-events:none;
    background: linear-gradient(180deg, rgba(21,19,15,.46) 0px, rgba(21,19,15,0) 420px), linear-gradient(0deg, rgba(21,19,15,.50) 0px, rgba(21,19,15,0) 640px); }
  .cutaway-video { position:absolute; left:0; top:0; width:1080px; height:1920px; object-fit:cover; z-index:8; }
  .card-host { position:absolute; left:0; top:0; width:1080px; height:1920px; pointer-events:none; overflow:hidden; visibility:hidden; }
  .disp { font-family:FONT_DISPLAY; font-weight:560; letter-spacing:-.022em; line-height:1.03; color:var(--fg); font-optical-sizing:auto; }
  .disp em, .t em { font-family:FONT_DISPLAY; font-style:italic; font-weight:480; color:var(--accent);
    background:linear-gradient(100deg, var(--accent) 10%, var(--accent2) 95%); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
    padding:0 .06em; margin:0 -.06em; }
  .ln { display:block; overflow:hidden; padding:.06em .04em .16em; margin:-.06em -.04em -.16em; }
  .ln > span { display:inline-block; white-space:nowrap; }
  .kicker { display:flex; align-items:center; gap:22px; font-weight:600; font-size:34px; line-height:1; letter-spacing:.2em; text-transform:uppercase; color:var(--accent); white-space:nowrap; }
  .kicker::before { content:""; width:56px; height:2px; background:currentColor; opacity:.85; flex:none; }
  .kicker em { font-style:normal; color:var(--fg); }
  svg.icn { fill:none; stroke:currentColor; stroke-width:3.4; stroke-linecap:round; stroke-linejoin:round; display:block; }
  svg.mk { flex:none; overflow:visible; } svg.mk .ring { fill:transparent; stroke:var(--faint); stroke-width:3; }
  svg.mk .tick { fill:none; stroke:var(--on-accent); stroke-width:4.6; stroke-linecap:round; stroke-linejoin:round; }

  /* ---------- overlays over the face cam: ink cards, hairline border, the free space above the head ---------- */
  .ocard { position:absolute; left:60px; right:60px; padding:36px 42px 38px; background:var(--panel); border:1px solid var(--line); border-radius:14px;
    box-shadow:0 26px 70px rgba(0,0,0,.45); color:var(--fg); }
  .ocard .kicker { font-size:28px; margin-bottom:24px; }
  .ocard .row { display:flex; align-items:center; gap:28px; }
  .ocard .ttl { font-size:82px; } .ocard .sub { margin-top:10px; font-size:40px; font-weight:450; color:var(--soft); line-height:1.25; }
  .ic-box { flex:none; width:104px; height:104px; border-radius:12px; background:var(--accent-soft); color:var(--accent); display:flex; align-items:center; justify-content:center; }
  .olist .items { display:flex; flex-direction:column; gap:20px; }
  .olist .item { display:none; align-items:center; gap:24px; }
  .olist .item .t { font-size:60px; font-weight:650; line-height:1.1; letter-spacing:-.015em; color:var(--fg); }
  .olist .item .d { flex:none; width:16px; height:16px; border-radius:50%; background:var(--accent); }
  .olist .item .num { flex:none; font-family:FONT_DISPLAY; font-style:italic; font-size:44px; color:var(--accent); width:64px; }
  .ostat .big { font-size:168px; line-height:.95; letter-spacing:-.03em; font-variant-numeric:tabular-nums lining-nums; }
  .oprog .prow { display:flex; align-items:baseline; gap:24px; }
  .oprog .big { font-size:136px; line-height:.95; font-variant-numeric:tabular-nums lining-nums; }
  .oprog .goal { font-size:46px; color:var(--soft); } .oprog .goal b { color:var(--fg); font-weight:650; }
  .ptrack { position:relative; margin-top:30px; height:14px; border-radius:7px; background:var(--raised); }
  .pfill { position:absolute; left:0; top:0; bottom:0; width:100%; border-radius:7px; background:var(--accent); transform-origin:0 50%; }
  .ppin { position:absolute; top:50%; width:34px; height:34px; margin:-17px 0 0 -17px; border-radius:50%; background:var(--fg); border:6px solid var(--accent); }
  .pflag { position:absolute; right:0; top:-14px; bottom:-14px; width:0; border-right:3px dashed var(--faint); }
  .chip { position:absolute; left:60px; display:inline-flex; align-items:center; gap:18px; padding:20px 30px; border-radius:999px; background:var(--panel);
    border:1px solid var(--line); color:var(--fg); font-size:38px; font-weight:600; letter-spacing:.01em; white-space:nowrap; box-shadow:0 16px 44px rgba(0,0,0,.4); }
  .chip.right { left:auto; right:60px; } .chip em { font-style:normal; color:var(--accent); }
  .chip .dot { width:16px; height:16px; border-radius:50%; background:LIVE; box-shadow:0 0 0 6px rgba(255,90,79,.22); }
  .otitle { position:absolute; left:60px; right:60px; color:#f5f2ec; text-shadow:0 4px 18px rgba(0,0,0,.6), 0 2px 4px rgba(0,0,0,.5); }
  .plate { position:absolute; left:60px; width:250px; height:250px; border-radius:14px; background:#fbf9f5; display:flex; align-items:center; justify-content:center;
    box-shadow:0 22px 60px rgba(0,0,0,.45); } .plate.right { left:auto; right:60px; }
  .plate img { max-width:170px; max-height:170px; display:block; }
  .pills { position:absolute; left:60px; right:60px; display:flex; flex-wrap:wrap; gap:18px; }
  .pill { display:inline-flex; align-items:center; gap:14px; padding:20px 30px; border-radius:999px; background:var(--panel); border:1px solid var(--line);
    color:var(--fg); font-size:44px; font-weight:600; white-space:nowrap; box-shadow:0 14px 40px rgba(0,0,0,.4); }
  .pill.accent { background:var(--accent); color:var(--on-accent); border-color:transparent; } .pill.money { color:var(--money); } .pill.good { color:var(--good); }
  .osub .yt { flex:none; width:104px; height:104px; border-radius:12px; background:#e5372c; color:#fff; display:flex; align-items:center; justify-content:center; }
  .osub .grow { flex:1; } .osub .ttl { font-size:70px; }
  .osub .row2 { display:flex; align-items:center; gap:26px; margin-top:28px; }
  .sbtn { padding:20px 38px; border-radius:999px; background:#f0ede4; color:#15130f; font-size:42px; font-weight:650; } .sbtn .s1 { display:none; }
  .osub .bell { color:var(--soft); transform-origin:50% 10%; }
  .rawo { position:absolute; inset:0; }

  /* ---------- scenes: full frame, paper or ink. Content lives between y 250 and y 1250 (captions sit below) ---------- */
  .sc { position:absolute; inset:0; background:var(--bg); color:var(--fg); overflow:hidden; }
  .grain { position:absolute; inset:0; opacity:.5; mix-blend-mode:multiply; pointer-events:none;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' seed='11' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0.16 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }
  .t-ink .grain { mix-blend-mode:screen; opacity:.35; }
  .chrome { position:absolute; left:72px; right:72px; top:150px; display:flex; justify-content:space-between; align-items:center; }
  .chrome .kicker { font-size:26px; } .chrome-r { font-size:28px; font-weight:600; color:var(--soft); letter-spacing:.02em; }
  .chrome-r em { font-style:normal; color:var(--accent); }
  .chrome-line { position:absolute; left:72px; right:72px; top:204px; height:1px; background:var(--line); }
  .body { position:absolute; left:72px; right:72px; top:290px; bottom:670px; display:flex; flex-direction:column; justify-content:center; }
  .body > .kicker { margin-bottom:38px; }
  .sttl { font-size:96px; margin-bottom:44px; }
  .ssub { margin-top:40px; font-size:50px; line-height:1.28; font-weight:450; color:var(--soft); max-width:900px; }
  .slabel { margin-top:36px; font-size:44px; font-weight:600; color:var(--fg); line-height:1.2; } .slabel em { font-style:normal; color:var(--accent); }
  .nb-body .nbig { line-height:.92; letter-spacing:-.04em; font-variant-numeric:tabular-nums lining-nums; color:var(--fg); }
  .nrule { width:100%; height:2px; background:var(--fg); margin:34px 0 30px; transform-origin:0 50%; }
  .nlabel { font-size:70px; font-weight:650; letter-spacing:-.015em; line-height:1.1; } .nlabel em { font-style:normal; color:var(--accent); }
  .steps { display:flex; flex-direction:column; }
  .step { display:flex; align-items:center; gap:34px; padding:36px 0; border-top:1px solid var(--line); }
  .step:last-child { border-bottom:1px solid var(--line); }
  .step .idx { flex:none; width:132px; font-style:italic; font-weight:480; font-size:100px; color:var(--accent); line-height:1; }
  .step .t { font-size:74px; font-weight:650; letter-spacing:-.02em; line-height:1.06; } .step .s { margin-top:10px; font-size:42px; color:var(--soft); line-height:1.25; }
  .steps.n4 .step { padding:28px 0; } .steps.n4 .step .t { font-size:66px; } .steps.n5 .step { padding:20px 0; } .steps.n5 .step .t { font-size:58px; } .steps.n5 .step .s { font-size:36px; } .steps.n5 .step .idx { font-size:80px; }
  .steps.n6 .step { padding:14px 0; } .steps.n6 .step .t { font-size:52px; } .steps.n6 .step .s { font-size:32px; } .steps.n6 .step .idx { font-size:70px; }
  .step svg.mk { width:72px; height:72px; margin:0 16px; }
  .flowcol { display:flex; flex-direction:column; align-items:stretch; }
  .node { display:flex; align-items:center; gap:30px; padding:0 34px; background:var(--card); border:1px solid var(--line); border-radius:14px; box-shadow:0 14px 40px rgba(21,19,15,.08); }
  .node .t { font-size:62px; font-weight:650; letter-spacing:-.018em; line-height:1.08; } .node .s { margin-top:6px; font-size:38px; color:var(--soft); }
  .node.payoff { background:var(--accent); border-color:transparent; color:var(--on-accent); } .node.payoff .s { color:var(--on-accent); opacity:.8; }
  .node.payoff .ic-box { background:rgba(255,255,255,.16); color:var(--on-accent); }
  .conn { position:relative; width:4px; margin-left:86px; } .conn .shaft { position:absolute; inset:0; background:var(--accent); opacity:.55; transform-origin:50% 0%; }
  .conn .pk { position:absolute; left:-6px; top:0; width:16px; height:16px; border-radius:50%; background:var(--accent); }
  .bars { display:flex; flex-direction:column; gap:44px; }
  .brow .bl { display:flex; justify-content:space-between; align-items:baseline; font-size:52px; font-weight:600; margin-bottom:16px; }
  .brow .bl b { font-family:FONT_DISPLAY; font-weight:560; font-size:78px; letter-spacing:-.02em; }
  .btrack { height:46px; border-radius:6px; background:var(--raised); overflow:hidden; } .bfill { width:100%; height:100%; background:var(--faint); transform-origin:0 50%; border-radius:6px; }
  .brow.hi .bfill { background:var(--accent); } .brow.hi .bl b { color:var(--accent); }
  .bw-body, .tm-body, .im-body { justify-content:flex-start; top:250px; bottom:600px; } .bw-body > .kicker, .tm-body > .kicker, .im-body > .kicker { margin-bottom:30px; }
  .win { position:relative; align-self:center; border-radius:16px; overflow:hidden; background:#fff; border:1px solid var(--line); box-shadow:0 34px 90px rgba(21,19,15,.22); flex:none; }
  .win.phone { border-radius:64px; border:12px solid #15130f; }
  .bbar { position:absolute; left:0; right:0; top:0; height:66px; background:var(--raised); display:flex; align-items:center; gap:10px; padding:0 22px; z-index:2; border-bottom:1px solid var(--line); }
  .bbar i { width:15px; height:15px; border-radius:50%; background:var(--faint); opacity:.6; }
  .bbar .url { margin-left:16px; padding:9px 22px; border-radius:999px; background:var(--card); color:var(--soft); font-size:24px; font-weight:500; line-height:1; }
  .pagewrap { position:absolute; left:0; right:0; bottom:0; overflow:hidden; } .pg { position:absolute; left:0; top:0; } .pg img { display:block; height:auto; }
  .callout { position:absolute; border:5px solid var(--accent); border-radius:12px; box-shadow:0 0 0 9999px rgba(21,19,15,.34); }
  .term { border-radius:16px; overflow:hidden; background:#15130f; border:1px solid rgba(240,237,228,.16); box-shadow:0 34px 90px rgba(21,19,15,.3); }
  .tbar { height:66px; display:flex; align-items:center; gap:10px; padding:0 24px; background:#1d1a15; border-bottom:1px solid rgba(240,237,228,.1); }
  .tbar i { width:15px; height:15px; border-radius:50%; background:#726d62; } .tbar span { margin-left:14px; font-family:FONT_MONO; font-size:26px; color:#a7a297; }
  .tlines { padding:38px 40px 46px; min-height:600px; font-family:FONT_MONO; font-size:46px; line-height:1.5; color:#f0ede4; }
  .tl { display:none; white-space:pre-wrap; word-break:break-word; min-height:1.55em; } .tl.good { color:#62c890; } .tl.bad { color:#f08070; } .tl.dim { color:#a7a297; } .tl.accent { color:#9fb0f0; }
  .imcard { align-self:center; width:936px; max-height:860px; border-radius:16px; overflow:hidden; border:1px solid var(--line); box-shadow:0 34px 90px rgba(21,19,15,.22); }
  .imcard img { display:block; width:100%; height:auto; }
  .imfull { position:absolute; left:0; top:0; width:1080px; height:1920px; object-fit:cover; }
  .imshade { position:absolute; inset:0; background:linear-gradient(0deg, rgba(21,19,15,.72) 0%, rgba(21,19,15,0) 50%); }
  .im-cover { justify-content:flex-end; } .im-cover .slabel { color:#f5f2ec; font-size:56px; text-shadow:0 3px 14px rgba(0,0,0,.6); }
  .cliplabel { position:absolute; left:72px; right:72px; top:1090px; font-size:56px; font-weight:650; line-height:1.15; color:#f5f2ec; text-shadow:0 3px 14px rgba(0,0,0,.7), 0 1px 3px rgba(0,0,0,.6); }
  .cliplabel em { font-style:normal; color:#9fb0f0; }
  .ct-body { align-items:flex-start; } .cphoto { width:210px; height:210px; border-radius:50%; overflow:hidden; border:6px solid var(--card); box-shadow:0 18px 50px rgba(21,19,15,.2); margin-bottom:44px; }
  .cphoto img { width:100%; height:100%; object-fit:cover; display:block; }
  .curl { position:relative; margin-top:50px; padding:26px 44px; border-radius:999px; background:var(--fg); color:var(--bg); font-size:52px; font-weight:650; letter-spacing:-.01em; }
  .curl i { position:absolute; left:44px; right:44px; bottom:20px; height:3px; background:var(--bg); opacity:.7; transform-origin:0 50%; }
  .cchips { display:flex; flex-wrap:wrap; gap:16px; margin-top:34px; } .cchip { padding:16px 28px; border-radius:999px; border:1px solid var(--line); background:var(--card); font-size:34px; font-weight:550; color:var(--soft); }
  /* action scenes */
  .slots { display:flex; flex-direction:column; gap:26px; }
  .slot { position:relative; display:flex; align-items:center; gap:30px; min-height:150px; padding:20px 34px; border:3px dashed var(--faint); border-radius:16px; }
  .slot .sl-n { flex:none; width:110px; font-style:italic; font-size:84px; color:var(--faint); line-height:1; }
  .slot .sl-q { font-family:FONT_DISPLAY; font-size:84px; color:var(--faint); opacity:.6; }
  .slot .sl-fill { position:absolute; left:174px; right:34px; top:50%; translate:0 -50%; opacity:0; }
  .slot .t { font-size:66px; font-weight:650; letter-spacing:-.02em; line-height:1.06; } .slot .s { margin-top:8px; font-size:38px; color:var(--soft); }
  .slot.on { border-style:solid; border-color:transparent; background:var(--card); box-shadow:0 14px 40px rgba(21,19,15,.1); } .slot.on .sl-n { color:var(--accent); }
  .slots.n5 .slot { min-height:120px; } .slots.n5 .slot .t { font-size:56px; }
  .vs { position:relative; display:flex; gap:96px; }
  .vs-col { position:relative; flex:1; padding:44px 36px; min-height:560px; border-radius:16px; background:var(--card); border:1px solid var(--line); box-shadow:0 14px 40px rgba(21,19,15,.08); }
  .vs-col .kicker { margin-bottom:28px; } .vs-col .t { font-size:62px; font-weight:650; letter-spacing:-.02em; line-height:1.08; }
  .vs-col .v { margin-top:26px; font-size:110px; line-height:1; letter-spacing:-.03em; } .vs-col .s { margin-top:18px; font-size:38px; color:var(--soft); line-height:1.25; }
  .vs-col.win { border:4px solid var(--accent); } .vs-col.win .v { color:var(--accent); }
  .vs-x { position:absolute; left:24px; right:24px; top:50%; height:8px; border-radius:4px; background:var(--bad); transform:rotate(-12deg) scaleX(0); transform-origin:0 50%; }
  .vs-ok { position:absolute; right:30px; bottom:30px; } .vs-ok svg.mk { width:84px; height:84px; } .vs-col:not(.win) .vs-ok { display:none; }
  .vs-mid { position:absolute; left:50%; top:50%; translate:-50% -50%; width:84px; height:84px; border-radius:50%; background:var(--fg); color:var(--bg);
    display:flex; align-items:center; justify-content:center; font-style:italic; font-size:40px; z-index:2; }
  .sm-body { align-items:center; }
  .sm-card { position:relative; width:900px; padding:64px 56px; border-radius:16px; background:var(--card); border:1px solid var(--line); box-shadow:0 30px 80px rgba(21,19,15,.16); }
  .sm-card .t { font-size:100px; line-height:1.02; margin-top:6px; } .sm-card .s { margin-top:26px; font-size:44px; color:var(--soft); line-height:1.25; }
  .sm-stamp { position:absolute; right:110px; bottom:120px; padding:18px 40px; border:9px solid var(--good); border-radius:14px; color:var(--good);
    font-size:96px; font-weight:800; letter-spacing:.06em; text-transform:uppercase; mix-blend-mode:multiply; background:rgba(255,255,255,.02); }
  .t-ink .sm-stamp { mix-blend-mode:normal; }
  .sm-stamp.bad { border-color:var(--bad); color:var(--bad); } .sm-stamp.accent { border-color:var(--accent); color:var(--accent); } .sm-stamp.money { border-color:var(--money); color:var(--money); }
  .sk-old { line-height:1.04; } .sk-line { position:relative; display:table; } .sk-new { margin-top:54px; line-height:1.04; color:var(--accent); }
  .sk-bar { position:absolute; left:-14px; right:-14px; top:54%; height:14px; border-radius:7px; background:var(--bad); transform-origin:0 50%; rotate:-2deg; }
  .rc-body { align-items:center; }
  .rc { width:780px; padding:46px 52px 40px; background:#fbf9f5; color:#15130f; font-family:FONT_MONO; box-shadow:0 30px 80px rgba(21,19,15,.2);
    clip-path:polygon(0 0,100% 0,100% calc(100% - 18px),95% 100%,90% calc(100% - 18px),85% 100%,80% calc(100% - 18px),75% 100%,70% calc(100% - 18px),65% 100%,60% calc(100% - 18px),55% 100%,50% calc(100% - 18px),45% 100%,40% calc(100% - 18px),35% 100%,30% calc(100% - 18px),25% 100%,20% calc(100% - 18px),15% 100%,10% calc(100% - 18px),5% 100%,0 calc(100% - 18px)); }
  .rc-h { text-align:center; font-size:34px; letter-spacing:.2em; text-transform:uppercase; padding-bottom:26px; border-bottom:3px dashed rgba(21,19,16,.3); }
  .rc-rows { padding:18px 0; } .rc-row { display:flex; justify-content:space-between; gap:20px; padding:14px 0; font-size:42px; }
  .rc-tot { display:flex; justify-content:space-between; align-items:baseline; padding:26px 0 26px; border-top:3px dashed rgba(21,19,16,.3); font-size:42px; font-weight:700; }
  .rc-tot b { font-family:FONT_DISPLAY; font-size:110px; color:#1d2f6f; font-variant-numeric:tabular-nums lining-nums; }
  .ga-body { align-items:center; } .ga { display:block; overflow:visible; }
  .ga-trk, .ga-fill { fill:none; stroke-width:48; stroke-linecap:round; } .ga-trk { stroke:var(--raised); } .ga-fill { stroke:var(--accent); }
  .ga-ndl line { stroke:var(--fg); stroke-width:12; stroke-linecap:round; } .ga-ndl circle { fill:var(--fg); }
  .ga-ends { width:800px; display:flex; justify-content:space-between; margin-top:10px; font-size:36px; color:var(--soft); font-weight:600; }
  .ga-v { margin-top:24px; font-size:200px; text-align:center; } .ga-lab { text-align:center; margin-top:10px; }

  /* ---------- glass looks (aurora, dusk, bloom): drifting light, frosted cards, gradient accents ---------- */
  .mesh { position:absolute; inset:-260px; pointer-events:none; filter:blur(170px) saturate(1.15); }
  .t-aurora .mesh::after, .t-dusk .mesh::after { content:""; position:absolute; inset:0; background:radial-gradient(ellipse at 50% 42%, transparent 30%, var(--bg) 92%); }
  .mesh i { position:absolute; border-radius:50%; opacity:.62; }
  .mesh .m1 { left:-120px; top:80px; width:900px; height:900px; background:var(--b1); }
  .mesh .m2 { right:-160px; top:640px; width:820px; height:820px; background:var(--b2); }
  .mesh .m3 { left:160px; bottom:-60px; width:960px; height:760px; background:var(--b3); opacity:.38; }
  .t-bloom .mesh i { opacity:.9; }
  .t-aurora .grain, .t-dusk .grain { mix-blend-mode:overlay; opacity:.55; } .t-bloom .grain { opacity:.35; }
  .t-aurora .ocard, .t-dusk .ocard, .t-bloom .ocard { backdrop-filter:blur(26px) saturate(1.5); -webkit-backdrop-filter:blur(26px) saturate(1.5); border-radius:28px; }
  .t-aurora.chip, .t-dusk.chip, .t-bloom.chip, .t-aurora.pill, .t-dusk.pill, .t-bloom.pill { backdrop-filter:blur(26px) saturate(1.5); -webkit-backdrop-filter:blur(26px) saturate(1.5); }
  .t-aurora .ocard, .t-dusk .ocard { box-shadow:0 30px 80px rgba(0,0,0,.45), 0 1px 0 rgba(255,255,255,.22) inset; }
  .t-aurora .ic-box, .t-dusk .ic-box, .t-bloom .ic-box { border-radius:26px; background:linear-gradient(135deg, var(--accent), var(--accent2)); color:var(--on-accent); }
  .t-aurora .pfill, .t-dusk .pfill, .t-bloom .pfill, .t-aurora .brow.hi .bfill, .t-dusk .brow.hi .bfill, .t-bloom .brow.hi .bfill { background:linear-gradient(90deg, var(--accent), var(--accent2)); }
  .t-aurora .pfill, .t-dusk .pfill { box-shadow:0 0 30px var(--accent); }
  .t-aurora .kicker::before, .t-dusk .kicker::before, .t-bloom .kicker::before { height:3px; border-radius:2px; background:linear-gradient(90deg, var(--accent), var(--accent2)); opacity:1; }
  .t-aurora .node, .t-dusk .node, .t-bloom .node, .t-aurora .slot.on, .t-dusk .slot.on, .t-bloom .slot.on, .t-aurora .vs-col, .t-dusk .vs-col, .t-bloom .vs-col, .t-aurora .sm-card, .t-dusk .sm-card, .t-bloom .sm-card, .t-aurora .imcard, .t-dusk .imcard, .t-bloom .imcard, .t-aurora .win, .t-dusk .win, .t-bloom .win { border-radius:30px; backdrop-filter:blur(30px) saturate(1.4); -webkit-backdrop-filter:blur(30px) saturate(1.4);
    box-shadow:0 30px 90px var(--glow), 0 1px 0 rgba(255,255,255,.25) inset; }
  .t-aurora .node.payoff, .t-dusk .node.payoff, .t-bloom .node.payoff { background:linear-gradient(120deg, var(--accent), var(--accent2)); box-shadow:0 24px 80px var(--glow), 0 0 60px var(--accent); }
  .t-aurora .vs-col.win, .t-dusk .vs-col.win, .t-bloom .vs-col.win { border:3px solid var(--accent); box-shadow:0 30px 100px var(--glow), 0 0 70px var(--accent); }
  .t-aurora .vs-mid, .t-dusk .vs-mid, .t-bloom .vs-mid { background:linear-gradient(135deg, var(--accent), var(--accent2)); color:var(--on-accent); box-shadow:0 0 40px var(--accent); }
  .t-aurora .slot, .t-dusk .slot, .t-bloom .slot { border-radius:30px; }
  .t-aurora .sm-stamp, .t-dusk .sm-stamp, .t-bloom .sm-stamp { mix-blend-mode:normal; box-shadow:0 0 40px currentColor; text-shadow:0 0 24px currentColor; }
  .t-aurora .nbig, .t-dusk .nbig, .t-bloom .nbig, .t-aurora .ostat .big, .t-dusk .ostat .big, .t-bloom .ostat .big { background:linear-gradient(170deg, var(--fg) 30%, var(--accent2) 130%); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }
  .t-aurora .ga-fill, .t-dusk .ga-fill, .t-bloom .ga-fill { stroke:var(--accent); filter:drop-shadow(0 0 18px var(--accent)); }
  .t-aurora .sk-bar, .t-dusk .sk-bar { box-shadow:0 0 24px var(--bad); }
  .t-aurora .conn .shaft, .t-dusk .conn .shaft, .t-bloom .conn .shaft { background:linear-gradient(180deg, var(--accent), var(--accent2)); opacity:1; }
  .t-aurora .conn .pk, .t-dusk .conn .pk { box-shadow:0 0 22px var(--accent2); background:var(--accent2); }
  .t-aurora .curl, .t-dusk .curl, .t-bloom .curl { background:linear-gradient(110deg, var(--accent), var(--accent2)); color:var(--on-accent); box-shadow:0 20px 70px var(--glow); }

  .otitle em { text-shadow:none; filter:drop-shadow(0 4px 14px rgba(0,0,0,.55)); }
  /* ---------- white boards on the dark glass looks: the field glows, the boards read ---------- */
  .t-aurora .node:not(.payoff), .t-aurora .slot.on, .t-aurora .vs-col, .t-aurora .sm-card, .t-aurora .imcard, .t-aurora .ocard, .t-aurora .rc, .t-aurora.ocard, .t-aurora.chip, .t-aurora.pill:not(.accent) {
    --fg:#15102a; --soft:#5c5674; --faint:#a9a3bf; --line:rgba(20,10,60,.10); --card:#ffffff; --raised:#efedf6;
    --accent:#e5368f; --accent2:#6a3cff; --accent-soft:rgba(106,60,255,.10); --on-accent:#ffffff; --good:#12a36a; --bad:#e0384f; --money:#c27a00;
    background:#ffffff; color:var(--fg); backdrop-filter:none; -webkit-backdrop-filter:none; border-color:rgba(255,255,255,.7);
    box-shadow:0 34px 90px rgba(0,0,0,.42), 0 0 0 1px rgba(255,255,255,.5); }
  .t-aurora .vs-col.win { box-shadow:0 34px 100px rgba(0,0,0,.45), 0 0 0 4px #ffffff, 0 0 60px rgba(255,255,255,.55); border-color:var(--accent); }
  .t-aurora .vs-col:not(.win) .vs-x { background:var(--bad); }
  .t-aurora .slot { border-color:rgba(255,255,255,.45); } .t-aurora .slot .sl-n, .t-aurora .slot .sl-q { color:rgba(255,255,255,.7); } .t-aurora .slot.on .sl-n { color:var(--accent); }
  .t-aurora .btrack, .t-aurora .ptrack { background:rgba(255,255,255,.14); } .t-aurora .bfill { background:rgba(255,255,255,.4); } .t-aurora .brow.hi .bfill { background:#ffffff; box-shadow:0 0 30px rgba(255,255,255,.6); }
  .t-aurora .ga-trk { stroke:rgba(255,255,255,.14); } .t-aurora .ga-fill { stroke:#ffffff; filter:drop-shadow(0 0 22px rgba(255,255,255,.7)); }
  .t-aurora .kicker { color:rgba(255,255,255,.78); } .t-aurora.ocard .kicker, .t-aurora .ocard .kicker, .t-aurora .node .kicker, .t-aurora .vs-col .kicker, .t-aurora .sm-card .kicker { color:var(--accent); }
  .t-aurora .sk-new { color:#ffffff; } .t-aurora .disp em { -webkit-text-fill-color:currentColor; background:none; }
  .t-aurora.ocard .disp em, .t-aurora.ocard .t em, .t-aurora .ocard .disp em, .t-aurora .node .t em, .t-aurora .slot .t em, .t-aurora .vs-col em, .t-aurora .sm-card em { -webkit-text-fill-color:transparent; background:linear-gradient(100deg, var(--accent), var(--accent2)); -webkit-background-clip:text; background-clip:text; }
  .t-aurora .nbig { -webkit-text-fill-color:#ffffff; background:none; text-shadow:0 0 60px rgba(255,255,255,.35); }
  .t-aurora .conn .shaft { background:#ffffff; opacity:.7; } .t-aurora .conn .pk { background:#ffffff; box-shadow:0 0 20px #ffffff; }
  .t-aurora .vs-mid, .t-aurora .curl { background:#ffffff; color:#15102a; box-shadow:0 0 40px rgba(255,255,255,.5); }
  .t-aurora .node.payoff { background:#ffffff; color:#15102a; box-shadow:0 0 0 3px var(--b2), 0 30px 90px rgba(0,0,0,.4), 0 0 70px rgba(255,255,255,.4); } .t-aurora .node.payoff .ic-box { background:linear-gradient(135deg, #e5368f, #6a3cff); color:#fff; }
  .t-aurora.ocard .ic-box, .t-aurora .ocard .ic-box, .t-aurora .node .ic-box { background:linear-gradient(135deg, #e5368f, #6a3cff); color:#ffffff; }
  .t-aurora .pfill { background:linear-gradient(90deg, #e5368f, #6a3cff); box-shadow:none; }
  .t-dusk .node:not(.payoff), .t-dusk .slot.on, .t-dusk .vs-col, .t-dusk .sm-card, .t-dusk .imcard, .t-dusk .ocard, .t-dusk .rc, .t-dusk.ocard, .t-dusk.chip, .t-dusk.pill:not(.accent) {
    --fg:#15102a; --soft:#5c5674; --faint:#a9a3bf; --line:rgba(20,10,60,.10); --card:#ffffff; --raised:#efedf6;
    --accent:#f0640f; --accent2:#d11f62; --accent-soft:rgba(240,100,15,.10); --on-accent:#ffffff; --good:#12a36a; --bad:#e0384f; --money:#c27a00;
    background:#ffffff; color:var(--fg); backdrop-filter:none; -webkit-backdrop-filter:none; border-color:rgba(255,255,255,.7);
    box-shadow:0 34px 90px rgba(0,0,0,.42), 0 0 0 1px rgba(255,255,255,.5); }
  .t-dusk .vs-col.win { box-shadow:0 34px 100px rgba(0,0,0,.45), 0 0 0 4px #ffffff, 0 0 60px rgba(255,255,255,.55); border-color:var(--accent); }
  .t-dusk .vs-col:not(.win) .vs-x { background:var(--bad); }
  .t-dusk .slot { border-color:rgba(255,255,255,.45); } .t-dusk .slot .sl-n, .t-dusk .slot .sl-q { color:rgba(255,255,255,.7); } .t-dusk .slot.on .sl-n { color:var(--accent); }
  .t-dusk .btrack, .t-dusk .ptrack { background:rgba(255,255,255,.14); } .t-dusk .bfill { background:rgba(255,255,255,.4); } .t-dusk .brow.hi .bfill { background:#ffffff; box-shadow:0 0 30px rgba(255,255,255,.6); }
  .t-dusk .ga-trk { stroke:rgba(255,255,255,.14); } .t-dusk .ga-fill { stroke:#ffffff; filter:drop-shadow(0 0 22px rgba(255,255,255,.7)); }
  .t-dusk .kicker { color:rgba(255,255,255,.78); } .t-dusk.ocard .kicker, .t-dusk .ocard .kicker, .t-dusk .node .kicker, .t-dusk .vs-col .kicker, .t-dusk .sm-card .kicker { color:var(--accent); }
  .t-dusk .sk-new { color:#ffffff; } .t-dusk .disp em { -webkit-text-fill-color:currentColor; background:none; }
  .t-dusk.ocard .disp em, .t-dusk.ocard .t em, .t-dusk .ocard .disp em, .t-dusk .node .t em, .t-dusk .slot .t em, .t-dusk .vs-col em, .t-dusk .sm-card em { -webkit-text-fill-color:transparent; background:linear-gradient(100deg, var(--accent), var(--accent2)); -webkit-background-clip:text; background-clip:text; }
  .t-dusk .nbig { -webkit-text-fill-color:#ffffff; background:none; text-shadow:0 0 60px rgba(255,255,255,.35); }
  .t-dusk .conn .shaft { background:#ffffff; opacity:.7; } .t-dusk .conn .pk { background:#ffffff; box-shadow:0 0 20px #ffffff; }
  .t-dusk .vs-mid, .t-dusk .curl { background:#ffffff; color:#15102a; box-shadow:0 0 40px rgba(255,255,255,.5); }
  .t-dusk .node.payoff { background:#ffffff; color:#15102a; box-shadow:0 0 0 3px var(--b2), 0 30px 90px rgba(0,0,0,.4), 0 0 70px rgba(255,255,255,.4); } .t-dusk .node.payoff .ic-box { background:linear-gradient(135deg, #f0640f, #d11f62); color:#fff; }
  .t-dusk.ocard .ic-box, .t-dusk .ocard .ic-box, .t-dusk .node .ic-box { background:linear-gradient(135deg, #f0640f, #d11f62); color:#ffffff; }
  .t-dusk .pfill { background:linear-gradient(90deg, #f0640f, #d11f62); box-shadow:none; }

  /* ---------- captions: always on, one short phrase at a time, the spoken word inverted ---------- */
  #captions { position:absolute; inset:0; z-index:40; pointer-events:none; }
  .cg { position:absolute; left:50%; translate:-50% -50%; visibility:hidden; white-space:nowrap; max-width:980px; font-size:CAP_SIZEpx; font-weight:700; line-height:1.1;
    letter-spacing:-.01em; text-align:center; }
  .cg.pill { padding:16px 20px; border-radius:18px; background:rgba(21,19,15,.9); border:1px solid rgba(240,237,228,.14); box-shadow:0 14px 40px rgba(0,0,0,.35); }
  .cg.bare { text-shadow:0 0 14px rgba(0,0,0,.85), 0 3px 6px rgba(0,0,0,.9); font-weight:800; }
  .cw { display:inline-block; padding:5px 12px 7px; margin:0 -3px; border-radius:11px; background-color:rgba(0,0,0,0); }
  .cw.em.it { font-family:FONT_DISPLAY; font-style:italic; font-weight:560; letter-spacing:-.005em; }
"""
if LAYOUT != "full":
    _s = min(1.0, (AREA_BOT - AREA_TOP) / 720.0)       # scene content is rarely taller than 720 px: fit to that, not the 960 px box
    _ty = (AREA_TOP + AREA_BOT) / 2.0 - 770
    CSS += """
  /* ---------- layout %(m)s: animations above, the face cam in its own box ---------- */
  .video-wrapper { left:%(x)dpx; top:%(y)dpx; width:%(w)dpx; height:%(h)dpx; border-radius:%(r)dpx; z-index:9; }
  #cam-shade { display:none; }
  .sc.lay > .layfit { position:absolute; inset:0; transform:translateY(%(ty).0fpx) scale(%(s).3f); transform-origin:50%% 770px; }
  .cutaway-video { height:%(ab)dpx; }
  .cliplabel { top:%(lt)dpx; }
  .sc.lay .bw-body, .sc.lay .tm-body, .sc.lay .im-body { top:290px; bottom:670px; justify-content:center; }
""" % {"m": LAYOUT, "x": CAM["x"], "y": CAM["y"], "w": CAM["w"], "h": CAM["h"], "r": CAM["r"], "s": _s, "ty": _ty, "ab": CAM["y"] if LAYOUT == "split" else 1920, "lt": AREA_BOT - 130}
    if LAYOUT == "inset":
        CSS += """  .video-wrapper { box-shadow:0 40px 110px rgba(0,0,0,.55), 0 0 0 2px rgba(255,255,255,.14); }
"""
    else:
        CSS += """  .video-wrapper { box-shadow:0 -1px 0 rgba(255,255,255,.18), 0 -30px 80px rgba(0,0,0,.45); }
"""
CSS = (CSS.replace("THEMES", "\n  ".join(theme_css(n) for n in TOKENS)).replace("FONT_DISPLAY", FONT_DISPLAY).replace("FONT_BODY", FONT_BODY)
       .replace("FONT_MONO", FONT_MONO).replace("LIVE", LIVE).replace("ORIGIN", frame.get("origin", "50% 34%")).replace("CAP_SIZE", str(CAP_SIZE)))

HELPERS = """
        const EO = '%s';
        const rise = function (sel, t, o) { o = o || {}; tl.fromTo(sel, { opacity: 0, y: o.y == null ? 36 : o.y }, { opacity: 1, y: 0, duration: o.d || 0.5, ease: EO, stagger: o.s || 0 }, t); };
        const fadeOut = function (sel, t, d) { tl.to(sel, { opacity: 0, duration: d || 0.26, ease: 'power2.in' }, t); };
        const maskIn = function (sel, t, o) { o = o || {}; tl.fromTo(sel, { yPercent: 112 }, { yPercent: 0, duration: o.d || 0.66, ease: EO, stagger: o.s == null ? 0.09 : o.s }, t); };
        const pop = function (sel, t) { tl.fromTo(sel, { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.36, ease: 'back.out(1.8)' }, t); };
        const count = function (sel, from, to, t, dur, o) {      // one proxy on the one timeline: any frame renders the same
          o = o || {}; const el = document.querySelector(sel), p = { v: from }, dec = o.dec || 0;
          const f = function (v) { return (o.prefix || '') + Number(v).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + (o.suffix || ''); };
          const put = function () { el.textContent = f(dec ? p.v : Math.round(p.v)); };
          put(); tl.to(p, { v: to, duration: dur, ease: 'power2.out', onUpdate: put }, t);
        };
        const typeIn = function (sel, t0, t1) {                  // text from one proxy, never a set per character (seek-safe)
          const el = document.querySelector(sel), full = el.getAttribute('data-text') || '', p = { n: 0 };
          const put = function () { el.textContent = full.slice(0, Math.floor(p.n + 1e-6)) + (p.n < full.length ? '\\u258C' : ''); };
          el.textContent = ''; tl.to(p, { n: full.length, duration: Math.max(0.05, t1 - t0), ease: 'none', onUpdate: put }, t0);
        };
        const showText = function (sel) { const el = document.querySelector(sel); el.textContent = el.getAttribute('data-text') || ''; };
        const draw = function (sel, t, dur) {                    // draw an SVG stroke; give the path pathLength="1"
          tl.fromTo(sel, { strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: dur || 0.5, ease: 'power2.inOut' }, t);
        };
        const checkIn = function (scope, t) {                    // the ring fills with the accent, then the tick draws
          const el = document.querySelector(scope + ' .mk'); if (!el) return;
          const acc = getComputedStyle(el).getPropertyValue('--accent').trim() || '#1d2f6f';
          tl.to(scope + ' .mk .ring', { fill: acc, stroke: acc, duration: 0.24, ease: 'power2.out' }, t);
          tl.to(scope + ' .mk .tick', { strokeDashoffset: 0, duration: 0.3, ease: 'power2.out' }, t + 0.1);
        };
""" % EASE

page = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<style>%(css)s%(raw_css)s</style>
</head>
<body>
  <div id="stage" data-composition-id="%(id)s" data-start="0" data-duration="%(d).3f" data-fps="30" data-width="1080" data-height="1920">
    <div class="video-wrapper" id="video-wrap">
      <div id="video-zoom">
        <video id="bg-video" src="%(video)s" playsinline data-has-audio="true" data-start="0" data-duration="%(d).3f" data-track-index="1"></video>
      </div>
    </div>
    <div id="cam-shade"></div>
%(videos)s%(hosts)s%(raw_html)s
    <div id="captions">
%(caps)s
    </div>
%(audio)s
    <script src="vendor/gsap.min.js"></script>
    <script>
      (function () {
        const tl = window.gsap.timeline({ paused: true });
%(helpers)s
        tl.set('#video-zoom', { scale: %(base).4f, y: %(fy)d }, 0);
        // camera
        %(cam)s
        // beats
        %(beats)s
        // captions
        %(capjs)s
%(raw_js)s
        tl.to({}, { duration: %(d).3f }, 0);
        window.__timelines = window.__timelines || {};
        window.__timelines["%(id)s"] = tl;
      })();
    </script>
  </div>
</body>
</html>
""" % {"css": CSS, "raw_css": S.get("raw_css", ""), "id": esc(S.get("id", os.path.basename(os.path.abspath(P)))), "d": D,
       "video": esc(S.get("video", "input-video.mp4")), "videos": "".join(video_parts), "hosts": "".join(html_parts), "raw_html": S.get("raw_html", ""),
       "caps": "\n".join(cap_html), "audio": "".join(audio_parts), "helpers": HELPERS, "base": BASE, "fy": int(frame.get("y", 0)),
       "cam": "\n        ".join(cam_js), "beats": "\n        ".join(js_parts), "capjs": "\n        ".join(cap_js), "raw_js": S.get("raw_js", "")}
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
    f.write(page)
with open(os.path.join(OUT, "hyperframes.json"), "w", encoding="utf-8") as f:
    json.dump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
               "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
               "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
               "media": {"autoProxy": True}}, f, indent=2)

# ---- the moments worth a snapshot: every beat, every state inside a beat, and a spread of captions -----------
for c in cap_json[::max(1, len(cap_json) // 6)][:8]:
    moments.append((c["start"] + min(0.25, (c["end"] - c["start"]) / 2), "caption"))
uniq, seen = [], []
for tt, lab in sorted(moments):
    tt = round(max(0.05, min(D - 0.06, tt)), 2)
    if all(abs(tt - s) > 0.12 for s in seen):
        seen.append(tt); uniq.append({"t": tt, "label": lab})
save(os.path.join(P, "moments.json"), {"duration": D, "moments": uniq,
                                       "beats": [{"id": b["id"], "type": b["type"], "in": round(b["_in"], 3), "out": round(b["_out"], 3), "full": b["_full"]} for b in order]})

counts = {}
for b in order:
    counts[b["type"]] = counts.get(b["type"], 0) + 1
print("wrote %s: %.2f s, %d beats, %d camera ops, %d captions, %d sounds (mood %s)"
      % (os.path.join(OUT, "index.html"), D, len(order), len(cam_js), len(cap_json), len(kept), MOOD))
print("spans: " + ", ".join("%s %.1f-%.1f" % (s["kind"], s["start"], s["end"]) for s in SPANS))
for b in order:
    print("  %6.2f - %6.2f  %-10s %s" % (b["_in"], b["_out"], b["type"], b["id"]))
print("format use: " + ", ".join("%s %d" % kv for kv in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))))
for w in warnings:
    print("WARN " + w)
