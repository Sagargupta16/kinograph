# Engine

What a `scenes.py` must do, how a working folder is set up, what every file in [engine/](../engine/) is for, what the three stages of `run_all.py` run and print, how frames reach ffmpeg, which files a build leaves behind, how the sound is made, and the encode ladder for an ffmpeg without libx264. The builder reads this before it writes `scenes.py`; the main chat comes here for the fallback encode commands.

Every fact below is read from the code (the function or constant is named) or comes from runs made on 2026-11-01 on Windows 11 with uv 0.13.6, Python 3.15.2, Pillow 13.0.0, numpy 2.5.4 and ffmpeg 9.0.2. What the Q codes mean and what they hold a build to is in [qa-gates.md](qa-gates.md); the score and the master in [sound.md](sound.md); narration in [voice.md](voice.md); what an error means in [troubleshooting.md](troubleshooting.md).

In the commands below, `python` stands for `uv run --no-project --with-requirements requirements.txt python`, run from the working folder. Each command was run once that way, in bash, on 2026-11-01.

## The contract: each frame is a function of time

`draw(t)` takes a time in seconds and returns the frame the film shows then: a PIL image of exactly `W x H`. The template ends every draw with `finish(img)`, which scales a supersampled canvas down (Lanczos) and converts it to RGB. The render checks every frame's size and stops at the first wrong one (`render.checked`): in a raw pipe, one frame of another size shears every frame after it.

`draw(t)` must be pure and deterministic. The same `t` gives the same pixels whatever was drawn before it, in whichever process, in whichever order. This is not style: the render draws frames out of order in a pool of fresh processes, the purity gate and the text recorder draw single frames on their own, and `qa.py approve` and `run_all.py audio` draw key frames again and compare them with the render. In practice:

- Carry no state from one call to the next. A cache is fine when it holds only what a pure function would give anyway, such as a font or a background built once at import.
- Read no clock, no process id and no unseeded random source. For randomness use `rng(*keys)` from `engine.py`. It returns a numpy Generator seeded from the keys: strings go through crc32, whole numbers from 0 to 2**32 - 1 are used as they are, and the number of keys leads the seed. Seed each element from its own keys, for example `rng("dust", i, frame_of(t, FPS))`, and never advance one stream frame after frame. A float key raises TypeError, so pass `frame_of(t, FPS)`, not `t`. Sounds have their own seeding, `synth.rng_for(name, *args)`.
- Take every time from one declaration: `TIMELINE`, compiled by `compile_schedule` into `SCHEDULE`, `DURATION`, `CUTS`, `WINDOWS` and `CUES` (see below). A hand-written `SCHEDULE = {name: (start, end)}` with a `DURATION` still works; the engine then takes the cuts from every scene start after 0.

What enforces it, all in the proof stage (codes in [qa-gates.md](qa-gates.md)):

- The purity gate, Q1201 (FIX): frames at the ends, both sides of the cuts, cues, key times and an even spread are hashed in order in this process, in reverse order in a fresh `python -I` process, and through a spawn pool, and must match exactly. On the template that was 24 frames.
- The lint of `scenes.py` and the local modules it imports: Q1202 (FIX) for unseeded randomness, clock reads and hashes of strings; Q1203 to Q1206 (NOTE) for module state written inside a function, an engine helper defined again, text drawn outside the engine's text helpers and a colour literal outside the palette block; Q904 and Q905 (NOTE) for a time off the frame grid and a beat that is not a whole number of frames. A finding that is meant is silenced with a pragma comment on its line: `# praxinoscope: rng-ok`, `state-ok`, `shadow-ok`, `text-ok` or `colour-ok`.

### The names a scenes.py declares

| Name | When | Read by |
|---|---|---|
| `draw(t)` | always | the render, the proof sheets, every gate that draws |
| `SCHEDULE`, `DURATION` | always | the frame count (`frame_of(DURATION, FPS)`), the proof sheets, the score, the gates |
| `CUTS`, `WINDOWS`, `CUES` | made by `compile_schedule`; `CUES` may be extended | the score (one hit per cut, labelled from `CUES`), the key sheet, Q901, Q902 |
| `text_items(t)`, or `NO_TEXT` | one of the two | the text gates and the text recorder |
| `NO_CUES` | a piece with no shared sound and picture moment | Q902 |
| `BPM` | music pieces | the template score's tempo (120 when absent), Q901, Q905, the Gantt strip |
| `KEY_TIMES` | optional | the key sheet |
| `CUE_LAG` | optional, in frames | the picture side of Q902, the hard-cut scan |
| `STATIC` | optional | the render (see Held frames) |
| `BUDGET_MB` | optional | the bitrate cap and Q1001 |
| `SILENT` | optional | the mux (no audio track), the audio gates |
| `ALLOW` | optional | the NOTE-level scans |
| `HOLD_PROFILE` | optional | Q401 |

## Setting up a working folder

```
cp -r <skill>/engine/. <working folder>/
```

The `/.` copies everything inside `engine/`, hidden files and folders included, so `.python-version` and `qa_fixtures/` (which `qa.py selftest` needs) come along. An `engine/*` glob would leave the hidden `.python-version` behind.

Run every script from the working folder as `uv run --no-project --with-requirements requirements.txt python <script>`. `--no-project` stops uv from looking for a project file. uv takes the interpreter from `.python-version` in the folder it runs in: a scratch folder whose `.python-version` said 3.14 ran Python 3.14.9. It then runs on the hashed pins of `requirements.txt`. So a proof and its render in one folder always run on the same Python, Pillow and numpy.

| Pin file | What it holds |
|---|---|
| `.python-version` | `3.15` |
| `requirements.in` | `pillow==13.0.0` and `numpy==2.5.4` |
| `requirements.txt` | the same two, compiled with their sha256 hashes |
| `requirements-voice.in` | the optional text-to-speech pins; nothing installs this file (see the table of files) |

`bash <skill>/setup.sh` checks the machine and installs nothing system-wide; its first uv run may fetch the pinned Python and wheels into uv's cache. On 2026-11-01 it found uv 0.13.6, an ffmpeg 9.0.2 build that has libx264, ffprobe, Python 3.15.2 with Pillow 13.0.0 and numpy 2.5.4 from the pins, and Arial Bold as the default bold font, and ended `SETUP: PASS` with exit code 0.

## The files in engine/

| File | What it does |
|---|---|
| `engine.py` | The toolkit `scenes.py` star-imports: `W`, `H`, `FPS` and `SS`; the frame clock re-exported from `contract.py` (`frame_of`, `snap`, `stepped`, `on_grid`, `sample_of`, `frame_sample`); easing (`prog`, `lerp`, `linear`, the cubic eases, `ease_out_expo`, `ease_out_back`, `spring`, `settle_time`); fonts (`font`, with the search lists `FONT_BOLD` and `FONT_REG`: Arial, Helvetica, Liberation Sans, then DejaVu Sans); `hexrgb` and `rng`; layers (`canvas`, `gradient`, `rrect`, `shadow`); text (`text`, `text_outline`, `text_halo`, `text_box`, `text_w`, `fit_size`, `wrap`); `finish`; scene lookup (`scene_at`, `scenes_at`, `crossfade`); and declared timing (`Scene`, `Transition`, `Timeline`, `compile_schedule`) |
| `contract.py` | What every module shares; it imports neither `scenes` nor `engine`, so anything can import it first. The frame and sample clock; the QA row (`Row`, `row`, `summary`, `line`, `exit_code`); the names of the build files and their readers and writers; frame digests and grey thumbs; the colour chain (`COLOR_VF`, `COLOR_FLAGS`, `DECODE_709`, `DECODE_LINEAR`); `AAC_ARGS` and `mux_cmd`; `CODES`, the table of every Q code and its owner module; `find_ffmpeg`; and `Ctx`, the decoded file that each gate module reads |
| `run_all.py` | The three stages, `proof`, `full` and `audio`. It holds `OUT` (the deliverable's name, `out.mp4` until you rename it), `CRF = 18` and the true-peak loop constants |
| `render.py` | Draws frames in a process pool into a shared-memory ring and pipes them in order into one libx264 encode (`render_to_ffmpeg`, `encode_cmd`); PNG frames in parallel (`render_parallel`) or in one process (`render_frames`); `static_reuse` for held spans; `stale` to compare frames with `frames.hash` |
| `scenes.py` | The template video, and the shape every video's `scenes.py` keeps |
| `transitions.py` | Nine pure transitions `f(a, b, p)` in `MENU` (crossfade, wipe, push, slide, iris, clock, blinds, dip, luma), each tagged with `flash_risk` |
| `grain.py` | `grain(img, t, std=1.6, hz=None, tiles=4, seed=0)`: film grain cut from four seeded 256 px tiles, stepped at fps / 2 unless `hz` is given, pure in t |
| `audio.py` | The template score (`bed`, `render_audio`) at 44.1 kHz, the WAV writer (`write_wav`) and the master: a static gain to -14 LUFS and a 4x oversampled true-peak limiter (`master`, `true_peak`, `tp_limit`, `measure`), which reports Q805 |
| `synth.py` | numpy instruments (kick, snare, hat, clap, bass, pad, pluck, riser, boom, whoosh, tick), `reverb` and `duck`; `landmarks`, which finds the instant of a sound that should sit on its event; `place`, `put` and `put_peak`, the one way sounds go into a bus; and the cue sheet (`recording`, `CueSheet`). `python synth.py out.wav` writes a 4 s demo |
| `voice.py` | Offline narration: `synthesize` (one cached file per line, then `narration.wav` and `narration.json`), `load_narration`, `word_cue`, `onset_offsets`, `dec`, `span`, `trim`, `slot`, `section_beats` and `duck_mix`, with four engines in `ENGINES` (sapi, kokoro, kokoro-ts, piper) |
| `voice_samples.py` | Speaks three fixed lines with every voice engine that is ready, into `narration_samples/<engine>/<voice>/narration.wav`, so the user can choose by ear |
| `proof.py` | The review sheets: `proof.png`, `proof_keys.png` (paged as `proof_keys_2.png` and on), `proof_strips.png` and `proof_gantt.png`. `python proof.py keys` redraws the last three from `review_times.json` |
| `kit_index.py` | The helper index: every public top-level function, class and namedtuple a scene builder may call, with its signature, the first line of its docstring and file:line. It leaves out `scenes.py`, `run_all.py`, `proof.py`, `render.py`, `contract.py`, itself and the `qa_*` modules, and reads the files with `ast` without importing them. `python kit_index.py` listed 144 helpers; `python kit_index.py show engine.py:rng` printed that function's source |
| `qa.py` | The gate CLI: `check`, `look` and `holds`, plus the subcommands the modules below add. The gates it measures itself: the text gates 2 to 4 on the registry, frame 0 and the last frame (gate 5), the file's format and colour (gate 7), loudness and silence (gate 8), the beat grid (gate 9) and size and bitrate (gate 10) |
| `qa_scan.py` | Flashes (Q601 to Q603), the reviewer's pointer scans (Q1101 to Q1104, on the decode and on `thumbs.npy`) and Q1105, the file against the drawn frames |
| `qa_stack.py` | Q802 (true peak, with the sounds stacked there) and Q804 (the stack guard), from the cue sheet and the decode |
| `qa_sync.py` | Q902 (cue sync, found on `sfx.wav`), Q903 (the mux) and Q906, with `qa.py calib` |
| `qa_registry.py` | The text recorder: what `draw(t)` paints against what `text_items(t)` reports (Q204 to Q206, Q208, Q209) |
| `qa_approve.py` | `qa.py approve`, `qa.py diff` and `qa.py verify`, and Q1301 to Q1304 |
| `qa_purity.py` | Q1201 and `qa.py purity` |
| `qa_lint.py` | Q1202 to Q1206, Q904 and Q905; `qa.py lint`, and `qa.py owner`, which names the scene function that owns a time or a traceback |
| `qa_audiostrip.py` | `qa.py audiostrip`: `review/audio.png`, the sound drawn for a reviewer who cannot hear it |
| `qa_selftest.py` | `qa.py selftest`: every gate against planted faults, plus the template at 1920x1080 and 1080x1920. On 2026-11-01 it ended `SELFTEST: PASS (147 fixtures, 58 of 58 codes covered, 0 expected gaps)` in 55.5 s |
| `qa_fixtures/` | The cases selftest runs: seven case modules (text, registry, source, files, sound, scans, approval), two shared makers (`fake.py`, `media.py`) and small scenes files that each plant one fault or serve as a clean control. Media are made at run time in temporary folders; nothing is downloaded |
| `requirements.txt` | Pillow and numpy pinned with hashes; the only packages the engine imports outside the standard library |
| `requirements.in` | The two pins `requirements.txt` is compiled from |
| `requirements-voice.in` | The pins of the optional voice engines. `setup.sh` does not install it and it is not hashed; `voice.py` runs each engine in its own uv environment with the same pins, so `requirements.txt` stays Pillow and numpy |
| `.python-version` | The Python version every copy of the engine runs on (3.15), read by uv in the working folder |

## Frame size, frame rate and supersampling

Every stage takes `--size WxH` (default 1920x1080), `--fps N` (default 30) and `--ss N` (default 1). With `--ss 2` each frame is drawn at twice the width and height and `finish()` brings it down. A run at 640x360 with `--ss 2` passed every gate and recorded `"ss": 2`. Sizes per aspect, safe areas and frame rates are in [formats.md](formats.md).

`run_all.py` reads the three flags at the very top of the file (`size_flags`, which ignores every other argument) and only then imports `scenes`. The order matters because `scenes.py` reads `W`, `H`, `FPS` and `SS` once, when it is imported (`from engine import *` copies them), and lays everything out from them. It matters again in the render. The pool starts fresh spawned processes; each one runs the top of `run_all.py` again with the same arguments, and `render._start` sets the size before it imports `scenes` too. This is why the stage code sits under `if __name__ == "__main__":`, and why any script of your own that starts a pool needs the same guard.

A `scenes.py` can fix its own size: assign `engine.W` and `engine.H` (or `FPS`, `SS`) after `import engine` and before `from engine import *`. It then wins over the flags, and the stage says so: `note: scenes.py sets 640x360 at 30 fps, SS 1 itself, which wins over --size, --fps and --ss` (seen when `--size 1920x1080` was passed).

After `scenes` is imported, every stage writes `build.json`, `{"w", "h", "fps", "ss"}`: the size the build really uses, once `scenes.py` has had its say. It is written there, not at the top of the file, because every render worker runs the top again. The standalone tools read it: `qa.py check` (only SS; the size and rate come from the file itself), `qa.py purity`, `lint` and `owner`, `qa.py approve` and `diff`, and `python proof.py keys`. Each falls back on `frames.hash` when there is no `build.json`. Pass the same flags to every stage of one build: the audio stage refuses a picture rendered at another size.

## Writing scenes.py from the template

The template is 8 s at 120 BPM: a title (2 s), one point (3 s) and an end card (3 s), with hard cuts at 2 s and 5 s and a cue on each. Every position is a share of `W` and `H` and every size a share of `min(W, H)`, so one file draws 16:9 and 9:16 alike. On 2026-11-01 it passed `run_all.py proof` (23 checks) and `run_all.py full` (49 checks, one DELIVERED line) at 1920x1080, 1080x1920 and 640x360.

Replace for each video:

- the palette block (`TEAL` to `SHADE`) and `GROUND`, with the style card's colours, used by name only;
- every placeholder in `COPY`, word for word from the storyboard;
- `PLACES`: where each text sits, its size as a share of the short side, its colour and its delay;
- `TIMELINE` (scenes, lengths, transitions and cues), `BPM` and `KEY_TIMES`;
- the drawing in `paint`, `drift` and `underline`, and the motion timings `ENTER`, `EXIT` and `SLIDE`.

Keep:

- `from engine import *` at the top and the palette at module level;
- the line `SCHEDULE, DURATION, CUTS, WINDOWS, CUES = compile_schedule(TIMELINE)`; add `bpm=BPM` to give the lengths in beats;
- one layout function that both `draw` and `text_items` read (the template's `placed(name, lt)`), so the registry cannot drift from the picture;
- `shares(t)`, the scenes on screen with their weights, used by both `draw` and `text_items`;
- `text_items(t)` returning one dict per text, with `s`, `box` (from `text_box` with the same arguments as the draw), `fg`, `alpha`, `px` and `bold`;
- `draw(t)` ending in `finish(...)`;
- a first scene fully in place on frame 0 and a last scene that never leaves: the template's `motion` skips the entrance of a scene that starts at 0 and the exit of one that ends at `DURATION`.

### Scene, Transition and compile_schedule

`Scene(name, dur, cues=())`. `dur` is a number, or a function that returns one (`lambda: max(2.0, narration_s)`), in seconds, or in beats when `compile_schedule` is given `bpm`. `cues` is a list of `(t, label)` or `(t, label, kind)`, a list of dicts, or one dict `{label: t}`. Cue times count from the scene's first drawn frame; kind is `"both"` (the default), `"audio"` or `"picture"`.

`Transition(kind, dur, split=0.5)` is a window between the scenes on either side of it. `kind` is a name for your own draw code (the `transitions.py` names), `dur` is in seconds or beats, and `split` is the share of the window that lies before the cut: 0.5 centres it on the cut and 0 starts it there.

`compile_schedule(items, mode="straddle", bpm=None, fps=None)` returns `Timeline(schedule, duration, cuts, windows, cues)`; `fps` defaults to `engine.FPS`. In `"straddle"` mode the scenes run cut to cut, so `DURATION` is their sum, and a window spans its cut with both scenes drawn inside it. In `"overlap"` mode each scene after the first starts the transition's `dur` before the previous one ends, so `DURATION` loses every transition, and the cut sits `split` of the way into the overlap. A plain tuple such as `("intro", 2)` is read as a Scene. Results at 30 fps:

| Items | Mode | SCHEDULE (s) | DURATION | CUTS | WINDOWS |
|---|---|---|---|---|---|
| `Scene("a", 2)`, `Transition("crossfade", 0.5)`, `Scene("b", 2)` | straddle | a 0 to 2.267, b 1.767 to 4.0 | 4.0 | 2.0 | 1.767 to 2.267 |
| the same | overlap | a 0 to 2.0, b 1.5 to 3.5 | 3.5 | 1.767 | 1.5 to 2.0 |
| `Scene("a", 4)`, `Scene("b", 6)` with `bpm=120` | straddle | a 0 to 2.0, b 2.0 to 5.0 | 5.0 | 2.0 | none |
| `Scene("a", lambda: max(2.0, 1.234))`, `Scene("b", 5 / 30)` | straddle | a 0 to 2.0, b 2.0 to 2.167 | 2.167 | 2.0 | none |

How the numbers are made: each length becomes an exact fraction (`_exact`: ints and Fractions as they are, any other number as its nearest fraction with a denominator up to 10**6, so 0.1 reads as 1/10 and 5 / 30 as 1/6), is multiplied by the frames per unit (fps, or 60 x fps / bpm), and is summed exactly. Each instant is then rounded once to its nearest frame, halves up, as `frame_of` does. So `5 / 30` s is exactly 5 frames. A 0.5 s window centred on a cut at frame 60 spans frames 52.5 to 67.5, which round to 53 and 68; that is why the outgoing scene above is drawn to 2.267 s.

A cue at 0 lands on its scene's first drawn frame. For a scene entered through a window, that is the window's start, not the cut: scene b's cue at 0 behind the 0.5 s crossfade above landed at 1.767 s. A sound meant for the cut itself goes on the outgoing scene at the cut time with kind `"audio"`: `Scene("a", 2, cues=[(2.0, "cut", "audio")])` gave a cue at 2.0 s. A cut inside a window has no hard picture change, so kind `"audio"` is the honest one.

Every error `compile_schedule` raises is a ValueError. The forms below are real messages:

| Cause | Message |
|---|---|
| an unknown mode | `mode 'cut': use "straddle" or "overlap"` |
| a Transition first, or two in a row | `Transition(kind='crossfade', dur=0.2, split=0.5) must sit between two scenes` |
| no scene, or a Transition last | `a timeline needs a scene and must not end on a Transition` |
| a name used twice | `scene 'a' is declared twice` |
| a length of 0 or less | `scene 'a' lasts 0 s: it must be over 0` |
| a split outside 0 to 1 | `Transition(kind='x', dur=0.2, split=1.5): split must be 0 to 1` |
| a window under 2 frames | `'x' transition of 0.05 s (1.5 frames) between 'a' (1.000 s) and 'b' (1.000 s) is under 2 frames at 30 fps, so no frame of it is blended: make it at least 0.067 s, or use a hard cut` |
| a window over half the shorter scene | `'x' transition of 0.6 s (18.0 frames) between 'a' (1.000 s) and 'b' (3.000 s) is over half the shorter scene, 'a' (0.500 s): shorten it or lengthen 'a'` |
| a scene that rounds to no frame | `scene 'b' lasts 0.01 s (0.30 frames) and rounds to no frame at 30 fps: lengthen it to at least one frame or drop it` |
| a cue off its scene's frames | `cue 'end' at 1 s does not land on a frame of scene 'a' (0 to 0.966667 s); a cue at the scene's end belongs to the next scene at 0` |

### Drawing inside a transition window

`scenes_at(t, SCHEDULE)` returns `([(name, local_t, k), ...], mix)`. Outside a window that is one scene and a mix of 0. Inside one it is the outgoing scene, then the incoming one, and a mix that is 0 on the window's first frame and grows from there; at the cut in the table above it read 0.467. `local_t` counts from each scene's first drawn frame, and `k` runs from 0 to 1 over the scene's drawn span. `scene_at` answers the outgoing scene inside a window. Both decide on whole frames, through `frame_of`.

The template's `shares(t)` turns that into the weights `[1 - mix, mix]`. `draw` blends the two pictures with `engine.crossfade`, and `text_items` multiplies each text's alpha by its scene's weight. For another kind, `import transitions` and call `transitions.MENU[kind](a, b, p)`, or a named one such as `transitions.wipe(a, b, ease_in_out_cubic(mix), direction="left")`. Every transition is pure: p = 0 returns a, p = 1 returns b, the inputs are never changed, and both frames must share one size and mode. Ease p yourself, and give `text_items` the same weights `draw` uses. `dip` carries `flash_risk = "check"`: run `qa.flash_window(draw, t0, t1, fps=FPS)` over its window before the render. Each transition's arguments are listed in [craft.md](craft.md).

### Voiced pieces

Run `voice.synthesize` once, before the proof, from a small script in the working folder. `scenes.py` never calls it: every render worker and every gate that draws imports `scenes.py`, so a call there would run on every import and rewrite the narration files each time. `scenes.py` reads the result instead, `voice.load_narration("narration/narration.json")`, and takes each scene's `dur` from its line's `slot["duration"]`. A word that carries a cue comes from `voice.word_cue(...)`, put on the frame grid with `snap(t, FPS)`. The engines, the downloads and the word clock are in [voice.md](voice.md).

### Music pieces

Give lengths in beats with `compile_schedule(TIMELINE, bpm=BPM)`. At 30 fps one beat at 120 BPM is 15 frames. A tempo whose beat is not a whole number of frames still compiles, since each instant rounds once, and Q905 notes it (`contract.whole_frame_beat`). `BPM` also sets the template score's tempo and the grid Q901 holds the cuts to.

### Held frames: STATIC

`STATIC = [(t0, t1), ...]` in seconds, end exclusive like `SCHEDULE`, asks the render to draw a hold once (`render.static_reuse`). It first draws sample frames of the span: both ends, the middle and about one a second, at most six of those (`hold_samples`). If all their digests match, every later frame of the span reuses the first frame's bytes. If one differs, the whole span is drawn and a warning names the first frame that moved. Spans under 2 frames are skipped. A change that falls between samples is not seen, so declare only frames that truly hold. `--keep-frames` turns STATIC off.

On 2026-11-01 the template's end card, whose shapes drift, gave `warning: STATIC (5, 8) s moves (frame 180 differs from frame 150): every frame of it is drawn`. With the drift stopped in a scratch copy, `STATIC = [(6.0, 8.0)]` gave `STATIC: 59 of 240 frames reuse a held frame`, and the build still passed every gate.

### Springs

`spring(t, stiffness=100, damping=10, mass=1)` is the 0 to 1 position of a spring released from rest t seconds ago: Remotion's spring, in closed form. Damping under `2 * sqrt(stiffness * mass)` overshoots and settles; at or above it the spring moves critically damped. It is 0 for t <= 0 and raises ValueError for a damping of 0 or less. `settle_time(stiffness, damping, mass, fps=None, threshold=0.005)` gives the seconds until the spring is at rest: the first frame within 0.005 of 1, pushed past any frame outside that band in the next 20 frames. `fps` defaults to `engine.FPS`; a spring not at rest within 10 minutes raises ValueError. At 30 fps the default spring peaked at 1.163 and settled in 0.933 s, and (100, 200, 1) settled in 0.767 s. Report a springing text as at rest only from `settle_time` on. Tables of springs and eases are in [craft.md](craft.md).

## The stages

| Stage | Command | Needs | Ends with |
|---|---|---|---|
| proof | `python run_all.py proof --size 1920x1080` | no ffmpeg | a `PROOF:` line |
| full | `python run_all.py full --size 1920x1080` | ffmpeg with libx264 | an `APPROVAL:` line and one `DELIVERED` line, or a `REJECTED` or `UNCHECKED` line |
| audio | `python run_all.py audio --size 1920x1080` | `video.mp4` from `full`, with the same flags | the same as full |

Every stage writes `build.json` once its refusals are past; the proof has none. Both stages that need ffmpeg look for it on PATH, then in `/opt/homebrew/bin` and `/usr/local/bin`. A folder found that way is put on PATH, so the gates' own ffmpeg and ffprobe calls find it too. With none at all they print `NO_FFMPEG: no ffmpeg on this machine. Every rung of the encode ladder needs one: install an ffmpeg with libx264, then check it with setup.sh` and exit 1, leaving the folder as it was (seen with ffmpeg taken off PATH).

### proof

It runs the gates that need no file: `qa.proof_rows` (Q501 on frame 0, the text gates on the registry and the text recorder), `qa_purity.run` (Q1201) and `qa_lint.run("scenes.py")`. It writes their rows to `qa_proof.json`. Then it draws `proof.png` (up to 12 stills: scene middles first, then window edges, then scene bounds; 9 on the template) and starts `review_times.json` afresh with this proof's moments, carrying over only the `changed` entries `qa.py diff` left (they stay until the next diff). From it the stage draws `proof_keys.png` (with more pages when the cells do not fit), `proof_strips.png` (frames f-2 to f+2, only when an entry asks for a strip) and `proof_gantt.png`. It prints every row and the summary, and exits 0 when all pass, 1 on any FIX, and 2 on a NOT CHECKED with no FIX. A `draw(t)` that raises stops the stage with its traceback before any row is printed, since the text gates draw first and are not guarded ([troubleshooting.md](troubleshooting.md)). On the template the stage took 10 s at 1920x1080.

### full

`python run_all.py full [procs] --size WxH --fps N --ss N`, with these options:

- `procs`: render processes; the default is a quarter of the logical CPUs, at most 8 (8 on a 32-thread machine);
- `--budget-mb N` (or `BUDGET_MB` in `scenes.py`): a bitrate cap from a size budget (`run_all.caps`; the formula is in [formats.md](formats.md)). `python run_all.py full 2 --size 640x360 --budget-mb 2` printed `size budget 2 MB for 8 s: maxrate 1580 kb/s, bufsize 1580 kb/s (a cap, not a guarantee: Q1001 checks the file)`. Its Q1001 row then said `(cap 2 MB, from --max-mb)`, because the budget reaches `qa.check` as `max_mb`;
- `--keep-frames`: every frame is also kept as PNG in `frames/`;
- `--redraw T0-T1[,T0-T1]`: only with `--keep-frames`; it draws those passages again and reads the rest back from `frames/`. Without `--keep-frames` the stage stops with `--redraw needs --keep-frames (and frames/ from an earlier --keep-frames run)` (exit 2).

Once its refusals are past (no ffmpeg, or a size budget too small for the audio), it deletes `mix_raw.wav`, `sfx.wav`, `cuesheet.json`, `cue_sounds.npz`, `mix.wav`, `OUT`, `video.mp4`, `video.mp4.log`, `frames.hash`, `thumbs.npy` and every `*.rejected.mp4` and `*.unchecked.mp4`, so a failed run never leaves an older file to be reviewed. `frames/` is left alone; `--keep-frames` without `--redraw` empties it.

Then it renders the picture into `video.mp4` (see the next section) and delivers:

1. The sound: with `SILENT` declared, the picture is muxed with no audio; otherwise `audio.render_audio`, then the master and mux loop (see Sound in a build).
2. Q1101 to Q1104 on `thumbs.npy`, every drawn frame before the encode (`qa_scan.scan_thumbs`).
3. `qa.check` on `OUT` with the build folder as `--scenes`: every gate on the file.
4. The approval rows (Q1301 to Q1304) are set apart. They describe the review state, not the file, so they never reject it.
5. Every other row is printed, then the `QA:` summary. Any FIX or NOT CHECKED row moves the file to `<name>.rejected.mp4`.
6. The moment of every row that did not pass goes into `review_times.json`, and `proof_keys.png`, `proof_strips.png` and `proof_gantt.png` are drawn again with those rows.
7. A clean run prints the `APPROVAL:` line and one `DELIVERED` line.

The `QA:` line counts 49 rows on the template. Run alone, `qa.py check` counts 44 on the same file: it adds no Q805 row and no thumbs scans. At 1920x1080 the template's full stage took 17 s.

### audio

It makes the sound again, then masters, muxes and runs every gate on the `video.mp4` already there, without drawing the film. It refuses, with exit code 1:

- when there is no `video.mp4`: `` no video.mp4 here: run `run_all.py full` first ``;
- when the picture no longer matches the flags or the source (`picture_is_current`). Either `frames.hash` records another size, rate, SS or frame count (`video.mp4 was rendered at 640x360, 30 fps, SS 1, 240 frames; this run is 1920x1080, 30 fps, SS 1, 240 frames: pass the same --size, --fps and --ss, or run run_all.py full`), or up to 12 frames, the first, middle and last of every `SCHEDULE` span, drawn again do not hash as `frames.hash` says (from the code: `video.mp4 predates scenes.py: frame <i> (<t> s) and <n> more of <m> checked differ from frames.hash (or its size, fps, SS or length): run run_all.py full`).

Both refusals come before the clean-up and before `build.json` is written, so a refused run leaves the last build as it was. On 2026-11-01 an audio run at 1920x1080 on a 640x360 build was refused and left `out.mp4`, `mix.wav`, `mix_raw.wav`, `video.mp4`, `frames.hash`, `thumbs.npy` and `build.json` byte for byte the same; `python run_all.py audio --size 640x360` then ended with a DELIVERED line.

### The lines a stage prints

| Line | When | Form (real lines from 2026-11-01 unless marked) |
|---|---|---|
| `PROOF:` | end of proof | `PROOF: PASS (23 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)`; otherwise `PROOF: FIX (n) (...)` or `PROOF: NOT CHECKED (n) (...)` (`contract.summary`) |
| `master:` | the first master | `master: ceiling -2.00 dBTP, mix.wav -14.0 LUFS at -2.00 dBTP (Q805 PASS) -> out.mp4 -14.1 LUFS at -1.80 dBTP` |
| `re-master k of 3:` | out.mp4's true peak over -1.3 dBTP | the same shape with the lower ceiling (from the code; not seen on the template). It may be followed by `kept the cleanest master: ...` or `kept the least limited master: ...`, by a `note:` when the peak ends inside -1 dBTP but within 0.3 dB of it, by `true peak still over -1 dBTP after N re-masters: lower the hits Q802 names`, or by `the file's peak did not follow the ceiling (...): no lower ceiling will help` |
| `QA:` | after every gate | `QA: PASS (49 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)`; with a planted fault, `QA: FIX (1) (49 checks, 1 FIX, 0 NOTE, 0 NOT CHECKED)` |
| `APPROVAL:` | a clean run | `APPROVAL: none yet -> final review, then qa.py approve`; with an approval, `APPROVAL: current -> ...` or `APPROVAL: stale: <code> <item> -> re-review the changed scenes, then qa.py approve` (from the code). A stale approval does not stop delivery; each approval row is also printed as `approval <state>: <code> <message>` |
| `DELIVERED` | a clean run, last line | `DELIVERED <working folder>/out.mp4 (0.4 MB, 8.00 s, -14.1 LUFS, -1.8 dBTP)`, with the absolute path; a silent piece shows `silent` in place of the loudness. Exit 0 |
| `REJECTED` | any FIX or NOT CHECKED row | `REJECTED out.rejected.mp4: Q502 FIX` (a planted dark end card). No APPROVAL or DELIVERED line follows. Exit 1 on a FIX, 2 when every bad row is NOT CHECKED |
| `UNCHECKED` | an error after the mux and before the verdict | `UNCHECKED out.unchecked.mp4: the run broke before the QA verdict (the error follows)`, then the traceback (a planted error in `text_items`; exit 1). An error before the mux (in the render, the score or the master) leaves no file, so only the traceback is printed |

Each row prints as `STATUS CODE message`, then `[worst T s]` when a row that did not pass names a moment, `[n checked]` when it counted items, and `-> fix` when it failed (`contract.line`, ASCII only).

## How the render moves frames

`render.render_to_ffmpeg` draws every frame and pipes it into one encode at `video.mp4`:

1. **Workers.** A `ProcessPoolExecutor` of `procs` spawned processes, on every OS: a forked worker would keep ffmpeg's stdin open, so its end of input never came. Each worker's initializer (`_start`) sets the size, imports `scenes` and attaches the ring.
2. **The ring.** One shared-memory block of `2 x procs` slots, each one raw RGB frame (`W x H x 3` bytes). At 1920x1080 with 8 workers that is 16 slots of 6,220,800 bytes, 99.5 MB. A worker draws frame i into its slot and returns only the frame's digest and grey thumb, so the messages between processes stay small.
3. **Order.** The parent keeps `slots` frames in flight and takes them back in the order it sent them. It copies each slot out, then hands that slot to the next frame. Frames therefore reach ffmpeg strictly in order, whatever order the workers finish in.
4. **Retries.** A frame whose result Windows refused (WinError 1450) or that ran out of memory is drawn again after a pause of 0.5 s times the attempt, up to 6 tries (`POOL_TRIES`). Any other error belongs to the frame and stops the render. Frames go to ffmpeg's stdin in 256 KiB slices (`SLICE`); a slice refused while ffmpeg still runs is tried again up to 40 times (`WRITE_TRIES`), with pauses growing to 2 s.
5. **ffmpeg's messages.** stderr goes to the file `video.mp4.log`, never to a pipe, which could fill unread and hang ffmpeg. The encode runs with `-v error`, so a good encode writes nothing there. Any text left there after exit 0 fails the render (`ffmpeg exited 0 but logged errors: ...`). A dead ffmpeg is reported with its exit code and the first three and last lines of its log (`ffmpeg stopped after k of n frames (exit rc): ...`).
6. **On failure.** ffmpeg is killed if it still runs, the partial `video.mp4` is deleted, waiting frames are cancelled, and the ring is closed and released. `video.mp4.log` stays for reading (the next `full` deletes it); `frames.hash` and `thumbs.npy` are not written. On success the log is deleted, and then `frames.hash` and `thumbs.npy` are written.

The argv, printed from the engine's own builders at 640x360:

```
python -c "import render, contract as C; print(*render.encode_cmd('ffmpeg', 'video.mp4', 640, 360, 30)); print(*C.mux_cmd('ffmpeg', 'video.mp4', 'mix.wav', 'out.mp4'))"
```

```
ffmpeg -y -v error -f rawvideo -pixel_format rgb24 -video_size 640x360 -framerate 30 -i - -an -c:v libx264 -preset medium -crf 18 -vf scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv -pix_fmt yuv420p video.mp4
ffmpeg -y -v error -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -shortest -movflags +faststart out.mp4
```

With a size budget, `-maxrate` and `-bufsize` (kb/s) are added; x264 ignores a maxrate given without a bufsize. The colour chain:

- `contract.COLOR_VF` converts the RGB frames with the BT.709 matrix to limited range, makes them yuv420p and stamps the stream with BT.709 and tv range;
- `contract.COLOR_FLAGS` writes the same four tags into the container;
- `contract.DECODE_709` is put in front of every RGB decode a gate makes (BT.709, limited range, accurate rounding and full chroma interpolation), so the gates see the frames a player shows;
- `contract.DECODE_LINEAR` decodes to linear light for the flash gate.

Q707 checks the four tags and Q708 encodes five saturated swatches through `COLOR_VF` and reads them back through `DECODE_709`: worst 1 level, on swatch (40, 180, 60), against a limit of 8.

**frames.hash and thumbs.npy** are made from the same frames that go to the encoder. `frames.hash` is JSON with `w`, `h`, `fps`, `ss`, `n`, `algo` (`blake2b-8`) and `hash`: one 8-byte blake2b of each frame's mode, size and raw bytes. `thumbs.npy` is a uint8 array `(n, 108, 192)`, each frame in PIL grey, box-filtered to 192 x 108 whatever its aspect (a 9:16 build gives the same shape). For the 240 template frames at 1920x1080 they were 4,883 and 4,976,768 bytes. Q1105 compares the decoded file with `thumbs.npy`. The audio stage, `render.stale` and `qa.py approve` draw frames again and compare them with `frames.hash`. `qa.py approve` copies both files into `approved/`, and `qa.py diff` reads them against that copy.

**--keep-frames and --redraw.** `--keep-frames` saves each frame as `frames/f00000.png`, `f00001.png` and on (PNG compression level 1) while it renders. `--redraw T0-T1` then draws only the frames from `frame_of(T0)` up to `frame_of(T1)` and reads the rest back. It stops when a PNG it needs is missing: `frames/ lacks N of the frames to reuse (first ...): run once with keep_frames and no redraw`. The frames it reads back are checked for size only, not against `draw(t)`. A PNG left from an older `scenes.py` goes into the film unnoticed until `qa.py approve` or `run_all.py audio` draws its key frames again. Measured on the template at 1920x1080 with 8 workers, the time of the picture step only:

| Run | Picture step | Notes |
|---|---|---|
| `python run_all.py full --size 1920x1080` | 4.4 to 6.0 s (3 runs) | |
| `python run_all.py full --size 1920x1080 --keep-frames` | 5.0 s | 240 PNGs, 18.6 MB |
| `python run_all.py full --size 1920x1080 --keep-frames --redraw 3.0-4.0` | 3.4 to 3.7 s (3 runs) | 30 frames drawn, 210 read back; `frames.hash` byte for byte the same as the keep-frames run |

The template's frames are cheap to draw, so keeping them cost disk, not time, and a redraw saved about a second. The saving grows with what a frame costs to draw.

## The files a build writes

All in the working folder. The names come from `contract.py` unless the row says otherwise; the gates find the files by these names.

| File | Name in contract.py | Written by | Read by |
|---|---|---|---|
| `build.json` | `BUILD` | every stage of `run_all.py` | `qa.py check` (SS), purity, lint, owner, approve, diff, `proof.py keys` |
| `qa_proof.json` | `QA_PROOF` | proof | `proof.py keys` (the panel of rows with no moment) |
| `proof.png` | none (`run_all.proof_stage`) | proof | the reviewer |
| `proof_keys.png`, `proof_keys_2.png`, ... | none (`proof.key_sheet`) | proof; full and audio redraw it | the reviewer |
| `proof_strips.png` | none (`proof.STRIPS`) | proof, full, audio, when an entry asks for a strip; a stale one is deleted | the reviewer |
| `proof_gantt.png` | `GANTT` | proof, full, audio | the reviewer |
| `review_times.json` | `REVIEW_TIMES` | proof starts it; full, audio, `qa.py check --json` with `--scenes`, `qa.py diff` and the scans add to it | the key sheets, `review/audio.png` |
| `video.mp4` | `VIDEO` | full (`render.render_to_ffmpeg`) | the mux, the audio stage |
| `video.mp4.log` | none (`f"{out}.log"`) | full, while ffmpeg runs; deleted after a good encode | you, after a failed encode |
| `frames.hash` | `FRAMES_HASH` | full | audio stage, `render.stale`, approve, diff, lint (size), `proof.py keys` (size) |
| `thumbs.npy` | `THUMBS` | full | Q1101 to Q1104 before the encode, Q1105, approve, diff |
| `frames/` | none (`render.FRAMES`) | `--keep-frames`, `render.render_parallel` | `--redraw`, rung b |
| `mix_raw.wav` | `MIX_RAW` | `audio.render_audio` (full, audio) | the master, Q802, Q903, approve (audio hash) |
| `sfx.wav` | `SFX` | `audio.render_audio` | Q902 (each cue's sound is found here), Q802 |
| `cuesheet.json` | `CUESHEET` | `synth.CueSheet.write`, called by `render_audio` | Q802, Q804, Q902 |
| `cue_sounds.npz` | `CUE_SOUNDS` | the same | Q802, Q804, Q902 |
| `mix.wav` | `MIX` | `audio.master` | the mux, Q903 |
| `out.mp4` | none (`run_all.OUT`) | full, audio (the mux) | `qa.py check`, the reviewer, delivery |
| `<name>.rejected.mp4`, `<name>.unchecked.mp4` | none (`run_all.set_aside`) | full, audio | nobody: never delivered; the next full or audio deletes them |
| `qa.json` | `QA_JSON` | `qa.py check ... --json qa.json` | `qa.py approve` (the baseline), `proof.py keys` |
| `approved/`, `approved/approval.json` | `APPROVED`, `APPROVAL` | `qa.py approve` | `qa.py check` (Q1301 to Q1304), `diff`, `verify` |
| `review/audio.png` | `AUDIO_PNG` | `qa.py audiostrip` | the reviewer |
| `review/look.jpg` and its stills | none (`qa.look`) | `qa.py look` | the reviewer |

## Sound in a build

In `full` and `audio`, `run_all.deliver` calls `audio.render_audio(scenes, fps=E.FPS)`. That writes `mix_raw.wav` (music plus effects), `sfx.wav` (the effects bus alone, at the same scale) and the cue sheet (`cuesheet.json` with `cue_sounds.npz`). Then `master_and_mux` runs `audio.master(mix_raw.wav, mix.wav, TP=ceiling)` and the mux, and measures the true peak of the decoded `out.mp4` with `qa.loud`. While that peak is over -1.3 dBTP (`TP_MAX` -1.0 less `TP_TOL` 0.3), it masters again at a lower ceiling, at most 3 times (`RETRIES`, `MARGIN` 0.2 dB). It keeps the try with the lowest peak among those that are Q805 clean and inside -1 dBTP, or among all tries when none is, and masters and muxes that one again if it was not the last.

The template score (`audio.bed`): a kick on beats 1 and 3, a tick on every off-beat, and one sine `tone` on every beat, its pitch changing each bar (220, 261.63, 196, 246.94 Hz), all on the music bus. On the effects bus, at each cut, a whoosh whose loudest point leads the cut by `WHOOSH_LEAD` (0.08 s) and a hit whose onset is on the cut's frame, labelled with the cue at that time. A kick within 3 frames of a cut is left out, so two heavy sounds never stack. The cuts come from `scenes.CUTS`, or from every scene start after 0.

| Where | Sample rate |
|---|---|
| `audio.SR`, `synth.SR`, `voice.SR`: the buses, `mix_raw.wav`, `sfx.wav`, `narration.wav` | 44,100 Hz |
| `audio.SR_MASTER`: the master resamples to it, limits there and writes `mix.wav` (16-bit stereo) | 48,000 Hz |
| the gates' decodes of the file | 48,000 Hz (true peak, and the check that confirms each cue on the file), 8,000 Hz (silence, and the onset detector used when there is no cue sheet); with a cue sheet, Q902 searches the 44.1 kHz stems |

The master (`audio.master`) applies one static gain to -14 LUFS, then the true-peak limiter: 4x oversampled through Kaiser-windowed sinc filters (`OS`, `TAPS` 32 a phase), 3 ms lookahead and 100 ms release, with no delay added. It measures again with ffmpeg's ebur128 and nudges the gain, up to 6 passes, until it is within 0.05 LU of the target and at or under the ceiling. The first ceiling is `audio.CEILING`, -2.0 dBTP, which leaves room for the peak the AAC encode adds. On the template the encode raised the peak from -2.00 to -1.80 dBTP. Q805 fails a master that missed by more than 0.1 LU or 0.05 dB, or whose limiter took more than 0.5 LU off the programme (`LINEAR_COST`) or more than 6 dB at any moment (`LINEAR_DEPTH`). On the template: gain +0.82 dB in 2 passes, 0.22 LU taken, at most 1.4 dB.

### Your own score

The sync and stack gates measure what the cue sheet and `sfx.wav` say, so a score of your own must write the same four files the same way. Place every sound with `synth.place`, `put` or `put_peak` (or `audio.place`) inside `with synth.recording() as sheet:`. Build both buses at `synth.SR`, write them with `audio.write_wav` at one shared scale, and let `sheet.write(folder, scale)` fold that scale into every row's gain. Give each cue's sound its `CUES` label. A frame cue (`frame=`, `fps=`) puts the sound's landmark on the frame's first sample. This example was run in a scratch copy:

```python
# score.py : this video's own score, in place of audio.render_audio
from pathlib import Path

import audio
import contract as C
import numpy as np
import synth as S


def render_score(scenes, folder=".", fps=None):
    """A pad on every bar, a hat on every off-beat, a clap on every cue that has
    sound. Writes the same four files as render_audio and returns their paths."""
    fps = fps or scenes.FPS
    n = C.sample_of(scenes.DURATION, S.SR)
    music, sfx = np.zeros(n), np.zeros(n)
    beat = 60 / scenes.BPM
    chord = [57, 60, 64]
    # every place() inside this block becomes a row of the cue sheet
    with S.recording() as sheet:
        for bar in range(round(scenes.DURATION / (4 * beat))):
            pad = S.pad(chord, 4 * beat)
            S.place(music, pad, bar * 4 * beat, 0.6, sound="pad", stem="music")
        for i in range(round(scenes.DURATION / beat)):
            at = (i + 0.5) * beat
            S.place(music, S.hat(), at, 0.3, sound="hat", stem="music")
        for c in C.cues(scenes):
            if c["kind"] == "picture":
                continue
            # a frame cue: the clap's onset lands on the cue frame's first sample
            f = C.frame_of(c["t"], fps)
            S.place(
                sfx, S.clap(), frame=f, fps=fps, g=0.8, sound="clap", label=c["label"]
            )
    # one scale for both files, so sfx.wav lines up with mix_raw.wav sample for sample
    scale = 0.85 / max(np.abs(music + sfx).max(), np.abs(sfx).max(), 1e-9)
    out = {k: str(Path(folder, getattr(C, k.upper()))) for k in ("mix_raw", "sfx")}
    audio.write_wav(out["mix_raw"], music + sfx, scale=scale)
    audio.write_wav(out["sfx"], sfx, scale=scale)
    out["cuesheet"], out["cue_sounds"] = sheet.write(folder, scale)
    return out
```

In the working copy of `run_all.py`, add `import score` under `import scenes`, and change `made = audio.render_audio(scenes, fps=E.FPS)` in `deliver` to `made = score.render_score(scenes, fps=E.FPS)`. Both `full` and `audio` go through `deliver`. With the template's scenes at 640x360, `python run_all.py full --size 640x360` then gave `QA: PASS (49 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)`: Q902 found both claps on their cues (worst +0.0 ms), Q804 counted 2 placed sounds and set 20 music-bus sounds aside, and the master took 0.03 LU.

### Narration in the mix

`render_audio` takes no voice, so a voiced piece needs a score of its own that adds `narration/narration.wav` to the mix. The engine has three pieces for it:

- `voice.dec(path)` decodes it to float32 mono at 44.1 kHz.
- `audio.write_wav(path, mono, voice=v, scale=...)` adds the voice into the mix it writes.
- `voice.duck_mix(bed, voice, depth_db=8)` sets the bed to about -18 dBFS RMS, pulls it down 8 dB while the voice speaks (a -38 dB gate on 10 ms windows, 40 ms to close and 300 ms to let go) and lays the voice over it at a peak of 0.89 plus 2 dB. The template's `audio.bed(..., voice_spans=[(a, b)])` ducks only its music bus, 8 dB, in the spans given.

Keep the voice out of `sfx.wav`: Q902 finds each cue's own sound there by cross-correlation. Levels and practice are in [sound.md](sound.md) and [voice.md](voice.md).

## The encode ladder

H.264 in MP4 through libx264 comes first: it is what `run_all.py full` makes, and the only kind every gate covers. Without libx264, draw PNG frames and encode AV1 in MP4, or VP9 in WebM when there is no AV1 encoder. A GIF is the last rung, for a preview. The delivery report names the rung and the reason ([delivery.md](delivery.md)). The limits and the destinations are in [formats.md](formats.md).

See what your ffmpeg has with `ffmpeg -hide_banner -encoders`. This machine's ffmpeg 9.0.2 listed every encoder the ladder uses: libx264, libsvtav1, libaom-av1, librav1e, libvpx-vp9, libopus, aac, gif and png. It also had h264_nvenc and av1_nvenc, which the engine does not use.

### Rung a: libx264

`python run_all.py full --size WxH --fps N` runs the pipe and the mux shown above (`render.encode_cmd`, then `contract.mux_cmd`). To mux again by hand after changing `mix.wav`, run the mux line as printed; it returned exit code 0 and a file with h264 and aac:

```
ffmpeg -y -v error -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -shortest -movflags +faststart out.mp4
```

Then run `python qa.py check out.mp4 --scenes . --size WxH --fps N --json qa.json` (add `--bpm N` for a piece with a BPM). On the template at 1920x1080 it ended `QA: PASS (44 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)`.

### Rung b: no libx264

**Step 1: frames, their records and the sound.** Save this as `ladder_b.py` in the working folder and run it with the build's flags. It draws every frame as PNG in parallel (`render.render_parallel`). It writes `frames.hash` and `thumbs.npy` from those PNGs exactly as the render would. Then it makes and masters the sound by hand (`audio.render_audio`, then `audio.master`); use your own score function there if the build has one.

```python
# ladder_b.py : rung b of the encode ladder, the steps before ffmpeg. Run it like run_all.py, with the same
# --size, --fps and --ss: PNG frames in frames/, frames.hash and thumbs.npy rebuilt from them, then the mastered mix.
import numpy as np
from PIL import Image

import run_all  # reads --size, --fps and --ss, then imports scenes at that size
import audio
import contract as C
import render

if __name__ == "__main__":
    E, scenes = run_all.E, run_all.scenes
    C.write_build(E.W, E.H, E.FPS, E.SS)
    n = render.render_parallel()  # every frame as frames/f00000.png, f00001.png, ...
    digests, thumbs = [], []
    for i in range(n):
        with Image.open(render.png_path(i)) as im:
            frame = im.convert("RGB")
        digests.append(C.frame_digest(frame))
        thumbs.append(C.thumb(frame))
    C.write_frame_manifest(digests, E.W, E.H, E.FPS, ss=E.SS)
    np.save(C.THUMBS, np.stack(thumbs))
    audio.render_audio(scenes, fps=E.FPS)
    m = audio.master(C.MIX_RAW, C.MIX)
    print(
        f"{n} frames in {render.FRAMES}/; {C.MIX} {m['I']:.1f} LUFS at {m['tp']:.2f} dBTP"
    )
    for r in m["rows"]:
        print(C.line(r))
```

```
python ladder_b.py --size 640x360
```

It printed `240 frames in frames/; mix.wav -14.0 LUFS at -2.00 dBTP` and a PASS Q805 row, in 7.6 s. The `frames.hash` and `thumbs.npy` it wrote were byte for byte the ones an earlier `full` at the same size had written for the same `scenes.py`. On a machine where the process pool cannot start, `render.render_frames()` writes the same PNGs in one process, more slowly (not run here).

**What to do with an earlier render's frames.hash and thumbs.npy.** They describe the frames that render drew. Q1105 compares the file under check with `thumbs.npy`: it fails when they differ, reads NOT CHECKED when only `frames.hash` is there, and gives no row when neither is. `qa.py approve` needs both, and the audio stage trusts `frames.hash`. So do not check a rung b file against a pair from another state of `scenes.py`. Let `ladder_b.py` rewrite both from the PNGs you are about to encode, as above. Deleting both also clears Q1105, but leaves nothing to approve against.

**Step 2: encode.** Use the first line whose encoder your ffmpeg has: SVT-AV1, then libaom AV1, then VP9 in WebM. Each runs the frames through the engine's colour chain (`contract.COLOR_VF`, `COLOR_FLAGS`), and all three files read back yuv420p, tagged BT.709 and tv range:

```
ffmpeg -y -v error -framerate 30 -i frames/f%05d.png -i mix.wav -map 0:v -map 1:a -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv" -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv -c:v libsvtav1 -preset 8 -crf 35 -c:a aac -b:a 320k -shortest -movflags +faststart out_av1.mp4
ffmpeg -y -v error -framerate 30 -i frames/f%05d.png -i mix.wav -map 0:v -map 1:a -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv" -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv -c:v libaom-av1 -cpu-used 6 -row-mt 1 -crf 30 -b:v 0 -c:a aac -b:a 320k -shortest -movflags +faststart out_av1.mp4
ffmpeg -y -v error -framerate 30 -i frames/f%05d.png -i mix.wav -map 0:v -map 1:a -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv" -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv -c:v libvpx-vp9 -row-mt 1 -crf 32 -b:v 0 -c:a libopus -b:a 160k -shortest out.webm
```

Set `-framerate` to the build's fps. The MP4 lines use the engine's AAC settings (`contract.AAC_ARGS`); WebM carries Opus. SVT-AV1 prints its own banner of `Svt[info]` lines even under `-v error`; that is not an error.

| Encoder (640x360, 8 s template) | Encode | File | Read back |
|---|---|---|---|
| libsvtav1, preset 8, CRF 35 | 0.9 s | 280,077 bytes | av1, yuv420p, bt709 / tv, 240 frames, aac |
| libaom-av1, cpu-used 6, CRF 30 | 1.7 s | 277,529 bytes | av1, yuv420p, bt709 / tv, aac |
| libvpx-vp9, CRF 32, Opus 160 kb/s | 1.6 s | 198,356 bytes | vp9, yuv420p, bt709 / tv, opus, no frame count in the container |

**Step 3: check.**

```
python qa.py check out_av1.mp4 --scenes . --size 640x360 --fps 30 --bpm 120
```

`qa.py check` holds the pixel format and the BT.709 chain to the H.264 deliverable only. On any other codec it gives Q705, Q707 and Q708 as NOT CHECKED rows (`av1 file: the yuv420p check is for the H.264 deliverable`, and so on) and runs every other gate. All three files ended `QA: NOT CHECKED (3)` with exit code 2: 44 checks for each AV1 file, and 43 for the WebM, which has no frame count for Q704. Q1105 passed on all three against the rebuilt `thumbs.npy` (worst 1.14 levels mean, 0 of 240 frames over 4), and so did every sound gate (Q801, Q802, Q902, Q903). Check the WebM the same way with `out.webm` in place of `out_av1.mp4`.

Those three rows are expected on rung b. The delivery report lists them under Not checked, as [delivery.md](delivery.md) says. They also stop `qa.py approve`: with `qa.json` from that check, `qa.py approve --video out_av1.mp4` printed `REFUSED: qa.json has NOT CHECKED rows: Q705, Q707, Q708`. Approve then takes `--override "<why>"` and keeps the reason in `approval.json` (the override was not run here). `--video` names the file, because `qa.py approve` otherwise takes `OUT` from `run_all.py`.

### Rung c: a GIF preview

At most 15 s, at most 960 px wide, 15 fps and no sound ([formats.md](formats.md)); a preview, never the deliverable ([delivery.md](delivery.md)). From a finished MP4, decoded as BT.709 limited range through `contract.DECODE_709` before the palette is made:

```
ffmpeg -y -v error -t 15 -i out.mp4 -vf "fps=15,scale=in_color_matrix=bt709:in_range=tv:flags=accurate_rnd+full_chroma_int,format=rgb24,scale='min(960,iw)':-2:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" -an -loop 0 preview.gif
```

From rung b's PNG frames, which are already RGB (set `-framerate` to the build's fps):

```
ffmpeg -y -v error -framerate 30 -t 15 -i frames/f%05d.png -vf "fps=15,scale='min(960,iw)':-2:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" -loop 0 preview.gif
```

At 640x360 the first gave 120 frames at 15 fps, 640x360, 513,486 bytes, and the second 162,978 bytes. On the 1920x1080 template file the first gave 960x540, 120 frames, 799,169 bytes. `qa.py check` is not run on a GIF.

### No ffmpeg at all

No rung finishes without ffmpeg. The master decodes and measures loudness through ffmpeg, and every encode and every gate on a file runs ffmpeg. What still runs is the whole proof stage, the PNG frames (`render.render_parallel`) and the raw mix (`audio.render_audio`). With ffmpeg taken off PATH, the proof ended `PROOF: PASS`, and `python ladder_b.py --size 640x360` wrote 240 PNG frames, `frames.hash`, `thumbs.npy`, `mix_raw.wav`, `sfx.wav` and the cue sheet before `audio.master` stopped with FileNotFoundError. Install ffmpeg with libx264, check it with `setup.sh`, and run `full`.
