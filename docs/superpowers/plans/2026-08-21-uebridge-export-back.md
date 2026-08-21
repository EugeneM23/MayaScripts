# UE Bridge Export-Back Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A checkouts window in the UE Animation Bridge: list my checked-out AnimSequence uassets, checkout/revert the uasset+fbx pair from Maya, and export the scene's root hierarchy back to the working FBX and reimport the uasset in the running editor.

**Architecture:** Pure decision logic goes into `vcs.py` (stdlib) and small pure helpers; the UE-side reimport is a new script in `uescripts.py`; the Maya-side FBX export is a new `animexport.py` mirroring `animimport.py`; the window and orchestration live in a new `checkouts.py`; `window.py` grows two buttons and content-dir plumbing. Spec: `docs/superpowers/specs/2026-08-21-uebridge-export-back-design.md`.

**Tech Stack:** Maya 2027 `maya.cmds`/`maya.mel` (FBX plugin), Epic Python Remote Execution, p4 CLI, stdlib. Tests: mayapy + unittest with the repo's fake-maya pattern.

## Global Constraints

- Test runner: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v` (no system Python, no pytest).
- `vcs.py`, `uescripts.py`, `records.py`, `uelink.py` stay stdlib-only — the `Purity` subprocess test in `tests/test_uebridge_records.py` enforces it.
- Every dialog is injectable (`asks=` dicts) — a modal over the command port blocks Maya (bridge note 6).
- Every UI callback goes through a `_run` that puts failures on the status line (trap 20).
- p4 exits 0 on "no such file(s)" — classify by stderr text (`vcs.classify_failure`); ztag other-open blocks are double-prefixed.
- FBX settings are global per session: reset + set explicitly before each use, never inherit (trap 33).
- The scene's frame rate and the animator's scene state are never changed by the bridge; the exporter's only scene write is the selection, restored after.
- Commit after each green task; messages follow the repo's `feat(uebridge):`/`fix(uebridge):`/`docs:` style.

---

### Task 1: vcs.py — opened files, package mapping, revert/add

**Files:**
- Modify: `maya_uebridge/vcs.py` (append after `checkout`, plus two pure helpers after `package_folder`)
- Test: `tests/test_uebridge_vcs.py` (append classes)

**Interfaces:**
- Produces: `opened_records(content_dir, run=run_p4) -> (list[dict], str)`;
  `package_of(client_file, content_dir) -> str`;
  `uasset_path_of(package, content_dir) -> str`;
  `open_action(fields) -> "edit"|"add"|"others"|""`;
  `revert(path, run=run_p4) -> str` ("" on success);
  `add(path, run=run_p4) -> str` ("" on success).
- Consumes: existing `run_p4`, `parse_ztag_records`, `classify_failure`, `plan_for`, `checkout`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_uebridge_vcs.py`:

```python
_OPENED_TWO = """\
... depotFile //atone/main/Atone/Content/Anims/AS_Walk.uasset
... clientFile C:\\p4\\Atone\\Content\\Anims\\AS_Walk.uasset
... action edit
... change default

... depotFile //atone/main/Atone/Content/Props/SM_Rock.uasset
... clientFile C:\\p4\\Atone\\Content\\Props\\SM_Rock.uasset
... action add
... change default
"""


class OpenedRecords(unittest.TestCase):

    def test_two_opened_files_arrive_as_two_records(self):
        run = lambda args, cwd: (0, _OPENED_TWO, "")
        found, failure = vcs.opened_records("C:/p4/Atone/Content", run=run)
        self.assertEqual(failure, "")
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["action"], "edit")

    def test_the_pattern_asks_for_opened_uassets_only(self):
        seen = {}
        def run(args, cwd):
            seen["args"] = args
            return (0, "", "")
        vcs.opened_records("C:/p4/Atone/Content", run=run)
        self.assertIn("-Ro", seen["args"])
        self.assertTrue(seen["args"][-1].endswith("....uasset"))

    def test_nothing_opened_is_an_empty_answer_not_a_failure(self):
        run = lambda args, cwd: (0, "", "... - no such file(s).\n")
        found, failure = vcs.opened_records("C:/p4/x", run=run)
        self.assertEqual((found, failure), ([], ""))

    def test_a_dead_p4_is_a_failure(self):
        run = lambda args, cwd: (None, "", "p4 timed out - server unreachable?")
        found, failure = vcs.opened_records("C:/p4/x", run=run)
        self.assertEqual(found, [])
        self.assertIn("timed out", failure)

    def test_a_record_without_action_is_dropped(self):
        text = "... depotFile //d/f.uasset\n... clientFile C:\\d\\f.uasset\n"
        run = lambda args, cwd: (0, text, "")
        found, _ = vcs.opened_records("C:/d", run=run)
        self.assertEqual(found, [])


class PackageMapping(unittest.TestCase):

    CONTENT = "C:\\p4\\Atone\\Content"

    def test_a_content_file_maps_to_its_game_package(self):
        self.assertEqual(
            vcs.package_of("C:\\p4\\Atone\\Content\\A\\B\\AS_X.uasset",
                           self.CONTENT),
            "/Game/A/B/AS_X")

    def test_case_and_separators_do_not_matter(self):
        self.assertEqual(
            vcs.package_of("c:/P4/atone/content/A/AS_X.uasset", self.CONTENT),
            "/Game/A/AS_X")

    def test_a_file_outside_content_maps_to_nothing(self):
        self.assertEqual(vcs.package_of("C:\\elsewhere\\AS_X.uasset",
                                        self.CONTENT), "")

    def test_empty_inputs_map_to_nothing(self):
        self.assertEqual(vcs.package_of("", self.CONTENT), "")
        self.assertEqual(vcs.package_of("C:\\x.uasset", ""), "")

    def test_the_inverse_builds_the_local_uasset_path(self):
        path = vcs.uasset_path_of("/Game/A/B/AS_X", self.CONTENT)
        self.assertEqual(os.path.normcase(path),
                         os.path.normcase(self.CONTENT + "\\A\\B\\AS_X.uasset"))

    def test_the_two_directions_round_trip(self):
        package = "/Game/Prototype/Animation/AS_Y"
        path = vcs.uasset_path_of(package, self.CONTENT)
        self.assertEqual(vcs.package_of(path, self.CONTENT), package)


class OpenAction(unittest.TestCase):

    def test_untracked_needs_add(self):
        self.assertEqual(vcs.open_action({}), "add")

    def test_tracked_and_free_needs_edit(self):
        self.assertEqual(vcs.open_action({"depotFile": "//d/f"}), "edit")

    def test_already_mine_needs_nothing(self):
        self.assertEqual(
            vcs.open_action({"depotFile": "//d/f", "action": "edit"}), "")

    def test_held_by_others_is_named(self):
        self.assertEqual(
            vcs.open_action({"depotFile": "//d/f", "otherOpen0": "a@b"}),
            "others")


class RevertCall(unittest.TestCase):

    def test_a_reverted_edit_is_success(self):
        run = lambda args, cwd: (0, "//d/f#3 - was edit, reverted\n", "")
        self.assertEqual(vcs.revert("C:/d/f", run=run), "")

    def test_a_reverted_add_is_success(self):
        run = lambda args, cwd: (0, "//d/f#1 - was add, abandoned\n", "")
        self.assertEqual(vcs.revert("C:/d/f", run=run), "")

    def test_not_opened_is_already_the_goal_state(self):
        run = lambda args, cwd: (1, "", "f - file(s) not opened on this client.\n")
        self.assertEqual(vcs.revert("C:/d/f", run=run), "")

    def test_a_dead_p4_is_reported(self):
        run = lambda args, cwd: (None, "", "p4.exe not found - is Perforce installed?")
        self.assertIn("p4", vcs.revert("C:/d/f", run=run))


class AddCall(unittest.TestCase):

    def test_opened_for_add_is_success(self):
        run = lambda args, cwd: (0, "//d/f#1 - opened for add\n", "")
        self.assertEqual(vcs.add("C:/d/f", run=run), "")

    def test_already_opened_for_add_is_success(self):
        run = lambda args, cwd: (0, "//d/f - currently opened for add\n", "")
        self.assertEqual(vcs.add("C:/d/f", run=run), "")

    def test_an_existing_depot_file_falls_back_to_edit(self):
        calls = []
        def run(args, cwd):
            calls.append(args[0] if args[0] != "-ztag" else args[1])
            if args[0] == "add":
                return (0, "", "//d/f - can't add existing file\n")
            return (0, "//d/f#3 - opened for edit\n", "")
        self.assertEqual(vcs.add("C:/d/f", run=run), "")
        self.assertIn("edit", calls)

    def test_a_dead_p4_is_reported(self):
        run = lambda args, cwd: (None, "", "p4 timed out - server unreachable?")
        self.assertIn("timed out", vcs.add("C:/d/f", run=run))
```

(The file already imports `os`, `unittest` and `vcs`; check its header and only add missing imports.)

- [ ] **Step 2: Run to verify the new tests fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_vcs -v`
Expected: FAIL/ERROR with `AttributeError: ... has no attribute 'opened_records'` (and friends). Do **not** use `2>&1` in PowerShell 5.1.

- [ ] **Step 3: Implement** — in `maya_uebridge/vcs.py`. After `package_folder`, add the two pure path mappers:

```python
def package_of(client_file, content_dir):
    """The /Game package of a file under the project's Content dir, "" when it
    is not under it. Case-insensitive: Windows paths arrive in mixed case."""
    if not client_file or not content_dir:
        return ""
    node = os.path.normpath(client_file)
    prefix = os.path.normpath(content_dir) + os.sep
    if not os.path.normcase(node).startswith(os.path.normcase(prefix)):
        return ""
    relative = os.path.splitext(node[len(prefix):])[0]
    return "/Game/" + relative.replace(os.sep, "/")


def uasset_path_of(package, content_dir):
    """/Game/A/B/AS_X -> <content_dir>/A/B/AS_X.uasset. Pure inverse of
    `package_of` (modulo case, which Windows does not keep anyway)."""
    text = (package or "").replace("\\", "/")
    if text.lower().startswith("/game/"):
        text = text[len("/game/"):]
    parts = [part for part in text.split("/") if part]
    return os.path.join(content_dir, *parts) + ".uasset"
```

After `plan_for`, the open-verb decision:

```python
def open_action(fields):
    """Which p4 verb opens this file for the pair: "edit", "add", "others"
    (held exclusively elsewhere - the caller decides what to say), or ""
    when it is already opened by me."""
    decision = plan_for(fields)
    if decision["kind"] == "untracked":
        return "add"
    if decision["kind"] == "mine":
        return ""
    if decision["kind"] == "others":
        return "others"
    return "edit"
```

After `checkout`, the three runners:

```python
def opened_records(content_dir, run=run_p4):
    """(records, failure): every file opened in the current workspace under
    the project's Content dir (`fstat -Ro`), one call - `p4 opened` answers
    depot paths only and would need a `where` per file. Records without an
    action are not opened and are dropped. Nothing opened is ([], "")."""
    pattern = os.path.join(content_dir, "....uasset")
    code, out, err = run(["-ztag", "fstat", "-Ro", pattern], content_dir)
    if code is None:
        return [], err or "p4 failed"
    failure = classify_failure(err, code)
    if failure:
        return [], failure
    return [record for record in parse_ztag_records(out)
            if record.get("clientFile") and record.get("action")], ""


def revert(path, run=run_p4):
    """p4 revert; "" on success. "not opened" is success too - nothing opened
    is exactly the state a revert asks for. Reverting an add abandons the open
    and leaves the file on disk, which is what the fbx invariant wants."""
    code, out, err = run(["revert", path], os.path.dirname(path))
    if code is None:
        return err or "p4 failed"
    low = (out or "").lower()
    if "reverted" in low or "abandoned" in low:
        return ""
    if "not opened" in (err or "").lower():
        return ""
    failure = classify_failure(err, code)
    return failure or "p4 revert did not revert the file"


def add(path, run=run_p4):
    """p4 add; "" on success. "can't add existing file" means a stale fstat
    called the wrong verb - self-heal with the edit instead of reporting."""
    code, out, err = run(["add", path], os.path.dirname(path))
    if code is None:
        return err or "p4 failed"
    low = ((out or "") + " " + (err or "")).lower()
    if "opened for add" in low:
        return ""
    if "can't add existing file" in low:
        return checkout(path, run)
    failure = classify_failure(err, code)
    return failure or "p4 add did not open the file"
```

- [ ] **Step 4: Run the module's tests, then the purity test**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_vcs tests.test_uebridge_records -v`
Expected: PASS (purity still clean — the additions import nothing new).

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/vcs.py tests/test_uebridge_vcs.py
git commit -m "feat(uebridge): p4 opened listing, package mapping, revert and add"
```

---

### Task 2: uescripts.py — content_dir in the listing, the reimport script

**Files:**
- Modify: `maya_uebridge/uescripts.py`
- Test: `tests/test_uebridge_scripts.py` (append)

**Interfaces:**
- Produces: `reimport_script(out_path, package, fbx_path) -> str`; the list
  reply and cache gain a `content_dir` key.
- Consumes: existing `_REPLY_TAIL`, `MARKER`.

- [ ] **Step 1: Failing tests** — append to `tests/test_uebridge_scripts.py` (it already imports `uescripts`; follow its existing assertions style):

```python
class ReimportScript(unittest.TestCase):

    def script(self):
        return uescripts.reimport_script(
            "C:\\temp\\out.json", "/Game/Anims/AS_X",
            "C:\\src\\Exports\\AS_X.fbx")

    def test_paths_are_json_encoded_not_pasted(self):
        self.assertIn(json.dumps("C:\\src\\Exports\\AS_X.fbx"), self.script())

    def test_the_reimport_is_pointed_at_our_fbx_without_asking(self):
        text = self.script()
        self.assertIn("set_reimport_paths", text)
        self.assertIn("ask_new_file=False", text)

    def test_the_asset_is_saved_after_the_reimport(self):
        self.assertIn("save_asset", self.script())

    def test_a_missing_asset_is_guarded_before_use(self):
        """Trap 24: a null object crashes the editor, it does not raise."""
        self.assertIn("could not load asset", self.script())

    def test_the_reply_tail_is_present(self):
        text = self.script()
        self.assertIn("finally:", text)
        self.assertIn(json.dumps(uescripts.MARKER), text)


class ListScriptContentDir(unittest.TestCase):

    def test_the_listing_reports_the_content_dir(self):
        text = uescripts.list_script("C:/out.json")
        self.assertIn("project_content_dir", text)
        self.assertIn("content_dir", text)
```

- [ ] **Step 2: Run to verify failure**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_scripts -v`
Expected: FAIL — `reimport_script` missing, `project_content_dir` absent.

- [ ] **Step 3: Implement.** In `_LIST_HEAD`, extend the result init line to include `"content_dir": ""` and add, right after `result["project"] = ...`:

```python
    result["content_dir"] = unreal.Paths.convert_relative_path_to_full(
        unreal.Paths.project_content_dir())
```

Add the reimport head and builder after `export_script`:

```python
_REIMPORT_HEAD = '''\
import json
import os
import traceback

import unreal

_OUT = %(out_path)s
_PACKAGE = %(package)s
_FBX = %(fbx_path)s

result = {"ok": False, "error": "", "saved": False,
          "frames": None, "length": None, "notes": []}


def attempt(call, default=None):
    """Engine APIs move between versions; a miss must not abort the run."""
    try:
        return call()
    except Exception:
        return default


try:
    anim = unreal.load_asset(_PACKAGE)
    if anim is None:
        raise RuntimeError("could not load asset: " + str(_PACKAGE))
    if not os.path.isfile(_FBX):
        raise RuntimeError("no FBX at " + str(_FBX))

    subsystem = attempt(
        lambda: unreal.get_editor_subsystem(unreal.ReimportSubsystem))
    if subsystem is None:
        raise RuntimeError("no ReimportSubsystem on this engine build")

    # Point the stored import source at OUR fbx first: ask_new_file=False
    # plus an explicit path is what keeps the editor from raising a file
    # dialog nobody can click (the trap-23/24 family).
    if attempt(lambda: subsystem.set_reimport_paths(anim, [_FBX]) or True) is None:
        result["notes"].append("set_reimport_paths failed")

    ran = attempt(lambda: subsystem.reimport(
        anim, ask_new_file=False, load_new_file=False, preferred_file=_FBX))
    if not ran:
        raise RuntimeError("the editor refused the reimport - check its "
                           "Output Log (returned " + str(ran) + ")")

    result["saved"] = bool(attempt(lambda: unreal.EditorAssetLibrary.save_asset(
        _PACKAGE, only_if_is_dirty=False)))

    length = attempt(lambda: float(anim.get_play_length()))
    if length is None:
        length = attempt(lambda: float(anim.get_editor_property("sequence_length")))
    result["length"] = length

    frames = attempt(lambda: int(anim.get_editor_property("number_of_sampled_keys")))
    if frames is None:
        frames = attempt(lambda: int(anim.get_editor_property("number_of_frames")))
    result["frames"] = frames

    result["ok"] = True
'''


def reimport_script(out_path, package, fbx_path):
    """Source that reimports one AnimSequence from `fbx_path` and saves it.

    The uasset must already be writable (checked out) - this script does not
    touch Perforce; the bridge did that before calling it.
    """
    values = {"out_path": json.dumps(out_path),
              "package": json.dumps(package),
              "fbx_path": json.dumps(fbx_path),
              "marker": json.dumps(MARKER)}
    return (_REIMPORT_HEAD % values) + (_REPLY_TAIL % values)
```

- [ ] **Step 4: Run to verify pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_scripts tests.test_uebridge_records -v`
Expected: PASS (purity intact).

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/uescripts.py tests/test_uebridge_scripts.py
git commit -m "feat(uebridge): reimport script and content_dir in the listing reply"
```

---

### Task 3: animexport.py — the Maya-side FBX export

**Files:**
- Create: `maya_uebridge/animexport.py`
- Test: `tests/test_uebridge_export.py` (new file, fake-maya pattern from `tests/test_uebridge_window.py`)

**Interfaces:**
- Produces: `resolve_root() -> str` (raises with `NO_TARGET_MESSAGE`/`AMBIGUOUS_TARGET_MESSAGE`);
  `union_range((ast, aet), (mn, mx)) -> (start, end)` (pure);
  `outside_keys_warning(times, start, end) -> str` (pure);
  `export_line(name, info) -> str` (pure);
  `export_command(fbx_path) -> str` (pure);
  `export_hierarchy(fbx_path, root=None, start=None, end=None) -> info dict`
  with keys `root`, `joints`, `start`, `end`, `warning`, `notes`.
- Consumes: `animimport.ensure_fbx_plugin`, `animimport.skeleton_roots`,
  `animimport.selected_roots`, `animimport.choose_target_root`,
  `animimport.joints_under`.

- [ ] **Step 1: Failing tests** — create `tests/test_uebridge_export.py`:

```python
"""Tests for the export-back direction: the pure range/wording logic and the
window-free parts of the checkouts machinery."""

import sys
import types
import unittest


def _install_fake_maya():
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_uebridge import animexport  # noqa: E402


class UnionRange(unittest.TestCase):

    def test_equal_ranges_stay_put(self):
        self.assertEqual(animexport.union_range((0, 60), (0, 60)), (0, 60))

    def test_a_zoomed_in_timeline_does_not_trim_the_clip(self):
        """Trap 38: the visible slider narrowed inside the animation range
        must not narrow the export."""
        self.assertEqual(animexport.union_range((0, 120), (30, 50)), (0, 120))

    def test_a_widened_slider_widens_the_export(self):
        self.assertEqual(animexport.union_range((0, 60), (-10, 80)), (-10, 80))


class OutsideKeysWarning(unittest.TestCase):

    def test_keys_inside_say_nothing(self):
        self.assertEqual(animexport.outside_keys_warning([0, 30, 60], 0, 60), "")

    def test_no_keys_say_nothing(self):
        self.assertEqual(animexport.outside_keys_warning([], 0, 60), "")

    def test_keys_outside_are_counted_and_placed(self):
        text = animexport.outside_keys_warning([-5, 0, 60, 70, 80], 0, 60)
        self.assertIn("3", text)
        self.assertIn("-5", text)


class ExportCommand(unittest.TestCase):

    def test_backslashes_become_forward_slashes(self):
        self.assertEqual(animexport.export_command("C:\\a\\b.fbx"),
                         'FBXExport -f "C:/a/b.fbx" -s;')


class ExportLine(unittest.TestCase):

    def info(self, **over):
        info = {"root": "root", "joints": 93, "start": 0.0, "end": 62.0,
                "warning": ""}
        info.update(over)
        return info

    def test_names_the_clip_the_bones_and_the_range(self):
        line = animexport.export_line("AS_Walk", self.info())
        self.assertIn("AS_Walk", line)
        self.assertIn("93", line)
        self.assertIn("0-62", line)

    def test_a_warning_rides_along(self):
        line = animexport.export_line("A", self.info(warning="2 key(s) outside"))
        self.assertIn("outside", line)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_export -v`
Expected: ERROR — `maya_uebridge.animexport` does not exist.

- [ ] **Step 3: Implement** — create `maya_uebridge/animexport.py`:

```python
"""Sending the scene's skeleton back out as FBX.

The mirror of `animimport`: same plugin, the same guarded-option pattern, and
the same rule - the animator's scene is never changed. Bake-on-export samples
the rigged bones into the file, so the OverRig rig stays untouched and there
is nothing to restore afterwards; the one thing written is the selection, and
it is put back.
"""

import os

import maya.cmds as cmds
import maya.mel as mel

from maya_uebridge import animimport

NO_TARGET_MESSAGE = ("no skeleton in the scene to export - select a joint of "
                     "the one you mean")
AMBIGUOUS_TARGET_MESSAGE = ("several skeletons in the scene - select a joint "
                            "of the one to export")

# Bones only, rig excluded: constraints and input connections would drag the
# OverRig knots into the file, and a UE animation reimport reads none of it.
# Reset first, then set every flag explicitly - FBX settings are global for
# the session and inheriting whatever ran before is trap 33.
_EXPORT_OPTIONS = (
    "FBXExportBakeComplexAnimation -v true",
    "FBXExportBakeResampleAnimation -v true",
    "FBXExportConstraints -v false",
    "FBXExportInputConnections -v false",
    "FBXExportSkins -v false",
    "FBXExportShapes -v false",
    "FBXExportCameras -v false",
    "FBXExportLights -v false",
    "FBXExportEmbeddedTextures -v false",
    "FBXExportSkeletonDefinitions -v true",
    "FBXExportUpAxis y",
)


def union_range(animation, playback):
    """The exported range: animation range UNION playback range. Pure.

    An export clipped to a zoomed-in timeline trims the clip (trap 38), so
    the outer animation range always counts; the union also covers a slider
    dragged wider than the animation range.
    """
    return (min(animation[0], playback[0]), max(animation[1], playback[1]))


def outside_keys_warning(times, start, end):
    """Text when the hierarchy carries keys outside the exported range -
    warned, not silently included: a stray key at frame -200 must not
    stretch the clip. Pure."""
    outside = [t for t in (times or []) if t < start or t > end]
    if not outside:
        return ""
    return ("{0} key(s) outside the exported range {1:g}-{2:g} are not in "
            "the clip (first at {3:g})".format(
                len(outside), start, end, min(outside)))


def export_line(name, info):
    """What the status says about the export itself. Pure."""
    head = "{0}: {1} bones, frames {2:g}-{3:g}".format(
        name, info.get("joints", 0), info.get("start", 0), info.get("end", 0))
    if info.get("warning"):
        return "{0}  |  {1}".format(head, info["warning"])
    return head


def export_command(fbx_path):
    """MEL for the FBX plugin's own exporter. -s exports the selection (the
    skeleton root; children ride along); forward slashes because a backslash
    inside a MEL string starts an escape."""
    return 'FBXExport -f "{0}" -s;'.format(fbx_path.replace("\\", "/"))


def resolve_root():
    """The skeleton the export takes - the import merge's own rule (selection
    wins, else the only plain skeleton, else the one named root), so the two
    directions of the bridge always agree about "the" character."""
    roots = animimport.skeleton_roots()
    root = animimport.choose_target_root(roots, animimport.selected_roots())
    if root is None:
        raise RuntimeError(AMBIGUOUS_TARGET_MESSAGE if roots
                           else NO_TARGET_MESSAGE)
    return root


def export_range():
    return union_range(
        (cmds.playbackOptions(query=True, animationStartTime=True),
         cmds.playbackOptions(query=True, animationEndTime=True)),
        (cmds.playbackOptions(query=True, minTime=True),
         cmds.playbackOptions(query=True, maxTime=True)))


def _apply_export_options(start, end):
    """Best-effort like the import side: an unknown flag on some Maya build
    must not stop the export, but nothing is inherited either."""
    missing = []
    try:
        mel.eval("FBXResetExport")
    except Exception:
        missing.append("FBXResetExport")
    options = _EXPORT_OPTIONS + (
        "FBXExportBakeComplexStart -v {0:g}".format(start),
        "FBXExportBakeComplexEnd -v {0:g}".format(end),
        "FBXExportBakeComplexStep -v 1",
    )
    for option in options:
        try:
            mel.eval(option + ";")
        except Exception:
            missing.append(option.split(" ", 1)[0])
    return missing


def export_hierarchy(fbx_path, root=None, start=None, end=None):
    """Write `root`'s hierarchy (resolved when not given) to `fbx_path` with
    the animation baked in, and report what was written."""
    animimport.ensure_fbx_plugin()
    if root is None:
        root = resolve_root()
    if start is None or end is None:
        start, end = export_range()

    folder = os.path.dirname(fbx_path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)

    joints = animimport.joints_under(root)
    times = cmds.keyframe(joints, query=True, timeChange=True) or []

    notes = _apply_export_options(start, end)
    previous = cmds.ls(selection=True, long=True) or []
    cmds.select(root, replace=True)
    try:
        mel.eval(export_command(fbx_path))
    finally:
        if previous:
            cmds.select(previous, replace=True)
        else:
            cmds.select(clear=True)

    if not os.path.isfile(fbx_path) or os.path.getsize(fbx_path) == 0:
        raise RuntimeError("the exporter wrote nothing at {0}".format(fbx_path))

    return {"root": root.split("|")[-1],
            "joints": len(joints),
            "start": start, "end": end,
            "warning": outside_keys_warning(times, start, end),
            "notes": notes}
```

- [ ] **Step 4: Run to verify pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_export -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/animexport.py tests/test_uebridge_export.py
git commit -m "feat(uebridge): FBX export of the skeleton hierarchy, bake-on-export"
```

---

### Task 4: window.py — content_dir through cache and state

**Files:**
- Modify: `maya_uebridge/window.py` (`cache_payload`, `load_cache`, `_STATE`, `refresh`, `show_window`)
- Test: `tests/test_uebridge_window.py` (append to `CacheRoundTrip`)

**Interfaces:**
- Produces: `cache_payload(record_list, project="", choice="", content_dir="")`;
  `load_cache() -> (records, project, choice, content_dir)`;
  `_STATE["content_dir"]`.
- Consumes: the `content_dir` key Task 2 put in the editor reply.

- [ ] **Step 1: Failing tests** — append to `CacheRoundTrip` in `tests/test_uebridge_window.py`:

```python
    def test_the_cache_keeps_the_content_dir(self):
        cached = window.cache_payload([], content_dir="C:/proj/Content")
        self.assertEqual(cached["content_dir"], "C:/proj/Content")

    def test_an_old_cache_without_content_dir_still_loads(self):
        """load_cache must answer four values even for a phase-1 cache file."""
        payload = window.cache_payload([])
        payload.pop("content_dir")
        self.assertEqual(payload.get("content_dir", ""), "")
```

- [ ] **Step 2: Run to verify failure**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_window -v
Expected: FAIL — `cache_payload` has no `content_dir` parameter.

- [ ] **Step 3: Implement.** In `window.py`:
- `_STATE` init gains `"content_dir": ""`.
- `cache_payload(record_list, project="", choice="", content_dir="")` and the dict gains `"content_dir": content_dir`.
- `load_cache` returns `(..., payload.get("content_dir", ""))` — four values; the failure branch returns `[], "", "", ""`.
- In `refresh()`, after `_STATE["project"] = ...`:

```python
    _STATE["content_dir"] = payload.get("content_dir", "")
    save_cache(found, _STATE["project"], chosen, _STATE["content_dir"])
```

(replacing the old `save_cache(found, _STATE["project"], chosen)` line), and `save_cache` gains the `content_dir=""` parameter passed through to `cache_payload`.
- In `show_window()`, unpack four: `cached, project, choice, content_dir = load_cache()` and set `_STATE["content_dir"] = content_dir`.

- [ ] **Step 4: Run to verify pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_window -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/window.py tests/test_uebridge_window.py
git commit -m "feat(uebridge): content dir travels through the listing cache"
```

---

### Task 5: checkouts.py — rows, pair checkout, revert, export orchestration

**Files:**
- Create: `maya_uebridge/checkouts.py`
- Test: `tests/test_uebridge_export.py` (append)

**Interfaces:**
- Produces: `CheckoutRow` namedtuple `(record, client_file, action, fbx, fbx_path)`;
  `anim_checkouts(opened, content_dir, record_list) -> [(record, client_file, action)]` (pure);
  `fbx_state(name, root, run) -> (state, path)` with state `"ok"|"depot"|"missing"`;
  `format_row(row) -> str` (pure); `count_line(n) -> str` (pure);
  `reimport_line(payload) -> str` (pure);
  `checkout_pair(record, asks=None) -> str`;
  `revert_pair(row, asks=None) -> str`;
  `export_to(row, asks=None) -> str`;
  `load_rows(run=vcs.run_p4) -> (rows, failure)`;
  `content_dir() -> str`; `open_for_export()`; `show_window(rows=None)`.
- Consumes: Task 1's vcs additions, Task 2's `reimport_script`, Task 3's
  `animexport`, Task 4's `_STATE["content_dir"]`, and `window`'s existing
  `_vcs_target`, `_saved_root`, `_pick_root`, `_apply_root`, `_ask_others`,
  `_ask_failure`, `temp_folder`, `project_choice`, `_selected_record`,
  `_status`.

- [ ] **Step 1: Failing tests** — append to `tests/test_uebridge_export.py`:

```python
from maya_uebridge import checkouts, records, vcs  # noqa: E402


def _record(name="AS_Walk", package="/Game/Anims/AS_Walk"):
    return records.AnimRecord(name=name, package=package, skeleton="SK",
                              frames=60, length=2.0, fps=30.0)


class AnimCheckouts(unittest.TestCase):

    CONTENT = "C:\\p4\\Atone\\Content"

    def opened(self, client, action="edit"):
        return {"depotFile": "//d/x", "clientFile": client, "action": action}

    def test_an_opened_animsequence_is_matched_to_its_record(self):
        rows = checkouts.anim_checkouts(
            [self.opened(self.CONTENT + "\\Anims\\AS_Walk.uasset")],
            self.CONTENT, [_record()])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0].name, "AS_Walk")
        self.assertEqual(rows[0][2], "edit")

    def test_a_non_animation_uasset_is_dropped(self):
        """The window is about animations, not the depot."""
        rows = checkouts.anim_checkouts(
            [self.opened(self.CONTENT + "\\Props\\SM_Rock.uasset")],
            self.CONTENT, [_record()])
        self.assertEqual(rows, [])

    def test_matching_ignores_case(self):
        rows = checkouts.anim_checkouts(
            [self.opened("c:\\P4\\ATONE\\content\\anims\\as_walk.uasset")],
            self.CONTENT, [_record()])
        self.assertEqual(len(rows), 1)

    def test_rows_sort_by_name(self):
        rows = checkouts.anim_checkouts(
            [self.opened(self.CONTENT + "\\Anims\\AS_Zed.uasset"),
             self.opened(self.CONTENT + "\\Anims\\AS_Abc.uasset")],
            self.CONTENT,
            [_record("AS_Zed", "/Game/Anims/AS_Zed"),
             _record("AS_Abc", "/Game/Anims/AS_Abc")])
        self.assertEqual([r[0].name for r in rows], ["AS_Abc", "AS_Zed"])


class FormatRow(unittest.TestCase):

    def row(self, fbx="ok"):
        return checkouts.CheckoutRow(_record(), "C:\\x.uasset", "edit", fbx,
                                     "C:\\src\\AS_Walk.fbx")

    def test_a_row_names_the_animation_the_action_and_the_fbx(self):
        text = checkouts.format_row(self.row())
        self.assertIn("AS_Walk", text)
        self.assertIn("edit", text)
        self.assertIn("ok", text)

    def test_a_missing_fbx_shouts(self):
        self.assertIn("MISSING", checkouts.format_row(self.row("missing")))

    def test_rows_align(self):
        a = checkouts.format_row(self.row())
        b = checkouts.format_row(checkouts.CheckoutRow(
            _record("AS_A_Very_Much_Longer_Animation_Name_Than_That",
                    "/Game/Deep/Folder/AS_X"),
            "C:\\y.uasset", "add", "depot", ""))
        self.assertEqual(a.index("fbx "), b.index("fbx "))


class CountLine(unittest.TestCase):

    def test_zero_says_nothing_checked_out(self):
        self.assertIn("nothing", checkouts.count_line(0))

    def test_a_count_is_reported(self):
        self.assertIn("3", checkouts.count_line(3))


class ReimportLine(unittest.TestCase):

    def test_saved_with_frames(self):
        line = checkouts.reimport_line({"ok": True, "saved": True, "frames": 62})
        self.assertIn("saved", line)
        self.assertIn("62", line)

    def test_unsaved_is_loud(self):
        line = checkouts.reimport_line({"ok": True, "saved": False})
        self.assertIn("NOT saved", line)


class FbxState(unittest.TestCase):

    def test_no_root_is_unknown(self):
        state, path = checkouts.fbx_state("AS_X", "", lambda a, c: (0, "", ""))
        self.assertEqual(state, "missing")
        self.assertEqual(path, "")
```

- [ ] **Step 2: Run to verify failure**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_export -v`
Expected: ERROR — no module `maya_uebridge.checkouts`.

- [ ] **Step 3: Implement** — create `maya_uebridge/checkouts.py`:

```python
"""The checkouts window: my checked-out AnimSequence uassets, the pair
checkout (uasset+fbx together), revert, and the export back into the uasset.

The invariant this window exists for, in the user's words: «у нас не должно
быть такой ситуации что скрипт видит uasset на чекауте в перфорсе а fbx в
сорс каталоге нету» - the source fbx is the intermediary the pipeline works
through, so a checkout through the bridge always leaves the pair complete,
creating the fbx from the editor when it exists nowhere.

Every dialog is injectable (`asks=`), for the same reason as vcs.py: a modal
over the command port blocks Maya's idle queue.
"""

import collections
import os
import traceback

import maya.cmds as cmds

from maya_uebridge import animexport
from maya_uebridge import animimport
from maya_uebridge import records
from maya_uebridge import uelink
from maya_uebridge import uescripts
from maya_uebridge import vcs
from maya_uebridge import window

WINDOW = "ueBridgeCheckouts"
_LIST = "ueBridgeCheckoutsList"
_STATUS = "ueBridgeCheckoutsStatus"

_STATE = {"rows": []}

CheckoutRow = collections.namedtuple(
    "CheckoutRow", ["record", "client_file", "action", "fbx", "fbx_path"])


# ---------------------------------------------------------------- pure

def anim_checkouts(opened, content_dir, record_list):
    """Match p4's opened uassets to known AnimSequences, sorted by name.

    Anything not in the record list is dropped - the window is about
    animations, never the depot's every uasset. Pure.
    """
    by_package = dict((rec.package.lower(), rec) for rec in record_list)
    rows = []
    for fields in opened:
        package = vcs.package_of(fields.get("clientFile", ""), content_dir)
        record = by_package.get(package.lower()) if package else None
        if record is None:
            continue
        rows.append((record, fields.get("clientFile", ""),
                     fields.get("action", "")))
    rows.sort(key=lambda row: row[0].name.lower())
    return rows


def format_row(row):
    """One fixed-width line: name, folder tail, p4 action, fbx state."""
    folder = row.record.package.rsplit("/", 1)[0]
    shown = row.fbx.upper() if row.fbx == "missing" else row.fbx
    return "{0:<{1}} {2:<{3}} {4:<6} fbx {5}".format(
        records._middle(row.record.name, records.NAME_WIDTH),
        records.NAME_WIDTH,
        records._tail(folder, 30), 30,
        row.action, shown)


def count_line(count):
    if not count:
        return "nothing checked out"
    return "{0} animation uasset(s) checked out".format(count)


def reimport_line(payload):
    """What the status says about the editor's side of the export. Pure."""
    frames = payload.get("frames")
    tail = " ({0} frames)".format(frames) if frames is not None else ""
    if not payload.get("saved"):
        return "reimported, NOT saved - save it in the editor" + tail
    return "reimported and saved" + tail


# ---------------------------------------------------------------- lookups

def fbx_state(name, root, run):
    """("ok"|"depot"|"missing", path): where the прокладка is."""
    hits = vcs.find_fbx(name, root)
    if hits:
        return "ok", hits[0]
    for fields in vcs.find_fbx_depot(name, root, run):
        return "depot", fields.get("clientFile", "")
    return "missing", ""


def content_dir():
    """The project's Content folder: the cached listing first, discovery's
    pong (which carries project_root) second, "" when unknowable."""
    known = window._STATE.get("content_dir") or ""
    if known and os.path.isdir(known):
        return known
    try:
        nodes = uelink.discover_nodes()
    except uelink.UeBridgeError:
        return ""
    node = uelink.pick_node(nodes, window.project_choice()) or {}
    root = str(node.get("project_root") or "")
    if not root:
        return ""
    found = os.path.join(root, "Content")
    return found if os.path.isdir(found) else ""


def load_rows(run=vcs.run_p4):
    """(rows, failure). Needs the Content dir and the cached animation list -
    without the list nothing can be classified as an AnimSequence."""
    folder = content_dir()
    if not folder:
        return [], "no Content dir known - press Refresh in the bridge first"
    if not window._STATE.get("records"):
        return [], "no animation list - press Refresh in the bridge first"
    opened, failure = vcs.opened_records(folder, run=run)
    if failure:
        return [], failure
    matched = anim_checkouts(opened, folder, window._STATE["records"])
    root = window._saved_root()
    rows = []
    for record, client_file, action in matched:
        state, path = fbx_state(record.name, root, run)
        rows.append(CheckoutRow(record, client_file, action, state, path))
    return rows, ""


# ---------------------------------------------------------------- actions

def _fbx_from_editor(record, target):
    """Export the CURRENT animation out of the editor onto `target`, so the
    прокладка holds the uasset's pre-edit state from the moment of checkout."""
    out = os.path.join(window.temp_folder(), "export.json")
    temp = os.path.join(window.temp_folder(), "{0}.fbx".format(record.name))
    payload = uelink.run_script(
        uescripts.export_script(out, record.package, temp),
        out, project=window.project_choice())
    vcs.place(payload.get("path") or temp, target)


def checkout_pair(record, asks=None):
    """Open the uasset AND its fbx; create the fbx when it exists nowhere.
    Returns the status text. The pair is the user's pick: one changelist,
    one submit, source and asset never drift apart in the depot."""
    asks = asks or {}
    run = asks.get("run", vcs.run_p4)
    folder = content_dir()
    if not folder:
        return "no Content dir known - press Refresh first"

    uasset = vcs.uasset_path_of(record.package, folder)
    fields, failure = vcs.fstat(uasset, run)
    if failure:
        return "no checkout - " + failure
    decision = vcs.plan_for(fields)
    if decision["kind"] == "others":
        return "checked out by " + ", ".join(decision["users"])
    if decision["kind"] == "untracked":
        return "uasset is not in the depot: " + record.name
    uasset_note = "uasset already checked out"
    if decision["kind"] == "edit":
        failure = vcs.checkout(uasset, run)
        if failure:
            return "no checkout - " + failure
        uasset_note = "uasset checked out"

    resolved = window._vcs_target(record, asks)
    if resolved is None:
        return uasset_note + ", fbx cancelled"
    target, _is_new = resolved

    if not os.path.isfile(target):
        fbx_fields, failure = vcs.fstat(target, run)
        if failure:
            return "{0}, fbx unknown - {1}".format(uasset_note, failure)
        if fbx_fields.get("depotFile"):
            failure = vcs.checkout(target, run)  # sync-retry lives inside
            fbx_note = ("fbx synced and checked out" if not failure
                        else "fbx not opened - " + failure)
        else:
            _fbx_from_editor(record, target)
            failure = vcs.add(target, run)
            fbx_note = ("fbx created from the editor and added"
                        if not failure
                        else "fbx created, not added - " + failure)
    else:
        fbx_fields, failure = vcs.fstat(target, run)
        if failure:
            fbx_note = "fbx not opened - " + failure
        else:
            action = vcs.open_action(fbx_fields)
            if action == "edit":
                failure = vcs.checkout(target, run)
                fbx_note = ("fbx checked out" if not failure
                            else "fbx not opened - " + failure)
            elif action == "add":
                failure = vcs.add(target, run)
                fbx_note = ("fbx added" if not failure
                            else "fbx not added - " + failure)
            elif action == "others":
                fbx_note = ("fbx checked out by "
                            + ", ".join(vcs.other_openers(fbx_fields)))
            else:
                fbx_note = "fbx already checked out"

    return "{0}: {1}, {2}".format(record.name, uasset_note, fbx_note)


def _ask_revert(paths):
    answer = cmds.confirmDialog(
        title="Perforce revert", icon="warning",
        message="Revert discards local changes:\n\n  {0}".format(
            "\n  ".join(paths)),
        button=["Revert", "Cancel"], defaultButton="Cancel",
        cancelButton="Cancel", dismissString="Cancel")
    return answer == "Revert"


def revert_pair(row, asks=None):
    """Revert the uasset and, when we hold it, the fbx - the pair goes back
    together. The one destructive button in this window, so the one confirm."""
    asks = asks or {}
    run = asks.get("run", vcs.run_p4)
    fbx_opened = ""
    if row.fbx_path:
        fields, failure = vcs.fstat(row.fbx_path, run)
        if not failure and fields.get("action"):
            fbx_opened = row.fbx_path
    confirm = asks.get("confirm", _ask_revert)
    if not confirm([row.client_file] + ([fbx_opened] if fbx_opened else [])):
        return "revert cancelled"
    failure = vcs.revert(row.client_file, run)
    if failure:
        return "revert failed - " + failure
    note = "reverted " + row.record.name
    if fbx_opened:
        failure = vcs.revert(fbx_opened, run)
        note += (", fbx reverted" if not failure
                 else ", fbx NOT reverted - " + failure)
    return note


def export_to(row, asks=None):
    """The whole reverse trip for one checkout: scene -> temp fbx -> p4 ->
    working fbx -> reimport in the editor. Returns the status text.

    Order is the import direction's, for the same reasons: dialogs about
    paths first (a cancel costs nothing), the export to a temp file (a failed
    export must not destroy the previous working file), p4 only after a new
    file exists, the editor last.
    """
    asks = asks or {}
    run = asks.get("run", vcs.run_p4)
    record = row.record
    resolved = window._vcs_target(record, asks)
    if resolved is None:
        return "export cancelled"
    target, _is_new = resolved

    temp = os.path.join(window.temp_folder(),
                        "{0}.export.fbx".format(record.name))
    info = animexport.export_hierarchy(temp)

    proceed, note = vcs.prepare_target(
        target, asks.get("others", window._ask_others),
        asks.get("failure", window._ask_failure), run=run)
    if not proceed:
        return "export cancelled - {0} untouched".format(
            os.path.basename(target))
    vcs.place(temp, target)
    if note == "not in depot":
        failure = vcs.add(target, run)
        note = "added" if not failure else "no add - " + failure

    out = os.path.join(window.temp_folder(), "reimport.json")
    payload = uelink.run_script(
        uescripts.reimport_script(out, record.package, target),
        out, project=window.project_choice())

    suffix = vcs.status_suffix(target, window._saved_root(), False, note)
    parts = [animexport.export_line(record.name, info), suffix,
             reimport_line(payload),
             # Same rule as import: the scene's rate is never changed, a
             # mismatch is said out loud - UE will resample the clip.
             animimport.fps_warning(record.fps, animimport.scene_fps())]
    return "  |  ".join(part for part in parts if part)


# ---------------------------------------------------------------- window

def _status(text):
    if cmds.text(_STATUS, exists=True):
        cmds.text(_STATUS, edit=True, label=text)
    else:
        window._status(text)


def _run(action, busy=None):
    """Same shape as the main window's: a failure lands on the status line,
    not in the Script Editor (trap 20)."""
    if busy:
        _status(busy)
        cmds.refresh()
    try:
        action()
    except uelink.UeBridgeError as error:
        text = str(error).strip()
        _status(text.splitlines()[0] if text else "failed")
        print("[uebridge] {0}".format(error))
    except Exception as error:
        _status("{0}: {1}".format(type(error).__name__, error))
        print(traceback.format_exc())


def _selected_row():
    indices = cmds.textScrollList(_LIST, query=True,
                                  selectIndexedItem=True) or []
    if not indices:
        return None
    index = indices[0] - 1
    if 0 <= index < len(_STATE["rows"]):
        return _STATE["rows"][index]
    return None


def _populate(rows):
    _STATE["rows"] = rows
    cmds.textScrollList(_LIST, edit=True, removeAll=True)
    for row in rows:
        cmds.textScrollList(_LIST, edit=True, append=format_row(row))
    _status(count_line(len(rows)))


def _refresh_pressed():
    rows, failure = load_rows()
    _populate(rows)
    if failure:
        _status(failure)


def _export_pressed():
    row = _selected_row()
    if row is None:
        _status("select a checked-out animation first")
        return
    line = export_to(row)
    _refresh_pressed()   # the fbx column may have changed
    _status(line)


def _revert_pressed():
    row = _selected_row()
    if row is None:
        _status("select a checked-out animation first")
        return
    line = revert_pair(row)
    _refresh_pressed()   # the row is usually gone now
    _status(line)


def _ask_save_path():
    kwargs = {"fileMode": 0, "dialogStyle": 2, "caption": "Save FBX as",
              "fileFilter": "FBX Files (*.fbx)"}
    saved = window._saved_root()
    if saved and os.path.isdir(saved):
        kwargs["startingDirectory"] = saved
    picked = cmds.fileDialog2(**kwargs) or []
    return picked[0] if picked else ""


def open_for_export():
    """The main window's Export press: the checkouts window when anything is
    checked out, a plain save-as export when nothing is («если файлов на
    чекауте нету ... пользователь укажет путь для сохранения fbx»)."""
    root = window._saved_root()
    if not root or not os.path.isdir(root):
        root = window._pick_root()
        if not root:
            window._status("export needs the source project folder")
            return
        window._apply_root(root)
    rows, failure = load_rows()
    if failure:
        window._status(failure)
        return
    if not rows:
        path = _ask_save_path()
        if not path:
            window._status("export cancelled")
            return
        info = animexport.export_hierarchy(path)
        window._status("no checkouts - " + animexport.export_line(
            os.path.basename(path), info))
        return
    show_window(rows)


def show_window(rows=None):
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    cmds.window(WINDOW, title="UE Checkouts", widthHeight=(700, 340))
    form = cmds.formLayout(numberOfDivisions=100)

    header = cmds.text(
        label="AnimSequence uassets checked out in this workspace",
        align="left")
    scroll = cmds.textScrollList(
        _LIST, allowMultiSelection=False, font="fixedWidthFont",
        doubleClickCommand=lambda *_: _run(_export_pressed,
                                           busy="exporting..."))
    refresh_button = cmds.button(
        label="Refresh", width=80,
        command=lambda *_: _run(_refresh_pressed, busy="asking p4..."))
    revert_button = cmds.button(
        label="Revert", width=80,
        command=lambda *_: _run(_revert_pressed))
    export_button = cmds.button(
        label="EXPORT", height=30, width=140,
        command=lambda *_: _run(_export_pressed, busy="exporting..."))
    status = cmds.text(_STATUS, label="", align="left")

    cmds.formLayout(
        form, edit=True,
        attachForm=[
            (header, "top", 8), (header, "left", 8), (header, "right", 8),
            (scroll, "left", 8), (scroll, "right", 8),
            (refresh_button, "left", 8),
            (export_button, "right", 8),
            (status, "left", 8), (status, "right", 8), (status, "bottom", 8),
        ],
        attachControl=[
            (scroll, "top", 8, header),
            (scroll, "bottom", 8, export_button),
            (refresh_button, "bottom", 6, status),
            (revert_button, "bottom", 6, status),
            (revert_button, "left", 6, refresh_button),
            (export_button, "bottom", 6, status),
        ])

    if rows is None:
        _refresh_pressed()
    else:
        _populate(rows)
    cmds.showWindow(WINDOW)
    return WINDOW
```

- [ ] **Step 4: Run to verify pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_export -v`
Expected: PASS. (The import of `checkouts` pulls `window` in under the fake maya — that is fine in this test file; the purity test never imports `checkouts`.)

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/checkouts.py tests/test_uebridge_export.py
git commit -m "feat(uebridge): checkouts window - pair checkout, revert, export back"
```

---

### Task 6: window.py — the Checkout and Export buttons

**Files:**
- Modify: `maya_uebridge/window.py` (two handlers + two buttons in `show_window`)

**Interfaces:**
- Consumes: `checkouts.checkout_pair`, `checkouts.open_for_export` (imported
  lazily inside the handlers — `checkouts` imports `window` at module top, so
  the top-level import must stay one-directional).

- [ ] **Step 1: Implement.** After `import_selected` in `window.py`:

```python
def checkout_selected():
    """Open the selected animation's uasset+fbx pair in Perforce."""
    record = _selected_record()
    if record is None:
        _status("select an animation first")
        return
    from maya_uebridge import checkouts
    _status(checkouts.checkout_pair(record))


def export_pressed():
    """The reverse bridge: the checkouts window, or a plain save-as export
    when nothing is checked out."""
    from maya_uebridge import checkouts
    checkouts.open_for_export()
```

In `show_window`, next to the IMPORT button:

```python
    checkout_button = cmds.button(
        label="Checkout", height=34, width=90,
        command=lambda *_: _run(checkout_selected, busy="talking to p4..."))
    export_button = cmds.button(
        label="EXPORT", height=34, width=90,
        command=lambda *_: _run(export_pressed, busy="reading checkouts..."))
```

and in the formLayout edit, attach them left of the import button:

```python
            (export_button, "right", 6, import_button),
            (export_button, "bottom", 6, status),
            (checkout_button, "right", 6, export_button),
            (checkout_button, "bottom", 6, status),
```

(`attachControl` entries; `import_button` keeps its `attachForm` right/8 and
`attachControl` bottom/6-to-status lines unchanged.)

- [ ] **Step 2: Sanity-run the full suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
Expected: all green (the new handlers are exercised live, not by unit tests — they are two lines over tested seams).

- [ ] **Step 3: Commit**

```bash
git add maya_uebridge/window.py
git commit -m "feat(uebridge): Checkout and Export buttons in the main window"
```

---

### Task 7: the live verify script

**Files:**
- Create: `docs/superpowers/plans/verify_uebridge_export.py`

**Interfaces:**
- Consumes: everything above, through the bridge. Injectable dialogs only —
  no modal may reach a command-port run (bridge note 6). Runner rules: no
  `raise SystemExit` (note 8), marker-guard with `if`, own output file per
  run, `sys.path.insert(0, REPO)` + purge of the installed SkeldarAnim
  copies (note 9).

- [ ] **Step 1: Write the script.** Gates, sandbox-first:

1. **Exporter round trip (no p4, no editor):** build a throwaway 3-joint
   chain keyed over frames 0..24 in a `__uebx_sandbox` group, export it with
   `animexport.export_hierarchy` to the scratchpad, then `FBXImport` it back
   into a fresh namespace and assert 3 joints and the key range arrived;
   delete both the sandbox and the import. autoKey off around the pokes
   (trap 14); key off current values, never literal zeros (trap 30).
2. **Range policy:** with the sandbox keyed 0..24 and the timeline narrowed
   to 5..10, `export_range()` still answers the outer range (trap 38 gate).
3. **Pure seams against the real depot (read-only):** `vcs.opened_records`
   over the real Content dir parses without error; `checkouts.load_rows`
   answers rows or a named failure, never raises; every row's package
   round-trips through `vcs.package_of`/`vcs.uasset_path_of`.
4. **Reimport on a sandbox uasset (editor required, no depot writes):**
   duplicate a small real AnimSequence to
   `/Game/__bridge_verify/AS_VerifyReimport` via a run_script snippet
   (`unreal.EditorAssetLibrary.duplicate_asset`), export the scene skeleton
   to a scratchpad fbx, `uescripts.reimport_script` it onto the duplicate,
   assert `ok` and `saved` in the reply, then delete the duplicate asset
   (`EditorAssetLibrary.delete_asset`) and its saved package folder. The
   duplicate was never in p4 — nothing to revert.
5. **Pair checkout+revert (depot, guarded):** on the known Longsword fbx +
   uasset pair — SKIP unless `p4 fstat` shows both free (never touch a file
   anyone holds open, ours included); `checkout_pair` with injected asks,
   assert both now open (`opened_records` sees the uasset, fstat sees the
   fbx), then `revert_pair` with injected confirm=yes and assert both free
   again.

Each gate prints `GATE <n> OK/FAIL <reason>`; the script ends with
`print("VERIFY DONE", failures)`. If no editor answers, gates 4 is reported
SKIPPED, not failed; if p4 is unreachable, 3 and 5 are SKIPPED with the
classified reason.

- [ ] **Step 2: Run it through the bridge if the port is listening** (check
`Get-NetTCPConnection -State Listen -LocalPort 7001` first). If the port is
down, leave the script committed and note it must run at the next session.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/verify_uebridge_export.py
git commit -m "docs: live verify script for the uebridge export-back direction"
```

---

### Task 8: working notes

**Files:**
- Modify: `CLAUDE.md` (the `maya_uebridge` section)

- [ ] **Step 1:** Add a subsection describing: the checkouts window and the
pair rule (checkout opens both, revert reverts both, «прокладка» created from
the editor when missing), the export flow order (resolve → temp → p4 → place
→ reimport → save), the range union rule, `-Ro` listing with clientFile, the
`content_dir` cache field, and the verify script's status (run or pending).
Record any new traps the implementation or live run taught.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: working notes for the uebridge export-back direction"
```
