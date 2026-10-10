"""verify_hub_popups - the hub's section popups, live, through the command port.

2026-10-09. Spec: docs/superpowers/specs/2026-10-09-hub-section-popups-design.md.

Send it to Maya's command port (sourceType python), one line:

    exec(open(r'<this file>', encoding='utf-8').read())

It writes its gates to OUT (JSON) and is idempotent (a marker file: a second
send does nothing - trap 5 of CLAUDE.md). It runs everything inside run(), so
the names it uses are its own locals (trap 17). It leaves the scene untouched
(it builds no rig and presses no button that changes the scene: the Colour
palette press refuses with "select something" in an empty scene), leaves the
popups that were open open, and puts the Maya window back as it found it.

Phases (each a separate send when the window must move between them):
  A  the cards' popout buttons; every card section opened and closed
  B  one popup: its copy's controls, its press, the hub unchanged, the roll,
     the drag clamp, the fit (no wasted space)
  C  the close kills the copy (scriptJobs, controls, window), the card lit off
  D  the remembered set: destroy (an install), restore, the roll remembered
  E  follow: the Maya window moved, the popup moved with its viewport (its own
     send: the timer runs between sends)
"""

import json
import os
import sys
import traceback

OUT = ("C:/Users/MYPC~1/AppData/Local/Temp/claude/C-----Work-MayaScripts/"
       "6d1b9644-60a6-4c79-b206-645973975641/scratchpad/verify_hub_popups.out")
PHASES = ("A", "B", "C", "D")    # "E" is sent on its own, after a window move
SECTIONS = ("characters", "weapons", "connections", "shared", "stash",
            "retarget", "graphoverlay", "com", "poses", "studio", "colour",
            "update")
STATUS = {"colour": "skeldarColourStatus"}   # a section's status control name


def run(phases):
    import maya.cmds as cmds
    import maya_hub
    import maya_hubcopy
    import maya_hubpop
    import maya_hubpop_rules as rules
    from PySide6 import QtCore, QtGui, QtWidgets

    res = {"phases": phases, "gates": {}}
    gates = res["gates"]

    def gate(name, ok, detail=None):
        gates[name] = {"ok": bool(ok), "detail": detail}

    def mouse(widget, kind, local, global_pt, buttons):
        event = QtGui.QMouseEvent(
            kind, QtCore.QPointF(local[0], local[1]),
            QtCore.QPointF(global_pt[0], global_pt[1]),
            QtCore.Qt.LeftButton, buttons, QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(widget, event)

    def text_of(name):
        if not name or not cmds.control(name, exists=True):
            return None
        return cmds.text(name, query=True, label=True)

    def hub_status():
        return text_of(STATUS["colour"])

    maya_hub.show("colour")
    skin = maya_hub._SKIN
    gate("hub_skin", skin is not None and skin.alive(),
         sorted(skin.cards.keys()) if skin is not None else None)
    was_open = list(maya_hubpop.open_keys())
    res["was_open"] = was_open

    if "A" in phases:
        buttons = {}
        for key in SECTIONS:
            card = skin.cards.get(key) if skin is not None else None
            buttons[key] = bool(card is not None and card.popout is not None)
        gate("A_popout_buttons", all(buttons.values()), buttons)
        opened = {}
        for key in SECTIONS:
            if key in was_open:
                opened[key] = "left open by the animator - not touched"
                continue
            try:
                popup = maya_hubpop.open_popup(key)
                if popup is None:
                    opened[key] = "no viewport"
                    continue
                errors = [w.text() for w in popup.content.findChildren(
                    QtWidgets.QLabel) if "could not be built" in (w.text() or "")]
                opened[key] = {"names": len(popup.scope.names),
                               "errors": errors,
                               "prefixed": all(
                                   v.startswith(popup.scope.prefix) or
                                   popup.scope.prefix in v
                                   for v in popup.scope.names.values())}
                maya_hubpop.close_popup(key)
                opened[key]["closed"] = not maya_hubpop.is_open(key)
            except Exception:
                opened[key] = {"exception": traceback.format_exc()[-600:]}
                try:
                    maya_hubpop.close_popup(key)
                except Exception:
                    pass
        res["A_sections"] = opened
        bad = [k for k, v in opened.items()
               if isinstance(v, dict) and (v.get("errors") or "exception" in v
                                           or not v.get("closed", True))]
        gate("A_every_section_builds_and_closes", not bad, bad)
        gate("A_no_stray_scopes",
             all(s.section in was_open for s in maya_hubcopy.instances("colour")
                 ) and len([s for s in maya_hubcopy.live()
                            if s.section not in was_open]) == 0,
             [s.tag for s in maya_hubcopy.live()])

    if "B" in phases:
        popup = maya_hubpop.open_popup("colour")
        gate("B_open", popup is not None and popup.alive())
        if popup is not None:
            name = STATUS["colour"]
            copy_name = popup.scope.names.get(name)
            before_hub = hub_status()
            before_copy = text_of(copy_name)
            palette = [b for b in popup.content.findChildren(QtWidgets.QPushButton)
                       if b.isEnabled() and b.isVisible()]
            if palette:
                palette[0].click()
            after_copy = text_of(copy_name)
            after_hub = hub_status()
            gate("B_copy_press_changes_the_copy", after_copy != before_copy,
                 [before_copy, after_copy])
            gate("B_hub_line_unchanged", after_hub == before_hub,
                 [before_hub, after_hub])
            # fit: the window is exactly the title plus the section (no waste)
            hint = popup.content.sizeHint().height()
            want = popup._chrome() + hint
            gate("B_fits_its_content", abs(popup.root.height() - max(
                want, rules.MIN_HEIGHT)) <= 2,
                 [popup.root.height(), want])
            # roll up and back
            popup.toggle_roll()
            gate("B_roll_up", popup.collapsed and popup.scroll.isHidden()
                 and popup.root.height() == popup._chrome(),
                 [popup.root.height(), popup._chrome()])
            popup.toggle_roll()
            gate("B_unroll", (not popup.collapsed) and abs(
                popup.root.height() - max(want, rules.MIN_HEIGHT)) <= 2,
                 popup.root.height())
            # a click on the name rolls it; a drag of the name does not
            title = popup.title
            tg = title.mapToGlobal(QtCore.QPoint(0, 0))
            start = (tg.x() + 60, tg.y() + 8)
            mouse(title, QtCore.QEvent.MouseButtonPress, (60, 8), start,
                  QtCore.Qt.LeftButton)
            mouse(title, QtCore.QEvent.MouseButtonRelease, (60, 8), start,
                  QtCore.Qt.NoButton)
            gate("B_click_on_name_rolls", popup.collapsed)
            mouse(title, QtCore.QEvent.MouseButtonPress, (60, 8), start,
                  QtCore.Qt.LeftButton)
            far = (start[0] + 200, start[1] + 40)
            mouse(title, QtCore.QEvent.MouseMove, (260, 48), far,
                  QtCore.Qt.LeftButton)
            mouse(title, QtCore.QEvent.MouseButtonRelease, (260, 48), far,
                  QtCore.Qt.NoButton)
            gate("B_drag_of_name_does_not_roll", popup.collapsed)
            popup.set_collapsed(False)
            # the drag clamp, both corners, on the real mouse events
            rect = maya_hubpop._rect_of(popup.panel)
            pos = popup.root.pos()
            popup._grab((pos.x() + 5, pos.y() + 5))
            popup._drag((rect[0] - 3000, rect[1] + rect[3] + 900))
            pos = popup.root.pos()
            gate("B_drag_clamped_left_bottom",
                 pos.x() == rect[0] and pos.y() + popup.root.height()
                 == rect[1] + rect[3], [pos.x(), pos.y()])
            popup._drop()
            popup._grab((pos.x() + 5, pos.y() + 5))
            popup._drag((rect[0] + rect[2] + 2000, rect[1] - 900))
            pos = popup.root.pos()
            gate("B_drag_clamped_right_top",
                 pos.x() + popup.root.width() == rect[0] + rect[2]
                 and pos.y() == rect[1], [pos.x(), pos.y()])
            popup._drop()
            stored = cmds.optionVar(query="skeldarHubPopupPos_colour")
            gate("B_offset_remembered", stored == rules.encode_offset(
                popup.offset), stored)
            res["B_popup"] = {"geometry": [popup.root.x(), popup.root.y(),
                                           popup.root.width(),
                                           popup.root.height()],
                              "offset": popup.offset,
                              "scope": popup.scope.tag,
                              "names": sorted(popup.scope.names)}

    if "C" in phases:
        popup = maya_hubpop._state()["popups"].get("colour")
        if popup is None:
            popup = maya_hubpop.open_popup("colour")
        scope = popup.scope
        jobs = list(scope.jobs)
        names = list(scope.names.values())
        root_name = popup.root.objectName()
        maya_hubpop.close_popup("colour")
        gate("C_closed", not maya_hubpop.is_open("colour"))
        gate("C_scope_closed", not scope.alive and scope not in maya_hubcopy.live())
        gate("C_jobs_killed", all(not cmds.scriptJob(exists=j) for j in jobs),
             jobs)
        gone = [n for n in names if cmds.control(n, exists=True)]
        gate("C_controls_gone", not gone, gone)
        windows = [w.objectName() for w in QtWidgets.QApplication.topLevelWidgets()
                   if w.objectName() == root_name]
        gate("C_window_gone", not windows, windows)
        card = skin.cards.get("colour") if skin is not None else None
        gate("C_card_lit_off", card is not None and
             not bool(card.popout.property("skPopped")))

    if "D" in phases:
        popup = maya_hubpop.open_popup("colour")
        popup.set_collapsed(True)
        offset = popup.offset
        maya_hubpop.destroy_all(forget=False)
        remembered = cmds.optionVar(query="skeldarHubPopups")
        gate("D_remembered_after_destroy", "colour" in remembered.split(","),
             remembered)
        maya_hubpop._restore()
        again = maya_hubpop._state()["popups"].get("colour")
        gate("D_restored", again is not None and again.alive())
        if again is not None:
            gate("D_restored_rolled_up", again.collapsed and
                 again.scroll.isHidden())
            gate("D_restored_at_its_offset", again.offset == offset,
                 [again.offset, offset])
            again.set_collapsed(False)
            maya_hubpop.close_popup("colour")
    res["was_open_restored"] = sorted(set(was_open) - set(maya_hubpop.open_keys()))

    for key in was_open:
        if key not in maya_hubpop.open_keys():
            try:
                maya_hubpop.open_popup(key)
            except Exception:
                pass
    res["open_now"] = maya_hubpop.open_keys()
    return res


def phase_e():
    """The window moved: the popup follows its viewport (its own send)."""
    import maya_hubpop
    from PySide6 import QtCore
    res = {"gates": {}}
    popup = maya_hubpop._state()["popups"].get("colour")
    if popup is None:
        popup = maya_hubpop.open_popup("colour")
    mw = maya_hubpop._main_window()
    res["main_before"] = [mw.x(), mw.y(), mw.width(), mw.height(),
                          bool(mw.isMaximized())]
    res["popup_before"] = [popup.root.x(), popup.root.y()]
    if mw.isMaximized():
        mw.showNormal()
    mw.setGeometry(QtCore.QRect(mw.x() + 180, mw.y() + 70, mw.width() - 300,
                                mw.height() - 200))
    res["main_moved_to"] = [mw.x(), mw.y(), mw.width(), mw.height()]
    res["rect_moved"] = list(maya_hubpop._rect_of(popup.panel) or [])
    return res


def phase_e_check(before):
    """The next send: the popup has followed (or not)."""
    import maya_hubpop
    popup = maya_hubpop._state()["popups"].get("colour")
    rect = maya_hubpop._rect_of(popup.panel)
    expected = maya_hubpop.rules.origin_of(popup.offset, rect, popup.root.width(),
                                           popup.root.height(), popup.scale)
    return {"rect": list(rect), "popup": [popup.root.x(), popup.root.y()],
            "expected": list(expected),
            "followed": (popup.root.x(), popup.root.y()) == tuple(expected)}


# The runner decides the action (the send's globals, trap 17): "run" (the
# gates A-D), "e1" (move the window), "e2" (check the follow). Each writes its
# own JSON once (a marker per action, trap 5).
_ACTION = globals().get("VERIFY_ACTION", "run")
_OUTS = {"run": OUT, "e1": OUT + ".e1.json", "e2": OUT + ".e2.json"}
if _ACTION in _OUTS and not os.path.exists(_OUTS[_ACTION] + ".ran"):
    open(_OUTS[_ACTION] + ".ran", "w").write("1")
    try:
        if _ACTION == "run":
            result = run(PHASES)
        elif _ACTION == "e1":
            result = phase_e()
        else:
            result = phase_e_check(None)
    except Exception:
        result = {"error": traceback.format_exc()}
    open(_OUTS[_ACTION], "w", encoding="utf-8").write(
        json.dumps(result, indent=2, ensure_ascii=False, default=str))
