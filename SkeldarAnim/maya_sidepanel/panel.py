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
GRIP = "skeldarSidePanelGrip"


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
QWidget#{grip} {{ background: transparent; border-left: 1px solid {inset_line}; }}
""".format(panel=PANEL, header=HEADER, pin=PIN, grip=GRIP, panel_c=t["panel"], line=t["line"],
           track=t["track"], track_edge=t["track_edge"], muted=t["muted"], hover=t["hover"],
           text=t["text"], thumb=t["thumb"], accent=t["accent"], accent_tint=t["accent_tint"],
           accent_text=t["accent_text"], inset_line=t["inset_line"],
           r=px(5), pad=px(10), h=px(22), fs=px(11.5))


def make(parent, ui=1.0, tokens=None, motion=True, on_tab=None, on_pin=None, on_width=None):
    q = hubqt.qt()
    QtCore, QtWidgets = q.QtCore, q.QtWidgets
    tokens = tokens or hubstyle.TOKENS

    class Grip(QtWidgets.QWidget):
        def __init__(self, owner):
            QtWidgets.QWidget.__init__(self, owner)
            self.setObjectName(GRIP)
            self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            self.setCursor(QtCore.Qt.SizeHorCursor)
            self.start = None

        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.LeftButton:
                self.start = event.globalPosition().toPoint().x()

        def mouseMoveEvent(self, event):
            if self.start is not None and on_width is not None:
                on_width(event.globalPosition().toPoint().x() - self.start, False)

        def mouseReleaseEvent(self, event):
            if self.start is not None and on_width is not None:
                on_width(event.globalPosition().toPoint().x() - self.start, True)
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
            column.addWidget(header)
            self.header = header

            self.stack = QtWidgets.QStackedWidget(self)
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
