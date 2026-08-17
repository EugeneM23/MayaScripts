# Connect arms to weapon — design

**Date:** 2026-08-17
**Status:** designed, not implemented. Builds on
`2026-08-17-weapon-attach-design.md`.

## The ask

Two buttons in the weapon window.

**Connect Arms To Weapon** turns the rig inside out: the weapon leaves the
skeleton and becomes the thing that drives the hands. Both arms end up in IK
with their hand controls riding the weapon, so animating the weapon animates
the arms — and the animation that was there survives every step.

**Disconnect Arms** puts it back: the hand controls return to the root
controller, the weapon returns to `weapon_r`.

## The three steps of Connect, and why in that order

1. **Both arms to IK.** Not "switch" — *bring to* IK. Switching a limb that is
   already IK converts it to FK, which is the opposite of what the button
   promises. The state is read from the scene: a limb is IK when
   `builder.ik_control(limb, "end")` resolves to a node that exists. Limbs that
   are not get `fkcontrols.switch_limbs`, which converts FK and auto-builds IK
   on a bare chain — both paths already exist and re-bake the animation.
2. **The weapon out to world.** `apply_Parent_out` on the carrier. It leaves
   `weapon_r` carrying the world motion it had, now baked onto its own
   channels.
3. **The hand controls onto the weapon.** `apply_Parent_in`, selection child
   then parent. The end controls currently hang under `root_FK_ctrl`
   (`hang_ik_on_root`), and re-parenting a knot that already has a parent is
   not a path this repo has measured — so each control is lifted to world with
   `apply_Parent_out` first and hung on the carrier second. That is exactly
   what `switch_limbs` does with its rider chains, and it is the only sequence
   with evidence behind it.

Arms are brought to IK **before** the weapon is lifted, so the weapon is taken
off a hand motion that will not change afterwards.

Only the **end** controls ride the weapon, by the user's call. The pole
(elbow) and base groups stay on `root_FK_ctrl`: elbows keep answering to the
body, which is the ordinary prop workflow, and hanging the chain base on a
prop tears the shoulder off (measured when the IK rig was first hung on the
root — see `CLAUDE.md`).

Finger controls need no handling. They ride `<limb>_IK_anchor`, a locator
parented under the end control, so they follow the hand wherever it goes.

## Where the code lives

Rig knowledge stays in the rig module. `maya_overrig.fkcontrols` gains two
functions next to `hang_ik_on_root` / `lift_ik_off_root`:

```python
def hang_ik_end_on(limb, target):
    """Hang a limb's IK end group on `target`, animation re-baked."""

def lift_ik_end(limb):
    """Lift a limb's IK end group back to world."""
```

Both record what OverRig creates into the **limb** manifest
(`builder._ensure_limb_set`), the way `hang_ik_on_root` does: the coupling
lives and dies with the IK rig rather than with the weapon.

`maya_weapons.connect` orchestrates, and knows nothing about OverRig
internals:

```python
ARMS = ("arm_l", "arm_r")

def limbs_to_switch(state):      # pure: {limb: is_ik} -> limbs needing a switch
def marked_ancestor(path, marked)  # pure: nearest ancestor carrying the marker
def linked_carrier(limbs)        # the weapon the hands ride, or None
def connect(carrier, scene_map)  # the three steps, one undo chunk
def disconnect(carrier, bone)    # the three steps backwards
```

## How the module knows a link exists

Once the weapon is in world it is no longer a child of `weapon_r`, so
`attach.find_attached` cannot see it. A scene-wide hunt for the marker would
find it — and would also find the identical sword in the hand of a second
character.

The exact question is asked instead: **the linked weapon is the nearest
ancestor of the IK hand control that carries our `mayaWeapon` marker.** No
scene-wide search, no ambiguity, and it costs one walk up a DAG path.

Two consequences, both required:

- **Add is refused while a link exists.** Add replaces, replacing deletes the
  carrier, and the IK end controls are its DAG children — the press would take
  both arm rigs down unbaked. The status line says so instead.
- **The offset fields stop writing.** After `apply_Parent_out` the carrier's
  channels carry baked curves, and `setAttr` on a connected channel raises.
  The window reports "weapon is animated - offsets are baked in" rather than a
  traceback.

## Disconnect

The same procedures backwards: each end control is lifted to world and
`hang_ik_on_root` puts it back under the root controller (idempotent, so the
base and pole groups already there are left alone), then the carrier is hung
back in `weapon_r` with `apply_Parent_in`.

The weapon's animation is **not** stripped. It is re-baked into the bone's
local space, so whatever the animator did with the sword survives the round
trip. The cost is that the carrier now holds curves instead of clean zeros, so
the offset fields stay inert until someone deletes those keys by hand. Silently
throwing away the animator's work would be the worse trade.

## Failure modes

| Situation | The button says |
|---|---|
| no weapon anywhere | `no weapon - press Add first` |
| Connect while already linked | `already connected` (and does nothing) |
| Disconnect with no link | `not connected` |
| the character has no arms to rig | `no arm chains on this skeleton` |
| OverRig cannot be found | `overrig.NOT_LOADED_MESSAGE`, as everywhere else |

Every entry point that runs MEL calls `overrig.ensure_loaded()` first, and the
whole operation runs in one `undoInfo` chunk: a half-applied Connect leaves the
arms in a state nobody asked for.

## Testing

Unit tests, with the fake-`cmds` pattern the repo already uses:

- `limbs_to_switch` — nothing to do when both arms are IK, both when neither
  is, and only the FK one in a mixed rig. This is the guard against the
  "switch turns my IK arm into FK" bug.
- `marked_ancestor` — finds the carrier several levels up, returns None when
  no ancestor is marked, and does not mistake `|swordExtra` for `|sword`
  (trap 7's separator rule, again).
- `attach.is_animated` — true when any of the six channels has a curve.
- the window's new messages.

**The live proof** is `docs/superpowers/plans/verify_connect_arms.py`, run in
the Manny scene through the command port:

1. before Connect: sample both hand bones' world matrices across the timeline;
2. Connect;
3. both arms report IK, and each end control is a DAG descendant of the
   carrier;
4. the carrier has no parent and carries animation;
5. **the hands did not move** — the same world matrices, frame by frame. This
   is the check the whole feature stands on;
6. Connect again changes nothing (idempotent);
7. Disconnect: the carrier is back under `weapon_r`, the end controls are back
   under `root_FK_ctrl`, and the hands still have not moved.

If a channel on the carrier is free to write (no curves), the script also turns
it and measures that both hands follow. Where the scene leaves nothing free —
a built rig drives its bones through a `pairBlend` and its controllers carry
baked curves — the script says so rather than reporting a green check it did
not earn.
