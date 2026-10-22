"""Verify the Playerchar character and its clothing (2026-10-21), in mayapy STANDALONE.

    mayapy verify_playerchar.py <UE5 clip .fbx, e.g. C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX> <scratch dir>

Spec: docs/superpowers/specs/2026-10-21-playerchar-and-clothing-design.md. Against the source the assets
were built from (sources/playerchar/Playerchar_Proxy.mb, imported into `chk`):

- «Playerchar [rig]» and «Playerchar [skeleton]» added: one mesh each, naked, on its bind, textured with
  the shipped atlas, the body where the source's skin shows it; each with the first-person `Body_1P`
  (the body's arms and legs, Manny's cut), hidden, the rig's `Main.view` (3P:1P) switching the two;
- the four clothing rows equipped on the rig: each in its bone's armor space, its meshes not
  inheriting, no joint of the piece's left, every vertex on a vertex of the source's own mesh, the body's
  material shared;
- a UE clip retargeted onto the rig through the button (Manny's skeleton: exact), and under the take
  every clothing vertex where the source's own skin puts it with the source's skeleton on the rig's
  game bones; every `Body_1P` vertex on its body vertex under the take; the switch untouched by the
  retarget and showing each mesh in turn; a clothing mesh selected names its character; the export
  bones only;
- refused on the Creep (another body) with the scene untouched; worn on a Manny skeleton (a twin);
  a second Equip replaces; Unequip leaves nothing; Delete character takes the clothes.
"""
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
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:                                       # noqa: BLE001
        pass
import maya_rig_retarget as rr  # noqa: E402
import maya_rigs  # noqa: E402
from maya_scenesetup import armor, catalog, character, colour, deletion, skeleton  # noqa: E402
from maya_uebridge import animexport  # noqa: E402

CLIP = sys.argv[1].replace("\\", "/")
SCRATCH = sys.argv[2].replace("\\", "/")
SOURCE = REPO + "/sources/playerchar/Playerchar_Proxy.mb"
ATLAS = catalog.asset_path("Playerchar/Playerchar_Color.jpg")
CLOTHES = [r for r in catalog.ARMOR if r.kind == catalog.SKINNED]
FROM = {"Playerchar_Helmet": ["polySurface9"],
        "Playerchar_Armor": ["TorsoCloth_", "chains_Shoulders", "chains_Legs", "polySurface9"],
        "Playerchar_Shield": ["Shield"], "Playerchar_Pants": ["Pants"]}
FAILS = []
TOTAL = 18


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(n)


def points(node):
    sel = om.MSelectionList()
    sel.add(node)
    fn = om.MFnMesh(sel.getDagPath(0))
    return np.array([[p.x, p.y, p.z] for p in fn.getPoints(om.MSpace.kWorld)])


def live_meshes(node):
    return [cmds.listRelatives(m, parent=True, fullPath=True)[0]
            for m in cmds.ls(node, dag=True, type="mesh", long=True, noIntermediate=True) or []]


def skin_error(skin):
    worst = 0.0
    for idx in cmds.getAttr(skin + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (skin, idx), s=True, d=False)
        if src:
            m = np.array(cmds.getAttr("%s.bindPreMatrix[%d]" % (skin, idx))).reshape(4, 4) @ \
                np.array(cmds.getAttr(src[0] + ".worldMatrix[0]")).reshape(4, 4)
            worst = max(worst, float(np.abs(m - np.eye(4)).max()))
    return worst


def skins(node):
    shapes = cmds.ls(node, dag=True, type="mesh", long=True, noIntermediate=True) or []
    return sorted(set(cmds.ls(cmds.listHistory(shapes, pruneDagObjects=True) or [], type="skinCluster") or []))


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def joints_of(root):
    return dict((leaf(j), j) for j in cmds.ls(root, dag=True, type="joint", long=True) or [])


def match(piece_points, source_points, tol=1e-3):
    """For each piece vertex its nearest source vertex: (indices, worst distance)."""
    src = np.vstack(source_points)
    idx, worst = [], 0.0
    for chunk in range(0, len(piece_points), 512):
        p = piece_points[chunk:chunk + 512]
        d = ((p[:, None, :] - src[None, :, :]) ** 2).sum(-1)
        i = d.argmin(1)
        idx.extend(i.tolist())
        worst = max(worst, float(np.sqrt(d[np.arange(len(p)), i]).max()))
    return np.array(idx), worst


def namespaces(prefix):
    return [n for n in character.existing_namespaces() if n.split(":")[-1].startswith(prefix)]


cmds.file(new=True, force=True)
# ------------------------------------------------------------------ the source, beside
cmds.file(SOURCE, i=True, type="mayaBinary", namespace="chk", ignoreVersion=True)
CHK = joints_of(cmds.ls("chk:root", long=True)[0])
SRC_MESH = dict((leaf(t), t) for t in live_meshes(cmds.ls("chk:MESH", long=True)[0]))
SRC_AT_BIND = dict((k, points(v)) for k, v in SRC_MESH.items())

# ------------------------------------------------------------------ the rig and the skeleton
print("   ", character.add_character(catalog.character_by_key("Playerchar_Rig")))
cmds.select(clear=True)
rig = [r for r in maya_rigs.rigs() if r.namespace.endswith("Playerchar_Rig")][0]
RIG = rig.skeleton_root
group = character.character_group(RIG) or ""
body = [m for m in live_meshes(group) if leaf(m) == "Body"] if group else []
body1 = [m for m in live_meshes(group) if leaf(m) == "Body_1P"] if group else []
main = maya_rigs.node(rig, "Main")
files = [f for f in cmds.ls(type="file") if cmds.attributeQuery(colour.ASSET_IMAGE, node=f, exists=True)]
view_ok = (cmds.attributeQuery("view", node=main, exists=True)
           and cmds.attributeQuery("view", node=main, listEnum=True) == ["3P:1P"]
           and cmds.getAttr(main + ".view") == 0 and not cmds.getAttr(main + ".view", keyable=True))
gate(1, len(body) == 1 and len(body1) == 1 and len(live_meshes(group)) == 2
     and skin_error(skins(body[0])[0]) < 1e-4 and skin_error(skins(body1[0])[0]) < 1e-4 and view_ok
     and cmds.getAttr(body[0] + ".visibility") and not cmds.getAttr(body1[0] + ".visibility")
     and [os.path.normcase(cmds.getAttr(f + ".fileTextureName")) for f in files] == [os.path.normcase(ATLAS)],
     "Playerchar [rig]: the body (naked) and Body_1P, on their bind %.1e, Main.view 3P (not keyable) showing "
     "the body, its image the shipped atlas %s"
     % (skin_error(skins(body[0])[0]) if body else -1, [cmds.getAttr(f + ".fileTextureName") for f in files]))
BODY, BODY_1P = body[0], body1[0]
ONE_P, one_p_off = match(points(BODY_1P), [points(BODY)])
print("    Body_1P: %d of the body's vertices, each on one to %.1e cm" % (len(ONE_P), one_p_off))
drift = float(np.abs(points(BODY) - SRC_AT_BIND["Body"]).max())
gate(2, drift < 1e-3, "the rig's body where the source's skin shows it at the bind to %.1e cm" % drift)

print("   ", character.add_character(catalog.character_by_key("Playerchar")))
cmds.select(clear=True)
bare_group = [g for g in cmds.ls(assemblies=True, long=True) if g.endswith("Playerchar_Skeleton_Character")]
BARE = cmds.ls(bare_group[0] + "|root", long=True)[0] if bare_group else ""
bare_body = [m for m in live_meshes(bare_group[0]) if leaf(m) == "Body"] if bare_group else []
bare_1p = [m for m in live_meshes(bare_group[0]) if leaf(m) == "Body_1P"] if bare_group else []
gate(3, len(bare_body) == 1 and len(bare_1p) == 1 and skin_error(skins(bare_body[0])[0]) < 1e-4
     and skin_error(skins(bare_1p[0])[0]) < 1e-4
     and cmds.getAttr(bare_body[0] + ".visibility") and not cmds.getAttr(bare_1p[0] + ".visibility")
     and float(np.abs(points(bare_body[0]) - SRC_AT_BIND["Body"]).max()) < 1e-3,
     "Playerchar [skeleton]: the body on its bind, where the source's skin shows it, Body_1P beside it "
     "hidden (%s)" % BARE)

# ------------------------------------------------------------------ the clothing on the rig
joints_before = len(cmds.ls(type="joint"))
lines = [armor.equip(RIG, row) for row in CLOTHES]
for line in lines:
    print("   ", line)
worn = armor.worn(RIG)
ok = sorted(worn) == sorted(r.key for r in CLOTHES) and len(cmds.ls(type="joint")) == joints_before
notes = []
for row in CLOTHES:
    node = worn.get(row.key, (None,))[0]
    if not node:
        ok = False
        continue
    space = cmds.listRelatives(node, parent=True, fullPath=True)[0]
    chan = max(abs(cmds.getAttr(node + "." + a)) for a in ("tx", "ty", "tz", "rx", "ry", "rz"))
    inherit = [cmds.getAttr(m + ".inheritsTransform") for m in live_meshes(node)]
    shown = all(cmds.getAttr(m + ".visibility") for m in live_meshes(node))
    ok = ok and shown and space.endswith("%s_armorSpace" % row.bone) and chan < 1e-9 and not any(inherit) \
        and "in its texture" in lines[CLOTHES.index(row)]
    notes.append("%s in %s" % (row.key, leaf(space)))
gate(4, ok, "all four worn, each in its bone's armor space at identity, its meshes shown and not inheriting, no joint "
     "added (%d): %s" % (len(cmds.ls(type="joint")) - joints_before, "; ".join(notes)))

MAPS = {}
worst_bind, counts = 0.0, []
for row in CLOTHES:
    node = worn[row.key][0]
    src_pts = [SRC_AT_BIND[n] for n in FROM[row.key]]
    for mesh in live_meshes(node):
        idx, worst = match(points(mesh), src_pts)
        MAPS[mesh] = (row.key, idx)
        worst_bind = max(worst_bind, worst)
        counts.append("%s %d" % (leaf(mesh), len(idx)))
gate(5, worst_bind < 1e-3, "at the bind every clothing vertex on a vertex of the source's own mesh to %.1e cm (%s)"
     % (worst_bind, ", ".join(counts)))
def engines(node):
    shape = cmds.listRelatives(node, shapes=True, fullPath=True, noIntermediate=True)[0]
    return tuple(sorted(set(cmds.listConnections(shape, type="shadingEngine") or [])))


body_mat = engines(BODY)
cloth_mats = set(engines(m) for m in MAPS)
gate(6, cloth_mats == {body_mat} and len(body_mat) == 1, "the clothes wear the body's own material: %s / %s" % (cloth_mats, body_mat))

# ------------------------------------------------------------------ a UE clip retargeted onto it
cmds.namespace(add="clip")
cmds.namespace(set=":clip")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
joints_seen = set(cmds.ls(type="joint", long=True))
mel.eval('FBXImport -f "%s";' % CLIP)
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in joints_seen]
tops = [j for j in new if not cmds.listRelatives(j, parent=True, type="joint")]
src = [j for j in tops if "pelvis" in joints_of(j)][0]
keyed = [j for j in new if cmds.listConnections(j, type="animCurve")]
first, last = cmds.findKeyframe(keyed, which="first"), cmds.findKeyframe(keyed, which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
cmds.select(main, src)
ok_rt, text_rt = rr.run_retarget()
print("   ", text_rt.splitlines()[0][:180])
CLIPJ, RIGJ = joints_of(src), joints_of(RIG)
print("    the clip: %d joints, not in it: %s" % (len(CLIPJ), [n for n in ("head", "neck_01", "hand_r") if n not in CLIPJ]))
frames = list(range(int(first), int(last) + 1, max(1, int((last - first) / 6))))
worst_bone, worst_skin, travel, start, worst_1p = 0.0, 0.0, 0.0, None, 0.0
for t in frames:
    cmds.currentTime(t)
    for name in [n for n in ("hand_r", "hand_l", "head", "neck_01", "foot_l", "foot_r", "pelvis") if n in CLIPJ]:
        a = np.array(cmds.xform(RIGJ[name], q=True, ws=True, t=True))
        b = np.array(cmds.xform(CLIPJ[name], q=True, ws=True, t=True))
        worst_bone = max(worst_bone, float(np.linalg.norm(a - b)))
    # the source's skeleton onto the rig's game bones, parents first: its own skin, the reference
    for name in sorted(CHK, key=lambda n: CHK[n].count("|")):
        if name in RIGJ:
            cmds.xform(CHK[name], worldSpace=True, matrix=cmds.getAttr(RIGJ[name] + ".worldMatrix[0]"))
    for mesh, (key, idx) in MAPS.items():
        want = np.vstack([points(SRC_MESH[n]) for n in FROM[key]])[idx]
        worst_skin = max(worst_skin, float(np.abs(points(mesh) - want).max()))
    worst_1p = max(worst_1p, float(np.abs(points(BODY_1P) - points(BODY)[ONE_P]).max()))
    head = np.array(cmds.xform(RIGJ["hand_r"], q=True, ws=True, t=True))
    start = head if start is None else start
    travel = max(travel, float(np.linalg.norm(head - start)))
gate(7, ok_rt and worst_bone < 0.1, "the clip retargeted onto the rig through the button: hands, head, feet, "
     "pelvis on the clip's to %.4f cm at %d frames" % (worst_bone, len(frames)))
gate(8, worst_skin < 1e-3 and travel > 10.0,
     "under the take every clothing vertex where the source's own skin puts it to %.1e cm (hand_r travels %.0f cm)"
     % (worst_skin, travel))
gate(17, worst_1p < 1e-3, "under the take every Body_1P vertex on its body vertex to %.1e cm" % worst_1p)
seen = []
for value in (1, 0):
    cmds.setAttr(main + ".view", value)
    seen.append((bool(cmds.getAttr(BODY + ".visibility")), bool(cmds.getAttr(BODY_1P + ".visibility"))))
gate(18, seen == [(False, True), (True, False)] and not cmds.listConnections(main + ".view", type="animCurve"),
     "Main.view untouched by the retarget (no key), 1P shows Body_1P alone, 3P the body: %s" % seen)
cmds.select(list(MAPS)[0])
named = skeleton.current_root()
cmds.select(clear=True)
gate(9, named == RIG, "a clothing mesh selected names its character: %s" % named)

fbx = SCRATCH + "/verify_playerchar_export.fbx"
if os.path.exists(fbx):
    os.remove(fbx)
animexport.export_hierarchy(fbx, root=RIG, start=first, end=last)
cmds.namespace(add="exp")
cmds.namespace(set=":exp")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
before_nodes = set(cmds.ls(long=True))
mel.eval('FBXImport -f "%s";' % fbx)
cmds.namespace(set=":")
arrived = [n for n in cmds.ls(long=True) if n not in before_nodes]
j_in, m_in = cmds.ls(arrived, type="joint") or [], cmds.ls(arrived, type="mesh") or []
gate(10, len(j_in) == 93 and not m_in, "the export read back: %d joints, %d meshes" % (len(j_in), len(m_in)))
cmds.delete([n for n in cmds.ls("exp:*", long=True, type="transform") or []
             if cmds.objExists(n) and not cmds.listRelatives(n, parent=True)])

# ------------------------------------------------------------------ another body, a twin
print("   ", character.add_character(catalog.character_by_key("Creep_Rig")))
cmds.select(clear=True)
CREEP = [r for r in maya_rigs.rigs() if r.namespace.endswith("Creep_Rig")][0].skeleton_root
nodes_before, ns_before = len(cmds.ls()), sorted(character.existing_namespaces())
refused = armor.equip(CREEP, catalog.armor_by_key("Playerchar_Pants"))
gate(11, "made for another body" in refused and len(cmds.ls()) == nodes_before
     and sorted(character.existing_namespaces()) == ns_before and not armor.worn(CREEP),
     "the Creep refused, the scene untouched: %r" % refused)
print("   ", character.add_character(catalog.character_by_key("Manny")))
cmds.select(clear=True)
manny_group = [g for g in cmds.ls(assemblies=True, long=True) if g.endswith("Manny_Skeleton_Character")][0]
MANNY = cmds.ls(manny_group + "|root", long=True)[0]
line = armor.equip(MANNY, catalog.armor_by_key("Playerchar_Pants"))
pants = armor.worn(MANNY).get("Playerchar_Pants", (None,))[0]
off = float(np.abs(points(live_meshes(pants)[0]) - SRC_AT_BIND["Pants"]).max()) if pants else 1e9
gate(12, pants is not None and off < 0.1, "the Manny skeleton wears the pants (%r), at its bind %.3f cm off the "
     "source (Manny's own calf offset)" % (line, off))

again = armor.equip(RIG, catalog.armor_by_key("Playerchar_Pants"))
gate(13, "replaced Pants" in again and len(armor.worn(RIG)) == 4 and len(namespaces("Playerchar_Pants")) == 2,
     "a second Equip replaces: %r, Pants namespaces %s" % (again, namespaces("Playerchar_Pants")))

# ------------------------------------------------------------------ Unequip, Delete
body_before = points(BODY)
lines = [armor.unequip(RIG, row.key) for row in CLOTHES]
left = [p for p in armor.pieces() if armor.inside(p[3], RIG)]
gate(14, all("taken off" in l for l in lines) and not left and not armor.worn(RIG)
     and len(namespaces("Playerchar_Helmet") + namespaces("Playerchar_Armor") + namespaces("Playerchar_Shield")) == 0
     and float(np.abs(points(BODY) - body_before).max()) < 1e-9,
     "Unequip of all four: nothing of them on the rig, their namespaces gone, the body unmoved (%s)" % lines)
line = deletion.delete_selected([pants], confirm=lambda text: True)
gate(15, not cmds.objExists(MANNY) and not namespaces("Playerchar_Pants") and not cmds.ls(manny_group),
     "Delete character through the pants takes the Manny and its pants: %r" % line)
gate(16, not [n for n in cmds.ls(type="skinCluster") if not cmds.listConnections(n + ".outputGeometry")],
     "no skinCluster left driving nothing")

print("checks passed" if not FAILS else "FAILURES: %s of %d" % (FAILS, TOTAL))
