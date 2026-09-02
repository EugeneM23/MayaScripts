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

Every key this script binds is bound while its own SANDBOX set is current,
and gate 5 refuses if that set is not current: the animator's own set
cannot be written to. One thing is left behind on purpose --
`skeldarAnimVerifyProbe`, a nameCommand -- because Maya has no flag that
deletes one. It is named to be recognisable and nothing is bound to it.

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
            key_before = cmds.hotkey(keyShortcut=TEST_KEY, query=True,
                                     name=True) or ""
            cmds.nameCommand("skeldarAnimVerifyProbe",
                             annotation="verify probe",
                             command="skeldarAnimPickerBuild",
                             sourceType="mel")
            cmds.hotkey(keyShortcut=TEST_KEY,
                        name="skeldarAnimVerifyProbe")
            sample = cmds.hotkey(keyShortcut=TEST_KEY, query=True,
                                 name=True) or ""
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
            inherited = cmds.hotkey(keyShortcut=TEST_KEY, query=True,
                                    name=True) or ""
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
