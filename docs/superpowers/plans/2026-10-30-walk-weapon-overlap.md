# Plan: Walk Builder's Weapon overlap (2026-10-30)

Spec: `docs/superpowers/specs/2026-10-30-walk-weapon-overlap-design.md`. Built in this order, each step's
gates written before its code.

1. **The tip rule, shared.** `aim._axes` / `aim.tip_offset` out of `aim.placement` (the blade's axis and its
   further end, no margin), `placement` on top of it. Gates: `tip_offset` on the Long Sword's extents,
   `placement` still its target past that tip, a model with nothing to measure. DONE
2. **The pure halves in the model.** `shifted_points` (shifted_cycle's place half, gated against it),
   `aim_swing` (the minimal swing, no twist, the antiparallel and the too-short cases), `swung_about` (the
   world turn about a point). DONE
3. **The knob.** `weapon_overlap` in DEFAULTS / RANGES / SIDED / ENGINE_ONLY; `gait.WEAPON` group with the
   one `Param` in ms; `engine_knobs` ms -> frames at the output rate; `ranges` capped at half the cycle.
   DONE
4. **The pass.** `model._weapon_swing`, called from `_arm_overlap` after the other lags and before
   `_arm_to_hand`; `moved_arms` counts it; `info["arms"]["overlap"]["weapon" / "weapon_sides" /
   "weapon_cm"]`; `describe`'s line. Gates: the aim, the grip held, the length kept, the riders under a
   two-handed grip, a weapon in each hand, on top of Arm overlap, 0 a no-op, Whip, Balance. DONE
5. **The reading.** `scene.weapons_in_hands` (every marked weapon in a hand of the walker, as the grip and
   the tip in that hand's frame), `weapons_key`, through `animate` -> `evaluated` -> `evaluate`, and the
   press's line ("the weapon trails ... its tip ... cm behind", "no weapon in the hands"). DONE
6. **The card.** `panel.GROUP_ROWS` gains the `weapon` tab (the table is derived from `gait.GROUPS`, so the
   slider and its Reset come for nothing). DONE
7. **The proof.** `tests/test_walk_weapon_overlap.py` (38 tests; a control with the pass neutered fails 13
   of them) and `docs/superpowers/plans/walkparam/verify_walk_weapon_overlap.py` (mayapy standalone, three
   phases: reading, keys, model). DONE - 0 of 30 gates failed.
8. **CLAUDE.md** and a push, so Check update carries it. DONE

## What the proof measured

On the animator's own cycle (`own:8e4ef9f3703a44a3`, 27 frames at ntsc) with `LongSword_Idle_3P` at share 1
(a two-handed grip) and a Long Sword equipped in the right hand:

- the reading: the grip is the weapon's own origin in the hand (0.00e+00 cm), the tip its mesh's farthest
  vertex (1.4e-14 cm), the blade the Long Sword's own 115.925 cm;
- 150 ms is 4.500 frames at 30 fps; the blade points at its own tip that many frames earlier to
  **0.0100 deg**, the grip is held to **0.0217 cm**, the blade keeps its length to 0.0000 cm, and the
  sword mesh's own tip swings 8.70 cm;
- the two-handed hold is kept to **1.08e-12**, the other hand is carried 2.02 cm;
- `weapon_r` still stands on the weapon's socket (2.4e-08), so the exported bone carries the lag;
- 0 ms is the walk matrix for matrix, and with no weapon in the hands the lag changes nothing and says so;
- under the animator's own Whip and In place the tip trails 9.7 cm with the aim within 0.76 deg: In place
  takes the root's own per-frame shift out AFTER the arms pass, so the aim is exact in the travelling world
  it was computed in.

## Not done

- the lever as a second knob (the aim at a share of the blade);
- the weapon lagging inside the grip (the question's other answer: nothing writes the weapon's own channels);
- a weapon out in the world, and the weapon's own twist about its blade.
