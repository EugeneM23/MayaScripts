"""Connections: a hand on an animation layer released from the weapon, standalone (2026-10-21).

    mayapy verify_connections_layered_release.py

Found live in AS_Dagger_Attack_Cbm_L_R_1p_Full_with3p_1: Hand_R from Weapon to Free broke the
animation - IKArm_R rides the additive layer `_3P_Upper_Body`, and `bakeResults` landed in the
layers' blend node: the control came off the dagger 33 cm away on every frame, the hand turned up
to 300 degrees. A layered rider is now read on every frame while it still rides, freed, and keyed
onto the active layer as final values (`layered.key_shown`, as Tools' re-parent does).

No rig needed - the real `attach_to_proxy` / `detach_from_proxy` on a cube:
- the cube has base keys and an additive layer `Upper` on all six channels, and rides a proxy
  inside a moving, turning `dagger`;
- the old path (`bakeResults`) is off - the gates below catch the bug;
- the release keeps the world track exact on every frame, keys `Upper`, leaves the base curves,
  removes the proxy, our constraint and the pairBlend, and shows the cube again;
- a locked or quaternion active layer is refused before anything moves;
- one undo puts the hand back on the proxy.
"""

import math
import os
import sys

import maya.standalone
maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

from maya_scenesetup import connections  # noqa: E402
from maya_tools import layered  # noqa: E402

FAILS = []
COUNT = [0]
FRAMES = list(range(0, 21))
SIX = ("tx", "ty", "tz", "rx", "ry", "rz")


def gate(ok, msg):
    COUNT[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    if not ok:
        FAILS.append(msg)


def track(node):
    """The world matrix on every frame, walked: `getAttr(time=)` read a layer keyed a moment
    before 33 cm off what the frame shows (measured), so the gates go by what is shown. Off
    the undo queue, or the gates' `cmds.undo()` would take back a time change."""
    out = []
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        for f in FRAMES:
            cmds.currentTime(f, update=True)
            out.append(om.MMatrix(cmds.xform(node, query=True, worldSpace=True, matrix=True)))
    finally:
        cmds.undoInfo(stateWithoutFlush=True)
    return out


def apart(a, b):
    """(worst position cm, worst rotation degrees) between two tracks."""
    worst_d, worst_r = 0.0, 0.0
    for x, y in zip(a, b):
        worst_d = max(worst_d, max(abs(x[12 + i] - y[12 + i]) for i in range(3)))
        q = om.MTransformationMatrix(x).rotation(asQuaternion=True)
        r = om.MTransformationMatrix(y).rotation(asQuaternion=True)
        dot = min(1.0, abs(q.x * r.x + q.y * r.y + q.z * r.z + q.w * r.w))
        worst_r = max(worst_r, math.degrees(2 * math.acos(dot)))
    return worst_d, worst_r


def layer_curve(layer, plug):
    return (cmds.animLayer(layer, query=True, findCurveForPlug=plug) or [None])[0]


cmds.file(new=True, force=True)
cmds.undoInfo(state=True, infinity=True)
cmds.playbackOptions(min=FRAMES[0], max=FRAMES[-1])

hand = cmds.ls(cmds.polyCube(name="hand")[0], long=True)[0]
for ch, keys in (("tx", ((0, 0), (10, 30), (20, 10))), ("ty", ((0, 100), (20, 110))),
                 ("tz", ((0, 5), (20, -5))), ("rx", ((0, 0), (20, 10))),
                 ("ry", ((0, 0), (10, 40), (20, 0))), ("rz", ((0, 0), (20, 45)))):
    for t, v in keys:
        cmds.setKeyframe(hand, attribute=ch, time=t, value=v)

upper = cmds.animLayer("Upper")
cmds.setAttr(upper + ".rotationAccumulationMode", 0)
cmds.animLayer(upper, edit=True, attribute=[hand + "." + ch for ch in SIX])
for ch, keys in (("ty", ((0, 33), (20, 33))), ("rx", ((0, 0), (10, 60), (20, 20))),
                 ("tz", ((0, 0), (20, 12)))):
    cmds.setKeyframe(hand, attribute=ch, animLayer=upper, time=0, identity=True)
    curve = layer_curve(upper, hand + "." + ch)
    for t, v in keys:
        cmds.setKeyframe(curve, time=t, value=v)

dagger = cmds.ls(cmds.createNode("transform", name="dagger"), long=True)[0]
for ch, keys in (("tx", ((0, 0), (20, 50))), ("ty", ((0, 120), (20, 120))),
                 ("ry", ((0, 0), (20, 90)))):
    for t, v in keys:
        cmds.setKeyframe(dagger, attribute=ch, time=t, value=v)

base = cmds.animLayer(query=True, root=True)
base_curves = dict((ch, layer_curve(base, hand + "." + ch)) for ch in SIX)
base_values = dict((ch, cmds.keyframe(c, query=True, valueChange=True))
                   for ch, c in base_curves.items() if c)
gate(layered.is_layered(hand), "the cube is on an animation layer")

before = track(hand)
connections.attach_to_proxy(hand, dagger, (FRAMES[0], FRAMES[-1]), "handProxy_V", "verify:R")
riding = track(hand)
d, r = apart(riding, before)
gate(d < 1e-3 and r < 1e-3, "riding the proxy keeps the track (%.6f cm, %.6f deg)" % (d, r))
gate(bool(connections.our_constraints(hand)), "the cube rides our constraint")

for node in cmds.ls(type="animLayer"):
    cmds.animLayer(node, edit=True, selected=(node == upper))
gate(connections.release_refusal(hand) == "", "Upper takes the release")

cmds.animLayer(upper, edit=True, lock=True)
text = connections.release_refusal(hand)
gate("locked" in text, "a locked active layer is refused: %s" % text)
cmds.animLayer(upper, edit=True, lock=False)
cmds.setAttr(upper + ".rotationAccumulationMode", 1)
text = connections.release_refusal(hand)
gate("quaternion" in text, "a quaternion active layer is refused: %s" % text)
cmds.setAttr(upper + ".rotationAccumulationMode", 0)

#  the old path, to show the gates catch the bug: bakeResults through the blend node
real = connections.layered.is_layered
connections.layered.is_layered = lambda obj, *a: False
cmds.undoInfo(openChunk=True, chunkName="verify: old release")
try:
    connections.detach_from_proxy(hand, (FRAMES[0], FRAMES[-1]))
finally:
    cmds.undoInfo(closeChunk=True)
    connections.layered.is_layered = real
d, r = apart(track(hand), riding)
gate(d > 1.0 or r > 1.0, "the old bakeResults release is off (%.3f cm, %.3f deg)" % (d, r))
cmds.undo()
d, r = apart(track(hand), riding)
gate(d < 1e-3 and r < 1e-3 and bool(connections.our_constraints(hand)),
     "undo puts the hand back on the proxy")

cmds.undoInfo(openChunk=True, chunkName="verify: release")
try:
    removed = connections.detach_from_proxy(hand, (FRAMES[0], FRAMES[-1]))
finally:
    cmds.undoInfo(closeChunk=True)
d, r = apart(track(hand), riding)
gate(d < 1e-3 and r < 1e-3, "the release keeps the track on every frame (%.6f cm, %.6f deg)" % (d, r))
gate(removed == 1 and not cmds.ls("*handProxy_V*"), "the proxy is gone")
gate(not connections.our_constraints(hand), "our constraint is gone")
gate(not cmds.ls(cmds.listConnections(hand, source=True, destination=False) or [], type="pairBlend"),
     "no pairBlend left on the cube")
gate(cmds.getAttr(hand + ".visibility"), "the cube is shown again")
gate(all(cmds.keyframe(base_curves[ch], query=True, valueChange=True) == values
         for ch, values in base_values.items()), "the base curves are untouched")
keyed = [ch for ch in SIX if layer_curve(upper, hand + "." + ch)
         and len(cmds.keyframe(layer_curve(upper, hand + "." + ch), query=True,
                               timeChange=True) or []) == len(FRAMES)]
gate(keyed == list(SIX), "Upper holds the release on every frame: %s" % ", ".join(keyed))

cmds.undo()
d, r = apart(track(hand), riding)
gate(d < 1e-3 and r < 1e-3 and bool(connections.our_constraints(hand)),
     "one undo takes the release back")

print("%d of %d gates failed" % (len(FAILS), COUNT[0]))
maya.standalone.uninitialize()
sys.exit(1 if FAILS else 0)
