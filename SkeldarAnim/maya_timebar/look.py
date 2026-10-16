"""The Time Bar's arithmetic (2026-10-16): frame <-> x, the ticks, what a press hits,
the highlight, the keys either side. Stdlib only - a test pins it.

Every length here is in the strip's own pixels (the caller multiplies its logical
sizes by the display scale). Spec: docs/superpowers/specs/2026-10-16-time-bar-design.md
"""

import math

#  frames between labels, the first that leaves at least LABEL_GAP px between two labels
LABEL_STEPS = (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000)
LABEL_GAP = 46          # logical px
TICK_GAP = 5            # the least logical px between two ticks
HANDLE_REACH = 6        # logical px either side of a handle that grabs it
GRIP = 10               # logical px of the track's ends that hold the animation range's grips

#  the fps chip: Maya's time unit names, in order
FPS = (("24", "film"), ("25", "pal"), ("30", "ntsc"), ("48", "show"),
       ("50", "palf"), ("60", "ntscf"))
UNIT_FPS = {"game": 15, "film": 24, "pal": 25, "ntsc": 30, "show": 48, "palf": 50,
            "ntscf": 60, "millisec": 1000, "sec": 1, "min": 1.0 / 60, "hour": 1.0 / 3600}


def fps_label(unit):
    """'30 fps' for 'ntsc', '23.976 fps' for '23.976fps', the unit itself otherwise."""
    if unit in UNIT_FPS and UNIT_FPS[unit] >= 1:
        value = UNIT_FPS[unit]
    elif unit.endswith("fps"):
        value = unit[:-3]
    else:
        return unit
    text = ("%g" % float(value)) if not isinstance(value, str) else value
    return text + " fps"


class Track(object):
    """The timeline's frame <-> x over [left, right] showing frames [v0, v1]."""

    def __init__(self, v0, v1, left, right):
        self.v0, self.v1 = float(v0), float(v1)
        if self.v1 <= self.v0:
            self.v1 = self.v0 + 1.0
        self.left, self.right = float(left), float(max(right, left + 1))

    @property
    def scale(self):
        """px a frame."""
        return (self.right - self.left) / (self.v1 - self.v0)

    def x(self, frame):
        return self.left + (frame - self.v0) * self.scale

    def frame(self, x):
        return self.v0 + (x - self.left) / self.scale

    def whole(self, x, lo=None, hi=None):
        """The whole frame under `x`, kept in [lo, hi] when given."""
        f = int(math.floor(self.frame(x) + 0.5))
        if lo is not None:
            f = max(int(math.ceil(lo)), f)
        if hi is not None:
            f = min(int(math.floor(hi)), f)
        return f


def step_for(scale, gap, steps=LABEL_STEPS):
    """The first step of `steps` whose frames stand `gap` px apart at `scale` px a frame."""
    for step in steps:
        if step * scale >= gap:
            return step
    return steps[-1]


def ticks(track, ui=1.0):
    """[(frame, kind)] for the ruler: kind 'label' (a number under it), 'mid' (half way
    between labels when there is room) or 'tick'. Frames are whole."""
    label = step_for(track.scale, LABEL_GAP * ui)
    small = step_for(track.scale, TICK_GAP * ui, [s for s in LABEL_STEPS if label % s == 0])
    half = label // 2 if label % 2 == 0 and (label // 2) % small == 0 else 0
    out = []
    first = int(math.ceil(track.v0 / small)) * small
    f = first
    while f <= track.v1 + 1e-9:
        if f % label == 0:
            out.append((f, "label"))
        elif half and f % half == 0:
            out.append((f, "mid"))
        else:
            out.append((f, "tick"))
        f += small
    return out


def hit(track, x, now, p0, p1, ui=1.0, band=True):
    """What a press at `x` takes: 'a0' / 'a1' (the animation range's grips at the
    track's ends), 'p0' / 'p1' (the playback band's edges) or 'now' (a scrub)."""
    grip = GRIP * ui
    if x < track.left + grip * 0.5 and x <= track.x(p0) - HANDLE_REACH * ui:
        return "a0"
    if x > track.right - grip * 0.5 and x >= track.x(p1) + HANDLE_REACH * ui:
        return "a1"
    if band:
        reach = HANDLE_REACH * ui
        d0, d1 = abs(x - track.x(p0)), abs(x - track.x(p1))
        if min(d0, d1) <= reach:
            return "p0" if d0 <= d1 else "p1"
    return "now"


def dragged(which, frame, a0, a1, p0, p1):
    """(a0, a1, p0, p1) after the grip or handle `which` is dragged to `frame`:
    the playback range keeps a frame at least and stays inside the animation range,
    which grows to hold it."""
    frame = int(round(frame))
    if which == "p0":
        p0 = min(frame, p1 - 1)
        a0 = min(a0, p0)
    elif which == "p1":
        p1 = max(frame, p0 + 1)
        a1 = max(a1, p1)
    elif which == "a0":
        a0 = min(frame, p0)
    elif which == "a1":
        a1 = max(frame, p1)
    return a0, a1, p0, p1


def highlight(start, end):
    """[first, last] of a shift-drag from frame `start` to frame `end`, either way."""
    a, b = int(round(start)), int(round(end))
    return (a, b) if a <= b else (b, a)


def range_array(selection):
    """(first, last) -> [first, last + 1), as `timeControl -q -rangeArray` answers a
    highlight; None for nothing or one frame (the tools' rule: more than one frame)."""
    if not selection:
        return None
    first, last = selection
    if last <= first:
        return None
    return (float(first), float(last + 1))


def neighbour_key(keys, now, forward):
    """The key after (or before) frame `now`, or None."""
    eps = 1e-6
    if forward:
        later = [k for k in keys if k > now + eps]
        return min(later) if later else None
    earlier = [k for k in keys if k < now - eps]
    return max(earlier) if earlier else None


def frame_text(frame):
    """A frame as the field shows it: whole frames plainly, a sub-frame to 2 places."""
    if abs(frame - round(frame)) < 1e-6:
        return "%d" % int(round(frame))
    return ("%.2f" % frame).rstrip("0").rstrip(".")


# -- the full bar (2026-10-16, the second mockup) -------------------------------------

SPEEDS = (("Real-time", 1.0), ("Every frame", 0.0), ("Half", 0.5), ("Twice", 2.0))
LOOPS = ("continuous", "once", "oscillate")
TANGENTS = (("Auto", "auto"), ("Spline", "spline"), ("Clamped", "clamped"), ("Linear", "linear"),
            ("Flat", "flat"), ("Stepped", "step"), ("Plateau", "plateau"))
MIN_VIEW = 8.0              # the fewest frames a zoom shows


def zoomed(v0, v1, at, factor, lo=None, hi=None):
    """The view [v0, v1] zoomed by `factor` (>1 out, <1 in) about frame `at`;
    never fewer than MIN_VIEW frames, never past [lo - 20, hi + 20] when given."""
    n0 = at - (at - v0) * factor
    n1 = at + (v1 - at) * factor
    if n1 - n0 < MIN_VIEW:
        return v0, v1
    if lo is not None:
        n0 = max(n0, lo - 20.0)
    if hi is not None:
        n1 = min(n1, hi + 20.0)
    return n0, n1


def highlight_hit(track, x, selection, ui=1.0):
    """'h0' / 'h1' (the highlight's edges), 'hmove' (inside it) or None. A
    one-frame highlight has no edges: anywhere on it moves."""
    if not selection:
        return None
    a, b = selection
    x0, x1 = track.x(a), track.x(b)
    reach = HANDLE_REACH * ui
    if b > a:
        if abs(x - x0) <= reach:
            return "h0"
        if abs(x - x1) <= reach:
            return "h1"
    if x0 - (0 if b > a else reach) < x < x1 + (0 if b > a else reach):
        return "hmove"
    return None


def key_drag(kind, selection, start, frame):
    """The highlight after dragging its body ('hmove') or an edge ('h0' / 'h1')
    from frame `start` to frame `frame`: a move keeps its length, an edge scales
    toward the other edge, which stays."""
    a, b = selection
    d = int(round(frame)) - int(round(start))
    if kind == "hmove" or b <= a:
        return a + d, b + d
    if kind == "h0":
        return min(a + d, b - 1), b
    return a, max(b + d, a + 1)


def mapped(t, selection, target):
    """Key time `t` after the highlight `selection` becomes `target`: the keys
    inside follow linearly, rounded to whole frames; the others stay."""
    a, b = selection
    na, nb = target
    if not (a - 1e-6 <= t <= b + 1e-6):
        return t
    if b <= a:
        return t + (na - a)
    return int(round(na + (t - a) * float(nb - na) / (b - a)))


def passed(keys, before, now, near=6.0):
    """The keys the playhead reached going from `before` to `now`: every key it
    swept over when the step is short (playback, a scrub), only the one it lands
    on after a jump (the loop going back to the start)."""
    if before is None or abs(now - before) < 1e-9:
        return []
    lo, hi = min(before, now), max(before, now)
    hit = []
    for k in keys:
        if abs(k - now) < 0.5:
            hit.append(k)
        elif hi - lo <= near and lo - 1e-6 < k <= hi + 1e-6 and abs(k - before) > 1e-6:
            hit.append(k)
    return hit


def flash(age_ms, decay_ms):
    """A reached key's light: 1 at once, eased back to 0 over `decay_ms`."""
    if age_ms < 0 or age_ms >= decay_ms:
        return 0.0
    u = 1.0 - age_ms / float(decay_ms)
    return u * u


def approach(value, goal, dt_ms, ms):
    """`value` eased toward `goal` over about `ms` (exponential, never past it)."""
    if ms <= 0:
        return goal
    k = 1.0 - math.exp(-3.0 * dt_ms / ms)
    out = value + (goal - value) * k
    return goal if abs(out - goal) < 0.005 else out


def back_out(u):
    """The radial menu's ease-out-back: overshoots a little, lands on 1."""
    u = max(0.0, min(1.0, u))
    c = 1.70158
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


def opening(age_ms, index, open_ms=200.0, step_ms=18.0):
    """(scale, opacity) of control `index` `age_ms` after the bar opened."""
    u = (age_ms - index * step_ms) / open_ms
    if u <= 0:
        return 0.3, 0.0
    if u >= 1:
        return 1.0, 1.0
    return 0.3 + 0.7 * back_out(u), min(1.0, u * 1.6)


def envelope(samples, rate, fps, offset, start, end, per_frame=4):
    """[(frame, amplitude 0..1)] of a mono sound (`samples` -1..1 at `rate` Hz,
    starting at frame `offset`) over frames [start, end], `per_frame` bins a frame."""
    out = []
    if not samples or rate <= 0 or fps <= 0:
        return out
    n = len(samples)
    step = 1.0 / per_frame
    f = float(start)
    peak = max(abs(s) for s in samples) or 1.0
    while f <= end + 1e-9:
        i0 = int((f - offset) / fps * rate)
        i1 = int((f + step - offset) / fps * rate)
        if i1 > 0 and i0 < n:
            chunk = samples[max(0, i0):min(n, max(i1, i0 + 1))]
            amp = max(abs(s) for s in chunk) / peak if chunk else 0.0
            out.append((f, amp))
        f += step
    return out


# -- the bottom edge (2026-10-16: «всплывающим когда наводим в область нижней части экрана») --

MODES = ("maya", "docked", "edge")
MODE_LABELS = (("Maya's", "maya"), ("Docked", "docked"), ("Bottom edge", "edge"))
SLIDE_MS = 180          # out
SLIDE_BACK_MS = 140     # back


def mode_from(mode, old=None):
    """The mode from its optionVar; an older build's on/off one (1 docked, 0
    Maya's) when there is none; docked by default."""
    if mode in MODES:
        return mode
    if old is not None:
        return "docked" if old else "maya"
    return "docked"


def bottom_band(window, height):
    """(x, y, w, h): the band along the bottom of Maya's window `window` (x, y,
    w, h) the bar slides out into."""
    x, y, w, h = window
    height = min(int(height), int(h))
    return int(x), int(y + h - height), int(w), height


def sensor_band(window, px=2):
    """The thin strip along the bottom of Maya's window that brings the bar out."""
    x, y, w, h = window
    return int(x), int(y + h - px), int(w), int(px)


def slide(t_ms, height, showing, ms):
    """How far the bar stands below its place (px) `t_ms` into a slide of `ms`:
    out eases from `height` to 0, back from 0 to `height`."""
    u = 1.0 if ms <= 0 else max(0.0, min(1.0, t_ms / float(ms)))
    e = 1 - (1 - u) ** 3 if showing else u ** 3
    return int(round(height * (1 - e))) if showing else int(round(height * e))


ZONE_DWELL_MS = 150     # the cursor resting in the band this long brings the bar out
ZONE_POLL_MS = 50


def zone_dwell(dwelt, inside, dt_ms):
    """The time the cursor has rested in the band so far: it grows while it stays,
    and any moment outside starts it again."""
    return dwelt + dt_ms if inside else 0.0


# -- the burst from the cursor (2026-10-16, mockup A, «скорость на 50 % медленнее») ---------

BURST_SLOW = 1.5        # every timing of the mockup, half as fast again
UNROLL_MS = 240 * BURST_SLOW        # the panel unrolls from the cursor
POP_OPEN_MS = 200 * BURST_SLOW      # a control pops in
FOLD_MS = 140 * BURST_SLOW          # a control folds away
CLOSE_MS = 180 * BURST_SLOW         # the panel closes onto the cursor
CLOSE_AFTER_MS = 60 * BURST_SLOW    # after the last control folded
START_SCALE = 0.3


def ease_out_quint(u):
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 5


def ease_in_quint(u):
    u = max(0.0, min(1.0, u))
    return u ** 5


def back_in(u):
    """The radial menu's leave: draws back a little, then goes."""
    u = max(0.0, min(1.0, u))
    c = 1.70158
    return (c + 1) * u ** 3 - c * u ** 2


def burst_delay(dx, dy, ui=1.0):
    """When a control pops in: the nearer the cursor the sooner (the mockup's
    40 ms + 18 ms per 60 px, a vertical step counting 1.5)."""
    d = (abs(dx) + abs(dy) * 1.5) / max(ui, 1e-6)
    return (40.0 + d / 60.0 * 18.0) * BURST_SLOW


def fold_delay(dx, ui=1.0):
    """When a control folds away: the farthest first, toward the cursor."""
    d = abs(dx) / max(ui, 1e-6)
    return max(0.0, 180.0 - d / 60.0 * 12.0) * BURST_SLOW


def popping(age, delay, ms=POP_OPEN_MS):
    """(scale, opacity) of a control `age` ms into the burst, popping in at `delay`."""
    u = (age - delay) / float(ms)
    if u <= 0:
        return START_SCALE, 0.0
    if u >= 1:
        return 1.0, 1.0
    return START_SCALE + (1 - START_SCALE) * back_out(u), min(1.0, u * 1.6)


def folding(age, delay, ms=FOLD_MS):
    """(scale, opacity) of a control `age` ms into the fold, folding at `delay`."""
    u = (age - delay) / float(ms)
    if u <= 0:
        return 1.0, 1.0
    if u >= 1:
        return START_SCALE, 0.0
    e = back_in(u)
    return 1.0 - (1 - START_SCALE) * e, max(0.0, 1.0 - u)


def unroll(u, cx, width, showing):
    """(x0, x1) of the panel `u` (0..1) into its unroll from - or close onto - `cx`."""
    e = ease_out_quint(u) if showing else 1 - ease_in_quint(u)
    cx = max(0.0, min(float(width), cx))
    return cx * (1 - e), cx + (width - cx) * e
