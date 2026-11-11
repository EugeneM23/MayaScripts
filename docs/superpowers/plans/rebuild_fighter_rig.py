"""Build the Fighter's AdvancedSkeleton rig -- LIVE, in a Maya of its own.

    exec'd over a command port in a disposable Maya (AdvancedSkeleton's procedures read their own
    UI, so mayapy cannot build it), with IN / OUT set in the globals:
        IN  = sources/fighter/Fighter_Source.mb (|root, 82 joints; |Fighter_Body at its bind)
        OUT = where to save the built rig (.mb); `make_fighter_assets.py rig` turns it into the asset

2026-11-11 (spec: docs/superpowers/specs/2026-11-11-fighter-design.md).  `as_creep_rig_procedure`
as `rebuild_creep2_rig.py` runs it (Manny's ik_hand rule, the midline fit joints on x = 0), with
what his skeleton asks of it:

- **ghosts**: his spine stops at spine_04 and his fingers hang on the hand with no metacarpal, so
  the fit's `Spine5` and four `<Finger>Finger0` have no bone.  They stay (AdvancedSkeleton's chains
  need them) and drive nothing: Spine5 half way spine_04 -> neck_01 on the midline, a metacarpal a
  third of the way hand -> its finger_01; every mapped fit joint is put back on its bone after.
- **his twists**: one thigh and one calf twist a leg - Hip and Knee get one Part each, mapped
  HipPart1 -> thigh_twist_01, KneePart1 -> calf_twist_01; his upper-arm twists stand unevenly
  (0.149 / 0.595 of the bone), which one BM weight cannot place, so that segment keeps AS's spacing
  and the bones follow by orientation with their offsets.
- `helm` and `jaw` have no fit joint: they ride the head.
"""
import os
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

PLANS = "C:/!!!Work/MayaScripts/docs/superpowers/plans"
MESHES = ("Fighter_Body",)
IK_HELPERS = [("hand_r", "ik_hand_gun"), ("hand_r", "ik_hand_r"), ("hand_l", "ik_hand_l")]
FINGERS = ("Index", "Middle", "Ring", "Pinky")

for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
cmds.file(IN, open=True, force=True, executeScriptNodes=False)
P = PLANS + "/as_creep_rig_procedure.py"
g = {"__name__": "fighter_rig", "__file__": P}
exec(compile(open(P, encoding="utf-8").read(), P, "exec"), g)
g["HEAD_MESH"] = "Fighter_BodyShape"
g["ROOT"] = "|root"
g["LAYER"] = "Fighter_Skeleton"
g["PART_ROWS"] = [("ShoulderPart1", "upperarm_twist_01"), ("ShoulderPart2", "upperarm_twist_02"),
                  ("ElbowPart1", "lowerarm_twist_02"), ("ElbowPart2", "lowerarm_twist_01"),
                  ("HipPart1", "thigh_twist_01"), ("KneePart1", "calf_twist_01"), ("NeckPart1", "neck_02")]
g["TWIST_SEGMENTS"] = [("Elbow", "lowerarm", "hand", ("lowerarm_twist_02", "lowerarm_twist_01"), "Wrist"),
                       ("Hip", "thigh", "calf", ("thigh_twist_01",), "Knee"),
                       ("Knee", "calf", "foot", ("calf_twist_01",), "Ankle")]


def place_ik_helpers():
    """Manny's rule: each ik_hand helper follows its hand from where it stands (maintainOffset)."""
    b = g["bones"]()
    made = 0
    for hand, helper in IK_HELPERS:
        if hand in b and helper in b and not cmds.listRelatives(b[helper], children=True, type="constraint"):
            cmds.parentConstraint(b[hand], b[helper], maintainOffset=True)
            made += 1
    return made


g["place_ik_helpers"] = place_ik_helpers

MIDDLE = set(k for k, v in g["ROWS"] if v in ("pelvis", "neck_01", "head") or v.startswith("spine_")) | {"HeadEnd"}
_fit = g["fit"]


def fit_fighter(heel_y=0.0):
    _fit(heel_y)
    fj = g["fit_joints"]()
    b = g["bones"]()
    pos, snap = g["_pos"], g["_snap"]
    # one twist on each leg segment, on both sides
    for leaf in ("Hip", "Knee", "Hip" + g["NONSYM"], "Knee" + g["NONSYM"]):
        if leaf in fj:
            if not cmds.attributeQuery("twistJoints", node=fj[leaf], exists=True):
                cmds.addAttr(fj[leaf], k=True, ln="twistJoints", at="long", min=0, dv=1)
            cmds.setAttr(fj[leaf] + ".twistJoints", 1)
    # the ghosts, and every mapped fit joint on its bone, parents first (a move carries the children),
    # the midline on x = 0
    s4, n1 = pos(b["spine_04"]), pos(b["neck_01"])
    ghosts = {"Spine5": om.MVector(0.0, (s4.y + n1.y) / 2, (s4.z + n1.z) / 2)}
    for sd, s in (("", "_r"), (g["NONSYM"], "_l")):
        hand = pos(b["hand" + s])
        for f in FINGERS:
            ghosts["%sFinger0%s" % (f, sd)] = hand + (pos(b["%s_01%s" % (f.lower(), s)]) - hand) / 3.0
    fj = g["fit_joints"]()
    for path in sorted(fj.values(), key=lambda p: p.count("|")):
        leaf = path.split("|")[-1]
        if leaf in ghosts:
            snap(path, ghosts[leaf])
            continue
        bone = g["_target"](leaf, b)
        if bone:
            p = pos(bone)
            if leaf in MIDDLE:
                p = om.MVector(0.0, p.y, p.z)
            snap(path, p)
    mel.eval("asFitModeManualUpdate;")
    fj = g["fit_joints"]()
    worst = max((pos(fj[leaf]) - pos(g["_target"](leaf, b))).length()
                for leaf in fj if g["_target"](leaf, b) and leaf not in MIDDLE)
    middle = max(abs(pos(fj[leaf]).x) for leaf in fj if leaf in MIDDLE)
    print("// ghosts placed: Spine5 %s; side joints on their bones to %.6f, midline off x = 0 by %.6f"
          % ([round(v, 2) for v in pos(fj["Spine5"])], worst, middle))
    return len(fj), worst


g["fit"] = fit_fighter


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
    raise RuntimeError("the skin is not at its bind (%.2e) -- run make_fighter_source.py first" % before)
state = {"autoKey": cmds.autoKeyframe(q=True, st=True), "em": cmds.evaluationManager(q=True, mode=True)[0]}
cmds.autoKeyframe(st=False)
cmds.evaluationManager(mode="off")
try:
    joints = list(g["bones"]().values())
    rest = dict((j, cmds.getAttr(j + ".worldMatrix[0]")) for j in joints)
    placed, worst_fit = g["fit"]()
    print("// fit: %d fit joints, mapped side joints on their bones to %.6f cm" % (placed, worst_fit))
    g["build"]()
    print("// twist / in-between joints on his: %s" % dict((k, round(v, 4)) for k, v in g["place_parts"]().items()))
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
