# Animation Setup: folders you can pick, export and save into, Show in Explorer (2026-10-23)

The animator, after the folder tree (`2026-10-23-animation-setup-folder-tree-design.md`): «Мы должны иметь
возможность выделять папки по необходимости экспортировать или сохранять файл в выделенной папке. Так же по
нажатию правой кнопочки на папке или файле мы должны иметь возможность выбрать show in explorer». Asked, and
answered:

- a click PICKS a folder, a double click opens / closes it (Explorer's way);
- the export writes the FBX straight into the picked folder, asking only for the name;
- besides the FBX, the Maya scene is saved there too (a second command);
- an Unreal folder means its folder on disk under the project's Content.

**This replaces the tree spec's click rules**: «A click on a folder row opens or closes it; the folder row is
taken out of the selection at once» and the double-click guard (`DOUBLE_S`, `last_toggle`, `last_click`,
`picked`, `prev_sel`). Everything else in the tree spec stands.

## 1. Clicks in Folders mode

- A click on a folder row picks it like an animation row; Ctrl and Shift work as Maya's list does. Nothing
  opens.
- A double click with exactly one folder picked and no animation opens or closes that folder, and imports
  nothing. Any other double click imports the picked animations, as in List mode (with nothing picked,
  `import_selected` says «select an animation first»).
- Import, the drag into a viewport and Export to uasset act on the picked animations only; a picked folder
  never imports (`_selected_records` skips folder rows, `listdrag.carried_records` already does).
- A rebuild (a folder opened, a search, a refresh) keeps the picked animations by package and the picked
  folders by path (`_repopulate`'s keep).

## 2. Where a row lives on disk

`foldertree.disk_path(row, source, root, content_dir)` (pure):

- **Folder** source: `root` (the chosen folder) + the row's path; an animation row, its record's `path`.
- **Unity**: `root` (the project folder) + the row's path; an animation row, its record's `path`.
- **Unreal**: a folder `Game/<rest>` -> `content_dir/<rest>` (`Game` alone -> `content_dir`); an animation
  row, `records.uasset_path_of(package, content_dir)`. A folder of another mount, or no `content_dir`
  (an old cache), answers "".
- Slashes forward, no trailing slash.

## 3. Export FBX... and Save scene... into a picked folder

In the Export ▸ row: Export FBX... (as now) and a new **Save scene...**.

- `window.picked_folders()`: the picked folder rows (Folders mode only; List mode none).
- **One folder picked**: a name prompt (`cmds.promptDialog`, the default the scene's short name, else the
  first picked animation's name, else `animation`; `.fbx` / `.ma` added, a typed extension dropped; Windows'
  forbidden characters turned into `_`), then the file written straight into the folder's disk path. A file
  already there is asked about once (Overwrite / Cancel). The folder missing on disk is refused by name.
- **No folder picked**: the save dialog, as Export FBX does today (Save scene: `fileDialog2` with `.ma`/`.mb`).
- **Several folders picked**: «pick one folder - N are picked», nothing written.
- Export writes through `animexport.export_hierarchy(path)` (unchanged). Save scene: with Scene Tabs on, the
  active tab through `maya_scenetabs.saving.save_tab(path=...)`; off, `cmds.file(rename=path)` +
  `cmds.file(save=True, type="mayaAscii"|"mayaBinary")`.
- The labels follow the pick: «Export FBX to Chars...», «Save scene to Chars...» (the folder's last
  name, elided past 24 characters), else «Export FBX...», «Save scene...». Repainted by `paint_import`.
- The status line says what was written and where.

## 4. The right-click menu on a row

A `cmds.popupMenu` on the list (works in the skinned hub and the classic one), its rows made on every open
(`postMenuCommand`) for the row under the mouse, NOT the selection:

- the row: `listdrag`'s event filter remembers the row index of the last right press (`_STATE["menu_row"]`);
  without Qt, the first picked row; outside every row, a menu of one disabled row «no file here»;
- every row: **Show in Explorer** - a file: `explorer /select,<path>`; a folder: `explorer <path>`;
- a folder row also: **Export FBX here...** and **Save scene here...**, the same as §3 with that folder;
- a path that does not exist on disk: its rows disabled, the first reading «not on disk: <path>».
- The rows are built by a pure `window.menu_rows(row, source, root, content_dir, exists)` -> [(label,
  action key, enabled)] and run by `window.run_menu(key, row)`.

## Units

- `foldertree.py`: `disk_path`, `safe_file_name(text, ext)`.
- `window.py`: the click rules (§1), `picked_folders`, `export_fbx_selected` / `save_scene_selected`
  taking the picked folder, `_into_folder(folder, ext, write)`, the labels in `paint_import`, the popup menu.
- `listdrag.py`: the right press records the row (`on_right(row)` callback set by the window).

## Proof

- `tests/test_uebridge_foldertree.py`: `disk_path` for each source, an Unreal folder and a uasset, no
  content dir; `safe_file_name`.
- `tests/test_uebridge_window.py` (the fake `cmds`): a click picks a folder and opens nothing; a double click
  on a lone picked folder toggles it and imports nothing; a double click with animations imports; a rebuild
  keeps a picked folder and animations; Export and Save with one folder write there (the prompt and the
  confirm stubbed, the writer recorded), with none open the dialog, with two refuse; an existing file asked,
  Cancel writes nothing; the labels; `menu_rows` for a file, a folder, a missing path.
- `tests/test_uebridge_listdrag.py`: a right press records the row.
- Not seen in a GUI Maya: the popup over the list, Explorer opening, the prompt - the animator's check after
  Check update.

## Not built

Creating, renaming or deleting folders; Export to uasset into a folder (a new AnimSequence); Show in Explorer
for Shared / Stash rows; an animation's own folder counting as the target.
