"""Where the viewport is, right now.

The overlay is a window of its own, so it has to be told a rectangle in
global pixels, and that rectangle moves: the Maya window is dragged, a panel
is maximised with Ctrl+Space, a layout is switched, the window crosses to a
monitor with another DPI. This module answers "where is it now" and nothing
else.

Qt is imported inside the functions, not at module level, so the `cmds`-only
half can be exercised in a headless test with no Qt platform plugin.
"""

import maya.cmds as cmds

_real_cmds = cmds

# Measured 2026-09-05: the native GL surface inside a model panel. It is a
# NATIVE window, which is why nothing of ours is ever parented to it.
GL_CLASS = "QmayaGLWidget"


def _type_of(panel):
    try:
        return cmds.getPanel(typeOf=panel) or ""
    except Exception:
        return ""


def model_panels():
    """Every visible model panel, in Maya's own order."""
    visible = cmds.getPanel(visiblePanels=True) or []
    return [panel for panel in visible if _type_of(panel) == "modelPanel"]


def active_panel():
    """The model panel to draw on: the focused one, else the first visible.

    One viewport at a time, deliberately. Two overlays would need two
    dragger contexts and there is only one current tool.
    """
    panels = model_panels()
    if not panels:
        return None
    try:
        focus = cmds.getPanel(withFocus=True)
    except Exception:
        focus = None
    if focus and focus in panels:
        return focus
    return panels[0]


# ------------------------------------------------------------------ Qt side

def maya_main_window():
    """Maya's main window as a QWidget, or None.

    The overlay is parented to it so it rides Maya's z-order and hides with
    it -- the first probe used `WindowStaysOnTopHint` with no parent and
    left a panel floating over the animator's other application.
    """
    try:
        from maya import OpenMayaUI as omui
        from shiboken6 import wrapInstance
        from PySide6 import QtWidgets
    except ImportError:
        return None
    pointer = omui.MQtUtil.mainWindow()
    if not pointer:
        return None
    return wrapInstance(int(pointer), QtWidgets.QWidget)


def gl_widget(panel):
    """The panel's GL surface as a QWidget, or None."""
    if not panel:
        return None
    try:
        from maya import OpenMayaUI as omui
        from shiboken6 import wrapInstance
        from PySide6 import QtWidgets
    except ImportError:
        return None
    pointer = omui.MQtUtil.findControl(panel)
    if not pointer:
        return None
    holder = wrapInstance(int(pointer), QtWidgets.QWidget)
    for child in holder.findChildren(QtWidgets.QWidget):
        try:
            if child.metaObject().className() == GL_CLASS:
                return child
        except RuntimeError:      # a widget Maya deleted mid-walk
            continue
    return None


def global_rect(widget):
    """(x, y, width, height) in global pixels, or None."""
    if widget is None:
        return None
    try:
        from PySide6 import QtCore
    except ImportError:
        return None
    try:
        top_left = widget.mapToGlobal(QtCore.QPoint(0, 0))
        return (top_left.x(), top_left.y(), widget.width(), widget.height())
    except RuntimeError:
        return None


def panel_rect(panel=None):
    """Where the drawing goes: the GL surface's rectangle, or None."""
    panel = panel or active_panel()
    if not panel:
        return None
    return global_rect(gl_widget(panel))


def maya_has_focus():
    """Whether a Maya window is the active window.

    Used to hide the overlay when the animator switches application: it sits
    above Maya's own panels, so leaving it up over another program is rude
    and over a Maya menu it draws curve lines across the menu.
    """
    try:
        from PySide6 import QtWidgets
    except ImportError:
        return True
    try:
        return QtWidgets.QApplication.activeWindow() is not None
    except RuntimeError:
        return True
