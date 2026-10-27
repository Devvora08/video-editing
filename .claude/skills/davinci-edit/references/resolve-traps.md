# Resolve MCP traps (measured, from the server's own guides)

Re-read the live guide (`knowledge get <topic>`) when in doubt: the server's notes are newer than this list.

| Trap | What happens | Do instead |
|---|---|---|
| Source vs record frames | plan `keep_ranges` are SOURCE frames (end exclusive); `structural_diff` in/out are RECORD frames. Mixing them places every clip at the wrong moment of the right file, silently | place one range, read back with `timeline clip_where`, then batch |
| WAV source rate | a WAV takes the project's frame rate at import; source frames of audio items are counted in that rate, which may differ from the timeline's | always read `source_fps` from `probe_timeline_structure`; never assume |
| Retime | clip speed / retime is absent on every build | FFmpeg-made slow motion / ramp, imported as a new clip |
| Audio levels | Volume / Pan / EQ writes on timeline audio are ignored (`known_limitation`) | bake levels and ducking into the WAV; Fairlight presets (20.2.2+) only apply a whole saved mix |
| Fusion at render | a script-built comp rendered on 19.1.3 but was ignored at render on Studio 21.0.4 | animate in HyperFrames; prove any Fusion effect on a rendered frame |
| Thumbnails | contact sheets and pool thumbnails decode source media: no grade, no Fusion | `gallery_stills grab_and_export` (Color page) or a frame from the render |
| `apply_grade_from_drx` | replaces the whole node graph; defaults to video track 1 item 0, not the current clip | `timeline_item_color.safe_apply_drx` with explicit track/item, backup still first |
| Render "Complete" | a job can report Complete for a near-empty stub, and its own mark range is rewritten | `render verify_output` with the expected duration, before deleting the job |
| StartRendering on 21.1 | a fresh job can return False and stay Ready | read the job status and the output; do not assume |
| Subtitle render settings | `ExportSubtitle` / `SubtitleFormat` returned True and did nothing before 21 | check the rendered file for the burn-in or sidecar |
| `hasattr` probing | true for any name on a Resolve object | use the MCP's `check_version_support` / `get_version` |
| Closing mid-render | orphans the render and wedges Resolve until restart | `project_manager close` refuses during a render; stop it first |
| `move_clips` to open a gap | can delete sources whose duplicate failed to land | `ripple_insert` (dry run, confirm token) |
| `ripple_insert` side effects | shifted items lose grades, keyframes, transitions and links | insert before grading and camera work, or redo those after |
