# Creep 2 Arm R and Head on Manny's whole skeleton (2026-10-27)

The animator: «риги крипа и скелеты нужно переделать под новые требования. Структура рига должна
сохраниться нам лишние контроллеры не нужны, но скелеты должны быть от менни. Так же должна работать
библиотека поз». Asked:
- the skeleton is Manny's hierarchy and axes with Creep 2's proportions;
- only Creep 2 Body / Arm R / Head are in scope;
- no control is added;
- the Pose Library must work, though nothing was reported broken.

Then: Arm R and Head carry the whole 93-bone skeleton, the bones without controls stand at the bind,
and `spine_05` is driven by the part's anchor (variant A).

## Measured first (mayapy, the shipped assets read only)

| asset | joints | against Manny |
|---|---|---|
| Creep2_Body_Skeleton.ma | 93 | Manny's names and hierarchy, no parent differs. Each bone's child direction in its parent's frame matches Manny's (0-27 deg; the largest are the left fingers and `ik_hand_gun`, Creep 2's own proportions, not another axis convention) |
| Creep2_ArmR_Skeleton.ma | 29 | `clavicle_r` hangs on `root` (Manny: `spine_05`); 64 bones missing; the arm's own axes match Manny's (0-0.5 deg) |
| Creep2_Head_Skeleton.ma | 4 | `neck_01` hangs on `root` (Manny: `spine_05`); 89 bones missing; axes match (0.6 / 5.3 deg) |

So Body needs no rebuild, only the Pose Library checks. Arm R and Head get the whole skeleton.

## What changes

**The skeleton assets** `Creep2_ArmR_Skeleton.ma` and `Creep2_Head_Skeleton.ma`:
- the whole Creep 2 game skeleton at its bind: 93 joints, camera and weapon bones included, Creep 2's
  UE weapon sockets, read from the shipped `Creep2_Skeleton.ma`;
- the part's mesh unchanged (its points, UVs, normals and weights), its skinCluster rewired onto the
  same-named joints of the whole skeleton (the clothing's `rewire_plan` rule). The part's own bones
  stand where Creep 2's do (the split came from that skeleton): checked to 1e-4 cm before the rewire,
  refused otherwise;
- one bind pose saved again over all 93 joints (traps 79 / 91);
- the root at world level, Creep 2's shape. The `Armature` wrapper goes, as on the other Creep 2 rows.

**The rig assets** `Creep2_ArmR_Rig.ma` and `Creep2_Head_Rig.ma`, edited in mayapy; the AdvancedSkeleton
rig is not rebuilt:
- every AS control, joint, constraint network, `PartAnchor` and `Group.skeldarPartAnchor` is kept as it
  is;
- the game skeleton is replaced by the whole one. Each part bone is driven as now, point + orient +
  scale `-mo` from its AS joint, made again onto the new bone of that name with the offset it had;
- **`spine_05` is parent-constrained to `PartAnchor`** with its offset kept, so the clavicle or the neck
  stands where it stood;
- every other bone (pelvis, spine_01..04, legs, the other arm, the head or arm not in the part, the
  helpers) carries no constraint. It stands at the bind under `root`, and `root` follows Main as before;
- the mesh rewired as on the skeleton; the rig's painted material kept.

**The catalog rows** keep their keys, labels and `part="spine_05"`. `character_skeletons.json` is written
again (the rows now carry 93 bones; the Auto card still never matches a part).

## The roads after the change

- **Retarget onto a part rig**: unchanged. RootX_M follows the clip's chest; the part's controls follow
  the clip's bones, twin or rotations, never asked. The extra bones get no keys.
- **Onto a part skeleton**: the part skeleton is a whole Creep 2 skeleton now, so the ordinary skeleton
  road takes the clip. The part's special case (a bone straight on `root` takes the clip's place) is no
  longer needed for these rows and is removed if nothing else uses it.
- **Export**: 93 bones, no mesh, like every character.
- **A part portrait dropped on a character** (`swap.attach_part`): unchanged; the part still lands on
  the character's chest.

## The Pose Library

- **Saving from a part rig**: the card's members are the bones the rig drives (the part chain and
  `spine_05`). The bind bones are never members, so a card from Arm R applied onto Manny leaves Manny's
  body alone.
- **Saving from a part skeleton**: as any skeleton, the selection decides.
- **Applying**: a card from Manny or Creep 2 onto a part rig poses the part's controls. It names its
  members by bone name, Manny's names being the part's. A card onto a part skeleton poses the bones it
  holds.
- To prove (rig and skeleton, pose and animation):
  - Creep 2 Body, Arm R, Head;
  - a card from Manny, a card from Creep 2, and a card saved on the part itself.

## Proof

`docs/superpowers/plans/verify_creep_parts_manny.py`, mayapy standalone, on a Creep clip:
- both part skeletons: 93 joints, Manny's hierarchy (every parent as Manny's), the mesh where the old
  asset's skin put it at the bind (each vertex to 1e-4 cm), skin at its bind;
- both part rigs: the same 93 joints; the controls exactly the old rig's (names, count, compared against
  the old asset); a clip through the Retarget button with the part bones where the old rig put them
  (1e-3 cm); `spine_05` on `PartAnchor`; the bind bones still (0.0);
- the Pose Library cases above: each card's bones on the card's (directions to 0.01 deg), the bind
  bones untouched, one undo;
- the existing `verify_creep_parts.py`, `verify_part_drop.py` and `verify_creep2_body.py` run again.

Unit tests: the catalog pins 93 joints and Manny's parents for the part rows.

## Not built

- The extra bones following the clip (variant B).
- A rebuild of the AS rig.
- The first Creep (it is not in scope).
