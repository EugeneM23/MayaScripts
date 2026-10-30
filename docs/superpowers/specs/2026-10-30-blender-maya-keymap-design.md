# A Maya keymap for Blender — design (2026-10-30)

The animator asked for a Maya keyboard layout for Blender. Blender 5.2 was installed
on this machine the same day (`C:/Program Files/Blender Foundation/Blender 5.2`), its
user config empty. Asked what they would do in it, they answered **animation**, so the
design is weighted to the timeline, the Graph Editor and keying, not to modelling.

## What is already Maya, measured

Blender ships **Industry Compatible**, written from the Maya / Max / Modo conventions
(`<install>/5.2/scripts/presets/keyconfig/Industry_Compatible.py` over
`keymap_data/industry_compatible_data.py`). Read line by line, it already gives:

- navigation `Alt+LMB` tumble, `Alt+MMB` pan, `Alt+RMB` zoom (3D View, line 688-694);
- tools `Q W E R T` select / move / rotate / scale / transform (117-121, 634-638);
- `F` frame selected, `A` frame all — in the 3D View (695, 722) and in the Graph
  Editor and Dope Sheet (992-994, 1489);
- `S` key everything, `Shift+W / Shift+E / Shift+R` key location / rotation / scale,
  in Object Mode and in Pose Mode alike (2502-2508, 2575-2581);
- `G` repeat last (232), `P` parent (2473);
- `W / E / R` move / rotate / scale KEYS in the Graph Editor and Dope Sheet
  (997-1003, 1495-1505), middle-drag to move them (1499);
- arrows step a frame, `Ctrl`+arrows jump to the ends (95-101);
- `Ctrl+Z` undo, `Shift+Ctrl+Z` redo (254-255).

So the work is a **delta**, not a keymap.

## What is missing or in the way

| | Maya | Industry Compatible |
|---|---|---|
| next / previous KEY | `.` / `,` | nothing — `screen.keyframe_jump` is bound nowhere |
| play / stop | `Alt+V` | `Space` only |
| go to the start | `Alt+Shift+V` | nothing (`Ctrl+Left` is there) |
| scrub in the viewport | hold `K` + drag | nothing — `anim.change_frame` is bound nowhere |
| undo | `Z` | `Z` is `zoom_border` (783 in the 3D View, 362 in View2D) |
| wireframe / shaded / textured | `4 / 5 / 6` | `4` object mode, `5` mode pie (3506-3507), `6` free |
| object ↔ component | `F8` | nothing (`1 / 2 / 3` enter edit mode by submode) |

`.` and `,` are taken by the pivot and orientation pies in the 3D View (791-792), the
Image editor (1097) and the Clip editor (2188). A space keymap is read before a global
one, so those three items have to go or they eat the new global binding.

## The approach

**A keyconfig preset of our own, built on the shipped Industry Compatible data.**

One file, `Maya.py`, in the user's preset folder
(`%APPDATA%\Blender Foundation\Blender\5.2\scripts\presets\keyconfig\`). It finds the
shipped data module through `bpy.utils.system_resource('SCRIPTS', ...)`, generates the
Industry Compatible keymap data, patches it, and registers a keyconfig named **Maya**.
It then stands in Preferences → Keymap beside Blender, Blender 27x and Industry
Compatible, and is chosen with one click.

Why this and not the other two roads:

- *editing `industry_compatible_data.py` in place* — a Blender update replaces it and
  there is nothing to fall back to;
- *an addon* — needed only to change things that are not keys (auto-key, playback sync,
  select-through). Not asked for; a preset is a dropdown entry with no state.

The master copy lives in `docs/superpowers/plans/blender_keymap/Maya.py` — a Blender
update to another version series empties its own preset folder, and the repo is where
this workshop keeps what it has to re-copy. It is not in the plugin's payload and
`make_build.py` never sees it.

## The delta, exactly

Added to the global **Frames** keymap, so it reads the same in the viewport, the
timeline, the Graph Editor and the Dope Sheet:

| key | operator |
|---|---|
| `.` | `screen.keyframe_jump` next=True, repeat |
| `,` | `screen.keyframe_jump` next=False, repeat |
| `Alt+.` | `screen.frame_offset` +1, repeat |
| `Alt+,` | `screen.frame_offset` -1, repeat |
| `Alt+V` | `screen.animation_play` |
| `Alt+Shift+V` | `screen.frame_jump` end=False |

Added to **Window**: `Z` → `ed.undo`, `Shift+Z` → `ed.redo` (both repeatable).
Blender's own `Ctrl+Z` is in the **Screen** keymap, so the two do not meet. A text
field consumes its own keys through the UI handler before any keymap, so typing a name
still types a `z` — the animator's own check, and the fallback is to bind `Z` per
editor instead.

`Window` is the last keymap Blender reads, so any editor binding a plain `Z` would
shadow the undo there. Measured: after the removals below, exactly one is left —
`image.view_zoom_border` in the Image editor — and it goes too. The probe gates that
nothing else holds a plain `Z`.

Added to **3D View**:

| key | operator |
|---|---|
| `4` | `wm.context_set_enum` `space_data.shading.type` = WIREFRAME |
| `5` | = SOLID |
| `6` | = MATERIAL |
| `7` | = RENDERED |
| `K` + LMB drag | `anim.change_frame`, `key_modifier` K — Maya's virtual time slider |

`F8` → `object.posemode_toggle` (a rig animator's object ↔ component) and the mode pie
`5` used to carry, moved to `Ctrl+Tab` — Blender's own key for it — go into **3D View**
as well, not into a mode's keymap: `Object Non-modal` is read in object mode only, and
F8 has to read the same from inside pose mode to get back out. The cost of `Ctrl+Tab`
is `screen.space_context_cycle`, which keeps working outside the viewport.

Removed: the pivot pie on `.` and the orientation pie on `,` (3D View, Image, Clip),
`view3d.zoom_border`, `view2d.zoom_border` and `image.view_zoom_border` on `Z`,
`object.mode_set` OBJECT on `4` and the mode pie on `5`.

Note for a later reader: `Q W E R` are not in the `3D View` keymap but in each mode's
own (`Object Mode`, `Pose`, `Mesh`, `Armature`, …), and `Ctrl+Z` is in `Screen`. Both
cost a probe run to find.

`outliner.show_active` on `.` (544) is **left alone**: it only fires with the mouse over
the Outliner, where nobody steps keys.

## What is not built, and why

- **The hotbox and marking menus** (`Space`, held `W / E / R`). Blender has pie menus,
  which are not marking menus and carry none of Maya's items. A hotbox would be a tool,
  not a keymap.
- **Shift-drag on the timeline** for a time range that then moves and scales keys.
  Blender has no such selection; its preview range is another thing.
- **`Ctrl+A` Attribute Editor** — no equivalent.
- Component masks `F9 / F10 / F11`. They matter for modelling, and the answer was
  animation; `1 / 2 / 3` already enter edit mode by submode.

## How it is verified

`docs/superpowers/plans/blender_keymap/verify_maya_keymap.py`, run as
`blender --background --factory-startup --python <it> -- <installed Maya.py>`
(`--factory-startup` so a run cannot touch the animator's own preferences): it loads
the preset, then reads every item of the delta back out of
`window_manager.keyconfigs["Maya"]` — each added key resolving to its operator with its
properties, each removed key gone, every Maya-ism Industry Compatible already gave still
given, and Industry Compatible itself unchanged beside it. **0 of 60 gates failed,
2026-10-30**, on Blender 5.2.3 LTS.

Blender also really lists it: `bpy.utils.preset_paths("keyconfig")` answers the user's
own folder beside the install's, with `Maya.py` in it, so it stands in the Keymap
dropdown. And a GUI session (`--factory-startup`, activate, report, quit) comes up with
`active keyconfig = 'Maya'`, 280 keymaps and the `K`+LMB scrub item in place, with no
error or warning.

**Left to the animator**, since no API presses a key or drags a mouse in Blender: that
`K`+drag really scrubs, and that `Z` in a text field still types a `z`.
