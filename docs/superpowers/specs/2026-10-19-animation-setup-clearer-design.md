# Animation Setup, made clearer (variant A)

The animator, 2026-10-19: «Давай переделаем меню animation setup и сделаем его более понятным»,
then «Пердложи разные макеты в нашем стиле». Three clickable mockups
(https://claude.ai/artifact/WRzYdrKnKmDKqCHqJjCZcM): A two numbered steps, B three tabs, C a sentence.
Chosen: **A**.

## What read unclearly

- Two orange buttons both called Import (a character, an animation).
- The [Rig | Skeleton] switch also decided what the animation import made, with nothing saying so.
- Delete, Camera, the timeline clock, FBX and uasset were bare icons; «Onto sel.» / «New» clipped words.
- The exports shared the import's row.

## The card now

1. **1 · Character** (classic: «1. Character»)
   - `Type [Rig | Skeleton]` - a `label` before the segments.
   - The portraits.
   - `[Add Manny rig] [Camera] [Delete]` - words in both hubs. Add names what it brings
     (`maya_charlook.add_label`, `maya_scenesetup.window.add_label`), a bare «Add» when the portrait
     has nothing of that kind (Auto, Orc D's skeleton).
2. **2 · Animation** (classic: «2. Animation»; the classic hub keeps its inset)
   - `From [Unreal | Unity | Folder]`, the editor dropdown, search, the list and its grip.
   - `Put it on [Selected rig | A new rig]` - the words follow the kind (`records.target_labels`).
   - «Set the timeline to the clip» - a chip in words.
   - ONE Import button naming the clip and where it goes (`records.import_label`, ≤ 44 characters so
     it never widens the dock: «Import A_Jump → selected rig», «Import 3 animations → 3 new Manny rigs»).
   - «Export ▸» folds the two exports («Export FBX...», «Export to uasset») under it, remembered in
     `ueAnimBridgeExportOpen` (folded by default).
3. The status line.

`maya_uebridge.window.paint_import()` repaints the segments and Import's words; it reads no scene and
never raises. Called on a row click (`selectCommand`), a target segment, `_repopulate`, and through
`scenesetup.window._paint_labels` on a portrait or kind change.

Nothing the card does changed: the same presses, modes, drags and refusals.

## Proof

Unit tests (the layout pinned in `test_hub_sections`, the label helpers in `test_uebridge_records` and
`test_charlook`); the suite 7596 OK. Not seen in a GUI Maya: the animator's to try after Check update.
