# Physical stop: three poses - an arc into the overshoot, the lag from the breakdown - 2026-10-12

The animator, after the two-pose prototype (`2026-10-10-physical-stop-design.md`): «давай попробуем сделать
не две позы а 3 задача промежуточной позы определить арку входа в овершут и силу захлеста ... попробуй
улучшить найминг парамметров настройки сделать более логичными и понятными». Asked, and answered:
- **The breakdown M is a key**: the object stands exactly in pose M at M's frame (over a guide that only
  shapes the arc and the lag).
- **Three poses only** (over a [2 | 3] switch): the script always takes the last three keys.
- The rest was presented and approved («делай»): the overlap slider goes (M sets the lag; a multiplier
  would miss M), the names below.

## The model, changed

**The arc.** The bottom point travels a parabola through its places at A, M and B, parameterised by the
chords (`u = tau = |AM| / (|AM| + |MB|)` at M), so an even breakdown on the line makes a straight path and a
breakdown off it bends the path through it. `C(u) = A + u V + u^2 Q`, `V + Q = B - A`,
`tau V + tau^2 Q = M - A`. The progress is the arc-length fraction `s` (a 256-sample table); past B the
bottom runs on along the arc's tangent at B (`C'(1) = V + 2Q`): the overshoot leaves in the direction the arc
arrived, and swings back along the same line.

**The timing.** `p(t)` is a cubic Hermite spline through `(tA, 0)`, `(tM, s_M)`, `(tB, 1)`: slope 0 at A,
`vB` at B (from the overshoot, as before), and at M the slope that makes the curvature continuous
(a clamped spline: `vM = (3 (h2 d1 + h1 d2) - h1 vB) / (2 (h1 + h2))`), each slope held to `[0, 3 x` the
segment's secant`]` (Fritsch-Carlson), so the object never runs backwards and hits M exactly at its frame.

**The lag from M.** At M's frame the path's own pose (channels lerped A to B by `s_M`, its bottom on the arc)
is compared with pose M: `G = W_path(tM)^-1 . W_M` is a rotation about the bottom (both bottoms are M's).
That rotation, less the yaw the sway spring holds at M, is the lag `D` - its angle the overlap's strength,
its axis the direction the top swings (back, aside, twisted - whatever was posed). The tilt spring
(driven by the path speed) gives its shape in time, scaled so it is exactly 1 at M:
`lag(t) = Rot(axis_D, angle_D * tilt(t) / tilt(tM))`. Where the spring barely bends at M (under 15 % of its
peak - a breakdown at the very start), the shape is scaled to its peak instead and the pin below finishes M.
No tilt at M, no lag.

**Exactly M.** The sink and the sway at M's frame, and anything numerical, are what is left between the
model and pose M there: `X = W(tM)^-1 . W_M`. It is pinned with a smooth bump `beta(t)` - 0 at A, rising
(smoothstep) to 1 at M, falling to 0 at B, 0 after - as `T(-c) Rot(axis_X, beta angle_X) T(c) T(beta d)`
about the bottom `c` of each frame. So the object stands in pose M at M's frame, and A, B and the settle
after B are untouched.

Everything else is the two-pose model: the springs and their constants, the settle and the fade, the
geometry (up axis, bottom, the channels back through pivots and the parent).

## The script, changed

- **Source**: the last three key times on translate/rotate; fewer, or two less than a frame apart, is
  refused by name. The marker (`skeldarPhysStop`) holds tA, tM, tB, tE; a re-run reads A at tA, M at tM
  (the key written there is pose M) and B at the last key. A marker from the two-pose version asks for
  Restore keys first; Restore puts its two keys back.
- **Restore keys**: back to the three keys, the marker removed.
- **Controls**, renamed and grouped:
  - **Stop**: **Overshoot, %** (the first swing past B, % of the path; 4.5), **Swing length, fr** (frames of
    one swing; 5), **Weight** (heavier: more swings, deeper sink; 1);
  - **Extras**: **Side sway** (drift aside with a yaw; + is left, 0 off; 1), **Up axis**.
  - optionVars `skeldarPhysStop_overshoot/swing/weight/sway/axis`.
- **Status**: «pCube1: frames 0-32 | breakdown at 5: lag 17.2 deg back, arc bends 1.3 cm | sink 3.10 cm,
  sway 1.31 cm | settles 23 frames after B», and the notes.

## Proof

- Unit: the spline (A at rest, M and B exactly, continuous speed at M and B, never backwards, the first
  overshoot, the swing), the arc (through all three, straight when they line up, the tangent, the run past
  B), the pin bump, the cube's components with M at its frame 5, the composition (A, M and B exact, the lag
  sideways when M is tilted sideways), the window.
- `verify_physstop.py`, standalone: the cube rebuilt from its own frames 0, 5 and its final pose at 9,
  against the animator's cube frame by frame; M exact; an arc bent sideways; the overshoot along the arc's
  tangent; re-apply, undo, Restore; a parented pivoted zxy prop; refusals.
