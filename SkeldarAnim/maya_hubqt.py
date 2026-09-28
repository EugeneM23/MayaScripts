"""maya_hubqt - the SkeldarAnim hub's skin: its Qt widgets.

What `maya_hub` builds when Qt is there (2026-09-28, style B + scheme 3 of
the brainstorm): a root of ours inside the same workspaceControl, holding

    header    the SA mark, "SkeldarAnim", the hotkeys button (lit while the
              map is on), the version chip (click: Check update), a menu
    message   one line under the header, shown while it holds text
    strip     one icon per section: expand it and scroll to it
    scroll    group labels and CARDS - a clickable header (icon chip,
              title, the moved subtitle, chevron) over a BODY whose named
              layout is where a tool's `build_panel()` runs

Every cmds control a builder makes lands in a body through
`cmds.setParent(path_of(body_layout))` -- measured 2026-09-28 in a probe
window: names, exists/edit/query all as before, the full path running
through the Qt objects (which is why every object here has a name). The
look is `maya_hubstyle.stylesheet()` on the root; the builders' marks are
turned into `skRole` properties, icons, swatches and moved subtitles by
`apply_marks`.

Two Maya seams, replaced by the tests: `find` (MQtUtil -> a QWidget
wrapper) and `path_of` (MQtUtil.fullName). Class-specific calls on Maya's
own widgets go through Qt PROPERTIES (`wordWrap`, `icon`, `iconSize`):
`wrapInstance(ptr, QLabel)` hands back the cached QWidget wrapper when one
exists, and its `setWordWrap` raises AttributeError (measured).

Spec: docs/superpowers/specs/2026-09-28-hub-skin-design.md
"""

import types

import maya_hubicons as hubicons
import maya_hubstyle as hubstyle

_QT = []

#  How long the mouse may be off every card before the light goes to the
#  resting card (see Skin.resting): long enough to cross the gap between two
#  cards without a flash, short enough to read as immediate.
FALLBACK_MS = 150


def qt():
    """PySide6 (Maya 2025+), else PySide2, as one namespace; None without Qt."""
    if _QT:
        return _QT[0]
    ns = None
    try:
        from PySide6 import QtCore, QtGui, QtSvg, QtWidgets
        import shiboken6 as shiboken
        ns = types.SimpleNamespace(QtCore=QtCore, QtGui=QtGui, QtSvg=QtSvg,
                                   QtWidgets=QtWidgets, shiboken=shiboken)
    except ImportError:
        try:
            from PySide2 import QtCore, QtGui, QtSvg, QtWidgets
            import shiboken2 as shiboken
            ns = types.SimpleNamespace(QtCore=QtCore, QtGui=QtGui,
                                       QtSvg=QtSvg, QtWidgets=QtWidgets,
                                       shiboken=shiboken)
        except ImportError:
            ns = None
    _QT.append(ns)
    return ns


def _maya_ui_ok():
    """Maya's UI is up: OpenMayaUI imports, not batch, a QApplication runs."""
    try:
        import maya.cmds as cmds
        import maya.OpenMayaUI  # noqa: F401
        if cmds.about(batch=True):
            return False
    except Exception:                                        # noqa: BLE001
        return False
    q = qt()
    return bool(q and q.QtWidgets.QApplication.instance())


def available():
    """Whether the skin can be built here."""
    return qt() is not None and _maya_ui_ok()


# ------------------------------------------------------------------- seams

def find(name, layout=False):
    """The QWidget of Maya control (or layout) `name`, or None."""
    import maya.OpenMayaUI as omui
    q = qt()
    ptr = (omui.MQtUtil.findLayout(name) if layout
           else omui.MQtUtil.findControl(name))
    if not ptr and not layout:
        ptr = omui.MQtUtil.findLayout(name)
    if not ptr:
        return None
    widget = q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
    if not q.shiboken.isValid(widget):
        #  a dead wrapper cached at this address (see _spread): drop it and
        #  wrap afresh; still dead means nothing to style
        q.shiboken.invalidate(widget)
        widget = q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
        if not q.shiboken.isValid(widget):
            return None
    return widget


def path_of(obj):
    """The Maya path of a Qt object of ours: what `cmds.setParent` takes."""
    import maya.OpenMayaUI as omui
    q = qt()
    return omui.MQtUtil.fullName(int(q.shiboken.getCppPointer(obj)[0]))


def destroy_roots(control):
    """Delete every skin root standing in workspaceControl `control`, NOW.

    Measured 2026-09-28: after an install the fresh `maya_hub` does not know
    the skin an older module object built, so a rebuild left that root in
    the control beside the new one -- two sets of controls with the same
    names, and `find` styling the old set. Found by objectName, never by
    module state. Returns how many were deleted."""
    q = qt()
    host = host_widget(control)
    if host is None:
        return 0
    roots = [w for w in host.findChildren(q.QtWidgets.QWidget)
             if w.objectName() == hubstyle.ROOT]
    for root in roots:
        root.setParent(None)
        q.shiboken.delete(root)
    return len(roots)


def host_widget(control):
    """The QWidget of workspaceControl `control`, which a root goes into.

    The WIDGET, not its layout: a layout reached through a temporary
    wrapper is invalidated with that wrapper -- measured 2026-09-28,
    `find(control).layout()` returned valid and was "Internal C++ object
    already deleted" one call later, when the wrapper had been collected.
    The Skin holds the widget for as long as it needs the layout.
    """
    return find(control)


# ------------------------------------------------------------------- icons

def pixmap(name, colour, size):
    """Icon `name` in `colour`, `size` physical pixels square."""
    q = qt()
    data = q.QtCore.QByteArray(hubicons.svg(name, colour).encode("utf-8"))
    renderer = q.QtSvg.QSvgRenderer(data)
    image = q.QtGui.QPixmap(size, size)
    image.fill(q.QtCore.Qt.transparent)
    painter = q.QtGui.QPainter(image)
    renderer.render(painter)
    painter.end()
    return image


def icon_file(name, colour, folder=None):
    """Icon `name` in `colour` written as an SVG file; its path, forward
    slashes (what a stylesheet's `url()` takes -- the dropdown arrow)."""
    import os
    import tempfile
    folder = folder or os.path.join(tempfile.gettempdir(), "skeldar_hub")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    path = os.path.join(folder, "{0}_{1}.svg".format(name,
                                                     colour.lstrip("#")))
    with open(path, "w") as handle:
        handle.write(hubicons.svg(name, colour))
    return path.replace("\\", "/")


def icon(name, colour, size, on_colour=None):
    """A QIcon; `on_colour` draws its checked state."""
    q = qt()
    result = q.QtGui.QIcon()
    result.addPixmap(pixmap(name, colour, size), q.QtGui.QIcon.Normal,
                     q.QtGui.QIcon.Off)
    if on_colour:
        result.addPixmap(pixmap(name, on_colour, size), q.QtGui.QIcon.Normal,
                         q.QtGui.QIcon.On)
    return result


# ICON colour per role: the text colour the stylesheet gives that role.
_ICON_COLOUR = {"primary": "on_accent", "danger": "danger"}


def repolish(widget):
    """Re-read the stylesheet after a property the rules select on changed."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def _named(widget, name, role=None):
    widget.setObjectName(name)
    if role:
        widget.setProperty("skRole", role)
    return widget


# ------------------------------------------------------------------- cards

_CLASSES = {}


def _head_class():
    """A QWidget that calls back on a left click: the card's header."""
    if "head" not in _CLASSES:
        q = qt()

        class CardHead(q.QtWidgets.QWidget):

            def __init__(self, on_click, parent=None):
                super(CardHead, self).__init__(parent)
                self._on_click = on_click
                self.setCursor(q.QtCore.Qt.PointingHandCursor)

            def mousePressEvent(self, event):              # noqa: N802
                if event.button() == q.QtCore.Qt.LeftButton:
                    self._on_click()
                    event.accept()
                    return
                super(CardHead, self).mousePressEvent(event)

        _CLASSES["head"] = CardHead
    return _CLASSES["head"]


def _watcher_class():
    """An application-wide event filter: a press or a focus change anywhere
    is handed to `on_press(widget)`, the mouse entering a widget to
    `on_enter(widget)`; it never swallows the event."""
    if "watch" not in _CLASSES:
        q = qt()
        pressed = (q.QtCore.QEvent.MouseButtonPress, q.QtCore.QEvent.FocusIn)
        entered = q.QtCore.QEvent.Enter
        left = q.QtCore.QEvent.Leave

        class Watcher(q.QtCore.QObject):

            def __init__(self, on_press, on_enter, on_leave, parent=None):
                super(Watcher, self).__init__(parent)
                self._on_press = on_press
                self._on_enter = on_enter
                self._on_leave = on_leave

            def eventFilter(self, obj, event):             # noqa: N802
                kind = event.type()
                try:
                    if kind in pressed:
                        self._on_press(obj)
                    elif kind == entered:
                        self._on_enter(obj)
                    elif kind == left:
                        self._on_leave(obj)
                except Exception:                            # noqa: BLE001
                    pass
                return False

        _CLASSES["watch"] = Watcher
    return _CLASSES["watch"]


class Card(object):
    """One section: header over body. `body_layout` is where a builder runs."""

    def __init__(self, key, label, icon_name, colour, chip, scale,
                 collapsed=False, on_toggle=None):
        q = qt()
        w = q.QtWidgets
        self.key = key
        self.scale = scale
        self._on_toggle = on_toggle
        s = lambda n: hubstyle.px(n, scale)             # noqa: E731

        self.frame = _named(w.QFrame(), "skeldarHubCard_" + key)
        self.frame.setProperty("skCard", True)
        column = w.QVBoxLayout(self.frame)
        column.setObjectName("skeldarHubCardLayout_" + key)
        column.setContentsMargins(s(8), s(7), s(8), s(8))
        column.setSpacing(s(6))

        self.header = _named(_head_class()(self.toggle),
                             "skeldarHubCardHead_" + key, "cardhead")
        row = w.QHBoxLayout(self.header)
        row.setObjectName("skeldarHubCardHeadLayout_" + key)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(s(7))
        chip_label = _named(w.QLabel(), "skeldarHubCardIcon_" + key,
                            "cardicon")
        chip_label.setFixedSize(s(22), s(22))
        chip_label.setAlignment(q.QtCore.Qt.AlignCenter)
        chip_label.setPixmap(pixmap(icon_name, colour, s(14)))
        chip_label.setStyleSheet("background: {0}; border-radius: {1}px;"
                                 .format(chip, s(6)))
        title = _named(w.QLabel(label), "skeldarHubCardTitle_" + key,
                       "cardtitle")
        #  Where a moved subtitle goes: takes what the title leaves and never
        #  asks for more, so a long line clips instead of widening the hub.
        self.subtitle_slot = _named(w.QWidget(), "skeldarHubCardSub_" + key)
        self.subtitle_slot.setSizePolicy(w.QSizePolicy.Ignored,
                                         w.QSizePolicy.Preferred)
        sub = w.QHBoxLayout(self.subtitle_slot)
        sub.setObjectName("skeldarHubCardSubLayout_" + key)
        sub.setContentsMargins(0, 0, 0, 0)
        self.chevron = _named(w.QLabel(), "skeldarHubCardChevron_" + key)
        row.addWidget(chip_label)
        row.addWidget(title)
        row.addWidget(self.subtitle_slot, 1)
        row.addWidget(self.chevron)

        self.body = _named(w.QWidget(), "skeldarHubBody_" + key)
        self.body_layout = w.QVBoxLayout(self.body)
        self.body_layout.setObjectName("skeldarHubBodyLayout_" + key)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        column.addWidget(self.header)
        column.addWidget(self.body)
        self._collapsed = None
        self.set_collapsed(collapsed)

    def body_path(self):
        return path_of(self.body_layout)

    def collapsed(self):
        return bool(self._collapsed)

    def set_collapsed(self, collapsed):
        """Show or hide the body. No callback: code opening a card remembers
        through the hub; only the animator's click calls back (`toggle`)."""
        collapsed = bool(collapsed)
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        self.body.setVisible(not collapsed)
        name = "chevron-right" if collapsed else "chevron-down"
        self.chevron.setPixmap(pixmap(name, hubstyle.TOKENS["muted"],
                                      hubstyle.px(14, self.scale)))

    def toggle(self):
        self.set_collapsed(not self._collapsed)
        if self._on_toggle:
            self._on_toggle(self.key, self._collapsed)

    def add_subtitle(self, widget):
        """Move a builder's line into the header, one line, never widening."""
        q = qt()
        widget.setProperty("wordWrap", False)
        widget.setProperty("skRole", "subtitle")
        widget.setProperty("alignment", q.QtCore.Qt.AlignRight
                           | q.QtCore.Qt.AlignVCenter)
        widget.setMinimumHeight(0)
        widget.setMaximumHeight(16777215)
        widget.setMinimumWidth(0)
        widget.setSizePolicy(q.QtWidgets.QSizePolicy.Ignored,
                             q.QtWidgets.QSizePolicy.Preferred)
        self.subtitle_slot.layout().addWidget(widget, 1)
        return widget


# -------------------------------------------------------------------- skin

class Skin(object):
    """The whole skinned hub. `parent_layout` is the workspaceControl's."""

    def __init__(self, parent, scale=1.0, callbacks=None):
        q = qt()
        w = q.QtWidgets
        #  a widget (the workspaceControl's) or a layout; the widget wrapper
        #  is kept, or its layout's wrapper dies with it (see host_widget)
        self.host = parent
        parent_layout = (parent if isinstance(parent, w.QLayout) or parent
                         is None else parent.layout())
        self.scale = scale
        self.cb = callbacks or {}
        self.cards = {}
        self.jumps = {}
        s = self.px

        self.root = _named(w.QWidget(), hubstyle.ROOT)
        top = w.QVBoxLayout(self.root)
        top.setObjectName("skeldarHubRootLayout")
        top.setContentsMargins(s(6), s(6), s(6), s(6))
        top.setSpacing(s(6))
        if parent_layout is not None:
            parent_layout.addWidget(self.root)

        self.header = self._build_header()
        top.addWidget(self.header)
        self.message = self._build_message()
        top.addWidget(self.message)

        self.strip = _named(w.QWidget(), "skeldarHubStrip", "strip")
        strip = w.QHBoxLayout(self.strip)
        strip.setObjectName("skeldarHubStripLayout")
        strip.setContentsMargins(s(3), s(3), s(3), s(3))
        strip.setSpacing(s(2))
        top.addWidget(self.strip)

        self.scroll = _named(w.QScrollArea(), hubstyle.SCROLL)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(w.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(
            q.QtCore.Qt.ScrollBarAlwaysOff)
        self.content = _named(w.QWidget(), hubstyle.CONTENT)
        self.column = w.QVBoxLayout(self.content)
        self.column.setObjectName("skeldarHubColumnLayout")
        self.column.setContentsMargins(0, 0, s(2), 0)
        self.column.setSpacing(s(6))
        self.column.addStretch(1)
        self.scroll.setWidget(self.content)
        self.scroll.viewport().setObjectName(hubstyle.VIEWPORT)
        top.addWidget(self.scroll, 1)

        #  The lit card (2026-09-28, «активное окно подсвечивалось немного
        #  другим цветом»; then «когда я наводил мышкой на какой-то раздел у
        #  него включалась подсветка»): the card under the mouse. With the
        #  mouse off every card, the one last pressed or focused in, or
        #  jumped to (`pinned`) -- only while it is OPEN, and only after
        #  FALLBACK_MS («подсветка перепрыгивает на последний активный
        #  раздел ... картинка как бы мигает»): crossing the gap between two
        #  cards lit the pinned one for a moment. The watcher is the root's
        #  child, so it leaves the application's filters when the root is
        #  deleted; the timer likewise.
        self.active = None
        self.pinned = None
        self._fallback = q.QtCore.QTimer(self.root)
        self._fallback.setObjectName("skeldarHubFallback")
        self._fallback.setSingleShot(True)
        self._fallback.setInterval(FALLBACK_MS)
        self._fallback.timeout.connect(self._fall_back)
        self._watcher = _watcher_class()(self._activate_from,
                                         self._hover_from, self._left_from,
                                         self.root)
        app = q.QtWidgets.QApplication.instance()
        if app is not None:
            app.installEventFilter(self._watcher)

    # --------------------------------------------------------------- parts

    def px(self, value):
        return hubstyle.px(value, self.scale)

    def _call(self, key, *args):
        fn = self.cb.get(key)
        if fn:
            return fn(*args)
        return None

    def _head_button(self, name, icon_name, tip, checkable=False):
        q = qt()
        button = _named(q.QtWidgets.QToolButton(), name, "headbtn")
        button.setIcon(icon(icon_name, hubstyle.TOKENS["muted"], self.px(16),
                            on_colour=hubstyle.TOKENS["accent_text"]))
        button.setIconSize(q.QtCore.QSize(self.px(16), self.px(16)))
        button.setToolTip(tip)
        button.setCheckable(checkable)
        button.setAutoRaise(True)
        return button

    def _build_header(self):
        q = qt()
        w = q.QtWidgets
        s = self.px
        header = _named(w.QWidget(), "skeldarHubHeader", "header")
        row = w.QHBoxLayout(header)
        row.setObjectName("skeldarHubHeaderLayout")
        row.setContentsMargins(s(2), s(2), s(2), s(2))
        row.setSpacing(s(6))
        logo = _named(w.QLabel("SA"), "skeldarHubLogo", "logo")
        logo.setFixedSize(s(20), s(20))
        logo.setAlignment(q.QtCore.Qt.AlignCenter)
        title = _named(w.QLabel("SkeldarAnim"), "skeldarHubTitle",
                       "hubtitle")
        self.hotkeys = self._head_button(
            "skeldarHubHotkeys", "keyboard", "Hotkey map: OFF",
            checkable=True)
        self.hotkeys.clicked.connect(lambda *_a: self._call("hotkeys"))
        self.version = _named(w.QToolButton(), "skeldarHubVersion", "version")
        self.version.setText("")
        self.version.setCursor(q.QtCore.Qt.PointingHandCursor)
        self.version.clicked.connect(lambda *_a: self._call("version"))
        self.menu_button = self._head_button("skeldarHubMenu",
                                             "dots-vertical", "More")
        self.menu = w.QMenu(self.menu_button)
        self.menu.setObjectName("skeldarHubMenuPopup")
        for text, key in (("Check update", "check_update"),
                          ("Hotkey Editor...", "hotkey_editor"),
                          (None, None),
                          ("Classic look", "classic")):
            if text is None:
                self.menu.addSeparator()
                continue
            action = self.menu.addAction(text)
            action.triggered.connect(lambda *_a, k=key: self._call(k))
        self.menu_button.setMenu(self.menu)
        self.menu_button.setPopupMode(w.QToolButton.InstantPopup)
        row.addWidget(logo)
        row.addWidget(title)
        row.addStretch(1)
        row.addWidget(self.hotkeys)
        row.addWidget(self.version)
        row.addWidget(self.menu_button)
        return header

    def _build_message(self):
        q = qt()
        w = q.QtWidgets
        s = self.px
        box = _named(w.QWidget(), "skeldarHubMessage", "message")
        row = w.QHBoxLayout(box)
        row.setObjectName("skeldarHubMessageLayout")
        row.setContentsMargins(s(8), s(4), s(4), s(4))
        row.setSpacing(s(4))
        self.message_text = _named(w.QLabel(""), "skeldarHubMessageText",
                                   "messagetext")
        self.message_text.setWordWrap(True)
        self.message_text.setSizePolicy(w.QSizePolicy.Ignored,
                                        w.QSizePolicy.Preferred)
        self.message_close = self._head_button("skeldarHubMessageClose", "x",
                                               "Hide")
        self.message_close.clicked.connect(lambda *_a: box.setVisible(False))
        row.addWidget(self.message_text, 1)
        row.addWidget(self.message_close, 0, q.QtCore.Qt.AlignTop)
        box.setVisible(False)
        return box

    # ----------------------------------------------------------------- api

    def add_group(self, key, label):
        q = qt()
        group = _named(q.QtWidgets.QLabel(label), "skeldarHubGroup_" + key,
                       "grouplabel")
        group.setContentsMargins(self.px(3), self.px(2), 0, 0)
        self.column.insertWidget(self.column.count() - 1, group)
        return group

    def add_card(self, key, label, icon_name, colour, chip, collapsed=False):
        card = Card(key, label, icon_name, colour, chip, self.scale,
                    collapsed=collapsed,
                    on_toggle=lambda k, c: self._call("toggled", k, c))
        self.column.insertWidget(self.column.count() - 1, card.frame)
        self.cards[key] = card
        return card

    def add_jump(self, key, label, icon_name, colour):
        q = qt()
        button = _named(q.QtWidgets.QToolButton(), "skeldarHubJump_" + key,
                        "jump")
        button.setIcon(icon(icon_name, colour, self.px(16)))
        button.setIconSize(q.QtCore.QSize(self.px(16), self.px(16)))
        button.setToolTip(label)
        button.setAutoRaise(True)
        button.setSizePolicy(q.QtWidgets.QSizePolicy.Expanding,
                             q.QtWidgets.QSizePolicy.Fixed)
        button.clicked.connect(lambda *_a, k=key: self._call("jump", k))
        self.strip.layout().addWidget(button)
        self.jumps[key] = button
        return button

    def finish(self, sheet):
        self.root.setStyleSheet(sheet)

    def say(self, text, state=None):
        """The header's message line: shown while it holds text."""
        self.message_text.setText(text or "")
        self.message.setVisible(bool(text))
        if state is not None:
            self.set_state(state)

    def set_state(self, state):
        self.version.setProperty("skState", state or "")
        repolish(self.version)

    def set_version(self, text, tooltip, state=None):
        self.version.setText(text)
        self.version.setToolTip(tooltip)
        if state is not None:
            self.set_state(state)

    def paint_hotkeys(self, active):
        self.hotkeys.setChecked(bool(active))
        self.hotkeys.setToolTip("Hotkey map: " + ("ON" if active else "OFF")
                                + " - press to switch")

    def set_active(self, key):
        """Card `key` is the one worked in (None: none): pinned and lit."""
        self._fallback.stop()
        self.pinned = key if key in self.cards else None
        self._light(self.pinned)

    def resting(self):
        """What is lit with the mouse off every card: the pinned card if it
        is open, else none."""
        card = self.cards.get(self.pinned) if self.pinned else None
        if card is not None and not card.collapsed():
            return self.pinned
        return None

    def _fall_back(self):
        self._light(self.resting())

    def _light(self, key):
        """Light card `key` (None: none), the previous one back to plain."""
        key = key if key in self.cards else None
        if key == self.active:
            return
        for other in (self.active, key):
            card = self.cards.get(other) if other else None
            if card is not None:
                card.frame.setProperty("skActive", other == key)
                repolish(card.frame)
        self.active = key

    def card_of(self, widget):
        """The key of the card holding `widget`, or None."""
        q = qt()
        if not isinstance(widget, q.QtWidgets.QWidget):
            return None
        if widget is not self.root and not self.root.isAncestorOf(widget):
            return None                     # most of Maya: one walk, out
        for key, card in self.cards.items():
            if card.frame is widget or card.frame.isAncestorOf(widget):
                return key
        return None

    def _activate_from(self, widget):
        key = self.card_of(widget)
        if key is not None:
            self.set_active(key)

    def _hover_from(self, widget):
        """The mouse entered `widget`: its card lit at once; off every card,
        the resting light after FALLBACK_MS -- entering another card first
        cancels it, so a gap between cards lights nothing in between."""
        key = self.card_of(widget)
        if key is not None:
            self._fallback.stop()
            self._light(key)
        elif self.active != self.resting():
            self._fallback.start()

    def _left_from(self, widget):
        """The mouse left the hub (to another window, where no Enter of
        ours arrives): the resting light, after the same pause."""
        if widget is self.root and self.active != self.resting():
            self._fallback.start()

    def scroll_to(self, key):
        card = self.cards.get(key)
        if card is None:
            return None
        offset = card.frame.y()
        self.scroll.verticalScrollBar().setValue(offset)
        return offset

    def alive(self):
        q = qt()
        try:
            return bool(q.shiboken.isValid(self.root))
        except Exception:                                    # noqa: BLE001
            return False

    def destroy(self):
        """Delete the root NOW (not deferred): a classic build right after
        must not meet the controls' names still standing."""
        if not self.alive():
            return
        q = qt()
        self.root.setParent(None)
        q.shiboken.delete(self.root)


# ------------------------------------------------------------------- marks

def _luminance(hex_colour):
    """Relative brightness 0..1 of "#rrggbb" (Rec. 709 weights)."""
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _swatch_sheet(hex_colour, radius, scale):
    #  a colour's name readable on it: dark on the light ones, light on
    #  the dark ones (blue and violet)
    text = (hubstyle.TOKENS["panel"] if _luminance(hex_colour) > 0.45
            else hubstyle.TOKENS["text"])
    return ("QPushButton {{ background: {0}; border: none; border-radius: "
            "{1}px; padding: 0px; color: {2}; }} QPushButton:hover {{ border: "
            "{3}px solid {4}; }}").format(hex_colour, radius, text,
                                          hubstyle.px(2, scale),
                                          hubstyle.TOKENS["text"])


def _fill_class():
    """An event filter keeping a widget of ours over the whole of another."""
    if "fill" not in _CLASSES:
        q = qt()

        class Fill(q.QtCore.QObject):

            def __init__(self, cover, parent=None):
                super(Fill, self).__init__(parent)
                self._cover = cover

            def eventFilter(self, obj, event):             # noqa: N802
                if event.type() == q.QtCore.QEvent.Resize:
                    self._cover.setGeometry(obj.rect())
                return False

        _CLASSES["fill"] = Fill
    return _CLASSES["fill"]


def _spread(row, scale=1.0):
    """The segments of a Maya rowLayout share its width equally.

    Measured 2026-09-28: the rowLayout's layout is `QmayaRowLayout` (a
    QHBoxLayout underneath) and it places its children at their own widths
    whatever their stretch or size policy says -- the segments packed to
    the left of their track. A minimum width does move them, and would
    also stop the dock from ever getting narrower. So the buttons go into
    a row of OURS laid over the track (kept over it on every resize), with
    equal stretches; the track keeps no minimum width of theirs. Maya
    finds a moved control by name as before (the subtitle's move proved
    it). `row` stays referenced while its children are used."""
    q = qt()
    w = q.QtWidgets
    buttons = [child for child in row.children()
               if isinstance(child, w.QAbstractButton)]
    if not buttons:
        return 0
    cover = _named(w.QWidget(row), row.objectName() + "_skinSegments")
    box = w.QHBoxLayout(cover)
    box.setObjectName(row.objectName() + "_skinSegmentsLayout")
    inset = hubstyle.px(2, scale)
    box.setContentsMargins(inset, inset, inset, inset)
    box.setSpacing(inset)
    height = 0
    for button in buttons:
        button.setSizePolicy(w.QSizePolicy.Expanding, w.QSizePolicy.Preferred)
        box.addWidget(button, 1)
        height = max(height, button.sizeHint().height())
    row.setMinimumHeight(height + 2 * inset)
    watcher = _fill_class()(cover, cover)
    row.installEventFilter(watcher)
    cover.setGeometry(row.rect())
    cover.show()
    return len(buttons)


def apply_marks(marks, card, scale):
    """Turn a builder's marks into the skin: properties, icons, swatches,
    subtitles moved into `card`'s header. Returns how many were applied."""
    applied = 0
    size = hubstyle.px(15, scale)
    for mark in marks:
        try:
            if _apply_mark(mark, card, scale, size):
                applied += 1
        except Exception:                                    # noqa: BLE001
            #  one control that will not take its look must not cost the
            #  whole skin (the hub would fall back to classic)
            import traceback
            print("SkeldarAnim hub: no look for {0} ({1})".format(
                mark.name, mark.role))
            print(traceback.format_exc())
    #  The segment tracks last: their buttons have their own marks applied
    #  by now, and move into the skin's row with them (_spread).
    for mark in marks:
        if mark.role != "segments":
            continue
        try:
            row = find(mark.name, True)
            if row is not None:
                _spread(row, scale)
        except Exception:                                    # noqa: BLE001
            import traceback
            print(traceback.format_exc())
    return applied


def _apply_mark(mark, card, scale, size):
    """One mark onto its control; False when the control is not there."""
    q = qt()
    widget = find(mark.name, mark.layout)
    if widget is None:
        return False
    if mark.role == "subtitle":
        card.add_subtitle(widget)
        return True
    if mark.role == "swatchonly":
        for child in widget.findChildren(q.QtWidgets.QWidget):
            if child.objectName() in ("slider", "color"):
                child.setVisible(False)
        widget.setProperty("skRole", "swatchonly")
        return True
    widget.setProperty("skRole", mark.role)
    if mark.role == "segments":
        #  after the segment marks (they come later in the list): see
        #  apply_marks
        return True
    if mark.role == "segment":
        widget.setSizePolicy(q.QtWidgets.QSizePolicy.Expanding,
                             q.QtWidgets.QSizePolicy.Preferred)
    if mark.role == "swatch":
        side = min(widget.maximumWidth(), widget.maximumHeight())
        radius = (side // 2 if side <= hubstyle.px(24, scale)
                  else hubstyle.px(6, scale))
        widget.setStyleSheet(_swatch_sheet(mark.colour, radius, scale))
        return True
    if mark.icon:
        colour = hubstyle.TOKENS[_ICON_COLOUR.get(mark.role, "text2")]
        widget.setProperty("icon", icon(mark.icon, colour, size))
        widget.setProperty("iconSize", q.QtCore.QSize(size, size))
    return True
