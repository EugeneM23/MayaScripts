# Pose on clip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a standalone script that puts a Walk Builder pose onto a locomotion clip (the sprint stop first) and keys the result onto a copy of the character beside it.

**Architecture:** `poseclip.py` is the model (numpy + a copied `posemath`): the clip's reference, the pose read against it, per-frame synthesis (torso and head in world axes, arms in locals, feet by one rigid motion a contact, legs by IK, pelvis by the height rule, balance and reach). `poseclip_maya.py` reads the scene, duplicates the character with its upstream graph and keys it. Nothing in `SkeldarAnim/` changes.

**Tech Stack:** Maya 2027 mayapy (Python 3, numpy, maya.api.OpenMaya, maya.cmds), stdlib unittest.

## Global Constraints

- Everything lives in `docs/superpowers/plans/poseclip/`; `SkeldarAnim/` is not modified.
- No interface: `poseclip_maya.apply(pose, share=1.0, motion=1.0, parts=PARTS, offset=150.0)` from the Script Editor.
- Poses: `<userAppDir>/SkeldarWalks/<name>.wpose.gz` (format `skeldar.walkpose`) or a path to one.
- Row-vector matrices (`world = local . parent`), centimetres, Y up.
- `share 0` reproduces the clip; a planted foot stays planted; the original character is never written.
- One undo chunk per apply; a second apply for the same source replaces the copy.
- Tests run with `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_poseclip -v` from the repo root.

---

### Task 1: The folder, the copied modules, the rotation toolkit

**Files:**
- Create: `docs/superpowers/plans/poseclip/posemath.py` (copy of `SkeldarAnim/maya_poselib/posemath.py`, `import maya_skeletonmap as skelmap` -> `import skeletonmap as skelmap`, a header line naming the source commit)
- Create: `docs/superpowers/plans/poseclip/skeletonmap.py` (copy of `SkeldarAnim/maya_skeletonmap.py`, header line)
- Create: `docs/superpowers/plans/poseclip/manny_skeleton_template.json` (copy of `SkeldarAnim/assets/manny_skeleton_template.json`)
- Create: `docs/superpowers/plans/poseclip/poseclip.py` (toolkit part)
- Test: `tests/test_poseclip.py`

**Interfaces — produces** (`poseclip`): `exp_rot(w)`, `log_rot(r)`, `mean_rot(rs)`, `orthonormal(m)`, `toward(a, b, alpha)`, `power(r, k)` (= `exp_rot(k log_rot(r))`), `slerp(a, b, w)`, `blend_matrix(a, b, alpha)`, `two_bone(hip, ankle, l1, l2, bend, reach)`, `align(u_src, n_src, u_new, n_new)`, `turned_about(v, axis, angle)`, `matrix(rot, pos)`, `yaw_of(r)`, `yaw(angle)`. Copied verbatim from `SkeldarAnim/maya_walk/model.py` where they exist there.

- [ ] Tests: `exp_rot(log_rot(r)) == r` for random rotations; `toward(a, b, 0) is a`, `toward(a, b, 1) ~ b`; `power(r, 0) == I`, `power(r, 1) == r`; `two_bone` reaches an ankle within reach exactly and falls short by `d - reach (l1 + l2)` beyond it; `align` takes (u, n) onto (u', n'); `yaw(yaw_of(exp_rot([0, a, 0]))) == exp_rot([0, a, 0])`.
- [ ] Run, see them fail (no module), write the toolkit, run green.
- [ ] Copy the three plugin files, check `import posemath` works under mayapy from the folder.
- [ ] Commit.

### Task 2: The clip analysis (pure)

**Files:** Modify `poseclip.py`; test `tests/test_poseclip.py`.

**Interfaces — produces:**
- `Clip(names, parents, worlds, fps=30.0, name="clip")` — `worlds` (J, F, 4, 4); `.index`, `.order` (parents first).
- `kind_of(name)` -> one of `root, pelvis, torso, leg, toe, legtwist, arm, finger, helper` (by UE leaf; descendants of a hand that are not helpers are fingers; anything unknown a helper).
- `still_run(speeds, threshold=STILL_SPEED, least=STILL_MIN)` -> `(a, b)` inclusive or `None`; `speeds` (F,) the body's largest joint speed a frame.
- `runs(mask)` -> list of inclusive `(a, b)`; `contacts(still, merge=1, least=2)` -> merged runs.
- `cover(need, sigma)` — `smooth_cover` with held ends (pad by the edge values, no wrap).
- `foot_weights(down_l, down_r)` -> (F, 2): one foot down 1; both down from a landing a linear hand-over to the foot that stays (to 0.5 / 0.5 over `SETTLE` frames when nobody lifts); none down interpolated in time between the neighbours.
- `Analysis(clip)` — heading `H` (F, 3, 3) from the root's turn about up; `rel` (J, F, 3, 3) relative world rotations; `local` (J, F, 3, 3) and `offset` (J, F, 3) (the child's place in the parent's rigid frame); the reference `(a, b)` and per bone `rel_ref`, `local_ref`; `floor`, `h_ref`; per side `still`, `down`, `contacts`, `pivot` (F, 3), `lengths` (F, 2); `masses` (de Leva, Walk Builder's table); `com` (F, 3); `support` (F, 3) from `foot_weights`; `ref_offset` (3,).

- [ ] Tests on a synthetic biped (built in the test from `manny_skeleton_template.json`: a root sliding forward 20 cm a frame for 10 frames then still, the pelvis dipping, both feet planted from frame 12 on, the left foot also planted 3-6): `kind_of` on every Manny name; `still_run` finds 14..end; `contacts` gives left `[(3, 6), (12, F-1)]`; `foot_weights` sums to 1 where a foot is down, hands over linearly, interpolates across a flight; `cover` lies over every need and holds its ends; `Analysis` reproduces the template rest at frame 0 of a still clip (`rel_ref` identity heading).
- [ ] Red, implement, green, commit.

### Task 3: The pose against the reference (pure)

**Files:** Modify `poseclip.py`; test `tests/test_poseclip.py`.

**Interfaces — consumes:** `Analysis`, `posemath.pairs / twin / Transfer`. **Produces:** `prepare(analysis, statics, pose_bones)` -> dict:
`rel` {j: 3x3 relative world}, `local` {j: 3x3}, `height` (pelvis over its lower ball), `feet` {side: 4x4 target foot world at the reference}, `ball` {side: 3x3 ball local}, `knee_turn` {side: radians}, `grip` (bool), `grip_rel` (4x4 left hand in the right hand's space), `holds` {helper j: 4x4 relation to its body bone}, `offset` (3,) CoM - support, `width` (pose spread - reference spread along the side axis), `scale`.
`PARTS = ("torso", "pelvis", "knees", "arms", "feet")`; `filtered(pose, parts)`.

- [ ] Tests: a pose that IS the clip's reference (the synthetic biped at rest as a pose) prepares to `rel == rel_ref`, `local == local_ref`, `height == h_ref`, the feet on the reference feet, `knee_turn` 0, `width` 0, `offset == ref_offset`; a pose with the pelvis 20 cm lower gives `height = h_ref - 20`; a pose with the feet 20 cm wider gives `width = 20`; `filtered` drops a part's keys.
- [ ] Red, implement, green, commit.

### Task 4: The synthesis (pure)

**Files:** Modify `poseclip.py`; test `tests/test_poseclip.py`.

**Interfaces — produces:** `evaluate(analysis, pose, share=1.0, motion=1.0)` -> `Result(worlds (J, F, 4, 4), info)`; `info`: `carry` (largest balance carry, cm), `drop` (largest reach sink, cm), `moved` {side: number of contacts moved}, `final` {side: contact index or None}.
Internals: `contact_motions(analysis, pose, share)` -> per side per frame `(Q, c, d, final_weight)`; `_frame(f, ...)` one frame's rots and poss; `_carry` the balance; `_legs` the IK; the reach cover.

- [ ] Tests on the synthetic biped: `share 0` gives the clip's worlds to 1e-6; `share 1, motion 0` in the reference gives the pose's torso relative rotations, the pose's pelvis height and the feet on the pose's targets; a planted foot (left, frames 3-6 and 12-end) never moves more than the clip's own foot did; every bone length is the clip's; the CoM minus support is the clip's (+ the pose's - reference's offset) where a foot is down, to 0.05 cm; `motion 0` stills the torso's own motion.
- [ ] Red, implement, green, commit.

### Task 5: The scene (`poseclip_maya.py`)

**Files:** Create `docs/superpowers/plans/poseclip/poseclip_maya.py`.

**Interfaces — produces:**
- `top_joint(node)`, `character_group(root)`; `read_clip(root)` -> `(Clip, start)`; `read_statics(root)` -> `{leaf: {parent, canonical, rest}}` (skinCluster bind, else the template, else as it stands);
- `load_pose(name_or_path)` -> `(name, bones)`;
- `make_copy(group, name)` -> `(copy group, {original joint path: copy joint path}, created UUIDs)`; `remove_copies(source_uuid)`;
- `channel_values(...)` / `write_curves(...)` (Walk Builder's, keys through `MFnAnimCurve.addKeys`, translate and rotate on every joint, scale set to 1);
- `apply(pose, share=1.0, motion=1.0, parts=PARTS, offset=150.0, reference=None)` -> the status line. One undo chunk.

- [ ] No unit tests (cmds); proven by Task 6.
- [ ] Commit.

### Task 6: The proof (`verify_poseclip.py`) and pictures

**Files:** Create `docs/superpowers/plans/poseclip/verify_poseclip.py`, `render_poseclip.py`.

- [ ] mayapy standalone: the plugin's `Manny UE5 [skeleton]` added (its `character.add_character`, read only), the stop's FBX imported into a namespace and keyed onto it by the tool's own writer (every joint by world matrix), then the spec's five proof groups as gates with numbers.
- [ ] `render_poseclip.py`: side-view stick sheets (offscreen Qt) of the clip, the goblin and the sword at the brake and in the idle.
- [ ] Run, fix what the gates find, commit.

### Task 7: Live

- [ ] Over the port, in the animator's Maya, select the stop's skeleton and `apply("goblin")`; read back the copy; leave it there.
