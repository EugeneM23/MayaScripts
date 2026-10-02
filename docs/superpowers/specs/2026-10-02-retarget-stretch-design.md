# Two retargets - rotations and squash & stretch - and which one runs (2026-10-02)

## The ask

The animator, away for two hours («сделать самостоятельно от начала и до конца ... пушить и
делать сборку не нужно пока я не проверю»), task 2:

> «Нужно проработать ретаргеты для наших ригов во первых у нас должно быть две версии ретаргета в
> первой где мы делаем ретаргет но гарантируем что кости не растягиваются, то есть переносим в
> основном вращения костей. Вторая версия где у нас учитывается растяжение костей. Наш скрипт должен
> определить какую ретаргет систему стоит использовать и если перенос анимации на риг или скелет
> будет ломать пропорции то необходимо спросить у пользователя согласен ли он на сквош и стрейч
> костей.»

Built in parallel with four other sessions (sources, conventions, groups, labels); this one is
"stretch". Every decision below was taken alone and is recorded as such.

## What was there

- `maya_asretarget` already had two behaviours, chosen by the rig, not by the clip: a UE5 source
  (schema `twin`) drives every FK control in position AND rotation (a parentConstraint holding our
  rest offset - the 2026-09-05 Longsword fix: «мне важно чтобы мой ретаргет всегда имел 100%
  точность»); a rig marked `skeldarRetarget = "rotation"` (the Creep, the Orc D) takes rotations
  only, IK ends and poles following the rig's own FKX. Mixamo onto an unmarked rig: FK rotation
  only, IK ends on the source's positions.
- `maya_pmretarget` (PlayerMale): rotations only, travel scaled by pelvis height.
- `skeletonimport.transfer` (the bridge's Skeleton mode): a twin (median bone within 1 %) whole,
  any other body by orientation (root and pelvis placed).

## Measured first

`docs/superpowers/plans/verify_retarget_modes.py`'s probe, LongSword_Attack_Right_Heavy_3P (a UE5
3P clip, 0..60) against the three shipped rigs added into an empty mayapy scene:

| target | median bone off | s (legs) | regions the stretch would change |
|---|---|---|---|
| Manny_Rig | 0.0000 | 1.00001 | none (a twin) |
| Creep_Rig | 0.2424 | 1.00000 | arms -16.7 %, spine +1.4 %, fingers -29.6 % |
| Orc_D_Rig | 0.0322 | 0.99992 | arms -4.9 %, spine +1.8 %, fingers -9.2 % |
| Manny_Rig vs Sweep Fall (Mixamo) | 0.204 | 0.946 | arms -9.4 %, spine -30.4 %, neck -23.6 %, fingers +11.3 % |

The clip's own stretch: spine_04 varies 0.124 cm over the take (the 3P clip slides its spine; the
pelvis "length" - its offset from the root - is the root motion, 52 cm, and is not a length).

Two facts that changed the design, both now traps:

1. **The joints' own `.bindPose` attribute is stale on Manny_Rig**: parent-child distances read
   from it differ from the bind by up to **3.5 cm**. The rest lengths come from each skinCluster's
   `bindPreMatrix` (its inverse is the joint's world matrix at the bind), the current world matrix
   only for an unskinned joint. A rig carrying a stretched take still answers its own lengths.
2. **The Creep's and the Orc D's game bones take ORIENTATION ONLY from AdvancedSkeleton** (their
   procedure's design, 2026-09-24: «Bones take ORIENTATION only ... lengths exact, no translation
   keys below the pelvis»). The first stretch run put every FK control on the clip's joints and the
   exported bones did not move at all: lengths changed **0.0 %** against an asked -16.7 %, a
   fingertip **18.6 cm** off the clip's. The AS deformation joints stand ON the game bones
   (0.0000 cm, the Creep's gate 26), so the stretch needs the game bones to follow their position.

## The design

### Two versions, one setting, one rule - `SkeldarAnim/maya_retargetmode.py`

Stdlib at import (a subprocess test pins it); the scene wrappers import `maya.cmds` inside.

- **ROTATIONS** («кости не растягиваются»): every bone turns as the clip's (aligned rests as
  before) and keeps the target's own length; root and pelvis placed. On a rotation-marked rig:
  `drive_plan(rotation=True)`, IK ends and poles following the rig's own FK; on any other rig
  (since the fix pass, addendum 1) the legacy plan with no FK position, IK ends on the clip's.
  On a skeleton: orient for every bone, orient + point for root and pelvis, a twin included.
- **STRETCH** («учитывается растяжение»): every bone lands on the clip's joint, the clip taken at
  OUR size - `s` = our leg chains over the clip's (pose-independent: a clip's rest pose is never
  visible in an animated clip, its legs' lengths are; legs therefore always read 0 % after the size
  is taken out) - so the target's lengths become the clip's, the clip's own animated stretch
  included. **The twin path IS the stretch for a twin and is unchanged** (bones_mode "twin":
  `drive_plan` as before, gate a4: Manny_Rig against a legacy-connected Manny_Rig1 **0.0 cm** on
  every bone and frame). For another body the source drives ride **scaled followers**.
- **The setting**: optionVar `skeldarRetargetBones` = `auto` (default) | `rotation` | `stretch`.
- **The rule** (`decide`, pure): Rotations / Stretch forced - that, never asked. Auto: a twin
  (unscaled median ≤ 1 %) - stretch, exact; the same proportions at another size (scaled median ≤
  1 %) - stretch, the clip at our size; otherwise the stretch would break our proportions - ASK,
  default rotations; with no one to ask (`cmds.about(batch=True)` and no answerer) rotations, and
  the status line says so («...; no one to ask here»).
- **Measured, by the retarget's own map** (`segments`, pure): each paired bone with its nearest
  PAIRED ancestor on our side, kept only when the clip's counterpart of that anchor is an ancestor
  of the clip's bone too - so Mixamo's 3-joint spine against our 5 compares chord with chord. Root,
  pelvis, `ik_*`, `weapon_*`, `camera_*`, `center_of_mass`, `interaction` are not lengths. Regions
  by OUR bone's name (arms, legs, spine, neck, fingers) - UE, PlayerMale and Mixamo names all land.
- **The question** (`question`, one `confirmDialog`): «Heavy onto Creep_Rig: its bones are not
  Creep_Rig's. / Squash & stretch would change Creep_Rig's proportions: arms -17 %, spine +1 %,
  fingers -30 %. / The clip itself stretches spine_04 0.1 cm.» Buttons **Keep proportions**
  (default), **Squash & stretch**, **Cancel**. The clip is named by its namespace (the bridge names
  it after the animation, `clip_name`).
- **The status line always says which ran and why** («rotations - Creep_Rig keeps its proportions
  (arms -17 %, spine +1 %, fingers -30 %)», «stretch - Manny_Rig is the clip's twin, exact»,
  «stretch - Creep_Rig squashed & stretched to the clip (...)»).
- An answerer can be installed (`set_asker`) - how the verify answers, and counts, the questions.

### The scaled follower - `scale_space` / `scaled_follower`

Transforms and plain connections only, so everything dies with its parent (the holder):

```
space  (under the holder) rides the clip root's PARENT rigidly (parentConstraint -mo, so the
       bridge's wrapper - moved and turned onto the rig's place AFTER the connect - carries the
       move 1:1 and only the body is scaled); the world when the root has no parent
  follow  point + orient constrained to the joint: its channels ARE the joint in the space
  scaled  (scale s) > body (translate/rotate connected from follow) > unit (scale 1/s)
```

`unit` stands at the joint's position times s in the space, turned as the joint, scale 1.

### On the AdvancedSkeleton rigs - `maya_asretarget`

- `connect(..., bones=None)`: None is the legacy rule (the rig's mark) - every older caller and
  verify keeps it; "rotation" / "stretch" are the versions. `_plan(..., bones_mode)` measures the
  clip for "stretch": a measured twin on a twin schema is the old twin path, anything else is
  `drive_plan(scaled=True)` - the rotation plan whose FK controls take position too, Main and
  RootX_M included - every source drive's target swapped for its scaled follower and the offset read
  exactly as the twin path reads it (against our own bone). IK ends and poles follow the rig's FK.
- **`position_follow(rig, on)`**: a stretch press gives every game bone driven by ONE
  orientConstraint and nothing that moves it (not the pelvis, not twist bones - the AS Part joints
  stand up to 0.17 cm off the Creep's twists - not the helpers) a point constraint from its AS
  joint with no offset, marked `skeldarStretchFollow`; a rotations press takes them away (the
  rotations export keeps exact lengths and no translation below the pelvis). Found by the marker,
  never by name. They are not registered on the holder: they belong to the take, not the connect.
  Manny's bones already have AS's point constraints; nothing is added there.
- The holder remembers the version (`skeldarRetargetBones`: "rotation" / "stretch" / "twin");
  `connected_mode`. `maya_rig_retarget.helper_space` reads it: the helper bones (weapon, camera)
  carry in world space only for the twin's exact stretch, relative to their parent otherwise.
- `measure(source_root, rig)` (read-only) and `pairs_of`.

### PlayerMale - `maya_pmretarget`

`connect(bones=...)`: "stretch" adds a point constraint from a scaled follower (the module's own
travel scale, `plan.scale`, so the limbs and the travel agree) to every FK control; the game bones
already follow AS's point constraints. `measure`, `pairs_of`, `connected_mode`.

### The presses

- **The Retarget button** (`maya_rig_retarget.run_retarget(..., bones=None)`): the decision is taken
  BEFORE the reset (`decide_for`), so a Cancel («cancelled - nothing changed») leaves the rig and
  its take exactly as they were. A holder already standing is baked, unasked.
- **The bridge onto a rig** (`rigimport.import_and_retarget`): the order changed - for a rig in the
  scene the clip is imported first, the question asked, THEN the rig's take reset (a Cancel removes
  the clip's namespace and touches nothing else); an added rig is added first (what the clip is
  measured against) and deleted again on Cancel (`discard_added`, Characters' own Delete). A posed
  rig's refusal now comes after the import and removes the clip's namespace.
  `retarget_imported(..., bones=)`.
- **Onto a skeleton** (`skeletonimport.onto_skeleton(..., decide=)`, `onto_existing(..., decide=)`):
  `decide=None` is the legacy transfer; `import_onto_skeleton` / `import_onto_existing` pass
  `choose_for`. Cancel deletes a skeleton the press added (`discard_new`) and the clip's namespace.
  `transfer(..., mode=, scale=)`, `drive_for(..., mode)`: rotation never whole (a twin too),
  stretch whole for a twin and `orient+scaled` for another body.
- **A batch** (`lineimport.run`, `_Versions`): measured against the FIRST target the batch adds
  (every target of a batch is the same catalog row), every clip at once, asked ONCE with the worst
  named («The answer goes for all 2 animations that differ»), the answer for every clip that would
  ask, a twin exact. By UUID: the clip being placed is wrapped before it is asked about. Cancel
  deletes the target just added and every clip skeleton of the batch. The summary line ends with the
  distinct reasons.
- **The setting is shown in the Retarget card only** (`maya_rig_retarget._bones_row`:
  `[Auto | Rotations | Stretch]`, hubstyle segments, tooltips): the Animation Setup card's import
  rows are the "sources" session's work this same day, and one setting serves every press - the
  bridge reads it too.

## Decided alone

1. The size `s` is the legs' ratio, not the pelvis height (not observable in a clip).
2. "Proportions break" = the SCALED median > 1 %: a clip at another size with our proportions is
   stretched without asking.
3. A twin answers stretch (exact) and is never asked - the old twin path.
4. Rotations on a twin (forced) drops the clip's own animated stretch: lengths kept.
5. The legacy call (`bones=None`) keeps every module's old behaviour; only the presses decide.
6. Measure our rest lengths from `bindPreMatrix`, never the joints' `.bindPose` (stale).
7. The position follow on the rotation-only rigs is added by a stretch press and removed by a
   rotations press - not shipped in the assets.
8. In stretch the IK limbs still follow the rig's FK and reach with the rig's own lengths; the FK
   chain carries the stretch. Since the fix pass the question and the status line SAY it. Measured: the Orc D's ball 0.56 cm off in IK (its foot is not the
   clip's), 0.0002 cm in FK; the Creep 0.0097 / 0.0001.
9. The batch is asked once; twins in it stay exact whatever the answer.
10. The setting lives in the Retarget card only (above).
11. Cancel after an import deletes what the press imported and added; the scene's UUIDs are back
    (gate g: 0 nodes left, the rig's 190 curves and 11590 keys untouched).
12. PlayerMale stretch scales by the module's travel scale (pelvis height), not the legs, so limbs
    and travel agree.

## Proof

`docs/superpowers/plans/verify_retarget_modes.py PLUGIN [a,b,c,d,e,f,g]` - mayapy STANDALONE,
empty scenes, the clips on disk, the question answered by an injected answerer that counts:

- **a** (Manny_Rig, the UE5 3P clip, the Retarget button): measured a twin (median 0.00000, s
  1.00001, 59 lengths); Auto: stretch, **0 questions**; every bone on the clip's: worst
  **0.0723 cm** (calf_l, the rig's own left-leg fit, CLAUDE.md's 0.06-0.08), **0.0016°**; against
  the legacy connect on a second Manny **0.0 cm** on every bone and frame.
- **b** (Creep_Rig, Orc_D_Rig): Auto asks **once** each, naming the rig and the regions.
  Rotations: lengths kept to **5.9e-14 cm** (Creep) / **1.9e-5 cm** (Orc), orientations on the
  clip's to **0.0013°**, limb directions 0.53° / 0.07° (AS's limbs do not roll); positions off by
  the proportions (18.6 / 4.9 cm). Squash & stretch, the limbs shown in FK: every paired bone on
  the clip's joint to **0.0001 cm** (Creep) / **0.0002 cm** (Orc), turned to 0.0012°; as the rig
  stands (legs in IK) 0.0097 / 0.56 cm; the lengths changed by the measured difference (arms
  -16.7 % asked -16.7 %; the Orc's arms read 0.9 points short because its shoulder-pad joints
  `AB_Armor_Shoulder_*` count as arm bones in the verify's sum and are not stretched). 62 game bones
  got a position follow; Rotations on the same rig took them away (0 left), lengths back to the
  bind to 5.2e-10 / 1.9e-5.
- **c** (skeletons): Manny UE5 [skeleton] - a twin, nothing asked, every bone on the clip's
  **8.9e-4 cm**, **9.4e-4°**; Creep [skeleton] Keep - asked once, lengths **5.6e-14 cm**,
  orientations 0.00095°; Squash - asked once, every bone on the clip's joint **7.2e-14 cm**.
- **d** (the PlayerMale / Lugal rig, opened read-only from the animator's backup
  `Lugal_Rig_01_left_arm_fixed_20260906_0058.mb` with `executeScriptNodes=False`, never saved):
  Keep - asked once, lengths kept to 6.0e-4 units (the vendor's -mo point constraints on that rig);
  Squash (limbs in FK) - every FK-driven game bone on the clip's joint at x0.1169 to
  **0.0007 units**.
- **e** (Sweep Fall, Mixamo, onto Manny_Rig - another size and aligned rests): measured median
  0.20 off, s **0.946**, asked once. Keep - lengths kept to 0.059 cm (foot_l: Manny's own left-leg
  fit, FKKnee_L 0.0637 cm off calf_l, wandering with the knee's roll through the vendor's -mo point
  constraints - this rig's floor, gated at 0.1); Squash, limbs in FK - every paired bone on the
  clip's joint at x0.946 to **0.0637 cm** (calf_l, the same fit). Note: Mixamo onto Manny in
  ROTATIONS now drives the IK ends from the rig's own FK, where the legacy call put them on the
  clip's positions (`connect()` without `bones` still does).
- **f** (a batch of three clips onto Creep skeletons): **1 question** for 3 clips, every skeleton's
  lengths kept to 8.0e-14 cm, the line saying it.
- **g** (Cancel): the Retarget button - «cancelled - nothing changed», the rig's 190 curves and
  11590 keys as they were, **+0 nodes**; a bridge import onto a new Creep - 0 nodes left, 1 rig,
  namespaces as they were; a batch of two onto new Creeps - one question, 0 nodes left.

The existing proofs, run standalone against this worktree (`run_verify.py` rewrote the main
checkout's paths): `verify_rig_pipeline.py` **0 of 30 failed**, `verify_many_rigs.py` **0 of 32**,
`verify_creep_rig_asset.py` **0 of 16**, `verify_orc_d_rig_asset.py` **0 of 22**,
`verify_weapon_space.py` **0 of 11**. Unit tests: **3562, OK** (55 new: `test_retargetmode.py`,
`test_retarget_versions.py`). The whole verify, all seven phases in one run: **31 of 31 gates** (before the fix pass; after it **39 of 39** over eight phases - the addendum).

Not proven: the dialog itself in a GUI Maya (the answerer stands in for it; `confirmDialog` with
those buttons is Maya's own); a real Mixamo clip onto a Creep (the conventions session's mapping
makes it reachable); the Animation Setup card carrying the setting.

## Addendum: the fix pass (the same day, an independent review)

Eight findings, each confirmed by reading the code and measured where it was cheap; seven fixed,
one (the IK limbs) answered by saying it rather than changing the rig's mode.

1. **Rotations broke Manny's legacy Mixamo road** (confirmed). `ROTATION` forced
   `rotation=True` for every rig, so «Keep proportions» (and Auto in a batch) put Manny's IK ends
   on the rig's own FKX instead of the clip's hands and feet; `verify_asretarget_mixamo.py` calls
   `connect()` without `bones` and could not see it. Now `rotation` is the rig's MARK
   (`rotation_mode`); an unmarked rig in Rotations runs the legacy plan with
   `drive_plan(keep_lengths=True)`: FK by angle and NO position, a twin's neither, IK ends and
   poles on the clip's own bones. Measured first: **`stretchy` is 0 on the IK arms and legs of
   Manny_Rig and Creep_Rig** (and Lenght1/2 1.0), so an IK limb bends and never stretches - the
   lengths are kept and the feet stand on the clip's footprints. The connect's line says
   «ROTATIONS (every bone its own length, the IK hands and feet on the clip's)», the note
   `keep_note`. Gate e-keep-ik.
2. **The PlayerMale's stretch tore the body when the clip moved after the connect** (confirmed).
   Its FK followers rode `retargetmode.scale_space` (a rigid copy of the clip's top node) while
   Main and RootX_M rode pm's own `_scale_group` (world positions times s, about the origin, plus
   the rest offset). Now the FK followers ride pm's `_scaled_follower` with the pelvis drive's world
   offset (`stretch_offset`): ONE frame, so the body is the clip's scaled shape about its pelvis
   whatever moves. Not changed: pm's legacy travel itself scales about the world origin, so a clip
   moved after the connect moves Main s times as far - that was so before this task and is noted,
   not fixed (no PlayerMale row ships). Gate d-frame.
3. **Stretch did not do what the dialog said for a limb in IK** (confirmed; the Creep's and the Orc
   D's legs default to IK). Driving AS's IK `stretchy` / `Lenght1/2` would stretch an IK limb only
   outward and only to a constant ratio, and switching the blends would change the animator's rig
   mode unasked - so it is SAID instead: the question («a limb in IK keeps its own lengths, its end
   following the FK (switch it to FK to see the clip's)») and the connect's first line, which the
   button's status carries («SQUASH & STRETCH - leg_l, leg_r in IK keep their own lengths, their
   ends following the FK - switch them to FK to see the clip's»; `ik_limbs`, `stretch_ik_note`, the
   same in pm). Gate b4 now measures the promise AS THE RIG STANDS: every bone outside the IK limbs
   on the clip's joint, the IK limbs' lengths kept, their ends on the clip's to a centimetre, the
   line naming them; the FK-switched measurement stays as b4fk.
4. **A Cancel left the scene's time changed** (confirmed and measured in mayapy, trap 162?):
   FBXImport of a 30 fps clip into a film scene switches it to ntsc AND RESCALES the keys already
   there (a key at 24 lands on 30), sets the playback and animation ranges to the clip's and the
   current time to its first frame. `rigimport.time_state` / `restore_time`: the unit back with
   `updateAnimation` (the keys return to 24), then the ranges and the frame in the old unit's
   frames. Every Cancel after an import restores it (the bridge onto a rig, onto a skeleton, onto
   one standing, a batch). Gates g2, g3 (a film scene with keys at 24/48, ranges 5-40 / 0-50,
   frame 7).
5. **The clip was scaled about its space's origin** (confirmed): every place the bridge computes
   is measured from the UNSCALED root at its first frame, so a root starting away from the origin
   put the stretched body (1 - s) of that distance off. `scale_space` sets the scaled group's
   `scalePivot` to the root's first-frame floor point (x, 0, z) in the space (`root_start`,
   `floor_pivot`, `to_local`). A scaled clip top node now also leaves the followers at world scale
   1 (`scaled_follower` cancels the body's whole world scale, not just s). Gate h1: a clip under a
   group turned 30° and scaled 0.8 (s = 1.25), its root's own keys moved (150, -80) off the group's
   origin - the stretched game root starts on it to **0.0000 cm**; the pre-fix code, run as a
   control from a `git archive` of 614ec05, put it **33.78 cm** away. h2-h4: the body intact (the
   clip's spans times s to 0.0000), a bridge import onto a Creep standing at (120, -60) turned 30°
   (Main on the place to 0.0002 cm, facing 30.0000°), a Skeleton-mode drop point (0.0000 - not
   discriminating: the Creep skeleton's s is 1.0000 against a UE clip, the old code passes it too).
6. **Gate b6's "no follow left" could not fail** (confirmed): Maya names a pointConstraint in the
   ROOT namespace (`b_pointConstraint1` for `Creep_Rig:b`), so a namespace-prefix filter on short
   names found nothing whatever happened. The follows are found by their attribute under the rig's
   skeleton.
7. **A removed follow left the bone at the DG's last evaluation** (confirmed by reading; trap 58's
   mechanism). The follow now remembers the bone's own translate (`skeldarStretchRest`, double3)
   and Rotations writes it back after deleting it (a follow from before the fix pass: the
   bind-local translate from `bindPreMatrix`). Gate b6: the translates back to **0.0**.
8. **The skeleton transfer judged "twin" again by its own rule** (confirmed): the decision came from
   `measure` (nearest paired ancestor, at the bind), `transfer` re-ran `is_twin` (DAG parent, as the
   target stands) - the line could name one version while the other ran. `Decision` carries the
   measure's `twin` (a fourth field, default None) and `transfer(twin=)` runs on it.

Fix-pass proof: `verify_retarget_modes.py` - see the CLAUDE.md draft below for the numbers;
`test_retarget_fixpass.py` (18 tests, the pure halves). **Positive control**: the new gates run
against the pre-fix plugin (`git archive 614ec05`) fail where they should - d-squash **0.267
units** (the PlayerMale's FK off its pelvis by the rest offset), d-frame **31.99 units** ((1 - s) of
the 36-unit move), h1 **33.78 cm**. Decided alone in the fix pass: 1 keeps the legacy
road rather than announcing a change; 3 says it rather than flipping blends or driving AS's IK
stretch; 2 leaves pm's legacy origin-scaled travel alone.

## CLAUDE.md section (draft)

## Two retargets: rotations, or squash & stretch - and which one runs (2026-10-02)

The animator: «у нас должно быть две версии ретаргета в первой где мы делаем ретаргет но
гарантируем что кости не растягиваются ... Вторая версия где у нас учитывается растяжение костей.
Наш скрипт должен определить какую ретаргет систему стоит использовать и если перенос анимации на
риг или скелет будет ломать пропорции то необходимо спросить у пользователя согласен ли он на сквош
и стрейч костей.» Away for two hours: every choice taken alone, in the spec
`docs/superpowers/specs/2026-10-02-retarget-stretch-design.md`.

**`SkeldarAnim/maya_retargetmode.py`** (stdlib at import, a payload row; its scene wrappers import
`cmds` inside) holds the measurement, the rule, the question and the scaled followers; the retarget
modules build their own drives.

- **ROTATIONS**: every bone turns as the clip's and keeps the target's length; root and pelvis
  placed; on a rotation-marked rig (the Creep, the Orc D) the IK ends and poles follow the rig's
  own FK, on any other (Manny) they stay on the clip's hands and feet - the legacy plan with no FK
  position (`drive_plan(keep_lengths=True)`): an AS IK limb has `stretchy` 0 on every shipped rig,
  it bends and never stretches. **STRETCH**: every bone on the clip's joint,
  the clip taken at OUR size (`s` = our legs over the clip's; a clip's rest is never visible, its
  legs are) - the target's lengths become the clip's, its animated stretch included. **The twin's
  stretch IS the old twin path**, unchanged to **0.0 cm** (a Manny retargeted with the new press
  against one with the legacy call, every bone, every frame).
- **The setting** `skeldarRetargetBones` = auto (default) | rotation | stretch, as `[Auto | Rotations
  | Stretch]` segments in the **Retarget card** (only there: one setting for every press, and the
  Animation Setup import rows were another session's that day). **Auto**: a twin (median paired
  bone ≤ 1 %) - stretch, exact, never asked; the same proportions at another size (the scaled
  median ≤ 1 %) - stretch; anything else - one `confirmDialog` («Heavy onto Creep_Rig: ... Squash &
  stretch would change Creep_Rig's proportions: arms -17 %, spine +1 %, fingers -30 %.» - and «a
  limb in IK keeps its own lengths, its end following the FK»; **Keep proportions** (default) /
  **Squash & stretch** / **Cancel**); batch mode: rotations, said so. The status line always names
  the version and why, and a stretch's names the limbs in IK («SQUASH & STRETCH - leg_l, leg_r in
  IK keep their own lengths ...»). `set_asker` installs an answerer (the verify).
- **Lengths by the retarget's own map**: each paired bone against its nearest PAIRED ancestor (a
  3-joint Mixamo spine against our 5 compares chord with chord); root, pelvis and the helpers are
  not lengths; regions by our bone's name. Ours from the skinCluster's `bindPreMatrix` (trap 159?),
  the clip's at its first frame.
- **Scaled followers**: under the holder, a space riding the clip root's PARENT rigidly (the
  bridge's wrapper is moved onto the rig's place after the connect: the move rides 1:1), a follow
  point+orient-constrained to the joint, its channels connected into a node under a group scaled s
  **about the clip root's first-frame floor point** (`scalePivot`, trap 163?), a child cancelling
  the body's whole world scale - at the joint times s, turned as it, scale 1. Transforms and
  connections only.
- `maya_asretarget.connect(bones=None|"rotation"|"stretch")` (None the legacy rule every older
  caller keeps): stretch onto another body is `drive_plan(scaled=True)` - the rotation plan whose FK
  controls (and Main, RootX_M) take position from the followers with the twin path's own offsets.
  **The Creep's and the Orc D's game bones follow AS by orientation only** (trap 160?): a stretch
  press gives each such bone a point constraint from its AS joint (marked `skeldarStretchFollow`, no
  offset - the joint stands on the bone, its own translate kept on it as `skeldarStretchRest`), a
  rotations press takes them away and writes that translate back (trap 58's mechanism). The holder
  remembers the version (`connected_mode`); the helper bones carry in world space only for the
  twin. `maya_pmretarget.connect(bones=)`: stretch puts every FK control on the clip's joint in the
  frame Main and the pelvis ride - pm's own scaled group, plus the pelvis's rest offset - so the body
  is the clip's shape about its pelvis whatever moves the clip after the connect.
- **Every press decides before anything changes**: the Retarget button before the reset; the
  bridge onto a rig imports the clip FIRST, asks, then resets (Cancel removes the clip; an added rig
  is deleted again); onto a skeleton (`onto_skeleton` / `onto_existing(decide=)`; Cancel deletes the
  added skeleton and the clip); a batch (`lineimport._Versions`) measures every clip against the
  first target it adds and asks ONCE, the worst named, by UUID (trap 161?). «cancelled - nothing
  changed» - and it is: every Cancel after an import puts the scene's time unit (with its keys),
  ranges and frame back (`rigimport.time_state` / `restore_time`, trap 162?). The skeleton transfer
  runs on the twin verdict the press decided on (`Decision.twin`), never its own second opinion.

Proof: `docs/superpowers/plans/verify_retarget_modes.py` **39 of 39 gates standalone** after the
review's fix pass (phases a-h; numbers in the spec): Manny a twin, 0 questions, every bone on the
clip's 0.072 cm (its left-leg fit), the legacy path to 0.0; Creep_Rig / Orc_D_Rig asked once each,
Keep - lengths kept 5.9e-14 / 1.9e-5 cm, orientations 0.0013°; Squash AS THE RIG STANDS - every bone
outside the IK legs on the clip's joint 0.0001 / 0.0002 cm, the IK legs' lengths kept (3.9e-10 /
1.6e-6) with their ends 0.0002 cm off the clip's, the line naming them; the lengths changed by the
measured -16.7 % / -4.9 %; Rotations on the same rig took the 62 follows away and wrote every
translate back to 0.0; skeletons Manny exact 8.9e-4 cm unasked, Creep Keep 5.6e-14 / Squash
7.2e-14; the Lugal rig opened read-only - Keep 6e-4 units, Squash 0.0007 units at x0.117 about its
pelvis, and 0.0007 again with the clip moved 36 units and turned 25° AFTER the connect; a Mixamo
clip onto Manny - Keep IS the legacy plan (a second Manny retargeted by the legacy call 0.0 cm,
limbs in FK and in IK), Squash 0.064 cm; a batch of 3 asked once; Cancel - 0 nodes left, the rig's
190 curves and 11590 keys untouched, and in a film scene with keys at 24/48 the unit, the keys, the
ranges 5-40 / 0-50 and frame 7 all back; a clip under a group turned 30° and scaled 0.8 (x1.25),
its root's keys moved (150, -80) off the group's origin: the stretched game root starts ON it to
0.0000 cm, where the pre-fix code put it 33.78 cm away (the positive control: the pre-fix plugin
fails d-squash 0.267 units, d-frame 31.99, h1 33.78);
`verify_rig_pipeline.py` 30/30, `verify_many_rigs.py` 32/32, `verify_creep_rig_asset.py` 16/16 after
the fix pass. 3580 unit tests.

159?. **A joint's own `.bindPose` attribute can be stale by centimetres**: on Manny_Rig's game
      skeleton parent-child distances read from it differed from the bind by up to 3.5 cm, so a
      rest length read there would call a twin "not a twin". The skinCluster's `bindPreMatrix` is
      the bind the mesh uses (its inverse is the joint's world matrix at bind); read that.
160?. **A rotation-only rig's game bones ignore a control's translation.** The Creep's and the Orc
      D's bones take ORIENTATION ONLY from their AS joints (lengths exact by design), so the first
      squash & stretch put every FK control on the clip's joints and the exported skeleton did not
      move: lengths 0.0 % against an asked -16.7 %, a fingertip 18.6 cm off. Every control gate
      would have passed; only measuring the GAME bones caught it.
162?. **An FBX import changes the scene's time, and a Cancel has to change it back.** Measured in
      mayapy: FBXImport of a 30 fps clip into a film scene (FBXImportSetMayaFrameRate off) switches
      it to ntsc AND RESCALES the keys already there - a key at 24 lands on 30 - and puts the
      playback and animation ranges on the clip's and the time on its first frame. `currentUnit
      -time film -updateAnimation true` takes the keys back to 24; the ranges and the frame are
      then set in the old unit's frames. A Cancel that only deleted the imported nodes left all four
      changed, and every node-counting gate passed.
163?. **A body scaled about its space's ORIGIN stands (1 - s) of its start away from where the
      bridge put it** - every place (`place_moves`, a drop point, a skeleton's own place) is
      measured from the UNSCALED root at its first frame. Scale about the root's first-frame floor
      point (`scalePivot`). Two verify lessons from proving it: the Creep's legs equal a UE clip's,
      so s = 1.0000 and no pivot can show - scale the clip's group to make s 1.25; and `cmds.parent`
      KEEPS the world position, so moving a group and then parenting the clip under it moves
      nothing (the gate read a root at (0, 0) and could not fail) - parent first, then move.
164?. **Maya names a constraint in the ROOT namespace**: `pointConstraint` on `Creep_Rig:b` makes
      `b_pointConstraint1`, so a gate filtering constraints by a namespace prefix on short names
      finds nothing whatever happened - "no follow left" could not fail. Find our nodes by their
      attribute under the rig's skeleton.
161?. **A batch that measures every clip when the first is placed reads the first clip at a stale
      path**: `onto_skeleton` wraps the clip's root (re-parents it) before it asks, and the other
      clips' recorded paths were fine while the first one's was `|Heavy:root` - «No object matches
      name» three times, every clip failed. Keep clips by UUID across anything that re-parents
      (trap 16 again).
