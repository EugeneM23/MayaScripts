# Manual twist controls — 2026-09-03

The animator, the same evening the roll limit shipped: «А можем ли мы сделать
для твистов дополнительные контроллы и там где не справляется авто вращение
вращать твисты руками?»

Yes, and the network already has the place for it. Its last node is an
`addDoubleLinear` whose `input2` holds a constant. That is the addition point.

Read `2026-09-03-twist-roll-limit-design.md` first: it records why the
automatic roll cannot be made to work past ±180°, which is what makes a manual
path necessary rather than a convenience.

**And read the ADDENDUM at the end before acting on the main text**: the bone
axis turned out to run down BOTH signs of local X on this skeleton family,
which corrects what this text says about the ring's placement and about the
sense its rotation carries.

## The four decisions

The animator chose all four:

1. **One mechanic, both jobs** — a control that ADDS to the automatic roll,
   and on a segment where the roll was refused there is simply no automatic
   term, so the same control becomes the only source.
2. **One ring per segment**, eight of them, distributing its rotation to that
   segment's twist joints by the SAME measured fractions the automatic roll
   uses. Not one ring per joint: the fractions stay the single source of truth,
   and «предплечье на 30° больше» spreads 10/20 by itself.
3. **Viewport selection only.** No picker buttons, so `bodymap` and
   `pickerstate` are untouched. The rings are placed and sized to be grabbed.
4. **An `autoTwist` dial, 0..1**, on the same ring: fade the automatic
   contribution out where it is wrong and back in afterwards.

## The arithmetic

Per twist joint, where the segment has an automatic term:

```
auto   = multDoubleLinear(angle.outputRotateX, fraction)   as today
gated  = multDoubleLinear(auto.output, ring.autoTwist)     new
manual = multDoubleLinear(ring.rotateX, fraction)          new
sum    = addDoubleLinear(gated.output, manual.output)      new
total  = addDoubleLinear(sum.output, build-pose value)     as today
```

`manual` is multiplied by **the same `fraction`** — the signed weight
`weights()` already computes, including the follow/counter sign. That is the
whole point of one ring per segment: distribution cannot drift between the
automatic and the manual path, because there is one number.

Cost: three nodes per joint plus one ring per segment. Sixteen joints and eight
segments take the module from 112 nodes to about 170.

## A refused segment: the same shape, minus the automatic term

Where `roll_refusal` fires there is no `delta`/`quat`/`dot`/`norm`/`angle`/
`auto`/`gated` at all:

```
manual = multDoubleLinear(ring.rotateX, fraction)
total  = addDoubleLinear(manual.output, build-pose value)
```

Two nodes. The `autoTwist` attribute is **not created** on such a ring — it
would claim to affect something that does not exist, and its absence is how the
ring says "this segment is yours alone".

**This closes a gap the roll-limit change left open.** `build` bakes any
standing network before it rebuilds, and the refusal then skipped the segment —
so a rebuild of the reported scene baked the old 223° whip into keys on
`upperarm_twist_01_r` and refused to re-rig it, leaving the whip alive as plain
animation. A manual-only network reaches `_clear_channel`, which deletes those
keys. The refusal changes meaning from **skip** to **manual only**, and the
message says so.

## The ring

- **A DAG child of the segment's own bone.** Bones survive FK/IK switches, and
  the twist rig reads bones for exactly that reason — a control on an FK
  controller would be deleted by a switch to IK. It also travels with the limb,
  so it is where the limb is.
- **Its local rotation is identity**, so its own X is the bone axis — measured
  0.00° off on every counter segment of this skeleton family — and `rotateX`
  with rotate order `xyz` is the innermost channel, which is the only way a
  rotate channel is a roll about the bone rather than a turn about the parent.
  `axis_choice` already checks that claim for the joints; here it holds by
  construction.
- **`rotateY`, `rotateZ`, all three translates, all three scales and
  `visibility` are locked.** The control does one thing.
- **At the bone's midpoint**, `(length/2, 0, 0)` in the bone's own frame,
  radius from the skinned mesh through `fkrings` with an outward margin so it
  can be grabbed over the geometry. FK rings sit on the joints, so there is no
  overlap. The margin rides a per-bone correction table like `fkrings._SCALE`,
  and its entries are held to the same standard: chosen by looking at viewport
  captures, not on paper.
- **Seated like `attach.seat` does it** — shear, both pivots, both pivot
  translates and `rotateAxis` zeroed. Trap 32: `cmds.parent` compensates a
  pivot into `rotatePivotTranslate`, and translate 0 / rotate 0 is then not the
  parent's origin.
- **Identity by attribute**: `rigPickerTwistSegment` holds the segment's bone
  name, and the ring is a member of `RigPicker_twist_<limb>`. Never found by
  name — Maya uniquifies `upperarm_r_twist_ctrl` to `...ctrl1` on the second
  character, which is the whole lesson of the active-character work.

## Where the code lives

`fkrings` already owns "ring sizing from the skin, knot dressing" for the whole
toolset, so the ring itself is its job: `_make_ring`, `_final_radii`,
`_style_curve`, `colour_for` and `_hide_rig_machinery` are all there and none of
it is duplicated. `twist.py` keeps owning the segment table, the arithmetic and
the manifest.

The new dependency `twist → fkrings` is acyclic: `fkrings → fkchains → builder`,
and `builder` does not know about `twist`.

## What does not change

The picker, `bake`, `Bake+Delete`, and FK/IK switching. `bake` already samples
the driven channel, so the sum lands in the keys by itself, and the rings die
as manifest members like every other node we create. `twist_limbs_for` takes
the rings down with the limb they belong to.

## Known cost, stated rather than solved

**Build always tears down and rebuilds.** A dialled ring is baked into the
joints' keys and the fresh ring starts at zero: the animation survives, the dial
does not. So dial the twists after the last Build. Carrying the ring's curves
across a rebuild is separate work and is deliberately not done here.

Two smaller consequences, both accepted deliberately:

- **The ring turns +30 while its joints turn 10 and 20.** It is a distributor,
  and that is what the automatic term does too. Showing the full commanded roll
  instead was offered and not chosen.
- **`autoTwist` gates a whole segment**, both of its twist joints together.
  Per-joint gating would need per-joint controls, which decision 2 rejected.

## Deliberately not done

Picker buttons (decision 3 — added later if the rings prove hard to grab),
per-joint rings, carrying the dial across a rebuild, and any change to the
automatic roll's mathematics: the roll-limit spec records why two candidate
reformulations were refuted by measurement.

## Addendum, the same evening — the bone axis runs down BOTH signs

The animator, minutes after the first build: «твисты по левой стороне
строятся нормально по правой криво». Measured in their scene, the bone
direction in each bone's OWN frame:

| segment | axis |
|---|---|
| `upperarm_l`, `lowerarm_l` | **+X** |
| `upperarm_r`, `lowerarm_r` | **−X** |
| `thigh_l`, `calf_l` | **−X** |
| `thigh_r`, `calf_r` | **+X** |

Not left versus right — **arms and legs use opposite conventions per side**.
`ring_offset` returned `(+length/2, 0, 0)` unconditionally, so four of the
eight controls landed at **t = −0.5 along the bone, outside it entirely**:
27.771 cm off on `upperarm_r`, 43.348 on `thigh_l`. The twist joints and their
fractions were correct on both sides all along; only the ring's placement was
wrong.

`ring_offset(length, direction)` now follows the **measured** direction, and a
degenerate direction falls back to the bone's origin — the same call `fkrings`
makes for a bone with no child.

**The fixture is the real lesson.** `verify_twist_manual.py` built every bone
along +X on both sides, so it could not see a control placed by assuming +X.
A fixture more symmetric than the skeleton proves nothing about the skeleton.
It now carries Manny's actual signs (`ARM_SIGN`, `LEG_SIGN`) and gates that
**all eight** controls sit at t = +0.5, plus that the two sides really do run
down opposite signs — so the gate cannot pass by accident.

### And the sense the ring turns in

The control's own X is its bone's own X, so on half the segments it points
against the bone. `axis_sense` cancels the handedness that `choice.sign`
carries for the automatic term, leaving the manual share as **the signed
distribution and nothing else**: `manual = ring.rotateX × fraction`.

That choice follows the toolset's standing convention, set by
`align_controllers`: *equal values on both sides give a mirrored pose*. Verified
on all four pairs — a +30 ring on both sides moves the two joints identically
(−20.000000 / −20.000000 on the upper arms, +10.000000 / +10.000000 on the
forearms) while the bones run down opposite signs.

**The deliberate consequence:** on a −X segment the ring dials *against* the
automatic term's reported number. With the mesh in front of the animator that
is the half that matters — they drag until the shoulder looks right, and they
never compute against the network's angle. A first version of the gate assumed
the opposite convention (that setting the ring to the network's own roll
reading reproduces the automatic term) and failed on correct code; it was
replaced by the mirror invariant, which is the property the toolset actually
promises.
