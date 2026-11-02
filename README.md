# Kinograph

A Claude Code plugin that plans, storyboards, animates, scores and renders short videos from code. You describe the video in one line; the plugin writes a storyboard for you to approve, builds a proof, has a fresh-eyes reviewer check it, renders the file, checks it with 58 coded QA checks, and hands it over only once a second review has passed.

Named from *kino*, motion picture, and *graph*, written: a moving picture written in code.

## Install

```
/plugin marketplace add Sagargupta16/kinograph
/plugin install kinograph@kinograph
```

Then ask for a video, for example `/kinograph:kinograph a 30 second launch video for <product>`. The skill asks at most three questions, offers two or three styles, and stops twice for your approval: at the storyboard and at the proof.

### What it needs on your machine

| Need | Why | Check |
| --- | --- | --- |
| [uv](https://docs.astral.sh/uv/) | Runs the engine with pinned Pillow and numpy, on the Python version the engine pins (uv fetches it) | `uv --version` |
| ffmpeg with libx264 | Encodes, measures loudness, decodes for the gates | `ffmpeg -encoders` lists `libx264` |
| A system font | Text rendering (Arial on Windows, Helvetica on macOS, Liberation or DejaVu on Linux) | `bash skills/kinograph/setup.sh` |

`setup.sh` checks all of it and ends `SETUP: PASS`. The engine's `.python-version` pins one Python version for every build folder, so a proof and its render always run on the same interpreter. Each style names two free fonts under the SIL Open Font License; they are not bundled, so install them for the intended look (`skills/kinograph/styles/README.md` says where each comes from), or the builder draws with the system font. Narration is optional: the default voice (Kokoro-82M `af_heart`) needs about 326 MB of model files, downloaded only when you say so; see `skills/kinograph/references/voice.md`.

## How a video gets made

![How kinograph makes a video: the main chat, the builder and reviewer agents and the gates, from brief to delivered file](docs/kinograph-flow.svg)

1. **Brief and style.** At most three questions (purpose, length and aspect, sound), then two or three of the styles with a recommendation.
2. **Storyboard gate.** A table of time, beat, visuals, on-screen text and audio. `qa.py holds` checks that every line stays on screen long enough to read. Nothing is built until you approve it.
3. **Proof.** The `kinograph:builder` agent copies the engine, writes `scenes.py` (every frame a pure function of time) and the score, and renders review sheets. The proof gates check the first frame, every drawn string against its registry, purity across processes, and a lint.
4. **Proof review.** The `kinograph:reviewer` agent sees only the storyboard and the sheets, never the builder's report. It returns REVIEW PASS, or REVIEW FIX with findings ranked P0 to P2.
5. **Render.** Every frame goes straight into one H.264 encode. The sound is synthesized and mastered to -14 LUFS, then every gate runs on the encoded file.
6. **Final review and approval.** A fresh reviewer checks the file. `qa.py approve` binds that review to the file's content hashes, so any later change reopens review by itself.

The diagram's source is `docs/kinograph-flow.workflow.json`, an archify workflow in which every box cites the file and lines it comes from.

## Styles

| Style | Use it for | Default length |
| --- | --- | --- |
| signal | A product or feature launch | 15 to 30 s |
| ledger | A data story: numbers that count up, charts that draw | 30 to 60 s |
| blueprint | A technical explainer: diagrams that draw themselves | 45 to 90 s |
| marquee | A logo sting or title card | 4 to 10 s |
| pulse | Beat-locked kinetic type for 9:16 reels | 15 to 30 s |
| cartridge | A retro 8-bit game parody with chip music | 20 to 40 s |

Each card in `skills/kinograph/styles/` gives the palette with its contrast ratios, free fonts with system fallbacks, the motion and sound grammar, a beat map and the QA watch-outs.

## What is in it

| Part | What it does |
| --- | --- |
| Skill | `skills/kinograph/SKILL.md`: the workflow, the approval gates, defaults and rules |
| Builder agent | Builds, renders and checks one video in its own context, so engine logs stay out of your chat |
| Reviewer agent | Fresh eyes on the sheets and the file; never edits |
| Engine | `skills/kinograph/engine/`: drawing helpers on one integer frame clock, nine pure transitions, film grain, numpy instruments placed by their perceptual landmark, a 4x true-peak master, offline narration with word cues, frames passed through shared memory into ffmpeg |
| QA gates | 58 coded checks, 47 of them run by `qa.py check` on the file and the rest at the proof, in the master, `qa.py calib` and `qa.py diff`: safe area, overlap, contrast, reading holds, WCAG 2.2 flashes, pops and freezes, true peak, cue sync, the mux, colour tags, size |
| Self test | `qa.py selftest` plants a fault for every code and proves each gate still catches it |
| Approval | `qa.py approve`, `diff` and `verify`: what was reviewed is pinned by hash, and what changed since is named frame by frame |

## Commands

From a working folder holding a copy of the engine (`cp -r skills/kinograph/engine/. <folder>/`), each run as `uv run --no-project --with-requirements requirements.txt python <command>`:

| Command | Result |
| --- | --- |
| `run_all.py proof --size 1920x1080` | Proof gates and review sheets; ends `PROOF: PASS`, `FIX` or `NOT CHECKED` |
| `run_all.py full --size 1920x1080` | Frames, sound, master, mux and every gate; ends with `APPROVAL:` and one `DELIVERED` line |
| `qa.py check out.mp4 --scenes . --size 1920x1080 --fps 30 --bpm 120` | Every gate on a finished file, one coded row each |
| `qa.py approve --review <reply>`, `qa.py verify <file>` | Bind a review to the file; re-hash before delivery |
| `qa.py selftest` | Every gate against its planted faults |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). `python scripts/check.py`, ruff, skillcheck and the engine self test run in CI.

## License

[MIT](LICENSE). Pillow, numpy and ffmpeg keep their own licenses and are not bundled; nor are voice models, which you download yourself under their own terms.
