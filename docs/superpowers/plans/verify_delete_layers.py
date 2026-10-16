"""verify_delete_layers.py - Animation Setup > Delete takes the animation layers the character was in
(2026-10-16), in mayapy STANDALONE:

    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_delete_layers.py

A layer of only the rig (a locked one, a parent and its child) goes; a layer shared with a cube or
another rig, and an empty one of the animator's, stays; an emptied BaseAnimation goes; Ctrl+Z / redo.
"""
import sys
import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try: cmds.loadPlugin(p, quiet=True)
    except RuntimeError: pass
sys.path.insert(0, "C:/!!!Work/MayaScripts/SkeldarAnim")
cmds.undoInfo(state=True, infinity=True)
import maya_rigs
from maya_scenesetup import catalog, character, deletion
R = []
def gate(n, ok, d=""):
    R.append(ok); print(("PASS " if ok else "FAIL ") + n, d)

def setup():
    cmds.file(new=True, force=True)
    character.add_character(catalog.default_rig())
    rig = maya_rigs.rigs()[0]
    return rig, maya_rigs.node(rig, "FKShoulder_R"), maya_rigs.node(rig, "FKElbow_R")

# 1: mixed, empty, nested, locked
rig, c1, c2 = setup()
cube = cmds.polyCube(name="myCube")[0]
cmds.setKeyframe(cube + ".tx", t=0, v=0)
cmds.select(c1, c2); A = cmds.animLayer("OnlyRig", addSelectedObjects=True)
cmds.setKeyframe(c1 + ".rz", t=5, v=10, animLayer=A)
cmds.select(c1, cube); M = cmds.animLayer("Mixed", addSelectedObjects=True)
cmds.setKeyframe(cube + ".tx", t=5, v=3, animLayer=M)
E = cmds.animLayer("EmptyMine")
cmds.select(c1); P = cmds.animLayer("Parent", addSelectedObjects=True)
C = cmds.animLayer("Child", parent=P)
cmds.select(c2); cmds.animLayer(C, e=True, addSelectedObjects=True)
cmds.select(c2); Lk = cmds.animLayer("Locked", addSelectedObjects=True); cmds.animLayer(Lk, e=True, lock=True)
before = sorted(cmds.ls(type="animLayer"))
asked = []
line = deletion.delete_selected([c1], confirm=lambda t: asked.append(t) or True)
print(line); print(asked[0])
after = sorted(cmds.ls(type="animLayer"))
gate("the rig's layers go, the others stay", after == ["BaseAnimation", "EmptyMine", "Mixed"], after)
gate("the confirm names them", all(n in asked[0] for n in ("OnlyRig", "Parent", "Child", "Locked")) and "Mixed" not in asked[0].split("deleted:")[-1])
gate("the line names them", "Animation layers deleted" in line and "OnlyRig" in line)
gate("Mixed keeps the cube", cmds.animLayer("Mixed", q=True, attribute=True) and all(a.startswith("myCube") for a in cmds.animLayer("Mixed", q=True, attribute=True)))
CUBE_GATE = lambda: gate("the cube still plays its layer", abs(cmds.getAttr(cube + ".tx") - 3) < 1e-6, cmds.getAttr(cube + ".tx"))
cmds.undo()
gate("Ctrl+Z brings every layer back", sorted(cmds.ls(type="animLayer")) == before, sorted(cmds.ls(type="animLayer")))
gate("OnlyRig holds the rig again", len(cmds.animLayer("OnlyRig", q=True, attribute=True) or []) == 18)
cmds.redo()
gate("redo takes them again", sorted(cmds.ls(type="animLayer")) == after, sorted(cmds.ls(type="animLayer")))
cmds.currentTime(5); CUBE_GATE()
cmds.undo(); cmds.undo()
cmds.currentTime(0); cmds.currentTime(5)
gate("the layer key plays again", abs(cmds.getAttr(maya_rigs.node(rig, "FKShoulder_R") + ".rz") - 10) < 1e-4, cmds.getAttr(maya_rigs.node(rig, "FKShoulder_R") + ".rz"))

# 2: only the rig's layers: the root goes too
rig, c1, c2 = setup()
cmds.select(c1); A = cmds.animLayer("OnlyRig", addSelectedObjects=True)
cmds.setKeyframe(c1 + ".rz", t=5, v=10, animLayer=A)
line = deletion.delete_selected([c1], confirm=lambda t: True)
gate("an emptied BaseAnimation goes too", cmds.ls(type="animLayer") == [], cmds.ls(type="animLayer"))
cmds.undo()
gate("and comes back", sorted(cmds.ls(type="animLayer")) == ["BaseAnimation", "OnlyRig"])
cmds.redo()
cube = cmds.polyCube()[0]; cmds.select(cube); L = cmds.animLayer("After", addSelectedObjects=True)
gate("a new layer after it works", cmds.animLayer(q=True, root=True) == "BaseAnimation", cmds.animLayer(q=True, root=True))

# 3: two rigs in one layer, one deleted: stays
cmds.file(new=True, force=True)
character.add_character(catalog.default_rig()); character.add_character(catalog.default_rig())
rigs = maya_rigs.rigs()
a = maya_rigs.node(rigs[0], "FKShoulder_R"); b = maya_rigs.node(rigs[1], "FKShoulder_R")
cmds.select(a, b); L = cmds.animLayer("Both", addSelectedObjects=True)
deletion.delete_selected([a], confirm=lambda t: True)
gate("a layer shared with another rig stays", cmds.objExists("Both") and all(x.startswith(rigs[1].namespace) for x in cmds.animLayer("Both", q=True, attribute=True)))
deletion.delete_selected([b], confirm=lambda t: True)
gate("then the other rig takes it", cmds.ls(type="animLayer") == [], cmds.ls(type="animLayer"))
print("RESULT %d/%d" % (sum(R), len(R)))
