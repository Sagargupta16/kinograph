# Delivery

The message that hands a finished video to the user. Every value in it is copied from a tool's output in this session, never retyped from memory or taken from an agent's summary; anything that was not run is listed as not checked.

## Before the report

1. The run ended with an `APPROVAL` line and one `DELIVERED` line (`engine.md`). A `REJECTED` or `UNCHECKED` line means there is nothing to deliver: a `<name>.rejected.mp4` or `<name>.unchecked.mp4` is never sent, shown as finished or described as a result.
2. The final reviewer replied REVIEW PASS, and `qa.py approve --review <reply>` recorded it.
3. `python qa.py verify <file>` printed `VERIFY: SAME`: the file is byte for byte the approved one.
4. One ffprobe run and one ebur128 run on the file give the numbers below:
   ```
   ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of default=nw=1 <file>
   ffmpeg -nostdin -hide_banner -i <file> -af ebur128=peak=true -f null -
   ```
   Read I and Peak in the ebur128 Summary. They agree with the `DELIVERED` line to its rounding.

## The report

```
Video: <absolute path, as the DELIVERED line printed it>
Duration: <s> s | Size: <MB> MB | Resolution: <W>x<H> | <fps> fps | <video codec> + <audio codec>
Loudness: <I> LUFS integrated, true peak <dBTP> dBTP (target -14 LUFS, at or under -1 dBTP)
Encode: rung <a | b | c>, <encoder and setting> because <why>

Checked:
- <the PROOF: line> and <the QA: line>, as printed
- reviews: <each reviewer id and verdict, e.g. proof-1 REVIEW PASS, final-1 REVIEW FIX, final-2 REVIEW PASS>
- <the APPROVAL: line> and VERIFY: SAME
Not checked:
- how it looks and sounds to a person: no script listens or watches; the reviewer read the sheets and frames
- photosensitivity: the flash gates measure WCAG 2.2 limits, but no tool certifies compliance
- <every NOT CHECKED row and every check not run, with its reason>
Weak spots:
- <each NOTE row left in, each reviewer P1 or P2 not fixed, anything close to a limit, with its time>
Sources:
- <claim> | <source> | <date read>, one line per fact on screen (the scenario's Facts table)
Media and credits:
- fonts: <the font files used>
- music and sound: <made in code by the engine, or the user's track and its licence>
- voice: <engine, voice, and the weights' licence> | none
- images, logos, footage: <each item the user supplied, with its source> | none
Next options:
1. <option>
2. <option>
3. <option>
```

## Filling each field

| Field | Where it comes from |
|---|---|
| Video | The `DELIVERED` line, as printed: `DELIVERED <absolute path> (<MB> MB, <s> s, <LUFS> LUFS, <dBTP> dBTP)`. The name follows `<slug>_<aspect>_<length>s_v<n>.mp4` (`formats.md`) |
| Duration, size | The `DELIVERED` line, and ffprobe's `duration` and `size` |
| Resolution, fps, codec | ffprobe's `width`, `height`, `r_frame_rate` and `codec_name` (rung a is h264 with aac) |
| Loudness | The `DELIVERED` line, and the ebur128 Summary. A silent piece says `silent` there and in the report |
| Encode | Which rung of the ladder made the file and why (`formats.md`): rung a needs nothing more than "libx264 present"; rung b names the missing libx264 and the encoder used; rung c says the GIF is a preview |
| Checked | The `PROOF:` and `QA:` summary lines, as printed (`QA: PASS (49 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)` on the template, 2026-11-01); every reviewer id with its verdict; the `APPROVAL:` line; `VERIFY: SAME` |
| Not checked | Always the two lines above about people and photosensitivity; then every `NOT CHECKED` row (on rung b, Q705, Q707 and Q708 by design) and anything skipped, such as a platform's own overlay zones (`formats.md`) or a voice engine's word clock on a voice nobody measured (`voice.md`) |
| Weak spots | Every NOTE row in the final check and why it stays (an `ALLOW` entry says it was designed), every reviewer P1 or P2 finding left open, and a true peak inside -1 dBTP but within the meter tolerance (run_all prints a `note:` line for that) |
| Sources | The scenario's Facts table: each claim on screen, its source and the date it was read. A claim with no source is not on screen |
| Media and credits | The font files `engine.font()` used (the first file in `FONT_BOLD` or `FONT_REG` that exists on this machine); the music, made in code by `audio.py` or `synth.py` with no samples, or the user's own track and its licence; the voice engine, voice and licence (`voice.md`); every image, logo or clip the user supplied, with its source |
| Next options | Two or three concrete follow-ups that fit the brief: a 9:16 cut (`--size 1080x1920`), a GIF preview (rung c), a shorter cut, a 720p cut for email, a poster PNG of the strongest frame, another voice from `voice_samples.py` |

## Rules

- Quote the lines exactly as the tools printed them; never round or retype a number.
- Say which rung made the file and why, every time, even when it is rung a.
- Never claim a check, a render or a review that did not run. A check that could not run is listed under Not checked with its reason, not left out.
- Never deliver past a size limit the user gave: the file must pass Q1001 against that limit (`--budget-mb` or `BUDGET_MB`, `formats.md`).
- When time runs out, deliver what is verified (a shorter cut, or the GIF preview made from a verified file) and list everything still open under Weak spots.
- A change after the approval reopens review: `qa.py diff --expect <windows>`, a fresh final reviewer, a new approval, then a new report.
