# Every common source convention onto our rigs and skeletons (2026-10-02)

## The ask

The animator, away for two hours («сделать самостоятельно от начала и до конца ... пушить и
делать сборку не нужно пока я не проверю»), Task 2 of four:

> Нужно проработать ретаргеты для наших ригов ... Так же я бы хотел что бы ты прошелся по
> интернету нашел самые часто используемые иерархии костей для Unity, Mixamo, blender,
> motionbuilder, 3dmax Unrealengine и сделал ретаргеты для этих систем на наши риги и скелеты.

This branch (agent B, "conventions") makes every common SOURCE skeleton recognisable and
mapped onto our names. The rotation / squash-and-stretch versions of the retarget and the
question to the user are agent C's, built in parallel; the import formats agent A's.

## What the conventions are (research, with sources)

| convention | hierarchy and names | quirks that matter |
|---|---|---|
| Unreal UE5 Manny | root > pelvis > spine_01..05 > neck_01/02 > head; clavicle_l > upperarm_l > lowerarm_l > hand_l > *_metacarpal_l > index_01_l..03; thigh_l > calf_l > foot_l > ball_l; twist and ik_ helpers | already ours |
| Unreal UE4 Mannequin | spine_01..03 (03 carries the clavicles), one neck, no metacarpals | already ours (the UE4 spine map) |
| Mixamo | mixamorig:Hips > Spine/Spine1/Spine2 > Neck > Head > HeadTop_End; LeftShoulder > LeftArm > LeftForeArm > LeftHand > LeftHandIndex1..4; LeftUpLeg > LeftLeg > LeftFoot > LeftToeBase > LeftToe_End | side a PREFIX, bind in jointOrient (rest = rotates at 0, an exact T-pose), no root bone |
| MotionBuilder HumanIK | Hips, Spine, Spine1..Spine9, Neck, Neck1.., Head, LeftShoulder, LeftArm, LeftForeArm, LeftHand, LeftUpLeg, LeftLeg, LeftFoot, LeftToeBase, LeftHandThumb1.., roll bones LeftArmRoll; often a `Character1_` prefix (Unity-chan) | `Shoulder` is the CLAVICLE; 15 required + auxiliary bones |
| Unity Mecanim (HumanBodyBones as bone names) | Hips, Spine, Chest, UpperChest, Neck, Head, LeftShoulder, LeftUpperArm, LeftLowerArm, LeftHand, LeftUpperLeg, LeftLowerLeg, LeftFoot, LeftToes, LeftThumbProximal/Intermediate/Distal, LeftLittle* | game exports keep the bind in the rotate channels |
| VRM / VRoid | J_Bip_C_Hips, J_Bip_C_Spine, J_Bip_C_Chest, J_Bip_C_UpperChest, J_Bip_C_Neck, J_Bip_C_Head, J_Bip_L_Shoulder, J_Bip_L_UpperArm, J_Bip_L_LowerArm, J_Bip_L_Hand, J_Bip_L_Thumb1.., J_Bip_L_UpperLeg, J_Bip_L_LowerLeg, J_Bip_L_Foot, J_Bip_L_ToeBase; J_Sec_ hair | A-pose, metres |
| Blender Rigify (deform bones) | DEF-spine (the hips) > DEF-spine.001..003 > .004/.005 (neck) > .006 (head); DEF-shoulder.L > DEF-upper_arm.L > .001 > DEF-forearm.L > .001 > DEF-hand.L > DEF-palm.01..04.L > DEF-f_index.01.L..; DEF-thigh.L > .001 > DEF-shin.L > .001 > DEF-foot.L > DEF-toe.L; DEF-pelvis.L | the spine is NUMBERED, not named; .001 segments; metres under an Armature null |
| Blender Auto-Rig Pro export | root.x (the HIPS) > spine_01.x.. > neck.x > head.x; shoulder.l > arm_stretch.l > forearm_stretch.l > hand.l > thumb1.l..; thigh_stretch.l > leg_stretch.l > foot.l > toes_01.l; *_twist.l | `.x` centre suffix; `root` is the hips |
| 3ds Max Biped | Bip001 (centre of mass) > Bip001 Pelvis > Bip001 Spine > Spine1.. > Bip001 Neck > Bip001 Head > HeadNub; Bip001 L Clavicle under the NECK; Bip001 L Thigh under Bip001 SPINE; L UpperArm > L Forearm > L Hand > L Finger0, Finger01, Finger02 (thumb), Finger1, Finger11 ..; L Toe0 > Toe0Nub | spaces in names (FBX/Maya make them `_`), two-digit finger numbers (finger, then segment minus one), nubs, Z-up |
| 3ds Max CAT | user-named; read by the generic tokens | - |
| Character Creator / iClone | CC_Base_BoneRoot > CC_Base_Hip > {CC_Base_Pelvis > thighs, CC_Base_Waist > CC_Base_Spine01 > Spine02 > CC_Base_NeckTwist01 > NeckTwist02 > CC_Base_Head}; CC_Base_L_Clavicle > L_Upperarm > L_Forearm > L_Hand > L_Thumb1, L_Index1, L_Mid1 ..; twist bones *Twist01, *ShareBone | the neck bones are CALLED twists |
| Daz Genesis 3/8 | hip > {pelvis > lThighBend > lThighTwist > lShin > lFoot > lToe, abdomenLower > abdomenUpper > chestLower > chestUpper > neckLower > neckUpper > head}; lCollar > lShldrBend > lShldrTwist > lForearmBend > lForearmTwist > lHand > lCarpal1..4 > lIndex1.., lThumb1.. | side a lower-case prefix letter; Bend = the bone, Twist = the twist |
| CMU BVH (cgspeed release) | Hips > LHipJoint > LeftUpLeg > LeftLeg > LeftFoot > LeftToeBase; Hips > LowerBack > Spine > Spine1 > Neck > Neck1 > Head; Spine1 > LeftShoulder > LeftArm > LeftForeArm > LeftHand > LeftFingerBase > LeftHandIndex1, LeftHand > LThumb | offset bones, BVH units, rest = zero rotation |
| Xsens MVN | Pelvis > L5 > L3 > T12 > T8 > Neck > Head; RightShoulder > RightUpperArm > RightForeArm > RightHand; RightUpperLeg > RightLowerLeg > RightFoot > RightToe | vertebra-named spine |
| Rokoko | HumanIK names | as HumanIK |
| Synty | Root > Hips > Spine_01..03 > Neck > Head; Clavicle_L > Shoulder_L > Elbow_L > Hand_L > Thumb_01, IndexFinger_01, Finger_01; UpperLeg_L > LowerLeg_L > Ankle_L > Ball_L > Toes_L | `Shoulder` is the UPPER ARM; finger names without a side |

Sources:
- 3ds Max Biped naming: https://help.autodesk.com/cloudhelp/2022/ENU/3DSMax-Character-Animation/files/GUID-8CDF3763-66B4-4565-BFD1-136332FA2EA4.htm ,
  https://download.autodesk.com/us/motionbuilder/sdk-documentation/SDKSamples/Scripts/Tasks/3dsMaxBipedTemplate.html ,
  https://github.com/nirholas/three.ws/issues/339 (Finger0/Finger01 numbering, spaces as underscores) ,
  https://download.autodesk.com/esd/3dsmax/cat-help-2010/files/WS7af5cac11814013a17ba0fbf11fde8bf84b-7ff0.htm (CAT naming)
- MotionBuilder / HumanIK: https://download.autodesk.com/global/docs/motionbuilder2013/en-us/files/Skeletons_Bone_naming_conventions.htm ,
  https://help.autodesk.com/cloudhelp/2022/ENU/Maya-CharacterAnimation/files/GUID-33859AA1-887B-4F8A-8360-F881C28EF351.htm ,
  https://mocappys.com/creating-custom-characters-using-custom-bone-names/
- Blender Rigify: https://docs.blender.org/manual/en/2.81/addons/rigging/rigify.html ,
  https://developer.blender.org/docs/features/animation/rigify/rig_class/
- Auto-Rig Pro: https://lucky3d.fr/auto-rig-pro/doc/ge_export_doc.html , https://lucky3d.fr/auto-rig-pro/doc/auto_rig.html
- VRM: https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md ,
  https://pixiv.github.io/three-vrm/docs/variables/three-vrm.VRMHumanBoneName.html
- Unity: https://docs.unity3d.com/ScriptReference/HumanBodyBones.html
- Character Creator: https://manual.reallusion.com/Character-Creator-4/Content/ENU/4.0/04_Introducing_the_User_Interface/Bone-List.htm ,
  https://github.com/soupday/cc_blender_tools/issues/414
- Daz Genesis 8: https://www.daz3d.com/forums/discussion/286281/g8-list-of-bones , https://github.com/GNVR-Dev/DazUERig
- CMU BVH: https://sites.google.com/a/cgspeed.com/cgspeed/motion-capture/the-motionbuilder-friendly-bvh-conversion-release-of-cmus-motion-capture-database/readme-file-for-the-bvh-conversion-release ,
  https://github.com/una-dinosauria/cmu-mocap/blob/master/READMEFIRST.txt
- General: https://cgtyphoon.com/rigging/bones-naming-in-the-human-character-rig/

## The design

### `SkeldarAnim/maya_skeletonmap.py` - stdlib, pure (a subprocess test pins it)

`recognize(paths, positions=None, spine_targets, neck_targets)` -> `Result(mapping,
convention, confidence, missing, refusal, notes, chains)`; `mapping` is {our UE5 name: source
path}. The hierarchy comes WITH the paths (`parent_map`: the nearest ancestor in the set).

- **Names** (`tokens`, `parse`): namespaces dropped, camel case, digits and every separator
  (space _ . - :) split; the side read wherever it sits (`Left`, `L`, `l` prefix - Daz's
  `lShldrBend` and CMU's `LHipJoint` come apart by camel case - `_l`, `.L`, `_L_`); known
  noise dropped (`mixamorig`, `DEF`, `CC_Base`, `J_Bip`, `Bip001`, `Character1`, Bend,
  stretch, `.x`); a kind per joint (hips, root, spine, neck, head, clavicle, shoulder,
  upperarm, lowerarm, hand, palm, finger + which + segment, thigh, calf, foot, toe), with
  `ignore` for twist, roll, end, nub, IK, weapon, camera, eye, jaw and face bones. Three
  convention-specific rules: Rigify's numbered spine (`_rigify`), Biped's two-digit fingers,
  Xsens' vertebrae. A side inherited from the nearest sided ancestor (Synty's fingers).
- **Chains decide what names cannot** (`_by_names`): the hips are the deepest joint named
  hips/pelvis that is an ancestor-or-self of the common ancestor of both thighs and the head
  (else that ancestor itself - ARP's `root.x`); the main chain runs hips -> head; an arm is
  the path from the main chain to a hand, so the forearm is the named one, the upper arm the
  named one or the joint before the forearm, the clavicle the joint before the upper arm
  (`Shoulder` resolves to either by position); a knee / elbow without a name is the chain
  joint furthest off the line (positions). The spine is the main chain below the first neck
  joint (or the arms' branch), DISTRIBUTED onto our targets with both ends kept
  (`distribute`: 3 onto 5 = spine_01/03/05, the Mixamo retarget's rule since 2026-09-05; 5
  onto 4 = 1, 2, 4, 5; 1 onto 2 = the first). Fingers by chain under the hand, 3 segments;
  a joint between the hand and a finger's first segment is that finger's metacarpal.
- **The root** is an ancestor of the hips standing at the FLOOR (UE root, CC BoneRoot, Daz's
  figure root); one at the hips' height (Biped's Bip001, the centre of mass) is no root - Main
  then takes the hips' horizontal travel, the Mixamo rule.
- **Structural fallback** with positions when names fail: the two lowest leaves are the
  feet, the top the head, their common ancestor the hips, the two leaves furthest out
  sideways above the hips the hands, sides from up x forward (forward from the feet), leg
  joints by height share, arm joints by chain position. Confidence 0.6. No fingers.
- **Refusal**, never a guess: a missing hips / head / thigh / calf / foot / upper arm /
  forearm / hand names what was not found («generic: no Hips/pelvis found - not a humanoid
  this retarget knows»).
- **Rest poses** (`body_frame`, `rest_score`, `choose_rest`): each candidate rest is scored
  by how far its limb bones point from the rig's, each read in its own skeleton's body frame
  (up pelvis->head, lateral right->left shoulder), so facing and wrappers do not count.
- `canonical_parents` (the mapped hierarchy in our names), `direction_children` (which child
  a bone's direction is read toward: the pelvis and spine up their chain, a hand at its
  middle metacarpal or middle finger, never the thumb), `covers_ue_core`, `scale_ratio`.

### Integration (kept to detection, schema construction, pairing and rest choice)

- **`maya_asretarget`**: `detect_schema` unchanged. A source that is neither UE5 nor Mixamo -
  or one that SCORED as Mixamo but `convention_of` says is not Mixamo/HumanIK (CMU, Unity), or
  scored as UE5 without the UE limbs by name (ARP shares `hand_r`, Daz `pelvis`) - becomes a
  `GenericSchema`: the map's mapping re-keyed into UE names, so every policy downstream
  (drive_plan, alignments, offsets, the vendor's Bake) runs as for a UE skeleton. Never a twin.
  The rest is the best of `rest_candidates` (jointOrient, firstFrame, bindPose); the mapped
  hierarchy goes to `alignments`; a source whose size is not ours (beyond 2 %) has its rest
  positions scaled about its root's parent and is driven through unregistered stand-ins
  (`_unit_sources`: a transform per bone at its world rotation, position x scale, under the
  holder; one `plan._replace(bones=...)` line in `connect`). A hand with a mapped metacarpal
  aims at it (`alignments`). UE5/Mixamo/UE4 paths byte-identical in behaviour.
- **`maya_pmretarget`**: the same fallback onto `UE5_ROWS` with its own spine targets
  (`spine_01, 02, 03, 05` = Spine1..3, Chest) and one neck; `rest_matrices(... "given")`; its
  own travel scaling, unchanged. Still imports nothing of its sibling.
- **`maya_uebridge/skeletonimport.transfer`**: a clip whose leaf names do not cover the UE
  limbs goes to `transfer_foreign`: both skeletons read by the map, paired through our names
  (`foreign_pairs`: chains distributed chain onto chain, so a 3-joint source spine drives the
  5-joint Manny at its ends and the UE4 Mannequin takes a 5-joint source's ends), every pair
  oriented with an offset aligning the two rests bone by bone, the pelvis placed too, the root
  on the hips' horizontal travel (`ground_axis` picks the local channel that is world height
  - the Creep's root is under a -90 X Null) or on the source's own floor root; a source at
  another size wrapped in a scale group about its origin for the length of the bake. The
  target's rest is its bind frame, its directions where its children actually stand.
  The UE path (leaf pairing, twin by median bone) is untouched.
- `maya_rig_retarget`: nothing changed; its refusal now carries the map's reason.
- `install.payload()`: `maya_skeletonmap.py` (the "every module ships" test).

## Decisions taken alone

1. UE5 and Mixamo detection stay first and exact; the generic schema only takes what they
   would have mis-taken: Mixamo-scored skeletons whose convention is not Mixamo/HumanIK, and
   UE5-scored skeletons without the UE limbs by name (not the head - see trap 161?).
2. The generic schema is never a twin: FK takes rotation only, rests aligned bone by bone.
3. Sizes within 2 % are our size (no scaling, no stand-ins) - Mixamo's path never changes.
4. A root bone counts only when it stands at the floor (15 % of the hips' height).
5. The head is required for a foreign convention (the main chain is hips -> head).
6. Synthetic sources for every convention (no Max/Blender/Unity/BVH files exist on this
   machine); the only real file, `Downloads/Sweep Fall.fbx` (Mixamo), is used where present.
7. Unreal's own synthetic rows are left out of the Maya verify (its road is
   verify_rig_pipeline's, run green on this branch).
8. The structural fallback maps no fingers.
9. Biped's spaces assumed to arrive as `_` (FBX/Maya node names cannot hold a space); the
   tokens treat space and `_` alike either way.

## Proof

- **Unit tests**: `tests/test_skeletonmap.py` (31), `tests/test_skeleton_conventions_wiring.py`
  (11), fixtures `tests/skeleton_conventions.py` (15 conventions + an obfuscated one): every
  convention maps exactly the bones its fixture names and NOTHING more, with and without
  positions; twist/roll/end/nub/IK never mapped; Biped's hips the Pelvis though its thighs
  hang off Spine; HIK's Shoulder a clavicle, Synty's an upper arm; Maya-sanitised Rigify and
  ARP names; covers_ue_core; the stdlib boundary. Full suite: **3549 tests OK**.
- **`docs/superpowers/plans/verify_skeleton_conventions.py` - 76/76 in mayapy standalone**
  (scratch `MAYA_APP_DIR`, 42 s). Each convention built as Maya joints with its own joint-axis
  convention (X, Y or Z down the bone), rest in jointOrient (or in rotate: CC, Synty, Unity),
  unit (metres for VRM/Rigify x100.9, CMU x2.243) and wrapper (Biped under a -90 X Z-up
  group, Rigify under an Armature), keyed arms/knees/spine/head/fingers and 70 cm of travel:
  - onto **Manny_Rig, Creep_Rig, Orc_D_Rig** through the Retarget button: every mapped bone of
    the game skeleton POINTS where the source's points (FK) - worst **0.0078 deg** Manny
    (0.16 deg at neck_02, the rig's neck in-between), **0.0002 deg** Creep and Orc D; bone
    lengths unchanged **0.000000 cm** on Creep/Orc D (Manny's left leg 0.009-0.046 cm, the
    rig's own mirrored-fit wander, CLAUDE.md); pelvis and root travel scaled exactly
    (**0.0000 cm**); 17-49 pairs per convention;
  - onto **Manny UE5 [skeleton], Creep [skeleton]** through `skeletonimport.transfer`: worst
    **0.0005 deg**, lengths **0.000000**, travel **0.0000 cm**, the map's scale equal to the
    measured one (x100.94 VRM/Rigify, x2.2432 CMU);
  - **Sweep Fall.fbx** (the animator's Mixamo clip): on Manny_Rig still the MIXAMO schema,
    worst 0.104 deg; onto both skeletons (new: it used to be "no bone matches") 0.0001 deg;
  - **rest choice sets the roll only**: the Unity clip with its rest forced to jointOrient,
    then firstFrame: directions 0.0000 / 0.0000 deg, upperarm_l's frame 95.80 deg apart;
  - the **PlayerMale** generic schema on a Biped and a Daz figure: 63/64 drives, 0 missing,
    the spine onto Spine1/Spine3/Chest and all four;
  - **refusals**: a quadruped refused on both roads with the map's reason;
  - **controls**: our bones at frame 10 against the source at frame 20 read 70-149 deg.
- **Existing standalone verifies on this branch** (copies with the plugin path pointed at the
  worktree): `verify_rig_pipeline.py` **0 of 30 failed**, `verify_many_rigs.py` **0 of 32**,
  `verify_creep_rig_asset.py` **0 of 16** (Creep orientations 0.00132 deg, lengths 0.000000).
  Not run: `verify_asretarget.py` / `verify_asretarget_mixamo.py` (live-scene, port 7001 is the
  animator's), `verify_uebridge_many.py` (needs a GUI Maya).

## Not done

- No real Max / Blender / Unity / VRM / CC / Daz / BVH file was on disk: those roads are
  proven on synthetic skeletons built to the researched conventions. BVH import itself is
  agent A's (formats).
- The PlayerMale rig's connect was not run (its asset is not in the plugin); its schema is.
- The structural fallback maps no fingers; a foreign skeleton without a head is refused.
- CAT rigs have no table of their own (user-named; the generic tokens read typical names).

## Merge risks

- `maya_asretarget.py`: `_plan` (the detect line now also calls `generic_schema`; `src_rest`
  from `schema.rest_given`; `alignments(... getattr(schema, "parents", None) or ...)`; `notes`
  starts from the schema's), `connect` (one line after `_remember_source`:
  `plan = plan._replace(bones=_unit_sources(plan, rig))`; the key-range line reads
  `source_bones(plan.root)`), `alignments` (the metacarpal preference), a new block before
  `rig_paths`, `import maya_skeletonmap`. Agent C edits drive building and `connect(bones=...)`
  in the same functions: keep both; if C's stretch drive adds its own scaled followers, the
  generic stand-ins (`_unit_sources`) and C's must not BOTH scale - `_unit_sources` is a no-op
  at scale 1.0, so C can route a scaled source through its own followers instead.
- `maya_pmretarget.py`: `_plan` detect + alignments + notes lines, `rest_matrices` "given",
  a new block before `rig_paths`, the import.
- `maya_uebridge/skeletonimport.py`: `transfer` (one early return to `transfer_foreign`), new
  functions after `onto_existing`/before `onto_skeleton`, `result_line` (the convention), the
  two "no bone matches" refusals (+ `_why`). Agent A's import funnel calls these unchanged.
- `install.py`: one payload row.

## CLAUDE.md section (draft)

## Every common source convention onto our rigs and skeletons (2026-10-02)

The animator: «прошелся по интернету нашел самые часто используемые иерархии костей для Unity,
Mixamo, blender, motionbuilder, 3dmax Unrealengine и сделал ретаргеты для этих систем на наши
риги и скелеты» (one of four tasks left for two hours, «сделать самостоятельно»). Spec:
`docs/superpowers/specs/2026-10-02-skeleton-conventions-design.md` - its table lists every
convention with its quirks and the sources read.

**`SkeldarAnim/maya_skeletonmap.py`** (stdlib, pure; a payload row): `recognize(paths,
positions)` answers {our UE5 name: source path} for Unreal, Mixamo, MotionBuilder HumanIK
(`Character1_`), Unity Mecanim, VRM (`J_Bip_`), Blender Rigify (`DEF-`) and Auto-Rig Pro
(`.x`), 3ds Max Biped (`Bip001`), Character Creator (`CC_Base_`), Daz Genesis, CMU BVH, Xsens
and Synty. Names first (namespaces, prefixes, camel case, the side anywhere: `Left`, `l`,
`_l`, `.L`, `_L_`), then the CHAIN: the hips where both legs and the spine meet (Biped hangs
its thighs off `Spine`, CC splits `Hip` into `Pelvis` and `Waist`), an arm the path from the
spine to a hand - so `Shoulder` is a clavicle in HumanIK and an upper arm in Synty by where it
stands - the spine and neck distributed onto ours with both ends kept (`distribute`, Mixamo's
3-onto-5 rule). Twist, roll, end, nub, IK, weapon and camera bones are never mapped. A root
counts only at the floor (Biped's `Bip001` is the centre of mass: Main takes the hips' travel).
Names failing, positions give a STRUCTURAL pass (lowest leaves the feet, the top the head,
furthest leaves sideways the hands). It refuses by name: «generic: no Hips/pelvis found - not a
humanoid this retarget knows». The rest pose is CHOSEN (`choose_rest`: the candidate - rotates
at 0, the first frame, the bind - whose bones point most like the rig's, each in its own body
frame); it sets only the roll, never where a bone points.

**Wired in without touching UE5 or Mixamo**: `maya_asretarget` / `maya_pmretarget` keep their
schemas; a source neither (or one only SCORING as Mixamo - CMU, Unity - or as UE5 by one shared
name - ARP's `hand_r`, Daz's `pelvis`) becomes a `GenericSchema` re-keyed into UE names, never
a twin, its rest chosen, its size scaled about its own origin through unregistered stand-ins
(`_unit_sources`) beyond 2 %. `skeletonimport.transfer`: a clip without the UE limbs by name
goes to `transfer_foreign` - both skeletons read, paired through our names (chains distributed
chain onto chain), each bone oriented through a rest-aligned offset, the pelvis placed, the
root on the hips' ground travel (`ground_axis`: the Creep's root is under a -90 X Null), the
source scaled for the bake. `Sweep Fall.fbx` now goes onto our skeletons too.

Proof: `verify_skeleton_conventions.py` **76/76 in mayapy standalone** - 13 synthetic
conventions (each with its own joint axes, rest in jointOrient or in rotate, metres / BVH units,
a Z-up Biped wrapper) plus Sweep Fall onto Manny_Rig, Creep_Rig, Orc_D_Rig (the Retarget
button) and Manny UE5 / Creep skeletons: every mapped bone POINTS where the source's does -
**0.0078 deg** Manny_Rig (0.16 at its neck in-between), **0.0002** Creep/Orc D, **0.0005** the
skeletons - lengths unchanged (0.000000 cm; Manny's left leg its own 0.05 cm wander), travel
scaled exactly (x100.94 metres, x2.2432 CMU, 0.0000 cm), refusals, the rest forced either way
(directions 0.0000 / 0.0000, frames 95.8 deg apart), controls 70-149 deg.
`verify_rig_pipeline.py` 30/30, `verify_many_rigs.py` 32/32, `verify_creep_rig_asset.py` 16/16
on the branch. 3549 unit tests. No real Max/Blender/Unity/BVH file exists here: synthetic only.

159?. **Maya has no `.` or `-` in a node name: an FBX import writes Rigify's `DEF-spine.003` as
     `DEF_spine_003` and ARP's `root.x` as `root_x`.** A reader written for the source file's
     spelling missed the scene's: Rigify's numbered spine read as six spine joints and no head,
     and the structural fallback took over with 21 bones. Read both spellings.
160?. **One shared bone name made a foreign skeleton score as Unreal.** `detect_schema` takes
     any hint: ARP's `hand_r`, Daz's `pelvis` -> the UE5 TWIN schema -> fingers 170 deg off and
     70 cm of travel lost. Unreal is the UE limbs BY NAME (`covers_ue_core`).
161?. **…and not the head: a first-person UE clip carries none.** The first guard required it
     and sent `LongSword_Attack_Right_Heavy_1P` (90 joints) down the generic road, which refused
     it - `verify_rig_pipeline.py` 13 of 30 failed until the head left `UE_LIMBS`.
162?. **A skeleton can stand off its own bind** (Manny's, 0.07 cm at the left calf): directions
     read off the `.bindPose` matrices came out 0.0989 deg wrong at EVERY frame. Read where a
     bone points from where its children stand, in the bind frame.
163?. **A hand aimed past a mapped metacarpal at the middle finger depends on the metacarpal's
     own turn**: 3.3 deg on Rigify/Daz sources. With metacarpals both sides, aim at the
     metacarpal.
164?. **The session scratchpad is shared by parallel agents**: another agent's commit message
     replaced this one's `msg1.txt` between two calls. Name scratch files per agent.
