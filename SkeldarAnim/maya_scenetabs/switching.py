"""Scene tabs: switching. The tab being left is recorded (its time, view,
selection, layout, modified flag) and hidden; the new one is shown with its
own, in ONE undo chunk - so a Ctrl+Z past a switch brings the previous tab
back before it undoes that tab's step (measured: one undo restores the
namespace, the unit, the ranges and the visibility).

Hidden by `lodVisibility` and `hiddenInOutliner` on the tab's top nodes, never
`visibility`, which the animator keys.
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""

import maya.cmds as cmds

from . import layers, records, session

VIEW_FLAGS = ("displayAppearance", "displayTextures", "displayLights", "shadows", "joints",
              "nurbsCurves", "polymeshes", "locators", "cameras", "grid")


def _gui():
    return not cmds.about(batch=True)


def tops(namespace):
    """The tab's top DAG nodes (its namespace or one nested in it)."""
    prefix = namespace + ":"
    return [t for t in cmds.ls(assemblies=True, long=True) or [] if t.lstrip("|").startswith(prefix)]


def _set(node, attr, value):
    plug = node + "." + attr
    if cmds.attributeQuery(attr, node=node, exists=True) and cmds.getAttr(plug, settable=True):
        cmds.setAttr(plug, value)


#  2026-10-16, found live: the Outliner listed a hidden tab's selection sets. A set is a
#  DG node with its own `hiddenInOutliner`; the ones WE hid carry SET_MARK, so a set the
#  animator hid stays hidden when its tab comes back.
SET_MARK = "skeldarTabSetHidden"


def sets(namespace):
    """The tab's sets (objectSets of every kind: selection sets, the rig's ControlSet,
    shading groups), its namespace and the ones nested in it."""
    return session.typed(namespace, "objectSet")


def hide_sets(namespace):
    for node in sets(namespace):
        if cmds.attributeQuery(SET_MARK, node=node, exists=True):
            continue
        if not cmds.attributeQuery("hiddenInOutliner", node=node, exists=True):
            continue
        if cmds.getAttr(node + ".hiddenInOutliner") or not cmds.getAttr(node + ".hiddenInOutliner",
                                                                         settable=True):
            continue
        cmds.addAttr(node, longName=SET_MARK, attributeType="bool")
        cmds.setAttr(node + ".hiddenInOutliner", 1)


def show_sets(namespace):
    for node in sets(namespace):
        if not cmds.attributeQuery(SET_MARK, node=node, exists=True):
            continue
        cmds.deleteAttr(node + "." + SET_MARK)
        _set(node, "hiddenInOutliner", 0)


def _refresh_outliners():
    if _gui():
        cmds.evalDeferred("import maya.mel; maya.mel.eval('AEdagNodeCommonRefreshOutliners')",
                          lowestPriority=True)


def hide(namespace):
    for top in tops(namespace):
        _set(top, "lodVisibility", 0)
        _set(top, "hiddenInOutliner", 1)
    hide_sets(namespace)
    layers.hide_layers(namespace)       # out of the Layer Editor too (2026-10-15)
    layers.refresh_editors()
    _refresh_outliners()


def show(namespace):
    for top in tops(namespace):
        _set(top, "lodVisibility", 1)
        _set(top, "hiddenInOutliner", 0)
    show_sets(namespace)
    layers.show_layers(namespace)
    layers.refresh_editors()
    _refresh_outliners()


# ------------------------------------------------------------------ the view

def _camera_shape(camera):
    return (cmds.listRelatives(camera, shapes=True, fullPath=True) or [camera])[0]


def capture_views():
    """Each model panel's camera, a startup camera's place, the display flags."""
    if not _gui():
        return []
    views = []
    for panel in cmds.getPanel(type="modelPanel") or []:
        try:
            camera = cmds.modelPanel(panel, q=True, camera=True)
        except RuntimeError:
            continue
        view = {"panel": panel, "camera": camera, "flags": {}}
        for flag in VIEW_FLAGS:
            try:
                view["flags"][flag] = cmds.modelEditor(panel, q=True, **{flag: True})
            except (RuntimeError, TypeError):
                pass
        if camera and cmds.objExists(camera):
            shape = _camera_shape(camera)
            if cmds.camera(shape, q=True, startupCamera=True):
                view["matrix"] = cmds.xform(camera, q=True, matrix=True, worldSpace=True)
                view["focal"] = cmds.getAttr(shape + ".focalLength")
                view["coi"] = cmds.getAttr(shape + ".centerOfInterest")
        views.append(view)
    return views


def apply_views(views):
    if not _gui():
        return
    panels = cmds.getPanel(type="modelPanel") or []
    for view in views or []:
        panel = view.get("panel")
        if panel not in panels:
            continue
        camera = view.get("camera")
        if camera and cmds.objExists(camera):
            cmds.modelPanel(panel, e=True, camera=camera)
            if "matrix" in view:
                shape = _camera_shape(camera)
                cmds.xform(camera, matrix=view["matrix"], worldSpace=True)
                cmds.setAttr(shape + ".focalLength", view["focal"])
                cmds.setAttr(shape + ".centerOfInterest", view["coi"])
        for flag, value in (view.get("flags") or {}).items():
            try:
                cmds.modelEditor(panel, e=True, **{flag: value})
            except (RuntimeError, TypeError):
                pass


# ------------------------------------------------------------------ the layout

def _layouts():
    try:
        return cmds.workspaceLayoutManager(listLayouts=True) or []
    except RuntimeError:
        return []


def save_layout(tab):
    if _gui():
        try:
            cmds.workspaceLayoutManager(saveAs=tab["layout"])
        except RuntimeError:
            pass


def load_layout(tab):
    if not _gui():
        return
    try:
        if tab["layout"] in _layouts():
            cmds.workspaceLayoutManager(setCurrent=tab["layout"])
    except RuntimeError:
        pass
    from . import bar
    bar.ensure_docked()


def forget_layout(tab):
    if _gui() and tab.get("layout") in _layouts():
        try:
            cmds.workspaceLayoutManager(delete=tab["layout"])
        except RuntimeError:
            pass


# ------------------------------------------------------------------ leave / enter

def leave(state):
    """The active tab recorded and hidden; its modified flag taken off Maya's."""
    active = state["active"]
    current = records.tab(state, active)
    if current is None:
        return state
    current = dict(current)
    current["modified"] = bool(current["modified"] or cmds.file(q=True, modified=True))
    current["unit"] = cmds.currentUnit(q=True, time=True)
    current["ranges"] = session.current_ranges()
    current["frame"] = cmds.currentTime(q=True)
    current["selection"] = cmds.ls(selection=True, uuid=True) or []
    current["views"] = capture_views()
    save_layout(current)
    hide(active)
    cmds.file(modified=False)
    return records.with_tab(state, current)


def enter(state, namespace, fresh=False):
    """`namespace` shown and made current with its time, view, selection and
    layout (`fresh`: a new tab takes a copy of the current layout)."""
    current = dict(records.tab(state, namespace))
    show(namespace)
    cmds.namespace(setNamespace=":" + namespace)
    if current.get("unit"):
        cmds.currentUnit(time=current["unit"], updateAnimation=True)
    session.apply_ranges(current.get("ranges"))
    if current.get("frame") is not None:
        cmds.currentTime(current["frame"], update=True)
    apply_views(current.get("views"))
    found = cmds.ls(current.get("selection") or [], long=True) or []
    if found:
        cmds.select(found, replace=True)
    else:
        cmds.select(clear=True)
    if fresh:
        save_layout(current)
    else:
        load_layout(current)
    return records.with_tab(dict(state, active=namespace), current)


def _restore(before):
    """A switch that failed half way: the tab that was active back, the rest hidden."""
    for item in before["tabs"]:
        if item["ns"] != before["active"]:
            hide(item["ns"])
    try:
        enter(before, before["active"])
    finally:
        session.write(before)


def switch(namespace):
    """One undo chunk: leave the active tab, enter `namespace`."""
    state = session.state()
    if namespace == state["active"]:
        return state
    if records.tab(state, namespace) is None:
        raise session.TabError("no tab %s" % namespace)
    before = state
    cmds.undoInfo(openChunk=True, chunkName="skeldarTabSwitch")
    try:
        try:
            state = enter(leave(state), namespace)
            session.write(state)
        except Exception:
            _restore(before)
            raise
    finally:
        cmds.undoInfo(closeChunk=True)
    return state


def cycle(step):
    """The next (`step` 1) or previous (-1) tab."""
    state = session.state()
    names = [t["ns"] for t in state["tabs"]]
    if len(names) < 2:
        return "One scene open - no other tab"
    target = names[(names.index(state["active"]) + step) % len(names)]
    switch(target)
    return "Tab: %s" % records.title(records.tab(session.state(), target))
