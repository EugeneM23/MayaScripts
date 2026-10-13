"""Standalone gates for the Tools card's Layer: what drives an object baked onto a new additive
layer (2026-10-13).

    mayapy verify_bake_layer.py

mayapy STANDALONE, a fresh scene per case (spec
docs/superpowers/specs/2026-10-13-tools-bake-to-layer-design.md). The prop is verify_knots' (a cube
under an animated carrier, rotate pivot off its origin, zxy, keyed tx / rx / ry, static ty / rz,
frames 0..40, the current frame 12).

L0 a plainly keyed object (the animator's report, 2026-10-13): its keys move onto the layer, the
   base holds frame 0's pose, the prop shows what it showed, muted it stands; a second press is
   refused (its animation is on layers already); with a highlight the base bridges it and keeps
   its keys outside.
L1 a knot edited, Layer on the knot: the prop shows exactly what the knot showed, the base holds
   the pose of frame 0, the knot and Maya's pairBlend gone, the layer marked; muted the prop
   stands in that pose, its weight blends.
L2 a ranged knot (attach 0/1/1/0), Layer over the whole take: as shown, the original outside its
   span; a whole-take knot with a highlight: only inside the highlight, zero one frame outside,
   the base bridged.
L3 the animator's parentConstraint to a moving target: baked and deleted, the base frame 0's pose;
   an unkeyed object the same; an orientConstraint spinning two turns keyed without a jump.
L4 a double knot riding a knot: both off, the motion kept.
L5 refusals change nothing: nothing selected, nothing animating, an expression, a weapon link, a
   Connections link, a weapon space, the Retarget's holder, a refused object beside a good one.
L6 one undo puts the knot and the base keys back and takes the layer away.
L7 a Manny rig: a game bone refused (the rig's own); a knot on a control and the animator's
   constraint on another baked onto a layer, the game bones showing what they showed.
L8 the Overlap still writes its layer through the shared writer.
L9 an object under the animator's own layer: only the base's motion moves, their layer untouched.
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

from maya_tools import knotplan as plan, knots, layerbake, overlap, overlapplan  # noqa: E402

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


def _source(plug):
    found = cmds.listConnections(plug, source=True, destination=False, plugs=True,
                                 skipConversionNodes=True) or []
    return found[0] if found else None


def base(node, channels=plan.CHANNELS):
    """What the base gives each channel - through a layer's blend node to its input A (trap
    235): a curve's keys, a value, or what else drives it."""
    out = {}
    for ch in channels:
        plug = node + "." + ch
        src = _source(plug)
        if src and cmds.nodeType(src.split(".")[0]).startswith("animBlendNode"):
            blend, attr = src.split(".", 1)
            plug = "%s.inputA%s" % (blend, attr[len("output"):])
            src = _source(plug)
        if src and cmds.nodeType(src.split(".")[0]).startswith("animCurve"):
            curve = src.split(".")[0]
            out[ch] = (tuple(cmds.keyframe(curve, query=True, timeChange=True)),
                       tuple(round(v, 6) for v in cmds.keyframe(curve, query=True,
                                                                valueChange=True)))
        elif src:
            out[ch] = ("driven by", cmds.nodeType(src.split(".")[0]))
        else:
            out[ch] = round(cmds.getAttr(plug), 6)
    return out


def nudge(node, ch, delta):
    plug = node + "." + ch
    if cmds.keyframe(plug, query=True, keyframeCount=True):
        cmds.keyframe(plug, edit=True, relative=True, valueChange=delta)
    else:
        cmds.setAttr(plug, cmds.getAttr(plug) + delta)


def layers():
    return layerbake.bake_layers()


def channels(node, frames=FRAMES):
    """{frame: (tx, ty, tz, rx, ry, rz)} - the node's local values after a real time change."""
    out = {}
    now = cmds.currentTime(query=True)
    for f in frames:
        cmds.currentTime(f, update=True)
        out[f] = tuple(cmds.getAttr(node + ".translate")[0]) + tuple(
            cmds.getAttr(node + ".rotate")[0])
    cmds.currentTime(now, update=True)
    return out


def still_at(node, pose, frames=FRAMES):
    """The worst gap between the node's channels on `frames` and the one `pose`."""
    got = channels(node, frames)
    return max(abs(got[f][i] - pose[i]) for f in frames for i in range(6))


def static_base(node, pose):
    """True when every channel's base is a plain value equal to `pose`'s."""
    got = base(node)
    return all(not isinstance(got[ch], tuple) and abs(got[ch] - pose[i]) < 1e-3
               for i, ch in enumerate(plan.CHANNELS)), got


def layer_curve(layer, node, ch):
    found = cmds.animLayer(layer, query=True, findCurveForPlug="%s.%s" % (node, plan.LONG[ch]))
    return found[0] if found else None


def snapshot(nodes):
    return (sorted(cmds.ls(long=True)), dict((n, base(n)) for n in nodes),
            sorted(cmds.ls(type="animLayer") or []))


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


def knot_of(obj):
    found = [k for k in knots.knots() if knots.source_of(k) == obj]
    return found[0] if found else None


def leftovers():
    return {"knots": knots.knots(), "pairBlends": cmds.ls(type="pairBlend") or [],
            "constraints": cmds.ls(type="constraint") or []}


def clean():
    left = leftovers()
    return not any(left.values()), str(dict((k, v) for k, v in left.items() if v))


def mover(name="mover"):
    """A locator travelling and turning over the take."""
    loc = cmds.spaceLocator(name=name)[0]
    loc = cmds.ls(loc, long=True)[0]
    for t, tx, tz, ry in ((0, -10.0, 0.0, 0.0), (20, 5.0, 8.0, 60.0), (40, 12.0, -4.0, 20.0)):
        cmds.setKeyframe(loc, attribute="tx", time=t, value=tx)
        cmds.setKeyframe(loc, attribute="tz", time=t, value=tz)
        cmds.setKeyframe(loc, attribute="ry", time=t, value=ry)
    return loc


# --------------------------------------------------------------------- cases

def case_l0():
    case("L0 plain keys")
    prop = make_prop()
    original, first = track(prop), channels(prop, [0])[0]
    line = layerbake.bake([prop], highlight=None)
    found = layers()
    gate(len(found) == 1 and "its keys moved onto it" in line
         and "the base holds the pose of frame 0" in line, line)
    ok, text = same(original, track(prop))
    gate(ok, "the prop shows what it showed: " + text)
    ok, got = static_base(prop, first)
    gate(ok, "the base holds frame 0's pose, no curve left: %s" % (got,))
    curve = layer_curve(found[0], prop, "tx")
    values = cmds.keyframe(curve, query=True, valueChange=True)
    gate(abs(values[0]) < 1e-9 and len(values) == 41, "the layer starts at 0, a key a frame: %d"
         % len(values))
    cmds.animLayer(found[0], edit=True, mute=True)
    gap = still_at(prop, first)
    gate(gap < 1e-6, "muted: the prop stands in frame 0's pose: %.2e" % gap)
    cmds.animLayer(found[0], edit=True, mute=False)
    before = snapshot([prop])
    line = layerbake.bake([prop], highlight=None)
    gate("on layers already" in line and snapshot([prop]) == before, "a second press: " + line)

    prop = make_prop()
    original = track(prop)
    line = layerbake.bake([prop], highlight=(10, 21))
    after = track(prop)
    ok, text = same(original, after)
    gate(ok and "outside the highlight" in line, "a highlight 10-20: as shown everywhere: "
         + text + " - " + line)
    times = base(prop, ("tx",))["tx"][0]
    gate(9.0 in times and 21.0 in times and not plan.bridged(list(times), 10.0, 20.0),
         "the base bridges it on keys at 9 and 21: %s" % (times,))


def case_l1():
    case("L1 knot")
    prop = make_prop()
    original = track(prop)
    knots.create("knot", [prop], highlight=None)
    top = knot_of(prop)
    nudge(top, "tx", 6.0)
    nudge(top, "ry", 25.0)
    shown, first = track(prop), channels(prop, [0])[0]
    gate(diff(original, shown)[0] > 1.0, "the knot edit moves the prop: %.3f cm"
         % diff(original, shown)[0])
    line = layerbake.bake([top], highlight=None)
    found = layers()
    gate(len(found) == 1 and found[0].startswith("Baked_prop"), "one layer, ours: %s - %s"
         % (found, line))
    ok, text = same(shown, track(prop))
    gate(ok, "the prop shows what the knot showed: " + text)
    ok, got = static_base(prop, first)
    gate(ok, "the base holds frame 0's pose: %s" % (got,))
    ok, text = clean()
    gate(ok, "the knot and Maya's pairBlend gone " + text)
    gate("its keys and 1 knot moved onto it" in line and "Baked_prop" in line
         and "over 0-40" in line, line)
    layer = found[0]
    gate(cmds.getAttr(layer + "." + plan.LAYER_MARKER) == "prop", "marked with the prop")
    gate(cmds.getAttr(layer + ".rotationAccumulationMode") == 0, "rotation by component")
    full = channels(prop)
    cmds.animLayer(layer, edit=True, mute=True)
    gap = still_at(prop, first)
    gate(gap < 1e-6, "muted: the prop stands in frame 0's pose: %.2e" % gap)
    cmds.animLayer(layer, edit=True, mute=False, weight=0.5)
    half = channels(prop)
    gap = max(abs(half[f][i] - (first[i] + full[f][i]) * 0.5) for f in FRAMES for i in range(6))
    gate(gap < 1e-4, "weight 0.5: every channel half way: %.2e" % gap)
    gate(cmds.ls(selection=True, long=True) == [prop], "the prop is selected")


def case_l2():
    case("L2 ranged")
    prop = make_prop()
    original = track(prop)
    knots.create("knot", [prop], highlight=(10, 21))
    top = knot_of(prop)
    nudge(top, "tz", 7.0)
    shown = track(prop)
    line = layerbake.bake([prop], highlight=None)
    ok, text = same(shown, track(prop))
    gate(ok, "a ranged knot over the whole take: as shown: " + text)
    outside = [f for f in FRAMES if f < 9 or f > 21]
    ok, text = same(original, track(prop), outside)
    gate(ok, "outside its span the original: " + text)

    prop = make_prop()
    original = track(prop)
    knots.create("knot", [prop], highlight=None)
    top = knot_of(prop)
    nudge(top, "tz", 7.0)
    shown = track(prop)
    line = layerbake.bake([top], highlight=(10, 21))
    after = track(prop)
    ok, text = same(shown, after, list(range(10, 21)))
    gate(ok, "a highlight 10-20: as shown inside: " + text)
    outside = [f for f in FRAMES if f < 9 or f > 21]
    ok, text = same(original, after, outside)
    gate(ok, "outside it the original: " + text)
    layer = layers()[0]
    curve = layer_curve(layer, prop, "tz")
    times = cmds.keyframe(curve, query=True, timeChange=True)
    values = cmds.keyframe(curve, query=True, valueChange=True)
    gate(times[0] == 9.0 and times[-1] == 21.0 and abs(values[0]) < 1e-9
         and abs(values[-1]) < 1e-9, "the layer zero at 9 and 21: %s..%s" % (times[0], times[-1]))
    gate("highlight" in line, line)
    keyed = base(prop, ("tx",))["tx"][0]
    gate(not plan.bridged(list(keyed), 10.0, 20.0), "the base bridged: %s" % (keyed,))


def case_l3():
    case("L3 constraints")
    prop = make_prop()
    original = track(prop)
    loc = mover()
    cmds.parentConstraint(loc, prop, maintainOffset=True)
    shown, first = track(prop), channels(prop, [0])[0]
    gate(diff(original, shown)[0] > 1.0, "the constraint moves the prop")
    line = layerbake.bake([prop], highlight=None)
    ok, text = same(shown, track(prop))
    gate(ok, "baked onto the layer: " + text)
    ok, got = static_base(prop, first)
    gate(ok, "the base holds frame 0's pose, its keys moved too: %s" % (got,))
    ok, text = clean()
    gate(ok, "the constraint and its pairBlend deleted " + text)
    gate("1 constraint" in line, line)

    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    loc = mover()
    bare = cmds.ls(cmds.polyCube(name="bare")[0], long=True)[0]
    cmds.pointConstraint(loc, bare)
    cmds.currentTime(12)
    shown, first = track(bare), channels(bare, [0])[0]
    line = layerbake.bake([bare], highlight=None)
    ok, text = same(shown, track(bare))
    gate(ok, "an unkeyed object baked: " + text)
    ok, got = static_base(bare, first)
    gate(ok and "the base holds the pose of frame 0" in line,
         "its base frame 0's pose: %s - %s" % (got, line))

    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    spinner = cmds.ls(cmds.spaceLocator(name="spinner")[0], long=True)[0]
    cmds.setKeyframe(spinner, attribute="ry", time=0, value=0.0)
    cmds.setKeyframe(spinner, attribute="ry", time=40, value=720.0)
    cmds.keyTangent(spinner, attribute="ry", inTangentType="linear", outTangentType="linear")
    spun = cmds.ls(cmds.polyCube(name="spun")[0], long=True)[0]
    cmds.orientConstraint(spinner, spun)
    shown = track(spun)
    layerbake.bake([spun], highlight=None)
    ok, text = same(shown, track(spun))
    gate(ok, "two turns baked: " + text)
    curve = layer_curve(layers()[0], spun, "ry")
    values = cmds.keyframe(curve, query=True, valueChange=True)
    step = max(abs(b - a) for a, b in zip(values, values[1:]))
    gate(step < 20.0 and abs(abs(values[-1] - values[0]) - 720.0) < 1e-3,
         "the turn keyed without a jump: largest step %.3f deg, %.3f in all"
         % (step, values[-1] - values[0]))


def case_l4():
    case("L4 double on a knot")
    prop = make_prop()
    own = base(prop)
    knots.create("knot", [prop], highlight=None)
    top = knot_of(prop)
    nudge(top, "ty", 3.0)
    knots.create("double_local", [top], highlight=None)
    outer = [k for k in knots.knots() if knots.source_of(k) == top][0]
    inner = [c for c in cmds.listRelatives(outer, children=True, type="transform",
                                           fullPath=True) or []
             if knots._has(c, plan.INNER_MARKER)][0]
    nudge(inner, "rx", 30.0)
    shown, first = track(prop), channels(prop, [0])[0]
    line = layerbake.bake([prop], highlight=None)
    ok, text = same(shown, track(prop))
    gate(ok, "both knots baked onto the layer: " + text)
    ok, text = clean()
    still, got = static_base(prop, first)
    gate(ok and still, "both knots gone, the base frame 0's pose " + text)
    gate("2 knots" in line, line)


def case_l5():
    case("L5 refusals")
    prop = make_prop()
    cmds.select(clear=True)
    gate(layerbake.bake(highlight=None) == plan.LAYER_NOTHING, "nothing selected")
    still = cmds.ls(cmds.polyCube(name="still")[0], long=True)[0]
    before = snapshot([still])
    line = layerbake.bake([still], highlight=None)
    gate("nothing animates still" in line and snapshot([still]) == before, line)

    expr = cmds.ls(cmds.polyCube(name="expr")[0], long=True)[0]
    cmds.expression(string="expr.tx = frame * 0.5;", object=expr)
    before = snapshot([expr])
    line = layerbake.bake([expr], highlight=None)
    gate("an expression" in line and snapshot([expr]) == before, line)

    sword = cmds.ls(cmds.polyCube(name="sword")[0], long=True)[0]
    cmds.addAttr(sword, longName="mayaWeapon", dataType="string")
    cmds.setKeyframe(sword, attribute="tx", time=0, value=0.0)
    cmds.setKeyframe(sword, attribute="tx", time=40, value=9.0)
    cmds.select(clear=True)
    bone = cmds.ls(cmds.joint(name="weapon_r"), long=True)[0]
    cmds.parentConstraint(sword, bone, maintainOffset=True)
    before = snapshot([bone])
    line = layerbake.bake([bone], highlight=None)
    gate("driven by the plugin" in line and snapshot([bone]) == before, "a weapon link: " + line)

    cup = cmds.ls(cmds.polyCube(name="cup")[0], long=True)[0]
    cmds.parentConstraint(sword, cup, maintainOffset=True)
    shown = track(cup)
    line = layerbake.bake([cup], highlight=None)
    ok, text = same(shown, track(cup))
    gate(ok and "baked onto" in line, "a prop constrained to the sword is the animator's: "
         + text)

    loc = mover("proxy")
    rider = cmds.ls(cmds.polyCube(name="rider")[0], long=True)[0]
    con = cmds.parentConstraint(loc, rider)[0]
    cmds.addAttr(con, longName="skeldarHandLink", dataType="string")
    before = snapshot([rider])
    line = layerbake.bake([rider], highlight=None)
    gate("driven by the plugin" in line and snapshot([rider]) == before,
         "a Connections link: " + line)

    space = cmds.createNode("transform", name="hand_r_weaponSpace")
    cmds.addAttr(space, longName="mayaWeaponSpace", dataType="string")
    cmds.parentConstraint(bone, space)
    before = snapshot([space])
    line = layerbake.bake([space], highlight=None)
    gate("driven by the plugin" in line and snapshot([space]) == before, "a weapon space: " + line)

    held = cmds.ls(cmds.polyCube(name="held")[0], long=True)[0]
    con = cmds.orientConstraint(loc, held)[0]
    holder = cmds.createNode("transform", name="MoCapConstraints")
    cmds.addAttr(holder, longName="disableConstraints", attributeType="short")
    cmds.connectAttr(holder + ".disableConstraints", con + ".nodeState")
    before = snapshot([held])
    line = layerbake.bake([held], highlight=None)
    gate("Retarget" in line and snapshot([held]) == before, "the Retarget's holder: " + line)

    good = cmds.ls(cmds.polyCube(name="good")[0], long=True)[0]
    cmds.pointConstraint(loc, good)
    before = snapshot([good, held])
    line = layerbake.bake([good, held], highlight=None)
    gate("Retarget" in line and snapshot([good, held]) == before,
         "a refused object beside a good one: nothing changes")


def case_l6():
    case("L6 undo")
    prop = make_prop()
    knots.create("knot", [prop], highlight=None)
    top = knot_of(prop)
    nudge(top, "tx", 4.0)
    shown, own = track(prop), base(prop)
    layerbake.bake([top], highlight=None)
    cmds.undo()
    gate(knot_of(prop) is not None and not layers() and base(prop) == own,
         "one undo: the knot and the base keys back, no layer")
    ok, text = same(shown, track(prop))
    gate(ok, "and the prop as the knot shows it: " + text)


def case_l7():
    case("L7 rig")
    from maya_scenesetup import catalog, character
    import maya_rigs
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    character.add_character(catalog.default_rig())
    rig = maya_rigs.rigs()[0]

    def bone(leaf):
        return [j for j in cmds.ls(type="joint", long=True)
                if j.split("|")[-1].split(":")[-1] == leaf
                and maya_rigs.under(j, rig.skeleton_root)][0]

    hand = bone("hand_r")
    before = snapshot([hand])
    line = layerbake.bake([hand], highlight=None)
    gate("driven by its rig" in line and snapshot([hand]) == before, "a game bone: " + line)

    head_ctrl = cmds.ls(maya_rigs.node(rig, "FKHead_M"), long=True)[0]
    arm_ctrl = cmds.ls(maya_rigs.node(rig, "FKShoulder_R"), long=True)[0]
    for t, rz in ((0, 0.0), (20, 15.0), (40, -10.0)):
        cmds.setKeyframe(head_ctrl, attribute="rz", time=t, value=rz)
    cmds.currentTime(12)
    knots.create("knot", [head_ctrl], highlight=None)
    nudge(knot_of(head_ctrl), "ry", 20.0)
    loc = mover("armTarget")
    cmds.orientConstraint(loc, arm_ctrl, maintainOffset=True)
    head, forearm = bone("head"), bone("lowerarm_r")
    shown_head, shown_arm = track(head), track(forearm)
    line = layerbake.bake([head_ctrl, arm_ctrl], highlight=None)
    ok, text = same(shown_head, track(head))
    gate(ok, "the head bone as the knot showed it: " + text)
    ok, text = same(shown_arm, track(forearm))
    gate(ok, "the forearm as the constraint showed it: " + text)
    gate("2 objects" in line and "their keys, 1 knot and 1 constraint" in line, line)


def case_l8():
    case("L8 overlap")
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=48, animationStartTime=0, animationEndTime=48)
    cmds.select(clear=True)
    joints = [cmds.joint(name="j%d" % i, position=(10.0 * i, 0.0, 0.0)) for i in range(5)]
    joints = cmds.ls(joints, long=True)
    for t in range(49):
        cmds.setKeyframe(joints[0], attribute="rz", time=t,
                         value=40.0 * math.sin(2.0 * math.pi * t / 48.0))
    own = base(joints[0], ("rz",))
    line = overlap.run([joints[0]], overlapplan.DEFAULTS, highlight=None)
    found = overlap.overlap_layers()
    gate(len(found) == 1 and cmds.getAttr(found[0] + "." + overlap.LAYER_MARKER) == "j0",
         "the Overlap layer, marked: " + line)
    gate(base(joints[0], ("rz",)) == own and not layers(),
         "the base untouched, not a Layer layer")


def case_l9():
    case("L9 under another layer")
    prop = make_prop()
    other = cmds.animLayer("Mine")
    cmds.animLayer(other, edit=True, attribute=[prop + ".translateX", prop + ".rotateY"])
    for t, v in ((0, 0.0), (20, 4.0), (40, 0.0)):
        cmds.setKeyframe(prop, attribute="translateX", animLayer=other, time=t, value=v)
    mine = layer_curve(other, prop, "tx")
    keys = (cmds.keyframe(mine, query=True, timeChange=True),
            cmds.keyframe(mine, query=True, valueChange=True))
    shown, first = track(prop), channels(prop, [0])[0]
    line = layerbake.bake([prop], highlight=None)
    ok, text = same(shown, track(prop))
    gate(ok and "its keys moved onto it" in line, "baked over the animator's layer: " + text)
    gate((cmds.keyframe(mine, query=True, timeChange=True),
          cmds.keyframe(mine, query=True, valueChange=True)) == keys,
         "the animator's layer untouched")
    cmds.animLayer(layers()[0], edit=True, mute=True)
    cmds.animLayer(other, edit=True, mute=True)
    gap = still_at(prop, first)
    gate(gap < 1e-6, "both muted: the base holds frame 0's pose: %.2e" % gap)


def main():
    for run in (case_l0, case_l9, case_l1, case_l2, case_l3, case_l4, case_l5, case_l6, case_l7, case_l8):
        try:
            run()
        except Exception:
            import traceback
            traceback.print_exc()
            gate(False, "%s raised" % run.__name__)
    print("verify_bake_layer: %d gates, %d failed%s" % (
        COUNT[0], len(FAILS), (" - " + ", ".join("%s#%d" % (c, n) for c, n, _ in FAILS))
        if FAILS else ""))


main()
