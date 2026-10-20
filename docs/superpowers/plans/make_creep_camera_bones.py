"""The Creep's camera bones, in place: `camera_root` / `camera_bone` on the Creep rig and skeleton.

    mayapy make_creep_camera_bones.py [<asset .ma> ...]      (both Creep assets by default)

2026-10-20, the animator: «Если у нас в каких-то ригах нету камеры то ее нужно добавить. Нужно
переносить анимацию camera root и camera bone между скелетами и ригами» - and, asked, the bones AND
the camera (spec 2026-10-20-camera-and-weapon-bones-design.md). Measured first: Manny_Rig, the Manny
skeleton and the Orc D carry `camera_root` under the game root at local (0, 0, 164), rotate,
jointOrient and rotateAxis zero, and `camera_bone` under it at identity; the Creep's 91 joints have
neither. The Creep's root stands like Manny's (Z up: under `Armature` at -90 X, its own jointOrient
a few 1e-5 deg), so Manny's locals put the camera where Manny's stands and `camera.AXIS_OFFSET`
holds on it.

What it does, per asset:

- adds `camera_root` under the root with Manny's local, `camera_bone` under it at identity, xyz,
  at `weapon_r`'s radius, in the root's display layer;
- saves the bind pose again WHOLE over every joint and the `Armature` Null (trap 79's rule, the
  layout script's), so the new bones are in it and Maya's FBX exporter keeps the bind pose;
- checks: every other joint's world matrix, every vertex, the skins at their bind unchanged; on the
  rig, the new bones follow the root through a pose of Main / RootX_M and back;
- saves as .ma in place: Maya's script nodes cut (trap 74), banned words refused, the header the
  file had.

Idempotent: an asset whose root already holds `camera_root` is left alone. Opened through
`asset_dress.open_asset` (mayaUsd's extra `UsdDefaultRenderSettings` dropped, trap 121) from an
empty working folder (trap 119). One mayapy process per asset (trap 122).

Pipeline: the Creep's last step, after make_creep_textured_assets.py. Then
make_character_skeletons.py (the Auto card's templates pin the assets' sha1).
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asset_dress  # noqa: E402

PLUGIN = asset_dress.PLUGIN
ARGS = [a.replace("\\", "/") for a in sys.argv[1:]]
ASSETS = ARGS or [os.path.join(PLUGIN, "assets", n).replace("\\", "/")
                  for n in ("Creep_Rig.ma", "Creep_Skeleton.ma")]
# Manny's, measured on Manny_Rig.ma / Manny_Skeleton.ma / Orc_D_Rig.ma (2026-10-20)
CAMERA_ROOT_T = (0.0, 0.0, 164.0)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def meshes():
    out = {}
    for s in cmds.ls(type="mesh", long=True, noIntermediate=True):
        sel = om.MSelectionList()
        sel.add(s)
        out[cmds.ls(s, uuid=True)[0]] = om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)
    return out


def snapshot():
    joints = dict((cmds.ls(j, uuid=True)[0], wm(j)) for j in cmds.ls(type="joint", long=True))
    return joints, meshes()


def drift(before):
    joints, pts = before
    dj = max(mdiff(wm(cmds.ls(u, long=True)[0]), m) for u, m in joints.items())
    now = meshes()
    dv = max(max(a.distanceTo(b) for a, b in zip(pts[u], now[u])) for u in pts)
    return dj, dv


def bind_error():
    worst = 0.0
    for sc in cmds.ls(type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if src:
                m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src[0])
                worst = max(worst, mdiff(m, om.MMatrix()))
    return worst


def whole_bind_pose(joints, null):
    """make_creep_weapon_sockets.py's: the bind pose saved again over every joint and the Null."""
    skins = cmds.ls(type="skinCluster") or []
    old = set(p for sc in skins for p in cmds.listConnections(sc + ".bindPose", s=True, d=False) or []
              if cmds.objectType(p) == "dagPose")
    old.update(cmds.ls(type="dagPose"))
    new = cmds.dagPose(joints + [null], save=True, bindPose=True, name="skeldarBindPose_new")
    new = new[0] if isinstance(new, (list, tuple)) else new
    keep = set(cmds.ls(joints + [null], long=True))
    strays = [m for m in cmds.ls(cmds.dagPose(new, q=True, members=True) or [], long=True)
              if m not in keep]
    if strays:
        cmds.dagPose(strays, remove=True, name=new)
    for sc in skins:
        cmds.connectAttr(new + ".message", sc + ".bindPose", force=True)
    for pose in old:
        if cmds.objExists(pose):
            cmds.delete(pose)
    new = cmds.rename(new, "bindPose1")
    return new, len(cmds.dagPose(new, q=True, members=True) or [])


def add_joint(name, parent, translate, radius, layer):
    joint = cmds.createNode("joint", name=name, parent=parent, skipSelect=True)
    joint = cmds.ls(joint, long=True)[0]
    cmds.setAttr(joint + ".translate", *translate, type="double3")
    for attr in ("rotate", "jointOrient", "rotateAxis"):
        cmds.setAttr(joint + "." + attr, 0.0, 0.0, 0.0, type="double3")
    cmds.setAttr(joint + ".rotateOrder", 0)
    cmds.setAttr(joint + ".radius", radius)
    if layer:
        cmds.editDisplayLayerMembers(layer, joint, noRecurse=True)
    return joint


def relative_images():
    """The open resolved every shipped image against the file's own folder and stores it ABSOLUTE
    (a path of this machine): each file node is given its relative image back - from the empty
    working folder it stays relative (trap 119) - its colour space kept."""
    from maya_scenesetup import colour
    for node in cmds.ls(type="file") or []:
        if not cmds.attributeQuery(colour.ASSET_IMAGE, node=node, exists=True):
            continue
        relative = cmds.getAttr(node + "." + colour.ASSET_IMAGE)
        space = cmds.getAttr(node + ".colorSpace")
        cmds.setAttr(node + ".fileTextureName", relative, type="string")
        cmds.setAttr(node + ".colorSpace", space, type="string")
        assert cmds.getAttr(node + ".fileTextureName") == relative, node


def save_checked(asset, before_text):
    """Saved beside the asset, checked, then moved over it - a refused file never touches it."""
    new = asset[:-3] + ".new.ma"
    cmds.file(rename=new)
    cmds.file(save=True, type="mayaAscii", force=True)
    after = asset_dress.text_without_scripts(new)
    with open(new, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.write("\n".join(after))
    bad = [(n, w) for n, line in enumerate(after, 1) for w in asset_dress.BANNED if w in line]
    if bad:
        raise RuntimeError("banned content in %s (left as %s): %s" % (asset, new, bad[:10]))
    head_b, _ = asset_dress.split_header(before_text)
    head_a, _ = asset_dress.split_header(after)
    if head_b != head_a:
        raise RuntimeError("the header changed (left as %s): %s -> %s" % (new, head_b, head_a))
    os.replace(new, asset)
    print("  saved %s (%.1f MB), the header the same (%d lines)"
          % (asset, os.path.getsize(asset) / 1e6, len(head_a)))


def main(asset):
    print("=== " + asset)
    asset_dress.begin()
    before_text = asset_dress.open_asset(asset)
    roots = cmds.ls("|Armature|root", type="joint", long=True)
    assert len(roots) == 1, roots
    root, null = roots[0], "|Armature"
    if cmds.listRelatives(root, children=True, type="joint", fullPath=True) and \
            cmds.ls(root + "|camera_root"):
        print("  camera_root already there - not saved")
        return
    bones = dict((j.split("|")[-1], j) for j in cmds.ls(root, dag=True, type="joint", long=True))
    radius = cmds.getAttr(bones["weapon_r"] + ".radius")
    layers = [l for l in cmds.listConnections(root + ".drawOverride", type="displayLayer") or []
              if l != "defaultLayer"]
    layer = layers[0] if layers else None
    before = snapshot()
    camera_root = add_joint("camera_root", root, CAMERA_ROOT_T, radius, layer)
    camera_bone = add_joint("camera_bone", camera_root, (0.0, 0.0, 0.0), radius, layer)
    world = om.MTransformationMatrix(wm(camera_root))
    t = world.translation(om.MSpace.kWorld)
    r = [math.degrees(v) for v in world.rotation()]
    print("  camera_root at (%.3f, %.3f, %.3f) turned (%.3f, %.3f, %.3f); camera_bone %.2e off it"
          % (t.x, t.y, t.z, r[0], r[1], r[2], mdiff(wm(camera_bone), wm(camera_root))))
    assert abs(t.y - 164.0) < 0.5 and abs(r[0] + 90.0) < 0.1, (t, r)
    joints = cmds.ls(root, dag=True, type="joint", long=True)
    pose, members = whole_bind_pose(joints, null)
    dj, dv = drift(before)
    print("  bind pose %s over %d members; other joints moved %.2e, vertices %.2e cm, skins off "
          "their bind %.2e" % (pose, members, dj, dv, bind_error()))
    assert dj < 1e-9 and dv < 1e-4 and bind_error() < 1e-4, (dj, dv, bind_error())
    assert camera_root in cmds.ls(cmds.dagPose(pose, q=True, members=True), long=True)
    if cmds.objExists("Main"):
        local = wm(camera_root) * wm(root).inverse()
        posed = []
        for node, plug, value in (("Main", "translateX", 25.0), ("Main", "rotateY", 30.0),
                                  ("RootX_M", "translateY", -7.0)):
            if cmds.objExists(node + "." + plug):
                posed.append((node + "." + plug, cmds.getAttr(node + "." + plug)))
                cmds.setAttr(node + "." + plug, value)
        cmds.dgdirty(allPlugs=True)
        moved = (om.MTransformationMatrix(wm(root)).translation(om.MSpace.kWorld) -
                 om.MTransformationMatrix(before[0][cmds.ls(root, uuid=True)[0]])
                 .translation(om.MSpace.kWorld)).length()
        follows = mdiff(wm(camera_root) * wm(root).inverse(), local)
        for plug, value in posed:
            cmds.setAttr(plug, value)
        cmds.dgdirty(allPlugs=True)
        print("  posed through Main/RootX_M: root moved %.2f, camera_root on the root %.2e" %
              (moved, follows))
        assert moved > 1.0 and follows < 1e-9
    relative_images()
    save_checked(asset, before_text)


if len(ASSETS) > 1:
    asset_dress.run_each(ASSETS, __file__)
else:
    main(ASSETS[0])
print("CAMERA BONES DONE")
