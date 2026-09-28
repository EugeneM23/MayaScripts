"""The Orc Marauder D out of the animator's Unreal project, into sources/orc/.

    mayapy export_orc_d_from_unreal.py

2026-09-28, the animator: «Давай добавим еще один вариант орка но на этот раз SK_Orc_Marauder_D
... и для этой версии сделаем материал с текстурами» -- with MyProject2 open in the editor and
Remote Execution on (Project Settings > Plugins > Python).  Talks to the editor through
maya_uebridge.uelink (stdlib; no Maya scene is touched) and writes:

- `sources/orc/SK_Orc_Marauder_D.fbx` -- the skeletal mesh, LOD0 only, its 56 morph targets;
- `sources/orc/textures/<T_...>.png` -- the seven textures the maps are made from, exported from
  each Texture2D's SOURCE data (the image as it was imported, at its own size -- not the platform
  compression): the body's colour, normal and tattoo mask, the cloth's colour (its alpha is the
  opacity mask) and normal, the eye's sclera and iris;
- `sources/orc/orc_d_materials.json` -- every parameter the maps are baked with, read off the
  material instances the mesh wears, plus the cloth master's opacity clip and the 64 samples of
  the `CA_Mannequin` curve atlas the body's tattoo colour is multiplied by (an atlas is not a
  texture the exporter writes).

Refuses (raises) if the editor does not answer, a texture did not land on disk, or the mesh does
not wear the four instances this was measured on.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
from maya_uebridge import uelink  # noqa: E402

OUT_DIR = os.path.join(REPO, "sources", "orc").replace("\\", "/")
REPLY = os.path.join(OUT_DIR, "_export_reply.json").replace("\\", "/")
TEXTURES = ("/Game/Orc_Marauder/Textures/T_Orc_Marauder_Body_BaseColor",
            "/Game/Orc_Marauder/Textures/T_Orc_Marauder_Body_Normal",
            "/Game/Orc_Marauder/Textures/T_Orc_Marauder_Body_Tatoo_Mask",
            "/Game/Orc_Marauder/Textures/T_Orc_Marauder_Cloth_BaseColor",
            "/Game/Orc_Marauder/Textures/T_Orc_Marauder_Cloth_Normal",
            "/Game/Orc_Marauder/Textures/Eye/T_Orc_Marauder_Eyes_ScleraBaseColor",
            "/Game/Orc_Marauder/Textures/Eye/T_Orc_Marauder_Eyes_BaseColor")

UE = r'''
import json, os, unreal
DIR = __DIR__
TEXTURES = __TEXTURES__
MESH = "/Game/Orc_Marauder/Meshes/SK_Orc_Marauder_D"
R = {"ok": False, "error": "", "slots": [], "materials": {}, "textures": {}}

def export(obj, filename, options=None):
    if os.path.isfile(filename):
        os.remove(filename)
    task = unreal.AssetExportTask()
    task.set_editor_property("object", obj)
    task.set_editor_property("filename", filename)
    # automated/prompt are load-bearing: without them the editor raises a modal nobody can click
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    if options is not None:
        task.set_editor_property("options", options)
    unreal.Exporter.run_asset_export_task(task)
    return os.path.isfile(filename) and os.path.getsize(filename) > 0

def params(mi):
    mel = unreal.MaterialEditingLibrary
    out = {"parent": mi.get_editor_property("parent").get_path_name().split(".")[0],
           "scalars": {}, "vectors": {}, "textures": {}}
    for n in mel.get_scalar_parameter_names(mi):
        out["scalars"][str(n)] = mel.get_material_instance_scalar_parameter_value(mi, n)
    for n in mel.get_vector_parameter_names(mi):
        v = mel.get_material_instance_vector_parameter_value(mi, n)
        out["vectors"][str(n)] = [v.r, v.g, v.b, v.a]
    for n in mel.get_texture_parameter_names(mi):
        t = mel.get_material_instance_texture_parameter_value(mi, n)
        out["textures"][str(n)] = t.get_path_name().split(".")[0] if t else None
    return out

try:
    mesh = unreal.load_asset(MESH)
    if mesh is None:
        raise RuntimeError("could not load " + MESH)
    for s in mesh.get_editor_property("materials"):
        mi = s.get_editor_property("material_interface")
        path = mi.get_path_name().split(".")[0]
        R["slots"].append([str(s.get_editor_property("material_slot_name")), path])
        if path not in R["materials"]:
            R["materials"][path] = params(mi)
    for path, info in list(R["materials"].items()):
        parent = unreal.load_asset(info["parent"])
        info["parent_clip"] = parent.get_editor_property("opacity_mask_clip_value")
        info["parent_two_sided"] = parent.get_editor_property("two_sided")
    atlas = unreal.load_asset("/Game/Orc_Marauder/Demo/Characters/Mannequins/Materials/Functions/CA_Mannequin")
    curve = list(atlas.get_editor_property("gradient_curves"))[0]
    R["atlas"] = [[c.r, c.g, c.b, c.a] for c in
                  (curve.get_linear_color_value((i + 0.5) / 64.0) for i in range(64))]
    os.makedirs(DIR + "/textures", exist_ok=True)
    for tp in TEXTURES:
        tex = unreal.load_asset(tp)
        fn = DIR + "/textures/" + tp.rsplit("/", 1)[1] + ".png"
        R["textures"][tp] = {"file": fn, "ok": export(tex, fn),
                             "size": [tex.blueprint_get_size_x(), tex.blueprint_get_size_y()],
                             "srgb": tex.get_editor_property("srgb")}
    options = unreal.FbxExportOption()
    for name, value in (("ascii", False), ("export_morph_targets", True),
                        ("level_of_detail", False), ("collision", False), ("vertex_color", True)):
        options.set_editor_property(name, value)
    R["fbx"] = DIR + "/SK_Orc_Marauder_D.fbx"
    R["fbx_ok"] = export(mesh, R["fbx"], options)
    R["ok"] = True
except Exception:
    import traceback
    R["error"] = traceback.format_exc()
with open(DIR + "/_export_reply.json", "w") as h:
    json.dump(R, h, indent=1, default=str)
'''.replace("__DIR__", repr(OUT_DIR)).replace("__TEXTURES__", repr(TEXTURES))

os.makedirs(OUT_DIR, exist_ok=True)
reply = uelink.run_script(UE, REPLY, timeout=15, project="MyProject2")
if not reply.get("ok"):
    raise RuntimeError(reply.get("error") or "the editor said nothing")
wanted = {"MI_Orc_Marauder_Body_A_Inst", "MI_Orc_Marauder_Cloth_Inst", "MI_Orc_Marauder_Eye_Inst",
          "MI_Orc_Marauder_Fur_Inst"}
worn = set(p.rsplit("/", 1)[1] for _slot, p in reply["slots"])
if worn != wanted:
    raise RuntimeError("the mesh wears %s, measured on %s" % (sorted(worn), sorted(wanted)))
bad = [tp for tp, t in reply["textures"].items() if not t["ok"]]
if bad or not reply.get("fbx_ok"):
    raise RuntimeError("did not land on disk: %s%s" % (bad, "" if reply.get("fbx_ok") else " + the FBX"))
record = {"slots": reply["slots"], "materials": reply["materials"], "atlas_CA_Mannequin": reply["atlas"],
          "textures": dict((tp.rsplit("/", 1)[1], {"size": t["size"], "srgb": t["srgb"]})
                           for tp, t in reply["textures"].items())}
with open(os.path.join(OUT_DIR, "orc_d_materials.json"), "w") as handle:
    json.dump(record, handle, indent=1, sort_keys=True)
for tp, t in sorted(reply["textures"].items()):
    print("%-44s %4dx%-4d %6.1f MB" % (tp.rsplit("/", 1)[1], t["size"][0], t["size"][1],
                                      os.path.getsize(t["file"]) / 1e6))
print("fbx %.1f MB, materials %s" % (os.path.getsize(reply["fbx"]) / 1e6, sorted(worn)))
