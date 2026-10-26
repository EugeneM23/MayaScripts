# Gait Builder: Walk Builder and our CAT as one tool, step 1 (standalone)

2026-10-26. The animator: «У нас есть walkbuilder и скрипт который повторяет работу CAT ... сильно много ручек
контроля и тежело для понимания как этим всем управлять, но главное что эти ручки часто не сильно влияют на
финальный результат». Asked for:
1. an analysis of both tools' algorithms and how to improve them;
2. one computation, controlled as simply and as effectively as CAT, with the helpers (knee bend, knee clicks)
   working;
3. Walk Builder not made worse: fewer, stronger knobs, better algorithms, joined with the CAT model.

Step 2 brings the new tools and ideas.

Asked, all the recommendation but one:
- **the base is a clip, CAT on top**: untouched knobs leave the clip as it is; with no clip a CAT preset
  generates one;
- **main knobs + details** by body part, every knob in physical units, starting at the clip's own value;
- **re-keyed when a slider is let go, faster** (~0.3 s), no separate drag preview;
- **a standalone script first** (`docs/superpowers/plans/gaitbuilder/`); nothing in `SkeldarAnim/` changes.

Then: «Делай все до самого конца».

## The analysis (2026-10-26, headless)

Scripts: the session's scratchpad `knobscan/` (`scan.py`, `quality.py`, `clicks.py`, `timing.py`, `prof.py`).
Each knob was swept from its default to each end of its range. The cycle was measured per body group: the rms
change of the joints' world turn (deg) and of their place against the travel line (cm). The sweep ran on:
- Walk Builder: asd, HavyRun, asd + goblin, asd + two_handed_sword;
- CAT: its Walk and Run presets on Manny's template.

**Fewer real controls than knobs.** Each knob's signed change was stacked into a matrix and decomposed:
- CAT, 77 knobs: 90 % of all change lies in 9 directions, 99 % in 29.
- Walk Builder, 38 knobs: 90 % in 5-7 directions, 99 % in 14-17.

**Knobs that sleep** (no effect while another setting is at its usual value):
- CAT:
  - `knee_plant/load/mid/lift` give 0 while `knee_drive` is 0 (it is 0 in every preset);
  - `swing_point` gives 0 while `foot_follow` is 0;
  - `bob_phase`, `head_stabilize`, `push`, `swing_knee` give 1-4° over their whole range.
- Walk Builder:
  - Leg match, Leg turn, Knee <-> foot and Gait lean give 0 without a pose;
  - Foot flat gives 0 until the pelvis is raised;
  - Balance without a pose gives 0.5-1.7° (16° with the goblin);
  - Root sway gives 1.8 cm;
  - on asd, Head, Head drag, Torso drag and Torso bounce give 2.5-3.6° over their whole range.

**Duplicates** (signed effects correlated 0.85-1.0):
- CAT:
  - `lean`, `spine_lean`, `bend_spine_01..04` (six knobs bend the trunk alike);
  - `foot_push` ≈ `swing_reach`, `swerve` ≈ `stance`, `crouch` ≈ -`knee_drive`, `nod` ≈ -`head_stabilize`,
    `elbow` ≈ `hand_bend`.
- Walk Builder: Arms ≈ Exaggeration 0.96, Overlap ≈ Weight 0.95, Leg turn ≈ -Knee <-> foot 1.0.

**Multipliers of the clip's motion are weak where the clip has little of it.** asd's hip drop is 1.1°, so ×3
is still nothing; a noisy clip has its noise multiplied instead. The knobs in units (Twist, Chest twist, every
CAT knob) carry their whole range.

**The ends of ranges.** Arm drag and Arm bounce at the top of their ranges spin the arms 100-128°.

**Helpers.** A knee click was measured as the knee angle's second difference on frames where the knee is
within 25° of straight. The clip's own (asd) is 7 deg/frame².

| | defaults | long step | longer ground time |
|---|---|---|---|
| Walk Builder, asd | 9-10 | Stride 1.4: 20-21 | Ground time 1.3: 0 (the knee kept 35° bent, the pelvis 12 cm lower) |
| Walk Builder, HavyRun | 31-37 | | the clip's own: 19-37 |
| CAT Walk | 8-9 | Stride ×1.4: 28-50 | Ground time +0.15: 37-48 |
| CAT Run, `crouch` -0.06 | | the knee 0.5° from straight: 51-59 | |

The rest of the helpers:
- Balance does not undo the pelvis knobs: Sway and Bob move the pelvis the same with it on or off. Pelvis
  forward loses 15 % to it.
- Foot placement holds a planted foot to 0.0 cm a frame.

**Speed.** One evaluation of asd: Walk Builder 1.03 s, CAT 0.05 s. Of Walk Builder's 1.03 s:
- Balance takes 0.55 s; it re-runs the arms' springs in every one of its rounds;
- Foot placement takes 0.2 s;
- `exp_rot` alone (25 000 small numpy calls a cycle) is a quarter of the whole.

**What each tool is good at.** CAT is a good control language: units, phases, synthesis. Walk Builder is good
physics and style: the clip, planted feet, balance, inertia, poses. So the CAT layer goes on top of Walk
Builder's engine; the reverse would lose the clip's detail, since `catmatch.fit` leaves the legs ~10° and the
hands ~14° off.

## The design: aspects over a clip

An **aspect** is one measurable feature of a gait: the bob in cm, the hip twist in degrees, the arm swing in
degrees, the share of a cycle a foot is down. The tool measures every aspect on the clip; each knob sets one in
its unit. Untouched, every knob holds the clip's own value and changes nothing.

How a knob changes its aspect, by kind:
- **A swing** (bob, sway, surge, hip twist and drop, chest twist / sway / bounce, arm swing, elbow swing): the
  clip's own motion of that series is split into its gait harmonic (its clean shape: twice a stride for the
  bob, once for the sway...) and the rest. The harmonic is scaled to the asked amplitude; the rest (the clip's
  hand) is kept. Where the clip has next to none of it (under `QUIET` of the knob's unit), a CAT shape at the
  norm's phase is added instead. So Hip drop goes from asd's 1.1° to 8° honestly, and noise is never
  multiplied. This is how Walk Builder already does Twist, Hip drop and Chest twist; it now does all of them.
- **A posture** (lean, elbow, arms forward, arm out, shoulders, nod): a constant turn of the difference,
  asked minus measured, on top of the clip's motion.
- **A timing or a size** (speed, step length, ground time, width, foot lift, foot lag): the engine's own
  machinery (stride, tempo, ground time, stance, lift), set from the asked value over the measured one.
- **A helper** (foot placement, balance, follow-through, knee bend on stance): a strength or a target.

The measurement is the same code for the clip and for the result. So every knob is checked to read back:
asked X, the result measures X.

### The knobs

Every knob starts at the clip's measured value. Its range is set from the clip and from the body: the leg
length L, the measured value, sane human limits.

**Main (12):**

| knob | unit | what it does | the engine |
|---|---|---|---|
| Speed | m/s | step length and cadence grow together, keeping the clip's walk ratio (step length over cadence); past the longest step the cadence grows alone | stride, tempo |
| Step length | cm | the step at the same cadence; the speed follows | stride |
| Ground time | % of a cycle | how long a foot is down at a step; under 50 % the feet leave the ground together (a run) | ground_time |
| Weight | -1..+1 | light to heavy: deeper bob and lower body, more knee on the load, a slower strike, more follow-through | weight, Knee bend, Follow-through |
| Bounce | cm | the pelvis's bob | swing |
| Hips | deg | the pelvis's twist; its hip drop follows in the clip's ratio | swing |
| Lean | deg | the trunk forward over the hips | posture |
| Arm swing | deg | the upper arms' swing | swing |
| Width | cm | the feet apart | stance |
| Foot lift | cm | the swinging foot's rise over its path | lift |
| Energy | % | every motion about the mean pose (Exaggeration) | exaggeration |
| Pose | card + share | as in Walk Builder | pose |

**Details** (collapsed, by body part; Both / Left / Right for the legs and arms, as in Walk Builder):
- **Pelvis**: Height cm, Forward cm, Sway cm, Surge cm, Hip drop deg, Root on line (on / off).
- **Legs and feet**:
  - Toe out deg, Swing out cm, Foot lag frames, Ankle flex %;
  - Knee bend on stance deg: the least bend of a planted knee. It is one knob in place of CAT's four knee
    angles and is also the knee-click guard (below).
- **Trunk and head**: Chest twist deg, Chest sway deg, Chest bounce deg, Head steady %, Nod deg.
- **Arms**: Elbow deg, Elbow swing deg, Arms forward deg, Arm out deg, Shoulders deg, Arm timing frames.
- **Physics**:
  - Foot placement (on / off);
  - Balance %;
  - Follow-through frames: one knob for the trunk's, the head's and the arms' springs;
  - Whip: how far they overshoot as they catch up.

  Their ranges are cut to the part that reads (no 100° spinning arms).
- **Clean**: Seam, Smooth, as they are.

**Gone, and where:**

| gone | now |
|---|---|
| `stride`, `tempo` | Speed, Step length |
| `bob`, `sway`, `surge`, `lift`, `stance` (multipliers) | the same in cm |
| `pelvis_rot`, `spine`, `arms`, `elbow`, `head` (multipliers) | degrees, and Energy |
| `overlap` (Weight's duplicate) | Weight, Follow-through |
| `torso_drag`, `torso_bounce`, `head_drag`, `arm_drag`, `arm_bounce` | Follow-through, Whip |
| `leg_match`, `leg_turn`, `knee_foot`, `gait_lean`, `foot_flat` | fixed at Walk Builder's defaults, acting by themselves with a pose |
| CAT: the six trunk-bend knobs | Lean (the spine's shape comes from the pose) |
| CAT: `lift_peak`, `lift_late`, `swing_reach`, `foot_push`, `swerve`, `stance_center`, `foot_height`, `toe_hold`, `swing_toes`, `foot_follow`, `swing_point` | gone (weak or duplicates) |
| CAT: fingers and hands | the pose |

To step 2, as new abilities: heel strike and toe off, step snap (CAT `step_shape`), cross swing, direction,
gradient, a cycle offset, limb phases (a limp), curves by phase.

12 main and 31 details, against 38 + 77.

### CAT presets

`catmodel.generate` on Manny's template makes a cycle; it is wrapped as a clip (Manny's names and bind as its
statics) and from then on is a clip like any other. Its aspects are measured the same way. The presets: Walk,
Jog, Run, Sneak (Strafe and Backward wait for Direction, step 2).

## The helpers

- **Foot placement, Balance, the springs**: Walk Builder's, unchanged in what they do. The springs now hang on
  one Follow-through knob in frames (trunk = arms = F, head = 1.33 F) and one Whip (trunk 0.67 W, arms W).
  Ranges: Follow-through 0..4 frames, Whip 0..0.6.
- **Knee bend on stance**: the least bend of a planted knee. It becomes the reach a planted leg may straighten
  to, and Walk Builder's lowering sinks the pelvis smoothly where a leg would straighten past it.
  - Its default is the clip's own straightest planted knee, so nothing changes.
  - Raised, it sinks the pelvis: CAT's knee angle, made safe.
  - Under it, the legs straighten to the clip's own limit at most; raising the body is Height's job.
- **Knee clicks**: a step longer than the clip's, or a longer ground time, must not click.
  - Measure: the knee's second difference within 25° of straight.
  - Acceptance: at most max(1.5 × the clip's own, 12 deg/frame²) over the main knobs' ranges.
  - The fix is chosen by measurement in the build and written up here.

## Speed

- **Target**: ≤ 0.35 s for one evaluation of asd at the defaults (now 1.03 s), best of three, mayapy.
- **How**:
  - a fork of the model (below), optimised where the profile says;
  - `exp_rot` and the small 3x3 helpers in plain Python;
  - the arms' springs run once per balance round only when the carry moved;
  - vectorised loops where they are per frame.
- **Gate**: the optimised fork against the unoptimised one, the same knobs, every joint every frame: ≤ 1e-6 cm
  and deg, except where an approximation is named.

## Files

`docs/superpowers/plans/gaitbuilder/`:

| file | does | imports |
|---|---|---|
| `gaitmodel.py` | a fork of `maya_walk/model.py`: the same model, faster, with the aspects' operators; its own knobs are Walk Builder's plus the new ones | numpy |
| `aspects.py` | the knob table (main, details, units, ranges from the clip), `measure(cycle)` in units, `engine_knobs(measured, gait)`: the units into the model's knobs; the speed law | numpy |
| `gaitgen.py` | a CAT preset as a clip (catmodel on Manny's template) | numpy, catwalk/catmodel |
| `skeldar_gait.py` | Maya: the window, the sources (saved walks, Walk cycles cards, CAT presets), the pose, Apply to the selection, the re-key on release, the marker `skeldarGait` | cmds + the plugin's maya_walk (files, clean, meanpose, pose, target, scene's readers and writer) |
| `verify_gait.py` | mayapy standalone | |

The plugin's `maya_walk` modules are used as they are; only the model is forked. When the tool moves into the
plugin (later, asked), `gaitmodel` replaces `maya_walk/model.py` and the card's knobs are migrated.

## Proof

- **Identity**: aspects at their measured values with the physics off give the clip exactly, as Walk Builder's
  own knobs do (≤ 1e-4 cm).
- **Parity**: the fork with Walk Builder's knobs gives Walk Builder's result before any helper fix (≤ 1e-6).
- **Read-back**: each knob set to three values in its range, the result measured. Within 15 % of the asked
  change or 1 unit, on asd, dw, HavyRun and a CAT Walk.
- **Effect**: each knob over its range moves its body part by at least 5° or 3 cm rms.
- **Redundancy**: no two knobs' signed effects correlated above 0.85.
- **Helpers**:
  - knee clicks within the acceptance;
  - a planted foot's slide, bone lengths and double support no worse than Walk Builder's at the same values.
- **Speed**: the target above.
- **Maya** (`verify_gait.py`, standalone): a walk keyed on the plugin's Manny UE5 skeleton reproduces the
  model, the loop closes, one undo, a re-key from the stored place.
- **Unit tests**: `tests/test_gait*.py` on the synthetic walker of `tests/test_walkmodel.py`.

## Not built (step 1)

- the hub card;
- a drag preview;
- curves by phase;
- the step 2 list above;
- several walkers at once;
- the mean pose rig;
- Fix posture (the clip's own Clean knobs still work).

## Status at the pause: handed over to another agent (2026-10-26)

The animator, mid-build: «Сохрани весь прогресс в документацию и поставь на паузу. Передам другому агенту на
доработку ... запиши все пояснения и ход работы и план что бы другой агент продолжил с места остановки».

Everything below is committed on `main`; nothing is pushed. Nothing in `SkeldarAnim/` changed, so no build or
release is involved. The plan file `docs/superpowers/plans/2026-10-26-gait-builder.md` holds the task list; its
checkboxes are marked as below.

### How the work went

1. **The analysis** (the top of this spec):
   - every knob of both tools swept headless over its range: `analysis/scan.py`, summarised by
     `analysis/report.py`;
   - the helpers stressed: `analysis/quality.py`, `analysis/clicks.py`;
   - one evaluation timed: `analysis/timing.py`, profiled: `analysis/profile.py`.

   These scripts write their JSON beside themselves. Run them with mayapy from the `analysis` folder; they read
   the animator's walks from `<Documents>/maya/SkeldarWalks` (asd, dw, HavyRun...), which are not in git.
2. **The brainstorm**: the four answers at the top of this spec, then approach A (aspects over a clip) and the
   knob list in "The knobs".
3. **The build**, task by task in the plan (Tasks 1-5 done, 7-8 written, 6 and 9 open). Each task was committed
   with its tests.

### What exists (`docs/superpowers/plans/gaitbuilder/`)

| file | state |
|---|---|
| `gaitmodel.py` | DONE. A fork of `maya_walk/model.py`: the speed-ups and the aspects' operators |
| `aspects.py` | DONE. `measure`, the knob table `KNOBS` (12 main + details), `base_engine`, `defaults`, `ranges`, `value`, `timing`, `speed_law`, `engine_knobs` |
| `gaitgen.py` | DONE. The CAT presets Walk / Jog / Run / Sneak made clips on Manny's template; all four analyse |
| `gaitload.py` | WRITTEN, run only through `gates.py`-like use. Sources (saved walk, card, preset), the clean, the baseline cache, `evaluate` |
| `skeldar_gait.py` | WRITTEN, compiles, NEVER RUN (not in a GUI Maya, not in mayapy) |
| `gates.py` | DONE. Headless gates on real walks: parity, speed, identity, readback, effect, redundancy, clicks |
| `analysis/` | the analysis scripts and the gate results of 2026-10-26 (`analysis/results-2026-10-26/`) |

`skeldar_gait.py` holds the window and Apply onto a selected skeleton: `maya_walk.target.Retarget`, the memo
`skeldarGait` on the top joint, a re-key on a slider's release, the source / pose / parts / Both-Left-Right
controls.

Tests: `tests/test_gait_model.py`, `tests/test_gait_aspects.py`, `tests/test_gait_operators.py`, 28 tests, all
green. Run them with:

```
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_gait_model tests.test_gait_aspects tests.test_gait_operators
```

Gates:

```
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/gaitbuilder/gates.py <parity|speed|identity|readback|effect|redundancy|clicks|all> [asd dw HavyRun cat:Walk]
```

Each gate on one walk runs 1-5 minutes; run them in parallel, one process per gate and walk.

### Decisions taken in the build (keep them)

- **A fork, not a subclass**, of Walk Builder's model, so its internals can be optimised and extended freely.
  When the tool moves into the plugin (asked later), `gaitmodel` replaces `maya_walk/model.py` and the card's
  knobs are migrated. The other `maya_walk` modules (files, clean, meanpose, pose, target, scene, cards) are used
  as they are. `pose.prepare(walk, statics, bones, model, target)` takes the model module, so it is given
  `gaitmodel`.
- **The knobs are relative to the walk** (`engine_knobs`):
  - every engine value is the walk's own plus a difference;
  - an untouched knob changes nothing exactly (`MappingTests.test_own_values_are_the_walk`);
  - a knob's default is what `measure` reads off the walk evaluated at `base_engine(walk)`: Walk Builder's
    defaults, but with the walk's own twist, hip drop and chest twist / sway.

  Walk Builder's own defaults set those to people's norms (5, 4, 7, 5); Gait Builder starts at the clip. The
  helpers stay on at their defaults: Foot placement, Balance, the springs.
- **A swing is added in phase with the walk's own** (`aspect_phase`, its gait harmonic's phase): "+2 cm bob"
  grows the walk's bob by 2 cm and keeps the rest of its shape.
- **Ranges come from the walk** (`Knob.rule(base, leg)`).
- **Speed** keeps the walk ratio: step and cadence both grow as √speed, and past the step's range the cadence
  takes the rest. The window stores `speed` and `step`: a Speed press drops `step`; a Step press stores both,
  keeping the cadence (`skeldar_gait._knob_changed`).
- **Hips**: when it is moved and Hip drop is not, the drop follows in the walk's ratio.
- **CPU time, not the wall clock**, for speed: this machine runs Unity beside Maya and the wall clock swung
  ±40 %. Speed is gated as a share of Walk Builder's time in the same run (`SPEED_SHARE` 0.45) or ≤ 0.35 s.

### What the fork changed against Walk Builder

**Speed** (asd 0.98 s → 0.38-0.56 s CPU; 43-45 % of Walk Builder's on asd, dw, HavyRun):
- `exp_rot` of one vector in plain floats (it was a quarter of the time);
- `_frame` of `align` and `_unit` in floats; `np.cross` in the legs replaced by `_cross3`;
- a bone whose place in its parent never moves (`LT_STILL` 1e-5 cm) answers its place without the spline;
- `_foot_free` kept per evaluation (`ctx["_feet"]`): a third of the foot targets were repeats;
- the roll's golden-section search in floats;
- **the one approximation**: in a balance round the arms swing again only when the carry moved more than
  `ARM_RECARRY` (0.1 cm). Against Walk Builder that is ≤ 0.06 cm and ≤ 0.15° on asd, dw and HavyRun; exact with
  `ARM_RECARRY` 0 (`ParityTests`).
- Tried and dropped: a `periodic_cr` cache keyed by `id(table)`. Each `self.pdev[j]` is a new view object, so
  the cache missed every call and was slower.

**The aspects' operators** (new engine knobs, all defaulting to no change; `ASPECT_KNOBS`, sided ones in
`SIDED`):
- the pelvis: `bob_add`, `sway_add`, `surge_add` cm, in `_body`;
- the trunk and head: `lean_add` (spread over the spine joints, divided by the measured `lean_gain`),
  `chest_bounce_add` (the chest-share joints), `nod_add`;
- the arms:
  - `arm_swing_add` and `arm_fwd_add` (a world turn of the upper arm about -lside);
  - `arm_out_add` (about ±ahead);
  - `elbow_add` and `elbow_swing_add` (about the elbow's hinge, measured in the upper arm's frame);
  - `shoulder_add` (the clavicle);
  - `arm_lag_add` frames;
- the legs: `toe_add` deg (into the feet's toe turn) and `knee_bend` deg (it caps the planted leg's reach;
  the lowering sinks the pelvis).

The turns are added in `_frame` by `aspect_turns`; `aspects_on(k)` switches the work off when all are 0.

### Gate results at the pause (`analysis/results-2026-10-26/`)

**Identity**: the physics off gives the clip to 0.0002 cm / 0.05°, exactly as Walk Builder's own knobs (asd,
CAT Walk).

**Speed**: 43-45 % of Walk Builder's CPU time.

**Readback** (asked change against measured change, 43 a walk). It passes 35-39 a walk; the failures:

| knob | the walks | asked → got |
|---|---|---|
| `duty` | all four | +6.35 → +4.84 % on asd: Walk Builder's ground time multiplies the contact, not the duty |
| `lift` | asd, CAT Walk | +6.24 → +4.37 cm |
| `chest_bounce` | all | +2.4 → +0.07: broken under the trunk spring, see "Next" 1 |
| `elbow_swing` | HavyRun, dw | +5 → +2.3: the arms' springs filter it |
| `arm_out` | HavyRun | +10 → +4.2 |
| `knee_bend` | HavyRun, dw | overshoots: +9 → +19.6 |
| `elbow` | dw | −4.4 → −3.0 |

**Effect** (each knob over its range): the failures:
- `root_line` 0-2.3 cm (a switch);
- `chest_sway` 4.0-4.3° on asd and HavyRun (a spine-group rms dilutes it);
- `chest_bounce` 2.9-3.7° (the bug);
- `head_steady` 0.4-1.7° where the walk's head is already steady;
- `balance` 0.4-2° without a pose.

**Redundancy**:
- `weight` ~ `follow` 0.93, `weight` ~ `arm_timing` 0.90, `arm_timing` ~ `follow` 0.88;
- `speed` ~ `step` 0.85;
- `forward` ~ `balance` 0.90 (HavyRun).

The real dimensions are now 22-24 for 90 % and 30-33 for 99 % (were 5-9 and 14-29).

**Clicks** (limit max(12, 1.5 × the clip's own)), in deg/frame²:

| walk | over the limit |
|---|---|
| asd | step high 27.8, duty low 20.8, lift high 20.2, speed high 26.9 |
| CAT Walk | defaults 34.0, step high 47.4, bob low 25.4, lift low 20.4, lift high 48.5, speed high 49.7 |
| dw | step high 31.4, lift high 25.4, speed high 44.2 |
| HavyRun | none |

### Next, in this order

1. **Chest bounce under the trunk spring.** It reads back with the springs off (`tests/test_gait_operators`,
   QUIET) and gives ~0 with Torso drag 1.5.
   - `_body_dynamics` takes the chest as `kin[spine[-1]]` from the frames (bounce included), springs it and
     spreads the difference over the spine (`_spread_turn`). Find where the oscillation is lost.
   - Suspects: `_spread_turn` / `_reattach` writing the frames' own turn back; or the spring's lag putting
     the 2×/stride bounce out of phase. A 1.5-frame lag on a 15-frame period should not.
   - Print the top spine joint's pitch series before and after `_body_dynamics` on asd with
     `chest_bounce_add` 5.
2. **Readback gains.**
   - **lift**: map through the height above the take-off / landing line. `foot_target` scales `lift_up`, the
     height over the straight line between the foot's off and on places. Add `lift_line` per side to `measure`
     (the swing's max over that line) and set `lift = 1 + (asked - base) / lift_line`.
   - **duty**: Walk Builder's `ground_time` lengthens each contact past its step and is capped by the swing's
     room, so it is not linear in duty. Calibrate once a walk: evaluate at ground time 1.15 and 0.85 at load
     (cache with the baseline) and interpolate duty → ground time.
   - **elbow swing** under the springs: the same probe-calibration, or scale by the springs' measured gain at
     the stride frequency.
   - **arm out**: turn about `unit(arm_dir × (sign · lside))`, where `arm_dir` = the lowerarm's mean local
     translation through `rots[upper]`. About `ahead`, an arm pointing forward cannot go out (a run). Keep
     Arms forward about −lside: it reads back exactly.
   - **knee bend**: `smooth_cover` in `_lowering` drops the pelvis more than the cap needs, so the knee ends
     bent more than asked. Either gate it as a lower bound (the knob says "at least") with a stated slack, or
     cover the need more tightly where `knee_bend` drives it.
3. **The knob set** (redundancy and effect):
   - Remove the arm lag that Walk Builder's `weight` carries:
     - `ctx["lag"] = overlap + WEIGHT_LAG · weight` in `evaluate`;
     - add a fork knob `weight_lag` (default 1, Walk Builder's) and set it to 0 from `engine_knobs`;
     - drop `WEIGHT_FOLLOW`;
     - Weight is then the bob shape, the clock warp and the knee bend.
   - Remove the `arm_timing` knob: Follow-through covers it, at 0.88.
   - In `gate_redundancy`, exempt the declared macro pair (speed, step) and the helpers (placement, balance).
   - In `gate_effect`:
     - measure the max over the group's joints of each joint's rms, not the group rms (a chest knob moves
       the top joint far and the lumbar little);
     - exempt the switches (`root_line`, `in_place`, `placement`);
     - report `head_steady` and `balance` as "acts only where the walk / pose has it" rather than fail.
     - Or hide such knobs when they cannot act: hide Balance without a pose; hide Head steady when the walk's
       head moves under 3°.
4. **Knee clicks** (plan Task 6).
   - The failures are long steps, fast speeds, a high or low lift and a short duty, plus the CAT Walk at its
     defaults (34). The straightest knee sits at the reach limit (12.2-13.9°) in every failure. So the knee
     dwells at the cap and enters and leaves it sharply: trap 266, a knee near straight is the square root of
     its reach.
   - Look by frame where the second difference peaks (bend series, `drop` from `info["drop"]`, the roll).
   - Candidates:
     - an extra margin that grows with the asked step beyond the clip's (the knee kept ≥ the clip's own
       straightest + a few degrees when Step / Speed / Lift go past the walk's);
     - a smoother cover in `_lowering` (wider sigma when the cap is hit on many frames);
     - the `rate_limited` roll applied to the reach as well.
   - Acceptance as in the spec; re-run `gates.py clicks` for all four walks.
5. **The Maya window** (plan Task 8):
   - Run `skeldar_gait.py` in a GUI Maya.
   - The animator opened port 7001 for this session. Their scene then was untitled and modified: a
     `Manny_Skeleton_Character` walked with the asd card at Walk Builder's defaults. It was only read.
   - Ask before writing into their scene; prefer a disposable Maya or mayapy.
   - Write `verify_gait.py` (mayapy standalone, `verify_cat.py`'s shape: `ma_import` of
     `SkeldarAnim/assets/Manny_Skeleton.ma`):
     - Apply a saved walk and a CAT preset;
     - the keys reproduce `gaitload.evaluate`'s worlds through the retarget;
     - bone lengths kept;
     - the loop closes;
     - one Ctrl+Z;
     - a re-key from the stored place does not drift;
     - a knob changed re-keys;
     - a pose card at a share.
   - Known risks in the window code:
     - `_source_chosen` keeps only the non-measured knobs (intended);
     - `sources()` / `pose_cards()` read `maya_poselib.store.cards(...)[0]` (`Card.path`);
     - `apply` reuses a memo's place across sources (check that a new source on a walked skeleton keeps its
       place);
     - `_build` reads `wc.knobs(state["clean"])` for Seam / Smooth.
6. **Gates again**: all seven on asd, dw, HavyRun, cat:Walk. Then add `goblin` / `two_handed_sword` pose runs
   (they need the pose path in `gates.Bench`: `pose.prepare` with the fork, as `analysis/scan.py`'s `run_wb`
   does).
7. **Write-up**:
   - an addendum here with the final numbers;
   - a "Gait Builder (standalone, 2026-10-26)" section in CLAUDE.md (where it lives, the decisions above, the
     traps below);
   - the plan's checkboxes.

### Second session, paused again (2026-10-26, evening)

Done ("Next" 1 and 2), committed on `main`, not pushed:
- **Chest bounce was a measurement bug, not the spring.** `aspects._pitch_series` and the model's chest phase read
  the turn as `r . mean^T` (in the spine joint's own axes); asd's spine_05 stands ~90 deg off the world, so 5 deg
  read 0.13. Now `mean^T . r` (the world's pitch): +5 asked reads +5.0 with the springs off, +4.55 under them.
- **Foot lift** is solved exactly on the model's own swing (`Walk.lift_profile`: each swinging frame's height and
  foot_target's lift_up; `aspects.lift_scale` bisects the convex max). A profile read off the result's contacts
  overshot 17-34 %.
- **Arm out** turns the upper arm about `arm_dir x side` (`Walk.arm_dir`, `ARM_OUT_AXIS`): about the body's front
  a run's forward arm only spun about itself.
- **Knee bend** caps only a PLANTED leg (`ctx["stance_reach"]`, `Walk._leg_reach`), from the straightest knee over
  the MODEL's planted frames (`aspects.annotate`, `base["_knee_planted"]`, read off `result.info["placement"]`).
  Capped on both legs, a run's swinging leg was drawn in (3x overshoot); capped from the measure's own, HavyRun's
  push-off frame jumped 5-7 deg at the first ask. A soft cap (by the ground weight) was tried and dropped:
  HavyRun then under-responded.
- **Duty** is measured to a fraction of a frame (`Cycle.margin` / `down_share`: a 26-frame run is 3.8 % a frame).
- **Response curves** (`aspects.calibrate`, CALIBRATED = (duty, elbow_swing), (knee_bend, elbow); PROBES, and
  KNOB_PROBES for knee_bend): each source probed once out to its range's ends, `base["_curve"]`; the asked change
  goes through `_inverse` (past the reach: the first asked reaching it, never the end - a run's right elbow swing
  turns back and grew the wrong way); a Both ask through the sides' MEAN curve (`_calibrated_sides`: the legs
  share the pelvis); the range cut to what the walk reaches (asd's duty floor ~53 % under Foot placement; a run's
  elbow swing). Probed together, arm and leg knobs read within 6 % of alone (measured).
- **Elbow swing's range** stops at the elbow's bend (past it the unsigned bend folds back).
- **A sided knob moves each side from its own** (HavyRun's planted knees straighten to 52 and 15 deg): `gates.Bench.ask`
  / `change`, and the window's Both (`skeldar_gait._knob_changed`) for a measured knob.

Numbers: readback **172 of 172** on asd, dw, HavyRun, cat:Walk (was 152); parity and identity unchanged; speed
alone 27 % (HavyRun) / 44 % (asd) of Walk Builder's. 38 unit tests green (`test_gait_*`).

**Open, before the rest of "Next":**
- **The calibration is slow**: 9 evaluations a source - asd 6.5 s CPU, dw ~30 s (one dw evaluation ~3.3 s under
  load). Too slow for the window's source load. Options: cache it on disk per walk file (mtime) and pose; fewer
  probes (elbow needs only +-1); a lazy curve per knob on its first move; speed up the evaluation (profile dw).
- The baseline is still keyed by pose share in `gaitload.baseline`, so a share change recalibrates: key the
  curves by source and pose only.
- Then "Next" 3 (the knob set), 4 (knee clicks), 5 (verify_gait.py), 6 (all gates), 7 (write-up). The effect and
  redundancy gates were not re-run after this session's changes; the ranges of the calibrated knobs are now cut
  to their reach, so effect numbers may move.

### Third session, paused (2026-10-26, afternoon)

Done, committed on `main`, not pushed (`ac7444c`, `2026e84`, `6e0636b`, and the verify / preset test):
- **The calibration once a walk, on disk.** `gaitload.curves(source)`: probed with no pose (a pose's share changes
  the walk's own values, which the baseline measures again, not how far a knob moves them) and kept on the source
  and in `<maya>/SkeldarGaitCache/<sha1>.json`, named for the walk file, its clean, its mean pose correction and
  the code's mtimes. A first read 3-17 s CPU (13 evaluations), again 0.4-1.5 s, a share change one evaluation.
  Under the goblin and the sword the share-0 curves read back wherever a posed calibration does (a two-handed
  grip holds the arms' swing either way). The window says so and shows a wait cursor on a first read.
- **The knob set.** Weight no longer carries Walk Builder's arm lag (fork knob `weight_lag`, Gait Builder 0;
  `WEIGHT_FOLLOW` gone) and bends a planted knee 6 deg, not 12 (12 duplicated Knee bend, 0.86 on dw). Arm timing
  is gone. Gates: effect is the most one joint of a group moves; switches not gated; Head steady needs what the
  walk's head has; Balance gated at the widest stance and under the goblin (17-18 cm); redundancy names the
  pairs by design (Speed~Step, the helpers). The bench takes a pose (`Bench(name, pose)`).
- **Knee clicks: 52/52** (were 14 failing). A soft limit (fork knob `knee_soft`, Gait Builder 0.04): a leg past
  max(the source's own stretch, 96 % of its limit) eases into the limit with no corner (`soft_reach`); the
  lowering and the growth aim at that start. Step, Speed and Ground time stop where the pelvis is down 15 % of
  the leg (`DROP_MAX`, probed in the calibration): past it a lunge whose swinging knee snaps. The click limit
  follows the cadence squared. `smooth_cover` treats a need under 1e-9 as none.
- **`verify_gait.py`: 33/33 in mayapy standalone** (the keys reproduce the model through the retarget to 3e-5
  cm, lengths constant to 7e-6, the loop closes, Speed and Step read back on the keyed skeleton, the place kept,
  one Ctrl+Z, the goblin lowers asd's pelvis 92.3 -> 68.8, 81.0 at 0.5, the disk cache read again).
- **The CAT presets as clips** (`tests/test_gait_gen.py`): close, their step exact, their duty within a frame.

**Open, in this order:**
1. **The window in a GUI Maya.** A disposable Maya (scratch `MAYA_APP_DIR`, port 7061 by a userSetup in
   `<app>/2027/scripts`) opened its port in 6 s, but the first send ran nothing in 120 s (cause not found: Maya
   may not have finished starting; check its CPU and a two-line print first). The phases are written:
   `docs/superpowers/plans/gaitbuilder/verify_gait_window.py` (open, Apply's own command, a slider's changeCommand,
   Left alone and the `*`, another source through the menu, Reset, a DWM picture, a re-drop) - a runner per phase.
2. **Every gate again** on asd, dw, HavyRun, cat:Walk after this session's changes (readback was 172/172 before
   `knee_soft` and the cut ranges; parity, identity, speed, readback, effect, redundancy), then under the goblin
   and the sword (`Bench(name, pose)`).
3. **Write-up**: the final numbers here, a CLAUDE.md section, the plan's checkboxes.

### Traps met in this build

- **`a` is the pose's share inside `Walk._frame`'s joint loop** (`pose, a = ctx["pose"], ctx["alpha"]`). A
  stride phase kept in a variable called `a` was overwritten to 0, and every swing operator added a constant.
  The fork calls it `stride_a`.
- **An elbow's bend read as an angle is unsigned**: a swing through straight folds back, and the read-back
  halves. Test elbow swings about a bent elbow.
- **A bob added upward is cut by the legs' reach** where the legs are near straight at mid-stance. That is
  the pelvis's drop, by design. Test bob increases with the pelvis lowered.
- **`periodic_cr` tables are numpy views**: `self.pdev[j]` is a new object each call, so a cache keyed by
  `id()` never hits.
- **Bash heredocs of long Python with backslashes break** (trap 198). Write patch scripts with the Write tool
  and run them.
- **The wall clock on this machine swings ±40 %** (Unity running): time with `time.process_time`, against Walk
  Builder in the same run.
- **The synthetic walker's hip twist reads negative**: its twist is out of phase with its feet's split. Ranges
  must allow negative Hips (the `hips` rule does).
