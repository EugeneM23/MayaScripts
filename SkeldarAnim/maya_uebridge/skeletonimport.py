"""The Skeleton mode's skeleton: the Characters card's, with its geometry.

2026-10-01, the animator: «Давай сделаем что бы скелет вставлялся с
геометрией» - and, before anything was built, «давай будем использовать
скелет который активен в вкладке character». Asked: the clip goes on by
bone names respecting proportions, and a rig active in Characters means
that model's skeleton.

So the Skeleton mode - the Import button or a drag, one clip or several -
adds the Characters card's skeleton (`character.add_character`: its meshes,
its textures or a palette colour, as Add Character gives them), moves the
clip's own skeleton onto the slot (its root wrapped, the keys untouched),
transfers the clip onto the skeleton bone by bone and bakes it, and deletes
the clip's skeleton - as the rig modes do.

The transfer is measured, not assumed (`is_twin`): a skeleton whose bones
are the clip's lengths (Manny UE5 against a UE5 clip: the median bone 0.0000
off) takes every bone's world matrix and is exact; any other body (the Creep
0.24, the UE4 Mannequin 0.24) takes every bone's world orientation - its own
lengths kept, the mesh not stretched - with root and pelvis placed too, and
its `ik_*` helpers left at rest, their layout being the skeleton's own.

Spec: docs/superpowers/specs/2026-10-01-uebridge-many-animations-design.md
(addendum 3)
"""

import os

import maya.cmds as cmds

from maya_uebridge import rigimport

TWIN_TOLERANCE = 0.01     # the median bone within 1 % of the clip's makes a twin
SHORTEST = 1.0            # cm: shorter bones do not vote
HELPERS = "ik_"           # helper bones a body of its own leaves at rest
UE4_SPINE = {"spine_01": "spine_02", "spine_02": "spine_04", "spine_03": "spine_05"}
NO_FILE = "no skeleton file - {0} is missing from assets/"
SHOWN = 6                 # bone names a status line lists
CHANNELS = ("translateX", "translateY", "translateZ",
            "rotateX", "rotateY", "rotateZ")
TIME_CURVES = ("animCurveTL", "animCurveTA", "animCurveTU", "animCurveTT")


# ------------------------------------------------------------------ pure

def leaf(path):
    """A DAG path's last name without its namespace."""
    return path.split("|")[-1].split(":")[-1]


def skeleton_entry_for(chosen, model=None):
    """The skeleton row the Skeleton mode adds: `chosen` (the Characters
    card's active row) when it is a skeleton; else its model's skeleton -
    `model` (the card's remembered model) when nothing is chosen; else
    Manny UE5 [skeleton]. Pure (the catalog is data)."""
    from maya_scenesetup import catalog
    if chosen is not None and getattr(chosen, "kind", "") == "skeleton":
        return chosen
    model = getattr(chosen, "model", None) or model
    found = catalog.character_for(model, "skeleton") if model else None
    return found or catalog.default_character()


def pair_bones(source_leaves, target_leaves):
    """{target bone: the clip's bone} by leaf name, for the bones both carry.
    A UE4-schema target under a UE5 clip (no spine_04/05 where the clip has
    them) takes `maya_retarget`'s spine map - the same bones, fewer of them."""
    source = set(source_leaves or [])
    target = list(target_leaves or [])
    ue4 = ("spine_05" in source and "spine_05" not in target
           and "spine_04" not in target)
    out = {}
    for name in target:
        wanted = UE4_SPINE.get(name, name) if ue4 else name
        if wanted in source:
            out[name] = wanted
    return out


def is_twin(lengths, tolerance=TWIN_TOLERANCE, shortest=SHORTEST):
    """Whether the (clip, target) bone lengths say the target is the clip's
    own skeleton: the MEDIAN relative difference over the bones longer than
    `shortest` within `tolerance`. Measured on six UE clips: 0.0000 against
    Manny UE5 on every one, 0.2424 against the Creep, 0.2403 against the
    UE4 Mannequin - while the share within 1 % read 0.90 for a 3P clip
    against Manny (3P clips animate bone translations and scale)."""
    diffs = sorted(abs(a - b) / max(a, b) for a, b in lengths
                   if max(a, b) > shortest)
    if not diffs:
        return False
    return diffs[len(diffs) // 2] <= tolerance


def drive_for(name, is_root, twin, mode=None):
    """How a target bone follows its clip bone: "parent" (the whole world
    matrix, a twin), "orient+point" (root and pelvis of another body),
    "orient" (every other bone of it), "orient+scaled" (every bone of another
    body under squash & stretch: turned as the clip's bone and standing on its
    joint at our size), or None (its ik_* helpers).

    `mode` is the retarget version (2026-10-02, `maya_retargetmode`): None the
    legacy rule (a twin whole, another body by rotation); "rotation" never
    whole, a twin too - every bone keeps its length; "stretch" whole for a
    twin, scaled for another body."""
    if twin and mode != "rotation":
        return "parent"
    if name.startswith(HELPERS):
        return None
    if mode == "stretch":
        return "orient+scaled"
    if is_root or name == "pelvis":
        return "orient+point"
    return "orient"


def choose_skeleton(named, rig_labels, bare, labels=None):
    """(root, refusal) for the Skeleton x Onto selected press (2026-10-01).
    Pure.

    `named` are the bare skeleton roots the selection names (repeats
    allowed), `rig_labels` the rigs it names, `bare` every bare skeleton in
    the scene, `labels` {root: what a message calls it}. One named: it.
    Several named: refused. A rig named and no skeleton: refused - the kind
    says skeletons. Nothing named: the only skeleton; none at all: (None, "")
    - a new skeleton is added; several: refused, named."""
    labels = labels or {}

    def name(root):
        return labels.get(root) or root.split("|")[-1]

    picked = list(dict.fromkeys(r for r in named or [] if r))
    if len(picked) == 1:
        return picked[0], ""
    if picked:
        return None, "{0} skeletons selected ({1}) - select one".format(
            len(picked), ", ".join(name(r) for r in picked))
    rigs = list(dict.fromkeys(rig_labels or []))
    if rigs:
        return None, ("{0} is a rig - pick Rig in Animation Setup, or select a "
                      "skeleton".format(", ".join(rigs)))
    bare = list(bare or [])
    if len(bare) == 1:
        return bare[0], ""
    if not bare:
        return None, ""
    return None, ("{0} skeletons in the scene ({1}) - select any bone or mesh "
                  "of the one you mean".format(
                      len(bare), ", ".join(name(r) for r in bare)))


def first_only(names):
    """The note when Onto selected (or a drop on a skeleton) was given
    several: the skeleton takes the first. Pure; "" for one."""
    names = list(names or [])
    if len(names) < 2:
        return ""
    return "only {0}: a skeleton takes one animation ({1} more picked)".format(
        names[0], len(names) - 1)


def _names(names):
    names = list(names)
    shown = ", ".join(names[:SHOWN])
    return shown + (" and {0} more".format(len(names) - SHOWN)
                    if len(names) > SHOWN else "")


def result_line(name, label, top, result, info):
    """The status after a clip went onto a skeleton. Pure."""
    mode = result.get("mode")
    how = ("exact" if result.get("twin") and mode != "rotation"
           else "squashed & stretched to the clip" if mode == "stretch"
           else "by rotation (its own proportions)")
    span = ""
    if (info or {}).get("start") is not None:
        span = ", frames {0:g}-{1:g}".format(info["start"], info["end"])
    who = " ".join(part for part in (label, top) if part)
    parts = ["{0} onto {1}: {2} bones {3}{4}".format(
        name, who, result.get("moved", 0), how, span)]
    if result.get("missing"):
        parts.append("not in the clip: " + _names(result["missing"]))
    if result.get("skipped"):
        parts.append("at rest: " + _names(result["skipped"]))
    return "  |  ".join(parts)


# ------------------------------------------------------------------ scene

def skeleton_entry():
    """The skeleton row, from the Characters card's memory (the card need
    not be open)."""
    chosen, model = None, None
    try:
        from maya_scenesetup import window as scene_window
        chosen = scene_window.chosen_character()
        model = scene_window.remembered_choice()[0]
    except Exception:                                        # noqa: BLE001
        pass
    return skeleton_entry_for(chosen, model)


def precheck(entry=None):
    """The refusal before anything is exported, or ""."""
    from maya_scenesetup import catalog
    entry = entry or skeleton_entry()
    path = catalog.character_file(entry) or ""
    if not path or not os.path.isfile(path):
        return NO_FILE.format(os.path.basename(path) or entry.label)
    return ""


def _joints(root):
    return [root] + (cmds.listRelatives(root, allDescendents=True,
                                        type="joint", fullPath=True) or [])


# -------------------------------------------- onto a skeleton in the scene

def bare_roots():
    """The skeletons in the scene that are no rig's: every character root
    (OverRig's and the armor spaces' joints already left out) that is
    neither under a rig's group nor the game skeleton a rig drives."""
    import maya_rigs
    from maya_overrig import builder
    rigs = maya_rigs.rigs()
    out = []
    for root in builder.character_roots():
        if any(rig.skeleton_root == root for rig in rigs):
            continue
        if any(rig.group and maya_rigs.under(root, rig.group) for rig in rigs):
            continue
        out.append(root)
    return out


def skeleton_label(root):
    """What a message calls a skeleton: the catalog row its Add recorded and
    its root («Manny UE5 [skeleton] (root)»), else its root."""
    leaf_name = root.split("|")[-1]
    try:
        from maya_scenesetup import deletion
        label = deletion.recorded(root)[1]
    except Exception:                                        # noqa: BLE001
        label = ""
    return "{0} ({1})".format(label, leaf_name) if label else leaf_name


def _top_joint(path):
    """The topmost joint above (and including) the joint `path`."""
    top, node = None, path
    while node and cmds.objExists(node) and cmds.objectType(node) == "joint":
        top = (cmds.ls(node, long=True) or [node])[0]
        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        node = parent[0] if parent else None
    return top


def _skin_root(path):
    """The skeleton a mesh (its transform or its shape) is skinned to, as
    the topmost joint of its first influence, or None."""
    shapes = [path] if cmds.objectType(path) == "mesh" else (
        cmds.listRelatives(path, shapes=True, type="mesh", fullPath=True) or [])
    for shape in shapes:
        for skin in cmds.ls(cmds.listHistory(shape) or [], type="skinCluster") or []:
            for joint in cmds.skinCluster(skin, query=True, influence=True) or []:
                return _top_joint(joint)
    return None


def selection_names(selection, bare, rigs):
    """(the bare roots the selection names, the rigs it names): a joint by
    its topmost joint, a mesh by the skeleton it is skinned to, a transform
    by the skeleton under it (the Creep's Armature), a weapon or armor piece
    by the bone its space follows; a rig's node by that rig."""
    import maya_rigs
    from maya_scenesetup import armor, weaponspace
    named, rig_labels = [], []
    for path in selection or []:
        if not cmds.objExists(path):
            continue
        path = weaponspace.hand_for(path) or armor.bone_for(path) or path
        rig = maya_rigs.rig_of(path, rigs)
        if rig is not None:
            rig_labels.append(maya_rigs.label(rig))
            continue
        if cmds.objectType(path) == "joint":
            root = _top_joint(path)
        else:
            root = _skin_root(path) or next(
                (r for r in bare if maya_rigs.under(r, path)), None)
        if root in bare:
            named.append(root)
    return named, rig_labels


def target_skeleton():
    """(root, refusal): the skeleton Skeleton x Onto selected puts the clip
    on - `choose_skeleton` over the scene. (None, "") means none stands:
    the press adds the Characters card's skeleton."""
    import maya_rigs
    rigs = maya_rigs.rigs()
    bare = bare_roots()
    named, rig_labels = selection_names(
        cmds.ls(selection=True, long=True) or [], bare, rigs)
    labels = dict((root, skeleton_label(root)) for root in bare)
    return choose_skeleton(named, rig_labels, bare, labels)


def _links(root):
    """[(bone, weapon)] our weapon tool drives on the skeleton; [] without it."""
    try:
        from maya_scenesetup import bonedrive
    except ImportError:
        return []
    return bonedrive.find_links(_joints(root))


def onto_refusal(root):
    """The refusal before the editor is asked, or "": a bone of the skeleton
    under a constraint that is not our weapon's (a camera on camera_root, a
    rig of somebody's) - the transfer would fight it."""
    from maya_uebridge import animimport
    joints = _joints(root)
    foreign = animimport.foreign_constrained(
        animimport.constrained_joints(joints), [bone for bone, _w in _links(root)])
    if not foreign:
        return ""
    return ("{0}: {1} bone(s) under a constraint that is not ours (e.g. {2}) - "
            "remove it first (a camera: press Camera Setup again)".format(
                skeleton_label(root), len(foreign),
                ", ".join(leaf(j) for j in foreign[:3])))


def skeleton_place(root):
    """Where the skeleton stands now: its root on the current frame, as
    {"point", "yaw", "kept"}. Read before anything moves."""
    matrix = cmds.xform(root, query=True, worldSpace=True, matrix=True)
    return {"point": (matrix[12], matrix[13], matrix[14]),
            "yaw": rigimport.facing(matrix), "kept": True}


def onto_existing(root, namespace, info, source, name, place, decide=None):
    """(line, failure): the imported clip transferred onto the skeleton
    `root` already in the scene, which keeps `place` - the clip wrapped,
    turned about its root's first frame and moved there, as a rig keeps its
    place. Our weapon links are released around it and relinked after (the
    old merge's rule). A clip with no bone in common keeps its skeleton and
    is the failure.

    `decide(source, root, label, start)` answers the retarget version first,
    before anything moves (2026-10-02; None: the legacy transfer); its
    Cancelled removes the clip's namespace and goes on up."""
    import maya_retargetmode
    from maya_scenesetup import bonedrive
    start, end = info.get("start"), info.get("end")
    if start is None:
        return "", "{0} carries no keys - nothing to transfer".format(name)
    decision = None
    if decide is not None:
        try:
            decision = decide(source, root, skeleton_label(root), start)
        except maya_retargetmode.Cancelled:
            cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
            raise
    links = _links(root)
    for bone, _weapon in links:
        bonedrive.unlink(bone)
    relinked = []
    try:
        shift, source = rigimport._wrap(source, namespace)
        clip_start = cmds.getAttr(source + ".worldMatrix[0]", time=start)
        placed = rigimport.move_wrapper(shift, place, clip_start,
                                        rigimport.facing)
        result = _transfer(source, root, start, end, decision)
    finally:
        for bone, weapon in links:
            if cmds.objExists(weapon) and cmds.objExists(bone):
                bonedrive.relink(weapon, bone)
                relinked.append(leaf(bone))
    label = skeleton_label(root)
    if not result["moved"]:
        return "", "no bone of {0} matches {1} - its skeleton is kept as {2}".format(
            name, label, namespace)
    cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
    line = result_line(name, label, "", result, info)
    parts = [line, placed]
    if relinked:
        parts.append("weapon re-linked on " + ", ".join(relinked))
    return _with_reason("  |  ".join(parts), decision), ""


def import_onto_existing(fbx_path, name, root, clip_fps=None, set_timeline=True):
    """One clip onto the skeleton `root` already in the scene (Skeleton x
    Onto selected, or a drop on it). Its place is read before the import.
    Returns the status line."""
    root_uuid = cmds.ls(root, uuid=True)[0]
    place = skeleton_place(root)
    namespace, info, source = rigimport.import_source(fbx_path, name, clip_fps,
                                                      set_timeline)
    if source is None:
        return rigimport.NO_JOINT.format(name, namespace)
    root = cmds.ls(root_uuid, long=True)[0]
    import maya_retargetmode
    try:
        line, failure = onto_existing(root, namespace, info, source, name, place,
                                      decide=choose_for)
    except maya_retargetmode.Cancelled:
        return CANCELLED
    return failure or line


def _length(path, frame=None):
    if frame is None:
        value = cmds.getAttr(path + ".translate")[0]
    else:
        value = cmds.getAttr(path + ".translate", time=frame)[0]
    return sum(v * v for v in value) ** 0.5


def top_name(root):
    """The skeleton's top node: its root, or the group above it (the
    Creep's Armature)."""
    path = (cmds.ls(root, long=True) or [root])[0]
    return path.split("|")[1] if path.count("|") >= 1 else path


def new_skeleton(entry):
    """(root, note): `entry` added, and its topmost new joint."""
    from maya_scenesetup import character
    before = set(cmds.ls(type="joint", long=True) or [])
    note = character.add_character(entry)
    fresh = [j for j in (cmds.ls(type="joint", long=True) or [])
             if j not in before]
    root = min(fresh, key=lambda p: (p.count("|"), p)) if fresh else None
    return root, note


def _cut_time_keys(node):
    """Delete the time curves on `node`'s translate and rotate channels (never
    a driven key's); how many went."""
    curves = set()
    for attr in CHANNELS:
        for curve in (cmds.listConnections(node + "." + attr, source=True,
                                           destination=False,
                                           type="animCurve") or []):
            if cmds.nodeType(curve) in TIME_CURVES:
                curves.add(curve)
    if curves:
        cmds.delete(sorted(curves))
    return len(curves)


STRETCH_TEMP = "skeldarStretch"    # the scaled followers' space, deleted after the bake


def measure(source_root, target_root, start=None, label=""):
    """The clip under `source_root` against the skeleton under `target_root`
    (`maya_retargetmode.Measure`), paired as `transfer` pairs them."""
    import maya_retargetmode
    source = dict((leaf(j), j) for j in _joints(source_root))
    target = dict((leaf(j), j) for j in _joints(target_root))
    pairs = pair_bones(source, target)
    end = None
    if start is not None:
        span = maya_retargetmode.key_span(list(source.values()))
        end = span[1]
    return maya_retargetmode.measure_scene(
        pairs, target, source, start, end, source=maya_retargetmode.clip_name(source_root),
        target=label or leaf(target_root))


def transfer(source_root, target_root, start, end, mode=None, scale=None):
    """The clip under `source_root` onto the skeleton under `target_root`,
    baked over start..end: dict(twin, moved, skipped, missing, mode).

    `mode` is the retarget version (`drive_for`); `scale` our size over the
    clip's for the squash & stretch (measured when not given)."""
    source = dict((leaf(j), j) for j in _joints(source_root))
    targets = [j for j in _joints(target_root) if j != target_root]
    target = dict((leaf(j), j) for j in targets)
    pairs = pair_bones(source, target)
    if not pairs:                     # nothing in common: touch nothing
        return dict(twin=False, moved=0, skipped=[], missing=sorted(target),
                    mode=mode)
    lengths = [(_length(source[s], start), _length(target[t]))
               for t, s in pairs.items() if not t.startswith(HELPERS)]
    twin = is_twin(lengths)
    plan = [(target_root, source_root, leaf(target_root), True)]
    plan += [(target[t], source[s], t, False) for t, s in sorted(pairs.items())]
    constraints, driven, skipped, temp = [], [], [], []
    space = scaled = None
    if mode == "stretch" and not twin:
        import maya_retargetmode
        if scale is None:
            scale = measure(source_root, target_root, start).scale
        space, scaled, _made = maya_retargetmode.scale_space(
            source_root, scale, None, STRETCH_TEMP)
        temp.append(space)
    for dst, src, name, is_root in plan:
        how = drive_for(name, is_root, twin, mode)
        if how is None:
            skipped.append(name)
            continue
        # A skeleton already in the scene may carry a take: its keys go first,
        # or the constraint splices a pairBlend in (trap 37's mechanism) - the
        # bake below writes the new take. A fresh skeleton has none.
        _cut_time_keys(dst)
        if how == "parent":
            constraints += cmds.parentConstraint(src, dst, maintainOffset=False)
        else:
            constraints += cmds.orientConstraint(src, dst, maintainOffset=False)
            if how == "orient+point":
                constraints += cmds.pointConstraint(src, dst, maintainOffset=False)
            elif how == "orient+scaled":
                follower, _made = maya_retargetmode.scaled_follower(
                    src, space, scaled, scale, "{0}_{1}".format(STRETCH_TEMP, name))
                constraints += cmds.pointConstraint(follower, dst, maintainOffset=False)
        driven.append(dst)
    if driven:
        cmds.bakeResults(driven, time=(start, end), simulation=True,
                         sampleBy=1, disableImplicitControl=True,
                         preserveOutsideKeys=False, sparseAnimCurveBake=False,
                         attribute=list(CHANNELS))
    existing = [c for c in constraints if cmds.objExists(c)]
    if existing:
        cmds.delete(existing)
    gone = [node for node in temp if cmds.objExists(node)]
    if gone:
        cmds.delete(gone)
    missing = sorted(name for name in target if name not in pairs
                     and not name.startswith(HELPERS))
    return dict(twin=twin, moved=len(driven), skipped=sorted(skipped),
                missing=missing, mode=mode)


CANCELLED = "cancelled - nothing changed"


def choose_for(source, root, label, start):
    """The retarget version for the clip under `source` onto the skeleton
    `root` (2026-10-02): the Retarget card's setting and the measured clip,
    asked when the stretch would break the skeleton's proportions. Raises
    `maya_retargetmode.Cancelled`."""
    import maya_retargetmode
    return maya_retargetmode.choose(measure(source, root, start, label))


def discard_new(root):
    """A skeleton this press added, deleted whole - Characters' own Delete,
    unasked (a Cancel leaves the scene as it was)."""
    from maya_scenesetup import deletion
    return deletion.delete_selected([root], confirm=lambda _text: True)


def _transfer(source, root, start, end, decision):
    """`transfer` with the decided version (the legacy call without one)."""
    if decision is not None and decision.mode:
        return transfer(source, root, start, end, mode=decision.mode)
    return transfer(source, root, start, end)


def _with_reason(line, decision):
    if decision is not None and decision.reason:
        return "{0}  |  {1}".format(line, decision.reason)
    return line


def onto_skeleton(entry, namespace, info, source, name, point=None, decide=None):
    """(line, failure, top): `entry` added and the imported clip
    (`namespace`, its `source` root) transferred onto it, the clip standing
    on the floor `point` first (None: where it is), the clip's skeleton
    deleted; `top` names the new skeleton. A clip with no bone in common
    keeps its skeleton and is the failure.

    `decide(source, root, label, start)` answers the retarget version
    (2026-10-02; None: the legacy transfer). Its Cancelled deletes the new
    skeleton and the clip's namespace and goes on up."""
    import maya_retargetmode
    root, note = new_skeleton(entry)
    if root is None:
        return "", note or "{0} did not arrive".format(entry.label), None
    root_uuid = cmds.ls(root, uuid=True)[0]
    start, end = info.get("start"), info.get("end")
    placed = ""
    if point is not None:
        at_start = rigimport.root_at(source, start)
        shift, source = rigimport._wrap(source, namespace)
        dx, dy, dz = rigimport.shift_for(point, at_start)
        cmds.move(dx, dy, dz, shift, relative=True, worldSpace=True)
        placed = "standing at floor ({0}, {1})".format(
            int(round(point[0])), int(round(point[2])))
    root = cmds.ls(root_uuid, long=True)[0]
    top = top_name(root)
    if start is None:
        return "", "{0} carries no keys - nothing to transfer".format(name), top
    decision = None
    if decide is not None:
        try:
            decision = decide(source, root, entry.label, start)
        except maya_retargetmode.Cancelled:
            discard_new(root)
            cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
            raise
    result = _transfer(source, root, start, end, decision)
    if not result["moved"]:
        return "", "no bone of {0} matches {1} - its skeleton is kept as {2}".format(
            name, entry.label, namespace), top
    cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
    line = result_line(name, entry.label, top, result, info)
    line = "{0}  |  {1}".format(line, placed) if placed else line
    return _with_reason(line, decision), "", top


def import_onto_skeleton(fbx_path, name, clip_fps=None, set_timeline=True,
                         at=None, entry=None):
    """One clip in the Skeleton mode: imported, put onto a new Characters
    skeleton standing on `at` (None: where the clip is). Returns the
    status line."""
    import maya_retargetmode
    entry = entry or skeleton_entry()
    namespace, info, source = rigimport.import_source(fbx_path, name, clip_fps,
                                                      set_timeline)
    if source is None:
        return rigimport.NO_JOINT.format(name, namespace)
    try:
        line, failure, _top = onto_skeleton(entry, namespace, info, source, name, at,
                                            decide=choose_for)
    except maya_retargetmode.Cancelled:
        return CANCELLED
    return failure or line
