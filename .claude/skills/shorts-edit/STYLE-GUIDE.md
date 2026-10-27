# Style guide: devvora Shorts

**Default look since 2026-10-15: `aurora`** (see "Glass looks" below). The devvora.dev paper and ink looks further down
are kept as the `paper` and `ink` themes.

## Glass looks

| Role | aurora | dusk | bloom |
|---|---|---|---|
| Background | `#0a0720` | `#170b12` | `#fff5ee` |
| Light blobs (b1, b2, b3) | `#6a3cff` `#ff4fa3` `#13c3e8` | `#ff5e3a` `#c2187a` `#ffb03b` | `#ffb3d1` `#bfa8ff` `#9ff0dc` |
| Card | white 7 %, blurred 30 px | warm white 7 %, blurred | white 62 %, blurred |
| Text / soft | `#f6f3ff` / `#beb6e0` | `#fff4ea` / `#e2c4b6` | `#221238` / `#5f4f78` |
| Accent → accent 2 | `#ff6fb1` → `#7ae8ff` | `#ffb547` → `#ff5e7e` | `#7b3dff` → `#ff4f8b` |
| Glow | violet 35 % | coral 30 % | violet 22 % |

**White on the field, colour on the boards** (creator, 2026-10-15: "aurora elements on aurora bg is monotonous").
On aurora and dusk, everything that sits straight on the background is white: titles, kickers, big numbers, gauge,
bars, connectors, accent words (white italic). Every card is a solid **white board** with dark text (`#15102a`), and
only the boards carry colour: aurora pink `#e5368f` → violet `#6a3cff`, dusk orange `#f0640f` → rose `#d11f62`
(the `pop` token; caption emphasis uses it too). Bloom stays as it is.

Radius 30 on scene cards, 28 on overlay cards, pills stay round. Accent words and big numbers are gradients. Scene
content blurs in (18 px to 0 over 0.8 s). Keep the type (Fraunces + Geist) and every layout rule below.

## The devvora looks (`paper`, `ink`)

The original look, drawn from devvora.dev (paper, ink, imperial blue, Fraunces + Geist, hairlines, quiet
motion) and tuned for a phone screen. To change it, edit a row here and tell Claude: "update the shorts-edit skill to
match the style guide". The values live in `TOKENS`, `SFX` and the CSS at the top and bottom of `scripts/compose.py`.

## Colour

| Role | On paper | On ink / over footage |
|---|---|---|
| Background | Paper `#f5f2ec` | Ink `#15130f` |
| Card | `#fbf9f5` | `#1d1a15` |
| Text | Ink `#15130f` | `#f0ede4` |
| Soft text | `#5b564c` | `#a7a297` |
| Accent (key words, index numbers, active bars) | Imperial `#1d2f6f` | Imperial light `#9fb0f0` |
| Money | `#a8710a` | `#ecb850` |
| Good / done | `#2f8f5b` | `#62c890` |
| Live dot | `#ff5a4f` | `#ff5a4f` |

Imperial blue is never used on ink or over footage (it disappears): the light tint takes its place there.

## Type

| | |
|---|---|
| Display | Fraunces, weight 560, tight tracking. The accent word is *italic* in the accent colour |
| Body, captions | Geist 600 to 700 |
| Code | Geist Mono |
| Kicker | Geist 600, uppercase, letter-spaced, with a short rule before it |
| Numbers | Fraunces, tabular figures, counting up; index numbers (01, 02) italic |
| Smallest text on screen | 36 px (on a 1080 px wide frame) |

## Surfaces and layout

| | |
|---|---|
| Over the face cam | ink cards with a hairline border, radius 14, in the free space above the head (`overlay_top` 150) |
| Voiceover stretches | full-frame paper (or ink for a dramatic beat) with light grain; one chrome line at the top: day on the left, goal on the right |
| Scene content | between y 250 and y 1250, left edge 72 |
| Captions | y 1400, centred, inside x 80 to 960 |
| Keep clear | the top 140 px, everything under y 1500, the right 120 px from y 850 to 1560 (YouTube's buttons) |

## Motion

| | |
|---|---|
| Entrances | 0.5 s, `expo.out` (fast in, long settle); headline lines rise from behind a mask |
| Exits | 0.26 s, `power2.in` |
| Small things (chips, pills, the pin) | one soft overshoot, `back.out(1.8)` |
| Scene changes | a paper wipe upward, 0.45 s; same look to same look: content swaps, nothing wipes |
| Timing | every element lands on its word, 0.2 s ahead |
| Never | bounces on text, flips, spins, flashes, the same format twice in a row |

## Camera (face cam)

| | |
|---|---|
| Zoom centre | on the face (`50% 34%`) |
| Jump cuts | alternate framing 100% / 108.5% at cuts at least 1.4 s apart |
| Punch-in on a key word | 110 to 115%, 0.32 s |
| Slow creep | up to 108% across a thought |

## Captions

| | |
|---|---|
| Style | ink pill, Geist 700 at 58 px, one to four words |
| Spoken word | inverted: paper block, ink text |
| Emphasis | two or three phrases a Short; accent, money or good colour; optional italic display face |
| Punctuation | commas and full stops dropped; ? and ! kept |

## Sound

| | |
|---|---|
| Rule | a sound needs a visible cause; the voice always wins |
| Default mood | balanced (calm for reflective pieces, punchy for launches) |
| Effects | every animated element has one, all subtle (0.06 to 0.22); nothing louder than the voice's quietest word |
| Music | a fun, jazzy synthesised bed on every Short (a quiet swing trio), in the background for the whole video, clearly audible: -25 LUFS (11 LU under the voice), dipping slightly under speech |
| Music moods | jazzy (default), calm (ambient pad, only when asked), upbeat, tense, none |
| Master | -14 LUFS |

## Cuts

| | |
|---|---|
| Retakes | the last take of every line |
| Pauses | nothing over 0.40 s after a sentence, 0.45 s elsewhere |
| Length | 45 s to 3 min; the daily series about 60 s |
