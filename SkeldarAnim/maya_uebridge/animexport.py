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
import re
import tempfile

import maya.cmds as cmds
import maya.mel as mel

from maya_uebridge import animimport, fbxkeys, fbxlayout

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

# The FBX plugin's stuck bake rate (2026-10-27, «в сцене 30 фпс после экспорта в uasset 120»;
# fbxkeys says what was measured). The only thing found to set it back without reloading the
# plugin -- a reload put it right and crashed mayapy on exit, 0xC0000374 -- is an FBXImport that
# samples at the FILE's rate: the plugin takes that file's rate as its own. So a probe holding
# one empty transform is exported at the scene's rate (the header is always right) and imported
# back in exmerge mode, which merges onto a node of the probe's name and creates nothing.
# Measured: the undo queue survives it, the current frame does not (it goes to 0).
PROBE = "skeldarFbxRateProbe"
PROBE_FILE = "skeldar_fbx_rate_probe.fbx"
PROBE_FOLDER = os.path.join(tempfile.gettempdir(), "maya_uebridge")
_PROBE_IMPORT = (("Import|IncludeGrp|Animation", True),
                 ("Import|IncludeGrp|Animation|ExtraGrp|TimeLine", False),
                 ("Import|IncludeGrp|Animation|SamplingPanel|SamplingRateSelector", "File"))

REARMED = ("the FBX plugin was baking {0} (left by an earlier FBX export in this session) - "
           "reset, exported again")
STUCK = ("the FBX plugin bakes {0} and would not let go - nothing was exported; restart Maya "
         "and export again")

# The file's one take cut to the exported range (2026-10-28, «чому не експортиться анімація»):
# the bake writes start..end, but a bone keyed on its own keeps every key it has past them
# (measured: a 0-62 export of a scene keyed to 65 held 0..62, 64 and 65) - a clip longer than the
# scene says, and a hole the rate check took for a latched plugin. A split take over the range
# with the original take deleted holds start..end only, every key inside as before, under the
# take's usual name. The split outlives FBXResetExport (measured), so it is set for the length of
# one export and the animator's own is put back.
TAKE = "Take 001"
OUTSIDE = ("{0} reached the file - nothing was exported; set the range over every key, or delete "
           "the keys past it")


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


def _frame(value):
    return "%d" % value if float(value) == int(value) else "%g" % value


def split_command(name, start, end):
    """MEL adding one split take `name` over frames `start`..`end`. Pure."""
    return 'FBXExportSplitAnimationIntoTakes -v "{0}" {1} {2}'.format(name, _frame(start),
                                                                      _frame(end))


def parse_split_takes(answer):
    """[(name, start, end)] out of `FBXExportSplitAnimationIntoTakes -q`: 0 with nothing set,
    else "name=<name> start=<frame> end=<frame>" for each (measured). Pure."""
    if not answer:
        return []
    if isinstance(answer, str):
        answer = [answer]
    out = []
    for text in answer:
        match = re.match(r"^name=(.*) start=(\S+) end=(\S+)$", str(text))
        if match:
            try:
                out.append((match.group(1), float(match.group(2)), float(match.group(3))))
            except ValueError:
                pass
    return out


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


@contextlib.contextmanager
def _range_take(start, end):
    """The file's one take cut to `start`..`end` for the length of an export (see TAKE). A plugin
    without splits exports as before: the read-back still refuses keys past the range."""
    prior, delete = None, None
    try:
        prior = parse_split_takes(mel.eval("FBXExportSplitAnimationIntoTakes -q"))
        delete = mel.eval("FBXExportDeleteOriginalTakeOnSplitAnimation -q")
        mel.eval("FBXExportSplitAnimationIntoTakes -c")
        mel.eval(split_command(TAKE, start, end))
        mel.eval("FBXExportDeleteOriginalTakeOnSplitAnimation -v true")
    except Exception:                                            # noqa: BLE001
        pass
    try:
        yield
    finally:
        if prior is not None:
            try:
                mel.eval("FBXExportSplitAnimationIntoTakes -c")
                for name, first, last in prior:
                    mel.eval(split_command(name, first, last))
                if delete is not None:
                    mel.eval("FBXExportDeleteOriginalTakeOnSplitAnimation -v {0}".format(
                        "true" if delete else "false"))
            except Exception:                                    # noqa: BLE001
                pass


def _export_range(fbx_path, start, end):
    with _range_take(start, end):
        mel.eval(export_command(fbx_path))


def _discard(fbx_path):
    try:
        os.remove(fbx_path)
    except OSError:
        pass


def _export_checked(fbx_path, start, end, select):
    """Export the selection cut to `start`..`end`, read the file back, and put a stuck bake rate
    right.

    Returns "" when the bones were baked on every frame of the scene's rate, else the note that
    the plugin had to be reset (the file is then the second export's). Raises RuntimeError, the
    file removed, when even the reset does not help, or when keys past the range reached the file
    (no reset: it cannot help): a clip at the wrong rate or length must not reach Unreal or a
    colleague. `select` puts the export's own selection back after the reset."""
    _export_range(fbx_path, start, end)
    fps = animimport.scene_fps()
    problem = _read_back(fbx_path, fps, start, end)
    if not problem:
        return ""
    rearm_bake_rate()
    _apply_export_options(start, end)
    select()
    _export_range(fbx_path, start, end)
    still = _read_back(fbx_path, fps, start, end)
    if still:
        _discard(fbx_path)
        raise RuntimeError(STUCK.format(still))
    return REARMED.format(problem)


def _read_back(fbx_path, fps, start, end):
    """The file's bake problem inside the range; keys past it refuse there and then."""
    keys = fbxkeys.read_key_times(fbx_path)
    outside = fbxkeys.outside_range(keys, fps, start, end)
    if outside:
        _discard(fbx_path)
        raise RuntimeError(OUTSIDE.format(outside))
    return fbxkeys.bake_problem(keys, fps, start, end)


def rearm_bake_rate():
    """Set the FBX plugin's bake rate to the scene's (see PROBE). The animator's FBX import
    settings, the time unit and the current frame are what they were afterwards."""
    if not os.path.isdir(PROBE_FOLDER):
        os.makedirs(PROBE_FOLDER)
    probe = os.path.join(PROBE_FOLDER, PROBE_FILE)
    node = cmds.createNode("transform", name=PROBE, skipSelect=True)
    try:
        cmds.select(node, replace=True)
        mel.eval("FBXResetExport")
        mel.eval(export_command(probe))
    finally:
        if cmds.objExists(node):
            cmds.delete(node)
    unit = cmds.currentUnit(query=True, time=True)
    frame = cmds.currentTime(query=True)
    mode = mel.eval("FBXImportMode -q")
    set_rate = mel.eval("FBXImportSetMayaFrameRate -q")
    saved = [(path, mel.eval('FBXProperty "{0}" -q'.format(path))) for path, _ in _PROBE_IMPORT]
    try:
        mel.eval("FBXImportMode -v exmerge")
        mel.eval("FBXImportSetMayaFrameRate -v false")
        for path, value in _PROBE_IMPORT:
            mel.eval(_property(path, value))
        mel.eval('FBXImport -f "{0}"'.format(probe.replace("\\", "/")))
    finally:
        for path, value in saved:
            mel.eval(_property(path, value))
        mel.eval("FBXImportMode -v {0}".format(mode))
        mel.eval("FBXImportSetMayaFrameRate -v {0}".format("true" if set_rate else "false"))
        if cmds.currentUnit(query=True, time=True) != unit:
            # the probe is at the scene's rate, so this should never run; if it does, the keys
            # go back with the unit (trap 179)
            cmds.currentUnit(time=unit, updateAnimation=True)
        _put_time(frame)
        try:
            os.remove(probe)
        except OSError:
            pass


def _property(path, value):
    """MEL setting one FBXProperty to `value` as `FBXProperty -q` answered it: a bool comes back
    1 or 0, an enum as its word."""
    if isinstance(value, str):
        text = '"{0}"'.format(value)
    else:
        text = "true" if value else "false"
    return 'FBXProperty "{0}" -v {1}'.format(path, text)


def _put_time(frame):
    """The current frame back where it was, as no undo step (the export runs in one chunk)."""
    if abs(cmds.currentTime(query=True) - frame) < 1e-9:
        return
    try:
        from maya.api import OpenMaya, OpenMayaAnim
        OpenMayaAnim.MAnimControl.setCurrentTime(OpenMaya.MTime(frame, OpenMaya.MTime.uiUnit()))
    except Exception:
        cmds.currentTime(frame, edit=True)


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
    rearmed = ""
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
                chosen = bones + ([wrapper] if wrapper else [])
                cmds.select(chosen, replace=True)
                # read back: the plugin may bake at another session export's rate (fbxkeys)
                rearmed = _export_checked(fbx_path, start, end,
                                          lambda: cmds.select(chosen, replace=True))
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
        rearmed,
    ) if text)

    return {"root": exported_as,
            "joints": len(joints),
            "start": start, "end": end,
            "warning": warning,
            "notes": notes,
            "layout": "cascadeur" if wrapper_used else "plain",
            "wrapper": wrapper_used}
