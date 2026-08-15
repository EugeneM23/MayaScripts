# Symmetric FK control axes — mirroring that Animbot understands

Date: 2026-08-15
Status: proposed
Branch: `feature/overrig-picker`
Follows: `2026-08-15-fk-knots-design.md`

## Goal

Left and right FK controllers should behave as mirror images: a mirrored pose
is expressed by the same channel values on both sides, and Animbot's mirror
tools — which the user already has installed and uses on other rigs — produce a
geometrically correct mirror on our controllers with no per-rig setup.

## The problem, measured

Three things were measured in the user's live scene rather than assumed.

**The skeleton is already consistent.** Every left/right bone pair is related by
the classic behaviour mirror: reflect the left frame across the character's
plane of symmetry, then negate all three axes. Written as sign triples on
`mirror(left_axis) · right_axis`, every pair reads `(-1, -1, -1)`. The practical
consequence is that in a symmetric pose the two sides carry *identical* rotate
values — verified on `upperarm`, `lowerarm`, `hand`, `calf`, `foot`, `ball`.
(`thigh` and `clavicle` show a 180° offset in Z; that offset lives in the
skeleton's bind pose, not in its frames, and controllers that zero at build time
never see it.)

**Our controllers are not.** OverRig's `apply_ForwHierarhy` orients its knots by
its own rule, and every FK controller pair comes out as `(+1, -1, +1)` instead —
a self-consistent convention, but a different one from the skeleton's, and one
that no tool expects.

**Animbot's mirror is wrong on our controllers today.** With the left arm posed
and both arms selected, Animbot's mirror puts the right hand 127 units away from
where a mirror would put it — the arm crosses to the other side of the body.
Animbot applied the channel pattern `(+rx, -ry, -rz)`; the geometry of our
frames requires `(-rx, +ry, -rz)`.

Two supporting findings shaped the design:

- **Animbot pairs our controllers correctly already.** `Select Opposite` finds
  `upperarm_r_FK_ctrl` from `upperarm_l_FK_ctrl` on names alone. Nothing needs
  to change about naming, and no pairing snapshot is required.
- **Animbot handles most conventions, but not ours.** Four rest-frame
  conventions were built as isolated control pairs and mirrored. Of the three
  that produce a right-handed frame, `behaviour (-1,-1,-1)` and
  `conjugate (-1,+1,+1)` mirror *exactly* (error 0.0000), while our current
  `(+1,-1,+1)` is off by 3.12. Our convention is the one broken case.

## Decision

| Decision | Choice | Rationale |
|---|---|---|
| Target convention | Each controller's rest frame equals its bone's frame | Puts controllers on the skeleton's behaviour mirror, measured exact under Animbot's mirror |
| Scope of alignment | All 17 chains, both sides and the centre | One rule for the whole body; a side-only rule would be two rules and a permanent source of confusion |
| When | At build time, inside `Build FK` | The rig is rebuilt from the skeleton anyway; patching a live rig means rebuilding every coupling constraint's offset |
| Animation | Preserved exactly, re-baked into the new frames | The same requirement every other operation in this tool already meets |
| Ring geometry | Unchanged | Ring planes are derived from the knot's own axes at dress time and follow the new frames automatically |

Aligning to the bones buys a second thing for free: controller values become the
values the animator sees on the skeleton in Unreal, so a pose read off one reads
off the other.

## What changes

`Build FK` gains one step, between building a chain's knots and coupling the
chains together: **align each fresh knot's rest frame to the bone it drives.**

The knots are joints with `jointOrient` and `rotateAxis` at zero, so the
alignment has a natural home — the orientation moves into `jointOrient`, and the
animation moves with it:

1. Walk the chain root-down. A parent's realignment changes every descendant's
   world frame, so parents must settle before their children are measured.
2. For each knot, record its world matrix at every keyed frame. That matrix is
   what drives the bone; preserving it preserves the animation exactly.
3. Set `jointOrient` so that with `rotate` at zero the knot's world orientation
   equals its bone's world orientation.
4. Recompute `rotate` at every recorded frame to reproduce the recorded world
   matrix under the new rest frame.

Chain coupling (`apply_Parent_in`) and ring dressing then run as they do today.

## Verification

Unit tests cover the pure parts: the convention as sign triples, the
frame-alignment maths, and the root-down ordering.

The real proof is in the scene, and the acceptance tests are the same
measurements that exposed the problem:

- **Zero drift.** Every bone's world matrix, at every frame, is unchanged by the
  alignment step. This is the gate — a mirror that costs the animation is worth
  nothing.
- **Symmetric values.** In the build pose, left and right controllers carry
  equal rotate values.
- **Frames.** Every left/right controller pair measures `(-1, -1, -1)`, matching
  the bones.
- **Animbot.** Pose the left arm, select both arms, run Animbot's mirror, and
  the right arm's joints land within tolerance of the mirror of where the left
  arm's joints were. The scripted entry point is
  `CORE.mirror.mirrorAllKeys_click()` — reached through `animBot._api.core`, not
  through the tool button, whose `click()` never arrives.

## Risks

- **Re-baking is where this can go wrong.** Every past bug in this project that
  survived a green test run was a scene bug. The drift check runs against the
  bones, across the whole timeline, not against the controllers.
- **Ordering.** Realigning a parent invalidates a child's measurement. Root-down
  order is a correctness requirement, not a preference, and gets its own test.
- **Animbot caches what it learns per controller.** Settings taught by an
  earlier experiment can outlive it. If a mirror behaves inconsistently between
  runs, `Clear Mirror Settings Data` is the reset, and verification should start
  from it.
- **The build pose is still whatever the skeleton stands in.** Unchanged by this
  work, and still worth the snapshot safety proposed earlier.

## Out of scope

- Translation channels. Our FK controllers rotate only.
- IK controls; spine and neck mirroring beyond what falls out of the general
  rule.
- A mirror button of our own. Animbot already has one, and the point of this
  work is that it starts working.
- Teaching Animbot through its own `Snapshot Mirror Settings`. It is the
  fallback if the alignment alone proves insufficient, not the plan.
