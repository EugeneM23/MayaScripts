"""maya_hubburst - a popup bursting out of a point, and folding back into one.

2026-10-17 (spec: docs/superpowers/specs/2026-10-17-popup-burst-design.md). The animator:
«Давай сделаем так что бы наши поапы появлялись с приятной анимацией» - of five mockups
(https://claude.ai/artifact/AQZc8xz9Bys9kXzXiFgZ2z) they chose D, «из точки»: the card's shape
unrolls from the point the popup was called from (the cursor, or the hub card's button) and its rows
pop in nearest first; it closes folding its rows farthest first, then the shape closes onto the point
the close came from. The radial menu's and the Time Bar's language.

2026-10-18 (spec: docs/superpowers/specs/2026-10-18-floating-windows-design.md). The animator:
«сделаем новые анимации в стиле таймслайдера»: the timing is now the Time Bar's (maya_timebar.look:
unroll, pop, fold, close, its delays and eases), and an opening carries the Time Bar's racing-edge
light (`light`): the shape's edges standing inside the card, and the card's top edge once reached.

Pure, stdlib only (maya_timebar's package imports no Maya and no Qt): rectangles are (x, y, w, h)
in the card's own physical px, a shape is (x0, y0, x1, y1), times are ms; `scale` is the hub's
(maya_hubstyle.px), so distances and the start box count in logical px. maya_hubwindow's burst effect draws it.
"""

import collections
import math

from maya_timebar import look as tlook

#  opening - twice the Time Bar's speed too (2026-10-21, the animator: «ускорим скорость
#  проигрывания анимации при открытии окон в два раза»): every opening time and delay over OPEN_SPEED
OPEN_SPEED = 2.0
SHAPE_MS = tlook.UNROLL_MS / OPEN_SPEED   # the shape unrolls (ease_out_quint)
FACE_IN_MS = 60 / OPEN_SPEED                  # the card's face comes up under it
START_HALF = (14, 10)               # logical px: the shape at the start, about the origin
START_RADIUS = 10
CARD_RADIUS = 8                     # the popup's own outline (maya_hubpop._paint_outline)
ORIGIN_PAD = 12                     # a point outside the card is pulled this far inside it
PART_MS = tlook.POP_OPEN_MS / OPEN_SPEED      # a part pops (back_out from START_SCALE)
PART_FROM = tlook.START_SCALE
REVEAL_MS = tlook.REVEAL_MS / OPEN_SPEED      # the light's whole length
EDGE_GLOW, EDGE_CORE, TOP_GLOW = tlook.EDGE_GLOW, tlook.EDGE_CORE, tlook.TOP_GLOW

#  closing - twice the Time Bar's speed (2026-10-19, the animator: «Скорость анимации закрытия
#  окон стоит ускорить в 2 раза»): every closing time, the folds' delays too, over CLOSE_SPEED
CLOSE_SPEED = 2.0
FOLD_MS = tlook.FOLD_MS / CLOSE_SPEED             # a part folds (back_in to START_SCALE)
CLOSE_SHAPE_MS = tlook.CLOSE_MS / CLOSE_SPEED     # the shape closes (ease_in_quint)
CLOSE_AFTER_MS = tlook.CLOSE_AFTER_MS / CLOSE_SPEED   # after the last fold ends
CLOSE_HALF = (12, 9)
FACE_OUT_MS = 80 / CLOSE_SPEED

#  the rows
ROW_MAX = 64              # logical px: a taller widget is split into its children
MAX_PARTS = 48
MAX_DEPTH = 8
MAX_MS = 1200             # the driver's length; the plan's total ends it sooner

#  the spring (2026-10-22, spec 2026-10-22-window-look-b-spring-design.md). The animator,
#  of the mockups https://claude.ai/artifact/Q2HzadyrH8RGqJeiot2c9k: «вид B (Time Bar) и
#  анимацию 4 (spring)». The whole window grows out of the point on a damped spring and fades
#  in; it shrinks a little toward the point and fades out. One picture drawn scaled: no rows,
#  no mask, no light - the burst's per-frame cost was what made it stutter.
MOTION = "spring"         # "spring" or "burst" (the 2026-10-17 motion, kept)
SPRING_FROM = 0.7         # the scale it grows from
SPRING_ZETA = 0.72        # damping: one small overshoot (the scale about 1.2 % over)
SPRING_HZ = 3.0           # the spring's own frequency
SPRING_MS = 420           # settled: the scale within 0.1 % of 1
SPRING_FADE_MS = 120      # the opacity comes up
SHUT_TO = 0.85            # the scale it shrinks to when closing
SHUT_MS = 140             # the close, ease-in cubic

Plan = collections.namedtuple(
    "Plan", "opening size origin parts pivots delays start end m0 total scale kind",
    defaults=("burst",))
State = collections.namedtuple("State", "shape radius face parts")
Light = collections.namedtuple("Light", "edges top")


# ------------------------------------------------------------------ easing

def _clamp(t):
    return min(1.0, max(0.0, float(t)))


def ease(t):
    return 1.0 - (1.0 - _clamp(t)) ** 3


def lerp(a, b, k):
    return a + (b - a) * k


# ------------------------------------------------------------------ geometry

def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def clamp_origin(point, size, pad):
    """`point` pulled inside the card by `pad` (physical px)."""
    w, h = size
    pad = min(pad, w / 2.0, h / 2.0)
    return (min(w - pad, max(pad, point[0])), min(h - pad, max(pad, point[1])))


def _centre(rect):
    return (rect[0] + rect[2] / 2.0, rect[1] + rect[3] / 2.0)


def pivot(rect, origin):
    """The point of `rect` nearest `origin`, relative to its top-left."""
    x = min(rect[2], max(0.0, origin[0] - rect[0]))
    y = min(rect[3], max(0.0, origin[1] - rect[1]))
    return (float(x), float(y))


def _box(origin, half, size, scale):
    """The small shape about `origin`, kept inside the card."""
    w, h = size
    hx, hy = half[0] * scale, half[1] * scale
    return (max(0.0, origin[0] - hx), max(0.0, origin[1] - hy),
            min(float(w), origin[0] + hx), min(float(h), origin[1] + hy))


def _shape_between(a, b, k):
    return tuple(lerp(a[i], b[i], k) for i in range(4))


# ------------------------------------------------------------------ plans

def plan_open(origin, size, parts, scale=1.0):
    """The opening of a card of `size` from `origin`, its rows `parts`."""
    size = (float(size[0]), float(size[1]))
    o = clamp_origin(origin, size, ORIGIN_PAD * scale)
    delays = []
    for p in parts:
        cx, cy = _centre(p)
        delays.append(tlook.burst_delay((cx - o[0]) / scale, (cy - o[1]) / scale) / OPEN_SPEED)
    total = max([SHAPE_MS, REVEAL_MS] + [d + PART_MS for d in delays])
    return Plan(True, size, o, list(parts), [pivot(p, o) for p in parts], delays,
                _box(o, START_HALF, size, scale), (0.0, 0.0, size[0], size[1]), 0.0,
                float(total), float(scale))


def plan_close(origin, size, parts, scale=1.0):
    """The closing of a card of `size` onto `origin`."""
    size = (float(size[0]), float(size[1]))
    o = clamp_origin(origin, size, ORIGIN_PAD * scale)
    delays = []
    for p in parts:
        cx, cy = _centre(p)
        d = abs(cx - o[0]) + 1.5 * abs(cy - o[1])
        delays.append(tlook.fold_delay(d, scale) / CLOSE_SPEED)
    m0 = max([0.0] + [d + FOLD_MS + CLOSE_AFTER_MS for d in delays])
    return Plan(False, size, o, list(parts), [pivot(p, o) for p in parts], delays,
                (0.0, 0.0, size[0], size[1]), _box(o, CLOSE_HALF, size, scale), m0,
                float(m0 + CLOSE_SHAPE_MS), float(scale))


def spring(ms):
    """The damped spring's progress `ms` in: 0 at 0, past 1 once by about 1.5 %, settling on 1
    (a mass let go from 0 toward 1, damping SPRING_ZETA, frequency SPRING_HZ)."""
    t = max(0.0, float(ms)) / 1000.0
    w0 = 2.0 * math.pi * SPRING_HZ
    z = SPRING_ZETA
    wd = w0 * math.sqrt(1.0 - z * z)
    return 1.0 - math.exp(-z * w0 * t) * (math.cos(wd * t) + z * w0 / wd * math.sin(wd * t))


def _scaled(origin, size, k):
    """The window's rect (x0, y0, x1, y1) scaled by `k` about `origin`."""
    w, h = size
    ox, oy = origin
    return (ox - ox * k, oy - oy * k, ox + (w - ox) * k, oy + (h - oy) * k)


def plan_spring(opening, origin, size, scale=1.0):
    """The spring's plan: out of `origin` (`opening`) or into it, for a window of `size`."""
    size = (float(size[0]), float(size[1]))
    o = clamp_origin(origin, size, ORIGIN_PAD * scale)
    whole = (0.0, 0.0, size[0], size[1])
    if opening:
        return Plan(True, size, o, [], [], [], _scaled(o, size, SPRING_FROM), whole, 0.0,
                    float(SPRING_MS), float(scale), "spring")
    return Plan(False, size, o, [], [], [], whole, _scaled(o, size, SHUT_TO), 0.0,
                float(SHUT_MS), float(scale), "spring")


def plan(opening, origin, size, parts, scale=1.0, motion=None):
    """The plan of the motion in use (MOTION, or `motion`): `parts` is called only for the
    burst, which needs the rows - the spring never walks them."""
    if (motion or MOTION) == "spring":
        return plan_spring(opening, origin, size, scale)
    rows_now = parts() if callable(parts) else parts
    return (plan_open if opening else plan_close)(origin, size, rows_now, scale)


def scale_of(plan, state):
    """The scale a spring state stands at, from its shape (1 for the burst)."""
    if plan.kind != "spring":
        return 1.0
    w = plan.size[0]
    return (state.shape[2] - state.shape[0]) / w if w > 0 else 1.0


def _spring_at(plan, ms):
    s = plan.scale
    if plan.opening:
        if ms >= plan.total:
            return State(plan.end, CARD_RADIUS * s, 1.0, [])
        #  held at 1: a window cannot paint past its own edge, and the spring's overshoot
        #  was cut there (the filmstrip, 2026-10-22) - it lands softly instead
        k = min(1.0, lerp(SPRING_FROM, 1.0, spring(ms)))
        return State(_scaled(plan.origin, plan.size, k), CARD_RADIUS * s * k,
                     _clamp(ms / float(SPRING_FADE_MS)), [])
    if ms >= plan.total:
        return State(plan.end, CARD_RADIUS * s * SHUT_TO, 0.0, [])
    u = _clamp(ms / float(SHUT_MS))
    e = u * u * u
    k = lerp(1.0, SHUT_TO, e)
    return State(_scaled(plan.origin, plan.size, k), CARD_RADIUS * s * k, 1.0 - e, [])


def at(plan, ms):
    """The burst's state `ms` after its start: the shape, its corner radius (physical px), the
    face's opacity, and per row (opacity, scale). At or past the total, exactly the end.
    A spring's state has no rows: its shape is the window scaled about the point."""
    if plan.kind == "spring":
        return _spring_at(plan, ms)
    s = plan.scale
    if plan.opening:
        if ms >= plan.total:
            return State(plan.end, CARD_RADIUS * s, 1.0, [(1.0, 1.0)] * len(plan.parts))
        f = tlook.ease_out_quint(ms / float(SHAPE_MS))
        parts = []
        for d in plan.delays:
            u = (ms - d) / float(PART_MS)
            if u <= 0.0:
                parts.append((0.0, PART_FROM))
            elif u >= 1.0:
                parts.append((1.0, 1.0))
            else:
                parts.append((min(1.0, u * 1.6),
                              PART_FROM + (1.0 - PART_FROM) * tlook.back_out(u)))
        return State(_shape_between(plan.start, plan.end, f),
                     lerp(START_RADIUS, CARD_RADIUS, f) * s, ease(ms / float(FACE_IN_MS)), parts)
    if ms >= plan.total:
        return State(plan.end, START_RADIUS * s, 0.0, [(0.0, PART_FROM)] * len(plan.parts))
    parts = []
    for d in plan.delays:
        u = (ms - d) / float(FOLD_MS)
        if u >= 1.0:
            parts.append((0.0, PART_FROM))
        else:
            u = max(0.0, u)
            parts.append((max(0.0, 1.0 - u), 1.0 - (1.0 - PART_FROM) * tlook.back_in(u)))
    k = tlook.ease_in_quint((ms - plan.m0) / float(CLOSE_SHAPE_MS))
    face = 1.0 - ease((ms - plan.m0 - (CLOSE_SHAPE_MS - FACE_OUT_MS)) / float(FACE_OUT_MS))
    return State(_shape_between(plan.start, plan.end, k), lerp(CARD_RADIUS, START_RADIUS, k) * s,
                 face, parts)


def light(plan, ms):
    """The burst's light `ms` in (2026-10-18, the Time Bar's racing edges): the shape's edges
    standing inside the card, each (axis, pos, intensity) - 1 at the start, fading as
    (1 - ease_out_quint)^0.55 - and the card's top edge, once the shape reaches it, fading as
    (1 - ms / REVEAL_MS)^1.6. A close carries none."""
    if not plan.opening or ms >= plan.total or plan.kind == "spring":
        return Light([], 0.0)
    w, h = plan.size
    u = ms / float(SHAPE_MS)
    e = tlook.ease_out_quint(u)
    x0, y0, x1, y1 = _shape_between(plan.start, plan.end, e)
    edges = []
    if u < 1.0:
        k = (1.0 - e) ** 0.55
        for axis, pos, limit in (("x", x0, w), ("x", x1, w), ("y", y0, h), ("y", y1, h)):
            if 0.5 < pos < limit - 0.5 and k > 0.0:
                edges.append((axis, pos, k))
    top = 0.0
    if y0 <= 0.5:
        top = max(0.0, 1.0 - ms / float(REVEAL_MS)) ** 1.6
    return Light(edges, top)


# ------------------------------------------------------------------ rows

def _cut(rect, clip):
    if clip is None:
        return rect
    x0, y0 = max(rect[0], clip[0]), max(rect[1], clip[1])
    x1 = min(rect[0] + rect[2], clip[0] + clip[2])
    y1 = min(rect[1] + rect[3], clip[1] + clip[3])
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1 - x0, y1 - y0)


def sliced(rect, row_max):
    """`rect` cut into equal horizontal bands no taller than `row_max`, together exactly
    `rect` (2026-10-19: a list's viewport has no child widgets, and whole it waited its
    turn as one empty rectangle of the card's face)."""
    x, y, w, h = rect
    if row_max <= 0 or h <= row_max:
        return [rect]
    n = int(math.ceil(h / float(row_max)))
    edges = [y + int(round(h * i / float(n))) for i in range(n + 1)]
    return [(x, a, w, b - a) for a, b in zip(edges, edges[1:]) if b > a]


def rows(root, kids, rect_of, row_max, clip=None, max_depth=MAX_DEPTH):
    """The rows of `root`: a node no taller than `row_max` is one row; a taller one is
    split into its children, and one with no children (or at `max_depth`) into bands
    (`sliced`). Every row is cut to `clip`, and one outside it goes. `kids(node)` and
    `rect_of(node)` read the tree."""
    out = []

    def walk(node, depth):
        rect = _cut(rect_of(node), clip)
        if rect is None:
            return
        children = list(kids(node)) if rect[3] > row_max and depth < max_depth else []
        if not children:
            out.extend(sliced(rect, row_max))
            return
        before = len(out)
        for child in children:
            walk(child, depth + 1)
        if len(out) == before:
            out.extend(sliced(rect, row_max))

    walk(root, 0)
    return out


def bands(rects, cap):
    """At most `cap` rows: consecutive rows merged into bands (their bounding boxes)."""
    rects = list(rects)
    if len(rects) <= cap or cap <= 0:
        return rects
    size = int(math.ceil(len(rects) / float(cap)))
    out = []
    for i in range(0, len(rects), size):
        chunk = rects[i:i + size]
        x0 = min(r[0] for r in chunk)
        y0 = min(r[1] for r in chunk)
        x1 = max(r[0] + r[2] for r in chunk)
        y1 = max(r[1] + r[3] for r in chunk)
        out.append((x0, y0, x1 - x0, y1 - y0))
    return out


def blend(a, b, k):
    """Colour `a` toward `b` ("#rrggbb") by `k`, as (r, g, b) ints."""
    k = _clamp(k)
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return tuple(int(round(lerp(x, y, k))) for x, y in zip(ca, cb))
