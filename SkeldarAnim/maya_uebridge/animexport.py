"""Sending the scene's skeleton back out as FBX.

The mirror of `animimport`: same plugin, the same guarded-option pattern, and
the same rule - the animator's scene is never changed. Bake-on-export samples
the rigged bones into the file, so the OverRig rig stays untouched and there
is nothing to restore afterwards; the one thing written is the selection, and
it is put back.
"""

import contextlib
import math
import os

import maya.cmds as cmds
import maya.mel as mel

from maya_uebridge import animimport, fbxlayout

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
    # BONES ONLY (2026-09-24): the exporter takes a selected node's children
    # along by default, and a sword hung under the hand went into every clip
    # (measured: 10890 vertices, six curves and a material in an animation
    # FBX). Every joint is selected instead and nothing else rides along --
    # whatever anybody parents under a bone.
    "FBXExportIncludeChildren -v false",
)

# Cascadeur's layout for every export (2026-09-25, the animator's choice): the skeleton under a
# Null `Armature` (fbxlayout.WRAPPER_NAME), rotated -90 X, `root` with no orientation of its own and its
# translation in Z-up space (fbxlayout). "plain" is the file as it was before: `root` at world
# level carrying the -90 on its jointOrient.
LAYOUT = "cascadeur"

# The roads that end in Unreal's own import (Export to uasset, the checkouts' EXPORT) keep the
# plain layout until Unreal has been seen reading Cascadeur's the same way: the sandbox round trip
# docs/superpowers/plans/verify_cascadeur_layout_unreal.py (spec: "verified before the switch is
# kept"). One word here switches both.
UNREAL_LAYOUT = "plain"


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


def export_hierarchy(fbx_path, root=None, start=None, end=None, layout=LAYOUT):
    """Write `root`'s hierarchy (resolved when not given) to `fbx_path` with
    the animation baked in, and report what was written.

    `layout` is "cascadeur" (the default: the skeleton under the Null `Armature`,
    see fbxlayout) or "plain" (the file as it was before 2026-09-25)."""
    animimport.ensure_fbx_plugin()
    if root is None:
        root = resolve_root()
    if start is None or end is None:
        start, end = export_range()
    # The FBX exporter writes a selected bone's ANCESTORS into the file (measured 2026-10-02), so a
    # character standing in its outliner group (2026-10-02) has its top -- the root, or the
    # Armature Null over it -- out at world level for the length of the export, put back after.
    # The name the animator sees is taken BEFORE the lift: a lifted `root` beside a world-level
    # `root` is `root1` for the export's length, and the status line must not name that.
    # One undo chunk round all of it: the lift, the layout's Null and the renames are scene edits
    # that end where they began, so a Ctrl+Z after an export undoes the whole round trip (a net
    # nothing) instead of its LAST step -- which put a grouped root back out at world level.
    shown = (root or "").split("|")[-1]
    cmds.undoInfo(openChunk=True, chunkName="skeldarExportFbx")
    try:
        with _out_of_group(root) as root:
            return _export_hierarchy(fbx_path, root, start, end, layout, shown=shown)
    finally:
        cmds.undoInfo(closeChunk=True)


@contextlib.contextmanager
def _out_of_group(root):
    """`chargroup.lifted`, lazily and guarded: a Maya without Scene Setup exports as before."""
    try:
        from maya_scenesetup import chargroup
    except ImportError:
        yield root
        return
    with chargroup.lifted(root) as path:
        yield path or root


def _export_hierarchy(fbx_path, root, start, end, layout, shown=None):
    """The body of `export_hierarchy`, the root out of any character group. `shown` is the root's
    leaf as the outliner shows it (before any lift renamed it), for the status line."""

    folder = os.path.dirname(fbx_path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)

    joints = animimport.joints_under(root)
    times = cmds.keyframe(joints, query=True, timeChange=True) or []

    notes = _apply_export_options(start, end)
    leaf = shown or root.split("|")[-1]
    previous = cmds.ls(selection=True, long=True) or []
    root_uuid = (cmds.ls(root, uuid=True) or [None])[0]
    joint_ids = cmds.ls(joints, uuid=True) or []
    exported_as = leaf
    # One name for every character since 2026-09-25's evening: `Armature`.
    name = fbxlayout.WRAPPER_NAME if layout == "cascadeur" else ""
    wrapper_used = ""
    try:
        # The same name Maya decorated on arrival would go into the file,
        # and the UE skeleton has no bone called `Manny_Skeleton_root` --
        # nor `Manny_Rig:pelvis`: a rig lives in a namespace since
        # 2026-09-08 and the exporter writes the namespace (measured). So
        # every joint wears its plain name for the length of the export -
        # every export road runs through here, which is why this is the
        # one place it lives.
        with animimport.target_plain_names(root, joints) as took:
            exported_as = took or leaf
            # The rename invalidated every path resolved above (trap 16):
            # the bones are selected by UUID, all of them, and only them.
            root_now = ((cmds.ls(root_uuid, long=True) or [root])[0]
                        if root_uuid else root)
            # A root standing in Cascadeur's layout already (2026-09-28, the Creep): `wrapped`
            # writes its own Null as it is, `flattened` takes it out for the plain file.
            manager = (fbxlayout.wrapped(root_now, name) if name
                       else fbxlayout.flattened(root_now))
            with fbxlayout.tag_held(root_now), manager as (wrapper, layout_note):
                if layout_note:
                    notes.append(layout_note)
                # the wrapper re-parented the root: every path is resolved again
                bones = cmds.ls(joint_ids, long=True) or []
                if not bones:
                    bones = [(cmds.ls(root_uuid, long=True) or [root])[0]
                             if root_uuid else root]
                cmds.select(bones + ([wrapper] if wrapper else []), replace=True)
                mel.eval(export_command(fbx_path))
                # a Null went into the file -- ours, or the one the root stands under
                wrapper_used = fbxlayout.WRAPPER_NAME if wrapper else ""
    finally:
        restored = [node for node in previous if cmds.objExists(node)]
        if restored:
            cmds.select(restored, replace=True)
        else:
            cmds.select(clear=True)

    if not os.path.isfile(fbx_path) or os.path.getsize(fbx_path) == 0:
        raise RuntimeError("the exporter wrote nothing at {0}".format(fbx_path))

    warning = "  |  ".join(text for text in (
        outside_keys_warning(times, start, end),
        animimport.root_note(leaf, exported_as),
    ) if text)

    return {"root": exported_as,
            "joints": len(joints),
            "start": start, "end": end,
            "warning": warning,
            "notes": notes,
            "layout": "cascadeur" if wrapper_used else "plain",
            "wrapper": wrapper_used}
