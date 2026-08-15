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


def joints_under(root):
    """{short name, namespace stripped: full DAG path} for joints under root."""
    found = {}
    for path in cmds.ls(root, dag=True, type="joint", long=True) or []:
        found[path.split("|")[-1].split(":")[-1]] = path
    return found


def _record(created, nodes, parent_path=None):
    """Store created nodes as full paths - a short name can be ambiguous."""
    for node in nodes or []:
        matches = cmds.ls(node, long=True) or []
        if parent_path and len(matches) > 1:
            inside = [m for m in matches if m.startswith(parent_path + "|")]
            matches = inside or matches
        created.append(matches[0] if matches else node)


def build_retarget(source_root=SOURCE_ROOT, target_root=TARGET_ROOT,
                   finger_mode=ABSOLUTE, include_ik_helpers=True,
                   retarget_set=RETARGET_SET):
    """Constrain the suit skeleton to Manny's. Returns a summary dict."""
    for node in (source_root, target_root):
        if not cmds.objExists(node):
            raise RuntimeError("not in the scene: %s" % node)
    if cmds.objExists(retarget_set):
        raise RuntimeError(
            "%s already exists - run remove_retarget() first" % retarget_set)

    source = joints_under(source_root)
    target = joints_under(target_root)
    if SOURCE_SKEL not in source:
        raise RuntimeError("no %r joint under %s" % (SOURCE_SKEL, source_root))

    mapping, unmatched = build_bone_map(sorted(target), sorted(source),
                                        finger_mode)
    side_offset = cmds.getAttr(target_root + ".translateX")
    created = []

    cmds.undoInfo(openChunk=True, chunkName="build_retarget")
    try:
        # Pelvis carries the world position. point + orient, never parent:
        # a parent constraint stores its offset in the source's space and
        # swings the suit through an arc when Manny turns on the spot.
        _record(created, cmds.pointConstraint(
            source["pelvis"], target["pelvis"], maintainOffset=True),
            target["pelvis"])

        for name in sorted(mapping):
            src_name, mode = mapping[name]
            _record(created, cmds.orientConstraint(
                source[src_name], target[name],
                maintainOffset=(mode == OFFSET)), target[name])

        if include_ik_helpers:
            for name in IK_ROOTS:
                if name not in target:
                    continue
                _record(created, cmds.pointConstraint(
                    source[SOURCE_SKEL], target[name], maintainOffset=True),
                    target[name])
                _record(created, cmds.orientConstraint(
                    source[SOURCE_SKEL], target[name], maintainOffset=True),
                    target[name])
            # Both ends live inside the suit, so no side offset is involved
            # and parentConstraint is safe here - it is what Manny uses.
            for name, driver in IK_DRIVEN:
                if name in target and driver in target:
                    _record(created, cmds.parentConstraint(
                        target[driver], target[name], maintainOffset=True),
                        target[name])

        cmds.sets(created, name=retarget_set)
        cmds.addAttr(retarget_set, longName="retargetSideOffset",
                     attributeType="double")
        cmds.setAttr(retarget_set + ".retargetSideOffset", side_offset)
    finally:
        cmds.undoInfo(closeChunk=True)

    summary = {"constraints": len(created), "bones": len(mapping),
               "unmatched": unmatched, "side_offset": side_offset}
    print("retarget: %d constraints over %d bones, side offset %.3f cm"
          % (summary["constraints"], summary["bones"], side_offset))
    if unmatched:
        print("retarget: UNMATCHED target bones: %s" % ", ".join(unmatched))
    return summary


def remove_retarget(retarget_set=RETARGET_SET):
    """Delete every node this tool created. Returns how many were deleted."""
    if not cmds.objExists(retarget_set):
        print("retarget: nothing to remove")
        return 0
    members = cmds.sets(retarget_set, query=True) or []
    alive = [m for m in members if cmds.objExists(m)]
    cmds.undoInfo(openChunk=True, chunkName="remove_retarget")
    try:
        if alive:
            cmds.delete(alive)
        # Maya takes the set down with its last member, so it may already be
        # gone here - deleting it unconditionally raises on a clean teardown.
        if cmds.objExists(retarget_set):
            cmds.delete(retarget_set)
    finally:
        cmds.undoInfo(closeChunk=True)
    print("retarget: removed %d constraint node(s)" % len(alive))
    return len(alive)
