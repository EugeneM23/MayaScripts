# Camera Shake: handheld filming and an impact, on an animation layer - 2026-10-13

The animator: «Нужно реализовать отдельный от нашего плагина скрипт (после тестов мы вставим его в наш
плагин). Скрипт нужен для создания процедурной анимации камеры. Суть - я выбираю участок на таймлайне,
выставляю разные параметры а скрипт делает на дополнительном слое анимацию камеры с возможностью нескольких
режимов. 1 - режим реальной съемки. Мы должны передать эффект реальной камеры которую держит человек в руках с
покачиваниями и микро тряской. 2 - режим удара, шейк камеры. Камеру тряхнуло, она вздрогнула и
успокаивается».

Asked, each answered with the recommendation:
- **What shakes: the selected camera** (any camera or transform; nothing selected - our `SceneSetup_camera`
  when there is exactly one). Rotations in the camera's own axes (pan / tilt / roll), offsets in its own axes.
  Our camera drives `camera_root`, so the shake reaches the export.
- **One additive layer per press** (`CamShake_Handheld_10_200`, `CamShake_Impact_45_70`): impacts stack even
  when the second comes before the first has settled; the layer's weight is a strength dial, Mute turns it off.
  The same mode on the same range and cameras rewrites its own layer.
- **An impact is a kick plus a rattle**: the camera is knocked in a chosen direction, springs back with an
  overshoot, and a fine fast rattle rides on top; all of it dies by the end of the chosen range.
- **Live tuning**: after Apply a released slider re-keys that shake; one of ours selected in the Anim Layer
  Editor reads its settings back into the window.

Like the physical stop it starts **outside the plugin**: `docs/superpowers/plans/camshake/skeldar_camshake.py`,
one file, dropped into a viewport (or exec'd) it opens its window; it moves into the hub once tuned.

## The range

The time slider's highlight `[a, b)` gives frames `a .. b-1`. Without one:
- **Handheld**: the playback range.
- **Impact**: the hit at the current frame, settling over **Length** frames (a slider, used only then).

Fewer than 2 frames is refused by name.

## The model (numpy, no Maya)

Time `s = (f - a) / fps` in seconds (the scene's own rate), so a shake reads the same at 24 and 30 fps.
Every frequency is held below `0.42 x fps` (Nyquist would alias it into a slow wobble).

**Smooth noise** `noise(seed, stream, hz)`: Gaussian values on knots `1/hz` seconds apart, a uniform cubic
B-spline through them (C2, no overshoot), scaled to unit RMS by the spline's own mean variance. Knots come in
blocks of 64 from `default_rng([seed, stream, block])`, so **lengthening the range keeps the start the same**
and a seed always gives the same shape. `fractal(..., octaves, gain)` sums octaves at `hz x 2^k` with
amplitude `gain^k`, renormalised to unit RMS. An amplitude below is "about this much at the extremes": two
RMS.

Each target camera has its own streams (the seed plus its index), so two cameras in one press do not shake
in step.

**Handheld** - an operator standing with the camera in their hands. Per frame a rotation vector
`(tilt, pan, roll)` about the camera's X, Y, Z and an offset `(side, bob, push)` along them:
- **Sway** (deg): the body's slow drift and the hands' corrections, a 3-octave fractal from 0.25 Hz x Speed
  (gain 0.5); pan 1.0, tilt 0.75, roll x Roll.
- **Jitter** (deg): the hands' tremor, one octave at 7 Hz x sqrt(Speed); pan 1, tilt 1, roll x Roll.
- **Drift** (cm): the camera's own travel, a 2-octave fractal from 0.2 Hz x Speed; side 0.7, bob 1.0,
  push 0.4.
- **Speed** (x): calm to nervous, scales every frequency.
- **Roll** (x): roll against pan and tilt (an operator holds the horizon better than the aim).
- **Ease** (frames): a smootherstep in from 0 at `a` and out to 0 at `b`; with Ease 0 the shake starts at
  full on `a` (a cut).

Presets: **Calm** (Sway 0.4, Speed 0.6, Jitter 0.05, Roll 0.3, Drift 0.6), **Handheld** (1.0, 1.0, 0.12, 0.4,
1.5, the default), **Nervous** (1.8, 1.8, 0.3, 0.5, 3.0); Ease 6 and the seed kept.

**Impact** - `u = (f - a)/(b - a)`, `tau = f - a` frames.
- **Direction** - where the hit comes FROM, as `h` in camera space (x right, y up, z back): Below `(0,1,0)`
  (knocked up), Above `(0,-1,0)`, Left `(1,0,0)` (knocked right), Right `(-1,0,0)`, Front `(0,0,1)`
  (knocked back, the view kicking up as a recoil), Random (a seeded direction in the picture's plane).
- **The kick**: an underdamped spring's impulse response `x(tau) = e^(-sigma tau) sin(w tau) / crest`, 1 at
  its first crest, `w = pi / Swing` (Swing: frames from the crest to the overshoot), `zeta = 0.08 + 0.72 (1 -
  Bounce)`, `sigma = zeta w / sqrt(1 - zeta^2)`. The view turns toward the picture-plane direction `r` of `h`
  (Front: up): rotation vector `(r_y, -r_x, 0) x Strength`; the camera moves `h x Push` cm; roll `-h_x x Roll
  x Strength` (a hit from the left knocks the top to the right; a vertical hit rolls to a seeded side at half
  that). A second, perpendicular wobble at 1.37 w and a quarter of the strength (seeded sign) keeps the
  recovery from running back along a straight line.
- **The rattle** (deg): a 2-octave fractal from half the rattle rate (`min(11 Hz, 0.42 fps)`), on pan and
  tilt, roll x Roll; enveloped by `(1 - u)^2` (trauma squared: loud at the hit, gone well before the end) and
  ramped in over the first frame.
- Every part is 0 at `a` (frame `a` is the last still frame, `a+1` the jolt), and the kick is tapered by a
  smootherstep over the second half of the range, so **the camera is still at `b`** whatever Bounce says.

Presets: **Light** (Strength 2, Push 1, Swing 3, Bounce 0.5, Rattle 0.6, Roll 0.4), **Hit** (4, 2, 4, 0.5, 1.0,
0.4, the default), **Heavy** (6, 4, 4, 0.55, 1.6, 0.5), **Explosion** (9, 8, 6, 0.4, 3.0, 0.6, from Below),
**Recoil** (3, 2, 3, 0.3, 0.4, 0.2, from Front).

## Onto the camera (exact, by construction)

The shake is a rotation `S` in the camera's own axes and an offset `d` along them. Its own frame is `M = RA .
R(e) [. JO]` (rotate axis, the euler in its rotate order, a joint's orient; Maya's row vectors). The shaken
frame is `S . M`, so the new euler is the one of `RA^-1 . S . RA . R(e)` **nearest the base euler** (both
solutions, every turn of 360), and the layer holds `e' - e`. The offset in the parent's space is `d . M`.
The layer accumulates rotations **by component** (`rotationAccumulationMode` 0), so the camera shows exactly
`S . M` on every keyed frame.

The base `e` is what the camera shows without this layer: its channels read at each frame
(`getAttr(time=)`, after dirtying every curve upstream - a DG context read keeps a stale value per time
otherwise, measured) minus this layer's own value times its weight (0 when muted). So a shake added over
another one composes with it exactly; re-tuning an older one under a newer one is off by the product of the
two shakes' angles (second order: 0.07 deg for two 2-deg shakes).

## The layer

- Created as an additive layer, weight 1, `rotationAccumulationMode` 0, marked `skeldarCamShake` (JSON: mode,
  settings, the frames, the targets' UUIDs, version 1); named `CamShake_<Mode>_<a>_<b>`, Maya uniquifies.
- Keys on every frame `a .. b` (spline), plus 0 at `a-1` and `b+1` (flat) with `a`'s in-tangent and `b`'s
  out-tangent linear, so nothing leaks outside the range, not even between frames.
- Rotate channels always; translate only when Drift / Push is above 0. A locked channel is skipped and
  named.
- **Refused before anything changes**, by name: nothing to shake (no selection and not exactly one of our
  cameras), a channel driven by anything but time curves and animation layers (a constraint, an aim, an
  expression, a driven key) - with a hint when the driver is a camera (`camera_root` is driven by
  SceneSetup_camera: select the camera), a range under 2 frames.
- One undo chunk per Apply, per re-tune and per Delete.

## The window

```
Camera Shake
<SceneSetup_camera - frames 45-70 (highlight)>
Shake  [ + New shake                 v ]  [Delete]
Mode   (o) Handheld  ( ) Impact
Preset [ Hit v ]
  Direction [ Random v ]          (impact)
  sliders of the mode
  Seed [ 7 ]  [New seed]
[ Apply ]
status (3 lines)
```

- **Shake** lists `+ New shake` and every shake of ours in the scene («CamShake_Impact_45_70 -
  SceneSetup_camera»). Picking one loads its mode, settings and seed. Apply always makes a shake for the
  selection and the range (or rewrites the one with the same mode, range and cameras) and picks it.
- **Live**: with a shake picked, a released slider, a preset, a direction or New seed re-keys it on its own
  cameras and frames (one undo chunk). With `+ New shake` they only set up the next Apply. Switching Mode
  picks `+ New shake`.
- One of ours selected in the Anim Layer Editor is picked (a scriptJob on `animLayerRefresh`); the list is
  rebuilt on SelectionChanged.
- Settings are remembered per mode in optionVars `skeldarCamShake_<mode>_<name>`; the picked shake lives on
  `sys` (trap 111), by the layer's UUID.

## Proof

- `tests/test_camshake.py` (mayapy, no scene): the noise (deterministic, unit RMS, smooth, a longer range
  keeps the start, its rate), the envelopes, handheld (amplitudes, roll, drift, ease, speed, seed, scaling keeps
  the shape), impact (still at `a`, the first crest at the strength in the hit's direction, the view turning
  toward the hit, push, bounce, rattle's decay, still at `b`), the euler algebra against OpenMaya on all six
  rotate orders with rotate axes and joint orients, the closest solution across 180, presets, names, ranges.
- `docs/superpowers/plans/camshake/verify_camshake.py`, mayapy standalone: a keyed camera (zxy, a rotate axis)
  shaken handheld and hit; the shown world rotation equal to `S . M_base` on every frame by a real time walk;
  the base curves untouched; nothing outside the range, between frames too; a re-tune rewriting the same layer
  with its weight kept and the shape kept; two impacts stacking; one undo each; Delete; refusals changing
  nothing; two cameras; a joint; and on the plugin's Manny with Camera Setup on `camera_root`, nothing
  selected: the SceneSetup camera shaken and `camera_root` carrying the shake.
- The window in the animator's Maya is theirs to try.

Not built: an operator walking (step bob), a pivot behind the lens, translation in the rattle, a shake's range
moved after Apply, sending the layer to Unreal as a CameraShake asset.
