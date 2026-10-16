# Ragdoll impulses: a hit on a body part, along an arrow (2026-10-16)

The animator, after the first Ragdoll build: «Теперь я бы хотел реализовать возможность задать импульс в
определенную часть тела по определенному вектору». Asked, and answered (each the recommendation):

- **an arrow in the scene** - `+ Impulse` puts an arrow on the part of the body the selection names; its tip
  is the point of the hit, the arrow its direction; several arrows allowed;
- **its own frame** - each arrow carries `Frame` (the current frame when made); a hit can land at the fall's
  start or in the middle of it;
- **the strength is a speed, m/s** - `Speed`: how fast the hit knocks the part it lands on, whatever the
  part's or the character's mass; the arrow's length shows it.

## Measured first (mayapy, Maya 2027 Bullet)

- `bulletRigidBodyShape` carries `impulse` (world axes) and `impulsePosition`; the impulse is applied on
  EVERY step while non-zero (a constant 1000 accelerated the body), so it is set before one step and
  cleared after it.
- One such step on a 10 kg body with 1000: the body moves 3.33 cm a frame at 30 fps = 100 cm/s, so
  **Δv = J / m**, J in kg·cm/s.
- `impulsePosition` is the point as an offset from the body's centre **in world axes**: (0, 20, 0) spins a
  body the same whether it is turned 90° or not; (20, 0, 0) along the impulse spins nothing.

## The arrow

- `maya_ragdoll/impulse.py`. `+ Impulse` (card, and hotkey row `ragdoll.impulse`): the one rig the selection
  names (Fall's rule); the BODY - the capsule whose axis passes nearest the first selected node's pivot (a
  control, a bone, anything of the rig), read on the game skeleton at the current frame
  (`plan.nearest_body`); the arrow's tip on that body's centre, pointing along the active view's camera
  (the persp camera without a view): a hit from the viewer.
- It hangs in a space that follows the body's first bone (`weaponspace.ensure_marked_space`, marker
  `skeldarRagdollImpulseSpace`, group `RagdollImpulses` under the rig's group), so it rides the take and,
  after a Fall, the fall; it is free to move and turn. One space per bone, shared by its arrows.
- The arrow transform `impulse1` (Maya numbers the next): marked `skeldarRagdollImpulse` = the body's key;
  attributes in the Channel Box `frame` (int), `speed` (m/s, min 0, default 5), `enabled` (bool, on);
  scale locked. Drawn as a head at the tip (curves on the arrow itself) and a shaft on a child whose
  `scaleZ` is `speed` × `SHAFT_CM` (6 cm a m/s) through a multDoubleLinear - the shaft runs back along -Z.
- One undo chunk; the arrow selected after. Delete character takes it (it is under the rig's group).

## In Fall

- `impulse.arrows(rig)`: the rig's arrows, enabled ones used; each read at the fall's first frame `a` as a
  tip and a direction in its body's frame (`plan.in_body`), so it rides the simulated body after.
- `plan.hit_frame(F, a, b)`: a frame at or before `a` hits on the first step (`a + 1`); after `b` - none,
  named on the line («impulse2 at 90 is after the fall (ends 64)»).
- During the stepping (`fall.simulate`), before the step into `t`, each arrow hitting at `t` is turned into
  world from the body as it stands (`bodies[t - 1]`): J = mass(body) × speed × 100 along the arrow, the point
  the tip less the body's centre (`plan.impulse`); `sim.Scene.impulse(key, J, point)` sets it, the step runs,
  `sim.Scene.clear_impulses()` zeroes it.
- The line: «| 2 impulses: head 6 m/s at 12, pelvis 3 m/s at 4».

## Proof

`docs/superpowers/plans/verify_ragdoll.py` gains phases: an arrow on the head of Manny at the fall's first
frame - the head's body after the step moves by Δv against a run without it (the speed the arrow asks, ±10 %),
along the arrow; an arrow off the head's axis spins it, one through its centre does not; a hit mid-fall
changes nothing before its frame (0.000000) and moves after; a disabled arrow changes nothing; an arrow after
the fall is named; `+ Impulse` on a selected control puts the arrow on that part, one undo takes it away;
Delete character takes the arrows. Unit tests for `nearest_body`, `in_body`, `hit_frame`, `impulse`.

Not built: a torque-only impulse, impulses on the dropped weapon or colliders, an arrow keyed over frames.
