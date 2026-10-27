---
name: davinci-edit
description: Edit a long-form 16:9 YouTube video (about 5 to 25 min) end to end in DaVinci Resolve via the davinci-resolve MCP. Analyses 20 to 60+ min of raw footage, writes a storyboard, assembles the cut in Resolve, adds B-roll, punch-ins, colour, cleaned voice, a ducked music bed, SFX and subtitles, then renders and QCs. Animated scenes, overlays and fully animated sections are built with HyperFrames (shorts-edit tools and look) and placed on the timeline. Also makes fully animated long videos from a voiceover alone (chapter title cards, navbar progress, per-chapter dark gradients, realistic X/LinkedIn/Reddit/Facebook/YouTube/n8n UIs, plain white subtitles) with a proven HyperFrames kit, no Resolve needed. Use whenever the user says "edit this in Resolve", "DaVinci", "long video", "10 minute video", "turn this footage into a video", "rough cut", "assemble the timeline", "grade this", "render from Resolve", "animate my voiceover", "animated long video", "make a video from my audio", "build the video from this recording", or drops raw footage longer than a Short, even without naming Resolve. Vertical Shorts under 3 min use shorts-edit.
---

# DaVinci long-form editor

Turns a pile of raw footage into a finished 16:9 YouTube video, with **DaVinci Resolve as the edit**: the cut, the
timeline, B-roll, camera moves, colour, subtitles and the render all live in a Resolve project the creator can open,
scrub and change by hand. Where Resolve's scripting is weak (animation, audio levels, speed ramps), the work is done
outside Resolve with the `shorts-edit` tools and dropped back onto the timeline as a rendered clip or a baked audio file.

**Division of labour (the one idea to keep in mind):**

| Resolve does (via the `davinci-resolve` MCP) | Outside Resolve (FFmpeg, Parakeet, HyperFrames) does |
|---|---|
| media pool, timeline assembly, trims, track layout | voice clean-up and loudness (baked into a new WAV) |
| B-roll placement, punch-ins and pans (transform keyframes) | transcription with word times (Parakeet) |
| colour: balance, exposure, LUTs/CDL, shot matching | animated scenes, overlays, lower thirds, fully animated sections |
| subtitles (Studio AI captions, or an SRT we import) | music bed fitted and ducked under the voice (baked) |
| transitions and fades (21.1+), markers, versions | speed ramps / slow motion (Resolve's retime is not scriptable) |
| render jobs and render QC | page captures, logos, references (browser) |

**Two skills, two formats.** This skill is long-form only (16:9, usually 10 to 15 minutes). `shorts-edit` is Shorts
only (9:16) and stays exactly as it is: borrow its scripts, sounds, fonts and look read-only, and never edit its files
for long-form work.

**Voiceover only, fully animated (no footage)?** Do not use Resolve. Follow `references/animated-longform.md` and the
kit in `animated/` (scripts, shared look, and the approved "My First Week on YouTube" chapters as a scene library).
It is the creator's approved process for 5 to 10 minute animated videos: start there every time.

**This skill keeps learning.** When the creator gives a note worth keeping and says **"save this to the skill"**, write
it into the right section here as one plain rule. A new rule that contradicts an old one replaces it.

## Before anything: read the build, then the guides

Resolve's scripting API changes per patch release. At the start of every session:

1. `resolve_control get_version` (load the tool with ToolSearch first). Note the version, Studio or free, and
   `build.unavailable_on_this_build`. Free 21.1+ may not be reachable at all; say so plainly.
2. `project_manager get_current` and `timeline list`. Open or create the project the creator names
   (`project_manager load` / `safe_project_create`). Never close or switch a project with unsaved work without asking.
3. Before a creative or destructive step, read the matching guide with `knowledge get`: `resolve-rough-cut`,
   `resolve-tighten-recording`, `resolve-edit`, `resolve-color`, `resolve-audio`, `resolve-delivery`. They carry
   measured numbers and traps; this skill only summarises the ones that bit. `references/resolve-traps.md` lists them.

**Measured limits on this connection (do not promise these, route around them):**
- **Clip speed / retime is not scriptable on any build.** Slow motion or a speed ramp: make the clip with FFmpeg
  (`setpts`, `minterpolate`), import the result.
- **Audio Volume / Pan writes on timeline items are ignored.** Every level is baked into the audio file before import.
  Fairlight automation is not reachable either.
- **Fusion comps built by script did not show up in the render on Studio 21.0.4** (they did on 19.1.3). Any Fusion
  title or effect must be proven on a rendered frame; by default, build animation in HyperFrames instead.
- `add_transition`, `set_fades`, `set_speed` (native) need Resolve **21.1+**; check `get_version` before offering them.
- Subtitle burn-in render settings were measured inert before 21: verify the rendered file, not the setting.

## Where the videos live

Same convention as `shorts-edit`: **every video is one folder in `edited_videos/`** made by the creator, holding the
footage, voiceover, script, images and notes. Look there first (the named folder, or the newest one without a final cut).

- Read everything in the folder before planning. The script is the source for spelling and intended order; a notes file
  is instructions from the creator.
- **Never change, move or transcode the creator's files.** Work files go in `edited_videos/<video>/_work/` (`$W`).
  Derived media (cleaned audio, rendered inserts, conformed B-roll) goes in `$W/media/` and is what Resolve imports
  alongside the originals.
- The Resolve project is named after the video folder. The final render goes to `edited_videos/<video>/<video>-vN.mp4`;
  the `.srt` and reports go in `edited_videos/<video>/extras/` (never beside the MP4, players would load it twice).

```bash
SK=".claude/skills/shorts-edit"; DS=".claude/skills/davinci-edit"; V="edited_videos/<video>"; W="$V/_work"
export PYTHONUTF8=1 npm_config_cache=/d/devtools/npm-cache HYPERFRAMES_NO_TELEMETRY=1 HYPERFRAMES_NO_UPDATE_CHECK=1
export TEMP=/d/devtools/tmp TMP=/d/devtools/tmp      # C: is nearly full; renders and Resolve caches must not land there
```

Machine: 8 GB RAM, no dedicated GPU, C: nearly full. Use Resolve's optimized/proxy media for 4K footage (ask before
generating), keep one heavy job at a time (Resolve render **or** HyperFrames render, not both), and close other apps.

## The pipeline (four checkpoints, the rest unattended)

| Stage | Output | Checkpoint |
|---|---|---|
| 1. Ingest and analyse | footage inventory, transcripts, shot notes | |
| 2. Storyboard | `$W/STORYBOARD.md` (+ `storyboard.json` for animated inserts) | **A: the creator approves the story** |
| 3. Assemble in Resolve | `<video> v1` timeline: A-roll cut, B-roll, camera, inserts placeholders | **B: stills + beat list review** |
| 4. Dress | inserts rendered and placed, grade, subtitles, music and SFX | **C: review the dressed timeline** |
| 5. Render and QC | the MP4, `.srt`, `extras/QC.md` | **D: the creator watches the file** |

A note at any later point is a targeted change on a **new timeline version** (`timeline duplicate` or the edit engine's
variant), never a rebuild.

### 1. Ingest and analyse

1. **Inventory.** `ffprobe` every file: duration, resolution, fps (phones are variable frame rate), audio channels,
   colour (HDR/HLG vs SDR). Classify each: A-roll (the creator talking), B-roll, screen recording, voiceover, music,
   stills. Ask once about anything ambiguous (two files that could each be the intro).
2. **Clean the voice** of every A-roll and voiceover file, before anything else hears it:
   `python $SK/scripts/clean-audio.py --in FILE --out $W/media/audio/<name>-clean.wav` (DeepFilterNet strength 30, the
   setting the creator approved, then the polish chain to -16 LUFS). These WAVs replace the camera audio on the timeline.
3. **Transcribe** with Parakeet (16 kHz mono WAV from the cleaned audio): `python $SK/scripts/transcribe.py --audio
   X16k.wav --out $W/transcripts/<name>.json`. Word-level times are the backbone of every later step.
4. **Import into Resolve** (`media_pool safe_import_media`, dry run first) into bins: `A-Roll`, `B-Roll`, `Screen`,
   `Audio`, `Inserts`, `Music`. Mark VFR phone clips; if Resolve plays them unevenly, conform a constant 30 fps copy
   with FFmpeg into `$W/media/` and import that instead.
5. **Analyse in Resolve** with `media_analysis`: `capabilities` and `get_caps` first, then `analyze_bin` on A-Roll and
   B-Roll with `background: true`, poll `batch_job_status`. Vision runs through you: read the returned frame paths and
   `commit_vision`. Ask for: what each shot shows, framing, **exposure (under/over), white balance, focus (soft or
   sharp), motion/shake**, faces, on-screen text. `plan_story_beats` / `commit_story_beats` segments long takes.
6. Write `$W/FOOTAGE.md`: one row per clip with its role, length, quality flags (soft focus, dark, shaky, noisy audio)
   and the best moments. Soft-focus and badly lit takes are dropped when a better take exists; when none does, say so.

### 2. Storyboard (Checkpoint A)

Build the story from the transcript, not from file order. For a 30 to 40 minute recording aiming at 10 to 20 minutes:

- **Paper cut first**: `python $SK/scripts/paper-cut.py` logic (keep the last clean take of each line, drop restarts,
  "cut that", false starts). For several separate clips, use the edit engine's evidence instead:
  `edit_engine plan_selects` (ranked shots) and `plan_tighten` / `plan_silence_ripple` (dead air). Plans are dry runs.
- **Structure** (YouTube long-form): a hook in the first 15 to 30 s that states the payoff; a short promise of what is
  coming; sections (chapters) each with one point; a pattern change every 20 to 40 s (B-roll, a punch-in, an insert, a
  screen); a recap and one call to action at the end. Cut anything that repeats a point already made.
- **Find what to show.** For every line, decide the picture: the creator on camera, B-roll from the footage, a screen
  recording, a real page captured with the browser (the shorts-edit "References" rules apply: real pages, real numbers,
  never a made-up dashboard), or an animated insert (an idea with no picture: a process, a comparison, a number).

Write `$W/STORYBOARD.md` as a table the creator can read in two minutes:

```markdown
| # | Time (target) | Chapter | Spoken (first words … last words) | Picture | Camera | Audio | Note |
|---|---|---|---|---|---|---|---|
| 1 | 0:00–0:22 | Hook | "I spent 30 days…" … "here's what happened" | A-roll take 3 | punch 1.12 on "30 days" | voice, riser into title | insert: title card |
| 2 | 0:22–0:41 | Promise | … | B-roll desk + screen | slow push | music in | lower third: name |
```

Also list: target length, chapters with timestamps (they go in the YouTube description), every animated insert (what
it shows, its length), every reference fetched (URL, where it appears), and **your own concerns** (a weak take, a
claim without a source, a missing shot). Show it and wait. The creator answers in plain words; update and re-show only
the changed rows.

### 3. Assemble in Resolve (Checkpoint B)

Read `knowledge get resolve-rough-cut` and `resolve-tighten-recording` first.

1. **Timeline**: `media_pool create_timeline` named `<video> v1`, 3840x2160 (or 1920x1080 if the footage is HD),
   at the A-roll's frame rate (usually 30). Set it in project settings before adding clips; changing fps later breaks
   everything. Track layout:
   - V1 A-roll · V2 B-roll and screen · V3 animated inserts and overlays · V4 spare
   - A1 cleaned voice · A2 music bed (baked, ducked) · A3 SFX (baked stem) · camera audio muted or not placed
2. **Cut the A-roll**: `media_pool append_to_timeline` with `clip_infos` (source `start_frame`/`end_frame`, end
   exclusive, `record_frame` relative to the timeline start). **Place one range, read it back with
   `timeline clip_where` (position, duration, source span), then batch the rest.** Plan ranges are SOURCE frames;
   `structural_diff` numbers are RECORD frames: mixing them puts every clip at the wrong moment and nothing errors.
   For one long take, `edit_engine execute_tighten` / `execute_silence_ripple` builds the cut as a new variant timeline.
3. **Replace the camera audio** with the cleaned WAV: place it on A1 at the same source range (same file length, same
   start, so the frames line up), and disable the camera audio track. Check sync on one clip by ear and by
   `media_analysis detect_sync_events` if anything looks off.
4. **Tighten**: no pause over about 0.5 s inside a section (calmer pieces up to 0.7 s), every edge on a breath or
   word gap. `media_analysis cut_candidates` ranks cut frames near a joint (blink, pause, breath) when a jump cut looks rough.
5. **B-roll** on V2 at the line it illustrates, 2.5 to 6 s each, entering just before the word and leaving on a phrase
   end. Never cover the first seconds of the hook or a moment where the creator's face carries the point. Conform
   stock or phone B-roll first (`$SK/scripts/broll-conform.py`, but at 16:9: `--vf` to scale/crop, no audio). Stock
   rules from shorts-edit apply: Pexels first, no AI-labelled clips, no readable third-party logos, and **downloading
   needs the creator's yes** (show a shortlist).
6. **Camera** on A-roll (`timeline_item set_transform` + `add_keyframe` on ZoomX/ZoomY/Pan/Tilt, EaseInOut):
   - a punch-in of 1.10 to 1.20 on alternate jump cuts so cuts read as intent (4K source gives room without blur);
   - a slow push (1.00 to 1.06 over the shot) on an emotional or important line;
   - reframing a badly framed take (head cut off, off-centre) with Pan/Tilt and a slight zoom.
   Never zoom HD footage past 1.15 (it goes soft).
7. **Placeholders** for inserts on V3: a coloured marker or a solid generator with the insert's name, so the timing is
   fixed before the animation is built.
8. Review: `timeline detect_gaps_overlaps` (must be clean), `timeline story_spine_report`, and stills at each section
   with `gallery_stills grab_and_export` or `timeline thumbnail_contact_sheet` (source frames only: fine for checking
   the cut, NOT proof of grades or Fusion). Show the creator the beat list with timecodes, length, and concerns.

### 4. Dress (Checkpoint C)

**Animated inserts (HyperFrames, outside Resolve).** Anything that animates (explainer scenes, numbers counting,
flows, browser scenes with a callout, a lower third, the subscribe ask, a title card, a fully animated voiceover
section) is built with the `shorts-edit` composer and its format library and look (paper/ink themes, Fraunces + Geist,
the devvora.dev palette, `STYLE-GUIDE.md`). Read `references/inserts.md` for how to build one at 16:9, time it to the
voice and render it. In short:
- each insert is its own small HyperFrames project in `$W/inserts/<name>/`, 1920x1080 (or 3840x2160), timed to the
  words of the voice it sits under;
- **full-frame scenes** render to MP4 and replace the picture on V3 for their length;
- **overlays over footage** (lower thirds, cards, captions-style callouts) need a transparent background: render with
  alpha if the installed HyperFrames supports it (check `npx hyperframes render --help` for a transparent/ProRes 4444
  or WebM alpha option); otherwise render the overlay **with the footage underneath** (pass that stretch of the timeline
  as a `clip` beat) and place the result over V1 for exactly that range;
- each insert's sounds come from its own build (the shorts-edit SFX table and volumes: every animated element gets a
  subtle sound) and are exported as part of the insert, or mixed into the SFX stem.
- A **fully animated video** (voiceover only): follow `references/animated-longform.md` (kit in `animated/`), not
  Resolve. Its look (dark per-chapter gradients, DM Sans/Geist, outline-box title cards, navbar) is the approved
  long-form look; use it for inserts in footage-based videos too unless the creator asks otherwise. For pieces under
  3 minutes, `shorts-edit` alone is simpler: say so.

After rendering, import into the `Inserts` bin and place on V3 at the placeholder's record frame; read back each one.

**Colour** (read `knowledge get resolve-color` first; grab a still/.drx backup of any clip before changing it):
- Balance first, then match, then the look. Fix exposure and white balance per clip so skin sits naturally and the
  shots of one scene match; `timeline apply_look_to_items` copies a corrected grade (or a CDL) across the same setup.
- A gentle house look on top (a timeline-level node or a LUT the creator chooses), never a heavy stylised one on a
  talking head.
- **Lighting and focus cannot be reshot.** A dark take can be lifted (with noise); a blown-out window cannot be
  recovered; soft focus cannot be fixed. Flag those in FOOTAGE.md, prefer another take, and suggest the fix for next time
  (key light at 45 degrees, lock exposure and focus on the phone).
- Prove the grade on a rendered or grabbed frame (`gallery_stills grab_and_export`), never on a thumbnail.

**Subtitles:**
- Studio: `timeline_ai create_subtitles` (background job), then fix names, products and money (the script is the
  spelling source), then style with `set_subtitle_preset`.
- Otherwise build the `.srt` from the Parakeet transcript (phrases of 1 to 7 words, under 42 characters per line, no
  line split inside a name) and import it onto the subtitle track.
- For YouTube, deliver the `.srt` as a separate upload by default (searchable, viewer can switch it off). Burn in only
  when the creator asks; then verify the burn-in on the rendered file.

**Audio (all baked outside Resolve, then placed):**
- Voice: the cleaned WAVs from stage 1, levelled to -16 LUFS each.
- **Music:** the creator supplies tracks they have rights to (YouTube Audio Library, Epidemic, Artlist), or
  `python $SK/scripts/music.py --mood jazzy --duration S --seed N` makes the house jazzy bed. Different sections may
  use different beds (calmer under explanation, more energy under B-roll montages). Fit and duck it outside Resolve:
  export the voice stem of the cut (render an audio-only job from Resolve, or concatenate the cleaned WAV ranges in
  timeline order), then `ffmpeg` sidechain-compress the music against it (`sidechaincompress=threshold=0.03:ratio=8:
  attack=20:release=400`), music sitting about 11 LU under the voice (around -25 LUFS), cut 5 dB around 2.6 kHz.
  Fades in at the intro and out at the end. Import the result and place it on A2 from frame 0.
- **SFX:** collect the hit times (B-roll entrances, punch-ins, inserts, chapter titles) from the timeline, build one
  stem with the shorts-edit sounds at their subtle volumes, place on A3. A sound needs a visible cause.
- Re-bake whenever the cut changes (it is quick; the timeline positions are the input).

### 5. Render and QC (Checkpoint D)

Read `knowledge get resolve-delivery` first.
1. `project_manager lint` must be clean (no offline media, no mixed fps).
2. `render prepare_delivery_job` with target `youtube` (H.264/H.265, 3840x2160 or 1920x1080, timeline fps, AAC 320k),
   target dir `edited_videos/<video>/`, custom name `<video>-vN` (count up, never overwrite). Start it with
   `render start`; poll `get_job_status` sparingly (a 15-minute 4K video renders for a long time on this machine).
3. `render verify_output` with `expected_duration_seconds` **before** deleting the job (a "Complete" job can be a stub).
4. Own QC with ffprobe/ffmpeg into `extras/QC.md`: duration matches the timeline, picture and sound the same length,
   loudness about -14 LUFS integrated, true peak under -1 dBTP (fix by re-baking the stems, not in Resolve), no black
   runs (`blackdetect`), no silent runs over 2 s, and a contact sheet of frames from the rendered file (look at it).
5. Deliver: the MP4 path, its length and size, the chapter list with timestamps for the description, the `.srt` in
   `extras/`, what was added where, and your concerns. Open from Explorer; do not pass a large file through chat.

## Safety rules (always)

- Every destructive timeline action archives the timeline first (the MCP does it); for a series of edits wrap them in
  `timeline_versioning begin_run` / `end_run`. Keep `<video> v1`, `v2`… so any version can be reopened.
- Dry run first wherever the tool offers it (`dry_run`, `plan_*`, `confirm_token`). Show plans before executing on
  anything the creator already reviewed.
- Never delete media pool clips, timelines or projects without the creator's yes. Never touch source files.
- `project_manager save` after each stage.
- A claim about the result (grade, Fusion, subtitles, levels) is proven on a rendered or grabbed frame / measured file,
  never on a setting's readback.

## What this does not do (say so rather than fake it)

- Generate new filmed footage or illustrated art. Animation is built from type, shapes, icons, real screenshots and the
  creator's own assets.
- Watch the video like a viewer: judgement comes from the transcript, analysis and stills, so Checkpoints A to D matter.
- Per-parameter Fairlight mixing, retime, or AI Audio Assistant through script (the API does not have them).
- Upload to YouTube. The creator uploads; the skill provides the file, chapters, `.srt` and a suggested title,
  description and thumbnail frame on request.
