# Voice

Offline narration: how `voice.synthesize` turns lines into `narration.wav` and `narration.json`, which engines exist and what each needs, how to audition voices, how far the word clock can be trusted, and how to write lines that sound right. Numbers come from `voice.py` (constant or function named) or from the dated measurements given.

## What `voice.synthesize` does

```
narr = voice.synthesize(lines, engine="kokoro-ts", voice=None, speed=1.0, folder="narration", fps=30, rule="ours", profile=None)
```

- **Lines** are strings (ids `L01`, `L02`, ... in order), dicts `{"id", "text"}` or `(id, text)` pairs. Ids must be unique and no text empty.
- **One cached file per line.** Each line becomes `folder/<key>.wav` plus a `folder/<key>.json` sidecar, where the key is the sha256 of the cache version, engine, model id (every model file the voice reads, hashed), code id (the engine's own code, its worker or bridge program and its package pins), voice, speed and text. A second run synthesizes nothing that is already cached, a line said twice is synthesized once, and the render never needs the engine. A new file is checked before it is cached (speech found, word times inside the file); a bad one is deleted, named, and not cached, so the next run asks the engine again.
- **Trim.** Speech runs from the first to the last 10 ms window whose peak is above -48 dBFS, with 40 ms kept on each side (`TRIM_WIN`, `TRIM_DB`, `TRIM_KEEP`; tunables, not measurements). A file with nothing above -48 dBFS raises: the engine wrote silence.
- **Slots.** Each line gets a slot on one timeline, its scene's length:
  - `rule="ours"` (the default, our own design): `max(0.35 s + spoken length + 0.7 s, qa.min_hold(text, profile))` (`LEAD`, `TAIL`), so the voice has room before and after and a caption of the same words still meets its reading hold (`profile` as in `qa.HOLD_PROFILES`, None is display).
  - `rule="showtime"`: the trimmed clip plus 0.4 s (`GAP`), plus 0.8 s after the last line (`END_TAIL`); a slot then runs from one line's start to the next line's start.
  - With `fps` set, every slot ends on a whole frame (the frame count is rounded up).
- **Output.** `folder/narration.wav` (mono, 16-bit, 44.1 kHz, every line in its slot) and `folder/narration.json`, also returned as a dict: `engine`, `model`, `voice`, `speed`, `sr`, `fps`, `rule`, `profile`, `trim`, `duration`, `samples`, `file`, and `lines`, one per line with `id`, `text`, `start`, `end`, `speech_start`, `speech_end`, `slot` (`start`, `end`, `duration`), `file`, `clip`, `timing` (`engine`, `partial` or `none`) and `words` (`[{w, start, end}]`, plus `est: true` on a time shared out rather than heard).
- It prints one line per run: `voice: <engine> (<voice>): synthesized <n> of <m> lines, <k> from cache -> <folder>/narration.json (<s> s)`, and says which lines have no word times or only shared-out ones.

### Using it in a build

- Run `voice.synthesize` once, from the working folder, before the proof. `scenes.py` reads `narration.json` (`voice.load_narration(path)`) and never calls `synthesize`: every render worker imports scenes.py.
- Scene lengths come from the slots: `N["lines"][i]["slot"]["duration"]` as each scene's `dur` in `TIMELINE`.
- A word that carries a cue: `C.snap(voice.word_cue(N, "now"), FPS)`. `word_cue(narration, word, n=1, est=False)` finds the n-th time the word (or a phrase's first word, as in `"Vatican City"`) is spoken, in line order, ignoring case, punctuation, curly quotes and accents. It raises with the closest words when the word is not there, when its line has no word times (its engine gives none), and on a shared-out time unless `est=True`.
- The mix: `voice.dec("narration/narration.wav")` (any audio file to float32 mono at 44.1 kHz through ffmpeg, run with `-nostdin`) and `voice.duck_mix(bed, voice)` (`sound.md`).
- `voice.span(y)` gives speech start and end (10 ms RMS windows within 40 dB of the loudest), `voice.trim(y)` the trim bounds in samples, `voice.slot(line, rule, last, profile)` one slot.

## Engines

`voice.ENGINES` holds four. `voice.get_engine(name)` returns one; its `missing()` lists what is not installed or downloaded, and `status`, `use`, `needs` and `licence` say the rest. `synthesize` stops with `voice engine <name> is not ready (<status>). Missing: ... Needs: ...` when files are absent.

| Engine | Status (from `voice.py`) | Word times | Needs |
|---|---|---|---|
| `kokoro-ts` | The default narrator (`NARRATOR_ENGINE`, voice `af_heart`). Tested 2026-10-29 on Windows 11 with af_heart, af_bella, am_michael and bf_emma | Yes, from the model's per-phoneme durations | A side Python 3.13 environment that uv builds (kokoro-onnx 0.6.1 declares Python below 3.14) with kokoro-onnx 0.6.1, onnxruntime 1.31.1, phonemizer 3.4.0, espeakng-loader 0.2.4 and numpy 2.5.4 (about 40 MB of wheels, fetched by uv on first use), plus the model files below |
| `sapi` | Tested 2026-10-28 on Windows 11 (Microsoft David and Zira). Windows only. A timing and plumbing fallback, not a quality option: the built-in voices sound robotic | Yes, from SAPI's word events | Windows PowerShell 5.1 with System.Speech; nothing to download |
| `kokoro` | Untested: written to the sherpa-onnx 2.0.1 API | No | sherpa-onnx 2.0.1 (about 19 MB of wheels) and the Kokoro-82M int8 model (132 MB, from the k2-fsa/sherpa-onnx `tts-models` release) in `<voices>/kokoro-int8-multi-lang-v1_0` |
| `piper` | Untested: written to the piper-tts 1.8.0 API | No | piper-tts 1.8.0 and onnxruntime 1.31.1 (about 65 MB of wheels) and voices from huggingface.co/rhasspy/piper-voices, 63 to 114 MB each, as `<name>.onnx` plus `<name>.onnx.json` in `<voices>/piper` |

Licences (`licence` on each engine): kokoro-ts runs kokoro-onnx (MIT), onnxruntime (MIT), phonemizer and espeak-ng (GPL-3.0) and the Kokoro-82M weights (Apache-2.0); sapi is part of Windows; kokoro is sherpa-onnx (Apache-2.0) with Apache-2.0 weights; piper-tts is GPL-3.0-or-later (the engine's note: keep it out of anything you redistribute), and each Piper voice has its own licence in its model card. Name the engine, the voice and the weights' licence in the delivery report (`delivery.md`).

Platforms: sapi exists only on Windows. kokoro-ts, kokoro and piper run through uv wherever uv runs, but only kokoro-ts has been tested, and only on Windows 11; on macOS and Linux, say it is untested there and listen to the first line before building on it.

### The voice files and the download

Model and voice files live outside every repo, one folder per engine, under `$KINOGRAPH_VOICES` or, when that is unset, `~/.cache/kinograph/voices` (`voice.VOICE_DIR`). For the default narrator:

```
<voices>/kokoro-82m-v1.0-onnx-timestamped/
  onnx/model.onnx          fp32, 325.5 MB
  voices/af_heart.bin      0.5 MB (one .bin per voice)
```

Both come from huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX-timestamped (weights Apache-2.0); keep the `onnx/` and `voices/` folders as they are there. `onnx/model_fp16.onnx` (163.2 MB) also loads, but the fp16 export can turn a line into NaN, so `onnx/model.onnx` is tried first.

Nothing is downloaded without the user's yes. Ask once, naming each file, where it comes from, its size and its licence; the builder agent never downloads anything. Until the files are there, offer music with captions, or sapi on Windows for a timing draft, and say plainly that there is no natural voice yet and why.

Engine notes from the code:

- kokoro-ts takes `speed` from 0.5 to 2.0; voices whose name starts with `b` (British) are phonemized as `en-gb`, the rest as `en-us`.
- sapi's rate is an integer from -10 to 10 (`round(10 * log3(speed))`). Its bridge writes 16 kHz 16-bit mono, because SAPI counts word positions as if the stream were that format (probed 2026-10-28: with its default 22.05 kHz file every word time ran 1.378x late). SAPI reads a number, a date or a price as several words; the script words after the first in such a token get shared-out times (`est`).
- kokoro (sherpa-onnx 2.0) skips any word missing from its lexicon without a sound, so `synthesize` raises first and lists them (`voice.oov_words`): write numbers as words, spell names as they sound, or add a lexicon line.

## Auditioning voices

`python voice_samples.py [out_folder]` speaks the same three lines (a short hook, a line with two proper names, and a slower explainer sentence) with every engine that is ready, into `narration_samples/<engine>/<voice>/narration.wav`. Its candidates for kokoro and kokoro-ts are af_heart, af_bella, am_michael and bf_emma; for sapi and piper, every voice found. Engines that are not ready are listed with what they miss, need and are licensed under; a voice that fails does not stop the others. It ends with a table of every sample (engine, voice, length, how many lines got word times) and exits 0 when at least one sample was made and none failed.

Offer two or three voices per tone, let the user pick by ear, and pass the choice as `engine=` and `voice=`; with no engine named, `synthesize` speaks as the default narrator.

## The word clock

kokoro-ts word times come from the model's phoneme durations, which run late against what is heard. `voice.KOKORO_LAG = 0.07` moves every Kokoro word time 70 ms earlier.

`voice.onset_offsets(narration, folder=None, gap=0.1)` measures it: for each heard word that opens a line or follows a pause of over 0.1 s, its start minus the first voiced 10 ms window of `narration.wav` from 50 ms before it, as `(line id, word, ms)`. Near 0 means the clock is right. Measured 2026-10-29 with a 50 ms shift: 24 af_heart words that open a line or follow a pause, on 12 lines, read a median +22 ms late (p10 -11, p90 +56; vowel onsets run later, and unvoiced consonants read early because the onset test waits for voicing); af_bella, am_michael and bf_emma read medians of +19 to +45 ms on 7 to 10 words each. With 70 ms, the same 24 af_heart words read a median of +2 ms (p10 -31, p90 +51). Run `onset_offsets` on the first real narration of any other engine or voice before trusting its word cues.

Q902 measures sound effects, not words: a word cue is as good as this clock. For a word that must hit a beat exactly, cue a word the voice says on its own after a short pause, and look for its onset in the spectrogram of `review/audio.png`.

## Writing lines for the ear

- One idea per line, and short lines: the slot grows with the speech, so long sentences make long scenes.
- Say it the way a person would say it out loud. Read the line aloud once; if you run out of breath or trip, rewrite it.
- Put the word that carries the moment (the number, the name, "now") where the voice can land on it, best after a short pause, so `word_cue` has a clean onset to hit.
- Write numbers, units and symbols the way they should be spoken ("three point five million", "forty percent"); the screen can show the digits. kokoro (sherpa-onnx) skips digits it cannot find in its lexicon, and SAPI reads a number as several words with shared-out times.
- Respell hard names in the voice text only, and keep the right spelling on screen; ask the user to check how those lines sound.
- Use commas and full stops for pauses. Never put an ellipsis on a line by itself: SAPI wrote silence for "...", which fails the trim check.
- Keep the caption and the spoken line the same words when both appear, so the reading hold and the voice agree; with narration, a caption is on screen before its first word is heard (`qa-gates.md`, gate 4).
- Leave the bed room: the music ducks 8 dB under speech (`sound.md`), so a busy bed under a dense line still competes with it.
