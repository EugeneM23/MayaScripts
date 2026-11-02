"""Standalone gates for the Swordman (assets/Swordman_Rig.ma, Swordman_Skeleton.ma, his two weapons).

    mayapy verify_swordman.py <a UE clip .fbx>

mayapy STANDALONE, an empty scene, 2026-11-01 (the animator's own character on a 3ds Max Biped
skeleton: «перенесем на наш скелет (только сохраним пропорции) и сделаем риг и ретаргет ...
оружие должно быть в вепон боне»). Spec 2026-11-01-swordman-design.md.

 1. both rows in the catalog and the grid, textured, a portrait, a fire of his own;
 2. «Swordman [rig]» added: his own namespace, 55 game bones with OUR names, rotation-marked,
    22 position follows (an FK translation carries its bone), the skin at its bind, painted;
 3. the REWIRE: every body vertex where his own scene has it -- the skin was never re-bound;
 4. his proportions: all 22 of our segments the length his skeleton has them, at the bind;
 5. a UE clip through the Retarget button: the bones on the clip's orientations, HIS lengths
    unchanged -- the gate the whole job is for;
 6. a Manny beside him does not move;
 7. «Swordman Sword» at zero grip: every vertex where HIS hand holds it, driving weapon_r,
    the grip fields reading 0 0 0;
 8. «Swordman Shield» the same on weapon_l;
 9. both props at WORLD size -- his pelvis scales 2.54 and his props inherit it, so a rebind
    that forgets them ships a sword 1/2.54 too small (trap 86);
10. the export: 55 joints, no mesh, plain names;
11. «Swordman [skeleton]»: 55 joints, his one mesh at its bind, no constraint;
12. Delete character takes all of it, and one Ctrl+Z brings it back;
13. his own skeleton read by maya_skeletonmap: every pair right, left and right not swapped --
    with the PRE-FIX map as the control, so the gate can fail.
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

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:                                                   # noqa: BLE001
        pass
CLIP = sys.argv[1].replace("\\", "/")
SOURCE = (sys.argv[2] if len(sys.argv) > 2 else
          REPO + "/sources/swordman/Swordman_Scene.mb").replace("\\", "/")
BODY = "Cylinder003"            # his one skinned mesh, 268 vertices
PREFIX = "BaseFBXASC032Human"   # "Base Human" with the FBX space escape
PROPS = {"Swordman_Sword": ("Object014", "weapon_r", "hand_r"),
         "Swordman_Shield": ("Object013", "weapon_l", "hand_l")}
#  53 since 2026-11-02: his camera bones left the skeleton («кости камеры также можно
#  удалить»), so Camera Setup refuses on him as it does on the UE4 Mannequin.
JOINTS = 53
#  AdvancedSkeleton's fingers and its curl / spread dials, all out of his rig (2026-11-02)
FINGERS = ("IndexFinger", "MiddleFinger", "RingFinger", "PinkyFinger", "ThumbFinger")
FINGER_DIALS = ("Fingers_R", "Fingers_L")
CAMERA_BONES = ("camera_root", "camera_bone")
# our 55 bones against his, measured 2026-11-01 (make_swordman_source.py's PAIRS + UNSKINNED)
PAIRS = {"pelvis": "Pelvis", "spine_05": "Ribcage", "head": "Head",
         "clavicle_l": "LCollarbone", "upperarm_l": "LUpperarm",
         "lowerarm_l": "LForearm", "hand_l": "LPalm",
         "clavicle_r": "RCollarbone", "upperarm_r": "RUpperarm",
         "lowerarm_r": "RForearm", "hand_r": "RPalm",
         "thigh_l": "LThigh", "calf_l": "LCalf", "foot_l": "LFoot",
         "thigh_r": "RThigh", "calf_r": "RCalf", "foot_r": "RFoot",
         "spine_01": "Spine1", "spine_02": "Spine2", "spine_03": "Spine3",
         "spine_04": "Spine4", "neck_01": "Neck1", "neck_02": "Neck2"}
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


def points(transform, space=om.MSpace.kWorld):
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True, noIntermediate=True)[0]
    sel = om.MSelectionList()
    sel.add(shape)
    pts = om.MFnMesh(sel.getDagPath(0)).getPoints(space)
    return [om.MPoint(p) for p in pts]          # fresh: the MPointArray's own dangle


def span(pts):
    """The model's own size, in cm: the distance between its two farthest points.

    Not an axis-aligned extent: his shield carries his dialled grip in its points
    (2026-11-02), so it stands turned against his file's copy and only a measure
    blind to rotation compares the two.
    """
    return max((pts[i].distanceTo(pts[j])
                for i in range(len(pts)) for j in range(i + 1, len(pts))), default=0.0)


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
                worst = max(worst, max(abs(m.getElement(r, c) - (r == c))
                                       for r in range(4) for c in range(4)))
    return n, worst


def bones_of(root):
    return dict((p.split("|")[-1].split(":")[-1], p)
                for p in [root] + (cmds.listRelatives(root, ad=True, type="joint",
                                                      fullPath=True) or []))


def import_fbx(path, ns):
    before = set(cmds.ls(long=True, dag=True))
    cmds.namespace(add=ns)
    cmds.namespace(set=":" + ns)
    mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
    mel.eval('FBXImport -f "%s";' % path)
    cmds.namespace(set=":")
    return [n for n in cmds.ls(long=True, dag=True) if n not in before]


def import_his(ns):
    """His own scene beside ours, AT ITS BIND, in `ns`. Returns the nodes it made.

    His file is saved in whatever pose it was left in; the bind is the skinCluster's own
    (`bindPreMatrix[i].inverse()`, trap 176 -- never the dagPose, which is stale on this
    character). Parents first: each joint's world matrix is then set absolutely.
    """
    before = set(cmds.ls(long=True, dag=True))
    cmds.file(SOURCE, i=True, namespace=ns, executeScriptNodes=False)
    made = [n for n in cmds.ls(long=True, dag=True) if n not in before]
    want = {}
    for sc in cmds.ls(ns + ":*", type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            j = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if j:
                want[cmds.ls(j[0], long=True)[0]] = om.MMatrix(
                    cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))).inverse()
    for path in sorted(want, key=lambda p: p.count("|")):
        cmds.xform(path, worldSpace=True, matrix=list(want[path]))
    return made


def leaf_of(ns, leaf):
    found = [n for n in cmds.ls(ns + ":*", long=True, dag=True)
             if n.split("|")[-1].split(":")[-1] == leaf]
    return found[0] if found else None


def his_bone(ns, ours):
    """Our bone's name in HIS skeleton, through the Base Human prefix."""
    name = PAIRS.get(ours)
    return leaf_of(ns, PREFIX + name) if name else None


def drop(nodes, ns):
    """His nodes and his namespace out, mayaUsd's locked furniture included (trap 164)."""
    tops = [n for n in nodes if cmds.objExists(n) and not cmds.listRelatives(n, parent=True)]
    if tops:
        cmds.delete(tops)
    locked = [n for n in cmds.ls(ns + ":*") if cmds.lockNode(n, q=True, lock=True)[0]]
    if locked:
        cmds.lockNode(locked, lock=False)
    cmds.namespace(removeNamespace=ns, deleteNamespaceContent=True)


cmds.file(new=True, force=True)
from maya_scenesetup import catalog, character, deletion, attach, bonedrive  # noqa: E402
from maya_scenesetup import weaponspace, camera, skeleton, window  # noqa: E402
from maya_scenesetup import grips, equip  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swordman_seats  # noqa: E402
import maya_charfire  # noqa: E402
import maya_rigs  # noqa: E402
import maya_asretarget as ar  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
import maya_skeletonmap as sm  # noqa: E402
from maya_uebridge import animexport  # noqa: E402

# ------------------------------------------------------------------ 1: the rows
rig_row = catalog.character_by_key("Swordman_Rig")
skel_row = catalog.character_by_key("Swordman")
portrait = catalog.portrait_path("Swordman")
in_grid = "Swordman" in [m.key for m in catalog.MODELS]
fire = maya_charfire.fire_of("Swordman")
gate(1, rig_row and skel_row and in_grid and rig_row.textured and skel_row.textured
     and not rig_row.part and not skel_row.part
     and catalog.character_for("Swordman", "rig") == rig_row
     and catalog.character_for("Swordman", "skeleton") == skel_row
     and os.path.isfile(portrait) and fire in maya_charfire.PALETTES,
     "the rows %s / %s, in the grid, textured, a portrait (%s), fire %r"
     % (rig_row and rig_row.label, skel_row and skel_row.label, os.path.isfile(portrait), fire))

# ------------------------------------------------------------------ 2: the rig
print("   ", character.add_character(rig_row).splitlines()[0])
rig = maya_rigs.rigs()[0] if len(maya_rigs.rigs()) == 1 else None
NS = rig.namespace + ":" if rig else "Swordman_Rig:"
H = bones_of(rig.skeleton_root) if rig else {}
follows = len([p for p in H.values()
               if cmds.listRelatives(p, children=True, type="pointConstraint")])
n_sk, err = bind_error(NS)
mesh = cmds.ls(NS + "Swordman_Body", long=True)
mats = set()
for sg in cmds.listConnections(cmds.ls(NS + "Swordman_BodyShape", long=True) or [],
                               type="shadingEngine") or []:
    mats.update(cmds.listConnections(sg + ".surfaceShader") or [])
textured = any(cmds.attributeQuery("skeldarTexture", node=m, exists=True) for m in mats)
gate(2, rig and len(H) == JOINTS and set(PAIRS).issubset(H) and ar.rotation_mode(rig)
     and follows == 22 and n_sk == 1 and err < 1e-3 and len(mesh) == 1
     and not ar.posed_controls(rig=rig) and textured,
     "%s: %d game bones (ours), rotation-only, %d position follows, skin at its bind "
     "(%.2e), one mesh, textured %s"
     % (rig and rig.namespace, len(H), follows, err, textured))

# ------------------------------------------------------------- 3: the rewire
his = import_his("src")
his_body = leaf_of("src", BODY)
mine, theirs = points(mesh[0]), points(his_body)
worst_v = max(mine[i].distanceTo(theirs[i]) for i in range(len(mine))) \
    if len(mine) == len(theirs) else -1.0
gate(3, len(mine) == len(theirs) and 0 <= worst_v < 1e-3,
     "every one of %d body vertices where HIS scene has it, worst %.2e cm "
     "(the skin is rewired onto our bones, never re-bound)" % (len(mine), worst_v))

# -------------------------------------------------------- 4: his proportions
worst_len, worst_at, worst_skin = 0.0, "", 0.0
MIDLINE = ("spine_01", "spine_02", "spine_03", "spine_04", "neck_01", "neck_02")
checked = 0
for ours, parent_his in PAIRS.items():
    kids = [k for k in cmds.listRelatives(H[ours], children=True, type="joint", fullPath=True) or []
            if "twist" not in k.split("|")[-1] and "ik_" not in k.split("|")[-1]]
    hp = his_bone("src", ours)
    if not kids or not hp:
        continue
    for kid in kids:
        kid_leaf = kid.split("|")[-1].split(":")[-1]
        his_kid = his_bone("src", kid_leaf)
        if not his_kid:
            continue
        d = abs((pos(kid) - pos(H[ours])).length() - (pos(his_kid) - pos(hp)).length())
        checked += 1
        if d > worst_len:
            worst_len, worst_at = d, "%s->%s" % (ours, kid_leaf)
        if ours not in MIDLINE and kid_leaf not in MIDLINE:
            worst_skin = max(worst_skin, d)
gate(4, checked >= 20 and worst_len < 5e-3 and worst_skin < 1e-4,
     "his proportions: %d of our segments the length HIS skeleton has them -- every skinned one "
     "to %.2e cm, the six midline joints to %.2e (%s: they come off his dagPose up to 0.1548 cm "
     "off x = 0 and go back on it, trap 299)" % (checked, worst_skin, worst_len, worst_at))
drop(his, "src")

# --------------------------------------------- 5 + 6: the clip, and a Manny
print("   ", character.add_character(catalog.character_by_key("Manny_Rig")).splitlines()[0])
manny = [r for r in maya_rigs.rigs() if r.namespace != rig.namespace][0]
still = dict((p, wm(p)) for p in bones_of(manny.skeleton_root).values())
rest_t = dict((n, cmds.getAttr(p + ".translate")[0]) for n, p in H.items())

clip_nodes = import_fbx(CLIP, "clip")
src_root = min((j for j in clip_nodes if cmds.nodeType(j) == "joint"
                and not cmds.listRelatives(j, parent=True, type="joint")),
               key=lambda j: j.count("|"))
S = bones_of(src_root)
all_src = list(S.values())
first = cmds.findKeyframe(all_src, which="first")
last = cmds.findKeyframe(all_src, which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
cmds.select(maya_rigs.node(rig, "Main"), src_root)
ok, text = rr.run_retarget()
print("   ", text.splitlines()[0][:200])

# AdvancedSkeleton's Shoulder / Elbow / Hip / Knee never roll - the twist joints take it - so the
# limb bones are judged by where they POINT and the rest whole (Creep 2's rule, his rig's too).
POINT = ("upperarm_r", "lowerarm_l", "thigh_l", "calf_r")
WHOLE = ("pelvis", "spine_01", "spine_03", "spine_05", "neck_01", "head",
         "clavicle_l", "hand_l", "hand_r", "foot_l")
worst_rot, worst_dir, worst_stretch, moved = 0.0, 0.0, 0.0, 0.0
rot_at, dir_at, stretch_at = "", "", ""


def direction(B, k):
    kids = [c for c in cmds.listRelatives(B[k], children=True, type="joint", fullPath=True) or []
            if "twist" not in c.split("|")[-1]]
    return (pos(kids[0]) - pos(B[k])).normal() if kids else om.MVector(0, 1, 0)


step = max(1, int((last - first) / 12))
for t in range(int(first), int(last) + 1, step):
    cmds.currentTime(t)
    for k in WHOLE:
        if k in S:
            a_ = ang(rot(wm(S[k])), rot(wm(H[k])))
            if a_ > worst_rot:
                worst_rot, rot_at = a_, "%s at %d" % (k, t)
    for k in POINT:
        if k in S:
            d = direction(S, k) * direction(H, k)
            a_ = math.degrees(math.acos(max(-1.0, min(1.0, d))))
            if a_ > worst_dir:
                worst_dir, dir_at = a_, "%s at %d" % (k, t)
    for n, p in H.items():
        if n in ("root", "pelvis", "weapon_r", "weapon_l", "camera_root", "camera_bone") \
                or n.startswith("ik_"):
            continue
        d_ = (om.MVector(cmds.getAttr(p + ".translate")[0]) - om.MVector(rest_t[n])).length()
        if d_ > worst_stretch:
            worst_stretch, stretch_at = d_, "%s at %d" % (n, t)
    moved = max(moved, max(max(abs(x - y) for x, y in zip(list(mm), list(wm(p))))
                           for p, mm in still.items()))
# a rotations take keeps the lengths as far as the AS rig keeps its own: the game bones
# follow their AS joints by point constraint, and Manny's own foot moves 0.10 cm in his own
# rig under the same rule (CLAUDE.md, the Creep 2 gate's 0.05)
gate(5, ok and not cmds.objExists(ar.holder_of(rig)) and worst_rot < 0.05 and worst_dir < 0.5
     and worst_stretch < 1e-3,
     "the Retarget button (%d..%d): on the clip's orientations to %.5f deg (worst %s), the limb "
     "bones pointing as the clip's to %.4f deg (worst %s), HIS lengths unchanged to %.2e cm "
     "(worst %s)" % (first, last, worst_rot, rot_at, worst_dir, dir_at, worst_stretch, stretch_at))
gate(6, moved < 1e-6, "the Manny beside him did not move: %.9f" % moved)

# -------------------------------------------------- 7 + 8 + 9: his two props
cmds.file(new=True, force=True)
print("   ", character.add_character(rig_row).splitlines()[0])
rig = maya_rigs.rigs()[0]
H = bones_of(rig.skeleton_root)
his = import_his("src")
sizes = {}
def rigid(matrix):
    """`matrix` without its scale: the rig's own chain leaves 4e-6 of it on a weapon."""
    got = om.MTransformationMatrix(matrix)
    out = om.MTransformationMatrix()
    out.setRotation(got.rotation(asQuaternion=False))
    out.setTranslation(got.translation(om.MSpace.kTransform), om.MSpace.kTransform)
    return out.asMatrix()


def world(node):
    return om.MMatrix(cmds.xform(node, query=True, worldSpace=True, matrix=True))


for n, (key, (his_mesh, bone, hand)) in enumerate(sorted(PROPS.items()), start=7):
    entry = catalog.by_key(key)
    side = swordman_seats.HANDS[key][0]
    #  the press the animator uses, not `attach` with an explicit zero grip: Weapons > Add
    #  and the inventory both go through `equip.to_hand`, and for a LEFT hand that applies
    #  the mirror grip `grips.for_hand` computes -- which is why his shield stood ~171 deg
    #  away until his seat was folded into the points (2026-11-02).
    #  the frame the asset's points are cut in: the socket turn on the bone AT REST,
    #  read before the Add (the bone follows the weapon afterwards)
    seat = om.MMatrix(bonedrive.framed(bonedrive.socket_frame(entry.frame),
                                       cmds.getAttr(H[bone] + ".worldMatrix[0]")))
    hand_world = world(H[hand])
    said = equip.to_hand(rig.skeleton_root, side, entry)
    node = bonedrive.driving_weapon(H[bone])
    node = cmds.ls(node, long=True)[0] if node else None
    mine = points(node) if node else []
    theirs = points(leaf_of("src", his_mesh))
    sizes[key] = (span(mine), span(theirs),
                  span(points(node, om.MSpace.kObject)) if node else 0.0)
    #  the same model placed where HE set it: his matrix is in the hand's frame
    want = om.MMatrix(swordman_seats.IN_HAND[key]) * hand_world
    his_seat = [om.MPoint(q) * seat.inverse() * want for q in theirs]
    worst_p = max(mine[i].distanceTo(his_seat[i]) for i in range(len(mine))) \
        if len(mine) == len(theirs) else -1.0
    off_src = max(mine[i].distanceTo(theirs[i]) for i in range(len(mine))) \
        if len(mine) == len(theirs) else -1.0
    driven = bonedrive.driving_weapon(H[bone])
    gate(n, node and 0 <= worst_p < 1e-3
         and weaponspace.holding_hand(node) == H[hand]
         and driven and cmds.ls(driven, long=True)[0] == node,
         "%s through Weapons > Add: every one of %d vertices where HE set it on his own rig "
         "(%.2e cm; %.1f cm from where his source file held it), in %s, driving %s | %s"
         % (entry.label, len(mine), worst_p, off_src, hand, bone, said.splitlines()[0]))

# his props hang under a chain whose pelvis scales 2.54, so their size is INHERITED, not in
# their points: a rebind that drops the scale ships them 1/2.54 small and nothing of the
# geometry says so (trap 86). The model's own extent is 117.2 / 65.4, never 46.1 / 25.7.
sword_ok = sizes["Swordman_Sword"][2] > 100 and \
    abs(sizes["Swordman_Sword"][0] - sizes["Swordman_Sword"][1]) < 1e-3
shield_ok = sizes["Swordman_Shield"][2] > 55 and \
    abs(sizes["Swordman_Shield"][0] - sizes["Swordman_Shield"][1]) < 1e-3
gate(9, sword_ok and shield_ok,
     "at WORLD size (trap 86), whatever the seat turned: the sword's own model is %.1f cm "
     "and stands as wide as his (%.1f against %.1f), the shield %.1f cm (%.1f against %.1f)"
     % (sizes["Swordman_Sword"][2], sizes["Swordman_Sword"][0], sizes["Swordman_Sword"][1],
        sizes["Swordman_Shield"][2], sizes["Swordman_Shield"][0], sizes["Swordman_Shield"][1]))
drop(his, "src")

# ------------------------------------------------------------- 10: the export
path = os.path.join(tempfile.gettempdir(), "skeldar_swordman_export.fbx").replace("\\", "/")
animexport.export_hierarchy(path, root=rig.skeleton_root)
cmds.file(new=True, force=True)
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
mel.eval('FBXImport -f "%s";' % path)
out = cmds.ls(type="joint")
gate(10, len(out) == JOINTS and not cmds.ls(type="mesh") and not any(":" in j for j in out),
     "the export: %d joints, %d meshes, plain names %s"
     % (len(out), len(cmds.ls(type="mesh")), not any(":" in j for j in out)))

# ----------------------------------------------- 11 + 12: the skeleton row
cmds.file(new=True, force=True)
print("   ", character.add_character(skel_row).splitlines()[0])
joints = cmds.ls(type="joint", long=True)
n_sk, err = bind_error("")
meshes = [cmds.listRelatives(s, parent=True, fullPath=True)[0]
          for s in cmds.ls(type="mesh", noIntermediate=True, long=True)]
his = import_his("src")
mine = points(meshes[0]) if meshes else []
theirs = points(leaf_of("src", BODY))
worst_v = max(mine[i].distanceTo(theirs[i]) for i in range(len(mine))) \
    if len(mine) == len(theirs) else -1.0
gate(11, len(joints) == JOINTS and n_sk == 1 and err < 1e-3 and len(meshes) == 1
     and 0 <= worst_v < 1e-3 and not cmds.ls(type="constraint"),
     "Swordman [skeleton]: %d joints, %d mesh, skin at its bind (%.2e), on his own (%.2e cm), "
     "no constraint" % (len(joints), len(meshes), err, worst_v))
drop(his, "src")

before = set(cmds.ls(long=True))
cmds.select(meshes[0])
picked, unowned, _paths = deletion.selected_characters()
cmds.undoInfo(state=True, infinity=True)
print("   ", str(deletion.execute(deletion.plan(picked), len(unowned)))[:160])
gone = not cmds.ls(type="joint") and not cmds.ls(type="mesh")
cmds.undo()
back = len(cmds.ls(type="joint")) == JOINTS and len(cmds.ls(type="mesh", noIntermediate=True)) == 1
gate(12, gone and back, "Delete character: %s; one Ctrl+Z brings him back: %d joints, %d meshes"
     % ("nothing left" if gone else "LEFT OVER", len(cmds.ls(type="joint")),
        len(cmds.ls(type="mesh", noIntermediate=True))))

# ------------------------------------------- 13: his own skeleton, and the map
cmds.file(new=True, force=True)
his = import_his("src")
his_joints = [n for n in his if cmds.nodeType(n) == "joint"]
places = dict((p, tuple(cmds.xform(p, q=True, ws=True, t=True))) for p in his_joints)
now = sm.recognize(his_joints, places)


def answers(result):
    """{our bone: his leaf, the Base Human prefix off} -- his own spelling."""
    out = {}
    for ours, path in (result.mapping or {}).items():
        name = path.split("|")[-1].split(":")[-1]
        out[ours] = name[len(PREFIX):] if name.startswith(PREFIX) else name
    return out


mine_map = answers(now)
want = dict((ours, his_leaf) for ours, his_leaf in PAIRS.items()
            if his_leaf not in ("Spine1", "Spine2", "Spine3", "Spine4", "Neck1", "Neck2"))
wrong = sorted(k for k, v in want.items() if mine_map.get(k) != v)

# the control: the SAME call through the map as it stood before 2026-11-01, built by putting
# the three edits back. Its answer must differ, or this gate cannot fail.
src_text = open(REPO + "/SkeldarAnim/maya_skeletonmap.py", encoding="utf-8").read()
old_text = src_text
EDITS = [
    ('''if "clavicle" in words_set or "collar" in words_set or "clav" in words_set \\
            or "collarbone" in words_set or "scapula" in words_set:''',
     '''if "clavicle" in words_set or "collar" in words_set or "clav" in words_set:'''),
    ('''    "vector", "node", "platform"))''', '''    ))'''),
]
applied = 0
for new, old in EDITS:
    if new in old_text:
        old_text = old_text.replace(new, old, 1)
        applied += 1
# the palm -> hand pass (a hand with no finger below it), whole
marker = "    for side in SIDES:\n        if any(i.kind == \"hand\" and i.side == side"
if marker in old_text:
    cut = old_text.index(marker)
    end = old_text.index("\n    return info", cut)
    old_text = old_text[:cut] + old_text[end + 1:]
    applied += 1
old_mod = {"__name__": "maya_skeletonmap_before"}
exec(compile(old_text, "maya_skeletonmap_before.py", "exec"), old_mod)
old_map = answers(old_mod["recognize"](his_joints, places))
old_wrong = sorted(k for k, v in want.items() if old_map.get(k) != v)
gate(13, applied == 3 and not wrong and old_wrong,
     "his %d joints through maya_skeletonmap: %d of %d pairs right%s | the control (the map as it "
     "stood before, %d edits put back) gets %d wrong: %s"
     % (len(his_joints), len(want) - len(wrong), len(want),
        "" if not wrong else " -- WRONG: " + ", ".join("%s=%s" % (k, mine_map.get(k)) for k in wrong),
        applied, len(old_wrong), ", ".join("%s=%s" % (k, old_map.get(k)) for k in old_wrong[:6])))

# ----------------------------- 14 + 15: his back, against his file's own two-bone torso
# His file skinned the torso to `pelvis` and `spine_05` alone -- 1.2 joints a vertex over a
# 60 cm span -- so under a clip it was a rigid slab hinged at one place and his back folded
# (make_swordman_spine_skin.py). The measure: take the vertices the spine chain actually
# holds, band them by their place ALONG the chain, follow each band's centroid under the
# clip, and read the angle between successive band-to-band vectors; a fold spikes one band.
# Banding by world HEIGHT instead reads the thighs in the lowest band and a running clip
# then spikes it on a back that is perfectly smooth -- drawn and looked at, 2026-11-01.
# The control is HIS OWN skin with the chain collapsed back onto the two bones his file
# used, on the same clip, so the gate needs no second character and no fixed threshold.
from maya_uebridge import skeletonimport                                    # noqa: E402

CHAIN = ["pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05",
         "neck_01", "neck_02", "head"]
TWO = ("pelvis", "spine_05")
BANDS = 6
BETTER = 2.0             # how much flatter than his file's own torso the back must read
LAID_JOINTS = 2.0        # joints a vertex, on the ones laid along the chain (Manny: 2.5)
LAID_SPREAD = 1.5        # the weight's spread about its centre, cm (Manny: 3.3)


def bend(pts, groups):
    cs = [sum((om.MVector(pts[v]) for v in g), om.MVector()) / len(g) for g in groups]
    out = []
    for i in range(1, len(cs) - 1):
        u, v = cs[i] - cs[i - 1], cs[i + 1] - cs[i]
        if u.length() < 1e-6 or v.length() < 1e-6:
            out.append(0.0)
            continue
        out.append(math.degrees(math.acos(max(-1.0, min(1.0, u.normal() * v.normal())))))
    return out


def chain_arc(B):
    places = [om.MVector(cmds.xform(B[n], q=True, ws=True, t=True)) for n in CHAIN]
    out = [0.0]
    for i in range(1, len(places)):
        out.append(out[-1] + (places[i] - places[i - 1]).length())
    return dict(zip(CHAIN, out))


def riders(B, mesh, sc):
    """Every vertex the chain holds, with where it sits along it and on how many joints."""
    infl = cmds.skinCluster(sc, q=True, influence=True)
    leaf = [i.split("|")[-1].split(":")[-1] for i in infl]
    names = [n for n in CHAIN if n in leaf]
    pos_of = chain_arc(B)
    index = dict((n, leaf.index(n)) for n in names)
    out = []
    for v in range(cmds.polyEvaluate(mesh, vertex=True)):
        w = cmds.skinPercent(sc, "%s.vtx[%d]" % (mesh, v), q=True, value=True)
        got = dict((n, w[index[n]]) for n in names)
        s = sum(got.values())
        if s < 0.6:
            continue
        mean = sum(got[n] * pos_of[n] for n in names) / s
        var = sum(got[n] * (pos_of[n] - mean) ** 2 for n in names) / s
        out.append((v, mean, var ** 0.5, sum(1 for n in names if got[n] > 0.01)))
    return out, infl, index, pos_of


def collapse(sc, mesh, rows, infl, index, pos_of):
    """His file's own scheme: the chain's weight back on the nearer of the two bones."""
    for v, _mean, _sd, _n in rows:
        plug = "%s.vtx[%d]" % (mesh, v)
        w = cmds.skinPercent(sc, plug, q=True, value=True)
        share = sum(w[index[n]] for n in CHAIN if n in index)
        if share < 1e-6:
            continue
        here = om.MVector(cmds.xform(plug, q=True, ws=True, t=True))
        new = list(w)
        for n in CHAIN:
            if n in index:
                new[index[n]] = 0.0
        near = min(TWO, key=lambda n: abs(pos_of[n] - _mean))
        new[index[near]] += share
        cmds.skinPercent(sc, plug, transformValue=[(infl[k], new[k])
                                                   for k in range(len(infl))])


cmds.file(new=True, force=True)
print("   ", character.add_character(catalog.character_by_key("Swordman")).splitlines()[0])
root = [j for j in cmds.ls(type="joint", long=True)
        if j.split("|")[-1].split(":")[-1] == "root"
        and not cmds.listRelatives(j, parent=True, type="joint")][0]
B = bones_of(root)
body_mesh = max([cmds.listRelatives(s, parent=True, fullPath=True)[0]
                 for s in cmds.ls(type="mesh", noIntermediate=True, long=True)],
                key=lambda m: cmds.polyEvaluate(m, vertex=True))
body_sc = cmds.ls(cmds.listHistory(body_mesh), type="skinCluster")[0]
rows, infl, index, pos_of = riders(B, body_mesh, body_sc)
torso = [r for r in rows if r[1] <= pos_of["spine_05"] + 1e-6]
lo = min(r[1] for r in torso)
hi = max(r[1] for r in torso)
bands = []
for i in range(BANDS):
    a_ = lo + (hi - lo) * i / float(BANDS)
    b_ = lo + (hi - lo) * (i + 1) / float(BANDS)
    bands.append([r[0] for r in torso if a_ <= r[1] <= b_ + (1e-6 if i == BANDS - 1 else 0)])
bands = [g for g in bands if len(g) >= 3]
want = bend(points(body_mesh), bands)

nodes = import_fbx(CLIP, "clip")
src = min((j for j in nodes if cmds.nodeType(j) == "joint"
           and not cmds.listRelatives(j, parent=True, type="joint")),
          key=lambda j: j.count("|"))
all_src = list(bones_of(src).values())
first_f = int(cmds.findKeyframe(all_src, which="first"))
last_f = int(cmds.findKeyframe(all_src, which="last"))
skeletonimport.transfer(src, root, first_f, last_f)
frames = list(range(first_f, last_f + 1, max(1, (last_f - first_f) // 8)))


def worst_bend():
    worst = 0.0
    for t_ in frames:
        cmds.currentTime(t_)
        got = bend(points(body_mesh), bands)
        worst = max(worst, max(abs(got[i] - want[i]) for i in range(len(want))))
    return worst


laid_bend = worst_bend()
laid = [r for r in rows if r[3] >= 2]
joints_each = sum(r[3] for r in laid) / float(len(laid)) if laid else 0.0
spread_cm = sorted(r[2] for r in laid)[len(laid) // 2] if laid else 0.0
collapse(body_sc, body_mesh, torso, infl, index, pos_of)
two_bend = worst_bend()
gate(14, laid_bend * BETTER < two_bend,
     "his back under the clip (%d vertices the spine holds, %d bands along it): %.1f deg off "
     "its bind -- and %.1f with the SAME skin collapsed back onto the two bones his file used "
     "(the bar: at least %.0fx flatter than his file's own torso)"
     % (len(torso), len(bands), laid_bend, two_bend, BETTER))
gate(15, len(laid) >= 30 and joints_each >= LAID_JOINTS and spread_cm >= LAID_SPREAD,
     "his torso rides the whole spine: %d vertices on more than one chain joint, %.1f joints "
     "each, the weight's spread about its centre %.1f cm (Manny: 2.5 joints, 3.3 cm; his file: "
     "1.2 joints, 0.0 cm)" % (len(laid), joints_each, spread_cm))

# ------------------------------- 16 + 17: no fingers, no camera bones
cmds.file(new=True, force=True)
print("   ", character.add_character(rig_row).splitlines()[0])
rig = maya_rigs.rigs()[0]
NS = rig.namespace + ":"


def finger_named(path_):
    leaf_ = path_.rsplit("|", 1)[-1].rsplit(":", 1)[-1]
    return any(f in leaf_ for f in FINGERS)


fingers = [n for n in (cmds.ls(NS + "*", long=True) or []) if finger_named(n)]
dials = [n for d in FINGER_DIALS for n in cmds.ls(NS + d, long=True) or []]
#  the arm itself still works: its twist Parts are driven, and the hand is skinned
H = bones_of(rig.skeleton_root)
parts = [p for p in cmds.ls(NS + "ElbowPart*", NS + "ShoulderPart*", long=True) or []
         if cmds.nodeType(p) == "joint"
         and cmds.listConnections(p, source=True, destination=False)]
hand_skinned = False
for sc in cmds.ls(type="skinCluster") or []:
    inf = [i.rsplit("|", 1)[-1].rsplit(":", 1)[-1]
           for i in cmds.skinCluster(sc, q=True, influence=True) or []]
    hand_skinned = hand_skinned or ("hand_r" in inf and "hand_l" in inf)
gate(16, not fingers and not dials and len(parts) == 8 and hand_skinned,
     "no finger left in his rig (%d finger-named nodes, %d curl/spread dials), its 8 twist "
     "Parts still driven (%d), the mitten still skinned to hand_r and hand_l (%s)"
     % (len(fingers), len(dials), len(parts), hand_skinned))

cam_rig = [n for b in CAMERA_BONES for n in cmds.ls(NS + b, long=True) or []]
#  what the Camera Setup button does when the bone is not there: `camera_setup` resolves
#  the bone and puts `missing_bone_message` on the card's line (there is no card here).
found = skeleton.resolve_bone(rig.skeleton_root, camera.BONE)
refusal = "" if found else window.missing_bone_message(rig.skeleton_root, camera.BONE)
cmds.file(new=True, force=True)
print("   ", character.add_character(skel_row).splitlines()[0])
cam_skel = [n for b in CAMERA_BONES for n in cmds.ls(b, long=True) or []]
gate(17, not cam_rig and not cam_skel and not found and "camera_root" in refusal,
     "his camera bones are gone (rig %d, skeleton %d) and Camera Setup refuses by name: %r"
     % (len(cam_rig), len(cam_skel), refusal[:90]))

print("FAILED gates: %s" % FAILS if FAILS else "ALL GATES PASSED")
maya.standalone.uninitialize()
