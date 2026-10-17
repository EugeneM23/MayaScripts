# Ragdoll Blend: the take and the ragdoll mixed (2026-10-17)

The animator: «Возможно ли сделать режим в котором будет смешиваться наша анимация и работа
регдола?» Asked, they took all three kinds of mixing:
- the body follows the take with muscles;
- part of the body plays the take, part is physics;
- a blend in and out in time.

Asked further, they chose:
- **six zones in the card**, each `[Anim | Follow | Free]` with its own strength, and presets;
- **a span plus Blend in / Blend out**, in frames.

Approved: «Да, делай так».

## Measured first (mayapy, 2026-10-17)
- Maya's `bulletRigidBodyConstraintShape` has no equilibrium (target pose) attribute; its springs
  pull to the frame the constraint was built in.
- A **kinematic** body (`bodyType` 1) whose transform moves frame by frame is followed by Bullet.
  A dynamic capsule on a SixDOF2 with free linear and angular axes and springs to such a "ghost"
  follows it: 2.6 cm behind on a 100 cm move over 30 frames at k = 1e4 for 5 kg. Stiffer springs
  rang (14-17 cm): the stiffness is tuned, not maxed.

## The mode
The Ragdoll card gains `[Fall | Blend]`. Shared by both: Length, Mass, Friction, Bounce, the
layer, + Impulse, colliders selected beside the rig. Fall keeps Muscle fade, Strength and Drop
weapon. Blend has:
- **six zones**, each a row `<zone> [Anim | Follow | Free] <strength>`:
  - Torso: pelvis, spine_lo, spine_hi;
  - Head;
  - Arm L, Arm R: upper arm, forearm, hand;
  - Leg L, Leg R: thigh, calf, foot;
- **presets**:
  - Hit reaction: legs Anim (the pelvis with them), the rest Follow 0.5;
  - Arm overlap: arms Follow 0.3, the rest Anim;
  - All follow: every zone Follow 0.6;
- **Blend in, fr** (default 6) and **Blend out, fr** (default 10).

## How it works (`maya_ragdoll/blend.py`)
- **The span**: the highlight, else the current frame + Length (Fall's rule).
- **The take is read first**, on every frame a-1..b: the game skeleton and its drives
  (`scene.refresh_world`), each body's frame (`plan.body_frame`).
- **The bodies**: Fall's 16 capsules, joints with human limits and self-collision, no joint muscles.
  - an **Anim** zone's bodies are kinematic, set onto the take each frame: they play it exactly and
    carry their neighbours through the joints;
  - every other body is dynamic and has a **ghost**: a kinematic body that collides with nothing,
    set onto the take each frame, joined to it by a SixDOF2 with every axis free and sprung
    (`plan.follow_springs`: linear k = m w^2, angular k = I w^2, w = 2 pi `FOLLOW_HZ` x strength).
  A joint between two kinematic bodies is left out.
- **The strength over time** (`plan.blend_strength`): 1 at the span's first frame, smoothstep to the
  zone's own strength over Blend in, held, smoothstep back to 1 over the last Blend out frames.
  Free is strength 0 between the blends.
- **Impulses** hit as in Fall, at their own frames.
- **Out**: every bone the take's motion carried by its body's change:
  `W_bone(t) = W_take(t) . inv(B_take(t)) . B_sim(t)`, the drives the same; a bone riding no body
  plays the take. An Anim body's B_sim is B_take, so its bones are the take exactly, fingers included.
- **The layer** `RagdollBlend_<a>` (override, ours by the Fall marker, the mode in it): weight 1 over
  the span, easing to 0 over the Blend out frames to b, 0 outside. After the span the take plays
  untouched. On the base layer the span is replaced and nothing after it is cut.
- **Weapons** are not dropped: a held weapon hangs on its hand and goes where the hand goes.
- **Refused**: every zone Anim («nothing to simulate»), plus everything Fall refuses.

## Proof
- `docs/superpowers/plans/verify_ragdoll_blend.py` (mayapy) on Manny_Rig, Creep_Rig and Orc_D_Rig, a UE
  clip retargeted:
  - All follow at strength 1, no impulse: every game bone on the take within 2 cm;
  - Anim zones exactly the take;
  - a head impulse knocks the head off the take and it comes back;
  - before and after the span the take is untouched (0.0);
  - bone lengths kept; one undo; no Bullet node left.
- Unit tests: zones, presets, the strength curve, the layer weight, the springs, the carried bone.

## Not built
Balance (the torso holding itself up), a mask per bone, dropping a weapon in Blend.

## Addendum: what the build changed (2026-10-17)

The ghost springs above were built, measured and dropped:
- a spring's damping acts against the WORLD, so any damping lagged a sprint 15 cm, and stiff springs
  rang;
- a kinematic body moved by xform carries no velocity, so a joint to it lags (the hip 7.6 cm).

What stands instead:
- **A servo.** Each frame every body is kicked toward where the take has it on the next frame
  (`plan.servo`): an impulse and a torque impulse, Strength the share of the way. Gravity is paid
  for over the frame, and the velocity is read from the last two frames the run produced. Bullet's
  capsule inertia is a box's (`plan.capsule_inertia`). Every body is dynamic, Anim at strength 1.
- **A limb rolls with its bend plane** (`plan.blend_bodies`): Y along upper x lower, carried on from
  the frame before while straight, the plane's side kept continuous.
  - Rolled with its bone, a UE upper arm spins 80 deg a frame, and the spin made Bullet's capsule
    precess 28 deg off its axis.
  - Rolled with nothing, the chest's roll wandered and carried the shoulders 5 cm.
  - The Creep's straight arm flipped its plane 180 deg in a frame until the side was kept.
- **The drift leaned against**: the next aim is turned back by half the last frame's landing error
  (`plan.aimed`, `DRIFT_GAIN`). The worst bone went from 3.6 cm to 2.1 at strength 1.
- **Joints that never fight the take.** The human range is grown to what the take's own joint angles
  do (`plan.joint_angles`, `widened`, the middle axis inside 85). The linear axes are limited to how
  far the take moves the child's anchor off the joint (`joint_travel`): a shoulder carried by a
  shrugging clavicle moved 8-10 cm on the chest. Bodies the take brings together are left apart
  (`collision_filters(poses=)`).
- **The bake** turns each bone by its body's swing only (`plan.swung`, the take's roll kept) and lays
  it down the skeleton by the take's own offsets from the bone above (the take's lengths). An Anim
  zone's bones and drives are the take's exactly.
- **The pelvis plays the take whenever a leg does** (`plan.body_states`): planted legs hold the hips,
  or the hips tear off them.

Proof: `verify_ragdoll_blend.py`, AS_Longsword_Attack_Back_Light_Combo_1_3P, 14/14 on each of Manny_Rig,
Creep_Rig and Orc_D_Rig.
- All follow, strength 1: every game bone within 2.75 / 3.17 / 2.74 cm of the take (the Creep's long
  arms at a 50 deg/frame turn); bone lengths kept to 0.002 cm.
- Outside the span untouched (0.000000), one undo / redo, no Bullet node left.
- Hit reaction with a 4 m/s head impulse:
  - the leg bones play the take (0.0000-0.0024 cm);
  - the head is the same as in the run without the hit before it (0.000), knocked 5.7-6.3 cm, and
    back on the take by the end.
- The sprint attack on Manny too, with its Anim leg bodies 3.98 cm off (their bones exact).

Not built besides: a weapon's own body in Blend; the IK spine.

## Addendum 2: Follow is a spring with weight (2026-10-17)

The animator tried the build: «персонаж остается на своем месте и что-то там дергается ... Я вообще не
вижу работы регдола». Measured in mayapy on the Longsword combo, Hit reaction, no impulse: the bodies
left the take only during the fast swing (10 cm at the forearm) and their error flipped sign from frame
to frame (-5.8, +0.4, +3.5 cm): a share-of-the-way kick each frame lags a fast take and snaps back. The
frame-to-frame change of the error reached 17.6 cm - the twitch - and nothing read as weight.

- **Follow** (`plan.follow`): each body's error from the take (place and turn, world axes) is carried
  on one frame by a damped spring solved exactly (`spring_step`, `FOLLOW_DAMPING` 0.4: it rings a
  little), and the kick lands the body at the take's next frame plus that error. The strength sets the
  spring (`follow_spring`: 0.5 to 6 Hz, log-spaced - 0.5 is 1.7 Hz) and how much of gravity the muscles
  hold (strength squared: at 0.5 a quarter, the rest sags the body). Strength 1 is the old servo
  (Anim); 0 nothing (Free). The discrete map, the velocity read off the last two frames, is stable at
  every frequency (spectral radius 0.39-0.98, checked).
- The drift lean stays for the held bodies only.
- The status line says when there is no impulse and no Free zone: Follow then only adds weight and lag.

Measured after (mayapy):
- the Longsword's 18-frame span: the frame-to-frame jump of the error 3-4 cm (17.6 before);
- Victory_Emote, 60 frames at the card's defaults: Follow 0.5 lags and sags the hand and head 6-11 cm
  with a jump of 1.0-1.3 cm; Free arms hang 50-64 cm off the take;
- `verify_ragdoll_blend.py` **14/14 on Manny_Rig, Creep_Rig and Orc_D_Rig**: strength 1 within 2.75 /
  3.17 / 2.74 cm, the legs exact, a 4 m/s head hit knocking the head 14.4 / 15.8 / 13.4 cm (5.7-7
  before) and back by the end.
