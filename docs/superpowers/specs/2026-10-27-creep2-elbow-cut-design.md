# Creep 2's arm cut at the elbow (2026-10-27)

The animator: «мы отрезали руку по плече а нужно по локоть давай переделаем и руку и меш тело без
головы и руки». Asked, all three the recommendation:
- a plane through the elbow joint, across the arm;
- every asset on the new cut (the main rig, the Body and Arm R cards, rig and skeleton);
- the cut made here, not by hand.

## The cut

`docs/superpowers/plans/make_creep2_elbow_cut.py`, mayapy. Step `cut` works on `Creep2_Rig.ma` (the
shoulder-cut pieces), at the bind:
- **the plane**: through `lowerarm_r`, its normal the bisector of the upper arm's and the forearm's
  directions;
- the animator's arm piece is copied twice and each copy cut with `polyCut -deleteFaces`:
  - `Creep2_Forearm` (forearm and hand): 7056 vertices;
  - the upper arm: 2093 vertices;
- both are skinned with the arm piece's weights, copied by closest point: exact on the piece's own
  vertices, interpolated on the 212 the cut made (106 a side, standing on each other);
- the upper arm is united with the body (`polyUniteSkinned`, nothing merged): `Creep2_BodyElbow`,
  54092 vertices. The old shoulder seam stays where the animator's cut made it, vertex for vertex;
- saved as `sources/creep2/Creep2_ElbowCut.ma` (the two meshes, skinned, with the skeleton).

## The assets

Step `swap` takes each asset in turn and puts the cut's mesh in place of the old one under the old one's
name. The weights go vertex for vertex onto the asset's own joints; the mesh keeps the old one's
parent, visibility input (the main rig's `Main.armR`), layer and locks. One bind pose is saved again.

| asset | old mesh | becomes |
|---|---|---|
| Creep2_Rig.ma | Creep2_Body | the elbow-cut body |
| Creep2_Rig.ma | Creep2_ArmR | the forearm (still switched by `Main.armR`) |
| Creep2_Body_Rig.ma / Creep2_Body_Skeleton.ma | Creep2_BodySplit | the elbow-cut body |
| Creep2_ArmR_Rig.ma / Creep2_ArmR_Skeleton.ma | Creep2_ArmR | the forearm |

The head is the animator's, unchanged. The Arm R rig keeps all its controls, from the clavicle down.

## Proof

- `verify_creep2_split_rig.py`: every piece on the cut file at the bind and under a retarget, the
  switches as before.
- `verify_creep2_body.py`: the body on the cut file, at the bind, under a retarget and on the skeleton.
- `verify_creep2.py`, `verify_creep_parts.py`, `verify_creep_parts_manny.py`, `verify_part_drop.py`
  run again.
- The elbow seam: the forearm's 106 cut vertices stand on the body's to 1e-3 cm.

## Not done

The Creep 2 Arm R portrait still shows the arm from the shoulder. Rendering it again needs a GUI Maya
(`make_character_portraits.py`).
