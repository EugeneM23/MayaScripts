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
