# Connections: a Weapon tab and Aim Mode (2026-10-21)

The animator: «Давай реализуем дополнительную вкладку в connection для оружия перенесем в эту
вкладку парент оружия и добавим новый инструмент aim. Суть - когда мы нажимаем aim у нас должна
отработать логика aim из раздела tools только вместо локаторов мы должны создавать контроллеры.
Запекание ключей на эти контроллеры и обратно на наше оружие нужно сделать умным по ключам а не
весь таймлайн сразу (мы так делали для наших связей FK IK). Делаем 2 кнопки Aim Mode и Default.
Отдельно нужно убедиться что позы и анимации сохраняются и загружаются на любой мод из нашей
библеотеки вне зависимости от того как они были сохранены».

Asked: the controllers stand **in the world**; Aim drives the **rotation only** (as Tools > Aim);
a parent change in Aim Mode happens **automatically** (Default, the change, Aim Mode again); the
card is **[Body | Weapon]**.

## The card

`[Body | Weapon]` segments under the subtitle (`skeldarConnectionsTab`, remembered in
`skeldarConnectionsTab`, Body by default). Body: FK / IK (arms, legs, spine) and Any object
(BakeAcross, Release). Weapon: Acts on, the three parent rows, Apply all, then the caption «Aim»
and one row **Aim Mode** (primary) + **Default**. The status line stays under both. Hotkey rows
`connections.aim` and `connections.default`.

## Aim Mode (`maya_scenesetup/weaponaim.py`)

On the chosen weapon (Connections' «Acts on»):

- refused, nothing changed: no rig / no weapon, a retarget standing, the weapon already in Aim
  Mode, a rotate channel locked, or driven by anything but its own time curves (a constraint, a
  Tools knot, an animation layer - «bake its layers first»), a weapon with no geometry;
- the two controllers placed from the model's own extents (`aim.placement`, the old Add Aim's
  rule): the target past the tip along the blade, the up on the next longest axis at the same
  distance. The aim and up vectors are those axes in the weapon's own frame;
- **the frames are the weapon's own keys** (`fkik.own_keys` over its translate and rotate curves,
  FK/IK's rule since 2026-10-16); none: one plain value at the current frame, said. Tangents from
  the weapon's keys on each frame (`fkik.tangents_at`);
- on each frame the controllers' WORLD places are read off the weapon (one frame walk, the warp
  off - `maya_timewarp`) and keyed; the weapon's rotate keys cut and `aimConstraint` (no offset,
  `worldUpType object`) put on: on every keyed frame the weapon stands exactly where it stood;
- the controllers: curve controls (`curvectrl`), a diamond `<weapon>_aimTarget` (accent) and a
  smaller square `<weapon>_aimUp` (cyan), rotate and scale locked, in a group `<weapon>_aim`
  marked `skeldarWeaponAim` (the weapon's UUID; its aim / up vectors kept), parked in the
  character's group (`chargroup.park`) - so Delete character takes them;
- one undo chunk, autoKey off, the time put back.

Between the weapon's keys the world controllers interpolate on their own: a hand that moves while
the weapon has no key there turns the weapon somewhat differently than before. That is the
keys-only cost the FK/IK switch has, and the status line counts the keys.

## Default

The keys of the two controllers and of the weapon's translate, once each; on each the weapon's
local rotation read (its parent's world, its rotateAxis kept - `helpers.driver_channels`), the
constraint and the group deleted, the rotate keyed with those tangents (a constant channel a plain
value). Exact on every keyed frame.

## A parent change in Aim Mode

`connections.apply` with a lift or a hang on an aimed weapon: Default first, the steps, Aim Mode
again - all in the press's chunk. A follow or a release alone leaves the aim standing (the proxies
hang under the weapon, whatever drives its rotation).

## The Pose Library onto any mode

Saving reads the bones (`weapon_r`, `weapon_l`), whatever drives them - nothing to change.
Applying onto a weapon in Aim Mode (`helpers.Writer`): the entry's mode is `aimed`; the weapon's
wanted world matrix is computed as for any driver (`K⁻¹ · W_bone`), its translate keyed, and the
two controllers keyed at that matrix's aim and up points in world. The aim controllers are the
body (`scene._kind` ACCESSORY), never an object of a card.

## Proof

`docs/superpowers/plans/verify_weapon_aim_mode.py` (mayapy standalone): a Manny rig, a sword in the
right hand keyed on a few frames under a retargeted take - Aim Mode keeps the weapon on every key
(rotation, place), keys exactly the weapon's key frames, moving the target turns the blade toward
it; Default gives the same keys back; Hand R -> World and back in Aim Mode keeps the aim; a pose and
an animation saved in Default load in Aim Mode and the other way round, `weapon_r` on the card's
place both ways; one undo each.
