# Craft

How to turn a storyboard into frames that read: timing on the frame and beat clock, composition and type, motion and transitions, on-screen text, colour, the first frame, the end card and flash limits. Numbers come from the engine code (function or constant named) or from a dated run; a rule that is our own taste says so.

## Timing math

**Frames.** Every time in the engine goes through one clock: `frame_of(t, fps)` is the nearest frame, halves rounded up (`contract.py`, re-exported by `engine.py`). `snap(t, fps)` moves a time onto that grid, `stepped(t, rate)` counts held steps (drawings on twos at `fps / 2`, a typewriter, a ticking gear), and `on_grid(t, fps)` says whether a time sits on a frame. A frame lasts 33.3 ms at 30 fps, 41.7 ms at 24 and 16.7 ms at 60. Q904 notes any `SCHEDULE`, `DURATION` or `CUES` time more than 1e-3 frame off the grid, so write times as `frame / FPS` or snap them.

**Beats and bars.** A beat lasts `60 / BPM` seconds and `60 * fps / BPM` frames; a bar is 4 beats (`t(bar, beat)` in `sound.md`).

| BPM | Beat (s) | Frames per beat at 30 fps | Bar (s) |
|---|---|---|---|
| 90 | 0.667 | 20 | 2.667 |
| 100 | 0.6 | 18 | 2.4 |
| 120 | 0.5 | 15 | 2.0 |
| 128 | 0.469 | 14.06 | 1.875 |
| 140 | 0.429 | 12.86 | 1.714 |

At 30 fps the whole-frame tempos from 60 to 200 BPM are 60, 72, 75, 90, 100, 120, 150, 180 and 200 (Q905's list; other rates in `formats.md`). A tempo off that list still works: cuts land on the nearest frame and the audio keeps the exact beat, and Q905 says so as a NOTE.

**Declared timing.** All timing lives in `TIMELINE`, compiled by `compile_schedule(TIMELINE, bpm=BPM)` into `SCHEDULE`, `DURATION`, `CUTS`, `WINDOWS` and `CUES`. Give scene lengths in beats for a music piece and in slot seconds for a voiced one (`voice.md`); lengthen one scene and every later time moves with it. The arithmetic is exact (fractions), each instant is rounded once, and `5 / 30` reads as exactly 5 frames (`engine.md`).

**Reading holds.** A line must rest (alpha 0.98 or more) for at least `qa.min_hold(text, profile)` = max(floor, 0.5 s + 0.3 s per word, characters / cps + pad), with characters counted with spaces. The style sets `HOLD_PROFILE` in scenes.py; one item can carry its own `profile`.

| Profile (`qa.HOLD_PROFILES`) | cps | pad | floor | For |
|---|---|---|---|---|
| `display` (default) | 20 | 0.5 s | 1.0 s | titles, labels, end cards (our own pick) |
| `caption` | 17 | 0.5 s | 1.0 s | text read while the picture moves |
| `slow` | 15 | 1.0 s | 1.5 s | dense explainer cards |

Worked out with `qa.min_hold` (2026-10-31): "Shrink the gap" needs 1.4 s on display and 1.93 s on slow; "Almost every national flag is a rectangle." needs 2.6 s on display and 2.97 s on caption; a 37-character URL needs 2.35 s on display. `qa.slot_budget(has, profile)` turns it round: a line with 2.0 s on screen can carry at most 5 words and 30 characters on display, 5 words and 15 characters on slow. To fit a slot, cut words, not reading time.

**Storyboard to timeline.** Each storyboard row becomes one or more scenes; each quoted on-screen line keeps the time window written after it. Before anything is built, `qa.py holds <scenario.md>` checks every quoted line against its window, takes 0.4 s off each for the entrance, and prints `HOLDS: OK` or a `SHORT` line per problem with the words and characters that would fit; lines joined with ` / ` are read as one block. In the build, Q401 measures the real rests on the registry's frames, and Q403 fails a line that never reaches rest.

## Composition

**The safe area.** Text at rest stays inside a 4 percent pad on every edge (`qa.inside`, Q201): x 76.8 to 1843.2 and y 43.2 to 1036.8 at 1920x1080 (every aspect in `formats.md`). Vertical platforms draw their own controls over the bottom and the right edge, which no gate measures: keep key text, faces and the logo clear of them.

**A layout grid.** Pick one grid per video and put every element on it, then reuse it in every scene so cuts do not jump. Build it from the frame, not from fixed pixels: positions as fractions of `W` and `H` inside the safe box, sizes as fractions of `min(W, H)`, so the same scenes.py holds at 16:9 and 9:16 (the template centres every text on `W / 2`, at a height that is a share of `H` from its `PLACES` table). Compute it in one function that both `draw()` and `text_items()` call, as the template's `placed(name, lt)` does: then the registry cannot drift from the picture.

**Type sizes against the short side.** Size type from `min(W, H)`, never from `W`: the gates scale every size rule by `1080 / min(W, H)`, and a title sized from the width overflows the safe area at 9:16.

- The template sizes each text as a share of the short side in `PLACES` (0.11 for the title, 0.09 for the point and the end card, 0.045 for the link: 119, 97 and 49 px at a 1080 short side) and fits it to `W * 0.8` with `fit_size(s, size, maxw, bold=True, floor=36)`, which steps down 2 px at a time and never goes under the floor; cut copy rather than shrink further. Worked out on 2026-11-01: "A longer title line of seven words" set as the title fits at 97 px at 1920x1080 (`maxw` 1536 px) and at 55 px at 1080x1920, 1080x1080 and 1080x1350 (`maxw` 864 px).
- Key text is 36 px or more at 1080 (Q402). Large text, for the 3:1 contrast rule, is 36 px or more, or 24 px or more in bold (Q301).
- Under 24 px is texture: HUD labels, tags, footnotes. Nothing the viewer must learn may live there, and the text recorder only NOTEs unregistered text that small (Q204).
- `wrap(s, size, maxw)` fills lines word by word; test the widest line, and rewrite rather than leave a one-word orphan line.

## Motion

**Easing helpers in `engine.py`.** All take k from 0 to 1. Use `prog(t, t0, dur)` (0 before the move, 1 after it) to turn time into k, and `lerp(a, b, k)` to apply it.

| Helper | Shape |
|---|---|
| `linear(k)` | constant speed |
| `ease_out_cubic(k)` | `1 - (1 - k)**3`: fast start, soft landing |
| `ease_in_cubic(k)` | `k**3`: soft start, for exits |
| `ease_in_out_cubic(k)` | slow, fast, slow |
| `ease_out_expo(k)` | `1 - 2**(-10 k)`, exactly 1 from k = 1: a hard brake |
| `ease_out_back(k, s=1.70158)` | runs past 1 and settles back: with the default s it peaks at 1.100, a 10 percent overshoot (computed 2026-10-31) |
| `spring(t, stiffness=100, damping=10, mass=1)` | Remotion's spring in closed form, from rest, in seconds rather than k |
| `settle_time(stiffness, damping, mass, fps)` | seconds until that spring is at rest (Remotion's measureSpring) |

Springs, computed with `spring` and `settle_time` at 30 fps on 2026-10-31:

| stiffness, damping, mass | Peak | At rest after |
|---|---|---|
| 100, 10, 1 (the default) | 1.163 | 0.93 s |
| 100, 15, 1 | 1.028 | 0.73 s |
| 200, 20, 1 | 1.043 | 0.50 s |
| 100, 200, 1 (no bounce) | 1.000 | 0.77 s |

A springing item is at rest only from `settle_time` on; report its alpha and box in `text_items` with that in mind.

**The template's moves** (`scenes.motion`, `scenes.underline`, `scenes.drift`): each text slides in from the right by 6 percent of the short side (`SLIDE`, 64.8 px at 1080) while it fades up over 0.45 s (`ENTER`) with `ease_out_cubic`, and leaves to the left over its scene's last 0.3 s (`EXIT`) with `ease_in_cubic`; the end card's link starts 0.2 s after its line. The accent rule under the point grows out from the middle from 0.3 s to 0.9 s into its scene, with `ease_out_cubic`. Three soft pills drift sideways behind the copy at their own speeds, seeded with `rng("drift", name)`, so a long hold keeps moving (Q1102) while the end card still reads as held (Q503). The first scene is in place on frame 0 and the last never leaves.

**Stagger and overshoot.** The engine has no stagger helper: give each element its own start, `prog(t, t0 + i * gap, dur)`, from the same function that feeds `draw()` and `text_items()` (the template's `PLACES` gives each text a delay: the link comes in 0.2 s after its line). For overshoot use `ease_out_back` or a spring with damping under `2 * sqrt(stiffness * mass)`; keep overshoot off text that is about to be read, or wait for `settle_time`.

**Transitions (`transitions.py`).** Each is a pure `f(a, b, p, ...)` on two frames of one size and mode: p = 0 returns a and p = 1 returns b exactly, and the inputs are never changed. Ease p yourself, for example `wipe(a, b, ease_in_out_cubic(mix))`. `MENU` maps each name to its function; `MENU[name].flash_risk` is "low", or "check" for `dip`.

| Transition | Arguments after (a, b, p) | What it does |
|---|---|---|
| `crossfade` | none | dissolve |
| `wipe` | `direction="right", soft=0` | an edge reveals b; `soft` feathers it, in px |
| `push` | `direction="left"` | b pushes a out, both moving |
| `slide` | `direction="left"` | b slides in over a, which holds still |
| `iris` | `center=None, soft=1.5` | a circle opens from `center` (default the frame centre) |
| `clock` | `center=None, start=-90, soft=0.5` | a hand sweeps clockwise from `start` degrees (-90 is twelve o'clock); `soft` in degrees |
| `blinds` | `n=8, direction="down", soft=0` | n slats wipe open together |
| `dip` | `color="#000000"` | a fades to a flat colour by p = 0.5, then the colour fades to b; flash risk "check" |
| `luma` | `ramp, soft=0.1` | b shows where a grey ramp (an L image or a 0..1 array of the frame size) is under p |

Directions are `left`, `right`, `up` and `down`. Put a transition between two scenes with `Transition(kind, dur, split=0.5)` in `TIMELINE`: the window must be at least 2 frames and at most half the shorter scene (`compile_schedule` raises otherwise), and inside it `scenes_at(t, SCHEDULE)` gives both scenes and the mix. A kind other than a crossfade needs the same weights in `draw()` and `text_items()` (the template's `shares(t)`), or the registry drifts from the picture. Keep text out of a window (Q203 fails two texts crossfading in one place); a window under 0.5 s then leaves a changeover gap Q207 notes, so move the incoming text elsewhere.

**Held drawings and grain.** For drawings on twos, step time with `stepped(t, FPS / 2)`. `grain.grain(img, t, std=1.6, hz=None, tiles=4, seed=0)` adds film grain held for 2 frames at any rate (`hz` defaults to fps / 2), pure in t; call it last, after any weave shift. Grain is the main cost in file size (`formats.md`).

## On-screen text

**Every drawn string goes in the registry.** `text_items(t)` returns one dict per text drawn at t: `s` (the string as drawn), `box` (from `engine.text_box` with the same font, xy, anchor and `tracking=` as the draw), `fg`, `alpha`, `px`, `bold`, and when needed `texture`, `profile`, `reveal_end` and `ticker` (every key in `qa-gates.md`). While `draw(t)` runs, the text recorder logs every text call and holds the registry to it: drawn but not reported (Q204), box more than 2 px off (Q205), covered by a later layer (Q206), reported but not drawn (Q209).

**Draw text only with the engine helpers**, so the recorder and the lint see it (Q1205):

- `text(img, s, xy, size, fill="#FFFFFF", anchor="la", alpha=1.0, bold=True, scale=1.0, tracking=0)`;
- `text_outline(...)` (a solid stroke, `width=4`) and `text_halo(...)` (a soft dark halo, `radius=10`, `strength=0.6`) for text over busy pictures;
- `text_box(s, xy, size, anchor="la", bold=True, tracking=0)` for the registry box, `text_w` for widths, `wrap` and `fit_size` for fitting.

**Reveals.** A typewriter or a wipe-on reveal declares `reveal_end` on its item: at that time Q404 needs its ink to reach both ends of the box within 3 px and to be 0.98 of its ink at rest, so the box it reports must be the whole string's. Let the eased progress reach 1 by `reveal_end` (clamp it). Counters and clocks are `ticker=True`: only the value a run settles on must be held and pass contrast.

**Changeovers.** Never crossfade two strings in one place: fade the old one out, then bring the new one in (Q203). The gap between them should be 2 frames or less, or 0.5 s or more (Q207); a 2-frame gap repeats a frame between two moves (a Q1104 stall NOTE), so the only short gap that passes both is 1 frame, which is why the template's texts start to come in on their cut. With narration, a line is on screen before its first word is heard.

**Contrast.** Body text needs 4.5:1 against the real pixels behind it, large text 3:1 (WCAG 2.2; Q301 samples a ring of pixels just outside the box near the start, at the middle and near the end of every rest). The template's lowest is its link, 8.38:1 against 3:1 (2026-11-01). To raise it: darken the text tint, add `text_halo` or a scrim, or move the text off the busy area. Never set text that must be read in a blend mode such as difference or overlay.

## Colour

- One palette block at the top of scenes.py (the template's grounds `TEAL`, `CREAM` and `PLUM`, its text colours `SNOW`, `INK` and `LILAC`, the accent `MARK`, and `GLOW` and `SHADE` for the drifting shapes), named and used by name: Q1206 notes a colour literal written inside a function.
- One accent: the template's is `MARK`, the rule under the point; its drifting shapes are faint tints of white and ink (`GLOW`, `SHADE`), so nothing competes with it. One accent is our own taste, not a gate; the chosen style's palette wins (`styles/<id>.md`: signal, ledger, blueprint, marquee, pulse or cartridge).
- Check a pair before you build on it: `qa.contrast(fg, bg)` gives the WCAG ratio of two RGB tuples (turn a hex colour into one with `engine.hexrgb(h)[:3]`), `qa.lum` the relative luminance, and `qa.region_contrast(frame, box, fg)` measures against a drawn frame. A light brand colour on a pale ground (coral or mint on cream) usually needs a darker tint for text.
- Saturated colours survive the encode: the BT.709 chain round-trips saturated swatches within 8 levels (Q708; 1 level on 2026-10-31). Saturated red that alternates with another colour is what Q602 counts as a red flash.

## The first frame is the thumbnail

Many platforms show frame 0 as the poster, so it must carry the hook. Q501 fails a frame 0 whose grey mean is 25 or less, or whose standard deviation is 12 or less, both on the drawn frame at the proof and on the decoded file. Draw the headline or main visual fully at t = 0 and animate only the extras: the template's first scene is in place on frame 0 (`motion` skips the entrance of a scene that starts at 0), on a flat teal ground: frame 0 reads a grey mean of 71.0 drawn and 70.3 encoded, std 16.7 and 16.9 (2026-11-01). Offer a poster PNG of the strongest frame as well.

## The end card holds to the last frame

The last scene holds to the end with no exit (the template's `motion` keeps the departure at 0 for a scene that ends at `DURATION`). Q502 fails a last frame whose grey mean is 25 or less, a fade to black; Q503 notes a last second that changes 10/255 or more, an end card held under 1 s. The template reads 61.5 at its last frame and a change of 0.4/255 over its last second (2026-11-01).

## Flash limits

Nothing may flash more than three times in any one second (WCAG 2.2, success criterion 2.3.1).

- A general flash is a pair of opposing swings of 0.1 or more in linear relative luminance with the darker state under 0.8; a red flash is a pair of swings to or from saturated red (one state R/(R+G+B) of 0.8 or more, the two over 0.2 apart in u'v'). They count when they cover a quarter of the frame or of a 10 degree window (`qa-gates.md`, gate 6).
- More than 3 flashes in any sliding second is a FIX (Q601, Q602); 4 to 6 transitions a second held for 4 s of any 5 s is a NOTE (Q603).
- Check before the render: run `qa.flash_window(draw, t0, t1)` over every dip, wipe, hit and strobe, and `qa.flash_report(draw, DURATION)` over the film; both assume 30 fps, so pass `fps=FPS` at any other rate. `transitions.dip` is marked "check": a dip to white between dark scenes swings hard.
- What helps: at most 3 flips a second, a smaller flashing area, a softer swing (under 0.1 of luminance, or both states above 0.8), each flash spread over more frames, or no flash. No tool certifies compliance; tell the user when a passage is fast on purpose.
