# Creep 2 Arm R and Head on Manny's whole skeleton - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the Arm R and Head part assets (rig and skeleton) carry Creep 2's whole 93-bone skeleton,
the rigs keep every control, and the Pose Library works on them.

**Architecture:** one mayapy script edits each shipped asset in place.
- It imports `Creep2_Skeleton.ma` as the source of the missing joints and copies each missing joint's
  locals under its parent, top-down. The part's root already stands where Creep 2's does (measured
  2e-6).
- It re-parents the part's top joint (`clavicle_r` / `neck_01`) under `spine_05` with Creep 2's own
  locals.
- On a rig, it remakes the top joint's point / orient / scale constraints `-mo` (a point constraint's
  offset lives in the parent's space) and parent-constrains `spine_05` to `Root_M` `-mo`, the AS
  joint `PartAnchor` follows. A bone constrained to an AS joint is what the Pose Library's rig solve
  reads; a transform is not.
- It saves one bind pose over all 93 joints.
- On the Pose Library side, a card saved from a part rig takes only the bones the rig drives.

**Tech stack:** mayapy 2027 standalone, stdlib unittest.

## Global Constraints

- No control added or removed on the rigs; the AS rig is not rebuilt.
- Every part bone's world matrix unchanged (<= 1e-4); the mesh unchanged.
- The bones without controls carry no constraint and stand at the bind under `root`.
- One asset per mayapy process (trap 122); no script node, no machine path in a saved file.
- Keep `|Armature|root`, the part assets' layout (a spec deviation, recorded in its addendum).

---

### Task 1: `make_creep_parts_whole.py <rig|skeleton> <arm|head>`

**Files:** create `docs/superpowers/plans/make_creep_parts_whole.py`

- [ ] Open the asset (`executeScriptNodes=False`) and import `Creep2_Skeleton.ma` into namespace `src`.
- [ ] Record the world matrix of every joint under `|Armature|root`.
- [ ] Walk src top-down. For each joint missing from the part, create a joint under the part's joint
  of its parent's name, copying translate, rotate, jointOrient, rotateAxis, rotateOrder,
  segmentScaleCompensate and radius. The part's top joint goes under `spine_05` with src's locals.
- [ ] Rig: delete the top joint's constraints first (keeping their targets), then remake point /
  orient / scale `-mo`. `parentConstraint -mo Root_M spine_05`.
- [ ] Assert:
  - every recorded joint's world matrix is unchanged to 1e-4;
  - 93 joints, each with src's parent;
  - every new joint on src's world to 1e-4.
- [ ] Put the new joints in the root's display layer, save the whole bind pose (93 members), delete
  src, then save with the script-node cut and the banned-word check.
- [ ] Run it for rig arm, rig head, skeleton arm, skeleton head, one process each.

### Task 2: Pose Library - a part rig's card holds what the rig drives

**Files:**
- modify `SkeldarAnim/maya_poselib/scene.py`: `members_from_selection(..., limit=None)`, and
  `members_of` passes `driven_bones(ref)` for a rig whose group carries `skeldarPartAnchor`.
- test: `tests/test_poselib_scene.py`.

- [ ] Test: with `limit`, the whole body and the per-item bones keep only `limit`.
- [ ] Implement; run `tests/test_poselib_scene.py`.

### Task 3: Catalog pins, templates, verify

- [ ] `tests/test_scenesetup_catalog.py`: the part assets have 93 joints and `clavicle_r` /
  `neck_01` under `spine_05` (read from the `.ma` text).
- [ ] Re-run `make_character_skeletons.py`.
- [ ] `JOINTS` in `make_creep_part_assets.py` -> 93; `verify_creep_parts.py`'s counts.
- [ ] New `verify_creep_parts_manny.py`: the hierarchy, controls equal to `git show HEAD~:<asset>`'s,
  a retarget, the bind bones still, and the Pose Library cases.
- [ ] Run verify_creep_parts / part_drop / creep2_body and the unit suite; commit.
