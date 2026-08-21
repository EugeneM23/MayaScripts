"""Drag this file into an open Maya viewport to install SkeldarAnim.

Copies the toolset into <userAppDir>/scripts/SkeldarAnim and builds the
SkeldarAnim shelf: Rig Picker, UE Bridge, Scene Setup, Overshoot, and the
native OverRig panel. Re-dragging updates in place. The unzipped folder
can be deleted after installing.

Design: docs/superpowers/specs/2026-08-21-installer-design.md

Stdlib-only at import: at drop time nothing of ours is on sys.path, and
maya.cmds exists only inside the running Maya -- so the Maya imports live
inside the functions that run there.
"""

import os
import shutil

SHELF = "SkeldarAnim"

# The whitelist. Everything the animator's prefs receive, and nothing
# else: tests, docs, archive and the other root-level tools stay home.
_PAYLOAD = (
    "maya_overrig",
    "maya_uebridge",
    "maya_scenesetup",
    "maya_overshoot.py",
    "icons",
    "assets",
    "overrig",
    "install.py",
    "README_INSTALL.txt",
)

_PYTHON_BUTTONS = (
    ("Rig Picker", "OverRig picker: build, switch and select the rig",
     "maya_overrig", "show_picker", "picker.png"),
    ("UE Bridge", "Import animations from the running Unreal editor",
     "maya_uebridge", "show_window", "uebridge.png"),
    ("Scene Setup", "Weapon in the hand, camera on the camera bone",
     "maya_scenesetup", "show_window", "scenesetup.png"),
    ("Overshoot", "Build the stop of a move on the selected keys",
     "maya_overshoot", "show_overshoot_ui", "overshoot.png"),
)


def payload():
    """What gets copied, as names relative to the distribution root."""
    return _PAYLOAD


def source_root():
    """The distribution root: the folder this file was dragged from."""
    return os.path.dirname(os.path.abspath(__file__))


def button_specs(dest):
    """The five shelf buttons as data, every path baked in absolute.

    `dest` may arrive with backslashes; commands reach MEL and the shelf
    editor, where a backslash starts an escape -- so it is normalised
    once here and nowhere else needs to care.
    """
    dest = dest.replace("\\", "/").rstrip("/")
    bootstrap = (
        "import sys\n"
        "_p = \"{0}\"\n"
        "if _p not in sys.path:\n"
        "    sys.path.insert(0, _p)\n").format(dest)
    specs = []
    for label, note, module, func, icon in _PYTHON_BUTTONS:
        specs.append({
            "label": label,
            "annotation": note,
            "image": "{0}/icons/{1}".format(dest, icon),
            "sourceType": "python",
            "command": (bootstrap
                        + "import {0}\n{0}.{1}()\n".format(module, func)),
        })
    # Verbatim from OverRig's own Drag_and_Drop_to_install.mel, paths
    # aside: the two globals and the (1) coloring are the author's own
    # defaults, and $path_to_JGLBN must point at the shipped misc/.
    specs.append({
        "label": "OverRig",
        "annotation": "The native OverRig panel (Pavel Barnev, v10.2)",
        "image": "{0}/overrig/icons/base_OverRig.bmp".format(dest),
        "sourceType": "mel",
        "command": (
            'source "{0}/overrig/base_OverRig_scripts.mel";\n'
            "global int $barnev_OverRig_RotateOrder = 0;\n"
            "global string $path_to_JGLBN;\n"
            '$path_to_JGLBN = "{0}/overrig/misc/";\n'
            "base_OverRig_scripts(1);\n").format(dest),
    })
    return specs


def same_place(a, b):
    """True when the two paths are one folder on disk.

    The guard that keeps a re-drag from the installed folder itself from
    rmtree-ing the very files it is about to copy.
    """
    if not (os.path.isdir(a) and os.path.isdir(b)):
        return False
    return os.path.samefile(a, b)


def copy_payload(src_root, dest):
    """The whitelist into `dest`, replacing whatever was there."""
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in payload():
        src = os.path.join(src_root, name)
        target = os.path.join(dest, name)
        if os.path.isdir(src):
            shutil.copytree(src, target, ignore=ignore)
        else:
            shutil.copy2(src, target)


def _build_shelf(dest):
    """The SkeldarAnim tab, rebuilt button-for-button.

    The tab is created through Maya's own addNewShelfTab (it keeps the
    shelf optionVars consistent) and never deleted -- an existing tab
    only has its buttons replaced, which is what makes a re-drag an
    update rather than a duplicate.
    """
    import maya.cmds as cmds
    import maya.mel as mel
    if not cmds.shelfLayout(SHELF, exists=True):
        mel.eval('addNewShelfTab "{0}";'.format(SHELF))
    for child in cmds.shelfLayout(SHELF, query=True, childArray=True) or []:
        cmds.deleteUI(child)
    for spec in button_specs(dest):
        cmds.shelfButton(
            label=spec["label"],
            annotation=spec["annotation"],
            image=spec["image"],
            sourceType=spec["sourceType"],
            command=spec["command"],
            parent=SHELF,
        )


def install(dropped=None, quiet=False):
    """Copy the payload, build the shelf, say so.

    `dropped` is the path Maya hands onMayaDroppedPythonFile; __file__
    is the fallback. `quiet` skips the confirm dialog: a modal dialog
    over the command port blocks Maya's idle queue, so scripted runs
    must never raise one.
    """
    import maya.cmds as cmds
    src = os.path.dirname(os.path.abspath(dropped)) if dropped \
        else source_root()
    dest = os.path.join(cmds.internalVar(userAppDir=True),
                        "scripts", SHELF)
    if not same_place(src, dest):
        copy_payload(src, dest)
    _build_shelf(dest.replace("\\", "/"))
    if not quiet:
        cmds.confirmDialog(
            title="SkeldarAnim",
            message="Installed: shelf {0}, {1} buttons.\n{2}".format(
                SHELF, len(button_specs(dest)), dest),
            button=["OK"])
    return dest


def onMayaDroppedPythonFile(*args):
    install(args[0] if args else None)
