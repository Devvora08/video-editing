#!/usr/bin/env python3
"""music.py: synthesise a quiet background bed for a Short. No samples, no downloads, nothing to license.

It writes a simple track made for sitting FAR behind a voice. The house sound is a quiet swing trio (the creator asked
for fun and jazzy, not ambient). It is built to the exact length asked for (no loop point to hear), fades in and out,
and stays out of the range where speech lives. It is a bed, not a song: keep it low.

  python music.py --out videos/<p>/music.wav --duration 62.4 [--mood jazzy|calm|upbeat|tense] [--seed 7]

  jazzy    ~104 bpm swing: walking bass, electric piano, brushed ride, vibraphone    THE DEFAULT: fun, light, moving
  calm     70 bpm, major sevenths, a held pad, no drums     only when asked for something still and ambient
  upbeat   92 bpm, brighter chords, a soft kick and shaker  launches, wins, lists
  tense    78 bpm, minor, a low pulse                        problems, stakes, a hook that warns
--seed changes the key, tempo and chord order: render.py derives it from the video itself, so every Short gets a new tune.
--hits (jazzy) fits the tempo and the downbeat to the video: speech has no steady beat, so the band follows the EDIT.
       The tempo (98 to 118 bpm) and its offset are chosen so beats fall on the scene changes and card entrances, and the
       vibraphone and ride play a small accent exactly on each of them.
"""
import argparse, os, sys, wave
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--duration", type=float, required=True)
ap.add_argument("--mood", default="jazzy", choices=["jazzy", "calm", "upbeat", "tense"])
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--hits", default="", help="comma-separated times (s) of the moments the band should land on: scene changes, cards arriving")
args = ap.parse_args()
HITS = sorted(float(x) for x in args.hits.split(",") if x.strip())

SR = 48000
D = max(4.0, args.duration)
N = int(D * SR)
rng = np.random.default_rng(1000 + args.seed)

# chords as semitones above the key's root: (bass note, pad notes)
MOODS = {
    "calm":   {"bpm": 70, "bars": 2, "root": 53,   # F3
               "sets": [[(0, [0, 4, 7, 11]), (9, [9, 12, 16, 19]), (2, [2, 5, 9, 12]), (5, [5, 9, 12, 16])],
                        [(0, [0, 4, 7, 11]), (5, [5, 9, 12, 16]), (9, [9, 12, 16, 19]), (7, [7, 11, 14, 17])],
                        [(5, [5, 9, 12, 16]), (0, [0, 4, 7, 11]), (2, [2, 5, 9, 12]), (9, [9, 12, 16, 19])]]},
    "upbeat": {"bpm": 92, "bars": 1, "root": 55,   # G3
               "sets": [[(0, [0, 4, 7, 14]), (7, [7, 11, 14, 19]), (9, [9, 12, 16, 19]), (5, [5, 9, 12, 16])],
                        [(0, [0, 4, 7, 14]), (5, [5, 9, 12, 16]), (9, [9, 12, 16, 19]), (7, [7, 11, 14, 19])]]},
    "tense":  {"bpm": 78, "bars": 2, "root": 50,   # D3
               "sets": [[(0, [0, 3, 7, 10]), (8, [8, 12, 15, 19]), (5, [5, 8, 12, 15]), (7, [7, 10, 14, 17])],
                        [(0, [0, 3, 7, 10]), (5, [5, 8, 12, 15]), (8, [8, 12, 15, 19]), (3, [3, 7, 10, 14])]]},
}
M = MOODS[args.mood if args.mood in MOODS else "calm"]
beat = 60.0 / M["bpm"]
chord_len = M["bars"] * 4 * beat
prog = M["sets"][args.seed % len(M["sets"])]
root = M["root"] + [0, -2, 2, -3, 3][(args.seed // len(M["sets"])) % 5]
hz = lambda midi: 440.0 * 2 ** ((midi - 69) / 12.0)

L = np.zeros(N + SR * 4)
R = np.zeros(N + SR * 4)


def add(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    if i < 0:                       # the bar grid may start before 0 so that its beats line up with the edit
        sig, i = sig[-i:], 0
    if i >= N or len(sig) == 0:
        return
    n = min(len(sig), len(L) - i)
    L[i:i + n] += sig[:n] * gain * (1 - max(0.0, pan))
    R[i:i + n] += sig[:n] * gain * (1 + min(0.0, pan))


def pad(f, dur):
    """A soft held note: a few low harmonics, two slightly detuned voices, slow attack and release."""
    t = np.arange(int((dur + 1.4) * SR)) / SR
    s = sum(a * np.sin(2 * np.pi * f * h * (1 + d) * t + ph) for h, a in ((1, 1.0), (2, 0.28), (3, 0.10))
            for d, ph in ((0.0, 0.0), (0.0035, 1.3), (-0.0031, 2.1)))
    env = np.minimum(1.0, t / 1.1) * np.minimum(1.0, np.maximum(0.0, (dur + 1.4 - t) / 1.4))
    return s * env * (1 + 0.06 * np.sin(2 * np.pi * 0.23 * t)) / 3.0


def keys(f, dur=2.6):
    """An electric-piano note: a sine bent by a fast-decaying overtone, long soft tail."""
    t = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * f * t + 1.6 * np.exp(-t * 7.0) * np.sin(2 * np.pi * 2 * f * t))
    return s * np.exp(-t * 2.2) * np.minimum(1.0, t / 0.008)


def bass(f, dur):
    t = np.arange(int(dur * SR)) / SR
    return (np.sin(2 * np.pi * f * t) + 0.18 * np.sin(2 * np.pi * 2 * f * t)) * np.minimum(1.0, t / 0.03) * np.exp(-t * 1.1)


def kick():
    t = np.arange(int(0.32 * SR)) / SR
    return np.sin(2 * np.pi * (44 * t + (70 / 18.0) * (1 - np.exp(-t * 18)))) * np.exp(-t * 11)


def shaker():
    t = np.arange(int(0.07 * SR)) / SR
    n = rng.standard_normal(len(t))
    return np.diff(np.concatenate([[0.0], n])) * np.exp(-t * 60) * np.minimum(1.0, t / 0.004)



def jazzy():
    """A small swing trio, played quietly: walking bass, electric-piano comping on the off-beats, a brushed ride, and a
    vibraphone that answers now and then. ii-V-I harmony, swung eighths. Fun, light, and out of the way of a voice."""
    bpm, phase = 104 + (args.seed % 3) * 4, 0.0
    if HITS:
        # fit the grid to the edit: try every tempo and offset, keep the one whose beats sit closest to the hits
        best = None
        centre = 100 + (args.seed % 5) * 4                    # the seed still moves the feel: the search prefers tempos near it
        for cand in np.arange(98.0, 118.01, 0.25):
            b_ = 60.0 / cand
            for ph in np.linspace(0.0, b_, 32, endpoint=False):
                off = np.array([abs(((h - ph + b_ / 2) % b_) - b_ / 2) for h in HITS])
                cost = float(np.mean(off ** 2)) + (0.004 * abs(cand - centre) / 10.0) ** 2
                if best is None or cost < best[0]:
                    best = (cost, cand, ph, float(np.median(off)))
        _, bpm, phase, med = best
        print("fit: %.2f bpm, offset %.3f s; beats land a median %.0f ms from the %d hits" % (bpm, phase, med * 1000, len(HITS)))
    bt = 60.0 / bpm
    start = phase - np.ceil(phase / (4 * bt)) * 4 * bt        # the bar that contains t = 0
    sw = 2.0 / 3.0                                            # the swung off-beat sits two thirds of the way through the beat
    key = 48 + [0, -2, 3, 5, -4][args.seed % 5]               # C, Bb, Eb, F, Ab
    m7, d7, M7 = [3, 7, 10, 14], [4, 10, 14, 21], [4, 7, 11, 14]
    A = [(2, m7, [0, 3, 7]), (7, d7, [0, 4, 7]), (0, M7, [0, 4, 7]), (9, [4, 10, 13, 16], [0, 4, 7])]          # ii  V  I  VI7
    B = [(5, M7, [0, 4, 7]), (10, [4, 10, 14], [0, 4, 7]), (4, m7, [0, 3, 7]), (9, [4, 10, 13, 16], [0, 4, 7]),
         (2, m7, [0, 3, 7]), (7, d7, [0, 4, 7]), (0, M7, [0, 4, 7]), (0, [4, 7, 9, 14], [0, 4, 7])]            # IV bVII7 iii VI7 ii V I I6
    form = (A + A + B) if args.seed % 2 == 0 else (B + A + A)
    fold = lambda n, lo, hi: n + 12 * int(np.ceil((lo - n) / 12.0)) if n < lo else (n - 12 * int(np.ceil((n - hi) / 12.0)) if n > hi else n)

    def stab(f, dur=0.9):                                      # a short electric-piano chord tone
        t = np.arange(int(dur * SR)) / SR
        return np.sin(2 * np.pi * f * t + 1.9 * np.exp(-t * 9.0) * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 4.5) * np.minimum(1.0, t / 0.006)

    def upright(f, dur):                                       # a plucked double bass: a quick thump, then a round tone
        t = np.arange(int(dur * SR)) / SR
        s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 6) + 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 12)
        return s * np.minimum(1.0, t / 0.012) * np.exp(-t * 2.6)

    def vibes(f, dur=1.6):
        t = np.arange(int(dur * SR)) / SR
        return (np.sin(2 * np.pi * f * t) + 0.22 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 9)) * np.exp(-t * 3.0) * np.minimum(1.0, t / 0.004) * (1 + 0.12 * np.sin(2 * np.pi * 5.5 * t))

    def ride(dur=0.30, bright=1.0):                            # a brushed cymbal: filtered noise with a soft tail
        t = np.arange(int(dur * SR)) / SR
        n = np.diff(np.concatenate([[0.0], rng.standard_normal(len(t))]))
        return n * np.exp(-t * (14.0 / bright)) * np.minimum(1.0, t / 0.003)

    comps = [[0.0, 1 + sw], [sw, 2 + sw], [1 + sw, 3.0], [0.0, 2 + sw], [sw, 2.0, 3 + sw]]
    # an accent exactly on each hit (at least 1.2 s apart): a vibraphone note from the chord of that bar, and a ride
    last = -9.0
    for h in HITS:
        if h - last < 1.2 or h > D - 0.4:
            continue
        last = h
        r, voicing, walk = form[int((h - start) // (4 * bt)) % len(form)]
        add(vibes(hz(fold(key + r + voicing[-1], 67, 84)), 1.8), h, pan=0.2, gain=0.13)
        add(vibes(hz(fold(key + r + voicing[0], 60, 76)), 1.4), h, pan=-0.2, gain=0.07)
        add(ride(0.5, 1.4), h, pan=0.35, gain=0.035)
    t, k = float(start), 0
    while t < D + 0.5:
        r, voicing, walk = form[k % len(form)]
        nxt = form[(k + 1) % len(form)][0]
        b0 = fold(key + r - 12, 33, 45)
        bn = fold(key + nxt - 12, 33, 45)
        line = [b0, b0 + walk[1], b0 + walk[2], bn + (1 if bn < b0 + walk[2] else -1)]     # root, third, fifth, a half step into the next root
        for q, n in enumerate(line):
            add(upright(hz(n), bt * 1.05), t + q * bt, gain=0.42)
        for hit in comps[int(rng.integers(0, len(comps)))]:
            for j, iv in enumerate(voicing):
                add(stab(hz(fold(key + r + iv, 55, 72))), t + hit * bt + 0.004 * j, pan=(-0.3, 0.3, -0.1, 0.1)[j % 4], gain=0.085)
        for pos in (0.0, 1.0, 1 + sw, 2.0, 3.0, 3 + sw):          # ding, ding-da-ding
            add(ride(bright=1.0 if pos == int(pos) else 0.7), t + pos * bt, pan=0.35, gain=0.030 if pos == int(pos) else 0.020)
        for pos in (1.0, 3.0):                                    # the hi-hat closes on two and four
            add(ride(0.06, 0.5), t + pos * bt, pan=-0.3, gain=0.028)
        if k % 2 == 1 and rng.random() < 0.75:                   # the vibraphone answers every other bar with a two or three note figure
            scale = [iv for iv in voicing] + [walk[2]]
            start = [2.0, 2 + sw, 1 + sw][int(rng.integers(0, 3))]
            for i in range(int(rng.integers(2, 4))):
                n = fold(key + r + scale[int(rng.integers(0, len(scale)))], 67, 84)
                add(vibes(hz(n)), t + (start + i * (sw if i % 2 == 0 else 1 - sw) ) * bt, pan=float(rng.uniform(-0.4, 0.4)), gain=0.10)
        t += 4 * bt
        k += 1
    return bpm, key


JAZZ_INFO = jazzy() if args.mood == "jazzy" else None
t, k = 0.0, 0
while args.mood != "jazzy" and t < D + 0.5:
    b, notes = prog[k % len(prog)]
    for j, n in enumerate(notes):
        add(pad(hz(root + n), chord_len), t, pan=(-0.35, 0.35, -0.15, 0.15)[j % 4], gain=0.20)
    add(bass(hz(root + b - 12), min(chord_len, 3.5)), t, gain=0.34)
    if args.mood == "tense":                                  # a low pulse on every beat
        for q in range(int(M["bars"] * 4)):
            add(bass(hz(root + b - 12), beat * 0.9), t + q * beat, gain=0.13)
    # a sparse melody from the chord itself: which beats play is drawn once per chord, never busy
    slots = [0.0, 1.5, 2.5, 4.0, 5.5, 6.5] if M["bars"] == 2 else [0.0, 1.0, 2.5, 3.0]
    for s in slots:
        if rng.random() < (0.55 if args.mood != "upbeat" else 0.8):
            n = notes[int(rng.integers(0, len(notes)))] + 12
            add(keys(hz(root + n)), t + s * beat, pan=float(rng.uniform(-0.5, 0.5)), gain=0.13 * float(rng.uniform(0.7, 1.0)))
    if args.mood == "upbeat":
        for q in range(int(M["bars"] * 4)):
            if q % 2 == 0:
                add(kick(), t + q * beat, gain=0.30)
            add(shaker(), t + (q + 0.5) * beat, pan=0.3, gain=0.05)
    t += chord_len
    k += 1

# ---- room and softness: one pass in the frequency domain (a short diffuse tail, everything above ~5 kHz rolled off)
def finish(x, seed):
    n = len(x)
    r = np.random.default_rng(seed)
    tail = int(1.8 * SR)
    ir = r.standard_normal(tail) * np.exp(-np.arange(tail) / (0.45 * SR))
    ir[: int(0.012 * SR)] = 0.0
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << int(np.ceil(np.log2(n + tail)))
    X = np.fft.rfft(x, size)
    f = np.fft.rfftfreq(size, 1.0 / SR)
    wet = np.fft.irfft(X * np.fft.rfft(ir, size) / (1 + (f / 3500.0) ** 2), size)[:n]
    dry = np.fft.irfft(X / (1 + (f / 5200.0) ** 4) * (f > 28), size)[:n]
    return dry + 0.30 * wet


L, R = finish(L, 11)[:N], finish(R, 23)[:N]
t = np.arange(N) / SR
env = np.minimum(1.0, t / 1.5) * np.minimum(1.0, np.maximum(0.0, (D - t) / 2.2))
L, R = L * env, R * env
peak = max(np.abs(L).max(), np.abs(R).max(), 1e-9)
g = 10 ** (-6 / 20.0) / peak                                # peak at -6 dBFS; render.py sets the real level against the voice
pcm = (np.stack([L, R], axis=1) * g * 32767.0).astype("<i2")
os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
with wave.open(args.out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
bpm_, key_ = JAZZ_INFO if JAZZ_INFO else (M["bpm"], root)
print("wrote %s: %s, %.1f s, %d bpm, key root midi %d, seed %d" % (args.out, args.mood, D, bpm_, key_, args.seed))
