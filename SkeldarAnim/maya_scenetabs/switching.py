"""Scene tabs: switching. The tab being left is recorded (its time, view,
selection, modified flag) and hidden; the new one is shown with its
own, outside the undo queue: each tab's history ends at a fence laid as it is
entered (`tabundo`, 2026-10-19). Until then a switch was one undo chunk and a
Ctrl+Z past it brought the previous tab back.

Hidden by `lodVisibility` and `hiddenInOutliner` on the tab's top nodes, never
`visibility`, which the animator keys. The startup cameras (persp, top, front, side) are
the scene's, one of each for every tab: each tab keeps what they showed in it (2026-10-16,
`capture_cameras` / `apply_cameras`; a new tab its file's, an empty one Maya's defaults),
and its own keys on them: a key made in a tab is a curve in its namespace, connected while the
tab is active and disconnected while it is hidden (`detach_cameras` / `attach_cameras`,
2026-10-16: «если я накину анимации на камеру ... она будет во всех сценах»).
Maya's workspace is not a tab's: until 2026-10-16 each tab saved one, and they piled up
(`workspaces`).
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""

import maya.cmds as cmds

from . import layers, records, session, tabundo

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
    """Each model panel's camera and display flags (the startup cameras' places are
    the tab's `cameras`, `capture_cameras`)."""
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
            if "matrix" in view:            # a record from before the tab's `cameras`
                shape = _camera_shape(camera)
                cmds.xform(camera, matrix=view["matrix"], worldSpace=True)
                cmds.setAttr(shape + ".focalLength", view["focal"])
                cmds.setAttr(shape + ".centerOfInterest", view["coi"])
        for flag, value in (view.get("flags") or {}).items():
            try:
                cmds.modelEditor(panel, e=True, **{flag: value})
            except (RuntimeError, TypeError):
                pass


# ------------------------------------------------------------------ the cameras

def startup_cameras():
    """{"persp": (transform, shape), ...}: the scene's startup cameras by name."""
    out = {}
    for shape in cmds.ls(type="camera", long=True) or []:
        if not cmds.camera(shape, q=True, startupCamera=True):
            continue
        parent = (cmds.listRelatives(shape, parent=True, fullPath=True) or [""])[0]
        name = parent.split("|")[-1]
        if name in records.STARTUP_CAMERAS:
            out[name] = (parent, shape)
    return out


def capture_cameras():
    """What the startup cameras show now, in the scene's units."""
    out = {}
    for name, (transform, shape) in startup_cameras().items():
        values = {}
        for _short, long_name, node, _kind in records.CAMERA_ATTRS:
            value = cmds.getAttr((transform if node == "transform" else shape) + "." + long_name)
            values[long_name] = list(value[0]) if isinstance(value, list) else value
        out[name] = values
    return out


def apply_cameras(cameras):
    """The startup cameras put where `cameras` has them. A locked, keyed or driven
    channel is left as it is (a keyed persp is one curve for every tab)."""
    for name, (transform, shape) in startup_cameras().items():
        values = (cameras or {}).get(name) or {}
        for _short, long_name, node, _kind in records.CAMERA_ATTRS:
            if long_name not in values:
                continue
            target = transform if node == "transform" else shape
            value = values[long_name]
            if isinstance(value, (list, tuple)):
                children = cmds.attributeQuery(long_name, node=target, listChildren=True) or []
                for child, part in zip(children, value):
                    _set(target, child, part)
            else:
                _set(target, long_name, value)


TIME_CURVES = ("animCurveTL", "animCurveTA", "animCurveTU", "animCurveTT")


def camera_curves(namespace):
    """{"persp.translateX": curve, ...}: the time curves of `namespace` (its own or a
    namespace nested in it) driving a startup camera's channels - keys made while the tab
    was active (the current namespace is the tab's) or keys its file brought (an import
    connects them to the scene's persp, measured)."""
    prefix = namespace + ":"
    out = {}
    for transform, shape in startup_cameras().values():
        for node in (transform, shape):
            pairs = cmds.listConnections(node, source=True, destination=False, plugs=True,
                                         connections=True, skipConversionNodes=True) or []
            for plug, source in zip(pairs[::2], pairs[1::2]):
                curve = source.split(".")[0]
                if cmds.nodeType(curve) not in TIME_CURVES:
                    continue
                if not curve.lstrip(":").startswith(prefix):
                    continue
                out[plug.split("|")[-1]] = curve
    return out


def detach_cameras(namespace):
    """The tab's curves taken off the startup cameras (each channel keeps the value it
    showed). Returns {plug: curve UUID} for `attach_cameras`."""
    out = {}
    for plug, curve in sorted(camera_curves(namespace).items()):
        uid = (cmds.ls(curve, uuid=True) or [None])[0]
        try:
            cmds.disconnectAttr(curve + ".output", ":" + plug)
        except RuntimeError:
            continue
        if uid:
            out[plug] = uid
    return out


def attach_cameras(curves):
    """The tab's curves put back on the startup cameras. A curve gone, or a channel that
    something else drives meanwhile, is left as it stands."""
    for plug, uid in sorted((curves or {}).items()):
        found = cmds.ls(uid) or []
        target = ":" + plug
        if not found or not cmds.objExists(target):
            continue
        if cmds.listConnections(target, source=True, destination=False):
            continue
        try:
            cmds.connectAttr(found[0] + ".output", target)
        except RuntimeError:
            pass


def _units():
    return cmds.currentUnit(q=True, linear=True), cmds.currentUnit(q=True, angle=True)


def file_cameras(path):
    """A scene file's startup cameras in this scene's units (Maya's defaults where the
    file says nothing: an import never brings them, measured)."""
    return records.cameras_in_units(records.read_cameras(path), *_units())


def default_cameras():
    """Maya's startup cameras of a new scene, in this scene's units."""
    return records.cameras_in_units(records.with_defaults({}), *_units())


def _off_hidden(namespace, tabs):
    """A model panel left looking through a hidden tab's camera (a new tab has no
    views of its own) looks through persp instead."""
    if not _gui():
        return
    for panel in cmds.getPanel(type="modelPanel") or []:
        try:
            camera = cmds.modelPanel(panel, q=True, camera=True)
        except RuntimeError:
            continue
        path = (cmds.ls(camera, long=True) or [camera or ""])[0]
        if records.foreign_camera(path, namespace, tabs) and "persp" in startup_cameras():
            cmds.modelPanel(panel, e=True, camera=startup_cameras()["persp"][0])


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
    current["cameras"] = capture_cameras()
    current["camera_curves"] = detach_cameras(active)
    hide(active)
    cmds.file(modified=False)
    return records.with_tab(state, current)


def enter(state, namespace, fresh=False):
    """`namespace` shown and made current with its time, view and selection
    (`fresh`, a tab just opened: kept for the callers, it changes nothing now)."""
    current = dict(records.tab(state, namespace))
    show(namespace)
    cmds.namespace(setNamespace=":" + namespace)
    if current.get("unit"):
        cmds.currentUnit(time=current["unit"], updateAnimation=True)
    session.apply_ranges(current.get("ranges"))
    if current.get("frame") is not None:
        cmds.currentTime(current["frame"], update=True)
    apply_views(current.get("views"))
    attach_cameras(current.get("camera_curves"))
    apply_cameras(current.get("cameras"))
    _off_hidden(namespace, [t["ns"] for t in state["tabs"]])
    found = cmds.ls(current.get("selection") or [], long=True) or []
    if found:
        cmds.select(found, replace=True)
    else:
        cmds.select(clear=True)
    return records.with_tab(dict(state, active=namespace), current)


def settle_flag(state):
    """The scene's modified flag the active tab's own. A switch's setAttrs and the
    session's write flag the scene (measured: a clean tab came out modified from every
    switch, and the next leave recorded it so): called after the last write."""
    item = records.tab(state, state["active"]) or {}
    cmds.file(modified=bool(item.get("modified")))


def _restore(before, modified):
    """A switch that failed half way: the tab that was active back, the rest hidden,
    the scene's modified flag as it was before the switch (`before` is the state
    before `leave`, whose record has not taken the flag yet)."""
    for item in before["tabs"]:
        if item["ns"] != before["active"]:
            hide(item["ns"])
    try:
        enter(before, before["active"])
    finally:
        session.write(before)
        cmds.file(modified=bool(modified))


def switch(namespace):
    """Leave the active tab, enter `namespace` - outside the undo queue, with a
    fence on it for the tab entered (`tabundo`): Ctrl+Z in a tab never reaches
    another tab's work and never switches tabs (2026-10-19)."""
    state = session.state()
    if namespace == state["active"]:
        return state
    if records.tab(state, namespace) is None:
        raise session.TabError("no tab %s" % namespace)
    before = state
    modified = cmds.file(q=True, modified=True)
    lay = tabundo.before_switch(state["active"], namespace, cmds)
    cmds.file(modified=bool(modified))      # a fence popped (an undo) flags the scene; the tab left is as it was
    recording = cmds.undoInfo(q=True, stateWithoutFlush=True)
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        try:
            state = enter(leave(state), namespace)
            session.write(state)
        except Exception:
            _restore(before, modified)
            raise
    finally:
        cmds.undoInfo(stateWithoutFlush=recording)
    if lay:
        tabundo.after_switch(namespace, records.SESSION_NODE, cmds)
    settle_flag(state)
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
