"""The Graph Editor on the viewport, invisible, in a frameless host of ours.

The panel is Maya's OWN `graphEditor1`, borrowed for as long as the mode is
on and put back where it lived (its dock, its window, or unparented) when it
ends. Measured 2026-09-30: 55 of Maya's runtime commands name
`graphEditor1GraphEd` outright - Copy/Paste/Delete keys, the view modes,
infinity, frame all/selected, bake, simplify, the smoothness - and the
toolbar, the menus and the hotkeys reach them; in a panel of our own the
Stacked View button switched the animator's Graph Editor instead (read off
the button: `GraphEditorStackedView` = `graphEditorSetViewMode
graphEditor1GraphEd 1`). Borrowed, every one of them acts on the Graph
Editor over the viewport, with the animator's own settings. Without a
graphEditor1 (or with `borrow=False`) a `scriptedPanel` of our own stands
in. It goes into the host with the hub skin's `setParent(fullName(layout))`.
Measured on this construction:

- the curve area is `TanimCurveCanvas`, a QOpenGLWindow named
  `<panel>GraphEdImpl` inside a QWindowContainer - a native child HWND;
- by default (`chrome=True`, the animator's call the same day: the channel
  list and the tools are the Graph Editor) the WHOLE panel lies on the
  viewport - menu bar, toolbar, channel list, curve area - and the glass
  shows the chrome from `host.grab()` of the bands around the curve area
  (`geometry.chrome_bands`), the curve area keyed;
- without it the menu bar goes with `menuBarVisible=False`, the toolbar is
  the panel's one frameLayout (the parent of its `QadskFrameLayoutFrame`)
  unmanaged, the channel list the QSplitter's other side sized 0, handle
  width 0; then the canvas sits (5, 3) into the host with 8x6 of border,
  and the host placed by `geometry.host_rect` puts it on the viewport
  pixel for pixel.

PySide hands the canvas back as a QPaintDeviceWindow; the cached wrapper is
invalidated and the pointer wrapped as the QOpenGLWindow it is, which is
what reaches `grabFramebuffer()` and `frameSwapped`.

The ghost is made invisible by Qt's OWN window opacity, 1/255 - never by
setting WS_EX_LAYERED behind Qt's back: measured live 2026-09-30, Qt
rewrote the style of a window it thought opaque and dropped the bit (the
style read 0xa0), so the "invisible" Graph Editor stood grey over the
viewport and the follow timer's re-assertions made it redraw ~40 times a
second. With `setWindowOpacity` Qt keeps it layered itself (0x80080,
alpha 1, no redraws at rest).
"""

import maya.cmds as cmds
from maya import OpenMayaUI as omui
from PySide6 import QtCore, QtGui, QtOpenGL, QtWidgets
import shiboken6

from maya_graphoverlay import geometry, winstyle

PANEL = "skeldarGraphOverlayPanel"          # our own, when nothing is borrowed
BORROWED = "graphEditor1"                   # Maya's own Graph Editor panel
LIST_WIDTH = 260                            # the channel list, when it was shut
MIN_LIST = 120
HOST = "skeldarGraphOverlayHost"
LAYOUT = "skeldarGraphOverlayLayout"
PANE = "skeldarGraphOverlayPane"
LABEL = "Graph Overlay"
CANVAS_CLASS = "TanimCurveCanvas"
CONTAINER_CLASS = "QWindowContainer"
FRAME_CLASS = "QadskFrameLayoutFrame"
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
    """The panel, its host, and the canvas wrapper, held together."""

    def __init__(self, parent, rect, chrome=True, borrow=True):
        """`chrome`: the whole Graph Editor on `rect` - menu bar, toolbar,
        channel list and the curve area (2026-09-30, the animator: «я не
        могу выделить отдельно каналы для редактирования кривых и нет
        остальных инструментов»). False: the curve area alone on `rect`,
        everything else hidden - the first build's shape. `borrow`: Maya's
        own graphEditor1 rather than a panel of ours (see the module)."""
        delete_leftovers()
        self.chrome = bool(chrome)
        self.borrowed = False
        self.home = None            # where the borrowed panel lived
        self.list_sizes = None      # its splitter's sizes, when we opened it
        host = QtWidgets.QWidget(parent, QtCore.Qt.Tool
                                 | QtCore.Qt.FramelessWindowHint)
        host.setObjectName(HOST)
        host.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        layout = QtWidgets.QVBoxLayout(host)
        layout.setObjectName(LAYOUT)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.host, self.layout = host, layout
        self._canvas = None
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
        if self.chrome:
            self.open_channel_list()
        else:
            self.hide_chrome()

    # ------------------------------------------------------------ the chrome

    def chrome_widgets(self):
        """Every widget of the host but the curve area's container - the
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

    def canvas_offset(self):
        """The curve area's top-left inside the host, (0, 0) when unknown."""
        canvas = self.canvas_rect()
        if canvas is None:
            return (0, 0)
        corner = self.host.mapToGlobal(QtCore.QPoint(0, 0))
        return (canvas[0] - corner.x(), canvas[1] - corner.y())

    def chrome_pieces(self):
        """The chrome as [(QImage, x, y), ...] in host coordinates: the host
        grabbed band by band around the curve area (Qt widgets render into
        a grab whatever the window's opacity)."""
        if not self.chrome:
            return []
        canvas = self.canvas_rect()
        if canvas is None:
            return []
        x, y = self.canvas_offset()
        pieces = []
        for band in geometry.chrome_bands((self.host.width(),
                                           self.host.height()),
                                          (x, y, canvas[2], canvas[3])):
            pixmap = self.host.grab(QtCore.QRect(*band))
            pieces.append((pixmap.toImage(), band[0], band[1]))
        return pieces

    def _splitter(self):
        port = _widget(self.panel + "GraphEd")
        split = port.parentWidget() if port is not None else None
        if isinstance(split, QtWidgets.QSplitter):
            return split, split.indexOf(port)
        return None, -1

    def open_channel_list(self):
        """The channel list open at least `MIN_LIST` wide: a fresh panel
        comes up with it shut (measured: 15 px of border, sizes [0, 1686]),
        and it is where the channels are picked. What it was is kept for
        `destroy` to put back."""
        split, index = self._splitter()
        if split is None or split.count() < 2:
            return False
        sizes = split.sizes()
        other = 1 - index
        if sizes[other] >= MIN_LIST:
            return False
        self.list_sizes = sizes
        if not split.handleWidth():
            split.setHandleWidth(10)
        total = sum(sizes)
        wanted = [0, 0]
        wanted[other] = LIST_WIDTH
        wanted[index] = max(1, total - LIST_WIDTH)
        split.setSizes(wanted)
        return True

    def hide_chrome(self):
        """Menu bar, toolbar and channel list out; idempotent."""
        try:
            if cmds.scriptedPanel(self.panel, query=True,
                                  menuBarVisible=True):
                cmds.scriptedPanel(self.panel, edit=True,
                                   menuBarVisible=False)
        except Exception:                                     # noqa: BLE001
            pass
        panel_widget = _widget(self.panel)
        if panel_widget is None:
            return
        for frame in panel_widget.findChildren(QtWidgets.QWidget):
            try:
                if frame.metaObject().className() != FRAME_CLASS:
                    continue
                name = _full_name(frame.parentWidget())
            except RuntimeError:
                continue
            if cmds.frameLayout(name, exists=True) and \
                    cmds.frameLayout(name, query=True, manage=True):
                cmds.frameLayout(name, edit=True, manage=False)
        port = _widget(self.panel + "GraphEd")
        split = port.parentWidget() if port is not None else None
        if isinstance(split, QtWidgets.QSplitter):
            if split.handleWidth():
                split.setHandleWidth(0)
            index, sizes = split.indexOf(port), split.sizes()
            wanted = [sum(sizes) if i == index else 0
                      for i in range(len(sizes))]
            if sizes != wanted:
                split.setSizes(wanted)

    # ------------------------------------------------------------ the canvas

    def canvas(self):
        """The curve area as a QOpenGLWindow, or None."""
        if self._canvas is not None:
            try:
                self._canvas.objectName()
                return self._canvas
            except RuntimeError:
                self._canvas = None
        wanted = self.panel + "GraphEdImpl"
        for window in QtGui.QGuiApplication.allWindows():
            try:
                if window.objectName() != wanted or \
                        window.metaObject().className() != CANVAS_CLASS:
                    continue
                pointer = shiboken6.getCppPointer(window)[0]
            except RuntimeError:
                continue
            shiboken6.invalidate(window)
            self._canvas = shiboken6.wrapInstance(int(pointer),
                                                  QtOpenGL.QOpenGLWindow)
            return self._canvas
        return None

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

    def grab(self):
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

    def host_rect(self):
        g = self.host.geometry()
        return (g.x(), g.y(), g.width(), g.height())

    def place(self, target):
        """With the chrome: the host on `target`. Without it: the host moved
        so its canvas lands on `target` (it converges in the next layout
        pass when the size changed)."""
        if self.chrome:
            if self.host_rect() != tuple(target):
                self.host.setGeometry(*[int(v) for v in target])
            return
        self.hide_chrome()
        canvas = self.canvas_rect()
        if canvas is None:
            self.host.setGeometry(*[int(v) for v in target])
            return
        wanted = geometry.host_rect(target, self.host_rect(), canvas)
        if wanted != self.host_rect():
            self.host.setGeometry(*wanted)

    def aligned(self, target):
        if self.chrome:
            return self.host_rect() == tuple(target)
        return self.canvas_rect() == tuple(target)

    def alive(self):
        """The host stands and the panel is still in it. A borrowed
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
        self._canvas = None
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
