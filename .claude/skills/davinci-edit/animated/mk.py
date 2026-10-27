"""Wrap a chapter's page.html into a full HyperFrames project: shared look + lib, the video's images,
voice, subtitles, SFX and the navbar labels.

  python mk.py edited_videos/<video> <n>      -> <video>/_work/build/chN/index.html

Each build/chN/ holds page.html (<style> + markup + <script> using FW), sfx.json ([[t, file, vol], ...]),
and subs.json / voice.wav from plan.py. Per-video images live in build/img/ (avatar.png, screenshots, thumbnails).
"""
import json, os, shutil, subprocess, sys
KIT = os.path.dirname(os.path.abspath(__file__))
V = os.path.abspath(sys.argv[1]); B = os.path.join(V, '_work', 'build'); n = int(sys.argv[2]); d = os.path.join(B, f'ch{n}')
chs = json.load(open(os.path.join(B, 'chapters.json'))); ch = next(c for c in chs if c['n'] == n)
for sub in ('fonts', 'vendor', 'sfx'):
    shutil.copytree(os.path.join(KIT, 'shared', sub), os.path.join(d, sub), dirs_exist_ok=True)
if os.path.isdir(os.path.join(B, 'img')): shutil.copytree(os.path.join(B, 'img'), os.path.join(d, 'img'), dirs_exist_ok=True)
for f in ('lib.css', 'lib.js'): shutil.copy(os.path.join(KIT, 'shared', f), os.path.join(d, f))
open(os.path.join(d, 'hyperframes.json'), 'w').write('{"paths":{"blocks":"compositions","components":"compositions/components","assets":"assets"},"media":{"autoProxy":true}}')
page = open(os.path.join(d, 'page.html'), encoding='utf-8').read()
style, rest = page.split('</style>', 1); style = style.split('<style>', 1)[1]
markup, script = rest.split('<script>', 1); script = script.rsplit('</script>', 1)[0]
subs = json.load(open(os.path.join(d, 'subs.json'), encoding='utf-8'))
sfx = json.load(open(os.path.join(d, 'sfx.json'))) if os.path.exists(os.path.join(d, 'sfx.json')) else []
nav = [c['nav'] for c in sorted(chs, key=lambda c: c['n']) if c['n'] >= 1]
dur = ch['dur']; cache = {}
def sdur(f): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', os.path.join(d, 'sfx', f)]).decode())
aud = [f'<audio id="vo" src="voice.wav" data-start="0" data-duration="{dur:.3f}" data-track-index="10" data-volume="1"></audio>']
for i, (t, f, v) in enumerate(sorted(sfx)):   # every sound on its own track; long ones capped
    L = cache.setdefault(f, sdur(f)); L = min(L, 1.6 if 'riser' in f else 2.2, dur - t)
    aud.append(f'<audio id="sfx-{i}" src="sfx/{f}" data-start="{t:.3f}" data-duration="{L:.3f}" data-track-index="{40 + i}" data-volume="{v:.3f}"></audio>')
html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8" />
<link rel="stylesheet" href="lib.css" />
<style>{style}</style>
</head><body>
<div id="stage" data-composition-id="ch{n}" data-start="0" data-duration="{dur:.3f}" data-fps="30" data-width="1920" data-height="1080">
{markup}
{chr(10).join(aud)}
<script src="vendor/gsap.min.js"></script>
<script>window.NAV = {json.dumps(nav, ensure_ascii=False)};</script>
<script src="lib.js"></script>
<script>
(function () {{
const SUBS = {json.dumps(subs, ensure_ascii=False)};
const DUR = {dur:.3f};
{script}
}})();
window.__timelines = window.__timelines || {{}};
</script>
</div></body></html>
'''
open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(html)
print(f'ch{n}: {dur:.2f}s, {len(sfx)} sfx, {len(subs)} subs')
