# One outliner group and one display layer per character (2026-10-02)

## The ask

The animator, away for two hours («делай все сам»):

> Сейчас каждый персонаж в сцене создает кучу мусора если это не повредит нам то давай сделаем так
> чтобы все части которые относятся к одному персонажу ригу были в одной группе, важно что бы
> пользователь открыл аутлайнер и сразу все понял. Так же каждый риг должен иметь свою группу слой
> что бы его можно было включать и отключать в сцене.

Nothing was asked back; every decision below was taken alone and is marked **Decided**.

## Measured first: what a character leaves at the top level today

`docs/superpowers/plans/measure_character_tops.py` (mayapy standalone), run on the base build
(3606438, a `git archive` with this worktree's assets) and on this branch. Base, per row alone in a
new scene:

| row | new world-level DAG nodes | new display layers | new outliner sets |
|---|---|---|---|
| Manny [rig] | `Manny_Rig:Group`, `Manny_Rig:SKM_Manny_Simple`, `Manny_Rig:materialXStack1`, `Manny_Rig:root` | `Manny_Rig:UE5_Skeleton` | `Manny_Rig:AllSet`, `:ControlSet`, `:DeformSet`, `:Sets` |
| Creep [rig] | `Creep_Rig:Armature`, `Creep_Rig:Group` | `Creep_Rig:Creep_Skeleton` | the four AS sets |
| Orc D [rig] | `Orc_D_Rig:Group`, `Orc_D_Rig:root` | `Orc_D_Rig:Orc_Skeleton` | the four AS sets |
| Manny UE5 [skeleton] | `SKM_Manny_Simple`, `camera1`, `materialXStack1`, `root` | `BodyControls`, `DeformationJoints` | `AllSet`, `Sets` (the dead half of an AS rig the asset carries) |
| Creep [skeleton] | `Armature`, `Creep_Arm_L`, `Creep_Arm_R`, `Creep_Back`, `Creep_Body`, `Creep_Face` | `Creep_Skeleton` | - |
| UE4 Mannequin [skeleton] | `SK_Mannequin1`, `root` | - | - |

Then the extras. On a Manny rig: a sword in the hand nothing (its space is in the rig's `Group`), a
spear on the floor `SpearMesh`, the Tech Limb nothing, Camera Setup `Manny_Rig1:SceneSetup_camera`, a
CoM nothing (under `Group`), a retargeted UE clip nothing (its namespace deleted). On a Manny
skeleton every one of them landed at world level: `WeaponSpaces`, `SpearMesh`, `ArmorSpaces`,
`SceneSetup_camera`, `CenterOfMass`. Four characters with their kit: 30-odd loose nodes, and the
shared `WeaponSpaces` / `ArmorSpaces` of every bare skeleton mixed in one world-level group.

After this branch, every row alone: **one** new world-level node (`Manny_Rig_Character`,
`Creep_Rig_Character`, `Orc_D_Rig_Character`, `Manny_Skeleton_Character`, `Creep_Skeleton_Character`,
`UE4_Mannequin_Character`) and **one** layer of ours (`<base>_Layer`) beside the asset's own; every
extra **0** new world-level nodes, rig and skeleton alike.

Three Maya facts measured before choosing (`probe1.py` in the session scratchpad):

- **A node cannot have a namespace's name**: `createNode -name :Manny_Rig` with a namespace
  `Manny_Rig` standing answered `Manny_Rig1`. Worse, **a namespace cannot be made over a node's
  name, silently**: `namespace -add Bar` beside a node `|Bar` raised nothing and `namespace -exists
  :Bar` answered False. A group named for its rig's namespace would have made the NEXT rig's
  namespace impossible.
- **The FBX exporter writes a selected bone's ANCESTORS**: `|CharGrp|root|pelvis` exported with
  `-s` and `FBXExportIncludeChildren false`, read back, came in as `|CharGrp|root|pelvis`.
- **A hidden layer on a parent hides children that sit in a VISIBLE layer of their own**
  (`MDagPath.isVisible` False on both children, `ls -visible` misleadingly still listing them); a
  node with locked t/r/s parents in and out with `relative=True` unmoved, absolute too; a group with
  locked t/r/s takes and gives children.

## The design

### The group (`maya_scenesetup/chargroup.py`, a leaf: cmds + maya_rigs)

- **At world level, `<base>_Character`.** **Decided**: a rig's base is its namespace (`Manny_Rig1`
  - the name every message already uses); a skeleton's its asset's file stem made free
  (`Manny_Skeleton`, `Creep_Skeleton`, `UE4_Mannequin`; a second `Manny_Skeleton1_Character`,
  `free_base` checks both the group's and the layer's name). The suffix is what keeps it off every
  namespace (above). Root namespace, so it never rides a namespace delete or an export rename.
- **Marked** `skeldarCharacterGroup` (`maya_rigs.CHARACTER_MARKER`, a string: the catalog label) with
  a message attribute `skeldarCharacterRoot` fed by the character's root (a rig's game skeleton root);
  found by the marker, never by name (`maya_rigs.group_of(path)`: the top of the path if marked).
- **Locked t/r/s at identity. Decided**: it is a folder, not a control - a rig moves by `Main`, a
  skeleton by its `root` (Characters' drop already does that), and an identity parent is what makes
  every `relative=True` re-parent exact (a skinned mesh's included: its importer-locked transform
  never needs a write). Visibility stays free (the layer drives it anyway).
- **What goes in it at Add** (`character.group_character`, called from `_after_import` inside its
  unrecorded block - trap 115): a rig's every world-level node of its namespace (`Group`, `root` /
  `Armature`, `SKM_Manny_Simple`, `materialXStack1`); a skeleton's every world-level node its import
  brought (`root` / `Armature`, the meshes, the `camera1` and `materialXStack1` Manny's asset carries).
  Every road that adds a character goes through `add_character`: the hub's + Import, a portrait drop,
  the bridge's new rig / new skeleton / onto-skeleton / lineimport square.
- **Parked since** (`chargroup.park(node, owner)`, one call, the public API; `owner` a Rig or any path
  of the character): Camera Setup's camera (`camera.setup`), a weapon on the floor (`floor.drop`), a
  weapon Connections lifts out of the hand (`connections.apply`'s "lift" step, right after OverRig's
  `parent_out`), a bare skeleton's centre of mass (`maya_com.network.create`: parent = the rig's
  `Group` as before, else `maya_rigs.group_of(root)`), a bare skeleton's `WeaponSpaces` /
  `ArmorSpaces` (`weaponspace.group_for`: the rig's own `Group` as before, else **the skeleton's group
  - per character now, no longer one world-level group every skeleton shared**), and agent E's clip
  label. **`maya_scenesetup.character.character_group(root_or_rig)`** is the public question
  ("which group is this character's", long path or None).

### The layer

`<base>_Layer`, created empty in the root namespace, its one member the group (`noRecurse`). V off
hides the whole character; the assets' own layers (`Manny_Rig:UE5_Skeleton`, `Creep_Skeleton`,
`BodyControls`...) cannot bring anything back (measured above and gated). `chargroup.layer_of(group)`
follows `drawOverride`'s connection, never the name. Delete takes it as DG garbage: it touches only
the group (the `displayLayerManager` is a hub, `deletion.HUB_TYPES`), and Ctrl+Z brings it back
holding the group again.

### What must not break, and how it does not

- **`maya_rigs`**: `Rig` gained `character` (default "", so every `Rig(...)` of five fields still
  builds); `rigs()` takes the group as **`top_below(Main, character groups)`** - AdvancedSkeleton's own
  `Group`, the topmost ancestor of `Main` below the character group - so "the skeleton root is the
  shallowest constrained joint OUTSIDE the group", `foreign_constraints`, `rotation_mode`
  (`Group.skeldarRetarget`) and `rig_of` keep their meaning; `rig_of` also answers for a path under
  `rig.character` (the group itself, the parked camera). Every `top_of(rig.group)` in the plugin was
  the identity (the group WAS the top) and is now `rig.group`: `weaponspace.group_for`,
  `maya_asretarget/maya_pmretarget.rig_skeleton_root`. A grep for `split("|")`, `top_of`, `[1]` and
  `assemblies` found the rest: `skeletonimport.top_name` (skips a character group), the armor
  groups' search (`armor._groups`, `maya_overrig.active.armor_groups`: three levels deep now,
  `|Manny_Rig_Character|Manny_Rig:Group|ArmorSpaces`; `maya_rigs.marked_near_top`).
- **Who is it**: `skeleton.current_root` maps a selected non-joint, non-rig path in a skeleton's group
  (the group, a mesh, the camera, a floor weapon) to the root its group links (`_group_root`) - a mesh
  of a bare skeleton now names it, where it used to name nothing; `skeletonimport.selection_names`
  read the group as its skeleton already (a transform with the skeleton under it);
  `deletion.choose` through the parts.
- **Exports**: `animexport.export_hierarchy` wraps its body (`_export_hierarchy`) in
  `chargroup.lifted(root)`: the character's top under the group (`root`, or the `Armature` Null over
  it) out at world level `relative=True` for the length of the export, put back by UUID with its name
  (Maya may rename it on arrival at world). Every export road runs through it: Export FBX..., Export
  to uasset's temp fbx, the checkouts' EXPORT, both layouts. `fbxlayout`'s own rules then see exactly
  what they saw before (`root_state`'s "root stands under X - plain layout" would otherwise have sent
  every grouped Manny out without its Armature).
- **Delete**: a rig's tops gain `rig.character`, a skeleton's parts `group_of(root)`; the layer goes
  as garbage. **Decided**: whatever stands in a character's group goes with it - the group IS the
  character (a cube the animator parented into it goes too; one outside it never).
- **Legacy**: a character added before has no group; every lookup answers None / "" and every road
  behaves as before (gated: its spaces at world level, its export, its Delete).
- **The bridge** retargets in world space onto grouped rigs, adds new ones grouped, and its square of
  rigs lands as one group each; a second Manny skeleton now keeps the plain name `root` (it no longer
  collides at world level - the first stands in its group), so `rename_note` says nothing.

## Proof

- Unit: **3531 tests, OK** (`tests/test_rigs.py` `CharacterGroup`, new
  `tests/test_scenesetup_chargroup.py`: names, `free_base`, `child_on_path`, `group_base`,
  `world_tops`, the markers, the wiring of every parking road; `test_uebridge_export` now inspects
  `_export_hierarchy`, where the body moved).
- `docs/superpowers/plans/verify_character_groups.py`, mayapy standalone, **106/106** (phases A-F):
  - A, every row alone: one new world-level node (its group) and one layer of ours holding it alone,
    marked with the row, linked from its root, locked at identity, the line still counting what
    arrived; a rig's `group` AdvancedSkeleton's below the character group, its skeleton outside the
    rig group and inside the character group; **the grouping moved nothing** - every joint
    (93 / 91 / 95 / 93 / 91 / 68) and every sampled vertex of every skinned mesh **0.0 cm** against the
    same Add with the grouping switched off; **V off: 75 / 83 / 79 / 4 / 5 / 1 visible shapes → 0**,
    and 0 still with the asset's own layers (`UE5_Skeleton`, `Creep_Skeleton`, `Orc_Skeleton`,
    `BodyControls`, `DeformationJoints`) forced visible, back to all on V on;
  - B, Manny rig + Creep rig + Manny skeleton + Creep skeleton each with a sword in the hand, a spear
    on the floor, the Tech Limb, Camera Setup and a CoM: **nothing at world level but the four
    groups**; every part inside its own character's group; a rig's weapon space in its AS `Group`, a
    skeleton's `WeaponSpaces` its own in its group; the group selected names its character
    (`current_root`, `rig_of`, `deletion.choose`, the Colour card), a skeleton's mesh names it,
    Onto selected reads the group; the drop targets the four, no shield joint a character; the bridge:
    a UE clip onto the grouped rig (`hand_r` 102.0 cm at frame 30), a new rig, a new skeleton and a
    lineimport square of two each one group, nothing loose after;
  - C, the exports (Manny rig, Manny skeleton, Creep skeleton x cascadeur / plain): the scene put back
    exactly (paths, tops, joints), the file equal to the same character ungrouped - top node
    (`Armature` / `root`), the joints (93 / 93 / 91), every joint's world matrix at frame 20 **0.0** -
    and the control: `_export_hierarchy` without the lift writes `Manny_Skeleton_Character` into the
    file;
  - D, Delete of a Manny skeleton (433 nodes) and a Manny rig (2723 nodes) each with two weapons: the
    group, the layer and everything gone, the Creep beside them untouched, Ctrl+Z bringing all of it
    back with the layer holding the group again, redo;
  - E, a legacy skeleton (the grouping off): its root and `WeaponSpaces` at world level as before, its
    export `Armature` over `root`, Delete whole;
  - F, a portrait drop (`add_character(at=)`) of a Manny rig and a Creep skeleton: moved by exactly the
    point (0.0), the group at the origin, the Creep's `Armature` still in Cascadeur's layout.
- The existing verifies re-run on this worktree (`run_on_worktree.py` in the session scratchpad swaps
  the main checkout's path for this worktree's), standalone unless said: `verify_delete_character`
  **82/82**, `verify_rig_pipeline` **30/30**, `verify_many_rigs` **32/32**, `verify_weapon_space`
  **11/11**, `verify_inventory` **14/14**, `verify_armor` **15/15**, `verify_cascadeur_layout` **10/10**,
  `verify_creep_rig_asset` **16/16**, `verify_orc_d_rig_asset` **22/22**, `verify_one_shader` **4/4**,
  `verify_creep_skeleton_asset` **9/9**, `verify_fkik_switch` **63/63**, `verify_weapon_socket` **10/10**; in the disposable GUI Maya (port 7064):
  `verify_connections` **40/40** (OverRig's live `parent_out`/`parent_in`: the lifted weapon parked in
  the group, its world track intact), `verify_add_character` **31/31**. Every failure on the first runs
  was a world-level PATH LITERAL in the verify (`"|Manny_Rig:root"`, `"|Creep_Rig:Group|..."`,
  `"|Armature|root"`, "the spear lies at world level", "its space at world level", "not inside a
  group") - each moved into the group, the gate kept as strict; none was a behaviour change.
- GUI: `docs/superpowers/plans/character_groups_outliner.png` - a disposable Maya (port 7064, scratch
  `MAYA_APP_DIR`, `MAYA_NO_HOME`), Manny rig + Creep rig + Manny skeleton each holding a weapon: the
  Outliner's top level is the three groups (opened one level), the Layer Editor the three layers of
  ours beside the assets' own.

## Not done

- The **DG** clutter the default Outliner also lists (it shows every objectSet: the assets' `Sets` /
  `AllSet`, the shading groups) cannot be parented: they are not DAG nodes. Left as Maya shows them.
  Manny's skeleton asset still brings the dead half of an AS rig (`AllSet`, `Sets`, `BodyControls`,
  `DeformationJoints`) - an asset fix, not this one.
- No button to group a character added before (`chargroup.make` would do it; not asked).
- The group is locked: moving it by hand is refused by Maya. Unlocking and moving it would offset the
  character from its export (the export lifts relatively); stated, not guarded.

## CLAUDE.md section (draft)

## One outliner group and one layer per character (2026-10-02)

The animator: «Сейчас каждый персонаж в сцене создает кучу мусора если это не повредит нам то давай
сделаем так чтобы все части которые относятся к одному персонажу ригу были в одной группе, важно что
бы пользователь открыл аутлайнер и сразу все понял. Так же каждый риг должен иметь свою группу слой
что бы его можно было включать и отключать в сцене.» Away for two hours; every choice taken alone.
Spec `docs/superpowers/specs/2026-10-02-character-groups-design.md`.

**Measured first** (`measure_character_tops.py`, standalone, the build before and after): a Manny rig
left 4 world-level nodes (`Group`, `root`, `SKM_Manny_Simple`, `materialXStack1`), a Creep skeleton 6
(`Armature` and five meshes), a Manny skeleton 4 (`root`, `SKM_Manny_Simple`, `camera1`,
`materialXStack1`), and every extra on a bare skeleton one more (`WeaponSpaces`, `SpearMesh`,
`ArmorSpaces`, `SceneSetup_camera`, `CenterOfMass` - the spaces SHARED by every skeleton). After: one
node per character, and 0 for every extra.

- **The group** (`maya_scenesetup/chargroup.py`): `<base>_Character` at world level - a rig's base its
  namespace (`Manny_Rig1_Character`), a skeleton's its asset's file stem made free
  (`Manny_Skeleton_Character`, `Manny_Skeleton1_Character`); marked `skeldarCharacterGroup` (the
  catalog label) with a message link `skeldarCharacterRoot` from the root; found by the marker
  (`maya_rigs.group_of`), never by name; **t/r/s locked at identity** (a folder - the rig moves by
  `Main`, a skeleton by `root` - and an identity parent makes every `relative=True` re-parent exact).
  Add Character makes it for every row and every road (`character.group_character`, in
  `_after_import`'s unrecorded block): a rig's world-level nodes of its namespace, a skeleton's
  world-level nodes of its import.
- **One layer** `<base>_Layer`, the group its one member: V off hides the whole character, the assets'
  own layers included (`MDagPath.isVisible`, gated).
- **Parked in it** (`chargroup.park(node, owner)` - the one call for any future part;
  `character.character_group(root_or_rig)` the public question): Camera Setup's camera, a floor
  weapon, a weapon Connections lifts to world, a bare skeleton's CoM and its OWN `WeaponSpaces` /
  `ArmorSpaces` (a rig's stay in its AS `Group`).
- **`maya_rigs`**: `Rig.character` (default ""); `rig.group` is still AdvancedSkeleton's -
  `top_below(Main, character groups)` - so every rule about it holds; `rig_of` answers for the group
  and its loose parts. `top_of(rig.group)` was the identity and is `rig.group` now everywhere.
- **Exports lift the character's top out of the group** (`chargroup.lifted`, around
  `animexport._export_hierarchy`, both layouts, every road), because the exporter writes ancestors
  (trap 159?).
- **Who is it**: the group or a non-joint in a skeleton's group names that skeleton
  (`skeleton._group_root`); Delete takes the group and its layer; a legacy character (no group)
  behaves exactly as before.

Proof: `verify_character_groups.py` **106/106 standalone** - A every row: one node + one layer,
locked, linked, the grouping moving nothing (joints and sampled vertices **0.0 cm** against the same Add
ungrouped), V off **75 / 83 / 79 / 4 / 5 / 1 visible shapes → 0** with the assets' own layers forced on;
B four characters with their kits: nothing at world level but the four groups, the who-is-it questions
answering from the group, the bridge onto / new rig / new skeleton / a square of two all grouped; C the
exports in both layouts equal to the same character ungrouped (top node, joints, frame-20 matrices
**0.0**), the scene put back exactly, the control without the lift writing `Manny_Skeleton_Character`
into the file; D Delete (433 / 2723 nodes) + Ctrl+Z (the layer holding the group again) + redo; E a
legacy character as before; F a portrait drop moved by exactly the point, the group at the origin. The
existing verifies re-run on the branch: delete 82/82, rig pipeline 30/30, many rigs 32/32, weapon space
11/11, inventory 14/14, armor 15/15, cascadeur layout 10/10, Creep rig 16/16, Orc D 22/22, one shader
4/4, Creep skeleton 9/9, FK/IK 63/63, weapon socket 10/10; in a disposable GUI Maya (port 7064) Connections 40/40 and Add
Character 31/31 - every first-run failure a world-level path literal in the verify, moved into the
group. 3531 unit tests; the Outliner and Layer Editor photographed (`character_groups_outliner.png`).

159?. **The FBX exporter writes a selected node's ANCESTORS into the file.** Measured 2026-10-02:
     `FBXExport -s` of the joints of `|CharGrp|root|pelvis` with `FBXExportIncludeChildren false` came
     back as `|CharGrp|root|pelvis`. Anything that groups a skeleton must take its top out to world
     for the length of an export (relative, by UUID, the name put back) - or every file carries the
     group, and Cascadeur's layout reads "root stands under X" and goes out plain.
160?. **A node cannot take a namespace's name, and a namespace cannot be made over a node's - the
     second silently.** `createNode -name :Manny_Rig` beside a namespace `Manny_Rig` answered
     `Manny_Rig1`; `namespace -add Bar` beside a node `|Bar` raised nothing and `namespace -exists`
     answered False. A group named exactly for its rig would have blocked the next rig's namespace.
162?. **A verify that names a character's nodes by world-level long path breaks the day the character
     moves into a group** - `"|Manny_Rig:root"`, `"|Creep_Rig:Group|Creep_Rig:Geometry"`,
     `"|Armature|root"`, «lies at world level»: 14 gates across 9 verifies failed on correct code here.
     Ask `maya_rigs` / `character.character_group`, or use a partial path (`Manny_Rig:root`), and keep
     the expectation as strict as it was.
161?. **Re-parenting the import's nodes invalidates the paths `returnNewNodes` gave** (trap 16 in
     Add Character): the first grouped build said «added - 0 joints, 0 meshes». Resolve the import by
     UUID across any re-parent.
