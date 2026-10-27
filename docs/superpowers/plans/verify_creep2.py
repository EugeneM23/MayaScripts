"""Standalone gates for the second Creep (assets/Creep2_Rig.ma, Creep2_Skeleton.ma) through Add Character.

    mayapy verify_creep2.py <a UE clip .fbx> [<sources/creep2/SK_Creep_skinned.FBX>]

mayapy STANDALONE, an empty scene, 2026-10-27 (spec docs/superpowers/specs/2026-10-27-creep2-design.md):

1. both rows in the catalog and the grid, untextured;
2. «Creep 2 [rig]» added twice and «Manny [rig]» once: each in its own namespace, Creep 2 marked
   rotation-only, its 93 joints (camera bones, weapon sockets), no script node, its skin at its bind,
   its controls at default, painted in a palette colour, one mesh in Group|Geometry;
3. the mesh where Unreal's own file puts it: every vertex of Creep2_Body against SK_Creep_skinned.FBX
   imported beside it, at the bind;
4. the weapon sockets: the fist's grip line along +Z in weapon_r, -Z in weapon_l (UE's, the plugin's
   one socket standard), and a Long Sword at zero grip in the right fist with its blade along it;
5. the clip retargeted onto the first Creep 2 through the Retarget button's own function: rotations
   only, the bones on the clip's orientations, Creep 2's lengths kept, the other two rigs unmoved;
6. the export: bones only, 93 joints, no mesh;
7. «Creep 2 [skeleton]»: its bones at the rig's bind, its mesh on Unreal's, skinned;
8. Delete character: nothing of a Creep 2 left;
9. the Auto card: which of our skeletons the clip's is (said, not gated: it depends on the clip).
"""
import math
import os
import sys
import tempfile

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
CLIP = sys.argv[1].replace("\\", "/")
SOURCE = (sys.argv[2] if len(sys.argv) > 2 else
          "C:/!!!Work/MayaScripts/sources/creep2/SK_Creep_skinned.FBX").replace("\\", "/")
FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def rot(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def ang(a, b):
    q = a.inverse() * b
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def pos(n):
    return om.MVector(cmds.xform(n, q=True, ws=True, t=True))


def points(transform):
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True, noIntermediate=True)[0]
    sel = om.MSelectionList(); sel.add(shape)
    return om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)


def bind_error(prefix):
    worst, n = 0.0, 0
    for sc in cmds.ls(type="skinCluster"):
        if not sc.startswith(prefix):
            continue
        n += 1
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if src:
                m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src[0])
                worst = max(worst, max(abs(m.getElement(r, c) - (r == c)) for r in range(4) for c in range(4)))
    return n, worst


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


cmds.file(new=True, force=True)
from maya_scenesetup import catalog, character, deletion, attach, bonedrive  # noqa: E402
import maya_rigs  # noqa: E402
import maya_asretarget as ar  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_uebridge import animexport  # noqa: E402

rig_row, skel_row = catalog.character_by_key("Creep2_Rig"), catalog.character_by_key("Creep2")
gate(1, rig_row and skel_row and catalog.character_for("Creep2", "rig") == rig_row
     and catalog.character_for("Creep2", "skeleton") == skel_row and not rig_row.textured and not skel_row.textured
     and os.path.isfile(catalog.portrait_path("Creep2")),
     "the rows %s / %s, the model's portrait %s" % (rig_row and rig_row.label, skel_row and skel_row.label,
                                                     os.path.basename(catalog.portrait_path("Creep2"))))

texts = [character.add_character(rig_row), character.add_character(rig_row),
         character.add_character(catalog.character_by_key("Manny_Rig"))]
for t in texts:
    print("   ", t.splitlines()[0])
rigs = dict((r.namespace, r) for r in maya_rigs.rigs())
gate(2, set(rigs) == {"Creep2_Rig", "Creep2_Rig1", "Manny_Rig"},
     "three rigs, each in its own namespace: %s" % sorted(rigs))
c, c2, manny = rigs.get("Creep2_Rig"), rigs.get("Creep2_Rig1"), rigs.get("Manny_Rig")
H, H2, M = bones_of(c.skeleton_root), bones_of(c2.skeleton_root), bones_of(manny.skeleton_root)
n_sk, err = bind_error("Creep2_Rig:")
geo = cmds.listRelatives(cmds.ls("Creep2_Rig:Geometry", long=True)[0], children=True) or []
mats = set()
for sg in cmds.listConnections(cmds.ls("Creep2_Rig:Creep2_BodyShape", long=True)[0], type="shadingEngine") or []:
    mats.update(cmds.listConnections(sg + ".surfaceShader") or [])
gate(3, ar.rotation_mode(c) and ar.rotation_mode(c2) and not ar.rotation_mode(manny) and len(H) == 93
     and all(b in H for b in ("camera_root", "camera_bone", "weapon_r", "weapon_l"))
     and not [s for s in cmds.ls(type="script") if s.startswith("Creep2_Rig")]
     and n_sk == 1 and err < 1e-3 and not ar.posed_controls(rig=c) and geo == ["Creep2_Rig:Creep2_Body"]
     and len(mats) == 1 and any(cmds.attributeQuery("skeldarColour", node=m, exists=True) for m in mats),
     "rotation-only, %d joints, no script node, skin at its bind (%.2e), controls at default, Geometry %s, "
     "worn %s" % (len(H), err, geo, sorted(mats)))

# the mesh where Unreal's own file puts it, at the bind
src_nodes = import_fbx(SOURCE, "ue")
src_mesh = [n for n in src_nodes if cmds.nodeType(n) == "transform"
            and cmds.listRelatives(n, shapes=True, type="mesh")][0]
a, b = points(src_mesh), points(cmds.ls("Creep2_Rig:Creep2_Body", long=True)[0])
worst_v = max(a[i].distanceTo(b[i]) for i in range(len(a))) if len(a) == len(b) else -1
src_j = dict((p.split("|")[-1].split(":")[-1], p) for p in src_nodes if cmds.nodeType(p) == "joint")
worst_j = max((pos(src_j[k]) - pos(H[k])).length() for k in src_j if k in H)
gate(4, len(a) == len(b) and 0 <= worst_v < 1e-3 and worst_j < 1e-3,
     "every one of %d vertices where SK_Creep_skinned.FBX has it (%.2e cm), every joint (%.2e cm)"
     % (len(b), worst_v, worst_j))
cmds.delete([n for n in src_nodes if cmds.objExists(n) and not cmds.listRelatives(n, parent=True)] or [])
cmds.namespace(removeNamespace="ue", deleteNamespaceContent=True)


def grip(B, side):
    v = (pos(B["index_01_" + side]) - pos(B["pinky_01_" + side])).normal()
    t = om.MTransformationMatrix(wm(B["weapon_" + side]))
    t.setTranslation(om.MVector(), om.MSpace.kTransform)
    return v * t.asMatrix().inverse()


gr, gl = grip(H, "r"), grip(H, "l")
sword = catalog.by_key("LongSword_02")
weapon, _note = attach.attach(sword, H["hand_r"], H["weapon_r"], (0, 0, 0), (0, 0, 0))
weapon = cmds.ls(weapon, long=True)[0]
sel = om.MSelectionList(); sel.add(cmds.listRelatives(weapon, shapes=True, fullPath=True, noIntermediate=True)[0])
local = om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kObject)
axis = max(range(3), key=lambda k: max(p[k] for p in local) - min(p[k] for p in local))
m = wm(weapon)
blade = om.MVector(m.getElement(axis, 0), m.getElement(axis, 1), m.getElement(axis, 2)).normal()
knuckles = (pos(H["index_01_r"]) - pos(H["pinky_01_r"])).normal()
off_line = math.degrees(math.acos(max(-1.0, min(1.0, blade * knuckles))))
gate(5, gr.z > 0.95 and gl.z < -0.95 and off_line < 20 and bonedrive.driving_weapon(H["weapon_r"]),
     "the grip line in weapon_r %s, weapon_l %s; a Long Sword at zero grip, its blade %.1f deg off the "
     "fist's grip line, driving weapon_r" % ([round(v, 3) for v in gr], [round(v, 3) for v in gl], off_line))
attach.detach(H["hand_r"], H["weapon_r"])

# the clip onto the first Creep 2
clip_nodes = import_fbx(CLIP, "clip")
src = min((j for j in clip_nodes if cmds.nodeType(j) == "joint" and not cmds.listRelatives(j, parent=True, type="joint")),
          key=lambda j: j.count("|"))
S = bones_of(src)
first, last = cmds.findKeyframe(list(S.values()), which="first"), cmds.findKeyframe(list(S.values()), which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
rest_t = dict((n, cmds.getAttr(p + ".translate")[0]) for n, p in H.items())
still = dict((p, wm(p)) for p in list(H2.values()) + list(M.values()))
cmds.select(cmds.ls("Creep2_Rig:Main")[0], src)
ok, text = rr.run_retarget()
print("   ", text.splitlines()[0][:200])
# AdvancedSkeleton's Shoulder / Elbow / Hip / Knee never roll - the twist joints take it (the rig's
# design, the first Creep's too) - so the limb bones are judged by where they point, the rest whole
POINT = ("upperarm_r", "lowerarm_l", "thigh_l", "calf_r")
WHOLE = ("pelvis", "spine_01", "spine_03", "spine_05", "neck_01", "head", "clavicle_l", "hand_l", "hand_r",
         "foot_l", "ball_r", "middle_02_r", "thumb_02_l")
worst_rot, worst_dir, worst_len, moved, worst_at = 0.0, 0.0, 0.0, 0.0, ""


def direction(B, k):
    child = [c for c in cmds.listRelatives(B[k], children=True, type="joint", fullPath=True) or []
             if "twist" not in c.split("|")[-1]][0]
    return (pos(child) - pos(B[k])).normal()


for t in range(int(first), int(last) + 1, max(1, int((last - first) / 12))):
    cmds.currentTime(t)
    for k in WHOLE:
        if k in S:
            a_ = ang(rot(wm(S[k])), rot(wm(H[k])))
            if a_ > worst_rot:
                worst_rot, worst_at = a_, "%s at %d" % (k, t)
    for k in POINT:
        d = direction(S, k) * direction(H, k)
        worst_dir = max(worst_dir, math.degrees(math.acos(max(-1.0, min(1.0, d)))))
    for n, p in H.items():
        if n not in ("root", "pelvis", "weapon_r", "weapon_l", "camera_root", "camera_bone") and not n.startswith("ik_"):
            worst_len = max(worst_len, (om.MVector(cmds.getAttr(p + ".translate")[0]) - om.MVector(rest_t[n])).length())
    moved = max(moved, max(max(abs(x - y) for x, y in zip(list(mm), list(wm(p)))) for p, mm in still.items()))
gate(6, ok and not cmds.objExists(ar.holder_of(c)) and worst_rot < 0.05 and worst_dir < 0.5
     and worst_len < 1e-3,
     "the Retarget button (%d..%d): ok=%s, on the clip's orientations to %.5f deg (worst %s), the limb bones "
     "pointing as the clip's to %.4f deg, Creep 2's lengths kept to %.6f cm"
     % (first, last, ok, worst_rot, worst_at, worst_dir, worst_len))
gate(7, moved < 1e-6, "the second Creep 2 and the Manny did not move: %.9f" % moved)

# which of our skeletons the clip's is (the Auto card) - said, not gated
try:
    from maya_uebridge import autoimport, skeletonmatch
    keys = [e.key for e in catalog.CHARACTERS if e.kind == "rig"]
    found = skeletonmatch.match(autoimport.clip_bones(src), skeletonmatch.load_templates(), keys)
    print("    the Auto card reads the clip as: %s" % (skeletonmatch.match_text(found) if found is not None else found))
    for sc in found.scores:
        print("      %-16s %.3f of %d bones" % (sc.key, sc.share, sc.count))
except Exception as exc:                                                # noqa: BLE001
    print("    the Auto card's reading: not available (%s)" % exc)

path = os.path.join(tempfile.gettempdir(), "skeldar_creep2_export.fbx").replace("\\", "/")
animexport.export_hierarchy(path, root=c.skeleton_root)
cmds.file(new=True, force=True)
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
mel.eval('FBXImport -f "%s";' % path)
gate(8, len(cmds.ls(type="joint")) == 93 and not cmds.ls(type="mesh"),
     "the export: %d joints, %d meshes" % (len(cmds.ls(type="joint")), len(cmds.ls(type="mesh"))))

# the skeleton row
cmds.file(new=True, force=True)
print("   ", character.add_character(skel_row).splitlines()[0])
roots = [r for r in cmds.ls(type="joint", long=True) if r.split("|")[-1].split(":")[-1] == "root"]
K = bones_of(roots[0])
n_sk, err = bind_error("")
meshes = [cmds.listRelatives(s, parent=True, fullPath=True)[0] for s in cmds.ls(type="mesh", noIntermediate=True, long=True)]
src_nodes = import_fbx(SOURCE, "ue")
src_mesh = [n for n in src_nodes if cmds.nodeType(n) == "transform" and cmds.listRelatives(n, shapes=True, type="mesh")][0]
a, b = points(src_mesh), points(meshes[0])
worst_v = max(a[i].distanceTo(b[i]) for i in range(len(a))) if len(a) == len(b) else -1
gate(9, len(K) == 93 and n_sk == 1 and err < 1e-3 and len(meshes) == 1 and 0 <= worst_v < 1e-3
     and not cmds.ls(type="constraint"),
     "Creep 2 [skeleton]: %d joints, no constraint, skin at its bind (%.2e), its mesh on Unreal's (%.2e cm)"
     % (len(K), err, worst_v))
cmds.delete([n for n in src_nodes if cmds.objExists(n) and not cmds.listRelatives(n, parent=True)] or [])
cmds.namespace(removeNamespace="ue", deleteNamespaceContent=True)

# Delete character, through the mesh
cmds.file(new=True, force=True)
character.add_character(rig_row)
ns = maya_rigs.rigs()[0].namespace
cmds.select(cmds.ls(ns + ":Creep2_Body")[0])
picked, unowned, _paths = deletion.selected_characters()
deletion.execute(deletion.plan(picked), len(unowned))
# Maya's own singletons the first import into a new scene makes inside the namespace (trap 158) are
# Maya's, not the character's: verify_delete_character.py excuses them the same way
MAYA_OWN = ("UsdDefaultRenderSettings", "UsdDefaultSettings", "shapeEditorManager", "poseInterpolatorManager")
left = [n for n in cmds.ls(long=True) if "Creep2" in n and cmds.nodeType(n) not in MAYA_OWN]
gate(10, not left and not cmds.ls(type="joint") and not cmds.ls(type="mesh"),
     "Delete character through the mesh leaves nothing of Creep 2: %s" % left[:6])

print("%s - %d gate(s) failed%s" % ("FAILURES" if FAILS else "checks passed", len(FAILS),
                                     (": %s" % FAILS) if FAILS else ""))
maya.standalone.uninitialize()
