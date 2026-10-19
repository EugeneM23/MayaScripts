"""maya_radial - the radial menu: hold a key, point at a slot, let go (2026-10-15).

Spec: docs/superpowers/specs/2026-10-15-radial-menu-design.md. The animator: «я зажимаю какую-то
клавишу появляется радиальное меню ... В само меню можно поместить как и раздел так и отдельную
функцию раздела ... Если это двухэтапная кнопка например AIM то у нас на экране появится попап
финиша действия». Asked: hold and release (a click works too), alt+q, an editor card, eight slots.

- `press()` / `release()` are the hotkey rows `radial.press` / `radial.release`. The press puts the
  menu up under the cursor; which keys were down at that moment are watched by a 16 ms timer, and
  the moment they are all up is the release - Maya's release command may never come (the key let go
  over another window) or come early (auto-repeat), so it only acts when the keys really are up.
- The overlay is a frameless, see-through Qt.Tool window over the whole screen the cursor is on
  (alpha 1 everywhere, so a click anywhere lands on it), never taking focus.
- A section opens its window by the cursor (`maya_hubpop.open_at`); a function runs through
  `maya_hotkeys.run`; a two-step function that is left waiting gets the Finish popup.
- `build_panel()` is the hub's Radial Menu card, the editor of the slots and of how many there are
  (2..12, eight by default; 2026-10-16: «возможность указывать количество разделов»).

Qt is imported lazily through maya_hubqt. The state lives on `sys` (trap 111).
"""

import sys
import time
import traceback

import maya.cmds as cmds

import maya_hubstyle as hubstyle
import maya_radial_rules as rules

HUB_SECTION = "radial"
KEY_LABEL = "alt+q"
KEY = ("q", {"altModifier": True})

SLOT_BTN = "skeldarRadialSlot{0}"
SLOT_ROW = "skeldarRadialSlotRow{0}"
SLOT_DIR = "skeldarRadialSlotDir{0}"
COUNT_MENU = "skeldarRadialCount"
STATUS = "skeldarRadialStatus"

TICK_MS = 16
FINISH_POLL_MS = 300

# The icon of a function, by its row's key prefix (the section's own icon for a section).
_COMMAND_ICONS = (
    ("tools.", "tool"), ("tailbuilder.", "wave-sine"), ("walk.", "walk"),
    ("camshake.", "video"), ("connections.", "hand-grab"), ("scene.", "user"),
    ("graph.", "chart-line"), ("retarget.", "arrows-exchange"), ("time.", "clock"),
    ("editor.", "picture-in-picture"), ("window.", "picture-in-picture"),
)


def _state():
    st = getattr(sys, "_skeldar_radial", None)
    if st is None:
        st = {"menu": None, "finish": None}
        sys._skeldar_radial = st
    st.setdefault("leaving", None)     # a menu playing its close (2026-10-16)
    return st


def animated():
    """The menu moves (⋮ -> Interface animations), else it is up and gone at once."""
    try:
        import maya_hubmotion
        return bool(maya_hubmotion.enabled())
    except Exception:                                        # noqa: BLE001
        return True


def _now_ms():
    return time.perf_counter() * 1000.0


# ------------------------------------------------------------------ the slots

def slots():
    """Every remembered item, rules.MAX_SLOTS of them (rules.decode of the optionVar); the menu
    shows the first `count()`."""
    text = cmds.optionVar(query=rules.SLOTS_VAR) \
        if cmds.optionVar(exists=rules.SLOTS_VAR) else ""
    return rules.decode(text if isinstance(text, str) else "")


def count():
    """How many slots the menu shows (rules.SLOTS when never set)."""
    if not cmds.optionVar(exists=rules.COUNT_VAR):
        return rules.SLOTS
    return rules.clamp_count(cmds.optionVar(query=rules.COUNT_VAR))


def set_count(value):
    value = rules.clamp_count(value)
    cmds.optionVar(intValue=(rules.COUNT_VAR, value))
    return value


def set_slots(items):
    cmds.optionVar(stringValue=(rules.SLOTS_VAR, rules.encode(items)))


def set_slot(index, item):
    items = list(slots())
    items[index] = item or ""
    set_slots(items)


def _hub():
    import maya_hub
    return maya_hub


def _hotkeys():
    import maya_hotkeys
    return maya_hotkeys


def sections():
    """[(key, label, icon)] of every section of the hub."""
    return [(s.key, s.label, s.icon) for s in _hub().SECTIONS
            if s.key != HUB_SECTION]


def functions():
    """[(category, [(row key, label)])] of our hotkey rows a slot may hold: not the openers (a
    section is the opener) and not the menu's own key, in the table's order."""
    groups = []
    index = {}
    for key, category, label, _note, _action in _hotkeys().COMMANDS:
        if key.startswith(("window.", "radial.")):
            continue
        name = category.split(".", 1)[-1]
        if name not in index:
            index[name] = []
            groups.append((name, index[name]))
        index[name].append((key, label))
    return groups


def item_label(item):
    """What a slot reads ("" for an empty one, the item itself when it names nothing we know)."""
    kind, key = rules.parse(item)
    if kind == "section":
        sec = _hub().section(key)
        return sec.label if sec is not None else key
    if kind == "cmd":
        row = _hotkeys().row(key)
        return row[2] if row is not None else key
    return ""


def item_icon(item):
    kind, key = rules.parse(item)
    if kind == "section":
        sec = _hub().section(key)
        return sec.icon if sec is not None else "picture-in-picture"
    if kind == "cmd":
        for prefix, icon in _COMMAND_ICONS:
            if key.startswith(prefix):
                return icon
        return "chevron-right"
    return None


def waiting(row_key):
    """True while the two-step function `row_key` waits for its Finish."""
    entry = rules.TWO_STEP.get(row_key)
    if entry is None:
        return False
    module_name, func, _label = entry
    try:
        import importlib
        return bool(getattr(importlib.import_module(module_name), func)())
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return False


def slot_text(item):
    """A slot's label in the menu: «Finish Aim» while its tool waits."""
    kind, key = rules.parse(item)
    label = item_label(item)
    if kind == "cmd" and key in rules.TWO_STEP and waiting(key):
        return rules.finish_label(rules.TWO_STEP[key][2])
    return label


# -------------------------------------------------------------- keys (Win32)

_SKIP_VK = set([0x01, 0x02, 0x04, 0x05, 0x06, 0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2,
                0xA3, 0xA4, 0xA5, 0x5B, 0x5C, 0x14, 0x90, 0x91, 0x15, 0x19])
VK_ESCAPE = 0x1B
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02


def _user32():
    try:
        import ctypes
        return ctypes.windll.user32
    except Exception:                                        # noqa: BLE001
        return None


def key_down(vk):
    user32 = _user32()
    if user32 is None:
        return False
    return bool(user32.GetAsyncKeyState(int(vk)) & 0x8000)


def keys_down():
    """The ordinary keys held now (not the mouse buttons, not the modifiers, not Esc)."""
    if _user32() is None:
        return []
    return [vk for vk in range(0x08, 0xFF)
            if vk not in _SKIP_VK and vk != VK_ESCAPE and key_down(vk)]


# --------------------------------------------------------------- the presses

def _qt():
    import maya_hubqt as hubqt
    return hubqt.qt() if hubqt.available() else None


def _report(message):
    try:
        cmds.inViewMessage(assistMessage=message, position="midCenterTop", fade=True)
    except Exception:                                        # noqa: BLE001
        pass
    return message


def is_up():
    menu = _state()["menu"]
    return menu is not None and menu.alive()


def press():
    """The menu's key went down: the menu under the cursor. Nothing while it is already up (the
    key's auto-repeat)."""
    if is_up():
        return ""
    q = _qt()
    if q is None:
        return _report("The radial menu needs Maya's Qt UI")
    drop_leaving()
    menu = Menu(q)
    _state()["menu"] = menu
    menu.show(keys_down())
    return ""


def release():
    """Maya's release command for the menu's key: acted on only when the held keys are really up
    (the timer would see it a tick later anyway)."""
    menu = _state()["menu"]
    if menu is None or not menu.alive():
        return ""
    if menu.keys and any(key_down(vk) for vk in menu.keys):
        return ""
    menu.released()
    return ""


def close_menu():
    """The menu goes: back into its centre when the animations are on, at once otherwise."""
    menu = _state()["menu"]
    _state()["menu"] = None
    if menu is not None:
        if menu.alive() and menu.animate:
            drop_leaving()
            _state()["leaving"] = menu
            menu.leave()
        else:
            menu.destroy()


def drop_leaving():
    """A menu still playing its close is gone at once (a new press, a reload)."""
    menu = _state()["leaving"]
    _state()["leaving"] = None
    if menu is not None:
        menu.destroy()


def run_item(item, point):
    """Run a slot's item; `point` is the cursor's global (x, y)."""
    kind, key = rules.parse(item)
    if kind == "section":
        return _open_section(key, point)
    if kind == "cmd":
        return _run_command(key, point)
    return ""


def _open_section(key, point):
    hub = _hub()
    sec = hub.section(key)
    if sec is None:
        return _report("No section '{0}' - set this slot again".format(key))
    if sec.key in hub.HEADER_ONLY:
        return hub.show(sec.key)
    import maya_hubpop as hubpop
    try:
        popup = hubpop.open_at(sec.key, point)
    except Exception as error:                               # noqa: BLE001
        traceback.print_exc()
        return _report("{0}: {1}".format(sec.label, error))
    if popup is None:
        return hub.show(sec.key)
    return sec.label


def _run_command(key, point):
    hotkeys = _hotkeys()
    if hotkeys.row(key) is None:
        return _report("No function '{0}' - set this slot again".format(key))
    message = hotkeys.run(key)
    if key in rules.TWO_STEP and waiting(key):
        show_finish(key, point, message if isinstance(message, str) else "")
    return message


# --------------------------------------------------------------- the overlay

def _screen_rect(q, point):
    screen = q.QtGui.QGuiApplication.screenAt(q.QtCore.QPoint(*point)) \
        or q.QtGui.QGuiApplication.primaryScreen()
    return screen.geometry()


def _main_window(q):
    try:
        import maya.OpenMayaUI as omui
        ptr = omui.MQtUtil.mainWindow()
        if ptr:
            return q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
    except Exception:                                        # noqa: BLE001
        pass
    return None


def _scale():
    try:
        return float(cmds.mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
    except Exception:                                        # noqa: BLE001
        return 1.0


_CLASSES = {}


def _overlay_class(q):
    if "overlay" in _CLASSES:
        return _CLASSES["overlay"]
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets

    class Overlay(QtWidgets.QWidget):
        def __init__(self, menu, parent=None):
            super(Overlay, self).__init__(parent)
            self.menu = menu
            self.setObjectName("skeldarRadialMenu")
            self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint
                                | QtCore.Qt.WindowStaysOnTopHint
                                | QtCore.Qt.WindowDoesNotAcceptFocus
                                | QtCore.Qt.NoDropShadowWindowHint)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
            self.setMouseTracking(True)

        def paintEvent(self, _event):
            try:
                self.menu.paint(self)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()

        def mousePressEvent(self, event):
            try:
                self.menu.clicked(event.button() == QtCore.Qt.LeftButton)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()

        def mouseMoveEvent(self, _event):
            self.menu.tick()

    _CLASSES["overlay"] = Overlay
    return Overlay


class Menu(object):
    """The menu while it is up: the overlay, the held keys, the slot pointed at, and its motion
    (2026-10-16): `phase` is "open" (opening or up), "fired" (a chosen pill flashing) or
    "leaving" (going back into the centre)."""

    def __init__(self, q):
        self.q = q
        self.window = None
        self.timer = None
        self.keys = []
        self.mode = "hold"            # "hold" while the key is down, "click" after a tap
        self.hover = None
        self.count = count()
        self.items = slots()[:self.count]
        self.texts = [slot_text(item) for item in self.items]
        self.scale = _scale()
        self.centre = (0, 0)          # global
        self.origin = (0, 0)          # the window's global top-left
        self.last_cursor = None       # where the pointer line was last drawn to
        self.started = time.time()
        self.esc_was = False
        self._icons = {}
        self.animate = animated()
        self.phase = "open"
        self.opened_at = _now_ms()
        self.left_at = None           # when the close began
        self.fired = None             # the chosen slot while it flashes
        self.fired_at = None
        self.pending = None           # (item, point) to run when the flash ends
        self.lift = [0.0] * self.count
        self.ticked_at = self.opened_at

    def alive(self):
        if self.window is None:
            return False
        try:
            return bool(self.q.shiboken.isValid(self.window))
        except Exception:                                    # noqa: BLE001
            return False

    def show(self, keys):
        q = self.q
        pos = q.QtGui.QCursor.pos()
        self.centre = (pos.x(), pos.y())
        self.keys = list(keys)
        if not self.keys:
            self.mode = "click"       # a scripted call: no key to let go
        rect = _screen_rect(q, self.centre)
        self.origin = (rect.x(), rect.y())
        self.window = _overlay_class(q)(self, _main_window(q))
        self.window.setGeometry(rect)
        self.opened_at = self.ticked_at = _now_ms()
        self.window.show()
        self.window.raise_()
        self.esc_was = key_down(VK_ESCAPE)
        self.timer = q.QtCore.QTimer(self.window)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def px(self, value):
        return hubstyle.px(value, self.scale)

    def cursor(self):
        pos = self.q.QtGui.QCursor.pos()
        return (pos.x(), pos.y())

    def pointed(self):
        x, y = self.cursor()
        return rules.slot_at(x - self.centre[0], y - self.centre[1], self.px(rules.DEAD),
                             self.count)

    # ----------------------------------------------------------- the motion

    def elapsed(self, now=None):
        return (now if now is not None else _now_ms()) - self.opened_at

    def moving(self, now=None):
        """True while anything still has to be drawn again: the opening, a lift on its way."""
        if not self.animate:
            return False
        if self.phase != "open":
            return True
        if not rules.opened(self.elapsed(now), self.count):
            return True
        return any(abs(lift - (1.0 if i == self.hover else 0.0)) > 1e-6
                   for i, lift in enumerate(self.lift))

    def step_lift(self, dt_ms):
        for i in range(len(self.lift)):
            target = 1.0 if (i == self.hover and self.phase == "open") else 0.0
            self.lift[i] = target if not self.animate else \
                rules.approach(self.lift[i], target, dt_ms)

    def progress(self, index, now=None):
        """How far pill `index` is out of the centre now (0 at the centre, 1 in its place)."""
        if not self.animate:
            return 1.0
        now = now if now is not None else _now_ms()
        out = rules.item_open(self.elapsed(now), index, self.count)
        if self.phase == "leaving" and self.left_at is not None:
            out = min(out, rules.item_close(now - self.left_at, index, self.count))
        return out

    def ring(self, now=None):
        if not self.animate:
            return 1.0
        now = now if now is not None else _now_ms()
        grown = rules.ring_open(self.elapsed(now))
        if self.phase == "leaving" and self.left_at is not None:
            grown = min(grown, rules.ring_close(now - self.left_at, self.count))
        return grown

    def leave(self):
        """Back into the centre; destroyed when the close has played. Takes no clicks meanwhile
        (and paints no veil, so a click goes through to Maya)."""
        if self.phase == "leaving":
            return
        self.phase = "leaving"
        self.left_at = _now_ms()
        self.hover = None
        if self.alive():
            self.window.update()

    def tick(self):
        if not self.alive():
            return
        now = _now_ms()
        dt = max(0.0, now - self.ticked_at)
        self.ticked_at = now
        if self.phase == "leaving":
            self.step_lift(dt)
            if rules.closed(now - self.left_at, self.count):
                if _state()["leaving"] is self:
                    _state()["leaving"] = None
                self.destroy()
            else:
                self.window.update()
            return
        if self.phase == "fired":
            if now - self.fired_at >= rules.FLASH_MS:
                pending, self.pending = self.pending, None
                if _state()["menu"] is self:
                    close_menu()
                else:
                    self.leave()
                if pending is not None:
                    _run_later(self.q, *pending)
            else:
                self.window.update()
            return
        hover = self.pointed()
        cursor = self.cursor()
        changed = hover != self.hover or (hover is not None and cursor != self.last_cursor)
        self.hover = hover
        self.last_cursor = cursor
        was_moving = self.moving(now)
        self.step_lift(dt)
        # the pointer line follows the cursor, so a move inside one slot repaints too
        if changed or was_moving:
            self.window.update()
        esc = key_down(VK_ESCAPE)
        if esc and not self.esc_was:
            close_menu()
            return
        self.esc_was = esc
        if self.mode == "hold" and self.keys and not any(key_down(vk) for vk in self.keys):
            self.released()

    def released(self):
        """The key let go."""
        if not self.alive() or self.mode != "hold" or self.phase != "open":
            return
        slot = self.pointed()
        filled = slot is not None and bool(rules.parse(self.items[slot])[0])
        action = rules.release_action(slot, filled, time.time() - self.started)
        if action == rules.KEEP:
            self.mode = "click"
            self.window.update()
        elif action == rules.RUN:
            self.choose(slot)
        else:
            close_menu()

    def clicked(self, left):
        if self.phase != "open":
            return                    # flashing or going: it takes no clicks
        if not left:
            close_menu()
            return
        slot = self.pointed()
        if slot is not None and rules.parse(self.items[slot])[0]:
            self.choose(slot)
        else:
            close_menu()

    def choose(self, slot):
        item = self.items[slot]
        point = self.cursor()
        if not self.animate or not self.alive():
            close_menu()
            _run_later(self.q, item, point)
            return
        # the chosen pill flashes, then the menu goes back into its centre and the item runs
        self.phase = "fired"
        self.fired = slot
        self.fired_at = _now_ms()
        self.pending = (item, point)
        self.hover = None
        self.window.update()

    def destroy(self):
        if self.timer is not None:
            try:
                self.timer.stop()
            except Exception:                                # noqa: BLE001
                pass
        if self.alive():
            self.window.hide()
            self.window.deleteLater()
        self.window = None

    # ----------------------------------------------------------- painting

    def _icon(self, name, colour, size):
        key = (name, colour, size)
        if key not in self._icons:
            import maya_hubqt as hubqt
            self._icons[key] = hubqt.pixmap(name, colour, size)
        return self._icons[key]

    def _local(self, widget, point):
        """A global point in the overlay's own pixels, as the window really stands
        (a window placed off the asked rect, or another screen's scale, would put an
        origin subtraction somewhere beside the mouse)."""
        try:
            local = widget.mapFromGlobal(self.q.QtCore.QPoint(int(point[0]), int(point[1])))
            return float(local.x()), float(local.y())
        except Exception:                                    # noqa: BLE001
            return float(point[0] - self.origin[0]), float(point[1] - self.origin[1])

    def paint(self, widget, now=None, device=None):
        """Draw the menu on `widget` (or on `device`, an image of its size - a test)."""
        q = self.q
        QtCore, QtGui = q.QtCore, q.QtGui
        t = hubstyle.TOKENS
        now = now if now is not None else _now_ms()
        p = QtGui.QPainter(device if device is not None else widget)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        # alpha 1 everywhere: a click anywhere lands on the menu, not on the viewport under it -
        # but not once it goes, so a click while it closes reaches Maya
        if self.phase != "leaving":
            p.fillRect(widget.rect(), QtGui.QColor(0, 0, 0, 1))
        cx, cy = self._local(widget, self.centre)
        centre = QtCore.QPointF(cx, cy)
        grown = max(0.0, self.ring(now))
        ring_k = 0.2 + 0.8 * grown
        # the ring
        ring = self.px(rules.ring_radius(self.count))
        p.setOpacity(grown)
        pen = QtGui.QPen(QtGui.QColor(t["line"]))
        pen.setWidthF(self.px(1.5))
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawEllipse(centre, ring * ring_k, ring * ring_k)
        # the line toward the cursor, as lit as the pill it points at
        if self.hover is not None and self.phase == "open":
            lit = self.lift[self.hover] if self.animate else 1.0
            if lit > 0.0:
                x, y = self._local(widget, self.cursor())
                colour = QtGui.QColor(t["accent"])
                colour.setAlphaF(min(1.0, 0.25 + 0.75 * lit))
                pen = QtGui.QPen(colour)
                pen.setWidthF(self.px(2))
                p.setOpacity(1.0)
                p.setPen(pen)
                p.drawLine(centre, QtCore.QPointF(x, y))
        # the centre
        p.setOpacity(grown)
        dead = self.px(rules.DEAD) * ring_k
        p.setPen(QtGui.QPen(QtGui.QColor(t["line"]), self.px(1)))
        p.setBrush(QtGui.QColor(t["panel"]))
        p.drawEllipse(centre, dead, dead)
        p.setPen(QtGui.QColor(t["muted"] if self.mode == "hold" else t["accent_text"]))
        font = QtGui.QFont(widget.font())
        font.setPixelSize(int(self.px(10)))
        p.setFont(font)
        p.drawText(QtCore.QRectF(cx - dead, cy - dead, 2 * dead, 2 * dead),
                   QtCore.Qt.AlignCenter, "click" if self.mode == "click" else "")
        # the pills, the lit one last so its glow lies over its neighbours
        font.setPixelSize(int(self.px(12)))
        font.setBold(False)
        metrics = QtGui.QFontMetrics(font)
        order = list(range(len(self.items)))
        for top in (self.fired, self.hover):
            if top is not None and top in order:
                order.remove(top)
                order.append(top)
        for i in order:
            self._paint_pill(p, i, cx, cy, ring, font, metrics, now)
        p.end()

    def _paint_pill(self, p, i, cx, cy, ring, font, metrics, now):
        q = self.q
        QtCore, QtGui = q.QtCore, q.QtGui
        t = hubstyle.TOKENS
        place, size, opacity = rules.pose(self.progress(i, now))
        if opacity <= 0.0:
            return
        dx, dy = rules.slot_position(i, ring, self.count)
        text = self.texts[i]
        lift = self.lift[i] if self.animate else (1.0 if i == self.hover else 0.0)
        fired = i == self.fired
        p.setOpacity(opacity)
        if not text:
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(t["faint"] if lift > 0.5 else t["line"]))
            r = self.px(4) * size * rules.lifted_scale(lift)
            p.drawEllipse(QtCore.QPointF(cx + dx * place, cy + dy * place), r, r)
            return
        finish = text.startswith("Finish ")
        icon_px = int(self.px(16))
        h = self.px(30)
        w = metrics.horizontalAdvance(text) + icon_px + self.px(26)
        # the pill's own centre in its place, then carried out of the menu's centre
        fx = cx + dx - w * rules.pill_anchor(i, self.count) + w / 2.0
        fy = cy + dy
        x = cx + (fx - cx) * place
        y = cy + (fy - cy) * place
        k = size * rules.lifted_scale(lift)
        p.save()
        p.translate(x, y)
        p.scale(k, k)
        rect = QtCore.QRectF(-w / 2.0, -h / 2.0, w, h)
        flash = 0.0
        if fired and self.fired_at is not None:
            flash = 1.0 - rules.ease_out((now - self.fired_at) / float(rules.FLASH_MS))
        if fired:
            bg, fg, edge = QtGui.QColor(t["accent"]), t["on_accent"], t["accent"]
        else:
            bg = _mix(QtGui, t["card"], t["card_active"], lift)
            fg = t["accent_text"] if finish else t["text"]
            edge = t["accent"] if (finish or lift > 0.0) else t["line"]
        # the glow: rings of the accent fading outward
        glow = max(lift, flash if fired else 0.0)
        if glow > 0.0:
            p.setBrush(QtCore.Qt.NoBrush)
            spread = self.px(10) * (1.6 if fired else 1.0)
            rings = 6
            for j in range(rings, 0, -1):
                grow = spread * j / float(rings)
                colour = QtGui.QColor(t["accent"])
                colour.setAlphaF(0.22 * glow * (1.0 - j / float(rings + 1)))
                pen = QtGui.QPen(colour)
                pen.setWidthF(spread / rings + 0.5)
                p.setPen(pen)
                p.drawRoundedRect(rect.adjusted(-grow, -grow, grow, grow),
                                  h / 2.0 + grow, h / 2.0 + grow)
        width = self.px(1) + self.px(1) * (lift if not fired else 1.0)
        pen = QtGui.QPen(QtGui.QColor(edge))
        pen.setWidthF(width)
        p.setPen(pen)
        p.setBrush(bg)
        p.drawRoundedRect(rect, h / 2.0, h / 2.0)
        name = item_icon(self.items[i])
        left = rect.left() + self.px(10)
        if name:
            colour = fg if fired else (t["accent_text"] if lift > 0.5 else t["muted"])
            p.drawPixmap(int(round(left)), int(round(-icon_px / 2.0)),
                         self._icon(name, colour, icon_px))
        p.setPen(QtGui.QColor(fg if not (lift > 0.5 and not fired) else "#ffffff"))
        p.setFont(font)
        p.drawText(QtCore.QRectF(left + icon_px + self.px(6), rect.top(), w, h),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text)
        p.restore()


def _mix(QtGui, a, b, k):
    """Colour `a` toward `b` by `k` (0..1)."""
    ca, cb = QtGui.QColor(a), QtGui.QColor(b)
    k = min(1.0, max(0.0, k))
    return QtGui.QColor(int(round(ca.red() + (cb.red() - ca.red()) * k)),
                        int(round(ca.green() + (cb.green() - ca.green()) * k)),
                        int(round(ca.blue() + (cb.blue() - ca.blue()) * k)))


def _run_later(q, item, point):
    """Run a chosen item once the event loop turns (the menu's own press is over)."""
    def later():
        try:
            run_item(item, point)
        except Exception as error:                           # noqa: BLE001
            traceback.print_exc()
            _report("Radial menu: {0}".format(error))
    q.QtCore.QTimer.singleShot(0, later)


# --------------------------------------------------------- the finish popup

def close_finish():
    finish = _state()["finish"]
    _state()["finish"] = None
    if finish is not None:
        finish.destroy()


def show_finish(row_key, point, message=""):
    """The two-step function `row_key` waits: a small window by the cursor with Finish."""
    q = _qt()
    if q is None:
        return None
    close_finish()
    finish = Finish(q, row_key)
    _state()["finish"] = finish
    finish.show(point, message)
    return finish


class Finish(object):
    """«Aim waiting» + Finish + ✕, by the cursor; gone when nothing waits any more."""

    def __init__(self, q, row_key):
        self.q = q
        self.row = row_key
        self.window = None
        self.line = None
        self.timer = None
        self.grab = None

    def alive(self):
        if self.window is None:
            return False
        try:
            return bool(self.q.shiboken.isValid(self.window))
        except Exception:                                    # noqa: BLE001
            return False

    def show(self, point, message):
        q = self.q
        QtCore, QtWidgets = q.QtCore, q.QtWidgets
        t = hubstyle.TOKENS
        scale = _scale()
        px = lambda v: hubstyle.px(v, scale)                 # noqa: E731
        win = QtWidgets.QWidget(_main_window(q))
        win.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        outer = QtWidgets.QVBoxLayout(win)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QtWidgets.QFrame(win)
        card.setObjectName("skeldarRadialFinish")
        outer.addWidget(card)
        win.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint
                           | QtCore.Qt.WindowStaysOnTopHint
                           | QtCore.Qt.WindowDoesNotAcceptFocus)
        win.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        win.setStyleSheet(
            "QFrame#skeldarRadialFinish {{background: {card}; border: {b}px solid {accent};"
            " border-radius: {r}px;}}"
            "QLabel {{color: {text}; background: transparent;}}"
            "QLabel#skeldarRadialFinishLine {{color: {muted};}}"
            "QPushButton {{border-radius: {br}px; padding: {pv}px {ph}px;}}"
            "QPushButton#skeldarRadialFinishGo {{background: {accent}; color: {on};"
            " border: none; font-weight: bold;}}"
            "QPushButton#skeldarRadialFinishGo:hover {{background: {accent_hover};}}"
            "QPushButton#skeldarRadialFinishX {{background: transparent; color: {muted};"
            " border: none;}}"
            "QPushButton#skeldarRadialFinishX:hover {{color: {text};}}".format(
                card=t["card"], accent=t["accent"], accent_hover=t["accent_hover"],
                on=t["on_accent"], text=t["text"], muted=t["muted"],
                b=max(1, int(px(1))), r=int(px(8)), br=int(px(6)),
                pv=int(px(4)), ph=int(px(14))))
        column = QtWidgets.QVBoxLayout(card)
        m = int(px(10))
        column.setContentsMargins(m, int(px(6)), int(px(6)), m)
        column.setSpacing(int(px(6)))
        top = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("{0} waiting".format(rules.TWO_STEP[self.row][2]))
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        import maya_hubqt as hubqt
        close = QtWidgets.QPushButton()
        close.setObjectName("skeldarRadialFinishX")
        close.setIcon(hubqt.icon("x", t["muted"], int(px(14)), None))
        close.setIconSize(QtCore.QSize(int(px(14)), int(px(14))))
        close.setToolTip("Close - the tool keeps waiting (its card reads Finish)")
        close.clicked.connect(lambda *_: close_finish())
        top.addWidget(title, 1)
        top.addWidget(close)
        column.addLayout(top)
        self.line = QtWidgets.QLabel(message or "")
        self.line.setObjectName("skeldarRadialFinishLine")
        self.line.setWordWrap(True)
        self.line.setMaximumWidth(int(px(260)))
        self.line.setVisible(bool(message))
        column.addWidget(self.line)
        go = QtWidgets.QPushButton("Finish")
        go.setObjectName("skeldarRadialFinishGo")
        go.setToolTip("Press the tool again: the second step")
        go.clicked.connect(lambda *_: self.finish())
        column.addWidget(go)
        win.mousePressEvent = self._press
        win.mouseMoveEvent = self._move
        win.mouseReleaseEvent = lambda _e: setattr(self, "grab", None)
        self.window = win
        win.adjustSize()
        rect = _screen_rect(q, point)
        x = min(max(point[0] + int(px(16)), rect.x()), rect.right() - win.width())
        y = min(max(point[1] + int(px(12)), rect.y()), rect.bottom() - win.height())
        win.move(x, y)
        win.show()
        self.timer = QtCore.QTimer(win)
        self.timer.setInterval(FINISH_POLL_MS)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    def _press(self, event):
        pos = self.q.QtGui.QCursor.pos()
        self.grab = (pos.x() - self.window.x(), pos.y() - self.window.y())

    def _move(self, _event):
        if self.grab is None:
            return
        pos = self.q.QtGui.QCursor.pos()
        self.window.move(pos.x() - self.grab[0], pos.y() - self.grab[1])

    def finish(self):
        message = _hotkeys().run(self.row)
        if not waiting(self.row):
            close_finish()
            return message
        if self.alive() and isinstance(message, str) and message:
            self.line.setText(message)
            self.line.setVisible(True)
            self.window.adjustSize()
        return message

    def poll(self):
        if not waiting(self.row):
            close_finish()

    def destroy(self):
        if self.timer is not None:
            try:
                self.timer.stop()
            except Exception:                                # noqa: BLE001
                pass
        if self.alive():
            self.window.hide()
            self.window.deleteLater()
        self.window = None


# ------------------------------------------------------------- the editor

def _slot_name(index):
    return SLOT_BTN.format(index)


def status(message):
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=message)
        hubstyle.tell(STATUS, message)
    return message


def refresh(*_):
    """The count reads the optionVar; the first `count()` slot rows are shown, each its direction
    and its item; the rest are hidden (their items kept)."""
    n = count()
    if cmds.optionMenu(COUNT_MENU, exists=True):
        cmds.optionMenu(COUNT_MENU, edit=True, value=str(n))
    for i, item in enumerate(slots()):
        name = _slot_name(i)
        if not cmds.button(name, exists=True):
            continue
        shown = i < n
        if cmds.rowLayout(SLOT_ROW.format(i), exists=True):
            cmds.rowLayout(SLOT_ROW.format(i), edit=True, manage=shown)
        if not shown:
            continue
        where = rules.direction(i, n)
        if cmds.text(SLOT_DIR.format(i), exists=True):
            cmds.text(SLOT_DIR.format(i), edit=True, label=where)
        label = item_label(item) or "(empty)"
        cmds.button(name, edit=True, label=label,
                    annotation="{0}: {1} - click to choose, right click to clear".format(
                        where, label))


def _choose(index, item):
    set_slot(index, item)
    refresh()
    return status("{0}: {1}".format(rules.direction(index, count()),
                                     item_label(item) or "empty"))


def choose_count(value):
    """The count dropdown: how many slots the menu shows."""
    n = set_count(value)
    refresh()
    return status("{0} slots on the ring".format(n))


def _fill_menu(menu, index):
    """A slot's menu, built each time it opens: Empty, Sections, then a submenu per category."""
    cmds.popupMenu(menu, edit=True, deleteAllItems=True)
    cmds.menuItem(label="Empty", parent=menu,
                  command=lambda *_: _choose(index, ""))
    cmds.menuItem(divider=True, parent=menu)
    cmds.menuItem(label="Sections", subMenu=True, parent=menu)
    for key, label, _icon in sections():
        cmds.menuItem(label=label,
                      command=(lambda k: lambda *_: _choose(index, rules.section_item(k)))(key))
    cmds.setParent("..", menu=True)
    for category, rows in functions():
        cmds.menuItem(label=category, subMenu=True, parent=menu)
        for key, label in rows:
            cmds.menuItem(label=label,
                          command=(lambda k: lambda *_: _choose(index, rules.command_item(k)))(key))
        cmds.setParent("..", menu=True)


def reset_defaults():
    set_slots(rules.DEFAULTS)
    set_count(rules.SLOTS)
    refresh()
    return status("Eight slots, the defaults again")


def bind_key():
    """alt+q onto the menu in the CURRENT hotkey set - only when it is ours."""
    hotkeys = _hotkeys()
    if not hotkeys.is_active():
        return status("Turn the hotkey map on (the keyboard in the hub's header) - "
                      "{0} comes with it".format(KEY_LABEL))
    hotkeys.register()
    held = hotkeys.bind_row(KEY[0], KEY[1], "radial.press")
    note = " (it held {0})".format(held) if held else ""
    return status("{0} opens the radial menu{1}".format(KEY_LABEL, note))


def build_panel():
    """The card: a line on how it works, the count of slots, one row a slot (its direction, its
    item; the rows past the count hidden), Reset and Bind, the line."""
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(
        label="Hold {0} over a viewport, point at a slot, let go. A tap keeps it up for a "
              "click.".format(KEY_LABEL), align="left", wordWrap=True, height=36), "caption")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(hubstyle.pick(60, 70), 80),
                   columnAttach=[(1, "both", 0), (2, "both", 4)])
    cmds.text(label="Slots", align="left")
    cmds.optionMenu(COUNT_MENU, annotation="How many slots the ring holds (eight by default); "
                                           "slots past the count keep their items",
                    changeCommand=lambda value, *_: choose_count(value))
    for n in range(rules.MIN_SLOTS, rules.MAX_SLOTS + 1):
        cmds.menuItem(label=str(n))
    cmds.setParent("..")
    for index in range(rules.MAX_SLOTS):
        cmds.rowLayout(SLOT_ROW.format(index), numberOfColumns=2, adjustableColumn=2,
                       columnWidth2=(hubstyle.pick(60, 70), 80),
                       columnAttach=[(1, "both", 0), (2, "both", 4)])
        hubstyle.mark(cmds.text(SLOT_DIR.format(index), label="", align="left"), "caption")
        name = cmds.button(_slot_name(index), label="",
                           height=hubstyle.height("button", 26))
        hubstyle.mark(name, "secondary")
        menu = cmds.popupMenu(parent=name, button=1)
        cmds.popupMenu(menu, edit=True,
                       postMenuCommand=(lambda m, i: lambda *_: _fill_menu(m, i))(menu, index))
        clear = cmds.popupMenu(parent=name, button=3)
        cmds.menuItem(label="Clear", parent=clear,
                      command=(lambda i: lambda *_: _choose(i, ""))(index))
        cmds.setParent("..")
    row = cmds.rowLayout(numberOfColumns=2, columnAttach=[(1, "both", 0), (2, "both", 4)])
    hubstyle.mark(row, "fill", layout=True)
    hubstyle.mark(cmds.button(label="Reset to defaults", height=hubstyle.height("button", 26),
                              annotation="The slots the plugin ships with",
                              command=lambda *_: reset_defaults()), "secondary", "refresh")
    hubstyle.mark(cmds.button(label="Bind " + KEY_LABEL, height=hubstyle.height("button", 26),
                              annotation="Put the menu on {0} in the SkeldarAnim hotkey set "
                                         "(Hotkey Editor: SkeldarAnim > Radial Menu for any "
                                         "other key)".format(KEY_LABEL),
                              command=lambda *_: bind_key()), "secondary", "keyboard")
    cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=36), "status")
    cmds.setParent("..")
    refresh()
    return column


def is_open():
    return bool(cmds.text(STATUS, exists=True))


def show_window():
    import maya_hub
    return maya_hub.show(HUB_SECTION)

