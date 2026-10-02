"""Standalone gates: the IK limbs show what the FK limbs show after every retarget (2026-10-02).

    mayapy verify_ik_follows_fk.py [PLUGIN_DIR] [PHASES]

mayapy STANDALONE, an empty scene per phase (it adds rigs and imports clips): never the
animator's scene. PHASES is a comma list of a..g (all by default); run them in parallel
processes, each takes a minute.

The animator: «если мы перенесли анимацию с растяжением костей то кости при переключении
контролов на IK не растянулись ... анимация IK должна соответствовать анимации FK это
обязательное условие». Every gate switches each limb's FKIKBlend between 0 and 10 on the
same frames and measures the GAME bones - where the export is.

  a  Creep_Rig, a UE clip, Squash & stretch (arms -17 %): IK = FK on every limb bone; the
     control - the same press with the IK carry switched off - leaves the elbows 11 cm out
  b  Orc_D_Rig, the same clip: the clavicle's stretch (the shoulders) and the foot's (the ball)
  c  Manny_Rig, Sweep Fall (Mixamo) squashed & stretched: shoulders 4 cm, hips 3 cm, the foot
     2 cm longer - all in the IK
  d  Manny_Rig, the UE clip, a twin: the IK poles on the rig's own FK (on the clip's upper
     bones they put the elbows 20 cm off)
  e  a Rotations take on the Creep after a stretch one: every IK channel the stretch moved back
     at its rest, IK = FK again
  f  the Connections FK / IK switch on a stretched arm: to IK keeps it, to FK keeps it, a range
  g  Manny_Rig, Sweep Fall, Rotations: IK = FK (the IK used to stand on the clip's hands)
"""
import math
import os
import sys
import time

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = (sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1])
          else os.path.normpath(os.path.join(HERE, "..", "..", "SkeldarAnim")))
PHASES = set((sys.argv[2] if len(sys.argv) > 2 else "a,b,c,d,e,f,g").split(","))
sys.path.insert(0, PLUGIN)
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass

HEAVY = "C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX"
MIXAMO = "C:/Users/MY PC/Downloads/Sweep Fall.fbx"

import maya_ikmatch as ikm
import maya_retargetmode as rm
import maya_rigs
import maya_rig_retarget as rr
import maya_asretarget as ar
from maya_scenesetup import catalog, character, connections, fkik

print("plugin:", os.path.dirname(rm.__file__))
FAILS = []
ANSWER = [rm.SQUASH]
rm.set_asker(lambda text: ANSWER[0])


def gate(n, ok, msg):
    print("%s gate %s: %s" % ("PASS" if ok else "FAIL", n, msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(n)


def leaf(p):
    return p.split("|")[-1].split(":")[-1]


def add(key):
    before = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key(key))
    return [r for r in maya_rigs.rigs() if r.namespace not in before][0]


def import_clip(path, ns):
    before = set(cmds.ls(type="joint", long=True))
    cmds.namespace(add=ns)
    cmds.namespace(set=":" + ns)
    mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
    mel.eval('FBXImport -f "%s";' % path)
    cmds.namespace(set=":")
    new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
    root = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
               key=lambda j: j.count("|"))
    paths = cmds.listRelatives(root, ad=True, type="joint", fullPath=True)
    first = int(cmds.findKeyframe(paths, which="first"))
    last = int(cmds.findKeyframe(paths, which="last"))
    cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
    return root, first, last


def bones_of(rig):
    root = rig.skeleton_root
    return dict((leaf(p), p) for p in [root] + (cmds.listRelatives(
        root, ad=True, type="joint", fullPath=True) or []))


def wm(p):
    return om.MMatrix(cmds.xform(p, q=True, ws=True, m=True))


def P(m):
    return om.MVector(m[12], m[13], m[14])


CHILD = {"upperarm_r": "lowerarm_r", "lowerarm_r": "hand_r", "upperarm_l": "lowerarm_l",
         "lowerarm_l": "hand_l", "thigh_r": "calf_r", "calf_r": "foot_r", "foot_r": "ball_r",
         "thigh_l": "calf_l", "calf_l": "foot_l", "foot_l": "ball_l"}
LIMB_BONES = {"Arm_R": ["clavicle_r", "upperarm_r", "lowerarm_r", "hand_r", "middle_03_r"],
              "Arm_L": ["clavicle_l", "upperarm_l", "lowerarm_l", "hand_l", "middle_03_l"],
              "Leg_R": ["thigh_r", "calf_r", "foot_r", "ball_r"],
              "Leg_L": ["thigh_l", "calf_l", "foot_l", "ball_l"]}


def ik_against_fk(rig, first, last, n=13):
    """Over n frames, each limb shown in FK then in IK: (worst position, its bone@frame;
    worst bone direction, its bone@frame). The blends are put back."""
    bones = bones_of(rig)
    samples = [first + (last - first) * i // (n - 1) for i in range(n)]
    worst_p, worst_d = (0.0, ""), (0.0, "")
    for limb, names in LIMB_BONES.items():
        names = [k for k in names if k in bones]
        blend = maya_rigs.node(rig, "FKIK%s.FKIKBlend" % limb)
        was = cmds.getAttr(blend)
        try:
            for f in samples:
                shown = {}
                for value in (0.0, 10.0):
                    cmds.setAttr(blend, value)
                    cmds.currentTime(f + 0.5)
                    cmds.currentTime(f)
                    shown[value] = dict((k, wm(bones[k])) for k in set(names) | set(
                        CHILD[k] for k in names if k in CHILD))
                fk, ik = shown[0.0], shown[10.0]
                for k in names:
                    d = (P(ik[k]) - P(fk[k])).length()
                    if d > worst_p[0]:
                        worst_p = (d, "%s@%s" % (k, f))
                    if k in CHILD:
                        a = (P(ik[CHILD[k]]) - P(ik[k])).normal()
                        b = (P(fk[CHILD[k]]) - P(fk[k])).normal()
                        ang = math.degrees(math.acos(max(-1.0, min(1.0, a * b))))
                        if ang > worst_d[0]:
                            worst_d = (ang, "%s@%s" % (k, f))
        finally:
            cmds.setAttr(blend, was)
    return worst_p, worst_d


def retarget(rig, src, bones):
    t0 = time.time()
    ok, text = rr.run_retarget(source_root=src, rig=rig, bones=bones)
    print("    %s (%.1fs)" % (text[:420], time.time() - t0))
    return ok, text


def ik_lenghts(rig):
    out = {}
    for limb in ("IKArm_R", "IKArm_L", "IKLeg_R", "IKLeg_L"):
        node = maya_rigs.node(rig, limb)
        out[limb] = tuple(cmds.getAttr(node + "." + a) for a in ("Lenght1", "Lenght2"))
    return out


def stretch_phase(tag, rig_key, clip, bones=rm.STRETCH, control=False):
    cmds.file(new=True, force=True)
    rig = add(rig_key)
    src, first, last = import_clip(clip, "clip")
    ANSWER[0] = rm.SQUASH if bones == rm.STRETCH else rm.KEEP
    real = ikm.carry
    if control:
        ar.ikmatch.carry = lambda *a, **k: ""
    try:
        ok, text = retarget(rig, src, bones)
    finally:
        ar.ikmatch.carry = real
    worst_p, worst_d = ik_against_fk(rig, first, last)
    return rig, src, first, last, ok, text, worst_p, worst_d


TOL_CM, TOL_DEG = 0.06, 0.2

# ------------------------------------------------------------------- a
if "a" in PHASES:
    print("--- phase a: Creep_Rig, the UE clip, Squash & stretch")
    rig, src, first, last, ok, text, wp, wd = stretch_phase("a", "Creep_Rig", HEAVY, control=True)
    gate("a0", ok and wp[0] > 5.0,
         "the control (no IK carry): IK stands %.2f cm off the FK (%s) - the gates below can fail"
         % wp)
    rig, src, first, last, ok, text, wp, wd = stretch_phase("a", "Creep_Rig", HEAVY)
    gate("a1", ok and wp[0] < TOL_CM and wd[0] < TOL_DEG,
         "IK against FK: every limb bone %.4f cm (%s), directions %.3f deg (%s)" % (wp + wd))
    lens = ik_lenghts(rig)
    bones = bones_of(rig)
    cmds.currentTime(first)
    upper = (P(wm(bones["lowerarm_r"])) - P(wm(bones["upperarm_r"]))).length()
    unit = ikm.unit_of(maya_rigs.node(rig, "IKArm_R"), "Lenght1")
    gate("a2", abs(lens["IKArm_R"][0] - upper / unit) < 1e-4 and abs(lens["IKArm_R"][0] - 0.798) < 0.01
         and "the IK limbs take the FK's shape" in text and "arm_r lengths x0.798" in text,
         "IKArm_R.Lenght1 %.4f = the game upper arm %.3f over the IK rest %.3f; the line says it"
         % (lens["IKArm_R"][0], upper, unit))

# ------------------------------------------------------------------- b
if "b" in PHASES:
    print("--- phase b: Orc_D_Rig, the UE clip, Squash & stretch")
    rig, src, first, last, ok, text, wp, wd = stretch_phase("b", "Orc_D_Rig", HEAVY)
    gate("b1", ok and wp[0] < TOL_CM and wd[0] < TOL_DEG,
         "IK against FK: every limb bone %.4f cm (%s), directions %.3f deg (%s)" % (wp + wd))
    gate("b2", "the shoulder moved 0.91 cm" in text and "the ball moved 0.5" in text,
         "the clavicle's stretch and the foot's are in the IK: %s"
         % text.split("the IK limbs take the FK's shape: ")[-1].split("; retarget")[0][:300])

# ------------------------------------------------------------------- c
if "c" in PHASES:
    print("--- phase c: Manny_Rig, Sweep Fall (Mixamo), Squash & stretch")
    rig, src, first, last, ok, text, wp, wd = stretch_phase("c", "Manny_Rig", MIXAMO)
    shape = text.split("the IK limbs take the FK's shape: ")[-1].split("; retarget")[0]
    gate("c1", ok and wp[0] < TOL_CM and wd[0] < TOL_DEG,
         "IK against FK: every limb bone %.4f cm (%s), directions %.3f deg (%s)" % (wp + wd))
    gate("c2", "the shoulder moved 4.1" in shape and "the hip moved 3." in shape
         and "the ball moved 2.1" in shape, "carried: %s" % shape[:400])

# ------------------------------------------------------------------- d
if "d" in PHASES:
    print("--- phase d: Manny_Rig, the UE clip, a twin")
    rig, src, first, last, ok, text, wp, wd = stretch_phase("d", "Manny_Rig", HEAVY)
    gate("d1", ok and "twin, exact" in text and wp[0] < TOL_CM and wd[0] < TOL_DEG,
         "IK against FK: every limb bone %.4f cm (%s), directions %.3f deg (%s)" % (wp + wd))
    plan = ar._plan(src, rig)
    ik = [d for d in plan.drives if d.control.startswith(("IK", "Pole"))]
    gate("d2", ik and all(d.own for d in ik),
         "the twin's IK ends and poles ride our own FK (%d drives, none on the clip)" % len(ik))

# ------------------------------------------------------------------- e
if "e" in PHASES:
    print("--- phase e: Rotations after Squash & stretch, on the Creep")
    rig, src, first, last, ok, text, wp, wd = stretch_phase("e", "Creep_Rig", HEAVY)
    ANSWER[0] = rm.KEEP
    ok, text = retarget(rig, src, rm.ROTATION)
    rest = 0.0
    for limb in ikm.limbs(rig):
        for node, attr, value in ikm._plugs(limb):
            if value is None:
                continue
            values = value if isinstance(value, tuple) else (value,)
            for ch, v in zip(ikm._channels(attr), values):
                plug = node + "." + ch
                rest = max(rest, abs(cmds.getAttr(plug) - v))
                if ikm._time_curves(plug):
                    rest = 99.0
    wp, wd = ik_against_fk(rig, first, last)
    gate("e1", ok and rest < 1e-9, "every IK channel the stretch moved is at its rest to %.2e" % rest)
    gate("e2", wp[0] < TOL_CM and wd[0] < TOL_DEG,
         "IK against FK again: %.4f cm (%s), %.3f deg (%s)" % (wp + wd))

# ------------------------------------------------------------------- f
if "f" in PHASES:
    print("--- phase f: the Connections FK / IK switch on a stretched arm")
    rig, src, first, last, ok, text, wp, wd = stretch_phase("f", "Creep_Rig", HEAVY)
    bones = bones_of(rig)
    names = ["upperarm_r", "lowerarm_r", "hand_r", "middle_03_r"]
    frames = list(range(first, last + 1, 3))

    def snap():
        out = {}
        for f in frames:
            cmds.currentTime(f + 0.5)
            cmds.currentTime(f)
            out[f] = dict((k, P(wm(bones[k]))) for k in names)
        return out

    def worst(a, b):
        return max(((a[f][k] - b[f][k]).length(), "%s@%s" % (k, f)) for f in a for k in names)

    ik = maya_rigs.node(rig, "IKArm_R")
    fk_shown = snap()
    # the IK disturbed (the rig's own lengths, stretchy on, the root at rest), so the switch works
    cmds.cutKey(ik, attribute=["Lenght1", "Lenght2"], clear=True)
    cmds.setAttr(ik + ".Lenght1", 1.0)
    cmds.setAttr(ik + ".Lenght2", 1.0)
    cmds.setAttr(ik + ".stretchy", 4.0)
    root = maya_rigs.node(rig, "IKXShoulder_R")
    cmds.cutKey(root, attribute=["tx", "ty", "tz"], clear=True)
    cmds.setAttr(root + ".t", 0, 0, 0)
    note = connections.switch_arm("R", fkik.IK, rig=rig, highlight=())
    print("   ", note)
    got = snap()
    gate("f1", worst(got, fk_shown)[0] < 0.05 and "kept to" in note
         and abs(cmds.getAttr(ik + ".Lenght1") - 0.798) < 0.01 and cmds.getAttr(ik + ".stretchy") == 0,
         "to IK: the arm %.4f cm (%s) from the FK it showed, Lenght1 %.4f, stretchy reset"
         % (worst(got, fk_shown) + (cmds.getAttr(ik + ".Lenght1"),)))
    note = connections.switch_arm("R", fkik.FK, rig=rig, highlight=())
    got = snap()
    gate("f2", worst(got, fk_shown)[0] < 0.05, "back to FK: %.4f cm (%s) - %s"
         % (worst(got, fk_shown) + (note[:120],)))
    note = connections.switch_arm("R", fkik.IK, rig=rig, highlight=(20, 31))
    got = snap()
    gate("f3", worst(got, fk_shown)[0] < 0.05 and "range 20..30" in note,
         "a range to IK: %.4f cm (%s) - %s" % (worst(got, fk_shown) + (note[:120],)))

# ------------------------------------------------------------------- g
if "g" in PHASES:
    print("--- phase g: Manny_Rig, Sweep Fall, Rotations")
    rig, src, first, last, ok, text, wp, wd = stretch_phase("g", "Manny_Rig", MIXAMO, bones=rm.ROTATION)
    gate("g1", ok and wp[0] < TOL_CM and wd[0] < TOL_DEG,
         "IK against FK: %.4f cm (%s), %.3f deg (%s)" % (wp + wd))
    lens = ik_lenghts(rig)
    gate("g2", all(abs(v - 1.0) < 1e-9 for pair in lens.values() for v in pair),
         "a rotations take changes no IK length: %s" % sorted(lens.items()))

print("\n%d gate(s) failed: %s" % (len(FAILS), ", ".join(FAILS)) if FAILS else "\nall gates passed")
