"""Build OverRig setups on the skeleton the picker is bound to.

This module holds the policy -- which joints make up a limb, what gets
recorded, what a rebuild removes. All MEL knowledge lives in overrig.py.
"""

from collections import namedtuple

import maya.cmds as cmds

from maya_overrig import naming, overrig

BUILD_SET_PREFIX = "RigPicker_build_"

# Three joints per limb, in the order OverRig's IK proc requires:
# root, middle, end. Any other order produces a wrong chain.
LIMBS = (
    ("arm_l", ("upperarm_l", "lowerarm_l", "hand_l")),
    ("arm_r", ("upperarm_r", "lowerarm_r", "hand_r")),
    ("leg_l", ("thigh_l", "calf_l", "foot_l")),
    ("leg_r", ("thigh_r", "calf_r", "foot_r")),
)

BuildResult = namedtuple("BuildResult", "built skipped created removed message")


def limb_joints(scene_map):
    """Limbs whose joints all exist, as (limb name, [three long DAG paths]).

    `scene_map` is the picker's binding map, so prefixes and namespaces are
    already resolved by the time we get here.
    """
    resolved = []
    for name, joints in LIMBS:
        if all(joint in scene_map for joint in joints):
            resolved.append((name, [scene_map[joint] for joint in joints]))
    return resolved


def missing_limbs(scene_map):
    """Names of limbs that cannot be built because a joint is absent."""
    return [name for name, joints in LIMBS
            if not all(joint in scene_map for joint in joints)]


def limb_set(limb):
    """Name of the object set recording one limb's created nodes."""
    return BUILD_SET_PREFIX + limb


def resolve_limbs(nodes, limb_members, scene_map):
    """Which limbs the given nodes touch, in LIMBS order.

    A node counts for a limb when it is one of that limb's recorded nodes, a
    descendant of one, or one of the limb's three source joints. That last
    route is what lets the picker's own limb buttons drive a bake.

    Pure on purpose: `limb_members` is a {limb: [paths]} mapping supplied by
    the caller, so all of this is testable without Maya.
    """
    owner_of_joint = {}
    for name, joints in LIMBS:
        for joint in joints:
            path = scene_map.get(joint)
            if path:
                owner_of_joint[path] = name

    hit = set()
    for node in nodes:
        if node in owner_of_joint:
            hit.add(owner_of_joint[node])
            continue
        for name, members in limb_members.items():
            if any(node == m or node.startswith(m + "|") for m in members):
                hit.add(name)
                break

    return [name for name, _ in LIMBS if name in hit]


def built_limbs():
    """Limbs that currently have nodes recorded against them."""
    return [name for name, _ in LIMBS
            if overrig.set_members(limb_set(name))]


def limbs_in_selection(scene_map):
    """Limbs touched by the current Maya selection."""
    members = {name: overrig.set_members(limb_set(name))
               for name, _ in LIMBS}
    selected = cmds.ls(selection=True, long=True) or []
    return resolve_limbs(selected, members, scene_map)


def character_roots():
    """Skeleton roots that are characters, not rig helpers.

    Anything OverRig created is skipped. Its IK groups contain joints of their
    own, and without this a scene with a build in it reports a dozen skeletons
    instead of one, so the picker refuses to auto-connect.
    """
    return naming.find_skeleton_roots(
        exclude_under=overrig.set_members(overrig.KNOT_SET))


def _ensure_limb_set(limb):
    name = limb_set(limb)
    if not cmds.objExists(name):
        cmds.sets(name=name, empty=True)
    return name


def has_build():
    """True when this tool has anything recorded in the scene."""
    return bool(built_limbs())


def bake_limbs(scene_map, limbs):
    """Bake the given limbs back to FK and remove their OverRig setup.

    Uses OverRig's own selection-scoped primitives, so its structures come
    apart the way it expects. Limbs that were not asked for are never touched,
    and barn_fast_bake_source_obj_and_delete_knots() is never called -- that one
    is scene-global and would take the user's hand-made setups with it.
    """
    resolved = dict(limb_joints(scene_map))
    baked = []
    skipped = []
    removed = 0

    cmds.undoInfo(openChunk=True, chunkName="Rig Picker bake")
    try:
        for limb in limbs:
            members = [m for m in overrig.set_members(limb_set(limb))
                       if cmds.objExists(m)]
            joints = [j for j in resolved.get(limb, []) if cmds.objExists(j)]
            if not members and not joints:
                skipped.append(limb)
                continue

            if joints:
                overrig.fast_bake(joints)
                overrig.delete_constraint_attributes(joints)
            if members:
                cmds.delete(members)
                removed += len(members)
            if cmds.objExists(limb_set(limb)):
                cmds.delete(limb_set(limb))
            baked.append(limb)
    finally:
        cmds.undoInfo(closeChunk=True)

    message = "Baked {0} - {1} node(s) removed".format(
        ", ".join(baked) if baked else "nothing", removed)
    if skipped:
        message += ". Nothing recorded for: " + ", ".join(skipped)
    return BuildResult(baked, skipped, 0, removed, message)


def teardown(scene_map):
    """Bake and remove every limb this tool built."""
    return bake_limbs(scene_map, built_limbs())


def build(scene_map):
    """Build IK on every resolvable limb, replacing any previous build."""
    if not overrig.ensure_loaded():
        return BuildResult(
            [], [], 0, 0,
            "OverRig is not loaded - press the OverRig shelf button "
            "(looked for {0})".format(overrig.MEL_PATH))

    resolvable = limb_joints(scene_map)
    if not resolvable:
        return BuildResult([], [name for name, _ in LIMBS], 0, 0,
                           "No limb joints found on the bound skeleton")

    start, end = overrig.frame_range()
    warning = ""
    if end - start < 1:
        warning = "  (timeline is a single frame - nothing to bake over)"

    built = []
    created = []
    removed = 0

    cmds.undoInfo(openChunk=True, chunkName="Rig Picker build")
    try:
        if has_build():
            removed = teardown(scene_map).removed

        for name, joints in resolvable:
            before = set(overrig.set_members(overrig.KNOT_SET))
            overrig.build_ik(joints)
            after = set(overrig.set_members(overrig.KNOT_SET))

            fresh = sorted(after - before)
            if fresh:
                cmds.sets(fresh, addElement=_ensure_limb_set(name))
                created.extend(fresh)
            built.append(name)
    finally:
        cmds.undoInfo(closeChunk=True)

    skipped = missing_limbs(scene_map)
    message = "Built {0} limb(s), {1} node(s) created".format(
        len(built), len(created))
    if removed:
        message += ", {0} replaced".format(removed)
    if skipped:
        message += ". Skipped: " + ", ".join(skipped)
    return BuildResult(built, skipped, len(created), removed, message + warning)
