# The weapon inventory: two hands, the floor, and a Diablo window (2026-09-29)

The animator: «Возможно ли сделать во вкладке Weapon кнопку которая будет инвентарь похожий на
инвентарь как в игре diablo что бы я оружие переносил из этого инвентаря прямо на персонажа и оно
как вставлялось в руку или выпадало на пол?» Asked in the brainstorm and answered:

- **A weapon dropped on the floor is the CHARACTER's** (over "a free prop" and "nothing"): it lies
  on the floor and its hand's weapon bone follows it — the Connections "World" state — so a pickup
  can be animated from there and the export carries it through the bone.
- **Two weapons per character, one per hand** (over "one"): a sword in the right hand and a dagger
  in the left at once.
- **A weapon dropped into an occupied hand REPLACES** what is there (over "the old one falls to the
  floor" and "refuse") — Weapons > Add's rule.
- **Look A, Diablo** (dark bronze, gold serif title, the grid) over B, the hub's own style.
- «делай все» — build all of it.

## Measured before anything was decided

- **Two hands are already structurally independent.** Each hand has its own weapon space
  (`weaponspace.ensure_space(hand)`), its own drive bone (`weapon_r` / `weapon_l`), and
  `attach.attach(entry, hand_l, weapon_l, ...)` would put a dagger in the left hand without
  touching a sword in the right. What assumes ONE weapon is Connections (`weapon_of(rig)` answers
  one node, the scheme is one weapon's), the Weapons panel (every press on the catalog row's bone,
  `weapon_r`), and `window._attached`, which reads a weapon out in world as "the hands ride it".
- **The left socket is not the mirror of the right one, and not the same way on every rig.**
  The hands are UE's behaviour mirror on every rig we ship: `hand_l = F · hand_r · Mx` (F the three
  axes negated, Mx the world X mirror) to **0.0003 cm / 0.0001°** on Manny_Rig, Orc_D_Rig and
  Manny_Skeleton, **0.045 cm / 0.001°** on Creep_Rig. The weapon bones are not:
  - Manny, Orc: `weapon_l` stands **6.91 cm / 2.16°** off the mirror of `weapon_r` (weapon_r sits
    at (−6.62, −1.69, 0.98) in the hand, turned 1.6°; weapon_l at (0, 3.4, 0), unturned), and at
    ZERO grip a sword in the left hand points its blade **backwards** — the left blade against the
    mirrored right blade reads **−0.9993**.
  - Creep: our own `weapon_l` (made as the mirror of `weapon_r` on 2026-09-24) is a geometric
    mirror — zero grip already mirrors, **+1.0000**.
  So a left-hand grip cannot be "the same numbers" or one fixed formula: it is computed from the
  rig's own sockets (below).
- **The catalog's models**, imported: Long Sword 147.0 cm (−31.1..115.9 on Y, guard ±15.6),
  Spear 01 266.2, Spear 03 199.6, Dagger 114.3 × scale 0.4 = 45.7, Creep Sword 124.0. One mesh
  each, one plain lambert each (0.5 grey; Spear 01 brown; the rest 0.55 steel) — no model says
  which part is blade and which is grip; Spear 03 has its PNG.
- **Where the mouse can go.** A press in one of our Qt widgets captures the mouse on Windows: the
  moves and the release keep coming to that widget over Maya's viewport, which never sees them —
  so the drag is ours from start to finish and Maya's own drop handling (which would try to
  import or evaluate a dropped payload) never enters. `cmds.getPanel(underPointer=True)` names
  the panel under the cursor; `M3dView.getM3dViewFromModelPanel` gives its camera for
  `worldToView` / `viewToWorld`. A drag never moves the camera or the time, so everything about
  the characters can be read once when it starts.

## The three layers, in order

Each layer is built and verified before the next; the inventory is the last and only calls the
first two.

### 1. Two weapons per character

**The Weapons section gains a hand**: a segment row `Hand [Right | Left]` under the weapon list
(`iconTextRadioCollection` `mayaSceneSetupHand`, remembered in the optionVar
`mayaSceneSetup_hand`). Add, Remove, the grip fields and Recolour act on that hand. The bone is
the catalog row's bone for the right hand and its left twin for the left (`side_bone`: a trailing
`_r` becomes `_l` — `weapon_r` → `weapon_l`; a custom FBX follows the same rule). A rig without
`weapon_l` answers the existing "has no bone 'weapon_l'".

**The grip is remembered per hand.** Right: `mayaSceneSetup_offset_<key>` exactly as today
(legacy name read second, unchanged). Left: `mayaSceneSetup_offset_<key>_L`. A left hand with
nothing remembered gets the **mirror of the right grip**:

    G_l = Mz · G_r · Fr · K · Fr⁻¹,   K = S_r · F · S_l⁻¹

(row vectors, 4×4; `Mz` the model's thickness mirror — every catalog weapon lies with its
thickness on Z; `Fr` the weapon's frame, `bonedrive.FRAME_ROTATE`; `S_r`, `S_l` the weapon bones'
LOCAL matrices in their hands, read at the current frame — no clip on this disk moves them, trap
83; F the hands' behaviour-mirror map, which every shipped rig has to 0.045 cm). Derivation: we
want the left weapon to stand as the world mirror of the right one, `G_l·Fr·B_l =
Mz·G_r·Fr·B_r·Mx`, with `B = S·H` and `H_l = F·H_r·Mx`. `mirror_grip(rotate, translate, frame,
socket_r16, socket_l16)` is pure (`bonedrive`). Measured target: at the build pose, the left
weapon against the mirror of the right one to the hands' own residual (0.0003 cm on Manny).

**`linked` means "the hands ride it" again.** `window._attached` reports a weapon out in world
that drives the bone as the hand's weapon with `linked` False unless a hand's IK control actually
rides it (`connections.followers_of(weapon)`, the proxies inside it) or the legacy OverRig-rig
link holds it. So Add replaces, and Remove removes, a weapon standing in world (on the floor)
that nothing rides; one that hands ride is refused by name as before. **Add into a hand that
follows a weapon is refused** («Hand_L follows the Long Sword 02 - release it in Connections
first»): a hand holds XOR follows (below), in every path that puts a weapon into a hand.

**`attach.detach` takes off a weapon in world too**: the bone's weapon is found in the hand's
space, then under the bone (legacy), then as the node driving the bone
(`bonedrive.driving_weapon`) when nothing holds it — and a weapon carrying a PARKED track (layer
2) gives the bone that track back instead of baking. The one removal every path shares.

**`attach` records where a weapon came from**: `mayaWeaponSource` = the FBX path, so a weapon can
be put into another hand from the inventory by re-importing it (a custom FBX too).

**Connections works on ONE weapon at a time, chosen** — the model stays the per-weapon scheme it
is, which keeps the three rows, every pure function and the 360 px dock as they are:

- `weapons_of(rig)`: every weapon of the rig — driving `weapon_r` / `weapon_l`, in either hand's
  space, or holding one of the rig's proxies — deduplicated, right-hand-related first.
- **The chosen weapon**: the selection's (a weapon, anything under it, one of its proxies), else
  the segment picked in a new top row `Weapon [<A> | <B>]` (shown only with two), else the first.
  Labels are the catalog labels from the marker key, with `(R)` / `(L)` when two share one.
- `read_scheme(rig, weapon)` is that weapon's scheme; `other_scheme` is the other weapon's.
- **A hand holds XOR follows, across both weapons** — the rule that makes a cycle impossible (a
  holding hand rides nothing, so every chain ends on a holding hand). `blocked(wanted, other,
  other_label)` (pure) refuses before anything moves:
  - «Hand_L holds the Dagger 01 - move it first» — hanging into, or following with, a hand the
    other weapon hangs in;
  - «Hand_L follows the Dagger 01 - release it first» — the same for a hand riding the other one;
  - «weapon_l is driven by the Dagger 01 (in world) - remove it or put it in a hand first» —
    hanging into a hand whose bone the other weapon, out in world, drives.
- The drive bone is THIS weapon's: `driven_side(rig, weapon)`; a hang unlinks only this weapon's
  old bone. A hang also drops a parked track (layer 2): once a weapon is in a hand, the bone's
  truth is the weapon's motion.
- The hotkeys' `connect` / `disconnect` act on the chosen weapon.
- With one weapon nothing on screen changes (the chooser row is hidden).

**Everything downstream already handles both bones** — the retarget's `carry_helpers` unlinks
and relinks `weapon_r` and `weapon_l`, the bridge's merge uses `find_links` over every joint, the
export writes bones only. Proven with a second weapon in the scene, not assumed.

### 2. A weapon on the floor

`maya_scenesetup/floor.py`.

- **Lying**: the weapon is imported like Add's (`attach.import_weapon` — the import, the mark, the
  seat, the colour or texture, split out of `attach`), stays at world level, and is placed flat:
  its thickness (model Z) straight up, its blade (model Y) along the given heading — the camera's
  right, projected on the floor — its bounding box's centre over the hit point, its lowest point on
  the floor (Y = 0). `lying_pose(bbox, scale, point, heading)` is pure.
- **The bone follows it**: the side's drive bone is constrained to the weapon with no offset and
  the weapon's frame undone (`bonedrive.drive_socket`, moved out of `connections._drive_bone`,
  which then uses it). The weapon is exactly the Connections "World" state; Weapon → Hand_R /
  Hand_L there picks it up (re-baked, the weapon still lying where it was until the animator keys
  it into the hand).
- **The bone's own track is PARKED, not lost** (the animator's standing rule: «главное чтобы наша
  анимация сохранилась в исходном виде»): before the constraint each of the bone's six channels
  moves onto the weapon — an animCurve is reconnected to a matching attribute
  `skeldarPark<Channel>` (doubleLinear / doubleAngle), a plain value is copied — and
  `skeldarParkBone` records the bone's UUID. Taking the weapon off while it is still out in world
  reconnects the curves (or writes the values) and drops the constraint: the bone is exactly as it
  was before the drop. A hang in Connections drops the parked data (above).
- **A retarget or a clip import keeps a floor weapon on the floor**: `bonedrive.relink` on a
  weapon no hand holds re-parks the bone's FRESH track (the new clip's) and re-drives the bone —
  it no longer snaps a world weapon onto the bone. Taking it off afterwards gives the bone the new
  clip's track.
- **Whose, which bone**: the character nearest to the hit point on the floor (its skeleton root's
  horizontal distance); its free side, right first — "free" meaning the hand holds nothing and no
  weapon drives its bone; both taken → the right hand's weapon is replaced. A weapon being replaced
  that hands ride is refused by name.

### 3. The inventory window

**Opened** by an `Inventory` button in the Weapons section (and a hotkey row `window.inventory`).
A frameless Qt tool window over Maya, moved by its title, position remembered
(`skeldarInventoryGeometry`), found by its object name so an update replaces it (traps 75 / 102).

**Look A**: near-black brown ground, bronze bevelled frame, the title «Inventory» in a gold serif
(Palatino Linotype / Georgia), the character's name under it; two hand slots (2 × 4 cells each,
«Right hand» / «Left hand»); the grid, 10 × 5 cells of 40 logical px; a status line at the bottom
in parchment. Painted with QPainter (a stylesheet cannot draw bevels), every pixel × the display
scale (`mayaDpiSetting -q -realScaleValue`, trap 98).

**The grid is the catalog** — every row always there, taken as often as wanted, by any
character. Packed column by column in catalog order (`pack`, pure). An item's size comes from its
model: one cell wide, `h = clamp(round(2 + (L − 45) / 55), 2, 5)` tall — Dagger 2, Creep Sword 3,
Long Sword 4, both spears 5.

**Icons** are rendered from the models by `docs/superpowers/plans/make_weapon_icons.py` (mayapy
standalone, offscreen QPainter): the model's own triangles projected along its thickness axis,
flat-shaded by a light from the upper left, painted back to front; steel above the grip, bronze
where the guard widens, leather below it, wood along a thin shaft; Spear 03 sampled from its
texture. Written to `assets/weapon_icons/<key>.png` at twice the cell size, with
`assets/weapon_icons/weapon_icons.json` (`{key: {"cells": [w, h], "length": cm}}`). A row with no
icon draws its label in a plain box — never a refusal — and a test pins that every catalog row has
one.

**The paper doll**: the current character (`skeleton.current_root`: the selection, else the only
rig, else the only skeleton); each slot shows that side's weapon — in the hand (lit), on the floor
driving the bone (dimmed, «on the floor»), «follows <label>» when the hand rides a weapon, or
empty. Refreshed on selection change, undo/redo and scene open (one scriptJob, killed with the
window), and after every action.

**The drag**: press on an item (grid or slot) → a translucent frameless ghost with the icon
follows the cursor, a caption under it naming the target — «Manny_Rig · right hand», «floor ·
Manny_Rig1 · weapon_l», «Left hand», «back to the inventory», «no target». Esc or the right button
cancels. The release does the action:

| From | Onto | Action |
|---|---|---|
| grid | a slot, or a hand in the viewport | into that hand (Add's rule: replaces) |
| grid | the floor in the viewport | onto the floor (layer 2) |
| slot | the grid | take it off |
| slot | the other slot, or a hand in the viewport | take it off, put the same weapon into that hand |
| slot | the floor | take it off, drop the same weapon on the floor |

Each is ONE undo chunk; each refusal changes nothing and says why on the status line (and the
Weapons section's).

**The viewport target** (`maya_scenesetup/droptarget.py`): at drag start every character (rigs'
game skeletons and bare skeletons) is read once — its joints' world positions, its bones as
parent→child segments, its two hands (the drive bones' parents), its root; per move they are
projected through the panel under the cursor. `choose(point, characters, floor_hit)` (pure):
a character whose nearest bone segment on screen is within `R = max(16, 0.08 × its projected
height)` logical px is ON (the nearest by distance / R; ties to the one nearer the camera) and
the target is its hand nearer the cursor on screen; otherwise the floor under the cursor (the
camera ray through the point meets Y = 0 in front of the camera) and its owner (layer 2);
otherwise no target («no floor under the cursor»). No ray against meshes: bones are what every
character has, skeletons without skin included.

## Not built

Rearranging items inside the grid; custom FBX files in the inventory (they stay in Weapons);
picking a weapon up from the floor at a chosen frame; a raycast against meshes; more than two
weapons per character; a weapon without a character (a free prop).

## Proof

- Unit tests on every pure half: `side_bone`, `mirror_grip` (the zero right grip on a
  behaviour-mirrored socket pair gives the backwards-blade correction; a geometric pair gives the
  identity), `blocked`, the chosen-weapon rule, labels for two weapons of one key, `lying_pose`,
  the park plan, `choose`, `pack`, the window's hit tests; the Weapons panel's hand row on the fake
  `cmds`; the inventory widget offscreen (it builds, paints ink, hit-tests, runs a drag on a fake
  scene adapter).
- `docs/superpowers/plans/verify_inventory.py`, mayapy standalone on a Manny rig and a Creep rig:
  sword right + dagger left, both driving their bones; the left weapon against the world mirror of
  the right at the build pose; a spear on the floor lying flat (lowest point 0.000), the bone on
  its socket, the parked track back to the frame on removal; a retarget with all three — both
  hand weapons carried, the floor spear still on the floor, the new clip's track parked; the
  export bones only.
- `verify_connections.py` unchanged and green (one weapon), plus two-weapon gates in the
  disposable Maya (OverRig needs a live one): the chooser, each refusal, both moves.
- The drop in a disposable GUI Maya: the window open, `drop_at(global point)` onto a projected
  hand and onto the floor — everything but the mouse itself. The mouse is the animator's to try.
