"""The CoM tool: drag the point, every part of the body follows.

Select a CoM handle and the tool comes on (the previous tool is remembered
and comes back when something else is selected; W/E/R with the handle
selected comes back to ours - a handle's translate is driven, nothing else
can move it). LMB drags the CoM in the view plane, Shift on the floor, Ctrl
straight up or down. A click without a drag selects, as the Select tool does.

Every world driver of the body (dragmath.RIG_DRIVERS on a rig, the pelvis on a
bare skeleton) moves by the same world vector d, so the CoM moves by d
exactly; `Main` - root motion - never moves. A press measures once how each
driver's local translate turns into world (`plan`: the poles follow blends of
the others), a drag writes start + d·A, a release keys what Maya's autoKey
would key. `undoMode="all"`: one Ctrl+Z per drag.
"""

import math
import sys

import maya.cmds as cmds

import maya_hubcopy as hubcopy
from maya_com import dragmath, network

CONTEXT = "skeldarComContext"
BOUNCE_FROM = ("moveSuperContext", "RotateSuperContext", "scaleSuperContext",
               "manipMoveContext", "manipRotateContext", "manipScaleContext")
CLICK_PX = 3.0
UNIT = 1.0                      # cm: the probe of a plan


def _state():
    st = getattr(sys, "_skeldar_com", None)
    if st is None:
        st = {}
        sys._skeldar_com = st
    return st.setdefault("drag", {"previous": None, "press": None,
                                  "plans": {}, "jobs": []})


# ------------------------------------------------------------------- pure

def handles_only(selection, group_of_handle):
    """The CoM groups when the selection is CoM handles and nothing else,
    else []. `group_of_handle(path)` -> group or None."""
    groups = []
    for path in selection or []:
        group = group_of_handle(path)
        if not group:
            return []
        if group not in groups:
            groups.append(group)
    return groups


def should_bounce(tool, has_handles):
    """W/E/R with a handle selected comes back to the CoM tool."""
    return bool(has_handles) and tool in BOUNCE_FROM


# ------------------------------------------------------------------ scene

def _vec(attr):
    return tuple(cmds.getAttr(attr)[0])


def _free(node):
    return [a for a in ("tx", "ty", "tz")
            if cmds.getAttr(node + "." + a, settable=True)]


def _world_pos(node):
    return tuple(cmds.xform(node, query=True, worldSpace=True, translation=True))


def _parent3(node):
    m = cmds.getAttr(node + ".parentMatrix[0]")
    return (tuple(m[0:3]), tuple(m[4:7]), tuple(m[8:11]))


def _follows(drivers):
    """The follow blends a plan depends on, as a key for the cache."""
    out = []
    for node in drivers:
        for attr in cmds.listAttr(node, userDefined=True) or []:
            if attr.lower().startswith("follow"):
                out.append((node, attr, round(cmds.getAttr(node + "." + attr), 6)))
    return tuple(out)


def plan(char, drivers=None):
    """{driver: A (3 rows, a world axis each)}: the local translate a world
    move of 1 asks of each driver, every part moving together. Measured by
    finite differences - three axes, passes until every driver lands."""
    drivers = drivers if drivers is not None else network.drivers(char)
    drivers = [d for d in drivers if len(_free(d)) == 3]
    #  The answer depends on the follow blends and on how the drivers'
    #  parents are turned (a pole's parent turns with the hips), nothing else.
    key = (char.root, tuple(drivers), _follows(drivers),
           tuple(tuple(round(x, 6) for row in _parent3(d) for x in row)
                 for d in drivers))
    cache = _state()["plans"]
    if key in cache:
        return cache[key]
    #  The probes are set and put back inside the caller's undo chunk: they
    #  net to nothing, and turning the undo queue off and on in the middle of
    #  a chunk broke it (measured: one Ctrl+Z left the drag half applied).
    start = {d: _vec(d + ".translate") for d in drivers}
    base = {d: _world_pos(d) for d in drivers}
    result = {}
    try:
        rows = {d: [] for d in drivers}
        for axis in range(3):
            e = tuple(UNIT if k == axis else 0.0 for k in range(3))
            delta = {d: (0.0, 0.0, 0.0) for d in drivers}
            for _ in range(4):
                worst = 0.0
                for d in drivers:
                    now = _world_pos(d)
                    moved = tuple(n - b for n, b in zip(now, base[d]))
                    fix = dragmath.solve_local(e, moved, _parent3(d))
                    worst = max(worst, max(abs(x) for x in fix))
                    delta[d] = tuple(a + b for a, b in zip(delta[d], fix))
                    cmds.setAttr(d + ".translate",
                                 *[s + x for s, x in zip(start[d], delta[d])])
                if worst < 1e-7:
                    break
            for d in drivers:
                rows[d].append(tuple(x / UNIT for x in delta[d]))
                cmds.setAttr(d + ".translate", *start[d])
        result = {d: tuple(rows[d]) for d in drivers}
    finally:
        for d in drivers:
            cmds.setAttr(d + ".translate", *start[d])
    if len(cache) > 64:
        cache.clear()
    cache[key] = result
    return result


def com_of(group):
    return tuple(cmds.getAttr(network.part(group, "sum") + ".output3D")[0])


def _channels_with_curves(drivers):
    out = set()
    for d in drivers:
        for a in ("tx", "ty", "tz"):
            if cmds.listConnections(d + "." + a, source=True, destination=False,
                                    type="animCurve"):
                out.add((d, a))
    return out


def _write(targets):
    for driver, value in targets.items():
        cmds.setAttr(driver + ".translate", *value)


def _key(start, targets, autokey):
    moved = []
    for driver, value in targets.items():
        for i, a in enumerate(("tx", "ty", "tz")):
            if abs(value[i] - start[driver][i]) > 1e-9:
                moved.append((driver, a))
    keyed = dragmath.autokey_channels(moved, _channels_with_curves(list(targets)),
                                      autokey)
    for driver, attr in keyed:
        cmds.setKeyframe(driver, attribute=attr)
    return moved, keyed


def move(group, d, autokey=None):
    """Move the CoM of `group` by world vector `d` (the scripted drag).
    Returns a status line."""
    char = network._character_for(network.root_of(group))
    if autokey is None:
        autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(openChunk=True, chunkName="skeldarComMove")
    try:
        a = plan(char)
        if not a:
            return "%s: nothing to move the CoM with" % char.label
        start = {drv: _vec(drv + ".translate") for drv in a}
        targets = dragmath.apply(a, start, d)
        _write(targets)
        moved, keyed = _key(start, targets, autokey)
    finally:
        cmds.undoInfo(closeChunk=True)
    return summary(char, d, moved, keyed)


def summary(char, d, moved, keyed):
    dist = math.sqrt(sum(x * x for x in d))
    drivers = sorted({m[0].split("|")[-1].split(":")[-1] for m in moved})
    keys = (" - %d key(s) set" % len(keyed)) if keyed else ""
    return "%s: CoM moved %.2f cm - %d control(s)%s" % (char.label, dist,
                                                       len(drivers), keys)


# ------------------------------------------------------------- the context

def ensure_context():
    kw = dict(pressCommand=_press, dragCommand=_drag, releaseCommand=_release,
              cursor="crossHair", space="screen", undoMode="all")
    if cmds.draggerContext(CONTEXT, exists=True):
        cmds.draggerContext(CONTEXT, edit=True, **kw)
    else:
        cmds.draggerContext(CONTEXT, name=CONTEXT, **kw)
    return CONTEXT


def _view():
    import maya.api.OpenMayaUI as omui
    return omui.M3dView.active3dView()


def _ray(x, y):
    """The mouse's ray in world. API 2.0's viewToWorld FILLS the point and
    vector it is handed (it takes four arguments, measured)."""
    import maya.api.OpenMaya as om
    near, direction = om.MPoint(), om.MVector()
    _view().viewToWorld(int(x), int(y), near, direction)
    return (near.x, near.y, near.z), (direction.x, direction.y, direction.z)


def _view_dir():
    import maya.api.OpenMaya as om
    cam = _view().getCamera()
    v = om.MFnCamera(cam).viewDirection(om.MSpace.kWorld)
    return (v.x, v.y, v.z)


def _press():
    st = _state()
    st["press"] = None
    selection = cmds.ls(selection=True, long=True) or []
    groups = handles_only(selection, _group_of_handle)
    if len(groups) != 1:
        _say("Select one CoM handle to move it")
        return
    group = groups[0]
    char = network._character_for(network.root_of(group))
    try:
        a = plan(char)
    except Exception as exc:
        _say("%s: cannot move the CoM (%s)" % (char.label, exc))
        return
    x, y, _ = cmds.draggerContext(CONTEXT, query=True, anchorPoint=True)
    mode = dragmath.mode_for(cmds.draggerContext(CONTEXT, query=True,
                                                 modifier=True))
    com0 = com_of(group)
    view_dir = _view_dir()
    hit0 = dragmath.drag_point(mode, _ray(x, y), com0, view_dir)
    st["press"] = {"group": group, "char": char, "plan": a, "mode": mode,
                   "com0": com0, "hit0": hit0, "view_dir": view_dir,
                   "start": {drv: _vec(drv + ".translate") for drv in a},
                   "xy": (x, y), "moved_px": 0.0, "targets": None}


def _drag():
    st = _state()
    press = st.get("press")
    if not press:
        return
    x, y, _ = cmds.draggerContext(CONTEXT, query=True, dragPoint=True)
    press["moved_px"] = max(press["moved_px"],
                            math.hypot(x - press["xy"][0], y - press["xy"][1]))
    hit = dragmath.drag_point(press["mode"], _ray(x, y), press["com0"],
                              press["view_dir"])
    d = tuple(h - h0 for h, h0 in zip(hit, press["hit0"]))
    if press["mode"] == "floor":
        d = (d[0], 0.0, d[2])
    elif press["mode"] == "vertical":
        d = (0.0, d[1], 0.0)
    press["d"] = d
    press["targets"] = dragmath.apply(press["plan"], press["start"], d)
    _write(press["targets"])
    cmds.refresh(currentView=True)


def _release():
    st = _state()
    press = st.get("press")
    st["press"] = None
    if not press:
        return
    if press["moved_px"] < CLICK_PX or not press.get("targets"):
        if press.get("targets"):
            _write(press["start"])
        _click_select(*press["xy"])
        return
    autokey = cmds.autoKeyframe(query=True, state=True)
    moved, keyed = _key(press["start"], press["targets"], autokey)
    _say(summary(press["char"], press["d"], moved, keyed))


def _click_select(x, y):
    import maya.api.OpenMaya as om
    try:
        om.MGlobal.selectFromScreen(int(x), int(y),
                                    om.MGlobal.kReplaceList,
                                    om.MGlobal.kSurfaceSelectMethod)
    except Exception:
        pass


def _say(message):
    try:
        from maya_com import panel
        panel.status(message)
    except Exception:
        pass
    try:
        cmds.inViewMessage(assistMessage=message, position="topCenter",
                           fade=True, fadeStayTime=1500)
    except Exception:
        pass


# ------------------------------------------------------ switching the tool

def _group_of_handle(path):
    group = network.group_of_part(path)
    if not group:
        return None
    node = path
    if cmds.objectType(node) != "transform":
        node = (cmds.listRelatives(node, parent=True, fullPath=True) or [node])[0]
    if cmds.attributeQuery(network.PART, node=node, exists=True) \
            and cmds.getAttr(node + "." + network.PART) == "handle":
        return group
    return None


def on_selection(*_):
    st = _state()
    selection = cmds.ls(selection=True, long=True) or []
    groups = handles_only(selection, _group_of_handle)
    current = cmds.currentCtx()
    if groups:
        if current != CONTEXT:
            st["previous"] = current
            ensure_context()
            cmds.setToolTo(CONTEXT)
    elif current == CONTEXT:
        cmds.setToolTo(st.get("previous") or "selectSuperContext")
        st["previous"] = None


def on_tool(*_):
    selection = cmds.ls(selection=True, long=True) or []
    has = handles_only(selection, _group_of_handle)
    if should_bounce(cmds.currentCtx(), has):
        cmds.evalDeferred(lambda: (ensure_context(), cmds.setToolTo(CONTEXT)))


def start():
    """The two scriptJobs that put the tool on and take it off."""
    stop()
    st = _state()
    #  the tool is the scene's (2026-10-09): its jobs are the root's, whichever
    #  card's build started them - a popup copy's close must not take them
    with hubcopy.entered(None):
        st["jobs"] = [cmds.scriptJob(event=["SelectionChanged", on_selection]),
                      cmds.scriptJob(event=["ToolChanged", on_tool])]
    st["plans"] = {}


def stop():
    st = _state()
    for job in st.get("jobs", []):
        try:
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
        except Exception:
            pass
    st["jobs"] = []
