"""The Tech Limb's SKELETAL shield out of the animator's Atone project, into sources/armor/.

    mayapy export_techlimb_shield_from_unreal.py

2026-10-01, the evening, the animator on the plate: «Щит в сцене одевается совсем не так как в игре ...
в игре у нас есть скелет для щита». The shield the game animates is `SKM_Techlimb_Shield`
(skeleton `SK_Techlimb_Shield`: Root, Main, 36 rim joints), at identity on the techlimb actor's
root (BP_Techlimb_TestStartingRoster), which the equipment snaps onto `lowerarm_l`; `ABP_Shield`
plays the Block clips, which FORCE ROOT LOCK to the reference pose. Talks to the editor through
maya_uebridge.uelink and writes:

- `sources/armor/SKM_Techlimb_Shield.fbx` -- the skeletal mesh as Unreal exports it (skin, skeleton);
- `sources/armor/techlimb_shield_ue.json`:
  - every bone's parent and reference pose (local, and component space: translation + axes);
  - the Block Idle clip's local transforms at t = 0;
  - the game's Block Idle component pose: Root at its REFERENCE (the root lock), every other bone
    the clip's, composed by Unreal itself (`MathLibrary.compose_transforms`).

Refuses when the editor does not answer or the assets no longer carry what this was measured on.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
from maya_uebridge import uelink  # noqa: E402

OUT_DIR = os.path.join(REPO, "sources", "armor").replace("\\", "/")
REPLY = OUT_DIR + "/_export_shield_reply.json"

UE = r'''
import json, os, unreal
DIR = __DIR__
R = {"ok": False, "error": ""}
SKM = "/Game/Prototype/Animation/TechLimb/Shield/SKM_Techlimb_Shield"
IDLE = "/Game/Prototype/Animation/TechLimb/Shield/AS_Techlimb_Shield_Block_Idle_1P"
BP = "/Game/Tests/TechLimb/BP_Techlimb_TestStartingRoster"
DA = "/Game/Characters/Presets/TechLimb/DA_EquipmentItem_TechlimbTestStartingRoster"

def vec(v):
    return [v.x, v.y, v.z]

def frame(t):
    return {"t": vec(t.translation),
            "q": [t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w],
            "x": vec(unreal.MathLibrary.transform_direction(t, unreal.Vector(1, 0, 0)).normal()),
            "y": vec(unreal.MathLibrary.transform_direction(t, unreal.Vector(0, 1, 0)).normal()),
            "z": vec(unreal.MathLibrary.transform_direction(t, unreal.Vector(0, 0, 1)).normal()),
            "s": vec(t.scale3d)}

try:
    da = unreal.load_asset(DA)
    R["socket"] = str(da.get_editor_property("equip_socket"))
    if R["socket"] != "lowerarm_l":
        raise RuntimeError("the test techlimb equips on %s, measured on lowerarm_l" % R["socket"])
    subsys = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    comp = None
    for handle in subsys.k2_gather_subobject_data_for_blueprint(unreal.load_asset(BP)):
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(
            unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
        if obj is not None and obj.get_class().get_name() == "SkeletalMeshComponent":
            asset = obj.get_editor_property("skeletal_mesh_asset")
            if asset is not None and asset.get_path_name().split(".")[0] == SKM:
                comp = obj
    if comp is None:
        raise RuntimeError("BP_Techlimb_TestStartingRoster holds no SkeletalMeshComponent with " + SKM)
    loc, rot, scl = (comp.get_editor_property(p) for p in ("relative_location", "relative_rotation",
                                                          "relative_scale3d"))
    R["component"] = {"location": vec(loc), "rotation": [rot.pitch, rot.yaw, rot.roll], "scale": vec(scl),
                      "anim_class": str(comp.get_editor_property("anim_class"))}

    skm = unreal.load_asset(SKM)
    skel = skm.get_editor_property("skeleton")
    ref = unreal.AnimPoseExtensions.get_reference_pose(skel)
    names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(ref)]
    seq = unreal.load_asset(IDLE)
    R["idle_root_lock"] = [str(seq.get_editor_property("force_root_lock")),
                           str(seq.get_editor_property("root_motion_root_lock"))]
    idle = unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, 0.0, unreal.AnimPoseEvaluationOptions())
    R["bones"] = {}
    for n in names:
        R["bones"][n] = {
            "parent": str(unreal.AnimPoseExtensions.get_parent_bone_name(ref, n)) if hasattr(
                unreal.AnimPoseExtensions, "get_parent_bone_name") else "",
            "ref_local": frame(unreal.AnimPoseExtensions.get_ref_bone_pose(ref, n, unreal.AnimPoseSpaces.LOCAL)),
            "ref_cs": frame(unreal.AnimPoseExtensions.get_ref_bone_pose(ref, n, unreal.AnimPoseSpaces.WORLD)),
            "idle_local": frame(unreal.AnimPoseExtensions.get_bone_pose(idle, n, unreal.AnimPoseSpaces.LOCAL))}
    # the hierarchy, in case the API has no parent query: Root -> Main -> the rim
    for n, b in R["bones"].items():
        if not b["parent"] or b["parent"] == "None":
            b["parent"] = "" if n == "Root" else ("Root" if n == "Main" else "Main")
    # the game's Idle: Root locked at its reference, the rest the clip's, composed root-down
    cs = {}
    def compose(n):
        if n in cs:
            return cs[n]
        b = R["bones"][n]
        if n == "Root":
            local = unreal.AnimPoseExtensions.get_ref_bone_pose(ref, n, unreal.AnimPoseSpaces.LOCAL)
        else:
            local = unreal.AnimPoseExtensions.get_bone_pose(idle, n, unreal.AnimPoseSpaces.LOCAL)
        cs[n] = local if not b["parent"] else unreal.MathLibrary.compose_transforms(local, compose(b["parent"]))
        return cs[n]
    for n in names:
        R["bones"][n]["idle_cs"] = frame(compose(n))

    fbx = DIR + "/SKM_Techlimb_Shield.fbx"
    if os.path.isfile(fbx):
        os.remove(fbx)
    task = unreal.AssetExportTask()
    task.set_editor_property("object", skm)
    task.set_editor_property("filename", fbx)
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    options = unreal.FbxExportOption()
    for name, value in (("ascii", False), ("export_morph_targets", False), ("level_of_detail", False),
                        ("collision", False)):
        options.set_editor_property(name, value)
    task.set_editor_property("options", options)
    unreal.Exporter.run_asset_export_task(task)
    R["fbx_ok"] = os.path.isfile(fbx) and os.path.getsize(fbx) > 0
    R["ok"] = True
except Exception:
    import traceback
    R["error"] = traceback.format_exc()
with open(DIR + "/_export_shield_reply.json", "w") as h:
    json.dump(R, h)
'''.replace("__DIR__", repr(OUT_DIR))

os.makedirs(OUT_DIR, exist_ok=True)
reply = uelink.run_script(UE, REPLY, timeout=15, project="Atone")
if os.path.isfile(REPLY):
    os.remove(REPLY)
if not reply.get("ok"):
    raise RuntimeError(reply.get("error") or "the editor said nothing")
if not reply.get("fbx_ok"):
    raise RuntimeError("the FBX did not land on disk")
if len(reply["bones"]) != 38:
    raise RuntimeError("SK_Techlimb_Shield has %d bones, measured 38" % len(reply["bones"]))
record = dict((k, reply[k]) for k in ("socket", "component", "idle_root_lock", "bones"))
with open(OUT_DIR + "/techlimb_shield_ue.json", "w") as handle:
    json.dump(record, handle, indent=0, sort_keys=True)
main = record["bones"]["Main"]
print("socket %s, component %s, idle root lock %s" % (record["socket"], record["component"],
                                                     record["idle_root_lock"]))
print("Main in Block Idle, component space: %s" % [round(v, 3) for v in main["idle_cs"]["t"]])
print("%d bones, fbx %.1f KB" % (len(record["bones"]),
                                os.path.getsize(OUT_DIR + "/SKM_Techlimb_Shield.fbx") / 1e3))
