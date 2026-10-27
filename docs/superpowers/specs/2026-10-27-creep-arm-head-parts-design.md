# The Creep's right arm and head as rigs and skeletons of their own (2026-10-27)

The animator, after the Creep (`SK_Creep_skinned`, a model from Unreal, 91 bones, not our
shipped Creep_Rig) was split on port 7004 into a body, the right arm with its shoulder and the
head cut at mid neck, each with its own skeleton starting at the character's `root`
(`C:/!!!Work/Animations/Rigs/Characters/Creep_Split/Creep_{Body,Arm_R,Head}.fbx`):

> «Руку и голову ... нужно сделать риг на адванцед скелетоне и встроить в наш пайплайн как и
> персонажей. Рука должна переноситься по всем нашим правилам на правую руку голова на голову»
> «Убедись что ФК контролы работают как у менни при смени позиции растягиваются кости у орка и
> старого крипа это не так»

Asked, all three the recommendation:
- a clip lands on a part **where the body would hold it** (the clavicle / neck follow the clip's
  chest in the world, root motion included): set beside a whole character playing the same clip,
  the part sits on it;
- **rig and skeleton** cards, two new models in Animation Setup;
- the arm rig: **FK + IK with the switch, the pole, the fingers, Main**.

## The parts

| model | game skeleton | AdvancedSkeleton |
|---|---|---|
| `Creep_ArmR` | `root` > `clavicle_r` > upperarm_r ... fingers, twists, `weapon_r` (29) | Root_M at the chest, Scapula_R > Shoulder_R > Elbow_R > Wrist_R > fingers, twist Parts; `noMirror`: no left arm |
| `Creep_Head` | `root` > `neck_01` > `neck_02` > `head` (4) | Root_M at the chest, Neck_M (in-between NeckPart1_M on neck_02) > Head_M |

The fit is AdvancedSkeleton's `UE5.ma` with everything else deleted, the side chain / neck
re-parented under Root, every fit joint put on its bone (the Creep procedure's `fit`), Root on
where `spine_05` stands in the whole body's bind (the bone is not in the part, its place is read
from `Creep_Body.fbx`).

## FK as on Manny, not as on the Creep and the Orc

Every game bone follows its AdvancedSkeleton joint by **point + orient + scale, maintainOffset**
(the vendor's "Constraint to Joints", Manny's rig) - a translated FK control moves its bone and
the ones below it (stretch). The shipped Creep and Orc D take orientation only
(`as_creep_rig_procedure.constrain`); they are not changed here.

So the part rigs are NOT marked `skeldarRetarget = "rotation"`: the retarget's Auto rule
decides (a twin exact, another body asks Keep proportions / Squash & stretch).

## The anchor: where the part stands

A part rig carries `Group.skeldarPartAnchor = "spine_05"` and a transform
`<ns>:PartAnchor` under its `Group`, standing where `spine_05` stands in the whole body at the
build pose, following `Root_M` (parentConstraint, maintainOffset). `maya_asretarget`:
- `part_anchor(rig)` -> (UE bone, anchor path) or None;
- `_plan` adds the anchor to the rig's bones under the UE bone's name, and `RootX_M` is driven
  from the clip's bone of that name (UE5 `spine_05`, Mixamo `Spine2`, any other convention its
  canonical) instead of the pelvis; everything else is unchanged.
So RootX_M lands on the clip's chest exactly as a whole rig's lands on its pelvis, and the arm /
neck hang on it. Main still takes the clip's root (root motion in `root`).

## In the pipeline

- `catalog.Character` gains `part` ("" for a whole character, else the anchor bone). Rows
  «Creep Arm R [rig]» / «[skeleton]», «Creep Head [rig]» / «[skeleton]»; assets
  `Creep_ArmR_Rig.ma`, `Creep_ArmR_Skeleton.ma`, `Creep_Head_Rig.ma`, `Creep_Head_Skeleton.ma`;
  palette colours (the FBX carries no textures); portraits; a fire each.
- The Auto («?») card never matches a part (`skeletonmatch` skips rows with `part`): a
  full-body clip must not land on an arm.
- The Skeleton road (`skeletonimport`) needs nothing: a twin by leaf names puts every bone on the
  clip's world matrix, the top bone included.

## What the build changed (addendum, the same day)

- **AdvancedSkeleton wants its middle joints on x = 0** (within 1 % of its scale; else «"RootSide" is on
  the Left side»): this Creep stands 0.32 cm off it, so Root (and the head's Neck / Head / HeadEnd) fit
  joints go to x = 0 and the -mo constraints carry the step; `PartAnchor` stays on the real `spine_05`.
- **The FBX importer locks a skinned mesh's t/r/s AND the compounds `translate` / `rotate` / `scale`**:
  unlocking rx/ry/rz alone left `rotate` locked, `cmds.parent` and `xform` were silent no-ops and the
  first build's meshes lay on their side (the head's HeadEnd then stood at the mesh's wrong top).
  `out_of_group` unlocks both levels around the move.
- **weapon_r takes Creep 2's socket** (`WEAPON_SOCKET`, read off `Creep2_Rig.ma`): the FBX the part was
  cut from carries the creature's socket, a quarter turn about its X off the plugin's UE standard;
  turned with the skins kept at their bind.
- **A part is never squashed** (`maya_rig_retarget.decide_for`, `_plan`): its own clip (a twin) goes whole,
  any other by rotation, never asked - a scale has no body to happen about, and the head (three bones)
  was read at x0.898 from its neck alone and landed 47 cm off. The twin measure leaves out the root and
  the anchor pairs: the top bone's distance from root is the clip's spine moving, not a length.
- **The Skeleton road**: a bone hanging straight on the root takes the clip's place too
  (`skeletonimport.transfer`, `on_root`), as the pelvis does - else a part's top bone stayed on its root
  while the clip's chest moved (458 cm on a death clip).

## Proof

- `verify_creep_parts_rig.py` (live build, port 7004): every fit joint on its bone, every game
  bone on its AS joint, FK translate moves the bone (stretch), FK / IK switch, no left arm.
- `verify_creep_parts_asset.py` (standalone): the four rows added, a UE clip retargeted through
  the button onto each rig: the top bone stands where the clip's chest would carry it, bones
  point as the clip's; onto each skeleton; unit tests for `part`, the anchor, the Auto skip.
