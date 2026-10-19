"""The Time Bar's layer panel, laid out (2026-10-18): pure functions of sizes and rows.
Stdlib and `look` only (a test pins it). Rects are (x, y, w, h); every length is
logical px x `ui`.

Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md
"""

from . import look

ROW_H = 30          # a layer's row
ROW_GAP = 3
HEAD_H = 30         # the segments and the lanes button
FOOT_H = 28         # + Layer and the icon buttons
STATUS_H = 16       # the column's own line
PAD = 6             # inside the column
WELL_PAD = 3        # inside the list's well
GRIP_H = 9          # the top edge you drag
MIN_H = 150         # the least height (logical px)
DEFAULT_H = 268
ABOVE = 6           # between the column and the strip's top
SIDE = 6            # between the column and the timeline, and the strip's right
TOP_ROOM = 10       # left free under the viewport's top
TABS = ("anim", "disp")
TAB_LABELS = {"anim": "Animation", "disp": "Display"}
FOOT = {"anim": ("add", "addsel", "remsel", "merge", "delete"),
        "disp": ("add", "addsel", "remsel", "select", "delete")}
FOOT_TIPS = {"add": "A new layer from the selection (empty with nothing selected)",
             "addsel": "Add the selection to the layer",
             "remsel": "Take the selection out of the layer",
             "merge": "Merge the selected layers (Ctrl-click to pick several); one picked: into the one under it",
             "select": "Select the layer's objects",
             "delete": "Delete the layer"}
TYPES = ("", "T", "R")      # displayType 0 normal, 1 template, 2 reference
MODES = {"add": "ADD", "ovr": "OVR", "base": "BASE"}


def clamp_height(h, room):
    """The column's height: at least MIN_H, at most `room` less TOP_ROOM."""
    return max(MIN_H, min(float(h), float(room) - TOP_ROOM))


def column_rect(strip, timeline, height, ui):
    """Global (x, y, w, h) of the column: from the timeline's right plus SIDE to the
    strip's right less SIDE, its bottom ABOVE over the strip's top."""
    sx, sy, sw, _sh = strip
    tx, _ty, tw, _th = timeline
    x = tx + tw + SIDE * ui
    w = sx + sw - SIDE * ui - x
    return (x, sy - ABOVE * ui - height, w, height)


def lanes_rect(column, timeline):
    """Global (x, y, w, h) of the lanes: from the timeline's left to the column's left."""
    cx, cy, _cw, ch = column
    return (timeline[0], cy, cx - timeline[0], ch)


def _inside(rect, x, y):
    return rect[0] <= x < rect[0] + rect[2] and rect[1] <= y < rect[1] + rect[3]


class Layout(object):
    """Where everything of the column stands, in the column's own coordinates."""

    def __init__(self, width, height, rows, tab, ui):
        self.width, self.height, self.tab, self.ui = float(width), float(height), tab, float(ui)
        u, w, h = self.ui, self.width, self.height
        self.grip = (0.0, 0.0, w, GRIP_H * u)
        self.head = (PAD * u, 8 * u, w - 2 * PAD * u, HEAD_H * u - 8 * u)
        seg_w = 92 * u
        y = self.head[1]
        self.segments = {"anim": (PAD * u, y, seg_w, 24 * u),
                         "disp": (PAD * u + seg_w + 2 * u, y, seg_w * 0.85, 24 * u)}
        self.lanes = (w - PAD * u - 28 * u, y, 28 * u, 24 * u)
        foot_top = h - PAD * u - STATUS_H * u - FOOT_H * u
        self.well = (PAD * u, HEAD_H * u + 4 * u, w - 2 * PAD * u, foot_top - HEAD_H * u - 8 * u)
        wx, wy, ww, wh = self.well
        pitch = (ROW_H + ROW_GAP) * u
        self.rows = [(wx + WELL_PAD * u, wy + WELL_PAD * u + i * pitch, ww - 2 * WELL_PAD * u, ROW_H * u)
                     for i in range(len(rows))]
        self.bases = [bool(r.get("base")) for r in rows]
        self.content_h = len(rows) * pitch - ROW_GAP * u + 2 * WELL_PAD * u if rows else 0.0
        self.max_scroll = max(0.0, self.content_h - wh)
        names = FOOT.get(tab, FOOT["anim"])
        add_w = 76 * u
        icon = 28 * u
        fy = foot_top + 2 * u
        self.foot = [(names[0], (PAD * u, fy, add_w, 24 * u))]
        x = w - PAD * u - icon * (len(names) - 1) - 2 * u * (len(names) - 2)
        for name in names[1:]:
            self.foot.append((name, (x, fy, icon, 24 * u)))
            x += icon + 2 * u
        self.status = (PAD * u, h - PAD * u - STATUS_H * u, w - 2 * PAD * u, STATUS_H * u)

    def row_at(self, i, scroll):
        x, y, w, h = self.rows[i]
        return (x, y - scroll, w, h)


def row_parts(rect, tab, ui, base=False):
    """name -> rect of a row's controls, left to right."""
    x, y, w, h = rect
    u = ui
    cy = y + (h - 20 * u) / 2.0
    out = {}
    right = x + w - 6 * u
    if tab == "anim":
        for name in ("lock", "solo", "mute"):
            if not (base and name == "solo"):
                out[name] = (right - 20 * u, cy, 20 * u, 20 * u)
            right -= 22 * u
        if not base:
            out["wnum"] = (right - 30 * u, y, 30 * u, h)
            right -= 34 * u
            out["weight"] = (right - 60 * u, y + (h - 14 * u) / 2.0, 60 * u, 14 * u)
            right -= 64 * u
        out["mode"] = (x + 7 * u, y + (h - 16 * u) / 2.0, 32 * u, 16 * u)
        name_x = x + 45 * u
    else:
        for name in ("type", "playback", "visible"):
            width = 24 * u if name == "type" else 20 * u
            out[name] = (right - width, cy, width, 20 * u)
            right -= width + 2 * u
        out["swatch"] = (x + 9 * u, y + (h - 14 * u) / 2.0, 14 * u, 14 * u)
        name_x = x + 31 * u
    out["name"] = (name_x, y, max(0.0, right - 4 * u - name_x), h)
    return out


def hit(layout, x, y, scroll):
    """What is under (x, y): ("grip",), ("tab", t), ("lanes",), ("foot", name),
    ("row", i, part), or None. A row with no control under the point is ("row", i, "name")."""
    if _inside(layout.grip, x, y):
        return ("grip",)
    for tab, rect in layout.segments.items():
        if _inside(rect, x, y):
            return ("tab", tab)
    if _inside(layout.lanes, x, y):
        return ("lanes",)
    for name, rect in layout.foot:
        if _inside(rect, x, y):
            return ("foot", name)
    if _inside(layout.well, x, y):
        for i in range(len(layout.rows)):
            rect = layout.row_at(i, scroll)
            if _inside(rect, x, y):
                base = layout.bases[i]
                for part, prect in row_parts(rect, layout.tab, layout.ui, base=base).items():
                    if part != "name" and _inside(prect, x, y):
                        return ("row", i, part)
                return ("row", i, "name")
    return None


def weight_at(x, rect):
    return max(0.0, min(1.0, (x - rect[0]) / float(rect[2]))) if rect[2] > 0 else 0.0


def dimmed(row, rows):
    """A muted layer, or one left out by another's solo (BaseAnimation never is)."""
    if row.get("mute"):
        return True
    if row.get("base"):
        return False
    return any(r.get("solo") for r in rows) and not row.get("solo")


def step_type(t):
    return (int(t) + 1) % len(TYPES)


def signature(rows):
    return tuple(tuple(sorted(r.items())) for r in rows)


def schedule(parts, origin, ui):
    """(open delay, fold delay) of each part rect: in nearest the origin first,
    out farthest first (the Time Bar's burst, a vertical step counting 1.5)."""
    out = []
    for x, y, w, h in parts:
        dx, dy = x + w / 2.0 - origin[0], y + h / 2.0 - origin[1]
        d = abs(dx) + abs(dy) * 1.5
        out.append((look.burst_delay(dx, dy, ui), look.fold_delay(d, ui)))
    return out


# -- the lanes as a dope sheet (2026-10-19) ---------------------------------------------

def lane_at(layout, y, scroll):
    """The row index whose lane is under `y` (the lanes share the column's rows), or None."""
    wx, wy, ww, wh = layout.well
    if not (wy <= y < wy + wh):
        return None
    for i in range(len(layout.rows)):
        r = layout.row_at(i, scroll)
        if r[1] <= y < r[1] + r[3] + ROW_GAP * layout.ui:
            return i
    return None


def lanes_between(i, j):
    """The rows a shift-drag from lane `i` to lane `j` sweeps, top first."""
    lo, hi = (i, j) if i <= j else (j, i)
    return list(range(lo, hi + 1))


def selection_after(selected, clicked, anchor, ctrl, shift, names):
    """Maya's Layer Editor selection after a click on `clicked`: alone, toggled
    (Ctrl) or the range from `anchor` (Shift, order of `names`). Answers
    (selected names in `names`' order, active)."""
    selected = [n for n in names if n in set(selected)]
    if shift and anchor in names:
        i, j = names.index(anchor), names.index(clicked)
        lo, hi = min(i, j), max(i, j)
        picked = set(names[lo:hi + 1])
        if ctrl:
            picked |= set(selected)
        return [n for n in names if n in picked], clicked
    if ctrl:
        if clicked in selected:
            rest = [n for n in selected if n != clicked]
            return rest, (rest[-1] if rest else None)
        return [n for n in names if n in set(selected) | {clicked}], clicked
    return [clicked], clicked
