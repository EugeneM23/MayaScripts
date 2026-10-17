"""Live proof of the Maya theme (2026-10-17) - run in a GUI Maya.

    exec(compile(open(r"C:/!!!Work/MayaScripts/docs/superpowers/plans/verify_maya_theme.py",
                      encoding="utf-8").read(), "verify_maya_theme.py", "exec"),
         {"__name__": "__main__"})

Switches the theme on through the hub's own callback, measures, switches it off
and requires Maya exactly as it was: every display colour, the gradient flag, the
application's palette and stylesheet. Also requires that no Maya control changed
its size (the sheet sets colours, borders and radii only) and writes two
viewport playblasts (on / off) beside this file. Leaves the theme as it found it.
"""

import json
import os
import sys

REPO = r"C:/!!!Work/MayaScripts/SkeldarAnim"
HERE = os.path.dirname(os.path.abspath(globals().get("__file__") or os.path.join(
    REPO, "..", "docs", "superpowers", "plans", "x")))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
for name in list(sys.modules):
    if name.split(".")[0] in ("maya_mayatheme", "maya_hubstyle"):
        del sys.modules[name]

import maya.cmds as cmds                                      # noqa: E402
import maya_hubstyle as hubstyle                              # noqa: E402
import maya_mayatheme as theme                                # noqa: E402

try:
    from PySide6 import QtGui, QtWidgets
except ImportError:                                           # Maya < 2025
    from PySide2 import QtGui, QtWidgets

RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def colours():
    out = {}
    for name in theme.RGB:
        try:
            out[name] = [round(v, 4) for v in
                         cmds.displayRGBColor(name, query=True, alpha=True)]
        except Exception:                                     # noqa: BLE001
            out[name] = None
    return out


def sizes():
    """Size hints of a window of Maya's own controls."""
    if cmds.window("skeldarThemeProbe", exists=True):
        cmds.deleteUI("skeldarThemeProbe")
    cmds.window("skeldarThemeProbe")
    cmds.columnLayout()
    made = [cmds.floatField("thProbeFloat"), cmds.button("thProbeButton", label="Button"),
            cmds.textField("thProbeText"), cmds.optionMenu("thProbeMenu"),
            cmds.textScrollList("thProbeList", append=["a", "b"]),
            cmds.checkBox("thProbeCheck", label="Check")]
    cmds.menuItem(label="One", parent="thProbeMenu")
    cmds.showWindow("skeldarThemeProbe")
    QtWidgets.QApplication.processEvents()
    import maya.OpenMayaUI as omui
    try:
        import shiboken6 as shiboken
    except ImportError:
        import shiboken2 as shiboken
    out = {}
    for name in made:
        ptr = omui.MQtUtil.findControl(name)
        widget = shiboken.wrapInstance(int(ptr), QtWidgets.QWidget)
        hint = widget.sizeHint()
        out[name.split("|")[-1]] = (hint.width(), hint.height())
    cmds.deleteUI("skeldarThemeProbe")
    return out


def blast(tag):
    path = os.path.join(HERE, "maya_theme_viewport_%s" % tag)
    try:
        cmds.playblast(frame=[cmds.currentTime(q=True)], format="image",
                       compression="png", filename=path, viewer=False,
                       showOrnaments=True, percent=50, forceOverwrite=True,
                       offScreen=False)
    except Exception as error:                                # noqa: BLE001
        print("playblast failed: %s" % error)


app = QtWidgets.QApplication.instance()
was_on = theme.enabled()
if was_on:
    theme.set_enabled(False)

before = {"rgb": colours(),
          "gradient": cmds.displayPref(query=True, displayGradient=True),
          "sheet": app.styleSheet(),
          "window": app.palette().color(QtGui.QPalette.Window).name()}
size_before = sizes()
blast("off")

try:
    import maya_hub
    message = maya_hub.set_mayatheme(True)
except Exception:                                             # noqa: BLE001
    message = theme.set_enabled(True)
gate("on: said so", "ON" in message, message)
gate("on: remembered", theme.enabled())
now = colours()
wrong = [n for n, rgb in theme.RGB.items()
         if now[n] is not None and [round(v, 3) for v in now[n][:3]]
         != [round(v, 3) for v in rgb]]
gate("on: every display colour written", not wrong, ", ".join(wrong))
gate("on: viewport gradient", cmds.displayPref(query=True, displayGradient=True))
gate("on: palette is the hub's",
     app.palette().color(QtGui.QPalette.Window).name() == hubstyle.TOKENS["panel"],
     app.palette().color(QtGui.QPalette.Window).name())
gate("on: sheet appended once", app.styleSheet().count(theme.START) == 1)
size_on = sizes()
moved = dict((k, (size_before[k], size_on[k])) for k in size_before
             if size_before[k] != size_on[k])
gate("on: no Maya control changed size", not moved, json.dumps(moved))
blast("on")

#  Maya's start: ensure() again -> one copy
theme.ensure()
gate("ensure: still one copy", app.styleSheet().count(theme.START) == 1)

try:
    message = maya_hub.set_mayatheme(False)
except Exception:                                             # noqa: BLE001
    message = theme.set_enabled(False)
gate("off: said so", "OFF" in message, message)
after = {"rgb": colours(),
         "gradient": cmds.displayPref(query=True, displayGradient=True),
         "sheet": app.styleSheet(),
         "window": app.palette().color(QtGui.QPalette.Window).name()}
for key in ("rgb", "gradient", "sheet", "window"):
    gate("off: %s as before" % key, after[key] == before[key])
gate("off: memory removed", not cmds.optionVar(exists=theme.SAVED_VAR))

if was_on:
    theme.set_enabled(True)
failed = [r for r in RESULTS if not r[1]]
print("verify_maya_theme: %d of %d gates failed" % (len(failed), len(RESULTS)))
