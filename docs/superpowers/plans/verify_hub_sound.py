"""Live proof of the hub's hover sound.

Sent over the command port to a GUI Maya with the plugin installed and the
hub open (skinned). It touches no scene node: Qt Enter events go to the
hub's REAL widgets (Maya's QPushButton, segment, checkbox, dropdown; our
card header and strip; a label, a field and a card frame that must stay
silent), maya_hubsound.play is wrapped to count, the QSoundEffect pool is
read, the menu switch is pressed both ways and left as found. Whoever sits
at that Maya hears the ticks.

Never holds a widget across an event pump: every widget is found again by
name in the hub standing right then. The first version kept the wrappers
from one findChildren for two seconds of processEvents, and the animator's
Maya died in a Qt call on a deleted widget (2026-10-01 11:55, the hub
rebuilt under it by another session's install - CLAUDE.md trap 148).

Spec: docs/superpowers/specs/2026-10-01-hub-hover-sound-design.md
"""

import os
import time

import maya.cmds as cmds
import shiboken6
from PySide6 import QtCore, QtGui, QtWidgets

import maya_hub
import maya_hubsound

RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("{0} {1}{2}".format("PASS" if ok else "FAIL", name,
                              (" - " + detail) if detail else ""))


def pump(seconds):
    app = QtWidgets.QApplication.instance()
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.003)


def skin():
    s = maya_hub._SKIN
    if s is None or not s.alive():
        raise RuntimeError("no live skin")
    return s


def find(spec):
    """The live widget (meta class, object name, index among the matches) in
    the hub standing now, or None."""
    meta, name, index = spec
    matches = [w for w in skin().root.findChildren(QtWidgets.QWidget, name)
               if w.metaObject().className() == meta]
    if index >= len(matches) or not shiboken6.isValid(matches[index]):
        return None
    return matches[index]


def enter(spec):
    """Send `spec`'s widget an Enter; answer the plays it caused, which
    happen inside the send. Plays that come later, while events are pumped,
    are a REAL cursor over the hub (measured in the first disposable run:
    the hub's window under the animator's mouse, Enters on two card headers
    300 ms apart) and are not this send's."""
    widget = find(spec)
    if widget is None:
        raise RuntimeError("gone: {0}".format(spec))
    before = len(calls)
    QtWidgets.QApplication.sendEvent(
        widget, QtGui.QEnterEvent(QtCore.QPointF(2, 2), QtCore.QPointF(2, 2),
                                  QtCore.QPointF(2, 2)))
    return calls[before:]


def spec_of(meta, ok=lambda w: True):
    """The first visible, enabled widget of `meta` under the root, as a spec
    to find again later."""
    seen = {}
    for w in skin().root.findChildren(QtWidgets.QWidget):
        if w.metaObject().className() != meta:
            continue
        name = w.objectName()
        index = seen.get(name, 0)
        seen[name] = index + 1
        if w.isVisible() and w.isEnabled() and ok(w):
            return (meta, name, index)
    return None


installed = os.path.join(cmds.internalVar(userAppDir=True), "scripts",
                         "SkeldarAnim").replace("\\", "/")
gate("1 the hub is skinned by the installed copy",
     maya_hub.is_skinned() and maya_hubsound.__file__.replace("\\", "/")
     .startswith(installed), maya_hubsound.__file__)
was_on = maya_hubsound.enabled()
action = skin().sounds_action
gate("2 the menu row shows the switch",
     action.isCheckable() and action.isChecked() == was_on
     and action.text() == "Interface sounds", "on" if was_on else "off")

picks = {
    "a Maya button": spec_of("QPushButton", lambda w: bool(w.text())),
    "a segment": spec_of("QmayaIconTextRadioButton"),
    "a checkbox": spec_of("QmayaCheckBox"),
    "a dropdown": spec_of("QmayaOptionMenu"),
    "a card header": spec_of("CardHead"),
    "a strip jump": spec_of("QToolButton", lambda w: w.objectName()
                            .startswith("skeldarHubJump_")),
}
silent = {
    "a label": spec_of("QmayaLabel"),
    "a field": spec_of("QmayaField"),
    "a card frame": spec_of("QFrame", lambda w: w.objectName()
                            .startswith("skeldarHubCard_")),
}
everything = list(picks.items()) + list(silent.items())
gate("3 every kind of control found in the live hub",
     all(spec for _, spec in everything),
     ", ".join("{0}={1}".format(k, spec[1] if spec else None)
               for k, spec in everything))

calls = []
real_play = maya_hubsound.play


def counting(name, now=None):
    result = real_play(name, now)
    calls.append((name, result))
    return result


def effects():
    held = maya_hubsound._state()["players"].get("hover")
    return list(getattr(held[1], "effects", [])) if held else []


def rearm():
    del calls[:]
    maya_hubsound._state()["last"] = float("-inf")


maya_hubsound.play = counting
try:
    if not was_on:
        maya_hubsound.set_enabled(True)
    maya_hubsound.preload("hover")
    pump(0.6)
    pool = effects()
    gate("4 the hover sound is a QSoundEffect pool, loaded",
         len(pool) == maya_hubsound.POOL
         and all(e.status().name == "Ready" for e in pool),
         ", ".join(e.status().name for e in pool) + " | "
         + (pool[0].source().toLocalFile() if pool else ""))

    for label, spec in picks.items():
        if spec is None:
            continue
        rearm()
        t0 = time.time()
        mine = enter(spec)
        started = None
        while time.time() - t0 < 0.3:
            QtWidgets.QApplication.instance().processEvents()
            if started is None and any(e.isPlaying() for e in effects()):
                started = time.time() - t0
            time.sleep(0.002)
        gate("5 entering {0} plays it".format(label),
             mine == [("hover", True)] and started is not None,
             "{0} {1}, playing after {2}{3}".format(
                 spec[0], mine, "%.0f ms" % (started * 1000)
                 if started is not None else "never",
                 "; the real cursor: {0}".format(calls[1:]) if calls[1:]
                 else ""))
        pump(0.12)

    for label, spec in silent.items():
        if spec is None:
            continue
        rearm()
        mine = enter(spec)
        gate("6 entering {0} is silent".format(label), mine == [], spec[0])
        pump(0.05)

    #  a sweep: two buttons 10 ms apart, then one past the gap -- no pump in
    #  between, so no real cursor gets a word in
    rearm()
    sweep = enter(picks["a Maya button"])
    time.sleep(0.010)
    sweep += enter(picks["a segment"])
    time.sleep(0.050)
    sweep += enter(picks["a Maya button"])
    gate("7 a sweep is throttled, the next one plays",
         [r for _, r in sweep] == [True, False, True], str(sweep))
    pump(0.15)

    #  the switch, through the menu row
    rearm()
    skin().sounds_action.trigger()                       # -> off
    off_var = cmds.optionVar(query=maya_hubsound.OPTIONVAR)
    rearm()
    mine = enter(picks["a Maya button"])
    gate("8 Interface sounds off: remembered and silent",
         not skin().sounds_action.isChecked() and off_var == 0
         and not maya_hubsound.enabled() and mine == [("hover", False)],
         "optionVar {0}, {1}".format(off_var, mine))
    rearm()
    skin().sounds_action.trigger()                       # -> on, plays once
    mine = list(calls)
    gate("9 back on: remembered and heard once",
         skin().sounds_action.isChecked()
         and cmds.optionVar(query=maya_hubsound.OPTIONVAR) == 1
         and mine == [("hover", True)], str(mine))
    pump(0.15)
finally:
    maya_hubsound.play = real_play
    if not was_on:
        maya_hub.set_sounds(False)

gate("10 left as found", maya_hubsound.enabled() == was_on
     and skin().sounds_action.isChecked() == was_on
     and maya_hubsound.play is real_play)
failed = [n for n, ok in RESULTS if not ok]
print("{0} of {1} gates passed".format(len(RESULTS) - len(failed),
                                       len(RESULTS)))
