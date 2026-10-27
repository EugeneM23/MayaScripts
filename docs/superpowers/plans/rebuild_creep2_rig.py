"""Build the second Creep's AdvancedSkeleton rig -- LIVE, in a Maya of its own.

    exec'd over a command port in a disposable Maya (AdvancedSkeleton's procedures read their own
    UI, so mayapy cannot build it), with IN / OUT set in the globals:
        IN  = the scene `make_creep2_source.py` wrote (|root, 93 joints; |Creep2_Body at its bind)
        OUT = where to save the built rig (.mb); `make_creep2_assets.py rig` turns it into the asset

2026-10-27.  Creep 2 stands on Manny's bone NAMES with its own proportions -- the Creep's and the
Orc's case: `as_creep_rig_procedure` puts every fit joint on its bone by long path (the left side
non-symmetric), constrains the bones by ORIENTATION only (the pelvis its position too), carries
every FK control on its bone's frame, stands the IK feet level and marks the rig rotation-only.
Its steps run as `rebuild_orc_rig.py` runs them, with Creep 2's names:

- `HEAD_MESH` / `ROOT` / `LAYER` are Creep 2's (`Creep2_BodyShape` - one mesh, whose top is the
  head's -, `|root`, `Creep2_Skeleton`);
- **the IK hand helpers take MANNY's rule**: ik_hand_gun and ik_hand_r follow hand_r, ik_hand_l
  follows hand_l, from where the file has them (measured: all three ON their hands, Manny's
  layout - Unreal's file), maintainOffset;
- nothing of the first Creep's tidy / sword / weapon-bone steps: the source already stands in the
  shipped shape, the weapon sockets in UE's convention, the camera bones on Manny's values.

Then the mesh into `Group|Geometry`.  Refuses a scene whose skin is not at its bind.
"""
import os
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

PLANS = "C:/!!!Work/MayaScripts/docs/superpowers/plans"
MESHES = ("Creep2_Body",)
IK_HELPERS = [("hand_r", "ik_hand_gun"), ("hand_r", "ik_hand_r"), ("hand_l", "ik_hand_l")]

for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
cmds.file(IN, open=True, force=True, executeScriptNodes=False)
P = PLANS + "/as_creep_rig_procedure.py"
g = {"__name__": "creep2_rig", "__file__": P}
exec(compile(open(P, encoding="utf-8").read(), P, "exec"), g)
g["HEAD_MESH"] = "Creep2_BodyShape"
g["ROOT"] = "|root"
g["LAYER"] = "Creep2_Skeleton"


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

# Creep 2's midline stands 0.32 cm off x = 0 (pelvis, spine, head, and the hands' centre: the body is
# shifted against its root), and AdvancedSkeleton calls any fit joint past 1 % of its scale on +X a
# LEFT-side joint and refuses the build («"HeadEnd" is on the Left side»). So the midline fit joints
# go onto x = 0 and the rig's middle joints stand that far beside their bones - which keep their places:
# they follow AS by orientation with offsets, the pelvis its position too. The side joints stay exactly
# on their bones.
MIDDLE = set(k for k, v in g["ROWS"] if v in ("pelvis", "neck_01", "head") or v.startswith("spine_")) | {"HeadEnd"}
_fit = g["fit"]


def fit_centred(heel_y=0.0):
    placed, worst = _fit(heel_y)
    fj = g["fit_joints"]()
    order = sorted(fj.values(), key=lambda p: p.count("|"))
    was = dict((p, g["_pos"](p)) for p in order)
    moved = 0.0
    for path in order:
        if path.split("|")[-1] in MIDDLE:
            p = g["_pos"](path)
            moved = max(moved, abs(p.x))
            g["_snap"](path, om.MVector(0.0, p.y, p.z))
    for path in order:
        if path.split("|")[-1] not in MIDDLE:
            g["_snap"](path, was[path])
    mel.eval("asFitModeManualUpdate;")
    print("// midline fit joints put on x = 0 (they stood up to %.4f cm off it): %s"
          % (moved, sorted(k for k in fj if k in MIDDLE)))
    off = [k for k, p in fj.items() if k not in MIDDLE and abs(g["_pos"](p).x) < 0.5]
    if off:
        print("// fit joints near the midline left where they are: %s" % sorted(off))
    return placed, worst


g["fit"] = fit_centred


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
if before > 1e-3:
    raise RuntimeError("the skin is not at its bind (%.2e) -- run make_creep2_source.py first" % before)
state = {"autoKey": cmds.autoKeyframe(q=True, st=True), "em": cmds.evaluationManager(q=True, mode=True)[0]}
cmds.autoKeyframe(st=False)
cmds.evaluationManager(mode="off")
try:
    joints = list(g["bones"]().values())
    rest = dict((j, cmds.getAttr(j + ".worldMatrix[0]")) for j in joints)
    placed, worst_fit = g["fit"]()
    print("// fit: %d joints placed, mapped joints on their bones to %.6f cm" % (placed, worst_fit))
    g["build"]()
    print("// twist / in-between joints on Creep 2's: %s" % dict((k, round(v, 4)) for k, v in g["place_parts"]().items()))
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
