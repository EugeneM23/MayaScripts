"""Atone's main hero out of the open editor, into sources/mainhero/.

    mayapy export_mainhero_from_unreal.py

2026-11-20, the animator: «взяти актуального головного персонажа з проекту Атон і додати в плагін
Skeldar ... і скелет і ріг і одяг, наплічники окремо».  The current hero is what
/Game/Characters/BP_Character wears: /Game/Characters/Main_Hero/MainHero/SK_MainHeroProto_Skinned4
(on skeleton SK_Mannequin_proto).  Through maya_uebridge.uelink; no Maya scene is touched.  Writes:

- sources/mainhero/SK_MainHero_Full.fbx -- LOD0, all 19 material slots. Unreal's own FBX export of
  the asset drops the six sections that run cloth simulation (cape, skirts, three chain strands: 59573
  of 153534 triangles), so the mesh is copied through Geometry Script (copy_mesh_from_skeletal_mesh)
  into a temporary skeletal mesh on the same skeleton with the same slots and the original vertex
  order (/Game/__skeldar_export, deleted again), and that is exported;
- sources/mainhero/textures/<T_...>.png -- every texture the slots' materials name, SOURCE data;
- sources/mainhero/mainhero_materials.json -- the slots, each material's parameters, the sections.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
from maya_uebridge import uelink  # noqa: E402

OUT_DIR = os.path.join(REPO, "sources", "mainhero").replace("\\", "/")
REPLY = os.path.join(OUT_DIR, "_export_reply.json").replace("\\", "/")
MESH = "/Game/Characters/Main_Hero/MainHero/SK_MainHeroProto_Skinned4"

UE = r'''
import json, os, unreal
DIR = __DIR__
MESH = __MESH__
R = {"ok": False, "error": "", "slots": [], "materials": {}, "textures": {}, "sections": []}
mel = unreal.MaterialEditingLibrary

def export(obj, filename, options=None):
    if os.path.isfile(filename):
        os.remove(filename)
    task = unreal.AssetExportTask()
    task.set_editor_property("object", obj)
    task.set_editor_property("filename", filename)
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    if options is not None:
        task.set_editor_property("options", options)
    unreal.Exporter.run_asset_export_task(task)
    return os.path.isfile(filename) and os.path.getsize(filename) > 0

def params(mi):
    out = {"class": mi.get_class().get_name(), "scalars": {}, "vectors": {}, "textures": {}}
    if isinstance(mi, unreal.MaterialInstance):
        out["parent"] = mi.get_editor_property("parent").get_path_name().split(".")[0]
        for n in mel.get_scalar_parameter_names(mi):
            out["scalars"][str(n)] = mel.get_material_instance_scalar_parameter_value(mi, n)
        for n in mel.get_vector_parameter_names(mi):
            v = mel.get_material_instance_vector_parameter_value(mi, n)
            out["vectors"][str(n)] = [v.r, v.g, v.b, v.a]
        for n in mel.get_texture_parameter_names(mi):
            t = mel.get_material_instance_texture_parameter_value(mi, n)
            out["textures"][str(n)] = t.get_path_name().split(".")[0] if t else None
    try:
        out["used"] = [t.get_path_name().split(".")[0] for t in mel.get_used_textures(mi)]
    except Exception as e:
        out["used"] = []
    return out

try:
    mesh = unreal.load_asset(MESH)
    for s in mesh.get_editor_property("materials"):
        mi = s.get_editor_property("material_interface")
        path = mi.get_path_name().split(".")[0] if mi else ""
        R["slots"].append([str(s.get_editor_property("material_slot_name")), path])
        if mi and path not in R["materials"]:
            R["materials"][path] = params(mi)
    sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    try:
        n = sub.get_num_sections(mesh, 0)
        for i in range(n):
            info = {"index": i}
            for name in ("is_section_using_cloth",):
                try:
                    info["cloth"] = bool(getattr(mesh, name)(i, True)) if hasattr(mesh, name) else None
                except Exception as e:
                    info["cloth"] = str(e)
            R["sections"].append(info)
    except Exception as e:
        R["sections"] = str(e)
    os.makedirs(DIR + "/textures", exist_ok=True)
    tex = set()
    for info in R["materials"].values():
        tex.update(p for p in info["textures"].values() if p)
        tex.update(info.get("used") or [])
    for tp in sorted(tex):
        if not tp.startswith("/Game"):
            continue
        t = unreal.load_asset(tp)
        if not isinstance(t, unreal.Texture2D):
            continue
        fn = DIR + "/textures/" + tp.rsplit("/", 1)[1] + ".png"
        R["textures"][tp] = {"file": fn, "ok": export(t, fn),
                             "size": [t.blueprint_get_size_x(), t.blueprint_get_size_y()],
                             "srgb": t.get_editor_property("srgb")}
    options = unreal.FbxExportOption()
    for name, value in (("ascii", False), ("export_morph_targets", False),
                        ("level_of_detail", False), ("collision", False), ("vertex_color", True)):
        options.set_editor_property(name, value)
    TMP_DIR = "/Game/__skeldar_export"
    EAL = unreal.EditorAssetLibrary
    AU = unreal.GeometryScript_AssetUtils
    dm = unreal.DynamicMesh()
    AU.copy_mesh_from_skeletal_mesh(mesh, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                    unreal.GeometryScriptMeshReadLOD())
    R["triangles"] = dm.get_triangle_count()
    mats, names = AU.get_material_list_from_skeletal_mesh(mesh)
    opts = unreal.GeometryScriptCreateNewSkeletalMeshAssetOptions()
    mp = unreal.Map(unreal.Name, unreal.MaterialInterface)
    for n_, m_ in zip(names, mats):
        mp[n_] = m_
    opts.set_editor_property("materials", mp)
    opts.set_editor_property("use_original_vertex_order", True)
    try:
        full, _pin = unreal.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(
            dm, mesh.get_editor_property("skeleton"), TMP_DIR + "/SK_MainHero_Full", opts)
        R["fbx"] = DIR + "/SK_MainHero_Full.fbx"
        R["fbx_ok"] = export(full, R["fbx"], options)
        R["full_slots"] = [str(s.material_slot_name) for s in full.get_editor_property("materials")]
    finally:
        for a in (EAL.list_assets(TMP_DIR) if EAL.does_directory_exist(TMP_DIR) else []):
            EAL.delete_asset(a.split(".")[0])
        if EAL.does_directory_exist(TMP_DIR):
            EAL.delete_directory(TMP_DIR)
    R["ok"] = True
except Exception:
    import traceback
    R["error"] = traceback.format_exc()
with open(DIR + "/_export_reply.json", "w") as h:
    json.dump(R, h, indent=1, default=str)
'''.replace("__DIR__", repr(OUT_DIR)).replace("__MESH__", repr(MESH))

os.makedirs(OUT_DIR, exist_ok=True)
reply = uelink.run_script(UE, REPLY, timeout=30, project="Atone")
if not reply.get("ok"):
    raise RuntimeError(reply.get("error") or "the editor said nothing")
bad = [tp for tp, t in reply["textures"].items() if not t["ok"]]
if bad or not reply.get("fbx_ok"):
    raise RuntimeError("did not land on disk: %s%s" % (bad, "" if reply.get("fbx_ok") else " + the FBX"))
record = {"mesh": MESH, "slots": reply["slots"], "materials": reply["materials"],
          "sections": reply["sections"],
          "textures": dict((tp.rsplit("/", 1)[1], {"size": t["size"], "srgb": t["srgb"], "path": tp})
                           for tp, t in reply["textures"].items())}
with open(os.path.join(OUT_DIR, "mainhero_materials.json"), "w") as handle:
    json.dump(record, handle, indent=1, sort_keys=True)
for tp, t in sorted(reply["textures"].items()):
    print("%-44s %4dx%-4d %6.1f MB" % (tp.rsplit("/", 1)[1], t["size"][0], t["size"][1],
                                      os.path.getsize(t["file"]) / 1e6))
if reply.get("full_slots") != [s for s, _p in reply["slots"]]:
    raise RuntimeError("the full copy's slots %s are not the hero's" % reply.get("full_slots"))
print("fbx %.1f MB, %d triangles" % (os.path.getsize(reply["fbx"]) / 1e6, reply["triangles"]))
for slot, path in reply["slots"]:
    m = reply["materials"].get(path, {})
    print("%-24s %-40s %s" % (slot, path.rsplit("/", 1)[-1], sorted(m.get("textures", {}).items())))
print("sections", reply["sections"])
