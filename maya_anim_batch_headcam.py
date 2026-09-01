"""
Maya Anim Batch Head Cam Tool
Opens Maya/FBX files, point-constrains camera_root to head, bakes it,
applies clean scene, re-exports.
Preserves original FPS and frame timings from source file.
Run in Maya Script Editor (Python tab).
"""
import maya.cmds as cmds
import maya.mel as mel
import os

WINDOW_NAME = "animBatchHeadCamTool"


# -------------------------
# NODE UTILS
# -------------------------

def strip_namespace(node):
    short_name = node.split("|")[-1]
    return short_name.split(":")[-1]


def find_node_by_name(target_name):
    for node in (cmds.ls(long=True) or []):
        if strip_namespace(node) == target_name:
            return node
    return None


def find_child_by_name(root_node, target_name):
    for node in (cmds.listRelatives(root_node, allDescendents=True, fullPath=True) or []):
        if strip_namespace(node) == target_name:
            return node
    return None


def get_hierarchy(root_node):
    result = [root_node]
    result.extend(cmds.listRelatives(root_node, allDescendents=True, fullPath=True) or [])
    return result


def ensure_folder(path):
    if path and not os.path.isdir(path):
        os.makedirs(path)


# -------------------------
# TIMELINE
# -------------------------

def get_key_range_from_root():
    root = find_node_by_name("root")
    if not root:
        cmds.warning("root не найден.")
        return None

    all_keys = []
    for node in get_hierarchy(root):
        if cmds.objExists(node):
            try:
                keys = cmds.keyframe(node, query=True, timeChange=True) or []
                all_keys.extend(keys)
            except Exception:
                pass

    if not all_keys:
        cmds.warning("Ключи в иерархии root не найдены.")
        return None

    start = int(round(min(all_keys)))
    end = int(round(max(all_keys)))
    return {"min": start, "max": end}


def snap_keys_to_frames_in_root():
    root = find_node_by_name("root")
    if not root:
        return

    for node in get_hierarchy(root):
        if not cmds.objExists(node):
            continue
        curves = cmds.listConnections(node, type="animCurve", source=True, destination=False) or []
        for curve in set(curves):
            count = cmds.keyframe(curve, query=True, keyframeCount=True) or 0
            for i in range(int(count)):
                try:
                    t = cmds.keyframe(curve, query=True, index=(i, i), timeChange=True)[0]
                    cmds.keyframe(curve, edit=True, index=(i, i), timeChange=round(t))
                except Exception as e:
                    cmds.warning("snap key error on {} index {}: {}".format(curve, i, e))


def set_timeline(key_range):
    if not key_range:
        return
    cmds.playbackOptions(
        minTime=key_range["min"],
        maxTime=key_range["max"],
        animationStartTime=key_range["min"],
        animationEndTime=key_range["max"]
    )


# -------------------------
# FILES
# -------------------------

def get_files_from_folder(folder, process_maya=True, process_fbx=True):
    result = []
    if not os.path.isdir(folder):
        return result
    for name in os.listdir(folder):
        full = os.path.join(folder, name)
        if not os.path.isfile(full):
            continue
        low = name.lower()
        if process_maya and (low.endswith(".ma") or low.endswith(".mb")):
            result.append(full)
        if process_fbx and low.endswith(".fbx"):
            result.append(full)
    return result


def load_fbx_plugin():
    try:
        if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
            cmds.loadPlugin("fbxmaya")
    except Exception as e:
        cmds.warning("FBX plugin: {}".format(e))


# The mode an open needs: create everything the file holds. Never inherited --
# see open_file.
FBX_IMPORT_MODE = "add"


def get_fbx_import_mode():
    try:
        return mel.eval("FBXImportMode -q;")
    except Exception:
        return None


def set_fbx_import_mode(mode):
    try:
        mel.eval("FBXImportMode -v {};".format(mode))
    except Exception as e:
        cmds.warning("FBX import mode: {}".format(e))


def open_file(file_path):
    """Open file preserving its original FPS."""
    ext = os.path.splitext(file_path)[1].lower()
    cmds.file(new=True, force=True)

    if ext in (".ma", ".mb"):
        cmds.file(file_path, open=True, force=True)
        return True

    if ext == ".fbx":
        load_fbx_plugin()
        # The FBX import MODE is one global setting for the whole Maya session
        # and `cmds.file` inherits it. Any Unreal import leaves it on
        # `exmerge`, where the importer matches names against what is already
        # in the scene and creates NOTHING: measured, a clip opens with 0
        # joints where `add` and `merge` both give 94. The batch then cleaned,
        # placed and exported an empty scene over every file in the folder and
        # said nothing about it. Set the mode, and put back whatever was there
        # -- the animator is working in this session.
        previous = get_fbx_import_mode()
        set_fbx_import_mode(FBX_IMPORT_MODE)
        try:
            # Open FBX directly so Maya reads FPS from the file (import creates a new
            # scene with default 24fps and ignores the FBX frame rate)
            cmds.file(file_path, open=True, force=True)
        finally:
            if previous:
                set_fbx_import_mode(previous)
        return True

    cmds.warning("Неподдерживаемый формат: {}".format(file_path))
    return False


TIME_UNIT_TO_FPS = {
    "game":   15,   "film":   24,   "pal":    25,
    "ntsc":   30,   "show":   48,   "palf":   50,
    "ntscf":  60,   "millisec": 1000,
}


def get_scene_fps():
    unit = cmds.currentUnit(query=True, time=True)
    return TIME_UNIT_TO_FPS.get(unit, 30)


def export_file(source_path, output_folder, key_range=None, settings=None):
    # Everything this tool does is anchored on the root hierarchy, so a scene
    # without one is a scene nothing worked on -- and exporting it writes a
    # file holding the four default cameras and 8 KB of nothing. That is what
    # fourteen clips became when the import mode created no nodes: written,
    # counted as successes, and only noticed when the animator opened one.
    # Refuse instead, and let the caller count it as a failure.
    if not find_node_by_name("root"):
        cmds.warning("В сцене нет root, экспорт пропущен: {}".format(source_path))
        return None

    ensure_folder(output_folder)
    ext = os.path.splitext(source_path)[1].lower()
    base = os.path.splitext(os.path.basename(source_path))[0]
    out = os.path.join(output_folder, base + ext)

    if ext == ".fbx":
        load_fbx_plugin()
        fps = get_scene_fps()
        try:
            mel.eval("FBXExportFrameRate -v {};".format(fps))
        except Exception as e:
            cmds.warning("FBX FPS set error: {}".format(e))
        bake = settings.get("bake_animation", False) if settings else False
        try:
            mel.eval("FBXExportBakeComplexAnimation -v {};".format("true" if bake else "false"))
            if bake and key_range:
                mel.eval("FBXExportBakeComplexStart -v {};".format(key_range["min"]))
                mel.eval("FBXExportBakeComplexEnd -v {};".format(key_range["max"]))
                mel.eval("FBXExportBakeComplexStep -v 1;")
        except Exception as e:
            cmds.warning("FBX bake error: {}".format(e))
        cmds.select(all=True)
        cmds.file(out, force=True, options="v=0;", type="FBX export", exportAll=True)

    elif ext == ".ma":
        cmds.file(out, force=True, options="v=0;", type="mayaAscii", exportAll=True)

    elif ext == ".mb":
        cmds.file(out, force=True, options="v=0;", type="mayaBinary", exportAll=True)

    else:
        cmds.warning("Нельзя экспортировать: {}".format(source_path))
        return None

    return out


# -------------------------
# OPERATIONS
# -------------------------

def op_constrain_camera_to_head():
    """Point-constrain camera_root to head, bake the result, drop the constraint.

    Point, not parent: only the position follows the head, the camera keeps
    its own orientation. maintainOffset is off, so camera_root sits exactly on
    the head rather than keeping the ~85 cm it stands above it in these clips.
    """
    root = find_node_by_name("root")
    if not root:
        cmds.warning("root не найден.")
        return False

    camera_root = find_child_by_name(root, "camera_root")
    if not camera_root:
        cmds.warning("camera_root не найден в иерархии root.")
        return False

    head = find_child_by_name(root, "head")
    if not head:
        cmds.warning("head не найден в иерархии root.")
        return False

    key_range = get_key_range_from_root()
    if not key_range:
        cmds.warning("Нет ключей в иерархии root, запекать нечего.")
        return False

    # Only the translate curves: a constraint over an animated channel gets a
    # pairBlend, and rotation on camera_root is none of this operation's
    # business.
    for attr in ("translateX", "translateY", "translateZ"):
        curves = cmds.listConnections("{}.{}".format(camera_root, attr),
                                      type="animCurve",
                                      source=True, destination=False) or []
        if curves:
            cmds.delete(curves)

    constraint = cmds.pointConstraint(head, camera_root, maintainOffset=False)
    cmds.bakeResults(
        camera_root,
        time=(key_range["min"], key_range["max"]),
        attribute=["translateX", "translateY", "translateZ"],
        simulation=False,
        sampleBy=1,
        disableImplicitControl=True,
        preserveOutsideKeys=False,
    )
    if cmds.objExists(constraint[0]):
        cmds.delete(constraint)
    return True


def op_clean_scene():
    root = find_node_by_name("root")
    if not root:
        cmds.warning("root не найден, clean scene отменён.")
        return False

    # Вынести root в world
    if cmds.listRelatives(root, parent=True, fullPath=True):
        try:
            result = cmds.parent(root, world=True)
            if result:
                root = result[0]
        except Exception as e:
            cmds.warning("parent to world: {}".format(e))

    # Удалить всё кроме иерархии root
    root_set = set(get_hierarchy(root))
    for obj in (cmds.ls(assemblies=True, long=True) or []):
        keep = any(n == obj or n.startswith(obj + "|") for n in root_set)
        if not keep:
            try:
                cmds.delete(obj)
            except Exception as e:
                cmds.warning("delete {}: {}".format(obj, e))

    # Снова найти root после удалений и вынести в world
    root = find_node_by_name("root")
    if not root:
        cmds.warning("root потерян после очистки.")
        return False

    if cmds.listRelatives(root, parent=True, fullPath=True):
        try:
            result = cmds.parent(root, world=True)
            if result:
                root = result[0]
        except Exception as e:
            cmds.warning("parent to world (2): {}".format(e))

    # Убрать namespace
    hierarchy = sorted(get_hierarchy(root), key=lambda x: x.count("|"), reverse=True)
    for node in hierarchy:
        if cmds.objExists(node):
            clean = strip_namespace(node)
            try:
                cmds.rename(node, clean)
            except Exception as e:
                cmds.warning("rename {}: {}".format(node, e))

    return True


def apply_operations(settings):
    if settings["snap_keys"]:
        snap_keys_to_frames_in_root()

    if settings["constrain_to_head"]:
        op_constrain_camera_to_head()

    if settings["use_clean_scene"]:
        op_clean_scene()

    # Read key range and set timeline LAST — after all ops that may affect the scene
    key_range = get_key_range_from_root()
    if key_range:
        set_timeline(key_range)

    return key_range


# -------------------------
# RUN
# -------------------------

def run_on_current_scene(settings):
    source = cmds.file(query=True, sceneName=True)
    key_range = apply_operations(settings)

    if settings["output_folder"] and source:
        export_file(source, settings["output_folder"], key_range, settings)
    elif not source:
        cmds.warning("Текущая сцена не сохранена, экспорт пропущен.")

    cmds.inViewMessage(amg="<hl>Done:</hl> текущая сцена обработана",
                       pos="topCenter", fade=True)


def run_on_folder(settings):
    files = get_files_from_folder(
        settings["input_folder"],
        process_maya=settings["process_maya"],
        process_fbx=settings["process_fbx"]
    )

    if not files:
        cmds.warning("Файлы не найдены в папке.")
        return

    if not settings["output_folder"]:
        cmds.warning("Укажи output folder.")
        return

    ok = 0
    fail = 0

    for path in files:
        try:
            print("Processing: {}".format(path))

            if not open_file(path):
                fail += 1
                continue

            key_range = apply_operations(settings)
            if export_file(path, settings["output_folder"], key_range, settings):
                ok += 1
            else:
                fail += 1

        except Exception as e:
            fail += 1
            cmds.warning("Ошибка при обработке {}: {}".format(path, e))

    cmds.inViewMessage(
        amg="<hl>Batch done:</hl> success: <hl>{}</hl>, failed: <hl>{}</hl>".format(ok, fail),
        pos="topCenter",
        fade=True
    )


def run_tool(*args):
    settings = get_ui_settings()

    if settings["process_all_files"]:
        if not settings["input_folder"] or not os.path.isdir(settings["input_folder"]):
            cmds.warning("Укажи корректную input folder.")
            return
        run_on_folder(settings)
    else:
        run_on_current_scene(settings)


# -------------------------
# UI
# -------------------------

def browse_folder(field_name, caption):
    folder = cmds.fileDialog2(fileMode=3, dialogStyle=2, caption=caption)
    if folder:
        cmds.textFieldButtonGrp(field_name, edit=True, text=folder[0])


def get_ui_settings():
    return {
        "input_folder":      cmds.textFieldButtonGrp("inputFolderField",  query=True, text=True),
        "output_folder":     cmds.textFieldButtonGrp("outputFolderField", query=True, text=True),
        "process_all_files": cmds.checkBox("cbAllFiles",   query=True, value=True),
        "process_maya":      cmds.checkBox("cbMayaFiles",  query=True, value=True),
        "process_fbx":       cmds.checkBox("cbFbxFiles",   query=True, value=True),
        "constrain_to_head": cmds.checkBox("cbHeadCam",  query=True, value=True),
        "use_clean_scene":   cmds.checkBox("cbClean",      query=True, value=True),
        "snap_keys":         cmds.checkBox("cbSnapKeys",   query=True, value=True),
        "bake_animation":    cmds.checkBox("cbBake",       query=True, value=True),
    }


def show_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    cmds.window(WINDOW_NAME, title="Anim Batch Head Cam Tool", widthHeight=(540, 330))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)

    cmds.textFieldButtonGrp("inputFolderField",  label="Input folder",
                            buttonLabel="Выбрать", text="",
                            buttonCommand=lambda *_: browse_folder("inputFolderField",  "Папка с файлами"))
    cmds.textFieldButtonGrp("outputFolderField", label="Output folder",
                            buttonLabel="Выбрать", text="",
                            buttonCommand=lambda *_: browse_folder("outputFolderField", "Папка для сохранения"))

    cmds.separator(height=10, style="in")
    cmds.checkBox("cbAllFiles",  label="Apply to all files in input folder", value=False)
    cmds.checkBox("cbMayaFiles", label="Process Maya scenes (.ma / .mb)",    value=True)
    cmds.checkBox("cbFbxFiles",  label="Process FBX files (.fbx)",           value=True)

    cmds.separator(height=10, style="in")
    cmds.checkBox("cbHeadCam", label="Constrain camera_root to head + bake", value=True)

    cmds.checkBox("cbClean",    label="Clean scene (удалить всё кроме root)", value=True)
    cmds.checkBox("cbSnapKeys", label="Snap root keys to frames", value=True)
    cmds.checkBox("cbBake",     label="Bake animation on FBX export",         value=False)

    cmds.separator(height=10, style="in")
    cmds.button(label="GO", height=42, command=run_tool)

    cmds.showWindow(WINDOW_NAME)


show_ui()
