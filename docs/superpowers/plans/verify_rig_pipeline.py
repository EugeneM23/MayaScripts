"""The AdvancedSkeleton pipeline, end to end, in mayapy STANDALONE.

Never in the animator's open Maya: this adds a rig, imports clips and
deletes skeletons. Run:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_rig_pipeline.py

What it proves (spec: docs/superpowers/specs/2026-09-07-advancedskeleton-pipeline-design.md):

  phase 1  the REFERENCE: the clip imported on its own skeleton, the helper
           bones' world matrices sampled at six frames, the skeleton deleted.
           Every expectation below is computed from this, never typed.
  phase 2  IMPORT with no rig in the scene: the rig is added, the clip
           retargeted and baked, the source deleted; weapon_r / weapon_l /
           camera_root / camera_bone on the rig's skeleton land on the
           reference; the camera stands on camera_bone and drives it.
  phase 3  a sword attached, then IMPORT again on the standing rig: the
           previous take cleared, the sword still linked and riding the new
           weapon_r track, one camera, the resolver and the FBX export.
"""

import os
import sys
import tempfile
import time
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
CLIP = "C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_1P.FBX"
HELPERS = ("weapon_r", "weapon_l", "camera_root", "camera_bone")
WATCHED = HELPERS + ("hand_r", "root", "head")

if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)
for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(plugin, quiet=True)
cmds.currentUnit(time="ntsc")

from maya_scenesetup import attach, bonedrive, camera, catalog, character, skeleton  # noqa: E402
from maya_uebridge import animexport, animimport, rigimport  # noqa: E402
import maya_rig_retarget  # noqa: E402,F401

RESULTS = []


def gate(number, ok, text, detail=""):
    RESULTS.append(bool(ok))
    line = "%s %2d %s" % ("PASS" if ok else "FAIL", number, text)
    if detail:
        line += "   [%s]" % detail
    print(line)
    return bool(ok)


def _fmt(value):
    """A measured number, or 'missing' -- never `x or -1`, which turns an
    exact 0.0 into -1 on the report."""
    return "missing" if value is None else "%.6f" % value


def world(node):
    return cmds.xform(node, query=True, matrix=True, worldSpace=True)


def worst(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def at_frames(frames, fn):
    out = {}
    for frame in frames:
        cmds.currentTime(frame, edit=True)
        out[frame] = fn()
    return out


def bones_under(root):
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                         fullPath=True) or [])
    out = {}
    for path in paths:
        out.setdefault(path.split("|")[-1].split(":")[-1], path)
    return out


def namespace_root(namespace):
    nodes = cmds.namespaceInfo(namespace, listOnlyDependencyNodes=True,
                               recurse=True, dagPath=True) or []
    return rigimport.source_root_in(nodes, lambda p: cmds.objectType(p) == "joint")


def compare(reference, frames, bones, names, tol):
    """Worst world-matrix element between the rig's bones and the reference."""
    out = {}
    for name in names:
        if name not in bones or name not in reference:
            out[name] = None
            continue
        samples = at_frames(frames, lambda: world(bones[name]))
        out[name] = max(worst(samples[f], reference[name][f]) for f in frames)
    return out


def main():
    t_all = time.time()
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    gate(1, not character.rig_present() and not cmds.ls(type="joint"),
         "an empty scene: no rig, no joints")

    # ------------------------------------------------------------ phase 1
    info = animimport.import_clip(CLIP, "ref", set_timeline=False, merge=False)
    ref_root = namespace_root("ref")
    start, end = info["start"], info["end"]
    frames = sorted(set(int(round(start + (end - start) * k / 5.0)) for k in range(6)))
    ref_bones = bones_under(ref_root) if ref_root else {}
    gate(2, ref_root and info["joints"] >= 90 and end > start,
         "the reference clip imported on its own skeleton",
         "%s joints, frames %g..%g, sampled at %s" % (info["joints"], start, end, frames))
    reference = {}
    for name in WATCHED:
        if name in ref_bones:
            reference[name] = at_frames(frames, lambda n=name: world(ref_bones[n]))
    travel = {}
    for name in HELPERS:
        if name in reference:
            xs = [reference[name][f][12:15] for f in frames]
            travel[name] = max(worst(a, b) for a in xs for b in xs)
    gate(3, all(name in reference for name in HELPERS),
         "the clip carries all four helper bones",
         "travel over the take: " + ", ".join("%s %.2f cm" % kv for kv in sorted(travel.items())))
    cmds.namespace(removeNamespace="ref", deleteNamespaceContent=True)
    gate(4, not cmds.namespace(exists="ref") and not cmds.ls(type="joint"),
         "the reference skeleton deleted, the scene empty again")

    # ------------------------------------------------------------ phase 2
    t0 = time.time()
    text = rigimport.import_and_retarget(CLIP, "Heavy1P", set_timeline=True)
    print("    IMPORT #1 (%.1f s): %s" % (time.time() - t0, text))
    gate(5, "retargeted onto the rig" in text and "deleted" in text
         and "added" in text, "IMPORT with no rig: rig added, retargeted, source deleted")
    rig_root = skeleton.rig_root()
    gate(6, character.rig_present() and rig_root == "|root"
         and cmds.objExists("ControlSet") and cmds.objExists("Main"),
         "the rig stands and drives |root", "rig_root=%s" % rig_root)
    gate(7, character.add_character(catalog.default_rig()) == character.RIG_PRESENT,
         "a second Add Character with the rig is refused (one rig per scene)")
    gate(8, not cmds.namespace(exists="Heavy1P") and not cmds.objExists("MoCapConstraints")
         and not cmds.ls("*:*", type="joint"),
         "no source namespace, no holder, no namespaced joint left")

    controls = cmds.sets("ControlSet", query=True) or []
    keyed = [c for c in controls
             if cmds.listConnections(c, type="animCurve", source=True, destination=False)]
    curves = list(set(cmds.listConnections(keyed, type="animCurve", source=True,
                                           destination=False) or [])) if keyed else []
    k0 = cmds.findKeyframe(curves, which="first") if curves else None
    k1 = cmds.findKeyframe(curves, which="last") if curves else None
    gate(9, len(keyed) >= 20 and k0 is not None and abs(k0 - start) < 0.5 and abs(k1 - end) < 0.5,
         "the controls carry the take over the clip's range",
         "%d controls keyed, %d curves, keys %s..%s" % (len(keyed), len(curves), k0, k1))
    gate(10, abs(cmds.playbackOptions(query=True, min=True) - start) < 0.5
         and abs(cmds.playbackOptions(query=True, max=True) - end) < 0.5,
         "the playback range follows the clip")

    bones = bones_under(rig_root)
    errors = compare(reference, frames, bones, WATCHED, 0.05)
    gate(11, errors["hand_r"] is not None and errors["hand_r"] < 0.05,
         "the retarget itself: hand_r on the reference", "worst %s" % _fmt(errors["hand_r"]))
    gate(12, errors["root"] is not None and errors["root"] < 0.02,
         "root motion through Main", "worst %s" % _fmt(errors["root"]))
    gate(13, errors["weapon_r"] is not None and errors["weapon_r"] < 0.05,
         "weapon_r carried onto the rig's skeleton", "worst %s" % _fmt(errors["weapon_r"]))
    gate(14, errors["weapon_l"] is not None and errors["weapon_l"] < 0.05,
         "weapon_l carried", "worst %s" % _fmt(errors["weapon_l"]))
    gate(15, errors["camera_root"] is not None and errors["camera_root"] < 0.02,
         "camera_root carried", "worst %s" % _fmt(errors["camera_root"]))
    gate(16, errors["camera_bone"] is not None and errors["camera_bone"] < 0.02,
         "camera_bone carried (and now driven by the camera)",
         "worst %s" % _fmt(errors["camera_bone"]))

    cams = camera.our_cameras()
    cam_bone = bones.get("camera_bone")
    gate(17, len(cams) == 1 and cams[0].split("|")[-1] == camera.CAMERA_NAME
         and cam_bone and camera.our_constraints(cam_bone),
         "one camera of ours, named, driving camera_bone", "%s" % cams)
    offset = camera.rotation_only(camera.AXIS_OFFSET)
    cam_err = max(worst(world(cams[0]), camera.placed_matrix(world(cam_bone), offset))
                  for _ in at_frames(frames[:3], lambda: None)) if cams and cam_bone else -1
    gate(18, cams and cam_err < 1e-3, "the camera sits in camera_bone's transform, axes turned",
         "worst %.6f" % cam_err)

    # ------------------------------------------------------------ phase 3
    entry = catalog.by_key("LongSword_02")
    cmds.select(clear=True)
    root = skeleton.current_root()
    gate(19, root == "|root", "resolver: nothing selected, one rig -> the rig's skeleton", root)
    bone = skeleton.resolve_bone(root, "weapon_r")
    hand = attach.parent_bone(bone)
    weapon, note = attach.attach(entry, hand, bone)
    gate(20, weapon and cmds.objExists(weapon) and bonedrive.driving_weapon(bone) == weapon,
         "the sword attached under the hand and driving weapon_r", "%s %s" % (weapon, note))

    t0 = time.time()
    text2 = rigimport.import_and_retarget(CLIP, "Heavy1P", set_timeline=True)
    print("    IMPORT #2 (%.1f s): %s" % (time.time() - t0, text2))
    gate(21, "retargeted onto the rig" in text2 and "previous take cleared" in text2
         and "added" not in text2, "IMPORT on the standing rig: take replaced, no second rig")
    linked = bonedrive.driving_weapon(bone)
    gate(22, linked == weapon, "the sword is still linked after the second import", str(linked))
    bones = bones_under(rig_root)
    errors2 = compare(reference, frames, bones, ("weapon_r", "hand_r", "camera_bone"), 0.05)
    gate(23, errors2["weapon_r"] is not None and errors2["weapon_r"] < 0.05,
         "weapon_r on the reference again, through the sword", "worst %s" % _fmt(errors2["weapon_r"]))
    sword_err = max(worst(world(weapon), world(bone)) for _ in at_frames(frames, lambda: None))
    gate(24, sword_err < 0.05, "the sword rides weapon_r at the zero grip", "worst %.6f" % sword_err)
    cams = camera.our_cameras()
    cam_bone = bones.get("camera_bone")
    gate(25, len(cams) == 1 and cam_bone and camera.our_constraints(cam_bone)
         and errors2["camera_bone"] is not None and errors2["camera_bone"] < 0.02,
         "one camera again, camera_bone on the reference", "%d camera(s), worst %.6f" % (
             len(cams), _fmt(errors2["camera_bone"])))
    left = [ns for ns in (cmds.namespaceInfo(":", listOnlyNamespaces=True) or [])
            if ns not in ("UI", "shared")]
    gate(26, not left, "no namespace left behind", str(left))

    cmds.select("FKWrist_R", replace=True)
    gate(27, skeleton.current_root() == "|root", "resolver: a rig control selected -> the rig")
    cmds.select(weapon, replace=True)
    gate(28, skeleton.current_root() == "|root", "resolver: the sword selected -> the rig (a mesh says nothing)")
    stray = cmds.createNode("joint", name="stray_root")
    cmds.createNode("joint", name="stray_child", parent=stray)
    cmds.select(clear=True)
    r_none = skeleton.current_root()
    cmds.select("stray_child", replace=True)
    r_stray = skeleton.current_root()
    cmds.delete(stray)
    cmds.select(clear=True)
    gate(29, r_none == "|root" and r_stray == "|stray_root",
         "resolver: a stray skeleton loses to the rig unless selected", "%s / %s" % (r_none, r_stray))

    out = os.path.join(tempfile.gettempdir(), "verify_rig_pipeline_export.fbx")
    if os.path.exists(out):
        os.remove(out)
    export_root = animexport.resolve_root()
    export_info = animexport.export_hierarchy(out)
    gate(30, export_root == "|root" and os.path.isfile(out) and os.path.getsize(out) > 0
         and export_info.get("joints") == 93,
         "Export FBX: the rig's skeleton, 93 bones, a file on disk",
         "%s, %d bytes" % (export_root, os.path.getsize(out) if os.path.isfile(out) else 0))

    failed = RESULTS.count(False)
    print("\n%d of %d gates failed (%.0f s)" % (failed, len(RESULTS), time.time() - t_all))
    return failed


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        traceback.print_exc()
        code = 99
    sys.stdout.flush()
    try:
        maya.standalone.uninitialize()   # a bare os._exit trips Maya's crash handler
    except Exception:
        pass
    os._exit(1 if code else 0)
