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


# The bones a UE clip always carries: with all of them paired by leaf name the clip is
# Unreal's and the transfer below is the one it has been since 2026-10-01; without them
# it is another convention, read by maya_skeletonmap (2026-10-02).
UE_CORE = ("pelvis", "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r",
           "foot_r", "upperarm_l", "lowerarm_l", "hand_l", "upperarm_r", "lowerarm_r",
           "hand_r")             # never the head: a first-person UE clip carries none
SCALE_TOLERANCE = 0.02     # a source within 2 % of the skeleton's size is its size


def ue_covered(pairs):
    """Pure: did the leaf-name pairing find every UE core bone?"""
    return all(name in pairs for name in UE_CORE)


def foreign_pairs(source, target):
    """Pure: {target path: source path} for a source in another convention,
    `source` and `target` being maya_skeletonmap Results. Every bone both map
    pairs through OUR names; the spines and necks pair chain onto chain
    (`distribute`), so a 3-joint source spine drives a 5-joint target at both
    ends and a 3-joint target takes the ends of a 5-joint source. The root is
    the caller's (it is the top of the target, not a mapped bone)."""
    from maya_skeletonmap import distribute
    out = {}
    for ours, path in target.mapping.items():
        if ours == "root" or ours.startswith(("spine_", "neck_")):
            continue
        if ours in source.mapping:
            out[path] = source.mapping[ours]
    for chain in ("spine", "neck"):
        out.update(distribute(source.chains[chain], target.chains[chain]))
    return out


def ground_axis(parent_matrix):
    """Pure: which LOCAL translate channel of a node under `parent_matrix` (16
    floats, or None for world) carries world height - the one a 'horizontal
    travel only' point constraint skips. The Creep's root stands under a -90 X
    Null, where world height is its local Z, not Y."""
    if not parent_matrix:
        return "y"
    rows = [parent_matrix[0:3], parent_matrix[4:7], parent_matrix[8:11]]
    best = max(range(3), key=lambda i: abs(rows[i][1]) / max(1e-12, sum(c * c for c in rows[i]) ** 0.5))
    return "xyz"[best]


def drive_for(name, is_root, twin):
    """How a target bone follows its clip bone: "parent" (the whole world
    matrix, a twin), "orient+point" (root and pelvis of another body),
    "orient" (every other bone of it), or None (its ik_* helpers)."""
    if twin:
        return "parent"
    if is_root or name == "pelvis":
        return "orient+point"
    if name.startswith(HELPERS):
        return None
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


def _why(result):
    """The map's own reason after a transfer that moved nothing, or ""."""
    reason = (result or {}).get("refusal")
    return " ({0})".format(reason) if reason else ""


def _names(names):
    names = list(names)
    shown = ", ".join(names[:SHOWN])
    return shown + (" and {0} more".format(len(names) - SHOWN)
                    if len(names) > SHOWN else "")


def result_line(name, label, top, result, info):
    """The status after a clip went onto a skeleton. Pure."""
    how = ("exact" if result.get("twin")
           else "by rotation (its own proportions)")
    if result.get("convention"):
        how += " from a %s skeleton" % result["convention"]
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


def onto_existing(root, namespace, info, source, name, place):
    """(line, failure): the imported clip transferred onto the skeleton
    `root` already in the scene, which keeps `place` - the clip wrapped,
    turned about its root's first frame and moved there, as a rig keeps its
    place. Our weapon links are released around it and relinked after (the
    old merge's rule). A clip with no bone in common keeps its skeleton and
    is the failure."""
    from maya_scenesetup import bonedrive
    start, end = info.get("start"), info.get("end")
    if start is None:
        return "", "{0} carries no keys - nothing to transfer".format(name)
    links = _links(root)
    for bone, _weapon in links:
        bonedrive.unlink(bone)
    relinked = []
    try:
        shift, source = rigimport._wrap(source, namespace)
        clip_start = cmds.getAttr(source + ".worldMatrix[0]", time=start)
        placed = rigimport.move_wrapper(shift, place, clip_start,
                                        rigimport.facing)
        result = transfer(source, root, start, end)
    finally:
        for bone, weapon in links:
            if cmds.objExists(weapon) and cmds.objExists(bone):
                bonedrive.relink(weapon, bone)
                relinked.append(leaf(bone))
    label = skeleton_label(root)
    if not result["moved"]:
        return "", ("no bone of {0} matches {1} - its skeleton is kept as {2}".format(
            name, label, namespace) + _why(result))
    cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
    line = result_line(name, label, "", result, info)
    parts = [line, placed]
    if relinked:
        parts.append("weapon re-linked on " + ", ".join(relinked))
    return "  |  ".join(parts), ""


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
    line, failure = onto_existing(root, namespace, info, source, name, place)
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


def transfer(source_root, target_root, start, end):
    """The clip under `source_root` onto the skeleton under `target_root`,
    baked over start..end: dict(twin, moved, skipped, missing)."""
    source = dict((leaf(j), j) for j in _joints(source_root))
    targets = [j for j in _joints(target_root) if j != target_root]
    target = dict((leaf(j), j) for j in targets)
    pairs = pair_bones(source, target)
    if not ue_covered(pairs):         # another convention: read it, not its names
        return transfer_foreign(source_root, target_root, start, end)
    if not pairs:                     # nothing in common: touch nothing
        return dict(twin=False, moved=0, skipped=[], missing=sorted(target))
    lengths = [(_length(source[s], start), _length(target[t]))
               for t, s in pairs.items() if not t.startswith(HELPERS)]
    twin = is_twin(lengths)
    plan = [(target_root, source_root, leaf(target_root), True)]
    plan += [(target[t], source[s], t, False) for t, s in sorted(pairs.items())]
    constraints, driven, skipped = [], [], []
    for dst, src, name, is_root in plan:
        mode = drive_for(name, is_root, twin)
        if mode is None:
            skipped.append(name)
            continue
        # A skeleton already in the scene may carry a take: its keys go first,
        # or the constraint splices a pairBlend in (trap 37's mechanism) - the
        # bake below writes the new take. A fresh skeleton has none.
        _cut_time_keys(dst)
        if mode == "parent":
            constraints += cmds.parentConstraint(src, dst, maintainOffset=False)
        else:
            constraints += cmds.orientConstraint(src, dst, maintainOffset=False)
            if mode == "orient+point":
                constraints += cmds.pointConstraint(src, dst, maintainOffset=False)
        driven.append(dst)
    if driven:
        cmds.bakeResults(driven, time=(start, end), simulation=True,
                         sampleBy=1, disableImplicitControl=True,
                         preserveOutsideKeys=False, sparseAnimCurveBake=False,
                         attribute=list(CHANNELS))
    existing = [c for c in constraints if cmds.objExists(c)]
    if existing:
        cmds.delete(existing)
    missing = sorted(name for name in target if name not in pairs
                     and not name.startswith(HELPERS))
    return dict(twin=twin, moved=len(driven), skipped=sorted(skipped),
                missing=missing)


def _world(path, attr="worldMatrix[0]"):
    return list(cmds.getAttr(path + "." + attr))


def _rest_of_target(paths):
    """The target skeleton's rest: its bind (`.bindPose`, the world matrix at
    bind, on a skinned skeleton - ours all are) where every joint has one,
    else the pose it stands in."""
    out = {}
    for path in paths:
        bind = None
        if cmds.attributeQuery("bindPose", node=path, exists=True):
            value = cmds.getAttr(path + ".bindPose")
            if value and any(abs(a - b) > 1e-9 for a, b in zip(
                    value, (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1))):
                bind = list(value)
        out[path] = bind or _world(path)
    return out


def _source_rests(paths):
    """{name: {path: world matrix}}: rotates at 0 (the rest a BVH, a Mixamo or a
    Max FBX keeps in jointOrient) and the clip's first frame."""
    import maya.api.OpenMaya as om
    import maya_skeletonmap as skelmap
    parents = skelmap.parent_map(paths)

    def euler(values):
        import math
        return om.MEulerRotation([math.radians(v) for v in values], 0).asMatrix()
    zero = {}
    for path in sorted(paths, key=lambda p: (p.count("|"), p)):
        local = euler(cmds.getAttr(path + ".rotateAxis")[0]) * euler(
            cmds.getAttr(path + ".jointOrient")[0])
        scale = om.MMatrix()
        for i, v in enumerate(cmds.getAttr(path + ".scale")[0]):
            scale.setElement(i, i, v)
        local = scale * local
        for i, v in enumerate(cmds.getAttr(path + ".translate")[0]):
            local.setElement(3, i, v)
        parent = parents.get(path)
        if parent in zero:
            base = om.MMatrix(zero[parent])
        else:
            above = cmds.listRelatives(path, parent=True, fullPath=True)
            base = om.MMatrix(_world(above[0])) if above else om.MMatrix()
        zero[path] = list(local * base)
    out = {"jointOrient": zero}
    if cmds.keyframe(paths, query=True, keyframeCount=True) or 0:
        first = cmds.findKeyframe(paths, which="first")
        out["firstFrame"] = dict((p, list(cmds.getAttr(p + ".worldMatrix[0]", time=first)))
                                 for p in paths)
    return out


def _rigid(matrix):
    import maya.api.OpenMaya as om
    tm = om.MTransformationMatrix(om.MMatrix(matrix))
    out = om.MTransformationMatrix()
    out.setRotation(tm.rotation(asQuaternion=True))
    out.setTranslation(tm.translation(om.MSpace.kWorld), om.MSpace.kWorld)
    return out.asMatrix()


def _offset_euler(target_rest, source_rest, align, rotate_order):
    """The orientConstraint offset holding W_target = O * W_source, O being
    our rest frame turned by the alignment against the source's rest frame
    (rotation only, in the target's rotate order - measured in
    maya_asretarget 2026-09-05)."""
    import math
    import maya.api.OpenMaya as om
    o = _rigid(target_rest) * om.MMatrix(align) * _rigid(source_rest).inverse()
    tm = om.MTransformationMatrix(o)
    tm.reorderRotation(rotate_order + 1)
    e = tm.rotation(asQuaternion=False)
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def _alignments(canon, target_rest, source_rest, parents, target_live):
    """{our bone: the minimal world rotation taking the target's rest
    direction onto the source's}; a bone with no direction child inherits
    its parent's.

    The target's direction is its child's offset AS THE SKELETON STANDS, in
    the bone's rest frame: the rest frame is the bind (the roll), but where a
    bone points is its child's actual place - Manny's skeleton stands 0.07 cm
    off its own bind at the left calf, and a direction read off the bind
    alone came out 0.0989 deg wrong at every frame (measured 2026-10-02)."""
    import maya.api.OpenMaya as om
    import maya_skeletonmap as skelmap
    children = skelmap.direction_children(parents)

    def at(rest, path):
        m = rest[path]
        return om.MVector(m[12], m[13], m[14])

    def target_direction(bone_path, child_path):
        live = om.MMatrix(target_live[bone_path])
        offset = at(target_live, child_path) - at(target_live, bone_path)
        local = offset * _rigid(live).inverse()
        local = om.MVector(local.x, local.y, local.z)
        return local * _rigid(target_rest[bone_path])
    out = {}
    order = sorted(canon, key=lambda b: _canonical_depth(b, parents))
    for bone in order:
        child = children.get(bone)
        rotation = None
        if child in canon:
            t_dir = target_direction(canon[bone][0], canon[child][0])
            s_dir = at(source_rest, canon[child][1]) - at(source_rest, canon[bone][1])
            if t_dir.length() > 1e-9 and s_dir.length() > 1e-9:
                rotation = list(om.MQuaternion(t_dir.normal(), s_dir.normal()).asMatrix())
        if rotation is None:
            parent = parents.get(bone)
            rotation = out.get(parent, list(om.MMatrix()))
        out[bone] = rotation
    return out


def _canonical_depth(bone, parents):
    depth, node = 0, parents.get(bone)
    while node:
        depth += 1
        node = parents.get(node)
    return depth


def transfer_foreign(source_root, target_root, start, end):
    """A clip in another convention (Mixamo, a Biped, Rigify, Character Creator,
    Daz, a CMU BVH, Unity, VRM ...) onto one of our skeletons, by maya_skeletonmap.

    Both skeletons are read into our names and paired (`foreign_pairs`); every
    paired bone takes the source bone's world ORIENTATION through an offset that
    aligns the two rest poses bone by bone (so it POINTS where the source's bone
    points, and keeps its own length); the pelvis takes the source's position
    too, the root the hips' horizontal travel (or the source's own floor-standing
    root). A source at another size (a BVH, a metre-scale Blender or VRM export)
    is scaled about its own origin for the length of the bake: its travel at the
    skeleton's size. The source's rest is the candidate whose bones point most
    like the target's (`choose_rest`). Returns the transfer dict."""
    import maya_skeletonmap as skelmap
    source_paths = _joints(source_root)
    target_paths = _joints(target_root)
    target_names = sorted(set(leaf(p) for p in target_paths if p != target_root))
    live = dict((p, tuple(cmds.xform(p, query=True, worldSpace=True, translation=True)))
                for p in source_paths)
    found = skelmap.recognize(source_paths, live)
    if found.refusal:
        return dict(twin=False, moved=0, skipped=[], missing=target_names,
                    refusal=found.refusal, convention=found.convention)
    target_rest = _rest_of_target(target_paths)
    target_live = dict((p, _world(p)) for p in target_paths)
    ours = skelmap.recognize(target_paths, dict(
        (p, (m[12], m[13], m[14])) for p, m in target_rest.items()))
    if ours.refusal:
        return dict(twin=False, moved=0, skipped=[], missing=target_names,
                    refusal="the skeleton itself: " + ours.refusal,
                    convention=found.convention)
    pairs = foreign_pairs(found, ours)
    back = dict((path, name) for name, path in ours.mapping.items())
    canon = dict((back[t], (t, s)) for t, s in pairs.items() if t in back)
    parents = skelmap.canonical_parents(dict((n, ts[0]) for n, ts in canon.items()),
                                        skelmap.parent_map(target_paths))
    rests = _source_rests(source_paths)
    target_pos = dict((n, tuple(target_rest[ts[0]][12:15])) for n, ts in canon.items())
    choice, _scores = skelmap.choose_rest(
        dict((name, dict((n, tuple(rest[ts[1]][12:15])) for n, ts in canon.items()))
             for name, rest in rests.items()), target_pos)
    source_rest = rests[choice or "jointOrient"]
    # the size: the target's pelvis over the floor against the source's over its origin
    above = cmds.listRelatives(source_root, parent=True, fullPath=True)
    origin = cmds.xform(above[0], query=True, worldSpace=True, translation=True) \
        if above else [0.0, 0.0, 0.0]
    floor = target_rest[target_root][13]
    scale = skelmap.scale_ratio(target_rest[canon["pelvis"][0]][13] - floor,
                                source_rest[canon["pelvis"][1]][13] - origin[1])
    if abs(scale - 1.0) <= SCALE_TOLERANCE:
        scale = 1.0
    align = _alignments(canon, target_rest, source_rest, parents, target_live)
    uuids = dict((p, cmds.ls(p, uuid=True)[0]) for p in source_paths)
    wrapper = None
    if scale != 1.0:
        namespace = source_root.split("|")[-1].rpartition(":")[0]
        wrapper = cmds.createNode("transform", skipSelect=True,
                                  name=(namespace + ":" if namespace else "") + "skeldarUnitScale",
                                  parent=above[0] if above else None)
        cmds.parent(source_root, wrapper, relative=True)
        cmds.setAttr(wrapper + ".scale", scale, scale, scale)

    def now(path):
        return cmds.ls(uuids[path], long=True)[0]
    constraints, driven = [], []
    root_note = ""
    try:
        for name, (t, s) in sorted(canon.items()):
            _cut_time_keys(t)
            order = cmds.getAttr(t + ".rotateOrder")
            constraints += cmds.orientConstraint(
                now(s), t, offset=_offset_euler(target_rest[t], source_rest[s], align[name], order))
            if name == "pelvis":
                constraints += cmds.pointConstraint(now(s), t, maintainOffset=False)
            driven.append(t)
        _cut_time_keys(target_root)
        if "root" in found.mapping:
            src_root = found.mapping["root"]
            constraints += cmds.orientConstraint(
                now(src_root), target_root, offset=_offset_euler(
                    target_rest[target_root], source_rest[src_root], list(_identity()),
                    cmds.getAttr(target_root + ".rotateOrder")))
            constraints += cmds.pointConstraint(now(src_root), target_root, maintainOffset=False)
            root_note = "root from %s" % leaf(src_root)
        else:
            parent = cmds.listRelatives(target_root, parent=True, fullPath=True)
            skip = ground_axis(_world(parent[0]) if parent else None)
            constraints += cmds.pointConstraint(now(canon["pelvis"][1]), target_root,
                                                maintainOffset=False, skip=[skip])
            root_note = "root takes the hips' horizontal travel"
        driven.append(target_root)
        cmds.bakeResults(driven, time=(start, end), simulation=True, sampleBy=1,
                         disableImplicitControl=True, preserveOutsideKeys=False,
                         sparseAnimCurveBake=False, attribute=list(CHANNELS))
    finally:
        existing = [c for c in constraints if cmds.objExists(c)]
        if existing:
            cmds.delete(existing)
        if wrapper is not None and cmds.objExists(wrapper):
            top = cmds.ls(uuids[source_root], long=True)[0]
            if above:
                cmds.parent(top, above[0], relative=True)
            else:
                cmds.parent(top, world=True, relative=True)
            cmds.delete(wrapper)
    paired = set(t for t, _s in canon.values())
    missing = sorted(leaf(t) for name, t in ours.mapping.items()
                     if name != "root" and t not in paired)
    return dict(twin=False, moved=len(driven), skipped=[], missing=missing,
                convention=found.convention, rest=choice, scale=scale, root=root_note)


def _identity():
    import maya.api.OpenMaya as om
    return om.MMatrix()


def onto_skeleton(entry, namespace, info, source, name, point=None):
    """(line, failure, top): `entry` added and the imported clip
    (`namespace`, its `source` root) transferred onto it, the clip standing
    on the floor `point` first (None: where it is), the clip's skeleton
    deleted; `top` names the new skeleton. A clip with no bone in common
    keeps its skeleton and is the failure."""
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
    result = transfer(source, root, start, end)
    if not result["moved"]:
        return "", ("no bone of {0} matches {1} - its skeleton is kept as {2}".format(
            name, entry.label, namespace) + _why(result)), top
    cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
    line = result_line(name, entry.label, top, result, info)
    return ("{0}  |  {1}".format(line, placed) if placed else line), "", top


def import_onto_skeleton(fbx_path, name, clip_fps=None, set_timeline=True,
                         at=None, entry=None):
    """One clip in the Skeleton mode: imported, put onto a new Characters
    skeleton standing on `at` (None: where the clip is). Returns the
    status line."""
    entry = entry or skeleton_entry()
    namespace, info, source = rigimport.import_source(fbx_path, name, clip_fps,
                                                      set_timeline)
    if source is None:
        return rigimport.NO_JOINT.format(name, namespace)
    line, failure, _top = onto_skeleton(entry, namespace, info, source, name, at)
    return failure or line
