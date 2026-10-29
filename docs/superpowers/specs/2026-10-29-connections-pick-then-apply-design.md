# Connections: pick, then press - one bake rule for every section

2026-10-29. The animator: «предложи несколько вариантов более удобного
разсположения инструментов в вкладке connections и нужно сделать консистентно
что бы перепекание происходило по нажатию кнопки а не по разному в каждом
разделе».

Three layouts were drawn as a canvas - https://claude.ai/artifact/M5ZtJhXiuWCDVRFUdHuFC3
(A: one Apply a tab; B: an Apply on every row plus Apply all a tab; C: no tabs,
the Tools card's sections and one Apply at the card's foot). The animator chose
**B**, and, asked: the weapon's and the camera's **aim becomes a pick** applied
by the same button; **W is a chip** after the segments; **BakeAcross / Release
get a tab of their own**.

## What the card does today, and where it is inconsistent

Read off `maya_scenesetup/connections.py` as it stands:

- **Body tab.** A press of `FK`, `IK` or `W` bakes AT ONCE (`_press_fkik` ->
  `switch_arm` / `switch_limb` / `toggle_world`), and `_press_spine` likewise.
  The box that looks like a state is the trigger.
- **Weapon tab.** A pick runs `_menu_changed`: it only fixes a cycle
  (`resolve_menus`) and writes «press Apply for: ...». The row's own Apply
  (`_press_row`) or `Apply all` (`_press_apply_all`) bakes.
- **Camera tab.** The parent segments and the `Position only` chip are read by
  `_press_camera_parent` when its Apply is pressed.
- **BakeAcross / Release, Aim Mode / Default** (weapon and camera): buttons,
  so they act on their press.

So one card holds two different hands, and the hand with no button is the one
that bakes a whole limb over the take.

Measured, the other half of the ask ("более удобное расположение"): the limb
rows pack two limbs into one `rowLayout` with ONE adjustable column
(`_fkik_row`, `ARM_L_WIDTH` 128), so at the animator's 360 px dock the two
tracks get about 86 and 128 px - with `W` added (2026-10-28) a segment is
**~28 px wide**, and the two halves are not even equal. One limb a row gives
each segment ~80 px.

## The card after

Four tabs: **Body | Weapon | Camera | Object**. Every row reads
`label · segments · [W] · check`, and every tab that has picks ends in one
orange **Apply all · N**.

```
Body                          Weapon                       Camera
FK / IK                       WEAPON IN HANDS              CAMERA PARENT
Arm R  [FK|IK] (W) v          Acts on [Sword|Dagger]       [Main|Root|Chest|Head|World]
Arm L  [FK|IK] (W) v          Hand R  [Free|Weapon]   v    (Position only)          v
Leg R  [FK|IK] (W) v          Hand L  [Free|Weapon]   v    CAMERA AIM
Leg L  [FK|IK] (W) v          Weapon  [World|R|L]     v    Aim [Default|Aim Mode]   v
Spine  [FK|IK]     v          AIM                               Apply all - N
      Apply all - N           Aim [Default|Aim Mode]  v
                                    Apply all - N
Object: BakeAcross   Release        (buttons: they act on their press)
```

- One limb a row (five rows where there were three, +48 px) so the segments are
  readable at the dock's width.
- `W` leaves the `[FK|IK]` track for a `cmds.checkBox` chip beside it: a space
  is not a mode, and a track otherwise means "one of these".
- The weapon's and the camera's aim is a row `Aim [Default | Aim Mode]` with its
  own check - the pair of buttons is gone from the body of the card.
- BakeAcross and Release move to a tab of their own; they take no pick, so that
  tab has no Apply all.

## Pick, then press

**Nothing bakes on a pick.** A pick is *pending*:

- the picked segment (or the W chip) takes the accent tint with a 1 px accent
  border - a new skin state `want` on `[skRole=segment]` and `[skRole=chip]`
  (`b1`, the one border width the sheet scales);
- the row's check button lights accent - the skin's existing `wait` state, the
  one the Tools card's Finish row wears (`maya_hubqt.set_state`);
- the tab's foot button counts them: «Apply all · 2»;
- the status names them: «Picked: Arm R to FK, Leg L to IK. Press Apply.»

The filled thumb keeps meaning what the limb **is**, so state and intent never
collide in one mark. A pick equal to what the scene already shows is not
pending and lights nothing.

**Where pending lives.** One set per rig (its namespace), on module state -
not per card: the hub's card and a popup copy of it must not disagree, the way
the status relay is one line for the whole hub. Every card's `refresh` paints
the scene's state first (`_set_fkik`, `_set_spine`, `_set_menus`, `_set_camera`,
as now) and then lays the pending overlay on top; without that second step a
refresh - which fires on SelectionChanged, Undo, Redo and after every press -
would simply wipe a pick. Selecting another character drops the set: a pick
belongs to the rig it was made on.

**What a press does.**

- A row's check applies that row only, W included: a limb whose mode AND world
  both changed is one `switch_limb(side, mode, kind, world=...)`; only W
  changed is `toggle_world`. One undo chunk.
- `Apply all` applies that tab's pending picks in ONE undo chunk, in the order
  the pure halves already settle - the weapon's three rows through
  `plan(current, wanted)` (releases, the weapon's move, new followers), the
  camera's parent before its aim (`camera.set_parent` already leaves and
  re-enters Aim Mode around a move), the limbs in any order with each limb's W
  beside it.
- After a press the picks it applied are re-read against the scene: one that
  came true leaves the set, one a refusal left standing stays, and the refusal
  names itself on the status line. Nothing parses a refusal's text.
- A cycle between the weapon's three rows is still resolved at pick time
  (`resolve_menus`), as today.

**Untouched:** `switch_limb`, `switch_spine`, `toggle_world`, `apply`,
`camera.set_parent`, `weaponaim`, `cameraaim`, `bake_across`, `release_across`
and every pure half. The presses call them later, that is all. The six hotkey
rows (`connections.connect`, `.disconnect`, `.aim`, `.default`, `.camera_aim`,
`.camera_default`) act at once: a hotkey IS the button.

## Rules that bite here

- **Every painter stays quiet** (trap 116): `_set_fkik` / `_set_spine` already
  raise `_FKIK_QUIET` while they write, and the pending overlay writes through
  the same guard - an `iconTextCheckBox -e -value` ran a box's command in one
  hub build.
- **A refresh must not eat a pick** - the overlay after the state, every card.
- **Control names stay scopeable** (`maya_hubcopy`): the W chip is a plain
  `cmds.checkBox`, never a `checkBoxGrp`, as the camera tab's `Position only`
  already is.
- **One undo chunk a press**, opened by the press and closed in a `finally`;
  the chunks the called functions open nest inside it.
- The row's check is 30 px of every row (`hubstyle.tool_width(66)` is 30 in the
  skin, an icon, no word) - the stated cost of B.

## Proof

- Unit tests (`tests/test_scenesetup_connections.py`,
  `tests/test_scenesetup_connections_camera.py` and a new
  `tests/test_scenesetup_connections_pending.py`, on the fake `cmds` the
  others use): a pick bakes nothing;
  the pending set per rig; a refresh keeps the pick and re-paints the state
  under it; a pick equal to the state is not pending; the count on each tab's
  Apply all; a row's check applies its row only; Apply all applies the tab's
  set in the plan's order; a refusal keeps its pick; selecting another rig
  drops the set; the W chip; the aim row; the Object tab's buttons unchanged;
  the quiet guard; positive controls - a card that bakes on a pick fails them.
- `docs/superpowers/plans/verify_connections.py` re-run (40 gates, a disposable
  Maya: OverRig's `parent_in` / `parent_out` need a GUI Maya), and
  `verify_fkik_switch.py` / `verify_fkik_keys.py` / `verify_ik_world.py` /
  `verify_weapon_aim_mode.py` / `verify_camera_tab.py` green - the engines do
  not change, so their numbers must not move.
- A new `verify_connections_apply.py` in a disposable GUI Maya: pick FK on one
  arm and IK on a leg, read the scene unchanged; press Apply all, read both
  limbs switched and ONE undo putting both back; the same for the weapon's
  three rows and the camera's parent + aim.
- What only the animator can judge: the card at their dock's width with five
  limb rows, and whether a check a row is worth its 30 px in the hand.

## Not built

A pending pick that cannot be applied is not greyed at pick time (a refusal
still comes at press time, by name). No Apply all across tabs - each tab has
its own, which is what B means. The Tools card's sections (variant C) are not
built; the mockup stays on the canvas if the animator wants them later.
