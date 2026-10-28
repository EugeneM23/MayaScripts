# Camera Shake: Bobbing, a walk's or a run's steps in the camera (2026-10-28)

The animator: «давай для модуля камеры который у нас сейчас создает шейки. добавим еще бобинг вкладку в
которой мы будем настраивать имитацию шагов походки и бега». Asked where the rhythm comes from: «нужно
найти в интернете или посмотри у нас в гайде по походкам... сделать присет формулу и задавать бобинг
процедурно». Presets: walk, run, sneak, heavy / tired, «+ ручки контроля». Approach A of three chosen:
knobs in units, the curve's shape from the gait's physics, presets and a Speed knob from a formula.

## Where

A third mode of `maya_camshake`: `[Handheld | Impact | Bobbing]`. Everything a mode has, Bobbing has:
an additive layer `CamShake_Bobbing_<a>_<b>` (weight = strength), one bobbing layer per camera (Apply
replaces it), a released control re-keys the picked shake, presets, the Tilt / Pan / Roll chips, the
seed, memory per mode (`skeldarCamShake_bobbing`). Frames: the highlight, else the playback range (as
Handheld). The camera only bobs; its travel stays the animator's animation.

## The knobs

| Knob | Unit | Meaning |
|---|---|---|
| Gait | Walk / Run | the curve's shape |
| First foot | Left / Right | the side of the first contact |
| Speed, m/s (`pace`) | 0.5-10 | on release fills Gait, Tempo, Bob, Sway, Nod, Turn, Softness by the formula |
| Tempo, steps/min | 50-300 | the step rate |
| Bob, cm | 0-20 | up-down, peak to peak, twice a stride |
| Sway, cm (`side`) | 0-15 | side to side toward the stance foot, once a stride |
| Nod, deg | 0-10 | the head pitched down as the body rises (peak to peak) |
| Turn, deg | 0-15 | the head's yaw, once a stride, toward the striking foot at contact |
| Roll, deg (`lean`) | 0-10 | the horizon tilted toward the stance foot |
| Footfall, deg | 0-5 | a short jolt at every contact (down), with half as many cm down |
| Softness, % | 0-100 | walk: the double support rounding the low; run: the stance's share of a step |
| Variation, % | 0-50 | each step's size differs (seeded) |
| First contact, fr | 0-60 | frames after the range's start of the first contact |
| Ease, fr | 0-60 | fade in and out |

## The shapes (per step, u from 0 at a contact to 1 at the next)

- **Walk**: an inverted pendulum, `cos(θ0 (2u' − 1))` with θ0 30°, its cusp (the low) at u = 0.1
  (1-2 frames after the contact, ~5 % of the stride), its top at u = 0.6 (passing, ~30 %): fast into the
  down, slow over the up. The cusp is rounded by a periodic Gaussian over the double support
  (0.5 × Softness of a step).
- **Run**: stance (share c = 0.3 + 0.6 × Softness) a spring, `−A sin(π u / c)`, low at mid-stance; flight
  a ballistic parabola leaving and landing at the stance's speed (C1 at both joints), high mid-flight.
- Both normalised to 1 peak to peak about a zero mean (the camera's own height is the mean).
- Sway and roll: `cos(π (q − peak))`, q in steps, peak at mid-stance (walk 0.5, run c / 2), toward the
  first foot at step 0. Turn: `cos(π q)`, toward the striking foot at each contact.
- Footfall: `waves(τ, 0.2 s, 0.5 s, Sharp)` (Impact's) at every contact.
- Variation: a smooth noise at half the step rate scales every term but the turn.

## The formula (`from_speed`), from the gait guide (docs/superpowers/plans/gaitguide/research)

Walk below 2.1 m/s (the walk-run transition, Hansen 2017), run above.

- Walk tempo: 101 / 116 / 128 steps/min at 1.04 / 1.32 / 1.62 m/s (Winiarski 2019), extended linearly
  to 0.5 and 2.1. Bob: CoM 2.74 cm at 0.7 to 4.83 at 1.6 (Orendurff 2004). Sway: 6.99 → 3.85 cm
  (Orendurff), at least 2. Nod: head pitch 3.58° per 5.43 cm of C7 bob (Peters, NASA). Turn 2.85°.
  Softness: double stance 29 / 23 % of a step at 1.04 / 1.62 m/s (Winiarski) → 58 / 47 %.
- Run tempo: 162 / 172.6 / 171.4 / 183.5 / 262 at 2.5 / 2.9 / 3.5 / 4.5 / 12 m/s (Fukuchi, Heiderscheit,
  Čoh). Bob: 8.9 / 8.7 / 8.8 / 8.0 / 4.9 cm. Softness: stance 2 × duty 0.77 / 0.68 / 0.65 / 0.37 of a
  step. Turn 6.1° (Pontzer). Sway (3 cm at 2.5 to 1.5 at 10) and nod (0.35° a cm of bob) are estimates:
  the guide has no running numbers for them.
- Footfall, Roll and Variation are style: presets set them, Speed keeps them.

Presets: Slow walk (1.0 m/s), Walk (1.3), Fast walk (1.6), Jog (2.5), Run (3.5), Sprint (7.0), Sneak
(0.8: bob × 0.4, nod × 0.3, sway × 0.6, tempo × 0.85, soft, no footfall), Heavy (1.1: tempo × 0.9, bob
× 1.2, sway × 1.5, hard footfall), Tired (1.0: tempo × 0.9, bob × 1.3, sway × 1.6, nod × 1.8, variation
30 %). A preset keeps the seed, the first foot, the first contact and Ease.

## Directions

The rotations, as the other modes, about the camera's own axes. The moves are not: up is the camera
parent's up (the world's for a camera under Main), side and forward the camera's heading flattened in
the parent (`along_heading`), so a camera looking down still bobs straight up and down. A camera looking
straight up or down keeps its own axes.

## Proof

Unit tests (the shapes' lows and highs at the guide's places, C1 run, p-p and mean, the formula's table
values, presets, the heading frame, the card with its two menus and the Speed refill);
`verify_camshake.py` gates on a camera looking down 40° in mayapy standalone.
