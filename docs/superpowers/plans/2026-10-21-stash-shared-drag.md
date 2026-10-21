# Stash and Shared drag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rows of the Stash and Shared lists drag into a viewport (Import), from Stash onto Shared (send) and from Shared onto Stash (copy).

**Architecture:** The UE Bridge's list drag (`maya_uebridge/listdrag.py`) gains three seams on its scene (caption, drops, icon), defaulting to today's behaviour. A new module `maya_filedrag.py` holds the pure target rules and a `FileScene` for listdrag; `maya_stash` and `maya_share` gain drop entry points and attach the drag to their lists. `maya_share.when_local` runs an action once a not-yet-downloaded file lands.

**Tech Stack:** Maya 2027 `maya.cmds`, PySide6 through `maya_hubqt.qt()`, stdlib `unittest` run with mayapy.

Spec: `docs/superpowers/specs/2026-10-21-stash-shared-drag-design.md`

## Global Constraints

- A drop on a viewport is Import, exactly as the card's Import button does it.
- Stash → Shared sends with no question; Shared → Stash copies under the record's name, a taken name getting ` (2)`.
- Every picked row travels; actions run one by one in list order, one status line naming each result.
- A Shared row not on disk yet is fetched first and the action runs when it lands; sending / never sent / deleted / expired rows are refused by name (the text `_local_or_fetch` gives).
- Drop targets "in a section": its list (hub card or a popup copy - objectName ends with `skeldarStashList` / `skeldarShareList`) or its rail icon `skeldarHubJump_stash` / `skeldarHubJump_shared`.
- The UE Bridge drag is unchanged: `tests/test_uebridge_listdrag.py` stays green.
- Widgets are found again by name, never kept across a drop (trap 135).
- Tests run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v` from the repo root, with `$env:QT_QPA_PLATFORM = 'offscreen'`. Never `python` (the Store stub hangs). No `2>&1` on mayapy in PowerShell.
- Other sessions commit to this branch: stage only your own files (`git add <paths>`), commit with `git commit -F <file>`, never `git add -A`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

### Task 1: listdrag seams - caption, drops, icon

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/listdrag.py` (`Drag.drop_at`, `Drag._start`, `Drag.caption_at`)
- Test: `tests/test_uebridge_listdrag.py` (new class `SceneSeams`)

**Interfaces:**
- Produces: a listdrag scene MAY define `caption(records, aim) -> (text, good)`, `drops` (a tuple of aim kinds a release acts on), `icon` (a Tabler icon name). Missing: the module's `caption([r.name ...], aim)`, `DROPS`, `"run"`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_uebridge_listdrag.py`; reuse the `Drag` class's setUp by subclassing it)

```python
class SeamScene(FakeScene):
    """A scene with its own caption, drops and icon (Stash / Shared, 2026-10-21)."""

    drops = ("send",)
    icon = "send"

    def __init__(self):
        FakeScene.__init__(self)
        self.aim = dict(kind="send", text="send to Shared")

    def caption(self, records, aim):
        return "%d · %s" % (len(records), aim["text"]), True


@unittest.skipIf(QT is None, "no Qt")
class SceneSeams(Drag):

    def setUp(self):
        Drag.setUp(self)
        self.scene = SeamScene()
        self.drag = listdrag.attach_widget(self.list, lambda: list(self.records), self.scene)

    def test_the_scene_s_own_drop_kind_drops(self):
        start = self.row(0)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L)
        self.mouse(self.E.MouseMove, self.far(start), self.N, self.L)
        self.mouse(self.E.MouseButtonRelease, self.far(start), self.L, self.N)
        self.assertEqual(self.acts("drop"), [("drop", "A_Jump", "send")])

    def test_the_ghost_says_the_scene_s_caption(self):
        start = self.row(0)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L)
        self.mouse(self.E.MouseMove, self.far(start), self.N, self.L)
        self.drag.caption_at(self.list.viewport().mapToGlobal(self.far(start)), force=True)
        self.assertEqual(self.drag.ghost().caption_text(), "1 · send to Shared")
        self.mouse(self.E.MouseButtonRelease, self.far(start), self.L, self.N)
```

Before writing the second test, read `maya_hubqt.ghost_class()` (`grep -n "def set_caption" SkeldarAnim/maya_hubqt.py`) and use the attribute the ghost keeps its caption in; if it keeps none, add a `caption_text()` method returning the last text `set_caption` was given (one line, `self._caption = text` inside `set_caption`).

- [ ] **Step 2: Run to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_listdrag.SceneSeams -v`
Expected: FAIL - the drop logs nothing (kind `send` is not in `DROPS`), the caption is the module's.

- [ ] **Step 3: Implement the seams in `listdrag.py`**

In `Drag.drop_at` replace `if aim.get("kind") in DROPS:` with:

```python
            if aim.get("kind") in getattr(self.scene, "drops", DROPS):
```

In `Drag.caption_at` replace `text, good = caption([r.name for r in drag["records"]], aim)` with:

```python
            text, good = self._caption(drag["records"], aim)
```

and add to `Drag`:

```python
        def _caption(self, records, aim):
            own = getattr(self.scene, "caption", None)
            if callable(own):
                return own(list(records), aim)
            return caption([r.name for r in records], aim)
```

In `Drag._start` replace `maya_hubqt.pixmap("run", ...)` with `maya_hubqt.pixmap(getattr(self.scene, "icon", "run"), ...)`.

Note: `FakeScene` and the real `Scene` define none of the three, so the bridge is unchanged. `hubcopy.bind` wraps the scene as a `Bound` - check `getattr` on a `Bound` reaches plain attributes (read `class Bound` in `maya_hubcopy.py`; its `__getattr__` returns non-callables as they are). If it does not, add that branch there.

- [ ] **Step 4: Run the whole listdrag file**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_listdrag -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_uebridge/listdrag.py SkeldarAnim/maya_hubqt.py tests/test_uebridge_listdrag.py
git commit -F msg.txt   # "feat(listdrag): a scene may bring its own caption, drop kinds and icon"
```

---

### Task 2: maya_filedrag - the pure rules

**Files:**
- Create: `SkeldarAnim/maya_filedrag.py`
- Modify: `SkeldarAnim/install.py` (payload row, next to `maya_stash.py`)
- Test: `tests/test_filedrag.py`

**Interfaces:**
- Produces:
  - `Item(name, section, key)` - a namedtuple: the file's shown name, `"stash"` or `"shared"`, the Stash file name or the Shared record id.
  - `LISTS = {"stash": "skeldarStashList", "shared": "skeldarShareList"}`, `JUMP = "skeldarHubJump_"`.
  - `section_under(names) -> "stash" | "shared" | None` for a widget's object names, the widget first, its parents after.
  - `aim_for(source, under, over_viewport) -> dict(kind=..., text=..., section=...)`: kind `"import"` / `"send"` / `"stash"` / `"none"`.
  - `caption(items, aim) -> (text, good)`.
  - `DROPS = ("import", "send", "stash")`.

- [ ] **Step 1: Write the failing tests** `tests/test_filedrag.py`

```python
"""maya_filedrag: rows of Stash and Shared dragged between them and into the
scene (2026-10-21). The pure half here; the drag on a real QListWidget below.

Spec: docs/superpowers/specs/2026-10-21-stash-shared-drag-design.md
"""
import unittest

import maya_filedrag as fd


class SectionUnder(unittest.TestCase):

    def test_the_hub_s_list_and_a_popup_copy_s(self):
        self.assertEqual(fd.section_under(["skeldarStashList", "x"]), "stash")
        self.assertEqual(fd.section_under(["hubcopy3_skeldarShareList"]), "shared")

    def test_a_child_of_the_list_counts(self):
        self.assertEqual(fd.section_under(["qt_scrollarea_viewport", "skeldarShareList"]), "shared")

    def test_the_rail_icons(self):
        self.assertEqual(fd.section_under(["skeldarHubJump_stash", "rail"]), "stash")
        self.assertEqual(fd.section_under(["skeldarHubJump_shared"]), "shared")
        self.assertIsNone(fd.section_under(["skeldarHubJump_tools"]))

    def test_nothing_of_ours(self):
        self.assertIsNone(fd.section_under(["", "MayaWindow"]))
        self.assertIsNone(fd.section_under([]))


class AimFor(unittest.TestCase):

    def test_a_viewport_imports_from_either(self):
        for source in ("stash", "shared"):
            aim = fd.aim_for(source, None, True)
            self.assertEqual(aim["kind"], "import")
            self.assertEqual(aim["text"], "import into the scene")

    def test_the_other_section(self):
        self.assertEqual(fd.aim_for("stash", "shared", False)["kind"], "send")
        self.assertEqual(fd.aim_for("stash", "shared", False)["text"], "send to Shared")
        self.assertEqual(fd.aim_for("shared", "stash", False)["kind"], "stash")
        self.assertEqual(fd.aim_for("shared", "stash", False)["text"], "copy into Stash")

    def test_a_section_wins_over_a_viewport_behind_it(self):
        self.assertEqual(fd.aim_for("stash", "shared", True)["kind"], "send")

    def test_its_own_section_and_nowhere_are_nothing(self):
        self.assertEqual(fd.aim_for("stash", "stash", False)["kind"], "none")
        aim = fd.aim_for("shared", None, False)
        self.assertEqual(aim["kind"], "none")
        self.assertEqual(aim["text"], fd.NOWHERE)


class Caption(unittest.TestCase):

    def items(self, *names):
        return [fd.Item(n, "stash", n) for n in names]

    def test_one_and_several(self):
        aim = fd.aim_for("stash", "shared", False)
        self.assertEqual(fd.caption(self.items("A.fbx"), aim), ("A.fbx · send to Shared", True))
        self.assertEqual(fd.caption(self.items("A.fbx", "B.ma", "C.mb"), aim),
                         ("3 files · send to Shared", True))

    def test_nothing_is_muted(self):
        text, good = fd.caption(self.items("A.fbx"), fd.aim_for("stash", None, False))
        self.assertFalse(good)
        self.assertEqual(text, fd.NOWHERE)


class Pure(unittest.TestCase):

    def test_no_maya_or_qt_at_import(self):
        import subprocess, sys, os
        code = ("import sys; import maya_filedrag; "
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6')]; "
                "sys.exit(1 if bad else 0)")
        plugin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")
        self.assertEqual(subprocess.call([sys.executable, "-c", code], cwd=plugin), 0)
```

- [ ] **Step 2: Run to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_filedrag -v`
Expected: ERROR `No module named 'maya_filedrag'`.

- [ ] **Step 3: Write `SkeldarAnim/maya_filedrag.py`** (the pure half; Task 4 adds the scene below it)

```python
"""maya_filedrag - rows of Stash and Shared dragged between them and into the scene.

2026-10-21, the animator: «драг энд дроп того что находится в сташе и в шаре
между этими папками и на сцену, при драге на сцену это означает что мы делаем
экспорт в сцену». Asked: a viewport is Import as the card's button; Stash ->
Shared sends with no question; every picked row travels.

- a viewport: Import (`maya_stash.drop_import` / `maya_share.drop_import`);
- Stash -> Shared: Send file, each its own name (`maya_stash.drop_to_share`);
- Shared -> Stash: a copy into the stash (`maya_share.drop_to_stash`), a file
  not downloaded yet fetched first;
- a section is its list (the hub's card or a popup copy) or its rail icon.

The drag itself is the UE Bridge list's (`maya_uebridge.listdrag`), handed a
`FileScene`. Nothing here imports Maya or Qt at import time.

Spec: docs/superpowers/specs/2026-10-21-stash-shared-drag-design.md
"""

import collections

Item = collections.namedtuple("Item", "name section key")

LISTS = {"stash": "skeldarStashList", "shared": "skeldarShareList"}
JUMP = "skeldarHubJump_"
TITLES = {"stash": "Stash", "shared": "Shared"}
ICONS = {"stash": "archive", "shared": "send"}
DOT = u"\u00b7"
DROPS = ("import", "send", "stash")
NOWHERE = "drop onto Shared, Stash or a viewport"


def section_under(names):
    """The section whose list or rail icon the chain of object `names` (the
    widget under the cursor first) belongs to, or None. A popup copy's list
    is the base name with the copy's prefix in front. Pure."""
    for name in names or []:
        name = name or ""
        for section, leaf in LISTS.items():
            if name == leaf or name.endswith("_" + leaf):
                return section
        if name.startswith(JUMP) and name[len(JUMP):] in LISTS:
            return name[len(JUMP):]
    return None


def aim_for(source, under, over_viewport):
    """What a release does: dict(kind, text, section). The other section
    under the cursor wins over a viewport behind it. Pure."""
    if under and under != source:
        if under == "shared":
            return dict(kind="send", text="send to Shared", section=under)
        return dict(kind="stash", text="copy into Stash", section=under)
    if under is None and over_viewport:
        return dict(kind="import", text="import into the scene", section=None)
    return dict(kind="none", text=NOWHERE, section=None)


def caption(items, aim):
    """(text, good) for the ghost. Pure."""
    items = list(items or [])
    if aim.get("kind") not in DROPS or not items:
        return aim.get("text") or NOWHERE, False
    what = items[0].name if len(items) == 1 else "%d files" % len(items)
    return "%s %s %s" % (what, DOT, aim["text"]), True
```

Add `"maya_filedrag.py"` to `install.payload()` next to `"maya_stash.py"` (read the list there; a test pins every `maya_*.py` beside install.py ships).

- [ ] **Step 4: Run the tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_filedrag -v`
Expected: all PASS.

- [ ] **Step 5: Commit** (`SkeldarAnim/maya_filedrag.py SkeldarAnim/install.py tests/test_filedrag.py`; "feat(filedrag): the rules of a Stash / Shared row dropped")

---

### Task 3: the drop actions in maya_share and maya_stash

**Files:**
- Modify: `SkeldarAnim/maya_share.py` (`when_local`, `_fetched`, `_fetch_failed`, `drop_import`, `drop_to_stash`)
- Modify: `SkeldarAnim/maya_stash.py` (`drop_import`, `drop_to_share`)
- Test: `tests/test_share.py` (class `Dropped`), `tests/test_stash.py` (class `Dropped`)

**Interfaces:**
- Produces:
  - `maya_share.when_local(rid, fn) -> str`: `fn(path)` now when the file is here (its return is the answer); a ready row being fetched: `fn` queued on `state()["after_fetch"][rid]`, answers «<name> is downloading - it follows when it lands»; else `_local_or_fetch`'s reason.
  - `maya_share.drop_import(rids) -> str`, `maya_share.drop_to_stash(rids) -> str`.
  - `maya_stash.drop_import(names) -> str`, `maya_stash.drop_to_share(names) -> str`.
  - Each `drop_*` writes ONE status (`_status(" | ".join(lines))`) and returns it.

- [ ] **Step 1: Failing tests in `tests/test_share.py`**

```python
class Dropped(_Base):
    """Rows dropped from the list (2026-10-21)."""

    def test_a_local_file_imports_at_once(self):
        rec = self._colleague()
        share.receive(rec)                     # fetched at once: _spawn runs inline
        done = []
        saved = share.import_entry
        share.import_entry = lambda rid: done.append(rid) or "Imported %s" % rid
        try:
            message = share.drop_import([rec["id"]])
        finally:
            share.import_entry = saved
        self.assertEqual(done, [rec["id"]])
        self.assertIn("Imported", message)

    def test_a_file_still_downloading_follows_when_it_lands(self):
        rec = self._colleague()
        held = []
        share._spawn = lambda fn: held.append(fn)     # the download waits
        share.receive(rec)
        ran = []
        answer = share.when_local(rec["id"], lambda path: ran.append(path) or "done")
        self.assertIn("downloading", answer)
        self.assertEqual(ran, [])
        for fn in held:
            fn()
        self.assertEqual(len(ran), 1)
        self.assertTrue(ran[0].endswith("Longsword.fbx"))
        self.assertIn("done", self.statuses[-1])

    def test_a_failed_download_drops_the_waiting_action(self):
        rec = self._colleague()
        held = []
        share._spawn = lambda fn: held.append(fn)
        share.receive(rec)
        ran = []
        share.when_local(rec["id"], lambda path: ran.append(path) or "done")
        self.net.store.clear()                         # the download fails
        for fn in held:
            fn()
        self.assertEqual(ran, [])
        self.assertIn("did not download", self.statuses[-1])

    def test_a_row_still_being_sent_is_refused_by_name(self):
        rec = self._colleague()
        sending = records.with_state(rec, "sending")
        del sending["url"], sending["zip"]
        share.receive(sending)
        self.assertIn("still being sent", share.drop_import([rec["id"]]))

    def test_to_stash_copies_the_file_under_its_name(self):
        import maya_stash
        rec = self._colleague()
        share.receive(rec)
        copied = []
        saved = maya_stash.stash_file
        maya_stash.stash_file = lambda path, name: copied.append((path, name)) or "Stashed " + name
        try:
            message = share.drop_to_stash([rec["id"]])
        finally:
            maya_stash.stash_file = saved
        self.assertEqual(copied[0][1], "Longsword.fbx")
        self.assertTrue(copied[0][0].endswith("Longsword.fbx"))
        self.assertIn("Stashed Longsword.fbx", message)
```

Before running, read `_Net` in `tests/test_share.py` (line ~145) and adjust the failed-download test to the way `_Net.download` fails (a missing url in `store`; if it does not raise for a missing url, make the test set a url `_Net` raises for).

- [ ] **Step 2: Failing tests in `tests/test_stash.py`**

```python
class Dropped(_Base):

    def setUp(self):
        _Base.setUp(self)
        self.scene_path = self.stashed("draft.ma", b"//Maya ASCII")
        self.fbx_path = self.stashed("clip.fbx", b"FBX" * 100)
        stash.refresh()

    def test_import_each_in_turn_one_status(self):
        self.fake_import_clip({"nodes": ["a"], "joints": 3, "curves": 9})
        message = stash.drop_import(["draft.ma", "clip.fbx"])
        imports = [k for _a, k in self.fake.file_calls if k.get("i")]
        self.assertEqual(len(imports), 1)
        self.assertEqual(len(self.imports), 1)
        self.assertIn("draft.ma", message)
        self.assertIn("clip.fbx", message)
        self.assertIn(" | ", message)
        self.assertEqual(self.statuses[-1], message)

    def test_a_file_gone_from_the_folder_is_named(self):
        os.remove(self.fbx_path)
        self.assertIn("clip.fbx is no longer in the stash", stash.drop_import(["clip.fbx"]))

    def test_to_share_sends_each_with_its_own_name(self):
        import maya_share
        sent = []
        saved = maya_share.send_file
        maya_share.send_file = lambda path, name: sent.append((path, name)) or "Sending " + name
        try:
            message = stash.drop_to_share(["draft.ma", "clip.fbx"])
        finally:
            maya_share.send_file = saved
        self.assertEqual([n for _p, n in sent], ["draft.ma", "clip.fbx"])
        self.assertEqual(sent[0][0], self.scene_path)
        self.assertIn("Sending draft.ma | Sending clip.fbx", message)
```

- [ ] **Step 3: Run to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_share.Dropped tests.test_stash.Dropped -v`
Expected: `AttributeError: module 'maya_share' has no attribute 'drop_import'` (and the same for stash).

- [ ] **Step 4: Implement in `maya_share.py`** (after `_local_or_fetch`)

```python
def when_local(rid, fn):
    """`fn(path)` for `rid`'s file: now when it is on this disk, else once its
    download lands (2026-10-21, a drop from the list). A row being fetched gets
    `fn` queued; one that cannot be had answers why. Returns what to say."""
    path, why = _local_or_fetch(rid)
    if path:
        return fn(path)
    st = state()
    transfer = st["transfers"].get(rid)
    entry = st["entries"].get(rid)
    if entry is not None and transfer is not None and not transfer.get("error") \
            and entry["record"]["state"] == "ready":
        st.setdefault("after_fetch", {}).setdefault(rid, []).append(fn)
        return "{0} is downloading - it follows when it lands.".format(
            entry["record"]["name"])
    return why


def _run_after_fetch(rid, path):
    for fn in state().get("after_fetch", {}).pop(rid, []):
        try:
            _status(fn(path))
        except Exception as exc:                             # noqa: BLE001
            print(traceback.format_exc())
            _status("Shared failed: {0}".format(exc))


def drop_import(rids):
    """Rows dropped on a viewport: each imported as the Import button does."""
    lines = [when_local(rid, lambda _path, r=rid: import_entry(r)) for rid in rids]
    return _status(" | ".join(line for line in lines if line))


def drop_to_stash(rids):
    """Rows dropped on Stash: each file copied into the stash, its own name."""
    import maya_stash

    def copy(rid):
        name = state()["entries"][rid]["record"]["name"]
        return lambda path: maya_stash.stash_file(path, name)
    lines = [when_local(rid, copy(rid)) if rid in state()["entries"]
             else "That file is no longer in the list." for rid in rids]
    return _status(" | ".join(line for line in lines if line))
```

In `_fetched`, after `save_history()` / `refresh()` and the `each_card` call, add `_run_after_fetch(rid, path)`. In `_fetch_failed`, after the `_say_all(...)` line, add:

```python
    waiting = st.get("after_fetch", {}).pop(rid, [])
    if waiting and entry is not None:
        _say_all("{0} did not download - the drop was not done.".format(
            entry["record"]["name"]))
```

Note: `import_entry` itself calls `_status`; `drop_import` writes the joined line last, which is what stays shown.

- [ ] **Step 5: Implement in `maya_stash.py`** (after `import_selected`)

```python
def _drop_one(name, verb):
    path = _path(name)
    if not os.path.isfile(path):
        return "{0} is no longer in the stash.".format(name)
    return verb(path, name)


def drop_import(names):
    """Files dropped on a viewport (2026-10-21): each imported in turn, as the
    Import button does. One status line names each result."""
    def one(path, name):
        return _import_fbx(path, name) if _is_fbx(name) else _import_scene(path, name)
    lines = [_drop_one(name, one) for name in names]
    refresh()
    return _status(" | ".join(lines))


def drop_to_share(names):
    """Files dropped on Shared: each sent to everybody under its own name,
    with no question (Send file's road)."""
    import maya_share
    lines = [_drop_one(name, lambda path, n: maya_share.send_file(path, n))
             for name in names]
    return _status(" | ".join(line for line in lines if line))
```

- [ ] **Step 6: Run the share and stash suites**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_share tests.test_stash -v`
Expected: all PASS.

- [ ] **Step 7: Commit** (`SkeldarAnim/maya_share.py SkeldarAnim/maya_stash.py tests/test_share.py tests/test_stash.py`; "feat(stash, shared): drop entry points, a drop waits for its download")

---

### Task 4: FileScene, the attach, the rail icon lit

**Files:**
- Modify: `SkeldarAnim/maya_filedrag.py` (append `FileScene`, `attach`, `_names_at`, `light`)
- Modify: `SkeldarAnim/maya_stash.py` (`build_panel`: `_attach_drag()` before `return`)
- Modify: `SkeldarAnim/maya_share.py` (`build_panel`: `_attach_drag()` before `return column`)
- Test: `tests/test_filedrag.py` (classes `Scene`, `OnAList`)

**Interfaces:**
- Consumes: Task 1's seams, Task 2's `section_under` / `aim_for` / `caption` / `DROPS` / `ICONS`, Task 3's `drop_*`.
- Produces: `FileScene(source, names_at=None, viewport_at=None, act=None)` - a listdrag scene; `attach(source, records_of)`; `light(section, on)`.

- [ ] **Step 1: Failing tests** (append to `tests/test_filedrag.py`)

```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None


class Scene(unittest.TestCase):
    """FileScene with the widget lookup, the viewport and the action faked."""

    def make(self, source, names=(), viewport=False):
        acted = []
        scene = fd.FileScene(source, names_at=lambda gx, gy: list(names),
                             viewport_at=lambda gx, gy: viewport,
                             act=lambda kind, items: acted.append((kind, [i.key for i in items])) or "ok")
        return scene, acted

    def test_over_the_other_list_is_not_the_hub(self):
        scene, _ = self.make("stash", ["skeldarShareList"])
        self.assertFalse(scene.over_hub(0, 0))
        self.assertEqual(scene.target(0, 0, None)["kind"], "send")

    def test_over_its_own_list_is_the_hub(self):
        scene, _ = self.make("stash", ["skeldarStashList"])
        self.assertTrue(scene.over_hub(0, 0))

    def test_a_viewport_imports(self):
        scene, acted = self.make("shared", ["modelPanel4"], viewport=True)
        aim = scene.target(0, 0, None)
        self.assertEqual(aim["kind"], "import")
        scene.drop([fd.Item("A.fbx", "shared", "rid1")], aim)
        self.assertEqual(acted, [("import", ["rid1"])])

    def test_seams(self):
        scene, _ = self.make("stash")
        self.assertEqual(scene.drops, fd.DROPS)
        self.assertEqual(scene.icon, "archive")
        self.assertEqual(scene.caption([fd.Item("A.fbx", "stash", "A.fbx")],
                                       fd.aim_for("stash", "shared", False)),
                         (u"A.fbx \u00b7 send to Shared", True))


@unittest.skipIf(QT is None, "no Qt")
class OnAList(unittest.TestCase):
    """The real listdrag on an offscreen QListWidget named like Stash's, a
    second list named like Shared's as the target."""

    def setUp(self):
        q = QT
        self.app = q.QtWidgets.QApplication.instance() or q.QtWidgets.QApplication([])
        self.source = q.QtWidgets.QListWidget()
        self.source.setObjectName("skeldarStashList")
        self.source.addItems(["A.fbx", "B.ma"])
        self.source.resize(200, 120)
        self.source.move(3000, 3000)
        self.source.show()
        self.other = q.QtWidgets.QListWidget()
        self.other.setObjectName("skeldarShareList")
        self.other.resize(200, 120)
        self.other.move(3400, 3000)
        self.other.show()
        for w in (self.source, self.other):
            self.addCleanup(w.deleteLater)
        self.acted = []
        scene = fd.FileScene("stash", viewport_at=lambda gx, gy: False,
                             act=lambda kind, items: self.acted.append((kind, [i.key for i in items])) or "ok")
        items = [fd.Item("A.fbx", "stash", "A.fbx"), fd.Item("B.ma", "stash", "B.ma")]
        from maya_uebridge import listdrag
        self.drag = listdrag.attach_widget(self.source, lambda: items, scene)

    def test_a_row_dropped_on_the_other_list_sends(self):
        port = self.source.viewport()
        start = self.source.visualItemRect(self.source.item(0)).center()
        target = self.other.mapToGlobal(self.other.rect().center())
        self.drag._press = None
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton

        def send(kind, local, button, buttons):
            g = port.mapToGlobal(local)
            ev = QT.QtGui.QMouseEvent(kind, QT.QtCore.QPointF(local), QT.QtCore.QPointF(g),
                                      button, buttons, QT.QtCore.Qt.NoModifier)
            QT.QtWidgets.QApplication.sendEvent(port, ev)
        send(E.MouseButtonPress, start, L, L)
        send(E.MouseMove, start + QT.QtCore.QPoint(40, 0), N, L)
        self.drag.drop_at(target.x(), target.y())
        self.assertEqual(self.acted, [("send", ["A.fbx"])])
```

- [ ] **Step 2: Run to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_filedrag -v`
Expected: `AttributeError: module 'maya_filedrag' has no attribute 'FileScene'`.

- [ ] **Step 3: Append to `maya_filedrag.py`**

```python
# ------------------------------------------------------------------ the scene

def _names_at(gx, gy):
    """The object names of the widget under the global point, then its
    parents'. Read afresh every time: a widget is never kept (trap 135)."""
    import maya_hubqt
    q = maya_hubqt.qt()
    widget = q.QtWidgets.QApplication.widgetAt(q.QtCore.QPoint(int(gx), int(gy)))
    names = []
    while widget is not None:
        names.append(widget.objectName())
        widget = widget.parentWidget()
    return names


def _viewport_at(gx, gy):
    from maya_scenesetup import droptarget
    view, _local = droptarget.Viewport.at(gx, gy)
    return view is not None


def _act(kind, items):
    """The release's action, one idle later (the ghost gone first)."""
    keys = [item.key for item in items]
    source = items[0].section
    if source == "stash":
        import maya_stash as module
        verb = {"import": module.drop_import, "send": module.drop_to_share}[kind]
    else:
        import maya_share as module
        verb = {"import": module.drop_import, "stash": module.drop_to_stash}[kind]
    import maya.utils
    import maya_hubcopy as hubcopy
    maya.utils.executeDeferred(hubcopy.wrap(lambda: module._run(lambda: verb(keys))))
    return ""


def light(section, on):
    """The rail icon of `section` shown pressed while a drag is over it."""
    try:
        import maya_hubqt
        q = maya_hubqt.qt()
        for top in q.QtWidgets.QApplication.topLevelWidgets():
            for button in top.findChildren(q.QtWidgets.QToolButton, JUMP + section):
                button.setDown(bool(on))
    except Exception:                                        # noqa: BLE001
        pass


class FileScene(object):
    """The listdrag scene of one section's list (`source`)."""

    drops = DROPS

    def __init__(self, source, names_at=None, viewport_at=None, act=None):
        self.source = source
        self.icon = ICONS[source]
        self._names_at = names_at or _names_at
        self._viewport_at = viewport_at or _viewport_at
        self._act = act or _act
        self._lit = None

    def scale(self):
        try:
            import maya.cmds as cmds
            return float(cmds.mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def snapshot(self):
        return None

    def _light(self, section):
        if section == self._lit:
            return
        if self._lit:
            light(self._lit, False)
        if section:
            light(section, True)
        self._lit = section

    def target(self, gx, gy, snap):
        under = section_under(self._names_at(gx, gy))
        aim = aim_for(self.source, under, under is None and self._viewport_at(gx, gy))
        self._light(aim.get("section"))
        return aim

    def over_hub(self, gx, gy):
        """The hub stops a drop - but not the other section's list or icon."""
        under = section_under(self._names_at(gx, gy))
        if under and under != self.source:
            return False
        if under == self.source:
            return True
        try:
            import maya_hubqt
            return maya_hubqt.on_hub(gx, gy)
        except Exception:                                    # noqa: BLE001
            return False

    def caption(self, records, aim):
        return caption(records, aim)

    def drop(self, records, aim):
        self._light(None)
        self._act(aim["kind"], list(records))
        return caption(records, aim)[0] + "..."

    def say(self, text):
        self._light(None)
        module = __import__("maya_stash" if self.source == "stash" else "maya_share")
        try:
            module._status(text)
        except Exception:                                    # noqa: BLE001
            pass


def attach(source, records_of):
    """The drag on `source`'s list in the card being built (the hub's or a
    popup copy's: listdrag resolves the name in the current scope). Where Qt
    cannot stand the list stays the list it was."""
    try:
        from maya_uebridge import listdrag
        import maya_hubcopy as hubcopy
        listdrag.attach(LISTS[source], hubcopy.wrap(records_of), FileScene(source))
    except Exception:                                        # noqa: BLE001
        import traceback
        print(traceback.format_exc())
```

Check `maya_hubcopy.wrap` (line 216) runs its function in the scope current when `wrap` was called; if it returns `fn` unchanged with no scope, `records_of` reads the hub's rows, which is right for the hub.

A cancel (Esc, right button) goes through `Drag._cancel` → `_say(CANCELLED)` → `scene.say`, which puts the icon out. A release off every target goes through `_say(aim["text"])` too.

- [ ] **Step 4: Wire the cards**

In `maya_stash.py` add:

```python
def _attach_drag():
    """The list's rows drag into a viewport or onto Shared (2026-10-21)."""
    import maya_filedrag
    import maya_stashstore  # noqa: F401 - names are file names
    maya_filedrag.attach("stash", lambda: [
        maya_filedrag.Item(name, "stash", name) for name in _view()["rows"]])
```

and call `_attach_drag()` in `build_panel` right after `refresh()` (before `watch`).

In `maya_share.py` add:

```python
def _attach_drag():
    """The list's rows drag into a viewport or onto Stash (2026-10-21)."""
    import maya_filedrag
    entries = state()["entries"]
    maya_filedrag.attach("shared", lambda: [
        maya_filedrag.Item(entries[rid]["record"]["name"] if rid in entries else rid,
                           "shared", rid) for rid in _view()["rows"]])
```

and call `_attach_drag()` in `build_panel` after `refresh()`. (Read `entries` inside the lambda via `state()["entries"]` if `state()` can be replaced between builds; write it as `state()["entries"]` inside to be safe.)

- [ ] **Step 5: Run the drag tests and the card suites**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_filedrag tests.test_stash tests.test_share tests.test_uebridge_listdrag -v`
Expected: all PASS (the card tests run on a fake cmds where `listdrag.attach` finds no control: `attach` answers None, nothing raises).

- [ ] **Step 6: Commit** (`SkeldarAnim/maya_filedrag.py SkeldarAnim/maya_stash.py SkeldarAnim/maya_share.py tests/test_filedrag.py`; "feat(stash, shared): rows drag into the scene and between the two")

---

### Task 5: verify standalone, the full suite, CLAUDE.md

**Files:**
- Create: `docs/superpowers/plans/verify_stash_share_drag.py`
- Modify: `CLAUDE.md` (a section after "Shared: scenes and FBX between colleagues, one press")

- [ ] **Step 1: Write the verify** (mayapy standalone, a scratch `MAYA_APP_DIR` set by the caller)

```python
"""Stash / Shared drops, standalone (2026-10-21). Run:
    $env:MAYA_APP_DIR = "<scratch>"; mayapy verify_stash_share_drag.py
The drop entry points the drag calls, on a real scene: a stashed scene and FBX
imported, a shared file (downloaded by a fake net) copied into the stash."""
import os, sys, tempfile, zipfile
import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
sys.path.insert(0, r"C:/!!!Work/MayaScripts/SkeldarAnim")
import maya_stash, maya_share, maya_sharerecords as records

FAILS = []
def gate(n, ok, text):
    print("gate %d %s %s" % (n, "ok" if ok else "FAILED", text))
    if not ok:
        FAILS.append(n)

work = tempfile.mkdtemp(prefix="dragverify_")
cmds.polyCube(name="draftCube")
draft = os.path.join(work, "draft.ma")
cmds.file(rename=draft); cmds.file(save=True, type="mayaAscii")
cmds.file(new=True, force=True)
cmds.loadPlugin("fbxmaya", quiet=True)
cmds.joint(name="clipRoot"); cmds.setKeyframe("clipRoot.tx", t=0, v=0); cmds.setKeyframe("clipRoot.tx", t=10, v=5)
clip = os.path.join(work, "clip.fbx")
import maya.mel as mel
mel.eval('FBXExport -f "%s"' % clip.replace("\\", "/"))
cmds.file(new=True, force=True)

maya_stash.stash_file(draft, "draft.ma")
maya_stash.stash_file(clip, "clip.fbx")
message = maya_stash.drop_import(["draft.ma", "clip.fbx"])
gate(1, cmds.objExists("draftCube"), "the scene came in: %s" % message)
gate(2, any(j.endswith("clipRoot") for j in cmds.ls(type="joint")), "the FBX came in as a skeleton")
gate(3, " | " in message, "one line naming both")

class Net(object):
    def download(self, url, path, progress=None):
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("Long.fbx", open(clip, "rb").read())
maya_share.net = Net()
maya_share._spawn = lambda fn: fn()
maya_share._defer = lambda fn, *a: fn(*a)
rid = records.new_id()
rec = records.with_state(records.make_record("sending", rid, "Oleg", "theirs", "Long.fbx", 10, 0),
                         "ready", url="https://litter.catbox.moe/abc.zip", zip=10)
maya_share.receive(rec)
answer = maya_share.drop_to_stash([rid])
gate(4, "Long.fbx" in maya_stash.scan_names() if hasattr(maya_stash, "scan_names")
     else os.path.isfile(os.path.join(maya_stash.folder(), "Long.fbx")), "copied into the stash: %s" % answer)
print("verify: %d of 4 gates failed" % len(FAILS))
```

Before running, read `records.make_record` / `with_state` signatures in `maya_sharerecords.py` and `receive` in `maya_share.py`: a record whose `sent` is 0 may be expired - give it `time.time()`. Fix the record lines to what `receive` accepts.

- [ ] **Step 2: Run it**

Run (PowerShell): `$env:MAYA_APP_DIR = "$env:TEMP\dragverify_app"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\verify_stash_share_drag.py`
Expected: `verify: 0 of 4 gates failed`.

- [ ] **Step 3: The full suite**

Run: `$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
Expected: OK (the count in the summary).

- [ ] **Step 4: CLAUDE.md** - add after the Shared section:

```markdown
## Stash and Shared: rows dragged between them and into the scene (2026-10-21)

The animator: «драг энд дроп того что находится в сташе и в шаре между этими
папками и на сцену». Spec `docs/superpowers/specs/2026-10-21-stash-shared-drag-design.md`.
- A row (every picked row) pressed and carried: onto a viewport = Import as the
  card's button (`maya_stash.drop_import`, `maya_share.drop_import`); Stash onto
  Shared = Send file, no question (`drop_to_share`); Shared onto Stash = a copy
  under its name (`drop_to_stash`). A section is its list (hub card or popup
  copy) or its rail icon, shown pressed while a drag is over it.
- A Shared file not downloaded yet is fetched first: `maya_share.when_local`
  queues the action on `state()["after_fetch"]`, run by `_fetched`, dropped
  (and said) by `_fetch_failed`.
- The drag is the UE Bridge list's (`maya_uebridge.listdrag`): a scene may now
  bring `caption`, `drops` and `icon`. `maya_filedrag` holds the pure rules
  (`section_under`, `aim_for`, `caption`) and `FileScene`.
- Proof: `tests/test_filedrag.py`, the `Dropped` classes of test_share /
  test_stash, `verify_stash_share_drag.py` 4/4 standalone. Not seen in a GUI
  Maya: the real mouse, the rail icon pressed.
```

- [ ] **Step 5: Commit** (`docs/superpowers/plans/verify_stash_share_drag.py CLAUDE.md`; "docs: Stash / Shared drag verified standalone, CLAUDE.md")
