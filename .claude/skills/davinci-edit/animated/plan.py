"""Cut a long voiceover into chapter audio + chapter-local word times + subtitle lines.

  python plan.py edited_videos/<video>          (reads <video>/_work/build/plan.json)

plan.json:
{
  "voice": "_work/media/audio/voice-clean.wav",           # cleaned voice (relative to the video folder)
  "transcript": "_work/transcripts/raw.json",              # Parakeet words of that same file
  "music": "_work/media/audio/music-raw.wav",
  "title_lead": 2.8,                                       # seconds of title card before a chapter's first word
  "chapters": [                                            # n = 0 is the opening (no title card, no nav pill)
    {"n": 0, "name": "Intro",                "segs": [[2.00, 21.62]]},
    {"n": 1, "name": "One Week, Six Shorts", "nav": "Daily Shorts", "segs": [[25.18, 69.96]]},
    {"n": 3, "name": "Building the Brand",   "nav": "The Brand",    "segs": [[144.38, 221.00], [222.29, 229.45]]}
  ],
  "fix": {"shot": "short", "devora.dev": "devvora.dev"},   # word-level mishearings (punctuation kept)
  "phrase_fix": [["Sun and Shade", "Sun N Shade"]]         # sentence-level fixes, applied before splitting lines
}
segs are SOURCE seconds kept for that chapter: spoken chapter titles and retakes fall between them.
Writes build/chN/{voice.wav, words.json, subs.json} and build/chapters.json (durations + global start g0).
"""
import json, os, subprocess, sys
SK = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../shorts-edit/scripts')
sys.path.insert(0, os.path.abspath(SK))
from common import words_of

V = os.path.abspath(sys.argv[1]); B = os.path.join(V, '_work', 'build')
cfg = json.load(open(os.path.join(B, 'plan.json'), encoding='utf-8'))
SRC = os.path.join(V, cfg['voice']); WORDS = words_of(os.path.join(V, cfg['transcript']))
TITLE = cfg.get('title_lead', 2.8); TAIL = 0.5
FIXB = cfg.get('fix', {}); PHRASE_FIX = cfg.get('phrase_fix', [])
def run(*a): subprocess.run(a, check=True)

out = []
for ch in cfg['chapters']:
    n, segs = ch['n'], ch['segs']
    d = os.path.join(B, f'ch{n}'); os.makedirs(d, exist_ok=True)
    lead = 0.0 if n == 0 else TITLE
    inputs, filt = ['-f', 'lavfi', '-t', f'{lead or 0.01:.3f}', '-i', 'anullsrc=r=48000:cl=mono'], []
    for i, (a, b) in enumerate(segs):
        inputs += ['-ss', f'{a:.3f}', '-t', f'{b - a:.3f}', '-i', SRC]
        filt.append(f'[{i+1}:a]aresample=48000,afade=t=in:d=0.006,afade=t=out:st={b-a-0.006:.3f}:d=0.006[s{i}]')
    inputs += ['-f', 'lavfi', '-t', f'{TAIL:.3f}', '-i', 'anullsrc=r=48000:cl=mono']
    k = len(segs) + 1
    fc = ';'.join(filt) + ';[0:a]' + ''.join(f'[s{i}]' for i in range(len(segs))) + f'[{k}:a]concat=n={len(segs)+2}:v=0:a=1[o]'
    run('ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', fc, '-map', '[o]', '-ac', '1', '-ar', '48000', os.path.join(d, 'voice.wav'))
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', os.path.join(d, 'voice.wav')]).decode())
    lw, off = [], lead
    for a, b in segs:
        for x in WORDS:
            if x['start'] >= a - 0.02 and x['end'] <= b + 0.05:
                raw = x['text']; core = raw.rstrip('.,?!'); tail = raw[len(core):]
                tx = FIXB[core] + tail if core in FIXB else raw
                if tx.strip(): lw.append({'t': tx, 's': round(x['start'] - a + off, 3), 'e': round(min(x['end'], b) - a + off, 3)})
        off += b - a
    json.dump(lw, open(os.path.join(d, 'words.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    # subtitles: whole sentences, phrase fixes, then balanced lines of <= 42 chars
    sents, cur = [], []
    for w in lw:
        cur.append(w)
        if w['t'][-1] in '.?!' and w['t'] not in ('a.m.', 'p.m.'): sents.append(cur); cur = []
    if cur: sents.append(cur)
    S = []
    for p in sents:
        txt = ' '.join(c['t'] for c in p)
        for x, y in PHRASE_FIX: txt = txt.replace(x, y)
        txt = ' '.join(txt.split()); ws = txt.split(' '); n_lines = max(1, -(-len(txt) // 42))
        target = len(txt) / n_lines; groups, g = [], []
        for wd in ws:
            g.append(wd)
            if len(' '.join(g)) >= target and len(groups) < n_lines - 1: groups.append(g); g = []
        if g: groups.append(g)
        a0, a1 = p[0]['s'], p[-1]['e']; total = sum(len(' '.join(g)) for g in groups); t = a0
        for g in groups:
            seg = ' '.join(g); dt = (a1 - a0) * len(seg) / total
            S.append([round(t, 2), round(t + dt, 2), seg.rstrip(',')]); t += dt
    for i in range(len(S)):
        nx = S[i + 1][0] if i + 1 < len(S) else S[i][1] + 0.4
        S[i][1] = round(min(S[i][1] + 0.3, nx), 2)
    json.dump(S, open(os.path.join(d, 'subs.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    out.append({'n': n, 'name': ch['name'], 'nav': ch.get('nav', ch['name']), 'dur': round(dur, 3), 'lead': lead, 'segs': segs})
    print(f"ch{n} {ch['name']:28s} {dur:7.2f}s  {len(lw)} words  {len(S)} subs")
t = 0
for c in out: c['g0'] = round(t, 3); t += c['dur']
json.dump(out, open(os.path.join(B, 'chapters.json'), 'w'), indent=1)
print('total %.2fs = %d:%02d' % (t, t // 60, t % 60))
