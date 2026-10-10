"""maya_hubpop - a section's copy in a popup window over the active viewport.

2026-10-09 (spec: docs/superpowers/specs/2026-10-09-hub-section-popups-design.md).
The animator: «для каждого из наших разделов ... кнопочка которая открывает
копию раздела в окне вьюпорта ... перетаскивать эти попапы в пределах рабочего
окна ... всегда следовали за окном».

Each popup is a second build of a section (maya_hubcopy: its controls and
callbacks run in a scope of their own) in a frameless Qt.Tool window owned by
Maya's main window - the edge panel's pattern (maya_hubedge): above Maya, not
above another application, gone with Maya when minimised. Inside, a card-like
frame: the section's icon and name, a roll-up and a close button, and a scroll
area holding the section's controls.

The review of the first design (2026-10-09, the same day): the window is see-
through, so the card's rounded corners show the viewport and not a dark square;
a rolled-up popup is its name alone; an expanded one is at most
rules.MAX_HEIGHT tall and scrolls; opening, closing and rolling slide and fade
(maya_hubmotion POPUP_*); a popup lights up under the mouse as a card does.

The second pass of the review (2026-10-09, the same day): a rolled-up popup is as
wide as its name; its edges drag to resize - the right edge the width, the bottom
the height, the corner both; a double click gives a side back to automatic. The
sizes are remembered per section (maya_hubpop_rules: SIZE_VAR, BAR_VAR).

Its place is an offset from its viewport's top-left (maya_hubpop_rules: the
clamp, the cascade, the stored text). A drag of the title row moves it and is
clamped to the viewport's GL rectangle, so it cannot be carried onto another
monitor; a 20 Hz timer keeps it on the viewport when Maya's window moves, and
hides it while its panel is not visible.

The state lives on `sys` (trap 111: an install purges our modules, and the
popups must find the windows an older module object opened, to destroy them).
Qt is imported lazily through maya_hubqt; the hub is imported lazily here too
(maya_hub imports this module for its header button).
"""

import sys
import traceback

import maya.cmds as cmds

import maya_hubcopy as hubcopy
import maya_hubmotion as hubmotion
import maya_hubpop_rules as rules
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle

FOLLOW_MS = 50            # the viewport is followed 20 times a second
RESTORE_MS = 500          # a restore with no 3D view yet waits this long
RESTORE_TRIES = 60        # ... and gives up after this many tries (30 s)

_CLASSES = {}


def _state():
    """The popups standing (by key, in opening order), the ones fading shut,
    the follow timer and the restore's bookkeeping. On `sys` (trap 111)."""
    st = getattr(sys, "_skeldar_hubpop", None)
    if st is None:
        st = {"popups": {}, "timer": None, "queued": False, "tries": 0,
              "restoring": False}
        sys._skeldar_hubpop = st
    st.setdefault("closing", [])
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


GL_CLASS = "QmayaGLWidget"     # the model panel's native GL surface


def model_panels():
    """Every visible model panel, in Maya's own order."""
    visible = cmds.getPanel(visiblePanels=True) or []
    return [panel for panel in visible
            if (cmds.getPanel(typeOf=panel) or "") == "modelPanel"]


def active_panel():
    """The focused model panel, else the first visible one, else None - where
    a new popup goes (2026-10-09, «добавляется в активное окно»)."""
    panels = model_panels()
    if not panels:
        return None
    try:
        focus = cmds.getPanel(withFocus=True)
    except Exception:                                        # noqa: BLE001
        focus = None
    return focus if focus in panels else panels[0]


def _gl_rect(panel):
    """The panel's GL surface as (x, y, w, h) in global pixels, read while the
    panel's wrapper is held and never handed out (trap 96)."""
    q = hubqt.qt()
    try:
        import maya.OpenMayaUI as omui
        pointer = omui.MQtUtil.findControl(panel)
        if not pointer or q is None:
            return None
        holder = q.shiboken.wrapInstance(int(pointer), q.QtWidgets.QWidget)
        for child in holder.findChildren(q.QtWidgets.QWidget):
            try:
                if (child.metaObject().className() != GL_CLASS
                        or not child.isVisible()):
                    continue
                corner = child.mapToGlobal(q.QtCore.QPoint(0, 0))
                return (corner.x(), corner.y(), child.width(), child.height())
            except RuntimeError:          # a widget Maya deleted mid-walk
                continue
    except Exception:                                        # noqa: BLE001
        return None
    return None


def _rect_of(panel):
    """The panel's GL surface (x, y, w, h) in global pixels while the panel is
    visible, else None."""
    if not panel or panel not in model_panels():
        return None
    return _gl_rect(panel)


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
    """A QVariantAnimation with no Qt parent: the popup keeps it and stops it
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


def _popup_frame_class():
    """The popup's card frame (2026-10-09, «улучшим визуал рамки»): the card's
    own paint (its light and its group's stripe) and, over it, a 1 px outline
    in the hub's line colour, rounded like the card, a 2 px accent along the
    top in the section's group colour, and a hairline under the title row. The
    outline is painted, not a stylesheet border: a border would take layout
    space the popup must not waste."""
    if "frame" not in _CLASSES:
        q = hubqt.qt()
        base = hubqt._frame_class()

        class PopupFrame(base):

            def __init__(self, scale=1.0, parent=None):
                super(PopupFrame, self).__init__(scale, parent)
                self.title = None
                self.accent = None

            def paintEvent(self, event):                   # noqa: N802
                super(PopupFrame, self).paintEvent(event)
                _paint_outline(self, q)

        _CLASSES["frame"] = PopupFrame
    return _CLASSES["frame"]


def _paint_outline(frame, q):
    """The outline, the accent and the title's hairline of a popup frame. The
    grey outline fades as the light comes up (2026-10-09): the orange ring takes
    its place, as a lit card's does."""
    s = frame.scale
    painter = q.QtGui.QPainter(frame)
    try:
        painter.setRenderHint(q.QtGui.QPainter.Antialiasing, True)
        radius = float(hubstyle.px(8, s))
        line = q.QtGui.QColor(hubstyle.TOKENS["line"])
        line.setAlphaF(max(0.0, 1.0 - float(getattr(frame, "level", 0.0))))
        pen = q.QtGui.QPen(line)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(q.QtCore.Qt.NoBrush)
        box = q.QtCore.QRectF(frame.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.drawRoundedRect(box, radius, radius)
        if frame.accent:
            top = q.QtCore.QRectF(radius, 0.0, box.width() - 2 * radius,
                                  float(hubstyle.px(2, s)))
            painter.fillRect(top, q.QtGui.QColor(frame.accent))
        if frame.title is not None:
            y = frame.title.geometry().bottom() + 1
            hairline = q.QtGui.QColor(hubstyle.TOKENS["inset_line"])
            pen.setColor(hairline)
            painter.setPen(pen)
            painter.drawLine(q.QtCore.QPointF(box.left() + radius / 2.0, y),
                             q.QtCore.QPointF(box.right() - radius / 2.0, y))
    finally:
        painter.end()


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
    """One section's popup: its scope, its window and the place it stands."""

    def __init__(self, key, sec, panel, scale):
        self.key = key
        self.sec = sec
        self.panel = panel
        self.scale = scale
        self.scope = None
        self.root = None
        self.title = None
        self.subtitle_slot = None
        self.scroll = None
        self.content = None
        self.body = None
        self.offset = None        # logical, from the viewport's top-left
        self.grab = None          # a drag's cursor offset in the window
        self.hidden = False
        self.frame = None
        self.column = None
        self.roll = None          # the roll-up button in the title row
        self.collapsed = False    # rolled up to its name (2026-10-09)
        self.slide = 0.0          # physical px still offset down while opening
        self._hover = None        # the window's Enter / Leave watcher
        self._light_anim = None   # the card light fading (frame.level)
        self._roll_anim = None    # the window sliding to its rolled height
        self._open_anim = None    # the window fading and rising in
        self._fade = None         # the window fading out (closing)
        self.user_w = None        # the width the animator dragged (logical; None = automatic)
        self.user_h = None        # the height dragged, unrolled (logical; None = automatic)
        self.bar_w = None         # a rolled-up popup's width dragged (logical; None = its name's)
        self.grips = []           # the edge strips: right, bottom, corner (2026-10-09)
        self._grip_start = None   # a resize drag in progress: (point, w, h, viewport rect)

    # ------------------------------------------------------------ state

    def alive(self):
        q = hubqt.qt()
        if self.root is None or q is None:
            return False
        try:
            return bool(q.shiboken.isValid(self.root))
        except Exception:                                    # noqa: BLE001
            return False

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
        #  See-through (2026-10-09): the card's rounded corners show the
        #  viewport. The root is a plain QWidget, whose stylesheet background
        #  is not drawn - the palette's is, and that was the dark square
        #  behind the corners.
        root.setAttribute(Qt.WA_TranslucentBackground, True)
        outer = w.QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        #  the card's frame; its border is the painted outline's (see
        #  _popup_frame_class), so the frame is exactly its content
        frame = hubqt._named(_popup_frame_class()(s),
                             "skeldarAnimPopupFrame_" + tag)
        frame.setProperty("skCard", True)
        colour = hubstyle.group(self.sec.group).colour
        frame.stripe = colour
        frame.accent = colour
        outer.addWidget(frame)
        self.frame = frame
        column = w.QVBoxLayout(frame)
        #  the least height around the title (2026-10-09, «короче»)
        column.setContentsMargins(px(3), px(2), px(3), px(2))
        column.setSpacing(0)
        self.column = column

        self.title = hubqt._named(
            _title_class()(self._grab, self._drag, self._drop,
                           lambda: self.toggle_roll(animate=True), root),
            "skeldarAnimPopupTitle_" + tag, "cardhead")
        frame.title = self.title
        self.title.setSizePolicy(w.QSizePolicy.Preferred,
                                 w.QSizePolicy.Fixed)
        row = w.QHBoxLayout(self.title)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(px(5))
        chip_label = w.QLabel()
        chip_label.setFixedSize(px(16), px(16))
        chip_label.setAlignment(Qt.AlignCenter)
        chip_label.setPixmap(hubqt.pixmap(self.sec.icon, colour, px(11)))
        chip_label.setStyleSheet("background: {0}; border-radius: {1}px;"
                                 .format(hubstyle.group(self.sec.group).chip,
                                         px(4)))
        title_label = hubqt._named(w.QLabel(self.sec.label),
                                   "skeldarAnimPopupName_" + tag, "cardtitle")
        self.subtitle_slot = hubqt._named(w.QWidget(),
                                          "skeldarAnimPopupSub_" + tag)
        self.subtitle_slot.setSizePolicy(w.QSizePolicy.Ignored,
                                         w.QSizePolicy.Preferred)
        sub = w.QHBoxLayout(self.subtitle_slot)
        sub.setContentsMargins(0, 0, 0, 0)
        close = hubqt._named(w.QToolButton(), "skeldarAnimPopupClose_" + tag,
                             "popclose")
        close.setIcon(hubqt.icon("x", hubstyle.TOKENS["muted"], px(12)))
        close.setIconSize(q.QtCore.QSize(px(12), px(12)))
        close.setAutoRaise(True)
        close.setFixedSize(px(18), px(16))
        close.setCursor(Qt.PointingHandCursor)
        close.setToolTip("Close the popup - the section stays in the hub")
        close.clicked.connect(lambda *_a, k=self.key: _defer_close(k))
        #  roll up / unroll (2026-10-09): the chevron as the card's own, down
        #  while open, right while rolled up; a click on the name does the same
        self.roll = hubqt._named(w.QToolButton(),
                                 "skeldarAnimPopupRoll_" + tag, "poproll")
        self.roll.setAutoRaise(True)
        self.roll.setFixedSize(px(18), px(16))
        self.roll.setCursor(Qt.PointingHandCursor)
        self.roll.clicked.connect(lambda *_a: self.toggle_roll(animate=True))
        row.addWidget(chip_label)
        row.addWidget(title_label)
        row.addWidget(self.subtitle_slot, 1)
        row.addWidget(self.roll)
        row.addWidget(close)
        column.addWidget(self.title)
        self._paint_roll()

        self.scroll = w.QScrollArea()
        #  its own name (2026-10-09): the hub's scroll area is found by its
        #  name, and a popup's must not be
        self.scroll.setObjectName("skeldarAnimPopupScroll_" + tag)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(w.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #  a roll slides the scroll area to nothing, so it has no minimum
        self.scroll.setMinimumHeight(0)
        #  the viewport paints nothing: the card's face shows through it
        self.scroll.viewport().setAutoFillBackground(False)
        self.content = hubqt._named(w.QWidget(),
                                    "skeldarAnimPopupBody_" + tag, "popbody")
        self.body = w.QVBoxLayout(self.content)
        self.body.setObjectName("skeldarAnimPopupBodyLayout_" + tag)
        self.body.setContentsMargins(0, px(2), 0, 0)
        self.body.setSpacing(0)
        self.scroll.setWidget(self.content)
        column.addWidget(self.scroll, 1)

        sheet = hubstyle.stylesheet(s, arrow=_arrow())
        #  the card's own 2 px border is the painted outline's (see
        #  _popup_frame_class): none here, so the frame is exactly its content;
        #  the scroll area and its body paint nothing of their own
        root.setStyleSheet(
            sheet
            + "\n#{0} {{ border: none; }}\n"
              "QScrollArea#{1} {{ background: transparent; border: none; }}\n"
              "#{2} {{ background: transparent; }}".format(
                  frame.objectName(), self.scroll.objectName(),
                  self.content.objectName()))
        self.root = root
        #  the light: the window's Enter and Leave (2026-10-09, as a card's)
        self._hover = _hover_class()(self._on_hover, root)
        root.installEventFilter(self._hover)
        #  the edges a drag resizes (2026-10-09, «изменять размер перетягивая за край»):
        #  thin strips above the frame - right (the width), bottom (the height), corner
        #  (both); a rolled-up popup has its right strip only (_place_grips)
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
        self.scroll.setVisible(not self.collapsed)
        self._paint_roll()
        self._fit()

    def _chrome(self):
        """The height that is not the section: the title row and the frame's
        own margins (2026-10-09)."""
        margins = self.column.contentsMargins()
        return margins.top() + margins.bottom() + self.title.sizeHint().height()

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
            self.content.minimumSizeHint().width(), hint.height(), rect,
            self.scale, self._chrome(), collapsed=self.collapsed,
            scrollbar_w=hubstyle.px(12, self.scale),
            title_w=self._title_width(), user_w=user_w, user_h=user_h)

    def _fit(self, keep_place=False):
        """The window's size (2026-10-09, «минимум лишнего места»): the
        section's own natural size, within its viewport's rect and the cap -
        rolled up, the title row alone. `keep_place`: a roll-up or unroll keeps
        the window where it stands, clamped into the viewport (the offset is what
        is remembered, so it comes back when there is room). With no panel
        known, the section's size alone."""
        panel_rect = _rect_of(self.panel)
        rect = panel_rect or (0, 0, 10000, 10000)
        w, h = self._target(rect)
        #  The window's minimum is the layout's, and it is updated when Maya's
        #  event loop runs: a roll-up measured in the same send kept the expanded
        #  minimum and a 110 px window for a 38 px title row (2026-10-09). It is
        #  cleared first, so this resize is the one taken; the layout sets its own
        #  minimum again.
        self._set_size(w, h)
        if keep_place and panel_rect is not None:
            self._place_at(panel_rect)

    def _title_width(self):
        """The title row's own width with the frame's side margins: the width a
        rolled-up popup takes to show its name (2026-10-09)."""
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
        """A resize drag's press (`start`: the window's size and the viewport are
        taken then) and its moves: the new size from the cursor, bounded by
        rules.bounds, so the far edges stay inside the viewport. The size is the
        window's own memory, logical (2026-10-09)."""
        if self.root is None:
            return
        if start:
            self._settle()
            rect = _rect_of(self.panel)
            if rect is None:
                self._grip_start = None
                return
            self._grip_start = (point, self.root.width(), self.root.height(), rect)
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
            self.content.minimumSizeHint().width(), rect, self.scale,
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

    def _place_at(self, rect):
        """The window at its offset in `rect` - moved down by the opening's
        slide while that runs - clamped inside the viewport. Moved only when
        it is not already there."""
        if self.root is None or self.offset is None:
            return
        w, h = self.root.width(), self.root.height()
        x, y = rules.origin_of(self.offset, rect, w, h, self.scale)
        x, y = rules.clamp_origin(x, y + self.slide, w, h, rect)
        pos = self.root.pos()
        if (pos.x(), pos.y()) != (x, y):
            self.root.move(x, y)

    def set_collapsed(self, on, remember=True, animate=False):
        """Roll the popup up to its name, or unroll it (2026-10-09). `animate`
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
                if self.scroll is not None:
                    self.scroll.setVisible(not on)
                self._fit(keep_place=True)
        if remember:
            _save_collapsed(self.key, on)
        return on

    def _roll_to(self, on):
        """The window slides to its rolled height or its unrolled one (2026-10-09,
        «плавная анимация»): its height eased from where it stands, its top kept,
        the scroll area shown while it opens and hidden once it has shut. The
        target is measured once, at the start."""
        self._stop_anim("_roll_anim")
        rect = _rect_of(self.panel)
        if rect is None:
            self.scroll.setVisible(not on)
            self._fit(keep_place=True)
            return
        if not on:
            self.scroll.setVisible(True)
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
            self._place_at(rect)

        def done():
            self._roll_anim = None
            self._roll_done(on)

        anim.valueChanged.connect(tick)
        anim.finished.connect(done)
        self._roll_anim = anim
        anim.start()

    def _roll_done(self, on):
        """The end of a roll: a shut popup's scroll area hidden, its size exact."""
        if self.root is None:
            return
        if on and self.scroll is not None:
            self.scroll.setVisible(False)
        self._fit(keep_place=True)

    def toggle_roll(self, animate=False):
        """The roll-up button's press, or a click on the title row (animated
        there). Answers the new state."""
        return self.set_collapsed(not self.collapsed, animate=animate)

    def _paint_roll(self):
        """The chevron as the hub's cards draw theirs: down while open, right
        while rolled up."""
        if self.roll is None:
            return
        q = hubqt.qt()
        name = "chevron-right" if self.collapsed else "chevron-down"
        size = hubstyle.px(12, self.scale)
        self.roll.setIcon(hubqt.icon(name, hubstyle.TOKENS["muted"], size))
        self.roll.setIconSize(q.QtCore.QSize(size, size))
        self.roll.setToolTip("Unroll" if self.collapsed
                             else "Roll up to the name")

    # ------------------------------------------------------- open and close

    def show_open(self, rect, animate=False):
        """Show the window (2026-10-09): at once, or fading in and rising
        POPUP_SLIDE logical px into its place (POPUP_OPEN_MS)."""
        self._stop_anim("_open_anim")
        self.slide = 0.0
        self.root.setWindowOpacity(1.0)
        if not animate:
            self.root.show()
            return
        slide = float(hubstyle.px(hubmotion.POPUP_SLIDE, self.scale))
        self.slide = slide
        self.root.setWindowOpacity(0.0)
        self.root.show()
        self._place_at(rect)
        anim = _animation(0.0, 1.0, hubmotion.POPUP_OPEN_MS)

        def tick(value):
            if self.root is None:
                return
            k = hubmotion.ease(value)
            self.root.setWindowOpacity(k)
            self.slide = (1.0 - k) * slide
            self._place_at(rect)

        def done():
            self._open_anim = None
            if self.root is not None:
                self.slide = 0.0
                self.root.setWindowOpacity(1.0)
                self._place_at(rect)

        anim.valueChanged.connect(tick)
        anim.finished.connect(done)
        self._open_anim = anim
        anim.start()

    def fade_out(self, done):
        """Fade the window out (2026-10-09, POPUP_CLOSE_MS), then call `done`.
        Its controls take no press meanwhile."""
        self._stop_anim("_open_anim")
        self._stop_anim("_roll_anim")
        if self.root is None:
            done()
            return
        q = hubqt.qt()
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

    def _on_hover(self, entered):
        self.set_light(entered, animate=hubmotion.enabled())

    # ------------------------------------------------------------ place

    def place(self, rect, index=None):
        """Put the window at its offset (or the default for `index`), inside
        `rect`. The offset is stored."""
        if self.offset is None:
            w, h = self.root.width(), self.root.height()
            self.offset = rules.default_offset(index or 0, rect, w, h,
                                               self.scale)
        self._place_at(rect)

    def follow(self):
        """The viewport moved, or its panel hid: the window goes with it (or
        hides); a drag in progress moves it itself."""
        if not self.alive():
            return
        rect = _rect_of(self.panel)
        if rect is None:
            if not self.hidden:
                self.root.hide()
                self.hidden = True
            return
        if self.hidden:
            self.root.show()
            self.hidden = False
        if self.grab is not None or self.offset is None:
            return
        self._place_at(rect)

    # ------------------------------------------------------------- drag

    def _grab(self, point):
        self._settle()
        pos = self.root.pos()
        self.grab = (point[0] - pos.x(), point[1] - pos.y())

    def _settle(self):
        """Finish an opening or a roll at once: a drag takes the window."""
        if self.root is None:
            return
        if self._open_anim is not None:
            self._stop_anim("_open_anim")
            self.slide = 0.0
            self.root.setWindowOpacity(1.0)
            rect = _rect_of(self.panel)
            if rect is not None:
                self._place_at(rect)
        if self._roll_anim is not None:
            self._stop_anim("_roll_anim")
            self._roll_done(self.collapsed)

    def _drag(self, point):
        if self.grab is None:
            return
        rect = _rect_of(self.panel)
        if rect is None:
            return
        w, h = self.root.width(), self.root.height()
        x, y = rules.clamp_origin(point[0] - self.grab[0],
                                  point[1] - self.grab[1], w, h, rect)
        self.root.move(x, y)
        self.offset = rules.offset_of(x, y, rect, self.scale)

    def _drop(self):
        if self.grab is None:
            return
        self.grab = None
        if self.offset is not None:
            _save_offset(self.key, self.offset)

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
        for slot in ("_light_anim", "_roll_anim", "_open_anim", "_fade"):
            self._stop_anim(slot)

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


def open_popup(key, offset=None, animate=False):
    """Open section `key`'s popup in the ACTIVE viewport (the focused model
    panel, else the first visible one). The popup it returns, or None when
    there is no viewport to put it in (said on the hub's line). `animate`: it
    fades in and rises (the header button's press); the restore opens them at
    once."""
    st = _state()
    if is_open(key):
        return st["popups"][key]
    hub = _hub()
    sec = hub.section(key)
    if sec is None or sec.key in hub.HEADER_ONLY:
        raise KeyError("no popup for section '{0}'".format(key))
    panel = active_panel()
    rect = _rect_of(panel)
    if rect is None:
        _say("{0}: no 3D view to open it in - open a viewport".format(
            sec.label))
        return None
    popup = Popup(key, sec, panel, _scale())
    try:
        popup.build()
        #  the place remembered from the last drag, when the caller names none
        #  (2026-10-09: a popup opened by its button comes back where it was)
        popup.offset = offset if offset is not None else stored_offset(key)
        popup.place(rect, index=len(open_keys()))
        popup.show_open(rect, animate=animate and hubmotion.enabled())
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        popup.destroy()
        raise
    st["popups"][key] = popup
    _ensure_timer()
    if not st["restoring"]:
        _save_open()
    _notify(key, True)
    return popup


def close_popup(key, forget=True, animate=False):
    """Close section `key`'s popup. `animate` (the header button's and the
    close button's press): it fades out first, and it is gone from the hub's
    list at once. `forget`: it stays closed after a restart (the close button
    and the hub's press); False when an install destroys it - the next startup
    brings it back."""
    st = _state()
    popup = st["popups"].pop(key, None)
    if popup is not None:
        if animate and hubmotion.enabled() and popup.alive() \
                and popup.root.isVisible():
            st["closing"].append(popup)
            popup.fade_out(lambda: _later(lambda: _finish_closing(popup)))
        else:
            popup.destroy()
    if not st["popups"]:
        _stop_timer()
    if forget:
        _save_open()
    _notify(key, False)
    return popup is not None


def _finish_closing(popup):
    """A popup that faded out is destroyed (2026-10-09)."""
    st = _state()
    if popup in st["closing"]:
        st["closing"].remove(popup)
    popup.destroy()


def toggle(key):
    """The header button's press: open (fading in), or close (fading out) when
    open. True when open now."""
    if is_open(key):
        close_popup(key, animate=True)
        return False
    return open_popup(key, animate=True) is not None


def destroy_all(forget=False):
    """Every popup destroyed: ours, the ones fading out, and any an older module
    object opened (found by objectName - trap 102's family). `forget` as
    close_popup. Returns how many."""
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
    _stop_timer()
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
    popups an older one opened go, the remembered ones come back (deferred,
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


def stored_offset(key):
    var = rules.POS_VAR.format(key)
    if not cmds.optionVar(exists=var):
        return None
    return rules.decode_offset(cmds.optionVar(query=var))


def _save_open():
    cmds.optionVar(stringValue=(rules.POPUPS_VAR,
                                rules.encode_keys(open_keys())))


def _save_offset(key, offset):
    cmds.optionVar(stringValue=(rules.POS_VAR.format(key),
                                rules.encode_offset(offset)))


def stored_size(key):
    """The unrolled popup's size the animator dragged: (w, h) logical, None for a
    side that is automatic (2026-10-09)."""
    var = rules.SIZE_VAR.format(key)
    if not cmds.optionVar(exists=var):
        return (None, None)
    return rules.decode_pair(str(cmds.optionVar(query=var)))


def stored_bar(key):
    """A rolled-up popup's width the animator dragged, logical; None = it fits its
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
    """Whether section `key`'s popup was left rolled up (2026-10-09). False
    when nothing is remembered."""
    var = rules.COLLAPSED_VAR.format(key)
    if not cmds.optionVar(exists=var):
        return False
    return bool(rules.decode_flag(str(cmds.optionVar(query=var))))


def _save_collapsed(key, on):
    cmds.optionVar(stringValue=(rules.COLLAPSED_VAR.format(key),
                                rules.encode_flag(on)))


def restore_later():
    """Queue the restore of the remembered popups, deferred and once. The mark
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
    """Open the remembered popups. With no 3D view yet, the attempt waits and
    repeats (RESTORE_TRIES, a Maya still starting up)."""
    st = _state()
    st["queued"] = False
    try:
        pending = [key for key in remembered_keys() if not is_open(key)]
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return []
    if not pending:
        return []
    if active_panel() is None:
        st["tries"] += 1
        if st["tries"] <= RESTORE_TRIES:
            _retry_later()
        return []
    opened = []
    st["restoring"] = True
    try:
        for key in pending:
            try:
                if open_popup(key, offset=stored_offset(key)) is not None:
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


# -------------------------------------------------------------- the timer

def _ensure_timer():
    st = _state()
    if st["timer"] is not None:
        return
    q = hubqt.qt()
    timer = q.QtCore.QTimer()
    timer.setInterval(FOLLOW_MS)
    timer.timeout.connect(_tick)
    timer.start()
    st["timer"] = timer


def _stop_timer():
    st = _state()
    timer = st["timer"]
    st["timer"] = None
    if timer is not None:
        timer.stop()


def _tick():
    for popup in list(_state()["popups"].values()):
        try:
            popup.follow()
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()


# ------------------------------------------------------------ the rest

def _defer_close(key):
    """The close button's press: deferred - it comes from inside the window
    the close deletes - and faded (2026-10-09)."""
    cmds.evalDeferred(lambda: close_popup(key, animate=True),
                      lowestPriority=True)


def _notify(key, on):
    """The hub's card button lit or dark (a popup closed by its own button
    too)."""
    try:
        _hub().paint_popped(key, on)
    except Exception:                                        # noqa: BLE001
        pass


def _say(message):
    try:
        _hub().say(message)
    except Exception:                                        # noqa: BLE001
        print("SkeldarAnim: " + message)
