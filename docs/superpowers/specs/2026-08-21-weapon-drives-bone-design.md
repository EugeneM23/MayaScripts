# The weapon drives its bone — design

**Date:** 2026-08-21
**Status:** designed.

## The ask

> «Когда добавляем в сцену оружие мы должны перекинуть на него анимацию с
> weapon bone а потом weapon bone привязать к оружию. Само оружие в режиме по
> умолчанию давай крепить к кисти а не к вепон боне. Когда руки присоединяем к
> оружию то все должно работать так как сейчас»

Three statements, one scheme — the Camera Setup pattern applied to the weapon:

1. the weapon bone's animation moves **onto the weapon**;
2. the weapon bone is then **bound to the weapon** (the weapon drives it);
3. the weapon itself parents under the **hand**, not under `weapon_r`.

The third is not taste, it is mechanics: a node cannot both parent the weapon
and follow it — that is a cycle. Inverting the drive forces the weapon out
from under `weapon_r`, and the hand is where it belongs (it is `weapon_r`'s
own parent in the skeleton).

Why invert at all: a UE clip animates `weapon_r` (measured — clips carry it;
only `weapon_l` is absent), and today that motion is locked in a bone the
animator cannot edit. After the change the sword's own keys ARE the weapon
animation — grabbable, editable — and `weapon_r` becomes a driven export bone,
exactly what `camera_bone` already is.

## The Add flow

`attach.attach` gains a second bone. `parent_bone` — the DAG parent of
`weapon_r` (on Manny: `hand_r`) — is where the mesh parents; `drive_bone` —
`weapon_r` itself, resolved from `entry.bone` as today — is what ends up
constrained. A `weapon_r` with no parent, or absent, refuses with a message.

1. **The previous weapon comes off with its animation.** If a marked node
   exists (under the hand, or — legacy files — under `weapon_r`), the bone is
   first baked back from it (`bonedrive.unlink`: bake `weapon_r` over the
   union of the playback range and the driver's key range while the
   constraint still drives, then delete the constraint), and only then is the
   node deleted. Deleting first would take the animation with it — the camera
   paid for this order already.
2. Import, single-mesh resolution, marker, `seat` — unchanged.
3. The mesh parents under `parent_bone` and is **snapped onto `weapon_r`**
   (world translate+rotate).
4. **`bonedrive.link(weapon, drive_bone)`**:
   - if `weapon_r` carries moving animation: a temporary
     `parentConstraint(bone → weapon, mo=False)` plus `bakeResults` puts that
     motion onto the weapon's channels, and the temp is deleted;
   - any animCurves on the bone's translate/rotate are cut (a constraint over
     a still-connected channel splices a pairBlend — the camera's trap);
   - `parentConstraint(weapon → bone, maintainOffset=False)`.

   `mo=False` is the design in one flag: **`weapon_r` lives in the sword's
   frame.** No offset to capture, no snap-then-capture dance, and the export
   is honest — wherever the sword is, the bone is.
5. **Grip offsets apply after the link**, so the bone follows the grip. With
   animation transferred the fields are quiet anyway (`is_animated`, the
   existing rule), so this only happens on an unanimated bone.

Ranges everywhere are the **union of the playback range and the driving
node's own key range** (trap 38's lesson from the export side: a range
narrower than the keys silently truncates them).

## Grip offsets: a new space needs a new name

The stored grip used to mean "the sword's channels under `weapon_r`". Now the
channels live under the hand, so the same six numbers mean something else —
and writing an old-space triple as under-hand channels puts the sword at the
hand origin, visibly wrong.

- New saves go to **`mayaSceneSetup_grip_<key>`**: raw under-hand channels.
- The old names (`mayaSceneSetup_offset_<key>`, `mayaWeapons_offset_<key>`)
  are read **only to migrate**: the old grip matrix is composed with
  `weapon_r`'s current local matrix relative to the hand
  (`bonedrive.composed_grip`, pure OpenMaya math — the sword's world position
  is identical in both schemes by construction), shown in the fields, and the
  first edit or Add writes the new name. The dialled LongSword grip survives.
- With no character bound the composition has no bone to read, so the fields
  show zeros until one is; old-space numbers are never displayed as if they
  were new-space.

This is the same read-legacy/write-new dance the weapons→scenesetup rename
already does, one layer further.

## Connect / Disconnect — «все должно работать так как сейчас»

`connect.connect` is untouched: `parent_out` lifts the weapon from the hand
exactly as it lifted it from `weapon_r`, the world motion re-baked onto its
channels; the `weapon → weapon_r` constraint targets the node, not the path,
so the bone keeps following through the re-parent (zero world drift is the
existing measured property of `parent_out`). `disconnect` returns the weapon
under the **hand** — the window passes the parent bone now.

## Remove Weapon — a new button, forced by the constraint

Today deleting the sword by hand is harmless. After this change it loses the
bone's animation (it lives on the sword) and leaves an orphaned constraint
under `weapon_r` (trap 4). So removal becomes a tool concern:
**Remove Weapon** = `bonedrive.unlink` (bake the bone back) + delete the
marked node. Refused while the hands ride the weapon or an aim exists — the
same guards Add already has, for the same reasons.

## The UE bridge re-links across a merge

`weapon_r` under our constraint would trip the trap-37 guard and every clip
import would refuse. **The user's call (2026-08-21): the bridge handles it
itself** rather than refusing:

1. Before the merge, find the target joints whose parentConstraint is driven
   by a `mayaWeapon`-marked node (`bonedrive.find_links` — read-only).
2. The rigged-skeleton refusal now fires on the **other** constrained joints
   only. If it fires, nothing has been touched — the check runs before any
   unlink.
3. Unlink each found bone (bake back, delete constraint), merge as today
   (the bone is a plain joint again: cleared, rewritten).
4. After the merge, **re-link**: cut the weapon's now-stale translate/rotate
   curves, snap it onto the bone, `bonedrive.link` — the weapon picks up the
   new clip's motion and drives the bone again. A clip that does not animate
   `weapon_r` leaves the weapon riding the hand at the bone's cleared pose.
5. The status line names the re-link.

Replacing the sword's curves is consistent with what the merge already does
to every bone — the import's contract is "the scene plays this clip".

The bridge reaches `bonedrive` through a **lazy, guarded import**
(`maya_scenesetup` missing → the bridge behaves exactly as today). The camera
is out of scope: `camera_bone` sits outside the skeleton subtree in practice,
so its constraint never reaches the guard; if that ever changes, this is the
mechanism to extend.

## Where the logic lives

New module **`maya_scenesetup/bonedrive.py`** — "a bone that follows a marked
node": `MARKER` moves here (attach re-exports it, so `attach.MARKER` keeps
working), `find_links` / `driving_weapon`, `link` / `unlink` / `relink`,
`bake_range`, `composed_grip`, autoKey guarded throughout (trap 14). Imports
`maya.cmds` and `maya.api.OpenMaya` only — a leaf module, so `attach` depends
on it and not the other way around, and the bridge can import it without
dragging the window in.

`attach.py`: the two-bone `attach`, `detach` (unlink + delete, shared by
Add-replace and Remove), `find_attached` unchanged in shape (the window asks
under the hand first, `weapon_r` second for legacy files). `window.py`: bone
resolution, the Remove button, the grip migration, statuses.
`animimport.py`: the three-step wrap around the merge.

## Proof

Unit tests: `composed_grip` against hand-computed matrices, the range union,
the ours/foreign constraint split for the bridge, attach's ordering (unlink
before delete) and the legacy-lookup fallback, window grip migration
(new-name wins, old-name composes, absent shows zeros).

Live (`verify_weapons.py` gains gates): after Add the sword's parent is the
HAND and `weapon_r` follows the sword 1:1 (drag the sword, measure the bone —
world matrices, trap 31); a pre-animated `weapon_r` ends up with its motion on
the sword's channels and unchanged world motion on the bone; replace and
Remove round-trip the animation back onto the bone (worst element ~0);
Connect/Disconnect still round-trips with the constraint live. The bridge
re-link gate needs a running editor and stays in `verify_uebridge_merge.py`
territory — added there, guarded on the editor being reachable.
