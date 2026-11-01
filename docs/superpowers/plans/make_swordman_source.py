"""The Swordman's source: our 55 bones on HIS bind, the body rewired onto them.

    mayapy make_swordman_source.py

Reads  sources/swordman/Swordman_Scene.mb -- a copy of the animator's own scene,
exported over port 7006 on 2026-11-01 while they worked in it.
Writes sources/swordman/Swordman_Source.mb.

He came in on a 3ds Max "Base Human" Biped: 25 joints with no fingers, no toes,
no twists and no root at the floor, the pelvis carrying an inch-to-cm scale of
2.54 that everything below inherits.  Spec:
docs/superpowers/specs/2026-11-01-swordman-design.md.

Two measurements decide this script, both made before it was written:

  * `dagPose -restore bindPose1` does NOT reproduce the bind the mesh uses --
    the palms land 3.43 cm off, the collarbones 1.15, the ribcage 0.36, while
    the pelvis and legs are exact.  The skinCluster's `bindPreMatrix` is the
    bind (trap 176).  Our 17 shared joints are built from it, orientation
    included, so the skin is REWIRED and not re-bound: every vertex stays where
    it is.  The dagPose is still read, for one thing only -- the shape of the
    unskinned spine and neck, which carry no weight.

  * His sword and shield are unskinned children of the scaled chain, so their
    world size is 2.54x their own points: a 117 cm blade, not 46 (trap 86 --
    the same trap once shrank the Creep's sword and nobody noticed for days).
    Their WORLD matrices are carried across, never their locals.

Idempotent: a second run reads the same source and writes the same file.
"""
import math
import os
import shutil
import sys
import tempfile

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds
import maya.api.OpenMaya as om

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
SRC = os.path.join(REPO, "sources", "swordman", "Swordman_Scene.mb")
DST = os.path.join(REPO, "sources", "swordman", "Swordman_Source.mb")

PREFIX = "BaseFBXASC032Human"
SKIN = "skinCluster1"
BODY = "|Cylinder003"
SWORD, SHIELD = "Object014", "Object013"          # right hand, left hand

GROUP = "Swordman"
MESH_NAMES = {BODY: "Swordman_Body", SWORD: "Swordman_Sword", SHIELD: "Swordman_Shield"}

# his bone -> ours.  These 17 are the skinned ones, and they are placed on his
# bind exactly; everything else in the 55 is placed by rule.
PAIRS = {
    "Pelvis": "pelvis", "Ribcage": "spine_05", "Head": "head",
    "LCollarbone": "clavicle_l", "LUpperarm": "upperarm_l",
    "LForearm": "lowerarm_l", "LPalm": "hand_l",
    "RCollarbone": "clavicle_r", "RUpperarm": "upperarm_r",
    "RForearm": "lowerarm_r", "RPalm": "hand_r",
    "LThigh": "thigh_l", "LCalf": "calf_l", "LFoot": "foot_l",
    "RThigh": "thigh_r", "RCalf": "calf_r", "RFoot": "foot_r",
}
# the unskinned six, laid out along the shape the bind pose gives
SPINE_FILL = [("Pelvis", "pelvis"), ("Spine1", "spine_01"), ("Spine2", "spine_02"),
              ("Spine3", "spine_03"), ("Spine4", "spine_04"), ("Ribcage", "spine_05")]
NECK_FILL = [("Ribcage", "spine_05"), ("Neck1", "neck_01"), ("Neck2", "neck_02"),
             ("Head", "head")]

PARENTS = {
    "pelvis": "root",
    "spine_01": "pelvis", "spine_02": "spine_01", "spine_03": "spine_02",
    "spine_04": "spine_03", "spine_05": "spine_04",
    "neck_01": "spine_05", "neck_02": "neck_01", "head": "neck_02",
    "clavicle_l": "spine_05", "upperarm_l": "clavicle_l",
    "lowerarm_l": "upperarm_l", "hand_l": "lowerarm_l",
    "clavicle_r": "spine_05", "upperarm_r": "clavicle_r",
    "lowerarm_r": "upperarm_r", "hand_r": "lowerarm_r",
    "thigh_l": "pelvis", "calf_l": "thigh_l", "foot_l": "calf_l", "ball_l": "foot_l",
    "thigh_r": "pelvis", "calf_r": "thigh_r", "foot_r": "calf_r", "ball_r": "foot_r",
}
# the twists: (name, the segment's first bone, its second, the fraction along it).
# Manny's own spacing, measured from the shipped template 2026-11-01.
TWISTS = []
for _side in ("l", "r"):
    for _seg, _a, _b, _f in (("upperarm", "upperarm", "lowerarm", (1 / 3., 2 / 3.)),
                             ("lowerarm", "lowerarm", "hand", (2 / 3., 1 / 3.)),
                             ("thigh", "thigh", "calf", (1 / 3., 2 / 3.)),
                             ("calf", "calf", "foot", (2 / 3., 1 / 3.))):
        for _i, _frac in enumerate(_f):
            TWISTS.append(("%s_twist_%02d_%s" % (_seg, _i + 1, _side),
                           "%s_%s" % (_a, _side), "%s_%s" % (_b, _side), _frac))

ROOT_ORIENT = (-90.0, 0.0, 0.0)          # Manny's, Z-up into Y-up
SOCKET_TURN = (90.0, 0.0, 0.0)           # catalog.SOCKET_TURN: a model's +Y blade into a bone's +Z grip line
TOL = 1e-4


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def wmat(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def wpos(node):
    m = wmat(node)
    return om.MVector(m[12], m[13], m[14])


def rigid(m):
    """`m` with its scale and shear taken off: the rotation and the translation."""
    tm = om.MTransformationMatrix(m)
    out = om.MTransformationMatrix()
    out.setRotation(tm.rotation(asQuaternion=True))
    out.setTranslation(tm.translation(om.MSpace.kWorld), om.MSpace.kWorld)
    return out.asMatrix()


def euler_matrix(degs):
    return om.MEulerRotation(*[math.radians(v) for v in degs]).asMatrix()


def mesh_points(path, space=om.MSpace.kWorld):
    """A mesh's points as FRESH MPoints.

    `list(fn.getPoints(...))` hands back MPoints that share the MPointArray's
    own memory, and they read as garbage (5.9e+228 here) once that array is
    collected. Copy each one.
    """
    sel = om.MSelectionList().add(path)
    got = om.MFnMesh(sel.getDagPath(0)).getPoints(space)
    return [om.MPoint(p.x, p.y, p.z) for p in got]


# --------------------------------------------------------------- reading him

def read_source():
    """Everything this script needs from his scene, measured before anything moves."""
    cmds.file(SRC, open=True, force=True, executeScriptNodes=False, prompt=False)

    influences = cmds.skinCluster(SKIN, q=True, influence=True) or []
    bind = {}
    for index, inf in enumerate(influences):
        bpm = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (SKIN, index)))
        bind[leaf(inf)] = bpm.inverse()
    missing = [n for n in PAIRS if PREFIX + n not in bind]
    if missing:
        raise RuntimeError("his skin does not use: %s" % ", ".join(missing))

    props = {}
    for name in (SWORD, SHIELD):
        hits = cmds.ls("*" + name, long=True, type="transform") or []
        if len(hits) != 1:
            raise RuntimeError("%s: expected one, found %d" % (name, len(hits)))
        shape = cmds.listRelatives(hits[0], shapes=True, fullPath=True, noIntermediate=True)[0]
        props[name] = {
            "world": wmat(hits[0]),                        # carries the 2.54 (trap 86)
            "points": mesh_points(shape),                  # world, so at his real size
            "verts": cmds.polyEvaluate(shape, vertex=True),
        }

    body_shape = cmds.listRelatives(BODY, shapes=True, fullPath=True, noIntermediate=True)[0]
    orig = [s for s in (cmds.listRelatives(BODY, shapes=True, fullPath=True) or [])
            if cmds.getAttr(s + ".intermediateObject")]
    if not orig:
        raise RuntimeError("the body has no Orig shape: nothing to compare the bind against")
    body = {
        "shape": body_shape,
        "rest": mesh_points(orig[0], om.MSpace.kObject),
        "xform": wmat(BODY),
        "geom": om.MMatrix(cmds.getAttr(SKIN + ".geomMatrix")),
        "verts": cmds.polyEvaluate(body_shape, vertex=True),
        "weights": _foot_weights(influences),
    }

    # the unskinned six: read their SHAPE from the bind pose, which is all they
    # are used for -- they carry no weight, so where exactly they sit is ours
    # to choose, and his own curve is the honest choice.
    cmds.dagPose("bindPose1", restore=True)
    restored = {}
    for name in ("Pelvis", "Spine1", "Spine2", "Spine3", "Spine4", "Ribcage",
                 "Neck1", "Neck2", "Head"):
        hits = cmds.ls("*" + PREFIX + name, long=True, type="joint")
        restored[name] = wmat(hits[0])
    return bind, props, body, restored


def _foot_weights(influences):
    """{side: [vertex ids mostly on that foot]} -- where the ball joints go."""
    out = {}
    for side, his in (("l", "LFoot"), ("r", "RFoot")):
        index = next(i for i, n in enumerate(influences) if leaf(n) == PREFIX + his)
        ids = []
        for vid in range(cmds.polyEvaluate(BODY, vertex=True)):
            w = cmds.skinPercent(SKIN, "%s.vtx[%d]" % (BODY, vid), q=True, value=True)
            if w[index] > 0.5:
                ids.append(vid)
        out[side] = ids
    return out


# ------------------------------------------------------------ the 55 bones

def _fit_chain(restored, steps, ends):
    """His unskinned chain landed on the skinned bind at both ends.

    `steps` is [(his name, our name)] bottom up; `ends` the bind matrices of the
    first and last.  A rigid rotation about the first joint takes the restored
    last onto the bind last -- his segment lengths and his curve survive it
    exactly, because a rotation preserves both.  Returns {our name: world matrix}
    for the joints BETWEEN the ends, and the residual the rotation could not
    close (0.003 cm for the spine, 0.010 for the neck: his chain's own length
    against the skin's, measured 2026-11-01).
    """
    first, last = steps[0][0], steps[-1][0]
    origin = om.MVector(restored[first][12], restored[first][13], restored[first][14])
    have = om.MVector(restored[last][12], restored[last][13], restored[last][14]) - origin
    want_origin = om.MVector(ends[0][12], ends[0][13], ends[0][14])
    want = om.MVector(ends[1][12], ends[1][13], ends[1][14]) - want_origin
    turn = om.MQuaternion(have.normal(), want.normal())
    move = om.MTransformationMatrix()
    move.setRotation(turn)
    turn_matrix = move.asMatrix()

    out = {}
    for his, ours in steps[1:-1]:
        m = restored[his]
        local = om.MMatrix(m)
        local[12] = m[12] - origin.x
        local[13] = m[13] - origin.y
        local[14] = m[14] - origin.z
        placed = local * turn_matrix
        placed = om.MMatrix(placed)
        placed[12] += want_origin.x
        placed[13] += want_origin.y
        placed[14] += want_origin.z
        out[ours] = placed
    residual = abs(have.length() - want.length())
    return out, residual


def _make(name, parent, matrix=None, position=None):
    """One joint at a world matrix (or a world position, orientation inherited).

    The rotation goes into `jointOrient` and `rotate` stays zero -- the shape
    every skeleton in this repo has, and what lets a retarget's rest offsets
    mean what they say.  Scale is 1 throughout, so his pelvis's 2.54 never
    arrives.
    """
    node = cmds.createNode("joint", name=name, parent=parent, skipSelect=True)
    node = cmds.ls(node, long=True)[0]
    cmds.setAttr(node + ".segmentScaleCompensate", 0)
    cmds.setAttr(node + ".rotate", 0, 0, 0)
    cmds.setAttr(node + ".rotateAxis", 0, 0, 0)
    cmds.setAttr(node + ".jointOrient", 0, 0, 0)
    if matrix is not None:
        local = matrix * wmat(parent).inverse() if parent else om.MMatrix(matrix)
        tm = om.MTransformationMatrix(local)
        t = tm.translation(om.MSpace.kTransform)
        r = tm.rotation(asQuaternion=False)
        cmds.setAttr(node + ".translate", t.x, t.y, t.z)
        cmds.setAttr(node + ".jointOrient", math.degrees(r.x), math.degrees(r.y),
                     math.degrees(r.z))
    elif position is not None:
        cmds.xform(node, worldSpace=True, translation=list(position))
    return node


def build_skeleton(bind, props, body, restored):
    """Our 55, parents first. Returns {our name: long path}."""
    made = {}
    root = cmds.createNode("joint", name="root", skipSelect=True)
    root = cmds.ls(root, long=True)[0]
    cmds.setAttr(root + ".segmentScaleCompensate", 0)
    cmds.setAttr(root + ".jointOrient", *ROOT_ORIENT)
    made["root"] = root

    world = {}
    for his, ours in PAIRS.items():
        world[ours] = bind[PREFIX + his]
    spine, spine_residual = _fit_chain(restored, SPINE_FILL,
                                       (bind[PREFIX + "Pelvis"], bind[PREFIX + "Ribcage"]))
    neck, neck_residual = _fit_chain(restored, NECK_FILL,
                                     (bind[PREFIX + "Ribcage"], bind[PREFIX + "Head"]))
    world.update(spine)
    world.update(neck)

    # the body's bones, parents first
    order = ["pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05",
             "neck_01", "neck_02", "head",
             "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l",
             "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r",
             "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r"]
    for name in order:
        made[name] = _make(name, made[PARENTS[name]], matrix=world[name])

    # the balls: the forward-most point of each foot's own vertices, on the floor
    floor = min(p.y for p in mesh_points(body["shape"]))
    for side in ("l", "r"):
        pts = [mesh_points(body["shape"])[v] for v in body["weights"][side]]
        toe = max(pts, key=lambda p: p.z)
        made["ball_" + side] = _make("ball_" + side, made["foot_" + side],
                                     position=(toe.x, floor, toe.z))

    # the twists, oriented as the bone they ride
    for name, first, second, frac in TWISTS:
        a, b = wpos(made[first]), wpos(made[second])
        m = om.MMatrix(wmat(made[first]))
        p = a + (b - a) * frac
        m[12], m[13], m[14] = p.x, p.y, p.z
        made[name] = _make(name, made[first], matrix=m)

    # the weapon bones.  weapon_r is defined BY the sword: its +Z runs down the
    # blade -- the UE grip-line convention -- and its origin is the sword's own
    # origin, inside the grip.  So the sword at zero grip is exactly his hold.
    socket = euler_matrix(SOCKET_TURN)
    made["weapon_r"] = _make("weapon_r", made["hand_r"],
                             matrix=rigid(socket.inverse() * props[SWORD]["world"]))
    mirror = om.MMatrix([-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
    made["weapon_l"] = _make("weapon_l", made["hand_l"],
                             matrix=mirror * wmat(made["weapon_r"]) * mirror)

    # the ik helpers, the camera and the two markers: Manny's own rules
    made["ik_foot_root"] = _make("ik_foot_root", root, position=(0, 0, 0))
    for side in ("l", "r"):
        made["ik_foot_" + side] = _make("ik_foot_" + side, made["ik_foot_root"],
                                        position=wpos(made["foot_" + side]))
    made["ik_hand_root"] = _make("ik_hand_root", root, position=(0, 0, 0))
    made["ik_hand_gun"] = _make("ik_hand_gun", made["ik_hand_root"],
                                position=wpos(made["hand_r"]))
    for side, bone in (("l", "hand_l"), ("r", "hand_r")):
        made["ik_hand_" + side] = _make("ik_hand_" + side, made["ik_hand_gun"],
                                        position=wpos(made[bone]))
    head_y = wpos(made["head"]).y
    made["camera_root"] = _make("camera_root", root, position=(0, head_y, 0))
    made["camera_bone"] = _make("camera_bone", made["camera_root"], position=(0, head_y, 0))
    made["center_of_mass"] = _make("center_of_mass", root, position=(0, 0, 0))
    made["interaction"] = _make("interaction", root, position=(0, 0, 0))
    return made, spine_residual, neck_residual


# ------------------------------------------------------------------ the rest

def rewire(made, bind):
    """His skin onto our joints, each bindPreMatrix re-expressed for ours.

    `armor._wear` can rewire clothing and leave the bindPreMatrix alone because
    the wearer's joints stand EXACTLY where the piece's did. Ours do not quite:
    his bind matrices carry the pelvis's 2.54, and our skeleton is scale 1, so
    our frames are his rigidly -- same place, same orientation, no scale. The
    house's own correction then applies (`as_creep_rig_procedure.weapon_bones`):

        BPM' = BPM * WM_old * WM_new^-1

    and since BPM is WM_old^-1 here, that is simply WM_new^-1. The skin is a
    change of basis by a uniform scale, so it cancels: at the bind the mesh
    lands on `rest * geomMatrix` either way, and under animation the offsets
    are expressed in our frames and reconstructed in them.
    """
    influences = cmds.skinCluster(SKIN, q=True, influence=True) or []
    for index, inf in enumerate(influences):
        ours = PAIRS[leaf(inf)[len(PREFIX):]]
        plug = "%s.bindPreMatrix[%d]" % (SKIN, index)
        bpm = om.MMatrix(cmds.getAttr(plug))
        old = bind[leaf(inf)]
        cmds.connectAttr(made[ours] + ".worldMatrix[0]",
                         "%s.matrix[%d]" % (SKIN, index), force=True)
        cmds.setAttr(plug, list(bpm * old * wmat(made[ours]).inverse()), type="matrix")
    return len(influences)


def carry_props(made, props):
    """The sword and the shield out of his scaled chain, at their WORLD size.

    Their 2.54 is not a transform any more: it lives in the points, frozen, so
    nothing downstream can lose it the way the Creep's sword lost its (trap 86).
    """
    out = {}
    for name, bone in ((SWORD, "weapon_r"), (SHIELD, "weapon_l")):
        node = cmds.ls("*" + name, long=True, type="transform")[0]
        node = cmds.ls(cmds.parent(node, world=True)[0], long=True)[0]
        cmds.setAttr(node + ".scale", 1, 1, 1)
        cmds.setAttr(node + ".shear", 0, 0, 0)
        cmds.setAttr(node + ".rotate", 0, 0, 0)
        cmds.setAttr(node + ".rotateAxis", 0, 0, 0)
        cmds.setAttr(node + ".translate", 0, 0, 0)
        shape = cmds.listRelatives(node, shapes=True, fullPath=True, noIntermediate=True)[0]
        fn = om.MFnMesh(om.MSelectionList().add(shape).getDagPath(0))
        fn.setPoints(om.MPointArray(props[name]["points"]), om.MSpace.kObject)
        out[name] = node
    return out


def tidy(made, carried):
    """Everything of Max's gone, ours grouped under |Swordman|."""
    for junk in cmds.ls("*" + PREFIX + "*", long=True) or []:
        if cmds.objExists(junk):
            top = cmds.ls(junk.split("|")[1], long=True)
            cmds.delete(top[0] if top else junk)
    group = cmds.ls(cmds.group(empty=True, name=GROUP), long=True)[0]
    geometry = cmds.ls(cmds.group(empty=True, name="Geometry", parent=group), long=True)[0]
    cmds.parent(made["root"], group)
    body = cmds.ls("*" + BODY.strip("|"), long=True)[0]
    cmds.parent(body, geometry)
    for name, node in carried.items():
        cmds.parent(node, geometry)
    for old, new in MESH_NAMES.items():
        hits = cmds.ls("*" + old.strip("|"), long=True, type="transform")
        if hits:
            cmds.rename(hits[0], new)
    for pose in cmds.ls(type="dagPose") or []:
        cmds.delete(pose)
    joints = cmds.ls(cmds.ls(GROUP, dag=True, long=True), type="joint", long=True) or []
    cmds.dagPose(joints, save=True, bindPose=True, name="bindPose1")
    for node in cmds.ls(type="script") or []:
        cmds.delete(node)
    return group


# -------------------------------------------------------------------- gates

def check(bind, props, body, spine_residual, neck_residual):
    """Every promise this script makes, measured. Raises on the first break."""
    bad = []
    root = cmds.ls("*|root", long=True, type="joint")[0]
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                          fullPath=True) or [])
    if len(joints) != 55:
        bad.append("55 joints expected, got %d" % len(joints))
    for j in joints:
        s = cmds.getAttr(j + ".scale")[0]
        if max(abs(v - 1.0) for v in s) > 1e-9:
            bad.append("%s is scaled %s" % (leaf(j), s))
        r = cmds.getAttr(j + ".rotate")[0]
        if max(abs(v) for v in r) > 1e-9:
            bad.append("%s has a rotate of %s; the orientation belongs in jointOrient" % (leaf(j), r))
    by_leaf = dict((leaf(j), j) for j in joints)

    # His bind matrices carry the pelvis's 2.54; our skeleton is scale 1, so
    # what must match is his bind made RIGID -- the same place, the same
    # orientation, no scale.
    worst_bind = 0.0
    for his, ours in PAIRS.items():
        want, got = rigid(bind[PREFIX + his]), wmat(by_leaf[ours])
        off = max(abs(got[i] - want[i]) for i in range(16))
        worst_bind = max(worst_bind, off)
        if off > TOL:
            bad.append("%s is %.6f off his bind" % (ours, off))

    # the body stands at its bind: the skin's own formula collapses to the rest
    # points through the geometry's bind matrix, because bindPreMatrix * W is I.
    body_shape = cmds.listRelatives(cmds.ls("*Swordman_Body", long=True)[0],
                                    shapes=True, fullPath=True, noIntermediate=True)[0]
    want = [om.MPoint(p) * body["geom"] for p in body["rest"]]
    got = mesh_points(body_shape)
    worst_body = max((om.MVector(a - b).length() for a, b in zip(got, want)), default=0.0)
    if worst_body > TOL:
        bad.append("the body is %.6f cm off its bind (first vertex: got %s, want %s)"
                   % (worst_body,
                      tuple(round(v, 3) for v in (got[0].x, got[0].y, got[0].z)),
                      tuple(round(v, 3) for v in (want[0].x, want[0].y, want[0].z))))

    # his segment lengths, kept
    worst_len = 0.0
    for his, ours in PAIRS.items():
        parent = PARENTS.get(ours)
        if not parent or parent == "root" or parent not in by_leaf:
            continue
        mine = (wpos(by_leaf[ours]) - wpos(by_leaf[parent])).length()
        hb = bind[PREFIX + his]
        his_parent = next(h for h, o in PAIRS.items() if o == parent) if parent in PAIRS.values() else None
        if his_parent is None:
            continue
        pb = bind[PREFIX + his_parent]
        theirs = (om.MVector(hb[12], hb[13], hb[14]) - om.MVector(pb[12], pb[13], pb[14])).length()
        worst_len = max(worst_len, abs(mine - theirs))

    # the props at their world size
    sizes = {}
    for name, label in ((SWORD, "Swordman_Sword"), (SHIELD, "Swordman_Shield")):
        pts = mesh_points(cmds.ls("*" + label, long=True)[0])
        want_pts = props[name]["points"]
        off = max((om.MVector(om.MPoint(a) - b).length() for a, b in zip(want_pts, pts)), default=0.0)
        if off > TOL:
            bad.append("%s moved %.6f cm out of his hand" % (label, off))
        span = max((om.MVector(om.MPoint(a) - om.MPoint(b)).length()
                    for a in pts for b in pts), default=0.0)
        sizes[label] = span

    if bad:
        raise RuntimeError("source check failed:\n  " + "\n  ".join(bad))
    print("source check: 55 joints, scale 1, rotate 0")
    print("  his bind reproduced to %.2e (worst matrix element)" % worst_bind)
    print("  the body stands at its bind, worst vertex %.2e cm" % worst_body)
    print("  his segment lengths kept to %.2e cm" % worst_len)
    print("  the spine's chain closed to %.4f cm, the neck's to %.4f" % (spine_residual, neck_residual))
    print("  the sword is %.1f cm across, the shield %.1f (x2.54 of their own points)"
          % (sizes["Swordman_Sword"], sizes["Swordman_Shield"]))


def main():
    work = os.path.join(tempfile.gettempdir(), "swordman_source_work")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    os.chdir(work)                       # trap 119: nothing resolves against the repo

    bind, props, body, restored = read_source()
    made, spine_residual, neck_residual = build_skeleton(bind, props, body, restored)
    count = rewire(made, bind)
    carried = carry_props(made, props)
    tidy(made, carried)
    check(bind, props, body, spine_residual, neck_residual)
    print("  %d influences rewired onto our joints" % count)

    tmp = os.path.join(work, "Swordman_Source.mb")
    cmds.file(rename=tmp)
    cmds.file(save=True, type="mayaBinary", force=True)
    shutil.move(tmp, DST)
    print("wrote %s (%.1f KB)" % (DST, os.path.getsize(DST) / 1024.0))


if __name__ == "__main__":
    main()
    maya.standalone.uninitialize()
