"""A portrait dropped on a character standing in the scene swaps it (2026-10-17).

The animator: «когда я переносил драгом наш риг на сцену и попадал в стоящий в сцене скелет с
анимацией то скелет удалялся а анимация пересаживалась на наш риг по правилам ретаргета ... скелет
на скелет ... скелет на РИГ ... мы должны сработать на уровне скелетной анимации».

Every combination is one road: the old character's game skeleton is baked into a plain copy (what the
UE Bridge's import leaves), the new character is added and the copy retargeted onto it with the
bridge's own rules (the proportions question included), what the old one carried is carried, the
animator's objects constrained to it are re-bound to the new one (else baked), and the old one goes
whole. Spec: docs/superpowers/specs/2026-10-17-character-swap-design.md.
"""
from __future__ import absolute_import

import math

import maya.cmds as cmds
import maya_timewarp

import maya_rigs
from maya_scenesetup import catalog


COPY_BASE = "swapTake"
NEAREST_CM = 5.0           # a rig control maps onto the game bone standing within this of it
HELPERS = ("ik_", "weapon_", "camera_", "center_of_mass", "interaction")   # never a control's bone
TRANSFORM_ATTRS = ("translateX", "translateY", "translateZ",
                   "rotateX", "rotateY", "rotateZ")
CONSTRAINT_TYPES = ("parentConstraint", "pointConstraint", "orientConstraint",
                    "scaleConstraint", "aimConstraint")
CANCELLED = "cancelled - nothing changed"


# ------------------------------------------------------------------ pure

def leaf(path):
    return (path or "").split("|")[-1].split(":")[-1]


def take_range(playback, animation, keys):
    """(start, end): whole frames covering the playback range, the animation range and every key."""
    times = list(playback) + list(animation) + list(keys or [])
    return float(math.floor(min(times))), float(math.ceil(max(times)))


def nearest(point, bones, limit=NEAREST_CM):
    """The key of `bones` ({name: (x, y, z)}) nearest `point`, None past `limit`."""
    best, best_d = None, None
    for name, p in bones.items():
        d = math.sqrt(sum((a - b) ** 2 for a, b in zip(point, p)))
        if best_d is None or d < best_d:
            best, best_d = name, d
    if best is None or best_d > limit:
        return None
    return best


def map_target(kind, name, new_kind, new_bones, new_controls, near_bone=None, weapons=None):
    """(new name, same kind) for an old constraint target, or (None, False). Pure.

    `kind` is "bone" (a joint of the old game skeleton), "control" (any other node of an old rig),
    "weapon" or "other"; `new_bones` / `new_controls` the new character's {leaf: path};
    `near_bone` the leaf of the old game bone standing nearest an old control; `weapons` {old: new}."""
    if kind == "weapon":
        new = (weapons or {}).get(name)
        return (new, True) if new else (None, False)
    if kind == "bone":
        new = new_bones.get(leaf(name))
        return (new, True) if new else (None, False)
    if kind == "control":
        if new_kind == "rig" and leaf(name) in new_controls:
            return new_controls[leaf(name)], True
        if near_bone and near_bone in new_bones:
            return new_bones[near_bone], False
    return None, False


def swap_caption(old_label, new_label):
    return "swap {0} for {1}".format(old_label, new_label)


def swap_line(old_label, new_label, retarget, carried, rebound, baked, deleted, notes=()):
    """What the status says after the whole press. Pure."""
    parts = ["{0} swapped for {1}".format(old_label, new_label)]
    if retarget:
        parts.append(retarget)
    if carried:
        parts.append("carried: " + ", ".join(carried))
    if rebound:
        parts.append("re-bound to it: " + ", ".join(rebound))
    if baked:
        parts.append("baked in place: " + ", ".join(baked))
    parts.extend(n for n in notes if n)
    if deleted:
        parts.append(deleted)
    return "  |  ".join(parts)


# ------------------------------------------------------------------ scene: reading

def _uuid(node):
    return (cmds.ls(node, uuid=True) or [""])[0]


def _path(uuid):
    return (cmds.ls(uuid, long=True) or [None])[0] if uuid else None


def _parent(path):
    return (cmds.listRelatives(path, parent=True, fullPath=True) or [None])[0]


def old_character(root):
    """The `deletion.Character` whose root is `root`, or None."""
    from maya_scenesetup import deletion
    wanted = (cmds.ls(root, long=True) or [root])[0]
    for char in deletion.characters():
        if char.root and (cmds.ls(char.root, long=True) or [char.root])[0] == wanted:
            return char
    return None


def game_joints(root):
    """The root and every joint below it, parents first."""
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                          fullPath=True) or [])
    return sorted(joints, key=lambda p: (p.count("|"), p))


def _controls(rig):
    if rig is None or not rig.control_set or not cmds.objExists(rig.control_set):
        return []
    return cmds.ls(cmds.sets(rig.control_set, query=True) or [], long=True) or []


def range_of(char):
    """The old character's take range."""
    nodes = game_joints(char.root) + _controls(char.rig)
    keys = cmds.keyframe(nodes, query=True, timeChange=True) or [] if nodes else []
    playback = (cmds.playbackOptions(query=True, min=True),
                cmds.playbackOptions(query=True, max=True))
    animation = (cmds.playbackOptions(query=True, animationStartTime=True),
                 cmds.playbackOptions(query=True, animationEndTime=True))
    return take_range(playback, animation, keys)


def clip_name(char):
    """The clip the old character plays (its label), else its label."""
    try:
        from maya_scenesetup import cliplabel
        for label in cliplabel.labels_of(char.root):
            name = cliplabel.clip_of(label)
            if name:
                return name
    except Exception:                                        # noqa: BLE001
        pass
    return char.label.split(" (")[0]


def survey(root):
    """What the old character carries: dict(weapons=[(side, entry, where, point, heading)],
    armor=[entry], camera=bool, com=bool, follows=[side])."""
    from maya_scenesetup import armor, camera, equip, skeleton
    out = dict(weapons=[], armor=[], camera=False, com=False, follows=[])
    for side in catalog.SIDES:
        weapon, where = equip.occupant(root, side)
        if not weapon:
            hold = equip.holdings(root).get(side)
            if hold is not None and getattr(hold, "where", "") == "follows":
                out["follows"].append(side)
            continue
        entry = equip.entry_of(weapon)
        if entry is None:
            continue
        point = tuple(cmds.xform(weapon, query=True, worldSpace=True, translation=True))
        m = cmds.xform(weapon, query=True, worldSpace=True, matrix=True)
        heading = (m[0], 0.0, m[2]) if abs(m[0]) + abs(m[2]) > 1e-6 else (1.0, 0.0, 0.0)
        out["weapons"].append((side, entry, where, point, heading, weapon))
    for key in sorted(armor.worn(root)):
        row = catalog.armor_by_key(key)
        if row is not None:
            out["armor"].append(row)
    bone = skeleton.resolve_bone(root, camera.BONE)
    out["camera"] = bool(bone and camera.camera_for(bone))
    try:
        from maya_com import network
        out["com"] = bool(network.group_for(network._character_for(root)))
    except Exception:                                        # noqa: BLE001
        out["com"] = False
    return out


def _targets(con, kind):
    command = getattr(cmds, kind)
    names = command(con, query=True, targetList=True) or []
    return [(i, (cmds.ls(n, long=True) or [n])[0]) for i, n in enumerate(names)]


def _object_of(con):
    driven = cmds.listConnections(con + ".constraintParentInverseMatrix", source=True,
                                  destination=False, fullNodeName=True) or []
    if driven:
        return (cmds.ls(driven[0], long=True) or [None])[0]
    return _parent(con)


def foreign_constraints(core, skip=()):
    """[(constraint, kind, object, [(index, target)])] of constraints outside `core` (uuids)
    with a target inside it - the animator's props riding the old character."""
    from maya_scenesetup import deletion
    out = []
    for kind in CONSTRAINT_TYPES:
        for con in cmds.ls(type=kind, long=True) or []:
            uuid = _uuid(con)
            if uuid in core or uuid in skip:
                continue
            if cmds.attributeQuery(deletion.HAND_LINK, node=con, exists=True):
                continue
            targets = [(i, t) for i, t in _targets(con, kind) if _uuid(t) in core]
            obj = _object_of(con)
            if not targets or not obj or _uuid(obj) in core:
                continue
            out.append((con, kind, obj, targets))
    return out


# ------------------------------------------------------------------ scene: the take as a clip

def _free_namespace(base):
    from maya_uebridge import animimport, records
    return records.namespace_for(base, animimport.existing_namespaces())


def bake_copy(root, start, end):
    """(namespace, source root, info): a plain copy of the skeleton under `root` in a root-level
    namespace, baked onto the original's world motion over [start, end]."""
    joints = game_joints(root)
    namespace = _free_namespace(COPY_BASE)
    cmds.namespace(add=":" + namespace)
    copies, made = {}, []
    for joint in joints:
        parent = copies.get(_parent(joint))
        name = ":{0}:{1}".format(namespace, leaf(joint))
        kwargs = dict(name=name, skipSelect=True)
        if parent:
            kwargs["parent"] = parent
        new = cmds.createNode("joint", **kwargs)
        new = cmds.ls(new, long=True)[0]
        for attr in ("rotateOrder", "segmentScaleCompensate"):
            try:
                cmds.setAttr(new + "." + attr, cmds.getAttr(joint + "." + attr))
            except Exception:                                # noqa: BLE001
                pass
        for attr in ("jointOrient", "translate", "rotate", "scale"):
            value = cmds.getAttr(joint + "." + attr)[0]
            cmds.setAttr(new + "." + attr, *value)
        copies[joint] = new
        made.append(new)
    # the paths of the copies, read again (a parent made after its child moved nothing, but be sure)
    made = [cmds.ls(_uuid(m), long=True)[0] for m in made]
    temporary = []
    for joint, copy in zip(joints, made):
        temporary += cmds.parentConstraint(joint, copy, maintainOffset=False)
    maya_timewarp.call(cmds.bakeResults, made, time=(start, end), simulation=True, sampleBy=1,
                     attribute=list(TRANSFORM_ATTRS), disableImplicitControl=True,
                     preserveOutsideKeys=False, sparseAnimCurveBake=False)
    cmds.delete([c for c in temporary if cmds.objExists(c)])
    curves = cmds.listConnections(made, type="animCurveTA", source=True,
                                  destination=False) or []
    if curves:
        try:
            cmds.filterCurve(curves, filter="euler")
        except Exception:                                    # noqa: BLE001
            pass
    source = cmds.ls(made[0], long=True)[0]
    return namespace, source, {"start": start, "end": end}


def _drop_namespace(namespace):
    if namespace and cmds.namespace(exists=":" + namespace):
        cmds.namespace(removeNamespace=":" + namespace, deleteNamespaceContent=True)


# ------------------------------------------------------------------ scene: the new character

def _onto_rig(entry, namespace, info, source, name):
    """(new root, rig, line, failure)."""
    import maya_retargetmode
    from maya_uebridge import rigimport
    plan = dict(rig=None, mod=None, add=True, entry=entry)
    rig, mod, notes, failure = rigimport.ready_rig(plan)
    if failure:
        return None, rig, "", "  |  ".join(notes + [failure])
    try:
        decision = rigimport.decide_bones(rig, mod, source)
    except maya_retargetmode.Cancelled:
        rigimport.discard_added(rig)
        raise
    line, failure = rigimport.retarget_imported(rig, mod, namespace, info, source, name,
                                                bones=decision.mode)
    line = decision.reason or (line or "").split("  |  ")[0]
    fresh = maya_rigs.find(rig.namespace) or rig
    if failure:
        return fresh.skeleton_root, fresh, "", failure
    return fresh.skeleton_root, fresh, line, ""


def _onto_skeleton(entry, namespace, info, source, name):
    """(new root, None, line, failure)."""
    from maya_uebridge import skeletonimport
    before = set(cmds.ls(type="joint", long=True) or [])
    line, failure, _top = skeletonimport.onto_skeleton(
        entry, namespace, info, source, name, decide=skeletonimport.choose_for)
    fresh = [j for j in cmds.ls(type="joint", long=True) or []
             if j not in before and not j.split("|")[-1].startswith(namespace + ":")]
    root = min(fresh, key=lambda p: (p.count("|"), p)) if fresh else None
    parts = (line or "").split("  |  ")
    return root, None, parts[-1] if len(parts) > 1 else parts[0], failure


# ------------------------------------------------------------------ scene: carrying

def carry(survey_, new_root, start, end):
    """(texts, {old weapon: new weapon}) - what the old character carried, onto the new one."""
    from maya_scenesetup import armor, camera, equip, skeleton
    texts, weapons = [], {}
    for side, entry, where, point, heading, old in survey_["weapons"]:
        try:
            if where == "floor":
                equip.to_floor(new_root, entry, (point[0], 0.0, point[2]), heading, side=side)
            else:
                equip.to_hand(new_root, side, entry)
            new, _where = equip.occupant(new_root, side)
            if new:
                weapons[old] = new
                texts.append("{0} {1}".format(entry.label,
                                              "on the floor" if where == "floor"
                                              else "in the " + equip.SIDE_LABEL[side]))
        except Exception as error:                           # noqa: BLE001
            texts.append("{0} not carried ({1})".format(entry.label, _first(error)))
    for entry in survey_["armor"]:
        try:
            armor.equip(new_root, entry)
            texts.append(entry.label)
        except Exception as error:                           # noqa: BLE001
            texts.append("{0} not carried ({1})".format(entry.label, _first(error)))
    if survey_["camera"]:
        bone = skeleton.resolve_bone(new_root, camera.BONE)
        if bone and not camera.camera_for(bone):
            try:
                camera.setup(bone, start, end)
                texts.append("camera")
            except Exception as error:                       # noqa: BLE001
                texts.append("camera not set up ({0})".format(_first(error)))
        elif bone:
            texts.append("camera")
    if survey_["com"]:
        try:
            from maya_com import engine, network
            char = network._character_for(new_root)
            if not network.group_for(char):
                model, info = network.build_model(char)
                engine.track(network.create(char, model, info))
            texts.append("centre of mass")
        except Exception as error:                           # noqa: BLE001
            texts.append("centre of mass not carried ({0})".format(_first(error)))
    return texts, weapons


def _first(error):
    lines = [l for l in str(error).splitlines() if l.strip()]
    return lines[0] if lines else type(error).__name__


# ------------------------------------------------------------------ scene: re-binding

def _old_kind(target, old_bones, old_rig, weapons):
    if target in weapons:
        return "weapon"
    if target in old_bones:
        return "bone"
    if old_rig is not None and old_rig.namespace and \
            maya_rigs.namespace_of(target) == old_rig.namespace:
        return "control"
    if old_rig is not None and maya_rigs.under(target, old_rig.group):
        return "control"
    return "other"


def _bone_points(bones):
    """{leaf: world point} of the body bones (helpers stand on them: ik_hand_gun on hand_r)."""
    return dict((leaf(b), tuple(cmds.xform(b, query=True, worldSpace=True, translation=True)))
                for b in bones if not leaf(b).startswith(HELPERS))


def _offsets(con, index):
    return dict((a, cmds.getAttr("{0}.target[{1}].{2}".format(con, index, a))[0])
                for a in ("targetOffsetTranslate", "targetOffsetRotate"))


def _index_of(con, kind, target):
    for i, t in _targets(con, kind):
        if _uuid(t) == _uuid(target):
            return i
    return None


def _weight(con, kind, index):
    aliases = getattr(cmds, kind)(con, query=True, weightAliasList=True) or []
    if index < len(aliases):
        try:
            return cmds.getAttr(con + "." + aliases[index])
        except Exception:                                    # noqa: BLE001
            pass
    return 1.0


def _rebind(con, kind, obj, index, old, new, same):
    command = getattr(cmds, kind)
    weight = _weight(con, kind, index)
    if kind == "parentConstraint":
        saved = _offsets(con, index)
        command(new, obj, weight=weight, maintainOffset=not same)
        at = _index_of(con, kind, new)
        if same and at is not None:
            for attr, value in saved.items():
                cmds.setAttr("{0}.target[{1}].{2}".format(con, at, attr), *value)
    else:
        offset = cmds.getAttr(con + ".offset")[0] if cmds.attributeQuery(
            "offset", node=con, exists=True) else None
        command(new, obj, weight=weight)
        if offset is not None:
            cmds.setAttr(con + ".offset", *offset)
    command(old, obj, edit=True, remove=True)


def _bake_object(obj, start, end):
    attrs = [a for a in TRANSFORM_ATTRS
             if cmds.getAttr("{0}.{1}".format(obj, a), settable=True)
             or cmds.listConnections("{0}.{1}".format(obj, a), source=True, destination=False)]
    maya_timewarp.call(cmds.bakeResults, obj, time=(start, end), simulation=True, sampleBy=1,
                     attribute=attrs or list(TRANSFORM_ATTRS), disableImplicitControl=True,
                     preserveOutsideKeys=True, sparseAnimCurveBake=False)


def rebind_all(found, old_char, new_root, new_rig, weapons, start, end):
    """(re-bound names, baked names): every foreign constraint of `found` moved onto the new
    character, or its object baked where no counterpart stands."""
    old_bones = set(game_joints(old_char.root))
    old_points = _bone_points(old_bones)
    new_bones = dict((leaf(b), b) for b in game_joints(new_root))
    new_controls = {}
    if new_rig is not None:
        for control in _controls(new_rig):
            new_controls[leaf(control)] = control
    rebound, baked = [], []
    for con, kind, obj, targets in found:
        plan, ok = [], True
        for index, target in targets:
            what = _old_kind(target, old_bones, old_char.rig, weapons)
            near = None
            if what == "control":
                near = nearest(tuple(cmds.xform(target, query=True, worldSpace=True,
                                                translation=True)), old_points)
            new, same = map_target(what, target, "rig" if new_rig is not None else "skeleton",
                                   new_bones, new_controls, near, weapons)
            if new is None or (kind != "parentConstraint" and not same):
                ok = False
                break
            plan.append((index, target, new, same))
        name = leaf(obj)
        if ok:
            try:
                for index, target, new, same in plan:
                    _rebind(con, kind, obj, index, target, new, same)
                rebound.append(name)
                continue
            except Exception:                                # noqa: BLE001
                pass
        if cmds.objExists(con):
            _bake_object(obj, start, end)
            if cmds.objExists(con):
                cmds.delete(con)
        baked.append(name)
    return rebound, baked


# ------------------------------------------------------------------ the press

@maya_timewarp.wrapped
def swap(entry, root):
    """The character standing at `root` swapped for a new `entry`. Returns the status line."""
    import maya_retargetmode
    from maya_scenesetup import deletion
    from maya_uebridge import rigimport

    if entry is None:
        return "nothing to swap in"
    char = old_character(root)
    if char is None:
        return "no character at {0}".format(leaf(root))
    refusal = deletion._refusal([char])
    if refusal:
        return refusal
    start, end = range_of(char)
    name = clip_name(char)
    carried = survey(char.root)
    old_plan = deletion.plan([char])
    skip = deletion._holder_constraints(maya_rigs.rigs())
    found = foreign_constraints(set(old_plan.core), skip)
    timing = rigimport.time_state()
    frame = cmds.currentTime(query=True)

    namespace, source, info = bake_copy(char.root, start, end)
    try:
        if catalog.is_rig(entry):
            new_root, new_rig, line, failure = _onto_rig(entry, namespace, info, source, name)
        else:
            new_root, new_rig, line, failure = _onto_skeleton(entry, namespace, info, source, name)
    except maya_retargetmode.Cancelled:
        _drop_namespace(namespace)
        rigimport.restore_time(timing)
        return CANCELLED
    except Exception:
        _drop_namespace(namespace)
        raise
    _drop_namespace(namespace)
    if failure or not new_root:
        return "{0}: {1} - {2} kept".format(entry.label, failure or "it did not arrive",
                                            char.label)

    notes = []
    texts, weapons = carry(carried, new_root, start, end)
    if carried["follows"]:
        notes.append("Connections links not carried (" + ", ".join(carried["follows"]) + ")")
    rebound, baked = rebind_all(found, char, new_root, new_rig, weapons, start, end)

    fresh = old_character(char.root) or char
    deleted = deletion.execute(deletion.plan([fresh]))
    cmds.currentTime(frame)
    try:
        cmds.select(new_rig.main if new_rig is not None else new_root, replace=True)
    except Exception:                                        # noqa: BLE001
        pass
    new_label = maya_rigs.label(new_rig) if new_rig is not None else entry.label
    return swap_line(char.label, new_label, line, texts, rebound, baked, _first_line(deleted),
                     notes)


def _first_line(text):
    lines = [l for l in (text or "").splitlines() if l.strip()]
    return lines[0] if lines else ""
