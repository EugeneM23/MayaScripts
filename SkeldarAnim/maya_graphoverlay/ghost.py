"""Our own Graph Editor: invisible, its curve area exactly on the viewport.

A `scriptedPanel` of type graphEditor inside a frameless Qt host of ours
(the hub skin's `cmds.setParent(fullName(layout))`), never the animator's
graphEditor1 - their Graph Editor stays where they docked it. Measured
2026-09-30 on this very construction:

- the curve area is `TanimCurveCanvas`, a QOpenGLWindow named
  `<panel>GraphEdImpl` inside a QWindowContainer - a native child HWND;
- the menu bar goes with `menuBarVisible=False`, the toolbar is the panel's
  one frameLayout (the parent of its `QadskFrameLayoutFrame`) unmanaged,
  the channel list the QSplitter's other side sized 0, handle width 0;
- then the canvas sits (5, 3) into the host with 8x6 of border, and the
  host placed by `geometry.host_rect` puts it on the viewport pixel for
  pixel.

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

PANEL = "skeldarGraphOverlayPanel"
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


def delete_leftovers():
    """A panel of ours a saved scene brought back; a host or a glass an
    older module object built (an install purges modules, not widgets -
    trap 102). Found by name, never by module state."""
    try:
        if cmds.scriptedPanel(PANEL, exists=True):
            cmds.deleteUI(PANEL, panel=True)
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

    def __init__(self, parent, rect):
        delete_leftovers()
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
        self.panel = cmds.scriptedPanel(PANEL, type="graphEditor",
                                        label=LABEL, parent=pane)
        try:
            cmds.setParent(previous)
        except Exception:                                     # noqa: BLE001
            pass
        self.hide_chrome()

    # ------------------------------------------------------------ the chrome

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
        """Move the host so its canvas lands on `target` (it converges in the
        next layout pass when the size changed)."""
        self.hide_chrome()
        canvas = self.canvas_rect()
        if canvas is None:
            self.host.setGeometry(*[int(v) for v in target])
            return
        wanted = geometry.host_rect(target, self.host_rect(), canvas)
        if wanted != self.host_rect():
            self.host.setGeometry(*wanted)

    def aligned(self, target):
        return self.canvas_rect() == tuple(target)

    def alive(self):
        try:
            self.host.objectName()
            return bool(cmds.scriptedPanel(self.panel, exists=True))
        except Exception:                                     # noqa: BLE001
            return False

    def destroy(self):
        self._canvas = None
        try:
            if cmds.scriptedPanel(self.panel, exists=True):
                cmds.deleteUI(self.panel, panel=True)
        except Exception:                                     # noqa: BLE001
            pass
        try:
            self.host.hide()
            self.host.deleteLater()
        except RuntimeError:
            pass
