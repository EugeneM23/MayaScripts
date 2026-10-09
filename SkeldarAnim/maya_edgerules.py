"""maya_edgerules - the hub's edge panel as rules (stdlib only).

The animator (2026-10-08): «что бы наша полка получила возможность работать
как виджет ... когда я подношу мышку к левому краю экрана то появляется наша
полка когда убираю то полка скрывается». Asked: a switch in ⋮, waiting from
Maya's start, the full height of the screen, a 📌 pin. Since 2026-10-09 the
left OR the right edge (⋮ -> Edge panel ▸ Off / Left edge / Right edge).

Everything the panel decides is a function of plain values here; maya_hubedge
is the Qt that measures those values and moves the windows.

Spec: docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md,
docs/superpowers/specs/2026-10-09-edge-panel-side-design.md
"""

EDGE_VAR = "skeldarAnimHub_edge"
WIDTH_VAR = "skeldarAnimHub_edgeWidth"
WIDTH, MIN_WIDTH, MAX_WIDTH = 360, 280, 700     # logical px (the dock's 360)
#  The cursor must rest on the edge this long: thrown into the top-left
#  corner for File, or crossing into a monitor on the left, it does not.
DWELL_MS = 100
HIDE_MS = 350           # after the cursor left
RETRY_MS = 150          # a postponed hide asks again this often
#  Out: the panel's frame slides out (FRAME_MS) and the hub follows inside it
#  HUB_DELAY_MS after the frame began (IN_MS); back: the two together
#  (OUT_MS). 2026-10-09 («фоновая рамка ... появляется сильно резко ...
#  Скорость выезда панели можно замедлить на 50%»): the frame had popped up
#  whole; the hub is 1.5 x the first 180. The same day («уменьшим задержку
#  между выездами частей и увеличим скорость выезда фоновой подложки»): the
#  frame 150 instead of 270, the hub no longer waiting for it to finish.
FRAME_MS, HUB_DELAY_MS, IN_MS, OUT_MS = 150, 80, 270, 150
SENSOR_PX = 2           # physical px: the strip at the screen's edge
GRIP_PX = 5             # logical px: the width grip on the panel's inner side
#  2026-10-09 («Можем добавить опцию выбора стороны монитора откуда
#  выезжает наша полка?»): the left or the right edge, remembered. Every
#  quantity the controller keeps counts from the screen edge inward (the
#  slot's offset, the frame); the functions below turn them into the host's
#  own coordinates for a side.
SIDE_VAR = "skeldarAnimHub_edgeSide"
SIDES = ("left", "right")


def side_of(value):
    """A remembered or asked side: "right", else "left"."""
    return "right" if str(value or "").strip().lower() == "right" else "left"


def clamp_width(width):
    return int(max(MIN_WIDTH, min(MAX_WIDTH, int(round(width)))))


def panel_rect(work_area, width, scale, side="left"):
    """The panel in physical px: against the work area's `side` edge, its
    full height, `width` logical px wide (clamped, and never wider than the
    area)."""
    x, y, w, h = work_area
    pw = int(min(w, int(round(clamp_width(width) * float(scale or 1.0)))))
    if side_of(side) == "right":
        return (int(x + w - pw), int(y), pw, int(h))
    return (int(x), int(y), pw, int(h))


def sensor_rect(work_area, side="left"):
    x, y, w, h = work_area
    if side_of(side) == "right":
        return (int(x + w - SENSOR_PX), int(y), SENSOR_PX, int(h))
    return (int(x), int(y), SENSOR_PX, int(h))


def slot_x(offset, line, side="left"):
    """The slot's x inside the host at `offset` from the screen edge (-host
    width off it, 0 out). The slot is `line` px narrower than the host and
    leaves the line on the panel's inner side uncovered."""
    if side_of(side) == "right":
        return int(line - offset)
    return int(offset)


def offset_of(x, line, side="left"):
    """slot_x read back: the offset a slot standing at `x` has."""
    if side_of(side) == "right":
        return int(line - x)
    return int(x)


def frame_span(frame, host_w, side="left"):
    """(x, width) of the host showing when `frame` px of it are out."""
    if side_of(side) == "right":
        return (int(host_w - frame), int(frame))
    return (0, int(frame))


def line_x(frame, host_w, line, side="left"):
    """The line on the frame's inner edge, host-local x."""
    if side_of(side) == "right":
        return int(host_w - frame)
    return int(frame - line)


def grip_x(host_w, grip, side="left"):
    """The width grip on the host's inner side, host-local x."""
    if side_of(side) == "right":
        return 0
    return int(host_w - grip)


def dragged_width(width0, dx, scale, side="left"):
    """The logical width after the grip moved `dx` physical px: inward
    widens (to the right on the left edge, to the left on the right
    edge)."""
    step = float(dx) / float(scale or 1.0)
    if side_of(side) == "right":
        step = -step
    return width0 + step


def may_reveal(edge_on, shown, buttons, app_active):
    """The cursor at the edge may bring the panel out: edge mode on, the
    panel hidden, no mouse button held (a window or marquee dragged to the
    edge is not a request), Maya the active application."""
    return bool(edge_on and not shown and not buttons and app_active)


def hide_blockers(pinned=False, held=False, inside=False, buttons=False,
                  popup=False, modal=False, typing=False):
    """Why the panel must stay, in a fixed order (empty: it may go).

    pinned  the 📌 is on
    held    it was opened by a command and not yet visited (Hold)
    inside  the cursor is over it
    buttons a mouse button is down - a drag from the panel into the
            viewport would break if its source vanished
    popup   a dropdown's list, a menu is open
    modal   a dialog is up
    typing  a text field of the panel has the keyboard focus"""
    reasons = []
    for name, value in (("pinned", pinned), ("held", held),
                        ("inside", inside), ("buttons", buttons),
                        ("popup", popup), ("modal", modal),
                        ("typing", typing)):
        if value:
            reasons.append(name)
    return reasons


class Hold(object):
    """A reveal by command (the shelf button, a hotkey, a tool's
    show_window) holds the panel until the cursor has entered it and left,
    or a press lands outside it."""

    def __init__(self):
        self.held = False
        self.entered = False

    def start(self):
        self.held, self.entered = True, False

    def enter(self):
        if self.held:
            self.entered = True

    def leave(self):
        """True when this leave released the hold."""
        if self.held and self.entered:
            self.held = self.entered = False
            return True
        return False

    def press_outside(self):
        if self.held:
            self.held = self.entered = False
            return True
        return False


def slide_x(t, width, showing):
    """The panel's x inside its host at progress `t` (0..1): from -width to
    0 easing out while showing, from 0 to -width easing in while hiding."""
    t = max(0.0, min(1.0, float(t)))
    if showing:
        k = 1.0 - (1.0 - t) ** 3
        return int(round(-width * (1.0 - k)))
    k = t ** 3
    return int(round(-width * k))


def reveal_ms():
    """How long a reveal from rest takes: the hub's delay and its slide (the
    frame, quicker, is out before)."""
    return max(FRAME_MS, HUB_DELAY_MS + IN_MS)


def reveal_at(ms, width):
    """(frame, slot x) `ms` into a reveal from rest: the frame eases out over
    FRAME_MS; the hub eases in from -width over IN_MS, starting HUB_DELAY_MS
    after the frame. The frame, quicker and earlier, always leads."""
    ms = float(ms)
    frame = width + slide_x(ms / FRAME_MS, width, True)
    x = slide_x((ms - HUB_DELAY_MS) / IN_MS, width, True)
    return int(frame), int(x)


def contains(rect, point, margin=0):
    x, y, w, h = rect
    px, py = point
    return (x - margin <= px < x + w + margin
            and y - margin <= py < y + h + margin)
