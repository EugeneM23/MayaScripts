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
PENDING_KIND_MARKER = "skeldarKnotPendingKind"  # ... and what waits in it: "aim" (none: offset)
ORDER_MARKER = "skeldarKnotOrder"               # a waiting pivot: the rotate order choice
INNER_MARKER = "skeldarKnotInner"               # a double knot's inner node: its top's UUID
REGISTRY_MARKER = "skeldarKnotRegistry"         # the objectSet holding every across knot
GROUP_MARKER = "skeldarKnotGroup"               # the group knots live in
SNAPSHOT_OF_MARKER = "skeldarSnapshotOf"        # a snapshot: its object's UUID (it rides nothing)
ATTACH = "attach"                               # 0..1 on the top node: the object's own <-> the knot

GROUP_IN_CHARACTER = "Knots"
GROUP_AT_WORLD = "SkeldarKnots"
REGISTRY_NAME = "SkeldarAcrossKnots"

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
    #  2026-10-12, the parent tab: a knot inside the parent (OverRig's across).
    Kind("across", "Across", "_across", "", (0.3, 0.85, 0.8), None, "parent"),
    #  2026-10-13, the aim tab: a group holding a target and an up; the object's rotation aims
    #  at the target, leaning to the up (OverRig's aim).
    Kind("aim", "Aim", "_aim", "_aimUp", (1.0, 0.45, 0.65), (0.65, 0.9, 1.0), "aim"),
    #  2026-10-13, the snapshot: a locator repeating the object's world motion on every frame,
    #  driving nothing - nothing follows it (OverRig's object snapshot, in its colour).
    Kind("snapshot", "Snapshot", "_snapshot", "", (0.8, 0.5, 0.5), None, None),
)
_KINDS = dict((k.key, k) for k in KINDS)

PIVOT_SUFFIX = "_pivot"
PIVOT_SPACE_SUFFIX = "_pivotSpace"
PIVOT_COLOUR = (1.0, 0.35, 0.35)
AIM_TARGET_SUFFIX = "_aimTarget"
AIM_SPACE_SUFFIX = "_aimSpace"
AIM_REACH = 4.0                 # the target and the up start this many knot sizes from the object
AIM_UP_MIN_DEG = 3.0            # an up nearer the line to the target than this is refused


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


def snapshot_span(playback, keys, highlight):
    """(start, end, ranged) a snapshot is baked over: a highlight of more than one frame `[a, b)`
    gives exactly its frames `a .. b-1` (OverRig's: no ramp, nothing blends); otherwise the whole
    take, as a knot's. Pure."""
    if highlight and highlight[1] - highlight[0] > 1:
        return (float(highlight[0]), float(highlight[1]) - 1.0, True)
    return span_for(playback, keys, None)


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
SNAPSHOT_NOTHING = "select the objects to snapshot"
SNAPSHOT_COMPONENTS = "components are not snapshotted - select the object"
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


def snapshot_message(pairs, span):
    """`pairs` [(object leaf, snapshot leaf)], `span` its snapshot_span."""
    start, end, ranged = span
    words = "over %s-%s%s" % (_num(start), _num(end), " (the highlight)" if ranged else "")
    if len(pairs) == 1:
        return "Snapshot: %s -> %s %s" % (pairs[0][0], pairs[0][1], words)
    return "Snapshot: %d objects %s" % (len(pairs), words)


def snapshot_skipped(names):
    """Bake has nothing to write for a snapshot (it drives nothing)."""
    if len(names) == 1:
        return "%s is a snapshot - it drives nothing (Remove deletes it)" % names[0]
    return "%d snapshots skipped - they drive nothing (Remove deletes them)" % len(names)


def baked_message(names):
    return "Baked %s onto %s" % (_plural(len(names), "knot"), ", ".join(names))


def removed_message(names, pivots, snapshots=0):
    parts = []
    if names:
        parts.append("Removed %s - %s play%s their own animation again" % (
            _plural(len(names), "knot"), ", ".join(names), "" if len(names) != 1 else "s"))
    if pivots:
        parts.append("%s dropped" % _plural(pivots, "pivot"))
    if snapshots:
        parts.append("%s deleted" % _plural(snapshots, "snapshot"))
    return "; ".join(parts)


def offset_label(waiting):
    """The Offset button's word (2026-10-12, the compact card: short words)."""
    return "Finish" if waiting else "Offset"


def subtitle(knot_count, pivot_count, aim_count=0, snapshot_count=0):
    parts, standing = [], []
    if knot_count:
        standing.append(_plural(knot_count, "knot"))
    if snapshot_count:
        standing.append(_plural(snapshot_count, "snapshot"))
    if standing:
        parts.append("%s in the scene" % ", ".join(standing))
    if pivot_count:
        parts.append("%s waiting" % _plural(pivot_count, "pivot"))
    if aim_count:
        parts.append("%s waiting" % _plural(aim_count, "aim"))
    return ", ".join(parts) if parts else "no knots in the scene"


# ------------------------------------------------------------------ the aim tab

AIM_NOTHING = "select the objects to aim"


def aim_reach(size):
    """How far from the object its target and up start: four knot sizes."""
    return size * AIM_REACH


def _length(vector):
    return math.sqrt(sum(c * c for c in vector))


def axes_of(matrix):
    """The three axes (unit rows, made perpendicular) of a 16-value world matrix: its rotation
    with scale and shear taken out."""
    rows = [list(matrix[0:3]), list(matrix[4:7]), list(matrix[8:11])]
    x = [c / _length(rows[0]) for c in rows[0]]
    dot = sum(a * b for a, b in zip(rows[1], x))
    y = [a - dot * b for a, b in zip(rows[1], x)]
    y = [c / _length(y) for c in y]
    z = [x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0]]
    if sum(a * b for a, b in zip(z, rows[2])) < 0.0:       # a mirrored matrix keeps its Z
        z = [-c for c in z]
    return [tuple(x), tuple(y), tuple(z)]


def aim_vectors(name, target, up):
    """(aim vector, up vector, refusal) in the object's own axes, from where its target and up
    stand off its pivot (in its axes): the aimConstraint's vectors, so it holds the object where
    it stands. A target on the object, or an up on the line to the target, is refused."""
    length = _length(target)
    if length < 1e-4:
        return None, None, "%s: the aim target stands on the object - move it away" % name
    aim = tuple(c / length for c in target)
    dot = sum(a * b for a, b in zip(up, aim))
    across = tuple(a - dot * b for a, b in zip(up, aim))
    reach = _length(up)
    if reach < 1e-4 or _length(across) < math.sin(math.radians(AIM_UP_MIN_DEG)) * reach:
        return None, None, ("%s: the aim's up stands on the line to its target - move it to the "
                            "side" % name)
    return aim, tuple(c / _length(across) for c in across), ""


def choose_aims(named, waiting):
    """(aims, refusal) a Finish takes: the waiting aims the selection names, else every one."""
    if named:
        return list(named), ""
    if waiting:
        return list(waiting), ""
    return None, "no aim is waiting - press Aim first"


def aim_label(waiting):
    """The Aim button's word: Finish while an aim waits."""
    return "Finish" if waiting else "Aim"


def aim_begin_message(names):
    who = names[0] if len(names) == 1 else "%d objects" % len(names)
    return ("Aim: place the target (where %s points) and the up (where it leans) - they ride it "
            "while you place them - then press Finish" % who)


def aim_finish_message(pairs, span):
    """`pairs` [(object leaf, target leaf)]."""
    if len(pairs) == 1:
        return "Aim: %s aims at %s %s" % (pairs[0][0], pairs[0][1], span_words(span))
    return "Aim: %d objects aim at their targets %s" % (len(pairs), span_words(span))


# ------------------------------------------------------------ the parent tab

SWAP_TWO = "Swap takes two or more objects - select the parent first, then its child"
INSIDE_TWO = "select the objects, then the parent LAST (two or more)"
ACROSS_TWO = "select the objects, then the one they ride LAST (two or more)"
ATTACH_NOTHING = "select a knot, or an object riding one, to key its attach"


def inside_refusal(children, parent, parent_of):
    """'' or why Inside cannot put `children` under `parent` (long paths). Pure."""
    for child in children:
        name = leaf(child)
        if child == parent:
            return "%s is the parent - select the objects, then the parent LAST" % name
        if parent.startswith(child + "|"):
            return "the parent %s lies inside %s - a cycle" % (leaf(parent), name)
        if parent_of(child) == parent:
            return "%s is already inside %s" % (name, leaf(parent))
    return ""


def world_refusal(nodes, parent_of):
    for node in nodes:
        if parent_of(node) is None:
            return "%s is already at world level" % leaf(node)
    return ""


def swap_plan(paths, parent_of):
    """(moves, refusal) for Swap, OverRig's rule: after every node went to world level the others
    go under the LAST selected, and the last under the former parent of the one before it.
    `moves` [(node, new parent or None)] in that order. Pure."""
    paths = list(paths)
    if len(paths) < 2:
        return None, SWAP_TWO
    last, before = paths[-1], paths[-2]
    former = parent_of(before)
    for node in paths:
        if former and (former == node or former.startswith(node + "|")):
            return None, ("%s lies inside %s - select the parent first, then its child"
                          % (leaf(former), leaf(node)))
    return [(node, last) for node in paths[:-1]] + [(last, former)], ""


def attach_times(highlight, selected_keys, now):
    """When Attach 0 / 1 keys: the highlight's two ends (a, b-1), else the selected graph keys'
    first and last time, else the current frame. Pure."""
    if highlight and highlight[1] - highlight[0] > 1:
        return (float(highlight[0]), float(highlight[1]) - 1.0)
    if selected_keys:
        first, last = float(min(selected_keys)), float(max(selected_keys))
        return (first,) if first == last else (first, last)
    return (float(now),)


def list_label(word, count):
    return "%s %d" % (word, count) if count else word


def multiple_refusal(objects, targets, rotate, translate):
    if not objects or not targets:
        return "remember Objects and Targets first (select, then press each)"
    if objects != targets:
        return "Objects %d, Targets %d - they must match, pair by pair" % (objects, targets)
    if not rotate and not translate:
        return "turn Rotate or Translate on - the object would follow nothing"
    return ""


def rig_part_line(name, what):
    return "%s is %s - re-parenting it would break it; use Across" % (name, what)


def locked_line(name):
    return ("%s has locked translate or rotate channels - a re-parent rewrites them all" % name)


SCALE = ("sx", "sy", "sz")
SCALE_LONG = {"sx": "scaleX", "sy": "scaleY", "sz": "scaleZ"}


def scale_plan(ratios, tolerance=TOLERANCE):
    """How a re-parent carries an object's world scale (2026-10-13: an object keyed with S was
    refused under a scaled parent). `ratios` the old parent's world scale over the new one's, per
    frame of the take - one value when nothing in either chain animates scale.

    ('keep', 1.0): the same scale either side, nothing to do. ('rescale', k): one factor on every
    frame - the scale keys multiplied by k (they stay keys), an unkeyed channel compensated by
    Maya's own parent command. ('bake', None): the factor changes over the take - the scale keyed
    on every frame, as translate and rotate are. Pure."""
    if not ratios:
        return ("keep", 1.0)
    low, high = min(ratios), max(ratios)
    if high - low > tolerance * max(1.0, abs(high)):
        return ("bake", None)
    factor = float(ratios[0])
    if abs(factor - 1.0) <= tolerance:
        return ("keep", 1.0)
    return ("rescale", factor)


def carried_scale(values, ratios):
    """The local scale on each frame after the move: the old local value times that frame's
    ratio. Pure."""
    return [float(v) * float(r) for v, r in zip(values, ratios)]


def scale_refusal(name, kind, locked, drivers):
    """'' or why the object's scale cannot follow a move where the parents' scales differ (`kind`
    not 'keep'): a scale channel locked, or driven by anything but a time curve (`drivers` as
    `channel_plan` reads them). Pure."""
    if kind == "keep":
        return ""
    for ch in SCALE:
        if locked.get(ch):
            return ("%s.%s is locked and its new parent is scaled differently - unlock it, or "
                    "the object would change size" % (name, SCALE_LONG[ch]))
        if drivers.get(ch):
            return ("%s.%s is driven by %s and its new parent is scaled differently - the scale "
                    "cannot follow the move" % (name, SCALE_LONG[ch], drivers[ch]))
    return ""


def uneven_target(name, target, matrix):
    """'' or why an across knot cannot live inside `target` (its world matrix)."""
    if not uneven_parent(name, matrix):
        return ""
    return ("%s: %s is scaled unevenly, sheared or mirrored - a knot inside it cannot hold the "
            "object" % (name, target))


def reparent_message(verb, names, parent, span):
    who = names[0] if len(names) == 1 else "%d objects" % len(names)
    if verb == "World":
        where = "to world level"
    elif verb == "Swap":
        where = "swapped (%s on top)" % parent
    else:
        where = "under %s" % parent
    return "%s: %s moved %s, the motion kept %s" % (verb, who, where, span_words(span))


def attach_message(value, count, times):
    when = ("at %s" % _num(times[0]) if len(times) == 1
            else "over %s-%s" % (_num(times[0]), _num(times[-1])))
    return "attach %s keyed on %s %s" % (_num(value), _plural(count, "knot"), when)


# ------------------------------------------------- Bake to a layer (2026-10-13)

LAYER_PREFIX = "Baked_"
LAYER_MARKER = "skeldarBakeLayer"           # our layers: the baked objects' leaves
LAYER_MIN = 1e-4                           # a difference under this on every frame: not written
LAYER_NOTHING = ("select an object a knot or a constraint drives (or its knot) to bake it onto "
                 "a layer")


def driver_kind(knot, held, ours, rig_own):
    """What one constraint on an object is to Layer: "knot" (ours, taken off as Remove does),
    "retarget" (the Retarget holds it), "ours" (another card's - a weapon link, a hand proxy, the
    scene camera), "rig" (the rig's own), else "foreign" (baked and deleted). Pure."""
    if knot:
        return "knot"
    if held:
        return "retarget"
    if ours:
        return "ours"
    if rig_own:
        return "rig"
    return "foreign"


def driver_refusal(kind, name, constraint):
    """'' or why a constraint keeps the whole press from running."""
    if kind == "retarget":
        return ("%s is held by the Retarget (%s) - press Retarget to finish it first"
                % (name, constraint))
    if kind == "ours":
        return ("%s is driven by the plugin (%s) - undo it in its own card (Weapons, "
                "Connections, Camera Setup)" % (name, constraint))
    if kind == "rig":
        return "%s is driven by its rig (%s) - baking it would break the rig" % (name, constraint)
    return ""


def undriven_refusal(name, words, layered=False):
    """Why an object with nothing Layer takes is refused: no keys of its own, no knot, no
    constraint. `words` what else drives its channels; `layered` its motion is on layers."""
    seen = []
    for word in words or []:
        if word not in seen:
            seen.append(word)
    if seen:
        return "%s is driven by %s - Layer bakes keys, knots and constraints" % (
            name, " and ".join(seen))
    if layered:
        return "%s: its animation is on layers already - nothing left on its base to bake" % name
    return "nothing animates %s - no keys of its own, no knot, no constraint" % name


def layer_name(leaves):
    return LAYER_PREFIX + leaf(leaves[0])


def layer_deltas(shown, own, order, free, minimum=LAYER_MIN):
    """{channel: [difference per frame]}: what an additive layer (by component) adds to `own` for
    the object to show `shown` - rows of (tx, ty, tz, rx, ry, rz) per frame. The shown rotation is
    made continuous from the own one first and then from the frame before it (all three rotates
    free: the other euler solution too; else whole turns), so the layer holds the real turn and
    never a 360 step. Only `free` channels; one whose difference stays under `minimum` is left
    out (a negative one keeps every channel). Pure."""
    out = {}
    if not shown:
        return out
    rows = [list(s) for s in shown]
    rotates = [ch for ch in ROTATE if ch in free]
    if rotates == list(ROTATE):
        previous = tuple(own[0][3:6])
        for row in rows:
            row[3:6] = list(closest_euler(previous, row[3:6], order))
            previous = tuple(row[3:6])
    else:
        for ch in rotates:
            c = 3 + ROTATE.index(ch)
            previous = own[0][c]
            for row in rows:
                row[c] = unwrapped(previous, row[c])
                previous = row[c]
    for c, ch in enumerate(CHANNELS):
        if ch not in free:
            continue
        values = [row[c] - o[c] for row, o in zip(rows, own)]
        if max(abs(v) for v in values) > minimum:
            out[ch] = values
    return out


def anchored(deltas, minimum=LAYER_MIN):
    """(kept, shifts): the whole take's differences with each channel's first-frame value moved
    onto the base - the base then holds the pose of the first frame and the layer starts at 0.
    A channel left under `minimum` on every frame is dropped from `kept`. Pure."""
    kept, shifts = {}, {}
    for ch, values in deltas.items():
        shift = values[0]
        shifts[ch] = shift
        moved = [v - shift for v in values]
        if max(abs(v) for v in moved) > minimum:
            kept[ch] = moved
    return kept, shifts


def bridge_kind(out_types, weighted):
    """How a base curve's keys move onto the layer exactly under a highlight - from the out
    tangent types of its keys over it (one frame before it to its last key inside): "smooth" (no
    step: a Hermite segment minus the bridge's is a Hermite segment), "stepped" (every one a step:
    the bridge holds still, the keys move as they are), else None (weighted, or steps mixed in -
    keyed at its keys instead). Pure."""
    if weighted:
        return None
    if out_types and all(kind == "step" for kind in out_types):
        return "stepped"
    if any(kind in ("step", "stepnext") for kind in out_types):
        return None
    return "smooth"


def bridge_keys(keys, bridge):
    """The layer's keys over a highlight, exact: `keys` [(time, value, in slope, out slope)] of
    the base curve from one frame before the highlight to one frame after, `bridge` [(value, in
    slope, out slope)] of the bridged base at the same times; each layer key their difference.
    Slopes are UI units a frame. Pure."""
    return [(t, v - bv, si - bsi, so - bso)
            for (t, v, si, so), (bv, bsi, bso) in zip(keys, bridge)]


def bridged(times, first, last):
    """The base keys a highlight `first..last` takes away: those strictly between `first - 1`
    and `last + 1`, where the base then bridges on its own keys. Pure."""
    return [t for t in times if first - 1.0 + 1e-6 < t < last + 1.0 - 1e-6]


def layer_message(names, keyed, knots_off, constraints_off, first, last, ranged, layer,
                  notes=(), pose_frame=None):
    """The Layer press's line. `keyed`: how many objects had their own keys moved; `pose_frame`:
    the frame whose pose every base holds (None: each its own first frame)."""
    who = names[0] if len(names) == 1 else "%d objects" % len(names)
    moved = []
    if keyed:
        moved.append("its keys" if len(names) == 1 else "their keys")
    moved += [_plural(count, word) for count, word in ((knots_off, "knot"),
                                                       (constraints_off, "constraint")) if count]
    what = moved[0] if len(moved) == 1 else ", ".join(moved[:-1]) + " and " + moved[-1]         if moved else "nothing"
    if layer:
        line = "Layer: %s baked onto %s over %s-%s; %s moved onto it" % (
            who, layer, _num(first), _num(last), what)
        if ranged:
            line += " - outside the highlight the base keeps its keys"
        elif pose_frame is not None:
            line += ", the base holds the pose of frame %s" % _num(pose_frame)
        else:
            line += ", each base holds the pose of its first frame"
    else:
        line = ("Layer: %s - %s taken off; nothing changed over %s-%s, so no layer was made"
                % (who, what, _num(first), _num(last)))
    return " | ".join([line] + list(notes))
