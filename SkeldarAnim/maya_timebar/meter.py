"""The scrub meter (2026-10-16, the animator: «давай теперь проверим быстродействие
нашего интерфейса ... такое чувство что фпс программы проседает когда перетаскиваешь
ползунок»): for a few seconds every frame change Maya makes is clocked through its
own time-change callback - whichever slider drives it, ours or Maya's - and, when the
Time Bar drives it, its own work and Maya's `currentTime` per step. The report goes
to the Script Editor and the viewport.

Started from the Time Bar's right-click menu or the hotkey row `timebar.measure`.
"""

import time
import traceback

from . import look, _state

SECONDS = 10.0


def clock():
    return time.perf_counter() * 1000.0


def running():
    return _state().get("meter") is not None


def say(message, stay_ms=3000):
    print(message)
    try:
        import maya.cmds as cmds
        if not cmds.about(batch=True):
            cmds.inViewMessage(assistMessage=message, position="topCenter", fade=True,
                               fadeStayTime=int(stay_ms))
    except Exception:                                        # noqa: BLE001
        pass
    return message


def start(seconds=SECONDS):
    """Clock the next `seconds` of frame changes; the report comes by itself."""
    if running():
        return say("Scrub meter: already measuring - drag the playhead")
    import maya.api.OpenMaya as om
    meter = {"stamps": [], "ours": [], "mayas": [], "seconds": float(seconds)}

    def on_time(*_args):
        meter["stamps"].append(clock())
    meter["callback"] = om.MDGMessage.addTimeChangeCallback(on_time)
    _state()["meter"] = meter
    try:
        import maya_hubqt
        maya_hubqt.qt().QtCore.QTimer.singleShot(int(seconds * 1000), stop)
    except Exception:                                        # noqa: BLE001 - no Qt: the caller stops it
        pass
    return say("Scrub meter: drag the playhead now, for %g s - with the Time Bar or Maya's own slider"
               % seconds)


def record(ours_ms, maya_ms):
    """One step the Time Bar drove: its own work and Maya's frame change, ms."""
    meter = _state().get("meter")
    if meter is not None:
        meter["ours"].append(ours_ms)
        meter["mayas"].append(maya_ms)


def stop():
    """The measurement over: the callback off, the report said. Returns its text."""
    meter = _state().pop("meter", None)
    if meter is None:
        return ""
    try:
        import maya.api.OpenMaya as om
        om.MMessage.removeCallback(meter["callback"])
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
    _out, text = look.meter_report(meter["stamps"], meter["ours"], meter["mayas"], meter["seconds"])
    return say(text, stay_ms=8000)
