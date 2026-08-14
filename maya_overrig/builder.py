"""Build OverRig setups on the skeleton the picker is bound to.

This module holds the policy -- which joints make up a limb, what gets
recorded, what a rebuild removes. All MEL knowledge lives in overrig.py.
"""

from collections import namedtuple

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
