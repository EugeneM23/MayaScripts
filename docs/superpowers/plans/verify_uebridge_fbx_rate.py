"""Standalone proof: an export after another rate's export still bakes at the scene's rate.

The bug (2026-10-27, the animator): «наш экспортер в uasset может проставить фрейм рейт не такой
как в сцене ... в сцене 30 фпс после экспорта в uassete 120». Measured: Maya 2027's FBX plugin
latches its bake step at the first export of a session made at a rate other than 30; every later
export bakes at that step under a header naming the scene's rate; Unreal's legacy import reads
the keys and picks 120 (fbxkeys).

Runs in mayapy STANDALONE (it opens new scenes):

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_uebridge_fbx_rate.py

Gates:
  A  the control: after a 24 fps export, a bare FBXExport of a 30 fps scene bakes every 1/24 s
  B  export_hierarchy on the plugin's Manny skeleton, the uasset road's layout: every bone curve
     keyed on every frame at 1/30 s, start..end, and Unreal's own sample-rate rule reads 30
  C  the status line says the plugin was reset
  D  the file's bones are the scene's: re-imported, pelvis / hand_r / foot_l on the scene's to 1e-3
  E  the scene is as it was: no node added or lost, the frame, the unit; the selection as an
     export with no reset leaves it (any grouped character's export leaves its root selected:
     chargroup.lifted's re-parent, measured before this fix as well)
  F  the animator's FBX import settings are as they were
  G  the undo queue survives: one undo takes the export (a net nothing), the next the cube made
     before it
  H  a second export needs no reset
  I  any rate: latched at 60, a 24 fps scene comes out at 24
"""

import math
import os
import sys
import tempfile
import traceback

REPO = r"C:/!!!Work/MayaScripts/SkeldarAnim"
sys.path.insert(0, REPO)

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

from maya_scenesetup import catalog, character  # noqa: E402
from maya_uebridge import animexport, animimport, fbxkeys  # noqa: E402

OUT = tempfile.mkdtemp(prefix="fbxrate_")
RESULTS = []

SELECTOR = "Import|IncludeGrp|Animation|SamplingPanel|SamplingRateSelector"
TIMELINE = "Import|IncludeGrp|Animation|ExtraGrp|TimeLine"
ANIMATION = "Import|IncludeGrp|Animation"


def gate(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def unreal_rate(curves):
    """UnrealEd SkeletalMeshEdit.cpp's GetMaxSampleRate over the bone curves (legacy FBX)."""
    def delta_rate(delta):
        orig = 1.0 / delta
        value, mult = orig, 2.0
        prec = min(max(1e-4 * value, 1e-4), 0.1)
        while not (abs(value - math.floor(value)) <= prec or abs(value - math.floor(value) - 1) <= prec):
            value = orig * mult
            if value > 1920:
                value = 30
                break
            mult += 1
        return min(int(round(value)), 1920)

    def curve_rate(times):
        if len(times) < 2 or times[-1] == times[0]:
            return 0
        rate = int(round((len(times) - 1) / (times[-1] - times[0])))
        if rate >= 30:
            return rate
        rate, old, seen = 1, 0.0, set()
        for i, t in enumerate(times):
            d = 0.0 if (t < 0 and i == 0) else t - old
            d -= math.floor(d)
            if abs(d) > 1e-4 and int(round(d / 1e-4)) not in seen:
                seen.add(int(round(d / 1e-4)))
                r = delta_rate(d)
                rate = min(rate * r // math.gcd(rate, r), 1920)
            old = t
        return rate

    total = 1
    for r in set(curve_rate(t) for t in curves):
        if not r:
            continue
        total = min(total * r // math.gcd(total, r), 1920)
    return total


def keyed_skeleton(unit, name="vrf"):
    """A plain keyed chain to latch the plugin with."""
    cmds.file(new=True, force=True)
    cmds.currentUnit(time=unit)
    cmds.select(clear=True)
    root = cmds.joint(name=name + "_root")
    cmds.joint(name=name + "_pelvis", position=(0, 90, 0))
    for frame in range(0, 60, 5):
        cmds.setKeyframe(name + "_pelvis", attribute="rotateX", time=frame, value=frame)
    cmds.playbackOptions(minTime=0, maxTime=59, animationStartTime=0, animationEndTime=59)
    return cmds.ls(root, long=True)[0]


def latch(unit):
    animexport.export_hierarchy(os.path.join(OUT, "latch_%s.fbx" % unit),
                                root=keyed_skeleton(unit), layout="plain")


def world(node, frame):
    cmds.currentTime(frame)
    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def run():
    cmds.undoInfo(state=True, infinity=True)
    # ---- A: the control
    latch("film")
    root = keyed_skeleton("ntsc")
    cmds.select(cmds.listRelatives(root, allDescendents=True, type="joint") + [root])
    mel.eval("FBXResetExport; FBXExportBakeComplexAnimation -v true; "
             "FBXExportBakeResampleAnimation -v true; FBXExportBakeComplexStart -v 0; "
             "FBXExportBakeComplexEnd -v 59; FBXExportBakeComplexStep -v 1")
    bare = os.path.join(OUT, "bare30.fbx")
    mel.eval(animexport.export_command(bare))
    curves = fbxkeys.read_key_times(bare)
    gate("A  the latch is there: a bare 30 fps export bakes at 1/24",
         abs((fbxkeys.key_rate(curves) or 0) - 24) < 1e-3,
         "key rate %s, Unreal would read %s" % (fbxkeys.key_rate(curves), unreal_rate(curves)))

    # ---- the real character, at 30, in its character group
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    entry = catalog.character_for("Manny", "skeleton")
    character.add_character(entry)
    skel = animimport.skeleton_roots()[0]
    joints = animimport.joints_under(skel)
    leaf = {j.split("|")[-1]: j for j in joints}
    for name, attr, values in (("pelvis", "translateY", (0, 6, -4, 2)),
                               ("upperarm_r", "rotateZ", (0, 35, -20, 10)),
                               ("thigh_l", "rotateX", (0, -25, 30, 5))):
        base = cmds.getAttr(leaf[name] + "." + attr)
        for frame, value in zip((0, 13, 27, 40), values):
            cmds.setKeyframe(leaf[name], attribute=attr, time=frame, value=base + value)
    cmds.playbackOptions(minTime=0, maxTime=40, animationStartTime=0, animationEndTime=40)
    cube = cmds.polyCube(name="vrfUndoCanary")[0]
    cmds.currentTime(17)
    cmds.select(leaf["hand_r"])

    # the animator's own import settings, none of them the defaults
    mel.eval("FBXImportMode -v merge; FBXImportSetMayaFrameRate -v true")
    mel.eval('FBXProperty "%s" -v "Custom"' % SELECTOR)
    mel.eval('FBXProperty "%s" -v true' % TIMELINE)
    mel.eval('FBXProperty "%s" -v false' % ANIMATION)
    settings = (mel.eval("FBXImportMode -q"), mel.eval("FBXImportSetMayaFrameRate -q"),
                mel.eval('FBXProperty "%s" -q' % SELECTOR), mel.eval('FBXProperty "%s" -q' % TIMELINE),
                mel.eval('FBXProperty "%s" -q' % ANIMATION))
    nodes = sorted(cmds.ls(long=True))
    selection = cmds.ls(selection=True, long=True)

    path = os.path.join(OUT, "manny30.fbx")
    info = animexport.export_hierarchy(path, root=skel, layout=animexport.UNREAL_LAYOUT)

    # ---- B
    curves = fbxkeys.read_key_times(path)
    densest = max(curves, key=len)
    gate("B  every bone curve at 1/30 on every frame 0..40, Unreal reads 30",
         fbxkeys.bake_problem(curves, 30.0) == "" and len(densest) == 41
         and unreal_rate(curves) == 30,
         "%d curves, key rate %s, %d keys, Unreal %s" % (len(curves), fbxkeys.key_rate(curves),
                                                        len(densest), unreal_rate(curves)))
    # ---- C
    gate("C  the status says the plugin was reset", "exported again" in info["warning"],
         info["warning"])
    # ---- E
    gate("E  no node added or lost", sorted(cmds.ls(long=True)) == nodes,
         str(sorted(set(cmds.ls(long=True)) ^ set(nodes))[:6]))
    gate("E  the frame and the unit",
         cmds.currentTime(query=True) == 17 and cmds.currentUnit(query=True, time=True) == "ntsc",
         "%s %s" % (cmds.currentTime(query=True), cmds.currentUnit(query=True, time=True)))
    # Measured: any export of a grouped character leaves its root selected (chargroup.lifted's
    # re-parent, before this fix too); the reset must leave the selection as a plain export does.
    after_reset_selection = cmds.ls(selection=True, long=True)
    # ---- F
    after = (mel.eval("FBXImportMode -q"), mel.eval("FBXImportSetMayaFrameRate -q"),
             mel.eval('FBXProperty "%s" -q' % SELECTOR), mel.eval('FBXProperty "%s" -q' % TIMELINE),
             mel.eval('FBXProperty "%s" -q' % ANIMATION))
    gate("F  the FBX import settings as they were", after == settings, "%s -> %s" % (settings, after))

    # ---- G: the undo queue survived the reset's import -- before anything else imports
    keyed = cmds.keyframe(leaf["pelvis"], query=True, keyframeCount=True)
    undos = 0
    while cmds.objExists(cube) and undos < 6:
        cmds.undo()
        undos += 1
        if undos == 1:
            first_net = sorted(set(cmds.ls(long=True)) ^ set(nodes))
    gate("G  the first undo takes the export, a net nothing", first_net == [], str(first_net[:6]))
    gate("G  the undo queue reaches the cube made before the export", not cmds.objExists(cube),
         "%d undos, pelvis keys %s -> %s" % (undos, keyed,
                                             cmds.keyframe(leaf["pelvis"], query=True,
                                                           keyframeCount=True)))
    cmds.currentTime(17)

    # ---- D: the file's bones are the scene's
    scene = {name: [world(leaf[name], f) for f in (0, 13, 27, 40)]
             for name in ("pelvis", "hand_r", "foot_l")}
    cmds.namespace(add="chk")
    cmds.namespace(set="chk")
    mel.eval("FBXResetImport; FBXImportMode -v add")
    mel.eval('FBXImport -f "%s"' % path.replace("\\", "/"))
    cmds.namespace(set=":")
    worst = 0.0
    for name, mats in scene.items():
        node = (cmds.ls("chk:" + name, long=True) or [None])[0]
        for frame, m in zip((0, 13, 27, 40), mats):
            got = world(node, frame)
            worst = max(worst, max(abs(a - b) for a, b in zip(m, got)))
    gate("D  pelvis, hand_r, foot_l re-imported on the scene's at 0/13/27/40", worst < 1e-3,
         "worst element %.6f" % worst)
    cmds.namespace(removeNamespace="chk", deleteNamespaceContent=True)
    cmds.currentTime(17)

    # ---- H
    cmds.select(selection)
    info2 = animexport.export_hierarchy(os.path.join(OUT, "manny30b.fbx"), root=skel,
                                        layout=animexport.UNREAL_LAYOUT)
    gate("E  the reset leaves the selection as an export without one does",
         cmds.ls(selection=True, long=True) == after_reset_selection,
         "%s vs %s" % (after_reset_selection, cmds.ls(selection=True, long=True)))
    curves = fbxkeys.read_key_times(os.path.join(OUT, "manny30b.fbx"))
    gate("H  a second export needs no reset, and is at 30",
         "exported again" not in info2["warning"] and fbxkeys.bake_problem(curves, 30.0) == "",
         info2["warning"])
    return info


def run_any_rate():
    """A fresh latch at 60 needs a fresh session, so this half runs in its own process."""
    latch("ntscf")
    root = keyed_skeleton("film", name="vrf24")
    path = os.path.join(OUT, "film24.fbx")
    info = animexport.export_hierarchy(path, root=root, layout="plain")
    curves = fbxkeys.read_key_times(path)
    gate("I  latched at 60, a 24 fps scene comes out at 24",
         fbxkeys.bake_problem(curves, 24.0) == "" and unreal_rate(curves) == 24
         and "exported again" in info["warning"],
         "key rate %s, Unreal %s | %s" % (fbxkeys.key_rate(curves), unreal_rate(curves),
                                          info["warning"]))


if __name__ == "__main__":
    try:
        if "any_rate" in sys.argv[1:]:
            run_any_rate()
        else:
            run()
    except Exception:
        traceback.print_exc()
        gate("the run finished", False)
    failed = [r for r in RESULTS if not r[1]]
    print("%d of %d gates failed" % (len(failed), len(RESULTS)))
    sys.stdout.flush()
    maya.standalone.uninitialize()
    os._exit(0)
