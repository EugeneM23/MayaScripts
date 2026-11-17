# Start/Stop Builder: Pose on clip in the rail, starts too (2026-11-17)

The animator: «У нас где-то был инструмент который обрабытвал старты и стопы анимаций можешь встроить его в
реил?» The tool is **Pose on clip** (`docs/superpowers/plans/poseclip/`, 2026-10-14, spec
`2026-10-14-pose-on-clip-design.md`): a window dropped into a viewport that puts our poses onto a stop clip -
the stop ends in the pose's stance, the run can start on a frame of a cycle, Walk Builder's knobs over it.

Asked, all four the recommendation:
- **stops and starts**: a start (standing, then running) gets its stance where IT stands - on its first steps -
  and can END on a frame of a cycle, the way a stop can start on one;
- **onto the skeleton itself**, Walk / Idle Builder's way: Apply on the selected skeletons, their own keys kept
  on the skeleton, Restore gives them back; a knob released keys the working ones again. No copy beside;
- **poses are Pose Library cards**, dropped into wells (Walk / Idle Builder's `posewell`); the old `.wpose`
  poses are already cards (`Walk poses/`, Walk Builder's migration);
- the card is called **Start/Stop Builder**, in the Animation group after Idle Builder.

## What moves where

The standalone folder goes; the plugin gets a package `SkeldarAnim/maya_startstop/` (a payload row):

| from | to |
|---|---|
| `poseclip.py` (the model) | `maya_startstop/model.py` (`git mv`), posemath from `maya_poselib` |
| `poseclip_maya.py` (the scene) | `maya_startstop/scene.py`, rewritten for the skeleton itself and cards |
| `poseclip_tool.py` (the window) | `maya_startstop/panel.py`, the hub card |
| `posemath.py`, `skeletonmap.py`, the template | gone - the plugin's own (`maya_poselib.posemath`, `maya_skeletonmap`, `assets/manny_skeleton_template.json`) |
| `verify_poseclip.py`, `render_poseclip.py`, `run_poseclip.py` | `docs/superpowers/plans/verify_startstop.py`; the other two gone |
| `tests/test_poseclip.py` | `tests/test_startstop_model.py` |

The plugin's posemath has moved on since the copy (the torso rule, places, anchors): for a whole pose - and
`prepare` refuses a pose without legs and a pelvis - the torso rule is the old one (each torso bone against the
one below it, the pelvis against the root). The verify proves the numbers did not move.

## Starts (the model)

`Analysis.transition`: `"cycle"` with no still stretch, else `"stop"` when more of the clip lies before its
still stretch than after it, else `"start"`.

- **The stance contact** of each foot is the contact overlapping the reference (the still stretch) the most -
  a stop's last, a start's first (`Analysis.stance_contact(side)`). `_Motions` puts THAT contact onto the
  pose's stance; every other contact takes the width by its stillness as before. A stop reads exactly as it did
  (its last contact is the one over the reference).
- **The two poses** were already symmetric in time: the final pose comes in by the stillness, the start pose
  holds where the body runs. The card names them by what they are: the **Stand pose** (the model's final) and
  the **Run pose** (the model's start).
- **A start ends on a cycle**: `end_on_cycle` is `start_on_cycle` run on the clip read backwards (a shim analysis
  with its contacts reversed, the cycle sampled backwards, its travel negated), and the result read forwards
  again: the start's LAST frame is a frame of the cycle, its last `from_cycle` frames go from the start to the
  cycle. A stop keeps `start_on_cycle`.
- Everything else (the reach's cover with its ends held, the balance, the overlap springs from frame 0 at rest,
  the cycle's posture as the run pose) needs nothing.

## The scene

- **Which skeleton**: Walk Builder's `skeleton_root_of` (a rig refused). Apply on the selection's skeletons, else
  the working ones.
- **The source**: the first Apply keeps the skeleton's keys on its top joint (`skeldarStartStopSource`, Idle
  Builder's format: every joint's translate / rotate on every frame, gzip + base64); every later Apply rebuilds
  from it; Restore writes it back and removes it. The clip is rebuilt from it by FK (the joints' orients, rotate
  axes and orders, the root's parent as it stands). Cached per skeleton by the source's hash: the clip, its
  analysis, the statics (bind / Manny's template / as it stands), the poses prepared per card and its time.
- **The cycle**: Use selected reads a looping clip as it stands (its keys through `getAttr(time=)`), one for the
  card, kept by UUID on `sys`. A start ends on it, a stop starts on it, and the Run pose `Clip` is its posture.
- **The write**: every joint's world -> local -> channels (`skelsolve.joint_channels`, nearest the frame before),
  keyed by Walk Builder's `write_curves` (base layer, auto tangents, a driven channel left to its driver and
  named). A weapon driving its bone lets go for the write and takes the new track back (Idle Builder's rule).
  One undo chunk a skeleton. `skeldarStartStop` on the top joint keeps what was applied (cards, knobs, modes).

## The card

Top down:
- the subtitle: the selection / the working skeletons;
- **Stand pose**: a well, Share, chips Torso / Pelvis / Knees / Arms / Feet;
- **Run pose** `[Stand | Clip | Card]`: Stand - the stand pose all along; Clip - the clip's own run posture (with
  a cycle set, the cycle's posture); Card - the second well's card, its Share and chips (shown only then);
- **Cycle**: its line, **Use selected** and **Clear** («a stop starts on a frame of it, a start ends on one»);
- the knobs as Walk Builder's card has them: `[Timing | Legs | Pelvis | Chest | Arms | Weight]` one group shown,
  `[Both | Left | Right]` for the two-sided ones (marked * where the sides differ in Both);
- **Apply** (primary), **Restore**, **Reset**;
- **Skeletons**: every skeleton built, the working ones marked and picked; the right button Pick all, Key the
  picked now, Restore the picked;
- the status (three lines; also the hub's message line).

Everything remembered in `skeldarStartStop_*` optionVars, so the hotkey row `startstop.apply` presses with the
card closed; `window.startstop` opens it. Icon `run`.

## Proof

- `tests/test_startstop_model.py`: the old 58 model tests, plus the transition, the stance contact on a start, a
  start ending on a cycle frame (synthetic clips), and `end_run`;
- `tests/test_startstop_panel.py` on a fake `cmds`: the memory, the sides, the run mode, the wells, the presses,
  the Hold chip; `tests/test_startstop_weapon.py`: the Weapon tab (below);
- `docs/superpowers/plans/verify_startstop.py` - **21 of 21 gates, mayapy standalone**, on Manny UE5 skeletons,
  the goblin and the sword as cards in a temporary library, every clip pressed through `scene.apply` and read
  back off the joints: the stop (`M_Neutral_Sprint_Stop_F_Lfoot`) plays itself with no pose and no springs
  (2.6e-11 cm), the goblin keeps the planted feet (0.0015 cm a frame over the clip's) and every bone's length
  (8.6e-6 cm), the sword's grip held (7.9e-11), the keys the model's, the Weapon tab's gates, one undo, Restore
  (1.1e-13 cm); a START (`AS_am_LongS_OxGuardL_Walk_Fwd_Start`) ending on its loop (`..._Walk_Fwd`): the keys the
  model's, its last frame on the loop's frame placed (1.4e-5), lengths kept before and into the loop; the Creep's
  jog start and stop, which never stand still, read as a start and a stop.

## Not in this version

Rigs; a stand pose per skeleton (the card's poses key every working one); a cycle per skeleton.

## Addendum: the Weapon tab, and what the build changed (2026-11-17)

The animator, before the build was done: «Сразу давай перенесем новый функционал из вкладки wepoan в инструмент
по обработке стартов и стопов новую систему захлестов ... Все отличие стартов и стопов это в том что тут нет
цикла и средней позы тяжело вычислить, но все остальное должно работать по тем же принципам.»

**`maya_startstop/weapon.py`**, Walk Builder's Weapon tab (2026-11-05 / 11-10) on a clip that does not loop:

- **Hold** (a chip, sided, on): the hand rides the chest rigidly at its own offset from it. Walk Builder holds
  the MEAN offset over the cycle; here the offset's **slow part** stands for the mean (`slow_mats`: a Gaussian
  over `SLOW` 8 frames, rotations through their log about each frame, ends held), so a hand going from the run's
  swing into the stance's hold keeps its slow change and loses the swing. It acts where the pose holds the arm:
  per frame by the pose's arm share (`alpha` - the stand pose's where the body stands, the run pose's where it
  runs, none on the clip's own run), and fully on a hand the scene gives a weapon. A held hand takes no arm
  spring.
- **Inherit** (0..1): the share of the chest's own motion the held hand takes, in the ROOT's frame (the clip's
  travel is the root's - there is no cycle to take a line from): 1 all of it, 0 its slow part.
- **Overlap, ms**: the chest the hand rides is this old (the clip's fps); held at the clip's first and last frame.
- **Aim target** (0..1): the blade swung about its grip onto a target keeping that share of its motion about its
  slow part (the root's frame), the scene's weapon the lever, else `weapon_r` 100 cm along +Z.
- **Shoulder** (0..1): the clavicle takes that share of the arm's reach changes about their slow part.
- Two hands holding one thing: the carrier's motion is the rider's (`H_other . inv(H) . want`), the grip kept.
- The card's **Weapon** group; `scene.apply` hands `maya_walk.scene.weapons_in_hands(root)` in; the line
  («both hands ride the chest at 50 % of its motion, 3.0 fr late») ends the status.

What the real clips changed:

- **A start that never stands still** (`model.end_run`): Unreal's starts begin already moving (the OxGuard
  walk start's body at 1.2 cm a frame against 7.8 mid-clip, the Creep's jog start at 4.8 against 14.8) and a
  short stop never settles (the Creep's jog stop ends at 2.9), so `still_run`'s 8 still frames found none and
  they read as cycles. With no still run, an end whose frame moves slower than `END_SHARE` (0.4) of the clip's
  median is where it stands: the run under that speed from the end, at most 8 frames; a last frame repeating
  the one before is not counted. A loop's ends move at 0.86..1.5 of its middle (the slowest point inside a loop,
  0.54).
- **A cycle sampled between its frames keeps its bone lengths** (`Cycle.sample`): it lerped every joint's world
  position, a chord - a start ending on its loop at a fractional phase stood its foot 1.4 mm short. Each bone's
  local turn is slerped and its offset turned now, its length lerped; `_blend_frame`'s offsets the same.
- With no pose the card's default springs (Walk Builder's torso / head / arm drag) still act: on the sprint stop
  the left fingers trail 58 cm. The verify's identity gate names them off.
