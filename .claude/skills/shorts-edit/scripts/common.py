"""common.py: the few things every shorts-edit script shares (tool lookup that works on Windows, probing, JSON I/O).

Windows notes baked in here so no other script has to care:
  - npx is npx.cmd, and a bare "npx" fails in subprocess without a shell
  - a fresh winget FFmpeg lives in WinGet\\Links, which an already-open shell does not have on PATH yet
  - files are read and written as UTF-8 whatever the console code page is
"""
import json, os, shutil, subprocess, sys

WIN = os.name == "nt"
_LINKS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links")


def tool(name):
    """Full path of ffmpeg / ffprobe / auto-editor, or the bare name when it is already on PATH."""
    env = os.environ.get("HYPERFRAMES_%s_PATH" % name.upper())
    if env and os.path.exists(env):
        return env
    hit = shutil.which(name)
    if hit:
        return hit
    cand = os.path.join(_LINKS, name + ".exe")
    if WIN and os.path.exists(cand):
        return cand
    sys.exit("%s not found. Install it (winget install --id Gyan.FFmpeg.Essentials -e) and open a new terminal." % name)


def tool_env():
    """os.environ with the folder of ffmpeg on PATH, for the scripts and CLIs that call a bare 'ffmpeg'."""
    env = dict(os.environ)
    ff = os.path.dirname(tool("ffmpeg"))
    if ff and ff not in env.get("PATH", ""):
        env["PATH"] = ff + os.pathsep + env.get("PATH", "")
    env.setdefault("HYPERFRAMES_NO_TELEMETRY", "1")
    env.setdefault("HYPERFRAMES_NO_UPDATE_CHECK", "1")
    env.setdefault("PYTHONUTF8", "1")
    return env


def npx(args, **kw):
    """Run `npx hyperframes ...` (pass the arguments after npx). Returns the CompletedProcess."""
    exe = shutil.which("npx.cmd" if WIN else "npx") or ("npx.cmd" if WIN else "npx")
    kw.setdefault("env", tool_env())
    return subprocess.run([exe, "--yes"] + list(args), **kw)


def ffmpeg(args, check=True, **kw):
    return subprocess.run([tool("ffmpeg"), "-y", "-hide_banner", "-v", "error"] + list(args), check=check, **kw)


def probe(path):
    """ffprobe as a dict: {'format': {...}, 'streams': [...]}; exits with a clear line when the file is unreadable."""
    r = subprocess.run([tool("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        sys.exit("ffprobe could not read %s: %s" % (path, r.stderr.strip()[:200]))
    return json.loads(r.stdout)


def vstream(info):
    return next((s for s in info.get("streams", []) if s.get("codec_type") == "video"
                 and s.get("disposition", {}).get("attached_pic", 0) != 1), None)


def astream(info):
    return next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)


def duration(path):
    return float(probe(path)["format"]["duration"])


def display_size(vs):
    """(width, height) as displayed: phone footage is often stored landscape with a 90 degree rotation tag."""
    w, h = int(vs["width"]), int(vs["height"])
    rot = 0
    for sd in vs.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    rot = int(float(vs.get("tags", {}).get("rotate", rot)))
    return (h, w) if abs(rot) % 180 == 90 else (w, h)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def words_of(transcript):
    """The word list of a Parakeet / whisper transcript: [{text, start, end}], whichever shape the file has."""
    raw = load(transcript) if isinstance(transcript, str) else transcript
    ws = raw["words"] if isinstance(raw, dict) and "words" in raw else raw
    return [{"text": str(w["text"]), "start": float(w["start"]), "end": float(w["end"])} for w in ws if str(w.get("text", "")).strip()]


def spans_from_maps(source_map, cut_map):
    """Where the face is on screen and where it is voiceover only, in FLAT-CUT time.
    source_map: prep.py's segments in source time; cut_map: apply-cut.py's segments (src -> flat)."""
    out = []
    for c in cut_map["segments"]:
        for s in source_map["segments"]:
            a, b = max(c["src_start"], s["start"]), min(c["src_end"], s["end"])
            if b - a <= 1e-3:
                continue
            f0 = c["flat_start"] + (a - c["src_start"])
            f1 = c["flat_start"] + (b - c["src_start"])
            if out and out[-1]["kind"] == s["kind"] and abs(out[-1]["end"] - f0) < 0.05:
                out[-1]["end"] = round(f1, 3)
            else:
                out.append({"kind": s["kind"], "start": round(f0, 3), "end": round(f1, 3)})
    return out
