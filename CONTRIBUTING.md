# Contributing to kinograph

Thanks for helping. kinograph is one skill, two agents, six styles and a Python engine whose gates are measured and self-tested. The most welcome changes make videos look or sound better, or make a gate catch a real fault it missed.

## Setup

```bash
git clone https://github.com/Sagargupta16/kinograph
cd kinograph
bash skills/kinograph/setup.sh
pip install -r requirements-dev.txt
```

`setup.sh` checks uv, ffmpeg with libx264, the pinned Pillow and numpy and a usable font, and ends `SETUP: PASS`. To try your clone as a plugin, add it as a local marketplace (`/plugin marketplace add <path to your clone>`) and install `kinograph@kinograph`.

## What a pull request must pass

- `python scripts/check.py`: no en or em dashes, no secrets, no absolute home paths, LF line ends, valid skill frontmatter, working relative links, and matching versions in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and `CHANGELOG.md`.
- `ruff check skills/kinograph/engine scripts` and `ruff format --check skills/kinograph/engine scripts`.
- `npx -y @sagargupta1610/skillcheck@0.2.5 lint skills`.
- The engine self test, from a copy of the engine so `qa_fixtures/` comes along:

  ```bash
  cp -r skills/kinograph/engine/. /tmp/praxi-selftest/
  cd /tmp/praxi-selftest
  uv run --no-project --with-requirements requirements.txt python qa.py selftest
  ```

  It must end `SELFTEST: PASS` with every code covered and 0 expected gaps.
- A change to drawing, sound or a gate: render the template at 1920x1080 and at 1080x1920 (`run_all.py proof`, then `run_all.py full`, then `qa.py check out.mp4 --scenes . --size WxH --fps 30 --bpm 120`) and paste the `PROOF`, `DELIVERED` and `QA` lines into the pull request.

## Adding a style

Copy the template in `skills/kinograph/styles/README.md`. A new style needs its palette's contrast ratios, a beat map that passes `qa.py holds`, and one proof render made with it, attached to the pull request.

## Adding or changing a gate

Every Q code has planted-fault fixtures in `skills/kinograph/engine/qa_fixtures/`. A new code needs a fixture that makes it fire on the right item, time and value, and a row in `skills/kinograph/references/qa-gates.md`. Calibrate a new gate on real renders before trusting it: a scan that looks right on paper can flag dozens of false hits a minute.

## Conventions

- Plain English, LF line ends, no en or em dashes, no emoji.
- Original work only: never paste text, code or style recipes from another video tool, style guide or course.
- Every change gets a `CHANGELOG.md` line under a concrete version; a release bumps the version in both `.claude-plugin` files.
