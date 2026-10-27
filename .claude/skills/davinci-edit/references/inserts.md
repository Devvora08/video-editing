# Animated inserts for a Resolve timeline (HyperFrames)

Read this before building any animation for a `davinci-edit` video. The insert is made outside Resolve, rendered to a
file, and placed on V3 at the placeholder's record frame.

## Which composer

| Composer | Canvas | Look | Use for |
|---|---|---|---|
| `.claude/skills/shorts-edit/scripts/compose.py` | 1080x1920 only | devvora.dev: paper/ink, Fraunces + Geist, imperial blue | Shorts only. **Never modify shorts-edit for long-form** (the creator keeps it 9:16-only); read its look and code, copy what you need |
| `youtube-edit/scripts/compose.py` | 1920x1080 | WeAreNoCode glass: DM Sans, cyan/amber/magenta | 16:9 inserts when the creator accepts that look |
| a hand-built HyperFrames page | 1920x1080 | devvora.dev, copied from shorts-edit | the default for long-form |

If the same hand-built scene keeps coming back across videos, turn it into a 16:9 composer that lives in **this** skill
(`davinci-edit/scripts/`), copied from shorts-edit's, never shared with it. Ask the creator first.

**Default: hand-build at 1920x1080 in the devvora.dev look.** Copy the fonts (`shorts-edit/assets/fonts/`), GSAP
(`shorts-edit/assets/vendor/gsap.min.js`), sounds (`shorts-edit/assets/sfx/`) and the colour tokens from the top of
shorts-edit `compose.py` / `STYLE-GUIDE.md`. Reuse its format vocabulary (statement, number, steps, flow, bars,
browser, terminal, cta) at the wider proportions: content sits in x 160 to 1760, y 120 to 900 (keep the bottom
180 px clear for subtitles), headline Fraunces 96 to 140 px, body Geist 40 to 56 px. Before writing code, write the
state sheet (every state, every change: property, ease, time) as the shorts-edit `raw` rules say.

## Timing to the voice

Every insert sits under a known stretch of the cut. Get the words for that stretch from the transcript of the timeline:
take the Parakeet words of the A-roll source range the stretch uses, and shift them to insert-local time
(`t_local = t_source - source_in`). Elements land 0.2 s before their word; an insert holds until its last word plus
0.45 s. Write the times in a small `times.json` next to the page so a re-cut is a re-time, not a rebuild.

## Render

```bash
cd $W/inserts/<name>
npx hyperframes lint                                   # 0 errors
npx hyperframes snapshot --at 0.5,2,4 --no-end --describe false   # look at it before rendering
# full-frame scene (opaque):
npx hyperframes render -f 30 -q delivery -w 1 -o ../../media/inserts/<name>.mp4
# overlay over footage (transparent background, ProRes 4444 with alpha):
npx hyperframes render -f 30 -w 1 --format mov -o ../../media/inserts/<name>.mov
```

- `-f` must equal the Resolve timeline's frame rate. `-w 1` on this 8 GB machine; never while Resolve renders.
- For an overlay, the page's `body`, `#stage` and root must have a **transparent** background. Check the alpha in
  Resolve on one frame (V3 over V1) before rendering the rest.
- ProRes 4444 is large (roughly 1 GB a minute at 1080p): keep overlays short and render them to `D:`.
- Sounds: an insert's SFX are not carried in a MOV overlay reliably; list the hit times (insert start + local time)
  and add them to the SFX stem instead (`SKILL.md`, Audio).

## Fully animated sections

A voiceover-only section is one page per chapter (3 to 4 minutes max per render on this machine), each with the
voice WAV as its timing source. Lay the renders end to end on V1 in Resolve with the cleaned voice on A1. Inside a page,
use one scene at a time and a wipe between scenes (the shorts-edit transition rules apply).

## Checks before placing

- Duration of the file equals the placeholder's length (ffprobe), frame rate equals the timeline's.
- A frame from the rendered file (not a snapshot) looks right: `ffmpeg -ss T -i file -frames:v 1 check.png`.
- Real pages and numbers only; every reference listed at Checkpoint C with its URL.
