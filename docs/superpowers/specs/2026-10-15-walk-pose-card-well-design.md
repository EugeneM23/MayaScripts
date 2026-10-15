# Walk Builder: the pose is a Pose Library card dropped into a well (2026-10-15)

The animator, after asking why a pose put on the mean pose rig walks worse than a saved pose: «А мы можем
сделать вместо строчки pose окошко для карточек которые будем перекидывать драгом прямо из библиотеки поз?»
Asked:

- **only the library** (recommended): the well takes Pose Library cards; the old `.wpose` poses are moved into
  the library once as cards; Walk Builder's Save pose goes (a pose is saved with the library's + Save);
- **follow the card, with a copy** (recommended): a walked skeleton reads its pose from the card on every
  re-key, so the card's Update from selection is taken; a copy of the pose's bones on the skeleton keeps the
  walk working when the card is renamed or deleted, and the line says so.

«Да, делай до конца».

## Why it fits

A pose card's `bones` are `{leaf: {parent, canonical, rest, world, rotateOrder, [drive]}}` - the `.wpose` bones
plus `rotateOrder` and, on a card saved from a rig, `drive`. `walkpose.prepare` hands the bones to
`posemath.Transfer`, which already reads a rig card's four unrolled limb bones a side in their drive form where
the target has no twist bones to carry the roll (`drive_bones`). So a card is a Walk Builder pose as it stands.

The original question is answered by the same road: a pose made on the mean pose rig, saved as a library card
and dropped into the well, goes through the Pose knob (grip, Balance, Leg match, Gait lean) instead of the rig's
plain correction.

## The well

The card's `Pose` row (a dropdown and Save...) is replaced by a well: a square cell (the hub's `field` well, the
card's thumbnail, its name under it; empty: «Drop a pose card here» and a muted figure). Beside it, on the right:
the Pose share slider and the part chips, as before. Right button: «Show in Pose Library» (the library opened, the
card picked) and «Clear». A click on a filled well shows the library too.

`maya_walk/posewell.py` (Qt, lazily): a widget laid over the `cmds` placeholder `skeldarWalkPoseWell` (the
portraits' `attach` + Keeper pattern), registered per scope (`hubcopy.resolve`), so the hub's card and every popup
copy each have their own. `well_at(gx, gy)`: the standing well whose global rect holds the point, or None.
Without Qt (the classic hub with no PySide) the placeholder holds a text naming the card; the library cannot drop
there - the card is then set by the Pose Library's right button «Use in Walk Builder» (below).

## The drop

`maya_poselib.window.aim` checks the walk wells BEFORE «over the window / the hub: nothing»:
`{"kind": "walk", "well": ...}`; the ghost reads «two_handed_sword · Walk Builder pose». The release calls the
well's (scope-bound) `take(path)` → `maya_walk.panel.take_card(path)`:

- an animation card or an objects card: refused, «only a pose card of a character», nothing changed;
- the card remembered (`skeldarWalk_poseCard` = its path relative to the library), the well redrawn;
- the Pose share at 0 is set to 1 (a pose dropped to do nothing would read as broken; said);
- a target standing: re-keyed now, as a released knob does.

The library's card right button gains **Use in Walk Builder** (the same `take_card`), for the classic hub and for
the hub closed.

## Storage

`maya_walk/cards.py`:

- `library_root()` - the Pose Library's own root (`store.library_root(optionVar, plugin)`);
- `read_card(path)` → `(name, bones)`, refusing what is not a character pose card;
- `pack(bones)` / `unpack(text)` - gzip + base64 of the bones' JSON;
- `resolve(card_rel, copy_text, legacy_name, folder)` → `(name, bones, note)`: the card when it reads; else the
  copy («pose card X is gone - using the copy on the skeleton»); else a legacy name → the migrated card
  `Walk poses/<name>.pose`, then the `.wpose` file; else None.

The marker `skeldarWalk` keeps `pose` (the name, for the subtitle), gains `pose_card`; the pose's bones as last
used go into a second string attribute `skeldarWalkPose` (packed). `scene.apply` takes a pose REFERENCE
(`{"card": rel}` or a legacy name) instead of a name; `prepared_pose` is cached by the card's `pose.json` time.
`pick` answers the card; the card's well shows it.

## The old poses

`cards.migrate(folder, library)` on the card's build: every `<name>.wpose.gz` in the walks folder not yet listed
in `<folder>/library_poses.json` is written as the card `Walk poses/<name>.pose` (kind character, every bone a
member, character label = the name, no thumbnail - the grid draws its placeholder), and listed, so a card the
animator deletes is not made again. The `.wpose` files stay. A name already taken in the library is skipped and
listed.

## Not built

A card's own regions narrowing the walk's parts (the walk keeps its five chips); an animation card's frame as a
pose; following a card across a rename (the copy takes over, said).

## Proof

Unit tests: `read_card` (a pose card, a rig card with `drive`, refusing an animation / objects card), pack round
trip, `resolve`'s three roads and its note, `migrate` (made once, a deleted card not made again, a taken name),
the panel's `take_card` on a fake cmds (remembered, share set to 1, refusal changes nothing), the library's `aim`
on the walk kind and `drop_caption`. Headless verify: the two-handed sword from its `.wpose` and from its
migrated card key the same curves; a card deleted after Apply re-keys from the copy. The live drag is the
animator's.
