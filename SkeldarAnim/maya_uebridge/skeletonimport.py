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


def _names(names):
    names = list(names)
    shown = ", ".join(names[:SHOWN])
    return shown + (" and {0} more".format(len(names) - SHOWN)
                    if len(names) > SHOWN else "")


def result_line(name, label, top, result, info):
    """The status after a clip went onto a skeleton. Pure."""
    how = ("exact" if result.get("twin")
           else "by rotation (its own proportions)")
    span = ""
    if (info or {}).get("start") is not None:
        span = ", frames {0:g}-{1:g}".format(info["start"], info["end"])
    parts = ["{0} onto {1} {2}: {3} bones {4}{5}".format(
        name, label, top, result.get("moved", 0), how, span)]
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


def transfer(source_root, target_root, start, end):
    """The clip under `source_root` onto the skeleton under `target_root`,
    baked over start..end: dict(twin, moved, skipped, missing)."""
    source = dict((leaf(j), j) for j in _joints(source_root))
    targets = [j for j in _joints(target_root) if j != target_root]
    target = dict((leaf(j), j) for j in targets)
    pairs = pair_bones(source, target)
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
                         attribute=["translateX", "translateY", "translateZ",
                                    "rotateX", "rotateY", "rotateZ"])
    existing = [c for c in constraints if cmds.objExists(c)]
    if existing:
        cmds.delete(existing)
    missing = sorted(name for name in target if name not in pairs
                     and not name.startswith(HELPERS))
    return dict(twin=twin, moved=len(driven), skipped=sorted(skipped),
                missing=missing)


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
        return "", "no bone of {0} matches {1} - its skeleton is kept as {2}".format(
            name, entry.label, namespace), top
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
