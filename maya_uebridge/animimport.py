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


def _apply_import_options(merge):
    """Best-effort: a flag missing on this Maya build must not stop the import."""
    missing = []
    try:
        mel.eval("FBXResetImport")
    except Exception:
        missing.append("FBXResetImport")
    for option in (import_mode_command(merge),) + _IMPORT_OPTIONS:
        try:
            mel.eval(option + ";")
        except Exception:
            missing.append(option.split(" ", 1)[0])
    return missing


def _keyed_joints(curves):
    """The joints those curves drive, as long names.

    listConnections answers with short names; comparing those against the
    long paths a hierarchy walk produces matches nothing, silently, and every
    bone then looks untouched.
    """
    joints = set()
    for curve in curves:
        if not cmds.objExists(curve):
            continue
        for node in (cmds.listConnections(curve, source=False, destination=True,
                                          skipConversionNodes=False) or []):
            if cmds.objExists(node) and cmds.objectType(node) == "joint":
                joints.update(cmds.ls(node, long=True) or [])
    return joints


def wants_merge(namespace, merge):
    """Resolve the import mode: an explicit choice, else follow the namespace."""
    if merge is None:
        return not namespace
    return bool(merge)


def import_mode_command(merge):
    """How the importer treats what is already in the scene.

    `exmerge` - exclusive merge - writes animation onto nodes whose names
    already exist and creates nothing new, which is exactly "put this clip on
    the skeleton I already have". Measured on the Manny scene: 0 new joints,
    819 new curves, 92 of 93 joints keyed.

    `add` brings the clip in as its own skeleton instead.
    """
    return "FBXImportMode -v {0}".format("exmerge" if merge else "add")


NO_TARGET_MESSAGE = (
    "no skeleton in the scene to merge onto - select a joint of the one you "
    "mean, or switch to 'as a new skeleton'")


def _first_few(names):
    """The first four names, sorted, an ellipsis when there are more."""
    shown = ", ".join(sorted(names)[:4])
    if len(names) > 4:
        shown += ", ..."
    return shown


def rigged_target_message(names):
    """Refusal text for a merge onto a skeleton that is still rigged.

    Keying a constrained channel makes Maya splice a pairBlend in, and the
    importer skips other channels entirely, so the merge lands on part of the
    skeleton and the character plays two clips at once (measured: 32 bones on
    the new clip, 60 still on the rig's). Naming the cure beats describing
    the mess.
    """
    shown = _first_few(names)
    return ("the target skeleton is rigged - {0} bone(s) carry constraints "
            "(e.g. {1}); Bake+Delete the rig, then import".format(
                len(names), shown))


def constrained_joints(joints):
    """The joints a rig is still driving, by their constraint children."""
    return [j for j in joints
            if cmds.listRelatives(j, children=True, type="constraint")]

AMBIGUOUS_TARGET_MESSAGE = (
    "several skeletons in the scene - select a joint of the one you mean, or "
    "switch to 'as a new skeleton'")


def _short(node):
    return (node or "").split("|")[-1]


def choose_target_root(roots, selected_roots=()):
    """The skeleton a merge should land on, or None when it is not decidable.

    Namespaced skeletons are never candidates: an exclusive merge matches plain
    bone names, so a namespaced skeleton could not receive the clip anyway -
    and in this tool they are exactly the reference imports of earlier clips.

    Guessing between two plausible skeletons would animate the wrong character
    without saying so, which is worse than asking.
    """
    plain = [root for root in (roots or []) if ":" not in _short(root)]

    chosen = [root for root in (selected_roots or []) if ":" not in _short(root)]
    if chosen:
        return chosen[0]

    if len(plain) == 1:
        return plain[0]

    named = [root for root in plain if _short(root) == "root"]
    if len(named) == 1:
        return named[0]
    return None


def skeleton_roots():
    """Every joint in the scene that has no joint above it."""
    roots = []
    for joint in (cmds.ls(type="joint", long=True) or []):
        if not cmds.listRelatives(joint, parent=True, fullPath=True,
                                  type="joint"):
            roots.append(joint)
    return roots


def selected_roots():
    """The skeleton roots the current selection points at."""
    found = []
    for node in (cmds.ls(selection=True, long=True) or []):
        joints = ([node] if cmds.objectType(node) == "joint" else []) + \
            (cmds.listRelatives(node, allDescendents=True, fullPath=True,
                                type="joint") or [])
        for joint in joints:
            walker = joint
            while True:
                parent = cmds.listRelatives(walker, parent=True, fullPath=True,
                                            type="joint")
                if not parent:
                    break
                walker = parent[0]
            if walker not in found:
                found.append(walker)
    return found


def joints_under(root):
    return [root] + (cmds.listRelatives(root, allDescendents=True,
                                        fullPath=True, type="joint") or [])


def clear_animation(joints):
    """Remove the animation curves driving `joints`, and say how many went.

    Merging onto a skeleton that already carries animation is otherwise
    undecidable: the importer rewrites curves in place, so nothing can be
    measured and leftover bones keep animation from a different clip.
    """
    curves = set()
    for joint in joints:
        for curve in (cmds.listConnections(joint, type="animCurve", source=True,
                                           destination=False) or []):
            curves.add(curve)
    existing = [curve for curve in curves if cmds.objExists(curve)]
    if existing:
        cmds.delete(existing)
    return len(existing)


def merge_warning(matched):
    """Said when a merge matched nothing.

    A name mismatch imports without error and moves nothing at all - the tool
    looks broken rather than mismatched, so it has to say so itself.
    """
    if matched:
        return ""
    return ("no bone names matched, nothing was animated - the skeleton in the "
            "scene may sit in a namespace or carry a prefix the clip does not")


def stale_line(names):
    """Said about bones of the target the clip carried nothing for."""
    if not names:
        return ""
    shown = _first_few(names)
    return "{0} bone(s) not in the clip, now unanimated: {1}".format(
        len(names), shown)


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


def import_clip(fbx_path, namespace=None, set_timeline=True, clip_fps=None,
                merge=None):
    """Bring `fbx_path` into the scene and report what actually arrived.

    With `merge` the clip lands on the skeleton already in the scene, matched
    by bone name, with no namespace - press Import and your own skeleton moves.
    Without it the clip arrives as its own skeleton under `namespace`.

    `merge` left unset follows the namespace: asking for a namespace means
    asking for a separate skeleton. Defaulting to merge regardless would make
    `import_clip(fbx, "SomeName")` quietly ignore the name it was given and
    write over the scene instead.

    What arrived is measured as a scene delta either way, because FBXImport -
    unlike cmds.file - has no way to report what it touched. In merge mode
    there are no new nodes at all, so the delta that matters is the curves.
    """
    merge = wants_merge(namespace, merge)
    if not os.path.isfile(fbx_path):
        raise RuntimeError("no FBX at {0}".format(fbx_path))

    ensure_fbx_plugin()

    target = None
    cleared = 0
    target_joints = []
    if merge:
        roots = skeleton_roots()
        target = choose_target_root(roots, selected_roots())
        if target is None:
            raise RuntimeError(
                AMBIGUOUS_TARGET_MESSAGE if roots else NO_TARGET_MESSAGE)
        target_joints = joints_under(target)
        rigged = constrained_joints(target_joints)
        if rigged:
            raise RuntimeError(rigged_target_message(
                [_short(j) for j in rigged]))
        # Clear first. The importer rewrites curves in place - same names and
        # same uuids, measured - so without this there is no way to tell what
        # the clip touched, and bones missing from the clip would keep frames
        # from whatever was on the skeleton before.
        cleared = clear_animation(target_joints)

    notes = _apply_import_options(merge)

    before_nodes = set(cmds.ls(long=True))
    before_curves = set(cmds.ls(type="animCurve") or [])

    cmds.namespace(setNamespace=":")
    if merge:
        # Exclusive merge matches by name against what is already here, so the
        # import must NOT go into a namespace - a namespace is exactly what
        # stops the names matching.
        mel.eval(import_command(fbx_path))
    else:
        # FBXImport has no namespace flag, but it honours the current one
        # (verified: 116/116 joints and 1081/1081 curves landed inside).
        if not cmds.namespace(exists=namespace):
            cmds.namespace(addNamespace=namespace)
        cmds.namespace(setNamespace=namespace)
        try:
            mel.eval(import_command(fbx_path))
        finally:
            cmds.namespace(setNamespace=":")

    new_nodes = set(cmds.ls(long=True)) - before_nodes
    new_curves = list(set(cmds.ls(type="animCurve") or []) - before_curves)

    if merge:
        touched = _keyed_joints(new_curves)
        joint_count = len(touched)
        # Bones of the target the clip had nothing for. Named because a hand
        # that does not move while the arm does is otherwise a mystery.
        stale = sorted(_short(joint) for joint in target_joints
                       if joint not in touched)
    else:
        joint_count = len([n for n in new_nodes
                           if cmds.objExists(n)
                           and cmds.objectType(n) == "joint"])
        stale = []

    times = cmds.keyframe(new_curves, query=True, timeChange=True) or [] \
        if new_curves else []
    start, end = clip_range(times)

    if set_timeline and start is not None:
        cmds.playbackOptions(minTime=start, maxTime=end,
                             animationStartTime=start, animationEndTime=end)

    warnings = [fps_warning(clip_fps, scene_fps())]
    if merge:
        warnings.append(merge_warning(joint_count))
        warnings.append(stale_line(stale))

    return {"namespace": "" if merge else namespace,
            "merged": bool(merge),
            "target": _short(target) if target else "",
            "cleared": cleared,
            "nodes": len(new_nodes),
            "joints": joint_count,
            "curves": len(new_curves),
            "stale": stale,
            "start": start,
            "end": end,
            "warning": "  |  ".join([w for w in warnings if w]),
            "notes": notes}
