# The Hunter: clean skeleton, A-pose bind, an AdvancedSkeleton rig, a rotation-only retarget

2026-09-24. Scene: `C:/Users/MY PC/Downloads/creep_T-pose_MIX_06_skin.mb` (the animator's,
unsaved at the end of the day). The character is a creature ("Hunter"; its group was
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

## 3. The rig — `docs/superpowers/plans/as_hanter_rig_procedure.py`

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
  Hunter is 0.045 cm asymmetric, a `-mo` point constraint keeps that offset in the bone's
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

Proof: `verify_advancedskeleton_hunter_rig.py` — **0 of 25 gates failed, live 2026-09-24**.
Three gates of the Manny script measured the wrong quantity on this skeleton and were
rewritten, not loosened: the forearm twist (the Hunter's twist joints REST turned 26.7° and
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

Proof: `verify_hunter_rotation_retarget.py` in **mayapy standalone** on a saved copy of the
rigged scene with `AS_am_LongS_OxGuardR_AttackDownLeft_OxGuardL.FBX` (72 frames, 164 joints)
— **0 of 10 gates failed**: every non-limb bone on the source's world orientation to
0.001°, the Hunter's bone lengths unchanged on every sampled frame (0.000000 cm) while the
source's own differ (lowerarm 27.25 vs 35.98), root and pelvis 0.000000 cm, IK against FK
0.001 cm, nothing of the retarget left standing.

**Upperarm / lowerarm / thigh / calf are compared by where they POINT, not by roll:**
AdvancedSkeleton's Shoulder/Elbow/Hip/Knee do not roll about their own bone — the roll goes
to the twist (Part) joints (up to 94.9° on this clip), as on the Manny rig. And AS removes
the roll about ITS joint's axis, so a child standing off the bone's X (the Hunter's
lowerarm: 0.32 cm, 0.53°) swings on a cone; the joint-to-joint direction is therefore
bounded by twice each skeleton's own off-axis angle (1.07° on upperarm_r), measured from
the children's local translations. Worst excess over that bound: 0.038°.

**The hand helpers, the animator's layout** (asked after the first build): `ik_hand_r` and
`ik_hand_l` stand EXACTLY on their hands (0.000000 cm, ≤ 0.000003°) and follow them with no
offset; `ik_hand_gun`, their parent, is not driven and its channels are zero
(`place_ik_helpers`). The T-pose file had all three where a Manny's hands would be, 15–55 cm
off the Hunter's. They are skin influences of zero weight; their bindPreMatrix is
re-expressed anyway and bindPose1 reset. `ik_foot_*` already stood on the feet (0.0007 cm)
and follow them as before.

Not built: a catalog row for the Hunter rig in Add Character; the IK toes keep their bone's
frame.
