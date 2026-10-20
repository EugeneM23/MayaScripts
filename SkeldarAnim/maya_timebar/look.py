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
    """The timeline's frame <-> x over [left, right] showing frames [v0, v1].

    With `cells` (the timeline, 2026-10-17, as Maya's own slider) a frame is a
    cell [f, f + 1): the track runs to v1 + 1, so the last frame's cell is
    whole, and the frame under an x is the cell it falls in."""

    def __init__(self, v0, v1, left, right, cells=False):
        self.v0, self.v1 = float(v0), float(v1)
        self.cells = bool(cells)
        if self.v1 < self.v0 or (self.v1 == self.v0 and not self.cells):
            self.v1 = self.v0 + (0.0 if self.cells else 1.0)
        self.left, self.right = float(left), float(max(right, left + 1))

    @property
    def span(self):
        """Frames the track's width holds."""
        return (self.v1 - self.v0) + (1.0 if self.cells else 0.0)

    @property
    def scale(self):
        """px a frame."""
        return (self.right - self.left) / self.span

    def cell(self, frame):
        """(x0, x1) of the cell frame `frame` falls in."""
        f = math.floor(frame + 1e-9)
        return self.x(f), self.x(f + 1)

    def end(self, frame):
        """The x where whole frame `frame` ends: its cell's right edge, or the
        frame itself without cells."""
        return self.x(frame + 1) if self.cells else self.x(frame)

    def x(self, frame):
        return self.left + (frame - self.v0) * self.scale

    def frame(self, x):
        return self.v0 + (x - self.left) / self.scale

    def whole(self, x, lo=None, hi=None):
        """The whole frame under `x` (the cell it falls in, with cells), kept in
        [lo, hi] when given."""
        f = int(math.floor(self.frame(x) + (1e-9 if self.cells else 0.5)))
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
    if x > track.right - grip * 0.5 and x >= track.end(p1) + HANDLE_REACH * ui:
        return "a1"
    if band:
        reach = HANDLE_REACH * ui
        d0, d1 = abs(x - track.x(p0)), abs(x - track.end(p1))
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


#  a second right press within this many ms (or Qt's double-click interval, if shorter)
#  highlights every key; the key menu waits for it (2026-10-19)
RIGHT_DOUBLE_MS = 300


def all_keys(keys, breakdowns=()):
    """The highlight over every key the strip shows: (the first key's cell, the last
    key's cell) - a key between frames counts in the cell it stands in. None with no
    keys (2026-10-19: «виділення всіх ключів по подвійному кліку правої кнопки»)."""
    times = list(keys) + list(breakdowns)
    if not times:
        return None
    return (int(math.floor(min(times) + 1e-6)), int(math.floor(max(times) + 1e-6)))


def right_double(first, now_ms, window_ms):
    """True when a right press at `now_ms` is the second of a double: `first` is the
    earlier press's ms (None for none) and it was at most `window_ms` ago."""
    return first is not None and 0 <= now_ms - first <= window_ms


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


SPAN_GAP = 3.0          # logical px between a highlight's frame label and its edge


def span_labels(x0, x1, wa, wb, width, gap=SPAN_GAP, single=False):
    """Where a highlight's two frame labels stand (2026-10-20, «номер кадра в начале и в
    конце рамки выделения»): the left x of the start label and of the end label (None
    for a one-frame highlight, which shows one label centred on it). Inside the block,
    at its edges, when both fit there; else outside it, each beyond its own edge. Kept
    on the track [0, width] and never over each other."""
    if single:
        a = (x0 + x1) / 2.0 - wa / 2.0
        return max(0.0, min(a, width - wa)), None
    if x1 - x0 >= wa + wb + 3 * gap:
        a, b = x0 + gap, x1 - gap - wb
    else:
        a, b = x0 - gap - wa, x1 + gap
    a = max(0.0, min(a, width - wa))
    b = max(0.0, min(b, width - wb))
    if b < a + wa + gap:                    # pushed together at an end of the track
        if a + wa + gap + wb <= width:
            b = a + wa + gap
        else:
            b = width - wb
            a = max(0.0, b - gap - wa)
    return a, b


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
    x0, x1 = track.x(a), track.end(b)
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


def inside(t, selection):
    """Key time `t` in the highlight's cells, [first, last + 1)."""
    a, b = selection
    return a - 1e-6 <= t < b + 1 - 1e-6


def on_frame(t):
    """A key on a whole frame (a solid mark) rather than between frames (dashed)."""
    return abs(t - round(t)) < 1e-4


def mapped(t, selection, target):
    """Key time `t` after the highlight `selection` becomes `target`: the keys in
    its cells move with it, a key between frames keeping its place in its cell;
    scaled, they follow linearly and land on whole frames; the others stay."""
    a, b = selection
    na, nb = target
    if not inside(t, selection):
        return t
    if b <= a or (nb - na) == (b - a):
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
    cell = math.floor(now + 1e-9)
    for k in keys:
        if cell - 1e-6 <= k < cell + 1 - 1e-6:          # in the cell the playhead fills
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


DEFAULT_MODE = "edge"   # the bottom edge by default (2026-10-16)
DEFAULT_VERSION = 1     # raised when an update should switch the mode once more


def mode_from(mode, old=None):
    """The mode from its optionVar; an older build's on/off one (1 docked, 0
    Maya's) when there is none; the bottom edge by default."""
    if mode in MODES:
        return mode
    if old is not None:
        return "docked" if old else "maya"
    return DEFAULT_MODE


def upgraded(mode, seen):
    """The mode after an update (2026-10-16, «по умолчанию выдвижной снизу таймлайн был
    активен при установке нашего обновления»): once per DEFAULT_VERSION the bar goes
    to the bottom edge - unless the animator chose Maya's own slider."""
    if seen >= DEFAULT_VERSION or mode == "maya":
        return mode
    return DEFAULT_MODE


def bottom_band(window, height):
    """(x, y, w, h): the band along the bottom of Maya's window `window` (x, y,
    w, h) the bar slides out into."""
    x, y, w, h = window
    height = min(int(height), int(h))
    return int(x), int(y + h - height), int(w), height


def free_span(window, height, pane=None, obstacles=()):
    """(x0, x1): the stretch of the bottom band the bar may take (2026-10-17, «таймслайдер
    будет тоже учитывать наши интерфейсы и не перекрывать их»): Maya's viewport area
    `pane` across (docked editors left out), less every one of our panels in
    `obstacles` (x, y, w, h) that reaches into the band - one standing in the right
    half cuts the band's end, in the left half its start. Maya's whole width when
    nothing is left."""
    x, y, w, h = (int(v) for v in window)
    top, bottom = y + h - int(height), y + h
    x0, x1 = x, x + w
    if pane:
        x0, x1 = max(x0, int(pane[0])), min(x1, int(pane[0]) + int(pane[2]))
    for ox, oy, ow, oh in obstacles:
        if oy >= bottom or oy + oh <= top or ow <= 0:
            continue
        if ox + ow / 2.0 >= (x0 + x1) / 2.0:
            x1 = min(x1, int(ox))
        else:
            x0 = max(x0, int(ox + ow))
    if x1 - x0 < 1:
        return x, x + w
    return x0, x1


def band_in(window, height, span):
    """The bottom band (bottom_band) cut to `span` (x0, x1)."""
    x, y, w, h = bottom_band(window, height)
    return int(span[0]), y, int(span[1] - span[0]), h


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
HIDE_MS = 1200          # the bar waits this long after the cursor left before it hides
                        # (2026-10-17: 1.2 s, the animator; the hub panel keeps edgerules.HIDE_MS)
ZONE_POLL_MS = 50


def zone_dwell(dwelt, inside, dt_ms):
    """The time the cursor has rested in the band so far: it grows while it stays,
    and any moment outside starts it again."""
    return dwelt + dt_ms if inside else 0.0


# -- the burst from the cursor (2026-10-16, mockup A, «скорость на 50 % медленнее») ---------

BURST_SLOW = 1.2        # every timing of the mockup: 1.5x, then 20 % faster (2026-10-16)
HOVER_MS = 110          # the radial menu's lift (moved here from bar.py 2026-10-19; maya_hubwindow shares it)
FLASH_MS = 120          # a press
RIM = "#fff1e2"         # the light's hot core
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


# -- the reveal's glow (2026-10-17, «при открывании таймслайдера добавим вспышку глоу»: of five
#    flashes played side by side the animator took B, the racing edges) -------------------------

REVEAL_MS = 780         # the whole flash: the edges race out, the top edge stays lit a moment
EDGE_GLOW = 24          # logical px each side: the light an unrolling edge carries
EDGE_CORE = 3           # logical px each side: its hot core
TOP_GLOW = 16           # logical px: how far down the lit top edge glows


def reveal_glow(age, cx, width):
    """The racing edges `age` ms into a reveal from `cx` across `width`: (x0, x1, edges,
    edge, top) - the unrolling span (`unroll`), the edge xs still inside the window, the
    light they carry (1 on the cursor, fading as they slow) and the lit top edge's
    (1 -> 0 over REVEAL_MS)."""
    u = age / float(UNROLL_MS)
    x0, x1 = unroll(u, cx, width, True)
    edges = [x for x in (x0, x1) if 0.5 < x < width - 0.5]
    edge = (1.0 - ease_out_quint(u)) ** 0.55 if edges else 0.0
    top = max(0.0, 1.0 - age / float(REVEAL_MS)) ** 1.6
    return x0, x1, edges, edge, top


# -- the scrub meter (2026-10-16, «проверим быстродействие») --------------------------------

def meter_report(stamps, ours=(), mayas=(), seconds=10.0):
    """What a measured scrub came to: `stamps` the clock (ms) of every frame change
    Maya made, `ours` / `mayas` the Time Bar's own ms and Maya's `currentTime` ms per
    step it drove (empty when Maya's own slider was used). Returns (dict, text)."""
    def median(values):
        values = sorted(values)
        return values[len(values) // 2] if values else 0.0

    def p95(values):
        values = sorted(values)
        return values[min(len(values) - 1, int(len(values) * 0.95))] if values else 0.0

    stamps = sorted(stamps)
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    #  the scrubbing itself: gaps over half a second are pauses, not frames
    moving = [g for g in gaps if g <= 500.0]
    rate = (1000.0 / median(moving)) if moving and median(moving) > 0 else 0.0
    out = {"changes": len(stamps), "rate": rate, "gap_median": median(moving), "gap_p95": p95(moving),
           "gap_max": max(moving) if moving else 0.0, "ours": median(ours), "ours_p95": p95(ours),
           "maya": median(mayas), "seconds": seconds}
    if len(stamps) < 2:
        text = "Scrub meter: no scrubbing in %g s - start it, then drag the playhead" % seconds
        return out, text
    text = ("Scrub meter: %d frame changes, %.0f a second while dragging (a step every %.1f ms, "
            "p95 %.1f, longest %.0f)" % (out["changes"], rate, out["gap_median"], out["gap_p95"],
                                         out["gap_max"]))
    if ours:
        text += " | the Time Bar's own work %.2f ms a step (p95 %.2f), Maya's frame change %.1f ms" % (
            out["ours"], out["ours_p95"], out["maya"])
    else:
        text += " | Maya's own slider drove it"
    return out, text


# -- the key effects (2026-10-17, the animator after the whole mockup: «откатив все
#    эффекты ... оставим вспышку глоу (без частиц) когда ставим ключик и эффект
#    удаления ключа ... одни частицы») -----------------------------------------

EFFECT_MS = {"set": 520, "delete": 700, "trail": 380, "play": 420, "reveal": REVEAL_MS}
TRAIL_ALPHA = 0.28      # a cell the playhead left, at first
SMALL_CHANGE = 6        # more keys changed at once than this is a reload, not an edit


KEY_GAP = 0.18          # a key's cell: this share of the cell left free between neighbours
KEY_GAP_MAX = 3.0       # ... at most this many logical px
KEY_INSET = 2.0         # logical px off the key span's top and bottom
KEY_WIDTH = 0.8         # a key's width, this share of what its cell leaves it
                        # (2026-10-17, the animator: «ключи ... на 20% уже»)


def key_cell(x0, cell, top, bottom, ui=1.0):
    """(left, top, width, height) of a key on a whole frame, drawn in its frame's
    cell (2026-10-17, the animator's mockup: «ключ закрашивает кадр»): a gap between
    neighbouring keys, KEY_WIDTH of what is left, centred in the cell, an inset top
    and bottom; a cell too thin for a gap gives up its gap, and a key is never
    thinner than 1.5 px."""
    gap = max(1.0, min(KEY_GAP_MAX * ui, KEY_GAP * cell))
    if cell - gap < 2.0:
        gap = 0.0
    width = max(1.5, (cell - gap) * KEY_WIDTH)
    inset = KEY_INSET * ui
    return x0 + (cell - width) / 2.0, top + inset, width, max(1.0, bottom - top - 2 * inset)


def key_centre(track, t):
    """The x a key at time `t` is seen at: its cell's middle on a whole frame, the
    time itself between frames (a dashed line)."""
    if on_frame(t) and getattr(track, "cells", False):
        return track.x(t) + track.scale / 2.0
    return track.x(t)


def progress(age_ms, kind):
    """0..1 through effect `kind`, None once it is over (or before it starts)."""
    ms = EFFECT_MS[kind]
    if age_ms < 0 or age_ms >= ms:
        return None
    return age_ms / float(ms)


def key_changes(old, new, edited=False):
    """What an edit did to the key times: (added, removed, snapped) - snapped
    pairs (from, to) where a key between frames went onto a whole frame next to
    it. Nothing when the change is a reload (more than SMALL_CHANGE keys) - except
    a pure deletion Maya reported as a key edit (`edited`), however many keys: the
    animator deleted a whole highlight of them (2026-10-17)."""
    if old is None:
        return [], [], []
    before, after = set(old), set(new)
    added, removed = sorted(after - before), sorted(before - after)
    if edited and removed and not added:
        return [], removed, []
    if len(added) + len(removed) > SMALL_CHANGE:
        return [], [], []
    snapped = []
    for k in list(removed):
        if abs(k - round(k)) < 1e-4:
            continue
        to = next((f for f in (float(math.floor(k)), float(math.ceil(k))) if f in added), None)
        if to is not None:
            snapped.append((k, to))
            removed.remove(k)
            added.remove(to)
    return added, removed, snapped


DELETE_STEP_MS = 80     # keys deleted together: one after another, this far apart ...
DELETE_START_MS = 500   # ... but the last one starts within this, however many (2026-10-17: 1 s, then 0.5)
SHARDS = (3, 3)         # a deleted key breaks into three cubes (2026-10-18: «из 3 кубиков (всегда
                        # кубики разлетаются)»; 3..5 uneven pieces before)
# ... and how they fly: «Shorter», variant B of six played side by side (2026-10-17; D «Snap and
# drop» first) - two thirds of the first flight's kick, its fall; logical px / s, spin deg / s
SHARD_SPEED = 170.0
SHARD_FALL = 900.0
SHARD_SPIN = 420.0


def delete_plan(n):
    """How `n` deleted keys play, left to right: (delays ms per key in time order,
    each key's life ms). Every key breaks exactly as a single key does - the whole
    EFFECT_MS, the same flight - and only the starts are staggered: DELETE_STEP_MS
    apart, squeezed so the last starts by DELETE_START_MS (2026-10-17: «полет самих
    частиц не должен ускоряться ... запустить эффект не позднее чем за 1 секунду», then
    «максимальное время уменьшим до 0.5»)."""
    full = EFFECT_MS["delete"]
    if n <= 0:
        return [], full
    if n == 1:
        return [0.0], full
    spread = min(DELETE_STEP_MS * (n - 1), DELETE_START_MS)
    return [spread * i / float(n - 1) for i in range(n)], full


#  The keys a drag on the timeline still answers (2026-10-18, the animator: «зажимаю
#  кнопку мышки и вожу таймслайдер ... нажимаю S то ключи проставлялись»): while a
#  button is held the key does not reach Maya's hotkeys, so the strip runs Maya's own
#  runtime command for it - the one Maya's default set binds there.
DRAG_KEYS = {
    ("s", False): "SetKey",
    ("w", True): "SetKeyTranslate",
    ("e", True): "SetKeyRotate",
    ("r", True): "SetKeyScale",
}


def drag_key(letter, shift=False, ctrl=False, alt=False):
    """Maya's runtime command for a key pressed during a timeline drag, else None."""
    if ctrl or alt or not letter:
        return None
    return DRAG_KEYS.get((letter.lower(), bool(shift)))


def held(stamped):
    """What a key drag carries once S has put copies down (`stamp_keys`' record):
    (the dragged keys' times, the copies' times), each a frozenset over every
    curve; None before any S."""
    if not stamped:
        return None
    moved, copies = set(), set()
    for rec in stamped.values():
        moved.update(round(t, 4) for t, _data in rec.get("keys", ()))
        copies.update(round(t, 4) for t in rec.get("stamped", ()))
    return frozenset(moved), frozenset(copies)


def shown_at(frame, selection, target, carried=None):
    """Where a key is drawn while a block is dragged: a dragged key at its place on
    `target`, any other key where it stands - a copy S put down stays where it
    went down, it is not part of the drag («поставленные ключи добавляются в мое
    выделение», 2026-10-18). A dragged key with a copy on its own time is drawn
    at both."""
    if carried is None:
        return [mapped(frame, selection, target)]
    moved, copies = carried
    t = round(frame, 4)
    out = []
    if t in moved:
        out.append(mapped(frame, selection, target))
    if t in copies or t not in moved:
        out.append(frame)
    return out


def key_action(name, drag, highlight, preview=None):
    """What a Set Key key does on the strip (2026-10-18):
    ('stamp', selection, target) - highlighted keys are being dragged (moved, or
        scaled by an edge) and S is pressed: a copy of exactly those keys goes down
        where they are being dragged to, nothing in the gaps between them («когда
        мы переносим массив ключей и нажимаем s то мы должны проставлять все ключи
        которые у нас выделены, ключи в пробелах массива проставлять не нужно»);
    ('run',) - a playhead drag: Maya's own command, at the current frame;
    ('range', a, b) - no drag, a highlight of two frames or more: a key on every frame
        of it («во всех кадрах проставились ключи (такая себе версия бейка)»);
    None - Maya's hotkey as usual. `drag` is the timeline's drag tuple or None,
    `preview` the dragged keys' highlight now."""
    if not name:
        return None
    if drag:
        if drag[0] in ("hmove", "h0", "h1") and len(drag) > 3:
            if name != "SetKey":
                return None
            return ("stamp", tuple(drag[3]), tuple(preview or drag[3]))
        if drag[0] == "hl":                  # drawing a highlight: no key
            return None
        return ("run",)
    if highlight and highlight[1] > highlight[0]:
        return ("range", int(highlight[0]), int(highlight[1]))
    return None


def set_key_command(command):
    """A MEL command Maya reported: (frame or None, breakdown) when it is a
    `setKeyframe` - the S key, the Channel Box's Key Selected - else None. A key set
    over a key that stood changes no key time, so this is how it still flashes
    (2026-10-17: «эффект постановки ключа должен срабатывать даже если ключ уже
    стоял»). No `-t`/`-time`: the current frame."""
    if not command.startswith("setKeyframe"):
        return None
    words = command.replace('"', " ").replace(";", " ").split()
    if not words or words[0] != "setKeyframe":
        return None
    frame, breakdown = None, False
    for i, word in enumerate(words[:-1]):
        if word in ("-t", "-time") and frame is None:
            try:
                frame = float(words[i + 1].split(":")[0])
            except ValueError:
                pass
        elif word in ("-bd", "-breakdown"):
            breakdown = words[i + 1] in ("1", "true", "on")
    return frame, breakdown


SHARD_BUDGET = 900      # pieces a wave may throw; past it neighbouring keys break as one block


def shard_groups(n, budget=SHARD_BUDGET):
    """[(start, end)] runs of the `n` deleted keys (in time order) that break as one:
    each key alone while 3 pieces each fit the budget, else runs of neighbours - a
    wave of 1000 keys, each a pixel or two wide, throws ~900 pieces, not 3000."""
    if n <= 0:
        return []
    size = max(1, -(-n * SHARDS[0] // budget))
    return [(i, min(n, i + size)) for i in range(0, n, size)]


def _rand(state):
    state = (state * 1103515245 + 12345) & 0x7FFFFFFF
    return state, (state % 10000) / 10000.0


def shard_cuts(height):
    """Where a key of `height` breaks: [(top, bottom)] of its three cubes stacked
    down it, each a third of its height."""
    side = height / float(SHARDS[0])
    return [(i * side, (i + 1) * side) for i in range(SHARDS[0])]


def shards(seed, rect, age_ms, ms, speed, gravity, spin=SHARD_SPIN):
    """A deleted key broken into three cubes at `age_ms` - [(cx, cy, w, h, angle,
    alpha)], logical px, y down, angle in degrees. A cube's side is a third of the
    key's height, whatever its width (a hairline key throws cubes too); the three
    start stacked down the key's middle, are kicked up and away from it, spin and
    fall; they fade over the last half. Seeded, so a paint at any time reads the same
    flight. `rect` = (left, top, width, height)."""
    if age_ms < 0 or age_ms >= ms:
        return []
    left, top, w, h = rect
    t = age_ms / 1000.0
    u = age_ms / float(ms)
    alpha = 1.0 if u < 0.5 else 1.0 - (u - 0.5) / 0.5
    cuts = shard_cuts(h)
    s = (int(seed) * 40503 + 7) & 0x7FFFFFFF
    s, r0 = _rand(s)
    first = -1.0 if r0 < 0.5 else 1.0
    mid = top + h / 2.0
    out = []
    for i, (a, b) in enumerate(cuts):
        s, r2 = _rand(s)
        s, r3 = _rand(s)
        cy0 = top + (a + b) / 2.0
        side = first if i % 2 == 0 else -first                  # the pieces part left and right
        lift = (mid - cy0) / max(h, 1e-6)                       # the top pieces fly higher
        vx = side * speed * (0.35 + 0.65 * r2)
        vy = -speed * (0.55 + 0.6 * r3 + 0.8 * lift)
        cx = left + w / 2.0 + vx * t
        cy = cy0 + vy * t + 0.5 * gravity * t * t
        angle = side * spin * (0.4 + 0.6 * r3) * t
        out.append((cx, cy, b - a, b - a, angle, alpha))
    return out


def sparks(seed, count, age_ms, ms, speed, gravity, spread=360.0):
    """Sparks thrown from a point: [(dx, dy, life)] at `age_ms` (dy down, logical
    px), `life` 1 at the throw and 0 at the end. Seeded, so a paint at any time
    reads the same flight: no state is stepped."""
    if age_ms < 0 or age_ms >= ms:
        return []
    out, t = [], age_ms / 1000.0
    s = (int(seed) * 2654435761) & 0xFFFFFFFF
    for _i in range(count):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        a = (s % 10000) / 10000.0
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        b = (s % 10000) / 10000.0
        angle = math.radians(-90.0 + (a - 0.5) * spread)
        v = speed * (0.45 + 0.55 * b)
        dx = math.cos(angle) * v * t
        dy = math.sin(angle) * v * t + 0.5 * gravity * t * t
        out.append((dx, dy, 1.0 - age_ms / float(ms)))
    return out


# Steel keys (2026-10-20, «заменить оранжевые ключи на серебряные ... эффект остывания стали»):
# ⋮ -> Time bar ▸ Steel keys draws the keys in steel, and a key just set glows hot and
# cools into steel, as forged steel does: white heat, yellow, orange, cherry red, a dark
# temper, then the cold metal.
STEEL_VAR = "skeldarTimeBarSteelKeys"
STEEL = "#b8c0ca"
COOL_MS = 1800          # a key set is steel again after this
COOL_STEPS = 48         # the cooling in this many colours (the key glow caches one picture each)
HEAT = ((0.00, "#fff6e4"),      # white heat
        (0.08, "#ffd47a"),      # yellow
        (0.22, "#ff9a3c"),      # orange
        (0.45, "#d8432a"),      # cherry red
        (0.70, "#7a4a44"),      # the dark temper
        (1.00, STEEL))


def _rgb(hex_):
    hex_ = hex_.lstrip("#")
    return tuple(int(hex_[i:i + 2], 16) for i in (0, 2, 4))


def cooling(age_ms, steel=STEEL, cool_ms=COOL_MS):
    """(colour hex, heat 0..1) of a key `age_ms` after it was set hot: the colour along
    HEAT (its last stop `steel`), the heat its glow - 1 at once, gone by 70 % of the way."""
    u = max(0.0, min(1.0, age_ms / float(cool_ms)))
    u = round(u * COOL_STEPS) / float(COOL_STEPS)      # a few dozen colours: each glow is cached
    stops = HEAT[:-1] + ((1.0, steel),)
    for (u0, a), (u1, b) in zip(stops, stops[1:]):
        if u <= u1:
            s = (u - u0) / (u1 - u0) if u1 > u0 else 1.0
            s = s * s * (3.0 - 2.0 * s)
            ca, cb = _rgb(a), _rgb(b)
            hex_ = "#%02x%02x%02x" % tuple(int(round(x + (y - x) * s)) for x, y in zip(ca, cb))
            break
    else:
        hex_ = steel
    heat = max(0.0, 1.0 - u / 0.7) ** 1.5
    return hex_, heat
