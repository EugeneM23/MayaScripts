"""Live proof of the Center of Mass (2026-10-01) - a DISPOSABLE GUI Maya only.

It adds Manny, the Creep and the Orc D to a new scene, keys a take on each,
adds their CoMs through the panel's own presses and lets the real engine run
between sends (its Qt timer needs the event loop). Phases, one send each:

    setup     the three rigs, a take, Add CoM x3, the mass gates, the cost
    trail     (after the engine settles) every trail point = a reference walk
    edit      a key on Manny's RootX_M - only its frames recomputed
    edit2     ... the trail equals the walk again, the others untouched
    static    an unkeyed pole moved on the Creep: every frame dirty
    static2   ... the trail equals the walk again
    tweak     an unkeyed change on a keyed channel survives the engine
    tool      the tool comes on and off with the handle; a simulated drag
              lands the CoM under the cursor, every bone moves by d, Main
              still; one undo puts it all back
    remove    Remove on the Creep: nothing of it left, the others tracked
    picture   a playblast of Manny's trail

Each phase appends to a JSON results file beside its OUT; `run(phase, out)`.
"""

import json
import math
import os
import sys
import time
import traceback

REPO = r"C:/!!!Work/MayaScripts/SkeldarAnim"
RIGS = ("Manny_Rig", "Creep_Rig", "Orc_D_Rig")
TOL = 1e-4


def _fresh_import():
    if sys.path[0] != REPO:
        sys.path.insert(0, REPO)
    for name in list(sys.modules):
        root = name.split(".")[0]
        if root in ("maya_com", "maya_scenesetup", "maya_rigs", "maya_hub",
                    "maya_hubstyle", "maya_hubqt", "maya_hubicons", "maya_overrig",
                    "maya_chargrid", "maya_charlook", "maya_inventory",
                    "maya_invlook", "maya_uebridge", "maya_share",
                    "maya_sharenet", "maya_sharerecords", "maya_graphoverlay",
                    "maya_hotkeys", "maya_vpstudio", "maya_colour",
                    "maya_rig_retarget", "maya_asretarget", "maya_pmretarget",
                    "maya_update", "skeldar_features"):
            del sys.modules[name]


class Gates(object):

    def __init__(self, out):
        self.out = out
        self.lines = []
        self.failed = 0

    def gate(self, name, ok, detail=""):
        self.lines.append("%s %s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            self.failed += 1

    def note(self, text):
        self.lines.append("     " + text)

    def write(self):
        with open(self.out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(self.lines))
            fh.write("\n%d failed\nDONE\n" % self.failed)


def _state():
    st = getattr(sys, "_verify_com", None)
    if st is None:
        st = {}
        sys._verify_com = st
    return st


def _com(group):
    import maya.cmds as cmds
    from maya_com import network
    return tuple(cmds.getAttr(network.part(group, "sum") + ".output3D")[0])


def _reference(groups, span):
    """{uuid: {frame: point}} by walking the time the plain way."""
    import maya.cmds as cmds
    here = cmds.currentTime(q=True)
    out = {cmds.ls(g, uuid=True)[0]: {} for g in groups}
    for f in range(span[0], span[1] + 1):
        cmds.currentTime(f, update=True)
        for g in groups:
            out[cmds.ls(g, uuid=True)[0]][f] = _com(g)
    cmds.currentTime(here, update=True)
    return out


def _worst(track, ref):
    worst = 0.0
    for f, p in ref.items():
        q = track.points.get(f)
        if q is None:
            return float("inf")
        worst = max(worst, max(abs(a - b) for a, b in zip(q[:3], p)))
    return worst


def _groups():
    from maya_com import network
    return network.find_all()


def _group_of(namespace):
    for g in _groups():
        if g.split("|")[-1].startswith(namespace + ":"):
            return g
    return None


def _key_take(ns):
    import maya.cmds as cmds
    chans = {"RootX_M": [("tx", 20), ("tz", 35), ("ry", 30)],
             "FKShoulder_L": [("rz", 40)], "FKElbow_R": [("rz", 50)],
             "IKLeg_L": [("tz", 25), ("ty", 10)], "FKSpine1_M": [("rz", 20)],
             "FKNeck_M": [("rx", 15)]}
    for c, items in chans.items():
        node = ns + ":" + c
        if not cmds.objExists(node):
            continue
        for ch, amp in items:
            base = cmds.getAttr(node + "." + ch)
            for f in range(0, 61, 5):
                cmds.setKeyframe(node, attribute=ch, time=f,
                                 value=base + amp * math.sin(f / 60.0 * 2 * math.pi))


# ------------------------------------------------------------------ phases

def phase_setup(g):
    import maya.cmds as cmds
    import maya.api.OpenMaya as om
    import numpy as np
    cmds.file(new=True, force=True)
    for p in ("matrixNodes", "quatNodes"):
        cmds.loadPlugin(p, quiet=True)
    _fresh_import()
    from maya_scenesetup import catalog, character
    from maya_com import network, panel, engine, massmodel
    cmds.playbackOptions(minTime=0, maxTime=60, animationStartTime=0,
                         animationEndTime=60)
    cmds.evaluationManager(mode="parallel")
    for i, key in enumerate(RIGS):
        character.add_character(catalog.character_by_key(key), at=(i * 150.0, 0, 0))
    cmds.currentTime(0)
    #  the rig's cost before any CoM. Cached Playback refills in background
    #  threads after every graph change and steals the CPU from a foreground
    #  walk (15 then 11 ms for the same scene, measured): it is off for the
    #  measurement, and the best of five runs counts.
    def per_frame(n=60, runs=5):
        cache = cmds.evaluator(name="cache", query=True, enable=True)
        cmds.evaluator(name="cache", enable=False)
        best = float("inf")
        cmds.refresh(suspend=True)
        try:
            for _ in range(runs):
                t0 = time.time()
                for f in range(n):
                    cmds.currentTime(f % 60, update=True)
                best = min(best, (time.time() - t0) * 1000.0 / n)
        finally:
            cmds.refresh(suspend=False)
            cmds.evaluator(name="cache", enable=cache)
        return best
    for key in RIGS:
        _key_take(key)
    per_frame(10)
    before = per_frame()
    #  the panel in a window of its own: the whole hub would start Shared
    #  listening on the studio's channel from a disposable Maya
    if cmds.window("verifyComWindow", exists=True):
        cmds.deleteUI("verifyComWindow")
    cmds.window("verifyComWindow", title="CoM verify", width=380)
    panel.build_panel()
    cmds.showWindow("verifyComWindow")
    for key in RIGS:
        cmds.select(key + ":Main", replace=True)
        msg = panel.add()
        g.note(msg)
    groups = _groups()
    g.gate("three CoMs added", len(groups) == 3, str(len(groups)))
    per_frame(10)
    after = per_frame()
    #  A GUI Maya swings +-0.6 ms a rig run to run (measured over five runs:
    #  -1.3, -1.75, 0, -0.4, +1.6 ms for three rigs); the precise A/B is
    #  verify_com_cost.py in mayapy (no measurable cost). This gate only
    #  catches a network that costs more than the noise.
    g.gate("the three networks and the engine cost no more than the noise",
           (after - before) / 3.0 < 0.8, "%.2f -> %.2f ms for 3 rigs" % (before, after))
    #  mass sanity on Manny
    char = network._character_for("|Manny_Rig:root")
    mg = network.group_for(char)
    vol = cmds.getAttr(mg + ".volume")
    g.gate("Manny's volume is a person's (70-95 L)", 70 <= vol <= 95, "%.1f L" % vol)
    cmds.currentTime(0, update=True)
    low = cmds.exactWorldBoundingBox("Manny_Rig:Skin_3p")[1]
    height = cmds.getAttr(mg + ".height")
    ratio = (_com(mg)[1] - low) / height
    g.gate("Manny's CoM at 0.53-0.60 of stature at frame 0", 0.53 <= ratio <= 0.60,
           "%.3f" % ratio)
    #  each DG CoM equals its formula at a posed frame
    cmds.currentTime(23, update=True)
    for key in RIGS:
        grp = _group_of(key)
        rows = []
        wt = None
        for uuid in cmds.getAttr(grp + "." + network.NODES).split():
            n = (cmds.ls(uuid, long=True) or [None])[0]
            if n and cmds.objectType(n) == "wtAddMatrix" and n.endswith("comWt"):
                wt = n
        total = np.zeros(3)
        mass = 0.0
        for idx in range(cmds.getAttr(wt + ".wtMatrix", size=True)):
            joint = cmds.listConnections("%s.wtMatrix[%d].matrixIn" % (wt, idx),
                                         source=True)[0]
            w = cmds.getAttr("%s.wtMatrix[%d].weightIn" % (wt, idx))
            m = np.array(cmds.getAttr(joint + ".worldMatrix[0]")).reshape(4, 4)
            total += w * m[3, :3]
            mass += w
        g.gate("%s: the weights sum to one" % key, abs(mass - 1.0) < 1e-6,
               "%.9f" % mass)
        g.note("%s: CoM at f23 %s, volume %.1f L" % (key, tuple(round(x, 2) for x in _com(grp)),
                                                   cmds.getAttr(grp + ".volume")))
    #  Maya answers the flag as the STRING '0' (measured), which is truthy
    st = cmds.cacheEvaluator(query=True, safeModeTriggered=True)
    g.gate("Cached Playback stays out of safe mode", str(st) in ("0", "False"),
           repr(st))
    cmds.currentTime(10, update=True)
    _state()["t_setup"] = time.time()


def phase_trail(g):
    import maya.cmds as cmds
    from maya_com import engine
    st = engine.state()
    g.note("engine: pending %d, stats %s, error %s" % (engine.pending(), st["stats"],
                                                     st.get("last_error")))
    g.gate("the engine settled by itself", engine.pending() == 0,
           "pending %d" % engine.pending())
    groups = _groups()
    ref = _reference(groups, (0, 60))
    for grp in groups:
        uuid = cmds.ls(grp, uuid=True)[0]
        worst = _worst(st["tracks"][uuid], ref[uuid])
        g.gate("%s: every trail point = the walk" % grp.split("|")[-1], worst < TOL,
               "%.2e" % worst)
        from maya_com import network
        shape = network.trail_shape(grp)
        pts = cmds.getAttr(shape + ".points")
        g.gate("%s: the shape holds 61 points" % grp.split("|")[-1], len(pts) == 61,
               str(len(pts)))
    g.gate("the first full trail's slices stayed under 1 s",
           st["stats"]["longest_ms"] < 1000, "longest %.1f ms (the first slices pay "
           "the EM's graph rebuild)" % st["stats"]["longest_ms"])
    _state()["ref"] = ref
    st["stats"]["longest_ms"] = 0.0
    st["stats"]["walked"] = 0
    st["stats"]["slices"] = 0


def phase_edit(g):
    import maya.cmds as cmds
    from maya_com import engine
    st = engine.state()
    cmds.currentTime(12, update=True)
    st["stats"].update(walked=0, slices=0, longest_ms=0.0)
    _state()["t_edit"] = time.time()
    cmds.setKeyframe("Manny_Rig:RootX_M", attribute="tx", time=30, value=55)
    g.note("key set at %.3f" % _state()["t_edit"])


def phase_edit2(g):
    import maya.cmds as cmds
    from maya_com import engine
    st = engine.state()
    walked = st["stats"]["walked"]
    latency = st["stats"].get("last_write", 0) - _state()["t_edit"]
    g.gate("the edit recomputed only its frames (21..39 changed)", 15 <= walked <= 21,
           "walked %d in %d slices" % (walked, st["stats"]["slices"]))
    g.gate("the trail was redrawn within 0.6 s of the key (three rigs)",
           0 < latency < 0.6,
           "%.3f s, longest slice %.1f ms" % (latency, st["stats"]["longest_ms"]))
    g.gate("no slice over 100 ms (three rigs evaluate at every step)",
           st["stats"]["longest_ms"] < 100,
           "%.1f ms" % st["stats"]["longest_ms"])
    groups = _groups()
    ref = _reference(groups, (0, 60))
    old = _state()["ref"]
    for grp in groups:
        uuid = cmds.ls(grp, uuid=True)[0]
        worst = _worst(st["tracks"][uuid], ref[uuid])
        g.gate("%s: the trail = the walk after the edit" % grp.split("|")[-1],
               worst < TOL, "%.2e" % worst)
        if not grp.split("|")[-1].startswith("Manny_Rig"):
            same = max(max(abs(a - b) for a, b in zip(ref[uuid][f], old[uuid][f]))
                       for f in ref[uuid])
            g.gate("%s: untouched by Manny's edit" % grp.split("|")[-1], same < 1e-9,
                   "%.2e" % same)
    _state()["ref"] = ref


def phase_static(g):
    import maya.cmds as cmds
    from maya_com import engine
    st = engine.state()
    st["stats"].update(walked=0, slices=0, longest_ms=0.0)
    node = "Creep_Rig:PoleLeg_L"
    has = cmds.listConnections(node + ".tx", type="animCurve")
    g.gate("the Creep's left pole carries no keys", not has)
    _state()["t_static"] = time.time()
    cmds.setAttr(node + ".tx", cmds.getAttr(node + ".tx") + 25)


def phase_static2(g):
    import maya.cmds as cmds
    from maya_com import engine
    st = engine.state()
    #  the current frame is read live, not walked: 60 walked + 1 live
    g.gate("a static change recomputed every frame", st["stats"]["walked"] >= 60,
           "walked %d, longest %.1f ms, %.2f s" % (
               st["stats"]["walked"], st["stats"]["longest_ms"],
               st["stats"].get("last_write", 0) - _state()["t_static"]))
    groups = _groups()
    ref = _reference(groups, (0, 60))
    for grp in groups:
        uuid = cmds.ls(grp, uuid=True)[0]
        worst = _worst(st["tracks"][uuid], ref[uuid])
        g.gate("%s: the trail = the walk after the pole" % grp.split("|")[-1],
               worst < TOL, "%.2e" % worst)
    _state()["ref"] = ref


def phase_tweak(g):
    import maya.cmds as cmds
    from maya_com import engine
    cmds.currentTime(20, update=True)
    plug = "Manny_Rig:FKShoulder_L.rz"
    cmds.setAttr(plug, 77)
    _state()["tweak"] = plug
    #  something else dirty, so the engine walks while the tweak stands
    cmds.setKeyframe("Orc_D_Rig:RootX_M", attribute="tz", time=40, value=-20)


def phase_tweak2(g):
    import maya.cmds as cmds
    from maya_com import engine
    st = engine.state()
    g.gate("the engine walked meanwhile", st["stats"]["walked"] > 0,
           str(st["stats"]["walked"]))
    value = cmds.getAttr(_state()["tweak"])
    g.gate("the unkeyed tweak survived the walk", abs(value - 77) < 1e-6, "%.6f" % value)
    grp = _group_of("Manny_Rig")
    uuid = cmds.ls(grp, uuid=True)[0]
    live = _com(grp)
    point = st["tracks"][uuid].points.get(20)
    g.gate("the trail's current point is the live (tweaked) CoM",
           point is not None and max(abs(a - b) for a, b in zip(point[:3], live)) < TOL,
           "%s vs %s" % (point and tuple(round(x, 3) for x in point[:3]),
                         tuple(round(x, 3) for x in live)))
    cmds.currentTime(21, update=True)
    cmds.currentTime(20, update=True)


def phase_tool(g):
    import maya.cmds as cmds
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaUI as omui
    import numpy as np
    from maya_com import drag, network
    grp = _group_of("Manny_Rig")
    handle = network.part(grp, "handle")
    cmds.setToolTo("moveSuperContext")
    cmds.select("Manny_Rig:pelvis", replace=True)
    drag.on_selection()
    cmds.select(handle, replace=True)
    drag.on_selection()
    g.gate("selecting the handle puts the CoM tool on",
           cmds.currentCtx() == drag.CONTEXT, cmds.currentCtx())
    cmds.select("Manny_Rig:pelvis", replace=True)
    drag.on_selection()
    g.gate("selecting a bone gives the Move tool back",
           cmds.currentCtx() == "moveSuperContext", cmds.currentCtx())
    cmds.select(handle, replace=True)
    drag.on_selection()
    #  a drag simulated through the context's own functions
    cmds.currentTime(15, update=True)
    view = omui.M3dView.active3dView()
    com0 = np.array(_com(grp))
    x, y, _ = view.worldToView(om.MPoint(*com0))
    points = {"anchorPoint": [float(x), float(y), 0.0],
              "dragPoint": [float(x) + 80.0, float(y) + 30.0, 0.0],
              "modifier": "none"}
    real = drag.cmds.draggerContext

    def fake(name, **kw):
        if kw.get("query"):
            for k in ("anchorPoint", "dragPoint", "modifier"):
                if kw.get(k):
                    return points[k]
        return real(name, **kw)
    joints = network.mass_joints(grp)
    j0 = {j: np.array(cmds.xform(j, q=True, ws=True, t=True)) for j in joints}
    main0 = np.array(cmds.xform("Manny_Rig:Main", q=True, ws=True, t=True))
    tx_key0 = cmds.keyframe("Manny_Rig:RootX_M.tx", query=True, time=(15, 15),
                            valueChange=True)
    cmds.autoKeyframe(state=True)
    drag.cmds.draggerContext = fake
    cmds.undoInfo(openChunk=True, chunkName="verifyComDrag")
    try:
        t0 = time.time()
        drag._press()
        t_press = time.time() - t0
        drag._drag()
        drag._release()
    finally:
        cmds.undoInfo(closeChunk=True)
        drag.cmds.draggerContext = real
    #  autoKey goes off only after the undo gate: `autoKeyframe -state` is
    #  itself an undoable command, and a Ctrl+Z would undo IT, not the drag
    com1 = np.array(_com(grp))
    near, direction = om.MPoint(), om.MVector()
    view.viewToWorld(int(points["dragPoint"][0]), int(points["dragPoint"][1]),
                     near, direction)
    #  the CoM lies on the cursor's ray, in the view plane through com0
    ray_o, ray_d = np.array([near.x, near.y, near.z]), np.array([direction.x, direction.y, direction.z])
    to = com1 - ray_o
    off_ray = np.linalg.norm(to - np.dot(to, ray_d / np.linalg.norm(ray_d)) * ray_d / np.linalg.norm(ray_d))
    g.gate("the press measured its plan in under 150 ms", t_press < 0.15, "%.0f ms" % (t_press * 1000))
    g.gate("the dragged CoM sits under the cursor", off_ray < 0.05, "%.4f cm off the ray" % off_ray)
    d = com1 - com0
    worst = max(np.abs(np.array(cmds.xform(j, q=True, ws=True, t=True)) - j0[j] - d).max()
                for j in joints)
    g.gate("every weighed bone moved by the same d", worst < 1e-3,
           "d %s, worst %.2e" % (tuple(round(x, 2) for x in d), worst))
    g.gate("Main did not move", np.abs(np.array(cmds.xform("Manny_Rig:Main", q=True, ws=True, t=True)) - main0).max() < 1e-9)
    tx_key1 = cmds.keyframe("Manny_Rig:RootX_M.tx", query=True, time=(15, 15),
                            valueChange=True)
    tx_now = cmds.getAttr("Manny_Rig:RootX_M.tx")
    g.gate("autoKey keyed RootX_M.tx at the frame with its new value",
           tx_key1 and abs(tx_key1[0] - tx_now) < 1e-6 and tx_key1 != tx_key0,
           "%s -> %s (now %.4f)" % (tx_key0, tx_key1, tx_now))
    cmds.undo()
    back = np.abs(np.array(_com(grp)) - com0).max()
    g.gate("one undo puts the drag back", back < 1e-6, "%.2e" % back)
    cmds.autoKeyframe(state=False)
    cmds.select(clear=True)
    drag.on_selection()


def phase_remove(g):
    import maya.cmds as cmds
    from maya_com import engine, network, panel
    grp = _group_of("Creep_Rig")
    uuids = cmds.getAttr(grp + "." + network.NODES).split()
    cmds.select("Creep_Rig:Main", replace=True)
    g.note(panel.remove())
    left = [u for u in uuids if cmds.ls(u)]
    g.gate("Remove leaves nothing of the Creep's CoM", not left and not cmds.objExists(grp),
           str(left))
    g.gate("the other two are still tracked", len(engine.state()["tracks"]) == 2,
           str(len(engine.state()["tracks"])))


def phase_picture(g):
    import maya.cmds as cmds
    cam = "persp"
    cmds.setAttr(cam + ".translate", 230, 190, 300)
    cmds.setAttr(cam + ".rotate", -14, 38, 0)
    for panel in cmds.getPanel(type="modelPanel") or []:
        cmds.modelEditor(panel, edit=True, camera=cam)
    cmds.currentTime(15, update=True)
    cmds.select(clear=True)
    path = os.path.join(os.path.dirname(_state().get("out", "")) or ".", "com_trail.png")
    cmds.playblast(frame=[15], format="image", compression="png",
                   completeFilename=path, viewer=False, showOrnaments=False,
                   percent=100, widthHeight=(1280, 720), forceOverwrite=True)
    g.note("picture " + path)


PHASES = {name[6:]: fn for name, fn in globals().items() if name.startswith("phase_")}


def run(phase, out):
    g = Gates(out)
    _state()["out"] = out
    try:
        PHASES[phase](g)
    except Exception:
        g.gate("phase %s ran" % phase, False, traceback.format_exc())
    g.write()
