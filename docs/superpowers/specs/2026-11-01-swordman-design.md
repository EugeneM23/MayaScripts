# Swordman: a Max Biped character onto our skeleton, keeping his proportions

2026-11-01. The animator, with the character open in a Maya on port 7006:

> В открытой сцене по порту 7006 персонаж и у него есть скелет. Его нужно
> адаптировать под наш пайплайн, давай перенесем на наш скелет (только сохраним
> пропорции) и сделаем риг и ретаргет. Все по нашим правилам. Также давай
> разберемся с оружием оно должно быть в вепон боне а не так как сейчас.

Asked, and answered:

- the sword goes on `weapon_r` and the shield on `weapon_l`, both as catalog
  weapon rows;
- the skeleton is **our names, his proportions, 55 bones** — Manny's 93 less the
  38 finger bones (the hand is a mitten; there is nothing to animate in it).
  The first answer was "only the bones he has", which would have left him
  without the `weapon_r` the same message asked for; put precisely, the answer
  was 55;
- `maya_skeletonmap` learns this convention, so his old takes retarget;
- he arrives textured.

## What is in the scene

Measured over the port, read only. The scene is **untitled and modified**; a copy
was exported to `sources/swordman/Swordman_Scene.mb` (530 KB) with the scene's
name, modified flag, frame, unit, node count and selection all unchanged.

A 268-vertex mitten-handed body on a 3ds Max "Base Human" Biped skeleton of
**25 joints**: `Pelvis`, `Spine1..4`, `Ribcage`, `Neck1`, `Neck2`, `Head`,
`{L,R}Collarbone/Upperarm/Forearm/Palm`, `{L,R}Thigh/Calf/Foot`, and two
`UpVectorNode` helpers. No fingers, no toes, no twist joints, and **no root at
the floor** — the pelvis is the top joint, so root motion lives in it.

- The **pelvis carries scale 2.54** (an inch→cm conversion left in the channel).
  Everything below inherits it.
- **17 joints are skinned**; `Spine1..4`, `Neck1`, `Neck2` and the two helpers
  carry no weight.
- The local translates do not change over the take (spread 0.0000 on all 22
  parent-child pairs), so the bone lengths are rest constants.
- He **faces +Z with his left on +X** — our own convention. No axis conversion.
- The two `UpVectorNode` joints have `nan` world positions (scale 0, nan
  rotates). Biped junk; dropped.

### His proportions against Manny, at the bind, in cm

| | Manny | Swordman | ratio |
|---|---|---|---|
| head height | 162.6 | 158.9 | 0.98 |
| arm (upper+fore) | 55.0 | 54.8 | 1.00 |
| leg (thigh+calf) | 85.6 | 83.8 | 0.98 |
| spine total | 45.7 | **59.7** | **1.31** |
| pelvis height | 95.9 | **83.5** | **0.87** |
| shoulder width (x) | 19.0 | **25.7** | **1.35** |

Near Manny's height on Manny's limbs, but a long torso on a low pelvis with much
wider shoulders. That is what "сохраним пропорции" has to preserve.

His `Ribcage`→`Neck1` is **0.353 cm** — the neck starts at the ribcage, where
Manny's `spine_05`→`neck_01` is 11.9. Kept as his.

### The two hand objects

Both are plain DAG children of the palm joints — the thing to fix.

- `Object014` under `RPalm`: a **sword**. Blade down local +Y with the tip at
  +Y, guard on X, thickness on Z — already our catalog weapon frame.
- `Object013` under `LPalm`: a **shield**, a flat plate with a rim and a boss.

Their local matrices under the palms are rigid and pose-independent.

## Two measurements that decide the build

**The dagPose is not the bind.** `dagPose -restore bindPose1` leaves the skinned
joints up to **3.43 cm** off the bind the mesh actually uses (palms 3.43,
forearms 2.63, upper arms 2.08, head 1.95, collarbones 1.15, ribcage 0.36; the
pelvis and both legs are exact to 0.00008). The skinCluster's `bindPreMatrix`
is the bind. Anything built from the dagPose would move the mesh.

**The props are 2.54× their own points** (trap 86). The sword's own geometry is
46.1 cm long; in the world it is a **117 cm** blade, because it is an unskinned
child of the scaled chain. The shield's 19.2 × 23.7 × 3.7 is **48.8 × 60.2 ×
9.4** in the world. The same trap once shrank the Creep's sword from 124 cm to
94 and was not caught until the animator saw it.

## The design

### 1. The skeleton — 55 bones, built on the bind

`root` · `pelvis` · `spine_01..05` · `neck_01` `neck_02` `head` ·
`clavicle/upperarm/lowerarm/hand` ×2 · `thigh/calf/foot/ball` ×2 · 16 twists ·
7 ik helpers · `weapon_r` `weapon_l` · `camera_root` `camera_bone` ·
`center_of_mass` `interaction`.

The 17 bones he has twins for are placed **on their bind matrices**, read from
`bindPreMatrix`, orientation included. One to one:

| his | ours |
|---|---|
| Pelvis | `pelvis` |
| Spine1..4, Ribcage | `spine_01..05` |
| Neck1, Neck2, Head | `neck_01`, `neck_02`, `head` |
| {L,R}Collarbone | `clavicle_{l,r}` |
| {L,R}Upperarm / Forearm / Palm | `upperarm` / `lowerarm` / `hand` |
| {L,R}Thigh / Calf / Foot | `thigh` / `calf` / `foot` |

Because our bones land exactly where his are, **the body is rewired, not
re-bound**: each `skinCluster.matrix[i]` is reconnected to our joint of the
mapped name and the `bindPreMatrix` is left alone — the road
`armor._wear` / `rewire_plan` already takes for clothing. Every vertex stays
where it is, to zero. No weight transfer and no drift.

`Spine1..4`, `Neck1` and `Neck2` are unskinned, so they carry no weight and
nothing downstream depends on where exactly they sit. They are placed like this:
take their positions from the restored bind pose, express each as a fraction
along the chain, and then re-lay the chain from the **skinned** pelvis to the
**skinned** ribcage (and from the ribcage to the head) keeping **his** segment
lengths exact and distributing the endpoint difference — 0.36 cm over 59 cm for
the spine — evenly along it. So the curve is his, both ends are the skin's, and
every segment is his own length. Taking the restored positions as they stand
would mix two rests (trap 209); this does not.

The bones he has no twin for, by rule:

- `root` at the floor on the midline under the pelvis, with Manny's −90 X
  jointOrient. The floor is the body's lowest vertex at the bind, y = 0.210.
- the 16 twists at the measured fractions of **our** new segments: 1/3 and 2/3
  for `upperarm` and `thigh`, 2/3 and 1/3 for `lowerarm` and `calf`.
- `ball_{l,r}` at the forward-most point of the foot's own vertices, on the
  floor.
- the 7 ik helpers by Manny's rules: `ik_foot_*` on the feet, `ik_hand_gun` and
  `ik_hand_r` on `hand_r`, `ik_hand_l` on `hand_l`, the roots at the origin.
- `weapon_r` / `weapon_l` in the hands in the **UE socket convention** (the
  2026-09-30 standard: the grip line down the bone's +Z, the palm normal −Y),
  mirrored as Manny's are.
- `camera_root` / `camera_bone` on the midline at his head's height.
- `center_of_mass`, `interaction` by Manny's rule.

The **2.54 scale never arrives**: our skeleton is created fresh at scale 1 from
world matrices. The sword and shield are unskinned children of the scaled chain,
so their **world** matrices are carried across, never their locals.

### 2. The weapon

Two catalog rows, both exported from their geometry **at world size** (×2.54):

- `Swordman Sword` → `weapon_r`, scale 1
- `Swordman Shield` → `weapon_l`, scale 1

Each row's `frame` and its remembered grip are derived from one measurement: the
weapon's world matrix at the bind, expressed in its weapon bone's frame. That
whole matrix is `grip · frame · bone` by `bonedrive`'s own rule, so the part of
it that is the model's own turn becomes the row's `frame` and the remainder
becomes the grip stored under `mayaSceneSetup_offset_<key>`. The test of the
derivation is the one that matters: **Add Weapon at zero grip puts each back in
the fist exactly where he holds it now**, gated to 1e-4 cm. Because
`weapon_r`/`weapon_l` get the standard socket turn, every other catalog weapon
fits his hands too.

### 3. The rig

The Creep procedure, live in a **disposable Maya on port 7008** — never the
animator's: fit, build, the game bones constrained to their AS joints, controls
on the bones' own axes, IK feet level. Three differences:

- no finger chains in the fit;
- `Group.skeldarRetarget = "rotation"` — his proportions are not Manny's, so a
  clip keeps **his** lengths;
- Creep 2's position-follows, so moving an FK control carries its bone.

His bind is an A-pose with the arms 71° down from horizontal. That is steeper
than Manny's but still an A-pose, and `fit()` puts every fit joint on its bone,
so the build pose is his bind.

### 4. The look

`Swards Man Texture.psd` → `assets/Swordman/Swordman_Color.jpg`, one textured
material naming it relatively (trap 119: built from an empty working folder, the
path asserted relative before the save). Catalog rows `Swordman [rig]` and
`Swordman [skeleton]`, model `Swordman` in `MODELS`, a portrait rendered in a
disposable GUI Maya, a fire palette in `maya_charfire.FIRES`, and
`character_skeletons.json` re-run.

### 5. The skeleton map — three words

Measured, not guessed. The tokeniser already reads these names
(`BaseFBXASC032HumanLCollarbone` → `['base','fbxasc','032','human','l',
'collarbone']`) and **gets the sides right**. Three things are wrong:

| | today | fix |
|---|---|---|
| `LCollarbone` | `kind=None` | the token is `collarbone`; `parse` looks for `collar` |
| `LPalm` | `kind='palm'`, dropped from the arm chain as a metacarpal, so the **forearm became the hand** | a `palm` with no finger children *is* the hand |
| `UpVectorNode`, `Platform` | read as limbs | into `_IGNORE` |

Without them the structural fallback does map the skeleton — and **swaps left
and right and takes the 26 cm collarbone for the upper arm**. With them his
970-frame FBXs retarget correctly, and so does any future Max Biped.

## What this gets, and what it costs

Works: Retarget, the weapon sockets, Camera Setup, Connections, Inventory, the
Pose Library, Add and Delete character, the Auto card.

**Does not**: his FBX export is a 55-bone skeleton of its own in Unreal, not
interchangeable with the UE5 Manny skeleton; and a Manny clip's finger animation
is dropped on him. That is the price of the 55, accepted by the animator.

Not built: a 1P mesh (he has none), an Armor row for the shield (it is a
weapon_l row instead), and his takes are not baked onto the new rig — they come
through the bridge once the map reads them.

## Proof

`docs/superpowers/plans/verify_swordman.py`, mayapy standalone:

- both rows added, at their bind, textured, with **every vertex where the
  source's own skin puts it**;
- the 55 bones, our names, his segment lengths to the source's;
- a UE clip through the Retarget button: bones turned as the clip's, **his
  lengths unchanged**;
- the sword at zero grip in the fist driving `weapon_r`, the shield on
  `weapon_l`, both at their world size;
- the export: 55 joints, no meshes;
- Delete character takes all of it, one Ctrl+Z brings it back;
- his own old FBX read by the fixed map with left and right correct, against the
  present map as the control.

Unit tests for the three `maya_skeletonmap` words, including the two the present
map fails.
