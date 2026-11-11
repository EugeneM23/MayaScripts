# Walk Builder: Head aim, and the rig pose Update reading the weapon again (2026-11-11)

The animator: «Сейчас обновление позы в Walk builder не обновляет оружие. Давай для головы сделаем такую-же систему
фиксации как и для оружия, то что есть сейчас плохо работает». Asked:
- "pose update" is the Rig pose tab's **Update** (confirmed);
- the head copies **Snap weapon** (a target placed on the rig pose), and «создавать голове аим и контролировать
  ручкой насколько она смотрит туда» - a knob for how much it looks there.

## The bug: Update never read the snapped weapon

`snapweapon.press` reads the mean pose rig once, when Snap weapon is pressed. `meanrig.update` read only the rig's
bones, so a weapon, its Aim Mode target or its hand moved on the rig never reached the walker; and when only the
target moved (the aim controllers are no game bones) Update said «nothing moved».

Fix: `meanrig._snap_again(rig, standing)` - for a walker that has a snap, Update reads it again (`snapweapon.read`)
and keeps it when it differs past `SNAP_TOL`; a rig whose weapon has left Aim Mode keeps the walker's snap and the
line says why. A walker with no snap is never read for one. The walker is keyed again even when no bone moved.

## Head aim

Like Snap weapon, on the rig pose:
- **Rig pose > Head > Head aim**: a green diamond `HeadAim_ctrl` is made under the rig's Main, `AHEAD_CM` (150) in
  front of the head along the chest's facing (the clavicles' line, flat, crossed with up), marked `skeldarWalkHeadAim`
  and found by that marker (never by name: aimcore names a control by its leaf). It is read and kept on the walker
  (edits `head`: the head's look axis in its own frame, the target in the game ROOT's frame); the walker keyed again.
  A target just made stands where the head looks, so nothing moves yet.
- The animator moves the target and presses **Update** (or Head aim again): the target is read again, **the look
  axis is kept**, so the head turns toward the new point. (Reading the axis again would make every target point
  "where the head already looks" - the verify's first run caught that.)
- **Remove**: the walker's head aim and the target control dropped.
- **Head aim** (gait parameter, Head group, 0..1, default 1; engine knob `head_aim`, which the model itself ignores):
  how much the head looks at the target. 1 right at it, 0 the walk's own head.

`headaim.apply` (numpy, in `scene.animate` after Snap weapon, before In place): per frame the head is turned about
its pivot by `share` of the least swing taking its look axis onto the target (the target carried by the root, so
it travels with the walker and ignores the bob, sway and twist); everything under the head is carried with it; the
roll about the look stays the walk's. The head alone turns, not the neck.

Not built: spreading the turn over the neck; a lag (overlap) on the gaze; a target carried by the chest.
