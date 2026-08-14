# OverRig Picker — Design

Date: 2026-08-14
Status: approved
Branch: `feature/overrig-picker`

## Context

OverRig (Pavel Barnev, v10.2, `base_OverRig_scripts.mel`) is a MEL toolset that builds
helper objects — "knots", aim setups, IK, ribbons — on top of an existing rig and bakes
animation between them. It is not a rig builder. It exposes ~394 global MEL procs, all
driven by the current selection, and tracks what it created in two object sets:
`OverRig_rig_objects` (source joints) and `OverRig_knots` (created helpers).

We are building a Python wrapper around it so a character rig can be created and removed
conveniently. This spec covers the **first component only: the picker UI**.

Target skeleton is `SKM_Manny_Simple` in `Manny_Sckeleton.ma` — a stock UE5 Manny
skeleton, 93 joints, standard naming (`root`, `pelvis`, `spine_01..05`, `clavicle_*`,
`upperarm_*`, `thigh_*`, full fingers with metacarpals, plus UE export helpers
`ik_foot_root`, `ik_hand_gun`, and specials `interaction`, `center_of_mass`,
`camera_root`).

Reference for look and feel: the AdvancedSkeleton Control Panel — an anatomically
arranged grid of colour-coded buttons with a menu bar and group-select buttons.

## Goal

A picker panel that is pleasant to use and good-looking, showing the character as a
front-view body map, where clicking a region selects the corresponding object in the
scene.

## Scope

**In this iteration**

- Anatomical body map, 64 buttons (animator-facing joint set)
- Group buttons (Main, All, Spine, per-limb, per-hand)
- Click to select; `shift` adds; `ctrl` toggles
- Marquee (rubber-band) drag selection across many buttons
- Zoom and pan with the mouse wheel
- Hover highlight plus a status line showing the joint name
- Scene → picker sync: changing selection in Maya highlights the matching buttons
- Joints absent from the scene render dimmed and non-interactive

**Explicitly not in this iteration**

- `Build` and `Bake+Delete` sit in the toolbar as disabled stubs
- No reading of OverRig state (`OverRig_knots` / `OverRig_rig_objects`); those sets do
  not exist yet in the scene, so status colouring could not be verified against anything
- No mirror-select, no chain-select, no character switcher
- No docking (see Decisions)

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Click behaviour | Smart selection: pick the OverRig knot if one exists on that part, otherwise the joint. Button colour reflects rig state. | Picker stays useful both before and after the rig is built. **This iteration implements the joint half only** — knot lookup and status colouring arrive with the OverRig-state work, since no knots exist in the scene yet. |
| Button density | Animator-facing set, 64 buttons. Excludes twist joints, UE `ik_*` helpers, `weapon_*`, `interaction`, `center_of_mass`, `camera_*`. | Twists are driven, not animated. The `ik_*` joints are export helpers already sitting on parentConstraints (`ik_foot_l/r ← foot_l/r`, `ik_hand_l ← hand_l`, `ik_hand_gun ← hand_r`). Buttons for them would be noise. |
| Toolkit | PySide6 + `QGraphicsView` | Maya 2027 ships PySide6 6.8.3 / Qt 6.8.3. `QGraphicsView` gives marquee selection, zoom/pan, hit-testing and antialiased drawing essentially for free. Marquee selection is the decisive factor — it is the biggest ergonomic win in a picker and is unreachable in native `cmds` UI. |
| Layout source | Hand-authored coordinate table keyed to UE5 names, plus a name-resolution layer tolerating namespaces and prefixes | Produces the clean anatomical look. Auto-projecting joint world positions adapts to any skeleton but looks messy, especially in the hands. |
| Window | Floating, parented to the Maya main window | `workspaceControl` with restore-across-restart needs `uiScript` and module-path care, which is its own bug source. The view/shell split keeps wrapping it in a dock a small later change. |
| Palette | Standard rigging convention: left blue, right red, centre neutral | Matches what animators already have in muscle memory and what AS itself signals. |

**Deviation from repo convention, accepted deliberately:** every existing script in this
repo is a single flat `maya_*.py` file using pure `maya.cmds`, with no Qt anywhere. The
picker introduces both a package and Qt. The wrapper will grow — rig build and teardown
logic is still to come — and a picker is precisely the widget where `cmds` UI hits its
ceiling.

## Architecture

Package `maya_overrig/` at the repo root. The `maya_` prefix follows repo convention;
the package form is the deviation noted above.

| Module | Responsibility | May import |
|---|---|---|
| `bodymap.py` | Pure data: the button table and region definitions | nothing |
| `naming.py` | Resolve a logical joint name to a scene object | `maya.cmds` |
| `picker_view.py` | Qt scene, button items, painting, hover, marquee, zoom | Qt only |
| `picker_window.py` | Window shell, toolbar, wiring signals to Maya selection | Qt + `maya.cmds` |
| `__init__.py` | `show_picker()` entry point | the above |

**The dependency rule is the point of this split:** `picker_view.py` must not import
`maya.cmds`. It deals in geometry, drawing and button ids, and emits signals outward.
Everything that touches the scene lives in `picker_window.py`. This makes the view
openable and inspectable without a scene, and lets tests substitute the scene layer.

`bodymap.py` importing nothing means the layout is testable in plain Python, outside Maya.

## Data model

```python
Button = namedtuple("Button", "id joint x y w h region")
```

- `id` — stable unique key used in signals
- `joint` — logical UE5 joint name, resolved at runtime
- `x y w h` — position in body-space
- `region` — one of `root`, `spine`, `head`, `arm_l`, `arm_r`, `hand_l`, `hand_r`,
  `leg_l`, `leg_r`

`region` derives the group buttons, so groups are not a second hand-maintained list that
can drift out of sync with the map. Regions are deliberately finer-grained than the
palette: colour comes from a separate `region → colour family` mapping, where `root`,
`spine` and `head` all resolve to the neutral centre family. Without that split there
would be no way to derive a `Spine` group button distinct from root, neck and head.

Two group buttons are special-cased rather than derived: `All` selects every enabled
button, and `Main` selects the primary body controls only — `root`, `pelvis`, the spine
stack, and the limb roots — skipping fingers.

Body-space is a fixed coordinate system roughly 400 × 620 units, front view, character
centred on `x = 200`. The view uses `fitInView` on resize, so the panel scales cleanly at
any window size. Vertical band order, top to bottom: head and neck; clavicles and the
spine stack; arms outward from the spine with the finger blocks outboard; pelvis and
root; legs; feet at the bottom. Exact coordinates are authored in `bodymap.py` and tuned
visually against screenshots.

No labels on the 64 body buttons — at that size text is noise. The joint name appears in
the bottom status line on hover, and as a tooltip. Only group buttons carry text, as in
AS.

## Interaction

| Input | Result |
|---|---|
| Click | Replace selection |
| `shift` + click | Add to selection |
| `ctrl` + click | Toggle |
| Drag on empty space | Marquee: replace selection with every intersecting button |
| `shift` + drag | Marquee that adds to the current selection instead of replacing |
| Wheel | Zoom |
| Middle-drag | Pan |
| Hover | Outline highlight + joint name in status line |

## Scene integration

```
click / marquee ──► view.selection_requested(ids, modifier)
                          │
                          ▼
        window: ids ──naming.resolve──► DAG paths ──► cmds.select
                          
SelectionChanged (scriptJob) ──► window: cmds.ls(sl=True) ──► reverse map
                                          │
                                          ▼
                                  view.set_selected(ids)
```

**Feedback loop.** We change the selection, Maya fires `SelectionChanged`, we repaint,
which risks looping. A reentrancy guard flag is held for the duration of our own
selection change and the callback returns early while it is set. This is the one piece of
non-obvious control flow in the component and must be built in from the start, not
patched on later.

**scriptJob lifecycle.** The `SelectionChanged` job is registered when the window opens
and killed in `closeEvent`. Left alive, it keeps firing into a dead widget and spams
errors — the classic Qt-in-Maya leak.

## Visual design

Dark ground matching Maya. Region tints follow rigging convention.

| Element | Colour |
|---|---|
| Background | `#2b2b2b` |
| Centre (root, pelvis, spine, neck, head) | `#8a8378` warm grey |
| Left limbs | `#4a7ea8` blue |
| Right limbs | `#a85a4a` red |
| Left fingers | `#3f6885` desaturated blue |
| Right fingers | `#8a4c40` desaturated red |
| Group buttons | `#3c3c3c`, text `#d8d8d8` |
| Disabled (joint missing) | fill `#3a3a3a`, outline `#4a4a4a` |
| Hover | 1 px outline `#cfcfcf` |
| Selected | fill lightened ~18%, 2 px outline `#ffb648` amber |

Buttons are rounded rectangles with a subtle vertical gradient.

Button items take a `state` enum from the start, with only `NEUTRAL` and `SELECTED`
implemented. Adding `HAS_KNOT`, `IN_IK` and `BAKED` later then touches colour lookup
only, not layout or hit-testing.

## Error handling

| Situation | Behaviour |
|---|---|
| Joint not in scene | Button dimmed and non-interactive. No exception — the panel stays useful on a partial skeleton. |
| No skeleton at all | Panel opens, every button dimmed, status line explains why. |
| Several matches (two characters) | Take the first, log a warning. Character switcher is future work. |
| `show_picker()` called again | Existing window is destroyed first, so windows do not accumulate. |
| Window closed | `scriptJob` killed in `closeEvent`. |

## Testing

- `bodymap.py` — plain Python, no Maya: ids unique, rectangles do not overlap, exactly 64
  body buttons, every `joint` a valid UE5 name, every `region` known.
- `naming.py` — resolution against a substituted `cmds`, covering bare names, namespaced
  names, prefixed names, missing names and ambiguous matches.
- View and final look — verified live through the Maya command-port bridge: open the panel
  in the real scene, screenshot it, iterate on the layout.
- Integration smoke test through the bridge: drive a button programmatically and assert
  `cmds.ls(sl=True)` holds the expected joint; confirm the `scriptJob` is gone after the
  window closes.

## Usage

```python
import sys
sys.path.append(r"C:/!!!Work/MayaScripts")
import maya_overrig
maya_overrig.show_picker()
```

`show_picker()` does no module-reload magic; the development bridge reloads submodules
explicitly when iterating.

## Future work

Ordered roughly by expected sequence, not committed to here:

1. Read OverRig state from `OverRig_knots` / `OverRig_rig_objects`; colour buttons by it.
2. Wire `Build` — map body parts to OverRig procs (IK legs via
   `apply_rebike_3_or_more_object_to_IK`, spline spine via `apply_objects_spline_IK`,
   knots via `apply_parentConstrAnim`), selecting in the right order since every proc
   reads `ls -sl` and IK needs its three joints ordered.
3. Wire teardown. OverRig's own `barn_fast_bake_source_obj_and_delete_knots()` is
   scene-global and all-or-nothing, always bakes, and `apply_Fast_Bake` consumes
   `OverRig_rig_objects` as it goes — so partial, per-part teardown needs our own
   manifest rather than OverRig's sets.
4. Optional dockable `workspaceControl` wrapper.
5. Mirror-select and chain-select.
6. Character switcher for namespaced or multiple characters.

## Note on scene hygiene

The working scene carries roughly 260 orphaned AdvancedSkeleton utility nodes in `AllSet`
(IK stretch, pole lock, FKIK blend, volume, SDK finger scale, unit conversions) plus 8
`antiPop`/`normal` anim curves and 9 `as*` shading groups, left behind after an AS rig's
controls were deleted — there are zero NURBS curves in the scene. Harmless to the picker,
but it will blur the line between "ours" and "foreign" once teardown is implemented.
Cleaning it should be a separate explicit action, never folded into rig teardown.
