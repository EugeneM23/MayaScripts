"""Several animations in a line: where each clip's rig stands. Pure, stdlib only.

2026-10-01, the animator: «если мы нажали add new rig или перетянули в пустое
место на сцене то давай мы создадим все наши анимации в линию с некоторым
шагом что бы они не пересекались» - about the scene's zero for the button,
about the pointed point for a drag. Asked, the step is 2.5 m WIDENED where a
clip's root travels sideways: the gap to a neighbour grows by exactly how far
each of the two wanders toward the other, so their root paths stay a whole
step apart and still clips stand evenly.

A slot is where the rig's Main (a skeleton's root) stands at its clip's first
frame; a track is the clip's root positions over its frames.

Spec: docs/superpowers/specs/2026-10-01-uebridge-many-animations-design.md
"""

import math

STEP = 250.0        # cm between two clips that stand still
WANDER = 1.0        # cm: a root that leaves its start sideways by more widens its gaps
SAMPLES = 240       # at most this many frames of a clip are read


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def side_extent(track, axis):
    """(lo, hi), lo <= 0 <= hi: how far the track leaves its first point along
    `axis`, either way."""
    if not track:
        return (0.0, 0.0)
    first = track[0]
    along = [_dot((p[0] - first[0], p[1] - first[1], p[2] - first[2]), axis)
             for p in track]
    return (min(0.0, min(along)), max(0.0, max(along)))


def offsets(extents, step=STEP):
    """Each clip's place along the line: slot i + 1 stands `step + hi_i -
    lo_(i+1)` past slot i, and the first and last are equidistant from 0."""
    if not extents:
        return []
    out = [0.0]
    for i in range(1, len(extents)):
        out.append(out[-1] + step + extents[i - 1][1] - extents[i][0])
    middle = (out[0] + out[-1]) / 2.0
    return [value - middle for value in out]


def floor_axis(direction):
    """A horizontal unit vector from `direction` (the camera's right); world X
    when it has no horizontal part."""
    if not direction:
        return (1.0, 0.0, 0.0)
    x, z = float(direction[0]), float(direction[2])
    length = math.hypot(x, z)
    if length < 1e-6:
        return (1.0, 0.0, 0.0)
    return (x / length, 0.0, z / length)


def slots(centre, axis, offs):
    """The world points `offs` along `axis` from `centre` (its height kept)."""
    return [(centre[0] + axis[0] * o, centre[1], centre[2] + axis[2] * o)
            for o in offs]


def widened(names, extents, wander=WANDER):
    """The clips whose root leaves its start sideways by more than `wander`."""
    return [name for name, (lo, hi) in zip(names, extents)
            if lo < -wander or hi > wander]


def sample_frames(start, end, samples=SAMPLES):
    """The frames a clip's track is read at: every whole frame of a short
    clip, `samples` evenly over a long one, the start alone with no range."""
    if end is None or end <= start:
        return [float(start)]
    count = int(min(samples, math.floor(end - start) + 1))
    if count < 2:
        return [float(start), float(end)]
    step = (end - start) / float(count - 1)
    return [float(start) + i * step for i in range(count)]
