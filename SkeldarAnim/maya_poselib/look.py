"""The Pose Library window's look as data (2026-10-02).

The animator: «карточки с позами ... превью которое мы сами делаем из сцены ... поиск и
сортировка ... перетягивать наши карточки на персонажа драгом мышки». The window shows a grid
of thumbnail cards, drags one onto a character, and says what a release would do. This module
says how many columns a width holds, where each card is, what a point is, what the drag's
caption reads, and what the details panel and the status line say; `window.py` paints what it
says. Stdlib only and knowing no other module of the library, like `maya_charlook` and
`maya_invlook`, so every decision is tested without Qt or Maya.

Sizes are physical px. The constants are LOGICAL and every function multiplies them by `scale`
(`mayaDpiSetting -q -realScaleValue`; trap 98: Qt pixels are physical here), rounding each
size once so the grid, the hit test and the culling agree to the pixel.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md
"""

import math
import re

CELL_MIN = 72           # a card is at least this wide (the card-size slider's low end) ...
CELL_MAX = 200          # ... and at most this
CELL_DEFAULT = 112      # what the slider starts at
GAP = 8                 # between rows, and the least between columns
NAME_H = 34             # the strip under a card: its name and, under it, the character chip
GHOST = 96              # the thumbnail riding the cursor during a drag
THROTTLE_MS = 33        # the drag's caption is re-read at most this often
DOT = "·"          # the middle dot the plugin's captions separate with

OFF_WINDOW = "release off the window to apply"
NO_TARGET = "no target"


def _px(value, scale):
    """A logical size in physical px. The one rounding every function uses."""
    return int(round(value * float(scale or 1.0)))


def grid(width, count, cell, scale=1.0):
    """(columns, rects, height) for `count` cards in `width` physical px.

    A card is a square of `cell` (the slider's value, clamped to CELL_MIN..CELL_MAX) times
    `scale`, with a NAME_H strip under it; `rects` are the squares, `(x, y, w, h)`. As many
    columns as fit (n cards need n * cell + (n - 1) * GAP), never more than `count` and never
    fewer than one. The row is SPREAD over the columns that FIT: the cards keep the size the
    slider says and the extra width goes into the gaps between those columns, so the first
    card touches the left edge and the last card of a full row the right one. Because the
    spread is over the columns that fit and not over the cards there are, a card's x is a
    function of the width and its column alone: the cards already in the library do not move
    when another is saved, and a short row (fewer cards than fit) simply stops where its
    cards end, in the same places a full row would put them. A single column (only one fits)
    is centred; a pane narrower than a card shrinks the card rather than clip it; a width of
    0 (not laid out yet) is one column at the left. A short last row keeps the columns.
    `height` is every row with its name strip plus the gaps between rows. Pure."""
    k = float(scale or 1.0)
    gap, name = _px(GAP, k), _px(NAME_H, k)
    width = int(round(width or 0))
    side = max(1, _px(max(CELL_MIN, min(CELL_MAX, cell)), k))
    if width > 0:
        side = min(side, width)
        fit = (width + gap) // (side + gap)
    else:
        fit = 1
    cols = max(1, min(count, fit))
    if count <= 0:
        return cols, [], 0
    rows = int(math.ceil(count / float(cols)))
    rects = []
    for index in range(count):
        row, col = divmod(index, cols)
        if fit > 1:
            # Column c of the `fit` columns stands at c * (width - side) / (fit - 1), rounded
            # half up, in integers so no float or half-to-even rounding is involved. The step
            # between columns is at least side + gap (fit columns fit, so width - side >=
            # (fit - 1) * (side + gap)) and floor(a + n) = floor(a) + n for a whole n, so
            # neighbouring columns stay at least side + gap apart; the last column lands on
            # width - side, the pane's right edge. A function of width and column only.
            x = (2 * col * (width - side) + (fit - 1)) // (2 * (fit - 1))
        else:
            x = max(0, (width - side) // 2)
        rects.append((x, row * (side + name + gap), side, side))
    return cols, rects, rows * (side + name) + (rows - 1) * gap


def name_rect(rect, scale=1.0):
    """The name strip under a card's square."""
    x, y, w, h = rect
    return (x, y + h, w, _px(NAME_H, scale))


def tile_rect(rect, scale=1.0):
    """The square and its name strip: what a press on the card covers."""
    x, y, w, h = rect
    return (x, y, w, h + _px(NAME_H, scale))


def visible(rects, top, bottom, scale=1.0):
    """The indexes of the cards whose tile (square and name strip) intersects the vertical
    span [top, bottom] - what a scrolled viewport must paint, so hundreds of cards cost what
    the screen holds. A card touching the span only at an edge is not in it. Pure."""
    strip = _px(NAME_H, scale)
    return [index for index, (_x, y, _w, h) in enumerate(rects)
            if y < bottom and y + h + strip > top]


def hit(rects, x, y, scale=1.0):
    """The index of the card under (x, y), or None: the square and its name strip, the gaps
    between cards nothing. Pure."""
    for index, rect in enumerate(rects):
        rx, ry, rw, rh = tile_rect(rect, scale)
        if rx <= x < rx + rw and ry <= y < ry + rh:
            return index
    return None


def drop_caption(name, aim):
    """(text, good): what the ghost says over `aim` while the card `name` is dragged. `good`
    is whether a release there does something. The aim is the window's own reading of the
    point under the cursor:

        {"kind": "character", "label"}         onto a character standing in a viewport
        {"kind": "floor", "label", "point"}    an empty floor: the card's source is added
                                               there (`label` its catalog row, `point` the
                                               world point, x and z shown)
        {"kind": "folder", "folder"}           a folder of the tree: the card moves
        {"kind": "window"}                     over the window itself: nothing
        {"kind": "none", "text"}               nothing to apply to, and why

    Anything else reads «no target». Pure."""
    aim = aim or {}
    kind = aim.get("kind")
    name = name or "Pose"
    if kind == "character":
        return "%s %s onto %s" % (name, DOT, aim.get("label") or "the character"), True
    if kind == "floor":
        text = "%s %s a new %s" % (name, DOT, aim.get("label") or "character")
        point = aim.get("point")
        if point is not None:
            text += " %s floor (%d, %d)" % (DOT, int(round(point[0])), int(round(point[-1])))
        return text, True
    if kind == "folder":
        return "%s %s move to %s" % (name, DOT, aim.get("folder") or "Library"), True
    if kind == "window":
        return OFF_WINDOW, False
    if kind == "none":
        return aim.get("text") or NO_TARGET, False
    return NO_TARGET, False


def _num(value, places=3):
    """A number as the status line prints it: at most `places` decimals, no trailing zeros
    («12.0» is «12», «0.003» stays), never «-0»."""
    text = ("%.*f" % (places, float(value))).rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _counted(count, noun):
    """«3 bones», «1 bone»: `noun` is given in the plural."""
    if count == 1 and noun.endswith("s"):
        noun = noun[:-1]
    return "%s %s" % (_num(count), noun)


def _field(data, card, key, default=""):
    """`key` from the pose file when it holds one, else from the card (the listing's copy)."""
    value = data.get(key)
    if value in (None, ""):
        value = getattr(card, key, default)
    return default if value is None else value


def _when(created):
    """«2026-10-02T18:00:00» as «2026-10-02 18:00»; anything that is not an ISO stamp as it
    stands."""
    text = str(created or "")
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", text):
        return text[:16].replace("T", " ")
    return text


def details(card, data):
    """The lines of the details panel for `card` (a `store.Card`) and `data` (its `pose.json`,
    or None before it is read - the card's listing stands in). Lines that would be empty are
    left out:

        Manny [rig]
        3 bones · Hand L, Arm L            (an objects pose: «2 objects»)
        Eugene · 2026-10-02 18:00
        frame 12 · shot_010.ma

    Pure."""
    data = data if isinstance(data, dict) else {}
    if card is None and not data:
        return []
    if (data.get("kind") or getattr(card, "kind", "")) == "objects":
        label = "Objects"
        objects = data.get("objects")
        count = len(objects) if objects is not None else getattr(card, "count", 0)
        second = _counted(count, "objects")
    else:
        label = (data.get("character") or {}).get("label") or getattr(card, "label", "")
        members = data.get("members")
        count = len(members) if members is not None else getattr(card, "count", 0)
        regions = data.get("regions")
        if regions is None:
            regions = getattr(card, "regions", [])
        second = _counted(count, "bones")
        if regions:
            second += " %s %s" % (DOT, ", ".join(regions))
    who = [part for part in (_field(data, card, "author"), _when(_field(data, card, "created")))
           if part]
    frame, scene = data.get("frame"), data.get("scene") or ""
    where = []
    if isinstance(frame, (int, float)):
        where.append("frame " + _num(frame))
    if scene:
        where.append(str(scene).replace("\\", "/").rsplit("/", 1)[-1])
    return [line for line in (label, second, (" %s " % DOT).join(who),
                              (" %s " % DOT).join(where)) if line]


def status_line(applied):
    """The status line after an apply, from the summary of one target (or a list of them, one
    per character, joined with « | »):

        {"name": "Fist", "target": "Manny_Rig1", "count": 23, "noun": "controls",
         "layer": "AnimLayer1", "frame": 12.0, "worst": 0.003, "worst_unit": "deg",
         "notes": ["the FK forearm twist is lost on arm_r (31 deg)"]}

    reads «Fist onto Manny_Rig1: 23 controls keyed on AnimLayer1 at frame 12 - worst 0.003 deg |
    the FK forearm twist is lost on arm_r (31 deg)». Everything but `name` and `target` may be
    missing and is then left out of the sentence; `noun` is given in the plural (default
    «channels»), `worst_unit` defaults to «deg», a worst too small to print reads «<0.001».
    Pure."""
    if isinstance(applied, (list, tuple)):
        return " | ".join(text for text in (status_line(one) for one in applied) if text)
    if not applied:
        return ""
    name, target = applied.get("name") or "Pose", applied.get("target")
    text = ("%s onto %s" % (name, target)) if target else name
    count = applied.get("count")
    if count is None:
        text += ": applied"
    else:
        text += ": %s keyed" % _counted(count, applied.get("noun") or "channels")
    if applied.get("layer"):
        text += " on %s" % applied["layer"]
    if applied.get("frame") is not None:
        text += " at frame %s" % _num(applied["frame"])
    worst = applied.get("worst")
    if worst is not None:
        shown = "<0.001" if 0 < worst < 0.001 else _num(worst)
        text += " - worst %s %s" % (shown, applied.get("worst_unit") or "deg")
    return " | ".join([text] + [note for note in applied.get("notes") or [] if note])
