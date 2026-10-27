"""AdvancedSkeleton rig over a PART of the Creep (SK_Creep from Unreal) -- the right arm or the head.

2026-10-27.  The Creep was split on port 7004 into a body, the right arm with its shoulder and the
head cut at mid neck, each skinned to its own skeleton starting at the character's `root`
(`C:/!!!Work/Animations/Rigs/Characters/Creep_Split/`).  This builds an AdvancedSkeleton rig over
one part, LIVE (AdvancedSkeleton reads its own UI), with the shipped Creep procedure's steps
(`as_creep_rig_procedure.py`, exec'd into a dict and given this part's lookups) and two
differences:

- the fit is UE5.ma cut down to the part: Root (standing where `spine_05` stands in the whole
  body) with the right arm chain (Scapula > Shoulder > ... fingers, `noMirror`, so no left arm)
  or the neck (Neck with its in-between > Head) right under it;
- **every game bone follows its AS joint by point + orient + scale, maintainOffset** -- Manny's
  rig (the animator, 2026-10-27: «ФК контролы работают как у менни при смени позиции растягиваются
  кости»), not the shipped Creep's orientation-only; the rig is not marked rotation-only.

The rig carries `Group.skeldarPartAnchor` (the UE bone its RootX_M follows in a retarget) and a
transform `PartAnchor` under Group on that bone's place, following Root_M.  See the spec
`docs/superpowers/specs/2026-10-27-creep-arm-head-parts-design.md`.
"""
import math
import os
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

PLANS = "C:/!!!Work/MayaScripts/docs/superpowers/plans"
SPLIT = "C:/!!!Work/Animations/Rigs/Characters/Creep_Split"
ANCHOR_BONE = "spine_05"
ANCHOR_ATTR = "skeldarPartAnchor"
ANCHOR_NODE = "PartAnchor"
PARTS = {
    "arm": {"fbx": "Creep_Arm_R.fbx", "group": "SK_Creep_arm_r", "mesh": "Creep_ArmR",
            "keep": "Scapula", "head_mesh": None},
    "head": {"fbx": "Creep_Head.fbx", "group": "SK_Creep_head", "mesh": "Creep_Head",
             "keep": "Neck", "head_mesh": "Creep_HeadShape"},
}
_P = PLANS + "/as_creep_rig_procedure.py"
g = {"__name__": "creep_part", "__file__": _P}
exec(compile(open(_P, encoding="utf-8").read(), _P, "exec"), g)
_pos, _snap, _wmat = g["_pos"], g["_snap"], g["_wmat"]


def _fbx(path, namespace=None):
    if not cmds.pluginInfo("fbxmaya", q=True, loaded=True):
        cmds.loadPlugin("fbxmaya")
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    if namespace:
        cmds.namespace(add=namespace)
        cmds.namespace(set=namespace)
    try:
        mel.eval('FBXImport -f "%s"' % path)
    finally:
        cmds.namespace(set=":")


def anchor_world():
    """Where `spine_05` stands in the whole Creep's bind: read from Creep_Body.fbx, then gone."""
    _fbx(SPLIT + "/Creep_Body.fbx", "creepBodyTmp")
    try:
        j = [x for x in cmds.ls("creepBodyTmp:*", type="joint", long=True) if x.endswith(":" + ANCHOR_BONE)][0]
        return cmds.xform(j, q=True, ws=True, m=True)
    finally:
        cmds.namespace(removeNamespace="creepBodyTmp", deleteNamespaceContent=True)


def out_of_group(mesh):
    """The skinned mesh out of the FBX's -90 X group to world level, its world matrix kept.  The FBX
    importer LOCKS a skinned mesh's t/r/s and a locked plug makes the parent's compensation a silent
    no-op (CLAUDE.md trap 51): the first build's meshes lay on their side.  Unlocked around the move,
    locked back.  Returns the new leaf name."""
    # the compounds too: the importer locks `rotate` itself, and unlocking rx/ry/rz alone leaves it
    # locked (measured 2026-10-27: setAttr rotate refused, xform a silent no-op)
    plugs = [mesh + "." + a + x for a in "trs" for x in ("", "x", "y", "z")]
    locked = [p for p in plugs if cmds.getAttr(p, lock=True)]
    for p in locked:
        cmds.setAttr(p, lock=False)
    w = cmds.xform(mesh, q=True, ws=True, m=True)
    m = cmds.parent(mesh, world=True)[0]
    cmds.xform("|" + m, ws=True, m=w)
    for p in locked:
        cmds.setAttr("|" + m + "." + p.split(".")[-1], lock=True)
    return "|" + m


# weapon_r in hand_r's space as the second Creep ships it (Creep2_Rig.ma, read 2026-10-27): its socket
# turned into UE's convention, the plugin's one socket standard (the fist's grip line along +Z) - the
# FBX the part was cut from has the creature's own socket, a quarter turn about its X off.
WEAPON_SOCKET = [0.9023638608, -0.3496252732, 0.2519985282, 0.0, 0.3490667668, 0.9358437785, 0.0484502887, 0.0,
                 -0.2527707062, 0.044244523, 0.9665141917, 0.0, -9.8019504547, -4.6126813889, 1.0132220984, 1.0]


def weapon_socket():
    """weapon_r onto WEAPON_SOCKET in hand_r, the skins kept at their bind (BPM' = BPM * W_old * W_new^-1)
    and the bind pose saved again for it.  Nothing else moves.  Returns the angle turned (deg)."""
    b = bones()
    if "weapon_r" not in b:
        return 0.0
    w = b["weapon_r"]
    old = om.MMatrix(cmds.getAttr(w + ".worldMatrix[0]"))
    new = om.MMatrix(WEAPON_SOCKET) * om.MMatrix(cmds.getAttr(b["hand_r"] + ".worldMatrix[0]"))
    cmds.xform(w, ws=True, m=list(new))
    new = om.MMatrix(cmds.getAttr(w + ".worldMatrix[0]"))
    for sc in cmds.ls(type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.ls(cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False) or [], long=True)
            if src and src[0] == w:
                bpm = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx)))
                cmds.setAttr("%s.bindPreMatrix[%d]" % (sc, idx), list(bpm * old * new.inverse()), type="matrix")
    for pose in cmds.ls(type="dagPose"):
        if w in (cmds.ls(cmds.dagPose(pose, q=True, members=True) or [], long=True)) and cmds.getAttr(pose + ".bindPose"):
            cmds.dagPose(w, reset=True, name=pose)
    q = om.MTransformationMatrix(old).rotation(asQuaternion=True).inverse() *         om.MTransformationMatrix(new).rotation(asQuaternion=True)
    return math.degrees(2 * math.acos(min(1.0, abs(q.w))))


def prepare(part):
    """A new scene with the part: `Armature` (the FBX's -90 X group) > root, the mesh at world level."""
    spec = PARTS[part]
    cmds.file(new=True, force=True)
    for p in ("matrixNodes", "quatNodes"):
        try:
            cmds.loadPlugin(p, quiet=True)
        except Exception:
            pass
    anchor = anchor_world()
    _fbx(SPLIT + "/" + spec["fbx"])
    grp = cmds.rename("|" + spec["group"], "Armature")
    meshes = [t for t in cmds.listRelatives("|Armature", children=True, fullPath=True) if cmds.nodeType(t) == "transform"]
    assert len(meshes) == 1, meshes
    m = out_of_group(meshes[0])
    m = cmds.rename(m, spec["mesh"])
    shp = [s for s in cmds.listRelatives("|" + m, shapes=True, fullPath=True) if not cmds.getAttr(s + ".io")][0]
    cmds.rename(shp, spec["mesh"] + "Shape")
    print("// weapon_r onto the UE socket: turned %.3f deg" % weapon_socket())
    g["ROOT"] = "|Armature|root"
    g["HEAD_MESH"] = spec["head_mesh"]
    return anchor


def bones():
    root = "|Armature|root"
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    return dict((p.split("|")[-1], p) for p in paths)


g["bones"] = bones


def fit(part, anchor):
    """UE5.ma cut to the part, every fit joint on its bone, Root on the anchor."""
    spec = PARTS[part]
    for n in ("FitSkeleton", "Group", "Main", "MotionSystem", "DeformationSystem", "Geometry"):
        if cmds.objExists(n):
            raise RuntimeError("%s already exists" % n)
    b = bones()
    g["ensure_as_ui"]()
    cmds.optionMenu("asFitFiles", e=True, v="UE5.ma")
    guard = cmds.createNode("transform", n="FitSkeletonNameMatcherImporting")
    try:
        mel.eval("asFitSkeletonImport;")
    finally:
        if cmds.objExists(guard):
            cmds.delete(guard)
    fj = g["fit_joints"]()
    root, keep = fj["Root"], fj[spec["keep"]]
    # the kept chain under Root, at its place; then everything else goes
    w = _pos(keep)
    kept = cmds.parent(keep, root)[0]
    kept = [x for x in cmds.listRelatives(root, children=True, fullPath=True) if x.split("|")[-1] == spec["keep"]]
    if not kept:   # Maya put a transform between: take the joint out of it
        raise RuntimeError("parenting %s under Root inserted a node" % spec["keep"])
    for c in cmds.listRelatives(root, children=True, fullPath=True) or []:
        if c.split("|")[-1] != spec["keep"]:
            cmds.delete(c)
    fj = g["fit_joints"]()
    for n in ("Eye", "Jaw"):
        if n in fj and cmds.objExists(fj[n]):
            cmds.delete(fj[n])
    fj = g["fit_joints"]()
    if part == "arm":
        sc = fj["Scapula"]
        for a, dv in (("noMirror", 1), ("noMirrorLeft", 0)):
            if not cmds.attributeQuery(a, node=sc, exists=True):
                cmds.addAttr(sc, k=True, ln=a, at="bool", dv=dv)
            cmds.setAttr(sc + "." + a, dv)
    else:
        cmds.setAttr(fj["Neck"] + ".inbetweenJoints", 1)
    rows = dict(g["ROWS"])
    tip = {}
    if part == "arm":
        for f in g["FINGERS"]:
            j2, j3, j4 = (_pos(fj["%sFinger%d" % (f, i)]) for i in (2, 3, 4))
            tip[f] = (j4 - j3).length() / max((j3 - j2).length(), 1e-6)
    A = om.MMatrix(anchor)
    # AdvancedSkeleton wants its middle joints ON x = 0 (within 1 % of its scale): this Creep stands
    # 0.32 cm off it, so the middle fit joints go to x = 0 and the -mo constraints carry the step
    _snap(root, om.MVector(0.0, A.getElement(3, 1), A.getElement(3, 2)))
    placed = 1
    for path in sorted(fj.values(), key=lambda p: p.count("|")):
        leaf = path.split("|")[-1]
        ue = rows.get(leaf)
        if leaf == "Root" or ue is None:
            continue
        bone = b.get(ue) or b.get(ue + "_r")
        if bone:
            _snap(path, _pos(bone)); placed += 1
    fj = g["fit_joints"]()
    if part == "arm":
        for f in g["FINGERS"]:
            j2, j3 = _pos(fj["%sFinger2" % f]), _pos(fj["%sFinger3" % f])
            _snap(fj["%sFinger4" % f], j3 + (j3 - j2) * tip[f]); placed += 1
    else:
        head = _pos(b["head"])
        sel = om.MSelectionList(); sel.add(spec["head_mesh"])
        top = max(p.y for p in om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld))
        _snap(fj["HeadEnd"], om.MVector(head.x, top, head.z)); placed += 1
    if part == "head":
        for leaf in ("Neck", "Head", "HeadEnd"):
            p_ = _pos(fj[leaf]); _snap(fj[leaf], om.MVector(0.0, p_.y, p_.z))
    mel.eval("asFitModeManualUpdate;")
    fj = g["fit_joints"]()
    worst = 0.0
    for leaf, path in fj.items():
        ue = rows.get(leaf)
        bone = (b.get(ue) or b.get((ue or "") + "_r")) if ue and leaf != "Root" else None
        if bone:
            worst = max(worst, (_pos(path) - _pos(bone)).length())
    return placed, worst, sorted(fj)


def constrain():
    """Manny's way: every game bone follows its AS joint by point + orient + scale, maintainOffset;
    root follows Main."""
    b = bones()
    made = 0
    for d, bone in sorted(g["mapping"]().items()):
        if cmds.listRelatives(bone, children=True, type="constraint"):
            continue
        cmds.pointConstraint(d, bone, maintainOffset=True)
        cmds.orientConstraint(d, bone, maintainOffset=True)
        cmds.scaleConstraint(d, bone, maintainOffset=True)
        made += 3
    cmds.parentConstraint("Main", b["root"], maintainOffset=True)
    return made + 1


def anchor_node(anchor):
    """`PartAnchor` under Group on the anchor bone's place, following Root_M; the mark on Group."""
    n = cmds.createNode("transform", name=ANCHOR_NODE, parent="Group", skipSelect=True)
    cmds.xform(n, ws=True, m=anchor)
    cmds.parentConstraint("Root_M", n, maintainOffset=True)
    for a in ("t", "r", "s", "v"):
        cmds.setAttr(n + "." + a, lock=True)
    if not cmds.attributeQuery(ANCHOR_ATTR, node="Group", exists=True):
        cmds.addAttr("Group", longName=ANCHOR_ATTR, dataType="string")
    cmds.setAttr("Group." + ANCHOR_ATTR, ANCHOR_BONE, type="string")
    return n


def control_sizes(radii):
    """The right side only: a part has no left."""
    out = {}
    for name, wanted in sorted(radii.items()):
        ctrl = name + "_R"
        if not cmds.objExists(ctrl):
            continue
        shapes = cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve", fullPath=True) or []
        cvs = dict((s, cmds.getAttr(s + ".cv[*]")) for s in shapes)
        factor = wanted / max(math.sqrt(x * x + y * y + z * z) for pts in cvs.values() for x, y, z in pts)
        for s, pts in cvs.items():
            for i, (x, y, z) in enumerate(pts):
                cmds.xform("%s.cv[%d]" % (s, i), objectSpace=True, translation=(x * factor, y * factor, z * factor))
        out[ctrl] = round(factor, 4)
    return out


def build(part, anchor):
    spec = PARTS[part]
    state = {"autoKey": cmds.autoKeyframe(q=True, st=True), "em": cmds.evaluationManager(q=True, mode=True)[0]}
    cmds.autoKeyframe(st=False)
    cmds.evaluationManager(mode="off")
    try:
        rest = dict((j, cmds.getAttr(j + ".worldMatrix[0]")) for j in bones().values())
        g["build"]()
        left = cmds.ls("*_L", type="joint")
        print("// built; left joints:", left)
        print("// twist / in-between on the bones:", dict((k, round(v, 4)) for k, v in g["place_parts"]().items()))
        print("// constraints:", constrain())
        n, worst = g["orient_controls"]()
        print("// %d controls on their bones' frames, worst %.5f deg; curves aligned %d" % (n, worst, g["align_shapes"]()))
        if part == "arm":
            print("// finger SDK groups re-framed:", g["finger_sdk_axes"]())
            print("// drawings:", control_sizes(g["CONTROL_RADII"]))
        print("// Main at Manny's size x%.4f" % g["main_size"]())
        anchor_node(anchor)
        cmds.parent("|" + spec["mesh"], "Geometry")
        lay = cmds.createDisplayLayer(name=spec["mesh"] + "_Skeleton", empty=True)
        cmds.editDisplayLayerMembers(lay, list(bones().values()), noRecurse=True)
        drift = max(max(abs(a - c) for a, c in zip(m, cmds.getAttr(j + ".worldMatrix[0]"))) for j, m in rest.items())
        print("// skeleton drift through the build %.9f" % drift)
    finally:
        cmds.evaluationManager(mode=state["em"])
        cmds.autoKeyframe(st=state["autoKey"])
