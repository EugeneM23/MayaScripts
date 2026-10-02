"""The Python we send into the Unreal editor.

stdlib only: this module builds source text, it never imports `unreal`.

Two rules shape everything here. Parameters are interpolated with `json.dumps`,
never concatenated - a Windows path carries backslashes that would otherwise
become escape sequences, and an asset name is user data. And every script wraps
its body in try/except/finally so the reply file is written even when the body
raises: a traceback that reaches us is a bug report, a traceback that stays in
the editor's log is a mystery.

The scripts do not return their answer through the protocol. They write JSON to
a path we chose and print a marker. Both processes are on one machine, and a
project with thousands of animations would otherwise push a large payload
through the command channel.
"""

import json

MARKER = "__UEBRIDGE_DONE__"


_REPLY_TAIL = '''
except Exception:
    result["error"] = traceback.format_exc()
finally:
    try:
        _folder = os.path.dirname(_OUT)
        if _folder and not os.path.isdir(_folder):
            os.makedirs(_folder)
        with open(_OUT, "w") as _handle:
            json.dump(result, _handle)
    except Exception:
        unreal.log_error("uebridge: cannot write reply to " + str(_OUT))
    print(%(marker)s)
'''


_LIST_HEAD = '''\
import json
import os
import traceback

import unreal

_OUT = %(out_path)s
_PACKAGE_PATH = %(package_path)s
_SAMPLE_TAGS = %(sample_tags)s

# Tag spellings move between engine versions, so try several and take the first
# that answers rather than betting on one.
_FRAME_TAGS = ["Number of Frames", "NumberOfFrames", "Number of Keys"]
_LENGTH_TAGS = ["SequenceLength", "Sequence Length", "PlayLength"]
_FPS_TAGS = ["TargetFrameRate", "Target Frame Rate", "FrameRate", "Frame Rate"]

result = {"ok": False, "error": "", "scanning": False, "project": "",
          "content_dir": "", "assets": [], "sample_tags": {}}


def first_tag(data, names):
    for name in names:
        try:
            value = data.get_tag_value(name)
        except Exception:
            value = None
        if value not in (None, ""):
            return str(value)
    return ""


def short_name(value):
    """A skeleton tag arrives as /Game/Path/SK_Manny.SK_Manny or an object path."""
    text = str(value or "").replace("'", "").replace(chr(34), "")
    for separator in (".", "/"):
        if separator in text:
            text = text.rsplit(separator, 1)[-1]
    return text


try:
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    result["project"] = str(unreal.Paths.get_project_file_path())
    # The checkouts window maps p4's clientFile paths to /Game packages, and
    # get_project_file_path can come back engine-relative - so the absolute
    # Content dir travels in the reply rather than being derived Maya-side.
    result["content_dir"] = str(unreal.Paths.convert_relative_path_to_full(
        unreal.Paths.project_content_dir()))

    if registry.is_loading_assets():
        # A partial list right after editor start reads as "this project has few
        # animations", which is a silent wrong answer. Say so instead.
        result["scanning"] = True
    else:
        try:
            asset_filter = unreal.ARFilter(
                class_paths=[unreal.TopLevelAssetPath("/Script/Engine",
                                                      "AnimSequence")],
                package_paths=[_PACKAGE_PATH],
                recursive_paths=True,
                recursive_classes=True)
        except Exception:
            # class_names is the pre-5.1 spelling.
            asset_filter = unreal.ARFilter(
                class_names=["AnimSequence"],
                package_paths=[_PACKAGE_PATH],
                recursive_paths=True,
                recursive_classes=True)

        found = registry.get_assets(asset_filter)
        for data in found:
            result["assets"].append({
                "name": str(data.asset_name),
                "package": str(data.package_name),
                "skeleton": short_name(first_tag(data, ["Skeleton"])),
                "frames": first_tag(data, _FRAME_TAGS),
                "length": first_tag(data, _LENGTH_TAGS),
                "fps": first_tag(data, _FPS_TAGS)})

        if _SAMPLE_TAGS and found:
            sample = found[0]
            dump = {}
            for attribute in ("tags_and_values", "tag_values", "get_tag_values"):
                try:
                    raw = getattr(sample, attribute)
                    raw = raw() if callable(raw) else raw
                    dump = dict((str(k), str(v)) for k, v in dict(raw).items())
                    break
                except Exception:
                    continue
            if not dump:
                for name in _FRAME_TAGS + _LENGTH_TAGS + _FPS_TAGS + ["Skeleton"]:
                    value = first_tag(sample, [name])
                    if value:
                        dump[name] = value
            result["sample_tags"] = {"asset": str(sample.asset_name), "tags": dump}

        result["ok"] = True
'''


_EXPORT_HEAD = '''\
import json
import os
import traceback

import unreal

_OUT = %(out_path)s
_PACKAGE = %(package)s
_FBX = %(fbx_path)s

result = {"ok": False, "error": "", "path": "",
          "frames": None, "length": None, "fps": None, "notes": []}


def attempt(call, default=None):
    """Engine APIs move between versions; a miss must not abort the export."""
    try:
        return call()
    except Exception:
        return default


try:
    anim = unreal.load_asset(_PACKAGE)
    if anim is None:
        raise RuntimeError("could not load asset: " + str(_PACKAGE))

    length = attempt(lambda: float(anim.get_play_length()))
    if length is None:
        length = attempt(lambda: float(anim.get_editor_property("sequence_length")))
    result["length"] = length

    frames = attempt(lambda: int(anim.get_editor_property("number_of_sampled_keys")))
    if frames is None:
        frames = attempt(lambda: int(anim.get_editor_property("number_of_frames")))
    result["frames"] = frames

    rate = attempt(lambda: anim.get_editor_property("target_frame_rate"))
    if rate is not None:
        result["fps"] = attempt(
            lambda: float(rate.numerator) / float(rate.denominator))

    folder = os.path.dirname(_FBX)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    if os.path.isfile(_FBX):
        attempt(lambda: os.remove(_FBX))

    options = unreal.FbxExportOption()
    # The Auto card (2026-10-02) asks for the clip's own mesh: the exporter
    # writes its preview mesh (else its skeleton's, else FindCompatibleMesh),
    # skinned, beside the skeleton - for a clip that turns out to be no
    # character of ours and comes in its own skeleton.
    for name, value in (("ascii", False),
                        ("export_preview_mesh", %(preview_mesh)s),
                        ("export_morph_targets", False),
                        ("map_skeletal_motion_to_root", False),
                        ("level_of_detail", False),
                        ("collision", False),
                        ("vertex_color", False)):
        if attempt(lambda: options.set_editor_property(name, value) or True) is None:
            result["notes"].append("no FbxExportOption." + name)

    task = unreal.AssetExportTask()
    task.set_editor_property("object", anim)
    task.set_editor_property("filename", _FBX)
    # automated/prompt are load-bearing: without them UE raises a modal dialog
    # that nobody can click, and the editor hangs for good.
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    task.set_editor_property("exporter", unreal.AnimSequenceExporterFBX())
    task.set_editor_property("options", options)

    ran = unreal.Exporter.run_asset_export_task(task)

    # A True return is not proof of a file on disk; check the disk.
    if os.path.isfile(_FBX) and os.path.getsize(_FBX) > 0:
        result["ok"] = True
        result["path"] = _FBX
    else:
        raise RuntimeError("export returned " + str(ran)
                           + " but no file appeared at " + str(_FBX))
'''


def list_script(out_path, package_path="/Game", sample_tags=False):
    """Source that writes every AnimSequence under `package_path` to `out_path`.

    Reads asset-registry tags rather than loading assets - loading every
    animation to read its length would take minutes on a real project.

    `sample_tags` adds the raw tag map of the first asset to the reply. It
    exists for the spike, which has to learn the real tag names on this engine
    build rather than trust the candidate list above.
    """
    values = {"out_path": json.dumps(out_path),
              "package_path": json.dumps(package_path),
              "sample_tags": "True" if sample_tags else "False",
              "marker": json.dumps(MARKER)}
    return (_LIST_HEAD % values) + (_REPLY_TAIL % values)


_REIMPORT_HEAD = '''\
import json
import os
import traceback

import unreal

_OUT = %(out_path)s
_PACKAGE = %(package)s
_FBX = %(fbx_path)s

result = {"ok": False, "error": "", "saved": False,
          "frames": None, "length": None, "notes": [],
          "before_frames": None, "before_length": None, "skeleton": ""}


def attempt(call, default=None):
    """Engine APIs move between versions; a miss must not abort the run."""
    try:
        return call()
    except Exception:
        return default


try:
    anim = unreal.load_asset(_PACKAGE)
    if anim is None:
        raise RuntimeError("could not load asset: " + str(_PACKAGE))
    if not os.path.isfile(_FBX):
        raise RuntimeError("no FBX at " + str(_FBX))

    skeleton = anim.get_editor_property("skeleton")
    if skeleton is None:
        raise RuntimeError("the asset has no skeleton: " + str(_PACKAGE))
    result["skeleton"] = str(attempt(lambda: skeleton.get_name(), "") or "")

    # Read the asset BEFORE the import, so the caller can tell a real
    # replacement from a silent no-op. Measured 2026-09-01: an FBX whose
    # bones do not match the asset's skeleton imports "successfully" -
    # ok, saved, no notes, no error - and leaves the animation untouched.
    # Reporting "reimported and saved (196 frames)" over that is how an
    # animator believes an export landed when nothing was written.
    result["before_frames"] = attempt(
        lambda: int(anim.get_editor_property("number_of_sampled_keys")))
    result["before_length"] = attempt(lambda: float(anim.get_play_length()))

    # This engine build exposes no ReimportSubsystem (measured 2026-08-21:
    # hasattr(unreal, "ReimportSubsystem") is False), so the reimport is an
    # automated import task over the existing package: replace_existing
    # rewrites the same asset, the skeleton comes from the asset itself, and
    # automated=True keeps every dialog away (the trap-23/24 family).
    options = unreal.FbxImportUI()
    for name, value in (("import_mesh", False),
                        ("import_animations", True),
                        ("import_materials", False),
                        ("import_textures", False),
                        ("create_physics_asset", False),
                        ("import_as_skeletal", False),
                        ("automated_import_should_detect_type", False),
                        ("skeleton", skeleton)):
        if attempt(lambda: options.set_editor_property(name, value) or True) is None:
            result["notes"].append("no FbxImportUI." + name)
    if attempt(lambda: options.set_editor_property(
            "mesh_type_to_import",
            unreal.FBXImportType.FBXIT_ANIMATION) or True) is None:
        result["notes"].append("no FbxImportUI.mesh_type_to_import")

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", _FBX)
    task.set_editor_property("destination_path", _PACKAGE.rsplit("/", 1)[0])
    task.set_editor_property("destination_name", _PACKAGE.rsplit("/", 1)[-1])
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)

    # Interchange owns .fbx on this build and swallows a bones-only file
    # with "nothing to import" (measured 2026-08-21 in the editor log), so
    # the task runs on the legacy fbx path and the flag goes straight back.
    flag = attempt(lambda: unreal.SystemLibrary.get_console_variable_int_value(
        "Interchange.FeatureFlags.Import.FBX"))
    if flag:
        unreal.SystemLibrary.execute_console_command(
            None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    finally:
        if flag:
            unreal.SystemLibrary.execute_console_command(
                None, "Interchange.FeatureFlags.Import.FBX 1")

    # task.result is deprecated and imported_object_paths stays empty on
    # this build (both measured) - get_objects is what answers.
    landed = list(attempt(lambda: task.get_objects(), []) or [])
    if not landed:
        raise RuntimeError("the import task reported nothing imported - "
                           "check the editor's Output Log")

    anim = unreal.load_asset(_PACKAGE)
    if anim is None:
        raise RuntimeError("the asset vanished after the reimport: "
                           + str(_PACKAGE))

    result["saved"] = bool(attempt(lambda: unreal.EditorAssetLibrary.save_asset(
        _PACKAGE, only_if_is_dirty=False)))

    length = attempt(lambda: float(anim.get_play_length()))
    if length is None:
        length = attempt(lambda: float(anim.get_editor_property("sequence_length")))
    result["length"] = length

    frames = attempt(lambda: int(anim.get_editor_property("number_of_sampled_keys")))
    if frames is None:
        frames = attempt(lambda: int(anim.get_editor_property("number_of_frames")))
    result["frames"] = frames

    result["ok"] = True
'''


def export_script(out_path, package, fbx_path, preview_mesh=False):
    """Source that exports one AnimSequence to `fbx_path`: bones only, or with
    its preview mesh skinned beside them (`preview_mesh`, the Auto card)."""
    values = {"out_path": json.dumps(out_path),
              "package": json.dumps(package),
              "fbx_path": json.dumps(fbx_path),
              "preview_mesh": "True" if preview_mesh else "False",
              "marker": json.dumps(MARKER)}
    return (_EXPORT_HEAD % values) + (_REPLY_TAIL % values)


def reimport_script(out_path, package, fbx_path):
    """Source that reimports one AnimSequence from `fbx_path` and saves it.

    The uasset must already be writable (checked out) - this script does not
    touch Perforce; the bridge did that before calling it. The mechanism is a
    replace-import (AssetImportTask over the existing package), because this
    engine build exposes no ReimportSubsystem to Python; note that a replace
    rebuilds the asset from the fbx, so curves the fbx does not carry do not
    survive it - the same contract as reimporting by hand in the editor.
    """
    values = {"out_path": json.dumps(out_path),
              "package": json.dumps(package),
              "fbx_path": json.dumps(fbx_path),
              "marker": json.dumps(MARKER)}
    return (_REIMPORT_HEAD % values) + (_REPLY_TAIL % values)
