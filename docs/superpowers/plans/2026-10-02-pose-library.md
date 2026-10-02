# Pose Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Studio-Library-like pose library: cards of a character's BONES (or plain objects' attributes) in folders, saved from the scene with a thumbnail, applied by selecting any part of any of our rigs or skeletons (or by dragging the card onto a character / an empty floor), keyed on the active animation layer, with blend and mirror.

**Architecture:** A new package `SkeldarAnim/maya_poselib/` split by responsibility: `store` (files, stdlib), `posemath` (the bone transfer, OpenMaya-only, pure), `scene` + `capture` (reading the scene), `rigsolve` + `skelsolve` (bone targets → channel values, analytic, generalising `maya_scenesetup/fkik.py`), `keys` (the active layer and writing), `apply` (orchestration, blend, drops), `look` + `window` (the Qt window in a workspaceControl). The pure halves carry the unit tests; mayapy-standalone verify scripts prove the scene halves on the shipped rigs; a disposable GUI Maya proves the window.

**Tech Stack:** Maya 2027 Python 3 (`maya.cmds`, `maya.api.OpenMaya`), PySide6 6.8.3, stdlib `unittest` under mayapy.

**Spec:** `docs/superpowers/specs/2026-10-02-pose-library-design.md` (read it first; every rule there is a requirement).

## Global Constraints

- Work happens in the worktree `C:/!!!Work/MayaScripts-poselib` on branch `feature/pose-library`. Never edit the main checkout `C:/!!!Work/MayaScripts` (peers commit there).
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .` from the worktree root (PowerShell; never `2>&1` on mayapy; never system `python` — it is a hanging Store stub). One module: `... -m unittest tests.test_poselib_store -v`. Qt tests: `$env:QT_QPA_PLATFORM='offscreen'`.
- `store.py`, `look.py` import the stdlib only; `posemath.py` imports the stdlib, `maya.api.OpenMaya` and `maya_skeletonmap` only — a subprocess test pins each. `window.py` is the only module importing Qt; `apply.py`/`scene.py`/`rigsolve.py`/`skelsolve.py`/`keys.py`/`capture.py` import `maya.cmds` lazily or at top (they never run without Maya).
- Matrices cross module boundaries as 16-float lists (row-major, Maya's `world = local · parent` row-vector convention). Inside a module use `om.MMatrix`.
- NEVER call from a pose apply (each destroys the take): `maya_asretarget.reset_build_pose`, `maya_pmretarget.reset_build_pose`, `maya_rig_retarget.run_retarget`/`bake`, `vendor_bake`, `connect`, `maya_ikmatch.restore`, `skeletonimport.transfer`/`transfer_foreign`/`onto_existing`/`onto_skeleton`, `rigimport.ready_rig`/`retarget_imported`, `set_exact_neck`, `position_follow`, `cliplabel.*`.
- Never write `Main`, a skeleton's root, `FKNeck_M.bias`, `twistAmountDivideNeckPart1_M.input2`, `FKIK*.FKIKBlend`.
- Resolve nodes by long path or UUID inside the chosen character, never by a short name (trap 47, 187); rigs through `maya_rigs.node(rig, leaf)`.
- Rotate orders: `MEulerRotation.reorder` takes cmds' 0..5; `MTransformationMatrix.reorderRotation` takes 1..6. Use `fkik.local_channels` (0..5) for controls.
- Euler written = the solution nearest the channel's current value (`closestSolution`).
- Keys: `cmds.setKeyframe(plug, time=frame, value=v, animLayer=L)` — `v` is the FINAL value (measured). Always pass `animLayer` when any layer exists. Add the plug to a non-base layer first (`cmds.animLayer(L, edit=True, attribute=plug)`). Refuse a locked layer.
- Every apply is one undo chunk (`cmds.undoInfo(openChunk=True, chunkName="skeldarPoseApply")` … `closeChunk` in `finally`), autoKey off inside it and restored.
- Files written atomically: `path + ".part"` then `os.replace`.
- Statuses and comments in English; quotes of the animator stay Russian. Comment density like the surrounding plugin code (a docstring per function saying what and why).
- No new shelf button, no `icons/*.png` (house rule). New hub icon = a Tabler path tuple in `maya_hubicons.ICONS`.
- Commit after each task with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; `git commit -F <file>` (no PowerShell here-strings with quotes). Only files of the task.

---

## File structure

| file | responsibility |
|---|---|
| `SkeldarAnim/maya_poselib/__init__.py` | lazy `show_window` / `build_panel` (`__getattr__`), so importing the package drags in no Qt |
| `SkeldarAnim/maya_poselib/store.py` | the library on disk: root, folders, cards, read/write/rename/move/trash, search, sort (stdlib) |
| `SkeldarAnim/maya_poselib/posemath.py` | pairing, rest alignment, mirror, the parent-relative transfer, blend, regions (OpenMaya, pure) |
| `SkeldarAnim/maya_poselib/scene.py` | selection → characters / objects; a character's skeleton as data; members from the selection; source identity |
| `SkeldarAnim/maya_poselib/capture.py` | build a pose dict from the scene; the thumbnail playblast |
| `SkeldarAnim/maya_poselib/skelsolve.py` | bone targets → joint channel values on a bare skeleton |
| `SkeldarAnim/maya_poselib/rigsolve.py` | bone targets → AS control channel values (FK tree, IK ends, poles, toes, RootX_M, neck); the rig's drive matrices |
| `SkeldarAnim/maya_poselib/keys.py` | the active animation layer; writable plugs; preview / restore / key |
| `SkeldarAnim/maya_poselib/apply.py` | Apply, Apply onto a dropped character, drop onto the floor (load the source), Select objects, the Blend session |
| `SkeldarAnim/maya_poselib/look.py` | grid geometry, captions, details text (stdlib) |
| `SkeldarAnim/maya_poselib/window.py` | the workspaceControl + Qt window, the hub card's `build_panel` |
| `SkeldarAnim/poses/.gitkeep` | the shipped library folder |
| `tests/test_poselib_*.py` | unit tests per module |
| `docs/superpowers/plans/verify_poselib_solve.py` | mayapy standalone: save/solve round trips on every shipped character |
| `docs/superpowers/plans/verify_poselib_apply.py` | mayapy standalone: apply end to end (layers, mirror, blend, partial, cross-character, objects, floor drop, undo) |
| `docs/superpowers/plans/verify_poselib_gui.py` | disposable GUI Maya: the window, thumbnail, drags, blend gesture, pictures |
| `SkeldarAnim/install.py`, `maya_hub.py`, `maya_hotkeys.py`, `maya_hubicons.py`, `tests/test_install.py`, `tests/test_hub.py`, `tests/test_hotkeys.py` | integration (Task 9 only, on the latest branch) |

## Shared data shapes (every task uses these names)

```python
# pose.json, kind "character"
{
  "format": "skeldar.pose", "version": 1, "kind": "character",
  "name": "Fist", "created": "2026-10-02T18:00:00", "author": "Eugene",
  "scene": "shot_010.ma", "frame": 12.0, "fps": "ntsc",
  "character": {"key": "Manny_Rig", "model": "Manny", "kind": "rig", "label": "Manny [rig]",
                "namespace": "Manny_Rig1", "root": "root", "convention": "unreal_ue5",
                "rotation_only": False},
  "bones": {"<leaf>": {"parent": "<leaf>" or None, "canonical": "<UE5 name>" or None,
                       "rest": [16 floats], "world": [16 floats],
                       "drive": [16 floats],          # optional, rig sources only
                       "rotateOrder": 0}},
  "members": ["hand_l", "index_01_l"],
  "regions": ["Hand L"],
  "objects": [],
}
# pose.json, kind "objects"
{"format": "skeldar.pose", "version": 1, "kind": "objects", "name": ..., "created": ..., "author": ...,
 "scene": ..., "frame": ..., "fps": ...,
 "objects": [{"name": "pCube1", "path": "|grp|pCube1", "attrs": {"translateX": 1.0, "visibility": 1.0}}]}

# a skeleton read from the scene (scene.skeleton): {leaf: Bone-dict}
{"<leaf>": {"path": "|Manny_Character|root|pelvis", "parent": "<leaf>" or None,
            "canonical": "pelvis" or None, "rest": [16], "world": [16],
            "rotateOrder": 0, "jointOrient": [3], "rotateAxis": [3]}}

# a solution (rigsolve.solve / skelsolve.solve)
Solution = namedtuple("Solution", "values notes skipped")
# values: {"Manny_Rig1:FKShoulder_L.rotateX": 12.5, ...}  (FINAL channel values)
# notes:  ["the FK forearm twist is lost on arm_r (an IK elbow is a hinge): 31 deg"]
# skipped: {"weapon_r": "driven by a constraint"}
```

`CharacterRef = namedtuple("CharacterRef", "kind root rig label key model namespace")`:
`kind` "rig" | "skeleton"; `root` the game skeleton's root long path; `rig` a `maya_rigs.Rig` or None; `label` the outliner/catalog label; `key`/`model` the catalog row or None; `namespace` "" for a plain skeleton.

---

### Task 1: The library on disk (`store.py`)

**Files:**
- Create: `SkeldarAnim/maya_poselib/__init__.py`, `SkeldarAnim/maya_poselib/store.py`, `SkeldarAnim/poses/.gitkeep`
- Test: `tests/test_poselib_store.py`

**Interfaces:**
- Produces:
  - `ROOT_VAR = "skeldarPoseLibraryRoot"`, `CARD_SUFFIX = ".pose"`, `POSE_FILE = "pose.json"`, `THUMB_FILE = "thumbnail.jpg"`, `FORMAT = "skeldar.pose"`, `VERSION = 1`, `SORTS = ("name", "newest", "character")`
  - `Card = namedtuple("Card", "path folder name created author label kind count regions thumbnail")`
  - `default_root(plugin_dir) -> str`, `library_root(option_value, plugin_dir) -> str`
  - `safe_name(text, fallback="Pose") -> str`, `unique_name(root, folder, name) -> str`
  - `folders(root) -> list[str]` (relative, "/"-separated, sorted case-insensitively, never `""`)
  - `cards(root, folder="", recursive=True) -> (list[Card], list[str])` (cards, broken paths)
  - `read(path) -> dict` (raises `ValueError` on a bad file)
  - `write(root, folder, name, data, thumbnail=None, replace=False) -> str` (the card path)
  - `set_thumbnail(path, image) -> None`, `rename(path, name) -> str`, `move(path, root, folder) -> str`
  - `remove(path, trash) -> str` (moved into `trash`, stamped), `trash_dir(user_app_dir) -> str`
  - `make_folder(root, parent, name) -> str`, `rename_folder(root, rel, name) -> str`
  - `filter_cards(cards, query) -> list[Card]`, `sort_cards(cards, key) -> list[Card]`

- [ ] **Step 1: Write the failing tests**

```python
"""The pose library on disk (2026-10-02): a card is a folder <Name>.pose holding pose.json and a
thumbnail, a catalog is a plain folder; written atomically, deleted to a trash folder. Stdlib only.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from maya_poselib import store

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(store.__file__)))


def pose(name="Fist", label="Manny [rig]", members=("hand_l",), created="2026-10-02T10:00:00"):
    return {"format": store.FORMAT, "version": store.VERSION, "kind": "character", "name": name,
            "created": created, "author": "A", "character": {"label": label},
            "members": list(members), "regions": ["Hand L"], "bones": {}}


class Root(unittest.TestCase):

    def test_default_is_the_plugins_poses_folder(self):
        self.assertEqual(store.default_root("C:/p/SkeldarAnim"), "C:/p/SkeldarAnim/poses")

    def test_the_option_wins_only_when_it_is_a_folder(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        self.assertEqual(store.library_root(tmp, "C:/p"), tmp.replace("\\", "/"))
        self.assertEqual(store.library_root(os.path.join(tmp, "nope"), "C:/p"), "C:/p/poses")
        self.assertEqual(store.library_root("", "C:/p"), "C:/p/poses")


class Names(unittest.TestCase):

    def test_safe_name(self):
        self.assertEqual(store.safe_name('a:b*c?'), "a_b_c_")
        self.assertEqual(store.safe_name("  Fist  pose. "), "Fist pose")
        self.assertEqual(store.safe_name("CON"), "_CON")
        self.assertEqual(store.safe_name(""), "Pose")
        self.assertEqual(len(store.safe_name("x" * 200)), 80)


class Cards(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_write_read_list(self):
        path = store.write(self.root, "Hands", "Fist", pose())
        self.assertTrue(path.endswith("Hands/Fist.pose"))
        self.assertEqual(store.read(path)["name"], "Fist")
        found, broken = store.cards(self.root)
        self.assertEqual([c.name for c in found], ["Fist"])
        self.assertEqual(found[0].folder, "Hands")
        self.assertEqual(found[0].label, "Manny [rig]")
        self.assertEqual(found[0].count, 1)
        self.assertEqual(broken, [])
        self.assertEqual(store.folders(self.root), ["Hands"])

    def test_no_part_file_is_left(self):
        path = store.write(self.root, "", "Fist", pose())
        self.assertEqual(sorted(os.listdir(path)), [store.POSE_FILE])

    def test_refuses_to_overwrite_unless_asked(self):
        store.write(self.root, "", "Fist", pose())
        with self.assertRaises(ValueError):
            store.write(self.root, "", "Fist", pose())
        store.write(self.root, "", "Fist", pose(members=("a", "b")), replace=True)
        self.assertEqual(store.cards(self.root)[0][0].count, 2)

    def test_unique_name(self):
        store.write(self.root, "", "Fist", pose())
        self.assertEqual(store.unique_name(self.root, "", "Fist"), "Fist 2")

    def test_a_broken_card_is_reported_not_raised(self):
        bad = os.path.join(self.root, "Bad.pose")
        os.makedirs(bad)
        with open(os.path.join(bad, store.POSE_FILE), "w") as handle:
            handle.write("{nope")
        found, broken = store.cards(self.root)
        self.assertEqual(found, [])
        self.assertEqual(len(broken), 1)

    def test_thumbnail_rename_move_remove(self):
        image = os.path.join(self.root, "x.jpg")
        with open(image, "wb") as handle:
            handle.write(b"\xff\xd8jpg")
        path = store.write(self.root, "", "Fist", pose(), thumbnail=image)
        self.assertTrue(store.cards(self.root)[0][0].thumbnail.endswith(store.THUMB_FILE))
        path = store.rename(path, "Grip")
        self.assertEqual(store.read(path)["name"], "Grip")
        store.make_folder(self.root, "", "Hands")
        path = store.move(path, self.root, "Hands")
        self.assertEqual(store.cards(self.root)[0][0].folder, "Hands")
        trash = os.path.join(self.root, "_trash_test")
        gone = store.remove(path, trash)
        self.assertTrue(os.path.isdir(gone))
        self.assertEqual(store.cards(self.root)[0], [])

    def test_folders_skip_cards_and_hidden(self):
        store.write(self.root, "A/B", "P", pose())
        os.makedirs(os.path.join(self.root, ".git"))
        self.assertEqual(store.folders(self.root), ["A", "A/B"])

    def test_rename_folder(self):
        store.write(self.root, "A", "P", pose())
        self.assertEqual(store.rename_folder(self.root, "A", "Hands"), "Hands")
        self.assertEqual(store.cards(self.root)[0][0].folder, "Hands")


class SearchSort(unittest.TestCase):

    def card(self, name, folder="", label="Manny [rig]", created="2026-10-01T00:00:00"):
        return store.Card("p/" + name, folder, name, created, "A", label, "character", 1, [], "")

    def test_every_term_narrows(self):
        cards = [self.card("Fist", "Hands"), self.card("Run", "Body"), self.card("Fist", "Body",
                                                                                  "Creep [rig]")]
        self.assertEqual(len(store.filter_cards(cards, "fist")), 2)
        self.assertEqual(len(store.filter_cards(cards, "fist creep")), 1)
        self.assertEqual(len(store.filter_cards(cards, "")), 3)

    def test_sorts(self):
        a = self.card("b", created="2026-10-01T00:00:00")
        b = self.card("A", created="2026-10-03T00:00:00", label="Creep [rig]")
        self.assertEqual([c.name for c in store.sort_cards([a, b], "name")], ["A", "b"])
        self.assertEqual([c.name for c in store.sort_cards([a, b], "newest")], ["A", "b"])
        self.assertEqual([c.name for c in store.sort_cards([a, b], "character")], ["A", "b"])


class Purity(unittest.TestCase):

    def test_stdlib_only(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_poselib.store; "
                "bad = [m for m in sys.modules if m.startswith(('maya.', 'PySide'))]; "
                "print(bad); sys.exit(1 if bad else 0)") % PLUGIN
        self.assertEqual(subprocess.call([sys.executable, "-c", code]), 0)
```

- [ ] **Step 2: Run them to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_poselib_store -v`
Expected: ImportError (no `maya_poselib`).

- [ ] **Step 3: Implement**

`__init__.py`:

```python
"""The Pose Library (2026-10-02): cards of a character's bones, applied to any rig or skeleton.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md
"""


def __getattr__(name):
    # lazy: importing the package drags neither Qt nor Maya in (the maya_overrig rule)
    if name in ("show_window", "build_panel", "is_open"):
        from maya_poselib import window
        return getattr(window, name)
    raise AttributeError(name)
```

`store.py` — implement every function of the Interfaces block. Rules that matter:
- `default_root(plugin_dir)` = `plugin_dir.replace("\\", "/").rstrip("/") + "/poses"`; `library_root` returns the option (forward slashes) when `os.path.isdir(option_value)`, else the default.
- `safe_name`: strip, collapse whitespace, replace `<>:"/\\|?*` and control chars with `_`, strip trailing dots and spaces and leading dots, cap 80, a Windows device name (`CON PRN AUX NUL COM1..9 LPT1..9`, case-insensitive) gets a `_` prefix, empty → fallback.
- A card folder is `<safe_name>.pose`; `folders()` walks `os.walk`, never descends into `*.pose` or names starting with `.` or `_trash`, returns relative paths with `/`.
- `cards()` reads each `pose.json`; `Card.label` = `data["character"]["label"]` for kind character else `"objects"`; `count` = `len(members)` or `len(objects)`; `thumbnail` = the image path when it exists else `""`; `created` from the file (fallback the folder's mtime as ISO). A JSON error or a wrong `format` goes to `broken`.
- `write()`: `os.makedirs(folder)`, refuse an existing card unless `replace`; write `pose.json` to `pose.json.part` then `os.replace`; `data["name"]` is set to the card's name; a thumbnail is copied with `shutil.copy2` to `THUMB_FILE`.
- `rename()` renames the folder AND rewrites `name` inside; refuses a taken name with `ValueError`.
- `remove(path, trash)`: `os.makedirs(trash)`; `shutil.move(path, trash/<YYYYmmdd_HHMMSS>_<basename>)`.
- `trash_dir(user_app_dir)` = `<user_app_dir>/SkeldarPoses_trash`.
- `filter_cards`: every whitespace term must occur, case-insensitively, in `name + " " + folder + " " + label`.
- `sort_cards`: `name` → `name.lower()`; `newest` → `created` descending; `character` → `(label.lower(), name.lower())`.

`SkeldarAnim/poses/.gitkeep`: empty file.

- [ ] **Step 4: Run them to see them pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_poselib_store -v` → all OK.

- [ ] **Step 5: Commit** — `feat(poselib): the library on disk - cards, folders, search, sort`

---

### Task 2: The bone transfer (`posemath.py`)

**Files:**
- Create: `SkeldarAnim/maya_poselib/posemath.py`
- Test: `tests/test_poselib_posemath.py`

**Interfaces:**
- Consumes: `maya_skeletonmap.covers_ue_core`, `distribute`, `direction_children`, `canonical_parents` (all pure).
- Produces (all pure; `bones` dicts are `{leaf: {"parent", "canonical", "rest", "world", ["drive"]}}`):
  - `matrix(values) -> om.MMatrix`, `flat(m) -> list`, `rigid(m)`, `rotation(m)`, `position(m) -> om.MVector`, `angle(a, b) -> float` (degrees between two rotations), `direction_angle(a, b)`
  - `opposite(name) -> str | None` — `hand_l`↔`hand_r`, `LeftHand`↔`RightHand`, `Left_Arm`↔`Right_Arm`, `hand.L`↔`hand.R`, `DEF-hand.L`, `upperarm_L_`↔`upperarm_R_`, `Bip001 L Hand`↔`Bip001 R Hand`; centre bones answer None
  - `root_of(bones) -> leaf` (the shallowest bone whose parent is None or not in the dict; ties sorted)
  - `ue_named(bones) -> bool` (`covers_ue_core` of the leaves)
  - `pairs(source, target) -> {target leaf: source leaf}`
  - `alignments(pairs, source, target) -> {target leaf: om.MMatrix}`
  - `scale_between(source, target, pairs) -> float`
  - `mirror(source, members) -> (dict, list)`
  - `targets(source, target, pairs, members, use_drive=False, scale=1.0, pelvis="pelvis") -> {target leaf: om.MMatrix}`
  - `blend(a, b, alpha) -> om.MMatrix`
  - `REGIONS` and `regions(names) -> list[str]` (`Head`, `Spine`, `Pelvis`, `Arm L`, `Hand L`, `Arm R`, `Hand R`, `Leg L`, `Leg R`, in that order; from canonical UE5 names)
  - `HELPERS = ("ik_", "weapon_", "camera_", "interaction", "center_of_mass")`, `is_helper(leaf) -> bool`, `is_twist(leaf) -> bool` (`"_twist_"` in the leaf)

**The rules** (copy them into the docstrings):

1. **Pairing.** Both `ue_named` → by leaf: every target leaf that the source carries; a UE4 target under a UE5 source (`spine_05` in the source, neither `spine_04` nor `spine_05` in the target) takes `{"spine_01": "spine_02", "spine_02": "spine_04", "spine_03": "spine_05"}`. Otherwise by canonical name (`bones[leaf]["canonical"]`): a target bone whose canonical name a source bone carries; spine (`spine_*`) and neck (`neck_*`) are paired chain onto chain with `distribute(source_chain, target_chain)` where each chain is the ordered list of that side's canonical spine/neck bones (bottom-up by canonical name). Helpers (`is_helper`) are paired only by leaf on the UE road. **The two roots are always paired** (`root_of`).
2. **Rest alignment** `A[t]` (rotation): the minimal rotation `om.MQuaternion(t_dir, s_dir)` taking the target's rest direction onto the source's, where the direction child is `direction_children(canonical_parents_of_target)` (use the canonical name for the rule, map back to leaves); the target direction is the child's offset in the bone's CURRENT frame re-expressed in its rest frame (trap 171: `local = (pos(child_now) - pos(bone_now)) · rigid(bone_now)⁻¹`, `t_dir = local · rigid(bone_rest)` as a vector); the source direction is the child's rest position minus the bone's rest position; a bone with no paired direction child inherits its nearest paired ancestor's `A`; the root's `A` is identity. For a twin every `A` is ≈ identity.
3. **The transfer.** Let `P[s]` be `source[s]["drive"]` when `use_drive` and the bone has one, else `source[s]["world"]`. Process target bones parents first (depth order). For a target bone `t` that is a member's partner (`pairs[t] in members`), with `tp` its nearest ancestor present in `pairs` and `s = pairs[t]`, `sp = pairs[tp]`:

   ```python
   O_t  = rigid(T_rest[t]) * A[t] * rigid(S_rest[s]).inverse()
   O_tp = rigid(T_rest[tp]) * A[tp] * rigid(S_rest[sp]).inverse()
   R_t  = rotation(O_t * rotation(P[s]) * rotation(P[sp]).inverse() * O_tp.inverse() * rotation(W[tp]))
   ```

   where `W[tp]` is `tp`'s RESULT (its target when it was solved, else its current world). Every other target bone follows its parent rigidly: `W[x] = (T_now[x] * T_now[parent].inverse()) * W[parent]` (so a non-member between two members, and every descendant, moves with what moved). Positions: every bone keeps its own local translation — `W[t]` gets `R_t` and the position `local_translation(t) * W[parent]` with `local_translation = position(T_now[t] * T_now[parent].inverse())`. The root keeps its current world. **The pelvis** (target leaf `pelvis` paired with a member — use the canonical name `pelvis`), position only:

   ```python
   d_local = (position(P[s_pelvis]) - position(P[s_root])) * rotation(P[s_root]).inverse()   # in the source root's frame
   d_t = d_local * rotation(O_root).inverse() * scale       # into the target root's frame
   pos = position(T_now[t_root]) + d_t * rotation(T_now[t_root])
   ```

   Returns `{leaf: om.MMatrix}` for EVERY target bone (unchanged ones = current world).
4. **Scale** (`scale_between`): the pelvis's rest height above the root's rest along world Y, target over source; 1.0 when either pelvis is missing or a height is below 1 cm; a ratio within 2 % of 1 is 1.0.
5. **Mirror** (`mirror`): in the source root's frame. `l` = normalised (left upper arm or thigh rest position − its opposite's), in root-local coordinates; `F = I − 2 l lᵀ` as an `om.MMatrix` (3×3 in the upper left). For every bone `s` with an opposite `ō` (`opposite`) present: `r = rot(S_rest[x]) * rot(S_rest[root]).inverse()`, `p = rot(P[x]) * rot(P[root]).inverse()`, `D = r.inverse() * p` (the root-space delta), and the mirrored bone takes `p' = r[s] * F * D[ō] * F`; a centre bone takes `p' = r[s] * F * D[s] * F`; then back to world `P'[s] = p' * rot(P[root])` with `P[s]`'s position. The pelvis position mirrors: `d = (pos(P[pel]) - pos(P[root])) * rot(P[root]).inverse()`, `d' = d * F`. Both `world` and `drive` are mirrored. Members swap to their opposites (centre members stay). Returns `(new_source, new_members)`.
6. **Blend** (`blend`): translation lerped, rotation slerped the short way (copy `fkik.blended`).

- [ ] **Step 1: Write the failing tests**

```python
"""posemath: pairing, rest alignment, the parent-relative transfer, mirror, blend - on synthetic
skeletons built here (no Maya scene).

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md
"""
import math
import os
import subprocess
import sys
import unittest

import maya.api.OpenMaya as om

from maya_poselib import posemath as pm


def trs(t=(0, 0, 0), r=(0, 0, 0)):
    tm = om.MTransformationMatrix()
    tm.setRotation(om.MEulerRotation(*[math.radians(v) for v in r]))
    tm.setTranslation(om.MVector(*t), om.MSpace.kTransform)
    return tm.asMatrix()


CHAIN = [("root", None, (0, 0, 0)), ("pelvis", "root", (0, 95, 0)),
         ("spine_01", "pelvis", (0, 10, 0)), ("upperarm_l", "spine_01", (15, 30, 0)),
         ("lowerarm_l", "upperarm_l", (28, 0, 0)), ("hand_l", "lowerarm_l", (26, 0, 0)),
         ("middle_01_l", "hand_l", (8, 0, 0)), ("upperarm_r", "spine_01", (-15, 30, 0)),
         ("lowerarm_r", "upperarm_r", (-28, 0, 0)), ("hand_r", "lowerarm_r", (-26, 0, 0)),
         ("middle_01_r", "hand_r", (-8, 0, 0)), ("thigh_l", "pelvis", (10, -5, 0)),
         ("calf_l", "thigh_l", (0, -45, 0)), ("foot_l", "calf_l", (0, -42, 0)),
         ("thigh_r", "pelvis", (-10, -5, 0)), ("calf_r", "thigh_r", (0, -45, 0)),
         ("foot_r", "calf_r", (0, -42, 0)), ("head", "spine_01", (0, 50, 0))]


def skeleton(locals_=None, scale=1.0, rest_locals=None, place=om.MMatrix()):
    """{leaf: bone} with world matrices from local (translate, rotate) per bone."""
    locals_ = locals_ or {}
    worlds, rests, out = {}, {}, {}
    for name, parent, t in CHAIN:
        t = tuple(v * scale for v in t)
        rest_local = trs(t, (rest_locals or {}).get(name, (0, 0, 0)))
        local = trs(t, locals_.get(name, (rest_locals or {}).get(name, (0, 0, 0))))
        rests[name] = rest_local * (rests[parent] if parent else om.MMatrix())
        worlds[name] = local * (worlds[parent] if parent else place)
        out[name] = {"parent": parent, "canonical": name, "rest": pm.flat(rests[name]),
                     "world": pm.flat(worlds[name])}
    return out


class Pairing(unittest.TestCase):

    def test_ue_by_leaf_and_roots(self):
        s, t = skeleton(), skeleton()
        pairs = pm.pairs(s, t)
        self.assertEqual(pairs["hand_l"], "hand_l")
        self.assertEqual(pairs["root"], "root")

    def test_canonical_road(self):
        s = skeleton()
        renamed = {}
        for leaf, bone in s.items():
            new = "mx_" + leaf
            renamed[new] = dict(bone, parent=("mx_" + bone["parent"]) if bone["parent"] else None)
        pairs = pm.pairs(renamed, skeleton())
        self.assertEqual(pairs["hand_l"], "mx_hand_l")
        self.assertEqual(pairs["root"], "mx_root")


class Opposite(unittest.TestCase):

    def test_spellings(self):
        for a, b in (("hand_l", "hand_r"), ("LeftHand", "RightHand"), ("Left_Arm", "Right_Arm"),
                     ("hand.L", "hand.R"), ("Bip001 L Hand", "Bip001 R Hand"),
                     ("upperarm_L_", "upperarm_R_")):
            self.assertEqual(pm.opposite(a), b)
            self.assertEqual(pm.opposite(b), a)
        self.assertIsNone(pm.opposite("spine_01"))


class Transfer(unittest.TestCase):

    def test_twin_full_pose_is_exact(self):
        pose = {"upperarm_l": (0, 30, 40), "lowerarm_l": (0, 0, 50), "hand_l": (10, 20, 30),
                "spine_01": (5, 0, 10)}
        s = skeleton(pose)
        t = skeleton()
        out = pm.targets(s, t, pm.pairs(s, t), [b for b in s if b != "root"])
        for leaf in ("upperarm_l", "lowerarm_l", "hand_l", "spine_01"):
            self.assertLess(pm.angle(out[leaf], pm.matrix(s[leaf]["world"])), 1e-6, leaf)

    def test_the_root_stays_and_the_pose_is_relative(self):
        pose = {"pelvis": (0, 0, 20), "upperarm_l": (0, 30, 40)}
        s = skeleton(pose)
        turned = trs((300, 0, -50), (0, 90, 0))
        t = skeleton(place=turned)
        out = pm.targets(s, t, pm.pairs(s, t), ["pelvis", "upperarm_l"])
        self.assertLess(pm.angle(out["root"], turned), 1e-9)
        want = pm.matrix(s["upperarm_l"]["world"]) * turned
        self.assertLess(pm.angle(out["upperarm_l"], want), 1e-6)

    def test_a_hand_pose_lands_on_the_arm_as_it_stands(self):
        s = skeleton({"hand_l": (0, 0, 45), "upperarm_l": (0, 0, 80)})
        t = skeleton({"upperarm_l": (0, 60, 0)})
        out = pm.targets(s, t, pm.pairs(s, t), ["hand_l"])
        self.assertLess(pm.angle(out["upperarm_l"], pm.matrix(t["upperarm_l"]["world"])), 1e-9)
        local_s = pm.rotation(pm.matrix(s["hand_l"]["world"])) * \
            pm.rotation(pm.matrix(s["lowerarm_l"]["world"])).inverse()
        local_t = pm.rotation(out["hand_l"]) * pm.rotation(out["lowerarm_l"]).inverse()
        self.assertLess(pm.angle(local_s, local_t), 1e-6)

    def test_other_proportions_keep_lengths_and_scale_the_pelvis(self):
        s = skeleton({"pelvis": (0, 0, 0)}, scale=1.0)
        t = skeleton(scale=2.0)
        pairs = pm.pairs(s, t)
        scale = pm.scale_between(s, t, pairs)
        self.assertAlmostEqual(scale, 2.0, 6)
        out = pm.targets(s, t, pairs, ["pelvis", "upperarm_l"], scale=scale)
        self.assertAlmostEqual(pm.position(out["pelvis"]).y, 190.0, 6)
        arm = (pm.position(out["lowerarm_l"]) - pm.position(out["upperarm_l"])).length()
        self.assertAlmostEqual(arm, 56.0, 6)

    def test_rest_alignment_points_bones_like_the_source(self):
        # the source's arm rests 40 deg down (an A-pose), the target's level (a T-pose)
        s = skeleton({"upperarm_l": (0, 0, -40)}, rest_locals={"upperarm_l": (0, 0, -40)})
        t = skeleton()
        out = pm.targets(s, t, pm.pairs(s, t), ["upperarm_l"])
        s_dir = pm.position(pm.matrix(s["lowerarm_l"]["world"])) - \
            pm.position(pm.matrix(s["upperarm_l"]["world"]))
        t_dir = pm.position(out["lowerarm_l"]) - pm.position(out["upperarm_l"])
        self.assertLess(pm.direction_angle(s_dir, t_dir), 1e-5)


class Mirror(unittest.TestCase):

    def test_left_takes_the_right_mirrored(self):
        s = skeleton({"upperarm_r": (0, 30, -40)})
        m, members = pm.mirror(s, ["upperarm_r"])
        self.assertEqual(members, ["upperarm_l"])
        expect = skeleton({"upperarm_l": (0, -30, 40)})
        self.assertLess(pm.angle(pm.matrix(m["upperarm_l"]["world"]),
                                 pm.matrix(expect["upperarm_l"]["world"])), 1e-6)

    def test_twice_is_identity(self):
        s = skeleton({"upperarm_r": (10, 30, -40), "spine_01": (0, 20, 5)})
        once, mem = pm.mirror(s, ["upperarm_r", "spine_01"])
        twice, mem2 = pm.mirror(once, mem)
        self.assertEqual(sorted(mem2), ["spine_01", "upperarm_r"])
        for leaf in ("upperarm_r", "spine_01"):
            self.assertLess(pm.angle(pm.matrix(twice[leaf]["world"]),
                                     pm.matrix(s[leaf]["world"])), 1e-6)


class Blend(unittest.TestCase):

    def test_half(self):
        a, b = trs((0, 0, 0), (0, 0, 0)), trs((10, 0, 0), (0, 0, 90))
        half = pm.blend(a, b, 0.5)
        self.assertAlmostEqual(pm.position(half).x, 5.0, 9)
        self.assertAlmostEqual(pm.angle(half, a), 45.0, 6)


class Regions(unittest.TestCase):

    def test_names(self):
        # REGIONS order: Head, Spine, Pelvis, Arm L, Hand L, Arm R, Hand R, Leg L, Leg R
        self.assertEqual(pm.regions(["hand_l", "index_01_l", "upperarm_r", "head"]),
                         ["Head", "Hand L", "Arm R"])


class Purity(unittest.TestCase):

    def test_imports(self):
        plugin = os.path.dirname(os.path.dirname(os.path.abspath(pm.__file__)))
        code = ("import sys; sys.path.insert(0, %r); import maya_poselib.posemath; "
                "bad = [m for m in sys.modules if m.startswith(('maya.cmds', 'PySide'))]; "
                "sys.exit(1 if bad else 0)") % plugin
        self.assertEqual(subprocess.call([sys.executable, "-c", code]), 0)
```

`regions` returns the present regions in `REGIONS` order. Region rules: `Head` = neck_*, head; `Spine` = spine_*; `Pelvis` = pelvis; `Arm <S>` = clavicle, upperarm, lowerarm, their twists; `Hand <S>` = hand and every finger/metacarpal; `Leg <S>` = thigh, calf, foot, ball, their twists.

- [ ] **Step 2:** run, expect failures (no module).
- [ ] **Step 3:** implement `posemath.py` per the rules above. Rest/world/drive values arrive as lists; convert with `matrix()`. Use `om.MQuaternion(u, v)` for the minimal rotation; `om.MQuaternion.slerp` for blend. Keep the functions small (one rule each) with docstrings.
- [ ] **Step 4:** run `tests.test_poselib_posemath` → OK.
- [ ] **Step 5: Commit** — `feat(poselib): posemath - pair, align, transfer, mirror, blend`

---

### Task 3: The active layer and writing values (`keys.py`)

**Files:**
- Create: `SkeldarAnim/maya_poselib/keys.py`
- Test: `tests/test_poselib_keys.py`

**Interfaces:**
- Produces:
  - `Layer = namedtuple("Layer", "name base additive locked quaternion")`
  - pure `pick_layer(layers) -> (Layer | None, refusal)`; `layers` = list of dicts `{name, base, selected, locked, override, quaternion, order}` (`order` = stack position, larger is higher). Rule: no layers → `(None, "")`; the selected non-base layers → the highest `order`; none selected (or only the base) → the base; a chosen locked layer → `(None, "the animation layer <name> is locked - unlock it or pick another")`.
  - pure `input_kind(source_type) -> "free" | "curve" | "layer" | "driven"` (`None` → free; a type starting `animCurveT` → curve; `animBlendNode*` → layer; anything else → driven).
  - `active_layer() -> (Layer | None, refusal)` (reads the scene, calls `pick_layer`)
  - `writable(plug) -> (bool, reason)` (locked → `"locked"`; driven → `"driven by <node>"`)
  - `current(plugs) -> {plug: float}`
  - `preview(values) -> None` (setAttr each writable plug; skips silently)
  - `write(values, frame, layer) -> (count, notes)` — adds plugs to a non-base layer, then `setKeyframe(plug, time=frame, value=v, animLayer=layer.name)` (no `animLayer` when `layer is None`); counts keys; notes name skipped plugs (grouped by reason).
  - `quaternion_note(layer) -> str` (non-empty when `layer.quaternion` and additive: the press refuses such a layer for ROTATE channels, the note names it; translate channels are fine).

- [ ] **Step 1: Write the failing tests** — `pick_layer` and `input_kind` exhaustively (no layers; base only; one selected; two selected → higher order; locked chosen → refusal; base selected while another not → base), plus a fake-`cmds` test of `write`:

```python
class FakeCmds(object):
    def __init__(self):
        self.calls = []
        self.layer_attrs = {"AddL": set()}

    def animLayer(self, name=None, **kw):
        if kw.get("edit") and "attribute" in kw:
            self.layer_attrs[name].add(kw["attribute"])
            self.calls.append(("add", name, kw["attribute"]))
            return None
        if kw.get("query") and kw.get("attribute"):
            return sorted(self.layer_attrs.get(name, ()))
        raise AssertionError(kw)

    def setKeyframe(self, plug, **kw):
        self.calls.append(("key", plug, kw.get("time"), kw.get("value"), kw.get("animLayer")))
        return 1

    def getAttr(self, plug, **kw):
        return False                       # never locked in this fake

    def listConnections(self, plug, **kw):
        return None


class Write(unittest.TestCase):
    def test_adds_then_keys_final_values_on_the_layer(self):
        fake = FakeCmds()
        keys.cmds = fake
        layer = keys.Layer("AddL", False, True, False, False)
        count, notes = keys.write({"a:FKShoulder_L.rotateX": 12.0}, 5.0, layer)
        self.assertEqual(count, 1)
        self.assertIn(("add", "AddL", "a:FKShoulder_L.rotateX"), fake.calls)
        self.assertIn(("key", "a:FKShoulder_L.rotateX", 5.0, 12.0, "AddL"), fake.calls)

    def test_no_layers_no_flag(self):
        fake = FakeCmds()
        keys.cmds = fake
        keys.write({"j.rotateX": 1.0}, 3.0, None)
        self.assertIn(("key", "j.rotateX", 3.0, 1.0, None), fake.calls)
```

(Rebind the module attribute `keys.cmds = fake` — CLAUDE.md's rule — and restore it in `tearDown`.)

- [ ] **Step 2:** run, expect failure.
- [ ] **Step 3:** implement. `active_layer()`: `root = cmds.animLayer(query=True, root=True)`; no root → `(None, "")`; layers = `[root] + cmds.animLayer(root, query=True, children=True)` walked depth-first (children of children too; `order` = index in that walk); per layer `selected`, `lock`, `override`, `quaternion = getAttr(layer + ".rotationAccumulationMode") == 1`. `write()` keys with `cmds.setKeyframe(plug, time=(frame, frame), value=v, animLayer=name)` — note `time` as a tuple works too; keep `time=frame` if measured fine. The base layer's name is `layer.name` too (`BaseAnimation`); do not add plugs to the base.
- [ ] **Step 4:** tests OK.
- [ ] **Step 5: Commit** — `feat(poselib): keys - the active animation layer, preview, final-value keys`

---

### Task 4: Grid geometry and texts (`look.py`)

**Files:**
- Create: `SkeldarAnim/maya_poselib/look.py`
- Test: `tests/test_poselib_look.py`

**Interfaces:**
- Produces (stdlib, pure; sizes are physical px, `scale` = `mayaDpiSetting -q -realScaleValue`):
  - `CELL_MIN = 72`, `CELL_MAX = 200`, `CELL_DEFAULT = 112`, `GAP = 8`, `NAME_H = 34` (two lines: name + character chip), `GHOST = 96`, `THROTTLE_MS = 33`, `DOT = "·"`
  - `grid(width, count, cell, scale=1.0) -> (cols, rects, height)` — columns of `cell*scale` (clamped to CELL_MIN..CELL_MAX), as many as fit (≥ 1), spread so the row fills the width, rects `(x, y, w, h)` of the square part, `height` incl. the name strips and gaps
  - `visible(rects, top, bottom, scale=1.0) -> list[int]` (indexes whose tile intersects [top, bottom])
  - `hit(rects, x, y, scale=1.0) -> int | None` (square + name strip)
  - `drop_caption(name, aim) -> (text, good)` with aims `{"kind": "character", "label"}` → `"Fist · onto Manny_Rig1"`, `{"kind": "floor", "label", "point"}` → `"Fist · a new Manny [rig] · floor (120, -36)"`, `{"kind": "folder", "folder"}` → `"Fist · move to Hands"`, `{"kind": "none", "text"}` → `(text, False)`, over the window → `("release off the window to apply", False)`
  - `details(card, data) -> list[str]` (lines: label, `N bones · Hand L, Arm L`, `author · 2026-10-02 18:00`, `frame 12 · shot_010.ma`)
  - `status_line(applied) -> str` for the apply summary (Task 7 gives the dict)

- [ ] **Step 1:** tests: `grid(1000, 7, 112)` → 7 columns? (1000 // (112+8) = 8 → min(8, 7) = 7 columns, one row); `grid(300, 7, 112)` → 2 columns, 4 rows, height = 4*(cell+NAME_H) + 3*GAP; `hit` inside the square and inside the name strip; `visible` culls; captions exact strings above; `details` for a character card and an objects card.
- [ ] **Step 2–4:** implement until green.
- [ ] **Step 5: Commit** — `feat(poselib): look - the card grid's geometry and texts`

---

### Task 5: Reading the scene (`scene.py`, `capture.py`)

**Files:**
- Create: `SkeldarAnim/maya_poselib/scene.py`, `SkeldarAnim/maya_poselib/capture.py`
- Test: `tests/test_poselib_scene.py` (pure parts with fakes)
- Verify (part of): `docs/superpowers/plans/verify_poselib_solve.py` phase `save` (written in Task 6; this task leaves `scene`/`capture` callable from it)

**Interfaces:**
- Consumes: `maya_rigs.rigs/rig_of/node/group_of/group_root/label`, `maya_scenesetup.weaponspace.hand_for`, `maya_scenesetup.armor.bone_for`, `maya_uebridge.skeletonimport.bare_roots/_skin_root/_top_joint/skeleton_label`, `maya_scenesetup.deletion.recorded`, `maya_scenesetup.catalog.character_by_label/character_by_key`, `maya_retargetmode.rest_world`, `maya_skeletonmap.recognize/convention_of`, `maya_asretarget.our_bone_map/rotation_mode`, `posemath`, `rigsolve.drive_matrices` (Task 6 — import lazily inside `capture.build_pose`).
- Produces:
  - `CharacterRef` (see Shared data shapes)
  - `characters(selection=None) -> (list[CharacterRef], list[str])` — every character the selection touches (deduplicated, in selection order) and the selected transforms that belong to none
  - `character_of(path, rigs=None) -> CharacterRef | None`
  - `all_characters() -> list[CharacterRef]` (every rig with a game skeleton, every bare skeleton)
  - `skeleton(ref) -> (bones, convention)` — the Shared shape; canonical names from `recognize` over the whole skeleton with REST positions (`rest_world`); a refusal leaves canonical = the leaf for UE-named skeletons, else None
  - `members_from_selection(ref, selection, bones) -> list[str]` — the spec's Save rules (controls through `our_bone_map` + the limb/hand expansions; joints themselves; anything else → `whole_body(bones)`)
  - `whole_body(bones) -> list[str]` — every bone but helpers (`posemath.is_helper`) and the root
  - `limb_bones(bones, limb, side) -> list[str]` (`arm`: clavicle excluded, upperarm..hand + their twists; `leg`: thigh..ball + twists; `hand`: hand + fingers + metacarpals)
  - `identity(ref) -> dict` (the pose's `character` block)
  - `bone_path(ref, leaf) -> str | None`
  - `capture.build_pose(selection=None, regions=None, frame=None) -> (data, note)` — a character pose when exactly one character is selected (several → `(None, "pick one character for a pose")`), else an objects pose of the selected transforms, else `(None, "select a character or objects")`; `regions` (a list of region labels) narrows the members to those regions when given
  - `capture.objects_pose(nodes) -> dict`
  - `capture.region_members(bones, members, regions) -> list[str]` (pure)
  - `capture.thumbnail(path, size=320) -> (ok, note)`

**Rules:**
- `character_of(path)`: `p = weaponspace.hand_for(path) or armor.bone_for(path) or path`; a rig node (`maya_rigs.rig_of`) → `CharacterRef("rig", rig.skeleton_root, rig, label, key, model, rig.namespace)` where the catalog row comes from the rig's character group marker (`cmds.getAttr(rig.character + ".skeldarCharacterGroup")` → `catalog.character_by_label`), else the namespace with trailing digits stripped → `character_by_key`; a joint → its topmost joint (`skeletonimport._top_joint`); a mesh → `_skin_root`; another transform → the bare skeleton root under it, else its character group's root (`maya_rigs.group_root(maya_rigs.group_of(p))`); a skeleton's row from `deletion.recorded(root)[1]` (the label) else the group marker. A rig with no game skeleton is not a character for poses.
- Bones are keyed by LEAF (namespace stripped). A duplicate leaf inside one skeleton keeps the first and is noted.
- `rest` = `maya_retargetmode.rest_world(path)`; `world` = `cmds.getAttr(path + ".worldMatrix[0]")` at the current frame.
- `capture.build_pose` for a rig source fills `drive` for the bones `rigsolve.drive_matrices(rig)` returns.
- `capture.objects_pose`: per node every keyable, scalar, unlocked attribute (`cmds.listAttr(node, keyable=True, scalar=True, unlocked=True)`), `name` = leaf without namespace, `path` long.
- `capture.thumbnail`: panel = `maya_vpstudio.active_panel()`; port = `omui.M3dView.getM3dViewFromModelPanel(panel)` `portWidth/portHeight`; query then switch off on that panel `nurbsCurves, joints, locators, dimensions, grid, manipulators, headsUpDisplay, selectionHiliteDisplay, handles, ikHandles, deformers, motionTrails, cameras, lights, follicles, nParticles` (each queried, put back in `finally`); `cmds.refresh(force=True)`; blast `cmds.playblast(frame=[cmds.currentTime(query=True)], format="image", compression="jpg", quality=95, completeFilename=raw, widthHeight=(w, h), percent=100, viewer=False, showOrnaments=False, offScreen=True, forceOverwrite=True, clearCache=True, editorPanelName=panel)`; repeat until two consecutive blasts are byte-identical (at most 5, `maya.utils.processIdleEvents()` + `QApplication.processEvents()` between — trap 120); centre-crop the square with `QImage.copy`, scale to `size` with `Qt.SmoothTransformation`, save JPG quality 92. No panel / batch mode → `(False, "no viewport for a thumbnail")`.

- [ ] **Step 1:** tests for the pure parts: `region_members`, `whole_body` (helpers out), `limb_bones`, and `members_from_selection` with a fake: given selected leaves `["Manny_Rig1:FKWrist_L"]` → `["hand_l"]`; `["Manny_Rig1:IKArm_L"]` → the left arm's bones; `["Manny_Rig1:Fingers_L"]` → the left hand's fingers; `["Manny_Rig1:Main"]` → whole body; a game bone `"...|hand_l"` → `["hand_l"]`. Make `members_from_selection` take the selection as leaf names + kinds so it is testable without a scene: signature `members_from_selection(ref, selection, bones)` where `selection` is a list of `(leaf, node_type)` tuples — the scene wrapper `members_of(ref, nodes)` builds that list.
- [ ] **Step 2–4:** implement; tests OK.
- [ ] **Step 5: Commit** — `feat(poselib): reading the scene - which character, its skeleton, the pose and the thumbnail`

---

### Task 6: Bone targets → channels (`skelsolve.py`, `rigsolve.py`) + `verify_poselib_solve.py`

This is the riskiest task. **Probe before writing**: in mayapy standalone add a `Manny_Rig`, a `Creep_Rig`, an `Orc_D_Rig` (`maya_scenesetup.character.add_character(catalog.character_by_key(k))`; `loadPlugin matrixNodes/quatNodes` first) and print, per FK control, its DAG ancestors up to the first FKX joint or constraint-driven group, and which node each `FKParentConstraintTo*` group is constrained to; print the neck in-between network (`FKNeck_M`, `NeckInbetween*`, `NeckPart1`), `AlignIKToWrist_*`, `AlignIKToAnkle_*`, `IKToes_*` vs `IKXToes_*`. Record what you measured in the module docstring.

**Files:**
- Create: `SkeldarAnim/maya_poselib/skelsolve.py`, `SkeldarAnim/maya_poselib/rigsolve.py`
- Create: `docs/superpowers/plans/verify_poselib_solve.py`
- Test: `tests/test_poselib_solve.py` (pure helpers)

**Interfaces:**
- Consumes: `posemath`, `keys.writable`, `maya_scenesetup.fkik.local_channels/pole_side/pole_point/blended/angle`, `maya_asretarget.ROWS/SIDES/has_neck_inbetween/rotation_mode`, `maya_rigs.node`.
- Produces:
  - `Solution = namedtuple("Solution", "values notes skipped")` (in `skelsolve`, re-exported by `rigsolve`)
  - `skelsolve.solve(ref, bones, wanted, members) -> Solution` — `bones` = `scene.skeleton(ref)[0]`, `wanted` = `posemath.targets(...)` (every target bone's world), `members` = the TARGET leaves to write
  - `skelsolve.joint_channels(local, joint_orient, rotate_axis, rotate_order, current) -> (rx, ry, rz)` (pure: `R = RA⁻¹ · rot(local) · JO⁻¹`, euler in `rotate_order` nearest `current`)
  - `rigsolve.bases(rig) -> {game leaf: Base}` with `Base = namedtuple("Base", "leaf base side fk fkx ikx deform limb")` (node names in the rig's namespace, only existing ones; `limb` = `"arm"`/`"leg"`/None)
  - `rigsolve.drive_matrices(rig) -> {game leaf: [16]}` — for the six unrolled bones (upperarm, lowerarm, thigh, calf per side; neck_01, neck_02): `G · D⁻¹ · S` with `S = fkik.blended(FKX, IKX, blend/10)` for limbs and `S = FKX` for the neck; the other bones are absent (their `world` is their drive)
  - `rigsolve.solve(rig, wanted, members) -> Solution` — FINAL channel values for the controls; the scene is left exactly as found (every temporary setAttr restored)
  - `rigsolve.controls_for(rig, members) -> list[str]` (what Apply would key: for Select objects)
  - `rigsolve.measure(rig, wanted, members) -> (worst_deg, worst_cm, worst_leaf)` (after keys: directions for the four unrolled limb bones, full rotation for the rest, the pelvis position)

**`rigsolve.solve` algorithm** (per the spec's "Onto a rig"):

1. `bases(rig)` → the member bases (`wanted` leaves in `members` that have a `Base`; others noted: twist bones and helpers are driven on a rig).
2. Sample once (one evaluation at the current frame, `cmds.currentTime(cmds.currentTime(query=True))` before): `G`, `D` (the AS deformation joint = the target of the game bone's orient constraint), `FKX`, `IKX`, `C` (FK control), blends.
3. `O_g = rigid(G) · rigid(D)⁻¹`; drive-chain target `S*[b] = O_g⁻¹ · wanted[g]` (rotation; position from the FKX chain, step 4).
4. **FK tree, level by level** (robust to every non-rigid parent — finger SDK groups, `FKHead_M.Global`, follow blends): sort the member FK controls by DAG depth; for each depth level: for each control `c`, `L = rigid(FKX_c) · rigid(C)⁻¹` (sampled once, constant), target world rotation `rot(L⁻¹ · S*[b])`, the parent's world READ NOW (`cmds.getAttr(parent + ".worldMatrix[0]")` after the previous level's setAttrs), local = `world · parent⁻¹`, rotate channels via `fkik.local_channels(local, rotate_order, current_rotate)`; `cmds.setAttr` the rotation (temporarily; the original values recorded). Translation channels are not written. **Measure first** (in the probe) that a `getAttr` after `setAttr` is fresh in mayapy AND in a GUI Maya; if not, run the solve with `cmds.evaluationManager(mode="off")` inside a try/finally that restores the mode.
5. **Neck**: after its level, compare the deformation joints `Neck_M` / `NeckPart1_M` with their targets; while the angle is > 0.01° (at most 6 rounds), correct the FK control by the measured gain: `delta_wanted = target · current⁻¹` (rotation), `angle_now`, apply `delta^(1/gain)` where `gain` = achieved angle / commanded angle from the previous round (quaternion power via `MQuaternion.log/exp` or axis-angle scaling). Never write bias/share.
6. **RootX_M** when `pelvis` is a member: `M = rigid(RootX_M) · rigid(G_pelvis)⁻¹` (sampled before anything moved), target world `M · wanted[pelvis]` (rotation AND position), local = world · parent⁻¹ (parent read now), translate + rotate channels; set it FIRST (before level 1), since every chain hangs under it.
7. **IK ends**, per limb with a member and an IK control: after the FK levels, read `AlignIKTo<Wrist|Ankle>_<side>` world (it rides the FKX end, which now stands on the target) → IK control world; local against its parent (read), translate + rotate. **IKToes**: the relation `rigid(IKToes) · rigid(IKXToes)⁻¹` sampled before; target `that · FKXToes_now`; rotate only. **Poles**: `side = fkik.pole_side(pole_pos, S, E, W, rot(E))` from the CURRENT IK chain sampled before anything moved; after the IK end is set, `fkik.pole_point(FKX_s, FKX_e, FKX_w, rot(FKX_e), side)` with the FKX chain read now; local = point against the pole's parent read now; translate only. Key `IKArm.swivel` 0, `IKLeg.roll`/`rock` 0 when the limb has a member. A limb whose `stretchy`, `antiPop`, pole `follow*` or `lock` is off its default (`fkik.off_default`) keeps its IK half unposed, noted.
8. The spine in IK (`FKIKSpine_M.FKIKBlend` ≠ 0): noted («the spine shows IK - its FK took the pose»).
9. Read every channel set, record them as `values`, **restore every temporary setAttr** (original values, in reverse order), return. A plug that is not writable (`keys.writable`) is skipped and named.
10. The IK hinge: when a limb is in IK (blend > 0) and the FK forearm/calf twist about its own bone differs from what the IK elbow can hold, note it with the angle (measure it after the IK set as `fkik.measure` does for its switch).

**`verify_poselib_solve.py`** (mayapy standalone, `MAYA_APP_DIR` scratch; the runner rules of CLAUDE.md — no `raise SystemExit`, every gate printed `PASS/FAIL name value`, a final `SUMMARY x/y`):

- phase `save`: add `Manny_Rig`, `Creep_Rig`, `Orc_D_Rig`, `Manny` (skeleton), `Creep` (skeleton), `UE4_Mannequin`; pose each rig by setting a deterministic set of FK control rotations (arms, legs, spine, neck, head, fingers) and RootX_M translate/rotate; capture a full pose and a left-hand pose from each (`capture.build_pose`); gates: bones count = the skeleton's, every member has `rest`/`world`, rig sources carry `drive` on the six bones, `canonical` names for UE skeletons equal the leaf.
- phase `rig-twin`: for each rig, reset its controls to other values (setAttr), `rigsolve.solve` the captured pose onto the SAME rig (wanted = `posemath.targets(source, target, …, use_drive=True)`), key the values (`keys.write` with no layer), evaluate, gates: every member game bone on the captured world to 0.01° (directions for the four unrolled limb bones) and 0.01 cm, the twist bones on the captured ones to 0.05°, `Main` unmoved, the control values within 0.001° of the ones that made the pose (FK controls).
- phase `ik`: Creep and Orc D legs are in IK (shipped); Manny with `FKIKArm_L` blend 10 set before solving; gates: the IK limb's bones on the pose to 0.05 cm / 0.05° (hinge note allowed), then switch the blend to 0 (setAttr) and the FK chain shows the same pose to 0.01°.
- phase `neck`: Manny at `FKNeck_M.bias` 0 and at 10: a neck pose from the Manny SKELETON (a bare skeleton posed by joint rotations) onto Manny_Rig: neck_01, neck_02, head to 0.05°, bias and share unchanged.
- phase `cross`: Manny_Rig pose → Creep_Rig, Orc_D_Rig, Manny skeleton, Creep skeleton, UE4 Mannequin: every paired member bone POINTS where the source's does to 0.1° (directions), lengths unchanged (0.0001 cm), the root/Main unmoved, the pelvis at the scaled offset.
- phase `skeleton`: a Manny skeleton pose → another Manny skeleton: exact (0.001° / 0.001 cm), twist bones included.
- phase `partial`: the left-hand pose onto Creep_Rig: only the left hand's finger and wrist controls change (every other control's value equal to 1e-6), the fingers on the pose relative to the hand.

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_poselib_solve.py` with `$env:MAYA_APP_DIR` set to a scratch folder; expected `SUMMARY n/n`.

- [ ] **Step 1:** probe (above), write the measured facts into `rigsolve`'s docstring.
- [ ] **Step 2:** unit tests for the pure helpers: `skelsolve.joint_channels` (a joint with jointOrient (10,20,30), rotateAxis (5,0,0), order zyx: a local matrix built from known channels decomposes back to them); `rigsolve` pure helpers you factor out (e.g. `level_order(depths)`, `gain_step(...)`).
- [ ] **Step 3:** implement `skelsolve.py` then `rigsolve.py`.
- [ ] **Step 4:** write `verify_poselib_solve.py`, run it, iterate until every gate passes. Unit tests green.
- [ ] **Step 5: Commit** — `feat(poselib): bone targets onto skeletons and AS rigs - an analytic, level-by-level solve`

---

### Task 7: Apply, blend, drops, select (`apply.py`) + `verify_poselib_apply.py`

**Files:**
- Create: `SkeldarAnim/maya_poselib/apply.py`, `docs/superpowers/plans/verify_poselib_apply.py`
- Test: `tests/test_poselib_apply.py` (pure parts + a fake scene)

**Interfaces:**
- Consumes: `scene`, `capture`, `posemath`, `rigsolve`, `skelsolve`, `keys`, `maya_scenesetup.character.add_character/new_root`, `maya_uebridge.rigimport.fresh_rig`, `maya_scenesetup.catalog`, `maya_overrig.builder.character_roots` (lazy), `maya_uebridge.formats.build` (a native source's rebuild).
- Produces:
  - `Plan = namedtuple("Plan", "ref values current notes skipped")` (per target character)
  - `plan_for(data, ref, mirror=False) -> Plan` — the full computation without writing (the scene is left as found)
  - `apply(data, selection=None, mirror=False, alpha=1.0) -> (ok, text)` — targets from the selection (nothing selected → the only character, else refusal naming them); one undo chunk; keys on the active layer at the current frame; `alpha` < 1 blends the values (below); an objects pose goes through `apply_objects`
  - `apply_onto(data, root, mirror=False) -> (ok, text)` (a dropped character, by root long path)
  - `drop_floor(data, point, mirror=False) -> (ok, text)` — the source's catalog row added at `point` (`add_character(entry, at=point)`, the new rig/root found by diff), the user's selection put back, then `apply_onto`; a native source (no key): rebuilt bones-only (`formats.build` from the card's rests, namespace `pose_<name>`), then posed; a pose with no source row and no bones → refused
  - `apply_objects(data, selection=None, alpha=1.0) -> (ok, text)` (by name, namespace-blind; else the stored ones; else by order when counts match)
  - `select_objects(data, selection=None) -> (ok, text)` (rig: `rigsolve.controls_for`; skeleton: member bone paths; objects: their nodes)
  - pure `mix(current, final, alpha, rotations) -> dict` — translations/scalars lerped; for each node's rotate triple (`rotations`: `{node: (plugX, plugY, plugZ, rotate_order)}`) the quaternion slerp of the two eulers, written nearest `current`
  - `Blend` class: `start(data, mirror=False, selection=None) -> refusal` (computes every target's `Plan` once), `set(alpha)` (preview: `keys.preview(mix(...))` + `cmds.refresh(currentView=True)`), `finish() -> text` (keys at the last alpha in one undo chunk), `cancel()` (`keys.preview(current)` — every value back)
  - `summary(results) -> str` — «Fist onto Manny_Rig1: 23 controls keyed on AnimLayer1 at frame 12 - worst 0.003 deg | the FK forearm twist is lost on arm_r (31 deg)»; several targets joined with « | »

**Rules:**
- Per target: `bones, _ = scene.skeleton(ref)`; `source = data["bones"]`; members from `data["members"]` (mirrored by `posemath.mirror` when `mirror`); `pairs = posemath.pairs(source, bones)`; `scale = posemath.scale_between(...)`; `wanted = posemath.targets(source, bones, pairs, members, use_drive=(ref.kind == "rig"), scale=scale)`; target members = the target leaves paired with a source member; rig → `rigsolve.solve(ref.rig, wanted, members_t)`, skeleton → `skelsolve.solve(ref, bones, wanted, members_t)`.
- Unpaired source members are noted («no hand_l on Creep_Rig»).
- The active layer: `keys.active_layer()`; a refusal stops the press before anything changes; an additive quaternion layer refuses rotate channels with `keys.quaternion_note`.
- autoKey off inside the chunk (`cmds.autoKeyframe(query=True, state=True)` restored in `finally`).
- After keys: `cmds.currentTime(t)` re-evaluated, `rigsolve.measure` (rigs) or a direct comparison (skeletons) → the worst number in the summary.
- `drop_floor`: the import flushes undo (trap 115) — the pose after it is its own chunk; Add selects the rig's Main: put the user's selection back.

**`verify_poselib_apply.py`** (mayapy standalone) gates:
- `layers`: an additive layer `PoseL` selected, a Manny_Rig keyed on the base: apply → keys only on `PoseL` (base curves unchanged key for key), the final pose on target to 0.01°; an override layer the same; a locked layer → refused, nothing changed; no layers → keys on the base.
- `root`: the target Manny_Rig moved (Main translate (300, 0, -120), rotate Y 70) → after a full pose Main unchanged, the pose relative to it (bones vs the source's root-relative pose to 0.01°).
- `mirror`: a right-arm pose applied mirrored → the left arm takes the mirror (the left bones' root-space rotations equal `F·…·F` of the right's, 0.05°).
- `blend`: alpha 0.5 → each control's rotation halfway (quaternion angle from current = half the angle to final, 0.01°); `Blend.cancel()` → every value back exactly; `Blend.finish()` → keys.
- `partial`: the hand pose onto a Manny skeleton and onto a Creep_Rig: only the hand's channels change.
- `mixamo`: a synthetic Mixamo skeleton (build it like `verify_skeleton_conventions.py`'s Mixamo fixture: `mixamorig:` names, rest in jointOrient) posed → a pose card → onto Manny_Rig: directions to 0.1°.
- `objects`: two cubes posed → an objects pose → applied to renamed copies in a namespace → their attributes equal.
- `floor`: `drop_floor` of a Creep_Rig card into an empty scene at (150, 0, -60): a Creep_Rig added with Main on the point (0.01 cm), its bones on the pose (0.01°), the selection as before, one Ctrl+Z removes only the pose keys.
- `undo`: an apply then `cmds.undo()` → every channel back to before (exact).

- [ ] Steps: tests for `mix` and `summary` first; implement; verify until green; commit — `feat(poselib): apply - onto the selection, a dropped character, the floor; blend, mirror, select`

---

### Task 8: The window (`window.py`)

**Files:**
- Create: `SkeldarAnim/maya_poselib/window.py`
- Test: `tests/test_poselib_window.py` (offscreen Qt, a fake scene and a temp library)

**Interfaces:**
- Consumes: `store`, `look`, `apply`, `capture`, `maya_hubqt` (`qt`, `ghost_class`, `run_menu`, `pixmap`, `icon`, `on_hub`, `host_widget`, `destroy_roots`, `repolish`), `maya_hubstyle` (`stylesheet`, `TOKENS`, `px`), `maya_scenesetup.droptarget` (`snapshot`, `character_target`, `floor_at`).
- Produces:
  - `CONTROL = "skeldarPoseLibrary"`, `LABEL = "Pose Library"`, `ROOT = "skeldarPoseLibraryRoot"` (the Qt root's objectName)
  - `show_window() -> None` (create or restore the workspaceControl, floating, `initialWidth=1000, initialHeight=640`, `uiScript` = the sys.path bootstrap + `import maya_poselib.window as w; w.build()`; rebuild in place when this module object did not build it — the hub's `_BUILT_HERE` pattern), `build()`, `rebuild()`, `is_open() -> bool`
  - `build_panel()` — the hub card: one note line («Poses of bones - onto any rig or skeleton.») and **Open Pose Library** (primary, icon `books`)
  - `Scene` — the seam every scene call goes through (tests replace it): `scale()`, `library()` (root), `selection_label()`, `save(name, folder, regions, snapshot_path) -> (path, text)`, `snapshot(path) -> (ok, text)`, `apply(path, mirror) -> (ok, text)`, `apply_onto(path, root, mirror)`, `drop_floor(path, point, mirror)`, `select_objects(path)`, `blend_start(path, mirror) -> refusal`, `blend_set(alpha)`, `blend_finish() -> text`, `blend_cancel()`, `snapshot_scene()` (droptarget.snapshot), `target(gx, gy, snap)` (character → floor → none), `over_window(gx, gy)`, `say(text)`
  - `PoseWindow(QWidget)` with the spec's layout; public for tests: `set_library(root)`, `refresh()`, `pick(path)`, `drop_at(gx, gy, path)`, `blend_drag(path, dx)`, `cards_shown() -> list[str]`, `folder() -> str`

**Layout and behaviour** (exactly the spec's "The window"):
- Header (title, path muted, ⋮ menu: Library folder… → `QFileDialog.getExistingDirectory`, writes `skeldarPoseLibraryRoot`; Open in Explorer → `os.startfile`; Refresh).
- Toolbar: `QLineEdit` search (placeholder «search name, folder, character»), `QComboBox` sort (Name, Newest, Character), `QSlider` card size (CELL_MIN..CELL_MAX), **+ Save pose** (`skRole` primary).
- `QSplitter`: `QTreeWidget` folders (root item «Library»; context: New folder, Rename, Delete, Show in Explorer; accepts card drops = move), the grid (a `QScrollArea` holding a painted widget: `look.grid`, `look.visible` culling, pixmaps cached per (path, size); a click picks, a double-click applies, right button → `maya_hubqt.run_menu` with the spec's rows; left drag past `QApplication.startDragDistance()` → the hub ghost (`ghost_class()(pixmap, k*GHOST, k*GHOST, k, anchor=(0.5, 0.5), name="skeldarPoseGhost", backdrop="field")`), captions throttled `THROTTLE_MS`, release → `drop_at`; middle drag → live blend (`alpha = clamp(dx / (200*k))`, release finishes, Esc cancels)), the details panel (thumbnail, `look.details` lines, **Apply** primary, **Mirror** checkbox, **Blend** `QSlider` 0..100 with live preview on drag and key on release, **Select objects**), the status label (`skRole` status, word-wrapped).
- The save panel replaces the details while saving: name `QLineEdit` (default «Pose», `store.unique_name`), folder (the tree's current), the character line (`scene.selection_label()`), region chips (checkable `QPushButton`s `skRole` chip, pre-lit from the selection), the thumbnail with **Snapshot**, **Save** (primary) / **Cancel**.
- `drop_at(gx, gy, path)`: a point inside the window or on the hub → nothing; over a folder item in the tree → move; else `scene.target(gx, gy, snap)` → character → `apply_onto`; floor → `drop_floor` deferred one idle (`maya.utils.executeDeferred`); none → nothing.
- Selection-following (the character line, the Apply enabled state): a `SelectionChanged` scriptJob killed on `destroyed` (the inventory's `watch`/`unwatch` pattern, capturing the job id, not `self`).
- The stylesheet: `maya_hubstyle.stylesheet(scale, arrow=maya_hubqt.icon_file("chevron-down", TOKENS["muted"]))` on the root, plus `#skeldarPoseLibraryRoot { background: <panel> }`.

- [ ] Step 1: tests (offscreen, FakeScene, temp library with three cards written by `store.write`): the window lists the cards; search narrows; sort reorders; a folder pick narrows; `pick` shows details; `drop_at` over a fake character calls `apply_onto`, over floor calls `drop_floor` (deferred function replaced in the test), inside the window does nothing; the context menu rows (`context_actions(path)` returns the labels); the blend drag calls `blend_start`/`blend_set`/`blend_finish`; Esc during the blend calls `blend_cancel`.
- [ ] Steps 2–4: implement until green.
- [ ] Step 5: Commit — `feat(poselib): the window - folders, cards, details, save, drags, blend`

---

### Task 9: Integration (on the LATEST `feature/overrig-picker`)

First `git -C C:/!!!Work/MayaScripts-poselib merge feature/overrig-picker` (resolve conflicts keeping both sides), then:

**Files:**
- Modify: `SkeldarAnim/install.py` (payload rows `"maya_poselib"`, `"poses"`; `copy_payload` keeps local poses; `rebuild_open_poselib(dest)` scheduled like `rebuild_open_hub` when `skeldarPoseLibrary` exists)
- Modify: `SkeldarAnim/maya_hub.py` (a `Section("poses", "Pose Library", "maya_poselib.window", "build_panel", "skeldarHubFramePoses", "animation", "books")` after `com`)
- Modify: `SkeldarAnim/maya_hubicons.py` (Tabler `books` outline icon)
- Modify: `SkeldarAnim/maya_hotkeys.py` (`("window.poses", "Windows", "Pose Library", "Open the Pose Library", partial(_show, "maya_poselib.window", "show_window"))`)
- Modify tests: `tests/test_install.py` (payload, the preserve rule), `tests/test_hub.py` (labels, keys/groups), `tests/test_hotkeys.py` (counts), `tests/test_hubicons.py` if it pins a count

**`copy_payload` preserve rule** (test first):

```python
def keep_local(old, new):
    """Every file under the old `poses` that the new build does not carry, copied in;
    a build's own file wins over a local one of the same relative path."""
```

Test: an installed folder with `poses/Mine.pose/pose.json` and `poses/Shipped.pose/pose.json` (old content); a source build with `poses/Shipped.pose/pose.json` (new content) → after `copy_payload`: `Mine.pose` exists, `Shipped.pose/pose.json` has the new content.

- [ ] Steps: tests → implement → full suite green → commit `feat(poselib): ship it - payload, kept local poses, the hub card, the hotkey row`

---

### Task 10: The window live (`verify_poselib_gui.py`, disposable GUI Maya)

A disposable Maya (`MAYA_APP_DIR` scratch, `MAYA_NO_HOME=1`, the userSetup that opens a free port copied into `<MAYA_APP_DIR>/2027/scripts/` — trap 109; killed after; never the animator's Maya). The plugin from the worktree on `sys.path`. Gates (find every widget again by name before each use — trap 148; measure in the send after a deferred action — trap 191):
- the window opens from the hub card's button; its content fits 600 px wide;
- Save with a Manny_Rig control selected: a card with a thumbnail (a JPG, 320², not blank — pixel variance > threshold);
- the card listed; search narrows; a folder created and the card moved there by `drop_at` over the folder item;
- `drop_at` over the projected `hand_l` of a second Manny_Rig → that rig takes the pose (bones to 0.01°);
- `drop_at` over empty floor → a new rig of the source's row on the point, posed;
- the blend slider at 50 previews (controls halfway), release keys;
- a middle drag on a card blends; Esc cancels (values back);
- pictures: the window (DWM copy, trap 134 — never `QWidget.grab()` of Maya widgets), the viewport after the drops.

Commit the verify and the pictures — `test(poselib): the window live in a disposable Maya`

---

### Task 11: Review, docs, merge, install

- Run the code-review workflow over the branch diff; fix every confirmed finding (with tests).
- CLAUDE.md: a section «The Pose Library (2026-10-02)» in the house style (what, measured, traps found), committed on the branch.
- Merge `feature/pose-library` into `feature/overrig-picker` in the main checkout (ask the peers first with ListAgents/SendMessage; commit only our paths); full suite green there.
- Install into the animator's Maya: ask the peers whether anyone is verifying on 7001; install from a `git archive` snapshot of the merged commit (memory: parallel-sessions-in-repo); point `skeldarPoseLibraryRoot` at `C:/!!!Work/MayaScripts/SkeldarAnim/poses` in their Maya (the animator's choice), and say so.
- Do NOT push (pushing publishes a build) — ask.
