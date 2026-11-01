# Styles

A style card is the recipe for one kind of video. The scenario names one in its header (`style:`), the builder follows it, and the reviewer judges the look against it. Every card has the same sections:

- **Use when**: the job it does, what the scenario must supply, and the jobs it is not for.
- **Format**: default aspect, size, length, tempo and reading pace (`HOLD_PROFILE`).
- **Look**: four to six colours with roles, every text pair's WCAG contrast ratio, two font families with fallbacks, and the layout grid.
- **Motion**, **Sound**: easing, stagger, transitions and how both follow the beat grid; the `synth.py` instruments and where each sound effect lands.
- **Beat map**: the default length, bar by bar, with on-screen text placeholders and their windows.
- **Build notes**, **QA watch-outs**, **Variations**: engine helpers and registry, the gates this style is most likely to trip, a 9:16 or other cut and a shorter one.

## Router

| Card | Use when | Default length | Aspect |
|---|---|---|---|
| [signal](signal.md) | a product or feature launch, one idea per beat on interface-like panels | 20 s (15 to 30; cuts of 16 and 24) | 16:9 or 9:16 |
| [ledger](ledger.md) | a data story where every figure has a source the user supplied | 48 s (30 to 60; cut of 32) | 16:9, 9:16 cut |
| [blueprint](blueprint.md) | how a system or process works, a diagram drawn step by step | 60 s (45 to 90; cut of 45.6) | 16:9, 9:16 cut |
| [marquee](marquee.md) | a logo sting or title card | 6 s (4 to 10; cut of 4) | 16:9, 9:16 and 1:1 |
| [pulse](pulse.md) | kinetic type locked to the beat, for a social reel | 20 s (15 to 30; cut of 16) | 9:16, 1:1 cut |
| [cartridge](cartridge.md) | a playful 8-bit game parody, pixel art and chip music drawn in code | 32 s (20 to 40; cut of 22.4) | 16:9, 9:16 cut |

## How to pick

1. Start from the one thing the viewer must take away, not from a look:
   - something new to try: **signal**;
   - a number, and the user can say where it comes from: **ledger**;
   - how something works: **blueprint**;
   - a name to remember, as an intro, an outro or a title: **marquee**;
   - a line or a feeling for a phone feed, cut to music: **pulse**;
   - a story told for fun: **cartridge**.
2. Check the length and aspect in the router. A brief outside a card's range takes the card's variation, or another card; never stretch a beat map past its range.
3. When two fit, prefer the card whose main material the user already has: sourced figures (ledger), a product interface (signal), a mark (marquee), a list of parts and flows (blueprint). Say in one line why the other was not picked.
4. A number with no source never goes on screen in any card. Ask for the source, or cut the number.

## What every card shares

- **Contrast.** Every pair in a card's table was computed with the WCAG 2.x formula (`qa.contrast`, the one Q301 applies to real pixels) and clears 4.5:1, so any pair may carry text at any size. A brand colour that replaces a card colour is checked against every background the card names; under 4.5:1 it colours shapes, never words.
- **First and last frame.** Each background lists its PIL grey (0.299 R + 0.587 G + 0.114 B): Q501 and Q502 need a frame mean over 25, so every card opens on its hook fully drawn and ends on a held end card, never on black.
- **Tempo.** Every default tempo (75, 100, 120, 150 BPM) has a whole number of frames per beat at 30 fps (`formats.md`). Scenes are declared in beats, and every time in a beat map sits on its grid.
- **Placeholders.** A quoted placeholder in a beat map is as long, in words and characters, as the longest line its slot is built for. Replace it with a line no longer than it, then run `qa.py holds` on the scenario with the card's profile (SKILL.md, step 3); a SHORT line loses words, never reading time. The six beat maps print `HOLDS: OK` as written (2026-11-01).
- **9:16 margins.** Cards keep the bottom 400 to 440 px of a 9:16 frame, and a strip down its right side, empty. That margin is this card set's own: platforms draw their controls in places that differ and change, and no gate measures them (`formats.md`, Safe areas).
- **Originality.** No card imitates a named film, show, game, brand or product, and none uses a third-party logo or character. A mark appears only when the user supplies it.

## Fonts

Fonts are not bundled. Each card names two families under the SIL Open Font License, one for each of the engine's slots: `E.FONT_BOLD` (`bold=True`) and `E.FONT_REG` (`bold=False`). Put their paths first at the top of scenes.py, at import time, which the lint passes: `E.FONT_BOLD[:0] = [...]` and `E.FONT_REG[:0] = [...]`, followed by the card's fallbacks for the OS.

Use one static file per weight. `engine.font` opens a variable file (a `[wght]` in its name) at its default instance: Windows' variable `bahnschrift.ttf` drew the same ink as its Regular instance on Pillow 13.0.0, and its Bold instance 27 percent more, only after `set_variation_by_name` (checked 2026-10-31). Every family below sits in the `ofl/` tree of the google/fonts repository with its `OFL.txt`; static files, checked 2026-11-01:

| Family | Card | Static files |
|---|---|---|
| Inter | signal | unchecked: rsms/inter publishes one release zip (v4.1, not opened here), and google/fonts and the repo's `docs/font-files` hold only the variable file |
| Libre Franklin | ledger | impallari/Libre-Franklin, `fonts/TTF/LibreFranklin-Bold.ttf`, `-Regular.ttf` |
| Space Grotesk | blueprint | floriankarsten/space-grotesk, `fonts/ttf/static/SpaceGrotesk-Bold.ttf` |
| JetBrains Mono | blueprint | JetBrains/JetBrainsMono, `fonts/ttf/JetBrainsMono-Regular.ttf` |
| Fraunces | marquee | undercasetype/Fraunces, `fonts/ttf/Fraunces144pt-Bold.ttf` (one file per optical size) |
| Outfit | marquee | Outfitio/Outfit-Fonts, `fonts/ttf/Outfit-Regular.ttf` |
| Anton | pulse | google/fonts, `ofl/anton/Anton-Regular.ttf` (one weight) |
| Barlow | pulse | google/fonts, `ofl/barlow/Barlow-SemiBold.ttf` |

Downloading a font is the user's call: ask before fetching one. With no file at hand, the card's fallback draws the build. cartridge needs no font file: its grid font is part of the build.

## Adding a card

Copy this outline into `styles/<id>.md`, add a row to the router above and to the style table in SKILL.md:

```markdown
# <id>

<One line: what the video is.>

## Use when
- <the job, the length, what the scenario must supply>
- Not for: <the neighbouring jobs, and the card that does each>

## Format
- Default <aspect>, <WxH>, 30 fps, <N> s: <bars> bars at <BPM> BPM (a whole-frame tempo).
- `HOLD_PROFILE = "<display, caption or slow>"`.

## Look
| Role | Hex | Use |            (four to six colours; PIL grey for each background)
| Text | On | WCAG ratio |     (every text pair, computed, each 4.5:1 or more)
**Type.** <bold slot family>, <regular slot family>: SIL OFL, static files, fallbacks per OS, sizes at 1080.
**Grid.** <margins over the 4 percent gate, zones, the 9:16 reserve>.

## Motion
<easing by engine name, stagger, transitions.py transitions, how moves meet the beat>

## Sound
<tempo, synth.py instruments, each sound effect's landmark and moment, gains>

## Beat map
| Time (s) | Bar.beat | Visuals | On-screen text | Audio |
<rows that tile the default length on the bar grid; quoted placeholders with (a-b) windows>

## Build notes
<TIMELINE in beats, helpers, registry items, CUES, KEY_TIMES, STATIC>

## QA watch-outs
<the codes this style trips most, and how it avoids each>

## Variations
<another aspect, a shorter cut>
```

Before it ships: `qa.py holds styles/<id>.md` (with the card's `--profile`) prints `HOLDS: OK`; every ratio is recomputed with `qa.contrast`; every helper it names exists in `engine/`; the text is ASCII with LF line ends.
