"""Bringing the exported FBX into the Maya scene.

One rule dominates this module: the scene's frame rate is never written. The
animator is working in that scene while the tool runs, and silently changing
its frame rate would be the most destructive thing this bridge could do. A
mismatch is reported and the import proceeds.
"""

import os
import re

import maya.cmds as cmds
import maya.mel as mel

FBX_PLUGIN = "fbxmaya"

TIME_UNIT_TO_FPS = {
    "game": 15, "film": 24, "pal": 25, "ntsc": 30,
    "show": 48, "palf": 50, "ntscf": 60, "millisec": 1000,
}

_NUMERIC_UNIT = re.compile(r"^([0-9]+(?:\.[0-9]+)?)fps$")

# The FBX importer options we care about. Each is applied on its own so an
# unknown flag on some Maya build cannot abort the whole import. These
# configure the plugin's own FBXImport command - which is the only reason they
# take effect at all; through cmds.file they are ignored.
_IMPORT_OPTIONS = (
    "FBXImportMode -v add",
    # Never let the importer rewrite the scene's frame rate.
    "FBXImportSetMayaFrameRate -v false",
    # We set the timeline ourselves, from the keys that actually arrived.
    "FBXImportFillTimeline -v false",
    "FBXImportCameras -v false",
    "FBXImportLights -v false",
    "FBXImportConstraints -v false",
)


def fps_from_unit(unit):
    """Maya's time unit as a number, or None when we cannot tell.

    Custom rates come back as '30fps' rather than a named unit, and guessing a
    rate would be worse than admitting we do not know one.
    """
    if unit in TIME_UNIT_TO_FPS:
        return float(TIME_UNIT_TO_FPS[unit])
    match = _NUMERIC_UNIT.match(str(unit or ""))
    if match:
        return float(match.group(1))
    return None


def scene_fps():
    return fps_from_unit(cmds.currentUnit(query=True, time=True))


def fps_warning(clip_fps, fps_of_scene):
    """Text for a frame-rate mismatch, empty when there is nothing to say."""
    if clip_fps is None or fps_of_scene is None:
        return ""
    if abs(float(clip_fps) - float(fps_of_scene)) < 0.01:
        return ""
    return ("clip is {0:g} fps, scene is {1:g} fps - timing will not match "
            "frame for frame. Scene rate left unchanged.".format(
                float(clip_fps), float(fps_of_scene)))


def clip_range(times):
    """Outermost key times, or (None, None) when there are no keys."""
    if not times:
        return (None, None)
    return (min(times), max(times))


def existing_namespaces():
    found = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
    return set(name.lstrip(":").split(":")[-1] for name in found)


def ensure_fbx_plugin():
    if not cmds.pluginInfo(FBX_PLUGIN, query=True, loaded=True):
        cmds.loadPlugin(FBX_PLUGIN)


def _apply_import_options():
    """Best-effort: a flag missing on this Maya build must not stop the import."""
    missing = []
    try:
        mel.eval("FBXResetImport")
    except Exception:
        missing.append("FBXResetImport")
    for option in _IMPORT_OPTIONS:
        try:
            mel.eval(option + ";")
        except Exception:
            missing.append(option.split(" ", 1)[0])
    return missing


def import_command(fbx_path):
    """MEL for the FBX plugin's own importer.

    `cmds.file(i=True, type="FBX")` looks like the obvious call and is wrong:
    it brings the skeleton and silently drops every animation curve, because
    the FBXImport* settings do not reach the file translator. Measured on the
    same file - 1081 curves through FBXImport, 0 through cmds.file.

    Forward slashes only: inside a MEL string a backslash starts an escape, so
    a Windows path would mangle before the importer ever saw it.
    """
    return 'FBXImport -f "{0}";'.format(fbx_path.replace("\\", "/"))


def import_clip(fbx_path, namespace, set_timeline=True, clip_fps=None):
    """Import `fbx_path` under `namespace` and report what arrived.

    Returns a dict with the namespace used, the joint count, the key range and
    any frame-rate warning. What arrived is measured as a scene delta, because
    FBXImport - unlike cmds.file - has no way to report the nodes it made.
    """
    if not os.path.isfile(fbx_path):
        raise RuntimeError("no FBX at {0}".format(fbx_path))

    ensure_fbx_plugin()
    notes = _apply_import_options()

    before = set(cmds.ls(long=True))

    # FBXImport has no namespace flag, but it honours the current one
    # (verified: 116/116 joints and 1081/1081 curves landed inside).
    if not cmds.namespace(exists=namespace):
        cmds.namespace(addNamespace=namespace)
    cmds.namespace(setNamespace=namespace)
    try:
        mel.eval(import_command(fbx_path))
    finally:
        cmds.namespace(setNamespace=":")

    new_nodes = [node for node in (set(cmds.ls(long=True)) - before)]

    joints = [node for node in new_nodes
              if cmds.objExists(node) and cmds.objectType(node) == "joint"]
    curves = [node for node in new_nodes
              if cmds.objExists(node)
              and cmds.objectType(node).startswith("animCurve")]

    times = cmds.keyframe(curves, query=True, timeChange=True) or [] if curves else []
    start, end = clip_range(times)

    if set_timeline and start is not None:
        cmds.playbackOptions(minTime=start, maxTime=end,
                             animationStartTime=start, animationEndTime=end)

    return {"namespace": namespace,
            "nodes": len(new_nodes),
            "joints": len(joints),
            "curves": len(curves),
            "start": start,
            "end": end,
            "warning": fps_warning(clip_fps, scene_fps()),
            "notes": notes}
