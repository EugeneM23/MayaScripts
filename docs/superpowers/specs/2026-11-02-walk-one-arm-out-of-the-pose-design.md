# One arm out of the additive pose, playing the cycle

2026-11-02. The animator: «еще нам нужен инструмент который позводит исключить одну из рук из адетивной позы и
оставить анимации цикла».

Asked, and answered: an excluded arm plays **the cycle entirely** - its own mean and its own swing, exactly as
if there were no pose for that arm (its upper arm hangs and swings in the world again, as it does with no pose).
A two-handed lock then falls apart by necessity: a hand that holds a thing cannot swing freely. The weapon
stays in the hand the pose put it in.

## What stands today

Walk Builder's Pose share has five part chips (`maya_walk.pose.PARTS`, the card's `PART_LABELS`): Torso,
Pelvis, Knees, **Arms**, Feet. `Arms` is both arms in one chip and carries three keys of the prepared pose -
`arms` ({joint: its local 3x3 in the pose}), `weapons` ({a weapon helper joint: its relation to the hand that
holds it}) and `grip` (both hands on one thing).

The model's own mixing is already per joint (`model.py`, the FK walk of the frames):

- a bone of the arm or finger kind takes `centre = toward(lmean[j], pose["arms"][j], alpha)` - **the pose's
  local is only the mean the cycle's own swing runs about** - and a joint the pose does not name keeps
  `lmean[j]`, the cycle's own mean;
- `grip` multiplies that side's swing by `(1 - alpha)`: at share 1 a two-handed pose stills both arms;
- an upper arm (`world_arms`) hangs and swings in the WORLD rather than in its parent - but only while the pose
  names no arms at all (`pose is None or "arms" not in pose`), in the frame walk and in `_body_dynamics`'s
  reattach.

So excluding one side is mostly a question of what the prepared pose is allowed to say, plus two places in the
model that ask «does this pose have arms» where they should ask «does it have THIS arm».

## The design

**Two chips in place of one**: `Arm L` and `Arm R` (`pose.PARTS` gains `arm_l` and `arm_r`, the card's
`PART_LABELS` with them). Six chips in the card's flow; nothing else in the row changes.

**`pose.prepare`** records which side each arm joint and each weapon helper belongs to (`arm_side`,
`weapon_side`, read off the bone's name), so the filtering needs no walk.

**`pose.filtered(pose, parts)`** keeps the generic keys as it does today and, for the arms:

- the sides whose chip is on keep their joints in `arms` and their own `weapons` entry (a weapon bone whose
  name names no side is kept while either arm is kept);
- `grip` survives only when **both** chips are on;
- neither chip on drops `arms`, `weapons` and `grip` whole - today's behaviour with `Arms` unticked, so both
  upper arms hang in the world again.

**`model.py`**, the two places that must ask per joint:

- the frame walk's world-arm branch takes an upper arm the pose does not name (`j not in pose["arms"]`);
- `_body_dynamics`'s `held` set is every world arm the pose does not name, so an excluded upper arm keeps
  hanging in the world on the moving chest.

Nothing else in the model changes: an excluded side's forearm, hand and fingers fall through to `lmean[j]`
with their own gains, and `grip` being False leaves both swings alone - which is what «the cycle entirely»
means, written in the model's own terms.

**An old memo keeps working.** A walker keyed before this carries `parts: [..., "arms", ...]`, and the panel
and `scene` drop names they do not know - which would silently take BOTH arms out of the pose on the next
re-key. `pose.parts_read(parts)` maps `arms` to both sides (and drops anything unknown), and every read of a
stored list goes through it: `scene.animate`, the card's `chosen_parts` / `_set_parts`, a preset's parts. The
memo is written with the new names by the next press.

## The cost, stated

A pose's two-handed grip and a one-armed exclusion cannot both hold: the excluded hand swings and the weapon
rides the other one. That is the animator's own choice here, and the Pick line says it
(«left arm out of the pose: the two-handed grip is off»).

## Proof

`docs/superpowers/plans/walkparam/verify_walk_one_arm.py`, mayapy standalone, a Manny UE5 skeleton walking
`asd` under the two-handed sword pose at share 1 (the pose that stills both arms today), every gate measuring
the walker's own keys:

- both chips on: what it does today, to the digit (a control against the build before);
- `Arm L` off: the left arm's bones play the cycle - its local mean within a hair of the cycle's own mean and
  its swing back to the cycle's amplitude - while the right arm still stands in the pose;
- the left upper arm hangs in the world again (its world swing equals the no-pose walk's);
- the right hand keeps the weapon (the weapon bone's relation to `hand_r` is the pose's);
- `Arm R` off instead: the mirror;
- neither on: both arms as the walk's own, to the digit against a run with no pose arms at all;
- a walker whose memo says `arms` keeps both arms on the next re-key (the migration), measured on its keys.

Unit tests: `tests/test_walk_one_arm.py` - `filtered`'s own rules (the sides, the weapons, the grip, the
migration) and the card's two chips.

## Not built

- Per-arm Pose share (one number for the pose, as today).
- Per-side exclusion of the legs, the torso or the head (the chips stay whole-body).
- Anything in the Pose Library's own parts (`maya_poselib`): this is Walk Builder's additive pose only.
