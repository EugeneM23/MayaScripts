"""Rebuild the Hunter's AdvancedSkeleton rig on the re-bound skeleton -- LIVE, in a Maya of its own.

    exec'd over a command port in a disposable Maya (AdvancedSkeleton's procedures read their own
    UI, so mayapy cannot build it), with IN / OUT set in the globals:
        IN  = a scene holding the clean Hunter skeleton re-bound by `rebind_hunter_pose.py`
        OUT = where to save the built rig (.mb); `make_hunter_rig_asset.py` turns it into the asset

2026-09-24: the rig's zero pose must BE the new bind (the animator: «исходная поза у рига ... не
должна никак отличаться от позы скелета SKM_Manny_Simple»).  `as_hanter_rig_procedure` puts every
fit joint on its bone, so a rig built over a skeleton standing in the pose has that pose as its
build pose -- nothing is re-aimed afterwards.  The procedure's own steps, minus the ones the clean
skeleton no longer needs (tidy, the sword export, drop_props, weapon_bones -- weapon_r / weapon_l
are already there): fit (the left side NON-symmetric) -> build -> place_parts -> constrain -> orient_controls -> align_shapes ->
finger_sdk_axes -> as_frames(LEVEL_CONTROLS) -> mark, then the meshes into `Group|Geometry`,
where the shipped rig keeps them.  Refuses a scene whose skin is not at its bind.
"""
import os
import maya.cmds as cmds
import maya.api.OpenMaya as om

PLANS = "C:/!!!Work/MayaScripts/docs/superpowers/plans"
MESHES = ("Hunter_Body", "Hunter_Back", "Hunter_Arm_L", "Hunter_Arm_R", "Hunter_Face")

for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
cmds.file(IN, open=True, force=True, executeScriptNodes=False)
P = PLANS + "/as_hanter_rig_procedure.py"
g = {"__name__": "hunter_rig", "__file__": P}
exec(compile(open(P, encoding="utf-8").read(), P, "exec"), g)
g["HEAD_MESH"] = "Hunter_FaceShape"


def bind_error():
    worst = 0.0
    for sc in cmds.ls(type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if src:
                m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * \
                    om.MMatrix(cmds.getAttr(cmds.ls(src[0], long=True)[0] + ".worldMatrix[0]"))
                worst = max(worst, max(abs(a - b) for a, b in zip(list(m), list(om.MMatrix()))))
    return worst


before = bind_error()
if before > 1e-4:
    raise RuntimeError("the skin is not at its bind (%.2e) -- run rebind_hunter_pose.py first" % before)
state = {"autoKey": cmds.autoKeyframe(q=True, st=True), "em": cmds.evaluationManager(q=True, mode=True)[0]}
cmds.autoKeyframe(st=False)
cmds.evaluationManager(mode="off")
try:
    joints = list(g["bones"]().values())
    rest = dict((j, cmds.getAttr(j + ".worldMatrix[0]")) for j in joints)
    placed, worst_fit = g["fit"]()
    print("// fit: %d joints placed, mapped joints on their bones to %.6f cm" % (placed, worst_fit))
    g["build"]()
    print("// twist / in-between joints on the Hunter's: %s" % dict((k, round(v, 4)) for k, v in g["place_parts"]().items()))
    print("// constraints: %d" % g["constrain"]())
    n, worst = g["orient_controls"]()
    shapes = g["align_shapes"]()
    sdk = g["finger_sdk_axes"]()
    print("// IK foot controls level (AS's frame): worst %.5f deg" % g["as_frames"](g["LEVEL_CONTROLS"]))
    g["mark"]()
    drift = max(max(abs(a - c) for a, c in zip(m, cmds.getAttr(j + ".worldMatrix[0]"))) for j, m in rest.items())
    print("// %d controls oriented (worst frame angle %.5f deg), %d curves aligned, %d finger SDK groups re-framed; "
          "bind-pose drift %.9f" % (n, worst, shapes, sdk, drift))
    geo = "|Group|Geometry"
    for name in MESHES:
        tr = cmds.ls(name, type="transform", long=True)
        if tr and not tr[0].startswith(geo + "|"):
            cmds.parent(tr[0], geo)
    for holder in cmds.ls("|Hunter", long=True) or []:
        if not cmds.listRelatives(holder, children=True):
            cmds.delete(holder)
    print("// Geometry:", cmds.listRelatives(geo, children=True))
    print("// skin off its bind after the build: %.2e" % bind_error())
finally:
    cmds.evaluationManager(mode=state["em"])
    cmds.autoKeyframe(st=state["autoKey"])
    cmds.select(clear=True)
if not os.path.isdir(os.path.dirname(OUT)):
    os.makedirs(os.path.dirname(OUT))
cmds.file(rename=OUT)
cmds.file(save=True, type="mayaBinary", force=True)
print("// saved", OUT)
