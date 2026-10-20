"""Scene Time Warp, switched off for the length of a bake (2026-10-20).

The animator: «наши анимационные слои некорректно работают с scene time warp».

Maya's Scene Time Warp (Key > Scene Time Warp) is an animCurveTT `timewarp` connected into
`time1.timewarpIn_Raw`, on while `time1.enableTimewarp` is: at scene frame f every time curve
is evaluated at the warped time w(f) (`time1.outTime`), while keys still live in curve time -
Maya's own `setKeyframe` at frame f keys curve time f, and `getAttr(plug, time=t)` and
`keyframe -eval` read curve time t (measured 2026-10-20, Maya 2027).

So whatever READS the scene by moving the time and WRITES keys at the frames it walked mixes
the two clocks: it reads w(f) and keys f. Measured on a cube parent-constrained to a keyed
locator under a non-linear warp: Tools > Layer moved its animation up to 83 deg, and Maya's
own `bakeResults -simulation` 20.8 cm (without `-simulation` Maya reads curve time and is
right). Every bake, time walk and layer write of the plugin did the same.

`unwarped()` switches the warp off for the length of such a read - through the API, so it is
no step on the undo queue (an undo of the press must not switch the warp) - evaluates the
current frame, and switches it back on and evaluates again after. With the warp off the scene
frame IS curve time, and a bake keys exactly what it read: a layer baked under a warp plays
under it as the take played before. Re-entrant (a walk inside a press inside a bake switches
once). Nothing at all happens without a warp in the scene.

Every evaluation re-evaluates the time curves and throws away an unkeyed tweak (trap 206); a
time walk reads the tweaks before it switches (`maya_poselib.timewalk.Walk`).
"""

import sys

_STATE = sys.__dict__.setdefault("_skeldar_timewarp", {"depth": 0, "off": False})

ENABLE = "time1.enableTimewarp"
INPUT = "time1.timewarpIn_Raw"


def active():
    """True when a Scene Time Warp warps the scene now: switched on, and something feeds it."""
    try:
        import maya.cmds as cmds
        if not cmds.objExists(ENABLE) or not cmds.getAttr(ENABLE):
            return False
        return bool(cmds.listConnections(INPUT, source=True, destination=False))
    except Exception:                                        # noqa: BLE001 - no Maya, a fake
        return False


def _plug():
    import maya.api.OpenMaya as om
    found = om.MSelectionList()
    found.add(ENABLE)
    return found.getPlug(0)


def _evaluate():
    """The current frame evaluated again (a same-frame set re-evaluates every time curve)."""
    import maya.api.OpenMayaAnim as oma
    oma.MAnimControl.setCurrentTime(oma.MAnimControl.currentTime())


def _switch(on):
    _plug().setBool(bool(on))
    _evaluate()


class unwarped(object):
    """with unwarped(): ... - the scene in curve time for the length of the block."""

    def __enter__(self):
        if _STATE["depth"] == 0 and active():
            _switch(False)
            _STATE["off"] = True
        _STATE["depth"] += 1
        return self

    def __exit__(self, kind, error, trace):
        _STATE["depth"] = max(0, _STATE["depth"] - 1)
        if _STATE["depth"] == 0 and _STATE["off"]:
            _STATE["off"] = False
            _switch(True)
        return False


def bake_results(*args, **kwargs):
    """`cmds.bakeResults` read in curve time (its `-simulation` walks the scene's frames)."""
    import maya.cmds as cmds
    with unwarped():
        return cmds.bakeResults(*args, **kwargs)


def call(fn, *args, **kwargs):
    """`fn(*args, **kwargs)` with the warp off."""
    with unwarped():
        return fn(*args, **kwargs)


def wrapped(fn):
    """A press decorated to run with the warp off."""
    import functools

    @functools.wraps(fn)
    def run(*args, **kwargs):
        with unwarped():
            return fn(*args, **kwargs)
    return run
