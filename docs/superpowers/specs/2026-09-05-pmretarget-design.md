# Retarget onto the PlayerMale AdvancedSkeleton rig — design and record

**Date:** 2026-09-05/06. **Ask:** «Теперь давай для текущего рига который открыт в
сцене сделаем копию скрипта ретаргета на разные скелеты. На скелеты unreal
engine, mixamo и на собственный скелет. При создании ретаргетов давай не
учитывать изменения позиций в костях как мы делали раньше только вращения. И делай
это отдельным модулем это не имеет отношения к skeldar».

Module: `maya_pmretarget.py` (repo root, standalone, `cmds` + OpenMaya, no Qt, a
copy of `maya_asretarget.py` with a different target and rules — it imports nothing
from its sibling, and a test pins that). Tests: `tests/test_pmretarget.py` (55).
Proof: `docs/superpowers/plans/verify_pmretarget.py` — **green live 2026-09-06,
all 32 gates passed**, on three sources the script builds or imports itself.

## The target

The rig built 2026-09-05 over the PlayerMale game skeleton
(`2026-09-05-advancedskeleton-playermale-rig-design.md`): 57 game joints driven
by 56 AS deformation joints, four spine controls (`FKSpine1..3_M`, `FKChest_M`),
one neck, jaw and eyes, fingers of three joints, no twist joints, 17.5 units tall
in a centimetre scene. `our_bone(control)` is the whole map from a control to
the game bone it stands on (`FKChest_M → Spine4`, `IKLeg_L → Left_Ankle`,
`Main → Root`, `RootX_M → Hip`).

## Decisions

1. **FK controls take rotation only**, through an `orientConstraint` whose offset is
   our rest frame against the source's rest frame, the rest poses aligned bone by
   bone where the skeletons differ (the Mixamo module's `alignments`, with the hand
   pointing along the middle finger). Never position — the animator's rule, and a
   foreign skeleton's positions would hand the rig its proportions. Measured: a
   source bone translated 1.0 slides the copy's arm root 1.0 away while ours keeps
   its 0.954 clavicle and the same orientation (gate 8).
2. **The IK end controls and the poles follow OUR OWN FK joints**, not the source:
   `IKArm/IKLeg ← FKXWrist/FKXAnkle` (parentConstraint, rest offset on its target
   offsets), `IKToes ← FKXToes` (orient), and each pole placed from its whole FK
   limb. A rotation-only retarget has no source position to give an IK hand; the
   vendor's own connect puts the source's hand there and lands wrong by the
   proportion difference. So the IK pose is the FK pose in our proportions, and the
   animator bakes once and switches either way (gate 9: switching the arm to IK
   moves the hand 0.000000).
3. **Travel is scaled.** UE and Mixamo clips stand ~170 cm, this character 17.5
   units: `scale_factor` = our pelvis height over the source's, each above its own
   root (8.557× for the Manny, 1.0 for our own skeleton). `Main` follows the
   source's root bone in rotation and scaled translation (a Manny's 100 cm root
   travel becomes 11.6869, gate 19); with no root bone (Mixamo) it takes the
   hips' horizontal travel from their rest. `RootX_M` follows the pelvis in
   rotation and scaled position.
4. **Three source schemas, detected in order** by required and absent bones: `OWN`
   (`Hip`, `Spine4`, `Right_Arm`…; rest = our own bones' rest by name, no
   alignment), `UE5` (`spine_05`; rest from the shipped
   `manny_skeleton_template.json`), `UE4` (`spine_03` and NO `spine_05`; rest from
   `ue4_mannequin_template.json`, extracted 2026-09-05 from the shipped
   `UE4_Mannequin.fbx` in mayapy: 68 joints, pelvis at 96.75), `MIXAMO` (`Hips`,
   `Spine2`; rest = every rotate at 0). A UE clip's `root` carries `jointOrient
   −90`, the template's world matrices carry the same, so the rest matches the
   clip as it stands.
5. **Spines.** UE5: `Spine1..3 ← spine_01..03`, `Chest ← spine_05` (spine_04 is
   left alone); UE4: `Chest ← spine_03`, our `Spine3` left alone; Mixamo:
   `Spine1 ← Spine`, `Spine2 ← Spine1`, `Chest ← Spine2`, our `Spine3` left alone.
   UE has no jaw or eyes and Mixamo no jaw — those rows are simply not in the
   tables, so they are never "missing". Mixamo's eyes drive `FKEye_*`.
6. **A control already constrained by something that is not the rig is left
   alone and named** (`foreign_constraints`): the animator's own work in progress
   (2026-09-05, the left arm's FK controls parent-constrained to `locator1/2/3`
   beside an OverRig setup) — a second constraint on a driven channel would fail
   or fight. Our own constraints are recognised by their `nodeState` registration
   on `MoCapConstraints.disableConstraints`, so a plan read after a connect is not
   fooled by them.
7. **The vendor's contract is kept**: every constraint registers its `nodeState`
   on `MoCapConstraints.disableConstraints`, every helper sits under
   `MoCapConstraints`, so AdvancedSkeleton's own Bake and Disconnect work
   unchanged (gate 12: 26 driven controls keyed, every node of ours gone).

## What went wrong on the way, and what it cost

- **A `pointConstraint`'s `offset` is in the constrained node's PARENT space.**
  `RootX_M`'s parent follows `Main`, so a 25° root turn turned the pelvis offset
  with it: the pelvis was 0.115 off after the yaw. The offset now lives on a third
  helper transform under the scaled group (`pmrtOffset_`, the offset divided by
  the scale so it comes out in world units), and the control's pointConstraint
  carries none. Difference after the fix: 0.000000 (gate 20).
- **The pole.** Three placements were built and measured before one stood. A pole
  riding the UPPER bone's frame at its rest standoff (the Manny module's answer)
  was 0.11° off on our own take and **5.0°** on a UE take, whose bends come
  through the alignment about axes that are not our knee's hinge. One riding the
  KNEE's frame was the same. The vendor's three-point placement — a base on the
  hip-ankle line at the knee's share, nudged a tenth of the limb in world z and
  aimed at the knee — went **19.7°** wrong on a STRAIGHT leg under a yaw, because
  a straight knee's direction is undefined and the world-z nudge decided it. What
  stands: the same base, the nudge **in the FK knee's own frame** (so it turns with
  the knee and, on a straight limb, carries the FK roll) and **0.2 % of the limb**
  long (a 2 % nudge left 0.3° of itself out of plane on a bent knee), aimed at the
  knee, the pole a limb's length out. Measured: pole 0.000384 from the FK plane,
  IK knee 0.000083 from the FK knee, bone directions 0.001°; UE take in IK
  **0.0388°** (from 4.87°).
- **What remains in IK is the skeleton's own.** With the pole in the plane the IK
  thigh and knee still differ from FK by **0.33° of roll** (directions exact, Y and
  Z axes both 0.33° off): this skeleton's knee hinge stands **0.36° off its own
  rest bend plane** (`knee Z · plane normal = 0.99998`), and an IK solver bends
  about the plane's normal where FK bends about the hinge. No pole position fixes
  that — moving the pole off the plane trades roll for knee position. Stated as a
  cost: in IK the legs follow to 0.33°, in FK exactly (0.00000°). The FK bake is
  the product; the IK follows for switching.
- **`ls("pmrtMx:*")` does not reach a nested namespace**: the clip's joints arrive
  as `pmrtMx:mixamorig:Hips`. The verify finds them by the UUIDs the import created.
- The verify read its plan AFTER connecting, when every control carried our
  constraint and `foreign_constraints` called them all busy (before the holder
  check existed); measure before you build.

## Measured, in the final state (verify_pmretarget.py, 2026-09-06)

- **OWN** (a copy of the game skeleton, 20-frame take with 19 rotations, a 30-unit
  root travel with a 25° yaw, one bone translation): 64 controls driven (52 FK by
  rotation, 6 IK ends, 4 poles, Main, RootX_M; 3 left-arm FK controls skipped for
  the animator's own constraints), 80 constraints. FK bones on the source to
  **0.00000°** at every sample; root travel, yaw and pelvis **0.000000**; the
  translated clavicle ignored; IK arm on the FK hand **0.000000 / 0.00000°**; IK
  legs to 0.33° (roll, the hinge skew); AS's Bake keys 26 controls, Disconnect
  leaves nothing; the rig plays the take with the source gone (FK 0.00016°).
- **UE5** (the Manny template as a 93-joint fixture, 8.557× our size): 61 controls
  (49 FK), bone DIRECTIONS on the Manny's to **0.0042°** in FK and **0.0388°** in
  IK over 31 bones; root travel **11.6869** for 100 cm (scale 0.1169), yaw 25.0000;
  pelvis delta **0.000000** off the scaled source; the clavicle translation
  ignored; the arm's proportion difference reported, not scaled away.
- **MIXAMO** (the animator's `Sweep Fall.fbx`, 65 joints): 60 controls (48 FK),
  directions to **0.0155°** in FK; Main on the hips' scaled horizontal travel from
  rest (0.1183) and on the ground; Hip at our rest height plus the scaled travel
  (10.7866 vs 10.7865 expected).
- Nothing left in the scene, no namespace, the controls carrying exactly the keys
  they carried before; range, frame, autoKey, evaluation mode, blends, selection and
  the FBX import mode restored.

## The morning after: «ретаргет сработал только на 1 кадре»

The animator connected the Mixamo clip and pressed AdvancedSkeleton's Disconnect —
without its Bake. What the scene showed (2026-09-06): no `MoCapConstraints`, no
keys on any driven control, the rig frozen in the pose of the frame it was
disconnected on, the MoCap Matcher window not even open. Connected again and
measured, the rig followed the clip on every sampled frame (bone directions
0.000–0.008° at 0, 15, 30, 45, 60, 75; the root travelling with the scaled hips), so
the transfer worked and only the bake was missing — a Disconnect keeps nothing.

The fix is a step that cannot be skipped by accident: **`bake(disconnect=True)`**
calls the vendor's `asMoCapMatcherBake` (it reads the holder, not its window) with
the playback range set to the connected source's keys for the length of the bake
and put back — a range left at 0..100 over a 0..75 clip would otherwise bake 25
frames of nothing — then the vendor's Disconnect. The holder remembers the source
root (`pmrtSourceRoot`) for that. `connect()` now ends by saying so, and
`disconnect()`'s docstring says what it does not keep. Gate 12 of the verify goes
through `bake()` and asserts the baked span is the clip's (0..20) with the range
back at 0..100.

## One button for both rigs

«В случае с manny_rig_02 я просто выделяю скелет, нажимаю на скрипт и ретаргет
готов. Точно так же я хочу и для Lugal_Rig_01.» The animator's shelf button
(`shelfButton9`, on the SkeldarAnim shelf, made by dragging the Script Editor
snippet) ran `maya_asretarget.connect()` — on the Lugal rig that module refuses,
since the bones it maps are UE's. `maya_rig_retarget.py` is the dispatcher: it reads
the constrained game skeleton under the rig, UE names go to `maya_asretarget`,
PlayerMale names to `maya_pmretarget`, anything else is refused by name; `report`,
`connect`, `bake`, `disconnect` are forwarded and prefixed with the module's name.
`maya_asretarget` gained the same `bake()` so the pair of buttons means the same on
both scenes: **RTG** (`shelfButton9`, connect — the rig follows the selected
skeleton) and **BAKE** (`shelfButton32`, the vendor's Bake over the clip's keys,
then Disconnect). Both were rewired live and the shelves saved
(`saveAllShelves`). Stated risk: the SkeldarAnim shelf is rebuilt by the installer
on a re-drag, and these two buttons are not in its payload — they belong on the
Custom shelf.

## Not done, deliberately

- No neck knobs (this rig has no in-between) and no twist handling (no twist joints).
- IK end positions never come from the source. If a take's contact points matter
  more than its angles, that is a different retarget.
- The UE4 template was not exercised live (no UE4 clip in the scene); its rows and
  detection are unit-tested, its rest pose read off the shipped fbx.
