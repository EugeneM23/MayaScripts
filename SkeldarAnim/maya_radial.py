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
- A section opens its popup by the cursor (`maya_hubpop.open_at`); a function runs through
  `maya_hotkeys.run`; a two-step function that is left waiting gets the Finish popup.
- `build_panel()` is the hub's Radial Menu card, the editor of the eight slots.

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
CENTRE_BTN = "skeldarRadialCentre"
STATUS = "skeldarRadialStatus"

TICK_MS = 16
FINISH_POLL_MS = 300

# Where the slots stand in the editor's three rows (the compass: NW N NE / W . E / SW S SE).
GRID = ((7, 0, 1), (6, None, 2), (5, 4, 3))

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
    return st


# ------------------------------------------------------------------ the slots

def slots():
    """The eight items (rules.decode of the optionVar)."""
    text = cmds.optionVar(query=rules.SLOTS_VAR) \
        if cmds.optionVar(exists=rules.SLOTS_VAR) else ""
    return rules.decode(text if isinstance(text, str) else "")


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
    menu = _state()["menu"]
    _state()["menu"] = None
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
    """The menu while it is up: the overlay, the held keys, the slot pointed at."""

    def __init__(self, q):
        self.q = q
        self.window = None
        self.timer = None
        self.keys = []
        self.mode = "hold"            # "hold" while the key is down, "click" after a tap
        self.hover = None
        self.items = slots()
        self.texts = [slot_text(item) for item in self.items]
        self.scale = _scale()
        self.centre = (0, 0)          # global
        self.origin = (0, 0)          # the window's global top-left
        self.started = time.time()
        self.esc_was = False
        self._icons = {}

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
        return rules.slot_at(x - self.centre[0], y - self.centre[1], self.px(rules.DEAD))

    def tick(self):
        if not self.alive():
            return
        hover = self.pointed()
        if hover != self.hover:
            self.hover = hover
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
        if not self.alive() or self.mode != "hold":
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
        close_menu()

        def later():
            try:
                run_item(item, point)
            except Exception as error:                       # noqa: BLE001
                traceback.print_exc()
                _report("Radial menu: {0}".format(error))
        self.q.QtCore.QTimer.singleShot(0, later)

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

    def paint(self, widget):
        q = self.q
        QtCore, QtGui = q.QtCore, q.QtGui
        t = hubstyle.TOKENS
        p = QtGui.QPainter(widget)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        # alpha 1 everywhere: a click anywhere lands on the menu, not on the viewport under it
        p.fillRect(widget.rect(), QtGui.QColor(0, 0, 0, 1))
        cx, cy = self.centre[0] - self.origin[0], self.centre[1] - self.origin[1]
        centre = QtCore.QPointF(cx, cy)
        # the ring
        ring = self.px(rules.RADIUS)
        pen = QtGui.QPen(QtGui.QColor(t["line"]))
        pen.setWidthF(self.px(1.5))
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawEllipse(centre, ring, ring)
        # the line toward the cursor
        x, y = self.cursor()
        if self.hover is not None:
            pen = QtGui.QPen(QtGui.QColor(t["accent"]))
            pen.setWidthF(self.px(2))
            p.setPen(pen)
            p.drawLine(centre, QtCore.QPointF(x - self.origin[0], y - self.origin[1]))
        # the centre
        dead = self.px(rules.DEAD)
        p.setPen(QtGui.QPen(QtGui.QColor(t["line"]), self.px(1)))
        p.setBrush(QtGui.QColor(t["panel"]))
        p.drawEllipse(centre, dead, dead)
        p.setPen(QtGui.QColor(t["muted"] if self.mode == "hold" else t["accent_text"]))
        font = QtGui.QFont(widget.font())
        font.setPixelSize(int(self.px(10)))
        p.setFont(font)
        p.drawText(QtCore.QRectF(cx - dead, cy - dead, 2 * dead, 2 * dead),
                   QtCore.Qt.AlignCenter, "click" if self.mode == "click" else "")
        # the pills
        font.setPixelSize(int(self.px(12)))
        font.setBold(False)
        metrics = QtGui.QFontMetrics(font)
        icon_px = int(self.px(16))
        h = self.px(30)
        for i, item in enumerate(self.items):
            dx, dy = rules.slot_position(i, ring)
            px_, py_ = cx + dx, cy + dy
            text = self.texts[i]
            lit = i == self.hover
            if not text:
                p.setPen(QtCore.Qt.NoPen)
                p.setBrush(QtGui.QColor(t["line"] if not lit else t["faint"]))
                p.drawEllipse(QtCore.QPointF(px_, py_), self.px(4), self.px(4))
                continue
            finish = text.startswith("Finish ")
            w = metrics.horizontalAdvance(text) + icon_px + self.px(26)
            rect = QtCore.QRectF(px_ - w * rules.pill_anchor(i), py_ - h / 2.0, w, h)
            if lit:
                bg, fg = QtGui.QColor(t["accent"]), t["on_accent"]
            else:
                bg, fg = QtGui.QColor(t["card"]), t["accent_text"] if finish else t["text"]
            p.setPen(QtGui.QPen(QtGui.QColor(t["accent"] if (lit or finish) else t["line"]),
                                self.px(1)))
            p.setBrush(bg)
            p.drawRoundedRect(rect, h / 2.0, h / 2.0)
            name = item_icon(self.items[i])
            left = rect.left() + self.px(10)
            if name:
                p.drawPixmap(int(left), int(py_ - icon_px / 2.0),
                             self._icon(name, fg if lit else t["muted"], icon_px))
            p.setPen(QtGui.QColor(fg))
            p.setFont(font)
            p.drawText(QtCore.QRectF(left + icon_px + self.px(6), rect.top(),
                                     w, h), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text)
        p.end()


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
    """Every slot button reads its item."""
    items = slots()
    for i, item in enumerate(items):
        name = _slot_name(i)
        if not cmds.button(name, exists=True):
            continue
        label = item_label(item) or "(empty)"
        cmds.button(name, edit=True, label=label,
                    annotation="{0}: {1} - click to choose, right click to clear".format(
                        rules.COMPASS[i], label))


def _choose(index, item):
    set_slot(index, item)
    refresh()
    return status("{0}: {1}".format(rules.COMPASS[index], item_label(item) or "empty"))


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
    refresh()
    return status("The eight slots are the defaults again")


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


def _fill_row():
    row = cmds.rowLayout(numberOfColumns=3,
                         columnAttach=[(1, "both", 0), (2, "both", 4), (3, "both", 4)])
    return hubstyle.mark(row, "fill", layout=True)


def build_panel():
    """The card: a line on how it works, the eight slots as a compass around the key, Reset and
    Bind, the line."""
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(
        label="Hold {0} over a viewport, point at a slot, let go. A tap keeps it up for a "
              "click.".format(KEY_LABEL), align="left", wordWrap=True, height=36), "caption")
    for row in GRID:
        _fill_row()
        for index in row:
            if index is None:
                hubstyle.mark(cmds.button(CENTRE_BTN, label=KEY_LABEL, enable=False,
                                          height=hubstyle.height("button", 26),
                                          annotation="The key that holds the menu"),
                              "secondary")
                continue
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

