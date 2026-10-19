"""The side panel's own widget (Qt): a header in the hub's look - the tabs
[Channels | Attributes] and the 📌 - a page per tab holding Maya's borrowed
editors, and a grip on the inner (left) edge to drag the width.

Our stylesheet reaches only the header (scoped by objectName): Maya's editors in
the pages keep Maya's own look.
"""

import maya_hubqt as hubqt
import maya_hubstyle as hubstyle

from . import look

PANEL = "skeldarSidePanel"
HEADER = "skeldarSidePanelHeader"
PIN = "skeldarSidePanelPin"
CLOSE = "skeldarSidePanelClose"
GRIP = "skeldarSidePanelGrip"
HEIGHT_GRIP = "skeldarSidePanelHeightGrip"


def tab_name(tab):
    return "skeldarSidePanelTab_" + tab


def sheet(ui, tokens):
    t = tokens

    def px(v):
        return "%dpx" % max(1, int(round(v * ui)))
    return """
QWidget#{panel} {{ background: {panel_c}; }}
QWidget#{header} {{ background: {panel_c}; border-bottom: 1px solid {line}; }}
QWidget#{header} QPushButton {{
    background: {track}; color: {muted}; border: 1px solid {track_edge};
    border-radius: {r}; padding: 0 {pad}; min-height: {h}; font-size: {fs};
}}
QWidget#{header} QPushButton:hover {{ background: {hover}; color: {text}; }}
QWidget#{header} QPushButton:checked {{
    background: {thumb}; color: {text}; font-weight: bold; border-color: {line};
}}
QPushButton#{pin}:checked {{ background: {accent_tint}; color: {accent_text}; border-color: {accent}; }}
QPushButton#{close}:hover {{ background: {danger_tint}; color: {danger}; }}
QWidget#{grip} {{ background: transparent; border-left: 1px solid {inset_line}; }}
QWidget#{hgrip} {{ background: transparent; border-top: 1px solid {inset_line}; }}
QWidget#{hgrip}:hover {{ background: {accent_tint}; }}
""".format(panel=PANEL, header=HEADER, pin=PIN, close=CLOSE, grip=GRIP, hgrip=HEIGHT_GRIP,
           panel_c=t["panel"], line=t["line"],
           danger=t["danger"], danger_tint=t["danger_tint"],
           track=t["track"], track_edge=t["track_edge"], muted=t["muted"], hover=t["hover"],
           text=t["text"], thumb=t["thumb"], accent=t["accent"], accent_tint=t["accent_tint"],
           accent_text=t["accent_text"], inset_line=t["inset_line"],
           r=px(5), pad=px(10), h=px(22), fs=px(11.5))


def name_layouts(root, prefix="skeldarSidePanelLayout"):
    """Every unnamed QLayout of OUR widgets under `root` (the host) named. Maya builds a
    control's path through the QLayouts above it, and an unnamed one is an empty
    segment: `skeldarSidePanelHost|||||MainAttributeEditorLayout` could not be set as
    a parent, and an Attribute Editor section expanded in the panel built its
    controls under the editor's bottom buttons instead (2026-10-17, live). Maya's own
    layouts inside the borrowed forms are left as they are. Returns how many."""
    q = hubqt.qt()
    named = 0
    for layout in [root.layout()] + root.findChildren(q.QtWidgets.QLayout):
        try:
            if layout is None or layout.objectName():
                continue
            owner = layout.parentWidget()
            if owner is None or not owner.objectName().startswith("skeldarSidePanel"):
                continue
            named += 1
            layout.setObjectName("%s%d" % (prefix, named))
        except RuntimeError:
            pass
    return named


def make(parent, ui=1.0, tokens=None, motion=True, on_tab=None, on_pin=None, on_width=None,
         on_height=None):
    q = hubqt.qt()
    QtCore, QtWidgets = q.QtCore, q.QtWidgets
    tokens = tokens or hubstyle.TOKENS

    class Grip(QtWidgets.QWidget):
        """The width grip (left edge, x) or the height grip (bottom edge, y). The
        handler is looked up at each move: the edge may set the height's later."""
        def __init__(self, owner, vertical=False):
            QtWidgets.QWidget.__init__(self, owner)
            self.vertical = bool(vertical)
            self.setObjectName(HEIGHT_GRIP if vertical else GRIP)
            self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            self.setCursor(QtCore.Qt.SizeVerCursor if vertical else QtCore.Qt.SizeHorCursor)
            self.start = None

        def _at(self, event):
            p = event.globalPosition().toPoint()
            return p.y() if self.vertical else p.x()

        def _call(self, event, done):
            owner = self.parentWidget()
            handler = getattr(owner, "on_height", None) if self.vertical else on_width
            if self.start is not None and handler is not None:
                handler(self._at(event) - self.start, done)

        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.LeftButton:
                self.start = self._at(event)

        def mouseMoveEvent(self, event):
            self._call(event, False)

        def mouseReleaseEvent(self, event):
            self._call(event, True)
            self.start = None

    class SidePanel(QtWidgets.QWidget):
        def __init__(self):
            QtWidgets.QWidget.__init__(self, parent)
            self.setObjectName(PANEL)
            self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            self.ui = float(ui)
            self.motion = bool(motion)
            self._clock = QtCore.QElapsedTimer()
            self._clock.start()
            self.setStyleSheet(sheet(self.ui, tokens))
            outer = QtWidgets.QHBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
            self.grip = Grip(self)
            self.grip.setFixedWidth(max(2, int(round(look.GRIP * self.ui))))
            outer.addWidget(self.grip)
            column = QtWidgets.QVBoxLayout()
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(0)
            outer.addLayout(column, 1)

            header = QtWidgets.QWidget(self)
            header.setObjectName(HEADER)
            header.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            header.setFixedHeight(int(round(look.HEADER * self.ui)))
            row = QtWidgets.QHBoxLayout(header)
            m = int(round(4 * self.ui))
            row.setContentsMargins(m, m, m, m)
            row.setSpacing(int(round(3 * self.ui)))
            self.tabs = {}
            for label, tab in look.TAB_LABELS:
                button = QtWidgets.QPushButton(label, header)
                button.setObjectName(tab_name(tab))
                button.setCheckable(True)
                button.setFocusPolicy(QtCore.Qt.NoFocus)
                button.clicked.connect(lambda checked=False, t=tab: self._pick(t))
                row.addWidget(button)
                self.tabs[tab] = button
            row.addStretch(1)
            self.pin = QtWidgets.QPushButton("\U0001F4CC", header)
            self.pin.setObjectName(PIN)
            self.pin.setCheckable(True)
            self.pin.setFocusPolicy(QtCore.Qt.NoFocus)
            self.pin.setToolTip("Keep the side panel out")
            self.pin.toggled.connect(lambda on: on_pin(on) if on_pin else None)
            row.addWidget(self.pin)
            #  2026-10-17: the panel no longer hides by itself while the Time Bar is
            #  out, so a press must be able to send it away
            self.close_button = QtWidgets.QPushButton("✕", header)
            self.close_button.setObjectName(CLOSE)
            self.close_button.setFocusPolicy(QtCore.Qt.NoFocus)
            self.close_button.setToolTip("Hide the side panel")
            row.addWidget(self.close_button)
            column.addWidget(header)
            self.header = header

            self.stack = QtWidgets.QStackedWidget(self)
            self.stack.setObjectName("skeldarSidePanelStack")
            self.pages = {}
            for tab in look.TABS:
                page = QtWidgets.QWidget(self.stack)
                page.setObjectName("skeldarSidePanelPage_" + tab)
                layout = QtWidgets.QVBoxLayout(page)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)
                self.stack.addWidget(page)
                self.pages[tab] = layout
            column.addWidget(self.stack, 1)
            self.on_height = on_height
            self.height_grip = Grip(self, vertical=True)
            self.height_grip.setFixedHeight(max(3, int(round(look.GRIP * self.ui))))
            column.addWidget(self.height_grip)
            self.tab = None
            self.set_tab(look.TABS[0])

        def clock(self):
            return float(self._clock.elapsed())

        def _pick(self, tab):
            self.set_tab(tab)
            if on_tab is not None:
                on_tab(tab)

        def set_tab(self, tab):
            tab = look.tab_from(tab)
            self.tab = tab
            for name, button in self.tabs.items():
                button.setChecked(name == tab)
            self.stack.setCurrentIndex(look.TABS.index(tab))

        def set_pinned(self, on):
            blocked = self.pin.blockSignals(True)
            self.pin.setChecked(bool(on))
            self.pin.blockSignals(blocked)

    return SidePanel()
