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

#  The compact hub (2026-10-08, variant B): five tiles a row in a 338 px card
#  and the name drawn OVER the picture's bottom, on a shade - no strip under
#  the square. Was CELL_MIN 72, GAP 6 and an 18 px strip beneath.
CELL_MIN = 58           # a portrait is at least this wide ...
CELL_MAX = 120          # ... and at most this
GAP = 3
NAME_H = 16             # the name strip INSIDE the square's bottom
RADIUS = 6              # a tile's corners: the hub's well radius
GHOST = 88              # the portrait riding the cursor
THROTTLE_MS = 33        # the drag's caption is re-read at most this often
DOT = "·"

PALETTE = maya_hubstyle.TOKENS


def grid(width, count, scale=1.0):
    """(columns, cell, rects, height) for `count` tiles in `width` physical
    px: as many columns of at least CELL_MIN as fit, never more than `count`,
    each tile a square of at most CELL_MAX, left-aligned, rows wrapping. The
    rects are the squares, the name lies over each one's bottom (`name_rect`),
    so the height is the rows and the gaps between them and nothing else. A
    width of 0 (not laid out yet) is one row at the minimum. Pure."""
    if count <= 0:
        return (0, 0, [], 0)
    k = float(scale or 1.0)
    gap, low, high = GAP * k, CELL_MIN * k, CELL_MAX * k
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
                      int(round(row * (cell + gap))),
                      int(round(cell)), int(round(cell))))
    height = int(round(rows * cell + (rows - 1) * gap))
    return cols, int(round(cell)), rects, height


def name_rect(rect, scale=1.0):
    """The name strip over the bottom of a portrait's square: inside it, the
    last NAME_H px (2026-10-08; it was a strip under the square)."""
    x, y, w, h = rect
    strip = int(round(NAME_H * float(scale or 1.0)))
    return (x, y + h - strip, w, strip)


def tile_rect(rect, scale=1.0):
    """What a press on the tile covers: the square - the name is over it."""
    return rect


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


# The Auto card (2026-10-02): no character of its own - an import finds one.
AUTO_ADD = ("Auto brings no character of its own - Import Animation puts a clip on our "
            "character whose skeleton it is, else brings it in its own skeleton")


def auto_text(kind):
    """What the line says while the Auto card is picked."""
    return ("Auto [{0}] - Import Animation puts a clip on our {0} whose skeleton it is, "
            "else brings it in its own skeleton").format(kind)


OPEN_SCENE = "Open scene"


def open_absent_text(kind):
    """The right button's row on a dimmed portrait, disabled: why it cannot
    open a file (2026-09-30)."""
    return "{0} ({1})".format(OPEN_SCENE, tag_text(kind))


def dragged(start, now, threshold):
    """Whether a held press has travelled far enough to be a drag (Qt's own
    measure: the manhattan length)."""
    return abs(now[0] - start[0]) + abs(now[1] - start[1]) >= threshold
