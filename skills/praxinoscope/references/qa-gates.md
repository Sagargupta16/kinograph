# QA gates

This page is the reference for every coded check the engine makes. The skill sends readers here for the Q codes, what scenes.py declares, review times and approval; the [builder](../../../agents/builder.md) reads it for the codes and the declarations, and the [reviewer](../../../agents/reviewer.md) for the codes. The one table of codes is `contract.CODES` in [contract.py](../engine/contract.py): for each code it holds the owner module (the module whose function makes the row), the gate number, the status on failure and a one-line meaning. Every code in it has a row on this page. A new code needs its row here and a planted-fault fixture in `engine/qa_fixtures/` ([CLAUDE.md](../../../CLAUDE.md), [CONTRIBUTING.md](../../../CONTRIBUTING.md)).

Numbers come from the engine code, with the constant or function named, or from runs of the shipped template on 2026-11-01. Commands run from the working folder, where `python` means `uv run --no-project --with-requirements requirements.txt python`.

## Where the gates run

Every gate runs on the user's machine, with Python, Pillow, numpy and the ffmpeg and ffprobe the engine finds. No gate module opens a network connection.

| Step | What it reads | Codes it makes |
|---|---|---|
| `run_all.py proof` | Drawn frames only, before any encode (`qa.proof_rows`, `qa_purity.run`, `qa_lint.run`) | Q501, Q200 to Q209, Q301, Q401 to Q404, Q1201 to Q1206, Q904, Q905 |
| `run_all.py full` and `audio` | The master, then `thumbs.npy` (every drawn frame, before the encode), then the finished file through `qa.check` | Q805, Q1101 to Q1104 on `thumbs.npy`, then every `qa.py check` code |
| `qa.py check <file>` | The file, and with `--scenes` its scenes.py and the build files | 47 of the 58 codes: all but Q805, Q904, Q905, Q906, Q1201 to Q1206 and Q1303 |
| `qa.py purity`, `qa.py lint` | The proof gates on their own | Q1201; Q1202 to Q1206, Q904, Q905 |
| `qa.py calib` | A 4 s test clip through the master and the mux | Q906 |
| `qa.py diff` | Every frame and every 100 ms audio block against the approval | Q1303, Q1304 |

The flash gate can also run on drawn frames before a render: `qa.flash_report(draw, DURATION, fps=FPS)` over the film and `qa.flash_window(draw, t0, t1, fps=FPS)` over one passage return the same Q601 to Q603 rows as the file check. Both default to 30 fps.

### The verdict

- `run_all.py proof` prints every row and a `PROOF:` line, and exits 0 when clear, 1 on any FIX, else 2 on any NOT CHECKED.
- `run_all.py full` and `run_all.py audio` collect the master's Q805 row, the scans of `thumbs.npy` and every `qa.check` row. Any FIX or NOT CHECKED row outside the approval codes moves the file to `<name>.rejected.mp4` and prints `REJECTED <path>: <code> <status>, ...`; a run that breaks before the verdict leaves `<name>.unchecked.mp4`. Neither is delivered.
- The approval codes (Q1301 to Q1304, and a Q100 row raised by `qa_approve`) are a review state, never a defect of the file (`run_all.is_approval`). They print as `approval current|note|stale|unknown: <code> <message> -> <fix>` and decide the APPROVAL line: `APPROVAL: none yet -> final review, then qa.py approve`, `APPROVAL: current -> ...` or `APPROVAL: stale: <code> <item> -> re-review the changed scenes, then qa.py approve`. A clean run then ends with one `DELIVERED <path> (<MB> MB, <s> s, <LUFS> LUFS, <dBTP> dBTP)` line.
- `qa.py approve` refuses a build whose `qa.json` holds a FIX or NOT CHECKED row outside the approval codes (see Approval).

## qa.py check

### Arguments

| Flag | What it does |
|---|---|
| `video` | The file to check |
| `--scenes <folder>` | The working folder: imports its scenes.py, reads its build files, and lets the gates write `review_times.json` there |
| `--size WxH` | Q703 against it |
| `--fps N` | Q702 against it |
| `--duration S` | Q701 against it; with `--scenes` and no `--duration`, `DURATION` is used |
| `--bpm N` | The beat grid for Q901; with `--scenes` and no `--bpm`, `scenes.BPM` is used |
| `--max-mb N` | The Q1001 cap; without it, `scenes.BUDGET_MB` |
| `--silent` | The piece has no audio on purpose; `scenes.SILENT` counts the same |
| `--json <path>` | Also writes every row as JSON, and with `--scenes` adds each finding's moment to `review_times.json` |
| `--registry-procs N` | Processes for the text recorder's sampling pass (from `qa_registry.add_check_args`; 1 or less means none). Default: up to 8, and only when one process would take over 20 s |
| `--baseline <qa.json>` | The `qa.json` the approval kept (`approved/qa.json`): Q1302 against it (from `qa_approve.add_check_args`) |

### What it prints

1. `qa check: <video> (written YYYY-MM-DD HH:MM:SS, <size> MB)`. The written time is the file's local modified time; the final review quotes it, and `qa.py approve` holds the review to it within 1 s.
2. Progress lines from the text recorder, for example `qa_registry: drew 66 of 240 frames (38 in transitions and changeovers, 28 more on the 0.25 s grid) in 2.6 s on 1 process; 84 text calls, 84 records on frames` (template at 1920x1080, 2026-11-01).
3. One line per row (`contract.line`): the status padded to 4, the code padded to 5, the message, then ` [worst <t> s]` on a row that did not pass and names a moment, ` [<n> checked]` when the gate says how many items it looked at, and ` -> <fix>` on a row that did not pass. At most 10 rows of one code are printed; the rest are counted on one line, `<n> more <code> rows like these (every row is in --json)`.
4. The summary (`contract.summary`): `QA: PASS (44 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)` on the template, 2026-11-01. The state is `FIX (<n>)` when any row is FIX, else `NOT CHECKED (<n>)` when any is, else `PASS`.
5. Without `--scenes`: `not checked here: safe area, overlap, contrast, reading holds and cue sync (pass --scenes . with a text_items(t) registry and CUES in scenes.py)`.
6. Always: `not checked by any script: how it looks and sounds to a person (the reviewer looks; nobody has listened)`.

Output is ASCII only. `contract.line` writes any other character as a backslash escape, and qa.py sets stdout and stderr to escape what the console cannot show, so a registered string with an arrow or a Greek letter never stops a check on a redirected Windows console.

### The four statuses

| Status | Means | For delivery |
|---|---|---|
| PASS | The gate measured and the value is inside its limit | Nothing to do |
| NOTE | A pointer for the reviewer: something to look at, a taste rule, or a value inside a soft window | Never blocks; goes into the delivery report as a weak spot |
| FIX | A measured defect | Blocks: the build is rejected and `qa.py approve` refuses it |
| NOT CHECKED | The gate could not run, or had nothing to look at and nothing declared it so (`considered` 0 with no opt-out) | Blocks like a FIX: the build is rejected, and the run cannot be called clean |

### Exit codes

`contract.exit_code`: 0 when no row is FIX or NOT CHECKED (NOTE rows allowed), 1 when any row is FIX, 2 when some row is NOT CHECKED and none is FIX. With no ffmpeg, check and look stop with `qa.py: no ffmpeg on PATH (nor in /opt/homebrew/bin or /usr/local/bin)` and exit 1.

### --json

`--json <path>` writes a list with one object per row (`contract.write_rows`), with these keys: `status`, `code`, `msg`, `fix` (empty on a PASS), `t0` and `t1` (the first and last second the finding covers), `worst_t` (the moment to open first), `item` (the string, cue label, scene or file that failed), `metric` (the measured number), `limit` (what it was held to), `spans` (merged runs of frames as `[t0, t1]` pairs) and `considered` (how many items the gate looked at). The builder writes it to `qa.json`; `qa.py approve` keeps that file as the baseline.

### What --scenes adds

With `--scenes <folder>`, check sets `engine.W`, `engine.H` and `engine.FPS` from the file and `engine.SS` from `build.json`, then imports the folder's scenes.py. It reads `SCHEDULE`, `DURATION`, `BPM`, `SILENT` and `BUDGET_MB`, and runs:

- Q901 (when there is a BPM) and the text gates Q200 to Q207, Q301 and Q401 to Q404 on every frame;
- the text recorder (Q204 to Q206, Q208, Q209);
- Q902, and Q903's NOT CHECKED row when the folder has no `mix.wav`;
- Q1103, and the `ALLOW`, `CUE_LAG`, `WINDOWS`, `HOLDS` and `STATIC` declarations every scan reads;
- the `payoff` cues of Q804.

Without it those rows are missing, not NOT CHECKED, and the extra line under the summary says so. Q1105, Q802's cue names, Q804, Q903's mux rows and the approval rows still read build files from the file's own folder when they are there: `contract.Ctx` uses that folder as the working folder.

### What it adds to review_times.json

Only into a folder named with `--scenes` (`Ctx.record`):

- `qa_scan` adds its own findings on every check: kind `pop` with a strip for Q1101 (the strongest pop and each pop of the row, folded ones included), kind `finding` for the rest, and for Q601 and Q602 the middle of every passage too.
- With `--json` as well, every other row that is not PASS and names a `worst_t` becomes a `finding` entry: reason `<code> <status> <item>` (the message when there is no item), its status, and a strip for Q203, Q207 and Q404 (`qa.STRIP`). Codes owned by `qa_scan` are left to it (`qa.RECORDS_OWN`).

### ffmpeg and the decode

`contract.find_ffmpeg` takes the ffmpeg on PATH, else `/opt/homebrew/bin/ffmpeg`, else `/usr/local/bin/ffmpeg`, and ffprobe is the file beside it with the same name pattern. `run_all.py` has its own finder with the same places, and puts that folder on PATH. Every gate module reads the file through one `contract.Ctx`, decoded once per need with stdin closed: RGB at 192x108 as a player shows it (`DECODE_709`), linear light at 192x108 for the flash gate (`DECODE_LINEAR`), grey from that RGB, and the audio at the rate a gate asks for. Each picture decode must hold every frame ffprobe counts, within 1 (`Ctx._counted`): a short decode raises, so the gate module that asked reports Q100, or Q503 reads NOT CHECKED, rather than a gate passing on part of the film. The full-size decodes of frame 0 and the last frame for Q501 and Q502 (`qa.frame_grey`) say NOT CHECKED when they fail, as Q503 does, so a file whose last second will not decode ends with a NOT CHECKED verdict, not a traceback.

## The codes

There are 58 codes: 35 fail as FIX, 19 as NOTE and 4 as NOT CHECKED (`contract.CODES`, counted 2026-11-01). The gate numbers 0 to 10 group them; the families below follow the order a review usually takes. In the tables, "Module" is the owner `contract.CODES` names and "Fails as" is the status it gives; a row may say NOT CHECKED instead when its inputs are missing.

### Gate 0: a gate module that raised

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q100 | 0 | qa | NOT CHECKED | A gate module (`qa_scan`, `qa_stack`, `qa_sync`, `qa_registry` or `qa_approve`, in that order, `contract.GATE_MODULES`) raised inside `check_rows`, so none of its codes ran. The item names the module; the message gives the error and the deepest engine file and line it came from |

The other modules still run (`qa._module_row`), and `run_all.py` turns a crash of the thumbs scan into the same row (`run_all.guarded`). A module that does not even import makes qa.py print `qa.py: <module> did not import (...)` on stderr, and check reports it as Q100.

### Frame scans and pops

Q1101 to Q1104 read 192x108 grey frames (PIL luma) and are pointers for the reviewer: all NOTE, all honour `ALLOW`. A full build runs them twice, on `thumbs.npy` before the encode (`qa_scan.scan_thumbs`) and on the decoded file. Each scan keeps its 5 strongest rows (`MAX_ROWS`) and folds the rest into one row that lists their times. Q1105 compares the file with what was drawn.

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q1101 | 1 | qa_scan | NOTE | One-frame pop: a frame that changes into and out of itself while its neighbours agree, strong enough that 0.2 percent of all pixels or more sit 12 levels off both neighbours on the popping tiles |
| Q1102 | 1 | qa_scan | NOTE | Frozen run: under 0.2 percent of pixels move more than 6 levels for 3 s or more, outside holds, the end tail and `ALLOW` |
| Q1103 | 1 | qa_scan | NOTE | A hard cut that no SCHEDULE start, CUTS time, cue or transition window explains |
| Q1104 | 1 | qa_scan | NOTE | Stall: a frame that repeats the one before while both steps around it move |
| Q1105 | 1 | qa_scan | FIX | The decoded file does not match `thumbs.npy`: a frame whose mean grey differs by more than 4 levels (`MATCH`), or a different frame count (a wrong-size or sheared encode) |

- **Q1101** (`qa_scan._pops`, `POP`, `STRONG`): on a 12 x 12 tile grid, a tile pops when 0.004 or more of its pixels change by more than 4 levels both into and out of the frame while the change across it (f - 1 to f + 1) is at most 0.35 of the smaller step, and the same holds on its 3 x 3 tile neighbourhood at 0.5. A tile that also pops on a neighbouring frame is alternation, and one whose steps either side change by 0.25 of its pop step or more is motion passing through; neither counts. Three or more pop frames within 3 frames are one fast mover, not pops. Pops under 1 s apart make one row. The message says "whole-frame" when over 1 percent of all pixels sit 12 levels off both neighbours, else "local", with the tile rows and columns.
- **Q1102** (`_frozen`, `STILL`): still means under 0.2 percent of pixels leave the 3 x 3 range of the other frame by 6 levels, frame to frame and against the run's first frame, so a slow draw-on is not frozen. Not counted: near-black runs (the median share of pixels above 25/255 is under 2 percent), registry rests and `HOLDS` and `STATIC` spans with 2 frames either side, the last 2 s plus a frame (the end card), and `ALLOW` spans.
- **Q1103** (`_cut_frames`, `CUT`, `DARK_CUT`): a hard cut is a step where over 30 percent of pixels change by more than 12 levels with a mean change over 18 levels and over 3 times the median of the 5 steps either side, or a dark cut (over 30 percent by more than 6 levels, mean over 6, over 4 times the median); either must be at least twice its larger neighbouring step. A cut answered within 3 frames by a cut back to the picture before it is a flash, not a cut. A cut passes when it is within 1 frame of a SCHEDULE start or CUTS time, between 1 frame before a cue and `CUE_LAG` + 1 frames after it, inside a `WINDOWS` span (1 frame slack) or in `ALLOW`. Cut frames within 2 frames of each other are one row. With a scenes.py that has no SCHEDULE, CUTS or CUES the row is NOT CHECKED; without `--scenes` there is no row.
- **Q1104** (`_stalls`, `STALL`): the pixels that move more than 4 levels in both neighbouring steps (at least 0.5 percent of the frame) move into the frame under 5 percent of the time, or the step into it changes under 0.05 levels on average (an exact repeat); both neighbouring steps move over 0.8 levels on average; and no other repeat sits within 6 frames, so animation on twos is not a stall. Not counted: a held flash (the frame after returns to the one 2 before), inside a transition window, up to 2 frames after a SCHEDULE start or CUTS time, and `ALLOW`.
- **Q1105** (`match_rows`): no `thumbs.npy` and no `frames.hash` gives no row (not a build); `frames.hash` without `thumbs.npy` is NOT CHECKED. The template read worst 1.00 levels mean at 1920x1080 and 1.05 at 1080x1920, 0 of 240 frames over 4 (2026-11-01).

### Gate 6: flashes

WCAG 2.2 success criterion 2.3.1 (Three Flashes or Below Threshold) allows at most three flashes in any one second unless they stay under its general flash and red flash thresholds. `qa_scan.flash_rows` implements those definitions on the linear-light decode:

- **Luminance.** The file's RGB is read as sRGB code values, turned to linear light and only then averaged down to 192x108 (`DECODE_LINEAR`), so sparse bright lines are not underrated. Relative luminance uses the WCAG weights 0.2126, 0.7152, 0.0722 (`Y_W`).
- **General transition.** A swing of relative luminance by 0.1 or more of the maximum (`STEP`), where the darker of its two states is under 0.8 (`DARK`). A flash is a pair of opposing transitions, so the limit is more than 6 transitions in any sliding 1 s window (`MAX_T`); the row reports flashes as transitions / 2.
- **Red transition.** One state has R / (R + G + B) of 0.8 or more and the two states are more than 0.2 apart in CIE 1976 u'v' (`RED_UV`); a state too dark for a chromaticity (luminance under 0.005) counts against a lit one. The saturated-red measure (R - G - B) x 320 must also move by 1.0 or more (`RED_STEP`), which keeps noise out.
- **Area.** A transition counts where the cells that moved together cover a quarter of the frame or of one 10 degree window (`AREA`). The window is WCAG's 341 x 256 field on a 1024 x 768 view with the frame fitted into that view (`_window`): about a third of the width by 0.44 of the height at 16:9, 0.79 of the width by a third of the height at 9:16. Every window position one cell apart is judged on its own, as is the whole frame. Cells are 4 x 4 pixels of the 192x108 decode (`CELLS`).
- **Runs.** A window's mean is split into runs at its extremes; a reversal smaller than 0.005 in luminance or 1.0 in the red measure (`HYST`) does not end a run, so shimmer does not count.

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q601 | 6 | qa_scan | FIX | More than 6 general transitions (3 flashes) in any sliding second, over a quarter of the frame or of one 10 degree window |
| Q602 | 6 | qa_scan | FIX | More than 6 red transitions in any sliding second, by the same area rule |
| Q603 | 6 | qa_scan | NOTE | Extended band: 4 to 6 transitions in the trailing second, held for 4 s of any 5 s (`EXT`); an `ALLOW` span holding the whole passage within 1 s clears it |

A FIX row names the worst second, the window position as percentages of the frame and how many passages are over the limit. Fewer than 2 frames makes all three NOT CHECKED. The template read worst 0.5 general and 0 red flashes in any second (2026-11-01). No tool certifies photosensitivity safety; the delivery report says so ([delivery.md](delivery.md)).

### Gate 2: text placement

The text gates read `text_items(t)` on every frame of `DURATION`. An item is at rest at alpha 0.98 or more (`qa.FULL`) and on screen above 0.05 (`qa.VISIBLE`); `texture=True` items are skipped. Sizes are scaled by 1080 / min(W, H), so the rules read as written at any aspect. One row per string or pair that fails, with every frame it fails on as spans; one PASS row per clean code.

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q200 | 2 | qa | NOT CHECKED | No `text_items(t)` and no `NO_TEXT`; or text_items reports nothing readable on any frame; or its items lack `s` and `box` (the older registry form, sampled every 0.5 s). Gates 2 to 4 did not run. PASS when `NO_TEXT` is declared |
| Q201 | 2 | qa | FIX | Text at rest whose box leaves the safe area, a 4 percent pad on every edge (`qa.inside`); metric is the px outside |
| Q202 | 2 | qa | FIX | Two different strings at rest whose boxes, each shrunk by 1 px, share area; metric is the shared px squared |
| Q203 | 2 | qa | FIX | The same while either of the two is fading (on screen but under 0.98) |
| Q204 | 2 | qa_registry | FIX | Drawn text that text_items(t) does not report. FIX when it is seen at alpha 0.5 or more, 24 px or more at 1080 and with a letter or digit (`READ_ALPHA`, `READ_PX`); NOTE otherwise |
| Q205 | 2 | qa_registry | FIX | A registry box more than 2 px (`BOX_PX`) from the drawn glyph box |
| Q206 | 2 | qa_registry | FIX | Registered text covered: under 0.7 (`EXPOSED`) of its ink shows |
| Q207 | 2 | qa | NOTE | Text replaced in one place with an empty gap of 3 frames up to under 0.5 s; a gap of 0 to 2 frames, or of 0.5 s or more, passes |
| Q208 | 2 | qa_registry | NOT CHECKED | The text recorder saw no text call in any sampled frame, so Q204 to Q206 and Q209 did not run (PASS with `NO_TEXT`); also when the recorder itself failed |
| Q209 | 2 | qa_registry | NOTE | text_items(t) reports text at alpha 0.5 or more that nothing drawn matches |

- **Q207** (`qa._changeover_rows`): for each run of a string on screen, the next run of a different string whose first box overlaps its last box is a changeover; the gap is the empty frames between them, a NOTE when it is over 2 frames and under fps / 2 (3 to 14 frames at 30 fps). `ALLOW['Q207']` lists the gap's middle.
- **Q204 to Q209** come from the text recorder, below. Q205 accepts a box from a textbbox (as tall as a drawn copy within 2 px) when every edge is within 2 px; any other box is hand-made and must hold the glyphs within 2 px and reach no more than 0.6 em past them (`HAND_EM`), because Q201 and Q202 judge the text by that box. Q206 tests the middle frame of every rest and the first frame of every pair of overlapping registered texts (where Q301, Q202 and Q203 look); a pixel is the text's when drawing the frame without it moves a channel by 8 levels (`CHANGED`). A text with under 12 ink px, drawn where its place is unknown, or that cannot be drawn without is not measurable; when under half the tests can be measured (`MEASURED`) the row is a NOTE, and when draw(t) gives other pixels on a second call inside a tested text it is NOT CHECKED. Q209 makes one NOTE per moment, and one more for items that give no alpha, where being off screen may be right.

### Gate 3: contrast

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q301 | 3 | qa | FIX | Text at rest under 4.5:1, or under 3:1 for large text (36 px or more at 1080, or 24 px or more with `bold`), against the pixels the frame really holds around its box |

`qa._contrast_rows` draws each rest at its second, middle (`contract.mid_frame`) and second-to-last frame, every frame of a rest 3 frames or shorter, at the build's supersampling. The background is the median colour of a ring 6 px wide just outside the box (`qa.ring_bg`), since the box itself is mostly glyph ink; the ratio is `qa.contrast`, the WCAG formula. A string that fails gets one row, at its lowest ratio against its minimum. A string at rest with no `fg` gives a NOT CHECKED row; values a ticker passes on the way are not sampled, and when only those ever rest the row is NOT CHECKED. The template's lowest was `'{handle or link}' 8.38:1 against 3:1` at 1920x1080 and `'{title}' 6.27:1 against 3:1` at 1080x1920 (2026-11-01).

### Gate 4: reading holds

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q401 | 4 | qa | FIX | A string's longest rest is shorter than the reading hold its profile needs |
| Q402 | 4 | qa | NOTE | Key text under 36 px at 1080, measured at the middle of its longest rest; `texture=True` if nobody must read it |
| Q403 | 4 | qa | FIX | A readable item whose alpha never reaches 0.98 (an eased fade that stops short, a ghost at half alpha) |
| Q404 | 4 | qa | FIX | At `reveal_end`, under 0.98 of the ink the string has at the end of its rest is drawn, or the ink stops more than 3 px (`INK_SLACK`) inside the left or right end of its box |

The hold rule (`qa.min_hold`): need = max(floor, 0.5 s + 0.3 s per word, characters / cps + pad), where characters count spaces and a run of white space counts once. The profile is the item's `profile`, else `HOLD_PROFILE`, else display (`qa.HOLD_PROFILES`):

| Profile | Characters a second | Pad | Floor | For |
|---|---|---|---|---|
| display | 20 | 0.5 s | 1.0 s | Titles, labels, end cards (the default) |
| caption | 17 | 0.5 s | 1.0 s | Lines read while the picture moves |
| slow | 15 | 1.0 s | 1.5 s | Dense explainers |

A dict as `HOLD_PROFILE` overrides display's numbers and reads as "custom"; an unknown name gives one NOT CHECKED row naming the profiles, and the other strings go on. `qa.py holds` applies the same rule to the storyboard before anything is built. The template's tightest was `'{title}' 1.80/1.00 s` (2026-11-01).

Tickers (`ticker=True`, `qa._ticker_passing`): a value whose every run hands over to another ticker value in the same place within 2 frames is on the way; it needs no hold and no contrast. The value a ticker settles on needs both. Q402 applies to every value.

Q404 counts as ink the pixels within 24 levels of `fg` inside the box padded by 2 px. It is NOT CHECKED when the item has no `fg`, `reveal_end` is outside the piece, the string never rests after `reveal_end`, or no pixel of its `fg` is in its box at rest.

### Gate 5: frame 0 and the end card

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q501 | 5 | qa | FIX | Frame 0 has a grey mean of 25 or less (dark) or a standard deviation of 12 or less (flat). NOT CHECKED when frame 0 does not decode |
| Q502 | 5 | qa | FIX | The last frame has a grey mean of 25 or less (a fade to black). NOT CHECKED when the last frame does not decode (a cut or damaged file) |
| Q503 | 5 | qa | NOTE | The last frame differs from the frame 1 s before it by 10/255 or more on average: the end card is not held 1 s |

At the proof Q501 reads the drawn frame 0 (`qa.first_frame`); on the file it decodes frame 0 at full size as a player shows it (`qa.frame_grey`, grey 0.299 R + 0.587 G + 0.114 B). Q502 decodes the last frame from the final second. Q503 compares the last frame with the one `round(fps)` frames before it on the 64x36 block grey of the decode, and is NOT CHECKED when that decode fails or comes back short. The selftest case `files.cut` cuts a clean file to 35 percent of its bytes: Q501 passes, and Q502 and Q503 read NOT CHECKED. Template at 1920x1080, 2026-11-01: frame 0 mean 71.0 and std 16.7 drawn, 70.3 and 16.9 decoded; last frame mean 61.5; last second change 0.4/255 (at 1080x1920: 69.9 and 16.6 drawn, 69.2 and 16.7 decoded, 61.5, 0.5/255).

### Gate 7: what ffprobe reports

All from one ffprobe run (`qa.probe`), except Q708.

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q701 | 7 | qa | FIX | Duration more than 0.10 s off `DURATION` or `--duration` (no row when neither is known) |
| Q702 | 7 | qa | FIX | Frame rate 0.01 or more off `--fps` (no row without it) |
| Q703 | 7 | qa | FIX | Width x height not `--size` (no row without it) |
| Q704 | 7 | qa | FIX | The stream's frame count more than 1 off round(duration x rate) (no row when the stream reports no count) |
| Q705 | 7 | qa | FIX | Pixel format not yuv420p |
| Q706 | 7 | qa | FIX | No audio stream (no row for a silent piece) |
| Q707 | 7 | qa | FIX | Colour tags not bt709 / bt709 / bt709 / tv (space, primaries, transfer, range; a missing tag reads `unknown`) |
| Q708 | 7 | qa | FIX | The colour chain round trip off by more than 8 levels |

Q705, Q707 and Q708 are for the H.264 deliverable: on any other codec all three are NOT CHECKED. Q708 (`qa.colour_round_trip`) encodes five flat swatches, (40, 180, 60), (192, 32, 32), (0, 255, 0), (30, 60, 200) and (128, 128, 128), through `contract.COLOR_VF` and `COLOR_FLAGS` with libx264 at CRF 18, decodes them with `DECODE_709` and takes the median of each swatch's core; it is NOT CHECKED when the encode or decode fails (an ffmpeg without libx264). It tests this machine's ffmpeg chain, not the file's own pixels. The template read `worst 1 levels, on swatch (40, 180, 60)` (2026-11-01).

### Gate 8: loudness, true peak and the master

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q801 | 8 | qa | FIX | Integrated loudness outside -14 +/- 1 LUFS |
| Q802 | 8 | qa_stack | FIX | True peak above -1 dBTP (`qa_stack.TP_MAX`), with the sounds that stack at the loudest moment |
| Q803 | 8 | qa | NOTE | A near-silent second inside the piece: RMS under -60 dBFS |
| Q804 | 8 | qa_stack | NOTE | Stacked sounds: heavy sounds within 3 frames, a crowded payoff, or more than 2 sounds in 100 ms |
| Q805 | 8 | audio | FIX | The master is not linear, or missed its loudness target |

- **Q801** comes from one ffmpeg `ebur128=peak=true` pass (`qa.loud`), which also keeps every 100 ms line for Q802. It runs only when the file has audio and the piece is not silent. Template: -14.1 LUFS (2026-11-01).
- **Q802** reads the true peak from the ebur128 Summary. The loudest moment is found channel by channel on the 4x oversampled 48 kHz decode, inside the loudest 100 ms frames (`qa_stack.moment`, `peak_moment`). A FIX row spans every 100 ms frame over -1 dBTP, names up to 8 cue sheet sounds sounding within 50 ms (span, gain, peak plus gain, level there, bus), the music bed and SFX bus levels there from `mix_raw.wav` and `sfx.wav`, and an order to cut the designed sounds within 20 dB of the loudest: impact, then chime or bell, then press or drop (`CUT_ORDER`, a house heuristic). `SILENT` makes it PASS; no loudness measured makes it NOT CHECKED. Template: -1.8 dBTP at 5.009 s (2026-11-01).
- **Q803** decodes the audio at 8 kHz mono and takes the RMS of each whole second; seconds 1 to n - 2 are inside. One NOTE per run of quiet seconds; `ALLOW` lists a time in the second. A piece under 3 s passes with nothing to measure; a stream that decodes to nothing is NOT CHECKED.
- **Q804** (`qa_stack.stack_rows`) counts every SFX-bus sound on the cue sheet and a music-bus sound only when it serves a CUES label; a muted sound counts for nothing. Heavy is the sheet's `heavy` flag, else a name with kick, hit, boom, impact or drop. A riser, swell, suck, reverse or whoosh whose end or landmark lands within 3 frames or 100 ms (whichever is longer) of a heavy sound is one gesture with it and does not count. NOTE for: 2 or more heavy sounds within 3 frames; 2 or more sounds on a `payoff=True` cue, counting those within 3 frames of it and a lead-in still sounding 0.1 s before it; more than 2 sounds in any 100 ms (a taste rule). No cue sheet is one NOTE; a sheet that cannot be read is NOT CHECKED; `ALLOW['Q804']` and `SILENT` clear it.
- **Q805** is made by `audio.master` inside `run_all.py full` and `audio`, not by `qa.py check`. The master applies one static gain to -14 LUFS and a 4x true-peak limiter at the ceiling (default `audio.CEILING`, -2.0 dBTP, with no added delay), then measures and nudges for up to 6 passes. FIX when the result misses -14 LUFS by more than 0.1 LU or the ceiling by more than 0.05 dB, when the limiter took more than 0.5 LU off the programme (`LINEAR_COST`) or more than 6 dB at one moment (`LINEAR_DEPTH`), or when the raw mix is silent. `run_all.master_and_mux` then measures the muxed file and masters again, at most 3 times, while its true peak is over -1.3 dBTP (-1 less the 0.3 dB meter tolerance), and keeps the clean master with the lowest peak. Template line, 2026-11-01: `master: ceiling -2.00 dBTP, mix.wav -14.0 LUFS at -2.00 dBTP (Q805 PASS) -> out.mp4 -14.1 LUFS at -1.80 dBTP`.

### Gate 9: sync

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q901 | 9 | qa | NOTE | A cut more than 1 frame from the nearest beat of the BPM grid |
| Q902 | 9 | qa_sync | FIX | A cue's sound late by more than one frame (never over 60 ms) or early by more than 40 ms, or missing; NOTE outside -5 to +15 ms and for the picture side |
| Q903 | 9 | qa_sync | FIX | The mux moved the audio: stream start times, or the decoded audio against `mix.wav`, more than 1 ms apart |
| Q904 | 9 | qa_lint | NOTE | A SCHEDULE, DURATION or CUES time more than 0.001 frame off the frame grid |
| Q905 | 9 | qa_lint | NOTE | One beat at `BPM` is not a whole number of frames |
| Q906 | 9 | qa_sync | FIX | The calibration clip's white frame and blip do not come back together |

- **Q901** (`qa.grid_rows`) needs a SCHEDULE and a BPM (`--bpm` or `scenes.BPM`). The cuts are `CUTS` when scenes.py has it, else every SCHEDULE start after 0. The beat is 60 / BPM; `ALLOW` lists a planned off-grid cut. Without `--scenes` there is no row.
- **Q902** (`qa_sync.cue_rows`) has three modes.
  - With a cue sheet (`cuesheet.json`, `cue_sounds.npz` and the stems `sfx.wav` or `mix_raw.wav`), each cue is matched to its sheet entries by label (nearest in time when a label repeats), else to unlabelled entries within 100 ms, SFX bus first. Each entry is found where it really sits on its stem by normalised cross-correlation in 250 Hz to 9 kHz (from 20 Hz on a lossless stem when the band misses), within 250 ms of the sheet's place, at a match of 0.7 or more; overlapping recorded neighbours are fitted out by least squares, and copies of one sound close together are measured as a group. The instant heard is the sound's landmark, or its audible attack at -15 dB when it was placed by its start or onset and the attack comes 5 ms or more later. Late past one frame (`late_limit`: 1000 / fps, at most 60 ms) or early past -40 ms is a FIX, outside -5 to +15 ms a NOTE; a cue no sound serves is a FIX, and a copy that cannot be told from its twins is NOT CHECKED. The picture side looks for the strong change nearest the cue frame (0.2 percent or more of pixels moving over 12 levels on the 192x108 grey), from 4 frames before to `CUE_LAG` + 2 after, inside the cue's `region=` box, else the box of the registry text that changes across the cue, else the whole frame; outside -1 to `CUE_LAG` + 1 frames, or no change, is a NOTE, and a whole frame where under 0.2 percent moves is "not measurable" (a NOTE). The decoded file confirms each sound within 20 ms; one NOTE when it moves confirmed cues by more than 2 ms. Template: `all 2 cues land: audio worst +0.0 ms on sfx.wav; the decoded file confirms 2 of 2 within 2 ms` (2026-11-01).
  - With no cue sheet, one NOTE row from an onset detector (a 3 dB rise in 10 ms windows within 100 ms of the cue, on the whole mix or above 2 kHz, or in the cue's own `band=`): a guess, not a measurement. It passes only when it finds every cue.
  - A silent piece, or CUES with picture cues only, measures the picture side alone.
  - `NO_CUES` makes it PASS. Empty or missing CUES is NOT CHECKED (a PASS for a silent piece), as are CUES in a form `contract.cues` cannot read, a sheet without its buffers or stems, and a sheet row with no `i`, `t` or `landmark_s`. NOTE rows honour `ALLOW['Q902']`. Without `--scenes` there is no row.
- **Q903** (`qa_sync.mux_rows`) needs both streams and a piece that is not silent. Rows: the audio and video `start_time` within 1 ms (a NOTE when ffprobe reports none); the decoded audio against `mix.wav` in three 2 s windows at 12, 45 and 85 percent, searched +/- 0.1 s after a 500 Hz high-pass, FIX past 1 ms, searched again over +/- 1 s at a match of 0.8 or more when no window matches, NOT CHECKED when none does; and the same against `mix_raw.wav`, which catches a delay in the master, a NOTE when unmatched. A build folder without `mix.wav` is NOT CHECKED. Template: `+0.00 ms at 12%, +0.00 ms at 45%, +0.00 ms at 85%` against both (2026-11-01).
- **Q904** and **Q905** run at the proof and in `qa.py lint` (`qa_lint.grid_rows`). Q904 reads every SCHEDULE start and end, `DURATION` and every cue time; `ALLOW['Q904']` within half a frame clears a planned one, and CUES it cannot read make it NOT CHECKED. Q905 passes when there is no BPM, and its fix lists the whole-frame tempos from 60 to 200 BPM at the build's rate (60, 72, 75, 90, 100, 120, 150, 180 and 200 at 30 fps). Template: `one beat at 120 BPM is 15 frames at 30 fps`.
- **Q906** is `qa.py calib` (`qa_sync.calib`): a 4 s clip, black but for one white frame at 2 s and quiet but for a one-frame 1 kHz blip on that frame over a 3 to 6 kHz noise bed, through `audio.master` and `contract.mux_cmd` (the mux `run_all.py` runs), read back as qa.py check reads a file. Three rows: the white frame comes back on its own frame; the blip lands within 1 ms of it (the row splits the offset into the master's part and the mux and AAC part); the two streams' `start_time` are within 1 ms. It reports where an offset entered and never writes one for the mixer to subtract.

### Gate 1: purity and lint

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q1201 | 1 | qa_purity | FIX | draw(t) is not pure: one frame, different pixels, depending on order or process |
| Q1202 | 1 | qa_lint | FIX | Unseeded randomness, a clock or entropy read, or `hash()` of a string, in scenes.py or a local module it imports |
| Q1203 | 1 | qa_lint | NOTE | Module state written inside a function: the next frame sees what this one left |
| Q1204 | 1 | qa_lint | NOTE | A top-level def or class in scenes.py named like something the engine defines or re-exports |
| Q1205 | 1 | qa_lint | NOTE | Text drawn, or a font loaded, outside the engine text helpers |
| Q1206 | 1 | qa_lint | NOTE | A colour literal inside a function, outside the palette block |

**Q1201** (`qa_purity.run`) picks at most 2 + 2n frames (n is `--n`, default 16): the first and last frame; both sides of the cuts (SCHEDULE starts and ends, CUTS, the edges of WINDOWS), spread over at most n / 2 cuts, then the frame after some of them; the midpoints of every window and scene, the CUES and KEY_TIMES, then even steps; plus every `--t` second and one frame every `--grid` seconds. It draws them three ways: in order in this process, reversed in a fresh `python -I` process (a new string hash seed, no PYTHON variables) at the same time, and through a spawn pool (2 to 4 processes) as the render does. Digests (`contract.frame_digest`) must match exactly. A FIX names how many frames differ, the worst frame, how many pixels differ, a diagnosis from fresh processes (drawn cold twice with one hash seed, cold with a second seed, twice in one process, and behind each of its 8 nearest samples) and the owning scene function. It is NOT CHECKED when scenes.py does not import, has no DURATION, a fresh process cannot draw it, a pass hangs for 240 s, or draw(t) raises. That holds for `qa.py purity`; inside `run_all.py proof` the text gates and the recorder draw first and are not guarded, so a draw(t) that raises stops the proof with its traceback and no `PROOF:` line. The row also says whether the lines the lint flags as Q1202 ran on any sampled frame. Template at the proof: `draw(t) pure: 24 frames ... at 1920x1080, 30 fps, SS 1 (3.2 s)` (2026-11-01).

**Q1202 to Q1206** (`qa_lint.run`) read the syntax trees of scenes.py and every local module it imports, skipping the engine's own files and `qa*` modules. Each row lists the first 5 sites as `file:line text in function`; `qa.py lint --all` lists every one.

- Q1202: `time.time`, `perf_counter`, `monotonic` and their kin, `datetime.now`, `today` and `utcnow`, `os.urandom`, `os.getpid`, `time.localtime` and the like called with no timestamp, `secrets.*`, `uuid.*` except `uuid3`, `uuid5` and `UUID`, the shared `random` stream or an unseeded `random.Random`, numpy's global stream or an unseeded generator, and `hash()` of a str or bytes (the hash seed changes per process).
- Q1203: a `global` written, an item or attribute of a module-level object written or deleted, a mutating method (`append`, `update`, `paste`, `putpixel` and others) on one, drawing onto a module-level image, drawing from a module-level random generator, and a mutable default argument. Code that runs only while the module imports is skipped.
- Q1204: a top-level def or class named like something `engine.py` defines or re-exports from its folder, or like something a star-imported local module defines.
- Q1205: `.text()` or `.multiline_text()` on an ImageDraw (a single-band mask image, or a number as the fill, is allowed), and loading a font with `ImageFont.truetype`, `FreeTypeFont`, `load_default`, `load` or `load_path` instead of `engine.font()`.
- Q1206: a hex colour string (`#rgb`, `#rgba`, `#rrggbb`, `#rrggbbaa`) inside a function or as a parameter default, or an RGB or RGBA tuple of ints from 0 to 255 passed to a colour keyword (`fill`, `color`, `colour`, `outline`, `stroke_fill`, `background`, `bg`, `fg`, `ink`, `col`, `tint`, `halo`) or used as a colour parameter's default. A fully transparent tuple, and three or four mixed decimal digits such as `#404`, do not count.

The lint's pragmas silence a meant finding: a comment `# praxinoscope: <tag>` on the finding's line, on the def line of the function holding it, or for Q1203 on the line that binds the module-level name.

| Tag | Clears |
|---|---|
| `rng-ok` | Q1202 |
| `state-ok` | Q1203 |
| `shadow-ok` | Q1204 |
| `text-ok` | Q1205 |
| `colour-ok` or `color-ok` | Q1206 |

Several tags may share one comment, separated by commas or spaces. Template: `LINT: PASS (7 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)` (2026-11-01).

### Gate 10: file size

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q1001 | 10 | qa | FIX | The file is over its size budget (MB of 1,000,000 bytes): `--max-mb`, else `scenes.BUDGET_MB`; `run_all.py full --budget-mb` passes its budget the same way. No budget is a PASS that says so |
| Q1002 | 10 | qa | NOTE | Bitrate (size x 8 / duration) over 12 Mb/s; flat graphics land at 1 to 5 |

Template: 0.4 MB, 0.4 Mb/s (2026-11-01). The budget's bitrate cap is in [formats.md](formats.md).

### Approval codes

| Code | Gate | Module | Fails as | Catches |
|---|---|---|---|---|
| Q1301 | 1 | qa_approve | FIX | Stale approval: a scene's key frames changed, a scene was added or removed, or the file's picture is not the approved one. NOTE when only the audio changed, or when a human override is recorded. NOT CHECKED when `approved/` cannot be trusted or the key frames cannot be redrawn |
| Q1302 | 1 | qa_approve | FIX | Regression: a gate that was PASS in the baseline (and never FIX there) is FIX now |
| Q1303 | 1 | qa_approve | FIX | `qa.py diff`: frames or 100 ms audio blocks changed outside `--expect` (NOTE inside it), or an `--expect` window that saw no change |
| Q1304 | 1 | qa_approve | NOT CHECKED | The frame size, or the environment that draws the pixels, changed since the approval and frames moved: re-approve. NOTE when the environment changed but every redrawn key frame is the same |

They are explained under Approval below.

## What scenes.py declares

The gates read these names from scenes.py. `compile_schedule(TIMELINE)` writes `SCHEDULE`, `DURATION`, `CUTS`, `WINDOWS` and `CUES`, frame-exact ([engine.md](engine.md)).

| Name | Form | Read by |
|---|---|---|
| `draw(t)` | The frame at t, a pure function of t | Q1201, the text recorder, Q301, Q404, Q501 at the proof, approval and diff |
| `text_items(t)` | The text registry: one dict per text on screen at t | Q200 to Q209, Q301, Q401 to Q404, Q1102's holds, Q902's picture boxes, the proof sheets |
| `SCHEDULE` | `{name: (start, end)}` in seconds | Q901, Q904, Q1103, Q1104, Q1201, approval's key frames, the sheets |
| `DURATION` | Seconds | Q701, Q904, the frame count of the text gates and Q1201 |
| `CUTS` | Seconds of every scene change (or `(t, label)` entries) | Q901 (instead of SCHEDULE starts), Q1103, Q1104, Q1201 |
| `WINDOWS` | Transition windows as `(t0, t1, out, in)` | Q1103 and Q1104 (skipped inside), the recorder samples every frame inside, Q1201, the sheets |
| `CUES` | Every moment sound and picture share (forms below) | Q902, Q904, Q1103, Q1201, Q804's payoffs, the audio strip |
| `CUE_LAG` | Frames the picture may land after its cue by design (default 0) | Q902's picture side, Q1103's cue window |
| `KEY_TIMES` | `(t, why)` or bare seconds: moments the proof must show | The key sheet, Q1201 |
| `BPM` | Beats a minute | Q901 when `--bpm` is not given, Q905, the Gantt bar lines |
| `HOLDS` | `[(text, drawn at, exit at), ...]`, an older form; the last two numbers of each entry are a hold | Q1102 |
| `STATIC` | `[(t0, t1), ...]` spans drawn once by design (end exclusive) | Q1102, and the render reuses the frame |
| `HOLD_PROFILE` | `"display"`, `"caption"`, `"slow"` or a dict of `cps`, `pad`, `floor` | Q401 |
| `BUDGET_MB` | A size cap in MB | Q1001, and the bitrate cap of `run_all.py full` |
| `NO_TEXT` | `True`: no on-screen text by design | Q200, Q204 to Q206, Q208, Q209 pass instead of NOT CHECKED; drawn text then is a Q204 row |
| `NO_CUES` | `True`: no cue the picture must hit | Q902 passes |
| `SILENT` | `True`: no audio track on purpose, as `--silent` | Q706, Q801 and Q803 skipped; Q802 and Q804 pass; Q903 makes no rows; Q902 measures the picture only; the mux has no audio |
| `ALLOW` | `{code: [t or (t0, t1), ...]}`: designed exceptions | The NOTE-level codes below |

Declare `NO_TEXT`, `NO_CUES`, `SILENT` or an `ALLOW` entry only when the storyboard means it.

### text_items(t) items

| Key | Meaning |
|---|---|
| `s` | The drawn string, exactly |
| `box` | `(l, t, r, b)` in output px, from `engine.text_box` with the same font, xy, anchor and tracking as the draw (Q205 holds it to the ink) |
| `fg` | The text colour, hex or RGB: Q301 and Q404 need it |
| `alpha` | 0 to 1, including any fade or blend weight; missing reads 1.0, and Q209 then cannot tell whether hidden is right |
| `px` | The font size in output px: Q402 and Q301's large-text rule need it |
| `bold` | True for bold type: large text from 24 px (Q301) |
| `texture` | True for text nobody must read: skipped by gates 2 to 4, still counted as reported by Q204 |
| `profile` | A hold profile for this item; None means the video's |
| `reveal_end` | Seconds at which a typewriter or wipe reveal is complete (Q404) |
| `ticker` | True for a counter or clock whose values pass on the way |

Strings are compared as written by gates 2 to 4. The text recorder compares them with white space collapsed and case folded.

### CUES forms

`contract.cues` reads any of these and sorts them by time:

- a list of `(t, label)` or `(t, label, kind)` tuples, as `compile_schedule` writes;
- a list of dicts with `t` and optional `label` and `kind`, keeping every other key they carry;
- a dict of label to one time or a list of times: `CUES = dict(bell=[t0, t1], warm=t)`.

`kind` is `"both"` (the default), `"audio"` or `"picture"`. Extra dict keys the gates read: `payoff=True` (Q804 keeps other sounds off it; the audio strip draws it thicker), `region=(x0, y0, x1, y1)` in output px (where Q902 looks for the picture change) and `band=(lo, hi)` in Hz (the no-cue-sheet detector's band for that cue).

### What ALLOW can clear

`ALLOW` lists times or spans for NOTE-level findings only (`contract.allowed`); it clears no FIX and no NOT CHECKED. The tolerance is 1 frame unless the table says otherwise.

| Code | What an entry matches |
|---|---|
| Q204 | An unreported string too faint, small or symbol-only to be a FIX |
| Q207 | The middle of a changeover gap, within half the gap plus a frame |
| Q209 | A moment where registered text is not drawn |
| Q402 | The middle of the small text's longest rest |
| Q603 | A span holding the whole passage, with 1 s of slack at either end |
| Q803 | A time inside the quiet second (0.5 s tolerance around its middle) |
| Q804 | The stack's time, within 3 frames |
| Q901 | The cut time |
| Q902 | A cue time, for its NOTE rows and the onset detector's cues |
| Q904 | The off-grid time, within half a frame |
| Q1101 | The pop frame |
| Q1102 | A span covering the frozen run (a frame of slack at either end) |
| Q1103 | The cut frame |
| Q1104 | The stalled frame |

## The text recorder

`qa_registry` holds `text_items(t)` to what `draw(t)` really paints. It runs at the proof and inside `qa.py check --scenes`.

**What it records.** While one `draw(t)` runs, it wraps the PIL entry points and logs every `ImageDraw.text` call: the string, its ink box with any stroke, its glyph box, the fill's alpha, the font and size, the stroke width, the image drawn on, and the pixels the call changed. It imports a private copy of scenes.py with the hooks on, so tiles and sprites cached before the gate ran are made again and recorded. Labels qa.py and proof.py draw on their sheets are drawn outside it.

**How it follows text to the frame.** `copy`, `convert`, `filter`, `point`, `getchannel`, `split`, `crop`, `resize`, `reduce`, `paste`, `alpha_composite` (method and function), `putalpha`, `Image.blend`, `Image.composite`, `Image.merge` and the `ImageChops` operations carry each record to where it lands, with its new place, clip and opacity: a blend keeps its weight, and a composite clips the text to the part its mask shows. A record that reaches an image the size of the frame (or SS times it) has landed. When the returned frame still carries records, exactly what reached it counts; when the chain broke (the frame came back through numpy), every record that reached a frame-sized image counts, and so does every call that never did. Letters drawn one call at a time on one baseline join into their words; copies of one string at one place (a halo, a glow, a shadow, motion-blur sub-frames) count once, and a stroked copy is never the fill.

**Which frames.** Every frame inside a `WINDOWS` span (with a frame either side) and every caption changeover (a registered alpha between 0.05 and 0.98, or the set of shown strings changing), one frame every 0.25 s elsewhere (`GRID`), and the last frame. Q204 then walks the span edges of up to 20 unreported strings a frame at a time (`REFINE`). It times 6 frames first and uses worker processes only when the rest would take over 20 s, or when `--registry-procs` asks. A drawn box with under a quarter of its area on the frame (`SEEN`) is not counted.

**Matching.** A drawn item matches a registry item with the same string near it (within half an em, at least 8 px), or as part of a registered string (a typewriter, one line of a wrapped block), or as a set of registered words, or with spaces taken out.

**Where it is blind.**

- Text that never goes through `ImageDraw.text`: glyphs pasted as images, text masks built in numpy, a pre-rendered bitmap. Q208 is NOT CHECKED when it sees no call at all; otherwise such text is simply missing from Q204.
- Text that was rotated or transformed: the record goes along but its place is lost, so it is matched by its string alone, its box is not compared (Q205) and its cover is not measured (Q206).
- Text whose layer reaches the frame through numpy: it still counts, but by its string alone, with no box to compare.
- Frames it did not sample: between grid frames outside windows and changeovers.

## review_times.json

One list, every moment a reviewer must see (`contract.add_review_times`). One entry per time, rounded to 3 decimals:

| Field | Meaning |
|---|---|
| `t` | Seconds |
| `why` | Every reason at that time, joined with `; ` |
| `kind` | The highest-ranked of its kinds |
| `kinds` | Every kind given at that time, ranked |
| `code` | The first code that asked for it, or null |
| `status` | The most severe status seen: FIX over NOT CHECKED over NOTE |
| `strip` | True when any entry asks for an f-2 to f+2 strip |
| `n` | Its cell number on `proof_keys.png`, or null when the cap left it off |

Kinds, highest rank first (`contract.KINDS`): `finding`, `changed`, `pop`, `cut`, `window`, `key`, `audio`, `rest`. No engine module writes `audio` today; it is ranked for entries added by hand.

| Step | What it does to the file |
|---|---|
| `run_all.py proof` | Starts it afresh: both sides of every cut (`cut`), the first and last frame of every window (`window`), the middle of each string's longest rest (`rest`), `KEY_TIMES` (`key`), and a `finding` for every FIX, NOT CHECKED and NOTE row of the proof that names a moment. It keeps the `changed` entries of the last `qa.py diff` |
| `run_all.py full`, `audio` | The scans add theirs; then a `finding` for every row that is not PASS and names a moment (`<code> <status> <item>: <meaning>`); then the sheets are redrawn and `n` written back |
| `qa.py check --scenes` | The scans add theirs; with `--json`, every other finding too |
| `qa.py diff` | Takes out what the last diff added, then adds `changed` entries: status FIX for an undeclared change, NOTE for a declared one or a sampled unchanged frame |
| `qa.py approve` | Retires the `changed` entries the review covered |
| `python proof.py keys` | Redraws the sheets from the file and writes `n` back |

A file that does not parse is moved to `review_times.json.bad` with a warning, and a new one is started. `qa.py approve` adds every time in the file to the key frames it pins, and `qa.py audiostrip` draws the numbered cells on its keys lane.

## The proof sheets

| Sheet | What it shows | Drawn by |
|---|---|---|
| `proof.png` | Up to 12 stills: every scene midpoint, then the first and last frame of each window, then scene boundaries | `run_all.py proof` |
| `proof_keys.png` (and `_2`, `_3` pages) | One cell per frame of `review_times.json`, most urgent first: FIX, NOT CHECKED, changed, pop, NOTE, cut, window, key, audio, rest. A cap of 40 cells drops captions at rest first and never a FIX. Page 1 lists the FIX and NOT CHECKED rows that name no moment | `run_all.py proof`, again at the end of `full` and `audio`, and `python proof.py keys` |
| `proof_strips.png` | Frames f-2 to f+2 from draw(t) for every entry with a strip (Q1101 pops; Q203, Q207 and Q404 from `check --json`), at most 24 | The same steps |
| `proof_gantt.png` | Scenes, windows, texts (solid at rest, dim while fading), cues and the numbered cells on one time axis, with bar lines on the BPM grid; at most 2000 px wide (1920x270 on the template) | The same steps |
| `review/audio.png` | The sound as a picture (see audiostrip) | `qa.py audiostrip` |
| `review/look.jpg` | Frames of the encoded file | `qa.py look` |
| `review/diff_*.jpg` | Before, after and difference of each changed passage | `qa.py diff` |

On the template the proof wrote `proof_keys.png: 9 of 9 key moments` and no strip sheet (2026-11-01).

## Approval

**`qa.py approve`** keeps what the final reviewer passed in `approved/`. Flags: `--scenes` (the working folder, default `.`), `--review <file>` (the reviewer's reply, verbatim), `--video` (default: `OUT` in `run_all.py`, else `out.mp4`), `--reviewer <id>` (when the reply has no `reviewer:` line), `--override "<why>"` and `--procs`.

It stores, in `approved/`: `approval.json`; `frames.hash` and `thumbs.npy` of the last render; `qa.json` when there is one (the `--baseline` for Q1302); `mix_raw.hash` (one digest per 100 ms block of the pre-master mix) with a copy of `mix_raw.wav`; and `src/`, a copy of scenes.py and every local module it imports. `approval.json` holds the time, the file (path, sha256, size, written time, the sha256 of its decoded picture, duration, fps, size, frame count, loudness, true peak), the digests of each scene's key frames (its first, middle and last frame, plus every `review_times.json` time and every `qa.py look` copy made after the file was written), the reply (verbatim, with its sha256 and the verdict, reviewer, stage, file, written time and `frames seen:` line read from it), any overrides, the environment (Python, Pillow, numpy, ffmpeg version, the sha256 of each font file the drawing opened, the frame size, the sha256 of each local module), the sha256 of every file in `approved/` and the history of earlier approvals. It writes everything into `approved.new/` and swaps it in with two renames, so a run that stops on the way leaves the previous approval whole.

It **refuses** (exit 1, `REFUSED: ...` lines) when the reply is missing, is not REVIEW PASS, names no stage or a stage other than final, names no file or another file, gives no written time or one more than 1 s from the file's; when `qa.json` has a FIX or NOT CHECKED row outside the approval codes; or when `qa.json` is older than the file. `--override "<why>"` approves anyway and records each refusal with the reason and the time; qa.py check then shows it as a Q1301 NOTE until a clean review is approved. It **cannot approve** (exit 2, `CANNOT APPROVE: ...`) when scenes.py, the file, `frames.hash` and `thumbs.npy`, or the review file is missing; when the file's size, rate or frame count, or `frames.hash`, does not match the build; when scenes.py does not draw; or when `frames.hash` no longer matches draw(t) at the key frames (scenes.py changed after the render). With no `qa.json` it only prints a note.

On the scratch template, 2026-11-01: `APPROVED out.mp4 (sha256 7f7a0a56ee98, 240 frames, 3 scenes, 14 key frames; REVIEW PASS by final-1)`, and with no reply, `REFUSED: no reviewer verdict: pass --review <file holding the reviewer's reply>`.

**`qa.py check` afterwards** (`qa_approve.check_rows`, only when the working folder holds an approval):

1. A changed frame size (E.W, E.H, E.FPS or E.SS, or the file's own size and rate) is Q1304 NOT CHECKED, and nothing else is compared.
2. The approved key frames are redrawn now, in worker processes. A change in Python (major.minor), Pillow, numpy or a font file is Q1304 NOT CHECKED when a key frame moved, and a Q1304 NOTE when none did.
3. Q1301 FIX when any scene's key frames differ, or a scene was added or removed (a scene renamed in its old time slot is matched). Its fix names the windows for `qa.py diff --expect`.
4. Otherwise Q1301 PASS, `approval current`, or a NOTE when an override is recorded. Then, when the file is not the approved one: its decoded picture the same as approved is a NOTE (`only the audio changed`); a different picture is a FIX, saying whether only the encode changed (the last render's `frames.hash` matches the approved one) or which frames differ.
5. With `--baseline`, Q1302 compares this run's rows with the baseline's, and is NOT CHECKED for gates that passed there and made no row now (a flag the baseline run had is missing).

An `approved/` whose files do not match the hashes `approval.json` recorded makes Q1301 NOT CHECKED. Template with its approval, 2026-11-01: `PASS Q1301 approval current: key frames of 3 scenes match the approval of 2026-11-01 18:11:15 (REVIEW PASS by final-1); the file is the approved one (sha256 matches)`; after a change to the end card's ground colour, `FIX Q1301 STALE APPROVAL: scenes end changed since the approval ...`.

**`qa.py diff`** (flags `--scenes`, `--expect t0-t1[,t0-t1 ...]`, `--procs`, default a quarter of the cores, at most 8) draws every frame of the current source at the approved size and compares it with the approved `frames.hash`, and compares `mix_raw.wav` with the approved blocks after taking out one overall gain (the median of the per-block gains, as the pre-master mix is peak-normalised); a block changed when what is left is over 2 steps of 16 bit RMS. It uses `mix_raw.wav` as the last render wrote it, and never rebuilds the mix. Rows: Q1303 FIX for a change outside every `--expect` window, NOTE inside one, FIX for a window that saw no change, PASS when nothing changed; Q1304 when the size or environment changed and frames moved; NOT CHECKED when there is no approval or the frames cannot be drawn. A window holds frames `frame_of(t0)` to `frame_of(t1) - 1`, like a scene. It writes `review/diff_tSSS.SS.jpg` triptychs (before, after and the difference in magenta) at the first, middle and last frame of each changed span; a change over 30 percent of the film and more than one scene (or of a one-scene film) is global, sampled at about twelve even steps plus both sides of every cut, on `review/diff_global_NN.jpg` pages. The last line is `DIFF: SAME as the approval`, `DIFF: CHANGED, every change declared with --expect (re-review each NOTE above)`, `DIFF: FIX (...)` or `DIFF: NOT CHECKED (...)`; exit 0, 0, 1 or 2. Scratch template, 2026-11-01: `DIFF: SAME as the approval` before the change; after it, `DIFF: CHANGED, every change declared with --expect` with `--expect 5-8`, and `DIFF: FIX (1 undeclared change; 1 --expect window saw no change)` with `--expect 2-5`.

**`qa.py verify [video]`** (flag `--scenes`) re-hashes a file, by default the approved one, against `approval.json`: `VERIFY: SAME <file> is the approved file (...)` exits 0; `VERIFY: DIFFERS ...` exits 1 and says whether its decoded picture is the approved one; `VERIFY: NOT CHECKED (...)` exits 2. Any error reads as exit 2, never 1.

**What approval protects against.** It is per hash, not per conversation turn: a changed source that moves a key frame, a re-rendered or re-encoded picture, a new mix, a new environment that moves pixels, a new frame size and an edit inside `approved/` all show up in check, and `diff` names every changed frame and audio block.

**What it does not protect against.** `qa.py check` redraws key frames only; a change between them shows through the file's picture hash once the film is rendered again, or in `diff`, which draws every frame. The ffmpeg version is recorded but not compared (Q708 covers the colour chain), and a Python patch release is ignored. Approve reads only the reply's verdict, stage, file name and written time, so the reply's care is the reviewer's; it approves with no `qa.json` at all (a note only); and an `--override` approves on the record.

## Other qa.py subcommands

| Command and flags | What it does | Prints or writes | Exit |
|---|---|---|---|
| `look <video> [--times T,T] [--width 480] [--out review]` | Frames of the encoded file, by default every 5 s and the last frame; each time goes onto the frame clock and is decoded from half a frame before | `<out>/tSSS.SS.jpg` per frame and `<out>/look.jpg` (4 columns), then `wrote review/look.jpg (3 frames at 480 px, 1920x270)` on the template (2026-11-01; Windows prints the folder with a backslash) | 0 |
| `holds <scenario> [--section S] [--profile display\|caption\|slow]` | The reading-hold rule on a storyboard: every quoted on-screen line gets its window, or an equal share of its row's time, less a 0.4 s entrance; lines joined by ` / ` read as one block; rows saying "for example" are skipped. Needs no ffmpeg | One `OK` or `SHORT` line per line with the time it has, the time it needs and the words and characters the slot fits, then `HOLDS: OK` or `HOLDS: SHORT (<n>)` with the profile's numbers | 0, or 1 when any line is short |
| `purity [--scenes .] [--n 16] [--fps] [--size] [--ss] [--t T,T] [--grid S] [--procs] [--json]` | Q1201. Size, rate and supersampling default to `build.json`, else 1920x1080, 30 fps, SS 1 | The rows and `PURITY: ...` | 0, 1, 2 |
| `lint [path] [--fps] [--all] [--json]` | Q1202 to Q1206, Q904, Q905 on `scenes.py` (or the path) | The rows, with `--all` every site, and `LINT: ...` | 0, 1, 2 |
| `owner --t S` or `owner --traceback <file>` `[--path scenes.py] [--fps]` | The scene function(s) a moment or a traceback belongs to: both scenes within a frame of a cut or inside a window; a shared helper routes to the scene functions that call it | `owner: <why>`, `error: <last line>` for a traceback, one line per function with its `file:first-last` lines | 0; 2 unless exactly one of `--t` and `--traceback` is given |
| `approve`, `diff`, `verify` | See Approval | | |
| `calib [--fps 30] [--size 320x180] [--out calib]` | Q906 | `video.mp4`, `mix_raw.wav`, `mix.wav` and `calib.mp4` in the folder, the rows and `CALIB: ...`. A folder holding a build is refused: `refused: <folder> holds a build (...)` | 0, 1, 2 |
| `audiostrip <video or mix.wav> [--scenes .] [--out review/audio.png]` | The sound as a picture on one time axis: scenes, a log-frequency spectrogram, the CUES ticks coloured by their measured offset (green within a frame, amber within 100 ms, red missing or further, grey not measured), momentary and short-term loudness with the integrated line, true peak per 100 ms with every frame over -1 dBTP in red, and the key sheet's numbered cells. Works on `mix.wav` at the proof stage | The picture (1600 px wide) and `wrote review/audio.png (1600x656) in 1.4 s: I -14.1 LUFS, TP -1.8 dBTP, 0 of 80 frames over -1 dBTP; sync: 2 within 1 frame (of 2 audio cues)` on the template (2026-11-01) | 0 written; 2 no audio (0 when `SILENT`) or no ebur128 summary |
| `selftest [--quick] [--only CODE,CODE] [--keep]` | See below | | 0, 1, 2 |

Scratch template runs, 2026-11-01: `CALIB: PASS (3 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)` with `blip lands +0.00 ms from the white frame`; `owner --t 2.0` routed to `draw` (the template has no per-scene functions); `purity` drew 24 frames in 2.7 s.

## The self test

`qa.py selftest` feeds every gate planted faults and known-good inputs, and renders the template as a control.

**How to run it.** From a full copy of the engine: `cp -r <skill>/engine/. <folder>/`, then `python qa.py selftest` in that folder. The fixtures are the `qa_fixtures/` package beside `qa_selftest.py`; a copy of only the `.py` files has none, so the run prints `MISSING qa_fixtures/__init__.py: ModuleNotFoundError: No module named 'qa_fixtures'`, marks every code it was asked to prove UNCOVERED (only Q201 with `--only Q201`) and exits 2 (tried with `--only Q201`, 2026-11-01). The template control renders the `scenes.py` beside `qa_selftest.py`, so a copy holding a video's own scenes.py controls that instead; the run prints the template's path and sha256 to show which.

**What it runs.** Every `CASES` entry of the fixture modules (`text`, `registry`, `source`, `files`, `sound`, `scans`, `approval`): a tiny fake scenes, a scenes file in `qa_fixtures/`, or a short WAV or MP4 made at run time in a temp folder, through one gate. Each states what the gate must say: the code, the status, the item, the time and the measured value within a tolerance, and for known-good inputs that no row is FIX or NOT CHECKED. Meanwhile, in two threads, the template is copied to temp folders and run through `run_all.py proof` and `full` at 1920x1080 and 1080x1920; each must end with 0 FIX, 0 NOT CHECKED and, after `full`, a DELIVERED line.

**What it prints.** One line per judged want: `<outcome> <code> <status> <case> <detail>`, where the outcome is `ok`, `MISSED` (the planted fault did not fire), `WRONG` (it fired with the wrong item, time, value or count, or a known-good input fired), `EMPTY` (the gate looked at 0 items), `MISSING` (a fixture file or module is missing) or `ERROR` (the case raised; the line says where). Then one line per template run, `UNCOVERED` for a code no fixture makes fire at its failure status, `STALE` for an `EXPECTED_GAPS` entry a fixture now covers, `gap` lines, `selftest took ...`, `kept <folder>` when it failed or `--keep` was given, and the last line, `SELFTEST: PASS|FAIL (<missed or wrong>, <not proven>) (<n> fixtures, <k> of <K> codes covered, <g> expected gaps)`. A code counts as covered only when a want at its failure status in `contract.CODES` held.

**Exit codes.** 0 when everything held; 1 when a gate missed or misreported a planted fault, or a control failed; 2 when a code could not be proven (no fixture and no `EXPECTED_GAPS` entry, a missing fixture file, a gate that looked at 0 items, a case that raised, a stale gap). 1 wins over 2.

**EXPECTED_GAPS** in `qa_selftest.py` is a dict of code to the reason no fixture can make it fire on this machine. It is empty today: every code has a fixture.

**Today.** `SELFTEST: PASS (147 fixtures, 58 of 58 codes covered, 0 expected gaps)` in 55.5 s, with the template controls `PROOF: PASS (23 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)` and `QA: PASS (49 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED), exit 0, DELIVERED` at both sizes (2026-11-01). The 147 are the judged lines: every want of every case plus the four template runs.

**What it proves, and what it does not.** It proves that every code can still fire on the right item, time and value, that its known-good inputs stay clean, and that the template passes at 16:9 and 9:16 on this machine's ffmpeg, fonts and libraries. It does not prove that a gate catches a fault unlike its fixtures, how often a gate flags a real film by mistake, or anything about how a video looks or sounds. `--quick` skips the `full` renders, and `--only` runs no template control at all.

## Known limits

- No gate watches or listens. The reviewer reads the sheets and frames, and the delivery report says what nobody heard.
- The flash gate measures WCAG 2.2's thresholds on a 192x108 decode with 4 x 4 pixel cells; area is counted in whole cells, so a flash of exactly a quarter of a window can go either way. It certifies nothing. `qa.flash_report(..., rows=False)` and the other old list forms read the whole-frame mean only, so an empty list proves nothing.
- The text gates judge the registry: they see what `text_items(t)` reports, and the recorder holds that to the drawn ink only on the frames it samples and only for text drawn through `ImageDraw.text` (see the text recorder).
- Q201 measures the 4 percent pad only. Platform overlays on 9:16 (buttons, captions, progress bars) are measured by no gate ([formats.md](formats.md)).
- Q301 compares the text colour with the median of a ring around the box at three frames of each rest, not glyph by glyph; a gradient or texture under the letters can differ from its ring.
- Q401 holds each string's longest rest to a reading-pace heuristic; it does not know what a narrator says over it.
- Q501 and Q502 read only the grey mean and spread of one frame.
- Q708 tests this machine's colour chain on swatches, not the file's own colours; Q1105 compares grey means, so an error that shifts colour but keeps grey passes it.
- Q803 looks at whole seconds; a gap shorter than a second is not seen.
- Q902 measures sound effects placed with a cue sheet, on the lossless stems; without a sheet its detector is a guess. It does not measure narrated words ([voice.md](voice.md)). A small moving part on a large still frame needs `region=` or registry text, or the picture side is not measurable.
- Q903 looks at three 2 s windows; Q906 runs on its own test clip, not the film.
- Q1101 to Q1104 are NOTE-level heuristics on 192x108 grey: pointers for the reviewer, not verdicts.
- Q1201 draws at most 2 + 2n sampled frames plus `--t` and `--grid`; a state leak that shows only on other frames is not seen. The lint reads syntax: it cannot follow a name whose type it does not know, such as an object passed in with its own `text` method.
- Approval compares key frames, file hashes and the environment that draws pixels; see Approval for what it does not cover.

## Template numbers, 2026-11-01

The shipped template (8 s, 120 BPM) on ffmpeg 9.0.2, Python 3.15.2, Pillow 13.0.0 and numpy 2.5.4, identical at 1920x1080 and 1080x1920 unless noted:

```
PROOF: PASS (23 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)
master: ceiling -2.00 dBTP, mix.wav -14.0 LUFS at -2.00 dBTP (Q805 PASS) -> out.mp4 -14.1 LUFS at -1.80 dBTP
QA: PASS (49 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)
APPROVAL: none yet -> final review, then qa.py approve
DELIVERED <working folder>/out.mp4 (0.4 MB, 8.00 s, -14.1 LUFS, -1.8 dBTP)
QA: PASS (44 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)
wrote review/audio.png (1600x656) in 1.4 s: I -14.1 LUFS, TP -1.8 dBTP, 0 of 80 frames over -1 dBTP; sync: 2 within 1 frame (of 2 audio cues)
SELFTEST: PASS (147 fixtures, 58 of 58 codes covered, 0 expected gaps)
```

The first five lines are `run_all.py proof` and `full`; the 49 rows of `full` are the 44 of `qa.py check` plus Q805 and the four scans of `thumbs.npy`. The sixth is `qa.py check out.mp4 --scenes . --size WxH --fps 30 --bpm 120 --json qa.json`, the seventh `qa.py audiostrip out.mp4 --scenes .` (1.1 s at 1080x1920), the last `qa.py selftest`. The proof's 23 rows are Q501, nine text gates, the five recorder codes, Q1201 and the seven lint rows. The same file with no `--scenes` and no build files beside it gave `QA: PASS (23 checks, 0 FIX, 1 NOTE, 0 NOT CHECKED)`, the NOTE being Q804's missing cue sheet.
