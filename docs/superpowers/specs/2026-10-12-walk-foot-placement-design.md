# Parametric walk: Foot placement — no slides, one foot always down (2026-10-12)

The animator: «Давай реализуем парамметр foot placement который будет исключать проскальзования ног.
Сейчас у нас есть момент когда двигаются сразу две ноги, но так не бывает когда человек идет».
Asked, both answers the recommendation:
- **one knob**, Foot placement 0..1;
- **on by default**: 1, with `own_knobs()` giving 0, which is the walk's own feet.

## Measured first (Walk_01, the walk tool's source)

- **The walk's stance feet slide** up to **0.87 cm a frame**: about 6.5 cm over each contact, mostly
  forward.
- **There is a step with both feet moving.** Between the left lift-off and the right strike, both feet
  move at frames 7, 8 and 14, and the double support is **−0.19 frames** (a flight). The other step's
  double support is 0.75 frames.
- **The contacts, by height** (the heel = the ankle, or the ball, within `CONTACT_TOL` 1.5 cm of its own
  lowest):
  - left: heel 9.3–20.1, ball 10.5–24.8 → contact 9.31–24.81;
  - right: contact 25.00–41.06.

## The model (`walkmodel.py`)

**The analysis** (`_placement`, once per walk):
- **Each foot's contact:** the longest stretch with the heel or the ball down.
- **Its pivot weight λ:** 0 on the heel, 1 on the ball. Whichever is down alone holds; where both are
  down, a smoothstep moves it across. A forefoot strike works the same way.
- **The heel's ground point** (`heel_loc`, in the foot's frame): under the ankle at the ball's height,
  `HEEL_BACK` (0.25) of the foot behind it.
- **The joints below each thigh** (balls, twists) are listed in `leg_side`; they ride their foot's clock.
- **Each foot's growth target:** the trailing foot stays down longer, until both feet are down
  `DOUBLE_SUPPORT` (8 %) of the cycle at every step.

**Per evaluate:**
- **The lock** (`_locks`): integrated on the foot's own output at 1/16 frame. Over the contact, the ankle
  shifts along the ground by minus the pivot's motion, where the pivot is `(1 − λ)·heel + λ·ball`.
  - It is zero at the load-weighted mean of the walk's contact, so the walk's mean pressure is unchanged.
  - Across the swing a cubic carries the lock from the lift-off's shift to the next strike's, with end
    slopes that cancel the pivot's own speed: the foot lifts and lands without sliding.
  - It is scaled by the knob.
- **The clock** (`foot_time`): each foot runs on its own source time.
  - It is a periodic monotone C1 cubic through (strike', strike) and (lift-off', lift-off), both slopes
    the harmonic mean of the two stretches.
  - The contact plays slower and the swing quicker; the body keeps its own time.
  - The leg's source data, `down`, the hang, the balls and the twists all read the foot's time; the hip
    reads the body's.
- **The growth** (`_growth`): the trailing foot's extra stance (the strike keeps its time). It starts from
  the target × the knob and is cut back while the trailing leg can't reach as well as at the walk's own
  lift-off.
  - The leg is rolled over its ball for this test, against the knobs' own hip before Balance carries it,
    so Balance never retimes the feet.
  - It is never below one frame of the new cycle with both feet down: no flight.
  - It is at most `EXTEND_MAX` (half) of the swing.
- **The roll** (`_rolled`): a foot on the ground, or just off it, rolls about the point it stands on so
  its leg reaches the hip; the pelvis drops only for what remains.
  - Mostly on its ball (λ ≥ 0.5) it rolls further over it: heel up, up to `ROLL_BALL` 30°. The toes take
    the turn back and stay flat.
  - Mostly on its heel it rolls back onto it: toes up, up to `ROLL_HEEL` 15°.
  - The angle comes in closed form: the least roll that reaches, else the nearest.
- **Only a planted foot holds the pelvis down** (`planted`):
  - under the knob, the lock's contact;
  - else, as before, `down` (`GROUND_TOL` 2.5 cm).

  A foot 1.5–2.5 cm up has left the ground, so it passes nearer the body instead.
- **Balance's pressure loads each foot on the walk's own timing.** The longer push-off rolls off a foot
  the weight has already left. With per-foot clocks the mean pressure moved 5.5 cm back, and Balance
  carried the pelvis 6.6 cm back on every frame.
- **Reported:** `info["placement"]` = on, the longest slide held, the double support per step (new frames),
  the frames each foot is planted, and a note. The status line reads «feet planted (slides of up to 6.5 cm
  held), both feet down 2.5 / 2.4 frames a step».

## Two roads that failed, measured

- **The double support at 8 % at every stride**, its growth split between the strike and the lift-off:
  - the pelvis dropped 13.2 cm at stride 1.3 (without placement 5.5) and 39 at 1.6 (18.5);
  - the trailing leg, 64–68 cm behind the hip, was binding;
  - the heel strike side can't roll much.

  So now only the push-off grows, as far as the leg reaches.
- **The 2.5 cm "down" window holding the pelvis down under the lock:**
  - frames just after lift-off, where the foot is already rising, needed 8–15 cm of drop;
  - only the lock's contact counts now.

## Proof

- **`tests/test_walkmodel.py`, FootPlacementTests** (synthetic walkers, one sliding 6 cm, one with a
  flight):
  - the knob and `own_knobs`;
  - the clock is the identity at 0, hits its knots, never runs back and is periodic;
  - a planted foot stands still to 1e-6 (4+ cm without);
  - no flight, and one frame or more with both feet down at each step;
  - the full 8 % on a short step;
  - the status line.

  Four older tests now name `foot_placement: 0` where they measure the walk's own feet; 111 tests pass.
- **`verify_walk.py`, 66/66 standalone.** New gates 58–65, on Manny's keys:
  - a foot on the ground slides **0.135 cm a frame** at most (the walk's own 0.749);
  - **no frame with both feet moving** (the walk's own: 7, 8, 23);
  - both feet down 2 and 3 frames at the steps (the walk's own 1);
  - at stride 1.3: slides 0.123, both down at every step, and the pelvis drops **5.32 cm** (without
    placement 5.83);
  - under the goblin, every part: slides 0.141, both down 2 / 3, never neither.

  Changed gates:
  - `check()` compares a target's stance against the model's own feet × the size;
  - the Balance gates ask that the point a planted foot rolls about stays put (≤ 0.0001 cm), on the
    frames the model plants it;
  - the two pose-width gates measure with the walk's own feet.
- **Picture:** `docs/superpowers/plans/walkparam/walk_feet.png`.
- **Pelvis drop, placement 1 against 0:**

  | stride | placement 1 | placement 0 |
  |---|---|---|
  | defaults | 0.7 | 0.5 |
  | 1.15 | 0.0 | 1.3 |
  | 1.3 | 4.5 | 5.5 |
  | 1.45 | 11.9 | 11.2 |
  | 1.6 | 21.6 | 18.5 |

## Not built, and seen

- **The goblin pose (knees) dips the swinging toe to the floor mid-swing**: 0.8 cm without placement,
  −0.8 with it. Its turned shin hangs the foot. This was there before and isn't touched here.
- Not built:
  - a ground that isn't flat;
  - a contact found by force rather than height;
  - weight transfer within the double support (the pressure loads a foot by its contact);
  - the roll's limits per character.
