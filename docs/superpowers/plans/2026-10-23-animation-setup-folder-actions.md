# Animation Setup folder actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In Animation Setup's Folders mode a click picks a folder (a double click opens it), Export FBX... and a new Save scene... write straight into the one picked folder, and a right click on any row offers Show in Explorer (plus Export / Save here on a folder).

**Architecture:** The pure halves go in `maya_uebridge/foldertree.py` (`disk_path`, `safe_file_name`) and as pure functions in `window.py` (`folder_label`, `menu_rows`). `window.py` gets the new click rules, the folder-aware export/save presses and a `cmds.popupMenu` on the list. `listdrag.py`'s Qt event filter records which row a right press landed on, so the menu acts on the row under the mouse, not the selection.

**Tech Stack:** Maya 2027 `maya.cmds`, PySide6 (only in `listdrag`), stdlib `unittest` run by `mayapy`.

Spec: `docs/superpowers/specs/2026-10-23-animation-setup-folder-actions-design.md`.

## Global Constraints

- Work on `main`. Other sessions keep uncommitted files in this repo: commit ONLY the files a task names, `git commit -F <msgfile> -- <paths>`. Never `git add -A`, never push (pushing is asked separately).
- Every commit message ends with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Tests: from the repo root `C:/!!!Work/MayaScripts`, run `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest <module> -v`. There is no system Python (`python` hangs). For Qt tests set `QT_QPA_PLATFORM=offscreen` first.
- Python that contains backslashes (regexes) is written with the Write/Edit tools, never through a Bash heredoc (a heredoc turns `\\` into `\`).
- `foldertree.py` stays pure: stdlib and `records` only (a subprocess test pins it).
- `window.py` talks to Maya only through its module-level `cmds` (tests swap it for a fake).
- Slashes in every path the new code returns are forward, with no trailing slash.
- Messages are lowercase-first status lines in the bridge's existing voice («export cancelled», «pick one folder - 2 are picked»).
- No live GUI Maya, no command port, no install: the GUI check is the animator's.

---

### Task 1: `foldertree.disk_path` and `safe_file_name`

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/foldertree.py` (add after `folder_of`; add `import os` and `import re`)
- Test: `tests/test_uebridge_foldertree.py` (append two classes)

**Interfaces:**
- Consumes: `foldertree.Row(kind, depth, path, label, record, count, opened)`, `records.AnimRecord` (fields used: `name`, `package`, `source`, `path`), `records.uasset_path_of(package, content_dir)` (returns an `os.path.join` path - backslashes on Windows).
- Produces:
  - `disk_path(row, source, root, content_dir) -> str` - "" when the row has no place on disk.
  - `safe_file_name(text, ext, allowed=()) -> str` - a file name ending in `ext` (or a typed extension listed in `allowed`).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_uebridge_foldertree.py` (it already imports `foldertree` and `records`; check the top of the file and reuse its imports):

```python
class DiskPath(unittest.TestCase):

    def folder(self, path):
        return foldertree.Row("folder", 0, path, path.rsplit("/", 1)[-1],
                              None, 1, False)

    def anim(self, record):
        return foldertree.Row("anim", 0, "", record.name, record, 1, False)

    def test_an_unreal_folder_is_under_the_content_dir(self):
        self.assertEqual(foldertree.disk_path(
            self.folder("Game/Chars/Hero"), "unreal", "", "C:/P/Content"),
            "C:/P/Content/Chars/Hero")

    def test_the_game_folder_is_the_content_dir_itself(self):
        self.assertEqual(foldertree.disk_path(
            self.folder("Game"), "unreal", "", "C:\\P\\Content\\"),
            "C:/P/Content")

    def test_another_mount_or_no_content_dir_has_no_place(self):
        self.assertEqual(foldertree.disk_path(
            self.folder("Engine/Anims"), "unreal", "", "C:/P/Content"), "")
        self.assertEqual(foldertree.disk_path(
            self.folder("Game/Chars"), "unreal", "", ""), "")

    def test_an_unreal_animation_is_its_uasset(self):
        record = records.AnimRecord("Walk", "/Game/Chars/Walk", "", 30, 1.0, 30.0)
        self.assertEqual(foldertree.disk_path(
            self.anim(record), "unreal", "", "C:/P/Content"),
            "C:/P/Content/Chars/Walk.uasset")

    def test_a_file_source_folder_is_under_its_root(self):
        for source in ("folder", "unity"):
            self.assertEqual(foldertree.disk_path(
                self.folder("walks/fast"), source, "C:\\clips\\", ""),
                "C:/clips/walks/fast")

    def test_a_file_animation_is_its_file(self):
        record = records.AnimRecord("W", "C:/clips/walks/W.fbx", "", 24, 1.0,
                                    30.0, "folder", "C:\\clips\\walks\\W.fbx",
                                    "", "fbx")
        self.assertEqual(foldertree.disk_path(self.anim(record), "folder",
                                              "C:/clips", ""),
                         "C:/clips/walks/W.fbx")

    def test_no_row_and_no_root_have_no_place(self):
        self.assertEqual(foldertree.disk_path(None, "folder", "C:/c", ""), "")
        self.assertEqual(foldertree.disk_path(
            self.folder("walks"), "folder", "", ""), "")


class SafeFileName(unittest.TestCase):

    def test_the_extension_is_added(self):
        self.assertEqual(foldertree.safe_file_name("Hero walk", ".fbx"),
                         "Hero walk.fbx")

    def test_a_typed_extension_is_not_doubled(self):
        self.assertEqual(foldertree.safe_file_name("hero.FBX", ".fbx"),
                         "hero.fbx")

    def test_an_allowed_typed_extension_wins(self):
        self.assertEqual(foldertree.safe_file_name(
            "hero.mb", ".ma", (".ma", ".mb")), "hero.mb")
        self.assertEqual(foldertree.safe_file_name(
            "hero", ".ma", (".ma", ".mb")), "hero.ma")

    def test_forbidden_characters_become_underscores(self):
        self.assertEqual(foldertree.safe_file_name('a<b>c:d"e/f\\g|h?i*', ".fbx"),
                         "a_b_c_d_e_f_g_h_i_.fbx")

    def test_dots_spaces_and_devices(self):
        self.assertEqual(foldertree.safe_file_name("  ..walk.  ", ".fbx"),
                         "walk.fbx")
        self.assertEqual(foldertree.safe_file_name("", ".fbx"), "animation.fbx")
        self.assertEqual(foldertree.safe_file_name("con", ".fbx"), "_con.fbx")
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_foldertree -v`
Expected: the new tests fail with `AttributeError: module 'maya_uebridge.foldertree' has no attribute 'disk_path'` (and `safe_file_name`).

- [ ] **Step 3: Implement** (write with the Edit tool: the regex has backslashes)

In `foldertree.py` add `import os` and `import re` to the imports, then after `folder_of`:

```python
def _clean(path):
    """`path` with forward slashes and no trailing slash ("" stays "")."""
    text = _slashed(path)
    return text.rstrip("/") if text.strip("/") else text


def disk_path(row, source, root, content_dir):
    """Where the list row `row` lives on disk, "" when it has no place.

    A folder: Unreal's `Game/<rest>` under `content_dir` (another mount, or no
    `content_dir` from an old cache, has none); a file source's under `root`
    (the chosen folder, the Unity project). An animation: its uasset, or its
    file. Slashes forward, no trailing slash."""
    if row is None:
        return ""
    if row.kind != "folder":
        record = row.record
        if record is None:
            return ""
        if source == "unreal" or not record.path:
            if not content_dir:
                return ""
            return _clean(records.uasset_path_of(record.package, content_dir))
        return _clean(record.path)
    if source == "unreal":
        parts = [p for p in _slashed(row.path).split("/") if p]
        if not content_dir or not parts or parts[0].lower() != "game":
            return ""
        base = _clean(content_dir)
        return "/".join([base] + parts[1:])
    if not root:
        return ""
    base = _clean(root)
    rest = _slashed(row.path).strip("/")
    return base + "/" + rest if rest else base


_BAD_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_DEVICES = set(["CON", "PRN", "AUX", "NUL"]
               + ["COM%d" % n for n in range(1, 10)]
               + ["LPT%d" % n for n in range(1, 10)])


def safe_file_name(text, ext, allowed=()):
    """A file name from what the animator typed: whitespace collapsed, a typed
    `ext` (or one of `allowed`, which then wins) not doubled, Windows'
    forbidden characters as "_", leading and trailing dots and spaces gone, a
    device name prefixed with "_", nothing at all named "animation"."""
    name = " ".join((text or "").split())
    chosen = ext
    for known in tuple(allowed) + (ext,):
        if name.lower().endswith(known.lower()):
            name = name[:-len(known)]
            chosen = known.lower()
            break
    name = _BAD_NAME.sub("_", name).strip(". ")
    if not name:
        name = "animation"
    if name.split(".")[0].strip().upper() in _DEVICES:
        name = "_" + name
    return name + chosen
```

Note `os` is only needed if you use it; `records.uasset_path_of` already joins. If `os` ends up unused, do not import it.

- [ ] **Step 4: Run the tests to see them pass**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_foldertree -v`
Expected: every test OK, the purity test included.

- [ ] **Step 5: Commit**

Write the message to a scratch file (`msg.txt`):

```
feat(uebridge): where a folder-tree row lives on disk, and a safe file name

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

Run: `git commit -F msg.txt -- SkeldarAnim/maya_uebridge/foldertree.py tests/test_uebridge_foldertree.py`

---

### Task 2: A click picks a folder, a double click opens it

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/window.py` - the comment block at lines ~97-107 (`DOUBLE_S`, `_now`), `_STATE` (line ~119), `_repopulate` (~270), `_remember_selection` / `_pick_packages` (~321-338, delete), `_on_select` / `_on_double` (~349-409, rewrite), the list's annotation in `build_rows` (~1414), `LIST_MODES`' folders note.
- Test: `tests/test_uebridge_window.py`, class `FolderTree` (~970-1165).

**Interfaces:**
- Consumes: `foldertree.Row`, `foldertree.toggled(open_paths, path)`, the module's `_open_folders()`, `_save_open(paths)`, `list_mode()`, `_selected_records()`, `import_selected`, `_import_busy()`.
- Produces: `window.picked_folders() -> list[foldertree.Row]` - the picked folder rows in list order (Folders mode only; `[]` in List mode). Tasks 3 and 4 use it.

- [ ] **Step 1: Rewrite the FolderTree click tests**

In `tests/test_uebridge_window.py`, class `FolderTree`:

1. In `setUp` remove the clock: drop `window._now` from `saved` and from `put_back`, and delete the three lines `self.clock = [100.0]` / `window._now = lambda: ...`. The new `setUp` saves and restores `(window.cmds, dict(window._STATE), window._status, window.paint_import)`.
2. Delete these tests (they pin the old rules): `test_a_folder_click_opens_it_remembers_it_and_leaves_it_unpicked`, `test_picked_animations_stay_picked_across_a_folder_click`, `test_the_second_click_of_a_double_click_does_not_close_it_again`, `test_a_double_click_on_a_folder_imports_nothing`, `test_a_double_click_on_an_animation_still_imports`, `test_a_folder_click_during_a_search_changes_nothing`, `test_a_plain_folder_click_keeps_the_animations_picked_before`, `test_a_shift_range_over_several_folders_toggles_none`, `test_a_folder_already_picked_is_not_toggled_again`, `test_a_double_click_on_an_animation_soon_after_a_folder_imports`, and the old `_open_chars` helper.
3. Keep `test_list_is_the_default_and_unchanged`, `test_the_mode_is_remembered`, `test_folders_mode_fills_folder_rows_closed_at_first`, `test_a_search_opens_every_matching_branch_and_keeps_the_memory`, `_imports`, `test_list_mode_double_click_with_nothing_picked_still_imports`, `test_a_file_source_is_a_tree_under_its_folder`.
4. Add:

```python
    def _open_chars(self):
        """Game, then Chars, opened by double clicks: rows Game, Chars, Run,
        Walk, Props."""
        window.set_list_mode("folders")
        self.fake.picked = [1]
        window._on_double()
        self.fake.picked = [2]
        window._on_double()
        self.fake.picked = []

    def test_a_click_picks_a_folder_and_opens_nothing(self):
        window.set_list_mode("folders")
        self.fake.picked = [1]
        window._on_select()
        self.assertEqual(self.fake.lines, ["\u25b8 Game  (3)"])
        self.assertEqual(self.fake.picked, [1])
        self.assertNotIn(self.foldertree.OPEN_VAR, self.fake.vars)
        self.assertEqual([r.path for r in window.picked_folders()], ["Game"])

    def test_a_double_click_on_a_lone_folder_opens_it_and_imports_nothing(self):
        imported = self._imports()
        window.set_list_mode("folders")
        self.fake.picked = [1]
        window._on_double()
        self.assertEqual(self.fake.lines[0], "\u25be Game  (3)")
        self.assertEqual(imported, [])
        key = self.foldertree.place_key("unreal", "Atone")
        self.assertEqual(self.foldertree.read_open(
            self.fake.vars[self.foldertree.OPEN_VAR], key), {"Game"})
        self.assertEqual(self.fake.picked, [1])     # still picked, by path

    def test_a_second_double_click_closes_it(self):
        window.set_list_mode("folders")
        self.fake.picked = [1]
        window._on_double()
        window._on_double()
        self.assertEqual(self.fake.lines, ["\u25b8 Game  (3)"])

    def test_a_double_click_with_an_animation_picked_imports(self):
        imported = self._imports()
        self._open_chars()
        before = list(self.fake.lines)
        self.fake.picked = [2, 3]                 # Chars and Run
        window._on_double()
        self.assertEqual(imported, [True])
        self.assertEqual(self.fake.lines, before)

    def test_a_double_click_with_two_folders_goes_to_import(self):
        imported = self._imports()
        self._open_chars()
        self.fake.picked = [2, 5]                 # Chars and Props
        window._on_double()
        self.assertEqual(imported, [True])        # it says «select an animation»

    def test_picked_folders_never_import(self):
        self._open_chars()
        self.fake.picked = [2, 3]
        self.assertEqual([r.name for r in window._selected_records()], ["Run"])
        self.assertEqual([r.path for r in window.picked_folders()],
                         ["Game/Chars"])

    def test_a_rebuild_keeps_picked_folders_and_animations(self):
        self._open_chars()
        self.fake.picked = [3, 5]                 # Run and Props
        window._repopulate(quiet=True)
        self.assertEqual(self.fake.picked, [3, 5])

    def test_a_double_click_on_a_folder_during_a_search_changes_nothing(self):
        window.set_list_mode("folders")
        self.fake.text = "spin"
        window._repopulate(quiet=True)
        self.fake.picked = [1]
        window._on_double()
        self.assertNotIn(self.foldertree.OPEN_VAR, self.fake.vars)
        self.assertEqual(self.fake.lines[0], "\u25be Game/Props  (1)")

    def test_list_mode_has_no_picked_folders(self):
        window._repopulate(quiet=True)
        self.fake.picked = [1]
        self.assertEqual(window.picked_folders(), [])
```

- [ ] **Step 2: Run them to see them fail**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_window.FolderTree -v`
Expected: the new tests fail (`picked_folders` missing; a click still opens; a double click does not).

- [ ] **Step 3: Implement**

In `window.py`:

1. Replace the comment above `_LIST_MODE` with:

```python
#  2026-10-23 («режим в котором я буду видеть структуру папок»): the list as
#  a folder tree in the same Maya list (`foldertree`). A click picks a folder
#  like any row, a double click on a lone picked folder opens or closes it
#  («Клик выделяет, двойной раскрывает»); a picked folder never imports.
```

and the folders note in `LIST_MODES` to `"The animations in their folders: a double click opens or closes a folder"`. Delete `DOUBLE_S` and `_now = time.monotonic`. Run `grep -n "time\." SkeldarAnim/maya_uebridge/window.py`: if nothing but the docstring uses `time`, delete `import time`.

2. `_STATE`: remove the keys `"last_toggle"`, `"last_click"`, `"picked"`, `"prev_sel"`.

3. Delete `_remember_selection` and `_pick_packages`.

4. In `_repopulate`, replace the keep block and the re-select loop:

```python
    previous = _STATE.get("filtered") or []
    previous_rows = _STATE.get("tree_rows") or []
    picked = cmds.textScrollList(_LIST, query=True,
                                 selectIndexedItem=True) or []
    keep = set(previous[i - 1].package for i in picked
               if 0 < i <= len(previous) and previous[i - 1] is not None)
    keep_folders = set(previous_rows[i - 1].path for i in picked
                       if 0 < i <= len(previous_rows)
                       and previous_rows[i - 1].kind == "folder")
```

and after the `append` loop:

```python
    for index, record in enumerate(entries, 1):
        if record is not None and record.package in keep:
            cmds.textScrollList(_LIST, edit=True, selectIndexedItem=index)
        elif (record is None and index <= len(tree_rows)
              and tree_rows[index - 1].path in keep_folders):
            cmds.textScrollList(_LIST, edit=True, selectIndexedItem=index)
```

Remove the `_remember_selection()` call there (keep `paint_import()`). Update the comment «A folder row (None) is never kept.» to «A folder row is kept by its path.».

5. Add after `_selected_records`:

```python
def picked_folders():
    """The picked folder rows, in list order (Folders mode; none in List)."""
    if list_mode() != "folders":
        return []
    rows = _STATE.get("tree_rows") or []
    indices = cmds.textScrollList(_LIST, query=True,
                                  selectIndexedItem=True) or []
    return [rows[i - 1] for i in sorted(indices)
            if 0 < i <= len(rows) and rows[i - 1].kind == "folder"]


def _searching():
    return bool((cmds.textField(_SEARCH, query=True, text=True)
                 if cmds.textField(_SEARCH, exists=True) else "").strip())
```

6. Replace `_on_select` and `_on_double`:

```python
def _on_select():
    """A row click picks it - a folder too, nothing opens; the words that
    follow the pick are repainted."""
    paint_import()


def _on_double():
    """A double click on exactly one picked folder with no animation picked
    opens or closes it (not during a search, which shows every match open);
    any other double click imports the picked animations."""
    if list_mode() == "folders":
        folders = picked_folders()
        if len(folders) == 1 and not _selected_records():
            if not _searching():
                _save_open(foldertree.toggled(_open_folders(), folders[0].path))
                _repopulate(quiet=True)
            return
    _run(import_selected, busy=_import_busy())
```

7. The list's `annotation` in `build_rows`: replace its last sentence «In Folders, a click on a folder opens or closes it.» with «In Folders, a click picks a folder (Export and Save write into it), a double click opens or closes it; the right button shows a row in Explorer.».

- [ ] **Step 4: Run the bridge tests**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_window tests.test_uebridge_foldertree tests.test_uebridge_listdrag -v`
(the last needs `QT_QPA_PLATFORM=offscreen`: `QT_QPA_PLATFORM=offscreen "/c/Program Files/..../mayapy.exe" -m unittest ...`)
Expected: all OK. If any other test reads `_STATE["picked"]`, `"prev_sel"`, `"last_click"`, `DOUBLE_S` or `_now`, `grep -rn` for them in `tests/` and remove that reading.

- [ ] **Step 5: Commit**

```
feat(uebridge): a click picks a folder, a double click opens it

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

`git commit -F msg.txt -- SkeldarAnim/maya_uebridge/window.py tests/test_uebridge_window.py`

---

### Task 3: Export FBX... and Save scene... into the picked folder

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/window.py` - constants near `_EXPORT_ROW` (~85), `export_fbx_selected` (~1247), new functions after it, the export row in `build_rows` (~1476-1505), `toggle_export` (~1523), `paint_import` (~1545).
- Test: `tests/test_uebridge_window.py` (a new class `FolderSave` after `FolderTree`, reusing `FakeTreeCmds`).

**Interfaces:**
- Consumes: `picked_folders()` (Task 2), `foldertree.disk_path`, `foldertree.safe_file_name` (Task 1), `current_source()`, `_STATE["location"]`, `_STATE["content_dir"]`, `animexport.export_hierarchy(path) -> info`, `animexport.export_line(name, info) -> str`, `maya_scenetabs.scope.tabs_on()`, `maya_scenetabs.saving.save_tab(path=...)` (returns `session.Cancelled` - a `str` subclass - when cancelled), `session.Cancelled`.
- Produces (Task 4 calls the first two with a folder row):
  - `export_fbx_selected(folder=None)` - `folder` a `foldertree.Row`; None = the picked folder.
  - `save_scene_selected(folder=None)`.
  - `folder_disk(row) -> str` - `disk_path` with this list's source, location and content dir.
  - `folder_label(words, name) -> str` (pure).
  - seams the tests replace: `_ask_name(title, default, folder) -> str | None`, `_ask_overwrite(path) -> bool`, `_isdir(path)`, `_exists(path)`, `_save_scene(path) -> str`.
  - control names `_EXPORT_FBX = "ueAnimBridgeExportFbx"`, `_SAVE_SCENE = "ueAnimBridgeSaveScene"`.

- [ ] **Step 1: Write the failing tests**

Append after class `FolderTree`:

```python
class FolderSave(unittest.TestCase):
    """2026-10-23: Export FBX... and Save scene... write into the picked
    folder, asking only for the name."""

    def setUp(self):
        self.fake = FakeTreeCmds()
        self.said = []
        saved = (window.cmds, dict(window._STATE), window._status,
                 window.paint_import, window._ask_name, window._ask_overwrite,
                 window._isdir, window._exists, window._save_scene)
        window.cmds = self.fake
        window._status = self.said.append
        window.paint_import = lambda: None
        self.asked = []
        self.answer = "Hero walk"
        window._ask_name = lambda title, default, folder: (
            self.asked.append((title, default, folder)) or self.answer)
        self.overwrite = []
        window._ask_overwrite = lambda path: self.overwrite.append(path) or False
        self.dirs = {"C:/clips/walks", "C:/clips/runs"}
        self.files = set()
        window._isdir = lambda path: path in self.dirs
        window._exists = lambda path: path in self.files or path in self.dirs
        self.saved_scenes = []
        window._save_scene = lambda path: self.saved_scenes.append(path) or "saved"

        def put_back():
            (window.cmds, state, window._status, window.paint_import,
             window._ask_name, window._ask_overwrite, window._isdir,
             window._exists, window._save_scene) = saved
            window._STATE.clear()
            window._STATE.update(state)
        self.addCleanup(put_back)
        recs = [records.AnimRecord(n, "C:/clips/{0}/{1}.fbx".format(f, n), "",
                                   24, 1.0, 30.0, "folder",
                                   "C:/clips/{0}/{1}.fbx".format(f, n), "", "fbx")
                for f, n in (("walks", "W"), ("runs", "R"))]
        window._STATE.update(records=recs, filtered=[], source="folder",
                             location="C:/clips", list_mode=None)
        window.set_list_mode("folders")           # rows: runs, walks

        import maya_uebridge.animexport as animexport
        self.exported = []
        saved_export = (animexport.export_hierarchy, animexport.export_line)
        animexport.export_hierarchy = lambda path: self.exported.append(path) or {}
        animexport.export_line = lambda name, info: "exported " + name
        self.addCleanup(lambda: (setattr(animexport, "export_hierarchy", saved_export[0]),
                                 setattr(animexport, "export_line", saved_export[1])))

    def test_one_folder_writes_the_fbx_straight_into_it(self):
        self.fake.picked = [2]                    # walks
        window.export_fbx_selected()
        self.assertEqual(self.exported, ["C:/clips/walks/Hero walk.fbx"])
        self.assertEqual(self.asked[0][2], "C:/clips/walks")
        self.assertIn("C:/clips/walks", self.said[-1])

    def test_the_name_defaults_to_animation_with_no_scene_or_pick(self):
        self.fake.picked = [2]
        window.export_fbx_selected()
        self.assertEqual(self.asked[0][1], "animation")   # no scene, no animation picked

    def test_a_cancelled_name_writes_nothing(self):
        self.answer = None
        self.fake.picked = [2]
        window.export_fbx_selected()
        self.assertEqual(self.exported, [])
        self.assertEqual(self.said[-1], "export cancelled")

    def test_an_existing_file_is_asked_and_kept_on_cancel(self):
        self.files.add("C:/clips/walks/Hero walk.fbx")
        self.fake.picked = [2]
        window.export_fbx_selected()
        self.assertEqual(self.overwrite, ["C:/clips/walks/Hero walk.fbx"])
        self.assertEqual(self.exported, [])
        self.assertIn("kept", self.said[-1])

    def test_a_folder_gone_from_disk_is_refused_by_name(self):
        self.dirs.discard("C:/clips/walks")
        self.fake.picked = [2]
        window.export_fbx_selected()
        self.assertEqual(self.exported, [])
        self.assertEqual(self.said[-1], "not on disk: C:/clips/walks")

    def test_two_folders_refuse(self):
        self.fake.picked = [1, 2]
        window.export_fbx_selected()
        self.assertEqual(self.exported, [])
        self.assertEqual(self.said[-1], "pick one folder - 2 are picked")

    def test_no_folder_opens_the_dialog(self):
        dialogs = []
        self.fake.fileDialog2 = lambda **kw: dialogs.append(kw) or ["C:/x/y.fbx"]
        window.export_fbx_selected()
        self.assertEqual(len(dialogs), 1)
        self.assertEqual(self.exported, ["C:/x/y.fbx"])

    def test_a_given_folder_row_wins_over_the_pick(self):
        self.fake.picked = [1, 2]
        window.export_fbx_selected(folder=window._STATE["tree_rows"][1])
        self.assertEqual(self.exported, ["C:/clips/walks/Hero walk.fbx"])

    def test_save_scene_writes_a_ma_or_the_typed_mb(self):
        self.fake.picked = [2]
        window.save_scene_selected()
        self.answer = "take.mb"
        window.save_scene_selected()
        self.assertEqual(self.saved_scenes, ["C:/clips/walks/Hero walk.ma",
                                             "C:/clips/walks/take.mb"])

    def test_the_labels(self):
        self.assertEqual(window.folder_label("Export FBX", ""), "Export FBX...")
        self.assertEqual(window.folder_label("Save scene", "Chars"),
                         "Save scene to Chars...")
        self.assertEqual(window.folder_label("Export FBX", "A" * 30),
                         "Export FBX to " + "A" * 23 + "\u2026...")
```

`FakeTreeCmds.__getattr__` returns a no-op for anything not defined; an instance attribute (`self.fake.fileDialog2 = ...`) wins over it. Check `animexport` imports cleanly under the fake `maya` (it is already imported lazily by the real `export_fbx_selected`; if its import fails under the fake, patch through `sys.modules["maya_uebridge.animexport"]` with a `types.ModuleType` stand-in holding the two functions instead).

- [ ] **Step 2: Run them to see them fail**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_window.FolderSave -v`
Expected: errors - `_ask_name`, `folder_label`, `save_scene_selected` missing.

- [ ] **Step 3: Implement**

In `window.py`, beside the other control names:

```python
_EXPORT_FBX = "ueAnimBridgeExportFbx"
_SAVE_SCENE = "ueAnimBridgeSaveScene"
LABEL_NAME_MAX = 24        # a folder's name in a button, elided past this
```

Replace `export_fbx_selected` with:

```python
def folder_label(words, name):
    """«Export FBX to Chars...» for a picked folder `name`, «Export FBX...»
    for none; a name past LABEL_NAME_MAX elided. Pure."""
    if not name:
        return words + "..."
    if len(name) > LABEL_NAME_MAX:
        name = name[:LABEL_NAME_MAX - 1] + "\u2026"
    return "{0} to {1}...".format(words, name)


def folder_disk(row):
    """`row`'s folder on disk for this list's source and place."""
    return foldertree.disk_path(row, current_source(),
                                _STATE.get("location") or "",
                                _STATE.get("content_dir") or "")


def _isdir(path):
    return os.path.isdir(path)


def _exists(path):
    return os.path.exists(path)


def _ask_name(title, default, folder):
    """The file's name, asked; None when cancelled."""
    answer = cmds.promptDialog(
        title=title, message="Name in {0}:".format(folder), text=default,
        button=["OK", "Cancel"], defaultButton="OK", cancelButton="Cancel",
        dismissString="Cancel")
    if answer != "OK":
        return None
    return cmds.promptDialog(query=True, text=True)


def _ask_overwrite(path):
    return cmds.confirmDialog(
        title="File exists", message="{0} is already there. Overwrite it?"
        .format(path), button=["Overwrite", "Cancel"], defaultButton="Cancel",
        cancelButton="Cancel", dismissString="Cancel") == "Overwrite"


def _default_name():
    """The scene's name, else the first picked animation's, else
    «animation»."""
    try:
        scene = cmds.file(query=True, sceneName=True, shortName=True) or ""
    except (RuntimeError, TypeError, ValueError):
        scene = ""
    stem = os.path.splitext(scene)[0] if isinstance(scene, str) else ""
    if stem:
        return stem
    chosen = _selected_records()
    return chosen[0].name if chosen else "animation"


def _path_in(row, ext, allowed, title, word):
    """(path, None) where a file goes in the folder `row` - its name asked,
    the folder checked on disk, an existing file confirmed - or (None, why)."""
    folder = folder_disk(row)
    if not folder:
        return None, "{0} is not a folder on disk".format(row.label)
    if not _isdir(folder):
        return None, "not on disk: {0}".format(folder)
    typed = _ask_name(title, _default_name(), folder)
    if typed is None:
        return None, "{0} cancelled".format(word)
    path = folder + "/" + foldertree.safe_file_name(typed, ext, allowed)
    if _exists(path) and not _ask_overwrite(path):
        return None, "{0} cancelled - {1} kept".format(
            word, os.path.basename(path))
    return path, None


def _destination(folder, ext, allowed, title, word, dialog):
    """(path, None) or (None, why). `folder` a folder row; None means the
    picked folder: one writes into it, none opens `dialog()`, several refuse."""
    if folder is None:
        folders = picked_folders()
        if len(folders) > 1:
            return None, "pick one folder - {0} are picked".format(len(folders))
        folder = folders[0] if folders else None
    if folder is None:
        paths = dialog()
        if not paths:
            return None, "{0} cancelled".format(word)
        return paths[0].replace("\\", "/"), None
    return _path_in(folder, ext, allowed, title, word)


def export_fbx_selected(folder=None):
    """A plain FBX of the resolved skeleton (selection, the rig, the sole
    skeleton), baked on export so no rig is ever touched - into the picked
    folder (2026-10-23, «FBX сразу в папку»), else where the dialog says."""
    path, refusal = _destination(
        folder, ".fbx", (".fbx",), "Export FBX", "export",
        lambda: cmds.fileDialog2(fileFilter="FBX (*.fbx)", dialogStyle=2,
                                 fileMode=0, caption="Export skeleton animation"))
    if refusal:
        _status(refusal)
        return
    from maya_uebridge import animexport   # lazy: keeps the import graph flat
    info = animexport.export_hierarchy(path)
    _status("{0} - in {1}".format(
        animexport.export_line(os.path.basename(path), info),
        os.path.dirname(path)))


def _save_scene(path):
    """The scene (the active tab with Scene Tabs on) saved as `path`."""
    try:
        from maya_scenetabs import scope
        tabs = scope.tabs_on()
    except Exception:                                        # noqa: BLE001
        tabs = False
    if tabs:
        from maya_scenetabs import saving, session
        result = saving.save_tab(path=path)
        if isinstance(result, session.Cancelled):
            return str(result)
    else:
        cmds.file(rename=path)
        cmds.file(save=True, type="mayaBinary"
                  if path.lower().endswith(".mb") else "mayaAscii")
    return "saved the scene as {0} - in {1}".format(
        os.path.basename(path), os.path.dirname(path))


def save_scene_selected(folder=None):
    """The scene saved into the picked folder (2026-10-23, «FBX и сцену
    Maya»), else where the dialog says."""
    path, refusal = _destination(
        folder, ".ma", (".ma", ".mb"), "Save scene", "save",
        lambda: cmds.fileDialog2(
            fileFilter="Maya ASCII (*.ma);;Maya Binary (*.mb)", dialogStyle=2,
            fileMode=0, caption="Save scene"))
    if refusal:
        _status(refusal)
        return
    _status(_save_scene(path))
```

The export row in `build_rows`: `_EXPORT_ROW` becomes a `columnLayout` holding two rows - Export FBX + Save scene, then Export to uasset alone (three buttons in one row do not fit the 360 px dock, trap 67):

```python
    cmds.columnLayout(_EXPORT_ROW, adjustableColumn=True, manage=opened,
                      rowSpacing=3)
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 3)])
    hubstyle.mark(cmds.button(
        _EXPORT_FBX, label="Export FBX...",
        height=hubstyle.height("button", 28),
        annotation="Export FBX... - Write the scene skeleton's animation to "
                   "an FBX (selection, else the rig, else the only "
                   "skeleton), baked on export. A folder picked in Folders: "
                   "straight into it, only the name asked.",
        command=lambda *_: _run(export_fbx_selected,
                                busy="writing the fbx...")),
        "secondary", "upload")
    hubstyle.mark(cmds.button(
        _SAVE_SCENE, label="Save scene...",
        height=hubstyle.height("button", 28),
        annotation="Save the scene (the active tab) as a Maya file. A folder "
                   "picked in Folders: straight into it, only the name asked.",
        command=lambda *_: _run(save_scene_selected,
                                busy="saving the scene...")),
        "secondary", "device-floppy")
    cmds.setParent("..")
```

followed by the existing `Export to uasset` button (unchanged, its `width=` removed so it fills the column) and `cmds.setParent("..")` closing the column. Keep the existing `cmds.setParent("..")` that closes the Connect block after it.

`toggle_export`: `cmds.layout(_EXPORT_ROW, exists=True)` / `cmds.layout(_EXPORT_ROW, edit=True, manage=opened)` in place of `cmds.rowLayout`. Run `grep -rn "_EXPORT_ROW\|ueAnimBridgeExportRow" tests/` and fix any test that asks `rowLayout` for it.

`paint_import`: before the `if not cmds.button(_IMPORT, exists=True): return` line add:

```python
        folders = (picked_folders()
                   if cmds.textScrollList(_LIST, exists=True) else [])
        name = (folders[0].label.rsplit("/", 1)[-1]
                if len(folders) == 1 else "")
        for button, words in ((_EXPORT_FBX, "Export FBX"),
                              (_SAVE_SCENE, "Save scene")):
            if cmds.button(button, exists=True):
                cmds.button(button, edit=True,
                            label=folder_label(words, name))
```

- [ ] **Step 4: Run the bridge tests**

Run: `QT_QPA_PLATFORM=offscreen "/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_window tests.test_uebridge_foldertree tests.test_uebridge_listdrag -v`
Expected: all OK. Then `grep -rn "Export FBX\.\.\." tests/` - any test that finds the button by its label now finds it by `_EXPORT_FBX`.

- [ ] **Step 5: Commit**

```
feat(uebridge): Export FBX and a new Save scene write into the picked folder

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

`git commit -F msg.txt -- SkeldarAnim/maya_uebridge/window.py tests/test_uebridge_window.py`

---

### Task 4: The right-click menu: Show in Explorer, Export / Save here

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/listdrag.py` - `Drag.__init__` (~290), `Drag._mouse` (~528), `attach_widget` (~583), `attach` (~610).
- Modify: `SkeldarAnim/maya_uebridge/window.py` - `import subprocess`; new functions after `save_scene_selected`; `build_rows` (a popupMenu after the list's `textScrollList`); `_attach_drag`.
- Test: `tests/test_uebridge_listdrag.py` (class `Drag`), `tests/test_uebridge_window.py` (new class `ListMenu`), and the source check at `test_uebridge_window.py:360` if it pins the attach call's text.

**Interfaces:**
- Consumes: `folder_disk`, `export_fbx_selected(folder=)`, `save_scene_selected(folder=)` (Task 3); `foldertree.disk_path`, `foldertree.Row` (Task 1); `picked_folders` (Task 2).
- Produces:
  - `listdrag.attach(list_name, records_of, scene=None, on_right=None)`, `attach_widget(widget, records_of, scene=None, key=None, on_right=None)`: `on_right(index)` is called on every right press with no drag standing, `index` the 0-based row under the mouse or None.
  - `window.menu_rows(row, source, root, content_dir, exists=os.path.exists) -> [(label, key, enabled)]`, keys `MENU_EXPLORER = "explorer"`, `MENU_EXPORT = "export"`, `MENU_SAVE = "save"`, None for a row that does nothing.
  - `window.run_menu(key, row)`, `window.show_in_explorer(path, is_file)`, seam `window._popen` (= `subprocess.Popen`).

- [ ] **Step 1: Write the failing tests**

In `tests/test_uebridge_listdrag.py`, class `Drag`, add:

```python
    def test_a_right_press_tells_the_row_under_the_mouse(self):
        told = []
        self.drag.on_right = told.append
        self.mouse(self.E.MouseButtonPress, self.row(2), self.R, self.R)
        self.mouse(self.E.MouseButtonPress, self.row(2) + QT.QtCore.QPoint(0, 400),
                   self.R, self.R)
        self.assertEqual(told, [2, None])
        self.assertIsNone(self.drag.dragging())

    def test_attach_takes_the_right_press_callback(self):
        told = []
        drag = listdrag.attach_widget(self.list, lambda: list(self.records),
                                      self.scene, on_right=told.append)
        self.mouse(self.E.MouseButtonPress, self.row(0), self.R, self.R)
        self.assertEqual(told, [0])
```

(Make the list tall enough that `row(2) + (0, 400)` is below every row but inside the viewport: the fixture is 200 px tall with 3 rows, so use `+ QPoint(0, 150)` if 400 falls outside the widget - check `self.list.viewport().height()` and pick a point between the last row and the bottom edge.)

In `tests/test_uebridge_window.py` add after `FolderSave`:

```python
class ListMenu(unittest.TestCase):
    """2026-10-23: the right button on a row - Show in Explorer, and on a
    folder Export / Save here."""

    def folder(self, path):
        from maya_uebridge import foldertree
        return foldertree.Row("folder", 0, path, path, None, 1, False)

    def anim(self):
        from maya_uebridge import foldertree
        record = records.AnimRecord("W", "C:/c/w/W.fbx", "", 24, 1.0, 30.0,
                                    "folder", "C:/c/w/W.fbx", "", "fbx")
        return foldertree.Row("anim", 0, "", "W", record, 1, False)

    def test_a_file_shows_in_explorer(self):
        self.assertEqual(window.menu_rows(self.anim(), "folder", "C:/c", "",
                                          exists=lambda p: True),
                         [("Show in Explorer", window.MENU_EXPLORER, True)])

    def test_a_folder_also_exports_and_saves_here(self):
        rows = window.menu_rows(self.folder("w"), "folder", "C:/c", "",
                                exists=lambda p: True)
        self.assertEqual([key for _l, key, _e in rows],
                         [window.MENU_EXPLORER, window.MENU_EXPORT,
                          window.MENU_SAVE])
        self.assertTrue(all(enabled for _l, _k, enabled in rows))

    def test_a_missing_path_is_said_and_disabled(self):
        rows = window.menu_rows(self.folder("w"), "folder", "C:/c", "",
                                exists=lambda p: False)
        self.assertEqual(rows[0], ("not on disk: C:/c/w", None, False))
        self.assertFalse(any(enabled for _l, _k, enabled in rows))

    def test_no_row_and_no_place(self):
        self.assertEqual(window.menu_rows(None, "folder", "C:/c", ""),
                         [("no file here", None, False)])
        self.assertEqual(window.menu_rows(self.folder("Engine"), "unreal", "",
                                          "C:/P/Content"),
                         [("not a folder on disk", None, False)])

    def test_show_in_explorer_selects_a_file_and_opens_a_folder(self):
        ran = []
        saved = window._popen
        window._popen = ran.append
        self.addCleanup(setattr, window, "_popen", saved)
        saved_status = window._status
        window._status = lambda *a, **k: None     # no real control headless
        self.addCleanup(setattr, window, "_status", saved_status)
        window.show_in_explorer("C:/c/w/W.fbx", True)
        window.show_in_explorer("C:/c/w", False)
        self.assertEqual(ran[0][:2], ["explorer", "/select,"])
        self.assertEqual(ran[1][0], "explorer")
        self.assertEqual(len(ran[1]), 2)
        self.assertNotIn("/", ran[0][2])          # a native path

    def test_run_menu_presses_with_that_folder(self):
        pressed = []
        saved = (window.export_fbx_selected, window.save_scene_selected)
        window.export_fbx_selected = lambda folder=None: pressed.append(("x", folder))
        window.save_scene_selected = lambda folder=None: pressed.append(("s", folder))
        self.addCleanup(lambda: (setattr(window, "export_fbx_selected", saved[0]),
                                 setattr(window, "save_scene_selected", saved[1])))
        row = self.folder("w")
        window.run_menu(window.MENU_EXPORT, row)
        window.run_menu(window.MENU_SAVE, row)
        self.assertEqual(pressed, [("x", row), ("s", row)])

    def test_the_menu_row_is_the_right_pressed_one_else_the_first_picked(self):
        fake = FakeTreeCmds()
        saved = (window.cmds, dict(window._STATE))
        window.cmds = fake

        def put_back():
            window.cmds = saved[0]
            window._STATE.clear()
            window._STATE.update(saved[1])
        self.addCleanup(put_back)
        rec = self.anim().record
        window._STATE.update(filtered=[rec, rec], tree_rows=[], list_mode="list")
        window._right_pressed(1)
        self.assertEqual(window._menu_row().record, rec)
        self.assertNotIn("menu_row", window._STATE)     # used once
        fake.picked = [2]
        self.assertEqual(window._menu_row().record, rec)
        fake.picked = []
        self.assertIsNone(window._menu_row())
        window._right_pressed(None)
        self.assertIsNone(window._menu_row())
```

- [ ] **Step 2: Run them to see them fail**

Run: `QT_QPA_PLATFORM=offscreen "/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_listdrag tests.test_uebridge_window.ListMenu -v`
Expected: failures - no `on_right`, no `menu_rows`.

- [ ] **Step 3: Implement**

`listdrag.py`:
- `Drag.__init__`: add `self.on_right = None`.
- `Drag._mouse`, in the `MouseButtonPress` branch, right after `self._press = None`:

```python
                if (event.button() == Qt.RightButton
                        and self.on_right is not None):
                    index = self.list.indexAt(local_of(event))
                    try:
                        self.on_right(index.row() if index.isValid() else None)
                    except Exception:                        # noqa: BLE001
                        traceback.print_exc()
                    return False             # Maya's popup menu still opens
```

- `attach_widget(widget, records_of, scene=None, key=None, on_right=None)`: after building `drag`, `drag.on_right = on_right`.
- `attach(list_name, records_of, scene=None, on_right=None)`: pass `on_right=on_right` to `attach_widget`.

`window.py`: add `import subprocess` to the imports, then after `save_scene_selected`:

```python
MENU_EXPLORER = "explorer"
MENU_EXPORT = "export"
MENU_SAVE = "save"
_popen = subprocess.Popen


def menu_rows(row, source, root, content_dir, exists=os.path.exists):
    """The right-click rows for the list row `row`: (label, key, enabled).
    Pure but for `exists`."""
    if row is None:
        return [("no file here", None, False)]
    path = foldertree.disk_path(row, source, root, content_dir)
    if not path:
        return [("not a folder on disk", None, False)]
    there = bool(exists(path))
    out = [] if there else [("not on disk: {0}".format(path), None, False)]
    out.append(("Show in Explorer", MENU_EXPLORER, there))
    if row.kind == "folder":
        out.append(("Export FBX here...", MENU_EXPORT, there))
        out.append(("Save scene here...", MENU_SAVE, there))
    return out


def show_in_explorer(path, is_file):
    """Explorer on `path`: a file selected in its folder, a folder opened."""
    native = os.path.normpath(path)
    _popen(["explorer", "/select,", native] if is_file
           else ["explorer", native])
    _status("Explorer: {0}".format(path))


def run_menu(key, row):
    if key == MENU_EXPLORER:
        show_in_explorer(folder_disk(row), row.kind != "folder")
    elif key == MENU_EXPORT:
        export_fbx_selected(folder=row)
    elif key == MENU_SAVE:
        save_scene_selected(folder=row)


def _right_pressed(index):
    """listdrag: the right button went down on row `index` (0-based) or on
    no row (None)."""
    _STATE["menu_row"] = index


def _row_at(index):
    """The list row at 0-based `index`: a tree row in Folders, an animation
    row made from the record in List."""
    if index is None:
        return None
    rows = _STATE.get("tree_rows") or []
    if list_mode() == "folders" and 0 <= index < len(rows):
        return rows[index]
    shown = _STATE.get("filtered") or []
    if 0 <= index < len(shown) and shown[index] is not None:
        record = shown[index]
        return foldertree.Row("anim", 0, "", record.name, record, 1, False)
    return None


def _menu_row():
    """The row a menu opening is for: the right-pressed one (told by
    listdrag, used once), else - no Qt - the first picked row."""
    if "menu_row" in _STATE:
        return _row_at(_STATE.pop("menu_row"))
    picked = cmds.textScrollList(_LIST, query=True,
                                 selectIndexedItem=True) or []
    return _row_at(min(picked) - 1) if picked else None


def _fill_list_menu(menu):
    cmds.popupMenu(menu, edit=True, deleteAllItems=True)
    row = _menu_row()
    for label, key, enabled in menu_rows(
            row, current_source(), _STATE.get("location") or "",
            _STATE.get("content_dir") or ""):
        if key is None:
            cmds.menuItem(parent=menu, label=label, enable=False)
            continue
        cmds.menuItem(parent=menu, label=label, enable=enabled,
                      command=(lambda k, r: lambda *_: _run(
                          lambda: run_menu(k, r)))(key, row))
```

In `build_rows`, right after the list's `cmds.textScrollList(_LIST, ...)` call:

```python
    menu = cmds.popupMenu(parent=_LIST, button=3)
    cmds.popupMenu(menu, edit=True,
                   postMenuCommand=lambda *_a, m=menu: _fill_list_menu(m))
```

`_attach_drag`: `listdrag.attach(_LIST, lambda: list(_STATE["filtered"]), on_right=_right_pressed)`. The source check `test_uebridge_window.py:360` asserts `"listdrag.attach(_LIST"` is in the source - it still is.

- [ ] **Step 4: Run the bridge tests**

Run: `QT_QPA_PLATFORM=offscreen "/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_window tests.test_uebridge_foldertree tests.test_uebridge_listdrag -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```
feat(uebridge): right button on a row - Show in Explorer, Export / Save here

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

`git commit -F msg.txt -- SkeldarAnim/maya_uebridge/listdrag.py SkeldarAnim/maya_uebridge/window.py tests/test_uebridge_listdrag.py tests/test_uebridge_window.py`

---

### Task 5: CLAUDE.md and the whole suite

**Files:**
- Modify: `CLAUDE.md` - the section «Animation Setup: the list as a folder tree (2026-10-23)».

- [ ] **Step 1: Write the record**

Under the folder-tree section's bullets, replace the bullet about `_on_select` toggling a picked folder and the `DOUBLE_S` double click with:

```markdown
- **Folders you pick, export and save into** (the same day: «выделять папки ... экспортировать или
  сохранять фаил в выделенной папке ... show in explorer»; spec
  `docs/superpowers/specs/2026-10-23-animation-setup-folder-actions-design.md`, which replaces the click
  rules above): a click picks a folder like a row (Ctrl / Shift as Maya's), a double click on a lone
  picked folder opens / closes it, any other double click imports the picked animations; a picked folder
  never imports and a rebuild keeps it by path (`picked_folders`). **Export FBX...** and a new **Save
  scene...** (the Export ▸ row: FBX + Save, then uasset) write straight into the one picked folder, its
  name asked (`_ask_name`, `foldertree.safe_file_name`: `.fbx` / `.ma`, a typed `.mb` kept), an existing
  file confirmed, a folder gone from disk refused; none picked: the save dialog; several: refused; the
  buttons read «Export FBX to Chars...» (`folder_label`, repainted by `paint_import`). Save scene with
  Scene Tabs on saves the active tab there (`saving.save_tab(path=)`). An Unreal folder is its folder
  under the project's Content (`foldertree.disk_path`; another mount has none). **The right button on a
  row** (a `popupMenu` on the list; `listdrag`'s filter tells the row under the mouse,
  `_right_pressed` / `_menu_row`): Show in Explorer (a file selected, a folder opened), on a folder
  also Export FBX here... / Save scene here...; a missing path disabled and said (`menu_rows`). Proof:
  unit tests only (`DiskPath`, `SafeFileName`, `FolderTree`, `FolderSave`, `ListMenu`, the listdrag
  right press). Not seen in a GUI Maya: the popup, Explorer, the prompt.
```

- [ ] **Step 2: Run the whole suite**

Run: `QT_QPA_PLATFORM=offscreen "/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest discover -s tests -t .`
Expected: OK, except the known `test_chat_deploy.Keys` failure (the animator's saved Cloudflare keys). Any other failure: fix it before committing.

- [ ] **Step 3: Commit**

```
docs: Animation Setup folder actions in CLAUDE.md

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

`git commit -F msg.txt -- CLAUDE.md`

Do not push: pushing is the animator's call (and local `main` may hold other sessions' unpushed commits - a push then goes by cherry-pick onto `origin/main` in a temporary worktree).
