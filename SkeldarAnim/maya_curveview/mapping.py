"""The Curve Overlay's arithmetic. Pure: stdlib only, no Maya, no Qt.

Everything fiddly about drawing a graph editor over a viewport lives here,
because everything fiddly is where the bugs are: the pixel a key is drawn
at, the pixel a click has to forgive, which keys a marquee caught, and the
direction a tangent handle leans. All of it is a function of numbers, so all
of it is testable in a bare interpreter -- the same reason `bodymap` and
`pickerstate` are pure in the picker.

Two coordinate systems meet in this module and they disagree about Y.

    curve space   time along X, value along Y, Y increasing upward
    pixel space   Qt: X from the left edge, Y from the TOP, increasing down

and a third arrives at the door: `cmds.draggerContext(space="screen")`
reports Y from the BOTTOM of the viewport (measured 2026-09-05, by drawing
both readings and watching which one followed the cursor). `flip_y` is the
one place that crossing happens.
"""

import math
from collections import namedtuple

# The curve-space window the overlay is showing: time t0..t1, value v0..v1.
Frame = namedtuple("Frame", "t0 t1 v0 v1")

# The overlay's own size in pixels.
Rect = namedtuple("Rect", "width height")

AXIS_COLOURS = {
    "x": (236, 92, 92),
    "y": (122, 214, 108),
    "z": (94, 158, 255),
    "other": (214, 208, 192),
}

# Only these families carry an axis letter. A colour taken from the last
# letter of any name at all would lie about the curve: `visibility` would
# read as a Y channel, and a rig's own `myCustomZ` as a Z one.
_AXIS_FAMILIES = frozenset((
    "translate", "rotate", "scale", "shear", "jointOrient", "rotateAxis",
    "rotatePivot", "scalePivot", "rotatePivotTranslate",
    "scalePivotTranslate", "preferredAngle",
))

# `draggerContext -q -modifier` answers a string (measured: 'none').  The
# mapping is Maya's own viewport behaviour, not an invention: plain replaces,
# shift toggles, ctrl removes, ctrl+shift adds.
_ADJUSTMENTS = {
    "none": "replace",
    "": "replace",
    "shift": "toggle",
    "ctrl": "remove",
    "control": "remove",
    "ctrlshift": "add",
    "shiftctrl": "add",
    "controlshift": "add",
}


# ------------------------------------------------------------------ framing

def value_span(series):
    """(lowest, highest) value across every curve, or None if there is none.

    `series` is an iterable of iterables of (time, value) pairs -- the shape
    `curves.visible_curves()` hands over, so the caller never flattens.
    """
    lo = hi = None
    for points in series:
        for _time, value in points:
            value = float(value)
            if lo is None or value < lo:
                lo = value
            if hi is None or value > hi:
                hi = value
    if lo is None:
        return None
    return (lo, hi)


def autoframe(time_range, span, margin=0.08, floor=1.0):
    """The window to draw: X is the playback range, Y fits `span`.

    There is no pan and no zoom in this tool -- that is what leaves every
    camera gesture to the camera -- so this function is the whole of
    navigation and it has to survive the degenerate cases: a still channel
    (`span` collapsed to a point), no curves at all (`span` None), and a
    playback range of one frame.
    """
    t0, t1 = float(time_range[0]), float(time_range[1])
    if t1 <= t0:
        t1 = t0 + 1.0
    if span is None:
        lo, hi = -1.0, 1.0
    else:
        lo, hi = float(span[0]), float(span[1])
    reach = (hi - lo) * float(margin)
    if hi - lo < 1e-9:
        reach = abs(float(floor)) or 1.0
    return Frame(t0, t1, lo - reach, hi + reach)


def normalise(time_range, series, margin=0.08):
    """One Y window per curve, so every curve fills the same pixel band.

    The alternative to the shared axis. With several channels at once the
    magnitudes are not comparable -- a translate around a hundred and a
    rotate at thirty degrees on one axis give one real curve and one flat
    line -- and this is the answer when shape matters more than value.
    """
    return [autoframe(time_range, value_span([points]), margin=margin)
            for points in series]


def grid_step(span, target=12):
    """A readable frame step for the vertical grid over `span` frames.

    Rounded up to a friendly number so the labels read 10, 20, 30 rather
    than 8, 16, 24 -- and never below 1, because a grid line at a fraction
    of a frame means nothing to an animator.
    """
    span = abs(float(span))
    if span <= 0:
        return 1.0
    raw = span / max(int(target), 1)
    if raw <= 1.0:
        return 1.0
    power = 10.0 ** math.floor(math.log10(raw))
    for multiple in (1.0, 2.0, 2.5, 5.0, 10.0):
        step = multiple * power
        if step >= raw:
            return step
    return 10.0 * power


def sample_count(rect, step=3, minimum=2):
    """How many samples a curve needs to look smooth in `rect`.

    One sample every `step` pixels: finer is invisible and every sample is a
    call into Maya.
    """
    width = max(int(rect.width), 0)
    return max(int(minimum), width // max(int(step), 1))


# ------------------------------------------------------- the two coordinates

def to_pixels(frame, rect, t, v):
    """Curve space to Qt pixels."""
    if rect.width <= 0 or rect.height <= 0:
        return (0.0, 0.0)
    time_span = frame.t1 - frame.t0
    value_span_ = frame.v1 - frame.v0
    x = 0.0 if time_span == 0 else \
        (float(t) - frame.t0) / time_span * rect.width
    if value_span_ == 0:
        y = 0.0
    else:
        y = rect.height - (float(v) - frame.v0) / value_span_ * rect.height
    return (float(x), float(y))


def to_curve(frame, rect, x, y):
    """Qt pixels back to curve space."""
    if rect.width <= 0 or rect.height <= 0:
        return (frame.t0, frame.v0)
    t = frame.t0 + float(x) / rect.width * (frame.t1 - frame.t0)
    v = frame.v0 + (rect.height - float(y)) / rect.height \
        * (frame.v1 - frame.v0)
    return (t, v)


def flip_y(rect, y):
    """Between Maya's bottom-up screen Y and Qt's top-down Y.

    Its own inverse, which is why one function serves both directions.
    """
    return float(rect.height) - float(y)


def snap(t):
    """To the nearest whole frame, a half going away from zero.

    Python's `round` goes to even, which would send 2.5 to 2 and 3.5 to 4 --
    an animator dragging a key past the halfway mark expects the next frame
    both times.
    """
    value = float(t)
    if value >= 0:
        return float(math.floor(value + 0.5))
    return float(math.ceil(value - 0.5))


# ------------------------------------------------------------------- picking

def pick_key(frame, rect, keys, x, y, radius=8.0):
    """Index of the key nearest (x, y) within `radius` pixels, or None.

    Distance in PIXELS, not in curve units: the forgiveness an animator
    feels is a distance on the screen, and in curve units it would change
    with the value range of whatever else happens to be drawn.
    """
    best = None
    best_distance = float(radius) ** 2
    for index, (t, v) in enumerate(keys):
        kx, ky = to_pixels(frame, rect, t, v)
        distance = (kx - float(x)) ** 2 + (ky - float(y)) ** 2
        if distance <= best_distance:
            best, best_distance = index, distance
    return best


def keys_in_box(frame, rect, keys, x0, y0, x1, y1):
    """Indices of the keys inside the rectangle, corners in any order."""
    left, right = sorted((float(x0), float(x1)))
    top, bottom = sorted((float(y0), float(y1)))
    found = []
    for index, (t, v) in enumerate(keys):
        kx, ky = to_pixels(frame, rect, t, v)
        if left <= kx <= right and top <= ky <= bottom:
            found.append(index)
    return found


def is_marquee(x0, y0, x1, y1, slop=3.0):
    """True when the gesture travelled far enough to mean a rectangle.

    A click is a drag of nearly zero length, and the animator's hand always
    moves a pixel or two.
    """
    return abs(float(x1) - float(x0)) > slop \
        or abs(float(y1) - float(y0)) > slop


# ------------------------------------------------------------------ tangents

def _axis_scale(frame, rect):
    """Pixels per frame and pixels per unit of value."""
    time_span = frame.t1 - frame.t0
    value_span_ = frame.v1 - frame.v0
    sx = rect.width / time_span if time_span else 0.0
    sy = rect.height / value_span_ if value_span_ else 0.0
    return (sx, sy)


def tangent_points(frame, rect, key, angle_in, angle_out, length=48.0):
    """The two handle ends in pixels, for a key at `key` = (time, value).

    Maya reports a tangent as an ANGLE in curve space (value per frame), so
    the handle has to be converted through the current frame's scale or it
    will not lie along the curve as drawn -- and then normalised back to a
    constant pixel length, because a handle is a thing the animator grabs
    and its grab size must not depend on the value range on screen.
    """
    kx, ky = to_pixels(frame, rect, key[0], key[1])
    sx, sy = _axis_scale(frame, rect)

    def reach(angle, sign):
        slope = math.tan(math.radians(float(angle)))
        dx = sign * sx
        dy = -sign * slope * sy          # Qt Y grows downward
        span = math.hypot(dx, dy)
        if span < 1e-12:
            return (kx + sign * float(length), ky)
        scale = float(length) / span
        return (kx + dx * scale, ky + dy * scale)

    return (reach(angle_in, -1.0), reach(angle_out, 1.0))


def tangent_angle(frame, rect, key, x, y, side):
    """The Maya-space angle a handle dragged to (x, y) means. Degrees.

    The exact inverse of `tangent_points`, which a test pins: draw a handle
    at 30 degrees and read it back at 30.
    """
    kx, ky = to_pixels(frame, rect, key[0], key[1])
    sx, sy = _axis_scale(frame, rect)
    if sx <= 0 or sy <= 0:
        return 0.0
    dx = (float(x) - kx) / sx
    dy = -(float(y) - ky) / sy
    if side == "in":
        dx, dy = -dx, -dy
    if abs(dx) < 1e-9:
        return 89.9 if dy >= 0 else -89.9
    return math.degrees(math.atan2(dy, dx)) if dx > 0 else \
        math.degrees(math.atan(dy / dx))


def pick_tangent(frame, rect, keys, angles, selected, x, y, radius=8.0):
    """(index, "in"|"out") of the handle under the point, or None.

    Only the handles of SELECTED keys exist to be grabbed, because only
    those are drawn -- and a handle sits on top of its own key, so callers
    ask this before `pick_key`.
    """
    best = None
    best_distance = float(radius) ** 2
    for index in sorted(selected):
        if index >= len(keys):
            continue
        pair = angles.get(index)
        if pair is None:
            continue
        into, out = tangent_points(frame, rect, keys[index], pair[0], pair[1])
        for side, point in (("in", into), ("out", out)):
            distance = (point[0] - float(x)) ** 2 \
                + (point[1] - float(y)) ** 2
            if distance <= best_distance:
                best, best_distance = (index, side), distance
    return best


# -------------------------------------------------------------------- policy

def adjustment(modifier):
    """`draggerContext`'s modifier string to a selection behaviour token.

    A token rather than an `MGlobal` constant, so this module stays pure;
    `tool.py` owns the one table that turns it into the API value.
    """
    if not modifier:
        return "replace"
    key = str(modifier).strip().lower().replace("_", "").replace("+", "")
    return _ADJUSTMENTS.get(key, "replace")


def axis_colour(attribute):
    """The line colour for a channel: X red, Y green, Z blue, else neutral.

    Takes a plug (`ctrl.translateX`) or a bare attribute.
    """
    name = str(attribute).rpartition(".")[2]
    letter = name[-1:].lower()
    if letter in ("x", "y", "z") and name[:-1] in _AXIS_FAMILIES:
        return AXIS_COLOURS[letter]
    return AXIS_COLOURS["other"]


def should_evaluate(now, last, interval=0.05):
    """Whether the throttle lets a scene evaluation through.

    Measured basis: one drag delivers ~860 events (about one per pixel of
    travel) and the animator's scene runs 10.4 fps, so following the dragged
    key on every event would be seconds of stall. The first event always
    passes -- the animator must see something move at once.
    """
    return last is None or (float(now) - float(last)) >= float(interval)
