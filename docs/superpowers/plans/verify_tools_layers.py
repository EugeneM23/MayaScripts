"""Standalone gates for the Tools card on animation layers (2026-10-15).

    mayapy verify_tools_layers.py

The animator: «Bake to layer должна создавать новый слой и перекидывать туда анимацию с текущего
выбранного слоя ... опция смены парента не работает если на объекте уже есть слой ... To world тоже
... Давай проверим все инструменты на работоспособность в случае если у нас есть анимационный
слой». mayapy STANDALONE, a fresh scene per case. The fixture: a prop keyed on the base (tx, ry),
an additive layer `Anim1` holding tx / ty / rz keys of it, rotate pivot off its origin, zxy;
carrier B at world level (tx, rz keyed). Frames 0..40, the current frame 12.

K  every knot kind on the layered prop: made, nothing moves; a knot edited moves it; Remove gives
   the layers back exactly; Bake keeps what it showed - into the base with no layer selected,
   into Anim1 when it is selected (the base untouched); a ranged knot's bake unbent outside.
P  Inside / World / Swap on the layered prop: the world track kept on every frame, Anim1's curves
   untouched (keyed into the base), or keyed into Anim1 when it is selected; one undo.
L  Layer always takes the base (2026-10-15): the prop only on Anim1 refused; Anim1 (or Anim2, or
   a muted Anim1) selected - the base's keys moved as keys, the base without a curve, the other
   layers untouched, shown kept at half frames; a highlight bridging the base; Layer on a knot
   keeps the knot driving, Layer on the prop then takes it off.
O  Overlap, Attach and Snapshot on layered objects.
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

from maya_tools import knotplan as plan, knots, layerbake, overlap, overlapplan, reparent  # noqa

FAILS = []
COUNT = [0]
CASE = ["-"]
FRAMES = list(range(0, 41))
HALVES = [f + 0.5 for f in range(40)]
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


def track(node, frames=FRAMES):
    out = {}
    now = cmds.currentTime(query=True)
    for f in frames:
        cmds.currentTime(f, update=True)
        p = om.MVector(*cmds.xform(node, query=True, worldSpace=True, rotatePivot=True))
        out[f] = (p, rot(wm(node)))
    cmds.currentTime(now, update=True)
    return out


def same(a, b, frames=None, eps=EPS_CM):
    cm = deg = 0.0
    for f in (frames if frames is not None else a):
        cm = max(cm, (a[f][0] - b[f][0]).length())
        deg = max(deg, ang(a[f][1], b[f][1]))
    return cm < eps and deg < EPS_DEG * (eps / EPS_CM), "%.6f cm, %.6f deg" % (cm, deg)


def curves(layer, node):
    """{channel: (key times, values)} of the node's curves on `layer` (the base: a plug keyed
    plainly in a layered scene is its own curve - `maya_poselib.keys.curve_for`)."""
    from maya_poselib import keys
    out = {}
    for ch in plan.CHANNELS:
        found = keys.curve_for("%s.%s" % (node, plan.LONG[ch]), layer)
        if found:
            out[ch] = (tuple(round(t, 6) for t in cmds.keyframe(found, query=True,
                                                                 timeChange=True) or []),
                       tuple(round(v, 6) for v in cmds.keyframe(found, query=True,
                                                                 valueChange=True) or []))
    return out


def select_layer(layer):
    for each in cmds.ls(type="animLayer") or []:
        cmds.animLayer(each, edit=True, selected=(each == layer))


def scene(base_keys=True):
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    prop = cmds.polyCube(name="prop")[0]
    cmds.setAttr(prop + ".rotateOrder", 2)
    cmds.setAttr(prop + ".rotatePivot", 0, 2, 0)
    if base_keys:
        for t, v in ((0, 0), (20, 6), (40, 2)):
            cmds.setKeyframe(prop, attribute="tx", time=t, value=v)
            cmds.setKeyframe(prop, attribute="ry", time=t, value=v * 9)
    b = cmds.polyCube(name="B")[0]
    for t, v in ((0, 0), (40, 8)):
        cmds.setKeyframe(b, attribute="tx", time=t, value=v)
        cmds.setKeyframe(b, attribute="rz", time=t, value=v * 5)
    lay = cmds.animLayer("Anim1")
    cmds.animLayer(lay, edit=True, attribute=["prop.tx", "prop.ty", "prop.rz"])
    for t, v in ((0, 0), (10, 3), (25, -2), (40, 1)):
        cmds.setKeyframe(prop, attribute="ty", animLayer=lay, time=t, value=v)
        cmds.setKeyframe(prop, attribute="rz", animLayer=lay, time=t, value=v * 7)
        cmds.setKeyframe(prop, attribute="tx", animLayer=lay, time=t, value=v * 0.5
                         + (cmds.getAttr(prop + ".tx", time=t) if base_keys else 0))
    select_layer(None)
    cmds.currentTime(12)
    return "|prop", "|B", lay


def no_highlight():
    return None


# ------------------------------------------------------------------- K

case("K knots")
for kind in ("knot", "orient", "double_local", "double_world"):
    prop, b, lay = scene()
    before = track(prop)
    line = knots.create(kind, [prop], highlight=None)
    ok, how = same(before, track(prop))
    gate(bool(knots.knots()) and ok, "%s on the layered prop: %s; %s" % (kind, line, how))

prop, b, lay = scene()
line = knots.begin_offset([prop], highlight=None)
line2 = knots.finish_offset()
gate(len(knots.knots()) == 1, "Knot Offset on the layered prop: %s / %s" % (line, line2))

prop, b, lay = scene()
before = track(prop)
line = knots.begin_aim([prop], highlight=None)
line2 = knots.finish_aim()
ok, how = same(before, track(prop))
gate(len(knots.knots()) == 1 and ok, "Aim on the layered prop: %s / %s; %s" % (line, line2, how))

prop, b, lay = scene()
before = track(prop)
line = knots.create_across([(prop, b)], highlight=None)
ok, how = same(before, track(prop))
gate(len(knots.knots()) == 1 and ok, "Across on the layered prop: %s; %s" % (line, how))

# Remove gives the layers back exactly
prop, b, lay = scene()
before, layer_before = track(prop), curves(lay, prop)
knots.create("knot", [prop], highlight=None)
top = knots.knots()[0]
cmds.setKeyframe(top, attribute="tx", time=20, value=cmds.getAttr(top + ".tx", time=20) + 10)
edited = track(prop)
moved = (edited[20][0] - before[20][0]).length()
gate(moved > 5, "a knot edited moves the layered prop: %.3f cm" % moved)
knots.remove([top])
ok, how = same(before, track(prop))
gate(ok and curves(lay, prop) == layer_before, "Remove: the layered prop as before: " + how)

# Bake with no layer selected: into the base, Anim1 untouched
prop, b, lay = scene()
layer_before = curves(lay, prop)
knots.create("knot", [prop], highlight=None)
top = knots.knots()[0]
cmds.setKeyframe(top, attribute="tx", time=20, value=cmds.getAttr(top + ".tx", time=20) + 10)
shown = track(prop)
line = knots.bake([top])
ok, how = same(shown, track(prop))
gate(ok and not knots.knots() and curves(lay, prop) == layer_before
     and not cmds.ls(type="pairBlend"),
     "Bake (no layer selected): %s; as shown %s, Anim1 untouched" % (line, how))
gate(same(shown, track(prop, HALVES + FRAMES), FRAMES)[0], "  the frames again after the bake")

prop, b, lay = scene()
knots.create("knot", [prop], highlight=None)
top = knots.knots()[0]
cmds.setKeyframe(top, attribute="tx", time=20, value=cmds.getAttr(top + ".tx", time=20) + 10)
shown = track(prop)
knots.bake([top])
cmds.undo()                       # straight after the press: a time change is an undo step (222)
ok, how = same(shown, track(prop))
gate(len(knots.knots()) == 1 and ok, "  one undo brings the knot back: " + how)

# Bake with Anim1 selected: into Anim1, the base untouched
prop, b, lay = scene()
base_before = curves("BaseAnimation", prop)
knots.create("knot", [prop], highlight=None)
top = knots.knots()[0]
cmds.setKeyframe(top, attribute="tz", time=20, value=cmds.getAttr(top + ".tz", time=20) + 7)
shown = track(prop)
select_layer(lay)
line = knots.bake([top])
ok, how = same(shown, track(prop))
gate(ok and curves("BaseAnimation", prop) == base_before,
     "Bake (Anim1 selected): %s; as shown %s, the base untouched" % (line, how))
gate("prop.translateZ" in (cmds.animLayer(lay, query=True, attribute=True) or []),
     "  Anim1 took tz (it did not hold it)")

# a ranged knot: unbent outside its span at half frames
prop, b, lay = scene()
before = track(prop, FRAMES + HALVES)
knots.create("knot", [prop], highlight=(10, 21))
top = knots.knots()[0]
cmds.setKeyframe(top, attribute="tx", time=15, value=cmds.getAttr(top + ".tx", time=15) + 6)
shown = track(prop, FRAMES + HALVES)
knots.bake([top])
after = track(prop, FRAMES + HALVES)
outside = [f for f in FRAMES + HALVES if f < 9 or f > 21]
ok_out, how_out = same(before, after, outside)
ok_in, how_in = same(shown, after, list(range(9, 22)))
gate(ok_out and ok_in, "a ranged knot baked: outside %s, inside %s" % (how_out, how_in))

# ------------------------------------------------------------------- P

case("P re-parent")
prop, b, lay = scene()
before, layer_before = track(prop), curves(lay, prop)
line = reparent.inside([prop, b])
moved = cmds.ls("prop", long=True)[0]
ok, how = same(before, track(moved))
gate(moved == "|B|prop" and ok and curves(lay, moved) == layer_before,
     "Inside: %s; world track %s, Anim1 untouched" % (line, how))
gate(same(before, track(moved, HALVES + FRAMES), FRAMES)[0], "  again after a time walk")

prop, b, lay = scene()
before, layer_before = track(prop), curves(lay, prop)
reparent.inside([prop, b])
cmds.undo()
ok, how = same(before, track("|prop"))
gate(cmds.ls("prop", long=True)[0] == "|prop" and ok and curves(lay, "|prop") == layer_before,
     "  one undo puts it back: " + how)

prop, b, lay = scene()
cmds.parent(prop, b)
prop = "|B|prop"
before, layer_before = track(prop), curves(lay, prop)
line = reparent.to_world([prop])
moved = cmds.ls("prop", long=True)[0]
ok, how = same(before, track(moved))
gate(moved == "|prop" and ok and curves(lay, moved) == layer_before,
     "World: %s; world track %s, Anim1 untouched" % (line, how))

prop, b, lay = scene()
cmds.parent(prop, b)
before_p, before_b = track("|B|prop"), track("|B")
line = reparent.swap(["|B", "|B|prop"])
p2, b2 = cmds.ls("prop", long=True)[0], cmds.ls("B", long=True)[0]
ok1, how1 = same(before_p, track(p2))
ok2, how2 = same(before_b, track(b2))
gate(p2 == "|prop" and b2 == "|prop|B" and ok1 and ok2,
     "Swap: %s; prop %s, B %s" % (line, how1, how2))

prop, b, lay = scene()
select_layer(lay)
base_before = curves("BaseAnimation", prop)
before = track(prop)
line = reparent.inside([prop, b])
moved = cmds.ls("prop", long=True)[0]
ok, how = same(before, track(moved))
gate(ok and curves("BaseAnimation", moved) == base_before,
     "Inside with Anim1 selected: %s; world %s, the base untouched" % (line, how))

# ------------------------------------------------------------------- L

case("L layer")
#  Layer always takes the base (2026-10-15): a layer selected in the Anim Layer Editor is not the
#  source, and every other layer stays as it is.
prop, b, lay = scene(base_keys=False)
before = (curves(lay, prop), sorted(cmds.ls(type="animLayer")))
line = layerbake.bake([prop], highlight=None)
gate("on layers already" in line and not layerbake.bake_layers()
     and (curves(lay, prop), sorted(cmds.ls(type="animLayer"))) == before,
     "only on Anim1: refused, nothing changed: " + line)


def taken_from_base(label, select=None, highlight=None, mute=None):
    prop, b, lay = scene()
    extra = None
    if select == "Anim2":
        extra = cmds.animLayer("Anim2")
        cmds.animLayer(extra, edit=True, attribute=["prop.tz"])
        cmds.setKeyframe(prop, attribute="tz", animLayer=extra, time=0, value=0)
        cmds.setKeyframe(prop, attribute="tz", animLayer=extra, time=30, value=4)
    if mute:
        cmds.animLayer(lay, edit=True, mute=True)
    select_layer(extra or (lay if select else None))
    base_keys = curves("BaseAnimation", prop)
    others = dict((n, curves(n, prop)) for n in (lay, extra) if n)
    shown = track(prop, FRAMES + HALVES)
    line = layerbake.bake([prop], highlight=highlight)
    new = layerbake.bake_layers()
    ok, how = same(shown, track(prop, FRAMES + HALVES))
    untouched = all(curves(n, prop) == c for n, c in others.items())
    if highlight:
        cleared = curves("BaseAnimation", prop) != base_keys
    else:
        cleared = not curves("BaseAnimation", prop)
        moved = curves(new[0], prop) if new else {}
        cleared = cleared and all(moved.get(ch, ((),))[0] == base_keys[ch][0]
                                  for ch in base_keys)
    gate(ok and len(new) == 1 and untouched and cleared,
         "%s: %s; shown %s, the other layers untouched %s, the base's keys %s" % (
             label, line, how, untouched,
             "bridged" if highlight else "moved as keys, the base without a curve"))


taken_from_base("Anim1 selected, base keyed too: taken from the base", select=True)
taken_from_base("Anim1 selected, a highlight", select=True, highlight=(10, 21))
taken_from_base("a muted Anim1 selected: not refused, taken from the base", select=True,
                mute=True)
taken_from_base("Anim2 selected over Anim1", select="Anim2")

# a knot on a layered prop: Layer on the knot bakes the knot as an object and keeps it
prop, b, lay = scene()
knots.create("knot", [prop], highlight=None)
top = knots.knots()[0]
cmds.setKeyframe(top, attribute="ty", time=20, value=cmds.getAttr(top + ".ty", time=20) + 5)
select_layer(lay)
shown = track(prop, FRAMES + HALVES)
a1 = curves(lay, prop)
line = layerbake.bake([top], highlight=None)
ok, how = same(shown, track(prop, FRAMES + HALVES), FRAMES)    # keyed on every frame
gate(ok and knots.knots() == [top] and knots.constraints_of(prop) and curves(lay, prop) == a1
     and not curves("BaseAnimation", top),
     "Layer on a knot of the layered prop: %s; %s, the knot kept and driving, its base "
     "without a curve" % (line, how))
# ... and Layer on the prop takes the knot off
line = layerbake.bake([prop], highlight=None)
ok, how = same(shown, track(prop, FRAMES + HALVES), FRAMES)
gate(ok and not knots.knots(), "then Layer on the prop: %s; %s, the knot off" % (line, how))

# ------------------------------------------------------------------- O

case("O overlap, attach, snapshot")
cmds.file(new=True, force=True)
cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
cmds.select(clear=True)
j = [cmds.joint(position=(0, i * 5, 0), name="j%d" % i) for i in range(4)]
j = [cmds.ls(n, long=True)[0] for n in j]
for t, v in ((0, 0), (10, 40), (20, -30), (40, 0)):
    cmds.setKeyframe(j[0], attribute="rz", time=t, value=v)
lay = cmds.animLayer("Anim1")
cmds.animLayer(lay, edit=True, attribute=[j[0] + ".rx", j[1] + ".rz"])
for t, v in ((0, 0), (15, 20), (40, 0)):
    cmds.setKeyframe(j[0], attribute="rx", animLayer=lay, time=t, value=v)
    cmds.setKeyframe(j[1], attribute="rz", animLayer=lay, time=t, value=-v)
select_layer(None)
line = overlap.run([j[0]], highlight=None)
gate(bool(overlap.overlap_layers()), "Overlap on a layered chain: " + line)

prop, b, lay = scene()
before = track(prop)
line = knots.snapshot([prop], highlight=None)
snap = knots.snapshots()
ok, how = same(before, track(snap[0]) if snap else {}) if snap else (False, "none")
gate(ok, "Snapshot of the layered prop: %s; %s" % (line, how))
knots.create("knot", [prop], highlight=None)
top = [t for t in knots.knots() if not knots.is_snapshot(t)][0]
line = knots.set_attach(0.0, [top], highlight=(10, 21))
gate("0" in line and cmds.keyframe(top + "." + plan.ATTACH, query=True, keyframeCount=True),
     "Attach 0 on a knot of the layered prop: " + line)

print("\n%d gates, %d failed" % (COUNT[0], len(FAILS)))
for f in FAILS:
    print("FAILED", f)
