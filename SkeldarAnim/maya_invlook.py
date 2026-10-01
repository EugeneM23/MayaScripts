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

And since 2026-10-01, the evening («для wepon раздела уберем функционал
сетчатого инвентаря ... перемещать по сетке не нужно. Пусть все будет
конссистентно»), the grid is gone: under the hands stand TILES, the
portraits' and the armor's own geometry (`maya_charlook.grid`) - one square
per catalog row, its name under it. Nothing is rearranged, sorted or
remembered any more.

Everything is in LOGICAL px; the panel multiplies by the display scale
(trap 98 - Qt pixels are physical here).
"""

import os

import maya_charlook
import maya_hubstyle

#  The hand cards' proportions follow the card's width as the grid's cell
#  did (2026-09-30, tuned to the animator's 360 px dock, trap 117): a UNIT
#  of a tenth of the width, between these.
UNIT = 40
MIN_UNIT = 24
UNITS = 10

PAD = 4                   # inside a card
GAP = 8                   # between the hands and the tiles
HAND_GAP = 6              # between the two hands
HAND_MAX = 230            # a hand card's width at most (a wide classic hub)
NAME_H = 20               # "Right hand" over a card
ROW_H = 19                # one channel row
ROW_GAP = 3               # between a row's name and its value
TURN = 45                 # degrees an icon is turned to lie across its tile
GHOST = maya_charlook.GHOST

# The grip as Maya's Channel Box shows a transform: translate, then rotate.
CHANNELS = ("tx", "ty", "tz", "rx", "ry", "rz")
NICE = {"tx": "Translate X", "ty": "Translate Y", "tz": "Translate Z",
        "rx": "Rotate X", "ry": "Rotate Y", "rz": "Rotate Z"}

PALETTE = maya_hubstyle.TOKENS
RADIUS = {"card": 8, "well": 6, "item": 4}      # the hub stylesheet's corners

# The right button's row on a weapon (2026-09-30).
OPEN_SCENE = "Open scene"
WORN_TEXT = "equipped"    # the pill on a weapon the character holds (Armor's)

_HERE = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------ icons

def icons_dir():
    return os.path.join(_HERE, "assets", "weapon_icons")


def icon_path(key):
    return os.path.join(icons_dir(), key + ".png")


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

def panel(width, count):
    """{name: rect} in logical px for a card `width` wide holding `count`
    weapons: the two hand cards side by side - the right hand on the
    viewer's LEFT, as the character faces you (the picker's convention) -
    each with its name on top, its channel column (a row per CHANNELS) and,
    right of it, its well; under them "tiles", a list of the weapons'
    squares (`maya_charlook.grid`), and "tilesarea" round them. Pure."""
    width = int(width)
    unit = int(max(MIN_UNIT, min(UNIT, (width - 2 * PAD) // UNITS)))
    well_w = int(max(32, min(56, round(1.2 * unit))))
    hand_w = int(max(0, min(HAND_MAX, (width - HAND_GAP) // 2)))
    left = max(0, (width - (2 * hand_w + HAND_GAP)) // 2)
    body_h = len(CHANNELS) * ROW_H
    hand_h = NAME_H + body_h + PAD
    rects = {}
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
    y = hand_h + GAP
    _cols, _cell, squares, height = maya_charlook.grid(width, count, 1.0)
    rects["tiles"] = [(x, y + ty, w, h) for x, ty, w, h in squares]
    rects["tilesarea"] = (0, y, width, height)
    rects["panel"] = (0, 0, width, y + height)
    return rects


def scaled(rects, scale):
    """The same rects in physical px (the tiles' list too)."""
    out = {}
    for name, rect in rects.items():
        if name == "tiles":
            out[name] = [tuple(int(round(v * scale)) for v in r) for r in rect]
        else:
            out[name] = tuple(int(round(v * scale)) for v in rect)
    return out


def inside(rect, x, y):
    rx, ry, rw, rh = rect
    return rx <= x < rx + rw and ry <= y < ry + rh


def hit(rects, keys, x, y, scale=1.0):
    """What the point is: ("slot", side) anywhere on a hand's card,
    ("tile", key) on a weapon's tile or its name, ("tiles",) elsewhere among
    the tiles, or None. Pure."""
    for side in ("R", "L"):
        if inside(rects["hand_" + side], x, y):
            return ("slot", side)
    index = maya_charlook.hit(rects["tiles"], x, y, scale)
    if index is not None and index < len(keys):
        return ("tile", keys[index])
    if inside(rects["tilesarea"], x, y):
        return ("tiles",)
    return None


def worn(holding):
    """The keys the character holds - in a hand or on the floor - the tiles'
    «equipped» pills. `holding` is {side: equip.Holding}. Pure."""
    return set(h.key for h in (holding or {}).values()
               if h is not None and getattr(h, "where", "") in ("hand", "floor")
               and getattr(h, "key", ""))
