"""Bringing the exported FBX into the Maya scene.

One rule dominates this module: the scene's frame rate is never written. The
animator is working in that scene while the tool runs, and silently changing
its frame rate would be the most destructive thing this bridge could do. A
mismatch is reported and the import proceeds.
"""

import contextlib
import os
import re

import maya.cmds as cmds
import maya.mel as mel

FBX_PLUGIN = "fbxmaya"

# The prefix the OTHER characters' joints wear for the length of one
# exclusive merge. Nothing in this project or in UE is called anything
# like it, and it is only ever on disk if Maya dies mid-import.
HOLD_PREFIX = "rpHold_"

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


def foreign_constrained(constrained, linked_bones):
    """The constrained joints that are NOT ours to unlink. Pure.

    A weapon-driven bone (weapon_r riding the sword since 2026-08-21) is
    released and re-linked around the merge, so it must not count as "the
    skeleton is rigged" -- but anything else constrained still refuses.
    """
    ours = set(linked_bones)
    return [joint for joint in constrained if joint not in ours]


def relink_note(bones):
    """Status text for the weapon links rebuilt after the merge."""
    if not bones:
        return ""
    return "weapon re-linked on " + ", ".join(bones)


def unheld_warning(names):
    """Status text when another character could not be held aside. Pure.

    Worth a warning rather than a refusal: the merge still lands on the
    right names for the target, but a joint left holding its plain name in
    another character could have taken the clip too.
    """
    if not names:
        return ""
    unique = sorted(set(names))
    return ("{0} joint(s) of another character could not be renamed out of "
            "the way ({1}) - check they kept their animation".format(
                len(unique), ", ".join(unique[:3])))


def _weapon_links(joints):
    """[(bone, weapon)] our weapon tool drives; [] when scenesetup is absent.

    Lazy and guarded on purpose: the bridge must work in a Maya that never
    installed the weapon tool, and a bare import here would be a hard
    dependency for every user of the window.
    """
    try:
        from maya_scenesetup import bonedrive
    except ImportError:
        return []
    return bonedrive.find_links(joints)

AMBIGUOUS_TARGET_MESSAGE = (
    "several skeletons in the scene - select a joint of the one you mean, or "
    "switch to 'as a new skeleton'")


def _short(node):
    return (node or "").split("|")[-1]


def choose_target_root(roots, selected_roots=(), bound_root=None):
    """The skeleton a merge should land on, or None when it is not decidable.

    The order the animator asked for (2026-09-01): "Import and Export
    should first look at whether a bone hierarchy is SELECTED, and if the
    selection is not empty, import onto the bones in the selection. If the
    selection is empty, then look at the connect."

        selection -> the picker's connected character -> the only skeleton
        -> the one called `root` -> refuse

    `bound_root` is the picker's binding, which is the animator's explicit
    statement of which character they are working on. It sits ahead of
    "the only skeleton" so that a scene holding several characters is
    decidable at all without clicking a bone first.

    Namespaced skeletons found by scanning the scene are never candidates:
    an exclusive merge matches plain bone names, so a namespaced skeleton
    could not receive the clip anyway - and in this tool they are exactly
    the reference imports of earlier clips. The CONNECT is the exception
    since 2026-09-08: a rig's game skeleton lives in the rig's namespace
    (`|Manny_Rig:root`), the connect names it on purpose, and the export
    strips the namespace for the length of the call (`target_plain_names`).

    Guessing between two plausible skeletons would animate the wrong
    character without saying so, which is worse than asking.
    """
    def plain_only(paths):
        return [root for root in (paths or [])
                if root and ":" not in _short(root)]

    plain = plain_only(roots)

    chosen = plain_only(selected_roots)
    if chosen:
        return chosen[0]

    if bound_root:
        return bound_root

    if len(plain) == 1:
        return plain[0]

    named = [root for root in plain if _short(root) == "root"]
    if len(named) == 1:
        return named[0]
    return None


def connected_root():
    """The character Scene Setup would act on, or None.

    Since 2026-09-07 that is `maya_scenesetup.skeleton.current_root()` --
    the selection (a rig control or a joint), then the AdvancedSkeleton
    rig's skeleton, then the sole skeleton -- where it used to be the Rig
    Picker's Connect. Lazy and guarded: the bridge is plain `cmds`, and a
    session without `maya_scenesetup` keeps the older rule below (the sole
    skeleton, then the one named `root`).
    """
    try:
        from maya_scenesetup import skeleton
        return skeleton.current_root()
    except Exception:
        return None


def resolve_target():
    """The skeleton to merge onto, asking the scene the three questions.

    `connected_root` already applies the selection, so the selection slot
    and the connect slot agree by construction; Import, Export and Add
    Weapon can never name different characters.
    """
    return choose_target_root(skeleton_roots(), selected_roots(),
                              connected_root())


def skeletons_to_hold(roots, target):
    """Plain-named skeletons other than the target. Pure.

    Choosing the right target is not enough on its own. `FBXImport -v
    exmerge` matches bone names INSIDE the FBX plugin, so with two Mannys
    in the scene `pelvis` is ambiguous and the plugin lands on whichever
    it finds first - the animator asked for one character and the other
    one moves.

    Namespaced skeletons are left alone: their bones cannot collide with
    the plain names the merge matches, and a REFERENCED skeleton (always
    namespaced) could not be renamed anyway.
    """
    return [root for root in (roots or [])
            if root and root != target and ":" not in _short(root)]


def hold_name(short):
    """The name a held-aside joint wears for one merge. Pure."""
    return HOLD_PREFIX + short


# The UE skeleton's root bone. Not a new assumption: `choose_target_root`
# already falls back to "the skeleton called `root`", and the hold above
# already rests on "`root` is a bone in every UE clip".
UE_ROOT = "root"

_TRAILING_DIGITS = re.compile(r"[0-9]+$")


def plain_root_name(root_short, bone_shorts):
    """The undecorated name behind a clashing root, or "". Pure.

    Maya will not let two nodes at world level share a short name - a
    top-level node's path IS its short name - so a second character has
    exactly ONE joint renamed: its root. Everything below keeps its plain
    name, because its path is unique already. An exmerge matches by name,
    so the clip's `root` reaches nothing and the character plays the clip
    on the spot while the first one walks.

    Two decorations exist, both measured: a trailing run of digits (a
    `duplicate`, a plain rename, the FBX importer) and the file stem
    (`cmds.file(i=True)` of Manny_Skeleton.ma gives `Manny_Skeleton_root`).

    Decorated **relative to its own skeleton**, which is the exact
    statement of the mechanism: only the top node ever collides, so a
    prefix the rest of the skeleton also wears was never a collision.
    `ik_foot_root` is a bone of the UE schema and its own children are
    `ik_foot_l` and `ik_foot_r` - they wear the prefix, so it is left
    alone. So is a root genuinely called something else. The answer is
    then "" and the behaviour is exactly what it was.
    """
    short = _short(root_short)
    leaf = short.split(":")[-1]
    if not leaf:
        return ""
    if leaf == UE_ROOT:
        # `ns:root` (a rig's skeleton, 2026-09-08) wants the plain name; a
        # bare `root` already has it.
        return UE_ROOT if ":" in short else ""
    stripped = _TRAILING_DIGITS.sub("", leaf)
    if stripped == UE_ROOT:
        return UE_ROOT
    if not stripped.endswith("_" + UE_ROOT):
        return ""
    prefix = stripped[:-len(UE_ROOT)]
    others = [_short(name).split(":")[-1] for name in (bone_shorts or [])]
    if any(name != leaf and name.startswith(prefix) for name in others):
        return ""
    return UE_ROOT


def root_note(actual, used):
    """Said when the root wore a different name for the transfer. Pure.

    Without it the next person finds one name in the outliner and another
    in the FBX, with nothing to go on.
    """
    if not actual or not used or actual == used:
        return ""
    return "root motion: `{0}` treated as `{1}`".format(actual, used)


def _rename_back(uuid, short):
    """Put a name back, resolved from the UUID.

    Never from a path recorded earlier: renaming a root invalidates the
    path of every joint beneath it, and `cmds.ls(stale, uuid=True)` then
    answers nothing at all (traps 16 and 48).
    """
    paths = cmds.ls(uuid, long=True) or []
    if not paths:
        return                # the animator deleted it mid-import
    try:
        cmds.rename(paths[0], short)
    except RuntimeError:
        pass                  # nothing better to do; the name is cosmetic


@contextlib.contextmanager
def target_root_plain(target_root, joints):
    """The target's OWN root wears its undecorated name for the length of
    the call. Yields the name it took, or "" when nothing was renamed.

    `other_skeletons_held` frees the names the OTHER characters hold; this
    is the other half, and without it the clip's `root` matches nothing on
    every character after the first (measured: 67 of 68 bones).

    Three steps. Free the name - whatever answers to it is renamed aside
    with the same `rpHold_` prefix, which on the import path has already
    happened and on the export path has not. Rename the root, and CHECK
    the name Maya actually gave it: `cmds.rename` onto a taken name
    succeeds with `root1` rather than failing, and `root1` matches the
    clip no better than the name we started with. Then restore in a
    `finally`, ours first so the name is free for whatever was displaced.

    A wrong answer costs nothing: the rename either matches the clip's
    root or matches nothing, which is exactly today's behaviour, and
    either way the name is put back.
    """
    leaf = _short(target_root)
    wanted = plain_root_name(leaf, [_short(j) for j in (joints or [])
                                    if _short(j) != leaf])
    root_uuid = ""
    if wanted:
        root_uuid = (cmds.ls(target_root, uuid=True) or [""])[0]
    if not root_uuid:
        yield ""
        return

    displaced = []
    blocked = False
    for node in (cmds.ls(wanted, long=True) or []):
        uuid = (cmds.ls(node, uuid=True) or [None])[0]
        if not uuid or uuid == root_uuid:
            continue
        try:
            cmds.rename(node, hold_name(wanted))
        except RuntimeError:
            blocked = True    # locked, referenced, read-only
            break
        displaced.append((uuid, wanted))

    took = ""
    path = (cmds.ls(root_uuid, long=True) or [None])[0]
    if not blocked and path:
        try:
            if _short(cmds.rename(path, wanted)) == wanted:
                took = wanted
            else:
                _rename_back(root_uuid, leaf)
        except RuntimeError:
            pass
    try:
        yield took
    finally:
        if took:
            _rename_back(root_uuid, leaf)
        for uuid, short in reversed(displaced):
            _rename_back(uuid, short)


def namespace_of(path):
    """The namespace of a path's own node, "" for the root namespace. Pure."""
    short = _short(path)
    return short.rsplit(":", 1)[0] if ":" in short else ""


def plain_names_plan(target_root, joints):
    """Which joints of the target wear a namespace, as (path, plain leaf). Pure.

    The root is left to `target_root_plain`, which handles its collision.
    """
    out = []
    for joint in joints or []:
        if joint == target_root:
            continue
        if namespace_of(joint):
            out.append((joint, _short(joint).split(":")[-1]))
    return out


@contextlib.contextmanager
def target_plain_names(target_root, joints):
    """Every joint of the target wears its leaf name in the ROOT namespace
    for the length of the call. Yields the name the root took, or "".

    Since 2026-09-08 a rig lives in a namespace, and **the FBX exporter
    writes the namespace into the file** -- measured: `rigns:root`,
    `rigns:pelvis`, and no flag strips it -- so Unreal would receive bones
    its skeleton does not have. `cmds.rename(path, ":pelvis")` moves a node
    into the root namespace (measured, and back again with the prefix), and
    the root's own collision with a plain `root` in the scene is handled by
    `target_root_plain`, which frees the name first. A plain-named skeleton
    strips nothing and behaves exactly as before.

    Resolved by UUID on the way back: renaming a parent invalidates every
    path beneath it (traps 16 and 48). Restored in a `finally`, the root
    first so the namespace is whole again before its children rejoin it.
    """
    wanted = []
    for path, leaf in plain_names_plan(target_root, joints):
        uuid = (cmds.ls(path, uuid=True) or [None])[0]
        if uuid:
            wanted.append((uuid, _short(path), leaf))
    stripped = []
    for uuid, short, leaf in wanted:
        paths = cmds.ls(uuid, long=True) or []
        if not paths:
            continue
        try:
            if _short(cmds.rename(paths[0], ":" + leaf)) == leaf:
                stripped.append((uuid, short))
            else:
                _rename_back(uuid, short)
        except RuntimeError:
            pass                  # locked, referenced; the bone keeps its name
    root_uuid = (cmds.ls(target_root, uuid=True) or [None])[0]
    root_now = (cmds.ls(root_uuid, long=True) or [target_root])[0] \
        if root_uuid else target_root
    try:
        with target_root_plain(root_now, joints) as took:
            yield took
    finally:
        for uuid, short in reversed(stripped):
            _rename_back(uuid, short)


@contextlib.contextmanager
def other_skeletons_held(target_root, roots=None):
    """Rename every other character's joints out of the merge's way.

    A rename is invisible to connections - constraints, skinClusters and
    animCurves are wired to nodes, not to names - and it is the only lever
    that reaches inside the FBX plugin's own name matching.

    Resolved through UUIDs on the way back: renaming a root changes every
    descendant's path (trap 16), so the recorded paths are stale by the
    second node. Restored in a `finally`, and skipped entirely when there
    is nothing to hold, which is every single-character scene the tool has
    ever run in.

    `roots` narrows the candidates; None means every skeleton in the
    scene, which is what an import wants. It exists so a verify run can
    exercise the mechanism on its own throwaway characters instead of
    renaming the animator's.
    """
    candidates = skeleton_roots() if roots is None else roots

    # Every UUID collected BEFORE the first rename, and each path resolved
    # from its UUID again right before its own rename. `root` is a bone in
    # every UE clip, so it is held like any other -- and renaming it
    # invalidates the path of every joint beneath it (trap 16). Measured
    # 2026-09-01: walking the paths straight through renamed the root and
    # SILENTLY skipped all twenty bones under it, so the merge stayed
    # exactly as ambiguous as before.
    wanted = []
    for root in skeletons_to_hold(candidates, target_root):
        for joint in joints_under(root):
            short = _short(joint)
            if short.startswith(HOLD_PREFIX):
                continue
            uuid = (cmds.ls(joint, uuid=True) or [None])[0]
            if uuid:
                wanted.append((uuid, short))

    held = []
    failed = []
    for uuid, short in wanted:
        paths = cmds.ls(uuid, long=True) or []
        if not paths:
            failed.append(short)
            continue
        try:
            cmds.rename(paths[0], hold_name(short))
        except RuntimeError:
            failed.append(short)   # locked, referenced, read-only
            continue
        held.append((uuid, short))
    try:
        yield failed
    finally:
        for uuid, short in reversed(held):
            paths = cmds.ls(uuid, long=True) or []
            if not paths:
                continue          # the animator deleted it mid-import
            try:
                cmds.rename(paths[0], short)
            except RuntimeError:
                pass              # nothing better to do; the name is cosmetic


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
    links = []
    root_as = ""
    if merge:
        roots = skeleton_roots()
        target = resolve_target()
        if target is None:
            raise RuntimeError(
                AMBIGUOUS_TARGET_MESSAGE if roots else NO_TARGET_MESSAGE)
        target_joints = joints_under(target)
        # Our weapon-driven bones are released around the merge and re-linked
        # after it; the refusal fires on the OTHER constrained joints only.
        # Reading before refusing is load-bearing: a refusal must leave the
        # scene exactly as it was, so nothing is unlinked yet.
        links = _weapon_links(target_joints)
        rigged = foreign_constrained(constrained_joints(target_joints),
                                     [bone for bone, _ in links])
        if rigged:
            raise RuntimeError(rigged_target_message(
                [_short(j) for j in rigged]))
        if links:
            from maya_scenesetup import bonedrive
            for bone, _weapon in links:
                bonedrive.unlink(bone)
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
        # stops the names matching. For the same reason the OTHER characters
        # are held aside by name for the length of the call: `pelvis` has to
        # mean exactly one joint while the plugin is matching.
        #
        # And the target's OWN root is renamed to its plain name inside
        # that, because Maya renamed exactly one of its joints when the
        # character arrived - the root - and without this the clip's
        # `root` matches nothing on every character after the first.
        # Nested, so the hold has already freed the name.
        with other_skeletons_held(target) as failed_to_hold:
            with target_root_plain(target, target_joints) as root_as:
                mel.eval(import_command(fbx_path))
        unheld = list(failed_to_hold)
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

    # After the timeline is set, so the re-link's bake range unions against
    # the CLIP's range rather than whatever the scene showed before.
    relinked = []
    if merge and links:
        from maya_scenesetup import bonedrive
        for bone, weapon in links:
            if cmds.objExists(weapon) and cmds.objExists(bone):
                bonedrive.relink(weapon, bone)
                relinked.append(_short(bone))

    warnings = [fps_warning(clip_fps, scene_fps())]
    if merge:
        warnings.append(merge_warning(joint_count))
        warnings.append(root_note(_short(target), root_as))
        warnings.append(stale_line(stale))
        warnings.append(relink_note(relinked))
        warnings.append(unheld_warning(unheld))

    return {"relinked": relinked,
            "namespace": "" if merge else namespace,
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
