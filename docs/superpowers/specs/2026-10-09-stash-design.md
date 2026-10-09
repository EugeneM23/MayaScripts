# Stash: a local scratch shelf for scenes and FBX files

Date: 2026-10-09
Status: built on the working tree (not committed; the animator reviews first)

## The ask

The animator, asked for a Stash tab: «сделать раздел в котором будет список
сцен или файлов (так как сейчас у нас сделано с разделом shared). Только в
отличии от общей шары это будет локальное хранилище ... быстро сохранять
какие-то черновики и промежуточные файлы а потом их открывать или
импортировать и в этом процессе нам не приходилось бы тратить много
усилий».

So: the Shared section's list and its Open / Import / Save to... / Delete
row, but nothing leaves the machine. A draft is one press to keep and one
press to bring back.

## Decisions taken without a question round

The animator is away and has asked for the build to be finished without
approval gates. Each choice below is the one a reviewer can most easily
change.

1. **The store is a plain folder** `<userAppDir>/SkeldarStash/`, flat, one
   file per item. The file system is the truth: no index file, nothing to
   fall out of step with it. The animator can open the folder in Explorer
   and see exactly what is there.
2. **Items are `.ma`, `.mb`, `.fbx`** - the same kinds Shared sends.
3. **Stash scene** writes a COPY of the open scene into the folder
   (`cmds.file(..., exportAll=True)`, as Shared does). The working file, its
   name and its modified flag are untouched. Without a typed Name the copy is
   called `<scene stem>_HHMM` (or `untitled_HHMM`). A name already taken gets
   ` (2)`, ` (3)` ... - a second press on the same draft never overwrites the
   first.
4. **Stash file...** copies a picked `.ma`/`.mb`/`.fbx` in, under the same
   naming rule.
5. **Open** opens a stash scene as the scene, through the open helper the
   Open scene menu already uses (`maya_scenesetup.opener.open_path`, extracted
   from `open_asset`): a modified scene gets Maya's «save changes?», script
   nodes do not run, the ranges are read from the scene configuration node,
   the vaccine is swept, the plugin's images are relinked. The scene opened
   from the stash IS the stash file: Ctrl+S writes the draft back. That is
   the point of a draft, and the line says so. An FBX opens as a new scene
   through `fbximport.open_file` (trap 33's guard).
6. **Import** brings a scene's contents into the open scene (every script
   node removed, as Shared does for an import) or an FBX as its own skeleton
   in a namespace (`animimport.import_clip`, as Shared does).
7. **Save to...** copies a stash item out to a place the animator picks.
8. **Delete** removes the picked stash files from this disk, after a Maya
   confirm that names them. **It refuses the scene open in this Maya** (named
   in the line; nothing deleted for it), because deleting the file under an
   open draft would leave Save to recreate it silently. Cancel changes nothing.
9. **Show folder** opens the stash folder in Explorer (`os.startfile`).
   Nothing else in the plugin does this, so it is the one escape hatch.
10. **No Rename.** Names are set at stash time. A rename would be one more
    thing to get wrong quickly; a copy under a new name is one press too.
11. **No Shared hand-off.** Sending a stash item to everybody is a different
    feature (the animator asked for local). It can come later as a button.
12. **The hub** gets a section `stash`, label «Stash», group **Scene**, right
    after Shared, icon `archive` (a new Tabler outline icon). Its hotkey row
    is `window.stash`, the same as the other cards.
13. **Nothing is ever opened by itself**, and nothing is sent anywhere.

## Architecture

Two new modules, one small extraction.

| module | does | imports |
|---|---|---|
| `SkeldarAnim/maya_stashstore.py` | the folder's rules, pure: the file kinds, a unique name, the listing (newest first), the row and subtitle text, the delete question, the scene file name | stdlib + `maya_sharerecords` (the name and size rules, shared on purpose) |
| `SkeldarAnim/maya_stash.py` | the hub card: the Name field, Stash scene / Stash file..., the list, Open / Import / Save to... / Show folder / Delete, the status line; the `cmds` glue | `maya.cmds`, `maya_stashstore`, `maya_scenesetup.opener` and `maya_uebridge.animimport` (lazy) |
| `SkeldarAnim/maya_scenesetup/opener.py` (changed) | `open_path(path)` extracted from `open_asset`: returns `(opened, note)`; `open_asset` keeps its message | unchanged |

The FBX import (`_import_fbx` in `maya_share`) is six lines; `maya_stash`
carries its own copy rather than reaching into a private function of another
section. The scene import (every script node out) is also local.

## Where it sits in the hub

- `maya_hub.SECTIONS`: `Section("stash", "Stash", "maya_stash", "build_panel",
  "skeldarHubFrameStash", "scene", "archive")` after `shared`.
- `maya_hubicons.ICONS["archive"]`: Tabler outline `archive`.
- `install._PAYLOAD`: `maya_stashstore.py`, `maya_stash.py`, after the Shared
  rows.
- `maya_hotkeys.COMMANDS`: `("window.stash", "Windows", "Stash", ...)`.

## Panel

Top to bottom, the same shape as Shared so the two read alike:

- the subtitle: «N files on this machine - nothing is sent»;
- the **Name** field (placeholder «name (empty: the scene's)») - one row;
- **Stash scene** (primary) and **Stash file...** (secondary);
- the list (several rows picked; a double click opens; Delete key deletes);
- **Open** (secondary), **Import** (secondary), and icon-only **Save to...**,
  **Show folder**, **Delete** (danger) - the skin's compact row;
- the status line.

The list is rebuilt from the folder on build and after every action. Picked
rows are kept by path across a rebuild.

## Edge cases

- An empty Name on Stash scene of an untitled scene: `untitled_HHMM.ma`.
- The Name is cleared after a stash, as Shared clears it after a send.
- A name with Windows' forbidden characters or a device name: the
  `upload_name` rules.
- A file in the folder that is not `.ma`, `.mb` or `.fbx`, or a `.part`
  leftover: not listed.
- The folder does not exist yet: it is created by the first stash; an empty
  folder lists nothing.
- Open of a stash file that vanished meanwhile (deleted by hand): the line
  says so and the list refreshes.
- Several picked: Open, Import, Save to... name the count and take none.
- Delete of the open scene: refused, named, nothing deleted.

## Testing

- `tests/test_stashstore.py` - pure: kinds, unique names (taken, case,
  extension kept), listing order and filters, row and subtitle text, the
  delete question, the scene file name, purity (no `maya`).
- `tests/test_stash.py` - the section on a recording `cmds` (the `uifakes`
  pattern of `test_share`): stash a scene twice (two files, the first
  untouched), stash a file, open a scene (script nodes off, ranges applied),
  open an FBX (import guard), import a scene (script nodes gone), import an
  FBX (namespace), save to, delete (confirm, the open scene refused), show
  folder, picked-count refusals, the panel's named controls.
- `tests/test_opener.py` cases stay green after `open_path` is extracted.
- Registration: the hub's section order and group, the icon, the payload
  rows, the hotkey row (the `window.*` count goes up by one).
- A mayapy standalone verify (`docs/superpowers/plans/verify_stash.py`):
  scratch `MAYA_APP_DIR`, a real stash of the open scene, a real open and
  import, a real delete, the working scene's name and modified flag checked
  before and after. Written and run in a disposable Maya if time allows.
