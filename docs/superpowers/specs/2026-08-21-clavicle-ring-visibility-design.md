# Clavicle ring visibility — design

**Date:** 2026-08-21
**Status:** designed.

## The ask

> «Только сейчас контролеры не видно из-за меша давай сдвинем их в сторону и
> сделаем больше по размеру что бы их хорошо было видно!»

The new clavicle controls work but cannot be seen: like every ring, theirs is
drawn centred on the knot pivot — the clavicle bone's ORIGIN — and that origin
sits 1.4 cm off the midline, inside the chest. Measured in the live scene
(2026-08-21): ring radius 9.02, centre at (1.43, 146.30, −1.74), while the
bone's far end (the shoulder, `upperarm_l`) is 17.8 cm away at
(18.44, 141.08, −2.54). The mesh near the shoulder rises to y=157.8. A 9 cm
ring buried mid-chest is invisible from everywhere.

Two asks in one: move the ring aside, and make it bigger.

## The design: draw the ring at the bone's far END

The repo's rings share one visual language — a band encircling the body part
the control drives. The clavicle's natural band is around the DELTOID: same
language, just at the other end of the bone. So:

- **`_AT_BONE_END`** — a new frozenset beside `_SQUARE`, listing bones whose
  ring is centred on the bone's far end (its first joint child) instead of
  its origin: `clavicle_l`, `clavicle_r`. The normal stays the bone axis
  (local X), so the circle encircles the shoulder; `cmds.circle` takes the
  centre directly. The end is computed, not assumed: the child joint's world
  position through the knot's inverse matrix — the knot stands ON the bone
  (parentConstrAnim), so this is very nearly `(bone length, 0, 0)`, but the
  knot's frame is OverRig's, not ours.
- **`_SCALE` gains the clavicles** (the table that exists exactly for
  user-driven size fixes): the skin-measured 9.0 is the spread around the
  clavicle AXIS; around the deltoid the meaningful comparison is the
  upperarm's measured 7.75, so the ring must beat that with a visible
  margin. Factor **1.4** → radius ≈ 12.6, standing ~4.9 proud of the deltoid
  all around — the proportion the other rings' margins give. (Chosen against
  the measurements above, confirmed by looking at an actual viewport
  capture; a number that "should be fine" was not acceptable after the
  first invisible ring.)
- A bone in `_AT_BONE_END` with no joint child keeps the origin centre —
  same as today, nothing to point at (the UE4-schema rig has upperarms, so
  this is a guard, not a path).

Why not a floating "halo" above the shoulder: any flat curve is edge-on from
some angle, and a band around a limb always shows some of itself — which is
why the existing rings read well. The band also lands where the animator's
eye already looks for the shoulder.

In full FK the upperarm's own ring (7.75, its origin at the same shoulder
point) sits inside the clavicle band (12.6, tilted 17° with the clavicle
axis) — same nesting the staggered spine rings already read as.

## What does not change

The knot, its pivot, the picker, selection, mirroring, alignment: the shape
is display only, and rotating the control still turns about the bone origin
— the ring sweeping with the shoulder is exactly the behaviour a clavicle
control shows in any rig. Old files re-dress on their next Build; nothing
migrates.

## Proof

Unit: `apply_size_rules` scales both clavicles; `at_bone_end` answers the
two clavicles and nothing else on the body map; the tables stay consistent
with CHAINS.

Live (`verify_hybrid_build.py` gains a gate): after the hybrid build the
clavicle ring shape's world bounding-box centre stands at the SHOULDER
(|x| > 10 where the knot pivot is at |x| ≈ 1.4) and its radius beats the
upperarm's measured size. Plus the honest check for a visibility complaint:
a viewport capture (playblast frame) actually looked at.
