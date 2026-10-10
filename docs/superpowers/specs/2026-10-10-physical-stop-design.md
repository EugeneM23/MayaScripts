# Physical stop: a pose-to-pose transition with overshoot, overlap and weight - 2026-10-10

The animator: «в открытой сцене в мае я проанимировал кубик, эта анимация это пример для тебя, нужно
изучить анимацию кубика и сделать математическую модель построения подобных анимаций. В будущем я бы хотел
поставить стартовую позу объекта и финальную куда он должен прийти а наш скрипт должен построить переход от
позы к позе ... Мы должны уметь контролировать амплитудность, силу захлеста (отставания) верхней части от
нижней, вес анимации (от веса зависит насколько сильно объект проваливается и как долго он останавливается)
... скрипт берет два последних ключа ... Что бы ты понимал мы делаем скрипт который имитирует физичную
остановку объектов». First a script SEPARATE from the plugin; it moves into the plugin once tuned.

Answered in the brainstorm, each the recommendation but the last:
- **Timing: B stays, the settle comes after.** The object passes pose B exactly at key B's frame, with
  speed, overshoots, and settles back into B over the frames after it.
- **"Overshoot time" is ONE swing (frames); weight is how many swings** (and how deep it sinks).
- **A rigid object, like the cube**: any selected transform, each on its own; the bottom is the low end of
  its bounding box along its up axis; overlap tilts it about that bottom against the motion; sink is world
  down. The up axis can be overridden.
- **Sway is a parameter** (sideways drift + yaw, as in the cube; 0 turns it off, the sign picks the side).
- **Keys on every frame** (not the sparse extremes that was recommended).

## What the cube is (measured over the port, read only)

`pCube1`: a polyCube scaled (4.131, 11.645, 3.884), pivot at its centre, 24 fps, every frame 0..30 keyed
(auto tangents), 32.36 cm of travel along -Z. Decomposed into the bottom point B and the top point T (the
cube's local -Y/+Y ends), `docs/superpowers/plans/physstop/cube_reference.json` holds its world matrices
per frame and per quarter frame.

1. **The bottom's travel is keys at extremes with flat tangents**: a smoothstep over 10 frames to 0.85 cm
   past the target, then -0.95, +0.32, still at f24. Rebuilt from those extremes the curve is exact to
   0.04 cm: hand-keyed.
2. **The top lags like a spring, not by keys**: the long axis tilts back up to 24.1 deg (f8), then -7.4,
   +7.6, +0.8, and rests at 2.9 deg (a lean of pose B itself). Keys at its extremes miss it by 2.4 deg; a
   damped spring DRIVEN BY THE BOTTOM'S VELOCITY (damped period 9.7 frames, damping 0.32) follows it to
   1.4 deg rms.
3. **The sink is the same kind of spring, driven by speed**: -3.1 cm at f7 (the fastest moment, braking
   begins), +0.68, -0.47, +0.08; period 9.0 frames, damping 0.30, rms 0.09 cm.
4. **Sideways sway and yaw**: the bottom drifts -1.25 cm (left of the motion) with +5.7 deg of yaw at f7,
   back at f15, again at f23; slower than the rest (period ~13-16 frames).

So the overlap and the weight are ONE rule: speed loads springs; when the bottom brakes they release into
the follow-through. Both springs ring at the same rhythm. That rhythm is the model's.

## The model

Frames are the time unit (the scene's own rate); `tA`, `tB` the two keys, `A`, `B` their poses.

**1. The path.** A progress `p(t)` carries the object from A (0) to B (1): translate channels lerp, rotate
channels lerp as eulers (what Maya does between two keys, and it keeps a spin of 360 deg a spin).
- `tA..tB`: `p(u) = 3u^2 - 2u^3 + m(u^3 - u^2)`, `u = (t - tA)/(tB - tA)`: from rest, through B exactly at
  `tB` with slope `m` (clamped to [0, 3], so the travel never overshoots on the way).
- after `tB`, with `tau = t - tB`: `p = 1 + (vB/w) e^(-sigma tau) sin(w tau)`, `w = pi/h`, `h` the swing
  time; `sigma = zeta w / sqrt(1 - zeta^2)`, `zeta = clamp(0.32/weight, 0.05, 0.9)`. The velocity is
  continuous at `tB` (`p' = vB` both sides) and `vB` is chosen so the FIRST overshoot equals the
  amplitude: its peak is at `tau1 = atan2(w, sigma)/w`, so `vB = amp w / (e^(-sigma tau1) sin(w tau1))`,
  and `m = vB (tB - tA)`.

**2. The bottom's speed** `q = |b(B) - b(A)| p'(t) / H` in object heights per frame (b the bottom point, H
the height) drives three springs, all `x'' = wn^2 (drive - x) - 2 zeta wn x'`, at rest at `tA`, with
`wn = w / sqrt(1 - zeta^2)` (damped period `2h`):
- **overlap** `theta` (deg, + = the top behind the motion): drive `K_theta q`, `K_theta = 45.4 overlap`;
- **sink** `y` (cm, world down): drive `K_y |q| H`, `K_y = 0.51 weight`;
- **sway** `x` (cm, + = left of the motion) at `0.74 wn`: drive `K_x |q| H`, `K_x = 0.21 sway`, and a yaw
  `psi = 52 x / H` (deg, about world up).

The numbers are the cube's (fitted by `calibrate_physstop.py`; final values there).

**3. The end.** The settle runs until every component (the path residual, theta, y, x, psi) stays within 2 %
of its own peak; that frame is `tE`. Over the last 30 % of `tB..tE` every residual fades to 0 (a smooth
step), so the last key is pose B exactly. The cube's settle is ~20 frames.

**4. Geometry.** Up axis = the object's local axis (sign included) whose world direction at pose B is
closest to world +Y, unless overridden. `H` = the bounding box's extent along it (shapes under the
transform, intermediates excluded) in world units; the bottom point `b` = the box's centre moved to its
low end along that axis. Motion direction `d` = the horizontal part of `b(B) - b(A)`. Per frame:
`W = W_pose(p) . T(-b) . R(axis d x up, theta) . R(up, psi) . T(b) . T(-y up + x (up x d))`. With no
horizontal travel there is no tilt, sway or yaw; with no travel at all (a pure rotation) nothing but the
path's overshoot. `W` is brought back into the object's channels through its parent's matrix at that frame
and its own scale, shear, pivots and rotate axis (`L = W . P^-1`; with `X` = the transform's fixed part
up to the rotation, `X^-1 L = R . Tr(rp + rpt + t)`), the euler in its rotate order nearest the path's own
euler at that frame.

## The script

`docs/superpowers/plans/physstop/skeldar_physstop.py`, one file (the repo root holds only what builds the
plugin since the 2026-10-10 cleanup): dropped into a viewport it opens the window (`onMayaDroppedPythonFile`);
`show()` from the Script Editor. Four layers in it: the model (stdlib `math`), the geometry
(`maya.api.OpenMaya` math classes only), the scene (cmds), the window (cmds).

- **Window** `skeldarPhysStopWindow`: Overshoot (% of path) 4.5, Overlap 1.0, Weight 1.0, Swing time
  (frames) 4.75, Sway 1.0, Up axis [Auto | +X ... -Z]; Apply, Restore keys, Reset; a status line with
  what the last press wrote («pCube1: frames 0-30, tilt up to 23.3 deg, sink 3.0 cm, settles 21 frames
  after B»). The values are remembered (`skeldarPhysStop_*` optionVars). Releasing a slider re-applies to
  the selected objects that already carry a transition.
- **Apply**, per selected transform: the source is the LAST TWO KEY TIMES over translate/rotate XYZ (a
  channel with no curve holds its value); or, when the object carries `skeldarPhysStop` (JSON: tA, tB,
  tE, params) and its last key is at that `tE`, the remembered times - with A read at `tA` and B at `tE`
  NOW, so editing the last key edits pose B. Keys in `(tA, end]` are cut, then a key on every frame
  `tA..tE` on the six channels (auto tangents); one undo chunk per press. A locked or driven channel is
  left alone and named.
- **Restore keys**: back to the two keys (A at `tA`, B at `tB`), the marker removed.
- Fewer than two keys, keys less than a frame apart, a referenced node: refused by name.

## Proof

- `tests/test_physstop.py` (mayapy): the path (0 and 1 exactly at the keys, slope 0 at A, continuous
  velocity at B, the first overshoot equal to the amplitude, the swing time, weight -> more swings), the
  springs (at rest with no drive, the damped period `2h`), the settle and the fade (the last frame is B),
  the signs (the top lags, sink is down, + sway is left), the transform round trip with pivots, rotate
  axis and every rotate order, the euler continuity.
- `verify_physstop.py`, mayapy standalone: the cube rebuilt from two keys (A f0, B f9 - the cube's base
  passes its target at f9.1) with the cube's own pose B; the defaults against `cube_reference.json` frame by
  frame (bottom travel, tilt, sink, sway, yaw); A and B exact; the bottom at B's place at `tB`; keys on
  every frame and none after `tE`; re-apply and Restore; a parented, pivoted, zxy object whose world matrix
  is the model's to 1e-6; one undo.
- The live try is the animator's.

## Not built

A chain (each link a spring driven by the one below), sparse keys, a parent that is constrained or IK
(the parent matrix is read per frame with `getAttr(time=)`, trap 69), scale animation between A and B,
angular speed as a drive (a pure rotation gets the path's overshoot only), integration into the plugin and
the hub (with `maya_overshoot.py`'s future decided then).

## Addendum - what the build changed (the same day)

- **The fitted numbers** (`calibrate_physstop.py` on the real model): `ZETA` 0.30, `K_TILT` 47.10, `K_SINK`
  0.526, `K_SWAY` 0.217, `SWAY_RATE` 0.75, `K_YAW` 51.9; the defaults overshoot 4.5 %, **swing 5.0 frames**
  (not 4.75). Against the cube, rms over frames 0-30: travel 0.37 cm (of 33), tilt 2.0 deg (of 32), sink
  0.08 cm (of 3.8), sway 0.19 cm (of 1.8), yaw 0.8 deg (of 8); it settles at frame 32 (the cube ~27-30).
- **The drives saturate** (tanh): the tilt at 40 deg, the sink at 0.5 heights, the sway at 0.25 heights.
  Speed is measured in object heights per frame (so a scene at any scale behaves alike), which makes a small
  object flying far very fast in its own heights: a 1 cm cube flying 20 cm in 8 frames tilted 102 deg at
  the first limit (80 deg); at 40 it peaks at 54.
- **The clamp is on LONG moves, not short ones**: the arrival slope is held to 3 times the average (else the
  ease dips on the way), so a slow move asked for a big overshoot delivers less, and says so.
- The verify (`verify_physstop.py`, 20 gates) rebuilt the cube from keys at f0 and f9: the bottom 0.45 cm
  rms against the animator's, the top 0.65 cm, the tilt peak 25.7 deg at f7 (the cube 24.1 at f8), the sink
  -3.08 cm (-3.10).
