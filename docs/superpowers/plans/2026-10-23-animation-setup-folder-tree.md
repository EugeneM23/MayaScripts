# Animation Setup Folder Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `[List | Folders]` switch in Animation Setup's search row that shows the animation list as a folder tree inside the same Maya list.

**Architecture:** A new stdlib module `maya_uebridge/foldertree.py` builds the tree from the records and flattens it into rows (pure, fully unit-tested). `maya_uebridge/window.py` fills the existing `textScrollList` from those rows in Folders mode, keeps one `_STATE["filtered"]` entry per row (`None` for a folder), toggles a folder on a click and remembers the open folders per place. Everything that reads `_STATE["filtered"]` (import, the drag, the Import button's words) already skips or can skip `None`.

**Tech Stack:** Python 3 (Maya 2027's mayapy), `maya.cmds`, stdlib `unittest`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-23-animation-setup-folder-tree-design.md`.
- optionVars: `ueAnimBridgeListMode` (`"list"` / `"folders"`, default `"list"`), `ueAnimBridgeOpenFolders` (JSON, at most 20 places).
- A folder row only opens / closes. It is never part of the selection, never imported, never dragged.
- `foldertree.py` imports nothing of Maya (stdlib + `maya_uebridge.records`, itself stdlib).
- Tests run with: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <module> -v` from the repo root (`C:\!!!Work\MayaScripts`). No system Python exists; `python` hangs.
- The repo has other sessions' uncommitted changes: commit ONLY the files a task names (`git commit -- <paths>`), never `git add -A`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; write them to a file and use `git commit -F` (PowerShell here-strings break quotes).

---

### Task 1: `foldertree` - the tree, its rows, the memory

**Files:**
- Create: `SkeldarAnim/maya_uebridge/foldertree.py`
- Test: `tests/test_uebridge_foldertree.py`

**Interfaces:**
- Consumes: `records.AnimRecord` (fields `name package skeleton frames length fps source path clip fmt`), `records._middle(text, width)`, `records.NAME_WIDTH`.
- Produces:
  - `MODE_VAR = "ueAnimBridgeListMode"`, `OPEN_VAR = "ueAnimBridgeOpenFolders"`, `MODES = ("list", "folders")`, `MAX_PLACES = 20`
  - `Row = namedtuple("Row", "kind depth path label record count opened")` - `kind` `"folder"` / `"anim"`; `record` None for a folder
  - `folder_of(record, root="") -> str`
  - `build(records, root="") -> Node` (`Node.name`, `.path`, `.folders` dict, `.anims` list, `.count`)
  - `rows(tree, open_paths=None) -> [Row]` - `open_paths=None` means every folder open (a search)
  - `row_text(row) -> str`
  - `toggled(open_paths, path) -> set`
  - `place_key(source, place) -> str`
  - `read_open(text, key) -> set`, `write_open(text, key, paths) -> str`

- [ ] **Step 1: Write the failing tests**

`tests/test_uebridge_foldertree.py`:

```python
"""The folder tree of Animation Setup's list (2026-10-23): pure, no Maya."""

import json
import os
import subprocess
import sys
import unittest

import tests  # noqa: F401  (puts SkeldarAnim on sys.path)
from maya_uebridge import foldertree, records

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "SkeldarAnim")


def ue(package, frames=30):
    return records.AnimRecord(package.rsplit("/", 1)[-1], package, "", frames, 1.0, 30.0)


def onfile(path, source="folder", name=None):
    return records.AnimRecord(name or os.path.splitext(os.path.basename(path))[0], path,
                              "", 24, 1.0, 30.0, source, path, "", "fbx")


class FolderOf(unittest.TestCase):

    def test_an_unreal_record_lives_in_its_package_folder(self):
        self.assertEqual(foldertree.folder_of(ue("/Game/Characters/Anims/A_Jump")),
                         "Game/Characters/Anims")
        self.assertEqual(foldertree.folder_of(ue("/Game/A_Jump")), "Game")

    def test_a_file_lives_in_its_folder_under_the_root(self):
        rec = onfile("C:/clips/walks/fast/W.fbx")
        self.assertEqual(foldertree.folder_of(rec, "C:/clips"), "walks/fast")
        self.assertEqual(foldertree.folder_of(rec, "c:\\CLIPS\\"), "walks/fast")

    def test_a_file_in_the_root_itself_is_at_the_top(self):
        self.assertEqual(foldertree.folder_of(onfile("C:/clips/W.fbx"), "C:/clips"), "")

    def test_a_file_outside_its_root_keeps_its_whole_folder(self):
        self.assertEqual(foldertree.folder_of(onfile("D:\\x\\W.fbx"), "C:/clips"), "D:/x")

    def test_a_unity_clip_lives_in_its_model_s_folder(self):
        rec = onfile("C:/proj/Assets/Anim/Hero.fbx", source="unity", name="Run")
        self.assertEqual(foldertree.folder_of(rec, "C:/proj"), "Assets/Anim")


class Rows(unittest.TestCase):

    def setUp(self):
        self.tree = foldertree.build([
            ue("/Game/Chars/Manny/Walk"), ue("/Game/Chars/Manny/Run"),
            ue("/Game/Chars/Manny/sub/Idle"), ue("/Game/Chars/Quinn/Jump"),
            ue("/Game/Root_Anim")])

    def test_counts_take_the_subfolders_in(self):
        game = self.tree.folders["game"]
        self.assertEqual(game.count, 5)
        self.assertEqual(game.folders["chars"].folders["manny"].count, 3)

    def test_only_the_top_level_when_nothing_is_open(self):
        rows = foldertree.rows(self.tree, set())
        self.assertEqual([(r.kind, r.label, r.count, r.opened) for r in rows],
                         [("folder", "Game", 5, False)])

    def test_folders_come_first_then_animations_by_name(self):
        rows = foldertree.rows(self.tree, {"Game", "Game/Chars", "Game/Chars/Manny"})
        self.assertEqual([(r.kind, r.depth, r.label) for r in rows], [
            ("folder", 0, "Game"),
            ("folder", 1, "Chars"),
            ("folder", 2, "Manny"),
            ("folder", 3, "sub"),
            ("anim", 3, "Run"),
            ("anim", 3, "Walk"),
            ("folder", 2, "Quinn"),
            ("anim", 1, "Root_Anim")])
        self.assertIsNone(rows[0].record)
        self.assertEqual(rows[4].record.package, "/Game/Chars/Manny/Run")

    def test_a_chain_of_lone_folders_is_one_row_named_for_the_deepest(self):
        tree = foldertree.build([ue("/Game/A/B/C/Walk"), ue("/Game/A/B/C/Run")])
        rows = foldertree.rows(tree, set())
        self.assertEqual([(r.label, r.path) for r in rows], [("Game/A/B/C", "Game/A/B/C")])
        opened = foldertree.rows(tree, {"Game/A/B/C"})
        self.assertEqual([r.label for r in opened], ["Game/A/B/C", "Run", "Walk"])

    def test_none_opens_every_folder(self):
        rows = foldertree.rows(self.tree, None)
        self.assertEqual(sum(1 for r in rows if r.kind == "anim"), 5)
        self.assertTrue(all(r.opened for r in rows if r.kind == "folder"))

    def test_a_search_is_a_tree_of_the_matches_alone(self):
        shown = records.filter_records([ue("/Game/Chars/Manny/Walk"),
                                        ue("/Game/Chars/Quinn/Jump")], "walk")
        rows = foldertree.rows(foldertree.build(shown), None)
        self.assertEqual([r.label for r in rows], ["Game/Chars/Manny", "Walk"])


class RowText(unittest.TestCase):

    def test_a_folder_row_says_its_state_and_its_count(self):
        closed = foldertree.Row("folder", 1, "Game/Chars", "Chars", None, 12, False)
        opened = closed._replace(opened=True)
        self.assertEqual(foldertree.row_text(closed), "  \u25b8 Chars  (12)")
        self.assertEqual(foldertree.row_text(opened), "  \u25be Chars  (12)")

    def test_an_animation_row_sits_under_its_folder_s_name(self):
        row = foldertree.Row("anim", 1, "", "Walk", ue("/Game/Chars/Walk", 61), 1, False)
        text = foldertree.row_text(row)
        self.assertTrue(text.startswith("    Walk"))
        self.assertTrue(text.endswith("61 fr"))

    def test_an_animation_with_no_length_has_no_length(self):
        rec = records.AnimRecord("Walk", "/Game/Walk", "", None, None, None)
        row = foldertree.Row("anim", 0, "", "Walk", rec, 1, False)
        self.assertEqual(foldertree.row_text(row), "  Walk")


class Memory(unittest.TestCase):

    def test_toggled_opens_and_closes(self):
        self.assertEqual(foldertree.toggled(set(), "A"), {"A"})
        self.assertEqual(foldertree.toggled({"A", "B"}, "A"), {"B"})

    def test_a_place_key_is_its_source_and_place_case_free(self):
        self.assertEqual(foldertree.place_key("folder", "C:\\Clips"), "folder:c:/clips")

    def test_the_memory_round_trips_per_place(self):
        text = foldertree.write_open("", "unreal:atone", {"Game", "Game/Chars"})
        text = foldertree.write_open(text, "folder:c:/x", {"walks"})
        self.assertEqual(foldertree.read_open(text, "unreal:atone"), {"Game", "Game/Chars"})
        self.assertEqual(foldertree.read_open(text, "folder:c:/x"), {"walks"})
        self.assertEqual(foldertree.read_open(text, "unity:none"), set())

    def test_the_memory_keeps_the_last_twenty_places(self):
        text = ""
        for i in range(25):
            text = foldertree.write_open(text, "p%d" % i, {"x"})
        self.assertEqual(len(json.loads(text)), foldertree.MAX_PLACES)
        self.assertEqual(foldertree.read_open(text, "p0"), set())
        self.assertEqual(foldertree.read_open(text, "p24"), {"x"})

    def test_a_broken_memory_reads_empty(self):
        for text in ("{", "42", '{"a": 1}', '[["k", 5]]', None):
            self.assertEqual(foldertree.read_open(text, "k"), set())


class Pure(unittest.TestCase):

    def test_it_imports_nothing_of_maya(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_uebridge.foldertree; "
                "print([m for m in sys.modules if m.startswith('maya.') or m == 'maya'])"
                % PLUGIN)
        out = subprocess.check_output([sys.executable, "-c", code], cwd=PLUGIN)
        self.assertEqual(out.decode().strip(), "[]")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_foldertree -v`
Expected: ERROR - `cannot import name 'foldertree'`.

- [ ] **Step 3: Write the module**

`SkeldarAnim/maya_uebridge/foldertree.py`:

```python
"""Animation Setup's list as a folder tree (2026-10-23).

The animator: «сделать режим в котором я буду видеть структуру папок». The tree
is drawn as rows of the same Maya list (`window._repopulate`), so the selection,
the drag and the import keep working; a folder row only opens and closes.

Pure: stdlib and `records` only, so it is testable with no Maya at all.
"""

import collections
import json

from maya_uebridge import records

MODE_VAR = "ueAnimBridgeListMode"        # "list" / "folders"
OPEN_VAR = "ueAnimBridgeOpenFolders"     # JSON [[place key, [folder paths]], ...]
MODES = ("list", "folders")
MAX_PLACES = 20
OPEN_MARK = "\u25be"
CLOSED_MARK = "\u25b8"
INDENT = "  "

Row = collections.namedtuple("Row", "kind depth path label record count opened")


class Node(object):
    """One folder: its own name, its path from the top, its subfolders (by
    lower-case name), the animations right in it, and how many below it."""

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.folders = {}
        self.anims = []
        self.count = 0


def _slashed(path):
    return (path or "").replace("\\", "/")


def folder_of(record, root=""):
    """The folder `record` lives in, slashes forward, "" for the top.

    Unreal: the package without its last part (`/Game/A/Walk` -> `Game/A`).
    A file (Unity, a folder): its folder relative to `root`, the project or
    the chosen folder; outside `root` its whole folder."""
    if record.source == "unreal" or not record.path:
        package = (record.package or "").lstrip("/")
        return package.rsplit("/", 1)[0] if "/" in package else ""
    path = _slashed(record.path)
    folder = path.rsplit("/", 1)[0] if "/" in path else ""
    base = _slashed(root).rstrip("/")
    if base:
        if folder.lower() == base.lower():
            return ""
        if folder.lower().startswith(base.lower() + "/"):
            return folder[len(base) + 1:]
    return folder


def build(record_list, root=""):
    """The tree of `record_list`: a nameless top node."""
    top = Node("", "")
    for record in record_list:
        node = top
        for part in [p for p in folder_of(record, root).split("/") if p]:
            key = part.lower()
            if key not in node.folders:
                node.folders[key] = Node(
                    part, node.path + "/" + part if node.path else part)
            node = node.folders[key]
        node.anims.append(record)
    _count(top)
    return top


def _count(node):
    node.count = len(node.anims) + sum(_count(c) for c in node.folders.values())
    return node.count


def rows(tree, open_paths=None):
    """The rows top down. A chain of folders holding one folder and no
    animation is one row, named by the chain and kept by its deepest path.
    `open_paths` None opens every folder (a search shows its matches)."""
    out = []

    def walk(node, depth):
        for child in sorted(node.folders.values(), key=lambda n: n.name.lower()):
            label = child.name
            while len(child.folders) == 1 and not child.anims:
                only = next(iter(child.folders.values()))
                label += "/" + only.name
                child = only
            opened = open_paths is None or child.path in open_paths
            out.append(Row("folder", depth, child.path, label, None,
                           child.count, opened))
            if opened:
                walk(child, depth + 1)
        for record in sorted(node.anims, key=lambda r: r.name.lower()):
            out.append(Row("anim", depth, "", record.name, record, 1, False))

    walk(tree, 0)
    return out


def row_text(row):
    """The list's line: a folder's arrow, name and count; an animation under
    its folder's name, then its length."""
    pad = INDENT * row.depth
    if row.kind == "folder":
        mark = OPEN_MARK if row.opened else CLOSED_MARK
        return "{0}{1} {2}  ({3})".format(pad, mark, row.label, row.count)
    record = row.record
    frames = "{0} fr".format(record.frames) if record.frames is not None else ""
    return "{0}{1}{2:<{3}} {4}".format(
        pad, INDENT, records._middle(record.name, records.NAME_WIDTH),
        records.NAME_WIDTH, frames).rstrip()


def toggled(open_paths, path):
    """`open_paths` with `path` opened when it was closed, closed when open."""
    paths = set(open_paths or ())
    if path in paths:
        paths.discard(path)
    else:
        paths.add(path)
    return paths


def place_key(source, place):
    """Which memory a list uses: its source and its project / folder."""
    return "{0}:{1}".format(source, _slashed(place).lower())


def _pairs(text):
    try:
        data = json.loads(text or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if (isinstance(item, list) and len(item) == 2
                and isinstance(item[0], str) and isinstance(item[1], list)):
            out.append((item[0], [p for p in item[1] if isinstance(p, str)]))
    return out


def read_open(text, key):
    """The open folders the memory `text` keeps for `key`; a broken or
    missing memory is none."""
    for name, paths in _pairs(text):
        if name == key:
            return set(paths)
    return set()


def write_open(text, key, paths):
    """`text` with `key`'s open folders set; the place goes last, and only
    the last MAX_PLACES places are kept."""
    pairs = [(name, p) for name, p in _pairs(text) if name != key]
    pairs.append((key, sorted(paths)))
    return json.dumps([[name, p] for name, p in pairs[-MAX_PLACES:]])
```

- [ ] **Step 4: Run them to see them pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_foldertree -v`
Expected: all PASS. If `test_an_animation_row_sits_under_its_folder_s_name` fails, check the indent: depth 1 gives `INDENT` (2) + `INDENT` (2) = 4 spaces before the name.

- [ ] **Step 5: Commit**

```
git add SkeldarAnim/maya_uebridge/foldertree.py tests/test_uebridge_foldertree.py
git commit -F <msg file> -- SkeldarAnim/maya_uebridge/foldertree.py tests/test_uebridge_foldertree.py
```
Message: `feat(uebridge): foldertree - Animation Setup's list as a folder tree, pure`

---

### Task 2: `window` - the switch, the tree in the list, a folder click

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/window.py` - constants near `_SOURCE` (~line 88), `_STATE` (line 106), `_repopulate` (line 255), `_selected_records` (line 294), the search row and the list in `build_rows` (~lines 1240-1260)
- Test: `tests/test_uebridge_window.py` (a new class at the end, before `if __name__`)

**Interfaces:**
- Consumes (Task 1): `foldertree.MODE_VAR`, `OPEN_VAR`, `MODES`, `build`, `rows`, `row_text`, `toggled`, `place_key`, `read_open`, `write_open`, `Row`.
- Produces:
  - `list_mode() -> "list" | "folders"`, `set_list_mode(mode)`
  - `_STATE["filtered"]` holds one entry per list row: an `AnimRecord`, or `None` for a folder row; `_STATE["tree_rows"]` the `Row`s in Folders mode (`[]` in List)
  - `_on_select()` (the list's `selectCommand`), `_on_double()` (its `doubleClickCommand`)
  - `DOUBLE_S = 0.5` and `_now = time.monotonic` (a seam for the tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_uebridge_window.py`:

```python
class FakeTreeCmds(object):
    """Just what `_repopulate`, `_on_select` and the mode switch ask: a list
    of lines with a 1-based selection, a search text, optionVars."""

    def __init__(self):
        self.lines, self.picked, self.vars, self.text = [], [], {}, ""

    def textScrollList(self, name, edit=False, query=False, exists=False,
                       removeAll=False, append=None, selectIndexedItem=None,
                       deselectIndexedItem=None, **kwargs):
        if exists:
            return True
        if query:
            return list(self.picked)
        if removeAll:
            self.lines, self.picked = [], []
        if append is not None:
            self.lines.append(append)
        if selectIndexedItem is not None and not isinstance(selectIndexedItem, bool):
            self.picked = sorted(set(self.picked) | {selectIndexedItem})
        if deselectIndexedItem is not None:
            self.picked = [i for i in self.picked if i != deselectIndexedItem]

    def textField(self, name, query=False, exists=False, **kwargs):
        if exists:
            return True
        return self.text if query else None

    def optionVar(self, exists=None, query=None, stringValue=None, **kwargs):
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars[query]
        if stringValue is not None:
            self.vars[stringValue[0]] = stringValue[1]

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class FolderTree(unittest.TestCase):
    """2026-10-23: the list in Folders mode is a tree; a folder only opens."""

    def setUp(self):
        from maya_uebridge import foldertree
        self.foldertree = foldertree
        self.fake = FakeTreeCmds()
        saved = (window.cmds, dict(window._STATE), window._status, window._now,
                 window.paint_import)
        window.cmds = self.fake
        window._status = lambda *a, **k: None
        window.paint_import = lambda: None
        self.clock = [100.0]
        window._now = lambda: self.clock[0]

        def put_back():
            window.cmds, state, window._status, window._now, window.paint_import = saved
            window._STATE.clear()
            window._STATE.update(state)
        self.addCleanup(put_back)
        recs = [records.AnimRecord(p.rsplit("/", 1)[-1], p, "", 30, 1.0, 30.0)
                for p in ("/Game/Chars/Walk", "/Game/Chars/Run", "/Game/Props/Spin")]
        window._STATE.update(records=recs, filtered=[], source="unreal",
                             project="Atone", location="", list_mode=None)

    def test_list_is_the_default_and_unchanged(self):
        self.assertEqual(window.list_mode(), "list")
        window._repopulate(quiet=True)
        self.assertEqual(len(self.fake.lines), 3)
        self.assertNotIn(None, window._STATE["filtered"])

    def test_the_mode_is_remembered(self):
        window.set_list_mode("folders")
        self.assertEqual(self.fake.vars[self.foldertree.MODE_VAR], "folders")
        window._STATE["list_mode"] = None
        self.assertEqual(window.list_mode(), "folders")

    def test_folders_mode_fills_folder_rows_closed_at_first(self):
        window.set_list_mode("folders")
        self.assertEqual(self.fake.lines, ["\u25b8 Game  (3)"])
        self.assertEqual(window._STATE["filtered"], [None])

    def test_a_folder_click_opens_it_remembers_it_and_leaves_it_unpicked(self):
        window.set_list_mode("folders")
        self.fake.picked = [1]
        window._on_select()
        self.assertEqual(self.fake.lines[0], "\u25be Game  (3)")
        self.assertEqual(self.fake.picked, [])
        key = self.foldertree.place_key("unreal", "Atone")
        self.assertEqual(self.foldertree.read_open(
            self.fake.vars[self.foldertree.OPEN_VAR], key), {"Game"})

    def test_picked_animations_stay_picked_across_a_folder_click(self):
        window.set_list_mode("folders")
        self.fake.picked = [1]
        window._on_select()                       # Game open: Chars, Props
        self.clock[0] += 5
        self.fake.picked = [2]                    # Chars
        window._on_select()                       # Game, Chars, Run, Walk, Props
        self.clock[0] += 5
        self.fake.picked = [3]                    # Run
        window._on_select()
        self.assertEqual([r.name for r in window._selected_records()], ["Run"])
        self.fake.picked = [3, 5]                 # Run and Props (a folder)
        self.clock[0] += 5
        window._on_select()                       # Props opens: Spin under it
        self.assertEqual([r.name for r in window._selected_records()], ["Run"])
        self.assertIn("    Spin", "\n".join(self.fake.lines))

    def test_the_second_click_of_a_double_click_does_not_close_it_again(self):
        window.set_list_mode("folders")
        self.fake.picked = [1]
        window._on_select()
        self.clock[0] += 0.2
        self.fake.picked = [1]
        window._on_select()
        self.assertEqual(self.fake.lines[0], "\u25be Game  (3)")

    def test_a_double_click_on_a_folder_imports_nothing(self):
        imported = []
        saved = window.import_selected
        window.import_selected = lambda: imported.append(True)
        self.addCleanup(setattr, window, "import_selected", saved)
        window.set_list_mode("folders")
        self.fake.picked = [1]
        window._on_select()
        window._on_double()
        self.assertEqual(imported, [])

    def test_a_double_click_on_an_animation_still_imports(self):
        imported = []
        saved = window.import_selected
        window.import_selected = lambda: imported.append(True)
        self.addCleanup(setattr, window, "import_selected", saved)
        window.set_list_mode("folders")
        self.fake.picked = [1]
        window._on_select()
        self.clock[0] += 5
        self.fake.picked = [2]
        window._on_select()                       # Chars open
        self.clock[0] += 5
        self.fake.picked = [3]                    # Run
        window._on_select()
        window._on_double()
        self.assertEqual(imported, [True])

    def test_a_search_opens_every_matching_branch_and_keeps_the_memory(self):
        window.set_list_mode("folders")
        self.fake.text = "spin"
        window._repopulate(quiet=True)
        self.assertEqual(self.fake.lines[0], "\u25be Game/Props  (1)")
        self.assertTrue(self.fake.lines[1].strip().startswith("Spin"))
        self.assertNotIn(self.foldertree.OPEN_VAR, self.fake.vars)

    def test_a_folder_click_during_a_search_changes_nothing(self):
        window.set_list_mode("folders")
        self.fake.text = "spin"
        window._repopulate(quiet=True)
        self.fake.picked = [1]
        window._on_select()
        self.assertEqual(self.fake.picked, [])
        self.assertNotIn(self.foldertree.OPEN_VAR, self.fake.vars)
        self.assertEqual(self.fake.lines[0], "\u25be Game/Props  (1)")

    def test_a_file_source_is_a_tree_under_its_folder(self):
        window._STATE.update(source="folder", location="C:/clips", records=[
            records.AnimRecord("W", "C:/clips/walks/W.fbx", "", 24, 1.0, 30.0,
                               "folder", "C:/clips/walks/W.fbx", "", "fbx")])
        window.set_list_mode("folders")
        self.assertEqual(self.fake.lines, ["\u25b8 walks  (1)"])
```

- [ ] **Step 2: Run them to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_window.FolderTree -v`
Expected: ERROR - `module 'maya_uebridge.window' has no attribute '_now'` (setUp).

- [ ] **Step 3: Implement**

In `window.py`:

1. Imports at the top: add `import time` beside the other stdlib imports, and `from maya_uebridge import foldertree` beside the other `maya_uebridge` imports (if `records` is imported as `from maya_uebridge import records`, add it the same way).

2. Constants after `RECENT_VAR` / `BROWSE`:

```python
#  2026-10-23 («режим в котором я буду видеть структуру папок»): the list as
#  a folder tree in the same Maya list (`foldertree`); a folder row only opens
#  and closes, it is never picked, imported or dragged.
_LIST_MODE = "ueAnimBridgeListMode"
LIST_MODES = (("list", "List", "Every animation in one list"),
              ("folders", "Folders",
               "The animations in their folders: a click on a folder opens or "
               "closes it"))
DOUBLE_S = 0.5            # a second click on the same folder this soon is the
                          # double click's, not a new toggle
_now = time.monotonic
```

3. `_STATE`: add `"list_mode": None, "tree_rows": [], "last_toggle": (None, 0.0)` to the dict literal.

4. New functions after `_recent` (they use `_var`):

```python
def list_mode():
    """"list" or "folders": the switch in the search row."""
    mode = _STATE.get("list_mode")
    if mode is None:
        try:
            mode = _var(foldertree.MODE_VAR, "list")
        except Exception:                                    # noqa: BLE001
            mode = "list"
    return mode if mode in foldertree.MODES else "list"


def set_list_mode(mode):
    mode = mode if mode in foldertree.MODES else "list"
    _STATE["list_mode"] = mode
    cmds.optionVar(stringValue=(foldertree.MODE_VAR, mode))
    _repopulate()


def list_mode_button(mode):
    return "{0}_{1}".format(_LIST_MODE, mode)


def _tree_root():
    """What a file's folder is relative to: the project / the folder."""
    return "" if current_source() == "unreal" else _STATE.get("location") or ""


def _place():
    place = (_STATE.get("project") if current_source() == "unreal"
             else _STATE.get("location"))
    return foldertree.place_key(current_source(), place or "")


def _open_folders():
    return foldertree.read_open(_var(foldertree.OPEN_VAR, ""), _place())


def _save_open(paths):
    cmds.optionVar(stringValue=(foldertree.OPEN_VAR, foldertree.write_open(
        _var(foldertree.OPEN_VAR, ""), _place(), paths)))
```

5. `_repopulate`: replace the body from `previous = ...` up to `paint_import()` with:

```python
    # The selection survives the rebuild by identity, not by position - a
    # narrowed filter must not silently select a different animation. A
    # folder row (None) is never kept.
    previous = _STATE.get("filtered") or []
    picked = cmds.textScrollList(_LIST, query=True,
                                 selectIndexedItem=True) or []
    keep = set(previous[i - 1].package for i in picked
               if 0 < i <= len(previous) and previous[i - 1] is not None)

    if list_mode() == "folders":
        tree = foldertree.build(shown, _tree_root())
        tree_rows = foldertree.rows(
            tree, None if query.strip() else _open_folders())
        entries = [row.record for row in tree_rows]
        lines = [foldertree.row_text(row) for row in tree_rows]
    else:
        tree_rows = []
        entries = list(shown)
        lines = [records.format_row(record) for record in shown]
    _STATE["filtered"] = entries
    _STATE["tree_rows"] = tree_rows
    #  the placeholder says how many animations the source holds (the skin
    #  has no editor line to carry the count)
    try:
        cmds.textField(_SEARCH, edit=True,
                       placeholderText=search_hint(len(_STATE["records"])))
    except (RuntimeError, TypeError, ValueError):
        pass
    cmds.textScrollList(_LIST, edit=True, removeAll=True)
    for line in lines:
        cmds.textScrollList(_LIST, edit=True, append=line)
    for index, record in enumerate(entries, 1):
        if record is not None and record.package in keep:
            cmds.textScrollList(_LIST, edit=True, selectIndexedItem=index)
    paint_import()
```

   (`query` is already read at the top of `_repopulate`; the status line after it is unchanged and still counts `shown`.)

6. `_selected_records`: skip folder rows:

```python
    return [shown[i - 1] for i in sorted(indices)
            if 0 < i <= len(shown) and shown[i - 1] is not None]
```

7. The list's commands - new functions after `_selected_records`:

```python
def _on_select():
    """A row click. A folder row in Folders mode opens or closes (not during a
    search, which shows every match open) and leaves the selection at once;
    the animations picked stay picked."""
    rows = _STATE.get("tree_rows") or []
    if list_mode() == "folders" and rows:
        picked = cmds.textScrollList(_LIST, query=True,
                                     selectIndexedItem=True) or []
        folders = [i for i in picked
                   if 0 < i <= len(rows) and rows[i - 1].kind == "folder"]
        if folders:
            for index in folders:
                cmds.textScrollList(_LIST, edit=True, deselectIndexedItem=index)
            searching = bool((cmds.textField(_SEARCH, query=True, text=True)
                              if cmds.textField(_SEARCH, exists=True) else "")
                             .strip())
            if not searching:
                paths = _open_folders()
                last_path, last_at = _STATE.get("last_toggle") or (None, 0.0)
                for index in folders:
                    path = rows[index - 1].path
                    if path == last_path and _now() - last_at < DOUBLE_S:
                        continue        # the double click's second click
                    paths = foldertree.toggled(paths, path)
                    _STATE["last_toggle"] = (path, _now())
                _save_open(paths)
                _repopulate(quiet=True)
    paint_import()


def _on_double():
    """A double click imports the picked animations - never on a folder:
    its clicks opened it, and a folder clicked a moment ago means this double
    click was the folder's."""
    _path, last_at = _STATE.get("last_toggle") or (None, 0.0)
    if list_mode() == "folders" and _now() - last_at < DOUBLE_S:
        return
    if not _selected_records():
        return
    _run(import_selected, busy=_import_busy())
```

   Note for `test_a_double_click_on_a_folder_imports_nothing`: the test replaces `window.import_selected` and `_run` calls whatever it is given, so `_on_double` must pass `import_selected` looked up at call time (as written: the module global).

8. `build_rows`: the search field and the switch share one row. Replace

```python
    cmds.textField(_SEARCH, placeholderText=search_hint(0),
                   height=hubstyle.height("field", 24),
                   textChangedCommand=lambda *_: _run(_repopulate))
```

with

```python
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "left", 3)])
    cmds.textField(_SEARCH, placeholderText=search_hint(0),
                   height=hubstyle.height("field", 24),
                   textChangedCommand=lambda *_: _run(_repopulate))
    switch = cmds.rowLayout(numberOfColumns=len(LIST_MODES),
                            columnAttach=[(i + 1, "both", 1)
                                          for i in range(len(LIST_MODES))])
    hubstyle.mark(switch, "segments", layout=True)
    cmds.iconTextRadioCollection(_LIST_MODE)
    for mode, words, note in LIST_MODES:
        hubstyle.mark(cmds.iconTextRadioButton(
            list_mode_button(mode), style="textOnly", label=words,
            height=hubstyle.height("segment", 22),
            select=mode == list_mode(), annotation=note,
            onCommand=lambda *_a, m=mode: _run(lambda: set_list_mode(m))),
            "segment")
    cmds.setParent("..")
    cmds.setParent("..")
```

   and in the `cmds.textScrollList(_LIST, ...)` call change the two commands to

```python
        selectCommand=lambda *_: _run(_on_select),
        doubleClickCommand=lambda *_: _on_double())
```

   and add to the list's `annotation` text the sentence `" In Folders, a click on a folder opens or closes it."` (before the closing parenthesis of the string).

- [ ] **Step 4: Run the new tests and the whole window module**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_window -v`
Expected: all PASS (the old classes too: List mode is the old code path).

If `test_picked_animations_stay_picked_across_a_folder_click` fails on the row numbers, print `self.fake.lines` - the expected order after opening Game then Chars is `Game, Chars, Run, Walk, Props` (folders first, animations by name, Props a sibling of Chars).

- [ ] **Step 5: Commit**

```
git commit -F <msg file> -- SkeldarAnim/maya_uebridge/window.py tests/test_uebridge_window.py
```
Message: `feat(uebridge): Animation Setup's [List | Folders] switch - the list as a folder tree`

---

### Task 3: the drag never carries a folder, and the record

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/listdrag.py` (`_start`, ~line 407-411)
- Test: `tests/test_uebridge_listdrag.py` (a new test in the class that tests `carried_rows` / `_as_list`, or a new class)
- Modify: `CLAUDE.md` (a new section after "Animation Setup as two numbered steps (2026-10-19)")

**Interfaces:**
- Consumes (Task 2): `_STATE["filtered"]` may hold `None` (a folder row); `listdrag.attach(_LIST, lambda: list(_STATE["filtered"]))` hands it over unchanged.
- Produces: `listdrag.carried_records(rows, records) -> [AnimRecord]` (pure).

`_row_at` already returns `(row, None)` for a folder row, and a press only starts when its record is not None, so a drag can never START on a folder. But `carried_rows` can include a folder row picked beside animations (Ctrl), so `_start` must drop it.

- [ ] **Step 1: Write the failing test**

In `tests/test_uebridge_listdrag.py`, a new class:

```python
class FolderRows(unittest.TestCase):
    """2026-10-23: in Folders mode a list row may be a folder (None)."""

    def test_a_folder_row_is_never_carried(self):
        a = records.AnimRecord("A", "/Game/A", "", 1, 1.0, 30.0)
        b = records.AnimRecord("B", "/Game/B", "", 1, 1.0, 30.0)
        self.assertEqual(listdrag.carried_records([0, 1, 2, 7], [a, None, b]), [a, b])
```

(If the test module has no `records` import, add `from maya_uebridge import records` beside its `listdrag` import.)

- [ ] **Step 2: Run it to see it fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_listdrag.FolderRows -v`
Expected: ERROR - `no attribute 'carried_records'`.

- [ ] **Step 3: Implement**

In `listdrag.py`, after `carried_rows`:

```python
def carried_records(rows, records):
    """The records of `rows` - a folder row (None, Folders mode) and a row
    past the list's end are left out. Pure."""
    return [records[r] for r in rows
            if 0 <= r < len(records) and records[r] is not None]
```

and in `_start` replace

```python
            carried = [records[r] for r in rows if 0 <= r < len(records)]
```

with

```python
            carried = carried_records(rows, records)
```

- [ ] **Step 4: Run the bridge's tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_listdrag tests.test_uebridge_window tests.test_uebridge_foldertree tests.test_uebridge_records -v`
Expected: all PASS.

- [ ] **Step 5: The record in CLAUDE.md**

After the section "## Animation Setup as two numbered steps (2026-10-19)" add:

```markdown
## Animation Setup: the list as a folder tree (2026-10-23)

The animator: «сделать режим в котором я буду видеть структуру папок». Asked: the tree INSIDE the list (not
two panes, not one folder at a time); a folder only opens and closes. Spec
`docs/superpowers/specs/2026-10-23-animation-setup-folder-tree-design.md`, plan beside it.
- `[List | Folders]` segments beside the search field (`ueAnimBridgeListMode`, List by default), every source.
- `maya_uebridge/foldertree.py` (stdlib, pinned): `folder_of` (Unreal's package folder, a file's folder under
  the project / chosen folder), `build`, `rows` (folders first, then animations, by name; a chain of lone
  folders one row; `None` opens all), `row_text` (`▸`/`▾`, two spaces a level, the count), the open folders per
  place in `ueAnimBridgeOpenFolders` (JSON, the last 20 places).
- `window._repopulate` fills the same `textScrollList`; `_STATE["filtered"]` holds one entry a ROW, `None` for a
  folder - `_selected_records`, the Import button's words and `listdrag.carried_records` skip it.
  `_on_select` toggles a picked folder and deselects it (the picked animations stay); a second click on the
  same folder within `DOUBLE_S` 0.5 s is the double click's and toggles nothing; `_on_double` imports nothing
  then. A search shows only the matching branches, all open, and leaves the memory alone.
- Proof: `tests/test_uebridge_foldertree.py`, `test_uebridge_window.FolderTree`,
  `test_uebridge_listdrag.FolderRows`. Not seen in a GUI Maya (the arrows in Maya's list font, a real double
  click's order of select / double-click commands).
```

- [ ] **Step 6: Run the whole suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . 2>$null` - read the last lines of the output (or redirect it to a file in the scratchpad and read its tail).
Expected: OK, but the known `test_chat_deploy.Keys` failure (the animator's saved Cloudflare keys), unrelated.

- [ ] **Step 7: Commit**

CLAUDE.md carries other sessions' uncommitted edits: stage only this section's hunk (`git add -p CLAUDE.md` is interactive and not allowed here - instead write the section, then `git diff CLAUDE.md` to confirm the only other hunks are not yours; if there are others, build the staged file with `git show HEAD:CLAUDE.md` + the new section and `git update-index --cacheinfo` from a blob made by `git hash-object -w`).

```
git commit -F <msg file> -- SkeldarAnim/maya_uebridge/listdrag.py tests/test_uebridge_listdrag.py
```
then the CLAUDE.md section as its own commit by the staging route above.
Message: `fix(uebridge): a folder row is never dragged; CLAUDE.md: the folder tree`
```

---

## Self-review

- Spec coverage: switch + memory (Task 2), folders from each source (Task 1 `folder_of`, Task 2 `_tree_root`), chains joined (Task 1), counts (Task 1), folders first / by name (Task 1), folder click toggles and is never picked (Task 2), double click (Task 2), open folders per place, 20 places (Tasks 1-2), search (Tasks 1-2), the drag (Task 3), status line unchanged (Task 2 keeps it), proof (all).
- Names checked across tasks: `foldertree.rows/row_text/toggled/place_key/read_open/write_open/MODE_VAR/OPEN_VAR/MODES`, `window.list_mode/set_list_mode/_on_select/_on_double/_now/DOUBLE_S`, `listdrag.carried_records`.
