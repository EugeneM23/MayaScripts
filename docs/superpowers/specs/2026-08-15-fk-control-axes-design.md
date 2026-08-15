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

The knots are joints, so the alignment has a natural home in their static
orientation attributes. Two facts, both measured on the live rig, make it a
purely local edit:

- a joint's world rotation is `rotateAxis · rotate · jointOrient · parent`;
- the rotation offset `C` between a knot and the bone it drives is constant over
  time (deviation 1e-14 across frames).

So, per controller: `rotateAxis` takes `C⁻¹`, `jointOrient` takes the total
local rotation the controller holds at the build pose, and every rotate key
becomes `C · T(t) · T(ref)⁻¹ · C⁻¹`. The product `rotateAxis · rotate ·
jointOrient` is then algebraically unchanged, which is the whole safety
argument: no world transform moves, no constraint is touched, no node is
created or deleted. Working from that whole product rather than the rotate
channel alone also makes a second pass a no-op.

**Ordering is irrelevant**, because every input is read from world transforms
the operation provably leaves alone. An earlier draft of this spec called for a
root-down walk; that was written for a formulation that moved world transforms,
and it is not needed here.

Two scene details the implementation must respect: OverRig **locks
`jointOrient`** on its knots, so it is unlocked and re-locked around the write,
and the two attributes must be written together — a `rotateAxis` without its
`jointOrient` moves the bone. The `root` controller is skipped: built by
`apply_parentConstrAnim` as a plain transform, it has no `jointOrient` to carry
the change, and as a lone centre control it has no mirror partner.

The step runs once at the end of `build_fk`, after every chain is built and
coupled. Chain coupling (`apply_Parent_in`) and ring dressing are untouched.

## Verification

Unit tests cover the pure parts: the convention as sign triples, the
frame-alignment maths, and the root-down ordering.

The real proof is in the scene, and the acceptance tests are the same
measurements that exposed the problem:

- **Zero drift.** Every bone's world matrix, at every frame, is unchanged by the
  alignment step. This is the gate — a mirror that costs the animation is worth
  nothing. *Measured: 2.8e-07 across 31 frames and 64 bones.*
- **Symmetric values.** Setting both sides to the same channel values produces a
  mirrored pose. *Measured: 0.0004.* Every controller reads zero at the build
  pose.
- **Animbot.** Pose the left arm, select both arms, run Animbot's mirror, and
  the right arm's joints land within tolerance of the mirror of where the left
  arm's joints were. The scripted entry point is
  `CORE.mirror.mirrorAllKeys_click()` — reached through `animBot._api.core`, not
  through the tool button, whose `click()` never arrives.

A check that was specified and then **retired**: comparing the rest frames of
each left/right pair and demanding `(-1, -1, -1)`. The algebra says it cannot
happen. The rest frame is `rotateAxis · jointOrient · parent`, and requiring the
controller to read zero at the build pose forces `rotateAxis · jointOrient` to
be exactly what it held there — so the rest frame stays the knot's own frame.
Symmetric values and bone-convention rest frames are not both reachable through
`rotateAxis` and `jointOrient`: the first needs `rotateAxis = C⁻¹`, and then the
rest frame carries `C⁻¹` whatever `jointOrient` does. Symmetric values are the
half that animators actually use, so that is the half this design keeps.

## Risks

- **Re-baking is where this can go wrong.** Every past bug in this project that
  survived a green test run was a scene bug. The drift check runs against the
  bones, across the whole timeline, not against the controllers.
- **A half-written controller moves its bone.** `rotateAxis` and `jointOrient`
  only make sense as a pair, and OverRig locks the second one. Unlock first, so
  a refused write cannot leave the first one applied on its own.
- **Animbot caches what it learns per controller.** Settings taught by an
  earlier experiment can outlive it. If a mirror behaves inconsistently between
  runs, `Clear Mirror Settings Data` is the reset, and verification should start
  from it.
- **Animbot may still need teaching.** It picks its channel signs by guessing at
  the rig, and the rest frames it reads are the knots' — which this design
  cannot change. `Snapshot Mirror Settings` is its own answer to that, and it is
  a button the user presses: called from a command port it puts up a modal
  dialog and blocks Maya.
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
