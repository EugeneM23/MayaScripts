# Camera Shake: Loop for Handheld and Bobbing (2026-10-29)

The animator: «В компоненте camera shake нужно добавить опцию зацикливания анимации для бобинга и для
хенди камеры».

## What a looped shake is

- **The range is one cycle**: frames a..b, frame b shows what frame a shows. This is how our UE clips
  close (Walk_01: frame 31 = frame 0 moved by the travel), how Unreal loops a sequence (its length is
  `(frames - 1) / fps`), and how Maya's cycle infinity repeats a curve (first key to last key).
- **The layer's curves cycle past the range** (pre / post infinity cycle), so the shake goes on before
  and after it.
- **No Ease**: a loop has no ends to fade. The Ease slider is dimmed while Loop is on.
- **Impact has no Loop**: a hit is an event, not a cycle.

## The model

- `noise(..., period)`: a whole number of knots in the cycle (`loop_knots`: the nearest to
  `period x hz x KNOTS_PER_CYCLE`, at least `LOOP_KNOTS` 3), their indices wrapped. The spline closes C2
  across the seam, and the rate moves a little to fit.
- `fractal(..., period)`: every octave so.
- `tremor(..., period)`: the sine at a whole number of cycles (`whole_cycles`, at least one, under the
  frame rate's cap), its swell and wander looped noises.
- Handheld: every noise looped over `(b - a) / fps` seconds.
- Bobbing: the tempo is the nearest that fits a whole number of strides in the cycle (`loop_tempo`,
  at least one stride), and the variation is looped. The footfall's waves are shorter than a step, so
  they repeat with the steps.
- Loop off: the model is unchanged, value for value (tests compare it against settings with no
  `loop` key).

## The keys

- Every frame a..b keyed (spline), and nothing a frame outside.
- An earlier press's zeros at a - 1 and b + 1 are cut, and the curve's pre / post infinity set to cycle.
  Loop off sets constant infinity and the zeros again.
- **Both end keys fixed on the chord across the seam**, `atan((v[a+1] - v[b-1]) / 2)`. Measured in
  2027: a spline's end key takes one side's slope only, even on a cycling curve (0.77 against 1.29 on the
  two sides of a seam, the chord 1.03). A fixed angle's tangent is the slope in the curve's units a
  frame, at film, ntsc and 60 fps alike. My first probe used a sine, whose one-sided and two-sided slopes
  happen to agree; the verify's seam gate is what caught it.

## What the line says

- `| looped: frame b shows frame a, the layer cycles past them`.
- A bobbing adds `| 2 strides in the loop at 120 steps/min (Tempo 116)`.
- **The seam's honesty**: the layer adds the shake on top of the camera's own turn, so its first and last
  frames differ when the camera's own animation does not repeat over the range. The press then names the
  camera and the jump: `loopCam's own animation differs at frames 0 and 45: the loop's seam jumps 0.55
  cm - loop it over the range too`. The layer keeps the honest per-frame values; forcing its ends equal
  would put the shake off the model at frame b.

## The card

- A **Loop** chip (`skeldarCamShakeLoop_<mode>`, a checkBox, so a popup copy scopes it) at the top of the
  Handheld and Bobbing columns.
- Remembered with the mode's settings and kept by presets.
- A press re-keys the picked shake of its mode, else sets up the next Apply.
- The subtitle reads «New looped handheld shake ...», or «Editing L: cam, frames 0-60, looped».

## Found on the way: a deleted shake left its shake behind

Measured in mayapy: a deleted animation layer leaves what its blend last evaluated in whatever fed it:

- in an unkeyed channel: rotateX -15 stood at -13.03;
- in the base of the layer above it: -19.41.

So Delete, and an Apply replacing a shake, left the shake at the current frame in a camera's unkeyed
channels for good, and a new shake was built on that offset.

- **The fix** (`_delete_layer`): mute the layer and let Maya evaluate its plugs, then delete it. The
  stack is then left without it, in both orders.
- Giving one camera's channels back (`removeAttribute`) leaves nothing behind, so it is unchanged.

## Proof

- `tests/test_camshake_loop.py` (41 tests): periodic noise, tremor, fractal, handheld and bobbing over
  three cycles; loop off unchanged; the fitted tempo and its steps; the keys, the seam tangents and the
  infinity; the seam's gap and line; the card's chip; a deleted layer muted first.
- With the existing suites, 214 tests OK.
- `docs/superpowers/plans/camshake/verify_camshake.py loop`, **16/16 in mayapy standalone**, on a
  camera under a turned parent whose own turn cycles every 60 frames:
  - keys exactly 0..60, every curve cycling;
  - the camera's turn in its own axes to 1e-16;
  - past the range the cycle again, half frames too, 4e-16;
  - the seam's slope jump 9e-4 against 2e-3 at any key inside (0.54 before the fixed tangents);
  - a re-tune out of the loop and back;
  - a looped walk at 120 for 116;
  - both loops repeating together;
  - the layers gone and the camera its own (2.43 before the mute);
  - the seam named for a 45-frame loop.
- The whole verify **58/58**.
- Picture `docs/superpowers/plans/camshake/camshake_loop.png` (`render_camshake_loop.py`).
- Not seen in a GUI Maya.
