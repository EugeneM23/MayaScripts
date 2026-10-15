# Scene Tabs, Stage 1 - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Several scenes open in one Maya as browser-like tabs: each tab a scene file imported into a namespace of its own, the inactive ones hidden, switched with their own time, view, selection and layout, saved back to their own plain files.

**Architecture:** A new package `SkeldarAnim/maya_scenetabs/`. `records` holds every decision that needs no Maya (names, a file's fps, the session's JSON, what a Save means); `session` keeps the session on a `network` node and moves a tab's nodes between its namespace and the root namespace by UUID; `layers` keeps one session-owned animation-layer root; `opening`, `switching` and `saving` are the operations; `hooks` redirects Maya's own Save / Open / New; `bar` is the Qt tab bar docked above the viewport.

**Tech Stack:** Maya 2027 `maya.cmds` + `maya.api.OpenMaya` (scene message callbacks), PySide6 through `maya_hubqt.qt()` (the bar only), stdlib `unittest` under `mayapy`.

**Spec:** `docs/superpowers/specs/2026-10-15-scene-tabs-design.md` (Task 1 adds the addendum of what was measured while planning).

**Ships with stage 2, never alone** (`docs/superpowers/plans/2026-10-15-scene-tabs-stage2.md`): with a tab active the current namespace is the tab's, and the plugin's own creations then double the tab's prefix - measured while planning stage 2, Retarget inside a tab fails with «setAttr: No object matches name: tab_plain:Manny_Rig:MoCapConstraints.tx» and Add Character leaves a `tab_plain:tab_plain:Manny_Rig` namespace behind.

## Global Constraints

- Every `maya_scenetabs` module but `bar` imports no Qt; `records` imports only the stdlib and `maya_sharerecords` (a subprocess test pins it).
- A tab is a `.ma` / `.mb` file imported with `preserveReferences=True, executeScriptNodes=False` into the namespace `tab_<stem>` (illegal characters `_`), made free with a trailing number.
- The session node is `skeldarSceneTabs` (type `network`, root namespace), its JSON in the string attribute `skeldarSceneTabs`; the session's animation-layer root is `skeldarTabsLayerRoot`; a tab's layer root is `<tab>:AnimLayerRoot` under it and is written into the tab's file as `BaseAnimation`.
- Tab mode means two or more tabs. With one scene open nothing is intercepted and the scene sits in the root namespace.
- Batch mode (`cmds.about(batch=True)`) installs no callbacks, jobs, filter or bar unless the caller forces it (the verify).
- Hiding a tab uses `lodVisibility` and `hiddenInOutliner` on its top DAG nodes, never `visibility`.
- A switch is ONE undo chunk named `skeldarTabSwitch`. A save runs unrecorded (`undoInfo -stateWithoutFlush false`, never inside an open chunk - trap 145).
- Names are moved by UUID; every `cmds.rename` passes `ignoreShape=True`.
- Run the tests from the repo root: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <module> -v` (PowerShell; no `2>&1` on mayapy). Qt tests need `$env:QT_QPA_PLATFORM = 'offscreen'`.
- Run the verify in a scratch prefs folder: `$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_scene_tabs.py <phase|all>`. Never through the animator's port 7001; a GUI check is the animator's (CLAUDE.md memory: live checks are theirs).
- Commits stage only this plan's files (`git add <paths>`): other sessions work in the same checkout. Messages go through a file (`git commit -F`), ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## File Structure

| File | Responsibility |
|---|---|
| `SkeldarAnim/maya_scenetabs/__init__.py` | the package; `show()` resolved lazily (no Maya import on `import maya_scenetabs`) |
| `SkeldarAnim/maya_scenetabs/records.py` | stdlib: constants, tab namespaces, a file's fps and ranges, the session JSON, furniture, Save vs Save As, the bar's items |
| `SkeldarAnim/maya_scenetabs/session.py` | the session node; which nodes are a tab's; `lift` / `lower` a tab between its namespace and the root namespace; `move_into` (tab 1) |
| `SkeldarAnim/maya_scenetabs/layers.py` | the session-owned layer root, a tab's layer root, detach / attach for a save, adopt a new layer, flatten back to one scene |
| `SkeldarAnim/maya_scenetabs/switching.py` | hide / show, a tab's time, view, selection and layout, the switch chunk, next / previous |
| `SkeldarAnim/maya_scenetabs/opening.py` | the scene becoming tab 1, open / new / close / reload a tab, back to one scene, restore a session, tabs off, the quit question |
| `SkeldarAnim/maya_scenetabs/saving.py` | save / save as a tab into a plain file |
| `SkeldarAnim/maya_scenetabs/hooks.py` | Maya's Save / Open / New redirected, new layers adopted, Undo / Redo / SceneOpened jobs, the quit filter |
| `SkeldarAnim/maya_scenetabs/bar.py` | the workspaceControl and its Qt tab bar |
| `SkeldarAnim/install.py` | modify: payload row `maya_scenetabs` |
| `SkeldarAnim/maya_hotkeys.py` | modify: rows `window.tabs`, `tabs.next`, `tabs.previous` |
| `SkeldarAnim/maya_hub.py` | modify: `build()` shows the bar once per session (`_tabs_bar_soon`) |
| `tests/test_scenetabs_records.py` | records, and its stdlib purity |
| `tests/test_scenetabs_bar.py` | the bar offscreen on fake actions |
| `docs/superpowers/plans/verify_scene_tabs.py` | the proof in mayapy standalone, phases `convert layers open_close switch save hooks restore` |
| `docs/superpowers/specs/2026-10-15-scene-tabs-design.md` | modify: the planning addendum |
| `CLAUDE.md` | modify: the section for scene tabs |

---

### Task 1: The package and `records` (pure)

**Files:**
- Create: `SkeldarAnim/maya_scenetabs/__init__.py`
- Create: `SkeldarAnim/maya_scenetabs/records.py`
- Create: `tests/test_scenetabs_records.py`
- Modify: `SkeldarAnim/install.py` (the `_PAYLOAD` tuple, after `"maya_walk",`)
- Modify: `tests/test_install.py` (one assertion)
- Modify: `docs/superpowers/specs/2026-10-15-scene-tabs-design.md` (append the addendum)

**Interfaces:**
- Produces (used by every later task): the constants `SESSION_NODE`, `SESSION_ATTR`, `LAYER_ROOT`, `TAB_LAYER_ROOT`, `FILE_LAYER_ROOT`, `CONFIG_NODE`, `CONFIG_SCRIPT_TYPE`, `WORKSPACE_PREFIX`, `TAB_PREFIX`, `UNTITLED`, `VERSION`, `SYSTEM_NAMESPACES`, `FILE_TYPES`, `RANGE_KEYS`; and
  `namespace_for(path, taken) -> str`, `unit_from_ma(text) -> str`, `unit_from_mb(data) -> str`, `read_unit(path) -> str`, `ranges_from_script(text) -> dict`, `config_script(ranges) -> str`, `range_text(ranges) -> str`, `is_furniture(leaf, node_type) -> bool`, `empty_state() -> dict`, `new_tab(namespace, path, unit, ranges, mtime=0.0) -> dict`, `dumps(state) -> str`, `loads(text) -> dict`, `tab(state, namespace) -> dict|None`, `with_tab(state, tab, index=None) -> dict`, `removed(state, namespace) -> dict`, `neighbour(state, namespace) -> str`, `title(tab) -> str`, `bar_items(state, scene_name="", scene_modified=False) -> list`, `same_file(a, b) -> bool`, `save_plan(target, session_name) -> (str, str)`, `is_autosave(target, folder) -> bool`, `changed_on_disk(path, mtime) -> bool`, `holds_session(path) -> bool`, `session_name(folder, stamp) -> str`.
- A tab is a dict: `{"ns", "path", "mtime", "unit", "ranges", "frame", "modified", "layout", "views", "selection"}`. The state: `{"version", "active", "session", "tabs": [tab, ...]}`.

- [ ] **Step 1: Write the failing tests**

`tests/test_scenetabs_records.py`:

```python
"""maya_scenetabs.records: the session as data, pure (2026-10-15).

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""
import os
import subprocess
import sys
import tempfile
import unittest

from maya_scenetabs import records

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


def _tab(ns, path="", modified=False, unit="ntsc", ranges=None):
    tab = records.new_tab(ns, path, unit, ranges or {"minTime": 0.0, "maxTime": 50.0})
    tab["modified"] = modified
    return tab


class Names(unittest.TestCase):

    def test_a_tab_namespace_is_its_files_stem_with_the_prefix(self):
        self.assertEqual(records.namespace_for("C:/a/attack_01.ma", []), "tab_attack_01")

    def test_illegal_characters_become_underscores(self):
        self.assertEqual(records.namespace_for("C:/a/my attack-v2.final.mb", []), "tab_my_attack_v2_final")

    def test_a_taken_namespace_gets_a_number(self):
        self.assertEqual(records.namespace_for("x/attack.ma", ["tab_attack", ":tab_attack1"]), "tab_attack2")

    def test_no_file_is_untitled(self):
        self.assertEqual(records.namespace_for("", ["UI", "shared"]), "tab_untitled")

    def test_the_prefix_keeps_a_rigs_namespace_free(self):
        # a tab opened from assets/Manny_Rig.ma must not BE the namespace its rig moves into on a save
        self.assertNotEqual(records.namespace_for("assets/Manny_Rig.ma", []), "Manny_Rig")


class Units(unittest.TestCase):

    def test_the_ma_header_line(self):
        text = '//Maya ASCII 2027 scene\nrequires maya "2027";\ncurrentUnit -l centimeter -a degree -t ntsc;\n'
        self.assertEqual(records.unit_from_ma(text), "ntsc")

    def test_the_ma_header_with_a_frame_rate(self):
        self.assertEqual(records.unit_from_ma("currentUnit -l centimeter -a degree -t 23.976fps;"), "23.976fps")

    def test_no_unit_line_is_empty(self):
        self.assertEqual(records.unit_from_ma("createNode transform;"), "")

    def test_the_mb_tuni_chunk_as_measured(self):
        # 2026-10-15, Maya 2027: b'TUNI' + 4 bytes + an 8-byte big-endian size + the name
        data = b"FOR8\x00\x00" + b"TUNI\xfc\x00\x00\x00" + (4).to_bytes(8, "big") + b"film\x00\x00\x00\x00"
        self.assertEqual(records.unit_from_mb(data), "film")
        data = b"TUNI\xfc\x00\x00\x00" + (5).to_bytes(8, "big") + b"ntscf\x00\x00\x00"
        self.assertEqual(records.unit_from_mb(data), "ntscf")

    def test_a_broken_mb_chunk_is_empty(self):
        self.assertEqual(records.unit_from_mb(b"TUNI\x00\x00\x00\x00" + (900).to_bytes(8, "big")), "")
        self.assertEqual(records.unit_from_mb(b"no chunk here"), "")

    def test_read_unit_reads_either_kind_from_disk(self):
        folder = tempfile.mkdtemp()
        ma = os.path.join(folder, "a.ma")
        with open(ma, "w") as fh:
            fh.write("currentUnit -l centimeter -a degree -t film;\n")
        mb = os.path.join(folder, "b.mb")
        with open(mb, "wb") as fh:
            fh.write(b"TUNI\xfc\x00\x00\x00" + (4).to_bytes(8, "big") + b"ntsc\x00\x00\x00\x00")
        self.assertEqual(records.read_unit(ma), "film")
        self.assertEqual(records.read_unit(mb), "ntsc")
        self.assertEqual(records.read_unit(os.path.join(folder, "missing.ma")), "")


class Ranges(unittest.TestCase):

    def test_ranges_from_the_config_node(self):
        got = records.ranges_from_script("playbackOptions -min 5 -max 40 -ast 0 -aet 45 ;")
        self.assertEqual(got, {"minTime": 5.0, "maxTime": 40.0, "animationStartTime": 0.0, "animationEndTime": 45.0})

    def test_the_config_script_round_trips(self):
        ranges = {"minTime": 1.25, "maxTime": 150.0, "animationStartTime": 0.0, "animationEndTime": 200.5}
        self.assertEqual(records.ranges_from_script(records.config_script(ranges)), ranges)

    def test_no_ranges_no_script(self):
        self.assertEqual(records.config_script({}), "")

    def test_range_text(self):
        self.assertEqual(records.range_text({"minTime": 0.0, "maxTime": 50.0}), "0-50")
        self.assertEqual(records.range_text({}), "?")


class Furniture(unittest.TestCase):

    def test_maya_managers_and_the_files_copies_are_furniture(self):
        for leaf, kind in (("renderLayerManager", "renderLayerManager"), ("defaultRenderLayer", "renderLayer"),
                           ("lightLinker1", "lightLinker"), ("shapeEditorManager", "shapeEditorManager"),
                           ("UsdDefaultRenderSettings", "UsdDefaultSettings"), ("defaultLayer", "displayLayer"),
                           ("uiConfigurationScriptNode", "script")):
            self.assertTrue(records.is_furniture(leaf, kind), leaf)

    def test_the_config_node_and_a_users_nodes_are_not(self):
        self.assertFalse(records.is_furniture("sceneConfigurationScriptNode", "script"))
        self.assertFalse(records.is_furniture("hero", "transform"))
        self.assertFalse(records.is_furniture("cubesLayer", "displayLayer"))
        self.assertFalse(records.is_furniture("Layer1", "animLayer"))


class State(unittest.TestCase):

    def test_round_trip(self):
        state = records.empty_state()
        state = records.with_tab(state, _tab("tab_a", "C:/a.ma"))
        state = records.with_tab(state, _tab("tab_b", "C:/b.ma"))
        state["active"], state["session"] = "tab_b", "C:/s/session_1.ma"
        self.assertEqual(records.loads(records.dumps(state)), state)

    def test_bad_json_is_an_empty_state(self):
        self.assertEqual(records.loads("{nope"), records.empty_state())
        self.assertEqual(records.loads('{"version": 99, "tabs": []}'), records.empty_state())

    def test_an_unknown_active_falls_back_to_the_first_tab(self):
        state = records.with_tab(records.empty_state(), _tab("tab_a"))
        state["active"] = "tab_gone"
        self.assertEqual(records.loads(records.dumps(state))["active"], "tab_a")

    def test_with_tab_replaces_in_place_and_inserts_at_an_index(self):
        state = records.empty_state()
        for ns in ("tab_a", "tab_b", "tab_c"):
            state = records.with_tab(state, _tab(ns))
        state = records.with_tab(state, _tab("tab_b", "C:/new.ma"))
        self.assertEqual([t["ns"] for t in state["tabs"]], ["tab_a", "tab_b", "tab_c"])
        self.assertEqual(records.tab(state, "tab_b")["path"], "C:/new.ma")
        state = records.with_tab(state, _tab("tab_x"), index=1)
        self.assertEqual([t["ns"] for t in state["tabs"]], ["tab_a", "tab_x", "tab_b", "tab_c"])

    def test_removed_hands_active_to_the_right_neighbour_else_the_left(self):
        state = records.empty_state()
        for ns in ("tab_a", "tab_b", "tab_c"):
            state = records.with_tab(state, _tab(ns))
        state["active"] = "tab_b"
        self.assertEqual(records.removed(state, "tab_b")["active"], "tab_c")
        state["active"] = "tab_c"
        self.assertEqual(records.removed(state, "tab_c")["active"], "tab_b")
        state["active"] = "tab_a"
        self.assertEqual(records.removed(state, "tab_c")["active"], "tab_a")


class Bar(unittest.TestCase):

    def test_one_scene_is_one_item_without_a_close_button(self):
        items = records.bar_items(records.empty_state(), "C:/a/attack.ma", True)
        self.assertEqual(items, [{"ns": "", "text": "attack*", "tip": "C:/a/attack.ma", "active": True, "closable": False}])

    def test_an_unsaved_single_scene_is_untitled(self):
        self.assertEqual(records.bar_items(records.empty_state(), "", False)[0]["text"], "untitled")

    def test_tabs_carry_star_tooltip_and_active(self):
        state = records.empty_state()
        state = records.with_tab(state, _tab("tab_a", "C:/a/attack.ma", modified=True))
        state = records.with_tab(state, _tab("tab_b", "C:/a/walk.mb", unit="film"))
        state["active"] = "tab_b"
        items = records.bar_items(state, "C:/s/session.ma", scene_modified=True)
        self.assertEqual([i["text"] for i in items], ["attack*", "walk*"])
        self.assertEqual([i["active"] for i in items], [False, True])
        self.assertEqual(items[1]["tip"], "C:/a/walk.mb\nfilm, 0-50")
        self.assertTrue(all(i["closable"] for i in items))


class Saves(unittest.TestCase):

    def test_saving_to_the_sessions_name_is_save(self):
        self.assertEqual(records.save_plan("C:/s/session_1.ma", "C:/s/session_1.ma"), ("save", ""))
        self.assertEqual(records.save_plan("", "C:/s/session_1.ma"), ("save", ""))

    def test_any_other_name_is_save_as(self):
        self.assertEqual(records.save_plan("C:/w/new.ma", "C:/s/session_1.ma"), ("save_as", "C:/w/new.ma"))

    def test_same_file_ignores_case_and_slashes(self):
        self.assertTrue(records.same_file("C:/A/b.ma", "c:\\a\\B.ma"))

    def test_autosave_is_inside_the_autosave_folder(self):
        self.assertTrue(records.is_autosave("C:/p/autosave/session_1.0001.ma", "C:/p/autosave/"))
        self.assertFalse(records.is_autosave("C:/p/scenes/a.ma", "C:/p/autosave/"))
        self.assertFalse(records.is_autosave("C:/p/a.ma", ""))

    def test_changed_on_disk(self):
        path = os.path.join(tempfile.mkdtemp(), "a.ma")
        with open(path, "w") as fh:
            fh.write("x")
        stamp = os.path.getmtime(path)
        self.assertFalse(records.changed_on_disk(path, stamp))
        os.utime(path, (stamp + 30, stamp + 30))
        self.assertTrue(records.changed_on_disk(path, stamp))
        self.assertFalse(records.changed_on_disk(path, 0.0))

    def test_holds_session_finds_the_node_name_in_the_file(self):
        folder = tempfile.mkdtemp()
        yes, no = os.path.join(folder, "s.ma"), os.path.join(folder, "n.ma")
        with open(yes, "w") as fh:
            fh.write('createNode network -n "skeldarSceneTabs";\n')
        with open(no, "w") as fh:
            fh.write('createNode transform -n "hero";\n')
        self.assertTrue(records.holds_session(yes))
        self.assertFalse(records.holds_session(no))

    def test_session_name(self):
        self.assertEqual(records.session_name("C:/u/SkeldarTabs/", "20261015_120000"),
                         "C:/u/SkeldarTabs/session_20261015_120000.ma")


class Purity(unittest.TestCase):

    def test_records_imports_no_maya_and_no_qt(self):
        code = ("import sys; sys.path.insert(0, %r); from maya_scenetabs import records;"
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6', 'shiboken6')]; print(bad)"
                % PLUGIN)
        out = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenetabs_records -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'maya_scenetabs'`.

- [ ] **Step 3: Write the package and `records`**

`SkeldarAnim/maya_scenetabs/__init__.py`:

```python
"""Scene tabs (2026-10-15): several scenes in one Maya, switched like browser tabs.

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md. `show()` is
resolved lazily so `import maya_scenetabs` pulls in neither Maya nor Qt.
"""


def __getattr__(name):
    if name == "show":
        from . import bar
        return bar.show
    raise AttributeError(name)
```

`SkeldarAnim/maya_scenetabs/records.py`:

```python
"""Scene tabs: the session as data (stdlib only; a subprocess test pins it).

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md (and its addendum).
Every tab is a scene file imported into a namespace of its own. What the scene
code needs to decide without Maya lives here: a tab's namespace, a file's fps
and ranges, the session's JSON, which nodes are Maya's furniture, what a Save
means, and what the bar shows.
"""

import json
import os
import re

import maya_sharerecords

SESSION_NODE = "skeldarSceneTabs"
SESSION_ATTR = "skeldarSceneTabs"
#  Maya keeps ONE root animation layer and remembers it internally; deleting it
#  left the other layers rootless and the next new layer crashed mayapy
#  (measured 2026-10-15). So the session owns the root while tabs are on.
LAYER_ROOT = "skeldarTabsLayerRoot"
TAB_LAYER_ROOT = "AnimLayerRoot"      # Maya's own rename of an imported BaseAnimation
FILE_LAYER_ROOT = "BaseAnimation"
CONFIG_NODE = "sceneConfigurationScriptNode"
CONFIG_SCRIPT_TYPE = 6                # what Maya writes for its configuration node
WORKSPACE_PREFIX = "SkeldarTab_"
TAB_PREFIX = "tab_"
UNTITLED = "untitled"
VERSION = 1
SYSTEM_NAMESPACES = ("UI", "shared")
FILE_TYPES = {".ma": "mayaAscii", ".mb": "mayaBinary"}
RANGE_KEYS = ("minTime", "maxTime", "animationStartTime", "animationEndTime")
_RANGE_FLAGS = (("min", "minTime"), ("max", "maxTime"),
                ("ast", "animationStartTime"), ("aet", "animationEndTime"))

#  The scene's own managers: an import makes copies of them inside the tab's
#  namespace (they clashed with the root's on the first save, measured), and a
#  tab never moves them.
FURNITURE_TYPES = frozenset((
    "lightLinker", "partition", "renderLayer", "renderLayerManager",
    "displayLayerManager", "ikSolver", "ikRPsolver", "ikSCsolver",
    "ikSplineSolver", "ikSystem", "shapeEditorManager", "poseInterpolatorManager",
    "UsdDefaultSettings", "nodeGraphEditorInfo", "hyperLayout", "hyperView",
    "hyperGraphInfo", "time", "sequenceManager", "defaultRenderUtilityList",
    "defaultShaderList", "defaultTextureList", "defaultLightList"))
FURNITURE_NAMES = frozenset(("uiConfigurationScriptNode", "defaultLayer",
                             "sharedReferenceNode"))

_ILLEGAL = re.compile(r"[^A-Za-z0-9_]")
_UNIT_MA = re.compile(r"currentUnit\b[^;]*?-t(?:ime)?\s+([A-Za-z0-9_.]+)")
_UNIT = re.compile(r"^[A-Za-z0-9_.]+$")


# ------------------------------------------------------------------ names

def namespace_for(path, taken):
    """`tab_<stem>`, made legal and free among `taken` (with or without a
    leading colon). The prefix keeps a tab from BEING a namespace its own rig
    moves into on a save (a tab opened from assets/Manny_Rig.ma)."""
    stem = os.path.splitext(os.path.basename(path or ""))[0] or UNTITLED
    base = TAB_PREFIX + _ILLEGAL.sub("_", stem)
    used = set(t.lstrip(":") for t in taken or ())
    if base not in used:
        return base
    number = 1
    while "%s%d" % (base, number) in used:
        number += 1
    return "%s%d" % (base, number)


# ------------------------------------------------------------------ a file's time

def unit_from_ma(text):
    """The time unit of a `.ma` header (`currentUnit ... -t ntsc;`), or ""."""
    match = _UNIT_MA.search(text or "")
    return match.group(1) if match else ""


def unit_from_mb(data):
    """The time unit of a `.mb` header: the TUNI chunk (measured 2026-10-15:
    the tag, 4 bytes, an 8-byte big-endian size, the name), or ""."""
    at = (data or b"").find(b"TUNI")
    if at < 0 or len(data) < at + 16:
        return ""
    size = int.from_bytes(data[at + 8:at + 16], "big")
    if not 0 < size <= 32:
        return ""
    raw = data[at + 16:at + 16 + size].split(b"\0")[0]
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return ""
    return text if _UNIT.match(text) else ""


def read_unit(path, head=65536):
    """A scene file's time unit read from its header, or "" (unknown kind,
    unreadable, no unit line)."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(head)
    except OSError:
        return ""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".ma":
        return unit_from_ma(data.decode("utf-8", "replace"))
    if ext == ".mb":
        return unit_from_mb(data)
    return ""


def ranges_from_script(text):
    """The playback and animation ranges in a configuration node's MEL,
    parsed, never evaluated."""
    found = maya_sharerecords.playback_from_script(text)
    return {key: found[key] for key in RANGE_KEYS if key in found}


def _number(value):
    text = ("%.6f" % float(value)).rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def config_script(ranges):
    """The MEL a tab's configuration node carries into its file."""
    parts = ["-%s %s" % (flag, _number(ranges[key]))
             for flag, key in _RANGE_FLAGS if key in (ranges or {})]
    return ("playbackOptions %s ;" % " ".join(parts)) if parts else ""


def range_text(ranges):
    ranges = ranges or {}
    if "minTime" not in ranges or "maxTime" not in ranges:
        return "?"
    return "%s-%s" % (_number(ranges["minTime"]), _number(ranges["maxTime"]))


def is_furniture(leaf, node_type):
    """A node of the scene's own, never a tab's."""
    return node_type in FURNITURE_TYPES or leaf in FURNITURE_NAMES


# ------------------------------------------------------------------ the session

def empty_state():
    return {"version": VERSION, "active": "", "session": "", "tabs": []}


def new_tab(namespace, path, unit, ranges, mtime=0.0):
    return {"ns": namespace, "path": path or "", "mtime": float(mtime or 0.0),
            "unit": unit or "", "ranges": dict(ranges or {}), "frame": None,
            "modified": False, "layout": WORKSPACE_PREFIX + namespace,
            "views": [], "selection": []}


def dumps(state):
    return json.dumps(state, sort_keys=True)


def loads(text):
    """The state in a session node, or an empty one for anything else."""
    try:
        state = json.loads(text or "")
    except ValueError:
        return empty_state()
    if not isinstance(state, dict) or state.get("version") != VERSION \
            or not isinstance(state.get("tabs"), list):
        return empty_state()
    out = empty_state()
    for item in state["tabs"]:
        if not isinstance(item, dict) or not item.get("ns"):
            continue
        tab = new_tab(item["ns"], item.get("path"), item.get("unit"),
                      item.get("ranges"), item.get("mtime"))
        for key in ("frame", "modified", "layout", "views", "selection"):
            if key in item:
                tab[key] = item[key]
        out["tabs"].append(tab)
    names = [t["ns"] for t in out["tabs"]]
    out["active"] = state.get("active") if state.get("active") in names else (names[0] if names else "")
    out["session"] = state.get("session") or ""
    return out


def tab(state, namespace):
    for item in state["tabs"]:
        if item["ns"] == namespace:
            return item
    return None


def with_tab(state, item, index=None):
    """A new state holding `item`: in its old place when the namespace is
    there, else at `index` (the end by default)."""
    out = dict(state, tabs=list(state["tabs"]))
    for position, old in enumerate(out["tabs"]):
        if old["ns"] == item["ns"]:
            out["tabs"][position] = item
            return out
    if index is None:
        out["tabs"].append(item)
    else:
        out["tabs"].insert(index, item)
    return out


def neighbour(state, namespace):
    """The tab that takes over when `namespace` closes: the right-hand one,
    else the left-hand one, else none."""
    names = [t["ns"] for t in state["tabs"]]
    if namespace not in names:
        return state.get("active", "")
    at = names.index(namespace)
    if at + 1 < len(names):
        return names[at + 1]
    return names[at - 1] if at > 0 else ""


def removed(state, namespace):
    out = dict(state, tabs=[t for t in state["tabs"] if t["ns"] != namespace])
    if state.get("active") == namespace:
        out["active"] = neighbour(state, namespace)
    return out


def title(item):
    stem = os.path.splitext(os.path.basename(item.get("path") or ""))[0] or UNTITLED
    return stem + ("*" if item.get("modified") else "")


def bar_items(state, scene_name="", scene_modified=False):
    """What the bar shows: one item per tab, or the one open scene."""
    if not state["tabs"]:
        stem = os.path.splitext(os.path.basename(scene_name or ""))[0] or UNTITLED
        return [{"ns": "", "text": stem + ("*" if scene_modified else ""),
                 "tip": scene_name or "not saved yet", "active": True, "closable": False}]
    items = []
    for item in state["tabs"]:
        active = item["ns"] == state["active"]
        modified = bool(item.get("modified") or (active and scene_modified))
        items.append({"ns": item["ns"], "text": title(dict(item, modified=modified)),
                      "tip": "%s\n%s, %s" % (item.get("path") or "not saved yet",
                                              item.get("unit") or "?", range_text(item.get("ranges"))),
                      "active": active, "closable": True})
    return items


# ------------------------------------------------------------------ saving

def same_file(first, second):
    norm = lambda p: os.path.normcase(os.path.normpath(p or ""))    # noqa: E731
    return bool(first and second) and norm(first) == norm(second)


def save_plan(target, session_name):
    """What Maya's Save means while tabs are on: the session's own name (or
    none) is Save (the active tab into its own file); any other name is Save As."""
    if not target or same_file(target, session_name):
        return "save", ""
    return "save_as", target


def is_autosave(target, folder):
    if not target or not folder:
        return False
    norm = lambda p: os.path.normcase(os.path.normpath(p))          # noqa: E731
    return norm(target).startswith(norm(folder).rstrip("\\/") + os.sep)


def changed_on_disk(path, mtime):
    """The file was written by somebody else since the tab read or saved it."""
    if not mtime or not path or not os.path.isfile(path):
        return False
    return abs(os.path.getmtime(path) - float(mtime)) > 1e-3


def holds_session(path, chunk=1 << 22):
    """The file holds a session node: a session saved by autosave or a crash."""
    needle = SESSION_NODE.encode("ascii")
    tail = b""
    try:
        with open(path, "rb") as handle:
            while True:
                data = handle.read(chunk)
                if not data:
                    return False
                if needle in tail + data:
                    return True
                tail = data[-len(needle):]
    except OSError:
        return False


def session_name(folder, stamp):
    return "%s/session_%s.ma" % (folder.replace("\\", "/").rstrip("/"), stamp)
```

- [ ] **Step 4: The payload row and its test**

In `SkeldarAnim/install.py`, inside `_PAYLOAD`, after the line `"maya_walk",                # the Walk Builder card: ...`, add:

```python
    "maya_scenetabs",           # scene tabs: several scenes in one Maya (2026-10-15)
```

In `tests/test_install.py`, beside the existing `self.assertIn("maya_poselib", install.payload())`, add:

```python
        self.assertIn("maya_scenetabs", install.payload())
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenetabs_records tests.test_install -v`
Expected: all OK.

- [ ] **Step 6: The spec's planning addendum**

Append to `docs/superpowers/specs/2026-10-15-scene-tabs-design.md`:

```markdown
## Addendum: measured while planning (2026-10-15)

- **Tab namespaces are `tab_<stem>`**, not the bare stem: a tab opened from `assets/Manny_Rig.ma` would
  otherwise BE the namespace `Manny_Rig`, the child namespace a saved tab's rig moves into for its export.
- **The session owns the animation-layer root `skeldarTabsLayerRoot`.** Maya remembers its root layer
  internally: with the root deleted (the tab holding it closed) the other tabs' layers lost theirs and the next
  new layer crashed mayapy. Measured working: the root made once (a temporary layer, deleted), each import's
  root hung under it as `<tab>:AnimLayerRoot`, a scene that already had layers handing its root over (renamed)
  with its layers moved under a tab root, closing any tab leaving the others' layers alone, and back to one
  scene the tab root's layers under the root renamed `BaseAnimation` (or no root when no layer is left). A
  layer made while a tab is active is parented to the session root by Maya and re-parented to the tab's.
- **Import with `executeScriptNodes=False`**: an import otherwise RUNS a file's open-type script nodes.
- **Furniture** an import brings into a tab's namespace and a save never moves: Maya's managers and the
  file's own `defaultRenderLayer`, `renderLayerManager`, `defaultLayer` copies (they clashed with the root's).
- **An `.mb` file's fps** is the header's TUNI chunk (an 8-byte big-endian size at +8, the name at +16).
- **The Open check's callback is `(MFileObject, clientData) -> bool`**; the Save check has no file variant
  (`kInvalidParameter`), so it reads the target from `file -q -sceneName`, which Save As has already set.
- **`maya.utils.executeDeferred` never runs in mayapy standalone**: the hooks defer through a seam the verify
  replaces with a queue it runs itself.
- **Ctrl+Tab / Ctrl+Shift+Tab are not bound by default** in stage 1 (what Maya holds there needs a GUI to
  check); the rows `tabs.next` / `tabs.previous` are in the plugin's map for the animator to bind.
- **Maya's own Save, refused by the callback, prints «File operation cancelled by user supplied callback»**;
  the tab's save then says «Saved ...» in the viewport.
- **Found by running the plan's own code** (its verify, 127 gates, in a scratch copy):
  - re-parenting a layer (`animLayer -e -parent`) REBUILDS its blend nodes in the ROOT namespace whatever is
    current, and a save rebuilds some under names of Maya's own: a tab's blend nodes are brought back into its
    namespace (`layers.home_blends`) after every re-parent, before and after a save and before a close; the
    tab root is cut from and put back on the session's root by its five exact connections, never by re-parenting;
  - renaming a reference node by hand breaks its link to its namespace («Cannot find the associated
    namespace»), and moving a reference's namespace back does not bring its node back: a reference is always
    found by its namespace, and after a save its node may sit in the root as `refRN`;
  - removing a reference by its file path is ambiguous between two tabs of one file (`file{1}`): by its node;
  - an import made INSIDE a tab brings its file's configuration node (Maya skips it only when the ROOT holds
    one); in the tab's file it ran after the tab's and won (1-120 for 0-50): only the tab's own is exported;
  - the managers the first import into an empty scene makes inside the namespace cannot be deleted (trap 158):
    closing a tab deletes what can be deleted and merges the rest into the root, deepest namespace first;
  - a tab root is known by its NAME (`AnimLayerRoot`): right after tab 1's conversion its own layers hang on
    the session root too.
```

- [ ] **Step 7: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs_msg.txt" <<'EOF'
feat(scenetabs): the package and its records, pure

Tab namespaces, a file's fps (.ma header, .mb TUNI chunk) and ranges, the
session JSON, Maya's furniture, Save vs Save As, the bar's items. The spec
gains what was measured while planning.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_scenetabs/__init__.py SkeldarAnim/maya_scenetabs/records.py tests/test_scenetabs_records.py SkeldarAnim/install.py tests/test_install.py docs/superpowers/specs/2026-10-15-scene-tabs-design.md
git commit -F "$TEMP/scenetabs_msg.txt"
```

---

### Task 2: `session` - the node, a tab's nodes, lift / lower, tab 1 and back; the verify harness

**Files:**
- Create: `SkeldarAnim/maya_scenetabs/session.py`
- Create: `docs/superpowers/plans/verify_scene_tabs.py`

**Interfaces:**
- Consumes: `records.*` (Task 1).
- Produces: `TabError(RuntimeError)`; `exists() -> bool`, `state() -> dict`, `write(state)`, `write_quiet(state)`, `delete()`, `is_on() -> bool`, `current_ranges() -> dict`, `apply_ranges(ranges)`, `own_nodes(namespace) -> [uuid]` (`""` = the root namespace), `top_references(namespace) -> [(reference node uuid, namespace leaf)]`, `child_namespaces(namespace, skip=()) -> [leaf]`, class `Moved` (`.namespace`, `.nodes [(uuid, leaf, locked)]`, `.references [(uuid, namespace leaf)]`, `.children [leaf]`, `.held [(uuid, name)]`), `lift(namespace, renames=None) -> Moved`, `lower(moved)`, `move_into(namespace, skip_namespaces=()) -> Moved`, `drop_held(moved)`.
- The verify harness (`gate`, `fresh`, `copy`, `fixtures`, `summary`, `PHASES`) is used by Tasks 3-8.

- [ ] **Step 1: Write the harness and the failing `convert` phase**

`docs/superpowers/plans/verify_scene_tabs.py`:

```python
"""Scene tabs, stage 1: the proof in mayapy standalone (2026-10-15).

Run from the repo root (PowerShell):
  $env:MAYA_APP_DIR = "$env:TEMP\\skeldar_tabs_appdir"
  & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_scene_tabs.py all
Phases: convert layers open_close switch save hooks restore, or "all".
Every gate prints PASS / FAIL; the last line is "N of M gates failed".
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""
import builtins
import os
import shutil
import sys
import tempfile
import traceback

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402

for _plug in ("matrixNodes", "quatNodes"):
    cmds.loadPlugin(_plug, quiet=True)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PLUGIN = os.path.join(REPO, "SkeldarAnim").replace("\\", "/")
sys.path.insert(0, PLUGIN)

from maya_scenetabs import records, session  # noqa: E402

WORK = os.path.join(tempfile.gettempdir(), "skeldar_tabs_verify").replace("\\", "/")
RUN = WORK + "/run"
RESULTS = []
QUEUE = []


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def flush():
    """Run what the hooks deferred (executeDeferred never runs in mayapy)."""
    while QUEUE:
        QUEUE.pop(0)()


def fresh():
    """An empty scene, the hooks off, no namespace left. Maya keeps a namespace
    alive across `file -new` when the managers an import made sit in it (trap
    158): the next phase's tab would then be `tab_rig1` and nest the leftovers."""
    try:
        from maya_scenetabs import hooks
        hooks.remove()
    except Exception:                                           # noqa: BLE001
        pass
    cmds.file(new=True, force=True)
    found = [n for n in cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or []
             if n.split(":")[0] not in records.SYSTEM_NAMESPACES]
    for name in sorted(found, key=lambda n: -n.count(":")):
        if cmds.namespace(exists=":" + name):
            cmds.namespace(removeNamespace=":" + name, mergeNamespaceWithRoot=True)
    cmds.undoInfo(state=True, infinity=True)


def copy(name, as_name=None):
    """A fixture copied into the run folder (tabs edit and save their files)."""
    os.makedirs(RUN, exist_ok=True)
    target = RUN + "/" + (as_name or name)
    shutil.copyfile(WORK + "/" + name, target)
    return target


def _save(path, kind="mayaAscii"):
    cmds.file(rename=path)
    cmds.file(save=True, type=kind, force=True)


def fixtures():
    """rig.ma / rig.mb: a Manny rig, ntsc, 0-50 / 0-60, FKShoulder_R keyed.
    film.ma: film, a cube with an animation layer and a display layer, a
    camera, a nested reference to ref.ma, an open-type script node, 5-40 / 0-45.
    plain.mb: ntscf, a keyed sphere, 0-24. Built once per WORK folder."""
    os.makedirs(WORK, exist_ok=True)
    done = WORK + "/fixtures.done"
    if os.path.exists(done):
        return
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="film")
    box = cmds.polyCube(name="box")[0]
    cmds.setKeyframe(box, attribute="translateX", time=10, value=0)
    cmds.setKeyframe(box, attribute="translateX", time=30, value=10)
    _save(WORK + "/ref.ma")

    cmds.file(new=True, force=True)
    cmds.currentUnit(time="film")
    cmds.file(WORK + "/ref.ma", reference=True, namespace="ref")
    hero = cmds.polyCube(name="hero")[0]
    cmds.setKeyframe(hero, attribute="translateY", time=5, value=0)
    cmds.setKeyframe(hero, attribute="translateY", time=40, value=4)
    cmds.select(hero)
    layer = cmds.animLayer("Layer1", addSelectedObjects=True)
    cmds.setKeyframe(hero + ".rotateY", time=20, value=45, animLayer=layer)
    cmds.createDisplayLayer(hero, name="cubesLayer", noRecurse=True)
    cmds.camera(name="shotCam")
    cmds.scriptNode(name="opener", scriptType=1, sourceType="mel",
                    beforeScript='python("import builtins; builtins.SKELDAR_TABS_RAN = True")')
    cmds.playbackOptions(minTime=5, maxTime=40, animationStartTime=0, animationEndTime=45)
    _save(WORK + "/film.ma")

    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    from maya_scenesetup import catalog, character
    character.add_character(catalog.default_rig())
    control = cmds.ls("*:FKShoulder_R", long=True)[0]
    cmds.setKeyframe(control, attribute="rotateZ", time=0, value=0)
    cmds.setKeyframe(control, attribute="rotateZ", time=20, value=40)
    cmds.playbackOptions(minTime=0, maxTime=50, animationStartTime=0, animationEndTime=60)
    _save(WORK + "/rig.ma")
    _save(WORK + "/rig.mb", "mayaBinary")

    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntscf")
    ball = cmds.polySphere(name="ball")[0]
    cmds.setKeyframe(ball, attribute="translateX", time=0, value=0)
    cmds.setKeyframe(ball, attribute="translateX", time=24, value=12)
    cmds.playbackOptions(minTime=0, maxTime=24, animationStartTime=0, animationEndTime=24)
    _save(WORK + "/plain.mb", "mayaBinary")
    open(done, "w").close()


def value_at(plug, frame):
    """A plug's value after a real time change (getAttr(time=) skips layer blends, trap 232)."""
    cmds.currentTime(frame)
    return round(cmds.getAttr(plug), 4)


def summary(path, probes=()):
    """What a scene file holds, read by opening it alone (the hooks off)."""
    fresh()
    cmds.file(path, open=True, force=True)
    defaults = set(cmds.ls(defaultNodes=True) or [])
    #  Maya names layer curves and blend nodes by rules of its own (a tab's
    #  file got `Layer4_inputB` where the same edit made directly got
    #  `hero_translateX_Layer2_inputB`, measured): they are compared by their
    #  keys and by the value probes, not by name.
    unnamed = set(cmds.ls(type=("animCurve", "animBlendNodeBase")) or [])
    startup = [c for c in cmds.ls(type="camera") or [] if cmds.camera(c, q=True, startupCamera=True)]
    unnamed |= set(startup) | set(cmds.listRelatives(startup, parent=True) or [])     # Maya makes them on open
    names = sorted(n for n in cmds.ls()
                   if n not in defaults and n not in unnamed and not cmds.referenceQuery(n, isNodeReferenced=True)
                   and cmds.nodeType(n) != "script"
                   and not records.is_furniture(n.split("|")[-1].split(":")[-1], cmds.nodeType(n)))
    keys = []
    for curve in cmds.ls(type="animCurve") or []:
        if not cmds.referenceQuery(curve, isNodeReferenced=True):
            pairs = cmds.keyframe(curve, q=True, timeChange=True, valueChange=True) or []
            keys.append([round(v, 4) for v in pairs])
    keys.sort()
    layer_tree = {l: cmds.animLayer(l, q=True, parent=True) for l in cmds.ls(type="animLayer") or []}
    refs = sorted((cmds.referenceQuery(r, namespace=True),
                   os.path.basename(cmds.referenceQuery(r, filename=True, withoutCopyNumber=True)))
                  for r in cmds.ls(type="reference") or []
                  if not r.endswith("sharedReferenceNode") and not cmds.referenceQuery(r, isNodeReferenced=True))
    displays = {d: sorted(cmds.editDisplayLayerMembers(d, q=True, fullNames=False) or [])
                for d in cmds.ls(type="displayLayer") or [] if d != "defaultLayer"}
    solved = all(cmds.listConnections(h + ".ikSolver") for h in cmds.ls(type="ikHandle") or [])
    values = {"%s@%s" % (plug, frame): value_at(plug, frame) for plug, frame in probes}
    return {"names": names, "keys": keys, "layers": layer_tree, "refs": refs, "displays": displays,
            "ik_solved": solved, "values": values, "unit": cmds.currentUnit(q=True, time=True),
            "ranges": [cmds.playbackOptions(q=True, minTime=True), cmds.playbackOptions(q=True, maxTime=True),
                       cmds.playbackOptions(q=True, animationStartTime=True),
                       cmds.playbackOptions(q=True, animationEndTime=True)]}


def scene_is(path):
    return records.same_file(cmds.file(q=True, sceneName=True), path)


def current_ns():
    return cmds.namespaceInfo(currentNamespace=True).lstrip(":")


# ------------------------------------------------------------------ phases

def phase_convert():
    """The open scene becomes tab 1 and back, every name exact."""
    from maya_scenetabs import opening
    import maya_rigs
    path = copy("rig.ma")
    fresh()
    cmds.file(path, open=True, force=True)
    before = sorted(cmds.ls())
    state = opening.start()
    gate("convert: tab 1 is tab_rig", state["active"] == "tab_rig", state["active"])
    gate("convert: the rig is in the tab", [r.namespace for r in maya_rigs.rigs()] == ["tab_rig:Manny_Rig"],
         [r.namespace for r in maya_rigs.rigs()])
    gate("convert: nothing of the scene is left in the root namespace", session.own_nodes("") == [],
         cmds.ls(session.own_nodes("")))
    gate("convert: the scene is the session", scene_is(state["session"]), cmds.file(q=True, sceneName=True))
    gate("convert: the tab's namespace is current", current_ns() == "tab_rig", current_ns())
    gate("convert: the key plays", value_at("tab_rig:Manny_Rig:FKShoulder_R.rotateZ", 20) == 40.0)
    message = opening.finish()
    gate("finish: back to one scene, every name exact", sorted(cmds.ls()) == before,
         sorted(set(cmds.ls()) ^ set(before))[:10])
    gate("finish: the scene is rig.ma again", scene_is(path), message)
    gate("finish: no session node", not session.exists())


PHASES = {"convert": phase_convert}


def main(names):
    fixtures()
    for name in names:
        try:
            PHASES[name]()
        except Exception:                                       # noqa: BLE001
            gate("phase %s ran to the end" % name, False, traceback.format_exc())
    failed = RESULTS.count(False)
    print("%d of %d gates failed" % (failed, len(RESULTS)))
    return failed


if __name__ == "__main__":
    wanted = sys.argv[1:] or ["all"]
    if wanted == ["all"]:
        wanted = list(PHASES)
    code = main(wanted)
    maya.standalone.uninitialize()
    sys.exit(1 if code else 0)
```

(Task 4 adds `opening.start` / `opening.finish`; until then `convert` fails on the import of `opening`. Task 2 proves `session` through the phase added in Step 4.)

- [ ] **Step 2: Run the script to see it fail**

Run: `$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_scene_tabs.py convert`
Expected: a traceback ending in `ImportError: cannot import name 'session' from 'maya_scenetabs'` (the script's own top-level import).

- [ ] **Step 3: Write `session`**

`SkeldarAnim/maya_scenetabs/session.py`:

```python
"""Scene tabs: the session in the scene - its node, which nodes are a tab's,
and moving a tab between its namespace and the root namespace.

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
A save lifts the tab's nodes into the root namespace for the length of the
export and lowers them back by UUID: a whole-namespace move refuses on the
furniture an import brings, and `exportSelected -relativeNamespace` refuses
with `-preserveReferences` (measured 2026-10-15). The same pair converts the
open scene into tab 1 (`move_into`) and back.
"""

import maya.cmds as cmds

from . import records

HELD_PREFIX = "skeldarHeld_"


class TabError(RuntimeError):
    """A tab operation refused; the message says why."""


# ------------------------------------------------------------------ the node

def exists():
    return cmds.objExists(records.SESSION_NODE)


def state():
    if not exists():
        return records.empty_state()
    return records.loads(cmds.getAttr(records.SESSION_NODE + "." + records.SESSION_ATTR) or "")


def write(new_state):
    node = records.SESSION_NODE
    if not cmds.objExists(node):
        cmds.createNode("network", name=":" + node, skipSelect=True)
        cmds.addAttr(node, longName=records.SESSION_ATTR, dataType="string")
    cmds.setAttr(node + "." + records.SESSION_ATTR, records.dumps(new_state), type="string")


def write_quiet(new_state):
    """`write` outside the undo queue (never inside an open chunk, trap 145)."""
    recording = cmds.undoInfo(q=True, stateWithoutFlush=True)
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        write(new_state)
    finally:
        cmds.undoInfo(stateWithoutFlush=recording)


def delete():
    if exists():
        cmds.lockNode(records.SESSION_NODE, lock=False)
        cmds.delete(records.SESSION_NODE)


def is_on():
    """Tab mode: two or more tabs."""
    return exists() and len(state()["tabs"]) >= 2


def current_ranges():
    return {key: cmds.playbackOptions(q=True, **{key: True}) for key in records.RANGE_KEYS}


def apply_ranges(ranges):
    if ranges:
        cmds.playbackOptions(**{key: ranges[key] for key in records.RANGE_KEYS if key in ranges})


# ------------------------------------------------------------------ which nodes

def _name(uid):
    found = cmds.ls(uid, long=True) or []
    return found[0] if found else ""


def _leaf(path):
    return path.split("|")[-1].split(":")[-1]


def _startup_nodes():
    cameras = [c for c in cmds.ls(type="camera") or [] if cmds.camera(c, q=True, startupCamera=True)]
    return cameras + (cmds.listRelatives(cameras, parent=True) or [])


def _skipped():
    names = (cmds.ls(defaultNodes=True) or []) + (cmds.ls(readOnly=True) or []) + _startup_nodes()
    names += [n for n in (records.SESSION_NODE, records.LAYER_ROOT) if cmds.objExists(":" + n)]
    return set(cmds.ls(names, uuid=True) or [])


def own_nodes(namespace):
    """The UUIDs of a namespace's OWN nodes at its own level ("" = the root
    namespace): not Maya's default, read-only or startup nodes, not referenced,
    not a reference node, not furniture, not the session's own."""
    skip = _skipped()
    if namespace:
        paths = cmds.namespaceInfo(":" + namespace, listOnlyDependencyNodes=True, dagPath=True) or []
    else:
        paths = [p for p in cmds.ls(long=True) or [] if ":" not in p.split("|")[-1]]
    out = []
    for path in paths:
        uid = (cmds.ls(path, uuid=True) or [None])[0]
        if uid is None or uid in skip or cmds.referenceQuery(path, isNodeReferenced=True):
            continue
        kind = cmds.nodeType(path)
        if kind == "reference" or records.is_furniture(_leaf(path), kind):
            continue
        out.append(uid)
    return out


def top_references(namespace):
    """(reference node UUID, namespace leaf) of the references whose namespace
    sits directly in `namespace` ("" = the root)."""
    parent = (":" + namespace) if namespace else ""
    out = []
    for node in cmds.ls(type="reference") or []:
        if node.split(":")[-1] == "sharedReferenceNode" or cmds.referenceQuery(node, isNodeReferenced=True):
            continue
        try:
            ref_ns = cmds.referenceQuery(node, namespace=True)
        except RuntimeError:
            continue
        above, _, leaf = ref_ns.rpartition(":")
        if above == parent:
            out.append((cmds.ls(node, uuid=True)[0], leaf))
    return out


def child_namespaces(namespace, skip=()):
    """The leaves of the namespaces directly in `namespace` that are not a
    reference's and not in `skip` (Maya's own, the tabs)."""
    references = set(leaf for _, leaf in top_references(namespace))
    found = cmds.namespaceInfo(":" + namespace if namespace else ":", listOnlyNamespaces=True) or []
    leaves = [n.split(":")[-1] for n in found]
    return [n for n in leaves if n not in references and n not in skip
            and n not in records.SYSTEM_NAMESPACES]


# ------------------------------------------------------------------ moving

class Moved(object):
    """What `lift` took into the root namespace (or `move_into` takes out of
    it), for `lower` to put back."""

    def __init__(self, namespace):
        self.namespace = namespace
        self.nodes = []          # (uuid, leaf in the tab, locked)
        self.references = []     # (reference node uuid, namespace leaf)
        self.children = []       # child namespace leaves
        self.held = []           # (uuid, root name) of root nodes held aside


def _ref_file(uid):
    """The reference's file WITH its copy number ({1}, {2}): two tabs of one
    file reference the same file twice. A reference node is never renamed by
    hand: that breaks its link to its namespace («Cannot find the associated
    namespace», measured), so after a save its node may sit in the root as
    `refRN` - which is why references are always found by their NAMESPACE."""
    return cmds.referenceQuery(_name(uid), filename=True)


def _hold(moved, wanted):
    """A root node of Maya's own config name blocking `wanted` goes aside."""
    blocker = ":" + wanted
    if wanted != records.CONFIG_NODE or not cmds.objExists(blocker):
        return
    uid = cmds.ls(blocker, uuid=True)[0]
    cmds.rename(blocker, ":" + HELD_PREFIX + wanted, ignoreShape=True)
    moved.held.append((uid, wanted))


def lift(namespace, renames=None):
    """The tab's content into the root namespace, its own nodes renamed by
    UUID (`renames` maps a UUID to the leaf it takes outside: the tab's layer
    root -> BaseAnimation), its references and child namespaces moved. A name
    the root already uses refuses by name, after everything taken is back."""
    renames = renames or {}
    moved = Moved(namespace)
    try:
        for uid in own_nodes(namespace):
            path = _name(uid)
            locked = bool(cmds.lockNode(path, q=True, lock=True)[0])
            if locked:
                cmds.lockNode(path, lock=False)
            leaf = _leaf(path)
            wanted = renames.get(uid, leaf)
            _hold(moved, wanted)
            got = _leaf(cmds.rename(path, ":" + wanted, ignoreShape=True))
            moved.nodes.append((uid, leaf, locked))
            if got != wanted:
                raise TabError("cannot save %s: the scene already holds a node named %s"
                               % (namespace, wanted))
        for uid, leaf in top_references(namespace):
            if cmds.namespace(exists=":" + leaf):
                raise TabError("cannot save %s: the scene already holds a namespace %s" % (namespace, leaf))
            cmds.file(_ref_file(uid), edit=True, namespace=leaf)
            moved.references.append((uid, leaf))
        for child in child_namespaces(namespace):
            if cmds.namespace(exists=":" + child):
                raise TabError("cannot save %s: the scene already holds a namespace %s" % (namespace, child))
            cmds.namespace(rename=(":%s:%s" % (namespace, child), child), parent=":")
            moved.children.append(child)
    except Exception:
        lower(moved)
        raise
    return moved


def lower(moved):
    """`lift` undone exactly: child namespaces, references and nodes back in
    the tab's namespace by UUID, locks back, held root nodes back."""
    namespace = moved.namespace
    if not cmds.namespace(exists=":" + namespace):
        cmds.namespace(add=namespace, parent=":")
    for child in reversed(moved.children):
        if cmds.namespace(exists=":" + child):
            cmds.namespace(rename=(":" + child, child), parent=":" + namespace)
    for uid, leaf in reversed(moved.references):
        cmds.file(_ref_file(uid), edit=True, namespace="%s:%s" % (namespace, leaf))
    for uid, leaf, locked in reversed(moved.nodes):
        path = _name(uid)
        if path:
            cmds.rename(path, ":%s:%s" % (namespace, leaf), ignoreShape=True)
            if locked:
                cmds.lockNode(_name(uid), lock=True)
    for uid, name in reversed(moved.held):
        path = _name(uid)
        if path:
            cmds.rename(path, ":" + name, ignoreShape=True)
    moved.nodes, moved.references, moved.children, moved.held = [], [], [], []


def move_into(namespace, skip_namespaces=()):
    """The root namespace's own content into `namespace` (the open scene
    becoming tab 1): a `Moved` built from the root and lowered."""
    moved = Moved(namespace)
    for uid in own_nodes(""):
        path = _name(uid)
        moved.nodes.append((uid, _leaf(path), bool(cmds.lockNode(path, q=True, lock=True)[0])))
    moved.references = top_references("")
    moved.children = child_namespaces("", skip=tuple(skip_namespaces) + (namespace,))
    for uid, _, locked in moved.nodes:
        if locked:
            cmds.lockNode(_name(uid), lock=False)
    lower(moved)
    return moved


def drop_held(moved):
    """Held root nodes deleted (a lift that is not lowered: back to one scene)."""
    for uid, _ in moved.held:
        path = _name(uid)
        if path:
            cmds.lockNode(path, lock=False)
            cmds.delete(path)
    moved.held = []
```

- [ ] **Step 4: A temporary driver proves `session` before `opening` exists**

Add to `verify_scene_tabs.py`, above `PHASES`:

```python
def phase_session():
    """session alone: move_into and lift/lower round trips on the rig scene."""
    path = copy("rig.ma")
    fresh()
    cmds.file(path, open=True, force=True)
    before = sorted(cmds.ls())
    moved = session.move_into("tab_rig")
    gate("session: move_into empties the root namespace", session.own_nodes("") == [])
    gate("session: the rig's namespace moved under the tab", cmds.namespace(exists=":tab_rig:Manny_Rig"))
    lifted = session.lift("tab_rig")
    gate("session: lift brings it back to the root", sorted(cmds.ls()) == before)
    session.lower(lifted)
    gate("session: lower puts it in the tab again", session.own_nodes("") == [] and
         cmds.namespace(exists=":tab_rig:Manny_Rig"))
    cmds.createNode("transform", name=":Manny_Rig_Character")
    try:
        session.lift("tab_rig")
        refused = ""
    except session.TabError as exc:
        refused = str(exc)
    gate("session: a clash refuses by name", "Manny_Rig_Character" in refused, refused)
    gate("session: a refused lift leaves the tab whole",
         cmds.objExists("tab_rig:Manny_Rig_Character") and cmds.namespace(exists=":tab_rig:Manny_Rig"))
```

and register it: `PHASES = {"session": phase_session, "convert": phase_convert}`.

- [ ] **Step 5: Run the session phase**

Run: `$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_scene_tabs.py session`
Expected: 6 PASS, `0 of 6 gates failed`. (The first run also builds the fixtures: about 10 s.)

- [ ] **Step 6: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs_msg.txt" <<'EOF'
feat(scenetabs): the session node, a tab's nodes, lift / lower by UUID

Proof: verify_scene_tabs.py session (move_into, lift, lower, a clash
refused with the tab left whole).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_scenetabs/session.py docs/superpowers/plans/verify_scene_tabs.py
git commit -F "$TEMP/scenetabs_msg.txt"
```

---

### Task 3: `layers` - the session-owned root

**Files:**
- Create: `SkeldarAnim/maya_scenetabs/layers.py`
- Modify: `docs/superpowers/plans/verify_scene_tabs.py` (phase `layers_alone`)

**Interfaces:**
- Consumes: `records.LAYER_ROOT`, `TAB_LAYER_ROOT`, `FILE_LAYER_ROOT` (Task 1).
- Produces: `root() -> str`, `ensure_root() -> str`, `take_root() -> [uuid]` (the old root's children), `home_blends(namespace) -> int`, `give_children(namespace, children) -> str`, `is_tab_root_name(layer) -> bool`, `tab_root(namespace, make=False) -> str`, `detach(layer) -> [(source plug, destination plug)]`, `attach(links)`, `adopt(layer, namespace) -> bool`, `flatten(namespace)`.

- [ ] **Step 1: Write the failing phase**

Add to `verify_scene_tabs.py` above `PHASES`, and register `"layers_alone": phase_layers_alone`:

```python
def layer_parent(layer):
    return cmds.animLayer(layer, q=True, parent=True) or ""


def phase_layers_alone():
    """layers without tabs: the film scene's root handed to the session and back."""
    from maya_scenetabs import layers
    path = copy("film.ma")
    fresh()
    cmds.file(path, open=True, force=True)
    children = layers.take_root()
    gate("layers: the session takes the root", layers.root() == records.LAYER_ROOT, layers.root())
    session.move_into("tab_film")
    made = layers.give_children("tab_film", children)
    gate("layers: the tab's root under the session's", made == "tab_film:AnimLayerRoot"
         and layer_parent(made) == records.LAYER_ROOT, made)
    gate("layers: the tab's layer under the tab's root", layer_parent("tab_film:Layer1") == made)
    gate("layers: the layer still plays", value_at("tab_film:hero.rotateY", 20) == 45.0)
    blends = sorted(cmds.ls(type="animBlendNodeBase") or [])
    links = layers.detach(made)
    gate("layers: detach cuts the tab root free", len(links) == 5 and layer_parent(made) == "", links)
    layers.attach(links)
    gate("layers: attach puts it back, no blend node rebuilt",
         layer_parent(made) == records.LAYER_ROOT and sorted(cmds.ls(type="animBlendNodeBase") or []) == blends)
    cmds.select("tab_film:hero")
    cmds.namespace(setNamespace=":tab_film")
    fresh_layer = cmds.animLayer("Fresh", addSelectedObjects=True)
    cmds.namespace(setNamespace=":")
    gate("layers: Maya parents a new layer to the session root", layer_parent(fresh_layer) == records.LAYER_ROOT)
    gate("layers: adopt moves it under the tab's root", layers.adopt(fresh_layer, "tab_film")
         and layer_parent(fresh_layer) == made)
    layers.flatten("tab_film")
    gate("layers: flatten - BaseAnimation is the root again", layers.root() == "BaseAnimation")
    gate("layers: flatten - the layers under it, the tab root gone",
         layer_parent("tab_film:Layer1") == "BaseAnimation" and not cmds.objExists(made))
    gate("layers: flatten - the layer still plays", value_at("tab_film:hero.rotateY", 20) == 45.0)
```

- [ ] **Step 2: Run it to see it fail**

Run: `... verify_scene_tabs.py layers_alone`
Expected: `FAIL  phase layers_alone ran to the end` (no module `layers`).

- [ ] **Step 3: Write `layers`**

`SkeldarAnim/maya_scenetabs/layers.py`:

```python
"""Scene tabs: animation layers with tabs.

Maya keeps ONE root layer and remembers it internally: delete it and the other
layers lose theirs, and the next new layer crashed mayapy (measured
2026-10-15). So while tabs are on the session owns the root
(`skeldarTabsLayerRoot`), every tab's layers hang under a tab root of their own
(`<tab>:AnimLayerRoot` - Maya's own name for an imported BaseAnimation), and a
tab's file gets its tree back with that root named BaseAnimation.
"""

import maya.cmds as cmds

from . import records


def root():
    return cmds.animLayer(q=True, root=True) or ""


def _children(layer):
    return [l for l in cmds.ls(type="animLayer") or []
            if (cmds.animLayer(l, q=True, parent=True) or "") == layer]


def ensure_root():
    """The session's root, made once: a temporary layer makes Maya's root,
    the temporary goes, the root is renamed."""
    found = root()
    if found:
        return found
    temporary = cmds.animLayer("skeldarTabsTempLayer")
    made = root()
    cmds.delete(temporary)
    return cmds.rename(made, ":" + records.LAYER_ROOT, ignoreShape=True)


def _in_namespace(namespace, make):
    """`make()` run with `namespace` current ("" = the root), the current one
    put back. A layer's name is relative to the current namespace, and so are
    the blend nodes Maya rebuilds when a layer is re-parented (measured: a
    re-parent run in the root put a tab's blend nodes in the root)."""
    current = cmds.namespaceInfo(currentNamespace=True) or ":"
    cmds.namespace(setNamespace=(":" + namespace) if namespace else ":")
    try:
        return make()
    finally:
        cmds.namespace(setNamespace=current if current.startswith(":") else ":" + current)


def _in_root_namespace(make):
    return _in_namespace("", make)


def take_root():
    """The open scene's root handed to the session (renamed). Returns the
    UUIDs of its children: they become tab 1's (`give_children`)."""
    found = root()
    if not found:
        return []
    children = cmds.ls(_children(found), uuid=True) or []
    if found.split(":")[-1] != records.LAYER_ROOT:
        cmds.rename(found, ":" + records.LAYER_ROOT, ignoreShape=True)
    return children


def is_tab_root_name(layer):
    """`AnimLayerRoot` (Maya's own name for an imported BaseAnimation, and
    ours), with Maya's uniqueness number if any."""
    leaf = layer.split(":")[-1]
    rest = leaf[len(records.TAB_LAYER_ROOT):]
    return leaf.startswith(records.TAB_LAYER_ROOT) and (rest == "" or rest.isdigit())


def _make_tab_root(namespace, session_root):
    return _in_root_namespace(lambda: cmds.animLayer("%s:%s" % (namespace, records.TAB_LAYER_ROOT),
                                                     parent=session_root))


def tab_root(namespace, make=False):
    """The tab's layer root: the layer of its namespace named AnimLayerRoot
    hanging on the session's root (by NAME: right after tab 1's conversion
    its own layers hang on the session root too, measured); made when asked
    and missing."""
    session_root = root()
    if not session_root:
        return ""
    for layer in cmds.ls(":%s:*" % namespace, type="animLayer") or []:
        if is_tab_root_name(layer) and (cmds.animLayer(layer, q=True, parent=True) or "") == session_root:
            return layer
    return _make_tab_root(namespace, session_root) if make else ""


def home_blends(namespace):
    """The blend nodes of the tab's layers renamed into the tab's namespace.
    Re-parenting a layer (`animLayer -e -parent`) rebuilds its blend nodes in
    the ROOT namespace whatever namespace is current (measured): left there
    they are not the tab's - not lifted, not deleted with it - and they clash
    by name with another tab's when that tab is saved."""
    prefix = namespace + ":"
    moved = 0
    for layer in cmds.ls(":%s:*" % namespace, type="animLayer", recursive=True) or []:
        for node in cmds.animLayer(layer, q=True, blendNodes=True) or []:
            if node.startswith(prefix) or not cmds.objExists(node):
                continue
            locked = bool(cmds.lockNode(node, q=True, lock=True)[0])
            if locked:
                cmds.lockNode(node, lock=False)
            renamed = cmds.rename(node, ":%s:%s" % (namespace, node.split(":")[-1]))
            if locked:
                cmds.lockNode(renamed, lock=True)
            moved += 1
    return moved


def give_children(namespace, children):
    """Tab 1's layers (by UUID) under a tab root made for them; their rebuilt
    blend nodes brought home."""
    found = cmds.ls(children or []) or []
    if not found:
        return ""
    made = tab_root(namespace, make=True)
    for layer in found:
        cmds.animLayer(layer, e=True, parent=made)
    home_blends(namespace)
    return made


def detach(layer):
    """Every connection between `layer` and its parent cut (five, measured).
    Returns them as (source plug, destination plug), for `attach`."""
    parent = cmds.animLayer(layer, q=True, parent=True) or ""
    if not parent:
        return []
    cut = []
    pairs = cmds.listConnections(layer, connections=True, plugs=True) or []
    for own, other in zip(pairs[0::2], pairs[1::2]):
        if other.split(".")[0] != parent:
            continue
        if cmds.isConnected(own, other):
            cut.append((own, other))
        elif cmds.isConnected(other, own):
            cut.append((other, own))
    for source, destination in cut:
        cmds.disconnectAttr(source, destination)
    return cut


def attach(links):
    """`detach` undone: exactly those connections back. Never `animLayer -e
    -parent`, which rebuilds the layer's blend nodes in the current namespace."""
    for source, destination in links or []:
        if not cmds.isConnected(source, destination):
            cmds.connectAttr(source, destination)


def adopt(layer, namespace):
    """A layer Maya parented to the session root while `namespace` was the
    active tab goes under that tab's root. True when it moved."""
    if not namespace or not cmds.objExists(layer):
        return False
    session_root = root()
    if not session_root or (cmds.animLayer(layer, q=True, parent=True) or "") != session_root:
        return False
    if is_tab_root_name(layer) or layer.split(":")[-1] == records.LAYER_ROOT:
        return False
    made = tab_root(namespace, make=True)
    if not made or made == layer:
        return False
    cmds.animLayer(layer, e=True, parent=made)
    home_blends(namespace)
    return True


def flatten(namespace):
    """Back to one scene: the tab root's layers under the session root, the
    tab root gone, the root named BaseAnimation again - or no root at all when
    no layer is left (a fresh scene's state, safe)."""
    session_root = root()
    if not session_root:
        return
    made = tab_root(namespace)
    if made:
        for layer in _children(made):
            cmds.animLayer(layer, e=True, parent=session_root)
        cmds.delete(made)
    if [l for l in cmds.ls(type="animLayer") or [] if l != session_root]:
        cmds.rename(session_root, ":" + records.FILE_LAYER_ROOT, ignoreShape=True)
    else:
        cmds.delete(session_root)
```

- [ ] **Step 4: Run the phase**

Run: `... verify_scene_tabs.py layers_alone session`
Expected: every line PASS, `0 of 17 gates failed`.

- [ ] **Step 5: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs_msg.txt" <<'EOF'
feat(scenetabs): the session owns the animation-layer root

A tab's layers hang under its own root; detach / attach for a save, a new
layer adopted, flatten back to one scene. Proof: verify layers_alone.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_scenetabs/layers.py docs/superpowers/plans/verify_scene_tabs.py
git commit -F "$TEMP/scenetabs_msg.txt"
```

---

### Task 4: `switching` and `opening` - tab 1, open, new, close, back to one scene

`opening` needs `switching.leave` / `enter`; they are written together and proven together (phases `convert`, `layers`, `open_close`).

**Files:**
- Create: `SkeldarAnim/maya_scenetabs/switching.py`
- Create: `SkeldarAnim/maya_scenetabs/opening.py`
- Modify: `docs/superpowers/plans/verify_scene_tabs.py` (phases `layers`, `open_close`; `convert` runs now)

**Interfaces:**
- Consumes: `records`, `session`, `layers` (Tasks 1-3).
- Produces in `switching`: `VIEW_FLAGS`, `tops(namespace) -> [path]`, `hide(namespace)`, `show(namespace)`, `capture_views() -> list`, `apply_views(views)`, `save_layout(tab)`, `load_layout(tab)`, `forget_layout(tab)`, `leave(state) -> state`, `enter(state, namespace, fresh=False) -> state`, `switch(namespace) -> state`, `cycle(step) -> str`.
- Produces in `opening`: `ASK` (seam: `callable(message, buttons) -> answer`), `folder() -> str`, `start() -> state`, `open_tab(path, index=None) -> str`, `open_any(path) -> str`, `new_tab() -> str`, `close_tab(namespace=None, ask=True) -> str`, `close_others(namespace=None) -> str`, `reload_tab(namespace=None, ask=True) -> str`, `finish() -> str`, `restore() -> str`, `tabs_off() -> str`, `unsaved() -> [tab]`, `quit_ok() -> bool`, `explore(namespace=None) -> str`.
- `opening.close_tab` imports `saving` lazily (Task 5); `switching.load_layout` imports `bar` lazily (Task 8) - both only in a GUI.

- [ ] **Step 1: Write the failing phases**

Add above `PHASES` and register `"layers": phase_layers, "open_close": phase_open_close`:

```python
def tops_visible(namespace):
    from maya_scenetabs import switching
    return [cmds.getAttr(t + ".lodVisibility") for t in switching.tops(namespace)]


def phase_layers():
    """Three tabs with layers: the session owns the root; closing tab 1 leaves the others; back to one scene."""
    from maya_scenetabs import layers, opening, switching
    film, film_b, film_c = copy("film.ma"), copy("film.ma", "film_b.ma"), copy("film.ma", "film_c.ma")
    fresh()
    cmds.file(film, open=True, force=True)
    opening.open_tab(film_b)
    opening.open_tab(film_c)
    gate("layers: the session owns the root", layers.root() == records.LAYER_ROOT, layers.root())
    roots = [layers.tab_root(ns) for ns in ("tab_film", "tab_film_b", "tab_film_c")]
    gate("layers: each tab has its own root under the session's",
         all(r and layer_parent(r) == records.LAYER_ROOT for r in roots), roots)
    gate("layers: each tab's layer under its own root",
         all(layer_parent(ns + ":Layer1") == r for ns, r in zip(("tab_film", "tab_film_b", "tab_film_c"), roots)))
    gate("layers: every tab plays its layer",
         [value_at(ns + ":hero.rotateY", 20) for ns in ("tab_film", "tab_film_b", "tab_film_c")] == [45.0] * 3)
    opening.close_tab("tab_film", ask=False)
    gate("layers: closing tab 1 keeps the root", layers.root() == records.LAYER_ROOT)
    gate("layers: closing tab 1 keeps the others' layers",
         layer_parent("tab_film_b:Layer1") == layers.tab_root("tab_film_b")
         and value_at("tab_film_b:hero.rotateY", 20) == 45.0)
    switching.switch("tab_film_b")
    cmds.select("tab_film_b:hero")
    made = cmds.animLayer("Fresh", addSelectedObjects=True)
    gate("layers: a new layer after closing tab 1, no crash", cmds.objExists(made), made)
    layers.adopt(made, "tab_film_b")
    gate("layers: adopted under the active tab's root", layer_parent(made) == layers.tab_root("tab_film_b"))
    opening.close_tab("tab_film_c", ask=False)
    gate("layers: back to one scene - BaseAnimation is the root", layers.root() == "BaseAnimation", layers.root())
    gate("layers: back to one scene - both layers under it",
         layer_parent("Layer1") == "BaseAnimation" and layer_parent("Fresh") == "BaseAnimation")
    gate("layers: back to one scene - the layer plays", value_at("hero.rotateY", 20) == 45.0)


def phase_open_close():
    """Three tabs from three kinds of file; a reload; closing; back to one scene."""
    from maya_scenetabs import opening, switching
    import maya_rigs
    rig, film, plain = copy("rig.ma"), copy("film.ma"), copy("plain.mb")
    fresh()
    cmds.file(rig, open=True, force=True)
    builtins.SKELDAR_TABS_RAN = False
    opening.open_tab(film)
    opening.open_tab(plain)
    state = session.state()
    gate("open: three tabs in order", [t["ns"] for t in state["tabs"]] == ["tab_rig", "tab_film", "tab_plain"],
         [t["ns"] for t in state["tabs"]])
    gate("open: units read from the files", [t["unit"] for t in state["tabs"]] == ["ntsc", "film", "ntscf"],
         [t["unit"] for t in state["tabs"]])
    gate("open: the film's ranges read from its file", records.tab(state, "tab_film")["ranges"] ==
         {"minTime": 5.0, "maxTime": 40.0, "animationStartTime": 0.0, "animationEndTime": 45.0},
         records.tab(state, "tab_film")["ranges"])
    gate("open: the nested reference stays a reference",
         cmds.referenceQuery("tab_film:refRN", namespace=True) == ":tab_film:ref")
    gate("open: the file's script node did not run", not builtins.SKELDAR_TABS_RAN)
    gate("open: only the active tab shows",
         tops_visible("tab_plain") and all(tops_visible("tab_plain")) and not any(tops_visible("tab_rig"))
         and not any(tops_visible("tab_film")))
    gate("open: hidden tabs are out of the outliner",
         all(cmds.getAttr(t + ".hiddenInOutliner") for t in switching.tops("tab_rig")))
    gate("open: the active tab's unit is the scene's", cmds.currentUnit(q=True, time=True) == "ntscf")
    gate("open: keys on whole frames in their own unit",
         cmds.keyframe("tab_plain:ball.translateX", q=True, timeChange=True) == [0.0, 24.0])
    gate("open: the rig is still found", [r.namespace for r in maya_rigs.rigs()] == ["tab_rig:Manny_Rig"])
    switching.switch("tab_film")
    cmds.setAttr("tab_film:hero.translateZ", 5)
    opening.ASK = lambda message, buttons: "Reload"
    message = opening.reload_tab()
    opening.ASK = None
    gate("reload: the tab's changes dropped, read from disk", cmds.getAttr("tab_film:hero.translateZ") == 0.0
         and session.state()["active"] == "tab_film", message)
    gate("reload: still in its own unit, its layer playing", cmds.currentUnit(q=True, time=True) == "film"
         and value_at("tab_film:hero.rotateY", 20) == 45.0)
    switching.switch("tab_plain")
    opening.close_tab("tab_plain")
    gate("close: the tab's namespace is gone", not cmds.namespace(exists=":tab_plain"))
    gate("close: the right-hand neighbour - none - so the left one is active",
         session.state()["active"] == "tab_film")
    cmds.setAttr("tab_film:hero.translateX", 3)
    opening.ASK = lambda message, buttons: "Cancel"
    message = opening.close_tab("tab_film")
    gate("close: Cancel keeps a modified tab", cmds.namespace(exists=":tab_film") and "cancelled" in message, message)
    opening.ASK = lambda message, buttons: "Don't Save"
    message = opening.close_tab("tab_film")
    opening.ASK = None
    gate("close: down to one tab is one ordinary scene", not session.exists() and scene_is(rig), message)
    gate("close: its names are plain again", [r.namespace for r in maya_rigs.rigs()] == ["Manny_Rig"])
    gate("close: no tab namespace left", not [n for n in cmds.namespaceInfo(":", listOnlyNamespaces=True) or []
                                              if n.startswith(records.TAB_PREFIX)])
```

- [ ] **Step 2: Run them to see them fail**

Run: `... verify_scene_tabs.py convert layers open_close`
Expected: three `FAIL  phase ... ran to the end` (no module `opening`).

- [ ] **Step 3: Write `switching`**

`SkeldarAnim/maya_scenetabs/switching.py`:

```python
"""Scene tabs: switching. The tab being left is recorded (its time, view,
selection, layout, modified flag) and hidden; the new one is shown with its
own, in ONE undo chunk - so a Ctrl+Z past a switch brings the previous tab
back before it undoes that tab's step (measured: one undo restores the
namespace, the unit, the ranges and the visibility).

Hidden by `lodVisibility` and `hiddenInOutliner` on the tab's top nodes, never
`visibility`, which the animator keys.
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""

import maya.cmds as cmds

from . import records, session

VIEW_FLAGS = ("displayAppearance", "displayTextures", "displayLights", "shadows", "joints",
              "nurbsCurves", "polymeshes", "locators", "cameras", "grid")


def _gui():
    return not cmds.about(batch=True)


def tops(namespace):
    """The tab's top DAG nodes (its namespace or one nested in it)."""
    prefix = namespace + ":"
    return [t for t in cmds.ls(assemblies=True, long=True) or [] if t.lstrip("|").startswith(prefix)]


def _set(node, attr, value):
    plug = node + "." + attr
    if cmds.attributeQuery(attr, node=node, exists=True) and cmds.getAttr(plug, settable=True):
        cmds.setAttr(plug, value)


def hide(namespace):
    for top in tops(namespace):
        _set(top, "lodVisibility", 0)
        _set(top, "hiddenInOutliner", 1)


def show(namespace):
    for top in tops(namespace):
        _set(top, "lodVisibility", 1)
        _set(top, "hiddenInOutliner", 0)
    if _gui():
        cmds.evalDeferred("import maya.mel; maya.mel.eval('AEdagNodeCommonRefreshOutliners')",
                          lowestPriority=True)


# ------------------------------------------------------------------ the view

def _camera_shape(camera):
    return (cmds.listRelatives(camera, shapes=True, fullPath=True) or [camera])[0]


def capture_views():
    """Each model panel's camera, a startup camera's place, the display flags."""
    if not _gui():
        return []
    views = []
    for panel in cmds.getPanel(type="modelPanel") or []:
        try:
            camera = cmds.modelPanel(panel, q=True, camera=True)
        except RuntimeError:
            continue
        view = {"panel": panel, "camera": camera, "flags": {}}
        for flag in VIEW_FLAGS:
            try:
                view["flags"][flag] = cmds.modelEditor(panel, q=True, **{flag: True})
            except (RuntimeError, TypeError):
                pass
        if camera and cmds.objExists(camera):
            shape = _camera_shape(camera)
            if cmds.camera(shape, q=True, startupCamera=True):
                view["matrix"] = cmds.xform(camera, q=True, matrix=True, worldSpace=True)
                view["focal"] = cmds.getAttr(shape + ".focalLength")
                view["coi"] = cmds.getAttr(shape + ".centerOfInterest")
        views.append(view)
    return views


def apply_views(views):
    if not _gui():
        return
    panels = cmds.getPanel(type="modelPanel") or []
    for view in views or []:
        panel = view.get("panel")
        if panel not in panels:
            continue
        camera = view.get("camera")
        if camera and cmds.objExists(camera):
            cmds.modelPanel(panel, e=True, camera=camera)
            if "matrix" in view:
                shape = _camera_shape(camera)
                cmds.xform(camera, matrix=view["matrix"], worldSpace=True)
                cmds.setAttr(shape + ".focalLength", view["focal"])
                cmds.setAttr(shape + ".centerOfInterest", view["coi"])
        for flag, value in (view.get("flags") or {}).items():
            try:
                cmds.modelEditor(panel, e=True, **{flag: value})
            except (RuntimeError, TypeError):
                pass


# ------------------------------------------------------------------ the layout

def _layouts():
    try:
        return cmds.workspaceLayoutManager(listLayouts=True) or []
    except RuntimeError:
        return []


def save_layout(tab):
    if _gui():
        try:
            cmds.workspaceLayoutManager(saveAs=tab["layout"])
        except RuntimeError:
            pass


def load_layout(tab):
    if not _gui():
        return
    try:
        if tab["layout"] in _layouts():
            cmds.workspaceLayoutManager(setCurrent=tab["layout"])
    except RuntimeError:
        pass
    from . import bar
    bar.ensure_docked()


def forget_layout(tab):
    if _gui() and tab.get("layout") in _layouts():
        try:
            cmds.workspaceLayoutManager(delete=tab["layout"])
        except RuntimeError:
            pass


# ------------------------------------------------------------------ leave / enter

def leave(state):
    """The active tab recorded and hidden; its modified flag taken off Maya's."""
    active = state["active"]
    current = records.tab(state, active)
    if current is None:
        return state
    current = dict(current)
    current["modified"] = bool(current["modified"] or cmds.file(q=True, modified=True))
    current["unit"] = cmds.currentUnit(q=True, time=True)
    current["ranges"] = session.current_ranges()
    current["frame"] = cmds.currentTime(q=True)
    current["selection"] = cmds.ls(selection=True, uuid=True) or []
    current["views"] = capture_views()
    save_layout(current)
    hide(active)
    cmds.file(modified=False)
    return records.with_tab(state, current)


def enter(state, namespace, fresh=False):
    """`namespace` shown and made current with its time, view, selection and
    layout (`fresh`: a new tab takes a copy of the current layout)."""
    current = dict(records.tab(state, namespace))
    show(namespace)
    cmds.namespace(setNamespace=":" + namespace)
    if current.get("unit"):
        cmds.currentUnit(time=current["unit"], updateAnimation=True)
    session.apply_ranges(current.get("ranges"))
    if current.get("frame") is not None:
        cmds.currentTime(current["frame"], update=True)
    apply_views(current.get("views"))
    found = cmds.ls(current.get("selection") or [], long=True) or []
    if found:
        cmds.select(found, replace=True)
    else:
        cmds.select(clear=True)
    if fresh:
        save_layout(current)
    else:
        load_layout(current)
    return records.with_tab(dict(state, active=namespace), current)


def _restore(before):
    """A switch that failed half way: the tab that was active back, the rest hidden."""
    for item in before["tabs"]:
        if item["ns"] != before["active"]:
            hide(item["ns"])
    try:
        enter(before, before["active"])
    finally:
        session.write(before)


def switch(namespace):
    """One undo chunk: leave the active tab, enter `namespace`."""
    state = session.state()
    if namespace == state["active"]:
        return state
    if records.tab(state, namespace) is None:
        raise session.TabError("no tab %s" % namespace)
    before = state
    cmds.undoInfo(openChunk=True, chunkName="skeldarTabSwitch")
    try:
        try:
            state = enter(leave(state), namespace)
            session.write(state)
        except Exception:
            _restore(before)
            raise
    finally:
        cmds.undoInfo(closeChunk=True)
    return state


def cycle(step):
    """The next (`step` 1) or previous (-1) tab."""
    state = session.state()
    names = [t["ns"] for t in state["tabs"]]
    if len(names) < 2:
        return "One scene open - no other tab"
    target = names[(names.index(state["active"]) + step) % len(names)]
    switch(target)
    return "Tab: %s" % records.title(records.tab(session.state(), target))
```

- [ ] **Step 4: Write `opening`**

`SkeldarAnim/maya_scenetabs/opening.py`:

```python
"""Scene tabs: the open scene becoming tab 1, opening a file into a tab, an
empty tab, closing, reloading, back to one scene, a saved session restored,
tabs off, and the question on quit.

Imports run with `preserveReferences=True` (a nested reference stays one) and
`executeScriptNodes=False` (an import otherwise runs a file's open-type script
nodes - measured). An import flushes Maya's undo, as opening a file does.
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""

import os
import subprocess
import time

import maya.cmds as cmds

from . import layers, records, session, switching

ASK = None          # seam: callable(message, buttons) -> the button picked


def _ask(message, buttons, default):
    if ASK is not None:
        return ASK(message, buttons)
    if cmds.about(batch=True):
        return default
    return cmds.confirmDialog(title="Scene Tabs", message=message, button=list(buttons),
                              defaultButton=buttons[0], cancelButton=buttons[-1],
                              dismissString=buttons[-1])


def folder():
    path = os.path.join(cmds.internalVar(userAppDir=True), "SkeldarTabs").replace("\\", "/")
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def _taken():
    return cmds.namespaceInfo(":", listOnlyNamespaces=True) or []


def _mtime(path):
    return os.path.getmtime(path) if path and os.path.isfile(path) else 0.0


def start():
    """The open scene becomes tab 1: its layer root to the session, its content
    into its own namespace, the scene renamed to the session's file. Returns
    the state (unchanged when tabs are on already)."""
    state = session.state()
    if state["tabs"]:
        return state
    scene = (cmds.file(q=True, sceneName=True) or "").replace("\\", "/")
    namespace = records.namespace_for(scene or records.UNTITLED, _taken())
    first = records.new_tab(namespace, scene, cmds.currentUnit(q=True, time=True),
                            session.current_ranges(), _mtime(scene))
    first["frame"] = cmds.currentTime(q=True)
    first["modified"] = bool(cmds.file(q=True, modified=True))
    children = layers.take_root()
    session.move_into(namespace)
    layers.give_children(namespace, children)
    state = records.empty_state()
    state["tabs"], state["active"] = [first], namespace
    state["session"] = records.session_name(folder(), time.strftime("%Y%m%d_%H%M%S"))
    session.write(state)
    cmds.namespace(setNamespace=":" + namespace)
    cmds.file(rename=state["session"])
    return state


def _sweep(namespace):
    """The imported file's ui configuration node and any vaccine malware node
    deleted (never run: the import did not execute script nodes)."""
    from maya_scenesetup import character
    scripts = [s for s in cmds.namespaceInfo(":" + namespace, listOnlyDependencyNodes=True, recurse=True) or []
               if cmds.nodeType(s) == "script" and not cmds.referenceQuery(s, isNodeReferenced=True)]
    doomed = character.malware_nodes(scripts) + [
        s for s in scripts if s.split(":")[-1] == "uiConfigurationScriptNode"]
    for node in doomed:
        if cmds.objExists(node):
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    return doomed


def _ranges_of(namespace):
    node = ":%s:%s" % (namespace, records.CONFIG_NODE)
    if not cmds.objExists(node):
        return {}
    return records.ranges_from_script(cmds.getAttr(node + ".before") or "")


def _import(path, namespace):
    """`path` imported into `namespace` in its own unit. Returns (unit, ranges)."""
    ext = os.path.splitext(path)[1].lower()
    unit = records.read_unit(path) or cmds.currentUnit(q=True, time=True)
    layers.ensure_root()
    cmds.currentUnit(time=unit, updateAnimation=True)
    cmds.namespace(setNamespace=":")
    cmds.file(path, i=True, type=records.FILE_TYPES[ext], namespace=namespace,
              preserveReferences=True, executeScriptNodes=False, mergeNamespacesOnClash=False,
              ignoreVersion=True)
    _sweep(namespace)
    return unit, (_ranges_of(namespace) or session.current_ranges())


def _check(path):
    path = (path or "").replace("\\", "/")
    if os.path.splitext(path)[1].lower() not in records.FILE_TYPES:
        raise session.TabError("only Maya scenes open in a tab (.ma, .mb): %s" % os.path.basename(path))
    if not os.path.isfile(path):
        raise session.TabError("no such file: %s" % path)
    return path


def open_tab(path, index=None):
    """`path` into a new tab (the open scene becomes tab 1 first)."""
    path = _check(path)
    state = start()
    namespace = records.namespace_for(path, _taken())
    state = switching.leave(state)
    unit, ranges = _import(path, namespace)
    state = records.with_tab(state, records.new_tab(namespace, path, unit, ranges, _mtime(path)), index)
    state = switching.enter(state, namespace, fresh=True)
    session.write(state)
    cmds.file(modified=False)
    return "Opened %s in a tab (%s, %s)" % (os.path.basename(path), unit, records.range_text(ranges))


def open_any(path):
    """Maya's own Open while tabs are on: a saved session replaces the tabs
    (after asking about unsaved ones), any other scene opens in a new tab."""
    path = _check(path)
    if not records.holds_session(path):
        return open_tab(path)
    if not quit_ok():
        return "Open cancelled - the tabs are as they were"
    from . import hooks
    with hooks.bypass():
        cmds.file(path, open=True, force=True)
    return restore()


def new_tab():
    """An empty tab (its first Save asks for a path)."""
    state = start()
    namespace = records.namespace_for(records.UNTITLED, _taken())
    state = switching.leave(state)
    cmds.namespace(add=namespace, parent=":")
    state = records.with_tab(state, records.new_tab(namespace, "", cmds.currentUnit(q=True, time=True),
                                                    session.current_ranges()))
    state = switching.enter(state, namespace, fresh=True)
    session.write(state)
    return "New empty tab"


def _remove_namespace(namespace):
    """Every node of the namespace that can be deleted deleted; what Maya will
    not delete (the managers the first import into an empty scene makes inside
    the namespace, trap 158) merged into the root; the namespaces removed
    deepest first. `namespace -deleteNamespaceContent` dies on those managers
    («is locked, can not remove it», measured in the plan's own verify)."""
    if not cmds.namespace(exists=":" + namespace):
        return
    nodes = cmds.namespaceInfo(":" + namespace, listOnlyDependencyNodes=True, recurse=True, dagPath=True) or []
    for node in nodes:
        if cmds.objExists(node) and not cmds.referenceQuery(node, isNodeReferenced=True):
            try:
                cmds.lockNode(node, lock=False)
            except RuntimeError:
                pass
    for node in nodes:
        if cmds.objExists(node) and not cmds.referenceQuery(node, isNodeReferenced=True):
            try:
                cmds.delete(node)
            except (RuntimeError, ValueError):
                pass
    found = cmds.namespaceInfo(":" + namespace, listOnlyNamespaces=True, recurse=True) or []
    for child in sorted(found, key=lambda name: -name.count(":")) + [namespace]:
        if cmds.namespace(exists=":" + child.lstrip(":")):
            cmds.namespace(removeNamespace=":" + child.lstrip(":"), mergeNamespaceWithRoot=True)


def _delete_namespace(namespace):
    """The tab's blend nodes brought home, its references removed BY NODE (a
    path is ambiguous between two tabs of one file - the wrong copy went,
    measured), then its namespace and everything in it."""
    layers.home_blends(namespace)
    for uid, _ in session.top_references(namespace):
        found = cmds.ls(uid) or []
        if found:
            cmds.file(referenceNode=found[0], removeReference=True)
    _remove_namespace(namespace)


def _is_modified(state, item):
    return bool(item["modified"] or (item["ns"] == state["active"] and cmds.file(q=True, modified=True)))


def close_tab(namespace=None, ask=True):
    """A tab closed (asking about unsaved changes); down to one tab, the last
    one becomes an ordinary scene again."""
    state = session.state()
    namespace = namespace or state["active"]
    item = records.tab(state, namespace)
    if item is None:
        raise session.TabError("no tab %s" % namespace)
    name = records.title(dict(item, modified=False))
    if ask and _is_modified(state, item):
        answer = _ask("%s has unsaved changes." % name, ("Save", "Don't Save", "Cancel"), "Don't Save")
        if answer == "Cancel":
            return "Close cancelled - %s is still open" % name
        if answer == "Save":
            from . import saving
            saving.save_tab(namespace)
            state = session.state()
    if namespace == state["active"] and len(state["tabs"]) > 1:
        state = switching.switch(records.neighbour(state, namespace))
    _delete_namespace(namespace)
    switching.forget_layout(item)
    state = records.removed(state, namespace)
    session.write(state)
    if len(state["tabs"]) == 1:
        return finish()
    return "Closed %s" % name


def close_others(namespace=None):
    state = session.state()
    keep = namespace or state["active"]
    message = ""
    for item in [t for t in state["tabs"] if t["ns"] != keep]:
        message = close_tab(item["ns"])
        if "cancelled" in message:
            return message
    return message or "No other tab"


def reload_tab(namespace=None, ask=True):
    """The tab read again from its file, its unsaved changes dropped."""
    state = session.state()
    namespace = namespace or state["active"]
    item = records.tab(state, namespace)
    if item is None or not item["path"] or not os.path.isfile(item["path"]):
        raise session.TabError("nothing on disk to reload for %s" % namespace)
    name = records.title(dict(item, modified=False))
    if ask and _is_modified(state, item):
        if _ask("Drop the changes to %s and read it from disk?" % name, ("Reload", "Cancel"), "Cancel") != "Reload":
            return "Reload cancelled - %s is as it was" % name
    active = namespace == state["active"]
    keep_unit = cmds.currentUnit(q=True, time=True)
    _delete_namespace(namespace)
    unit, ranges = _import(item["path"], namespace)
    fresh_item = records.new_tab(namespace, item["path"], unit, ranges, _mtime(item["path"]))
    fresh_item["layout"] = item["layout"]
    state = records.with_tab(state, fresh_item)
    if active:
        state = switching.enter(state, namespace)
        cmds.file(modified=False)
    else:
        switching.hide(namespace)
        cmds.currentUnit(time=keep_unit, updateAnimation=True)
        cmds.namespace(setNamespace=":" + state["active"])
    session.write(state)
    return "Reloaded %s from disk" % name


def finish():
    """The last tab becomes an ordinary scene: its layers flattened, its nodes
    into the root namespace, the session gone, the scene named for its file."""
    state = session.state()
    if len(state["tabs"]) != 1:
        return ""
    last = state["tabs"][0]
    namespace = last["ns"]
    modified = _is_modified(state, last)
    switching.show(namespace)
    cmds.namespace(setNamespace=":")
    layers.flatten(namespace)
    moved = session.lift(namespace)
    session.drop_held(moved)
    _remove_namespace(namespace)            # what is left in it is the import's furniture
    session.delete()
    switching.forget_layout(last)
    if last["path"]:
        cmds.file(rename=last["path"])
    cmds.file(modified=modified)
    return "Back to one scene: %s" % records.title(dict(last, modified=False))


def restore():
    """A session file opened (autosave, a crash's recovery file): its tabs
    back, only the active one shown, the scene named for the session."""
    state = session.state()
    if not state["tabs"]:
        return ""
    for item in state["tabs"]:
        if item["ns"] != state["active"]:
            switching.hide(item["ns"])
    state = switching.enter(state, state["active"])
    session.write_quiet(state)
    if state.get("session"):
        cmds.file(rename=state["session"])
    cmds.file(modified=False)
    from . import hooks
    hooks.install()
    return "Restored %d tabs" % len(state["tabs"])


def tabs_off():
    """Every tab but the active one closed (asking), the active one an
    ordinary scene again."""
    state = session.state()
    if not state["tabs"]:
        return "Tabs are off already"
    message = close_others(state["active"])
    if "cancelled" in message:
        return "Tabs off cancelled - " + message
    return finish() or message


def unsaved():
    state = session.state()
    return [item for item in state["tabs"] if _is_modified(state, item)]


def quit_ok():
    """Maya may quit (or replace the tabs): nothing unsaved, or the animator
    saved or dropped it."""
    if not session.is_on():
        return True
    pending = unsaved()
    if pending:
        names = ", ".join(records.title(dict(t, modified=False)) for t in pending)
        answer = _ask("Unsaved tabs: %s" % names, ("Save all", "Discard", "Cancel"), "Cancel")
        if answer == "Cancel":
            return False
        if answer == "Save all":
            from . import saving
            for item in pending:
                saving.save_tab(item["ns"])
    cmds.file(modified=False)
    return True


def explore(namespace=None):
    state = session.state()
    item = records.tab(state, namespace or state["active"])
    path = (item or {}).get("path") or ""
    if not path:
        return "This tab has no file yet"
    subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    return "Shown in Explorer: %s" % path
```

- [ ] **Step 5: Run the phases**

Run: `... verify_scene_tabs.py session layers_alone convert layers open_close`
Expected: every line PASS, `0 of 55 gates failed`.

If `open: the nested reference stays a reference` fails because the reference node came in under another name, print `cmds.ls(type="reference")` in the gate's detail and match the node through `session.top_references("tab_film")` instead of the literal `tab_film:refRN` - the gate is about the reference's namespace, not its node's name.

- [ ] **Step 6: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs_msg.txt" <<'EOF'
feat(scenetabs): switching and opening - tab 1, open, new, close, back to one scene

A switch records and hides the tab being left and shows the new one with
its unit, ranges, frame, view, selection and layout in one undo chunk.
Proof: verify convert, layers, open_close.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_scenetabs/switching.py SkeldarAnim/maya_scenetabs/opening.py docs/superpowers/plans/verify_scene_tabs.py
git commit -F "$TEMP/scenetabs_msg.txt"
```

---

### Task 5: Switching and undo, proven

**Files:**
- Modify: `docs/superpowers/plans/verify_scene_tabs.py` (phase `switch`)
- Modify (only if a gate finds it): `SkeldarAnim/maya_scenetabs/switching.py`

**Interfaces:**
- Consumes: `switching.switch`, `switching.cycle`, `opening.open_tab` (Task 4).

- [ ] **Step 1: Write the phase**

Add above `PHASES` and register `"switch": phase_switch`:

```python
def phase_switch():
    """Each tab keeps its own time, view and selection; Ctrl+Z past a switch brings the tab back first."""
    from maya_scenetabs import opening, switching
    rig, film = copy("rig.ma"), copy("film.ma")
    fresh()
    cmds.file(rig, open=True, force=True)
    opening.open_tab(film)
    cmds.undoInfo(state=True, infinity=True)
    rig_frame = records.tab(session.state(), "tab_rig")["frame"]
    cmds.currentTime(12)
    cmds.select("tab_film:hero")
    switching.switch("tab_rig")
    gate("switch: the rig shows, the film hides", all(tops_visible("tab_rig")) and not any(tops_visible("tab_film")))
    gate("switch: the rig's unit", cmds.currentUnit(q=True, time=True) == "ntsc")
    gate("switch: the rig's ranges", [cmds.playbackOptions(q=True, minTime=True),
                                      cmds.playbackOptions(q=True, maxTime=True),
                                      cmds.playbackOptions(q=True, animationEndTime=True)] == [0.0, 50.0, 60.0])
    gate("switch: the rig's frame", cmds.currentTime(q=True) == rig_frame, (cmds.currentTime(q=True), rig_frame))
    gate("switch: the rig's namespace is current", current_ns() == "tab_rig")
    gate("switch: the rig's keys on their ntsc frames",
         cmds.keyframe("tab_rig:Manny_Rig:FKShoulder_R.rotateZ", q=True, timeChange=True) == [0.0, 20.0])
    switching.switch("tab_film")
    gate("switch: the film's frame comes back", cmds.currentTime(q=True) == 12.0)
    gate("switch: the film's selection comes back", cmds.ls(selection=True) == ["tab_film:hero"],
         cmds.ls(selection=True))
    gate("switch: the film's keys on their film frames (its base curve: the channel is in a layer)",
         cmds.keyframe("tab_film:hero_translateY", q=True, timeChange=True) == [5.0, 40.0],
         cmds.keyframe("tab_film:hero_translateY", q=True, timeChange=True))
    cmds.setAttr("tab_film:hero.translateX", 2)
    switching.switch("tab_rig")
    cmds.setAttr("tab_rig:Manny_Rig:FKShoulder_L.rotateY", 10)
    cmds.undo()
    gate("undo: the rig's step undone, still on the rig",
         cmds.getAttr("tab_rig:Manny_Rig:FKShoulder_L.rotateY") == 0.0 and session.state()["active"] == "tab_rig")
    cmds.undo()
    gate("undo: the next Ctrl+Z brings the film back",
         session.state()["active"] == "tab_film" and cmds.currentUnit(q=True, time=True) == "film"
         and all(tops_visible("tab_film")) and not any(tops_visible("tab_rig")))
    cmds.undo()
    gate("undo: and then undoes the film's step", cmds.getAttr("tab_film:hero.translateX") == 0.0)
    cmds.redo()
    cmds.redo()
    gate("redo: forward to the rig again",
         session.state()["active"] == "tab_rig" and cmds.currentUnit(q=True, time=True) == "ntsc")
    message = switching.cycle(1)
    gate("cycle: the next tab", session.state()["active"] == "tab_film", message)
    gate("cycle: wraps round", switching.cycle(1) and session.state()["active"] == "tab_rig")
```

- [ ] **Step 2: Run it**

Run: `... verify_scene_tabs.py switch`
Expected: `0 of 15 gates failed`. If `undo: the next Ctrl+Z brings the film back` fails with the film active but its tops still hidden, the chunk did not record `hide`/`show`: check that `switch` opens the chunk BEFORE `leave` (it does) and that nothing inside `leave` / `enter` runs `undoInfo -stateWithoutFlush` (trap 145).

- [ ] **Step 3: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs_msg.txt" <<'EOF'
test(scenetabs): switching and undo across a switch, proven

Proof: verify switch (unit, ranges, frame, selection per tab; Ctrl+Z past
a switch brings the tab back before undoing its step; redo; cycle).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add docs/superpowers/plans/verify_scene_tabs.py SkeldarAnim/maya_scenetabs/switching.py
git commit -F "$TEMP/scenetabs_msg.txt"
```

---

### Task 6: `saving` - a tab into its own plain file

**Files:**
- Create: `SkeldarAnim/maya_scenetabs/saving.py`
- Modify: `docs/superpowers/plans/verify_scene_tabs.py` (phase `save`)

**Interfaces:**
- Consumes: `records`, `session.lift / lower / write_quiet`, `layers.tab_root / detach / attach`, `switching.switch`.
- Produces: `CONFIRM` (seam: `callable(question) -> bool`), `PICK` (seam: `callable() -> path or ""`), `export_uuids(namespace) -> [uuid]`, `save_tab(namespace=None, path=None, adopt=True) -> str`, `save_as(namespace=None) -> str`. `adopt=False` writes a copy without the tab taking the path (stage 2's Shared send uses it).

- [ ] **Step 1: Write the failing phase**

Add above `PHASES` and register `"save": phase_save`:

```python
PROBES = {
    "rig.ma": [("Manny_Rig:FKShoulder_L.rotateZ", 10), ("Manny_Rig:FKShoulder_R.rotateZ", 20)],
    "film.ma": [("hero.rotateY", 20), ("hero.translateX", 20), ("ref:box.translateZ", 0), ("ref:box.translateX", 20)],
    "plain.mb": [("ball.translateY", 12)],
}


def edit_rig(prefix, tab=None):
    control = prefix + "Manny_Rig:FKShoulder_L"
    cmds.setKeyframe(control, attribute="rotateZ", time=0, value=0)
    cmds.setKeyframe(control, attribute="rotateZ", time=10, value=30)
    cmds.spaceLocator(name="madeHere")
    cmds.file(WORK + "/ref.ma", i=True, namespace="Extra", preserveReferences=True, executeScriptNodes=False)


def edit_film(prefix, tab=None):
    from maya_scenetabs import layers
    hero = prefix + "hero"
    cmds.select(hero)
    layer = cmds.animLayer("Layer2", addSelectedObjects=True)
    if tab:
        layers.adopt(layer, tab)
    cmds.setKeyframe(hero + ".translateX", time=20, value=7, animLayer=layer)
    cmds.setAttr(prefix + "ref:box.translateZ", 3)
    cmds.select(clear=True)


def edit_plain(prefix, tab=None):
    cmds.setKeyframe(prefix + "ball", attribute="translateY", time=12, value=5)


EDITS = (("rig.ma", "tab_rig", edit_rig), ("film.ma", "tab_film", edit_film), ("plain.mb", "tab_plain", edit_plain))


def direct(name, edit):
    """The same edits made in the file opened on its own, saved: the expectation."""
    path = copy(name, "direct_" + name)
    fresh()
    cmds.file(path, open=True, force=True)
    edit("")
    cmds.file(save=True, force=True, type=records.FILE_TYPES[os.path.splitext(name)[1]])
    return summary(path, PROBES[name])


def phase_save():
    """Each tab saved back equals its file edited directly; refusals write nothing."""
    from maya_scenetabs import layers, opening, saving, switching
    expected = {name: direct(name, edit) for name, _, edit in EDITS}
    paths = {name: copy(name) for name, _, _ in EDITS}
    fresh()
    cmds.file(paths["rig.ma"], open=True, force=True)
    opening.open_tab(paths["film.ma"])
    opening.open_tab(paths["plain.mb"])
    for name, namespace, edit in EDITS:
        switching.switch(namespace)
        edit(namespace + ":", namespace)
    def names():
        """The session's names. Left out: a reference node - after a save it
        legitimately sits in the root (session._ref_file) - checked by its
        namespace in references(); and the layers' curves and blend nodes,
        which Maya rebuilds under names of its own during a save (measured:
        `hero_rotate_Layer2` came back `Layer10`) - checked by playing them."""
        rebuilt = set(cmds.ls(type=("animCurve", "animBlendNodeBase")) or [])
        return sorted(n for n in cmds.ls() if cmds.nodeType(n) != "reference" and n not in rebuilt)

    def references():
        return sorted(cmds.referenceQuery(r, namespace=True) for r in cmds.ls(type="reference") or []
                      if not r.endswith("sharedReferenceNode"))

    for _, namespace, _ in EDITS:
        layers.home_blends(namespace)           # what every save does first
    before, refs_before = names(), references()
    for name, namespace, _ in EDITS:
        switching.switch(namespace)
        message = saving.save_tab()
        gate("save %s: written" % namespace, message.startswith("Saved"), message)
        gate("save %s: the tab is clean" % namespace,
             not records.tab(session.state(), namespace)["modified"] and not cmds.file(q=True, modified=True))
    gate("save: the session is exactly as before the saves", names() == before,
         sorted(set(names()) ^ set(before))[:10])
    gate("save: every reference back under its tab", references() == refs_before, references())
    switching.switch("tab_film")
    gate("save: the film tab still plays both its layers in the session",
         value_at("tab_film:hero.rotateY", 20) == 45.0 and value_at("tab_film:hero.translateX", 20) == 7.0,
         (value_at("tab_film:hero.rotateY", 20), value_at("tab_film:hero.translateX", 20)))
    switching.switch("tab_rig")
    cmds.createNode("transform", name=":madeHere")
    with open(paths["rig.ma"], "rb") as handle:
        saved_rig = handle.read()
    try:
        saving.save_tab()
        refused = ""
    except session.TabError as exc:
        refused = str(exc)
    gate("save: a name the root namespace holds refuses by name", "madeHere" in refused, refused)
    with open(paths["rig.ma"], "rb") as handle:
        gate("save: the refused save wrote nothing", handle.read() == saved_rig)
    gate("save: the refused save put every name back",
         cmds.objExists("tab_rig:madeHere") and cmds.objExists("|madeHere")
         and names() == sorted(before + ["madeHere"]),
         sorted(set(names()) ^ set(before + ["madeHere"]))[:10])
    cmds.delete("|madeHere")
    switching.switch("tab_plain")
    stamp = os.path.getmtime(paths["plain.mb"]) + 20
    os.utime(paths["plain.mb"], (stamp, stamp))
    stamp = os.path.getmtime(paths["plain.mb"])                 # what NTFS kept (100 ns)
    cmds.setAttr("tab_plain:ball.translateZ", 1)
    saving.CONFIRM = lambda question: False
    message = saving.save_tab()
    saving.CONFIRM = None
    gate("save: a file changed on disk asks first; No writes nothing",
         "cancelled" in message and abs(os.path.getmtime(paths["plain.mb"]) - stamp) < 1e-3, message)
    cmds.setAttr("tab_plain:ball.translateZ", 0)
    switching.switch("tab_film")
    target = RUN + "/film_saved_as.ma"
    saving.save_tab(path=target)
    gate("save as: the tab takes the new path",
         records.tab(session.state(), "tab_film")["path"] == target and os.path.isfile(target))
    copy_path = RUN + "/film_copy.ma"
    saving.save_tab(path=copy_path, adopt=False)
    gate("save a copy: written, the tab keeps its path",
         os.path.isfile(copy_path) and records.tab(session.state(), "tab_film")["path"] == target)
    actual = {"rig.ma": summary(paths["rig.ma"], PROBES["rig.ma"]),
              "film.ma": summary(target, PROBES["film.ma"]),
              "plain.mb": summary(paths["plain.mb"], PROBES["plain.mb"])}
    for name in expected:
        for key in ("names", "keys", "layers", "refs", "displays", "ik_solved", "values", "unit", "ranges"):
            mine, theirs = actual[name][key], expected[name][key]
            same = mine == theirs
            if same:
                detail = ""
            elif key == "names":
                detail = "only the tab's: %s | only the direct: %s" % (sorted(set(mine) - set(theirs))[:15],
                                                                       sorted(set(theirs) - set(mine))[:15])
            else:
                detail = "tab %r / direct %r" % (mine, theirs)
            gate("save %s: %s as the same edits made directly" % (name, key), same, detail[:900])
```

- [ ] **Step 2: Run it to see it fail**

Run: `... verify_scene_tabs.py save`
Expected: `FAIL  phase save ran to the end` (no module `saving`).

- [ ] **Step 3: Write `saving`**

`SkeldarAnim/maya_scenetabs/saving.py`:

```python
"""Scene tabs: a tab saved into its own plain file - no prefix, its own fps
and ranges, its own layers and references.

The tab's nodes go into the root namespace for the length of the export and
come back by UUID (`session.lift` / `lower`); its layer root is cut from the
session's and written as BaseAnimation; its ranges go into its configuration
node; the file is written to a temporary name and then replaces the tab's file,
so a failed save never leaves half a file. Unrecorded: a save nets to nothing.
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""

import os

import maya.cmds as cmds

from . import layers, records, session, switching

CONFIRM = None      # seam: callable(question) -> bool
PICK = None         # seam: callable() -> a path, or "" for none


def _confirm(question):
    if CONFIRM is not None:
        return CONFIRM(question)
    if cmds.about(batch=True):
        return False
    return cmds.confirmDialog(title="Scene Tabs", message=question, button=["Overwrite", "Cancel"],
                              defaultButton="Cancel", cancelButton="Cancel",
                              dismissString="Cancel") == "Overwrite"


def _pick():
    if PICK is not None:
        return PICK()
    if cmds.about(batch=True):
        return ""
    found = cmds.fileDialog2(fileMode=0, caption="Save the tab as",
                             fileFilter="Maya ASCII (*.ma);;Maya Binary (*.mb)") or []
    return found[0].replace("\\", "/") if found else ""


def _config(namespace, ranges):
    """The tab's configuration node carrying its ranges into its file."""
    node = ":%s:%s" % (namespace, records.CONFIG_NODE)
    text = records.config_script(ranges)
    if cmds.objExists(node):
        cmds.setAttr(node + ".before", text, type="string")
        return node
    return cmds.scriptNode(name=node, scriptType=records.CONFIG_SCRIPT_TYPE, beforeScript=text,
                           sourceType="mel")


def export_uuids(namespace):
    """Every node the tab's file holds: its own nodes at every level (not
    referenced, not furniture, not a reference node) and its top references'
    nodes - found by their namespace, since a saved reference's node sits in
    the root (`session._ref_file`)."""
    own_config = "%s:%s" % (namespace, records.CONFIG_NODE)
    out = []
    for path in cmds.namespaceInfo(":" + namespace, listOnlyDependencyNodes=True, recurse=True,
                                   dagPath=True) or []:
        if cmds.referenceQuery(path, isNodeReferenced=True):
            continue
        kind = cmds.nodeType(path)
        leaf = path.split("|")[-1].split(":")[-1]
        if kind == "reference" or records.is_furniture(leaf, kind):
            continue
        if leaf == records.CONFIG_NODE and path.lstrip(":") != own_config:
            #  an import made inside the tab brought its file's configuration
            #  node (Maya skips it only when the ROOT has one - a tab's sits in
            #  the tab); in the file it runs after ours and wins (measured:
            #  the rig tab reopened at 1-120 for 0-50)
            continue
        out.append(cmds.ls(path, uuid=True)[0])
    return out + [uid for uid, _ in session.top_references(namespace)]


def save_tab(namespace=None, path=None, adopt=True):
    """The tab (the active one by default) into `path` (its own file by
    default). `adopt`: the tab takes the path and is clean after."""
    state = session.state()
    namespace = namespace or state["active"]
    item = records.tab(state, namespace)
    if item is None:
        raise session.TabError("no tab %s" % namespace)
    target = (path or item["path"] or "").replace("\\", "/")
    if not target:
        target = _pick()
        if not target:
            return "Save cancelled - %s has no file yet" % records.title(dict(item, modified=False))
        path = target
    ext = os.path.splitext(target)[1].lower()
    if ext not in records.FILE_TYPES:
        raise session.TabError("a tab saves as .ma or .mb: %s" % os.path.basename(target))
    if namespace != state["active"]:
        state = switching.switch(namespace)
        item = records.tab(state, namespace)
    if not path and records.changed_on_disk(target, item["mtime"]):
        if not _confirm("%s changed on disk since you opened it. Overwrite it?" % os.path.basename(target)):
            return "Save cancelled - %s left as it is on disk" % os.path.basename(target)
    ranges = session.current_ranges()
    temporary = target + ".skeldartmp"
    recording = cmds.undoInfo(q=True, stateWithoutFlush=True)
    selection = cmds.ls(selection=True, uuid=True) or []
    current = cmds.namespaceInfo(currentNamespace=True) or ":"
    moved, links = None, []
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        _config(namespace, ranges)
        layers.home_blends(namespace)
        uuids = export_uuids(namespace)
        renames = {}
        tab_root = layers.tab_root(namespace)
        if tab_root:
            links = layers.detach(tab_root)
            renames[cmds.ls(tab_root, uuid=True)[0]] = records.FILE_LAYER_ROOT
        cmds.namespace(setNamespace=":")
        moved = session.lift(namespace, renames)
        cmds.select(cmds.ls(uuids) or [], noExpand=True, replace=True)
        cmds.file(temporary, exportSelected=True, preserveReferences=True, type=records.FILE_TYPES[ext],
                  force=True)
    except Exception:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise
    finally:
        if moved is not None:
            session.lower(moved)
        cmds.namespace(setNamespace=current if current.startswith(":") else ":" + current)
        layers.attach(links)
        layers.home_blends(namespace)       # Maya rebuilt some in the root on the way (measured)
        found = cmds.ls(selection) or []
        if found:
            cmds.select(found, replace=True)
        else:
            cmds.select(clear=True)
        cmds.undoInfo(stateWithoutFlush=recording)
    os.replace(temporary, target)
    if adopt:
        item = dict(item, path=target, mtime=os.path.getmtime(target), modified=False)
        session.write_quiet(records.with_tab(session.state(), item))
        cmds.file(modified=False)
    return "Saved %s (%s, %s)" % (os.path.basename(target), cmds.currentUnit(q=True, time=True),
                                  records.range_text(ranges))


def save_as(namespace=None):
    target = _pick()
    if not target:
        return "Save As cancelled"
    return save_tab(namespace, path=target)
```

- [ ] **Step 4: Run the phase**

Run: `... verify_scene_tabs.py save`
Expected: every line PASS, `0 of 42 gates failed`.

Three gates that can fail, and how to read them:
- `ik_solved` False on the tab's side only: the export did not take the root's shared `ikRPsolver` along with the rig's ikHandles. Add to the export selection the solvers the tab's handles connect to: in `save_tab`, after `uuids = export_uuids(namespace)`, extend it with `cmds.ls(sorted(set(sum([cmds.listConnections(h + ".ikSolver") or [] for h in cmds.ls(":%s:*" % namespace, type="ikHandle", recursive=True) or []], []))), uuid=True)`, and keep the gate.
- `names` differing only by Maya's own nodes that a plain open-and-save adds and an export does not (for example a `defaultRenderLayer`-like manager under a new name): add that node's TYPE to `records.FURNITURE_TYPES` with a comment naming the run, and its unit test in `Furniture`; never filter by a name in the verify.
- `ranges` failing with `[1.0, 120.0, ...]`: the configuration node did not reach the file (its name clashed with a root one held aside - look for `skeldarHeld_` in `cmds.ls()`).

- [ ] **Step 5: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs_msg.txt" <<'EOF'
feat(scenetabs): save a tab into its own plain file

Lifted into the root namespace for the export and lowered back by UUID,
its layer root written as BaseAnimation, its ranges in its configuration
node, temp file then replace. Proof: verify save (each tab equals the same
edits made in its file directly; a clash, a file changed on disk and Save
As).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_scenetabs/saving.py docs/superpowers/plans/verify_scene_tabs.py
git commit -F "$TEMP/scenetabs_msg.txt"
```

---

### Task 7: `hooks` - Maya's Save / Open / New, new layers, the session restored

**Files:**
- Create: `SkeldarAnim/maya_scenetabs/hooks.py`
- Modify: `docs/superpowers/plans/verify_scene_tabs.py` (phases `hooks`, `restore`)

**Interfaces:**
- Consumes: `opening.open_any / new_tab / restore / quit_ok`, `saving.save_tab`, `layers.adopt`, `records.save_plan / is_autosave`.
- Produces: `defer(fn)`, `bypass` (context manager), `on_save(client_data=None) -> bool`, `on_open(file_obj, client_data=None) -> bool`, `on_new(client_data=None) -> bool`, `on_layer(node, client_data=None)`, `install(force=False) -> bool`, `remove()`. State on `sys._skeldar_scenetabs` (trap 111): `{"callbacks", "jobs", "bypass", "defer", "quit_filter"}`; the verify sets `"defer"` to its queue.

- [ ] **Step 1: Write the failing phases**

Add above `PHASES` and register `"hooks": phase_hooks, "restore": phase_restore`:

```python
def hooks_on():
    from maya_scenetabs import hooks
    hooks.install(force=True)
    hooks._st()["defer"] = QUEUE.append
    return hooks


def phase_hooks():
    """Maya's own Save, Save As, New and Open redirected; an autosave let through; a new layer adopted."""
    from maya_scenetabs import layers, switching
    rig, film, plain = copy("rig.ma"), copy("film.ma"), copy("plain.mb")
    fresh()
    cmds.file(rig, open=True, force=True)
    from maya_scenetabs import opening
    opening.open_tab(film)
    hooks = hooks_on()
    session_file = session.state()["session"]
    cmds.setAttr("tab_film:hero.translateX", 2)
    stamp = os.path.getmtime(film)
    try:
        cmds.file(save=True, force=True)
    except RuntimeError:
        pass                                    # «cancelled by user supplied callback»
    flush()
    gate("hooks: Maya's Save saves the active tab", os.path.getmtime(film) != stamp
         and not os.path.exists(session_file))
    gate("hooks: the scene keeps the session's name", scene_is(session_file))
    target = RUN + "/film_hook_as.ma"
    cmds.file(rename=target)
    try:
        cmds.file(save=True, force=True)
    except RuntimeError:
        pass
    flush()
    gate("hooks: Save As saves the active tab under the new name",
         os.path.isfile(target) and records.tab(session.state(), "tab_film")["path"] == target
         and scene_is(session_file))
    autosave = (cmds.autoSave(q=True, destinationFolder=True) or (RUN + "/autosave/")).replace("\\", "/")
    os.makedirs(autosave, exist_ok=True)
    auto = autosave.rstrip("/") + "/tabs_auto.ma"
    cmds.file(rename=auto)
    cmds.file(save=True, force=True, type="mayaAscii")
    cmds.file(rename=session_file)
    gate("hooks: an autosave is let through", os.path.isfile(auto) and records.holds_session(auto))
    try:
        cmds.file(new=True, force=True)
    except RuntimeError:
        pass
    flush()
    names = [t["ns"] for t in session.state()["tabs"]]
    gate("hooks: File > New opens an empty tab", names == ["tab_rig", "tab_film", "tab_untitled"]
         and cmds.namespace(exists=":tab_rig"), names)
    try:
        cmds.file(plain, open=True, force=True)
    except RuntimeError:
        pass
    flush()
    names = [t["ns"] for t in session.state()["tabs"]]
    gate("hooks: File > Open opens the file in a tab", "tab_plain" in names and cmds.objExists("tab_plain:ball"),
         names)
    switching.switch("tab_film")
    cmds.select("tab_film:hero")
    made = cmds.animLayer("ByHook", addSelectedObjects=True)
    flush()
    gate("hooks: a new layer goes under the active tab's root",
         layer_parent(made) == layers.tab_root("tab_film"), layer_parent(made))
    hooks.remove()
    gate("hooks: removed", not hooks._st()["callbacks"])


def phase_restore():
    """A session file (autosave, a crash's recovery) brings its tabs back; tabs off ends them."""
    from maya_scenetabs import hooks, layers, opening, switching
    rig, film, plain = copy("rig.ma"), copy("film.ma"), copy("plain.mb")
    fresh()
    cmds.file(rig, open=True, force=True)
    opening.open_tab(film)
    opening.open_tab(plain)
    switching.switch("tab_film")
    cmds.currentTime(15)
    switching.switch("tab_plain")
    switching.switch("tab_film")
    recovered = RUN + "/recovered_session.ma"
    with hooks.bypass():
        cmds.file(rename=recovered)
        cmds.file(save=True, force=True, type="mayaAscii")
    gate("restore: the file holds the session", records.holds_session(recovered))
    fresh()
    cmds.file(recovered, open=True, force=True)
    message = opening.restore()
    state = session.state()
    gate("restore: three tabs back", [t["ns"] for t in state["tabs"]] == ["tab_rig", "tab_film", "tab_plain"],
         message)
    gate("restore: only the active tab shows",
         all(tops_visible("tab_film")) and not any(tops_visible("tab_rig")) and not any(tops_visible("tab_plain")))
    gate("restore: the active tab's unit and frame",
         cmds.currentUnit(q=True, time=True) == "film" and cmds.currentTime(q=True) == 15.0)
    gate("restore: the scene takes the session's name", scene_is(state["session"]))
    hooks.remove()
    opening.ASK = lambda message, buttons: "Don't Save"
    message = opening.tabs_off()
    opening.ASK = None
    gate("tabs off: one ordinary scene, the active one", not session.exists() and scene_is(film)
         and cmds.objExists("hero") and not cmds.namespace(exists=":tab_film"), message)
    gate("tabs off: its layers are plain again", layers.root() == "BaseAnimation"
         and layer_parent("Layer1") == "BaseAnimation")
```

- [ ] **Step 2: Run them to see them fail**

Run: `... verify_scene_tabs.py hooks restore`
Expected: two `FAIL  phase ... ran to the end` (no module `hooks`).

- [ ] **Step 3: Write `hooks`**

`SkeldarAnim/maya_scenetabs/hooks.py`:

```python
"""Scene tabs: Maya's own Save, Open and New redirected while two or more tabs
are open; a new animation layer put under the active tab's root; the bar kept
in step with Undo, Redo and a scene opened; a quit that asks about unsaved
tabs.

The checks return False (Maya then prints «File operation cancelled by user
supplied callback») and do the tab's work one idle later. The Save check has
no file variant (kInvalidParameter, measured) and reads the target from the
scene name, which Save As has already set; the Open check gets the file
(`(MFileObject, clientData) -> bool`). State on `sys._skeldar_scenetabs`
(trap 111). `executeDeferred` never runs in mayapy, so `defer` has a seam.
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""

import sys
import traceback

import maya.cmds as cmds

from . import records, session


def _st():
    state = getattr(sys, "_skeldar_scenetabs", None)
    if state is None:
        state = {"callbacks": [], "jobs": [], "bypass": 0, "defer": None, "quit_filter": None}
        sys._skeldar_scenetabs = state
    return state


def defer(fn):
    hook = _st()["defer"]
    if hook is not None:
        return hook(fn)
    import maya.utils
    maya.utils.executeDeferred(fn)
    return None


class bypass(object):
    """Our own file -open / -new / -save pass the checks."""

    def __enter__(self):
        _st()["bypass"] += 1
        return self

    def __exit__(self, *exc):
        _st()["bypass"] -= 1
        return False


def _bypassed():
    return _st()["bypass"] > 0


def _say(message):
    if not message:
        return
    try:
        from . import bar
        bar.say(message)
        bar.refresh()
    except Exception:                                           # noqa: BLE001
        print("Scene Tabs: " + message)


def _reported(fn):
    def run():
        try:
            _say(fn())
        except Exception as exc:                                # noqa: BLE001
            print(traceback.format_exc())
            _say("Scene Tabs: %s" % exc)
    return run


def on_save(client_data=None):
    if _bypassed() or not session.is_on():
        return True
    target = (cmds.file(q=True, sceneName=True) or "").replace("\\", "/")
    try:
        autosave = cmds.autoSave(q=True, destinationFolder=True) or ""
    except RuntimeError:
        autosave = ""
    if records.is_autosave(target, autosave):
        return True
    state = session.state()
    action, path = records.save_plan(target, state.get("session", ""))
    if state.get("session"):
        cmds.file(rename=state["session"])
    from . import saving
    if action == "save":
        defer(_reported(lambda: saving.save_tab()))
    else:
        defer(_reported(lambda: saving.save_tab(path=path)))
    return False


def on_open(file_obj, client_data=None):
    if _bypassed() or not session.is_on():
        return True
    path = (file_obj.resolvedFullName() or file_obj.rawFullName() or "").replace("\\", "/")
    from . import opening
    defer(_reported(lambda: opening.open_any(path)))
    return False


def on_new(client_data=None):
    if _bypassed() or not session.is_on():
        return True
    from . import opening
    defer(_reported(opening.new_tab))
    return False


def on_layer(node, client_data=None):
    """Called as the node is created, before the command names and parents it:
    the layer is followed by its UUID and adopted one idle later."""
    if _bypassed() or not session.exists():
        return
    import maya.api.OpenMaya as om
    uid = om.MFnDependencyNode(node).uuid().asString()

    def later():
        from . import layers
        found = cmds.ls(uid) or []
        if session.exists() and found:
            layers.adopt(found[0], session.state()["active"])
    defer(later)


def _refresh_bar():
    try:
        from . import bar
        bar.refresh()
    except Exception:                                           # noqa: BLE001
        pass


def _scene_opened():
    """A scene opened by any road: a session file brings its tabs back."""
    if session.exists():
        from . import opening
        defer(_reported(opening.restore))
    else:
        _refresh_bar()


def _install_quit_filter():
    import maya_hubqt
    q = maya_hubqt.qt()
    if q is None:
        return
    import maya.OpenMayaUI as omui
    window = q.shiboken.wrapInstance(int(omui.MQtUtil.mainWindow()), q.QtWidgets.QWidget)

    class QuitFilter(q.QtCore.QObject):
        def eventFilter(self, obj, event):
            if event.type() == q.QtCore.QEvent.Close:
                from . import opening
                try:
                    if not opening.quit_ok():
                        event.ignore()
                        return True
                except Exception:                               # noqa: BLE001
                    print(traceback.format_exc())
            return False

    keeper = QuitFilter(window)
    window.installEventFilter(keeper)
    _st()["quit_filter"] = (keeper, window)


def install(force=False):
    """The callbacks (and in a GUI the jobs and the quit filter), once."""
    if cmds.about(batch=True) and not force:
        return False
    state = _st()
    if state["callbacks"]:
        return True
    import maya.api.OpenMaya as om
    state["callbacks"] = [
        om.MSceneMessage.addCheckCallback(om.MSceneMessage.kBeforeSaveCheck, on_save),
        om.MSceneMessage.addCheckFileCallback(om.MSceneMessage.kBeforeOpenCheck, on_open),
        om.MSceneMessage.addCheckCallback(om.MSceneMessage.kBeforeNewCheck, on_new),
        om.MDGMessage.addNodeAddedCallback(on_layer, "animLayer"),
    ]
    if not cmds.about(batch=True):
        state["jobs"] = [cmds.scriptJob(event=("Undo", _refresh_bar)),
                         cmds.scriptJob(event=("Redo", _refresh_bar)),
                         cmds.scriptJob(event=("SceneOpened", _scene_opened))]
        try:
            _install_quit_filter()
        except Exception:                                       # noqa: BLE001
            print(traceback.format_exc())
    return True


def remove():
    state = _st()
    if state["callbacks"]:
        import maya.api.OpenMaya as om
        for callback in state["callbacks"]:
            try:
                om.MMessage.removeCallback(callback)
            except RuntimeError:
                pass
    for job in state["jobs"]:
        if cmds.scriptJob(exists=job):
            cmds.scriptJob(kill=job, force=True)
    if state["quit_filter"]:
        keeper, window = state["quit_filter"]
        try:
            window.removeEventFilter(keeper)
        except RuntimeError:
            pass
    state.update(callbacks=[], jobs=[], quit_filter=None, defer=None)
```

- [ ] **Step 4: Run the phases**

Run: `... verify_scene_tabs.py hooks restore`
Expected: every line PASS, `0 of 15 gates failed`.

If `hooks: a new layer goes under the active tab's root` fails with the parent still `skeldarTabsLayerRoot`: check the callback ran at all (`QUEUE` non-empty right after `animLayer`). `flush()` runs after the command ended, which is the order `later` expects (as the real `executeDeferred` in a GUI).

- [ ] **Step 5: Run every phase together**

Run: `... verify_scene_tabs.py all`
Expected: every line PASS, `0 of 127 gates failed` (session 6, layers_alone 11, convert 9, layers 11, open_close 18, switch 15, save 42, hooks 8, restore 7). This exact code was run while planning: 127 of 127.

- [ ] **Step 6: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs_msg.txt" <<'EOF'
feat(scenetabs): Maya's Save, Open and New redirected; a session restored

Save saves the active tab, Save As under the new name, an autosave passes,
New opens an empty tab, Open opens a tab (a saved session replaces the
tabs); a new layer goes under the active tab's root; tabs off. Proof:
verify hooks, restore, and every phase together.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_scenetabs/hooks.py docs/superpowers/plans/verify_scene_tabs.py
git commit -F "$TEMP/scenetabs_msg.txt"
```

---

### Task 8: `bar` - the tab bar above the viewport

**Files:**
- Create: `SkeldarAnim/maya_scenetabs/bar.py`
- Create: `tests/test_scenetabs_bar.py`

**Interfaces:**
- Consumes: `records.bar_items`, `session.state`, `opening.*`, `saving.save_tab / save_as`, `switching.switch`, `hooks.install`, `maya_hubqt.qt / host_widget / run_menu`, `maya_hubstyle.TOKENS`.
- Produces: `CONTROL = "skeldarSceneTabs"`, `TABS_BAR_VAR = "skeldarSceneTabsBar"`, `show() -> str`, `ensure_docked() -> str`, `hide_bar() -> str`, `build()`, `refresh()`, `say(message) -> str`, `bar_class()` (the Qt class), `stylesheet(tokens, scale) -> str`, class `Actions`. The Qt class takes an `actions` object with methods `switch(ns)`, `close(ns)`, `save(ns)`, `save_as(ns)`, `reload(ns)`, `explore(ns)`, `close_others(ns)`, `open_file()`, `open_path(path)`, `recent() -> [path]`, `empty_tab()`, `tabs_off()`, `hide()`, `items() -> [item]`.

- [ ] **Step 1: Write the failing tests**

`tests/test_scenetabs_bar.py`:

```python
"""The scene tabs bar offscreen on fake actions (2026-10-15): tabs, stars,
switching, closing, the single-scene item. The docking is the animator's live
check.

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None


def _items(active=1, star=False):
    return [{"ns": "tab_a", "text": "attack", "tip": "C:/a.ma\nntsc, 0-50", "active": active == 0, "closable": True},
            {"ns": "tab_b", "text": "walk" + ("*" if star else ""), "tip": "C:/b.ma\nfilm, 5-40",
             "active": active == 1, "closable": True}]


class FakeActions(object):

    def __init__(self):
        self.log = []
        self.next_items = _items()

    def __getattr__(self, name):
        def record(*args):
            self.log.append((name,) + args)
            return ""
        return record

    def recent(self):
        return []

    def items(self):
        return self.next_items


@unittest.skipIf(QT is None, "no Qt")
class TabBar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])

    def setUp(self):
        from maya_scenetabs import bar
        self.actions = FakeActions()
        self.bar = bar.bar_class()(self.actions)
        self.bar.populate(_items())

    def test_one_tab_per_item_with_its_tooltip(self):
        tabs = self.bar.tabs
        self.assertEqual([tabs.tabText(i) for i in range(tabs.count())], ["attack", "walk"])
        self.assertEqual(tabs.tabToolTip(1), "C:/b.ma\nfilm, 5-40")
        self.assertEqual(tabs.currentIndex(), 1)

    def test_populating_switches_nothing(self):
        self.assertEqual(self.actions.log, [])

    def test_picking_a_tab_switches_to_it(self):
        self.bar.tabs.setCurrentIndex(0)
        self.assertIn(("switch", "tab_a"), self.actions.log)

    def test_the_close_button_closes_that_tab(self):
        self.bar.tabs.tabCloseRequested.emit(0)
        self.assertIn(("close", "tab_a"), self.actions.log)

    def test_a_single_scene_has_no_close_button(self):
        self.bar.populate([{"ns": "", "text": "attack*", "tip": "C:/a.ma", "active": True, "closable": False}])
        for side in (QT.QtWidgets.QTabBar.LeftSide, QT.QtWidgets.QTabBar.RightSide):
            self.assertIsNone(self.bar.tabs.tabButton(0, side))

    def test_the_tick_updates_the_star_without_repopulating(self):
        self.actions.next_items = _items(star=True)
        self.bar.tick()
        self.assertEqual(self.bar.tabs.tabText(1), "walk*")
        self.assertEqual(self.actions.log, [])

    def test_the_stylesheet_uses_the_hubs_colours(self):
        from maya_scenetabs import bar
        import maya_hubstyle
        sheet = bar.stylesheet(maya_hubstyle.TOKENS, 1.5)
        self.assertIn(maya_hubstyle.TOKENS["accent"], sheet)
        self.assertIn("skeldarSceneTabsTabs", sheet)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them to see them fail**

Run: `$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenetabs_bar -v`
Expected: ERROR, no module `maya_scenetabs.bar`.

- [ ] **Step 3: Write `bar`**

`SkeldarAnim/maya_scenetabs/bar.py`:

```python
"""Scene tabs: the bar above the viewport (2026-10-15).

A workspaceControl `skeldarSceneTabs` holding a QTabBar in the hub's colours:
a tab per scene, `*` on a modified one, x to close, "+" to open (a file, a
recent one, an empty tab), the right button for Save / Save As / Reload /
Show in Explorer / Close others, the middle button closes, the menu turns
tabs off or hides the bar. Maya replays the control's uiScript at startup,
which also installs the hooks.
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""

import os
import sys
import traceback

import maya.cmds as cmds

from . import records, session

CONTROL = "skeldarSceneTabs"
LABEL = "Scene Tabs"
TABS_BAR_VAR = "skeldarSceneTabsBar"
ROOT_NAME = "skeldarSceneTabsRoot"
HEIGHT = 30


def _state():
    state = getattr(sys, "_skeldar_scenetabs_bar", None)
    if state is None:
        state = {"bar": None}
        sys._skeldar_scenetabs_bar = state
    return state


def plugin_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")


def uiscript(root):
    root = root.replace("\\", "/").rstrip("/")
    return ("import sys\n_p = \"{0}\"\nif _p not in sys.path:\n    sys.path.insert(0, _p)\n"
            "from maya_scenetabs import bar\nbar.build()\n").format(root)


def say(message):
    if message and not cmds.about(batch=True):
        cmds.inViewMessage(assistMessage=message, position="topCenter", fade=True)
    print("Scene Tabs: %s" % message)
    return message


def ensure_docked():
    """The bar shown (made the first time, docked above the viewport) and the hooks on."""
    if cmds.about(batch=True):
        return ""
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.workspaceControl(CONTROL, edit=True, restore=True, visible=True)
    else:
        cmds.workspaceControl(CONTROL, label=LABEL, retain=False, floating=False,
                              dockToMainWindow=("top", False), heightProperty="fixed",
                              initialHeight=HEIGHT, uiScript=uiscript(plugin_root()))
    from . import hooks
    hooks.install()
    return CONTROL


def show():
    cmds.optionVar(intValue=(TABS_BAR_VAR, 1))
    return ensure_docked()


def hide_bar():
    cmds.optionVar(intValue=(TABS_BAR_VAR, 0))
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.workspaceControl(CONTROL, edit=True, visible=False)
    return "Scene tabs bar hidden - the Scene Tabs hotkey row (window.tabs) brings it back"


def stylesheet(tokens, scale):
    px = lambda value: "%dpx" % max(1, int(round(value * scale)))      # noqa: E731
    return (
        "QWidget#{root} {{ background: {panel}; }}"
        "QTabBar#skeldarSceneTabsTabs::tab {{ background: {card}; color: {text2}; padding: {p4} {p10};"
        " margin-right: {p2}; border: 1px solid {line}; border-bottom: none;"
        " border-top-left-radius: {p6}; border-top-right-radius: {p6}; }}"
        "QTabBar#skeldarSceneTabsTabs::tab:selected {{ background: {card_active}; color: {text};"
        " border-color: {accent}; }}"
        "QTabBar#skeldarSceneTabsTabs::tab:hover:!selected {{ background: {hover}; }}"
        "QToolButton#skeldarSceneTabsButton {{ color: {text2}; padding: {p2} {p8}; border: none; }}"
        "QToolButton#skeldarSceneTabsButton:hover {{ background: {hover}; color: {text}; }}"
    ).format(root=ROOT_NAME, p2=px(2), p4=px(4), p6=px(6), p8=px(8), p10=px(10), **tokens)


def bar_class():
    """The Qt class, made on first use (no Qt at import)."""
    import maya_hubqt
    q = maya_hubqt.qt()
    QtCore, QtWidgets = q.QtCore, q.QtWidgets

    class TabBar(QtWidgets.QWidget):

        def __init__(self, actions, parent=None):
            super(TabBar, self).__init__(parent)
            self.setObjectName(ROOT_NAME)
            self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            self.actions = actions
            self.items = []
            self._filling = False
            row = QtWidgets.QHBoxLayout(self)
            row.setContentsMargins(4, 2, 4, 0)
            row.setSpacing(4)
            self.tabs = QtWidgets.QTabBar(self)
            self.tabs.setObjectName("skeldarSceneTabsTabs")
            self.tabs.setDocumentMode(True)
            self.tabs.setExpanding(False)
            self.tabs.setTabsClosable(True)
            self.tabs.setElideMode(QtCore.Qt.ElideMiddle)
            self.tabs.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.tabs.currentChanged.connect(self._current)
            self.tabs.tabCloseRequested.connect(self._close)
            self.tabs.customContextMenuRequested.connect(self._menu)
            self.tabs.installEventFilter(self)
            row.addWidget(self.tabs, 1)
            self.plus = self._button("+", "Open a scene in a new tab", self._plus_menu)
            self.more = self._button(u"\u22ee", "Scene tabs", self._more_menu)
            row.addWidget(self.plus)
            row.addWidget(self.more)
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(500)
            self.timer.timeout.connect(self.tick)
            self.timer.start()

        def _button(self, text, tip, opener):
            button = QtWidgets.QToolButton(self)
            button.setObjectName("skeldarSceneTabsButton")
            button.setText(text)
            button.setToolTip(tip)
            button.clicked.connect(lambda: opener(button))
            return button

        def populate(self, items):
            self._filling = True
            try:
                while self.tabs.count():
                    self.tabs.removeTab(0)
                for index, item in enumerate(items):
                    self.tabs.addTab(item["text"])
                    self.tabs.setTabToolTip(index, item["tip"])
                    if not item["closable"]:
                        #  the style decides the close button's side: clear both
                        for side in (QtWidgets.QTabBar.LeftSide, QtWidgets.QTabBar.RightSide):
                            if self.tabs.tabButton(index, side) is not None:
                                self.tabs.setTabButton(index, side, None)
                    if item["active"]:
                        self.tabs.setCurrentIndex(index)
                self.items = list(items)
            finally:
                self._filling = False

        def tick(self):
            """The stars kept current without repopulating (no flicker)."""
            fresh = self.actions.items()
            if [i["ns"] for i in fresh] != [i["ns"] for i in self.items]:
                self.populate(fresh)
                return
            for index, item in enumerate(fresh):
                if self.tabs.tabText(index) != item["text"]:
                    self.tabs.setTabText(index, item["text"])
            self.items = list(fresh)

        def _ns(self, index):
            return self.items[index]["ns"] if 0 <= index < len(self.items) else ""

        def _current(self, index):
            if not self._filling and self._ns(index):
                self.actions.switch(self._ns(index))

        def _close(self, index):
            if self._ns(index):
                self.actions.close(self._ns(index))

        def eventFilter(self, obj, event):
            if obj is self.tabs and event.type() == QtCore.QEvent.MouseButtonRelease \
                    and event.button() == QtCore.Qt.MiddleButton:
                point = event.position().toPoint() if hasattr(event, "position") else event.pos()
                namespace = self._ns(self.tabs.tabAt(point))
                if namespace:
                    self.actions.close(namespace)
                    return True
            return False

        def _menu(self, point):
            namespace = self._ns(self.tabs.tabAt(point))
            if not namespace:
                return
            a = self.actions
            maya_hubqt.run_menu(self.tabs, self.tabs.mapToGlobal(point), [
                ("Save", lambda: a.save(namespace)), ("Save As...", lambda: a.save_as(namespace)), None,
                ("Reload from disk", lambda: a.reload(namespace)),
                ("Show in Explorer", lambda: a.explore(namespace)), None,
                ("Close others", lambda: a.close_others(namespace))])

        def _plus_menu(self, button):
            a = self.actions
            rows = [("Open file...", a.open_file)]
            recent = a.recent()
            if recent:
                rows.append(None)
                rows.extend((os.path.basename(p), (lambda p=p: a.open_path(p))) for p in recent)
            rows.extend([None, ("Empty tab", a.empty_tab)])
            maya_hubqt.run_menu(button, button.mapToGlobal(button.rect().bottomLeft()), rows)

        def _more_menu(self, button):
            a = self.actions
            maya_hubqt.run_menu(button, button.mapToGlobal(button.rect().bottomLeft()),
                                [("Tabs off", a.tabs_off), ("Hide this bar", a.hide)])

    return TabBar


def _run(fn):
    try:
        message = fn()
    except Exception as exc:                                    # noqa: BLE001
        print(traceback.format_exc())
        message = "Scene Tabs: %s" % exc
    refresh()
    return say(message) if message else ""


class Actions(object):
    """What the bar's presses do in Maya."""

    def items(self):
        return records.bar_items(session.state(), cmds.file(q=True, sceneName=True) or "",
                                 bool(cmds.file(q=True, modified=True)))

    def switch(self, namespace):
        from . import switching
        return _run(lambda: switching.switch(namespace) and "Tab: %s" %
                    records.title(dict(records.tab(session.state(), namespace), modified=False)))

    def close(self, namespace):
        from . import opening
        return _run(lambda: opening.close_tab(namespace))

    def save(self, namespace):
        from . import saving
        return _run(lambda: saving.save_tab(namespace))

    def save_as(self, namespace):
        from . import saving
        return _run(lambda: saving.save_as(namespace))

    def reload(self, namespace):
        from . import opening
        return _run(lambda: opening.reload_tab(namespace))

    def explore(self, namespace):
        from . import opening
        return _run(lambda: opening.explore(namespace))

    def close_others(self, namespace):
        from . import opening
        return _run(lambda: opening.close_others(namespace))

    def open_file(self):
        found = cmds.fileDialog2(fileMode=1, caption="Open in a new tab",
                                 fileFilter="Maya Scenes (*.ma *.mb)") or []
        return self.open_path(found[0]) if found else ""

    def open_path(self, path):
        from . import opening
        return _run(lambda: opening.open_tab(path))

    def recent(self):
        if not cmds.optionVar(exists="RecentFilesList"):
            return []
        found = cmds.optionVar(q="RecentFilesList") or []
        return [p for p in reversed(found) if os.path.splitext(p)[1].lower() in records.FILE_TYPES][:10]

    def empty_tab(self):
        from . import opening
        return _run(opening.new_tab)

    def tabs_off(self):
        from . import opening
        return _run(opening.tabs_off)

    def hide(self):
        return _run(hide_bar)


def build():
    """The uiScript body: the bar inside the workspaceControl."""
    import maya_hubqt
    import maya_hubstyle
    q = maya_hubqt.qt()
    host = maya_hubqt.host_widget(CONTROL) if q is not None else None
    if host is None:
        return None
    for old in host.findChildren(q.QtWidgets.QWidget, ROOT_NAME):
        old.setParent(None)
        old.deleteLater()
    widget = bar_class()(Actions())
    scale = cmds.mayaDpiSetting(q=True, realScaleValue=True) or 1.0
    widget.setStyleSheet(stylesheet(maya_hubstyle.TOKENS, scale))
    host.layout().addWidget(widget)
    _state()["bar"] = widget
    refresh()
    from . import hooks
    hooks.install()
    return widget


def refresh():
    widget = _state()["bar"]
    if widget is None:
        return
    try:
        import maya_hubqt
        if not maya_hubqt.qt().shiboken.isValid(widget):
            _state()["bar"] = None
            return
        widget.populate(widget.actions.items())
    except RuntimeError:
        _state()["bar"] = None
```

- [ ] **Step 4: Run the tests**

Run: `$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenetabs_bar tests.test_scenetabs_records -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs_msg.txt" <<'EOF'
feat(scenetabs): the tab bar above the viewport

A QTabBar in the hub's colours in a workspaceControl docked at the top: a
tab per scene with its star, close, middle-click close, "+" (a file, a
recent one, an empty tab), the tab's menu and the bar's menu. Proven
offscreen on fake actions; docking is the animator's live check.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_scenetabs/bar.py tests/test_scenetabs_bar.py
git commit -F "$TEMP/scenetabs_msg.txt"
```

---

### Task 9: The bar shown from the hub; hotkey rows

**Files:**
- Modify: `SkeldarAnim/maya_hub.py` (`build()` and a new `_tabs_bar_soon`)
- Modify: `SkeldarAnim/maya_hotkeys.py` (a helper `_tabs` and three rows in the `COMMANDS` table)
- Modify: `tests/test_hotkeys.py` (class `OurRows`: the count, the `window.*` list, a new test)
- Modify: `tests/test_scenetabs_bar.py` (the hub test)

**Interfaces:**
- Consumes: `maya_scenetabs.bar.ensure_docked / show`, `maya_scenetabs.switching.cycle`, `maya_hotkeys.row(key)` (returns the table row: `(key, "SkeldarAnim.<category>", label, annotation, callable)`).

- [ ] **Step 1: Write the failing tests**

In `tests/test_hotkeys.py`, class `OurRows`:

1. `test_the_count`: add the comment line `#  + window.tabs, tabs.next / .previous (2026-10-15, Scene Tabs)` after the `tools.snapshot` comment and raise the number by 3 (63 -> 66 at the time of writing; if another session changed it since, add 3 to what is there).
2. `test_the_six_openers_and_the_toggle`: add `"window.tabs"` to the sorted list, between `"window.stash"` and `"window.tailbuilder"`.
3. Add:

```python
    def test_the_scene_tabs_rows(self):
        """Scene Tabs (2026-10-15): the bar's opener and next / previous tab."""
        self.assertEqual(maya_hotkeys.row("window.tabs")[4].args, ("maya_scenetabs.bar", "show"))
        found = maya_hotkeys.row("tabs.next")
        self.assertEqual(found[1], "SkeldarAnim.Scene Tabs")
        self.assertIs(found[4].func, maya_hotkeys._tabs)
        self.assertEqual(found[4].args, (1,))
        self.assertEqual(maya_hotkeys.row("tabs.previous")[4].args, (-1,))
```

Add to `tests/test_scenetabs_bar.py`:

```python
class HubShowsTheBar(unittest.TestCase):

    def test_the_hub_build_shows_the_bar_once_per_session(self):
        import inspect
        import maya_hub
        source = inspect.getsource(maya_hub.build)
        self.assertIn("_tabs_bar_soon()", source)
        helper = inspect.getsource(maya_hub._tabs_bar_soon)
        self.assertIn("skeldarSceneTabsBar", helper)
        self.assertIn("ensure_docked", helper)
```

- [ ] **Step 2: Run them to see them fail**

Run: `$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenetabs_bar tests.test_hotkeys -v`
Expected: `test_the_count`, `test_the_six_openers_and_the_toggle`, `test_the_scene_tabs_rows` and `test_the_hub_build_shows_the_bar_once_per_session` FAIL.

- [ ] **Step 3: The hub shows the bar**

In `SkeldarAnim/maya_hub.py`, in `build()`, right after `_register_pending_startup()`:

```python
    _tabs_bar_soon()
```

and add, after `build()`:

```python
TABS_BAR_VAR = "skeldarSceneTabsBar"


def _tabs_bar_soon():
    """The scene tabs bar above the viewport (2026-10-15), shown with the hub
    unless hidden from its own menu (optionVar 0). Deferred and guarded: a bar
    that cannot be built never costs the hub."""
    if cmds.about(batch=True):
        return
    if cmds.optionVar(exists=TABS_BAR_VAR) and not cmds.optionVar(q=TABS_BAR_VAR):
        return

    def show_bar():
        try:
            from maya_scenetabs import bar
            bar.ensure_docked()
        except Exception:                                    # noqa: BLE001
            print("SkeldarAnim: the scene tabs bar could not be shown")
            print(traceback.format_exc())
    cmds.evalDeferred(show_bar, lowestPriority=True)
```

- [ ] **Step 4: The hotkey rows**

In `SkeldarAnim/maya_hotkeys.py`, next to `_camshake` add:

```python
def _tabs(step):
    """The next / previous scene tab (2026-10-15)."""
    from maya_scenetabs import switching
    return _report(switching.cycle(step))
```

and in the `COMMANDS` table, after the `("camshake.apply", ...)` row:

```python
    ("window.tabs", "Windows", "Scene Tabs",
     "Show the scene tabs bar above the viewport: several scenes in one Maya",
     partial(_show, "maya_scenetabs.bar", "show")),
    ("tabs.next", "Scene Tabs", "Next tab",
     "Switch to the next scene tab",
     partial(_tabs, 1)),
    ("tabs.previous", "Scene Tabs", "Previous tab",
     "Switch to the previous scene tab",
     partial(_tabs, -1)),
```

- [ ] **Step 5: Run the whole unit suite**

Run: `$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
Expected: `OK` (about a minute). A failure in a test of another session's area that also fails on `git stash`-free HEAD before this task is not this task's; report it, do not fix it.

- [ ] **Step 6: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs_msg.txt" <<'EOF'
feat(scenetabs): the hub shows the bar; hotkey rows

The hub's build shows the bar once per session unless it was hidden from
its menu; rows window.tabs, tabs.next and tabs.previous (not bound by
default: Ctrl+Tab is checked in a GUI first).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_hub.py SkeldarAnim/maya_hotkeys.py tests/test_scenetabs_bar.py tests/test_hotkeys.py
git commit -F "$TEMP/scenetabs_msg.txt"
```

---

### Task 10: The proof together, CLAUDE.md, the animator's checklist

**Files:**
- Modify: `CLAUDE.md` (a section after "## Physical stop ..." chain - append at the end of the file)

- [ ] **Step 1: Run every verify phase and every unit test**

Run:
```
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_scene_tabs.py all
$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .
```
Expected: `0 of 127 gates failed`; unit tests `OK`. Record both numbers for CLAUDE.md.

- [ ] **Step 2: Write the CLAUDE.md section**

Append to `CLAUDE.md`:

```markdown
## Scene tabs: several scenes in one Maya, switched like browser tabs (2026-10-15)

The animator: «Возможно ли в maya сделать вкладки как в браузере что бы открывать разные сцены а не запускать
сразу несколько программ?» - then the references route: «мы нажимаем на вкладку и все объекты которые она
референсит скрываются и деактивируются, изменяется найтройки вюпорта, открываются старые окна и показываются
новые». Asked: tabs are for all three of working on several scenes, carrying things between them and looking
at a scene beside the work; approach A (imports, not references); one shared undo history; the bar above the
viewport; each tab its own whole layout. Spec `docs/superpowers/specs/2026-10-15-scene-tabs-design.md` (read
its planning addendum), plan `docs/superpowers/plans/2026-10-15-scene-tabs-stage1.md`. Stage 2 (the plugin
seeing only the active tab) is `2026-10-15-scene-tabs-plugin-scope-design.md` and is NOT built yet: until it
is, the plugin's tools see every tab's characters.

- **A tab** is a `.ma` / `.mb` imported with `preserveReferences=True, executeScriptNodes=False` into
  `tab_<stem>`; the session is a `network` node `skeldarSceneTabs` (JSON) and the scene is named
  `<userAppDir>/SkeldarTabs/session_<stamp>.ma` (never written by a Save; autosave writes it, and opening it
  restores the tabs). One scene open is ordinary Maya; the second converts it into tab 1 (1 ms, by UUID).
- **Switching** records the tab being left (modified flag, unit, ranges, frame, selection, views, layout) and
  hides it (`lodVisibility`, `hiddenInOutliner`), then shows the new one - ONE undo chunk, so Ctrl+Z past a
  switch brings the tab back before undoing its step.
- **Saving** lifts the tab into the root namespace by UUID, cuts its layer root free (written as
  `BaseAnimation`), writes its ranges into its configuration node, exports to a temp file and replaces the
  tab's file; refuses by name on a root-namespace clash; asks when the file changed on disk.
- **Layers**: the session owns the root `skeldarTabsLayerRoot` (trap 248).
- **Maya's own Save / Open / New** are redirected while two or more tabs are open (the check callbacks), an
  autosave passes; Save prints Maya's «File operation cancelled by user supplied callback» and then «Saved ...».
- **The bar** (`maya_scenetabs/bar.py`) is a QTabBar in a workspaceControl docked at the top, shown by the
  hub's build (optionVar `skeldarSceneTabsBar`); rows `window.tabs`, `tabs.next`, `tabs.previous`.

Proof: `docs/superpowers/plans/verify_scene_tabs.py` **<N> of <N>** in mayapy standalone (phases session,
layers_alone, convert, layers, open_close, switch, save, hooks, restore); <M> unit tests. **The animator's live
checks** (none of these can be proven headless): the bar docked above the viewport; per-tab workspaces and how
long a switch takes with them; whether a hidden tab still costs the viewport anything (if it does, the plan's
fallback is the `frozen` evaluator); the quit dialog; Ctrl+Tab free for `tabs.next`.

248. **Maya remembers its root animation layer internally, and does not promote another.** Closing the tab
     whose `BaseAnimation` was the scene's root deleted every other tab's layers with it; with the root gone
     and layers left, `animLayer -q -root` answered None and the next new layer crashed mayapy (measured
     2026-10-15). A layer's name and connections do not make it the root. Keep one root that never goes while
     anything else hangs below it.
249. **An import runs the file's open-type script nodes** unless `executeScriptNodes=False` (measured) - the
     vaccine malware's road into a scene that only imported a file.
250. **`animLayer -e -parent` rebuilds the layer's blend nodes in the ROOT namespace**, whatever namespace is
     current, and a save's rename of a layer rebuilds some under names of Maya's own (`hero_rotate_Layer2` came
     back `Layer10`). Anything that groups nodes by namespace must bring a layer's blend nodes home after it
     re-parents a layer (`animLayer -q -blendNodes` finds them), and never re-parent to restore a connection it
     cut - put back the exact connections.
251. **Renaming a reference node by hand breaks it**: `referenceQuery -namespace` then raises «Cannot find the
     associated namespace», and a reference's namespace moved and moved back leaves its node renamed in the
     root. Find a reference by its namespace, remove it by its node (`file -removeReference -referenceNode`): a
     path is ambiguous between two copies of one file (`file.ma{1}`).
252. **Maya imports a file's configuration node only when the root namespace holds none.** In a tab (whose
     configuration node sits in the tab) every import brings one, and in the saved file it runs after the tab's
     and wins. Export exactly one.
```

Fill `<N>` and `<M>` with the numbers from Step 1. The trap numbers 248-252 were free when this plan was written (CLAUDE.md ended at 247); if another session has taken them since, use the next free ones and fix the section's own references to them.

- [ ] **Step 3: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs_msg.txt" <<'EOF'
docs(scenetabs): CLAUDE.md section, traps 248-249, the live checklist

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add CLAUDE.md
git commit -F "$TEMP/scenetabs_msg.txt"
```

- [ ] **Step 4: Hand over**

Do not push, do not build, do not install into the animator's Maya. Go on to stage 2 (`docs/superpowers/plans/2026-10-15-scene-tabs-stage2.md`) before anything ships: stage 1 alone breaks the plugin's own creations inside a tab (see the note under the plan's header). Report to the animator when stage 2 is done too: the commits, the verify and unit-test numbers, and the live checklist from the CLAUDE.md section - the bar, layouts, hidden-tab cost, quit dialog, Ctrl+Tab.
