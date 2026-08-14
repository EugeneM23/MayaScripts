# Build FK v2 — real controllers through OverRig knots

Date: 2026-08-15
Status: approved
Branch: `feature/overrig-picker`
Replaces the inert markers of: `2026-08-15-fk-controllers-design.md`

## Context

The v1 FK button made inert rings — good to look at, driving nothing. The user
wants the controllers to sit **on top of existing animation**: select a ring,
adjust, and the bone follows, without losing the motion already on the bones.

That is exactly what an OverRig knot does: it bakes the object's current motion
onto a new node across the timeline, then constrains the object to that node.
Building FK through knots also drops the controllers into the same bookkeeping
our bake/teardown machinery already handles — `OverRig_knots`, reclaim, nested
ordering — instead of inventing a parallel constraint system that our own
reclaim would refuse to touch (it deliberately spares constraints OverRig did
not make).

Verified live before designing:

- `apply_parentConstrAnim(1)` on one joint: knot locator at world, animation
  transferred, joint constrained; rotating the knot moves the joint. ~18 nodes.
- `apply_ForwHierarhy(1)` on `spine_01..03`: three knot **joints** parented as a
  chain (`joint1 → joint2 → joint3`), animation transferred, bones constrained.
  Rotating the first knot moved `spine_03` by 7.17 cm — **real FK inside the
  chain**. ~30 nodes per bone.
- Our reclaim + closure removed both builds completely; the scene returned to
  its baseline node count.

## Scope

**In**

- 17 chains covering the same 64 animator bones as the picker
- Real FK within each chain via `apply_ForwHierarhy`; `root` gets a single knot
  via `apply_parentConstrAnim`
- Knots renamed to `<bone>_FK_ctrl`; our sized, coloured rings attached as
  **shapes on the knots themselves**, native knot shapes hidden — clicking a
  ring selects the control, not a proxy
- Existing animation transferred to the knots (the knot's own property)
- Manifest in `RigPicker_fk` by whole-scene diff per chain
- `Bake+Delete` with FK present bakes the whole FK back and removes it
- Pressing `Build FK` again = full bake + rebuild, one undo chunk

**Out**

- FK and IK coexisting on the same skeleton (guarded, see below)
- Per-chain FK bake — v1 treats FK as one unit
- The v1 inert-marker mode is gone; this button replaces it

## Revision, same day: coupling, root ring, machinery

Three corrections after the user drove the first build.

**Chains are coupled after all.** Independence was the original choice; in
practice moving the pelvis tore the skeleton apart at every chain boundary, so
the user reversed it. After every chain is built, each chain-root controller is
hung off its parent bone's controller with OverRig's `apply_Parent_in`
(selection: child first, parent last — established by experiment). The child
knot becomes a DAG child of the parent knot and its animation is **re-baked
into the new local space**: verified zero drift at every frame, which is why
this is done with OverRig's proc and not a bare `parent` — a bare re-parent
preserves only the current frame. The attach target is derived from the
skeleton: the chain's first bone walks up to the nearest ancestor carrying a
controller (`clavicle_l → spine_05`, `thigh_l → pelvis`, metacarpals and thumbs
→ the hand, `pelvis → root`). 16 couplings; `root` stays in world.

**The root ring lies flat** whatever the knot's own axes are: the circle normal
is world-up transformed into the knot's local space, not a guessed axis.

**All rig machinery is hidden.** ForwHierarhy's internal locators and helper
joints (driver locators, attach locators) drowned the rings in cyan crosses.
Every recorded locator shape is hidden and every recorded joint set to
`drawStyle` none — display-only, nothing is disconnected.

## Chains

`root` alone; spine `pelvis + spine_01..05`; neck `neck_01, neck_02, head`;
arms `clavicle, upperarm, lowerarm, hand` ×2; legs `thigh, calf, foot, ball` ×2;
ten finger chains (four metacarpal fingers + thumb, per hand). Together exactly
the 64 body-map joints, enforced by a test.

## Build flow

1. Refuse if the IK build exists ("bake the IK limbs first") — two drivers on
   one bone is the interaction explicitly deferred. Symmetrically, `Build`
   (IK) refuses while FK exists. Both guards live in the window layer, since
   `fkcontrols` imports `builder` and a guard inside `builder` would be a cycle.
2. If FK exists, bake it back first (same undo chunk).
3. Compute all ring radii up front with the existing machinery — skin buckets,
   correction table, stagger — into one `{joint: radius}` map.
4. Per chain: select the chain's resolvable joints in order; run the OverRig
   proc; diff the scene for new nodes (minus animCurves — bake output on the
   bones must outlive the rig, knot curves die with their knots).
5. Map each new knot to its bone **through its constraint targets**, never by
   name — OverRig names them `joint1..N` and suffixes on collision. Capture
   UUIDs first and re-resolve paths after each rename, since renaming a chain
   parent changes every descendant's path.
6. Rename to `<bone>_FK_ctrl`, parent the ring's shape onto the knot
   (`parent -shape -relative`), delete the ring's empty transform, hide the
   knot's native shape (`drawStyle 2` for joint knots, shape visibility for
   locator knots). Transforms stay **unlocked** — these are real controls now.
7. Record the diff in `RigPicker_fk`.

## Teardown (`bake_fk`)

Fast-bake all 64 source joints, strip constraint attributes, delete manifest
members and the set, then run the existing reclaim over the joints as a safety
net for anything the diff missed. One undo chunk.

`Bake+Delete` checks `has_fk()` first: FK present → whole-FK bake; otherwise the
existing per-limb IK path.

## Testing

Pure: the chains cover the 64 body-map joints exactly once; existing radius,
correction and stagger tests unchanged.

Live: 64 controls exist as knots with ring shapes; a bone with prior animation
keeps its motion (knot carries curves); rotating the pelvis control moves
`spine_05`'s bone (chain FK works); `Build FK` refuses while IK is built and
vice versa; rebuild does not grow the node count; `Bake+Delete` returns the
animation to the bones and the scene to its baseline.
