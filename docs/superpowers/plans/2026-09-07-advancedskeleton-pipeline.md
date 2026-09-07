# AdvancedSkeleton Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch the SkeldarAnim shelf from OverRig to the AdvancedSkeleton rig: OverRig and the picker off behind flags, the retarget in the plugin with a native bake that also carries the weapon and camera bones and sets the camera up, Scene Setup adding the rig and finding the character from the selection, and one Perforce-free UE Bridge window whose IMPORT goes clip → rig → retarget → bake → source deleted.

**Architecture:** Feature flags in one stdlib module gate the OverRig-era UI. The three root-level retarget modules move into `SkeldarAnim/`; `maya_rig_retarget` (the dispatcher, i.e. the shelf buttons) grows the after-bake step (helper bones, weapon relink, camera setup). `maya_scenesetup.skeleton.current_root()` becomes the one "which character" answer (selection → rig → sole skeleton) used by Scene Setup and the bridge. `maya_uebridge/rigimport.py` chains the existing pieces into the automation; `window.py` is rebuilt as a single window.

**Tech Stack:** Maya 2027 `cmds`/`mel`/OpenMaya, mayapy + stdlib `unittest`, PySide6 only for icon generation.

Spec: `docs/superpowers/specs/2026-09-07-advancedskeleton-pipeline-design.md`.

## Global Constraints

- **No system Python.** Every run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <module> -v` from the repo root, with `$env:QT_QPA_PLATFORM = 'offscreen'`. Discovery: `-m unittest discover -s tests -t . -v`.
- **One rig per scene**: a rig is `cmds.objExists("ControlSet") and cmds.objExists("Main")`.
- **`maya_pmretarget` imports nothing from `maya_asretarget`** (test pins it) — duplicate the native bake, do not share it.
- **Plain `cmds` in `maya_scenesetup` and `maya_uebridge`**; any `maya_overrig` or Qt import stays lazy and guarded.
- **`character_path()` with no argument still means `Manny_Skeleton.ma`.**
- **Nothing is deleted from the repo**: `maya_overrig`, `vcs.py`, `checkouts.py`, `connect.py`, `aim.py` stay with their tests.
- **Commit after every task**; message written to a file and `git commit -F` (PowerShell quoting).
- **A Bash call over ~8 KB dies silently** — write big payloads with the Write tool.
- **Never run the pipeline proof in the animator's open scene**: it adds a rig and deletes a skeleton. mayapy standalone only.

---

### Task 1: Feature flags, shelf buttons, icons

**Files:**
- Create: `SkeldarAnim/skeldar_features.py`
- Modify: `SkeldarAnim/install.py` (`_PAYLOAD`, `_PYTHON_BUTTONS`, `button_specs`, docstring)
- Modify: `SkeldarAnim/icons/make_icons.py` (`draw_scenesetup`, `draw_retarget`, `draw_bake`, `DRAWERS`)
- Modify: `SkeldarAnim/README_INSTALL.txt`
- Test: `tests/test_install.py`

**Interfaces:**
- Produces: `skeldar_features.OVERRIG: bool`, `skeldar_features.PICKER: bool`; `install.features()` → the module; `install.button_specs(dest)` → nine specs in order `UE Bridge, Scene Setup, Retarget, Bake, Overshoot, Hotkeys, Studio, Colour, Curves` when both flags are False. Retarget calls `maya_rig_retarget.retarget_button()`, Bake `maya_rig_retarget.bake_button()` (Task 2 defines them).

- [ ] **Step 1: Write the failing tests** (replace `test_nine_buttons_in_shelf_order`, `test_python_buttons_bootstrap_and_call`, `test_python_buttons_use_our_icons`; add the flag tests)

```python
class ButtonSpecs(unittest.TestCase):
    DEST = "C:/Users/Some Body/Documents/maya/scripts/SkeldarAnim"

    def setUp(self):
        self.features = install.features()
        self.saved = (self.features.OVERRIG, self.features.PICKER)
        self.features.OVERRIG = False
        self.features.PICKER = False

    def tearDown(self):
        self.features.OVERRIG, self.features.PICKER = self.saved

    def _specs(self):
        return install.button_specs(self.DEST)

    def test_nine_buttons_in_shelf_order(self):
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["UE Bridge", "Scene Setup", "Retarget", "Bake",
                                  "Overshoot", "Hotkeys", "Studio", "Colour", "Curves"])

    def test_the_flags_bring_the_picker_and_overrig_back(self):
        self.features.PICKER = True
        self.features.OVERRIG = True
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels[0], "Rig Picker")
        self.assertEqual(labels[-1], "OverRig")
        self.assertEqual(len(labels), 11)

    def test_python_buttons_bootstrap_and_call(self):
        wanted = {
            "UE Bridge": ("maya_uebridge", "show_window"),
            "Scene Setup": ("maya_scenesetup", "show_window"),
            "Retarget": ("maya_rig_retarget", "retarget_button"),
            "Bake": ("maya_rig_retarget", "bake_button"),
            "Overshoot": ("maya_overshoot", "show_overshoot_ui"),
            "Hotkeys": ("maya_hotkeys", "toggle"),
            "Studio": ("maya_vpstudio", "show_window"),
            "Colour": ("maya_colour", "show_window"),
            "Curves": ("maya_curveview", "toggle"),
        }
        for spec in self._specs():
            module, func = wanted[spec["label"]]
            self.assertEqual(spec["sourceType"], "python")
            self.assertIn(self.DEST, spec["command"])
            self.assertIn("sys.path.insert(0, _p)", spec["command"])
            self.assertIn("import {0}".format(module), spec["command"])
            self.assertIn("{0}.{1}()".format(module, func), spec["command"])

    def test_python_buttons_use_our_icons(self):
        icons = [s["image"] for s in self._specs()]
        self.assertEqual(icons, [self.DEST + "/icons/" + n for n in (
            "uebridge.png", "scenesetup.png", "retarget.png", "bake.png",
            "overshoot.png", "hotkeys.png", "vpstudio.png", "colour.png",
            "curveview.png")])

    def test_the_payload_carries_the_flags_and_the_retarget(self):
        for name in ("skeldar_features.py", "maya_asretarget.py",
                     "maya_pmretarget.py", "maya_rig_retarget.py"):
            self.assertIn(name, install.payload())
```

The existing `test_overrig_button_replays_the_native_installer` and the `$path_to_JGLBN` test must set `self.features.OVERRIG = True` before calling `_specs()` and read the LAST spec.

- [ ] **Step 2: Run** `mayapy -m unittest tests.test_install -v` — expect failures on `install.features` (AttributeError) and the label list.

- [ ] **Step 3: Implement**

`SkeldarAnim/skeldar_features.py`:

```python
"""Which parts of the shelf are switched on. Stdlib only.

2026-09-07, the animator: «отключим все что связано с over rig и полностью
перейдем на наш риг и ретаргет адванцед скелетон. Отключаем пикер пока он
не нужен (но оставь его где-то, удалять не нужно)». Nothing is deleted:
`maya_overrig`, the picker, their tests and verify scripts stay whole, and
flipping a flag here brings the buttons and the hotkey rows back.

Read by install.button_specs (the shelf), maya_hotkeys.COMMANDS (the rows),
maya_scenesetup.character.connect and the two picker_root() fallbacks.
"""

# The native OverRig panel button and the 84 OverRig hotkey rows.
OVERRIG = False

# The Rig Picker button, its six hotkey rows, and connecting a freshly added
# character to the open picker.
PICKER = False
```

`install.py`: add `"skeldar_features.py", "maya_asretarget.py", "maya_pmretarget.py", "maya_rig_retarget.py"` to `_PAYLOAD`; rows carry a fifth field naming the flag or `""`:

```python
_PYTHON_BUTTONS = (
    ("Rig Picker", "OverRig picker: build, switch and select the rig",
     "maya_overrig", "show_picker", "picker.png", "PICKER"),
    ("UE Bridge", "Import animations from the running Unreal editor onto "
     "the AdvancedSkeleton rig", "maya_uebridge", "show_window", "uebridge.png", ""),
    ("Scene Setup", "Add the rig or a skeleton, a weapon in the hand",
     "maya_scenesetup", "show_window", "scenesetup.png", ""),
    ("Retarget", "Select the imported skeleton: the rig follows it",
     "maya_rig_retarget", "retarget_button", "retarget.png", ""),
    ("Bake", "Bake the retarget onto the controls, carry weapon and camera "
     "bones, set the camera up, disconnect", "maya_rig_retarget", "bake_button",
     "bake.png", ""),
    ("Overshoot", ..., ""), ("Hotkeys", ..., ""), ("Studio", ..., ""),
    ("Colour", ..., ""), ("Curves", ..., ""),
)


def features():
    """The flag module, loaded from beside this file (nothing of ours is on
    sys.path at drop time)."""
    import importlib.util
    path = os.path.join(source_root(), "skeldar_features.py")
    spec = importlib.util.spec_from_file_location("skeldar_features", path)
    module = sys.modules.get("skeldar_features")
    if module is None or getattr(module, "__file__", "") != path:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules["skeldar_features"] = module
    return module
```

In `button_specs`: `flags = features()`; skip a row whose sixth field names a flag that is False; append the OverRig MEL spec only `if flags.OVERRIG`.

`make_icons.py`: `draw_scenesetup` → a gear (outer circle r 9 with eight teeth as short thick radial strokes, inner hole r 3.2, accent `#c8c8c8`); `draw_retarget` → two stick figures (dots + lines) with an arrow between (accent `#7bd88f`); `draw_bake` → a key diamond over a horizontal bar with tick marks (accent `#ff8a65`). Register both in `DRAWERS`. Run:

```
$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' SkeldarAnim/icons/make_icons.py
```

`README_INSTALL.txt`: nine buttons named; PySide6 note moved to the Curves button; OverRig sentence removed.

- [ ] **Step 4: Run** `tests.test_install` — PASS. Also `tests.test_make_build` — PASS (it reads `payload()`).
- [ ] **Step 5: Commit** `feat(shelf): OverRig and the picker behind flags, Retarget and Bake on the shelf, gear icon`.

---

### Task 2: The retarget moves into the plugin

**Files:**
- Move (`git mv`): `maya_asretarget.py`, `maya_pmretarget.py`, `maya_rig_retarget.py` → `SkeldarAnim/`
- Modify: `SkeldarAnim/maya_pmretarget.py:158` (`ASSETS`), `SkeldarAnim/maya_rig_retarget.py` (buttons)
- Modify: `docs/superpowers/plans/verify_asretarget.py`, `verify_asretarget_mixamo.py`, `verify_pmretarget.py` (`sys.path` lines → `C:/!!!Work/MayaScripts/SkeldarAnim`)
- Test: `tests/test_rig_retarget.py`, `tests/test_pmretarget.py`

**Interfaces:**
- Produces: `maya_rig_retarget.retarget_button()` / `bake_button()` — call `connect()` / `bake()`, `print` the text, `cmds.inViewMessage(assistMessage=first line, position="midCenterBot", fade=True)` (guarded — batch has no viewport); return the text.

- [ ] **Step 1: Tests**

```python
# tests/test_pmretarget.py
def test_assets_sit_beside_the_module(self):
    self.assertEqual(os.path.normcase(pm.ASSETS),
                     os.path.normcase(os.path.join(os.path.dirname(pm.__file__), "assets")))
    self.assertTrue(os.path.isfile(os.path.join(pm.ASSETS, "manny_skeleton_template.json")))

# tests/test_rig_retarget.py
def test_the_modules_live_in_the_plugin(self):
    for mod in (ar, pm, rr):
        self.assertEqual(os.path.basename(os.path.dirname(mod.__file__)), "SkeldarAnim")

def test_the_buttons_forward_and_report(self):
    calls = []
    rr.connect = lambda *a, **k: calls.append("connect") or "connected 74"
    rr.bake = lambda *a, **k: calls.append("bake") or "baked"
    rr._show = lambda text: calls.append(text)
    self.assertEqual(rr.retarget_button(), "connected 74")
    self.assertEqual(rr.bake_button(), "baked")
    self.assertEqual(calls, ["connect", "connected 74", "bake", "baked"])
```
(save and restore the patched names in `setUp`/`tearDown`.)

- [ ] **Step 2: Run** both modules — FAIL (ASSETS path, missing buttons).
- [ ] **Step 3: Implement** — `git mv` the three files; `ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")`; in `maya_rig_retarget`:

```python
def _show(text):
    """The first line in the viewport, everything in the Script Editor."""
    print(text)
    try:
        cmds.inViewMessage(assistMessage=text.splitlines()[0], position="midCenterBot", fade=True)
    except Exception:   # batch, or no viewport: the print is the report
        pass


def retarget_button():
    """The shelf button: the rig follows the SELECTED skeleton."""
    text = connect()
    _show(text)
    return text


def bake_button():
    """The shelf button: bake, carry the helper bones, camera up, disconnect."""
    text = bake()
    _show(text)
    return text
```
`sed -i 's#C:/!!!Work/MayaScripts")#C:/!!!Work/MayaScripts/SkeldarAnim")#'` on the three verify scripts (check each with grep first).

- [ ] **Step 4: Run** `tests.test_rig_retarget tests.test_asretarget tests.test_pmretarget` — PASS.
- [ ] **Step 5: Commit** `refactor(retarget): the three retarget modules move into the plugin`.

---

### Task 3: The native bake

**Files:**
- Modify: `SkeldarAnim/maya_asretarget.py` (`bake`, new `vendor_bake`, `connected_source`), `SkeldarAnim/maya_pmretarget.py` (same)
- Test: `tests/test_asretarget.py`, `tests/test_pmretarget.py`, `tests/test_rig_retarget.py`

**Interfaces:**
- Produces: `vendor_bake(start, end)` → list of controls baked; `connected_source()` → the remembered source root path or `None`; `bake(disconnect=True)` unchanged signature, no `mel.eval`.

- [ ] **Step 1: Tests** — a small fake bound onto the module (`ar.cmds = fake`, restored in `tearDown`):

```python
class FakeBakeCmds(object):
    def __init__(self):
        self.calls = []
        self.holder_targets = ["c1", "c2"]
        self.driven = {"c1": ["FKWrist_R"], "c2": ["IKArm_L"]}
    def objExists(self, n): return True
    def attributeQuery(self, *a, **k): return True
    def listConnections(self, plug, **k):
        node, attr = plug.split(".")
        if attr == "disableConstraints": return list(self.holder_targets)
        if attr == "constraintParentInverseMatrix": return self.driven[node]
        return []
    def bakeResults(self, *objs, **k): self.calls.append(("bakeResults", objs, k))
    def delete(self, *objs, **k): self.calls.append(("delete", objs, k))

def test_vendor_bake_issues_the_vendors_flags(self):
    fake = FakeBakeCmds(); ar.cmds = fake
    baked = ar.vendor_bake(3.0, 41.0)
    self.assertEqual(baked, ["FKWrist_R", "IKArm_L"])
    name, objs, k = fake.calls[0]
    self.assertEqual(name, "bakeResults")
    self.assertEqual(k["time"], (3.0, 41.0))
    for flag, value in (("simulation", True), ("sampleBy", 1), ("disableImplicitControl", True),
                        ("preserveOutsideKeys", False), ("sparseAnimCurveBake", False),
                        ("removeBakedAttributeFromLayer", False), ("bakeOnOverrideLayer", False),
                        ("controlPoints", False), ("shape", False)):
        self.assertEqual(k[flag], value, flag)
    name, objs, k = fake.calls[1]
    self.assertEqual((name, k["staticChannels"], k["unitlessAnimationCurves"], k["hierarchy"],
                      k["controlPoints"], k["shape"]), ("delete", True, False, "none", False, True))

def test_bake_no_longer_reaches_for_the_vendor(self):
    with open(ar.__file__, encoding="utf-8") as fh: src = fh.read()
    self.assertNotIn("asMoCapMatcherBake;", src.split("def vendor_bake")[1])
```
In `test_rig_retarget.TestMannyBake` replace the `assertNotIn("bakeResults")` gone-test with `assertIn("def vendor_bake", src)` for both modules.

- [ ] **Step 2: Run** — FAIL (`vendor_bake` missing).
- [ ] **Step 3: Implement** in both modules (identical text, the `mel` import stays only if still used elsewhere — in `maya_asretarget` it is not: drop it):

```python
def vendor_bake(start, end):
    """What AdvancedSkeleton's `asMoCapMatcherBake` does, in cmds, flag for flag.

    Read whole from the vendor's MEL (2026-09-07): every constraint on the holder's
    switch, resolved through `constraintParentInverseMatrix` to the object it drives,
    baked with -simulation over the range, static channels deleted. Ours so the bake
    needs nothing of AdvancedSkeleton sourced in the session -- a colleague's fresh
    Maya, or the bridge's IMPORT, would otherwise die on `Cannot find procedure`.
    """
    constraints = cmds.listConnections(HOLDER + "." + SWITCH, source=False, destination=True) or []
    controls = []
    for constraint in constraints:
        driven = cmds.listConnections(constraint + ".constraintParentInverseMatrix") or []
        if driven and driven[0] not in controls:
            controls.append(driven[0])
    if not controls:
        return []
    cmds.bakeResults(*controls, simulation=True, time=(start, end), sampleBy=1,
                     disableImplicitControl=True, preserveOutsideKeys=False,
                     sparseAnimCurveBake=False, removeBakedAttributeFromLayer=False,
                     bakeOnOverrideLayer=False, controlPoints=False, shape=False)
    cmds.delete(*controls, staticChannels=True, unitlessAnimationCurves=False,
                hierarchy="none", controlPoints=False, shape=True)
    return controls


def connected_source():
    """The source root connect() remembered on the holder, or None."""
    if not cmds.objExists(HOLDER) or not cmds.attributeQuery(SOURCE_ATTR, node=HOLDER, exists=True):
        return None
    root = cmds.getAttr(HOLDER + "." + SOURCE_ATTR)
    return root if root and cmds.objExists(root) else None
```
`bake()`: replace the `playbackOptions` save/set/restore + `mel.eval` with `span = source_key_range() or (playback min, max)` and `vendor_bake(span[0], span[1])`; wording `"baked %d controls over %g..%g (%d curves; static channels dropped, as the vendor's Bake does)"`. Docstrings: "the vendor's contract, our code".

- [ ] **Step 4: Run** the three test modules — PASS.
- [ ] **Step 5: Commit** `feat(retarget): the MoCap bake in cmds, on the vendor's contract - no AdvancedSkeleton needed at runtime`.

---

### Task 4: Hotkey rows follow the flags

**Files:**
- Modify: `SkeldarAnim/maya_hotkeys.py` (`_OURS` picker rows, the four Scene Setup rows for removed buttons, `COMMANDS`, new `_retarget_module` seam + two rows)
- Test: `tests/test_hotkeys.py`

**Interfaces:**
- Produces: `maya_hotkeys.commands(flags)` (pure: the table for given flags) and `COMMANDS = commands(skeldar_features)`; rows `retarget.connect`, `retarget.bake` under category `SkeldarAnim.Retarget` calling `_retarget("retarget_button")` / `_retarget("bake_button")`.

- [ ] **Step 1: Tests**

```python
def test_picker_and_overrig_rows_are_behind_the_flags(self):
    off = maya_hotkeys.commands(types.SimpleNamespace(PICKER=False, OVERRIG=False))
    on = maya_hotkeys.commands(types.SimpleNamespace(PICKER=True, OVERRIG=True))
    self.assertFalse([r for r in off if r[0].startswith("picker.") or r[0].startswith("overrig.")])
    self.assertEqual(len([r for r in on if r[0].startswith("overrig.")]), 84)
    self.assertEqual(len([r for r in on if r[0].startswith("picker.")]), 6)

def test_the_retarget_rows_press_the_shelf_buttons(self):
    fake_mod = types.SimpleNamespace(retarget_button=lambda: "c", bake_button=lambda: "b")
    maya_hotkeys._retarget_module = lambda: fake_mod
    self.assertEqual(maya_hotkeys.run("retarget.connect"), "c")
    self.assertEqual(maya_hotkeys.run("retarget.bake"), "b")

def test_the_removed_scene_setup_buttons_have_no_rows(self):
    for key in ("scene.connect_arms", "scene.disconnect_arms", "scene.aim", "scene.camera"):
        self.assertIsNone(maya_hotkeys.row(key))
```
Existing tests that count 84 OverRig rows or exercise `picker.*` must build their table with `commands(SimpleNamespace(PICKER=True, OVERRIG=True))` and patch `maya_hotkeys._INDEX`/`COMMANDS` for the test (add a helper `_with_all_rows(self)` in the test module that swaps them in `setUp` and back in `tearDown`).

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement**

```python
def _retarget_module():
    import maya_rig_retarget
    return maya_rig_retarget


def _retarget(func):
    """Press a Retarget shelf button; it reports in the viewport itself."""
    return getattr(_retarget_module(), func)()

# in _OURS, after the Scene Setup rows (which lose connect_arms/disconnect_arms/aim/camera):
    ("retarget.connect", "Retarget", "Retarget onto the rig",
     "The rig follows the selected imported skeleton", partial(_retarget, "retarget_button")),
    ("retarget.bake", "Retarget", "Bake retarget",
     "Bake onto the controls, carry weapon and camera bones, camera up, disconnect",
     partial(_retarget, "bake_button")),

_PICKER_ROWS = tuple(r for r in _OURS if r[0].startswith("picker."))


def commands(flags):
    """The table for a set of feature flags. Pure."""
    ours = tuple(r for r in _OURS if flags.PICKER or not r[0].startswith("picker."))
    table = _prefixed("SkeldarAnim", ours)
    if flags.OVERRIG:
        table += _prefixed("OverRig", _OVERRIG)
    return table


import skeldar_features
COMMANDS = commands(skeldar_features)
_INDEX = dict((command[0], command) for command in COMMANDS)
```

- [ ] **Step 4: Run** `tests.test_hotkeys` — PASS.
- [ ] **Step 5: Commit** `feat(hotkeys): picker and OverRig rows behind the flags, Retarget rows added`.

---

### Task 5: Catalog rows, the shipped rig, Add Character with the rig

**Files:**
- Create: `SkeldarAnim/assets/Manny_Rig.ma` (copy of `C:/!!!Work/Animations/Rigs/Characters/Manny_rig_02.ma` minus the `camera1` block)
- Modify: `SkeldarAnim/maya_scenesetup/catalog.py`, `colour.py` (`paint_fresh`), `character.py` (`add_character`, `connect`, `rig_present`, `RIG_PRESENT`)
- Test: `tests/test_scenesetup_catalog.py`, `tests/test_scenesetup_colour.py`, `tests/test_scenesetup_character.py`

**Interfaces:**
- Produces: `catalog.Character(key, label, file, legacy, kind)`; `catalog.CHARACTERS[0]` = the rig; `catalog.default_character()` = the `Manny` skeleton; `catalog.default_rig()` = the rig; `catalog.is_rig(entry)`. `colour.paint_fresh(shapes, rgb, key)` → material. `character.rig_present()` (True when `ControlSet` and `Main` exist), `character.RIG_PRESENT` message, `character.add_character(entry=None, rgb=None)` refusing a second rig.

- [ ] **Step 1: The asset.** Find the block and cut it by line range, then prove the cut:

```
f="C:/!!!Work/Animations/Rigs/Characters/Manny_rig_02.ma"
start=$(grep -n '^createNode transform -n "camera1";$' "$f" | cut -d: -f1)      # 1099986
next=$(awk -v s="$start" 'NR>s && /^createNode /{print NR; exit}' "$f")           # the node after cameraShape1's block
end=$((next-1))
sed "${start},${end}d" "$f" > SkeldarAnim/assets/Manny_Rig.ma
diff <(sed "${start},${end}d" "$f") SkeldarAnim/assets/Manny_Rig.ma && grep -c "camera1" SkeldarAnim/assets/Manny_Rig.ma   # expect 0
```
`next` must land on `createNode transform -n "Group";`-or-`joint -n "root"` — check by printing lines `start..end` before cutting; the shape block ends where the next `createNode` begins.

- [ ] **Step 2: Tests**

```python
# catalog
def test_the_rig_is_first_and_marked_as_a_rig(self):
    self.assertEqual(catalog.CHARACTERS[0].key, "Manny_Rig")
    self.assertEqual(catalog.CHARACTERS[0].kind, "rig")
    self.assertIn("[rig]", catalog.CHARACTERS[0].label)
    self.assertEqual(catalog.CHARACTERS[0].file, "Manny_Rig.ma")
def test_skeletons_are_marked_as_skeletons(self):
    for key in ("Manny", "UE4_Mannequin"):
        self.assertEqual(catalog.character_by_key(key).kind, "skeleton")
        self.assertIn("[skeleton]", catalog.character_by_key(key).label)
def test_the_default_character_is_still_the_skeleton(self):
    self.assertEqual(catalog.default_character().key, "Manny")
    self.assertTrue(catalog.character_path().endswith("Manny_Skeleton.ma"))
def test_default_rig(self):
    self.assertIs(catalog.default_rig(), catalog.CHARACTERS[0])
    self.assertTrue(catalog.is_rig(catalog.default_rig()))
    self.assertFalse(catalog.is_rig(catalog.default_character()))
# every_entry_ships_in_assets already covers Manny_Rig.ma once the row exists

# colour (fake cmds as the module's other tests do)
def test_paint_fresh_makes_a_new_material_even_over_a_marked_one(self):
    ... shapes already carry a material for which is_ours() is True ...
    material = colour.paint_fresh(shapes, (0, 1, 0), "Manny_Rig")
    self.assertNotEqual(material, old_material)
    self.assertEqual(fake.made, 1)      # one shadingNode created

# character
def test_a_second_rig_is_refused_by_name(self):
    character.rig_present = lambda: True
    text = character.add_character(catalog.default_rig())
    self.assertEqual(text, character.RIG_PRESENT)
def test_rig_present_asks_for_both_nodes(self):
    fake.existing = {"ControlSet"}   -> False ; {"ControlSet", "Main"} -> True
def test_connect_is_skipped_while_the_picker_is_off(self):
    features.PICKER = False; self.assertFalse(character.connect("|root"))
```

- [ ] **Step 3: Run** — FAIL.
- [ ] **Step 4: Implement**

```python
# catalog.py
Character = collections.namedtuple("Character", "key label file legacy kind")
_LEGACY_RIG = "C:/!!!Work/Animations/Rigs/Characters/Manny_rig_02.ma"
CHARACTERS = [
    # The AdvancedSkeleton rig over Manny (2026-09-04..05), the working
    # character since 2026-09-07. The animator's own file minus its leftover
    # camera1 (a textual cut, like the vaccine cut). ONE per scene: the
    # retarget addresses it by name.
    Character("Manny_Rig", "Manny [rig]", "Manny_Rig.ma", _LEGACY_RIG, "rig"),
    Character("Manny", "Manny UE5 [skeleton]", "Manny_Skeleton.ma", _LEGACY_CHARACTER, "skeleton"),
    Character("UE4_Mannequin", "UE4 Mannequin [skeleton]", "UE4_Mannequin.fbx", "", "skeleton"),
]
def default_character():
    """The Manny SKELETON: `character_path()` with no argument has always meant
    Manny_Skeleton.ma, and maya_skelfit asks it that way."""
    return character_by_key("Manny")
def default_rig():
    return CHARACTERS[0]
def is_rig(entry):
    return entry.kind == "rig"
```

```python
# colour.py
def paint_fresh(shapes, rgb, key):
    """A NEW material in `rgb` on `shapes`, whatever they wear now.

    For an Add: the shipped rig file carries the animator's own
    skeldarColour_red blinn, and `paint` -- which reuses a marked material --
    would bring every rig in red and ignore the swatch. The asset's material
    is left in the scene unassigned, where `is_assigned` stops counting it.
    """
    shapes = [shape for shape in (shapes or []) if shape]
    if not shapes:
        return None
    material, engine = make_material(rgb, key)
    cmds.sets(shapes, edit=True, forceElement=engine)
    return material
```

```python
# character.py
RIG_PRESENT = ("a rig is already in the scene - one AdvancedSkeleton rig per "
               "scene; delete it (Group and its skeleton) before adding another")

def rig_present():
    """One rig per scene: the retarget addresses it by name."""
    return bool(cmds.objExists("ControlSet") and cmds.objExists("Main"))

def connect(root):
    import skeldar_features
    if not root or not skeldar_features.PICKER:
        return False
    ...unchanged...

def add_character(entry=None, rgb=None):
    entry = entry or catalog.default_character()
    if catalog.is_rig(entry) and rig_present():
        return RIG_PRESENT
    ...
    painted = colour.paint_fresh(colour.mesh_shapes(new), rgb, entry.key)
```
Window: `add_character()` in `window.py` already passes `chosen_character()`; nothing else there yet.

- [ ] **Step 5: Run** the three test modules — PASS.
- [ ] **Step 6: Commit** `feat(scenesetup): Add Character adds the AdvancedSkeleton rig; skeletons marked as skeletons` (the 53 MB asset goes in this commit).

---

### Task 6: Which character — the resolver, Scene Setup's window, the bridge's target

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/skeleton.py` (`choose_root`, `current_root`, new `rig_root`, `rig_group`, `selection_roots`), `window.py` (buttons, callbacks, wording), `SkeldarAnim/maya_uebridge/animimport.py` (`picker_root` → `connected_root`)
- Test: `tests/test_scenesetup_skeleton.py`, `tests/test_scenesetup_window.py`, `tests/test_uebridge_import.py`

**Interfaces:**
- Produces: `skeleton.choose_root(selection_roots, rig_root, scene_roots)` (pure; NOTE the first argument changed meaning: no picker), `skeleton.current_root()`, `skeleton.rig_root()` → the rig's game-skeleton root path or `None`, `skeleton.rig_group()` → top ancestor of `Main` or `None`, `skeleton.selection_roots(selection, rig_group_path, rig_root_path)` (pure over paths + a `is_joint` callable). `animimport.connected_root()` → `skeleton.current_root()` lazily, `None` on any failure.

- [ ] **Step 1: Tests**

```python
# skeleton
RIG = "|root"; GROUP = "|Group"; OTHER = "|anim:root"
def test_a_control_means_the_rigs_skeleton(self):
    roots = skeleton.selection_roots(["|Group|MotionSystem|FKSystem|FKWrist_R"], GROUP, RIG, lambda p: False)
    self.assertEqual(roots, [RIG])
def test_a_joint_means_its_top_joint(self):
    roots = skeleton.selection_roots(["|anim:root|anim:pelvis"], GROUP, RIG, lambda p: True)
    self.assertEqual(roots, [OTHER])     # find_root is injected as `top_joint`
def test_a_mesh_is_ignored(self): ...
def test_choose_root_selection_then_rig_then_sole(self):
    self.assertEqual(skeleton.choose_root([OTHER], RIG, [RIG, OTHER]), OTHER)
    self.assertEqual(skeleton.choose_root([], RIG, [RIG, OTHER]), RIG)
    self.assertEqual(skeleton.choose_root([], None, [OTHER]), OTHER)
    self.assertIsNone(skeleton.choose_root([RIG, OTHER], RIG, [RIG, OTHER]))
    self.assertIsNone(skeleton.choose_root([], None, [RIG, OTHER]))
    self.assertIsNone(skeleton.choose_root([], None, []))

# window
def test_the_overrig_era_callbacks_are_gone(self):
    for name in ("connect_arms", "disconnect_arms", "add_aim", "camera_setup"):
        self.assertFalse(hasattr(window, name), name)
def test_no_character_names_the_new_rule(self):
    self.assertIn("select", window.NO_CHARACTER.lower())
    self.assertNotIn("picker", window.NO_CHARACTER.lower())
def test_bound_message_says_rig_or_skeleton(self):
    self.assertEqual(window.bound_message("|root", rig=True), "Character: root (rig)")
    self.assertEqual(window.bound_message("|anim:root", rig=False), "Character: anim:root (skeleton)")
```

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement**

```python
# skeleton.py
def rig_group():
    """The rig's top group: the top ancestor of `Main`, or None."""
    if not (cmds.objExists("ControlSet") and cmds.objExists("Main")):
        return None
    main = cmds.ls("Main", long=True)
    return "|" + main[0].split("|")[1] if main else None


def rig_root():
    """The game skeleton the rig drives, or None without a rig."""
    if rig_group() is None:
        return None
    import maya_pmretarget as pm      # rig_paths/rig_skeleton_root are schema-blind
    return pm.rig_skeleton_root(pm.rig_paths()) or None


def selection_roots(selection, rig_group_path, rig_root_path, top_joint):
    """Pure: what each selected path means. A node under the rig's group is
    the rig's skeleton; a joint is its topmost joint; anything else nothing."""
    roots = []
    for path in selection or []:
        if rig_group_path and (path == rig_group_path or path.startswith(rig_group_path + "|")):
            roots.append(rig_root_path)
        elif top_joint(path):
            roots.append(top_joint(path))
    return roots


def choose_root(selection_roots_, rig_root_path, scene_roots):
    """Selection, then the rig, then the only skeleton. Pure."""
    selected = list(dict.fromkeys(r for r in selection_roots_ if r))
    if len(selected) == 1:
        return selected[0]
    if selected:
        return None
    if rig_root_path:
        return rig_root_path
    if len(scene_roots) == 1:
        return scene_roots[0]
    return None


def current_root():
    from maya_overrig import builder     # character_roots; lazy, drags maya.mel
    group, root = rig_group(), rig_root()
    def top_joint(path):
        return naming.find_root(path) if cmds.objectType(path) == "joint" else None
    selection = cmds.ls(selection=True, long=True) or []
    scene_roots = [r for r in builder.character_roots()
                   if not (group and (r == group or r.startswith(group + "|")))]
    return choose_root(selection_roots(selection, group, root, top_joint), root, scene_roots)
```
`active.set_root(root)` stays after the choice (harmless; the OverRig modules still read it).

`window.py`: delete `connect_arms`, `disconnect_arms`, `add_aim`, `camera_setup` and their four buttons + the two separators around them; drop the `weaponaim`, `camerarig`, `linking`, `aimrig` imports ONLY if no remaining guard uses them — `add_weapon`/`remove_weapon` still call `linking.linked_weapon()` and `aimrig.aim_for`, so keep `linking` and `aimrig`; drop `weaponaim` and `camerarig`. `NO_CHARACTER = "no character - select any control or joint of it (with one rig in the scene nothing needs selecting)"`. `bound_message(root, rig=False)` → `"Character: <leaf> (rig|skeleton)"`, `"no character"` when None; `_bound_root()` passes `rig=(root == skeleton.rig_root())`. Add Character's annotation loses "connected in the picker"; the Character menu annotation names the rig.

`animimport.py`: rename `picker_root` → `connected_root`:

```python
def connected_root():
    """The character Scene Setup would act on: selection, the rig, the sole
    skeleton. Lazy and guarded -- the bridge is plain cmds, and a session
    without maya_scenesetup keeps the old rule (sole skeleton, then `root`)."""
    try:
        from maya_scenesetup import skeleton
        return skeleton.current_root()
    except Exception:
        return None
```
and `resolve_target()` passes `connected_root()`. Since `current_root()` already applies the selection, `choose_target_root(roots, selected_roots(), connected_root())` keeps working: the selection slot and the connect slot agree.

- [ ] **Step 4: Run** `tests.test_scenesetup_skeleton tests.test_scenesetup_window tests.test_uebridge_import` — PASS.
- [ ] **Step 5: Commit** `feat(scenesetup): the character comes from the selection, the rig, or the sole skeleton; OverRig-era buttons gone`.

---

### Task 7: The Bake button carries the helper bones and sets the camera up

**Files:**
- Modify: `SkeldarAnim/maya_rig_retarget.py`
- Test: `tests/test_rig_retarget.py`

**Interfaces:**
- Produces: `HELPER_BONES = ("weapon_r", "weapon_l", "camera_root", "camera_bone")`; `helper_plan(source_bones, rig_bones, foreign)` (pure) → `(moves: [(name, src_path, dst_path)], skipped: [(name, reason)])`; `transfer_bone(src, dst, start, end)`; `helper_note(moved, skipped, camera_text)` (pure wording); `bake()` → the six-step text.

- [ ] **Step 1: Tests**

```python
def test_helper_plan_moves_what_both_have_and_names_the_rest(self):
    src = {"weapon_r": "|a:root|a:hand_r|a:weapon_r", "camera_root": "|a:root|a:camera_root"}
    dst = {"weapon_r": "|root|hand_r|weapon_r", "weapon_l": "|root|hand_l|weapon_l",
           "camera_root": "|root|camera_root", "camera_bone": "|root|camera_root|camera_bone"}
    moves, skipped = rr.helper_plan(src, dst, foreign={"camera_root"})
    self.assertEqual(moves, [("weapon_r", src["weapon_r"], dst["weapon_r"])])
    self.assertEqual(dict(skipped), {"weapon_l": "not in the source", "camera_bone": "not in the source",
                                     "camera_root": "driven by somebody else's constraint"})
def test_helper_note_wording(self):
    text = rr.helper_note(["weapon_r", "camera_bone"], [("weapon_l", "not in the source")], "camera SceneSetup_camera on camera_bone (46 frames)")
    self.assertIn("weapon_r, camera_bone carried", text); self.assertIn("weapon_l (not in the source)", text)
    self.assertIn("SceneSetup_camera", text)
```

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement**

```python
HELPER_BONES = ("weapon_r", "weapon_l", "camera_root", "camera_bone")


def helper_plan(source_bones, rig_bones, foreign=()):
    """Pure: which helper bones move from the source onto the rig's skeleton."""
    moves, skipped = [], []
    for name in HELPER_BONES:
        if name not in rig_bones:
            continue                     # a rig without the bone has nothing to carry
        if name not in source_bones:
            skipped.append((name, "not in the source"))
        elif name in foreign:
            skipped.append((name, "driven by somebody else's constraint"))
        else:
            moves.append((name, source_bones[name], rig_bones[name]))
    return moves, skipped


def helper_note(moved, skipped, camera_text):
    parts = []
    if moved:
        parts.append(", ".join(moved) + " carried from the source")
    if skipped:
        parts.append("skipped " + ", ".join("%s (%s)" % s for s in skipped))
    if camera_text:
        parts.append(camera_text)
    return "; ".join(parts)


_CHANNELS = ["translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ"]


def transfer_bone(src, dst, start, end):
    """The rig's bone onto the source's world track: constrain, bake, release."""
    constraint = cmds.parentConstraint(src, dst)[0]
    cmds.bakeResults(dst, time=(start, end), attribute=_CHANNELS, simulation=False, sampleBy=1,
                     disableImplicitControl=True, preserveOutsideKeys=False, sparseAnimCurveBake=False)
    cmds.delete(constraint)
    cmds.delete(dst, staticChannels=True, unitlessAnimationCurves=False, hierarchy="none",
                controlPoints=False, shape=True)


def _bones_under(root):
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    out = {}
    for p in paths:
        out.setdefault(p.split("|")[-1].split(":")[-1], p)
    return out


def _foreign(bones):
    """Helper bones under a constraint that is neither ours nor the weapon link's."""
    from maya_scenesetup import bonedrive, camera
    found = set()
    for name, path in bones.items():
        for c in cmds.listRelatives(path, children=True, type="constraint", fullPath=True) or []:
            if bonedrive.driving_weapon(path) or camera.our_constraints(path):
                continue
            found.add(name)
    return found


def carry_helpers(source_root, rig_root, start, end):
    """Steps 2-4 and 6 of the Bake button. Returns (moved names, skipped, camera text)."""
    from maya_scenesetup import bonedrive, camera
    src, dst = _bones_under(source_root), _bones_under(rig_root)
    cam_bone = dst.get("camera_bone")
    if cam_bone:
        camera.teardown(cam_bone, start, end)          # bakes the bone back, deletes the camera
    links = dict(bonedrive.find_links([dst[n] for n in ("weapon_r", "weapon_l") if n in dst]))
    for bone in links:
        bonedrive.unlink(bone)
    moves, skipped = helper_plan(src, dst, _foreign(dst))
    for _name, s, d in moves:
        transfer_bone(s, d, start, end)
    for bone, weapon in links.items():
        if cmds.objExists(weapon) and cmds.objExists(bone):
            bonedrive.relink(weapon, bone)
    camera_text = camera.setup(cam_bone, start, end) if cam_bone else ""
    return [m[0] for m in moves], skipped, camera_text


def bake(*args, **kwargs):
    mod, refusal = rig_module()
    if mod is None:
        return refusal
    source = mod.connected_source()
    if source is None:
        return mod.bake(*args, **kwargs)              # nothing connected: the module says so
    span = mod.source_key_range() or (cmds.playbackOptions(query=True, min=True),
                                      cmds.playbackOptions(query=True, max=True))
    rig_root = mod.rig_skeleton_root(mod.rig_paths())
    cmds.undoInfo(openChunk=True, chunkName="Retarget bake")
    try:
        note = mod.bake(disconnect=False)
        moved, skipped, camera_text = carry_helpers(source, rig_root, span[0], span[1])
        note += "; " + mod.disconnect()
    finally:
        cmds.undoInfo(closeChunk=True)
    extra = helper_note(moved, skipped, camera_text)
    return "%s: %s%s" % (mod.__name__, note, ("; " + extra) if extra else "")
```
`carry_helpers` runs BEFORE `disconnect()` only because the source root is read from the holder; the transfer itself does not need the holder. Camera setup after the transfer, on the bone's new track.

- [ ] **Step 4: Run** `tests.test_rig_retarget` — PASS.
- [ ] **Step 5: Commit** `feat(retarget): Bake carries weapon_r/weapon_l/camera_root/camera_bone from the source and sets the camera up`.

---

### Task 8: The bridge — one window, no Perforce, IMPORT = the whole pipeline

**Files:**
- Create: `SkeldarAnim/maya_uebridge/rigimport.py`
- Rewrite: `SkeldarAnim/maya_uebridge/window.py`
- Test: `tests/test_uebridge_rigimport.py` (new), `tests/test_uebridge_window.py`

**Interfaces:**
- Produces: `rigimport.source_root_in(namespace_nodes, is_joint)` (pure), `rigimport.precheck(rig_present, holder_present, posed, rig_file_ok)` (pure → refusal or ""), `rigimport.result_line(name, info, connect_text, bake_text, deleted_ns)` (pure), `rigimport.import_and_retarget(fbx_path, name, clip_fps=None, set_timeline=True)` → status text. `window.retarget_selected()` (mode 1), `window.new_skeleton_selected()`... (one `import_selected` branching on `_MODE`), `window.export_fbx_selected()`, constants `NO_PERFORCE = True` not needed — the module simply has no vcs import (test pins it).

- [ ] **Step 1: Tests**

```python
# tests/test_uebridge_rigimport.py
def test_the_source_root_is_the_topmost_joint_of_the_namespace(self):
    nodes = ["|c:root|c:pelvis", "|c:root", "|c:root|c:pelvis|c:spine_01", "|c:rootShape"]
    self.assertEqual(rigimport.source_root_in(nodes, lambda p: not p.endswith("Shape")), "|c:root")
def test_a_nested_namespace_still_resolves(self):
    nodes = ["|m:mixamorig:Hips|m:mixamorig:Spine", "|m:mixamorig:Hips"]
    self.assertEqual(rigimport.source_root_in(nodes, lambda p: True), "|m:mixamorig:Hips")
def test_precheck_refusals(self):
    self.assertIn("MoCapConstraints", rigimport.precheck(True, True, False, True))
    self.assertIn("BuildPose", rigimport.precheck(True, False, True, True))
    self.assertIn("Manny_Rig.ma", rigimport.precheck(False, False, False, False))
    self.assertEqual(rigimport.precheck(True, False, False, True), "")
def test_result_line(self):
    text = rigimport.result_line("A_Jump", {"joints": 93, "start": 0.0, "end": 45.0}, "connected 74", "baked 20 controls", "A_Jump")
    self.assertIn("A_Jump", text); self.assertIn("0-45", text); self.assertIn("source skeleton A_Jump deleted", text)
def test_the_window_imports_no_perforce(self):
    import maya_uebridge.window as w, sys
    self.assertNotIn("maya_uebridge.vcs", sys.modules)      # after a fresh import in a subprocess, as test_uebridge_uasset does it
```

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement `rigimport.py`**

```python
"""IMPORT in one press: the rig if it is missing, the clip as its own skeleton,
the retarget, the bake, and the source skeleton gone.

2026-09-07, the animator: «import onto the skeleton давай поменяем на
автоматический импорт нашего рига + импорт выбранной анимации, потом
ретаргет, бейк анимаций на ретаргет и удаление скелета с которого взяли
анимацию». Every piece already existed; this module is the order they run in
and the refusals that stop the press before anything is imported.
"""
import maya.cmds as cmds

from maya_uebridge import animimport, records

NO_RIG_FILE = "no rig file - Manny_Rig.ma is missing from assets/ and the legacy path"
CONNECTED = ("the rig is still connected to a source (MoCapConstraints stands) - "
             "press Bake, or disconnect, first")
POSED = "the rig is posed - AdvancedSkeleton: Go To BuildPose, then import again"


def precheck(rig_present, holder_present, posed, rig_file_ok):
    """Pure. The refusal, or "" when the press may go ahead."""
    if not rig_present and not rig_file_ok:
        return NO_RIG_FILE
    if holder_present:
        return CONNECTED
    if rig_present and posed:
        return POSED
    return ""


def source_root_in(namespace_nodes, is_joint):
    """The topmost joint among a namespace's DAG nodes. Pure."""
    joints = [p for p in namespace_nodes if p.startswith("|") and is_joint(p)]
    if not joints:
        return None
    return sorted(joints, key=lambda p: (p.count("|"), p))[0]


def result_line(name, info, connect_text, bake_text, deleted_namespace):
    span = ""
    if info.get("start") is not None:
        span = ", frames {0:g}-{1:g}".format(info["start"], info["end"])
    head = "{0} retargeted onto the rig{1}".format(name, span)
    tail = "source skeleton {0} deleted".format(deleted_namespace) if deleted_namespace else "source skeleton kept"
    return "  |  ".join(part for part in (head, connect_text.splitlines()[0], bake_text.splitlines()[0], tail) if part)


def import_and_retarget(fbx_path, name, clip_fps=None, set_timeline=True):
    import maya_rig_retarget
    from maya_scenesetup import catalog, character
    import maya_asretarget

    rig_file_ok = bool(catalog.character_file(catalog.default_rig())) and \
        __import__("os").path.isfile(catalog.character_file(catalog.default_rig()))
    posed = character.rig_present() and bool(maya_asretarget.posed_controls())
    refusal = precheck(character.rig_present(), cmds.objExists(maya_asretarget.HOLDER), posed, rig_file_ok)
    if refusal:
        return refusal

    notes = []
    cmds.undoInfo(openChunk=True, chunkName="UE anim import + retarget")
    try:
        if not character.rig_present():
            notes.append(character.add_character(catalog.default_rig()))
        namespace = records.namespace_for(name, animimport.existing_namespaces())
        info = animimport.import_clip(fbx_path, namespace, set_timeline=set_timeline,
                                      clip_fps=clip_fps, merge=False)
        nodes = cmds.namespaceInfo(namespace, listOnlyDependencyNodes=True, recurse=True, dagPath=True) or []
        source = source_root_in(nodes, lambda p: cmds.objectType(p) == "joint")
        if source is None:
            return "{0} imported into {1} but holds no joint - nothing to retarget".format(name, namespace)
        connect_text = maya_rig_retarget.connect(source_root=source)
        if not cmds.objExists(maya_asretarget.HOLDER):
            return "{0} imported as {1}; retarget refused: {2}".format(name, namespace, connect_text)
        bake_text = maya_rig_retarget.bake()
        cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
        deleted = namespace
    finally:
        cmds.undoInfo(closeChunk=True)
    line = result_line(name, info, connect_text, bake_text, deleted)
    return "  |  ".join(notes + [line]) if notes else line
```
(`posed_controls` is `maya_asretarget`'s; for the PlayerMale rig the dispatcher's module has its own — call `maya_rig_retarget.rig_module()` and use that module's `posed_controls`/`HOLDER` instead of importing `maya_asretarget` directly. Both modules define both names.)

- [ ] **Step 4: Rewrite `window.py`** — keep: cache helpers, `_status/_header/_run`, project menu, `_repopulate` (rows = `records.format_row(record)` only), `_selected_record`, `refresh` (minus the `vcs_enabled()` block), `import_line`, `export_uasset_selected`, `merge_selected` renamed `retarget_selected()`. Remove every `vcs`/`checkouts` import and function. `import_selected`:

```python
def import_selected():
    record = _selected_record()
    if record is None:
        _status("select an animation first"); return
    out = os.path.join(temp_folder(), "export.json")
    fbx = os.path.join(temp_folder(), "{0}.fbx".format(record.name))
    payload = uelink.run_script(uescripts.export_script(out, record.package, fbx), out, project=project_choice())
    exported = payload.get("path") or fbx
    set_timeline = cmds.checkBox(_TIMELINE, query=True, value=True)
    fps = payload.get("fps") or record.fps
    if retarget_selected():
        from maya_uebridge import rigimport
        _status(rigimport.import_and_retarget(exported, record.name, clip_fps=fps, set_timeline=set_timeline))
        return
    namespace = records.namespace_for(record.name, animimport.existing_namespaces())
    cmds.undoInfo(openChunk=True, chunkName="UE anim import")
    try:
        info = animimport.import_clip(exported, namespace, set_timeline=set_timeline, clip_fps=fps, merge=False)
    finally:
        cmds.undoInfo(closeChunk=True)
    _status(import_line(record.name, info))


def export_fbx_selected():
    """A plain FBX of the resolved skeleton, where the dialog says."""
    from maya_uebridge import animexport
    paths = cmds.fileDialog2(fileFilter="FBX (*.fbx)", dialogStyle=2, fileMode=0, caption="Export skeleton animation")
    if not paths:
        _status("export cancelled"); return
    info = animexport.export_hierarchy(paths[0])
    _status(animexport.export_line(os.path.basename(paths[0]), info))
```
Layout: one `formLayout`, no `tabLayout`; radio labels `["retarget onto the rig", "as a new skeleton"]`; buttons bottom row `Export FBX...`, `Export to uasset`, `IMPORT`. Window title "UE Animation Bridge". Delete a leftover `ueBridgeCheckouts` window by its literal id.

- [ ] **Step 5: Run** `tests.test_uebridge_rigimport tests.test_uebridge_window tests.test_uebridge_import tests.test_uebridge_uasset` — PASS. Full discovery — PASS.
- [ ] **Step 6: Commit** `feat(uebridge): one window, no Perforce; IMPORT adds the rig, imports, retargets, bakes and deletes the source`.

---

### Task 9: The standalone proof

**Files:**
- Create: `docs/superpowers/plans/verify_rig_pipeline.py`

Runs in mayapy standalone (`maya.standalone.initialize()`), never in the animator's Maya. Clip: `C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_1P.FBX` (a UE5 first-person clip: weapon_r and camera_bone move). Gates, each printed `PASS/FAIL <n> <text> <numbers>`, summary `N of M gates failed`:

1. `cmds.loadPlugin` for `matrixNodes`, `quatNodes`, `fbxmaya`; scene empty.
2. `import_and_retarget(clip, "Heavy1P")` returns a line containing "retargeted onto the rig" and "deleted".
3. Rig present: `ControlSet`, `Main`, `|root`; `character.rig_present()` True; a second `add_character(default_rig())` returns `RIG_PRESENT`.
4. No namespace `Heavy1P` remains; no `MoCapConstraints`.
5. Controls keyed: `FKWrist_R` etc. carry animCurves over the clip's range (read the range from the returned line and from `findKeyframe`).
6. **Expectation computed, not typed**: before the pipeline, import the same clip on its own into namespace `ref` (`animimport.import_clip(clip, "ref", set_timeline=False, merge=False)`) and sample `ref:weapon_r`, `ref:camera_bone`, `ref:hand_r` world matrices at 6 frames; delete `ref` BEFORE the pipeline (or the pipeline would see two candidates... it does not — it imports its own namespace — but the resolver's "sole skeleton" would). After the pipeline compare the rig's `weapon_r`/`camera_bone` world matrices at the same frames: worst element < 0.02 for weapon_r (the hand lands to 0.0016 cm), and camera_bone < 0.02 (note: after camera setup the bone follows the camera which was baked from the bone — same track).
7. Camera: exactly one transform with `mayaSceneSetupCamera`, named `SceneSetup_camera`; `camera_bone` carries a parentConstraint whose target is that camera; the camera's world matrix equals `placed_matrix(bone, AXIS_OFFSET)` at 3 frames to 1e-4.
8. Weapon path: attach the sword (`attach.attach(catalog.by_key("LongSword_02"), hand, bone)`) — hand/bone via `skeleton.resolve_bone`; run the pipeline a SECOND time on the same clip: the sword still linked (`bonedrive.driving_weapon(weapon_r)` is the sword), `weapon_r` again matches the reference to < 0.02, one camera (teardown + setup), no `ref`/clip namespace left.
9. Resolver: with nothing selected `skeleton.current_root()` == `|root`; with `FKWrist_R` selected the same; with the sword's mesh selected the same (it is under `hand_r`... a mesh is ignored → falls to the rig) — and with a stray extra skeleton added (`cmds.joint` chain at world level) and nothing selected still `|root` (the rig wins over "sole skeleton").

Run: `& mayapy docs/superpowers/plans/verify_rig_pipeline.py` — expect `0 of N gates failed`. Fix whatever it finds (this is where the real bugs are), re-run to green, then commit `test(verify): the rig pipeline end to end in mayapy - N gates green`.

---

### Task 10: Ship it — build, install, live smoke, docs

- [ ] Full discovery run green: `mayapy -m unittest discover -s tests -t . -v` (expect ~2050 tests, count reported).
- [ ] `& mayapy make_build.py` → `SkeldarAnim_2026-09-07.zip` beside the repo (~68 MB, ~66 files; the build verifies itself).
- [ ] Install into the animator's Maya over the bridge (runner + sender rebuilt in the scratchpad per CLAUDE.md notes 5–9, `if not os.path.exists(marker)` guard, ASCII, hardcoded paths): purge `install` from `sys.modules`, `exec` the repo's `SkeldarAnim/install.py`, `install.install(quiet=True)`. Gates through the port: `cmds.shelfLayout("SkeldarAnim", q=True, childArray=True)` labels == the nine; `maya_scenesetup.show_window()`, `maya_uebridge.show_window()` open without a traceback (`_run` traps go to the status text — read it back); `maya_hotkeys.COMMANDS` holds no `overrig.` key; `mel.eval('exists "base_OverRig_scripts"')` is 0 after a fresh Maya (state it if the session already has it sourced). Tell the animator their two hand-made RTG/BAKE buttons were replaced by the shelf's Retarget/Bake.
- [ ] CLAUDE.md: a new top section "**The AdvancedSkeleton pipeline (2026-09-07)**" — flags, moved modules, native bake, Bake's six steps, the bridge automation, one rig per scene, the resolver, the shipped rig asset and its cut; mark the OverRig/picker sections as *switched off, code intact*; update "What is here" tree, the shelf button list in `install.py`'s section, README; note the `Manny_rig_02.ma` legacy path.
- [ ] Memory: update `MEMORY.md`/`advancedskeleton-in-maya.md` with the vendor bake contract (already replicated) — one line.
- [ ] Commit `docs: CLAUDE.md for the AdvancedSkeleton pipeline`, then `git push origin feature/overrig-picker`.

---

## Self-review

- **Spec coverage**: flags (T1, T4, T5 connect gate, T6 picker_root), shelf/icons (T1), moves + ASSETS + verify paths (T2), native bake (T3), Bake's six steps (T7), bridge automation + single window + no p4 + Export FBX (T8), catalog kinds + shipped rig + paint_fresh + second-rig refusal (T5), resolver + Scene Setup buttons removed + header (T6), hotkey rows (T4), standalone proof + live smoke + docs (T9–10). Not built list needs no task.
- **Types**: `helper_plan(source_bones: {leaf: path}, rig_bones: {leaf: path}, foreign: set) -> (moves, skipped)`; `carry_helpers(...) -> (moved names, skipped, camera_text)`; `choose_root(selection_roots, rig_root, scene_roots)`; `precheck(rig_present, holder_present, posed, rig_file_ok)`; `connected_source()`/`vendor_bake(start, end)` on both retarget modules; `features()` on install — consistent across tasks.
- **Placeholders**: none; every step carries its code or its exact command.
