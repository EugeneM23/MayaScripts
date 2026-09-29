"""The weapon inventory's look as data (2026-09-29): Diablo's bronze and
parchment, the cells, where each weapon sits, what a point in the window is.

The animator's ask: «инвентарь похожий на инвентарь как в игре diablo», and
look A of the two mocked up (dark bronze, a gold serif title, the grid) over
the hub's own style. Stdlib only, like maya_hubstyle: the window paints what
this module says, and every decision here is tested without Qt.

Everything is in LOGICAL px; the window multiplies by the display scale
(trap 98 - Qt pixels are physical here).
"""

import json
import os

CELL = 40                 # one inventory cell
COLS, ROWS = 10, 5        # the grid: the catalog, every row always there
SLOT = (2, 4)             # a hand slot, in cells
MARGIN = 14
TITLE_H = 34
NAME_H = 18
STATUS_H = 34
GAP = 12
ICON_PX = 80              # an icon's pixels per cell (twice CELL, for 150 %)

PALETTE = {
    "ground": "#16110c",      # the window
    "frame": "#7a5a2e",       # the bronze frame
    "frame_hi": "#b08a3c",
    "frame_lo": "#3a2a14",
    "cell": "#0d0a07",        # a cell's floor
    "cell_line": "#3a2c18",
    "gold": "#d8b36a",        # the title
    "parchment": "#a08a64",   # names, labels, the status
    "dim": "#7d6a4a",
    "valid": "#4f8f45",       # a slot a drag may land on
    "invalid": "#8a2f24",
    "hover": "#1f2a3a",       # the item under the mouse (Diablo's blue)
    "ghost_text": "#e8d6a8",
}
TITLE_FONTS = ("Palatino Linotype", "Book Antiqua", "Georgia", "serif")

_HERE = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------ icons

def icons_dir():
    return os.path.join(_HERE, "assets", "weapon_icons")


def icon_path(key):
    return os.path.join(icons_dir(), key + ".png")


def load_cells():
    """{key: (w, h)} from the icons' JSON, {} without it."""
    path = os.path.join(icons_dir(), "weapon_icons.json")
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError):
        return {}
    return dict((key, tuple(value["cells"])) for key, value in data.items())


def item_cells(length):
    """A weapon's cells from its model's length in cm: one wide, 2..5 tall
    (Dagger 2, Creep Sword 3, Long Sword 4, the spears 5)."""
    height = int(round(2 + (float(length) - 45.0) / 55.0))
    return (1, max(2, min(5, height)))


# ------------------------------------------------------------------ grid

def pack(items, cols=COLS, rows=ROWS):
    """{key: (col, row)} for [(key, (w, h))]: column by column, first fit,
    in the given order; what fits nowhere is left out. Pure."""
    taken = set()
    placed = {}
    for key, (w, h) in items:
        spot = None
        for col in range(cols - w + 1):
            for row in range(rows - h + 1):
                cells = set((col + i, row + j) for i in range(w)
                            for j in range(h))
                if not cells & taken:
                    spot = (col, row, cells)
                    break
            if spot:
                break
        if spot:
            placed[key] = (spot[0], spot[1])
            taken |= spot[2]
    return placed


def layout():
    """{name: (x, y, w, h)} in logical px: window, title, close, name, the
    two hand slots (the right hand on the viewer's LEFT, as the character
    faces you - the picker's convention), grid, status."""
    grid_w, grid_h = COLS * CELL, ROWS * CELL
    width = grid_w + 2 * MARGIN
    slot_w, slot_h = SLOT[0] * CELL, SLOT[1] * CELL
    y = MARGIN
    rects = {"title": (MARGIN, y, grid_w, TITLE_H),
             "close": (MARGIN + grid_w - 24, y + 5, 24, 24)}
    y += TITLE_H
    rects["name"] = (MARGIN, y, grid_w, NAME_H)
    y += NAME_H + GAP // 2
    middle = MARGIN + grid_w // 2
    rects["slot_R"] = (middle - CELL - slot_w, y, slot_w, slot_h)
    rects["slot_L"] = (middle + CELL, y, slot_w, slot_h)
    y += slot_h + GAP
    rects["grid"] = (MARGIN, y, grid_w, grid_h)
    y += grid_h + GAP // 2
    rects["status"] = (MARGIN, y, grid_w, STATUS_H)
    y += STATUS_H + MARGIN
    rects["window"] = (0, 0, width, y)
    return rects


def scaled(rects, scale):
    """The same rects in physical px."""
    return dict((name, tuple(int(round(v * scale)) for v in rect))
                for name, rect in rects.items())


def inside(rect, x, y):
    rx, ry, rw, rh = rect
    return rx <= x < rx + rw and ry <= y < ry + rh


def item_rect(rects, placement, cells, cell=CELL):
    """The rect an item at (col, row) of (w, h) cells covers in the grid."""
    gx, gy = rects["grid"][:2]
    col, row = placement
    w, h = cells
    return (gx + col * cell, gy + row * cell, w * cell, h * cell)


def hit(rects, placements, cells, x, y, cell=CELL):
    """What the point is: ("close",), ("slot", side), ("item", key),
    ("grid",), ("title",) or None. Pure."""
    if inside(rects["close"], x, y):
        return ("close",)
    for side in ("R", "L"):
        if inside(rects["slot_" + side], x, y):
            return ("slot", side)
    if inside(rects["grid"], x, y):
        for key, spot in placements.items():
            if inside(item_rect(rects, spot, cells.get(key, (1, 3)), cell), x, y):
                return ("item", key)
        return ("grid",)
    if inside(rects["title"], x, y):
        return ("title",)
    return None
