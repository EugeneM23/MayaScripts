"""verify_walk_keys_changed.py - Walk Builder keeps working after a weapon or a camera joins the
walked skeleton. mayapy standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_keys_changed.py

Measured in the animator's Maya on 2026-10-29 (port 7004): the walk was keyed onto a Manny skeleton,
then the Long Sword went into its right hand - bonedrive.link cut `weapon_r`'s own curves and
constrained the bone to the sword - and from then on every knob of the card answered

    0 walkers keyed | not keyed: Manny_Skeleton - Manny_Skeleton's cycle:
    new keys on it since the walk - Pick it to take them

although every key on the skeleton was still the walk's own output (worst difference 5.7e-14). The
digest keys_print kept was one hash over every joint, so a bone a driver took changed it with no new
animation. The memo's digest was reproduced exactly, uniquely among 8000 candidates, by the scene's
keys plus weapon_r's six curves - which is what pins the cause.

This script reproduces that sequence on a real skeleton and gates both directions: a weapon, a camera
and a Tools-style knot must not be read as a new take, while a clip keyed over the walk still must.
The old digest is monkeypatched back in as a positive control, so every gate here can fail.
"""
import hashlib
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")
WALK = os.path.join(HERE, "walks", "asd.walk.gz")

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except RuntimeError:
        pass

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))     # the repository's plugin, never the installed copy
from maya_walk import scene as sw                         # noqa: E402
from maya_walk import panel                               # noqa: E402
from maya_scenesetup import catalog, equip, camera        # noqa: E402

FAILED = []
COUNT = [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


def old_keys_print(root):
    """keys_print as it was until 2026-10-29: one hash over every joint and channel."""
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    digest = hashlib.sha1()
    for joint in sorted(joints):
        for ch in sw.CHANNELS:
            try:
                curve = sw.base_input(joint + "." + ch)[1]
            except sw.Refusal:
                continue
            if not curve:
                continue
            times = cmds.keyframe(curve, query=True, timeChange=True) or []
            values = cmds.keyframe(curve, query=True, valueChange=True) or []
            digest.update(repr((sw._short(joint).split(":")[-1], ch, [round(t, 3) for t in times],
                                [round(v, 4) for v in values])).encode("utf-8"))
    return digest.hexdigest()[:16]


def old_changed(root):
    """keys_changed as it was: the one hash against the marker's."""
    memo = sw.memo_of(root)
    known = memo.get("keys")
    return bool(memo.get("walk")) and bool(known) and known != old_keys_print(root)


def driver_of(bone, ch="rotateY"):
    src = cmds.listConnections(bone + "." + ch, source=True, destination=False,
                              skipConversionNodes=True) or []
    return (src[0], cmds.nodeType(src[0])) if src else (None, None)


def refusal_in(text):
    return "new keys on it since the walk" in (text or "")


if not os.path.exists(WALK):
    print("SKIP: the fixture %s is not here" % WALK)
    sys.exit(0)

TEMP = tempfile.mkdtemp(prefix="walkkeys_")
shutil.copy(WALK, TEMP)
sw.WALKS = TEMP
for key in [k for k in (cmds.optionVar(list=True) or []) if k.startswith(panel.OPTION)]:
    cmds.optionVar(remove=key)

# ---------------------------------------------------------------- the walk on a Manny skeleton
cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, ignoreVersion=True)
root = cmds.ls("root", long=True)[0]
sw.apply(root, "asd", {})
sw.set_working([root])

memo = sw.memo_of(root)
gate(isinstance(memo.get("keys"), dict) and len(memo["keys"]) > 60,
     "the marker keeps a digest a bone a row (%s rows)" % len(memo.get("keys") or {}))
gate(not sw.keys_changed(root), "right after the walk nothing reads as new animation")
gate(not refusal_in(panel.rekey_all(roots=[root])), "and a knob keys it")

weapon_r = cmds.ls("weapon_r", long=True)[0]
camera_root = cmds.ls("camera_root", long=True)[0]
gate(driver_of(weapon_r)[1] == "animCurveTA" and driver_of(camera_root)[1] == "animCurveTA",
     "the walk keyed weapon_r and camera_root: both carry their own curves")

# ---------------------------------------------------------------- the sword into the hand
line = equip.to_hand(root, "R", catalog.by_key("LongSword_02"))
print("   Add Weapon:", line)
gate(driver_of(weapon_r)[1] == "parentConstraint",
     "Add Weapon cut weapon_r's curves and drove the bone from the sword (%s)" % driver_of(weapon_r)[1])
gate(not sw.keys_changed(root), "a weapon in the hand is not new animation")
gate(old_changed(root), "CONTROL: the old digest read it as a new take (this is the bug)")
gate(not refusal_in(panel.rekey_all(roots=[root])), "a knob keys the walker with the sword in its hand")
gate(cmds.ls("*.mayaWeapon", recursive=True, objectsOnly=True) and True,
     "the sword is in the scene")

# ---------------------------------------------------------------- Camera Setup on camera_root
start, end = int(cmds.playbackOptions(query=True, min=True)), int(cmds.playbackOptions(query=True, max=True))
print("   Camera Setup:", camera.setup(camera_root, start, end))
gate(driver_of(camera_root)[1] == "parentConstraint",
     "Camera Setup drives camera_root from its control (%s)" % driver_of(camera_root)[1])
gate(not sw.keys_changed(root), "a camera on the skeleton is not new animation either")
gate(old_changed(root), "CONTROL: the old digest read that as a new take too")
gate(not refusal_in(panel.rekey_all(roots=[root])), "a knob still keys it")

# ---------------------------------------------------------------- a knot on a bone (Tools)
hand_r = cmds.ls("hand_r", long=True)[0]
knot = cmds.spaceLocator(name="probeKnot")[0]
cmds.cutKey(hand_r, attribute=sw.CHANNELS, clear=True)
cmds.parentConstraint(knot, hand_r, maintainOffset=True)
gate(driver_of(hand_r)[1] == "parentConstraint", "a knot drives hand_r")
gate(not sw.keys_changed(root), "a bone a knot took is not new animation")
gate(old_changed(root), "CONTROL: the old digest read that as a new take as well")

# ---------------------------------------------------------------- what IS new animation
pelvis = cmds.ls("pelvis", long=True)[0]
was = cmds.keyframe(pelvis + ".rotateY", query=True, time=(start + 3,), valueChange=True)
cmds.setKeyframe(pelvis + ".rotateY", time=start + 3, value=(was[0] if was else 0.0) + 12.0)
gate(sw.keys_changed(root), "a key moved on the pelvis IS new animation")
gate(refusal_in(panel.rekey_all(roots=[root])), "and a knob refuses it, naming the walker")

cmds.undo()                                           # the hand correction taken back
gate(not sw.keys_changed(root), "undone, the walker is the walk's own again")

# ---------------------------------------------------------------- a clip over the whole skeleton
for leaf in ("pelvis", "spine_01", "thigh_l", "calf_l", "upperarm_r"):
    path = cmds.ls(leaf, long=True)[0]
    for ch in ("rotateX", "rotateY", "rotateZ"):
        cmds.setKeyframe(path + "." + ch, time=start + 2, value=7.0)
gate(sw.keys_changed(root), "a clip keyed over the walk IS new animation, weapon and camera and all")

# ---------------------------------------------------------------- the weapon off again
print("   Remove Weapon:", equip.take_off(root, "R"))
gate(driver_of(weapon_r)[1] != "parentConstraint",
     "Remove Weapon handed weapon_r back (%s)" % str(driver_of(weapon_r)[1]))
sw.apply(root, "asd", {})                             # the take is the walk's again
gate(not sw.keys_changed(root), "a fresh press settles it, the weapon gone")

# ---------------------------------------------------------------- an older marker cannot tell
stale = dict(sw.memo_of(root))
stale["keys"] = "0123456789abcdef"
sw._set_memo(root, stale)
gate(not sw.keys_changed(root), "a marker from before the per-bone digest answers False")

shutil.rmtree(TEMP, ignore_errors=True)
print()
print("%d of %d gates failed%s" % (len(FAILED), COUNT[0], (": " + ", ".join(map(str, FAILED))) if FAILED else ""))
sys.stdout.flush()
