# Animation Setup: the animation list as a folder tree (2026-10-23)

The animator: «Нужно прокачать наш Animation setup и сделать режим в котором я буду видеть структуру
папок». Asked, and answered:

- **The tree inside the list**: the same Maya list, not a Content-Browser pair of panes and not a
  one-folder breadcrumb view.
- **A folder only opens and closes.** Selecting a folder does NOT select its animations. Import and a
  drag act on the animations picked by hand, as now.

Approach A of two: the tree is drawn as rows of the existing `cmds.textScrollList` (`_LIST`), so the
selection, Ctrl / Shift, the double click, the drag to a viewport (`listdrag`), the square of several
and the green / checked row marks keep working, in the skinned hub and the classic one. Approach B, a
Qt tree laid over the card (the portraits' pattern), was turned down: more to rebuild, a fallback
needed for the classic hub.

## What the animator sees

- **A switch `[List | Folders]`** in the search row (two segments, the hub's `segments` role), the
  choice in the optionVar `ueAnimBridgeListMode` (`"list"` / `"folders"`, List by default). It applies
  to every source: Unreal, Unity, Folder.
- **List** is today's list, untouched.
- **Folders**: one row a folder or an animation, indented two spaces a level.
  - A folder row: `▸ Longsword  (118)` closed, `▾ Longsword  (118)` open; the count is every animation
    below it, subfolders included.
  - An animation row: its name and length (no folder column - the tree says where it is), the same
    marks as in List.
  - Folders first, then animations, each by name (case-insensitive).
- **A click on a folder row** opens or closes it; the folder row is taken out of the selection at once
  and the animations picked before stay picked (by identity, as the rebuild already keeps them).
- **A double click on a folder row** does the same, never an import.
- **The open folders are remembered** per source and place (the Unreal project, the Unity project, the
  folder) in the optionVar `ueAnimBridgeOpenFolders` (JSON `{place key: [folder paths]}`, at most 20
  places kept, oldest dropped). The first time a place is shown, only the top level is listed (every
  folder closed).
- **Search** in Folders shows only the branches holding a match and opens them all while the search
  field is not empty; the remembered open set is not changed by a search, and clearing the field shows
  it again.
- **The status line** keeps its words («619 animations», «12 of 619 shown»).

## Where a record's folders come from

`foldertree.folder_of(record, root)`:

- **Unreal**: the package without its last part, the leading `/` dropped
  (`/Game/Characters/Mannequins/Anims/A_Jump` -> `Game/Characters/Mannequins/Anims`).
- **Unity**: the file's path relative to the project folder (`Assets/...`); a clip of a model's
  `.meta` lives in the model's folder (the record's `path`).
- **Folder**: the file's path relative to the chosen folder; a file in the folder itself is at the top.
- A path that is not under its root (it should not happen) keeps its whole path, slashes forward.

**A chain of folders holding only one folder and no animation** is joined into one row
(`Game/Characters/Mannequins`), so the animator does not open five empty levels. The joined row opens
and closes as one; its remembered path is the deepest folder of the chain.

## Units

- **`maya_uebridge/foldertree.py`** (stdlib, pure, a subprocess test pins it imports nothing of Maya):
  - `folder_of(record, root)`;
  - `build(records, root)` -> the tree (folders with children, animations, counts), the chains joined;
  - `rows(tree, open_paths, query)` -> the flat rows top down, each `Row(kind, depth, path, label,
    record)` (`kind` `"folder"` / `"anim"`; `record` None for a folder). With a query: only branches
    with a match (`records.filter_records`' rule: every term in name + package), every folder open;
  - `row_text(row)` -> the line for the list (`▸` / `▾`, the indent, the count; an animation's name and
    length through `records`' own width rules);
  - `toggled(open_paths, path)`, `place_key(source, place)`, and the JSON memory's read / write rules
    (a broken value reads as empty, the 20-place cap).
- **`maya_uebridge/window.py`**:
  - the switch's builder and its memory;
  - `_repopulate`: in Folders it fills the list from `foldertree.rows`, and `_STATE["filtered"]` holds
    one entry a ROW - the record for an animation, `None` for a folder - so an index still maps to a row;
  - `_selected_records` skips `None` rows; `selectCommand` first looks for a picked folder row,
    toggles it (`toggled`), writes the memory, rebuilds, and keeps the picked animations;
  - the double click on a folder row toggles instead of importing;
  - `records.format_row` is unchanged; the green / ✓ marks are painted by the row's record.
- **`maya_uebridge/listdrag.py`**: `carried_rows` and the press skip `None` rows; a drag started on a
  folder row carries nothing and does nothing.

## Not built

A folder's own import, folder icons or an expand animation, a two-pane view, opening every folder at
once (a button or a key), drag between folders, folders for Shared / Stash.

## Proof

- `tests/test_uebridge_foldertree.py`: `folder_of` for each source; a chain joined and opened as one;
  counts with subfolders; folders before animations; rows for an open set; the search showing only the
  matching branches, all open, and leaving the open set alone; the memory's cap and a broken value;
  the module imports nothing of Maya.
- `tests/test_uebridge_window.py`: on the fake `cmds`, the switch remembered; Folders fills folder and
  animation rows; a folder click toggles and keeps the picked animations; a double click on a folder
  imports nothing; `_selected_records` gives the picked animations only; List unchanged.
- `tests/test_uebridge_listdrag.py`: a drag from a folder row carries nothing; picked animations under
  folders are carried.
- Not seen in a GUI Maya: the animator's live check after Check update (the 360 px dock, the arrows'
  glyphs in Maya's list font).
