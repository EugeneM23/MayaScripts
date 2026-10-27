"""Standalone gates for the second Creep's PARTS: «Creep 2 Arm R» and «Creep 2 Head», rig and skeleton.

    mayapy verify_creep_parts.py <clip .fbx> [<clip .fbx> ...]

mayapy STANDALONE, 2026-10-27 (spec docs/superpowers/specs/2026-10-27-creep-arm-head-parts-design.md).
Per clip, in a new scene, the four rows added through Add Character, then:

1. the rows, their portraits, the Auto card leaving the parts out;
2. each rig: own namespace, no left arm, its skin at its bind, `skeldarPartAnchor` + PartAnchor;
3. FK as on Manny: an FK control translated moves its game bone by as much (the bone stretches);
4. the clip through the Retarget button's own function onto each rig: every mapped game bone turns
   from its first frame as the clip's bone does (W0^-1 W, the constant rest offset cancels), RootX_M's
   anchor moves as the clip's chest (spine_05) does, root takes the clip's root motion; the other rig
   unmoved; for a clip that is the Creep 2's own (a twin: Auto squash & stretch, exact) every bone also
   on the clip's world matrix;
5. the clip onto each part SKELETON (`skeletonimport.transfer`): the top bone where the clip's is.
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

sys.path.insert(0, "C:/!!!Work/MayaScripts/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:                                                   # noqa: BLE001
        pass
FAILS = []


def gate(n, ok, msg):
    print("%s gate %s: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def wm(n, t=None):
    if t is not None:
        cmds.currentTime(t)
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def ang(a, b):
    q = om.MTransformationMatrix(a).rotation(asQuaternion=True).inverse() * \
        om.MTransformationMatrix(b).rotation(asQuaternion=True)
    return math.degrees(2 * math.acos(min(1.0, abs(q.w))))


def pos(m):
    return om.MVector(m.getElement(3, 0), m.getElement(3, 1), m.getElement(3, 2))


def bones_of(root):
    return dict((p.split("|")[-1].split(":")[-1], p)
                for p in [root] + (cmds.listRelatives(root, ad=True, type="joint", fullPath=True) or []))


def import_fbx(path, ns):
    before = set(cmds.ls(long=True, dag=True))
    cmds.namespace(add=ns)
    cmds.namespace(set=":" + ns)
    mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
    mel.eval('FBXImport -f "%s";' % path)
    cmds.namespace(set=":")
    return [n for n in cmds.ls(long=True, dag=True) if n not in before]


from maya_scenesetup import catalog, character  # noqa: E402
import maya_rigs  # noqa: E402
import maya_asretarget as ar  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_uebridge import skeletonimport  # noqa: E402

ARM_BONES = ("clavicle_r", "upperarm_r", "lowerarm_r", "hand_r", "middle_02_r", "thumb_03_r", "weapon_r")
HEAD_BONES = ("neck_01", "neck_02", "head")
rows = dict((k, catalog.character_by_key(k)) for k in
            ("Creep2_ArmR_Rig", "Creep2_Head_Rig", "Creep2_ArmR", "Creep2_Head"))
gate("1a", all(rows.values()) and all(r.part == "spine_05" for r in rows.values())
     and all(os.path.isfile(catalog.portrait_path(m)) for m in ("Creep2_ArmR", "Creep2_Head")),
     "the four rows, part = spine_05, two portraits")
from maya_uebridge import autoimport  # noqa: E402
src = open(autoimport.__file__, encoding="utf-8").read()
gate("1b", "if not getattr(entry, \"part\", \"\")" in src, "the Auto card leaves parts out")

for n_clip, clip in enumerate(sys.argv[1:]):
    clip = clip.replace("\\", "/")
    print("== clip", os.path.basename(clip))
    cmds.file(new=True, force=True)
    for key in rows:
        print("   ", character.add_character(rows[key]).splitlines()[0])
    # a second scene may number the namespaces (mayaUsd keeps the first one alive): by prefix
    rigs = maya_rigs.rigs()
    arm = ([r for r in rigs if r.namespace.startswith("Creep2_ArmR_Rig")] or [None])[0]
    head = ([r for r in rigs if r.namespace.startswith("Creep2_Head_Rig")] or [None])[0]
    gate("2a", arm and head and not cmds.ls(arm.namespace + ":*_L", type="joint")
         and ar.part_anchor(arm)[0] == "spine_05" and ar.part_anchor(head)[0] == "spine_05",
         "both rigs, in their namespaces, no left arm, anchored on spine_05")
    A, H = bones_of(arm.skeleton_root), bones_of(head.skeleton_root)
    # Manny's whole skeleton since 2026-10-27 (the part's mesh on its own bones, the rest at the bind)
    gate("2b", len(A) == 93 and len(H) == 93, "the game skeletons: arm %d, head %d joints" % (len(A), len(H)))
    if n_clip == 0:
        socket = [0.9023638608, -0.3496252732, 0.2519985282, 0.0, 0.3490667668, 0.9358437785, 0.0484502887, 0.0,
                  -0.2527707062, 0.044244523, 0.9665141917, 0.0, -9.8019504547, -4.6126813889, 1.0132220984, 1.0]
        for label, root in (("rig", arm.skeleton_root), ("skeleton", [r for r in skeletonimport.bare_roots()
                                                                      if "Arm R" in skeletonimport.skeleton_label(r)][0])):
            B = bones_of(root)
            rel = wm(B["weapon_r"]) * wm(B["hand_r"]).inverse()
            gate("2c", max(abs(x - y) for x, y in zip(list(rel), socket)) < 1e-5,
                 "the arm %s's weapon_r on Creep 2's UE socket in hand_r (%.2g)"
                 % (label, max(abs(x - y) for x, y in zip(list(rel), socket))))
        worst = 0.0
        for sc in cmds.ls(type="skinCluster"):
            for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
                src_ = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
                if src_:
                    m_ = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src_[0])
                    worst = max(worst, max(abs(x - y) for x, y in zip(list(m_), list(om.MMatrix()))))
        gate("2d", worst < 1e-3, "every part's skin at its bind (%.2g)" % worst)
        for rig, ctrl, bone, below in ((arm, "FKShoulder_R", "upperarm_r", "hand_r"), (head, "FKNeck_M", "neck_01", "head")):
            B = bones_of(rig.skeleton_root)
            c = "%s:%s" % (rig.namespace, ctrl)
            p0, q0 = pos(wm(B[bone])), pos(wm(B[below]))
            cmds.setAttr(c + ".tx", cmds.getAttr(c + ".tx") + 5.0)
            cmds.currentTime(1); cmds.currentTime(0)
            d1, d2 = (pos(wm(B[bone])) - p0).length(), (pos(wm(B[below])) - q0).length()
            cmds.setAttr(c + ".tx", cmds.getAttr(c + ".tx") - 5.0)
            gate("3", abs(d1 - 5.0) < 1e-3 and abs(d2 - 5.0) < 1e-3,
                 "%s tx +5 moves %s %.4f and %s %.4f (Manny's way)" % (ctrl, bone, d1, below, d2))

    nodes = import_fbx(clip, "clip")
    src_root = min((j for j in nodes if cmds.nodeType(j) == "joint" and not cmds.listRelatives(j, parent=True, type="joint")),
                   key=lambda j: j.count("|"))
    S = bones_of(src_root)
    first = cmds.findKeyframe(list(S.values()), which="first")
    last = cmds.findKeyframe(list(S.values()), which="last")
    cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
    frames = sorted(set([first, last] + [first + (last - first) * k / 5.0 for k in range(1, 5)]))
    frames = [round(f) for f in frames]
    for rig, names, other in ((arm, ARM_BONES, head), (head, HEAD_BONES, arm)):
        B = bones_of(rig.skeleton_root)
        still = dict((p, wm(p)) for p in bones_of(other.skeleton_root).values())
        cmds.currentTime(first)
        cmds.select(rig.main, src_root)
        ok, text = rr.run_retarget()
        print("   ", text.splitlines()[0][:220])
        if not ok:
            gate("4-" + rig.namespace, False, "the retarget refused")
            continue
        anchor = ar.part_anchor(rig)[1]
        worst_d, worst_a, worst_twin, worst_root = 0.0, 0.0, 0.0, 0.0
        # AdvancedSkeleton's Shoulder / Elbow never roll (the twist joints take it - Manny's rig too):
        # those bones are judged by their places in the twin check, the rest whole
        r0 = dict((n, wm(B[n], first)) for n in names if n in S and n not in ("upperarm_r", "lowerarm_r"))
        s0 = dict((n, wm(S[n], first)) for n in r0)
        a0, c0 = wm(anchor, first), wm(S["spine_05"], first)
        for f in frames:
            for n in names:
                if n not in S:
                    continue
                rw, sw = wm(B[n], f), wm(S[n], f)
                if n in s0:
                    worst_d = max(worst_d, ang(r0[n].inverse() * rw, s0[n].inverse() * sw))
                worst_twin = max(worst_twin, (pos(rw) - pos(sw)).length())
            aw, cw = wm(anchor, f), wm(S["spine_05"], f)
            worst_a = max(worst_a, ang(a0.inverse() * aw, c0.inverse() * cw),
                          ((pos(aw) - pos(a0)) - (pos(cw) - pos(c0))).length() / 100.0)
            worst_root = max(worst_root, (pos(wm(B["root"], f)) - pos(wm(S["root"], f))).length())
        moved = max(max(abs(a - b) for a, b in zip(list(m), list(wm(p)))) for p, m in still.items())
        twin = "twin, exact" in text
        gate("4-" + rig.namespace, worst_d < 0.05 and worst_a < 0.05 and worst_root < 1e-3 and moved < 1e-6,
             "bones turn as the clip's to %.4f deg; the anchor follows the chest to %.4f; root on the clip's root "
             "%.5f cm; the other rig moved %.2g; bones off the clip's world places %.3f cm (%s)"
             % (worst_d, worst_a, worst_root, moved, worst_twin, "twin" if twin else "rotations"))
        if twin:
            gate("4t-" + rig.namespace, worst_twin < 0.01, "a twin clip: every bone on the clip's world place, %.4f cm"
                 % worst_twin)

    for key, names in (("Creep2_ArmR", ARM_BONES), ("Creep2_Head", HEAD_BONES)):
        roots = [r for r in skeletonimport.bare_roots() if skeletonimport.skeleton_label(r).startswith(rows[key].label)]
        if not roots:
            gate("5-" + key, False, "no skeleton of %s found" % key)
            continue
        T = bones_of(roots[0])
        try:
            res = skeletonimport.transfer(src_root, roots[0], first, last)
        except Exception as e:                                          # noqa: BLE001
            gate("5-" + key, False, "transfer raised %s" % e)
            continue
        top = names[0]; print("    transfer:", res)
        off = max((pos(wm(T[top], f)) - pos(wm(S[top], f))).length() for f in frames)
        turn = max(ang(wm(T[n], f), wm(S[n], f)) for f in frames for n in names if n in S and n != "weapon_r")
        gate("5-" + key, off < 0.05 or turn < 0.05, "onto the skeleton (%s): %s on the clip's place to %.4f cm, bones "
             "turned as the clip's to %.4f deg" % (res.get("mode", "") if isinstance(res, dict) else "", top, off, turn))

print("\n%d failed: %s" % (len(FAILS), FAILS) if FAILS else "\nall gates passed")
