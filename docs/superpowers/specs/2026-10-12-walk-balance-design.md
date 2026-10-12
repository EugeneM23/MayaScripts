# The parametric walk keeps its balance: the centre of mass over the support

2026-10-12. The animator: «Сейчас наша походка не учитывает центр массы персонажа. В реальной жизни когда
человек идет то тело постоянно сваливается в ту сторону где нету опоры, поэтому ... когда мы ставим ногу на
землю таз находится над этой точкой опоры и начинает сваливаться в другую сторону, мы делаем шаг и как бы
ловим наше тело ... Нам нужно добавить какойто инструмент который будет учитывать поведение центра массы и
корректно переносить вес». Asked: **physics on top of style** (the pendulum adds what the changes bring; at
the defaults the walk is unchanged; Sway stays the style), **masses from a table by bone names**.

## What was measured first (Walk_01, the animator's own cycle)

- The centre of mass from de Leva's segment table on the UE bones: 97.1 cm high (the pelvis 95.1); side to
  side 3.31 cm peak to peak (the pelvis 3.97), forward 1.40.
- A linear inverted pendulum, x'' = (g / h)(x - p), driven by the walk's own centre of pressure p (each
  foot's ground contact, heel to toe), predicts the side sway with **correlation 0.98** (the shape and the
  timing) at 1.4 times its size; forward only 0.89 at 2-3 times. So the walk's body IS a pendulum on its
  support, sideways clearly, forward loosely. The model takes the pendulum's CHANGES, each axis scaled by how
  strongly this walk's own body follows it (fitted on the source: 0.70 sideways, 0.42 forward), never the
  pendulum outright.
- Contact for the pressure is the HEIGHT (a foot point within 2.5 cm of its lowest), not the planted window
  the step uses (13 of 30 frames there; the pressure needs heel strike to toe-off, and no frame without a foot
  down).

## The model (walkmodel.py, numpy)

- **Mass**: de Leva's table (lower, middle, upper trunk spread along the pelvis-to-neck_01 chain at its
  thirds; head 6.94 % at the head; upper arm 2.71 % at 0.577, forearm 1.62 % at 0.457, hand 0.61 % half way
  to its fingers; thigh 14.16 % at 0.410, calf 4.33 % at 0.446, foot 1.37 % at 0.442 to the ball). Every mass
  point is a fixed blend of joint positions, so the centre of mass is one weighted sum of joints
  (`com_weights`, helpers weigh nothing; a missing bone's share goes to the rest).
- **Pressure**: per foot a heel point (the ankle 0.4 of the foot back) and a toe point (the ball 0.4 forward),
  each loaded by its ground contact read on the SOURCE by phase (a lift of 0 does not plant a swinging foot);
  the centre of pressure is the loads' blend, taken where the NEW walk puts the feet (stride, width, the
  pose's feet).
- **Pendulum** (`pendulum`): per harmonic k of the cycle the CoM follows the pressure by w^2 / (w^2 + w_k^2),
  w^2 = g / h (g 981 cm/s^2, h the walk's CoM height, so a crouch sways more), w_k = 2 pi k / the cycle's
  seconds (a slower tempo sways more). The mean is followed exactly.
- **The correction** (knob **Balance**, 0..1, default 1): with M the new walk's CoM and S the source's, L the
  pendulum's path on the new pressure and L0 on the source's (the source's at the same phase):
  - the swing: Balance x (L - L0) about their means, x the fitted follow, forward x Exaggeration, sideways x
    Sway x Exaggeration (Sway still owns the sway);
  - the mean: Balance x [(the new pressure's mean - the source's) - (M's mean - S's)], unscaled - a pose that
    leans the torso forward takes the pelvis back until the CoM stands over the feet as the source's did.
  The pelvis is carried horizontally until the CoM lies on M + the correction (per frame, a secant solve on
  the frame's own CoM; the legs re-solved by IK to the same feet), then the reach's drop is measured again.
- Forward, Balance replaces the old guess: the pelvis's forward swing was scaled by Stride; it is scaled by
  (1 - Balance) x Stride + Balance and the pendulum brings what the step changes.
- At the defaults the pressure, the pendulum and the CoM are the source's: the walk comes back exactly.

## The window and the result

The knob Balance in the Weight group. The status line: «balance: the pelvis carried up to x cm, the CoM sways
y cm (the source z)». `info["balance"]`: the carry, the CoM sway side and forward, the follow fitted, the
residual. A walk without the masses' bones (no spine to neck_01, no legs) skips Balance and says so.

## Proof

- unit (`tests/test_walkmodel.py`, the synthetic walker): the weights sum to 1, helpers 0, legs 39.7 %;
  the pendulum's DC is exact and a harmonic is scaled by its gain, lower and slower follow more; the defaults
  at Balance 1 give the source back; wider feet sway the CoM more than at Balance 0 and onto the target; a
  slower tempo sways more, a faster less; a forward-leaning pose keeps the CoM's mean where the source's was
  (Balance 0 lets it lean); Sway 0 keeps the pelvis on its line; the feet stay planted.
- `verify_walk.py` on Walk_01 / Manny with the goblin and the sword poses: the same, on real data, and a sheet
  (`walk_balance.png`): the CoM path over the footprints, Balance 0 against 1.

## Addendum (2026-10-12, the build)

- Built as designed; the default Balance is 1 (the defaults give the source back, so it costs nothing until a
  knob or a pose changes the support).
- **The carry is cheap**: moving the pelvis moves the body over it rigidly, so a trial re-solves only the legs
  (`_moved_com` on a base frame computed once; the leg's source half cached, `_leg_source`). An evaluate on
  Walk_01 0.25-0.4 s (1-1.4 s solving whole frames). Nothing is carried when the target equals the walk's own.
- **Only feet that are down hold the pelvis down** (found by the goblin's picture, CLAUDE.md trap 227): the
  reach's drop and the shortfall now count a leg only while its foot is within GROUND_TOL of the ground; a foot
  in the air that cannot reach passes nearer the body (`info["swing_in"]`). It changes Balance 0 too, a little:
  stride 1.5 sinks 20.8 cm at the contacts (was 20.4), and 14.0 under Balance (the pelvis carried back).
- Measured on Manny's keys (`verify_walk.py` 47/47): the CoM's change is the pendulum's on the keyed feet to
  0.0013 cm (20 cm wider: the CoM sways 6.63 cm against 3.28), 0.0054 (tempo 45: 5.27 against 3.26), 0.0004
  (tempo 22: 2.02 against 3.21); the goblin's CoM 14.3 cm ahead at Balance 0, over the feet at 1 to 0.002 cm,
  the pelvis 16.7 cm back; the sword's mean following its feet to 0.002 cm. With every part the goblin's feet
  are 68.6 cm wider than the walk's: under Balance it waddles (the CoM sways 21.5 cm) and dips 8.8 cm where its
  far foot lands.
