# I Only Compile Now (1960 edition)

A fork of [pfrazee/i-dont-code-anymore](https://github.com/pfrazee/i-dont-code-anymore), MIT licensed. The audio is `assets/I-Only-Compile-Now.m4a`: the Suno take plus the a cappella coda. Upstream's original song and files are left in place.

## The idea

The song is the upstream lament sung straight by an IBM 704 programmer in 1960 who has given up hand-coding octal for FORTRAN. FORTRAN was the "automatic programming" of its day. The hand-coders distrusted it just as people distrust AI code generation now. The arrangement is 1950s big-band swing in the Postmodern Jukebox style: a vintage arrangement of a modern song, which is the parody's own joke.

- **What he gives up is not punch cards.** FORTRAN source was punched on cards too. He gives up the hand-punched octal deck, where he chose every machine word himself.
- **The irony loop.** The 2026 singer begs "let me *compile* my hands." In 1960, compiling is what took the craft away, so this singer asks to *assemble* them.
- **Daisy.** In verse 2 he sings "I ask the machine to sing / And Daisy?", and one of the backing singers answers, coyly, "Daisy," before he finishes "is the thing." The machine's song is answered by a woman's voice, which suggests the backing singers *are* the machine singing. The coda says so outright.
- **The coda.** After the band stops, the women sing "I can sing anything now" a cappella, entering one at a time and reluctantly. The voices were generated, so the song turns its own complaint on itself: the musicians are now the ones being replaced. In the video this is a deliberate break from the frame: there is no period colour grade, and the stage is dark.
- **A historical footnote that supports the coda.** In 1961 at Bell Labs, an IBM 7094 (the 704's successor) sang "Daisy Bell". It was the first computer to sing, and it is the song HAL sings in *2001*.

## Period glossary (what the lyrics and sets refer to)

| Term | Meaning |
|---|---|
| Octal, octal groups | 704 machine words were written as 3-bit octal digits |
| Lights concurred | The console indicator lamps |
| Index loops | The 704's index registers |
| A room of tape | IBM 729 tape drives, the four cabinets on stage |
| Stand at the door | The closed shop: programmers handed decks to operators through a window |
| Block time | Booking the whole machine yourself, usually overnight |
| Switches that aren't there | Console sense switches, which programmers could no longer touch |
| The dump | An octal core dump |
| Patching traps | The 704's transfer trapping mode |
| Columns 73–80 | Card sequence numbers. A dropped deck was re-sorted by them, which the inside-the-machine runner does |

## Scenes (upstream → 1960)

| Upstream | 1960 version |
|---|---|
| Opening terminal: build fails | 1403 green-bar listing ending `ERROR 07 JOY NOT DEFINED` |
| Bedroom desk | Office desk, keypunch keyboard, listing on a copy holder |
| TypeScript editor fix | FORTRAN coding form: `TOTLA` → `TOTAL`, deck submitted |
| Build succeeded | Listing ending `EXECUTION COMPLETE` |
| Digital runner | Runner inside the 704: card ledges, tape reel, sequence-numbered deck |
| Singing-head cursor | Head rides the 1403 print position |
| ASCII assembly | Singer assembled from Hollerith punch holes |
| Head hops | Hops between FORTRAN statements |
| Neon club stage | Red-curtain supper club, four 729 tape drives with turning reels, console lamps that fire on the beat |
| Club dance moves | Lindy rock, Charleston, Suzie-Q, Shorty George, kick-ball-change, jazz hands, shoulder shimmy, snap-and-sway, the Twist, tracking turn |

## Lyrics files

| File | What it is |
|---|---|
| `lyrics-1960.txt` | The script given to Suno, with singer tags (`[Male Lead]`, `[Female backing harmonies]`, also inline mid-line). The coda was generated separately (`assets/Outro.wav`). |
| `lyrics-take2.txt` | What take 2 actually sang, used for alignment and captions: one "Remember when", two "assemble"s, the caption "panels' glare", and the coda appended. |
| `lyrics-take1.txt` | The same for take 1, which dropped the second chorus. Kept for reference. |

The singer tags drive lip sync. Each character's mouth opens only on their own lines, because the vocal stem mixes every voice. Backing-only lines outside a chorus bring the two women in from the frame edges, leaning toward the lead. The Daisy exchange is a dedicated two-shot, timed from the aligned "And Daisy?" / "Daisy," / "is the thing." cues.

## Dropping in the new recording

All song timing lives in `data/timeline.json`. Nothing in `src/` hard-codes seconds.

```sh
# 1. Join the song and the coda into the track the video plays.
#    Demucs strips the accompaniment off the coda. The output is assets/I-Only-Compile-Now-full.wav;
#    encode it to assets/I-Only-Compile-Now.m4a, which data/timeline.json "song.audio" points at.
#    (The source WAVs are not in the repo.)
.venv-audio/bin/python src/assemble_audio.py

# 2. Separate the vocals (Demucs, CPU, several minutes), then list the vocal phrases.
.venv-audio/bin/python src/prepare_vocals.py
.venv-audio/bin/python src/vocal_map.py

# 3. Write the rough cues, giving one start per [Section] in the take's lyrics file.
#    If you are unsure what was sung, transcribe the vocal stem first and fix the lyrics copy to match.
.venv/bin/python src/make_cues.py lyrics-take2.txt <one start per section> --end <duration>

# 4. Align the words and build the mouth track. Every word must align; the assert says which section failed.
.venv-audio/bin/python src/align_vocals.py

# 5. Find the drum attacks. For brushes or ride cymbal, lower percussion.prominence/height in
#    timeline.json, and set percussion.mix_downbeats to the first chorus downbeat.
.venv-audio/bin/python src/refine_percussion.py

# 6. Map the whole edit onto the new sections. This writes timeline.json (including coda) and chapters.ffmeta.
.venv/bin/python src/retime.py --cues data/cues.json

# 7. Check, then render.
.venv/bin/python build.py --still 60
.venv/bin/python build.py --workers 3
```

`retime.py` matches sections by name. A section the take skips, such as take 1's missing chorus, collapses out of the edit along with its shots. After step 6, hand-check:
- the intro split (listing vs desk);
- the outro start, which should land just before "But I miss the way I began";
- the chorus camera cuts and the montage cuts. A swing arrangement phrases differently, and the cuts should land on its hits.

Other details:
- Fonts default to the URW faces on Linux. Override them with `IDCA_FONT`, `IDCA_FONT_INDEX`, `IDCA_MONO_FONT` and `IDCA_PRINT_FONT`.
- `IDCA_GRADE=0` turns off the film grade.
