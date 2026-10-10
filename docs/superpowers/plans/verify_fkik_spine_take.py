"""The spine FK / IK switch on a REAL take, measured on every frame (2026-10-10).

    mayapy verify_fkik_spine_take.py [clip.fbx] [rig keys, default Manny_Rig,Creep_Rig,Orc_D_Rig]
                                     [step, default 1]

mayapy STANDALONE, an empty scene per rig. The rig added through Add Character, the clip
retargeted onto it through the Retarget button, the source deleted; `step` > 1 then thins every
curve of the rig to keys every `step` frames (a hand-keyed take). The switch is pressed through
the Connections card's own path (`connections.switch_spine`).

Why this verify exists: the first spine switch moved the IK root - the spline's hip control is
the IK root, and the root carries the pelvis and both legs - so every switch to IK put the feet
2 cm off on every frame («ломается анимация»). verify_fkik_spine.py measured the spine alone and
passed. Here everything the animator sees is measured, on every frame:

- FK -> IK: the root, the pelvis and both legs do not move (the game skeleton's joints); the
  spine stands where the FK spine stood; the skinned meshes' vertices stay put;
- IK -> FK: back to the FK take;
- the animator moves the IK hip control (3 cm), then IK -> FK: the root, the pelvis and the
  legs stay where the IK put them (the FK root control follows the IK root).
"""
import math
import os
import sys
import time

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except Exception:
        pass

from maya_scenesetup import character, catalog, fkik, fkikspine  # noqa: E402
from maya_scenesetup import connections as cx  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402

CLIP = (sys.argv[1] if len(sys.argv) > 1 else
        "C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX").replace("\\", "/")
RIGS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["Manny_Rig", "Creep_Rig", "Orc_D_Rig"]
STEP = int(sys.argv[3]) if len(sys.argv) > 3 else 1
MAX_FRAMES = 61
LOWER = ("root", "pelvis", "thigh_l", "calf_l", "foot_l", "ball_l", "thigh_r", "calf_r",
         "foot_r", "ball_r")                       # what the root carries: must not move
SPINE = ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05")
LOWER_CM, LOWER_DEG = 0.01, 0.02
SPINE_CM, SPINE_DEG = 0.06, 0.6                   # the Creep's spline twist: 0.55 deg at one frame
# between the keys of a thinned take each chain interpolates its own way (the keys-only cost,
# 2026-10-08): the spine is held at the keys, between them only within this
BETWEEN_CM, BETWEEN_DEG = 0.5, 2.0
SKIN_CM = 0.5
HIP_NUDGE = 3.0
FAILS = []
COUNT = [0]
RIG_KEY = [""]


def gate(ok, text):
    COUNT[0] += 1
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", COUNT[0], text))
    sys.stdout.flush()
    if not ok:
        FAILS.append((RIG_KEY[0], COUNT[0]))


def pos(m):
    return om.MVector(m[12], m[13], m[14])


def turn(a, b):
    return math.degrees(fkik.rotation_vector(b, a).length())


def world(path):
    return om.MMatrix(cmds.getAttr(path + ".worldMatrix[0]"))


def sample(frames, nodes):
    out = {}
    for f in frames:
        cmds.currentTime(f, update=True)
        out[f] = [world(n) for n in nodes]
    return out


def mesh_points(shape):
    sel = om.MSelectionList()
    sel.add(shape)
    return om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)


def sample_mesh(frames, shapes):
    out = {}
    for f in frames:
        cmds.currentTime(f, update=True)
        out[f] = [mesh_points(s) for s in shapes]
    return out


def worst(before, after, frames):
    """(worst cm, worst deg, frame) over the nodes and frames."""
    cm = deg = 0.0
    at = None
    for f in frames:
        for a, b in zip(before[f], after[f]):
            d = (pos(a) - pos(b)).length()
            if d > cm:
                cm, at = d, f
            deg = max(deg, turn(a, b))
    return cm, deg, at


def worst_skin(before, after, frames):
    out = 0.0
    for f in frames:
        for pa, pb in zip(before[f], after[f]):
            for p, q in zip(pa, pb):
                out = max(out, (om.MVector(p.x, p.y, p.z) - om.MVector(q.x, q.y, q.z)).length())
    return out


def setup(key):
    cmds.file(new=True, force=True)
    text = character.add_character(catalog.character_by_key(key))
    rig = maya_rigs.rigs()[0]
    node = lambda leaf: cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]  # noqa: E731
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
    last = min(last, first + MAX_FRAMES - 1)
    cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
    cmds.select(node("Main"), src)
    ok, rtext = rr.run_retarget()
    cmds.namespace(removeNamespace="clip", deleteNamespaceContent=True)
    cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
    cmds.select(clear=True)
    gate(ok, "%s added, %s retargeted (%d..%d)" % (text.split(" - ")[0], os.path.basename(CLIP),
                                                    first, last))
    if STEP > 1:
        prefix = rig.namespace + ":"
        cut = 0
        for curve in cmds.ls(type="animCurve", long=True) or []:
            plugs = [p for p in (cmds.listConnections(curve + ".output", source=False,
                                                      destination=True, plugs=True) or [])
                     if p.startswith(prefix)]
            times = cmds.keyframe(curve, query=True, timeChange=True) or []
            for plug in plugs:
                for t in times:
                    if (int(t) - first) % STEP and int(t) != last:
                        cmds.cutKey(plug, time=(t, t), clear=True)
                        cut += 1
        print("    thinned every %d frames: %d keys cut" % (STEP, cut))
    frames = list(range(first, last + 1))
    keys = [f for f in frames if STEP <= 1 or (f - first) % STEP == 0 or f == last]
    return rig, node, frames, keys


def skins(rig):
    shapes = []
    for shape in cmds.ls(rig.namespace + ":*", type="mesh", long=True) or []:
        if cmds.listConnections(shape, type="skinCluster", source=True, destination=False):
            shapes.append((len(mesh_points(shape)), shape))
    return [s for _n, s in sorted(shapes, reverse=True)][:2]


def spine_gates(label, before, after, frames, keys):
    """The spine at the keys (strict) and, on a thinned take, between them (loose)."""
    cm, deg, at = worst(before, after, keys)
    gate(cm <= SPINE_CM and deg <= SPINE_DEG,
         "%s: the spine stands where it stood, at the %d keys (%.4f cm, %.3f deg at %s)"
         % (label, len(keys), cm, deg, at))
    between = [f for f in frames if f not in keys]
    if between:
        cm, deg, at = worst(before, after, between)
        gate(cm <= BETWEEN_CM and deg <= BETWEEN_DEG,
             "%s: between the keys each chain interpolates its own way (%.4f cm, %.3f deg at %s)"
             % (label, cm, deg, at))


def run(key):
    RIG_KEY[0] = key
    print("=" * 30, key, "(keys every %d frames)" % STEP if STEP > 1 else "")
    t0 = time.time()
    rig, node, frames, keys = setup(key)
    sp, text = fkikspine.spine(rig)
    gate(sp is not None and fkikspine.state(rig) == fkik.FK, "the spine resolves and is FK (%s)" % text)
    if sp is None:
        return
    lower = [node(j) for j in LOWER]
    spine = [node(j) for j in SPINE]
    meshes = skins(rig)
    fk_lower, fk_spine, fk_skin = sample(frames, lower), sample(frames, spine), \
        sample_mesh(frames, meshes)

    message = cx.switch_spine(fkik.IK, rig=rig)
    print("   ", message)
    gate(fkikspine.state(rig) == fkik.IK and "the root and legs kept" in message,
         "Connections: the spine to IK, the line says the root and the legs were kept")
    ik_lower, ik_spine, ik_skin = sample(frames, lower), sample(frames, spine), \
        sample_mesh(frames, meshes)
    cm, deg, at = worst(fk_lower, ik_lower, frames)
    gate(cm <= LOWER_CM and deg <= LOWER_DEG,
         "FK -> IK: the root, the pelvis and both legs stay, every frame (%.4f cm, %.4f deg at %s)"
         % (cm, deg, at))
    spine_gates("FK -> IK", fk_spine, ik_spine, frames, keys)
    skin = worst_skin(fk_skin, ik_skin, frames)
    gate(skin <= SKIN_CM, "FK -> IK: the skin stays, every frame (worst vertex %.3f cm)" % skin)

    back = cx.switch_spine(fkik.FK, rig=rig)
    print("   ", back)
    bk_lower, bk_spine = sample(frames, lower), sample(frames, spine)
    cm_l, deg_l, at = worst(fk_lower, bk_lower, frames)
    gate(fkikspine.state(rig) == fkik.FK and cm_l <= LOWER_CM and deg_l <= LOWER_DEG,
         "IK -> FK: the root and the legs back on the FK take, every frame (%.4f cm, %.4f deg "
         "at %s)" % (cm_l, deg_l, at))
    gate("FK root put" not in back, "IK -> FK with nothing edited keys no FK root")
    spine_gates("IK -> FK", fk_spine, bk_spine, frames, keys)

    # the animator works in IK: the hip control moved, then the switch back to FK
    cx.switch_spine(fkik.IK, rig=rig)
    hip = node("IKSpine1_M")
    if cmds.keyframe(hip + ".translateX", query=True, keyframeCount=True):
        cmds.keyframe(hip + ".translateX", edit=True, relative=True, valueChange=HIP_NUDGE)
    else:
        cmds.setAttr(hip + ".translateX", cmds.getAttr(hip + ".translateX") + HIP_NUDGE)
    ed_lower, ed_spine = sample(frames, lower), sample(frames, spine)
    moved, _deg, _at = worst(fk_lower, ed_lower, frames)
    gate(moved > 1.0, "the IK hip control moved the root and the legs (%.2f cm) - the edit took"
         % moved)
    after = cx.switch_spine(fkik.FK, rig=rig)
    print("   ", after)
    fk2_lower, fk2_spine = sample(frames, lower), sample(frames, spine)
    cm_l, deg_l, at = worst(ed_lower, fk2_lower, frames)
    gate(cm_l <= LOWER_CM and deg_l <= LOWER_DEG and "FK root put" in after,
         "IK -> FK after an IK hip edit: the FK root follows, the root and the legs stay where "
         "IK put them, every frame (%.4f cm, %.4f deg at %s)" % (cm_l, deg_l, at))
    spine_gates("IK -> FK after the hip edit", ed_spine, fk2_spine, frames, keys)
    print("    %s: %.1f s" % (key, time.time() - t0))


try:
    for rig_key in RIGS:
        run(rig_key)
except Exception as exc:  # noqa: BLE001 - report, do not hide
    import traceback
    traceback.print_exc()
    FAILS.append("exception: %s" % exc)
print("RESULT: %d gates, %d failed %s" % (COUNT[0], len(FAILS), FAILS))
sys.stdout.flush()
os._exit(0 if not FAILS else 1)
