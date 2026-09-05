# Retarget from a Mixamo skeleton — design and record

**Date:** 2026-09-05. **Ask:** «Нужно улучшить наш скрипт который делает
ретаргет. В открытой сцене у нас есть скелет который я взял с миксамо на
скелете анимация. Давай сделаем так чтобы наш скрипт делал ретаргет и для
миксамовского скелета».

Companion: `2026-09-04-as-retarget-design.md`, which built the retarget for a
UE5 twin of the rig's own skeleton. That one could assume the source was the
same skeleton in the same bind pose; this one cannot, and everything below
follows from that.

Proof: `docs/superpowers/plans/verify_asretarget_mixamo.py` — **green live
2026-09-05, 0 of 18 gates failed** on the animator's own clip, and the twin's
`verify_asretarget.py` re-run **green, 0 of 26**, so the UE5 path is unchanged.
77 unit tests.

## What is in the animator's scene

`Manny_rig_02.ma`: the AdvancedSkeleton rig on the UE5 Manny, and a Mixamo
skeleton — **65 joints under `mixamorig:Hips`, 52 of them animated, 12084 keys
over frames 0..75**. Measured differences from a twin source, every one of
which the design has to answer:

| | our rig | the Mixamo source |
|---|---|---|
| names | `upperarm_l`, `spine_01..05`, `neck_01/02` | `LeftArm`, `Spine/Spine1/Spine2`, `Neck` |
| side | a suffix (`_l`) | a **prefix** (`Left`) |
| bone axis | local **X** down the bone (and −X on `upperarm_r`, `lowerarm_r`, `thigh_l`, `calf_l`) | local **Y**, every bone |
| bind pose | in the joints' **rotate** channels | in their **jointOrient** |
| rest pose | **A-pose** | **T-pose** (measured: arm along +X to 0.000, 47.23 cm out, 0.00 cm up) |
| spine | 5 joints | 3 |
| neck | 2 | 1 |
| fingers | metacarpal + 3 phalanges | 3 phalanges + an end joint |
| root motion | a `root` bone | none: the travel is in the hips |
| arm length | 55.02 cm | 47.23 cm (**the rig is +16.5%**) |
| leg length | 85.57 cm | 87.86 cm (**the rig is −2.6%**) |

## The core: align the rest poses, bone by bone

A rigid rest offset — `orientConstraint -mo`, or the twin design's
`C_rest · S_rest⁻¹` — preserves the source's motion **relative to its own
rest**. Fed a T-posed source it hands an A-posed rig arms that are 54.83° too
low for the whole clip. That is the classic broken retarget, and the number is
exactly the rest-pose difference.

So the offset is built against a **reference pose**, not against our bind:

```
R_align   = the minimal rotation taking OUR rest bone direction
            onto the SOURCE's rest bone direction
C_ref     = C_rest · R_align            (row vectors: a world rotation post-multiplies)
O         = C_ref · S_rest⁻¹
target(t) = O · S_now(t)
```

At the source's rest the control stands at `C_ref` — our bone pointing where
the source's rest bone points — and from there it follows rigidly. The
consequence is the property worth stating, because it is what "correct" means
here and it is what gate 11 measures: **our bone POINTS exactly where the
source's bone points, at every frame.** Measured on the animator's clip over
six samples and 18 bones: **worst 0.028°**.

The proof is one line of algebra: our direction is
`d_ours(t) = X_ours · C_ref · S_rest⁻¹ · S_now(t)`, and `X_ours · C_ref` is by
construction the source's rest direction `Y_src · S_rest`, so
`d_ours(t) = Y_src · S_now(t) = d_src(t)`.

**The minimal rotation is the honest choice.** Two skeletons agree on where a
bone points at rest and say nothing about the roll around it; the minimal
rotation changes nothing else, so our rig keeps the roll its own axis work
established (`2026-09-04-advancedskeleton-ue5-rig-design.md`). The source's own
roll about a bone then maps to ours about the same axis, which is why the
different axis conventions (our X, Mixamo's Y) need no handling at all: the
whole thing is done in world space.

**A bone needs a child to point at, and it must be a child BOTH skeletons
map.** So the hand aims at the middle finger (Mixamo has no metacarpal, so
`hand_l ↔ LeftHand` reaches down to `middle_01_l ↔ LeftHandMiddle1`), and the
head, the toes and the finger tips — which have no mapped child at all —
**inherit their parent's alignment**. `alignments()` walks root-down so a
parent's answer is ready when its child asks.

**The nearest mapped child is the WRONG one for a hand, and it cost a measured
30.77°.** A hand's nearest mapped descendant is the **thumb** — the one finger
that does not continue the hand — and taking its direction rolled the wrist by
that much for the whole clip. `DIRECTION_CHILD` names the two exceptions
(`hand_l → middle_01_l`, `hand_r → middle_01_r`); everything else takes the
nearest, which the numbers vindicate: every other bone measured ≤ 0.028°.

## Where the source's rest pose comes from

A retarget rests entirely on the source's rest, and it is **not observable at
any frame of an animated clip**. So the schema declares it:

- **`rest="jointOrient"`** (Mixamo): the bind is in the joints' `jointOrient`,
  so the rest is the pose with every `rotate` at 0, walked down the hierarchy
  (`rest_matrices`). Measured on the animator's clip: that pose is an exact
  T-pose — arm direction (1.000, 0.000, 0.000), 47.23 cm out and 0.00 cm up.
- **`rest="live"`** (a UE5 twin): the source stands in the same bind pose as our
  rig, so what the scene shows IS the rest.

**Our own rig must never be read the jointOrient way**, and the probe that tried
it is the record of why: this skeleton's bind lives in its **rotate** channels
(CLAUDE.md's own fact), so zeroing them straightened it and the computed "rest"
sat **76.25 cm** from the live one.

`connect` prints what the computed rest looks like — the arm's sideways and
vertical reach, and the height — because a wrong rest makes every number under
it wrong quietly.

## The rest of the schema

`Schema` is one namedtuple and a third skeleton is a row in `SCHEMAS`, not a
branch anywhere:

- **names and sides**: `rows` plus `sides`, and `side_before` for Mixamo's
  prefix. `bone_name` is the only place a source name is spelled.
- **the spine, 3 against 5**: `Spine1←Spine`, `Spine3←Spine1`, `Spine5←Spine2`.
  Our `spine_02`/`spine_04` stay at rest; the three driven ones take the
  source's absolute orientations, so the driven spans match exactly (measured
  0.000°) and the two gaps keep their rest relationship. Gate 11 measures the
  DRIVEN spans for exactly that reason — its first version measured
  `spine_01 → spine_02`, half of which nothing drives, and read 1.787°.
- **the neck, 1 against 2**: `Neck←Neck` and `Head←Head`, with `NeckPart1`
  deliberately undriven. The rig's neck in-between then distributes the bend
  across both neck joints by itself and the head control lands the head
  absolutely — the in-between doing the job it was built for instead of
  fighting a second driver.
- **no metacarpals**: those four controls per hand are simply not in the table.
  A schema's own gaps are not "missing bones" and are not reported as such.
- **`twin`** (named `keep_position` until 2026-09-05, when the field turned out
  to decide two things that are one fact): a twin keeps its sub-millimetre rest
  offset on position drives, and — since the same day — its FK controls are
  driven in position as well, because a clip can animate a bone's translation
  and only a twin's positions are ours to reproduce (the twin spec's Addendum
  2). A foreign source gets neither: its rest hand is 40 cm from where ours
  rests, so its position drives go straight to the source's bone, and its FK
  controls stay rotation-only — placing them on Mixamo's joints would hand the
  rig Mixamo's proportions. A **pole** keeps its offset in both cases: the 85 cm
  standoff from its bone IS the control.
- **`root_bone=None`**: Mixamo has no root bone, so `Main` takes the source
  hips' **horizontal travel** (`pointConstraint`, `skip=["y"]`) and nothing
  else. Translation is unambiguous — the hips' ground travel IS the character's
  travel — while a yaw would have to be invented, and the pelvis is constrained
  absolutely so it absorbs whatever `Main` does: the pose is untouched either
  way. Measured on the clip: `Main` travels x −10.85, y 0.00, z −59.73.

## Proportions: nothing is scaled, both modes are driven

The rig's arm is 16.5% longer than the source's and its leg 2.6% shorter, and
that cannot be fixed by a rotation copy. Both promises are kept and named
rather than one being chosen:

- **in FK** the rig copies the source's ANGLES and keeps its own proportions —
  measured, every bone points where the source's does (0.028°), and our hand
  therefore sits **8.29 cm** from the source's;
- **in IK** the hand and foot land on the source's own positions — measured
  **0.0003 cm** and **0.0094 cm** — and the elbow bends more to get there.

`proportion_note` says exactly that in the status line, with the measured
percentages. A weighted point constraint would have let the IK reach be scaled
about the pelvis, and **Maya refuses a negative target weight** ("Cannot set
the attribute below its min"), which is what a 1.165 ratio needs; the matrix
network that would work is not built, because the two modes above already
cover what an animator wants.

**Each promise is measured in the mode that makes it** (gates 11 and 12). The
first version of gate 11 measured the FK promise with the legs in IK and read
6–20° — the IK solver reaching the source's foot with our shorter leg, which is
the OTHER promise working. That also exposed a real bug in the verify script's
teardown: `asGoToBuildPose` writes the FKIKBlend values the rig was BUILT with,
so restoring the animator's blends before it hands them back a rig in the wrong
mode. Restore them after.

## What the constraint offset saved

Measured 2026-09-05: an `orientConstraint`'s own `offset` holds
`W_target = O · W_source` — trap 19's convention, worst element **0.000000000**
— which is exactly the shape of our rest offset. So a **rotation-only** drive
needs no helper node at all: 53 of the 62 Mixamo drives are one constraint
each, and only the 9 position drives get the two-node helper. Without that the
Mixamo case would have added ~140 transforms and doubled the vendor bake's
work, since AS bakes every object its constraints drive.

The euler is written in the CONTROL's own rotate order (`euler_offset`); a unit
test round-trips all six orders, because `FKWrist_L` is `zyx` and the rig uses
four different orders.

## Verification

`verify_asretarget_mixamo.py` builds **no fixture** — the source is the
animator's own Mixamo skeleton, read-only — and runs the animator's whole loop:
detect, refuse, report, connect, measure, AdvancedSkeleton's own **Bake**, its
**Disconnect**, and the rig back at its bind pose. Measured: the bake keyed 63
controls, Disconnect left nothing of ours, **the baked rig held the pose to
0.000000 cm** with the constraints gone, no pairBlend was spliced anywhere
(trap 37's signature never appears), and the bind pose came back to
**0.000000000**.

Its two gate lessons are the project's own in miniature: an expectation must be
computed from the scene rather than guessed (gate 6 asserted 60 drives against
the real 62), and a gate must measure its promise in the mode that makes it
(gate 11, above).

## Deliberately not done

- **No scaled IK reach.** Negative point-constraint weights are refused and the
  matrix network is unbuilt; the FK/IK split above is the answer instead.
- **No invented yaw for `Main`.** The travel is unambiguous, the facing is not.
- **No third schema.** `SCHEMAS` is where one goes — rows, sides, a rest mode
  and five hint bones — and `detect_schema` refuses anything it cannot name
  rather than guessing at it.
- **No re-timing.** The clip is 30 fps in a 30 fps scene here; a mismatch is the
  UE bridge's business, not the retarget's.
