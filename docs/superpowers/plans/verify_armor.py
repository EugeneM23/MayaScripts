"""Standalone gates for the Armor card's machinery and the Tech Limb's skeletal shield (2026-10-01).

    mayapy verify_armor.py <UE5 clip .fbx, e.g. Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX> <scratch dir>

mayapy STANDALONE, an empty scene (spec docs/superpowers/specs/2026-10-01-armor-techlimb-design.md and
its addendum): a Manny rig, a Creep rig, an Orc D rig and a bare Manny skeleton added through Add
Character, the Tech Limb equipped through `armor.equip`, and everything measured against UNREAL's
numbers -- sources/armor/techlimb_shield_ue.json (the shield's joints in the game's Block Idle, Root at
its reference: the clips force root lock) and techlimb_ue.json (lowerarm_l on the reference pose); the
axis map is re-derived here from the rig's own bones, never read from the asset script:

- on Manny: every shield joint where the game puts it, the group's channels 0, its space outside the
  skeleton in the rig's group, its own namespace, the skinned mesh following the joints only;
- on the Creep and the Orc D the same shield on their own lowerarm_l;
- the shield's Root is no character; a second Equip replaces; a selected shield names its character;
- a UE clip retargeted onto Manny through the button: the shield rides the bone at every sampled frame;
- the export bones only, none of the shield's;
- Unequip leaves no node of ours and no namespace; a bare skeleton's space at world level;
- the other characters never moved.
"""
import json
import os
import sys

import numpy as np

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
sys.path.insert(0, REPO + "/docs/superpowers/plans")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
import ue_maya_axes as axes  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_overrig import builder  # noqa: E402
from maya_scenesetup import armor, catalog, character, colour, skeleton  # noqa: E402
from maya_uebridge import animexport  # noqa: E402

CLIP = sys.argv[1].replace("\\", "/")
SCRATCH = sys.argv[2].replace("\\", "/")
SHIELD = json.load(open(REPO + "/sources/armor/techlimb_shield_ue.json"))
LIMB = json.load(open(REPO + "/sources/armor/techlimb_ue.json"))
TECH = catalog.armor_by_key("Tech_Limb")
FAILS = []
TOTAL = 15


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(n)


def wm(node):
    return np.array(cmds.getAttr(node + ".worldMatrix[0]")).reshape(4, 4)


def points(node):
    sel = om.MSelectionList()
    sel.add(node)
    fn = om.MFnMesh(sel.getDagPath(0))
    return np.array([[p.x, p.y, p.z] for p in fn.getPoints(om.MSpace.kWorld)])


def in_bone(pts, bone_wm):
    """World points in the bone's space (row vectors)."""
    h = np.hstack([pts, np.ones((len(pts), 1))])
    return (h @ np.linalg.inv(bone_wm))[:, :3]


def add(key):
    print("   ", character.add_character(catalog.character_by_key(key)))
    cmds.select(clear=True)


def root_of(namespace):
    return cmds.ls(namespace + ":root", long=True)[0] if namespace else \
        [r for r in cmds.ls("root", long=True) if ":" not in r][0]


def piece_parts(piece):
    joints = dict((j.split("|")[-1].split(":")[-1], j)
                  for j in cmds.listRelatives(piece, allDescendents=True, type="joint", fullPath=True) or [])
    meshes = [cmds.listRelatives(m, parent=True, fullPath=True)[0]
              for m in cmds.listRelatives(piece, allDescendents=True, type="mesh", fullPath=True) or []
              if not cmds.getAttr(m + ".intermediateObject")]
    return joints, meshes


def our_nodes():
    out = []
    for node in cmds.ls(type="transform", long=True) or []:
        for attr in (armor.MARKER, armor.SPACE_MARKER, armor.GROUP_MARKER):
            if cmds.attributeQuery(attr, node=node, exists=True):
                out.append(node)
                break
    return out


def armor_namespaces():
    return [n for n in character.existing_namespaces() if n.split(":")[-1].startswith("Tech_Limb")]


# ------------------------------------------------------------------ the asset as it stands alone
cmds.file(new=True, force=True)
cmds.file(TECH.path, i=True, type="mayaAscii", ignoreVersion=True, namespace="probe")
ALONE = points(cmds.ls("probe:TechLimbShieldMesh", long=True)[0])
cmds.file(new=True, force=True)

add("Manny_Rig")
add("Creep_Rig")
add("Orc_D_Rig")
add("Manny")
MANNY, CREEP, ORC, BARE = root_of("Manny_Rig"), root_of("Creep_Rig"), root_of("Orc_D_Rig"), root_of("")
LOWER = dict((r, skeleton.resolve_bone(r, "lowerarm_l")) for r in (MANNY, CREEP, ORC, BARE))
STILL = dict((r, wm(LOWER[r])) for r in (CREEP, ORC, BARE))

# ------------------------------------------------------------------ Manny, against Unreal
text = armor.equip(MANNY, TECH)
print("   ", text)
piece = armor.worn(MANNY).get("Tech_Limb", (None,))[0]
joints = {}
for path in cmds.listRelatives(MANNY, allDescendents=True, type="joint", fullPath=True) + [MANNY]:
    joints[path.split("|")[-1].split(":")[-1]] = path
shared = sorted(n for n in LIMB["bones"] if n in joints and not n.startswith(("weapon_", "camera_", "ik_")))
M, res = axes.ue_to_maya([LIMB["bones"][n]["t"] for n in shared],
                         [cmds.xform(joints[n], query=True, worldSpace=True, translation=True) for n in shared])
low = LIMB["bones"]["lowerarm_l"]
R_low, t_low = np.array([low["x"], low["y"], low["z"]]).T, np.array(low["t"])
sj, smeshes = piece_parts(piece) if piece else ({}, [])
worst, name = 0.0, ""
for bone, b in SHIELD["bones"].items():
    expected = M @ (R_low @ np.array(b["idle_cs"]["t"]) + t_low)     # the game's world, mapped to Maya
    got = np.array(cmds.xform(sj[bone], query=True, worldSpace=True, translation=True)) if bone in sj else np.full(3, 1e9)
    if np.linalg.norm(got - expected) > worst:
        worst, name = float(np.linalg.norm(got - expected)), bone
gate(1, piece is not None and len(sj) == 38 and worst < 1e-3 and res < 0.1,
     "Manny: all %d shield joints where the game's Block Idle puts them to %.2e cm (%s), the map over %d bones"
     % (len(sj), worst, name, len(shared)))
main_bone = in_bone(np.array([cmds.xform(sj["Main"], q=True, ws=True, t=True)]), wm(LOWER[MANNY]))[0] if sj else [0, 0, 0]
print("    Main in lowerarm_l space: %s (%.1f cm from the elbow)" % (np.round(main_bone, 2).tolist(),
                                                                  float(np.linalg.norm(main_bone))))
chan = [cmds.getAttr(piece + "." + a) for a in ("tx", "ty", "tz", "rx", "ry", "rz")] if piece else [1]
space = (cmds.listRelatives(piece, parent=True, fullPath=True) or [""])[0] if piece else ""
group = (cmds.listRelatives(space, parent=True, fullPath=True) or [""])[0] if space else ""
gate(2, piece is not None and max(abs(c) for c in chan) < 1e-9 and space.endswith("lowerarm_l_armorSpace")
     and group.startswith("|Manny_Rig:Group|") and not piece.startswith(MANNY + "|")
     and cmds.getAttr(piece + "." + armor.NAMESPACE) == "Tech_Limb",
     "the group at identity in the space, outside the skeleton, in the rig's group, namespace Tech_Limb: %s" % piece)
mesh = smeshes[0] if smeshes else None
skin = cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster") if mesh else []
moved = in_bone(points(mesh), wm(LOWER[MANNY])) if mesh else np.zeros((1, 3))
drift = float(np.abs(moved - ALONE).max()) if mesh and moved.shape == ALONE.shape else 1e9
gate(3, mesh is not None and len(skin) == 1 and not cmds.getAttr(mesh + ".inheritsTransform") and drift < 1e-3,
     "the skinned mesh follows the joints only: in lowerarm_l's space where the asset stands alone to %.2e cm"
     % drift)
mat = colour.material_on([cmds.listRelatives(mesh, shapes=True, fullPath=True, noIntermediate=True)[0]]) if mesh else None
gate(4, "Tech Limb on Manny_Rig's lowerarm_l" in text and bool(mat) and colour.is_ours(mat),
     "the line %r, one material of ours (%s)" % (text, mat))

# ------------------------------------------------------------------ the other rigs
ok, notes = True, []
for root in (CREEP, ORC):
    armor.equip(root, TECH)
    p = armor.worn(root).get("Tech_Limb", (None,))[0]
    if not p:
        ok = False
        notes.append("%s: nothing" % root)
        continue
    off = float(np.abs(wm(p) - wm(LOWER[root])).max())
    pj, _pm = piece_parts(p)
    rel = in_bone(np.array([cmds.xform(pj["Main"], q=True, ws=True, t=True)]), wm(LOWER[root]))[0]
    ok = ok and off < 1e-6 and float(np.linalg.norm(rel - main_bone)) < 1e-4
    notes.append("%s %.1e, Main %.1e" % (armor.character_name(root), off, float(np.linalg.norm(rel - main_bone))))
gate(5, ok, "the Creep and the Orc D: the shield at identity on their own lowerarm_l (%s)" % ", ".join(notes))

shield_roots = [r for r in builder.character_roots() if "Tech_Limb" in r]
gate(6, not shield_roots, "no shield Root counted as a character (%s)" % shield_roots)
before = len(armor.pieces())
again = armor.equip(MANNY, TECH)
piece = armor.worn(MANNY)["Tech_Limb"][0]
gate(7, len(armor.pieces()) == before and len(armor.worn(MANNY)) == 1 and "replaced Tech Limb" in again
     and len(armor_namespaces()) == 3,
     "a second Equip replaces: %d pieces, namespaces %s, the line %r" % (len(armor.pieces()), armor_namespaces(), again))
sj, smeshes = piece_parts(piece)
mesh = smeshes[0]
cmds.select(mesh)
named = skeleton.current_root()
cmds.select(clear=True)
gate(8, named == MANNY, "the shield's mesh selected names its character: %s" % named)

# ------------------------------------------------------------------ a retarget onto Manny
cmds.namespace(add="clip")
cmds.namespace(set=":clip")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
joints_before = set(cmds.ls(type="joint", long=True))
mel.eval('FBXImport -f "%s";' % CLIP)
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in joints_before]
src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")), key=lambda j: j.count("|"))
keyed = [j for j in new if cmds.listConnections(j, type="animCurve")]
first, last = cmds.findKeyframe(keyed, which="first"), cmds.findKeyframe(keyed, which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
cmds.select(cmds.ls("Manny_Rig:Main")[0], src)
ok_rt, text_rt = rr.run_retarget()
print("   ", text_rt.splitlines()[0][:160])
worst_g, worst_m, travel, start = 0.0, 0.0, 0.0, None
frames = list(range(int(first), int(last) + 1, max(1, int((last - first) / 10))))
for t in frames:
    cmds.currentTime(t)
    b = wm(LOWER[MANNY])
    worst_g = max(worst_g, float(np.abs(wm(piece) - b).max()))
    worst_m = max(worst_m, float(np.abs(in_bone(points(mesh), b) - ALONE).max()))
    start = b if start is None else start
    travel = max(travel, float(np.linalg.norm(b[3, :3] - start[3, :3])))
gate(9, ok_rt and worst_g < 1e-5 and worst_m < 1e-3 and travel > 1.0,
     "the clip retargeted onto Manny: the shield on lowerarm_l at %d frames to %.1e, its mesh in the bone's space "
     "to %.1e cm (the bone travels %.1f cm)" % (len(frames), worst_g, worst_m, travel))

fbx = SCRATCH + "/verify_armor_export.fbx"
if os.path.exists(fbx):
    os.remove(fbx)
animexport.export_hierarchy(fbx, root=MANNY, start=first, end=last)
cmds.namespace(add="chk")
cmds.namespace(set=":chk")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
before_nodes = set(cmds.ls(long=True))
mel.eval('FBXImport -f "%s";' % fbx)
cmds.namespace(set=":")
arrived = [n for n in cmds.ls(long=True) if n not in before_nodes]
j_in = cmds.ls(arrived, type="joint") or []
m_in = cmds.ls(arrived, type="mesh") or []
gate(10, len(j_in) == 93 and not m_in and not [j for j in j_in if "joint_on_vertex" in j or j.endswith("Main")],
     "the export read back: %d joints, %d meshes, none of the shield's" % (len(j_in), len(m_in)))
cmds.delete([n for n in cmds.ls("chk:*", long=True, type="transform") or []
             if cmds.objExists(n) and not cmds.listRelatives(n, parent=True)])

# ------------------------------------------------------------------ a bare skeleton, Unequip
armor.equip(BARE, TECH)
bare_piece = armor.worn(BARE).get("Tech_Limb", (None,))[0]
bare_group = cmds.listRelatives(cmds.listRelatives(bare_piece, parent=True, fullPath=True)[0],
                                parent=True, fullPath=True)[0] if bare_piece else ""
roots_now = builder.character_roots()
gate(11, bare_piece is not None and bare_group == "|ArmorSpaces"
     and float(np.abs(wm(bare_piece) - wm(LOWER[BARE])).max()) < 1e-6
     and not [r for r in roots_now if "Tech_Limb" in r],
     "the bare skeleton: its space at world level (%s), the shield on its lowerarm_l, still no extra character"
     % bare_group)

lines = [armor.unequip(r, "Tech_Limb") for r in (MANNY, CREEP, ORC, BARE)]
left = our_nodes()
leftover = [n for n in cmds.ls(type="joint", long=True) or [] if "joint_on_vertex" in n]
gate(12, not left and not armor.pieces() and not leftover, "Unequip on all four: nothing of ours left (%s %s)"
     % (left, leftover[:3]))
gate(13, not armor_namespaces(), "no Tech_Limb namespace left: %s" % armor_namespaces())
gate(14, all("taken off" in line for line in lines) and "does not wear" in armor.unequip(MANNY, "Tech_Limb"),
     "the lines %s; a second Unequip says so" % lines)
moved = max(float(np.abs(wm(LOWER[r]) - m).max()) for r, m in STILL.items())
gate(15, moved < 1e-9, "the Creep, the Orc D and the bare skeleton never moved: %.1e" % moved)

print("DONE %d of %d gates passed%s" % (TOTAL - len(FAILS), TOTAL, "" if not FAILS else " - FAILED %s" % FAILS))
