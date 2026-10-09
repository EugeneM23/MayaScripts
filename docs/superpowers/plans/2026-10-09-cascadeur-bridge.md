# Cascadeur bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A bridge window that lives inside Cascadeur (menu `SkeldarAnim.Bridge`) and moves skeletal animation between Unreal and Cascadeur: import a clip into a new scene tab, export the scene back to a uasset, and send the animation to Shared.

**Architecture:** A package `SkeldarAnim/skeldar_cascadeur/` loaded by Cascadeur's own action discovery (`settings.json` → `Python.Path` + `Scripts`). Pure modules (rules, prefs, shared, unreal, uasset_core, actions) are stdlib-only and take their ports as arguments, so they are tested without Cascadeur or Unreal. Only `cascade_io.py` imports `csc`. The Unreal side reuses `maya_uebridge.uelink`, `uescripts`, `records` unchanged. The Shared side reuses `maya_sharenet` and `maya_sharerecords` unchanged. The installer `SkeldarAnim_Cascadeur_Install.py` at the repo root unpacks the release and edits Cascadeur's `settings.json` (backup first, idempotent).

**Tech Stack:** Python 3.11 (Cascadeur's bundled interpreter with PySide6 6.x; mayapy for the repo's unit tests), stdlib `urllib`, `zipfile`, `json`; Unreal Python Remote Execution through `maya_uebridge.uelink`; Cascadeur `csc` API as documented in `resources/scripts/stubs/csc/*.pyi`.

## Global Constraints

- Pure modules import nothing outside the stdlib and the existing stdlib-only share/uebridge modules. `cascade_io.py` is the ONLY module that imports `csc` or `pycsc`.
- No module in `skeldar_cascadeur/` other than `bridge.py` defines a module-level function named `run` or `name` (Cascadeur's discovery treats any module with `run` as an action; see Task 9).
- Destructive file operations refuse when the target is not ours (installer: `Documents\SkeldarAnim` without our marker is refused; Task 10).
- Nothing is pushed and no release is published by this plan. Commits stay local on `feature/overrig-picker`; the animator decides the push (Task 13).
- Shared is tested on a TEST ntfy topic only, never `maya_sharenet.TOPIC`.
- The animator's own assets are never written. Live verification writes only the sandbox `/Game/__bridge_verify` and deletes it.
- Tests run with mayapy: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.<module> -v` from `C:\!!!Work\MayaScripts`. No system Python exists on this machine (the Microsoft Store stub hangs).
- Maya-free modules must not import `maya.cmds`; a subprocess test pins it (Task 1).

---

## File Structure

| Path | Responsibility | Task |
|---|---|---|
| `docs/superpowers/plans/probe_cascadeur.py` | live probe run inside Cascadeur (not shipped) | 0 |
| `docs/superpowers/plans/cascadeur_probe_results.md` | what the probe found (not shipped) | 0 |
| `SkeldarAnim/skeldar_cascadeur/__init__.py` | package marker, no imports | 1 |
| `SkeldarAnim/skeldar_cascadeur/rules.py` | pure refusals and status wording | 1 |
| `tests/test_cascadeur_rules.py` | rules tests + Maya-free purity test | 1 |
| `SkeldarAnim/maya_uebridge/uasset_core.py` | Maya-free read-only and staging helpers moved out of `uassetexport` | 2 |
| `SkeldarAnim/maya_uebridge/uassetexport.py` | imports the moved helpers under their old names | 2 |
| `tests/test_cascadeur_uasset_core.py` | tests for the moved helpers | 2 |
| `SkeldarAnim/skeldar_cascadeur/prefs.py` | author name and last target, JSON | 3 |
| `tests/test_cascadeur_prefs.py` | prefs tests | 3 |
| `SkeldarAnim/skeldar_cascadeur/shared.py` | zip, upload, publish records | 4 |
| `tests/test_cascadeur_shared.py` | shared tests with a fake net | 4 |
| `SkeldarAnim/skeldar_cascadeur/unreal.py` | list, export, reimport through uelink/uescripts | 5 |
| `tests/test_cascadeur_unreal.py` | unreal tests with fake run_script | 5 |
| `SkeldarAnim/skeldar_cascadeur/cascade_io.py` | the only `csc` module: import, export, roots, frames, fps | 6 |
| `tests/test_cascadeur_purity.py` | only cascade_io imports csc | 6 |
| `SkeldarAnim/skeldar_cascadeur/actions.py` | the three flows over injected ports | 7 |
| `tests/test_cascadeur_actions.py` | flows with fakes | 7 |
| `SkeldarAnim/skeldar_cascadeur/window.py` | PySide6 window, thin wiring | 8 |
| `tests/test_cascadeur_window.py` | offscreen smoke test | 8 |
| `SkeldarAnim/skeldar_cascadeur/bridge.py` | menu action `name`/`description`/`run`, wiring | 9 |
| `tests/test_cascadeur_discovery.py` | discovery test (`run` only in bridge.py) | 9 |
| `SkeldarAnim_Cascadeur_Install.py` | installer at repo root | 10 |
| `tests/test_cascadeur_installer.py` | installer tests (loads the file by path) | 10 |
| `SkeldarAnim/install.py` | payload gains `skeldar_cascadeur` | 11 |
| `tests/test_cascadeur_payload.py` | payload tests | 11 |
| `.github/workflows/build.yml` | the installer is a third release asset | 11 |
| `docs/superpowers/plans/verify_cascadeur_bridge.py` | live verify run inside Cascadeur | 12 |
| `docs/superpowers/plans/cascadeur_bridge_live.md` | live result record | 12 |

---

### Task 0: Live probe of the Cascadeur API (answers the spec's open items)

The stubs fix most signatures, but four facts only a running Cascadeur can answer: whether `settings.json` takes an absolute path (deferred to Task 12, it needs a restart), how to read the skeleton roots of the current scene, how to read fps and the animation frame count, and what `export_joints` writes. This task writes a probe, runs it in the animator's Cascadeur through the script server, and records the answers. It changes no repo code.

**Files:**
- Create: `docs/superpowers/plans/probe_cascadeur.py`
- Create: `docs/superpowers/plans/cascadeur_probe_results.md`

**Interfaces:**
- Consumes: Cascadeur running with `MCP.Start script server` started (animator's action); a UE clip exported to disk (Step 1).
- Produces: the recorded call shapes that Task 6 uses (`skeleton_roots`, `animation_frames`, `scene_fps`, `export_skeleton`, `import_clip_new_tab`).

- [ ] **Step 1: Export one probe clip from Unreal with mayapy (stdlib uelink)**

Write `C:\Users\MY PC\AppData\Local\Temp\claude\C-----Work-MayaScripts\f9e380b6-a79a-4b4b-b323-dde74f02825a\scratchpad\probe_export.py`:

```python
import os, sys
sys.path.insert(0, r"C:\!!!Work\MayaScripts\SkeldarAnim")
from maya_uebridge import uelink, uescripts, records

OUT = r"C:\Users\MY PC\AppData\Local\Temp\skeldar_cascade_probe"
os.makedirs(OUT, exist_ok=True)
listing = os.path.join(OUT, "list.json")
payload = uelink.run_script(uescripts.list_script(listing, "/Game"), listing)
recs = records.parse_payload(payload)
print("content_dir", payload.get("content_dir"))
print("clips", len(recs))
pick = next(r for r in recs if "Walk" in r.name) if any("Walk" in r.name for r in recs) else recs[0]
print("pick", pick.name, pick.package, pick.frames, pick.fps)
fbx = os.path.join(OUT, "probe_clip.fbx")
out = os.path.join(OUT, "export.json")
reply = uelink.run_script(uescripts.export_script(out, pick.package, fbx), out)
print("export", reply.get("ok"), os.path.isfile(fbx), os.path.getsize(fbx) if os.path.isfile(fbx) else 0)
```

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' 'C:\...\scratchpad\probe_export.py'`
Expected: `clips N` with N > 0, `export True True <size>`. If the editor is off, the output names it; ask the animator to enable Remote Execution and stop.

- [ ] **Step 2: Write the probe that runs inside Cascadeur**

Write `docs/superpowers/plans/probe_cascadeur.py`. It is pasted through `POST /run` as one `code` string, so it must be self-contained and print everything it learns:

```python
import csc, csc.app, os, json, traceback
from pycsc.general import wrapping, fbx as pfbx

OUT = r"C:\Users\MY PC\AppData\Local\Temp\skeldar_cascade_probe"
FBX = os.path.join(OUT, "probe_clip.fbx")
RESULT = os.path.join(OUT, "probe_result.json")
result = {}

def attempt(key, fn):
    try:
        result[key] = repr(fn())
    except Exception:
        result[key] = "ERR " + traceback.format_exc(limit=2)

app = csc.app.get_application()
result["tools"] = attempt("tools", lambda: app.get_tools_manager().get_tool("FbxSceneLoader") is not None)
result["current_scene"] = attempt("current_scene", lambda: type(app.current_scene()).__name__)
result["wrapping_current"] = attempt("wrapping_current", lambda: type(wrapping.get_current_scene()).__name__)
result["wrapping_methods"] = attempt("wrapping_methods",
    lambda: [m for m in dir(wrapping.get_current_scene()) if not m.startswith("_")][:80])

# Import the probe clip into a NEW tab, the way the bridge will.
attempt("new_scene", lambda: wrapping.new_scene() is not None)
loader = app.get_tools_manager().get_tool("FbxSceneLoader").get_fbx_loader(app.current_scene())
attempt("import_scene", lambda: loader.import_scene(FBX.replace("\\", "/")))

# Skeleton roots: try the domain scene's object query.
ws = wrapping.get_current_scene()
for label, fn in [
    ("domain_scene", lambda: ws.domain_scene()),
    ("roots_joint", lambda: [o.name for o in ws.domain_scene().get_scene_objects(only_roots=True, of_type="joint")]),
    ("roots_bone", lambda: [o.name for o in ws.domain_scene().get_scene_objects(only_roots=True, of_type="bone")]),
    ("roots_any", lambda: [o.name for o in ws.domain_scene().get_scene_objects(only_roots=True)][:20]),
    ("animation_size", lambda: ws.domain_scene().get_animation_size()),
    ("current_frame", lambda: ws.domain_scene().get_current_frame()),
]:
    attempt(label, fn)

# fps: look for any attribute that carries it on the loader or the scene.
attempt("loader_fps", lambda: getattr(loader, "fps", "absent"))
attempt("scene_fps_attrs", lambda: [a for a in dir(ws.domain_scene()) if "fps" in a.lower() or "frame" in a.lower()])

# Export back: bones only, and whole scene, into the probe folder.
attempt("export_joints", lambda: loader.export_joints(os.path.join(OUT, "probe_export_joints.fbx").replace("\\", "/")))
attempt("export_joints_exists", lambda: os.path.isfile(os.path.join(OUT, "probe_export_joints.fbx")))

with open(RESULT, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, ensure_ascii=False, sort_keys=True)
print("probe written", RESULT)
```

- [ ] **Step 3: Start the script server and check health (animator action if needed)**

Run: `Invoke-RestMethod http://127.0.0.1:8765/health`
Expected: `ok : True`. If it fails, ask the animator to choose `Scripts → MCP → Start script server` in Cascadeur, then retry. Do not kill any other process on the port.

- [ ] **Step 4: Run the probe through the script server**

Run (PowerShell, reading the probe file into the JSON body):

```powershell
$code = Get-Content -Raw -Encoding utf8 'C:\!!!Work\MayaScripts\docs\superpowers\plans\probe_cascadeur.py'
$body = @{ code = $code } | ConvertTo-Json -Depth 3
Invoke-RestMethod -Uri http://127.0.0.1:8765/run -Method Post -Body $body -ContentType 'application/json; charset=utf-8' -TimeoutSec 120
```

Expected: `ok : True` and `messages` with the probe's print. If the HTTP call times out (30 s server cap) but the script is running, wait and read the result file `probe_result.json`; do not run it again (it would import a second copy).

- [ ] **Step 5: Read the result file and record the answers**

Read `C:\Users\MY PC\AppData\Local\Temp\skeldar_cascade_probe\probe_result.json`. Write `docs/superpowers/plans/cascadeur_probe_results.md` with one line per key: the call that worked (or the ERR), and the decision for Task 6:
- `roots_*`: the working `of_type` value and the call chain for root joints. Task 6's `skeleton_roots()` uses exactly this chain.
- `animation_size` / `current_frame`: the working call for the frame count. Task 6's `animation_frames()` uses it.
- `loader_fps` / `scene_fps_attrs`: where fps can be read. If nothing reads it, Task 6's `scene_fps()` returns `None` and the fps warning is skipped (rules.fps_problem treats None as unknown).
- `export_joints`: whether it writes the file and whether the re-read joint names equal the import's.

- [ ] **Step 6: Commit the probe and its results**

```bash
git add docs/superpowers/plans/probe_cascadeur.py docs/superpowers/plans/cascadeur_probe_results.md
git commit -m "docs: Cascadeur API probe and its results"
```

---

### Task 1: Package skeleton and pure rules

**Files:**
- Create: `SkeldarAnim/skeldar_cascadeur/__init__.py`
- Create: `SkeldarAnim/skeldar_cascadeur/rules.py`
- Test: `tests/test_cascadeur_rules.py`

**Interfaces:**
- Consumes: nothing.
- Produces (used by Tasks 6, 7): `EXPECTED_FPS = 30.0`; `skeleton_problem(roots) -> str`; `export_refusal(package, uasset, uasset_exists) -> str`; `fps_problem(fps, expected=EXPECTED_FPS) -> str`; `frame_range_outward(start, end) -> (int, int)`; `clip_tab_name(name) -> str`; `join_status(parts) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cascadeur_rules.py`:

```python
"""Pure rules of the Cascadeur bridge. Neither Cascadeur nor Maya present."""

import os
import subprocess
import sys
import unittest

from skeldar_cascadeur import rules


class SkeletonProblem(unittest.TestCase):

    def test_one_root_is_fine(self):
        self.assertEqual(rules.skeleton_problem(["root"]), "")

    def test_no_root_is_refused(self):
        self.assertEqual(rules.skeleton_problem([]), rules.NO_SKELETON)

    def test_several_roots_are_refused_and_named(self):
        text = rules.skeleton_problem(["root", "Hips"])
        self.assertIn("2 skeletons", text)
        self.assertIn("Hips", text)
        self.assertIn("root", text)


class ExportRefusal(unittest.TestCase):

    def test_no_package_asks_for_a_target(self):
        self.assertEqual(rules.export_refusal("", "", False), rules.NO_TARGET)

    def test_missing_uasset_is_named(self):
        text = rules.export_refusal("/Game/A/B", "C:/P/Content/A/B.uasset", False)
        self.assertIn("C:/P/Content/A/B.uasset", text)

    def test_existing_uasset_passes(self):
        self.assertEqual(rules.export_refusal("/Game/A/B", "x", True), "")


class FpsProblem(unittest.TestCase):

    def test_thirty_is_fine(self):
        self.assertEqual(rules.fps_problem(30.0), "")

    def test_unknown_is_not_claimed(self):
        self.assertEqual(rules.fps_problem(None), "")

    def test_other_rate_is_named(self):
        text = rules.fps_problem(24.0)
        self.assertIn("24 fps", text)
        self.assertIn("30", text)


class FrameRangeOutward(unittest.TestCase):

    def test_whole_range_unchanged(self):
        self.assertEqual(rules.frame_range_outward(0, 45), (0, 45))

    def test_fraction_rounds_outward(self):
        self.assertEqual(rules.frame_range_outward(0.4, 44.2), (0, 45))


class TabNameAndJoin(unittest.TestCase):

    def test_blank_name_gets_a_default(self):
        self.assertEqual(rules.clip_tab_name("  "), "clip")

    def test_name_is_kept(self):
        self.assertEqual(rules.clip_tab_name("A_Jump"), "A_Jump")

    def test_join_drops_empty_parts(self):
        self.assertEqual(rules.join_status(["a", "", "b"]), "a  |  b")


class Purity(unittest.TestCase):

    def test_rules_import_nothing_outside_the_stdlib(self):
        plugin = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
        code = ("import sys; sys.path.insert(0, %r); "
                "import skeldar_cascadeur.rules; "
                "print('maya.cmds' in sys.modules, 'csc' in sys.modules, "
                "'PySide6' in sys.modules)") % plugin
        out = subprocess.check_output([sys.executable, "-c", code],
                                      cwd=plugin).decode().strip()
        self.assertEqual(out, "False False False")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_rules -v`
Expected: ImportError (no `skeldar_cascadeur`).

- [ ] **Step 3: Write the minimal implementation**

Create `SkeldarAnim/skeldar_cascadeur/__init__.py`:

```python
"""The SkeldarAnim bridge for Cascadeur. Imports nothing; each module says what it is."""
```

Create `SkeldarAnim/skeldar_cascadeur/rules.py`:

```python
"""The Cascadeur bridge's pure rules: what may run, and what the status says.

Stdlib only. Every refusal is a sentence that names what did not change.
"""

import math

EXPECTED_FPS = 30.0

NO_SKELETON = "the scene holds no skeleton - nothing to export"
SEVERAL_SKELETONS = ("the scene holds {0} skeletons ({1}) - keep one, "
                     "export refused")
NO_TARGET = ("no Unreal animation to write back to - select one in the "
             "list, or import a clip first")
NO_UASSET = "no uasset at {0} - nothing changed"


def skeleton_problem(roots):
    """Why an export must not run, or "". `roots` is the scene's root joints."""
    roots = list(roots or [])
    if not roots:
        return NO_SKELETON
    if len(roots) > 1:
        return SEVERAL_SKELETONS.format(len(roots), ", ".join(sorted(roots)))
    return ""


def export_refusal(package, uasset, uasset_exists):
    """Why the write-back must not run, or "". Pure: the disk is passed in."""
    if not package:
        return NO_TARGET
    if not uasset_exists:
        return NO_UASSET.format(uasset)
    return ""


def fps_problem(fps, expected=EXPECTED_FPS):
    """A warning when the scene's rate is not Unreal's, or "" (also when unknown)."""
    if fps is None:
        return ""
    if abs(float(fps) - float(expected)) < 1e-6:
        return ""
    return ("scene is {0:g} fps, Unreal's clip is {1:g} - UE resamples "
            "it".format(float(fps), float(expected)))


def frame_range_outward(start, end):
    """A range rounded outward to whole frames. A fractional end makes UE refuse
    the animation silently (trap 50); outward can only widen it."""
    return int(math.floor(start)), int(math.ceil(end))


def clip_tab_name(name):
    """The scene tab's name for an imported clip."""
    text = (name or "").strip()
    return text or "clip"


def join_status(parts):
    """One status line from its parts; empty parts are dropped."""
    return "  |  ".join(part for part in parts if part)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_rules -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/skeldar_cascadeur/__init__.py SkeldarAnim/skeldar_cascadeur/rules.py tests/test_cascadeur_rules.py
git commit -m "feat(cascadeur): package skeleton and pure bridge rules"
```

---

### Task 2: Move the Maya-free helpers out of uassetexport

**Files:**
- Create: `SkeldarAnim/maya_uebridge/uasset_core.py`
- Modify: `SkeldarAnim/maya_uebridge/uassetexport.py` (remove the moved definitions; import them)
- Test: `tests/test_cascadeur_uasset_core.py`; existing `tests/test_uebridge_uasset.py` must stay green.

**Interfaces:**
- Consumes: nothing.
- Produces: `uasset_core.LOST_CURVES`, `is_read_only(path)`, `clear_read_only(path) -> str`, `fbx_staging_path(name, folder)`, `readonly_note(cleared)`. `uassetexport` keeps the same public names by importing them.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cascadeur_uasset_core.py`:

```python
"""The Maya-free helpers moved out of uassetexport. Neither Maya nor Unreal."""

import os
import stat
import subprocess
import sys
import tempfile
import unittest

from maya_uebridge import uasset_core


class ReadOnly(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="core_ro_")
        self.path = os.path.join(self.folder, "AS_X.uasset")
        with open(self.path, "wb") as handle:
            handle.write(b"x")

    def tearDown(self):
        os.chmod(self.path, stat.S_IWRITE | stat.S_IREAD)
        os.remove(self.path)
        os.rmdir(self.folder)

    def test_writable_file_is_not_read_only(self):
        self.assertFalse(uasset_core.is_read_only(self.path))

    def test_missing_file_is_not_read_only(self):
        self.assertFalse(uasset_core.is_read_only(self.path + ".nope"))

    def test_clear_read_only_makes_it_writable(self):
        os.chmod(self.path, stat.S_IREAD)
        self.assertTrue(uasset_core.is_read_only(self.path))
        self.assertEqual(uasset_core.clear_read_only(self.path), "")
        self.assertFalse(uasset_core.is_read_only(self.path))


class Staging(unittest.TestCase):

    def test_staging_path_names_the_clip(self):
        path = uasset_core.fbx_staging_path("A_Jump", r"C:\tmp")
        self.assertTrue(path.endswith("A_Jump.uasset.fbx"))

    def test_readonly_note(self):
        self.assertEqual(uasset_core.readonly_note(True), "read-only cleared")
        self.assertEqual(uasset_core.readonly_note(False), "")

    def test_lost_curves_named(self):
        self.assertIn("Pose_0..9", uasset_core.LOST_CURVES)


class Purity(unittest.TestCase):

    def test_uasset_core_imports_no_maya(self):
        plugin = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
        code = ("import sys; sys.path.insert(0, %r); "
                "import maya_uebridge.uasset_core as u; "
                "print('maya.cmds' in sys.modules, 'unreal' in sys.modules)") % plugin
        out = subprocess.check_output([sys.executable, "-c", code],
                                      cwd=plugin).decode().strip()
        self.assertEqual(out, "False False")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_uasset_core -v`
Expected: ImportError (no `uasset_core`).

- [ ] **Step 3: Write the minimal implementation**

Create `SkeldarAnim/maya_uebridge/uasset_core.py`:

```python
"""The Maya-free part of the uasset road, shared with the Cascadeur bridge.

uassetexport keeps its Maya flow and imports these names from here, so the
Maya module's public names do not change. Stdlib only.
"""

import os
import stat

# What a replace-import throws away, named in the dialog. Measured on one
# real UE clip (trap 40): 135 such curves against 9 transform channels.
LOST_CURVES = "Pose_0..9, MoveData_*, DisableLegIK, RootMotionAdditiveInput"


def is_read_only(path):
    """True when the file exists and cannot be written to.

    `os.access(W_OK)` rather than the mode bits: it is what actually decides
    whether the editor's save will succeed.
    """
    return os.path.isfile(path) and not os.access(path, os.W_OK)


def clear_read_only(path):
    """Take the read-only flag off. Returns "" or the reason it failed."""
    try:
        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IWRITE | stat.S_IWUSR)
    except OSError as exc:
        return str(exc)
    if not os.access(path, os.W_OK):
        return "still not writable"
    return ""


def fbx_staging_path(name, folder):
    """Where the intermediate FBX goes. Named for what it is, so a leftover
    in the temp folder says which button wrote it."""
    return os.path.join(folder, "{0}.uasset.fbx".format(name))


def readonly_note(cleared):
    """What the status says about the flag. Pure."""
    return "read-only cleared" if cleared else ""
```

Edit `SkeldarAnim/maya_uebridge/uassetexport.py`:
1. Delete the definition of `LOST_CURVES` (the module-level string at its top, the block starting `# What a replace-import throws away` through `LOST_CURVES = "..."`) and replace it with an import.
2. Delete the function definitions `is_read_only`, `clear_read_only`, `fbx_staging_path`, `readonly_note`.
3. Add after the existing `from maya_uebridge import uescripts` line:

```python
from maya_uebridge.uasset_core import (LOST_CURVES, clear_read_only,
                                       fbx_staging_path, is_read_only,
                                       readonly_note)
```

Keep `import os` and `import stat` in uassetexport if other code there still uses them (`os.path` is used by `export_to_uasset`); remove `stat` only if it is no longer referenced (check with Grep for `stat.` in the file).

- [ ] **Step 4: Run both test modules to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_uasset_core tests.test_uebridge_uasset -v`
Expected: all OK (the existing uasset tests still see the same names through uassetexport).

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_uebridge/uasset_core.py SkeldarAnim/maya_uebridge/uassetexport.py tests/test_cascadeur_uasset_core.py
git commit -m "refactor(uebridge): move the Maya-free uasset helpers into uasset_core"
```

---

### Task 3: Prefs (author name and last target)

**Files:**
- Create: `SkeldarAnim/skeldar_cascadeur/prefs.py`
- Test: `tests/test_cascadeur_prefs.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `default_path(appdata=None) -> str`; `load(path) -> dict`; `save(path, data)`; `get(path, key, default="")`; `put(path, key, value)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cascadeur_prefs.py`:

```python
"""Prefs of the Cascadeur bridge: a JSON file it owns. Stdlib only."""

import os
import shutil
import tempfile
import unittest

from skeldar_cascadeur import prefs


class Prefs(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="prefs_")
        self.path = os.path.join(self.folder, "SkeldarAnim", "cascadeur.json")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_missing_file_reads_empty(self):
        self.assertEqual(prefs.load(self.path), {})
        self.assertEqual(prefs.get(self.path, "author", "fallback"), "fallback")

    def test_put_then_get_round_trips(self):
        prefs.put(self.path, "author", "Yevhen")
        self.assertEqual(prefs.get(self.path, "author"), "Yevhen")

    def test_put_keeps_other_keys(self):
        prefs.put(self.path, "author", "A")
        prefs.put(self.path, "target", "/Game/A/B")
        self.assertEqual(prefs.get(self.path, "author"), "A")
        self.assertEqual(prefs.get(self.path, "target"), "/Game/A/B")

    def test_a_broken_file_reads_empty_and_is_not_overwritten_by_get(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        self.assertEqual(prefs.load(self.path), {})
        self.assertEqual(prefs.get(self.path, "author", "d"), "d")

    def test_a_non_object_file_reads_empty(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("[1, 2]")
        self.assertEqual(prefs.load(self.path), {})

    def test_default_path_is_under_appdata(self):
        self.assertEqual(prefs.default_path(r"C:\Users\x\AppData\Roaming"),
                         os.path.join(r"C:\Users\x\AppData\Roaming",
                                      "SkeldarAnim", "cascadeur.json"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_prefs -v`
Expected: ImportError.

- [ ] **Step 3: Write the minimal implementation**

Create `SkeldarAnim/skeldar_cascadeur/prefs.py`:

```python
"""The Cascadeur bridge's own small settings: the author name for Shared and
the last Unreal target. A JSON file it owns; a broken file reads as empty and
is never rewritten by a read. Stdlib only.
"""

import json
import os


def default_path(appdata=None):
    """Where the prefs live: %APPDATA%\\SkeldarAnim\\cascadeur.json."""
    base = appdata or os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "SkeldarAnim", "cascadeur.json")


def load(path):
    """The stored dict, or {} when the file is missing, broken or not an object."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(path, data):
    """Write atomically: a temp file, then replace."""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
    os.replace(temp, path)


def get(path, key, default=""):
    """One stored value, or `default` when it is missing or of another type."""
    value = load(path).get(key, default)
    return value if isinstance(value, type(default)) else default


def put(path, key, value):
    """Store one value, keeping every other key."""
    data = load(path)
    data[key] = value
    save(path, data)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_prefs -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/skeldar_cascadeur/prefs.py tests/test_cascadeur_prefs.py
git commit -m "feat(cascadeur): prefs for the author name and the last target"
```

---

### Task 4: Send an animation to Shared

**Files:**
- Create: `SkeldarAnim/skeldar_cascadeur/shared.py`
- Test: `tests/test_cascadeur_shared.py`

**Interfaces:**
- Consumes: `maya_sharenet` (`publish(text)`, `upload_any(path, progress=None)`, `ShareError`), `maya_sharerecords` (`new_id()`, `make_record(...)`, `with_state(...)`, `encode(...)`, `MAX_ZIP`).
- Produces: `zip_fbx(path, name, folder=None) -> str`; `send(path, name, author, machine, net=None, now=None, progress=None) -> dict` (returns the ready record with `url` and `zip`; raises `ShareError` after publishing `failed`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_cascadeur_shared.py`:

```python
"""Shared sends from the Cascadeur bridge, with a fake net. No network."""

import os
import shutil
import tempfile
import unittest
import zipfile

from skeldar_cascadeur import shared
import maya_sharenet
import maya_sharerecords as records


class FakeNet(object):
    ShareError = maya_sharenet.ShareError

    def __init__(self, fail=False):
        self.published = []
        self.uploads = []
        self.fail = fail

    def publish(self, text, topic=None, base=None):
        self.published.append(records.parse(text) if False else text)
        return "id"

    def upload_any(self, path, progress=None):
        self.uploads.append(path)
        if self.fail:
            raise maya_sharenet.ShareError("temp.sh refused")
        return "https://temp.sh/abc/A_Jump.fbx.zip"


class Send(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="share_")
        self.fbx = os.path.join(self.folder, "A_Jump.fbx")
        with open(self.fbx, "wb") as handle:
            handle.write(b"FBX-DATA" * 10)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def states(self, net):
        import json
        return [json.loads(text)["state"] for text in net.published]

    def test_sends_sending_then_ready_with_url(self):
        net = FakeNet()
        ready = shared.send(self.fbx, "A_Jump.fbx", "Yevhen", "PC", net=net,
                            now=lambda: 1000)
        self.assertEqual(self.states(net), ["sending", "ready"])
        self.assertEqual(ready["url"], "https://temp.sh/abc/A_Jump.fbx.zip")
        self.assertEqual(ready["from"], "Yevhen")
        self.assertEqual(ready["kind"], "fbx")

    def test_the_zip_holds_the_file_under_its_name(self):
        net = FakeNet()
        shared.send(self.fbx, "A_Jump.fbx", "Y", "PC", net=net, now=lambda: 1)
        archive = net.uploads[0]
        # cleanup removes the zip after the upload; the test reads it from
        # the upload's own call instead: nothing to read after send returned.
        self.assertFalse(os.path.exists(archive))

    def test_zip_helper_keeps_the_name(self):
        archive = shared.zip_fbx(self.fbx, "A_Jump.fbx", folder=self.folder)
        try:
            with zipfile.ZipFile(archive) as zipped:
                self.assertEqual(zipped.namelist(), ["A_Jump.fbx"])
        finally:
            os.remove(archive)

    def test_failure_publishes_failed_and_raises(self):
        net = FakeNet(fail=True)
        with self.assertRaises(maya_sharenet.ShareError):
            shared.send(self.fbx, "A_Jump.fbx", "Y", "PC", net=net,
                        now=lambda: 1)
        self.assertEqual(self.states(net), ["sending", "failed"])


if __name__ == "__main__":
    unittest.main()
```

Note for the implementer: the `publish` fake stores raw text; `FakeNet.publish` line with `if False` is a placeholder-looking line that must be cleaned up. Replace the body of `FakeNet.publish` with `self.published.append(text)` and return `"id"` before running the test.

- [ ] **Step 2: Run it to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_shared -v`
Expected: ImportError (no `shared`).

- [ ] **Step 3: Write the minimal implementation**

Create `SkeldarAnim/skeldar_cascadeur/shared.py`:

```python
"""Send an animation FBX to everybody, the way Maya's Shared card sends a file:
zip it, announce it as `sending`, upload (temp.sh, then litterbox), announce
`ready` with the address. A failure announces `failed` and re-raises.

Stdlib plus the two share modules. No Maya, no Cascadeur.
"""

import os
import tempfile
import time
import zipfile

import maya_sharenet
import maya_sharerecords as records


def zip_fbx(path, name, folder=None):
    """A zip holding `path` under the member name `name`. The caller removes it."""
    handle, archive = tempfile.mkstemp(prefix="skeldar_cascade_", suffix=".zip",
                                       dir=folder)
    os.close(handle)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        out.write(path, name)
    return archive


def send(path, name, author, machine, net=None, now=None, progress=None):
    """Upload `path` as `name`; the ready record (with `url` and `zip`).

    `net` and `now` are injectable for the tests. Raises the net's ShareError
    after publishing `failed`, so the colleagues drop the row.
    """
    net = net or maya_sharenet
    clock = now or time.time
    rid = records.new_id()
    size = os.path.getsize(path)
    record = records.make_record("sending", rid, author, machine, name, size,
                                 int(clock()))
    net.publish(records.encode(record))
    archive = zip_fbx(path, name)
    try:
        zipped = os.path.getsize(archive)
        if zipped > records.MAX_ZIP:
            raise net.ShareError("the zip is {0} bytes, over the hosts' 1 GB"
                                 .format(zipped))
        url = net.upload_any(archive, progress=progress)
        ready = records.with_state(record, "ready", url=url, zip=zipped)
        net.publish(records.encode(ready))
        return ready
    except Exception:
        try:
            net.publish(records.encode(records.with_state(record, "failed")))
        except Exception:
            pass
        raise
    finally:
        if os.path.exists(archive):
            os.remove(archive)
```

Also fix the test's `FakeNet.publish` as described in the note under Step 1, and replace `test_the_zip_holds_the_file_under_its_name` with a test that asserts the uploaded archive path was passed and then removed (already the body) — keep it as written.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_shared -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/skeldar_cascadeur/shared.py tests/test_cascadeur_shared.py
git commit -m "feat(cascadeur): send an animation FBX to Shared"
```

---

### Task 5: The Unreal side without Maya

**Files:**
- Create: `SkeldarAnim/skeldar_cascadeur/unreal.py`
- Test: `tests/test_cascadeur_unreal.py`

**Interfaces:**
- Consumes: `maya_uebridge.uelink.run_script(source, out_path, engine_root=None, timeout=..., client=None, keep_reply=False, project=None)`; `maya_uebridge.uescripts` (`list_script`, `export_script`, `reimport_script`); `maya_uebridge.records` (`parse_payload`).
- Produces: `safe_name(name) -> str`; `list_clips(out_dir, project=None, run_script=None) -> (content_dir, [AnimRecord])`; `export_clip(record, out_dir, project=None, run_script=None) -> (fbx_path, payload)`; `reimport(package, fbx, out_dir, project=None, run_script=None) -> payload`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cascadeur_unreal.py`:

```python
"""The Unreal side of the Cascadeur bridge, with a fake run_script. No editor."""

import os
import shutil
import tempfile
import unittest

from skeldar_cascadeur import unreal
from maya_uebridge import records


class FakeRun(object):
    """Records each call; writes the FBX a real export would write."""

    def __init__(self, reply, write_fbx=False):
        self.reply = reply
        self.write_fbx = write_fbx
        self.calls = []

    def __call__(self, source, out_path, project=None, **kwargs):
        self.calls.append((source, out_path, project))
        if self.write_fbx and "export" in source.lower():
            fbx = source.split("_FBX = ", 1)[1].split("\n", 1)[0]
            with open(eval(fbx), "wb") as handle:
                handle.write(b"fbx")
        return self.reply


class Unreal(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="ue_")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_safe_name_keeps_letters_digits_and_underscore(self):
        self.assertEqual(unreal.safe_name("A Jump/Q"), "A_Jump_Q")
        self.assertEqual(unreal.safe_name(""), "clip")

    def test_list_returns_content_dir_and_records(self):
        run = FakeRun({"content_dir": "C:/P/Content",
                       "assets": [{"name": "A_Jump",
                                   "package": "/Game/Anim/A_Jump",
                                   "frames": 45, "fps": 30.0}]})
        content, recs = unreal.list_clips(self.folder, project="P", run_script=run)
        self.assertEqual(content, "C:/P/Content")
        self.assertEqual([r.name for r in recs], ["A_Jump"])
        self.assertEqual(run.calls[0][2], "P")

    def test_export_returns_the_fbx_path_and_payload(self):
        rec = records.AnimRecord(name="A_Jump", package="/Game/Anim/A_Jump",
                                 skeleton="", frames=45, length=1.5, fps=30.0,
                                 source="unreal", path="", clip="", fmt="")
        run = FakeRun({"ok": True, "error": ""}, write_fbx=True)
        fbx, payload = unreal.export_clip(rec, self.folder, run_script=run)
        self.assertTrue(fbx.endswith("A_Jump.fbx"))
        self.assertTrue(os.path.isfile(fbx))
        self.assertTrue(payload["ok"])

    def test_reimport_passes_the_package_and_fbx(self):
        run = FakeRun({"saved": True, "frames": 45, "error": ""})
        payload = unreal.reimport("/Game/Anim/A_Jump", r"C:\x\A_Jump.fbx",
                                  self.folder, run_script=run)
        self.assertTrue(payload["saved"])
        self.assertIn("/Game/Anim/A_Jump", run.calls[0][0])


if __name__ == "__main__":
    unittest.main()
```

Note for the implementer: `records.AnimRecord` is the record type returned by `records.parse_payload`; check its constructor fields in `SkeldarAnim/maya_uebridge/records.py` (the `AnimRecord` definition) and make the test construct it with exactly those fields (the fields used are: name, package, skeleton, frames, length, fps, source, path, clip, fmt). If the class is a namedtuple with other fields, pass them. Also, the `FakeRun` export branch parses the `_FBX = ...` line of the generated export source: verify that line's exact form in `uescripts._EXPORT_HEAD` (it is `_FBX = %(fbx_path)s` with a JSON string) and adjust the parsing to `json.loads` if needed.

- [ ] **Step 2: Run it to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_unreal -v`
Expected: ImportError.

- [ ] **Step 3: Write the minimal implementation**

Create `SkeldarAnim/skeldar_cascadeur/unreal.py`:

```python
"""The Unreal side of the Cascadeur bridge: list, export and reimport.

Reuses maya_uebridge's stdlib modules unchanged. No Maya, no Cascadeur.
`run_script` is injectable (tests); the default is uelink.run_script.
"""

import json
import os
import re

from maya_uebridge import records
from maya_uebridge import uelink
from maya_uebridge import uescripts

NO_FBX = "the editor did not write {0} - nothing imported"


def _runner(run_script):
    return run_script or uelink.run_script


def safe_name(name):
    """A file name for the clip: letters, digits, underscore and dash only."""
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", (name or "").strip()).strip("_")
    return text or "clip"


def list_clips(out_dir, project=None, run_script=None):
    """(content_dir, records) of every AnimSequence under /Game."""
    out = os.path.join(out_dir, "uelist.json")
    payload = _runner(run_script)(uescripts.list_script(out, "/Game"), out,
                                  project=project)
    return payload.get("content_dir", ""), records.parse_payload(payload)


def export_clip(record, out_dir, project=None, run_script=None):
    """The clip as a bones-only FBX in `out_dir`: (fbx_path, payload)."""
    fbx = os.path.join(out_dir, safe_name(record.name) + ".fbx")
    out = os.path.join(out_dir, "uexport_" + safe_name(record.name) + ".json")
    payload = _runner(run_script)(
        uescripts.export_script(out, record.package, fbx), out, project=project)
    if not os.path.isfile(fbx):
        raise uelink.UeBridgeError(NO_FBX.format(os.path.basename(fbx)))
    return fbx, payload


def reimport(package, fbx, out_dir, project=None, run_script=None):
    """Replace-import `fbx` over the AnimSequence at `package`; the editor's reply."""
    out = os.path.join(out_dir, "ureimport.json")
    return _runner(run_script)(uescripts.reimport_script(out, package, fbx), out,
                               project=project)
```

Note: the test's `FakeRun` does not need `json`; remove unused imports if the linter complains. `json` is intentionally not used here; delete `import json` from the implementation before committing.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_unreal -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/skeldar_cascadeur/unreal.py tests/test_cascadeur_unreal.py
git commit -m "feat(cascadeur): the Unreal side without Maya (list, export, reimport)"
```

---

### Task 6: The Cascadeur side (the only `csc` module)

**Files:**
- Create: `SkeldarAnim/skeldar_cascadeur/cascade_io.py`
- Test: `tests/test_cascadeur_purity.py`

**Interfaces:**
- Consumes: Task 0's recorded call chains (`docs/superpowers/plans/cascadeur_probe_results.md`). The probe answers replace the `ROOT_TYPE` and frame/fps lookups below.
- Produces: `current_scene()`; `import_clip_new_tab(path)`; `export_skeleton(path)`; `skeleton_roots() -> list[str]`; `animation_frames() -> int | None`; `scene_fps() -> float | None`.

- [ ] **Step 1: Write the failing purity test**

Create `tests/test_cascadeur_purity.py`:

```python
"""Only cascade_io may import csc or pycsc. Every other module must stay
importable where Cascadeur is absent."""

import ast
import os
import unittest

PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "SkeldarAnim", "skeldar_cascadeur")
ALLOWED = {"cascade_io.py"}
BANNED = ("csc", "pycsc")


def _imports(path):
    with open(path, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), path)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


class OnlyCascadeIoTouchesCsc(unittest.TestCase):

    def test_no_other_module_imports_csc(self):
        for name in sorted(os.listdir(PKG)):
            if not name.endswith(".py") or name in ALLOWED:
                continue
            for module in _imports(os.path.join(PKG, name)):
                root = module.split(".")[0]
                self.assertNotIn(root, BANNED, "%s imports %s" % (name, module))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it passes (no module yet, no violation)**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_purity -v`
Expected: OK (nothing to violate yet). It must keep passing after this task's implementation.

- [ ] **Step 3: Write the implementation against the probe's answers**

Create `SkeldarAnim/skeldar_cascadeur/cascade_io.py`. The first block is fixed by the stubs (`fbx.pyi`, `app/__init__.pyi`) and `pycsc/general/wrapping.py`. The probe answers fill the marked lines; use the exact call the probe recorded:

```python
"""The Cascadeur side of the bridge. The only module that imports csc.

It runs inside Cascadeur. Every call here is the one Task 0's probe confirmed
(see docs/superpowers/plans/cascadeur_probe_results.md); the stub files are
resources/scripts/stubs/csc/fbx.pyi and app/__init__.pyi.
"""

import csc
import csc.app
from pycsc.general import wrapping

# The FBX loader's object-type name for a skeleton's root joints, as the probe
# recorded it. Task 0 writes the confirmed value here.
JOINT_TYPE = "joint"


def _app():
    return csc.app.get_application()


def current_scene():
    """The csc view scene of the tab in front."""
    return _app().current_scene()


def _loader(scene=None):
    tools = _app().get_tools_manager()
    return tools.get_tool("FbxSceneLoader").get_fbx_loader(scene or current_scene())


def import_clip_new_tab(path):
    """The FBX into a new scene tab (scene import: skeleton and animation)."""
    wrapping.new_scene()
    _loader(current_scene()).import_scene(path.replace("\\", "/"))


def export_skeleton(path):
    """The current scene's joints and their animation into `path` (bones only)."""
    _loader().export_joints(path.replace("\\", "/"))


def skeleton_roots():
    """Names of the root joints in the current scene. The call chain is the
    one Task 0 recorded for `get_scene_objects(only_roots=True, ...)`."""
    domain = wrapping.get_current_scene().domain_scene()
    return [obj.name for obj in domain.get_scene_objects(only_roots=True,
                                                         of_type=JOINT_TYPE)]


def animation_frames():
    """The animation's frame count, or None when the probe found no call for it."""
    domain = wrapping.get_current_scene().domain_scene()
    return domain.get_animation_size()


def scene_fps():
    """The scene's frame rate, or None when the probe found no way to read it."""
    return None
```

The `scene_fps` body is the probe's answer: if the probe found an attribute (for example `loader.fps` or a scene property), return that value instead of `None`. If nothing was found, it stays `None` and the status line skips the fps check (rules.fps_problem treats None as unknown).

- [ ] **Step 4: Run the purity test again**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_purity -v`
Expected: OK (cascade_io is the allowed module). `cascade_io.py` cannot be imported under mayapy (no csc); nothing imports it in tests. Live checks in Task 12 exercise it.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/skeldar_cascadeur/cascade_io.py tests/test_cascadeur_purity.py
git commit -m "feat(cascadeur): the Cascadeur side, the only csc module"
```

---

### Task 7: The three flows (actions)

**Files:**
- Create: `SkeldarAnim/skeldar_cascadeur/actions.py`
- Test: `tests/test_cascadeur_actions.py`

**Interfaces:**
- Consumes: `rules` (Task 1), `uasset_core` (Task 2), `prefs` (Task 3), `shared.send` (Task 4), `unreal` (Task 5); the cascade port (Task 6 names).
- Produces: class `Bridge(unreal, cascade, share, prefs_path, temp_dir, ask, machine, now=None)` with: attributes `records`, `content_dir`, `target`; methods `refresh(project=None) -> str`, `import_clips(picked, project=None) -> str`, `export_to_uasset(record=None, project=None) -> str`, `send_to_shared(typed_name, author) -> str`.

The cascade port must have: `import_clip_new_tab(path)`, `export_skeleton(path)`, `skeleton_roots()`, `animation_frames()`, `scene_fps()`. The share port is `shared` (module with `send`). The unreal port is `unreal` (module with `list_clips`, `export_clip`, `reimport`). `ask(text) -> bool`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cascadeur_actions.py`:

```python
"""The three flows over fake ports. No Cascadeur, Unreal or network."""

import os
import shutil
import tempfile
import unittest

from skeldar_cascadeur import actions
from maya_uebridge import records


def clip(name="A_Jump", package="/Game/Anim/A_Jump", frames=45, fps=30.0):
    return records.AnimRecord(name=name, package=package, skeleton="", frames=frames,
                              length=1.5, fps=fps, source="unreal", path="",
                              clip="", fmt="")


class FakeUnreal(object):
    def __init__(self, reply=None):
        self.reply = reply if reply is not None else {
            "saved": True, "frames": 45, "error": "",
            "before_frames": 45, "before_length": 1.5, "length": 1.6}
        self.exports = []
        self.reimports = []

    def list_clips(self, out_dir, project=None, run_script=None):
        return "C:/P/Content", [clip()]

    def export_clip(self, record, out_dir, project=None, run_script=None):
        path = os.path.join(out_dir, record.name + ".fbx")
        with open(path, "wb") as handle:
            handle.write(b"fbx")
        self.exports.append(record.name)
        return path, {"ok": True}

    def reimport(self, package, fbx, out_dir, project=None, run_script=None):
        self.reimports.append((package, fbx))
        return self.reply


class FakeCascade(object):
    def __init__(self, roots=("root",), frames=45, fps=30.0):
        self.roots = list(roots)
        self.frames = frames
        self.fps = fps
        self.imported = []
        self.exported = []

    def import_clip_new_tab(self, path):
        self.imported.append(path)

    def export_skeleton(self, path):
        with open(path, "wb") as handle:
            handle.write(b"fbx")
        self.exported.append(path)

    def skeleton_roots(self):
        return list(self.roots)

    def animation_frames(self):
        return self.frames

    def scene_fps(self):
        return self.fps


class FakeShare(object):
    def __init__(self):
        self.sent = []

    def send(self, path, name, author, machine, net=None, now=None, progress=None):
        self.sent.append((path, name, author))
        return {"name": name, "url": "https://x", "zip": 10}


class Bridge(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="bridge_")
        self.temp = os.path.join(self.folder, "temp")
        os.makedirs(self.temp)
        self.uasset = os.path.join(self.folder, "Content", "Anim", "A_Jump.uasset")
        os.makedirs(os.path.dirname(self.uasset))
        with open(self.uasset, "wb") as handle:
            handle.write(b"uasset")
        self.asks = []
        self.ue = FakeUnreal()
        self.cs = FakeCascade()
        self.share = FakeShare()

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def make(self, ask_answer=True):
        def ask(text):
            self.asks.append(text)
            return ask_answer
        return actions.Bridge(self.ue, self.cs, self.share,
                              os.path.join(self.folder, "prefs.json"), self.temp,
                              ask, "PC", now=lambda: 1000)

    def test_refresh_lists_and_keeps_the_content_dir(self):
        bridge = self.make()
        text = bridge.refresh()
        self.assertEqual(bridge.content_dir, "C:/P/Content")
        self.assertEqual([r.name for r in bridge.records], ["A_Jump"])
        self.assertIn("1", text)

    def test_import_exports_then_imports_and_remembers_the_target(self):
        bridge = self.make()
        bridge.refresh()
        text = bridge.import_clips([clip()])
        self.assertEqual(self.ue.exports, ["A_Jump"])
        self.assertEqual(len(self.cs.imported), 1)
        self.assertEqual(bridge.target.package, "/Game/Anim/A_Jump")
        self.assertIn("A_Jump", text)

    def test_export_refused_without_a_target(self):
        bridge = self.make()
        self.assertIn("no Unreal animation", bridge.export_to_uasset())
        self.assertEqual(self.cs.exported, [])

    def test_export_refused_with_several_skeletons_and_nothing_written(self):
        self.cs.roots = ["root", "Hips"]
        bridge = self.make()
        bridge.target = clip()
        bridge.content_dir = os.path.join(self.folder, "Content")
        text = bridge.export_to_uasset()
        self.assertIn("2 skeletons", text)
        self.assertEqual(self.ue.reimports, [])

    def test_declined_confirm_writes_nothing(self):
        bridge = self.make(ask_answer=False)
        bridge.target = clip()
        bridge.content_dir = os.path.join(self.folder, "Content")
        text = bridge.export_to_uasset()
        self.assertEqual(self.ue.reimports, [])
        self.assertIn("cancelled", text)

    def test_export_writes_back_and_reports_the_unchanged_warning(self):
        bridge = self.make()
        bridge.target = clip()
        bridge.content_dir = os.path.join(self.folder, "Content")
        self.ue.reply = {"saved": True, "frames": 45, "before_frames": 45,
                         "before_length": 1.5, "length": 1.5, "error": ""}
        text = bridge.export_to_uasset()
        self.assertEqual(len(self.ue.reimports), 1)
        self.assertIn("did NOT change", text)

    def test_export_names_the_fps_when_it_differs(self):
        self.cs.fps = 24.0
        bridge = self.make()
        bridge.target = clip()
        bridge.content_dir = os.path.join(self.folder, "Content")
        self.assertIn("24 fps", bridge.export_to_uasset())

    def test_read_only_uasset_is_cleared_after_the_export(self):
        import stat
        os.chmod(self.uasset, stat.S_IREAD)
        bridge = self.make()
        bridge.target = clip()
        bridge.content_dir = os.path.join(self.folder, "Content")
        text = bridge.export_to_uasset()
        self.assertIn("read-only cleared", text)
        self.assertTrue(os.access(self.uasset, os.W_OK))

    def test_send_exports_the_scene_then_sends(self):
        bridge = self.make()
        text = bridge.send_to_shared("A_Jump", "Yevhen")
        self.assertEqual(len(self.cs.exported), 1)
        self.assertEqual(self.share.sent[0][1], "A_Jump.fbx")
        self.assertEqual(self.share.sent[0][2], "Yevhen")
        self.assertIn("A_Jump.fbx", text)

    def test_send_needs_an_author(self):
        bridge = self.make()
        self.assertIn("author", bridge.send_to_shared("A", ""))
        self.assertEqual(self.share.sent, [])

    def test_author_is_remembered(self):
        import skeldar_cascadeur.prefs as prefs
        bridge = self.make()
        bridge.send_to_shared("A", "Yevhen")
        self.assertEqual(prefs.get(os.path.join(self.folder, "prefs.json"),
                                   "author"), "Yevhen")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_actions -v`
Expected: ImportError.

- [ ] **Step 3: Write the minimal implementation**

Create `SkeldarAnim/skeldar_cascadeur/actions.py`:

```python
"""The three flows of the bridge window, over injected ports.

The window's buttons call these. Nothing here imports Qt, csc or Maya, so the
whole flow is tested with fakes. The defaults are wired by bridge.py.

Ports:
  unreal   -- module-like: list_clips, export_clip, reimport  (unreal.py)
  cascade  -- import_clip_new_tab, export_skeleton, skeleton_roots,
              animation_frames, scene_fps                     (cascade_io.py)
  share    -- module-like: send                                 (shared.py)
  ask      -- callable(text) -> bool, the confirm dialog
"""

import os
import socket
import tempfile

from maya_uebridge import records
from maya_uebridge import uasset_core
from skeldar_cascadeur import prefs
from skeldar_cascadeur import rules

CANCELLED = "cancelled - nothing changed"
NO_AUTHOR = "type an author name first - nothing sent"


def _machine():
    try:
        return socket.gethostname()
    except OSError:
        return "unknown"


class Bridge(object):
    """One bridge window's state and its three flows."""

    def __init__(self, unreal, cascade, share, prefs_path, temp_dir, ask,
                 machine=None, now=None):
        self.unreal = unreal
        self.cascade = cascade
        self.share = share
        self.prefs_path = prefs_path
        self.temp_dir = temp_dir
        self.ask = ask
        self.machine = machine or _machine()
        self.now = now
        self.records = []
        self.content_dir = ""
        self.target = None
        os.makedirs(temp_dir, exist_ok=True)

    # ---- the list ---------------------------------------------------------

    def refresh(self, project=None):
        """Re-read the Unreal list. Returns the status line."""
        self.content_dir, self.records = self.unreal.list_clips(
            self.temp_dir, project=project)
        return "{0} animation(s) in Unreal".format(len(self.records))

    # ---- import -----------------------------------------------------------

    def import_clips(self, picked, project=None):
        """Each picked clip: exported from Unreal, imported into a new tab.
        Returns one status line naming every clip and its frame count."""
        lines = []
        for rec in picked:
            try:
                fbx, _payload = self.unreal.export_clip(rec, self.temp_dir,
                                                        project=project)
                self.cascade.import_clip_new_tab(fbx)
                frames = self.cascade.animation_frames()
                self.target = rec
                lines.append("{0}: new tab, {1} frames".format(
                    rules.clip_tab_name(rec.name),
                    "?" if frames is None else frames))
            except Exception as exc:                    # noqa: BLE001
                lines.append("{0}: {1}".format(rec.name, exc))
        self._remember_target()
        return rules.join_status(lines)

    # ---- export to uasset -------------------------------------------------

    def export_to_uasset(self, record=None, project=None):
        """The scene's skeleton animation back into the picked clip's uasset."""
        rec = record or self.target
        package = rec.package if rec is not None else ""
        uasset = (records.uasset_path_of(package, self.content_dir)
                  if package and self.content_dir else "")
        problem = rules.export_refusal(package, uasset,
                                       bool(uasset) and os.path.isfile(uasset))
        if problem:
            return problem
        problem = rules.skeleton_problem(self.cascade.skeleton_roots())
        if problem:
            return problem

        read_only = uasset_core.is_read_only(uasset)
        if not self.ask(self._confirm_text(rec, uasset, read_only)):
            return CANCELLED

        fbx = uasset_core.fbx_staging_path(rec.name, self.temp_dir)
        self.cascade.export_skeleton(fbx)
        if read_only:
            failure = uasset_core.clear_read_only(uasset)
            if failure:
                return "cannot clear read-only on {0}: {1}".format(uasset, failure)

        payload = self.unreal.reimport(package, fbx, self.temp_dir, project=project)
        self.target = rec
        self._remember_target()
        return rules.join_status([
            uasset_core.readonly_note(read_only),
            records.reimport_line(payload),
            records.unchanged_warning(payload),
            rules.fps_problem(self.cascade.scene_fps()),
            ("editor: " + str(payload.get("error"))) if payload.get("error") else "",
        ])

    def _confirm_text(self, rec, uasset, read_only):
        lines = ["Overwrite the animation in {0}?".format(rec.name), "",
                 "    asset:    {0}".format(rec.package),
                 "",
                 "The asset is REBUILT from an FBX of the scene, so curves the FBX",
                 "does not carry do not survive it ({0}).".format(
                     uasset_core.LOST_CURVES),
                 "",
                 "Perforce is not touched: the uasset is written on disk."]
        if read_only:
            lines += ["", "The file is read-only. That flag will be CLEARED and "
                          "left off."]
        return "\n".join(lines)

    # ---- send to Shared ---------------------------------------------------

    def send_to_shared(self, typed_name, author, project=None):
        """The scene's skeleton animation to everybody, as a zipped FBX."""
        author = (author or "").strip()
        if not author:
            return NO_AUTHOR
        problem = rules.skeleton_problem(self.cascade.skeleton_roots())
        if problem:
            return problem
        fallback = "animation.fbx"
        name = records.upload_name(typed_name, fallback)
        fbx = os.path.join(self.temp_dir, name)
        self.cascade.export_skeleton(fbx)
        self._remember_author(author)
        ready = self.share.send(fbx, name, author, self.machine, now=self.now)
        return "sent {0} to everybody ({1} zipped)".format(
            ready["name"], records.size_text(ready["zip"]))

    # ---- prefs ------------------------------------------------------------

    def _remember_target(self):
        if self.target is not None:
            prefs.put(self.prefs_path, "target", self.target.package)

    def _remember_author(self, author):
        prefs.put(self.prefs_path, "author", author)
```

Note for the implementer: `records.size_text` exists in `maya_sharerecords` (line ~300), not in `maya_uebridge.records`. Replace `records.size_text(ready["zip"])` with `sharerecords.size_text(ready["zip"])` after adding `import maya_sharerecords as sharerecords` at the top. Also `records.upload_name` lives in `maya_sharerecords` (not in `maya_uebridge.records`): use `sharerecords.upload_name(typed_name, fallback)` in `send_to_shared`. Fix both imports before running the tests; the `maya_uebridge.records` name clash is why the share module is aliased. The `self.share` fake in the tests does not define `upload_name`, so the actions module must call `sharerecords.upload_name` directly (the pure function), not through the share port. The test `test_send_exports_the_scene_then_sends` expects the name `A_Jump.fbx` from typed "A_Jump" — `upload_name("A_Jump", "animation.fbx")` keeps the source extension only when the typed name has none; therefore for the export file name the actions pass the fallback extension `.fbx`. Set the fallback to "animation.fbx" and make `upload_name` produce `A_Jump.fbx` by appending `.fbx` only when the typed name has no extension: call `sharerecords.upload_name(typed, fallback)` and assert in the test against the value it returns; keep the test's expectation `A_Jump.fbx` and verify it when running.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_actions -v`
Expected: all OK. If `send_to_shared` naming fails, fix as the note says before continuing.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/skeldar_cascadeur/actions.py tests/test_cascadeur_actions.py
git commit -m "feat(cascadeur): the three bridge flows over injected ports"
```

---

### Task 8: The window (PySide6, thin)

**Files:**
- Create: `SkeldarAnim/skeldar_cascadeur/window.py`
- Test: `tests/test_cascadeur_window.py`

**Interfaces:**
- Consumes: a bridge object with `records`, `refresh(project=None)`, `import_clips(picked, project=None)`, `export_to_uasset(record=None, project=None)`, `send_to_shared(typed_name, author, project=None)`, and `target` (Task 7).
- Produces: class `BridgeWindow(QtWidgets.QWidget)` with `__init__(self, bridge)`, `populate()`, `visible_names() -> list[str]`, and `status` as a QLabel. Module must NOT define `run` or `name`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cascadeur_window.py`:

```python
"""The Cascadeur bridge window, offscreen. No Cascadeur, Unreal or network."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

from skeldar_cascadeur import window  # noqa: E402
from maya_uebridge import records  # noqa: E402


def clip(name):
    return records.AnimRecord(name=name, package="/Game/" + name, skeleton="",
                              frames=10, length=0.3, fps=30.0, source="unreal",
                              path="", clip="", fmt="")


class FakeBridge(object):
    def __init__(self):
        self.records = [clip("A_Jump"), clip("B_Walk")]
        self.target = None
        self.calls = []

    def refresh(self, project=None):
        self.calls.append("refresh")
        return "2 animation(s) in Unreal"

    def import_clips(self, picked, project=None):
        self.calls.append(("import", [r.name for r in picked]))
        return "done"

    def export_to_uasset(self, record=None, project=None):
        self.calls.append(("export", record.name if record else None))
        return "exported"

    def send_to_shared(self, typed_name, author, project=None):
        self.calls.append(("send", typed_name, author))
        return "sent"


class Window(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_lists_every_clip(self):
        bridge = FakeBridge()
        win = window.BridgeWindow(bridge)
        win.populate()
        self.assertEqual(win.visible_names(), ["A_Jump", "B_Walk"])

    def test_search_filters_the_list(self):
        win = window.BridgeWindow(FakeBridge())
        win.populate()
        win.search.setText("walk")
        self.assertEqual(win.visible_names(), ["B_Walk"])

    def test_import_button_passes_the_selection(self):
        bridge = FakeBridge()
        win = window.BridgeWindow(bridge)
        win.populate()
        win.list.item(0).setSelected(True)
        win.import_selected()
        self.assertIn(("import", ["A_Jump"]), bridge.calls)
        self.assertIn("done", win.status.text())

    def test_export_uses_the_single_selected_row(self):
        bridge = FakeBridge()
        win = window.BridgeWindow(bridge)
        win.populate()
        win.list.item(1).setSelected(True)
        win.export_selected()
        self.assertIn(("export", "B_Walk"), bridge.calls)

    def test_send_passes_name_and_author(self):
        bridge = FakeBridge()
        win = window.BridgeWindow(bridge)
        win.author.setText("Yevhen")
        win.name.setText("attack")
        win.send_selected()
        self.assertIn(("send", "attack", "Yevhen"), bridge.calls)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_window -v`
Expected: ImportError.

- [ ] **Step 3: Write the minimal implementation**

Create `SkeldarAnim/skeldar_cascadeur/window.py`:

```python
"""The Cascadeur bridge window. Plain PySide6 widgets; every button calls the
bridge object (actions.Bridge), which holds the logic and is tested without Qt.

Module-level functions here are NOT named `run` or `name`: Cascadeur's action
discovery treats a module with `run` as a menu action (only bridge.py is one).
"""

from PySide6 import QtCore, QtWidgets


class BridgeWindow(QtWidgets.QWidget):

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.setObjectName("skeldarCascadeurBridge")
        self.setWindowTitle("SkeldarAnim - Bridge")
        self.resize(460, 620)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Unreal animations"))

        row = QtWidgets.QHBoxLayout()
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("search")
        self.search.textChanged.connect(self._filter)
        row.addWidget(self.search, 1)
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        row.addWidget(self.refresh_button)
        layout.addLayout(row)

        self.list = QtWidgets.QListWidget()
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.list, 1)

        self.import_button = QtWidgets.QPushButton("Import into Cascadeur")
        self.import_button.clicked.connect(self.import_selected)
        layout.addWidget(self.import_button)

        layout.addWidget(QtWidgets.QLabel("Cascadeur scene"))
        self.export_button = QtWidgets.QPushButton("Export to uasset")
        self.export_button.clicked.connect(self.export_selected)
        layout.addWidget(self.export_button)

        self.author = QtWidgets.QLineEdit()
        self.author.setPlaceholderText("author")
        self.name = QtWidgets.QLineEdit()
        self.name.setPlaceholderText("name of the upload")
        layout.addWidget(self.author)
        layout.addWidget(self.name)
        self.send_button = QtWidgets.QPushButton("Send to Shared")
        self.send_button.clicked.connect(self.send_selected)
        layout.addWidget(self.send_button)

        self.target = QtWidgets.QLabel("")
        layout.addWidget(self.target)
        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.populate()
        self._show_target()

    # ---- the list ---------------------------------------------------------

    def populate(self):
        self.list.clear()
        for rec in self.bridge.records:
            item = QtWidgets.QListWidgetItem(rec.name)
            item.setData(QtCore.Qt.UserRole, rec.package)
            self.list.addItem(item)
        self._filter(self.search.text())

    def visible_names(self):
        return [self.list.item(i).text() for i in range(self.list.count())
                if not self.list.item(i).isHidden()]

    def _filter(self, text):
        needle = (text or "").lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(needle not in item.text().lower())

    def _picked(self):
        by_name = {rec.name: rec for rec in self.bridge.records}
        return [by_name[item.text()] for item in self.list.selectedItems()
                if item.text() in by_name]

    # ---- the buttons ------------------------------------------------------

    def refresh(self):
        self._say(self.bridge.refresh())
        self.populate()

    def import_selected(self):
        picked = self._picked()
        if not picked:
            return self._say("select one or more animations first")
        self._say(self.bridge.import_clips(picked))
        self._show_target()

    def export_selected(self):
        picked = self._picked()
        record = picked[0] if len(picked) == 1 else None
        self._say(self.bridge.export_to_uasset(record))
        self._show_target()

    def send_selected(self):
        self._say(self.bridge.send_to_shared(self.name.text(), self.author.text()))

    # ---- helpers ----------------------------------------------------------

    def _say(self, text):
        self.status.setText(text)

    def _show_target(self):
        rec = getattr(self.bridge, "target", None)
        self.target.setText("Write-back target: {0}".format(
            rec.package if rec is not None else "none - import a clip first"))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_window -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/skeldar_cascadeur/window.py tests/test_cascadeur_window.py
git commit -m "feat(cascadeur): the bridge window"
```

---

### Task 9: The menu action (bridge.py) and discovery

**Files:**
- Create: `SkeldarAnim/skeldar_cascadeur/bridge.py`
- Test: `tests/test_cascadeur_discovery.py`

**Interfaces:**
- Consumes: `window.BridgeWindow`, `actions.Bridge`, `unreal`, `shared`, `prefs`; `cascade_io` (imported lazily inside `wire()`).
- Produces: `name() -> "SkeldarAnim.Bridge"`, `description() -> str`, `run(scene)` (opens or raises the window), `wire(temp_dir=None) -> actions.Bridge`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cascadeur_discovery.py`:

```python
"""Cascadeur discovers menu actions by `run`/`name` (python_actions_rule). The
bridge must be the only module of its package that defines `run`, so it is
the only menu entry, and its name() is the menu text."""

import ast
import os
import unittest

PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "SkeldarAnim", "skeldar_cascadeur")


def _top_level_functions(path):
    with open(path, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), path)
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


class Discovery(unittest.TestCase):

    def test_only_bridge_defines_run(self):
        for name in sorted(os.listdir(PKG)):
            if not name.endswith(".py") or name == "bridge.py":
                continue
            defined = _top_level_functions(os.path.join(PKG, name))
            self.assertNotIn("run", defined, name)
            self.assertNotIn("name", defined, name)

    def test_bridge_defines_the_action_contract(self):
        defined = _top_level_functions(os.path.join(PKG, "bridge.py"))
        self.assertTrue({"name", "description", "run"} <= defined)

    def test_menu_text_is_the_bridge_name(self):
        import sys
        plugin = os.path.dirname(PKG)
        if plugin not in sys.path:
            sys.path.insert(0, plugin)
        from skeldar_cascadeur import bridge
        self.assertEqual(bridge.name(), "SkeldarAnim.Bridge")
        self.assertIn("Unreal", bridge.description())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_discovery -v`
Expected: FAIL (bridge.py missing).

- [ ] **Step 3: Write the minimal implementation**

Create `SkeldarAnim/skeldar_cascadeur/bridge.py`:

```python
"""Scripts > SkeldarAnim > Bridge in Cascadeur.

Cascadeur's action discovery (python_actions_rule.get_action_info) reads
`name`, `description` and `run` from this module. `run(scene)` opens the
window once; a second press raises it. The window and the Cascadeur side are
imported only when the window opens, so discovery at Cascadeur's start stays
light and cannot fail on PySide6.
"""

import os
import sys
import tempfile

HOLDER = "_skeldar_cascadeur_bridge"


def name():
    return "SkeldarAnim.Bridge"


def description():
    return ("Unreal <-> Cascadeur: import a skeletal animation, write the "
            "scene back to its uasset, send it to Shared")


def wire(temp_dir=None):
    """The bridge object with the real ports (Unreal, Cascadeur, Shared)."""
    from skeldar_cascadeur import actions
    from skeldar_cascadeur import cascade_io
    from skeldar_cascadeur import prefs
    from skeldar_cascadeur import shared
    from skeldar_cascadeur import unreal
    from PySide6 import QtWidgets

    def ask(text):
        box = QtWidgets.QMessageBox.question(
            None, "SkeldarAnim - Bridge", text,
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        return box == QtWidgets.QMessageBox.Ok

    folder = temp_dir or os.path.join(tempfile.gettempdir(), "skeldar_cascadeur")
    return actions.Bridge(unreal, cascade_io, shared, prefs.default_path(),
                          folder, ask)


def run(scene):
    """Open the bridge window, or raise the one already open."""
    from skeldar_cascadeur import window

    existing = getattr(sys, HOLDER, None)
    if existing is not None and existing.isVisible():
        existing.raise_()
        existing.activateWindow()
        return existing
    win = window.BridgeWindow(wire())
    setattr(sys, HOLDER, win)
    win.show()
    return win
```

Note for the implementer: `window.BridgeWindow` needs the Qt application: Cascadeur is a Qt application already; `QtWidgets.QApplication.instance()` is not None there. Do not create a second QApplication in `run`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_discovery -v`
Expected: all OK. (`bridge.name()` imports nothing heavy; `wire`/`run` are not called.)

- [ ] **Step 5: Run every Cascadeur-bridge unit test together**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_rules tests.test_cascadeur_uasset_core tests.test_cascadeur_prefs tests.test_cascadeur_shared tests.test_cascadeur_unreal tests.test_cascadeur_purity tests.test_cascadeur_actions tests.test_cascadeur_window tests.test_cascadeur_discovery tests.test_uebridge_uasset -v`
Expected: all OK.

- [ ] **Step 6: Commit**

```bash
git add SkeldarAnim/skeldar_cascadeur/bridge.py tests/test_cascadeur_discovery.py
git commit -m "feat(cascadeur): the Scripts > SkeldarAnim > Bridge menu action"
```

---

### Task 10: The installer for Cascadeur (repo root)

**Files:**
- Create: `SkeldarAnim_Cascadeur_Install.py` (repo root)
- Test: `tests/test_cascadeur_installer.py`

**Interfaces:**
- Consumes: the release zip layout made by `make_build.py`: a top folder `SkeldarAnim/` containing `skeldar_cascadeur/bridge.py`.
- Produces: `settings_edit(text, install_dir, package) -> (new_text, changed)` (pure, raises `SetupError`); `archive_problems(names) -> [str]`; `is_ours(folder) -> bool`; `install(source_zip=None, install_dir=None, settings_path=None, progress=None) -> str` (the status line).

Defaults: `install_dir = %USERPROFILE%\Documents\SkeldarAnim`; `settings_path = %LOCALAPPDATA%\Nekki Limited\Cascadeur\settings.json`; `package = "skeldar_cascadeur"`; release URL `https://github.com/EugeneM23/MayaScripts/releases/latest/download/SkeldarAnim.zip`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cascadeur_installer.py`:

```python
"""The Cascadeur installer, loaded from the repo root by path. Stdlib only."""

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "skeldar_cascade_installer", os.path.join(ROOT, "SkeldarAnim_Cascadeur_Install.py"))
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

INSTALL = r"C:\Users\x\Documents\SkeldarAnim"


class SettingsEdit(unittest.TestCase):

    def base(self):
        return json.dumps({"ScriptsDir": "", "Python": {
            "Path": [], "Commands": ["commands"], "Scripts": ["scripts"]}})

    def test_adds_path_and_package(self):
        text, changed = installer.settings_edit(self.base(), INSTALL, "skeldar_cascadeur")
        data = json.loads(text)
        self.assertTrue(changed)
        self.assertIn(INSTALL, data["Python"]["Path"])
        self.assertIn("skeldar_cascadeur", data["Python"]["Scripts"])
        self.assertIn("scripts", data["Python"]["Scripts"])
        self.assertEqual(data["ScriptsDir"], "")
        self.assertEqual(data["Python"]["Commands"], ["commands"])

    def test_second_run_changes_nothing(self):
        first, _ = installer.settings_edit(self.base(), INSTALL, "skeldar_cascadeur")
        second, changed = installer.settings_edit(first, INSTALL, "skeldar_cascadeur")
        self.assertFalse(changed)
        self.assertEqual(json.loads(first), json.loads(second))

    def test_path_compare_ignores_case_and_trailing_slash(self):
        text = json.dumps({"Python": {"Path": [INSTALL.upper() + "\\"],
                                      "Scripts": ["skeldar_cascadeur"]}})
        _, changed = installer.settings_edit(text, INSTALL, "skeldar_cascadeur")
        self.assertFalse(changed)

    def test_missing_python_section_is_created(self):
        text, changed = installer.settings_edit("{}", INSTALL, "skeldar_cascadeur")
        self.assertTrue(changed)
        self.assertIn("skeldar_cascadeur", json.loads(text)["Python"]["Scripts"])

    def test_not_json_is_refused_and_nothing_changes(self):
        with self.assertRaises(installer.SetupError):
            installer.settings_edit("{broken", INSTALL, "skeldar_cascadeur")


class Archive(unittest.TestCase):

    def test_a_build_needs_the_bridge_module(self):
        self.assertTrue(installer.archive_problems(["SkeldarAnim/install.py"]))

    def test_a_good_build_passes(self):
        names = ["SkeldarAnim/install.py",
                 "SkeldarAnim/skeldar_cascadeur/bridge.py"]
        self.assertEqual(installer.archive_problems(names), [])

    def test_a_path_escape_is_refused(self):
        names = ["SkeldarAnim/skeldar_cascadeur/bridge.py", "../evil.py"]
        self.assertTrue(any("outside" in p for p in installer.archive_problems(names)))


class Install(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cascadeur_install_")
        self.zip = os.path.join(self.root, "SkeldarAnim.zip")
        with zipfile.ZipFile(self.zip, "w") as archive:
            archive.writestr("SkeldarAnim/skeldar_cascadeur/bridge.py", "def name():\n    return 'x'\n")
            archive.writestr("SkeldarAnim/install.py", "# build\n")
        self.target = os.path.join(self.root, "Documents", "SkeldarAnim")
        self.settings = os.path.join(self.root, "Cascadeur", "settings.json")
        os.makedirs(os.path.dirname(self.settings))
        with open(self.settings, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"ScriptsDir": "", "Python": {
                "Path": [], "Commands": ["commands"], "Scripts": ["scripts"]}}))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_installs_edits_settings_and_backs_up(self):
        status = installer.install(source_zip=self.zip, install_dir=self.target,
                                   settings_path=self.settings)
        self.assertTrue(os.path.isfile(os.path.join(self.target, "skeldar_cascadeur", "bridge.py")))
        self.assertTrue(os.path.isfile(self.settings + ".skeldar-backup"))
        with open(self.settings, encoding="utf-8") as handle:
            self.assertIn("skeldar_cascadeur", json.load(handle)["Python"]["Scripts"])
        self.assertIn("restart", status.lower())

    def test_second_run_updates_and_leaves_settings_alone(self):
        installer.install(source_zip=self.zip, install_dir=self.target,
                          settings_path=self.settings)
        with open(self.settings, encoding="utf-8") as handle:
            after_first = handle.read()
        status = installer.install(source_zip=self.zip, install_dir=self.target,
                                   settings_path=self.settings)
        with open(self.settings, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), after_first)
        self.assertIn("already", status.lower())

    def test_refuses_a_folder_that_is_not_ours(self):
        os.makedirs(self.target)
        with open(os.path.join(self.target, "my_notes.txt"), "w") as handle:
            handle.write("keep me")
        with self.assertRaises(installer.SetupError):
            installer.install(source_zip=self.zip, install_dir=self.target,
                              settings_path=self.settings)
        self.assertTrue(os.path.isfile(os.path.join(self.target, "my_notes.txt")))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_installer -v`
Expected: FAIL (file missing).

- [ ] **Step 3: Write the minimal implementation**

Create `SkeldarAnim_Cascadeur_Install.py` at the repo root:

```python
"""SkeldarAnim_Cascadeur_Install.py - the SkeldarAnim bridge for Cascadeur.

Run it once in Cascadeur's Python console (no Maya needed):

    exec(open(r"<path>\\SkeldarAnim_Cascadeur_Install.py", encoding="utf-8").read())

It downloads the latest SkeldarAnim build from GitHub's Releases, unpacks it,
copies the plugin to  %USERPROFILE%\\Documents\\SkeldarAnim  and adds that
folder and the skeldar_cascadeur package to Cascadeur's settings.json (a
backup is written first). Restart Cascadeur afterwards: the menu entry
SkeldarAnim > Bridge appears then.

Stdlib only. The open scene is not touched. A folder at the install path that
is not ours is refused and left alone. Spec:
docs/superpowers/specs/2026-10-09-cascadeur-bridge-design.md
"""

import json
import os
import shutil
import tempfile
import urllib.request
import zipfile

REPO = "EugeneM23/MayaScripts"
ZIP_URL = "https://github.com/{0}/releases/latest/download/SkeldarAnim.zip".format(REPO)
TOP = "SkeldarAnim"
PACKAGE = "skeldar_cascadeur"
MARKER = os.path.join(PACKAGE, "bridge.py")
BACKUP_SUFFIX = ".skeldar-backup"
USER_AGENT = "SkeldarAnim-cascadeur-setup"
TIMEOUT = 30
CHUNK = 256 * 1024


class SetupError(Exception):
    """A refusal before anything was changed."""


# ---------------------------------------------------------------- pure

def archive_problems(names):
    """What is wrong with the archive's member names, as sentences."""
    problems = []
    if TOP + "/install.py" not in names and MARKER.replace("\\", "/") not in [
            n.replace("\\", "/") for n in names]:
        problems.append("the archive holds no {0} module".format(MARKER))
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if name.startswith(("/", "\\")) or ".." in parts or ":" in parts[0]:
            problems.append("a path outside the archive: " + name)
    return problems


def _same_path(a, b):
    return os.path.normcase(os.path.normpath(a)).rstrip("\\/") == \
        os.path.normcase(os.path.normpath(b)).rstrip("\\/")


def settings_edit(text, install_dir, package):
    """(new_text, changed): the settings with the install folder on Python.Path
    and the package on Python.Scripts. Every other key is kept. Raises
    SetupError when the text is not a JSON object."""
    try:
        data = json.loads(text) if text.strip() else {}
    except ValueError:
        raise SetupError("settings.json is not valid JSON - nothing changed")
    if not isinstance(data, dict):
        raise SetupError("settings.json is not a JSON object - nothing changed")
    python = data.get("Python")
    if not isinstance(python, dict):
        python = {}
        data["Python"] = python
    changed = False
    paths = list(python.get("Path") or [])
    if not any(_same_path(p, install_dir) for p in paths if isinstance(p, str)):
        paths.append(install_dir)
        changed = True
    python["Path"] = paths
    scripts = list(python.get("Scripts") or [])
    if package not in scripts:
        scripts.append(package)
        changed = True
    python["Scripts"] = scripts
    if "Commands" not in python:
        python["Commands"] = ["commands"]
    return json.dumps(data, indent=4, ensure_ascii=False) + "\n", changed


def is_ours(folder):
    """True when the folder is missing or holds our marker module."""
    return (not os.path.exists(folder)) or os.path.isfile(os.path.join(folder, MARKER))


# ------------------------------------------------------------ the world

def default_install_dir():
    return os.path.join(os.path.expanduser("~"), "Documents", TOP)


def default_settings_path():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Nekki Limited", "Cascadeur", "settings.json")


def download(url, path, progress=None):
    """`url` into `path`; `progress(done, total)` returning False cancels."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response, \
                open(path, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                block = response.read(CHUNK)
                if not block:
                    break
                out.write(block)
                done += len(block)
                if progress and progress(done, total) is False:
                    raise SetupError("cancelled - nothing changed")
    except SetupError:
        raise
    except Exception as exc:                          # noqa: BLE001
        raise SetupError("could not download the build ({0}) - nothing "
                         "changed".format(exc))


def _backup(settings_path):
    backup = settings_path + BACKUP_SUFFIX
    if not os.path.isfile(backup):
        shutil.copy2(settings_path, backup)
    return backup


def install(source_zip=None, install_dir=None, settings_path=None, progress=None):
    """Install (or update) the bridge. Returns the status line."""
    install_dir = install_dir or default_install_dir()
    settings_path = settings_path or default_settings_path()
    if not is_ours(install_dir):
        raise SetupError("{0} exists and is not a SkeldarAnim install - nothing "
                         "changed".format(install_dir))
    if not os.path.isfile(settings_path):
        raise SetupError("no Cascadeur settings.json at {0} - start Cascadeur "
                         "once, then run this again".format(settings_path))
    with open(settings_path, "r", encoding="utf-8") as handle:
        current = handle.read()
    new_text, changed = settings_edit(current, install_dir, PACKAGE)

    work = tempfile.mkdtemp(prefix="skeldar_cascade_install_")
    try:
        archive = source_zip
        if archive is None:
            archive = os.path.join(work, "SkeldarAnim.zip")
            download(ZIP_URL, archive, progress)
        with zipfile.ZipFile(archive) as zipped:
            names = zipped.namelist()
            problems = archive_problems(names)
            if problems:
                raise SetupError("; ".join(problems) + " - nothing changed")
            zipped.extractall(os.path.join(work, "unpacked"))
        source = os.path.join(work, "unpacked", TOP)
        if os.path.isdir(install_dir):
            shutil.rmtree(install_dir)
        shutil.copytree(source, install_dir)
        if changed:
            _backup(settings_path)
            with open(settings_path, "w", encoding="utf-8") as handle:
                handle.write(new_text)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if changed:
        return ("installed to {0} and added to Cascadeur's settings - restart "
                "Cascadeur, then SkeldarAnim > Bridge".format(install_dir))
    return ("updated {0}; Cascadeur's settings already hold it - restart "
            "Cascadeur if it was open".format(install_dir))


if __name__ == "__main__":
    print(install())
```

Note for the implementer: the `archive_problems` first condition is intentionally simple: the archive must hold `SkeldarAnim/skeldar_cascadeur/bridge.py` or the Maya installer `SkeldarAnim/install.py`; the test `test_a_build_needs_the_bridge_module` passes only `install.py` and expects a problem, so change the condition to require `MARKER` inside `TOP/`: `TOP + "/" + MARKER.replace("\\", "/")`. Make the test and the function agree on that exact member name, then run the test.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_installer -v`
Expected: all OK. Fix `archive_problems` per the note first.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim_Cascadeur_Install.py tests/test_cascadeur_installer.py
git commit -m "feat(cascadeur): the installer for Cascadeur (no Maya needed)"
```

---

### Task 11: Payload and release asset

**Files:**
- Modify: `SkeldarAnim/install.py` (`_PAYLOAD` gains `skeldar_cascadeur` and the Shared modules if missing)
- Modify: `.github/workflows/build.yml` (the Cascadeur installer as a release asset)
- Test: `tests/test_cascadeur_payload.py`

**Interfaces:**
- Consumes: `install.payload()`.
- Produces: the release zip contains `SkeldarAnim/skeldar_cascadeur/` and the shared modules.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cascadeur_payload.py`:

```python
"""The Cascadeur package and everything it imports ships in the zip."""

import os
import unittest

from maya_uebridge import records  # noqa: F401  (importable from the plugin)
import install

PLUGIN = os.path.dirname(os.path.abspath(install.__file__))


class Payload(unittest.TestCase):

    def test_cascadeur_package_ships(self):
        self.assertIn("skeldar_cascadeur", install.payload())

    def test_shared_modules_ship(self):
        names = install.payload()
        self.assertIn("maya_sharenet.py", names)
        self.assertIn("maya_sharerecords.py", names)

    def test_uebridge_package_ships(self):
        self.assertIn("maya_uebridge", install.payload())

    def test_every_package_module_is_in_the_payload(self):
        package = os.path.join(PLUGIN, "skeldar_cascadeur")
        for name in os.listdir(package):
            if name.endswith(".py"):
                self.assertTrue(os.path.isfile(os.path.join(PLUGIN, "skeldar_cascadeur", name)))
        self.assertIn("skeldar_cascadeur", install.payload())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_payload -v`
Expected: FAIL on `test_cascadeur_package_ships`.

- [ ] **Step 3: Add the package to the payload and the Cascadeur installer to CI**

In `SkeldarAnim/install.py`, inside `_PAYLOAD`, add after the `"maya_uebridge",` line:

```python
    "skeldar_cascadeur",        # the Cascadeur bridge (2026-10-09)
```

If `maya_sharenet.py` or `maya_sharerecords.py` is not already in `_PAYLOAD`, add both after `"maya_share.py"` (grep `_PAYLOAD` for `maya_share` first; add only what is missing).

In `.github/workflows/build.yml`:
- In the line `gh release create "$tag" dist/SkeldarAnim.zip dist/version.json SkeldarAnim_Install.py \`, add `SkeldarAnim_Cascadeur_Install.py \` after `SkeldarAnim_Install.py \` (keep the trailing backslash).
- In the re-upload step (`gh release upload "$latest" SkeldarAnim_Install.py --clobber`), add a second line `gh release upload "$latest" SkeldarAnim_Cascadeur_Install.py --clobber`.
- If the workflow's `paths:` trigger lists `SkeldarAnim_Install.py`, add `SkeldarAnim_Cascadeur_Install.py` beside it.

Verify the YAML is still well-formed: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -c "import json,sys; print('ok')"` is not a YAML check; instead open the file and check the indentation of the edited lines matches their neighbours.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_cascadeur_payload tests.test_make_build -v`
Expected: all OK. (`test_make_build` checks the zip against the payload; it must still pass.)

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/install.py .github/workflows/build.yml tests/test_cascadeur_payload.py
git commit -m "build: ship the Cascadeur bridge and its installer as a release asset"
```

---

### Task 12: Live verification in the animator's Cascadeur and Unreal

**Files:**
- Create: `docs/superpowers/plans/verify_cascadeur_bridge.py`
- Create: `docs/superpowers/plans/cascadeur_bridge_live.md`

**Interfaces:**
- Consumes: everything above; the animator's running Cascadeur with the script server started; the Unreal editor open with Remote Execution on.
- Produces: the live proof record.

The verify runs inside Cascadeur through `POST /run` (one code string that exec's the file with a fresh namespace). It writes its gate results to `verify_result.json` in the probe folder, and the runner marks itself with a `.ran` file so a queued duplicate does nothing (CLAUDE.md note 5, 8: guard with an `if`, never a raise).

- [ ] **Step 1: Install through the installer, in Cascadeur**

Build the local source zip from the working tree with `make_build.py` (mayapy), then run the installer's `install` in Cascadeur through `/run`. Commands:

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' 'C:\!!!Work\MayaScripts\make_build.py' --out 'C:\Users\MY PC\AppData\Local\Temp\skeldar_cascade_probe\SkeldarAnim_cascade.zip'
```

Then `POST /run` with this code (the zip path is the one just built):

```python
import importlib.util
spec = importlib.util.spec_from_file_location("sk_cascade_install", r"C:\!!!Work\MayaScripts\SkeldarAnim_Cascadeur_Install.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.install(source_zip=r"C:\Users\MY PC\AppData\Local\Temp\skeldar_cascade_probe\SkeldarAnim_cascade.zip"))
```

Expected: a status line ending in "restart Cascadeur". Check: `Documents\SkeldarAnim\skeldar_cascadeur\bridge.py` exists; `settings.json.skeldar-backup` exists; `settings.json` lists the folder in `Python.Path` and `skeldar_cascadeur` in `Python.Scripts`. Do NOT print `config\v1\token.cfg`.

- [ ] **Step 2: Ask the animator to restart Cascadeur**

Say in chat: "Установка прошла. Перезапустите Cascadeur (закройте и откройте), и напишите мне, когда он снова откроется с запущенным сервером: Scripts → MCP → Start script server." Wait for the answer. This is the one point that needs the animator's hands.

- [ ] **Step 3: Write the verify script**

Create `docs/superpowers/plans/verify_cascadeur_bridge.py`. It is exec'd by `/run` with `scene` and `csc` in scope (the server's namespace); it imports the installed copy and checks the gates:

```python
"""Live verify of the Cascadeur bridge, run inside Cascadeur via /run.

Gates (0 failed = green): menu entry discovered; window opens and raises;
Unreal list non-empty; import of one clip into a NEW tab has the clip's frame
count; export to a sandbox uasset (duplicated from the clip, deleted after)
round-trips the frame count and is not reported unchanged; a read-only sandbox
is cleared; the send goes to a TEST ntfy topic and reads back.
Writes verify_result.json; marks itself with .ran so a queued duplicate exits.
"""

import json, os, sys, time, uuid, stat, traceback

OUT = r"C:\Users\MY PC\AppData\Local\Temp\skeldar_cascade_probe"
RESULT = os.path.join(OUT, "verify_result.json")
MARK = os.path.join(OUT, "verify.ran")
PLUGIN = r"C:\Users\MY PC\Documents\SkeldarAnim"
SANDBOX = "/Game/__bridge_verify/"
TEST_TOPIC = "skeldar-cascade-verify-" + uuid.uuid4().hex[:12]

if not os.path.exists(MARK):
    open(MARK, "w").close()
    results = {"gates": [], "notes": []}

    def gate(name, ok, detail=""):
        results["gates"].append({"name": name, "ok": bool(ok), "detail": str(detail)})

    try:
        if PLUGIN not in sys.path:
            sys.path.insert(0, PLUGIN)
        for mod in [m for m in list(sys.modules) if m.split(".")[0] in (
                "skeldar_cascadeur", "maya_uebridge", "maya_sharenet", "maya_sharerecords")]:
            del sys.modules[mod]

        from skeldar_cascadeur import bridge, unreal, shared, rules
        import maya_sharenet
        from maya_uebridge import uelink

        # 1. menu entry discovered
        from csc.app import topology_controller  # noqa: F401
        gate("menu name", bridge.name() == "SkeldarAnim.Bridge", bridge.name())

        # 2. window opens and a second press raises the same one
        win = bridge.run(scene)
        win2 = bridge.run(scene)
        gate("window opens once", win is win2 and win.isVisible(), win.objectName())

        # 3. Unreal list
        brd = bridge.wire(OUT)
        status = brd.refresh()
        gate("unreal list", len(brd.records) > 0, status)
        clip = next((r for r in brd.records if "Walk" in r.name), brd.records[0])
        results["notes"].append("clip " + clip.name + " frames " + str(clip.frames))

        # 4. import into a new tab keeps the frame count
        msg = brd.import_clips([clip])
        gate("import new tab", "new tab" in msg, msg)
        frames = brd.cascade.animation_frames()
        gate("import frames", frames is not None and clip.frames is not None
             and abs(int(frames) - int(clip.frames)) <= 1, (frames, clip.frames))

        # 5. sandbox uasset: duplicate the clip, export into it, read back
        dup_src = ("import unreal\n"
                   "src = %r\n"
                   "dst = %r\n"
                   "unreal.EditorAssetLibrary.duplicate_asset(src, dst)\n"
                   "print(unreal.EditorAssetLibrary.does_asset_exist(dst))\n") % (
                       clip.package, SANDBOX + "AS_CascadeVerify")
        sandbox_pkg = SANDBOX + "AS_CascadeVerify"
        rec = type(clip)(name="AS_CascadeVerify", package=sandbox_pkg, skeleton=clip.skeleton,
                         frames=clip.frames, length=clip.length, fps=clip.fps,
                         source="unreal", path="", clip="", fmt="")
        brd.target = rec
        # Duplicate the sandbox through the same editor link the bridge uses.
        from maya_uebridge import uescripts
        dup_out = os.path.join(OUT, "dup.json")
        uelink.run_script(uescripts.list_script(dup_out, "/Game"), dup_out)  # warm the link
        brd.content_dir = brd.content_dir or ""
        gate("sandbox placeholder", True, "duplicate is run in the next step")

        results["notes"].append("export/reimport on the sandbox is the next gate; "
                                "its duplicate is made by the editor's script below")
    except Exception:
        results["gates"].append({"name": "run", "ok": False, "detail": traceback.format_exc()})

    with open(RESULT, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)
    print("verify written", RESULT, "failed:",
          sum(1 for g in results["gates"] if not g["ok"]))
```

The script above is the skeleton of the verify; complete it in Step 3b before running. Replace the placeholder gate ("sandbox placeholder") with the real steps below, and do not run it until they are there:

- **Duplicate the sandbox asset** through the editor (`uelink.run_script` with a source that calls `unreal.EditorAssetLibrary.duplicate_asset(clip.package, sandbox_pkg)` and writes `{ok, exists}` to its out file). Gate: `exists` is true.
- **Export/write-back round trip:** `brd.export_to_uasset(rec, project=None)` with the sandbox uasset path resolved through `brd.content_dir` (set it from `brd.refresh()`'s listing). The answer must NOT contain "did NOT change" and must contain "reimported and saved". Gate: both.
- **Read-only:** before the export, `os.chmod(uasset_path, stat.S_IREAD)`; the answer must contain "read-only cleared" and the file must be writable afterwards. Gate: both.
- **Shared to a TEST topic:** temporarily set `maya_sharenet.TOPIC = TEST_TOPIC` (restore it in `finally`), then `brd.send_to_shared("verify", "verify-bot")`. Gate: the status starts with "sent verify"; then GET `https://ntfy.sh/<TEST_TOPIC>/json?poll=1` and check it holds a `sending` and a `ready` record. Gate: both states present.
- **Cleanup:** delete the sandbox asset through the editor (`unreal.EditorAssetLibrary.delete_asset(sandbox_pkg)`); gate: `does_asset_exist` is false. Restore `maya_sharenet.TOPIC`. Gate: the animator's uasset is untouched (its mtime equal to the value read before the verify).

Every gate that fails must be recorded with its detail. The `finally` restores the topic and deletes the sandbox even when a gate fails.

- [ ] **Step 4: Run the verify through /run**

Write the verify to the probe folder for `exec`, then:

```powershell
$code = "exec(open(r'C:\!!!Work\MayaScripts\docs\superpowers\plans\verify_cascadeur_bridge.py', encoding='utf-8').read(), {'scene': scene, 'csc': csc, '__name__': '__verify__'})"
$body = @{ code = $code } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8765/run -Method Post -Body $body -ContentType 'application/json; charset=utf-8' -TimeoutSec 300
```

If the HTTP call times out, the verify is still running: wait and read `verify_result.json`. Do not send it twice (the `.ran` marker prevents a second run; delete the marker only to rerun deliberately).

Expected: `verify_result.json` with every gate `ok: true`. Any `ok: false` names what failed; fix the code and rerun from Step 1 of this task with the marker removed.

- [ ] **Step 5: Record the live result and commit**

Write `docs/superpowers/plans/cascadeur_bridge_live.md`: date, the gate table (name, ok, detail), the installed build's commit, the Unreal editor and Cascadeur versions shown in their About dialogs, and anything the animator must check by hand (the mouse drag of the window, the dock look). Then:

```bash
git add docs/superpowers/plans/verify_cascadeur_bridge.py docs/superpowers/plans/cascadeur_bridge_live.md
git commit -m "docs: live verify of the Cascadeur bridge"
```

---

### Task 13: Full test run, status, and what stays with the animator

**Files:** none new.

- [ ] **Step 1: Run the whole unit suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -p "test_*.py"`
Expected: every test OK, including the older uebridge, share and make_build tests. If an older test fails because of the `uassetexport` refactor, fix the import in `uassetexport.py`, not the test.

- [ ] **Step 2: Check that the staging is clean**

Run: `git status --short`
Expected: only the files of this plan are new or modified. The peer files (`SkeldarAnim/poses/...`, `CLAUDE.md`, the report files) are NOT touched by this work and are NOT staged. Never `git add -A`.

- [ ] **Step 3: Report to the animator**

Tell the animator, in Russian: what is built and committed (commit list via `git log --oneline` of this plan's commits), what the live verify proved (the table from `cascadeur_bridge_live.md`), and what stays with them:
- push and the release (`git push` and a new build are THEIR call; nothing here pushed);
- the look of the window and the mouse drag over the viewport, which the verify does not cover;
- the Shared test was sent to a test topic only; a real send to the team is their check.

Do not push. Do not publish a release.

---

## Self-Review

**1. Spec coverage**
- Bridge only inside Cascadeur (menu action) → Tasks 1, 8, 9.
- Unreal → Cascadeur import, each clip a new tab → Tasks 5, 6, 7.
- Cascadeur → uasset write-back with the Maya warnings (lost curves, read-only, unchanged, fps) → Tasks 2, 5, 7 (`_confirm_text`, `unchanged_warning`, `fps_problem`, read-only clear).
- Send to Shared → Tasks 4, 7.
- Installer B (no Maya), backup, idempotent, refuses a foreign folder → Task 10.
- Payload and release asset → Task 11.
- Testing: unit tests (Tasks 1-10), live verify in Cascadeur and Unreal (Tasks 0, 12).
- Open items of the spec: `settings.json` absolute path and restart → Task 12 Steps 1-2; PySide6 window inside Cascadeur → Task 12 (the window is opened by `bridge.run` in the live verify); round trip of names/orientation/30 fps → Task 0 probe and Task 12; csc call names → Task 0.
- Spec's "export scope = whole scene's skeleton, refused with several" → Task 7 `skeleton_problem`.
- Spec's "target = last import, changeable in the window" → Task 7 `self.target` set by import, Task 8 export uses the single selected row.
- Not built (spec's "not in v1") → nothing in the tasks touches mesh export, rigs, Maya, hotkeys.

**2. Placeholder scan**
- Task 0 and Task 6 depend on the probe results. They are explicit dependencies with the exact recording file, not open placeholders; the code in Task 6 shows the call shapes from the stubs, and the probe either confirms or replaces `JOINT_TYPE` and the lookups.
- Task 12 Step 3 is a skeleton with a required completion list, not a finished script. It is marked as incomplete and to be finished before running. This is the one place the plan asks the implementer to write the rest of the code from the listed steps; the gates are fully specified.
- Task 7 and Task 10 contain implementer notes that fix a known mismatch in the code shown (names of `size_text`/`upload_name`, the `archive_problems` member name). These are corrections the implementer applies before the first run, stated in the step.

**3. Type consistency**
- `records.AnimRecord` fields (name, package, skeleton, frames, length, fps, source, path, clip, fmt) are used identically in Tasks 5, 7, 8, 12.
- `Bridge` methods: `refresh(project=None)`, `import_clips(picked, project=None)`, `export_to_uasset(record=None, project=None)`, `send_to_shared(typed_name, author, project=None)` — the window (Task 8) calls them with those shapes; the fake in Task 8 matches.
- `shared.send(path, name, author, machine, net=None, now=None, progress=None)` — Task 7 calls `self.share.send(fbx, name, author, self.machine, now=self.now)`; the fake in Task 7 accepts that.
- `unreal.list_clips(out_dir, project=None, run_script=None)`, `export_clip(record, out_dir, project=None, run_script=None)`, `reimport(package, fbx, out_dir, project=None, run_script=None)` — Task 7 calls them with those shapes; Task 7's fake matches.
- `cascade` port names (`import_clip_new_tab`, `export_skeleton`, `skeleton_roots`, `animation_frames`, `scene_fps`) — defined in Task 6 and used with the same names in Tasks 7 and 12.
- `uasset_core` names (`LOST_CURVES`, `is_read_only`, `clear_read_only`, `fbx_staging_path`, `readonly_note`) — Task 2 defines them; Task 7 uses them.
- `prefs.put/get/load/save/default_path` — Task 3 defines them; Task 7 uses `prefs.put` and the test uses `prefs.get`.
- `rules` names (`skeleton_problem`, `export_refusal`, `fps_problem`, `frame_range_outward`, `clip_tab_name`, `join_status`, `NO_SKELETON`, `NO_TARGET`) — Task 1 defines them; Task 7 uses them.
- `bridge.name/description/run/wire` — Task 9 defines them; Task 12 calls `bridge.run(scene)` and `bridge.wire(OUT)`.
- `installer.install(source_zip, install_dir, settings_path, progress)` and `settings_edit(text, install_dir, package)` — Task 10 defines them; Task 12 calls `install(source_zip=...)`.

---

## Revision after the first live run (2026-10-09)

- **The window is QML, not QtWidgets.** The live run aborted the animator's
  Cascadeur (Qt6Core fast-fail 0xc0000409, event log 15:32:45): Cascadeur runs as a
  QGuiApplication, and a QWidget there kills the process. Tasks 8 and 9 are built as:
  `window.py` = `BridgeModel` (QtCore only), `view.qml` = a top-level `Window` in plain
  QtQuick, `bridge.run` = a `QQmlApplicationEngine` held on `sys`.
- **Confirm is Cascadeur's own dialog.** `cascade_io.confirm(text, on_yes)` calls
  `csc.view.DialogManager.show_buttons_dialog`; it is asynchronous. `Bridge.plan_export`
  checks everything and writes nothing; `Bridge.run_export(plan)` runs after the yes.
- **A blocked FBX export is a status line, not a silent success.** `cascade_io.export_skeleton`
  raises `EXPORT_BLOCKED` when no file appears (the licence refusal arrives as a message).
  `Bridge` returns it instead of writing to Unreal or Shared.
- **The installer checks `settings.json` before it copies the plugin**, and refuses a
  read-only file (live: the animator's `settings.json` is read-only).
- The probe answers are in `cascadeur_probe_results.md`: `of_type` is not used for roots,
  `scene_fps` is None, export needs a licence that allows FBX.
