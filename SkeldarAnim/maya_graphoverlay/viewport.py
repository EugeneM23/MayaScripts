"""Where the viewport is, right now. cmds, with Qt imported inside.

From the Curve Overlay (archive/maya_curveview/viewport.py, measured
2026-09-05), with one change the hub skin paid for (trap 96): the rectangle
is read while the panel's wrapper is held, never through a child wrapper
handed out of the function - one handed out read "already deleted" a call
later on 2026-09-30.
"""

import maya.cmds as cmds

GL_CLASS = "QmayaGLWidget"     # the model panel's native GL surface


def _type_of(panel):
    try:
        return cmds.getPanel(typeOf=panel) or ""
    except Exception:                                         # noqa: BLE001
        return ""


def model_panels():
    """Every visible model panel, in Maya's own order."""
    visible_panels = cmds.getPanel(visiblePanels=True) or []
    return [panel for panel in visible_panels
            if _type_of(panel) == "modelPanel"]


def visible(panel):
    return bool(panel) and panel in model_panels()


def active_panel():
    """The focused model panel, else the first visible one, else None."""
    panels = model_panels()
    if not panels:
        return None
    try:
        focus = cmds.getPanel(withFocus=True)
    except Exception:                                         # noqa: BLE001
        focus = None
    return focus if focus in panels else panels[0]


def maya_main_window():
    """Maya's main window as a QWidget, or None: what our windows are owned
    by, so they ride its z-order and hide with it."""
    try:
        from maya import OpenMayaUI as omui
        from PySide6 import QtWidgets
        from shiboken6 import wrapInstance
    except ImportError:
        return None
    pointer = omui.MQtUtil.mainWindow()
    return wrapInstance(int(pointer), QtWidgets.QWidget) if pointer else None


def gl_rect(panel):
    """The panel's GL surface as (x, y, width, height) in global pixels."""
    if not panel:
        return None
    try:
        from maya import OpenMayaUI as omui
        from PySide6 import QtCore, QtWidgets
        from shiboken6 import wrapInstance
    except ImportError:
        return None
    pointer = omui.MQtUtil.findControl(panel)
    if not pointer:
        return None
    holder = wrapInstance(int(pointer), QtWidgets.QWidget)
    for child in holder.findChildren(QtWidgets.QWidget):
        try:
            if (child.metaObject().className() != GL_CLASS
                    or not child.isVisible()):
                continue
            corner = child.mapToGlobal(QtCore.QPoint(0, 0))
            return (corner.x(), corner.y(), child.width(), child.height())
        except RuntimeError:                  # a widget Maya deleted mid-walk
            continue
    return None


def maya_active():
    """Whether a Maya window is the active window."""
    try:
        from PySide6 import QtWidgets
        return QtWidgets.QApplication.activeWindow() is not None
    except (ImportError, RuntimeError):
        return True
