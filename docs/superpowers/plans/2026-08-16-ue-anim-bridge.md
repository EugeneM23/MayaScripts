# UE → Maya Animation Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Maya window that lists every `AnimSequence` in the running Unreal editor's project, filters it by name, and imports the selected one into the scene as its own keyed skeleton.

**Architecture:** Maya talks to the live editor over Epic's Python Remote Execution (UDP discovery + TCP command). The editor answers by writing JSON to a temp file whose path Maya chose, and by exporting the picked animation to FBX; Maya then imports that FBX into a fresh namespace. The pure halves — UE script text, reply parsing, search, namespace naming, engine discovery — hold all the fiddly logic and are tested with neither Maya nor Unreal running.

**Tech Stack:** Python 3 (Maya 2027's `mayapy`), `maya.cmds`, `maya.mel` (FBX plugin), Epic's `remote_execution.py` loaded from the engine install, `unittest`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-16-ue-anim-bridge-design.md`.
- Package `maya_uebridge/`. `uelink.py`, `uescripts.py`, `records.py` import **stdlib only** — no `maya.cmds`, no `unreal`. A subprocess test enforces it.
- `remote_execution.py` is **loaded from the engine install, never copied into this repo**.
- `__init__.py` resolves the entry point through `__getattr__`, so importing the package does not drag `maya.cmds` in.
- Every UE-side script embeds paths through `json.dumps`, never string concatenation.
- `automated=True` on every `AssetExportTask` — a modal dialog hangs the editor.
- The scene's frame rate is never changed. A mismatch is reported, not fixed.
- Every UI callback routes exceptions to the status line (`CLAUDE.md` trap 20).
- Tests run with `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`.
- Engine on this machine: `C:\!!!Work\Perforce`. Project: `C:\!!!Work\Perforce\Atone\Atone.uproject`.

---

### Task 1: Spike — confirm the live UE API before writing any module

**Blocked on:** `bRemoteExecution=True` in
`C:\!!!Work\Perforce\Atone\Saved\Config\WindowsEditor\Engine.ini` plus one editor
restart. Nothing else in this plan is blocked; Tasks 2–6 proceed without it.

**Files:**
- Create (scratchpad, not committed): `spike_ue.py`

**Interfaces:**
- Produces: confirmed facts recorded in the spec's risk section — the exact
  `FbxExportOption` field names on 5.8, whether `AnimSequenceExporterFBX` needs a
  preview mesh, the asset-tag keys carrying frame count and skeleton.

- [ ] **Step 1: Enable remote execution**

Append to `C:\!!!Work\Perforce\Atone\Saved\Config\WindowsEditor\Engine.ini`:

```ini
[/Script/PythonScriptPlugin.PythonScriptPluginSettings]
bRemoteExecution=True
```

This file is local user config, not under Perforce. Restart the editor.

- [ ] **Step 2: Confirm the listener is up**

```bash
powershell -c "Get-NetUDPEndpoint -LocalPort 6766"
```
Expected: one endpoint owned by the `UnrealEditor` process. Empty means the
setting did not take.

- [ ] **Step 3: Connect from mayapy and print the project path**

Load Epic's client from `C:\!!!Work\Perforce\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python\remote_execution.py`,
`start()`, poll `remote_nodes` until non-empty, `open_command_connection(node)`,
then `run_command` with `unreal.Paths.get_project_file_path()`.
Expected: the Atone uproject path.

- [ ] **Step 4: List one page of AnimSequence assets and dump the available tags**

Run an Asset Registry query and print, for the first asset found, every tag key
and value. Record which keys carry frame count, sequence length and skeleton —
these names differ across engine versions and must not be guessed.

- [ ] **Step 5: Export one animation to FBX**

Drive `AssetExportTask` + `AnimSequenceExporterFBX` with `automated=True` into
the temp folder. Record the exact `FbxExportOption` attribute names that exist on
5.8 and whether export succeeds on a skeleton with no preview mesh.

- [ ] **Step 6: Import that FBX into Maya by hand and confirm the keys arrived**

Through the existing `:7001` bridge. Confirm joint count and key range.

- [ ] **Step 7: Update the spec's risk section with what was measured**

```bash
git add docs/superpowers/specs/2026-08-16-ue-anim-bridge-design.md
git commit -F <message file>
```

---

### Task 2: `records.py` — the pure record model

**Files:**
- Create: `maya_uebridge/__init__.py`
- Create: `maya_uebridge/records.py`
- Create: `tests/test_uebridge_records.py`

**Interfaces:**
- Produces:
  - `AnimRecord` — namedtuple `(name, package, skeleton, frames, length, fps)`
  - `parse_payload(payload: dict) -> list[AnimRecord]`
  - `filter_records(records, query: str) -> list[AnimRecord]`
  - `namespace_for(asset_name: str, taken: set) -> str`
  - `format_row(record: AnimRecord) -> str`

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from maya_uebridge import records


class ParsePayload(unittest.TestCase):
    def test_reads_the_fields_it_needs(self):
        payload = {"assets": [{"name": "A_Jump", "package": "/Game/Anim/A_Jump",
                               "skeleton": "SK_Manny", "frames": 45,
                               "length": 1.5, "fps": 30.0}]}
        (rec,) = records.parse_payload(payload)
        self.assertEqual(rec.name, "A_Jump")
        self.assertEqual(rec.frames, 45)

    def test_survives_missing_tags(self):
        """UE returns no frame count for some assets; that must not lose the row."""
        payload = {"assets": [{"name": "A_Jump", "package": "/Game/Anim/A_Jump"}]}
        (rec,) = records.parse_payload(payload)
        self.assertIsNone(rec.frames)
        self.assertEqual(rec.skeleton, "")


class Filtering(unittest.TestCase):
    def setUp(self):
        self.recs = records.parse_payload({"assets": [
            {"name": "A_Jump_Start", "package": "/Game/Manny/A_Jump_Start"},
            {"name": "A_Walk_Fwd", "package": "/Game/Manny/A_Walk_Fwd"},
            {"name": "A_Idle", "package": "/Game/Enemy/A_Idle"}]})

    def test_empty_query_keeps_everything(self):
        self.assertEqual(len(records.filter_records(self.recs, "")), 3)

    def test_matches_case_insensitively(self):
        got = records.filter_records(self.recs, "jump")
        self.assertEqual([r.name for r in got], ["A_Jump_Start"])

    def test_matches_on_the_path_too(self):
        got = records.filter_records(self.recs, "enemy")
        self.assertEqual([r.name for r in got], ["A_Idle"])

    def test_every_term_must_match(self):
        """Typing two words narrows instead of widening."""
        got = records.filter_records(self.recs, "manny walk")
        self.assertEqual([r.name for r in got], ["A_Walk_Fwd"])


class Namespaces(unittest.TestCase):
    def test_uses_the_asset_name(self):
        self.assertEqual(records.namespace_for("A_Jump", set()), "A_Jump")

    def test_strips_characters_maya_rejects(self):
        self.assertEqual(records.namespace_for("A Jump-01.v2", set()), "A_Jump_01_v2")

    def test_prefixes_a_leading_digit(self):
        self.assertEqual(records.namespace_for("01_Jump", set()), "_01_Jump")

    def test_uniquifies_against_what_exists(self):
        self.assertEqual(records.namespace_for("A_Jump", {"A_Jump", "A_Jump1"}),
                         "A_Jump2")


class Purity(unittest.TestCase):
    def test_imports_without_maya(self):
        """records/uescripts/uelink must not drag maya.cmds in."""
        import subprocess, sys, os
        code = ("import sys; sys.path.insert(0, %r);"
                "import maya_uebridge.records, maya_uebridge.uescripts, maya_uebridge.uelink;"
                "assert 'maya.cmds' not in sys.modules;"
                "assert 'maya_uebridge.window' not in sys.modules;"
                "print('clean')" % os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertIn("clean", out.stdout, out.stderr)
```

- [ ] **Step 2: Run to verify they fail**

```bash
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_records -v
```
Expected: `ModuleNotFoundError: No module named 'maya_uebridge'`.

- [ ] **Step 3: Write `__init__.py` with lazy resolution**

Mirror `maya_overrig/__init__.py`: `__getattr__` resolves `show_window` by
importing `.window` only when asked, so `import maya_uebridge` stays Maya-free.

- [ ] **Step 4: Implement `records.py`**

`parse_payload` reads with `.get` defaults so a missing tag yields `None`/`""`
rather than dropping the row. `filter_records` splits the query on whitespace and
requires every term to appear in `name + package`, lowercased. `namespace_for`
maps every character outside `[A-Za-z0-9_]` to `_`, prefixes `_` if the first
character is a digit, then appends the lowest integer that clears `taken`.

- [ ] **Step 5: Run the tests**

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add maya_uebridge/__init__.py maya_uebridge/records.py tests/test_uebridge_records.py
git commit -F <message file>
```

---

### Task 3: `uescripts.py` — the UE-side source text

**Files:**
- Create: `maya_uebridge/uescripts.py`
- Create: `tests/test_uebridge_scripts.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `list_script(out_path: str, package_path: str = "/Game") -> str`
  - `export_script(out_path: str, package: str, fbx_path: str) -> str`
  - `MARKER: str` — printed by both scripts on success.

- [ ] **Step 1: Write the failing tests**

```python
import json
import unittest
from maya_uebridge import uescripts


class Embedding(unittest.TestCase):
    def test_windows_paths_survive_embedding(self):
        r"""A raw C:\temp\x.json would make \t a tab inside the generated source."""
        src = uescripts.list_script(r"C:\temp\new\anim.json")
        self.assertIn(json.dumps(r"C:\temp\new\anim.json"), src)
        self.assertNotIn(r"'C:\temp\new\anim.json'", src)

    def test_quotes_in_an_asset_name_cannot_break_out(self):
        src = uescripts.export_script("/tmp/o.json", "/Game/A'; import os; x='", "/tmp/a.fbx")
        compile(src, "<gen>", "exec")

    def test_both_scripts_compile(self):
        compile(uescripts.list_script("/tmp/o.json"), "<gen>", "exec")
        compile(uescripts.export_script("/tmp/o.json", "/Game/A", "/tmp/a.fbx"), "<gen>", "exec")


class Contract(unittest.TestCase):
    def test_list_script_checks_the_registry_is_done_scanning(self):
        self.assertIn("is_loading_assets", uescripts.list_script("/tmp/o.json"))

    def test_export_runs_unattended(self):
        """A modal dialog with nobody to click it hangs the editor."""
        src = uescripts.export_script("/tmp/o.json", "/Game/A", "/tmp/a.fbx")
        self.assertIn("automated = True", src)
        self.assertIn("prompt = False", src)

    def test_scripts_write_their_reply_to_the_file_we_named(self):
        src = uescripts.list_script("/tmp/out.json")
        self.assertIn(json.dumps("/tmp/out.json"), src)
        self.assertIn("json.dump", src)

    def test_scripts_report_their_own_failures_into_the_reply(self):
        """A traceback must reach the reply file, not vanish into the editor log."""
        for src in (uescripts.list_script("/tmp/o.json"),
                    uescripts.export_script("/tmp/o.json", "/Game/A", "/tmp/a.fbx")):
            self.assertIn("except Exception", src)
            self.assertIn("traceback", src)
```

- [ ] **Step 2: Run to verify they fail**

Expected: `ImportError: cannot import name 'uescripts'`.

- [ ] **Step 3: Implement `uescripts.py`**

Both scripts follow one shape: build a `result` dict, wrap the body in
`try/except Exception` writing `traceback.format_exc()` into `result["error"]`,
`json.dump` to the path in a `finally`, print `MARKER`. Parameters are
interpolated with `json.dumps` only.

The listing body queries `unreal.AssetRegistryHelpers.get_asset_registry()`,
returns early with `scanning: True` if `is_loading_assets()`, builds an
`unreal.ARFilter` on `AnimSequence` (5.1+ `class_paths` with
`unreal.TopLevelAssetPath`, falling back to `class_names`), and reads per-asset
tags without loading anything.

The export body `unreal.load_asset`s the package, fills an `AssetExportTask`
(`automated = True`, `prompt = False`, `replace_identical = True`), attaches
`AnimSequenceExporterFBX` and an `FbxExportOption` set to bones-only, and runs
`unreal.Exporter.run_asset_export_task`.

- [ ] **Step 4: Run the tests**

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/uescripts.py tests/test_uebridge_scripts.py
git commit -F <message file>
```

---

### Task 4: `uelink.py` — finding the engine and running Python in it

**Files:**
- Create: `maya_uebridge/uelink.py`
- Create: `tests/test_uebridge_link.py`

**Interfaces:**
- Consumes: `uescripts.MARKER`.
- Produces:
  - `REMOTE_EXEC_RELPATH: str`
  - `pick_engine_root(candidates: list, exists: callable) -> str | None`
  - `find_engine_root(override=None) -> str | None`
  - `UeLink(engine_root=None, timeout=8.0)` — context manager with
    `run(source) -> dict` returning `{"success": bool, "output": str}`
  - `run_script(source, out_path, engine_root=None, timeout=8.0) -> dict` —
    connects, runs, reads the JSON reply, closes
  - `NO_ENGINE_MESSAGE`, `NO_EDITOR_MESSAGE`

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from maya_uebridge import uelink


class EngineDiscovery(unittest.TestCase):
    def test_picks_the_first_candidate_that_has_the_client(self):
        present = {r"C:\Src\Engine\Plugins\Experimental\PythonScriptPlugin"
                   r"\Content\Python\remote_execution.py"}
        got = uelink.pick_engine_root([r"C:\Nope", r"C:\Src"], lambda p: p in present)
        self.assertEqual(got, r"C:\Src")

    def test_returns_none_when_nothing_matches(self):
        self.assertIsNone(uelink.pick_engine_root([r"C:\Nope"], lambda p: False))

    def test_an_override_is_tried_first(self):
        """A user-set engine path must beat whatever the registry says."""
        seen = []
        uelink.pick_engine_root([r"C:\Override", r"C:\Registry"],
                                lambda p: seen.append(p) or False)
        self.assertTrue(seen[0].startswith(r"C:\Override"))


class Messages(unittest.TestCase):
    def test_the_no_editor_message_says_what_to_do(self):
        """The likeliest cause is the setting being off, so name it."""
        self.assertIn("Remote Execution", uelink.NO_EDITOR_MESSAGE)
        self.assertIn("restart", uelink.NO_EDITOR_MESSAGE.lower())
```

- [ ] **Step 2: Run to verify they fail**

Expected: `ImportError: cannot import name 'uelink'`.

- [ ] **Step 3: Implement `uelink.py`**

`pick_engine_root` joins each candidate with `REMOTE_EXEC_RELPATH` and returns
the first whose path satisfies `exists`. `find_engine_root` assembles candidates
— explicit override, then `HKCU\Software\Epic Games\Unreal Engine\Builds` via
`winreg`, then `C:\Program Files\Epic Games\UE_*` via `glob` — and hands them to
`pick_engine_root(os.path.isfile)`.

`UeLink` loads the client through `importlib.util.spec_from_file_location` under
a private module name, `start()`s it, polls `remote_nodes` until non-empty or
`timeout`, opens a command connection and runs with `MODE_EXEC_FILE`. `__exit__`
always `stop()`s.

`run_script` writes nothing itself: it runs the source, then reads the JSON the
editor wrote at `out_path`. A missing reply file means the script died before its
`finally`, so the raw editor output is surfaced as the error.

- [ ] **Step 4: Run the tests**

Expected: all pass, including the purity test from Task 2.

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/uelink.py tests/test_uebridge_link.py
git commit -F <message file>
```

---

### Task 5: `animimport.py` — the Maya side

**Files:**
- Create: `maya_uebridge/animimport.py`
- Create: `tests/test_uebridge_import.py`

**Interfaces:**
- Consumes: `records.namespace_for`.
- Produces:
  - `TIME_UNIT_TO_FPS: dict`
  - `scene_fps() -> float`
  - `fps_warning(clip_fps, scene_fps) -> str` — pure, `""` when they agree
  - `import_clip(fbx_path, namespace, set_timeline=True) -> dict` returning
    `{"namespace", "joints": int, "start": float, "end": float, "warning": str}`

- [ ] **Step 1: Write the failing tests**

`import_clip` needs a live Maya, so the unit tests cover the pure half; the real
proof is Task 7.

```python
import unittest
from maya_uebridge import animimport


class FpsPolicy(unittest.TestCase):
    def test_silent_when_they_agree(self):
        self.assertEqual(animimport.fps_warning(30.0, 30.0), "")

    def test_tolerates_float_noise(self):
        """29.97 from UE against 30 in the scene is not worth shouting about."""
        self.assertEqual(animimport.fps_warning(30.0, 30.000001), "")

    def test_names_both_rates_when_they_differ(self):
        msg = animimport.fps_warning(30.0, 24.0)
        self.assertIn("30", msg)
        self.assertIn("24", msg)

    def test_says_nothing_when_the_clip_rate_is_unknown(self):
        self.assertEqual(animimport.fps_warning(None, 24.0), "")


class SceneFps(unittest.TestCase):
    def test_knows_the_units_maya_reports(self):
        self.assertEqual(animimport.TIME_UNIT_TO_FPS["ntsc"], 30)
        self.assertEqual(animimport.TIME_UNIT_TO_FPS["film"], 24)
```

- [ ] **Step 2: Run to verify they fail**

Expected: `ImportError: cannot import name 'animimport'`.

- [ ] **Step 3: Implement `animimport.py`**

`import_clip` loads `fbxmaya` if needed, resets FBX import settings through
`mel.eval`, sets add-mode and leaves the scene frame rate alone, then calls
`cmds.file(..., i=True, type="FBX", namespace=ns, returnNewNodes=True)`. The
returned node list — not a scene scan — gives the joints and the anim curves,
and the curves give the key range. With `set_timeline` the range goes to
`playbackOptions`; the frame rate is never written.

- [ ] **Step 4: Run the tests**

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/animimport.py tests/test_uebridge_import.py
git commit -F <message file>
```

---

### Task 6: `window.py` — the window

**Files:**
- Create: `maya_uebridge/window.py`
- Modify: `maya_uebridge/__init__.py`
- Create: `tests/test_uebridge_window.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `show_window()`, plus the pure helpers `cache_path()` and
  `cache_payload(records) -> dict` / `records_from_cache(payload) -> list`.

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from maya_uebridge import records


class CacheRoundTrip(unittest.TestCase):
    def test_records_survive_a_save_and_load(self):
        from maya_uebridge import window
        recs = records.parse_payload({"assets": [
            {"name": "A_Jump", "package": "/Game/A_Jump", "frames": 45}]})
        again = window.records_from_cache(window.cache_payload(recs))
        self.assertEqual(again, recs)
```

- [ ] **Step 2: Run to verify it fails**

Expected: `ImportError: cannot import name 'window'`.

- [ ] **Step 3: Implement `window.py`**

A `cmds.window` holding: a project/status header with a Refresh button, a
`textField` with `textChangedCommand` filtering the cached list, a
`textScrollList` of `format_row` lines, a "set timeline to clip range" checkbox
defaulted on, and an Import button (double-click on a row does the same).

Refresh runs `uescripts.list_script` through `uelink.run_script`, stores
`parse_payload` output in module state and writes the cache under
`cmds.internalVar(userPrefDir=True)`. The window opens from the cache, so a
closed editor still shows a browsable list.

Import resolves the selected row to its record, exports through the editor into
`tempfile.gettempdir()/maya_uebridge/`, then calls `animimport.import_clip`.

Every callback goes through one `_run` wrapper that puts the exception text on
the status line instead of the Script Editor.

- [ ] **Step 4: Run the tests**

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/window.py maya_uebridge/__init__.py tests/test_uebridge_window.py
git commit -F <message file>
```

---

### Task 7: Live verification

**Files:**
- Create: `docs/superpowers/plans/verify_uebridge.py`

**Interfaces:**
- Consumes: the whole package.

- [ ] **Step 1: Write the verification script**

Sent through the `:7001` bridge, run against the live editor. It asserts, in
order: the engine root is found; a connection opens; the listing returns assets
and is not in the scanning state; the count matches a second independent count
taken inside the editor; a named animation exports to an FBX that exists on disk
and is non-empty; importing it creates joints in the expected namespace; the
imported key range equals the frame count UE reported; and importing the same
clip twice yields two distinct namespaces rather than a collision.

It must not mutate the user's scene beyond what it imports, and must delete its
own imported namespaces at the end. Per `CLAUDE.md`: never `cmds.undo()` inside a
bridge script.

- [ ] **Step 2: Run it against the live scene**

Expected: every check green. A red check is a real bug — unit tests in this
project have repeatedly passed while the scene was broken.

- [ ] **Step 3: Update `CLAUDE.md`**

Add a section describing the bridge, how to run it, and any trap the live run
exposed.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/verify_uebridge.py CLAUDE.md
git commit -F <message file>
```

---

## Self-Review

**Spec coverage:** transport (Task 4), engine discovery (Task 4), listing and
export scripts (Task 3), record model, search and namespace naming (Task 2),
FBX import and the fps policy (Task 5), window, cache and status-line error
routing (Task 6), unit tests (Tasks 2–6), live proof (Task 7), the four
hand-checked risks (Task 1).

**Placeholders:** none — every step names its file, its command and its expected
result.

**Type consistency:** `AnimRecord` fields are used identically in Tasks 2, 6 and
7; `parse_payload`/`filter_records`/`namespace_for`/`format_row` keep the names
declared in Task 2; `run_script` returns the same dict shape in Tasks 4, 6 and 7.

**Deviation from the spec:** the spec listed four modules; this plan splits the
pure record model out of `uescripts.py` into `records.py`, so that module holds
only UE source text. The spec's module table is updated in Task 7's commit.
