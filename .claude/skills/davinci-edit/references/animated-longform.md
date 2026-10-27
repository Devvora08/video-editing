# Fully animated long-form (voiceover → 5 to 10 min animated video)

The approved way to make a long video from the creator's voiceover alone, proven on "My First Week on YouTube"
(7:08, `edited_videos/first_week/first_week-v1.mp4`). The creator called the styling, music and real-world UIs
exactly what they wanted. **Start every new animated long-form from this file and the kit in `animated/`.**
Resolve is not needed for this; it is all HyperFrames + FFmpeg.

## What the creator wants (non-negotiable)
- A new visual for nearly every sentence, each one showing literally what the voice says (inspired by two
  references, see `style-study/STYLE-STUDY.md`): kinetic type, diagrams that build on the words, counters, cards.
- **Real platforms look real.** When he talks about X, LinkedIn, Reddit, Facebook, YouTube, YouTube Studio,
  Google Meet, WhatsApp, Telegram, n8n, DaVinci Resolve, etc., build a near-exact UI of that product (layout,
  colours, type sizes), using his real profile details from the reference screenshots he provides (he keeps them
  in the video folders, e.g. `edited_videos/12-10-2026/*_reference*.png`). His handles: X `@Devvora15`, YouTube
  `@devvora08`, site `devvora.dev`, subreddit `r/YourServiceGuy`. Real screenshots (his site, sponsor email) are
  shown as images in a browser/mail window, scrolled and highlighted.
- Name spelling: **Dev Vora** (two words). Parakeet mishears it.
- **Plain white one-line subtitles** at the bottom (40 px, soft shadow, no highlights). Keep y > 950 clear.
- **Chapter title card**: thin white outline box that draws in from its sides, light Geist 300 text, a mono
  "CHAPTER 0N" kicker above (his reference: `edited_videos/first_week/N8N Automation Title Card.png`).
- **Top navbar**: one pill per chapter, each with its own progress line filling through its chapter, a ✓ when done,
  active pill lit. Hidden during the opening, slides in at its end.
- **Dark gradient per chapter**, a different palette each (bg, glow, two drifting blobs), dark enough that every
  element reads clearly. Palette may shift inside a chapter at a new idea.
- Smooth motion only: soft ease-outs (power3.out, 0.55 s+), no bounce/elastic/back eases, transforms only.
- Nothing overlaps: snapshot every scene and fix collisions before rendering.
- No made-up numbers. Only figures he states; charts without values are fine as illustrations.
- **1080p by default. Do not render 4K unless he asks for it for that video** (he declined 4K for the pilot).

## The pipeline
```bash
SK=.claude/skills/shorts-edit/scripts; A=.claude/skills/davinci-edit/animated; V=edited_videos/<video>; W=$V/_work
export PYTHONUTF8=1 TEMP=/d/devtools/tmp TMP=/d/devtools/tmp
```
1. **Script first (if he asks).** Write the script as spoken lines only, chapter headings he reads aloud
   ("Chapter two: quality over quantity"), nothing else in the file (he found visual notes in it confusing). Keep a
   separate storyboard file for yourself. Fill every [bracket] with his real facts before he records.
2. **Clean + transcribe** the voiceover: `python $SK/clean-audio.py --in $V/<audio> --out $W/media/audio/voice-clean.wav`,
   16 kHz copy, `python $SK/transcribe.py --audio ...-16k.wav --out $W/transcripts/raw.json` (background job, minutes).
3. **Cut plan**: read the transcript with word times; find the spoken chapter titles and every retake ("they are
   giving me and they are giving me", "change how change how", a restarted sentence, "David, DaVinci"). Write
   `$W/build/plan.json` (format in `animated/plan.py`; full example in `animated/examples/first-week/plan.json`):
   kept source ranges per chapter, word fixes for mishearings, phrase fixes. Spoken titles are cut; each chapter
   gets 2.8 s of room at its start for the title card. Then `python $A/plan.py $V`.
   Check subtitle lines for orphans and mishears and iterate plan.json until clean.
4. **Music**: `python $SK/music.py --out $W/media/audio/music-raw.wav --duration <total+2> --mood calm --seed 11`
   (calm was approved).
5. **Images**: put the video's assets in `$W/build/img/` (avatar.png cropped from a profile screenshot, his
   thumbnails, site/email screenshots). Check every thumbnail's label matches what it's used for.
6. **Pages**: one `build/chN/page.html` per chapter (`<style>`, markup with `.clip` scenes, `<script>` calling
   `FW({...})`), plus `sfx.json`. Start by copying the closest example chapter from `animated/examples/first-week/`.
   Time every element 0.1 to 0.2 s before its word (`words.json` gives chapter-local times).
   `python $A/mk.py $V N`, then in `build/chN`: `npx hyperframes lint` (0 errors) and
   `npx hyperframes snapshot --at <every scene> --no-end --describe false -o ../../snaps/chN`. **Look at the sheet**,
   fix overlaps, re-snapshot changed beats.
7. **Render** chapter by chapter in the background, one at a time: `bash $A/render.sh $V 1080 0 1 2 ...`
   (~3.5 s per second of video; a 7 min video is ~25 min). Build the next chapter while one renders.
8. **Assemble**: `python $A/assemble.py $V 1080 v1` joins the chapters, ducks the music under the voice, levels to
   -14 LUFS / -1.5 dBTP and writes `extras/chapters.txt` (YouTube description timestamps) and `extras/<video>.srt`.
9. **QC** the file: ffprobe (video = audio length), ebur128, blackdetect (only the 0.7 s fade-in is OK),
   silencedetect (no gap > 2 s), a contact sheet of the rendered MP4 (look at it). Then send it.

## The kit (`animated/`)
- `shared/lib.css`: tokens, background layers, navbar, title card, subtitles, cards/pills/tiles/windows/avatar.
- `shared/lib.js`: `FW(cfg)` returns `tl` and helpers: `IN`, `INS` (stagger), `OUT`, `WIPE`, `DRAW` (stroke draw-on),
  `COUNT`, `TYPE`, `PULSE`, `FLOAT`, `BG(at, [bg, glow, blob1, blob2])`, `NAVIN`, `TITLE(id, at, out)`, `SUBS`, `done`.
  `cfg = {id, chapter, duration: DUR, palette, doneAt}`; chapter 0 hides the nav until `NAVIN`.
- `plan.py`, `mk.py`, `render.sh`, `assemble.py`: see their headers.
- `examples/first-week/ch0..6/`: the approved pages, the scene library. Reuse and adapt:

| Scene | Where |
|---|---|
| YouTube Studio upload dialog, Studio analytics (retention + viewed-vs-swiped) | ch0, ch1 |
| Week calendar with ticks, $0 → $1K MRR track, "IN PUBLIC" stamp, crossed-out plan card | ch0, ch1 |
| Day cards from real thumbnails, daily loop circle with a runner dot and spinning clock | ch1 |
| Stat cards counting up, retention curve with a red ring + "?" | ch1 |
| Crowd grid lighting up (algorithm tests on 100 → 300 → 1,000) | ch2 |
| Phone Shorts feed with a swipe gesture, two signal meters | ch2 |
| Stamps on cards ("RUSHED"), slam headline "QUALITY > QUANTITY", YouTube search with an OUTLIER result | ch2 |
| Script doc writing itself, 3 hook cards fanning out, time-split bar, weekly plan calendar, goal curve | ch2 |
| Client cards, 3-column "this week" (checklist, 5:30 AM board call grid, pitch with agent tree) | ch3 |
| Google Meet + WhatsApp windows, brand node, real site in a browser scrolled to services with highlights | ch3 |
| **X, LinkedIn, Reddit, Facebook, YouTube channel UIs** swapping with a left icon rail | ch3 |
| Platform web linking to a hub, visitor dot → CTA, real email zoom + highlight, 30-day ring + server rack | ch3 |
| Storefront illustration, **n8n editor** (dotted canvas, n8n nodes, bezier edges, packets, ✓, "1 item") | ch4 |
| `flow(canvas, nodes, edges)` builder with `node/edge/run/pkt`, product page form, Telegram bot phone | ch4 |
| Private dashboard (bars + lines, no fake values), 6/16/1 counters with a workflow grid | ch4 |
| Overflowing to-do → agent cards, Claude Code terminal, pipeline with ticks, DaVinci Resolve timeline | ch5 |
| Scheduled-jobs board, Me/Agents split | ch5 |
| Reference cards (abstract, never their footage), voice waveform → chapter mosaic, kinetic quote | ch6 |
| Subscribe press → "Subscribed ✓", comment poll bars, thank-you card | ch6 |

Palettes used (bg, glow, blob1, blob2): opening `#03061a #1238c8 #0a9fc0 #2b1aa0` · YouTube red
`#120309 #8e0f26 #ff2d55 #4a0a8a` · violet `#0d0418 #6512aa #e040fb #2e1ab0` · blue/gold `#040a1e #1a36b0 #ffb904 #2b4bff` ·
n8n `#100c14 #a02a4a #ff6d5a #5b3cff` · warm store `#120e0a #8a6a1a #f1d48a #ff6d5a` · teal `#031412 #0a6a5c #0AF0F0 #22d46b` ·
sunset `#140814 #8a2a4a #ff6a3d #7a2ab8`.

## Traps hit on the pilot (do not repeat)
- `:nth-of-type` counts tags, not classes: give repeated elements ids (`#a1..#a5`).
- `DRAW` overrides `stroke-dasharray`, so a dashed line drawn with it turns solid: fade/scale a dashed line instead.
- GSAP `xPercent: -50` plus a CSS `transform: translateX(-50%)` shifts twice: use one.
- Bars in a flex row need `height:100%` or a scaleY tween shows nothing.
- Never tween width/height/left/top/letter-spacing (lint error, stutters): transforms only; morph shapes with scaleX/Y
  and fade in contents (icons) after the morph so they do not squash.
- Every SFX on its own track (mk.py does it), long sounds capped (risers 1.6 s) or the renderer drops overlaps.
- The lint check wants `window.__timelines` in the page itself (mk.py adds it).
- Elements placed near the title/heading area (y < 240) or the subtitle band (y > 950) collide: check both.
- Two heavy jobs at once (render + render) risk the 8 GB machine; snapshots while a render runs are OK.
- A stopped background render leaves its node/Chrome children and the loop running: kill the render loop processes
  too, then remove the partial output folder.
