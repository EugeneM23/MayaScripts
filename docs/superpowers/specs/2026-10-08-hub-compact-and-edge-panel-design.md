# The hub, compact (variant B) and as an edge panel

2026-10-08. The animator: «Нужно улучшить наш интерфейс. Давай первое что сделаем это сделаем его
компактным. Сейчас много места в отступах и местами есть лишняя информация. Вторая часть я бы хотел
(если это возможно что бы наша полка получила возможность работать как виджет) тоесть когда я подношу
мышку к левому краю экрана то появляется наша полка когда убираю то полка скрывается».

Picked in the brainstorm from browser mockups (`docs/superpowers/mockups/hub-compact-density.html`,
`hub-compact-all-cards-v2.html`):

- **density B, "as dense as it goes"** (over A, "denser, same look"): the same content was 1236 px in the
  current hub, 728 in A, 465 in B;
- every card in B as the second mockup shows it, and then «Окошки в которых списки файлов нужно делать
  шире ... хотя бы 10 было и нужно сделать возможность раздвигать или сдвигать окошко по высоте»: both
  file lists show 10 rows by default and have a height grip;
- the edge panel: **a switch in ⋮** (the dock stays as the other mode), **waiting at the edge from
  Maya's start** (a small autoloaded plug-in), **the full height of the screen**, **a 📌 pin** in the
  header. All four the recommendation.

"Наша полка" is the hub (the SkeldarAnim panel), not Maya's shelf tab (which is two buttons since
2026-09-19).

## Measured before designing

- **The screens** (2026-10-08, DPI-aware): `DISPLAY1` primary 2560 x 1600 at x 0 (150 %), `DISPLAY5`
  3840 x 2160 at x 2560. All three running Mayas are MAXIMIZED on DISPLAY1 (window rect -11..2571, the
  border off screen). So the left edge of Maya's screen is the left wall of the desktop: the cursor
  stops there and nothing lies beyond it. (CLAUDE.md note 3's «virtual desktop starts at X=-2560» is
  stale.) The design still copes with a monitor on the left (below), because colleagues' desks differ.
- **Where the hub's height goes now** (logical px, the skin): root margins 6, gaps 6, the jump strip 28,
  a group label per group, card margins 8 / 7 / 8 / 8, a 6 px gap under each card header, `rowSpacing
  6` in every builder, buttons 32-36 tall, and a FIXED-HEIGHT text line in most cards whether it holds
  anything or not: 14 controls at `height=36`, 3 at `height=54` (statuses, static hints, context
  lines). The full inventory of every card's controls is in the brainstorm's agent report; the
  per-card changes below are written against it.

## Part 1 - compact (variant B)

### The look (maya_hubstyle tokens, maya_hubqt layout)

| What | Now | B |
|---|---|---|
| root margins / gaps | 6 / 6 | 3 / 3 |
| card padding (l t r b) | 8 7 8 8 | 5 4 5 5 |
| gap under the card header | 6 | 4 |
| card header: icon chip / row | 22 / 22 | 18 / 18 |
| builders' `rowSpacing` (skin) | 6 | 3 |
| primary / secondary buttons | 32-36 | 24 |
| small buttons, segments, fields | 22-28 | 20-22 |
| inset padding | 8 | 5 |

Heights are the BUILDERS' numbers, so one constant set decides them: `maya_hubstyle.H` (`button` 24,
`small` 22, `segment` 22, `field` 20) read through `hubstyle.pick(H[...], classic_value)`. The classic
hub keeps its own numbers.

### The header

- One row: the logo, then **the eleven jump icons** (the strip is gone, its buttons move here, each in
  its group's colour), then ⌨ (the hotkey map), 📌 (edge mode only), ⋮.
- **Gone**: the title «SkeldarAnim», the version chip, the group labels (Scene / Animation / Look /
  Settings), the jump strip.
- The version chip's two jobs move:
  - clicking it opened the Update card and checked: ⋮ → Check update does that, and so does the Update
    card's own button;
  - its colour said "a new build is out": the Update jump icon takes `chip_state` (accent when "new",
    `ok` when "ok", muted otherwise).
- The jump icons are Expanding with a minimum of 16 logical px, so the row fits down to ~280 px.

### The cards

- **Group by colour**: a 3 px stripe down each card's left edge in its group's colour (`CardFrame` paints
  it with the light; `card.group_colour`).
- **One message line for the whole hub** (the existing `Skin.message`, under the header): every card's
  status goes there, with that card's icon at its left. Empty: no height. Long: wraps to at most 3
  lines, the rest elided, the whole text its tooltip. × hides it.
  - The relay is `maya_hubstyle.tell(control, text, viewport=False)`: stdlib, a listener list the skin
    registers on build and drops on destroy. Each status writer calls it with its own status control's
    name. The skin knows which card marked that control (`apply_marks`), hence the icon. The eleven
    writers (as of `ed00397`):
    - `maya_scenesetup/window._status(message, control)`: Animation Setup and Inventory;
    - `maya_uebridge/window._status`;
    - `maya_scenesetup/armorpanel._status`;
    - `maya_scenesetup/connections._status`;
    - `maya_share._status`;
    - `maya_rig_retarget._show`;
    - `maya_graphoverlay/mode._show`;
    - `maya_com/panel.status`;
    - `maya_vpstudio._status`;
    - `maya_colour._status`;
    - `maya_update._status`.

    The grids' `Scene.say` go through the first and the armor writers.
  - In the skin a control marked `status` is hidden (zero height), its control kept: every `is_open()`
    asks for it, and the writers still edit it. The classic hub has no listener and shows it as now.
- **Static hints** (role `note`) become their card's header TOOLTIP and are hidden: Retarget's «Select the
  clip's skeleton (and the rig, when several)», Graph Overlay's, Pose Library's, Studio's, Colour's.
  Labels in front of a row («Import», «Bones», «Author», «Name») are gone; their meaning is the row's
  tooltip or the field's placeholder.
- **Runtime context lines** move into the card header's subtitle slot (role `context` -> `subtitle`):
  Connections' state line, Colour's «taken: …», Update's installed line. The subtitle is elided at the
  card's width; its tooltip is the full text.

Per card, top to bottom, as the mockup shows it:

1. **Animation Setup**
   - `[Rig | Skeleton] [+ Import] [🗑] [📷]`: Delete and Camera Setup icon-only.
   - The portraits 5 a row, the «?» card included, the name drawn OVER the picture's bottom on a dark
     gradient (no name strip under it).
   - The Connect inset, no heading:
     - `[Unreal | Unity | Folder]`;
     - `● [project ▾] [⟳]`: the dot is a new role `dot`, green when the editor answered, grey otherwise,
       and the dropdown's tooltip carries `editor_line`;
     - the search field, its placeholder «search 619 animations»;
     - the list, then its grip (below);
     - `[Onto sel. | New] [⏱] [⤓ Import] [⤒] [uasset]`: the timeline checkbox is a chip with a clock
       icon, Export FBX icon-only.
2. **Inventory**
   - `[Weapon | Armor] [⚔ Equip] [🗑]`, the Equip/Unequip of the tab shown.
   - The hand cards: rows 15 px (were 19), names 16 (were 20), channels always `tx … rz`.
   - Weapon and armor tiles 5 a row, names over the picture.
3. **Connections**
   - The state line in the header.
   - `Arm R [FK|IK]  Arm L [FK|IK]` on one row.
   - «Acts on» only while two weapons stand.
   - Hand R / Hand L / Weapon rows with 44 px labels.
   - `[✓ Apply all] [🔗 BakeAcross] [⛓ Release]` on one row.
4. **Shared**
   - `[author] [name]` in one row, no labels (placeholders say which).
   - `[➤ Send scene] [⤒ Send file...]`.
   - The list, then its grip.
   - `[⤓ Open] [Import] [📁] [🗑]`.
5. **Retarget**: `[Auto | Rot. | Stretch] [⇄ Retarget]`, the hint the button's tooltip.
6. **Graph Overlay**: the toggle button alone; its hint the tooltip; «alt+c» the subtitle.
7. **Center of Mass**
   - `[◎ Add CoM] [⟳] [🗑] [Select]`.
   - `[Trail] [Floor] [Playback | Around] [20]`: «frames» is gone, it is the field's tooltip.
8. **Pose Library**: Open Pose Library alone; its line the tooltip.
9. **Studio**
   - `[look ▾] [quality ▾]`.
   - The ten chips as a wrapping flow with short labels: Floor, Shadows, AO, Blur, AA, Bloom, Haze, DoF,
     Clean, Backdrop. The full name is each chip's tooltip.
   - Brightness and Rotate sliders 19 px, labels «Bright» / «Rotate».
   - `[💡 Apply Look] [↶ Restore]`.
10. **Colour**
    - The eight swatches on ONE row.
    - `[custom swatch] [🖌 Paint] [🎨 Next free]`.
11. **Update**: the button alone; installed and found builds in the header.

### The file lists: 10 rows and a height grip

- Both lists (the animations `ueAnimBridgeList`, `skeldarShareList`) show **10 rows by default**.
- Under each list there is a **grip**, an 8 px bar showing ⋯ with the vertical resize cursor. Dragging
  it changes the list's height in whole rows, from 5 to 40.
- The height is **remembered per list** (`skeldarAnimHub_listRows_<name>`).
- How it is built: the builder adds a placeholder right after the list (`cmds.separator(height=8,
  style="none")` marked `grip` with the list's name), so Maya's column holds only Maya controls. The skin
  turns the placeholder into the grip: an event filter for press / move / release, the cursor, the ⋯
  painted.
- The height is set through `cmds.textScrollList(name, edit=True, height=...)` in logical units. Rows ->
  px come from the list widget's own row height (`sizeHintForRow`), measured once.
- The classic hub keeps its fixed heights (300 / 150) and has no grip.

## Part 2 - the edge panel

### What the animator sees

- ⋮ → **Edge panel** (checkable, remembered in `skeldarAnimHub_edge`, off by default, so colleagues keep
  the dock until they turn it on).
  - Turning it on closes the docked hub and builds it in the edge panel; the panel slides out once, so
    the animator sees where it went.
  - Turning it off destroys the edge panel and opens the dock as `show()` does now. The dock's old slot
    is not restored, because the workspaceControl was deleted while the edge panel stood.
- **Hidden**: nothing at the edge.
- **Reveal**: the cursor touches the left edge of the screen holding Maya's main window and stays there
  `DWELL_MS` (100). The dwell stops it popping when the mouse is thrown into the top-left corner for
  File, or crosses into a monitor on the left. No reveal while a mouse button is held (a window or a
  marquee dragged to the edge), and none while Maya is not the active application.
- **The panel**:
  - x from the screen's left edge; y from the top of the screen's WORK AREA to its bottom (above the
    Windows taskbar);
  - over the viewport, not pushing Maya's layout;
  - width `skeldarAnimHub_edgeWidth` (default 360 logical, the animator's dock), changed by dragging a 5
    px grip on its right edge, between 280 and 700;
  - a soft shadow on its right.
- **Slide**: in 180 ms ease-out, out 150 ms ease-in. With ⋮ → Interface animations off it appears and
  disappears at once.
- **Hide**: `HIDE_MS` (350) after the cursor leaves the panel. Postponed (checked again every 150 ms)
  while:
  - 📌 is on;
  - a mouse button is held (a portrait, animation or weapon being dragged into the viewport: hiding the
    source would break its drag);
  - a popup is open (a dropdown's list, ⋮, a right-click menu) or a modal dialog is up;
  - a text field of the panel has the keyboard focus. A click outside moves the focus and the hide goes
    ahead.
- **Opened by command** (the SkeldarAnim shelf button, a hotkey row, any tool's `show_window`): it
  slides out on that card, and stays until the cursor has entered and left it, or a mouse press lands
  outside it.
- **📌** in the header, edge mode only, per session: pinned, it does not hide.
- **A message while hidden** (an import by drag finishing after the panel left): it is also shown as
  Maya's `inViewMessage` for 3 s, unless its writer already shows one itself (`tell(...,
  viewport=True)`: the Retarget button does).

### How it is built

- **`SkeldarAnim/maya_edgerules.py`** (stdlib, pure): the constants, the panel rect from a screen's work
  area and a width, `may_reveal(...)`, `may_hide(...)`, the hold-after-command rule, the slide curve.
  Every rule above is a function of plain values and is unit-tested.
- **`SkeldarAnim/maya_hubedge.py`** (Qt):
  - **`EdgeHost`**: a frameless `Qt.Tool` window owned by MayaWindow (the Graph Overlay's ghost host,
    measured to hold cmds controls), objectName `skeldarAnimHubEdge`, `WA_ShowWithoutActivating`. It
    stands at the screen's left edge, full width, while shown. The Skin's root is its child, and the
    slide MOVES THE ROOT inside the host: no window crosses into a monitor on the left, and nothing is
    laid out again per frame. The host is shown at the start of a slide in and hidden at the end of a
    slide out.
  - **`EdgeSensor`**: a 2-physical-px Tool window over the full work-area height at the screen's left
    edge, owned by MayaWindow, `setWindowOpacity(1/255)` (Qt keeps it layered and hit-testable, trap
    110; the ghost measured that a window at alpha 1 takes the mouse). It is shown only while the panel
    is hidden. Enter starts the dwell timer, Leave stops it.
  - **The controller**: the timers, pin, hold, width grip, follow-the-screen (re-read when the panel is
    revealed and on `QScreen` changes). It reads the cursor and buttons through two seams (`cursor()`,
    `buttons()`), so a verify can drive it without moving the animator's real mouse.
- **`maya_hub`**:
  - `EDGE_VAR`, `edge_on()`, `set_edge(on)` (deferred, like `set_classic`);
  - `build()` builds into the edge host when edge mode is on; the uiScript of an old docked control
    deletes that control and starts the edge;
  - `show(key)` reveals and holds;
  - `is_open()` is true for either home;
  - `start()` is the plug-in's entry: edge mode on → build the edge (hidden); off → nothing.
  - Edge mode needs the skin. With Classic look the menu item is absent and `set_edge(True)` refuses.
- **The startup plug-in** `SkeldarAnim/plug-ins/skeldarAnimStartup.py` (API 2.0, a payload row):
  - `initializePlugin` registers nothing, and outside batch mode `executeDeferred`s: the installed
    folder on `sys.path` (derived from the plug-in's own path), then `maya_hub.start()`;
  - `uninitializePlugin` removes the edge panel;
  - `install.install` loads it by path and sets it `autoload` (`pluginInfo -edit -autoload true`, then
    `-savePluginPrefs`). Measure first whether `pluginPrefs.mel` keeps a full path; if not, copy the file
    to `<userAppDir>/<version>/plug-ins/` (on the default plug-in path, also to be confirmed) and load it
    by name.
- **`install.rebuild_open_hub`** rebuilds the edge panel when it stands, as it rebuilds the dock.
- The drag targets need nothing: `maya_hubqt.on_hub` already answers by the root's objectName, which the
  edge host contains.

## What does not change

- Every control NAME, callback, `refresh`, hotkey row and opener: the work is arrangement, roles, and
  the host.
- The Pose Library window (its own workspaceControl).
- The classic hub except the builders' new row arrangement (its lists keep 300 / 150 px and get no
  grip).

## Proof

- **Unit tests**:
  - `maya_edgerules` (rect, reveal/hide/hold rules, slide);
  - the relay (`tell` with and without a listener);
  - the list-row arithmetic and its clamp;
  - the header's minimum width;
  - the overlay-name grid (`maya_charlook.grid` with no name strip: 5 columns at 338 px);
  - every builder's rows and roles (the existing builder tests updated where a row moved);
  - the plug-in's entry points (a fake `cmds` / `maya.utils`);
  - `install` loading and autoloading the plug-in;
  - `maya_hub` edge-mode switching with fakes.
- **`docs/superpowers/plans/verify_hub_compact.py`**, in a disposable GUI Maya (scratch `MAYA_APP_DIR`,
  `MAYA_NO_HOME`, its own port), the hub floated to the animator's dock (viewport 510 physical):
  - every card opened, the content's minimum width ≤ the viewport, no row wider than its card;
  - each card's height against the current build's, measured by the same script on a snapshot of
    `ed00397`;
  - a status written by each card's writer arrives on the message line with that card's icon, and its
    card grows by 0 px;
  - the notes are tooltips;
  - the grips: a drag changes the list by whole rows, clamps, remembers, and the new hub opens at it.
- **`docs/superpowers/plans/verify_hub_edge.py`**, same Maya. The cursor and buttons come through the
  seams; sensor and host events are sent through Qt; the real cursor is never moved.
  - Edge mode on → the dock gone, the panel built.
  - The sensor's Enter + dwell → slid in, monotonic, landing at the work area's left. A dwell cut short
    → nothing.
  - Leave → hidden after 350 ms. Each postponement (button held, a dropdown open, a field focused, 📌)
    holds it.
  - `show("retarget")` → revealed on that card and held.
  - The width grip remembered. Animations off → instant.
  - Edge mode off → the dock back, every control answering by name.
- **The plug-in**, in a fresh disposable Maya: install → loaded + autoload; Maya restarted with edge
  mode on → the panel waiting, hidden, its sensor up.

## Not built

- The pin remembered across sessions.
- Edges other than the left one.
- The classic hub at the edge.
- Pushing Maya's layout aside instead of overlaying.
- A visible hint while hidden (offered, the default "nothing" kept).
