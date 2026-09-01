"""Sending the scene's skeleton back out as FBX.

The mirror of `animimport`: same plugin, the same guarded-option pattern, and
the same rule - the animator's scene is never changed. Bake-on-export samples
the rigged bones into the file, so the OverRig rig stays untouched and there
is nothing to restore afterwards; the one thing written is the selection, and
it is put back.
"""

import math
import os

import maya.cmds as cmds
import maya.mel as mel

from maya_uebridge import animimport

NO_TARGET_MESSAGE = ("no skeleton in the scene to export - select a joint of "
                     "the one you mean")
AMBIGUOUS_TARGET_MESSAGE = ("several skeletons in the scene - select a joint "
                            "of the one to export")

# Bones only, rig excluded: constraints and input connections would drag the
# OverRig knots into the file, and a UE animation reimport reads none of it.
# Reset first, then set every flag explicitly - FBX settings are global for
# the session and inheriting whatever ran before is trap 33.
_EXPORT_OPTIONS = (
    "FBXExportBakeComplexAnimation -v true",
    "FBXExportBakeResampleAnimation -v true",
    "FBXExportConstraints -v false",
    "FBXExportInputConnections -v false",
    "FBXExportSkins -v false",
    "FBXExportShapes -v false",
    "FBXExportCameras -v false",
    "FBXExportLights -v false",
    "FBXExportEmbeddedTextures -v false",
    "FBXExportSkeletonDefinitions -v true",
    "FBXExportUpAxis y",
)


def union_range(animation, playback):
    """The exported range: animation range UNION playback range, snapped to
    WHOLE frames. Pure.

    An export clipped to a zoomed-in timeline trims the clip (trap 38), so
    the outer animation range always counts; the union also covers a slider
    dragged wider than the animation range.

    The snap is the other half, and it was measured the hard way
    (2026-09-01). A Maya range can end on a fraction -- the animator drags
    the slider and it stops at 88.792 -- and UE REFUSES such a clip:

        FBXImport: Error: Animation length 2.96 is not compatible with
        import frame-rate 31 fps (sub frame 0.752), animation has to be
        frame-border aligned.

    ...while the import task still reports success and saves the package,
    so from Python the export looks like it worked and the asset is
    untouched. Rounding OUTWARD (floor the start, ceil the end) can only
    widen the range, so it cannot re-introduce trap 38's clipping.
    """
    start = min(animation[0], playback[0])
    end = max(animation[1], playback[1])
    return (float(math.floor(start)), float(math.ceil(end)))


def outside_keys_warning(times, start, end):
    """Text when the hierarchy carries keys outside the exported range -
    warned, not silently included: a stray key at frame -200 must not
    stretch the clip. Pure."""
    outside = [t for t in (times or []) if t < start or t > end]
    if not outside:
        return ""
    return ("{0} key(s) outside the exported range {1:g}-{2:g} are not in "
            "the clip (first at {3:g})".format(
                len(outside), start, end, min(outside)))


def export_line(name, info):
    """What the status says about the export itself. Pure."""
    head = "{0}: {1} bones, frames {2:g}-{3:g}".format(
        name, info.get("joints", 0), info.get("start", 0), info.get("end", 0))
    if info.get("warning"):
        return "{0}  |  {1}".format(head, info["warning"])
    return head


def export_command(fbx_path):
    """MEL for the FBX plugin's own exporter. -s exports the selection (the
    skeleton root; children ride along); forward slashes because a backslash
    inside a MEL string starts an escape."""
    return 'FBXExport -f "{0}" -s;'.format(fbx_path.replace("\\", "/"))


def resolve_root():
    """The skeleton the export takes - the import merge's own rule.

    One function decides for both directions (selection, then the picker's
    connected character, then the only plain skeleton, then the one named
    `root`), so Import and Export can never disagree about "the"
    character. That was the user's ask in as many words: "такая же логика
    с экспортом".
    """
    roots = animimport.skeleton_roots()
    root = animimport.resolve_target()
    if root is None:
        raise RuntimeError(AMBIGUOUS_TARGET_MESSAGE if roots
                           else NO_TARGET_MESSAGE)
    return root


def export_range():
    return union_range(
        (cmds.playbackOptions(query=True, animationStartTime=True),
         cmds.playbackOptions(query=True, animationEndTime=True)),
        (cmds.playbackOptions(query=True, minTime=True),
         cmds.playbackOptions(query=True, maxTime=True)))


def _apply_export_options(start, end):
    """Best-effort like the import side: an unknown flag on some Maya build
    must not stop the export, but nothing is inherited either."""
    missing = []
    try:
        mel.eval("FBXResetExport")
    except Exception:
        missing.append("FBXResetExport")
    options = _EXPORT_OPTIONS + (
        "FBXExportBakeComplexStart -v {0:g}".format(start),
        "FBXExportBakeComplexEnd -v {0:g}".format(end),
        "FBXExportBakeComplexStep -v 1",
    )
    for option in options:
        try:
            mel.eval(option + ";")
        except Exception:
            missing.append(option.split(" ", 1)[0])
    return missing


def export_hierarchy(fbx_path, root=None, start=None, end=None):
    """Write `root`'s hierarchy (resolved when not given) to `fbx_path` with
    the animation baked in, and report what was written."""
    animimport.ensure_fbx_plugin()
    if root is None:
        root = resolve_root()
    if start is None or end is None:
        start, end = export_range()

    folder = os.path.dirname(fbx_path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)

    joints = animimport.joints_under(root)
    times = cmds.keyframe(joints, query=True, timeChange=True) or []

    notes = _apply_export_options(start, end)
    previous = cmds.ls(selection=True, long=True) or []
    cmds.select(root, replace=True)
    try:
        mel.eval(export_command(fbx_path))
    finally:
        if previous:
            cmds.select(previous, replace=True)
        else:
            cmds.select(clear=True)

    if not os.path.isfile(fbx_path) or os.path.getsize(fbx_path) == 0:
        raise RuntimeError("the exporter wrote nothing at {0}".format(fbx_path))

    return {"root": root.split("|")[-1],
            "joints": len(joints),
            "start": start, "end": end,
            "warning": outside_keys_warning(times, start, end),
            "notes": notes}
