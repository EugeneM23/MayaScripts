"""Maya's own editors borrowed into the side panel and given back (2026-10-17).

A form layout of Maya's (`MainAttributeEditorLayout`, `MainChannelsLayersLayout`, ...) is
moved, as a Qt widget, into a page of ours; its workspaceControl is hidden; the record of
where it came from (the workspaceControl, the parent widget's objectName, the index in
its layout, whether the control was shown) lives on `sys` with the rest of the state
(trap 111). Every widget is found again by name when it is used (trap 135).

While anything is held, `isAttributeEditorVisible` / `isChannelBoxVisible` answer for
the panel (look.MEL_OVERRIDE): the Attribute Editor refreshes only while that is true,
and showEditor (Ctrl+A) would otherwise restore the empty workspaceControl.
"""

import traceback

import maya_hubqt as hubqt

from . import look


def _omui():
    import maya.OpenMayaUI as omui
    return omui


def _cmds():
    import maya.cmds as cmds
    return cmds


def _mel():
    import maya.mel as mel
    return mel


def widget(name):
    """The QWidget of a Maya control or layout called `name`, or None."""
    q = hubqt.qt()
    if q is None or not name:
        return None
    omui = _omui()
    ptr = omui.MQtUtil.findControl(name) or omui.MQtUtil.findLayout(name)
    if not ptr:
        return None
    try:
        return q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
    except Exception:                                        # noqa: BLE001
        return None


def dock_control(component):
    """The workspaceControl Maya keeps `component` (a UI component's name) in."""
    try:
        name = _mel().eval('getUIComponentDockControl("%s", false)' % component)
    except Exception:                                        # noqa: BLE001
        name = ""
    if name and _cmds().workspaceControl(name, exists=True):
        return name
    return ""


def separate():
    cmds = _cmds()
    try:
        return bool(cmds.optionVar(q="channelsLayersSeparate"))
    except Exception:                                        # noqa: BLE001
        return False


def ws_visible(name):
    try:
        return bool(name) and bool(_cmds().workspaceControl(name, q=True, visible=True))
    except Exception:                                        # noqa: BLE001
        return False


def _set_ws(name, visible):
    cmds = _cmds()
    try:
        if visible:
            cmds.workspaceControl(name, edit=True, restore=True)
        cmds.workspaceControl(name, edit=True, visible=bool(visible))
    except Exception:                                        # noqa: BLE001
        pass


def take(component, form, layout):
    """Move `form` into the Qt `layout`; the record of where it was, or None."""
    ws = dock_control(component)
    shown = ws_visible(ws)
    w = widget(form)
    if w is None and ws:
        _set_ws(ws, True)                  # a control never shown: built now
        w = widget(form)
    if w is None:
        return None
    parent = w.parentWidget()
    index = -1
    parent_name = ""
    if parent is not None:
        parent_name = parent.objectName()
        if parent.layout() is not None:
            index = parent.layout().indexOf(w)
    record = {"component": component, "form": form, "ws": ws, "shown": shown,
              "parent": parent_name, "index": index}
    layout.addWidget(w)
    w.show()
    if ws:
        _set_ws(ws, False)
    return record


def _parent_for(record):
    """The widget `record`'s form came from, found again: by its objectName under
    the workspaceControl, else the workspaceControl itself."""
    q = hubqt.qt()
    ws = widget(record.get("ws"))
    if ws is None:
        return None
    name = record.get("parent")
    if name:
        if ws.objectName() == name:
            return ws
        for child in ws.findChildren(q.QtWidgets.QWidget, name):
            return child
    return ws


def give(record):
    """Put the form back where `record` says it came from. True when it went."""
    w = widget(record.get("form"))
    if w is None:
        return False
    parent = _parent_for(record)
    if parent is None:
        return False
    layout = parent.layout()
    if layout is not None:
        index = int(record.get("index", -1))
        insert = getattr(layout, "insertWidget", None)
        if insert is not None and index >= 0:
            insert(min(index, layout.count()), w)
        else:
            layout.addWidget(w)
    else:
        w.setParent(parent)
    w.show()
    if record.get("ws") and record.get("shown"):
        _set_ws(record["ws"], True)
    return True


def refresh_attribute_editor():
    """The Attribute Editor on the last selected node (look.MEL_REFRESH_AE)."""
    try:
        mel = _mel()
        if not mel.eval('exists "skeldarSidePanelRefreshAE"'):
            mel.eval(look.MEL_REFRESH_AE)
        mel.eval("skeldarSidePanelRefreshAE")
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())


def install():
    """The two visibility procs answer for the panel (look.MEL_OVERRIDE)."""
    try:
        _mel().eval(look.MEL_REFRESH_AE)
        _mel().eval(look.MEL_OVERRIDE)
        return True
    except Exception:                                        # noqa: BLE001
        print("SkeldarAnim: the side panel could not redefine Maya's visibility procs")
        print(traceback.format_exc())
        return False


def uninstall():
    """Maya's own procs again."""
    for line in look.MEL_RESTORE:
        try:
            _mel().eval(line)
        except Exception:                                    # noqa: BLE001
            pass


def update_channel_box():
    try:
        _cmds().channelBox("mainChannelBox", edit=True, update=True)
    except Exception:                                        # noqa: BLE001
        pass
