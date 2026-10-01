"""Standalone gates for the Armor card's machinery and the Tech Limb (2026-10-01).

    mayapy verify_armor.py <UE5 clip .fbx, e.g. Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX> <scratch dir>

mayapy STANDALONE, an empty scene (spec docs/superpowers/specs/2026-10-01-armor-techlimb-design.md):
a Manny rig, a Creep rig, an Orc D rig and a bare Manny skeleton added through Add Character, the
Tech Limb equipped through `armor.equip`, and everything measured against UNREAL's numbers
(sources/armor/techlimb_ue.json -- the plate's vertices in component space on the reference pose,
the axis map re-derived here from the bones, never read from the asset script):

- on Manny: every plate vertex where Unreal puts it, its channels 0, its space outside the
  skeleton in the rig's group;
- on the Creep and the Orc D: the piece at identity on their own lowerarm_l;
- a second Equip replaces, never doubles; a selected piece names its character;
- a UE clip retargeted onto Manny through the button: the piece on the bone at every sampled frame;
- the export bones only;
- Unequip leaves no node of ours; a bare skeleton's space at world level, pruned too;
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
from maya_scenesetup import armor, catalog, character, colour, skeleton  # noqa: E402
from maya_uebridge import animexport  # noqa: E402

CLIP = sys.argv[1].replace("\\", "/")
SCRATCH = sys.argv[2].replace("\\", "/")
UE = json.load(open(REPO + "/sources/armor/techlimb_ue.json"))
TECH = catalog.armor_by_key("Tech_Limb")
FAILS = []
TOTAL = 14


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


def add(key):
    text = character.add_character(catalog.character_by_key(key))
    print("   ", text)
    cmds.select(clear=True)
    return text


def root_of(namespace):
    return cmds.ls(namespace + ":root", long=True)[0] if namespace else \
        [r for r in cmds.ls("root", long=True) if ":" not in r][0]


def bone(root, name):
    return skeleton.resolve_bone(root, name)


def our_nodes():
    """Everything of ours an Equip leaves: pieces, spaces, groups -- found by attribute."""
    out = []
    for node in cmds.ls(type="transform", long=True) or []:
        for attr in (armor.MARKER, armor.SPACE_MARKER, armor.GROUP_MARKER):
            if cmds.attributeQuery(attr, node=node, exists=True):
                out.append(node)
                break
    return out


cmds.file(new=True, force=True)
add("Manny_Rig")
add("Creep_Rig")
add("Orc_D_Rig")
add("Manny")
MANNY, CREEP, ORC, BARE = (root_of("Manny_Rig"), root_of("Creep_Rig"), root_of("Orc_D_Rig"),
                           root_of(""))
print("    roots", MANNY, CREEP, ORC, BARE)
LOWER = dict((r, bone(r, "lowerarm_l")) for r in (MANNY, CREEP, ORC, BARE))
STILL = dict((r, wm(LOWER[r])) for r in (CREEP, ORC, BARE))

# ------------------------------------------------------------------ Manny, against Unreal
text = armor.equip(MANNY, TECH)
print("   ", text)
worn = armor.worn(MANNY)
piece = worn.get("Tech_Limb", (None,))[0]
joints = {}
for path in cmds.listRelatives(MANNY, allDescendents=True, type="joint", fullPath=True) + [MANNY]:
    joints[path.split("|")[-1].split(":")[-1]] = path
shared = sorted(n for n in UE["bones"] if n in joints and not n.startswith(("weapon_", "camera_", "ik_")))
M, res = axes.ue_to_maya([UE["bones"][n]["t"] for n in shared],
                         [cmds.xform(joints[n], query=True, worldSpace=True, translation=True)
                          for n in shared])
target = np.array(UE["verts_cs"]) @ M.T
pts = points(piece) if piece else np.zeros((1, 3))
_i, d = axes.nearest(pts, target)
_j, back = axes.nearest(target, pts)
chan = [cmds.getAttr(piece + "." + a) for a in ("tx", "ty", "tz", "rx", "ry", "rz")] if piece else [1]
scale = [cmds.getAttr(piece + "." + a) for a in ("sx", "sy", "sz")] if piece else [0]
gate(1, piece is not None and d.max() < 1e-3 and back.max() < 1e-3 and res < 0.1,
     "Manny: every plate vertex where Unreal puts it to %.2e cm (and back %.2e), the map over %d bones %.4f cm"
     % (d.max(), back.max(), len(shared), res))
gate(2, piece is not None and max(abs(c) for c in chan) < 1e-9 and max(abs(s - 1) for s in scale) < 1e-9,
     "its channels read 0 0 0 / 0 0 0, scale 1 (%s)" % ([round(c, 9) for c in chan],))
space = (cmds.listRelatives(piece, parent=True, fullPath=True) or [""])[0] if piece else ""
group = (cmds.listRelatives(space, parent=True, fullPath=True) or [""])[0] if space else ""
gate(3, space.endswith("lowerarm_l_armorSpace") and group.endswith("|ArmorSpaces")
     and group.startswith("|Manny_Rig:Group|") and not piece.startswith(MANNY + "|")
     and armor.space_of(LOWER[MANNY]) == space,
     "the space outside the skeleton, in the rig's group: %s" % piece)
mat = colour.material_on([cmds.listRelatives(piece, shapes=True, fullPath=True)[0]]) if piece else None
gate(4, "Tech Limb on Manny_Rig's lowerarm_l" in text and bool(mat) and colour.is_ours(mat),
     "the line %r, one material of ours (%s)" % (text, mat))

# ------------------------------------------------------------------ the other rigs
ok = True
notes = []
for root in (CREEP, ORC):
    t = armor.equip(root, TECH)
    p = armor.worn(root).get("Tech_Limb", (None,))[0]
    if not p:
        ok = False
        notes.append("%s: nothing" % root)
        continue
    off = float(np.abs(wm(p) - wm(LOWER[root])).max())
    ok = ok and off < 1e-6
    notes.append("%s %.1e" % (armor.character_name(root), off))
gate(5, ok, "the Creep and the Orc D: the piece on their own lowerarm_l at identity (%s)" % ", ".join(notes))

before = len(armor.pieces())
again = armor.equip(MANNY, TECH)
gate(6, len(armor.pieces()) == before and len(armor.worn(MANNY)) == 1 and "replaced Tech Limb" in again,
     "a second Equip replaces: %d pieces in the scene, the line %r" % (len(armor.pieces()), again))
piece = armor.worn(MANNY)["Tech_Limb"][0]
cmds.select(piece)
named = skeleton.current_root()
cmds.select(clear=True)
gate(7, named == MANNY, "the piece selected names its character: %s" % named)

# ------------------------------------------------------------------ a retarget onto Manny
cmds.namespace(add="clip")
cmds.namespace(set=":clip")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
joints_before = set(cmds.ls(type="joint", long=True))
mel.eval('FBXImport -f "%s";' % CLIP)
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in joints_before]
src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
          key=lambda j: j.count("|"))
keyed = [j for j in new if cmds.listConnections(j, type="animCurve")]
first = cmds.findKeyframe(keyed, which="first")
last = cmds.findKeyframe(keyed, which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
cmds.select(cmds.ls("Manny_Rig:Main")[0], src)
ok_rt, text_rt = rr.run_retarget()
print("   ", text_rt.splitlines()[0][:160])
worst, travel, start_wm = 0.0, 0.0, None
frames = list(range(int(first), int(last) + 1, max(1, int((last - first) / 10))))
for t in frames:
    cmds.currentTime(t)
    b, p = wm(LOWER[MANNY]), wm(piece)
    worst = max(worst, float(np.abs(p - b).max()))
    if start_wm is None:
        start_wm = b
    travel = max(travel, float(np.linalg.norm(b[3, :3] - start_wm[3, :3])))
#  1e-5: float precision on a bone 200 cm from the origin (the constraint chain is evaluated in
#  single precision -- 4e-6 measured), far under anything visible
gate(8, ok_rt and worst < 1e-5 and travel > 1.0,
     "the clip retargeted onto Manny: the piece on lowerarm_l at %d frames to %.1e (the bone travels %.1f cm)"
     % (len(frames), worst, travel))
chan = [cmds.getAttr(piece + "." + a) for a in ("tx", "ty", "tz", "rx", "ry", "rz")]
gate(9, max(abs(c) for c in chan) < 1e-9 and not cmds.listConnections(piece, type="animCurve"),
     "the piece's own channels untouched by the retarget: %s, no curve on it" % ([round(c, 9) for c in chan],))

fbx = SCRATCH + "/verify_armor_export.fbx"
if os.path.exists(fbx):
    os.remove(fbx)
result = animexport.export_hierarchy(fbx, root=MANNY, start=first, end=last)
cmds.namespace(add="chk")
cmds.namespace(set=":chk")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
before_nodes = set(cmds.ls(long=True))
mel.eval('FBXImport -f "%s";' % fbx)
cmds.namespace(set=":")
arrived = [n for n in cmds.ls(long=True) if n not in before_nodes]
j_in = cmds.ls(arrived, type="joint") or []
m_in = cmds.ls(arrived, type="mesh") or []
gate(10, len(j_in) > 80 and not m_in, "the export read back: %d joints, %d meshes" % (len(j_in), len(m_in)))
cmds.delete([n for n in cmds.ls("chk:*", long=True, type="transform") or []
             if cmds.objExists(n) and not cmds.listRelatives(n, parent=True)])

# ------------------------------------------------------------------ a bare skeleton, Unequip
t = armor.equip(BARE, TECH)
bare_piece = armor.worn(BARE).get("Tech_Limb", (None,))[0]
bare_group = cmds.listRelatives(cmds.listRelatives(bare_piece, parent=True, fullPath=True)[0],
                                parent=True, fullPath=True)[0] if bare_piece else ""
gate(11, bare_piece is not None and bare_group == "|ArmorSpaces"
     and float(np.abs(wm(bare_piece) - wm(LOWER[BARE])).max()) < 1e-6,
     "the bare skeleton: its space at world level (%s), the piece on its lowerarm_l" % bare_group)

lines = [armor.unequip(r, "Tech_Limb") for r in (MANNY, CREEP, ORC, BARE)]
left = our_nodes()
gate(12, not left and not armor.pieces(), "Unequip on all four: nothing of ours left (%s)" % left)
gate(13, all("taken off" in line for line in lines)
     and "does not wear" in armor.unequip(MANNY, "Tech_Limb"),
     "the lines %s; a second Unequip says so" % lines)
moved = max(float(np.abs(wm(LOWER[r]) - m).max()) for r, m in STILL.items())
gate(14, moved < 1e-9, "the Creep, the Orc D and the bare skeleton never moved: %.1e" % moved)

print("DONE %d of %d gates passed%s" % (TOTAL - len(FAILS), TOTAL,
                                        "" if not FAILS else " - FAILED %s" % FAILS))
