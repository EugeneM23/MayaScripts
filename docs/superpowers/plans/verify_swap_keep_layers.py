"""Verify: a rig swapped for another keeps its layers, or bakes them (2026-10-29). mayapy
standalone - it adds and deletes characters, so never the animator's scene.

    mayapy verify_swap_keep_layers.py [clip.FBX] [out.txt] [phases]

`phases` is a comma-separated subset of keep,bake,cancel,weight,quaternion,none,first_person,
other_model (default: all of them).

keep         a Manny rig playing a UE clip with a correction layer «Fix» on FKSpine3_M (keyed on
             3 frames, one of them stepped), swapped for a Manny rig with Keep: the new rig
             carries a layer of the same name, mode and weight, its keys stand on exactly those
             3 frames, the stepped key is stepped, and at the keys the game bones are where the
             old rig's were - with the layer on AND with it muted.
bake         the same scene with Bake: no layer on the new rig, a key on every frame, the bones
             where the old rig showed them.
cancel       the same scene Cancelled: nothing changed, the old rig still standing with its
             layer.
weight       a layer at weight 0.5 and an OVERRIDE layer, each showing on the new rig what it
             showed on the old one.
quaternion   an additive layer accumulating rotation as quaternions: folded, named in the line,
             and the whole take still right at the keys.
none         a rig with no layer at all: never asked, today's road.
first_person a rig through Tools > 1P Setup, swapped with Keep: the new rig in 1P (both layers
             marked with its namespace, the chest control, the camera under it, the display
             layers, Main.view 1), its bones under both layers where the old rig's 3P take put
             them and, with the upper layer muted, where the old rig's 1P look was.
other_model  a Manny rig with a layer swapped for a CREEP rig with Keep: the layer carried, the
             bones pointing as the old rig's at the keys with the layer on and muted.
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
for _p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(_p, quiet=True)
    except Exception:
        pass

ARGS = [a for a in sys.argv[1:]]
CLIP = (ARGS.pop(0) if ARGS and ARGS[0].lower().endswith((".fbx", ".ma", ".mb"))
        else "C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX")
OUT = ARGS.pop(0) if ARGS and ARGS[0].lower().endswith(".txt") else None
ALL = ("keep", "bake", "cancel", "weight", "quaternion", "none", "first_person", "other_model",
       "skeleton")
PHASES = [p.strip() for p in ARGS.pop(0).split(",")] if ARGS else list(ALL)

import maya_retargetmode as rm
import maya_rigs
from maya_poselib import keys as pkeys
from maya_scenesetup import catalog, character, swap, swaplayers
from maya_tools import firstperson
from maya_uebridge import skeletonimport

print("plugin:", os.path.dirname(swap.__file__))
print("clip:  ", CLIP)
FAILS, GATES = [], []
ASKED, ANSWER = [], [swaplayers.KEEP]
LOG = open(OUT, "w") if OUT else None


def say(text):
    print(text)
    sys.stdout.flush()
    if LOG:
        LOG.write(text + "\n")
        LOG.flush()


def gate(n, ok, msg):
    GATES.append(n)
    say("%s gate %s: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def answerer(text):
    ASKED.append(text)
    return ANSWER[0]


swaplayers.set_asker(answerer)
rm.set_asker(lambda text: rm.KEEP)
rm.set_setting(rm.AUTO)

SKIP = ("ik_", "camera_", "center_of_mass", "interaction", "weapon_")


def leaf(p):
    return p.split("|")[-1].split(":")[-1]


def by_leaf(root):
    js = [root] + (cmds.listRelatives(root, ad=True, type="joint", fullPath=True) or [])
    return dict((leaf(j), j) for j in js)


def bones(root):
    return dict((k, v) for k, v in by_leaf(root).items() if not k.startswith(SKIP))


def world(n):
    return om.MMatrix(cmds.xform(n, q=True, ws=True, m=True))


def pos(m):
    return om.MVector(m[12], m[13], m[14])


def quat(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def ang(a, b):
    q = a.inverse() * b
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def sample(nodes, frames):
    out = {}
    for f in frames:
        cmds.currentTime(f)
        for name, path in nodes.items():
            out[(f, name)] = world(path)
    return out


def compare(before, after):
    """(worst cm, worst deg, where): the limb bones' roll left out - AdvancedSkeleton spreads it
    into the twist joints, which this never asks about."""
    worst_d, worst_a, at, at_a = 0.0, 0.0, "", ""
    for key, m in before.items():
        if key not in after or "_twist_" in key[1]:
            continue
        roll_free = key[1].startswith(("upperarm_", "lowerarm_", "thigh_", "calf_"))
        d = (pos(m) - pos(after[key])).length()
        a = ang(quat(m), quat(after[key]))
        if d > worst_d:
            worst_d, at = d, key
        if not roll_free and a > worst_a:
            worst_a, at_a = a, key
    return worst_d, worst_a, "%s / %s" % (at, at_a if worst_a else "")


def muted(names, fn):
    """`fn()` with `names` muted, the mutes put back."""
    saved = swaplayers.mutes_of(names)
    try:
        swaplayers.set_mutes(names, [n for n in saved if n not in names])
        return fn()
    finally:
        swaplayers.restore_mutes(saved)


def import_clip(path, ns):
    before = set(cmds.ls(type="joint", long=True))
    cmds.namespace(add=ns)
    cmds.namespace(set=":" + ns)
    mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
    mel.eval('FBXImport -f "%s";' % path.replace("\\", "/"))
    cmds.namespace(set=":")
    new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
    return min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
               key=lambda j: j.count("|"))


def add_rig(model="Manny"):
    before = maya_rigs.rigs()
    character.add_character(catalog.character_for(model, "rig"))
    fresh = [r for r in maya_rigs.rigs() if r not in before]
    return fresh[0] if fresh else None


def retargeted_rig(model="Manny"):
    """A rig of `model` playing the clip, its take baked onto the base layer. (rig, start, end)."""
    rig = add_rig(model)
    clip = import_clip(CLIP, "clip")
    joints = list(by_leaf(clip).values())
    s0 = cmds.findKeyframe(joints, which="first")
    s1 = cmds.findKeyframe(joints, which="last")
    cmds.playbackOptions(min=s0, max=s1, animationStartTime=s0, animationEndTime=s1)
    import maya_rig_retarget
    maya_rig_retarget.connect(source_root=clip, rig=rig)
    maya_rig_retarget.bake(rig=rig)
    cmds.namespace(removeNamespace=":clip", deleteNamespaceContent=True)
    return maya_rigs.find(rig.namespace) or rig, s0, s1


def control(rig, name):
    return cmds.ls(maya_rigs.node(rig, name), long=True)[0]


def make_layer(name, plug, times, offset, **kwargs):
    """An animation layer holding `plug` keyed `offset` off what it shows, stepped at the
    middle key."""
    layer = cmds.animLayer(name, **kwargs)
    for attr, value in (("rotationAccumulationMode", 0), ("scaleAccumulationMode", 1)):
        cmds.setAttr(layer + "." + attr, value)
    cmds.animLayer(layer, edit=True, attribute=plug)
    for i, t in enumerate(times):
        cmds.setKeyframe(plug, time=t, animLayer=layer,
                         value=cmds.getAttr(plug, time=t) + offset)
        if i == 1:
            curve = pkeys.curve_for(plug, layer)
            if curve:
                cmds.keyTangent(curve, time=(t, t), outTangentType="step")
    return layer


def frames_of(s0, s1, n=5):
    return [float(round(s0 + (s1 - s0) * i / float(n - 1))) for i in range(n)]


def swap_for(rig, model="Manny", kind="rig"):
    ASKED[:] = []
    text = swap.swap(catalog.character_for(model, kind), rig.skeleton_root)
    say("    " + text)
    return text


def newest_rig(old_namespace):
    found = [r for r in maya_rigs.rigs() if r.namespace != old_namespace]
    return found[-1] if found else None


# ---------------------------------------------------------------- keep / other_model
def phase_keep(tag="A", tol_cm=0.35, tol_deg=0.6):
    """A TWIN swap (Manny for Manny), where the new rig's bones can be compared with the old
    rig's directly - another body keeps its own proportions and is `phase_other_model`."""
    cmds.file(new=True, force=True)
    rig, s0, s1 = retargeted_rig()
    chest = control(rig, "FKSpine3_M")
    at = [float(s0), float(round((s0 + s1) / 2.0)), float(s1)]
    layer = make_layer("Fix", chest + ".rotateY", at, 20.0)
    frames = sorted(set(at))
    old = bones(rig.skeleton_root)
    on = sample(old, frames)
    off = muted(["Fix"], lambda: sample(old, frames))
    ANSWER[0] = swaplayers.KEEP
    text = swap_for(rig)
    gate(tag + "1", len(ASKED) == 1 and "Fix" in ASKED[0],
         "asked once, naming the layer (%d questions)" % len(ASKED))
    new = newest_rig(rig.namespace)
    gate(tag + "2", new is not None, "the new rig stands: %s" % (new.namespace if new else None))
    if new is None:
        return
    made = [n for n in pkeys.layer_stack()[1:] if leaf(n).startswith("Fix")]
    gate(tag + "3", made == ["Fix"],
         "one layer, named Fix as the old rig's was: %s" % made)
    gate(tag + "4", swaplayers.KEPT.split(":")[0] in text and "Fix" in text,
         "the line says the layer was kept")
    if not made:
        return
    name = made[0]
    plugs = sorted(pkeys.layer_plugs(name))
    curves = [c for c in (pkeys.curve_for(p, name) for p in plugs) if c]
    times = sorted(set(round(t, 4) for c in curves
                       for t in (cmds.keyframe(c, q=True, timeChange=True) or [])))
    gate(tag + "5", times == [round(t, 4) for t in at],
         "its keys stand on exactly %s: %s" % (at, times))
    steps = [c for c in curves
             if "step" in (cmds.keyTangent(c, q=True, time=(at[1], at[1]),
                                           outTangentType=True) or [""])]
    gate(tag + "6", bool(steps), "the stepped key came out stepped (%d of %d curves)"
         % (len(steps), len(curves)))
    record = pkeys.layer_record(name)
    gate(tag + "7", not record["override"] and abs(record["weight"] - 1.0) < 1e-6
         and not record["mute"], "its mode, weight and mute are the old layer's: %s" % record)
    fresh = bones(new.skeleton_root)
    d, a, where = compare(on, sample(fresh, frames))
    gate(tag + "8", d < tol_cm and a < tol_deg,
         "with the layer on, the bones are where the old rig's were at the keys: "
         "%.4f cm, %.4f deg %s" % (d, a, where))
    d2, a2, where2 = compare(off, muted([name], lambda: sample(fresh, frames)))
    gate(tag + "9", d2 < tol_cm and a2 < tol_deg,
         "with the layer muted, they are where muting it on the old rig put them: "
         "%.4f cm, %.4f deg %s" % (d2, a2, where2))


# ---------------------------------------------------------------- bake
def phase_bake():
    cmds.file(new=True, force=True)
    rig, s0, s1 = retargeted_rig()
    chest = control(rig, "FKSpine3_M")
    at = [float(s0), float(round((s0 + s1) / 2.0)), float(s1)]
    make_layer("Fix", chest + ".rotateY", at, 20.0)
    frames = frames_of(s0, s1)
    old = bones(rig.skeleton_root)
    on = sample(old, frames)
    ANSWER[0] = swaplayers.BAKE
    swap_for(rig)
    new = newest_rig(rig.namespace)
    gate("B1", new is not None, "the new rig stands")
    if new is None:
        return
    gate("B2", not [n for n in pkeys.layer_stack()[1:] if leaf(n).startswith("Fix")],
         "no layer of the old stack on it: %s" % pkeys.layer_stack()[1:])
    d, a, where = compare(on, sample(bones(new.skeleton_root), frames))
    gate("B3", d < 0.35 and a < 0.6,
         "the bones are where the old rig showed them on every sampled frame: "
         "%.4f cm, %.4f deg %s" % (d, a, where))
    spine = control(new, "FKSpine3_M") + ".rotateY"
    count = cmds.keyframe(spine, q=True, keyframeCount=True) or 0
    gate("B4", count >= (s1 - s0), "a key on every frame: %d over %d frames"
         % (count, int(s1 - s0) + 1))


# ---------------------------------------------------------------- cancel
def phase_cancel():
    cmds.file(new=True, force=True)
    rig, s0, s1 = retargeted_rig()
    chest = control(rig, "FKSpine3_M")
    at = [float(s0), float(round((s0 + s1) / 2.0)), float(s1)]
    make_layer("Fix", chest + ".rotateY", at, 20.0)
    frames = frames_of(s0, s1)
    old = bones(rig.skeleton_root)
    before = sample(old, frames)
    rigs_before = len(maya_rigs.rigs())
    nodes_before = len(cmds.ls())
    ANSWER[0] = swaplayers.CANCEL
    text = swap_for(rig)
    gate("C1", text == swap.CANCELLED, "the press says it changed nothing: %r" % text)
    gate("C2", len(maya_rigs.rigs()) == rigs_before and len(cmds.ls()) == nodes_before,
         "no rig added or node made (%d rigs, %d nodes)"
         % (len(maya_rigs.rigs()), len(cmds.ls())))
    gate("C3", cmds.objExists(rig.skeleton_root), "the old rig still stands")
    gate("C4", bool([n for n in pkeys.layer_stack()[1:] if leaf(n).startswith("Fix")]),
         "its layer is still there")
    d, a, _where = compare(before, sample(bones(rig.skeleton_root), frames))
    #  sampling the same scene twice differs in the last digits (the rig's own evaluation), so
    #  "untouched" is measured at a scale a thousand times under anything visible.
    gate("C5", d < 1e-4 and a < 1e-4, "its take is untouched: %.9f cm, %.9f deg" % (d, a))


# ---------------------------------------------------------------- weight / override
def phase_weight():
    cmds.file(new=True, force=True)
    rig, s0, s1 = retargeted_rig()
    chest = control(rig, "FKSpine3_M")
    neck = control(rig, "FKNeck_M")
    at = [float(s0), float(round((s0 + s1) / 2.0)), float(s1)]
    half = make_layer("Half", chest + ".rotateY", at, 20.0)
    cmds.animLayer(half, edit=True, weight=0.5)
    make_layer("Over", neck + ".rotateZ", at, 10.0, override=True)
    frames = sorted(set(at))
    old = bones(rig.skeleton_root)
    on = sample(old, frames)
    ANSWER[0] = swaplayers.KEEP
    swap_for(rig)
    new = newest_rig(rig.namespace)
    gate("W1", new is not None, "the new rig stands")
    if new is None:
        return
    names = dict((leaf(n)[:4], n) for n in pkeys.layer_stack()[1:])
    gate("W2", names.get("Half") == "Half" and names.get("Over") == "Over",
         "both layers made, under their own names: %s" % sorted(names.values()))
    if "Half" in names:
        record = pkeys.layer_record(names["Half"])
        gate("W3", abs(record["weight"] - 0.5) < 1e-6,
             "the weighted layer kept its weight: %.4f" % record["weight"])
    if "Over" in names:
        record = pkeys.layer_record(names["Over"])
        gate("W4", record["override"], "the override layer is an override: %s" % record)
    d, a, where = compare(on, sample(bones(new.skeleton_root), frames))
    gate("W5", d < 0.35 and a < 0.6,
         "both layers show on the new rig what they showed on the old one at the keys: "
         "%.4f cm, %.4f deg %s" % (d, a, where))


# ---------------------------------------------------------------- quaternion
def phase_quaternion():
    """A quaternion layer over a plain one folds into it; alone, the press is never asked and
    the line says why it was baked."""
    cmds.file(new=True, force=True)
    rig, s0, s1 = retargeted_rig()
    chest = control(rig, "FKSpine3_M")
    neck = control(rig, "FKNeck_M")
    at = [float(s0), float(round((s0 + s1) / 2.0)), float(s1)]
    make_layer("Fix", chest + ".rotateY", at, 20.0)
    spin = make_layer("Spin", neck + ".rotateZ", at, 10.0)
    cmds.setAttr(spin + ".rotationAccumulationMode", 1)
    frames = sorted(set(at))
    old = bones(rig.skeleton_root)
    on = sample(old, frames)
    ANSWER[0] = swaplayers.KEEP
    swap_for(rig)
    gate("Q1", len(ASKED) == 1 and "Spin cannot be kept on its own" in ASKED[0]
         and "lands on Fix" in ASKED[0],
         "the question says Spin cannot be kept on its own and lands on Fix")
    new = newest_rig(rig.namespace)
    gate("Q2", new is not None, "the new rig stands")
    if new is None:
        return
    standing = [leaf(n) for n in pkeys.layer_stack()[1:]]
    gate("Q3", any(n.startswith("Fix") for n in standing)
         and not any(n.startswith("Spin") for n in standing),
         "Fix was made and Spin was not: %s" % standing)
    d, a, where = compare(on, sample(bones(new.skeleton_root), frames))
    gate("Q4", d < 0.35 and a < 0.6,
         "Spin's motion landed in Fix's layer at the keys: %.4f cm, %.4f deg %s"
         % (d, a, where))

    cmds.file(new=True, force=True)
    rig, s0, s1 = retargeted_rig()
    alone = make_layer("Spin", control(rig, "FKSpine3_M") + ".rotateY",
                       [float(s0), float(s1)], 20.0)
    cmds.setAttr(alone + ".rotationAccumulationMode", 1)
    frames = frames_of(s0, s1)
    on = sample(bones(rig.skeleton_root), frames)
    ANSWER[0] = swaplayers.CANCEL          # a question here would cancel the press
    text = swap_for(rig)
    gate("Q5", not ASKED, "a stack nothing can be kept from is not asked (%d questions)"
         % len(ASKED))
    gate("Q6", swaplayers.NOT_KEPT % ("Spin", "it accumulates rotation as quaternions") in text,
         "the line says why it was baked: %r" % text[-120:])
    new = newest_rig(rig.namespace)
    if new is None:
        gate("Q7", False, "the new rig stands")
        return
    d, a, where = compare(on, sample(bones(new.skeleton_root), frames))
    gate("Q7", d < 0.35 and a < 0.6,
         "the take came across whole: %.4f cm, %.4f deg %s" % (d, a, where))


# ---------------------------------------------------------------- no layers
def phase_none():
    cmds.file(new=True, force=True)
    rig, s0, s1 = retargeted_rig()
    frames = frames_of(s0, s1)
    on = sample(bones(rig.skeleton_root), frames)
    ANSWER[0] = swaplayers.CANCEL          # a question here would cancel the press
    swap_for(rig)
    gate("N1", not ASKED, "a character with no layer is never asked (%d questions)" % len(ASKED))
    new = newest_rig(rig.namespace)
    gate("N2", new is not None, "the new rig stands")
    if new is None:
        return
    d, a, where = compare(on, sample(bones(new.skeleton_root), frames))
    gate("N3", d < 0.35 and a < 0.6, "today's road: %.4f cm, %.4f deg %s" % (d, a, where))


# ---------------------------------------------------------------- 1P
def phase_first_person():
    cmds.file(new=True, force=True)
    rig, s0, s1 = retargeted_rig()
    say("    " + firstperson.setup(selection=[rig.main]))
    rig = maya_rigs.find(rig.namespace) or rig
    upper = [n for n in firstperson.setup_layers(rig.namespace) if "Upper" in n]
    frames = frames_of(s0, s1)
    old = bones(rig.skeleton_root)
    three_p = muted([], lambda: sample(old, frames))        # as it stands: Upper muted
    every = firstperson.setup_layers(rig.namespace)
    saved = swaplayers.mutes_of(every)
    swaplayers.set_mutes(every, every)                      # every layer on: the 3P take
    whole = sample(old, frames)
    swaplayers.restore_mutes(saved)
    gate("P0", bool(upper) and len(every) == 2,
         "the old rig is in 1P: %s (upper muted: %s)" % (every, saved))
    ANSWER[0] = swaplayers.KEEP
    text = swap_for(rig)
    gate("P1", len(ASKED) == 1 and "1P Setup is run again" in ASKED[0],
         "asked once, saying 1P Setup runs again")
    new = newest_rig(rig.namespace)
    gate("P2", new is not None, "the new rig stands")
    if new is None:
        return
    layers = firstperson.setup_layers(new.namespace)
    gate("P3", len(layers) == 2, "it carries both 1P layers, marked with its namespace: %s"
         % layers)
    gate("P4", bool(firstperson.chest_of(new)), "the chest control stands: %s"
         % firstperson.chest_of(new))
    gate("P5", cmds.getAttr(new.main + ".view") == 1, "Main.view is 1P")
    shown = firstperson.display_layers_of(new.namespace)
    gate("P6", len(shown) == 2, "the two display layers stand: %s" % shown)
    gate("P7", swaplayers.SPLIT_AGAIN.split("%")[0].strip() in text,
         "the line says 1P Setup ran again")
    fresh = bones(new.skeleton_root)
    every_new = firstperson.setup_layers(new.namespace)
    saved = swaplayers.mutes_of(every_new)
    swaplayers.set_mutes(every_new, every_new)
    d, a, where = compare(whole, sample(fresh, frames))
    swaplayers.restore_mutes(saved)
    gate("P8", d < 0.6 and a < 1.0,
         "with both layers on, its bones are where the old rig's 3P take put them: "
         "%.4f cm, %.4f deg %s" % (d, a, where))
    d2, a2, where2 = compare(three_p, sample(fresh, frames))
    gate("P9", d2 < 0.6 and a2 < 1.0,
         "as it stands (the upper layer muted), they are where the old rig's 1P look was: "
         "%.4f cm, %.4f deg %s" % (d2, a2, where2))
    camera = firstperson.camera_control(
        [j for k, j in by_leaf(new.skeleton_root).items() if k == "camera_root"][0])
    chest = firstperson.chest_of(new)
    under = bool(camera) and chest and (cmds.ls(camera, long=True)[0] or "").startswith(
        cmds.ls(chest, long=True)[0] + "|")
    gate("P10", under, "the camera control rides the chest: %s" % camera)


# ---------------------------------------------------------------- other model
def phase_other_model():
    """Another body keeps its own proportions, so its bones cannot stand where the old rig's
    stood - what Keep must not change is the RETARGET's answer. The same scene swapped for a
    Creep rig three times: Keep, Bake, and Bake with the layer muted; Keep with the layer on
    must equal Bake, and Keep with it muted must equal the muted Bake."""
    def build():
        cmds.file(new=True, force=True)
        rig, s0, s1 = retargeted_rig()
        at = [float(s0), float(round((s0 + s1) / 2.0)), float(s1)]
        make_layer("Fix", control(rig, "FKSpine3_M") + ".rotateY", at, 20.0)
        return rig, sorted(set(at))

    def fix_layer():
        found = [n for n in pkeys.layer_stack()[1:] if leaf(n).startswith("Fix")]
        return found[0] if found else None

    rig, frames = build()
    ANSWER[0] = swaplayers.KEEP
    text = swap_for(rig, "Creep")
    kept = newest_rig(rig.namespace)
    gate("M1", kept is not None and len(ASKED) == 1 and "Fix" in ASKED[0],
         "asked once, naming the layer, and the Creep stands: %s"
         % (kept.namespace if kept else None))
    if kept is None:
        return
    gate("M2", fix_layer() == "Fix" and swaplayers.KEPT.split(":")[0] in text,
         "a layer named Fix, as the old rig's was, on the Creep: %s" % fix_layer())
    on_keep = sample(bones(kept.skeleton_root), frames)
    off_keep = muted([fix_layer()], lambda: sample(bones(kept.skeleton_root), frames))

    rig, frames = build()
    ANSWER[0] = swaplayers.BAKE
    swap_for(rig, "Creep")
    baked = newest_rig(rig.namespace)
    on_bake = sample(bones(baked.skeleton_root), frames) if baked else {}

    rig, frames = build()
    cmds.animLayer(fix_layer(), edit=True, mute=True)
    ANSWER[0] = swaplayers.BAKE
    swap_for(rig, "Creep")
    flat = newest_rig(rig.namespace)
    off_bake = sample(bones(flat.skeleton_root), frames) if flat else {}

    d, a, where = compare(on_bake, on_keep)
    gate("M3", bool(on_bake) and d < 0.05 and a < 0.05,
         "with the layer on, the Creep is where Bake puts it at the keys: "
         "%.4f cm, %.4f deg %s" % (d, a, where))
    d2, a2, where2 = compare(off_bake, off_keep)
    gate("M4", bool(off_bake) and d2 < 0.05 and a2 < 0.05,
         "with the layer muted, it is where Bake of the muted stack puts it: "
         "%.4f cm, %.4f deg %s" % (d2, a2, where2))
    d3, a3, _w = compare(on_bake, off_bake)
    gate("M5", d3 > 1.0 or a3 > 1.0,
         "a control: the layer does change the take (%.4f cm, %.4f deg between the two bakes)"
         % (d3, a3))


# ---------------------------------------------------------------- onto a skeleton
def phase_skeleton():
    """A rig with a layer swapped for a SKELETON: the cuts go through the bridge's own transfer
    (`skeletonimport._transfer`) instead of a rig retarget, and the layer lands on the joints."""
    cmds.file(new=True, force=True)
    rig, s0, s1 = retargeted_rig()
    at = [float(s0), float(round((s0 + s1) / 2.0)), float(s1)]
    make_layer("Fix", control(rig, "FKSpine3_M") + ".rotateY", at, 20.0)
    frames = sorted(set(at))
    old = bones(rig.skeleton_root)
    on = sample(old, frames)
    off = muted(["Fix"], lambda: sample(old, frames))
    was = cmds.ls(rig.skeleton_root, long=True)[0]        # the old root goes with the swap
    ANSWER[0] = swaplayers.KEEP
    text = swap_for(rig, "Manny", "skeleton")
    gate("S1", len(ASKED) == 1 and "Fix" in ASKED[0], "asked once, naming the layer")
    from maya_scenesetup import deletion
    roots = [c.root for c in deletion.characters()]
    fresh = [r for r in roots if (cmds.ls(r, long=True) or [r])[0] != was]
    gate("S2", len(fresh) == 1 and not maya_rigs.rigs(),
         "a bare skeleton stands and the rig is gone: %s" % fresh)
    if not fresh:
        return
    made = [n for n in pkeys.layer_stack()[1:] if leaf(n).startswith("Fix")]
    gate("S3", made == ["Fix"] and swaplayers.KEPT.split(":")[0] in text,
         "the layer landed on the skeleton under its own name: %s" % made)
    if not made:
        return
    plugs = sorted(pkeys.layer_plugs(made[0]))
    curves = [c for c in (pkeys.curve_for(p, made[0]) for p in plugs) if c]
    times = sorted(set(round(t, 4) for c in curves
                       for t in (cmds.keyframe(c, q=True, timeChange=True) or [])))
    gate("S4", times == [round(t, 4) for t in at],
         "its keys stand on exactly %s: %s" % (at, times))
    joints = bones(fresh[0])
    d, a, where = compare(on, sample(joints, frames))
    gate("S5", d < 0.35 and a < 0.6,
         "with the layer on, the joints are where the rig's bones were at the keys: "
         "%.4f cm, %.4f deg %s" % (d, a, where))
    d2, a2, where2 = compare(off, muted([made[0]], lambda: sample(joints, frames)))
    gate("S6", d2 < 0.35 and a2 < 0.6,
         "with it muted, they are where muting it on the rig put them: %.4f cm, %.4f deg %s"
         % (d2, a2, where2))


# ---------------------------------------------------------------- run
RUN = {"keep": phase_keep, "bake": phase_bake, "cancel": phase_cancel, "weight": phase_weight,
       "quaternion": phase_quaternion, "none": phase_none,
       "first_person": phase_first_person, "other_model": phase_other_model,
       "skeleton": phase_skeleton}

for phase in PHASES:
    if phase not in RUN:
        say("unknown phase %r" % phase)
        continue
    say("---- %s" % phase)
    try:
        RUN[phase]()
    except Exception as error:                               # noqa: BLE001
        import traceback
        traceback.print_exc()
        gate(phase, False, "the phase raised: %s" % error)

say("%d of %d gates failed%s" % (len(FAILS), len(GATES),
                                 (": " + ", ".join(FAILS)) if FAILS else ""))
if LOG:
    LOG.close()
