# Dev Vora's video editor: Claude Code skills

These are the two Claude Code skills that edit my YouTube videos, Shorts and long-form. I record, drop the files into
Claude Code, and it hands me back a finished first version: cuts, captions, camera moves, animated scenes, sound
effects and music. I watch it, give notes in plain words, and say "save this to the skill". That's why it keeps
getting better: every rule in here came from a real note on a real video.

## Get started

1. Install [Claude Code](https://claude.com/download) and open it in an empty folder for your videos.
2. Paste this repo's link into Claude Code and say:

   > Clone https://github.com/Devvora08/video-editing into this folder so the skills land in `.claude/skills`. Then
   > check everything they need (FFmpeg, Node, Python, HyperFrames, Parakeet, DeepFilterNet), install what's missing,
   > change any machine-specific paths in the skills to fit my computer, and run the tests.

3. Open a **new** thread (skills load when a thread starts).
4. Make a folder per video in `edited_videos/<video-name>/`, put your clips, voiceover and script in it, and say:

   > Edit this short: edited_videos/<video-name>

## What's inside

| Skill | For | What it does |
|---|---|---|
| `.claude/skills/shorts-edit/` | Shorts (9:16, 45 s to 3 min) | Cuts retakes and dead air, word-highlight captions, animated overlays and full-frame explainer scenes, B-roll, camera moves, subtle SFX, a music bed, render and checks. Face cam, face cam + voiceover, or fully animated. |
| `.claude/skills/davinci-edit/` | Long-form (16:9, 5 to 25 min) | **Fully animated from a voiceover** (chapter title cards, progress navbar, per-chapter dark gradients, realistic app UIs, subtitles): no extra software needed. **Footage edits in DaVinci Resolve** (timeline, B-roll, colour, subtitles, render) through the DaVinci Resolve MCP server. |
| `style-study/` | Learning new styles | Notes from breaking down other creators' videos frame by frame. This is how the skills pick up a new look. |

Each skill's `SKILL.md` is the rulebook Claude reads; `scripts/` are the tools it runs.

## Prompts I use

- Edit: `Edit this short: edited_videos/day_5` · `Animate my voiceover into a long video: edited_videos/first_week`
- Notes: `At 0:22 the text is too small. Around 0:14 there's a flash, take it out.`
- Learn: `Save this to the skill.`
- New style: `Here's a Short with a style I like [file or link]. Study it and add that style to the skill.`
- Make it yours: `Here's my style guide. Update the skills to match it.`

## What you need

- Claude Code on a paid plan. Full edits use a lot of usage.
- Free tools Claude installs for you: FFmpeg, Node.js, Python, HyperFrames
  (draws and renders the animations), Parakeet (word-level transcripts), DeepFilterNet (voice clean-up).
- Optional, for long-form footage edits: DaVinci Resolve (Studio for external scripting) and the DaVinci Resolve MCP
  server connected to Claude Code.

## Notes

- The look, handles and examples are mine (devvora.dev). Change `shorts-edit/STYLE-GUIDE.md` and the skills will follow.
- The skills mention reference screenshots (`layout1.png`, `layout2.png`) and a folder of my videos that aren't in this
  repo. Put your own references in your project folder and tell Claude what they are.
- Parts of the scripts started from an MIT-licensed starter kit; its notice is in `LICENSES/` and in
  `shorts-edit/LICENSES/`. Fonts are under the SIL Open Font License. Sound effects are from Pixabay
  (`shorts-edit/assets/sfx/CREDITS.md`). No footage or music ships here.
