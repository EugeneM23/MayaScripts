"""
Manny -> protective-suit retarget.

Drives the referenced Mesh_protective_suit skeleton from SKM_Manny_Simple with
constraints: the body keeps the suit's own rest pose and receives Manny's
relative world rotation, the fingers copy Manny's grip absolutely.

Design: docs/superpowers/specs/2026-08-15-manny-to-suit-retarget-design.md

Run in Maya (Script Editor, Python tab):
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_retarget; maya_retarget.build_retarget()
"""

import re

import maya.cmds as cmds

SOURCE_ROOT = "SKM_Manny_Simple"
SOURCE_SKEL = "root"
TARGET_ROOT = "Mesh_protective_suit:root"
RETARGET_SET = "retarget_manny_to_suit"

# The suit hangs clavicles and neck on spine_03, Manny on spine_05: those are
# the same bone. Matching by name instead costs 3.5 / 14.1 / 5.9 degrees of
# rest-pose error against 0.00 / 2.75 / 0.65 for this map.
SPINE_MAP = {
    "spine_01": "spine_02",
    "spine_02": "spine_04",
    "spine_03": "spine_05",
}

# Export helpers. Not retargeted from Manny - driven from the suit's own bones,
# exactly as Manny drives its own.
IK_HELPERS = (
    "ik_foot_root", "ik_foot_l", "ik_foot_r",
    "ik_hand_root", "ik_hand_gun", "ik_hand_l", "ik_hand_r",
)
IK_ROOTS = ("ik_foot_root", "ik_hand_root")
IK_DRIVEN = (
    ("ik_foot_l", "foot_l"),
    ("ik_foot_r", "foot_r"),
    ("ik_hand_gun", "hand_r"),
    ("ik_hand_l", "hand_l"),
)

FINGER_RE = re.compile(r"^(thumb|index|middle|ring|pinky)_\d+_[lr]$")

OFFSET = "offset"
ABSOLUTE = "absolute"
MODES = (OFFSET, ABSOLUTE)


def is_finger(name):
    """True for a suit finger bone such as index_01_l, false for metacarpals."""
    return FINGER_RE.match(name) is not None


def build_bone_map(target_names, source_names, finger_mode=ABSOLUTE):
    """Map suit bone -> (Manny bone, mode), plus the target names with no source.

    Pure: takes the two skeletons as lists of short names, touches no scene.
    """
    if finger_mode not in MODES:
        raise ValueError(
            "finger_mode must be one of %s, got %r" % (list(MODES), finger_mode))

    available = set(source_names)
    mapping = {}
    unmatched = []
    for name in target_names:
        if name in IK_HELPERS:
            continue
        source = SPINE_MAP.get(name, name)
        if source not in available:
            unmatched.append(name)
            continue
        mapping[name] = (source, finger_mode if is_finger(name) else OFFSET)
    return mapping, sorted(unmatched)
