"""The layer panel's weight key cell (2026-10-20), mayapy standalone:
a layer's weight keyed and unkeyed at the current frame, read back by the rows,
one undo a press, the weight playing its keys.

    mayapy verify_timebar_layer_weight_key.py
"""
import os
import sys

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SkeldarAnim")
sys.path.insert(0, os.path.abspath(REPO))

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

from maya_timebar import layerscene as S
from maya_timebar import layerlook as L

FAILS = []


def gate(n, ok, text):
    print("%s %2d %s" % ("PASS" if ok else "FAIL", n, text))
    if not ok:
        FAILS.append(n)


cmds.file(new=True, force=True)
cmds.undoInfo(state=True, infinity=True)
cube = cmds.polyCube()[0]
cmds.setKeyframe(cube, attribute="tx", time=0, value=0)
cmds.select(cube)
cmds.animLayer("Lay1", addSelectedObjects=True)
cmds.setKeyframe(cube, attribute="tx", time=0, value=5, animLayer="Lay1")

row = lambda: next(r for r in S.anim_layers() if r["name"] == "Lay1")
gate(1, row()["weight_keys"] == () and L.weight_state(row(), 0) == "plain", "unkeyed: a plain cell")

cmds.currentTime(10)
cmds.setAttr("Lay1.weight", 0.25)
ok, msg = S.toggle_weight_key("Lay1")
gate(2, ok and row()["weight_keys"] == (10.0,), "keyed at 10: %s" % msg)
gate(3, L.weight_state(row(), 10) == "onkey" and L.weight_state(row(), 3) == "keyed", "on the key / off it")

cmds.currentTime(20)
cmds.setAttr("Lay1.weight", 1.0)
S.toggle_weight_key("Lay1")
gate(4, row()["weight_keys"] == (10.0, 20.0), "a second key at 20")
cmds.currentTime(15)
w = cmds.getAttr("Lay1.weight")
gate(5, 0.25 < w < 1.0, "the weight plays its keys (%.3f at 15)" % w)

cmds.currentTime(20)
ok, msg = S.toggle_weight_key("Lay1")
gate(6, row()["weight_keys"] == (10.0,), "a press on the key takes it off: %s" % msg)
cmds.undo()
gate(7, row()["weight_keys"] == (10.0, 20.0), "one undo brings it back")

cmds.currentTime(20)
S.toggle_weight_key("Lay1")
cmds.currentTime(10)
w = cmds.getAttr("Lay1.weight")
S.toggle_weight_key("Lay1")
gate(8, row()["weight_keys"] == () and abs(cmds.getAttr("Lay1.weight") - w) < 1e-9,
     "the last key off: no curve, the weight kept (%.3f)" % cmds.getAttr("Lay1.weight"))

root = S.anim_layers()[-1]["name"]
ok, msg = S.toggle_weight_key(root)
gate(9, not ok and "no weight" in msg, "BaseAnimation refused: %s" % msg)
gate(10, cmds.keyframe("Lay1", q=True, attribute="weight", keyframeCount=True) == 0,
     "nothing of the cube's keys touched; the weight free")

print("%d of 10 gates failed" % len(FAILS))
maya.standalone.uninitialize()
