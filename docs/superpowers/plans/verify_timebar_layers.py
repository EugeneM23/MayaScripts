"""verify_timebar_layers.py - the Time Bar's layer panel's Maya half, mayapy standalone
(2026-10-18). Every write of maya_timebar.layerscene on a real scene, read back."""
import sys
import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds
sys.path.insert(0, r"C:/!!!Work/MayaScripts/SkeldarAnim")
for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
from maya_timebar import layerscene as S

FAIL = []
N = [0]


def gate(ok, text):
    N[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", N[0], text))
    if not ok:
        FAIL.append(N[0])


def values(plug, frames=(0, 5, 10, 20)):
    out = []
    for t in frames:
        cmds.currentTime(t)
        out.append(round(cmds.getAttr(plug), 5))
    return out


cube = cmds.polyCube(name="cube")[0]
for t, v in ((0, 0), (10, 5), (20, 0)):
    cmds.setKeyframe(cube, attribute="translateX", time=t, value=v)
cmds.select(cube)
ok, msg = S.create_anim()
rows = S.anim_layers()
gate(ok and len(rows) == 2 and rows[-1]["base"] and rows[0]["active"], "a layer made from the selection, active: %s" % msg)
first = rows[0]["name"]
cmds.setKeyframe(cube, attribute="translateX", time=5, value=3, animLayer=first)
S.create_anim()
rows = S.anim_layers()
gate([r["base"] for r in rows] == [False, False, True], "newest first, base last: %s" % [r["label"] for r in rows])
second = rows[0]["name"]
keys = S.keys_by_layer([r["name"] for r in rows])
gate(keys[first] == [5.0] and keys[rows[-1]["name"]] == [0.0, 10.0, 20.0], "keys per layer: %s" % keys)
S.set_flag(first, "mute", True)
gate(cmds.getAttr(first + ".mute"), "mute written")
cmds.undo()
gate(not cmds.getAttr(first + ".mute"), "one undo takes the mute back")
S.begin_weight(); S.set_weight(first, 0.25); S.set_weight(first, 0.4); S.end_weight()
gate(abs(cmds.getAttr(first + ".weight") - 0.4) < 1e-6, "weight dragged to 0.4")
cmds.undo()
gate(abs(cmds.getAttr(first + ".weight") - 1.0) < 1e-6, "the whole drag is one undo")
S.set_mode(first, "ovr")
gate(cmds.getAttr(first + ".override"), "override")
S.set_mode(first, "add")
S.set_weight(first, 0.5)
S.set_weight(second, 1.0)

# merge: the scene must play the same before and after
cmds.optionVar(intValue=("animLayerMergeUp", 0))
before = values(cube + ".translateX")      # (time changes are undo steps in standalone: measure undo first)
ok, msg = S.merge_down(second)
merged = [r["name"] for r in S.anim_layers()]
steps = 0
while len(cmds.ls(type="animLayer")) < 3 and steps < 20:
    cmds.undo(); steps += 1
undone = [r["name"] for r in S.anim_layers()]
print("undo steps to restore the merge:", steps)
gate(steps == 1 and len(undone) == 3, "ONE undo brings both layers back (%d step(s)): %s" % (steps, undone))
ok, msg = S.merge_down(second)
after_names = [r["name"] for r in S.anim_layers()]
after = values(cube + ".translateX")
gate(ok, "merge down: %s; layers now %s" % (msg, after_names))
gate(len(after_names) == 2 and merged == after_names, "two layers became one (plus the base): %s" % after_names)
gate(before == after, "the scene plays the same: %s -> %s" % (before, after))
gate(first.split(":")[-1] == after_names[0].split(":")[-1] or second.split(":")[-1] == after_names[0].split(":")[-1],
     "the result keeps a source layer's name: %s" % after_names[0])
gate(cmds.optionVar(q="animLayerMergeUp") == 0, "the merge's option put back")
cmds.undo()
gate(values(cube + ".translateX") == before, "undone, the values are back")
base = cmds.animLayer(q=True, root=True)
gate(not S.merge_down(S.anim_layers()[-2]["name"])[0], "nothing to merge into the base")
gate(not S.delete_anim(base)[0], "BaseAnimation is never deleted")
cmds.select(cube)
ok, msg = S.create_display()
d = S.display_layers()
gate(ok and len(d) == 1, "a display layer from the selection")
name = d[0]["name"]
S.set_display(name, "visible", False); S.set_display(name, "playback", False); S.set_display(name, "type", 2)
d = S.display_layers()[0]
gate((d["visible"], d["playback"], d["type"]) == (False, False, 2), "V, P, type written: %s" % d)
cmds.select(clear=True); S.display_select(name)
gate(cmds.ls(selection=True) == [cube], "the layer's objects selected")
print("%d of %d gates failed" % (len(FAIL), N[0]))
