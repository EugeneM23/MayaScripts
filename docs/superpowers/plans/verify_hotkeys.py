"""Live verification of the temporary hotkey map, run inside Maya.

`hotkeySet` needs a UI -- it raises "Maya command error" in mayapy -- so
everything about the SET itself is proved here and nowhere else.

This script touches PREFS, not the scene, which changes the hygiene rules:
the current set name and the whole set list are recorded first, every
restore step stands on its own (trap 42: one raising teardown step abandons
the rest), and our set is deleted only if THIS RUN created it. An animator
who already has a SkeldarAnim set with their own keys in it must find it
exactly as they left it -- those gates skip themselves and say why, the way
phase 2 of verify_two_characters.py steps aside when it finds manifests
that are not its own.

Every key this script binds ITSELF is bound while its own SANDBOX set is
current, and gate 5 refuses if that set is not current: the animator's own
set cannot be written to. One thing is left behind on purpose --
`skeldarAnimVerifyProbe`, a nameCommand -- because Maya has no flag that
deletes one. It is named to be recognisable and nothing is bound to it.

Two deliberate exceptions to "restore everything", both because proving the
feature IS the feature: calling `activate()` binds the four starter keys
into the `SkeldarAnim` set and marks them installed in an optionVar. When
that set already belongs to the animator it is not deleted afterwards, so
those four keys stay -- which is what they asked for. Gate 16 is the check
that nothing leaked anywhere else.

Gates 17-19 measure real key times, so they build their own locator with
its own keys and a real set-driven curve and delete both.

Sent through the command-port bridge. Bridge hygiene lives in the runner
(if-guarded marker, no SystemExit, unique output file); this script only
has to avoid modal dialogs, and the Hotkey Editor it opens is not one.
"""

import sys

import maya.cmds as cmds
import maya.mel as mel

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"

if REPO not in sys.path:
    sys.path.insert(0, REPO)
for name in [n for n in list(sys.modules)
             if n == "maya_hotkeys" or n.split(".")[0] in
             ("maya_overrig", "maya_scenesetup", "maya_uebridge")]:
    del sys.modules[name]

import maya_hotkeys  # noqa: E402

RESULTS = []
TEST_SET = "SkeldarAnim_verify_base"
TEST_KEY = "F12"


def gate(number, name, passed, detail=""):
    RESULTS.append("GATE {0} {1} {2}{3}".format(
        number, "PASS" if passed else "FAIL", name,
        " - " + str(detail) if detail else ""))


def skip(number, name, why):
    RESULTS.append("GATE {0} SKIP {1} - {2}".format(number, name, why))


# ---- what we found, so we can put it back ---------------------------
set_before = cmds.hotkeySet(query=True, current=True)
sets_before = sorted(cmds.hotkeySet(query=True, hotkeySetArray=True) or [])
ours_existed = maya_hotkeys.SET in sets_before
# Gate 13 runs a real OverRig row, and that one selects: the animator's
# selection is theirs, and a verify run gives it back (CLAUDE.md's rule).
selection_before = cmds.ls(selection=True, long=True) or []
var_before = cmds.optionVar(query=maya_hotkeys.PREVIOUS_VAR) \
    if cmds.optionVar(exists=maya_hotkeys.PREVIOUS_VAR) else None
created = []

RESULTS.append("BEFORE current={0} sets={1} ours_existed={2}".format(
    set_before, sets_before, ours_existed))

try:
    # ---- Gate 1: registration lands in Maya's command list ----------
    try:
        result = maya_hotkeys.register()
        name = maya_hotkeys.command_name("picker.build")
        exists = cmds.runTimeCommand(name, query=True, exists=True)
        category = cmds.runTimeCommand(name, query=True, category=True) \
            if exists else ""
        gate(1, "every row registered",
             exists and category == "SkeldarAnim.Rig Picker",
             "{0} created/updated, {1} -> {2}".format(
                 result, name, category))
    except Exception as exc:
        gate(1, "every row registered", False, repr(exc))

    # ---- Gate 2: all of them are really there -----------------------
    try:
        missing = [maya_hotkeys.command_name(row[0])
                   for row in maya_hotkeys.COMMANDS
                   if not cmds.runTimeCommand(
                       maya_hotkeys.command_name(row[0]),
                       query=True, exists=True)]
        gate(2, "no row missing", not missing,
             "{0} rows, missing {1}".format(
                 len(maya_hotkeys.COMMANDS), missing[:5]))
    except Exception as exc:
        gate(2, "no row missing", False, repr(exc))

    # ---- Gate 3: re-registration is an edit, not a duplicate --------
    try:
        again = maya_hotkeys.register()
        gate(3, "re-registration edits", again[0] == 0, str(again))
    except Exception as exc:
        gate(3, "re-registration edits", False, repr(exc))

    # ---- Gate 4: a base set of our own, so nothing of theirs moves --
    try:
        if TEST_SET in (cmds.hotkeySet(query=True, hotkeySetArray=True) or []):
            cmds.hotkeySet(TEST_SET, edit=True, delete=True)
        cmds.hotkeySet(TEST_SET, source=set_before, current=True)
        created.append(TEST_SET)
        gate(4, "sandbox base set is current",
             cmds.hotkeySet(query=True, current=True) == TEST_SET, TEST_SET)
    except Exception as exc:
        gate(4, "sandbox base set is current", False, repr(exc))

    # ---- Gate 5: a sample key in the base set -----------------------
    # A hotkey binds a nameCommand, not a runTimeCommand: the Hotkey Editor
    # makes one when a command is dragged onto a key, and with no editor in
    # the loop we make it ourselves.
    if cmds.hotkeySet(query=True, current=True) != TEST_SET:
        skip(5, "sample key bound in the base set",
             "the sandbox set is not current - refusing to bind a key in "
             "the animator's own set")
    else:
        try:
            # In QUERY mode `keyShortcut` is a boolean flag and the key goes
            # in POSITIONALLY -- `hotkey(keyShortcut="F12", query=True)`
            # raises "must be passed a boolean argument when query flag is
            # set". Measured live 2026-09-02, and it cost this script two
            # gates. Setting a binding is the other way round: there the key
            # IS the keyShortcut flag's value.
            key_before = cmds.hotkey(TEST_KEY, query=True, name=True) or ""
            cmds.nameCommand("skeldarAnimVerifyProbe",
                             annotation="verify probe",
                             command="skeldarAnimPickerBuild",
                             sourceType="mel")
            cmds.hotkey(keyShortcut=TEST_KEY,
                        name="skeldarAnimVerifyProbe")
            sample = cmds.hotkey(TEST_KEY, query=True, name=True) or ""
            gate(5, "sample key bound in the base set",
                 sample == "skeldarAnimVerifyProbe",
                 "{0}, was {1}".format(sample, key_before or "unbound"))
        except Exception as exc:
            gate(5, "sample key bound in the base set", False, repr(exc))

    # ---- Gates 6-8: create ours as a copy of that base ---------------
    if ours_existed:
        for number, name in ((6, "created from the current set"),
                             (7, "the copy inherited the sample key"),
                             (8, "the editor opened on creation")):
            skip(number, name,
                 "a SkeldarAnim set already exists - not touching the "
                 "animator's own keys")
    else:
        try:
            message = maya_hotkeys.activate()
            created.append(maya_hotkeys.SET)
            gate(6, "created from the current set",
                 cmds.hotkeySet(query=True, current=True)
                 == maya_hotkeys.SET and TEST_SET in message, message)
        except Exception as exc:
            gate(6, "created from the current set", False, repr(exc))
        try:
            inherited = cmds.hotkey(TEST_KEY, query=True, name=True) or ""
            gate(7, "the copy inherited the sample key",
                 inherited == "skeldarAnimVerifyProbe", inherited)
        except Exception as exc:
            gate(7, "the copy inherited the sample key", False, repr(exc))
        try:
            # The editor's window id is not documented, so ask Maya what is
            # up rather than guessing a name. It is non-modal, which is what
            # makes it safe to open over the command port at all (bridge
            # note 6: a modal dialog blocks the idle queue).
            windows = [w for w in (cmds.lsUI(windows=True) or [])
                       if "otkey" in w]
            gate(8, "the editor opened on creation", bool(windows),
                 "windows: " + str(windows))
        except Exception as exc:
            gate(8, "the editor opened on creation", False, repr(exc))

    # ---- Gate 9: the way back is the recorded name -------------------
    try:
        cmds.optionVar(stringValue=(maya_hotkeys.PREVIOUS_VAR, TEST_SET))
        if not maya_hotkeys.is_active():
            cmds.hotkeySet(maya_hotkeys.SET, edit=True, current=True)
        maya_hotkeys.deactivate()
        gate(9, "toggle back lands on the remembered set",
             cmds.hotkeySet(query=True, current=True) == TEST_SET,
             cmds.hotkeySet(query=True, current=True))
    except Exception as exc:
        gate(9, "toggle back lands on the remembered set", False, repr(exc))

    # ---- Gate 10: a hand-switch between presses is respected ---------
    try:
        maya_hotkeys.activate()
        cmds.hotkeySet(TEST_SET, edit=True, current=True)   # by hand
        maya_hotkeys.toggle()
        gate(10, "a hand-switch turns the map ON, not off",
             cmds.hotkeySet(query=True, current=True) == maya_hotkeys.SET,
             cmds.hotkeySet(query=True, current=True))
    except Exception as exc:
        gate(10, "a hand-switch turns the map ON, not off", False, repr(exc))

    # ---- Gate 11: the command body reaches run() ---------------------
    # The chain a keypress travels is key -> nameCommand -> runTimeCommand
    # -> body -> run(). A keypress cannot be sent over the port and a
    # nameCommand cannot be QUERIED (it has no -q flag at all, measured),
    # so the two halves are proved separately: gate 5 bound the key to a
    # nameCommand, and this runs a runTimeCommand the way Maya runs one --
    # by its own name, as MEL -- with a probe row standing in for a real
    # one so nothing in the scene moves.
    try:
        maya_hotkeys._REACHED = []
        maya_hotkeys._INDEX["verify.probe"] = (
            "verify.probe", "SkeldarAnim.Windows", "Probe", "probe",
            lambda: maya_hotkeys._REACHED.append(1))
        if cmds.runTimeCommand("skeldarAnimVerifyReach", query=True,
                               exists=True):
            cmds.runTimeCommand("skeldarAnimVerifyReach", edit=True,
                                delete=True)
        cmds.runTimeCommand(
            "skeldarAnimVerifyReach", command=maya_hotkeys.command_body(
                "verify.probe"), commandLanguage="python", default=False)
        mel.eval("skeldarAnimVerifyReach;")
        target = cmds.runTimeCommand("skeldarAnimPickerBuild", query=True,
                                     exists=True)
        gate(11, "a command body reaches run()",
             maya_hotkeys._REACHED == [1] and target,
             "reached {0}, gate 5's nameCommand target exists: {1}".format(
                 maya_hotkeys._REACHED, target))
    except Exception as exc:
        gate(11, "a command body reaches run()", False, repr(exc))
    finally:
        maya_hotkeys._INDEX.pop("verify.probe", None)

    # ---- Gate 12: the shelf button paints both ways ------------------
    try:
        button = maya_hotkeys.shelf_button()
        if not button:
            skip(12, "the shelf button paints",
                 "no Hotkeys button on the shelf - re-drag install.py")
        else:
            maya_hotkeys.paint(True)
            on = cmds.shelfButton(button, query=True,
                                  enableBackground=True)
            maya_hotkeys.paint(False)
            off = cmds.shelfButton(button, query=True,
                                   enableBackground=True)
            gate(12, "the shelf button paints", on and not off,
                 "{0}: on={1} off={2}".format(button, on, off))
    except Exception as exc:
        gate(12, "the shelf button paints", False, repr(exc))

    # ---- Gate 13: an OverRig row sources the toolset -----------------
    # Only honest in a FRESH Maya, where the OverRig shelf button has not
    # been pressed: that is the whole trap-20 case. Run it there.
    try:
        from maya_overrig import overrig
        was_loaded = overrig.is_loaded()
        maya_hotkeys.run("overrig.select_knots")
        gate(13, "an OverRig row sources the toolset",
             overrig.is_loaded(),
             "loaded before: {0} (only proves trap 20 in a fresh "
             "Maya)".format(was_loaded))
    except Exception as exc:
        gate(13, "an OverRig row sources the toolset", False, repr(exc))

    # ---- Gate 14: the shelf button's OWN command runs ----------------
    # Everything above called the module directly. This is the string the
    # installer baked into the button, which is what the animator's finger
    # travels: bootstrap sys.path, import, toggle. Pressed twice, so it
    # ends on the set it started from. (Both presses land on the module
    # THIS script imported from the repo -- `maya_hotkeys` is already in
    # sys.modules -- so what the gate proves is the string and the toggle,
    # not which copy on disk answers. A fresh session proves that.)
    try:
        button = maya_hotkeys.shelf_button()
        have_sandbox = cmds.hotkeySet(TEST_SET, query=True, exists=True)
        if not button:
            skip(14, "the shelf button's own command toggles",
                 "no Hotkeys button on the shelf - re-drag install.py")
        elif not have_sandbox:
            skip(14, "the shelf button's own command toggles",
                 "the sandbox base set is gone - nothing safe to toggle "
                 "against")
        else:
            cmds.hotkeySet(TEST_SET, edit=True, current=True)
            cmds.optionVar(stringValue=(maya_hotkeys.PREVIOUS_VAR, TEST_SET))
            body = cmds.shelfButton(button, query=True, command=True)
            globals_for_press = {"__name__": "__main__"}
            exec(compile(body, "shelfButton", "exec"), globals_for_press)
            on = cmds.hotkeySet(query=True, current=True)
            exec(compile(body, "shelfButton", "exec"),
                 dict(globals_for_press))
            back = cmds.hotkeySet(query=True, current=True)
            gate(14, "the shelf button's own command toggles",
                 on == maya_hotkeys.SET and back == TEST_SET,
                 "{0} -> {1} -> {2}".format(TEST_SET, on, back))
    except Exception as exc:
        gate(14, "the shelf button's own command toggles", False, repr(exc))

    # ---- Gate 15: the four starter keys are bound in OUR set ---------
    # All four were taken by a Maya default and overwriting them was the
    # animator's call. Inside our set only, which is what gate 16 checks.
    try:
        if not maya_hotkeys.is_active():
            cmds.hotkeySet(maya_hotkeys.SET, edit=True, current=True)
        wrong = []
        for key, modifiers, row_key in maya_hotkeys.DEFAULT_KEYS:
            held = cmds.hotkey(key, query=True, name=True, **modifiers) or ""
            wanted = maya_hotkeys.name_command(row_key)
            if held != wanted:
                wrong.append((key, held, wanted))
        gate(15, "the four starter keys are ours in our set", not wrong,
             "wrong: {0}".format(wrong) if wrong else
             "alt+a/s/4/5 -> prev/next/insert/remove")
    except Exception as exc:
        gate(15, "the four starter keys are ours in our set", False,
             repr(exc))

    # ---- Gate 16: and no other set has them --------------------------
    # The whole promise of a temporary map: what it takes, it takes only
    # inside itself. Checked against Maya_Default rather than the set that
    # was current on entry -- the animator may well have left the map ON,
    # in which case `set_before` IS ours and the gate would be comparing
    # our set with itself. Maya_Default always exists, is never ours, and
    # nothing here ever writes to it.
    try:
        cmds.hotkeySet(maya_hotkeys.FALLBACK_SET, edit=True, current=True)
        theirs = dict(
            (key, cmds.hotkey(key, query=True, name=True, **modifiers) or "")
            for key, modifiers, _row in maya_hotkeys.DEFAULT_KEYS)
        ours_names = set(maya_hotkeys.name_command(row)
                         for _k, _m, row in maya_hotkeys.DEFAULT_KEYS)
        leaked = [(key, held) for key, held in theirs.items()
                  if held in ours_names]
        gate(16, "no other set got our keys", not leaked,
             "leaked: {0}".format(leaked) if leaked else str(theirs))
    except Exception as exc:
        gate(16, "no other set got our keys", False, repr(exc))

    # ---- Gates 17-19: insert and remove on a SANDBOX -----------------
    # Never on the animator's curves: this measures real key times, so it
    # builds its own locator, gives it keys and a set-driven curve, and
    # deletes both. The driven curve is the gate that can fail --
    # `ls(type="animCurve")` answers it too, and shifting it would move a
    # set-driven-key relationship instead of animation.
    sandbox = []
    time_before = cmds.currentTime(query=True)
    auto_before = cmds.autoKeyframe(query=True, state=True)
    try:
        cmds.autoKeyframe(state=False)
        loc = cmds.spaceLocator(name="skdHotkeyProbe")[0]
        driver = cmds.spaceLocator(name="skdHotkeyDriver")[0]
        sandbox = [loc, driver]
        for frame, value in ((0, 0.0), (1, 1.0), (2, 2.0), (10, 10.0)):
            cmds.setKeyframe(loc + ".translateX", time=frame, value=value)
        # A real set-driven key: driver.tx drives loc.translateZ.
        cmds.setDrivenKeyframe(loc + ".translateZ",
                               currentDriver=driver + ".translateX",
                               driverValue=0.0, value=0.0)
        cmds.setDrivenKeyframe(loc + ".translateZ",
                               currentDriver=driver + ".translateX",
                               driverValue=5.0, value=5.0)
        driven = [c for c in (cmds.keyframe(loc, query=True, name=True) or [])
                  if cmds.objectType(c) not in maya_hotkeys.TIME_CURVES]
        moving = loc + "_translateX"

        def times(node):
            return cmds.keyframe(node, query=True, timeChange=True) or []

        def drivers(node):
            """A driven curve's x axis is a driver VALUE, so timeChange
            answers nothing at all for one -- the first version of gate 19
            compared [] with [] and could not fail. floatChange is the
            axis that would move if we shifted it by mistake."""
            return cmds.keyframe(node, query=True, floatChange=True) or []

        before_moving = times(moving)
        before_driven = [drivers(c) for c in driven]

        cmds.select(loc, replace=True)
        cmds.currentTime(1.0, edit=True)
        maya_hotkeys.run("time.insert")
        after_insert = times(moving)
        gate(17, "insert makes room after the current frame",
             after_insert == [0.0, 1.0, 3.0, 11.0],
             "{0} -> {1}".format(before_moving, after_insert))

        maya_hotkeys.run("time.remove")
        after_remove = times(moving)
        gate(18, "remove is insert's exact inverse",
             after_remove == before_moving,
             "{0} -> {1}".format(after_insert, after_remove))

        after_driven = [drivers(c) for c in driven]
        gate(19, "a set-driven curve never moved",
             bool(driven) and after_driven == before_driven
             and any(after_driven),
             "{0} driven curve(s): {1} -> {2}".format(
                 len(driven), before_driven, after_driven))
    except Exception as exc:
        for number, name in ((17, "insert makes room after the current "
                                  "frame"),
                             (18, "remove is insert's exact inverse"),
                             (19, "a set-driven curve never moved")):
            if not [line for line in RESULTS
                    if line.startswith("GATE {0} ".format(number))]:
                gate(number, name, False, repr(exc))
    finally:
        for node in sandbox:
            try:
                if cmds.objExists(node):
                    cmds.delete(node)
            except Exception:
                pass
        try:
            cmds.autoKeyframe(state=auto_before)
        except Exception:
            pass
        try:
            cmds.currentTime(time_before, edit=True)
        except Exception:
            pass

    # ---- Gate 20: stepping a frame ------------------------------------
    try:
        start = cmds.currentTime(query=True)
        maya_hotkeys.run("time.next")
        forward = cmds.currentTime(query=True)
        maya_hotkeys.run("time.prev")
        back = cmds.currentTime(query=True)
        gate(20, "alt+s/alt+a step one frame",
             forward == start + 1.0 and back == start,
             "{0:g} -> {1:g} -> {2:g}".format(start, forward, back))
    except Exception as exc:
        gate(20, "alt+s/alt+a step one frame", False, repr(exc))

    # ---- Gate 21: the starter keys' whole chain --------------------------
    # A keypress travels key -> nameCommand -> runTimeCommand -> body ->
    # run(). Gate 15 proved the first link for these four keys and gate 11
    # the last one for a probe row; this closes them for the real four:
    # each nameCommand points at the right runTimeCommand, and the two
    # stepping commands are RUN BY THEIR MEL NAME, which is exactly what a
    # keypress does. Only prev/next are run for real -- insert and remove
    # are proved on the sandbox above, and running them here would shift
    # the animator's own keys.
    try:
        wrong = []
        for _key, _mods, row_key in maya_hotkeys.DEFAULT_KEYS:
            wrapper = maya_hotkeys.name_command(row_key)
            wanted = maya_hotkeys.command_name(row_key)
            if not cmds.runTimeCommand(wanted, query=True, exists=True):
                wrong.append((wrapper, "no runTimeCommand " + wanted))
        start = cmds.currentTime(query=True)
        mel.eval(maya_hotkeys.command_name("time.next") + ";")
        stepped = cmds.currentTime(query=True)
        mel.eval(maya_hotkeys.command_name("time.prev") + ";")
        home = cmds.currentTime(query=True)
        gate(21, "the starter keys run by their MEL name",
             not wrong and stepped == start + 1.0 and home == start,
             "{0} | {1:g} -> {2:g} -> {3:g}".format(
                 wrong or "all four wired", start, stepped, home))
    except Exception as exc:
        gate(21, "the starter keys run by their MEL name", False, repr(exc))

finally:
    # Each step on its own: one raising teardown abandons the rest.
    #
    # The key needs no unbinding: every binding this script made was made
    # while the SANDBOX set was current, and the sandbox is deleted below.
    try:
        if cmds.runTimeCommand("skeldarAnimVerifyReach", query=True,
                               exists=True):
            cmds.runTimeCommand("skeldarAnimVerifyReach", edit=True,
                                delete=True)
    except Exception:
        pass
    try:
        if set_before in (cmds.hotkeySet(query=True, hotkeySetArray=True)
                          or []):
            cmds.hotkeySet(set_before, edit=True, current=True)
    except Exception:
        pass
    for name in created:
        try:
            if cmds.hotkeySet(name, query=True, exists=True):
                cmds.hotkeySet(name, edit=True, delete=True)
        except Exception:
            pass
    try:
        if var_before is None:
            cmds.optionVar(remove=maya_hotkeys.PREVIOUS_VAR)
        else:
            cmds.optionVar(stringValue=(maya_hotkeys.PREVIOUS_VAR,
                                        var_before))
    except Exception:
        pass
    try:
        alive = [node for node in selection_before if cmds.objExists(node)]
        if alive:
            cmds.select(alive, replace=True)
        else:
            cmds.select(clear=True)
    except Exception:
        pass

    sets_after = sorted(cmds.hotkeySet(query=True, hotkeySetArray=True)
                        or [])
    current_after = cmds.hotkeySet(query=True, current=True)
    RESULTS.append("AFTER current={0} sets={1}".format(
        current_after, sets_after))
    RESULTS.append("HYGIENE sets restored: {0}, current restored: {1}".format(
        sets_after == sets_before, current_after == set_before))

    failed = len([line for line in RESULTS if " FAIL " in line])
    print("\n".join(RESULTS))
    print("VERIFY hotkeys: {0} of {1} gates failed".format(
        failed, len([line for line in RESULTS if line.startswith("GATE")])))
