"""Live gates for the Mixamo half of maya_asretarget.

Send through the command-port bridge into the animator's OPEN scene, the one
holding the AdvancedSkeleton rig and a Mixamo skeleton with a clip on it.

Unlike `verify_asretarget.py` this builds NO fixture: the source is the
animator's own Mixamo skeleton, read-only. What it does write -- the
constraints, the baked keys of the bake gate -- it removes again, and it leaves
the rig at its bind pose with autoKey, the playback range, the frame, the
FKIK blends and the selection as it found them.

The gate that matters is 6: a rotation retarget is correct exactly when our
bone POINTS where the source's bone points, at every frame. The rest-pose
alignment is what makes that possible across a T-pose source and an A-pose rig.

Spec: docs/superpowers/specs/2026-09-05-asretarget-mixamo-design.md
"""
import math
import sys

import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"   # the retarget modules live in the plugin since 2026-09-07
AS_MEL = "C:/Users/MY PC/Downloads/AdvancedSkeleton/AdvancedSkeleton.mel"
BAKE = True                      # the bake gate costs ~76 frames x 70 controls

if REPO not in sys.path:
    sys.path.insert(0, REPO)
sys.modules.pop("maya_asretarget", None)
import maya_asretarget as ar     # noqa: E402

# bone pairs to measure, ours <- the source's, with the child that gives the
# direction on each side
CHECK = [("upperarm_l", "lowerarm_l", "LeftArm", "LeftForeArm"),
         ("lowerarm_l", "hand_l", "LeftForeArm", "LeftHand"),
         ("upperarm_r", "lowerarm_r", "RightArm", "RightForeArm"),
         ("lowerarm_r", "hand_r", "RightForeArm", "RightHand"),
         ("clavicle_l", "upperarm_l", "LeftShoulder", "LeftArm"),
         ("clavicle_r", "upperarm_r", "RightShoulder", "RightArm"),
         ("thigh_l", "calf_l", "LeftUpLeg", "LeftLeg"),
         ("calf_l", "foot_l", "LeftLeg", "LeftFoot"),
         ("thigh_r", "calf_r", "RightUpLeg", "RightLeg"),
         ("calf_r", "foot_r", "RightLeg", "RightFoot"),
         ("foot_l", "ball_l", "LeftFoot", "LeftToeBase"),
         ("spine_01", "spine_03", "Spine", "Spine1"),
         ("spine_03", "spine_05", "Spine1", "Spine2"),
         ("spine_05", "neck_01", "Spine2", "Neck"),
         ("hand_l", "middle_01_l", "LeftHand", "LeftHandMiddle1"),
         ("index_01_l", "index_02_l", "LeftHandIndex1", "LeftHandIndex2"),
         ("index_02_l", "index_03_l", "LeftHandIndex2", "LeftHandIndex3"),
         ("thumb_01_r", "thumb_02_r", "RightHandThumb1", "RightHandThumb2")]
SAMPLES = [0.0, 12.0, 25.0, 40.0, 60.0, 75.0]

FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append((n, msg))


def wm(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def where(node):
    return om.MVector(cmds.xform(node, query=True, worldSpace=True, translation=True))


def worst(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def angle_between(u, v):
    return math.degrees(math.acos(max(-1.0, min(1.0, u.normal() * v.normal()))))


saved = {"autoKey": cmds.autoKeyframe(query=True, state=True),
         "time": cmds.currentTime(query=True),
         "sel": cmds.ls(selection=True, long=True) or [],
         "em": cmds.evaluationManager(query=True, mode=True)[0],
         "min": cmds.playbackOptions(query=True, min=True),
         "max": cmds.playbackOptions(query=True, max=True)}
blends = dict((c, cmds.getAttr(c + ".FKIKBlend"))
              for c in ("FKIKArm_L", "FKIKArm_R", "FKIKLeg_L", "FKIKLeg_R")
              if cmds.objExists(c))
# connect() sets the neck bias by default since 2026-09-05; the animator's own
# value goes back at the end
bias_saved = (cmds.getAttr("%s.%s" % ar.NECK_BIAS[:2])
              if cmds.objExists(ar.NECK_BIAS[0]) else None)
share_saved = (cmds.getAttr("%s.%s" % ar.NECK_TWIST[:2])
               if cmds.objExists(ar.NECK_TWIST[0]) else None)
controls = cmds.sets("ControlSet", query=True) or []
keyed_before = set(c for c in controls
                   if cmds.listConnections(c, type="animCurve", source=True,
                                           destination=False))
blend_nodes = set(cmds.ls(type="pairBlend") or [])
rest = {}
cmds.autoKeyframe(state=False)
cmds.evaluationManager(mode="off")
try:
    if mel.eval('whatIs "asMoCapMatcherBake"') == "Unknown":
        mel.eval('source "%s";' % AS_MEL)
    if cmds.objExists(ar.HOLDER):
        ar.disconnect()

    # ------------------------------------------------------------- the source
    mixamo = [j for j in cmds.ls(type="joint", long=True)
              if "mixamorig" in j and not cmds.listRelatives(j, parent=True, type="joint")]
    gate(1, len(mixamo) == 1, "one Mixamo root in the scene: %s" % mixamo)
    if len(mixamo) != 1:
        # every gate below reads that skeleton; stop here with a name rather
        # than an IndexError (the scene held two UE clips and no Mixamo one
        # when this first tripped, 2026-09-05)
        raise RuntimeError("this scene holds %d Mixamo skeleton(s) - import the "
                           "animator's Mixamo clip (65 joints under mixamorig:Hips) "
                           "and run again" % len(mixamo))
    source = mixamo[0]
    bones = ar.source_bones(source)
    schema, score = ar.detect_schema(list(bones))
    gate(2, schema is not None and schema.name == "mixamo" and score == 5,
         "%d bones, detected schema %s on %d of its hint bones"
         % (len(bones), schema.name if schema else None, score))

    rig = ar.rig_paths()
    ue_root = ar.rig_skeleton_root(rig)
    rig_bones = dict((ar.leaf(p), p) for p in [ue_root] + (
        cmds.listRelatives(ue_root, allDescendents=True, type="joint",
                           fullPath=True) or []))
    cmds.currentTime(0.0)
    for name, path in rig_bones.items():
        rest[name] = cmds.getAttr(path + ".worldMatrix[0]")
    gate(3, not ar.posed_controls(),
         "the rig stands at its build pose, %d bones, %d controls"
         % (len(rig_bones), len(controls)))

    # ------------------------------------------------------------ the refusals
    cmds.select(clear=True)
    msg = ar.connect()
    gate(4, "select" in msg.lower() and not cmds.objExists(ar.HOLDER),
         "connect() with nothing selected: %r" % msg)
    cmds.select(rig_bones["pelvis"])
    msg = ar.connect()
    gate(5, "rig's own" in msg and not cmds.objExists(ar.HOLDER),
         "connect() on our own skeleton: %r" % msg)

    # --------------------------------------------------------------- the plan
    cmds.select(bones["LeftArm"])
    report = ar.report()
    plan = ar._plan(source)
    print("// report():")
    for line in report.splitlines():
        print("//   " + line)
    ours = ar.our_bone_map()
    # the count is computed from the schema and the scene, never guessed: every
    # control the schema can drive, that this rig has, whose own bone is ours
    expected = [c for c in ar.candidates(plan.schema)
                if cmds.objExists(c) and ours.get(c) in rig_bones
                and not (c == "Main" and plan.schema.root_bone is None)]
    gate(6, plan.schema.name == "mixamo" and not plan.missing
         and len(plan.drives) == len(expected),
         "%d drives of the %d controls this schema can reach, nothing missing (%s)"
         % (len(plan.drives), len(expected), plan.missing[:3]))
    arm_align = ar.rotation_angle(plan.align["FKShoulder_L"])
    leg_align = ar.rotation_angle(plan.align["FKHip_L"])
    gate(7, 50.0 < arm_align < 60.0 and leg_align < 6.0,
         "rest alignment: the arm needs %.2f deg (T-pose against our A-pose), the "
         "thigh only %.2f" % (arm_align, leg_align))

    # -------------------------------------------------------------- the build
    msg = ar.connect()
    print("// connect():")
    for line in msg.splitlines():
        print("//   " + line)
    gate(8, msg.startswith("retarget connected") and cmds.objExists(ar.HOLDER),
         "connect() built it")
    helpers = cmds.listRelatives(ar.HOLDER, children=True, fullPath=True) or []
    registered = set(cmds.listConnections(ar.HOLDER + "." + ar.SWITCH, source=False,
                                          destination=True) or [])
    # since 2026-09-05 only a POLE goes through a helper pair (a point constraint
    # cannot turn its offset with the bone); a position+rotation drive is one
    # parentConstraint carrying its rest offset on its own target offsets
    poles = [d for d in plan.drives if d.translate and not d.rotate]
    rigid_drives = [d for d in plan.drives if d.translate and d.rotate]
    single = [d.control for d in rigid_drives
              if cmds.listConnections(d.control, source=True, destination=False,
                                      type="parentConstraint")]
    gate(9, len(helpers) == len(poles) and len(single) == len(rigid_drives)
         and len(registered) >= len(plan.drives),
         "%d helpers for the %d poles, the %d position+rotation drives are single "
         "parentConstraints, %d constraints registered on %s.%s"
         % (len(helpers), len(poles), len(rigid_drives), len(registered),
            ar.HOLDER, ar.SWITCH))
    main_driven = bool(cmds.listConnections("Main", source=True, destination=False,
                                            type="constraint"))
    gate(10, main_driven, "Main is driven (the horizontal travel; Mixamo has no root)")

    # ----------------------------------------------------- what it looks like
    # A rotation retarget is a promise about ANGLES, and the FK chain is what
    # carries them: with a limb in IK its bones come from the solver reaching the
    # source's foot instead (gate 12 measures that half).  So each promise is
    # measured in the mode that makes it.
    for name in blends:
        cmds.setAttr(name + ".FKIKBlend", 0.0)
    print("// per-bone direction error against the source, at every sample "
          "(all four limbs in FK):")
    tracks, worst_dir = {}, (0.0, "", 0.0)
    for frame in SAMPLES:
        cmds.currentTime(frame)
        row = {}
        for bone, kid, sbone, skid in CHECK:
            ours_dir = where(rig_bones[kid]) - where(rig_bones[bone])
            src_dir = where(bones[skid]) - where(bones[sbone])
            row[bone] = angle_between(ours_dir, src_dir)
            if row[bone] > worst_dir[0]:
                worst_dir = (row[bone], bone, frame)
        tracks[frame] = row
    for bone, _, _, _ in CHECK:
        print("//   %-14s %s" % (bone, "  ".join("%6.3f" % tracks[f][bone]
                                                 for f in SAMPLES)))
    gate(11, worst_dir[0] < 0.05,
         "every measured bone POINTS where the source's does, over %d frames: worst "
         "%.6f deg (%s at frame %g)" % (len(SAMPLES), worst_dir[0], worst_dir[1],
                                        worst_dir[2]))
    cmds.currentTime(40.0)
    pelvis = (where(rig_bones["pelvis"]) - where(bones["Hips"])).length()
    fk_hand = (where(rig_bones["hand_l"]) - where(bones["LeftHand"])).length()
    for name in blends:
        cmds.setAttr(name + ".FKIKBlend", 10.0)
    ik_hand = (where(rig_bones["hand_l"]) - where(bones["LeftHand"])).length()
    ik_foot = (where(rig_bones["foot_l"]) - where(bones["LeftFoot"])).length()
    for name in blends:
        cmds.setAttr(name + ".FKIKBlend", 0.0)
    gate(12, pelvis < 0.01 and ik_hand < 0.05 and ik_foot < 0.05 and fk_hand > 1.0,
         "the pelvis lands on the source's hips (%.6f cm apart); in IK the hand is "
         "%.4f cm and the foot %.4f cm from the source's own, while in FK the hand "
         "sits %.2f cm away because our arm is 16.5%% longer and the angles are what "
         "is copied" % (pelvis, ik_hand, ik_foot, fk_hand))
    travel = abs(cmds.getAttr("Main.translateZ")) + abs(cmds.getAttr("Main.translateX"))
    gate(13, cmds.getAttr("Main.translateY") == 0.0,
         "Main carries the horizontal travel only: x %.2f y %.2f z %.2f"
         % (cmds.getAttr("Main.translateX"), cmds.getAttr("Main.translateY"),
            cmds.getAttr("Main.translateZ")))

    # ---------------------------------------------------------------- the bake
    if BAKE:
        cmds.playbackOptions(edit=True, min=0.0, max=75.0)
        cmds.currentTime(40.0)
        before = dict((b, where(rig_bones[b])) for b, _, _, _ in CHECK)
        mel.eval("asMoCapMatcherBake;")
        baked = set(c for c in controls
                    if c not in keyed_before and cmds.listConnections(
                        c, type="animCurve", source=True, destination=False))
        gate(14, len(baked) >= 40 and "RootX_M" in baked and "FKShoulder_L" in baked,
             "AdvancedSkeleton's own Bake keyed %d controls of the %d driven"
             % (len(baked), len(plan.drives)))
        mel.eval("asMoCapMatcherDisconnect;")
        leftovers = (cmds.ls(ar.DRIVER_PREFIX + "*") or []) + \
                    (cmds.ls(ar.TARGET_PREFIX + "*") or []) + \
                    ([ar.HOLDER] if cmds.objExists(ar.HOLDER) else [])
        still = [d.control for d in plan.drives
                 if cmds.listConnections(d.control, source=True, destination=False,
                                         type="constraint")]
        gate(15, not leftovers and not still,
             "Disconnect left no node of ours (%s) and no constraint on a control (%s)"
             % (leftovers[:3], still[:3]))
        cmds.currentTime(40.0)
        after = dict((b, where(rig_bones[b])) for b, _, _, _ in CHECK)
        moved = max((after[b] - before[b]).length() for b in before)
        gate(16, moved < 0.01,
             "with the constraints gone the baked rig holds the same pose: worst bone "
             "moved %.6f cm" % moved)
        blends_now = sorted(set(cmds.ls(type="pairBlend") or []) - blend_nodes)
        gate(17, not blends_now,
             "the bake spliced no pairBlend onto the rig (%s)" % blends_now[:3])
finally:
    for control in controls:
        if control in keyed_before:
            continue
        try:
            if cmds.listConnections(control, type="animCurve", source=True,
                                    destination=False):
                cmds.cutKey(control, clear=True)
        except Exception as exc:
            print("// could not clear %s: %s" % (control, exc))
    for node in sorted(set(cmds.ls(type="pairBlend") or []) - blend_nodes):
        try:
            cmds.delete(node)
        except Exception:
            pass
    try:
        if cmds.objExists(ar.HOLDER):
            ar.disconnect()
    except Exception as exc:
        print("// disconnect in teardown: %s" % exc)
    try:
        cmds.playbackOptions(edit=True, min=saved["min"], max=saved["max"])
        cmds.currentTime(0.0)
        mel.eval("asGoToBuildPose bodySetup;")
        # AFTER the build pose, never before: asGoToBuildPose writes the FKIKBlend
        # values the rig was BUILT with (IK legs), so restoring them first hands
        # the animator back a rig in the wrong mode -- measured, it did.
        for name, value in blends.items():
            cmds.setAttr(name + ".FKIKBlend", value)
        if bias_saved is not None:
            cmds.setAttr("%s.%s" % ar.NECK_BIAS[:2], bias_saved)
        if share_saved is not None:
            cmds.setAttr("%s.%s" % ar.NECK_TWIST[:2], share_saved)
    except Exception as exc:
        print("// build pose: %s" % exc)
    drift, where_worst = 0.0, None
    for name, path in (rig_bones.items() if rest else []):
        if not cmds.objExists(path):
            continue
        dev = worst(om.MMatrix(rest[name]), wm(path))
        if dev > drift:
            drift, where_worst = dev, name
    gate(18, drift < 1e-3, "the rig is back at its bind pose, drift %.9f (%s)"
         % (drift, where_worst))
    try:
        cmds.evaluationManager(mode=saved["em"])
        cmds.autoKeyframe(state=saved["autoKey"])
        cmds.currentTime(saved["time"])
        cmds.select(clear=True)
        if saved["sel"]:
            cmds.select([s for s in saved["sel"] if cmds.objExists(s)])
    except Exception as exc:
        print("// restore: %s" % exc)
    print("restored: em %s autoKey %s range %g..%g time %g sel %s"
          % (cmds.evaluationManager(query=True, mode=True)[0],
             cmds.autoKeyframe(query=True, state=True),
             cmds.playbackOptions(query=True, min=True),
             cmds.playbackOptions(query=True, max=True),
             cmds.currentTime(query=True), cmds.ls(selection=True)))
print("RESULT: %d of 18 gates failed %s" % (len(FAILS), FAILS))
