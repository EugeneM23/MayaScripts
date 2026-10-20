"""The layer's weight keys (the L keys on the lanes) move and delete with the lanes' keys
(2026-10-20: «ключи слоя нельзя передвигать и удалять»). mayapy standalone:

    mayapy verify_timebar_weight_keys_move.py
"""
import sys
sys.path.insert(0, r"C:/!!!Work/MayaScripts/SkeldarAnim")
import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
from maya_timebar import layerscene as S

FAILED = []
N = [0]


def gate(ok, text):
    N[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", N[0], text))
    if not ok:
        FAILED.append(text)


box = cmds.polyCube(name="box")[0]
cmds.select(box)
L1 = cmds.animLayer("AnimLayer1", addSelectedObjects=True)
cmds.setKeyframe(box + ".ty", t=0, v=1, animLayer=L1)
cmds.setKeyframe(box + ".ty", t=30, v=3, animLayer=L1)
cmds.setKeyframe(L1, attribute="weight", time=(10, 10), value=0.2)
cmds.setKeyframe(L1, attribute="weight", time=(20, 20), value=0.9)
cmds.undoInfo(state=True)

# nothing selected: the L keys are still the lane's
cmds.select(clear=True)
gate(S.keys_by_layer([L1]).get(L1) == [10.0, 20.0], "nothing selected: the lane reads its weight keys")
gate(S.lane_live_begin([L1], (10, 10)), "a drag on an L key has a curve to move")
S.lane_live_to((14, 14))
S.lane_live_end((14, 14))
gate(S.weight_keys(L1) == (14.0, 20.0), "the weight key moved 10 -> 14")
gate(abs(cmds.keyframe(S._weight_curve(L1), q=True, time=(14, 14), valueChange=True)[0] - 0.2) < 1e-9,
     "it keeps its value")
cmds.undo()
gate(S.weight_keys(L1) == (10.0, 20.0), "one undo puts it back")

S.lane_move([L1], (20, 20), (25, 25))
gate(S.weight_keys(L1) == (10.0, 25.0), "lane_move moves an L key too")
cmds.undo()

ok, _msg = S.lane_keys("delete", [L1], (20, 20), 0.0)
gate(ok and S.weight_keys(L1) == (10.0,), "Delete on the lane takes the L key off")
cmds.undo()
gate(S.weight_keys(L1) == (10.0, 20.0), "one undo brings it back")

# with the cube selected: its keys and the layer's weight keys move together
cmds.select(box)
gate(S.keys_by_layer([L1]).get(L1) == [0.0, 10.0, 20.0, 30.0], "selected: the cube's and the weight's keys")
S.lane_live_begin([L1], (0, 10))
S.lane_live_to((5, 15))
S.lane_live_end((5, 15))
ty = S.curves_of([L1], weights=False)
gate(S.weight_keys(L1) == (15.0, 20.0), "a block moves the weight key with the cube's")
gate(any(5.0 in (cmds.keyframe(c, q=True, timeChange=True) or []) for c in ty), "and the cube's key")
cmds.undo()

# S over a block keys the cube, never the weight
S.lane_key_range([L1], 2, 4)
gate(S.weight_keys(L1) == (10.0, 20.0), "S over a block leaves the weight curve alone")

print("%d of %d gates failed" % (len(FAILED), N[0]))
