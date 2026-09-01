"""Live verification of the SkeldarAnim installer, run inside Maya.

Eight gates: the real install() into this Maya's prefs, the payload on
disk, the shelf and its five buttons, every button command actually
executing (windows up, then closed), the OverRig panel sourcing, the
installed catalog resolving the shipped sword, idempotence of a second
install, and session hygiene (sys.path put back).

Sent through the command-port bridge. Bridge hygiene lives in the runner
(if-guarded marker, no SystemExit, unique output file); this script only
needs to avoid modal dialogs -- which is what install(quiet=True) is for.
"""

import importlib.util
import os
import sys

import maya.cmds as cmds
import maya.mel as mel

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"

RESULTS = []


def gate(number, name, passed, detail=""):
    RESULTS.append("GATE {0} {1} {2}{3}".format(
        number, "PASS" if passed else "FAIL", name,
        " - " + str(detail) if detail else ""))


def load_probe(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


path_before = list(sys.path)
modules_before = set(sys.modules)

# ---- Gate 1: install() runs from the repo's install.py ---------------
install_mod = None
dest = ""
try:
    install_mod = load_probe("skeldar_install_probe",
                             REPO + "/install.py")
    dest = install_mod.install(quiet=True).replace("\\", "/")
    gate(1, "install() ran", bool(dest), dest)
except Exception as exc:  # noqa: broad -- a gate reports, never raises
    gate(1, "install() ran", False, repr(exc))

# ---- Gate 2: the payload landed, whole and alone ---------------------
try:
    listed = sorted(os.listdir(dest))
    wanted = sorted(install_mod.payload())
    misc_ok = os.path.isdir(os.path.join(dest, "overrig", "misc"))
    gate(2, "payload on disk", listed == wanted and misc_ok,
         "extra={0} missing={1} misc={2}".format(
             [n for n in listed if n not in wanted],
             [n for n in wanted if n not in listed], misc_ok))
except Exception as exc:
    gate(2, "payload on disk", False, repr(exc))

# ---- Gate 3: the shelf and its five buttons --------------------------
buttons = []
try:
    exists = cmds.shelfLayout(install_mod.SHELF, exists=True)
    # every child of this shelf is one of our buttons: _build_shelf makes
    # nothing else, and the rebuild deletes whatever was there before
    buttons = (cmds.shelfLayout(install_mod.SHELF, query=True,
                                childArray=True) or []) if exists else []
    labels = [cmds.shelfButton(b, query=True, label=True) for b in buttons]
    gate(3, "shelf with five buttons",
         exists and labels == ["Rig Picker", "UE Bridge", "Scene Setup",
                               "Overshoot", "OverRig"],
         "exists={0} labels={1}".format(exists, labels))
except Exception as exc:
    gate(3, "shelf with five buttons", False, repr(exc))

# ---- Gate 4: each Python button command executes, window appears -----
WINDOWS = {
    "UE Bridge": "ueAnimBridgeWindow",
    "Scene Setup": "mayaSceneSetupWindow",
    "Overshoot": "animOvershootWin",
}


def picker_widget():
    from PySide6.QtWidgets import QApplication
    for widget in QApplication.topLevelWidgets():
        if widget.objectName() == "rigPickerWindow":
            return widget
    return None


for button in buttons:
    label = cmds.shelfButton(button, query=True, label=True)
    if label == "OverRig":
        continue
    try:
        command = cmds.shelfButton(button, query=True, command=True)
        exec(compile(command, "<shelf:{0}>".format(label), "exec"), {})
        if label == "Rig Picker":
            widget = picker_widget()
            up = widget is not None
            if widget is not None:
                widget.close()
        else:
            up = cmds.window(WINDOWS[label], exists=True)
            if up:
                cmds.deleteUI(WINDOWS[label], window=True)
        gate(4, "button '{0}' opens its window".format(label), up)
    except Exception as exc:
        gate(4, "button '{0}' opens its window".format(label), False,
             repr(exc))

# ---- Gate 5: the OverRig button sources the toolset and its panel ----
try:
    overrig_cmd = cmds.shelfButton(buttons[4], query=True, command=True)
    mel.eval(overrig_cmd)
    sourced = bool(mel.eval('exists "base_OverRig_scripts"'))
    dock = cmds.dockControl("basicOverRigScripts", query=True,
                            exists=True)
    gate(5, "OverRig panel up (left open - it is the user's tool)",
         sourced and dock, "sourced={0} dock={1}".format(sourced, dock))
except Exception as exc:
    gate(5, "OverRig panel up", False, repr(exc))

# ---- Gate 6: the installed catalog resolves the shipped sword --------
try:
    catalog = load_probe("skeldar_catalog_probe",
                         dest + "/maya_scenesetup/catalog.py")
    sword = catalog.WEAPONS[0].path
    gate(6, "installed catalog finds the shipped sword",
         sword.startswith(dest) and os.path.isfile(sword)
         and catalog.missing(catalog.WEAPONS[0]) == "",
         sword)
except Exception as exc:
    gate(6, "installed catalog finds the shipped sword", False, repr(exc))

# ---- Gate 7: a second install is an update, not a duplicate ----------
try:
    install_mod.install(quiet=True)
    again = cmds.shelfLayout(install_mod.SHELF, query=True,
                             childArray=True) or []
    gate(7, "second install keeps five buttons", len(again) == 5,
         "buttons={0}".format(len(again)))
except Exception as exc:
    gate(7, "second install keeps five buttons", False, repr(exc))

# ---- Gate 8: session hygiene -----------------------------------------
try:
    sys.path[:] = path_before
    for name in [n for n in set(sys.modules) - modules_before]:
        module = sys.modules[name]
        file_path = getattr(module, "__file__", "") or ""
        if file_path.replace("\\", "/").startswith(dest):
            del sys.modules[name]
    leaked = [p for p in sys.path
              if p.replace("\\", "/").startswith(dest)]
    gate(8, "sys.path and sys.modules put back", not leaked,
         "leaked={0}".format(leaked))
except Exception as exc:
    gate(8, "sys.path and sys.modules put back", False, repr(exc))

print("\n".join(RESULTS))
failed = sum(1 for line in RESULTS if " FAIL " in line)
print("VERDICT: {0} of {1} gates failed".format(failed, len(RESULTS)))
