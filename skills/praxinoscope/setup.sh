#!/usr/bin/env bash
# Toolchain check for the praxinoscope engine. Run it once, from any folder:
#   bash <skill>/setup.sh
# It reads the machine and installs nothing system-wide (the first uv run may fetch the pinned Python and the
# pinned wheels into uv's own cache). Each passing check prints an "ok" line. Each gap prints one line that starts
# with FIX and says what is missing and how to get it. The last line is "SETUP: PASS" (exit 0) or
# "SETUP: FAIL (n to fix)" (exit 1).

set -u

here=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2> /dev/null || exit 1; pwd)
engine="$here/engine"
fixes=0
have_uv=0
pyver=""

ok() { printf 'ok    %s\n' "$*"; }
note() { printf 'note  %s\n' "$*"; }
skip() { printf 'skip  %s\n' "$*"; }
fix() {
  printf 'FIX   %s\n' "$*"
  fixes=$((fixes + 1))
}

first_line() { printf '%s\n' "$1" | sed -n '1p'; }
# the line that says what went wrong in a failed run: the first one uv marks "error", else the last non-empty one
error_line() { printf '%s\n' "$1" | awk '/^error/ { print; found = 1; exit } NF { last = $0 } END { if (!found) print last }'; }

# run_capture CMD ARGS...: stdout and stderr land in $cap (carriage returns dropped), the exit status in $capstatus
run_capture() {
  cap=$("$@" 2>&1)
  capstatus=$?
  cap=$(printf '%s\n' "$cap" | tr -d '\r')
}

# engine_python SOURCE: run SOURCE on the engine's interpreter exactly as the docs run any engine script, from the
# engine folder, through uv, on the pinned Python and the hashed requirements.txt. Nothing is written to the folder.
# shellcheck disable=SC2329  # it is only called through run_capture, which shellcheck cannot see
engine_python() {
  (
    cd "$engine" || exit 1
    printf '%s\n' "$1" | PYTHONDONTWRITEBYTECODE=1 uv run --no-project --python "$pyver" \
      --with-requirements requirements.txt python -
  )
}

# What the engine's interpreter reports: its version, then name, pin and installed version of each requirements.in
# pin. The two imports prove the wheels load, not just that they are installed.
PKG_PROBE='import sys
from importlib import metadata

import numpy
import PIL

print("px-python", sys.version.split()[0])
with open("requirements.in", encoding="utf-8") as pins:
    for line in pins:
        pin = line.split("#")[0].strip()
        if "==" in pin:
            name, want = (part.strip() for part in pin.split("==", 1))
            print("px-pkg", name.lower(), want, metadata.version(name))
'

# The font question goes to the engine itself: import it and load its default bold face.
FONT_PROBE='import os
import sys

sys.path.insert(0, os.getcwd())
import engine

try:
    face = engine.font(32)
except FileNotFoundError:
    print("px-font-missing")
else:
    print("px-font", getattr(face, "path", "(path not reported)"))
'

check_uv() {
  local bin ver
  bin=$(type -P uv)
  if [ -z "$bin" ]; then
    fix "uv is not on PATH. Get it: macOS 'brew install uv', Windows 'winget install --id astral-sh.uv', or on any system 'curl -LsSf https://astral.sh/uv/install.sh | sh'. Open a new terminal afterwards so PATH picks it up."
    return
  fi
  run_capture "$bin" --version
  if [ "$capstatus" -ne 0 ]; then
    fix "uv is on PATH at $bin but would not run ($(first_line "$cap")). Reinstall it from https://docs.astral.sh/uv/"
    return
  fi
  read -r _ ver _ <<< "$(first_line "$cap")"
  ok "uv $ver at $bin"
  have_uv=1
}

# Same search as contract.find_ffmpeg in the engine: PATH, then Homebrew on Apple silicon, then /usr/local.
find_ffmpeg() {
  local p
  p=$(type -P ffmpeg)
  if [ -n "$p" ]; then
    printf '%s\n' "$p"
    return
  fi
  for p in /opt/homebrew/bin/ffmpeg /usr/local/bin/ffmpeg; do
    if [ -e "$p" ]; then
      printf '%s\n' "$p"
      return
    fi
  done
}

check_ffmpeg() {
  local ff dir base probe ver
  ff=$(find_ffmpeg)
  if [ -z "$ff" ]; then
    fix "ffmpeg was not found on PATH, in /opt/homebrew/bin or in /usr/local/bin. Get a build with libx264: Windows 'winget install Gyan.FFmpeg', macOS 'brew install ffmpeg', Debian and Ubuntu 'sudo apt install ffmpeg'. Open a new terminal afterwards."
    fix "ffprobe is looked for beside ffmpeg, so it is missing too; the same ffmpeg package installs both."
    return
  fi

  run_capture "$ff" -version
  if [ "$capstatus" -ne 0 ]; then
    fix "ffmpeg at $ff would not run ($(first_line "$cap")). Reinstall it, or put a working one earlier on PATH."
  else
    read -r _ _ ver _ <<< "$(first_line "$cap")"
    ok "ffmpeg $ver at $ff"
    run_capture "$ff" -hide_banner -encoders
    if printf '%s\n' "$cap" | grep -Eq '^[[:space:]]*[A-Z.]{6}[[:space:]]+libx264[[:space:]]'; then
      ok "libx264 encoder is in that ffmpeg"
    else
      fix "the ffmpeg at $ff has no libx264 encoder, which every encode needs. Use a build that includes it: Windows 'winget install Gyan.FFmpeg', macOS 'brew install ffmpeg', Debian and Ubuntu 'sudo apt install ffmpeg', other Linux the full ffmpeg package of your distribution."
    fi
  fi

  dir=${ff%/*}
  base=${ff##*/}
  probe="$dir/${base//ffmpeg/ffprobe}"
  run_capture "$probe" -version
  if [ "$capstatus" -eq 0 ]; then
    read -r _ _ ver _ <<< "$(first_line "$cap")"
    ok "ffprobe $ver at $probe"
  else
    fix "ffprobe is missing or would not run at $probe, beside the ffmpeg. The engine looks for it there; install the full ffmpeg package, which ships both."
  fi
}

# The engine pins its Python in engine/.python-version. There is no fallback version: no file, no check.
read_pinned_python() {
  local file="$engine/.python-version"
  if [ -f "$file" ]; then
    read -r pyver < "$file"
    pyver=$(printf '%s' "$pyver" | tr -d '[:space:]')
  fi
  if [ -z "$pyver" ]; then
    fix "$file is missing or empty. The engine pins its Python version there and this script does not guess one. Restore the file (reinstall the plugin, or 'git restore' it in a clone)."
  fi
}

check_packages() {
  local name want have need seen=" "
  env_ok=0
  note "starting Python $pyver on the hashed pins (the first run may download them into uv's cache)"
  run_capture engine_python "$PKG_PROBE"
  if [ "$capstatus" -ne 0 ]; then
    fix "uv could not run Python $pyver with the hashed Pillow and numpy from engine/requirements.txt ($(error_line "$cap")). Go online once so uv can fetch them into its cache, or run 'uv python install $pyver'."
    return
  fi
  env_ok=1
  ok "python $(printf '%s\n' "$cap" | sed -n 's/^px-python //p') from uv (engine/.python-version says $pyver)"
  while read -r name want have; do
    [ -n "$name" ] || continue
    seen="$seen$name "
    if [ "$have" = "$want" ]; then
      ok "$name $have, equal to its requirements.in pin"
    else
      fix "$name $have is what requirements.txt installs but requirements.in pins $want. Make them agree: 'uv pip compile --generate-hashes requirements.in -o requirements.txt' in the engine folder."
    fi
  done <<< "$(printf '%s\n' "$cap" | sed -n 's/^px-pkg //p')"
  for need in pillow numpy; do
    case "$seen" in
      *" $need "*) ;;
      *) fix "engine/requirements.in has no $need== pin to compare with." ;;
    esac
  done
}

check_font() {
  local found
  run_capture engine_python "$FONT_PROBE"
  found=$(printf '%s\n' "$cap" | sed -n 's/^px-font //p')
  if [ -n "$found" ]; then
    ok "default bold font $found"
  elif printf '%s\n' "$cap" | grep -q '^px-font-missing'; then
    fix "no usable default font. Install Arial (Windows and macOS have it), or on Linux Liberation Sans or DejaVu Sans: Debian and Ubuntu 'sudo apt install fonts-liberation fonts-dejavu-core', Fedora 'sudo dnf install liberation-sans-fonts dejavu-sans-fonts'."
  else
    fix "importing the engine failed ($(error_line "$cap")). Run 'uv run --no-project --with-requirements requirements.txt python -c \"import engine\"' in the engine folder to see the whole traceback."
  fi
}

printf 'praxinoscope setup check, engine at %s\n' "$engine"
check_uv
check_ffmpeg

if [ ! -d "$engine" ]; then
  fix "the engine folder $engine is missing. Reinstall the plugin, or restore the folder in a clone."
else
  read_pinned_python
  ready=1
  [ "$have_uv" -eq 1 ] || ready=0
  [ -n "$pyver" ] || ready=0
  for f in requirements.in requirements.txt; do
    if [ ! -f "$engine/$f" ]; then
      fix "engine/$f is missing. It ships with the plugin: reinstall it, or 'git restore' the file in a clone."
      ready=0
    fi
  done
  if [ "$ready" -eq 1 ]; then
    check_packages
    if [ "$env_ok" -eq 1 ]; then
      check_font
    else
      skip "font check needs the Python environment above"
    fi
  else
    skip "python, pillow, numpy and font checks need uv, the pinned Python version and both requirements files"
  fi
fi

if [ "$fixes" -eq 0 ]; then
  echo "SETUP: PASS"
  exit 0
fi
printf 'SETUP: FAIL (%s to fix, then run this script again)\n' "$fixes"
exit 1
