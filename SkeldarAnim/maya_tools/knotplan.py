"""The Tools card's knots: the pure half (2026-10-12).

The animator: «то что находится во вкладке knots ... что во вкладке double knots ... заведем
раздел тул и реализуем такие же инструменты». OverRig's Knot, Knot Offset, Knot Orient and Double
knot (local, world) are rebuilt in `knots`; this module holds what needs no Maya: the kinds, the
span a knot covers and its attach keys, which channels a knot takes, what a knot remembers, the
bake order of a knot on a knot, which waiting pivot a Finish means, sizes, rotate orders and the
card's lines.

Stdlib only (a subprocess test pins it).
Spec: docs/superpowers/specs/2026-10-12-tools-knots-design.md
"""

import collections
import math

# ------------------------------------------------------------------ markers

KIND_MARKER = "skeldarKnot"                     # the knot's top node: its kind
SOURCE_MARKER = "skeldarKnotSource"             # ... the object's UUID
SPAN_MARKER = "skeldarKnotSpan"                 # ... "start end ranged" (a waiting pivot too)
KEYED_MARKER = "skeldarKnotKeyed"               # ... "tz=3.0 rx=0.0": channels we keyed
OF_MARKER = "skeldarKnotOf"                     # the object's constraint: the knot's UUID
PENDING_MARKER = "skeldarKnotPending"           # a waiting pivot: its object's UUID
PENDING_SPACE_MARKER = "skeldarKnotPendingSpace"  # the space it rides in: the same
ORDER_MARKER = "skeldarKnotOrder"               # a waiting pivot: the rotate order choice
INNER_MARKER = "skeldarKnotInner"               # a double knot's inner node: its top's UUID
GROUP_MARKER = "skeldarKnotGroup"               # the group knots live in
ATTACH = "attach"                               # 0..1 on the top node: the object's own <-> the knot

GROUP_IN_CHARACTER = "Knots"
GROUP_AT_WORLD = "SkeldarKnots"

# -------------------------------------------------------------------- kinds

Kind = collections.namedtuple(
    "Kind", "key label suffix inner_suffix colour inner_colour constraint")

KINDS = (
    Kind("knot", "Knot", "_knot", "", (0.45, 0.85, 0.55), None, "parent"),
    Kind("offset", "Knot Offset", "_knotOffset", "", (1.0, 0.6, 0.25), None, "parent"),
    Kind("orient", "Knot Orient", "_knotOrient", "", (0.4, 0.7, 1.0), None, "orient"),
    Kind("double_local", "Double knot Local", "_dknotBase", "_dknot",
         (0.7, 0.5, 1.0), (0.85, 0.75, 1.0), "parent"),
    Kind("double_world", "Double knot World", "_dknotMove", "_dknotRotate",
         (1.0, 0.85, 0.3), (1.0, 0.95, 0.65), "parent"),
)
_KINDS = dict((k.key, k) for k in KINDS)

PIVOT_SUFFIX = "_pivot"
PIVOT_SPACE_SUFFIX = "_pivotSpace"
PIVOT_COLOUR = (1.0, 0.35, 0.35)


def kind(key):
    """The Kind `key` names, or None."""
    return _KINDS.get(key)


# ----------------------------------------------------------------- channels

TRANSLATE = ("tx", "ty", "tz")
ROTATE = ("rx", "ry", "rz")
CHANNELS = TRANSLATE + ROTATE
LONG = {"tx": "translateX", "ty": "translateY", "tz": "translateZ",
        "rx": "rotateX", "ry": "rotateY", "rz": "rotateZ"}
TIME_CURVES = ("animCurveTL", "animCurveTA", "animCurveTU", "animCurveTT")

TOLERANCE = 1e-6


def leaf(path):
    """A node's short name without its namespace: what a knot's name starts with."""
    return path.split("|")[-1].split(":")[-1]


def driver_word(node_type, is_constraint):
    """'' for a channel a knot may take (a time curve), else what drives it, in words."""
    if node_type in TIME_CURVES:
        return ""
    if node_type.startswith("animCurveU"):
        return "a driven key"
    if node_type.startswith("animBlendNode"):
        return "an animation layer"
    if is_constraint or node_type == "pairBlend":
        return "a constraint"
    if node_type == "expression":
        return "an expression"
    return "a " + node_type


def channel_plan(name, locked, drivers, channels=CHANNELS):
    """(free, skipped, refusal) for object `name`.

    `locked` {channel: bool}; `drivers` {channel: None (no input) | '' (a time curve) | words}.
    A locked channel is skipped (OverRig's -st / -sr), a free one driven by anything but a time
    curve refuses the object, no free channel refuses it. Pure."""
    free, skipped = [], []
    for ch in channels:
        if locked.get(ch):
            skipped.append(ch)
            continue
        word = drivers.get(ch)
        if word:
            return [], [], "%s.%s is driven by %s - a knot takes keyed or free channels" % (
                name, LONG[ch], word)
        free.append(ch)
    if not free:
        what = "rotate" if tuple(channels) == ROTATE else "translate or rotate"
        return [], skipped, "%s has no free %s channel" % (name, what)
    return free, skipped, ""


def encode_keyed(keyed):
    """The channels we keyed at creation and their values, as text."""
    return " ".join("%s=%r" % (ch, float(keyed[ch])) for ch in CHANNELS if ch in keyed)


def decode_keyed(text):
    out = {}
    for item in (text or "").split():
        ch, _, value = item.partition("=")
        try:
            out[ch] = float(value)
        except ValueError:
            continue
    return out


def is_constant(values, tolerance=TOLERANCE):
    return bool(values) and max(values) - min(values) <= tolerance


def still_static(values, value, tolerance=TOLERANCE):
    """True when a curve we keyed still holds nothing but the value we keyed (the animator did
    not key it since): Remove may cut it."""
    return bool(values) and all(abs(v - value) <= tolerance for v in values)


def uneven_parent(name, matrix):
    """'' or a refusal: a parent matrix (16 floats, row-major) scaled unevenly, sheared or
    mirrored cannot be followed by a constraint - the object would stand off its own animation
    (0.4-0.8 cm measured under a (1, 2.5, 0.7) parent). Uniform scale is fine. Pure."""
    rows = [matrix[0:3], matrix[4:7], matrix[8:11]]
    lengths = [math.sqrt(sum(v * v for v in row)) for row in rows]
    if min(lengths) < 1e-9:
        return "%s's parent is scaled to zero - a knot cannot hold it" % name
    spread = max(lengths) / min(lengths) - 1.0
    skew = max(abs(sum(a * b for a, b in zip(rows[i], rows[j]))) / (lengths[i] * lengths[j])
               for i, j in ((0, 1), (0, 2), (1, 2)))
    det = (rows[0][0] * (rows[1][1] * rows[2][2] - rows[1][2] * rows[2][1])
           - rows[0][1] * (rows[1][0] * rows[2][2] - rows[1][2] * rows[2][0])
           + rows[0][2] * (rows[1][0] * rows[2][1] - rows[1][1] * rows[2][0]))
    if spread > 1e-4 or skew > 1e-4 or det < 0:
        return ("%s's parent is scaled unevenly, sheared or mirrored - a knot's constraint "
                "cannot hold it in place" % name)
    return ""


# ------------------------------------------------------------------ eulers

#  The middle axis of each rotate order (Maya's enum: xyz yzx zxy xzy yxz zyx), as a channel
#  index: an euler's other solution turns the outer two by 180 and the middle to 180 - b.
_MIDDLE = (1, 2, 0, 2, 0, 1)


def unwrapped(previous, value):
    """`value` moved by whole turns to stand nearest `previous`."""
    return value - 360.0 * round((value - previous) / 360.0)


def closest_euler(previous, angles, order):
    """The equivalent of euler `angles` (rx, ry, rz in degrees, rotate order `order`) nearest
    `previous`: whole turns per channel, and the other solution tried - an euler filter's step.
    Pure."""
    middle = _MIDDLE[int(order)]
    other = tuple((180.0 - v) if i == middle else (v + 180.0) for i, v in enumerate(angles))
    best = None
    for candidate in (tuple(angles), other):
        moved = tuple(unwrapped(p, v) for p, v in zip(previous, candidate))
        cost = sum(abs(m - p) for m, p in zip(moved, previous))
        if best is None or cost < best[0] - 1e-9:
            best = (cost, moved)
    return best[1]


def continuous_eulers(anchor, rows, order):
    """Rows of (rx, ry, rz) made continuous from `anchor` (None: the first row stays as it is).
    What a bake's own keys get - never the rest of the animator's curve (filterCurve on the whole
    curve rewrote a key at 300 to -60, far outside the bake). Pure."""
    out, previous = [], anchor
    for row in rows:
        current = tuple(row) if previous is None else closest_euler(previous, row, order)
        out.append(current)
        previous = current
    return out


def continuous_channel(anchor, values):
    """One rotate channel's values made continuous by whole turns (the other two locked: the
    other euler solution needs all three). Pure."""
    out, previous = [], anchor
    for value in values:
        current = value if previous is None else unwrapped(previous, value)
        out.append(current)
        previous = current
    return out


# -------------------------------------------------------------------- spans

def take_range(playback, animation):
    """The take a whole-take knot covers: the playback and animation ranges together (OverRig
    baked over the animation range; a narrowed playback must not freeze the object outside it)."""
    return (min(playback[0], animation[0]), max(playback[1], animation[1]))


def span_for(playback, keys, highlight):
    """(start, end, ranged) a knot is baked over.

    A highlight of more than one frame, `[a, b)` as `timeControl -rangeArray` answers it, gives
    OverRig's `[a-1, b]`; otherwise the whole take - the playback range and the object's keys,
    whole frames outward."""
    if highlight and highlight[1] - highlight[0] > 1:
        return (float(highlight[0]) - 1.0, float(highlight[1]), True)
    lo, hi = float(playback[0]), float(playback[1])
    if keys:
        lo, hi = min(lo, min(keys)), max(hi, max(keys))
    return (float(math.floor(lo)), float(math.ceil(hi)), False)


def widen(span, keys):
    """`span` grown to hold `keys` (a knot the animator keyed past its own span)."""
    if not keys:
        return span
    return (min(span[0], float(math.floor(min(keys)))),
            max(span[1], float(math.ceil(max(keys)))), span[2])


def encode_span(span):
    return "%r %r %d" % (float(span[0]), float(span[1]), int(bool(span[2])))


def decode_span(text):
    try:
        start, end, ranged = (text or "").split()
        return (float(start), float(end), bool(int(ranged)))
    except ValueError:
        return None


def influence(samples):
    """(first, last) frame where `attach` is above zero, from [(frame, value)], or None: what a
    Bake writes into the object (the animator may have keyed attach since). Pure."""
    on = [frame for frame, value in samples if value > TOLERANCE]
    if not on:
        return None
    return (float(min(on)), float(max(on)))


def attach_keys(span):
    """OverRig's attach keys for a ranged span `[a-1, b]`: 0 at a-1, 1 at a and b-1, 0 at b
    (flat tangents). [] for a whole take: attach stays 1, unkeyed."""
    start, end, ranged = span
    if not ranged:
        return []
    return [(start, 0.0), (start + 1.0, 1.0), (end - 1.0, 1.0), (end, 0.0)]


# --------------------------------------------------------- orders and sizes

ORDERS = ("object", "xyz", "xzy")
ORDER_DEFAULT = "object"
_ORDER_INDEX = {"xyz": 0, "xzy": 3}

MIN_SIZE = 3.0
DEFAULT_SIZE = 5.0
OUTER_SCALE = 1.6


def rotate_order_index(choice, object_order):
    """The knot's rotateOrder index: xyz 0, xzy 3, anything else (object) the object's own."""
    return _ORDER_INDEX.get(choice, int(object_order))


def knot_size(diagonal, radius=None):
    """A knot's locator scale: a third of the object's bounding-box diagonal, at least 3 cm; a
    joint without a shape twice its radius; nothing known 5."""
    if diagonal and diagonal > TOLERANCE:
        return max(diagonal / 3.0, MIN_SIZE)
    if radius:
        return max(radius * 2.0, MIN_SIZE)
    return DEFAULT_SIZE


# ----------------------------------------------------- order and the choice

def bake_order(pairs):
    """`pairs` [(knot, source)] -> the knots, a knot whose source is another listed knot first
    (a knot on a knot collapses inward), the rest in their order. Pure."""
    source = dict(pairs)

    def depth(knot, seen):
        nxt = source.get(knot)
        if nxt in source and nxt not in seen:
            return 1 + depth(nxt, seen | {knot})
        return 0

    knots = [k for k, _ in pairs]
    return sorted(knots, key=lambda k: -depth(k, frozenset()))


def choose_pivot(named, waiting):
    """(pivot, refusal) for Finish: the selected pivot, else the only one waiting."""
    if len(named) == 1:
        return named[0], ""
    if len(named) > 1:
        return None, "%d pivots selected - select the one to finish" % len(named)
    if len(waiting) == 1:
        return waiting[0], ""
    if not waiting:
        return None, "no pivot is waiting - press Offset first"
    return None, "%d pivots are waiting (%s) - select the one to finish" % (
        len(waiting), ", ".join(leaf(p) for p in waiting))


# ------------------------------------------------------------------ lines

NOTHING = "select the objects to knot"
OFFSET_ONE = "Knot Offset takes one object - select one"
BAKE_NOTHING = "select a knot, or an object riding one, to bake it"
REMOVE_NOTHING = "select a knot, a waiting pivot, or an object riding a knot"


def _num(value):
    return "%g" % value


def _plural(count, word):
    return "%d %s%s" % (count, word, "" if count == 1 else "s")


def span_words(span):
    start, end, ranged = span
    if ranged:
        return "over %s-%s (the highlight - attach blends it in and out)" % (
            _num(start + 1.0), _num(end - 1.0))
    return "over %s-%s" % (_num(start), _num(end))


def riding_refusal(name):
    return ("%s already rides a knot - select its knot to knot it again, or Bake / Remove "
            "first" % name)


def created_message(label, pairs, span):
    """`pairs` [(object leaf, knot leaf)]."""
    if len(pairs) == 1:
        return "%s: %s rides %s %s" % (label, pairs[0][0], pairs[0][1], span_words(span))
    return "%s: %d objects ride knots %s" % (label, len(pairs), span_words(span))


def begin_message(name):
    return ("%s: place the pivot - move and turn it, it rides %s while you place it - then press "
            "Finish" % (name, name))


def finish_message(name, knot, span):
    return "Knot Offset: %s rides %s at its pivot %s" % (name, knot, span_words(span))


def baked_message(names):
    return "Baked %s onto %s" % (_plural(len(names), "knot"), ", ".join(names))


def removed_message(names, pivots):
    parts = []
    if names:
        parts.append("Removed %s - %s play%s their own animation again" % (
            _plural(len(names), "knot"), ", ".join(names), "" if len(names) != 1 else "s"))
    if pivots:
        parts.append("%s dropped" % _plural(pivots, "pivot"))
    return "; ".join(parts)


def offset_label(waiting):
    """The Offset button's word (2026-10-12, the compact card: short words)."""
    return "Finish" if waiting else "Offset"


def subtitle(knot_count, pivot_count):
    parts = []
    if knot_count:
        parts.append("%s in the scene" % _plural(knot_count, "knot"))
    if pivot_count:
        parts.append("%s waiting" % _plural(pivot_count, "pivot"))
    return ", ".join(parts) if parts else "no knots in the scene"
