# Walk Builder: a two-handed hold is 2H, not the pose - addendum to the hands' share

2026-11-04, the same day, after the animator installed Arms % and Hands % and opened their scene:

> Открыл сцену 7002. Я не понимаю почему сейчас работает по разному один и тот же функционал с разными
> позами у меча руки стоят на месте при ручках в 0 у ножа дагера сильно двигаются. Наши ручки не должны
> зависит от позы

The knobs built this morning reach what they say they reach. What differs between the two poses is the
**baseline**, which no knob sets: a pose whose two hands hold one thing (within `GRIP_DIST` 30 cm) is
called a **grip** by `pose.prepare`, and the model then does two separate things to it that it does to
nothing else. Both are invisible and neither is a knob.

Read the spec of the morning's work first:
`docs/superpowers/specs/2026-11-04-walk-hands-from-the-cycle-design.md`.

## The two sources, measured apart

Their own cycle (`own:7833074715b34c33`), their own two cards, their own card state (Chest on,
Rotation 0, Position 0, **2H on**, share 1), at the knobs' own 100 %. The hand's turn in the pelvis's
frame and the fingers' own turn, R / L:

| | hand | fingers |
|---|---|---|
| sword, as it is | 6.84 / 6.84 | 0.00 / 0.00 |
| sword, the gain stilling off | 6.84 / 6.84 | 11.07 / 12.80 |
| sword, the stilling AND the one-body spring off | 12.05 / 15.58 | 11.07 / 12.80 |
| dagger, as it is | **16.25 / 14.01** | **11.07 / 12.80** |
| dagger, + the one-body spring | **6.84 / 6.84** | 11.07 / 12.80 |
| dagger, + the one-body spring + the stilling | **6.84 / 6.84** | **0.00 / 0.00** |

So the dagger with both becomes **the sword exactly**, and the two sources are independent:

1. **The one-body spring.** `_arm_dynamics` reads `pose["grip"]` and, when it is set, runs
   `_grip_motion` - the right hand carries the held thing through one spring and the left keeps its hold,
   both arms reaching their hands by IK - instead of a spring per arm. That is the whole of the hand's
   16.25 against 6.84.
2. **The gain stilling.** The frame walk reads `pose["grip_sides"]` and multiplies the arms' and the
   fingers' gain by `1 - alpha`. With `Hands %` and `Arms %` built this morning that is now a duplicate of
   a knob - and it is the whole of the fingers' 11.07 against 0.00.

## Why it reads as the knobs depending on the pose

**The animator's card already says the hold is two-handed**: `weapon_hold` (2H) is on, and its own tooltip
is «Binds the free hand to the one holding the weapon ... so a two-handed carry holds without a pose's own
grip». `_arm_overlap` honours it - it binds the free hand and carries the weapon. But neither of the two
things above looks at it: both read the POSE. So a dagger pose with 2H on is a two-handed carry that the
springs still treat as two loose arms.

`_grip_motion` needs nothing from the pose (it springs the right hand's own world track and the left keeps
its hold on it), so there is no reason for it to be the pose's to decide.

## The design

**One rule, in one helper, for both places: the sides whose hands hold one thing together.**

```python
def held_together(self, ctx):
    """The sides whose hands hold ONE thing, and the side that carries it: a pose's own grip, and 2H
    (`weapon_hold`) binding a free hand to the hand that holds a weapon. 2H is a knob and a pose's grip
    is not, and the two mean the same thing - so the model follows the knob too, and a pose whose hands
    are apart reads exactly as a two-handed pose does once 2H is on (2026-11-04). An arm the pose's own
    chip leaves out holds nothing (the 2026-11-03 rule)."""
```

- the pose's own `grip_sides` while its share is above 0, exactly as the frame walk has read it since
  2026-11-02 (one arm out of the pose leaves the other holding its thing; a pose from before carries the
  bare flag for both arms);
- **plus**, where there are two arm chains, the holding side and the side 2H binds to it - the same
  condition `_arm_overlap` already computes for `hold_sides`: a weapon in one hand (`ctx["weapons"]`), the
  other hand free, `ks[side]["weapon_hold"] > 0.5`, and neither arm left out of the pose by its own chip.
  A weapon in each hand binds nobody: neither is free.

It also answers **which hand carries the thing**: the hand the weapon is in under 2H, and the right hand
for a pose's own grip, as it always was. `_grip_motion` takes that as `hold_side`, so a weapon in the LEFT
hand is carried by the left and the right keeps its hold on it; it used to be the right hand whatever the
scene held.

Worked out once per evaluate into `ctx["held_sides"]` / `ctx["held_by"]` (`_held_sides` works it out for a
ctx made by hand, in a test), and read by:

- **`_arm_dynamics`**: `grip = len(chains) == 2 and all(s in holding for s in chains)`, in place of
  `pose and pose.get("grip") and ctx["alpha"] > 0.0`;
- **the frame walk's stilling**: `self._side(j) in holding` (hoisted once per frame), in place of
  `pose.get("grip_sides", SIDES if pose.get("grip") else ())`.

`_arm_overlap` is not changed: it already reads 2H (its `hold_sides` binds the free hand) and it keeps its
own `grip` for the lag averaging, where a pose's grip is still a grip.

## What changes, and what does not

- **A pose whose hands are apart, with 2H on** gets the one-body spring and the stilling: on their own
  cycle the hand goes 16.25 / 14.01 -> 6.84 / 6.84 and the fingers 11.07 / 12.80 -> 0.00, **which is the
  sword card's own reading to 0.000 deg**. This is the ask, and it changes takes they have already keyed
  with 2H on - in the direction they asked for.
- **A pose grip** is untouched at every knob value: its `grip_sides` already hold both sides, and with no
  weapon in the scene 2H binds nobody. The one case that does change is a pose grip with 2H on and the
  weapon in the LEFT hand: the carrier moves from the right hand to the left, which is where the thing is.
- **No 2H and no grip** - two loose arms - is untouched: nothing is stilled and the springs run per arm.
- **The knobs themselves do not change.** `Arms %` and `Hands %` scale what is left, as they did this
  morning; at 0 % both poses are still, and now at 100 % both poses are the same too, as long as the hold
  is declared the same way (by 2H or by the pose).
- **The stilling stays the pose's share.** It is `gain *= 1 - alpha` inside the pose branch: it fades the
  swing toward the hold the pose gives the hand, and with no pose there is no hold to fade toward. So 2H
  with no pose at all gets the one-body spring and no stilling, and `Hands %` is the lever there. Both of
  the animator's cards are at share 1, so both get it.

## What is deliberately NOT done

- The grip's stilling is **not removed**. Taking it away would make a two-handed sword's fingers flex on
  the hilt by default (11-13 deg) on every take already made, and a hand holding a thing should not flex
  its fingers. It becomes one half of a rule a knob can declare, which is what the animator asked for; it
  does not become a free-for-all.
- `GRIP_DIST` and `pose.prepare`'s detection are untouched: a pose that really does hold one thing with
  two hands is still read as one.
- Nothing about the Chest mode, Weapon overlap or `Whip`.

## Proof

- `tests/test_walk_two_handed.py` - 23 tests: the rule (a pose grip, one arm out, an old pose, 2H with a
  weapon left or right, 2H with no weapon, a weapon with 2H off, a weapon in each hand, an arm out of the
  pose, no pose at all, share 0) and both readers (2H reads exactly as a two-handed pose, matrix for
  matrix; the control without it; the fingers; the carrier through a spy on `_grip_motion`; `Hands %` still
  scaling; the one-body spring not a no-op). **On the build before: 7 failures and 13 errors.**
- `docs/superpowers/plans/walkparam/verify_walk_two_handed.py` - **0 of 12 gates, mayapy standalone**, on
  their own cycle and their own card as it stands: the sword card still (6.84 / 6.84 deg of hand in the
  pelvis's frame, 0.000 of finger), **the dagger card the same at the same knobs, the two agreeing to
  0.000 deg**, the control with 2H off (16.21 / 54.02, fingers 11.07 / 12.80), the sword card unchanged
  with 2H off, the spring following the knob, 2H with no weapon binding nobody (42.43 / 54.04), a left-hand
  weapon carried by the left, an arm out of the pose playing the cycle, the loop closed (3.9e-14), the
  bones whole (3.6e-14 cm) and the line saying «the held weapon trails». **On the build before: 5 of 12
  fail**, gates 2, 3, 6, 8 and 12, reading 16.25 / 14.01 and 11.073 / 12.799 - the morning's numbers.
- **The morning's `verify_walk_hands.py` had to drop 2H**, and that is the finding worth keeping: with the
  chip on, the hold now stills the hands by itself, so every knob gate would be vacuous - the knobs would
  have nothing left to hold back (trap 334's family). It runs with `weapon_hold` dropped from their card
  and is **0 of 11** again. Two of its gates were also wrong about what they measured, and both are
  mended: `FLOOR` 6.84 is not «the body's own turn» but the hand riding the weapon the chest override holds
  still (the chest itself turns 15.7 deg on this cycle), and «the whole ask brings the dagger to the
  floor» only held because 2H was binding the left hand - it now reads «the free arm stands still on the
  body», 23 joints at 0.0000 deg, the arm riding the weapon being re-solved by IK to hold it (17.8 deg of
  its own, whatever the knobs say).
- The neighbours, green on this change: `verify_walk_one_arm.py` 0 of 13, `verify_walk_arm_overlap.py`
  0 of 101, `verify_walk_weapon_overlap.py` 0 of 30, `verify_walk_weapon_chest.py` 0 of 22,
  `verify_walk_keys_changed.py` 0 of 23, `verify_walk_sprint.py` 12 of 12,
  `verify_walk_rig_pose_layer.py` 0 of 22, `verify_walk_pose_card.py` 0 of 6; 1177 walk unit tests OK.
  `verify_walk_straight_leg.py` [25] and `verify_walk_own.py` [10, 19] fail exactly what this repository
  already records them as failing.
