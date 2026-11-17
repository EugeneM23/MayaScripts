# Walk Builder on a whole clip: its start, its walk and its stop (2026-11-17)

## The ask

The animator, on a start-and-walk clip they had pressed Start/Stop Builder on: «И можем ли мы так сделать что бы
все настройки walk buidler работали пока наш персонаж идет, тоесть как-то определять где старт где стоп кусочек и
где наш цикл. Думаю нам важно это сделать и не делать отдельный start stop builder а научить walk builder рабоать
с стартами и стопами».

Asked, and answered:
- **What comes out**: the same clip, edited - its frames and timing kept; the start part takes the stance rules,
  the walking part every Walk Builder setting, and the two meet smoothly. Works on a start, a stop, or
  start-walk-stop.
- **Timing**: the clip's own. Tempo, Step and Speed (and the other knobs that change a cycle's timing or travel)
  are greyed out for such a clip.
- **Start/Stop Builder**: kept for now, removed once this has been tried.
- **Approach A** (of three): Walk Builder's changes laid over the clip as a difference, faded out where the body
  stands. B (Start/Stop Builder taught every Walk Builder setting) is two models of one body to maintain; C (the
  loop pasted over the walking part) throws the clip's own strides away.

## What exists to build on

- **Walk Builder already reads such a clip**: a walker's own keys that do not loop go through `clean.loop`, which
  cuts the best whole-stride loop out of the clip (`loop_window`: Kovar-Gleicher, the fewest strides) and analyses
  that. Today the result is the LOOP alone - the start and the rest of the walk are dropped. On the animator's
  98-frame clip (left contacts 0-16, 33-46, 63-76, 92-97; right 0-5, 18-31, 48-61, 77-90) it is one stride.
- **`scene.animate`** gives the walker's whole evaluated loop: parameters, the pose, the physics, the rig pose and
  key poses layer, Snap weapon, Head aim - In place last.
- **Start/Stop Builder's model** knows a clip's still part (`still_run` / `end_run`), its transition, its contacts,
  the stance weight `e(f)` (`stillness_at`), each contact's rigid motion onto the pose's stance (`_Motions`), the
  leg IK, the smoothed balance carry and the no-cycle Weapon tab.

## The design

### 1. The clip's parts

`maya_walk/wholeclip.py` (numpy, pure) reads the clip (every joint's world on every frame, the walker's own kept
keys):
- **the contacts** (Start/Stop's `Analysis` feet) and **the strides**: each left heel strike to the next;
- **the walking part**: the strides the loop read as one of its own - a stride whose body speed is within
  `WALK_SHARE` (0.75) of the loop's own; before it the **start**, after it the **stop** (either may be empty);
- **the phase** `φ(f)`: inside a stride, its left strike to the next mapped linearly onto the loop's `[0, P)`; in
  the start and the stop, the phase of the nearest stride continued at the loop's own rate.

The status line names them: «start 0-16, walk 17-90 (3 strides), stop -».

Refused by name: a clip in which the loop finds no whole stride («no whole stride to read the walk from - Start/
Stop Builder takes a clip with no walk»).

### 2. The walk's difference, laid over the clip

`scene.animate` gives Walk Builder's result `R(φ)` of the cut loop and its source `S(φ)` (the cut loop itself,
cleaned, before the model). For every frame of the clip and every joint, in its parent's frame:

    L_new(f) = L_clip(f) . ( L_S(φ(f))^-1 . L_R(φ(f)) )

- turns composed as rotations, offsets added in the parent's frame; the pelvis and the root's place as an offset
  in the root's ground frame (heading kept, the travel the clip's);
- a loop sampled between its frames keeps its bone lengths (the rule `Cycle.sample` got on 2026-11-17);
- **at the parameters' own values the difference is the identity**, so the clip comes out as it went in - the
  card's contract that a parameter starts at the cycle's own value.

Everything Walk Builder does to the loop comes through this one difference: the parameters, the pose card and its
parts, Hold / Overlap / Aim target / Shoulder, the rig pose and key poses layer, Snap weapon, Head aim.

### 3. Where the body stands

The difference is weighted by **w(f) = 1 - e(f)**, the stance weight Start/Stop Builder reads off the centre of
mass's speed (`stillness_at(final_speed)`): 1 while walking, 0 standing still. Where `e > 0` the stance rules come
in from the same pose card and parts (Start/Stop Builder's `evaluate` with the pose, its run pose the clip's own):

    L(f) = slerp( L_new(f), L_stance(f), e(f) )        per joint, offsets lerped with their lengths kept

So a start goes from the pose's stance into Walk Builder's walk as the body picks up speed, and a stop the other
way, with no seam of their own.

### 4. The legs and the balance

Last, on the blended frames:
- each foot's contact is moved by ONE rigid motion (the start/stop `_Motions` rule, its target the blended
  ankle at the contact's middle), blended across the swing - a planted foot never slides;
- the legs by two-bone IK from the blended hips, the clip's bone lengths, the plane read from the hint (trap 245);
- the pelvis sunk where a down foot is out of reach (`cover`, non-periodic);
- Balance as Start/Stop Builder's, the carry smoothed over `CARRY_SIGMA` frames.

### 5. The card

- **A chip «Whole clip»** in the Walk cycle row, shown when Pick reads the walker's own clip and the clip does not
  loop by itself; on by default there; remembered on the walker's memo (`whole`).
- With it on, the parameters that change a cycle's timing or travel are greyed out, with the tooltip «the clip
  keeps its own timing»: Tempo, Step, Speed, Ground time, In place.
- Every other press is as it is: a released knob, a pose card, a part, Snap, Head aim, the rig poses' Update re-key
  the walker's whole clip.
- The status line leads with the parts, then the walk's usual line.

### 6. Keying

The walker keeps its own keys as it does today (`capture_source`; Restore the original keys gives them back). A
whole clip is keyed over the clip's own frame range (not the loop's), every frame, through `write_curves`; the
curves do not cycle. The rig poses and key poses stand in the loop's result as today.

## Proof

- `tests/test_walk_wholeclip.py`: the parts and the phase on a synthetic clip made of a standing start, three
  copies of a loop and a stop; at the parameters' own values the whole clip is the clip (to 1e-9); a parameter
  turned changes the walking frames exactly as it changes the loop (each walking frame equal to Walk Builder's
  result at its phase, to 1e-6, where the clip's strides ARE the loop); w falls to 0 where the body stands; no
  planted foot slides; every bone keeps its length; the refusal.
- `docs/superpowers/plans/walkparam/verify_walk_wholeclip.py`, mayapy standalone: the animator's start-and-walk
  clip (dumped from their scene, not committed), Unreal's `AS_am_LongS_OxGuardL_Walk_Fwd_Start` and
  `M_Neutral_Sprint_Stop_F_Lfoot` on Manny UE5 skeletons through the card's presses: own values the clip, the pose
  card under LongSword_Idle_3P, Arm overlap and Height turned, the walking part showing them and the start / stop
  standing in the stance; no jolt above the clip's own (the second difference of the hips, chest, head and hands);
  no planted foot sliding; Restore exact; one undo.

## Not in this version

Retiming the walking part (Tempo / Step / Speed on a whole clip); a clip of two different walks; turning walks
(a curved path); a whole clip onto another skeleton (the own clip only); removing Start/Stop Builder.
