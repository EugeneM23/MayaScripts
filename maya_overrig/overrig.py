"""Thin binding to the OverRig MEL toolset.

Nothing in here decides anything -- it selects objects, calls global MEL procs
and reads OverRig's bookkeeping sets. Policy lives in builder.py.

Every OverRig proc is driven by the current selection, so each call here
selects first. That is OverRig's interface, not a choice.
"""

import os
from contextlib import contextmanager

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

# What every entry point says when the toolset is not in the session. One
# wording, because there is one cure: nothing here works without the procs.
NOT_LOADED_MESSAGE = (
    "OverRig is not loaded - press the OverRig shelf button "
    "(looked for {0})".format(MEL_PATH))


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
    """Long DAG paths of an object set's members, or [] if it does not exist.

    Resolved member by member: `sets -q` returns shortest-unique names, and
    pushing the whole list through one `ls` call lets any name that became
    ambiguous expand to EVERY match. OverRig reuses `fin_jnt1` inside every
    limb rig, so that expansion put one arm's joints into the other arm's
    manifest -- a bake then dragged the wrong limb in and aborted. Ambiguous
    names are settled by actual set membership.
    """
    if not cmds.objExists(set_name):
        return []
    out = []
    for member in cmds.sets(set_name, query=True) or []:
        paths = cmds.ls(member, long=True) or []
        if len(paths) > 1:
            paths = [p for p in paths if cmds.sets(p, isMember=set_name)]
        out.extend(paths)
    return list(dict.fromkeys(out))


_PAD_DEPTH = [0]


@contextmanager
def padded_range():
    """One frame of playback padding around an OverRig capture or bake.

    OverRig's CHAIN CAPTURE procs clip a frame at each end of the range: a
    pose keyed only at the first and last frames came out of
    `apply_ForwHierarhy` as a CONSTANT track holding the interior value --
    fingers posed at frame 0 fell to where they were on frame 1 after a
    rebuild. Widening the playback range by one frame on each side keeps
    the real range fully inside the capture.

    Scope this to the capture procs ONLY (ForwHierarhy, parentConstrAnim,
    the rebike IK): `apply_Fast_Bake` and `apply_Parent_in/out` measured
    zero drift for weeks without padding, and blanket padding introduced
    one-frame glitches around the current frame. Re-entrant: only the
    outermost use pads.
    """
    if _PAD_DEPTH[0]:
        _PAD_DEPTH[0] += 1
        try:
            yield
        finally:
            _PAD_DEPTH[0] -= 1
        return

    saved = (cmds.playbackOptions(query=True, animationStartTime=True),
             cmds.playbackOptions(query=True, animationEndTime=True),
             cmds.playbackOptions(query=True, minTime=True),
             cmds.playbackOptions(query=True, maxTime=True))
    _PAD_DEPTH[0] += 1
    cmds.playbackOptions(animationStartTime=saved[0] - 1,
                         animationEndTime=saved[1] + 1,
                         minTime=saved[2] - 1, maxTime=saved[3] + 1)
    try:
        yield
    finally:
        _PAD_DEPTH[0] -= 1
        cmds.playbackOptions(animationStartTime=saved[0],
                             animationEndTime=saved[1],
                             minTime=saved[2], maxTime=saved[3])


def build_ik(joint_paths):
    """Run OverRig's FK-to-IK on exactly three joints, root to end.

    The proc takes no arguments and reads the selection, and the order of that
    selection decides the chain.
    """
    cmds.select(list(joint_paths), replace=True)
    with padded_range():
        mel.eval(IK_PROC)


def fast_bake(objects):
    """Bake the given objects using OverRig's own bake."""
    cmds.select(list(objects), replace=True)
    mel.eval(BAKE_PROC)


def parent_out(node):
    """Lift a node to world through OverRig, animation re-baked into it."""
    cmds.select(node, replace=True)
    mel.eval("apply_Parent_out()")


def parent_in(child, parent):
    """Hang a node inside another, animation re-baked into the new space.

    Selection is child first, parent last -- verified by experiment.
    """
    cmds.select([child, parent], replace=True)
    mel.eval("apply_Parent_in()")


def delete_constraint_attributes(objects):
    """Strip the constraint channels OverRig adds to source objects."""
    cmds.select(list(objects), replace=True)
    mel.eval("{0}(`ls -sl`)".format(CLEAN_PROC))


def frame_range():
    """Playback range as (start, end)."""
    return (cmds.playbackOptions(query=True, minTime=True),
            cmds.playbackOptions(query=True, maxTime=True))
