import csc, csc.app, os, json, traceback
from pycsc.general import wrapping

OUT = r"C:\Users\MY PC\AppData\Local\Temp\skeldar_cascade_probe"
FBX = os.path.join(OUT, "probe_clip.fbx")
RESULT = os.path.join(OUT, "probe_result.json")
result = {}

def attempt(key, fn):
    try:
        value = fn()
        result[key] = repr(value)
        return value
    except Exception:
        result[key] = "ERR " + traceback.format_exc(limit=2)
        return None

app = csc.app.get_application()
attempt("tools", lambda: app.get_tools_manager().get_tool("FbxSceneLoader") is not None)
attempt("current_scene", lambda: type(app.current_scene()).__name__)
attempt("wrapping_current", lambda: type(wrapping.get_current_scene()).__name__)
attempt("wrapping_methods", lambda: [m for m in dir(wrapping.get_current_scene()) if not m.startswith("_")][:80])

# Import the probe clip into a NEW tab, the way the bridge will.
attempt("new_scene", lambda: wrapping.new_scene() is not None)
loader = attempt("get_loader", lambda: app.get_tools_manager().get_tool("FbxSceneLoader").get_fbx_loader(app.current_scene()))
attempt("import_scene", lambda: loader.import_scene(FBX.replace("\\", "/")))

# Skeleton roots and frame count: try the domain scene's queries.
ws = wrapping.get_current_scene()
for label, fn in [
    ("domain_scene", lambda: ws.domain_scene()),
    ("roots_joint", lambda: [o.name for o in ws.domain_scene().get_scene_objects(only_roots=True, of_type="joint")]),
    ("roots_bone", lambda: [o.name for o in ws.domain_scene().get_scene_objects(only_roots=True, of_type="bone")]),
    ("roots_any", lambda: [o.name for o in ws.domain_scene().get_scene_objects(only_roots=True)][:20]),
    ("animation_size", lambda: ws.domain_scene().get_animation_size()),
    ("current_frame", lambda: ws.domain_scene().get_current_frame()),
]:
    attempt(label, fn)

# fps: look for any attribute that carries it on the loader or the scene.
attempt("loader_attrs", lambda: [a for a in dir(loader) if not a.startswith("_")])
attempt("loader_fps", lambda: getattr(loader, "fps", "absent"))
attempt("scene_fps_attrs", lambda: [a for a in dir(ws.domain_scene()) if "fps" in a.lower() or "frame" in a.lower()])

# Export back: bones only, into the probe folder.
out_joints = os.path.join(OUT, "probe_export_joints.fbx")
attempt("export_joints", lambda: loader.export_joints(out_joints.replace("\\", "/")))
attempt("export_joints_exists", lambda: os.path.isfile(out_joints))

with open(RESULT, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, ensure_ascii=False, sort_keys=True)
print("probe written", RESULT)
