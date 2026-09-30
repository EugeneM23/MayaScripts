# One weapon socket for every rig, and the inventory in the hub's own look (2026-09-30)

The animator: «Давай сделаем дизайн инвентаря все же не в стиле диабло а в стиле нашего
интерфейса. Также сейчас некоторые виды оружия нужно поворачивать на 90, а некоторые сразу
встают в руку, давай сделаем так, чтобы по умолчанию все виды оружия вставлялись в руку
правильно без офсетов». Asked whether the Creep's weapon bones should follow the same standard
(it changes a shipped rig): «Yes, one standard».

## 1. What was measured first

In mayapy standalone, on the three shipped rigs, the fist at the bind pose in the weapon bone's
own axes (`scratchpad/measure_fist.py`). A hammer grip holds the blade (+Y of every catalog
model) along the knuckle line pinky → index, the model's width (X) along the metacarpals, and
its thickness (Z) along the palm normal:

| rig | knuckles in `weapon_r` | palm normal | metacarpals | zero-grip blade off the knuckles |
|---|---|---|---|---|
| Manny_Rig | +Z (0.978) | −Y (−0.988) | −X (−0.991) | **84.0°** |
| Orc_D_Rig | +Z (0.981) | −Y (−0.990) | −X (−0.991) | **85.2°** |
| Creep_Rig | **+Y** (0.995) | +Z (0.956) | −X (−0.929) | 5.8° |

- Manny's and the Orc's `weapon_r` are UE's own bone (the Orc has Manny's local values), with
  the grip line along +Z. `weapon_l` is its behaviour mirror, with the knuckles along −Z.
- Every catalog model lies along +Y, so on those two rigs every weapon stands a quarter turn off
  at zero grip. The animator's prefs hold exactly that correction: `mayaSceneSetup_offset_`
  Long Sword 02, Dagger 01 and Spear 03 = (90, 0, 0 / 0, 0, 0). Spear 01 and the Creep Sword
  have none stored.
- At (90, 0, 0) the blade is **11.9°** off the knuckle line and the thickness **8.8°** off the
  palm normal. That is the natural tilt of UE's socket, not an error.
- The Creep's weapon bones are ours (2026-09-24: `weapon_test` turned half a turn about Z,
  `weapon_l` made as its mirror). They are a quarter turn off UE's: the grip line lies along
  their +Y.
- **A UE clip retargeted onto the Creep gives its `weapon_r` UE's orientation in the hand**,
  because the helper bones are carried relative to their parent on a rotation-only rig
  (`transfer_bone(relative=True)`). Measured (`scratchpad/m2.py`, the Longsword combo through
  `run_retarget`): the Creep's `weapon_r` took the clip's local rotation (−23.4, −36.2, 10.7) at
  frame 0, the same as Manny's. A zero-grip Long Sword then stood **101.9°** off the Creep's
  knuckles, as it does on Manny. So the Creep's convention holds only at its bind pose.
- The Creep's `weapon_r` is an influence of `skinCluster5` and a member of `bindPose1`, has no
  children, no constraint and no keys. `weapon_l` is in `bindPose1` only.

## 2. The decision

**One socket, UE's.** Every rig's weapon bones follow UE's `weapon_r`, and one fixed turn takes
a catalog model's axes into it.

### 2.1 The socket turn

- `catalog.SOCKET_TURN = (90.0, 0.0, 0.0)`: the model's axes (blade +Y, width X, thickness Z)
  turned into a UE weapon bone's (grip line +Z, palm −Y). Rotate X 90 takes Y to Z and Z to −Y.
- `Weapon.frame` keeps its meaning, the model's OWN extra turn in its own axes (the Creep
  Sword's 45 about its blade). What a weapon node stores and uses is the composition:
  `bonedrive.socket_frame(frame)` = R(frame) · R(SOCKET_TURN), as an XYZ euler.
- Two call sites:
  - `attach.import_weapon` → `store_frame`;
  - `grips.for_hand`, the left hand's mirror.
- Everything downstream already reads the node's own frame and needs no change:
  - `place_at_grip`, `measured_grip` (the fields read 0 0 0 at zero grip);
  - `relink`;
  - `mirror_grip`;
  - the floor's `drive_socket`;
  - Connections' `_drive_bone`.
- A custom FBX from the field gets the turn too: it is taken to be authored in the catalog's
  axes, which is the only convention this tool has.
- **Weapons already in a scene keep the frame stored on their node** (identity, or the Creep
  Sword's 45), so they, their relink and their grips are unchanged.

### 2.2 The Creep's weapon bones

The Creep's `weapon_r` / `weapon_l` are turned into UE's convention in both assets, in place.
`make_creep_weapon_sockets.py` (mayapy) follows `make_creep_armature_layout.py`'s pattern.

- Row vectors, with Q in the bone's own axes: new world = Q · old world, so new local =
  Q · old local.
  - `weapon_r`: Q = Rx(−90), so its +Z comes onto the old +Y (the grip line) and its −Y onto
    the old +Z (the palm normal).
  - `weapon_l`: Q = Rx(+90), so its −Z comes onto the old +Y.
- The position is kept: only the rotate channels change (jointOrient 0 on both).
- **Idempotent by measurement, never by a flag.** A bone whose knuckle line already lies along
  its ±Z is left alone. One along its ±Y is turned. Anything else is refused by name.
- `skinCluster5`'s bindPreMatrix for `weapon_r` is re-expressed as `WM⁻¹` at the new bind, and
  the bind pose is saved again whole over every joint and the Null (trap 79's rule, the layout
  script's `whole_bind_pose`).
- Checked unchanged:
  - every other joint's world matrix;
  - every vertex, and the skins at their bind;
  - on the rig, the world under a pose of Main / RootX_M.
- Saved as `.ma` in place, Maya's script nodes cut (trap 74), banned words refused.
- **The Creep Sword stays where it stood on the Creep, exactly.** Its node world is
  R(0,45,0) · Rx(90) · Q · B_old = R(0,45,0) · B_old, because Rx(90) · Rx(−90) = I.
- The pipeline's order gains the script as its last step, after the layout script.

What the change costs:
- A Creep added to a scene before this has the old bones; re-add it (the precedent of every
  Creep asset change).
- A clip exported from Maya off the OLD Creep skeleton carries `weapon_r` in the old
  orientation, and a weapon on it stands a quarter turn off. Cascadeur's own Creep clips carry
  `weapon_test` and are not affected.
- The animator's `Animations/Rigs/Characters/Creep_Skeleton.fbx` is their file; it is re-exported
  only if they ask.

### 2.3 The remembered grips

A stored grip G was dialled against the old zero R(frame) · B. It is re-expressed once, so the
weapon stands where the animator put it:

    G_new = G_old · R(frame) · R(socket_frame(frame))⁻¹

For an identity frame that is G_old · Rx(−90). The animator's three (90, 0, 0) become exactly
0 0 0.

- `grips.migrate()` runs on the first read of any stored grip in a session.
- It is gated by the optionVar `mayaSceneSetup_gripSocket` = 1, written after the pass. It
  never runs twice, even across sessions.
- It walks every optionVar named `mayaSceneSetup_offset_*` (both hands) and
  `mayaWeapons_offset_*` (the legacy right hand).
- The frame is the catalog row's for the key, with a trailing `_L` stripped for the left hand;
  a key the catalog does not know (a custom FBX) uses the identity.
- A value that is not six numbers is left as it is: `unpack` already reads it as zeros.

### 2.4 The left hand

It stays as designed on 2026-09-29: an undialled left grip is the mirror of the right one
through the rig's own sockets. Both hands' zero grip therefore put the weapon correctly in the
fist. Manny's `weapon_l` is not the mirror socket of `weapon_r` (6.9 cm / 2.16°), so the left
fields show the mirror's numbers rather than zeros. The measured values are reported after the
build.

## 3. The inventory in the hub's look (style B)

`maya_invlook.PALETTE` stops being Diablo's. It IS `maya_hubstyle.TOKENS` (both stdlib), so the
inventory can never drift from the hub's colours. `TITLE_FONTS` and the serif small caps go; the
window uses the UI font, as the hub does. The layout is unchanged.

| element | now (Diablo) | becomes (hub) |
|---|---|---|
| window | bronze bevel, corner diamonds, ground #16110c | `panel`, rounded 8, a 1 px `line` outline (translucent top-level) |
| title | gold serif small caps, centred, a bronze rule | «Inventory» bold `text`, left, after the `backpack` icon in `muted` (`maya_hubqt.pixmap`) |
| close | bronze ✕ | `muted` ✕; `hover` face and `text` under the mouse |
| character name | parchment, centred | `muted`, small, left, as a card subtitle |
| hand slot | cell floor, bronze border, label below | a `card` (rounded 8), label «Right hand» / «Left hand» in `muted` small at its top, the weapon on a `field` well (rounded 6) |
| slot under the mouse / valid drop | green border | the hub's active card: `card_active` face, 2 px `accent` outline |
| slot being dragged from | red border | `danger` outline |
| «on the floor» | parchment on dark | a `status` pill, `status_text` |
| grid | cell floor, bronze border, brown lines | a `card` holding a `field` well (rounded 6), cell lines `line` at low alpha |
| item under the mouse | Diablo blue | `hover`, rounded 4 |
| preview fits / no room | green / red fill | `ok_tint` fill + `ok` outline / `danger_tint` fill + `danger` outline |
| status | parchment text | the hub's message line: `status` rounded 6, `status_text` |
| ghost caption | bronze / red edge | a `card` pill, `accent` edge (fits) or `danger` edge, `text` |

The weapon icons themselves (steel, bronze guard, leather, wood) stay; they are the items.

## 4. Proof

- **Unit tests** (TDD):
  - `socket_frame` composition, including the identity and the Creep Sword's frame;
  - `import_weapon` storing the composed frame, and `for_hand`'s mirror using it;
  - the migration's arithmetic ((90,0,0) → 0, the Creep Sword's frame, the left hand's key,
    unknown keys, bad values, run once);
  - `PALETTE is TOKENS` and no hex colour in `maya_inventory`;
  - the window still painting in the offscreen renders.
- **`verify_weapon_socket.py`**, standalone:
  - Manny, Orc D and the rebuilt Creep, every catalog weapon at zero grip in the right hand: the
    blade within 15° of the knuckle line and the thickness within 15° of the palm normal on all
    three, and the fields reading 0 0 0;
  - the left hand's default grip (the mirror) putting the blade within 15° of the left
    knuckles;
  - the Creep Sword on the Creep where the old asset stood it (the old asset read from git);
  - a UE clip retargeted onto the Creep keeping a zero-grip sword in the fist at three frames
    (was 101.9°);
  - a seeded (90,0,0) migrating to 0 and placing the sword where the old grip did.
- The Creep asset verifies re-run: `verify_creep_rig_asset.py`, `verify_creep_skeleton_asset.py`,
  `verify_weapon_space.py`, `verify_creep_bind_pose.py`, `verify_inventory.py`.
- The live inventory stages in a disposable Maya on port 7003, and a photograph of the restyled
  window.

## Addendum — what the build found (2026-09-30)

- **Measured after the build**:
  - Zero-grip blade off the fist's grip line:

    | rig | right hand | left hand (the mirror) |
    |---|---|---|
    | Manny | 11.9° | 11.9° |
    | Orc D | 11.3° | 11.3° |
    | Creep | 5.8° | 5.9° |

  - Manny's left fields show the mirror (1.38, −1.58, −179.51) / (6.62, −0.98, 1.71). The Creep's
    left zero grip now mirrors like Manny's, a half turn about the thickness.
  - The Creep's thickness sits 17.0° off its palm normal: its socket's own roll, the creature's
    `weapon_test`, unchanged by a turn about X.
- **The inventory remembered grips it had only computed.** `equip.to_hand` stored the left hand's
  mirror as if it had been dialled, so the next rig got Manny's numbers. It remembers nothing now.
- **Euler flips between keys** in the weapon and helper-bone bakes: a UE take on the Creep held the
  sword exactly at every key while its curves stepped up to 538°. Both bakes are euler-filtered now:
  17.1° at most, equal to Manny's.
- **A weapon node added before the turn** reads and dials in the standard (`grips.standard` /
  `on_node`), so an old scene's sword at (90, 0, 0) reads 0 0 0 and a re-Add adds nothing.
- The installed copy was not refreshed: port 7001 stopped listening before the end of the build.
