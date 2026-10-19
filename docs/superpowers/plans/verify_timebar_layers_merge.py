"""verify_timebar_layers_merge.py - Merge selected and the lanes' key ops, mayapy standalone
(2026-10-19). Spec: docs/superpowers/specs/2026-10-19-time-bar-layers-merge-lanes-design.md"""
import sys
import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds
import maya.mel as mel
sys.path.insert(0, r"C:/!!!Work/MayaScripts/SkeldarAnim")
from maya_timebar import layerscene as S

FAIL = []
N = [0]


def gate(ok, text):
    N[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", N[0], text))
    if not ok:
        FAIL.append(N[0])


def values(plug, frames=range(0, 31, 3)):
    out = []
    for t in frames:
        cmds.currentTime(t)
        out.append(round(cmds.getAttr(plug), 4))
    return out


def layer_keys(layer, plug):
    curve = (cmds.animLayer(layer, q=True, findCurveForPlug=plug) or [None])[0]
    return cmds.keyframe(curve, q=True, timeChange=True) or [] if curve else []


cube = cmds.polyCube(name="cube")[0]
for t, v in ((0, 0), (10, 5), (20, 0), (30, 2)):
    cmds.setKeyframe(cube, attribute="translateX", time=t, value=v)
cmds.select(cube)
names = []
for i, (t, v) in enumerate(((5, 3), (10, 2), (15, 1))):
    S.create_anim()
    layer = S.anim_layers()[0]["name"]
    cmds.setKeyframe(cube, attribute="translateX", time=t, value=v, animLayer=layer)
    names.append(layer)
L1, L2, L3 = names
root = S.anim_layers()[-1]["name"]

# -- Ctrl selection is Maya's ---------------------------------------------------------
S.select_layers([L1, L3], L3)
sel = [n for n in [root] + names if cmds.animLayer(n, q=True, selected=True)]
gate(sel == [L1, L3], "Maya's layer selection: %s" % sel)
gate(mel.eval("global string $gSelectedAnimLayers[]; $tmp = $gSelectedAnimLayers;") == [L1, L3],
     "the editor's $gSelectedAnimLayers follows")
rows = dict((r["name"], r) for r in S.anim_layers())
gate(rows[L1]["selected"] and rows[L3]["selected"] and not rows[L2]["selected"] and rows[L3]["active"],
     "rows read selected / active")

# -- Merge selected: two layers apart, the scene plays the same ---------------------------
#  (time changes are undo steps in standalone - trap 222: undo straight after the press)
before = values(cube + ".translateX")
ok, msg = S.merge_selected([L3, L1])
cmds.undo()
gate(len(S.anim_layers()) == 4, "one undo brings both back: %s" % [r["name"] for r in S.anim_layers()])
ok, msg = S.merge_selected([L3, L1])
left = [r["name"] for r in S.anim_layers()]
gate(ok and len(left) == 3 and L2 in left and L1 not in left and L3 not in left,
     "%s; layers now %s" % (msg, left))
gate(values(cube + ".translateX") == before, "plays the same after the merge")

# -- BaseAnimation in the selection merges into the base ------------------------------------
cmds.optionVar(intValue=("animLayerMergeUp", 1))
before = values(cube + ".translateX")
ok, msg = S.merge_selected([root, L2])
left = [r["name"] for r in S.anim_layers()]
gate(ok and L2 not in left and len(left) == 2 and "into BaseAnimation" in msg, "into the base: %s; layers now %s" % (msg, left))
gate(values(cube + ".translateX") == before, "plays the same after merging into the base")
gate(S.merge_selected([L1])[0] is False, "one layer refused")

cmds.select(cube)
# -- the lanes ------------------------------------------------------------------------------
S.create_anim()
lane = S.anim_layers()[0]["name"]
for t, v in ((2, 1), (4, 2), (6, 3)):
    cmds.setKeyframe(cube, attribute="translateY", time=t, value=v, animLayer=lane)
base_tx = (cmds.animLayer(root, q=True, findCurveForPlug=cube + ".translateX") or [None])[0]
base_before = cmds.keyframe(base_tx, q=True, timeChange=True)
ok, _m = S.lane_move([lane], (2, 4), (12, 14))
gate(layer_keys(lane, cube + ".translateY") == [6.0, 12.0, 14.0],
     "the lane's keys moved: %s" % layer_keys(lane, cube + ".translateY"))
gate(cmds.keyframe(base_tx, q=True, timeChange=True) == base_before, "the base's keys stay")
cmds.undo()
gate(layer_keys(lane, cube + ".translateY") == [2.0, 4.0, 6.0], "one undo")
S.lane_move([lane], (2, 6), (2, 10))
gate(layer_keys(lane, cube + ".translateY") == [2.0, 6.0, 10.0],
     "an edge scales: %s" % layer_keys(lane, cube + ".translateY"))
S.lane_keys("delete", [lane], (6, 6), 0.0)
gate(layer_keys(lane, cube + ".translateY") == [2.0, 10.0], "delete on the lane")
S.lane_keys("copy", [lane], (2, 2), 0.0)
S.lane_keys("paste", [lane], None, 40.0)
gate(40.0 in layer_keys(lane, cube + ".translateY"), "copy / paste on the lane: %s"
     % layer_keys(lane, cube + ".translateY"))
S.lane_keys("tangents", [lane], (2, 10), 0.0, "linear")
crv = (cmds.animLayer(lane, q=True, findCurveForPlug=cube + ".translateY") or [None])[0]
gate(set(cmds.keyTangent(crv, q=True, time=(2, 10), outTangentType=True)) == {"linear"}, "tangents on the lane")
cmds.currentTime(25)
S.lane_set_key(lane)
gate(25.0 in layer_keys(lane, cube + ".translateY"), "Set key on the lane at the current frame")
gate(cmds.keyframe(base_tx, q=True, timeChange=True) == base_before, "the base never touched")

# -- the live key drag on a lane (the timeline's): the scene follows, one undo -----------
before_keys = layer_keys(lane, cube + ".translateY")
gate(S.lane_live_begin([lane], (2, 2)), "a live drag of the lane's key at 2 begins")
S.lane_live_to((7, 7))
gate(7.0 in layer_keys(lane, cube + ".translateY") and 2.0 not in layer_keys(lane, cube + ".translateY"),
     "while dragging the key stands at 7: %s" % layer_keys(lane, cube + ".translateY"))
stamped = S.lane_live_stamp()
gate(bool(stamped), "S puts a copy down where the drag has it")
S.lane_live_to((9, 9))
S.lane_live_end((9, 9))
got = layer_keys(lane, cube + ".translateY")
gate(9.0 in got and 7.0 in got and 2.0 not in got, "let go at 9, the copy at 7 stays: %s" % got)
cmds.undo()
gate(layer_keys(lane, cube + ".translateY") == before_keys, "one undo takes the whole drag back: %s"
     % layer_keys(lane, cube + ".translateY"))
gate(cmds.keyframe(base_tx, q=True, timeChange=True) == base_before, "the base never touched by the drag")


# -- in scene tabs: a tab's BaseAnimation has a parent, Maya's proc misses it ---------
import os
import tempfile
from maya_scenetabs import opening
folder = tempfile.mkdtemp()


def make(path, tag):
    cmds.file(new=True, force=True)
    c = cmds.polyCube(name="cube" + tag)[0]
    for t, v in ((0, 0), (10, 5), (20, 0)):
        cmds.setKeyframe(c, attribute="translateX", time=t, value=v)
    for name, attr, t, v in (("AnimLayer1", "translateY", 5, 3), ("AnimLayer2", "translateZ", 8, 2)):
        cmds.select(c)
        cmds.animLayer(name, addSelectedObjects=True)
        cmds.setKeyframe(c, attribute=attr, time=t, value=v, animLayer=name)
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii", force=True)


def track(node):
    out = []
    for t in range(0, 21, 2):
        cmds.currentTime(t)
        out.append(tuple(round(v, 4) for v in cmds.xform(node, q=True, ws=True, t=True)))
    return out


pa, pb = os.path.join(folder, "a.ma"), os.path.join(folder, "b.ma")
make(pa, "A")
make(pb, "B")
cmds.file(pa, open=True, force=True)
opening.open_tab(pb)
cube_b = cmds.ls("tab_b:cubeB")[0]
cube_a = cmds.ls("tab_a:cubeA")[0]
cmds.select(cube_b)
rows = S.anim_layers()
tab_root = rows[-1]["name"]
before_b, before_a = track(cube_b), track(cube_a)
ok, msg = S.merge_selected([tab_root, rows[0]["name"]])
left = [r["name"] for r in S.anim_layers()]
gate(ok and "into BaseAnimation" in msg and len(left) == 2 and left[-1] == tab_root,
     "a tab: BaseAnimation + a layer merged into the tab's base: %s, %s" % (msg, left))
gate(track(cube_b) == before_b, "the tab's cube plays the same")
gate(track(cube_a) == before_a, "the other tab's cube untouched")
gate(cmds.ls(selection=True) == [cube_b], "the selection kept: %s" % cmds.ls(selection=True))
ok, msg = S.merge_selected([r["name"] for r in S.anim_layers()])
gate(ok and track(cube_b) == before_b and [r["name"] for r in S.anim_layers()] == [tab_root],
     "the last layer merged into the tab's base too: %s" % [r["name"] for r in S.anim_layers()])

cmds.select(cube_b)
made = [S.create_anim()[1] for _i in range(3)]
gate(made == ["AnimLayer1 made", "AnimLayer2 made", "AnimLayer3 made"],
     "new layers in a tab named plainly, one after another: %s" % made)
ok, msg = S.merge_selected([r["name"] for r in S.anim_layers()][:2])
gate(msg.endswith("into Merged_Layer"), "the merge's result named plainly: %s" % msg)

print("%d of %d gates failed" % (len(FAIL), N[0]))
