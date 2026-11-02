---
name: kinograph
description: >-
  Makes short videos from code. It turns a brief into a fact-checked
  storyboard, draws every frame in Python with Pillow and numpy, writes and
  masters the sound, and encodes with ffmpeg (MP4 first, then WebM or GIF).
  A builder agent does the build, a fresh-eyes reviewer agent checks the proof
  and the finished file, and coded QA gates must pass before anything is
  delivered. Six styles cover product launches, data stories, technical
  explainers, logo stings, beat-locked 9:16 reels and retro 8-bit game
  parodies. Use when a user wants a video, promo, explainer, reel, motion
  graphic, title card or logo animation made, animated or rendered. It is not
  for animating a web UI or for editing camera footage.
license: MIT
---

# kinograph

A video here is a program: `scenes.py` draws frame t as a pure function of t, so the same source always gives the same file and a fix redraws only what it touches. The user approves twice, the storyboard and then the proof sheet, and gets a file only after the gates and a final review have passed.

Links and the `engine/`, `styles/` and `references/` paths are relative to this skill's folder, the base directory shown when the skill loads; `videos/` paths sit under the user's current folder. Below, `<skill>` is the skill folder as an absolute path; both agents need it.

## Setting up and running commands

- First use: `bash <skill>/setup.sh` checks uv, ffmpeg with libx264, ffprobe, the pinned Pillow and numpy, and a default font. It installs nothing system-wide (its first uv run may fetch the pinned Python and wheels into uv's cache) and ends `SETUP: PASS`, or prints a `FIX` line for each gap and ends `SETUP: FAIL`.
- Engine scripts run from the video's working folder once the builder has copied the engine there: `uv run --no-project --with-requirements requirements.txt python <script> ...`. Below, `python` means exactly that.
- Outputs go to `videos/<slug>/` under the current folder unless the user names another. A batch keeps one scenario at `videos/<batch>/scenario.md` (a "Rules for all" paragraph, then one `## <nn> <slug>` section per video) and builds each video in `videos/<batch>/builds/<nn-slug>/`, with its own builder and reviewers.
- Before launching long background agents in the Claude desktop app, hold the computer awake with the app's keep-awake tool. On battery the app holds it only with its Keep awake on battery power setting on, and a closed lid sleeps whatever the setting. A long review once lost 6.5 hours to a laptop that went to sleep after the turn ended.
- The agents are `kinograph:builder` and `kinograph:reviewer`. In a session that started before the plugin was installed those types are missing: launch a general-purpose agent instead and tell it to read and follow `<skill>/../../agents/builder.md` or `<skill>/../../agents/reviewer.md`.

## House defaults

16:9 at 1920x1080, 30 fps, 30 s and 120 BPM, unless the brief or the card says otherwise. Sound mastered to -14 LUFS integrated, true peak at or under -1 dBTP. Text inside the safe area, with contrast of at least 4.5:1. At most three flashes in any second. Frame 0 is the thumbnail, so it is never black. Cuts land on beats.

## The eight steps

### 1. Brief

Ask at most three questions, in one message, and only for what the request leaves open. Give each a default, so the user can just say go:

1. Purpose and audience: what should a viewer know or do afterwards? (default: read from the request and said back in one line)
2. Length, aspect and where it plays. (default: 30 s at 16:9 for a site or a deck; 9:16 at 1080x1920 for Reels, Shorts or TikTok)
3. Sound: music only, or narration over music? (default: music only)

### 2. Style

Read [styles/README.md](styles/README.md). Offer the two or three cards that fit best, one line each, and recommend one. When the user picks, read that card in full: its palette, type, motion and sound rules bind the build.

| Style | For | Length |
|---|---|---|
| [signal](styles/signal.md) | a product or feature launch | 15 to 30 s |
| [ledger](styles/ledger.md) | a data story: numbers that count up and charts that draw, every figure sourced | 30 to 60 s |
| [blueprint](styles/blueprint.md) | a technical explainer: diagrams that draw themselves step by step | 45 to 90 s |
| [marquee](styles/marquee.md) | a logo sting or title card | 4 to 10 s |
| [pulse](styles/pulse.md) | beat-locked kinetic type for 9:16 social reels | 15 to 30 s |
| [cartridge](styles/cartridge.md) | a retro 8-bit game parody: pixel art drawn in code, chip music | 20 to 40 s |

### 3. Script and storyboard

Write `videos/<slug>/scenario.md` with three parts:

- A header of plain lines: `style:`, `size:`, `fps:`, `length:`, `bpm:`, `sound:`, `working folder:` and `skill folder:`. The reviewer finds the card and the gate docs through it.
- A Facts table with the claim, its source and the date it was read. Check every name, number, date, price and quote here in the main chat, with web tools or the user's own files. The builder cannot browse, so nothing new goes on screen after this step.
- The storyboard: one table with the columns Time, Beat, Visuals, On-screen text and Audio, one row per beat with its span in seconds (`0-2.5`). Quote each on-screen line exactly as it will read and follow it with its own time window, as in `"Ship it today" (0.4-2.5)`. Lines on screen together are joined with ` / ` and read as one block.

Before showing the table, run `uv run --no-project --with-requirements <skill>/engine/requirements.txt python -B <skill>/engine/qa.py holds videos/<slug>/scenario.md` (add `--profile caption` or `--profile slow` when the card asks for that reading pace, and `--section <nn>` for one video of a batch). Fix every SHORT line by cutting words or widening its window, never by shrinking the reading time, until it prints `HOLDS: OK`. Then show the table. Nothing is built until the user approves the storyboard.

### 4. Proof

Launch `kinograph:builder` in proof mode. Its brief: the brief from step 1, the approved storyboard (the scenario path, and the section in a batch), the style id, size, length, fps, BPM, the sound plan, the working folder and `<skill>`. It copies the engine into the working folder, writes `scenes.py` and the score, runs `run_all.py proof` and stops. Its report opens with the PROOF line (PASS, FIX or NOT CHECKED) and lists the sheets.

### 5. Proof review

Launch `kinograph:reviewer` with only the stage, the scenario path (and section), the working folder and a reviewer id such as `proof-1`. Never give it the builder's report.

- REVIEW FIX: send the findings to the same builder as one numbered list. It fixes them, runs the proof again and reports; then a fresh reviewer (`proof-2`, and so on) checks. Stop after three rounds while a P0 or a FIX row is open, or after two rounds for P1 and P2 findings, and tell the user what is still open.
- REVIEW PASS: show the user `proof.png`, the contact sheet, with the gate results, and ask whether to render.

### 6. Render

On a yes, send the same builder `render`. `run_all.py full` draws every frame straight into the encoder, makes and masters the sound, muxes, runs every gate and ends with an APPROVAL line and one DELIVERED line. A file that fails a gate becomes `<name>.rejected.mp4` and a run that broke leaves `<name>.unchecked.mp4`; neither is delivered or shown as finished.

### 7. Final review and approval

Launch a fresh reviewer at the final stage (`final-1`, and so on), again with only the stage, the scenario, the working folder and the id. Fix rounds and their limits work as in step 5.

On REVIEW PASS, save the reply verbatim to `review/reply_final_<n>.txt` in the working folder and run `python qa.py approve --review review/reply_final_<n>.txt` there. The approval is bound to content hashes, so any later change reopens review: the builder reports each change with its time windows, a fresh final reviewer gets that change list (never the rest of the report) and runs `qa.py diff --expect <windows>`, which names everything that changed, and `qa.py check` shows a stale approval as a FIX row (Q1301).

### 8. Deliver

1. `python qa.py verify <file>` must print `VERIFY: SAME`.
2. Re-check duration, size, resolution, fps and codec with one ffprobe run, and loudness with one ebur128 run (I and Peak in its Summary):
   `ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of default=nw=1 <file>`
   `ffmpeg -nostdin -hide_banner -i <file> -af ebur128=peak=true -f null -`
3. Report the path, duration, size, resolution, fps, codec and loudness; what was checked (the gates and both reviews) and what was not (no gate listens, and none certifies photosensitivity safety); the weak spots; and two or three next options, such as a 9:16 cut, a GIF preview or a shorter cut. The full report shape is in [references/delivery.md](references/delivery.md).

## Narration voices

`voice.synthesize` speaks with the kokoro-ts engine and the af_heart voice once its files are in `~/.cache/kinograph/voices`: about 326 MB of model plus 0.5 MB per voice. Ask the user before that download; the builder never downloads anything. `python voice_samples.py` renders the same lines in every ready voice, so the user can pick by ear. The Windows SAPI voices sound robotic: use them only as a timing fallback, and say so. Details: [references/voice.md](references/voice.md).

## Encoder fallbacks

H.264 MP4 through libx264 comes first; it is what `run_all.py full` makes. Without libx264, write PNG frames and encode AV1 MP4 or, failing that, VP9 WebM; a GIF comes last. The delivery report names the rung that made the file, and the reason. Commands: [references/engine.md](references/engine.md).

## Changing the engine

Never edit `engine/` here for one video; the builder edits its own copy. After any change to the engine itself, make a fresh copy (`cp -r <skill>/engine/. <scratch folder>/`, so `qa_fixtures/` comes along) and run `python qa.py selftest` there. It must end `SELFTEST: PASS`.

## Hard limits

- Put nothing on screen that the scenario's Facts do not source: no made-up facts, metrics, prices, ratings, testimonials or user counts.
- Show a third-party logo or trademark only from official files the user supplies.
- Never say a render, a check or a review happened when it did not, and never deliver a `.rejected.mp4` or an `.unchecked.mp4`.
- Never render the full film before the user approves the proof, and never approve a file the final reviewer did not pass.
- Never give a reviewer the builder's report (at a re-review, only its list of changes and their windows), and never reuse a reviewer for a second round.

## Further reading

- [references/engine.md](references/engine.md): the scenes.py contract, the stages, the files a build writes and the encode ladder.
- [references/qa-gates.md](references/qa-gates.md): every Q code, what scenes.py declares, review times and approval.
- [references/craft.md](references/craft.md): storyboard, layout, type and motion craft.
- [references/sound.md](references/sound.md): the score, cues and beat sync, the mix and the master.
- [references/voice.md](references/voice.md): narration engines, voice downloads and word cues.
- [references/formats.md](references/formats.md): sizes per aspect, frame rates, safe areas, encoders, size budgets and file names.
- [references/delivery.md](references/delivery.md): the delivery report and the next options.
- [references/troubleshooting.md](references/troubleshooting.md): what an error or a rejected file means, and what to do.
