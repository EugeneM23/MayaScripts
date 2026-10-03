"""maya_poselib.animdata - the pure arithmetic of an animation card (2026-10-03). Stdlib only.

The animator: «теперь давай добавим возможность сохранять анимации. Все правила которые работают
для поз должны работать и для анимаций. Так же мы должны уметь выбирать способ вставки анимации как
в studio library». An animation card is a pose card per frame: the header (`anim.json`) holds each bone's STATIC half
(parent, canonical name, rest, rotate order) once, and `frames.json.gz` its per-frame half - every
bone's world matrix (and, from a rig, the drive of the unrolled limb bones) on every frame of the
range. This module holds what needs no scene:

  - the frame CODEC: a world matrix written as seven numbers, a unit quaternion and a translation
    (`encode` / `decode`). Scale and shear are dropped - the pose library reads a bone's turn and
    its place, never its scale - and the file is a third the size of sixteen numbers a bone;
  - a frame of the arrays read back as a POSE card's bones (`bones_at`), so the pose's transfer
    and solve take a frame exactly as they take a pose;
  - the apply OPTIONS (`Options`, `options_from` - what the window remembers, validated);
  - the PASTE PLAN (`paste_plan`): which source frame lands on which target frame, and what the
    paste mode cuts or moves on the layer curves before the keys go in (Studio Library's / Maya's
    `pasteKey` modes);
  - Connect's offsets (`connect_offsets` / `apply_offsets`): every pasted channel moved so its
    first pasted value is what the channel showed at the paste frame.

Matrices are 16-float lists, row-major, in Maya's row-vector convention (`world = local · parent`),
as everywhere in the library. Frames are WHOLE frames: a time is rounded half up (`_frame`).

Spec: docs/superpowers/specs/2026-10-03-pose-library-animation-design.md
"""

import math
from collections import OrderedDict, namedtuple

MODES = ("replace", "replace_all", "insert", "merge")
KEY_MODES = ("every", "source")
MODE_LABELS = {"replace": "Replace", "replace_all": "Replace all", "insert": "Insert",
               "merge": "Merge"}

EMPTY_RANGE = "the range holds no frame of the clip"

#  How a card is pasted: `mode` one of MODES; `at_current` - the first pasted frame lands on the
#  current frame (off: on its own source frame); `start` / `end` - a part of the clip in source
#  frames (None: the clip's own end); `connect` - Connect's offsets; `keys` one of KEY_MODES (a
#  key on every frame, or only where the source had keys); `in_place` - root / Main untouched
Options = namedtuple("Options", "mode at_current start end connect keys in_place")
Options.__new__.__defaults__ = ("replace", True, None, None, False, "every", False)

#  What a paste does: `frames` [(source frame, index into the frames arrays, target time)] in
#  time order; `a` / `b` the target times of the first and last pasted frame; `offset` target
#  minus source; `ops` what the paste mode does to the layer curves first - [("cut", a, b)],
#  [("cut_all",)], [("shift", a, n)] (every key at or after `a` moves n frames later) or []
PastePlan = namedtuple("PastePlan", "frames a b offset ops")

_FALSE = ("", "0", "false", "off", "no", "none")


# ---------------------------------------------------------------- the frame codec

def _rows(flat):
    """The three rotation rows of a row-vector matrix, orthonormalised: scale and shear dropped,
    the X row's direction kept, the Y row made square to it, the Z row their cross product (so a
    mirrored matrix comes back a turn, never a reflection)."""
    def norm(v):
        n = math.sqrt(sum(c * c for c in v)) or 1.0
        return [c / n for c in v]

    r0 = norm(list(flat[0:3]))
    r1 = list(flat[4:7])
    d = sum(a * b for a, b in zip(r1, r0))
    r1 = norm([a - d * b for a, b in zip(r1, r0)])
    r2 = [r0[1] * r1[2] - r0[2] * r1[1], r0[2] * r1[0] - r0[0] * r1[2],
          r0[0] * r1[1] - r0[1] * r1[0]]
    return r0, r1, r2


def _clean(value, places):
    """`value` rounded to `places` decimals, a negative zero written as zero (the file stays
    compact and two encodings of one pose compare equal as text)."""
    return round(value, places) + 0.0


def encode(flat):
    """[qx, qy, qz, qw, tx, ty, tz] of a 16-float world matrix: its turn as a unit quaternion
    (9 decimals - about 1e-7 degrees, far below what a key shows) and its translation (6
    decimals of a cm, a hundredth of a micron). Maya's quaternion of the same turn (MQuaternion: +90 about X
    is (sin 45, 0, 0, cos 45)). Shepperd's method, the branch on the largest diagonal term, so a
    half turn reads as exactly as the identity."""
    r0, r1, r2 = _rows(flat)
    # M = the column-vector matrix, the transpose of the row-vector rows
    m00, m01, m02 = r0[0], r1[0], r2[0]
    m10, m11, m12 = r0[1], r1[1], r2[1]
    m20, m21, m22 = r0[2], r1[2], r2[2]
    tr = m00 + m11 + m22
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        w, x, y, z = 0.25 * s, (m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        w, x, y, z = (m21 - m12) / s, 0.25 * s, (m01 + m10) / s, (m02 + m20) / s
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        w, x, y, z = (m02 - m20) / s, (m01 + m10) / s, 0.25 * s, (m12 + m21) / s
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
        w, x, y, z = (m10 - m01) / s, (m02 + m20) / s, (m12 + m21) / s, 0.25 * s
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    return [_clean(x / n, 9), _clean(y / n, 9), _clean(z / n, 9), _clean(w / n, 9),
            _clean(flat[12], 6), _clean(flat[13], 6), _clean(flat[14], 6)]


def decode(q):
    """The 16-float world matrix of seven numbers `encode` wrote (floats, scale 1). The quaternion
    is normalised first: what the rounding to 9 decimals left, or a hand-written file, names a
    turn and never a scale."""
    x, y, z, w = (float(v) for v in q[0:4])
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    m = [[1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
         [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
         [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)]]
    rows = [[m[0][i], m[1][i], m[2][i]] for i in range(3)]          # back to row vectors
    out = []
    for row in rows:
        out += row + [0.0]
    return out + [float(q[4]), float(q[5]), float(q[6]), 1.0]


def bones_at(header, frames, index, mirror=None):
    """{leaf: {"parent", "canonical", "rest", "rotateOrder", "world"[, "drive"]}} - a POSE card's
    bones for frame `index` of the arrays: each header bone's static half copied (the header is
    never touched, the rest a list of its own), its `world` decoded from that frame, its `drive`
    where the frames hold one. The header's order. A header bone the frames do not hold has no
    world and is left out (the pose's transfer reads a world for every bone it is given).
    `index` outside the arrays is an IndexError, never Python's count from the end. `mirror` is
    reserved: the press mirrors the bones itself (posemath.mirror)."""
    world = frames["world"]
    if not 0 <= index < len(world):
        raise IndexError("frame %d of %d" % (index, len(world)))
    row = world[index]
    slot = dict((leaf, i) for i, leaf in enumerate(frames["bones"]))
    drives = frames.get("drive") or {}
    out = OrderedDict()
    for leaf, static in header["bones"].items():
        i = slot.get(leaf)
        if i is None:
            continue
        bone = dict(static)
        if isinstance(bone.get("rest"), list):
            bone["rest"] = list(bone["rest"])
        bone["world"] = decode(row[7 * i:7 * i + 7])
        series = drives.get(leaf)
        if series:
            bone["drive"] = decode(series[index])
        out[leaf] = bone
    return out


# ---------------------------------------------------------------- the options and the plan

def _frame(time):
    """A time as a whole frame, rounded half UP: Python's round() goes to even, so 12.5 and 13.5
    would land on 12 and 14 - a paste at a half frame must not depend on which half."""
    return int(math.floor(float(time) + 0.5))


def _flag(value):
    """A remembered on/off as a bool: optionVars hand back ints and strings ("0" is off)."""
    if isinstance(value, str):
        return value.strip().lower() not in _FALSE
    return bool(value)


def _number(value):
    """A remembered range end as a float, or None when there is none (empty, not a number, not
    finite)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def options_from(mapping):
    """`Options` of a mapping (the window's remembered values): only the fields `Options` knows
    are read, each validated - an unknown paste mode is "replace", unknown keys "every", flags
    are bools, range ends floats or None - so a value from an older build or a colleague's prefs
    never reaches a press."""
    mapping = mapping or {}
    base = Options()
    mode = mapping.get("mode", base.mode)
    keys = mapping.get("keys", base.keys)
    return Options(
        mode=mode if mode in MODES else "replace",
        at_current=_flag(mapping.get("at_current", base.at_current)),
        start=_number(mapping.get("start")),
        end=_number(mapping.get("end")),
        connect=_flag(mapping.get("connect", base.connect)),
        keys=keys if keys in KEY_MODES else "every",
        in_place=_flag(mapping.get("in_place", base.in_place)))


def paste_plan(start, end, key_times, options, current):
    """The `PastePlan` of a clip saved over source frames `start`..`end` (its frames arrays hold
    one entry a frame from `start`), pasted with `options` while the time stands at `current`.

    The source range is the options' `start`..`end` clamped to the clip, in whole frames; a range
    holding no frame is refused (`ValueError(EMPTY_RANGE)`). Keys "every": every frame of it;
    "source": its two ends and every source key time inside it (`key_times`, rounded), so the
    curves interpolate between them as the source's did. The first pasted frame lands on the
    current frame (rounded) - or, `at_current` off, on its own source frame. The ops are the
    paste mode's: Replace cuts the keys inside the paste range, Replace all every key, Insert moves
    every key at or after the first pasted frame later by the clip's length, Merge touches
    nothing. An unknown mode or keys value is refused, never guessed (`options_from` is where the
    window's values are made valid); `options` None is the defaults."""
    options = options or Options()
    if options.mode not in MODES:
        raise ValueError("unknown paste mode %r" % (options.mode,))
    if options.keys not in KEY_MODES:
        raise ValueError("unknown keys %r" % (options.keys,))
    first = _frame(start)
    lo, hi = first, _frame(end)
    if options.start is not None:
        lo = max(lo, _frame(options.start))
    if options.end is not None:
        hi = min(hi, _frame(options.end))
    if lo > hi:
        raise ValueError(EMPTY_RANGE)
    if options.keys == "source":
        inside = set(_frame(k) for k in (key_times or ()))
        source = sorted(set([lo, hi]) | set(k for k in inside if lo <= k <= hi))
    else:
        source = list(range(lo, hi + 1))
    offset = _frame(current) - lo if options.at_current else 0
    a, b = lo + offset, hi + offset
    if options.mode == "replace":
        ops = [("cut", a, b)]
    elif options.mode == "replace_all":
        ops = [("cut_all",)]
    elif options.mode == "insert":
        ops = [("shift", a, b - a + 1)]
    else:
        ops = []
    frames = [(s, s - first, s + offset) for s in source]
    return PastePlan(frames, a, b, offset, ops)


# ---------------------------------------------------------------- Connect

def connect_offsets(before, first, skip=()):
    """{plug: before - first} for every plug both mappings hold and `skip` does not: what each
    pasted channel is moved by so its FIRST pasted value (`first`, the solve at the paste frame)
    becomes the value it showed there before the paste (`before`) - Studio Library's / Maya's
    `pasteKey -connect`. The press skips Main and the root (the travel is placed, not offset).
    `first`'s order."""
    skip = set(skip or ())
    out = OrderedDict()
    for plug, value in first.items():
        if plug in skip or plug not in before:
            continue
        out[plug] = before[plug] - value
    return out


def apply_offsets(values, offsets):
    """A new OrderedDict of `values` (their order) each moved by its offset; a plug without one
    is kept as it is. `values` is left alone."""
    return OrderedDict((plug, value + offsets.get(plug, 0.0)) for plug, value in values.items())
