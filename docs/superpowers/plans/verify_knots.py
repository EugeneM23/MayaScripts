"""Standalone gates for the Tools card's knots (2026-10-12).

    mayapy verify_knots.py

mayapy STANDALONE, a fresh scene per case (spec
docs/superpowers/specs/2026-10-12-tools-knots-design.md). The prop: a cube under an animated
carrier (ty, ry keyed), its rotate pivot 2 cm up its own Y, rotate order zxy, tx / ry / rx keyed,
ty and tz free and unkeyed, rz locked at 5. Frames 0..40, the current frame 12.

A  Knot: nothing moves; the knot on the prop's world pivot and orientation; at world level in
   SkeldarKnots; marked; a knot edit (+10 on its tx) moves the prop 10 along world X; attach 0 the
   original; Remove restores every curve; undo of a create.
B  Bake keeps the edit, leaves no constraint / pairBlend / knot / group; undo brings the knot back.
C  A ranged knot (highlight 10..30): attach 0/1/1/0, the edit only inside, the outside keys kept
   by Bake.
D  Knot Orient: the knot rides the pivot; +30 on its ry turns the prop 30 deg and leaves the pivot
   path alone.
E  Knot Offset: the pivot rides the prop while waiting; a second begin refuses; Finish puts the
   knot on the chosen point, which then rides the knot through a 90 deg turn; Bake keeps it.
F  Double knot Local: the inner's rx 30 turns the prop about its OWN X, the pivot fixed.
G  Double knot World: the outer has no rotation; its ry 90 turns the prop about WORLD Y, its tx +5
   shifts the path 5 along world X.
H  Refusals change nothing.
I  A knot on a knot bakes inward.
J  The rotate order choice.
K  A Manny rig control: its game bone does not move, the knot in the character's Knots group,
   Delete character takes it.
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

from maya_tools import knotplan as plan, knots  # noqa: E402

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


def origin(node):
    m = wm(node)
    return om.MVector(m[12], m[13], m[14])


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
    """{channel: (times, values, in, out)} or the plain value."""
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


def nudge(node, ch, delta):
    plug = node + "." + ch
    if cmds.keyframe(plug, query=True, keyframeCount=True):
        cmds.keyframe(plug, edit=True, relative=True, valueChange=delta)
    else:
        cmds.setAttr(plug, cmds.getAttr(plug) + delta)


def leftovers(prop):
    groups = [n for n in cmds.ls(type="transform", long=True) or []
              if cmds.attributeQuery(plan.GROUP_MARKER, node=n, exists=True)]
    return {"knots": knots.knots(), "pivots": knots.pivots(), "groups": groups,
            "pairBlends": cmds.ls(type="pairBlend") or [],
            "constraints": cmds.listRelatives(prop, children=True, type="constraint") or [],
            "blend attrs": [a for a in (cmds.listAttr(prop, userDefined=True) or [])
                            if a.startswith("blend")]}


def clean(prop):
    left = leftovers(prop)
    return not any(left.values()), str(dict((k, v) for k, v in left.items() if v))


def transforms_count():
    return len(cmds.ls(type="transform") or [])


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
    case("A knot")
    prop = make_prop()
    before_curves = curves(prop)
    before = track(prop)
    count = transforms_count()
    line = knots.create("knot", [prop], highlight=None)
    gate("rides prop_knot" in line, line)
    knot = knot_of(prop)
    gate(knot is not None, "the knot %s" % knot)
    ok, text = same(before, track(prop))
    gate(ok, "nothing moves at creation: " + text)
    gate((origin(knot) - pivot(prop)).length() < EPS_CM and ang(rot(wm(knot)), rot(wm(prop))) < EPS_DEG,
         "on the prop's world pivot and orientation at frame 12")
    parent = cmds.listRelatives(knot, parent=True, fullPath=True)[0]
    gate(parent == "|" + plan.GROUP_AT_WORLD
         and cmds.attributeQuery(plan.GROUP_MARKER, node=parent, exists=True)
         and cmds.getAttr(parent + ".translateX", lock=True),
         "at world level in %s (locked, marked)" % parent)
    cons = knots.constraints_of(prop)
    gate(len(cons) == 1 and cmds.getAttr(cons[0] + "." + plan.OF_MARKER) == cmds.ls(knot, uuid=True)[0],
         "the prop's constraint marked with the knot")
    gate(cmds.getAttr(knot + "." + plan.ATTACH) == 1.0
         and not cmds.keyframe(knot + "." + plan.ATTACH, query=True, keyframeCount=True),
         "attach 1, unkeyed (whole take)")
    keyed = plan.decode_keyed(cmds.getAttr(knot + "." + plan.KEYED_MARKER))
    gate(keyed == {"ty": 1.0, "tz": 3.0}, "the free unkeyed channels keyed: %s" % keyed)
    gate(cmds.getAttr(prop + ".rz") == 5.0 and not cmds.listConnections(prop + ".rz", source=True,
                                                                         destination=False),
         "the locked rz untouched")
    gate(cmds.currentTime(query=True) == 12, "the frame is still 12")
    gate(knot in (cmds.ls(selection=True, long=True) or []), "the knot is selected")

    nudge(knot, "tx", 10.0)
    after = track(prop)
    shifted = dict((f, (before[f][0] + om.MVector(10, 0, 0), before[f][1])) for f in FRAMES)
    ok, text = same(shifted, after)
    gate(ok, "knot tx +10 moves the prop 10 along world X: " + text)

    cmds.setAttr(knot + "." + plan.ATTACH, 0.0)
    ok, text = same(before, track(prop))
    gate(ok, "attach 0 plays the original: " + text)
    cmds.setAttr(knot + "." + plan.ATTACH, 1.0)

    line = knots.remove([knot])
    gate("Removed 1 knot" in line, line)
    gate(curves(prop) == before_curves, "Remove restores every curve and value exactly")
    ok, text = clean(prop)
    gate(ok, "nothing left: " + text)
    gate(transforms_count() == count, "as many transforms as before")

    knots.create("knot", [prop], highlight=None)
    cmds.undo()
    ok, text = clean(prop)
    gate(ok and curves(prop) == before_curves, "one undo takes a create back: " + text)

    knots.create("knot", [prop], highlight=None)
    knot = knot_of(prop)
    knots.remove([prop])                                          # the object names its knot
    gate(knot_of(prop) is None, "Remove through the object")
    cmds.undo()
    gate(knot_of(prop) is not None and len(knots.constraints_of(prop)) == 1,
         "one undo brings a removed knot back")


def case_b():
    case("B bake")
    prop = make_prop()
    knots.create("knot", [prop], highlight=None)
    knot = knot_of(prop)
    nudge(knot, "tx", 10.0)
    nudge(knot, "ry", 15.0)
    edited = track(prop)
    line = knots.bake([knot])
    cmds.undo()                    # straight away: a time walk is an undo step and ends redo
    gate(knot_of(prop) is not None and len(knots.constraints_of(prop)) == 1,
         "undo of Bake brings the knot and the constraint back")
    cmds.redo()
    gate("Baked 1 knot onto prop" in line, line)
    ok, text = same(edited, track(prop))
    gate(ok, "the prop keeps the edit: " + text)
    ok, text = clean(prop)
    gate(ok, "nothing left: " + text)
    times = cmds.keyframe(prop + ".tx", query=True, timeChange=True) or []
    gate(times == [float(f) for f in FRAMES], "tx keyed on every frame of the take")
    gate(prop in (cmds.ls(selection=True, long=True) or []), "the prop is selected after")


def case_c():
    case("C range")
    prop = make_prop()
    before = track(prop)
    line = knots.create("knot", [prop], highlight=(10.0, 30.0))
    gate("10-29" in line, line)
    knot = knot_of(prop)
    keys = list(zip(cmds.keyframe(knot + "." + plan.ATTACH, query=True, timeChange=True),
                    cmds.keyframe(knot + "." + plan.ATTACH, query=True, valueChange=True)))
    gate(keys == [(9.0, 0.0), (10.0, 1.0), (29.0, 1.0), (30.0, 0.0)], "attach keys %s" % keys)
    ok, text = same(before, track(prop))
    gate(ok, "nothing moves: " + text)
    nudge(knot, "tx", 10.0)
    after = track(prop)
    inside = [f for f in FRAMES if 10 <= f <= 29]
    outside = [f for f in FRAMES if f <= 8 or f >= 31]
    shifted = dict((f, (before[f][0] + om.MVector(10, 0, 0), before[f][1])) for f in inside)
    ok_in, text_in = same(shifted, after, inside)
    ok_out, text_out = same(before, after, outside)
    gate(ok_in and ok_out, "the edit inside only: %s inside, %s outside" % (text_in, text_out))
    halves = [f / 2.0 for f in range(0, 81) if f / 2.0 <= 8.0 or f / 2.0 >= 31.0]
    before_halves = track(prop, halves)                   # the knot's attach is 0 there
    knots.bake([knot])
    baked = track(prop)
    ok_in, text_in = same(shifted, baked, inside)
    ok_out, text_out = same(before, baked, outside)
    gate(ok_in and ok_out, "Bake keeps it: %s inside, %s outside" % (text_in, text_out))
    ok, text = same(before_halves, track(prop, halves))
    gate(ok, "the curve outside the range not bent (half frames): " + text)
    times = cmds.keyframe(prop + ".tx", query=True, timeChange=True) or []
    out_keys = [t for t in times if t < 9 or t > 30]
    gate(out_keys == [0.0, 40.0], "the prop's own tx keys outside the range kept: %s" % out_keys)
    ok, text = clean(prop)
    gate(ok, "nothing left: " + text)


def case_d():
    case("D orient")
    prop = make_prop()
    before_curves = curves(prop)
    before = track(prop)
    knots.create("orient", [prop], highlight=None)
    knot = knot_of(prop)
    gate(cmds.getAttr(knot + "." + plan.KIND_MARKER) == "orient", "kind orient")
    ok, text = same(before, track(prop))
    gate(ok, "nothing moves: " + text)
    worst = 0.0
    for f in (0, 10, 25, 40):
        cmds.currentTime(f)
        worst = max(worst, (origin(knot) - pivot(prop)).length())
    cmds.currentTime(12)
    gate(worst < EPS_CM and cmds.getAttr(knot + ".tx", lock=True),
         "the knot rides the prop's pivot (%.6f), translate locked" % worst)
    gate(not cmds.listConnections(prop + ".tx", source=True, destination=False, type="pairBlend"),
         "the prop's translation is its own (no pairBlend on tx)")
    nudge(knot, "ry", 30.0)
    after = track(prop)
    path = max((before[f][0] - after[f][0]).length() for f in FRAMES)
    turn = [ang(before[f][1], after[f][1]) for f in FRAMES]
    gate(path < EPS_CM and max(abs(t - 30.0) for t in turn) < EPS_DEG,
         "ry +30 turns the prop 30 deg (%.6f..%.6f), the pivot path stays (%.6f)"
         % (min(turn), max(turn), path))
    knots.remove([knot])
    gate(curves(prop) == before_curves, "Remove restores every curve")


def case_e():
    case("E offset")
    prop = make_prop()
    before = track(prop)
    count = transforms_count()
    line = knots.begin_offset([prop], highlight=None)
    gate("press Finish" in line, line)
    piv = knots.pivots()
    gate(len(piv) == 1 and knots.waiting(), "one pivot waiting")
    piv = piv[0]
    gate(piv in (cmds.ls(selection=True, long=True) or []), "the pivot is selected")
    cmds.setAttr(piv + ".ty", 5.0)
    point = om.MPoint(0.0, 7.0, 0.0)                               # the prop's rp + (0, 5, 0)
    worst = 0.0
    for f in (0, 30):
        cmds.currentTime(f)
        worst = max(worst, (origin(piv) - om.MVector(point * wm(prop))).length())
    cmds.currentTime(12)
    gate(worst < EPS_CM, "the pivot rides the prop while waiting (%.6f)" % worst)
    again = knots.begin_offset([prop], highlight=None)
    gate("waiting" in again and len(knots.pivots()) == 1, "a second begin refuses: " + again)
    line = knots.finish_offset([])
    gate("rides prop_knotOffset" in line, line)
    knot = knot_of(prop)
    gate(not knots.pivots() and not knots.waiting(), "no pivot left")
    ok, text = same(before, track(prop))
    gate(ok, "nothing moves: " + text)
    gate((origin(knot) - om.MVector(point * wm(prop))).length() < EPS_CM,
         "the knot stands on the chosen point")
    nudge(knot, "ry", 90.0)
    worst, turned = 0.0, 0.0
    now = cmds.currentTime(query=True)
    for f in FRAMES:
        cmds.currentTime(f)
        worst = max(worst, (origin(knot) - om.MVector(point * wm(prop))).length())
        turned = max(turned, ang(before[f][1], rot(wm(prop))))
    cmds.currentTime(now)
    gate(worst < EPS_CM and abs(turned - 90.0) < 0.01,
         "turned 90 deg (%.4f) about the chosen point (%.6f)" % (turned, worst))
    edited = track(prop)
    knots.bake([knot])
    ok, text = same(edited, track(prop))
    gate(ok, "Bake keeps it: " + text)
    ok, text = clean(prop)
    gate(ok and transforms_count() == count, "nothing left: " + text)
    knots.begin_offset([prop], highlight=None)
    line = knots.remove([knots.pivots()[0]])
    gate("1 pivot dropped" in line and not knots.pivots() and transforms_count() == count,
         "Remove drops a waiting pivot: " + line)


def case_f():
    case("F double local")
    prop = make_prop(lock_rz=False)            # a local turn needs every rotate channel
    before_curves = curves(prop)
    before = track(prop)
    knots.create("double_local", [prop], highlight=None)
    top = knot_of(prop)
    inner = cmds.listRelatives(top, children=True, type="transform", fullPath=True)
    inner = [n for n in inner if cmds.listRelatives(n, shapes=True)]
    gate(len(inner) == 1 and inner[0] in (cmds.ls(selection=True, long=True) or []),
         "outer %s, inner %s selected" % (top, inner))
    inner = inner[0]
    ok, text = same(before, track(prop))
    gate(ok, "nothing moves: " + text)
    cmds.setAttr(inner + ".rx", 30.0)
    after = track(prop)
    rx30 = om.MEulerRotation(math.radians(30), 0, 0).asQuaternion()
    worst = max(ang(rx30 * before[f][1], after[f][1]) for f in FRAMES)
    path = max((before[f][0] - after[f][0]).length() for f in FRAMES)
    gate(worst < EPS_DEG and path < EPS_CM,
         "inner rx 30 turns the prop about its own X (%.6f deg), the pivot fixed (%.6f)"
         % (worst, path))
    knots.remove([inner])
    gate(curves(prop) == before_curves, "Remove (through the inner) restores every curve")
    ok, text = clean(prop)
    gate(ok, "nothing left: " + text)


def case_g():
    case("G double world")
    prop = make_prop()
    before = track(prop)
    knots.create("double_world", [prop], highlight=None)
    top = knot_of(prop)
    gate(top in (cmds.ls(selection=True, long=True) or []), "the outer is selected")
    inner = [n for n in cmds.listRelatives(top, children=True, type="transform", fullPath=True)
             if cmds.listRelatives(n, shapes=True)][0]
    zero = all(abs(cmds.getAttr(top + "." + ch, time=f)) < 1e-9
               for ch in plan.ROTATE for f in (0, 20, 40))
    still = all(abs(cmds.getAttr(inner + "." + ch, time=f)) < 1e-9
                for ch in plan.TRANSLATE for f in (0, 20, 40))
    gate(zero and still, "the outer has no rotation, the inner no translation")
    ok, text = same(before, track(prop))
    gate(ok, "nothing moves: " + text)
    cmds.setAttr(top + ".ry", 90.0)
    after = track(prop)
    ry90 = om.MEulerRotation(0, math.radians(90), 0).asQuaternion()
    worst = max(ang(before[f][1] * ry90, after[f][1]) for f in FRAMES)
    path = max((before[f][0] - after[f][0]).length() for f in FRAMES)
    gate(worst < EPS_DEG and path < EPS_CM,
         "outer ry 90 turns the prop about WORLD Y (%.6f deg), the pivot fixed (%.6f)"
         % (worst, path))
    nudge(top, "tx", 5.0)
    after = track(prop)
    shifted = dict((f, (before[f][0] + om.MVector(5, 0, 0), after[f][1])) for f in FRAMES)
    ok, text = same(shifted, after)
    gate(ok, "outer tx +5 shifts the path 5 along world X: " + text)
    knots.remove([prop])
    ok, text = clean(prop)
    gate(ok, "nothing left: " + text)


def case_h():
    case("H refusals")
    prop = make_prop()
    knots.create("knot", [prop], highlight=None)
    count = transforms_count()
    line = knots.create("knot", [prop], highlight=None)
    gate("already rides a knot" in line and transforms_count() == count, line)
    driven = cmds.polyCube(name="driven")[0]
    cmds.expression(string="%s.tx = frame;" % driven)
    count = transforms_count()
    line = knots.create("knot", [driven], highlight=None)
    gate("expression" in line and transforms_count() == count, line)
    stuck = cmds.polyCube(name="stuck")[0]
    for ch in plan.CHANNELS:
        cmds.setAttr(stuck + "." + ch, lock=True)
    count = transforms_count()
    line = knots.create("knot", [stuck], highlight=None)
    gate("no free translate or rotate" in line and transforms_count() == count, line)
    line = knots.create("knot", [], highlight=None)
    gate(line == plan.NOTHING, line)
    line = knots.begin_offset([driven, stuck], highlight=None)
    gate(line == plan.OFFSET_ONE, line)
    cmds.select(clear=True)
    gate(knots.bake() == plan.BAKE_NOTHING, "Bake with nothing selected refuses")
    gate(knots.remove() == plan.REMOVE_NOTHING, "Remove with nothing selected refuses")
    gate(len(knots.knots()) == 1, "the standing knot was never touched")


def case_i():
    case("I knot on a knot")
    prop = make_prop()
    before = track(prop)
    knots.create("knot", [prop], highlight=None)
    a = knot_of(prop)
    line = knots.create("knot", [a], highlight=None)
    gate("rides" in line, "a knot can be knotted: " + line)
    b = [k for k in knots.knots() if knots.source_of(k) == a][0]
    nudge(b, "tx", 5.0)
    shifted = dict((f, (before[f][0] + om.MVector(5, 0, 0), before[f][1])) for f in FRAMES)
    ok, text = same(shifted, track(prop))
    gate(ok, "the outer knot moves the prop through the inner: " + text)
    knots.bake([a, b])
    ok, text = same(shifted, track(prop))
    gate(ok, "Bake collapses inward: " + text)
    ok, text = clean(prop)
    gate(ok and not knots.knots(), "nothing left: " + text)


def case_j():
    case("J rotate order")
    prop = make_prop()
    knots.create("knot", [prop], order="xzy", highlight=None)
    gate(cmds.getAttr(knot_of(prop) + ".rotateOrder") == 3, "xzy -> 3")
    knots.remove([prop])
    knots.create("knot", [prop], order="object", highlight=None)
    gate(cmds.getAttr(knot_of(prop) + ".rotateOrder") == 2, "object -> the prop's zxy (2)")


def case_k():
    case("K rig")
    from maya_scenesetup import catalog, character, deletion
    import maya_rigs
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    character.add_character(catalog.default_rig())
    rig = maya_rigs.rigs()[0]
    control = cmds.ls(maya_rigs.node(rig, "FKShoulder_R"), long=True)[0]
    bone = [j for j in cmds.ls(type="joint", long=True) if j.split("|")[-1].split(":")[-1] == "upperarm_r"
            and maya_rigs.under(j, rig.skeleton_root)][0]
    for t, rx, rz in ((0, 0.0, 0.0), (20, 30.0, -20.0), (40, 0.0, 10.0)):
        cmds.setKeyframe(control, attribute="rx", time=t, value=rx)
        cmds.setKeyframe(control, attribute="rz", time=t, value=rz)
    cmds.currentTime(12)
    before = track(bone)
    line = knots.create("knot", [control], highlight=None)
    gate("rides FKShoulder_R_knot" in line, line)
    ok, text = same(before, track(bone))
    gate(ok, "upperarm_r does not move: " + text)
    knot = knot_of(control)
    group = cmds.listRelatives(knot, parent=True, fullPath=True)[0]
    gate(group == rig.character + "|" + plan.GROUP_IN_CHARACTER,
         "the knot in the character's Knots group: %s" % group)
    line = deletion.delete_selected([control], confirm=lambda text: True)
    gate(not knots.knots() and not cmds.objExists(group), "Delete character takes it: " + line)


def bare_cube(name="cube", parent=None):
    cube = cmds.polyCube(name=name)[0]
    if parent:
        cube = cmds.parent(cube, parent)[0]
    return cmds.ls(cube, long=True)[0]


def case_l():
    case("L the review's findings")
    # 1. Bake must not rewrite the animator's rotate keys outside the knot.
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    cube = bare_cube()
    for t, rx in ((0, 0.0), (5, 10.0), (35, 20.0), (40, 300.0)):
        cmds.setKeyframe(cube, attribute="rx", time=t, value=rx, inTangentType="linear",
                         outTangentType="linear")
    cmds.currentTime(12)
    knots.create("knot", [cube], highlight=(10.0, 21.0))
    knots.bake([cube])
    keys = dict(zip(cmds.keyframe(cube + ".rx", query=True, timeChange=True),
                    cmds.keyframe(cube + ".rx", query=True, valueChange=True)))
    gate([round(keys.get(t, -1), 6) for t in (0.0, 5.0, 35.0, 40.0)] == [0.0, 10.0, 20.0, 300.0],
         "a ranged Bake leaves the rotate keys outside it alone: %s"
         % [round(keys.get(t, -1), 3) for t in (0.0, 5.0, 35.0, 40.0)])
    # 2. A knot whose attach was keyed to 0 everywhere: Bake bakes nothing and changes nothing.
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    cube = bare_cube()
    for t, rx in ((0, 0.0), (5, 10.0), (35, 20.0), (40, 300.0)):
        cmds.setKeyframe(cube, attribute="rx", time=t, value=rx, inTangentType="linear",
                         outTangentType="linear")
    before_curves = curves(cube)
    knots.create("knot", [cube], highlight=None)
    knot = knot_of(cube)
    cmds.setKeyframe(knot, attribute=plan.ATTACH, time=0, value=0.0)
    knots.bake([knot])
    gate(curves(cube) == before_curves and not knots.knots(),
         "attach 0 everywhere: Bake leaves every curve as it was")
    # 3. A spinning object: the baked keys stay a spin (no 360 jumps between them).
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    cube = bare_cube()
    for t, ry in ((0, 0.0), (40, 720.0)):
        cmds.setKeyframe(cube, attribute="ry", time=t, value=ry, inTangentType="linear",
                         outTangentType="linear")
    cmds.currentTime(12)
    knots.create("knot", [cube], highlight=None)
    knot = knot_of(cube)
    nudge(knot, "rx", 10.0)
    edited = track(cube)
    knots.bake([knot])
    values = cmds.keyframe(cube + ".ry", query=True, valueChange=True)
    jump = max(abs(b - a) for a, b in zip(values, values[1:]))
    ok, text = same(edited, track(cube))
    gate(ok and jump < 90.0, "a spin baked stays a spin (largest step %.2f deg), the edit kept: %s"
         % (jump, text))
    # 4. A knot on a knot, the OBJECT selected: both bake, nothing orphaned.
    prop = make_prop()
    before = track(prop)
    knots.create("knot", [prop], highlight=None)
    a = knot_of(prop)
    knots.create("knot", [a], highlight=None)
    b = [k for k in knots.knots() if knots.source_of(k) == a][0]
    nudge(b, "tx", 5.0)
    shifted = dict((f, (before[f][0] + om.MVector(5, 0, 0), before[f][1])) for f in FRAMES)
    knots.bake([prop])
    ok, text = same(shifted, track(prop))
    gate(ok and not knots.knots(), "the object selected bakes both knots, none orphaned: " + text)
    # 5. Remove of the base knot takes the knot riding it too, curves restored.
    prop = make_prop()
    before_curves = curves(prop)
    knots.create("knot", [prop], highlight=None)
    a = knot_of(prop)
    knots.create("knot", [a], highlight=None)
    knots.remove([a])
    gate(not knots.knots() and curves(prop) == before_curves,
         "Remove of the base knot takes its rider, the curves restored")
    # 6. A narrowed playback range: the knot still covers the animation range.
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=10, max=20, animationStartTime=0, animationEndTime=40)
    carrier = cmds.createNode("transform", name="carrier")
    for t, tx in ((0, 0.0), (40, 50.0)):
        cmds.setKeyframe(carrier, attribute="tx", time=t, value=tx)
    cube = bare_cube(parent=carrier)
    cmds.currentTime(12)
    before = track(cube)
    knots.create("knot", [cube], highlight=None)
    ok, text = same(before, track(cube))
    gate(ok, "a narrowed playback: nothing moves over the whole animation range: " + text)
    # 7. An unevenly scaled parent refuses.
    cmds.file(new=True, force=True)
    squashed = cmds.createNode("transform", name="squashed")
    cmds.setAttr(squashed + ".scale", 1.0, 2.5, 0.7, type="double3")
    cube = bare_cube(parent=squashed)
    count = transforms_count()
    line = knots.create("knot", [cube], highlight=None)
    gate("scaled unevenly" in line and transforms_count() == count, line)
    # 8. A node the animator parented under a knot survives Remove, in place.
    prop = make_prop()
    knots.create("knot", [prop], highlight=None)
    knot = knot_of(prop)
    mine = cmds.spaceLocator(name="animatorsOwn")[0]
    mine = cmds.parent(mine, knot)[0]
    uuid = cmds.ls(mine, uuid=True)[0]
    where = origin(cmds.ls(uuid, long=True)[0])
    knots.remove([knot])
    kept = cmds.ls(uuid, long=True)
    gate(bool(kept) and (origin(kept[0]) - where).length() < EPS_CM,
         "the animator's node under a knot survives Remove in place: %s" % kept)


def main():
    for run in (case_a, case_b, case_c, case_d, case_e, case_f, case_g, case_h, case_i,
                case_j, case_l, case_k):
        try:
            run()
        except Exception:
            import traceback
            traceback.print_exc()
            gate(False, "%s raised" % run.__name__)
    print("verify_knots: %d gates, %d failed%s" % (
        COUNT[0], len(FAILS), (" - " + ", ".join("%s#%d" % (c, n) for c, n, _ in FAILS))
        if FAILS else ""))


main()
