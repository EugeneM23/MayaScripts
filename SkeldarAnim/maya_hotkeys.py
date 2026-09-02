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


# ------------------------------------------------------------ registration

def install_dir():
    """The folder this module was installed into.

    The path a command's body has to put on `sys.path`: a key pressed
    before any shelf button in a fresh Maya has nothing of ours there. Read
    from our own location, so the installed copy knows where it lives and a
    move is picked up by the next registration.
    """
    return os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")


def command_name(key):
    """`picker.build` -> `skeldarAnimPickerBuild`.

    Maya wants an identifier; the readable name is the row's `label`, which
    is what the Hotkey Editor shows.
    """
    parts = [chunk[:1].upper() + chunk[1:]
             for chunk in key.replace(".", "_").split("_") if chunk]
    return PREFIX + "".join(parts)


def command_body(key, dest=None):
    """The runTimeCommand's body: bootstrap, then dispatch through us.

    Deliberately a one-liner into the table rather than real logic. Maya
    SAVES a user runTimeCommand into userRunTimeCommands.mel (measured:
    `default` comes back False), so a body is a copy that outlives the
    installed plugin -- and this one keeps resolving through whatever table
    is current, or reports an unknown key instead of raising.
    """
    dest = install_dir() if dest is None \
        else dest.replace("\\", "/").rstrip("/")
    return ("import sys\n"
            "_p = \"{0}\"\n"
            "if _p not in sys.path:\n"
            "    sys.path.insert(0, _p)\n"
            "import maya_hotkeys\n"
            "maya_hotkeys.run(\"{1}\")\n").format(dest, key)


def register(dest=None):
    """Create or refresh every command. Returns (created, updated).

    Called from `toggle()` in both directions, which is the only moment
    registration happens: a press that turns the map OFF refreshes the
    commands too, so an updated plugin's rows -- and the path baked inside
    them -- come into step with what is on disk.
    """
    created = updated = 0
    for key, category, label, annotation, _action in COMMANDS:
        name = command_name(key)
        body = command_body(key, dest)
        if cmds.runTimeCommand(name, query=True, exists=True):
            cmds.runTimeCommand(name, edit=True, command=body,
                                category=category, label=label,
                                annotation=annotation,
                                commandLanguage="python")
            updated += 1
        else:
            cmds.runTimeCommand(name, command=body, category=category,
                                label=label, annotation=annotation,
                                commandLanguage="python", default=False)
            created += 1
    return created, updated


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

# Pavel Barnev's own list of procedures meant for hotkeys, from
# overrig/function_for_hotkeys.TXT, with his headings as the categories and
# his arguments as written there.
#
# Two procedures are deliberately absent, spelled out here so a grep for
# either one lands on the reason: barn_fast_bake_source_obj_and_delete_knots
# and barn_fast_bake_min_max_or_range_source_obj_and_delete_knots are the
# only ones in the file that ignore the selection and work on the whole
# scene -- they select all of OverRig_rig_objects, bake, and delete every
# knot -- which is not a thing to put one keypress away. A gone-test names
# both. The ones needing real arguments (execute_overlap_command, the motion
# trail, the ribbon) are here as their windows instead: for those, the
# window IS the one-press command.
_OVERRIG = (
    ("overrig.panel", "Menu", "OverRig panel",
     "The native OverRig panel", partial(_mel, "base_OverRig_scripts(1);")),

    ("overrig.rotate_order_xyz", "Rotation order", "Convert to xyz",
     "Convert the selection's rotation order to xyz",
     partial(_mel, 'barn_execute_convert_rotation_order("xyz");')),

    ("overrig.smart_knot", "Smart object", "Smart knot",
     "Bake the animation onto a smart locator",
     partial(_mel, "apply_smart_parentConstrAnim(1);")),
    ("overrig.smart_pivot", "Smart object", "Smart pivot knot",
     "Bake the animation onto a smart offset locator",
     partial(_mel, "apply_smart_PivotParentAnimation(1.5);")),
    ("overrig.smart_orient", "Smart object", "Smart orient knot",
     "Bake the animation onto a smart orient locator",
     partial(_mel, "apply_smart_Knot_Orient_Point(1.5);")),
    ("overrig.smart_bake_object", "Smart object", "Smart bake (object keys)",
     "Bake with this object's keyframes",
     partial(_mel, "apply_Smart_Bake(0);")),
    ("overrig.smart_bake_knot", "Smart object", "Smart bake (knot keys)",
     "Bake with the smart knot's keyframes",
     partial(_mel, "apply_Smart_Bake(1);")),

    ("overrig.knot_orient", "Knot", "Knot orient",
     "Create an orient knot on the selection",
     partial(_mel, "apply_Knot_Orient_Point(1);")),
    ("overrig.knot_pivot", "Knot", "Pivot knot",
     "Create a pivot knot on the selection",
     partial(_mel, "apply_PivotParentAnimation(1);")),
    ("overrig.knot", "Knot", "Knot",
     "Create a knot on the selection",
     partial(_mel, "apply_parentConstrAnim(1);")),

    ("overrig.parent_out", "Parent", "Parent to world",
     "Lift the selection to world, animation re-baked",
     partial(_mel, "apply_Parent_out();")),
    ("overrig.parent_in", "Parent", "Parent inside",
     "Hang the child on the parent - select child first, parent last",
     partial(_mel, "apply_Parent_in();")),
    ("overrig.parent_swap", "Parent", "Swap parent",
     "Swap the parent", partial(_mel, "apply_Swap_parent();")),
    ("overrig.parent_across", "Parent", "Parent across knot",
     "Create a parent-across knot",
     partial(_mel, "apply_parent_anim_across(1);")),

    ("overrig.aim", "Aim", "Create aim",
     "Create the aim locators on the selection",
     partial(_mel, "make_aim_from_selected(1);")),
    ("overrig.overlap_window", "Aim", "Overlapper window",
     "Open the overlapper window",
     partial(_mel, "bar_tail_overlap_window;")),
    ("overrig.attach_on", "Aim", "Key attach 1",
     "Key the attach attribute at 1",
     partial(_mel, "setKey_on_attach_attr(1);")),
    ("overrig.attach_off", "Aim", "Key attach 0",
     "Key the attach attribute at 0",
     partial(_mel, "setKey_on_attach_attr(0);")),

    ("overrig.lag_key", "Key tools", "Lag key",
     "Lag the keys by 1.2 frames", partial(_mel, "Lag_Key(1.2);")),
    ("overrig.infinity_cycle", "Key tools", "Infinity: cycle",
     "Pre/post infinity to cycle",
     partial(_mel, 'set_infinity_graphEditor("cycle");')),
    ("overrig.infinity_oscillate", "Key tools", "Infinity: oscillate",
     "Pre/post infinity to oscillate",
     partial(_mel, 'set_infinity_graphEditor("oscillate");')),
    ("overrig.infinity_linear", "Key tools", "Infinity: linear",
     "Pre/post infinity to linear",
     partial(_mel, 'set_infinity_graphEditor("linear");')),
    ("overrig.infinity_constant", "Key tools", "Infinity: constant",
     "Pre/post infinity to constant",
     partial(_mel, 'set_infinity_graphEditor("constant");')),
    ("overrig.oscillate", "Key tools", "Oscillate keys",
     "Oscillate the period taken from the time slider",
     partial(_mel, "double_oscillate_keys(2);")),
    ("overrig.first_to_last", "Key tools", "Copy first frame to last",
     "For cycling animation", partial(_mel, "copy_start_frame_to_end();")),
    ("overrig.keys_first_last", "Key tools", "Key first and last frame",
     "Set keys on the first and last frame",
     partial(_mel, "set_start_end_key();")),
    ("overrig.key_range_all", "Key tools", "Key range: all",
     "The same keyframe across the selected time range",
     partial(_mel, 'set_key_time_range("all");')),
    ("overrig.key_range_translate", "Key tools", "Key range: translate",
     "Translate keys across the selected time range",
     partial(_mel, 'set_key_time_range("translate");')),
    ("overrig.key_range_rotate", "Key tools", "Key range: rotate",
     "Rotate keys across the selected time range",
     partial(_mel, 'set_key_time_range("rotate");')),
    ("overrig.key_range_channelbox", "Key tools", "Key range: channel box",
     "The channel box's channels across the selected time range",
     partial(_mel, 'set_key_time_range("channelbox");')),
    ("overrig.select_keys_range", "Key tools", "Select keys in range",
     "Select the current key or the selected frame range",
     partial(_mel, "selKeys_by_timerange();")),
    ("overrig.delete_keys", "Key tools", "Delete keys",
     "Delete the selected frames on every channel of every selection",
     partial(_mel, "delete_keys_from_selected_or_timeslider();")),
    ("overrig.slider_range", "Key tools", "Toggle slider range",
     "Toggle the time slider range by 24",
     partial(_mel, "time_slider_range(24);")),
    ("overrig.time_to_mid", "Key tools", "Time to mid selection",
     "Move the time slider to the middle of the selection",
     partial(_mel, "set_currenttime_to_mid_selection();")),
    ("overrig.copy_keys", "Key tools", "Copy keys",
     "Copy the selected single-curve frames",
     partial(_mel, "barn_copy_keys();")),
    ("overrig.paste_scaled", "Key tools", "Paste scaled keys",
     "Paste, scaled to the selected frames",
     partial(_mel, "barn_past_scaled_keys();")),
    ("overrig.offset_half_period", "Key tools", "Offset by half period",
     "Shift the keys by half a period",
     partial(_mel, "offset_keys_by_period(2);")),
    ("overrig.mirror_keys", "Key tools", "Mirror keys in X",
     "Inverse-mirror the selected keys about X",
     partial(_mel, 'double_inv_oscillate_or_mirror(2, "x", "x");')),
    ("overrig.noise_window", "Key tools", "Noise window",
     "Open the noise window", partial(_mel, "overRig_noise_window;")),
    ("overrig.tween_window", "Key tools", "Tween window",
     "Tween, overshoot and curve push",
     partial(_mel, "overRig_tween_window();")),
    ("overrig.tween_left", "Key tools", "Tween 0%",
     "All the way to the left-side key",
     partial(_mel, "bar_tween_machine(0, `ls -sl`);")),
    ("overrig.tween_right", "Key tools", "Tween 100%",
     "All the way to the right-side key",
     partial(_mel, "bar_tween_machine(1, `ls -sl`);")),

    ("overrig.select_constrained", "Selector", "Select constrained object",
     "From a knot to the object it drives",
     partial(_mel, "return_constrained_object(1);")),
    ("overrig.select_sources", "Selector", "Select rig sources",
     "Every object OverRig's rigs drive",
     partial(_mel, 'barn_sel_set_member("OverRig_rig_objects");')),
    ("overrig.select_knots", "Selector", "Select knots",
     "Every OverRig knot in the scene",
     partial(_mel, 'barn_sel_set_member("OverRig_knots");')),

    ("overrig.double_global", "Double knots", "Double global knot",
     "Create a double global knot",
     partial(_mel, "apply_DoubleUzelGlobal(1);")),
    ("overrig.double_local", "Double knots", "Double local knot",
     "Create a double local knot",
     partial(_mel, "apply_DoubleUzelLocal(1);")),

    ("overrig.snapshot_object", "Snapshot", "Object snapshot",
     "Create an object snapshot", partial(_mel, "apply_LOH_Fast(1);")),
    ("overrig.snapshot_component", "Snapshot", "Component snapshot",
     "Create a component snapshot",
     partial(_mel, "apply_LOH_Component(1);")),

    ("overrig.forward_hierarchy", "Hierarchy", "Forward hierarchy",
     "Create a forward hierarchy over the selection",
     partial(_mel, "apply_ForwHierarhy(1);")),
    ("overrig.reverse_hierarchy", "Hierarchy", "Reverse hierarchy",
     "Create a reverse hierarchy over the selection",
     partial(_mel, "apply_ReverseHierarhy(1);")),
    ("overrig.spine_menu", "Hierarchy", "Vertebra system menu",
     "Bake to the easy vertebra system",
     partial(_mel, "create_recalc_spine_rig_menue();")),

    ("overrig.to_ik", "IK", "Bake FK to IK",
     "Three or more selected joints to IK",
     partial(_mel, "apply_rebike_3_or_more_object_to_IK;")),
    ("overrig.spline_ik", "IK", "Bake to spline IK",
     "Two or more selected to spline IK",
     partial(_mel, "apply_objects_spline_IK(0);")),
    ("overrig.spline_ik_depend", "IK", "Bake to depend spline IK",
     "Two or more selected to dependent spline IK",
     partial(_mel, "apply_objects_spline_IK(1);")),

    ("overrig.bake", "Bake", "Bake",
     "Bake the selection", partial(_mel, "apply_Fast_Bake();")),
    ("overrig.bake_range", "Bake", "Bake range",
     "Bake min-max or the selected range, keys outside kept",
     partial(_mel, "apply_range_Fast_Bake();")),
    ("overrig.bake_layer", "Bake", "Bake to layer",
     "Bake the selection to an anim layer",
     partial(_mel, "apply_Bake_to_layer();")),
    ("overrig.bake_range_layer", "Bake", "Bake range to override layer",
     "Bake min-max or the selected range to an override layer",
     partial(_mel, "apply_range_Bake_to_Over_layer();")),
    ("overrig.strip_constraints", "Bake", "Delete constraint channels",
     "Strip the constraint channels from the selection",
     partial(_mel, "delete_constraint_attributes_on_objects(`ls -sl`);")),
    ("overrig.euler_filter", "Bake", "Euler filter",
     "Fast euler filter from zero",
     partial(_mel, "euler_filter_on_selected();")),
    ("overrig.viewport_on", "Bake", "Enable viewport",
     "Turn the viewport back on after a bake",
     partial(_mel, "OVR_en_viewport();")),

    ("overrig.arc_tool", "Sword", "Arc polish tool",
     "Open the arc polish tool", partial(_mel, "BP_arc_tool_menue();")),
    ("overrig.sword_reverse", "Sword", "Sword reverse system",
     "Assign the sword reverse system",
     partial(_mel, "assign_Sword_pivot_System(1);")),
    ("overrig.sword_system", "Sword", "Sword system",
     "Assign the sword system", partial(_mel, "assign_Sw_System;")),

    ("overrig.jiggle", "Physics", "Jiggle point",
     "Assign a physical point on the selection",
     partial(_mel, "assign_jiggle_bone_soft(1);")),
    ("overrig.chain_menu", "Physics", "Physic chain menu",
     "Open the physics chain window",
     partial(_mel, "dyn_tail_tool_window();")),

    ("overrig.locators_on_selected", "Misc", "Locators on selected",
     "Create locators on the selection",
     partial(_mel, "create_normalised_locators_on_selected();")),
    ("overrig.locators_inside", "Misc", "Locators inside",
     "Create locators inside the selection",
     partial(_mel, "mocup_parent_locators_inside();")),
    ("overrig.color_menu", "Misc", "Colour menu",
     "Override the display colour",
     partial(_mel, "small_DisplayColorOverrideUI();")),
    ("overrig.shape_menu", "Misc", "Shape menu",
     "Override the control shape",
     partial(_mel, "small_Shape_OverrideUI();")),
    ("overrig.scale_up", "Misc", "Scale locator or joint 1.5",
     "Locally scale the selected locator or joint",
     partial(_mel, "scale_selected_lock_or_joint(1.5);")),
    ("overrig.anim_pivot_last", "Misc", "Anim pivot (last selected)",
     "Animated pivot at the last selected position",
     partial(_mel, "move_and_rotate_total_pivot(0);")),
    ("overrig.anim_pivot_average", "Misc", "Anim pivot (average)",
     "Animated pivot at the average position",
     partial(_mel, "move_and_rotate_total_pivot(1);")),
    ("overrig.isolate_toggle", "Misc", "Isolate selection toggle",
     "Toggle isolate-select in the current viewport",
     partial(_mel, "apply_bar_isolate_selection_toggler(0);")),
    ("overrig.translate_axis", "Misc", "Translate tool axis",
     "Change the translate tool's axis",
     partial(_mel, "bar_translate_toggler();")),
    ("overrig.rotate_axis", "Misc", "Rotate tool axis",
     "Change the rotate tool's axis",
     partial(_mel, "bar_rotate_toggler();")),
    ("overrig.xray", "Misc", "X-ray toggle",
     "Toggle x-ray in the current viewport",
     partial(_mel, "bar_x_ray_toggler();")),

    ("overrig.finger_pivot_window", "Finger", "Finger pivot window",
     "Open the finger pivot window",
     partial(_mel, "brn_apply_finger_pivot_window();")),
    ("overrig.finger_bend", "Finger", "Finger bend",
     "Finger bend tool",
     partial(_mel, 'brn_apply_finger_bend_tool("bend");')),
    ("overrig.finger_3ik", "Finger", "Finger 3IK",
     "Finger three-joint IK",
     partial(_mel, 'brn_apply_finger_bend_tool("3IK");')),
    ("overrig.finger_4ik", "Finger", "Finger 4IK",
     "Finger four-joint IK variant",
     partial(_mel, 'brn_apply_finger_bend_tool("4IK_var");')),
    ("overrig.finger_rot_pivot", "Finger", "Finger rotate pivot",
     "Finger rotate-pivot tool",
     partial(_mel, 'brn_apply_finger_bend_tool("rot_piv");')),
    ("overrig.finger_twist", "Finger", "Finger twist",
     "Finger twist tool",
     partial(_mel, 'brn_apply_finger_bend_tool("twist");')),
)


def _prefixed(root, table):
    return tuple((key, root + "." + category, label, note, action)
                 for key, category, label, note, action in table)


COMMANDS = _prefixed("SkeldarAnim", _OURS) + _prefixed("OverRig", _OVERRIG)

_INDEX = dict((command[0], command) for command in COMMANDS)
