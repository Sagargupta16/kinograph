# Sound

Music on the beat grid, sound effects placed by the instant you hear them, the stems and the cue sheet, voice over a ducked bed, the master and how sync is measured. Thresholds are the engine's own constants, named where it helps; measurements carry their date.

## Rates and buses

- Everything inside runs at 44.1 kHz: `SR = 44100` in `audio.py`, `synth.py` and `voice.py`. Only `audio.master` writes 48 kHz (`SR_MASTER = 48000`), once, at the end. Never mix a 48 kHz voice file into the 44.1 kHz bed sample by sample: played at 44.1 kHz it runs 8.8 percent slow, so a word 10 s in lands 0.88 s late (48000 / 44100). Decode it first with `voice.dec(path)`, which resamples to 44.1 kHz mono.
- A score has two buses, `music` and `sfx` (the `stem=` argument of `synth.place`). `audio.render_audio` writes them as `mix_raw.wav` (both) and `sfx.wav` (the SFX bus alone), at the same scale and rate, so the stem lines up with the mix sample for sample. The gates find each cue's sound on `sfx.wav`.
- Every placed sound goes on the cue sheet: `cuesheet.json` (one row per sound, the keys in `contract.CUESHEET_KEYS`) and `cue_sounds.npz` (each sound's own buffer, before gain).

## The beat grid

One grid serves the cuts, the scene starts and every sound: `t(bar, beat) = T0 + ((bar - 1) * 4 + (beat - 1)) * 60 / BPM`. For our own synthesized music T0 is 0 and the beat is exact. Declare scene lengths in beats (`compile_schedule(TIMELINE, bpm=BPM)`): the arithmetic stays exact and each cut is rounded once, to its nearest frame.

- A beat lasts `60 / BPM` seconds and `60 * fps / BPM` frames: 15 frames at 120 BPM and 30 fps, 14.06 at 128 BPM. Only some tempos give whole frames (the list per fps is in `formats.md`); Q905 notes the others, and their cuts land on the nearest frame while the audio keeps the exact beat time.
- Strong cuts go on bar lines, small changes on beats 2 to 4. Hard cut times come from `SCHEDULE` or `CUTS`, never typed by hand.
- Save the biggest change (the logo, the price, the end card) for beat 1 of a bar, and let a riser fill the whole bar before it. A past build got this right by making the bar before the drop the riser's bar and dropping on the next downbeat.
- Q901 holds every cut to within a frame of the grid; Q904 and Q905 check the frame grid (`qa-gates.md`, gate 9).

## The instruments (`synth.py`)

numpy only, no scipy. Every generator returns a mono float array at 44.1 kHz; noise comes from `rng_for(name, *args)` (a seed made from the sound's name and arguments with `zlib.crc32`), so adding or removing one sound never changes another.

| Generator | Signature and defaults | Sound |
|---|---|---|
| `kick` | `kick(g=1.0, seed=0)` | 0.4 s pitch-dropping sine with a click, soft-clipped |
| `snare` | `snare(g=1.0, seed=0)` | 0.25 s high-passed noise over a 190 Hz body |
| `hat` | `hat(op=False, seed=0)` | 0.05 s closed hat, 0.2 s open with `op=True` |
| `clap` | `clap(seed=0)` | three noise bursts, at 0, 11 and 23 ms |
| `bass` | `bass(m, dur)` | saw plus sine at MIDI note `m`, low-passed at 420 Hz |
| `pad` | `pad(notes, dur, fc=1400, att=0.25)` | detuned saws per MIDI note, linear attack `att` seconds |
| `pluck` | `pluck(m, dur=0.4)` | bright saw pluck |
| `riser` | `riser(dur, seed=0)` | noise sweep that opens and grows to its last sample |
| `boom` | `boom(dur=1.2)` | low pitch-dropping hit |
| `whoosh` | `whoosh(dur=0.5, seed=0)` | noise sweep, loudest in its middle |
| `tick` | `tick(f=4200, seed=0)` | 20 ms click |

Helpers: `hz(m)` (MIDI note to Hz), `saw`, `lp` and `hp` (one-pole filters), `reverb(x, wet=0.2, taps=...)` (five delay taps from 29 to 131 ms), and `duck(bus, times, depth_db=6, rel=0.12, dur=0.3)`, a sidechain dip on each time (on kicks, say). `python synth.py demo.wav` writes a 4 s demo at 120 BPM (`synth.build`): kick on every beat, offbeat hats and bass, snare on 2 and 4, a pad chord a bar, plucks on eighths, a riser into the end, a whoosh, a boom and a tick, the music ducked 3 dB on each kick and given reverb at 0.15.

The template score (`audio.bed`, used by `audio.render_audio`) is simpler, with generators of its own in `audio.py`: a kick on beats 1 and 3 (gain 0.6), a hat tick on each offbeat (0.25), a tone on every beat (its bass and pad line) whose pitch changes every bar (220, 261.63, 196 and 246.94 Hz, 0.3), and on every cut a whoosh (0.5) and a hit (0.4). The whoosh's apex leads the cut by `WHOOSH_LEAD` (0.08 s) and the hit's onset sits on it; a kick within 3 frames of a cut is left out, because the hit carries that beat. On the template the master's limiter took 0.22 LU and at most 1.4 dB (2026-11-01).

## Placing a sound by its landmark

`synth.place(buf, sig, at, g=1.0, align=None, sound=None, label="", stem="sfx", frame=None, fps=None, offset=0.0, pad_db=-15.0, landmark=None)` adds `sig * g` into `buf` so that the chosen instant of the sound, not its first sample, lands on `at` (to the nearest sample). `frame=n, fps=f` lands it on the first sample of a frame instead. Place every sound this way inside `with synth.recording() as sheet:`, so it lands on the cue sheet that Q902 and Q804 measure, and give the sound that serves a cue its CUES label (`label=`). `audio.place` is the same call.

| Align | The instant, measured from the sound's first sample (`synth.landmarks`) | Default for |
|---|---|---|
| `onset` | start of the first 1 ms block within 30 dB of the loudest | kick, snare, clap, hat, tick, hit, pluck, bass, tone, boom, any unnamed sound |
| `peak` | middle of the loudest window: 50 ms for whoosh, riser, swell and reverse, 5 ms for the rest (an unnamed sound still rising 30 ms after its onset takes 50 ms) | whoosh |
| `end` | end of the last 5 ms block within 50 dB of the loudest | swell, riser, reverse |
| `pad` | the -15 dB point of the attack (`pad_db=` -15 to -6) | pad, chord |
| `start` | the first sample | `synth.put` |

- `synth.put_peak` is align peak; `synth.put` keeps the first sample on the time (beds and lead-ins are timed that way). A 1 ms argmax on a noise whoosh moved its peak by up to 128 ms between seeds (2026-10-28); the 50 ms window halves that.
- A pad or chord lands its -15 dB attack with `align='pad'`: `synth.pad` knows its own ramp; any other generator that knows its instant passes `landmark=` (seconds). A measured pad point on a beating chord read 0.65 to 2.8 times the true one, so the sheet marks it with `landmark_tol` (`PAD_TOL = 0.65`); rise times over 80 ms are untested.
- A slow sound placed by its start or onset is heard late, and Q902 holds it to its audible attack (the sheet's `audible_s`): `synth.pad`'s 0.25 s attack is heard 44 ms in. A labelled `put` or onset row heard over 10 ms late warns; place such a sound with `align='pad'`.
- `offset=-0.08` lands a lead-in's apex just before a hit instead of on it: the template's whoosh peaks 80 ms before its cut hit (on the hit it stacked 1.8 dB of true peak onto it; 80 ms early, the pair peaks 0.1 dB under the hit alone, 2026-10-28). `align='end'` warns when the sound rings over 30 ms past its climax (`RING`; trim the tail, or align peak).
- A sound that would start before 0 loses its head, fades in over 3 ms, and warns when its landmark itself is cut.
- A whoosh peaks where the move it follows is fastest; a chime lands on the beat after the dot lands (half a beat later in a past build).
- A tween starts one frame before its cue (`cue - 1/fps`), so its first visible change lands on the cue frame; cue the sound at the moment the move reads as done, about its 97 percent frame, not its last frame.

## The stacking budget (Q804)

One sound per visible event. The stack guard reads the cue sheet and counts every SFX-bus sound, and a music-bus sound only when it serves a cue label:

- 2 or more heavy sounds (kick, hit, boom, impact, drop: `synth.HEAVY`) within 3 frames;
- a payoff cue (`payoff=True` in its CUES entry) with any second sound within 3 frames, or a lead-in still sounding 0.1 s before it;
- more than 2 sounds in any 100 ms (a taste rule).

A riser or whoosh whose climax or end lands within 3 frames or 100 ms of a heavy sound is one gesture with it and never counts, and the bed's own drum pattern is texture, not a layer. Keep the heaviest sound, move the others 4 or more frames off or cut them, or list a designed stack in `ALLOW["Q804"]`. Levels that worked in past builds: hits about -17 to -31 dB relative to full scale, ticks -28 to -31, whooshes about -18, all well under the music.

## Stems and the cue sheet

`audio.render_audio(scenes)` is the model for any score: it builds both buses inside `with synth.recording() as sheet:`, picks one scale that fits both files (`0.85 / max(peak of the mix, peak of the SFX bus)`), writes `mix_raw.wav` and `sfx.wav` at that scale with `write_wav`, and writes the sheet with `sheet.write(folder, scale)` (the scale is folded into every row's gain). For a scored piece, build the bed with `synth.py` the same way, then replace the `render_audio` call in `run_all.deliver` with your score: Q902 and Q804 measure from that sheet, and a sheet without its buffers or stems is NOT CHECKED, never quietly guessed.

## Voice over the bed

- `audio.bed(..., voice_spans=[(t0, t1), ...])` drops the music 8 dB inside each span.
- `voice.duck_mix(bed, voice, sr=44100, depth_db=8)` mixes a narration over a bed: the bed is set to about -18 dBFS RMS, the voice to a 0.89 peak and then raised by 1.26 (about 2 dB), and the bed ducks `depth_db` while the voice speaks (a 10 ms gate at -38 dB, fast attack, slow release).
- `voice.section_beats(speech_len, bpm, hold=0.5, lead=0.06, tempo=1.04, min_beats=2)` gives the whole, even number of beats a voiced section needs: `lead + speech_len / tempo + hold`, rounded up to an even beat count, at least `min_beats`.
- Words that carry a cue (a price, "now", a brand name) are timed by the engine in `narration.json`: `C.snap(voice.word_cue(N, "now"), FPS)` is the cue (`voice.md`). For a voice file from elsewhere, find the word's onset by RMS onset and convert it to video time with `t0 + (onset - trim) / tempo`: `t0` is where the clip starts on the timeline, `trim` the seconds cut from the file's head, and `tempo` the speed the clip is played at (1.0 unless it was sped up, as `section_beats`' `tempo` assumes).
- Voice must stay clearly above the music; the narration engines and the word clock are in `voice.md`.

## The master

`audio.master(src, dst, ff="ffmpeg", I=-14, TP=-2.0, passes=6, tol=0.05)` (`run_all.py` calls it on `mix_raw.wav` with the ffmpeg it found):

1. One static gain to -14 LUFS integrated (`I`), measured with ffmpeg's ebur128 (`audio.measure`, 3 decimals).
2. A true-peak limiter at `CEILING = -2.0` dBTP: the true peak comes from a 4x polyphase interpolator (`OS = 4`, `TAPS = 32` per phase, Kaiser-windowed sinc), the gain is worked out per 1 ms block with 3 ms of lookahead and a 0.1 s release, and no delay is added (the gain is already down before the peak).
3. ebur128 again, and the gain nudged by the measured slope until the loudness is within 0.05 LU and the true peak at or under the ceiling, up to 6 passes.
4. `dst` is written as 16-bit stereo at 48 kHz.

Q805 fails the master when it misses -14 by over 0.1 LU or the ceiling by over 0.05 dB, or when the limiter stops catching peaks and starts shaping the mix: over 0.5 LU of loudness taken (`LINEAR_COST`), or over 6 dB at one moment (`LINEAR_DEPTH`). The fix is in the raw mix: lower the loudest hits or the bed's peaks at the time the row names.

The mux encodes the audio once, AAC at 320 kb/s (`contract.AAC_ARGS`). The AAC encode raises the true peak: over 9 mixes on 2026-10-28 by up to 1.23 dB at 192k and at most 0.45 dB at 320k, so the -2.0 dBTP ceiling keeps 0.55 dB under the -1 dBTP gate. Even so, `run_all.master_and_mux` measures the decoded mp4 after every mux, and while it reads over -1.3 dBTP (`TP_MAX` -1.0 less the 0.3 dB R128 meter tolerance `TP_TOL`) it masters and muxes again, at most 3 times (`RETRIES`). The new ceiling is `min(ceiling, the mix's own true peak) - (excess over -1.3 + 0.2) / slope`, where 0.2 dB is `MARGIN` and the slope is how far the file's peak really moved per dB of ceiling over the last two tries (1 at first, held between 0.25 and 1). A peak that stops following the ceiling ends the loop, and the cleanest try is kept (Q805 clean, file inside -1 dBTP), because a lower ceiling makes the limiter work harder. If the file is still over, the line says to lower the hits Q802 names.

The template on 2026-11-01: `master: ceiling -2.00 dBTP, mix.wav -14.0 LUFS at -2.00 dBTP (Q805 PASS) -> out.mp4 -14.1 LUFS at -1.80 dBTP` (`audio.measure`: mix.wav -2.004 dBTP, the mp4 -14.056 LUFS at -1.788 dBTP, so the AAC encode added 0.22 dB).

## Sync, measured on the SFX stem (Q902, Q903)

Sound may lead the picture a little, never trail it. This is a house rule, justified by ITU-R BT.1359-1 (viewers detect sound more than 45 ms early or 125 ms late; a lip-sync figure, an analogy for SFX). Q902 holds every audio cue to it:

| Offset of the heard instant from the cue | Status |
|---|---|
| late by more than one frame (33.3 ms at 30 fps, 41.7 ms at 24, 16.7 ms at 60), never more than 60 ms (`CEILING`) | FIX |
| early by more than 40 ms (`EARLY`) | FIX |
| outside -5..+15 ms (`NOTE_LO`, `NOTE_HI`: the per-stage window of EBU R37, also lip sync) | NOTE |

- How it measures: each cue's own buffer from `cue_sounds.npz` is searched for on the stem by band-limited cross-correlation (250 Hz to 9 kHz, +-250 ms, a match of 0.7 or more), with overlapping recorded sounds taken out when needed; twins placed close together are measured as a group. The heard instant is the sound's landmark, or its audible attack when it was placed by its start or onset.
- Put cue times on frame starts (the picture can only change on a frame); an off-grid time can miss the NOTE window by up to half a frame.
- The mux and the master are held separately: Q903 compares the decoded mp4 with `mix.wav` and `mix_raw.wav` (FIX past 1 ms), and `qa.py calib` sends one white frame and a one-frame 1 kHz blip through `audio.master` and the mux; it must read 0 ms (Q906). Never correct a measured offset in the mixer.
- Where the 2026-10-28 batch's 37 to 87 ms of SFX lateness came from (measured on the five samples): the mux and the AAC encode add 0.000 ms (the 1024-sample priming is trimmed by the mp4 edit list), an earlier master built on ffmpeg's alimiter delayed every sound by 4.0 ms, and the bulk was placement: slow attacks placed by their first sample (`synth.pad`'s 0.25 s attack reaches -15 dB 44 ms in, a 0.9 s swell 272 ms in). Now Q903 and `qa.py calib` hold the mux and the master at 0 ms, and Q902 measures the placement (`qa-gates.md`, gate 9).
- Frame check: convert each cut time to a frame with `frame_of(t, fps)` (the nearest frame; halves round up, the one rule in every module) and confirm in the contact sheet that the frame at the cut shows the new scene and the frame before shows the old one.

## Music you did not make

To check kick alignment on outside music (or to prove ours): low-pass the music (35 to 140 Hz band), take the envelope, and mark each kick onset as the first upward crossing of 25 percent of the maximum with a 300 ms refractory window (sub bass can enter about 45 ms after a kick and would otherwise be counted). Fit `t = t0 + n * period` to the onsets within 40 ms of the grid by least squares. It passes when the largest residual is only a few milliseconds and the fitted BPM matches the preset. Autocorrelation tempo can come out as half or double: fold it into 90 to 180 BPM. For a score with no cue sheet, give a hard cue its band and region in CUES, as one past build's own sync check did (ticks above 1.8 kHz, the cluster under 200 Hz, the gear's box): `{"t": 12.0, "label": "gear", "band": (1800, 9000), "region": (x0, y0, x1, y1)}`. Before any outside music goes in, ask the user for it and its licence: the engine downloads nothing.
