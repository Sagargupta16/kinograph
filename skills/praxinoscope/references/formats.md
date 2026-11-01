# Formats

Frame sizes per aspect, frame rates, safe areas, the encode ladder, size budgets and file names. Numbers come from the engine code (function or constant named) or from a dated measurement; the encode commands themselves are in `engine.md`, under the encode ladder.

## Sizes per aspect

Pass the size to every stage: `run_all.py <stage> --size WxH --fps N`. The engine draws any size; these four cover nearly every brief. The default, with no flag, is 1920x1080 at 30 fps (`run_all.py`).

| Aspect | `--size` | Typical place | 4 percent safe box (px) | 10 degree flash window |
|---|---|---|---|---|
| 16:9 | `1920x1080` | a site, a deck, YouTube, a wiki | x 76.8 to 1843.2, y 43.2 to 1036.8 | 0.33 of the width x 0.44 of the height |
| 9:16 | `1080x1920` | Reels, Shorts, TikTok, stories | x 43.2 to 1036.8, y 76.8 to 1843.2 | 0.79 x 0.33 |
| 1:1 | `1080x1080` | a square feed post | x 43.2 to 1036.8, y 43.2 to 1036.8 | 0.44 x 0.33 |
| 4:5 | `1080x1350` | a portrait feed post | x 43.2 to 1036.8, y 54.0 to 1296.0 | 0.56 x 0.33 |

- The short side is 1080 px in all four, and the text gates scale every size rule by `1080 / min(W, H)` (`qa.text_gates`), so 36 px key text and the 24 px floor apply as written. At another size, say 1280x720, a 24 px font counts as 36 px.
- The safe box is `qa.inside`'s 4 percent pad on every edge (Q201). The flash window is `qa_scan._window` on the 192x108 decode: WCAG's 341 x 256 field on a 1024 x 768 view, with the frame fitted into that view (`qa-gates.md`, gate 6).
- Width and height must be even: the encode writes yuv420p, which halves the chroma in both directions.
- `--ss 2` draws at twice the size and scales down in `finish()`: four times the pixels, for thin lines and small text.

## Frame rates

30 fps is the default (`engine.FPS`); `--fps` takes any whole number. One frame lasts `1 / fps`: 33.3 ms at 30, 41.7 ms at 24, 16.7 ms at 60. Every time in the engine goes through one clock, `contract.frame_of(t, fps)`, the nearest frame with halves rounded up.

Tempos whose beat is a whole number of frames (`qa_lint`'s Q905 list, 60 to 200 BPM, computed 2026-10-31):

| fps | Whole-frame BPM |
|---|---|
| 24 | 60, 72, 80, 90, 96, 120, 144, 160, 180 |
| 25 | 60, 75, 100, 125, 150 |
| 30 | 60, 72, 75, 90, 100, 120, 150, 180, 200 |
| 50 | 60, 75, 100, 120, 125, 150, 200 |
| 60 | 60, 72, 75, 80, 90, 100, 120, 144, 150, 180, 200 |

The rate also sets the cue windows: Q902's late limit is one frame, never over 60 ms (`sound.md`), and grain is held for 2 frames at any rate (`grain.grain` steps at fps / 2).

## Safe areas

The engine measures one safe area, the 4 percent pad above, on every aspect: Q201 fails text at rest outside it. Vertical platforms also draw their own buttons, captions and progress bars over the lower part of the frame and down the right edge. Their size differs from one platform to the next and changes over time, so no gate measures them and this page quotes no numbers for them: keep key text, faces and the logo away from the bottom and the right edge of a 9:16 frame, and check the target platform's current guide when the brief names one.

## The encode ladder

Always say in the delivery report which rung made the file and why (`delivery.md`).

| Rung | When | What it makes |
|---|---|---|
| a | ffmpeg has libx264 (the normal case) | `run_all.py full`: H.264 MP4 through `render.encode_cmd`, libx264 preset medium, CRF 18 (`render.CRF`), yuv420p, converted to BT.709 limited range and tagged so (`contract.COLOR_VF`, `COLOR_FLAGS`), then the mux: the picture copied, AAC at 320 kb/s (`contract.AAC_ARGS`), cut to the shorter stream, `+faststart`. It plays everywhere. Use CRF 20 for grain-heavy styles (the note on `render.CRF`) |
| b | ffmpeg without libx264 | PNG frames and the audio made by hand, then AV1 in MP4 (libsvtav1, else libaom-av1) or, without an AV1 encoder, VP9 in WebM (libvpx-vp9 with Opus audio). The gates for the H.264 deliverable (Q705, Q707, Q708) read NOT CHECKED, by design |
| c | a preview, or nothing else works | A GIF of at most 15 s, at most 960 px wide, at 15 fps, without sound |

Tested on ffmpeg 9.0.2 on 2026-11-01 with the 8 s template: rung a gave 0.4 MB at 1920x1080 with tags bt709 / bt709 / bt709 / tv and the BT.709 round trip within 1 level (Q708); rung b at 640x360 gave 0.28 MB (SVT-AV1, CRF 35), 0.28 MB (libaom-av1, CRF 30) and 0.20 MB (VP9 WebM, CRF 32, Opus 160 kb/s), all three read back yuv420p and bt709 / tv, and `qa.py check` ended `QA: NOT CHECKED (3)`; rung c gave a 960x540 GIF of 120 frames, 0.73 MB. The commands are in `engine.md`. AV1 and VP9 can fail to play in older QuickTime and in some company players: say so when the file is one of those.

### Which encoder

Our measurement on a 15 s 1920x1080 motion-graphics piece:

| Encoder and setting | Encode time | Bitrate | VMAF (mean) |
|---|---|---|---|
| x264 medium, CRF 18 (rung a) | 2.4 s | 2,438 kb/s | 97.88 (min 95.25) |
| x264 veryfast | 1.5 s | 1,919 kb/s | 97.24 |
| h264_nvenc p7 hq | 2.3 s | 1,873 kb/s | 97.99 |
| av1_nvenc p7 uhq | 4.8 s | 1,668 kb/s | 98.12 |

The encode is a few seconds, small next to drawing the frames and writing the scenes, so a GPU encoder saves file size, not time. The engine always encodes with libx264 (`render.encode_cmd`); the NVENC encoders need an NVIDIA GPU and are not wired in. When a size cap is tight, AV1 is the one that buys room, at the price of players that cannot open it.

## Size budgets

Ask where the file goes and what its limit is; we do not quote platform limits we have not checked. Give the limit to the build as `BUDGET_MB = N` in scenes.py or `run_all.py full --budget-mb N`. `run_all.caps` turns it into an x264 bitrate cap:

- `maxrate = 0.95 x budget_mb x 8000 / duration - 320` kb/s (the 320 is the AAC audio; 0 for a `SILENT` piece);
- `bufsize = maxrate` under 30 s, twice it from 30 s on.

| Budget | Length | maxrate / bufsize (kb/s) | Silent |
|---|---|---|---|
| 4 MB | 15 s | 1707 / 1707 | 2027 / 2027 |
| 8 MB | 30 s | 1707 / 3413 | 2027 / 4053 |
| 10 MB | 60 s | 947 / 1893 | 1267 / 2533 |
| 25 MB | 60 s | 2847 / 5693 | 3167 / 6333 |

(Computed with `run_all.caps` on 2026-10-31.) A budget too small for the audio alone stops the build: `a 0.05 MB budget leaves no video bitrate for 7.5 s with 320 kb/s of audio`. x264's buffer can still pass the total by up to about 0.9 x bufsize, so the cap is not a guarantee: Q1001 checks the finished file against the budget (or `--max-mb`), and Q1002 notes any bitrate over 12 Mb/s (flat graphics land at 1 to 5; the template read 0.4 Mb/s on 2026-11-01).

Film grain is what drives size. In the 2026-10-28 batch, grain std 2.6 gave 140.2 MB for 60 s, and std 1.6 at CRF 20 gave 35.9 MB. To shrink a file, in order: lower the grain's std (`grain.grain`, default 1.6) or drop it and the vignette, raise CRF to 20, drop to 720p (`--size 1280x720`), drop to 24 fps, shorten the cut.

### Where the file goes

| Destination | Hand over |
|---|---|
| Slack or another chat app | The MP4, and the GIF preview (rung c) beside it |
| Email | The MP4 attached only when it is small; otherwise a link, with a 720p cut and a poster PNG on offer |
| A site, an intranet, a wiki | H.264 MP4 (rung a) |
| Reels, Shorts, TikTok | 9:16 at 1080x1920, H.264 MP4 |

## File names

- The working folder is `videos/<slug>/` under the user's current folder, unless the user names another (`engine.md`).
- The deliverable is `OUT` in the working copy of `run_all.py` (default `out.mp4`). Set it per video to `<slug>_<aspect>_<length>s_v<n>.mp4`, for example `launch_16x9_30s_v1.mp4` or `launch_9x16_15s_v2.mp4`. Write the aspect with an `x`: Windows does not allow `:` in a file name. Raise `v<n>` for every new version the user sees.
- A file that failed a gate becomes `<name>.rejected.mp4`, and one from a run that broke before its verdict `<name>.unchecked.mp4`; neither is ever delivered, and the next `run_all.py full` or `audio` deletes both before it starts.
- The by-hand rungs write `out_av1.mp4`, `out.webm` and `preview.gif` in the commands of `engine.md`; rename them to the same pattern before delivery.
- The build's own files (`video.mp4`, `mix.wav`, `frames.hash` and the rest) keep the names `contract.py` gives them: the gates find them by those names.
