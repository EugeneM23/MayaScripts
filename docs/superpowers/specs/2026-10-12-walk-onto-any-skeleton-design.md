# Parametric walk onto any skeleton (2026-10-12, the second step)

The animator, after the first version (a copy of the cycle beside it): «Давай сделаем так что бы я выделил
любой скелет и моя походка применилась к нему и дальше я мог ее настраивать». Asked, and answered:
the walk goes **onto the selected skeleton itself** (its keys replaced, one Ctrl+Z, the knobs remembered on
it); a walk is **saved to a file** and applied in any scene; the targets are **any skeleton** the plugin
recognises (rigs refused in this version); the copy mode goes. Built on
`2026-10-12-parametric-walk-design.md` (the model, unchanged).

## What happens

**Save walk** (a bone of a walk cycle selected): the cycle is read as the model reads it (every joint's
world on every frame of its key range) plus, for each bone, its parent, its canonical name
(`maya_skeletonmap.recognize`, as the Pose Library reads a skeleton: `maya_poselib.scene.skeleton`) and its
REST, and written to `docs/superpowers/plans/walkparam/walks/<name>.walk.gz` (gzip JSON, format
`skeldar.walk` 1). The folder is the animator's data and git ignores it. The rest:

- a skinned skeleton rests at its bind (`scene.skeleton`'s rule);
- an UNSKINNED skeleton whose bones are Manny's (UE5 names, the median bone length within 1 % of the
  plugin's `assets/manny_skeleton_template.json`) rests at **Manny's bind from that template** - measured:
  `Walk_01`'s 93 bones are Manny's to 1.5e-6 cm (only the animated helpers and the root-pelvis offset
  differ), so it is Manny's walk and pairs with Manny's skeleton as a twin;
- any other unskinned skeleton rests as it stands, and the status line says so (rolls may differ).

The same rest rule reads a TARGET, so a cycle applied onto its own skeleton is a twin of itself.

**Apply** (any skeleton selected, a walk picked in the window's list): the walk is evaluated with the
window's knobs (`walkmodel.Walk.evaluate`) and carried onto the skeleton:

1. **the Pose Library's transfer, per frame** (`posemath.Transfer`): bones paired by leaf when both are
   UE-named, else by canonical name (spine and neck chain onto chain); each target bone takes its partner's
   rotation relative to its nearest paired ancestor, carried through the two rests (identity for a twin);
   the target keeps its own bone lengths; the pelvis takes the walk's offset from its root frame scaled by
   the size ratio (`scale_between`: pelvis height over the root, target over source); the root frame moves
   by the walk's travel (`travel`, scaled) from where the target stood - the target's PLACE (its root frame
   when the walk was first applied, stored, so re-tuning never drifts);
2. **the legs by IK in the target's own lengths**: each ankle's goal is the walk's ankle mapped exactly as
   the pelvis is (its offset from the source's root frame, scaled, in the target's root frame) - so a
   planted source foot is a planted target foot at any size; the knee bends toward the transferred knee;
   thigh and calf turned by the rotation taking the transferred (bone, leg plane) onto the solved one (roll
   kept); the foot keeps its transferred orientation;
3. **the pelvis drops per frame** where the target's legs cannot reach the goals without straightening past
   the walk's straightest (`walkmodel.smooth_cover` over each frame's need) - every bone under the pelvis
   rides the drop;
4. **the helpers** (`ik_foot_*`, `ik_hand_*`, `camera_*`, `interaction`, `center_of_mass`) that follow a
   body bone rigidly in the walk keep that relation on the target (its translation scaled);
5. every other bone keeps its own rest local on its (moved) parent.

The target is read at its REST (`world` = `rest` for every bone), so old animation on it changes nothing;
the transfer's place is the stored one. **Written**: rotate curves on every paired bone, the legs and the
helpers; translate curves on the root frame's bone (the root, or a rootless top joint), the pelvis and the
helpers; every other written bone's translate set static to its rest local (its old translate curves
deleted - a UE 3P clip's animated translations would otherwise stretch it); frames start..start+N (the
walk's own start); one undo chunk. The skeleton's top joint carries `skeldarWalk` = JSON {walk, knobs,
place, start, version 2}.

**The window**: the walk list + Save walk...; Apply to selection; Pick selection (a walked skeleton: its
walk and knobs into the window, it becomes the target); the knobs (a released slider re-applies onto the
current target); Reset; the status line (the walk, the target, the pairing count, the size ratio, the
drop, the time).

Refused, by name: a rig (`maya_rigs.rig_of`: "a rig - not in this version, select a skeleton"); a
skeleton with no pairable legs; a walk file of another format; no walk saved.

## Proof

- `tests/test_walkmodel.py`: the walk file round trip; the retarget on the synthetic walker - onto itself
  (identity), onto a copy scaled 0.7 (stride x0.7, stance feet still, bone lengths kept, the pelvis at
  0.7 height), the helpers on their bones.
- `verify_walk.py` (rewritten, mayapy standalone): Walk_01 imported (a temp copy) and saved; applied at
  defaults onto its own skeleton (= the cycle) and onto the plugin's Manny skeleton (a twin: every bone's
  world rotation equal, positions moved by the place); onto the Creep skeleton, the UE4 Mannequin, a Manny
  skeleton shrunk to 0.6 and the animator's Mixamo `Sweep Fall.fbx` skeleton when it is on the Desktop or in
  Downloads: stance feet still (no worse than the walk's own slide x the size), stride x the size, bone
  lengths unchanged, the seam; knobs re-tune the same skeleton from its stored place; Pick reads the knobs
  back; one Ctrl+Z; a rig refused.
