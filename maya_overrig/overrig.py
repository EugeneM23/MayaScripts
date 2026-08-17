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
# OverRig also keeps a set "OverRig_rig_objects" of the source objects it
# has rigged; nothing here reads it (builder._recordable skips it by prefix).

IK_PROC = "apply_rebike_3_or_more_object_to_IK"
BAKE_PROC = "apply_Fast_Bake"
CLEAN_PROC = "delete_constraint_attributes_on_objects"

# The aim. `make_aim_from_selected` only creates the two locators and arms a
# run-once `scriptJob -cf "SomethingSelected"`; the rig itself is built by
# AIM_BUILD_PROC, which that job calls on the next deselect -- which is the gap
# where the animator drags the locators into place by hand. We call the build
# ourselves so placement and the build land in one undo chunk and inside one
# node diff. A build that arrives later is outside both, and the job would
# still be armed to fire a second time.
AIM_SET_PROC = "BOVER_10_2_4b209c5c00abddc3e3509a14326e2488"
AIM_CREATE_PROC = "BOVER_10_2_c642429ed9a3aabf65a66eefcd97bfbb"
AIM_COLOUR_PROC = "BOVER_10_2_2e50fb684e35f7dc58ab390d98530944"
AIM_SIZE_PROC = "BOVER_10_2_6de8028af587b467034457b4d6349f89"
AIM_BUILD_PROC = "BOVER_10_2_10df34add5a583f84d24608e860c1b4b"

# In call order, which is also the order the native button uses.
AIM_PROCS = ("make_aim_from_selected", AIM_SET_PROC, AIM_CREATE_PROC,
             AIM_COLOUR_PROC, AIM_SIZE_PROC, AIM_BUILD_PROC)

AIM_PROCS_MESSAGE = ("OverRig has no procedure {0} - this is not the OverRig "
                     "v10.2 the aim was written against")

# What the native aim button paints its locators. Outliner colour only.
AIM_COLOUR = (0.45, 0.7, 0.45)

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


def missing_aim_procs():
    """Which of the aim procs are not in this session. [] means proceed.

    Four of the six are internal and hash-named. They are `global proc` and
    stable inside v10.2, but an OverRig update can rename them, and the
    failure has to reach the status line naming the proc rather than throwing
    "Cannot find procedure" out of a Qt slot where nobody sees it (trap 20).
    """
    return [p for p in AIM_PROCS if not mel.eval('exists "{0}"'.format(p))]


def mel_gate():
    """The refusal every MEL entry point shares, or None to proceed.

    Two guards, in this order. The toolset must be in the session: without it
    the first Build of a fresh Maya threw "Cannot find procedure" out of the
    Qt slot and the panel just looked dead (trap 20). And the time slider must
    not carry a multi-frame highlight: OverRig reads it before the playback
    range in nineteen bakes, so a bake under one silently clips to the
    highlighted frames and freezes everything outside it (trap 36).
    """
    if not ensure_loaded():
        return NOT_LOADED_MESSAGE
    selection = slider_selection()
    if selection:
        return slider_message(selection)
    return None


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
    one-frame glitches around the current frame.
    """
    saved = (cmds.playbackOptions(query=True, animationStartTime=True),
             cmds.playbackOptions(query=True, animationEndTime=True),
             cmds.playbackOptions(query=True, minTime=True),
             cmds.playbackOptions(query=True, maxTime=True))
    cmds.playbackOptions(animationStartTime=saved[0] - 1,
                         animationEndTime=saved[1] + 1,
                         minTime=saved[2] - 1, maxTime=saved[3] + 1)
    try:
        yield
    finally:
        cmds.playbackOptions(animationStartTime=saved[0],
                             animationEndTime=saved[1],
                             minTime=saved[2], maxTime=saved[3])


def half_frame_times(times):
    """The non-integer key times a doubled-time capture leaves behind.

    Pure. `cmds.keyframe` returns None for a curve with no keys.
    """
    return [t for t in (times or []) if abs(t - round(t)) > 1e-6]


def capture_channel(attr):
    """True when a captured curve on this channel gets its half-frame keys cut.

    Transform channels only -- rotate/translate/scale, plus the pairBlend
    input forms of the same. OverRig's `attach` weight keys its fade half a
    frame outside the range after the rescale; cutting those keys would turn
    a constant weight of 1 into a ramp across the whole clip.
    """
    lowered = (attr or "").lower()
    return any(word in lowered for word in ("rotate", "translate", "scale"))


def slider_message(selection):
    """What every entry point says when the time slider has a highlight."""
    return ("time slider has {0:g}..{1:g} highlighted - OverRig bakes across "
            "the highlight, not the clip; click a single frame on the "
            "timeline and try again".format(selection[0], selection[1]))


def slider_selection():
    """(start, end) highlighted on the time slider, or None.

    OverRig reads `timeControl -q -ra` in nineteen places and bakes across
    it. A highlight the animator dragged and forgot silently decides every
    bake range, so the entry points refuse to run under one.
    """
    slider = mel.eval("$gPlayBackSlider=$gPlayBackSlider")
    if not cmds.timeControl(slider, query=True, rangeVisible=True):
        return None
    got = cmds.timeControl(slider, query=True, rangeArray=True) or []
    if len(got) == 2 and got[1] - got[0] > 1:
        return (got[0], got[1])
    return None


def _curves_driving(nodes):
    """animCurve nodes feeding `nodes`, through pairBlends as well.

    A bone mid-switch is driven `curve -> pairBlend -> bone`, and scaling
    only the directly connected curves would leave that bone playing at the
    wrong rate inside the doubled window.
    """
    curves = set()
    for node in nodes:
        if not cmds.objExists(node):
            continue
        curves.update(cmds.listConnections(node, source=True,
                                           destination=False,
                                           type="animCurve") or [])
        for blend in cmds.listConnections(node, source=True,
                                          destination=False,
                                          type="pairBlend") or []:
            curves.update(cmds.listConnections(blend, source=True,
                                               destination=False,
                                               type="animCurve") or [])
    return sorted(curves)


def _driven_attr(curve):
    """Leaf attribute name the curve's output lands on, or ''."""
    plugs = cmds.listConnections(curve + ".output", source=False,
                                 destination=True, plugs=True) or []
    return plugs[0].split(".")[-1] if plugs else ""


@contextmanager
def full_rate_capture(nodes):
    """Run OverRig's chain capture with every real frame on a sampled slot.

    The capture loop inside `apply_ForwHierarhy` advances its frame counter
    TWICE per iteration (a second `$i++` in the body, base_OverRig_scripts.mel
    ~5404), so the aim-rig helpers that decide each knot's orientation are
    snapped on every second frame and LINEARLY INTERPOLATED in between. The
    dense bake that follows then records an approximation on the skipped
    frames: with the padded range starting at -1 the sampled frames are the
    even ones, and every odd frame of a fast clip came out wrong -- measured
    20.3 cm on a sword-swing's fingers, exactly zero on even frames.

    The cure is to double time around the capture: scale the driving curves
    and the playback range by two, so "every second frame" of the doubled
    clip IS every frame of the real one. Afterwards everything is scaled
    back, and the half-frame keys -- the interpolation artifacts -- are cut
    from the captured transform channels. `attach` weight curves keep their
    half-frame keys: their fade sits half a frame outside the range, which is
    exactly where the unscaled build puts it a whole frame out.

    `nodes` must cover everything whose animation the capture can read:
    the skeleton AND any rig already driving part of it -- a chain captured
    against an unscaled parent records a mixture of two timelines.
    """
    originals = _curves_driving(nodes)
    before = set(cmds.ls(type="animCurve") or [])
    saved = (cmds.playbackOptions(query=True, animationStartTime=True),
             cmds.playbackOptions(query=True, animationEndTime=True),
             cmds.playbackOptions(query=True, minTime=True),
             cmds.playbackOptions(query=True, maxTime=True))
    saved_time = cmds.currentTime(query=True)

    # The capture's range reader falls back to curves selected in the graph
    # editor before it falls back to playback.
    cmds.selectKey(clear=True)
    for curve in originals:
        cmds.scaleKey(curve, timeScale=2, timePivot=0)
    cmds.playbackOptions(animationStartTime=saved[0] * 2,
                         animationEndTime=saved[1] * 2,
                         minTime=saved[2] * 2, maxTime=saved[3] * 2)
    cmds.currentTime(saved_time * 2)
    try:
        yield
    finally:
        fresh = [c for c in (cmds.ls(type="animCurve") or [])
                 if c not in before]
        for curve in fresh:
            if cmds.objExists(curve):
                cmds.scaleKey(curve, timeScale=0.5, timePivot=0)
        for curve in originals:
            if cmds.objExists(curve):
                cmds.scaleKey(curve, timeScale=0.5, timePivot=0)
        cmds.playbackOptions(animationStartTime=saved[0],
                             animationEndTime=saved[1],
                             minTime=saved[2], maxTime=saved[3])
        cmds.currentTime(saved_time)
        for curve in fresh:
            if not cmds.objExists(curve):
                continue
            if not capture_channel(_driven_attr(curve)):
                continue
            for time in half_frame_times(
                    cmds.keyframe(curve, query=True, timeChange=True)):
                cmds.cutKey(curve, time=(time, time), clear=True)


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


def add_to_set(objects, set_name):
    """Register objects in one of OverRig's own bookkeeping sets.

    Through OverRig's own proc rather than `cmds.sets`, so the set is created
    the way OverRig creates it when this is the first thing in the session to
    need it.
    """
    quoted = ",".join('"{0}"'.format(obj) for obj in objects)
    mel.eval('{0}({{{1}}}, "{2}")'.format(AIM_SET_PROC, quoted, set_name))


def aim_outliner_colour():
    """OverRig's aim colour, on whatever is selected.

    Cosmetic and outliner-only -- the proc sets `useOutlinerColor` and
    `outlinerColor`, nothing else. Called exactly where the native button
    calls it: on the selection the create proc leaves behind.
    """
    mel.eval("{0}({{{1}, {2}, {3}}})".format(AIM_COLOUR_PROC, *AIM_COLOUR))


def aim_locator_size(objects, size=1.0):
    """OverRig's locator sizing, on the given objects."""
    cmds.select(list(objects), replace=True)
    mel.eval("{0}({1})".format(AIM_SIZE_PROC, size))


def make_aim_locators(source):
    """Create OverRig's two aim locators on `source`. Returns (top, side).

    The proc returns every top followed by every side, so one source gives
    exactly two names -- anything else means the proc is not the one this was
    written against. It also sets the MEL globals `build_aim` reads.
    """
    cmds.select(source, replace=True)
    created = mel.eval("{0}()".format(AIM_CREATE_PROC)) or []
    if len(created) != 2:
        raise RuntimeError(
            "OverRig returned {0} aim locator(s), expected 2".format(
                len(created)))
    return tuple(cmds.ls(name, long=True)[0] for name in created)


def build_aim():
    """Run the half of OverRig's aim that its scriptJob would have run.

    Driven by the MEL globals `make_aim_locators` set, not by the selection:
    it parent-constrains the locators to the source, bakes so they carry the
    source's world animation, drops those constraints, and aim-constrains the
    source to the locators.

    Not wrapped in `padded_range`: this bake reads `playbackOptions -ast/-aet`
    and never `timeControl -q -ra`, so it neither clips a frame at the ends
    (trap 12) nor answers to a slider highlight (trap 36). Read from the MEL,
    not assumed.
    """
    mel.eval("{0}()".format(AIM_BUILD_PROC))


def delete_constraint_attributes(objects):
    """Strip the constraint channels OverRig adds to source objects."""
    cmds.select(list(objects), replace=True)
    mel.eval("{0}(`ls -sl`)".format(CLEAN_PROC))


def frame_range():
    """Playback range as (start, end)."""
    return (cmds.playbackOptions(query=True, minTime=True),
            cmds.playbackOptions(query=True, maxTime=True))
