# The «?» card: a clip onto ours when its skeleton is ours, else in its own skeleton (2026-10-02)

The animator, with Maya and an Unreal project «где много разных персонажей» open: «Иногда хочется
иметь возможность импортировать анимацию с исходным ригом скелетом который находится в движке а не
переносить на наши. Давай сделаем карточку рига и скелета со знаком вопроса и когда переносим анимацию
при выбраной этой карточке наш плагин будет смотреть какой скелет в исходном файле если он найдет
скелет который совпадает с нашим то перенесем анимацию на наш риг или скелет, если скрипт обнаружит
что совпадений нету то импортируем в сцену родной риг или скелет».

Asked, and answered (all three the recommendation):

1. **An explicit target wins.** With «?» and Onto selected, a selected character (or one the clip is
   dropped on) takes the clip as today; with nothing selected «?» decides. Never "the only rig in the
   scene": a Kwang clip must not land on the one Manny standing there.
2. **A native character is painted in a palette colour**, as the UE4 Mannequin is (Unreal's FBX
   carries no textures: Paragon's and UE4's materials arrive black, MetaHuman's grey).
3. **The kind is kept**: Rig means our rigs, Skeleton our skeletons. A clip that matches a model with
   no row of that kind (a UE4 clip with Rig, an Orc clip with Skeleton) comes in its own skeleton -
   the same skeleton, with Unreal's mesh.

## Measured first (MarkerLess_02, UE 5.8, 12 skeletons, ~2500 AnimSequences)

- **`FbxExportOption.export_preview_mesh = True` brings the mesh**: one skinned mesh beside `root` at
  world level (no wrapper), a skinCluster and a `bindPose`. 1.4-6.4 MB a clip against 1.5-1.6 MB bones
  only. The mesh is the exporter's choice: the clip's preview mesh, else its skeleton's, else
  `FindCompatibleMesh()`. The Python API exposes none of these (`get_preview_mesh` and the
  `preview_*` properties raise).
- **Unreal gives a Manny clip Quinn's mesh.** MM_Fall_Loop exported from three different SK_Mannequin
  folders came with `SKM_Quinn_Simple`. Its bind has Quinn's proportions (2 % of the bones within 1 %
  of Manny's), while the ANIMATION's bones have Manny's (100 %). So the match reads the animation,
  never the mesh's bind.
- **The share of bones whose animated length is within 1 % of our rest length separates every
  skeleton in the project.** Lengths are the median over 9 sampled frames, to the nearest bone both
  sides share. Helpers are not counted: `ik_`, `weapon_`, `camera_`, root, pelvis.

  | clip (Unreal skeleton) | Manny | Creep | Orc D | UE4 |
  |---|---|---|---|---|
  | MM_Fall_Loop (SK_Mannequin) | **1.00** | 0.37 | 0.45 | 0.00 |
  | am_Ready_Idle (MC_DungeonLife's MCUE5) | **1.00** | 0.37 | 0.45 | 0.00 |
  | AS_am_LongS (MC_LongswordVol2's MCUE5v2, 164 joints) | **1.00** | 0.37 | 0.45 | 0.00 |
  | Orc MM_Fall_Loop (SKEL_Orc_Marauder) | 0.47 | 0.31 | **0.88** | 0.03 |
  | Sword1h_WalkStop / Jog_Fwd (UE4_Mannequin) | 0.00 | 0.03 | 0.03 | **1.00 / 0.98** |
  | Ability_Q_Catch (Kwang) | 0.00 | 0.00 | 0.03 | 0.00 |
  | Idle_RC_pose (Sevarog) | 0.00 | 0.00 | 0.00 | 0.00 |
  | AS_AttackTest (MetaHuman, 342 joints) | 0.03 | 0.03 | 0.04 | 0.00 |
  | Cartwheel SKEL_Manny (root = pelvis, 79 joints) | 0.07 | 0.07 | 0.00 | 0.00 |

  The Orc clip's 0.88 is its arms: its arm bones carry Manny's lengths, 6.4 % off Orc D's rest. A
  single median would not do. Orc against Manny reads 1.9 % (35 of 78 bones within 1 %), so a 1 %
  median test is a coin toss. Without fingers it drops to 0.14 %.
- An FBX import into a namespace brings the mesh, its skin, materials and bind pose into the namespace.
  A group made first and the namespace merged into the root namespace after leave plain names and no
  joint renamed: `|Kwang_Character|root|pelvis` beside `|Manny_Skeleton_Character|root|pelvis`.

## What it is

### The card

- A fifth portrait, **Auto**, last in the grid: `catalog.AUTO = "Auto"` in `MODELS`, with a drawn «?»
  (`assets/character_portraits/Auto.png`, `make_auto_portrait.py`).
- It is pickable in both kinds (`kinds_of(AUTO)` is `KINDS`) and has no catalog row
  (`character_for(AUTO, kind)` is None).
- The line says «Auto [rig] - Import Animation puts a clip on our rig whose skeleton it is, else brings
  it in its own skeleton».
- **+ Import** refuses: Auto has nothing of its own to add.
- The portrait cannot be dragged and its right button offers nothing.
- In the dropdown fallback (no Qt) it is «Auto [rig]» / «Auto [skeleton]».
- `window.current_choice()` answers (model, kind) for the grid and the dropdown alike.
  `window.auto_kind()` is the kind when Auto is picked, else None.
- `chosen_character()` is unchanged: None for Auto.
- At the animator's 360 px dock the grid wraps to 4 + 1.

### The match (`maya_uebridge/skeletonmatch.py`, stdlib)

- **The templates:** `assets/character_skeletons.json`, one entry per catalog row. Each holds every
  game-skeleton joint as `leaf: [parent leaf, x, y, z]` at its bind (`maya_retargetmode.rest_world`),
  the file and its sha1. It is written by `docs/superpowers/plans/make_character_skeletons.py` (mayapy).
  A unit test pins one entry per row and the sha1 of the shipped asset: rebuild a character asset,
  re-run the script.
- **The clip:** `autoimport.clip_bones(source, start, end)` gives `{leaf: (parent leaf, [positions])}`
  over 9 frames, read by `getAttr(worldMatrix, time=)`. That is a plain keyed skeleton, so no rig is
  evaluated (trap 69 does not apply).
- **`score(clip, template)`** pairs bones by leaf name. Each voter is measured to its nearest ancestor
  that both sides share, and the two anchors must agree. Bones shorter than 1 cm on both sides do not
  vote, and helpers do not vote. It returns the share within 1 % and the count.
- **`match(clip, templates, keys)`** takes the best row of the asked kind. It must have at least 10
  voters and a share of 0.75 or more. Ties go to catalog order.
- The status names the match: «matched Manny [rig] - 78 of 78 bones». A miss names the best: «no
  skeleton of ours: best Orc D [rig], 45 % of 78 bones».

### The roads

**What decides.** `uebridge.window` asks `auto_kind()`. With Auto picked:

- **Explicit target.** Under Onto selected, a selection naming a character of the kind takes the clip
  exactly as today (`explicit_rig` / `choose_skeleton` with no fallback). Two selected is today's
  refusal; a rig named with Skeleton is today's refusal. A drop on a rig (Rig) or a skeleton
  (Skeleton) is the same: the drag's existing kinds `rig` / `onto_skeleton`.
- **Otherwise «?» decides**: New, or Onto selected with nothing named, or a floor drop.

**The one-clip press** (`autoimport.import_auto(ref, name, kind, clip_fps, set_timeline, at)`):

1. Import the clip (`rigimport.import_source`). A failure takes the namespaces back and restores time.
2. Match it.
3. A rig matched: the rig of that row is added and the clip retargeted onto it. This is
   `ready_rig` → `decide_bones` → `retarget_imported`, placed at `at` when given. A twin is never
   asked; Cancel removes the rig and the clip.
4. A skeleton matched: `skeletonimport.onto_skeleton(entry, ...)`.
5. No match: `nativeimport.keep`.

**Unreal exports with the mesh** on every «?» road that can bring a native
(`uescripts.export_script(..., preview_mesh=True)`, `window._export_from_editor(record, mesh=True)`).
A file source brings what its file holds: an FBX its mesh, a BVH or glTF joints only, a Unity clip its
model.

**Several clips** (`lineimport.run(..., auto=kind)`):

- Every clip is imported, then matched one by one.
- The square is laid out as today. The travel is not scaled: a twin and a native both keep it.
- Each clip goes to its own end: a new rig of its row, a skeleton of its row, or its own skeleton on
  its slot.
- The retarget version is asked once per row (`_Versions` per entry); twins are never asked.
- The summary names each clip: «3 animations in a 2 x 2 square about (0, 0): Manny_Rig MM_Fall_Loop,
  Orc_D_Rig Orc_Fall, own Kwang_GDC Ability_Q_Catch».

**The drag** reads `auto_kind` at its start:

- Over the floor its caption is «A_Jump · our rig if it matches, else its own · floor (x, z)». With
  several it is «3 animations · each onto ours if it matches, else its own · in a square · floor (x, z)».
- The aim carries `auto=True`.
- Over a rig (Rig) or a skeleton (Skeleton) it is today's caption and today's drop.

### The native character (`maya_uebridge/nativeimport.py`)

The clip's own skeleton, with what its file brought, kept as a character like a skeleton row. All of
it runs unrecorded (trap 115: the import flushed the undo queue).

1. **What arrived**: every node of the clip's namespace, by UUID.
2. **Placement** at a drop point or a square slot. The root's translate keys (or values) are offset
   so the root at the clip's first frame stands on the point. The world move is mapped through the
   root's parent at the first frame. No wrapper is left: the exporter writes ancestors (trap 182), and
   `fbxlayout` reads a root under a moved transform as "plain, with a note".
3. **The group**: `chargroup.make(base, label, root, tops)`. The tops are the namespace's world-level
   nodes. The base is the largest skinned mesh's name (`Kwang_GDC`), else the clip's namespace. The
   label is «Kwang_GDC [own skeleton]».
4. **Plain names**: the namespace merged into the root namespace, deepest first. A Mixamo clip's own
   `mixamorig:` goes too; exports strip it anyway.
5. **Colour**: `colour.paint_nodes(nodes, free colour, base)`.
6. **Delete's record**: `deletion.record_import(root, uuids, label)`.
7. **The clip's label**: `cliplabel.label_skeleton(root, clip name)`.
8. **The line**: «Ability_Q_Catch: no skeleton of ours (best Orc D [rig], 3 % of 64 bones) - in its
   own skeleton Kwang_GDC: 116 joints, 1 mesh, frames 0-36 | standing at floor (120, -36)».

The native character then works like any skeleton:

- Skeleton x Onto selected puts a later clip on it.
- Export FBX writes its bones.
- Delete takes it whole.
- Colour repaints it.

## Not built

- Textures from Unreal for a native mesh (asked: palette colour).
- An AdvancedSkeleton rig for a native skeleton: Rig + no match brings the skeleton.
- Choosing which mesh Unreal exports. The Python API has no preview-mesh call, and changing an
  asset's preview mesh would dirty the animator's project.
- Matching by the Unreal Skeleton asset's name. Only a third of the assets carry the tag, and three
  different `SK_Mannequin` folders are one skeleton.
