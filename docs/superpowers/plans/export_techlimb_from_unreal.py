"""The Tech Limb plate out of the animator's Atone project, into sources/armor/.

    mayapy export_techlimb_from_unreal.py

2026-10-01, the animator: «Давай из нашего aton game он сейчас открыт, достанем technolimb сам его
fbx и добавим его ... в наши ассеты с возможностью одеть» -- the Atone editor open, Remote
Execution on. Asked which mesh: the plate only (`SM_Shield_Test`, what BP_Techlimb always shows on
the forearm; the two skeletal shields are not taken). Talks to the editor through
maya_uebridge.uelink (stdlib; no Maya scene is touched) and writes:

- `sources/armor/SM_Shield_Test.fbx` -- the static mesh as Unreal exports it;
- `sources/armor/techlimb_ue.json` -- what places it: DA_Techlimb's equip socket, BP_Techlimb's
  component offset, the material's colour, the plate's render vertices in mesh space, in
  `lowerarm_l`'s space after the offset, and in component space on SK_Mannequin_proto's reference
  pose (Unreal's own transforms do the arithmetic: `MathLibrary.transform_location`), plus every
  bone's reference-pose position and axes.

The game attaches the actor with SnapToTargetNotIncludingScale to `equip_socket` on the character
mesh (UEquipmentComponent::AttachActorToSocket), and neither SKM_Manny_Simple has a socket of that
name: the actor's root stands ON the bone. Refuses (raises) when the editor does not answer or the
assets no longer carry what this was measured on.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
from maya_uebridge import uelink  # noqa: E402

OUT_DIR = os.path.join(REPO, "sources", "armor").replace("\\", "/")
REPLY = OUT_DIR + "/_export_reply.json"

UE = r'''
import json, os, unreal
DIR = __DIR__
R = {"ok": False, "error": ""}
DA = "/Game/Characters/Presets/TechLimb/DA_Techlimb"
BP = "/Game/Items/Weapons/BP_Techlimb"
SM = "/Game/Prototype/Meshes/SM_Shield_Test"
MESH = "/Game/Prototype/Characters/UE5_Mannequins/SKM_Manny_Simple_3p"

def vec(v):
    return [v.x, v.y, v.z]

try:
    da = unreal.load_asset(DA)
    R["socket"] = str(da.get_editor_property("equip_socket"))
    if R["socket"] != "lowerarm_l":
        raise RuntimeError("DA_Techlimb equips on %s, measured on lowerarm_l" % R["socket"])
    bp = unreal.load_asset(BP)
    subsys = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    comp = None
    for handle in subsys.k2_gather_subobject_data_for_blueprint(bp):
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
        if obj is not None and obj.get_class().get_name() == "StaticMeshComponent":
            sm = obj.get_editor_property("static_mesh")
            if sm is not None and sm.get_path_name().split(".")[0] == SM:
                comp = obj
    if comp is None:
        raise RuntimeError("BP_Techlimb holds no StaticMeshComponent with " + SM)
    loc = comp.get_editor_property("relative_location")
    rot = comp.get_editor_property("relative_rotation")
    scl = comp.get_editor_property("relative_scale3d")
    R["placement"] = {"location": vec(loc), "rotation": [rot.pitch, rot.yaw, rot.roll],
                      "scale": vec(scl)}
    rel = unreal.Transform(loc, rot, scl)
    mats = comp.get_editor_property("override_materials")
    mat = mats[0] if mats else None
    R["material"] = mat.get_path_name().split(".")[0] if mat else None
    if mat is not None:
        expr = unreal.MaterialEditingLibrary.get_material_property_input_node(
            mat, unreal.MaterialProperty.MP_BASE_COLOR)
        if expr is not None and expr.get_class().get_name() == "MaterialExpressionConstant3Vector":
            c = expr.get_editor_property("constant")
            R["colour"] = [c.r, c.g, c.b]

    skel = unreal.load_asset(MESH).get_editor_property("skeleton")
    R["skeleton"] = skel.get_path_name().split(".")[0]
    pose = unreal.AnimPoseExtensions.get_reference_pose(skel)
    R["bones"] = {}
    for name in unreal.AnimPoseExtensions.get_bone_names(pose):
        t = unreal.AnimPoseExtensions.get_ref_bone_pose(pose, name, unreal.AnimPoseSpaces.WORLD)
        R["bones"][str(name)] = {
            "t": vec(t.translation),
            "x": vec(unreal.MathLibrary.transform_direction(t, unreal.Vector(1, 0, 0)).normal()),
            "y": vec(unreal.MathLibrary.transform_direction(t, unreal.Vector(0, 1, 0)).normal()),
            "z": vec(unreal.MathLibrary.transform_direction(t, unreal.Vector(0, 0, 1)).normal())}
    bone = unreal.AnimPoseExtensions.get_ref_bone_pose(pose, "lowerarm_l", unreal.AnimPoseSpaces.WORLD)

    sm = unreal.load_asset(SM)
    section = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(sm, 0, 0)
    R["verts_mesh"], R["verts_bone"], R["verts_cs"] = [], [], []
    for v in section[0]:
        b = unreal.MathLibrary.transform_location(rel, v)
        R["verts_mesh"].append(vec(v))
        R["verts_bone"].append(vec(b))
        R["verts_cs"].append(vec(unreal.MathLibrary.transform_location(bone, b)))
    R["triangles"] = len(section[1]) // 3

    fbx = DIR + "/SM_Shield_Test.fbx"
    if os.path.isfile(fbx):
        os.remove(fbx)
    task = unreal.AssetExportTask()
    task.set_editor_property("object", sm)
    task.set_editor_property("filename", fbx)
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    options = unreal.FbxExportOption()
    options.set_editor_property("ascii", False)
    options.set_editor_property("collision", False)
    options.set_editor_property("level_of_detail", False)
    task.set_editor_property("options", options)
    unreal.Exporter.run_asset_export_task(task)
    R["fbx_ok"] = os.path.isfile(fbx) and os.path.getsize(fbx) > 0
    R["ok"] = True
except Exception:
    import traceback
    R["error"] = traceback.format_exc()
with open(DIR + "/_export_reply.json", "w") as h:
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
if len(reply["verts_mesh"]) != 1526:
    raise RuntimeError("SM_Shield_Test has %d render vertices, measured 1526" % len(reply["verts_mesh"]))
record = dict((k, reply[k]) for k in ("socket", "placement", "material", "colour", "skeleton",
                                      "bones", "verts_mesh", "verts_bone", "verts_cs", "triangles"))
with open(OUT_DIR + "/techlimb_ue.json", "w") as handle:
    json.dump(record, handle, indent=0, sort_keys=True)
print("socket %s, placement %s" % (record["socket"], record["placement"]))
print("colour %s, %d bones, %d vertices, %d triangles, fbx %.1f KB" % (
    record.get("colour"), len(record["bones"]), len(record["verts_mesh"]), record["triangles"],
    os.path.getsize(OUT_DIR + "/SM_Shield_Test.fbx") / 1e3))
