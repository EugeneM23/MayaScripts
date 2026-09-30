# The Characters card as a portrait grid, and a character dragged into the scene

2026-09-30. The animator: «Давай теперь поработаем над меню выбора персонажа! Все что
касается покраски вынесем из меню, будем красить в меню с красками. Давай полностью
переделаем наше меню на сетку с портретами (как меню выбора героев в Mortal Kombat или
Dota 2). Выделив какой-то портрет, кликнув по нему мышкой, и потом нажав кнопочку Add
Character, мы как и сейчас добавляем риг или скелет в сцену. Но давай сделаем еще так,
чтобы я мог зажать на портрете и перетащить его в сцену Maya, и персонаж создастся в том
месте, куда я его перетащил, подобно тому функционалу, что мы сделали с оружием и
инвентарем.»

Answered in the brainstorm:

- the portrait is **head and shoulders, square** (Mortal Kombat), not the waist-up or
  full-height card;
- **one portrait per model** with a **`[Rig | Skeleton]` switch** above the grid, not two
  rows and not an X-ray skeleton portrait;
- a dropped character stands **as in its file, facing +Z**: only a translation, no turn;
- «Делай все до самого конца».

## What changes

### The Characters card

Before: the subtitle, a dropdown of six rows, the palette (eight dots, a swatch, Recolour),
Add Character, Camera Setup, the status line.

After:

```
Characters                                   Manny_Rig:root (rig)
[   Rig   |  Skeleton  ]
+------+ +------+ +------+ +------+
|      | |      | |      | | ░░░░ |   <- the portrait of a model without
| Manny| | Creep| | Orc D| | ░░░░ |      the chosen kind is dimmed
+------+ +------+ +------+ +------+
 Manny    Creep    Orc D   UE4 Mannequin
[+ Add Character                     ]   (primary)
[  Camera Setup                      ]
Manny [rig] - press Add, or drag the portrait into a viewport
```

- **The colour leaves the card.** No dots, no swatch, no Recolour here. A character
  arrives in the next free palette colour (`colour.free_colour()`, what `add_character`
  already does with `rgb=None`), so two presses in a row still never collide. Recolouring
  is the **Colour** section's (`maya_colour`): it paints the selection, and Add leaves the
  new rig's `Main` selected, so one click on a colour there repaints the character just
  added (a rig control resolves to the rig's game skeleton through `current_root`, measured
  in the live verify). The Weapons card keeps its colour row: the ask was about the
  character menu.
- **Four portraits, one per model**: Manny, Creep, Orc D, UE4 Mannequin. The switch picks
  the kind; the catalog row is (model, kind): Manny rig / Manny UE5 skeleton, Creep rig /
  Creep skeleton, Orc D rig, UE4 Mannequin skeleton. A model without the chosen kind is
  **dimmed**: not selectable, not draggable, its name muted, a small «no rig» / «no
  skeleton» tag on it.
- **A click selects** a portrait: the hub's active look, a 2 px accent outline on a
  `card_active` tile. The status line says what Add will import. The choice (model and
  kind) is remembered in two optionVars; a label remembered by the old dropdown
  (`mayaSceneSetup_character`) is read once as the fallback, so the animator's last pick
  survives the change.
- **The selection outlives a switch.** Picking Skeleton while Orc D is selected keeps it
  selected (dimmed ring); Add then refuses by name: «Orc D has no skeleton - pick Rig, or
  another portrait». Nothing is imported.
- **The grid fits the dock.** Columns = as many cells of at least 72 logical px as fit the
  card's width, at most 120 px each; in the animator's 360 px dock that is one row of four.
  A wider dock grows the portraits; a narrow one wraps into two rows.
- Add Character stays the one primary action; Camera Setup and the status line stay.

### Dragging a portrait into the scene

The inventory's gesture, for a character:

1. Press on an available portrait: it is selected at once.
2. Move past Qt's start-drag distance with the button held: the drag starts. A **ghost**
   (the portrait, square, and a caption pill under it) follows the cursor; the press has
   captured the mouse, so the viewport never sees the moves and Maya's own drop handling
   never enters. `Esc` or the right button cancels.
3. The caption names what a release would do, re-read at most every 33 ms:
   «Manny [rig] · floor (120, -35)», or «no floor under the cursor», or «drop onto a
   viewport».
4. Release over a viewport: the camera ray through the cursor meets the floor (`Y = 0`) in
   front of the camera (`droptarget.floor_hit`, the inventory's own), and the character is
   added **there**. Released over the hub or anywhere that is not a model panel: nothing,
   and the line says why.

**Where "there" is written:**
- **a rig**: its `Main` (the whole rig's control, root motion) moved by `(x, 0, z)` in world
  space. The skeleton's root rides Main by its constraint;
- **a skeleton**: its `root` moved by `(x, 0, z)` in world space. On the Creep skeleton that
  is `root` under `Armature`; the Null is never moved, or the export would no longer
  recognise Cascadeur's layout (`fbxlayout.in_layout` wants it at the origin).

The move is relative, so the feet keep the height the file gives them. **Facing is the
file's (+Z)**: no rotation is written.

**No half-undo** (the live run changed this; see the addendum). A character cannot be
undone: `file -import` flushes Maya's undo queue, as Maya's own File > Import does. So what
follows the import (the colour, the sweep, the move, the selection) runs with undo recording
off: a Ctrl+Z never leaves the new character unpainted at the origin.

**What a placement means, and what it does not.** The retarget works in world space: `Main`
follows the source's root. A rig dropped at (120, 0, -35) and then given a clip through the
bridge or the Retarget button stands where the clip stands, as a rig added at the origin
does today. The drop chooses where a character appears.

### Portraits

Rendered once, shipped as `SkeldarAnim/assets/character_portraits/<model>.png` (the whole
`assets/` folder is payload), exactly as the weapon icons are. A test pins a portrait for
every model of the catalog, so a new row cannot ship without one.

`docs/superpowers/plans/make_character_portraits.py` renders them **in a disposable GUI
Maya**. Viewport 2.0 needs a viewport, so not mayapy; and not the animator's scene. For each
model:
- a fresh scene; the model's rig row added (else its skeleton row) through
  `character.add_character`;
- only polygons shown. Non-textured models wear one light clay phong, so a portrait never
  shows a palette colour a character will not arrive in. The Orc D keeps its own textures;
- three directional lights (warm key, cool fill, rim), AO and multisample AA on;
- a perspective camera at 85 mm, framed head and shoulders from the skeleton:
  - the head joint and the two upper arms give the span;
  - the mesh top gives the crown;
  - a slight three-quarter turn and a little above the eyes;
- a 512 px playblast with an alpha background, scaled to 256 px with smooth filtering.

The widget draws each portrait over the hub's `field` colour, so the backdrop is always the
hub's.

## Units

| Unit | What | May import |
|---|---|---|
| `maya_scenesetup/catalog.py` | `Model(key, label)` and `MODELS` in grid order; `Character.model`; `character_for(model, kind)`, `kinds_of(model)`, `model_by_key`, `model_of(entry)`, `default_model()`, `portrait_path(model)`; `KINDS = ("rig", "skeleton")` | stdlib |
| `maya_charlook.py` (new) | the grid as data: `grid(width, count)` -> columns, cell size, the tiles' rects and the height; `hit`; a tile's state; the captions (`place_caption`, `absent_text`, `import_text`); `dragged(start, now, threshold)` | stdlib + `maya_hubstyle` (tokens) |
| `maya_chargrid.py` (new) | the Qt widget `PortraitGrid` (paint, select, drag, drop), `Scene` (what it asks and does to Maya: the floor target, the placement, the status line, the display scale), `attach(placeholder, scene)` / `live()`; Qt lazily through `maya_hubqt.qt()` | Qt, `maya_charlook`, `maya_hubqt`, lazily `maya_scenesetup` |
| `maya_hubqt.py` | `ghost_class()`: the drag ghost the inventory and the grid share, the inventory's own moved here (pixmap, icon size in physical px, the cursor's anchor on it) | Qt |
| `maya_inventory.py` | uses the shared ghost; no behaviour change | |
| `maya_scenesetup/droptarget.py` | `floor_at(gx, gy)`: the floor point under a global cursor position, or why not | Maya, Qt (inside) |
| `maya_scenesetup/character.py` | `add_character(entry, rgb=None, at=None)`: `at` places it; `place(entry, namespace, root, at)`; one undo chunk | `maya.cmds` |
| `maya_scenesetup/window.py` | the new card: the switch, the placeholder the grid is attached to, Add Character, Camera Setup; the choice's memory; `select_model`, `kind_changed`, `place_character`; the colour row gone from Characters | `maya.cmds`, lazily `maya_chargrid` |

### How the Qt grid lives in a `cmds` card

The builder makes an empty `columnLayout` named `mayaSceneSetupPortraits` where the grid
goes (both hubs: the skin's card body and the classic frameLayout are `cmds` parents). Then
`maya_chargrid.attach` does the following:
- finds its widget (`maya_hubqt.find(name, layout=True)`);
- makes the grid a CHILD of it, kept over its whole rect by an event filter (the `_spread`
  mechanism: Maya's layouts place their own children, so ours is laid over, not inserted);
- gives the placeholder a fixed height from `grid(width)`, recomputed on every resize.
  That is how the dock's width decides the rows.

Without Qt (a Maya where `maya_hubqt.qt()` is None, or the attach fails), the builder falls
back to the old dropdown of all six rows, and the rest of the card works as before.
`chosen_character()` answers from whichever stands.

## What stays

- `character.add_character(entry)` with no `at` behaves exactly as before, apart from the
  one undo chunk. The UE bridge's `add_character(default_rig())` and every verify script
  that calls it are unchanged.
- The Weapons card, its colour row, the inventory's behaviour.
- The hotkey rows (`window.characters` opens the section as before).

## Refusals and messages

- Add with the chosen model lacking the kind: `absent_text(model, kind)`, nothing imported.
- A drop on no floor or off every viewport: the caption's text on the status line, nothing
  imported.
- A missing asset: `character.NO_FILE`, as today.
- A drop that raises: the exception's last line on the status line (the grid's `_act`).

## Testing

- **Unit, stdlib**:
  - catalog: every row has a model; `character_for` and `kinds_of` agree with the table;
    every model has a portrait file;
  - `maya_charlook`: columns, cell size and height at 360 / 250 / 700 px; `hit`; states;
    captions; the drag threshold.
- **Unit, Qt offscreen, a fake scene**:
  - the grid paints ink and the portraits;
  - a click selects (and calls back), a dimmed tile does not;
  - the switch dims the right model;
  - a synthetic press-move-release outside the widget drops (`place` called with the model,
    the kind, the point);
  - Esc and the right button cancel;
  - `drop_at` on no floor says why and places nothing;
  - the ghost is the shared one.
- **Unit, fake cmds**:
  - the Characters builder: no colour controls; it makes the switch and the placeholder, Add
    Character primary, Camera Setup, the status line, and the dropdown only when the grid
    could not attach;
  - `chosen_character` from model + kind, from the old label, and None for an absent pair;
  - `add_character` refuses an absent pair, passes no colour, writes the status;
  - `character.place` moves `Main` / `root` relatively and never an `Armature`;
  - `add_character(at=)` runs in one chunk.
- **Live, a disposable Maya** (`verify_character_grid.py`, port 7003, scratch
  `MAYA_APP_DIR`, `MAYA_NO_HOME=1`):
  - the skinned hub's Characters card holds the grid with four portraits loaded, and no
    colour control;
  - the switch dims UE4 Mannequin under Rig and Orc D under Skeleton;
  - a drop of Manny [rig] at a floor point projected through the viewport lands `Main` on
    the point `floor_at` computed (1e-6) and within a pixel's worth of the intended point;
  - a drop of the Creep skeleton moves `root`, leaves `Armature` at the origin, and
    `fbxlayout.root_in_layout` still answers True;
  - a press of Add Character imports at the origin;
  - the Colour section's paint on the selection repaints the rig just added;
  - a Ctrl+Z after a drop leaves the character whole where it stands;
  - a synthetic press-drag-release on the grid (QMouseEvents at global points) adds a
    character at the release point.
- **The picture**: the card grabbed (`widget.grab()`, a send of its own - trap 68) for the
  animator.

## Addendum - what the live run changed (2026-09-30)

- **The import cannot be undone, and nothing after it is recorded.** The plan wrapped the
  press in one undo chunk, and the live gate failed. Measured in the disposable Maya:
  - a cube made before a `file -import` in the same deferred call could not be undone after
    it ("There are no more commands to undo");
  - the chunk left in the queue held only what followed the import, so a Ctrl+Z moved the
    dropped Orc D back to the origin.

  `character._unrecorded` turns undo recording off (`stateWithoutFlush`) for everything
  after the import and puts it back as it was. Gate 10 now proves that a Ctrl+Z leaves the
  dropped character exactly where it stands.
- **A scripted `iconTextRadioButton -e -select` is not a click.** It ran the segment's
  `onCommand` in one hub build and not in the next (the grid kept its kind while the
  segment moved). A Qt `click()` on the button runs it every time, and that is how the
  verify switches the kind. The animator's real click was never in question.
- **The rename note named a rig's joint again.** A Creep skeleton added beside rigs alone
  kept its plain `root`, yet the note said «imported as root (Manny_Rig:FKXAnkle_L already
  in the scene)». With no plain top joint among the others, nothing collided and there is
  no note.
- **The disposable Maya is on the animator's screen** (trap 85 again). Between two sends
  its hub moved and shrank (the placeholder went from 685 to 546 px), and the undo queue
  held a `selectionMaskResetAll` nobody sent. The drop's point is projected afresh on every
  send, and the floating hub is moved off it when it stands in the way.

Proof: `verify_character_grid.py`, all 11 gates passed in the disposable Maya (port 7004):
- gates 1-9 in one run;
- gates 10 and 11 in a re-run: a drop queued with `evalDeferred`, then the classic hub.

The measurements:
- the card holds the grid, 4 portraits, and the placeholder is 685 x 192 physical px at
  150 % (192 = the grid's height for its width);
- no colour control and no dropdown in the card;
- Skeleton dims Orc D, Rig dims the UE4 Mannequin;
- floor_at within 0.1-1.3 cm of the projected world points;
- Manny [rig] dropped with `Main` on that floor point to 1e-6, unturned;
- the Creep skeleton's root moved by exactly (x, 0, z), its `Armature` at the origin, still
  in Cascadeur's layout;
- Add Character at the origin;
- the Colour section repainting the rig Add left selected;
- a synthetic press-drag-release on the Creep portrait standing a Creep rig at the release
  point to 1e-6;
- Ctrl+Z after a drop changing nothing;
- the grid standing in the classic hub.
