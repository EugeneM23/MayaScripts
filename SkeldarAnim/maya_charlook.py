"""The Characters card's portrait grid as data (2026-09-30).

The animator: «переделаем наше меню на сетку с портретами (как меню выбора
героев в Mortal Kombat или Dota 2)». Square head-and-shoulders portraits, one
per model, the kind a [Rig | Skeleton] switch. This module says how many
columns a width holds, where each tile is, what a point is and what the lines
say; `maya_chargrid` paints what it says. Stdlib only, like maya_hubstyle and
maya_invlook, so every decision is tested without Qt.

Sizes are LOGICAL px; `grid` multiplies by the display scale (trap 98: Qt
pixels are physical here).

Spec: docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md
"""

import math

import maya_hubstyle

CELL_MIN = 72           # a portrait is at least this wide ...
CELL_MAX = 120          # ... and at most this
GAP = 6
NAME_H = 18             # the name strip under a portrait
RADIUS = 6              # a tile's corners: the hub's well radius
GHOST = 88              # the portrait riding the cursor
THROTTLE_MS = 33        # the drag's caption is re-read at most this often
DOT = "·"

PALETTE = maya_hubstyle.TOKENS


def grid(width, count, scale=1.0):
    """(columns, cell, rects, height) for `count` tiles in `width` physical
    px: as many columns of at least CELL_MIN as fit, never more than `count`,
    each tile a square of at most CELL_MAX, left-aligned, rows wrapping. The
    rects are the squares; the height includes the name strips. A width of 0
    (not laid out yet) is one row at the minimum. Pure."""
    if count <= 0:
        return (0, 0, [], 0)
    k = float(scale or 1.0)
    gap, low, high, name = GAP * k, CELL_MIN * k, CELL_MAX * k, NAME_H * k
    width = float(width or 0)
    if width <= 0:
        cols, cell = count, low
    else:
        cols = max(1, min(count, int((width + gap) // (low + gap))))
        cell = max(1.0, min(high, (width - gap * (cols - 1)) / cols))
    rows = int(math.ceil(count / float(cols)))
    rects = []
    for index in range(count):
        row, col = divmod(index, cols)
        rects.append((int(round(col * (cell + gap))),
                      int(round(row * (cell + name + gap))),
                      int(round(cell)), int(round(cell))))
    height = int(round(rows * (cell + name) + (rows - 1) * gap))
    return cols, int(round(cell)), rects, height


def name_rect(rect, scale=1.0):
    """The name strip under a portrait's square."""
    x, y, w, h = rect
    return (x, y + h, w, int(round(NAME_H * float(scale or 1.0))))


def tile_rect(rect, scale=1.0):
    """The square and its name strip: what a press on the tile covers."""
    x, y, w, h = rect
    return (x, y, w, h + int(round(NAME_H * float(scale or 1.0))))


def hit(rects, x, y, scale=1.0):
    """The index of the tile under (x, y), or None. Pure."""
    for index, rect in enumerate(rects):
        rx, ry, rw, rh = tile_rect(rect, scale)
        if rx <= x < rx + rw and ry <= y < ry + rh:
            return index
    return None


def state(model, kind, selected, kinds):
    """How a tile is drawn: "selected", "selected_absent" (picked, but the
    switch names a kind it lacks), "absent" (dimmed, not pickable) or
    "available". Pure."""
    present = kind in (kinds or ())
    if model == selected:
        return "selected" if present else "selected_absent"
    return "available" if present else "absent"


def place_caption(label, point):
    """What a release would do: «Manny [rig] · floor (120, -36)»."""
    return "{0} {1} floor ({2}, {3})".format(label, DOT, int(round(point[0])),
                                             int(round(point[2])))


def absent_text(model_label, kind):
    """The refusal when the picked model has no row of the chosen kind."""
    other = "Skeleton" if kind == "rig" else "Rig"
    return "{0} has no {1} - pick {2}, or another portrait".format(
        model_label, kind, other)


def import_text(label):
    """What the line says while a portrait is picked."""
    return ("{0} - press Import, or drag the portrait into a "
            "viewport".format(label))


def tag_text(kind):
    """The pill on a dimmed portrait."""
    return "no " + kind


OPEN_SCENE = "Open scene"


def open_absent_text(kind):
    """The right button's row on a dimmed portrait, disabled: why it cannot
    open a file (2026-09-30)."""
    return "{0} ({1})".format(OPEN_SCENE, tag_text(kind))


def dragged(start, now, threshold):
    """Whether a held press has travelled far enough to be a drag (Qt's own
    measure: the manhattan length)."""
    return abs(now[0] - start[0]) + abs(now[1] - start[1]) >= threshold
