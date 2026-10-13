"""Standalone gates for the Tools card's aim tab: Aim and Overlap (2026-10-13).

    mayapy verify_aim_overlap.py

mayapy STANDALONE, a fresh scene per case (spec
docs/superpowers/specs/2026-10-13-tools-aim-overlap-design.md).

Aim, on verify_knots' prop (a cube under an animated carrier, rotate pivot off its origin, zxy,
keyed tx / rx / ry, frames 0..40, the current frame 12) with every rotate free:
A  begin: the target and up ride the prop; finish: nothing moves; the knot's shape; the target
   moved turns the prop onto it; the up moved rolls it and it still aims; attach 0 the original;
   Remove restores every curve.
B  Bake keeps an edit and leaves nothing.
C  Undo of a finish brings the waiting aim back.
D  A ranged aim: attach 0/1/1/0, an edit only inside.
E  Refusals change nothing; Remove drops a waiting aim.
F  A Manny rig control: the head bone does not move at creation and turns with the target.

Overlap, on a joint chain j0..j4 along X (10 cm), j0 keyed rz = 40 sin(2 pi t / 48) on every frame
0..48:
O1 the layer, marked, the base untouched.  O2 the root delayed by exactly the lag.
O3 the tip trails.  O4 refusals.  O5 keep edges.  O6 cycled.  O7 a second press replaces.
O8 one undo.  O9 a highlight.  O10 the selection mode.  O11 positions follow a loose chain.
O12 a knotted member refused.  O13 an AdvancedSkeleton finger chain on Manny.
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
for _plugin in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(_plugin, quiet=True)
    except Exception:
        pass

from maya_tools import knotplan as plan, knots, overlap, overlapplan  # noqa: E402

FAILS = []
COUNT = [0]
CASE = ["-"]
FRAMES = list(range(0, 41))
EPS_CM, EPS_DEG = 1e-3, 1e-3


def case(name):
    CASE[0] = name
    print("--- %s" % name)


def gate(ok, msg):
    COUNT[0] += 1
    print("%s gate %02d [%s]: %s" % ("PASS" if ok else "FAIL", COUNT[0], CASE[0], msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append((CASE[0], COUNT[0], msg))


# ------------------------------------------------------------------ measure

def wm(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def rot(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def ang(qa, qb):
    q = qa.inverse() * qb
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def pivot(node):
    return om.MVector(*cmds.xform(node, query=True, worldSpace=True, rotatePivot=True))


def where(node):
    return om.MVector(*cmds.xform(node, query=True, worldSpace=True, translation=True))


def track(node, frames=FRAMES):
    """{frame: (world pivot, world rotation)} by a real time walk (trap 69)."""
    out = {}
    now = cmds.currentTime(query=True)
    for f in frames:
        cmds.currentTime(f, update=True)
        out[f] = (pivot(node), rot(wm(node)))
    cmds.currentTime(now, update=True)
    return out


def diff(a, b, frames=None):
    cm = deg = 0.0
    for f in (frames if frames is not None else a):
        cm = max(cm, (a[f][0] - b[f][0]).length())
        deg = max(deg, ang(a[f][1], b[f][1]))
    return cm, deg


def same(a, b, frames=None, eps_deg=EPS_DEG):
    cm, deg = diff(a, b, frames)
    return cm < EPS_CM and deg < eps_deg, "%.6f cm, %.6f deg" % (cm, deg)


def curves(node, channels=plan.CHANNELS):
    out = {}
    for ch in channels:
        plug = node + "." + ch
        found = cmds.listConnections(plug, source=True, destination=False) or []
        if found and cmds.nodeType(found[0]).startswith("animCurve"):
            out[ch] = (tuple(cmds.keyframe(found[0], query=True, timeChange=True)),
                       tuple(round(v, 9) for v in cmds.keyframe(found[0], query=True,
                                                                 valueChange=True)))
        elif found:
            out[ch] = ("driven by", cmds.nodeType(found[0]))
        else:
            out[ch] = round(cmds.getAttr(plug), 9)
    return out


def nudge(node, ch, delta):
    plug = node + "." + ch
    if cmds.getAttr(plug, lock=True):
        cmds.setAttr(plug, lock=False)
    if cmds.keyframe(plug, query=True, keyframeCount=True):
        cmds.keyframe(plug, edit=True, relative=True, valueChange=delta)
    else:
        cmds.setAttr(plug, cmds.getAttr(plug) + delta)


def make_prop():
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    cmds.currentTime(0)
    carrier = cmds.createNode("transform", name="carrier")
    for t, ty, ry in ((0, 0.0, 0.0), (40, 20.0, 45.0)):
        cmds.setKeyframe(carrier, attribute="ty", time=t, value=ty)
        cmds.setKeyframe(carrier, attribute="ry", time=t, value=ry)
    prop = cmds.polyCube(name="prop", width=2, height=6, depth=1)[0]
    prop = cmds.parent(prop, carrier)[0]
    prop = cmds.ls(prop, long=True)[0]
    cmds.setAttr(prop + ".rotateOrder", 2)                     # zxy
    cmds.setAttr(prop + ".rotatePivot", 0, 2, 0, type="double3")
    cmds.setAttr(prop + ".scalePivot", 0, 2, 0, type="double3")
    for t, tx in ((0, 0.0), (20, 10.0), (40, 0.0)):
        cmds.setKeyframe(prop, attribute="tx", time=t, value=tx)
    for t, ry in ((0, 0.0), (40, 90.0)):
        cmds.setKeyframe(prop, attribute="ry", time=t, value=ry)
    for t, rx in ((0, 0.0), (30, 40.0)):
        cmds.setKeyframe(prop, attribute="rx", time=t, value=rx)
    cmds.setAttr(prop + ".ty", 1.0)
    cmds.setAttr(prop + ".rz", 5.0)
    cmds.currentTime(12)
    cmds.select(clear=True)
    return prop


def aim_of(obj):
    found = [k for k in knots.knots() if knots.source_of(k) == obj]
    return found[0] if found else None


def parts(top):
    kids = cmds.listRelatives(top, children=True, type="transform", fullPath=True) or []
    target = [k for k in kids if k.endswith(plan.AIM_TARGET_SUFFIX)]
    up = [k for k in kids if k.endswith("_aimUp")]
    return (target[0] if target else None), (up[0] if up else None)


def aim_error(obj, target, con):
    """The angle between the constraint's aim vector and where the target stands, in the
    object's own axes - after a real time change."""
    p, t = pivot(obj), where(target)
    rows = plan.axes_of(cmds.getAttr(obj + ".worldMatrix[0]"))
    v = [t[i] - p[i] for i in range(3)]
    local = om.MVector(*[sum(v[j] * row[j] for j in range(3)) for row in rows])
    aim = om.MVector(*cmds.getAttr(con + ".aimVector")[0])
    return math.degrees(local.angle(aim))


def leftovers(obj):
    return {"knots": knots.knots(), "pivots": knots.pivots(), "aims": knots.aims_waiting(),
            "pairBlends": cmds.ls(type="pairBlend") or [],
            "constraints": cmds.listRelatives(obj, children=True, type="constraint") or []}


def clean(obj):
    left = leftovers(obj)
    return not any(left.values()), str(dict((k, v) for k, v in left.items() if v))


def make_aim(prop, highlight=None, up_z=3.0):
    knots.begin_aim([prop], highlight=highlight)
    target = knots.aims_waiting()[0]
    up = knots._pending_up(target)
    cmds.setAttr(up + ".translateZ", up_z)
    return knots.finish_aim([target])


# -------------------------------------------------------------------- Aim

def case_a():
    case("A aim")
    prop = make_prop()
    before_curves = curves(prop)
    before = track(prop)
    line = knots.begin_aim([prop], highlight=None)
    gate("Finish" in line, line)
    waiting = knots.aims_waiting()
    gate(len(waiting) == 1 and cmds.ls(selection=True, long=True) == waiting,
         "one aim waits, its target selected: %s" % waiting)
    target = waiting[0]
    up = knots._pending_up(target)
    reach = plan.aim_reach(knots._size(prop))
    offs = []
    for f in (12, 30):
        cmds.currentTime(f, update=True)
        rows = plan.axes_of(cmds.getAttr(prop + ".worldMatrix[0]"))
        expect = pivot(prop) + om.MVector(*rows[0]) * reach
        offs.append((where(target) - expect).length())
    cmds.currentTime(12, update=True)
    gate(max(offs) < EPS_CM, "the target rides the prop along its X, %g out: %.6f" % (
        reach, max(offs)))
    gate(knots.pivots() == [], "an aim is no Knot Offset pivot")
    cmds.setAttr(up + ".translateZ", 3.0)
    line = knots.finish_aim(None)
    gate("prop aims at prop_aimTarget" in line, line)
    ok, text = same(before, track(prop))
    gate(ok, "nothing moves at creation: " + text)
    top = aim_of(prop)
    target, up = parts(top)
    cons = knots.constraints_of(prop)
    gate(bool(top) and cmds.getAttr(top + "." + plan.KIND_MARKER) == "aim" and target and up
         and not knots.aims_waiting()
         and len(cons) == 1 and cmds.nodeType(cons[0]) == "aimConstraint",
         "a group holding the target and the up, one aimConstraint: %s %s" % (top, cons))
    gate(all(cmds.getAttr(n + "." + plan.INNER_MARKER) == knots._uuid(top) for n in (target, up)),
         "the target and the up are the knot's inner nodes")
    gate(cmds.getAttr(target + ".rx", lock=True), "the target's rotation locked")
    nudge(target, "tx", 15.0)
    nudge(target, "ty", 8.0)
    errors = []
    for f in (12, 20, 33):
        cmds.currentTime(f, update=True)
        errors.append(aim_error(prop, target, cons[0]))
    moved = diff(before, track(prop))[1]
    gate(max(errors) < 0.01 and moved > 5.0,
         "the target moved: the prop turns onto it (%.5f deg off, turned %.2f deg)" % (
             max(errors), moved))
    edited = track(prop)
    nudge(up, "ty", 25.0)
    cmds.currentTime(20, update=True)
    still = aim_error(prop, target, cons[0])
    rolled = diff(edited, track(prop))[1]
    gate(still < 0.01 and rolled > 1.0,
         "the up moved: the prop rolls %.2f deg and still aims (%.5f deg)" % (rolled, still))
    cmds.setAttr(top + "." + plan.ATTACH, 0.0)
    ok, text = same(before, track(prop))
    gate(ok, "attach 0: the original: " + text)
    line = knots.remove([top])
    gate(curves(prop) == before_curves, "Remove: every curve back exactly")
    ok, text = clean(prop)
    gate(ok, "nothing left: " + text)


def case_b():
    case("B bake")
    prop = make_prop()
    make_aim(prop)
    top = aim_of(prop)
    target, _up = parts(top)
    nudge(target, "ty", 10.0)
    edited = track(prop)
    line = knots.bake([top])
    ok, text = same(edited, track(prop))
    gate(ok and "Baked 1 knot" in line, "Bake keeps the edit: %s - %s" % (text, line))
    ok, text = clean(prop)
    gate(ok and not cmds.ls("*_aimTarget*"), "nothing left: " + text)


def case_c():
    case("C undo")
    prop = make_prop()
    knots.begin_aim([prop], highlight=None)
    knots.finish_aim(None)
    gate(aim_of(prop) and not knots.aims_waiting(), "finished")
    cmds.undo()
    gate(not knots.knots() and len(knots.aims_waiting()) == 1,
         "undo of the finish: the aim waits again")
    cmds.undo()
    gate(not knots.aims_waiting(), "undo of the begin: nothing waits")


def case_d():
    case("D range")
    prop = make_prop()
    before = track(prop)
    make_aim(prop, highlight=(10, 31))
    top = aim_of(prop)
    keys = list(zip(cmds.keyframe(top + "." + plan.ATTACH, query=True, timeChange=True),
                    cmds.keyframe(top + "." + plan.ATTACH, query=True, valueChange=True)))
    gate(keys == [(9.0, 0.0), (10.0, 1.0), (30.0, 1.0), (31.0, 0.0)], "attach keys %s" % keys)
    target, _up = parts(top)
    nudge(target, "tx", 15.0)
    after = track(prop)
    outside = [f for f in FRAMES if f < 9 or f > 31]
    ok, text = same(before, after, outside)
    inside = diff(before, after, [15, 20, 25])[1]
    gate(ok and inside > 5.0, "the edit only inside: outside %s, inside %.2f deg" % (text, inside))


def case_e():
    case("E refusals")
    prop = make_prop()
    gate(knots.begin_aim([], highlight=None) == plan.AIM_NOTHING, "nothing selected")
    knots.begin_aim([prop], highlight=None)
    target = knots.aims_waiting()[0]
    up = knots._pending_up(target)
    line = knots.begin_aim([prop], highlight=None)
    gate("already has an aim waiting" in line, line)
    cmds.setAttr(target + ".translate", 0, 0, 0, type="double3")
    line = knots.finish_aim(None)
    gate("stands on the object" in line and not knots.knots() and knots.aims_waiting(), line)
    cmds.setAttr(target + ".translate", 20, 0, 0, type="double3")
    cmds.setAttr(up + ".translate", 40, 0.1, 0, type="double3")
    line = knots.finish_aim(None)
    gate("line to its target" in line and not knots.knots(), line)
    line = knots.remove([up])
    gate(not knots.aims_waiting() and "1 pivot dropped" in line, "Remove drops it: " + line)
    ok, text = clean(prop)
    gate(ok, "nothing left: " + text)


def case_f():
    case("F rig")
    from maya_scenesetup import catalog, character, deletion
    import maya_rigs
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    character.add_character(catalog.default_rig())
    rig = maya_rigs.rigs()[0]
    control = cmds.ls(maya_rigs.node(rig, "FKHead_M"), long=True)[0]
    bone = [j for j in cmds.ls(type="joint", long=True)
            if j.split("|")[-1].split(":")[-1] == "head" and maya_rigs.under(j, rig.skeleton_root)][0]
    for t, rz in ((0, 0.0), (20, 15.0), (40, -10.0)):
        cmds.setKeyframe(control, attribute="rz", time=t, value=rz)
    cmds.currentTime(12)
    before = track(bone)
    make_aim(control)
    ok, text = same(before, track(bone))
    gate(ok, "the head does not move at creation: " + text)
    target, _up = parts(aim_of(control))
    nudge(target, "tx", 30.0)
    turned = diff(before, track(bone))[1]
    gate(turned > 5.0, "the head turns with the target: %.2f deg" % turned)
    line = deletion.delete_selected([control], confirm=lambda text: True)
    gate(not knots.knots(), "Delete character takes it: " + line)


# ----------------------------------------------------------------- Overlap

SWING = [40.0 * math.sin(2.0 * math.pi * t / 48.0) for t in range(49)]


def make_chain(name="j"):
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=48, animationStartTime=0, animationEndTime=48)
    cmds.select(clear=True)
    joints = []
    for i in range(5):
        joints.append(cmds.joint(name="%s%d" % (name, i), position=(10.0 * i, 0.0, 0.0)))
    joints = cmds.ls(joints, long=True)
    for t, value in enumerate(SWING):
        cmds.setKeyframe(joints[0], attribute="rz", time=t, value=value)
    cmds.currentTime(0)
    cmds.select(clear=True)
    return joints


def heading(node):
    m = cmds.getAttr(node + ".worldMatrix[0]")
    return math.degrees(math.atan2(m[1], m[0]))


def headings(node, frames=range(49)):
    out = []
    now = cmds.currentTime(query=True)
    for f in frames:
        cmds.currentTime(f, update=True)
        out.append(heading(node))
    cmds.currentTime(now, update=True)
    return out


def rotations(nodes, frames=range(49)):
    out = {}
    for node in nodes:
        out[node] = track(node, list(frames))
    return out


def settings(**kwargs):
    return overlapplan.DEFAULTS._replace(**kwargs)


def layer_plugs():
    out = []
    for layer in overlap.overlap_layers():
        out += cmds.animLayer(layer, query=True, attribute=True) or []
    return out


def case_o1():
    case("O1-O3 overlap")
    joints = make_chain()
    base_curve = cmds.listConnections(joints[0] + ".rz", source=True, destination=False)[0]
    base = cmds.keyframe(base_curve, query=True, valueChange=True)
    line = overlap.run(joints[:1], settings(lag=2.0, softness=2.0), highlight=None)
    gate("j0 > j4 (5 links)" in line and "layer Overlap" in line, line)
    layers = overlap.overlap_layers()
    gate(len(layers) == 1 and cmds.getAttr(layers[0] + "." + overlap.LAYER_MARKER) == "j0",
         "one marked layer: %s" % layers)
    gate(cmds.objExists(base_curve)
         and cmds.keyframe(base_curve, query=True, valueChange=True) == base
         and cmds.nodeType(cmds.listConnections(joints[0] + ".rz", source=True,
                                                destination=False)[0]).startswith("animBlend"),
         "the base curve untouched, under the layer's blend: %s" % base_curve)
    plugs = layer_plugs()
    gate(any(p.endswith("j0.rotateZ") for p in plugs)
         and not any(".translate" in p for p in plugs),
         "the layer holds rotations, no translation (a hierarchy): %s" % plugs)
    root = headings(joints[0])
    worst = max(abs(root[t] - SWING[t - 2]) for t in range(2, 49))
    gate(worst < 0.01, "the root delayed by exactly the lag: %.6f deg" % worst)
    tip = headings(joints[4])
    late = lambda series: max(range(len(series)), key=lambda i: series[i])
    gate(late(tip) > late(root) and max(abs(a - b) for a, b in zip(tip, root)) > 1.0,
         "the tip trails: peaks at %d against the root's %d" % (late(tip), late(root)))
    lengths = []
    for f in (0, 17, 33):
        cmds.currentTime(f, update=True)
        lengths.append((pivot(joints[4]) - pivot(joints[3])).length())
    gate(max(abs(v - 10.0) for v in lengths) < 1e-6, "the bones keep their length: %s" % lengths)


def case_o4():
    case("O4 refusals")
    joints = make_chain()
    gate("Lag" in overlap.run(joints[:1], settings(lag=0.0), highlight=None), "lag 0")
    gate("Softness" in overlap.run(joints[:1], settings(softness=0.0), highlight=None),
         "softness 0")
    gate(overlap.run([], settings(), highlight=None) == overlapplan.NOTHING, "nothing selected")
    gate("nothing of its kind below" in overlap.run(joints[4:], settings(), highlight=None),
         "a joint with nothing below")
    gate("alone is no chain" in overlap.run(joints[1:2], settings(hierarchy=False),
                                            highlight=None), "one member, Hierarchy off")
    gate(not overlap.overlap_layers(), "no layer made")


def case_o5():
    case("O5-O7 edges, cycled, replace")
    joints = make_chain()
    original = rotations(joints, [0, 24, 48])
    line = overlap.run(joints[:1], settings(lag=2.0, edges=True), highlight=None)
    now = rotations(joints, [0, 24, 48])
    ends = max(diff(original[j], now[j], [0, 48])[1] for j in joints)
    middle = max(diff(original[j], now[j], [24])[1] for j in joints)
    gate(ends < 1e-4 and middle > 1.0, "keep edges: the ends %.6f deg, the middle %.2f deg" % (
        ends, middle))
    line = overlap.run(joints[:1], settings(lag=2.0, cycled=True), highlight=None)
    gate("replaced" in line and len(overlap.overlap_layers()) == 1,
         "a second press replaces the first: %s" % line)
    layer = overlap.overlap_layers()[0]
    curve = cmds.animLayer(layer, query=True, findCurveForPlug=joints[0] + ".rotateZ")[0]
    gate(cmds.getAttr(curve + ".preInfinity") == 3 and cmds.getAttr(curve + ".postInfinity") == 3,
         "cycled: the layer curves cycle")
    root = headings(joints[0], [0, 1])
    gate(abs(root[0] - SWING[46]) < 0.01 and abs(root[1] - SWING[47]) < 0.01,
         "cycled: frame 0 looks back round the end (%.4f / %.4f)" % (root[0], SWING[46]))


def case_o8():
    case("O8 undo")
    joints = make_chain()
    overlap.run(joints[:1], settings(lag=1.0), highlight=None)
    gate(len(overlap.overlap_layers()) == 1, "a layer")
    cmds.undo()
    gate(not overlap.overlap_layers() and not cmds.ls(type="animLayer")[1:],
         "one undo takes it all: %s" % cmds.ls(type="animLayer"))


def case_o9():
    case("O9 highlight")
    joints = make_chain()
    original = rotations(joints[3:4], range(49))[joints[3]]
    line = overlap.run(joints[:1], settings(lag=2.0), highlight=(10, 31))
    gate("over 10-30 (the highlight)" in line, line)
    layer = overlap.overlap_layers()[0]
    curve = cmds.animLayer(layer, query=True, findCurveForPlug=joints[3] + ".rotateZ")[0]
    keys = dict(zip(cmds.keyframe(curve, query=True, timeChange=True),
                    cmds.keyframe(curve, query=True, valueChange=True)))
    gate(keys.get(9.0) == 0.0 and keys.get(31.0) == 0.0 and min(keys) == 9.0
         and max(keys) == 31.0, "zero one frame outside: %s..%s" % (min(keys), max(keys)))
    now = track(joints[3], list(range(49)))
    outside = [f for f in range(49) if f < 9 or f > 31]
    ok, text = same(original, now, outside)
    gate(ok and diff(original, now, [20])[1] > 0.5, "only inside: outside " + text)


def case_o10():
    case("O10-O12 selection mode, loose chain, knotted")
    joints = make_chain()
    line = overlap.run(joints[1:4], settings(hierarchy=False, lag=1.0), highlight=None)
    plugs = layer_plugs()
    names = sorted(set(p.split(".")[0].split("|")[-1] for p in plugs))
    gate(set(names) <= {"j1", "j2", "j3"} and "j1 > j3 (3 links)" in line,
         "the selection is the chain: %s - %s" % (names, line))
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=48, animationStartTime=0, animationEndTime=48)
    loose = []
    for i in range(3):
        node = cmds.spaceLocator(name="l%d" % i)[0]
        cmds.setAttr(node + ".tx", 10.0 * i)
        loose.append(cmds.ls(node, long=True)[0])
    for t, value in enumerate(SWING):
        cmds.setKeyframe(loose[0], attribute="ry", time=t, value=value)
    overlap.run(loose, settings(hierarchy=False, lag=1.0), highlight=None)
    plugs = layer_plugs()
    gate(any(p.endswith("l1.translateX") or p.endswith("l1.translateZ") for p in plugs),
         "a loose chain's members follow in position too: %s" % [p for p in plugs
                                                                   if "translate" in p])
    joints = make_chain()
    knots.create("knot", [joints[2]], highlight=None)
    line = overlap.run(joints[:1], settings(), highlight=None)
    gate("already rides a knot" in line and not overlap.overlap_layers(), line)


def case_o13():
    case("O13 AdvancedSkeleton fingers")
    from maya_scenesetup import catalog, character
    import maya_rigs
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=48, animationStartTime=0, animationEndTime=48)
    character.add_character(catalog.default_rig())
    rig = maya_rigs.rigs()[0]
    root = maya_rigs.node(rig, "FKIndexFinger1_R")
    if not cmds.objExists(root):
        gate(False, "no FKIndexFinger1_R: %s" % cmds.ls("*Finger1_R", recursive=True))
        return
    root = cmds.ls(root, long=True)[0]
    chain, _note = overlap.chain_from(root)
    gate([c.split(":")[-1] for c in chain] == ["FKIndexFinger1_R", "FKIndexFinger2_R",
                                                "FKIndexFinger3_R"],
         "the chain through the FKX joints and offsets: %s" % [c.split("|")[-1] for c in chain])
    for t, value in enumerate(SWING):
        cmds.setKeyframe(root, attribute="rz", time=t, value=value)
    bone = [j for j in cmds.ls(type="joint", long=True)
            if j.split("|")[-1].split(":")[-1] == "index_03_r"
            and maya_rigs.under(j, rig.skeleton_root)][0]
    before = track(bone, list(range(0, 49, 4)))
    line = overlap.run([root], settings(lag=2.0), highlight=None)
    after = track(bone, list(range(0, 49, 4)))
    gate("3 links" in line and diff(before, after)[1] > 1.0,
         "the game finger trails: %.2f deg - %s" % (diff(before, after)[1], line))


def main():
    for run in (case_a, case_b, case_c, case_d, case_e, case_f, case_o1, case_o4, case_o5,
                case_o8, case_o9, case_o10, case_o13):
        try:
            run()
        except Exception:
            import traceback
            traceback.print_exc()
            gate(False, "%s raised" % run.__name__)
    print("verify_aim_overlap: %d gates, %d failed%s" % (
        COUNT[0], len(FAILS), (" - " + ", ".join("%s#%d" % (c, n) for c, n, _ in FAILS))
        if FAILS else ""))


main()
