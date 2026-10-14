> **Fork note:** this fork restyles the project into *I Only Compile Now*, a 1960 big-band parody. See [NOTES.md](NOTES.md). The text below describes upstream.

# I Don't Code Anymore

A new low-poly music video derived from the procedural animation and vocal-alignment approach used in **P(doom)! Kaboom!**. This project has its own supplied song, three human performers, a redesigned club stage, and a separate edit. The lead wears a purple hoodie and rectangular glasses; one backing singer is a woman with long dark hair, a white button-down with pens in the pocket, and round glasses; the other wears an argyle sweater vest over a collared shirt. The lead keeps his hoodie and glasses in the desk, digital-avatar, ASCII, and head-only scenes.

The stage uses folded acoustic panels, geometric neon frames, slate flooring, moving light beams, and blue, green, and purple palettes. The opening types a musical-number build command into a fake terminal, prints build messages, and fails. At 0:08 the singer sits at a desk, staring at the same terminal; at 0:14 the performance resumes with his sliding entrance. Starting with the measured beat around 0:53, two colored lighting banks alternate: teal/green and blue/violet, each with ceiling downlights and floor uplights.

At 0:21.5–0:28.4, the lead types a fix in the editor, runs a build, and sees it succeed. At 1:08–1:23, a digitized version of the same human runs through terminals and code editors and restores fallen text. The runner has no following code, fragment trail, parser sparks, or hand-to-code connecting lines. At 1:23–1:32, terminal output uses his singing head as its cursor. Both typing and cursor movement run at half their previous speed, while vocal timing remains unchanged. The singers return to the stage at 1:32; flashing lights remain off until the strong chorus drum downbeat, refined from the isolated drum track to 1:42.92.

At 1:56–2:03.5, colored ASCII characters fly together to assemble the singer inside a terminal. At 2:30–2:36, his head hops between code fragments. Each real drum attack triggers one 0.22-second hop, followed by a complete hold until the next hit. The timing comes from isolated percussion rather than an extrapolated tempo grid; triggers use the nearest output frame (at most 16.7 ms rounding at 30 fps). At 2:45 the bouncing head returns and continues until the existing terminal cut at 2:47.8183. The slower terminal output then stays through 2:52, followed by a singer close-up through 2:54.4348. The remaining stage, coding, successful-build, and stage-wide cuts keep their earlier timing through 3:03. Repeated scenes use the current vocal and lyric timing, and the head holds still during gaps in the drums.

Each chorus stage performance cuts between four moving cameras: an opening orbit, a floor-level upward-looking swoop, a high crane sweep, and a closer arc. Most cuts land on isolated drum attacks; the final floor swoop starts when the bouncing-head insert ends at 2:36. The camera tracks the lead while reprojecting the entire stage and light rig; captions stay fixed. Alternating flashes are strictly limited to the three chorus intervals and stop at the last chorus lyric, including during the later montage. Steady ambient stage lighting remains elsewhere. Both backing singers perform ten full-body dance moves: step-touch, running man, kick-and-point, grapevine cross-steps, robot, body roll, skater lunges, twist, overhead clap, and pivot turn. Each chorus has its own four-beat phrase sequence driven by the measured percussion. Both dancers perform the same moves in the same direction on one shared beat phase. Their steps, arms, body turns, head movements, and phrase transitions match exactly. The formation leaves room for their synchronized travel and wide gestures. Feet remain above the floor through torso leans and crouches. The dancers stay still during the final chorus entrance at 2:28–2:30, resume at the stage return at 2:36, and remain enabled in stage appearances until 2:53. The light gate remains independent of the dance gate, so flashes still stop at the chorus boundary.

At 3:03 the edit returns to the singer sitting at his desk and stays there through the end. He faces the camera and sings “But I miss the way I began” with the existing vocal-driven mouth animation, then looks back toward the monitor. A single slow camera pullback makes him about one tenth of his initial screen height before the final fade.

The edit alternates stage angles with isolated portraits, sliding entrances, a light-frame alcove, split screens, and ensemble shots. The lead holds a microphone and uses articulated gestures. Lyrics stay at the bottom; there are no title banners or lyric illustration cards.

The video is 1920×1080 at 30 fps and runs for the complete 198.76-second song. This repository contains the source code, original inputs, and saved timing data needed to rebuild it. Generated videos, preview images, validation reports, and exported subtitles are excluded.

## Files

- `assets/`: original audio, supplied lyrics, original embedded subtitle track, and checksums.
- `data/`: vocal/character alignment, the 100 Hz two-state mouth track, retimed captions, chapters, and shot list.
- `src/render_video.py`: low-poly character meshes, clothing, expressions, poses, stage geometry, lighting, camera compositions, and the complete edit.
- `src/choreography.py`: ten full-body dance moves, chorus-specific routines, synchronized partner movement, and smooth phrase transitions. `data/choreography.json` records the routine order and timing.
- `src/digital_scenes.py`: the successful coding insert and animated digital running and repair environments.
- `src/terminal_sequences.py`: the singing cursor, ASCII assembly, beat-driven head bounce, and directed montage edit. `data/montage.json` records the generated montage cuts.
- `src/prepare_vocals.py`: local Demucs vocal separation.
- `src/align_vocals.py`: acoustic alignment and mouth-track generation.
- `src/analyze_beats.py`: audio-onset analysis for the alternating light banks, saved in `data/beats.json`.
- `src/refine_percussion.py`: isolated-drum attack detection for the revised lights and head hops, saved in `data/percussion-beats.json`. The original beat grid remains available as a timing reference.
- `build.py`: full rendering, short previews, stills, and audio muxing.

The original embedded subtitles incorrectly place the first vocal near the start of the instrumental introduction and contain a duplicate “No red squiggles in the dark” cue. The original subtitle file is preserved in `assets/`. The alignment input removes that duplicate to match the supplied lyrics; final timing follows the separated vocals, beginning around 14.6 seconds.

## Render

Use Python 3.12, FFmpeg on `PATH`, and macOS's Avenir Next font. The terminal uses macOS Menlo (`IDCA_MONO_FONT` can override its path). The tested lyric font is `/System/Library/Fonts/Avenir Next.ttc`, medium face (index 5). Set `IDCA_FONT` to another copy of that collection if needed. Fonts and model weights are not bundled.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python build.py --still 36.6
python build.py --start 51.9 --end 59 --workers 1
python build.py --workers 3
```

Results go to `renders/` unless `--output-dir` specifies another directory. Scratch audio and intermediate movies go to `work/`; set `IDCA_WORK_DIR` to use a different scratch directory. These generated directories are ignored by Git. Full rendering uses the saved timing data and requires no model downloads.

The video burns in the lyrics and includes chapter navigation. A separate `.srt` is written alongside a complete render.

## Rebuild vocal timing

This optional step downloads pretrained Demucs and Wav2Vec2 weights on the first run and performs the analysis locally. Use a separate environment for the audio-analysis dependencies.

```sh
python3.12 -m venv .venv-audio
source .venv-audio/bin/activate
python -m pip install -r requirements-audio.txt
python src/prepare_vocals.py
python src/align_vocals.py
python src/analyze_beats.py
python src/refine_percussion.py
```

The scripts write new alignment and mouth data to `data/`. Check the new timing before rendering. Chapter metadata and the saved subtitle export correspond to the supplied song; update these too if replacing or re-editing the audio.

## Editing

Change the editor and digital action sequences in `src/digital_scenes.py`; `CUTS` controls their internal transitions. The terminal-head, ASCII and bouncing-head sequences and `montage_cuts()` live in `src/terminal_sequences.py`. The explicit montage cut list keeps the edit identical between render workers and rebuilds. Change `CAST` and `Human` for character design and gestures, `src/choreography.py` for dance moves and chorus routines, `background` and `lighting` for the set, `CAMERAS` for static camera positions, `chorus_camera()` and `CHORUS_CAMERA_CUTS` for the chorus shots, `outro_camera()` for the final pullback, and `SHOTS` plus the time ranges in `render()` for the main edit. Chorus performances override static shot cameras with the current moving shot. The shot-list, chorus-cameras, and montage JSON files are reference exports.

The mouth uses only an open square or a closed line. Its state follows the separated vocal energy, aligned phrase bounds, and consonant closures; it does not use a periodic mouth animation. Backing singers join the choruses.

## License

MIT. See [LICENSE.md](LICENSE.md).
