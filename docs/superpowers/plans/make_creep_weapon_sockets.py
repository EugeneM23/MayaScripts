"""The Creep's weapon bones in UE's orientation, in place: one weapon socket for every rig.

    mayapy make_creep_weapon_sockets.py [<asset .ma> ...]      (both Creep assets by default)

2026-09-30, the animator: «некоторые виды оружия нужно поворачивать на 90, а некоторые сразу
встают в руку, давай сделаем так, чтобы по умолчанию все виды оружия вставлялись в руку правильно
без офсетов» - and, asked whether the Creep's bones should follow the same standard: «Yes, one
standard». Measured first (spec 2026-09-30-weapon-socket-and-inventory-skin-design.md): Manny's
and the Orc D's `weapon_r` is UE's, the fist's grip line pinky_01 -> index_01 along its +Z (0.978)
and the palm normal along -Y, `weapon_l` its behaviour mirror (grip line -Z). The Creep's (ours,
2026-09-24: `weapon_test` turned half a turn about Z, `weapon_l` its mirror) hold the grip line
along +Y (0.995) - a quarter turn off. And a UE clip retargeted onto the Creep hands its
`weapon_r` UE's local rotation anyway (helper bones travel relative to the hand on a
rotation-only rig), so a sword that fitted the Creep at its bind stood 101.9 deg off the fist
mid-take.

So each bone is turned a quarter turn about its own X - new local = Q . old local, row vectors,
Q = Rx(-90) for weapon_r, Rx(+90) for weapon_l, whichever of the two brings the measured grip
line onto the wanted +-Z - and nothing else moves:

- only the rotate channels change (jointOrient and rotateAxis zero, rotate order xyz asserted),
  the position stays;
- the bindPreMatrix of every skinCluster the bone influences (weapon_r in skinCluster5) is
  re-expressed as its new WM^-1, the bind pose saved again WHOLE over every joint and the
  `Armature` Null (trap 79 - the layout script's rule);
- checked unchanged: every other joint's world matrix, each weapon bone's position, every
  vertex, the skins at their bind, and on the rig the same under a pose of Main / RootX_M.

Idempotent BY MEASUREMENT: a bone whose grip line already lies along the wanted +-Z is left
alone, one along +-Y is turned, anything else is refused by name; nothing turned, nothing saved.
Then saved as .ma in place, Maya's own script nodes cut (trap 74), banned words refused.

The Creep Sword stays exactly where it stood on the Creep: its node carries R(0,45,0) .
R(catalog.SOCKET_TURN) now, and Rx(90) . Rx(-90) = I.

Pipeline: the last step, after make_creep_armature_layout.py.
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)

ASSETS = [a.replace("\\", "/") for a in sys.argv[1:]] or [
    os.path.join(PLUGIN, "assets", n).replace("\\", "/") for n in ("Creep_Rig.ma", "Creep_Skeleton.ma")]
BANNED = ("createNode script", "vaccine", "breed_gene", "rpHold_", "cascadeurLayoutNegate")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(p, quiet=True)

# side: (the grip line's wanted sign on the bone's Z)
WANT = {"r": 1.0, "l": -1.0}


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def rx(degrees):
    return om.MEulerRotation(math.radians(degrees), 0.0, 0.0).asMatrix()


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


def drift(before, skip=()):
    joints, pts = before
    dj = max(mdiff(wm(cmds.ls(u, long=True)[0]), m) for u, m in joints.items() if u not in skip)
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
    skins = cmds.ls(type="skinCluster") or []
    old = set(p for sc in skins for p in cmds.listConnections(sc + ".bindPose", s=True, d=False) or []
              if cmds.objectType(p) == "dagPose")
    old.update(cmds.ls(type="dagPose"))
    new = cmds.dagPose(joints + [null], save=True, bindPose=True, name="skeldarBindPose_new")
    new = new[0] if isinstance(new, (list, tuple)) else new
    keep = set(cmds.ls(joints + [null], long=True))
    strays = [m for m in cmds.ls(cmds.dagPose(new, q=True, members=True) or [], long=True) if m not in keep]
    if strays:
        cmds.dagPose(strays, remove=True, name=new)
    for sc in skins:
        cmds.connectAttr(new + ".message", sc + ".bindPose", force=True)
    for pose in old:
        if cmds.objExists(pose):
            cmds.delete(pose)
    new = cmds.rename(new, "bindPose1")
    return new, len(cmds.dagPose(new, q=True, members=True) or [])


def cut_and_check(path):
    with open(path, encoding="utf-8", errors="surrogateescape") as fh:
        lines = fh.readlines()
    kept, skipping, cut = [], False, 0
    for line in lines:
        if line.startswith("createNode script "):
            skipping, cut = True, cut + 1
            continue
        if skipping and line[:1] not in ("\t", " "):
            skipping = False
        if not skipping:
            kept.append(line)
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.writelines(kept)
    bad = [(n, w) for n, line in enumerate(kept, 1) for w in BANNED if w in line]
    if bad:
        raise RuntimeError("banned content in %s: %s" % (path, bad[:10]))
    return cut


def pos(n):
    return om.MVector(cmds.xform(n, q=True, ws=True, t=True))


def grip_line(bones, side, frame):
    """The fist's grip line pinky_01 -> index_01, unit, in the axes of `frame`."""
    v = (pos(bones["index_01_" + side]) - pos(bones["pinky_01_" + side])).normal()
    inverse = frame.inverse()
    local = om.MVector(v.x * inverse[0] + v.y * inverse[4] + v.z * inverse[8],
                       v.x * inverse[1] + v.y * inverse[5] + v.z * inverse[9],
                       v.x * inverse[2] + v.y * inverse[6] + v.z * inverse[10])
    return local.normal()


def rotation_only(m):
    t = om.MTransformationMatrix(m)
    t.setTranslation(om.MVector(0, 0, 0), om.MSpace.kTransform)
    return t.asMatrix()


def turn(bone, side, bones):
    """Turn `bone` into UE's convention; answers what was done, or raises."""
    want = WANT[side]
    k = grip_line(bones, side, rotation_only(wm(bone)))
    if abs(k.z) > 0.9 and k.z * want > 0:
        return "already in UE's convention (grip line %s)" % [round(v, 3) for v in k]
    if abs(k.y) <= 0.9:
        raise RuntimeError("%s: the grip line %s lies along neither +-Y nor +-Z - refused"
                           % (bone, [round(v, 3) for v in k]))
    for attr in ("jointOrient", "rotateAxis"):
        values = cmds.getAttr(bone + "." + attr)[0]
        assert max(abs(v) for v in values) < 1e-9, (bone, attr, values)
    assert cmds.getAttr(bone + ".rotateOrder") == 0, bone
    for degrees in (-90.0, 90.0):
        q = rx(degrees)
        # the grip line in the turned frame: k . Q^-1
        qi = q.inverse()
        kz = k.x * qi[2] + k.y * qi[6] + k.z * qi[10]
        if kz * want > 0.9:
            break
    else:
        raise RuntimeError("%s: no quarter turn about X brings %s onto %+d Z" % (bone, k, want))
    local = om.MMatrix(cmds.xform(bone, q=True, matrix=True, objectSpace=True))
    new = om.MTransformationMatrix(q * local)
    euler = new.rotation(asQuaternion=False).reorder(om.MEulerRotation.kXYZ)
    for attr in ("rx", "ry", "rz"):
        cmds.setAttr(bone + "." + attr, lock=False)
    cmds.setAttr(bone + ".rotate", *[math.degrees(v) for v in (euler.x, euler.y, euler.z)],
                 type="double3")
    after = grip_line(bones, side, rotation_only(wm(bone)))
    assert after.z * want > 0.99, (bone, after)
    for sc in sorted(set(cmds.listConnections(bone + ".worldMatrix", type="skinCluster") or [])):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False) or []
            if src and cmds.ls(src[0], long=True)[0] == bone:
                cmds.setAttr("%s.bindPreMatrix[%d]" % (sc, idx), list(wm(bone).inverse()),
                             type="matrix")
    return "turned %+.0f about its X: grip line %s -> %s" % (
        degrees, [round(v, 3) for v in k], [round(v, 3) for v in after])


for asset in ASSETS:
    print("=== " + asset)
    cmds.file(asset, open=True, force=True, executeScriptNodes=False)
    roots = cmds.ls("|Armature|root", type="joint", long=True)
    assert len(roots) == 1, roots
    root, null = roots[0], "|Armature"
    joints = cmds.ls(root, dag=True, type="joint", long=True)
    bones = dict((j.split("|")[-1], j) for j in joints)
    before = snapshot()
    turned, weapon_uuids, positions = False, set(), {}
    for side in ("r", "l"):
        bone = bones["weapon_" + side]
        weapon_uuids.add(cmds.ls(bone, uuid=True)[0])
        positions[bone] = pos(bone)
        what = turn(bone, side, bones)
        turned = turned or what.startswith("turned")
        print("  weapon_%s: %s" % (side, what))
    if not turned:
        print("  nothing turned - not saved")
        continue
    pose, members = whole_bind_pose(joints, null)
    dj, dv = drift(before, skip=weapon_uuids)
    dp = max((pos(b) - p).length() for b, p in positions.items())
    print("  bind pose %s over %d members; other joints moved %.2e, weapon bones' positions %.2e,"
          " vertices %.2e cm, skins off their bind %.2e" % (pose, members, dj, dp, dv, bind_error()))
    assert dj < 1e-9 and dp < 1e-9 and dv < 1e-4 and bind_error() < 1e-4, (dj, dp, dv, bind_error())
    main = cmds.ls("Main", type="transform")
    if main:
        posed = []
        for node, plug, value in (("Main", "translateX", 25.0), ("Main", "rotateY", 30.0),
                                  ("RootX_M", "translateY", -7.0)):
            if cmds.objExists(node + "." + plug):
                posed.append((node + "." + plug, cmds.getAttr(node + "." + plug)))
                cmds.setAttr(node + "." + plug, value)
        cmds.dgdirty(allPlugs=True)
        moved = mdiff(wm(root), before[0][cmds.ls(root, uuid=True)[0]])
        for plug, value in posed:
            cmds.setAttr(plug, value)
        cmds.dgdirty(allPlugs=True)
        back = drift(before, skip=weapon_uuids)
        print("  posed through Main/RootX_M: root moved %.2f, back at build pose to %.2e / %.2e"
              % ((moved,) + back))
        assert moved > 1.0 and back[0] < 1e-6 and back[1] < 1e-4
    cmds.file(rename=asset)
    cmds.file(save=True, type="mayaAscii", force=True)
    print("  saved; script nodes cut: %d; %.1f MB" % (cut_and_check(asset), os.path.getsize(asset) / 1e6))
print("SOCKETS DONE")
