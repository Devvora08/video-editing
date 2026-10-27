"""Composer tests: no media, no browser. Run from scripts/:  python -m unittest discover tests"""
import json, os, re, shutil, subprocess, sys, tempfile, unittest

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS)
from common import spans_from_maps

WORDS = [("Hi,", 0.3, 0.6), ("I", 0.6, 0.7), ("am", 0.7, 0.9), ("Dev.", 0.9, 1.4), ("This", 2.0, 2.2), ("week", 2.2, 2.5), ("I", 2.5, 2.6),
         ("shipped", 2.6, 3.0), ("three", 3.0, 3.3), ("things.", 3.3, 3.9), ("First,", 4.2, 4.6), ("a", 4.6, 4.7), ("mobile", 4.7, 5.0),
         ("app.", 5.0, 5.5), ("Second,", 5.9, 6.3), ("a", 6.3, 6.4), ("backend", 6.4, 6.9), ("with", 6.9, 7.1), ("30", 7.1, 7.4),
         ("services.", 7.4, 8.1), ("Subscribe", 8.6, 9.1), ("to", 9.1, 9.2), ("the", 9.2, 9.3), ("channel.", 9.3, 9.9)]


def project(story, spans=None):
    d = tempfile.mkdtemp(prefix="se-test-")
    json.dump([{"text": t, "start": a, "end": b} for t, a, b in WORDS], open(os.path.join(d, "transcript.json"), "w"))
    json.dump(spans or [{"kind": "cam", "start": 0, "end": 2.0}, {"kind": "vo", "start": 2.0, "end": 8.4}, {"kind": "cam", "start": 8.4, "end": 10.2}],
              open(os.path.join(d, "spans.json"), "w"))
    story.setdefault("duration", 10.2)
    json.dump(story, open(os.path.join(d, "storyboard.json"), "w"))
    return d


def compose(d):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "compose.py"), "--project", d], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONUTF8="1"))
    html = ""
    p = os.path.join(d, "public", "index.html")
    if os.path.exists(p):
        html = open(p, encoding="utf-8").read()
    return r, html


class Compose(unittest.TestCase):
    def setUp(self):
        self.dirs = []

    def tearDown(self):
        for d in self.dirs:
            shutil.rmtree(d, ignore_errors=True)

    def build(self, story, spans=None):
        d = project(story, spans); self.dirs.append(d)
        r, html = compose(d)
        return d, r, html

    def test_phrase_times_and_lead(self):
        d, r, html = self.build({"id": "t", "beats": [{"type": "statement", "id": "s1", "lines": ["I shipped", ["*three* things", "three things"]], "in": "this week"}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = re.search(r'id="h-s1"[^>]*data-start="([\d.]+)"', html)
        self.assertAlmostEqual(float(m.group(1)), 2.0 - 0.20, places=2)       # enters LEAD ahead of "This"
        self.assertIn('data-anchor="this week"', html)
        self.assertIn("<em>three</em>", html)

    def test_unknown_phrase_fails_with_its_name(self):
        d, r, html = self.build({"id": "t", "beats": [{"type": "chip", "id": "c", "text": "x", "in": "never said this"}]})
        self.assertEqual(r.returncode, 1)
        self.assertIn("never said this", r.stdout)

    def test_captions_cover_every_word_and_write_srt(self):
        d, r, html = self.build({"id": "t", "captions": {"replace": [{"say": "dev", "show": "Dev Vora"}], "emphasis": [{"say": "three things", "color": "money"}]}, "beats": []})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        caps = json.load(open(os.path.join(d, "captions.json"), encoding="utf-8"))
        said = " ".join(c["text"] for c in caps)
        self.assertIn("Dev Vora", said)
        self.assertEqual(len(said.replace("Dev Vora", "Dev").split()), len(WORDS))
        for a, b in zip(caps, caps[1:]):
            self.assertLessEqual(a["end"], b["start"] + 1e-6)             # one caption at a time
        self.assertTrue(all(len(c["text"]) <= 26 for c in caps))
        self.assertIn("-->", open(os.path.join(d, "captions.srt"), encoding="utf-8").read())
        self.assertIn("#ecb850", html)                                     # the money colour on the emphasised words

    def test_voiceover_without_a_scene_warns(self):
        d, r, html = self.build({"id": "t", "beats": []})
        self.assertIn("has no scene", r.stdout)
        self.assertIn('id="world0"', html)                                 # paper still covers the black picture

    def test_scenes_do_not_overlap_and_only_one_moves_at_a_join(self):
        d, r, html = self.build({"id": "t", "beats": [
            {"type": "statement", "id": "a", "lines": ["One"], "in": "this week", "out": "services"},
            {"type": "steps", "id": "b", "in": "first", "items": [{"title": "A mobile app", "at": "a mobile app"}, {"title": "A backend", "at": "a backend"}]}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        mm = json.load(open(os.path.join(d, "moments.json")))["beats"]
        a, b = [x for x in mm if x["id"] == "a"][0], [x for x in mm if x["id"] == "b"][0]
        self.assertAlmostEqual(a["out"], b["in"], places=2)
        self.assertNotIn("tl.fromTo('#b', { clipPath", html)                         # same paper: content swaps, nothing wipes
        self.assertIn('data-at=', html)

    def test_sounds_have_ids_and_exist(self):
        d, r, html = self.build({"id": "t", "beats": [{"type": "chip", "id": "c", "text": "Day 07", "in": "hi"}]})
        auds = re.findall(r'<audio id="(sfx-\d+)" src="(sfx/[^"]+)"', html)
        self.assertTrue(auds)
        for _, src in auds:
            self.assertTrue(os.path.exists(os.path.join(d, "public", src)))
        d2, r2, html2 = self.build({"id": "t", "sfx": False, "beats": [{"type": "chip", "id": "c", "text": "Day 07", "in": "hi"}]})
        self.assertNotIn("<audio", html2)

    def test_every_format_builds(self):
        beats = [
            {"type": "title", "id": "t1", "lines": ["A *b*"], "in": 0.1, "out": 0.9},
            {"type": "card", "id": "c1", "title": "T", "sub": "s", "icon": "code", "in": 1.0, "out": 1.8},
            {"type": "number", "id": "n1", "value": 30, "suffix": "+", "label": "x", "in": 2.0, "out": 3.0},
            {"type": "flow", "id": "f1", "in": 3.0, "out": 4.2, "nodes": [{"label": "A", "at": 3.2}, {"label": "B", "at": 3.6, "payoff": True}]},
            {"type": "bars", "id": "b1", "in": 4.2, "out": 5.4, "rows": [{"label": "A", "value": 10, "at": 4.4}, {"label": "B", "value": 1, "hi": True, "at": 4.8}]},
            {"type": "terminal", "id": "m1", "in": 5.4, "out": 6.8, "lines": [{"text": "$ run", "at": 5.6, "type": True}, {"text": "ok", "at": 6.4, "tone": "good"}]},
            {"type": "raw", "id": "r1", "in": 6.8, "out": 7.6, "html": "<div class='kicker'>k</div>", "js": "rise($('.kicker'), GO);"},
            {"type": "cta", "id": "x1", "url": "devvora.dev", "in": 7.6, "out": 8.4},
            {"type": "list", "id": "l1", "in": 8.5, "out": 9.3, "items": [["A", 8.6]], "marker": "check"},
            {"type": "pills", "id": "p1", "in": 9.4, "out": 10.1, "top": 500, "items": [["A", 9.5]]}]
        d, r, html = self.build({"id": "t", "beats": beats})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for b in beats:
            self.assertIn('id="h-%s"' % b["id"], html)
        self.assertEqual(html.count('window.__timelines["t"]'), 1)

    def test_action_scenes_build(self):
        beats = [
            {"type": "slots", "id": "sl", "in": 2.0, "out": 3.0, "empty": 1, "items": [{"title": "A", "at": "three"}]},
            {"type": "versus", "id": "vs", "in": 3.0, "out": 4.2, "left": {"title": "Old", "at": 3.2}, "right": {"title": "New", "value": "2x", "at": 3.5}},
            {"type": "stamp", "id": "sm", "in": 4.2, "out": 5.2, "title": "App", "stamp": "Shipped", "at": "mobile"},
            {"type": "strike", "id": "sk", "in": 5.2, "out": 6.2, "old": "Old", "new": ["New", "line"], "at": 5.7},
            {"type": "receipt", "id": "rc", "in": 6.2, "out": 7.4, "rows": [{"label": "A", "value": 20, "at": 6.5}, {"label": "B", "value": 5, "at": 6.8}]},
            {"type": "gauge", "id": "ga", "in": 7.4, "out": 8.4, "value": 90, "from": 40, "at": 7.6}]
        d, r, html = self.build({"id": "t", "beats": beats})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for b in beats:
            self.assertIn('id="h-%s"' % b["id"], html)
        self.assertIn("count('#rc-v', 0, 25.0", html)                  # the receipt total is the sum of its rows
        self.assertEqual(html.count('class="slot"'), 2)                 # one filled, one left empty
        self.assertEqual(html.count('class="sk-bar"'), 1)


class Spans(unittest.TestCase):
    def test_spans_follow_the_cut(self):
        smap = {"segments": [{"kind": "cam", "start": 0, "end": 10}, {"kind": "vo", "start": 10, "end": 30}]}
        cmap = {"segments": [{"src_start": 1, "src_end": 4, "flat_start": 0, "flat_end": 3}, {"src_start": 8, "src_end": 12, "flat_start": 3, "flat_end": 7},
                             {"src_start": 20, "src_end": 25, "flat_start": 7, "flat_end": 12}]}
        sp = spans_from_maps(smap, cmap)
        self.assertEqual([(s["kind"], s["start"], s["end"]) for s in sp], [("cam", 0, 5), ("vo", 5, 12)])


if __name__ == "__main__":
    unittest.main()
