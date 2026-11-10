# Walk Builder: Inherit - how much of the chest a held hand takes (2026-11-10)

## The ask

The animator, after Aim target: «Давай сделаем ручку которая будет контролировать процент холда 1 - 100%
наследования как сейчас 0 - 0 процентов полная статика».

The history behind it: the 2026-11-03 Weapon tab had `Chest rotation` / `Chest position` (0 / 0 stood the
weapon still); the 2026-11-05 rebuild replaced the whole tab by Hold (the hand rigid on the chest) and
Overlap, and the "stands still" end went with it.

## The knob

**`Inherit`**, the Weapon tab, between Hold and Overlap. Sided, 0..1, **1 by default**.

Hold parents the hand to the chest; Inherit is that parent's weight:

- **1**: the hand takes all of the chest's motion - Hold as it is today, matrix for matrix.
- **0**: none - the hand with whatever it holds stands still in the frame the cycle travels in (in place:
  in the world), at the place its own mean offset puts it on the chest's mean pose. The body moves under
  it and the arms reach it by IK.
- Between: that share of the chest's turn (slerped from its mean heading) and of its place (pulled toward
  its mean), one number for both.

## The mechanism

`model._weapon_hold` already computes `H' = A . shifted(C, lag)` with `A` the hand's mean offset from the
chest and `C` the chest's cycle. The chest is now read through the helper the 2026-11-03 strengths used
and the rebuild kept: `C_k = steady_chest(C, k, k)`, so `H' = A . shifted(C_k, lag)`. At `k = 1` the
chest's cycle is passed untouched (no arithmetic on it), so the default is bit for bit what it was.

- Hands holding one thing (a pose's grip) take the two sides' mean, as Overlap does; the carrier drives
  and the other takes its delta, so the grip is exact.
- Overlap reads the same scaled chest late. Aim target runs after, from where this leaves the hand.
- A held hand has no arm spring (the 2026-11-05 rule), so 0 is exact: nothing rings on top.
- It acts where Hold acts: the chip on and the additive pose holding that arm, blended by the pose's
  share. Hold off: nothing.

The line: «both hands ride the chest at 30 % of its motion» / «both hands stand still: none of the chest's
motion» (`model.hold_line`, one writer for `describe` and the Pick line).

## What it costs

The body still moves, so at low values the arms pay for it: the elbows work to keep the hand where it is,
and a shoulder that travels further than the arm reaches clamps the arm on its line (the IK's rule for
every knob of the tab).

## Proof

- `tests/test_walk_weapon_inherit.py`.
- `docs/superpowers/plans/walkparam/verify_walk_weapon_inherit.py`, mayapy standalone: the model on the
  animator's own cycle and two-handed card, and the keys on a Manny skeleton with a Long Sword.
