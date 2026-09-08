"""Many rigs in one scene, in mayapy STANDALONE.

Never in the animator's open Maya: this adds rigs, imports clips and deletes
skeletons. Run:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_many_rigs.py

What it proves (spec: docs/superpowers/specs/2026-09-08-many-rigs-design.md):

  phase 1  two REFERENCES: each clip on its own skeleton, hand_r / root /
           camera_bone sampled at six frames, the skeleton deleted. Every
           expectation below is computed from these, never typed.
  phase 2  Add Character: the rig arrives in its own namespace, selected.
  phase 3  IMPORT «onto a NEW rig»: a second rig, clip B retargeted onto it,
           the FIRST rig unmoved to 0.000, one camera on the new rig's bone.
  phase 4  IMPORT «onto the rig» with rig A's control selected: clip A onto
           rig A, rig B untouched, two cameras each on its own bone.
  phase 5  the resolver: two rigs and nothing selected refuses by name (and
           so does IMPORT, before anything is exported), a rig's mesh means
           its rig, two rigs selected is no answer.
  phase 6  the ONE Retarget button on a hand-imported skeleton: source bone
           plus a control of rig B selected, the take replaced, the source
           kept, rig A untouched.
  phase 7  Export FBX of rig B: 93 joints, and the file carries PLAIN bone
           names (re-imported into a check namespace), while the rig's own
           joints keep their namespace.
  phase 8  a weapon on rig B lands in rig B's hand and drives rig B's
           weapon_r; rig A has none.
  phase 9  a LEGACY scene: the rig file imported into the ROOT namespace is
           still a rig (namespace ""), and IMPORT retargets onto it.
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
CLIP_A = "C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_1P.FBX"
CLIP_B = "C:/!!!Work/Animations/Export/ShortSword_Walk_1P.fbx"
WATCHED = ("hand_r", "root", "camera_bone")

if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)
for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(plugin, quiet=True)
cmds.currentUnit(time="ntsc")

import maya_rigs  # noqa: E402
import maya_rig_retarget  # noqa: E402
from maya_scenesetup import attach, bonedrive, camera, catalog, character, skeleton  # noqa: E402
from maya_uebridge import animexport, animimport, rigimport  # noqa: E402

RESULTS = []


def gate(number, ok, text, detail=""):
    RESULTS.append(bool(ok))
    line = "%s %2d %s" % ("PASS" if ok else "FAIL", number, text)
    if detail:
        line += "   [%s]" % detail
    print(line)
    return bool(ok)


def _fmt(value):
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


def reference_for(clip, namespace):
    """Import a clip on its own skeleton, sample WATCHED, delete it."""
    info = animimport.import_clip(clip, namespace, set_timeline=False, merge=False)
    root = namespace_root(namespace)
    start, end = info["start"], info["end"]
    frames = sorted(set(int(round(start + (end - start) * k / 5.0)) for k in range(6)))
    bones = bones_under(root) if root else {}
    ref = {}
    for name in WATCHED:
        if name in bones:
            ref[name] = at_frames(frames, lambda n=name: world(bones[n]))
    cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
    return ref, frames, info


def compare(reference, frames, bones, names):
    out = {}
    for name in names:
        if name not in bones or name not in reference:
            out[name] = None
            continue
        samples = at_frames(frames, lambda: world(bones[name]))
        out[name] = max(worst(samples[f], reference[name][f]) for f in frames)
    return out


def snapshot(bones, frames, names):
    return dict((n, at_frames(frames, lambda: world(bones[n]))) for n in names if n in bones)


def drift(before, bones, frames):
    return max(max(worst(world_at, before[n][f]) for f, world_at in
                   at_frames(frames, lambda: world(bones[n])).items()) for n in before)


def rig_by_ns(namespace):
    return maya_rigs.find(namespace)


def main():
    t_all = time.time()
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    gate(1, not maya_rigs.rigs() and not cmds.ls(type="joint"), "an empty scene: no rig, no joints")

    # ------------------------------------------------------------ phase 1
    ref_a, frames_a, info_a = reference_for(CLIP_A, "refA")
    ref_b, frames_b, info_b = reference_for(CLIP_B, "refB")
    gate(2, all(n in ref_a for n in WATCHED) and all(n in ref_b for n in WATCHED)
         and not cmds.ls(type="joint"),
         "two references sampled and deleted",
         "A frames %g..%g (%s), B frames %g..%g (%s)" % (
             info_a["start"], info_a["end"], sorted(ref_a), info_b["start"], info_b["end"], sorted(ref_b)))
    # The two clips must differ, or "the other rig is unmoved" proves nothing.
    apart = worst(ref_a["hand_r"][frames_a[-1]], ref_b["hand_r"][frames_b[-1]])
    gate(3, apart > 1.0, "the two clips end with hand_r in different places", "%.3f" % apart)

    # ------------------------------------------------------------ phase 2
    t0 = time.time()
    text = character.add_character(catalog.default_rig())
    print("    ADD (%.1f s): %s" % (time.time() - t0, text))
    rigs = maya_rigs.rigs()
    gate(4, "added as Manny_Rig" in text and len(rigs) == 1 and rigs[0].namespace == "Manny_Rig"
         and rigs[0].skeleton_root == "|Manny_Rig:root" and rigs[0].group == "|Manny_Rig:Group",
         "Add Character: the rig in its own namespace, group and skeleton found",
         repr(rigs[0]._replace(control_set="...", main="...")) if rigs else "none")
    gate(5, (cmds.ls(selection=True, long=True) or []) == [rigs[0].main] if rigs else False,
         "the new rig's Main is selected: it is the current rig",
         str(cmds.ls(selection=True)))
    rig_a = rigs[0]
    bones_a = bones_under(rig_a.skeleton_root)
    rest_a = snapshot(bones_a, frames_b, ("hand_r", "spine_01", "root"))

    # ------------------------------------------------------------ phase 3
    t0 = time.time()
    text = rigimport.import_and_retarget(CLIP_B, "ClipB", set_timeline=True, target="new_rig")
    print("    IMPORT new_rig (%.1f s): %s" % (time.time() - t0, text))
    rigs = maya_rigs.rigs()
    rig_b = rig_by_ns("Manny_Rig1")
    gate(6, "added as Manny_Rig1" in text and "retargeted onto Manny_Rig1" in text
         and "deleted" in text and len(rigs) == 2 and rig_b is not None,
         "IMPORT onto a NEW rig: a second rig, clip B on it, source deleted",
         "rigs: %s" % [r.namespace for r in rigs])
    bones_b = bones_under(rig_b.skeleton_root) if rig_b else {}
    err_b = compare(ref_b, frames_b, bones_b, ("hand_r", "root", "camera_bone"))
    gate(7, err_b["hand_r"] is not None and err_b["hand_r"] < 0.05,
         "rig B's hand_r on reference B", "worst %s" % _fmt(err_b["hand_r"]))
    gate(8, err_b["root"] is not None and err_b["root"] < 0.02 and err_b["camera_bone"] is not None
         and err_b["camera_bone"] < 0.02, "rig B's root motion and camera_bone on reference B",
         "root %s, camera_bone %s" % (_fmt(err_b["root"]), _fmt(err_b["camera_bone"])))
    moved_a = drift(rest_a, bones_a, frames_b)
    gate(9, moved_a < 1e-6, "rig A unmoved by rig B's import", "worst %.9f" % moved_a)
    cams = camera.our_cameras()
    cam_b = bones_b.get("camera_bone")
    gate(10, len(cams) == 1 and cams[0].split("|")[-1] == "Manny_Rig1:" + camera.CAMERA_NAME
         and cam_b and camera.camera_for(cam_b) == cams[0],
         "one camera, in rig B's namespace, driving rig B's camera_bone", str(cams))
    gate(11, not cmds.objExists("Manny_Rig1:MoCapConstraints") and not cmds.objExists("Manny_Rig:MoCapConstraints")
         and not cmds.namespace(exists="ClipB"), "no holder and no source namespace left")

    # ------------------------------------------------------------ phase 4
    rest_b = snapshot(bones_b, frames_a, ("hand_r", "spine_01"))
    cmds.select("Manny_Rig:FKWrist_R", replace=True)
    t0 = time.time()
    text = rigimport.import_and_retarget(CLIP_A, "ClipA", set_timeline=True, target="rig")
    print("    IMPORT rig (%.1f s): %s" % (time.time() - t0, text))
    gate(12, "retargeted onto Manny_Rig," in text and "added" not in text and len(maya_rigs.rigs()) == 2,
         "IMPORT onto the SELECTED rig: clip A onto rig A, no third rig")
    err_a = compare(ref_a, frames_a, bones_a, ("hand_r", "root", "camera_bone"))
    gate(13, err_a["hand_r"] is not None and err_a["hand_r"] < 0.05 and err_a["root"] is not None
         and err_a["root"] < 0.02, "rig A's hand_r and root on reference A",
         "hand_r %s, root %s" % (_fmt(err_a["hand_r"]), _fmt(err_a["root"])))
    # rig B still plays clip B: its keyed track is what the snapshot holds
    moved_b = drift(rest_b, bones_b, frames_a)
    gate(14, moved_b < 1e-6, "rig B untouched by rig A's import", "worst %.9f" % moved_b)
    cams = camera.our_cameras()
    cam_a = bones_a.get("camera_bone")
    gate(15, len(cams) == 2 and camera.camera_for(cam_a) and camera.camera_for(cam_b)
         and camera.camera_for(cam_a) != camera.camera_for(cam_b)
         and camera.camera_for(cam_a).split("|")[-1] == "Manny_Rig:" + camera.CAMERA_NAME,
         "two cameras, each driving its own rig's camera_bone",
         "%s" % [c.split("|")[-1] for c in cams])
    offset = camera.rotation_only(camera.AXIS_OFFSET)
    cam_err = max(worst(world(camera.camera_for(cam_a)), camera.placed_matrix(world(cam_a), offset))
                  for _ in at_frames(frames_a[:3], lambda: None))
    gate(16, cam_err < 1e-3, "rig A's camera sits in its camera_bone's transform", "worst %.6f" % cam_err)

    # ------------------------------------------------------------ phase 5
    cmds.select(clear=True)
    rig, why = maya_rigs.current_rig()
    gate(17, rig is None and "Manny_Rig, Manny_Rig1" in why and skeleton.current_root() is None,
         "two rigs and nothing selected: refused by name", why)
    before_ns = set(cmds.namespaceInfo(":", listOnlyNamespaces=True) or [])
    text = rigimport.import_and_retarget(CLIP_A, "ClipX", set_timeline=False, target="rig")
    gate(18, text == why and set(cmds.namespaceInfo(":", listOnlyNamespaces=True) or []) == before_ns,
         "IMPORT onto the rig with two rigs and no selection refuses before importing", text)
    mesh = cmds.ls("Manny_Rig1:Skin_3p", long=True) or []
    cmds.select(mesh[0] if mesh else "Manny_Rig1:root", replace=True)
    gate(19, skeleton.current_root() == rig_b.skeleton_root and maya_rigs.current_rig()[0] == rig_b,
         "a rig's MESH selected means that rig", str(mesh))
    cmds.select(["Manny_Rig:FKWrist_R", "Manny_Rig1:FKWrist_R"], replace=True)
    gate(20, maya_rigs.current_rig()[0] is None and skeleton.current_root() is None,
         "two rigs selected is no answer")

    # ------------------------------------------------------------ phase 6
    info = animimport.import_clip(CLIP_A, "hand", set_timeline=True, merge=False)
    src_root = namespace_root("hand")
    rest_a2 = snapshot(bones_a, frames_a, ("hand_r", "spine_01"))
    cmds.select([src_root, "Manny_Rig1:Main"], replace=True)
    t0 = time.time()
    text = maya_rig_retarget.retarget()
    print("    RETARGET button (%.1f s): %s" % (time.time() - t0, text.replace("\n", " / ")))
    gate(21, text.startswith("Manny_Rig1: ") and "previous take cleared" in text
         and "retarget connected" in text and "baked" in text and "disconnected" in text,
         "the one Retarget button: reset, connect, bake, disconnect on the SELECTED rig")
    err_b2 = compare(ref_a, frames_a, bones_b, ("hand_r", "root"))
    gate(22, err_b2["hand_r"] is not None and err_b2["hand_r"] < 0.05,
         "rig B now plays clip A (the take replaced)", "worst %s" % _fmt(err_b2["hand_r"]))
    gate(23, cmds.namespace(exists="hand") and cmds.objExists(src_root)
         and not cmds.objExists("Manny_Rig1:MoCapConstraints"),
         "the hand-imported source is KEPT and the holder is gone")
    gate(24, drift(rest_a2, bones_a, frames_a) < 1e-6, "rig A untouched by the button on rig B")
    cams = camera.our_cameras()
    gate(25, len(cams) == 2, "still two cameras (rig B's rebuilt, not doubled)", str(len(cams)))

    # ------------------------------------------------------------ phase 7
    out = os.path.join(tempfile.gettempdir(), "verify_many_rigs_export.fbx")
    if os.path.exists(out):
        os.remove(out)
    cmds.select("Manny_Rig1:Main", replace=True)
    export_root = animexport.resolve_root()
    export_info = animexport.export_hierarchy(out)
    gate(26, export_root == rig_b.skeleton_root and os.path.isfile(out) and export_info.get("joints") == 93,
         "Export FBX: rig B's skeleton, 93 bones", "%s -> %s" % (export_root, export_info.get("root")))
    gate(27, cmds.objExists("|Manny_Rig1:root|Manny_Rig1:pelvis") and cmds.objExists("|Manny_Rig:root"),
         "after the export every joint wears its namespace again")
    animimport.import_clip(out, "chk", set_timeline=False, merge=False)
    chk = [j.split("|")[-1] for j in cmds.ls("chk:*", type="joint", long=True)]
    nested = [n for n in chk if n.count(":") > 1]
    gate(28, len(chk) >= 90 and "chk:root" in chk and "chk:pelvis" in chk and not nested,
         "the exported file carries PLAIN bone names (re-imported as chk:root, chk:pelvis)",
         "%d joints, nested %s" % (len(chk), nested[:3]))
    cmds.namespace(removeNamespace="chk", deleteNamespaceContent=True)

    # ------------------------------------------------------------ phase 8
    entry = catalog.by_key("LongSword_02")
    cmds.select("Manny_Rig1:Main", replace=True)
    root = skeleton.current_root()
    bone = skeleton.resolve_bone(root, "weapon_r")
    hand = attach.parent_bone(bone)
    weapon, note = attach.attach(entry, hand, bone)
    gate(29, root == rig_b.skeleton_root and bone and bone.startswith("|Manny_Rig1:root")
         and weapon and bonedrive.driving_weapon(bone) == weapon
         and not bonedrive.driving_weapon(bones_a["weapon_r"]),
         "a weapon on rig B lands in rig B's hand and drives rig B's weapon_r only",
         "%s %s" % (weapon, note))

    # ------------------------------------------------------------ phase 9
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    path = catalog.character_file(catalog.default_rig())
    cmds.file(path, i=True, type="mayaAscii", ignoreVersion=True)
    rigs = maya_rigs.rigs()
    gate(30, len(rigs) == 1 and rigs[0].namespace == "" and rigs[0].skeleton_root == "|root"
         and rigs[0].group == "|Group" and maya_rigs.label(rigs[0]) == "Group",
         "a LEGACY scene: the rig in the root namespace is found", repr(rigs[0]._replace(main="...")) if rigs else "")
    t0 = time.time()
    text = rigimport.import_and_retarget(CLIP_B, "ClipB", set_timeline=True, target="rig")
    print("    IMPORT legacy (%.1f s): %s" % (time.time() - t0, text))
    bones_l = bones_under("|root")
    err_l = compare(ref_b, frames_b, bones_l, ("hand_r", "root"))
    gate(31, "retargeted onto Group" in text and err_l["hand_r"] is not None and err_l["hand_r"] < 0.05
         and cmds.objExists("SceneSetup_camera") and not cmds.objExists("MoCapConstraints"),
         "IMPORT onto the legacy rig: retargeted, camera under the old name, holder gone",
         "hand_r %s" % _fmt(err_l["hand_r"]))
    cmds.select("FKWrist_R", replace=True)
    gate(32, skeleton.current_root() == "|root" and maya_rigs.current_rig()[0] == maya_rigs.rigs()[0],
         "the legacy rig's control means the legacy rig")

    failed = RESULTS.count(False)
    print("\n%d of %d gates failed (%.0f s)" % (failed, len(RESULTS), time.time() - t_all))
    return failed


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    try:
        maya.standalone.uninitialize()   # a bare os._exit trips Maya's crash handler
    except Exception:
        pass
    os._exit(1 if code else 0)
