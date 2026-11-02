# scenes.py : the template video, and the shape every video's scenes.py keeps: a palette, the copy, one declared
# TIMELINE, the registry qa.py and proof.py read (text_items, CUES, KEY_TIMES), and draw(t), a pure function of t.
# This one is a title card, one point and an end card; it fits 16:9 and 9:16 alike because every size and place
# comes from W, H and the short side.
from engine import *

# Palette: put the chosen style's colours here, and only here (qa.py lint wants no colour literal in a function).
# Each scene has a flat ground; GLOW and SHADE are the soft shapes that drift behind the copy, MARK the rule under
# the point.
TEAL, CREAM, PLUM = "#1F4E5F", "#F4EAD5", "#3A2E5C"
SNOW, INK, LILAC, MARK = "#FFFFFF", "#1A1A2E", "#D9D2F2", "#F2A541"
GLOW, SHADE = hexrgb(SNOW, 34), hexrgb(INK, 22)
GROUND = {"title": TEAL, "point": CREAM, "end": PLUM}

# The copy: replace every placeholder with the real words.
COPY = {
    "title": "{title}",
    "point": "{the one point}",
    "end": "{end card line}",
    "link": "{handle or link}",
}
# Where each scene's texts sit: (copy key, centre height as a share of H, size as a share of the short side,
# colour, seconds after its scene starts that it begins to come in).
PLACES = {
    "title": [("title", 0.5, 0.11, SNOW, 0.0)],
    "point": [("point", 0.5, 0.09, INK, 0.0)],
    "end": [("end", 0.44, 0.09, SNOW, 0.0), ("link", 0.6, 0.045, LILAC, 0.2)],
}

# Timing is declared once, here: the scenes in order and their lengths in seconds (in beats when compile_schedule
# gets bpm=BPM). Lengthen one and every later scene, cut and cue moves with it. A cue given on a scene counts from
# that scene's first frame, so the two below sit on the cuts: render_audio puts the cut's hit on them and Q902
# checks that sound and picture meet there. Transition("crossfade", 0.4) between two scenes blends them over a
# window (draw and text_items below already handle one); a cut inside a window has no hard picture change, so give
# its cue kind "audio". More cues can be added to CUES as (t, label, kind), kind "both", "audio" or "picture".
BPM = 120  # qa.py holds the cuts to this beat grid
TIMELINE = [
    Scene("title", 2.0),
    Scene("point", 3.0, cues=[(0.0, "point lands", "both")]),
    Scene("end", 3.0, cues=[(0.0, "end card", "both")]),
]
SCHEDULE, DURATION, CUTS, WINDOWS, CUES = compile_schedule(TIMELINE)  # frame-exact
CUE_LAG = 0  # frames the picture may land after its cue by design
# Moments the proof sheet must show besides the cuts and every text at rest: (t, why) or a bare time.
KEY_TIMES = [(SCHEDULE["point"][0] + 0.9, "the rule under the point fully drawn")]

ENTER, EXIT = (
    0.45,
    0.3,
)  # seconds a text takes to come in, and to go out before its scene's last frame
SLIDE = 0.06  # how far a text travels while it comes in or goes out, as a share of the short side


def motion(name, lt, delay):
    """(alpha, dx) of a text in scene name at local time lt that starts to come in delay seconds into the scene.
    It slides in from the right and fades up, then leaves to the left in the scene's last EXIT seconds. The first
    scene is already in place on frame 0 (the thumbnail), and the last one stays to the end (the end card)."""
    a, b = SCHEDULE[name]
    arrive = 1.0 if a == 0 else ease_out_cubic(prog(lt, delay, ENTER))
    depart = 0.0 if b >= DURATION else ease_in_cubic(prog(lt, (b - a) - EXIT, EXIT))
    travel = SLIDE * min(W, H)
    return arrive * (1 - depart), travel * (1 - arrive) - travel * depart


def placed(name, lt):
    """Every text of scene name at local time lt as (key, string, xy, size, colour, alpha): draw paints exactly
    these and text_items reports exactly these, so the registry cannot drift from the picture."""
    out = []
    for key, height, share, colour, delay in PLACES[name]:
        s = COPY[key]
        size = fit_size(s, round(min(W, H) * share), W * 0.8)
        alpha, dx = motion(name, lt, delay)
        out.append((key, s, (W / 2 + dx, H * height), size, colour, alpha))
    return out


def drift(img, name, t):
    """Three soft pills sliding sideways behind the copy at their own speeds, each from a seeded start, so even a
    long hold keeps moving (Q1102) while the end card stays calm enough to read as held (Q503)."""
    short = min(W, H)
    tone = SHADE if name == "point" else GLOW
    starts = rng("drift", name)
    for i in range(3):
        u, v = starts.random(2)
        tall = short * (0.18 + 0.1 * i)
        wide = tall * 2.4
        lane = W + wide
        x = (u * lane + t * short * (0.02 + 0.015 * i)) % lane - wide
        y = v * (H - tall)
        rrect(img, (x, y, x + wide, y + tall), tall / 2, tone)


def underline(img, xy, size, alpha, lt):
    """The accent rule under the point: it grows out from the middle from 0.3 s to 0.9 s into the scene."""
    grow = ease_out_cubic(prog(lt, 0.3, 0.6))
    half = text_w(COPY["point"], size) * 0.3 * grow
    if half < 1:  # under a pixel wide a rounded box still paints a dot
        return
    thick = max(6.0, min(W, H) * 0.008)
    x, y = xy[0], xy[1] + size * 0.8
    rrect(img, (x - half, y, x + half, y + thick), thick / 2, MARK, alpha)


def paint(name, lt, t):
    """Scene name at local time lt (t is the film's time, which the drifting shapes run on)."""
    img = canvas(GROUND[name])
    drift(img, name, t)
    for key, s, xy, size, colour, alpha in placed(name, lt):
        if key == "point":
            underline(img, xy, size, alpha, lt)
        text(img, s, xy, size, colour, "mm", alpha)
    return img


def shares(t):
    """([(name, local_t), ...], [weight, ...]): one scene at weight 1, or inside a transition window the outgoing
    and the incoming scene at 1 - mix and mix."""
    shown, mix = scenes_at(t, SCHEDULE)
    weights = [1.0] if len(shown) == 1 else [1 - mix, mix]
    return [(name, lt) for name, lt, _ in shown], weights


def text_items(t):
    """The registry: every text on screen at t with its box in output px, colour, alpha and size. In a window each
    text's alpha is its own times its scene's weight."""
    items = []
    for (name, lt), weight in zip(*shares(t)):
        for _, s, xy, size, colour, alpha in placed(name, lt):
            if alpha * weight > 0:
                items.append(
                    {
                        "s": s,
                        "box": text_box(s, xy, size, "mm"),
                        "fg": colour,
                        "alpha": alpha * weight,
                        "px": size,
                        "bold": True,
                    }
                )
    return items


def draw(t):
    shown, weights = shares(t)
    pictures = [paint(name, lt, t) for name, lt in shown]
    if len(pictures) == 1:
        return finish(pictures[0])
    # a window: another transitions.py kind needs the same weights here and in text_items, or the registry drifts
    return finish(crossfade(pictures[0], pictures[1], weights[1]))
