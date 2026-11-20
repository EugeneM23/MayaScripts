"""Build the Main Hero assets: the textures, the source, the rig, the skeleton and the clothing.

    mayapy make_mainhero_assets.py               every step, each in its own mayapy (trap 122)
    mayapy make_mainhero_assets.py textures      SkeldarAnim/assets/MainHero/*.jpg
    mayapy make_mainhero_assets.py source        sources/mainhero/MainHero_Source.mb
    mayapy make_mainhero_assets.py rig           SkeldarAnim/assets/MainHero_Rig.ma
    mayapy make_mainhero_assets.py skeleton      SkeldarAnim/assets/MainHero_Skeleton.ma
    mayapy make_mainhero_assets.py armor <key>   SkeldarAnim/assets/Armor/<key>.ma

2026-11-20, the animator: «взяти актуального головного перонажа з проекту Атон і додати в плагін
Skeldar по всім правилам пайплайну, і скелет і ріг і одяг, наплічники окремо».  The hero is what
Atone's BP_Character wears, /Game/Characters/Main_Hero/MainHero/SK_MainHeroProto_Skinned4, on
SK_Mannequin_proto: its body bones are Manny's to 0.07 cm (Manny's own calf offset), so this is the
Playerchar's road (make_playerchar_assets.py, whose helpers it uses): Manny_Rig with Manny's meshes
out and the hero's body in, its skeleton, and the outfit as skinned clothing.

Unreal's FBX export drops the six sections that run cloth simulation (cape, skirts, three chain
strands), so sources/mainhero/SK_MainHero_Full.fbx was written from a Geometry Script copy of the
mesh (export_mainhero_from_unreal.py + the full-mesh step): 19 material slots, LOD0, the original
vertex order, the same skeleton.  The three `artefacts_sim_*_proxy` slots are the cloth simulation's
cages (trap 92) and are left out; the bones `joint`, `AB_Armor_Shoulder_L/R` carry no weight and go.

- body (the character, as the Playerchar: «по умолчанию без одягу» is the rule): the head (slot 9),
  eyes (8), arms (11) and the suit with its boots (10) -- without the suit the body is a head and
  arms -- one mesh `Body`, three materials: the suit in its own colour and normal maps, the skin and
  the eyes in flat colours (M_HeroBody has no texture).  `Body_1P` the Playerchar's limb rule.
- clothing (PIECES): helmet, chainmail (coif + neck chains), chains (the three hanging strands),
  cape, skirt, shoulders -- the three shoulder layers, a piece of their own as asked.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PLUGIN = os.path.join(REPO, "SkeldarAnim")
ASSETS = os.path.join(PLUGIN, "assets").replace("\\", "/")
SRC_DIR = os.path.join(REPO, "sources", "mainhero").replace("\\", "/")
FBX = SRC_DIR + "/SK_MainHero_Full.fbx"
SOURCE = SRC_DIR + "/MainHero_Source.mb"
RIG = ASSETS + "/MainHero_Rig.ma"
SKELETON = ASSETS + "/MainHero_Skeleton.ma"
MAPS = "MainHero/"
OUTFIT = "MainHero_Outfit_Color.jpg"
OUTFIT_N = "MainHero_Outfit_Normal.jpg"
CHAINS = "MainHero_Chains_Color.jpg"
CHAINS_N = "MainHero_Chains_Normal.jpg"
TEXTURES = {OUTFIT: ("T_MainHero_Outfit01_BC", False), OUTFIT_N: ("T_MainHero_Outfit01_N", True),
            CHAINS: ("T_MainHero_Chains01_BC", False), CHAINS_N: ("T_mainHero_chains01_N", True)}
GROUP = "SKM_MainHero"
SKIN_RGB = (0.62, 0.47, 0.40)
EYES_RGB = (0.32, 0.25, 0.22)
# slot -> what it is (Unreal's material slot index on SK_MainHeroProto_Skinned4)
BODY_SLOTS = {9: "skin", 11: "skin", 8: "eyes", 10: "outfit"}
PIECES = {
    "MainHero_Helmet": [4],
    "MainHero_Chainmail": [12, 1],
    "MainHero_Chains": [0, 2, 3],
    "MainHero_Cape": [5],
    "MainHero_Skirt": [6, 7],
    "MainHero_Shoulders": [16, 17, 18],
}
DROPPED = (13, 14, 15)
EXTRA_JOINTS = ("joint", "AB_Armor_Shoulder_L", "AB_Armor_Shoulder_R")


def drive():
    steps = [["textures"], ["source"], ["rig"], ["skeleton"]] + [["armor", k] for k in PIECES]
    for step in steps:
        print("=" * 20, " ".join(step))
        sys.stdout.flush()
        code = subprocess.call([sys.executable, os.path.abspath(__file__)] + step)
        if code:
            raise SystemExit("step %s failed (%d)" % (" ".join(step), code))


def build_textures():
    """The colour maps as they are, the normal maps (Unreal's DirectX) with green flipped; 2048 JPG."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtGui
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])  # noqa: F841
    out_dir = ASSETS + "/MainHero"
    os.makedirs(out_dir, exist_ok=True)
    for name, (src, normal) in TEXTURES.items():
        img = QtGui.QImage(SRC_DIR + "/textures/" + src + ".png")
        assert not img.isNull(), src
        img = img.convertToFormat(QtGui.QImage.Format_RGB32)
        if img.width() > 2048:
            img = img.scaled(2048, 2048)
        if normal:
            import numpy as np
            arr = np.frombuffer(img.bits(), dtype=np.uint8).reshape(img.height(), img.bytesPerLine())
            arr = arr[:, :img.width() * 4].reshape(img.height(), img.width(), 4).copy()
            arr[:, :, 1] = 255 - arr[:, :, 1]                 # BGRA in memory: index 1 is green
            img = QtGui.QImage(arr.data, img.width(), img.height(), img.width() * 4,
                               QtGui.QImage.Format_RGB32).copy()
        assert img.save(out_dir + "/" + name, "JPG", 95), name
        print("%-30s %dx%d %.1f MB" % (name, img.width(), img.height(), os.path.getsize(out_dir + "/" + name) / 1e6))


if __name__ == "__main__" and len(sys.argv) == 1:
    drive()
    raise SystemExit(0)
if __name__ == "__main__" and sys.argv[1] == "textures":
    build_textures()
    raise SystemExit(0)

sys.path.insert(0, HERE)
sys.path.insert(0, PLUGIN)
import make_playerchar_assets as pc  # noqa: E402  (initializes maya.standalone)
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402
import asset_dress  # noqa: E402

BANNED = pc.BANNED + ("srcH:", "SK_MainHero_Full", "artefacts_sim")


def slot_faces(transform):
    """{slot index: [face ids]} read off the FBX's shading groups (`<mesh>SG<n>` is slot n)."""
    fn = pc.mfn(transform)
    shaders, ids = fn.getConnectedShaders(pc.dag(transform).instanceNumber())
    names = [om.MFnDependencyNode(s).name() for s in shaders]
    slot_of = []
    for n in names:
        tail = n.rsplit("SG", 1)[1]
        slot_of.append(int(tail) if tail else 0)
    out = {}
    for f, i in enumerate(ids):
        out.setdefault(slot_of[i], []).append(f)
    return out


# ------------------------------------------------------------------ source
def build_source():
    asset_dress.begin()
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval('FBXImport -f "%s"' % FBX)
    top = [t for t in cmds.ls(assemblies=True, long=True) if t.endswith("SK_MainHero_Full")][0]
    mesh = cmds.ls(top + "|SK_MainHero_Full", type="transform", long=True)[0]
    skin = pc.skin_of(mesh)
    cmds.skinCluster(skin, e=True, removeUnusedInfluence=True)
    infl = [pc.leaf(j) for j in cmds.skinCluster(skin, q=True, influence=True)]
    assert not set(infl) & set(EXTRA_JOINTS), infl
    slots = slot_faces(mesh)
    assert sorted(slots) == list(range(19)), sorted(slots)
    # the skeleton out of the importer's -90 X wrapper, every bone where it stood
    root = cmds.ls(top + "|root", type="joint", long=True)[0]
    joints = sorted(cmds.ls(root, dag=True, type="joint", long=True), key=lambda j: j.count("|"))
    world = [(pc.uid(j), pc.wm(j)) for j in joints]
    root_id = pc.uid(root)
    cmds.parent(root, world=True)
    for u, m in world:
        j = pc.path(u)
        for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(j + "." + a, lock=False)
        cmds.xform(j, worldSpace=True, matrix=list(m))
    drift = max(max(abs(a - b) for a, b in zip(list(m), list(pc.wm(pc.path(u))))) for u, m in world)
    assert drift < 1e-6, drift
    for name in EXTRA_JOINTS:
        for j in cmds.ls(name, type="joint", long=True):
            kids = cmds.listRelatives(j, children=True, fullPath=True) or []
            assert not kids, (j, kids)
            cmds.delete(j)
    names = dict((pc.leaf(j), j) for j in cmds.ls("|root", dag=True, type="joint", long=True))
    print("skeleton: %d joints, re-seated (drift %.1e); skin %d influences" % (len(names), drift, len(infl)))
    group = cmds.createNode("transform", name="MESH", skipSelect=True)
    made = []
    # the body: four slots in one mesh, each face's kind kept on it
    body_faces = sorted(f for s in BODY_SLOTS for f in slots[s])
    kinds = dict((f, BODY_SLOTS[s]) for s in BODY_SLOTS for f in slots[s])
    for name, faces, face_kinds in [("Body", body_faces, [kinds[f] for f in body_faces])] + \
            [(key.split("_", 1)[1], sorted(f for s in sl for f in slots[s]), None) for key, sl in PIECES.items()]:
        copy, kept = pc.copy_mesh(mesh, name, faces, tol=1e-3)
        sk = pc.bind_like(copy, kept, mesh, names, name)
        copy = cmds.ls(cmds.parent(copy, "|MESH")[0], long=True)[0]
        if face_kinds:
            cmds.addAttr(copy, longName="skeldarFaceKinds", dataType="string")
            cmds.setAttr(copy + ".skeldarFaceKinds", json.dumps(face_kinds), type="string")
        made.append((copy, kept, sk))
    src_points = pc.mfn(mesh).getPoints(om.MSpace.kWorld)
    cmds.delete(top)
    for copy, kept, sk in made:
        cmds.dgdirty(copy)
        now = pc.mfn(copy).getPoints(om.MSpace.kWorld)
        still = max(now[k].distanceTo(src_points[v]) for k, v in enumerate(kept))
        print("  %-12s %6d vertices %6d faces, on the FBX's to %.1e cm, skin off its bind %.1e"
              % (pc.leaf(copy), len(kept), pc.mfn(copy).numPolygons, still, pc.bind_error(sk)))
        assert still < 1e-3 and pc.bind_error(sk) < 1e-4
    for shape in cmds.ls("|MESH", dag=True, type="mesh", long=True, noIntermediate=True):
        cmds.sets(shape, edit=True, forceElement="initialShadingGroup")
    kinds_gone = pc.drop_unused(["|root", "|MESH"])
    pc.whole_bind_pose("|root", [s for _c, _k, s in made])
    print("deleted:", sorted(kinds_gone.items(), key=lambda kv: -kv[1])[:10])
    print("assemblies:", cmds.ls(assemblies=True))
    cmds.file(rename=SOURCE)
    cmds.file(save=True, type="mayaBinary", force=True)
    print("saved %s (%.1f MB)" % (SOURCE, os.path.getsize(SOURCE) / 1e6))


def flat_material(key, rgb):
    mat = cmds.shadingNode(pc.colour.SHADER, asShader=True, name=key)
    pc.colour.dress(mat)
    cmds.setAttr(mat + ".color", *rgb, type="double3")
    engine = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=mat + "SG")
    cmds.connectAttr(mat + ".outColor", engine + ".surfaceShader", force=True)
    return mat, engine


def dress_body(meshes_kinds):
    """The suit in its maps, the skin and the eyes flat, face by face."""
    _m, outfit = asset_dress.material(MAPS, "MainHero_Outfit", OUTFIT, OUTFIT_N)
    _m, skin = flat_material("MainHero_Skin", SKIN_RGB)
    _m, eyes = flat_material("MainHero_Eyes", EYES_RGB)
    engines = {"outfit": outfit, "skin": skin, "eyes": eyes}
    for mesh, kinds in meshes_kinds:
        for kind, engine in engines.items():
            faces = ["%s.f[%d]" % (mesh, f) for f, k in enumerate(kinds) if k == kind]
            if faces:
                cmds.sets(faces, edit=True, forceElement=engine)


# ------------------------------------------------------------------ rig
def build_rig():
    asset_dress.begin()
    asset_dress.open_asset(ASSETS + "/Manny_Rig.ma")
    root = cmds.ls("|root", type="joint", long=True)[0]
    game = dict((pc.leaf(j), j) for j in cmds.ls(root, dag=True, type="joint", long=True))
    assert len(game) == 93, len(game)
    manny = cmds.ls("|SKM_Manny_Simple", long=True)[0]
    history = []
    for shape in cmds.listRelatives(manny, allDescendents=True, type="mesh", fullPath=True) or []:
        history += [h for h in cmds.listHistory(shape) if cmds.nodeType(h) in
                    ("skinCluster", "blendShape", "tweak", "groupParts", "groupId")]
    main = cmds.ls("|Group|MotionSystem|MainSystem|Main", long=True)[0]
    conds = [c for c in cmds.listConnections(main + ".view", source=False, destination=True) or []
             if cmds.nodeType(c) == "condition"]
    cmds.delete(manny)
    cmds.delete([n for n in history + conds if cmds.objExists(n)])
    cmds.deleteAttr(main + ".view")
    for lod in cmds.ls(type="lodGroup"):
        cmds.delete(lod)

    cmds.file(SOURCE, i=True, type="mayaBinary", namespace="srcH", ignoreVersion=True)
    src_body = cmds.ls("srcH:Body", type="transform", long=True)[0]
    src_skin = pc.skin_of(src_body)
    worst = 0.0
    for idx in cmds.getAttr(src_skin + ".matrix", multiIndices=True):
        joint = cmds.listConnections("%s.matrix[%d]" % (src_skin, idx), s=True, d=False)[0]
        bind = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (src_skin, idx))).inverse()
        worst = max(worst, max(abs(a - b) for a, b in zip(list(bind), list(pc.wm(game[pc.leaf(joint)])))))
    print("the rig's game joints on the hero's bind to %.3f" % worst)
    assert worst < 0.1, worst            # Manny's own calf_l, 0.073 cm
    src_points = pc.mfn(src_body).getPoints(om.MSpace.kWorld)
    kinds = json.loads(cmds.getAttr(src_body + ".skeldarFaceKinds"))

    body, kept = pc.copy_mesh(src_body, pc.BODY)
    cmds.createNode("transform", name=GROUP, skipSelect=True)
    body = cmds.ls(cmds.parent(body, "|" + GROUP)[0], long=True)[0]
    skin = pc.bind_like(body, kept, src_body, game, pc.BODY)
    faces_1p = pc.first_person_faces(src_body)
    body1, kept1 = pc.copy_mesh(src_body, pc.BODY_1P, faces_1p)
    body1 = cmds.ls(cmds.parent(body1, "|" + GROUP)[0], long=True)[0]
    skin1 = pc.bind_like(body1, kept1, src_body, game, pc.BODY_1P)
    pose = pc.whole_bind_pose(root, [skin, skin1])
    for mesh, keep, sc in ((body, kept, skin), (body1, kept1, skin1)):
        cmds.dgdirty(mesh)
        now = pc.mfn(mesh).getPoints(om.MSpace.kWorld)
        still = max(now[k].distanceTo(src_points[v]) for k, v in enumerate(keep))
        print("%s: %d vertices, %d faces, skin off its bind %.2e, on the hero's to %.2e cm, %s"
              % (pc.leaf(mesh), len(keep), pc.mfn(mesh).numPolygons, pc.bind_error(sc), still, pose))
        assert still < 1e-3 and pc.bind_error(sc) < 1e-4
    cmds.namespace(removeNamespace="srcH", deleteNamespaceContent=True)
    dress_body([(body, kinds), (body1, [kinds[f] for f in faces_1p])])
    for mesh in (body, body1):
        for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(mesh + "." + a, lock=True)
    cmds.addAttr(main, longName=pc.VIEW, attributeType="enum", enumName="3P:1P", defaultValue=0, keyable=False)
    cmds.setAttr(main + "." + pc.VIEW, channelBox=True)
    for mesh, value in ((body, 0), (body1, 1)):
        cond = cmds.createNode("condition", name=pc.leaf(mesh) + "_viewCondition", skipSelect=True)
        cmds.connectAttr(main + "." + pc.VIEW, cond + ".firstTerm")
        cmds.setAttr(cond + ".secondTerm", value)
        cmds.setAttr(cond + ".colorIfTrueR", 1.0)
        cmds.setAttr(cond + ".colorIfFalseR", 0.0)
        cmds.connectAttr(cond + ".outColorR", mesh + ".visibility", force=True)
    for value, shown, hidden in ((1, body1, body), (0, body, body1)):
        cmds.setAttr(main + "." + pc.VIEW, value)
        assert cmds.getAttr(shown + ".visibility") and not cmds.getAttr(hidden + ".visibility"), value
    gone = asset_dress.unused_shading()
    print("shading taken out:", sorted(set(t for _n, t in gone)))
    assert sorted(cmds.ls(type="skinCluster")) == sorted([skin, skin1]), cmds.ls(type="skinCluster")
    assert cmds.ls(type="dagPose") == ["bindPose1"], cmds.ls(type="dagPose")
    print("images:", asset_dress.check_images(MAPS, [OUTFIT, OUTFIT_N]))
    print("assemblies:", cmds.ls(assemblies=True))
    pc.save_ascii(RIG, BANNED)


# ------------------------------------------------------------------ skeleton
def build_skeleton():
    pc.RIG, pc.SKELETON, pc.GROUP = RIG, SKELETON, GROUP
    pc.MAPS, pc.ATLAS = MAPS, OUTFIT
    pc.BANNED = BANNED
    check = asset_dress.check_images
    asset_dress.check_images = lambda maps, _images: check(maps, [OUTFIT, OUTFIT_N])
    pc.build_skeleton()


# ------------------------------------------------------------------ armor
def build_armor(key):
    asset_dress.begin()
    cmds.file(SOURCE, open=True, force=True, executeScriptNodes=False)
    joints = dict((pc.leaf(j), j) for j in cmds.ls("|root", dag=True, type="joint", long=True))
    src = cmds.ls("|MESH|" + key.split("_", 1)[1], type="transform", long=True)[0]
    name = key.split("_", 1)[1]
    mesh, kept = pc.copy_mesh(src, name + "_tmp")
    sk = pc.bind_like(mesh, kept, src, joints, name)
    mesh_id, skin_id = pc.uid(mesh), pc.uid(sk)
    cmds.delete("|MESH")
    mesh = cmds.rename(pc.path(mesh_id), name)
    cmds.rename(cmds.listRelatives(pc.path(mesh_id), shapes=True, fullPath=True, noIntermediate=True)[0],
                name + "Shape")
    cmds.rename(cmds.ls(skin_id)[0], name + "_skinCluster")
    cmds.createNode("transform", name=key, skipSelect=True)
    cmds.parent(pc.path(mesh_id), "|" + key)
    cmds.setAttr(pc.path(mesh_id) + ".inheritsTransform", 0)
    for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(pc.path(mesh_id) + "." + a, lock=True)
    for shape in cmds.ls("|" + key, dag=True, type="mesh", long=True, noIntermediate=True):
        cmds.sets(shape, edit=True, forceElement="initialShadingGroup")
    pc.drop_unused(["|root", "|" + key])
    skins = [cmds.ls(skin_id)[0]]
    pc.whole_bind_pose(cmds.ls("|root", long=True)[0], skins)
    worst = max(pc.bind_error(sc) for sc in skins)
    assert worst < 1e-4, worst
    assert sorted(cmds.ls(assemblies=True)) == sorted(["persp", "top", "front", "side", "root", key]), \
        cmds.ls(assemblies=True)
    print("  %s: %d vertices, skin off its bind %.1e" % (key, len(kept), worst))
    pc.save_ascii(ASSETS + "/Armor/" + key + ".ma", BANNED)


if __name__ == "__main__":
    step = sys.argv[1]
    {"source": build_source, "rig": build_rig, "skeleton": build_skeleton}.get(
        step, lambda: build_armor(sys.argv[2]) if step == "armor" else (_ for _ in ()).throw(SystemExit(step)))()
    import maya.standalone
    maya.standalone.uninitialize()
