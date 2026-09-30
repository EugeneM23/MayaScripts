# Open scene on the right button — design

2026-09-30. The animator, after asking whether Maya allows a context menu on the
icons at all («А можно ли при нажатии правой клавишей мыши на иконку оружия или
рига\селета вызывать контекстное меню ... Есть ли такая возможность в мая?»):

> Давай сделаем так что бы когда я нажимал правой клавишей по иконке рига или
> оружия то у меня появлялось опция Open scene и при нажатии на нее у нас бы
> открывался соответствующий фаил

## What it is

- **Characters grid** (`maya_chargrid`): the right button on a portrait opens a
  menu with one row, **Open scene**. It opens the model's file in the kind the
  `[Rig | Skeleton]` switch shows (`catalog.character_file`), e.g.
  `assets/Manny_Rig.ma`, `assets/Creep_Skeleton.ma`, `assets/UE4_Mannequin.fbx`.
  A dimmed portrait (the model has no such kind) shows the row disabled with the
  reason — «Open scene (no skeleton)».
- **Weapons inventory** (`maya_inventory`): the right button on a weapon in the
  grid, or on a hand card holding / dropping a catalog weapon, offers **Open
  scene** — the row's `path` (`assets/Spear_03.fbx`). On the grid the existing
  **Sort the inventory** stays, under a separator. An empty hand offers nothing.
- A right press during a drag still cancels the drag; a right press never picks
  (no click, no drag starts).

Both are ordinary Qt `QMenu`s (`maya_hubqt.build_menu` / `run_menu`, one helper);
the hub's stylesheet already styles `QMenu` (the ⋮ menu in the header). They
live in the skinned hub and the classic one alike, since both grids are laid
over their `cmds` placeholders in either.

## Opening (`maya_scenesetup/opener.py`)

- The file is the plugin's own copy under `assets/`. Missing → «the plugin has
  no assets/X - nothing opened».
- A modified scene gets **Maya's own «save changes?»** (`saveChanges("")`, the
  Shared card's road); Cancel → «Open scene cancelled - nothing changed».
- `.ma`/`.mb`: `file -open -force -executeScriptNodes false -prompt false`. The
  plugin's assets carry no script nodes we want run, and the rule that nothing in
  a file runs on the way in is Shared's (trap "vaccine"). The ranges the scene
  configuration node would have set are parsed out of it and applied
  (`maya_sharerecords.playback_from_script`, trap 129), a vaccine node that got
  in anyway is deleted, and the shipped textures — named relatively in the
  assets (`colour.ASSET_IMAGE`) — are pointed at the plugin's own images
  (`colour.relink_images`). Then `file -modified false`: the scene is the file.
- `.fbx`: `fbximport.open_file` — the same import-mode guard as every import
  (trap 33: under the `exmerge` a UE-bridge import leaves, the open would bring
  nothing).
- The line: «Opened Manny [rig] - assets/Manny_Rig.ma. Save As to keep changes:
  a save writes into the plugin, and an update replaces its files.» Opening the
  file itself was the ask, so Ctrl+S does write into the installed plugin; the
  line says so rather than hiding the file behind an untitled copy.

Decided without asking:

- **The file as it is on disk.** Spear 03's FBX carries a plain lambert (its
  texture is applied by Weapons > Add), so it opens untextured; an FBX
  character opens with its importer wrapper (Add flattens it). Opening means
  the file, not what Add makes of it.
- **Shared keeps its own copy** of the save-changes / playback / clean lines:
  its tests drive it on a fake `cmds` of their own, and binding it to this
  module would tie two test harnesses together for twenty lines.

## Proof

- Unit: `tests/test_scenesetup_opener.py`, `OpenFile` in
  `test_scenesetup_fbximport.py`, `Menu` in `test_hubqt.py`, the right-button
  tests in `test_chargrid.py` / `test_inventory.py`, `OpenScene` in
  `test_scenesetup_window.py`.
- Live: `docs/superpowers/plans/verify_open_scene_menu.py` in a disposable GUI
  Maya — real right-button events, the real menu read and activated while its
  `exec()` runs, Maya's save dialog answered by clicking its buttons.
