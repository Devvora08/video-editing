# Style study: two motion-graphics creators

Source files (project root):
- **A, English:** `How To Create Insane Motion Graphics With Opus 5.5` (8:01, 480p, 30fps)
- **B, Hindi/Hinglish:** `Stop Uploading Daily Shorts` (6:35, 1080p, 30fps)

Method: frames read at 1 per second for both videos, a scene-cut pass, a loudness pass, and a full transcript of A. B's speech is mostly mirrored as on-screen kinetic text, so its script is readable from the frames.

| | A, English (tutorial) | B, Hindi (storytelling) |
|---|---|---|
| Overall feel | Calm, premium, Apple-keynote minimal | Loud, punchy, TV-promo maximal |
| Background | Off-white `#F7F8FA` to `#FFFFFF` near-flat; cream `#F2EFE9` for product scenes; near-black `#141414` for the logo/brand beats | Deep saturated gradients with a vignette: royal blue to indigo, purple to magenta, blood red, mustard/olive gold, dark grey |
| Accent | **One** colour, a terracotta/coral red (`~#D9573F`, Claude orange) | Yellow `#FFE600`, hot magenta `#FF2BD6`, neon green, cyan, plus YouTube red |
| Type | Small, quiet sans for labels. Large serif (Instrument-Serif style) with an *italic* accent word for headlines | Heavy condensed caps (Bebas/Anton style) for section titles, rounded bold sans (Gilroy/Montserrat Black) for body |
| Who is on screen | Talking head in a fixed corner PiP almost the whole time | No face cam. A voiceover drives illustrations, stock footage and memes |
| Integrated loudness | −14.9 LUFS (YouTube standard) | −10.9 LUFS (very hot, compressed) |
| Speech pace | ~210 wpm, fast and even | Fast Hinglish, read straight from a script |

---

## A: English creator. "Clean UI explainer with a face-cam corner"

### 1. Face cam placement (the key layout)
Measured on a 854×480 frame and scaled to 1920×1080:

- **Position:** bottom-left, always. About 2% margin from the left and bottom edges (~38px at 1080p).
- **Size:** a square crop about **380×380 at 1080p** (~20% of width, ~35% of height).
- **Shape:** rounded corners (~16 to 20px radius at 1080p) and a soft, wide drop shadow (big blur, low opacity) so it floats on the white canvas.
- **Crop:** head and shoulders plus the mic arm, from the same wide studio shot (dark warm room, plant, curtain, practical lamp). The warm, dark PiP contrasts hard with the white canvas, so your eye always finds the speaker.
- **The canvas works around it.** Every animation sits centred in the **remaining area**, usually upper-centre or centre-right, and never runs under the PiP. Flow diagrams start at x ≈ 25% of the width.
- **Three layout states:**
  1. **Full-screen A-roll** (no graphics). Used for the hook ~0:07, "why it matters" beats (0:15, 0:24 to 0:36), the reveal at 2:41, the reaction at 4:17, and the outro at 7:18. About 15 to 20% of runtime.
  2. **Canvas + corner PiP.** The default, about 70% of runtime.
  3. **Full-bleed showcase with no PiP.** He drops the cam entirely when showing the finished product video (4:27 to 4:47, 6:41 to 7:09) so the work gets the whole frame. The PiP comes back the moment he comments on it again.
- Between states it is a **hard cut**: no PiP fly-in. The PiP just appears or disappears.

### 2. The animation language
It's a **"UI-card explainer."** The vocabulary is small and reused constantly:

- **Icon tiles:** white rounded squares (~1:1, soft shadow) holding a logo or glyph, with a tiny grey label under it ("Claude", "ChatGPT", "Remotion", "HyperFrames", "Video").
- **Build-up chains:** tiles appear **one at a time, left to right, as he names them**, with thin grey arrows drawing in between (Code → Screen → Frames → Video at 1:00 to 1:06). Each new element arrives with a small scale-up (≈0.9→1.0) plus a fade, and the existing row shifts over to stay centred. That re-centring is the signature move.
- **Numbered step cards:** three white cards with circled numbers. The active card's number turns **accent-coloured** and gets a label ("1 Frameworks", "2 Drawn in code", "3 Image and video models"); the inactive cards drop to grey. Then he zooms *into* the active card's topic. Use this as a chaptering device.
- **Status micro-animations:** a red ✕ badge pops onto a tile when something can't do a job (0:57). A green ✓ appears on approval (1:54, 5:04). A progress bar fills under a tile (1:34). A spinner shows while generating (2:33).
- **Branching node graph:** Claude on the left, curved bezier lines draw out to three model tiles on the right, and small "packet" icons travel along the lines (2:08 to 2:16). It's an easy way to show data flowing.
- **Typed prompt bar:** a dark pill-shaped input with white text typing character by character and an accent underline ("Create a 20 second launch video…"). This is how he visualises "what you type."
- **Pricing/usage cards:** a big bold number ("$20", "$100"), a usage bar that fills up and **turns red** when it hits the limit, then the second card highlights and the first greys out (5:14 to 5:25). He shows the numbers as animation instead of saying them aloud.
- **Screen recordings get wrapped.** Real Claude Code and X posts are shown full-canvas with slow zoom/pan, and the important line is highlighted in blue (3:24 to 3:29) like a text selection.

**Motion feel:** slow, eased, never bouncy. Everything is ease-out with a ~300 to 500ms settle; nothing overshoots. Elements fade and scale. There are no whip pans, no glitches, no shakes. Exits are soft fades with a slight blur (1:37, 2:17).

### 3. Theme & colour
- 90% white/off-white canvas, light grey UI chrome, black text, and **exactly one accent** (terracotta red), used only to mean "this one / active / important."
- Product-demo scenes switch to warm cream paper with a serif headline and an *italic accent phrase* ("Catch the thought *in a second*", "Loop finds *the connections*").
- Brand moments flip to near-black with a warm red radial glow behind a serif wordmark.
- The overall look is high-end SaaS launch. The calm contrasts nicely with his energetic delivery.

### 4. Story/structure (8 min)
1. **0:00 to 0:15 cold open:** a 1-second-per-shot montage of the best outputs (calendar UI, cartoon robot, CLAUDE kinetic type). "Here's what you'll be able to make."
2. **Promise plus problem:** "people post these but don't show the details."
3. **Naive attempt vs. good attempt:** shows the bad one-line-prompt result first, then explains why.
4. **Mental model:** "AI doesn't make video, it writes code → screen → frames → video."
5. **Three methods**, each a numbered card chapter.
6. **Recreate a viral example** with the detailed prompt, then **reveal the result full-screen**.
7. **Practical caveats** (pricing/limits) as animated cards.
8. **Second use case** (logo animations, three variants).
9. **Style gallery:** a 2×2 grid cycling through 20 styles. This is the "pause and screenshot" retention trick.
10. **Outro:** subscribe and comments, full-screen A-roll.

Average gap between hard cuts is ~8s. Most of the visual change happens **inside** a scene through elements building, so it feels fast without being choppy.

### 5. Sound
Soft, minimal music bed, voice-forward, with subtle UI clicks/whooshes on element entrances. Loudness sits right at YouTube's −14 LUFS.

---

## B: Hindi creator. "Illustrated docu-promo with kinetic Hinglish type"

### 1. No face cam: voiceover plus a "visual for every sentence"
The creator never appears as a talking head (except as a cut-out avatar at the end). Every sentence gets its own visual, so the screen changes roughly every 1 to 2 seconds even though hard cuts average ~8.7s, because animation happens inside the shot.

Visual sources, mixed freely:
- **Flat vector illustration:** a recurring "confused guy" character (yellow striped shirt, hand on chin, animated "?" marks popping around his head), a yellow stick-figure, a faceless hoodie man with a clock or a white balloon for a head.
- **Mascot:** a glowing magenta blob with eyes and an "A" on its body, standing in for "the Algorithm." It blinks, shifts its eyes, and squints when sceptical (0:52 to 0:57).
- **3D-ish props:** glossy YouTube logo, Shorts phone cards, Instagram + YouTube icons, a 3D clock with circular arrows, a magnifying glass.
- **Real UI screenshots** rebuilt as floating cards: YouTube Studio's "#smallcreator, First 3 days" stat cards, retention graphs, "How viewers engaged" bars, with the key number highlighted in a red box.
- **Movie/meme cutaways:** Money Heist's Professor, a lecture-hall movie scene, Kevin Spacey teaching (5:01). 1 to 2 second reaction shots used as punctuation.
- **Stock B-roll:** a person writing in a notebook (top-down), creators filming with a gimbal, a stressed guy on a phone, reading a book, a highway aerial with HOOK written as a speed bump (3:20 to 3:30, a visual pun).

### 2. Kinetic typography (the signature)
- **Word-by-word reveal of the Hinglish script:** text types in a word at a time synced to the voice, with the upcoming word showing faintly in grey before it lands ("so ek short video ka sabse important part hai-"). It reads as live captions designed as a title card.
- **Keyword slams:** one KEY WORD in huge heavy caps sits above the sentence in a contrasting colour (red **IDEA**, green **HOOK**, magenta **STORY TELLING**, magenta **SHORTS UPLOAD**), often with a two-tone fill.
- **Chapter cards:** "POINT NO.1 / ALGORITHM TIME" in condensed caps under a blue stage-spotlight glow. They enter with heavy motion blur and focus-pull to sharp (0:35, 1:42, 2:57, 4:01). Point 4 uses a light-cone "portal" transition.
- **Circle-badge numbers:** "24 hours", "48 hours", "best perform", "Views 10k → 16k" inside outlined circles hanging from a thin line like a pendulum, swinging in and rotating out. The numbers count up.
- **Strike-throughs:** a yellow slash across the IDEA box (3:10), a red ✕ over a timeline (0:59), "BILKUL NAHI" stamped in red.

### 3. Recurring diagram systems
- **Daily Routine table** (purple glass panel): rows fill in one by one as each step is explained (Idea research 1h → Script 1h → Hook 1h → Voiceover/shooting/editing 1.5h → YouTube Studio 30m). It comes back between sections so the viewer always knows where they are. Use it as a progress map.
- **Skill bars** (gold background): labelled pill bars (Idea Research, Story Telling, Script, Voiceover, Visuals, Sound Design) fill to different levels, then a clock-with-arrows icon slams on top.
- **Bulleted explainer card:** a big header with an underline swoosh ("IDEA RESEARCHING") and ▶ bullets that reveal one at a time, each with its explanation typing in beside it, plus side annotations ("1 YEARS ←" with a hand-drawn curved arrow).
- **Timeline/node lines:** dots joined by a line that turns yellow as it progresses (Shorts upload → 100 people → 300 people).
- **Icon rows:** white circle icons (eye, heart, confused face, speaker) pop in, then a bracket line joins them into "AVD" (3:42 to 3:51).

### 4. Theme & colour
- Each section owns a background colour: **blue** for statements and chapter cards, **purple** for routine and algorithm, **red** for problems and danger ("CHANNEL DEAD", stats), **gold** for skills, **dark grey** for upload mechanics. This colour-coding works as a silent chapter marker.
- Everything glows: vignettes, spotlight cones, neon icons. Very high saturation and contrast, designed to grab attention on mobile.

### 5. Story/structure (6.5 min)
1. **Hook (0:00 to 0:16):** a provocative stat ("PER DAY 1.2 CRORE" shorts uploaded), "Daily 2-3 Shorts!" advice, a sarcastic "CONGRATULATIONS", rats swarming (you're one of millions), then **"CHANNEL DEAD"**.
2. **Proof:** a real channel with 2 months of daily uploads and low views.
3. **Four numbered points:** Algorithm Time → Improvement Time → Skills Importance → The Routine. Each opens with a spotlight chapter card.
4. Each point follows **claim → analogy/visual → proof screenshot → meme reaction**.
5. **Payoff:** a concrete prescription ("Beginner/Intermediate: 2 to 4 shorts per week") plus a visual routine.
6. **End screen:** points to their next video ("Why These Creators Survived YouTube") using a YouTube-card mock.

### 6. How he speaks (from the transcript)
- Conversational **Hinglish**, about 150 wpm. That's slower than A, and it leaves room for the visuals to land. He mixes Hindi sentence structure with English nouns ("algorithm", "retention", "outlier topics", "hook").
- He talks straight to the viewer with **"tum"** and teasing sarcasm ("congratulations, you're running the rat race like 90% of people", "digital kachra", "jhunjhuna bajana").
- **Pre-empts objections in the viewer's voice**: "lekin bro, hamare short pe toh views hi nahi aate, uska kya?" / "theek hai brother, toh kya hafte mein ek short upload karein?" → "Bilkul nahi." This Q→A rhythm drives each section forward.
- **Credibility drop early:** "growing a channel from zero took me 2 months; understanding the algorithm took 2 years."
- **Hard numbers everywhere:** 1 crore shorts a day, tested on 100 → 200 → 500 people, wait 24h before the next upload, 70%+ viewed-vs-swiped, 80%+ AVD, 10 to 20 small creators, 10 hooks per short, 2 to 4 shorts a week. Every number becomes an on-screen badge.
- **Callback-based transition to the end screen:** "and speaking of jhunjhuna, I made a video…".

### 7. Sound
Hot master at −10.9 LUFS. The voice is compressed and up front, with heavy whoosh, impact and pop SFX on every text slam and badge swing. TV-promo energy.

---

## What to take for your 7 to 10 min videos

Use **A's frame as the base and B's storytelling devices on top**: A's layout is sustainable to produce every week, and B's devices hold retention over a long runtime.

**Layout (from A)**
- [ ] Three-state layout: full A-roll for hooks/opinions → canvas + bottom-left rounded PiP (~380px square, ~38px margin, soft shadow) for explaining → full-bleed with no PiP for showcases/demos.
- [ ] Keep a "safe zone": graphics never go under the PiP. Centre all content in the remaining ~75% of the frame.
- [ ] Hard cut between states. Don't animate the PiP.

**Animation vocabulary to build as reusable HyperFrames components**
- [ ] Icon tile plus label, and a "build-a-chain" row that re-centres as items are added (A)
- [ ] Numbered step cards with an active/inactive state, used for chapters (A)
- [ ] ✓ / ✕ / spinner / progress-bar status badges (A)
- [ ] Typed prompt pill (A)
- [ ] Node graph with travelling packets (A)
- [ ] Word-by-word kinetic sentence with a keyword slam above it (B)
- [ ] Spotlight chapter card, "POINT NO.X", with a blur-to-sharp entrance (B)
- [ ] A persistent "progress map" panel that comes back between chapters (B's Daily Routine table)
- [ ] Circle-badge counters for numbers (B)
- [ ] Rebuilt-screenshot stat cards with the key number boxed (B)

**Theme**
- [ ] Choose one: A's calm minimal look (white/cream, one accent, serif headline with an italic accent word) **or** your existing aurora glass look with A's restraint. Use B's per-section background colour as a chapter signal, but keep it subtle: tint the canvas, don't go full neon.

**Pacing & story**
- [ ] Open with a 10 to 15s montage of the payoff (A) or a shocking stat plus a "you're doomed" beat (B).
- [ ] Split the body into 3 to 4 numbered points, each opening on a chapter card.
- [ ] Change something on screen every 1 to 3s inside a scene. Hard cuts can stay ~8s apart.
- [ ] Use 1 to 2s meme/movie reaction cutaways as punctuation, sparingly (copyright risk).
- [ ] End on a gallery/variants payoff (A) or a direct pointer to your next video (B).

**Sound**
- [ ] Master around −14 LUFS (A). B's −11 is louder than YouTube's −14 normalisation target, so YouTube turns it down anyway.
- [ ] Put a soft UI click/whoosh on every element entrance (A), and save heavy impacts for chapter cards and keyword slams only (B).
