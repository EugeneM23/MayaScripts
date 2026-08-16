# Controllers that stand in their bone's axes

Date: 2026-08-16
Status: accepted
Branch: `feature/overrig-picker`
Follows: `2026-08-15-fk-control-axes-design.md`

## Goal

Selecting an FK controller and turning it should feel like turning the bone.
The animator's report is about fingers — "the controls are created with axes
that do not match the bones' axes, and I want them to match so I can rotate the
fingers correctly" — but the cause is general and the fix is general.

## The problem, measured

Built on the live Manny scene with the default (hybrid) Build, then measured per
controller: `dC`, the angle between the controller's own world frame and its
bone's, and `chan`, the angle between the frame the rotate channels act in
(`jointOrient · parentWorld`) and the bone's frame.

| controllers | `dC` | `chan` |
|---|---|---|
| left-hand fingers (14) | 85.1° – 97.1° | 0.000° |
| right-hand fingers (14) | 171.5° – 180.0° | 0.000° |
| spine, neck (8) | 90.0° – 90.6° | 0.000° |
| `root`, `pelvis` | 0.000° | 90.0°, 90.1° |

Two separate facts hide behind one complaint.

**`chan` is already zero.** The alignment step from the previous design does
work: typing `rotateZ` on a finger controller turns the bone about the bone's
own Z, and the controller reads zero at the build pose. That half is not broken
and this design does not touch it.

**`dC` is not.** Every knot stands rolled about 90° about its bone (about 180°
on the right hand, where OverRig's convention flips as well). `rotateAxis`
carries exactly that roll — measured `(85.7, -2.3, 0.4)` on
`index_metacarpal_l`, `(90.0, 0, 0)` on the spine, `(94.3, 2.3, -179.6)` on
`index_metacarpal_r`. What an animator sees is the controller's own frame: the
rotate manipulator in its default Local mode, the local-rotation-axes display,
and the direction a dragged handle turns. All of them are 90° off from the
finger. Typing numbers works; grabbing the manipulator does not.

That is not an accident of the build — it is what the previous design chose.
Its closing section retires exactly this check, on the grounds that the rest
frame `rotateAxis · jointOrient · parent` cannot be the bone's frame while
`rotateAxis` is pinned to `C⁻¹`. That reasoning is sound as far as it goes, and
its conclusion — the two goals are not both reachable — holds only while the
knot is forbidden to move. Let the knot turn in place, and both are reachable.

`root` and `pelvis` are the mirror image of the same story and are discussed
under *Out of scope*.

## Decision

| Decision | Choice | Rationale |
|---|---|---|
| What changes | The knot turns in place onto its bone's frame | The only way to move the frame the manipulator reads |
| Who pays for it | The knot's DAG children are counter-rotated | Keeps the driver locator — and therefore the bone — exactly where it was |
| Scope | Every joint-type FK controller, all 17 chains | One rule for the whole body; fingers are not a special case, they are where it was noticed |
| Animation | Untouched, not even re-baked | The rotate curves are not part of this operation |
| When | At build time, after the existing alignment | Same undo chunk, same rebuild-from-skeleton assumption |
| `root`, `pelvis` | Left alone | Their frames already match their bones; their channels need a structural change, see below |

## What changes

`Build` gains one step after `align_controllers`: **turn each knot onto its
bone's frame.**

Per controller, with `C = B · W⁻¹` the constant knot-to-bone offset:

- the knot's `rotateAxis` becomes `C · rotateAxis`;
- every DAG child's local rotation is right-multiplied by `C⁻¹`, **and its
  local translation is turned by `C⁻¹` as well**.

The knot's world rotation becomes `C · W = B` — the controller now stands in the
bone's frame. Every child's world matrix is unchanged by construction, and the
driver locator is a child, so the bone does not move. `rotate` and `jointOrient`
are not written on the knot, so the animation and the channel behaviour the
previous design established are carried through untouched.

The translation half is the one that is easy to miss, and missing it is not
subtle: a child sits at an offset from its knot, so a 90° turn swings it to a
different place entirely. Correcting only the rotations left every child facing
the right way in the wrong position and moved bones by **21 cm** in the first
live run. Local translation is applied after the local rotation, so the offset
takes the same inverse turn — `R·T·C⁻¹` is `(R·C⁻¹)·T(t·C⁻¹)`.

After the alignment has run, `rotateAxis` holds `C⁻¹`, so the new `rotateAxis`
is `C · C⁻¹` = zero. The controllers end up with **no `rotateAxis` at all** —
the clean state a hand-built control would have — but the step is written
against the measured `C` rather than against that assumption, which makes it
correct on a controller that was never aligned and **idempotent**: run it twice
and the second pass measures `C` = identity and writes nothing.

Compensating a child depends on what the child is:

- **a child knot** (a joint): `jointOrient` takes the correction. Its rotate
  curves and its own `rotateAxis` are untouched; OverRig locks `jointOrient`,
  so it is unlocked and re-locked around the write.
- **the driver locator** (a plain transform, `rotateAxis` zero): the correction
  goes into `rotate`, which is connected to animation curves — OverRig bakes
  everything. The curves are constant by construction (the locator rides the
  bone rigidly and both the constraint offset and `C` are constant; measured
  spread 0.000000 over 62 keys), so a constant curve is rewritten with one
  call per channel and a varying one key by key, nearest-solution so no key
  can flip by 360°.
- **the leftover `aimConstraint` nodes** OverRig parks under each knot are
  skipped: they have no live output (measured — their only connections are to
  the manifest set and to themselves), and a constraint node does not use its
  own transform.

A child whose rotation cannot be written — locked, or driven by something that
is not an animation curve — makes the whole controller skip, before anything is
written. Half a correction moves the bone.

## Verification

Unit tests cover the algebra: the knot lands on the bone's frame, a child's
world is unchanged, a second pass is a no-op, and the composite property over a
two-knot chain where the child is both corrected and compensated.

The proof is in the scene — `docs/superpowers/plans/verify_control_axes.py`,
which builds the rig itself in two halves so the step can be measured on its
own: once with the turn suppressed (the rig as it shipped), then for real.
**All green, measured on the live Manny scene:**

| Gate | Result |
|---|---|
| Bones do not move — 64 bones × 60 frames | worst **4.9e-07** |
| Controller frames on their bones | **180.000° → 0.00002°** |
| `rotateAxis` is gone | worst **0.000000** |
| Channels still in the bone's axes | worst **0.00002°** |
| Controllers still read zero at the build pose | worst **0.00000** |
| A finger turns about the axis you grab | **85.19° → 0.000°**, swing 30.00 for a 30 poked |
| Rest frames mirror as the bones do | **19/19**, all `(-1, -1, -1)` |
| Equal values on a pair give a mirrored pose | **0.0000 cm** |

The mirror row is the check the previous design retired as unreachable. It
becomes reachable here, which is what should finally let Animbot's mirror read
our controllers without being taught.

`verify_arm_switch.py` re-run against the change: green end to end, including
the finger-tear and torso-survival checks.

## Risks

- **The bone is driven through the child that gets counter-rotated.** If the
  compensation is wrong, the whole character shifts, visibly — which is exactly
  what the missing translation half did. The drift check runs against bones
  across the timeline, not against controllers, which is why it caught it.
- **A locator curve that is not constant** would make a single-value rewrite
  wrong. The implementation measures rather than assumes, and falls back to
  per-key.
- **Ring shapes turn with the knot.** They are circles drawn in the plane
  perpendicular to the knot's local X, and `C` is nearly a roll about that same
  X, so a circle maps onto itself; what shift remains puts the ring
  perpendicular to the bone, which is what the ring was always meant to be.
- **Animbot caches per controller.** A stale guess from an earlier rig can
  outlive it; `Clear Mirror Settings Data` is the reset if a mirror looks
  inconsistent between runs.

## Out of scope

- **`root` and `pelvis`.** Built by `apply_parentConstrAnim` as plain
  transforms, they have no `jointOrient`. Their frames already match their
  bones (`dC` 0.000) — the animator's request is already satisfied there — but
  their rotate channels act in a frame 90° away, and `pelvis` reads
  `(-270, -93.6, 270)` at the build pose. A transform carries only
  `rotateAxis · rotate`, and the algebra says no assignment of those two gives
  both a zero rest pose and channels in the bone's axes: it needs an offset
  group above the control, which is a structural change to what the root
  controller is — and the root controller is what every IK limb hangs on.
  Worth doing, deliberately not done here.
- IK controls. They are OverRig's own, with their own conventions.
- Translation channels. Our FK controllers rotate only.
