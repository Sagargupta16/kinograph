# Troubleshooting

What a line printed by the engine means, and what to do next. Start from the first words of the line in [Find your line](#find-your-line); each entry says what the line means and the exact next step. What a Q code measures is in [qa-gates.md](qa-gates.md); the stages, the build files and the encode ladder are in [engine.md](engine.md).

Every quoted line was printed by a run on 2026-11-01, on the shipped template or on a scratch copy of it with one fault planted (at 640x360 unless a size is given; Windows 11, uv 0.13.6, Python 3.15.2, Pillow 13.0.0, numpy 2.5.4, ffmpeg 9.0.2), or it is read from the code, which is then named. In a quoted line, `<...>` stands for a part that changes from run to run, `...` for a part left out, and paths are cut to `<working folder>`. In commands, `python` means `uv run --no-project --with-requirements requirements.txt python`, run from the working folder.

## Find your line

| The line starts with | Printed by | Entry |
|---|---|---|
| a FIX line from `setup.sh`, or no `SETUP: PASS` at the end | `bash <skill>/setup.sh` | [Setup and tools](#setup-and-tools) |
| `uv: command not found` | the shell | [Setup and tools](#setup-and-tools) |
| `NO_FFMPEG`, `qa.py: no ffmpeg on PATH` | `run_all.py full` or `audio`; `qa.py check` or `look` | [Setup and tools](#setup-and-tools) |
| `FileNotFoundError: engine.font` | any stage that draws | [Setup and tools](#setup-and-tools) |
| `MISSING qa_fixtures/__init__.py` | `qa.py selftest` | [The working folder](#the-working-folder) |
| `Traceback`, ending in a `ValueError` about a scene, a cue or a Transition | any stage, while `scenes.py` imports | [Tracebacks before any row](#tracebacks-before-any-row) |
| `note: scenes.py sets` | every stage | [Tracebacks before any row](#tracebacks-before-any-row) |
| `PROOF: FIX`, `PROOF: NOT CHECKED` | `run_all.py proof` | [Proof rows](#proof-rows) |
| `REJECTED`, `UNCHECKED` | `run_all.py full` or `audio` | [Rejected and unchecked files](#rejected-and-unchecked-files) |
| `master:`, `re-master`, `kept the`, `true peak still over`, `the file's peak did not follow` | the master inside `full` and `audio` | [Sound rows and the true-peak loop](#sound-rows-and-the-true-peak-loop) |
| `ValueError: frame`, `RuntimeError: ffmpeg stopped after`, `ffmpeg exited 0 but logged errors`, `write to ffmpeg failed`, `note: frame ... drawn again` | the render inside `full` | [Render failures](#render-failures) |
| `no video.mp4 here`, `video.mp4 was rendered at`, `video.mp4 predates scenes.py` | `run_all.py audio` | [Stage refusals](#stage-refusals) |
| `--redraw needs --keep-frames`, `frames/ lacks` | `run_all.py full --redraw` | [Stage refusals](#stage-refusals) |
| `a <N> MB budget leaves no video bitrate` | `run_all.py full` with a size budget | [Stage refusals](#stage-refusals) |
| `not checked here:`, `FIX  Q1105`, `NOT CHECKED Q100`, `NOT CHECKED Q502 the last frame did not decode` | `qa.py check` | [Checking a file by hand](#checking-a-file-by-hand) |
| `REFUSED:`, `CANNOT APPROVE`, `STALE APPROVAL`, `APPROVAL: stale`, `DIFF:`, `VERIFY:` | `qa.py approve`, `check`, `diff`, `verify`, and the end of `full` | [Approval, diff and verify](#approval-diff-and-verify) |
| `warning: STATIC`, or no error at all: a render that takes too long, a file over its budget | | [Slow builds and big files](#slow-builds-and-big-files) |

Every row prints as its status, its code and its message, then `[worst <t> s]` when it names a moment, `[<n> checked]`, and `-> <fix>` when it did not pass (`contract.line`). The `->` text is the first thing to try. Exit codes follow `contract.exit_code`: 0 when no row is FIX or NOT CHECKED, 1 on any FIX, 2 when some row is NOT CHECKED and none is FIX.

## Setup and tools

`bash <skill>/setup.sh` checks the machine and installs nothing system-wide (its first uv run may fetch the pinned Python and wheels into uv's cache). It ends `SETUP: PASS`, or it prints its FIX lines, one for each gap. Do what each FIX line says, open a new shell so that a changed PATH takes effect, and run `setup.sh` again until it ends `SETUP: PASS`.

**`uv: command not found`.** Every engine command runs through uv, so nothing runs without it (seen with uv taken off PATH: the shell's own message, exit 127). Install uv, open a new shell and run `setup.sh` again.

**`NO_FFMPEG: no ffmpeg on this machine. Every rung of the encode ladder needs one: install an ffmpeg with libx264, then check it with setup.sh`** (exit 1, seen with ffmpeg taken off PATH; the folder is left as it was). `run_all.find_ffmpeg` looks on PATH, then at `/opt/homebrew/bin/ffmpeg` and `/usr/local/bin/ffmpeg`. `qa.py check` and `qa.py look` stop the same way with `qa.py: no ffmpeg on PATH (nor in /opt/homebrew/bin or /usr/local/bin)` (exit 1, seen). The proof stage needs no ffmpeg. `full`, `audio`, the master (`audio.master` measures loudness with ffmpeg's ebur128) and every gate on a file do. Install an ffmpeg build with libx264 and ffprobe, check that `ffmpeg -version` runs in the same shell the build runs in, then run `setup.sh`.

**An ffmpeg without libx264.** The render pipes every frame into a libx264 encode (`render.encode_cmd`), so `full` stops at the first frame with `RuntimeError: ffmpeg stopped after 1 of 240 frames (exit <code>): ...`, followed by ffmpeg's own lines. A scratch copy with the encoder name changed printed `Unknown encoder 'libx264_absent'` and `Encoder not found` there. `ffmpeg -hide_banner -encoders` lists what your build has. Without libx264, follow the encode ladder in [engine.md](engine.md) (PNG frames, then AV1 in MP4 or VP9 in WebM) and say which rung made the file. Every rung still needs ffmpeg, for the master and for the encode. `qa.py check` then gives Q705, Q707 and Q708 as NOT CHECKED on a file that is not H.264, and on an H.264 file Q708 reads `colour round trip could not run: the libx264 encode or the decode of the swatch clip failed` when this ffmpeg cannot encode libx264 (`qa.check`). The delivery report lists those rows as not checked ([delivery.md](delivery.md)).

**`FileNotFoundError: engine.font: no file in FONT_BOLD exists and opens (...)`** (seen with the list emptied in a scratch copy). `engine.font` tries the paths in `engine.FONT_BOLD` (or `FONT_REG` for regular type) in order and takes the first file that exists and opens: Arial on Windows, Arial or Helvetica on macOS, then Liberation Sans and DejaVu Sans in the usual Linux folders. The message lists every path it tried and what to install: Arial, or on Debian and Ubuntu `apt install fonts-liberation fonts-dejavu-core`, or on Fedora `dnf install liberation-sans-fonts dejavu-sans-fonts`. To use a font file you already have, put its path first in `FONT_BOLD` (and `FONT_REG`) in the working copy of `engine.py`. A font change moves pixels, so make it before the proof, never between an approval and delivery (Q1304, below).

**The Python version.** uv takes the interpreter from `.python-version` in the folder it runs in; the engine's file says `3.15`, and `requirements.txt` pins Pillow and numpy with hashes. Keep both in the working folder and run every stage from there, so the proof and its render run on one Python. A folder without `.python-version` runs on whatever interpreter uv picks by its own rules: on 2026-11-01 this machine still gave 3.15.2, but nothing holds it there. An approval records the Python version and compares its major.minor number, so a change of Python that moves a key frame is Q1304 NOT CHECKED.

## The working folder

Copy the engine with `cp -r <skill>/engine/. <working folder>/`. The `/.` copies everything inside `engine/`, hidden files and folders included.

| Copy made with | What is missing | What you see |
|---|---|---|
| `cp -r <skill>/engine/* <working folder>/` | `.python-version`: a glob skips hidden files | nothing at once; the Python version is no longer pinned (above) |
| only the `.py` files | `qa_fixtures/` | `qa.py selftest` prints `MISSING qa_fixtures/__init__.py: ModuleNotFoundError: No module named 'qa_fixtures'`, an `UNCOVERED` line for each code, and ends `SELFTEST: FAIL (...)` with exit 2 (seen with `--only Q201`) |
| `cp -r <skill>/engine <working folder>`, into a folder that exists | the engine lands one folder down, in `<working folder>/engine/` | no stage script in the working folder |

Make the copy again with `/.`.

## Tracebacks before any row

**A `ValueError` from `compile_schedule`.** The `TIMELINE` cannot be compiled, so `scenes.py` does not import and no stage starts. Seen with a Transition put first: `ValueError: Transition(kind='crossfade', dur=0.2, split=0.5) must sit between two scenes`. Every message `compile_schedule` raises is listed with its cause in [engine.md](engine.md), under "Scene, Transition and compile_schedule". Fix the `TIMELINE` entry it names and run the stage again.

**A traceback that ends in your own error.** Save the stage's output to a file and let the engine route it: `python qa.py owner --traceback <file>`. It takes the innermost `scenes.py` frame of the traceback and names the function to edit (`qa_lint.owner`). Seen:

- `owner: scenes.py:43 is module-level code (runs at import)`, then `error: ValueError: ...`: the fault is in code that runs on import, such as the `TIMELINE` or a table built at module level.
- `owner: scenes.py:157 is inside text_items (scenes.py:155-158), a shared helper: ...`, then the functions to re-read.
- `owner: give --t SECONDS or --traceback FILE` (exit 2): give exactly one of the two.

**An exception inside `draw(t)` or `text_items(t)` during the proof.** The proof's text gates and text recorder call `text_items` and `draw` on sampled frames inside `qa.proof_rows`, with no guard and before any row is printed, so the proof stops with the traceback and prints no `PROOF:` line (seen with a planted `ZeroDivisionError` in `draw`). `python qa.py purity` on the same folder turns it into a row: `NOT CHECKED Q1201 draw(t) raised in this process at 1 sampled frames, so they were not compared: frame 92 (3.067 s): ...`. Route the traceback with `qa.py owner --traceback`, fix the exception, then run the proof again.

**`note: scenes.py sets 640x360 at 30 fps, SS 1 itself, which wins over --size, --fps and --ss`** (seen with `--size 1920x1080`). `scenes.py` assigns `engine.W`, `engine.H`, `FPS` or `SS` before `from engine import *`, so the build runs at that size whatever the flags say, and `build.json` records it. When that is not the storyboard's size, take the assignment out of `scenes.py` and pass the size with `--size`.

## Proof rows

`run_all.py proof` ends with `PROOF: PASS`, with `PROOF: FIX (<n>) (...)` (exit 1), or with `PROOF: NOT CHECKED (<n>) (...)` (exit 2, only when no row is FIX). Seen: `PROOF: FIX (2) (23 checks, 2 FIX, 1 NOTE, 0 NOT CHECKED)` and `PROOF: NOT CHECKED (1) (23 checks, 0 FIX, 0 NOTE, 1 NOT CHECKED)`.

From a row to its fix:

1. Read the row's `->` text: it says what to change.
2. Look the code up in [qa-gates.md](qa-gates.md). The digits after the Q give its family: Q100 a gate module that raised, Q2xx text placement, Q3xx contrast, Q4xx reading holds, Q5xx frame 0 and the end card, Q6xx flashes, Q7xx what ffprobe reports, Q8xx loudness and the master, Q9xx sync, Q10xx file size, Q11xx the frame scans, Q12xx purity and lint, Q13xx approval. `contract.CODES` names the module that makes each code.
3. A row with `[worst <t> s]` names a moment: `python qa.py owner --t <t>` names the scene function that draws it. The template has no scene functions of its own, so there it answers `draw`.
4. Fix it in that function and run the proof again with the same flags. Declare `NO_TEXT`, `NO_CUES`, `SILENT` or an `ALLOW` entry only when the storyboard means it, never to quiet a row; `ALLOW` clears NOTE rows only.

The contract faults that come up most, each planted in a scratch copy of the template:

| Row (seen unless marked) | What is wrong | Fix |
|---|---|---|
| `FIX  Q1201 draw(t) not pure: 24 of 24 frames differ; ...; drawn twice in one cold process the second draw differs: draw writes state it reads back; ...; owner: draw (...)` | `draw` changed a module-level list on each call and read it back | Make each frame depend on t alone: no counter, list or cache written inside `draw`, and a cache keyed by everything it depends on. The row names the frames that poison the next one, and the owner |
| `NOTE Q1203 module state written inside functions: 1 found: scenes.py:157 _calls[0] += 1 in draw ...` | the same state write, found by the lint | Compute it from t. A memo you mean takes `# kinograph: state-ok` on that line |
| `FIX  Q1202 unseeded randomness, clock reads or str hashes: 2 found: scenes.py:159 random.random() in draw; scenes.py:159 hash("dust") in draw ...` | the shared `random` stream, and `hash()` of a string, whose seed changes from process to process | `engine.rng(scene, element, frame_of(t, FPS))` for randomness, `zlib.crc32(s.encode())` for a string's hash. Q1201 can still pass, as it did here; its row then says the flagged line ran on the sampled frames, and the lint row stays FIX |
| `NOT CHECKED Q200  scenes.py has no text_items(t), so gates 2 to 4 did not run`, with `FIX  Q204  scenes.py has no text_items(t): 4 drawn strings are unreported (...)` | no text registry | Add `text_items(t)`, fed by the same layout function `draw` uses (the template's `placed`). `NO_TEXT = True` is only for a piece with no text |
| `NOT CHECKED Q200  text_items(t) returns items without the s and box keys at ...` (code, `qa.registry_rows`) | a registry in an older form | Report each text with `s`, a `box` from `engine.text_box`, `fg`, `alpha` and `px` |
| `FIX  Q204  drawn text not in text_items(t): 'Beta' (120 px at 1080, alpha 1.00; 5.00 to 7.97 s)` | `draw` paints a string the registry never reports | Report it, with its `engine.text_box` box, over the same span |
| `FIX  Q205  registry box of '{the one point}' is 12.0 px off the drawn glyph box (text_box, limit 2.0 px; registry (...), drawn (...); 25 of 25 frames)` | the registry box drifted from where the text is drawn | Build the box with `engine.text_box` from the string, xy, size and anchor the draw uses, read from one shared layout function |
| `NOTE Q209  text_items(t) reports 'Ghost' at alpha >= 0.5, but nothing drawn matches (at 2.00 to 4.97 s)` | the registry reports text the frame does not show | Report alpha 0, or leave the item out, while it is not drawn |
| `FIX  Q206  '{title}' is covered: 0.00 of its 1346 ink px show at 0.90 s (needs 0.7)` | a later layer is painted over a registered text | Draw the text after what covers it, or move one of the two |
| `NOT CHECKED Q401  HOLD_PROFILE 'fast' is not one of display, caption, slow (or a dict of cps, pad, floor), ...` | an unknown reading profile | Use `display`, `caption`, `slow`, or a dict of `cps`, `pad` and `floor` |

## Rejected and unchecked files

**`REJECTED <name>.rejected.mp4: <code> <status>, ...`.** A gate row other than the approval codes was FIX or NOT CHECKED, so `run_all.deliver` moved the file aside (`set_aside`) and printed no APPROVAL and no DELIVERED line. Exit 1 on a FIX, 2 when every bad row is NOT CHECKED. Seen: `REJECTED out.rejected.mp4: Q502 FIX` (an end card drawn black) and `REJECTED out.rejected.mp4: Q902 NOT CHECKED` (with `CUES = []`, exit 2). Next:

1. Read each named code's row in the output above the REJECTED line: its message, its `[worst <t> s]` and its `->` fix. The key sheets are drawn again with those rows, so `proof_keys.png` shows each named moment.
2. Find the code in [qa-gates.md](qa-gates.md), and the scene function with `python qa.py owner --t <t>`.
3. Fix it, then run the stage that covers the change, with the same flags: `run_all.py audio` when every frame stays as it was (the score, `CUES`, `text_items`), `run_all.py full` when the picture changes. `audio` refuses a picture that no longer matches `scenes.py` ([Stage refusals](#stage-refusals)).
4. Run `qa.py check ... --json qa.json` again on the new file, so `qa.json` is never older than it.

A `.rejected.mp4` is never delivered or approved; the next `full` or `audio` deletes it (`run_all.clean`).

**`UNCHECKED <name>.unchecked.mp4: the run broke before the QA verdict (the error follows)`.** An exception stopped the run after the mux and before the gates gave their verdict, and the traceback follows the line. Seen with `text_items` raising for t over 7.5 s: the text gates inside `qa.check` stopped with `KeyError: 'link'`. An error before the mux (in the render, the score or the master) leaves no file at all, only the traceback. Save the output, run `python qa.py owner --traceback <file>`, fix the error, and run again. In that case the fix touched `text_items` only, so `run_all.py audio` reused `video.mp4` and ended with a DELIVERED line. A gate module that raises inside `qa.check` does not stop the run: it becomes a Q100 NOT CHECKED row ([Checking a file by hand](#checking-a-file-by-hand)), and so does a crash of the scans of `thumbs.npy` (`run_all.guarded`).

**The approval rows.** Q1301 to Q1304 never reject a file (`run_all.is_approval`). They print as `approval <state>: <code> <message>` and set the APPROVAL line. Seen after a change to the end card: `APPROVAL: stale: Q1301 end -> re-review the changed scenes, then qa.py approve`, followed by a DELIVERED line. The run still ends that way, but the change goes to a fresh final review, and the new file cannot pass `qa.py verify` until it is approved ([Approval, diff and verify](#approval-diff-and-verify)).

## Sound rows and the true-peak loop

| Row (seen) | What it means | Fix |
|---|---|---|
| `FIX  Q902  point lands at 2.00 s: hit (onset) lands +66.7 ms late (FIX past +33.3 ms at 30 fps) on sfx.wav, match 1.00` | the sound for a cue sits 2 frames after it (a scratch score placed each cut's hit 2 frames late) | Place the sound by its landmark on the cue's frame, as in `synth.place(sfx, sound, frame=frame_of(t, fps), fps=fps, ...)`; the row's fix says how many ms to move it. Late by more than one frame (a limit capped at 60 ms) or early by more than 40 ms is a FIX |
| `FIX  Q902  sparkle at 6.63 s: no sound found (cuesheet.json has no sound labelled 'sparkle' and none within 100 ms)` | a cue no placed sound serves: no sound on the cue sheet carries its label, and none sits within 100 ms | Place a sound with that `CUES` label, or give the cue kind `"picture"`. A cue with any unlabelled sound within 100 ms is matched to it: in the same copy, a cue at 6.5 s matched a music-bed sound placed at 6.5 s and passed |
| `NOT CHECKED Q902  CUES is empty, so cue sync did not run` | no cues | List every moment sound and picture share in `CUES`, or set `NO_CUES = True` when the piece has none. With no `CUES` name at all, the message starts `scenes.py has no CUES` (code, `qa_sync`) |
| `FIX  Q802  true peak -0.8 dBTP (want <= -1) at 2.011 s; ...; sounding there: whoosh (...); hit 'point lands' (...); ...` | the decoded file peaks over -1 dBTP; the row lists the sounds there and the order to cut them in | Lower or cut the sounds it names, in its order, then run `run_all.py audio` |
| `NOTE Q804  stacked sounds at 2.00 s: hit 'point lands' + kick: 2 heavy 0 frame(s) apart (want more than 3)` | two heavy sounds on one moment | Keep the heaviest and move the other 4 or more frames off, or list a stack you mean in `ALLOW['Q804']` |

How Q902 finds each sound, and how a score of your own writes the cue sheet it reads, are in [sound.md](sound.md) and [engine.md](engine.md).

**The true-peak loop** (`run_all.master_and_mux`). The master aims for a decoded file at or under -1.3 dBTP (`TP_MAX` -1.0 less `TP_TOL` 0.3) and masters again, at most 3 times (`RETRIES`), while the file is over that. Each try prints one line. Seen in a scratch copy whose first ceiling was raised to -0.6 dBTP:

```
master: ceiling -0.60 dBTP, mix.wav -14.0 LUFS at -0.72 dBTP (Q805 PASS) -> out.mp4 -14.0 LUFS at -0.80 dBTP
re-master 1 of 3: ceiling -1.42 dBTP, mix.wav -14.0 LUFS at -1.43 dBTP (Q805 PASS) -> out.mp4 -14.0 LUFS at -1.40 dBTP
```

That file was delivered at -1.4 dBTP. The lines that can close the loop:

| Line | Source | Next step |
|---|---|---|
| `kept the cleanest master: ...` or `kept the least limited master: ...` | code | Nothing: the loop went back to its best try and mastered that one again |
| `note: <peak> dBTP is inside gate 8 but within the 0.3 dB meter tolerance of it (a lower ceiling made the master fail its own check)` | code | The file passes; the delivery report says it sits close to the limit |
| `the file's peak did not follow the ceiling (...): no lower ceiling will help` | code | The limiter cannot fix it: lower the loud sounds themselves |
| `true peak still over -1 dBTP after <n> re-masters: lower the hits Q802 names` | seen, with the retries set to 0 | A Q802 FIX follows: lower the sounds its row lists, then run `run_all.py audio` |

A Q805 FIX means the master missed -14 LUFS or its ceiling, or had to limit too hard ([qa-gates.md](qa-gates.md), gate 8). Bring the loud hits down in the score rather than pushing the limiter.

## Render failures

`render.render_to_ffmpeg` draws the frames in a pool of processes and pipes them, in order, into one ffmpeg. On any failure it kills ffmpeg, deletes the partial `video.mp4` and raises, so `full` ends with a traceback and leaves no `out.mp4`. ffmpeg writes its messages to `video.mp4.log`, which stays after a failure, is deleted after a good encode, and is deleted again by the next `full`.

| Last line | Source | What it means, and the next step |
|---|---|---|
| `ValueError: frame 180 (t 6.000 s) is 638x360; the build is 640x360` | seen (`render.checked`) | `draw(t)` returned a frame of another size. In a raw pipe one such frame would shear every frame after it, so the render stops at the first. End every path through `draw` in `finish(...)` on a canvas from `canvas()`, and never resize the returned frame |
| `RuntimeError: ffmpeg stopped after <k> of <n> frames (exit <code>): <log lines>` | seen (`render._failed`) | ffmpeg exited during the encode. The line carries the first three lines and the last line of its log; the whole log is in `video.mp4.log`, and the cause is there (seen: a missing encoder). Fix it and run `full` again. When ffmpeg has died, the failed write (seen: `OSError: [Errno 22] Invalid argument`) is reported this way, with ffmpeg's log |
| `ffmpeg exited 0 but logged errors: <log>` | code (`render.render_to_ffmpeg`) | The encode runs with `-v error`, so a good encode logs nothing, and any text left in the log fails the render. Read it, fix its cause, run `full` again |
| `write to ffmpeg failed while it was running (frame <k> of <n>, 40 retries): <error>` | code (`render._send`) | ffmpeg was alive but refused a 256 KiB slice of frame data 40 times running (`WRITE_TRIES`, about 41 s of pauses). On Windows it happens when the system is short of resources: run fewer builds at once, or fewer render processes |
| `note: frame <i> drawn again after <ErrorType>: <error>` | code (`render._result`) | Not an error yet: Windows refused a pipe message (WinError 1450) or a worker ran short of memory for a moment, and the frame was drawn again, up to 6 tries (`POOL_TRIES`). If the render then fails with that error, run fewer builds at once or pass fewer processes (`run_all.py full 2 ...`) |

Any other exception from a worker belongs to the frame: your `draw(t)` failed at that time. Route it with `qa.py owner --traceback`.

## Stage refusals

`run_all.py audio` reuses `video.mp4` and draws no film. It refuses, with exit 1:

- `` no video.mp4 here: run `run_all.py full` first `` (seen): there is no picture yet. Run `full`.
- `video.mp4 was rendered at 640x360, 30 fps, SS 1, 240 frames; this run is 1920x1080, 30 fps, SS 1, 240 frames: pass the same --size, --fps and --ss, or run run_all.py full` (seen): the flags are not the render's. Run `audio` again with the render's own flags.
- `video.mp4 predates scenes.py: frame 150 (5.00 s) and 2 more of 9 checked differ from frames.hash (or its size, fps, SS or length): run run_all.py full` (seen after a change to the end card's ground colour): the picture changed since the render. `picture_is_current` draws the first, middle and last frame of each scene again, at most 12, and compares them with `frames.hash`. Run `full`.

Every refusal comes before the stage's clean-up and before `build.json` is written, so the last build is left as it was (seen: after the size refusal, `out.mp4`, the mixes, `video.mp4`, `frames.hash`, `thumbs.npy` and `build.json` were byte for byte the same).

`run_all.py full --redraw T0-T1`:

- `run_all.py: error: --redraw needs --keep-frames (and frames/ from an earlier --keep-frames run)` (seen, exit 2): add `--keep-frames`.
- `FileNotFoundError: frames/ lacks 210 of the frames to reuse (first frames\f00000.png): run once with keep_frames and no redraw` (seen on Windows): no earlier `--keep-frames` run left the PNGs. Run `full --keep-frames` once, then `full --keep-frames --redraw T0-T1`.

Frames read back from `frames/` are checked for size only. A PNG left from an older `scenes.py` goes into the film unseen until `qa.py approve`, `qa.py diff` or `run_all.py audio` draws key frames again, so redraw every passage a change touches.

`a 0.3 MB budget leaves no video bitrate for 8 s with 320 kb/s of audio` (seen with `--budget-mb 0.3`, exit 1): the budget cannot hold even the AAC audio (`run_all.caps`). The check comes before the clean-up, so the last render is left as it was (seen). Ask for the real limit, or shorten the piece; the formula is in [formats.md](formats.md).

## Checking a file by hand

**`not checked here: safe area, overlap, contrast, reading holds and cue sync (pass --scenes . with a text_items(t) registry and CUES in scenes.py)`.** `qa.py check` ran without `--scenes`, so the text gates, the text recorder, Q901, Q902 and the cut scan made no row: they are missing, not passed. Seen on the template: 26 rows without `--scenes`, 44 with it. Run it from the working folder with `--scenes .`, the build's `--size` and `--fps`, and `--bpm` for a music piece.

**`FIX  Q1105 decoded file against the drawn frames: worst 60.95 levels mean at 7.97 s, 30 of 240 frames over 4`**, on a file that is not broken. Without `--scenes`, `qa.py check` takes the file's own folder as the build folder (`contract.Ctx`), and Q1105 compares the file with the `thumbs.npy` it finds there. Seen when a file from another build was copied into a working folder and checked there. A Q1105 like that means the `thumbs.npy` beside the file belongs to another render: check each file in its own working folder, after the render that made it. The same goes for an encode ladder file checked beside an older render's `frames.hash` and `thumbs.npy` ([engine.md](engine.md), rung b).

**`NOT CHECKED Q502  the last frame did not decode (...), so it was not measured`** (Q501 says the same of the first frame). Seen on 2026-11-01 on a copy of the template cut to 40 percent of its bytes, with `NOT CHECKED Q503  the decode failed (decoded 88 of the 240 frames ffprobe counts in ...)`, a Q100 row for `qa_scan`, and `QA: NOT CHECKED (3)`, exit 2. ffprobe still counts every frame, but ffmpeg cannot decode the end of the file. The file is damaged or incomplete, such as a copy that had not finished or a render stopped half way. Render it again, and never check a partial copy.

**A short decode.** Every decode the gates make must hold each frame ffprobe counts, within 1 (`contract.Ctx._counted`). When it does not, the decode raises `decoded <k> of the <n> frames ffprobe counts in <file>`, the gate modules that asked for it give Q100 rows and Q503 reads NOT CHECKED, rather than a gate passing on part of the film (code). Treat it as a damaged file.

**`NOT CHECKED Q100  <module> raised <ErrorType> at <file>:<line>: <error>; its gates did not run`** (code, `qa._module_row`). One gate module (`qa_scan`, `qa_stack`, `qa_sync`, `qa_registry` or `qa_approve`) raised, so none of its codes ran; the others did. A module that does not import also prints `qa.py: <module> did not import (...)` first. Fix the cause the message names, at the file and line it gives.

**Characters outside ASCII.** Rows print in ASCII only (`contract.line`), and `qa.py` and `run_all.py` set their output to escape what the console cannot show, so no character stops a run. A registered title of `Ship it`, an arrow and `now` printed as `'Ship it \u2192 now'` (seen). The text on screen is right; read the escape back before comparing it with the scenario.

## Approval, diff and verify

`qa.py approve --review <reply>` exits 0 with an `APPROVED ...` line, 1 when it refuses, and 2 when it cannot approve (`qa_approve.approve`). A refused or failed approve records nothing.

**`REFUSED: ...`** (exit 1): the reply or the QA record does not fit this file.

| REFUSED reason (seen unless marked) | Next step |
|---|---|
| `no reviewer verdict: pass --review <file holding the reviewer's reply>` | Save the final reviewer's reply verbatim in a file and pass it |
| `the review says REVIEW FIX`, or `the review says no REVIEW PASS or REVIEW FIX line` (code) | The final review has not passed, or the file holds no reply: send the findings to the builder, or save the reply again verbatim |
| `the review is a proof-stage review; approve after the final review` | Approve only after a final review |
| `the review names no stage (want 'stage: final'); approve after the final review` (code) | The reply lost its `stage:` line: save it again, verbatim |
| `the review is of proof.png, not out.mp4` | The reply names another file. It must name the file under approval as `qa.py check` printed it |
| `the review names no file (want 'file: <name> (written <time>)' as qa.py check prints it)` (code) | As above |
| `the review saw a file written 2026-11-01 19:00:00; out.mp4 was written 2026-11-01 19:22:06` | The file was rendered again after the review, or the time was typed by hand. Run a fresh final review on the file as it is now |
| `the review gives no written time for the file (want '(written YYYY-MM-DD HH:MM:SS')` (code) | As above |
| `qa.json has FIX rows: Q502`, or `qa.json has NOT CHECKED rows: ...` | Fix those rows and render again. On the encode ladder, the expected Q705, Q707 and Q708 rows need `--override "<why>"` |
| `qa.json is older than out.rejected.mp4: run qa.py check on it again with --json qa.json` | Run `qa.py check ... --json qa.json` on the current file |

`--override "<why>"` approves in spite of a refusal and keeps the reason in `approval.json`; `qa.py check` then shows a Q1301 NOTE until a clean review is approved. Use it only for a decision someone made, never to pass a FIX.

**`CANNOT APPROVE: ...`** (exit 2): an input is missing or is not from this build.

| CANNOT APPROVE reason (seen unless marked) | Next step |
|---|---|
| `no out.mp4: render it first (python run_all.py full)` with `no frames.hash and thumbs.npy: render with run_all.py full, which writes both` (after a proof only) | Render with `full` |
| `frames.hash does not match draw(t) at 5 of 14 key frames (first 5.00 s): scenes.py changed after the render, or the render ran at another size than 640x360 SS 1; re-render, then approve` | `scenes.py` changed after the reviewed render: render again, review again, then approve |
| `no scenes.py here: pass --scenes <working folder>`, `no review file <path>` (code) | Run it in the working folder, with the reply's real path |
| `<file> runs at <rate> fps, the build at <fps>`, `<file> is <WxH>, the build <WxH>`, `<file> has <n> frames, frames.hash <m>: not the same render`, `thumbs.npy has <n> frames, frames.hash <m>`, `frames.hash is ...: render again at the build's size` (code) | The file and the build records come from different renders: render once more with the build's flags |
| `scenes.py did not draw: <error>` (code) | Fix the error; `run_all.py proof` shows it |
| `CANNOT APPROVE (PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'approved' -> 'approved.old')` | A folder in use on Windows: see below |
| `approved.new/ is left from an earlier approve and cannot be removed (a file in it is open)` (code) | As below |

**Windows: a folder in use.** Approve writes the new approval into `approved.new/` and puts it in place with two renames (`qa_approve._swap`). Windows will not rename a folder that a program has as its current folder, or holds a file open in. Seen with a process whose current folder was `approved/`: the PermissionError line above, exit 2, `approved.new/` left behind, and the old `approved/` still whole. Close every terminal, editor and viewer whose current folder or open file is inside `approved/`, `approved.new/` or `approved.old/` (or `cd` out), then run approve again; the rerun removed `approved.new/` and approved. A leftover it cannot remove reads `approved.old/ is left from an earlier approve and cannot be removed (a file in it is open)` (code). `qa.py diff` keeps going instead: a `review/diff_*.jpg` open in a viewer stays, with `warning: <n> sheets from an earlier diff are open in another program and stay: ...`, and the new sheet gets a numbered name (code).

**A stale approval, Q1301.** Once a build is approved, `qa.py check` draws the approved key frames again. Seen after a change to the end card's ground colour: `FIX  Q1301 STALE APPROVAL: scenes end changed since the approval of 2026-11-01 19:25:18 (key frames differ at 5.00, 6.47, 6.67, 6.77 s in end; source changed: scenes.py); the file is still the approved one`. Its fix names the windows to review, here `qa.py diff --expect 5-8`. The builder reports each change with its windows, a fresh final reviewer runs the diff on them, and the main chat approves the new reply. Other forms, from `qa_approve.approval_rows`:

- `only the audio changed since approval (decoded video streamhash matches)...` (a NOTE): check the audio rows, then approve again to bind the new file.
- `the file's picture is not the approved one (decoded video streamhash differs) though every key frame is; the last render's frames.hash matches the approved one, so only the encode changed (CRF, preset, ffmpeg)`: look at the encoded file again at the review times with `qa.py look`, then approve.
- `...: it was rendered from another state of the source, or the change sits between key frames`: render from the current source; `qa.py diff` shows which frames differ.
- `NOT CHECKED Q1301 approved/ does not match approval.json: ... missing or changed since the approval`: a file in `approved/` was edited, or an approve stopped half way. Never edit `approved/` by hand; approve again after a review.

**Q1304, the frame size or the environment.** `frame size changed since approval: re-approve (...)` (NOT CHECKED): at another size every frame differs, so the film needs a full review. `environment changed since approval (...) and frames moved (...)` (NOT CHECKED): Python's major.minor version, Pillow, numpy or a font file changed and key frames moved; review in full, then approve. The same change with no key frame moved is a NOTE, and the approval stands (code).

**`qa.py diff --expect <t0-t1,...>`.** It draws every frame and compares each 100 ms block of `mix_raw.wav` with the approval. A window holds frames `frame_of(t0)` to `frame_of(t1) - 1`, so `--expect 2.5-5` does not hold the frame at 5.00 s. The diff reads `mix_raw.wav` as the last render wrote it and never rebuilds the mix. Its last line:

| DIFF line | Exit | Next step |
|---|---|---|
| `DIFF: SAME as the approval` (code) | 0 | Nothing changed |
| `DIFF: CHANGED, every change declared with --expect (re-review each NOTE above)` (seen with `--expect 5-8`) | 0 | Read the triptychs in `review/`, then the file 0.5 s either side |
| `DIFF: FIX (1 undeclared change; 1 --expect window saw no change)` (seen with `--expect 2-5`) | 1 | The change list missed a change: review it too. A `declared change not found` row means a fix did not land: check the edit was saved, in the right scene |
| `DIFF: NOT CHECKED (could not compare; this says nothing about whether the build changed)` (code) | 2 | Nothing was compared: review the whole film |

**`VERIFY: DIFFERS <file> is not the approved file (sha256 <hash>, approved <hash>); ...`** (exit 1). Seen on a render made after an approval, ending `its picture differs too (decoded video streamhash differs)`. The file at hand is not the one the reviewer passed: deliver the approved file, or review and approve the new one. The other ending, `its picture is identical (decoded video streamhash matches): only the audio or the container changed` (code), also needs an approval before delivery. `VERIFY: NOT CHECKED (...)` (exit 2) means there is no approval, or no such file. Delivery needs `VERIFY: SAME`.

## Slow builds and big files

What the code offers. Times are of the picture step (its `wrote video.mp4 ... in <s> s` line), on the template, on 2026-11-01, on a machine with 32 logical CPUs.

| Lever | What it does | Measured |
|---|---|---|
| `procs`: `run_all.py full <N>` | The number of render processes; the default is a quarter of the logical CPUs, from 1 to 8 (`render.default_procs`) | At 1920x1080: 16.7 s with 1, 10.2 s with 2, 5.5 s with the default of 8. A second run the same day: 6.0 s, and 17 s for the whole stage |
| Builds sharing a machine | Each build starts its own pool | Twelve 640x360 builds at once, with 2 processes each: 7.2 to 8.7 s each, against 1.7 to 2.0 s for one build alone. In a batch, give each builder fewer processes |
| `--ss <N>` | Draws each frame N times larger, then scales it down | At 1920x1080, `--ss 2` took 17.0 s against 5.5 s, and the whole stage 41 s against 16 s. Keep it for thin lines and small text, and pass the same `--ss` to every stage |
| `STATIC = [(t0, t1), ...]` in `scenes.py` | Draws a hold once. It samples the span first (`render.static_reuse`); when one sample moved, every frame of the span is drawn | On the template's drifting end card: `warning: STATIC (5, 8) s moves (frame 180 differs from frame 150): every frame of it is drawn`. Declare only frames that truly hold. `--keep-frames` turns `STATIC` off |
| `--keep-frames`, then `--keep-frames --redraw T0-T1` | Keeps every frame as a PNG in `frames/`, then draws only the named passages again | No saving at 640x360 (2.3 s, then 2.5 s): the template's frames are cheap to draw. The saving grows with what a frame costs |

A big file:

- Set the limit as `BUDGET_MB = N` in `scenes.py` or as `run_all.py full --budget-mb N`. `run_all.caps` turns it into an x264 bitrate cap, which is a cap and not a guarantee. A Q1001 FIX means the file is over it; its fix reads `raise CRF to 20, drop grain, or go 720p`. A Q1002 NOTE is a bitrate over 12 Mb/s, and its fix names baked-in grain as the usual cause. What to cut first to shrink a file is in [formats.md](formats.md). The template came out at 0.4 MB and 0.4 Mb/s at 1920x1080.
- CRF: `run_all.py full` encodes with the `CRF` in the working copy of `run_all.py` (18, or 20 for grain-heavy styles). `render.CRF` is only the default for code that calls `render.render_to_ffmpeg` itself. In a scratch copy at 640x360, `render.CRF = 40` left `video.mp4` at 52,903 bytes, the same as at 18; `CRF = 40` in `run_all.py` made it 21,054 bytes.

## When nothing here fits

Read the row's `->` fix and its code's section in [qa-gates.md](qa-gates.md). For a traceback, `python qa.py owner --traceback <file>` names the function to read first. The builder stops after three runs that do not pass and reports what is left ([builder.md](../../../agents/builder.md)); the reviewer puts what no gate could settle under `cannot verify:` ([reviewer.md](../../../agents/reviewer.md)).
