"""Applying an edit. Small on purpose: the arithmetic is not here.

Two things it owns and nothing else does.

**One undo chunk per drag.** A drag delivers ~860 events (measured) and each
one writes; without a chunk Ctrl+Z unpicks the gesture into hundreds of
steps. `begin`/`end` are counted, so a nested call cannot leave a chunk open.

**The throttle.** Following the dragged key with the current time is what
makes the feature what the animator asked for -- «править кривые и сразу же
смотреть на результат» -- and it is also a full rig evaluation. Their scene
runs 10.4 fps, so it is gated to ~20 Hz with one guaranteed evaluation when
the mouse comes up.

The keys moved are the ones MAYA has selected. `cmds.keyframe` with
`animation="keys"` takes them with no list to pass, which is also why undo
and the Graph Editor stay in step with us for free.
"""

import maya.cmds as cmds

from maya_curveview import mapping

_real_cmds = cmds

_depth = 0


def begin():
    """Open the undo chunk for a drag."""
    global _depth
    if _depth == 0:
        cmds.undoInfo(openChunk=True, chunkName="curveOverlayDrag")
    _depth += 1


def end():
    """Close it. Safe to call more often than `begin`."""
    global _depth
    if _depth <= 0:
        _depth = 0
        return
    _depth -= 1
    if _depth == 0:
        cmds.undoInfo(closeChunk=True)


def in_chunk():
    return _depth > 0


def apply_delta(dt, dv):
    """Move the selected keys by (dt, dv), relative.

    The caller sends the DIFFERENCE from what it has already applied, never
    the running total: snapping the time to whole frames on a total would
    re-round every event and accumulate drift over hundreds of them.
    """
    if abs(float(dt)) < 1e-9 and abs(float(dv)) < 1e-9:
        return
    cmds.keyframe(edit=True, relative=True, animation="keys",
                  timeChange=float(dt), valueChange=float(dv),
                  option="over")


def set_tangent(curve, index, side, angle):
    """Point one tangent handle at `angle` degrees."""
    flag = "inAngle" if side == "in" else "outAngle"
    cmds.keyTangent(curve, edit=True, index=(int(index), int(index)),
                    **{flag: float(angle)})


def insert_key(curve, at_time):
    """A key on the curve at `at_time`, leaving the shape alone.

    `insert=True` is what keeps the curve's shape: it plants the key and
    re-fits the neighbouring tangents instead of moving the curve to meet a
    value.
    """
    cmds.setKeyframe(curve, insert=True, time=(float(at_time),
                                               float(at_time)))


def delete_selected():
    """Remove the selected keys. Returns how many went.

    Counted BEFORE the cut: `cutKey(clear=True)` answers 0 even when it
    worked (measured live 2026-09-05 -- the keys were gone and the status
    line said "Deleted 0 key(s)", which reads as a tool that did nothing).
    """
    try:
        doomed = len(cmds.keyframe(query=True, selected=True,
                                   timeChange=True) or [])
    except Exception:
        doomed = 0
    if not doomed:
        return 0
    try:
        cmds.cutKey(animation="keys", clear=True)
    except Exception:
        return 0
    return doomed


def follow_time(at_time, now, last, interval=0.05):
    """Put the current time on `at_time` if the throttle allows.

    Returns the timestamp to remember, or the one passed in when it held --
    so the caller never has to know the rule, only to keep the answer.
    """
    if not mapping.should_evaluate(now, last, interval):
        return last
    cmds.currentTime(float(at_time), edit=True)
    return now


def settle(at_time):
    """The one evaluation the throttle may not skip: the mouse came up."""
    cmds.currentTime(float(at_time), edit=True)
