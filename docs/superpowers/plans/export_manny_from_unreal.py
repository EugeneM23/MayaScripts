"""UE5 Manny's textures out of the animator's Unreal project, into sources/manny/.

    mayapy export_manny_from_unreal.py

2026-09-30 (spec: docs/superpowers/specs/2026-09-30-manny-textured-design.md), the animator:
«Давай для нашего мени рига и скелета найдем текстуры и добавим их в проект точно так же как и для
орка» -- with MyProject2 open in the editor and Remote Execution on.  Talks to the editor through
maya_uebridge.uelink (stdlib; no Maya scene is touched) and writes:

- `sources/manny/SKM_Manny_Simple.fbx` -- the Orc Marauder pack's demo copy of the UE5 mannequin
  (`/Game/Orc_Marauder/Demo/Characters/Mannequins/Meshes/SKM_Manny_Simple`), LOD0: our `Skin_3p` is
  this mesh index for index (every UV equal), `Hands_1P` a cut of it; the FBX says which face wears
  which of its two material slots, which the shipped `.ma` files have lost;
- `sources/manny/textures/<T_...>.png` -- from each Texture2D's SOURCE data (the image as imported,
  4096^2 -- not the platform compression): both slots' base colour `D` and bevel normal `BN`, and the
  logo mask `T_UE_Logo_M` the torso's emissive is drawn from;
- `sources/manny/manny_materials.json` -- the slots, every parameter of the two instances, the
  master's blend mode and shading model, each texture's size and sRGB flag.

The template's own Manny (`/Game/Characters/Mannequins/`) is NOT used: its textures are 1024^2 and its
mesh's UVs stand 0.017 off ours.  Refuses (raises) if the editor does not answer, the mesh does not
wear the two instances this was measured on, or a file did not land on disk.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
from maya_uebridge import uelink  # noqa: E402

OUT_DIR = os.path.join(REPO, "sources", "manny").replace("\\", "/")
REPLY = os.path.join(OUT_DIR, "_export_reply.json").replace("\\", "/")
BASE = "/Game/Orc_Marauder/Demo/Characters/Mannequins/"
MESH = BASE + "Meshes/SKM_Manny_Simple"
TEXTURES = (BASE + "Textures/Manny/T_Manny_01_D", BASE + "Textures/Manny/T_Manny_01_BN",
            BASE + "Textures/Manny/T_Manny_02_D", BASE + "Textures/Manny/T_Manny_02_BN",
            BASE + "Textures/Shared/T_UE_Logo_M")
SLOTS = [["M_HeadLegs", BASE + "Materials/Instances/Manny/MI_Manny_01"],
         ["M_Torso", BASE + "Materials/Instances/Manny/MI_Manny_02"]]

UE = r'''
import json, os, unreal
DIR = __DIR__
TEXTURES = __TEXTURES__
MESH = __MESH__
R = {"ok": False, "error": "", "slots": [], "materials": {}, "textures": {}, "master": {}}
mel = unreal.MaterialEditingLibrary

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
    out = {"parent": mi.get_editor_property("parent").get_path_name().split(".")[0],
           "scalars": {}, "vectors": {}, "textures": {}, "switches": {}}
    for n in mel.get_scalar_parameter_names(mi):
        out["scalars"][str(n)] = mel.get_material_instance_scalar_parameter_value(mi, n)
    for n in mel.get_vector_parameter_names(mi):
        v = mel.get_material_instance_vector_parameter_value(mi, n)
        out["vectors"][str(n)] = [v.r, v.g, v.b, v.a]
    for n in mel.get_texture_parameter_names(mi):
        t = mel.get_material_instance_texture_parameter_value(mi, n)
        out["textures"][str(n)] = t.get_path_name().split(".")[0] if t else None
    for n in mel.get_static_switch_parameter_names(mi):
        out["switches"][str(n)] = mel.get_material_instance_static_switch_parameter_value(mi, n)
    return out

try:
    mesh = unreal.load_asset(MESH)
    if mesh is None:
        raise RuntimeError("could not load " + MESH)
    for s in mesh.get_editor_property("materials"):
        mi = s.get_editor_property("material_interface")
        path = mi.get_path_name().split(".")[0]
        R["slots"].append([str(s.get_editor_property("material_slot_name")), path])
        R["materials"][path] = params(mi)
    master = unreal.load_asset(R["materials"][R["slots"][0][1]]["parent"])
    while isinstance(master, unreal.MaterialInstance):
        master = master.get_editor_property("parent")
    R["master"] = {"path": master.get_path_name().split(".")[0],
                   "blend_mode": str(master.get_editor_property("blend_mode")),
                   "shading_model": str(master.get_editor_property("shading_model")),
                   "two_sided": master.get_editor_property("two_sided")}
    os.makedirs(DIR + "/textures", exist_ok=True)
    for tp in TEXTURES:
        tex = unreal.load_asset(tp)
        fn = DIR + "/textures/" + tp.rsplit("/", 1)[1] + ".png"
        R["textures"][tp] = {"file": fn, "ok": export(tex, fn), "srgb": tex.get_editor_property("srgb"),
                             "flip_green": tex.get_editor_property("flip_green_channel")}
    options = unreal.FbxExportOption()
    for name, value in (("ascii", False), ("export_morph_targets", False), ("level_of_detail", False),
                        ("collision", False), ("vertex_color", False)):
        options.set_editor_property(name, value)
    R["fbx"] = DIR + "/SKM_Manny_Simple.fbx"
    R["fbx_ok"] = export(mesh, R["fbx"], options)
    R["ok"] = True
except Exception:
    import traceback
    R["error"] = traceback.format_exc()
with open(DIR + "/_export_reply.json", "w") as h:
    json.dump(R, h, indent=1, default=str)
'''.replace("__DIR__", repr(OUT_DIR)).replace("__TEXTURES__", repr(TEXTURES)).replace("__MESH__", repr(MESH))


def png_size(path):
    with open(path, "rb") as handle:
        head = handle.read(24)
    return [int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")]


os.makedirs(OUT_DIR, exist_ok=True)
reply = uelink.run_script(UE, REPLY, timeout=15, project="MyProject2")
if not reply.get("ok"):
    raise RuntimeError(reply.get("error") or "the editor said nothing")
if reply["slots"] != SLOTS:
    raise RuntimeError("the mesh wears %s, measured on %s" % (reply["slots"], SLOTS))
bad = [tp for tp, t in reply["textures"].items() if not t["ok"]]
if bad or not reply.get("fbx_ok"):
    raise RuntimeError("did not land on disk: %s%s" % (bad, "" if reply.get("fbx_ok") else " + the FBX"))
record = {"slots": reply["slots"], "materials": reply["materials"], "master": reply["master"],
          "textures": dict((tp.rsplit("/", 1)[1], {"size": png_size(t["file"]), "srgb": t["srgb"],
                                                   "flip_green": t["flip_green"]})
                           for tp, t in reply["textures"].items())}
with open(os.path.join(OUT_DIR, "manny_materials.json"), "w") as handle:
    json.dump(record, handle, indent=1, sort_keys=True)
for tp, t in sorted(reply["textures"].items()):
    size = png_size(t["file"])
    print("%-24s %4dx%-4d srgb %-5s %6.1f MB" % (tp.rsplit("/", 1)[1], size[0], size[1], t["srgb"],
                                               os.path.getsize(t["file"]) / 1e6))
print("fbx %.1f MB; master %s" % (os.path.getsize(reply["fbx"]) / 1e6, reply["master"]))
