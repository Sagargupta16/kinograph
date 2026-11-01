#!/usr/bin/env bash
# setup.sh : first-run check for the praxinoscope skill. It installs nothing system-wide and can be run again at any
# time. Each dependency prints "ok" or "FIX <what> -> <how>"; the exit code is 1 when any of them needs fixing.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
fail=0

if command -v uv >/dev/null 2>&1; then
  echo "ok   uv $(uv --version | cut -d' ' -f2)"
else
  echo "FIX  uv missing -> winget install astral-sh.uv (Windows), brew install uv (macOS) or the installer at docs.astral.sh/uv, then open a new shell"
  fail=1
fi

if command -v ffmpeg >/dev/null 2>&1; then
  if ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libx264; then
    echo "ok   ffmpeg $(ffmpeg -hide_banner -version | head -1 | cut -d' ' -f3) with libx264"
  else
    echo "FIX  ffmpeg has no libx264 (videos fall back to AV1, VP9 or GIF) -> a full build: winget install Gyan.FFmpeg, brew install ffmpeg, or your distribution's ffmpeg"
    fail=1
  fi
else
  echo "FIX  ffmpeg missing -> winget install Gyan.FFmpeg (Windows), brew install ffmpeg (macOS) or your package manager's ffmpeg, then open a new shell"
  fail=1
fi

if command -v ffprobe >/dev/null 2>&1; then
  echo "ok   ffprobe"
else
  echo "FIX  ffprobe missing -> it comes with ffmpeg; reinstall ffmpeg"
  fail=1
fi

# the Python every build runs on: engine/.python-version, which each working folder gets with its copy of engine/
py="$(head -n 1 "$here/engine/.python-version" 2>/dev/null || echo 3.14)"

if [ "$fail" -eq 0 ]; then
  # the first run fetches that Python and the pinned wheels into uv's cache; every later run is instant
  if uv run --no-project --python "$py" --with-requirements "$here/engine/requirements.txt" python -c "import platform, PIL, numpy; print('ok   python', platform.python_version(), '| pillow', PIL.__version__, '| numpy', numpy.__version__)"; then
    :
  else
    echo "FIX  Python $py with the pinned Pillow and numpy did not install -> check the network once, then run setup.sh again"
    fail=1
  fi
fi

if [ "$fail" -eq 0 ]; then
  # ask engine.py itself which face it opens, so this check and the renders always agree (-B: no bytecode in the skill)
  if face="$(uv run --no-project --python "$py" --with-requirements "$here/engine/requirements.txt" python -B -c "import sys; sys.path.insert(0, sys.argv[1]); import engine; engine.font(40, bold=False); print(engine.font(40).path)" "$here/engine" 2>&1)"; then
    echo "ok   default font $face"
  else
    echo "FIX  no default font -> $(printf '%s\n' "$face" | tail -n 1)"
    fail=1
  fi
fi

if [ "$fail" -eq 0 ]; then echo "SETUP: PASS"; else echo "SETUP: FIX"; fi
exit "$fail"
