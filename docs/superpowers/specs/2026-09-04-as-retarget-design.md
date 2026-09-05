# Retarget onto the AdvancedSkeleton rig — design

**Date:** 2026-09-04, the same evening as the rig itself. **Ask:** «Теперь давай
сделаем сетап для ретаргета. Суть такая: я импортирую в сцену анимацию с
аналогичного скелета, анимация автоматически перекидывается на кости а наш
ретаргет привязан к этим костям. Потом я сам иду в настройки андванцед скелетона
и делаю запекание. Твоя задача сделать сам ретаргет».

So the animator brings a clip in on a SECOND UE5 skeleton, our setup makes the
AdvancedSkeleton rig follow that skeleton, and the baking is a button they press
themselves in AdvancedSkeleton. This spec covers the middle part only.

Companion: `2026-09-04-advancedskeleton-ue5-rig-design.md`, the rig this drives.

## The animator's loop

```
import the clip (a second UE5 Manny, animated)
  -> select any joint of it
  -> maya_asretarget.connect()
  -> set the playback range to the clip            (the bridge's import does this)
  -> AdvancedSkeleton > MoCap Matcher > Bake
  -> AdvancedSkeleton > MoCap Matcher > Disconnect MoCap Skeleton
```

Everything after `connect()` is the vendor's own UI, which is what the ask
demands.

## Why the vendor's Bake, and why not the vendor's Connect

**Bake and Disconnect are reused verbatim, because they are driven by a
convention rather than by their own bookkeeping** (read in
`AdvancedSkeleton.mel`): `asMoCapMatcherBake` finds the node `MoCapConstraints`,
walks the destinations of its `disableConstraints` attribute to collect the
constraints, resolves each constraint's `constraintParentInverseMatrix`
connection to the object it drives, and `bakeResults`-es exactly those objects
across `playbackOptions -min/-max`, then deletes static channels.
`asMoCapMatcherDisconnect` deletes those same constraints and the
`MoCapConstraints` node. So anything that builds constraints, registers each
one's `nodeState` on `MoCapConstraints.disableConstraints`, and parks its own
helper nodes UNDER `MoCapConstraints`, is indistinguishable from the vendor's
own connect as far as those two buttons are concerned — and the helpers die with
the parent on Disconnect.

**`asMappingUIFunction MoCapConnect` itself is not used**, for four measured
reasons:

1. **It constrains with `-mo`.** The offset is captured at the frame the button
   is pressed, so the clip's pose at that moment is read as the rig's rest pose
   and the whole take comes out offset. That is why the vendor's own UI has
   step 4, "`zero-out` MoCap-joints" (`MoCapZeroOut` writes `rotate` 0 0 0 on
   every mapped source joint — which a keyed source undoes on the next
   evaluation anyway). Our source is an IDENTICAL skeleton and our control
   frames now equal their bone frames, so the correct offset is the identity and
   no pose matching is needed at all. See the measurements below.
2. **It resolves the source by NAME** (`$nameSpaceB + <name>`), so an import
   without a namespace collides with our own UE skeleton — `upperarm_l` exists
   twice — and its tie-break takes the last non-`|Group|` path, i.e. a coin
   flip between our rigged bone and the clip's. Resolving inside the selected
   source's own subtree cannot make that mistake.
3. **It drives no pole vectors**, so in IK mode the knee direction comes from
   the pole sitting at its rest place and does not follow the source.
4. **It leaves root motion in the pelvis.** The rig's `Main` is what our UE
   `root` bone follows, so a clip's root motion must reach `Main` or the
   exported clip has none.

The vendor's `moCapMatchers/Unreal.txt` template is also the wrong shape for
this rig: it is UE4-schema (`Chest=spine_03`, no metacarpals, no `neck_02`) and
our fit is UE5 with `Spine1..Spine5`.

## Measured facts the design rests on

All measured 2026-09-04 in the animator's scene (`UE_To_Many_02.ma`), after the
control-axis work:

- **The offset between an FK control and its bone is exactly the identity.**
  Posing `FKSpine3_M` by 20/−15 turned `spine_03` by 24.95° while the angle
  between the control's frame and the bone's frame stayed **0.00001°**. Same for
  `FKIndexFinger1_L`/`index_01_l`. So writing a world orientation onto the
  control writes it onto the bone, and an `orientConstraint` with **no offset**
  copies the source's world orientation 1:1, at any frame, in any pose.
- **The IK end controls sit on their bones**: `IKLeg_L` 0.0094 cm from `foot_l`,
  `IKLeg_R` 0.0000, `IKArm_L` 0.0003, `IKToes_L` 0.0095, every frame angle
  0.00000°. So point+orient with no offset places hand, foot and ball exactly.
- **`RootX_M`, `Main` and the pole controls keep AdvancedSkeleton's own frames**
  (deliberately — see the rig spec), so those four need a real offset.
- **All four limbs are currently in IK** (`FKIKArm_L/R`, `FKIKLeg_L/R` = 10), so
  an FK-only retarget would move nothing. Both FK and IK have to be driven — as
  the vendor does — and then the rig follows whatever mode each limb is in, and
  a limb flipped after the bake still holds the take.
- **The scene's playback range is 0..46400.** The vendor's Bake reads exactly
  that range, so the range must be the clip's before it is pressed. `connect()`
  reports the range and the source's own key range so the mismatch is visible
  before anything is baked.

## What drives what

| rig control | source bone | constraint |
|---|---|---|
| `Main` | `root` | point + orient, through an offset helper |
| `RootX_M` | `pelvis` | point + orient, through an offset helper |
| 62 × `FK<joint><side>` — spine 1–5, `Neck`, `NeckPart1`, `Head`, `Scapula`, `Shoulder`, `Elbow`, `Wrist`, all five fingers × 4 (incl. the metacarpals), `Hip`, `Knee`, `Ankle`, `Toes` | its mapped UE bone | orient, no offset |
| `IKArm_L/R` | `hand_l/r` | point + orient, no offset |
| `IKLeg_L/R` | `foot_l/r` | point + orient, no offset |
| `IKToes_L/R` | `ball_l/r` | orient, no offset |
| `PoleArm_L/R` | `upperarm_l/r` | point, through an offset helper |
| `PoleLeg_L/R` | `thigh_l/r` | point, through an offset helper |

The twist joints (`ShoulderPart*`, `ElbowPart*`, `HipPart*`, `KneePart*`) have
no FK controls and are skipped: the rig's own twist network recomputes them from
the driven bones, which is the whole point of it.

**The pole rides the UPPER bone's frame, not the mid joint.** A pole
point-constrained straight to `calf_l` is degenerate whenever the leg is
straight (the pole lands on the hip→ankle axis and the knee can flip). The limb
plane is what the pole controls, and for an identical skeleton that plane is
fixed by the thigh's roll — so a helper carrying the pole's REST offset in the
thigh's frame reproduces the source's knee direction exactly and can never
degenerate.

## The offset helper

Two nodes per offset pair, both under `MoCapConstraints`:

```
MoCapConstraints                        (locked transform at the origin)
└── asrtDriver_<control>                point+orient (no offset) to the source bone
    └── asrtTarget_<control>            local matrix = C_rest · B_rest⁻¹
```

The driver carries the source bone's world matrix; the target's LOCAL matrix is
the analytic rest offset, so `target_world = C_rest · B_rest⁻¹ · source_world` —
which at the rest pose is exactly the control's own rest matrix. The control is
then constrained to the target with no offset.

`C_rest` and `B_rest` are read from the scene at connect time **from our own
rig** (the control's world matrix and our own UE bone's world matrix), not from
the source, so the values do not depend on the clip's pose. Maya's row-vector
convention makes the composition `world = local · parent`, so the target's local
matrix is the offset itself.

This is deliberately a pair of transforms rather than a constraint `offset`
attribute: trap 19 in CLAUDE.md is the record of how easy that convention is to
get backwards, and a transform pair is measurable — the gate asserts
`target_world == control_rest_world` while the source stands at rest.

## The tool

`maya_asretarget.py`, repo root, standalone, `maya.cmds` only, no Qt — the
convention every root-level tool follows, and the sibling of `maya_retarget.py`
(which drives another skeleton from Manny; this one drives the rig from another
skeleton).

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
import maya_asretarget
maya_asretarget.report()      # what would be driven, and from what; read-only
maya_asretarget.connect()     # build it, from the selected source skeleton
maya_asretarget.disconnect()  # the same as AdvancedSkeleton's own button
```

**The source is the selection**, climbed to the topmost joint of that hierarchy,
and its bones are resolved by LEAF name inside its own subtree — so a namespaced
import, a plain second Manny whose root Maya renamed, and a group around either
all work the same, and nothing is ever found by a scene-wide name lookup.

Refusals, each naming what to do instead:

- `MoCapConstraints` already exists → Disconnect first (the vendor's own rule).
- nothing selected, or the selection holds no joint.
- the selected hierarchy IS the rig's own — either the UE skeleton our
  `DeformationSystem` drives (its joints carry our constraints) or anything
  inside `Group`.
- no rig in the scene (`ControlSet`/`Main` missing).
- a source bone the map needs is missing → named, skipped, counted; only a
  complete miss (no bone found at all) is a refusal.
- the source's height differs from the rig's by more than 2% → a WARNING with
  both numbers, not a refusal: the vendor's scale step exists for that case and
  the animator may know better.

Everything runs with autoKey off, in one undo chunk, and writes no keys.

## Verification

`docs/superpowers/plans/verify_asretarget.py`, live, in the animator's open
scene. It builds its **own source**: an exact copy of the rig's UE skeleton in a
namespace of its own (`asrtVerify:`), carrying a synthetic take whose numbers
are known — a root translation, a spine bend, a hip/knee flexion, an arm raise
and a finger curl — then deletes it, registering every node it creates by UUID
as it creates it (trap 47).

Gates: the refusals; every row of the table constrained to the expected source
bone; each offset helper's target matching its control's rest matrix; our UE
bones reproducing the source's bones over sampled frames (hands, feet and every
FK-driven bone exactly; knee and elbow within tolerance in IK); the root motion
arriving in our `root` bone rather than the pelvis; the vendor's `Bake` leaving
keys on the driven controls; the vendor's `Disconnect` leaving no node of ours
behind; **the rig still playing the take after Bake + Disconnect**; and the
scene left as found — bind pose, autoKey, playback range, current frame,
selection.

The synthetic source is used rather than a real clip for the same reason
`verify_twist_manual.py` builds its own skeleton: the expectations are then
computed from geometry the run measured, and a fixture that is more symmetric
than the real thing proves nothing — so the source copy carries the real
skeleton's own bind orientations, being a duplicate of it.

## Deliberately not done

- **No scaling or pose alignment of the source.** The ask says «аналогичного
  скелета»; a different-sized skeleton is the vendor's MoCap Matcher's job
  (its steps 3 and 4), and guessing a scale would silently distort a take.
- **No UI.** The ask is for the retarget; the bake is the vendor's button. A
  shelf button can wrap `connect()` later if the loop proves repetitive.
- **No `FKExtra` mode.** The vendor's "Extra" checkbox drives the Extra
  controls so the animator can offset on top of the mocap; ours drives the
  controls themselves, which is what "перекидывается на кости" asks for.
- **No fix for a fractional or huge playback range.** `connect()` reports it;
  changing the animator's range behind their back is how trap 38 happened.

## Addendum: what the live run measured, and what it changed

`verify_asretarget.py` — **green live 2026-09-04, 0 of 26 gates failed** (the
spec above planned 23; three gates were added for what the run found). Five
things came out of getting there, and three of them changed the design.

**The offset is MEASURED per drive, not tabulated.** The design above had the
`Drive` record carry an `offset` flag, and the first run showed why that is the
wrong shape: the IK end controls do not sit exactly on their bones — measured
`IKLeg_L` 0.0094 cm from `foot_l`, `IKToes_L` 0.0095, `IKArm_L` 0.0003 — so a
no-offset point constraint snapped the limb by that much and `ball_l` came out
0.0095 cm off the source. Whether a control stands on its bone is a fact about
the rig, so `connect` now computes `local = C_rest · B_rest⁻¹` for every drive
and calls `needs_offset` (pure) on it: the full matrix for a drive that takes
position, the rotation block alone for a rotation-only drive. Eight helpers
result on this rig — `Main`, `RootX_M`, the four poles, `IKArm_L`, `IKLeg_L` —
and the flag is gone from the record.

**Every rest matrix is read BEFORE the first constraint.** `connect` measured
each control as it built, and by the time it reached the poles the IK controls
were already constrained — a leg pole rides its IK control (`followLeg` 10), so
it had moved, and its offset came out 0.022 cm wrong. The snapshot is now taken
up front. And because a pole's offset is pose-dependent in a way an FK
control's is not, `connect` **refuses a posed rig** and names
AdvancedSkeleton's own *Go To BuildPose*; `connect(require_build_pose=False)`
is there for whoever knows better.

**Both sides of the offset are made rigid** (`rigid`, pure). The rig's own
scale chain leaves about 4e-7 of scale on a bone, `B_rest⁻¹` carries its
reciprocal, and the helper's driver — a plain transform following the bone by
point+orient, scale 1 — cannot reproduce it: 85 cm out at the pole that was 33
microns of error. Stripping scale and shear from both matrices took it to 4
microns, which is float noise on an 85 cm lever.

**The neck cannot be exact, and the number says exactly why.** Measured at a
15° source neck bend: the control reaches its target perfectly (`FKNeck_M`
0.00000° from the source's `neck_01`) and the BONE still comes out 7.5000°
short — half. AdvancedSkeleton's neck in-between distributes the control's bend
across both neck joints, which is what `inbetweenJoints 1` bought us in the
rig. `neck_02` and `head` keep exact ORIENTATION (they have their own
absolutely-constrained controls) and pay in position: the head lands 0.6554 cm
off at that bend.

The knob that removes it is the animator's own: **`FKNeck_M.bias`** — keyable,
soft range 0..10, default 0 — feeds the in-between's blend weight linearly.
Measured: bias 0 → weight 0.5 → 30° on the control turns `neck_01` by
15.0000°; bias 10 → weight 1.0 → **30.0000°**, and with the retarget connected
the neck then lands 0.000015° / 0.000001 cm off the source. So `connect` names
it in the status line, and `connect(exact_neck=True)` sets it — with the
consequence stated, because the bias decides how the baked neck keys
distribute and moving it afterwards would halve the neck again. The default
leaves the animator's rig alone.

**What is exact, and what is not** (measured over four sampled frames of a take
carrying root motion, a spine bend, a leg flexion, an arm raise and a finger
curl):

| | worst error |
|---|---|
| pelvis, spine 1–5, clavicles, fingers, thumb | **0.000020177** (world-matrix element) |
| hands, feet, balls | **0.0016 cm** — the IK solver's own residual |
| knees, elbows | **0.0876°** (`calf_l`), the elbow 0.0005° |
| root motion in the `root` BONE | **0.000000000** against 100.0000 cm travelled |
| finger curl | **0.0000°** |
| neck_01 | 7.5000° short by design; 0.000015° with `bias` 10 |
| after Bake + Disconnect, source deleted | **0.0016 cm** — the same IK residual |
| limbs flipped to FK after the bake | **0.048 cm** |

That last row is the escape hatch the IK residual rests on: the FK controls
carry the source's pose too, so a limb flipped to FK reproduces it bone for
bone. Its 0.048 cm is the rig's own fit — the FitSkeleton was snapped to the
bones with a 0.01 cm tolerance, so the AS chain's segment lengths differ from
the UE skeleton's by a few hundredths and an FK chain shows that as position.
The vendor's bake is innocent: measured, it kept every watched control's value
to **0.000000°**, and spliced no pairBlend.

**Two things about the vendor's Bake worth knowing.** It reads
`playbackOptions -min/-max`, so the range must be the clip's before it is
pressed — `connect` reports both the range and the source's own key range for
exactly that reason (the animator's scene was sitting at 0..46400). And it ends
in `delete -staticChannels`, so it keys only what actually moves: 20 controls
of 74 on this take, and that is right — a rig whose root motion arrives through
`Main` turns as a whole, so the local values of everything else do not change.
The gate computes the must-be-keyed list from the take rather than counting.

**Harness note.** A probe that set `evaluationManager -mode off` outside its own
try/finally died on an unrelated error and left the animator's Maya in DG
evaluation for the rest of the session. Set scene state inside the guard that
restores it, from the first line.

## Addendum 2 (2026-09-05): a twin's bones carry translation, and the neck has a second knob

**Ask:** «Когда делаю ретаргет на AS_Death_Front_3p_01:root совпадение положения
костей очень точное (кроме шеи, что тоже нужно исправить), когда же я делаю
ретаргет на AS_Longsword_Attack_Backcombo:root положение костей начинает
отличаться заметно… Мне важно чтобы мой ретаргет всегда имел 100% точность».

**What was different between the two clips.** Nothing in the schema: both are
full UE5 twins — 94 joints, every hint bone, 74 drives, nothing missing, bind in
the rotate channels, identical limb lengths. What differs is what the clips
animate. Death's non-root bones never translate (≤ 0.02 cm over the take).
Longsword's do — the studio's retarget from the UE4 pack carried the mocap's
bone translations: neck_01 **3.67 cm**, clavicle_l/r **3.65 / 3.64**, spine_05
**2.52**, spine_04 1.46, thigh_l/r 0.81, spine_01–03 0.2–0.5. The twin path drove
every FK control with an `orientConstraint` alone, so those centimetres were
unreproducible and stacked down the chain. Measured at build pose, all four
limbs in FK, over six frames: pelvis 0.000, spine_05 **2.825**, neck_01
**5.037**, clavicle_l **6.347** and the whole left arm with it, clavicle_r
5.975, the thighs 0.800 — with every orientation exact except the rolls AS
sends to the twist joints. That is the 「заметно」.

**The fix: a twin's FK controls follow their bones in position too.** AS is
ready for it — all 62 FK controls have unlocked, keyable, unconnected translate
channels, and +2 cm on any of them moves its UE bone and everything below by
exactly 2.0000 and nothing above (measured on `FKScapula_L`, `FKSpine3_M`,
`FKNeck_M`, `FKHip_L`, `FKShoulder_L`). `Schema.twin` — renamed from
`keep_position`, because the two turned out to be one fact — makes
`drive_plan` give the FK rows `translate=True`. Mixamo's stay rotation-only:
placing our controls on Mixamo's joints would hand the rig Mixamo's proportions
(its arm is 16.5% shorter than ours).

**A rigid follow with a rest offset is ONE `parentConstraint`.** 62 more
position drives through the helper pair would have doubled the nodes the
vendor's Bake walks, so the offset convention was measured instead: on sandbox
transforms over all six rotate orders, `targetOffsetTranslate` = the offset's
translation and `targetOffsetRotate` = its euler **in the constrained node's
rotate order** make the constraint hold `W_control = O · W_source` to
**4.6e-14**; `-mo` stores exactly those numbers; read in xyz for a zyx control
the follow is wrong by up to 1.47; and the node carries
`constraintParentInverseMatrix`, so AS's Bake and Disconnect treat it like any
other. Every position+rotation drive — the 62 FK controls, the IK ends, `Main`,
`RootX_M`: 68 — is now one such constraint, and only the four poles keep the
helper pair (a pointConstraint cannot turn its offset with the bone). 82
constraints and 4 helpers, against 96 and 8 before. `parent_offsets` is the pure
half; a unit test round-trips all six orders.

**Measured after, on the real clips** (build pose, all FK, six frames each):
Longsword — every bone ≤ **0.0009 cm** except the left leg (thigh 0.0097, calf
0.0567, foot 0.0132); Death — ≤ **0.0004 cm** except the left leg (calf 0.0814).
The left leg is the rig's own: `FKKnee_L` stands **0.0637 cm** off `calf_l`
while the right knee stands 0.00004 — the FitSkeleton was mirrored and Manny's
left calf is 0.068 cm asymmetric (CLAUDE.md's own fact) — and because the AS
Knee joint does not roll with the bone (that roll goes to the twist joints), a
constant offset in the deform joint's frame is not constant in the bone's, so
it shows as up to 0.08 cm that wanders with the knee's roll. Sub-millimetre, a
fit fact rather than a retarget fact, and stated rather than hidden.

**The neck's second knob.** With `bias` 10, neck_01 landed exactly and
`neck_02`'s POSITION was exact, but its orientation read **0.73° / 24.24°**
(Longsword frames 18 / 28) and 0.69° / 3.30° (Death) while `FKNeckPart1_M`
reached its target to 0.0000°. Link by link: control → CustomOrientReverse →
`FKXNeckPart1_M` exact; **`FKXNeckPart1_M` → `NeckPart1_M`** carried the whole
error. A fresh orientConstraint to the same target landed exactly, under
`Neck_M` or in world; no cycle in the scene, no staleness (`dgdirty`,
`refresh`, `dgeval`, both evaluation modes identical), every `interpType` the
same. The rig's constraint differs in one input that reads (0, 0, 0) at build
pose: its **`offsetX` is DRIVEN** — `HeadQTETwist_M` (the head's twist about
the neck axis, a quatToEuler) × `twistAmountDivideNeckPart1_M.input2` = 0.5.
AdvancedSkeleton's in-between takes half of the head's ROLL, the same design as
the limb twist joints, while the UE source keeps neck_02 at its rest roll (its
local rotation is a constant 1.914° through the whole Longsword take); a head
twist of 52.8° therefore shows as 24.24° on neck_02. Share 0 → neck_02 exact on
every frame (0.000 at all six samples), neck_01 and the head untouched.
`set_exact_neck` now sets both knobs — `FKNeck_M.bias` 10 and
`twistAmountDivideNeckPart1_M.input2` 0 — and **`exact_neck=True` is the
default**, the ask being an exact neck; the status line says both stay, because
the baked keys assume them, and `exact_neck=False` leaves the rig's in-between
alone and only reports the cost. The lesson worth more than the fix: **a
constraint's `offset` can be a live input — read it under the pose, not at
rest.** Its (0, 0, 0) at build pose is what made this take eleven probes.

**Verification.** `verify_asretarget.py`'s fixture now slides `clavicle_l`
3 cm, `spine_05` 2 cm and `neck_01` −2.5 cm and rolls the head 30° — the shape
of the Longsword clip, without which it could not have seen either bug — and
runs **0 of 27 gates failed**: FK-driven bones to **7e-6** (world-matrix
element), the 68 position+rotation drives single parentConstraints standing on
their rests to **1e-5** (gate 27, the measured offset convention), the neck
1:1 by default (gate 25) with the two costs the default removes measured by
putting the rig's own values back for a moment (gate 26: 7.5000 of 15, and a
roll of neck_02 from the head's 30). `verify_asretarget_mixamo.py` re-run **0
of 18** on the animator's own `Sweep Fall.fbx`, imported into a throwaway
namespace and removed again (224 nodes, none left); its numbers are unchanged
to the last digit. Both verifies save and restore the two neck knobs — since
the default writes them, a verify must put the animator's values back.

**Two things about the workflow, stated rather than fixed.** A Disconnect
without a Bake leaves the rig in the clip's last pose, so the next `connect`
refuses («the rig is posed») until Go To BuildPose — right, since a pole's
offset is pose-dependent, and the message says what to press. And the vendor's
Bake reads the playback range while an FBX import MOVES that range to the
clip's: a wrapper that imports and then runs a verify saving the range restores
the wrong one (measured, the Mixamo wrapper did; the animator's 0..46 was put
back by hand). Save the range before the import.
