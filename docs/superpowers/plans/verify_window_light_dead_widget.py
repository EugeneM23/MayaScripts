"""A window light ring survives Maya deleting the window it rings.

2026-11-03. The animator: «Посмотри в логи мая вылетает при использовании
connection bake IK». 28 dumps since 2026-10-24 share one signature: a Qt
timer's slot, a Python frame, then an access violation inside shiboken - and
measured in a GUI Maya the same day, a wrapper of a widget MAYA deleted answers
`shiboken.isValid` TRUE and crashes on the FIRST method call (`objectName`,
`isVisible`, `mask`, `mapToGlobal` - the four this watch makes; `parentWidget`,
`children` and `removeEventFilter` survive).

So the watch may keep no wrapper of a foreign widget. It keeps the window's C++
pointer and name and looks the widget up again every time (`Light._live`).
This gates that, against real Maya controls Maya really deletes: the control
path (a workspaceControl, found by name) and the window path (a top-level).

Run it in a GUI Maya - it needs real Maya UI:

    maya -command "python(\"exec(open(r'<this file>').read())\")"

or over the command port. It writes its report to VERIFY_OUT (or the scratch
default) and prints it; a crash leaves the report up to the gate it reached,
which is the whole point - Maya's own handler writes a dump and exits 0.
"""
import json
import os
import sys

REPO = r"C:/!!!Work/MayaScripts/SkeldarAnim"
OUT = os.environ.get("VERIFY_OUT", os.path.join(
    os.environ.get("TEMP", "."), "verify_window_light_dead_widget.json"))

GATES = []


def gate(ok, name, measured=""):
    #  `measured` may be a tuple: the format argument is wrapped, or a 2-tuple
    #  reads as two arguments and raises (trap 323's family).
    shown = str(measured)
    GATES.append({"gate": len(GATES) + 1, "ok": bool(ok), "name": name,
                  "measured": shown})
    _flush()
    print("%s %2d %s%s" % ("ok  " if ok else "FAIL", len(GATES), name,
                           ("  [%s]" % (shown,)) if shown else ""))


def note(text):
    GATES.append({"note": str(text)})
    _flush()
    print("    %s" % text)


def _flush():
    with open(OUT, "w") as fh:
        json.dump(GATES, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())


def run():
    for path in (REPO,):
        if path not in sys.path:
            sys.path.insert(0, path)
    for name in [m for m in list(sys.modules)
                 if m.startswith(("maya_windowlight", "maya_hubqt",
                                  "maya_hubmotion"))]:
        del sys.modules[name]

    import maya.cmds as cmds
    import maya.utils
    import maya.OpenMayaUI as omui
    import shiboken6
    from PySide6 import QtCore, QtWidgets

    import maya_windowlight as wl

    def settle():
        for _ in range(3):
            QtWidgets.QApplication.processEvents()
            maya.utils.processIdleEvents()

    def wrap(control):
        ptr = omui.MQtUtil.findControl(control)
        return None if ptr is None else shiboken6.wrapInstance(
            int(ptr), QtWidgets.QWidget)

    note("Maya %s, Qt %s" % (cmds.about(version=True), QtCore.qVersion()))

    #  the watch, with the mouse's widget handed in (the unit tests' seam)
    under = {}
    wl.widget_at = lambda q, pos: under.get("w")
    light = wl.Light()
    light.start()
    light.tick_timer.stop()
    gate(light.alive(), "the watch is up")

    def settle_fades():
        for _ in range(200):
            light.tick_at = (light.tick_at or 0) - 0.05
            light.tick()
            if not light.tick_timer.isActive():
                break

    def why_not(leaf):
        """What the watch saw, when it picked nothing - so a failed run says
        why instead of leaving us guessing."""
        nodes, _widgets = light.chain(leaf)
        note("the chain the watch walked: %s" % [
            {k: n[k] for k in ("name", "top", "control", "w", "h")}
            for n in nodes])

    def make_control(name):
        ctl = cmds.workspaceControl(name, label=name, retain=False,
                                    floating=True,
                                    initialWidth=320, initialHeight=240)
        cmds.columnLayout(parent=ctl)
        btn = cmds.button(label="x", width=200, height=80)
        settle()
        try:
            cmds.workspaceControl(ctl, edit=True, resizeWidth=320,
                                  resizeHeight=240)
        except Exception:                                    # noqa: BLE001
            pass
        settle()
        return ctl, btn

    # ---- a workspaceControl: found again by name --------------------------
    ctl, btn = make_control("verifyDeadWidget")
    widget = wrap(ctl)
    leaf = wrap(btn)
    gate(widget is not None and leaf is not None,
         "a real workspaceControl is up and wrapped")
    note("the control's widget is %r, %sx%s, visible=%s" % (
        widget.objectName() if widget is not None else None,
        widget.width() if widget is not None else 0,
        widget.height() if widget is not None else 0,
        widget.isVisible() if widget is not None else None))

    under["w"] = leaf
    light.poll(force=True)
    settle_fades()
    if light.target is None:
        why_not(leaf)
    key = wl._ptr(light.q, widget)
    gate(light.target is not None and light.target[0] == key
         and light.target[1] == "ring",
         "the control is ringed", light.target[:2] if light.target else None)
    gate(light.target is not None
         and all(not isinstance(held, QtWidgets.QWidget)
                 for held in light.target),
         "the watch kept no widget of it",
         repr(light.target[2]) if light.target else None)
    gate(key in light.overlays and light.overlays[key].level == 1.0,
         "its ring is lit")
    gate(light.target is not None and light._live(key, light.target[2]) is not None,
         "it is looked up again while it stands")

    #  Maya deletes it - what the animator's layer / card / panel rebuilds do
    cmds.deleteUI(ctl, control=True)
    settle()
    gate(bool(shiboken6.isValid(widget)),
         "the wrapper of the deleted control still answers isValid TRUE "
         "(the trap)", shiboken6.isValid(widget))
    #  Measured 2026-11-03: `deleteUI` takes the CONTROL away at once and
    #  Maya lets its Qt widget linger (it stops being visible, and Qt frees it
    #  later), so the lookup may well still answer here - what matters is that
    #  the answer is a LIVE widget and never the wrapper we would have kept.
    lingering = light._live(key, "verifyDeadWidget")
    note("after deleteUI: the control exists=%s, the lookup answers %s, "
         "visible=%s" % (
             cmds.workspaceControl("verifyDeadWidget", exists=True),
             "a live widget" if lingering is not None else "None",
             lingering.isVisible() if lingering is not None else None))
    gate(lingering is None or not lingering.isVisible(),
         "the deleted control is gone or no longer visible - either way the "
         "ring must drop")

    note("about to poll, follow and tick over the deleted control: on the "
         "build before this, isVisible() on the kept wrapper crashed Maya here")
    under["w"] = None            # as the real widget_at does: nothing kept
    light._follow()
    gate(light.target is None, "the follow dropped the target, Maya standing",
         light.target)
    light.poll(force=True)
    settle_fades()
    gate(light.overlays == {}, "the ring is gone", light.overlays)

    # ---- a top-level window: found again in the live list -----------------
    win = cmds.window(title="verifyDeadWindow", widthHeight=(340, 260))
    cmds.columnLayout(parent=win)
    btn2 = cmds.button(label="y", width=220, height=90)
    cmds.showWindow(win)
    settle()
    leaf2 = wrap(btn2)
    top = leaf2.window() if leaf2 is not None else None
    under["w"] = leaf2
    light.poll(force=True)
    settle_fades()
    key2 = wl._ptr(light.q, top) if top is not None else 0
    shown2 = bool(top is not None and top.isVisible())
    if not shown2:
        #  This run's Maya is minimized, so a floating window of Maya's is not
        #  visible - and the watch rings no window that is not visible, which
        #  is why the ring is not expected here. The workspaceControl above
        #  carries the ring path; this one only has to not crash.
        note("the floating window reads visible=%s (a minimized Maya), so the "
             "ring is not expected - pick answers %r and the lookup %s"
             % (shown2, wl.pick(light.chain(leaf2)[0], light.maya_on),
                "a live widget" if light._live(key2, "window1") is not None
                else "None"))
    else:
        gate(light.target is not None and light.target[0] == key2,
             "a floating Maya window is ringed too",
             light.target[:2] if light.target else None)
    held2 = light.target[2] if light.target else "window1"

    cmds.deleteUI(win, window=True)
    under["w"] = None            # the real widget_at keeps nothing either
    settle()
    gone2 = light._live(key2, held2)
    gate(gone2 is None or not gone2.isVisible(),
         "the deleted window is gone or no longer visible",
         "None" if gone2 is None else "visible=%s" % gone2.isVisible())
    light._follow()
    light.poll(force=True)
    settle_fades()
    gate(light.target is None and light.overlays == {},
         "its ring went with it, Maya standing")

    # ---- the watch still works afterwards --------------------------------
    ctl3 = cmds.workspaceControl("verifyDeadWidget3", label="v3",
                                 retain=False, floating=True)
    cmds.columnLayout(parent=ctl3)
    btn3 = cmds.button(label="z", width=200, height=80)
    settle()
    try:
        cmds.workspaceControl(ctl3, edit=True, resizeWidth=320,
                              resizeHeight=240)
    except Exception:                                        # noqa: BLE001
        pass
    settle()
    under["w"] = wrap(btn3)
    light.poll(force=True)
    settle_fades()
    key3 = wl._ptr(light.q, wrap(ctl3))
    gate(key3 in light.overlays and light.overlays[key3].level == 1.0,
         "a new window is ringed after all that")
    cmds.deleteUI(ctl3, control=True)
    under["w"] = None
    light.stop()
    settle()
    gate(light.overlays == {} and light.watched == [],
         "the watch stopped clean")

    failed = [g for g in GATES if "ok" in g and not g["ok"]]
    print("\n%d of %d gates failed" % (len(failed),
                                       len([g for g in GATES if "ok" in g])))
    return len(failed)


def main():
    import traceback
    code = 1
    try:
        code = run()
    except Exception:                                        # noqa: BLE001
        note("the verify raised:\n" + traceback.format_exc())
        print(traceback.format_exc())
    try:
        import maya.cmds as cmds
        if os.environ.get("VERIFY_QUIT"):
            cmds.quit(force=True, abort=False)
    except Exception:                                        # noqa: BLE001
        pass
    return code


if __name__ in ("__main__", "__probe__"):
    main()
