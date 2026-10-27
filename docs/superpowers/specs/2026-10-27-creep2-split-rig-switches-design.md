# Creep 2's rig made of its three cut pieces, with switches on Main (2026-10-27)

The animator: «для нового крипа нужно добавить тело руку и голову в основной риг и сделать переключатели
на главном контроле которые могут включать или отключать отрезанные части». Asked, all three the
recommendation:
- the rig carries the three cut pieces in place of the whole mesh;
- the switches are keyable;
- the Body / Arm R / Head cards stay.

## What changes

**`assets/Creep2_Rig.ma`**, built by `docs/superpowers/plans/make_creep2_split_rig.py` (mayapy):
- the whole mesh `Creep2_Body` goes, with its skin;
- three meshes stand under `Group|Geometry`, each a copy of the animator's cut FBX
  (`Creep_Split/Creep_Body.fbx`, `Creep_Arm_R.fbx`, `Creep_Head.fbx`) at its bind:
  `Creep2_Body` (the cut body), `Creep2_ArmR`, `Creep2_Head`;
- each is skinned to the rig's own game joints with its FBX's weights vertex for vertex. The cut
  skeletons' binds are Creep 2's (each joint checked to 1e-3; the weapon sockets carry no weight);
- the faces wear the rig's materials by name;
- one bind pose is saved over the 93 joints.

**On `Main`**, two attributes: `armR` («Arm R») and `head` («Head»).
- Each is a bool, keyable, default on, and drives its mesh's `visibility` directly. A key on a bool
  is stepped.
- The body is always shown.
- With both on, the rig shows the whole Creep 2: the pieces were cut out of one mesh, so they meet.

Nothing else changes: controls, bones, the retarget, the Pose Library, the export (bones only), and the
Creep 2 skeleton row (still the whole mesh). `character_skeletons.json` is written again (the asset's
sha1).

## Proof

`docs/superpowers/plans/verify_creep2_split_rig.py <clip>`, mayapy standalone:
- the rig added: three meshes, every vertex on its FBX's at the bind (1e-3 cm), the skins at their
  bind, no whole mesh left;
- `Main.armR` 0 hides only the arm, `Main.head` 0 only the head; keyed off at frame 20, the arm is
  shown at 19 and hidden at 20;
- the clip through the Retarget button: every piece's vertices where its FBX's own skin puts them with
  its joints on the rig's bones (1e-3 cm), and the switches' keys untouched;
- the export: 93 joints, no mesh;
- Delete character takes all three.
