"""maya_hubpop - a section's copy in a floating window of its own.

2026-10-18 (spec: docs/superpowers/specs/2026-10-18-floating-windows-design.md). The
animator: «Попапы которые живут исключительно в рамках вьюпорта нам больше не нужны. Давай
наш плагин будет теперь открывать обычные окна ... перерисуем наши окна и сделаем новые
анимации в стиле таймслайдера».

Each window is a second build of a section (maya_hubcopy: its controls and callbacks run in
a scope of their own) in a frameless Qt.Tool window owned by Maya's main window - above
Maya, not above another application, gone with Maya when minimised. It is free of the
viewport: a drag of its title row carries it anywhere, onto another monitor too, and it is
kept wholly on the screen under the cursor (maya_hubpop_rules: screen_for, clamp_origin).
Its place is its top-left in global logical px, remembered in rules.WINDOW_POS_VAR; a place
whose title row stands on no screen any more is dropped, and with no place the window stands
by the point it came from (rules.place_by_point). It needs no 3D view, so a restore at
Maya's start waits only for Maya's main window.

Look B (maya_hubwindow): the hub's dark panel with a hairline, a 34 px title row - the
section's icon in its group colour, its name in spaced capitals, the roll-up and close
buttons as painted pills - and the section on a card inside. It bursts out of the point that
was pressed and folds back into the one the close came from (maya_hubwindow.Burster, the
Time Bar's burst). One window a section: a second ⧉ raises it and flashes it (`present`).

The 2026-10-09 history (spec: 2026-10-09-hub-section-popups-design.md): the window is see-
through, so its rounded corners show what is behind; a rolled-up window is its name alone
and as wide as it; an unrolled one is at most rules.MAX_HEIGHT tall and scrolls; its edges
drag to resize (right, bottom, corner; a double click gives a side back), the sizes
remembered per section (SIZE_VAR, BAR_VAR, COLLAPSED_VAR); it lights up under the mouse as a
card does. Until 2026-10-18 it lived inside the active viewport, followed it 20 times a
second and hid with its panel; that is gone.

The state lives on `sys` (trap 111: an install purges our modules, and the windows must find
the ones an older module object opened, to destroy them). Qt is imported lazily through
maya_hubqt; the hub is imported lazily here too (maya_hub imports this module for its card
button).
"""

import sys
import traceback

import maya.cmds as cmds

import maya_hubburst as hubburst
import maya_hubcopy as hubcopy
import maya_hubmotion as hubmotion
import maya_hubpop_rules as rules
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle
import maya_hubwindow as hubwindow

RESTORE_MS = 500          # a restore before Maya's main window stands waits this long
RESTORE_TRIES = 60        # ... and gives up after this many tries (30 s)
TITLE_H = hubwindow.TITLE_H  # logical px: the title row (2026-10-18)
FALLBACK_SCREEN = (0, 0, 1920, 1080)   # no screen known (no QGuiApplication yet)
AT_CURSOR = rules.AT_CURSOR

_CLASSES = {}


def _state():
    """The windows standing (by key, in opening order), the ones folding shut and the
    restore's bookkeeping. On `sys` (trap 111). `timer` is always None since 2026-10-18 (no
    viewport to follow); an older module object may have left one running, and destroy_all
    stops it."""
    st = getattr(sys, "_skeldar_hubpop", None)
    if st is None:
        st = {"popups": {}, "timer": None, "queued": False, "tries": 0,
              "restoring": False}
        sys._skeldar_hubpop = st
    st.setdefault("closing", [])
    st.setdefault("timer", None)
    return st


def _hub():
    import maya_hub
    return maya_hub


def _card_keys():
    """The keys of the sections that have a card (and so a popout button)."""
    return [sec.key for sec in _hub().card_sections()]


def _scale():
    try:
        return float(cmds.mayaDpiSetting(query=True, realScaleValue=True)
                     or 1.0)
    except Exception:                                        # noqa: BLE001
        return 1.0


def _main_window():
    """Maya's main window as a QWidget, or None (tests, mayapy). Fetched when
    needed and never kept (trap 135)."""
    q = hubqt.qt()
    if q is None or not hubqt._maya_ui_ok():
        return None
    try:
        import maya.OpenMayaUI as omui
        ptr = omui.MQtUtil.mainWindow()
        if ptr:
            return q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
    except Exception:                                        # noqa: BLE001
        pass
    return None


def screens():
    """Every screen's available geometry (x, y, w, h), the rectangles a window is kept on
    (2026-10-18). Maya runs Qt at a device pixel ratio of 1 (trap 98), so these are the
    physical pixels the windows move in. Never empty: with no screen known, FALLBACK_SCREEN
    (rules.screen_for needs one)."""
    found = []
    try:
        q = hubqt.qt()
        for screen in q.QtGui.QGuiApplication.screens():
            g = screen.availableGeometry()
            if g.width() > 0 and g.height() > 0:
                found.append((g.x(), g.y(), g.width(), g.height()))
    except Exception:                                        # noqa: BLE001
        found = []
    return found or [FALLBACK_SCREEN]


def _global(event):
    """An event's global point as (x, y) ints (Qt 6's globalPosition, Qt 5's
    globalPos)."""
    if hasattr(event, "globalPosition"):
        point = event.globalPosition().toPoint()
    else:
        point = event.globalPos()
    return (point.x(), point.y())


def _later(fn):
    """`fn` on the Qt loop's next turn: a window is not deleted inside the
    signal of the animation that shows it (2026-10-09)."""
    q = hubqt.qt()
    q.QtCore.QTimer.singleShot(0, fn)


def _animation(start, end, ms):
    """A QVariantAnimation with no Qt parent: the window keeps it and stops it
    (a window deleted under a running animation must not take it along by
    parenthood)."""
    q = hubqt.qt()
    anim = q.QtCore.QVariantAnimation()
    anim.setStartValue(float(start))
    anim.setEndValue(float(end))
    anim.setDuration(int(ms))
    return anim


# ------------------------------------------------------------------ Qt

def _title_class():
    """The popup's title row (2026-10-09 - a click rolls the popup up or down):
    a press grabs, a move past Qt's drag distance drags, a release that did
    not drag is a click (`click`), a release after a drag drops (each a
    callback of the popup)."""
    if "title" not in _CLASSES:
        q = hubqt.qt()

        class TitleRow(q.QtWidgets.QWidget):

            def __init__(self, grab, move, drop, click, parent=None):
                super(TitleRow, self).__init__(parent)
                self._grab = grab
                self._move = move
                self._drop = drop
                self._click = click
                self._press = None
                self._dragged = False
                self.setCursor(q.QtCore.Qt.SizeAllCursor)

            def mousePressEvent(self, event):              # noqa: N802
                if event.button() == q.QtCore.Qt.LeftButton:
                    self._press = _global(event)
                    self._dragged = False
                    self._grab(self._press)
                    event.accept()
                    return
                super(TitleRow, self).mousePressEvent(event)

            def mouseMoveEvent(self, event):               # noqa: N802
                if self._press is not None and \
                        event.buttons() & q.QtCore.Qt.LeftButton:
                    point = _global(event)
                    if not self._dragged:
                        slop = q.QtWidgets.QApplication.startDragDistance()
                        if abs(point[0] - self._press[0]) \
                                + abs(point[1] - self._press[1]) < slop:
                            event.accept()
                            return
                        self._dragged = True
                    self._move(point)
                    event.accept()
                    return
                super(TitleRow, self).mouseMoveEvent(event)

            def mouseReleaseEvent(self, event):            # noqa: N802
                if event.button() == q.QtCore.Qt.LeftButton \
                        and self._press is not None:
                    dragged = self._dragged
                    self._press = None
                    self._dragged = False
                    if dragged:
                        self._drop()
                    else:
                        self._click()
                    event.accept()
                    return
                super(TitleRow, self).mouseReleaseEvent(event)

        _CLASSES["title"] = TitleRow
    return _CLASSES["title"]


def _cursor_point():
    """The cursor's global position (physical px), or None."""
    try:
        q = hubqt.qt()
        pos = q.QtGui.QCursor.pos()
        return (pos.x(), pos.y())
    except Exception:                                        # noqa: BLE001
        return None


def _under(root):
    """True when the cursor stands on the window `root`."""
    point = _cursor_point()
    if point is None:
        return False
    try:
        return bool(root.frameGeometry().contains(point[0], point[1]))
    except Exception:                                        # noqa: BLE001
        return False


def _hover_class():
    """An event filter on the popup window: its Enter and Leave, which light
    the popup as a card is lit (2026-10-09). It never swallows an event."""
    if "hover" not in _CLASSES:
        q = hubqt.qt()

        class HoverWatch(q.QtCore.QObject):

            def __init__(self, on_change, parent=None):
                super(HoverWatch, self).__init__(parent)
                self._on_change = on_change

            def eventFilter(self, obj, event):               # noqa: N802
                kind = event.type()
                if kind == q.QtCore.QEvent.Enter:
                    self._on_change(True)
                elif kind == q.QtCore.QEvent.Leave:
                    self._on_change(False)
                return False

        _CLASSES["hover"] = HoverWatch
    return _CLASSES["hover"]


def _grip_class():
    """A strip along one edge of a popup window (2026-10-09, «изменять размер
    перетягивая за край»): a press starts a resize (`on_drag(point, True)`), the
    moves report the cursor (`on_drag(point, False)`), the release ends it
    (`on_end()`), and a double click gives the side back to automatic
    (`on_reset()`). The strips stand above the frame, so they take only their own
    few pixels; the cursor says which way the edge moves."""
    if "grip" not in _CLASSES:
        q = hubqt.qt()
        cursors = {
            "right": q.QtCore.Qt.SizeHorCursor,
            "bottom": q.QtCore.Qt.SizeVerCursor,
            "corner": q.QtCore.Qt.SizeFDiagCursor,
        }

        class EdgeGrip(q.QtWidgets.QWidget):

            def __init__(self, kind, on_drag, on_end, on_reset, parent=None):
                super(EdgeGrip, self).__init__(parent)
                self._on_drag = on_drag
                self._on_end = on_end
                self._on_reset = on_reset
                self._dragging = False
                self.setCursor(cursors[kind])

            def mousePressEvent(self, event):              # noqa: N802
                if event.button() == q.QtCore.Qt.LeftButton:
                    self._dragging = True
                    self._on_drag(_global(event), True)
                    event.accept()
                    return
                super(EdgeGrip, self).mousePressEvent(event)

            def mouseMoveEvent(self, event):               # noqa: N802
                if self._dragging and event.buttons() & q.QtCore.Qt.LeftButton:
                    self._on_drag(_global(event), False)
                    event.accept()
                    return
                super(EdgeGrip, self).mouseMoveEvent(event)

            def mouseReleaseEvent(self, event):            # noqa: N802
                if self._dragging and event.button() == q.QtCore.Qt.LeftButton:
                    self._dragging = False
                    self._on_end()
                    event.accept()
                    return
                super(EdgeGrip, self).mouseReleaseEvent(event)

            def mouseDoubleClickEvent(self, event):        # noqa: N802
                if event.button() == q.QtCore.Qt.LeftButton:
                    self._dragging = False
                    self._on_reset()
                    event.accept()
                    return
                super(EdgeGrip, self).mouseDoubleClickEvent(event)

        _CLASSES["grip"] = EdgeGrip
    return _CLASSES["grip"]


class PopupCard(object):
    """What maya_hubqt.apply_marks needs of a card, for a popup: the subtitle
    moves into the title row, the notes become its tooltip, and the status
    and context lines stay where the section put them (`keeps_text`)."""

    keeps_text = True

    def __init__(self, subtitle_slot, title):
        self.status_controls = set()
        self._slot = subtitle_slot
        self._title = title
        self._hints = []

    def add_subtitle(self, widget):
        q = hubqt.qt()
        widget.setProperty("wordWrap", False)
        widget.setProperty("skRole", "subtitle")
        widget.setProperty("alignment", q.QtCore.Qt.AlignRight
                           | q.QtCore.Qt.AlignVCenter)
        widget.setMinimumHeight(0)
        widget.setMaximumHeight(16777215)
        widget.setMinimumWidth(0)
        widget.setSizePolicy(q.QtWidgets.QSizePolicy.Ignored,
                             q.QtWidgets.QSizePolicy.Preferred)
        self._slot.layout().addWidget(widget, 1)
        widget.installEventFilter(hubqt._elide_class()(widget))
        return widget

    def add_hint(self, text):
        text = (text or "").strip()
        if text:
            self._hints.append(text)
            self._title.setToolTip("\n".join(self._hints))


def _run_section(sec):
    """The section's builder into the current parent. A failure is a line of
    text in its place (the hub's rule for a section whose builder raises)."""
    try:
        getattr(_hub()._import(sec.module), sec.builder)()
    except Exception:                                        # noqa: BLE001
        text = traceback.format_exc().strip().splitlines()[-1]
        cmds.text(label="{0} could not be built: {1}".format(sec.label, text),
                  align="left", wordWrap=True)
        print(traceback.format_exc())


def _arrow():
    try:
        return hubqt.icon_file("chevron-down", hubstyle.TOKENS["muted"])
    except Exception:                                        # noqa: BLE001
        return None


class Popup(object):
    """One section's floating window: its scope, its window and the place it stands."""

    def __init__(self, key, sec, scale):
        self.key = key
        self.sec = sec
        self.scale = scale
        self.scope = None
        self.root = None
        self.title = None
        self.subtitle_slot = None
        self.card = None          # the content's card (look B), holding the scroll area
        self.scroll = None
        self.content = None
        self.body = None
        self.place = None         # the window's top-left, global logical px (2026-10-18)
        self.grab = None          # a drag's cursor offset in the window
        self.frame = None
        self.column = None
        self.roll = None          # the roll-up pill in the title row
        self.collapsed = False    # rolled up to its name (2026-10-09)
        self._hover = None        # the window's Enter / Leave watcher
        self._light_anim = None   # the card light fading (frame.level)
        self._flash_anim = None   # a second ⧉'s flash (frame.flash, 2026-10-18)
        self._roll_anim = None    # the window sliding to its rolled height
        self._open_anim = None    # the window fading in (no burst)
        self._fade = None         # the window fading out (closing, no burst)
        self.user_w = None        # the width the animator dragged (logical; None = automatic)
        self.user_h = None        # the height dragged, unrolled (logical; None = automatic)
        self.bar_w = None         # a rolled-up window's width dragged (logical; None = its name's)
        self.grips = []           # the edge strips: right, bottom, corner (2026-10-09)
        self._grip_start = None   # a resize drag in progress: (point, w, h, screen rect)
        self.burster = None       # maya_hubwindow.Burster on the frame (2026-10-18)

    # ------------------------------------------------------------ state

    def alive(self):
        q = hubqt.qt()
        if self.root is None or q is None:
            return False
        try:
            return bool(q.shiboken.isValid(self.root))
        except Exception:                                    # noqa: BLE001
            return False

    @property
    def burst(self):
        """The frame's burst effect, None until the first burst (held by the Burster)."""
        return self.burster.effect if self.burster is not None else None

    # ------------------------------------------------------------ build

    def _window(self):
        q = hubqt.qt()
        w = q.QtWidgets
        Qt = q.QtCore.Qt
        s = self.scale
        tag = self.scope.tag
        px = lambda n: hubstyle.px(n, s)                    # noqa: E731
        root = w.QWidget(_main_window(), Qt.Tool | Qt.FramelessWindowHint)
        root.setObjectName(hubstyle.POPUP_ROOT + "_" + tag)
        root.setAttribute(Qt.WA_ShowWithoutActivating, True)
        #  See-through (2026-10-09): the frame's rounded corners show what is behind.
        #  The root is a plain QWidget, whose stylesheet background is not drawn - the
        #  palette's is, and that was the dark square behind the corners.
        root.setAttribute(Qt.WA_TranslucentBackground, True)
        outer = w.QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        #  look B (2026-10-18, maya_hubwindow): the panel with its hairline, the card inside
        frame = hubqt._named(hubwindow.frame_class()(s), "skeldarAnimPopupFrame_" + tag)
        outer.addWidget(frame)
        self.frame = frame
        column = w.QVBoxLayout(frame)
        column.setContentsMargins(px(5), 0, px(5), px(5))
        column.setSpacing(0)
        self.column = column

        self.title = hubqt._named(
            _title_class()(self._grab, self._drag, self._drop,
                           lambda: self.toggle_roll(animate=True), frame),
            "skeldarAnimPopupTitle_" + tag)
        self.title.setFixedHeight(px(TITLE_H))
        self.title.setSizePolicy(w.QSizePolicy.Preferred, w.QSizePolicy.Fixed)
        row = w.QHBoxLayout(self.title)
        row.setContentsMargins(px(5), 0, 0, 0)
        row.setSpacing(px(6))
        colour = hubstyle.group(self.sec.group).colour
        icon = hubwindow.title_icon(self.sec.icon, colour, s,
                                    "skeldarAnimPopupIcon_" + tag)
        #  the heading role's look: spaced capitals, bold, muted, at the caption size
        name = hubwindow.title_label(self.sec.label, s, "skeldarAnimPopupName_" + tag)
        self.subtitle_slot = hubqt._named(w.QWidget(),
                                          "skeldarAnimPopupSub_" + tag)
        self.subtitle_slot.setSizePolicy(w.QSizePolicy.Ignored,
                                         w.QSizePolicy.Preferred)
        sub = w.QHBoxLayout(self.subtitle_slot)
        sub.setContentsMargins(0, 0, 0, 0)
        #  roll up / unroll (2026-10-09): the chevron, down while open, right while rolled
        #  up; a click on the name does the same. Painted pills since 2026-10-18.
        pill = hubwindow.pill_class()
        self.roll = hubqt._named(pill("chevron-down", s), "skeldarAnimPopupRoll_" + tag)
        self.roll.clicked.connect(lambda *_a: self.toggle_roll(animate=True))
        close = hubqt._named(pill("x", s), "skeldarAnimPopupClose_" + tag)
        close.setToolTip("Close the window - the section stays in the hub")
        close.clicked.connect(lambda *_a, k=self.key: _defer_close(k))
        row.addWidget(icon)
        row.addWidget(name)
        row.addWidget(self.subtitle_slot, 1)
        row.addWidget(self.roll)
        row.addWidget(close)
        column.addWidget(self.title)
        self._paint_roll()

        #  the section stands on its own card (look B), the scroll area inside it
        self.card = w.QFrame()
        self.card.setObjectName("skeldarAnimPopupCard_" + tag)
        frame.content = self.card
        card_column = w.QVBoxLayout(self.card)
        card_column.setContentsMargins(px(4), px(4), px(4), px(4))
        card_column.setSpacing(0)
        self.scroll = w.QScrollArea()
        #  its own name (2026-10-09): the hub's scroll area is found by its
        #  name, and a window's must not be
        self.scroll.setObjectName("skeldarAnimPopupScroll_" + tag)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(w.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #  a roll slides the scroll area to nothing, so it has no minimum: Ignored, as
        #  setMinimumHeight(0) reads as "unset" and QScrollArea's own minimum (48 px)
        #  held the card, and so the window, taller than a dragged height (2026-10-18)
        self.scroll.setMinimumHeight(0)
        self.scroll.setSizePolicy(w.QSizePolicy.Preferred, w.QSizePolicy.Ignored)
        self.card.setSizePolicy(w.QSizePolicy.Preferred, w.QSizePolicy.Ignored)
        #  the viewport paints nothing: the card's face shows through it
        self.scroll.viewport().setAutoFillBackground(False)
        self.content = hubqt._named(w.QWidget(),
                                    "skeldarAnimPopupBody_" + tag, "popbody")
        self.body = w.QVBoxLayout(self.content)
        self.body.setObjectName("skeldarAnimPopupBodyLayout_" + tag)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(0)
        self.scroll.setWidget(self.content)
        card_column.addWidget(self.scroll, 1)
        column.addWidget(self.card, 1)

        sheet = hubstyle.stylesheet(s, arrow=_arrow())
        #  the frame and the card paint themselves (maya_hubwindow); the scroll area and
        #  its body paint nothing of their own
        root.setStyleSheet(
            sheet
            + "\n#{0} {{ border: none; background: transparent; }}\n"
              "QScrollArea#{1} {{ background: transparent; border: none; }}\n"
              "#{2} {{ background: transparent; }}".format(
                  frame.objectName(), self.scroll.objectName(),
                  self.content.objectName()))
        hubwindow.dress(frame, s)
        self.root = root
        #  the light: the window's Enter and Leave (2026-10-09, as a card's)
        self._hover = _hover_class()(self._on_hover, root)
        root.installEventFilter(self._hover)
        #  the edges a drag resizes (2026-10-09, «изменять размер перетягивая за край»):
        #  thin strips above the frame - right (the width), bottom (the height), corner
        #  (both); a rolled-up window has its right strip only (_place_grips)
        self.grips = []
        for kind in ("right", "bottom", "corner"):
            grip = _grip_class()(
                kind,
                lambda point, start, k=kind: self._grip_drag(k, point, start),
                self._grip_end,
                lambda k=kind: self._grip_reset(k),
                root)
            grip.raise_()
            self.grips.append(grip)
        return root

    def build(self):
        """The window and the section's controls in it. Raises (the caller
        destroys what was made); a builder's own failure is a line in place."""
        if not hubcopy.installed():
            hubcopy.install(cmds)
        self.scope = hubcopy.new_scope(section=self.key)
        self._window()
        self.burster = hubwindow.Burster(self.frame, self._burst_parts,
                                         self._burst_face, self.scale)
        card = PopupCard(self.subtitle_slot, self.title)
        hubstyle.take_marks()
        hubstyle.set_skinning(True)
        try:
            with hubcopy.entered(self.scope):
                cmds.setParent(hubqt.path_of(self.body))
                _run_section(self.sec)
            marks = hubstyle.take_marks()
            hubqt.apply_marks(marks, card, self.scale)
        finally:
            hubstyle.set_skinning(False)
        #  rolled up the last time the animator left it (2026-10-09)
        self.collapsed = stored_collapsed(self.key)
        self.user_w, self.user_h = stored_size(self.key)
        self.bar_w = stored_bar(self.key)
        self._show_body(not self.collapsed)
        self._paint_roll()
        self._fit()

    def _show_body(self, on):
        """The section's card shown or hidden (rolled up): hidden, not destroyed."""
        for widget in (self.card, self.scroll):
            if widget is not None:
                widget.setVisible(bool(on))

    def _chrome(self):
        """The height that is not the section: the title row and the frame's
        own margins (2026-10-09)."""
        margins = self.column.contentsMargins()
        title_h = max(self.title.sizeHint().height(), self.title.minimumHeight())
        return margins.top() + margins.bottom() + title_h

    def _sides(self):
        """The width round the section: the frame's and the card's side margins."""
        margins = self.column.contentsMargins()
        inner = self.card.layout().contentsMargins() if self.card is not None else None
        width = margins.left() + margins.right()
        if inner is not None:
            width += inner.left() + inner.right()
        return width

    def _card_pad(self):
        """The card's own top and bottom margins, round the scroll area."""
        if self.card is None:
            return 0
        inner = self.card.layout().contentsMargins()
        return inner.top() + inner.bottom()

    def _target(self, rect):
        """The (w, h) the window takes in `rect` now (rules.popup_size), the
        layouts settled first."""
        for widget in (self.content, self.root):
            layout = widget.layout()
            if layout is not None:
                layout.activate()
        hint = self.content.sizeHint()
        if self.collapsed:
            user_w, user_h = self.bar_w, None
        else:
            user_w, user_h = self.user_w, self.user_h
        return rules.popup_size(
            self.content.minimumSizeHint().width() + self._sides(),
            hint.height() + self._card_pad(), rect,
            self.scale, self._chrome(), collapsed=self.collapsed,
            scrollbar_w=hubstyle.px(12, self.scale),
            title_w=self._title_width(), user_w=user_w, user_h=user_h)

    def _centre(self):
        """The window's centre, global physical px."""
        if self.root is None:
            return (0, 0)
        return (self.root.x() + self.root.width() // 2,
                self.root.y() + self.root.height() // 2)

    def _screen(self):
        """The available rectangle of the screen the window stands on (2026-10-18)."""
        return rules.screen_for(self._centre(), screens())

    def _fit(self, keep_place=False):
        """The window's size (2026-10-09, «минимум лишнего места»): the section's own
        natural size, within its screen less the margins and the cap - rolled up, the
        title row alone. `keep_place`: the window is kept where it stands, clamped onto
        its screen (a roll-up or unroll, 2026-10-18)."""
        rect = self._screen()
        w, h = self._target(rect)
        #  The window's minimum is the layout's, and it is updated when Maya's
        #  event loop runs: a roll-up measured in the same send kept the expanded
        #  minimum and a 110 px window for a 38 px title row (2026-10-09). It is
        #  cleared first, so this resize is the one taken; the layout sets its own
        #  minimum again.
        self._set_size(w, h)
        if keep_place:
            self._keep_on(rect)

    def _keep_on(self, rect):
        """The window clamped wholly onto `rect`; moved only when it is not there."""
        if self.root is None:
            return
        w, h = self.root.width(), self.root.height()
        x, y = rules.clamp_origin(self.root.x(), self.root.y(), w, h, rect)
        if (self.root.x(), self.root.y()) != (x, y):
            self.root.move(x, y)

    def _title_width(self):
        """The title row's own width with the frame's side margins: the width a
        rolled-up window takes to show its name (2026-10-09)."""
        margins = self.column.contentsMargins()
        return margins.left() + margins.right() + self.title.sizeHint().width()

    def _set_size(self, w, h):
        """The window's size, and its edge strips where it now stands (2026-10-09).
        The minimum is cleared first: the layout's own minimum is updated only when
        Maya's event loop runs (see _fit)."""
        if self.root is None:
            return
        self.root.setMinimumHeight(0)
        self.root.resize(int(round(w)), int(round(h)))
        self._place_grips()

    def _place_grips(self):
        """The edge strips where the window now stands: the right one always, the
        bottom and the corner one only while unrolled (2026-10-09)."""
        if self.root is None or len(self.grips) != 3:
            return
        w, h = self.root.width(), self.root.height()
        edge = hubstyle.px(rules.GRIP_W, self.scale)
        right, bottom, corner = self.grips
        if self.collapsed:
            right.setGeometry(max(0, w - edge), 0, edge, h)
            bottom.hide()
            corner.hide()
        else:
            right.setGeometry(max(0, w - edge), 0, edge, max(0, h - edge))
            bottom.setGeometry(0, max(0, h - edge), max(0, w - edge), edge)
            corner.setGeometry(max(0, w - edge), max(0, h - edge), edge, edge)
            bottom.show()
            corner.show()
        right.show()

    def _grip_drag(self, kind, point, start):
        """A resize drag's press (`start`: the window's size and its screen are taken
        then) and its moves: the new size from the cursor, bounded by rules.bounds, so
        the far edges stay on the screen. The size is the window's own memory, logical
        (2026-10-09; the screen in place of the viewport since 2026-10-18)."""
        if self.root is None:
            return
        if start:
            self._settle()
            self._grip_start = (point, self.root.width(), self.root.height(),
                                self._screen())
            return
        if self._grip_start is None:
            return
        (x0, y0), w0, h0, rect = self._grip_start
        new_w, new_h = w0, h0
        if kind in ("right", "corner"):
            new_w = w0 + (point[0] - x0)
        if kind in ("bottom", "corner") and not self.collapsed:
            new_h = h0 + (point[1] - y0)
        low_w, high_w, low_h, high_h = rules.bounds(
            self.content.minimumSizeHint().width() + self._sides(), rect, self.scale,
            self._chrome(), collapsed=self.collapsed,
            scrollbar_w=hubstyle.px(12, self.scale),
            title_w=self._title_width(),
            origin=(self.root.x(), self.root.y()))
        new_w = min(max(new_w, low_w), high_w)
        new_h = min(max(new_h, low_h), high_h)
        self._set_size(new_w, new_h)
        if kind in ("right", "corner"):
            if self.collapsed:
                self.bar_w = new_w / self.scale
            else:
                self.user_w = new_w / self.scale
        if kind in ("bottom", "corner") and not self.collapsed:
            self.user_h = new_h / self.scale

    def _grip_end(self):
        """The release of a resize drag: the sizes are remembered (2026-10-09)."""
        if self._grip_start is None:
            return
        self._grip_start = None
        self._save_size()

    def _grip_reset(self, kind):
        """A double click on an edge gives that side back to automatic (2026-10-09):
        a rolled-up width fits the name again, an unrolled one is the dock's width,
        an unrolled height the section's own."""
        if self.root is None:
            return
        self._settle()
        if kind in ("right", "corner"):
            if self.collapsed:
                self.bar_w = None
            else:
                self.user_w = None
        if kind in ("bottom", "corner") and not self.collapsed:
            self.user_h = None
        self._fit(keep_place=True)
        self._save_size()

    def _save_size(self):
        """The sizes as the animator leaves them, both states (2026-10-09)."""
        _save_popup_size(self.key, self.user_w, self.user_h)
        _save_popup_bar(self.key, self.bar_w)

    def set_collapsed(self, on, remember=True, animate=False):
        """Roll the window up to its name, or unroll it (2026-10-09). `animate`
        (and the Interface animations on): the window slides to its new height;
        else at once. The section's controls are hidden, not destroyed, so
        nothing it holds is lost. Remembered for the next start unless
        `remember` is False."""
        on = bool(on)
        changed = on != self.collapsed
        self.collapsed = on
        self._paint_roll()
        if self.root is not None:
            self._place_grips()
            if animate and changed and hubmotion.enabled() \
                    and self.root.isVisible():
                self._roll_to(on)
            else:
                self._stop_anim("_roll_anim")
                self._show_body(not on)
                self._fit(keep_place=True)
        if remember:
            _save_collapsed(self.key, on)
        return on

    def _roll_to(self, on):
        """The window slides to its rolled height or its unrolled one (2026-10-09,
        «плавная анимация»): its height eased from where it stands, its top kept (and
        the window kept on its screen), the card shown while it opens and hidden once
        it has shut. The target is measured once, at the start."""
        self._stop_anim("_roll_anim")
        rect = self._screen()
        if not on:
            self._show_body(True)
        w, target = self._target(rect)
        start, start_w = self.root.height(), self.root.width()
        if target == start and w == start_w:
            self._roll_done(on)
            return
        self.root.setMinimumHeight(0)
        anim = _animation(0.0, 1.0, hubmotion.duration(
            max(abs(target - start), abs(w - start_w)), self.scale,
            opening=not on))

        def tick(value):
            if self.root is None:
                return
            k = hubmotion.ease(value)
            self._set_size(hubmotion.lerp(start_w, w, k),
                           hubmotion.lerp(start, target, k))
            self._keep_on(rect)

        def done():
            self._roll_anim = None
            self._roll_done(on)

        anim.valueChanged.connect(tick)
        anim.finished.connect(done)
        self._roll_anim = anim
        anim.start()

    def _roll_done(self, on):
        """The end of a roll: a shut window's card hidden, its size exact."""
        if self.root is None:
            return
        if on:
            self._show_body(False)
        self._fit(keep_place=True)

    def toggle_roll(self, animate=False):
        """The roll-up pill's press, or a click on the title row (animated
        there). Answers the new state."""
        return self.set_collapsed(not self.collapsed, animate=animate)

    def _paint_roll(self):
        """The roll pill's chevron as the hub's cards draw theirs: down while open,
        right while rolled up."""
        if self.roll is None:
            return
        self.roll.set_icon("chevron-right" if self.collapsed else "chevron-down")
        self.roll.setToolTip("Unroll" if self.collapsed
                             else "Roll up to the name")

    # ------------------------------------------------------------ place

    def place_window(self, origin=None):
        """The window's top-left: its remembered place when that still falls on a screen,
        else by `origin` (the point it came from; the cursor when None) - 2026-10-18. Then
        it is sized for the screen it stands on, and the place it took is its `place`."""
        w, h = self.root.width(), self.root.height()
        shown = screens()
        x_y = None
        if self.place is not None:
            x_y = rules.place_on_screens(self.place, w, h, shown, self.scale)
        if x_y is None:
            point = origin or _cursor_point() or (shown[0][0] + 100, shown[0][1] + 100)
            x_y = rules.place_by_point(point, w, h, shown, self.scale)
        self.root.move(int(x_y[0]), int(x_y[1]))
        self._fit(keep_place=True)
        self.place = (self.root.x() / self.scale, self.root.y() / self.scale)

    # ------------------------------------------------------- open and close

    def show_open(self, animate=False, origin=None):
        """Show the window: at once, or bursting out of the global `origin` - the cursor
        when None (maya_hubwindow.Burster, 2026-10-17/18). A burst that cannot start falls
        back to a fade (POPUP_OPEN_MS); the window stands still while it fades."""
        self._stop_anim("_open_anim")
        self._end_burst()
        self.root.setWindowOpacity(1.0)
        if not animate:
            self.root.show()
            return
        if self._burst(True, origin, self._opened):
            self.root.show()
            return
        self.root.setWindowOpacity(0.0)
        self.root.show()
        anim = _animation(0.0, 1.0, hubmotion.POPUP_OPEN_MS)

        def tick(value):
            if self.root is not None:
                self.root.setWindowOpacity(hubmotion.ease(value))

        def done():
            self._open_anim = None
            if self.root is not None:
                self.root.setWindowOpacity(1.0)

        anim.valueChanged.connect(tick)
        anim.finished.connect(done)
        self._open_anim = anim
        anim.start()

    def fade_out(self, done, origin=None):
        """Fold the window into the global `origin` (2026-10-17, the cursor when None), else
        fade it out (2026-10-09, POPUP_CLOSE_MS), then call `done`. Its controls take no
        press meanwhile."""
        self._stop_anim("_open_anim")
        self._stop_anim("_roll_anim")
        self._stop_anim("_flash_anim")
        if self.root is None:
            done()
            return
        q = hubqt.qt()
        self.root.setAttribute(q.QtCore.Qt.WA_TransparentForMouseEvents, True)
        if self.root.isVisible() and self._burst(False, origin, lambda: self._folded(done)):
            return
        self._end_burst()
        self.root.setAttribute(q.QtCore.Qt.WA_TransparentForMouseEvents, True)
        start = self.root.windowOpacity()
        anim = _animation(0.0, 1.0, hubmotion.POPUP_CLOSE_MS)

        def tick(value):
            if self.root is not None:
                self.root.setWindowOpacity(
                    start * (1.0 - hubmotion.smooth(value)))

        def finished():
            self._fade = None
            done()

        anim.valueChanged.connect(tick)
        anim.finished.connect(finished)
        self._fade = anim
        anim.start()

    # ------------------------------------------------------------- light

    def set_light(self, on, animate=False):
        """The light up (`on`) or down, as a card's (maya_hubqt.Card.set_lit):
        fading from where it stands when `animate`, else at once."""
        if self.frame is None or self.root is None:
            return
        target = 1.0 if on else 0.0
        self._stop_anim("_light_anim")
        frame = self.frame
        start = frame.level
        if not animate or not frame.isVisible() or start == target:
            frame.level = target
            frame.update()
            return
        shape = hubmotion.ease if on else hubmotion.smooth
        anim = _animation(0.0, 1.0, hubmotion.light_ms(on, start, target))

        def tick(value):
            frame.level = hubmotion.lerp(start, target, shape(value))
            frame.update()

        def done():
            self._light_anim = None
            frame.level = target
            frame.update()

        anim.valueChanged.connect(tick)
        anim.finished.connect(done)
        self._light_anim = anim
        anim.start()

    def flash(self):
        """A second ⧉ on a standing window (2026-10-18): it is raised and flashes as a
        chosen card does (maya_hubqt.Card.pulse) - the flash from its peak down to 0 over
        the rest of hubmotion.FLASH_MS. With the Interface animations off it is only
        raised."""
        if not self.alive():
            return
        try:
            self.root.raise_()
        except RuntimeError:
            return
        self._stop_anim("_flash_anim")
        frame = self.frame
        if frame is None or not hubmotion.enabled() or not frame.isVisible():
            return
        rise = hubmotion.FLASH_RISE
        frame.flash = 1.0
        frame.update()
        anim = _animation(rise, 1.0, hubmotion.FLASH_MS * (1.0 - rise))

        def tick(value):
            frame.flash = hubmotion.flash_at(value)
            frame.update()

        def done():
            self._flash_anim = None
            frame.flash = 0.0
            frame.update()

        anim.valueChanged.connect(tick)
        anim.finished.connect(done)
        self._flash_anim = anim
        anim.start()

    def _on_hover(self, entered):
        if self.bursting():
            return              # the light waits for the burst (2026-10-17)
        self.set_light(entered, animate=hubmotion.enabled())

    # ------------------------------------------------------------- burst

    def bursting(self):
        return bool(self.burster is not None and self.burster.busy())

    def _burst(self, opening, origin, done):
        """Start a burst (`opening`) or a fold toward the global `origin` (the cursor when
        None); `done` is called when it ends. False when it cannot start (the Burster's
        rule: animations off, no frame, a failure)."""
        if self.burster is None or self.root is None:
            return False
        q = hubqt.qt()
        self._stop_anim("_light_anim")
        point = origin or _cursor_point() or (self.root.x(), self.root.y())
        self.root.setAttribute(q.QtCore.Qt.WA_TransparentForMouseEvents, True)
        try:
            started = self.burster.run(opening, point, done)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
            started = False
        if not started:
            self._end_burst()
        return started

    def _end_burst(self):
        """The frame painted as it is again, the window taking presses."""
        if self.burster is not None:
            try:
                self.burster.stop()
            except RuntimeError:
                pass
        if self.root is not None:
            q = hubqt.qt()
            try:
                self.root.setAttribute(q.QtCore.Qt.WA_TransparentForMouseEvents, False)
                if self.frame is not None:
                    self.frame.update()
            except RuntimeError:
                pass

    def _opened(self):
        """A burst in: the frame plain, and lit when the mouse is over it now."""
        self._end_burst()
        if self.root is None:
            return
        self.set_light(_under(self.root), animate=hubmotion.enabled())

    def _folded(self, done):
        """A fold out: the window hidden at once (its last frame is empty), then `done`."""
        if self.root is not None:
            try:
                self.root.hide()
            except RuntimeError:
                pass
        done()

    def _burst_face(self):
        """The card's face under a burst: card toward card_active by the light's level."""
        return hubburst.blend(hubstyle.TOKENS["card"], hubstyle.TOKENS["card_active"],
                              getattr(self.frame, "level", 0.0))

    def _burst_parts(self):
        """The title row and the section's rows, in the frame's coordinates."""
        rows = (self.scroll is not None and self.content is not None
                and self.scroll.isVisible())
        return hubqt.burst_parts(self.frame, self.title,
                                 self.content if rows else None,
                                 self.scroll.viewport() if rows else None,
                                 self.scale)

    # ------------------------------------------------------------- drag

    def _grab(self, point):
        self._settle()
        pos = self.root.pos()
        self.grab = (point[0] - pos.x(), point[1] - pos.y())

    def _settle(self):
        """Finish an opening or a roll at once: a drag takes the window."""
        if self.root is None:
            return
        if self._open_anim is not None or self.bursting():
            self._stop_anim("_open_anim")
            self._end_burst()
            self.root.setWindowOpacity(1.0)
        if self._roll_anim is not None:
            self._stop_anim("_roll_anim")
            self._roll_done(self.collapsed)

    def _drag(self, point):
        """A drag of the title row (2026-10-18): anywhere, kept wholly on the screen under
        the cursor, so it can be carried from one monitor to the next."""
        if self.grab is None:
            return
        w, h = self.root.width(), self.root.height()
        rect = rules.screen_for(point, screens())
        x, y = rules.clamp_origin(point[0] - self.grab[0], point[1] - self.grab[1],
                                  w, h, rect)
        self.root.move(x, y)
        self.place = (x / self.scale, y / self.scale)

    def _drop(self):
        if self.grab is None:
            return
        self.grab = None
        if self.place is not None:
            _save_place(self.key, self.place)

    # ----------------------------------------------------------- destroy

    def _stop_anim(self, slot):
        anim = getattr(self, slot, None)
        setattr(self, slot, None)
        if anim is not None:
            try:
                anim.stop()
            except RuntimeError:                              # already gone
                pass

    def _stop_all(self):
        for slot in ("_light_anim", "_flash_anim", "_roll_anim", "_open_anim", "_fade"):
            self._stop_anim(slot)
        if self.burster is not None:
            try:
                self.burster.stop()
            except RuntimeError:
                pass

    def destroy(self):
        """The copy closed (its scriptJobs killed, its names forgotten) and
        its window deleted, the controls with it. Idempotent."""
        self._stop_all()
        hubcopy.close(self.scope, cmds)
        root = self.root
        self.root = None
        if root is None:
            return
        try:
            q = hubqt.qt()
            if q.shiboken.isValid(root):
                root.hide()
                root.setParent(None)
                q.shiboken.delete(root)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()


# ------------------------------------------------------------- the manager

def is_open(key):
    popup = _state()["popups"].get(key)
    return bool(popup is not None and popup.alive())


def open_keys():
    return [key for key, popup in _state()["popups"].items()
            if popup.alive()]


def open_popup(key, place=None, animate=False, origin=None):
    """Open section `key`'s floating window (2026-10-18: no viewport is asked). `place`:
    its top-left in global logical px, else the one remembered, else by `origin` (the
    global point it bursts out of; the cursor when None). `animate`: it bursts out (the
    card button's press); the restore opens them at once. The window it returns; a section
    already open answers its standing window."""
    st = _state()
    if is_open(key):
        return st["popups"][key]
    hub = _hub()
    sec = hub.section(key)
    if sec is None or sec.key in hub.HEADER_ONLY:
        raise KeyError("no popup for section '{0}'".format(key))
    popup = Popup(key, sec, _scale())
    try:
        popup.build()
        #  the place remembered from the last drag, when the caller names none
        popup.place = place if place is not None else stored_place(key)
        popup.place_window(origin)
        popup.show_open(animate=animate and hubmotion.enabled(), origin=origin)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        popup.destroy()
        raise
    st["popups"][key] = popup
    if not st["restoring"]:
        _save_open()
    _notify(key, True)
    return popup


def open_at(key, point, animate=True):
    """Section `key`'s window by the global `point` (the radial menu, 2026-10-15: «если он
    уже был открыт где-то то он должен открыться в новом месте возле курсора мышки»): a
    window standing anywhere is closed and opened here, unrolled, its top-left AT_CURSOR
    left of and above the point, kept on the point's screen. The window."""
    if is_open(key):
        close_popup(key, forget=False)
    scale = _scale()
    place = ((point[0] - AT_CURSOR[0] * scale) / scale,
             (point[1] - AT_CURSOR[1] * scale) / scale)
    if stored_collapsed(key):
        _save_collapsed(key, False)
    popup = open_popup(key, place=place, animate=animate, origin=point)
    if popup is not None and popup.place is not None:
        _save_place(key, popup.place)
    return popup


def close_popup(key, forget=True, animate=False, origin=None):
    """Close section `key`'s window. `animate` (the card button's and the close pill's
    press): it folds out first, and it is gone from the hub's list at once. `forget`: it
    stays closed after a restart (the close pill and the hub's press); False when an install
    destroys it - the next startup brings it back. `origin`: the global point it folds into
    (2026-10-17; the cursor when None)."""
    st = _state()
    popup = st["popups"].pop(key, None)
    if popup is not None:
        if animate and hubmotion.enabled() and popup.alive() \
                and popup.root.isVisible():
            st["closing"].append(popup)
            popup.fade_out(lambda: _later(lambda: _finish_closing(popup)), origin=origin)
        else:
            popup.destroy()
    if forget:
        _save_open()
    _notify(key, False)
    return popup is not None


def _finish_closing(popup):
    """A window that folded out is destroyed (2026-10-09)."""
    st = _state()
    if popup in st["closing"]:
        st["closing"].remove(popup)
    popup.destroy()


def present(key, origin=None):
    """The card button's press (2026-10-18): the window opens, bursting out of `origin`
    (the cursor when None); a window already standing is raised and flashes, and no copy is
    made («одно окно на раздел»). True: the window stands."""
    st = _state()
    if is_open(key):
        st["popups"][key].flash()
        return True
    return open_popup(key, animate=True, origin=origin) is not None


toggle = present            # the name the hub's popout button called before 2026-10-18


def destroy_all(forget=False):
    """Every window destroyed: ours, the ones folding out, and any an older module object
    opened (found by objectName - trap 102's family). A follow timer an older module object
    left running (before 2026-10-18) is stopped. `forget` as close_popup. Returns how
    many."""
    st = _state()
    count = 0
    for key, popup in list(st["popups"].items()):
        popup.destroy()
        count += 1
        _notify(key, False)
    st["popups"].clear()
    for popup in list(st["closing"]):
        popup.destroy()
        count += 1
    st["closing"] = []
    if st.get("timer"):
        try:
            st["timer"].stop()
        except Exception:                                    # noqa: BLE001
            pass
    st["timer"] = None
    q = hubqt.qt()
    if q is not None and q.QtWidgets.QApplication.instance() is not None:
        for widget in list(q.QtWidgets.QApplication.topLevelWidgets()):
            try:
                if widget.objectName().startswith(hubstyle.POPUP_ROOT):
                    widget.hide()
                    widget.setParent(None)
                    q.shiboken.delete(widget)
                    count += 1
            except RuntimeError:
                pass
    for scope in hubcopy.live():
        if scope.section is not None:
            hubcopy.close(scope, cmds)
    if forget:
        _save_open()
    return count


def adopt():
    """A fresh module object took the hub over (an install, a restart): the
    windows an older one opened go, the remembered ones come back (deferred,
    `restore_later`). Called by maya_hub.build() on a fresh module object."""
    destroy_all(forget=False)
    return restore_later()


# ------------------------------------------------------------- memory

def remembered_keys():
    """The section keys remembered as open, in order, the ones that still
    have a card."""
    if not cmds.optionVar(exists=rules.POPUPS_VAR):
        return []
    return rules.decode_keys(cmds.optionVar(query=rules.POPUPS_VAR),
                             _card_keys())


def stored_place(key):
    """The window's remembered top-left, global logical px, or None (2026-10-18). The old
    viewport offset (rules.POS_VAR) is not read: it held a place in a viewport."""
    var = rules.WINDOW_POS_VAR.format(key)
    if not cmds.optionVar(exists=var):
        return None
    return rules.decode_place(str(cmds.optionVar(query=var)))


def _save_open():
    cmds.optionVar(stringValue=(rules.POPUPS_VAR,
                                rules.encode_keys(open_keys())))


def _save_place(key, place):
    cmds.optionVar(stringValue=(rules.WINDOW_POS_VAR.format(key),
                                rules.encode_place(place)))


def stored_size(key):
    """The unrolled window's size the animator dragged: (w, h) logical, None for a
    side that is automatic (2026-10-09)."""
    var = rules.SIZE_VAR.format(key)
    if not cmds.optionVar(exists=var):
        return (None, None)
    return rules.decode_pair(str(cmds.optionVar(query=var)))


def stored_bar(key):
    """A rolled-up window's width the animator dragged, logical; None = it fits its
    name (2026-10-09)."""
    var = rules.BAR_VAR.format(key)
    if not cmds.optionVar(exists=var):
        return None
    return rules.decode_single(str(cmds.optionVar(query=var)))


def _save_popup_size(key, w, h):
    cmds.optionVar(stringValue=(rules.SIZE_VAR.format(key),
                                rules.encode_pair(w, h)))


def _save_popup_bar(key, w):
    cmds.optionVar(stringValue=(rules.BAR_VAR.format(key),
                                rules.encode_single(w)))


def stored_collapsed(key):
    """Whether section `key`'s window was left rolled up (2026-10-09). False
    when nothing is remembered."""
    var = rules.COLLAPSED_VAR.format(key)
    if not cmds.optionVar(exists=var):
        return False
    return bool(rules.decode_flag(str(cmds.optionVar(query=var))))


def _save_collapsed(key, on):
    cmds.optionVar(stringValue=(rules.COLLAPSED_VAR.format(key),
                                rules.encode_flag(on)))


def restore_later():
    """Queue the restore of the remembered windows, deferred and once. The mark
    that a restore is queued is set only once Maya has taken the call: a call
    that failed must not leave every later restore thinking one is pending
    (found 2026-10-09 by a run that built the hub before the popup tests)."""
    st = _state()
    if st["queued"]:
        return False
    st["tries"] = 0
    cmds.evalDeferred(_restore, lowestPriority=True)
    st["queued"] = True
    return True


def _restore():
    """Open the remembered windows. A window needs no 3D view (2026-10-18): the attempt
    waits and repeats only while Maya's UI runs and its main window does not stand yet
    (RESTORE_TRIES, a Maya still starting up)."""
    st = _state()
    st["queued"] = False
    try:
        pending = [key for key in remembered_keys() if not is_open(key)]
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return []
    if not pending:
        return []
    if _main_window() is None and hubqt._maya_ui_ok():
        st["tries"] += 1
        if st["tries"] <= RESTORE_TRIES:
            _retry_later()
        return []
    opened = []
    st["restoring"] = True
    try:
        for key in pending:
            try:
                if open_popup(key) is not None:
                    opened.append(key)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
    finally:
        st["restoring"] = False
        _save_open()
    return opened


def _retry_later():
    try:
        q = hubqt.qt()
        q.QtCore.QTimer.singleShot(RESTORE_MS, restore_later)
    except Exception:                                        # noqa: BLE001
        pass


# ------------------------------------------------------------ the rest

def _defer_close(key):
    """The close pill's press: deferred - it comes from inside the window
    the close deletes - and folded into the cursor where it was pressed (2026-10-17)."""
    point = _cursor_point()
    cmds.evalDeferred(lambda: close_popup(key, animate=True, origin=point),
                      lowestPriority=True)


def _notify(key, on):
    """The hub told a window opened or closed (one closed by its own pill too): the card's
    button lit or dark (`paint_popped`) and the rail's dot (`paint_floating`, 2026-10-18).
    Each asked on its own: a hub without one still hears the other."""
    try:
        _hub().paint_popped(key, on)
    except Exception:                                        # noqa: BLE001
        pass
    try:
        _hub().paint_floating(key, on)
    except Exception:                                        # noqa: BLE001
        pass
