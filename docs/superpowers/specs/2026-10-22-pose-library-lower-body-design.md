# Pose Library: 1P lower body (2026-10-22)

The animator: «Так как мы обрабатываем анимацию upper body в нашей библеотеке поз давай точно так
же сделаем обработку и lower body и галочку для загрузки анимации только на нижнюю часть».

Asked what the target's upper body does while only the lower body comes in, they chose **kept
stable** (over riding the new hips): the chest keeps its turn against the character's root, its
place rides the new spine - the mirror of 1P upper (whose chest is the card's against the root,
standing on the target's spine) and of 1P Setup's layers (the chest knot's turn on Upper, its
place on Lower).

## What a lower-body press poses

`maya_poselib/lower.py` (pure, beside `upper.py`): `restrict(data)` cuts a character card to

- every bone of the card that is NOT its chest (`upper.chest_of`: canonical `spine_03`) or below
  it in the card's hierarchy, selected at its save or not - the root, the pelvis, spine_01/02,
  the legs, their twists; never a helper (`weapon_*`, `ik_*`, `interaction`, `center_of_mass`)
  or the camera bones;
- `keep`: [the chest leaf] - the bone the press keeps stable on the target;
- `lower_1p: True`.

Refused: no chest («nothing marks where the lower body ends»), no member below the chest (a
hand card). An objects card as it is.

The pelvis is a member, so an animation card carries its travel onto Main (or the root) as a
whole card does; In place keeps the character where it stands. The weapon and the camera bones
do not come (no hand, not a whole body).

## The kept chest

`posemath.Transfer(kept=)` - target leaves. In `frame`, a kept bone that the card does not pose:

    turn  = rotation(T_now[kept]) · rotation(place)⁻¹ · rotation(root_world)
    point = local_translation(T_now[kept] · T_now[parent]⁻¹) · W[parent]

- its turn against the target's root frame as it stood (`place`), put on where this frame puts
  the root frame (`root_world`: a pose's root never moves, so its world turn; an animation's
  travel turns it with Main);
- its place on its parent as it stood, on the parent's RESULT - the chest sits on the end of
  the new spine_02.

Everything above the chest is no member and follows it rigidly: the neck, head, clavicles and
FK arms ride it; in 1P the IK arms (their Extra groups on `Chest_1P_ctrl`), the camera control
and a weapon in the chest ride the knot. In 3P the camera control hangs under Main, so the
camera stays with the character's root, as before.

`kept=` (a dict {leaf: (turn against the root frame, local translation)}) replaces what `frame`
reads off `T_now`: an animation reads it at every pasted frame BEFORE its ops (`kept_now`),
because the chest is a planned plug - Replace cuts its curve - the rule `read_ground` follows.
Under Insert too, at each pasted frame: the controls above the chest are not planned, so they
are not shifted, and the chest keeps what they show.

The solver gets the kept leaf as a member (`apply._plan`, `animapply._Target`), so the chest is
written and measured: in 3P `FKSpine3_M`; in 1P `Chest_1P_ctrl` (rigsolve's knot redirect) -
its place follows the new spine and its turn stays what it was, changing only with Main's turn.
On a bare skeleton spine_03's rotate. Select objects names the chest's control too.

## The window

A chip **1P lower** (`skeldarPoseLower1P`, optionVar `skeldarPoseLibraryLower1P`) beside
**1P upper**; the two exclude each other (turning one on turns the other off). `Scene._read`
cuts the card with `lower.restrict` while it is on - every press of a character card: Apply,
Blend, a drop onto a character, Select objects, the skill bar. A floor drop takes the whole card.

## Proof

- `tests/test_poselib_lower.py`: the cut (members, keep, refusals, the card untouched), the
  kept bone's rule in `Transfer` (the chest keeps its world turn under a moved pelvis, rides the
  spine's end, turns with a moved root frame, `kept=` overrides `T_now`);
- the window's exclusive chips and `_read`;
- `docs/superpowers/plans/verify_poselib_lower.py` (mayapy standalone): a UE clip retargeted
  onto Manny_Rig as the source, a card saved whole, pasted onto a second Manny_Rig carrying
  another take with 1P lower on, in 3P and after 1P Setup, and a pose onto a bare Manny UE5
  skeleton: the pelvis, spine_01/02 and the legs on the card's, an animation's root on the card's
  travel, the chest's turn against the root as before the press and its place on the new
  spine_02's end, the spine above it, the neck, the arms and the head on the chest as before; the
  camera on the root as before in 3P (its control hangs under Main) and on the chest in 1P;
  `_3P_Upper_Body`'s curves untouched; one undo.
