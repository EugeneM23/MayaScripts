# Reads the Maya keyconfig back out of Blender, item by item.
#
#   & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background ^
#     --factory-startup --python docs/superpowers/plans/blender_keymap/verify_maya_keymap.py ^
#     -- "<path to the installed Maya.py>"
#
# --factory-startup so the run cannot touch the animator's own preferences.

import sys

import bpy


FAILED = []
PASSED = []


def gate(name, ok, got=""):
    (PASSED if ok else FAILED).append(name)
    print("%s %s%s" % ("ok  " if ok else "FAIL", name, ("" if ok else "  <- %s" % (got,))))


def items(kc, keymap):
    km = kc.keymaps.get(keymap)
    return list(km.keymap_items) if km else []


def found(kc, keymap, idname, type, props=(), **mods):
    """The one item on this key, or None. Modifiers are matched exactly."""
    for kmi in items(kc, keymap):
        if kmi.idname != idname or kmi.type != type:
            continue
        if (bool(kmi.ctrl), bool(kmi.alt), bool(kmi.shift)) != (
                bool(mods.get("ctrl")), bool(mods.get("alt")), bool(mods.get("shift"))):
            continue
        if (kmi.key_modifier != 'NONE') != bool(mods.get("key_modifier")):
            continue
        if mods.get("key_modifier") and kmi.key_modifier != mods["key_modifier"]:
            continue
        if all(getattr(kmi.properties, k, None) == v for k, v in props):
            return kmi
    return None


def on_key(kc, keymap, type, **mods):
    """Every item bound to this key, whatever the operator."""
    out = []
    for kmi in items(kc, keymap):
        if kmi.type != type:
            continue
        if (bool(kmi.ctrl), bool(kmi.alt), bool(kmi.shift)) != (
                bool(mods.get("ctrl")), bool(mods.get("alt")), bool(mods.get("shift"))):
            continue
        out.append(kmi.idname)
    return out


def main():
    path = sys.argv[sys.argv.index("--") + 1]
    print("loading %s" % path)
    bpy.ops.preferences.keyconfig_activate(filepath=path)

    wm = bpy.context.window_manager
    gate("the keyconfig is registered as Maya", "Maya" in wm.keyconfigs)
    kc = wm.keyconfigs.get("Maya")
    if kc is None:
        return finish()

    # --- the operators the delta leans on exist in this Blender ---------------
    for op in ("screen.keyframe_jump", "screen.frame_offset", "screen.frame_jump",
               "screen.animation_play", "anim.change_frame", "ed.undo", "ed.redo",
               "wm.context_set_enum", "object.posemode_toggle"):
        mod, name = op.split(".")
        gate("the operator %s exists" % op, hasattr(getattr(bpy.ops, mod), name))

    # --- time, in the global Frames keymap -----------------------------------
    gate(". steps to the next key",
         found(kc, "Frames", "screen.keyframe_jump", 'PERIOD', [("next", True)]) is not None,
         on_key(kc, "Frames", 'PERIOD'))
    gate(", steps to the previous key",
         found(kc, "Frames", "screen.keyframe_jump", 'COMMA', [("next", False)]) is not None,
         on_key(kc, "Frames", 'COMMA'))
    gate("Alt+. steps a frame forward",
         found(kc, "Frames", "screen.frame_offset", 'PERIOD', [("delta", 1)], alt=True) is not None)
    gate("Alt+, steps a frame back",
         found(kc, "Frames", "screen.frame_offset", 'COMMA', [("delta", -1)], alt=True) is not None)
    gate("Alt+V plays",
         found(kc, "Frames", "screen.animation_play", 'V', alt=True) is not None)
    gate("Alt+Shift+V goes to the start",
         found(kc, "Frames", "screen.frame_jump", 'V', [("end", False)], alt=True, shift=True) is not None)
    gate("the key stepping repeats while held",
         all(kmi.repeat for kmi in items(kc, "Frames")
             if kmi.idname in ("screen.keyframe_jump", "screen.frame_offset")))
    gate("Space still plays", found(kc, "Frames", "screen.animation_play", 'SPACE') is not None)

    # --- undo ----------------------------------------------------------------
    # Ours go into the global Window keymap; Blender's own Ctrl+Z is in Screen.
    gate("Z undoes", found(kc, "Window", "ed.undo", 'Z') is not None)
    gate("Shift+Z redoes", found(kc, "Window", "ed.redo", 'Z', shift=True) is not None)
    gate("Ctrl+Z still undoes", found(kc, "Screen", "ed.undo", 'Z', ctrl=True) is not None,
         on_key(kc, "Screen", 'Z', ctrl=True))
    gate("Shift+Ctrl+Z still redoes",
         found(kc, "Screen", "ed.redo", 'Z', ctrl=True, shift=True) is not None)
    # An editor's own keymap is read before the global one, so a plain Z left
    # anywhere else would shadow the undo in that editor.
    elsewhere = sorted(
        "%s -> %s" % (km.name, kmi.idname)
        for km in kc.keymaps for kmi in km.keymap_items
        if kmi.type == 'Z' and kmi.idname
        and not (kmi.ctrl or kmi.alt or kmi.shift or kmi.oskey)
        and km.name not in ("Window",)
    )
    gate("nothing else holds a plain Z", not elsewhere, elsewhere)

    # --- the viewport --------------------------------------------------------
    for key, value in (('FOUR', 'WIREFRAME'), ('FIVE', 'SOLID'),
                       ('SIX', 'MATERIAL'), ('SEVEN', 'RENDERED')):
        gate("%s sets the shading to %s" % (key, value),
             found(kc, "3D View", "wm.context_set_enum", key,
                   [("data_path", "space_data.shading.type"), ("value", value)]) is not None,
             on_key(kc, "3D View", key))
    gate("K and a drag scrub the time",
         found(kc, "3D View", "anim.change_frame", 'LEFTMOUSE', key_modifier='K') is not None)
    gate("F8 toggles pose mode",
         found(kc, "3D View", "object.posemode_toggle", 'F8') is not None)
    gate("Ctrl+Tab opens the mode pie",
         found(kc, "3D View", "wm.call_menu_pie", 'TAB',
               [("name", "VIEW3D_MT_object_mode_pie")], ctrl=True) is not None)

    # --- what the pies used to eat -------------------------------------------
    gate(". opens no pie in the viewport", not on_key(kc, "3D View", 'PERIOD'),
         on_key(kc, "3D View", 'PERIOD'))
    gate(", opens no pie in the viewport", not on_key(kc, "3D View", 'COMMA'),
         on_key(kc, "3D View", 'COMMA'))
    gate(". opens no pie in the image editor", not on_key(kc, "Image", 'PERIOD'),
         on_key(kc, "Image", 'PERIOD'))
    gate(". opens no pie in the clip editor", not on_key(kc, "Clip Editor", 'PERIOD'),
         on_key(kc, "Clip Editor", 'PERIOD'))
    gate("4 is no longer object mode", not on_key(kc, "Object Non-modal", 'FOUR'),
         on_key(kc, "Object Non-modal", 'FOUR'))
    gate("5 is no longer the mode pie", not on_key(kc, "Object Non-modal", 'FIVE'),
         on_key(kc, "Object Non-modal", 'FIVE'))

    # --- what Industry Compatible already gave, still given ------------------
    gate("Alt+LMB tumbles", found(kc, "3D View", "view3d.rotate", 'LEFTMOUSE', alt=True) is not None)
    gate("Alt+MMB pans", found(kc, "3D View", "view3d.move", 'MIDDLEMOUSE', alt=True) is not None)
    gate("Alt+RMB zooms", found(kc, "3D View", "view3d.zoom", 'RIGHTMOUSE', alt=True) is not None)
    gate("F frames the selection", found(kc, "3D View", "view3d.view_selected", 'F') is not None)
    gate("A frames everything", found(kc, "3D View", "view3d.view_all", 'A') is not None)
    # The tools live in the mode keymaps, not in "3D View".
    for keymap in ("Object Mode", "Pose"):
        for key, tool in (('Q', "builtin.select_box"), ('W', "builtin.move"),
                          ('E', "builtin.rotate"), ('R', "builtin.scale")):
            gate("%s picks the %s tool in %s" % (key, tool.split(".")[1], keymap),
                 found(kc, keymap, "wm.tool_set_by_id", key, [("name", tool)]) is not None,
                 on_key(kc, keymap, key))
    gate("S keys the pose",
         found(kc, "Pose", "anim.keyframe_insert_by_name", 'S', [("type", 'LocRotScale')]) is not None)
    for key, kind in (('W', 'Location'), ('E', 'Rotation'), ('R', 'Scaling')):
        gate("Shift+%s keys %s" % (key, kind.lower()),
             found(kc, "Pose", "anim.keyframe_insert_by_name", key, [("type", kind)], shift=True) is not None)
    gate("F frames the selection in the Graph Editor",
         found(kc, "Graph Editor", "graph.view_selected", 'F') is not None)
    gate("A frames everything in the Graph Editor",
         found(kc, "Graph Editor", "graph.view_all", 'A') is not None)
    gate("W moves keys in the Graph Editor",
         found(kc, "Graph Editor", "transform.translate", 'W') is not None)
    gate("G repeats the last action", found(kc, "Screen", "screen.repeat_last", 'G') is not None)

    # --- Industry Compatible itself is not touched ---------------------------
    import os
    shipped = os.path.join(
        bpy.utils.system_resource('SCRIPTS', path="presets/keyconfig"),
        "Industry_Compatible.py",
    )
    gate("the shipped Industry Compatible preset is where we read it from",
         os.path.isfile(shipped), shipped)
    if os.path.isfile(shipped):
        bpy.ops.preferences.keyconfig_activate(filepath=shipped)
    ic = wm.keyconfigs.get("Industry_Compatible")
    gate("Industry Compatible still has its pivot pie on .",
         "wm.call_menu_pie" in on_key(ic, "3D View", 'PERIOD') if ic else False)
    gate("Industry Compatible still has its zoom border on Z",
         "view3d.zoom_border" in on_key(ic, "3D View", 'Z') if ic else False)

    return finish()


def finish():
    print("\n%d of %d gates failed" % (len(FAILED), len(FAILED) + len(PASSED)))
    for name in FAILED:
        print("  FAILED: %s" % name)
    sys.stdout.flush()
    if FAILED:
        sys.exit(1)


main()
