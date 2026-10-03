# Pose Library — poses of bones, applied to any rig or skeleton (2026-10-02)

The animator: «Я бы хотел реализовать в нашем плагине библиотеку поз на подобии studio library.
... карточка которая содержит в себе анимацию наших объектов ... превью которое мы сами делаем из
сцены. Выделив наши объекты мы можем применить на них карточку ... при нажатии правой клавишей
мышки по карточке мы можем выделить объекты ... отдельное окно ... каталоги ... поиск и
сортировка ... если анимация относится к ригу то мы должны сохранять анимацию не контроллов а
костей ... задействовал уже написаные элементы ретаргета ... мне не обязательно выделять именно
сохраненные элементы достаточно выделить любую часть скелета или рига нажать apply ... перетягивать
наши карточки на персонажа драгом мышки ... Поза должна накладываться на текущий активный
анимационный слой. Если мы перетягиваем карточку в пустую сцену ... загрузит исходный риг или скелет
и выставит позу. Давай пока попробуем реализовать этот функционал а дальше будем работать над
добавлением анимации».

This build is **poses** (one frame). Animation cards come later.

Asked and answered:

| question | answer |
|---|---|
| extras in the first version | **Blend** (mix the current pose and the card's, 0..100 %) and **Mirror** (left ↔ right) |
| where the library lives | **a `poses/` folder in the plugin, installed like all our content** |
| the install wipes the installed folder | **local poses survive every install; on the animator's machine the library points at the repo's `SkeldarAnim/poses` once, so a commit + push ships the poses** |
| a full pose on a character standing elsewhere | **the character stays where it stands and faces** (root / Main untouched; the pelvis relative to the root) |
| keys | **always a key on the current frame, on the active animation layer** |
| a limb in IK | **both modes keyed**: FK and IK controls both take the pose, as the retarget does |

## What a card is

A folder `<Name>.pose/` holding `pose.json` and `thumbnail.jpg`. A catalog is a plain folder.
The library root is `skeldarPoseLibraryRoot` (an optionVar) when it is set and is a folder, else
`<plugin>/poses/` (made on first use). Files, not a database: a colleague receives them with the
build, the animator commits them from the repo.

`pose.json` (version 1), two kinds:

- **`character`** — the bones of ONE character:
  - `character`: the source's catalog `key` (`Manny_Rig`, `Creep`, …, or null for a native
    skeleton), `model`, `kind` (rig | skeleton), `label`, `convention` (`maya_skeletonmap.convention_of`),
    `rotation_only` (the rig's mark);
  - `bones`: EVERY bone of the source skeleton (context for recognising it later), each
    `{parent, canonical, rest[16], world[16], drive[16]?, rotateOrder}`:
    - `rest` = `maya_retargetmode.rest_world` (the skinCluster bind; trap 176);
    - `world` = the bone as it stands (what the skeleton SHOWS);
    - `drive` (rig sources only, the eight limb bones AdvancedSkeleton keeps unrolled — upperarm,
      lowerarm, thigh, calf per side; `rigsolve.drive_matrices`): the bone as the rig's DRIVE
      CHAIN holds it, `G · D⁻¹ · S` (G the game bone, D its AS deformation joint, S the FKX/IKX
      chain blended as the rig blends it — `fkik.blended`), i.e. with the roll AdvancedSkeleton
      moved into the twist joints put back (trap 126). Not the neck (task 6b): its controls hold
      any turn of its bones, so the neck lands its BONES (step 6 below) — in drive form a
      skeleton's card put Manny_Rig's neck_02 12.7° off;
    - `canonical` = our UE5 name from `maya_skeletonmap.recognize` run on the WHOLE source
      skeleton (it refuses a hand chain alone);
  - `members`: the bones the pose holds (a hand pose holds the hand's bones; see Save);
  - `regions`: arms / hands / legs / spine / head / pelvis, for the card's text.
- **`objects`** — Studio Library's attribute pose for anything that is not a character: per
  object its name (namespace stripped), path, and keyable scalar attributes' values.

Common: `name`, `created` (ISO), `author` (`skeldarShareName`, else the Windows user), `scene`,
`frame`, `fps`.

## Save

**+ Save pose** (the window) reads the selection:

- a node of one of OUR rigs (`maya_rigs.rig_of`) or of a skeleton (any joint, a skinned mesh, its
  character group, a weapon or armour piece, the CoM) names a **character**;
- on a rig, a CONTROL names its bones (`maya_asretarget.our_bone_map` + chains: an IK end or a
  pole, or an FK/IK switch, the whole limb; `Fingers_<side>` the hand's fingers; `Main`, the rig's
  group, a mesh — the whole body); a game bone names itself; an AS deformation joint its game bone;
- on a skeleton, a joint names itself; a mesh, the group, the root names the whole body;
- helper bones (`ik_*`, `weapon_*`, `camera_*`, `interaction`, `center_of_mass`) and twist bones
  are never members on their own — twist bones ride with their limb;
- several characters selected → refused («pick one character for a pose»); nothing of a
  character → an **objects** pose of the selected transforms.

The save panel shows the name field, the folder (the tree's current one), the character, the
**regions** as chips pre-lit from the selection (the animator can turn one on or off), and the
thumbnail with **Snapshot** to take it again. **Save** writes the card.

**Thumbnail**: a playblast of the active model panel at the current frame, JPG, at the port's own
size (WYSIWYG for the animator's camera), centre-cropped square and scaled to 320 px. NURBS curves,
joints, locators, dimensions (the clip labels), the grid, the HUD, manipulators and selection
highlight are switched off for the blast and put back (queried first). Viewport 2.0 loads textures
on idle (trap 120): two blasts must agree, up to five, with idle events pumped between.

## Apply — where, and how

**Targets** are every character the selection touches (any part: «достаточно выделить любую часть»),
each a rig or a skeleton; nothing selected → the only character in the scene, else a refusal naming
them. An objects pose: **the selection decides** — with objects selected the pose goes onto the
selection ONLY (nothing unselected is touched, the card's originals included): a selected object
that IS a stored one (its path) takes its own entry; each other selected object by name
(namespace-blind) among the stored ones — the next entry of that name not taken yet, in the stored
order, so two referenced copies of one prop each take their own values, and when every entry of the
name is taken the first one (two selected copies of one object both take it); the selected objects
left over taking the stored entries left over by order when their counts match; with nothing
selected, onto the stored objects found in the scene (the exact path first, then by leaf when
exactly one transform carries it).

**Pairing** source bone → target bone (pure):

- both skeletons carry the UE limbs by name (`covers_ue_core`) → by leaf name (`pair_bones`, the
  UE4 spine map when one side is UE4) — this reaches the twist bones and works for any subset;
- otherwise by canonical name: the source's stored names, the target's `recognize` at apply time;
  spine and neck chains distributed chain onto chain (`distribute`);
- a member with no partner is named in the status line.

**The transfer** (pure, OpenMaya matrices, rotations only):

- every paired member's target world rotation is the source's rotation RELATIVE TO ITS NEAREST
  PAIRED ANCESTOR, carried through the two rests:
  `W*[t] = O[t] · P[s] · P[sp]⁻¹ · O[tp]⁻¹ · W*[tp]`, with `O[t] = rigid(T_rest[t]) · A[t] ·
  rigid(S_rest[s])⁻¹` and `A` the minimal rotation taking the target's rest bone direction onto the
  source's (`skeletonimport._alignments`, identity for a twin); `tp` the nearest paired target
  ancestor (`canonical_parents`), whose `W*` is its own target when it is a member and its CURRENT
  world when it is not — so a hand pose lands on the arm as it stands. The roots are always paired
  with each other, and the target root keeps its place: `W*[root] = T_now[root]`;
- `P` is the source's `drive` where the TARGET is a rig and the bone has one, else its `world`;
- **positions**: every bone keeps the target's own lengths (forward kinematics from its current
  local translations); only the **pelvis** takes the pose's offset from the root, scaled by the two
  bodies' size (`maya_skeletonmap.size_ratio`), in the target root's frame;
- a twin gives `A = I`, so a pose saved and applied on the same model is exact. A twin is
  decided on the two RESTS alone, never on a pose (`posemath.twin`): the median paired length
  within 1 % (`maya_retargetmode.measure`'s rule) AND every paired bone's rest chord to its
  direction child within `posemath.TWIN_DEG` (1°) of its partner's — lengths alone would call an
  A-posed and a T-posed copy of one skeleton twins, and read as the bones stand a card whose
  bones carry translations stopped being a twin of its own model past ~1 cm.

**Mirror** transforms the source pose before the transfer: each bone takes its opposite's delta
from rest, reflected across the source's sagittal plane (`F = I − 2·l·lᵀ` in the root's frame, `l`
the rest's right-to-left direction), `P'[s] = F·(P[s̄]·R[s̄]⁻¹)·F · R[s]`; a centre bone reflects its
own delta; the pelvis position reflects too. The opposite comes from the canonical `_l/_r`, else
the leaf's side token (`Left/Right`, `_l/_r`, `.L/.R`, `_L_/_R_`).

**Onto a skeleton**: each member's local = `W*[t] · W*[parent]⁻¹` → joint rotate channels
(`R = RA⁻¹ · L · JO⁻¹` in its rotate order, the euler nearest the current one); the pelvis also its
translate. A channel driven by anything that is not a curve or a layer (a weapon link's constraint,
the animator's own) is skipped and named.

**Onto a rig** (`rigsolve`, generalising `fkik`'s analytic switch to the whole rig; nothing is
constrained, nothing baked, `reset_build_pose` is never called):

1. sample the rig ONCE at the current frame (every matrix below);
2. per AdvancedSkeleton joint base `b` (`Shoulder_L`, …) the game bone's constant constraint offset
   `O_g = rigid(G) · rigid(D)⁻¹`, and the drive-chain target `S*[b] = O_g⁻¹ · W*[g]`; positions of
   `S*` by forward kinematics in AS's own chain (its local translations, sampled);
3. **FK controls**, root-down: `C* = L⁻¹ · S*[b]` (`L` = the FKX joint in its control, constant),
   the parent's target world `piece · W*(anchor)` where the anchor is the control's nearest ancestor
   whose motion the solve knows (a solved FKX joint, or a group constrained to a solved deformation
   joint — `FKParentConstraintToWrist_*`, `…ToChest`, `…ToRoot`), the piece in between sampled;
   anchors the solve does not move keep their current world; rotate channels only;
4. **IK ends** of every limb with a member: `IK* = K · S*[end]` (`K` = `AlignIKTo<Wrist|Ankle>` in
   its FKX joint); **IKToes** from the ball the same way through its own chain; **poles** on the
   plane of the limb's `S*` (`fkik.pole_point`, the side read off the current IK chain); the arm's
   `swivel` and the leg's `roll`/`rock` keyed at 0 on that frame (the pose decides the foot); a
   limb whose `stretchy`, `antiPop` or pole `follow`/`lock` is off its default keeps its IK half
   unposed and says why;
5. **RootX_M** from the pelvis (`M = RootX · G_pelvis⁻¹`, constant), translate + rotate; **Main**
   is never written;
6. **the neck**: `FKNeck_M.bias` and the in-between's twist share are READ, never written
   (`set_exact_neck`'s "leave them there"); the neck controls are solved NUMERICALLY so the
   neck's BONES land (`FKNeck_M` through the in-between's blend, `NeckPart1` with the head
   re-solved inside every probe — `rigsolve`), measured by the verify at bias 0 and 10;
7. the spine in IK (`FKIKSpine_M` not 0): the FK spine is posed and the line says the spine shows IK;
8. write (below), evaluate, **measure** every member bone against its target (directions for the
   four unrolled limb bones, full rotation for the rest) and, if anything is off by more than
   0.01° / 0.01 cm, solve again from the new samples (at most three passes); the line names the
   worst.

A limb pose onto an IK limb keeps places and the hand's turn; an FK forearm twisted about its own
bone cannot be held by an IK elbow (a hinge) — measured and said, as the FK/IK switch does.

## Keys — the active layer

Measured in Maya 2027 (2026-10-02, mayapy):

- `animLayer -q -selected` per layer says what the Layer Editor has selected; several can be;
- `setKeyframe(plug, animLayer=L, value=v)` takes `v` as the plug's FINAL value, on an additive
  layer (it writes `v − base`, and `/weight` at a weight ≠ 1), on an override layer, and on
  `BaseAnimation` under an additive layer (base becomes `v − layer`);
- a plug not in `L` is refused with a warning — it must be added first (`animLayer -e -attribute`);
- `setKeyframe` WITHOUT `animLayer` goes to Maya's own best layer, not the selected one — always
  pass it;
- additive rotation in component mode (`rotationAccumulationMode` 0, the default) is per-channel
  exact; quaternion mode (1) is not;
- a LOCKED layer still takes a scripted key — so the tool refuses a locked layer itself;
- `setAttr` on a layered channel works and holds until the next evaluation of time.

The rule: the **active layer** is the selected non-base layer (several → the topmost in the stack,
named), else `BaseAnimation`; no layers at all → plain keys. Locked → refused. A plug not in the
active layer is added to it. Every value is keyed with the layer and `value=` final; eulers nearest
the current value. An additive layer in quaternion accumulation: the per-channel final values are
corrected so the composite lands (measured in the verify), or the press refuses naming the layer.
One undo chunk per apply.

## Blend

**Blend** mixes the target's current values (`C0`) and the pose's (`C1`) per channel: translations
lerped, each control's/joint's rotation slerped as a quaternion and written as the euler nearest
`C0`. The window's slider and a **middle-mouse drag across a card** (Studio Library's gesture) both
preview live (`setAttr`, measured to work on layered channels) and key on release; Esc puts every
value back. 100 % is Apply.

## The window

A `workspaceControl` `skeldarPoseLibrary` (floating, dockable; its uiScript carries the plugin path,
the hub's way), Qt inside, the hub's stylesheet and tokens:

- header: «Pose Library», the library path (muted), ⋮ (Library folder…, Open in Explorer, Refresh);
- toolbar: search (every term in name, folder or character), sort (Name / Newest / Character),
  card size, **+ Save pose** (primary);
- a splitter: the **folder tree** (New folder, Rename, Delete — to a trash folder beside the
  library, never permanently; cards dropped on a folder move there), the **card grid** (thumbnail,
  name, a character chip; culled painting and cached scaled pixmaps for hundreds of cards), the
  **details** (big thumbnail, name, folder, character, bones and regions, author and date,
  **Apply** (primary), **Mirror**, **Blend** slider, **Select objects**) and the status line;
- a card: click picks, double-click applies to the selection, right button: Apply, Apply mirrored,
  Select objects, Rename, Move to…, Replace thumbnail, Update from selection, Show in Explorer,
  Delete;
- **drag a card** past the start distance: the hub's ghost with the thumbnail; over a character in
  a viewport («Fist · onto Manny_Rig1» — `droptarget.character_target`) the release applies onto it;
  over an empty floor («Fist · a new Manny [rig] · floor (120, -36)») the source character is added
  there (`character.add_character(at=)`; a native skeleton is rebuilt bones-only from the card, its
  root ON the point whatever the card's rest, in one group and layer with Delete's record, as a
  native import is) and posed — deferred one idle (Add takes seconds), the import flushes undo (trap 115) so only the pose
  is undoable; over a folder in the tree it moves the card; over the window or the hub nothing;
  Esc / right button cancel;
- **Select objects** (and the right button's row): on the target character (the selection's, else
  the only one, else the source's namespace if it is in the scene) the controls the pose would key
  on a rig, the bones on a skeleton; an objects pose its objects.

The hub gets a **Pose Library** card in Animation (one line and **Open Pose Library**); a hotkey row
`window.poses`. No shelf button (the house rule).

## The install

`poses/` is a payload row. `install.copy_payload` no longer loses local poses: the installed
`poses/` is moved aside before the folder is replaced and put back **card by card** (a
`<Name>.pose` folder is one unit, never merged file by file - the final review, 2026-10-03: a
file-by-file merge threw a colleague's `Pose` card away for the first shipped `Pose` and could
glue their thumbnail onto it):

- every install and every build records what it SHIPPED in `poses/.shipped.json` (each card's
  relative path and its files' sha1, made from the payload itself; `make_build` writes it into
  the archive, never taking one from the tree; the leading dot keeps it out of the library);
- a card still identical to the previous build's manifest entry is the BUILD's: the new build
  carries it, or it renamed, moved or deleted it upstream - then it stays gone (a curated
  library does not grow back);
- every other card is LOCAL (absent from the old manifest, or changed since: Update from
  selection, Replace thumbnail) and goes back whole at its place - or, where the new build ships
  a card of that path (case-insensitively, as the disk compares), BESIDE it as
  `<Name> (local).pose` (`store.unique_name`'s rule: `(local) 2`, ...), its `name` field with it;
  a card byte-identical to the build's own is not doubled;
- folders come along; anything that cannot go back (a build's file where a local folder was)
  keeps the aside folder, and the Script Editor and the install's dialog say where it is;
- a copy that fails half way puts everything back and drops nothing (no new manifest).

An open Pose Library is rebuilt from the new modules after an install, as the hub is.

## Not built

Animation cards (several frames), selection sets, a pose's bone translations below the pelvis
(rotations only — stated), applying with root (the character always stays), the IK spine, sending
a pose to a colleague through Shared.
