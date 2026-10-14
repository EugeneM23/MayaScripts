# Walk Builder on a sprint: legs matched to the gait, the trunk and the head on springs - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A walk (a sprint) under a pose runs on gait-matched legs, its upper body moves without the sprint's jitter, its head overlaps physically, and a repeated end frame no longer breaks the cycle.

**Architecture:** All model work in `SkeldarAnim/maya_walk/model.py` (numpy only): `trimmed` at analysis, `matched_pose` at evaluate (Leg match), `_body_dynamics` (two spring bodies) before `_arm_dynamics`, an ACCEL_HZ cap in `_smooth_accel`. `pose.prepare` hands the pose's hip yaw; the card gets four knobs; the status line says what Leg match did.

**Tech Stack:** Python 3 / numpy in mayapy 2027; unittest (`mayapy -m unittest`); verifies in mayapy standalone.

## Global Constraints

- `model.py` imports nothing of Maya (`PurityTests`); Maya's row vectors throughout (`world = local . parent`).
- New knobs (name, default, low, high): `("leg_match", 1.0, 0.0, 1.0)`, `("torso_drag", 2.0, 0.0, 8.0)`, `("torso_bounce", 0.2, 0.0, 1.0)`, `("head_drag", 2.5, 0.0, 8.0)`.
- `own_knobs()` give the source back: `torso_drag` 0 and `head_drag` 0 added.
- `leg_match` 0 is today's reading of a pose's legs, exactly.
- Overlap no longer shifts the spine, the neck or the head (LAG loses those entries); the arms keep it.
- Run tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walkmodel tests.test_walktarget tests.test_walk_panel` from the repo root.

---

### Task 1: A repeated frame is dropped

**Files:** Modify `SkeldarAnim/maya_walk/model.py` (new `DUP_TOL`, `trimmed`, `Walk.__init__`, `Walk.summary`); Test `tests/test_walkmodel.py` (new `TrimTests`).

**Interfaces:** Produces `trimmed(clip) -> (Clip, int)`, `Walk.dropped: int`.

- [ ] Write `TrimTests`: a synthetic clip with its last frame appended again reads `P == 24`, `dropped == 1`, `evaluate(own_knobs())` equal to the plain clip to 1e-6; the same with the first frame repeated; the summary says "repeated".
- [ ] Run, see them fail (P 25).
- [ ] Implement:

```python
DUP_TOL = (1e-3, 1e-5)   # cm, rotation elements: two frames this alike are one frame written twice


def trimmed(clip):
    """(clip, how many frames dropped): a cycle whose last frame repeats the one before it - or whose first the one
    after it - is one frame written twice (an export's closing frame, keyed again); with the copy in, every joint
    stood still a frame a cycle and every place carried a sawtooth of a frame's travel (AGS_Sprint, 2026-10-14). A
    walk's root travels, so two equal frames are never motion."""
    worlds = clip.worlds
    same = lambda a, b: (float(np.abs(worlds[:, a, 3, :3] - worlds[:, b, 3, :3]).max()) <= DUP_TOL[0] and
                         float(np.abs(worlds[:, a, :3, :3] - worlds[:, b, :3, :3]).max()) <= DUP_TOL[1])
    lo, hi = 0, worlds.shape[1] - 1
    while hi - lo > 9 and same(hi, hi - 1):
        hi -= 1
    while hi - lo > 9 and same(lo, lo + 1):
        lo += 1
    dropped = lo + (worlds.shape[1] - 1 - hi)
    if not dropped:
        return clip, 0
    return Clip(clip.names, clip.parents, worlds[:, lo:hi + 1], clip.fps, clip.up, clip.name), dropped
```
`Walk.__init__` starts `clip, self.dropped = trimmed(clip)` before `straightened`; `summary()` adds `" | %d repeated frame(s) dropped"`.
- [ ] Run the walk suites, green. Commit `fix(walk): a repeated frame at a cycle's end is dropped`.

### Task 2: Leg match

**Files:** Modify `model.py` (`KNOBS`, `GAIT_FROUDE`, `Walk._legs_and_pelvis` stores `leg_length`, new `Walk.gait_keep`, `knee_headings`, `toe_headings`, `matched_pose`, `_spine_takes`, `evaluate`), `pose.py` (`prepare` -> `"hips_yaw"`, `filtered` keeps it); Test `tests/test_walkmodel.py` (`LegMatchTests`; existing pose tests pass `leg_match=0`), `tests/test_walktarget.py` if prepare is tested there.

**Interfaces:** Consumes `pose["hips_yaw"]` (radians, + toward the walk's side axis). Produces `Walk.gait_keep(k, n) -> (keep, froude)`, `Walk.matched_pose(pose, m, keep) -> dict`, `info["leg_match"] = {"keep", "hips_deg", "on"}`.

- [ ] Tests: (a) `gait_keep` falls as Stride or Tempo speed the cycle; equals `1/(1+v^2/(981 L))`. (b) a pose yawed 30 deg about up (pelvis, hips_yaw) with spine locals: at leg_match 1 the pelvis's mean heading is the walk's, the chest's (last spine joint) world rotation the pose's (exaggeration 0), at 0 the pelvis turned 30. (c) knee/toe turns `{"l": a+d, "r": -(b+d)}` with hips_yaw d: matched turns are `sign * keep * (mean outward splay - the walk's own)`, raw at 0. (d) width x keep.
- [ ] Implement as specified in the spec section 2; `evaluate` replaces `ctx["pose"]` by `matched_pose` before `spread`, `spine_map` and `turns`.
- [ ] Existing pose tests that check the raw reading get `leg_match=0`.
- [ ] Green; commit `feat(walk): Leg match - a pose's legs matched to the gait`.

### Task 3: The trunk and the head on springs; the accel cap; Overlap for the arms

**Files:** Modify `model.py` (`KNOBS`, `LAG`, constants `ACCEL_HZ`, `TORSO_SHARES` rule, `NECK_SHARES`, `HEAD_LIFT`, `BODY_INERTIA`; `_smooth_accel` cap; new `_trunk_chains`, `_body_motion`, `_body_dynamics`; `evaluate` calls it in `armed()` and before the final `_arm_dynamics`; `own_knobs`); Test `tests/test_walkmodel.py` (`BodyDynamicsTests`; tests of other features pass `torso_drag=0, head_drag=0` where they measure exact spine/head values).

**Interfaces:** Produces `Walk._body_dynamics(worlds, n, ctx, only=None) -> {"torso": deg, "head": deg}` (in place on worlds), `info["body"]`.

- [ ] Tests: drags 0 = the frames; a walker whose pelvis jolts (a high harmonic on its pitch) - the chest's world rotation is smoother (residual against a 1-frame blur) and lags the frames' by about the drag; the head's world rotation deviates less from its mean than the frames' (gaze held); bones' lengths and the loop kept; own_knobs the source.
- [ ] Implement per spec section 3; `_smooth_accel` top = `min(ARM_HARMONICS * strides, int(ACCEL_HZ * n / fps), (n - 1) // 2)`, ACCEL_HZ = 8.
- [ ] Green; commit `feat(walk): the trunk and the head on springs - physical overlap, the jitter filtered`.

### Task 4: The card and the status line

**Files:** Modify `SkeldarAnim/maya_walk/panel.py` (`GROUPS`, `LABELS`), `scene.py` (`apply` text); Test `tests/test_walk_panel.py`.

- [ ] Legs: `leg_match` before `leg_turn`; Chest: `torso_drag`, `torso_bounce`, `head_drag` after `head`; labels and tips; Overlap's tip says arms only. Status: `" | legs matched x%.2f"`.
- [ ] Panel tests green (every knob in one group); commit.

### Task 5: Proof

**Files:** Create `docs/superpowers/plans/walkparam/verify_walk_sprint.py`; run `verify_walk.py`, fix gates that encode the old defaults by naming the knobs they test; CLAUDE.md section.

- [ ] verify_walk_sprint gates: the copy dropped; no frame stands still; knees' sideways swing and heading the source's; hips face the walk, shoulders the pose's 36 deg; chest/head/arms jerk below the kinematic version's and the old (61-frame) scene's; lengths; grip held; own knobs the source; picture.
- [ ] Commit; ask before push.
