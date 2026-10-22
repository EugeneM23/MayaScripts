"""Verify maya_camview (2026-10-22): a character's Camera Setup camera puts its rig in 1P.

    mayapy verify_camview.py

mayapy has no viewports, so the panels are stood in for (`_panels`,
`_shown_camera`); everything else is the scene: Manny_Rig and Creep_Rig added,
Camera Setup on each one's camera_root, `Main.view` read and written for real.
"""

import sys

import maya.standalone
maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass

from maya_scenesetup import catalog, character, camera  # noqa: E402
import maya_rigs  # noqa: E402
import maya_camview as cv  # noqa: E402

FAILS = []
COUNT = [0]


def gate(ok, msg):
    COUNT[0] += 1
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


cmds.file(new=True, force=True)
cmds.playbackOptions(minTime=0, maxTime=10)
for key in ("Manny_Rig", "Creep_Rig"):
    character.add_character(catalog.character_by_key(key))
rigs = {r.namespace.split(":")[-1]: r for r in maya_rigs.rigs()}
manny, creep = rigs["Manny_Rig"], rigs["Creep_Rig"]
cams = {}
for name, rig in (("manny", manny), ("creep", creep)):
    bone = cmds.ls(maya_rigs.node(rig, "camera_root"), long=True)[0]
    camera.setup(bone, 0, 10)
    cams[name] = camera.camera_for(bone)
VIEW = manny.main + ".view"
gate(bool(cams["manny"]) and bool(cams["creep"]), "A: a Camera Setup on each rig")
gate(cmds.getAttr(VIEW) == 0, "A: Manny in 3P")
gate(not cmds.attributeQuery("view", node=creep.main, exists=True), "A: the Creep has no 1P")
gate(cv.owner_plug(cams["manny"]) == VIEW, "A: Manny's camera names Manny's Main.view")
gate(cv.owner_plug(cams["creep"]) == "", "A: the Creep's camera names nothing")
gate(cv.owner_plug("|persp") == "", "A: persp names nothing")

shown = {"modelPanel4": "|persp"}
cv._panels = lambda: list(shown)
cv._shown_camera = lambda panel: shown[panel]
st = cv._state()
st.update(ours=set(), owners={})

cmds.file(modified=False)
undo_before = cmds.undoInfo(query=True, undoName=True)
shown["modelPanel4"] = cams["manny"]
first, third = cv.tick()
gate(first == [VIEW] and cmds.getAttr(VIEW) == 1, "B: into Manny's camera - 1P")
gate(not cmds.file(query=True, modified=True), "B: the scene stays clean")
gate(cmds.undoInfo(query=True, undoName=True) == undo_before, "B: no undo step")
shown["modelPanel4"] = "|persp"
cv.tick()
gate(cmds.getAttr(VIEW) == 0, "B: out to persp - 3P")

shown["modelPanel4"] = cams["creep"]
gate(cv.tick() == ([], []), "C: the Creep's camera switches nothing")

cmds.setAttr(VIEW, 1)
shown["modelPanel4"] = cams["manny"]
cv.tick()
shown["modelPanel4"] = "|persp"
cv.tick()
gate(cmds.getAttr(VIEW) == 1, "D: put in 1P by hand - left in 1P after leaving")
cmds.setAttr(VIEW, 0)

shown["modelPanel4"] = cams["manny"]
cv.tick()
cv.unwatch()
gate(cmds.getAttr(VIEW) == 0, "E: switching the option off puts it back in 3P")

cmds.setAttr(VIEW, lock=True)
st.update(ours=set(), owners={})
gate(cv.tick() == ([], []) and cmds.getAttr(VIEW) == 0, "F: a locked view is left alone")
cmds.setAttr(VIEW, lock=False)

print("%d of %d gates failed" % (len(FAILS), COUNT[0]))
