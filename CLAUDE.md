# CLAUDE.md

> This file stacks on top of the workspace root at `C:\Code\GitHub\`:
> - Root [`CLAUDE.md`](../../CLAUDE.md) -- voice, rules, routing map, references, skills, slash commands, conventions.
> - Root [`MEMORY.md`](../../MEMORY.md) -- live facts across repos.
> - Root [`STATUS.md`](../../STATUS.md) -- live PR/CI/security dashboard.
> - [`.claude/resources/`](../../.claude/resources/README.md) -- deep reference for collaboration, workflow, git, OSS, debugging, voice.
>
> Read those first. The guidance below only adds **repo-specific context** -- it does not override anything in the root.

## Project

Public Claude Code plugin (`praxinoscope`) that plans, storyboards, animates, scores and renders short videos from code: one skill, a builder agent, a fresh-eyes reviewer agent, six original styles, a Python engine and 58 coded QA checks.

Installed with `/plugin marketplace add Sagargupta16/praxinoscope` then `/plugin install praxinoscope@praxinoscope`; the skill is `/praxinoscope:praxinoscope` and the agents are `praxinoscope:builder` and `praxinoscope:reviewer`.

## Stack

- **Language**: Python 3.14 with pinned Pillow and numpy (`skills/praxinoscope/engine/requirements.txt`, hashed), run through uv; ffmpeg with libx264
- **Framework**: none at runtime; the plugin is Markdown (skill, agents, styles, references) plus the engine
- **Database**: none
- **Package manager**: uv for the engine; `pip install -r requirements-dev.txt` (ruff) for development
- **Deploy target**: GitHub repo + self-hosted plugin marketplace (`.claude-plugin/marketplace.json`, `source: "./"`)

## Run

```
bash skills/praxinoscope/setup.sh
cp -r skills/praxinoscope/engine/. <working folder>/
uv run --no-project --with-requirements requirements.txt python run_all.py proof --size 1920x1080
uv run --no-project --with-requirements requirements.txt python run_all.py full --size 1920x1080
```

The last two run from the working folder. Every video is build output: it goes to `videos/<slug>/` in the user's folder and is never committed.

## Test

```
python scripts/check.py
ruff check skills/praxinoscope/engine scripts
ruff format --check skills/praxinoscope/engine scripts
npx -y @sagargupta1610/skillcheck@0.2.5 lint skills
uv run --no-project --with-requirements requirements.txt python qa.py selftest
```

Run the self test from a copy of the engine (`cp -r skills/praxinoscope/engine/. <folder>/`, so `qa_fixtures/` comes along). It must end `SELFTEST: PASS` with every code covered and 0 expected gaps. CI runs all of these on Ubuntu.

## Entry points

| Path | What |
| --- | --- |
| `skills/praxinoscope/SKILL.md` | The workflow the main chat follows: brief, style, storyboard approval, proof, review, render, approval, delivery |
| `agents/builder.md`, `agents/reviewer.md` | The two agents the skill launches |
| `skills/praxinoscope/styles/` | Style cards; `README.md` is the router |
| `skills/praxinoscope/references/` | Engine, gates, craft, sound, voice, formats, delivery, troubleshooting |
| `skills/praxinoscope/engine/` | The engine: `run_all.py` (stages), `qa.py` (gate CLI), `contract.py` (shared contract) |
| `scripts/check.py` | The repo gate (PX001 to PX008) |

## Repo rules

- **Original work only.** Never paste text, code or style recipes from another video skill, style guide, course or product into this repo, including private ones in this workspace. New styles are designed here and proven with a render.
- Every change gets a CHANGELOG line under a concrete version; a release bumps the version in both `.claude-plugin/*.json` files (`scripts/check.py` PX007 checks all three agree).
- Files are LF (`.gitattributes` sets `eol=lf`); check the bytes after any non-Edit write.
- A drawing, sound or gate change is proven by the template rendering at 1920x1080 and 1080x1920 with `PROOF: PASS`, one `DELIVERED` line and `QA: PASS` (0 FIX, 0 NOT CHECKED), plus `qa.py selftest`.
- A new Q code needs a planted-fault fixture in `engine/qa_fixtures/` and its row in `references/qa-gates.md`.
- No personal names or machine paths in shipped files; the plugin runs on Windows, macOS and Linux.
- **The README diagram** `docs/praxinoscope-flow.svg` is exported from `docs/praxinoscope-flow.workflow.json` with the archify skill. When the flow changes, update the cited sources and `meta.repository.revision` (a pushed commit), run archify `finalize workflow` with `--repo-root .` (it needs the `origin` remote), open the HTML in a Chrome DevTools page (the browser pane cannot open `file://`), run `Archify.exportMenu.run('svg')` while catching the blob from `URL.createObjectURL`, replace its two non-ASCII separators (U+203A, U+00B7) with `&gt;` and `|`, and look at it at 880 px in both themes.
