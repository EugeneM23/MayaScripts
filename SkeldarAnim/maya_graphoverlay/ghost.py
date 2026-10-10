"""The Graph Editor in a window of its own, its background see-through.

The panel is Maya's OWN `graphEditor1`, borrowed for as long as the mode is
on and put back where it lived (its dock, its window, or unparented) when it
ends. Measured 2026-09-30: 55 of Maya's runtime commands name
`graphEditor1GraphEd` outright - Copy/Paste/Delete keys, the view modes,
infinity, frame all/selected, bake, simplify, the smoothness - and the
toolbar, the menus and the hotkeys reach them; in a panel of our own the
Stacked View button switched the animator's Graph Editor instead (read off
the button: `GraphEditorStackedView` = `graphEditorSetViewMode
graphEditor1GraphEd 1`). Borrowed, every one of them acts on the Graph
Editor with the animator's own settings.

2026-10-02 (the animator: «нужен стандартный граф эдитор только с
прозрачным фоном»): the panel lies in a standard window of ours - a title
bar to move it by, borders to resize it, the menu bar, toolbar and channel
list where Maya puts them - not on the whole viewport. Measured on this
construction:

- the curve area is `TanimCurveCanvas`, a QOpenGLWindow named
  `<panel>GraphEdImpl` inside a QWindowContainer - a native child HWND,
  which cannot be made transparent (the canvas clears opaque whatever the
  background alpha);
- the window is made invisible by Qt's OWN window opacity, 1/255 - never by
  setting WS_EX_LAYERED behind Qt's back (Qt rewrote such a style and the
  "invisible" graph stood grey over the viewport, measured 2026-09-30). At
  1/255 it still renders and takes every click, key and drag, title bar
  included;
- what shows is the glass (`glass.py`): DWM's copy of the WHOLE window,
  title bar and borders included (`winstyle.capture`), with the curve area's
  frames keyed out (`keying.py`) where the curve area is - so the background
  goes and the curves, the grid, the chrome stay as Maya draws them.

PySide hands the canvas back as a QPaintDeviceWindow; the cached wrapper is
invalidated and the pointer wrapped as the QOpenGLWindow it is, which is
what reaches `grabFramebuffer()` and `frameSwapped`.
"""

import maya.cmds as cmds
from maya import OpenMayaUI as omui
from PySide6 import QtCore, QtGui, QtOpenGL, QtWidgets
import shiboken6

from maya_graphoverlay import geometry, winstyle

PANEL = "skeldarGraphOverlayPanel"          # our own, when nothing is borrowed
BORROWED = "graphEditor1"                   # Maya's own Graph Editor panel
LIST_WIDTH = 320                            # the channel list, when it was shut
MIN_LIST = 120
LIST_TICKS = 20     # follow ticks (2 s) the list is looked after, then left
HOST = "skeldarGraphOverlayHost"
LAYOUT = "skeldarGraphOverlayLayout"
PANE = "skeldarGraphOverlayPane"
LABEL = "Graph Editor"
CANVAS_CLASS = "TanimCurveCanvas"
CONTAINER_CLASS = "QWindowContainer"
GHOST_OPACITY = winstyle.GHOST_ALPHA / 255.0
GLASS_NAME = "skeldarGraphOverlayGlass"      # glass.NAME, not imported here


def _full_name(qobject):
    return omui.MQtUtil.fullName(int(shiboken6.getCppPointer(qobject)[0]))


def _widget(name):
    pointer = omui.MQtUtil.findControl(name)
    return shiboken6.wrapInstance(int(pointer), QtWidgets.QWidget) \
        if pointer else None


def _control_path(panel):
    try:
        return cmds.scriptedPanel(panel, query=True, control=True) or ""
    except Exception:                                         # noqa: BLE001
        return ""


def home_of(panel):
    """The layout `panel` lives in, or None when it is unparented."""
    control = _control_path(panel)
    if not control:
        return None
    try:
        return cmds.control(control, query=True, parent=True) or None
    except Exception:                                         # noqa: BLE001
        return None


def in_host(panel):
    """Whether `panel` lives in a host of ours right now."""
    return _control_path(panel).startswith(HOST + "|")


def delete_leftovers():
    """A panel of ours a saved scene brought back; a host or a glass an
    older module object built (an install purges modules, not widgets -
    trap 102). Found by name, never by module state. A borrowed
    graphEditor1 left in such a host is unparented first - deleting the
    host would delete Maya's own Graph Editor with it."""
    try:
        if cmds.scriptedPanel(PANEL, exists=True):
            cmds.deleteUI(PANEL, panel=True)
        if cmds.scriptedPanel(BORROWED, exists=True) and in_host(BORROWED):
            cmds.scriptedPanel(BORROWED, edit=True, unParent=True)
    except Exception:                                         # noqa: BLE001
        pass
    app = QtWidgets.QApplication.instance()
    for widget in (app.topLevelWidgets() if app else []):
        try:
            if widget.objectName() in (HOST, GLASS_NAME):
                widget.hide()
                widget.deleteLater()
        except RuntimeError:
            continue


class Ghost(object):
    """The panel, its window, and the canvas wrapper, held together."""

    def __init__(self, parent, rect, borrow=True):
        """`rect` is the window's frame on screen (global pixels). `borrow`:
        Maya's own graphEditor1 rather than a panel of ours (see the
        module)."""
        delete_leftovers()
        self.borrowed = False
        self.home = None            # where the borrowed panel lived
        self.list_sizes = None      # its splitter's sizes, when we opened it
        self._list_ticks = 0
        # A Window, not a Tool: a tool window has only the close button, and
        # no maximise and no double-click on its title (measured 2026-10-10 on
        # the animator's build - the title showed one red button).
        host = QtWidgets.QWidget(parent, QtCore.Qt.Window)
        host.setObjectName(HOST)
        host.setWindowTitle(LABEL)
        host.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        layout = QtWidgets.QVBoxLayout(host)
        layout.setObjectName(LAYOUT)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.host, self.layout = host, layout
        self._canvas = None
        self._canvas_pointer = None
        host.setGeometry(*[int(v) for v in rect])
        # Invisible before it is ever shown: no frame of a grey Graph
        # Editor flashes over the viewport.
        host.setWindowOpacity(GHOST_OPACITY)
        host.show()
        previous = cmds.setParent(query=True)
        cmds.setParent(_full_name(layout))
        pane = cmds.paneLayout(PANE, configuration="single")
        if borrow and cmds.scriptedPanel(BORROWED, exists=True):
            self.home = home_of(BORROWED)
            cmds.scriptedPanel(BORROWED, edit=True, parent=pane)
            self.panel, self.borrowed = BORROWED, True
        else:
            self.panel = cmds.scriptedPanel(PANEL, type="graphEditor",
                                            label=LABEL, parent=pane)
        try:
            cmds.setParent(previous)
        except Exception:                                     # noqa: BLE001
            pass
        # The frame's insets exist only once the window is shown.
        self.place(rect)
        self.open_channel_list()

    # ------------------------------------------------------------ the window

    def frame_rect(self):
        """The window as the animator sees it - title bar and borders, global,
        without Windows' invisible resize border and shadow
        (`winstyle.visible_rect`); Qt's own frame when DWM does not say."""
        seen = winstyle.visible_rect(self.hwnd())
        if seen is not None:
            return seen
        g = self.host.frameGeometry()
        return (g.x(), g.y(), g.width(), g.height())

    def showing(self):
        """On screen: shown, not minimised, and exposed. A minimised Maya
        sends no hide event to a floating window, so `isVisible` alone
        answers True for it (measured 2026-10-01); the window handle is asked
        afresh - a held one can be a dead wrapper (trap 96)."""
        if not self.host.isVisible() or self.host.isMinimized():
            return False
        handle = self.host.windowHandle()
        return handle is not None and handle.isExposed()

    def place(self, rect):
        """The window's FRAME on `rect` (global): the client area is set
        inside it by the insets the window has, measured as it stands."""
        fx, fy, fw, fh = self.frame_rect()
        inner = self.host.geometry()
        left, top = inner.x() - fx, inner.y() - fy
        right = (fx + fw) - (inner.x() + inner.width())
        bottom = (fy + fh) - (inner.y() + inner.height())
        x, y, w, h = [int(v) for v in rect]
        self.host.setGeometry(x + left, y + top,
                              max(1, w - left - right),
                              max(1, h - top - bottom))

    # ------------------------------------------------------------ the chrome

    def chrome_widgets(self):
        """Every widget of the window but the curve area's container - the
        ones whose repaints mean the chrome changed."""
        try:
            widgets = self.host.findChildren(QtWidgets.QWidget)
        except RuntimeError:
            return []
        found = []
        for widget in widgets:
            try:
                if widget.metaObject().className() != CONTAINER_CLASS:
                    found.append(widget)
            except RuntimeError:
                continue
        return found

    def canvas_in_frame(self):
        """The curve area as (x, y, width, height) inside the window's frame,
        or None when Maya has no curve area to show."""
        canvas = self.canvas_rect()
        if canvas is None:
            return None
        fx, fy = self.frame_rect()[:2]
        return (canvas[0] - fx, canvas[1] - fy, canvas[2], canvas[3])

    def canvas_offset(self):
        """The curve area's top-left inside the frame, (0, 0) when unknown."""
        inside = self.canvas_in_frame()
        return (inside[0], inside[1]) if inside is not None else (0, 0)

    def chrome_pieces(self):
        """The window's chrome as [(QImage, x, y), ...] in frame coordinates,
        cut band by band around the curve area out of ONE capture of the
        whole window from DWM (`winstyle.capture`) - never `QWidget.grab()`,
        which re-renders Maya's widgets (it crashed Maya once, re-rendering
        the channel list right after the panel was re-parented). [] when the
        capture fails."""
        inside = self.canvas_in_frame()
        if inside is None:
            return []
        fx, fy, width, height = self.frame_rect()
        wx, wy, ww, wh = winstyle.window_rect(self.hwnd()) or \
            (fx, fy, width, height)
        data = winstyle.capture(self.hwnd(), ww, wh)
        if data is None:
            return []
        # The capture is the whole window, invisible border included; the
        # chrome is the part the animator sees.
        whole = QtGui.QImage(data, ww, wh, ww * 4,
                             QtGui.QImage.Format_RGB32).copy()
        whole = whole.copy(QtCore.QRect(fx - wx, fy - wy, width, height))
        pieces = []
        for band in geometry.chrome_bands((width, height), inside):
            piece = whole.copy(QtCore.QRect(*band)).convertToFormat(
                QtGui.QImage.Format_ARGB32)
            pieces.append((piece, band[0], band[1]))
        return pieces

    def _splitter(self):
        port = _widget(self.panel + "GraphEd")
        split = port.parentWidget() if port is not None else None
        if isinstance(split, QtWidgets.QSplitter):
            return split, split.indexOf(port)
        return None, -1

    def open_channel_list(self):
        """The channel list open, for the first `LIST_TICKS` follow ticks:
        a panel can come up with it shut (measured: sizes [0, 1681]), and
        it is where the channels are picked. Never narrower than its own
        minimum (310 px measured) - QSplitter collapses a side set below
        it, which is how a 260 px list came back as 0. Looked after for two
        seconds because the borrowed panel shut it once more itself while it
        finished laying out; after that a list the animator shuts stays
        shut. What it was is kept for `give_back`."""
        if self._list_ticks >= LIST_TICKS:
            return False
        self._list_ticks += 1
        split, index = self._splitter()
        if split is None or split.count() < 2:
            return False
        sizes = split.sizes()
        total = sum(sizes)
        if total < 0.8 * self.host.width():         # not laid out yet
            return False
        other = 1 - index
        if sizes[other] >= MIN_LIST:
            return False
        want = max(LIST_WIDTH, split.widget(other).minimumSizeHint().width())
        if self.list_sizes is None:
            self.list_sizes = sizes
        if not split.handleWidth():
            split.setHandleWidth(10)
        wanted = [0, 0]
        wanted[other] = want
        wanted[index] = max(1, total - want)
        split.setSizes(wanted)
        return True

    # ------------------------------------------------------------ the canvas

    def canvas(self):
        """The curve area as a QOpenGLWindow, or None - looked up among the
        LIVE windows every time. A cached wrapper is never asked anything
        first: Maya can delete the canvas and make another (re-parenting a
        panel does), and a method call on a wrapper of a deleted object
        shiboken was never told about reads freed memory - it does not
        raise, it crashes."""
        wanted = self.panel + "GraphEdImpl"
        for window in QtGui.QGuiApplication.allWindows():
            try:
                if window.objectName() != wanted or \
                        window.metaObject().className() != CANVAS_CLASS:
                    continue
                pointer = int(shiboken6.getCppPointer(window)[0])
            except RuntimeError:
                continue
            if self._canvas is not None and self._canvas_pointer == pointer:
                return self._canvas
            if not isinstance(window, QtOpenGL.QOpenGLWindow):
                shiboken6.invalidate(window)
                window = shiboken6.wrapInstance(pointer,
                                                QtOpenGL.QOpenGLWindow)
            self._canvas, self._canvas_pointer = window, pointer
            return self._canvas
        self._canvas, self._canvas_pointer = None, None
        return None

    def canvas_pointer(self):
        """The live canvas's C++ address, or None."""
        return self._canvas_pointer if self.canvas() is not None else None

    def canvas_rect(self):
        port = _widget(self.panel + "GraphEd")
        if port is None:
            return None
        for child in port.children():
            try:
                if isinstance(child, QtWidgets.QWidget) and \
                        child.metaObject().className() == CONTAINER_CLASS:
                    corner = child.mapToGlobal(QtCore.QPoint(0, 0))
                    return (corner.x(), corner.y(), child.width(),
                            child.height())
            except RuntimeError:
                continue
        return None

    def canvas_frame(self):
        canvas = self.canvas()
        return canvas.grabFramebuffer() if canvas is not None else None

    # --------------------------------------------------------------- the host

    def hwnd(self):
        return int(self.host.winId())

    def keep_invisible(self):
        """Put the 1/255 back if anything took it; True when it had to."""
        if winstyle.layered_alpha(self.hwnd()) == winstyle.GHOST_ALPHA:
            return False
        self.host.setWindowOpacity(1.0)
        self.host.setWindowOpacity(GHOST_OPACITY)
        return True

    def alive(self):
        """The window stands and the panel is still in it. A borrowed
        graphEditor1 can be taken back by Maya itself (the Graph Editor
        opened meanwhile re-parents it into its own window) - the mode
        then ends."""
        try:
            self.host.objectName()
            if not cmds.scriptedPanel(self.panel, exists=True):
                return False
            return in_host(self.panel) if self.borrowed else True
        except Exception:                                     # noqa: BLE001
            return False

    def give_back(self):
        """The borrowed panel back where it lived - its dock, its window,
        or unparented as it was - with its channel list's sizes; nothing
        when Maya already took it back."""
        if not self.borrowed or not in_host(self.panel):
            return False
        if self.list_sizes:
            split, _index = self._splitter()
            if split is not None:
                split.setSizes(self.list_sizes)
        if self.home and cmds.layout(self.home, exists=True):
            cmds.scriptedPanel(self.panel, edit=True, parent=self.home)
        else:
            cmds.scriptedPanel(self.panel, edit=True, unParent=True)
        return True

    def destroy(self):
        self._canvas, self._canvas_pointer = None, None
        try:
            if self.borrowed:
                self.give_back()
            elif cmds.scriptedPanel(self.panel, exists=True):
                cmds.deleteUI(self.panel, panel=True)
        except Exception:                                     # noqa: BLE001
            import traceback
            traceback.print_exc()
        try:
            self.host.hide()
            self.host.deleteLater()
        except RuntimeError:
            pass
