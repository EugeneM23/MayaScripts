"""Thin binding to the OverRig MEL toolset.

Nothing in here decides anything -- it selects objects, calls global MEL procs
and reads OverRig's bookkeeping sets. Policy lives in builder.py.

Every OverRig proc is driven by the current selection, so each call here
selects first. That is OverRig's interface, not a choice.
"""

import os

import maya.cmds as cmds
import maya.mel as mel

# Where the user's Custom shelf button sources the toolset from. Used only as a
# fallback when the procs are not already in the session.
MEL_PATH = ("C:/!!!Work/Animations/Scripts/base_OverRig_scripts_V10_2_f1/"
            "base_OverRig_scripts.mel")

KNOT_SET = "OverRig_knots"
SOURCE_SET = "OverRig_rig_objects"

IK_PROC = "apply_rebike_3_or_more_object_to_IK"
BAKE_PROC = "apply_Fast_Bake"
CLEAN_PROC = "delete_constraint_attributes_on_objects"


def is_loaded():
    """True when OverRig's procs are available in this Maya session."""
    return bool(mel.eval('exists "{0}"'.format(IK_PROC)))


def ensure_loaded():
    """Source the toolset if it is not already in the session.

    Deliberately does not go looking around the disk: either the procs are
    there, or MEL_PATH is, or the caller reports failure and the user presses
    the OverRig shelf button.
    """
    if is_loaded():
        return True
    if not os.path.isfile(MEL_PATH):
        return False
    mel.eval('source "{0}";'.format(MEL_PATH))
    return is_loaded()


def set_members(set_name):
    """Long DAG paths of an object set's members, or [] if it does not exist."""
    if not cmds.objExists(set_name):
        return []
    members = cmds.sets(set_name, query=True) or []
    return cmds.ls(members, long=True) or []


def build_ik(joint_paths):
    """Run OverRig's FK-to-IK on exactly three joints, root to end.

    The proc takes no arguments and reads the selection, and the order of that
    selection decides the chain.
    """
    cmds.select(list(joint_paths), replace=True)
    mel.eval(IK_PROC)


def fast_bake(objects):
    """Bake the given objects using OverRig's own bake."""
    cmds.select(list(objects), replace=True)
    mel.eval(BAKE_PROC)


def delete_constraint_attributes(objects):
    """Strip the constraint channels OverRig adds to source objects."""
    cmds.select(list(objects), replace=True)
    mel.eval("{0}(`ls -sl`)".format(CLEAN_PROC))


def frame_range():
    """Playback range as (start, end)."""
    return (cmds.playbackOptions(query=True, minTime=True),
            cmds.playbackOptions(query=True, maxTime=True))
