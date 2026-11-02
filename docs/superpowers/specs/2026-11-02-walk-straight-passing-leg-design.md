# Walk Builder: a straight stance leg at the passing phase (2026-11-02)

The animator: «почти всегда персонажи после обработки нашими инструментами ходят на согнутых ногах. В фазе
пассинга когда идет реальный человек его опорная нога выглядит прямой или почти прямой, у нас сейчас она
всегда согнута в колене. Мы должны сделать инструмент который будет бережно сохранять нашу походку но
приводить ее к прямой ноге в фазе пассинга ... можешь использовать уменьшение длины шага, растяжение
костей ... всё что нужно».

Asked and answered:
- **the knob only** — nothing straightens by itself, the knob starts at the cycle's own value (the card's
  contract: the defaults ARE the source);
- **the pelvis's lift at the passing is the one automatic lever** — the step is not shortened behind the
  animator's back, and nothing stretches unless its own knob is dialled;
- **walks only** for the advice — a run's stance knee is bent by its own physics, a crouched pose's by the
  pose; the knob still reaches them if it is dialled.

## What is measured, before anything is built

Every number below is from the plugin's own model, headless (`mayapy`), on the animator's own saved cycles
read exactly as Walk Builder reads them (the clean, the mean-pose correction, `gait.engine_knobs` at the
defaults).

**The passing knee today** (the stance leg's bend at the instant the other ankle crosses it; 0 = straight):

| cycle | the clip's own | our defaults give | the hip lift 5 deg wants | the room the legs leave | the drop |
|---|---|---|---|---|---|
| asd | 21.0 / 22.5 | **21.8** | +1.56 cm | 0.94 cm | 0.36 cm |
| dw | | **32.9** | +4.06 | 2.10 | 4.49 |
| TestStrefe | | **37.0** | +4.64 | 3.30 | 6.56 |
| TestDraaft | | **32.5** | +3.98 | 2.34 | 7.15 |
| Sword_Drunked | | 69.1 | +17.05 | 7.10 | 7.60 |
| Creep_Drunk | | 94.4 | +28.58 | 13.83 | 0.74 |
| HavyRun (a run) | | 72.1 | +18.19 | 14.38 | 0.43 |
| RunFast, AGS_Sprint (runs) | | 64.4 / 53.2 | +15.2 / +10.9 | 11.7 / 7.2 | 5.17 / 0.00 |

Three findings decide the design:

1. **The clips themselves walk on bent knees, and the plugin keeps them faithfully.** asd's own passing knee
   is 21.0 / 22.5 deg and our defaults give 21.8 with a drop of 0.36 cm; at `own_knobs()` the output is the
   source. So straightening means going **past the source**, which nothing in the model can do today: every
   leg is capped at `self.reach` — the source's own straightest over the cycle (asd 0.9929 of its length =
   13.7 deg) — and Height's own straightening (`STRAIGHT_KNEE`) stops at 12 deg and only while Height is
   raised.
2. **Near straight the knee is a square root of its reach** (trap 266), so the lever is tiny and sharp:
   **1.2 cm of hip lift takes asd's passing knee from 21 to 5 deg**. At 5 deg a millimetre of hip is 1.5 deg
   of knee. Whatever does this must move smoothly in time or the knee clicks.
3. **A uniform raise cannot do it — the drop's cover eats it exactly at the passing.** Measured, Height on
   the gait defaults:

   | | asd | dw | TestStrefe |
   |---|---|---|---|
   | Height +0 | 21.8 | 32.9 | 37.0 |
   | +1.5 | **23.2** (worse) | 26.4 | 28.9 |
   | +3 | 24.6 | 28.3 | 28.7 |
   | +10 | 19.0 | 31.4 | 22.3 |

   `_lowering` answers a raise by dropping the pelvis back (asd: drop 0.36 -> 1.26 -> 9.50), and
   `smooth_cover` widens, blurs and then **scales the whole curve** by the factor that covers the largest
   need - so a need at the contacts lands as a drop at the passing, where no leg needs it. asd's knee gets
   *more* bent. dw and TestStrefe gain only because Height's own plan shortens the step (x0.85, x0.75).

So the lever must be a **local lift at the stance's middle**, and the cap must give way **there only**: the
contacts keep the walk's own geometry, the passing gets the straight leg.

## The design

### One mechanism: a lift the legs allow, under a cap raised at the passing

The pelvis's vertical offset is already one number a frame (`_lowering`'s `drop`, subtracted in `_body`), so
the straightening is the same quantity with the other sign, computed in the same place, after the drop:

1. **The window.** A planted leg may straighten only around the middle of its own contact:
   `share(r) = smoothstep(r / STRAIGHT_EDGE) * smoothstep((1 - r) / STRAIGHT_EDGE)` over the contact's own
   progress `r` (`_contact_at`), `STRAIGHT_EDGE = 0.3`. Zero at the strike and at the toe-off, 1 across the
   middle 40 %. The window is the cycle's own contact, so Foot placement and Ground time carry it.
2. **The cap gives way inside the window.** `_leg_reach` returns `max(own, own + share * (target - own))` for
   a planted leg, `target` the ratio a knee bent `passing_knee` degrees makes
   (`sqrt(l1² + l2² + 2 l1 l2 cos θ) / (l1 + l2)`), and `_soft_from`'s soft zone gives way by the same share
   (Height's straightening already works this way). Nothing changes outside the window, and nothing changes
   where the ask is not straighter than the cycle's own.
3. **The need.** For every frame and every planted leg in its window, the lift that brings its hip-ankle
   distance to the asked ratio: the quadratic `|q + (drop - x) · up| = target · L` in the lift `x`
   (`q = ankle - hip` at the drop-0 hip, as `_lowering` already holds it).
4. **The allowance.** The same quadratic against each leg's own cap at that frame, for **every** leg - a
   planted one against its cap (the raised one inside its window), one in the air against its own reach, so
   the lift never puts a swinging foot out of reach and never pulls a planted leg past what it is allowed.
   The allowance is what makes the lift taper to nothing at the double supports, where the other leg is at
   its limit: the shape falls out of the geometry, not out of a table.
5. **The curve.** `lift = smooth_under(min(need, allow), sigma)` with `sigma = LOWER_BLUR` of a stride (the
   drop's own blur): the raw curve narrowed to its smallest neighbour within sigma, blurred, then held under
   itself. Smooth, periodic, and never over what a frame allows.
6. `_lowering` returns `drop - lift`. Everything downstream - the legs' solve, Balance's rounds, the bob, the
   body above the pelvis - follows for nothing, because it already reads that one offset.

### `Leg stretch` buys what the legs cannot reach

The lift is bounded by the contacts: on a long step the leg must reach the ground half a step away, and that
is what holds the whole cycle down (dw wants 4.06 cm and its legs leave 2.10). `Leg stretch, %` (sided,
default **0**, nothing stretches unless it is dialled) lets a leg grow where it falls short, so the pelvis
can stay high: in `_lowering`'s need pass a leg's limit is `(1 + stretch)` of its length, and `_leg` solves
with bones scaled by the factor that frame actually needed (`ctx["stretch"][side]`, 1.0 where the leg
reaches). The stretch lands at the **contacts**, where the leg is long - never at the passing, where the leg
is short of its length anyway.

### What the animator is told

- The Pick line says what it did and what is left: «passing knee 6.2 deg asked 5 (the hips lifted up to
  1.4 cm)», and where the legs ran out: «the legs allowed 2.1 cm of 4.1 - a shorter Step or Leg stretch gives
  the rest».
- `gait.diagnose` gains a finding for a **walk** whose passing knee is past `DIAG_PASSING` (18 deg) with its
  fix (`passing_knee` 8), and the existing «a planted knee within 5 deg of straight» finding is silenced for
  a side whose `passing_knee` was asked for - it is no longer a defect but the ask.
- A run or a crouched pose is never advised (`gait.diagnose` already knows the run; a pose's crouch is read
  from `pose_lower`).

### The knob

`Param("passing_knee", LEGS, "Passing knee", "deg", "offset", sided=True, rule=lambda b, leg: (0.0, b))`,
its own value **measured**: the stance knee's bend at the passing instant (`measure`, beside `knee_bend`) -
the frame inside each contact where the other ankle crosses it along the travel, the contact's middle where
a flight leaves no crossing, averaged over the contacts. A slider from 0 (dead straight) to the cycle's own,
starting at its own, so nothing moves until it is dialled - the card's contract.

It is read back by the same measure, so asked 5 reads 5 where the legs allowed it (and the gait read-back
gate measures exactly that).

### What it costs, stated

- **The bob grows** by the lift (asd 7.67 -> ~9 cm for a 5 deg passing knee). That is what a straight
  passing leg is: the body vaults over it.
- **A long step cannot reach it** with the lift alone. The step and `Leg stretch` are the animator's, and the
  line names the shortfall.
- **A dead-straight ask (0 deg) may click**: at 0 the knee's own rate is unbounded. The engine's soft zone
  (`PLANTED_SOFT`, `LEG_MARGIN`) still holds the leg a hair short, and the verify gates the knee's second
  difference at the asked 5 deg against the source's own.
- **The drop's cover is not touched** (it is what eats Height today - finding 3). Fixing that is a separate
  change with a far wider blast radius: every cycle that carries a drop would move. The lift subsumes it
  wherever the animator asks for a straight passing knee. Noted as a follow-up, not built here.

## Isolation

- `maya_walk/model.py`: `smooth_under` (pure, beside `smooth_cover`), `passing_share` (pure, the window),
  `straight_ratio` (pure, the geometry), the lift inside `_lowering`, the cap in `_leg_reach` / `_soft_from`,
  the stretch in `_lowering` / `_leg`, two `info` fields.
- `maya_walk/gait.py`: the `passing_knee` parameter, its measure, `engine_knobs`, the diagnosis.
- `maya_walk/panel.py`: nothing - the card builds its sliders from `gait.PARAMS`.
- The fork `docs/superpowers/plans/gaitbuilder/gaitmodel.py` is held to the plugin's model frame for frame by
  `tests/test_gait_model.ParityTests`: the same change goes into it word for word.

## Verification

- **Unit tests**: `smooth_under` (under its input, periodic, smooth, zero where the room is zero),
  `passing_share` (0 at the strike and the toe-off, 1 in the middle, smooth), `straight_ratio` /
  `bend_of` round trip, the lift's quadratic against a hand-worked case, the knob's own measure on a
  synthetic walker, `engine_knobs`, the diagnosis, the stretch's factor.
- **`docs/superpowers/plans/walkparam/verify_walk_straight_leg.py`** (mayapy standalone, the animator's own
  cycles and both poses):
  - `own_knobs()` and the defaults give the source back **bit for bit** (the knob untouched changes nothing);
  - asked 5 deg on asd / dw / TestStrefe / TestDraaft: the passing knee read back within 1 deg where the legs
    allowed it, and the shortfall named where they did not;
  - the planted feet never slide more than the source's own, the loop closes, bone lengths are exact with
    `Leg stretch` 0 and within the asked % with it;
  - the knee's worst second difference no worse than the source's own (no click);
  - under the goblin and the two-handed sword poses: the straightening works from the pose's own height and
    the pose's crouch is not undone;
  - a run (HavyRun, AGS_Sprint): nothing changes until the knob is dialled, and dialled it straightens;
  - the retarget onto a real skeleton (`target.Retarget`, `fix_pops`) does not bend the straightened knee
    back.
- **Live** in the animator's Maya on port 7006: Pick a walk, dial the knob, read the keys back and measure
  the game skeleton's knee at the passing.
