# Sound

How a video's sound is made and checked: the clock it shares with the picture, the template score, the instruments, how a sound is placed on its moment, the cue sheet the gates read, the beat grid, the mix, the master, and what no gate hears. The builder writes the score from this page. [engine.md](engine.md) shows how a score is wired into `run_all.py` and lists every file a build writes, [qa-gates.md](qa-gates.md) has every Q code, [voice.md](voice.md) has narration, and [troubleshooting.md](troubleshooting.md) says what a rejected file means.

Each fact is read from the engine code (the function or constant is named) or comes from a run on 2026-11-01 on Windows 11 with Python 3.15.2, numpy 2.5.4, Pillow 13.0.0 and ffmpeg 9.0.2. The runs are the shipped template at 1920x1080 and 1080x1920, and scratch scores built at 640x360 for this page. `python` stands for `uv run --no-project --with-requirements requirements.txt python`, run from the working folder.

## One clock for sound and picture

Sound and picture round time the same way (`contract.py`):

- `frame_of(t, fps)` is the nearest frame to t seconds, halves up.
- `sample_of(t, sr)` is the nearest sample to t seconds, halves up.
- `frame_sample(frame, fps, sr)` is the first sample of a frame. Frame 60 at 30 fps is sample 88200 at 44.1 kHz, exactly 2.0 s. Frame 1 at 24 fps is sample 1837.5, rounded to 1838.

A sound placed on a frame cue (`frame=` and `fps=`) puts its landmark on that frame's first sample, so it lands on the frame where the picture changes.

| Rate | Where |
|---|---|
| 44,100 Hz | `audio.SR`, `synth.SR` and `voice.SR`: every bus, `mix_raw.wav`, `sfx.wav`, the cue sheet and `narration.wav`. `voice.dec` decodes any outside file to this rate |
| 48,000 Hz | `audio.SR_MASTER`: `audio.master` decodes the raw mix at this rate through ffmpeg, limits there and writes `mix.wav` |
| the gates' own | the decodes of the finished file (`Ctx.audio`): 48 kHz for the true peak, the cue confirm and the audio picture, 8 kHz for Q803 and the no-sheet onset detector, and each WAV's own rate for the mux check |

Only two steps change the rate: `voice.dec` brings a file in at 44.1 kHz, and `audio.master` takes the finished mix to 48 kHz. Inside a score everything is a count of samples at 44.1 kHz. A buffer made at another rate and added by sample count plays at the wrong speed: 44.1 kHz samples read as 48 kHz run 8.1 percent fast, so a sound meant for 8.0 s plays at 7.35 s, 650 ms early, and at 30 s it is 2.4 s early (`t x 44100 / 48000`). Build every buffer at `synth.SR`, bring outside audio in through `voice.dec`, and record the cue sheet at the rate of its buffers: Q902 resamples each sheet buffer from the sheet's `sr` to the stem's rate before it searches (`qa_sync.buf_of`).

Check the clock in a working folder:

```
python -c "import contract as C; print(C.frame_sample(60, 30, 44100), C.frame_sample(1, 24, 44100), C.whole_frame_beat(120, 30), C.whole_frame_beat(128, 30))"
```

It printed `88200 1838 True False`.

## The template score

`audio.render_audio(scenes, folder=".", fps=None)` is the score a build gets unless it brings its own; `run_all.deliver` calls it with `fps=E.FPS`. It reads `DURATION` and `BPM` (120 when absent) from `scenes`, and takes the cuts from `scenes.CUTS`, else from every `SCHEDULE` start after 0. Each cut's hit takes the label of the CUES entry with sound (kind `both` or `audio`) within half a frame of it (1 ms without fps). `fps` defaults to `scenes.FPS`, and with it the cut sounds are frame cues. It builds the two buses with `audio.bed` inside `synth.recording()` and writes four files into `folder`: `mix_raw.wav` (both buses), `sfx.wav` (the SFX bus alone), `cuesheet.json` and `cue_sounds.npz`. It returns their paths under the keys `mix_raw`, `sfx`, `cuesheet` and `cue_sounds`.

`audio.bed(dur, bpm, cuts=(), voice_spans=(), fps=None, labels=())` returns the music bus and the SFX bus at 44.1 kHz:

| Bus | Sound | When | Gain | Placed by |
|---|---|---|---|---|
| music | `audio.kick()`: 0.35 s of sine falling from 135 to 45 Hz | beats 1 and 3 of each bar, left out within 3 frames of a cut | 0.6 | onset |
| music | `audio.tick()`: 30 ms of noise, named `tick` on the sheet | half a beat after every beat | 0.25 | onset |
| music | `audio.tone(f, beat, 0.01, 0.35)`: a sine one beat long, 10 ms attack, decaying with a 0.35 s time constant | every beat; f is 220, 261.63, 196, then 246.94 Hz, one per bar | 0.3 | onset |
| sfx | `audio.whoosh(0.4)`: noise through a low-pass that opens, swelling and falling | its loudest point `WHOOSH_LEAD` (0.08 s) before each cut | 0.5 | peak, `offset=-0.08` |
| sfx | `audio.hit()`: a 70 Hz thump with a burst of noise, 0.5 s | on each cut, with the cut's CUES label | 0.4 | onset |

The kick is left out near a cut because the hit carries that beat (`audio._near_cut`: within 3 frames when fps is known, else within 0.1 s). `voice_spans` multiplies the music bus by 10 ** (-8 / 20) inside each span; `render_audio` passes none. `audio.music(dur, bpm, cuts=(), voice_spans=())` returns the same score as one buffer, with no frame cues and no labels. `audio.place(buf, snd, at, gain=1.0, align=None, **kw)` is `synth.place` under another name.

On the template (8.0 s at 120 BPM, cuts at 2.0 and 5.0 s) the sheet had 42 rows on 2026-11-01: 16 `tick` rows, 16 `tone` rows and 6 kicks on the music bus (the kicks at 2.0 and 5.0 s left out), and 2 whooshes and 2 hits on the SFX bus. The whoosh's loudest 50 ms sits 0.300 s into its 0.4 s, so it starts at 1.620 s for an apex at 1.920 s. The hits labelled `point lands` and `end card` start on the cut frames' first samples. The shared scale was 0.993, so a placing gain of 0.6 is recorded as 0.5957. Two runs wrote byte-identical `mix_raw.wav`, `sfx.wav`, `cuesheet.json` and `cue_sounds.npz`.

`audio.py` keeps its own small instruments for this bed, and their names clash with `synth.py`'s. `audio.kick`, `audio.whoosh` and `audio.tick` are other sounds than the `synth` ones. `audio.noise(d, seed=1)` takes seconds and draws standard normal noise from a fixed seed, where `synth.noise(name, n, *args)` takes a sample count and draws uniform noise seeded from the name.

## The instruments

`synth.py` makes every sound in numpy, as a mono float array at `synth.SR`. "Lands by" is the default alignment for that `sound=` name (`synth.ALIGN`), and "Heavy" is the cue sheet flag that Q804 counts (`synth.HEAVY`). "Peak" is the buffer's own sample peak before any gain, read with `landmarks` on 2026-11-01.

| Call | Length | Sound | Lands by | Heavy | Peak |
|---|---|---|---|---|---|
| `kick(g=1.0, seed=0)` | 0.4 s | a sine sweeping from 178 down to 48 Hz with a 2.5 kHz click, driven into tanh | onset | yes | -0.48 dBFS |
| `snare(g=1.0, seed=0)` | 0.25 s | noise over 1.5 kHz on a 190 Hz body | onset | no | +0.53 dBFS |
| `hat(op=False, seed=0)` | 50 ms; 200 ms with `op` | noise over 7 kHz | onset | no | -13.22 dBFS, open -12.68 |
| `clap(seed=0)` | 0.3 s | three bursts of noise between 900 Hz and 5.2 kHz, at 0, 11 and 23 ms, the last ringing on | onset | no | -7.52 dBFS |
| `bass(m, dur)` | dur | MIDI note m: a saw plus a sine, low-passed at 420 Hz into tanh, 5 ms attack | onset | no | -11.22 dBFS (m 45, 1 s) |
| `pad(notes, dur, fc=1400, att=0.25)` | dur | a chord of MIDI notes, three detuned saws a note, low-passed at fc, a linear rise over att seconds and a 0.3 s fall | pad | no | -5.29 dBFS ([57, 61, 64], 1.5 s) |
| `pluck(m, dur=0.4)` | dur | a saw and its octave, low-passed at 3.5 kHz, 2 ms attack | onset | no | -2.15 dBFS (m 69) |
| `riser(dur, seed=0)` | dur | a noise band that opens and climbs, loudest at its last sample | end | no | +6.70 dBFS (2 s) |
| `boom(dur=1.2)` | dur | a sine gliding from 98 down to 38 Hz, driven into tanh | onset | yes | -1.24 dBFS |
| `whoosh(dur=0.5, seed=0)` | dur | a noise band sweeping up, swelling to its middle | peak | no | +4.66 dBFS (0.5 s) |
| `tick(f=4200, seed=0)` | 20 ms | noise high-passed at 0.8 f | onset | no | -10.35 dBFS |

The peaks span about 20 dB, and a riser or a whoosh starts above full scale before its gain. The gains in a style card are written for these buffers; a gain of your own needs the same care (see The mix).

`synth.ALIGN` also lists names with no generator in `synth.py`: `hit` and `tone` (the template's), `swell` and `reverse` (by end) and `chord` (by pad). A sound of your own given one of those names lands that way. `impact` and `drop` are heavy names with no generator.

The parts to build more from: `tt(n)` (the time of each sample), `ex(n, tau)` (an exponential decay), `hz(m)` (MIDI note to Hz; 69 is A4 at 440 Hz), `saw(f, n, det=0.0)`, `lp(x, fc)` (a one-pole low-pass), `hp(x, fc)` (x less its low-pass), `noise(name, n, *args)` and `rng_for(name, *args)`. Two effects:

- `reverb(x, wet=0.2, taps=_TAPS)` adds five early echoes from 29 to 131 ms, each heard again at twice its delay with its gain squared. It returns an array as long as x: a 10,000-sample impulse came back 10,000 samples long, its first echo at 29.0 ms. Pad a sound with silence first to keep its tail.
- `duck(bus, times, depth_db=6, rel=0.12, dur=0.3)` dips a bus by depth_db at each time and lets it back with time constant rel; where two dips overlap, the deeper one holds. With the defaults the gain read 0.501 (-6.0 dB) at the dip and 0.959 at 0.299 s, then 1 from 0.3 s.

`python synth.py demo.wav` writes a 4 s demo that plays every generator at 120 BPM (`synth.build`). It printed `wrote demo.wav (4 s)`.

### Seeds

Every noisy generator seeds itself from its own name and arguments. `rng_for(name, *args)` hashes the name and the arguments, joined by `|` with numbers written as `%.9g`, through crc32 into a numpy Generator, and `noise(name, n, *args)` draws n uniform samples between -1 and 1 from it. So `hat(seed=3)` is the same array on every call and `hat(seed=4)` is another one (both checked on 2026-11-01), and adding, removing or reordering one sound never changes another's draws. Draw randomness of your own the same way, for example `rng_for("shaker", bar, beat)`. `synth.rng`, one shared RandomState seeded 7, is kept for older scores only: a draw from it moves every later draw.

A seeded score writes the same bytes on every run, and review relies on that. Approval hashes `mix_raw.wav` in 100 ms blocks (`contract.MIX_RAW`, `qa_approve.audio_blocks`), Q1301 reads a change to the audio alone as a NOTE, and `qa.py diff` names every 100 ms block that changed (Q1303). An unseeded draw would change blocks on every run with no change to the score. The lint for unseeded randomness (Q1202) reads `scenes.py` and the local modules it imports (`qa_lint.local_modules`); a score file that only `run_all.py` imports is not read, so its seeds are up to you.

## Putting a sound on its moment

### Landmarks

The first sample of a sound is rarely the instant a listener hears as its moment. `synth.landmarks(sig, sound=None, pad_db=-15.0)` finds those instants, in seconds from the first sample:

| Landmark | What it is |
|---|---|
| `onset` | the start of the first 1 ms block within 30 dB of the loudest 1 ms block |
| `peak` | the middle of the loudest window: 50 ms for `whoosh`, `riser`, `swell` and `reverse` (`synth.SLOW`), 5 ms for every other named sound. An unnamed sound takes 5 ms when its loudest 5 ms comes within 30 ms of its onset, else 50 ms |
| `end` | the end of the last 5 ms block within 50 dB of the loudest |
| `pad` | the attack point, pad_db under full level (-6 to -15 dB; anything else raises ValueError). An array that `synth.pad` returned reports it from its own ramp, `att x 10 ** (pad_db / 20)`. Any other sound is measured: the middle of the first 5 ms window within pad_db of the loudest |
| `ring` | `end` less the middle of the loudest 5 ms: how long the sound rings on after its climax |

It also returns `win` (the peak window), `peak_dbfs` and `pad_known` (the pad point came from the generator).

The ramp is known only for the very array the generator returned (`synth._KNOWN` holds it by the array's id while the array lives). A copy or a scaled array is measured instead, and a beating chord measures badly. On 2026-11-01 `pad([57, 61, 64], 1.5)` reported 44.5 ms at att 0.25 and 88.9 ms at att 0.5; the same arrays times 1.0 measured 34.5 ms and 205.9 ms. So set a sound's level with the `g` of `place`, never by scaling its array. A measured pad point carries a tolerance of `PAD_TOL` (0.65) times itself on the sheet (`landmark_tol`): 22.5 ms and 133.8 ms for those two copies.

### place, put and put_peak

`synth.place(buf, sig, at=None, g=1.0, align=None, sound=None, label="", stem="sfx", frame=None, fps=None, offset=0.0, pad_db=-15.0, landmark=None)` adds `sig` times `g` into `buf` so that one instant of `sig` sits on the event, and returns the row it records.

- **The event** is `at` seconds, or a frame cue: `frame=` and `fps=` put it on the frame's first sample (`contract.frame_sample`). `offset` moves the instant off the event, in seconds, negative for earlier: a lead-in.
- **The instant** is `align`: `start` (the first sample), `onset`, `peak`, `end` or `pad`, as in the landmark table; any other value raises ValueError. With no `align`, the `sound=` name picks it from `synth.ALIGN`, and an unnamed or unlisted sound lands by its onset. `landmark=` (seconds from the first sample) replaces the measured instant when you know it better.
- **Where it goes.** The first sample lands at the event less the instant, to the nearest sample. A start before 0 cuts the head off and fades what is kept in over 3 ms; anything past the end of `buf` is dropped. A sound that lands wholly outside `buf` adds nothing and records no row.
- **Warnings** (a Python `UserWarning`, printed in the audio stage): the instant lands before 0; a sound placed by its end rings more than `RING` (30 ms) past its climax, so the climax lands early; a sound with a `label` placed by its start or onset is heard more than 10 ms after the instant on its cue.
- **The name matters.** `sound=` is matched exactly. It picks the default alignment, the peak window and the heavy flag: `sound="kick2"` lands by its onset, gets the unnamed peak rule and is not heavy, so Q804 never counts it as heavy. Q804's lead-in test matches by substring, so `whoosh_soft` is still a lead-in.

`put(bus, sig, t0, g=1.0, **kw)` is `place` with `align="start"`, and `put_peak(bus, sig, event_t, g=1.0, **kw)` is `place` with `align="peak"`. Both take every keyword of `place`.

Which instant to put on a cue:

| The moment | Place it | Why |
|---|---|---|
| a drum, hit, pluck or tick on the frame where something lands | by its onset (the default for those names), as a frame cue | its first audible energy is the event |
| a whoosh into a cut | `sound="whoosh"` (peak) with `offset=-audio.WHOOSH_LEAD` | its apex leads the cut by 80 ms, as the template's does |
| a riser or swell into a drop | `sound="riser"` (end) | it climaxes on its last sample: `riser(2.0)` rang 10.1 ms, under `RING` |
| a pad or chord heard on a moment | by its pad point (the default for `pad` and `chord`) | it starts from silence; its -15 dB point is when it is heard |
| a sound whose instant you computed | `landmark=` | the sheet records that instant |
| a bed loop whose first sample is the beat | `put()` | there is no landmark to find |

`whoosh(0.5)` rings 191.7 ms past its climax, so placing it by its end warns and lands the apex early: place it by its peak.

### What Q902 measures

For each CUES entry with sound (kind `both` or `audio`), Q902 (`qa_sync`) takes the sheet rows that carry its label, the nearest in time when a label repeats, else the unlabelled rows within 100 ms of it, SFX bus first. It finds each row's own buffer on its stem by normalised cross-correlation, within 250 ms of where the sheet put it and at a match of 0.7 or more: on `sfx.wav` for an SFX-bus row, on `mix_raw.wav` for a music-bus row. The instant it hears is the start it found plus the row's `landmark_s`. For a row placed by its start or onset whose `audible_s` comes 5 ms or more after that landmark (`ATTACK_TOL`), it is the start plus `audible_s` instead. The heard time less the cue time is then judged (`qa_sync.verdict`):

| Offset | Row |
|---|---|
| later than one frame: `late_limit(fps)` is 1000 / fps ms and never over 60 (41.7 at 24 fps, 40.0 at 25, 33.3 at 30, 20.0 at 50, 16.7 at 60) | FIX |
| earlier than -40 ms | FIX |
| inside those, but outside -5 to +15 ms | NOTE |
| no sound found for the cue | FIX |
| a copy that cannot be told from its twins | NOT CHECKED |

So the landmark a placement records is the instant Q902 checks: name the instant a listener hears, and the cue lands. Give the cue's label to the sound that lands on it, never to its lead-in. A labelled whoosh placed 80 ms ahead is heard 80 ms early, a FIX (from the code); the template labels only its hits.

**A slow attack, measured.** On 2026-11-01 the example score below placed `pad([57, 61, 64], 1.5)` (att 0.25 s) on both of the template's cues. Placed by its start (`align="start"`), the pad's audible point sat 44.5 ms after its first sample. `place` warned `pad at 2.000 s ('point lands') is heard 44 ms after the instant placed on its cue (a slow attack): place it with align='pad', or pass landmark=, so the attack lands on the cue`, and Q902 read `point lands at 2.00 s: pad (start) is heard +44.5 ms late (FIX past +33.3 ms at 30 fps)` for both cues, so the file was rejected. Placed by its pad point, the same pads read `all 2 cues land: audio worst +0.0 ms on sfx.wav`. At att 0.5 the pad point is 88.9 ms. A sheet row with no `audible_s` (one written by hand) gets an estimate from its buffer instead (`qa_sync.attack_of`): 33.4 ms at att 0.25 and 54.8 ms at att 0.5 on those chords.

## Stems and the cue sheet

The sync and stack gates read what the score says it did. `with synth.recording() as sheet:` opens a `CueSheet` (at `synth.SR` unless given `sr`), and every `place`, `put` and `put_peak` inside the block adds one row to it. Leaving the block puts back the sheet that was open before, or none. `sheet.write(folder=".", scale=1.0)` multiplies every row's gain by `scale` and writes two files through `contract.write_cuesheet`, returning their paths:

- `cuesheet.json`, `{"sr": ..., "cues": [row, ...]}`;
- `cue_sounds.npz`, each placed sound's whole buffer, before gain, as float32 under the key `c<i>`.

Each row holds the keys of `contract.CUESHEET_KEYS`:

| Key | Holds |
|---|---|
| `i` | the row's index, and its key `c<i>` in `cue_sounds.npz` |
| `label` | the CUES label the sound serves, or `""` |
| `sound` | the `sound=` name |
| `t` | the event time in seconds, offset included |
| `align` | the instant placed on `t` |
| `landmark_s` | seconds from the first sample to that instant |
| `start_s` | where the first kept sample went, clipped at 0 |
| `gain` | the placing gain times the write scale |
| `peak_dbfs` | the buffer's own sample peak |
| `heavy` | true when the name is kick, hit, boom, impact or drop |
| `bus` | `sfx` or `music`, from `stem=` |
| `trim_s` | seconds cut off the head |
| `audible_s` | seconds from the first sample to the -15 dB attack point |
| `landmark_tol` | how far a measured landmark may be off; 0 when the generator reported it |

Two buses at one scale:

- Put every sound that serves a cue on the SFX bus (`stem="sfx"`, the default) and the bed on the music bus. `sfx.wav` holds the SFX bus alone, so Q902 finds a cue's sound there with no bed under it. Q804 counts SFX rows, and music rows only when they carry a label.
- Write `mix_raw.wav` (music plus SFX) and `sfx.wav` with `audio.write_wav(path, mono, voice=None, scale=...)` at one scale, and give `sheet.write` the same scale. Then `sfx.wav` matches the SFX part of `mix_raw.wav` sample for sample, the sheet's gains match both files, and Q802 can read the music bed as `mix_raw.wav` less `sfx.wav` (`qa_stack._bed_level`). `render_audio` takes 0.85 over the larger of the mix's peak and the SFX bus's peak, so both files fit.
- `write_wav` writes 16-bit stereo at `audio.SR`, the same mono in both channels. With no scale it peak-normalises to 0.85 and returns the scale it used. A scale you pass is not clipped: on 2026-11-01 the samples 0, 0.5, 1.2 and -1.2 written at scale 1.0 came back as 0, 16383, -26216 and 26216, the loud two wrapped round.

A score of your own must write all four files this way. Without `cuesheet.json`, Q902 falls back on an onset detector that gives one NOTE and says it guesses, Q804 gives one NOTE for the missing sheet, and Q802 cannot name the sounds at a peak. A sheet whose buffers or stems are missing makes Q902 NOT CHECKED. How a score is called from `run_all.py` is in [engine.md](engine.md#your-own-score). This is the scratch score used on this page, wired in that way:

```python
# score.py : this video's score, in place of audio.render_audio. A hat and bass bed on the music bus; on each
# cue with sound, a whoosh whose apex leads the cue frame and a pad chord heard on it, on the SFX bus.
from pathlib import Path

import audio
import contract as C
import numpy as np
import synth as S


def render_score(scenes, folder=".", fps=None):
    """Writes mix_raw.wav, sfx.wav, cuesheet.json and cue_sounds.npz, as render_audio does."""
    fps = fps or scenes.FPS
    beat = 60 / scenes.BPM
    n = C.sample_of(scenes.DURATION, S.SR)
    music, sfx = np.zeros(n), np.zeros(n)
    with S.recording() as sheet:
        for k in range(round(scenes.DURATION / beat)):
            hat = S.hat(seed=k)  # a fresh seed per hit: no two hats are the same noise
            S.place(music, hat, (k + 0.5) * beat, 0.3, sound="hat", stem="music")
        for bar in range(round(scenes.DURATION / (4 * beat))):
            root = S.bass(45, 3.5 * beat)
            S.place(music, root, bar * 4 * beat, 0.5, sound="bass", stem="music")
        for c in C.cues(scenes):
            if c["kind"] == "picture":
                continue
            f = C.frame_of(c["t"], fps)
            lead = dict(sound="whoosh", offset=-audio.WHOOSH_LEAD)
            S.place(sfx, S.whoosh(0.4), frame=f, fps=fps, g=0.2, **lead)
            chord = S.pad([57, 61, 64], 1.5)
            S.place(sfx, chord, frame=f, fps=fps, g=0.5, sound="pad", label=c["label"])
    # one scale for both files, folded into the sheet's gains
    scale = 0.85 / max(np.abs(music + sfx).max(), np.abs(sfx).max(), 1e-9)
    out = {"mix_raw": str(Path(folder, C.MIX_RAW)), "sfx": str(Path(folder, C.SFX))}
    audio.write_wav(out["mix_raw"], music + sfx, scale=scale)
    audio.write_wav(out["sfx"], sfx, scale=scale)
    out["cuesheet"], out["cue_sounds"] = sheet.write(folder, scale)
    return out
```

`sound="pad"` lands each chord by its pad point. With the template's `scenes.py` at 640x360 it gave `QA: PASS (49 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)`, a Q804 row of `4 placed sounds checked` with `20 music-bed or muted sounds not counted`, and `DELIVERED <working folder>/out.mp4 (0.3 MB, 8.00 s, -14.0 LUFS, -2.5 dBTP)`. For a change to the sound alone, `python run_all.py audio --size 640x360` makes, masters and checks the sound again on the same `video.mp4`; run after that build, it ended with the same `QA: PASS` and `DELIVERED` lines.

## Beats and tempo

A beat lasts `60 / BPM` seconds, which is `60 x fps / BPM` frames. `contract.whole_frame_beat(bpm, fps)` says whether that is a whole number:

| BPM | Used by | Beat | Frames at 30 fps |
|---|---|---|---|
| 75 | ledger | 0.8 s | 24 |
| 100 | blueprint | 0.6 s | 18 |
| 120 | the template, signal, pulse and marquee | 0.5 s | 15 |
| 128 | no card | 0.4688 s | 14.06, not whole |
| 150 | cartridge | 0.4 s | 12 |

The whole-frame tempos at other frame rates are listed in [formats.md](formats.md).

The beat maps in the style cards write a moment as bar.beat, both counted from 1, four beats to the bar: `3.1` is the first beat of bar 3. A score turns them into seconds with a helper such as this one:

```python
BPM = 120


def t(bar, beat):
    """Seconds at bar.beat, both counted from 1, four beats to the bar."""
    return ((bar - 1) * 4 + (beat - 1)) * 60 / BPM
```

At 120 BPM, `t(3, 1)` is 4.0 and `t(4, 1)` is 6.0, the cut into signal's first idea and that idea's moment. A fraction works too: `t(1, 2.5)` is the off-beat after beat 2.

How a card's tempo reaches every part:

1. The card's Format section gives the default tempo. The scenario header carries it as `bpm:`, and the builder's brief as BPM.
2. `scenes.py` sets `BPM` and gives its scene lengths in beats with `compile_schedule(TIMELINE, bpm=BPM)`; each instant is then rounded once to its frame ([engine.md](engine.md)).
3. `render_audio` takes the bed's tempo from `scenes.BPM`, and a score of your own reads `scenes.BPM` too.
4. `run_all.deliver` passes `scenes.BPM` to `qa.check` for Q901, `qa_lint` reads it for Q905, and the Gantt sheet draws its bar lines from it.

Two NOTE-level gates hold the grid ([qa-gates.md](qa-gates.md)):

- Q901: every cut (`CUTS`, else every SCHEDULE start after 0) within one frame of the nearest beat (`qa.snap_ok`). The template: `2 cuts on the 120 BPM grid within 1 frame (from CUTS)`. A planned off-grid cut goes in `ALLOW["Q901"]`.
- Q905: one beat that is not a whole number of frames. The template: `one beat at 120 BPM is 15 frames at 30 fps`. Its fix lists the whole-frame tempos at the build's rate.

At a tempo off that list the bed and the picture part ways. A bed placed at beat times in seconds keeps the exact beat, while every cut and cue rounds to a frame, up to half a frame away. Put the sounds that must meet the picture on frame cues (`frame=frame_of(t, fps)`), as the template's cut sounds are, and let the bed keep the beat.

## The mix

**Levels.** The template's gains are in its table above, and each style card gives its own. The master brings the whole mix to -14 LUFS whatever its level, so a bus's absolute level does not decide loudness. A gain decides the balance, and how hard the master's limiter must work on the peaks, which Q805 judges. On 2026-11-01 the example score with its whoosh at 0.4 instead of 0.2 failed Q805 over its quiet bed: `the limiter took 0.90 LU, at most 2.8 dB at 4.90 s`, by the second whoosh's apex at 4.92 s, after a gain of +1.95 dB in 3 passes. At 0.2 the limiter took 0.00 LU and the gain was -1.14 dB. Q805's fix names the moment to lower.

**One sound per moment.** Q804 (`qa_stack.stack_rows`, a NOTE; [qa-gates.md](qa-gates.md)) counts the SFX-bus rows of the sheet and the music-bus rows that carry a label; unlabelled bed rows and rows at a gain of 0 or less are left out. It notes:

- two heavy sounds (the sheet's `heavy` flag) within 3 frames;
- two or more sounds on a `payoff=True` cue: those within 3 frames of it, and a lead-in still sounding 0.1 s before it;
- more than 2 sounds in any 100 ms.

A lead-in (a name that holds riser, swell, suck, reverse or whoosh) whose landmark or end falls within 3 frames or 100 ms, whichever is longer, of a heavy sound is one gesture with it and is not counted. On the template that gave `2 placed sounds checked`, `2 lead-in(s) into a heavy sound not counted` and `38 music-bed or muted sounds not counted`. Leave the bed's own heavy hits out near a designed one, as `audio.bed` leaves out its kick near a cut. A stack that is designed goes in `ALLOW["Q804"]`.

**When the peak is over.** A Q802 FIX names every sheet sound sounding within 50 ms of the loudest moment, the bed and SFX levels there, and the order in which to cut the designed sounds: impact, then chime or bell, then press or drop (`qa_stack.CUT_ORDER`).

**Pumping.** `synth.duck(bus, times, ...)` dips a whole bus under a list of times; `synth.build` ducks its music 3 dB under each kick. Keep it on the music bus: Q902 looks for each cue sound's own buffer on `sfx.wav`, and a dip reshapes what it finds there.

**Under narration.**

- `voice.duck_mix(bed, voice, sr=SR, depth_db=8)` pads both to the longer one and sets the bed to -18 dBFS RMS, measured over the whole bed. It pulls the bed down depth_db while the voice speaks (a -38 dB gate on 10 ms windows, 40 ms to close and 300 ms to let go) and lays the voice on top at a peak of 0.89, lifted 2 dB (times 1.26). On 2026-11-01, over a steady bed with a 1 s tone standing in for speech, the bed read -18.0 dBFS RMS before the tone and -26.0 under it; the voice peaked at 1.121 and the sum at 1.196, so the sum goes through a shared `write_wav` scale like any mix.
- `audio.bed(..., voice_spans=[(a, b), ...])` steps the template's music bus down 8 dB (times 0.398) inside each span, with no ramp, and leaves its SFX bus alone.
- The voice goes into `mix_raw.wav`, never into `sfx.wav`: Q902 searches `sfx.wav` for each cue's own sound, and speech there would bury it.

Slots, word cues and the engines are in [voice.md](voice.md), and the score that adds a voice in [engine.md](engine.md#narration-in-the-mix).

## The master

`audio.master(src, dst, ff="ffmpeg", I=-14, TP=CEILING, passes=6, tol=0.05)` turns `mix_raw.wav` into `mix.wav`:

1. It decodes `src` to 48 kHz stereo float through ffmpeg and measures it with ffmpeg's `ebur128=peak=true` filter (`audio.measure`, to three decimals). A mix under -60 LUFS is written out as it is, with a Q805 FIX that calls it silent.
2. One static gain takes it to I LUFS.
3. A true-peak limiter holds it at the ceiling (`audio._gain` over `audio.true_peak`). The 4x interpolator is four polyphase filters cut from one 129-tap Kaiser-windowed sinc (beta 10; `OS` 4, `TAPS` 32). The gain is worked out per 1 ms block, with 3 ms of lookahead and a 100 ms release, and adds no delay.
4. It measures again and nudges the gain by the measured slope, 1 to 3 dB of gain per LU, until I is within `tol` LU and the true peak is at or under TP, or the passes run out. A reading over the ceiling aims the limiter that much lower.
5. It writes `dst` as 16-bit stereo at 48 kHz and measures that file.

It returns `I`, `LRA` and `tp` (all measured on `dst`), `gain_db`, `passes`, `ceiling`, `limit_db` (the deepest gain reduction), `limit_t` (when it came), `limited_s` (seconds under more than 1 dB of it), `cost_db` (the loudness the limiter took), `input` (the source measured) and `rows`, which holds its one Q805 row (`audio.q805`). Q805 is a FIX when the result misses I by more than 0.1 LU or the ceiling by more than 0.05 dB, or when the limiter took more than `LINEAR_COST` (0.5 LU) off the programme or more than `LINEAR_DEPTH` (6 dB) at any moment. `audio.tp_limit(mix, ceiling_db, sr=SR_MASTER, look=0.003, release=0.1)` is the same limiter for a buffer of your own; it returns the limited mix and the gain per sample.

The template on 2026-11-01: the raw mix read -14.65 LUFS with a true peak of -1.38 dBTP, and the master gave `PASS Q805 master mix.wav: -14.04 LUFS (want -14), -2.00 dBTP (ceiling -2.0), gain +0.82 dB in 2 passes; the limiter took 0.22 LU, at most 1.4 dB at 2.01 s, over 1 dB for 0.09 s`, the same at both frame sizes.

To make and master the sound without drawing a frame (the builder does this at the proof, so the reviewer can read the sound):

```
python -c "import run_all, audio, contract as C; audio.render_audio(run_all.scenes); m = audio.master(C.MIX_RAW, C.MIX); print(C.line(m['rows'][0]))" --size 1920x1080
```

`import run_all` reads `--size` and imports `scenes` at that size. In a copy of the template it printed the same Q805 line. With a score of your own, call it in place of `audio.render_audio`.

**After the encode.** `audio.CEILING` is -2.0 dBTP because the AAC encode in the mux (`contract.AAC_ARGS`, 320 kb/s) raises the true peak. `run_all.master_and_mux` masters, muxes, and measures the muxed file with `qa.loud`. While the file's true peak is over -1.3 dBTP (`TP_MAX`, -1.0, less `TP_TOL`, the 0.3 dB meter tolerance), it masters again, at most 3 times (`RETRIES`). The new ceiling is the lower of the old one and the master's own true peak, less (file peak + 1.3 + `MARGIN` 0.2) divided by the slope: how far the file's peak followed the last change of ceiling, held between 0.25 and 1, and 1 at first. It stops early when the peak does not follow (a slope under 0.1). It then keeps the clean try (Q805 clean and the file inside -1 dBTP) with the lowest peak, or else the try with the lowest peak, and masters and muxes it again if it was not the last. Each try prints one line. The template needed no second try: `master: ceiling -2.00 dBTP, mix.wav -14.0 LUFS at -2.00 dBTP (Q805 PASS) -> out.mp4 -14.1 LUFS at -1.80 dBTP`.

The gates on the finished file ([qa-gates.md](qa-gates.md)):

| Code | Checks | Template, 2026-11-01 |
|---|---|---|
| Q801 | integrated loudness within -14 +/- 1 LUFS (`qa.loud`) | `loudness -14.1 LUFS` |
| Q802 | true peak at or under -1 dBTP (`qa_stack.TP_MAX`) | `true peak -1.8 dBTP (want <= -1); loudest moment 5.009 s` |
| Q903 | the audio and video streams start together, and the decoded audio lines up with `mix.wav` and with `mix_raw.wav` within 1 ms | `+0.00 ms` at 12, 45 and 85 percent against both |

Q805 comes from the build's master; `qa.py check` alone does not make it. `python qa.py calib` sends one white frame and a one-frame 1 kHz blip through `audio.master` and the mux and reads both back (Q906). It printed `blip lands +0.00 ms from the white frame (master +0.00 ms, mux and AAC +0.00 ms; ...)` and `CALIB: PASS (3 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)`.

## What no gate hears

The gates measure loudness, peaks, the limiter's work, the timing of the sheet's cue sounds, stacks and the mux. Nobody listens, and none of this is checked:

- whether the music is good: its key and harmony, notes that clash with a pluck or a chord, a timbre that grates, a sound that does not suit its picture;
- the balance of bed, effects and voice beyond what the limiter reports, and whether narration stays clear over the bed;
- a gap shorter than a second, since Q803 averages whole seconds. On 2026-11-01 the example score's `mix.wav` fell to -111.1 dBFS RMS from 3.80 to 3.98 s, where its bass and its pad had both stopped, while its quietest whole second read -26.0 dBFS RMS and Q803 passed;
- the timing of anything not in CUES, and the bed's own beats against the picture: Q901 holds the cuts to the grid, not the sounds;
- narrated words: Q902 measures the sheet's sounds, not speech ([voice.md](voice.md));
- stereo: every mix is the same mono in both channels (`audio.write_wav`);
- whether the last sound ends with the film: the mux cuts the longer stream to the shorter (`-shortest`).

### The audio picture

The reviewer cannot hear either. `qa.py audiostrip` draws the sound on one time axis into `review/audio.png`, 1600 px wide: the scenes, a spectrogram on a log frequency scale, one tick per cue coloured by its measured offset, momentary and short-term loudness with the integrated level, the true peak per 100 ms with every frame over -1 dBTP in red, and the numbered cells of the key sheet. At the proof it reads `mix.wav`, and after the render the finished file:

```
python qa.py audiostrip mix.wav --scenes .
python qa.py audiostrip out.mp4 --scenes .
```

On the template it printed `wrote review/audio.png (1600x656) in 1.4 s: I -14.1 LUFS, TP -1.8 dBTP, 0 of 80 frames over -1 dBTP; sync: 2 within 1 frame (of 2 audio cues)`. The example score's gap shows on it as a dark column just before 4.0 s that no row names. It exits 2 on a file with no audio stream, and 0 when the piece declares `SILENT` (`qa_audiostrip.run`). How the reviewer reads it: [reviewer.md](../../../agents/reviewer.md), under Reading the audio picture.

## Silent pieces

A piece with no sound on purpose says so in `scenes.py` (or with `--silent` on `qa.py check`):

```python
SILENT = True
```

`run_all.deliver` then makes no score and no master, and muxes the picture alone (`contract.mux_cmd` with no mix). Q706, Q801, Q803, Q805 and Q903 give no rows, Q802 and Q804 pass with `no audio by design (SILENT)`, and Q902 measures only the picture side of each cue. A size budget then counts no audio bitrate (`run_all.caps`). On 2026-11-01 the template with that one line added gave `QA: PASS (42 checks, 0 FIX, 0 NOTE, 0 NOT CHECKED)` and `DELIVERED <working folder>/out.mp4 (0.1 MB, 8.00 s, silent)`. Declare it only when the storyboard has no sound; it is not a way to quiet a fault.

## Narrated pieces

A voiced piece runs `voice.synthesize` once before the proof and takes each scene's length from its line's slot; the engines, the downloads, the slots and the word cues are in [voice.md](voice.md). For the score:

- `render_audio` takes no voice, so a voiced piece has a score of its own. It decodes `narration/narration.wav` with `voice.dec`, ducks the bed under it, adds it into `mix_raw.wav` and keeps it out of `sfx.wav` ([engine.md](engine.md#narration-in-the-mix)). `audio.write_wav(path, mono, voice=v, scale=...)` adds the voice as it writes; it keeps the mix's length, so a longer voice is cut at the end of the mix.
- A sound on a spoken word goes on the frame of `snap(voice.word_cue(narration, word), fps)`, as a frame cue that carries the word's CUES label.
- `voice.section_beats(speech_len, bpm, hold=0.5, lead=0.06, tempo=1.04, min_beats=2)` sizes a voiced section on the beat grid: lead, plus `speech_len / tempo`, plus hold, rounded up to a whole number of beat pairs and at least `min_beats`. At 120 BPM it gave 6 beats for 2.3 s of speech and 2 beats for 0.4 s.
