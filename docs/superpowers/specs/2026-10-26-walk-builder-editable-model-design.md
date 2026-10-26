# Walk Builder as an editable gait model (part 1)

2026-10-26. The animator, with the gait guide (the Claude Doc «Ходьба и бег: полное руководство по анимации
походки», https://claude.ai/artifact/HvcPWpgGbPgHYD5GgsmHwG, revision 18, sections 0-15):

> Давай возьмём этот документ, изучим его и на его базе максимально улучшим работу нашего walk builder. Мне нужен
> инструмент, который сможет проанализировать походку, построить её математическую модель, и при помощи ручек
> управления и умных помощников я смогу настраивать модель, добиваясь более корректного и чистого результата из
> любой походки. Самое главное: я могу взять любую айдловую позу, насадить её на любой цикл, и у меня получится
> корректная анимация.

What is wrong today, in their words:
- most knobs barely change anything;
- it is hard to give a walk weight or change its character;
- the centre-of-mass shift and the automatic balance do not work well;
- the upper body's overlap against the lower body is hard to control;
- the legs do not stretch well in the step. Asked what exactly: all four - the pelvis sinks, the knee clicks or goes
  stiff, the leading leg does not reach forward, the trailing leg does not push off.

Part 2, later: four key poses (contact, down, passing, up) found automatically in any cycle and put on four rigs; editing
them changes the walk's character. This spec is part 1 only.

Asked, in order:
1. **The base**: the plugin's Walk Builder, not today's standalone Gait Builder - «ручки придётся переосмыслить по
   новой. Главная идея walk builder в том, что это математическая модель, которую можно редактировать».
2. **The model against the clip**: decomposition plus details. The analysis splits the clip into named parameters
   and a residual (the clip's handwriting). A knob changes exactly its parameter. A Detail knob scales the residual:
   1 keeps the clip's handwriting, 0 is the clean model.
3. **The helpers**: physics on and fixing by itself (feet, knees, balance, the step); style as advice - a Diagnosis
   panel with the number, the guide's norm and a Fix button that moves visible knobs.
4. **Approach A**: the model rebuilt in place. The engine that works stays (the analysis, steps and contacts, foot
   placement, leg IK, the pose, the retarget onto any skeleton, the wells, many walkers, the mean pose rig); the knob
   layer is replaced by parameters.

Then: «Делай всё до конца».

## Measured before designing (2026-10-26, headless)

The stride harmonics of every body channel (least squares on the stride phase, 4 harmonics), on the animator's saved
walks:

| Clip | Pelvis, trunk, head, arms | Leg angles | What the harmonics leave |
|---|---|---|---|
| asd (walk), HavyRun, sadda (runs), TestStrefe | 97-100 %, residual 0.1-1 deg / 0.1-0.7 cm | 92-99 % | next to nothing |
| dw (drunk: 2 uneven strides a cycle) | 30-80 % | 30-85 % | uneven steps and speed: its character |
| AGS_Sprint (4 strides a cycle) | 90-96 % | 87-97 % | the difference between strides |

So a regular gait is almost all named components (amplitude and phase of the bob, sway, twist, arm swing...). A
special gait keeps its character in the residual, which Detail keeps. Legs, as today, come from the feet through IK,
not from their angles (8 harmonics still leave 2-4 deg: a contact is a corner).

## The design

### 1. The model

**The engine stays** (`maya_walk/model.py`): the analysis, the contacts and foot placement, the leg IK, the roll, the
lowering, the balance carry, the springs, the pose, Leg match. Its knobs stay too and keep their meaning: they become
**engine knobs**, which no animator sees. New engine knobs are added, each defaulting to no change, so every caller of
the engine (Gait Builder's parity tests among them) reads the engine exactly as before.

**The parameters** are new (`maya_walk/gait.py`, numpy): named quantities in units, each measured on a cycle by one
function used for the clip and for the result alike (`gait.measure(walk, worlds)`). Every parameter:
- starts at the clip's measured value;
- maps onto engine knobs exactly (`gait.engine_knobs`), so asked X reads back X wherever physics did not have to give
  way;
- is shown in its unit.

**The decomposition** (in the engine, `Walk._decompose`): every body series the engine samples - the root's and the
pelvis's place against the travel line, the pelvis's, the head's and the world-held upper arms' world turns, and the
local turns of the spine, neck, clavicles, arms and fingers - is split once into
- its regular part R: the mean plus `HARMONICS` (4) stride harmonics (least squares on `stride_phase`, so a cycle of
  several strides is fitted stride by stride);
- its residual E = X - R, orthogonal to R by construction.

The engine then samples `g . R + detail . E`, where `g` is the channel's regular gain (engine knob, default 1) and
`detail` the engine knob Detail (default 1). At g = 1, detail = 1 this is the series itself, frame for frame. A step's
footprint is decomposed the same way (each step's place against the mean step: the stride-to-stride irregularity),
scaled by Detail.

**What reads back exactly**: a measured amplitude is the amplitude of the result's regular part (its harmonics fitted
again). The residual is orthogonal to the harmonics, so scaling R by g scales the measured amplitude by g exactly,
whatever Detail is. Where physics moves the pelvis (a leg that cannot reach) the reading moves with it, and the
Diagnosis says by how much.

### 2. The parameters

**Main** (always shown, above the tabs):

| Parameter | Unit | Engine | Measured as |
|---|---|---|---|
| Tempo | frames a step (steps/min and m/s beside it) | `tempo` = frames a step x 2 x strides | the cycle's length |
| Step length | cm | `stride` = asked / own | the travel / 2 / strides |
| Width | cm | `stance` = asked / own | the mean distance between the left and right prints across the body |
| Bounce | cm | the pelvis height's regular gain `g_bob` | peak-to-peak of the pelvis height's regular part |
| Low point | % of a step after the contact | `bob_shift` frames | where the regular part is lowest, from the nearest heel strike |
| Lean | deg | `lean_add` (spread over the spine, Gait Builder's operator) | the neck_01 - pelvis line from vertical, forward + |
| Arm swing | deg | the upper arms' regular gain (per side) | peak-to-peak of the upper arm's forward angle (world) |
| Arm lag | frames | `arm_lag` (per side): the arm's whole series later | the upper arm's forward extreme after the opposite heel strike |
| Detail | 0-1 | `detail` | - |
| Pose | card + share | as today | as today |

**Macros** (one row under Main). A macro is a layer that moves several parameters: a size parameter by a factor, a
posture or a timing by an offset in its unit (the parameter's own kind, below). The parameter rows show their value
with the macro in it ("Bounce 9.1 cm, Weight +1.5"). Moving the macro back takes its share away; a parameter edited by
hand keeps the hand's value under the macro's share.
- **Speed** (m/s): Step length and Tempo by the clip's own walk ratio, `s = sqrt(WR . v)`, cadence `sqrt(v / WR)`
  (the guide's section 13), so a faster walk takes longer and quicker steps as people do.
- **Weight** (-1 light .. +1 heavy, past 1 to 2): a deeper bounce (x 1.6 at +1), the low point later (+8 % of a step),
  the planted knee a little bent (Knee bend +4 deg), the foot slapping down later (+1.5 frames), the arms and the
  trunk later (+1.5 / +1 frames), a 5 % slower tempo. Negative: the reverse, halved. The numbers are the guide's
  ranges (sections 3, 5, 10) set where they read; they are constants in `gait.py`, one place.
- **Character** (a dropdown) + **Strength** (0-1): the guide's table of section 10 and the emotions as deltas from the
  clip - Natural (none), Bouncy, Double bounce, March, Stroll, Tired, Heavy, Sneak, Angry, Happy, Sad, Afraid. Each
  row of `gait.CHARACTERS` names the parameters it moves and by how much (e.g. Sad: tempo +12 %, step -10 %, head
  down 15 deg, chest forward 8 deg, arm swing x 0.6, sway +20 %).

**Details** (tabs; legs and arms Both / Left / Right as today):

| Tab | Parameter | Unit | Engine |
|---|---|---|---|
| Timing | Ground time | % of the cycle a foot is down | `duty`: each contact lengthened or shortened to it directly (no calibration) |
| | Push-off | deg of heel up at the toe-off | `push`: an extra roll over the ball in the late stance |
| | Heel strike | deg of toes up at the contact | `heel_strike`: an extra roll back on the heel at the strike, gone by the foot-flat |
| | Foot flat | frames from the strike to a flat foot | `slap`: how fast the heel strike's roll goes |
| Pelvis | Height, Forward | cm | as today |
| | Sway | cm, peak-to-peak | the pelvis's side regular gain |
| | Surge | cm | its forward-back regular gain |
| | Double bounce | cm | `double_bounce`: a bob twice a step, its lows at the contact and the passing |
| | Hips twist, Hip drop | deg | Twist and Hip drop as today, now from the clip's own (not people's 5 / 4) |
| | Root on line | 0-1 | `root_sway` |
| Legs | Foot lift | cm | `lift`, solved on the model's own swing (Gait Builder's `lift_scale`) |
| | Toe out | deg | `toe_add` |
| | Swing out | cm | `swing_out` |
| | Knee bend | deg: the least bend of a planted knee | `knee_bend` (Gait Builder's) |
| | Leg match, Leg turn, Knee <-> foot | | as today (a pose's legs) |
| Trunk | Chest twist, Chest sway | deg | as today, from the clip's own |
| | Chest timing | deg of phase against the hips' twist | `chest_phase`: the chest's twist harmonic turned |
| | Chest bounce | deg | `chest_bounce_add` |
| | Torso lag | frames at the chest | `torso_lag`: the spine's series later, bottom up (0 at spine_01) |
| | Gait lean | | as today |
| Head | Head motion | deg | the head's regular gain (0 holds the gaze) |
| | Nod | deg | `nod_add` |
| | Head lag | frames | `head_lag` |
| Arms | Arms forward | deg | `arm_fwd_add` |
| | Elbow, Elbow swing | deg | `elbow_add`, the forearm's regular gain |
| | Arm out | deg | `arm_out_add` |
| | Shoulders | deg | `shoulder_add` |
| | Elbow lag, Hand lag | frames | `elbow_lag`, `hand_lag` |
| Physics | Whip | 0-1 | the springs' overshoot (below) |
| | Foot placement, Balance | on / off | as today |
| Clean | Seam, Smooth, Fix posture | | as today |
| Rig pose | | | as today |

**Overlap is a time shift, not a filter.** Today a spring both delays and damps: half an elbow's swing is lost under
Arm drag 1.5. The lags above shift a joint's whole series in time (exactly, the amplitude kept). The springs stay as
**Whip** only: a spring whose fundamental is compensated - its target sampled ahead by the spring's own phase delay at
the stride frequency and scaled by its gain there - so the stride's swing keeps its amplitude and phase and only the
overshoot and the pivot's jolts are added. Whip 0 is no spring at all. The clip's own lags are what the lag rows show
at the start.

**Pins and physics.** A parameter the animator set is **pinned** and holds its value. A parameter not set **follows
physics** when what it depends on changes, from the clip's own value:
- Sway and Surge (the pelvis's side and forward) follow Width, Tempo and a pose by the balance's linear inverted
  pendulum over the new prints (`pendulum`: a wider stance or a slower step sways more, section 13); pinned, the
  balance's swing term on that axis is off and the regular gain sets it exactly;
- Hips twist and Chest twist follow Step length (the engine's own: the twist grows with the step);
- Push-off and Heel strike follow Step length (a longer step rolls further: `gait.LINKS`);
- Arm swing follows the speed (50-53 deg at 1.43 m/s, 60-65 at 1.75: section 2; `gait.LINKS`).

The bounce is not linked: a longer step already lowers the pelvis at the contacts (the lowering), which is the
pendulum's arc growing; a link would count it twice.

A pinned row is marked in its label; its right button: Follow physics (unpin), Reset to the clip's. Reset (the card's
button) unpins everything.

**One card, many walkers** (as today: the knobs are shared, each cycle unique). A parameter is stored as a change from
the active cycle's own value: a ratio for sizes (Step, Width, Bounce, Sway, Surge, Arm swing, Head motion, Elbow
swing, twists, Tempo), an offset for postures and timings (Lean, Height, Forward, lags, Toe out, Knee bend, Push-off,
Heel strike, Arms forward, Elbow, Arm out, Shoulders, Low point, Chest timing, Nod, Ground time). An amplitude whose own
value is under its unit's `QUIET` (0.5 cm, 1 deg) is stored as an offset. Every walker takes the same ratios and
offsets on its own values; the card shows the active cycle's.

### 3. The helpers

**Physics, always on, fixing by itself:**

1. **The step as a chain of mechanisms** (the guide's sections 2, 12, 13: the legs are not stretched by IK alone). A
   step longer than the clip's (Step length, a pose, a lower body) is made of, in this order:
   - the hips' twist (it follows the step, above): each hip goes forward or back;
   - the trailing leg's push-off: the heel rises and the foot rolls over the ball and the toes late in the stance
     (`push`, following the step);
   - the leading leg's reach: the knee straightens in the terminal swing and the foot lands on its heel, toes up
     (`heel_strike`, following the step);
   - only then the pelvis lowers, in the double support, smoothly (the lowering, as today).

   The knees keep a soft limit (Gait Builder's `knee_soft` 0.04: a leg eases into its reach with no corner), so a leg
   neither snaps straight nor stays stiff. What the chain did is in the result's info.
2. **Balance.** The centre of mass's horizontal path is the linear inverted pendulum over the new prints and timing
   (the engine's `pendulum` of the new pressure), scaled by the clip's own follow (as today), plus the pose's static
   shift brought back over the support. Sway (above) sets its side amplitude; Width and Tempo move it by physics. The
   build measures what is wrong with it today (below) and fixes that; the gate is the guide's rule: the extrapolated
   centre of mass `x + v sqrt(l / g)` stays over the support (Hof), and the side sway reads what Sway asked.
3. **Feet**: foot placement, the roll, the floor - as today (no slides, the toe over the floor).

**Style, advice: the Diagnosis** (under the status line). Measured on the result after every re-key
(`gait.diagnose(measures)`), each finding a line with its number, the guide's norm and a Fix button that sets
parameters (visible, pinned):

| Finding | When | Fix |
|---|---|---|
| Arms in step with the legs | Arm lag under 1 frame (walk) | Arm lag 3 frames |
| The head pecks | the head's world pitch swings over 5 deg (walk) | Head motion x 0.5 |
| The second step is an exact mirror | the left and right arm swings and lags equal within 1 % | Arm swing Left / Right 6 % apart, Arm lag 1 frame apart |
| The hips turn the wrong way | the pelvis turned toward the trailing leg at the contact | Hips twist reversed |
| The chest turns with the hips | Chest timing under 90 deg | Chest timing 150 deg |
| A flat path | Bounce under 2 cm (walk) | Bounce 4 cm |
| No push-off | heel up under 10 deg at the toe-off | Push-off 20 deg |
| The tempo is not the body's size | frames a step off Froude's `1.15 f sqrt(h / g) Fr^-0.2` by more than 40 % | Tempo there |
| Physics gave way | the pelvis lowered more than 2 cm for the reach, a foot short, a knee within 5 deg of straight on the stance | names the parameter that asked it |

A walk is a run (both feet up at a handoff, the engine's `is_flight`) or a walk; the norms are the guide's for each.

### 4. Measured first in the build

Before each helper is changed, its complaint is measured on asd, dw, HavyRun and sadda, plain and under the goblin
and the sword:
- the step: at Step length x 1.15 / 1.3 the pelvis drop, the planted knee's straightest, its second difference
  (clicks), the trailing heel's lift at the toe-off, the leading knee at the contact;
- the balance: the CoM's side sway against the LIPM prediction, the extrapolated CoM's margin, under a pose;
- the overlap: how much of the arms' and elbow's swing the springs keep, and their lag.

The fix is chosen by the numbers and recorded in an addendum here.

### 5. The card

```
[subtitle]
Walk cycle well          Pose well, share, parts
Main:  Tempo  Step  Width  Bounce  Low point  Lean  Arm swing  Arm lag  Detail
Macros: Speed  Weight  Character [dropdown] Strength
[Timing | Pelvis | Legs | Trunk | Head | Arms | Physics | Clean | Rig pose]   [Both | Left | Right]
...the tab's rows...
Pick  [In place]  Reset
walkers list
status (three lines)
Diagnosis: one row a finding, [Fix] beside it
```

Each row a slider in its unit, its range from the clip and the body (as Gait Builder's `rule`), the pinned mark in its
label. The macros' rows show their own value; the parameters show the value with the macros in it.

### 6. Storage and what moves over

- **The card**: `skeldarWalk_param_<name>` (the stored change, a ratio or an offset), `skeldarWalk_pin_<name>`,
  `skeldarWalk_macro_<name>`, `skeldarWalk_character`; the side overrides as today (`param_<name>_l/_r`).
- **A walked skeleton's memo** (`skeldarWalk` on the top joint) goes to version 3: `params`, `pins`, `macros`, plus
  the engine knobs it was keyed with. A version 2 memo is read by translating its knobs (`gait.from_legacy`): stride
  -> Step ratio, tempo -> Tempo, bob / sway / surge / arms / head -> the regular gains, pelvis twist and drop, chest
  twist and sway -> their degrees, overlap -> Arm lag, the drags -> Whip (their largest), weight -> the Weight macro,
  the rest as they are. Nothing is re-keyed until the animator presses or moves a knob.
- The card's old `skeldarWalk_knob_*` values are translated once the same way, and left.

### 7. Speed

One evaluation at the defaults must not be slower than today's (asd 1.03 s). Gait Builder's speed-ups of the same
engine come over (one-vector rotations in floats, still bones answered without the spline, the feet kept per
evaluation, the roll's search in floats, the arms re-swung in a balance round only when the carry moved): 40-45 % of
today's time, at parity (≤ 1e-6 cm with the arms re-swung every round, ≤ 0.1 cm / 0.2 deg as shipped).

### 8. Proof

- **Unit tests** on the synthetic walker of `tests/test_walkmodel.py` and the new `tests/test_walkgait.py`:
  decomposition (R + E = X, E orthogonal to the harmonics, the regular gain reads back), every parameter's mapping,
  links, pins, macros, characters, the ratio/offset storage across two cycles, the legacy translation, the Diagnosis
  rules, the Whip's fundamental kept.
- **Identity**: the parameters at the clip's own values, Detail 1, the physics off -> the clip (≤ 1e-4 cm); every
  walk on disk.
- **Read-back** (headless, `docs/superpowers/plans/walkparam/verify_walk_gait.py`): each parameter set to three values
  in its range on asd, dw, HavyRun, sadda and TestStrefe; the result measured: within 10 % of the asked change or 1
  unit, wherever the Diagnosis reports no physics giving way.
- **Effect**: each parameter over its range moves its body part by at least 5 deg or 3 cm.
- **Physics**: knee clicks (the knee's second difference within 25 deg of straight) at most max(12, 1.5 x the clip's
  own) deg/frame^2 over the Main and Timing ranges; a planted foot's slide and double support no worse than today;
  the extrapolated CoM over the support.
- **The pose on any cycle**: the goblin and the two-handed sword on asd, dw, HavyRun, sadda: the same gates.
- **Maya** (mayapy standalone): Pick on the plugin's Manny UE5 skeleton, a slider re-key, two walkers on two cycles,
  a v2 memo read, one Ctrl+Z.
- Every existing walk test and verify stays green (`verify_walk.py`, `verify_walk_sprint.py`, `verify_walk_own.py`,
  `verify_walk_clean.py`, `verify_walk_meanpose.py`, `verify_walk_many.py`, the Gait Builder parity tests).

### 9. Not built (part 1)

- the four key poses on rigs (part 2);
- curves by phase drawn and edited (a key pose's timing is part 2);
- turns, starts and stops, slopes, stairs, loads as gaits (the guide's sections 10, 12: they need part 2's poses);
- a drag preview: a released slider re-keys, as today;
- Gait Builder stays a standalone experiment; its fork is not removed.
