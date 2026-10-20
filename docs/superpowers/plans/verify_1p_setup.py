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

import sys

import maya.standalone
maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
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
CAM0 = camera.camera_for(BONE0[0]) if BONE0 else None
if CAM0:   # no UE clip moves camera_root (trap 83): a motion of the camera's own, keyed
    import math
    for f in range(first, last + 1, 3):
        for ch, amp in (("translateY", 6.0), ("rotateX", 12.0)):
            v = cmds.keyframe(CAM0, attribute=ch, query=True, eval=True, time=(f, f))[0]
            cmds.setKeyframe(CAM0, attribute=ch, time=f, value=v + amp * math.sin(f * 0.4))
cam_raw = track([BONE0[0]], frames) if CAM0 else None
pose0 = track(bones, [first])[first]

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
     and (not HAS_VIEW or cmds.getAttr(N("Main") + ".view") == 0),
     "one undo: no layer, no knot, Main.view 0")
cmds.redo()
lower, upper = lower[0], upper[0]
gate(cmds.objExists(lower) and cmds.objExists(upper) and len(knots.knots()) == 1,
     "redo brings layers and knot back")
if HAS_VIEW:
    gate(cmds.getAttr(N("Main") + ".view") == 1, "Main.view 1 (1P mesh)")
else:
    gate("no 1P mesh" in line, "no Main.view: said on the line")

knot = knots.knots()[0]
rot_up = all(cmds.animLayer(upper, query=True, findCurveForPlug=knot + "." + c)
             for c in ("rotateX", "rotateY", "rotateZ"))
rot_lo = any(cmds.animLayer(lower, query=True, findCurveForPlug=knot + "." + c)
             for c in ("rotateX", "rotateY", "rotateZ"))
tr_lo = any(cmds.animLayer(lower, query=True, findCurveForPlug=knot + "." + c)
            for c in ("translateX", "translateY", "translateZ"))
gate(rot_up and not rot_lo and tr_lo, "knot's turn on Upper only, travel on Lower")

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
parent = cmds.listRelatives(cam, parent=True, fullPath=True) if cam else None
HAS_CAM and gate(bool(cam) and parent and parent[0] == knot and bool(cmds.keyframe(cam, query=True)),
     "camera %s under the knot, keyed" % cam)
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
    bline = knots.bake([knots.knots()[0]])
    cmds.undo()               # straight after the press (trap 222)
    back = len(knots.knots()) == 1
    cmds.redo()
    gate(back and not knots.knots(), "one undo brings the knot back, redo bakes it again")
    cam2 = camera.camera_for(bone)
    home = cmds.listRelatives(cam2, parent=True, fullPath=True) if cam2 else None
    gate(not knots.knots() and bool(cam2) and bool(home)
         and home[0] == maya_rigs.group_of(N("Main")),
         "knot baked off (%s), camera in %s" % (bline, home))
    cm, deg = worst(before, track(bones + [bone], frames))
    gate(cm < 0.02 and deg < 0.05, "after the knot's Bake: body and camera_root as before (%.4f cm, "
         "%.4f deg)" % (cm, deg))

print("%d gates, %d failed" % (COUNT[0], len(FAILS)))
for f in FAILS:
    print("  FAIL:", f)
