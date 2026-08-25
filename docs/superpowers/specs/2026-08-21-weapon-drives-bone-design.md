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

## Addendum (2026-08-25): the grip rides the transfer

Step 5 above — «grip offsets apply after the link… this only happens on an
unanimated bone» — shipped as designed and turned out to be the design's one
wrong call. The user's report: «когда мы добавляем оружие то офсеты смещения
поворота и позиции больше не учитываются». The report is exact. A UE clip
animates `weapon_r` (this spec's own measurement), so in any scene holding an
imported clip `moves(bone)` is true, the transfer runs, and the grip write
was skipped — every Add in the user's real workflow silently dropped the
dialled offsets. Under the pre-redesign scheme they always applied: the sword
was a DAG child of `weapon_r`, so its local grip channels composed with the
bone's animation for free. The inverted drive has to do that composition
explicitly, and didn't.

Three changes, one semantic: **the grip is not the clip's to flatten.**

1. **`attach.attach` writes the grip BEFORE `bonedrive.link`** (when given —
   the None-means-stay-on-the-bone rule is unchanged), and the transfer's
   temporary constraint is **`maintainOffset=True`**: the bake keeps the
   sword's current offset from the bone, which is the grip just written —
   and the identity when nothing was, so a grip-less attach and the bridge
   relink bake byte-identically to the old mo=False. On a clean bone the
   order swap changes nothing observable: the sword holds the grip channels
   and the mo=False final constraint puts the bone on it, exactly as
   grip-after-link did. The final constraint stays mo=False — the bone
   lives in the sword's frame, grip included; that half of the design
   stands.

2. **The grip is remembered on the marked node itself**
   (`mayaWeaponGripRotate` / `mayaWeaponGripTranslate`, written by
   `attach.write_offsets` whenever its target carries the marker). The
   optionVar is window policy the bridge must not reach into, and an
   attribute travels with the scene file. **`bonedrive.relink` re-applies
   it** between the snap and the link, so a clip import no longer flattens
   the grip either — before this, the first Refresh-import after an Add
   undid the dialled grip even on a clean bone. A legacy sword with no
   stored grip keeps the snap-only relink.

3. **The window's fields always show the GRIP, never the animation.**
   `refresh` over an animated weapon used to show the sword's current-frame
   channel values; a re-Add then saved those frame values into the
   optionVar as if they were a grip — quietly destroying the remembered
   one. Now an animated weapon's fields show the remembered grip (what the
   next Add or import applies), a clean weapon's channels remain the truth,
   and `add_weapon` re-runs `refresh` first so fields last filled in an
   unbound window cannot be applied and saved as zeros. Typed values
   survive the re-read — typing fired `offsets_changed`, which remembered
   them.

Why the no-compounding property holds on re-Add: the grip write is ABSOLUTE
(under-hand channels), so re-adding over a bone that already plays the
grip-shifted motion captures an offset of ~identity and the sword's track is
unchanged — measured as a gate. The one semantic consequence to know: with
animation transferred, the exported bone now carries grip∘clip rather than
the clip verbatim. That is this design's own philosophy («wherever the sword
is, the bone is») extended to the animated case, and it is what «офсеты
учитываются» means under an inverted drive.

Proof: unit tests updated (the transfer keeps the grip, the store
round-trips, relink re-applies, order pinned) — 1035 green. Live:
`verify_weapons.py` gained a self-contained grip section (runs only when the
script owns the bone's animation; restores every channel it touches) — grip
kept across the transfer, re-Add compound-free, relink under the same grip.
Awaiting its live run at the next open port.

## Addendum 2 (2026-08-25, the same day): the bone's animation is inviolate

The addendum above closed the report by letting the bone follow grip∘clip —
«wherever the sword is, the bone is» extended to the animated case. The
user rejected the shifted bone on sight: «Теперь ты изменяешь позицию
weapon bone… главное чтобы наша анимация сохранилась в исходном виде». That
settles the question the first addendum called "the one semantic
consequence to know", and settles it the other way: **the grip is a
Maya-side model correction — how the imported FBX sits relative to the
bone — and must never reach the export bone.** The game attaches its own
weapon model to `weapon_r` with its own socket; exporting grip∘clip would
double that correction in engine.

The scheme that satisfies all three constraints at once (grip visible on
the sword; bone bound to the sword; bone's track byte-original) is the
final constraint flag: **`parentConstraint(weapon, bone,
maintainOffset=True)`** — the camera's own flag, as it happens. At capture
time the sword stands at grip∘clip(f) and the just-cut bone stands frozen
at clip(f), so the captured offset is exactly the grip's inverse, and
bone(t) = grip⁻¹ ∘ grip ∘ clip(t) = clip(t) for every frame — algebra, not
approximation. With no grip the offset is the identity and nothing about
the grip-less paths changes. Everything downstream follows for free:
`unlink` bakes the bone back to the ORIGINAL clip (better than before, which
baked grip∘clip), the bridge's relink re-links the new clip under the same
inverse, Connect's `parent_out` keeps the offset because the constraint
targets the node, and the export (`animexport` bakes the skeleton) carries
the clip verbatim.

Two consequences that needed their own work:

1. **The offset is captured on a SAMPLED frame.** After the transfer the
   sword is a baked curve; a capture at a fractional currentTime compares
   an interpolated sword against the bone's exact cut value and rides that
   error on every frame for ever. `link` jumps to the range start (always
   a sample) for the cut-and-constrain, then puts the time back — only
   when a transfer ran; a static sword evaluates exactly at any time.

2. **A live grip dial must not write channels under the live constraint** —
   the bone would follow the sword by the OLD offset and leave its track.
   `bonedrive.regrip` (now what `offsets_changed` calls) drops our
   constraint (the bone freezes exactly where the invariant held it),
   writes the channels and the stored grip, and remakes the constraint
   capturing the new offset: the sword moves, the bone does not. A bone
   with no constraint (legacy file) or somebody else's keeps a plain
   write; a foreign constraint is not ours to rehook.

A file saved with yesterday's mo=False constraint keeps behaving as saved
until the next Add or import rebuilds the link; no migration — the files
are days old and the user re-adds constantly.

Proof: 1043 unit tests green (regrip order and refusals, the sampled-frame
pin, the flipped final flag). `verify_weapons.py`'s grip gates now measure
the ruling itself: the bone plays its ORIGINAL track under the grip, after
a re-Add, and after a relink onto a new clip; Add with a grip does not move
a clean bone; a live re-dial moves the sword to the new grip and the bone
not at all. Awaiting the live run at the next open port.

## Addendum 3 (2026-08-25, later the same day): the grip is BONE-relative

Addendum 2 shipped, the port came up, the no-grip story proved green live
(31/31 in the real scene, on a real clip carrying 47 frames of `weapon_r`)
— and the user pressed Add: «Сейчас оружие подставляется в позицию кисти а
должно подставляться в позицию weapon bone… с указанными офсетами». The
sword landed at the HAND. Root cause: the grip's SPACE. Since 2026-08-21
the fields meant "raw channels under the hand" — zeros put the sword at
the hand origin, and any number the user types means nothing they can
picture. The user thinks — and the same message says so explicitly — in
offsets **from the weapon bone**: zeros = exactly on `weapon_r`, the numbers
they dialled before the redesign. Their post-redesign typing had been saved
into the under-hand optionVar as if it were hand-space, which is precisely
what put the sword at the wrist.

The ruling collapses the whole under-hand construction:

- **The grip means "offset from `weapon_r`" everywhere** — fields, saved
  optionVar, the copy stored on the node. Application composes at APPLY
  time: `place_at_grip` = grip × the bone's WORLD matrix, two snap-style
  xform writes, so the weapon's DAG parent (still the hand — that part of
  the design stands, a node cannot both parent the weapon and follow it)
  never enters the math. `apply_grip` = place + store-on-marked; it is the
  one grip application shared by attach, relink and regrip. `measured_grip`
  (world matrices through the pure `grip_between`) is the read-back, so the
  fields show a hand-nudged sword honestly.
- **The transfer offset now IS the grip, exactly.** mo=True maintains the
  offset in the bone's frame; a bone-relative grip is constant there, so
  sword(t) = grip ∘ clip(t) with no capture-frame dependence — Addendum 2's
  under-hand scheme had a small f0-dependence where the clip animates
  `weapon_r` against the hand; that artifact is gone by construction.
- **The old optionVars come back verbatim.** Bone-relative is the
  pre-2026-08-21 meaning, so `mayaSceneSetup_offset_<key>` (and the legacy
  `mayaWeapons_offset_<key>`) read with no composition — the LongSword grip
  dialled before the inverted drive returns. The under-hand name
  (`mayaSceneSetup_grip_<key>`, four days old) is deliberately never read:
  its numbers are junk in the bone space. `grip_values`, the
  composed-migration and `attach.write_offsets`/`read_offsets` are gone
  rather than disabled, with gone-tests: a raw channel write lying around
  is how the next reader applies a grip in the wrong space again.
- A file saved during the four under-hand days carries an under-hand
  stored-grip attribute that the new code reads as bone-relative; the
  first re-Add rewrites it. No migration — the attribute is days old.

Everything Addendum 2 established stands: grip before link, both
constraints mo=True, the bone byte-original, the sampled-frame capture,
regrip's drop-place-remake.

Proof: 1036 unit tests green (the space pinned in attach's flow via
`apply_grip`, regrip placing instead of writing, `grip_between` inverting
`composed_grip`, the window's under-hand policy gone). Live the same day,
sandbox chain over the bridge, **13/13, every number 0.0000000**: sword at
the bone-relative grip over an animated bone, offset kept across the
transfer, the bone on its original track, unlink restoring it, relink onto
a rewritten clip under the same stored grip, a clean bone unmoved by Add
and by a live re-dial, and `measured_grip` reading the dialled numbers
back from world matrices. `verify_weapons.py` re-ran green 31/31 in the
real scene under the final build; its in-scene grip gates (bind-pose scene
required) remain pending.
