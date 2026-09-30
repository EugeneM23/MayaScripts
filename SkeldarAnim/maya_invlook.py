"""The weapon inventory's look as data: the hub's colours, the cells, where
each weapon sits, where the hands and their channels stand, what a point in
the panel is.

Built 2026-09-29 in Diablo's bronze (the animator's «инвентарь похожий на
инвентарь как в игре diablo»); restyled 2026-09-30 in the hub's own look
(«дизайн инвентаря все же не в стиле диабло а в стиле нашего интерфейса»):
the palette IS `maya_hubstyle.TOKENS`, so the inventory can never drift from
the hub's colours - charcoal, rounded cards, one orange accent. Stdlib only,
like maya_hubstyle: the window paints what this module says, and every
decision here is tested without Qt.

Since 2026-09-30 the inventory IS the Weapons card («вместо того что
сейчас открывается наш сетчатый инвентарь с оружием, но не в отдельном окне
а как часть нашего меню»): `panel(width)` lays the two hands side by side,
each a column of its grip laid out like Maya's Channel Box LEFT of its well
(«слева от окошка столбик с параметрами так как в стандартном интерфейсе
маи в channel box»), and the grid under them, its cell following the card's
width. The window's own layout (title, close, name, status) is gone.

Everything is in LOGICAL px; the panel multiplies by the display scale
(trap 98 - Qt pixels are physical here).
"""

import json
import os

import maya_hubstyle

CELL = 40                 # one inventory cell at most (the window's)
MIN_CELL = 24             # ... and at least, in a narrow dock
COLS, ROWS = 10, 5        # the grid: the catalog, every row always there
ICON_PX = 80              # an icon's pixels per cell (twice CELL, for 150 %)

PAD = 4                   # inside a card
GAP = 8                   # between the hands and the grid
HAND_GAP = 6              # between the two hands
HAND_MAX = 230            # a hand card's width at most (a wide classic hub)
NAME_H = 20               # "Right hand" over a card
ROW_H = 19                # one channel row
ROW_GAP = 3               # between a row's name and its value

# The grip as Maya's Channel Box shows a transform: translate, then rotate.
CHANNELS = ("tx", "ty", "tz", "rx", "ry", "rz")
NICE = {"tx": "Translate X", "ty": "Translate Y", "tz": "Translate Z",
        "rx": "Rotate X", "ry": "Rotate Y", "rz": "Rotate Z"}

PALETTE = maya_hubstyle.TOKENS
RADIUS = {"card": 8, "well": 6, "item": 4}      # the hub stylesheet's corners

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

def pack(items, cols=COLS, rows=ROWS, taken=None):
    """{key: (col, row)} for [(key, (w, h))]: column by column, first fit,
    in the given order, around the cells already `taken`; what fits nowhere
    is left out. Pure."""
    taken = set(taken or ())
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


# --------------------------------------------------- rearranged by hand
#
# 2026-09-29, the animator: «можно было перетаскивать по инвентарю». An item
# dropped in the grid moves into free cells (its own old cells count as free),
# or SWAPS with the one item it lands on when that one fits where the first
# came from - the animator's pick over refusing and over Diablo 2's
# pick-up-the-other; anything else is "no room". The layout is remembered as
# a record and read back through `arrange`, which never loses an item.

def footprint(spot, size):
    """The cells an item of `size` covers at `spot`. Pure."""
    col, row = spot
    return set((col + i, row + j) for i in range(size[0]) for j in range(size[1]))


def clamp(spot, size, cols=COLS, rows=ROWS):
    """`spot` moved just far enough for the item to lie inside the grid."""
    return (max(0, min(cols - size[0], int(spot[0]))),
            max(0, min(rows - size[1], int(spot[1]))))


def _clear(placements, cells, cols, rows):
    """True when every item lies inside the grid and none overlaps another."""
    seen = set()
    for key, spot in placements.items():
        size = cells.get(key, (1, 3))
        if (spot[0] < 0 or spot[1] < 0 or spot[0] + size[0] > cols
                or spot[1] + size[1] > rows):
            return False
        mine = footprint(spot, size)
        if mine & seen:
            return False
        seen |= mine
    return True


def plan_move(placements, cells, key, spot, cols=COLS, rows=ROWS):
    """(kind, placements, other) for dropping `key` at `spot` (clamped into
    the grid): kind "move", "swap" (with `other`), "same", or None - refused,
    the placements as they were. Pure; the input is never changed."""
    size = cells.get(key, (1, 3))
    spot = clamp(spot, size, cols, rows)
    if placements.get(key) == spot:
        return ("same", dict(placements), None)
    wanted = footprint(spot, size)
    under = [other for other, where in placements.items()
             if other != key and footprint(where, cells.get(other, (1, 3))) & wanted]
    moved = dict(placements)
    moved[key] = spot
    if not under:
        return ("move", moved, None)
    if len(under) > 1:
        return (None, dict(placements), None)
    other = under[0]
    moved[other] = placements[key]
    if _clear(moved, cells, cols, rows):
        return ("swap", moved, other)
    return (None, dict(placements), other)


def arrange(items, stored, cols=COLS, rows=ROWS):
    """The placements for [(key, size)] from a remembered record: a stored
    spot kept (in item order) while it lies in the grid and overlaps nothing
    placed before it; everything else - a new catalog row, a stale or broken
    record - packed into the free cells. Pure."""
    placed, taken = {}, set()
    for key, size in items:
        try:
            spot = (int(stored[key][0]), int(stored[key][1]))
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        if (spot[0] < 0 or spot[1] < 0 or spot[0] + size[0] > cols
                or spot[1] + size[1] > rows):
            continue
        mine = footprint(spot, size)
        if mine & taken:
            continue
        placed[key] = spot
        taken |= mine
    placed.update(pack([(k, s) for k, s in items if k not in placed],
                       cols, rows, taken))
    return placed


def layout_record(placements):
    """The placements as the JSON the window remembers."""
    return json.dumps(dict((k, list(v)) for k, v in placements.items()),
                      sort_keys=True)


def read_record(text):
    """A remembered record back as {key: [col, row]}; {} for anything else."""
    try:
        data = json.loads(text or "")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------- channels

def channel_names(short):
    """{channel: the name its row shows}: the Channel Box's nice names, or its
    SHORT ones (tx ... rz) - its own option for a narrow box."""
    return dict((c, c if short else NICE[c]) for c in CHANNELS)


def channel_text(value):
    """A value as the Channel Box shows it: three decimals at most, trailing
    zeros dropped, never "-0". Pure."""
    text = ("%.3f" % float(value)).rstrip("0").rstrip(".")
    return "0" if text in ("-0", "", "-") else text


def parse_channel(text):
    """A typed value as a float (a comma is a decimal point too), or None."""
    try:
        return float((text or "").strip().replace(",", "."))
    except ValueError:
        return None


def split_row(width, nice_w, short_w, value_min, gap=ROW_GAP):
    """(short, name width, value width) for a channel row `width` wide: the
    nice names while a value of at least `value_min` still fits beside them,
    the short ones otherwise. Pure - the widths come from the font."""
    if width - nice_w - gap >= value_min:
        return False, nice_w, width - nice_w - gap
    return True, short_w, max(0, width - short_w - gap)


# ------------------------------------------------------------------- panel

def panel(width):
    """{name: (x, y, w, h)} in logical px for a card `width` wide, plus
    "cell" (an int): the two hand cards side by side - the right hand on the
    viewer's LEFT, as the character faces you (the picker's convention) -
    each with its name on top, its channel column (a row per CHANNELS) and,
    right of it, its well; under them the grid's card and the grid, ten
    cells of the width between MIN_CELL and CELL, centred. Pure."""
    width = int(width)
    cell = int(max(MIN_CELL, min(CELL, (width - 2 * PAD) // COLS)))
    well_w = int(max(32, min(56, round(1.2 * cell))))
    hand_w = int(max(0, min(HAND_MAX, (width - HAND_GAP) // 2)))
    left = max(0, (width - (2 * hand_w + HAND_GAP)) // 2)
    body_h = len(CHANNELS) * ROW_H
    hand_h = NAME_H + body_h + PAD
    rects = {"cell": cell}
    for side, x in (("R", left), ("L", left + hand_w + HAND_GAP)):
        rects["hand_" + side] = (x, 0, hand_w, hand_h)
        rects["name_" + side] = (x + PAD + 2, 0, max(0, hand_w - 2 * PAD - 2),
                                 NAME_H)
        well_x = x + hand_w - PAD - well_w
        rects["well_" + side] = (well_x, NAME_H, well_w, body_h)
        col_x = x + PAD
        col_w = max(0, well_x - ROW_GAP - col_x)
        rects["column_" + side] = (col_x, NAME_H, col_w, body_h)
        for index, channel in enumerate(CHANNELS):
            rects["row_%s_%s" % (side, channel)] = (
                col_x, NAME_H + index * ROW_H, col_w, ROW_H)
    grid_w, grid_h = COLS * cell, ROWS * cell
    gx = max(PAD, (width - grid_w) // 2)
    y = hand_h + GAP
    rects["gridcard"] = (gx - PAD, y, grid_w + 2 * PAD, grid_h + 2 * PAD)
    rects["grid"] = (gx, y + PAD, grid_w, grid_h)
    rects["panel"] = (0, 0, width, y + grid_h + 2 * PAD)
    return rects


def scaled(rects, scale):
    """The same rects in physical px (the "cell" too)."""
    out = {}
    for name, rect in rects.items():
        if isinstance(rect, (int, float)):
            out[name] = int(round(rect * scale))
        else:
            out[name] = tuple(int(round(v * scale)) for v in rect)
    return out


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
    """What the point is: ("slot", side) anywhere on a hand's card,
    ("item", key), ("grid",), or None. Pure."""
    for side in ("R", "L"):
        if inside(rects["hand_" + side], x, y):
            return ("slot", side)
    if inside(rects["grid"], x, y):
        for key, spot in placements.items():
            if inside(item_rect(rects, spot, cells.get(key, (1, 3)), cell), x, y):
                return ("item", key)
        return ("grid",)
    return None
