# Walk Builder on a sprint: the legs matched to the gait, the trunk and the head on springs - design

2026-10-14. The animator, with `AGS_Sprint` (Unreal's Game Animation Sample sprint, saved as a walk) under the
`two_handed_sword` pose on a Manny skeleton in a second Maya (port 7002), Leg turn up: «1 - Ноги сопоставляются
между анимацией и позой плохо ... Нам нужен какой-то алгоритм (волшебная палочка) который будет автоматически
матчить ноги к более адекватному виду ... одну настройку. 2 - Шум в верхней части туловища ... A - фильтры ...
B - инструмент захлеста возможно на базе ИК ... вместо дрожания был красивый и аккуратный захлест. 3 - Захлесты
головы строятся как-то странно ... более плавный и аккуратный вариант, возможно более физичный.»

Asked, both the recommendation:
- a turned stance on a run: **the hips face the run, the shoulders keep the pose's turn** (the spine twists);
- the trunk's and the head's physics **on by default**; **Overlap stays for the arms only** (the spine's and
  the head's overlap is physical now).

## Measured first (the scene read only over the port; the walk and the pose in mayapy)

- `AGS_Sprint.walk.gz`: 62 frames 0..61, **frame 61 a copy of frame 60** (every joint, 0.0 apart) - the real
  cycle is 60 frames (4 strides, 7.0 m/s). The model read 61: every joint stood still one frame a cycle and,
  against the straight travel line, every place carried a 23 cm sawtooth. The arms' and the grip's springs and
  Balance's pendulum took the jump: the forearms flipped up to 128 deg at the seam, the arms were straight at
  frame 0 (the held sword 18.6 cm off its target, out of reach), the upper arms jerked up to 53 deg (world,
  against a 1-frame blur). With the copy dropped: 2-3 deg, smoother than the source's own arms.
- The pose stands side-on: its hip line 36.5 deg right of the walk's, the shoulders the same (the spine
  hardly twists). Relative to its own hips both legs splay out (knees 24.5 deg, toes 31.3 deg on average);
  relative to the RUN the model read the left knee 27 deg in and the right 63 deg out, and turned each bend
  plane about the hip-ankle line on every frame - in the sprint's swing, with the knee bent, that throws the
  knee sideways.
- What is left of the "noise" is the sprint's own: the chest and the head pitch +-6 deg with a corner at
  every step (8 steps in 2 s, at 30 fps). Rigid two-handed arms carry it into the sword.
- `_smooth_accel` takes ARM_HARMONICS (6) harmonics a stride: for a 15-frame stride that reaches a 2.5-frame
  period - the arms felt the frames' noise.

## 1. A repeated frame is dropped

`model.trimmed(clip)`: while the cycle has more than 9 frames and its last frame equals the one before (every
joint within DUP_TOL: 1e-3 cm, 1e-5 of a rotation element), the last goes; the same for a first frame equal to
the second. Read at `analyse`, so every saved walk is read right (the file keeps what was saved);
`Walk.dropped` says how many, and the summary says so. A walk's root travels, so two equal frames are never
motion.

## 2. Leg match (one knob)

`leg_match` (0..1, default 1, group Legs, before Leg turn). 0 is today's reading of a pose's legs, 1 matched to
the gait:
- **The hips face the walk.** The pose's turn about up (`hips_yaw`, its hip line against the walk's mean,
  from `pose.prepare`) comes off the pelvis (x leg_match); the lumbar joints (the ones Twist's counter turn
  uses, COUNTER_SHARES) take it back, so the chest keeps the pose's facing - only when the pose's Torso part
  is in it (without it the walk's own spine rides the hips).
- **Knees and toes against the pose's own hips.** Each side's turn re-read relative to the pose's hips,
  outward positive; only the symmetric part counts (the mean of the two sides - a front and a back foot are
  a stance, not a gait), against the walk's own symmetric splay.
- **Faded by the gait.** `keep = 1 / (1 + Fr)`, `Fr = v^2 / (g L)` - the Froude number of the NEW cycle (its
  speed after Stride and Tempo; L the legs' mean thigh + calf): a walk at 1.7 m/s keeps 0.75 of the pose's
  splay and width, a run at 4 m/s 0.36, this sprint 0.15. A fast leg has to swing in the line of travel.
- **Width** likewise: the pose's extra width x keep.
- Leg turn still scales the turn it gets; Knee <-> foot still meets them.

The status line: «legs matched to the gait x0.15 (the pose's hips 36 deg in the spine)».

## 3. The trunk and the head on springs

Two bodies on top of the frames, before the arms (the arms then hang on the moving chest):
- **The trunk**: the chest's world rotation (the last spine joint) follows its frame's through a damped
  spring and feels the first spine joint's acceleration on its lever (the upper body's centre of mass -
  spine, neck, head, arms - from that joint, in the chest's frame). The difference is spread up the spine
  (each joint its share by place along it: 0.15 ... 1). Knobs **Torso drag** (frames, default 2) and **Torso
  bounce** (0..1, 0.2).
- **The head**: its world rotation follows what the frames give it - the walk keeps the head's world turn, its
  gaze - through its own spring, feeling the first neck joint's acceleration (the head's mass point a little
  above the head joint); the neck takes the difference (0.3, 0.55, the head 1). Knob **Head drag** (frames,
  default 2.5), the bounce Torso bounce's.
- Same machinery as the arms (`_limb_motion`): world-frame spring (`w0 = 2 zeta / drag`, `zeta = 1 - 0.75
  bounce`), integrated periodic, the seam spread. A spring is also a low-pass filter: the step's corners go.
- Balance carries the pelvis with the bodies moving (they move the centre of mass).
- **The pivot accelerations, and the arms', take harmonics up to ACCEL_HZ (6 Hz)** as well as ARM_HARMONICS a
  stride - a sprint's stride is 15 frames.
- `own_knobs()` give the walk back: both drags 0.
- **Overlap** no longer shifts the spine, the neck or the head (their LAG shares go); the arms keep it.

## Proof

- Unit tests (`tests/test_walkmodel.py`): trimmed; leg match on a synthetic walker under a yawed, splayed pose
  (the hips face the walk, the chest keeps the pose's facing, the turns the symmetric splay x keep, 0 is
  today's); keep falls with speed; the bodies: drag 0 the frames, a jolted pelvis leaves the chest lagging and
  smoother, the head holding its world turn closer; own_knobs the source.
- `docs/superpowers/plans/walkparam/verify_walk_sprint.py` (mayapy standalone; the animator's AGS_Sprint and
  two_handed_sword from SkeldarWalks, skipped without them): the copy dropped and no seam; the knees swing in
  the line of travel as the source's; the hips face the walk and the shoulders the pose; the chest's, the
  head's and the arms' jerk below the kinematic and the source's; lengths kept; the grip held; pictures.
- `verify_walk.py` again.

## Not in this version

The sprint's forward lean under a pose (the pose's upright torso replaces the walk's mean spine, the lean with
it); a pose's split stance; the trunk's translation (it bends, it does not slide); inertia on the legs.
