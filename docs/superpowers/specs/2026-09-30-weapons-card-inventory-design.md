# The Weapons card IS the inventory: hands with a Channel Box, the grid, Add / Remove

2026-09-30. The animator: «Давай сделаем с меню Weapon тоже самое что сделали с
персонажами. Все что касается покраски оружия вынесем в покраску. А сам выбор оружия
превратим в наш инвентарь. Суть такая - когда я открываю вкладку weapon то у меня вместо
того что сейчас открывается наш сетчатый инвентарь с оружием, но не в отдельном окне а как
часть нашего меню. Возможность задавать офсеты давай добавим возле окошек правой и левой
руки оружия. Возможность добавлять кастомное оружие по указанию пути давай пока уберем
совсем.»

Answered in the brainstorm:

- the two hand slots stay **side by side, as in the inventory window**; to the LEFT of each
  a **column of the six grip values laid out like Maya's Channel Box** («слева от окошка
  столбик с параметрами так как в стандартном интерфейсе маи в channel box»);
- **Add / Remove stay, as in Characters**: a click picks a weapon in the grid, a click on a
  hand slot picks the hand; Add puts the picked weapon into the picked hand, Remove takes the
  picked hand's weapon off; dragging works as it does now.

## What changes

### The Weapons card

Before: a weapon dropdown with an FBX... button, `Hand [Right | Left]`, the FBX path field,
Add + Remove Weapon, an Inventory button (a floating window), the grip as two
`floatFieldGrp` rows, the palette row (dots, swatch, Recolour), the status line.

After:

```
Weapons                                     Manny_Rig:root (rig)      <- subtitle
+- Right hand ----------------+ +- Left hand -----------------+
|  Translate X   0  +-------+ | |  Translate X   0  +-------+ |
|  Translate Y   0  |   /   | | |  Translate Y   0  |       | |
|  Translate Z   0  |  /    | | |  Translate Z   0  |       | |
|     Rotate X   0  | /     | | |     Rotate X   0  |       | |
|     Rotate Y   0  |/      | | |     Rotate Y   0  |       | |
|     Rotate Z   0  +-------+ | |     Rotate Z   0  +-------+ |
+-----------------------------+ +-----------------------------+
+- the grid, 10 x 5 ---------------------------------------------+
|  |  /  |  |  |  |  |  |  |  |  |                                |
+----------------------------------------------------------------+
[+ Add                              ] [ Remove Weapon ]
Long Sword 02 - press Add to put it into the right hand, or drag it
```

- **The inventory lives in the card.** One Qt widget (`maya_inventory.InventoryPanel`) is
  laid over an empty `cmds` placeholder `mayaSceneSetupInventory` - the Characters grid's
  mechanism (`attach`, a `Keeper` keeping the placeholder as tall as the panel needs for its
  width) - so the same panel stands in the skinned hub and the classic one.
- **The floating window is gone.** `maya_inventory.show()` and the hotkey row
  `window.inventory` open the hub on the Weapons section. An older build's floating window
  (object name `skeldarInventory`) is closed by name on attach and on show (trap 102's rule:
  found by name, never by module state).
- **The colour leaves the card.** No dots, no swatch, no Recolour. A weapon arrives in the
  next free palette colour (`attach.import_weapon` with `rgb=None`, what the inventory's drops
  already do). The **Colour** section repaints the selection, and a selected sword means that
  sword (`maya_colour.target_for`), so recolouring a weapon is: click it in the viewport,
  click a colour.
- **No custom FBX.** The FBX field, the folder button and the path memory are removed
  (`chosen_entry`, `custom_changed`, `browse_fbx`, `_CUSTOM*`). `catalog.entry_for_path`
  stays: a scene holding a weapon added from a file before this still names its file
  (`equip.entry_of`), so the inventory can move it between hands.
- **No `Hand [Right | Left]` row**: the hand slot clicked last is the hand (a lit card). The
  choice is still `mayaSceneSetup_hand`.
- **No weapon dropdown**: the grid item clicked last is the weapon, remembered in
  `mayaSceneSetup_weapon` (a catalog key; the first row when never set or stale).
- **A subtitle names the character** (`mayaSceneSetupWeaponsBound`, marked `subtitle`), as
  the Characters card does; the panel itself paints no name and no status well - the card's
  status line `mayaSceneSetupStatus` says everything.

### The hands

Each hand is a card: its name on top ("Right hand" on the viewer's LEFT, as in the window -
the picker's convention), then the **channel column** and the **well** side by side.

- **The well** shows the hand's weapon - held (full), on the floor (dimmed, «on the floor»
  tag), or «follows <weapon>» text when the hand's IK rides another weapon - exactly what the
  window's slots showed (`equip.holdings`).
- **The channel column** is the Channel Box: six rows, `Translate X/Y/Z` then `Rotate X/Y/Z`
  (the Channel Box's own order), the name right-aligned in `muted`, the value an editable
  field right-aligned beside it. Values read like the Channel Box's: up to three decimals,
  trailing zeros dropped, `-0` shown as `0` (`look.channel_text`). The rows are 18-20 logical
  px, so the column stands as tall as the well.
  - Click a value, type, **Enter** (or leave the field): that hand's six values are applied
    (below). **Esc** puts back what was shown. **Tab** walks the column.
  - Where the names do not fit beside a value (a dock narrower than the animator's 360 px),
    the Channel Box's SHORT names are used (`tx ty tz rx ry rz`), the Channel Box's own option
    for exactly this (`look.channel_names`).
  - A hand that follows another weapon, a missing bone, or no character: the values are
    shown read-only in `faint`.
- **What a column shows** (`window.hand_grip(side)`, the old `refresh` per hand):
  - the hand HOLDS a clean weapon: its grip measured against the drive bone, in the socket
    standard (`bonedrive.measured_grip` -> `grips.standard`), so a sword nudged by hand reads
    back honestly;
  - the hand holds an ANIMATED weapon, or one lying on the floor: that weapon's remembered
    grip for this hand (`grips.for_hand`);
  - the hand is EMPTY: the grip the picked weapon would take in this hand
    (`grips.for_hand(picked, side, root)`) - what Add or a drag would apply.
- **What an edit does** (`window.set_hand_grip(side, rotate, translate)`, the old
  `offsets_changed` for one hand): the weapon in the hand owns the numbers when there is one,
  else the picked weapon; they are remembered for that weapon and hand (`grips.remember`);
  a clean held weapon is re-gripped live (`bonedrive.regrip`, the bone does not move); an
  animated one says `LINKED_NO_OFFSETS`; a floor one says the grip applies in the hand; an
  empty hand says the next Add brings it. The panel re-reads both columns afterwards.

### The grid

The catalog, 10 x 5 cells, every weapon always there, as the window's grid - its
rearranging by hand, Sort, the remembered layout (`skeldarInventoryLayout`), unchanged.

- **The cell follows the width**: `cell = (width - pads) / 10`, between 24 and 40 logical px
  (the window's 40); the grid is centred when the card is wider than 10 cells of 40.
- **A click picks** a weapon: an accent outline on a `card_active` fill (the Characters
  grid's selected tile), the status line «Long Sword 02 - press Add to put it into the right
  hand, or drag it». The empty hands' columns switch to that weapon's grips.
- **A drag starts past Qt's start distance** (it started on the press in the window; a click
  must now be a click). Everything a drop does is the window's table, unchanged: a hand slot
  -> into that hand; the grid -> rearrange (a grid item) or take off (a slot's weapon); the
  viewport -> the hand under the cursor, or the floor; Esc / the right button cancel; the
  ghost is the hub's shared one.

### Add / Remove

- **Add** (primary): the picked weapon into the picked hand of the current character, through
  `equip.to_hand` - the inventory's own path (the hand's remembered grip, whatever that hand
  held taken off first, one undo chunk). Refusals first and by name: no character, a missing
  bone, the legacy OverRig link, an aim on the weapon being replaced, the hand following
  another weapon, the hands riding the weapon it holds, a missing file.
- **Remove Weapon** (danger): the picked hand's weapon off through `equip.take_off` (the bone
  gets its animation back). Refused for the legacy link and an aim.
- The hotkey rows `scene.weapon` / `scene.remove_weapon` press the same functions; they read
  the picked weapon and hand from the optionVars, so they work with the card collapsed.

### Without Qt

`maya_hubqt.qt()` is None only on a Maya without PySide (none in use here). The builder then
makes a weapon dropdown and the `Hand [Right | Left]` segments in the placeholder's place,
both writing the same two optionVars, so Add and Remove still work; there are no grip fields
there.

## Units

| Unit | What | May import |
|---|---|---|
| `maya_invlook.py` | the panel's look as data: `panel(width)` -> the rects (hand cards, their names, channel columns and rows, wells, the grid card, the grid) and the cell; `channel_text(value)`, `parse_channel(text)`, `channel_names(fits)`, `CHANNELS`; `hit` over the panel's rects; `pack`, `arrange`, `plan_move`, the record - unchanged. The window's `layout()` (title, close, name, status) is gone | stdlib + `maya_hubstyle` |
| `maya_inventory.py` | `InventoryPanel` (paint, pick, the channel fields, drag, drop), `Keeper`, `Scene` (what it asks of and does to Maya), `attach(placeholder)`, `live(placeholder)`, `close_windows()`; `show()` opens the hub on Weapons | Qt (lazily, `maya_hubqt.qt()`), `maya_invlook`, `maya_hubqt`, lazily `maya_scenesetup` |
| `maya_scenesetup/window.py` | the Weapons card: subtitle, the placeholder the panel is attached to, Add + Remove, the status; `chosen_weapon`, `select_weapon`, `select_hand`, `hand_grip`, `set_hand_grip`, `add_weapon`, `remove_weapon`, `refresh`; everything listed under "What changes" gone | `maya.cmds`, lazily `maya_inventory` |
| `maya_hotkeys.py` | the `window.inventory` row's text | |

## Refusals and messages

- Add with nothing pickable (a stale key): the first catalog row is picked.
- Add / Remove / an edit with no character, a missing bone, a parentless bone: the old
  messages (`NO_CHARACTER`, `missing_bone_message`, `missing_parent_message`).
- Remove on an empty hand: «nothing in the right hand».
- A value that is not a number: the field puts back what was shown; nothing applied.
- Anything that raises: its last line on the status line (`_run`, the panel's `_act`).

## Testing

- **Unit, stdlib** (`test_invlook`): `panel` at 250 / 320 / 360 / 500 px (the hands side by
  side, each column left of its well, the grid 10 cells wide with its cell clamped, nothing
  overlapping, the height), `channel_text` (0, -0, 90, 1.38, -179.513, 1e-7), `parse_channel`,
  `channel_names` (nice names where they fit, short ones below), `hit` over the new rects; the
  packing and rearranging tests unchanged.
- **Unit, Qt offscreen, a fake scene** (`test_inventory`): the panel paints ink and the
  items; twelve channel fields named per hand and channel; the fields show the scene's grips
  in Channel Box text; an edit + Enter calls `set_grip` with that hand's six values; Esc puts
  the text back; a read-only hand's fields do not edit; a click on an item picks it (no drag)
  and a click on a slot picks the hand; a press moved past the start distance drags; the drop
  table (hand, floor, slot, back to the grid, the other slot, rearrange, no target); `attach`
  lays it over a placeholder and keeps the placeholder's height; `show` opens the hub; the old
  window's styling tests (no colour of its own, hub tokens only).
- **Unit, fake cmds** (`test_scenesetup_window`, `test_hub_sections`): the Weapons builder
  makes the subtitle, the placeholder, Add (primary), Remove (danger), the status - and no
  optionMenu, no FBX field or button, no Hand row, no floatFieldGrp, no colour row, no
  Inventory button; the fallback without Qt; `chosen_weapon` from the optionVar, a stale key
  and nothing; Add and Remove call `equip` with the picked weapon and hand and write its
  answer; the gone names (`chosen_entry`, `custom_changed`, `browse_fbx`, `recolour_weapon`,
  `open_inventory`, `hand_changed`).
- **Live, a disposable Maya** (`verify_weapons_card.py`, scratch `MAYA_APP_DIR`,
  `MAYA_NO_HOME=1`): the skinned hub's Weapons card holds the panel (twelve fields, the grid,
  every catalog item) and none of the removed controls; a click on the Spear 03 item and on the
  left hand's slot, then Add: Spear 03 in Manny's left hand, the left column showing its grip;
  an edit of Rotate Y in the right column after Add of the Long Sword: the sword turns in the
  hand, the bone does not move, the value reads back; Remove: the right hand empty, the bone's
  animation back; a drop of the Dagger onto the projected right hand (`drop_at`); the Colour
  section painting the selected sword; the classic hub holding the panel too; the card
  photographed (a send of its own, trap 68).
