"""Gates for the plugin's bakes and layer writes under a Scene Time Warp (2026-10-20).

    mayapy verify_timewarp.py            (standalone)
    or exec'd over a command port        (a GUI Maya: it opens new scenes - a disposable one)

Every case builds its own scene, adds a NON-LINEAR scene time warp (scene frames 0 / 20 / 40 play
curve times 0 / 8 / 40), records what the scene SHOWS at the scene frames whose warped time is a
whole frame (0, 5, 10 ... 40 -> 0, 2, 4 ... 40), presses a tool that must not change the take, and
reads it again. Each tool is pressed twice: with `maya_timewarp` working, and - the control that
proves the gate can fail - with `maya_timewarp.active` answering False (the build before).

- `maya_timewarp.unwarped`: the warp off inside, on after, nested once, no undo step, nothing
  without a warp;
- Tools > Layer on an object parent-constrained to a keyed locator;
- Tools > Knot made, then Bake;
- Tools > Snapshot: the snapshot on its object;
- Tools > Inside: an object keyed under a moving parent keeps its world track;
- Time Bar > the layer panel's Merge (an override layer over keys) keeps what shows;
- Connections FK -> IK on Manny_Rig's right arm keyed by hand.
"""
import math
import sys

try:
    import maya.standalone
    maya.standalone.initialize()
    STANDALONE = True
except Exception:                                        # noqa: BLE001 - inside a GUI Maya
    STANDALONE = False
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
for _m in list(sys.modules):
    if _m.split(".")[0].startswith(("maya_", "skeldar_")):
        del sys.modules[_m]
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)
for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:                                    # noqa: BLE001
        pass

import maya_timewarp  # noqa: E402

FAILS = []
COUNT = [0]
SCENE = list(range(0, 41, 5))          # scene frames whose warped time is a whole frame
REAL_ACTIVE = maya_timewarp.active


def gate(ok, msg):
    COUNT[0] += 1
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(COUNT[0])


def fresh():
    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    cmds.currentTime(0)


def warp():
    w = cmds.createNode("animCurveTT", name="timewarp")
    cmds.connectAttr(w + ".apply", "time1.timewarpIn_Raw")
    for f, v in ((0, 0), (20, 8), (40, 40)):
        cmds.setKeyframe(w, time=f, value=v)
    cmds.keyTangent(w, inTangentType="linear", outTangentType="linear")
    cmds.setAttr("time1.enableTimewarp", 1)
    return w


def keyed(node, attr, pairs):
    for t, v in pairs:
        cmds.setKeyframe(node, attribute=attr, time=t, value=v)


def world(nodes):
    """{(node, frame): world matrix} at the scene frames, by a real time change."""
    out = {}
    here = cmds.currentTime(q=True)
    for f in SCENE:
        cmds.currentTime(f)
        for n in nodes:
            out[(n, f)] = om.MMatrix(cmds.xform(n, q=True, matrix=True, worldSpace=True))
    cmds.currentTime(here)
    return out


def ang(a, b):
    qa = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    q = qa.inverse() * qb
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def diff(a, b, pairs=None):
    cm = deg = 0.0
    for key in (pairs or a):
        x, y = a[key], b[key if not pairs else pairs[key]]
        cm = max(cm, (om.MVector(x[12], x[13], x[14]) - om.MVector(y[12], y[13], y[14])).length())
        deg = max(deg, ang(x, y))
    return cm, deg


def both(name, build, press, nodes_of, tol=(1e-3, 1e-3), compare=None):
    """`press` on a warped scene with the fix and without it (the control)."""
    out = {}
    for fixed in (True, False):
        maya_timewarp.active = REAL_ACTIVE if fixed else (lambda: False)
        try:
            fresh()
            made = build()
            warp()
            nodes = nodes_of(made)
            before = world(nodes)
            text = press(made)
            after = world(compare(made) if compare else nodes)
            pairs = None
            if compare:
                pairs = dict(((n, f), (m, f)) for n, m in zip(nodes, compare(made)) for f in SCENE)
            out[fixed] = (diff(before, after, pairs), text)
        finally:
            maya_timewarp.active = REAL_ACTIVE
    (cm, deg), text = out[True]
    (ccm, cdeg), _ = out[False]
    gate(cm < tol[0] and deg < tol[1] and (ccm > 0.05 or cdeg > 0.05),
         "%s under the warp: the take kept to %.5f cm, %.5f deg (without the fix %.3f cm, %.3f deg)"
         " | %s" % (name, cm, deg, ccm, cdeg, str(text).splitlines()[0][:110] if text else ""))


# ----------------------------------------------------------------- the switch itself
fresh()
cube = cmds.polyCube(name="cube")[0]
keyed(cube, "tx", ((0, 0), (40, 40)))
gate(not maya_timewarp.active(), "no warp: inactive, %s" % cmds.getAttr("time1.enableTimewarp"))
was = cmds.getAttr("time1.enableTimewarp")
with maya_timewarp.unwarped():
    gate(cmds.getAttr("time1.enableTimewarp") == was, "no warp: unwarped() touches nothing")
w = warp()
cmds.currentTime(20)
shown = cmds.getAttr(cube + ".tx")
undo_name = cmds.undoInfo(q=True, undoName=True)
with maya_timewarp.unwarped():
    off_value = cmds.getAttr(cube + ".tx")
    with maya_timewarp.unwarped():
        inner = cmds.getAttr("time1.enableTimewarp")
    after_inner = cmds.getAttr("time1.enableTimewarp")
curve = cmds.listConnections(cube + ".tx", source=True, destination=False)[0]
at8, at20 = (cmds.keyframe(curve, q=True, eval=True, time=(t, t))[0] for t in (8, 20))
gate(abs(shown - at8) < 1e-6 and abs(off_value - at20) < 1e-6 and not inner and not after_inner
     and cmds.getAttr("time1.enableTimewarp") and abs(cmds.getAttr(cube + ".tx") - at8) < 1e-6
     and cmds.undoInfo(q=True, undoName=True) == undo_name,
     "unwarped(): frame 20 shows %.3f (curve time 8), %.3f inside (curve time), off through a nested block, "
     "on after, no undo step (%r)" % (shown, off_value, undo_name))


# ----------------------------------------------------------------- Tools > Layer
def build_constrained():
    loc = cmds.spaceLocator(name="drv")[0]
    keyed(loc, "tz", ((0, 0), (12, 20), (30, -10), (40, 5)))
    keyed(loc, "ry", ((0, 0), (12, 80), (30, -40), (40, 20)))
    k = cmds.polyCube(name="K")[0]
    cmds.parentConstraint(loc, k)
    return k


def layer(k):
    from maya_tools import layerbake
    cmds.select(k)
    return layerbake.bake([k], highlight=None)


both("Tools > Layer (a constrained object)", build_constrained, layer, lambda k: [k])


# ----------------------------------------------------------------- Tools > Knot, then Bake
def build_keyed():
    c = cmds.polyCube(name="C")[0]
    keyed(c, "tx", ((0, 0), (10, 15), (25, 5), (40, 30)))
    keyed(c, "rz", ((0, 0), (10, 45), (25, 15), (40, 90)))
    p = cmds.spaceLocator(name="P")[0]
    keyed(p, "ty", ((0, 0), (16, 30), (40, -10)))
    keyed(p, "rx", ((0, 0), (16, 60), (40, 10)))
    cmds.parent(c, p)
    return cmds.ls(c, long=True)[0]


def knot_and_bake(c):
    from maya_tools import knots
    made = knots.create("knot", [c], highlight=None)
    text = knots.bake(knots.knots())
    return "%s / %s" % (made, text)


both("Tools > Knot, then Bake", build_keyed, knot_and_bake, lambda c: [c])


# ----------------------------------------------------------------- Tools > Snapshot
def snapshot(c):
    from maya_tools import knots
    return knots.snapshot([c], highlight=None)


def the_snapshot(c):
    from maya_tools import knots
    return [knots.snapshots()[0]]


both("Tools > Snapshot (the snapshot on its object)", build_keyed, snapshot, lambda c: [c],
     compare=the_snapshot)


# ----------------------------------------------------------------- Tools > Inside / To world
def to_world(c):
    from maya_tools import reparent
    return reparent.to_world([c])


def world_node(c):
    return cmds.ls("|C", long=True) or cmds.ls("C", long=True)


both("Tools > To world (keyed under a moving parent)", build_keyed, to_world, lambda c: [c],
     compare=world_node)


# ----------------------------------------------------------------- Time Bar > Merge
def build_layered():
    c = cmds.polyCube(name="L")[0]
    keyed(c, "tx", ((0, 0), (10, 15), (25, 5), (40, 30)))
    loc = cmds.spaceLocator(name="ldrv")[0]
    keyed(loc, "ty", ((0, 0), (12, 20), (30, -10), (40, 5)))
    cmds.select(c)
    cmds.animLayer("Over", addSelectedObjects=True, override=True)
    con = cmds.pointConstraint(loc, c, skip=["x", "z"])[0]
    cmds.bakeResults(c, attribute=["ty"], time=(0, 40), simulation=False, destinationLayer="Over")
    cmds.delete(con)
    return c


def merge(c):
    from maya_timebar import layerscene
    root = cmds.animLayer(q=True, root=True)
    return layerscene.merge_selected([root, "Over"])


both("Time Bar > Merge (an override layer into the base)", build_layered, merge, lambda c: [c])


# ----------------------------------------------------------------- Connections FK -> IK
def build_rig():
    from maya_scenesetup import catalog, character
    import maya_rigs
    character.add_character(catalog.character_by_key("Manny_Rig"))
    rig = maya_rigs.rigs()[0]
    for leaf, attr, pairs in (("FKShoulder_R", "rz", ((0, 0), (16, 40), (40, -20))),
                              ("FKElbow_R", "rz", ((0, -30), (24, -80), (40, -10))),
                              ("FKWrist_R", "ry", ((0, 0), (8, 30), (32, -30), (40, 0)))):
        keyed(maya_rigs.node(rig, leaf), attr, pairs)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    return rig


def switch_ik(rig):
    from maya_scenesetup import connections as cx, fkik
    return cx.switch_arm("R", fkik.IK, rig=rig, highlight=False)


def arm_bones(rig):
    import maya_rigs
    return [cmds.ls(maya_rigs.node(rig, b), long=True)[0] for b in ("lowerarm_r", "hand_r")]


SCENE[:] = [0, 20, 25, 30, 35, 40]    # the arm's keys (curve 0, 8, 16, 24, 32, 40): the switch keys there
try:
    both("Connections FK -> IK (Manny_Rig's right arm keyed by hand)", build_rig, switch_ik,
         arm_bones, tol=(0.05, 0.05))
except Exception as problem:                             # noqa: BLE001
    import traceback
    traceback.print_exc()
    gate(False, "Connections FK -> IK raised %r" % problem)



# ----------------------------------------------------------------- Tools > 1P Setup
def build_take():
    rig = build_rig()
    import maya_rigs
    for leaf, attr, pairs in (("FKSpine3_M", "rx", ((0, 0), (16, 25), (40, -10))),
                              ("RootX_M", "tz", ((0, 0), (24, 60), (40, 90))),
                              ("FKNeck_M", "ry", ((0, 0), (8, 30), (40, -20)))):
        keyed(maya_rigs.node(rig, leaf), attr, pairs)
    return rig


def first_person(rig):
    import maya_rigs
    from maya_tools import firstperson
    return firstperson.setup([maya_rigs.node(rig, "Main")])


def body_bones(rig):
    import maya_rigs
    return [cmds.ls(maya_rigs.node(rig, b), long=True)[0]
            for b in ("pelvis", "spine_03", "head", "hand_r", "lowerarm_r")]


SCENE[:] = list(range(0, 41, 5))
try:
    both("Tools > 1P Setup (a Manny take onto its two layers)", build_take, first_person, body_bones,
         tol=(0.01, 0.01))
except Exception as problem:                             # noqa: BLE001
    import traceback
    traceback.print_exc()
    gate(False, "1P Setup raised %r" % problem)

print("%d gates, %d failed%s" % (COUNT[0], len(FAILS), (": %s" % FAILS) if FAILS else ""))
if STANDALONE:
    maya.standalone.uninitialize()
