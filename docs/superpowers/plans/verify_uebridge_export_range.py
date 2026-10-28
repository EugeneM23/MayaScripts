"""Standalone proof: keys past the exported range never reach the file (2026-10-28).

The bug (the animator, port 7003: «чому не експортиться анімація»): a 0-62 scene whose weapon_l and
camera_bone carry their own keys to 65. The FBX plugin baked 0..62 and kept 64 and 65; the rate
check read the hole 62 -> 64 as a latched plugin and refused («bakes keys every 1/30 s, the scene is
30 fps and would not let go ... restart Maya»). The export now cuts the file's one take to the range
(animexport.TAKE) and refuses keys past it by name.

Runs in mayapy STANDALONE (it opens new scenes):

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_uebridge_export_range.py
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_uebridge_export_range.py latched

Gates:
  A  Manny in its character group, a bone keyed to -5, 44 and 45 past 0-40: the uasset road's
     export goes through, the file holds frames 0..40 only, Unreal's rule reads 30
  B  one take, `Take 001`, 0-40 - the file reads as before
  C  the file's bones are the scene's inside the range: pelvis, hand_r and the keyed bone re-imported
     on the scene's to 1e-3 at 0/13/27/40
  D  the status line names the keys past the range
  E  the scene as it was: no node added or lost, the keyed bone's keys all there, the frame
  F  nothing is left split: a plain export after it (Stash's road) holds its one whole take
  G  the animator's own split takes and delete flag come back after an export
  H  Cascadeur's layout (Export FBX...) is cut the same
  I  (latched) a plugin latched at 24 is reset and the second export is cut to the range too
"""

import math
import os
import sys
import tempfile
import traceback

REPO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))), "SkeldarAnim")
sys.path.insert(0, REPO)

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

from maya_scenesetup import catalog, character  # noqa: E402
from maya_uebridge import animexport, animimport, fbxkeys  # noqa: E402

OUT = tempfile.mkdtemp(prefix="fbxrange_")
RESULTS = []
FRAMES = (0, 13, 27, 40)


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
        if r:
            total = min(total * r // math.gcd(total, r), 1920)
    return total


def frames_in(path, fps=30.0):
    return sorted(set(round(t * fps, 4) for c in (fbxkeys.read_key_times(path) or []) for t in c))


def takes(path):
    mel.eval('FBXRead -f "%s"' % path.replace("\\", "/"))
    count = int(mel.eval("FBXGetTakeCount") or 0)
    return [(mel.eval("FBXGetTakeName %d" % i), [round(v, 4) for v in
                                                  mel.eval("FBXGetTakeLocalTimeSpan %d" % i)])
            for i in range(1, count + 1)]


def world(node, frame):
    cmds.currentTime(frame)
    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def manny():
    """Manny in its character group, 0-40, a bone keyed on its own past both ends."""
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    character.add_character(catalog.character_for("Manny", "skeleton"))
    skel = animimport.skeleton_roots()[0]
    leaf = {j.split("|")[-1]: j for j in animimport.joints_under(skel)}
    for name, attr, values in (("pelvis", "translateY", (0, 6, -4, 2)),
                               ("upperarm_r", "rotateZ", (0, 35, -20, 10))):
        base = cmds.getAttr(leaf[name] + "." + attr)
        for frame, value in zip(FRAMES, values):
            cmds.setKeyframe(leaf[name], attribute=attr, time=frame, value=base + value)
    stray = "weapon_l" if "weapon_l" in leaf else "hand_l"
    base = cmds.getAttr(leaf[stray] + ".rotateX")
    for frame, value in ((-5, 40), (0, 0), (20, 15), (40, -10), (44, 60), (45, 90)):
        cmds.setKeyframe(leaf[stray], attribute="rotateX", time=frame, value=base + value)
    cmds.playbackOptions(minTime=0, maxTime=40, animationStartTime=0, animationEndTime=40)
    return skel, leaf, stray


def splits():
    return (animexport.parse_split_takes(mel.eval("FBXExportSplitAnimationIntoTakes -q")),
            mel.eval("FBXExportDeleteOriginalTakeOnSplitAnimation -q"))


def run():
    skel, leaf, stray = manny()
    cmds.currentTime(17)
    cmds.select(leaf["hand_r"])
    nodes = sorted(cmds.ls(long=True))
    stray_keys = cmds.keyframe(leaf[stray], query=True, timeChange=True)
    path = os.path.join(OUT, "manny_range.fbx")

    # ---- 0: the control - the plugin's own bake keeps the stray keys
    bare = os.path.join(OUT, "bare.fbx")
    animimport.ensure_fbx_plugin()
    animexport._apply_export_options(0, 40)
    cmds.select(animimport.joints_under(skel), replace=True)
    mel.eval(animexport.export_command(bare))
    got = frames_in(bare)
    gate("0  the control: a bare bake of 0-40 holds -5 and 45 too", got[:1] == [-5.0]
         and got[-1:] == [45.0], "%s..%s" % (got[:1], got[-1:]))
    cmds.currentTime(17)
    cmds.select(leaf["hand_r"])

    # ---- A
    try:
        info = animexport.export_hierarchy(path, root=skel, layout=animexport.UNREAL_LAYOUT)
        raised = ""
    except RuntimeError as exc:
        info, raised = {"warning": ""}, str(exc)
    got = frames_in(path) if os.path.exists(path) else []
    curves = fbxkeys.read_key_times(path) if os.path.exists(path) else []
    gate("A  exported, frames 0..40 only, Unreal reads 30",
         not raised and got[:1] == [0.0] and got[-1:] == [40.0] and len(got) == 41
         and fbxkeys.bake_problem(curves, 30.0) == "" and unreal_rate(curves) == 30,
         raised or "%s..%s (%d frames), Unreal %s" % (got[:1], got[-1:], len(got),
                                                     unreal_rate(curves)))
    # ---- B
    gate("B  one take, Take 001, 0-40", takes(path) == [("Take 001", [0.0, 40.0])], str(takes(path)))
    # ---- D
    gate("D  the status names the keys past the range", "outside the exported range"
         in info["warning"], info["warning"])
    # ---- E
    gate("E  no node added or lost", sorted(cmds.ls(long=True)) == nodes,
         str(sorted(set(cmds.ls(long=True)) ^ set(nodes))[:6]))
    gate("E  the stray bone keeps every key, the frame is put back",
         cmds.keyframe(leaf[stray], query=True, timeChange=True) == stray_keys
         and cmds.currentTime(query=True) == 17,
         "%s, frame %s" % (cmds.keyframe(leaf[stray], query=True, timeChange=True),
                           cmds.currentTime(query=True)))
    # ---- F
    gate("F  nothing left split after the export", splits() == ([], 0), str(splits()))
    plain = os.path.join(OUT, "stash_like.fbx")
    cmds.select(leaf["pelvis"], replace=True)
    mel.eval("FBXResetExport; FBXExportBakeComplexAnimation -v false")
    mel.eval(animexport.export_command(plain))
    gate("F  a plain export after it holds its one whole take", len(takes(plain)) == 1
         and takes(plain)[0][0] == "Take 001", str(takes(plain)))
    # ---- C
    scene = {name: [world(leaf[name], f) for f in FRAMES] for name in ("pelvis", "hand_r", stray)}
    cmds.namespace(add="chk")
    cmds.namespace(set="chk")
    mel.eval("FBXResetImport; FBXImportMode -v add")
    mel.eval('FBXImport -f "%s"' % path.replace("\\", "/"))
    cmds.namespace(set=":")
    worst = 0.0
    for name, mats in scene.items():
        node = (cmds.ls("chk:" + name, long=True) or [None])[0]
        for frame, m in zip(FRAMES, mats):
            worst = max(worst, max(abs(a - b) for a, b in zip(m, world(node, frame))))
    gate("C  pelvis, hand_r, %s re-imported on the scene's at 0/13/27/40" % stray, worst < 1e-3,
         "worst element %.6f" % worst)
    cmds.namespace(removeNamespace="chk", deleteNamespaceContent=True)

    # ---- G
    mel.eval("FBXExportSplitAnimationIntoTakes -c")
    mel.eval(animexport.split_command("walk", 5, 20))
    mel.eval(animexport.split_command("run b", 21, 40))
    mel.eval("FBXExportDeleteOriginalTakeOnSplitAnimation -v false")
    before = splits()
    animexport.export_hierarchy(os.path.join(OUT, "manny_g.fbx"), root=skel,
                                layout=animexport.UNREAL_LAYOUT)
    gate("G  the animator's own splits come back", splits() == before, "%s -> %s" % (before, splits()))
    gate("G  ...and did not reach our file", takes(os.path.join(OUT, "manny_g.fbx"))
         == [("Take 001", [0.0, 40.0])], str(takes(os.path.join(OUT, "manny_g.fbx"))))
    mel.eval("FBXExportSplitAnimationIntoTakes -c")

    # ---- H
    casc = os.path.join(OUT, "manny_cascadeur.fbx")
    animexport.export_hierarchy(casc, root=skel, layout="cascadeur")
    got = frames_in(casc)
    gate("H  Cascadeur's layout cut the same", got[:1] == [0.0] and got[-1:] == [40.0]
         and takes(casc) == [("Take 001", [0.0, 40.0])], "%s..%s %s" % (got[:1], got[-1:],
                                                                          takes(casc)))


def run_latched():
    """A latch needs a fresh session, so this half runs in its own process."""
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="film")
    cmds.select(clear=True)
    root = cmds.joint(name="lat_root")
    cmds.joint(name="lat_pelvis", position=(0, 90, 0))
    for frame in range(0, 60, 5):
        cmds.setKeyframe("lat_pelvis", attribute="rotateX", time=frame, value=frame)
    cmds.playbackOptions(minTime=0, maxTime=59, animationStartTime=0, animationEndTime=59)
    animexport.export_hierarchy(os.path.join(OUT, "latch24.fbx"), root=cmds.ls(root, long=True)[0],
                                layout="plain")
    skel, _leaf, _stray = manny()
    path = os.path.join(OUT, "manny_latched.fbx")
    try:
        info = animexport.export_hierarchy(path, root=skel, layout=animexport.UNREAL_LAYOUT)
        raised = ""
    except RuntimeError as exc:
        info, raised = {"warning": ""}, str(exc)
    got = frames_in(path) if os.path.exists(path) else []
    curves = fbxkeys.read_key_times(path) if os.path.exists(path) else []
    gate("I  latched at 24: reset, the second export cut to 0..40 at 30",
         not raised and "exported again" in info["warning"] and got[-1:] == [40.0]
         and len(got) == 41 and unreal_rate(curves) == 30 and splits() == ([], 0),
         raised or "%s | %d frames, Unreal %s" % (info["warning"], len(got), unreal_rate(curves)))


if __name__ == "__main__":
    try:
        if "latched" in sys.argv[1:]:
            run_latched()
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
