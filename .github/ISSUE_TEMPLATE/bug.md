---
name: Bug report
about: A video renders wrong, a gate misses or misflags something, a style or the skill gives bad guidance, docs are wrong.
title: "bug: <short summary>"
labels: bug
---

## What's broken

<!-- Which stage (storyboard, proof, render, review, approval), style, gate code or engine file. One sentence. -->

## Expected vs actual

<!-- What should happen, what happens instead. The gate row, a frame or the file helps most. -->

## Reproduction

1. Prompt or command used:
2. The PROOF, APPROVAL, DELIVERED or QA line it ended with:
3. Gate rows that look wrong (`qa.py check out.mp4 --scenes . --json qa.json`):

## Environment

- Claude Code version (`claude --version`):
- OS:
- Python (`uv run python --version`) and ffmpeg (`ffmpeg -version`, first line):
- praxinoscope version (from `.claude-plugin/plugin.json`):
