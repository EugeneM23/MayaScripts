# The parametric walk: the legs and the pelvis (2026-10-12)

The animator, looking at the goblin walk keyed in their scene: «Давай поработаем теперь над алгоритмом обработки
ног … 1 - у нас есть параметр сужения ног, но он очень ограничен и сейчас ноги стоят сильно широко … нужен
параметр который будет отвечать за сужение\расширение позиции ног в начале и конце шага и еще один параметр
который будет отвечать за амплитуду выброса ноги в сторону когда персонаж совершает пронос … 2 - нужно добавить
возможность подворота колена в зависимости от подворота ступни. например сейчас в 11 кадре правая нога сломана,
колено сильно вывернуто. Да и левая ступня тоже сломана … 3 - таз у живого существа должен вращаться во время
шага … таз вращается в зависимости от разворота ног и когда опорная нога ставится на землю она немного
продавливает таз вверх … 4 - сейчас в анимации стопы почти всегда ровные нужен параметр который усилит анимацию
захлеста стоп. Попробуй найти информацию о работе ног и таза в движении».

Asked, the animator chose:

- **the stance width as a multiplier** (1 is as now with the pose; 0.3 brings the feet near the centre) plus a
  second knob for the swinging foot's path out to the side in cm (+ out, − in);
- **the knee and the foot meet half way**: a knee turned against its foot and the foot turn toward each other,
  up to ±15° of twist left in the shin (a living shin twists that much); a 0..1 knob moves the meeting point;
- **physiological pelvis motion**: the knobs set target amplitudes in degrees, physiological by default (the
  walk changes at the defaults); the twist grows with the step;
- **the feet's overlap in the swing**: the foot lags the shin after it leaves the ground and catches up before it
  lands, with a delay and a strength knob.

The model is `docs/superpowers/plans/walkparam/walkmodel.py` (the parametric walk, its pose and its balance:
see CLAUDE.md, "Parametric walk").

## Measured first

On the source walk (`asd`, Walk_01: 31 frames, step 86.6 cm, leg 85.6 cm, step/leg 1.01, 1.71 m/s) and on the
goblin result in the animator's scene (every part of the goblin pose, Width −15, Balance 1), rebuilt in mayapy
standalone; the scene was only read.

| quantity | the walk | the goblin result | norm (Perry & Burnfield, Inman) |
|---|---|---|---|
| pelvis twist (hip line about up) | ±6.13°, in phase with the feet's fore-aft split (corr 0.99) | the same, pp 12.6 | ±4–5° at a normal step, more with a longer one |
| pelvis list (hip line, stance side up) | ±1.10° against the support (corr 0.76), its peak late in stance | pp 3.8 | ±4°, the peak ~17 % of the cycle after the heel strike |
| chest twist against the pelvis | counter-rotating, corr −0.89, pp 7.9 | corr 0.28, pp 4.0 | the thorax counter-rotates |
| feet apart (mid-stance) | 17.1 cm | 71 cm (the pose's 68.6 cm, Width −15) | 7–10 cm for a person |
| shin twist (knee hinge vs foot hinge) | within ±18° | −40° on the left in the swing | ~±15° of tibial rotation |
| foot pitch (ankle→ball, against flat stance) | +24° toe up at the heel strike, −57° at the toe-off | the walk's | +20–25° / plantarflexed at the toe-off |

**The twist was not missing**: ±6.1° is the norm for this step (my question to the animator said ±2°; that was
wrong). In the goblin it does not read because the chest stopped counter-rotating (the pose leans the spine 60°,
and the walk's spine twist, a local turn, then turns the chest about a leaning axis). The **list is weak** (±1.1°,
peaking late).

**The breaks** (frame 11):

- the left knee is turned in 38.6° by the pose while its toe is not (−0.2°), so the shin twists −40° once
  the foot leaves the ground: a swinging foot keeps the walk's WORLD orientation and does not follow its turned
  shin;
- the right leg runs straight over frames 19–24: its swinging foot is out of reach of a hip that Balance has
  carried over a stance foot 35 cm aside.

The feet stand 71 cm apart because the goblin's Feet part adds the pose's own spread (68.6 cm), which the
Width knob (−15 at the least) could not take back.

**The feet**: the walk's pitch is physiological; what is missing is a swing that trails the shin.

## The design

### 1. Stance (×) and Swing out (cm) — replace Width

A planted foot's place across the travel line, about the middle of the walk's two footprints `c`:

    aside = c + Stance · (h + sign · W / 2)

`h` is the walk's own half-spread (+9.2 / −7.9 cm about c = +0.65 here); `W` is the pose's added spread × Pose
(0 without a Feet part); sign is + left, − right. Stance 1 is the walk with the pose's feet; 0 puts both feet on
the middle line. Both footprints of a step move alike, so a swinging foot travels between its new prints as it
did between the walk's.

**Swing out** adds `sign · Swing out · sin(π s)` cm to the swinging foot's path along `side`, where `s` is
its progress between the prints (0 at the takeoff, 1 at the landing). + swings it out, − in toward the
other leg. It is in the walk's size (a target scales it).

The `width` knob is gone; a saved walk's `width` is ignored by Pick (its knobs are filtered by the model's).

### 2. Knee and foot meet

Under a pose:

- the knee's turn is `dk = Pose · knee_turn`;
- the toe's turn is `df = Pose · toe`;
- the twist they put in the shin is `d = dk − df`;
- `TWIST_FREE` = 15° of `d` stays; the excess `x = d − clip(d, ±15°)` is shared by **Knee ↔ foot** (`knee_foot`,
  0..1, 0.5 by default):

      knee = dk − (1 − knee_foot) · x        foot = df + knee_foot · x

  0 turns the knee to the foot, 1 the foot to the knee. A pose without knees or without feet has 0 for that
  turn, so a pose's toe-out alone takes the knee along too.

**In the swing the foot follows its shin**: its rotation is the walk's foot in its calf (`lrot_at`) on the new
calf, blended in from the world-planted rotation by a swing weight

    w = smoothstep(s / 0.25) · smoothstep((1 − s) / 0.25)

where `s` is the swing's progress in time. The foot leaves and lands planted; in mid-swing it hangs off its
shin as the walk's does. Without a pose, at the walk's stride, the new calf is the walk's and nothing changes.

### 3. The pelvis: Twist and Hip drop in degrees

Two knobs, each the amplitude of one turn about the travel frame. Each is laid on the walk's own as an extra
world turn of the pelvis that brings the walk's fitted amplitude to the target, on a fixed shape:

- **Twist (deg)** (`pelvis_twist`, 0..15, default **5**): about up, the forward leg's hip forward.
  - The shape is the walk's normalised fore-aft split of the feet (corr 0.99 with its own twist).
  - The knob is the twist at a normal step, 0.8 of the leg; the twist grows with the step:
    `amplitude = pelvis_twist · Stride · (step / leg) / 0.8`.
  - This walk: ×1.26, so 5 gives ±6.3°. Its own ±6.13° reads as 4.86.
- **Hip drop (deg)** (`pelvis_list`, 0..10, default **4**): about forward, the standing leg's hip up and the
  swinging leg's down.
  - The shape is `cos 2π(τ − t_l)/P`, with `t_l` 17 % of the cycle after the left heel strike (the norm's peak).
  - This walk's own: 1.10 on that shape (fitted).

The extra is `Pelvis motion · Exaggeration · [radians(twist_gain·(pelvis_twist·Stride − own_twist))·s(τ)·(−up)
+ radians(pelvis_list − own_list)·c(τ)·fwd]` post-multiplied on the pelvis's world rotation. `Walk.own_knobs()`
gives the walk's fitted values, at which the extra is exactly zero: the walk itself.

**The lumbar spine takes the extra back**: spine_01, spine_02, spine_03 (the walk's first three `spine_NN`) turn
by −0.40, −0.35, −0.25 of it in the world (renormalised over fewer). So the chest keeps its motion: the pelvis
twists and drops under a steady thorax, and the lower back bends between them. The CoM, the reach's drop and
Balance all see the turned pelvis (it is in `_body`).

`pelvis_rot` keeps scaling all of the pelvis's turns (the extra included): the label becomes «Pelvis motion».

### 4. The feet's overlap: Foot lag (frames) and Foot flex (×)

In the swing (the same weight `w`), the foot's rotation in its calf is the walk's:

- taken **Foot lag** frames earlier (0..6, default 0);
- its turn about the walk's mean foot-in-calf scaled by **Foot flex** (0..3, default 1).

The ball, in the foot, gets the same at 1.5× the lag. After the toe-off the foot trails the swinging shin and
flicks through; before the landing it is planted again. In stance nothing changes.

### The window

The groups:

- **Pose**: pose
- **Step**: stride, tempo, lift
- **Legs**: stance, swing_out, leg_turn (addendum 3), knee_foot, foot_lag, foot_flex
- **Pelvis**: bob, sway, pelvis_rot, pelvis_twist, pelvis_list
- **Upper body**: spine, arms, head, overlap
- **Weight**: weight, balance, exaggeration

The status line says the pelvis's twist and hip drop in degrees.

## Proof

- Unit tests (synthetic walker):
  - `own_knobs()` gives the source back, and the defaults are no longer the source;
  - Stance: the spread scaled about the prints' middle, the pose's width ×Stance, 0 on the line;
  - Swing out: `sin(π s)` across, 0 at the prints;
  - the meeting rule, alone and in the legs (knee and toe turns as computed; 15° kept);
  - the swinging foot on its shin under a turned knee;
  - Twist and Hip drop: the hip line's fitted amplitudes equal the knobs (×stride), the chest's world rotation
    unchanged by them;
  - Foot lag / flex: the foot-in-calf late by the lag, its turn scaled, the stance untouched;
  - every knob in one window group.
- `verify_walk.py` (mayapy standalone): the twin checks at `own_knobs()`; Balance's gates on Stance; new gates
  on the goblin — the feet apart at Stance 0.35, no shin past the free twist plus the walk's own, the hip drop
  and twist measured on Manny's keys.
- Pictures: the goblin before and after, front and side.

## Not built

A per-frame knee-to-foot solve (the rule acts on the pose's turns; the walk's own shin twist rides on top), the
pelvis's tilt as a degree knob (Pelvis motion scales it), the split stance of a lunge pose, the swing foot's path
avoiding the other leg.

## Addendum: what the build changed (2026-10-12)

1. **A posed pelvis and spine turn about the walk's WORLD axes.** Measured on the goblin: the twist the knobs
   lay on the pelvis read only in numbers. The pose leans the spine 60°, and the walk's spine twist, a turn
   in each joint's own frame, then turned the chest about a leaning axis:
   - chest heading pp 4.1 against the walk's 7.3;
   - counter-turn against the pelvis, corr −0.45 against −0.86.

   The fix:
   - Each spine joint's turn is re-expressed so it acts about the axis it acts about in the walk, at the mean
     pose (`_spine_map`: `turn @ W_walk_j @ W_pose_j^T`, both chains of mean locals from the mean pelvis).
   - The tilted pelvis's own turn gets the same (`turn @ wmean @ centre^T`).
   - On the synthetic walker every joint's world turn equals the walk's to 1e-9.
   - The goblin's chest is back at pp 7.4, corr −0.79.
   - Without a pose both maps are the identity.
2. **The hang and the bow act in the foot's flight, not the step's swing.**
   - The step's contact window (`Foot.on/length`) ends before the toe leaves the ground: `down` is the heel or
     the toe within 2.5 cm of its lowest. Keyed to the window, a toe still on the ground was turned by its shin
     and moved by Balance: up to 3.8 cm on the goblin, 0.9 cm sideways under Swing out 8.
   - The flight (`air`, `air_progress`) is the longest stretch off the ground, found to 1/64 of a frame, and
     never touches it.
   - The interpolated contact flickers just after takeoff: Catmull-Rom over a 0.86 → 0.08 → 0 heel rises
     again to 0.0015 near the next frame. The flight is the longest run, so the flicker is left out.
3. **Leg turn** (`leg_turn`, ×, 0..2, default 1, in Legs) scales the pose's knee and toe turns before they
   meet.
   - The goblin's right leg at frame 11 is not twisted: its knee is 35.5° out and its toe 44.8° out, 9° apart.
     It is turned out as a whole, on a leg folded to 50 cm hip to ankle under a 68 cm pelvis (the walk's: 80).
   - The walk's own knee there points 15° out too. The knee stands 32 cm outside the hip; at Leg turn 0.5,
     24 cm.
4. **The defaults lower the pelvis up to 0.47 cm** (mean 0.11) on Walk_01: the 4° hip drop lifts the standing
   hip past the leg's straightest, and the reach takes it back. It is in the model's result, not a target's
   drop. The pose-height gate now runs at the walk's own knobs.
5. Measured on the goblin (every part), Stance 0.35 against the scene's Width −15:
   - the feet 29.8 cm apart instead of 70.2;
   - the left shin's worst twist −13.0° instead of −40.7°;
   - no foot out of reach (the scene's: up to 8.2 cm nearer the body);
   - the right knee never at its reach: least bend 23.8° (the scene's sat at 12.4° for six frames);
   - the hip drop 3.4° instead of 1.1°;
   - the twist ±6.4°.
