"""Creep 2's rig of three cut pieces with Arm R / Head switches on Main - mayapy standalone.

    mayapy verify_creep2_split_rig.py <clip .fbx>

Spec: docs/superpowers/specs/2026-10-27-creep2-split-rig-switches-design.md
"""
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
sys.path.insert(0, PLUGIN)
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:                                                   # noqa: BLE001
        pass
cmds.undoInfo(state=True, infinity=True)

from maya_scenesetup import catalog, character, deletion  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_uebridge import animexport  # noqa: E402

CLIP = sys.argv[1].replace("\\", "/")
SPLIT = "C:/!!!Work/Animations/Rigs/Characters/Creep_Split"
PIECES = (("Creep2_Body", "Creep_Body.fbx", None), ("Creep2_ArmR", "Creep_Arm_R.fbx", "armR"),
          ("Creep2_Head", "Creep_Head.fbx", "head"))
FAILS = []


def gate(name, ok, msg=""):
    print("%s %s %s" % ("PASS" if ok else "FAIL", name, msg))
    if not ok:
        FAILS.append(name)


def leaf(p):
    return p.split("|")[-1].split(":")[-1]


def points(transform):
    return om.MFnMesh(om.MSelectionList().add(transform).getDagPath(0)).getPoints(om.MSpace.kWorld)


def evaluate(t):
    cmds.currentTime(t + 1)
    cmds.currentTime(t)


def shown(node):
    p = cmds.ls(node, long=True)[0]
    while p:
        if not cmds.getAttr(p + ".visibility"):
            return False
        p = p.rpartition("|")[0]
    return True


def import_fbx(path, ns):
    cmds.namespace(add=":" + ns)
    cmds.namespace(set=":" + ns)
    mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
    mel.eval('FBXImport -f "%s";' % path)
    cmds.namespace(set=":")


cmds.file(new=True, force=True)
character.add_character(catalog.character_by_key("Creep2_Rig"))
rig = [r for r in maya_rigs.rigs() if r.namespace.startswith("Creep2_Rig")][0]
ns = rig.namespace
geo = cmds.listRelatives("%s:Geometry" % ns, children=True) or []
gate("1 three pieces, no whole mesh", sorted(leaf(g) for g in geo) == sorted(p[0] for p in PIECES), str(geo))
for piece, fbx, switch in PIECES:
    import_fbx("%s/%s" % (SPLIT, fbx), "ref_" + piece)
    src = [cmds.listRelatives(s, parent=True, fullPath=True)[0]
           for s in cmds.ls("ref_%s:*" % piece, type="mesh", long=True, noIntermediate=True)][0]
    a, b = points("%s:%s" % (ns, piece)), points(src)
    off = max(a[i].distanceTo(b[i]) for i in range(len(a))) if len(a) == len(b) else -1
    gate("1 %s on its FBX at the bind" % piece, 0 <= off < 1e-3, "%d vertices, %.2e cm" % (len(a), off))

main = rig.main
for piece, fbx, switch in PIECES:
    if not switch:
        continue
    plug = main + "." + switch
    keyable = cmds.getAttr(plug, keyable=True) and cmds.getAttr(plug) == 1
    cmds.setAttr(plug, 0)
    others = [p for p, _f, _s in PIECES if p != piece]
    ok = not shown("%s:%s" % (ns, piece)) and all(shown("%s:%s" % (ns, o)) for o in others)
    cmds.setAttr(plug, 1)
    gate("2 Main.%s off hides only %s" % (switch, piece), keyable and ok and shown("%s:%s" % (ns, piece)))
cmds.setKeyframe(main, attribute="armR", time=19, value=1)
cmds.setKeyframe(main, attribute="armR", time=20, value=0)
evaluate(19)
at19 = shown("%s:Creep2_ArmR" % ns)
evaluate(20)
at20 = shown("%s:Creep2_ArmR" % ns)
gate("2 a key at 20: shown at 19, hidden at 20", at19 and not at20)

# the retarget: each piece where its FBX's own skin puts it with its joints on the rig's bones
import_fbx(CLIP, "clip")
src_root = min((j for j in cmds.ls("clip:*", type="joint", long=True)
                if not cmds.listRelatives(j, parent=True, type="joint")), key=lambda j: j.count("|"))
joints = cmds.ls(src_root, dag=True, type="joint", long=True)
first = cmds.findKeyframe(joints, which="first")
last = cmds.findKeyframe(joints, which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
cmds.currentTime(first)
cmds.select(rig.main, src_root)
ok, text = rr.run_retarget()
gate("3 retargeted", ok, (text or "").splitlines()[0][:160])
game = dict((leaf(j), j) for j in cmds.ls(rig.skeleton_root, dag=True, type="joint", long=True))
for piece, fbx, switch in PIECES:
    ref_joints = cmds.ls("ref_%s:*" % piece, type="joint", long=True)
    for j in ref_joints:
        if leaf(j) in game and leaf(j) not in ("weapon_r", "weapon_l"):
            cmds.parentConstraint(game[leaf(j)], j, maintainOffset=False)   # the binds are equal
src = [cmds.listRelatives(s, parent=True, fullPath=True)[0]
       for s in cmds.ls("ref_*:*", type="mesh", long=True, noIntermediate=True)]
worst = dict((p[0], 0.0) for p in PIECES)
for t in [round(first + (last - first) * k / 4.0) for k in range(5)]:
    evaluate(t)
    for piece, fbx, switch in PIECES:
        ref = [s for s in src if s.split("|")[1].startswith("ref_%s:" % piece) or ("ref_%s:" % piece) in s][0]
        a, b = points("%s:%s" % (ns, piece)), points(ref)
        worst[piece] = max(worst[piece], max(a[i].distanceTo(b[i]) for i in range(len(a))))
for piece in worst:
    gate("3 %s under the take on its FBX's own skin" % piece, worst[piece] < 1e-3, "%.2e cm" % worst[piece])
keys = cmds.keyframe(main, attribute="armR", q=True, timeChange=True) or []
gate("3 a new take: the switch's keys went with the old one, the arm shown again",
     not keys and cmds.getAttr(main + ".armR") and shown("%s:Creep2_ArmR" % ns), str(keys))

# the export: bones only
out = os.path.join(os.environ.get("TEMP", "."), "creep2_split_export.fbx").replace("\\", "/")
try:
    print("   ", str(animexport.export_hierarchy(out, root=rig.skeleton_root))[:160])
    cmds.file(new=True, force=True)
    import_fbx(out, "chk")
    gate("4 the export: 93 joints, no mesh", len(cmds.ls("chk:*", type="joint")) == 93
         and not cmds.ls("chk:*", type="mesh"), "%d joints" % len(cmds.ls("chk:*", type="joint")))
except Exception as exc:                                                # noqa: BLE001
    gate("4 the export", False, repr(exc))

# Delete character takes all three
cmds.file(new=True, force=True)
character.add_character(catalog.character_by_key("Creep2_Rig"))
rig = maya_rigs.rigs()[0]
print("   ", deletion.delete_selected(["%s:Creep2_ArmR" % rig.namespace], confirm=lambda *a, **k: True))
left = cmds.ls("*:Creep2_*", type="transform") + cmds.ls("Creep2_*", type="transform")
gate("5 Delete character takes all three", not left and not maya_rigs.rigs(), str(left))
print("%d failed: %s" % (len(FAILS), FAILS))
