"""Several animations in a square: where each clip's rig stands. Pure, stdlib only.

2026-10-01, the animator: «если мы нажали add new rig или перетянули в пустое
место на сцене то давай мы создадим все наши анимации в линию с некоторым
шагом что бы они не пересекались» - about the scene's zero for the button,
about the pointed point for a drag. Asked, the step is 2.5 m WIDENED where a
clip's root travels: the gap to a neighbour grows by exactly how far each of
the two wanders toward the other, so their root paths stay a whole step apart
and still clips stand evenly. The same evening, «всегда располагать наши
анимации в квадратной формации в не зависимости от угла камеры»: a square on
the world's axes - `grid_shape` columns along +X, rows from the front (+Z)
back, each column's and each row's band (the union of its clips' reach) a
whole step from the next.

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


COLUMNS = (1.0, 0.0, 0.0)     # a row runs left to right along world X
ROWS = (0.0, 0.0, -1.0)       # the rows go from the front (+Z) back


def grid_shape(count):
    """(columns, rows) of the squarest grid holding `count` clips."""
    if count < 1:
        return (0, 0)
    columns = int(math.ceil(math.sqrt(count)))
    return (columns, int(math.ceil(count / float(columns))))


def band(extents):
    """The union of several (lo, hi) reaches."""
    if not extents:
        return (0.0, 0.0)
    return (min(lo for lo, _hi in extents), max(hi for _lo, hi in extents))


def square_offsets(x_extents, z_extents, step=STEP):
    """(along COLUMNS, along ROWS) for each clip in a square: clip i in column
    i % columns, row i // columns; `x_extents` are the clips' reach along
    COLUMNS, `z_extents` along ROWS. Each column (row) is a band - the union
    of its clips' reach - a whole step from the next, the square centred."""
    count = len(x_extents)
    columns, rows = grid_shape(count)
    if not count:
        return []
    cells = [(i % columns, i // columns) for i in range(count)]
    column_off = offsets([band([x_extents[i] for i, (c, _r) in enumerate(cells)
                                if c == column]) for column in range(columns)], step)
    row_off = offsets([band([z_extents[i] for i, (_c, r) in enumerate(cells)
                             if r == row]) for row in range(rows)], step)
    return [(column_off[c], row_off[r]) for c, r in cells]


def square_slots(centre, x_extents, z_extents, step=STEP):
    """The world points of `square_offsets` about `centre` (its height kept)."""
    return [(centre[0] + COLUMNS[0] * xo + ROWS[0] * zo, centre[1],
             centre[2] + COLUMNS[2] * xo + ROWS[2] * zo)
            for xo, zo in square_offsets(x_extents, z_extents, step)]


def widened(names, *extent_lists, **kwargs):
    """The clips whose root leaves its start by more than `wander` along any
    of the axes the `extent_lists` were measured on."""
    wander = kwargs.get("wander", WANDER)
    return [name for index, name in enumerate(names)
            if any(lists[index][0] < -wander or lists[index][1] > wander
                   for lists in extent_lists)]


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
