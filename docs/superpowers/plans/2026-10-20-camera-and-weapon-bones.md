# Camera and weapon bones Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Pose Library writes `weapon_r` / `weapon_l` / `camera_root` / `camera_bone` from every card,
keying whatever drives them (our weapon, our camera), sets Camera Setup up where a card brings the camera;
the Creep gets camera bones; the skeleton road carries the helpers relative to their parent and re-binds the
camera.

**Architecture:** A pure+scene module `maya_poselib/helpers.py` adds the helper members at apply and writes
them (joint channels, or the driver's channels through the constant constraint offset). `posemath.Transfer`
carries a helper's displacement from its rest; `scene.rests` reads a helper's rest from the bind pose. The
body solvers never see helpers. `skeletonimport` gets a `relative` drive and the camera round trip.

**Tech Stack:** Maya 2027 cmds / OpenMaya 2.0, mayapy unittest (`tests/`, fake cmds), mayapy standalone verify.

Spec: `docs/superpowers/specs/2026-10-20-camera-and-weapon-bones-design.md`

## Global Constraints

- `HELPERS = ("weapon_r", "weapon_l", "camera_root", "camera_bone")`; `ik_*`, `interaction`, `center_of_mass` unchanged.
- weapon_r with hand_r, weapon_l with hand_l, camera bones with a whole-body card (`scene.whole_body`).
- Never `cmds.undo()` over the port; no GUI Maya / port 7001 / install (live checks are the animator's).
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . `
- UE4 Mannequin untouched.

---

### Task 1: helper rests from the bind pose (`scene.rests`)

**Files:** Modify `SkeldarAnim/maya_poselib/scene.py` (`rests`); Test `tests/test_poselib_scene.py` (`Rests`).

- [ ] Test: with `posed` holding HAND and WEAPON (weapon 5 cm further along the hand than it stands now),
  `rests(...)[WEAPON]` = `posed[WEAPON]·posed[HAND]⁻¹·rest[HAND]`; unlisted keeps the current local.

```python
    def test_an_unskinned_helper_listed_in_the_bind_pose_rests_at_its_bind_local(self):
        posed = {self.HAND: _at(-40, 100, 5, 30.0), self.WEAPON: _at(-48, 92, 5, 30.0)}
        out = scene.rests(self.PATHS, self.binds(), self.now(-150.0), posed)
        self.close(out[self.WEAPON], _at(-48, 92, 5, 30.0))
        unlisted = scene.rests(self.PATHS, self.binds(), self.now(-150.0), {})
        self.close(unlisted[self.WEAPON], _at(-45, 90, 5, 30.0))
```
- [ ] Implement in the "unskinned joint UNDER another" branch: if `path in posed and parent in posed`, use
  `matrix(posed[path]) * matrix(posed[parent]).inverse() * matrix(out[parent])`.
- [ ] Run `test_poselib_scene`, commit `fix(poselib): a helper bone rests at its bind-pose local`.

### Task 2: `posemath.Transfer` carries a helper's displacement

**Files:** Modify `SkeldarAnim/maya_poselib/posemath.py` (`Transfer.frame`, the non-pelvis place); Test
`tests/test_poselib_posemath.py` (new class `HelperPlace`).

- [ ] Tests (skeleton fixture + `weapon_r` under `hand_r`): twin with `places` → exact source local; another
  body (scale 0.8 lengths, own socket local (−6,−2,1)): at the source rest the target weapon stands on its own
  socket; with the source's weapon moved 5 cm along hand X from its rest, the target's moves 5·scale along its
  hand's X; non-helper members unchanged.
- [ ] Implement: in `frame`, for `is_helper(leaf)` members not `placed` with `parent == above`:

```python
rest_t = position(rigid(matrix(target[leaf]["rest"])) * rigid(matrix(target[parent]["rest"])).inverse())
sp = self.pairs.get(parent)
now_s = position(rigid(pose(s)) * rigid(pose(sp)).inverse())
rest_s = position(rigid(matrix(source[s]["rest"])) * rigid(matrix(source[sp]["rest"])).inverse())
d = (now_s - rest_s) * rotation(self._offset(parent)).inverse() * self.scale
t = rest_t + d
```
- [ ] Run, commit `feat(poselib): a helper member carries its displacement from its rest`.

### Task 3: `maya_poselib/helpers.py` - members and the Writer

**Files:** Create `SkeldarAnim/maya_poselib/helpers.py`; Test `tests/test_poselib_helpers.py`.

**Produces:** `HELPERS`, `CAMERA`, `members_with(members, bones) -> list`, `split(members) -> (body, helpers)`,
`Writer(ref, bones, leaves)` with `.solve(wanted, seed=None) -> skelsolve.Solution`, `.notes`, `.skipped`,
`.camera_bone()` (path of camera_root to set up, or None), `.plugs()`.

- [ ] Tests (pure): `members_with` adds weapon_r with hand_r, weapon_l with hand_l, camera with whole body only,
  nothing the skeleton lacks, no duplicates; `split`.
- [ ] Tests (fake cmds, rebinding `helpers.cmds`, `helpers.bonedrive`, `helpers.camera`, `helpers.connections`
  seams): free joint → its rotate+translate plugs from the local against the parent's wanted; weapon driver
  → the weapon's plugs at `K⁻¹·W` with the carrier moving the space; camera → camera plugs; followers → skipped
  with the note; foreign constraint → skipped.
- [ ] Implement; driver channels via `driver_channels(local, node)` (MTransformationMatrix with the node's
  scale, shear, pivots, rotateAxis; translate = `pos(local) − pos(X)`).
- [ ] Run, commit `feat(poselib): helpers - the four helper bones, keyed on what drives them`.

### Task 4: wire the Writer into apply, Blend and animapply

**Files:** Modify `SkeldarAnim/maya_poselib/apply.py` (`_plan`, `_apply_refs`), `animapply.py` (`_Target`,
`_press_refs`), `Blend.finish` paths; Test `tests/test_poselib_apply.py`, `tests/test_poselib_animapply.py`.

- [ ] `_plan`: `members = helpers.members_with(members, source)` (after mirror); body members to the solvers
  without helpers (`placed` without helpers); the Writer's values merged after the body's; Extra members without
  helpers; `Plan.notes` + writer notes; `Plan` gains nothing new - the camera bone travels in a new field
  `Extra.camera` (path or None).
- [ ] After `_key_entries` inside `_press`: `helpers.set_camera(extra.camera)` for each entry keyed at alpha
  1 or the Blend finish; its line joins the notes.
- [ ] `animapply._Target`: the same split; `_solve` merges `self.writer.solve(wanted, seed)`; after the frames,
  inside the chunk, the camera set up.
- [ ] Tests: fakes assert the solvers get no helper members and the values hold the writer's plugs.
- [ ] Commit `feat(poselib): every card writes its camera and weapon bones`.

### Task 5: the Camera Setup camera is the body

**Files:** `scene.is_body`, `apply.card_objects` / `animapply._card_matched` filter; tests in
`test_poselib_scene.py`, `test_poselib_apply.py`.

- [ ] `is_body`: a transform with `camera.MARKER` → True. Card objects found or matched carrying the marker
  dropped. Commit.

### Task 6: the Creep's camera bones

**Files:** Create `docs/superpowers/plans/make_creep_camera_bones.py`; run it; run
`make_character_skeletons.py`; tests pinning Creep joint counts/sha updated.

- [ ] Script per the spec; run on both assets; checks print; `character_skeletons.json` rewritten; unit tests
  green. Commit assets + script.

### Task 7: the skeleton road

**Files:** `SkeldarAnim/maya_uebridge/skeletonimport.py` (`drive_for`, `transfer`, `onto_refusal`,
`onto_existing`, the new-skeleton road); test `tests/test_uebridge_skeletonimport.py`.

- [ ] `drive_for(name, ...)` → `"relative"` for weapon_/camera_ onto another body; transfer builds the driver
  (`maya_rig_retarget._parent_space_driver`) and parent-constrains.
- [ ] Camera: `onto_refusal` ignores our camera's constraints; `onto_existing` tears down / sets up; after any
  skeleton transfer with a moving clip `camera_root` and a target `camera_root`, Camera Setup. Commit.

### Task 8: verify, docs

- [ ] `docs/superpowers/plans/verify_camera_weapon_bones.py` (spec's Proof) green in mayapy standalone;
  `verify_poselib_apply.py`, `verify_poselib_solve.py`, `verify_poselib_anim.py`, `verify_rig_pipeline.py`
  re-run; unit suite; CLAUDE.md section; commit; push (CI release).
