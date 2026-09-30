"""Build the Orc Marauder's AdvancedSkeleton rig -- LIVE, in a Maya of its own.

    exec'd over a command port in a disposable Maya (AdvancedSkeleton's procedures read their own
    UI, so mayapy cannot build it), with IN / OUT set in the globals:
        IN  = the scene `make_orc_source.py` wrote (|root, 95 joints; |Orc_Body at its bind)
        OUT = where to save the built rig (.mb); `make_orc_rig_asset.py` turns it into the asset

2026-09-25.  The orc stands on Manny's bone NAMES with its own proportions (the neck 1.39x,
the upper arm 1.07x, the head 5.2 cm higher; pelvis, spine, legs, forearms and hands exactly
Manny's), which is the Creep's case: `as_creep_rig_procedure` puts every fit joint on its bone
by long path, constrains the bones by ORIENTATION only (the pelvis its position too), carries
every FK control on its bone's frame, stands the IK feet level and marks the rig rotation-only.
Its steps run as they are, with three differences set from here:

- `HEAD_MESH` / `ROOT` / `LAYER` name the orc's (`Orc_BodyShape`, `|root`, `Orc_Skeleton`);
- **the IK hand helpers take MANNY's rule, not the Creep's**: `ik_hand_gun` and `ik_hand_r`
  follow hand_r and `ik_hand_l` follows hand_l, each with maintainOffset -- where they stand in
  the orc's own file, which is exactly Manny's layout (ik_hand_gun ON hand_r).  The Creep's rule
  (ik_hand_gun zeroed at the origin) was that animator's layout for a creature whose file had
  them off its hands; here moving them would re-bind a bone Unreal's skeleton places;
- nothing of the Creep's tidy / sword / weapon-bone steps: the source already stands in the
  shipped shape, the helper bones on Manny's local values.

Then the mesh into `Group|Geometry`, where the shipped rig keeps it.  Refuses a scene whose skin
is not at its bind.
"""
import os
import maya.cmds as cmds
import maya.api.OpenMaya as om

PLANS = "C:/!!!Work/MayaScripts/docs/superpowers/plans"
MESHES = ("Orc_Body",)
IK_HELPERS = [("hand_r", "ik_hand_gun"), ("hand_r", "ik_hand_r"), ("hand_l", "ik_hand_l")]

for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
cmds.file(IN, open=True, force=True, executeScriptNodes=False)
P = PLANS + "/as_creep_rig_procedure.py"
g = {"__name__": "orc_rig", "__file__": P}
exec(compile(open(P, encoding="utf-8").read(), P, "exec"), g)
g["HEAD_MESH"] = "Orc_BodyShape"
g["ROOT"] = "|root"
g["LAYER"] = "Orc_Skeleton"
# the orc's shoulders are bulkier than the Creep's (measure_control_sizes.py on the shipped Orc D)
g["CONTROL_RADII"] = {"FKScapula": 16.183303, "FKShoulder": 22.590540}


def place_ik_helpers():
    """Manny's rule: each ik_hand helper follows its hand from where it stands (maintainOffset)."""
    b = g["bones"]()
    made = 0
    for hand, helper in IK_HELPERS:
        if hand in b and helper in b and not cmds.listRelatives(b[helper], children=True, type="constraint"):
            cmds.parentConstraint(b[hand], b[helper], maintainOffset=True)
            made += 1
    return made


g["place_ik_helpers"] = place_ik_helpers     # constrain() resolves it through the module's globals


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
    raise RuntimeError("the skin is not at its bind (%.2e) -- run make_orc_source.py first" % before)
state = {"autoKey": cmds.autoKeyframe(q=True, st=True), "em": cmds.evaluationManager(q=True, mode=True)[0]}
cmds.autoKeyframe(st=False)
cmds.evaluationManager(mode="off")
try:
    joints = list(g["bones"]().values())
    rest = dict((j, cmds.getAttr(j + ".worldMatrix[0]")) for j in joints)
    placed, worst_fit = g["fit"]()
    print("// fit: %d joints placed, mapped joints on their bones to %.6f cm" % (placed, worst_fit))
    g["build"]()
    print("// twist / in-between joints on the orc's: %s" % dict((k, round(v, 4)) for k, v in g["place_parts"]().items()))
    print("// constraints: %d" % g["constrain"]())
    n, worst = g["orient_controls"]()
    shapes = g["align_shapes"]()
    sdk = g["finger_sdk_axes"]()
    print("// IK foot controls level (AS's frame): worst %.5f deg" % g["as_frames"](g["LEVEL_CONTROLS"]))
    g["mark"]()
    print("// Main drawn at Manny's size (x%.4f)" % g["main_size"]())
    print("// clavicle / shoulder drawings grown: %s" % g["control_sizes"]())
    drift = max(max(abs(a - c) for a, c in zip(m, cmds.getAttr(j + ".worldMatrix[0]"))) for j, m in rest.items())
    print("// %d controls oriented (worst frame angle %.5f deg), %d curves aligned, %d finger SDK groups re-framed; "
          "bind-pose drift %.9f" % (n, worst, shapes, sdk, drift))
    geo = "|Group|Geometry"
    for name in MESHES:
        tr = cmds.ls(name, type="transform", long=True)
        if tr and not tr[0].startswith(geo + "|"):
            cmds.parent(tr[0], geo)
    print("// Geometry:", cmds.listRelatives(geo, children=True))
    print("// skin off its bind after the build: %.2e" % bind_error())
    unconstrained = [j.split("|")[-1] for j in g["bones"]().values()
                     if not cmds.listRelatives(j, children=True, type="constraint")]
    print("// bones with no constraint of their own (ride their parent): %s" % sorted(unconstrained))
finally:
    cmds.evaluationManager(mode=state["em"])
    cmds.autoKeyframe(st=state["autoKey"])
    cmds.select(clear=True)
if not os.path.isdir(os.path.dirname(OUT)):
    os.makedirs(os.path.dirname(OUT))
cmds.file(rename=OUT)
cmds.file(save=True, type="mayaBinary", force=True)
print("// saved", OUT)
