"""Standalone gates for the Tools card's Snapshot (2026-10-13).

    mayapy verify_snapshot.py

mayapy STANDALONE, a fresh scene per case (spec
docs/superpowers/specs/2026-10-13-tools-snapshot-design.md). The prop is verify_knots.py's: a
cube under an animated carrier (ty, ry keyed), its rotate pivot 2 cm up its own Y, rotate order
zxy, tx / ry / rx keyed, ty and tz free and unkeyed, rz locked at 5. Frames 0..40, the current
frame 12.

A  The whole take:
   - the snapshot on the prop's world pivot and orientation on every frame;
   - keyed on every frame;
   - the prop untouched;
   - at world level in SkeldarKnots;
   - marked (a snapshot, of the prop, riding nothing, no attach);
   - selected, the frame kept, the prop's rotate order;
   - one undo.
B  A highlight 10..20: keys exactly on its frames, exact inside, holding its ends outside.
C  The rotate order choice.
D  On an object riding a knot:
   - the snapshot follows it;
   - Remove of the object's knot leaves the snapshot;
   - Remove of the snapshot deletes it.
E  Remove of a snapshot takes a knot riding it along.
F  Bake deletes a snapshot (2026-10-15: nothing to bake, it just goes); beside a knot it bakes
   the knot and deletes the snapshot.
G  Attach finds nothing on it. Layer treats it as itself.
H  Refusals change nothing.
I  On Manny's rig, a bone and a control:
   - each snapshot on its node;
   - the rig untouched;
   - in the character's Knots group;
   - the subtitle's count;
   - Delete character takes them.
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

from maya_tools import knotplan as plan, knots, layerbake  # noqa: E402

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


def same(a, b, frames=None):
    cm, deg = diff(a, b, frames)
    return cm < EPS_CM and deg < EPS_DEG, "%.6f cm, %.6f deg" % (cm, deg)


def curves(node):
    """{channel: (times, values, in, out)}, what drives it, or the plain value."""
    out = {}
    for ch in plan.CHANNELS:
        plug = node + "." + ch
        found = cmds.listConnections(plug, source=True, destination=False) or []
        if found and cmds.nodeType(found[0]).startswith("animCurve"):
            out[ch] = (tuple(cmds.keyframe(found[0], query=True, timeChange=True)),
                       tuple(round(v, 9) for v in cmds.keyframe(found[0], query=True,
                                                                 valueChange=True)),
                       tuple(cmds.keyTangent(found[0], query=True, inTangentType=True)),
                       tuple(cmds.keyTangent(found[0], query=True, outTangentType=True)))
        elif found:
            out[ch] = ("driven by", cmds.nodeType(found[0]))
        else:
            out[ch] = round(cmds.getAttr(plug), 9)
    return out


def key_times(node):
    """{channel: key times} of the channels keyed."""
    out = {}
    for ch in plan.CHANNELS:
        times = cmds.keyframe(node + "." + ch, query=True, timeChange=True)
        if times:
            out[ch] = times
    return out


def groups():
    return [n for n in cmds.ls(type="transform", long=True) or []
            if cmds.attributeQuery(plan.GROUP_MARKER, node=n, exists=True)]


def snapshots_of(node):
    uuid = cmds.ls(node, uuid=True)[0]
    return [s for s in knots.snapshots()
            if cmds.getAttr(s + "." + plan.SNAPSHOT_OF_MARKER) == uuid]


# ------------------------------------------------------------------ fixture

def make_prop(lock_rz=True):
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
    cmds.setAttr(prop + ".tz", 3.0)
    cmds.setAttr(prop + ".rz", 5.0)
    if lock_rz:
        cmds.setAttr(prop + ".rz", lock=True)
    cmds.currentTime(12)
    cmds.select(clear=True)
    return prop


def knot_of(prop):
    found = [k for k in knots.knots() if knots.source_of(k) == prop]
    return found[0] if found else None


# ------------------------------------------------------------------- cases

def case_a():
    case("A whole take")
    prop = make_prop()
    before_curves = curves(prop)
    before = track(prop)
    count = len(cmds.ls(type="transform") or [])
    line = knots.snapshot([prop], highlight=None)
    gate(line == "Snapshot: prop -> prop_snapshot over 0-40", line)
    found = snapshots_of(prop)
    gate(len(found) == 1, "one snapshot: %s" % found)
    snap = found[0]
    ok, text = same(before, track(snap))
    gate(ok, "on the prop's world pivot and orientation on every frame 0..40: " + text)
    times = key_times(snap)
    gate(times.get("tx") == [float(f) for f in FRAMES]
         and times.get("ry") == [float(f) for f in FRAMES],
         "keyed on every frame (tx %d keys, ry %d keys)" % (len(times.get("tx", [])),
                                                          len(times.get("ry", []))))
    gate(curves(prop) == before_curves and not knots.constraints_of(prop)
         and not cmds.ls(type="pairBlend"), "the prop untouched: curves, no constraint, no pairBlend")
    ok, text = same(before, track(prop))
    gate(ok, "the prop does not move: " + text)
    parent = cmds.listRelatives(snap, parent=True, fullPath=True)[0]
    gate(parent == "|" + plan.GROUP_AT_WORLD, "at world level in %s" % parent)
    gate(cmds.getAttr(snap + "." + plan.KIND_MARKER) == "snapshot"
         and knots.is_snapshot(snap) and knots.snapshot_of(snap) == prop
         and not cmds.attributeQuery(plan.SOURCE_MARKER, node=snap, exists=True)
         and not cmds.attributeQuery(plan.ATTACH, node=snap, exists=True)
         and knots.source_of(snap) is None,
         "marked a snapshot of the prop, riding nothing, no attach")
    gate(plan.decode_span(cmds.getAttr(snap + "." + plan.SPAN_MARKER)) == (0.0, 40.0, False),
         "its span recorded")
    gate(cmds.getAttr(snap + ".rotateOrder") == 2, "the prop's rotate order (zxy)")
    gate(cmds.ls(selection=True, long=True) == [snap] and cmds.currentTime(query=True) == 12,
         "the snapshot selected, the frame still 12")
    shape = cmds.listRelatives(snap, shapes=True, fullPath=True)[0]
    gate(tuple(round(c, 6) for c in cmds.getAttr(shape + ".overrideColorRGB")[0])
         == (0.8, 0.5, 0.5), "OverRig's colour")
    gate(knots.knots() == [snap] and knots.snapshots() == [snap], "listed as a knot and a snapshot")
    knots.remove([snap])
    #  Undo straight after the press: in standalone a currentTime is an undo step (trap 222).
    knots.snapshot([prop], highlight=None)
    cmds.undo()
    gate(not knots.knots() and not groups()
         and len(cmds.ls(type="transform") or []) == count, "one undo takes it back")
    cmds.redo()
    gate(len(snapshots_of(prop)) == 1, "redo makes it again")


def case_b():
    case("B highlight")
    prop = make_prop()
    before = track(prop)
    line = knots.snapshot([prop], highlight=(10.0, 21.0))
    gate(line == "Snapshot: prop -> prop_snapshot over 10-20 (the highlight)", line)
    snap = snapshots_of(prop)[0]
    times = key_times(snap)
    gate(all(t == [float(f) for f in range(10, 21)] for t in times.values()) and "tx" in times,
         "keys exactly on 10..20: %s" % sorted(set(len(t) for t in times.values())))
    inside = list(range(10, 21))
    ok, text = same(before, track(snap), inside)
    gate(ok, "exact inside: " + text)
    after = track(snap)
    held = dict((f, before[10] if f < 10 else before[20]) for f in FRAMES if f < 10 or f > 20)
    ok, text = same(held, after, sorted(held))
    gate(ok, "outside it holds its first and last frames: " + text)


def case_c():
    case("C rotate order")
    prop = make_prop()
    before = track(prop)
    knots.snapshot([prop], order="xyz", highlight=None)
    snap = snapshots_of(prop)[0]
    ok, text = same(before, track(snap))
    gate(cmds.getAttr(snap + ".rotateOrder") == 0 and ok, "xyz, still on the prop: " + text)


def case_d():
    case("D riding a knot")
    prop = make_prop()
    knots.create("knot", [prop], highlight=None)
    knot = knot_of(prop)
    cmds.keyframe(knot + ".tx", edit=True, relative=True, valueChange=5.0)
    shown = track(prop)
    knots.snapshot([prop], highlight=None)
    snap = snapshots_of(prop)[0]
    ok, text = same(shown, track(snap))
    gate(ok and len(knots.constraints_of(prop)) == 1,
         "follows the knotted prop, its constraint kept: " + text)
    line = knots.remove([prop])
    gate(knot_of(prop) is None and cmds.objExists(snap) and "Removed 1 knot" in line,
         "Remove of the prop's knot leaves the snapshot: " + line)
    ok, text = same(shown, track(snap))
    gate(ok, "it still shows what the prop showed: " + text)
    line = knots.remove([snap])
    gate(line == "1 snapshot deleted" and not knots.knots() and not groups(),
         "Remove deletes it: " + line)


def case_e():
    case("E a knot riding a snapshot")
    prop = make_prop()
    knots.snapshot([prop], highlight=None)
    snap = snapshots_of(prop)[0]
    knots.create("knot", [snap], highlight=None)
    rider = knot_of(snap)
    gate(rider is not None and knots.knots().count(rider) == 1, "a knot on the snapshot")
    line = knots.remove([snap])
    gate(not cmds.objExists(snap) and not knots.knots() and not groups(),
         "Remove of the snapshot takes its rider along: " + line)
    gate("1 snapshot deleted" in line, line)


def case_f():
    case("F bake")
    prop = make_prop()
    knots.snapshot([prop], highlight=None)
    snap = snapshots_of(prop)[0]
    line = knots.bake([snap])
    gate(line == "1 snapshot deleted" and not cmds.objExists(snap) and not groups(),
         "Bake deletes it (2026-10-15): " + line)
    knots.snapshot([prop], highlight=None)
    snap = snapshots_of(prop)[0]
    other = cmds.polyCube(name="other")[0]
    other = cmds.ls(other, long=True)[0]
    cmds.setKeyframe(other, attribute="tx", time=0, value=0.0)
    cmds.setKeyframe(other, attribute="tx", time=40, value=10.0)
    knots.create("knot", [other], highlight=None)
    knot = knot_of(other)
    line = knots.bake([snap, knot])
    gate(not cmds.objExists(snap) and knot_of(other) is None
         and "Baked 1 knot onto other; 1 snapshot deleted" in line,
         "beside a knot: the knot baked, the snapshot deleted: " + line)


def case_g():
    case("G attach and layer")
    prop = make_prop()
    before_curves = curves(prop)
    knots.snapshot([prop], highlight=None)
    snap = snapshots_of(prop)[0]
    knots.set_attach(0.0, [snap], highlight=None)
    gate(not cmds.attributeQuery(plan.ATTACH, node=snap, exists=True),
         "Attach finds nothing on it")
    shown = track(snap)
    line = layerbake.bake([snap], highlight=None)
    layer = [n for n in cmds.ls(type="animLayer") or []
             if cmds.attributeQuery(plan.LAYER_MARKER, node=n, exists=True)]
    plugs = cmds.animLayer(layer[0], query=True, attribute=True) or [] if layer else []
    gate(layer and plugs and all(p.split(".")[0].split("|")[-1] == "prop_snapshot" for p in plugs),
         "Layer bakes the snapshot itself: %s - %s" % (plugs[:3], line))
    ok, text = same(shown, track(snap))
    gate(ok and curves(prop) == before_curves, "it shows the same; the prop untouched: " + text)


def case_h():
    case("H refusals")
    prop = make_prop()
    count = len(cmds.ls(type="transform") or [])
    gate(knots.snapshot([], highlight=None) == plan.SNAPSHOT_NOTHING, "nothing selected")
    cmds.select(prop + ".vtx[0]")
    line = knots.snapshot(highlight=None)
    gate(line == plan.SNAPSHOT_COMPONENTS, "a component: " + line)
    gate(len(cmds.ls(type="transform") or []) == count and not knots.knots(), "nothing made")


def case_i():
    case("I rig")
    from maya_scenesetup import catalog, character, deletion
    import maya_rigs
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    character.add_character(catalog.default_rig())
    rig = maya_rigs.rigs()[0]
    control = cmds.ls(maya_rigs.node(rig, "FKShoulder_R"), long=True)[0]
    bone = [j for j in cmds.ls(type="joint", long=True)
            if j.split("|")[-1].split(":")[-1] == "upperarm_r"
            and maya_rigs.under(j, rig.skeleton_root)][0]
    for t, rx, rz in ((0, 0.0, 0.0), (20, 30.0, -20.0), (40, 0.0, 10.0)):
        cmds.setKeyframe(control, attribute="rx", time=t, value=rx)
        cmds.setKeyframe(control, attribute="rz", time=t, value=rz)
    cmds.currentTime(12)
    bone_track, control_track = track(bone), track(control)
    control_curves = curves(control)
    line = knots.snapshot([bone, control], highlight=None)
    gate(line == "Snapshot: 2 objects over 0-40", line)
    ok, text = same(bone_track, track(snapshots_of(bone)[0]))
    gate(ok, "the bone's snapshot on upperarm_r: " + text)
    ok, text = same(control_track, track(snapshots_of(control)[0]))
    gate(ok, "the control's snapshot on FKShoulder_R: " + text)
    ok, text = same(bone_track, track(bone))
    gate(ok and curves(control) == control_curves, "the rig untouched: " + text)
    snap = snapshots_of(bone)[0]
    group = cmds.listRelatives(snap, parent=True, fullPath=True)[0]
    gate(group == rig.character + "|" + plan.GROUP_IN_CHARACTER,
         "in the character's Knots group: %s" % group)
    gate(plan.subtitle(len(knots.knots()) - len(knots.snapshots()), 0, 0,
                       len(knots.snapshots())) == "2 snapshots in the scene", "the subtitle")
    line = deletion.delete_selected([control], confirm=lambda text: True)
    gate(not knots.knots() and not cmds.objExists(group), "Delete character takes them: " + line)


def main():
    for run in (case_a, case_b, case_c, case_d, case_e, case_f, case_g, case_h, case_i):
        try:
            run()
        except Exception:
            import traceback
            traceback.print_exc()
            gate(False, "%s raised" % run.__name__)
    print("verify_snapshot: %d gates, %d failed%s" % (
        COUNT[0], len(FAILS), (" - " + ", ".join("%s#%d" % (c, n) for c, n, _ in FAILS))
        if FAILS else ""))


main()
