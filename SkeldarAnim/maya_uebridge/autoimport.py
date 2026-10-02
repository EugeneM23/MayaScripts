"""The Auto card's import: onto OUR character whose skeleton the clip's is, else in its own.

2026-10-02, the animator: «сделаем карточку рига и скелета со знаком вопроса и когда переносим
анимацию при выбраной этой карточке наш плагин будет смотреть какой скелет в исходном файле если он
найдет скелет который совпадает с нашим то перенесем анимацию на наш риг или скелет, если скрипт
обнаружит что совпадений нету то импортируем в сцену родной риг или скелет». Asked: an explicit
target wins (a selected character, a drop on one), the kind is kept (Rig matches our rigs, Skeleton
our skeletons; a match with no row of that kind comes in its own skeleton), a native is painted in a
palette colour.

One clip, in this order (`import_auto`):

1. imported as its own namespaced skeleton (`rigimport.import_source`) - an Unreal clip with its
   preview mesh (the window asks the editor for it);
2. its bones read over a few frames (`clip_bones`, a plain keyed skeleton: no rig evaluated) and
   matched against our rows of the kind (`skeletonmatch`, `assets/character_skeletons.json`);
3. a rig row matched: that rig added and the clip retargeted onto it (`rigimport.ready_rig` ->
   `decide_bones` -> `retarget_imported`) - a twin, so never asked; a skeleton row matched:
   `skeletonimport.onto_skeleton`; nothing matched: `nativeimport.keep`.

The explicit target (`explicit_rig`, `explicit_skeleton`) is the selection's character of the kind
- never "the only one in the scene": a Kwang clip must not land on the one Manny standing there.

Spec: docs/superpowers/specs/2026-10-02-auto-character-import-design.md
"""

import maya.cmds as cmds

from maya_uebridge import animimport
from maya_uebridge import nativeimport
from maya_uebridge import rigimport
from maya_uebridge import skeletonmatch

KINDS = ("rig", "skeleton")


# --------------------------------------------------------------------- pure

def sample_frames(start, end, count=skeletonmatch.SAMPLES):
    """`count` frames from `start` to `end`, both ends in, whole frames, no repeats; [None] for a
    clip with no keys (read where it stands). Pure."""
    if start is None or end is None:
        return [None]
    if end <= start or count < 2:
        return [float(start)]
    step = (float(end) - float(start)) / (count - 1)
    return sorted(set(float(round(start + step * i)) for i in range(count)))


def pick_rig(selected_rigs):
    """(rig, refusal) the selection names for an Auto press onto a rig: its one rig; two rigs is a
    refusal; none is (None, "") - the Auto card decides. Pure (`maya_rigs.choose_rig`'s wording)."""
    import maya_rigs
    picked = []
    for rig in selected_rigs or []:
        if rig is not None and rig not in picked:
            picked.append(rig)
    if not picked:
        return None, ""
    return maya_rigs.choose_rig(picked, picked)


def label_of(key):
    """A catalog row's label by its key (the key itself for a stranger)."""
    from maya_scenesetup import catalog
    entry = catalog.character_by_key(key)
    return entry.label if entry is not None else key


def join(*parts):
    return "  |  ".join(part for part in parts if part)


# --------------------------------------------------------------------- scene

def _leaf(path):
    return path.split("|")[-1].split(":")[-1]


def clip_bones(source, start=None, end=None):
    """{bone: (parent bone or None, [(x, y, z) per sampled frame])} of the clip skeleton under
    `source`, its names without namespaces, read in a time context - a plain keyed skeleton, so
    nothing of a rig is evaluated (trap 69 is about constraint chains)."""
    joints = [source] + (cmds.listRelatives(source, allDescendents=True, type="joint",
                                            fullPath=True) or [])
    frames = sample_frames(start, end)
    out = {}
    for joint in joints:
        name = _leaf(joint)
        if name in out:
            continue
        parent = cmds.listRelatives(joint, parent=True, type="joint", fullPath=True)
        points = []
        for frame in frames:
            if frame is None:
                matrix = cmds.getAttr(joint + ".worldMatrix[0]")
            else:
                matrix = cmds.getAttr(joint + ".worldMatrix[0]", time=frame)
            points.append((matrix[12], matrix[13], matrix[14]))
        out[name] = (_leaf(parent[0]) if parent and joint != source else None, points)
    return out


def match_clip(source, info, kind):
    """The skeletonmatch.Match of the imported clip among our rows of `kind`."""
    from maya_scenesetup import catalog
    keys = [entry.key for entry in catalog.rows_of_kind(kind)]
    return skeletonmatch.match(clip_bones(source, info.get("start"), info.get("end")),
                               skeletonmatch.load_templates(), keys)


def explicit_rig():
    """(rig, refusal): the rig the selection names (Auto x Onto selected, Rig) - (None, "") when it
    names none."""
    import maya_rigs
    rigs = maya_rigs.rigs()
    selection = cmds.ls(selection=True, long=True) or []
    return pick_rig([maya_rigs.rig_of(path, rigs) for path in selection])


def explicit_skeleton():
    """(root, refusal): the skeleton the selection names (Auto x Onto selected, Skeleton) -
    (None, "") when it names none; a rig named is today's refusal (the kind says skeletons)."""
    import maya_rigs
    from maya_uebridge import skeletonimport
    rigs = maya_rigs.rigs()
    bare = skeletonimport.bare_roots()
    named, rig_labels = skeletonimport.selection_names(
        cmds.ls(selection=True, long=True) or [], bare, rigs)
    labels = dict((root, skeletonimport.skeleton_label(root)) for root in bare)
    return skeletonimport.choose_skeleton(named, rig_labels, [], labels)


class kept_selection(object):
    """The selection as the press found it, put back after it (by UUID).

    A character an Auto press ADDS selects itself - Add Character's rule, so the next press acts
    on it - and the next Auto press, Onto selected, would read that as the animator's explicit
    target: a Kwang clip landing on the Manny the previous press added, its take replaced (the
    review, 2026-10-02). Only a selection the animator made names a target."""

    def __enter__(self):
        try:
            picked = cmds.ls(selection=True, long=True) or []
            # never `ls([], uuid=True)`: with nothing to convert it answers every name (trap 8)
            self.uuids = (cmds.ls(picked, uuid=True) or []) if picked else []
        except Exception:                                    # noqa: BLE001
            self.uuids = None                     # a `cmds` without a scene: nothing to keep
        return self

    def __exit__(self, *_exc):
        if self.uuids is None:
            return False
        try:
            live = [p for u in self.uuids for p in (cmds.ls(u, long=True) or [])]
            if live:
                cmds.select(live, replace=True)
            else:
                cmds.select(clear=True)
        except Exception:                                    # noqa: BLE001
            import traceback
            traceback.print_exc()
        return False


def discard(namespace):
    """A clip skeleton nothing will keep."""
    try:
        if namespace and cmds.namespace(exists=namespace):
            cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
    except Exception:                                        # noqa: BLE001
        import traceback
        traceback.print_exc()


def onto_new_rig(entry, namespace, info, source, name, at=None):
    """(line, failure, label): the rig of `entry` added and the clip retargeted onto it, standing
    on `at` (None: where the clip is). One undo chunk, as the Import press. A Cancel of the
    retarget version (a non-twin only - a match is a twin) deletes the rig and the clip and
    raises maya_retargetmode.Cancelled."""
    import maya_retargetmode
    import maya_rigs
    if not rigimport._rig_file_ok(entry):
        discard(namespace)
        return "", rigimport.NO_RIG_FILE.format(rigimport._rig_file_name(entry)), None
    plan = dict(rig=None, mod=None, add=True, entry=entry)
    cmds.undoInfo(openChunk=True, chunkName="UE anim import + retarget")
    try:
        rig, mod, notes, failure = rigimport.ready_rig(plan)
        if failure:
            discard(namespace)
            return "", join(*(notes + [failure])), None
        try:
            decision = rigimport.decide_bones(rig, mod, source)
        except maya_retargetmode.Cancelled:
            discard(namespace)
            rigimport.discard_added(rig)
            raise
        if decision.reason:
            notes.append(decision.reason)
        place = {"point": tuple(at), "yaw": None} if at is not None else None
        line, failure = rigimport.retarget_imported(rig, mod, namespace, info, source, name,
                                                    place, bones=decision.mode)
    finally:
        cmds.undoInfo(closeChunk=True)
    if failure:
        return "", join(*(notes + [failure])), None
    return join(*(notes + [line])), "", maya_rigs.label(rig)


def onto_new_skeleton(entry, namespace, info, source, name, at=None, decide=None):
    """(line, failure, top): `skeletonimport.onto_skeleton` for the matched skeleton row, its file
    checked first. Cancelled goes on up (onto_skeleton has cleaned up)."""
    from maya_uebridge import skeletonimport
    refusal = skeletonimport.precheck(entry)
    if refusal:
        discard(namespace)
        return "", refusal, None
    return skeletonimport.onto_skeleton(entry, namespace, info, source, name, at,
                                        decide=decide or skeletonimport.choose_for)


def import_auto(fbx_path, name, kind, clip_fps=None, set_timeline=True, at=None):
    """The Auto card's press for one clip. Returns the status line.

    `fbx_path` is a clip reference (an Unreal export with its mesh, a file's clip); `kind` the
    card's [Rig | Skeleton]; `at` a floor point (a drop): the character - ours or its own -
    stands there at the clip's first frame. Refusals of the import take back what it made."""
    if kind not in KINDS:
        return "unknown kind {0!r}".format(kind)
    with kept_selection():
        return _import_auto(fbx_path, name, kind, clip_fps, set_timeline, at)


def _import_auto(fbx_path, name, kind, clip_fps, set_timeline, at):
    import maya_retargetmode
    from maya_scenesetup import catalog
    timing = rigimport.time_state()
    before = set(animimport.existing_namespaces())
    try:
        namespace, info, source = rigimport.import_source(fbx_path, name, clip_fps,
                                                          set_timeline)
    except Exception as error:                               # noqa: BLE001
        undone = rigimport._undo_failed_import(before, {}, None)
        rigimport.restore_time(timing)
        return rigimport.IMPORT_FAILED.format(
            name, rigimport._first_line(str(error)) or type(error).__name__, undone)
    if source is None:
        return rigimport.NO_JOINT.format(name, namespace)
    found = match_clip(source, info, kind)
    why = skeletonmatch.match_text(found, label_of)
    if found.key is None:
        line, failure, _base = nativeimport.keep(namespace, info, source, name, at, why)
        return failure or line
    entry = catalog.character_by_key(found.key)
    try:
        if kind == "rig":
            line, failure, _label = onto_new_rig(entry, namespace, info, source, name, at)
        else:
            line, failure, _top = onto_new_skeleton(entry, namespace, info, source, name, at)
    except maya_retargetmode.Cancelled:
        rigimport.restore_time(timing)
        return rigimport.CANCELLED
    return join(why, failure or line)
