"""Does the rewired skin deform the same as his, under a real pose?

The bind is proven to 5e-12. What is NOT yet proven is the change of basis: our
bindPreMatrix is re-expressed for scale-1 frames, and the claim is that a
uniform scale cancels. Put the same WORLD rotation on the same bone in both
scenes and compare every vertex.
"""
import math
import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds
import maya.api.OpenMaya as om

HIS = r"C:\!!!Work\MayaScripts\sources\swordman\Swordman_Scene.mb"
OURS = r"C:\!!!Work\MayaScripts\sources\swordman\Swordman_Source.mb"
P = "BaseFBXASC032Human"
SKIN = "skinCluster1"

# his bone -> ours, the 17 skinned
PAIRS = {"Pelvis": "pelvis", "Ribcage": "spine_05", "Head": "head",
         "LCollarbone": "clavicle_l", "LUpperarm": "upperarm_l",
         "LForearm": "lowerarm_l", "LPalm": "hand_l",
         "RCollarbone": "clavicle_r", "RUpperarm": "upperarm_r",
         "RForearm": "lowerarm_r", "RPalm": "hand_r",
         "LThigh": "thigh_l", "LCalf": "calf_l", "LFoot": "foot_l",
         "RThigh": "thigh_r", "RCalf": "calf_r", "RFoot": "foot_r"}
# depth order, parents first
ORDER = ["Pelvis", "LThigh", "RThigh", "LCalf", "RCalf", "LFoot", "RFoot",
         "Ribcage", "LCollarbone", "RCollarbone", "Head",
         "LUpperarm", "RUpperarm", "LForearm", "RForearm", "LPalm", "RPalm"]


def leaf(p):
    return p.split("|")[-1].split(":")[-1]


def points(path):
    sel = om.MSelectionList().add(path)
    got = om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)
    return [om.MPoint(p.x, p.y, p.z) for p in got]


def about(point, degrees, axis=(1.0, 0.0, 0.0)):
    """A world rotation of `degrees` about `axis` through `point`."""
    back = om.MMatrix()
    back[12], back[13], back[14] = -point.x, -point.y, -point.z
    fwd = om.MMatrix()
    fwd[12], fwd[13], fwd[14] = point.x, point.y, point.z
    turn = om.MQuaternion(math.radians(degrees), om.MVector(*axis)).asMatrix()
    return back * turn * fwd


def pose_his(angle):
    cmds.file(HIS, open=True, force=True, executeScriptNodes=False, prompt=False)
    infs = cmds.skinCluster(SKIN, q=True, influence=True) or []
    bind = {}
    for i, inf in enumerate(infs):
        bind[leaf(inf)] = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (SKIN, i))).inverse()
    # stand him at the bind, parents first
    for name in ORDER:
        node = cmds.ls("*" + P + name, long=True, type="joint")[0]
        cmds.xform(node, worldSpace=True, matrix=list(bind[P + name]))
    at_bind = points("|Cylinder003|Cylinder003Shape")
    if angle:
        node = cmds.ls("*" + P + "RForearm", long=True, type="joint")[0]
        m = bind[P + "RForearm"]
        pivot = om.MVector(m[12], m[13], m[14])
        cmds.xform(node, worldSpace=True, matrix=list(m * about(pivot, angle)))
    return at_bind, points("|Cylinder003|Cylinder003Shape"), bind


def pose_ours(angle, pivot):
    cmds.file(OURS, open=True, force=True, executeScriptNodes=False, prompt=False)
    node = cmds.ls("*lowerarm_r", long=True, type="joint")[0]
    at_bind = points(cmds.listRelatives(cmds.ls("*Swordman_Body", long=True)[0],
                                        shapes=True, fullPath=True, noIntermediate=True)[0])
    if angle:
        m = om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))
        cmds.xform(node, worldSpace=True, matrix=list(m * about(pivot, angle)))
    shape = cmds.listRelatives(cmds.ls("*Swordman_Body", long=True)[0],
                               shapes=True, fullPath=True, noIntermediate=True)[0]
    return at_bind, points(shape)


def worst(a, b):
    return max((om.MVector(x - y).length() for x, y in zip(a, b)), default=0.0)


for angle in (0.0, 30.0, 75.0):
    his_bind, his_posed, bind = pose_his(angle)
    m = bind[P + "RForearm"]
    pivot = om.MVector(m[12], m[13], m[14])
    our_bind, our_posed = pose_ours(angle, pivot)
    moved = worst(his_bind, his_posed)
    print("turn %5.1f deg about world X at his right elbow:" % angle)
    print("   the mesh moved %8.3f cm (his own skin)" % moved)
    print("   his skin vs ours: worst vertex %.3e cm" % worst(his_posed, our_posed))

maya.standalone.uninitialize()
