# Characters > Delete: a character out of the scene, whole

2026-10-01, the animator: «Давай в разделе character сделаем кнопку удаления. Суть такая - я выделяю
любую часть персонажа рига или скелета не важно какую нажимаю эту кнопку и у меня удаляется из сцены
все что связано с этим персонажем. Также если я выделил несколько разных персонажей кнопка должна
удалить все их части». Asked: a confirm dialog first («Диалог с подтверждением»). Everything else was
decided here and is below.

## What the button does

The Characters card gets **Delete** (danger, trash) beside Add Character. One press:

1. **Which characters**: every character a selected node belongs to. Nothing selected, or nothing
   selected that belongs to a character, is a refusal - a destructive button never falls back to "the
   only character". Several characters selected: all of them.
2. **The confirm** names them, what of theirs goes (weapons, armor, camera, centre of mass), a rig
   that will be disconnected from a deleted skeleton, and objects of the animator's that are
   constrained to them. Delete / Cancel; batch (a verify, a test) goes on.
3. **One undo chunk**: Ctrl+Z brings them all back.

## What a character is

A **rig** (`maya_rigs.rigs()`) or a **bare skeleton** (`builder.character_roots()` minus the rigs'
own joints and anything inside a weapon/armor space). Its **parts** are DAG tops:

- a rig: every top-level node of its namespace (`Group`, the game skeleton, the asset's other tops -
  measured: `Manny_Rig:SKM_Manny_Simple`, `Manny_Rig:materialXStack1`, the Creep's `Armature`); a
  root-namespace rig (a scene from before 2026-09-08): its group and skeleton;
- a skeleton: its root;
- both: the meshes skinned to its joints; the weapon/armor **spaces** following its bones (at world
  level beside a bare skeleton); our weapons and cameras that **drive** its bones (a weapon on the
  floor, a camera on `camera_root`); its **centre of mass** group (linked to the root);
- a skeleton the Add put in: what that import brought (below).

A selected node belongs to a character when it lies under one of its parts or in its namespace.
So a control, a bone, a mesh, a weapon in the hand or on the floor, a piece of armor, the CoM handle
and the camera all name it.

## What goes

The **core**:

- the parts, raised: a plain transform whose every child goes goes too (the Creep skeleton's
  `Armature`, Manny's `SKM_Manny_Simple`, an emptied `WeaponSpaces`);
- every DAG node below them;
- every node of the rig's namespace (all 2700 of an Add's nodes land there - measured);
- every node of a skeleton's namespace when the namespace holds nothing else (a clip imported as its
  own skeleton);
- every node of a skeletal armor piece's namespace.

Then the **DG garbage around it**. A plain delete of the DAG leaves materials, display layers, sets,
`AllSet`, animation curves and AdvancedSkeleton's utility nodes behind - measured: 292 nodes after
Manny's skeleton, 28 after the Creep's, 9 after the UE4 Mannequin. Rule:

- take the components of the graph of connections over the nodes outside the core, with the scene's
  **hubs** cut out:
  - default nodes;
  - locked and referenced nodes;
  - `lightLinker`, `partition`, `renderLayer`, `displayLayerManager`, `renderLayerManager`, the IK
    solvers, `shapeEditorManager`, `poseInterpolatorManager`, `UsdDefaultSettings`,
    `nodeGraphEditorInfo`, `hyperLayout`/`hyperView`/`hyperGraphInfo`, `animLayer`, `time`,
    `sequenceManager`;
- measured: `lightLinker1` is NOT a default node and links every shading group in the scene;
  without it every character's materials were one component;
- a component goes when it holds **no DAG node** and **touches the core** (a material worn only by
  the character, its skinClusters, its curves, a layer or set of only its members).

A component holding any DAG node - another character, the animator's cube - stays whole. An unknown
hub only merges components, so the failure mode is keeping, never deleting somebody else's node.

**The provenance record** (new, on Add): the AS-dead half Manny's skeleton asset carries (275 DG
nodes, `AllSet`, `BodyControls`, a `camera1`, a `materialXStack1`) and the asset materials the palette
unassigns are connected to nothing of the character, so no graph rule can find them.
`character._after_import` writes, for a skeleton (a rig has its namespace):

- a `network` node `<root>_skeldarImport`, its `skeldarImportRoot` message fed by `root.message`;
- `skeldarImportNodes`: the UUIDs of what the import brought, hubs left out;
- `skeldarImportLabel`: the catalog label.

At Delete:

- a recorded DAG node with nothing foreign below it, standing at world level or under the core,
  joins the core;
- a component that does not touch the core goes only when every node in it was recorded.

The record itself is DG, fed by the root only, so it goes with the character.

## Before the delete (inside the chunk)

- An object of somebody else's riding a proxy inside the character (BakeAcross) is **released**
  (`connections.release_across`: baked where it was carried, shown).
- A rig that is not deleted but whose MoCap holder's source is a deleted skeleton is **disconnected**
  (`maya_rig_retarget.disconnect`; its take is not baked - the confirm says so).
- The CoM engine forgets the deleted groups.
- Locked nodes of the core (mayaUsd's `UsdDefaultSettings` copies the assets carry into the rig's
  namespace - measured: they block `namespace -removeNamespace -deleteNamespaceContent`) are
  unlocked.

Then the DAG tops are deleted, then the DG nodes still standing, then every emptied namespace (deepest
first), then the orphaned hand proxies. Constraints of the animator's own objects aimed at the
character keep their constraint without a target, as with a delete by hand, and are named.

A character with a referenced node is refused by name (the Reference Editor removes it).

## Not done

- No hotkey row.
- The duplicates of Maya's own singletons an import makes (`shapeEditorManager1`,
  `poseInterpolatorManager1`, the root-namespace `UsdDefaultSettings` copies, trap 121/122) stay -
  they are hubs, as `verify_add_character.py` already excuses them.
- A skeleton added before this has no record: its DAG and its connected DG go, recorded-only junk
  of its asset stays.

## Proof

`docs/superpowers/plans/verify_delete_character.py`, mayapy standalone:

- every catalog row added and deleted;
- with a weapon, armor, a camera and a CoM;
- the scene back to its UUID set but for the excused singletons;
- Ctrl+Z restoring every node;
- two characters in one press;
- a part of each kind naming its character;
- the other characters untouched;
- a disconnected retarget source;
- a released rider.

Unit tests for the pure halves and the press.
