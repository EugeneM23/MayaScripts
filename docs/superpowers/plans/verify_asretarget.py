"""Live gates for the retarget onto the AdvancedSkeleton rig (maya_asretarget).

Send through the command-port bridge into the animator's OPEN scene, the one
holding the AdvancedSkeleton rig built on 2026-09-04.

It builds its own source: an exact twin of the rig's UE skeleton, duplicated
into the namespace `asrtVerify:` and given a synthetic take whose numbers are
known, then deleted by UUID (trap 47). Then it connects the retarget, measures
the transfer, presses AdvancedSkeleton's own Bake and Disconnect through MEL,
and measures that the rig plays the take with the source gone.

Everything it changes is put back: the baked keys it caused (only on controls
that carried none), the bind pose, the playback range, the current frame,
autoKey, the evaluation mode and the selection.

Spec: docs/superpowers/specs/2026-09-04-as-retarget-design.md
"""
import math
import sys

import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"   # the retarget modules live in the plugin since 2026-09-07
AS_MEL = "C:/!!!Work/MayaScripts/sources/AdvancedSkeleton/AdvancedSkeleton.mel"  # local, not in git
NS = "asrtVerify"
END = 20.0

if REPO not in sys.path:
    sys.path.insert(0, REPO)
sys.modules.pop("maya_asretarget", None)          # prove today's code, not yesterday's
import maya_asretarget as ar                       # noqa: E402

# base value + delta, keyed at frame 0 and frame END off the value the bone
# already holds -- keying a literal 0 would bend this skeleton (trap 30).
TAKE = [("root", "translateZ", 100.0), ("root", "rotateY", 25.0),
        ("spine_01", "rotateX", 10.0), ("spine_03", "rotateZ", 20.0),
        ("neck_01", "rotateY", 15.0), ("head", "rotateZ", -12.0),
        ("clavicle_l", "rotateY", 8.0),
        ("thigh_l", "rotateZ", 35.0), ("calf_l", "rotateZ", -45.0),
        ("foot_l", "rotateZ", 10.0),
        ("upperarm_r", "rotateY", -30.0), ("lowerarm_r", "rotateZ", 40.0),
        ("hand_r", "rotateX", 25.0), ("index_01_l", "rotateZ", 30.0),
        # a twin's bones can carry TRANSLATION too (measured 2026-09-05 on the
        # animator's Longsword clip: clavicles sliding 3.65 cm, the neck base
        # 3.67, spine_05 2.52) and a rotation-only drive lost every centimetre
        # of it -- so the fixture carries some, or it cannot see that bug
        ("clavicle_l", "translateY", 3.0), ("spine_05", "translateZ", 2.0),
        ("neck_01", "translateX", -2.5),
        # a head ROLL (X is the bone axis): the neck in-between hands half of it
        # to neck_02, which a UE source never does -- the neck's second knob
        ("head", "rotateX", 30.0)]
# bones the FK controls drive directly (the spine is FK, the limbs are IK).
# The neck chain is measured on its own: AdvancedSkeleton's neck in-between
# gives neck_01 half of its control's bend, so an absolute per-bone copy cannot
# land it -- see NECK_BONES below.
FK_BONES = ["pelvis", "spine_01", "spine_03", "spine_05",
            "clavicle_l", "clavicle_r", "index_01_l", "index_02_l", "thumb_02_r"]
NECK_BONES = ["neck_01", "neck_02", "head"]
IK_BONES = ["hand_l", "hand_r", "foot_l", "foot_r", "ball_l", "ball_r"]
MID_BONES = ["calf_l", "calf_r", "lowerarm_l", "lowerarm_r"]
SAMPLES = [0.0, 5.0, 12.0, 20.0]

FAILS = []
CREATED = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append((n, msg))


def register(nodes):
    for n in nodes:
        for uid in cmds.ls(n, uuid=True) or []:
            if uid not in CREATED:
                CREATED.append(uid)


def wm(node):
    return cmds.getAttr(node + ".worldMatrix[0]")


def worst(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def ang(a, b):
    qa = om.MTransformationMatrix(om.MMatrix(a)).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(om.MMatrix(b)).rotation(asQuaternion=True)
    d = qa.inverse() * qb
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(d.w)))))


def build_source(rig_bones):
    """An exact twin of the rig's UE skeleton, in its own namespace, animated."""
    dup = cmds.ls(cmds.duplicate("|root", returnRootsOnly=True)[0], long=True)[0]
    register([dup])
    joints = [dup] + (cmds.listRelatives(dup, allDescendents=True, type="joint",
                                         fullPath=True) or [])
    register(joints)
    cons = cmds.listRelatives(dup, allDescendents=True, type="constraint",
                              fullPath=True) or []
    if cons:                                        # the copy of OUR rig's drivers
        cmds.delete(cons)
    if not cmds.namespace(exists=NS):
        cmds.namespace(add=NS)
    plan = [(cmds.ls(j, uuid=True)[0], "root" if j == dup else ar.leaf(j))
            for j in joints]
    for uid, name in plan:                          # paths go stale on rename (trap 48)
        path = cmds.ls(uid, long=True)
        if path:
            cmds.rename(path[0], "%s:%s" % (NS, name))
    root = cmds.ls("%s:root" % NS, long=True)[0]
    bones = ar.source_bones(root)
    for bone, attr, delta in TAKE:
        plug = bones[bone] + "." + attr
        base = cmds.getAttr(plug)
        cmds.setKeyframe(plug, time=0.0, value=base)
        cmds.setKeyframe(plug, time=END, value=base + delta)
    register(cmds.listConnections(list(bones.values()), type="animCurve",
                                  source=True, destination=False) or [])
    return root, bones


saved = {"autoKey": cmds.autoKeyframe(query=True, state=True),
         "time": cmds.currentTime(query=True),
         "sel": cmds.ls(selection=True, long=True) or [],
         "em": cmds.evaluationManager(query=True, mode=True)[0],
         "min": cmds.playbackOptions(query=True, min=True),
         "max": cmds.playbackOptions(query=True, max=True)}
blends_saved = dict((c, cmds.getAttr(c + ".FKIKBlend"))
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
blends_before = set(cmds.ls(type="pairBlend") or [])
rest = {}
source_track = {}
cmds.autoKeyframe(state=False)
cmds.evaluationManager(mode="off")               # the rig crashed parallel EM once
try:
    if mel.eval('whatIs "asMoCapMatcherBake"') == "Unknown":
        mel.eval('source "%s";' % AS_MEL)
    rig = ar.rig_paths()
    ue_root = ar.rig_skeleton_root(rig)
    rig_bones = dict((ar.leaf(p), p) for p in [ue_root] + (
        cmds.listRelatives(ue_root, allDescendents=True, type="joint",
                           fullPath=True) or []))
    cmds.currentTime(0.0)
    for name, path in rig_bones.items():
        rest[name] = wm(path)
    rest_controls = dict((c, wm(c)) for c in ("Main", "RootX_M", "PoleLeg_L",
                                              "PoleArm_R"))
    gate(1, ue_root == "|root" and len(rig_bones) == 93 and not keyed_before,
         "the rig drives |root (%d bones); %d controls, none keyed"
         % (len(rig_bones), len(controls)))

    # ---------------------------------------------------------------- refusals
    cmds.select(clear=True)
    msg = ar.connect()
    gate(2, "select" in msg.lower() and not cmds.objExists(ar.HOLDER),
         "connect() with nothing selected: %r" % msg)
    cmds.select("persp")
    msg = ar.connect()
    gate(3, "joint" in msg.lower() and not cmds.objExists(ar.HOLDER),
         "connect() on a camera: %r" % msg)
    cmds.select(rig_bones["pelvis"])
    msg = ar.connect()
    gate(4, "rig's own" in msg and not cmds.objExists(ar.HOLDER),
         "connect() on our own rigged skeleton: %r" % msg)
    gate(5, "nothing connected" in ar.disconnect(),
         "disconnect() with nothing connected says so")

    # ---------------------------------------------------------------- fixture
    source_root, bones = build_source(rig_bones)
    gate(6, len(bones) == 93 and cmds.objExists("%s:pelvis" % NS),
         "source twin built: %s, %d bones, take on %d channels"
         % (source_root, len(bones), len(TAKE)))

    # ------------------------------------------------------------------ build
    existing = [c for c in ar.candidates() if cmds.objExists(c)]
    rest_control = dict((c, wm(c)) for c in existing)
    cmds.select(bones["spine_03"])
    msg = ar.connect()
    plan = ar._plan(source_root)
    gate(7, msg.startswith("retarget connected") and cmds.objExists(ar.HOLDER),
         "connect(): %s" % msg.replace("\n", " | "))
    gate(8, not plan.missing and len(plan.drives) == len(existing),
         "%d of the %d candidate controls exist and every one is driven; nothing "
         "missing (%s)" % (len(plan.drives), len(ar.candidates()), plan.missing))

    helpers = cmds.listRelatives(ar.HOLDER, children=True, fullPath=True) or []
    helped = set(h.split("|")[-1][len(ar.DRIVER_PREFIX):] for h in helpers)
    wrong = []
    for drive in plan.drives:
        got = set()
        for con in cmds.listConnections(drive.control, source=True,
                                        destination=False, type="constraint") or []:
            for tgt in cmds.listConnections(con + ".target[0].targetParentMatrix",
                                            source=True, destination=False) or []:
                got.add(tgt)
        want = (ar.TARGET_PREFIX + drive.control if drive.control in helped
                else bones[drive.bone].split("|")[-1])
        if want not in got:
            wrong.append((drive.control, want, sorted(got)))
    gate(9, not wrong, "every control constrained to its expected source; wrong=%s"
         % wrong[:4])

    # the offset is decided by measurement, so the gate measures the result: at
    # the take's rest frame each target must stand exactly on its control
    worst_target = max((worst(wm(ar.TARGET_PREFIX + c), rest_control[c]), c)
                       for c in helped)
    gate(10, worst_target[0] < 1e-4,
         "%d offset helpers (%s); at the take's rest frame each target sits on its "
         "control, worst %.9f (%s)"
         % (len(helped), " ".join(sorted(helped)), worst_target[0], worst_target[1]))

    cons = cmds.listConnections(ar.HOLDER + "." + ar.SWITCH, source=False,
                                destination=True) or []
    gate(11, len(set(cons)) >= len(plan.drives) and len(helpers) == len(helped),
         "%d constraints registered on %s.%s, %d helper drivers parented under it"
         % (len(set(cons)), ar.HOLDER, ar.SWITCH, len(helpers)))

    # A position+rotation drive (every FK control since 2026-09-05, the IK ends,
    # Main, RootX_M) is ONE parentConstraint carrying the rest offset on its own
    # target offsets -- so at the take's rest frame every such control must stand
    # exactly where it stood before the connect, with no helper node anywhere
    # near it.  This is the gate on the measured offset convention.
    rigid_drives = [d for d in plan.drives if d.translate and d.rotate]
    cmds.currentTime(1.0)
    cmds.currentTime(0.0)
    rigid_worst = max((worst(wm(d.control), rest_control[d.control]), d.control)
                      for d in rigid_drives)
    single = [d.control for d in rigid_drives
              if cmds.listConnections(d.control, source=True, destination=False,
                                      type="parentConstraint")
              and d.control not in helped]
    gate(27, rigid_worst[0] < 1e-4 and len(single) == len(rigid_drives)
         and len(rigid_drives) >= 66,
         "%d position+rotation drives are single parentConstraints (no helper), "
         "and at the rest frame each control stands on its own rest, worst "
         "%.9f (%s)" % (len(rigid_drives), rigid_worst[0], rigid_worst[1]))

    # --------------------------------------------------------------- transfer
    def measure(frame):
        cmds.currentTime(frame)
        out = {}
        for name in FK_BONES + NECK_BONES + IK_BONES + MID_BONES + ["root", "pelvis"]:
            out[name] = (wm(rig_bones[name]), wm(bones[name]))
        return out

    tracks = dict((f, measure(f)) for f in SAMPLES)
    source_track = dict((f, dict((n, v[1]) for n, v in t.items()))
                        for f, t in tracks.items())

    print("// per-bone at frame %g -- position error, orientation error:" % END)
    for name in FK_BONES + NECK_BONES + IK_BONES + MID_BONES:
        rigm, srcm = tracks[END][name]
        pos = math.sqrt(sum((rigm[12 + i] - srcm[12 + i]) ** 2 for i in range(3)))
        print("//   %-14s pos %8.4f cm   rot %8.4f deg" % (name, pos, ang(rigm, srcm)))
    print("// control against its source bone at frame %g (is the constraint "
          "reaching its target?):" % END)
    for control, bone in (("FKNeck_M", "neck_01"), ("FKNeckPart1_M", "neck_02"),
                          ("FKHead_M", "head"), ("FKSpine3_M", "spine_03"),
                          ("FKScapula_L", "clavicle_l")):
        locks = [a for a in ("rx", "ry", "rz")
                 if cmds.getAttr(control + "." + a, lock=True)
                 or not cmds.getAttr(control + "." + a, settable=True)]
        print("//   %-16s %8.5f deg from %s | locked/unsettable %s"
              % (control, ang(wm(control), wm(bones[bone])), bone, locks))
    for node in ("FKNeckStartBiasRV_M", "FKNeckMidBiasRV_M", "FKNeckEndBiasRV_M"):
        if not cmds.objExists(node):
            continue
        print("//   %s inputValue %s <- %s | output %s -> %s"
              % (node, cmds.getAttr(node + ".inputValue"),
                 cmds.listConnections(node + ".inputValue", source=True,
                                      destination=False, plugs=True),
                 cmds.getAttr(node + ".outValue"),
                 cmds.listConnections(node + ".outValue", source=False,
                                      destination=True, plugs=True)))
    print("//   bias-ish attributes on FKNeck_M: %s"
          % [(a, cmds.getAttr("FKNeck_M." + a))
             for a in (cmds.listAttr("FKNeck_M", userDefined=True) or [])])
    fk_worst = max((worst(*tracks[f][n]), n, f) for f in SAMPLES for n in FK_BONES)
    gate(12, fk_worst[0] < 1e-3,
         "FK-driven bones reproduce the source over %d frames, worst world-matrix "
         "element %.9f (%s at frame %g)" % (len(SAMPLES), fk_worst[0], fk_worst[1],
                                            fk_worst[2]))
    ik_worst = max((worst(*tracks[f][n]), n, f) for f in SAMPLES for n in IK_BONES)
    gate(13, ik_worst[0] < 0.01,
         "hands, feet and balls land on the source within the IK solver's own "
         "residual, worst %.9f cm (%s at frame %g)"
         % (ik_worst[0], ik_worst[1], ik_worst[2]))
    # the neck: AdvancedSkeleton's in-between hands neck_01 HALF of its control's
    # bend at bias 0, and connect() sets the bias to 10 by default since
    # 2026-09-05 (the animator's ask being an exact neck).  So first the exact
    # neck the default leaves, then the half-bend it removed -- measured by
    # putting the bias back for a moment with the retarget still connected.
    control, attr, full = ar.NECK_BIAS
    tnode, tattr, tfull = ar.NECK_TWIST
    own = dict((b, d) for b, a, d in TAKE if a.startswith("rotate"))["neck_01"]
    cmds.currentTime(END)
    neck_exact = ang(wm(rig_bones["neck_01"]), wm(bones["neck_01"]))
    neck2_exact = ang(wm(rig_bones["neck_02"]), wm(bones["neck_02"]))
    head_exact = math.sqrt(sum((wm(rig_bones["head"])[12 + i]
                                - wm(bones["head"])[12 + i]) ** 2 for i in range(3)))
    gate(25, cmds.getAttr(control + "." + attr) == full
         and cmds.getAttr(tnode + "." + tattr) == tfull
         and neck_exact < 1e-3 and neck2_exact < 1e-3 and head_exact < 1e-3,
         "connect() set %s.%s to %g and %s.%s to %g, and the neck lands 1:1: "
         "neck_01 %.6f deg, neck_02 %.6f deg, head %.6f cm off (the take bends "
         "neck_01 by %g deg, rolls the head 30 and slides the neck base)"
         % (control, attr, full, tnode, tattr, tfull, neck_exact, neck2_exact,
            head_exact, own))
    # the rig's own values for a moment, with the retarget still connected: the
    # bend share halves neck_01, the twist share rolls neck_02 by half the head's
    # roll (a UE source keeps neck_02 at its rest roll) -- both measured, then
    # both put back to what connect() set
    cmds.setAttr(control + "." + attr, 0.0)
    cmds.setAttr(tnode + "." + tattr, 0.5)
    cmds.currentTime(END - 1.0)
    cmds.currentTime(END)
    deficit = ang(wm(rig_bones["neck_01"]), wm(bones["neck_01"]))
    roll = ang(wm(rig_bones["neck_02"]), wm(bones["neck_02"]))
    head_turn = ang(wm(rig_bones["head"]), wm(bones["head"]))
    cmds.setAttr(control + "." + attr, full)
    cmds.setAttr(tnode + "." + tattr, tfull)
    gate(26, abs(deficit - own / 2.0) < 0.1 and roll > 5.0 and head_turn < 1e-3,
         "at bias 0 and twist share 0.5 the in-between costs exactly half of the "
         "neck's OWN bend (%g deg on the take, the rig %.4f short, half is %g) and "
         "rolls neck_02 by %.2f deg of the head's 30 deg roll, while the head's "
         "orientation stays exact (%.5f deg) -- the two costs the default removes"
         % (own, deficit, own / 2.0, roll, head_turn))
    mid_worst = max((ang(*tracks[f][n]), n, f) for f in SAMPLES for n in MID_BONES)
    gate(14, mid_worst[0] < 1.0,
         "knees and elbows follow the source's plane, worst %.4f deg (%s at frame %g)"
         % (mid_worst[0], mid_worst[1], mid_worst[2]))
    travel = worst(tracks[END]["root"][0], tracks[END]["root"][1])
    moved = math.sqrt(sum((tracks[END]["root"][0][12 + i] - rest["root"][12 + i]) ** 2
                          for i in range(3)))
    gate(15, travel < 1e-3 and abs(moved - 100.0) < 0.01,
         "root motion lands in the root BONE: it travelled %.4f cm of the source's "
         "100 and matches it to %.9f" % (moved, travel))
    idx = ang(*tracks[END]["index_01_l"])
    gate(16, idx < 1e-3 and ang(rest["index_01_l"], tracks[END]["index_01_l"][0]) > 25,
         "the finger curl transferred: %.4f deg from the source, %.2f deg from rest"
         % (idx, ang(rest["index_01_l"], tracks[END]["index_01_l"][0])))

    msg = ar.connect()
    gate(17, ar.HOLDER in msg and "Disconnect" in msg,
         "a second connect() refuses: %r" % msg)

    # ------------------------------------------------------------------- bake
    cmds.playbackOptions(edit=True, min=0.0, max=END)
    cmds.currentTime(END)
    watched = ("FKHip_L", "FKKnee_L", "FKAnkle_L", "FKShoulder_R", "FKElbow_R")
    before_bake = dict((c, cmds.getAttr(c + ".rotate")[0]) for c in watched)
    mel.eval("asMoCapMatcherBake;")
    baked = set(c for c in controls
                if c not in keyed_before and cmds.listConnections(
                    c, type="animCurve", source=True, destination=False))
    # what MUST be keyed is computed from the take, not guessed: the vendor's
    # Bake ends in `delete -staticChannels`, and a control whose LOCAL values do
    # not change (the whole rig turns with Main) is rightly left alone.
    must = set(d.control for d in plan.drives
               if d.bone in set(b for b, _, _ in TAKE))
    gate(18, must <= baked,
         "AdvancedSkeleton's own Bake keyed %d controls, including all %d the take "
         "moves (static channels are dropped by its own delete -staticChannels); "
         "missing %s" % (len(baked), len(must), sorted(must - baked)))
    mel.eval("asMoCapMatcherDisconnect;")
    leftovers = ([n for n in cmds.ls("%s*" % ar.DRIVER_PREFIX) or []]
                 + [n for n in cmds.ls("%s*" % ar.TARGET_PREFIX) or []]
                 + ([ar.HOLDER] if cmds.objExists(ar.HOLDER) else []))
    still = [c for c in (d.control for d in plan.drives)
             if cmds.listConnections(c, source=True, destination=False,
                                     type="constraint")]
    gate(19, not leftovers and not still,
         "Disconnect left no node of ours (%s) and no constraint on a control (%s)"
         % (leftovers[:3], still[:3]))

    cmds.currentTime(END)
    print("// what the bake kept, at frame %g (constrained value -> baked value):"
          % END)
    for control in watched:
        now = cmds.getAttr(control + ".rotate")[0]
        print("//   %-14s %s -> %s   worst %.6f deg"
              % (control, ["%.4f" % v for v in before_bake[control]],
                 ["%.4f" % v for v in now],
                 max(abs(a - b) for a, b in zip(before_bake[control], now))))

    for uid in list(CREATED):                        # the source goes away
        path = cmds.ls(uid, long=True)
        if path and cmds.objExists(path[0]):
            try:
                cmds.delete(path[0])
            except Exception:
                pass
    gate(20, not cmds.objExists("%s:root" % NS),
         "the source twin is gone; the rig is on its own now")

    played = []
    for frame in SAMPLES:
        cmds.currentTime(frame)
        for name in FK_BONES + IK_BONES:
            played.append((worst(wm(rig_bones[name]), source_track[frame][name]),
                           name, frame))
    play_worst = max(played)
    gate(21, play_worst[0] < 0.01,
         "with the source deleted the rig still plays the take, worst world-matrix "
         "element %.9f (%s at frame %g)" % (play_worst[0], play_worst[1],
                                            play_worst[2]))
    blends = sorted(set(cmds.ls(type="pairBlend") or []) - blends_before)
    gate(22, not blends, "the bake spliced no pairBlend onto the rig (%s)" % blends[:3])

    # The promise the IK residual rests on: the FK controls carry the source's
    # pose exactly, so a limb flipped to FK reproduces it bone for bone.
    for name, value in blends_saved.items():
        cmds.setAttr(name + ".FKIKBlend", 0.0)
    cmds.currentTime(END)
    fk_exact = max((worst(wm(rig_bones[n]), source_track[END][n]), n)
                   for n in ("calf_l", "foot_l", "lowerarm_r", "hand_r"))
    for name, value in blends_saved.items():
        cmds.setAttr(name + ".FKIKBlend", value)
    gate(23, fk_exact[0] < 0.1,
         "with the limbs flipped to FK the baked rig reproduces the source bone for "
         "bone, worst %.9f cm (%s)" % (fk_exact[0], fk_exact[1]))
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
    for node in sorted(set(cmds.ls(type="pairBlend") or []) - blends_before):
        try:
            cmds.delete(node)
        except Exception:
            pass
    try:
        if cmds.objExists(ar.HOLDER):
            ar.disconnect()
    except Exception as exc:
        print("// disconnect in teardown: %s" % exc)
    for uid in CREATED:
        path = cmds.ls(uid, long=True)
        if path and cmds.objExists(path[0]):
            try:
                cmds.delete(path[0])
            except Exception:
                pass
    try:
        if cmds.namespace(exists=NS):
            cmds.namespace(removeNamespace=NS, mergeNamespaceWithRoot=True)
    except Exception as exc:
        print("// namespace teardown: %s" % exc)
    try:
        cmds.playbackOptions(edit=True, min=saved["min"], max=saved["max"])
    except Exception:
        pass
    try:
        cmds.currentTime(0.0)
        mel.eval("asGoToBuildPose bodySetup;")
    except Exception as exc:
        print("// build pose: %s" % exc)
    drift = 0.0
    where = None
    for name, path in (rig_bones.items() if rest else []):
        if not cmds.objExists(path):
            continue
        dev = worst(rest[name], wm(path))
        if dev > drift:
            drift, where = dev, name
    gate(24, drift < 1e-3, "the rig is back at its bind pose, drift %.9f (%s)"
         % (drift, where))
    try:
        for name, value in blends_saved.items():
            cmds.setAttr(name + ".FKIKBlend", value)
        if bias_saved is not None:
            cmds.setAttr("%s.%s" % ar.NECK_BIAS[:2], bias_saved)
        if share_saved is not None:
            cmds.setAttr("%s.%s" % ar.NECK_TWIST[:2], share_saved)
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
print("RESULT: %d of 27 gates failed %s" % (len(FAILS), FAILS))
