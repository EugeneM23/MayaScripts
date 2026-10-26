# Walk Builder: the cycle's four key poses on four rigs (part 2)

2026-10-26. The animator, after Height was fixed the same day:

> После того как доделаешь это задание реализуй мою идею о ключевых позах, повторю суть. Мы находим в нашем цикле 4
> ключевые позы через которые строится походка или бег, выносим эти позы каждую на свой риг и изменяя риги
> контролируем весь наш цикл а умные обработчики нам помогают. Для этой фичи давай сделаем отдельную кнопку как сейчас
> для создания одной средней позы.

Then: «Порт 7002 открыт для тебя. Делай все до конца я отойду на 2 часа вернусь и проверю». Every choice below was taken
alone; part 1 is `2026-10-26-walk-builder-editable-model-design.md`, whose «Not built» listed this.

## What it does

- **Rig pose tab, a Key poses row** - Create, Reset, Delete - beside the mean pose's own (Create, Reset, Delete) and
  one **Update** for both.
- **Create key poses** adds four Manny [rig]s in a row beside the first walker on the active cycle (x - 150, - 260,
  - 370, - 480 cm; the mean pose rig stands at + 150), each labelled «asd - Contact (frame 9)» and stood, through the
  Pose Library's solve with no keys, in its key pose of the cycle as it now is (every edit so far in it). Its legs
  stand in IK. Pressed again: the cycle's own four are posed again.
- **Update** reads every rig pose and every key rig; a key rig's change goes into its key; the rigs that changed are
  stood again in what the cycle now does at their key; the walkers on the cycles that changed are keyed again once,
  each with its own settings.
- **Reset key poses** drops the cycle's key pose edits and stands its key rigs in the plain key poses; **Delete key
  poses** takes the four rigs out (the edits stay).

## The four key poses

Found by `maya_walk.keyposes.find(walk)` in every step (a foot's heel strike to the other foot's), from the walk the
mean pose's correction leaves (so an edit never moves its own key):

| key | where |
|---|---|
| Contact | the heel strike (the model's contact) |
| Down | the pelvis lowest between Contact and Passing, kept 35 % of that span away from both |
| Passing | the swinging foot passes the standing one along the travel (a strafe: where they come nearest) |
| Up | the pelvis highest between Passing and the next contact, kept 35 % away - a run's flight peak when it has one there |

**Why not the raw extremes or gait events**: a mocap pelvis is flat about the contact - asd's lowest frame was the one
after Contact, its highest the one after Passing, and its trailing toe-off a frame after the strike - so Down and Up
sat a frame from their neighbours and an edit at Contact fell to nothing in two frames. Kept 35 % in, asd reads 9, 12,
17, 20 of a 16-frame step; dw 12, 21, 37, 42; HavyRun 10, 12, 14, 19 (Up its flight); a pelvis moving under 0.2 cm
in its window takes the window's middle. A step under 4 frames is refused by name, as are feet that do not take turns
and a walk whose steps the model could not read.

The rigs show **the first step of the left foot**. A step of the right foot takes the same edit **mirrored** across
the walk's middle (`reflection`: the side axis flipped): the left arm's turn at the left contact is the right arm's at
the right contact; a middle bone's turn is mirrored onto itself; the pelvis's side move flips; a knee's turn changes
sign; a foot's move and turn go to the other foot, mirrored. A cycle of several steps a foot (dw) takes each key's edit
at every one of its steps.

## What a key rig's edit is

Read off the rig the way the mean pose's is (`meanrig._read`: its game skeleton carried onto the walk's skeleton, the
limb bones in their drive), against the base it was stood in:
- **the upper body's turns** (the mean pose's bones: pelvis, spine, neck, head, clavicles, arms, fingers): a local
  turned to now = base · Y adds Y in the bone's parent frame;
- **the pelvis's move** over the root, in travel coordinates (forward, side, up);
- **each foot's move and turn**: a foot in the air takes both; a foot on its heel or its ball takes its turn (about
  that point) and not its move; a foot flat on the ground takes neither (said: «foot_l stands flat at Passing: its
  move not taken (Step and Width move a planted foot)»); a knee that only followed a foot not taken is not taken
  either;
- **each knee's turn** about its leg's line (`meanpose.knee_turn`), from 1.5 deg (under it: the IK solver following
  the hips).

Kept beside the walk's file as `<walk>.walkkeys.json` (`skeldar.walkkeys` 1): per key, the turns (3x3), the pelvis,
the knees, the feet's moves and turns.

## Into the cycle

`scene.load_walk`: the clean, the mean pose's correction (as before), the walk analysed, its steps found
(`walk.key_steps`, or `walk.key_note` saying why there are none); then, with any key edit, `keyposes.correct` puts the
edits in the analysed clip's frames and the walk is analysed again. Cached by the key file's time too.

Per frame: the knots are every step's four keys in order; between two knots each edit goes from one to the next by a
smoothstep (log vectors for turns, nothing overshooting), exact at its key and nothing at the keys on either side.
Then:
- each upper bone's local · exp(the frame's Y);
- the pelvis moved over the root;
- the body rebuilt by FK;
- each leg solved again from its new hip onto its foot - the foot tree turned about its heel or ball where that point
  is down and moved and turned in the air, untouched flat (the shares from the foot's own lowest, GROUND_TOL 2.5 cm),
  the knee hint turned about the leg's line - lengths kept, out of reach the shin stretched (the target's reach drops
  the pelvis there);
- the helpers re-follow their bones.

The walk analysed again is an ordinary walk: parameters measure it, poses and the helpers (Foot placement, Balance, the
knees' soft limit, Whip's springs) work on it, the retarget puts it on any skeleton.

## Also fixed on the way

- **The Rig pose's re-key used the card's settings for every walker on the cycle** - a finished walk on another
  skeleton took the card's parameters on every Update (the bug class of b829ba7). It now keys each walker as it was
  keyed last (`meanrig.rekey_target`: its own memo).
- `Walk.evaluate`'s `info["knobs"]` is what was asked; Height's plan (the same day) is in `height_step` /
  `height_straighten`, so a memo never stores the shortened stride.

## Proof

- `tests/test_walk_keyposes.py` (18, the synthetic walker): four keys a step in order and inside the step; an edit
  exact at its key, nothing at the others; the other foot's step mirrored (world deltas M D M to 1e-9); a lowered
  pelvis keeping the feet and the legs' lengths; a foot in the air moved, a flat one not, the mirror at the right
  passing; a knee turn; a rig's edit read back landing exactly at its key; edits adding; a flat foot's move (and its
  knee) not taken, said; the pelvis read in travel coordinates, signed; the file; the knots.
- `tests/test_walk_panel.RigPoseTests` (5): the tab's rows, one Update keying each cycle once with each walker's own
  settings, nothing moved, no rig, the presses on the active cycle.
- `docs/superpowers/plans/walkparam/verify_walk_keyposes.py` **22/22 mayapy standalone** (asd on the plugin's Manny
  skeleton): four rigs in a row, each on its key's frame (upper locals to 0.0002 deg, the pelvis 0.0000 cm), no key on
  752 controls, untouched rigs reading nothing; FKShoulder_L +20 on Contact - the cycle's upperarm_l 20.000 deg at the
  contact and 0.000 at the Down, upperarm_r 20.000 at the right contact (the mirror), the walker 14.7 (its arms'
  inertia); RootX_M -4 on Down - the walker's pelvis -4.2 at the Down and -0.5 at the Passing, the cycle's feet
  0.000000 cm off; the right foot +6 on Passing (legs in IK) - taken 6.00, the walker 5.6 higher, the left foot 5.2
  higher at the right passing; the standing left foot's move not taken and said, its rig stood back (0.00 cm); Reset,
  Delete, Update refusing with no rig. Create 6.6 s for four rigs, Update 1.2 s.

## Not built

- a key pose's timing moved (the keys stay where the cycle has them);
- different edits for the two feet's steps (always mirrored);
- curves of an edit drawn or eased differently;
- the walker's arms follow an edit through their inertia (Whip): a sharp arm edit reads 70-75 % at its key on the
  walker (14.7 of 20 deg on asd) - Whip's springs smooth it.
