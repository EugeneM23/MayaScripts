"""maya_hubburst - a popup bursting out of a point, and folding back into one.

2026-10-17 (spec: docs/superpowers/specs/2026-10-17-popup-burst-design.md). The animator:
«Давай сделаем так что бы наши поапы появлялись с приятной анимацией» - of five mockups
(https://claude.ai/artifact/AQZc8xz9Bys9kXzXiFgZ2z) they chose D, «из точки»: the card's shape
unrolls from the point the popup was called from (the cursor, or the hub card's button) and its rows
pop in nearest first; it closes folding its rows farthest first, then the shape closes onto the point
the close came from. The radial menu's and the Time Bar's language.

Pure, stdlib only: rectangles are (x, y, w, h) in the card's own physical px, a shape is
(x0, y0, x1, y1), times are ms; `scale` is the hub's (maya_hubstyle.px), so distances and the start
box count in logical px. maya_hubpop draws it.
"""

import collections
import math

#  opening
SHAPE_MS = 300            # the shape unrolls (ease-out quint)
FACE_IN_MS = 60           # the card's face comes up under it
START_HALF = (14, 10)     # logical px: the shape at the start, about the origin
START_RADIUS = 10
CARD_RADIUS = 8           # the popup's own outline (maya_hubpop._paint_outline)
ORIGIN_PAD = 12           # a point outside the card is pulled this far inside it
DELAY0 = 40               # the first row starts this long after the press
DELAY_PER = 22            # ms more for every STEP logical px from the origin
STEP = 60
PART_MS = 240             # a row grows over this
PART_FADE_MS = 140        # ... and fades in over this
PART_FROM = 0.82
BACK = 1.6                # the radial menu's back ease

#  closing
FOLD_PER = 22
FOLD_MS = 130
FOLD_TO = 0.86
CLOSE_SHAPE_MS = 200
CLOSE_LEAD = 60           # the shape starts closing this long before the last row is gone
CLOSE_HALF = (12, 9)
FACE_OUT_AT = 120         # after the shape starts closing
FACE_OUT_MS = 80

#  the rows
ROW_MAX = 64              # logical px: a taller widget is split into its children
MAX_PARTS = 48
MAX_DEPTH = 8
MAX_MS = 1200             # the driver's length; the plan's total ends it sooner

Plan = collections.namedtuple(
    "Plan", "opening size origin parts pivots delays start end m0 total scale")
State = collections.namedtuple("State", "shape radius face parts")


# ------------------------------------------------------------------ easing

def _clamp(t):
    return min(1.0, max(0.0, float(t)))


def ease(t):
    return 1.0 - (1.0 - _clamp(t)) ** 3


def quint(t):
    return 1.0 - (1.0 - _clamp(t)) ** 5


def in_cubic(t):
    return _clamp(t) ** 3


def back(t, k=BACK):
    t = _clamp(t)
    c3 = k + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + k * (t - 1.0) ** 2


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
    step = STEP * scale
    delays = [DELAY0 + DELAY_PER * (_dist(o, _centre(p)) / step) for p in parts]
    total = max([SHAPE_MS] + [d + PART_MS for d in delays])
    return Plan(True, size, o, list(parts), [pivot(p, o) for p in parts], delays,
                _box(o, START_HALF, size, scale), (0.0, 0.0, size[0], size[1]), 0.0,
                float(total), float(scale))


def plan_close(origin, size, parts, scale=1.0):
    """The closing of a card of `size` onto `origin`."""
    size = (float(size[0]), float(size[1]))
    o = clamp_origin(origin, size, ORIGIN_PAD * scale)
    step = STEP * scale
    dists = [_dist(o, _centre(p)) for p in parts]
    far = max(dists) if dists else 0.0
    delays = [FOLD_PER * ((far - d) / step) for d in dists]
    m0 = max([0.0] + [d + FOLD_MS - CLOSE_LEAD for d in delays])
    return Plan(False, size, o, list(parts), [pivot(p, o) for p in parts], delays,
                (0.0, 0.0, size[0], size[1]), _box(o, CLOSE_HALF, size, scale), m0,
                float(m0 + CLOSE_SHAPE_MS), float(scale))


def at(plan, ms):
    """The burst's state `ms` after its start: the shape, its corner radius (physical px), the
    face's opacity, and per row (opacity, scale). At or past the total, exactly the end."""
    s = plan.scale
    if plan.opening:
        if ms >= plan.total:
            return State(plan.end, CARD_RADIUS * s, 1.0, [(1.0, 1.0)] * len(plan.parts))
        f = quint(ms / float(SHAPE_MS))
        parts = []
        for d in plan.delays:
            op = ease((ms - d) / float(PART_FADE_MS))
            sc = lerp(PART_FROM, 1.0, back((ms - d) / float(PART_MS)))
            parts.append((op, sc))
        return State(_shape_between(plan.start, plan.end, f),
                     lerp(START_RADIUS, CARD_RADIUS, f) * s, ease(ms / float(FACE_IN_MS)), parts)
    if ms >= plan.total:
        return State(plan.end, START_RADIUS * s, 0.0, [(0.0, FOLD_TO)] * len(plan.parts))
    parts = []
    for d in plan.delays:
        u = (ms - d) / float(FOLD_MS)
        parts.append((1.0 - ease(u), 1.0 - (1.0 - FOLD_TO) * in_cubic(u)))
    k = in_cubic((ms - plan.m0) / float(CLOSE_SHAPE_MS))
    face = 1.0 - ease((ms - plan.m0 - FACE_OUT_AT) / float(FACE_OUT_MS))
    return State(_shape_between(plan.start, plan.end, k), lerp(CARD_RADIUS, START_RADIUS, k) * s,
                 face, parts)


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


def rows(root, kids, rect_of, row_max, clip=None, max_depth=MAX_DEPTH):
    """The rows of `root`: a node no taller than `row_max` (or with no children, or at
    `max_depth`) is one row; a taller one is split into its children. Every row is cut to
    `clip`, and one outside it goes. `kids(node)` and `rect_of(node)` read the tree."""
    out = []

    def walk(node, depth):
        rect = _cut(rect_of(node), clip)
        if rect is None:
            return
        children = list(kids(node)) if rect[3] > row_max and depth < max_depth else []
        if not children:
            out.append(rect)
            return
        before = len(out)
        for child in children:
            walk(child, depth + 1)
        if len(out) == before:
            out.append(rect)

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
