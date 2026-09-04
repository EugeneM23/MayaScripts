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
