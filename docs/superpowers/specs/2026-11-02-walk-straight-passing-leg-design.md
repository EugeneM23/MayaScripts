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

## Addendum, the build (2026-11-02)

What the build changed against the design above.

**`Leg stretch` was not built.** The design's second lever — the bones lengthened a little at the passing so
a knee can come straight without the hips rising — cannot reach the scene from the model. The retarget
re-solves every leg itself with the TARGET's own rest lengths (`target._leg` → `model.two_bone(hip, goal,
l1, l2, ...)` with `self.lengths[side]`), and the writer keys rotations, so a per-frame length in the model's
result is dropped on the way out. Carrying it would want `target._leg` reading a per-frame length, the writer
keying the legs' translates, and a word about what Unreal does with a stretched export — a feature of its
own. The knob is therefore not in `gait.PARAMS`, and the line says what the legs left so the animator can
shorten the Step themselves, which is their own call («уменьшение длины шага ... всё что нужно»).

**The lift's rate is the cycle's own.** The design left the smoothness to `smooth_under` alone; measured, that
was not enough — the knee's own second difference grew past the cycle's on TestStrefe (20.7 deg against
12.9). The curve now also moves no faster than `STRAIGHT_SHARE` (0.4) of what the cycle's OWN hips do a frame
(its pelvis's p90 rise, 1.5–7 cm a frame over the saved walks), floored by `STRAIGHT_FLOOR` for a cycle with
no bob of its own. After: 11.8 against 12.9.

**A planted leg pins the hips at its contact's ends** (`passing_window`, the geometry alone, whatever is
asked). Without it a lift the OTHER leg's window allowed straightened dw's own strike by 8 deg — the contacts
are what the animator sees as the walk's weight.

**The ask is aimed at the ankle crossing, not the contact's middle.** The window's shoulders lie near the
double supports, where a leg can be straighter than at its passing; read off the middle, asd's left leg
landed its ask two frames late and came out 8 deg bent.

**The foot's reach roll reads the cap with the straightening off.** A raised cap took the roll away: the foot
stood flat where the cycle rolls it, its ankle 1.7 cm out of place.

**The retarget's own cap had to take the ask** (`target._reach_ratio`, trap 322). This was the whole
difference between a model that landed 8.00 and a scene that read 14.

**What the model cannot do, stated.** The ask is landed by scaling one smooth shape, so a single frame at its
room limit pins the whole curve: on a cycle whose hips barely bob, an ask the room cannot serve can land less
lift than a smaller one would. Measured on the synthetic walker (24 frames, hips 1.55 cm a frame): it lands
an ask up to 7 deg straighter than its own exactly and falls short past that. On every real walk each ask the
legs allow lands exactly (asd's 8 deg to 1e-14) and what they leave is reported as `short`.

## Addendum, 2026-11-02 evening: the pace is in the KNEE's degrees, not the hip's centimetres

The animator, on the Manny skeleton they walked with this feature: «правая нога сейчас почти идеально
работает а у левой не равномерное движение во время выпремления ноги». Reproduced headless on their own
walker (their cycle `own:1f0b1f09338f51c8`, their parameters, the `LongSword_Idle_3P` card, the build
they had installed - 387907e, their own): over its stance the left knee turned **14.14 deg a frame** where
that cycle's own knee turns 9.16, and its second difference 14.39 against 6.91; the right 10.65 / 10.26
against 4.41 / 2.81. On `asd` at an 8 deg ask the same: 15.08 against its own 6.60. So both legs were paced
wrong and the right only LOOKED right - during its stance the room collapses to nothing for five frames (the
left leg's swing is at its reach there), so the right got almost no rise and kept its own motion.

**Two findings.**

1. **The rise comes through two channels, and only one was paced.** `_passing_lift`'s own lift was a third
   of it (1.86 cm of 4.82 on the synthetic walker): the rest is the cap this feature relaxes inside the
   window, which lowers `_lowering`'s own need there, so the hips rise through the DROP. Pacing the lift
   alone left the measured jerk unchanged to five digits.
2. **A rate in centimetres of hip cannot pace a knee.** Near straight a knee is a square root of its reach
   (trap 266), so the one rate `smooth_under` is held to was 2 deg of knee at one frame of the animator's
   cycle and 14 at another. What they watch is the knee.

**The fix** (`model._knee_paced`, called from `_lowering` once both channels have landed): the drop is
computed a second time with the caps as the cycle's OWN (`needs_for(..., plain_limits)`, the cap
`_leg_reach(..., straight=False)` the foot's reach roll already reads), which gives the rise the ask added;
then a sweep LOWERS the hips again, by no more than that rise, wherever a planted asked knee would
- turn faster a frame than it turns under the cycle's own cap, by more than `STRAIGHT_DEG_SHARE` (1.25), or
- dip sharper than the cycle's own corner there (the same share on the second difference) - a straightening
  held at its allowance and then stopped is a corner, and a corner is what the eye reads as uneven.

Lowering the hips can only bend a planted knee, so the sweep only ever lowers them: it settles (24 sweeps,
`KNEE_SETTLED` 1e-4 cm), it cannot put a foot out of reach, and it can only take back what the ask added.
The reference is the knee under the cycle's own cap, not the source clip's: Height, the step, the ground
time and the pose change what a knee does itself by a factor of two on the synthetic walker.

**What it costs, measured.** A couple of degrees of depth for half the jerk, on every saved cycle:

| cycle, ask | before: step / 2nd / least bend | after | the cycle's own |
|---|---|---|---|
| the animator's own, 1 deg (L) | 14.14 / 14.39 / 1.04 | **9.26 / 5.98 / 9.38** | 9.16 / 6.91 / 23.48 |
| the animator's own, 1 deg (R) | 10.65 / 10.26 / 1.04 | **4.92 / 2.32 / 12.74** | 4.41 / 2.81 / 22.41 |
| asd, 8 deg (L) | 15.08 / 11.30 / 8.00 | **6.85 / 8.05 / 8.00** | 6.60 / 6.13 / 14.77 |
| dw, 8 deg (L) | 6.95 / 6.99 / 16.71 | **2.97 / 3.75 / 16.71** | 4.18 / 2.81 / 26.45 |
| TestStrefe, 8 deg (L) | 12.07 / 8.25 / 14.94 | **10.54 / 6.51 / 16.85** | 11.58 / 6.15 / 31.33 |

**Two shortfalls with two cures, and the line says which.** `info["passing"]["paced"]` holds what the pace
took, beside `short`: past half the shortfall the line reads «the pace held it N deg short: a knee turns no
faster than the cycle's own» (the card's own: «N deg left - the knee's own pace»), else the old «a shorter
Step gives the rest», which is the animator's own lever.

**`got` is read off the finished worlds** (`_passing_seen`), at the frames the ask was solved on. Neither
the lift's bisection nor the pace can say it: the pace comes after the bisection, and the body's own carry
(Balance) moves the hip after the drop is done - 3 deg of knee on asd. The verify's own passing frame now
rounds to the frame NEAREST the crossing rather than the one before it: the crossing is a fraction of a
frame and the knee dives 4 deg through it, which is the 3 deg the two readings used to disagree by.

**Proof.** `verify_walk_straight_leg.py` **0 of 58 gates**, every phase, with the smooth phase's own gate
(«the knee is no jerkier than the cycle's own») now measuring 13.1 against 15.2 on asd, 10.8 / 9.8 on dw,
11.8 / 12.9 on TestStrefe, 12.8 / 12.8 on TestDraaft; the target phase's scene knee 18.6 -> 9.2 deg.
`tests/test_walk_straight_leg.py` gained `PaceTests` (the fixture's hips raised 8 cm so its planted legs
stand near their reach - at the lock the knee turned 11.01 deg a frame against its own 4.16, and the test
fails on the build before this), and the wording test on a fixture where the pace is the whole shortfall.
