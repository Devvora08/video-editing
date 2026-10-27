---
name: shorts-edit
description: Edit a YouTube Short (9:16, 45 seconds to 3 minutes) end to end. Takes raw face-cam clips (retakes and all), a voiceover audio file, or both, cuts them, adds word-highlight captions, animated overlays and full-frame explainer scenes in a glass look (aurora by default; dusk, bloom, or the old devvora paper/ink), B-roll, camera moves and timed sound effects, then renders, checks and delivers the MP4 locally with HyperFrames. Use whenever the user drops a video or audio file and says "edit this short", "make a short", "today's short", "day N short", "cut this", "add captions", "add animations", "animate this voiceover", "explainer short", or names a clip to edit for Shorts. Covers the three kinds of Short (face cam, hybrid face cam + voiceover, fully animated voiceover), the 0 to $1K MRR daily series preset, the cut stage, the storyboard composer and its format library, captions, sound, B-roll, render checks and delivery.
---

# Shorts editor

Turns raw recordings into a finished vertical Short: the cut, captions, animated overlays, full-frame scenes, camera
moves, sound and a checked MP4. Everything runs on this computer through HyperFrames (Chrome + FFmpeg) and Parakeet:
no per-render cost, no footage leaves the machine.

**This skill keeps learning.** When the creator gives a note worth keeping ("captions too low", "no sound there"),
and says **"save this to the skill"**, write it into the right section of this file as one plain rule, and update
`STYLE-GUIDE.md` and the tokens at the top of `scripts/compose.py` when it changes the look. A new rule that
contradicts an old one replaces it; never leave both.

## Where the videos live (always look here first)

**Every video is one folder inside `edited_videos/`**, made by the creator: `edited_videos/<video>/` holds everything
for that edit (the face-cam video, the voiceover audio, the script, images, logos, notes). When asked to edit a
Short, look in `edited_videos/` first: the named folder, or the newest one that has no final cut yet.

- **Read everything in the folder before planning.** The script is the source for spelling (names, products, money:
  feed them to `captions.replace`), for the intended order of the inputs, and for what each scene should show. Images
  and logos there are for this video: copy them into `_work/public/img/`. A notes file is instructions from the creator.
- **Never change or move the creator's files.** All working files go in `edited_videos/<video>/_work/` (that is `$W`).
- **The final cut is delivered into the video's own folder and nowhere else**: `edited_videos/<video>/<video>-vN.mp4`.
  `render.py` does this on its own when `$W` ends in `_work`. The `.srt` and the verify report go in an `extras/`
  subfolder, **never beside the MP4**: players auto-load a same-named subtitle file and the creator then sees two sets
  of captions. The captions are burnt into the picture; do not upload the `.srt` to YouTube either, unless he asks.
- Assets reused across videos (the profile photo, tool logos) live in `edited_videos/_shared/` (`img/`, `music/`).
- If something needed is missing (no audio, no day number, two files that could each be the hook), ask once.

Commands run from the project folder with:

```bash
SK=".claude/skills/shorts-edit"; V="edited_videos/<video>"; W="$V/_work"      # the creator's files in $V, our work in $W
export PYTHONUTF8=1 npm_config_cache=/d/devtools/npm-cache HYPERFRAMES_NO_TELEMETRY=1 HYPERFRAMES_NO_UPDATE_CHECK=1
```

Use `python` (not `python3`) on this Windows machine. The scripts find FFmpeg and `npx.cmd` themselves.

## The three kinds of Short

| Kind | Inputs | What the viewer sees |
|---|---|---|
| **Face cam** | one or more face-cam clips | the creator on camera, captions, overlay cards above the head, punch-ins, a few cutaways |
| **Hybrid** (the daily series) | face-cam clips + voiceover audio, in play order | face cam for the hook and the sign-off, full-frame animated scenes over the voiceover, pieces of the face clip reused as cutaways |
| **Animated** | voiceover audio only | full-frame scenes the whole way: an explainer built from what is said |

All three are one pipeline. `prep.py` joins the inputs in play order; a voiceover becomes black picture under its
audio, and the composer covers those stretches with paper and scenes (it knows where they are from `spans.json`).

## The pipeline (two checkpoints, everything else unattended)

```bash
# 1. PREP: inputs in play order -> one 9:16, 30 fps source, voice levelled across every input
#          (it also cleans every input's sound: only the voice gets through; see "Voice clean-up")
python $SK/scripts/prep.py --out $W --in cam:$V/hook.mp4 --in vo:$V/narration.m4a --in cam:$V/outro.mp4
#    one face clip used twice:  --in "cam:$V/face.mp4@0-14.2" --in vo:$V/vo.m4a --in "cam:$V/face.mp4@14.2-31"
# 2. CUT PLAN: transcribe (Parakeet), find speech, paper cut per input -> PAPER-CUT.md
python $SK/scripts/cut.py plan $W
#    >>> CHECKPOINT A: show PAPER-CUT.md. The creator answers in plain words ("keep the earlier take of the app line").
# 3. CUT APPLY: tighten, audit every edge by the audio, encode, re-transcribe, remove dead air, prove no word was lost
python $SK/scripts/cut.py apply $W
# 4. STORY + STORYBOARD: write $W/STORY.md (hook, loop, beat purposes; below), then $W/storyboard.json, then build and look
python $SK/scripts/compose.py --project $W --shared edited_videos/_shared
python $SK/scripts/beat-check.py --index $W/public/index.html --transcript $W/transcript.json
python $SK/scripts/snap.py --project $W
#    >>> CHECKPOINT B: read snaps/sheet*.png yourself first, fix what is wrong, then show the creator the sheet, the beat list and the STORY.md opening + loop.
# 5. RENDER + FINISH + VERIFY + DELIVER
python $SK/scripts/render.py --project $W --res 4k          # delivers into $V
```

- The inputs are read straight from `$V` and never edited. Voiceover-only: a single `--in vo:FILE`.
- **Length:** 45 s to 3 min. `cut.py` and `render.py` warn or fail past 180 s. The daily series aims at about 60 s.
- **Checkpoint A is not optional on a raw take.** A fixed misread costs seconds there and a full re-edit later.
- A note after delivery is an edit to `storyboard.json` (one number or one phrase), then steps 4 and 5 again.

## Setup check (first use, and after moving the skill)

| Needs | Check | Install when missing |
|---|---|---|
| Node.js 22+ | `node -v` | nodejs.org |
| HyperFrames CLI | `npx hyperframes --version`, `npx hyperframes doctor` | comes through npx |
| FFmpeg + ffprobe | `ffmpeg -version` (new terminal after installing) | `winget install --id Gyan.FFmpeg.Essentials -e --location D:\devtools\ffmpeg` |
| Python 3 + numpy | `python -c "import numpy"` | `python -m pip install numpy` |
| auto-editor | `auto-editor --version` | `python -m pip install auto-editor` |
| Parakeet | `npx hyperframes models list` | `npx hyperframes models install parakeet` |
| Google Chrome | page captures and snapshots run in it | google.com/chrome |
| DeepFilterNet (voice isolation) | `D:\devtools\deepfilter\deep-filter.exe --version` (or `DEEP_FILTER_PATH`) | the Windows `.exe` from github.com/Rikorose/DeepFilterNet/releases (ask before downloading); without it a weaker FFmpeg denoiser is used and `prep.py` says so |

Then `cd $SK/scripts && python -m unittest discover tests` must end with `OK`.

**This machine (checked when the skill was built):** 8 GB RAM, no dedicated GPU, C: nearly full. So:
- Caches live on D: (`npm_config_cache` above; `~/.cache/hyperframes` is a junction to `D:\devtools\hyperframes-cache`;
  `render.py` keeps the frame cache in `$W/_cache`). Never let a render write to the system temp folder.
- Close other apps before a render. `--workers 1` if a render fails or paints black; 2 is the default.
- 4K is the delivery default the creator asked for; if a 4K render fails on memory, deliver `--res 1080` and say so.

**What ships:** the scripts, the fonts (Fraunces, Geist, Geist Mono; SIL Open Font License), GSAP, and the 19 free
HyperFrames sound effects in `assets/sfx/` (Pixabay Content License). **No music files ship**: the bed is
synthesised per video by `scripts/music.py` (nothing to license), or a file the creator supplies.

## Recording so the cut works

- Vertical, 4K if the phone allows, standard colour (HDR is tone-mapped, SDR is cleaner), one framing, the face in the
  middle third with clear space above the head (cards live there) and the chin above the lower third (captions live there).
- **Fluff a line? Pause two seconds and restart the whole sentence.** The last take wins. "Cut that" drops a stretch.
- Say numbers and money in full, name tools out loud, leave a second of silence at each end.
- Voiceover: same rules. Record it as one file in script order; retakes are removed the same way.

## Cut stage (what `cut.py` does and where it misreads)

`plan` runs the paper cut once per input, so a face-cam line is never taken for a retake of a voiceover line.
`paper-cut.py` keeps the **last take** of every line, drops restarts, false starts and "cut that / scratch that / start
over" (the marker and the sentence before it), and trims long pauses.

**Misreads to look for at Checkpoint A** (fix with `hand-cut.py --keep A-B ...`, which rebuilds the list from the kept
lines, or `patch-cut.py --add A-B / --drop T`; times are source seconds from `transcript-raw.json`):
- a list read as restarts ("an app, a backend, an automation");
- two different sentences that open with the same words: the first is struck as a "retake" of the second;
- a retake with the wrong number in it; a sentence retaken several times without a pause (keep the last clean take).

`apply` then runs: tighten-cut → sliver → edge-audit (must reach 0 issues) → apply-cut (one frame-exact encode with
20 ms audio fades into `public/input-video.mp4`) → transcribe → dead-air loop (no pause over 0.40 s after a sentence,
0.45 s elsewhere) → `spans.json` → `CUT-REPORT.md`. It exits 3 when an edge issue, a lost word or a repeated phrase
remains: read the report and fix before dressing the cut.

- **A phone in a real room is noisy** (the first real clip sat at 350 to 450 RMS between words; a studio is ~5).
  `prep.py` cleans every input by default (see "Voice clean-up"). `cut.py apply` also measures the room floor and scales
  its audio thresholds to it (it prints them); without that, nothing is tightened and every edge reads as "mid-word".
- `--keep-pause T` protects a deliberate beat (flat-cut time). A calmer piece: `--max-pause 0.7 --max-sentence 0.6 --target 0.45`.
- Parakeet marks phrase starts up to 0.4 s early and stretches last words into pauses: edges always come from the
  audio, never from word gaps. The report's "heard but not counted as kept" list is mostly that effect; a word there
  that you did NOT mean to keep is a leaked retake.
- "Transcribed differently" entries are spelling, not cuts: fix them in `captions.replace`.

## Story before graphics (write `$W/STORY.md` before the storyboard)

The first test, above every look and effect: **in the first 3 seconds, is a viewer convinced they need to watch to
the end?** This is editorial judgement, never a score. Answer it in writing before any `storyboard.json`, after
reading the locked cut's `transcript.json` line by line. `STORY.md` is short and has five parts:

1. **The payoff.** One sentence: what the viewer knows or has by the end, in the creator's own words. Never invent a
   result, a failure or a claim the footage does not say.
2. **Three openings.** Three different ways into the same spoken first lines: *problem first*, *result glimpse*, and
   *recognition first* ("you've done this"). For each: what is on screen at 0 s, what the viewer knows by 3 s, the
   question it opens, and the time it is answered. Pick one and write why. Reject vague teasing ("wait for it"), a
   promise this video cannot keep, a logo bumper, or loudness as the only hook. Vary the device between Shorts.
3. **The loop.** One main open question (at most one smaller one open at the same time), as a line each:
   `question | what shows it is unresolved | set up at | partial answers at | closed at | the words that close it`.
   Something missing that the viewer can see (empty slots, an unfilled progress bar, a locked card) beats a question
   mark. Close it **before** the CTA; "comment below" is never the answer. A thing that only reappears is a callback,
   not a closed loop.
4. **Beat purposes.** For every planned beat: what the viewer expects, and the new information or consequence it adds.
   A beat with no answer is cut.
5. **Rhythm.** Where it bursts (a few quick reveals), where it holds (a conviction line on the face, a result
   landing), and where it releases. 1 to 2 s per visual event is a check, not a metronome; a hold longer than about
   2.2 s needs a reason written here.

Rules this sets for the storyboard:
- **Every scene does something with a result.** A card flips to show the answer, a slot fills, a bar moves, a stack
  assembles, a crossed-out item turns into a check. No beat that only lands and freezes; idle bobbing on every card is
  not motion. Spend the strongest action on the most important spoken idea.
- **Don't say it three times.** The captions already carry the exact words. A scene should show the example, the
  number, the relationship or the consequence, not repeat the sentence as a headline (unless that emphasis is chosen).
- **Muted test.** With the sound off, the opening must still say the topic and change state once by 3 s.
- **Adjacent beats differ in action, not just words.** Read the snap sheet as shapes with the headings ignored; two
  neighbours that are both "a card slides in" means redesign the weaker one.
- **Real over generic.** For a named product or person, prefer the real page, screen recording, official logo or a
  verified photo (see References) over typing footage or a name in text. Never present a generated face as a photo.

## The storyboard (`storyboard.json`) and the composer

The storyboard is the review artifact **and** the source. **Times are written as the words they belong to**: any time
field takes seconds or a spoken phrase from `transcript.json`.

- `"in": "three things"` enters 0.20 s before the phrase; `"out": "real product"` leaves 0.45 s after it; `"out": "+4.5"`.
- Items carry their own phrase: `["A backend", "a backend"]` or `{"title": "...", "at": "phrase"}`.
- `"phrase#2"` = the second time it is said. Inside a beat, phrases are searched from the beat's `in` onward.
- A phrase that is not said fails the build with its name. Parakeet writes numbers as digits ("$0", "30", "7").
- With no `out`, an overlay holds 4.5 s and a scene holds until the next scene (or the end of the voiceover).

```json
{"id": "day-07", "mood": "balanced", "overlay_top": 150,
 "world": {"theme": "aurora", "chrome": {"left": "Day 07", "right": "$0 → *$1K MRR*"}},
 "frame": {"scale": 1.0, "y": 0, "origin": "50% 34%"}, "camera": "auto",
 "captions": {"replace": [{"say": "dev vora", "show": "Dev Vora"}], "emphasis": [{"say": "three things"}]},
 "beats": [
  {"type": "chip", "id": "day", "text": "Day 07 · Building in public", "in": "hi", "out": "+2.4"},
  {"type": "progress", "id": "mrr", "day": 7, "value": 0, "goal": 1000, "goal_label": "$1K", "in": "from $0", "out": "a month"},
  {"type": "statement", "id": "three", "kicker": "This week", "lines": ["I shipped", ["*three* things.", "three things"]], "in": "this week i shipped"},
  {"type": "steps", "id": "what", "kicker": "What shipped", "in": "first",
   "items": [{"title": "A mobile app", "sub": "iOS and Android", "at": "a mobile app"}, {"title": "A backend", "at": "a backend"}]}
 ]}
```

| Key | What it is |
|---|---|
| `world` | the look (`theme`: `aurora` default, `dusk`, `bloom`, or the devvora `paper` / `ink`), `overlay` (the look of cards over the face cam; defaults to the world's glass, `ink` for paper) and the `chrome` line at the top of every scene. One beat can take its own `theme` |
| `mood` | `calm`, `balanced` or `punchy`: how many sounds play and how loud |
| `overlay_top` | y of overlay cards over the face cam: the free space above the head (measure it on a snapshot) |
| `frame` | base framing of the face cam; `origin` is the zoom centre, on the face |
| `camera` | `"auto"` (a small punch-in alternates at jump cuts at least 1.4 s apart, so cuts read as intent) or a list: `["punch", t, 1.12]`, `["creep", t0, t1, 1.08]`, `["set", t, 1.0]`, `["release", t, 0.4]`; `"none"` |
| `captions` | see Captions |
| `cues` | extra sounds: `["riser", "the reveal", 0.10]` (a riser is started early so it crests on the time given) |
| `music` | `"auto"` (default: the jazzy bed), `"jazzy"`, `"calm"`, `"upbeat"`, `"tense"`, `"none"`, a file path, or `{"mood": "jazzy", "level": -25, "seed": 7}` |
| `tokens` | colour overrides per theme, e.g. `{"aurora": {"accent": "#ff6fb1", "b2": "#ff4fa3"}}` (`b1` to `b3` are the light blobs) |
| `raw_css`, `raw_html`, `raw_js` | page-level hand work |

Three working storyboards ship in `examples/`: `hybrid-daily` (the series shape, times as phrases), `every-format`
(one beat of each type, times in seconds) and `action-scenes` (the six action scenes; built in `videos/_gallery-actions`). Copy the shape from there rather than from memory.

`*word*` in any text marks the accent word (italic display face in headlines). Every beat takes `"sfx": false` or a
sound name. The composer prints the resolved times, format counts and WARN lines; fix every WARN or decide it out loud.

## Screen layouts (`"layout"` in the storyboard)

Pick the layout from how the creator recorded and what he asks for (reference shots: `layout1.png`, `layout2.png` in
the project root). Ask once if it is not clear.

| `layout` | What the viewer sees | Use when |
|---|---|---|
| `full` (default) | face cam fills the frame, cards float above the head | a normal face-cam Short |
| `split` | animations on top, the face cam fills the bottom edge to edge from y 880 (`layout2.png`) | animation-heavy face-cam Shorts; framing must keep the face in the lower half |
| `inset` | animations fill the screen, the face cam is a rounded card at the bottom, captions just above it (`layout1.png`) | the creator is a supporting voice, the graphics lead |

Options: `{"mode": "split", "top": 880}` or `{"mode": "inset", "height": 700, "bottom": 70, "radius": 44}`.
In `split` and `inset`, the world look plays behind the animations the whole time, every scene is fitted into the
area above the face cam, overlays sit at y 270 under the chrome line, and captions move (y 1700 in split, just above
the card in inset). Over a voiceover stretch the face cam steps away and scenes take the whole frame. Check on the
snapshot sheet that the face is centred in its box; move it with `frame.y` / `frame.origin`.
In `split`, captions sit on the seam just under the animation area (above the head, never over the mouth); keep
slot and step titles short (about 18 characters), the area is smaller than a full scene.

## Looks

The default is **not** the devvora palette any more (creator, 2026-10-15: "step out of it, be creative").

| Look | Feel | Field | Accent pair |
|---|---|---|---|
| `aurora` (default) | night sky, neon, premium tech | deep violet `#0a0720` with violet, pink and cyan light | pink `#ff6fb1` → cyan `#7ae8ff` |
| `dusk` | warm, golden hour, money and wins | near-black plum `#170b12` with orange, magenta and gold light | amber `#ffb547` → coral `#ff5e7e` |
| `bloom` | light, soft, friendly | cream `#fff5ee` with pink, lavender and mint light | violet `#7b3dff` → pink `#ff4f8b` |
| `paper`, `ink` | the old devvora.dev look | flat paper or ink with grain | imperial blue |

On aurora and dusk, elements on the background are **white** and cards are **white boards** with dark text; colour (the `pop` pair) appears only on the boards. Keep it that way: never put the look's own accent colour on its own background.

What the glass looks add, all automatic: three blurred light blobs drifting slowly behind every scene (on the
timeline, so renders are deterministic); frosted cards with a lit top edge and a coloured glow; the accent word as a
two-colour gradient; gradient icon boxes, progress fills, payoff nodes, connectors and URL pills; glowing gauge, stamp
and winner rings; and scene content that arrives out of focus and settles sharp. Pick one look per Short and keep it;
use a second look only for a single deliberate beat (`"theme": "dusk"` on that beat). Match the look to the story:
aurora for tech and building, dusk for money, wins and milestones, bloom for calm or personal Shorts.

## Format library

Vary the device: never the same format twice in a row (the composer warns). Sizes are 1080x1920 px.

**Overlays** (frosted cards over the face cam, at `overlay_top`; never over a voiceover stretch, never over the face):

| Type | Use for | Keys |
|---|---|---|
| `chip` | the series tag, a short label, the sign-off | `text`, `dot`, `align` |
| `title` | the hook line straight on the footage | `lines`, `size` |
| `card` | a person, a thing, a claim with a sub line | `kicker`, `title`, `sub`, `icon` |
| `list` | two to four short items, each on its word | `kicker`, `items`, `marker`: dot, check, number |
| `stat` | one number that counts up | `kicker`, `value`, `prefix`, `suffix`, `sub`, `at` |
| `progress` | the MRR track of the series | `day`, `value`, `goal`, `goal_label`, `at` |
| `logo` | a tool named out loud | `src` |
| `pills` | two to five short labels | `items` (`icon`, `tone`: accent, money, good) |
| `subscribe` | the ask | `title`, `sub`, `tap`, `bell` |

**Scenes** (full frame, in the world's look; content sits between y 250 and y 1250, captions below):

| Type | Use for | Keys |
|---|---|---|
| `statement` | one idea in big type, lines landing on their words | `kicker`, `lines`, `sub`, `hit` |
| `number` | a figure that is the point | `value`, `prefix`, `suffix`, `label`, `at` |
| `steps` | a numbered or checked list, one row per word, earlier rows dim | `items` (`title`, `sub`, `at`), `marker` |
| `flow` | a process: nodes joined by connectors, the last one the payoff | `nodes` (`label`, `sub`, `icon`, `payoff`) |
| `bars` | "this takes X, that takes Y" | `title`, `rows` (`label`, `value`, `text`, `hi`) |
| `browser` | a real page or app screen, scrolling, one spot ringed | `src`, `domain`, `frame`: browser, phone, `scroll`, `callout` |
| `terminal` | commands typed and their output | `title`, `lines` (`text`, `type`, `tone`: good, bad, dim, accent) |
| `clip` | a video cutaway: stock, a screen recording, a piece of the face clip | `src`, `media_start`, `label` |
| `image` | a still, full frame (`cover`) or framed (`card`) | `src`, `fit`, `label` |
| `cta` | the closing card | `photo`, `lines`, `url`, `chips` |
| `slots` | **the open loop**: numbered empty slots planted at once, each fills on its word | `kicker`, `title`, `items` (`title`, `sub`, `at`), `empty` (slots left open) |
| `versus` | old way against new way; the loser greys and is struck, the winner gets the ring and a check | `title`, `left`/`right` (`label`, `title`, `value`, `sub`, `at`), `winner`, `verdict` |
| `stamp` | a claim on a card, then the verdict slams onto it | `kicker`, `title`, `sub`, `stamp`, `tone`: good, bad, accent, money, `at` |
| `strike` | the wrong idea crossed out, the right one written under it | `kicker`, `old`, `new` (a line or a list), `at` (the strike), `new_at` |
| `receipt` | costs or wins printing line by line, the total counting up | `title`, `rows` (`label`, `value`, `text`, `at`), `total`, `total_label`, `prefix`, `total_at` |
| `gauge` | a score or speed: the needle swings from where it was to where it is | `kicker`, `value`, `from`, `min`, `max`, `prefix`, `suffix`, `label`, `at` |
| `raw` | a scene built by hand for this video | `html`, `js`, `times`, `theme`, `full` |

Icons: api arrow alert bell bolt browser chart chat check chip clock cloud code db doc eye folder gear globe heart key
layers lock mail money phone play robot rocket search shield star user video.

**Picking between them**

| You are... | Pick |
|---|---|
| saying one strong line | `statement`; on camera: `title` |
| giving one number | `number`; on camera: `stat`; the series MRR: `progress` |
| listing things | `steps`; on camera: `list` or `pills` (labels of one to three words) |
| explaining how something works | `flow`; with code or a deploy: `terminal`; bespoke mechanics: `raw` |
| comparing sizes | `bars`; a before and after with a winner: `versus` |
| setting up what the video will answer | `slots` (fill the last slot at the payoff) |
| a result or a verdict | `stamp`; a number moving to where it is now: `gauge` |
| correcting a belief ("it's not X, it's Y") | `strike` |
| adding up money or time | `receipt` |
| showing proof | `browser` with the real page, or `clip` of the real screen. Never a made-up dashboard or number |
| naming a tool | `logo` on camera; `pills` for three or more |

**Hand-built scenes (`raw`)** are how an explainer gets its own mechanics. Use the classes the library uses (`.kicker`,
`.disp`, `.ln > span` for masked lines, `.ssub`, `.node`, `.ic-box`, `.cchip`, theme variables `var(--fg)`,
`var(--accent)`, `var(--card)`, `var(--line)`). The `js` runs with `T0`, `T1` (the beat's window), `GO` (when content may
move, after a wipe), `AT` (the resolved `times`), `$` (a selector scoped to the beat) and the helpers `rise`, `maskIn`,
`pop`, `count`, `typeIn`, `draw`, `fadeOut`, `checkIn`, all on the one timeline `tl`. Before any code, write the state
sheet: every state (what is on screen, where, size, colour) and every change between two states (what moves, the
property, the ease, the time). A liked `raw` scene becomes a format: a branch in `compose.py`, a row here, a test.

## Captions (mandatory, always on)

Built from the flat-cut transcript: one short phrase at a time in an ink pill at y 1400, the word being spoken
inverted (paper block, ink text). `captions.json` and `captions.srt` are written on every build; the `.srt` is delivered.

| Key | Does |
|---|---|
| `replace` | fixes a mishearing or merges words: `{"say": "dev vora", "show": "Dev Vora"}`, `{"say": "one k", "show": "$1K"}` |
| `emphasis` | words that stay highlighted: `{"say": "three things", "color": "accent"}`; colours `accent`, `money`, `good`, `bad`; `"italic": true` sets them in the display face; `"nth": 2` picks one occurrence |
| `breaks` | start a new caption at a phrase (a name split badly, a punchline that should land alone) |
| `hide` | `[[t0, t1]]`: no captions in a window (only when the frame already shows the same words large) |
| `moves` | `[[t0, t1, y]]`: move the caption line for a window |
| `style`, `y`, `size`, `max_chars`, `max_words`, `case` | `pill` or `bare`; 1400; 58; 18; 4; `as-is`, `upper`, `lower` |

- **When the creator asks to highlight words, that is `emphasis`.** Two or three phrases a Short, the ones that carry
  the point: a number, the promise, the payoff. Money in `money`, a win in `good`. More than that and nothing stands out.
- Read every caption once in `captions.json`: names, product names and money are where Parakeet slips. Fix with `replace`.
- **Handles are shown** (creator, 2026-10-12): the official handles (@devvora08 on YouTube, @Devvora15 on X) and
  devvora.dev go on screen; following him everywhere is the point. His own profile screenshots are used **uncropped**
  when he supplies them, whatever they contain. We still never ADD a client project name (My Kind Karma, Smart
  Salesman / Sun n Shade) in text we write ourselves.
- Keep the mouth and chin above the caption line: raise `frame.y` (negative moves the picture up) or lower `captions.y`,
  but stay above y 1500 (YouTube's title and buttons cover the bottom, and x over 960 from y 850 to 1560).

## Voice clean-up (every input, automatically)

The creator hears "a buzz of wind, the atmosphere" under his voice even with the mic at his lips, and wants **only his
voice to pass through**. So `prep.py` runs `clean-audio.py` on the sound of every input, face cam and voiceover alike:

1. **Isolate**: DeepFilterNet (a speech-enhancement model, CPU, 48 kHz) pushes everything that is not speech down by
   `--strength` dB. **30 is the setting he approved** (2026-10-13, "much better"): on his first clips the voice went from
   29 to 46 dB above the room (face cam) and 31 to 35 dB (voiceover).
2. **Polish**: low cut at 80 Hz, -2 dB at 250 Hz, a de-esser, +2.5 dB presence at 3.5 kHz, 2.5:1 compression, then every
   input levelled to -16 LUFS so the phone mic and the voiceover mic match.

- "I can still hear the room": `prep.py --strength 40` (up to 100). "My voice sounds processed / thin": `--strength 20`,
  or lower `--presence` in `clean-audio.py`. Save the new number here when he settles on one.
- On its own, for a file he wants cleaned: `python $SK/scripts/clean-audio.py --in FILE --out FILE-cleaned.wav`.
- It adds about 1.5x the audio's length to prep. `--no-clean` skips it (studio audio).
- It cannot repair clipping (the mic too hot: his face-cam audio arrived at -11 LUFS, very loud) or wind hitting the
  capsule directly. Say so when you hear or measure it, and suggest lower gain or a foam windscreen.

## Sound

**A sound needs a visible cause.** The composer adds these on its own; change the feel with `mood`, silence a beat
with `"sfx": false`.

| Event | Sound | Volume |
|---|---|---|
| a scene wiping in or out | whoosh-short | 0.13 |
| a chip, pill or logo landing | pop | 0.20 |
| a list item, step, node or bar | click-soft | 0.15 |
| a count landing, a callout | ping | 0.12 |
| typing in a terminal, for exactly the typing time | typing | 0.16 |
| the subscribe tap / the bell | click / notification | 0.22 / 0.12 |
| the payoff node, a green terminal line | chime | 0.13 |
| a statement with `"hit": true` | impact-bass-1 | 0.16 |
| under-layer: a card or window arriving / a headline line landing / the winning bar growing | whoosh-short / click-soft / sparkle | 0.07 / 0.09 / 0.06 |

- **Every animated element has a sound, and every sound is subtle**: the creator asked for effects on the visual
  elements, never loud. When a note says "too loud" or "too many", lower the numbers in `SFX` at the top of
  `compose.py` (and this table) rather than muting beats one by one.
- `calm` drops item clicks and the under-layer and plays the rest at 0.7; `punchy` plays everything at 1.15. Match the piece: a
  reflective build log is calm, a launch or a hot take is punchy, the daily update is balanced.
- Two sounds within 0.09 s: the more important one plays. More than 7 in 10 s gets a WARN: thin it.
- Also in the library for `cues`: riser, whoosh, whoosh-cinematic, sparkle, glitch-1/2/3, impact-bass-2, error, key-press.
- Voice is levelled in `prep.py` (-16 LUFS per input) and the master is brought to -14 LUFS in `render.py`.

**Music: a fun, jazzy bed, far in the background, on every Short unless told otherwise.** `render.py` makes it with
`music.py` to the exact length of the video: a quiet swing trio (walking bass, electric-piano comping, a brushed
ride, a vibraphone answering now and then, ii-V-I harmony, about 104 bpm). It plays under the WHOLE video at -25 LUFS (11 LU under
the voice) and dips slightly while the voice speaks. At the first setting (-32) the creator could not hear it at all:
it has to be clearly audible in the background, and still never compete with a word.

- The creator rejected the first bed (a held pad on slow chords) as "calm nature-ish": the house sound is **fun and
  jazzy, not ambient**. `"auto"` is always `jazzy`. The others only when asked by name: `calm` (the ambient pad),
  `upbeat` (straight, a soft kick and shaker), `tense` (minor, a low pulse), `"none"`.
- **A new tune every time, fitted to the edit.** The seed comes from the video itself (its name and every word said),
  so no two Shorts share a tune; `{"seed": N}` picks one by hand. Speech has no steady beat, so the band follows the
  edit instead: `music.py --hits` chooses the tempo (98 to 118 bpm) and the downbeat so beats fall on the moments
  scenes and cards arrive, and the vibraphone and ride play a small accent exactly on each. It prints the fit ("beats
  land a median N ms from the hits"); under about 60 ms reads as in time. Change the storyboard's timing and the
  tune is refitted on the next render.
- **The voice always wins.** The bed is cut by 5 dB around 2.6 kHz (where consonants live), dips while the voice
  speaks, and `render.py` fails the delivery ("Music under the voice") if the bed is less than 9 LU under the voice
  or adds more than 1.0 LU to it.
- Louder or quieter: `{"level": -30}` in the storyboard or `--music-level -30`. Stay between -30 and -23 (the delivery check fails above that; below -30 it cannot be heard).
- A file the creator supplies (`"music": "edited_videos/_shared/music/track.mp3"`) is looped, set to the same level and ducked
  the same way. It is a synthesised bed, not a produced track: if the creator wants it more present, suggest a real
  track rather than turning this one up.
- A note on the music alone costs seconds: `render.py --skip-render` redoes the mix on the existing render.

## References: find them, fetch them, animate them

**Do this on every edit, without being asked.** After the cut, read the flat transcript and the script for anything
the viewer would want to SEE, and go and get it with the browser:

| The creator says... | Get | Show it as |
|---|---|---|
| a website, app or product by name | the real page, captured | `browser` (scroll through it, ring the part being talked about) |
| a tool, framework or company | its logo from its own site or press kit | `logo` on camera, `pills` for three or more |
| a number, fact or claim about the world ("70% of startups...") | the source page, to check it and to show it | `browser` with a `callout` on the figure, or `number` with the source named in `sub` |
| an article, a post, a launch, a news item | the page itself | `browser` scrolled to the headline; a quote goes in a `statement` with the source as kicker |
| the creator's own work ("my SaaS", "the dashboard") | their screen recording or screenshot from the video folder; else the live page | `clip` or `browser` |
| a person | ask for a photo; never pull one from search | `image` (`card`) |
| an idea with no picture ("an automation that saves time") | nothing to fetch | a scene: `flow`, `steps`, `bars`, or `raw` |

- **How:** research with the browser tools (search, open the page, read it). Capture a page with
  `npx hyperframes capture <url> -o $W/capture/<name> --skip-vision --max-screenshots 4`: it writes
  `screenshots/full-page.png` (use as the `browser` `src`, copied into `$W/public/img/`), the page's logos in `assets/`,
  and its text in `extracted/visible-text.txt` (quote from that, never from memory). Give `callout` in displayed pixels
  (the page is shown 936 px wide: source x and y times 936 / the screenshot's width).
- **Topic research when asked** ("research this", "find examples", "back this up"): search, open the two or three best
  primary sources, and report what was found with links BEFORE building on it. A claim goes on screen only with a
  source that says it; if the script's number does not match the source, say so at Checkpoint B and do not animate it.
- **List what was fetched at Checkpoint B**: each reference, its URL, and where it appears. The creator can drop any.
- **Limits, stated plainly:** pages behind a login, a paywall, a consent wall or bot detection are not worked around:
  ask the creator for a screenshot instead. Downloading a file (a video, a stock clip, an image that is not part of a
  captured page) needs the creator's yes first. No made-up screenshots, dashboards, reviews or numbers, ever.
- A capture of devvora.dev contains the client project previews: never put those on screen.
- **A name the creator has hidden stays hidden.** If he redacted a company in a screenshot or calls it "a European
  tech company" in the script, check every part of the image (subject lines, tabs, signatures) and mark any name he
  missed the same way on the working copy (day 4: the email subject still named the sender). Never edit his original.

## B-roll and sources

- **The creator's own footage first**: a screen recording of the real product is proof; a piece of the face clip
  (`"type": "clip", "src": ..., "media_start": s`) covers a jump cut or a long voiceover line.
- **Real pages**: capture with Chrome (`npx hyperframes capture <url>`, or the browser tools) and show them in a
  `browser` scene. Screenshots are windows showing the page, never crops of video frames. Do not work around bot
  detection, consent walls or logins; rebuild the top of the page from its real text instead, or ask for a screenshot.
- **Stock**: Pexels first (free on YouTube, no credit needed), then Coverr and Mixkit's free licence. Never a clip
  labelled AI-generated, never a paid tier, no readable third-party logos. Real people, vertical or croppable to 9:16,
  2.5 to 3.5 s. Downloading a file needs the creator's yes: propose a shortlist (page, licence, seconds to use) first.
- Conform every cutaway before use: `python $SK/scripts/broll-conform.py --in raw.mp4 --out $W/public/broll/x.mp4
  --start 2 --dur 4 [--4k] [--focus 0.5]` (9:16, 30 fps, no audio, dense keyframes), then read its sheet.
- Logos: the brand's own press kit or site. Photos of people: ask for the file.

## The daily series preset (0 → $1K MRR)

Hybrid, about 60 s: face cam hook → voiceover with scenes → face cam sign-off. Ask only for what is missing: the day
number, the current MRR, the files. Then:

- `world.chrome`: `{"left": "Day NN", "right": "$X → *$1K MRR*"}`.
- Hook (face cam): `chip` "Day NN · Building in public" on the first word → `progress` on the money line → at most one more card.
- Middle (voiceover): scenes found in what is said (see the picking table); 4 to 7 for 40 s; one `raw` scene at most.
- Sign-off (face cam): `subscribe` on the ask (`tap` on "subscribe", `bell` on "channel"), then `chip` "See you tomorrow · Day NN+1".
- Captions: `replace` for "Dev Vora", "devvora.dev", "$1K", "MRR"; `emphasis` on the day's one number and its payoff.
- `mood`: balanced. Music: auto (the jazzy bed, seeded by the day number: put `"series": {"day": NN}` in the storyboard).

## Reading the plan before rendering (Checkpoint B)

Read every tile of `snaps/sheet*.png` at full attention, and open `snaps/at-<t>.png` for anything doubtful:
- a card over the face or the hair; text off the frame or wrapped badly; a caption over the chin or under y 1500;
- a voiceover moment with paper and nothing on it; a scene whose content has not arrived yet at its snapshot;
- contrast (accent on a busy background), an image stretched, a number that is not the one said;
- the first frame: it must already say why to keep watching, and it must work muted.
- against `STORY.md`: the chosen opening is what the 0 to 3 s tiles show; the loop is visibly set up, updated and
  closed at the times written, before the CTA; every scene tile shows a changed state, not a card that only arrived;
  no two neighbouring tiles share the same action; no headline merely repeats the caption under it.

Fix, rebuild, snapshot the changed moments (`snap.py --only-at --at T`). Then give the creator the sheet, the beat
list with times, and **your own concerns**.

## Render, verify, deliver

`render.py` refuses to deliver a file that fails: wrong size, duration off by more than a frame, picture and sound of
different length, missing BT.709 tags, loudness away from -14 LUFS, any black run, over 180 s. The delivered folder
also gets the mix as rendered; `music.wav` in the project is the bed on its own. It writes `VERIFY.md`
and `render-sheet.png` (frames from the rendered file: look at it, the render can differ from the snapshots).
`--draft` is a fast low-quality pass for motion and timing. Delivery goes to `edited_videos/<video>/<video>-vN.mp4` with
the `.srt`; versions count up, nothing is overwritten. When the creator approves a version, `_work/` may be deleted
to free space (ask first; a later note is cheaper while it is still there). Open the file from Explorer; do not pass it through a chat upload.

Report: where the file is, its length and size, what was added where, and your concerns.

## Traps

- **HyperFrames lint warnings about file size, dense tracks and nested structure are expected** for a composed page.
  Any lint **error** stops the render.
- Every timed element is a `.clip` with `data-start` / `data-duration`; HyperFrames shows and hides it. Animate what is
  inside, never the host's visibility. A `<video>` cutaway is a direct child of the root, muted.
- Text that changes over time (counts, typing) comes from one proxy tween (`count`, `typeIn`), never a set per step.
- Never put a CSS `transform` on an element GSAP also moves; centre with the separate `translate` property.
- One scene at a time: a later scene takes the frame from the earlier one; only the incoming one wipes.
- Always `--engine parakeet` (the scripts do): `auto` falls back to another engine without a word.
- Phone footage is variable frame rate; never cut it before `prep.py` has made it constant 30 fps.

## Not built yet (say so rather than fake it)

Chat bubbles, before/after wipe, 3D browser, chart morphs, a
multi-part long-form route (10-minute videos: the kit this came from, `youtube-edit`, covers that and is the starting
point when the creator moves to long form).
