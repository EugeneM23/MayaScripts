# Twist bones — design

**Date:** 2026-08-20
**Status:** designed.

## The ask

> «В открытой сцене у меня есть скелет у этого скелета есть твист кости. Нужно
> сделать так что бы они работали когда мы создаем ИК руки»

The skeleton carries UE twist joints — `upperarm_twist_*`, `lowerarm_twist_*`,
`thigh_twist_*`, `calf_twist_*`. Nothing in this repo drives them: they are
absent from `bodymap` on purpose, a limb in `builder.LIMBS` is exactly three
joints, and `fkrings.rollup` only *describes* them as "driven joints" while the
thing that drives them lives in Unreal's animation blueprint, not in the Maya
file. So after a Build they hang rigidly off their parent, the skin twists like
a candy wrapper at the wrist, and the deltoid tears at the shoulder.

Answered by the user when asked:

- **Procedural auto-twist**, not controllers and not a rescue of existing
  curves. The animator never touches these bones.
- **The exact quaternion route**, chosen over the classic two-target
  `orientConstraint`, knowing it is more nodes and less conventional.

## Scope: arms and legs, both sides

The mechanism is one piece of code and the leg table is four rows longer than
the arm one, so restricting it to arms would buy nothing and leave the thigh —
which twists no less than the forearm — deforming badly. Asked twice about the
scope and told "делай"; taken wide. Narrowing is one table edit.

`camera_bone`, `weapon_*` and the `ik_*` export helpers are not twist joints and
are never touched.

## What one twist bone does

A twist joint exists to spread one segment's roll along its length so the skin
shears gradually instead of pinching at one joint. Which end the roll comes
from splits them into two kinds, and the sign of the fraction is the whole
difference:

| kind | bones | driver | fraction |
|---|---|---|---|
| **follow** | `lowerarm_twist_*`, `calf_twist_*` | the bone at the far end (`hand`, `foot`) | `+t` |
| **counter** | `upperarm_twist_*`, `thigh_twist_*` | the parent bone itself, against ITS parent | `−(1 − t)` |

`t` is the twist joint's measured position along its parent bone, 0 at the
parent's origin and 1 at the far end.

**follow**: the forearm's roll enters at the wrist. Skin near the elbow must
stay with the forearm, skin near the wrist must follow the hand — so a twist
joint at 40% of the forearm takes 40% of the hand's roll.

**counter**: the upper arm's roll enters at the shoulder. A twist joint is a DAG
child of `upperarm`, so it *already* inherits 100% of that roll; what it needs
is to give some back. A joint sitting at the shoulder (`t≈0`) counters
everything and effectively stays with the clavicle; one at the elbow (`t≈1`)
counters nothing. Hence `−(1 − t)`.

Nothing above is a convention this code invents — it is what the engine's
twist-correction nodes do at runtime, restated as Maya nodes so the animator can
see it in the viewport.

## The number, exactly

Let `M` be the driver's local matrix (`.matrix`, so the bind orientation that
this skeleton keeps in its **rotate** channels is included) and `M0` the same
matrix in the pose the rig was built in. The delta, as an operator on the
parent's frame (Maya is row-vector, so the order is not negotiable):

```
Δ = M0⁻¹ · M
```

`Δ` is an operator on the **driver's parent** frame — for a *follow* joint that
is the segment bone itself (`hand` hangs off `lowerarm`), for a *counter* joint
it is one level higher (`upperarm` hangs off `clavicle`). The unit bone axis `a`
is measured in whichever of the two it is, and the twist joint's own channel
sign is measured separately, so the two frames never have to agree.

Take `Δ`'s rotation as a quaternion `q = (w, v)`. The swing–twist decomposition
puts the twist about `a` at

```
θ = 2 · atan2(v · a, w)
```

which is one dot product and one `atan2` — no basis change, no matrix
conjugation, and **no bend contamination whatsoever**: a swing about any axis
perpendicular to `a` leaves `v · a` at zero. That is the property the classic
two-target `orientConstraint` cannot offer, because it blends the whole
orientation and then reads one euler channel out of it.

Six nodes per twist joint, all stock:

```
driver.matrix ──▶ multMatrix (matrixIn[0] = static M0⁻¹, matrixIn[1] = driver.matrix)
              ──▶ decomposeMatrix.outputQuat
              ──▶ vectorProduct (dot with a)            -> v·a
              ──▶ quatToEuler (x = v·a, w = q_w, y = z = 0, order XYZ)
                       outputRotateX == 2·atan2(v·a, w) == θ
              ──▶ multDoubleLinear (× fraction)
              ──▶ addDoubleLinear (+ the channel's value at build time)
              ──▶ twist.rotate<axis>
```

`quatToEuler` with the y and z components pinned to zero *is* the `atan2`: no
expression node, so nothing here breaks when a node is renamed, and it
evaluates on the DG like any rig.

`atan2` is undefined only when `v·a` and `w` are both zero — a pure 180° swing.
A wrist cannot reach it, and the failure would be a single frame of zero twist,
not a flip.

## Measured, never assumed

Three things are read off the scene at build time and refused rather than
guessed:

**The twist joints themselves.** Found among the parent's children by the
`_twist_` name pattern and sorted by index — not tabulated. A rig with one
twist per segment, or three, is then the same code path, and a UE4-schema
skeleton missing them entirely simply has nothing to build. Only the eight
**segments** are a table: `(limb, parent bone, driver bone, kind)`.

**The axis.** Which local axis of the twist joint runs along the bone, and with
which sign. Adding to a rotate channel only produces a twist about the bone when
that channel is the innermost one in the joint's rotate order; when the measured
axis is not first in the rotate order, that joint is **skipped with a named
reason**, because rigging it anyway would trade a candy wrapper for a bone that
bends when it should roll. Same for an axis more than a few degrees off the bone.

**The fractions**, from the joints' positions along the parent bone, clamped to
the bone's ends. The fallback is for positions that carry no information at all
— every joint of the segment sitting on the parent's origin, or two joints in
the same spot, which cannot be what a rigger who authored two of them meant —
and it is an even split by index (`1/(n+1) … n/(n+1)`). A measured position is
otherwise trusted, including a counter joint at the shoulder, whose `t≈0` and
`−1` weight are the correct answer rather than a degenerate one. A
`_WEIGHT` override table holds any per-bone correction the animator asks for
later — the same escape hatch `fkrings._BORROW`/`_SCALE` already is for ring
sizes.

## Where it plugs in

**Build.** Built automatically by `fkcontrols.rebuild`, in both modes, for every
segment whose bones exist. No new button: the user asked for bones that work,
not for a switch to remember.

**Switch FK/IK — nothing to do, and that is the point.** The network reads the
**bones**, so a hand is a hand whether an FK controller or an IK rig drives it.
No lift, no re-hang, no re-bake — the entire class of rider bugs (traps 9, 16,
21) does not exist here. It is the single strongest reason the quaternion route
won: had the fractions been read from controllers, every switch would have to
rebuild them.

**Bake+Delete** bakes each twist joint's driven channel with `cmds.bakeResults`
over the playback range, then deletes the network and its manifest — so the
button's promise of clean bones stays true, curves included. Our own bake reads
`playbackOptions`, never `timeControl -q -ra`, so it needs no time-slider guard
of its own (the same split the aim build/bake already documents, trap 36); the
Bake+Delete entry point is gated anyway because the OverRig bakes beside it are.

**The manifest is not a scene diff.** `RigPicker_twist_<limb>`, holding the
nodes we created, recorded from the return values of `createNode`. The UUID diff
in `builder._scene_nodes` exists because OverRig conjures up nodes we cannot
see; here every node is ours, and pretending otherwise would only invite the
diff's own traps.

**The picker gains nothing.** Twist joints stay out of `bodymap` — they are
driven, and a button that selects a joint the animator must not touch is worse
than no button.

**The UE bridge keeps working.** No constraint is created, so the trap-37 guard
in `animimport.import_clip` (which refuses a merge onto constrained joints) does
not trip. The twist channels *are* connected, so an FBX merge skips them
silently — which is the right outcome, since the network recomputes the twist
from the imported hand animation. The status line names it. A refusal would make
two of the animator's tools fight over the same skeleton for no gain.

## Idempotence and other people's work

A Build rebuilds: any twist network recorded for the limbs being built is baked
and removed first, exactly as every other build path in this tool does, so a
second press cannot double the network or leave one node driving another.

A twist joint whose driven channel already carries an incoming connection or a
constraint that is **not ours** is skipped and named. The animator may have
rigged these joints by hand, and silently taking them over is the one failure
here that would be hard to notice and hard to undo.

## Known limitation, shared with the FK axes

The zero of every fraction is the pose the rig was **built** in: `M0` is
measured then, and the rest value written into `addDoubleLinear` is the
channel's value then. Build in the bind pose. When a driver bone carries moving
animation at build time the status line says so — `fkcontrols.is_constant`
already knows the difference between a bone with baked constant curves and a
bone that actually moves (trap 30).

Closing it means reading the bind local rotations from the `bindPose` node
instead of the current pose. That is the *same* gap `align_controllers` has, and
it should be closed once for both rather than twice differently, so it is
deliberately not closed here.

## Module

New `maya_overrig/twist.py`, shaped like `aimrig.py` — a pure half above a
`# scene` banner, and nothing above that banner touches Maya:

| part | contents |
|---|---|
| pure | `SEGMENTS`, `_WEIGHT`, kind lookup, `twist_joints` (name filter + index sort), `fractions` (positions → weights, with the degenerate fallback), `axis_choice` (local axes + bone direction + rotate order → channel and sign, or a refusal) |
| scene | `build`, `built_limbs`, `bake`, the manifest, the network |

Imports `maya.cmds`, `maya.api.OpenMaya`, `naming`, `builder`. `fkcontrols`
calls it; nothing calls `fkcontrols` from here, so the existing layering holds.

## Proof

Unit tests on the pure half — kinds, fractions including the degenerate case and
the override table, axis choice including both refusals.

`docs/superpowers/plans/verify_twist_bones.py`, live in the Manny scene:

1. straight arm, hand rolled +90° → every twist joint takes exactly its
   measured fraction, checked against the analytic number;
2. **elbow and wrist bent 60° with no roll → twist is 0** — the gate that
   separates this design from the two-target constraint, which reads bend as
   twist;
3. Switch FK/IK there and back → the network is untouched and the values are
   unchanged;
4. Bake+Delete → the baked curves match the live values to 1e-4 and no node of
   ours is left;
5. a second Build does not double the network;
6. the driver bones do not move on any frame — compared as world **matrices**,
   never euler channels (trap 31).
