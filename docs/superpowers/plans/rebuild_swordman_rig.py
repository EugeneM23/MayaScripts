"""Build the Swordman's AdvancedSkeleton rig -- LIVE, in a Maya of its own.

    exec'd over a command port in a disposable Maya (AdvancedSkeleton's procedures read
    their own UI, so mayapy cannot build it), with IN / OUT set in the globals:
        IN  = sources/swordman/Swordman_Source.mb (|root, 55 joints; |Swordman_Body at its bind)
        OUT = where to save the built rig (.mb); make_swordman_assets.py turns it into the asset

2026-11-01. He stands on OUR bone names with HIS proportions -- the Creep's, the Orc's and
Creep 2's case -- so `as_creep_rig_procedure` runs as `rebuild_creep2_rig.py` runs it, with
three differences of his own:

  * NO FINGERS. His hand is a mitten and his skeleton has none (the animator: «всё кроме
    пальцев»), so the FitSkeleton's five finger chains are deleted before the build, the way
    the procedure already deletes Eye and Jaw. `finger_sdk_axes` has nothing to re-frame.
  * MANNY's ik_hand rule, as Creep 2 uses: ik_hand_gun and ik_hand_r follow hand_r, ik_hand_l
    follows hand_l, from where the source puts them.
  * His sword and shield are catalog rows now, so they leave the rig (`drop_props`'s job on
    the Creep): a weapon is added and removed like on every other character.

His bind is an A-pose with the arms 71 deg down from horizontal -- steeper than Manny's but
still an A-pose, and `fit()` puts every fit joint on its bone, so the build pose is his bind.
"""
import os

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

PLANS = "C:/!!!Work/MayaScripts/docs/superpowers/plans"
MESHES = ("Swordman_Body",)
PROPS = ("Swordman_Sword", "Swordman_Shield")
IK_HELPERS = [("hand_r", "ik_hand_gun"), ("hand_r", "ik_hand_r"), ("hand_l", "ik_hand_l")]
# The FitSkeleton's finger chains. His skeleton has no finger BONES (the animator:
# «всё кроме пальцев»), but AdvancedSkeleton will not build a hand that is a leaf:
# the Elbow's twist Parts blend toward `WristBM_<side>`, and a Wrist with no child
# never gets one -- «The source attribute 'WristBM_R.outputMatrix' cannot be found»,
# measured 2026-11-01 with the chains deleted and with the finger driving system
# dropped as well. Dropping the Elbow's twistJoints instead would leave his
# lowerarm_twist_01/02 undriven, which is worse.
#
# So the FIT keeps its fingers and the SKELETON does not: `_target` finds no bone for
# a finger fit joint, so `constrain()` drives nothing from them. What is left is five
# chains of controls per hand that move AdvancedSkeleton's own joints and no game bone.
FINGER_ROOTS = ()

for plugin in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except Exception:
        pass

cmds.file(IN, open=True, force=True, executeScriptNodes=False)

P = PLANS + "/as_creep_rig_procedure.py"
g = {"__name__": "swordman_rig", "__file__": P}
exec(compile(open(P, encoding="utf-8").read(), P, "exec"), g)
g["HEAD_MESH"] = "Swordman_BodyShape"
g["ROOT"] = "|root"
g["LAYER"] = "Swordman_Skeleton"


def place_ik_helpers():
    """Manny's rule: each ik_hand helper follows its hand from where it stands."""
    b = g["bones"]()
    made = 0
    for hand, helper in IK_HELPERS:
        if hand in b and helper in b and not cmds.listRelatives(
                b[helper], children=True, type="constraint"):
            cmds.parentConstraint(b[hand], b[helper], maintainOffset=True)
            made += 1
    return made


g["place_ik_helpers"] = place_ik_helpers      # constrain() resolves it through the globals

_fit = g["fit"]


def fit_fingerless(heel_y=0.0):
    """The procedure's fit, then the finger chains out of the FitSkeleton.

    After `fit()`, so AdvancedSkeleton's own non-symmetry copies exist and go with them.
    """
    placed, worst = _fit(heel_y)
    fj = g["fit_joints"]()
    gone = []
    for leaf, path in sorted(fj.items()):
        root = leaf.split("_NonSymmetry")[0]
        if root in FINGER_ROOTS and cmds.objExists(path):
            cmds.delete(path)
            gone.append(leaf)
    # and the finger driving system's own data with them: left on the
    # FitSkeleton it makes the build wire a system whose joints are gone
    # («The source attribute 'WristBM_R.outputMatrix' cannot be found»).
    dropped = []
    if not FINGER_ROOTS:
        print("// the FitSkeleton keeps its fingers (see FINGER_ROOTS); the skeleton has none")
        return placed, worst
    for attr in ("drivingSystem_Fingers_R", "drivingSystem_Fingers_L"):
        if cmds.attributeQuery(attr, node="FitSkeleton", exists=True):
            cmds.deleteAttr("FitSkeleton", attribute=attr)
            dropped.append(attr)
    mel.eval("asFitModeManualUpdate;")
    print("// finger chains deleted from the FitSkeleton: %s" % gone)
    print("// finger driving system dropped: %s" % dropped)
    left = [k for k in g["fit_joints"]() if "Finger" in k]
    if left:
        raise RuntimeError("finger fit joints still there: %s" % sorted(left))
    return placed, worst


g["fit"] = fit_fingerless


def bind_error():
    worst = 0.0
    for skin in cmds.ls(type="skinCluster"):
        for index in cmds.getAttr(skin + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (skin, index), s=True, d=False)
            if src:
                m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (skin, index))) * \
                    om.MMatrix(cmds.getAttr(cmds.ls(src[0], long=True)[0] + ".worldMatrix[0]"))
                worst = max(worst, max(abs(a - b) for a, b in zip(list(m), list(om.MMatrix()))))
    return worst


before = bind_error()
if before > 1e-3:
    raise RuntimeError("the skin is not at its bind (%.2e) -- run make_swordman_source.py first"
                       % before)

midline = max(abs(om.MMatrix(cmds.getAttr(g["bones"]()[name] + ".worldMatrix[0]"))[12])
              for name in ("pelvis", "spine_01", "spine_05", "neck_01", "head"))
print("// his midline stands %.4f cm off x = 0 (AdvancedSkeleton refuses past 1 %% of its scale)"
      % midline)

state = {"autoKey": cmds.autoKeyframe(q=True, st=True),
         "em": cmds.evaluationManager(q=True, mode=True)[0]}
cmds.autoKeyframe(st=False)
cmds.evaluationManager(mode="off")
try:
    joints = list(g["bones"]().values())
    rest = dict((j, cmds.getAttr(j + ".worldMatrix[0]")) for j in joints)
    placed, worst_fit = g["fit"]()
    print("// fit: %d joints placed, mapped joints on their bones to %.6f cm" % (placed, worst_fit))
    g["build"]()
    print("// twist / in-between joints on his: %s"
          % dict((k, round(v, 4)) for k, v in g["place_parts"]().items()))
    print("// constraints: %d" % g["constrain"]())
    n, worst = g["orient_controls"]()
    shapes = g["align_shapes"]()
    print("// IK foot controls level (AS's frame): worst %.5f deg"
          % g["as_frames"](g["LEVEL_CONTROLS"]))
    g["mark"]()
    print("// Main drawn at Manny's size (x%.4f)" % g["main_size"]())
    print("// clavicle / shoulder drawings grown: %s" % g["control_sizes"]())
    drift = max(max(abs(a - c) for a, c in zip(m, cmds.getAttr(j + ".worldMatrix[0]")))
                for j, m in rest.items())
    print("// %d controls oriented (worst frame angle %.5f deg), %d curves aligned; "
          "bind-pose drift %.9f" % (n, worst, shapes, drift))

    geo = "|Group|Geometry"
    for name in MESHES:
        tr = cmds.ls(name, type="transform", long=True)
        if tr and not tr[0].startswith(geo + "|"):
            cmds.parent(tr[0], geo)
    for name in PROPS:                      # the catalog's business now
        tr = cmds.ls(name, type="transform", long=True)
        if tr:
            cmds.delete(tr[0])
    print("// Geometry:", cmds.listRelatives(geo, children=True))
    print("// skin off its bind after the build: %.2e" % bind_error())
    unconstrained = [j.split("|")[-1] for j in g["bones"]().values()
                     if not cmds.listRelatives(j, children=True, type="constraint")]
    print("// bones with no constraint of their own (ride their parent): %s" % sorted(unconstrained))
    print("// controls: %d" % len(cmds.sets("ControlSet", q=True) or []))
finally:
    cmds.evaluationManager(mode=state["em"])
    cmds.autoKeyframe(st=state["autoKey"])
    cmds.select(clear=True)

if not os.path.isdir(os.path.dirname(OUT)):
    os.makedirs(os.path.dirname(OUT))
cmds.file(rename=OUT)
cmds.file(save=True, type="mayaBinary", force=True)
print("// saved", OUT)
