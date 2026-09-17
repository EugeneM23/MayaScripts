# SkeldarAnim Hub: one dockable window, every tool a collapsible section

**Date:** 2026-09-17
**Ask:** «Давай наши скрипты объединим в одно окошко которое можно будет
куда-то прикрепить или открепить! А каждый раздел будет представлять собой
вкладку с возможностью закрыть и раскрыть».
**Decisions taken in the brainstorm:** an accordion (sections stacked in one
scrollable column, each collapsible, several open at once), not a
`tabLayout`; the six shelf tools become six sections; the shelf keeps its
six buttons and gains a seventh that opens the hub — every old button now
opens the hub and expands its own section.

## What the animator sees

One `workspaceControl` named **SkeldarAnim**. Maya's workspace controls
already do everything the ask names: dock to any edge or into any existing
dock as a tab, tear off into a floating window, remember their place and
size across sessions, and come back at startup when they were docked.

Inside: a scrollable column of `frameLayout` sections in shelf order —
**UE Bridge, Scene Setup, Retarget, Hotkeys, Studio, Colour** — each with
the collapse triangle Maya draws on every frameLayout. Which sections are
collapsed is remembered per section in an optionVar, so the panel opens
the way it was left. Pressing a shelf button (or its hotkey row) opens the
hub if it is closed, expands that tool's section, leaves the others as they
are, and scrolls the section into view.

Four sections hold exactly what their windows held (UE Bridge, Scene Setup,
Studio, Colour). Two are new, small, and wrap the two shelf actions that
had no window:

- **Retarget** — one line of instruction, one large `Retarget` button, a
  status line. The button runs the same `retarget_button()` the shelf runs;
  the result lands in the status line as well as in the viewport message.
- **Hotkeys** — a toggle button that reads `Hotkey map: ON` / `OFF`, lit in
  `ON_COLOUR` while the map is on (the shelf button keeps its paint, both
  are repainted by the one `paint()`), and a `Hotkey Editor...` button
  opening Maya's own editor.

The flagged-off tools (Rig Picker on Qt, the OverRig MEL panel, Overshoot)
are not sections. They are not on the shelf, and the first two do not fit
an accordion. Overshoot can become a section later by growing a
`build_panel()` like the others; not done now.

## Architecture

### `maya_hub.py` (SkeldarAnim, `cmds` only)

```
CONTROL = "skeldarAnimHub"          # the workspaceControl
SECTIONS = (Section(key, label, module, builder, frame), ...)  # shelf order
show(section=None)                  # the shelf button and every show_window
build()                             # the uiScript body: the accordion
uiscript(root)                      # pure: the Python the control replays
collapsed(key) / remember(key, on)  # optionVar skeldarAnimHub_<key>
expand(key)                         # frameLayout -e -collapse False + remember + scroll
scroll_offset(heights, index, spacing)  # pure: pixels above section `index`
```

`show()` deletes the four legacy standalone windows if an older build left
one open, then: the control exists → `workspaceControl -e -restore` (raises
a hidden or tabbed one); else create it with `uiScript=uiscript(root)`,
`retain=False`, floating, `initialWidth`/`initialHeight`. Maya runs the
uiScript at creation and again at startup for a docked control, and at
startup nothing of ours is on `sys.path` — so the uiScript carries the
bootstrap with the plugin folder baked in, read from `__file__` (the
hotkey runTimeCommands' pattern).

`build()` sets the parent to the control, makes `scrollLayout
-childResizable` → `columnLayout -adjustableColumn` → per section a
`frameLayout(frame, label, collapsable=True, collapse=collapsed(key),
collapseCommand/expandCommand → remember)` → `columnLayout
-adjustableColumn` → `module.builder()` → `setParent("..")` twice. The
builder module is imported lazily inside `build()`, so `maya_hub` imports
none of the tools at module level and the tools import `maya_hub` lazily in
`show_window()`: no cycle.

`expand(key)` edits the frame, remembers `False`, and scrolls the section
into view through `evalDeferred` (the heights are real only after Maya lays
the column out): `scrollByPixel("up", big)` then `("down", scroll_offset(
heights_of_frames_above, index, spacing))`. Best effort, guarded — a
missing control skips it.

### Each tool gains `build_panel()`, and `show_window()` opens the hub

| Module | Was | Becomes |
|---|---|---|
| `maya_uebridge/window.py` | `show_window()` builds `cmds.window` + `formLayout` | `build_panel()` builds the same formLayout at a fixed `PANEL_HEIGHT` into the current parent and does the cache fill; `show_window()` → `maya_hub.show("uebridge")` |
| `maya_scenesetup/window.py` | window + columnLayout | `build_panel()` = the column, `refresh` and the swatch fill; `show_window()` → hub |
| `maya_vpstudio.py` | window, `forget_saved_size`, `fit_window` | `build_panel()` = the column and the late `changeCommand` wiring; no fit (the hub scrolls); `show_window()` → hub |
| `maya_colour.py` | same as Studio | same as Studio |
| `maya_rig_retarget.py` | shelf function only | `build_panel()` new; `retarget_button()` also writes the panel status when it exists |
| `maya_hotkeys.py` | shelf toggle, `paint()` paints the shelf button | `build_panel()` new; `paint()` also repaints the panel button; a `window.hub` row |

The control NAMES inside every panel are unchanged, so every callback,
`refresh`, hotkey row and unit test that reads `_STATUS`, `_LIST`,
`_control("look")` and the rest keeps working. `WINDOW` constants go: a
control has one name per Maya session, so a tool cannot live both in the
hub and in a window of its own, and "is the panel open" is now
`is_open()` — `cmds.control(<status control>, exists=True)` — in each
module. `maya_hotkeys._scene` asks that instead of `cmds.window(WINDOW)`.
Studio's `window_options()` and `refresh()` do the same.

`maya_winfit` is no longer called by Studio or Colour (the hub is
scrollable and the sections take their natural height). It stays in the
payload with its tests: Overshoot still opens a fixed-height window of its
own, and the module is the fix for the day that panel is measured.

### Shelf and installer

`_PYTHON_BUTTONS` gains a first row `("SkeldarAnim", ..., "maya_hub",
"show", "hub.png", "")`. The six other rows are unchanged in text — their
`show_window` / `retarget_button` / `toggle` now reach the hub through the
modules. `maya_hub.py` and `icons/hub.png` join the payload;
`icons/make_icons.py` gains `draw_hub` (a plate with a docked-panel glyph).
`purge_modules` derives its names from the payload and so drops `maya_hub`
on an update for free.

### Hotkeys

One new row `window.hub` → `maya_hub.show`. The existing `window.*` rows
open the hub on their section by way of the modules. `_scene` opens the
hub when Scene Setup is not built and says so, as before.

## Error handling

Every section builder runs inside the hub's own `try/except` in `build()`:
a tool whose import fails (a Maya without PySide6 does not matter here — all
six are `cmds`-only — but a broken install might) gets a section holding
the error text instead of taking the whole panel down. Each panel keeps its
own `_run`, which puts failures on that section's status line.

## Testing

- `tests/test_hub.py` on `FakeUiCmds`: sections in shelf order with the
  right module/builder names; `uiscript(root)` carries the bootstrap, the
  import and the `build()` call and no backslash; `build()` makes one
  collapsable frameLayout per section, collapsed as the optionVar says, and
  calls each builder inside its frame; a builder that raises leaves a text
  and the other sections built; `show()` restores an existing control and
  creates a missing one with the uiScript; `expand()` un-collapses,
  remembers, and `scroll_offset` is exact (pure).
- The Studio and Colour window-fit test classes are replaced by
  `build_panel` tests: the controls land in the caller's column, no
  `cmds.window` is created, `show_window` delegates to `maya_hub.show`
  with the tool's key, the late `changeCommand` wiring still happens last.
- Scene Setup and UE Bridge: `build_panel` creates the named controls and
  `show_window` delegates.
- Retarget and Hotkeys: the panel's button calls the shelf function; the
  status control receives the first line; `paint()` paints the panel button
  when it exists and never fails without it; `is_open()`.
- Installer: seven buttons, `SkeldarAnim` first, every icon exists,
  `maya_hub.py` in the payload.
- `FakeUiCmds` grows `workspaceControl`, `scrollLayout`, `frameLayout`,
  `setParent`, `evalDeferred` and `control -exists` bookkeeping.
- Live: `docs/superpowers/plans/verify_hub.py` over the command port —
  the control exists after `show()`, six frames, every panel's status
  control exists, `show("colour")` expands the Colour frame, collapsing
  a frame writes the optionVar, a widget grab saved to disk and looked at.

## Not built

Overshoot as a section; a tabbed alternative; per-section pop-out into its
own window; scrolling with animation; a hub-level status line (each section
keeps its own).

## Addendum — what the live run changed (2026-09-17, evening)

Built, unit-tested (2125 green), installed into the animator's Maya over
the port and photographed. `verify_hub.py` **0 of 18 gates failed**. Four
things the picture changed, none of which a test on a fake `cmds` could
have seen:

1. **A `formLayout` inside the hub's column reports a 1128 px minimum
   width** whatever its children are told (the list at `width=100` changed
   nothing), so the whole column grew a horizontal scrollbar and the UE
   Bridge's buttons stood off the right edge. The main text's "the same
   formLayout at a fixed height" is withdrawn: the bridge section is rows
   in a column (`rowLayout`s, the list at `LIST_HEIGHT`), the same controls
   under the same names. The three mode radios stand in a column
   (`vertical=True`) — in a row they want 670 px at 150 %.
2. **Long status lines widen the column too** (Scene Setup's refusal text
   asked for 657 px), so the status texts are `wordWrap=True` — and **a
   wrapped label inside a `columnLayout` keeps the one-line height it was
   given and clips the second line**, so they carry an explicit two-line
   `height=36`; the Retarget and Hotkeys notes likewise (70 / 54).
3. Scene Setup's default group widths (`floatFieldGrp` 588 px,
   `textFieldGrp` 580, `colorSliderGrp` rows 544) are narrowed with explicit
   `columnWidth`s. Measured after: the column's minimum is **331 logical**
   against the hub's initial 500; the widest section is now the bridge at
   495 px.
4. **`workspaceControl -q -uiScript` answers None**: Maya stores the script
   and will not show it, so the verify proves the script `show()` hands
   over rather than what Maya kept. And **a `widget.grab()` in the same
   send as the collapse that changed the layout photographs the OLD
   layout** — a collapsed frame still drawn at full height, an empty grey
   block. The heights are real in the next send (30 px per collapsed
   header); a picture of a state must come from a later send than the
   state change.

The scroll-into-view was measured: asked for Colour at the bottom, the
column landed at 2452 of an expected 2831 — the scroll's maximum, with the
Colour section fully in view.

## Addendum 2 — Scene Setup becomes Characters and Weapons (2026-09-17, later)

The animator's next ask: «декомпозируем scenesetup на characters и
weapons», and, offered a UI-only split against splitting the module too,
«как ты предлагаешь». So `SECTIONS` holds seven rows — UE Bridge,
**Characters**, **Weapons**, Retarget, Hotkeys, Studio, Colour — with the
two new ones built by `maya_scenesetup.window.build_characters_panel` and
`build_weapons_panel`. The module stays one: the two halves share
`refresh` (which writes the Characters header AND the weapon fields), the
character resolution and the colour scan, and a split of the code would
have moved those into a third place for no gain.

- **Characters**: the «Character: …» header, the skeleton/rig dropdown,
  its colour swatch + Recolour, Add Character, and its own status line
  `mayaSceneSetupCharacterStatus`. Post-build: the remembered dropdown
  row, the header (`_bound_root`), the swatch.
- **Weapons**: the weapon dropdown, the FBX field, Add, Remove Weapon,
  Rotate/Translate, its colour swatch + Recolour, and the line
  `mayaSceneSetupStatus`. Post-build: `refresh`, the swatch.
- **Order is load-bearing**: `refresh` writes the Characters header, and
  it runs from the Weapons builder, so Weapons follows Characters in the
  table. A test pins the order.
- `_status(message, control=_STATUS)` and `_run(action, status=_STATUS)`:
  character presses name the Characters line, everything else defaults to
  the Weapons line. `is_open()` still asks for the Weapons line (both
  sections are built by one hub build).
- The shelf's `Scene Setup` button becomes `Characters` and `Weapons`
  (eight buttons); `maya_scenesetup.show_weapons` joins `show_window`.
  Hotkeys: `scene.weapon`/`scene.remove_weapon` open the Weapons section
  when nothing is built, `scene.character` the Characters one; a new
  `window.weapons` opener row. Icons `characters.png` / `weapons.png`
  replace `scenesetup.png`.
