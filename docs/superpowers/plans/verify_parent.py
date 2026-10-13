"""Standalone gates for the Tools card's parent tab (2026-10-12).

    mayapy verify_parent.py

mayapy STANDALONE, a fresh scene per case (spec
docs/superpowers/specs/2026-10-12-tools-parent-design.md). The fixture: carrier A (ty, ry keyed)
holding a prop (tx / ry / rx keyed, its rotate pivot 2 cm up, zxy); carrier B at world level
(tx, rz keyed). Frames 0..40, the current frame 12. World tracks are compared on every integer
frame (a re-parent bakes every frame - between frames the dense keys interpolate their own way,
as OverRig's).

P  Inside / World / Swap keep the world tracks, the hierarchy as asked, one undo.
R  Refusals change nothing: a Manny control, a bone, a locked channel, a knot rider, a cycle,
   already inside / at world, an uneven parent, the plugin's own node.
A  Across: nothing moves, the knot inside the target and in the registry, the prop follows the
   target, Bake keeps it, Remove restores, a range.
M  Multiple across with Rotate off: translation follows the target, the rotation stays the prop's.
T  Attach 0 / 1 at a frame, a highlight, selected keys.
K  An across knot under a Manny control: nothing moves, Delete character takes it.
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

from maya_tools import knotplan as plan, knots, reparent  # noqa: E402

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


def wm(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def rot(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def ang(qa, qb):
    q = qa.inverse() * qb
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def pivot(node):
    return om.MVector(*cmds.xform(node, query=True, worldSpace=True, rotatePivot=True))


def origin(node):
    m = wm(node)
    return om.MVector(m[12], m[13], m[14])


def track(node, frames=FRAMES):
    out = {}
    now = cmds.currentTime(query=True)
    for f in frames:
        cmds.currentTime(f, update=True)
        out[f] = (pivot(node), rot(wm(node)))
    cmds.currentTime(now, update=True)
    return out


def same(a, b, frames=None):
    cm = deg = 0.0
    for f in (frames if frames is not None else a):
        cm = max(cm, (a[f][0] - b[f][0]).length())
        deg = max(deg, ang(a[f][1], b[f][1]))
    return cm < EPS_CM and deg < EPS_DEG, "%.6f cm, %.6f deg" % (cm, deg)


def curves(node):
    out = {}
    for ch in plan.CHANNELS:
        found = cmds.listConnections(node + "." + ch, source=True, destination=False) or []
        if found and cmds.nodeType(found[0]).startswith("animCurve"):
            out[ch] = (tuple(cmds.keyframe(found[0], query=True, timeChange=True)),
                       tuple(round(v, 9) for v in cmds.keyframe(found[0], query=True,
                                                                 valueChange=True)))
        elif found:
            out[ch] = ("driven by", cmds.nodeType(found[0]))
        else:
            out[ch] = round(cmds.getAttr(node + "." + ch), 9)
    return out


def parent_of(node):
    found = cmds.listRelatives(node, parent=True, fullPath=True)
    return found[0] if found else None


def by_uuid(uuid):
    return cmds.ls(uuid, long=True)[0]


def transforms_count():
    return len(cmds.ls(type="transform") or [])


def scene():
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    cmds.currentTime(0)
    a = cmds.createNode("transform", name="carrierA")
    for t, ty, ry in ((0, 0.0, 0.0), (40, 20.0, 45.0)):
        cmds.setKeyframe(a, attribute="ty", time=t, value=ty)
        cmds.setKeyframe(a, attribute="ry", time=t, value=ry)
    prop = cmds.polyCube(name="prop", width=2, height=6, depth=1)[0]
    prop = cmds.ls(cmds.parent(prop, a)[0], long=True)[0]
    cmds.setAttr(prop + ".rotateOrder", 2)
    cmds.setAttr(prop + ".rotatePivot", 0, 2, 0, type="double3")
    cmds.setAttr(prop + ".scalePivot", 0, 2, 0, type="double3")
    for t, tx in ((0, 0.0), (20, 10.0), (40, 0.0)):
        cmds.setKeyframe(prop, attribute="tx", time=t, value=tx)
    for t, ry in ((0, 0.0), (40, 90.0)):
        cmds.setKeyframe(prop, attribute="ry", time=t, value=ry)
    for t, rx in ((0, 0.0), (30, 40.0)):
        cmds.setKeyframe(prop, attribute="rx", time=t, value=rx)
    b = cmds.createNode("transform", name="carrierB")
    for t, tx, rz in ((0, 30.0, 0.0), (40, -10.0, 60.0)):
        cmds.setKeyframe(b, attribute="tx", time=t, value=tx)
        cmds.setKeyframe(b, attribute="rz", time=t, value=rz)
    cmds.currentTime(12)
    cmds.select(clear=True)
    return prop, cmds.ls(a, long=True)[0], cmds.ls(b, long=True)[0]


def case_p():
    case("P inside / world / swap")
    prop, a, b = scene()
    before = track(prop)
    uuid = cmds.ls(prop, uuid=True)[0]
    line = reparent.inside([prop, b])
    cmds.undo()                     # straight away: a time walk is an undo step (trap 222)
    gate(parent_of(by_uuid(uuid)) == a, "one undo puts it back under carrierA")
    cmds.redo()
    prop = by_uuid(uuid)
    gate("Inside: prop moved under carrierB" in line, line)
    gate(parent_of(prop) == b, "the prop is under carrierB: %s" % parent_of(prop))
    ok, text = same(before, track(prop))
    gate(ok, "its world track on every frame: " + text)
    gate(not cmds.listRelatives(prop, children=True, type="constraint")
         and not cmds.ls(type="pairBlend") and not cmds.ls("skeldarReparent_*"),
         "no constraint, pairBlend or locator left")
    gate(cmds.currentTime(query=True) == 12, "the frame is still 12")

    prop, a, b = scene()
    before = track(prop)
    uuid = cmds.ls(prop, uuid=True)[0]
    line = reparent.to_world([prop])
    prop = by_uuid(uuid)
    gate(parent_of(prop) is None and "world level" in line, line)
    ok, text = same(before, track(prop))
    gate(ok, "World keeps the world track: " + text)

    prop, a, b = scene()
    y = cmds.ls(cmds.parent(cmds.createNode("transform", name="Y"), prop)[0], long=True)[0]
    for t, tz, rx in ((0, 0.0, 0.0), (40, 8.0, 30.0)):
        cmds.setKeyframe(y, attribute="tz", time=t, value=tz)
        cmds.setKeyframe(y, attribute="rx", time=t, value=rx)
    before_x, before_y = track(prop), track(y)
    ux, uy = cmds.ls(prop, uuid=True)[0], cmds.ls(y, uuid=True)[0]
    line = reparent.swap([prop, y])
    x, y = by_uuid(ux), by_uuid(uy)
    gate(parent_of(y) == a and parent_of(x) == y, "Swap: carrierA > Y > prop (%s)" % line)
    ok_x, text_x = same(before_x, track(x))
    ok_y, text_y = same(before_y, track(y))
    gate(ok_x and ok_y, "both keep their world tracks: %s / %s" % (text_x, text_y))


def case_r():
    case("R refusals")
    prop, a, b = scene()
    count = transforms_count()
    checks = []
    checks.append(("parent inside the child", reparent.inside([a, prop]), "lies inside"))
    checks.append(("already inside", reparent.inside([prop, a]), "already inside"))
    checks.append(("already at world", reparent.to_world([b]), "already at world level"))
    squashed = cmds.createNode("transform", name="squashed")
    cmds.setAttr(squashed + ".scale", 1.0, 2.5, 0.7, type="double3")
    checks.append(("an uneven parent", reparent.inside([prop, squashed]), "scaled unevenly"))
    joint = cmds.createNode("joint", name="aBone")
    checks.append(("a bone", reparent.inside([joint, b]), "a skeleton bone"))
    count = transforms_count()
    stuck = cmds.polyCube(name="stuck")[0]
    cmds.setAttr(stuck + ".tx", lock=True)
    count = transforms_count()
    checks.append(("a locked channel", reparent.to_world([stuck]) if parent_of(stuck)
                   else reparent.inside([stuck, b]), "locked"))
    knots.create("knot", [prop], highlight=None)
    count = transforms_count()
    checks.append(("a knot rider", reparent.inside([prop, b]), "already rides a knot"))
    knot = [k for k in knots.knots() if knots.source_of(k) == prop][0]
    checks.append(("the plugin's own node", reparent.inside([knot, b]), "the plugin's own node"))
    checks.append(("Swap of one", reparent.swap([b]), "two or more"))
    for what, line, want in checks:
        gate(want in line and transforms_count() == count, "%s: %s" % (what, line))
    gate(len(cmds.ls("skeldarReparent_*") or []) == 0, "no locator left behind")


def case_a():
    case("A across")
    prop, a, b = scene()
    before = track(prop)
    curves_before = curves(prop)
    line = knots.across([prop, b], highlight=None)
    gate("Across: prop rides prop_across" in line, line)
    knot = [k for k in knots.knots() if knots.source_of(k) == prop]
    gate(len(knot) == 1 and parent_of(knot[0]) == b, "the knot inside carrierB: %s" % knot)
    knot = knot[0]
    registry = [s for s in cmds.ls(exactType="objectSet")
                if cmds.attributeQuery(plan.REGISTRY_MARKER, node=s, exists=True)]
    gate(len(registry) == 1 and knot in cmds.ls(cmds.sets(registry[0], query=True), long=True),
         "the knot is in the registry set")
    ok, text = same(before, track(prop))
    gate(ok, "nothing moves: " + text)
    cmds.keyframe(b + ".tx", edit=True, relative=True, valueChange=10.0)
    shifted = dict((f, (before[f][0] + om.MVector(10, 0, 0), before[f][1])) for f in FRAMES)
    ok, text = same(shifted, track(prop))
    gate(ok, "carrierB +10 on X takes the prop along: " + text)
    edited = track(prop)
    knots.bake([knot])
    ok, text = same(edited, track(prop))
    gate(ok and not knots.knots() and not [s for s in cmds.ls(exactType="objectSet")
                                           if cmds.attributeQuery(plan.REGISTRY_MARKER,
                                                                  node=s, exists=True)],
         "Bake keeps the ride, the knot and the registry gone: " + text)
    cmds.keyframe(b + ".tx", edit=True, relative=True, valueChange=-10.0)

    prop, a, b = scene()
    curves_before = curves(prop)
    knots.across([prop, b], highlight=None)
    knots.remove([prop])
    gate(curves(prop) == curves_before and not knots.knots(), "Remove restores every curve")

    prop, a, b = scene()
    before = track(prop)
    knots.across([prop, b], highlight=(10.0, 30.0))
    cmds.keyframe(b + ".tx", edit=True, relative=True, valueChange=10.0)
    after = track(prop)
    inside = [f for f in FRAMES if 10 <= f <= 29]
    outside = [f for f in FRAMES if f <= 8 or f >= 31]
    shifted = dict((f, (before[f][0] + om.MVector(10, 0, 0), before[f][1])) for f in inside)
    ok_in, text_in = same(shifted, after, inside)
    ok_out, text_out = same(before, after, outside)
    gate(ok_in and ok_out, "a ranged across rides only inside: %s / %s" % (text_in, text_out))
    line = knots.across([prop], highlight=None)
    gate(line == plan.ACROSS_TWO, line)
    gate("cycle" in knots.across([a, prop], highlight=None), "a target inside the object refuses")


def case_m():
    case("M multiple across")
    prop, a, b = scene()
    other = cmds.polyCube(name="other")[0]
    other = cmds.ls(other, long=True)[0]
    for t, tz, ry in ((0, 0.0, 0.0), (40, 5.0, 120.0)):
        cmds.setKeyframe(other, attribute="tz", time=t, value=tz)
        cmds.setKeyframe(other, attribute="ry", time=t, value=ry)
    c = cmds.createNode("transform", name="carrierC")
    c = cmds.ls(c, long=True)[0]
    before_p, before_o = track(prop), track(other)
    line = knots.create_across([(prop, b), (other, c)], highlight=None, rotate=False)
    gate("2 objects ride knots" in line, line)
    gate(not any(cmds.listConnections(prop + "." + ch, source=True, destination=False,
                                      type="pairBlend") for ch in plan.ROTATE),
         "Rotate off: the prop's rotation is its own")
    cmds.setAttr(b + ".tx", lock=False)
    cmds.keyframe(b + ".tx", edit=True, relative=True, valueChange=10.0)
    after_p, after_o = track(prop), track(other)
    shifted = dict((f, (before_p[f][0] + om.MVector(10, 0, 0), before_p[f][1])) for f in FRAMES)
    ok_p, text_p = same(shifted, after_p)
    ok_o, text_o = same(before_o, after_o)
    gate(ok_p and ok_o, "the prop follows carrierB's move, its rotation unchanged (%s); the other "
         "pair untouched (%s)" % (text_p, text_o))
    gate("must match" in plan.multiple_refusal(1, 2, True, True), "different lengths refuse")
    gate("Rotate or Translate" in knots.create_across([(prop, b)], highlight=None, rotate=False,
                                                      translate=False),
         "both off refuses")


def case_t():
    case("T attach")
    prop, a, b = scene()
    knots.create("knot", [prop], highlight=None)
    knot = [k for k in knots.knots() if knots.source_of(k) == prop][0]
    line = knots.set_attach(0.0, [knot], highlight=None)
    keys = list(zip(cmds.keyframe(knot + ".attach", query=True, timeChange=True),
                    cmds.keyframe(knot + ".attach", query=True, valueChange=True)))
    gate(keys == [(12.0, 0.0)] and "at 12" in line, "at the current frame: %s (%s)" % (keys, line))
    cmds.cutKey(knot + ".attach", clear=True)
    line = knots.set_attach(1.0, [prop], highlight=(10.0, 30.0))
    keys = list(zip(cmds.keyframe(knot + ".attach", query=True, timeChange=True),
                    cmds.keyframe(knot + ".attach", query=True, valueChange=True)))
    gate(keys == [(10.0, 1.0), (29.0, 1.0)], "at the highlight's ends, through the object: %s"
         % keys)
    cmds.cutKey(knot + ".attach", clear=True)
    cmds.selectKey(prop + ".tx", time=(20, 20))
    cmds.selectKey(prop + ".rx", time=(30, 30), add=True)
    knots.set_attach(0.0, [knot], highlight=None)
    times = cmds.keyframe(knot + ".attach", query=True, timeChange=True)
    gate(times == [20.0, 30.0], "at the selected keys' range: %s" % times)
    cmds.selectKey(clear=True)
    gate(knots.set_attach(1.0, [b], highlight=None) == plan.ATTACH_NOTHING,
         "nothing of ours selected refuses")


def case_k():
    case("K rig")
    from maya_scenesetup import catalog, character, deletion
    import maya_rigs
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    character.add_character(catalog.default_rig())
    rig = maya_rigs.rigs()[0]
    control = cmds.ls(maya_rigs.node(rig, "FKWrist_R"), long=True)[0]
    for t, rx in ((0, 0.0), (20, 40.0), (40, 0.0)):
        cmds.setKeyframe(control, attribute="rx", time=t, value=rx)
    prop = cmds.ls(cmds.polyCube(name="cup")[0], long=True)[0]
    for t, ty in ((0, 100.0), (40, 120.0)):
        cmds.setKeyframe(prop, attribute="ty", time=t, value=ty)
    cmds.currentTime(12)
    line = reparent.inside([control, prop])
    gate("a control of" in line and "Across" in line, "a rig control refuses: " + line)
    before = track(prop)
    knots.across([prop, control], highlight=None)
    ok, text = same(before, track(prop))
    knot = [k for k in knots.knots() if knots.source_of(k) == prop]
    gate(ok and knot and parent_of(knot[0]) == control,
         "the cup rides a knot inside FKWrist_R, nothing moved: " + text)
    line = deletion.delete_selected([control], confirm=lambda text: True)
    gate(not knots.knots() and cmds.objExists(prop),
         "Delete character takes the knot, the cup stays: " + line)


def matrices(node, frames):
    out = {}
    now = cmds.currentTime(query=True)
    for f in frames:
        cmds.currentTime(f, update=True)
        out[f] = cmds.getAttr(node + ".worldMatrix[0]")
    cmds.currentTime(now, update=True)
    return out


def axis_lengths(m):
    return [math.sqrt(sum(v * v for v in m[i * 4:i * 4 + 3])) for i in range(3)]


def matrix_off(a, b, frames):
    return max(max(abs(x - y) for x, y in zip(a[f], b[f])) for f in frames)


def scale_off(a, b, frames):
    return max(max(abs(x - y) for x, y in zip(axis_lengths(a[f]), axis_lengths(b[f])))
               for f in frames)


def scaled_scene():
    """The report (2026-10-13): the prop and carrierB keyed with S - every channel, scale too -
    carrierB at scale 2; before the fix Inside refused («has scale keys and its new parent is
    scaled differently»)."""
    prop, a, b = scene()
    cmds.parent(prop, world=True)
    prop = cmds.ls("|prop", long=True)[0]
    for t in (0, 20, 40):
        cmds.currentTime(t)
        for node in (prop, b):
            cmds.setKeyframe(node)
    for t in (0, 20, 40):
        cmds.setKeyframe(b, attribute="scale", time=t, value=2.0)
    cmds.currentTime(12)
    return prop, b


def case_s():
    case("S scale keys under a scaled parent")
    halves = [f * 0.5 for f in range(0, 81)]
    prop, b = scaled_scene()
    before = matrices(prop, halves)
    uuid = cmds.ls(prop, uuid=True)[0]
    keys_before = cmds.keyframe(prop + ".sx", query=True, timeChange=True)
    line = reparent.inside([prop, b])
    prop = by_uuid(uuid)
    after = matrices(prop, halves)
    gate("Inside: prop moved under carrierB" in line and parent_of(prop) == b, line)
    gate(matrix_off(before, after, FRAMES) < 1e-9,
         "the whole world matrix, scale included, on every frame: %.2e"
         % matrix_off(before, after, FRAMES))
    gate(scale_off(before, after, halves) < 1e-9
         and cmds.keyframe(prop + ".sx", query=True, timeChange=True) == keys_before
         and abs(cmds.getAttr(prop + ".sx") - 0.5) < 1e-9,
         "the scale keys stay keys (%s), scaled by 1/2, exact between frames too: %.2e"
         % (keys_before, scale_off(before, after, halves)))

    prop, b = scaled_scene()
    uuid = cmds.ls(prop, uuid=True)[0]
    reparent.inside([prop, b])
    cmds.undo()                     # straight away: a time walk is an undo step (trap 222)
    prop = by_uuid(uuid)
    gate(parent_of(prop) is None
         and cmds.keyframe(prop + ".sx", query=True, valueChange=True) == [1.0, 1.0, 1.0],
         "one undo: at world level again, its scale keys 1")

    prop, b = scaled_scene()
    reparent.inside([prop, b])
    prop = cmds.ls("|carrierB|prop", long=True)[0]
    before = matrices(prop, FRAMES)
    line = reparent.to_world([prop])
    prop = cmds.ls("|prop", long=True)[0]
    gate("World" in line and matrix_off(before, matrices(prop, FRAMES), FRAMES) < 1e-9
         and abs(cmds.getAttr(prop + ".sx") - 1.0) < 1e-9,
         "World out of the scale-2 parent: the matrix kept, the scale back to 1: %s" % line)

    prop, b = scaled_scene()
    cmds.setKeyframe(b, attribute="scale", time=40, value=3.0)       # the parent's scale moves
    before = matrices(prop, FRAMES)
    line = reparent.inside([prop, b])
    prop = cmds.ls("|carrierB|prop", long=True)[0]
    off = matrix_off(before, matrices(prop, FRAMES), FRAMES)
    gate("Inside" in line and off < 1e-9
         and cmds.keyframe(prop + ".sx", query=True, keyframeCount=True) == len(FRAMES),
         "an animated parent scale: the scale keyed on every frame, the matrix kept: %.2e" % off)

    prop, b = scaled_scene()
    cmds.setAttr(prop + ".sy", lock=True)
    count = transforms_count()
    line = reparent.inside([prop, b])
    gate("scaleY is locked" in line and transforms_count() == count
         and parent_of(prop) is None, "a locked scale refuses by name: " + line)


def main():
    for run in (case_p, case_r, case_a, case_m, case_t, case_k, case_s):
        try:
            run()
        except Exception:
            import traceback
            traceback.print_exc()
            gate(False, "%s raised" % run.__name__)
    print("verify_parent: %d gates, %d failed%s" % (
        COUNT[0], len(FAILS), (" - " + ", ".join("%s#%d" % (c, n) for c, n, _ in FAILS))
        if FAILS else ""))


main()
