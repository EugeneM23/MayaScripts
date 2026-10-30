# Maya keymap for Blender.
#
# Blender's own "Industry Compatible" keymap is already written from the Maya
# conventions - Alt+LMB/MMB/RMB navigation, Q W E R tools, F and A framing, S to
# key, Shift+W/E/R to key translate/rotate/scale, W/E/R on keys in the Graph
# Editor. This preset is that keymap plus the Maya reflexes it does not carry,
# for an animator: stepping over keys, Alt+V playback, K to scrub, Z to undo and
# 4/5/6/7 for the viewport's shading.
#
# Design: docs/superpowers/specs/2026-10-30-blender-maya-keymap-design.md
# Master copy: docs/superpowers/plans/blender_keymap/Maya.py in the MayaScripts
# repository. Install by copying this file into
#   %APPDATA%\Blender Foundation\Blender\<version>\scripts\presets\keyconfig\
# then pick "Maya" in Preferences > Keymap.

import os

import bpy


DIRNAME, FILENAME = os.path.split(__file__)
IDNAME = os.path.splitext(FILENAME)[0]

# The shipped Industry Compatible data, found in the running Blender's own
# scripts folder - never beside this file, which lives in the user's presets.
_KEYMAP_DATA = os.path.join(
    bpy.utils.system_resource('SCRIPTS', path="presets/keyconfig/keymap_data"),
    "industry_compatible_data.py",
)

industry_compatible = bpy.utils.execfile(_KEYMAP_DATA)


# ------------------------------------------------------------------------------
# Reading and editing the keymap data
#
# The data is a list of (name, space, {"items": [(idname, kmi_args, kmi_data)]}).

def _items(data, name):
    for km_name, _km_space, km_data in data:
        if km_name == name:
            return km_data["items"]
    raise KeyError("no keymap named %r in the Industry Compatible data" % name)


def _is_key(kmi_args, type, **mods):
    """True when this item's key is exactly `type` with exactly `mods` held."""
    if kmi_args.get("type") != type:
        return False
    for mod in ("ctrl", "alt", "shift", "oskey", "key_modifier"):
        if bool(kmi_args.get(mod)) != bool(mods.get(mod)):
            return False
    return True


def _drop(data, keymap, idname, type, **mods):
    """Take `idname` on this key out of `keymap`. Answers how many were dropped."""
    items = _items(data, keymap)
    kept = [it for it in items if not (it[0] == idname and _is_key(it[1], type, **mods))]
    dropped = len(items) - len(kept)
    if not dropped:
        # Loud, and the keymap still loads: a Blender update that renames an
        # operator must not leave a key quietly doing the old thing.
        print("[%s keymap] could not drop %s on %s from %r - the key keeps its "
              "Industry Compatible meaning" % (IDNAME, idname, type, keymap))
    items[:] = kept
    return dropped


def _shading(key, value):
    return ("wm.context_set_enum", {"type": key, "value": 'PRESS'},
            {"properties": [("data_path", "space_data.shading.type"), ("value", value)]})


def patch(data):
    # --- out of the way -------------------------------------------------------
    # `.` and `,` carry the pivot and orientation pies; a space keymap is read
    # before the global one the key stepping goes into, so these must go.
    _drop(data, "3D View", "wm.call_menu_pie", 'PERIOD')
    _drop(data, "3D View", "wm.call_menu_pie", 'COMMA')
    _drop(data, "Image", "wm.call_menu_pie", 'PERIOD')
    _drop(data, "Clip Editor", "wm.call_menu_pie", 'PERIOD')
    # Z is undo in Maya, a zoom border in Blender.
    _drop(data, "3D View", "view3d.zoom_border", 'Z')
    _drop(data, "View2D", "view2d.zoom_border", 'Z')
    _drop(data, "Image", "image.view_zoom_border", 'Z')
    # 4 and 5 are the viewport's shading in Maya, object mode and the mode pie
    # in Blender. The pie comes back on Ctrl+Tab, Blender's own key for it.
    _drop(data, "Object Non-modal", "object.mode_set", 'FOUR')
    _drop(data, "Object Non-modal", "wm.call_menu_pie", 'FIVE')

    # --- time -----------------------------------------------------------------
    # The global Frames keymap, so these read the same in the viewport, on the
    # timeline, in the Graph Editor and in the Dope Sheet.
    _items(data, "Frames").extend([
        ("screen.keyframe_jump", {"type": 'PERIOD', "value": 'PRESS', "repeat": True},
         {"properties": [("next", True)]}),
        ("screen.keyframe_jump", {"type": 'COMMA', "value": 'PRESS', "repeat": True},
         {"properties": [("next", False)]}),
        ("screen.frame_offset", {"type": 'PERIOD', "value": 'PRESS', "alt": True, "repeat": True},
         {"properties": [("delta", 1)]}),
        ("screen.frame_offset", {"type": 'COMMA', "value": 'PRESS', "alt": True, "repeat": True},
         {"properties": [("delta", -1)]}),
        ("screen.animation_play", {"type": 'V', "value": 'PRESS', "alt": True}, None),
        ("screen.frame_jump", {"type": 'V', "value": 'PRESS', "shift": True, "alt": True},
         {"properties": [("end", False)]}),
    ])

    # --- undo -----------------------------------------------------------------
    # Ctrl+Z and Shift+Ctrl+Z stay where they are. A text field consumes its own
    # keys through the UI handler before any keymap, so typing still types a z.
    _items(data, "Window").extend([
        ("ed.undo", {"type": 'Z', "value": 'PRESS', "repeat": True}, None),
        ("ed.redo", {"type": 'Z', "value": 'PRESS', "shift": True, "repeat": True}, None),
    ])

    # --- the viewport ---------------------------------------------------------
    # The 3D View keymap, not a mode's, so every one of these reads the same in
    # Object Mode and in Pose Mode.
    view3d = _items(data, "3D View")
    # Maya's virtual time slider: hold K and drag. Blender matches an item's key
    # modifier exactly, so the plain LMB items below cannot take this event.
    view3d.insert(0, ("anim.change_frame",
                      {"type": 'LEFTMOUSE', "value": 'PRESS', "key_modifier": 'K'}, None))
    view3d.extend([
        _shading('FOUR', 'WIREFRAME'),
        _shading('FIVE', 'SOLID'),
        _shading('SIX', 'MATERIAL'),
        _shading('SEVEN', 'RENDERED'),
        # Maya's object <-> component, for a rig.
        ("object.posemode_toggle", {"type": 'F8', "value": 'PRESS'}, None),
        # The mode pie 5 used to carry.
        ("wm.call_menu_pie", {"type": 'TAB', "value": 'PRESS', "ctrl": True},
         {"properties": [("name", "VIEW3D_MT_object_mode_pie")]}),
    ])

    return data


# ------------------------------------------------------------------------------
# Keymap

def load():
    from sys import platform
    from bl_keymap_utils.io import keyconfig_init_from_data

    prefs = bpy.context.preferences

    kc = bpy.context.window_manager.keyconfigs.new(IDNAME)
    params = industry_compatible.Params(
        use_mouse_emulate_3_button=prefs.inputs.use_mouse_emulate_3_button,
    )
    keyconfig_data = patch(industry_compatible.generate_keymaps(params))

    if platform == "darwin":
        from bl_keymap_utils.platform_helpers import keyconfig_data_oskey_from_ctrl_for_macos
        keyconfig_data = keyconfig_data_oskey_from_ctrl_for_macos(keyconfig_data)

    keyconfig_init_from_data(kc, keyconfig_data)


if __name__ == "__main__":
    load()
