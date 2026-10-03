# Pose Library — animation cards: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Animation cards in the Pose Library: several frames of a character's BONES (or plain objects' curves) saved with an animated preview, applied onto any rig or skeleton frame by frame with Studio Library's paste modes, keyed on the active layer, the character's travel carried from where it stands.

**Architecture:** The pose library's road, per frame. A card `<Name>.anim/` holds a small header (`anim.json`), the per-frame bone data (`frames.json.gz`), a still and a sprite-sheet preview. Saving walks the time and reads every bone's world; applying walks the target frames, transfers each frame through a PREPARED transfer (`posemath.Transfer`, alignment fixed on the first frame), solves it with a reusable solver (`rigsolve.Solver`, eulers seeded by the previous frame) and keys it on the active layer, after the paste mode's cut / shift of the layer curves. New pure modules carry the arithmetic (`animdata`, `look` additions); `animcapture` / `animapply` / `timewalk` touch the scene; the window grows a type filter, a Pose|Animation save switch, an options block and hover playback.

**Tech Stack:** Maya 2027 Python 3 (`maya.cmds`, `maya.api.OpenMaya`, `maya.api.OpenMayaAnim`), PySide6 6.8.3, stdlib `unittest` under mayapy, `gzip`/`json`.

**Spec:** `docs/superpowers/specs/2026-10-03-pose-library-animation-design.md` — read it first; every rule there is a requirement. The pose library's spec (`2026-10-02-pose-library-design.md`) and CLAUDE.md's section «The Pose Library» hold the rules this extends.

## Global Constraints

- Work ONLY in the worktree `C:/!!!Work/MayaScripts-poseanim` (branch `feature/pose-animation`). Never edit, stage or commit in `C:/!!!Work/MayaScripts` (peers commit there; it holds the animator's untracked poses).
- Several agents work in this worktree AT THE SAME TIME on disjoint files. Stage ONLY your task's files by name (`git add <file> ...`), never `git add -A`/`.`; if `git commit` fails on `index.lock`, wait a few seconds and retry. Never `git stash`, `git reset`, `git checkout -- <file>` on files that are not yours.
- Tests: from the worktree root, PowerShell: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_poselib_animdata -v` (one module), or `... -m unittest discover -s tests -t .` (all). Never `2>&1` on mayapy; never system `python` (a hanging Store stub). Run your OWN modules while others work; another agent's half-written file may break an import for a minute — re-run.
- Any mayapy STANDALONE Maya session (`maya.standalone.initialize`) runs with a scratch prefs folder: `$env:MAYA_APP_DIR = "$env:TEMP\skeldar_anim_<task>"` set in the same PowerShell call. Never connect to port 7001 (the animator's Maya).
- Purity (subprocess-pinned): `store.py`, `look.py`, `animdata.py` import the stdlib only (`look` imports no `maya_poselib` sibling either); `posemath.py` the stdlib, `maya.api.OpenMaya` and `maya_skeletonmap` only; `window.py` / `cardgrid.py` import neither Qt nor `maya.cmds` at import time.
- Matrices cross module boundaries as 16-float lists, row-major, Maya's row-vector convention (`world = local · parent`). Inside a module use `om.MMatrix`.
- NEVER called from an apply (each destroys the take): `maya_asretarget.reset_build_pose`, `maya_pmretarget.reset_build_pose`, `maya_rig_retarget.run_retarget`/`bake`, `vendor_bake`, `connect`, `maya_ikmatch.restore`, `skeletonimport.transfer*`, `onto_*`, `rigimport.ready_rig`/`retarget_imported`, `set_exact_neck`, `cliplabel.*`. Never written: `FKNeck_M.bias`, `twistAmountDivideNeckPart1_M.input2`, `FKIK*.FKIKBlend`.
- Resolve nodes by long path or UUID inside the chosen character, never by a bare short name (traps 47, 187); rig nodes through `maya_rigs.node(rig, leaf)`.
- Eulers: the solution nearest a seed (`skelsolve.joint_channels(..., current)`); a frame series seeds each frame with the PREVIOUS frame's solved values (trap 108).
- Keys: `cmds.setKeyframe(plug, time=t, value=v, animLayer=L)` with `v` the FINAL value, keyed at the CURRENT time `t` (the walk stands on it). Always pass `animLayer` when any layer exists; add a plug to a non-base layer first; refuse a locked layer.
- A time walk: `maya.api.OpenMayaAnim.MAnimControl.setCurrentTime` under `cmds.refresh(suspend=True)` (`currentTime -update 0` reads stale, trap 127); the animator's unkeyed tweaks read before (`keys.Tweaks()`) and put back after (`restore(skip=keyed plugs)`), the time put back.
- One undo chunk per apply (`cmds.undoInfo(openChunk=True, chunkName="skeldarAnimApply")` … `closeChunk` in `finally`), autoKey off inside it and restored.
- Files written atomically: `path + ".part"` then `os.replace`.
- Status lines and comments in English; the animator's quotes stay Russian. Comment density like the surrounding plugin code: a docstring per function saying what and why.
- No new shelf button, no `icons/*.png`. Commit after each task with a message file (`git commit -F <file>`), trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

## File structure

| file | responsibility | task |
|---|---|---|
| `SkeldarAnim/maya_poselib/store.py` | both card types on disk: suffixes, header + frames + preview files, `Card` fields, `read_frames`, type filter | 1 |
| `SkeldarAnim/install.py` | `.anim` folders are card units in `keep_local` | 1 |
| `SkeldarAnim/maya_poselib/animdata.py` (new) | pure: the frame codec, `bones_at`, `Options`, `paste_plan`, connect offsets | 2 |
| `SkeldarAnim/maya_poselib/look.py` | pure: fps of a unit, preview frames / sheet geometry / playing cell, badge, details and status text for animations | 3 |
| `SkeldarAnim/maya_poselib/posemath.py` | `Transfer` (prepare once, `frame()` per frame, a root frame override), `targets` on top of it, the root travel | 4 |
| `SkeldarAnim/maya_poselib/rigsolve.py` | `Solver` (structure once, `solve(wanted, seed)` per frame, Main written for travel), `solve` on top | 5 |
| `SkeldarAnim/maya_poselib/skelsolve.py` | `seed=`, `root=` | 5 |
| `SkeldarAnim/maya_poselib/scene.py` | `refresh_world(ref, bones)`: the bones' world/drive re-read, structure kept | 5 |
| `SkeldarAnim/maya_poselib/keys.py` | layer curves: `curve_for`, `cut`, `shift`, `write_keys` (keys with tangents) | 6 |
| `SkeldarAnim/maya_poselib/timewalk.py` (new) | `Walk` (the time walk context), `Progress` (cancellable progress window) | 6 |
| `SkeldarAnim/maya_poselib/animcapture.py` (new) | saving: the character's frames, its key times, objects' curves, the preview sheet | 7 |
| `SkeldarAnim/maya_poselib/animapply.py` (new) | applying: options, paste modes, the per-frame walk, travel, connect, blend, objects, drops, select | 8 |
| `SkeldarAnim/maya_poselib/apply.py` | `drop_floor(..., onto=None)` | 8 |
| `SkeldarAnim/maya_poselib/cardgrid.py` | badge, hover playback from the sheet | 9 |
| `SkeldarAnim/maya_poselib/window.py` | type filter, + Save with Pose/Animation and a range, the options block, details playback, Scene dispatch, rows | 9 |
| `tests/test_poselib_animdata.py`, `tests/test_poselib_timewalk.py`, `tests/test_poselib_animcapture.py`, `tests/test_poselib_animapply.py` (new) + extended `test_poselib_store/look/posemath/solve/scene/keys/cardgrid/window.py`, `tests/test_install.py` | unit tests | each |
| `docs/superpowers/plans/verify_poselib_anim.py` (new) | mayapy standalone, end to end | 10 |
| `docs/superpowers/plans/verify_poselib_anim_gui.py` (new) + its runner/sender | a disposable GUI Maya | 11 |
| `CLAUDE.md` | the section | 12 |

## Shared data shapes (every task uses these names)

```python
# store
CARD_SUFFIX = ".pose"; ANIM_SUFFIX = ".anim"; CARD_SUFFIXES = (".pose", ".anim")
POSE_FILE = "pose.json"; ANIM_FILE = "anim.json"; FRAMES_FILE = "frames.json.gz"
THUMB_FILE = "thumbnail.jpg"; PREVIEW_FILE = "preview.jpg"
FORMAT = "skeldar.pose"; ANIM_FORMAT = "skeldar.anim"; VERSION = 1
Card = namedtuple("Card", "path folder name created author label kind count regions thumbnail "
                          "type frames preview fps start end")
# defaults for the six new fields: type "pose", frames 0, preview "", fps "", start 0.0, end 0.0

# anim.json, kind "character" (the HEADER)
{"format": "skeldar.anim", "version": 1, "kind": "character", "name": "Walk",
 "created": "2026-10-03T12:00:00", "author": "Eugene", "scene": "shot.ma", "fps": "ntsc",
 "start": 0.0, "end": 47.0, "frames": 48,
 "key_times": [0.0, 6.0, 12.0, 47.0],
 "character": {"key": "Manny_Rig", "model": "Manny", "kind": "rig", "label": "Manny [rig]",
               "namespace": "Manny_Rig", "root": "root", "convention": "unreal_ue5",
               "rotation_only": False},
 "bones": {"<leaf>": {"parent": "<leaf>" or None, "canonical": "<UE5>" or None,
                      "rest": [16 floats], "rotateOrder": 0}},          # NO world/drive here
 "members": ["pelvis", "spine_01", ...], "regions": ["Spine", ...],
 "rig_source": True,
 "preview": {"frames": 48, "columns": 7, "size": 320, "step": 1},      # absent: no preview
 "objects": []}
# frames.json.gz (gzip of compact JSON)
{"bones": ["root", "pelvis", ...],               # every bone of the header, skeleton order
 "world": [[q7 of bone 0, q7 of bone 1, ...] per frame],   # q7 = qx qy qz qw tx ty tz
 "drive": {"upperarm_l": [[q7] per frame], ...}}           # rig sources: the 8 unrolled bones
# anim.json, kind "objects"
{..., "kind": "objects", "start": 0.0, "end": 47.0, "frames": 48,
 "objects": [{"name": "pCube1", "path": "|grp|pCube1",
              "attrs": {"translateX": {"keys": [[t, v, "auto", "auto", in_angle, in_weight,
                                                 out_angle, out_weight], ...],
                                       "weighted": False, "breakdown": []},
                        "visibility": {"static": 1.0}}}]}

# animdata
Options = namedtuple("Options", "mode at_current start end connect keys in_place")
# defaults: "replace", True, None, None, False, "every", False
MODES = ("replace", "replace_all", "insert", "merge"); KEY_MODES = ("every", "source")
PastePlan = namedtuple("PastePlan", "frames a b offset ops")
# frames: [(source_frame, index_into_frames_arrays, target_time)], ops: [("cut", a, b)] |
# [("cut_all",)] | [("shift", a, n)] | []
```

---

### Task 1: store + install — animation cards on disk

**Files:**
- Modify: `SkeldarAnim/maya_poselib/store.py`
- Modify: `SkeldarAnim/install.py` (the card-unit helpers only: `CARD_SUFFIX` users, `_is_card`, `free_card`, `_rename_inside`, `keep_local`)
- Test: `tests/test_poselib_store.py`, `tests/test_install.py`

**Interfaces:**
- Produces (store): the constants above; `Card` with the six defaulted fields; `is_anim(path) -> bool`; `card_suffix(path) -> ".pose"|".anim"`; `read(path) -> dict` (the header of either type); `read_frames(path) -> dict` (`{"bones","world","drive"}`, one-entry cache keyed by (path, mtime)); `write(root, folder, name, data, thumbnail=None, replace=False, frames=None, preview=None) -> path` (an `.anim` card when `data["format"] == ANIM_FORMAT`); `set_thumbnail(path, image)`, `set_preview(path, image)`; `unique_name(root, folder, name)` free against BOTH suffixes; `rename`, `move`, `remove`, `folders`, `cards`, `make_folder`, `rename_folder` for both; `filter_cards(cards, query)` hay `name folder label typeword` (`typeword` = "animation" or "pose"); `TYPES = ("all", "pose", "anim")`, `of_type(cards, type_name) -> list`.
- Produces (install): `CARD_SUFFIXES = (".pose", ".anim")`, `_is_card(name)` either suffix; `free_card(folder, name, suffix=" (local)", card_suffix=".pose")`; `_rename_inside(card, name)` rewrites `anim.json` in an `.anim` card, `pose.json` in a `.pose` one; `keep_local` slices the name by the card's own suffix.

- [ ] **Step 1: Write the failing store tests** — add a class `AnimCards` to `tests/test_poselib_store.py`:

```python
class AnimCards(Base):          # Base = the module's existing temp-root fixture class
    def header(self, **extra):
        data = {"format": store.ANIM_FORMAT, "version": 1, "kind": "character", "name": "Walk",
                "created": "2026-10-03T12:00:00", "author": "E", "fps": "ntsc",
                "start": 0.0, "end": 47.0, "frames": 48, "character": {"label": "Manny [rig]"},
                "members": ["pelvis", "hand_l"], "regions": ["Pelvis"], "bones": {},
                "preview": {"frames": 48, "columns": 7, "size": 320, "step": 1}}
        data.update(extra)
        return data

    def frames(self):
        return {"bones": ["root"], "world": [[0, 0, 0, 1, 0, 0, 0]] * 48, "drive": {}}

    def test_an_animation_is_a_dot_anim_card_with_its_files(self):
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames(),
                           thumbnail=self.image(), preview=self.image())
        self.assertTrue(path.endswith("/Walk.anim"))
        self.assertEqual(sorted(os.listdir(path)), sorted(
            [store.ANIM_FILE, store.FRAMES_FILE, store.THUMB_FILE, store.PREVIEW_FILE]))
        card = store.cards(self.root)[0][0]
        self.assertEqual((card.type, card.frames, card.fps, card.start, card.end),
                         ("anim", 48, "ntsc", 0.0, 47.0))
        self.assertTrue(card.preview.endswith("/Walk.anim/preview.jpg"))
        self.assertEqual(card.label, "Manny [rig]")
        self.assertEqual(card.count, 2)

    def test_read_answers_the_header_and_read_frames_the_data(self):
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        self.assertEqual(store.read(path)["frames"], 48)
        self.assertNotIn("world", store.read(path))
        self.assertEqual(len(store.read_frames(path)["world"]), 48)

    def test_a_pose_card_reads_as_a_pose(self):
        path = store.write(self.root, "", "Fist", pose())       # the module's pose() fixture
        card = store.cards(self.root)[0][0]
        self.assertEqual((card.type, card.frames, card.preview), ("pose", 0, ""))

    def test_a_name_is_free_only_when_neither_type_holds_it(self):
        store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        self.assertEqual(store.unique_name(self.root, "", "Walk"), "Walk 2")
        with self.assertRaises(ValueError):
            store.write(self.root, "", "Walk", pose())

    def test_an_objects_animation_counts_its_objects(self):
        path = store.write(self.root, "", "Door", self.header(kind="objects", objects=[
            {"name": "door", "path": "|door", "attrs": {}}], members=[]))
        card = store.cards(self.root)[0][0]
        self.assertEqual((card.type, card.kind, card.label, card.count), ("anim", "objects", "objects", 1))

    def test_rename_move_remove_keep_the_suffix(self):
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        path = store.rename(path, "Run")
        self.assertTrue(path.endswith("/Run.anim"))
        self.assertEqual(store.read(path)["name"], "Run")
        store.make_folder(self.root, "", "Loco")
        path = store.move(path, self.root, "Loco")
        self.assertTrue(path.endswith("/Loco/Run.anim"))
        gone = store.remove(path, self.trash)
        self.assertTrue(gone.endswith("_Run.anim"))

    def test_a_replace_keeps_the_files_it_is_not_given(self):
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames(),
                           thumbnail=self.image(), preview=self.image())
        store.write(self.root, "", "Walk", self.header(frames=10), frames=self.frames(), replace=True)
        self.assertTrue(os.path.isfile(path + "/" + store.PREVIEW_FILE))
        self.assertEqual(store.read(path)["frames"], 10)

    def test_a_folder_named_like_a_card_is_refused(self):
        with self.assertRaises(ValueError):
            store.make_folder(self.root, "", "Loco.anim")

    def test_a_broken_animation_header_is_reported(self):
        os.makedirs(self.root + "/Bad.anim")
        with open(self.root + "/Bad.anim/anim.json", "w") as f:
            f.write("{")
        found, broken = store.cards(self.root)
        self.assertEqual(found, [])
        self.assertEqual(len(broken), 1)

    def test_the_type_word_is_searched_and_the_type_filters(self):
        store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        store.write(self.root, "", "Fist", pose())
        cards = store.cards(self.root)[0]
        self.assertEqual([c.name for c in store.filter_cards(cards, "animation")], ["Walk"])
        self.assertEqual([c.name for c in store.of_type(cards, "pose")], ["Fist"])
        self.assertEqual(len(store.of_type(cards, "all")), 2)
```

(`self.image()` writes a small file and returns its path; `self.trash` a temp trash folder — add both to the fixture if absent.) Adjust the two listdir pins (L66, L273) only if they break — they are pose cards and must stay `[pose.json]` / `[pose.json, thumbnail.jpg]`.

- [ ] **Step 2: Run them, see them fail.** `... -m unittest tests.test_poselib_store -v` → AttributeError on `ANIM_FORMAT`.

- [ ] **Step 3: Implement in `store.py`.**
  - Constants as in Shared data shapes; `_is_card(name)` checks `CARD_SUFFIXES` (lower-cased); `card_suffix(path)`; `is_anim(path)`; `_main_file(path)` → `ANIM_FILE` for `.anim` else `POSE_FILE`; `_format_of(path)` → `ANIM_FORMAT` / `FORMAT`.
  - `read(path)`: opens `_main_file(path)`, checks `format == _format_of(path)`.
  - `read_frames(path)`: `gzip.open(path/FRAMES_FILE, "rt", encoding="utf-8")` + `json.load`; a module-level `_FRAMES = {}` holding ONE entry `(path, mtime) -> data`; ValueError when missing or unreadable.
  - `_card`: for both; `type = "anim" if is_anim(path) else "pose"`; for an anim header `frames = int(data.get("frames") or 0)`, `start`, `end` floats, `fps = str(data.get("fps") or "")`, `preview` = `path/PREVIEW_FILE` when it is a file; the label/count rules as today (character → `character.label`, members; any other kind → "objects", objects).
  - `write(...)`: the suffix from `data.get("format") == ANIM_FORMAT`; `frames` written gzip JSON through `.part` + `os.replace` (`separators=(",", ":")`); `preview` through `_copy_atomic`; the thumbnail; the main file LAST. A pose card given `frames`/`preview` raises ValueError. Rollback as today (rmtree only a card that did not exist).
  - `unique_name`: a candidate is taken when `<name>.pose` OR `<name>.anim` exists; `write` refuses a name the OTHER suffix holds too (same message «… already exists in …»).
  - `rename`: rewrites the main file's `name` (either type), keeps the suffix; `move`/`remove`: the suffix from the path (`remove`'s `_2` collision keeps the card's own suffix); `_folder_name` / `_clean_folder` refuse names ending in either suffix.
  - `set_preview(path, image)`: `_copy_atomic(image, path/PREVIEW_FILE)`.
  - `filter_cards`: hay `"%s %s %s %s" % (name, folder, label, "animation" if card.type == "anim" else "pose")`, every term in one field; `of_type(cards, name)`: `all` → all, else `card.type == name`.
  - Update the module docstring: two card types, their files, the write order, the rules unchanged.

- [ ] **Step 4: Run the store tests until they pass** (all of `tests.test_poselib_store`).

- [ ] **Step 5: Install tests** — add to `tests/test_install.py`'s `KeepsLocalPoses` (copy its fixture helpers; write `anim.json` with `{"format":"skeldar.anim","version":1,"kind":"character","name":...}` plus a `frames.json.gz` and `preview.jpg`):
  - `test_a_local_animation_survives_whole` — a colleague's `Walk.anim` (three files) is back at its place after `keep_local`, every file identical;
  - `test_an_animation_with_a_shipped_name_goes_beside_it` — the build ships `Walk.anim`, the colleague's differs → `Walk (local).anim` with `anim.json`'s `name` rewritten to `Walk (local)`;
  - `test_a_pose_and_an_animation_of_one_name_are_two_units` — `Walk.pose` (local) and `Walk.anim` (shipped) both stand after;
  - `test_the_manifest_lists_animation_cards` — `shipped_manifest(poses)["cards"]` has `"Walk.anim"` with its three files.
  Then implement: `CARD_SUFFIXES`, `_is_card`, `free_card(..., card_suffix)`, `_rename_inside` by suffix, `keep_local`'s name slicing by the card's suffix (`name[:-len(suffix)]`). Keep `CARD_SUFFIX = ".pose"` (other code reads it). Run `tests.test_install` and `tests.test_make_build` until green.

- [ ] **Step 6: Commit** — `git add SkeldarAnim/maya_poselib/store.py SkeldarAnim/install.py tests/test_poselib_store.py tests/test_install.py` and commit «feat(poselib): animation cards on disk - .anim folders, header and frames, kept by the install».

---

### Task 2: `animdata` — the pure arithmetic of an animation card

**Files:**
- Create: `SkeldarAnim/maya_poselib/animdata.py`
- Test: `tests/test_poselib_animdata.py`

**Interfaces:**
- Produces: `encode(flat16) -> [qx,qy,qz,qw,tx,ty,tz]` (rounded: q 9 decimals, t 6); `decode(q7) -> [16 floats]`; `bones_at(header, frames, index, mirror=None) -> {leaf: {"parent","canonical","rest","rotateOrder","world"[,"drive"]}}` (a POSE card's bones for frame `index` of the arrays — `mirror` unused here, reserved); `Options` (+ `options_from(mapping) -> Options` validating/clamping: unknown mode → "replace", unknown keys → "every"); `MODES`, `KEY_MODES`, `MODE_LABELS = {"replace": "Replace", "replace_all": "Replace all", "insert": "Insert", "merge": "Merge"}`; `PastePlan`; `paste_plan(start, end, key_times, options, current) -> PastePlan` (raises `ValueError(EMPTY_RANGE)` when the asked range holds no frame); `connect_offsets(before, first, skip=()) -> {plug: before - first}`; `apply_offsets(values, offsets) -> new OrderedDict`; `EMPTY_RANGE = "the range holds no frame of the clip"`.

- [ ] **Step 1: Write the failing tests** (`tests/test_poselib_animdata.py`; stdlib only — rotations built with `math`):

```python
import math, random, subprocess, sys, unittest
from maya_poselib import animdata as ad

def rot_xyz(rx, ry, rz, t=(0, 0, 0)):
    """A row-vector 4x4 (flat) of X then Y then Z rotations (degrees), translated."""
    def rx_m(a):
        c, s = math.cos(a), math.sin(a); return [[1,0,0],[0,c,s],[0,-s,c]]
    def ry_m(a):
        c, s = math.cos(a), math.sin(a); return [[c,0,-s],[0,1,0],[s,0,c]]
    def rz_m(a):
        c, s = math.cos(a), math.sin(a); return [[c,s,0],[-s,c,0],[0,0,1]]
    def mul(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    m = mul(mul(rx_m(math.radians(rx)), ry_m(math.radians(ry))), rz_m(math.radians(rz)))
    out = []
    for row in m:
        out += row + [0.0]
    return out + list(t) + [1.0]

class Codec(unittest.TestCase):
    def test_round_trip_keeps_rotation_and_translation(self):
        random.seed(3)
        for _ in range(200):
            m = rot_xyz(random.uniform(-180, 180), random.uniform(-89, 89),
                        random.uniform(-180, 180), (random.uniform(-500, 500), 3.25, -7.5))
            back = ad.decode(ad.encode(m))
            for a, b in zip(m, back):
                self.assertAlmostEqual(a, b, places=6)
    def test_scale_is_dropped(self):
        m = rot_xyz(10, 20, 30, (1, 2, 3))
        scaled = [v * 2.0 if i < 12 and i % 4 != 3 else v for i, v in enumerate(m)]
        back = ad.decode(ad.encode(scaled))
        for a, b in zip(m, back):
            self.assertAlmostEqual(a, b, places=6)
    def test_the_identity_and_the_half_turns(self):
        for angles in ((0, 0, 0), (180, 0, 0), (0, 180, 0), (0, 0, 180), (90, 90, 0)):
            m = rot_xyz(*angles)
            self.assertTrue(all(abs(a - b) < 1e-6 for a, b in zip(m, ad.decode(ad.encode(m)))))
    def test_seven_numbers_rounded(self):
        q = ad.encode(rot_xyz(10, 0, 0, (1.23456789, 0, 0)))
        self.assertEqual(len(q), 7)
        self.assertEqual(q[4], 1.234568)

class BonesAt(unittest.TestCase):
    def test_a_frame_is_a_pose_cards_bones(self):
        header = {"bones": {"root": {"parent": None, "canonical": "root", "rest": [1.0]*16,
                                     "rotateOrder": 0},
                            "upperarm_l": {"parent": "root", "canonical": "upperarm_l",
                                           "rest": [2.0]*16, "rotateOrder": 3}}}
        frames = {"bones": ["root", "upperarm_l"],
                  "world": [[0,0,0,1, 0,0,0, 0,0,0,1, 5,0,0], [0,0,0,1, 0,1,0, 0,0,0,1, 6,0,0]],
                  "drive": {"upperarm_l": [[0,0,0,1, 7,0,0], [0,0,0,1, 8,0,0]]}}
        bones = ad.bones_at(header, frames, 1)
        self.assertEqual(bones["root"]["world"][13], 1.0)
        self.assertEqual(bones["upperarm_l"]["world"][12], 6.0)
        self.assertEqual(bones["upperarm_l"]["drive"][12], 8.0)
        self.assertEqual(bones["upperarm_l"]["rotateOrder"], 3)
        self.assertNotIn("drive", bones["root"])
        self.assertIsNot(bones["root"], header["bones"]["root"])   # the header is not touched

class Plan(unittest.TestCase):
    def test_replace_at_the_current_frame(self):
        p = ad.paste_plan(0, 47, [], ad.Options(), 100)
        self.assertEqual((p.a, p.b, p.offset), (100, 147, 100))
        self.assertEqual(p.frames[0], (0, 0, 100)); self.assertEqual(p.frames[-1], (47, 47, 147))
        self.assertEqual(p.ops, [("cut", 100, 147)])
    def test_at_its_own_frames(self):
        p = ad.paste_plan(10, 20, [], ad.Options(at_current=False), 100)
        self.assertEqual((p.a, p.b, p.offset), (10, 20, 0))
    def test_a_sub_range(self):
        p = ad.paste_plan(0, 47, [], ad.Options(start=10, end=19), 5)
        self.assertEqual((p.a, p.b, len(p.frames)), (5, 14, 10))
        self.assertEqual(p.frames[0], (10, 10, 5))
    def test_a_range_outside_the_clip_is_refused(self):
        with self.assertRaises(ValueError):
            ad.paste_plan(0, 10, [], ad.Options(start=20, end=30), 0)
    def test_the_modes(self):
        o = lambda m: ad.paste_plan(0, 9, [], ad.Options(mode=m), 50).ops
        self.assertEqual(o("replace_all"), [("cut_all",)])
        self.assertEqual(o("insert"), [("shift", 50, 10)])
        self.assertEqual(o("merge"), [])
    def test_source_keys_take_the_ends_and_the_keys_inside(self):
        p = ad.paste_plan(0, 20, [0.0, 4.4, 12.0, 30.0, -3.0], ad.Options(keys="source", start=2), 0)
        self.assertEqual([f[0] for f in p.frames], [2, 4, 12, 20])
        self.assertEqual(p.frames[0], (2, 2, 0))
    def test_the_current_frame_is_rounded(self):
        self.assertEqual(ad.paste_plan(0, 3, [], ad.Options(), 12.6).a, 13)
    def test_options_from_a_mapping_keeps_only_what_it_knows(self):
        o = ad.options_from({"mode": "bogus", "keys": "source", "connect": 1, "start": "3"})
        self.assertEqual((o.mode, o.keys, o.connect, o.start), ("replace", "source", True, 3.0))

class Connect(unittest.TestCase):
    def test_offsets_and_their_use(self):
        off = ad.connect_offsets({"a.tx": 5.0, "a.rx": 90.0, "M.tx": 1.0},
                                 {"a.tx": 2.0, "a.rx": 80.0, "M.tx": 9.0}, skip=["M.tx"])
        self.assertEqual(off, {"a.tx": 3.0, "a.rx": 10.0})
        out = ad.apply_offsets({"a.tx": 2.5, "M.tx": 4.0}, off)
        self.assertEqual(out, {"a.tx": 5.5, "M.tx": 4.0})

class Purity(unittest.TestCase):
    def test_imports_nothing_but_the_stdlib(self):
        code = ("import sys; import maya_poselib.animdata; "
                "bad=[m for m in sys.modules if m.startswith(('maya.','PySide','shiboken')) "
                "or m=='maya']; print(bad)")
        out = subprocess.check_output([sys.executable, "-c", code], cwd=PLUGIN).decode()
        self.assertEqual(out.strip(), "[]")
```
(`PLUGIN` = the `SkeldarAnim` folder beside `tests` — copy how `test_poselib_store.Purity` finds it.)

- [ ] **Step 2: Run, see them fail** (ImportError).

- [ ] **Step 3: Implement `animdata.py`** (stdlib: `collections`, `math`):

```python
def _rows(flat):
    """The three rotation rows of a row-vector matrix, orthonormalised (scale, shear dropped)."""
    r0, r1 = list(flat[0:3]), list(flat[4:7])
    def norm(v):
        n = math.sqrt(sum(c * c for c in v)) or 1.0
        return [c / n for c in v]
    r0 = norm(r0)
    d = sum(a * b for a, b in zip(r1, r0))
    r1 = norm([a - d * b for a, b in zip(r1, r0)])
    r2 = [r0[1] * r1[2] - r0[2] * r1[1], r0[2] * r1[0] - r0[0] * r1[2], r0[0] * r1[1] - r0[1] * r1[0]]
    return r0, r1, r2

def encode(flat):
    r0, r1, r2 = _rows(flat)
    # M = the column-vector matrix, the transpose of the row-vector rows
    m00, m01, m02 = r0[0], r1[0], r2[0]
    m10, m11, m12 = r0[1], r1[1], r2[1]
    m20, m21, m22 = r0[2], r1[2], r2[2]
    tr = m00 + m11 + m22
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        w, x, y, z = 0.25 * s, (m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        w, x, y, z = (m21 - m12) / s, 0.25 * s, (m01 + m10) / s, (m02 + m20) / s
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        w, x, y, z = (m02 - m20) / s, (m01 + m10) / s, 0.25 * s, (m12 + m21) / s
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
        w, x, y, z = (m10 - m01) / s, (m02 + m20) / s, (m12 + m21) / s, 0.25 * s
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    return [round(x / n, 9), round(y / n, 9), round(z / n, 9), round(w / n, 9),
            round(flat[12], 6), round(flat[13], 6), round(flat[14], 6)]

def decode(q):
    x, y, z, w = q[0], q[1], q[2], q[3]
    m = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    rows = [[m[0][i], m[1][i], m[2][i]] for i in range(3)]          # back to row vectors
    out = []
    for row in rows:
        out += row + [0.0]
    return out + [float(q[4]), float(q[5]), float(q[6]), 1.0]
```

`bones_at`: copy each header bone's static keys into a new dict, `world = decode(frames["world"][index][7*i:7*i+7])` in `frames["bones"]` order, `drive` from `frames["drive"][leaf][index]` when present. A header bone absent from `frames["bones"]` keeps no world (skip it). `paste_plan` as the spec's table (whole frames: `int(round(...))`; `options.start/end` clamp to the clip; `keys == "source"`: `sorted({lo, hi} ∪ {round(k) for k in key_times if lo <= round(k) <= hi})`; index = `s - int(round(start))`). `Options.__new__.__defaults__ = ("replace", True, None, None, False, "every", False)`. Docstrings say what and why.

- [ ] **Step 4: Run until green.**
- [ ] **Step 5: Commit** «feat(poselib): animdata - the frame codec, the paste plan, the options».

---

### Task 3: `look` — playback geometry and the animation texts

**Files:**
- Modify: `SkeldarAnim/maya_poselib/look.py`
- Test: `tests/test_poselib_look.py`

**Interfaces:**
- Produces: `FPS = {"game": 15.0, "film": 24.0, "pal": 25.0, "ntsc": 30.0, "show": 48.0, "palf": 50.0, "ntscf": 60.0}`; `fps_of(unit) -> float` (also `"<n>fps"` strings like `"23.976fps"`, else 30.0); `PREVIEW_MAX = 60`, `PREVIEW_SIZE = 320`; `preview_frames(start, end, most=PREVIEW_MAX) -> (frames list of whole frames, step)` (`step = ceil(count / most)`, frames `start, start+step, …` ≤ end); `sheet_columns(count) -> int` (`ceil(sqrt(count))`, ≥ 1); `sheet_cell(index, columns, size) -> (x, y, size, size)`; `play_cell(elapsed_ms, cells, step, fps) -> int` (`int(elapsed_ms / (1000.0 * step / fps)) % cells`, 0 for cells ≤ 1); `PLAY_MS = 33`; `badge_text(frames) -> "▶ 48"` ("" for frames < 2); `details(card, data)` gains for an animation: line 2 «48 frames (0-47) · 30 fps · 12 keys» (keys from `len(key_times)`, the «· N keys» part only when `key_times` is non-empty) placed BEFORE the bones line; line 4 «scene.ma» (no «frame F»); `anim_status(result_like) -> str` — see below; `drop_caption` unchanged.

`anim_status` input mapping keys: `name, target, count, noun, layer, a, b, frames, mode, worst (deg, cm), worst_frame, notes, alpha, mirror` → «Walk[ mirrored][ at 50 %] onto Manny_Rig1: 73 controls keyed over frames 12-59 (48 frames, replace)[ on AnimLayer1][ - worst 0.003 deg / 0.02 cm at frame 31][ | note…]»; `count == 0` → «…: nothing keyed». Use the module's `_num` (worst 4 places, drop below 0.0005 like `apply._line` does — read `apply._line` for the exact rounding and copy its rules).

- [ ] **Step 1: Failing tests** in `tests/test_poselib_look.py`, class `Animation`:

```python
class Animation(unittest.TestCase):
    def test_fps_of_the_units(self):
        self.assertEqual(look.fps_of("ntsc"), 30.0)
        self.assertEqual(look.fps_of("film"), 24.0)
        self.assertAlmostEqual(look.fps_of("23.976fps"), 23.976)
        self.assertEqual(look.fps_of("bogus"), 30.0)
    def test_preview_frames_and_step(self):
        self.assertEqual(look.preview_frames(0, 47), (list(range(48)), 1))
        frames, step = look.preview_frames(0, 199)
        self.assertEqual(step, 4); self.assertEqual(frames[:3], [0, 4, 8]); self.assertLessEqual(len(frames), 60)
        self.assertEqual(look.preview_frames(5, 5), ([5], 1))
    def test_sheet_geometry(self):
        self.assertEqual(look.sheet_columns(48), 7)
        self.assertEqual(look.sheet_columns(1), 1)
        self.assertEqual(look.sheet_cell(8, 7, 320), (320, 320, 320, 320))
    def test_play_cell_runs_at_the_clips_rate(self):
        self.assertEqual(look.play_cell(0, 48, 1, 30.0), 0)
        self.assertEqual(look.play_cell(1000, 48, 1, 30.0), 30)
        self.assertEqual(look.play_cell(1000, 48, 4, 30.0), 7)
        self.assertEqual(look.play_cell(1700, 48, 1, 30.0), 3)      # 51 % 48
        self.assertEqual(look.play_cell(999, 1, 1, 30.0), 0)
    def test_badge(self):
        self.assertEqual(look.badge_text(48), "\u25b6 48")
        self.assertEqual(look.badge_text(1), "")
    def test_details_of_an_animation(self):
        card = Card(**dict(BASE, type="anim", frames=48, fps="ntsc", start=0.0, end=47.0))
        data = {"kind": "character", "character": {"label": "Manny [rig]"}, "members": ["a", "b"],
                "regions": ["Spine"], "frames": 48, "start": 0.0, "end": 47.0, "fps": "ntsc",
                "key_times": [0, 12, 47], "author": "E", "created": "2026-10-03T12:00:00",
                "scene": "C:/x/shot.ma"}
        lines = look.details(card, data)
        self.assertEqual(lines[0], "Manny [rig]")
        self.assertEqual(lines[1], "48 frames (0-47) \u00b7 30 fps \u00b7 3 keys")
        self.assertEqual(lines[2], "2 bones \u00b7 Spine")
        self.assertIn("shot.ma", lines[-1]); self.assertNotIn("frame ", lines[-1])
    def test_anim_status(self):
        text = look.anim_status({"name": "Walk", "target": "Manny_Rig1", "count": 73,
                                 "noun": "controls", "layer": "AnimLayer1", "a": 12, "b": 59,
                                 "frames": 48, "mode": "replace", "worst": (0.003, 0.0),
                                 "worst_frame": 31, "notes": ["n1"], "alpha": 1.0, "mirror": False})
        self.assertEqual(text, "Walk onto Manny_Rig1: 73 controls keyed over frames 12-59 "
                               "(48 frames, replace) on AnimLayer1 - worst 0.003 deg at frame 31 | n1")
```
(`Card`/`BASE` = the module's own local Card fixture at L20 — extend it with the six new fields and defaults, mirroring `store.Card`.)

- [ ] **Step 2: Run, fail. Step 3: implement. Step 4: green** (all of `tests.test_poselib_look`, including the purity test). **Step 5: Commit** «feat(poselib): look - preview playback geometry and the animation texts».

---

### Task 4: `posemath.Transfer` — prepare once, transfer per frame, the travel

**Files:**
- Modify: `SkeldarAnim/maya_poselib/posemath.py`
- Test: `tests/test_poselib_posemath.py`

**Interfaces:**
- Produces:

```python
class Transfer(object):
    def __init__(self, source, target, pairs, members, use_drive=False, scale=1.0,
                 pelvis="pelvis"):
        """Everything `targets` computes before its loop, once: the alignment (read off `source`
        AS GIVEN - for an animation the FIRST pasted frame's bones), the target root, `rooted`,
        the target pelvis, `drive_bones`, the root offset, the order, each member's paired
        ancestor."""
    def frame(self, source=None, target=None, root_world=None):
        """{target leaf: om.MMatrix} for the source's pose `source` (default: the one given to
        __init__) with the target standing as `target` says (default: the one given) - the loop
        of `targets`; `root_world` (an MMatrix) replaces the target's ROOT FRAME for this frame:
        a rooted target's root bone stands on it (its non-member children carried), a rootless
        target's top joint keeps it as its ground (`_on_ground`)."""
    def place(self, target=None):
        """The target's root frame as it stands (`target`'s world): its root bone's world, or -
        rootless - its ground frame (`_ground`)."""
    def travel(self, source_now, source_first, flip=False):
        """L_t: the source's root-frame motion from `source_first` to `source_now` (bone dicts,
        unmirrored), `L = rigid(R_now) · rigid(R_first)⁻¹`, reflected across the source root's
        sagittal plane when `flip` (`F · L · F`, `F = _reflection(source, rest root turn)`),
        carried into the target's root axes `Q · L · Q⁻¹` (`Q = rotation(root_offset)`), its
        translation scaled by `scale`. The target's root frame at that frame is `L_t · place`."""
```
- `targets(source, target, pairs, members, use_drive=False, scale=1.0, pelvis="pelvis")` becomes `return Transfer(source, target, pairs, members, use_drive, scale, pelvis).frame()` — BIT-IDENTICAL results (the existing tests and every verify number depend on it).
- `root_frame(bones, pose_bones=None) -> (pose frame, rest frame)`: public wrapper of `_root_frames` for a whole bone dict (the root found by `root_of`, rootless by `has_root`).

- [ ] **Step 1: Failing tests** in `tests/test_poselib_posemath.py` (reuse the module's `skeleton()`, `trs()`, `CHAIN`, `rootless()` helpers):
  - `test_targets_equals_a_transfers_frame` — for three existing fixtures (twin, scaled ×1.2 non-twin, rootless source) every matrix of `targets(...)` equals `Transfer(...).frame()` to 1e-12;
  - `test_frame_takes_another_pose_with_the_alignment_of_the_first` — build a non-twin (×1.2, a translated child on the source); `Transfer(first, ...)`; `.frame(second)` equals `targets(second-with-first's-translations...)`: assert the alignment matrices are the first's (`transfer.align` exposed as an attribute) and the second pose's rotations land (a member's world turn against its parent equals the source's relative turn through the fixed alignment);
  - `test_root_world_moves_the_root_and_carries_its_children` — rooted target, a helper `ik_foot_root` child of root that is no member: `frame(root_world=R)` puts `root` on R and the helper at its local · R; the pelvis on `pos(R) + d·rot(R)`;
  - `test_root_world_on_a_rootless_target_is_its_ground` — rootless target: the top joint's x/z equal R's, its heading R's;
  - `test_place` — rooted → the root's world; rootless → `_ground(rest, world)[0]`;
  - `test_travel_on_a_twin_is_the_root_motion` — source frames A (root at origin) and B (root moved (10, 0, 20), turned 30° about Y): `travel(B, A)` equals `rigid(B_root)·rigid(A_root)⁻¹`;
  - `test_travel_is_carried_through_the_root_axes_and_scaled` — target root rest turned -90 X (UE) against a source root at identity, scale 2: travel's rotation is Q·L·Q⁻¹ and its translation `t_L · Q⁻¹ · 2`;
  - `test_travel_mirrored_reflects_the_sideways_step` — source steps +X (sideways, `l` = +X): flipped → -X; a forward step (+Z) stays +Z; a yaw of +30 becomes -30;
  - `test_travel_of_a_rootless_source_is_its_ground_motion` — Hips moving (5,90,0)→(15,95,10) turning 20° about Y: travel translation (10, 0, 10) (the floor), heading 20°.

- [ ] **Step 2: Run, fail.**
- [ ] **Step 3: Implement** by MOVING the setup of `targets` (posemath.py ~L660-708: `members`, `align`, `target_root`, `rooted`, `target_pelvis`, `now`, `drives`, `pose()`, `source_frame` rest part, `root_rest`, `root_offset`, `is_frame`, `frame`, `offset`, `anchor`) into `Transfer.__init__` and the loop into `frame()`, keeping every expression; per call `frame()` computes `now` from `target`, `pose(s)` from `source`, `source_frame` from `source` (its POSE half per frame; the rest half — `source_frame[1]` — once), and `root_world`:

```python
        if root_world is None:
            root_world = self.place(target)
        root_world = om.MMatrix(root_world)
        ...
        if (self.rooted and leaf == self.target_root):
            out[leaf] = om.MMatrix(root_world)
            continue
        if top and leaf != self.target_root:
            out[leaf] = om.MMatrix(now[leaf]); continue
        parent_now = now_root_frame if top else now[parent]   # see below
```
  Careful with `parent_now`: in `targets` a top joint's `parent_now` is `root_world` (the target's root frame AS IT STANDS, i.e. `place`); keep THAT for the local (`now[leaf] · place⁻¹`) and use the given `root_world` as `parent_world`. For a rooted target, the root's children compute `local = now[child] · now[root]⁻¹` (unchanged) and `parent_world = out[root] = root_world` — so they ride the new root. `travel`:

```python
    def travel(self, source_now, source_first, flip=False):
        now = self._source_root_pose(source_now)
        first = self._source_root_pose(source_first)
        motion = rigid(now) * rigid(first).inverse()
        if flip:
            motion = self.flip * motion * self.flip
        q = rotation(self.root_offset)
        carried = q * motion * q.inverse()
        t = position(carried) * self.scale
        return _placed(rotation(carried), t)
```
  where `_source_root_pose(bones)` = `_root_frames(self.source, self.source_root, pose(bones, self.source_root), self.source_rootless)[0]` reading the bone's `world` (never its drive) from the given dict, and `self.flip = _reflection(self.source, rotation(self.source_rest_frame))`. `_placed(turn, vector)` accepts an MVector (check its signature in the module; adapt). Keep `targets`' docstring (now on `Transfer.frame`) and add the per-frame paragraph.

- [ ] **Step 4: Run `tests.test_poselib_posemath` (every old test unchanged) until green.**
- [ ] **Step 5: Commit** «feat(poselib): posemath.Transfer - prepare once, transfer per frame, carry the root's travel».

---

### Task 5: a reusable rig solver, seeds, the root written

**Files:**
- Modify: `SkeldarAnim/maya_poselib/rigsolve.py`, `SkeldarAnim/maya_poselib/skelsolve.py`, `SkeldarAnim/maya_poselib/scene.py`
- Test: `tests/test_poselib_solve.py`, `tests/test_poselib_scene.py`

**Interfaces:**
- Produces (rigsolve):

```python
class Solver(object):
    def __init__(self, rig, members, main=False):
        """The structure `_Job.__init__` computes, once: game bones, bases, the member filter,
        limbs, held bones, children, Main's path (`rig.main`) when `main`."""
    def solve(self, wanted, seed=None):
        """Solution for one frame - exactly `solve(rig, wanted, members)`'s, the structure
        reused. `seed` {spelled plug: value} (a previous Solution.values): the nearest-euler
        seed of every control it names (rotateX/Y/Z all three), else the control's current
        rotate. With `main` and the game root in `wanted`: Main turned and moved FIRST onto
        `O⁻¹ · wanted[root]` (`O = rigid(G_root) · rigid(Main)⁻¹`, sampled each frame) - its
        rotate / translate land in `values`; a Main that is not writable is skipped and noted
        (`MAIN_KEPT`)."""
    def measure(self, wanted):
        """`measure(rig, wanted, members)` with the structure reused."""
    def controls(self):
        """`controls_for(rig, members)` (+ Main when `main`)."""
MAIN_KEPT = "Main kept where it stands (%s) - the travel is not carried"
```
  `solve(rig, wanted, members)` = `Solver(rig, members).solve(wanted)`; `controls_for(rig, members, main=False)`; `measure` unchanged behaviour. `_Job` may stay as the per-frame worker built FROM a Solver (e.g. `_Job(solver, wanted, seed)`) — keep the `object.__new__(rigsolve._Job)` test pattern in `test_poselib_solve.OneUndoStep`/`FreshMode` working, or update those tests to the new construction while keeping what they assert (the log order, one chunk, `_fresh`).
- Produces (skelsolve): `solve(ref, bones, wanted, members, seed=None, root=False)` — `seed` {plug: value} replaces `getAttr` as the nearest-euler `current`; `root=True` and the skeleton HAS a root (`pm.has_root`) and `wanted` holds it: the root joint's rotate (via `joint_channels` with its JO / RA / order) and translate (`position(local)`, `local = wanted[root] · parentMatrix⁻¹`) are written like the pelvis's; a blocked root → `skipped[root]`.
- Produces (scene): `refresh_world(ref, bones) -> dict` — a NEW bones dict, the same keys and static fields, `world` re-read (`getAttr path.worldMatrix[0]`) and on a rig `drive` re-read (`rigsolve.drive_matrices(ref.rig)`), nothing else read (no recognize, no binds): the per-frame target read.

- [ ] **Step 1: Failing tests** (`tests/test_poselib_solve.py`): 
  - `Seed` — `skelsolve.solve` with a fake `cmds` (copy the module's existing fake patterns; `skelsolve.cmds` rebound) where the plug's getAttr says 0 and the seed says 360: the channel comes out near 360 (e.g. a 10° target gives 370), without the seed near 10;
  - `RootWritten` — a fake two-joint skeleton with a root: `root=False` never writes the root; `root=True` writes its rotate + translate to the target; a root whose `translateX` is locked lands in `skipped`;
  - `SolverIsSolve` — with `rigsolve._Job`'s scene steps stubbed as today's tests do, `rigsolve.solve(rig, wanted, members)` and `Solver(rig, members).solve(wanted)` log the same calls (structure built once: two `.solve` calls on one Solver call `bases` ONCE — count it through a stub);
  - `MainFirst` — a Solver with `main=True` whose wanted holds the root: the log shows Main's `_turn`/`_move` before RootX_M's; with `main=False` no Main write;
  - `RefreshWorld` (`tests/test_poselib_scene.py`) — with a fake cmds answering a new worldMatrix: `refresh_world` changes only `world` (and `drive` on a rig through a stubbed `rigsolve.drive_matrices`), keeps `rest`, `canonical`, `path`, and does not mutate the input dict.
- [ ] **Step 2: Run, fail. Step 3: Implement.** Seeds in `_Job._remember`: `spelled = _name(control)` — when `seed` holds `spelled + ".rotateX/Y/Z"` use those as `rest_rotate[control]`. Main: `self.main = maya_rigs.node(rig, "Main")` (or `rig.main`); in `sample()` read `O` when `main`; `run_pass()` calls `_main()` before `_root()`; `_main()`: `aim = O.inverse() * wanted[root]` (wanted keyed by plain leaf; the root's leaf is `self.root`), `if self._turn(main, aim): self._move(main, pm.position(aim))`, else note `MAIN_KEPT % why`. Main's `_remember` too (rotateAxis, order, seed). Note the root leaf is currently DROPPED from members (`if leaf == self.root: continue`) — keep that; Main is driven from `wanted[self.root]`, not from members.
- [ ] **Step 4: Green on `tests.test_poselib_solve tests.test_poselib_scene tests.test_poselib_apply`. Step 5: Commit** «feat(poselib): a reusable rig solver, euler seeds, the root and Main written for the travel».

---

### Task 6: layer curves and the time walk

**Files:**
- Modify: `SkeldarAnim/maya_poselib/keys.py`
- Create: `SkeldarAnim/maya_poselib/timewalk.py`
- Test: `tests/test_poselib_keys.py`, `tests/test_poselib_timewalk.py`
- Measure: a scratch mayapy script in your own temp folder (not committed)

**Interfaces:**
- Produces (keys):

```python
def curve_for(plug, layer):
    """The time curve (animCurveT*) holding `plug`'s keys on `layer` - `animLayer(L, q=True,
    findCurveForPlug=plug)` when layers exist (BaseAnimation included), else the plug's own
    curve (`listConnections(plug, source=True, destination=False, skipConversionNodes=True)`
    filtered to TIME_CURVES) - or None when it has none."""
def cut(plugs, layer, start=None, end=None):
    """Keys removed from each plug's `curve_for` curve: inside [start, end] (inclusive), or every
    key when both are None. A curve emptied by the cut is left in place (its plug keeps its
    last value). Returns the number of keys removed."""
def shift(plugs, layer, at, by):
    """Every key at or after `at` on each plug's curve moved `by` frames later (`keyframe -edit
    -relative -timeChange by -time (at, BIG)`); the keys moved, counted."""
def write_keys(plug, keys_list, layer, weighted=False, tangents=True):
    """Keys with their tangents: each `[t, v, in_type, out_type, in_angle, in_weight,
    out_angle, out_weight]` keyed (`_key`: final value on the layer), then the curve's tangent
    TYPES set per key, and - `tangents` (no layer, or the base without layers) - the angles and
    weights (`weightedTangents` first when `weighted`). (count, notes) as `write`'s."""
```
- Produces (timewalk):

```python
class Walk(object):
    """with Walk(fresh=True) as walk: walk.go(frame) ... - a time walk: the animator's tweaks read
    first (`keys.Tweaks()`), the viewport suspended (`refresh -suspend`), under the solve's
    evaluation when `fresh` (`rigsolve._fresh(tweaks)`), each `go` an
    `MAnimControl.setCurrentTime` (unrecorded, a full evaluation on read); on exit the time put
    back, the viewport resumed, the evaluation put back, and the tweaks restored but
    `walk.keyed` (the plugs a press keyed - extend it). `walk.restore_all()` puts every tweak back
    (a cancelled press)."""
class Progress(object):
    """with Progress("Saving Walk", total) as progress: progress.step(text) -> False once the
    animator pressed Esc. A no-op (always True) in batch mode or without a UI."""
```

- [ ] **Step 1: Measure first** (mayapy standalone, scratch `MAYA_APP_DIR`, a scratch script): a locator keyed tx at 0/10/20 = 0/10/20, two layers (an additive `L1` keyed at 5 = 1, an override `L2`). Print: `animLayer("BaseAnimation", q=True, findCurveForPlug="loc.tx")`, the same for L1/L2 (do they answer a list? names?), `cutKey(curve, time=(5, 15))` on the base curve leaves 0 and 20, `keyframe(curve, edit=True, relative=True, timeChange=7, time=(10, 1e9))` moves 10, 20 → 17, 27, the same on L1's curve; with NO layers `findCurveForPlug` behaviour (error?) → the plain-curve path. Write the answers into the docstrings you implement (measured, with numbers), and into your report.
- [ ] **Step 2: Failing tests** with fake cmds (copy `test_poselib_keys.FakeCmds`/`PlugCmds` patterns): `curve_for` calls `animLayer(L, query=True, findCurveForPlug=plug)` with layers and the connection path without; `cut` calls `cutKey(curve, time=(a, b), clear=True)` (or what the measure showed works) per curve, all keys when no range; `shift` the keyframe edit with `relative=True, timeChange=by, time=(at, BIG)`; a plug with no curve is skipped quietly; `write_keys` keys every key with `animLayer` and sets tangent types with `keyTangent(curve, edit=True, time=(t, t), inTangentType=..., outTangentType=...)`, angles/weights only when `tangents`. `timewalk`: with fake `cmds`/`oma`/`keys`: `Walk` reads Tweaks BEFORE suspending, `go` calls `setCurrentTime`, exit order: time back, resume, (fresh exit), `restore(skip=keyed)`; an exception inside still restores; `Progress` in batch never calls `progressWindow`.
- [ ] **Step 3: Implement. Step 4: Green** (`tests.test_poselib_keys tests.test_poselib_timewalk`). **Step 5: Commit** «feat(poselib): keys on layer curves - cut, shift, keys with tangents; the time walk».

---

### Task 7: `animcapture` — saving an animation

**Files:**
- Create: `SkeldarAnim/maya_poselib/animcapture.py`
- Test: `tests/test_poselib_animcapture.py`

**Interfaces:**
- Consumes: `scene.resolve/characters/skeleton/members_of/regions_of/identity/describe` (as `capture.build_pose` does), `capture.region_members`, `capture.author`, `capture.HIDDEN/BLAST_QUALITY/settle/square/_port`, `rigsolve.drive_matrices`, `keys.Tweaks`, `keys.TIME_CURVES`, `timewalk.Walk/Progress`, `animdata.encode`, `look.preview_frames/sheet_columns/sheet_cell/PREVIEW_SIZE`, `store.ANIM_FORMAT/VERSION`.
- Produces:

```python
def default_range():
    """(start, end) whole frames: the time slider's highlight when it spans frames
    (`overrig.slider_selection` / `timeControl -q -rangeArray`), else the playback range."""
def build_animation(selection=None, regions=None, start=None, end=None, progress=None):
    """(header, frames, note) of the selection over [start, end] (default_range when None): a
    CHARACTER card (one character) or an OBJECTS card (frames None); (None, None, refusal)."""
def key_times(nodes, start, end):
    """Sorted whole frames: every key time inside [start, end] of every time curve feeding a
    keyable channel of `nodes` (directly, or through animBlendNode chains - a layered take),
    the two ends always in."""
def object_curves(nodes, start, end):
    """[{name, path, attrs: {attr: CURVE}}] (the spec's CURVE shapes) of the keyable scalar
    unlocked attributes; a plain time curve copied through a DUPLICATE (`setKeyframe -insert`
    at both ends, keys inside read with their tangents, the duplicate deleted - unrecorded),
    a layered or otherwise fed plug sampled every frame (`getAttr(time=)`), a free one static."""
def preview(sheet_path, start, end, progress=None):
    """(ok, note, info): the active panel blasted over `look.preview_frames(start, end)` and
    painted into a sprite sheet JPG at `sheet_path` (`info` = {"frames","columns","size","step"});
    the HIDDEN flags off and back, the first frame settled (trap 120), tweaks and time put back.
    Batch / no panel / no Qt: (False, why, None)."""
```
  The header: `capture._common`-like fields with `format=store.ANIM_FORMAT`, `name="Anim"`, no `frame`, plus `start, end, frames, key_times, rig_source, bones` (STATIC: parent, canonical, rest, rotateOrder), `members`, `regions`, `character`, `objects: []`. Frames: `{"bones": list(bones) in skeleton order, "world": [...], "drive": {...}}` read in ONE `timewalk.Walk(fresh=False)` over `range(start, end + 1)` — per frame each bone path's `worldMatrix[0]` (`cmds.getAttr`) encoded, and on a rig `rigsolve.drive_matrices(ref.rig)` encoded; `progress.step` per frame, a cancel → `(None, None, "cancelled - nothing saved")`. The static half is read by `scene.skeleton(ref)` at the CURRENT frame before the walk. The members / regions as `capture.character_pose` computes them. Objects: `object_curves(loose, start, end)` + header `kind="objects"`. The note: «Manny_Rig: 48 frames (0-47), 79 of 93 bones - regions».

- [ ] **Step 1: Failing tests** (fakes; the scene functions rebound on the module): `default_range` (a highlight 10-20 wins; a single-frame highlight → playback); `key_times` (two curves 0, 4.4, 30 and 12 with range 0-20 → [0, 4, 12, 20]; a layered plug through an `animBlendNodeAdditiveDL` reaches both its curves); `build_animation` on a fake skeleton of three bones over 0..2 with a fake `Walk` whose `go` changes what `getAttr(worldMatrix)` answers → three frames, each bone's `decode(world)` equal to what the fake answered, `header["frames"] == 3`, no `world` in the header bones, `progress` cancel → refusal; objects (a fake curve with keys [0,0],[10,5] and a static attr) → the CURVE shapes.
- [ ] **Step 2-4: Run, implement, green.** `preview` is not unit-tested beyond its refusals (batch → False); the GUI verify (Task 11) proves it.
- [ ] **Step 5: Commit** «feat(poselib): animcapture - the frames of a character, objects' curves, the preview sheet».

---

### Task 8: `animapply` — applying an animation

**Files:**
- Create: `SkeldarAnim/maya_poselib/animapply.py`
- Modify: `SkeldarAnim/maya_poselib/apply.py` (`drop_floor(data, point, mirror=False, onto=None)` — `onto(root)` called in place of `apply_onto(data, root, mirror)` when given; nothing else)
- Test: `tests/test_poselib_animapply.py`, `tests/test_poselib_apply.py` (the `onto` case)

**Interfaces:**
- Consumes: Tasks 2, 4, 5, 6 and `apply.choose_targets/_targets/target_members/unpaired/unpaired_note/target_label/mix/rotations_of/_noun/shown_notes/_skipped_note/_measure`-like logic, `apply.pair_objects/_find_object/_not_characters/_selected/_add/_rebuild/_reselect/floor_xz`, `apply.Blend`, `look.anim_status`, `store.read_frames` (the WINDOW passes the frames in; `animapply` does not read files).
- Produces:

```python
def apply(header, frames, selection=None, mirror=False, alpha=1.0, options=None, progress=None):
    """(ok, text): the animation onto every character the selection touches (or the only one),
    or - an objects card - onto the selection's objects; the spec's press."""
def apply_onto(header, frames, root, mirror=False, alpha=1.0, options=None, progress=None)
def drop_floor(header, frames, point, mirror=False, options=None, progress=None)
def select_objects(header, selection=None, options=None)
class Blend(object):
    """start(header, frames, mirror=False, options=None, selection=None) -> refusal;
    set(alpha); finish(progress=None) -> text; cancel(); active()"""
UNDO_CHUNK = "skeldarAnimApply"
```

The character press (`_press_refs(header, frames, refs, mirror, alpha, options, progress)`), in this order:
1. `layer, refusal = keys.active_layer()`; refusal → return; `keys.quaternion_note(layer)` → return; `frames` missing/empty for a character card → `NO_FRAMES = "the card has no frames - save it again"`; `plan = animdata.paste_plan(header["start"], header["end"], header.get("key_times"), options, cmds.currentTime(q=True))` (ValueError → its text).
2. Per ref a `_Target`: under ONE `timewalk.Walk(fresh=True)` (opened here and kept for the whole press) go to `plan.a`; `bones = scene.skeleton(ref)[0]`; `first = animdata.bones_at(header, frames, plan.frames[0][1])`; `members = header["members"]`, and when mirror `src0, members = pm.mirror(first, members)` (the MIRRORED members from here on: the Transfer's, the target members', the pelvis test) else `src0 = first`; `pairs = pm.pairs(src0, bones)`; `scale = pm.scale_between(src0, bones, pairs)`; `members_t = apply.target_members(bones, pairs, members)`; `carry = not options.in_place and pelvis-member (the card's members hold `posemath._find(header bones, "pelvis")`) and pm.has_root or rootless ground`; `transfer = pm.Transfer(first_for_alignment, bones, pairs, members, use_drive=(ref.kind == "rig"), scale)` — alignment off the UNMIRRORED first frame, frames then given mirrored; `place = transfer.place(bones)`; the solver: rig → `rigsolve.Solver(ref.rig, members_t, main=carry)`, skeleton → a closure over `skelsolve.solve(ref, bones_now, wanted, members_t, seed, root=carry)`; the DRY solve at `a` (frame 0, root_world = place when carry) → `plugs` = its values' keys; `before = keys.current(plugs)`; `seed = values`.
3. alpha < 1: for each target time `t` (`walk.go(t)`) `partner[t] = keys.current(plugs)`.
4. `with cmds.undoInfo chunk + autoKey off:` the ops on every target's plugs — `keys.cut(plugs, layer, a, b)` / `keys.cut(plugs, layer)` / `keys.shift(plugs, layer, a, n)`.
5. The walk: for `(s, index, t)` in `plan.frames`: `walk.go(t)`; per target: `bones_t = scene.refresh_world(ref, bones)`; `src = bones_at(header, frames, index)`; `src_m = pm.mirror(src, members)[0] if mirror else src`; `root_world = transfer.travel(src, first, flip=mirror) * place if carry else None`; `wanted = transfer.frame(src_m, bones_t, root_world)`; solve with `seed`; `values` = solution values; `seed = values`; connect: `animdata.apply_offsets(values, offsets)` (offsets from `before` and the DRY solve's values, Main/root plugs skipped); alpha: `apply.mix(partner[t], values, alpha, rotations)`; `written = keys.write(values, t, layer)`; `walk.keyed.extend(written.plugs)`; dirty the feeds (`keys.feed_of` → `cmds.dgdirty`); measure (rig: `solver.measure(wanted)`; skeleton: `apply._measure`-like loop) → keep the worst and its frame; aggregate notes (a dict keyed by text, first seen kept) and skipped; `progress.step(...)` False → cancel.
6. Results → `look.anim_status(...)` per target joined with « | »; a frame-rate note when `header["fps"] != cmds.currentUnit(q=True, time=True)`: «the card is ntsc, the scene film - pasted frame for frame»; a muted layer note (`keys.layer_note`).
7. Cancel: close the chunk, `cmds.undo()`, `walk.restore_all()`, return `(False, CANCELLED)` with `CANCELLED = "cancelled - nothing changed"`.

Objects (`_press_objects`): pair as `apply._objects_entry` does (reuse `apply.pair_objects`, `_find_object`, `_not_characters`); per (record, path) and attr with `cmds.attributeQuery(attr, node=path, exists=True)`: the CURVE's keys clipped to the plan's source range (`[lo, hi]` = the options' range; keys outside dropped; when `lo`/`hi` falls between keys, a key inserted there through a temporary curve — `cmds.createNode("animCurveTU")` + `setKeyframe` of the stored keys + `keyTangent` + `setKeyframe -insert` at `lo`/`hi`, read back, deleted, all unrecorded), shifted by `plan.offset`; static → one key at `a`; Connect: `before(a) - value at lo`; Blend: each key's value mixed with `getAttr(plug, time=t)` read BEFORE the ops; the ops on these plugs; `keys.write_keys(plug, keys, layer, weighted, tangents=(layer is None))`. One chunk.

`apply_onto` = the character press on `[scene.character_of(root)]` (objects → `apply.OBJECTS_ONTO`). `drop_floor` = `apply.drop_floor(header, point, mirror, onto=lambda root: apply_onto(header, frames, root, mirror, 1.0, options, progress))`. `select_objects` = `apply.select_objects(header, selection)` then, when the travel would be carried, Main (rig) / the root joint (skeleton) added to the selection (`cmds.select(add=True)`). `Blend`: `start` builds a POSE card from the frame that falls on the current frame (`data = dict(header, bones=bones_at(header, frames, index))`, index = the plan's frame whose target time is nearest the current frame) and starts an `apply.Blend` on it (its preview); `set` forwards; `finish` cancels the inner blend (values back) then runs the full press at the session's alpha (≤ 0 → `apply.BLEND_ZERO`); `cancel` forwards.

- [ ] **Step 1: Failing tests** (`tests/test_poselib_animapply.py`) against fakes — rebind `animapply.cmds`, `keys`, `scene`, `pm`, `rigsolve`, `skelsolve`, `timewalk` (a fake Walk logging `go(t)`), and assert:
  - the log order: layer → quaternion → walk enter → go(a) → dry solve → [partner walk when alpha < 1] → open chunk → ops (`cut(plugs, layer, a, b)` for replace; `cut(plugs, layer)` for replace_all; `shift(plugs, layer, a, n)` for insert; none for merge) → go(t) / solve / write(values, t) per planned frame IN ORDER → close chunk → walk exit;
  - every frame's solve is seeded with the previous frame's values (the first with the dry solve's);
  - `connect=True`: the keyed values are the solved ones + (before − first), Main/root plugs untouched;
  - `in_place=True` or a hand card (no pelvis member): `root_world` None on every frame, the solver built with `main=False`;
  - carry: `root_world` = `travel(src_i, src_0, flip=mirror) * place`;
  - alpha 0.5: `apply.mix(partner[t], values, 0.5, ...)` keyed;
  - a cancel on the third frame: chunk closed then `undo()` called once, `restore_all()`, the text `CANCELLED`;
  - a locked layer refuses before the walk; a quaternion layer refuses a character card; an empty range refuses with `animdata.EMPTY_RANGE`;
  - the status text comes from `look.anim_status` with a, b, frames, mode and the worst frame;
  - objects: keys shifted by the offset, a static attr keyed once at `a`, `write_keys` with `tangents=True` without layers and `False` on a layer;
  - `drop_floor` hands `onto` to `apply.drop_floor`; `select_objects` adds Main when carried.
  In `tests/test_poselib_apply.py`: `drop_floor(..., onto=f)` calls `f(root)` instead of `apply_onto`.
- [ ] **Step 2-4: Run, implement, green** (`tests.test_poselib_animapply tests.test_poselib_apply`).
- [ ] **Step 5: Commit** «feat(poselib): animapply - an animation onto any rig or skeleton, frame by frame, with Studio Library's paste modes».

---

### Task 9: the window — save, options, playback

**Files:**
- Modify: `SkeldarAnim/maya_poselib/cardgrid.py`, `SkeldarAnim/maya_poselib/window.py`
- Test: `tests/test_poselib_cardgrid.py`, `tests/test_poselib_window.py`

**Interfaces:**
- Consumes: `store` (Task 1), `look` (Task 3), `animcapture` (Task 7), `animapply` (Task 8), `animdata.Options/options_from/MODES/MODE_LABELS`.
- Produces (window):
  - constants: `TYPE_VAR = "skeldarPoseLibraryType"`, `SAVE_TYPE_VAR = "skeldarPoseLibrarySaveType"`, option vars `PASTE_VAR = "skeldarPoseLibraryPaste"`, `AT_CURRENT_VAR = "skeldarPoseLibraryAtCurrent"`, `CONNECT_VAR = "skeldarPoseLibraryConnect"`, `KEYS_VAR = "skeldarPoseLibraryKeys"`, `IN_PLACE_VAR = "skeldarPoseLibraryInPlace"`; `NOTE = "Poses and animations of bones - onto any rig or skeleton."`; `EMPTY_LIBRARY = "Nothing saved yet - select a character and press Save"`;
  - `shown_cards(cards, folder, query, sort, type_name="all")`;
  - `Scene` additions (and the same names on the tests' `FakeScene`): `anim_range() -> (start, end)`; `save(name, folder, regions, snapshot_path, anim=None)` (`anim = {"start": s, "end": e}` → `animcapture.build_animation` + `animcapture.preview` into a temp sheet + `store.write(..., frames=, preview=)`, under one `timewalk.Progress`); `update(path)` (an animation: its own range again, thumbnail and preview kept); `replace_preview(path) -> text` (an animation: snapshot + preview again); `apply(path, mirror, options=None)`, `apply_onto(path, root, mirror, options=None)`, `drop_floor(path, point, mirror, options=None)`, `blend_start(path, mirror, options=None)` — dispatching on `store.is_anim(path)` to `animapply` with `store.read_frames(path)` (a `timewalk.Progress` around every animation press), else the pose road unchanged; `select_objects(path, options=None)`.
  - `PoseWindow`: toolbar `type_filter` QComboBox (`skeldarPoseType`: All / Poses / Animations, remembered); the save button «Save» (`skeldarPoseSave`); the save panel's segments `skeldarPoseSaveType_pose` / `skeldarPoseSaveType_anim` (checkable QPushButtons in an exclusive QButtonGroup, role segment — see how the hub styles segments), `save_start`/`save_end` QSpinBoxes (`skeldarPoseSaveStart`/`End`), a `save_frames` note (`skeldarPoseSaveFrames`: «48 frames · 48 preview cells»), shown only in Animation; the details' options block `anim_options` (`skeldarPoseAnimOptions`, hidden for a pose card) holding: paste segments `skeldarPosePaste_<mode>`, `at_current` QCheckBox (`skeldarPoseAtCurrent`), `range_start`/`range_end` QSpinBoxes (`skeldarPoseRangeStart`/`End`, the card's start..end, reset on every pick), `connect` (`skeldarPoseConnect`), keys segments `skeldarPoseKeys_every|source`, `in_place` (`skeldarPoseInPlace`); `options() -> dict` read from them (the remembered ones written back on change); every press passes `options=self.options()` when the picked card is an animation.
  - details playback: a 33 ms `QTimer` (`play_timer`) running while the picked card is an animation with a preview and the window is visible, setting the thumb label's pixmap to the cell `look.play_cell(elapsed, ...)` of the canvas's sheet (`canvas.sheet(card)`), scaled to `thumb_side()`; stopped on unpick / hide / pick of a pose.
  - context rows of an animation card: «Replace thumbnail and preview» in place of «Replace thumbnail» (calls `scene.replace_preview`); every other row as a pose card's.
- Produces (cardgrid): `canvas.sheet(card) -> QPixmap or None` (the decoded `preview.jpg`, an LRU of 6 by path+mtime, `forget(path)` drops it); `_paint_card` draws `look.badge_text(card.frames)` in a small pill at the square's bottom-right for `card.type == "anim"`; the HOVERED animation card (index `_hover`) with a preview draws `look.sheet_cell(look.play_cell(now - started, cells, step, fps), columns, size)` of its sheet into the square (`QPainter.drawPixmap(target, sheet, source)`, smooth) instead of its still — `started` set when the hover lands on it; a `play_timer` (`look.PLAY_MS`) runs while the hovered card is an animation with a preview and repaints only its `_reach`; it stops on leave / drag / a non-animation hover. The sheet's grid comes from the card's header `preview` dict — give `Card` access by reading it once per path through `store.read` (cache with the sheet).

- [ ] **Step 1: Failing tests.** `test_poselib_window.py`: extend `FakeScene` with the new methods/params (recording calls); tests: the type filter shows only animations / poses and is remembered; «Save» opens the panel with Pose lit; lighting Animation shows the range spin boxes filled from `scene.anim_range()` and Save calls `scene.save(..., anim={"start": 10, "end": 20})`; picking an animation shows the options block and fills the range from the card; Apply passes `options` with every field (mode from the lit segment, the checkboxes, the range); options are remembered across a new window (`scene.option`); a pose card hides the block and Apply passes `options=None`; the right-button rows of an animation card (exact list with «Replace thumbnail and preview»); the details timer runs for an animation with a preview and stops on unpick; drops pass options. `test_poselib_cardgrid.py`: an animation card paints its badge (render to a QImage, the badge region not the plain card colour); the hovered animation card's painted square changes between two `_now` values 100 ms apart (two cells of a two-colour test sheet) while a pose card's does not; `play_timer` active only while such a card is hovered; `forget(path)` drops the sheet. Update the pinned rows and NOTE tests.
- [ ] **Step 2-4: Run, implement, green** (`tests.test_poselib_cardgrid tests.test_poselib_window tests.test_poselib_look`), then the WHOLE suite.
- [ ] **Step 5: Commit** «feat(poselib): the window - save an animation, paste options, previews playing on hover».

---

### Task 10: `verify_poselib_anim.py` — mayapy standalone, end to end

**Files:** Create `docs/superpowers/plans/verify_poselib_anim.py` (copy the harness of `verify_poselib_apply.py`: standalone init, plugin beside the script / `POSELIB_PLUGIN`, `PHASES`, PASS/FAIL lines, SUMMARY; `matrixNodes`, `quatNodes`, `fbxmaya` loaded; ntsc).

Gates (each with a computed expectation and, where it can fail silently, a control):
1. `capture` — Manny_Rig A keyed over 0..23 (FK pose values per frame from `verify_poselib_solve.pose_values`-like seeds + Main travelling (0,0,0)→(60,0,120) turning 30°); `animcapture.build_animation` → 24 frames, `decode(world)` of every bone at frames 0/11/23 equals the scene's at those frames to 1e-5; key_times = the keyed frames; a skeleton (Manny UE5) card too.
2. `twin` — Manny_Rig B at (200, 0, -100) facing 90°: apply at frame 50: every member bone of B at 50+i equals A's at i RELATIVE TO each one's root frame (`rel_rows`) to 0.01 deg / 0.01 cm; B's root at 50+i = A's travel carried onto B's place (0.01 cm); `in_place`: B's Main keys untouched; a hand card: Main and the arm untouched.
3. `modes` — B carrying its own take (keys at 40, 60, 80, 100 on every control): Replace at 60 (24 frames): keys outside [60, 83] identical (times and values), inside only the card's; Replace all: no old key on any written plug; Insert: old keys at 60/80/100 now at 84/104/124 with their values; Merge: an old key at 70.5 still there; each on the base and on an additive layer (curve_state per layer).
4. `options` — at_current off: keys at 0..23; a sub-range 5..9 at 50: keys 50..54 = A's 5..9; connect: the first keyed value of a control equals its value before the press; source keys: keys only at the mapped key times.
5. `cross` — onto Creep_Rig, Orc_D_Rig, the Manny skeleton, the Creep skeleton: every mapped bone points as the source's at every frame within 0.1 deg (`pointing`), the travel scaled by `scale_between`.
6. `mirror` — onto a twin: each left bone at frame i = the reflected right of A at i (0.01 deg); the travel's sideways step reflected.
7. `blend` — alpha 0.5: a control's rotation at each frame is the slerp half of before and the card's (0.01 deg).
8. `objects` — a locator with tx keys (spline + a weighted out-tangent) and a static visibility: saved, applied at 30 onto another locator: keys at the shifted times with the same values, tangent types and the weighted angle; Replace/Insert on objects; connect.
9. `undo` — after a Replace press one `cmds.undo()` restores every curve key for key; a tweak on another character survives the press (`keys.Tweaks` style check).
10. `floor` — new scene: `drop_floor` at (150, 0, 80): a Manny_Rig added, Main at frame `a` on the point, its travel from there.
11. `mixamo` — the `skeleton_conventions` Mixamo fixture animated (Hips travelling) applied onto Manny_Rig: Main travels the Hips' floor travel scaled.
12. `speed` — the seconds per frame on a rig and a skeleton (printed, gated loosely: < 1.0 s/frame on the rig in standalone).

- [ ] Run it (`$env:MAYA_APP_DIR` scratch), fix the code it finds wrong (each fix with a unit test where it can have one), until every gate passes. Commit the verify and every fix separately.

### Task 11: `verify_poselib_anim_gui.py` — a disposable GUI Maya

**Files:** Create `docs/superpowers/plans/verify_poselib_anim_gui.py` + `_run.py` + `_send.py` (copy `verify_poselib_gui*.py`; port 7051; scratch `MAYA_APP_DIR`; `MAYA_NO_HOME=1`; userSetup in `<MAYA_APP_DIR>/2027/scripts/`; refuse port 7001; killed after).

Gates: the window opened from the hub card; a Manny_Rig keyed 0..23 with travel; + Save → Animation → the range 0..23 → Save writes an `.anim` card whose `preview.jpg` is a 5×5 sheet of 320 px cells, cells DIFFER (the character moves), not blank; the grid shows the badge; a hover (sent Qt events) makes the canvas paint two different cells 200 ms apart and the timer stops after leaving; the details picture changes over time; the options block reads back what was clicked; Apply onto a second rig with Insert keys the shifted range; a drag onto the floor adds a rig and plays; pictures (DWM capture, never `.grab()`, trap 134): the window with the card hovered, the save panel, the details. Run, fix, commit.

### Task 12: docs and the merge

- [ ] CLAUDE.md: a section «Pose Library — animation cards (2026-10-03)» after the Pose Library's, in its style: the ask, the answers, the card, save, apply (modes, travel, per frame), the window, proof numbers from Tasks 10-11, traps found.
- [ ] Full unit suite green; final multi-lens review (correctness of the maths, the undo/tweaks/time contract, the install unit rules, the UI) with fixes; merge `feature/pose-animation` into `feature/overrig-picker` (in the main checkout, only after checking `git status` there and staging nothing of the animator's / peers').
