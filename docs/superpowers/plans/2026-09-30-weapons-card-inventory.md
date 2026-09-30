# The Weapons card as the inventory - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the Weapons card of the hub becomes the inventory itself - two hand slots, each with
a Channel-Box column of its grip, the 10 x 5 grid, Add / Remove - with the colour and the custom
FBX gone from it.

**Architecture:** `maya_invlook` (stdlib) says where everything is for a given card width and how
a channel value reads; `maya_inventory` becomes a Qt panel laid over a `cmds` placeholder (the
Characters grid's `attach` + `Keeper`), twelve `QLineEdit` channel fields its children;
`maya_scenesetup.window` keeps every scene decision (which weapon, which hand, a hand's grip, Add,
Remove) and the panel reaches it through its `Scene`.

**Tech Stack:** Maya 2027 `maya.cmds`, PySide6 6.8.3 (lazily, `maya_hubqt.qt()`), stdlib
`unittest` under `mayapy` (`QT_QPA_PLATFORM=offscreen`).

Spec: `docs/superpowers/specs/2026-09-30-weapons-card-inventory-design.md`.

## Global Constraints

- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
  with `$env:QT_QPA_PLATFORM = 'offscreen'`; no system Python.
- `maya_invlook.py` imports the stdlib and `maya_hubstyle` only; Qt never at module level.
- Logical px in the look, physical in the widget (× `mayaDpiSetting -q -realScaleValue`, trap 98).
- Every colour is a `maya_hubstyle.TOKENS` name; no colour literals in the panel.
- Control names kept: `mayaSceneSetupStatus` (the Weapons line; `is_open`), `mayaSceneSetup_hand`
  (the picked hand), grips in `grips` (`mayaSceneSetup_offset_<key>` / `_L`).
- New names: placeholder `mayaSceneSetupInventory`, subtitle `mayaSceneSetupWeaponsBound`,
  optionVar `mayaSceneSetup_weapon`, fallback menu `mayaSceneSetupWeaponMenu`, panel object
  `skeldarInventoryPanel`, channel fields object `skeldarChannel` with property `skChannel` =
  `"<side>_<channel>"`.
- Channels in Channel Box order `tx ty tz rx ry rz`; nice names `Translate X` ... `Rotate Z`.
- Commit only this work's hunks (peers work in the repo: see memory `parallel-sessions-in-repo`).

---

### Task 1: the panel's look as data (`maya_invlook`)

**Files:**
- Modify: `SkeldarAnim/maya_invlook.py` (the window's `layout()`/`hit()` replaced)
- Test: `tests/test_invlook.py`

**Interfaces - Produces:**
- `CHANNELS = ("tx", "ty", "tz", "rx", "ry", "rz")`, `NICE = {"tx": "Translate X", ...}`
- `channel_names(short)` -> `{channel: name}` (short: the key itself)
- `channel_text(value)` -> str (3 decimals, trailing zeros and `-0` dropped)
- `parse_channel(text)` -> float or None (`,` accepted as the decimal point)
- `split_row(width, nice_w, short_w, value_min, gap=4)` -> `(short, label_w, value_w)`
- `panel(width)` -> `{name: (x, y, w, h)}` logical: `hand_R`, `hand_L`, `name_R/L`, `column_R/L`,
  `well_R/L`, `row_<side>_<ch>`, `gridcard`, `grid`, `panel` (0, 0, width, height); plus
  `cell` as a key of its own (an int)
- `hit(rects, placements, cells, x, y, cell)` -> `("slot", side)` over a hand card,
  `("item", key)`, `("grid",)`, or None

- [ ] **Step 1: failing tests** - `panel(320)`: `hand_R.x < hand_L.x`, the two cards the same
  size, `column_R` right edge < `well_R.x`, the six rows inside the column top to bottom in
  CHANNELS order, `grid.w == 10 * cell`, `24 <= cell <= 40`, `gridcard` below both hands, no
  two of `hand_R`, `hand_L`, `gridcard` overlapping, `panel.h == gridcard bottom`; the same at
  250, 360, 500 (at 500 the cell is 40 and the grid centred); `channel_text` of 0, -0.0, 90,
  1.38, -179.5134, 1e-7 -> "0", "0", "90", "1.38", "-179.513", "0"; `parse_channel` of "1,5",
  " -2 ", "x", "" -> 1.5, -2.0, None, None; `split_row(100, 55, 14, 40)` nice with 55/41,
  `split_row(80, 55, 14, 40)` short with 14/62; `hit` on a hand card, an item, the empty grid,
  the gap.
- [ ] **Step 2:** run `tests.test_invlook` - fails on the missing names.
- [ ] **Step 3: implement**

```python
CHANNELS = ("tx", "ty", "tz", "rx", "ry", "rz")
NICE = {"tx": "Translate X", "ty": "Translate Y", "tz": "Translate Z",
        "rx": "Rotate X", "ry": "Rotate Y", "rz": "Rotate Z"}
MIN_CELL = 24
PAD, GAP, HAND_GAP = 4, 8, 6
NAME_H, ROW_H = 20, 19
HAND_MAX = 230

def channel_names(short):
    return dict((c, c if short else NICE[c]) for c in CHANNELS)

def channel_text(value):
    text = "%.3f" % float(value)
    text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text

def parse_channel(text):
    try:
        return float((text or "").strip().replace(",", "."))
    except ValueError:
        return None

def split_row(width, nice_w, short_w, value_min, gap=4):
    if width - nice_w - gap >= value_min:
        return False, nice_w, width - nice_w - gap
    return True, short_w, max(0, width - short_w - gap)

def panel(width):
    width = int(width)
    cell = max(MIN_CELL, min(CELL, (width - 2 * PAD) // COLS))
    well_w = max(36, min(56, int(round(1.3 * cell))))
    hand_w = max(0, min(HAND_MAX, (width - HAND_GAP) // 2))
    left = max(0, (width - (2 * hand_w + HAND_GAP)) // 2)
    body_h = len(CHANNELS) * ROW_H
    hand_h = NAME_H + body_h + PAD
    rects = {"cell": cell}
    for side, x in (("R", left), ("L", left + hand_w + HAND_GAP)):
        rects["hand_" + side] = (x, 0, hand_w, hand_h)
        rects["name_" + side] = (x + PAD + 2, 0, hand_w - 2 * PAD - 2, NAME_H)
        well_x = x + hand_w - PAD - well_w
        rects["well_" + side] = (well_x, NAME_H, well_w, body_h)
        col_x = x + PAD
        col_w = max(0, well_x - 4 - col_x)
        rects["column_" + side] = (col_x, NAME_H, col_w, body_h)
        for i, ch in enumerate(CHANNELS):
            rects["row_%s_%s" % (side, ch)] = (col_x, NAME_H + i * ROW_H, col_w, ROW_H)
    grid_w, grid_h = COLS * cell, ROWS * cell
    gx = max(PAD, (width - grid_w) // 2)
    y = hand_h + GAP
    rects["gridcard"] = (gx - PAD, y, grid_w + 2 * PAD, grid_h + 2 * PAD)
    rects["grid"] = (gx, y + PAD, grid_w, grid_h)
    rects["panel"] = (0, 0, width, y + grid_h + 2 * PAD)
    return rects
```

`scaled()` skips the `cell` key's tuple handling (it is an int: scaled as `int(round(cell*k))`).
`hit()` checks `hand_R/L` then the grid as before; `layout()`, `SLOT`, `TITLE_H`, `NAME_H` (the
window's), `STATUS_H`, `MARGIN` go.

- [ ] **Step 4:** the invlook tests pass.
- [ ] **Step 5:** commit `feat(inventory): the card panel's look - hands with a channel column, the grid by width`.

### Task 2: the Weapons card's scene side (`maya_scenesetup/window.py`)

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/window.py`
- Test: `tests/test_scenesetup_window.py`, `tests/test_hub_sections.py`

**Interfaces:**
- Consumes: `equip.to_hand(root, side, entry)`, `equip.take_off(root, side)`,
  `equip.occupant(root, side)`, `grips.for_hand / remember / standard / on_node`,
  `bonedrive.measured_grip / is_held / regrip / frame_of`, `attach.is_animated`.
- Produces (read by Task 3's `Scene`):
  - `chosen_weapon()` -> catalog Weapon (the optionVar's key, else `catalog.WEAPONS[0]`)
  - `side()` -> "R"/"L" from `mayaSceneSetup_hand`
  - `select_weapon(key)` -> status text; `select_hand(side)` -> status text
  - `hand_grips(root)` -> `{side: (rotate, translate, editable)}`
  - `set_hand_grip(side, rotate, translate)` -> status text (also written)
  - `add_weapon()`, `remove_weapon()` -> None (status written)
  - `bound_weapons()` -> root (writes both subtitles; `_bound_root` renamed use)
  - `refresh()`; `say_weapon(text)`

Behaviour (the spec's "What a column shows / What an edit does"):

```python
def _hand_grip(root, side, picked):
    """(rotate, translate, editable) the column of `side` shows."""
    if not root:
        return grips.for_hand(picked, side, None) + (False,)
    hand, bone = equip.bones(root, side)
    if not bone or not hand:
        return grips.for_hand(picked, side, None) + (False,)
    weapon, where = equip.occupant(root, side)
    if weapon is None:
        rig = maya_rigs.rig_of(root, maya_rigs.rigs())
        rides = connections.following(rig, side) if rig else None
        return grips.for_hand(picked, side, root) + (not rides,)
    own = _held_entry(weapon, picked)
    if where == "hand" and bonedrive.is_held(weapon) and not attach.is_animated(weapon):
        rotate, translate = bonedrive.measured_grip(weapon, bone)
        return grips.standard(rotate, translate, bonedrive.frame_of(weapon), own) + (True,)
    return grips.for_hand(own, side, root) + (True,)
```

`set_hand_grip` is the old `offsets_changed` with `side` passed in (the entry = the weapon in
that hand, else the picked one; `grips.remember(entry.key, side, ...)`; floor / animated /
empty messages; `bonedrive.regrip` with `grips.on_node` for a clean held weapon). `add_weapon`:
`root = bound_weapons()`, `_locate` refusals (the character, the bone, the parent), the legacy
OverRig link (`linking.linked_weapon()` -> `LINKED_NO_ADD`), an aim on the occupant
(`AIMED_NO_ADD`), then `equip.to_hand(root, side(), chosen_weapon())`. `remove_weapon`: the same
front, then `equip.take_off(root, side())`. `refresh`: `bound_weapons()`, the live panel's
`refresh()`, then the picked hand's state on the line (the old `refresh`'s messages).

Builder:

```python
def build_weapons_panel():
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(_WEAPONS_BOUND, label="", align="left"), "subtitle")
    cmds.columnLayout(_INVENTORY, adjustableColumn=True)
    cmds.setParent("..")
    if not _attach_inventory():
        _weapon_fallback()          # optionMenu _WEAPON_MENU + the Hand segments
    ...Add (primary, plus) + Remove Weapon (danger, trash) in one rowLayout...
    hubstyle.mark(cmds.text(_STATUS, label="", align="left", wordWrap=True,
                            height=36), "status")
    cmds.setParent("..")
    _run(refresh)
    return column
```

Gone (a test pins each): `_MENU`, `_BROWSE`, `_CUSTOM`, `_CUSTOM_OPTIONVAR`, `chosen_entry`,
`custom_changed`, `browse_fbx`, `_remembered_path`, `_ROTATE`, `_TRANSLATE`, `_fields`,
`_set_fields`, `offsets_changed`, `_WEAPON_COLOUR`, `_WEAPON_DOT`, `recolour_weapon`,
`_colour_row`, `pick_dot`, `_swatch`, `_set_swatch`, `_advance_swatch`, `NO_COLOUR_TARGET`,
`recoloured_message`, `appearance`, `open_inventory`, `hand_changed`, `_hand_row`, `_entry`.

- [ ] **Step 1: failing tests** - builder: the subtitle and placeholder, Add primary + Remove
  danger sharing a row, the status marked, and none of optionMenu / textFieldGrp / floatFieldGrp /
  colorSliderGrp / iconTextRadioButton / an Inventory button in the Weapons half; the fallback
  (attach False) makes `_WEAPON_MENU` and the two Hand segments; `chosen_weapon` from the
  optionVar, a stale key, nothing; `select_weapon` / `select_hand` remember and say; Add and
  Remove call a recording `equip` with (root, side, entry) / (root, side) and write the answer;
  a refusal (no character) calls nothing; `set_hand_grip` remembers per side and regrips a
  clean held weapon (fakes for `grips`, `bonedrive`, `equip`); the gone names.
- [ ] **Step 2:** run the two modules - fail.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** both modules pass; the rest of the suite still does.
- [ ] **Step 5:** commit `feat(weapons): the card's scene side - picked weapon and hand, a hand's grip, Add/Remove through equip; no colour, no custom FBX`.

### Task 3: the panel (`maya_inventory`)

**Files:**
- Modify: `SkeldarAnim/maya_inventory.py` (the window class replaced by `InventoryPanel`)
- Test: `tests/test_inventory.py`

**Interfaces:**
- Consumes: Task 1's `panel`, `hit`, `split_row`, `channel_*`; Task 2's window functions.
- Produces: `PLACEHOLDER = "mayaSceneSetupInventory"`, `attach(placeholder=PLACEHOLDER,
  scene=None)`, `live(placeholder=PLACEHOLDER)`, `make_panel(scene, parent=None)`,
  `close_windows()`, `show()`; the panel's `refresh()`, `pick_item(key)`, `pick_hand(side)`,
  `field(side, channel)`, `drop_at(gx, gy, source, grab=None)`, `height_for(width)`.

`Scene` (real): `scale`, `current` (window.bound_weapons), `holdings` (equip), `grips(root)`
(window.hand_grips), `picked()` -> (key, side), `select_weapon`, `select_hand`, `set_grip`,
`snapshot`, `target`, `to_hand`, `to_floor`, `take_off`, `move`, `watch(callback)` /
`unwatch`, `say(text)` (window.say_weapon), `remembered_layout` / `remember_layout`.

Panel behaviour:
- twelve `ChannelField(QLineEdit)` children (`skeldarChannel`, `skChannel` property), placed
  on every resize from `panel(width / k)` rows split by `split_row` with `QFontMetrics`
  widths; `editingFinished` -> `_commit(side)`; Esc puts the shown text back and drops focus;
  read-only when the hand is not editable; `refresh()` never rewrites a field that has focus;
- press on an item picks it (`scene.select_weapon`) and arms a drag; on a hand card picks the
  hand (`scene.select_hand`) and arms a drag when it holds or has a floor weapon; a move past
  `startDragDistance` starts the drag (the hub ghost); the release drops through the window's
  table (unchanged `drop_at`); right click on the grid -> Sort; Esc / right cancel;
- paints the two hand cards (the picked one `card_active` + a 2 px `accent` outline, the drag's
  targets the same, the dragged slot `danger`), the names, the channel names right-aligned in
  `muted` (short names where `split_row` says so), the wells (held / floor / follows), the grid
  card, lines, the preview, the items (the picked one `card_active` + accent outline);
- a `Keeper` event filter keeps it over its placeholder and the placeholder
  `setFixedHeight(height_for(width))`.

- [ ] **Step 1: failing tests** - a `FakeScene` recording calls; the panel paints ink; twelve
  fields with the right properties; `refresh` fills them from `scene.grips` in channel text and
  sets read-only; `field.setText("12"); field.editingFinished.emit()` calls `set_grip("R",
  rotate, translate)` with the six values in order; a bad text reverts, nothing called; Esc
  reverts; a focused field is not rewritten by `refresh`; press+release on an item calls
  `select_weapon` and no drop; on a hand card calls `select_hand`; press + move past the
  distance + release outside -> `to_hand` / `to_floor` (the old table's tests, kept); `attach`
  over a plain QWidget host sets the host's height to `height_for(width)` on resize; `show`
  asks the hub for "weapons"; no colour literal and no Diablo word in the module.
- [ ] **Step 2:** run - fail.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** pass; the whole suite passes.
- [ ] **Step 5:** commit `feat(inventory): the inventory is the Weapons card - hands with a Channel Box, pick and drag`.

### Task 4: the rest of the wiring

**Files:** `SkeldarAnim/maya_hotkeys.py` (the `window.inventory` row's text: opens the Weapons
card), `SkeldarAnim/maya_colour.py` (docstring: weapons are recoloured here, no swatch in
Weapons), `SkeldarAnim/install.py` (the payload comment), `tests/test_hotkeys.py` if a text is
pinned.

- [ ] run the suite, commit `chore(weapons): hotkey text and docs follow the card`.

### Task 5: live proof, the installed copy, CLAUDE.md

- [ ] `docs/superpowers/plans/verify_weapons_card.py` in a disposable Maya (scratch
  `MAYA_APP_DIR`, `MAYA_NO_HOME=1`, a free port, killed afterwards): the gates of the spec's
  "Live" list, then the card photographed in a send of its own.
- [ ] refresh the animator's installed copy from a `git archive` of the commit (never the
  working tree), `diff -rq` it, the open hub rebuilt.
- [ ] CLAUDE.md: a section "The Weapons card IS the inventory (2026-09-30)" with the proof and
  any trap found; commit only those hunks.
