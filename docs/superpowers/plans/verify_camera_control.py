"""The camera's control, the Root control and 1P Setup's chest control, standalone (2026-10-21).

    mayapy verify_camera_control.py <UE5 clip .fbx> [rig key, default Manny_Rig]

The animator: «камеру всегда держать в паренте главного контроллера ... управление камерой через
специальный контроллер камеры который уже будет иметь возможность смены парентов ... корректно
переносит и сохраняет анимации камеры через контроллер во всех случаях, когда риг обычный и когда
он засетаплен как 1p. Для кости Root ... отдельный контроллер в паренте главного».

A. Add Character: the Root control under Main, the root bone following it; moving it moves the
   root and not the camera; Main moves both.
B. The retarget (carry_helpers) sets the camera up: its control under Main, keyed; the camera
   under it, unkeyed and locked; camera_root following the camera.
C. A camera motion of its own keyed on the control (no clip moves camera_root, trap 83); then
   every parent switch Main -> Root -> World -> Main keeps camera_root's world track; Chest is
   refused with no 1P Setup; one undo a switch.
D. Camera Setup pressed again (the button's teardown): the bone baked back, nothing of the
   camera left; pressed once more: a new control under Main on the same track.
E. 1P Setup on a rig whose camera was torn down: a camera set up and its control under the chest;
   the track kept; Upper muted, the camera rides the steadied chest; switched to Main and back to
   Chest from the 1P rig: the track kept; the chest baked off: the control back under Main.
F. A Pose Library pose card of the whole body onto the rig: the camera's CONTROL keyed, camera_root
   on the card's place.
G. A bare Manny skeleton: Camera Setup puts the control in its character group (World); Main is
   refused; delete character takes the control.
"""

import math
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

from maya_scenesetup import catalog, character, camera, rootcontrol, window  # noqa: E402
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


def parent_of(n):
    p = cmds.listRelatives(n, parent=True, fullPath=True)
    return p[0] if p else None


cmds.file(new=True, force=True)
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)
character.add_character(catalog.character_by_key(RIG_KEY))
rig = maya_rigs.rigs()[0]
N = lambda leaf: cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]  # noqa: E731
MAIN, ROOT = N("Main"), N("root")

# ---------------------------------------------------------------------- A
rc = rootcontrol.find(rig)
con = cmds.listRelatives(ROOT, children=True, type="parentConstraint", fullPath=True) or []
gate(bool(rc) and parent_of(rc) == MAIN and con
     and [cmds.ls(t, long=True)[0] for t in cmds.parentConstraint(con[0], q=True,
                                                                  targetList=True)] == [rc]
     and rc in (cmds.ls(cmds.sets(rig.control_set, q=True), long=True) or []),
     "A: Root_ctrl under Main, in the ControlSet, the root follows it")
r0 = wm(ROOT)
cmds.setAttr(rc + ".translateX", 10)
d, _ = apart(wm(ROOT) * r0.inverse(), om.MMatrix())
gate(abs(wm(ROOT)[12] - r0[12] - 10) < 1e-4, "A: Root_ctrl +10 moves the root 10 (%.4f)"
     % (wm(ROOT)[12] - r0[12]))
cmds.setAttr(rc + ".translateX", 0)
gate(apart(wm(ROOT), r0)[0] < 1e-6, "A: back to rest")
gate(rootcontrol.ensure(rig)[0] == rc and len([c for c in cmds.listRelatives(
    MAIN, children=True, type="transform") or [] if "Root_ctrl" in c]) == 1,
    "A: ensure is idempotent")

# ---------------------------------------------------------------------- B
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
cmds.select(MAIN, src)
ok, rtext = rr.run_retarget()
cmds.namespace(removeNamespace="clip", deleteNamespaceContent=True)
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
gate(ok, "B: clip retargeted (%d..%d)" % (first, last))
frames = list(range(first, last + 1, 3))
BONE = N("camera_root")
cam = camera.camera_for(BONE)
ctrl = camera.control_of(cam)
gate(bool(cam) and bool(ctrl) and parent_of(ctrl) == MAIN and camera.parent_choice(ctrl) == "Main"
     and bool(cmds.keyframe(ctrl, query=True)) and not cmds.keyframe(cam, query=True)
     and cmds.getAttr(cam + ".translateX", lock=True),
     "B: retarget's camera: %s under Main, keyed; the camera under it unkeyed, locked"
     % (ctrl or "").split("|")[-1])
offs = []
for f in frames:
    cmds.currentTime(f)
    offs.append(wm(BONE) * wm(cam).inverse())
gate(max(apart(offs[0], o)[0] for o in offs) < 1e-3, "B: camera_root follows the camera")
gate(apart(wm(ctrl), wm(BONE))[0] < 1e-3, "B: the control stands on camera_root")

# ---------------------------------------------------------------------- C
for f in range(first, last + 1, 3):     # a camera motion of its own (trap 83)
    for ch, amp in (("translateY", 6.0), ("rotateX", 12.0), ("translateX", 4.0)):
        v = cmds.keyframe(ctrl, attribute=ch, query=True, eval=True, time=(f, f))[0]
        cmds.setKeyframe(ctrl, attribute=ch, time=f, value=v + amp * math.sin(f * 0.4))
def cam_track():
    c = camera.camera_for(BONE)
    out = track([BONE, c], frames)
    return dict((fr, {"bone": v[BONE], "cam": v[c]}) for fr, v in out.items())


raw2 = cam_track()
raw = track([BONE], frames)
for choice in ("Root", "World", "Main"):
    line = camera.set_parent(BONE, choice)
    ctrl = camera.control_for(BONE)
    target = {"Root": rc, "World": maya_rigs.group_of(MAIN) if hasattr(maya_rigs, "group_of")
              else rig.character, "Main": MAIN}[choice]
    cm, deg = worst(raw2, cam_track())
    gate(camera.parent_choice(ctrl) == choice and parent_of(ctrl) == (target or rig.character)
         and cm < 0.01 and deg < 0.01,
         "C: %s - under %s, camera_root track kept (%.4f cm, %.4f deg)"
         % (line, (parent_of(ctrl) or "").split("|")[-1], cm, deg))
line = camera.set_parent(BONE, "Root")
cmds.undo()
gate(parent_of(camera.control_for(BONE)) == MAIN, "C: one undo puts a switch back")
chest_line = camera.set_parent(BONE, "Chest")
gate("no 1P Setup" in chest_line, "C: Chest refused without 1P Setup: %s" % chest_line)
cm, deg = worst(raw2, cam_track())
gate(cm < 0.01 and deg < 0.01, "C: track still kept (%.4f cm)" % cm)
#  Root_ctrl moved: the root moves, the camera does not (it lives under Main)
cmds.currentTime(first)
cam = camera.camera_for(BONE)
c0, b0 = wm(cam), wm(ROOT)
cmds.setAttr(rc + ".translateZ", 25)
moved = sum((wm(ROOT)[12 + i] - b0[12 + i]) ** 2 for i in range(3)) ** 0.5
gate(apart(wm(cam), c0)[0] < 1e-4 and abs(moved - 25) < 1e-3,
     "C: Root_ctrl +25 moves the root, not the camera")
cmds.setAttr(rc + ".translateZ", 0)

# ---------------------------------------------------------------------- D
start, end = first, last
window_bone = BONE
camera.teardown(BONE, start, end)
gate(not camera.camera_for(BONE) and not cmds.ls("*Camera_ctrl*", recursive=True)
     and not cmds.ls("*SceneSetup_camera*", recursive=True, type="transform"),
     "D: teardown leaves no camera, no control")
cm, deg = worst(raw, track([BONE], frames), [BONE])
gate(cm < 0.01 and deg < 0.01, "D: the bone baked back on its track (%.4f cm)" % cm)
camera.setup(BONE, start, end)
ctrl = camera.control_for(BONE)
cam = camera.camera_for(BONE)
cm, deg = worst(raw, track([BONE], frames), [BONE])
gate(parent_of(ctrl) == MAIN and cm < 0.01 and deg < 0.01,
     "D: set up again: under Main, the same track (%.4f cm)" % cm)
camera.teardown(BONE, start, end)       # E starts with no camera

# ---------------------------------------------------------------------- E
cmds.currentTime(first + 5)
cmds.select(N("FKElbow_R"))
line = fp.setup()
print("   ", line)
for _l in fp.setup_layers(rig.namespace):      # stabilized by default: the take with both on
    cmds.setAttr(_l + ".mute", 0)
chest = fp.chest_of(rig)
ctrl = camera.control_for(BONE)
cam = camera.camera_for(BONE)
gate(bool(chest) and bool(ctrl) and parent_of(ctrl) == chest
     and camera.parent_choice(ctrl) == "Chest",
     "E: 1P Setup made a camera, its control under %s" % (chest or "").split("|")[-1])
cm, deg = worst(raw, track([BONE], frames), [BONE])
gate(cm < 0.01 and deg < 0.01, "E: camera_root's track kept through 1P Setup (%.4f cm, %.4f deg)"
     % (cm, deg))
upper = [l for l in fp.setup_layers(rig.namespace) if l.startswith(fp.UPPER)][0]
lower = [l for l in fp.setup_layers(rig.namespace) if l.startswith(fp.LOWER)][0]
cmds.setAttr(upper + ".mute", 1)
rel = []
for f in frames:
    cmds.currentTime(f)
    rel.append(wm(cam) * wm(chest).inverse())
raw_rel = []
cmds.setAttr(upper + ".mute", 0)
for f in frames:
    cmds.currentTime(f)
    raw_rel.append(wm(cam) * wm(chest).inverse())
gate(max(apart(a, b)[0] for a, b in zip(rel, raw_rel)) < 1e-3,
     "E: Upper muted: the camera keeps its motion relative to the chest")
for choice in ("Main", "Chest"):
    line = camera.set_parent(BONE, choice)
    ctrl = camera.control_for(BONE)
    cm, deg = worst(raw, track([BONE], frames), [BONE])
    gate(camera.parent_choice(ctrl) == choice and cm < 0.01 and deg < 0.01,
         "E: on the 1P rig %s (%.4f cm, %.4f deg)" % (line, cm, deg))
line = fp.camera_parent("Root", [N("FKElbow_R")])
cm, deg = worst(raw, track([BONE], frames), [BONE])
gate("follows Root" in line and cm < 0.01, "E: the card's press: %s" % line)
fp.camera_parent("Chest", [N("FKElbow_R")])
knots.bake([chest])
ctrl = camera.control_for(BONE)
cm, deg = worst(raw, track([BONE], frames), [BONE])
gate(not fp.chest_of(rig) and parent_of(ctrl) == MAIN and camera.parent_choice(ctrl) == "Main"
     and cm < 0.02 and deg < 0.05,
     "E: the chest baked off: the control back under Main, track kept (%.4f cm, %.4f deg)"
     % (cm, deg))

# ---------------------------------------------------------------------- F
from maya_poselib import helpers  # noqa: E402
gate(helpers._camera_of(BONE) == camera.control_for(BONE)
     and helpers._camera_carrier(camera.control_for(BONE)) == "root",
     "F: the Pose Library keys the camera's control, carried by the root")

# ---------------------------------------------------------------------- G
character.add_character(catalog.character_by_key("Manny"))
roots = [r for r in cmds.ls(type="joint", long=True) if r.split("|")[-1] == "camera_root"
         and ":" not in r.split("|")[-1]]
sk_bone = roots[0] if roots else None
if sk_bone:
    camera.setup(sk_bone, first, last)
    sctrl = camera.control_for(sk_bone)
    from maya_scenesetup import chargroup
    gate(bool(sctrl) and parent_of(sctrl) == chargroup.group_of(sk_bone)
         and camera.parent_choice(sctrl) == "World",
         "G: a skeleton's camera control in its character group (World): %s"
         % parent_of(sctrl))
    refusal = camera.set_parent(sk_bone, "Main")
    gate("no rig" in refusal, "G: Main refused on a skeleton: %s" % refusal)
    from maya_scenesetup import deletion
    cmds.select(sk_bone, replace=True)
    print("   ", deletion.delete_selected(confirm=lambda *a, **k: True))
    gate(not cmds.objExists(sctrl), "G: Delete character takes the camera's control")
else:
    gate(False, "G: no skeleton camera_root")

print("%d gates, %d failed" % (COUNT[0], len(FAILS)))
for f in FAILS:
    print("  FAIL:", f)
