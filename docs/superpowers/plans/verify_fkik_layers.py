"""Connections FK / IK on a rig whose controls ride animation layers, standalone (2026-10-16).

    mayapy verify_fkik_layers.py <UE5 clip .fbx>

Found live: after Tools > 1P Setup every animated control is fed by `_3P_Upper_Body` /
`_3P_Lower_Body`, and every Connections FK / IK press refused - «IKArm_R.translateX is driven
by IKArm_R_translateX__3P_Upper_Body - not a key the switch can rewrite». A layered channel is
keyed with what it must SHOW on the active layer (the Tools' rule: the selected non-base
layer, else BaseAnimation); every other layer keeps its curves.

Manny_Rig, the clip retargeted through the button, 1P Setup pressed, then:
- Arm_R to IK and back, nothing selected in the Layer Editor: the game bones keep what they
  showed (positions of the arm to the switch's tolerance), `_3P_Upper_Body`'s curves untouched;
- Leg_L to IK and back the same, `_3P_Lower_Body` untouched;
- Arm_L to IK with `_3P_Upper_Body` selected: the keys on that layer, the base untouched;
- the Spine to IK and back;
- a locked active layer refused before anything moves;
- one undo takes a press back.
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

from maya_scenesetup import catalog, character, connections, fkik  # noqa: E402
from maya_tools import firstperson as fp  # noqa: E402
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


def layer_curves(layer):
    """{curve: (times, values)} of every curve on `layer`."""
    out = {}
    for node in cmds.animLayer(layer, query=True, animCurves=True) or []:
        out[node] = (tuple(cmds.keyframe(node, query=True, timeChange=True) or ()),
                     tuple(round(v, 6) for v in cmds.keyframe(node, query=True, valueChange=True) or ()))
    return out


def select_layer(layer):
    root = cmds.animLayer(query=True, root=True)
    for name in [root] + (cmds.ls(type="animLayer") or []):
        cmds.animLayer(name, edit=True, selected=(name == layer))


cmds.file(new=True, force=True)
cmds.undoInfo(state=True, infinity=True)
character.add_character(catalog.default_rig())
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
last = min(last, first + 30)
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
cmds.select(N("Main"), src)
ok, rtext = rr.run_retarget()
cmds.namespace(removeNamespace="clip", deleteNamespaceContent=True)
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
gate(ok, "clip retargeted onto %s (%d..%d)" % (rig.namespace, first, last))

cmds.currentTime(first)
cmds.select(N("FKElbow_R"))
print("   ", fp.setup())
made = fp.setup_layers(rig.namespace)
upper = [l for l in made if l.startswith(fp.UPPER)][0]
lower = [l for l in made if l.startswith(fp.LOWER)][0]
gate(bool(upper and lower), "1P Setup made %s / %s" % (upper, lower))
cmds.select(clear=True)
select_layer(None)

frames = list(range(first, last + 1, 3))
arm_r = [N(b) for b in ("upperarm_r", "lowerarm_r", "hand_r")]
arm_l = [N(b) for b in ("upperarm_l", "lowerarm_l", "hand_l")]
leg_l = [N(b) for b in ("thigh_l", "calf_l", "foot_l")]
spine = [N(b) for b in ("pelvis", "spine_01", "spine_03", "spine_05", "head")]
everything = arm_r + arm_l + leg_l + spine + [N("foot_r"), N("hand_r")]
take = track(everything, frames)


def press(label, fn, nodes, tol_cm, layers_kept=(), refused_ok=False):
    kept = dict((l, layer_curves(l)) for l in layers_kept)
    was = track(everything, frames)
    text = fn()
    print("    %s -> %s" % (label, text))
    refused = ("driven by" in text or "refused" in text or "locked" in text or "is already" in text
               or "not found" in text)
    gate(not refused, "%s goes through" % label)
    now = track(everything, frames)
    cm, deg = worst(was, now, nodes)
    # positions: an IK elbow / knee cannot hold the FK roll (said on the line), so turns are not gated
    gate(cm <= tol_cm, "%s: the limb where it was, %.4f cm (roll %.3f deg)" % (label, cm, deg))
    others = [n for n in everything if n not in nodes]
    ocm, odeg = worst(was, now, others)
    gate(ocm <= 1e-3 and odeg <= 1e-2, "%s: the rest of the body unmoved, %.6f cm %.5f deg"
         % (label, ocm, odeg))
    for layer, curves in kept.items():
        gate(layer_curves(layer) == curves, "%s: %s's curves untouched" % (label, layer))
    return text


TOL = 0.06          # the switch's own tolerance for a retargeted arm (FK lengths vs the rig's)
press("Arm_R to IK", lambda: connections.switch_limb("R", fkik.IK, rig=rig, highlight=None),
      arm_r, TOL, layers_kept=(upper, lower))
press("Arm_R back to FK", lambda: connections.switch_limb("R", fkik.FK, rig=rig, highlight=None),
      arm_r, TOL, layers_kept=(upper, lower))
press("Leg_L to IK", lambda: connections.switch_limb("L", fkik.IK, rig=rig, highlight=None, kind=fkik.LEG),
      leg_l, TOL, layers_kept=(upper, lower))
press("Leg_L back to FK", lambda: connections.switch_limb("L", fkik.FK, rig=rig, highlight=None,
                                                          kind=fkik.LEG), leg_l, TOL, layers_kept=(upper, lower))

# the active layer: Upper selected - its keys change, the base's do not
root = cmds.animLayer(query=True, root=True)
base_before = layer_curves(root)
upper_before = layer_curves(upper)
select_layer(upper)
press("Arm_L to IK on the selected layer", lambda: connections.switch_limb("L", fkik.IK, rig=rig,
                                                                             highlight=None),
      arm_l, TOL, layers_kept=(lower,))
gate(layer_curves(root) == base_before, "Arm_L: the base's curves untouched")
gate(layer_curves(upper) != upper_before, "Arm_L: the keys landed on %s" % upper)

# one undo (straight after the press: in mayapy a currentTime is an undo step, trap 222)
upper_before = layer_curves(upper)
connections.switch_limb("R", fkik.IK, rig=rig, highlight=None)
cmds.undo()
after_undo = layer_curves(upper)
diff = [c for c in set(after_undo) | set(upper_before) if after_undo.get(c) != upper_before.get(c)]
gate(not diff and layer_curves(root) == base_before,
     "Arm_R: one undo puts both layers back (%d curves differ: %s)" % (len(diff), sorted(diff)[:4]))
gate(fkik.mode_of(fkik.blend_values(fkik.limb(rig, "R")[0])) == fkik.FK, "Arm_R: FK again after the undo")
select_layer(None)

cmds.animLayer(upper, edit=True, lock=True)
select_layer(upper)
text = connections.switch_limb("R", fkik.IK, rig=rig, highlight=None)
gate("locked" in text, "a locked active layer is refused: %s" % text)
cmds.animLayer(upper, edit=True, lock=False)
select_layer(None)

press("Spine to IK", lambda: connections.switch_spine(fkik.IK, rig=rig, highlight=None),
      spine, 1.0, layers_kept=(upper, lower))
# 1P Setup leaves a Tools knot on FKSpine3_M: FK for the spine is refused, and says why
text = connections.switch_spine(fkik.FK, rig=rig, highlight=None)
gate("Tools knot" in text and "pairBlend" not in text, "Spine back to FK names the knot: %s" % text)

print("%d of %d gates failed" % (len(FAILS), COUNT[0]))
maya.standalone.uninitialize()
sys.exit(1 if FAILS else 0)
