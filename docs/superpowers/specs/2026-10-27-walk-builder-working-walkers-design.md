# Walk Builder: the walkers Pick chose, edits kept on them, every rig control read, knee pops

2026-10-27. The animator, after trying the key poses:

> Позы плохо обновляются. Вообще тут что-то не так кардинально. 1 - когда мы нажимаем pick это означает что мы
> будем работать с выбраной походкой и все наши изменения попадут на нее в независимости от выделения мы уже
> выбрали цикл. 2 - Текущая походка загруженная из библиотеки не должна пострадать. 3 - нужно убедиться что наша
> анимация реагирует на изменения всех контроллеров риг поз. 4 - давай сделаем какой-то инструмент который будет
> чинить щелчки в колене (перечитай документацию на эту тему нам нужен магический обработчик). 5 - вкладку main в
> плагине нужно выделить как main сейчас не понятно к чему относятся эти настройки 6 - у каждой вкладки должна быть
> кнопка ресет которая вернет к изначальным параметрам. 7 - когда мы меняем анимации на позах то наш цикл должен
> измениться по умному, не знаю как но читай документацию

Asked: after Pick the changes go to **the walkers Pick chose** (or a row clicked in the card's list), whatever is
selected; the edits are kept **on the walker** (the library's card and its cache never change). Everything else was
decided here.

## What was wrong (read off the animator's scene on port 7002, nothing written)

One Manny skeleton on its own cycle, four key rigs, all four `RootX_M` selected and moved.
- **The pelvis was measured from the rig's `root` bone**, which the Pose Library's solve never poses (it follows
  Main / Root_ctrl): the four rigs read the pelvis 27.75 cm "forward" when they were stood, 4.22 cm now - a 23.5 cm
  edit nobody made, written into every key.
- **A straightened IK leg flips its knee**: with the pelvis moved, the Passing and Up rigs' poles stood behind the
  knees; the knee's turn about its leg read 78-161 deg and went into the cycle as an edit.
- **A planted foot's move was dropped** («Step and Width move a planted foot»), so moving a standing IK foot did
  nothing.
- **The rigs stood in the source cycle, the walker showed the parameters, the pose and the physics on top**: an edit
  read back 70 % on the walker (the arms' inertia), and the rigs did not show what the walker does.
- **A parameter moved keyed only the selected walkers** (2026-10-26): with rig controls selected it keyed nobody.
- **The edits lived beside the walk's file**: every skeleton that ever took that card took them.

## 1 - the walkers Pick chose

- A walker's memo carries `"working": true`. **Pick** marks the skeletons it keyed and clears the mark on every
  other walker; a **row clicked in the list** does the same for the rows picked (and takes the first one's settings
  into the card, nobody keyed).
- Every change the card makes - a parameter, a macro, the pose, a part, In place, a walk card, Reset, Fix posture -
  keys **the working walkers**, whatever the viewport's selection. None marked: «press Pick on a skeleton, or click
  one in the list».
- The viewport's selection no longer takes a walker's settings into the card.
- The subtitle names the working walkers; their rows in the list are marked ▶.
- The Rig pose tab's rigs are made for the first working walker.

## 2 - the library's walk is never touched

- A walker keeps its own edits on its top joint, `skeldarWalkEdits` (JSON): `{"walk", "fix": the mean pose's
  correction, "keys": the key poses' edits, "posture": Fix posture on}`. They belong to that walk: Pick of another
  walk drops them, said.
- `scene.load_walk(name, given, edits)` reads the walk under the walker's edits; it reads no file beside the walk any
  more. **Fix posture** turns the working walkers' posture fix on (applied as the walk is read, cached by it); the
  walk's file is never written.
- A walker keyed before this (memo version 3) takes its cycle's old mean pose file once, so it keeps walking as it
  did; the old key pose files are not carried over (read with the broken measure above).

## 3 - every rig control

The rigs belong to a walker (`"walker"`: its UUID, on the rig's memo) and stand beside it.
- **The mean pose rig** stands in the walker's mean pose (its correction in); **the key rigs** stand in **the
  walker's own animation** at its key frames - the evaluated result (parameters, pose, physics, the key edits), its
  key poses found on it (`keyposes.find` of the result read as a walk). What a rig shows is what the walker does.
- A rig is read **in its own Main frame as it stood** (Main and Root_ctrl moved are no pose change; the root held where
  it stood).
- What is read: every game bone above the legs (spine, neck, head, clavicles, arms, fingers, the pelvis's turn and
  move), the toes' turn, each foot, each knee:
  - **a foot in the air**: its move and turn, as before;
  - **a foot on the ground** (heel or ball): its move is its **print** - where it stands for its whole stance -, its
    turn about the point it stands on; flat on the ground, the turn about up (toe out). A lift of a planted foot is
    not taken (said). Mirrored onto the other foot's stances.
  - **a knee**: its turn about the leg's line only while the leg is bent at least 10 deg in both readings and the turn
    is under 120 deg (else it is the IK solver straightening or flipping the leg - said, not taken).
- Kept per walker; `Update` re-stands the rigs that changed in the walker's new animation.

## 7 - the cycle changes "smartly"

The gait guide's knobs are the walk's (section 10: «темп, длина и ширина шага, глубина и место нижней точки,
наклон корпуса...»), and its mechanics hold whatever is edited (contact, down, passing, up; planted feet stay
planted; contacts mirror; never a straight knee). So an Update reads the four rigs' changes since the last Update
and splits them:
- **what moved alike on all four keys is a setting of the whole walk**: the pelvis raised or lowered on all four ->
  **Height**; moved forward or back on all four -> **Forward** (each a change pinned on the parameter; the walk's own
  physics then does the rest: Height straightens the planted knees, then shortens the step). Alike: the same sign on
  all four, each at least 60 % of the largest; the common part is the smallest;
- **what is left is that key's**: put on the walker's animation **after** the parameters, the pose and the physics
  (`keyposes.on_result`), exact at the key, fading to the keys on either side, mirrored onto the other foot's steps,
  each leg solved again onto its foot (prints included) - so the walker shows exactly the rig's pose at the key;
- the knee pop fix (4) runs last.

## 4 - the knee pop fix

The guide (section 12, «Колено щёлкает»): a knee clicks when an IK leg straightens fully and bends at once; never
straighten it fully, lower the root on the frames it is nearly straight; soft IK hides the click but slides the foot.
Built into the retarget, after the target's legs are solved (`target.Retarget.frames`, on the target's own lengths):
- each leg's knee bend per frame; a **click**: a local minimum of the bend under 15 deg whose curvature (the two
  neighbours less twice it) is over 6 deg;
- around each click (±3 frames) the bend may not fall under its own smoothed curve (Gaussian, 1.5 frames): on the
  frames the foot stands, the pelvis is lowered to give the leg that bend (the least drop, smoothed in time with the
  reach's own drop); on the frames it swings, the ankle is drawn toward the hip by what the bend needs (the foot is in
  the air - a centimetre there slides nothing);
- solved again; the status line: «knee pops smoothed: 3 (L 9, 24; R 33), pelvis down up to 0.8 cm».
- The Physics tab's chip **Fix knee pops** (on by default, the card's `knee_pops`).

## 5, 6 - Main, and Reset on every tab

- A heading **Main** with its own **Reset** above the main parameters and the macros; a heading **Details** above the
  tabs; every tab opens with its name and a **Reset**:
  - a parameter tab: its parameters back to the clip's own (their changes and pins);
  - Main: the main parameters, Speed, Weight, the character and its strength;
  - Physics: its parameters, Physics helpers on, Fix knee pops on;
  - Clean: Seam and Smooth back to their defaults, the working walkers' Fix posture off;
  - Rig pose: the working walker's mean pose correction and key edits dropped, its rigs stood again.
- The Reset beside Pick stays: every parameter.

## Build order

1. keyposes: `dumps/loads`; measure in a frame the caller gives; knees (bent, flip); prints; toes; `split_common`;
   `on_result` (the edits on an evaluated result, in place handled). Tests on the synthetic walker.
2. scene: edits on the walker, `load_walk(..., edits)`, the legacy carry-over, apply with the edits and the key
   layer, posture per walker, `working` / `set_working`. Tests.
3. meanrig / keyrig: rigs per walker, stood in the walker's result, read in Main's frame, Update split. Tests.
4. target: the knee pop fix. Tests on a synthetic leg that clicks.
5. panel: working walkers, Main / Details headings, a Reset per tab, Fix knee pops, Fix posture per walker. Tests.
6. Proof: unit tests; a standalone verify (asd and AGS_Sprint on Manny skeletons: Pick, a parameter with nothing
   selected, four rigs, the pelvis raised on all four -> Height, a planted foot moved, a straight knee not read,
   the library walk's file unchanged, a click removed); live on port 7002.

## Addendum: what the build changed

- **The pelvis raised on all four is Height, as far as the legs reach.** asd walks on near-straight legs (0.95 of
  their length mid-stance, the reach's limit 0.993 with the soft zone below it): Height +1 raises it 0.69 cm on
  average, +2 0.85, +5 0.92, +8 2.45 (Height's plan shortens the step to 0.8 there). No step helps at the passing,
  where the leg stands under the hip. So a raise past the reach is said: «on all four: Height +5.0 cm (the walk
  moves +0.9 cm - its legs reach no further, a shorter Step raises it more)»; Height keeps what was asked (as the
  card's slider would), so a lowering after it reads «Height now -5.0 cm, the walk moves -5.7 cm». A lowering is
  kept whole (-5 asked, -4.74 on average).
- **A leg the pelvis pulled straight gives no foot and no toes**: with the pelvis moved, an IK leg past its reach
  drags its foot with the hip (live: 1.4 cm lifts, 0.8 cm prints, 7 deg toes). When the pelvis moved and a leg's
  bend fell under 10 deg, that leg's foot, print, toes and knee are not taken, said («leg_l at Contact is pulled
  straight by the pelvis: its foot and toes not taken»). A foot moved on a straight leg with the pelvis still is
  taken.
- **An IK knee is read only when its pole moved**: a pelvis or a foot moved turns an IK leg's plane by itself (the
  pelvis -10 cm read 1.6-2.3 deg knees, a foot moved 6 cm read 8.5 deg). The rig's memo keeps each leg's FK/IK and its
  pole control's translate as it stood (`keyrig._poles`); a knee turn is the animator's in FK, or when the pole's
  channels changed (`keyrig.knees_taken`). A rig stood by a build before reads every knee.
- The verify `verify_walk_working.py` **23/23 standalone**; the older `verify_walk_keyposes.py` and
  `verify_walk_meanpose.py` call the rigs with a walk's name (the per-cycle files): history.
