# UE Bridge: several animations at once — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the UE Bridge list takes a multiple selection; Rig (button or drop on a rig) takes the first, New rig /
Skeleton (button) and a floor drop lay every picked clip out in a line — about the origin along X, or about
the drop point across the screen — with a 2.5 m step widened by each clip's sideways root travel.

**Architecture:** a pure `lineup` (extents, offsets, slots), a `lineimport` orchestrator (export all, import
all, measure, lay out, retarget or stand each), `rigimport.import_and_retarget` split into reusable pieces,
`window`/`listdrag`/`droptarget` routing and carrying a list.

**Tech Stack:** Maya 2027 `maya.cmds`, PySide6 (offscreen in tests), stdlib `unittest` under mayapy.

Spec: `docs/superpowers/specs/2026-10-01-uebridge-many-animations-design.md`.

## Global Constraints

- One animation behaves exactly as before on every road.
- `lineup.py` imports only the stdlib (a subprocess test).
- `listdrag.py` imports no Qt and no Maya at module level (the existing Boundary test).
- Step `STEP = 250.0` cm; a root leaving its start sideways by more than `WANDER = 1.0` cm is "widened".
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .` with
  `$env:QT_QPA_PLATFORM = 'offscreen'`.
- Stage only this work's files (peers share the branch; `CLAUDE.md` holds a peer's uncommitted hunk).

---

### Task 1: `lineup` — the line, pure

**Files:** Create `SkeldarAnim/maya_uebridge/lineup.py`; Test `tests/test_uebridge_lineup.py`.

**Produces:** `STEP`, `WANDER`, `side_extent(track, axis) -> (lo, hi)`, `offsets(extents, step=STEP) -> [float]`,
`floor_axis(direction) -> (x, 0, z)`, `slots(centre, axis, offsets) -> [(x, y, z)]`,
`widened(names, extents, wander=WANDER) -> [name]`, `sample_frames(start, end, samples) -> [float]`.

- [ ] Tests: a still clip `(0, 0)`; a strafe right `(0, 30)`, left `(-20, 0)`, both, relative to the FIRST
  point; three still clips → `[-250, 0, 250]`; a wanderer between two still ones → gaps `250 + 30` and
  `250 + 20`, first and last equidistant from 0; one clip → `[0]`; none → `[]`; `floor_axis((0, 5, 2))` →
  `(0, 0, 1)`, `floor_axis((0, 1, 0))` → `(1, 0, 0)`, `floor_axis((3, 0, 4))` → `(0.6, 0, 0.8)`; `slots` along
  an axis about a centre keeps the centre's Y; `widened`; `sample_frames(0, 10, 240)` → 11 whole frames,
  `(0, 1000, 240)` → 240 evenly, `(5, None)` → `[5]`; the module imports only the stdlib (subprocess).
- [ ] Run: FAIL (no module). Implement. Run: PASS. Commit `feat(uebridge): lineup - where each of several
  clips stands in a line`.

### Task 2: `rigimport` split into pieces; `stand_skeleton`

**Files:** Modify `SkeldarAnim/maya_uebridge/rigimport.py`; Test `tests/test_uebridge_rigimport.py`.

**Produces:**
- `plan_press(target, rig=None) -> (plan dict | None, refusal str)` — plan keys `rig, mod, add, entry`;
- `ready_rig(plan) -> (rig, mod, notes list, failure str)` — adds `plan["entry"]` or resets the standing rig;
- `import_source(fbx_path, name, clip_fps=None, set_timeline=True) -> (namespace, info, source|None)`;
- `retarget_imported(rig, mod, namespace, info, source, name, place=None) -> (line, failure)`;
- `root_at(source, frame) -> (x, y, z)` (`getAttr(worldMatrix[0], time=)`; current position when frame None);
- `stand_skeleton(namespace, source, point, start) -> (dx, dz)` — the root's wrapper moved onto the point;
- `NO_JOINT` format string. `import_and_retarget` composes them, behaviour unchanged.

- [ ] Tests (a fake `cmds` and fakes for `maya_rig_retarget`/`maya_rigs`/`character` in `sys.modules`):
  `import_and_retarget` onto a standing rig calls reset → import → wrap → connect → place → bake → remove the
  namespace in that order and returns the same line as before; `plan_press("new_rig")` refuses a missing rig
  file before anything; `stand_skeleton` groups the root under `<ns>:skeldarDropShift` and moves it by
  `shift_for(point, root_at_start)` horizontally.
- [ ] FAIL → implement → PASS → commit `refactor(uebridge): the import press in pieces a batch can reuse`.

### Task 3: `lineimport` — several animations, one press

**Files:** Create `SkeldarAnim/maya_uebridge/lineimport.py`; Test `tests/test_uebridge_lineimport.py`.

**Consumes:** Task 1, Task 2. **Produces:** `run(record_list, export, target, centre=(0, 0, 0),
axis=(1, 0, 0), set_timeline=True, step=lineup.STEP) -> str`, `summary(...)` (pure), `first_only(names)`
(pure), `TARGETS = ("new_rig", "skeleton")`.

- [ ] Tests with `rigimport` pieces and `cmds` faked: every clip exported before the first import; a clip the
  editor fails is named and left out; three clips onto new rigs stand on `lineup.slots` in list order; the
  timeline is set once to the union before the first retarget; skeleton mode stands each; a cancel during the
  retargets keeps the done ones and removes the namespaces imported for the rest; the wording of `summary`
  and `first_only`.
- [ ] FAIL → implement → PASS → commit `feat(uebridge): several animations at once, laid out in a line`.

### Task 4: the window and the drop target

**Files:** Modify `SkeldarAnim/maya_uebridge/window.py`, `SkeldarAnim/maya_scenesetup/droptarget.py`; Tests
`tests/test_uebridge_window.py`, `tests/test_scenesetup_droptarget.py`.

- [ ] `allowMultiSelection=True`; `_selected_records()`; `import_selected` routes several with New rig /
  Skeleton to `lineimport.run(chosen, _export_from_editor, mode, set_timeline=_timeline())`, Rig to the first
  with `first_only`; `import_dropped(records, aim)` takes a record or a list — a rig the first, a floor drop
  of several `lineimport.run(..., "new_rig", centre=aim point or origin, axis=aim axis or X)`;
  `export_uasset_selected` refuses several; `clip_target`'s "new_rig" aim carries `label` and `axis`.
- [ ] Tests for each route with the export, the status and the presses faked; droptarget expectations updated.
- [ ] FAIL → implement → PASS → commit `feat(uebridge): the list takes several animations; the button routes them`.

### Task 5: the drag carries several

**Files:** Modify `SkeldarAnim/maya_uebridge/listdrag.py`; Test `tests/test_uebridge_listdrag.py`.

- [ ] `carried_rows(pressed, before, after, plain)` (pure); the press remembers the rows picked before it and
  whether Ctrl/Shift was held; `_start` carries the rows and puts the selection back after the synthetic
  release; `dragging()` the first record, `carried()` the list; `drop_at(gx, gy, records=None)` takes a
  record or a list; `Scene.drop(records, aim)`; `caption(names, aim)`.
- [ ] Tests on an offscreen QListWidget in ExtendedSelection: two rows picked, press on one, drag, release far
  → both carried, both still selected; press on an unpicked row → that row alone; Shift+press → the range;
  captions for several.
- [ ] FAIL → implement → PASS → commit `feat(uebridge): a drag carries every picked animation`.

### Task 6: live proof, docs, install

- [ ] `docs/superpowers/plans/verify_uebridge_many.py` in a disposable Maya (port 7023, scratch
  `MAYA_APP_DIR`, `MAYA_NO_HOME=1`), the editor's export replaced by clips on disk (LongSword_Attack_Right_
  Heavy_1P, ShortSword_Attack_Thrust_3P — 249 cm of root motion forward, 23 cm sideways — ShortSword_Walk_1P):
  button New rig, button Skeleton, button Rig (first only), drag of three onto the floor with the camera
  looking along X (the thrust's forward travel is sideways to the line: widened), drag of three onto a rig
  (first only), the selection kept; Main/root on slots computed from an independent `currentTime` walk.
- [ ] Full unit suite; CLAUDE.md section (only this hunk staged); ask the peers, then install into the
  animator's Maya from a `git archive`; push.
