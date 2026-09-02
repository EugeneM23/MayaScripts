"""The temporary hotkey map: one shelf button that switches Maya's set.

Press `Hotkeys` on the SkeldarAnim shelf and Maya switches to a hotkey set
of our name; press it again and the animator's own set comes back. The map's
CONTENTS are theirs to lay out, in Maya's own Hotkey Editor -- what this
module adds is the switch, plus a command list worth binding: every button
of our panels, and every one-press procedure OverRig's author published in
`function_for_hotkeys.TXT`.

Design: docs/superpowers/specs/2026-09-02-hotkey-map-design.md

`maya.cmds` and `maya.mel` only at module level. Qt lives below the four
`_*_module()` seams: `picker_window` imports PySide6 when it loads, and four
of the five shelf buttons have to keep working on a Maya that has PySide2.
The seams are also where the tests hand in a fake panel.
"""

import importlib
import os
import traceback
from functools import partial

import maya.cmds as cmds
import maya.mel as mel

SET = "SkeldarAnim"
SHELF = "SkeldarAnim"
BUTTON_LABEL = "Hotkeys"
PREVIOUS_VAR = "skeldarAnimPreviousHotkeySet"
FALLBACK_SET = "Maya_Default"
PREFIX = "skeldarAnim"
EDITOR_COMMAND = "HotkeyPreferencesWindow"
ON_COLOUR = (0.27, 0.38, 0.48)


# --------------------------------------------------------------- reporting

def _report(message):
    """Say it where a keypress can be seen, and hand the text back.

    A hotkey has no status bar of its own. An exception out of a
    runTimeCommand goes to the Script Editor and nowhere else, which is
    exactly how "I press it and nothing happens" happened before (trap 20).
    """
    cmds.inViewMessage(assistMessage=message, position="midCenterTop",
                       fade=True)
    return message


# ------------------------------------------------------------------- seams

def _picker_module():
    """Lazy, and the seam the tests replace. Qt lives below this line."""
    from maya_overrig import picker_window
    return picker_window


def _scene_module():
    from maya_scenesetup import window
    return window


def _overshoot_module():
    import maya_overshoot
    return maya_overshoot


def _overrig_module():
    """The MEL binding. cmds and mel only -- no Qt below here either."""
    from maya_overrig import overrig
    return overrig


# ----------------------------------------------------------------- actions

def _show(module_name, func):
    """Open a tool's window; its own module knows how."""
    module = importlib.import_module(module_name)
    return getattr(module, func)()


def _picker(method, *args):
    """Press a Rig Picker button.

    With the panel closed there is nothing to press: the picker's binding is
    the character the animator can SEE, and re-deriving one to act on is how
    two characters got rigged onto each other. So we open it and say so.
    """
    module = _picker_module()
    window = module.live_window()
    if window is None:
        module.show_picker()
        return _report(
            "Rig Picker opened - connect a character and press again")
    return getattr(window, method)(*args)


def _scene(func, *args):
    """Press a Scene Setup button. Its callbacks read their own window."""
    module = _scene_module()
    if not cmds.window(module.WINDOW, exists=True):
        module.show_window()
        return _report("Scene Setup opened - press again")
    return getattr(module, func)(*args)


def _overshoot(shape):
    """Apply one overshoot preset. Strength and Frames come from the panel."""
    module = _overshoot_module()
    if not cmds.window(module.WINDOW, exists=True):
        module.show_overshoot_ui()
        return _report("Overshoot opened - press again")
    return module.apply_overshoot(shape)


def _mel(script):
    """Run one OverRig procedure, sourcing the toolset first.

    Without the source, a fresh Maya with the OverRig shelf button unpressed
    answers a keypress with `Cannot find procedure` in the Script Editor
    (trap 20 from the hotkey side). Deliberately NOT gated on the time
    slider's highlight the way our own MEL entry points are (trap 36): half
    of these procedures are ABOUT the highlighted range.
    """
    overrig = _overrig_module()
    if not overrig.ensure_loaded():
        return _report(overrig.NOT_LOADED_MESSAGE)
    return mel.eval(script)


# --------------------------------------------------------------- the table

def row(key):
    """The row for `key`, or None."""
    return _INDEX.get(key)


def run(key):
    """Run one command. The body of every runTimeCommand we register.

    Every failure is reported where the animator is looking and the full
    traceback still goes to the Script Editor -- the panels' own `_run`,
    for a button that has no panel.

    Deliberately NO undo chunk of our own: `rebuild` already builds in one
    undo step and OverRig's procedures manage theirs, so wrapping a chunk
    in another chunk buys nothing and nests. A hotkey inherits whatever its
    target does, which is what the shelf buttons already do.
    """
    found = row(key)
    if found is None:
        return _report("Unknown hotkey command '{0}' - re-drag the "
                       "installer".format(key))
    label, action = found[2], found[4]
    try:
        return action()
    except Exception as error:  # noqa: BLE001 - the message is the report
        traceback.print_exc()
        return _report("{0} failed: {1}".format(label, error))


_OURS = (
    # key, category leaf, label, annotation, action
    ("window.picker", "Windows", "Rig Picker",
     "Open the Rig Picker panel",
     partial(_show, "maya_overrig", "show_picker")),
    ("window.uebridge", "Windows", "UE Bridge",
     "Open the UE animation bridge",
     partial(_show, "maya_uebridge", "show_window")),
    ("window.scenesetup", "Windows", "Scene Setup",
     "Open Scene Setup: character, weapon, camera",
     partial(_show, "maya_scenesetup", "show_window")),
    ("window.overshoot", "Windows", "Overshoot",
     "Open the Overshoot panel",
     partial(_show, "maya_overshoot", "show_overshoot_ui")),

    ("picker.connect", "Rig Picker", "Connect",
     "Bind the picker to the selected character",
     partial(_picker, "connect_to_selection")),
    ("picker.build", "Rig Picker", "Build",
     "Build the hybrid rig on the connected character",
     partial(_picker, "build_rig")),
    ("picker.fk", "Rig Picker", "FK Limbs",
     "Bring the selected limbs to FK",
     partial(_picker, "convert_selected_limbs", False)),
    ("picker.ik", "Rig Picker", "IK Limbs",
     "Bring the selected limbs to IK",
     partial(_picker, "convert_selected_limbs", True)),
    ("picker.bake", "Rig Picker", "Bake+Delete",
     "Bake what the selection touches back onto clean bones",
     partial(_picker, "bake_selected_limbs")),
    ("picker.all", "Rig Picker", "Select All",
     "Select every controller on the body map",
     partial(_picker, "select_group", "all")),

    ("scene.character", "Scene Setup", "Add Character",
     "Import the chosen skeleton into this scene",
     partial(_scene, "add_character")),
    ("scene.weapon", "Scene Setup", "Add Weapon",
     "Import the chosen weapon and drive its bone from it",
     partial(_scene, "add_weapon")),
    ("scene.remove_weapon", "Scene Setup", "Remove Weapon",
     "Bake the bone back off the weapon and delete it",
     partial(_scene, "remove_weapon")),
    ("scene.connect_arms", "Scene Setup", "Connect Arms To Weapon",
     "Both arms to IK, the weapon out to world, the hands onto it",
     partial(_scene, "connect_arms")),
    ("scene.disconnect_arms", "Scene Setup", "Disconnect Arms",
     "Lift the hands off the weapon and put it back in the hand",
     partial(_scene, "disconnect_arms")),
    ("scene.aim", "Scene Setup", "Add Aim",
     "OverRig's aim on the weapon, both locators placed",
     partial(_scene, "add_aim")),
    ("scene.camera", "Scene Setup", "Camera Setup",
     "A camera on camera_bone, the bone driven from it",
     partial(_scene, "camera_setup")),

    ("shoot.snap", "Overshoot", "Overshoot Snap",
     "One tight swing out of the pose", partial(_overshoot, "Snap")),
    ("shoot.spring", "Overshoot", "Overshoot Spring",
     "Three decaying swings", partial(_overshoot, "Spring")),
    ("shoot.elastic", "Overshoot", "Overshoot Elastic",
     "Six slowly decaying swings", partial(_overshoot, "Elastic")),
    ("shoot.recoil", "Overshoot", "Overshoot Recoil",
     "Two hard swings", partial(_overshoot, "Recoil")),
    ("shoot.bounce", "Overshoot", "Overshoot Bounce",
     "Arcs under gravity", partial(_overshoot, "Bounce")),
)

_OVERRIG = ()


def _prefixed(root, table):
    return tuple((key, root + "." + category, label, note, action)
                 for key, category, label, note, action in table)


COMMANDS = _prefixed("SkeldarAnim", _OURS) + _prefixed("OverRig", _OVERRIG)

_INDEX = dict((command[0], command) for command in COMMANDS)
