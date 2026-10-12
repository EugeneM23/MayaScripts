# Parametric walk: the root's drift, the left leg's jitter, the click, the foot under a pose (2026-10-12)

The animator, with Maya open on the port: «1 - Посмотри у нас сейчас в анимации root почему-то смещается и
откланяется в право. 2 - Фут плйсмент вызывает дрожание левой ноги. 3 - если переменить позу двуручного меча
то носок правой ноги и стопа в 11 кадре имеют неприродную форму. Нам нужны какие-то инструменты что бы
корректировать стопу....не знаю как тут лучше поступить, нужно найти решение. 4 - в 27 кадре есть щелчек ноги
его нужно минимизировать».

## What the scene held (read only, over 7001)

- **The keys** are the walk `asd` at the window's knobs, with no pose. Recomputed in the session from its own
  loaded modules, they match the scene to 2.7e-5 cm.
- **The marker on `|root`** holds an older apply instead: the two-handed sword pose with Stance 0.13 and Swing out
  −9.06. Pick would bring that back.
- **The session's modules** are the files on disk (bytecode compared function by function).

## 1. The root drifts right

**Measured:**
- `asd` itself travels (−8.19, 0, 173.04) a cycle: 2.71° to the right of where its root faces.
- Its body faces the same way as it travels: the hips −0.9°, the shoulders −3.5°, the stance feet −2.3° / −3.1°.
- Its root is exactly under its pelvis, so the root weaves with the hips. Measured against the travel line: 0 at
  frames 0–7, 3.7 cm by frame 19, back to 0.
- The transfer carries the travel in the root's axes. So the target walks 2.7° off where it faces, and drifts
  8.2 cm a cycle.

**The fix:**
- **`walkmodel.straightened(clip)`.** A cycle travelling at most `STRAIGHTEN_MAX` (15°) off its root's nearest
  horizontal axis is turned onto that axis, about up through the root's first place. It turns every joint's
  place and every joint's turn but the root's own, so the body faces and goes where the root faces.
  - `Walk.turned` holds the angle and the summary says it («turned 2.7 deg onto its root's facing»).
  - A strafe, or a clip turned further, is left as it is.
  - A walk saved square (Walk_01) is unchanged.
- **Knob Root sway** (`root_sway`, 0..1, default 0; window group Pelvis). At 0 the root runs straight down the
  travel line, which is what a game's capsule wants; the pelvis keeps its sway around it. At 1 the root weaves
  with the hips as the walk does. `own_knobs()` gives 1, so the walk's own knobs still give the source back.

**After:** the root runs at a constant x for the whole cycle, 0.0 cm aside per cycle.

## 2 and 4. The left leg's jitter and the click at 27: one cause

**Measured at a quarter frame** (tempo × 4, the same cycle):
- Foot placement on: the left foot's turning speed jumped 7.9 → 19.8 → 10.8 → 3.5 deg per quarter frame at
  frames 28–28.5, and the ankle's position jerked 6.4 cm.
- Foot placement off: every jump stays under 3.2 deg; this walk's own roughness is about 1.5 cm of jerk.

At integer frames the foot's pitch zig-zagged −82, −65, −79, −74, −79 over 27–31: that is the jitter.

**Two reasons, both in the roll:**
1. **The least roll that reaches is ill-conditioned.**
   - At the toe-off the foot's own geometry turns fast. The chosen roll fell from the cap (30°) to the
     nearest-point branch (10.5°) and to 0 within half a frame.
   - At a heel strike where rolling barely helps, it leapt from 0 to 12° for a 3 mm shortfall.
   - It also stopped dead the moment the foot was no longer "down".
2. **The roll's axis came from the foot's flattened direction**, `up × flat(ball − ankle)`. A foot near vertical
   at the toe-off has no flat direction, and the axis flipped 180° as the foot passed upright. Rolled past
   vertical, the foot (heel over toes) also swung back.

**The fix (`walkmodel.py`):**
- **The axis is the foot's own side** (`foot_side`, read in the foot's frame at mid-contact), levelled.
- **The roll is a trade, not a threshold.** `_roll_cost` minimises `ROLL_COST · angle² + soft(shortfall)²`:
  - `ROLL_COST` is 25 cm²: a radian of roll weighs as much as 5 cm of the leg falling short;
  - the shortfall's weight eases in over `ROLL_SOFT` (1 cm);
  - it is searched on a grid of `ROLL_GRID` (32) and refined;
  - it is searched past the cap and eased into it (from 0.6 of the cap).

  It moves smoothly as the foot moves; where rolling barely helps it stays small and the pelvis covers the rest.
- **`_roll_need` is one signed number** (+ over the ball, − on the heel):
  - the heel and the ball blend by the pivot weight over `ROLL_SENSE` (0.3) about the middle;
  - off the ground the roll fades over the height between `CONTACT_TOL` and `GROUND_TOL`;
  - `_lowering` computes it once a frame (`ctx["rolls"]`), and every leg solve of that frame takes the same.
- **The sole's limit:**
  - no roll stands a sole steeper than `SOLE_HEEL_UP` (65°, which this walk's own toe-off reaches) or
    `SOLE_TOES_UP` (30°);
  - the roll eases into the limit over `SOLE_EASE` (15°) instead of stopping dead.
- **A foot just off the ground** (the first `SWING_EASE` of its swing, `_just_off`) holds the pelvis down no
  lower than its stance already did.
  - The cap matters: trap 227's walker, whose swing path stands 60 cm out of reach, still lowers nothing.
  - So a leg straight at a lift-off leaves its reach tangentially rather than stopping dead.
- **`_growth` tests the lift-off and the first `SWING_EASE` of the swing** (`GROWTH_SAMPLES` 12, bisected). A foot
  held down longer leaves from further behind, and its swing starts there; the old test looked at the lift-off
  instant only.
  - On `asd` at the defaults: double support 1.4 / 2.3 frames (before 2.5 / 2.4), the pelvis drop 0.85 cm
    (0.66).

**After**, on `asd` at the defaults, at a quarter frame:
- the left foot's biggest speed jump is 1.7 deg (11.9 before), its ankle's jerk 0.6 cm (6.4 before);
- the calves' biggest jerk is 2.0 cm (3.3 before); the walk's own is about 1.5 cm.
- Between frames 25 and 31 the foot's pitch now follows the walk's own (the source's swing has a wobble of its own
  there).

## 3. The right foot at frame 11 under the sword pose

**Measured:**
- Frame 11 is the right foot's push-off: heel up 53°, toes bent 55° on the ball.
- Without the pose it is the same: heel up 57°, toes 58°. This walk's own toe-off is steep.
- The pose turns the right leg out about 75°: the foot 73°, the knee with it. So the push-off reads as the heel
  rising sideways across the body.

**Tried and taken back:** unwinding the toe-out to the knee's turn as the heel rises. Measured, it changed the
foot's heading by at most 9° (the knee turns with the foot) and fixed nothing visible.

**The tool to correct a foot: animation layers.**
- `skeldar_walk.write_curves` re-keys the BASE layer (`base_input`): under animation layers it follows the blend
  chain (`animBlendNodeAdditive*`, `inputA*`) to the base layer's input.
  - So a layer the animator keys corrections on stays on top of every slider move.
  - Before this, a layer broke Apply: `connectAttr` onto a plug a blend node already drives.
- A channel driven by anything else (a constraint, an expression) is refused by name before anything is written.
- The workflow: select the foot (and the ball), Anim Layer Editor → Create Layer from Selected, key the
  correction at frame 11 and its neighbours. Every slider move re-keys the walk under it.

**Knobs that already shape it:**
- Leg turn (how far the pose turns the knees and toes out);
- Knee ↔ foot;
- the pose's Feet part.

## Proof

- **`tests/test_walkmodel.py`, 105 tests:**
  - RootTests: a walker skewed 3° and −7° gives back exactly the straight one; a strafe is left alone; the root
    runs straight and Root sway weaves it.
  - RollTests: the roll grows smoothly with the shortfall; a rolling foot turns without a jolt. The old code leapt
    13.2 and 9.5 deg a quarter frame on these walkers; the new one 5.8 and 5.6, under 7.
  - WindowTests: `base_input` under layers, and its refusal.
  - Two older tests now name the walker's own feet (Foot placement 0): it may roll a stance foot about its heel or
    ball, and FootPlacementTests check the pivot.
- **`test_walktarget.py`** green.
- **`verify_walk.py`, standalone**, including a new gate: a +20° correction on an animation layer stays on top
  of a re-key at stride 1.2.
- **Picture:** `walkparam/walk_fixes.png`, before against after: the root from above, the left foot's turning
  speed, the leg at 24–31.
