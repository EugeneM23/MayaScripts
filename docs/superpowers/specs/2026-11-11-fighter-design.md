# The Fighter and his Titan Axe

The animator, with the character and his weapon open on port 7005: «В сцене новый персонаж и
оружие для него. Нужно интегрировать в наш пайплайн по всем правилам». Asked, all four the
recommendation: **his own skeleton plus the camera bones**, the name **Fighter**, a **palette
colour** for now (his textures are on `D:/work/fighter`, the axe's on `E:/work/Atone_source`,
neither on this machine, and the FBXs embed none), the axe a **catalog row on the right hand**.

## Measured first (the scene read only)

- `Downloads/SK_Fighter_proto6.FBX` (Unreal's export; the `(1)` copy is byte-identical) and
  `Downloads/TitanAxe_2H_01.fbx` are what the scene holds.
- **His skeleton is not Manny's**: 79 joints under `|root` (-90 X in its jointOrient, Manny's
  shape), UE names but `spine_01..04` (no `spine_05`), no metacarpals (`index_01` hangs on the
  hand, at the knuckle), one thigh and one calf twist a leg, `helm` and `jaw` on the head, no
  camera bones. 184 cm; the pelvis 101.3 cm (Manny 95.9), forearms 33.1 (27.3), calves 46.0
  (42.2). Bone frames 1-31 deg off Manny's (his A-pose).
- One skinned mesh `SKM_fighter_test_06_2` (15526 vertices, 66 influences, two materials), the
  skin at its bind to 6e-5.
- **The Titan Axe** (1041 vertices, 175 cm) already lies in our weapon convention: its head
  along +Y (y 30..120, the blade on -X), the haft down to -70, the origin on the haft 30 cm
  under the head - the grip.

## The build (the Creep 2 road)

1. `make_fighter_source.py` (mayapy) -> `sources/fighter/Fighter_Source.mb`: the FBX in our
   shape, `camera_root` / `camera_bone` on Manny's values, the weapon sockets in UE's
   convention, Unreal's user attributes off the joints, the dead textures dropped, one bind
   pose over all 81 joints.
2. `rebuild_fighter_rig.py` (LIVE, a disposable Maya): `as_creep_rig_procedure` as
   `rebuild_creep2_rig.py` runs it (Manny's ik_hand rule, the midline on x = 0), with three
   differences of his:
   - **Spine5 and the four Finger0 are ghosts**: fit joints with no bone of his, placed
     between their neighbours (Spine5 half way spine_04 -> neck_01, a metacarpal a third of
     the way hand -> finger_01); they drive no game bone.
   - **His twists**: Hip and Knee one twist joint each; `HipPart1 -> thigh_twist_01`,
     `KneePart1 -> calf_twist_01`. His upper-arm twists stand at 0.15 / 0.60 of the bone
     (unevenly), so AS's evenly stepped Parts stand off them and the bones follow by
     orientation with their offsets.
   - `helm` and `jaw` ride the head (no fit joint).
3. `make_fighter_assets.py` -> `SkeldarAnim/assets/Fighter_Rig.ma` (with Creep 2's position
   follows, so an FK translation carries its bone) and `Fighter_Skeleton.ma`.
4. `make_fighter_axe.py` -> `assets/Titan_Axe.fbx` (one mesh, our marker-free model, no
   animation, no material path).
5. Catalog: `Fighter [rig]` / `Fighter [skeleton]` (model `Fighter`, untextured, a fire palette
   of its own), the weapon row `Titan_Axe` on `weapon_r`, scale 1; the portrait; the
   inventory icon; `character_skeletons.json` re-run.

## Proof

`verify_fighter.py <a UE clip>` (mayapy standalone): both rows added and painted, skin at its
bind, every vertex where his FBX has it; the Retarget button (rotations - bones turned as the
clip's, his lengths kept); the export his 81 joints, no mesh; Titan Axe at zero grip on
weapon_r driving it; Delete character.
