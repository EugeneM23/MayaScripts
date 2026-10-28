"""Tools > 1P Setup, standalone (2026-10-16).

    mayapy verify_1p_setup.py <UE5 clip .fbx> [rig key, default Manny_Rig]

A rig added, the clip retargeted through the button, then the press:
- one undo takes everything back, redo brings it again;
- both layers on: the game skeleton plays the take as before (camera_root aside);
- both muted: every frame stands in the first frame's pose;
- Lower alone: pelvis and feet as before, spine_03's world turn the first frame's;
- the knot's turn on Upper only, its travel on Lower only; Main.view 1;
- the camera under the knot, keyed: its world track and camera_root's as before the press
  (2026-10-20: it used to lose its keys), camera_root following it;
- a second press refused.
"""

import math
import os
import sys

import maya.standalone
maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))).replace("\\", "/")
sys.path.insert(0, REPO + "/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
CLIP = sys.argv[1].replace("\\", "/")
RIG_KEY = sys.argv[2] if len(sys.argv) > 2 else "Manny_Rig"

from maya_scenesetup import catalog, character, camera  # noqa: E402
from maya_tools import firstperson as fp, knots  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402

FAILS = []
COUNT = [0]


def gate(ok, msg):
    COUNT[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    if not ok:
        FAILS.append(msg)


def wm(n):
    return om.MMatrix(cmds.xform(n, query=True, matrix=True, worldSpace=True))


def apart(a, b):
    d = max(abs(a[12 + i] - b[12 + i]) for i in range(3))
    q = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    r = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    dot = min(1.0, abs(q.x * r.x + q.y * r.y + q.z * r.z + q.w * r.w))
    import math
    return d, math.degrees(2 * math.acos(dot))


def track(nodes, frames):
    out = {}
    for f in frames:
        cmds.currentTime(f)
        out[f] = dict((n, wm(n)) for n in nodes)
    return out


def worst(a, b, nodes=None):
    cm = deg = 0.0
    for f in a:
        for n in (nodes or a[f]):
            d, g = apart(a[f][n], b[f][n])
            cm, deg = max(cm, d), max(deg, g)
    return cm, deg


cmds.file(new=True, force=True)
cmds.undoInfo(state=True, infinity=True)
character.add_character(catalog.character_by_key(RIG_KEY))
rig = maya_rigs.rigs()[0]
N = lambda leaf: cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]  # noqa: E731
cmds.namespace(add="clip")
cmds.namespace(set=":clip")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
before = set(cmds.ls(type="joint", long=True))
mel.eval('FBXImport -f "%s";' % CLIP)
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
          key=lambda j: j.count("|"))
keys = cmds.keyframe(new, query=True, timeChange=True) or [0, 24]
first, last = int(min(keys)), int(max(keys))
last = min(last, first + 40)
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
cmds.select(N("Main"), src)
ok, rtext = rr.run_retarget()
cmds.namespace(removeNamespace="clip", deleteNamespaceContent=True)
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
gate(ok, "clip retargeted onto %s (%d..%d)" % (rig.namespace, first, last))

frames = list(range(first, last + 1, 4))
bones = [N(b) for b in ("pelvis", "foot_l", "foot_r", "spine_03", "spine_05", "head",
                        "hand_r", "hand_l", "calf_l")]
legs = [N(b) for b in ("pelvis", "foot_l", "foot_r", "calf_l")]
raw = track(bones, frames)
BONE0 = cmds.ls(maya_rigs.node(rig, "camera_root"), long=True)
CAM0 = camera.keyed_node(BONE0[0]) if BONE0 else None
if CAM0:   # no UE clip moves camera_root (trap 83): a motion of the camera's own, keyed
    import math
    for f in range(first, last + 1, 3):
        for ch, amp in (("translateY", 6.0), ("rotateX", 12.0)):
            v = cmds.keyframe(CAM0, attribute=ch, query=True, eval=True, time=(f, f))[0]
            cmds.setKeyframe(CAM0, attribute=ch, time=f, value=v + amp * math.sin(f * 0.4))
cam_raw = track([BONE0[0]], frames) if CAM0 else None
pose0 = track(bones, [first])[first]

_sh0 = cmds.listRelatives(N("FKShoulder_R"), shapes=True, fullPath=True)[0]
SHOULDER_RGB = fp.override_rgb(cmds.getAttr(_sh0 + ".overrideEnabled"),
                               cmds.getAttr(_sh0 + ".overrideRGBColors"),
                               cmds.getAttr(_sh0 + ".overrideColorRGB")[0],
                               cmds.getAttr(_sh0 + ".overrideColor"))
cmds.currentTime(first + 7)
cmds.select(N("FKElbow_R"))
line = fp.setup()
print("   ", line)
lower = [l for l in fp.setup_layers(rig.namespace) if l.startswith(fp.LOWER)]
upper = [l for l in fp.setup_layers(rig.namespace) if l.startswith(fp.UPPER)]
gate(len(lower) == 1 and len(upper) == 1, "two layers made: %s / %s" % (lower, upper))

cmds.undo()
HAS_VIEW = cmds.attributeQuery("view", node=N("Main"), exists=True)
gate(not fp.setup_layers(rig.namespace) and not knots.knots()
     and not fp.display_layers_of(rig.namespace)
     and (not HAS_VIEW or cmds.getAttr(N("Main") + ".view") == 0),
     "one undo: no layer, no knot, Main.view 0")
cmds.redo()
lower, upper = lower[0], upper[0]
gate(cmds.objExists(lower) and cmds.objExists(upper) and fp.chest_of(rig) is not None,
     "redo brings layers and knot back")
if HAS_VIEW:
    gate(cmds.getAttr(N("Main") + ".view") == 1, "Main.view 1 (1P mesh)")
else:
    gate("no 1P mesh" in line, "no Main.view: said on the line")

knot = fp.chest_of(rig)
shapes = cmds.listRelatives(knot, shapes=True, fullPath=True) or []
gate(len(shapes) == 1 and cmds.nodeType(shapes[0]) == "nurbsCurve"
     and cmds.getAttr(shapes[0] + ".wireColorRGB")[0][0] > 0.8
     and cmds.getAttr(shapes[0] + ".useObjectColor") == 2
     and len(cmds.getAttr(shapes[0] + ".cv[*]")) == 5 and knot.endswith(fp.CHEST_NAME)
     and fp.chest_of(rig) == knot,
     "the chest control: %s, a red square curve, found by its marker" % knot.split("|")[-1])
from maya_scenesetup import rootcontrol  # noqa: E402
rc = rootcontrol.find(rig)
con = cmds.listRelatives(N("root"), children=True, type="parentConstraint", fullPath=True) or []
gate(bool(rc) and con and [cmds.ls(t, long=True)[0] for t in
                          cmds.parentConstraint(con[0], q=True, targetList=True)] == [rc],
     "the root bone follows the Root control under Main (%s)" % rc)
rot_up = all(cmds.animLayer(upper, query=True, findCurveForPlug=knot + "." + c)
             for c in ("rotateX", "rotateY", "rotateZ"))
rot_lo = any(cmds.animLayer(lower, query=True, findCurveForPlug=knot + "." + c)
             for c in ("rotateX", "rotateY", "rotateZ"))
tr_lo = any(cmds.animLayer(lower, query=True, findCurveForPlug=knot + "." + c)
            for c in ("translateX", "translateY", "translateZ"))
gate(rot_up and not rot_lo and tr_lo, "knot's turn on Upper only, travel on Lower")

#  2026-10-21: the controls' display layers, and stabilized by default
dls = fp.display_layers_of(rig.namespace)
low_dl = [d for d in dls if d.endswith(fp.LOWER_CONTROLS)]
up_dl = [d for d in dls if d.endswith(fp.UPPER_CONTROLS)]


def members(layer):
    return set(cmds.ls(cmds.editDisplayLayerMembers(layer, query=True, fullNames=True) or [],
                       long=True) or [])


def shape_in(ctrl, layer):
    shapes = cmds.listRelatives(ctrl, shapes=True, fullPath=True, noIntermediate=True) or []
    return bool(shapes) and set(shapes) <= members(layer)


gate(len(low_dl) == 1 and len(up_dl) == 1, "two display layers: %s / %s" % (low_dl, up_dl))
if low_dl and up_dl:
    lo, up = low_dl[0], up_dl[0]
    gate(cmds.getAttr(lo + ".visibility") == 0 and cmds.getAttr(up + ".visibility") == 1,
         "the lower controls' layer hidden, the upper's shown")
    gate(shape_in(N("Main"), lo) and shape_in(N("IKLeg_L"), lo) and shape_in(N("FKSpine1_M"), lo)
         and shape_in(knot, up) and shape_in(N("FKShoulder_R"), up) and shape_in(N("FKHead_M"), up),
         "lower: Main, IK leg, Spine1; upper: the chest, shoulder, head (their shapes)")
    gate(not any(cmds.nodeType(m) == "transform" for m in members(lo) | members(up)),
         "only shapes in the layers (AS nests its FK controls)")
    sh = cmds.listRelatives(N("FKShoulder_R"), shapes=True, fullPath=True)[0]
    gate(cmds.getAttr(sh + ".useObjectColor") == 2
         and max(abs(a - b) for a, b in zip(cmds.getAttr(sh + ".wireColorRGB")[0],
                                            fp._rendering(SHOULDER_RGB))) < 1e-3,
         "the shoulder keeps its colour through the layer (%s)" % (SHOULDER_RGB,))
    cam_c = camera.control_for(N("camera_root")) if cmds.ls(maya_rigs.node(rig, "camera_root")) \
        else None
    if cam_c:
        gate(shape_in(cam_c, up), "the camera's control in the upper layer")
    cmds.currentTime(first + 3)
    vis = cmds.listRelatives(N("FKShoulder_R"), shapes=True, fullPath=True)[0]
    gate(om.MDagPath.getAPathTo(om.MSelectionList().add(vis).getDependNode(0)).isVisible()
         and not om.MDagPath.getAPathTo(om.MSelectionList().add(
             cmds.listRelatives(N("IKLeg_L"), shapes=True, fullPath=True)[0]).getDependNode(0)
         ).isVisible(), "a shoulder control visible, a leg control hidden")
gate(cmds.getAttr(upper + ".mute") == 1 and cmds.getAttr(lower + ".mute") == 0,
     "by default %s muted (stabilized), %s on" % (upper, lower))
sp0 = N("spine_03")
stab = track([sp0], frames)
turn0 = max(apart(stab[f][sp0], pose0[sp0])[1] for f in frames)
gate(turn0 < 0.05, "stabilized by default: spine_03 keeps the first frame's turn (%.4f deg)"
     % turn0)
cmds.setAttr(upper + ".mute", 0)

both = track(bones, frames)
cm, deg = worst(raw, both)
gate(cm < 0.02 and deg < 0.05, "both layers on: the take as before (%.4f cm, %.4f deg)" % (cm, deg))

cmds.setAttr(lower + ".mute", 1)
cmds.setAttr(upper + ".mute", 1)
muted = track(bones, frames)
cm, deg = worst(dict((f, pose0) for f in frames), muted)
gate(cm < 0.02 and deg < 0.05, "both muted: the first frame's pose (%.4f cm, %.4f deg)" % (cm, deg))

cmds.setAttr(lower + ".mute", 0)
lone = track(bones, frames)
cm, deg = worst(raw, lone, legs)
gate(cm < 0.02 and deg < 0.05, "Lower alone: pelvis and legs as before (%.4f cm, %.4f deg)"
     % (cm, deg))
sp = N("spine_03")
turn = max(apart(lone[f][sp], pose0[sp])[1] for f in frames)
moved = max(apart(raw[f][sp], pose0[sp])[1] for f in frames)
gate(turn < 0.05, "Lower alone: spine_03 keeps the first frame's turn (%.4f deg; the take turns "
     "it %.2f)" % (turn, moved))
cmds.setAttr(upper + ".mute", 0)

HAS_CAM = bool(cmds.ls(maya_rigs.node(rig, "camera_root")))
if not HAS_CAM:
    gate("no camera_root" in line, "no camera_root: said on the line")
bone = N("camera_root") if HAS_CAM else None
cam = camera.camera_for(bone) if HAS_CAM else None
ctrl = camera.control_of(cam) if cam else None
parent = cmds.listRelatives(ctrl, parent=True, fullPath=True) if ctrl else None
HAS_CAM and gate(bool(ctrl) and parent and parent[0] == knot and bool(cmds.keyframe(ctrl, query=True))
     and not cmds.keyframe(cam, query=True),
     "camera control %s under the chest control, keyed (the camera itself not)" % ctrl)
if HAS_CAM and cam_raw:
    cm, deg = worst(cam_raw, track([bone], frames))
    gate(cm < 0.01 and deg < 0.01, "camera_root keeps its world track through the press "
         "(%.4f cm, %.4f deg)" % (cm, deg))
offs = []
for f in (frames if HAS_CAM else []):
    cmds.currentTime(f)
    offs.append(wm(bone) * wm(cam).inverse())
spread = max([apart(offs[0], o)[0] for o in offs] or [0.0])
HAS_CAM and gate(spread < 1e-3, "camera_root follows the camera (%.6f)" % spread)
#  the game's crosshair on the camera (2026-10-28): where a hit goes - the root's forward held
#  level from the camera, whatever the take's own camera turn - never selected
hairs = fp.crosshairs_of(rig.namespace)
if HAS_CAM:
    hair = hairs[0] if len(hairs) == 1 else None
    on_cam = bool(hair) and cmds.listRelatives(hair, parent=True, fullPath=True)[0] == cam
    shapes = cmds.listRelatives(hair, shapes=True, fullPath=True) or [] if hair else []
    cvs = [cmds.xform(s + ".cv[*]", query=True, translation=True, objectSpace=True) for s in shapes]
    centred = len(cvs) == 2 and all(abs(sum(c[:-3][a::3])) < 1e-6      # closed: the last repeats
                                    for c in cvs for a in (0, 1))
    ahead = len(cvs) == 2 and all(abs(z + fp.CROSSHAIR_DISTANCE) < 1e-6 for c in cvs for z in c[2::3])
    ref = len(shapes) == 2 and all(cmds.getAttr(s + ".overrideDisplayType") == 2 for s in shapes)
    root_bone = cmds.listRelatives(bone, parent=True, fullPath=True)[0]
    off_aim, off_cam = 0.0, 0.0
    for f in frames:
        cmds.currentTime(f)
        aim = om.MVector(0, 0, -1) * wm(hair)
        fwd = om.MVector(0, -1, 0) * wm(root_bone)
        off_aim = max(off_aim, math.degrees(aim.angle(fwd)))
        off_cam = max(off_cam, math.degrees(aim.angle(om.MVector(0, 0, -1) * wm(cam))))
    gate(on_cam and centred and ahead and ref and "crosshair" in line and off_aim < 1e-3,
         "the crosshair on the camera along the root's forward (%.4f deg off it, the camera's "
         "axis up to %.2f deg away), Reference (%s: on %s, centred %s, ahead %s, ref %s, said %s)"
         % (off_aim, off_cam, hair, on_cam, centred, ahead, ref, "crosshair" in line))
else:
    gate(not hairs, "no camera: no crosshair")
nodes = len(cmds.ls())
again = fp.setup([N("Main")])
gate(again.startswith("1P Setup:") and "already" in again and len(cmds.ls()) == nodes,
     "a second press refused: %s" % again[:70])

#  the layers merged into the base, then the knot baked off (2026-10-20, the animator: «а если я
#  сделал сетап а потом удалил слои и все перепек?»): the camera leaves the knot with its motion
if HAS_CAM:
    from maya_timebar import layerscene
    before = track(bones + [bone], frames)
    base = cmds.animLayer(query=True, root=True)
    ok, mline = layerscene.merge_selected([base, lower, upper])
    gate(ok and cmds.ls(type="animLayer") == [base], "layers merged into the base: %s" % mline)
    cm, deg = worst(before, track(bones + [bone], frames))
    gate(cm < 0.02 and deg < 0.05, "after the merge: body and camera_root as before (%.4f cm, "
         "%.4f deg)" % (cm, deg))
    bline = knots.bake([fp.chest_of(rig)])
    cmds.undo()               # straight after the press (trap 222)
    back = fp.chest_of(rig) is not None
    cmds.redo()
    gate(back and not knots.knots(), "one undo brings the knot back, redo bakes it again")
    cam2 = camera.control_for(bone)
    home = cmds.listRelatives(cam2, parent=True, fullPath=True) if cam2 else None
    gate(not knots.knots() and bool(cam2) and bool(home) and home[0] == N("Main")
         and camera.parent_choice(cam2) == "Main",
         "chest baked off (%s), camera control back under Main (%s)" % (bline, home))
    gate(not fp.crosshairs_of(rig.namespace), "the crosshair gone with the chest")
    cm, deg = worst(before, track(bones + [bone], frames))
    gate(cm < 0.02 and deg < 0.05, "after the knot's Bake: body and camera_root as before (%.4f cm, "
         "%.4f deg)" % (cm, deg))

print("%d gates, %d failed" % (COUNT[0], len(FAILS)))
for f in FAILS:
    print("  FAIL:", f)
