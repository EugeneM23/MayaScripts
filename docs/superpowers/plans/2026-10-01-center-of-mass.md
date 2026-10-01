# Center of Mass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A live CoM point for every rig and bare skeleton, a fast Maya-looking trail of it, and a
tool that drags the CoM and moves the body with it.

**Architecture:**
- The mass model is a voxel union of the character's capped mesh shells, skinned by the closest
  surface point. It becomes per-joint masses and local centres, which feed a 9-node stock DG sum.
- Our engine walks the dirty frames through the parallel EM in idle slices and writes the points into
  `motionTrailShape`s.
- A `draggerContext` moves every world driver of the rig by the same world vector.

**Tech Stack:** Maya 2027 cmds + OpenMaya 2.0, numpy (ships with mayapy), PySide6 QTimer, unittest
under mayapy.

Spec: `docs/superpowers/specs/2026-10-01-center-of-mass-design.md`.

## Global Constraints

- Package `SkeldarAnim/maya_com/` (a payload row `"maya_com"`); every pure module imports no `maya`.
- Rig nodes live in the rig's namespace; identity by attribute `skeldarCom` (never by name).
- `Main` is never moved by the tool; the UE bone `center_of_mass` is never touched.
- Module state that outlives an install purge lives on `sys._skeldar_com` (trap 111).
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
- Live work only in a disposable GUI Maya (scratch `MAYA_APP_DIR`, `MAYA_NO_HOME=1`, a free port),
  killed after; install from a `git archive` of a commit (parallel sessions in the repo).
- Commit only this feature's files and hunks.

---

### Task 1: The mass model (`maya_com/massmodel.py`, pure numpy)

**Files:**
- Create: `SkeldarAnim/maya_com/__init__.py` (docstring + lazy `__getattr__` for `build_panel`)
- Create: `SkeldarAnim/maya_com/massmodel.py`
- Test: `tests/test_com_massmodel.py`

**Interfaces — Produces:**
- `border_loops(triangles) -> list[list[int]]`: ordered vertex loops of the boundary edges.
- `capped(points, triangles) -> (points2, triangles2, cap_of)`: one fan per loop, its centre the
  loop's mean, appended. `cap_of[i]` is the loop index of each new point (-1 for the originals).
- `shells(triangles) -> list[np.ndarray]`: triangle index arrays of connected shells.
- `inside(points, triangles, centres) -> bool array`: 3-axis ray parity per closed triangle soup,
  with a majority vote.
- `voxel_centres(bbox_min, bbox_max, step, jitter=(0.37, 0.61, 0.23)) -> (N,3)`.
- `accumulate(centres, dv, joint_weights, blend_inverse, bind) -> (masses: dict, centres_local: dict)`:
  - `joint_weights` is a list of `{joint: w}` per centre;
  - `blend_inverse[i]` = (Σ w_j B_j M_j)⁻¹ (4×4);
  - `bind[j]` = B_j.
- `com(masses, centres_local, world) -> np.array(3)`: Σ m_j c_j·M_j / Σ m_j (the reference the DG must
  equal).
- `segment_fractions(masses, segment_of) -> dict` (for the de Leva gate).

**Steps:**
- [ ] Write the tests:
  - an open tube (a cylinder without end caps, r 5, h 20) capped is closed, and `inside` finds
    π·25·20 within 3 % at step 0.5;
  - a box inside a bigger box in ONE soup (nested shells): the union is the bigger box's volume,
    shell by shell;
  - two overlapping boxes: the union volume, not the sum;
  - `accumulate` with one joint at identity puts the box's centroid in `c` and its volume in `m`;
  - a two-joint 50/50 element at a known pose: `com` equals the LBS-deformed point;
  - `border_loops` of a grid sheet is one loop of the perimeter.
- [ ] Run them: they fail (no module).
- [ ] Implement:
  - fan caps from the loops;
  - shells by union-find over shared edges;
  - parity: per axis, per grid line, the triangles' 2D bbox tests vectorised, barycentric in 2D, the
    crossing coordinate, then `searchsorted` per line;
  - majority over 3 axes; union over shells.
- [ ] Run: PASS.
- [ ] Commit `feat(com): the mass model - a voxel union of capped shells, skinned`.

### Task 2: The frame maths (`maya_com/frames.py`, pure)

**Files:** Create `SkeldarAnim/maya_com/frames.py`; Test `tests/test_com_frames.py`.

**Interfaces — Produces:**
- `trail_range(mode, playback, current, around) -> (start, end)`: Playback is the playback range;
  Around is `current ± around`, clipped to the animation range.
- `changed_frames(before, after, tol=1e-9) -> set[int]`: dicts frame→value.
- `nearest_first(dirty, current) -> list[int]`.
- `budget(per_frame_ms, slice_ms, cost_return_ms) -> int` (≥ 1).
- `merge_points(points, frames_values) -> dict`.

**Steps:**
- [ ] Tests:
  - changed frames for a key edit (only the changed ones);
  - nearest-first ordering, with ties earlier first;
  - Around clipped;
  - budget arithmetic;
  - a new frame range keeps the known points and dirties the new.
- [ ] Fail → implement → pass.
- [ ] Commit `feat(com): frame maths for the trail engine`.

### Task 3: The drag maths (`maya_com/dragmath.py`, pure)

**Files:** Create `SkeldarAnim/maya_com/dragmath.py`; Test `tests/test_com_dragmath.py`.

**Interfaces — Produces:**
- `RIG_DRIVERS = ("RootX_M", "IKLeg_L", "IKLeg_R", "IKArm_L", "IKArm_R", "PoleLeg_L", "PoleLeg_R",
  "PoleArm_L", "PoleArm_R", "IKSpine1_M", "IKSpine2_M", "IKSpine3_M")`.
- `SKELETON_DRIVERS = ("pelvis", "ik_foot_root", "ik_hand_root")`.
- `ray_plane(origin, direction, point, normal) -> point|None`.
- `ray_line_closest(origin, direction, point, axis) -> point`.
- `mode_for(modifier) -> "view"|"floor"|"vertical"`: "shift" → floor, "ctrl" → vertical.
- `drag_point(mode, ray, com, view_dir) -> point`.
- `solve_local(target, measured, parent_inverse3) -> delta_local`.
- `apply(plan, start, d) -> {driver: (x,y,z)}`, where a plan is `{driver: 3x3}` and the result is
  `start + d·A`.
- `autokey_channels(moved, has_curve, autokey_on) -> list[(driver, attr)]`.

**Steps:**
- [ ] Tests: ray/plane and ray/line; the modifiers; `apply` linearity; autoKey keys only curve
  channels when on, none when off.
- [ ] Fail → implement → pass.
- [ ] Commit `feat(com): drag maths`.

### Task 4: The scene side — sampling and the network (`maya_com/network.py`, cmds)

**Files:** Create `SkeldarAnim/maya_com/network.py`; Test `tests/test_com_network.py` (the pure helpers:
weights from masses, the mesh filter; the rest is live).

**Interfaces:**
- Consumes: `massmodel.*`, `maya_rigs`, `maya_scenesetup.skeleton.current_root`.
- Produces:
  - `Character = namedtuple("Character", "root rig namespace label")`;
  - `character()` → (Character, refusal);
  - `meshes_of(character) -> [(shape, skinCluster)]`, filtered by `is_first_person(name)` (pure);
  - `sample(character) -> dict` (points, triangles, weights, joints, bind, world);
  - `build_model(character) -> (masses, centres_local, volume)`;
  - `weights(masses, centres) -> rows` (pure: `[(joint, wx, wy, wz, wt)]`);
  - `create(character, masses, centres, volume) -> group`;
  - `find_all() -> [group]`;
  - `group_of(character)`;
  - `remove(group)`;
  - `handle_of(group)`, `trail_shapes(group)`, `com_plug(group)`, `root_of(group)`;
  - `drivers(group) -> [control paths]`.

**Steps:**
- [ ] Tests (pure): `is_first_person` («Hands_1P», «Orc_D_1PShape» yes; «Skin_3p», «Creep_Body» no);
  `weights` normalisation and the row layout.
- [ ] Implement:
  - sampling through OpenMaya: the deformed world mesh points, triangles, per-vertex weights from the
    skinCluster (`MFnSkinCluster.getWeights`), joints' current world matrices, the bindPreMatrix per
    influence;
  - closest points through `MMeshIntersector`;
  - the 9-node network, the handle shape, floor marker, trail shapes, the group's attributes, a
    message link `root.message → group.skeldarComRoot`.
- [ ] Unit tests pass; a mayapy smoke (Task 8's verify phase 1) proves the network.
- [ ] Commit `feat(com): the live CoM - nine stock nodes from the skin's mass`.

### Task 5: The trail engine (`maya_com/engine.py`)

**Files:** Create `SkeldarAnim/maya_com/engine.py`; Test `tests/test_com_engine.py` (the tick decisions
with a fake clock and fake scene seam).

**Interfaces — Produces:**
- `start()`, `stop()`, `state()`;
- `track(group)`, `untrack(group)`;
- `dirty_all(group)`;
- `tick()` (one slice, returns frames done);
- `pending() -> int`;
- `walk(frames) -> {group: {frame: (x,y,z,root_y)}}`;
- `preserve_tweaks(groups)` (context manager);
- `write_points(group)`.

**Steps:**
- [ ] Tests:
  - tick skips with a button down or during playback;
  - takes the nearest frames up to the budget;
  - a curve edit dirties only its changed frames;
  - a static set dirties all;
  - a tweak set dirties none but the live current point;
  - state survives a module reload (on `sys`).
- [ ] Implement the callbacks (MAnimMessage, MNodeMessage per control/joint, scriptJobs for
  playbackRangeChanged / SceneOpened / timeChanged for Around) and the QTimer slice.
- [ ] Pass; commit `feat(com): the trail engine - dirty frames walked in idle slices`.

### Task 6: The CoM tool (`maya_com/drag.py`)

**Files:** Create `SkeldarAnim/maya_com/drag.py`; Test `tests/test_com_drag.py` (the tool switching
decisions, pure).

**Interfaces — Produces:**
- `CONTEXT = "skeldarComContext"`;
- `ensure_context()`;
- `activate()`, `deactivate()`;
- `on_selection()`, `on_tool_changed()`;
- `press()`, `drag()`, `release()`;
- `plan(group) -> {driver: 3x3}`;
- `move(group, d, autokey=None) -> message`: the scripted equivalent of a drag, for verify and numbers.

**Steps:**
- [ ] Tests: which tool to restore; switching only with handles alone selected.
- [ ] Implement; pass; commit `feat(com): the CoM tool - drag the point, the body follows`.

### Task 7: The hub section, icon, hotkey row, payload

**Files:**
- Create: `SkeldarAnim/maya_com/panel.py`.
- Modify:
  - `SkeldarAnim/maya_hub.py` (SECTIONS row after graphoverlay);
  - `SkeldarAnim/maya_hubicons.py` ("target");
  - `SkeldarAnim/maya_hotkeys.py` (`window.com`);
  - `SkeldarAnim/install.py` (payload `"maya_com"`).
- Tests:
  - `tests/test_com_panel.py`;
  - update `tests/test_hub.py` (labels, groups, cards, builders, order);
  - update `tests/test_hotkeys.py` (openers count 11);
  - update `tests/test_install.py`.

**Steps:**
- [ ] Update the pinned tests first (they fail).
- [ ] Implement `build_panel`, `refresh`, `is_open`, `show_window`; the presses (Add, Remove, Rebuild,
  Select) run through `_run` onto the status line.
- [ ] Full suite green; commit `feat(com): the Center of Mass section`.

### Task 8: Live proof, docs, install

**Files:**
- Create: `docs/superpowers/plans/verify_com.py`.
- Modify: `CLAUDE.md` (a section + traps), memory.

**Steps:**
- [ ] Disposable GUI Maya with the repo's `SkeldarAnim` first on `sys.path`. Manny, Creep and Orc D
  are added by `character.add_character`, a take is keyed, and the gates from the spec are run.
- [ ] A playblast of the trail, looked at.
- [ ] CLAUDE.md section; commit; install refresh from `git archive HEAD` into the animator's installed
  copy only if the port is open and the scene is not a plugin asset (memory).
