"""The Creep's skeletal-mesh FBX held against the file Cascadeur itself wrote for this creature (2026-09-25).

    mayapy verify_creep_skeleton_fbx_cascadeur.py [<our fbx>] [<Cascadeur's fbx of the creature>]

The animator: «сделай мне экспорт персонажа creep с группой по новому пайплайну так чтобы в каскадере
всё было хорошо и его не переворачивало».  Cascadeur is not installed on this machine, so the export
(`export_creep_skeleton_fbx.py`, Cascadeur's layout through maya_uebridge.fbxlayout) is held against
`creep_T-pose_draft (1).fbx` -- written by Cascadeur 2024.1 for this very creature, the
SKM_Manny_Simple the Creep was re-bound onto, whose frame 0 IS the Creep's bind pose.  What Cascadeur
does with a file it does to both alike; where the two files agree, it reads ours as its own.

1. the header, read from each file: up +Y, front +Z, coord +X, unit scale 1;
2. the top of the tree, read from each file: a Null at Lcl Rotation (-90, 0, 0) holding `root`,
   root at Cascadeur's own local values with no PreRotation, the five meshes at the top of the scene
   beside the Null with Cascadeur's transforms -- the group is the character's (`Creep`), the rest is
   Cascadeur's layout to the number;
3. both imported the same way (FBXImport add, each into its namespace), every bone Cascadeur's file
   has: its world place and orientation, ours at the bind against Cascadeur's at frame 0 (weapon_r is
   Cascadeur's weapon_test turned half a turn about its own Z, as the rig was built; Cascadeur's arm
   scales 1.32 from lowerarm_r and is compared on its rigid frame);
4. every vertex of the five meshes, ours at the bind against Cascadeur's skinned at frame 0;
5. a control: the same comparison against Cascadeur's file with its Null turned the other way
   (+90) -- the flip the animator means -- must fail by a body height.
Read-only for both files.
"""
import collections
import math
import os
import struct
import sys
import zlib

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

try:
    cmds.loadPlugin("fbxmaya", quiet=True)
except Exception:
    pass
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OURS = (ARGS[0] if ARGS else "C:/!!!Work/Animations/Rigs/Characters/Creep_Skeleton.fbx").replace("\\", "/")
CASC = (ARGS[1] if len(ARGS) > 1 else "C:/Users/MY PC/Downloads/creep_T-pose_draft (1).fbx").replace("\\", "/")
MESHES = {"Creep_Body": "body", "Creep_Back": "back", "Creep_Arm_L": "arm_l", "Creep_Arm_R": "arm_r", "Creep_Face": "face"}
FLIP_Z = om.MMatrix([-1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])   # weapon_test -> weapon_r
FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


# ---- the file itself, as any FBX reader sees it -------------------------------------------------
Node = collections.namedtuple("Node", "name props children")


def parse(path):
    data = open(path, "rb").read()
    wide = struct.unpack_from("<I", data, 23)[0] >= 7500

    def prop(pos):
        t = chr(data[pos]); pos += 1
        sc = {"Y": "<h", "C": "<?", "I": "<i", "F": "<f", "D": "<d", "L": "<q"}
        if t in sc:
            return struct.unpack_from(sc[t], data, pos)[0], pos + struct.calcsize(sc[t])
        if t in "fdlib":
            n, enc, clen = struct.unpack_from("<III", data, pos); pos += 12
            raw = data[pos:pos + clen]; pos += clen
            if enc:
                raw = zlib.decompress(raw)
            return list(struct.unpack("<%d%s" % (n, {"f": "f", "d": "d", "l": "q", "i": "i", "b": "?"}[t]), raw)), pos
        n = struct.unpack_from("<I", data, pos)[0]; pos += 4
        raw = data[pos:pos + n]
        return (raw.decode("utf-8", "replace") if t == "S" else raw), pos + n

    def node(pos):
        if wide:
            end, np_, _ = struct.unpack_from("<QQQ", data, pos); pos += 24
        else:
            end, np_, _ = struct.unpack_from("<III", data, pos); pos += 12
        nl = data[pos]; pos += 1
        if end == 0:
            return None, pos
        name = data[pos:pos + nl].decode(); pos += nl
        props = []
        for _ in range(np_):
            v, pos = prop(pos)
            props.append(v)
        kids = []
        while pos < end:
            if data[pos:end].strip(b"\0") == b"":
                break
            k, pos = node(pos)
            if k is None:
                break
            kids.append(k)
        return Node(name, props, kids), end

    pos, top = 27, []
    while pos < len(data) - 200:
        n, pos = node(pos)
        if n is None:
            break
        top.append(n)
    return Node("", [], top)


def kid(n, name):
    return next((c for c in n.children if c.name == name), None)


def p70(n):
    block = kid(n, "Properties70")
    return dict((p.props[0], p.props[4:]) for p in (block.children if block else []))


def file_view(path):
    """header axes, and every Model: name -> (type, parent name, Lcl T, Lcl R, Lcl S, PreRotation)"""
    doc = parse(path)
    g = p70(kid(doc, "GlobalSettings"))
    v = lambda k: (g.get(k) or [None])[0]
    axes = ("%s%s" % ("+" if v("UpAxisSign") == 1 else "-", "XYZ"[v("UpAxis")]),
            "%s%s" % ("+" if v("FrontAxisSign") == 1 else "-", "XYZ"[v("FrontAxis")]),
            "%s%s" % ("+" if v("CoordAxisSign") == 1 else "-", "XYZ"[v("CoordAxis")]), v("UnitScaleFactor"))
    models = dict((m.props[0], m) for m in kid(doc, "Objects").children if m.name == "Model")
    parent = {}
    for c in kid(doc, "Connections").children:
        if c.props[0] == "OO" and c.props[1] in models and (c.props[2] in models or c.props[2] == 0):
            parent[c.props[1]] = c.props[2]
    name = lambda u: models[u].props[1].split("\x00")[0] if u else ""
    out = {}
    for u, m in models.items():
        pp = p70(m)
        out[name(u)] = (m.props[2], name(parent.get(u, 0)), tuple(pp.get("Lcl Translation", [0.0] * 3)),
                        tuple(pp.get("Lcl Rotation", [0.0] * 3)), tuple(pp.get("Lcl Scaling", [1.0] * 3)),
                        tuple(pp.get("PreRotation", [0.0] * 3)))
    return axes, out


def close(a, b, tol):
    return max(abs(x - y) for x, y in zip(a, b)) < tol


ax_o, file_o = file_view(OURS)
ax_c, file_c = file_view(CASC)
gate(1, ax_o == ax_c == ("+Y", "+Z", "+X", 1.0),
     "the header: ours up %s front %s coord %s unit %s -- Cascadeur's %s %s %s %s" % (ax_o + ax_c))

null_c = [n for n, v in file_c.items() if v[0] == "Null" and not v[1]]
null_o = [n for n, v in file_o.items() if v[0] == "Null" and not v[1]]
root_o, root_c = file_o.get("root"), file_c.get("root")
meshes_o = dict((n, v) for n, v in file_o.items() if v[0] == "Mesh")
# root's PreRotation: our jointOrient after the wrapper's turn, JO·W⁻¹ -- zero up to the -90's own
# float noise (measured 4e-5 deg)
top_ok = (null_o == ["Creep"] and len(null_c) == 1 and root_o and root_c
          and root_o[1] == "Creep" and root_c[1] == null_c[0]
          # Cascadeur writes its own Null at (-89.99998, -2e-5, 2e-5): float noise
          and close(file_o["Creep"][3], file_c[null_c[0]][3], 1e-3) and close(file_o["Creep"][3], (-90, 0, 0), 1e-6)
          and close(root_o[2], root_c[2], 1e-3) and close(root_o[3], root_c[3], 1e-3) and close(root_o[5], (0, 0, 0), 1e-3))
# the meshes: at the top of the scene, unturned and unscaled, as Cascadeur's.  A mesh's own TRANSLATE
# may differ: Creep_Face keeps the source model's pivot (0, 6.058, 0) -- the animator's Maya file of the
# creature (creep_T-pose_draft2.fbx, Maya 2023) carries it the same way, Cascadeur's own file has it
# baked to 0 -- and where its vertices stand is gate 4's business
mesh_ok = sorted(meshes_o) == sorted(MESHES) and all(
    not meshes_o[m][1] and not file_c[c][1] and close(meshes_o[m][3], file_c[c][3], 1e-4)
    and close(meshes_o[m][4], file_c[c][4], 1e-6) for m, c in MESHES.items())
pivots = ["%s T %s (Cascadeur's %s)" % (m, [round(x, 3) for x in meshes_o[m][2]], [round(x, 3) for x in file_c[c][2]])
          for m, c in MESHES.items() if m in meshes_o and not close(meshes_o[m][2], file_c[c][2], 1e-3)]
gate(2, bool(top_ok and mesh_ok),
     "in the file: our Null %s at R %s holds root (T %s R %s PreR %s) -- Cascadeur's %s at R %s holds root "
     "(T %s R %s); the meshes at the top %s, unturned and unscaled as Cascadeur's: %s; own pivots: %s"
     % (null_o, [round(x, 3) for x in file_o.get("Creep", (0, 0, 0, (0, 0, 0)))[3]],
        [round(x, 4) for x in root_o[2]] if root_o else None, [round(x, 4) for x in root_o[3]] if root_o else None,
        [round(x, 5) for x in root_o[5]] if root_o else None, null_c,
        [round(x, 3) for x in file_c[null_c[0]][3]] if null_c else None,
        [round(x, 4) for x in root_c[2]] if root_c else None, [round(x, 4) for x in root_c[3]] if root_c else None,
        sorted(meshes_o), mesh_ok, pivots or "none"))
jo = sum(1 for n, v in file_o.items() if v[0] in ("LimbNode", "Root") and max(abs(x) for x in v[5]) > 1e-6)
print("   our bones carrying a PreRotation (Maya's jointOrient): %d; Cascadeur's: %d"
      % (jo, sum(1 for n, v in file_c.items() if v[0] in ("LimbNode", "Root") and max(abs(x) for x in v[5]) > 1e-6)))


# ---- both imported the same way ------------------------------------------------------------------
def import_into(path, ns):
    cmds.namespace(add=ns)
    cmds.namespace(set=":" + ns)
    try:
        mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
        mel.eval('FBXImport -f "%s";' % path)
    finally:
        cmds.namespace(set=":")


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def rigid(m):
    t = om.MTransformationMatrix(m)
    out = om.MTransformationMatrix()
    out.setRotation(t.rotation(asQuaternion=True))
    out.setTranslation(t.translation(om.MSpace.kWorld), om.MSpace.kWorld)
    return out.asMatrix()


def pos(m):
    return om.MVector(m.getElement(3, 0), m.getElement(3, 1), m.getElement(3, 2))


def ang(a, b):
    qa = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    q = qa.inverse() * qb
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def joints(ns):
    root = cmds.ls(ns + ":root", type="joint", long=True)[0]
    return dict((p.split("|")[-1].split(":")[-1], p)
                for p in [root] + (cmds.listRelatives(root, ad=True, type="joint", fullPath=True) or []))


def points(ns, leaf):
    tr = cmds.ls(ns + ":" + leaf, type="transform", long=True)[0]
    live = [s for s in cmds.listRelatives(tr, shapes=True, fullPath=True) if not cmds.getAttr(s + ".intermediateObject")][0]
    sel = om.MSelectionList(); sel.add(live)
    return om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)


# The five IK helpers the Creep places by its OWN rules: the animator's layout for this creature
# (as_creep_rig_procedure.place_ik_helpers, rebind_creep_pose.py) keeps ik_hand_gun at zero under
# ik_hand_root, undriven, puts ik_hand_r / ik_hand_l exactly ON the hands and keeps ik_foot_l / _r in
# their relation to the feet -- in the bind pose.  Cascadeur's file never took them into its frame-0
# pose: ik_hand_gun on the right hand, ik_hand_r / _l 54 cm off the hands, ik_foot_l / _r 7.4 cm off
# the feet, where its T-bind had them (their orientations agree to 0.003 deg).  Named, not gated.
OWN_LAYOUT = ("ik_hand_gun", "ik_hand_r", "ik_hand_l", "ik_foot_l", "ik_foot_r")
# weapon_r is Cascadeur's weapon_test turned half a turn about its Z, and stands where it stands; its
# TURN in the hand differs: Cascadeur's file holds weapon_test turned (0.2, 46.1, -6.3) deg at frame 0
# against the Maya scene's, the turn the Creep Sword's frame (0, 45, 0) was dialled to by eye.  Its
# place is gated, its turn reported.
TURN_REPORTED = ("weapon_r",)


def compare_bones(O, C, skip=OWN_LAYOUT):
    worst_p = worst_r = 0.0
    wp = wr = ""
    for n, pc in C.items():
        on = "weapon_r" if n == "weapon_test" else n
        if on not in O or on in skip:
            continue
        mc = rigid(wm(pc))
        if n == "weapon_test":
            mc = FLIP_Z * mc
        mo = rigid(wm(O[on]))
        d, a = (pos(mo) - pos(mc)).length(), (0.0 if on in TURN_REPORTED else ang(mo, mc))
        if d > worst_p:
            worst_p, wp = d, on
        if a > worst_r:
            worst_r, wr = a, on
    return worst_p, wp, worst_r, wr


cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
import_into(OURS, "ours")
import_into(CASC, "casc")
cmds.currentTime(1)
cmds.currentTime(0)
O, C = joints("ours"), joints("casc")
worst_p, wp, worst_r, wr = compare_bones(O, C)
only_ours = sorted(set(O) - set(C) - {"weapon_r"})
missing = sorted(set(C) - set(O) - {"weapon_test"})
helpers = ", ".join("%s %.1f cm off" % (h, (pos(rigid(wm(O[h]))) - pos(rigid(wm(C[h])))).length())
                    for h in OWN_LAYOUT if h in O and h in C)
turn = ang(rigid(wm(O["weapon_r"])), FLIP_Z * rigid(wm(C["weapon_test"])))
gate(3, worst_p < 1e-3 and worst_r < 1e-3 and not missing,
     "every bone of Cascadeur's file (%d, the five IK helpers aside) where Cascadeur has it at frame 0: "
     "%.2e cm (%s), %.5f deg (%s); ours only: %s; Cascadeur's only: %s; the Creep's own helper layout: %s; "
     "weapon_r in place, turned %.2f deg from Cascadeur's weapon_test"
     % (len(C) - len(OWN_LAYOUT), worst_p, wp, worst_r, wr, only_ours, missing, helpers, turn))

worst_v, wv, counted = 0.0, "", 0
for ours_leaf, casc_leaf in MESHES.items():
    a, b = points("ours", ours_leaf), points("casc", casc_leaf)
    if len(a) != len(b):
        worst_v, wv = float("inf"), "%s %d vs %d vertices" % (ours_leaf, len(a), len(b))
        break
    d = max(p.distanceTo(q) for p, q in zip(a, b))
    counted += len(a)
    if d > worst_v:
        worst_v, wv = d, ours_leaf
gate(4, worst_v < 1e-3, "every vertex of the five meshes (%d) where Cascadeur's skin puts it at frame 0: %.2e cm (%s)"
     % (counted, worst_v, wv))

# the control: Cascadeur's Null turned the other way, the flip -- the same comparison must see it
null_node = cmds.ls("casc:" + null_c[0], long=True)[0]
was = cmds.getAttr(null_node + ".rotate")[0]
cmds.setAttr(null_node + ".rotateX", 90.0)
flipped_p, fp, flipped_r, fr = compare_bones(O, C)
cmds.setAttr(null_node + ".rotate", *was)
gate(5, flipped_p > 50.0 and flipped_r > 90.0,
     "control: with Cascadeur's Null at +90 the same gate reads %.1f cm (%s), %.1f deg -- it can fail"
     % (flipped_p, fp, flipped_r))
print("RESULT: %d of 5 gates failed %s" % (len(FAILS), FAILS))
