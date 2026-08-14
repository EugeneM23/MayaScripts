"""Build OverRig setups on the skeleton the picker is bound to.

This module holds the policy -- which joints make up a limb, what gets
recorded, what a rebuild removes. All MEL knowledge lives in overrig.py.
"""

from collections import namedtuple

import maya.cmds as cmds

from maya_overrig import overrig

BUILD_SET = "RigPicker_build"

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


def _ensure_build_set():
    if not cmds.objExists(BUILD_SET):
        cmds.sets(name=BUILD_SET, empty=True)
    return BUILD_SET


def has_build():
    """True when this tool has a build recorded in the scene."""
    return bool(overrig.set_members(BUILD_SET))


def teardown(scene_map):
    """Remove only what this tool created, using OverRig's own pieces.

    Never calls barn_fast_bake_source_obj_and_delete_knots(): that one is
    scene-global and would take the user's hand-made OverRig setups with it.
    """
    knots = [k for k in overrig.set_members(BUILD_SET) if cmds.objExists(k)]

    sources = [path for _, joints in limb_joints(scene_map) for path in joints]
    sources = [s for s in sources if cmds.objExists(s)]
    if sources:
        overrig.fast_bake(sources)
        overrig.delete_constraint_attributes(sources)

    if knots:
        cmds.delete(knots)
    if cmds.objExists(BUILD_SET):
        cmds.delete(BUILD_SET)

    return BuildResult([], [], 0, len(knots),
                       "Removed {0} node(s)".format(len(knots)))


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
                cmds.sets(fresh, addElement=_ensure_build_set())
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
