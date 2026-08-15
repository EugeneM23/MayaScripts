# Spline-IK spine v2 — three controls, surviving pelvis, no aim

Date: 2026-08-15
Status: built and live-verified (all three verify scripts green in the scene)
Branch: `feature/overrig-picker`
Supersedes: the spine section of `2026-08-15-spine-ik-picker-controls-design.md`

## Why v1 died

The first spine IK reused OverRig's rebike (3 joints, limb-style). The user
rejected it on sight, with two specific complaints and a reference:

1. **Bug:** with the spine in IK, moving the top control moved everything
   except the fingers. Root cause: `dependent_chains` catches every chain
   whose controller sits *anywhere* inside the spine containers — finger
   chains inside an FK arm included, transitively. They were lifted to world
   and, their attach bone (`hand_l`) not being one the spine re-hangs, left
   there.
2. **Design:** a limb-style 2-bone IK is the wrong mechanism for a torso.
   The reference is Advanced Skeleton's hybrid spine: the pelvis controller
   survives the switch; three nodes — bottom at pelvis level, top at the
   chest, middle following both at 50/50 yet still animatable; no aim
   behaviour anywhere.

## The design (verified against the standard references)

The industry-standard spline spine, per the Autodesk realtime-rigging course
and Riham Toulan's advanced-twist tutorial:

- **Pelvis is its own single-knot FK chain** (`CHAINS` gains `pelvis`,
  spine becomes `spine_01..spine_05`). A spine switch never touches its
  manifest — that is what "общий контроллер таза остается" means
  structurally. Thigh chains hang off the pelvis controller and never move
  during a spine switch.
- **`spineik.py` builds the rig** (our own Maya nodes, no OverRig proc):
  - degree-2 curve through spine_01 / spine_03 / spine_05;
  - one cluster per CV, handles parented under the three controls;
  - `ikSplineSolver` spine_01 → spine_05, `rootOnCurve`;
  - **advanced twist**: `dWorldUpType` 4 (Object Rotation Up start/end),
    up objects = bottom and top controls, forward axis +X (the bones aim
    along X on this skeleton — the only axis the twist supports), up axis =
    joint-local +Z with the world vectors measured at build. This is what
    replaces aim: roll interpolates between the two controls' rotations;
  - the chest bone is orient-constrained to the top control — the solver
    orients the chain, the animator owns the chest exactly;
  - **middle**: a blend group point+orient-constrained 50/50 (maintain
    offset, shortest interp) between bottom and top; the control sits under
    it through a zero group, so its own channels animate on top of the
    blend. Measured live: top +10 → mid moves 5.00;
  - **bottom sits at pelvis height** and sways the lower spine while the
    chest stays planted (measured: 8.0 vs 1.07);
  - all zero groups are **parent-constrained to the pelvis BONE** — not to
    any controller by name — so the rig rides whatever drives the pelvis
    and merely stops following if that driver is torn down.
- **Animation capture**: temp parent constraints (bottom←spine_01,
  mid←spine_03, top←spine_05), `apply_Fast_Bake`, delete temps, then cut
  the bones' rotation keys (they would fight the solver through
  pairBlends; the bake puts them back). Chest and base convert exactly;
  interior bones are a projection onto curve + twist — measured drift
  0.000–0.08 cm on this scene, bounded by the mid control carrying
  spine_03's animation.
- **Role addressing**: `builder.SPINE_IK_MARKS` (end=`IKSpine_top`,
  pole=`IKSpine_mid`, base=`IKSpine_bot`), matched against the *exact* leaf
  name (modulo numeric suffix) — a substring match resolved
  `IKSpine_mid_blend` before the control itself.
- **The dependents fix**: `spine_dependent_chains` (pure) keeps only chains
  whose own attach bone the spine re-hangs (`SPINE_REHANG = {spine_05:
  end}`); deeper chains ride their parent chain's subtree. Fingers stay on
  the hand through the whole switch — regression-checked live.

## Verified live (Manny scene, animated pelvis: 20 cm translate, 28° rotate)

- `verify_spine_ik.py` — SPINE IK WORKS: three controls resolve exactly,
  0.000 chest drift on convert and on bake-back, 50/50 both ways, waist
  animatable, lower-spine sway, rig follows the pelvis bone, no flip under
  large chest translate, picker circles live/dimmed correctly.
- `verify_spine_switch.py` — SPINE SWITCH WORKS: pelvis controller and
  manifest survive, thighs and fingers never lifted, neck+clavicles re-hang
  on the top node and back on `spine_05_FK_ctrl`, fingers follow the top
  control (the bug), 0.000–0.011 cm drift, scene at baseline after bake.
- `verify_hybrid_build.py` — HYBRID BUILD WORKS with the pelvis chain in
  `HYBRID_FK_CHAINS` (14 chains + 4 IK limbs, 18 full-FK).

## v3 — the user's corrections (same day)

Two changes requested after trying v2 in the scene, both live-verified:

1. **The bottom node moves the pelvis.** The pelvis's own FK controller is
   re-hung INSIDE `IKSpine_bot` through `apply_Parent_in` (animation
   re-baked, zero drift): the general pelvis control keeps working, and the
   bottom node now carries the pelvis bone and every FK chain riding it
   (thighs measured following 8.00/8.00). Two hidden followers close the
   loops: `IKSpine_hip` rides the pelvis BONE and carries the curve base CV
   and the mid blend, so the spine base tracks the hips wherever their
   motion comes from; the zero groups follow the ROOT bone, so the chest
   stays planted while the hips sway and root motion carries everything.
   The switch lifts the pelvis controller back out (containment adds it to
   the riders past the attach-bone filter) and re-hangs it on the root
   controller.
2. **The top control drives spine_04, one bone below the chest tip.** The
   solver runs spine_01→spine_04; spine_05 rides above with its own local
   keys (they are not cut). Dependent chains (neck, clavicles) hang on a
   hidden `IKSpine_chest` follower riding the spine_05 BONE, so its local
   animation keeps carrying them; the visible top control stays the
   picker's `end` role.

**The bug v3 exposed — path-based manifest diffs.** `apply_Parent_in`
re-parents existing nodes, and a re-parented node's new long path read as a
freshly created node: the spine manifest swallowed the pelvis controller
and both FK legs, and tearing the spine down deleted them. The manifest
diff now runs on UUIDs (`builder._scene_nodes` returns UUIDs,
`_fresh_paths` maps the new ones back to paths) — a UUID survives any
re-parenting. This also stopped chains from re-recording their own
subtrees on every coupling.

## Notes

- Without a pelvis controller in the scene the bottom node simply has no
  passenger (bare-skeleton builds); every real flow builds the pelvis FK
  chain first.
- Stretch (curve longer than the chain) is not built; the solver just runs
  out, matching the no-stretch limbs.
- Switching a limb to FK while the spine is IK still couples to nothing
  (noted in the status line), unchanged from v1.
