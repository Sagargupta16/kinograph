# engine.py : the drawing toolkit every scenes.py star-imports. Frame size and clock, easing curves, fonts and colour,
# layers (canvas, gradient, rounded boxes, soft shadows), text with the boxes it covers, and declared timing.
import math
import os
import zlib
from collections import namedtuple
from fractions import Fraction
from functools import lru_cache

import numpy as np

# the one frame clock (Z06), re-exported so `from engine import *` gives it to scenes.py
from contract import frame_of, frame_sample, on_grid, sample_of, snap, stepped  # noqa: F401

# ImageChops is not used here: it is imported so that scenes.py gets it from the star import as well
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont  # noqa: F401

# Output width and height in px, frames per second, and SS, the supersampling factor: frames are drawn SS times
# larger and brought down by finish(). run_all.py and every render worker set these before scenes.py is imported.
W, H = 1920, 1080
FPS, SS = 30, 1

# Where font() looks, in this order; the first file that exists and opens is used. One row per folder with its bold
# and its regular file: Arial on Windows; Arial or Helvetica on macOS (the system folders, then the user's); then
# Liberation Sans (drawn to Arial's widths) and DejaVu Sans in the folders the usual Linux packages install to.
_FONT_FOLDERS = (
    ("C:/Windows/Fonts", "arialbd.ttf", "arial.ttf"),
    ("/System/Library/Fonts/Supplemental", "Arial Bold.ttf", "Arial.ttf"),
    ("/System/Library/Fonts", "Helvetica.ttc", "Helvetica.ttc"),
    ("/Library/Fonts", "Arial Bold.ttf", "Arial.ttf"),
    (
        "/usr/share/fonts/truetype/liberation",
        "LiberationSans-Bold.ttf",
        "LiberationSans-Regular.ttf",
    ),
    (
        "/usr/share/fonts/truetype/liberation2",
        "LiberationSans-Bold.ttf",
        "LiberationSans-Regular.ttf",
    ),
    (
        "/usr/share/fonts/liberation-sans",
        "LiberationSans-Bold.ttf",
        "LiberationSans-Regular.ttf",
    ),
    (
        "/usr/share/fonts/liberation",
        "LiberationSans-Bold.ttf",
        "LiberationSans-Regular.ttf",
    ),
    ("/usr/share/fonts/truetype/dejavu", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"),
    ("/usr/share/fonts/dejavu-sans-fonts", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"),
    ("/usr/share/fonts/TTF", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"),
)
# the candidate files; put a .ttf of your own at the front of a list to set every title in it
FONT_BOLD = [f"{folder}/{bold}" for folder, bold, _ in _FONT_FOLDERS]
FONT_REG = [f"{folder}/{regular}" for folder, _, regular in _FONT_FOLDERS]
_FONT_HELP = (
    "install Arial (Windows and macOS ship it) or, on Linux, Liberation Sans or DejaVu Sans (Debian and Ubuntu: "
    "apt install fonts-liberation fonts-dejavu-core; Fedora: dnf install liberation-sans-fonts dejavu-sans-fonts), "
    "or put the path of an installed .ttf first in"
)


def clamp(x: float, a: float = 0.0, b: float = 1.0) -> float:
    """x held inside a..b (0..1 unless told otherwise)."""
    return max(a, min(b, x))


def lerp(a, b, k):
    return a + (b - a) * k


def prog(t: float, t0: float, dur: float) -> float:
    """How far a move that starts at t0 and lasts dur seconds has got at t: 0 before it, 1 once it is over."""
    elapsed = t - t0
    return clamp(elapsed / dur)


def linear(k):
    return k


def ease_out_cubic(k):
    return 1 - (1 - k) ** 3


def ease_in_cubic(k):
    return k**3


def ease_in_out_cubic(k: float) -> float:
    """Slow, fast, slow: the cubic ease-in up to the midpoint, its mirror after it."""
    if k < 0.5:
        return 4 * k**3
    return 1 - (2 - 2 * k) ** 3 / 2


def ease_out_expo(k: float) -> float:
    """A fast start that brakes hard; exactly 1 from k = 1 on."""
    if k >= 1:
        return 1.0
    return 1 - 2 ** (-10 * k)


def ease_out_back(k: float, s: float = 1.70158) -> float:
    """Runs past 1 and settles back; s sets the overshoot (the default, Penner's, is about 10 percent)."""
    u = k - 1
    return 1 + (s + 1) * u**3 + s * u**2


def spring(t, stiffness=100, damping=10, mass=1):
    """0 -> 1 position of a spring t seconds after release, from rest: Remotion's spring() with the same defaults,
    closed form. Damping under 2 * sqrt(stiffness * mass) overshoots, then settles; at or over it the spring moves
    as critically damped, as Remotion's does, so its damping: 200 'no bounce' config ports as it is. 0 for t <= 0."""
    if damping <= 0:
        raise ValueError("spring damping must be over 0, or it never comes to rest")
    if t <= 0:
        return 0.0
    w0 = math.sqrt(stiffness / mass)
    z = damping / (2 * math.sqrt(stiffness * mass))
    if z >= 1:
        return 1 - math.exp(-w0 * t) * (1 + w0 * t)
    w1 = w0 * math.sqrt(1 - z * z)
    decay = math.exp(-z * w0 * t)
    return 1 - decay * (math.cos(w1 * t) + z * w0 / w1 * math.sin(w1 * t))


def settle_time(stiffness=100, damping=10, mass=1, fps=None, threshold=0.005):
    """Seconds until spring() is at rest, by Remotion's measureSpring: the first frame under threshold of 1, moved on
    past any frame over it in the next 20 (Remotion's loop, its reset kept), then / fps. A registry can report a
    springing item as at rest from here."""
    fps = fps or FPS

    def off(f):
        return abs(1 - spring(f / fps, stiffness, damping, mass)) >= threshold

    f, limit = 0, 600 * fps  # ten minutes: a spring not at rest by then never is
    while off(f) and f < limit:
        f += 1
    done, i = f, 0
    while i < 20 and f < limit:
        f += 1
        if off(f):
            i, done = 0, f + 1
        i += 1
    if f >= limit:
        raise ValueError(
            f"spring({stiffness}, {damping}, {mass}) is not at rest within 10 minutes"
        )
    return done / fps


_FONT_CACHE = {}  # (whole px, bold) -> the face loaded for it


def _open_face(paths, px):
    """The first of paths that exists and opens at px, or None."""
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            return ImageFont.truetype(path, px)
        except Exception:  # noqa: BLE001, S112  a file that will not open (damaged, locked): try the next one
            continue
    return None


def font(size: float, bold: bool = True):
    """The face for size px (cut to a whole px), loaded once and reused: the first usable file in FONT_BOLD, or in
    FONT_REG when bold is False. FileNotFoundError, saying what to install, when no file in the list will do."""
    px = int(size)
    face = _FONT_CACHE.get((px, bold))
    if face is None:
        paths, name = (FONT_BOLD, "FONT_BOLD") if bold else (FONT_REG, "FONT_REG")
        face = _open_face(paths, px)
        if face is None:
            raise FileNotFoundError(
                f"engine.font: no file in {name} exists and opens ({', '.join(paths)}); {_FONT_HELP} "
                f"engine.{name}"
            )
        _FONT_CACHE[(px, bold)] = face
    return face


def hexrgb(h: str, a: int = 255) -> tuple:
    """A "#RRGGBB" colour (the # may be left off) as (r, g, b, a), with a as the alpha 0..255."""
    digits = h.lstrip("#")
    red, green, blue = (int(digits[i : i + 2], 16) for i in (0, 2, 4))
    return (red, green, blue, a)


def rng(*keys):
    """numpy Generator seeded by what is being drawn: rng("hook", "dust", frame). Strings go through zlib.crc32,
    ints (0 to 2**32 - 1: frames, indices) are used as they are, and the key count leads the seed, because numpy
    pads a seed with zeros (default_rng([5]) and default_rng([5, 0]) are the same stream). Seed each frame or
    element from its own keys, never from one stream advanced frame after frame: then any frame can be drawn alone,
    in any order, in any process, and the purity gate (Q1201) holds."""
    if not keys:
        raise TypeError("rng() needs a key, for example rng('hook', 'dust', frame)")
    seed = [len(keys)]
    for k in keys:
        if isinstance(k, str):
            seed.append(zlib.crc32(k.encode()))
        elif isinstance(k, (int, np.integer)):
            if not 0 <= k < 2**32:
                raise ValueError(f"rng key {k}: ints must be 0 to 2**32 - 1")
            seed.append(int(k))
        else:
            raise TypeError(
                f"rng key {k!r}: use a string or an int; for a time pass frame_of(t, FPS), not t"
            )
    return np.random.default_rng(seed)


# ---- layers: every helper below draws on its own transparent layer, then composites it onto the frame ----


def _layer(img):
    """A clear RGBA layer as large as img."""
    return Image.new("RGBA", img.size, (0, 0, 0, 0))


def _rgba(colour):
    """A hex string as an (r, g, b, a) tuple; a tuple is used as given."""
    return hexrgb(colour) if isinstance(colour, str) else colour


def _at(xy):
    """An output-px point in canvas px (SS times larger)."""
    return (xy[0] * SS, xy[1] * SS)


def _opaque(colour, alpha):
    """colour's (r, g, b) with alpha 0..1 as its 0..255 alpha (the colour's own alpha is not used)."""
    return colour[:3] + (int(255 * alpha),)


def canvas(color: str = "#000000"):
    """A new RGBA frame at the drawing size (W x H times SS), filled with color."""
    size = (W * SS, H * SS)
    return Image.new("RGBA", size, hexrgb(color))


def gradient(c1: str, c2: str, vertical: bool = True):
    """A new RGBA frame shaded linearly from c1 to c2: top to bottom, or left to right when vertical is False."""
    top, bottom = (np.array(hexrgb(c)[:3], float) for c in (c1, c2))
    steps = (H if vertical else W) * SS
    shades = top + (bottom - top) * np.linspace(0, 1, steps)[:, None]
    shades = shades.astype(np.uint8)
    if vertical:
        pixels = np.repeat(shades[:, None, :], W * SS, axis=1)
    else:
        pixels = np.repeat(shades[None, :, :], H * SS, axis=0)
    return Image.fromarray(pixels, "RGB").convert("RGBA")


def rrect(img, box: tuple, r: float, fill, alpha: float = 1.0):
    """Composite a rounded box onto img: box = (x0, y0, x1, y1) in output px, corner radius r, fill a hex string or
    an RGBA tuple whose own alpha alpha (0..1) scales. Draws nothing at alpha 0 or under."""
    if alpha <= 0:
        return
    x0, y0, x1, y1 = (v * SS for v in box)
    layer = _layer(img)
    colour = _rgba(fill)
    shade = colour[:3] + (int(colour[3] * alpha),)
    ImageDraw.Draw(layer).rounded_rectangle((x0, y0, x1, y1), r * SS, fill=shade)
    img.alpha_composite(layer)


def shadow(img, box: tuple, r: float, blur=24, dy=12, alpha=0.35):
    """A soft drop shadow under box (output px): the rounded box moved down dy px, black at alpha, blurred by blur
    px. Draw it before the thing it sits under."""
    x0, y0, x1, y1 = (v * SS for v in box)
    drop = dy * SS
    layer = _layer(img)
    black = (0, 0, 0, int(255 * alpha))
    ImageDraw.Draw(layer).rounded_rectangle(
        (x0, y0 + drop, x1, y1 + drop), r * SS, fill=black
    )
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur * SS)))


def _letter_anchor(anchor):
    """Letter-spaced text is set letter by letter from the left: on the baseline when anchor names it, else from the
    top."""
    return "ls" if anchor[1] == "s" else "la"


def _walk(d, s, x, face, gap):
    """(letter, x) for each letter of s set from x, each next one placed its own advance plus gap further on: the
    one walk text() draws and text_box() measures."""
    for letter in s:
        yield letter, x
        x += d.textlength(letter, font=face) + gap


def text(
    img,
    s,
    xy,
    size,
    fill="#FFFFFF",
    anchor="la",
    alpha=1.0,
    bold=True,
    scale=1.0,
    tracking=0,
):
    """Draw the string s on img at xy (output px). anchor is a PIL text anchor ("la" top left, "mm" the centre, "ls"
    left on the baseline ...); scale > 1 enlarges the type about that anchor; tracking puts that many extra px
    between letters, which are then set one at a time from the left. Nothing is drawn at alpha 0 or under."""
    if alpha <= 0:
        return
    face = font(size * scale * SS, bold)
    layer = _layer(img)
    ink = _opaque(_rgba(fill), alpha)
    d = ImageDraw.Draw(layer)
    if tracking:
        y, how = xy[1] * SS, _letter_anchor(anchor)
        for letter, x in _walk(d, s, xy[0] * SS, face, tracking * SS):
            d.text((x, y), letter, font=face, fill=ink, anchor=how)
    else:
        d.text(_at(xy), s, font=face, fill=ink, anchor=anchor)
    img.alpha_composite(layer)


def text_w(s: str, size: float, bold: bool = True) -> float:
    """Advance width of s at size, in output px: what wrap() and fit_size() compare against a width."""
    face = font(size * SS, bold)
    return face.getlength(s) / SS


def text_box(s, xy, size, anchor="la", bold=True, tracking=0):
    """(l, t, r, b) in output px of text drawn with text(): the box to report in scenes.text_items(t). Pass the same
    tracking text() got: letter-spaced text is drawn one letter at a time, so its box is the union of the letters."""
    f = font(size * SS, bold)
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    if not tracking:
        l, t, r, b = d.textbbox(_at(xy), s, font=f, anchor=anchor)
        return (l / SS, t / SS, r / SS, b / SS)
    y, how = xy[1] * SS, _letter_anchor(anchor)
    boxes = [
        d.textbbox((x, y), letter, font=f, anchor=how)
        for letter, x in _walk(d, s, xy[0] * SS, f, tracking * SS)
    ]
    if not boxes:  # "" draws nothing (a typewriter reveal at its first frame): an empty box, as the untracked path
        return (xy[0], xy[1], xy[0], xy[1])
    l, t = min(b[0] for b in boxes), min(b[1] for b in boxes)
    r, b = max(b[2] for b in boxes), max(b[3] for b in boxes)
    return (l / SS, t / SS, r / SS, b / SS)


def fit_size(s, size, maxw, bold=True, floor=36):
    """Largest size up to `size` at which s fits in maxw px; never below `floor` (cut copy instead of shrinking)."""
    while size > floor and text_w(s, size, bold) > maxw:
        size -= 2
    return size


def text_outline(
    img,
    s,
    xy,
    size,
    fill="#FFFFFF",
    outline="#000000",
    width=4,
    anchor="la",
    alpha=1.0,
    bold=True,
):
    """Text with a solid outline (PIL stroke): for game, anime and caption styles over busy pictures."""
    if alpha <= 0:
        return
    layer = _layer(img)
    body, edge = _rgba(fill), _rgba(outline)
    ImageDraw.Draw(layer).text(
        _at(xy),
        s,
        font=font(size * SS, bold),
        anchor=anchor,
        fill=_opaque(body, alpha),
        stroke_width=int(width * SS),
        stroke_fill=_opaque(edge, alpha),
    )
    img.alpha_composite(layer)


def text_halo(
    img,
    s,
    xy,
    size,
    fill="#FFFFFF",
    halo="#000000",
    radius=10,
    strength=0.6,
    anchor="la",
    alpha=1.0,
    bold=True,
):
    """Text over a soft dark halo (blurred thick stroke) so it reads over imagery without a hard box."""
    if alpha <= 0:
        return
    layer = _layer(img)
    glow = _rgba(halo)
    # the halo's alpha: 255 * strength first, then alpha, as one rounding at the end
    glow = glow[:3] + (int(255 * strength * alpha),)
    ImageDraw.Draw(layer).text(
        _at(xy),
        s,
        font=font(size * SS, bold),
        anchor=anchor,
        fill=glow,
        stroke_width=int(radius * SS),
        stroke_fill=glow,
    )
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius * SS * 0.8)))
    text(img, s, xy, size, fill, anchor, alpha, bold)


def wrap(s: str, size: float, maxw: float, bold: bool = True) -> list:
    """s as lines no wider than maxw px at size, filled word by word. A word wider than maxw by itself still gets a
    line of its own: nothing is cut."""
    lines, current = [], ""
    for word in s.split():
        longer = f"{current} {word}".strip()
        if text_w(longer, size, bold) <= maxw or not current:
            current = longer
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def finish(img):
    """The frame draw(t) returns: the canvas brought down to W x H (Lanczos) when it was drawn SS times larger,
    as RGB."""
    out = img.resize((W, H), Image.Resampling.LANCZOS) if SS > 1 else img
    return out.convert("RGB")


@lru_cache(maxsize=64)
def _spans(key):
    """(name, first frame, end frame, a, b) per scene from a hashable (fps, ((name, a, b), ...)) key."""
    fps, items = key
    return tuple((n, frame_of(a, fps), frame_of(b, fps), a, b) for n, a, b in items)


def _frames(schedule):
    return _spans((FPS, tuple((n, v[0], v[1]) for n, v in schedule.items())))


def scene_at(t: float, schedule: dict):
    """Return (name, local_t, k) for the scene active at time t; k = 0..1 through the scene. Decided on integer
    frames (nearest frame, contract.frame_of), so float error cannot start a scene one frame late. Where two spans
    overlap (a transition window) the first entry, the outgoing scene, wins. Past the end: the last scene at k = 1."""
    f = frame_of(t, FPS)
    for name, fa, fb, a, b in _frames(schedule):
        if fa <= f < fb:
            # the nearest frame can open a scene up to half a frame before a: hold local_t at 0 there
            lt = max(0.0, t - a)
            return name, lt, min(1.0, lt / (b - a))
    name, _, _, a, b = _frames(schedule)[-1]
    return name, b - a, 1.0


def scenes_at(t, schedule):
    """Every scene drawn at t as ([(name, local_t, k), ...], mix). Outside a transition window that is one scene and
    mix 0.0; inside one, the outgoing then the incoming scene, with mix 0 -> 1 through the window (0 on its first
    frame), ready for transitions.py: f(a, b, mix). Decided on integer frames, like scene_at."""
    f = frame_of(t, FPS)
    on = [s for s in _frames(schedule) if s[1] <= f < s[2]]
    if not on:
        name, _, _, a, b = _frames(schedule)[-1]
        return [(name, b - a, 1.0)], 0.0
    shown = []
    for name, _, _, a, b in on:
        lt = max(0.0, t - a)
        shown.append((name, lt, min(1.0, lt / (b - a))))
    if len(on) == 1:
        return shown, 0.0
    w0, w1 = max(s[1] for s in on), min(s[2] for s in on)
    return shown, (f - w0) / (w1 - w0)


def crossfade(a_img: Image.Image, b_img: Image.Image, k: float) -> Image.Image:
    """a_img dissolving into b_img: all a_img at k = 0, all b_img at 1 (k is clamped to 0..1)."""
    share = clamp(k)
    return Image.blend(a_img, b_img, share)


# ---- declared timing (Z19): scenes as durations, transitions between them, scene-local cues ----

Scene = namedtuple("Scene", "name dur cues", defaults=((),))
Scene.__doc__ = """One scene for compile_schedule. dur: seconds (beats when bpm is given), a number or a function
that returns one, for example lambda: max(2.0, narration_s). cues: scene-local [(t, label[, kind])] or {label: t},
t counted from the scene's first drawn frame."""
Transition = namedtuple("Transition", "kind dur split", defaults=(0.5,))
Transition.__doc__ = """A transition window between the two scenes either side of it. kind: a transitions.py name for
your draw code. dur: seconds (beats when bpm is given). split: the share of the window before the cut (0.5 centres it
on the cut, 0 starts it on the cut)."""
Timeline = namedtuple("Timeline", "schedule duration cuts windows cues")


def _exact(v):
    """v as an exact fraction: ints and fractions as they are, other numbers as the nearest fraction with a
    denominator up to 10**6, which recovers both typed decimals (0.1 -> 1/10) and quotients (5 / 30 -> 1/6, where the
    shortest repr 0.16666666666666666 is 4.9999999999999998 frames at 30 fps and loses a frame at a half-frame tie)."""
    if isinstance(v, (int, Fraction)):
        return Fraction(v)
    return Fraction(float(v)).limit_denominator(10**6)


def _local_cues(cues):
    """Scene-local cues as (t, label, kind), from {label: t} or the CUES shapes (tuples or dicts)."""
    if isinstance(cues, dict):
        return [(t, label, "both") for label, t in cues.items()]
    out = []
    for c in cues:
        if isinstance(c, dict):
            out.append((c["t"], c.get("label", ""), c.get("kind", "both")))
        else:
            out.append(
                (c[0], c[1] if len(c) > 1 else "", c[2] if len(c) > 2 else "both")
            )
    return out


def compile_schedule(items, mode="straddle", bpm=None, fps=None):
    """Absolute timing from declared scenes: [Scene, Transition, Scene, Scene, ...] -> Timeline, unpacked in
    scenes.py as SCHEDULE, DURATION, CUTS, WINDOWS, CUES. Lengthen one scene and every later scene, window and cue
    moves with it. SCHEDULE {name: (a, b)}: the span each scene is drawn. CUTS: the time of every scene change.
    WINDOWS [(t0, t1, out_name, in_name)]: the transition windows. CUES [(t, label, kind)]: the scene cues, absolute.
    mode "straddle" (default): scenes run cut to cut, so DURATION is their sum and the cuts stay on the grid the
      durations lie on; a window spans its cut (split of it before the cut) and both scenes are drawn in it.
    mode "overlap" (Remotion): the next scene starts dur before this one ends, so DURATION loses every transition
      (60 + 60 - 15 = 105 frames) and the cut sits split of the way into the overlap.
    The arithmetic is exact (fractions of seconds, or of beats when bpm is given) and each instant is rounded once to
    its nearest frame, so nothing drifts off the grid. ValueError for a transition under 2 frames (no frame of it
    would be blended) or over half the shorter of its two scenes, a scene that rounds to no frame, and a cue that
    does not land on a frame of its own scene."""
    if mode not in ("straddle", "overlap"):
        raise ValueError(f'mode {mode!r}: use "straddle" or "overlap"')
    fps = fps or FPS
    unit = "s" if bpm is None else "beats"
    # frames per unit: per second, or per beat when bpm is given
    per = Fraction(fps) if bpm is None else Fraction(60 * fps) / _exact(bpm)
    # trans[i] sits between scenes[i] and scenes[i + 1]; None is a hard cut
    scenes, trans, pending = [], [], None
    for it in items:
        if isinstance(it, Transition):
            if not scenes or pending is not None:
                raise ValueError(f"{it} must sit between two scenes")
            pending = it
            continue
        sc = it if isinstance(it, Scene) else Scene(*it)
        if any(s.name == sc.name for s in scenes):
            raise ValueError(f"scene {sc.name!r} is declared twice")
        if scenes:
            trans.append(pending)
        scenes.append(sc)
        pending = None
    if pending is not None or not scenes:
        raise ValueError("a timeline needs a scene and must not end on a Transition")

    d = []  # exact frames per scene
    for s in scenes:
        v = _exact(s.dur() if callable(s.dur) else s.dur)
        if v <= 0:
            raise ValueError(
                f"scene {s.name!r} lasts {float(v):g} {unit}: it must be over 0"
            )
        d.append(v * per)
    x = [0 if tr is None else _exact(tr.dur) * per for tr in trans]  # window frames
    for i, tr in enumerate(trans):
        if tr is None:
            continue
        if not 0 <= tr.split <= 1:
            raise ValueError(f"{tr}: split must be 0 to 1")
        what = (
            f"{tr.kind!r} transition of {float(tr.dur):g} {unit} ({float(x[i]):.1f} frames) between "
            f"{scenes[i].name!r} ({float(d[i] / fps):.3f} s) and {scenes[i + 1].name!r} "
            f"({float(d[i + 1] / fps):.3f} s)"
        )
        # a window's first frame is all outgoing (mix 0), so under 2 frames nothing is blended
        if x[i] < 2:
            raise ValueError(
                f"{what} is under 2 frames at {fps} fps, so no frame of it is blended: make it at least "
                f"{2 / fps:.3f} s, or use a hard cut"
            )
        j = min((i, i + 1), key=lambda k: d[k])  # the shorter neighbour
        if 2 * x[i] > d[j]:
            raise ValueError(
                f"{what} is over half the shorter scene, {scenes[j].name!r} "
                f"({float(d[j] / fps / 2):.3f} s): shorten it or lengthen {scenes[j].name!r}"
            )
    split = [0 if tr is None else _exact(tr.split) for tr in trans]

    n = len(scenes)
    if mode == "straddle":
        # cut i (into scene i + 1) lies at the sum of the scenes before it; its window spans it
        cut = [sum(d[: i + 1]) for i in range(n - 1)]
        w0 = [c - p * xi for c, p, xi in zip(cut, split, x)]
        w1 = [c + (1 - p) * xi for c, p, xi in zip(cut, split, x)]
        end = sum(d)
    else:
        # scene i + 1 starts x[i] before scene i ends; the cut sits split of the way in
        w0 = []
        for i in range(n - 1):
            w0.append((w0[-1] if w0 else 0) + d[i] - x[i])
        w1 = [a + xi for a, xi in zip(w0, x)]
        cut = [a + p * xi for a, p, xi in zip(w0, split, x)]
        end = (w0[-1] if w0 else 0) + d[-1]
    # exact: scene i is drawn from the start of the window into it to the end of the one out of it
    start, stop = [Fraction(0), *w0], [*w1, end]

    def fr(v):  # the one rounding: nearest frame, halves up, as contract.frame_of
        return math.floor(v + Fraction(1, 2))

    for i, s in enumerate(scenes):
        # under about half a frame: no frame would show the scene, yet it would still make a cut
        if fr(stop[i]) <= fr(start[i]):
            raise ValueError(
                f"scene {s.name!r} lasts {float(d[i] / per):g} {unit} ({float(d[i]):.2f} frames) and rounds to no "
                f"frame at {fps} fps: lengthen it to at least one frame or drop it"
            )
    schedule = {
        s.name: (fr(start[i]) / fps, fr(stop[i]) / fps) for i, s in enumerate(scenes)
    }
    windows = [
        (fr(w0[i]) / fps, fr(w1[i]) / fps, scenes[i].name, scenes[i + 1].name)
        for i in range(n - 1)
        if trans[i] is not None
    ]
    cues = []
    for i, s in enumerate(scenes):
        for t, label, kind in _local_cues(s.cues):
            f = fr(start[i] + _exact(t) * per)
            # on a frame the scene itself draws: at its end the cue would be the next scene's first frame, or for
            # the last scene frame DURATION, which is never drawn
            if not fr(start[i]) <= f < fr(stop[i]):
                last = (fr(stop[i]) - 1 - fr(start[i])) / per
                raise ValueError(
                    f"cue {label!r} at {float(t):g} {unit} does not land on a frame of scene {s.name!r} "
                    f"(0 to {float(last):g} {unit}); a cue at the scene's end belongs to the next scene at 0"
                )
            cues.append((f / fps, label, kind))
    return Timeline(
        schedule, fr(end) / fps, [fr(c) / fps for c in cut], windows, sorted(cues)
    )
