"""verify_floor.py - Tools > Floor, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/verify_floor.py [phases]

Spec: docs/superpowers/specs/2026-11-02-tools-floor-design.md. The shipped assets, a take keyed by hand
(the legs alternating, so each foot really has a stance and a swing), and the press read back by a
measurement of its own - never the tool's own reader.

  float     a Manny skeleton's whole take floated 15 cm: every contact's lowest point on the floor, no
            frame under it, the planted feet not sliding sideways, and one Ctrl+Z putting it all back.
  sunk      the same take 10 cm into the floor: the body raised, the same gates.
  contact   one contact 6 cm into the floor while the others stand on it: the body dips THERE and the
            other foot's stance stays on the floor - the contact-by-contact promise.
  creep     the Creep skeleton, whose root hangs under a -90 X `Armature`: the rise is written in the
            channel that really carries it (its own Z) and the feet still land (trap: a `ty` key there
            would move the body sideways).
  rig       Manny [rig]: the carrier is `Main`, not a bone.
  again     a second press on a take already standing on the floor says so and writes nothing; the
            refusals (a skeleton with no feet, the carrier's channel locked).

Phases can be named on the command line; the default runs all six.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")
PHASES = tuple(a for a in sys.argv[1:] if not a.startswith("-")) or (
    "float", "sunk", "contact", "creep", "rig", "again")

import maya.standalone                                        # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                      # noqa: E402

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))         # the repository's plugin, never the installed copy
import maya_retargetmode                                      # noqa: E402
from maya_tools import floor                                  # noqa: E402
from maya_tools import floorplan as fplan                     # noqa: E402

FAILED, COUNT = [], [0]
FRAMES = list(range(0, 25))


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


# ------------------------------------------------------------------ the scene

def ma_import(path, namespace):
    before = set(cmds.ls(long=True))
    cmds.file(new=True, force=True)
    cmds.loadPlugin("matrixNodes", quiet=True)
    cmds.loadPlugin("quatNodes", quiet=True)
    before = set(cmds.ls(long=True))
    cmds.file(path, i=True, namespace=namespace, preserveReferences=True)
    cmds.playbackOptions(animationStartTime=FRAMES[0], animationEndTime=FRAMES[-1],
                         min=FRAMES[0], max=FRAMES[-1])
    new = [p for p in cmds.ls(long=True) if p not in before]
    joints = [p for p in new if cmds.nodeType(p) == "joint"]
    roots = [p for p in joints if not [a for a in (cmds.listRelatives(p, parent=True,
                                                                     fullPath=True) or [])
                                       if cmds.nodeType(a) == "joint"]]
    return sorted(roots, key=len)[0]


def go(frame):
    """The time set UNRECORDED (`MAnimControl`, what every walk of the plugin uses): a `cmds.currentTime`
    is an undo step of its own in standalone (trap 222) and would bury the press we mean to undo."""
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaAnim as oma
    oma.MAnimControl.setCurrentTime(om.MTime(float(frame), om.MTime.uiUnit()))


def leaf_map(root):
    out = {}
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                         fullPath=True) or [])
    for path in paths:
        out.setdefault(path.split("|")[-1].split(":")[-1], path)
    return out


def feet_and_binds(root):
    feet = floor.feet_of(root)
    binds = {}
    for points in feet.values():
        for point in points:
            binds[point] = maya_retargetmode.rest_world(point)[13]
    return feet, binds


def clearance(feet, binds, frames=FRAMES):
    """{frame: {side: how far that foot stands above the floor}} - our own reader: a real time change
    and `xform -ws` (never the tool's own `read`)."""
    out = {}
    for frame in frames:
        go(frame)
        out[frame] = dict(
            (side, min(cmds.xform(p, query=True, worldSpace=True, translation=True)[1] - binds[p]
                       for p in points))
            for side, points in feet.items())
    return out


def ground(row):
    return min(row.values())


def planted_at(low, side):
    """The frames that foot stands within DOWN_TOL of its own lowest (the tool's own rule, read off
    OUR measurement)."""
    heights = dict((f, low[f][side]) for f in low)
    return fplan.down_frames(heights)


def feet_xz(feet, frames):
    out = {}
    for frame in frames:
        go(frame)
        out[frame] = dict((side, [cmds.xform(points[0], query=True, worldSpace=True,
                                             translation=True)[i] for i in (0, 2)])
                          for side, points in feet.items())
    return out


# ------------------------------------------------------------------ the fixture

def _lifting_swing(by_leaf, side="l", size=25.0):
    """(channel, angle) whose thigh swing RAISES the foot most - measured, never assumed: a UE bone runs
    down its own X, so `rotateX` on a hip is a ROLL and lifts nothing (traps 246, 311), and which of the
    other two flexes it is the skeleton's own business. A stance is the foot's own lowest, so a swing that
    moved the foot by nothing would leave the take with no stance to find."""
    thigh, ball = by_leaf["thigh_" + side], by_leaf["ball_" + side]
    kept = dict((ch, cmds.getAttr(thigh + "." + ch)) for ch in ("rotateX", "rotateY", "rotateZ"))
    rest = cmds.xform(ball, query=True, worldSpace=True, translation=True)[1]
    best, found = 0.0, ("rotateZ", size)
    for ch in ("rotateX", "rotateY", "rotateZ"):
        for angle in (size, -size):
            cmds.setAttr(thigh + "." + ch, kept[ch] + angle)
            rise = cmds.xform(ball, query=True, worldSpace=True, translation=True)[1] - rest
            cmds.setAttr(thigh + "." + ch, kept[ch])
            if rise > best:
                best, found = rise, (ch, kept[ch] + angle)
    return found


def walk_by_hand(root, offset=0.0, dip=None):
    """A crude walk keyed on the skeleton's own bones: the left leg swings over 0..12 and the right over
    12..24, so each foot has a stance (still, at its own lowest) and a swing. `offset` lifts the whole
    take; `dip` (frames, centimetres) sinks the body inside the LEFT foot's stance alone."""
    by_leaf = leaf_map(root)
    for side, window in (("l", (0, 6, 12)), ("r", (12, 18, 24))):
        thigh = by_leaf["thigh_" + side]
        channel, swing = _lifting_swing(by_leaf, side)
        #  the thigh ALONE: a counter-turned calf keeps the ankle level (the classic forward-and-back
        #  pair), and then the take has no swing to tell from its stance
        rest = cmds.getAttr(thigh + "." + channel)
        for frame, angle in ((window[0], rest), (window[1], swing), (window[2], rest)):
            cmds.setKeyframe(thigh, attribute=channel, time=frame, value=angle)
        last = window[2] + 12
        if last <= FRAMES[-1]:
            cmds.setKeyframe(thigh, attribute=channel, time=last, value=rest)
    carrier = floor.carrier_of(root)
    axis = floor._axis(carrier)
    base = dict((ch, cmds.getAttr(carrier + "." + ch))
                for ch in ("translateX", "translateY", "translateZ"))
    for frame in FRAMES:
        height = offset
        if dip and dip[0][0] <= frame <= dip[0][1]:
            height = offset - dip[1]
        for ch, value in zip(("translateX", "translateY", "translateZ"), axis):
            cmds.setKeyframe(carrier, attribute=ch, time=frame, value=base[ch] + height * value)
    return carrier


def layer_of():
    layers = floor.floor_layers()
    return layers[0] if layers else None


def channels_of(layer):
    return sorted(set(p.split(".")[-1] for p in
                      (cmds.animLayer(layer, query=True, attribute=True) or [])))


# -------------------------------------------------------------------- phases

def _press_and_measure(root, name, expect_up):
    feet, binds = feet_and_binds(root)
    before = clearance(feet, binds)
    xz_before = feet_xz(feet, FRAMES)
    message = floor.run(root=root)
    print("        line: %s" % message)
    after = clearance(feet, binds)
    layer = layer_of()
    rows = dict((s, dict((f, before[f][s]) for f in before)) for s in feet)
    aimed = sorted(fplan.wanted(rows, fplan.airborne(rows)))
    worst = max(abs(ground(after[f])) for f in aimed) if aimed else 99.0
    under = min(ground(after[f]) for f in FRAMES)
    moved = max(abs(ground(after[f]) - ground(before[f])) for f in FRAMES)
    xz_after = feet_xz(feet, aimed or FRAMES)
    slid = max(abs(xz_before[f][s][i] - xz_after[f][s][i])
               for f in (aimed or FRAMES) for s in feet for i in (0, 1))
    gate(layer is not None and "Floor" in message,
         "%s: a Floor layer (%s), %d contact frames aimed at" % (name, layer, len(aimed)))
    gate(worst < fplan.KEY_TOL + 1e-6,
         "%s: every frame's lower foot on the floor - worst %.6f cm (the thinning's own %.2f)"
         % (name, worst, fplan.KEY_TOL))
    gate(slid < 1e-9, "%s: the feet did not slide sideways - worst %.2e cm" % (name, slid))
    gate(under > -0.01, "%s: no frame under the floor - lowest %.6f cm" % (name, under))
    gate(moved > expect_up - 1.0 and moved < expect_up + 1.0 if expect_up else True,
         "%s: the body moved %.2f cm (asked about %.1f)" % (name, moved, expect_up))
    return feet, binds, before, after, layer


def phase_float():
    print("\n--- float: a Manny skeleton 15 cm off the floor")
    root = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "chk")
    carrier = walk_by_hand(root, offset=15.0)
    feet, binds, before, after, layer = _press_and_measure(root, "floated", 15.0)
    gate(channels_of(layer) == ["translateY"],
         "the rise is one channel on the root: %s" % channels_of(layer))
    cmds.undo()
    gate(not floor.floor_layers(), "one Ctrl+Z: no Floor layer left")
    back = clearance(feet, binds)
    worst = max(abs(back[f][s] - before[f][s]) for f in FRAMES for s in feet)
    gate(worst < 1e-6, "...and the take is back as it was - worst %.2e cm" % worst)


def phase_sunk():
    print("\n--- sunk: the same take 10 cm into the floor")
    root = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "chk")
    walk_by_hand(root, offset=-10.0)
    _press_and_measure(root, "sunk", 10.0)


def phase_contact():
    print("\n--- contact: one contact 6 cm under, the others on the floor")
    root = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "chk")
    walk_by_hand(root, offset=0.0, dip=((16, 20), 6.0))
    feet, binds = feet_and_binds(root)
    before = clearance(feet, binds)
    message = floor.run(root=root)
    print("        line: %s" % message)
    after = clearance(feet, binds)
    dipped = [f for f in FRAMES if 16 <= f <= 20]
    other = [f for f in FRAMES if f <= 10]
    worst_dip = max(abs(ground(after[f])) for f in dipped)
    gate(worst_dip < 0.01, "the sunk contact stands on the floor - worst %.6f cm" % worst_dip)
    worst_other = max(abs(ground(after[f]) - ground(before[f])) for f in other)
    gate(worst_other < 0.5, "the other foot's stance was not moved with it - worst %.3f cm" % worst_other)
    under = min(ground(after[f]) for f in FRAMES)
    gate(under > -0.01, "no frame under the floor - lowest %.6f cm" % under)


def phase_creep():
    print("\n--- creep: a root under a -90 X Armature")
    root = ma_import(os.path.join(ASSETS, "Creep_Skeleton.ma"), "chk")
    carrier = floor.carrier_of(root)
    parent = (cmds.listRelatives(carrier, parent=True, fullPath=True) or [None])[0]
    axis = floor._axis(carrier)
    gate(parent is not None and abs(axis[1]) < 0.01 and abs(axis[2]) > 0.99,
         "world up is the root's own Z under %s: axis %s" % (
             (parent or "").split("|")[-1], ", ".join("%.3f" % v for v in axis)))
    walk_by_hand(root, offset=12.0)
    feet, binds, before, after, layer = _press_and_measure(root, "the Creep", 12.0)
    gate(channels_of(layer) == ["translateZ"],
         "and the key went in that channel: %s" % channels_of(layer))


def phase_rig():
    print("\n--- rig: the carrier is Main")
    root = ma_import(os.path.join(ASSETS, "Manny_Rig.ma"), "chk")
    carrier = floor.carrier_of(root)
    gate(carrier.split("|")[-1].split(":")[-1] == "Main",
         "the carrier is the rig's Main: %s" % carrier.split("|")[-1])
    feet, binds = feet_and_binds(root)
    for frame in FRAMES:
        cmds.setKeyframe(carrier, attribute="translateY", time=frame, value=9.0)
    before = clearance(feet, binds)
    message = floor.run(root=root)
    print("        line: %s" % message)
    after = clearance(feet, binds)
    rows = dict((s, dict((f, before[f][s]) for f in before)) for s in feet)
    aimed = sorted(fplan.wanted(rows, fplan.airborne(rows)))
    worst = max(abs(ground(after[f])) for f in aimed)
    gate(worst < 0.01, "the rig's feet on the floor - worst %.6f cm" % worst)
    layer = layer_of()
    plugs = cmds.animLayer(layer, query=True, attribute=True) or []
    gate(len(plugs) == 1 and plugs[0].split(".")[0].split(":")[-1] == "Main",
         "the layer holds Main alone: %s" % plugs)


def phase_again():
    print("\n--- again: a second press, and the refusals")
    root = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "chk")
    carrier = walk_by_hand(root, offset=15.0)
    floor.run(root=root)
    first = layer_of()
    message = floor.run(root=root)
    print("        line: %s" % message)
    gate("already on the floor" in message and "nothing changed" in message,
         "the second press says there is nothing to do")
    gate(layer_of() == first and len(floor.floor_layers()) == 1,
         "...and wrote no second layer")
    #  the same layer rewritten in place, its weight and its mute kept - and the weight read, so
    #  the feet still land (the press reads the feet as they show)
    cmds.setAttr(first + ".weight", 0.5)
    carrier2 = floor.carrier_of(root)
    for frame in FRAMES:                                        # 5 cm more float, on the base
        #  `cmds.keyframe(q=True)` answers TIMES unless asked for valueChange: read the plug
        cmds.setKeyframe(carrier2, attribute="translateY", time=frame,
                         value=cmds.getAttr(carrier2 + ".translateY", time=frame) + 5.0)
    feet, binds = feet_and_binds(root)
    before = clearance(feet, binds)
    message = floor.run(root=root)
    print("        line: %s" % message)
    after = clearance(feet, binds)
    rows = dict((s2, dict((f, before[f][s2]) for f in before)) for s2 in feet)
    aimed = sorted(fplan.wanted(rows, fplan.airborne(rows)))
    worst = max(abs(ground(after[f])) for f in aimed)
    gate(layer_of() == first and len(floor.floor_layers()) == 1 and
         abs(cmds.getAttr(first + ".weight") - 0.5) < 1e-6,
         "the standing layer is rewritten in place, its weight kept (%.2f)"
         % cmds.getAttr(first + ".weight"))
    gate(worst < fplan.KEY_TOL + 1e-6,
         "...and the feet land all the same at weight 0.5 - worst %.6f cm" % worst)
    gate("weight 0.50" in message, "the line names the weight it wrote through")
    cmds.setAttr(first + ".weight", 1.0)
    #  a MUTED standing layer shows nothing, so the press must write the whole correction into it
    cmds.setAttr(first + ".mute", True)
    for frame in FRAMES:
        cmds.setKeyframe(carrier2, attribute="translateY", time=frame,
                         value=cmds.getAttr(carrier2 + ".translateY", time=frame) + 3.0)
    message = floor.run(root=root)
    print("        line: %s" % message)
    gate("muted" in message, "the line says the layer is muted")
    cmds.setAttr(first + ".mute", False)
    feet, binds = feet_and_binds(root)
    after = clearance(feet, binds)
    rows = dict((s2, dict((f, after[f][s2]) for f in after)) for s2 in feet)
    worst = max(abs(ground(after[f])) for f in sorted(fplan.wanted(rows, fplan.airborne(rows))))
    gate(worst < fplan.KEY_TOL + 1e-6,
         "...and unmuted the feet stand on the floor - worst %.6f cm" % worst)
    #  a locked channel
    cmds.setAttr(carrier + ".translateY", lock=True)
    message = floor.run(root=root)
    cmds.setAttr(carrier + ".translateY", lock=False)
    print("        line: %s" % message)
    gate("locked" in message, "a locked channel is refused by name")
    #  a skeleton that is no walker
    cmds.file(new=True, force=True)
    chain = cmds.joint(name="stump", position=(0, 0, 0))
    cmds.joint(name="stump_tip", position=(0, 10, 0))
    message = floor.run(root=cmds.ls(chain, long=True)[0])
    print("        line: %s" % message)
    gate("foot_l" in message, "a skeleton with no feet is refused by name")


def main():
    for name in PHASES:
        fn = globals().get("phase_" + name)
        if fn is None:
            print("no phase %s" % name)
            continue
        fn()
    print("\n%d of %d gates failed%s" % (len(FAILED), COUNT[0],
                                         (": " + ", ".join(map(str, FAILED))) if FAILED else ""))


if __name__ == "__main__":
    main()
