# Armor: the Tech Limb out of Atone, a card that equips it (2026-10-01)

The animator, with the Atone editor open: «Давай из нашего aton game ... достанем technolimb сам его
fbx и добавим его как оружие в наши ассеты с возможностью одеть. Только давай не будем добавлять его в
панель с оружием а сделаем для него отдельную панель Armor в которой пока будет только техно лимб но
позже мы добавим еще разные варианты одежды и брони. Только в отличии от оружия не нужно делать
сетчатый инвентарь а просто будем выделять предмет нажимать кнопочку equip и он будет добавляться к
нашему персонажу в заранее указанное место».

Asked, and answered: the item is **the plate only** (`SM_Shield_Test`), and the card shows **icon
tiles** like the Characters portraits.

## What the Tech Limb is in Atone (measured over Remote Execution)

- `DA_Techlimb` (EquipmentItemData): display name «Tech Limb», `spawn_actor_class` `BP_Techlimb`,
  **`equip_socket` = `holster_socket` = `lowerarm_l`**.
- `UEquipmentComponent::AttachActorToSocket` attaches the actor with
  `SnapToTargetNotIncludingScale` to that socket on the character mesh. Neither
  `SKM_Manny_Simple_3p` nor `_1p` has a socket of that name (their five sockets: `weapon_r_muzzle`,
  `foot_r/l_Socket`, `weapon_r_socket`, `consumable_r_socket`), so the actor's root stands **on the
  bone**.
- `BP_Techlimb`'s components:
  - `SM_Shield_Test` (StaticMesh) on the root: location (0.0794, −0.5499, 0.3283), rotation (pitch
    1.1872, yaw 89.8174, roll 84.3156), scale 1.17647;
  - `Techlimb_Shield_Energy` (SKM_Techlimb_Shield_Energy, visible only while blocking — the BP's
    `SetupShieldVisibility`);
  - two Niagara systems.
  The C++ root `Mesh` holds no mesh. The forms' `Mesh` is null on all fifteen.
- `SM_Shield_Test`: 1526 render vertices, 848 triangles, one LOD, its source `C:/Users/MY
  PC/Desktop/S3.obj`, bounds 7.9 × 54.9 × 64.3 cm. The BP overrides its material with `M_TechLimb_Test`:
  opaque, default lit, base colour a constant (0.2896, 0.3091, 0.3125) linear, no textures.
- The two skeletal shields and the test blueprint's `SKM_Techlimb_Shield` are not used (the
  animator's pick).

## The asset: the game's placement baked into the points

The placement is the game's: `lowerarm_l`, then BP_Techlimb's offset. The weapons' rule since
2026-09-30 is «вставлялись в руку правильно без офсетов». So the shipped model's points are already
in `lowerarm_l`'s local axes (Maya's) at that offset and scale. Equipped, the plate's node stands at
identity in its space, its channels read 0 exactly where Unreal puts it, and a nudge by the animator
shows as a number.

The scripts that make it, in `docs/superpowers/plans/`:

1. **`export_techlimb_from_unreal.py`** (mayapy, `uelink`) writes `sources/armor/`:
   - `SM_Shield_Test.fbx`, the static mesh as Unreal exports it;
   - `techlimb_ue.json`, which holds:
     - the BP's placement and the equip socket;
     - the material's colour;
     - the plate's 1526 vertices in UE mesh space (`ProceduralMeshLibrary.get_section_from_static_mesh`);
     - the same vertices in UE component space, attached to `lowerarm_l` at `SK_Mannequin_proto`'s
       reference pose;
     - every bone's component-space reference transform.

   It refuses if the editor does not answer or the BP no longer carries what was measured.
2. **`make_techlimb_asset.py`** (mayapy standalone) works on the exported FBX:
   - imports it and freezes whatever the importer's axis conversion left on the node;
   - finds the map from the imported points to UE's mesh-space points (a signed axis permutation, by
     nearest-neighbour fit of the two point sets);
   - finds the map from UE component space to Maya world from the bones of the Manny rig shipped in
     `assets/`, at its bind: a signed permutation, read off the bones and rounded;
   - composes the plate's Maya world placement on Manny's `lowerarm_l` and writes the points in that
     joint's local space;
   - names the mesh `TechLimbMesh`, plain lambert;
   - exports `SkeldarAnim/assets/Armor/Tech_Limb.fbx`.

   It refuses if:
   - a map leaves a residual over 1e-3 cm;
   - Maya's `lowerarm_l` frame is not UE's under the measured axis map;
   - the reread asset is not where Unreal puts the plate.

## In the scene: an ARMOR SPACE outside the skeleton

The weapons' shape (`weaponspace`, 2026-09-24) for any bone:
- a transform `lowerarm_l_armorSpace`, parent-constrained to the bone with no offset, marked
  `mayaArmorSpace`;
- it stands in an `ArmorSpaces` group (marked, locked) under the rig's top group, or at world level
  beside a bare skeleton;
- the plate is its child, marked `mayaArmor` (the row's key) and `mayaArmorSlot`, seated, its
  channels zero.

The skeleton stays bones only, so an export carries no plate. A retarget moves the bone, and the
plate follows.

`weaponspace`'s internals take their markers as arguments (`_space_of`, `_group_under`, `_ensure`,
`_prune`), and the weapon API keeps its names. The armor spaces use their own markers, so neither
module ever finds the other's space. `skeleton.current_root` resolves a selected path inside an armor
space to its bone, as it does for a weapon: selecting the plate names its character.

`maya_scenesetup/armor.py` (cmds; the pure halves tested without Maya):
- `equipped(root)` lists, per slot, the plate a character wears (found from the bone through its space,
  never by name);
- `equip(root, entry)`:
  - refuses a missing bone or file by name;
  - takes off whatever the entry's SLOT holds on that character (the same item again replaces);
  - imports the FBX (`attach.import_model`, the trap-33 mode guard) and takes its one mesh;
  - parents it into the space, marks and seats it;
  - paints it the next free palette colour (`colour.paint_nodes`, so the Colour card repaints a
    selected plate).

  As with Add Character, what follows the import runs unrecorded (trap 115: an import flushes undo).
- `unequip(root, key)`: the plate deleted, its space pruned (and the group once empty), in one undo
  chunk; «not equipped» otherwise.

## The catalog

`catalog.Armor = (key, label, path, bone, slot, texture="")` and `catalog.ARMOR`, one row:
`Armor("Tech_Limb", "Tech Limb", assets/Armor/Tech_Limb.fbx, "lowerarm_l", "left_forearm")`. A future
piece of armor or clothing is a row. `armor_by_key`, `armor_icon_path(key)`
(`assets/armor_icons/<key>.png`). A test pins one icon per row.

## The Armor card

A hub section **Armor**, the Scene group's last card (Connections stays beside Weapons and Shared beside Connections, both pinned), icon `shield` (Tabler, added to
`maya_hubicons`). Its module is `maya_scenesetup/armorpanel.py` (builder `build_panel`).

- the subtitle (the character, as the other two cards write it);
- the tiles (`maya_armorgrid`, Qt, laid over a `cmds` placeholder by the Characters grid's
  `attach`/Keeper pattern):
  - one square icon per row with its name, measured on `maya_charlook`'s grid;
  - a click picks it (remembered in `mayaSceneSetup_armor`);
  - an item the current character wears carries a small «equipped» pill;
  - the right button offers **Open scene** (the FBX as the scene, `opener`);
  - no drag;
- **Equip** (primary) and **Unequip** (danger) in one row, then a status line.
- Without Qt, a dropdown of the rows stands in for the tiles.
- A hotkey row `window.armor` opens the card.

The icon is `assets/armor_icons/Tech_Limb.png`, rendered by `make_armor_icons.py` (mayapy, offscreen
QPainter, flat-shaded triangles in the hub's steel tone), 256 px with alpha.

## Proof

- Unit tests:
  - the catalog row and its files;
  - the slot rules (`slot_plan`, pure);
  - the space markers kept apart from the weapons';
  - the grid's layout, hit, states and menu;
  - the card's presses on a fake `cmds`;
  - the hub section;
  - the hotkey row;
  - the payload.
- `verify_armor.py` in mayapy standalone, a Manny, a Creep and an Orc D added:
  - Equip on Manny: the plate's every vertex where Unreal puts it (UE component space through the
    measured axis map) to 1e-3 cm, its channels 0;
  - the same on the Creep and the Orc D, each on its own `lowerarm_l`;
  - a UE clip retargeted onto Manny through the button: the plate on the bone at every sampled frame,
    its local matrix in the space unchanged;
  - the export bones only;
  - a second Equip replacing, not doubling;
  - Unequip leaving no node of ours behind;
  - the other two characters unmoved.
- The card in a disposable GUI Maya: the tile clicked, Equip and Unequip pressed through Qt, a
  playblast of the plate on the forearm.
