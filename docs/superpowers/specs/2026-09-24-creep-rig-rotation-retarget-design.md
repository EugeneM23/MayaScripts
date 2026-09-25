# The Creep: clean skeleton, A-pose bind, an AdvancedSkeleton rig, a rotation-only retarget

2026-09-24. Scene: `C:/Users/MY PC/Downloads/creep_T-pose_MIX_06_skin.mb` (the animator's,
unsaved at the end of the day). The character is a creature ("Creep"; its group was
called `Hanter` in the morning and renamed by the animator mid-session) on a UE5 Manny
skeleton — Manny's 90 bone names plus `weapon_test`, minus `weapon_l/r` and `camera_*` —
with a creature's proportions: arms 34.8 + 36.0 cm against Manny's 27.8 + 27.3, a neck
7.3 + 7.8 against 5.1 + 4.9, the same legs (43.34 against 43.35). Six skinClusters: body,
back, arm_l, arm_r, face and a leftover `SKM_Manny_Simple` inside the group.

The animator's asks, in order:

1. «избавится от изменений скейлов на костях, скейл везде должен быть равен 1»
2. «в сцене есть персонаж из unreal engine, его байнд поза — A; я бы хотел чтобы и у
   нашего хантера байнд позой стала A поза»
3. «для хантера тоже сделаем такой же риг [AdvancedSkeleton] … ретаргет не должен
   учитывать растяжение костей (привязываем только по ротейшенам)»
4. (after seeing the rig) the IK foot controls stand slightly tilted — take the foot
   bones' turn away there, axes and drawing both level.

## 1. Joint scale → 1, nothing moves

Twelve joints carried scale (`lowerarm_l/r` 1.32, the first phalanges 1.12–1.29), with
segment scale compensate off everywhere — so the hands and fingers stood at world scale
up to 1.70. Every joint's scale set to 1 and its world matrix re-written with the scale
normalised out (parents first), then per influence `BPM' = BPM · WM_old · WM_new⁻¹`, which
keeps each skinning matrix and so the mesh. Measured: joint positions 0.000000 cm,
orientations 2e-6°, all six meshes 0.000000 (also the one skin that was not at its bind).

## 2. The A-pose bind, re-baked in place

Pose the joints, read each skinned mesh's object-space points, set `BPM = WM⁻¹` for every
influence, write the points onto the intermediate Orig shape, `dagPose -reset`. Mesh drift
across the bake ≤ 4e-6 with a non-identity geomMatrix on two skins (the skin is
`p·G·Σw(BPM·WM)·G⁻¹`).

**The first bake copied the UE bind for clavicle, upperarm, lowerarm AND hand — and the
animator saw the hands change size.** Every "unchanged" gate had passed: the gates
measured the mesh across the bake, which is trivially equal. The measurement that finds
it is edge lengths against the old rest mesh: the 51° wrist turn stretched arm_l/arm_r
edges ×3.2–4.4. Dual quaternion and a temporary deltaMush did not fix the wrist. The
standing bind keeps the hand's own turn against the forearm (clavicle/upperarm/lowerarm on
the UE bind to 0.000°): arm meshes ≤ ×1.06, 0 of 2949 edges changed more than 25%. The
body/back shoulders do change (1344 / 585 edges > 25%) — that is lowering an arm with
these weights, in any A-pose. Backups in `Downloads/creep_T-pose_MIX_06_skin_BACKUP_*.mb`.

## 3. The rig — `docs/superpowers/plans/as_creep_rig_procedure.py`

The Manny procedure with four differences:

- **Long paths everywhere** (`bones()`): the scene held a second skeleton with the same
  names (the UE reference Manny, later deleted by the animator), so `xform("hand_r")` and
  the vendor's Name Matcher were ambiguous.
- **Leftover AdvancedSkeleton utility nodes** of a deleted rig (264 DG nodes in `AllSet`,
  `Sets`, layers `BodyControls`/`DeformationJoints`) were removed first — checked to have
  no connection outside themselves. A build over them would get its node names uniquified.
- **The fit is put on every bone**; finger tips continue their last phalanx by the preset's
  ratio, HeadEnd sits on the top of the face mesh. 42 joints placed, mapped ones 0.000000 cm.
- **Orientation-only bone constraints** (pelvis point + orient). With the vendor's point +
  orient + scale the LEFT arm's lengths wandered 0.01–0.07 cm with the bends and
  neck_02→head sat 0.035 cm short: AS mirrors the left side from the right fit while the
  Creep is 0.045 cm asymmetric, a `-mo` point constraint keeps that offset in the bone's
  PARENT space, and the neck in-between joint is not on neck_02. Orientation only: lengths
  exact, no translation keys below the pelvis in an export, AS's own stretch never reaches
  the skeleton — which is this character's rule anyway.
- **IK feet level** (ask 4): `as_frames(("IKLeg_L", "IKLeg_R"))` gives them AS's own frame
  back (IKOffsetLeg, world-aligned) and AS's own drawing. **Trap:** asControlOrientAttach
  re-orients the FK↔IK align target (`AlignIKToAnkle_*`) only for a control that ends up
  custom-oriented; a control put back on AS's frame gets no CustomOrient, the target keeps
  the bone-frame turn, and asAlignIK2FK then lands the IK foot in the right place turned
  **117.93°** (exactly the old frame's angle). `align_ik_target` does Attach's
  `delete orientConstraint ctrl alignTo` itself.

Proof: `verify_advancedskeleton_creep_rig.py` — **0 of 25 gates failed, live 2026-09-24**.
Three gates of the Manny script measured the wrong quantity on this skeleton and were
rewritten, not loosened: the forearm twist (the Creep's twist joints REST turned 26.7° and
5.7° against the forearm — a difference of angles is not the twist; measured in the
forearm's frame: 39.1° / 19.6° for a 60° wrist roll), the finger curl axis (the right
pinky_02 rests rolled 16° against pinky_01, so the world delta is not about its Z; measured
against the parent), and "non-joint nodes under root" (the animator's swords under
`weapon_test`).

## 4. The rotation-only retarget — `maya_asretarget`, marked by the rig

`Group.skeldarRetarget = "rotation"` (`rotation_mode(rig)`, read off `rig.group`). Then:

- every FK control takes the source bone's world orientation (the twin's own rest offset,
  ≈ identity since the controls stand on their bones) and **no position**;
- the IK ends and poles follow the rig's OWN FKX joints — the PlayerMale retarget's rule,
  copied (`IK_FOLLOW`, `POLE_FOLLOW`, `_pole_measure` / `_pole_rig`); the pole's geometry is
  now measured BEFORE the first constraint moves the FK limb;
- Main and RootX_M keep the twin's drive: root motion and the hips land on the source's
  exactly. Unscaled: the legs are Manny's length, and root motion is gameplay data.

UE's "rotations from the animation, translations from the skeleton" — which is what "не
учитывать растяжение костей" means. An unmarked rig (every Manny rig) is driven exactly as
before; `maya_rig_retarget` needed no change (UE names → this module). 17 unit tests
(`tests/test_asretarget_rotation.py`), 2195 in all.

Proof: `verify_creep_rotation_retarget.py` in **mayapy standalone** on a saved copy of the
rigged scene with `AS_am_LongS_OxGuardR_AttackDownLeft_OxGuardL.FBX` (72 frames, 164 joints)
— **0 of 10 gates failed**: every non-limb bone on the source's world orientation to
0.001°, the Creep's bone lengths unchanged on every sampled frame (0.000000 cm) while the
source's own differ (lowerarm 27.25 vs 35.98), root and pelvis 0.000000 cm, IK against FK
0.001 cm, nothing of the retarget left standing.

**Upperarm / lowerarm / thigh / calf are compared by where they POINT, not by roll:**
AdvancedSkeleton's Shoulder/Elbow/Hip/Knee do not roll about their own bone — the roll goes
to the twist (Part) joints (up to 94.9° on this clip), as on the Manny rig. And AS removes
the roll about ITS joint's axis, so a child standing off the bone's X (the Creep's
lowerarm: 0.32 cm, 0.53°) swings on a cone; the joint-to-joint direction is therefore
bounded by twice each skeleton's own off-axis angle (1.07° on upperarm_r), measured from
the children's local translations. Worst excess over that bound: 0.038°.

**The hand helpers, the animator's layout** (asked after the first build): `ik_hand_r` and
`ik_hand_l` stand EXACTLY on their hands (0.000000 cm, ≤ 0.000003°) and follow them with no
offset; `ik_hand_gun`, their parent, is not driven and its channels are zero
(`place_ik_helpers`). The T-pose file had all three where a Manny's hands would be, 15–55 cm
off the Creep's. They are skin influences of zero weight; their bindPreMatrix is
re-expressed anyway and bindPose1 reset. `ik_foot_*` already stood on the feet (0.0007 cm)
and follow them as before.

Not built: a catalog row for the Creep rig in Add Character; the IK toes keep their bone's
frame.

## Addendum — the Creep ships in the plugin (same day)

«Давай сделаем пуш коммит в гит хаб, после чего добавим хантера как риг в наш плагин» —
the shelf is ours (SkeldarAnim; "Atone" was the project's name), and `SKM_Manny_Simple` is
not to be shipped: «Нет! И насчёт мешей давай приведём всё в порядок, назовём как-то
правильно и сгруппируем, чтобы геометрия не валялась где-то непонятно где».

**The tidy** (`tidy()` in the procedure, run live on the animator's scene; every node held
by UUID — the first attempt re-parented the root and then asked for the swords by their old
long paths, CLAUDE.md trap 16): `|root` to world level with the FBX wrapper's turn in its
jointOrient (Manny_Rig.ma's shape: skeleton at world, meshes in a group, the rig under
`Group`); `Creep_Body`, `Creep_Back`, `Creep_Arm_L`, `Creep_Arm_R`, `Creep_Face` (and
their shapes) in AdvancedSkeleton's own `Group|Geometry`, which was empty; the two swords
(`Creep_Sword` from `SwordPacked`, `Creep_Sword_Low` from `Sword_Low.001`) out of the
skeleton — a mesh under a bone rides into every animation export — into
`Geometry|Creep_Props`, parent-constrained to `weapon_test`; the old wrapper renamed
`Manny_Reference`, holding only the Manny mesh. Measured: swords 0.000000, every skin still
BPM·WM = I (the bones did not move), the sword following an arm pose 44.24 cm and back to
0.000000. The live verify's gates 1 and 16 were rewritten for this shape: 25/25.

**The asset** `SkeldarAnim/assets/Creep_Rig.ma` (39 MB), built by
`make_creep_rig_asset.py` in mayapy standalone from a saved copy: the reference mesh with
its skinCluster and animation, `camera1`, `materialXStack1`, the shading networks nothing
wears (Manny's, mostly), unknown nodes and empty dagPoses deleted; Maya's own two
configuration script nodes — rewritten by every save — cut out of the text afterwards; the
file refused if any banned string survives. Catalog row 1, «Creep [rig]», `kind` "rig";
`character.rig_namespace(entry)` = the entry's key, so a Creep lands as `Creep_Rig`,
`Creep_Rig1`. Proof `verify_creep_rig_asset.py`, 10/10 in standalone.

## Addendum 2 — the clean skeleton row

«Давай добавим возможность загрузить не только риг хантера, а и чистый скелет». Row
«Creep [skeleton]» (key `Creep`, kind "skeleton", after «Manny UE5 [skeleton]»), file
`assets/Creep_Skeleton.ma`, derived from the shipped rig so the two can never disagree about
the bind: `make_creep_skeleton_asset.py` records every bone's world matrix, deletes the
skeleton's constraints, re-seats each bone from its world matrix (0.000000000), moves the
meshes and props out of `Group|Geometry` into `|Creep`, deletes `|Group`, then deletes every
node nothing kept depends on — decided by DEPENDENCY, not by type or name: the kept set is the
two hierarchies, the meshes' and props' whole history, their shading networks, the bind pose,
the skeleton's display layer and Maya's default nodes. That removed 315 nodes of
AdvancedSkeleton's network (multiplyDivide 95, blendTwoAttr 25, setRange 24, …, its ik
solvers, expressions and driven-key curves) and the FBX-embedded textures of the creature's
original materials, which no assigned material used. Proof `verify_creep_skeleton_asset.py`,
9/9 standalone. Like every skeleton row it arrives with plain names: a UE clip merged onto it
by the bridge would carry the clip's bone translations — the rotation-only rule belongs to
the rig, which is the road for animating the Creep.

## Addendum 3 — weapons on the Creep, as on every rig

«Сейчас у нас оружие хантера встроено прямо в риг. Давай это исправим и сделаем
консистентно ... добавлять и удалять оружие и анимация переносилась на вепон бону и обратно.
Также давай добавим меч хантера в список нашего оружия». Two choices, the animator's: the
sword is `Creep_Sword` alone (described to the animator as "the whole sword; `Creep_Sword_Low`
is a second grip piece" -- wrongly: Low IS the grip, see addendum 8),
and the weapon bone is renamed to the plugin's `weapon_r` with a `weapon_l` added.

Measured first: in `weapon_test`'s frame the sword's blade ran down −Y (tip −74.30, pommel
+19.65), its guard across X (±6.17), its thickness on Z (±1.74) — the catalog's convention
turned half a turn. So `weapon_r` = `weapon_test` turned 180° about its own Z, and the sword,
expressed in that frame, IS the convention with the origin where the Creep held it: Add at
zero grip lands it exactly where it was. `weapon_l` is the behaviour mirror of weapon_r
(S·M·S, X negated) under hand_l. `make_creep_sword_asset.py` does it on the shipped rig in
standalone (sword exported FIRST — it rides the bone by constraint), then the clean skeleton
is rebuilt from the new rig.

The retarget's helper bones (weapon_r, weapon_l, camera_*) were carried in WORLD space —
right for a twin, whose hand stands where the source's does, and wrong for a rotation-only rig
whose arm is its own length: the Creep's weapon_r would have stood at Manny's hand.
`helper_space(mod, rig)` answers "parent" for a rotation-only rig and `transfer_bone` then
drives the bone through W_src · P_src⁻¹ · P_dst — the clip's grip, on the rig's own hand.
Proof `verify_creep_rig_asset.py` 13/13 (the weapon gates 11–13 in the summary above).

## Addendum 4 — the weapon lives OUTSIDE the skeleton (every rig, same day)

The animator asked what the export does with a sword parented under the hand. Measured: the
exporter takes a selected node's children along, and every animation FBX carried the sword
(10890 vertices, six curves and a material). Then: «А можем ли мы вообще не располагать наше
оружие прямо в иерархии скелета? А крепить его к скелету, например, констрейнами», and,
offered the options, «давай делать всё максимально правильно, так чтобы мы не нарушали
иерархию нашего скелета». Two changes, both for every rig and skeleton, not only the Creep.

**A weapon space per hand** (`maya_scenesetup/weaponspace.py`, a leaf): `hand_r_weaponSpace`,
a plain transform parent-constrained to the hand with NO offset, marked `mayaWeaponSpace` (the
hand's UUID), standing in a `WeaponSpaces` group (marked `mayaWeaponSpaces`, channels locked)
under the rig's top group, or at world level beside a bare skeleton. The weapon is the space's
CHILD, so its channels still mean "relative to the hand" and nothing downstream had to change:
the bone-relative grip, the bonedrive link, the relink after an import, OverRig's
`parent_in`/`parent_out`. The space is found FROM the hand, through the constraint the hand
drives (`space_of`), never by name, so a second character's `hand_r_weaponSpace1` changes
nothing. `ensure_space` makes it on the first Add or hang; `prune` deletes a space that holds
nothing but its constraint, and the group once it is empty. `holding_hand(weapon)` answers the
hand for a weapon in a space AND for one a file from before holds directly under the hand;
`hand_for(path)` lets a selected weapon still name its character (`skeleton.current_root`).

- `attach.attach` parents into `ensure_space(hand)`, `find_attached` asks the space first and
  the hand second, `detach` prunes.
- `connections.apply`: the hang is `parent_in(weapon, ensure_space(hand))`, and the space the
  weapon left is pruned after a lift or a move; `read_scheme` asks `holding_hand`.
- A legacy weapon keeps working where it is, and moves into a space on the next Connections
  hang or a Remove + Add.

**The export writes bones only**: `FBXExportIncludeChildren -v false`, and every joint of the
hierarchy is selected by UUID inside the plain-name rename (the rename invalidates the paths,
trap 16). So nothing parented under a bone, by us or by hand, reaches Unreal.

Proof: `verify_weapon_space.py`, **11 of 11 in mayapy standalone**. A Creep and a Manny rig:
each sword in its hand's space in its own rig's group, both skeletons bones and constraints
only, the space on the hand posed (2.8e-16), a selected sword naming the Creep, both retargeted
with the sword on weapon_r over the take (4.4e-14 / 1.2e-5), the FBXs read back with 91 and 93
joints and 0 meshes (a cube parented under hand_l by hand included) and weapon_r's
hand-relative track kept to 0.0000, Remove pruning the space and the group, a legacy under-hand
sword found and removed. `verify_connections.py`, **40 of 40 twice**, on a throwaway Manny_Rig
with the Long Sword and a throwaway Creep_Rig with the Creep Sword, in a SEPARATE disposable
Maya on port 7002 (OverRig's `parent_in`/`_out` need a live Maya, and the animator's scene was
not the place): hangs into `hand_l`'s and `hand_r`'s spaces, the emptied space pruned each way,
the skeleton bones-only at every step. 2211 unit tests.

## Addendum 5 — the bind becomes SKM_Manny_Simple's pose (same night)

The animator put the original creature back in a scene — `|SKM_Manny_Simple`, the untouched FBX
(T bind, the old joint scales 1.12–1.32 on forearms and fingers) — keyed at frame 0 into the pose
the Creep should stand in, beside a Creep rig added from the shipped asset: «исходная поза у рига
Creep_Rig:Group и у скелета этого рига не должна никак отличаться от позы скелета SKM_Manny_Simple,
нужно переделать так, чтобы позы максимально совпадали», and «текущая поза SKM_Manny_Simple должна
стать байнд позой для Creep_Rig:root».

Measured (read-only) against the A bind of section 2: bone lengths identical, all five meshes the
same vertex count; the pose differs by 50.6° on the hands, 55–91° on the fingers, 11° on the neck,
up to 6° on the spine, 7.5° on the legs, 5° on the feet, 1.4° and 2.4 cm on the pelvis, while
clavicles, upper arms and forearms matched to 0.001°. The hands' 50.6° is the first A bake's 51°
wrist turn again, and SKM's own skin shows what it costs: edges stretched ×3.1 at hand_l, ×4.7 at
thumb_01_r, 62 / 112 edges past 1.5× on the hand meshes (the A bind: 0). Offered the exact pose,
the exact pose with the wrist turn kept, or the exact pose with smoothed wrist weights, the animator
chose **the exact pose, the mesh exactly as SKM shows it** — what they see on SKM_Manny_Simple is
what the bind looks like.

How: the pose (90 world matrices) and SKM's five meshes as its skin deforms them there, plus its T
rest for a vertex-order check, dumped to `creep_bind_pose.json.gz`. `rebind_creep_pose.py`
re-binds the clean skeleton in place (section 2's method): the bones onto the pose's matrices with
the scale stripped (ours carry none), the helpers by their rules (ik_hand_r/l on the hands,
ik_hand_gun at zero, ik_foot_* keeping their relation to the feet, weapon_r/l riding the hands with
their local channels untouched), each Orig shape set to SKM's deformed points, BPM = WM⁻¹, bindPose1
reset — joints on the pose to 2e-9, the mesh to 5e-6. The vertex order is checked, not assumed: 100 %
of the face, 71 % of the body and 48 % of the back sit exactly on SKM's T rest (what the A bake never
moved), and the two arm meshes, which the A bake moved whole, match by edge length. Then the rig is
REBUILT, not re-aimed: `rebuild_creep_rig.py` runs the procedure's steps live in a disposable Maya
(AdvancedSkeleton reads its own UI), and because `fit()` sets every fit joint on its bone, the new
rig's build pose IS the new bind (gate 5: 2.6e-13). The asset scripts then produce Creep_Rig.ma and
Creep_Skeleton.ma as before (the rig asset's source is now the rebuilt scene; its asserts expect 91
joints and no props, and it refuses `Creep_Sword` / `Creep_Props` / `weapon_test` in the text).

Proof: `verify_creep_bind_pose.py` 9/9 (bones on the pose to 9.9e-10, vertices on SKM's to 5.1e-6
cm, skin at bind, helpers, a positive control, the clean skeleton, and weapon_r/l in the hands as in
the old asset to 2.8e-14 — the sword's frame); the live rig verify 25/25; the rig asset 13/13; the
clean skeleton 9/9; the weapon spaces 11/11; Connections 40/40 on the new Creep; 2211 unit tests.

## Addendum 6 — the rig's joints on the skeleton's, left side included (same night)

«Кости скелета и кости рига не совпадают, как минимум на левой руке». Measured on the rebuilt rig
(read-only, the animator's scene): the skeleton was on SKM's pose to 0.0000, and the AS joints were
off their bones in two ways.

- **The left fingers, 1.1–3.2 cm — new.** Exactly the pose's own asymmetry (left bone vs mirrored
  right bone, per joint): SKM_Manny_Simple bends its fingers differently on each hand, and
  AdvancedSkeleton builds the left side as the mirror of the right fit. The A-pose rig was symmetric
  (0.05–0.08 cm, the skeleton's own asymmetry), so it never showed. Fixed with the vendor's own
  "create non-symmetry joints" (`asCreateNonSymmetryJoints`): the left chains become fit joints of
  their own (`<joint>_NonSymmetry`, the right side marked `noMirror`), the build names them `_L` as
  before, and `fit()` puts them on the `_l` bones. The Knee's `twistJoints`, added by the procedure,
  is copied onto `Knee_NonSymmetry`.
- **The upper-arm twists 2.35 / 4.70 cm and the neck in-between 0.51 cm — old.** The A-pose asset
  measured the same numbers. AS spaces a segment's Part joints evenly (`<joint>PartBM<side>` blends
  toward the child by 1/(n+1), each Part the same step), and the Creep's upper-arm twists stand at
  0.266 / 0.532 of the bone (the forearm, thigh and calf twists are at 1/3, 2/3 already). The new
  `place_parts()` sets the BM weight to the game twists' step. The child joint is point-constrained
  by AS onto its FK/IK twin, so it keeps its place (checked, and refused if it did not). `NeckPart1_M`
  is point-constrained onto the neck→head line while neck_02 stands 0.44 cm off it, so the constraint's
  offset moves it on. The offset is in Neck_M's space, where neck_02 is rigid, and it held under neck
  bends to 0.0000.

The skeleton takes orientation only, so neither change moves it. Live gate 26: every deformation
joint on its bone to 0.0000 cm, twist Parts to 0.17 cm (the Creep's own twist bones stand that far
off the bone line), 26/26. The pose verify 9/9, rig asset 13/13, skeleton 9/9, weapon spaces 11/11,
Connections 40/40, 2211 unit tests. What is left and why: under a strong neck bend the rig's head
drifts ~0.1 cm from the skeleton's head, because the two neck chains are built differently. That is
cosmetic, since the skeleton copies orientation only.

## Addendum 7 — the normals (same night)

«Что произошло с геометрией, почему она стала такой тёмной?» — the hands of the re-bound Creep
shaded dark. Every normal of the five meshes is LOCKED (the FBX's own), and the rebind writes new
points into the Orig shapes, and locked normals do not follow points. So the rest mesh kept the
T-pose's normals: measured per vertex against the area-weighted surface normal, the hand meshes
read a median 55–59° (p90 99–107°) on the new rig and 44° already on the morning's A-pose asset;
the face and back 3–6°. The skin turns locked normals as the rig moves (a 60° shoulder turn turned
them 34–56°), so only the rest normals had to change, and unlocking was ruled out (it would lose
the file's hard edges).

The right rest normals are SKM_Manny_Simple's in the pose, which the skin already turned from its
T normals, consistent with "the mesh as SKM shows it". `dump_creep_bind_normals.py` imports that
FBX in standalone, checks its points against the pose data (1.5e-6), and dumps the world
face-vertex normals. `rebind_creep_pose.set_normals` writes them onto the Orig shapes (object
space, locked); the built rig scene was fixed with `--normals-only` and the assets rebuilt. After:
the hand meshes 4.6–4.8° median off their surface, the shown normals SKM's to 0.0008°; the pose
verify's gates 10/11 pin both on the rig and on the clean skeleton.

## Addendum 8 — the sword, whole and on the animator's grip (same night)

«Меч хантера почему-то оказался без рукоятки, мы где-то её потеряли, и он повёрнут на 45 градусов;
при повороте меча 0 0 0 он должен встать так, как сейчас». The handle was left out at addendum 3.
The creature's sword is two meshes riding weapon_test: `SwordPacked` (10890 vertices, blade,
guard and pommel) and `Sword_Low.001` (1170 vertices, the grip, −7.3..+13.6 along the bone). The
animator was asked about the second as "a second grip piece" and chose the first alone. The question
had not measured the piece. In the scene the animator had dialled the grip Rotate to (0, 45, 0).

`make_creep_sword_fbx.py` takes both pieces from the tidy backup scene into weapon_r's frame
(FLIP_Z · weapon_test, as `weapon_bones` built the bone), turns them by the (0, 45, 0) grip and
unites them into one mesh, since a catalog weapon is one geometry. So at zero grip the sword stands
where the 45 stood it. Read back like Add: 12060 vertices, the blade the old asset turned by the grip
to 8.7e-7, the handle at Y −13.57..7.33. In the animator's scene the sword was swapped at zero grip
(one undo chunk; refused if a hand followed the weapon), and the remembered grip was zeroed so the
next Add does not add the 45 again. Every blade vertex stood where it stood at 45, over the take, to
8.7e-7 cm; weapon_r did not move.

## Addendum 9 — the sword's axes on its geometry: a weapon's frame (same night)

«Сейчас у меча развёрнута геометрия, а оси стоят ровно … чтобы оси соответствовали направлению
геометрии», and then «но при этом меч сохранил свою позу в руке». With the 45 in the points, the node
stood on weapon_r's axes and the guard stood 45° off them. So the points go back to the model's own
axes (guard on X, like every catalog weapon), and the 45 becomes a property of the catalog row:
`Weapon.frame`, default identity, `(0, 45, 0)` for the Creep Sword. Attach writes it on the marked node
as `mayaWeaponFrameRotate`. Every grip is composed on it: world = grip · frame · bone. So zero grip
stands the node, with its axes, where the 45 stood the geometry, and the fields read 0 0 0. The
read-back takes the frame away, and a relink with nothing stored places at zero grip.

Connections moves the drive to weapon_l "with no offset: the socket sits on the weapon". The socket
is the weapon's frame undone, so the constraint's target offset holds `unframing(frame)` in the
bone's rotate order. A node without the attribute is the identity, so every other weapon and every
older file are unchanged.

Proof:
- `verify_creep_rig_asset.py` 15/15, including every vertex where the grip-in-its-points asset stood
  (8.7e-7) and the guard along the node's X;
- `verify_weapon_space.py` 11/11;
- `verify_connections.py` 40/40 for both Creep and Manny, in a disposable Maya.

## Addendum 10 — the exported mesh's smoothing, and the bind pose (same night)

«Скелет выгрузился без групп сглаживания на геометрии». The FBX's smoothing layer was all zeros.
Every edge of the five meshes was hard in Maya, already in the animator's creature scene, under
all-locked normals. The source FBX has the real flags, and they are exactly the normal
discontinuities plus the borders. Our meshes carry that source's normals, so the flags are derived
from them (`set_edges`). Only the flags are written: cleanup re-shares normals wrongly, and writing
the normals back hardens everything (both measured).

The same export dropped the bind pose. bindPose1 was missing four bones and had three members whose
parent link skipped the pose, so it is saved again over all 91 joints (`whole_bind_pose`).

Both steps now run in the rebind pipeline. `repair_creep_assets.py` applied them to the shipped rig
asset, and the clean skeleton was rebuilt from it. The export checks the smoothing on the way back.

Proof:
- hard edges per mesh equal the source's: 618 / 618 / 2832 / 10833 / 1284;
- no bind-pose warning in the export log;
- `verify_creep_bind_pose.py` 15/15, the rig asset 15/15, the skeleton 9/9.
