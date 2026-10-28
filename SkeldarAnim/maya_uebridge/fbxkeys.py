"""The baked bone keys an FBX holds, read straight from the binary file. Stdlib only.

Why it exists (2026-10-27, the animator: «в сцене 30 фпс после экспорта в uasset 120»). Measured
in mayapy: **Maya 2027's FBX plugin latches its bake step at the first export of a session made at
a rate other than 30**, and every later baked export steps at that rate while its header says the
scene's. A 30 fps scene after a 24 fps export came out with keys every 1/24 s under a 30 fps
header; Unreal's legacy import, which takes the sample rate that passes through every key, read
120 (the LCM of 24 and the 1/120 s step to the last key at 59/30). FBXResetExport, a 30 fps
export, a 30 fps FBXRead and FBXPopSettings all leave the latch where it is. Nothing tells the
plugin's state but the file it wrote, so the export reads it back (`animexport`).

What is read is what Unreal reads: the key times of the curves on a Model's Lcl Translation,
Rotation and Scaling. A layer's weight curve or a custom attribute is not looked at.
"""

import struct
import zlib

TICKS = 46186158000.0  # FBX time units in a second
CHANNELS = (b"Lcl Translation", b"Lcl Rotation", b"Lcl Scaling")
MAGIC = b"Kaydara FBX Binary  "
TOLERANCE = 1e-3  # of a frame: off the grid by more than this is off it


# ---------------------------------------------------------------------------
# the binary format
# ---------------------------------------------------------------------------

def _records(data, start, end, wide):
    """(name, first property, property count, children start, end) of every record in [start, end)."""
    pos = start
    while pos < end:
        if wide:
            if pos + 25 > end:
                return
            stop, count, length = struct.unpack_from("<QQQ", data, pos)
            pos += 24
        else:
            if pos + 13 > end:
                return
            stop, count, length = struct.unpack_from("<III", data, pos)
            pos += 12
        if stop == 0:
            return
        name_len = data[pos]
        name = data[pos + 1:pos + 1 + name_len]
        first = pos + 1 + name_len
        yield name, first, count, first + length, stop
        pos = stop


_SCALARS = {b"Y": ("<h", 2), b"C": ("<?", 1), b"I": ("<i", 4), b"F": ("<f", 4),
            b"D": ("<d", 8), b"L": ("<q", 8)}
_ARRAYS = {b"f": "f", b"d": "d", b"l": "q", b"i": "i", b"b": "?"}


def _properties(data, pos, count):
    values = []
    for _ in range(count):
        kind = data[pos:pos + 1]
        pos += 1
        if kind in _SCALARS:
            fmt, size = _SCALARS[kind]
            values.append(struct.unpack_from(fmt, data, pos)[0])
            pos += size
        elif kind in _ARRAYS:
            length, encoding, size = struct.unpack_from("<III", data, pos)
            pos += 12
            raw = data[pos:pos + size]
            pos += size
            if encoding == 1:
                raw = zlib.decompress(raw)
            values.append(struct.unpack("<%d%s" % (length, _ARRAYS[kind]), raw))
        elif kind in (b"S", b"R"):
            size = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            values.append(data[pos:pos + size])
            pos += size
        else:
            raise ValueError("unknown FBX property type %r" % kind)
    return values


def read_key_times(path):
    """Every bone T/R/S curve's key times in seconds, one list a curve; None when `path` is not a
    binary FBX that can be read (an ASCII file, a missing one, a broken one)."""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except (IOError, OSError):
        return None
    if not data.startswith(MAGIC) or len(data) < 27:
        return None
    try:
        return _bone_key_times(data)
    except (struct.error, ValueError, IndexError, zlib.error):
        return None


def _bone_key_times(data):
    wide = struct.unpack_from("<I", data, 23)[0] >= 7500
    models, curve_nodes, keys = set(), set(), {}
    links = []
    for name, first, count, kids, stop in _records(data, 27, len(data), wide):
        if name == b"Objects":
            for kind, first2, count2, kids2, stop2 in _records(data, kids, stop, wide):
                if kind == b"Model":
                    models.add(_properties(data, first2, 1)[0])
                elif kind == b"AnimationCurveNode":
                    curve_nodes.add(_properties(data, first2, 1)[0])
                elif kind == b"AnimationCurve":
                    curve = _properties(data, first2, 1)[0]
                    for field, first3, count3, _kids3, _stop3 in _records(data, kids2, stop2, wide):
                        if field == b"KeyTime":
                            keys[curve] = _properties(data, first3, count3)[0]
        elif name == b"Connections":
            for kind, first2, count2, _kids2, _stop2 in _records(data, kids, stop, wide):
                if kind == b"C":
                    links.append(_properties(data, first2, count2))
    # curve --> curve node --(Lcl channel)--> model
    up = {}
    for link in links:
        if len(link) >= 3:
            up.setdefault(link[1], []).append((link[2], link[3] if len(link) > 3 else b""))
    bone_nodes = set()
    for node in curve_nodes:
        for parent, channel in up.get(node, ()):
            if parent in models and channel in CHANNELS:
                bone_nodes.add(node)
    out = []
    for curve, times in keys.items():
        if any(parent in bone_nodes for parent, _channel in up.get(curve, ())):
            out.append([t / TICKS for t in times])
    return out


# ---------------------------------------------------------------------------
# pure
# ---------------------------------------------------------------------------

def key_rate(curves):
    """The rate the keys were baked at: one over the commonest step between two keys. None when
    no curve has two keys."""
    steps = {}
    for times in curves or ():
        for a, b in zip(times, times[1:]):
            step = round(b - a, 7)
            if step > 0:
                steps[step] = steps.get(step, 0) + 1
    if not steps:
        return None
    step = max(steps, key=lambda s: (steps[s], -s))
    return round(1.0 / step, 3)


def _inside(seconds, fps, start, end):
    frame = seconds * fps
    return start - TOLERANCE <= frame <= end + TOLERANCE


def bake_problem(curves, fps, start=None, end=None):
    """"" when every bone key lies on the scene's frame grid and the densest curve has a key on
    every frame, else what was wrong ("keys every 1/24 s, the scene is 30 fps"). Pure.

    Both halves are needed: latched at 24 in a 30 scene the keys leave the grid, but latched at 15
    every key lands on a 30 frame and half the frames are missing.

    Given the exported range (frames), only the keys inside it are looked at: keys past it are
    `outside_range`'s to tell (2026-10-28: a bone's own keys at 64 and 65 after a 0..62 bake left
    a hole the check read as a latched plugin)."""
    if not fps or not curves:
        return ""
    fps = float(fps)
    if start is not None and end is not None:
        curves = [[t for t in times if _inside(t, fps, start, end)] for times in curves]
    densest = max(curves, key=len)
    if len(densest) < 2:
        return ""
    off_grid = any(abs(t * fps - round(t * fps)) > TOLERANCE for times in curves for t in times)
    gaps = any(abs((b - a) * fps - 1.0) > TOLERANCE for a, b in zip(densest, densest[1:]))
    if not off_grid and not gaps:
        return ""
    rate = key_rate(curves)
    return "keys every 1/{0:g} s, the scene is {1:g} fps".format(rate or 0, fps)


def outside_range(curves, fps, start, end):
    """"" when every bone key lies inside frames `start`..`end`, else what reached the file past
    them ("24 keys at frames 64 to 65, outside 0-62"). Pure."""
    if not fps or not curves:
        return ""
    fps = float(fps)
    out = [round(t * fps, 3) for times in curves for t in times if not _inside(t, fps, start, end)]
    if not out:
        return ""
    return "{0} key{1} at frames {2:g} to {3:g}, outside {4:g}-{5:g}".format(
        len(out), "" if len(out) == 1 else "s", min(out), max(out), start, end)
