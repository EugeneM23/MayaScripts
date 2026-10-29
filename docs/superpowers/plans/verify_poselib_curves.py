"""Original curves and layers in animation cards (2026-10-28), end to end, mayapy STANDALONE.

Never in the animator's Maya: it adds rigs and layers and keys them. Run with a scratch
MAYA_APP_DIR:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_poselib_curves.py [out]

Rig A (Manny_Rig) keyed on the base - FKWrist_R rotateZ with a weighted fixed tangent, a breakdown
and cycle post-infinity, Main translateZ - plus an additive layer AddFix (FKWrist_R rotateX) and an
override layer OverHand at weight 0.5 (FKElbow_R rotateY). Saved whole body over 0..30:
  save      the header names BaseAnimation, AddFix, OverHand; the curves keep FKWrist_R and Main;
            the save of the whole rig takes under 2 s;
  same      onto rig B (same scene: AddFix / OverHand exist, same modes): every saved curve equal
            on B's curve of its layer, key for key - time, value, tangent types, angles, weights,
            breakdowns, infinity;
  one       onto rig C, only AddFix picked, Merge at frame 100: C's base untouched, AddFix keyed
            from 100;
  fresh     a new scene, one rig: AddFix and OverHand MADE with the card's mode, weight, mute;
  mode      a scene whose AddFix is an override: a new additive layer made beside it, said;
  undo      one cmds.undo() after the fresh paste: the keys AND the layers it made gone;
  other     a Creep rig in the same press: retargeted, the line says so;
  objects   a locator keyed on the base + AddFix saved as an objects card: pasted per layer.
Every gate prints PASS/FAIL, the run ends SUMMARY x/y.
"""

import io
import os
import sys
import tempfile
import time
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.environ.get("POSELIB_PLUGIN") or
                          os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(_plugin, quiet=True)
cmds.currentUnit(time="ntsc")
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)

import maya_rigs  # noqa: E402
from maya_scenesetup import catalog, character  # noqa: E402
from maya_poselib import animapply, animcapture, curvedata, keys, store  # noqa: E402

OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []
LIBRARY = tempfile.mkdtemp(prefix="skeldar_curves_lib_")


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    if OUT is not None:
        OUT.write(line + "\n")
        OUT.flush()


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, value))


def add_rig(key="Manny_Rig"):
    before = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key(key))
    cmds.select(clear=True)
    return [r for r in maya_rigs.rigs() if r.namespace not in before][0]


def ctrl(rig, leaf):
    return cmds.ls(rig.namespace + ":" + leaf, long=True)[0]


def curve_table(curve):
    """Every key of `curve`: (time, value, in type, out type, in angle, in weight, out angle, out
    weight, breakdown), rounded - and its infinity."""
    times = cmds.keyframe(curve, query=True, timeChange=True) or []
    rows = []
    for t in times:
        span = (t, t)
        value = cmds.keyframe(curve, query=True, time=span, valueChange=True)[0]
        tan = [cmds.keyTangent(curve, query=True, time=span, **{f: True})[0]
               for f in ("inTangentType", "outTangentType", "inAngle", "inWeight", "outAngle",
                         "outWeight")]
        brk = bool(cmds.keyframe(curve, query=True, time=span, breakdown=True))
        rows.append((round(t, 4), round(value, 4), tan[0], tan[1], round(tan[2], 3),
                     round(tan[3], 3), round(tan[4], 3), round(tan[5], 3), brk))
    return rows, (cmds.getAttr(curve + ".preInfinity"), cmds.getAttr(curve + ".postInfinity"))


def save(selection, name, start=0, end=30):
    clip = animcapture.build_clip(selection, start=start, end=end)
    if clip.header is None:
        raise RuntimeError(clip.note)
    path = store.write(LIBRARY, "", name, clip.header, frames=clip.frames, curves=clip.curves)
    header = store.read(path)
    frames = store.read_frames(path) if clip.frames is not None else None
    curves = store.read_curves(path) if clip.curves is not None else None
    return header, frames, curves, clip


def paste(card, selection, **options):
    header, frames, curves, _clip = card
    options.setdefault("paste_as", "curves")
    return animapply.apply(header, frames, selection=selection, options=options, curves=curves)


def same_curves(a, b, layer):
    """Every curve of `a`'s keyed channels on `layer` equal on `b` (key for key, infinity)."""
    bad = []
    for leaf in ("FKWrist_R", "FKElbow_R", "Main"):
        for attr in ("rotateX", "rotateY", "rotateZ", "translateZ"):
            src = keys.curve_for(ctrl(a, leaf) + "." + attr, layer)
            if src is None:
                continue
            dst = keys.curve_for(ctrl(b, leaf) + "." + attr, layer)
            if dst is None or curve_table(src) != curve_table(dst):
                bad.append((leaf, attr, layer))
    return bad


try:
    cmds.playbackOptions(minTime=0, maxTime=120, animationStartTime=0, animationEndTime=120)
    cmds.currentTime(0)
    a, b, c = add_rig(), add_rig(), add_rig()
    wrist, elbow, main = ctrl(a, "FKWrist_R"), ctrl(a, "FKElbow_R"), a.main
    for t, v in ((0, 0.0), (10, 40.0), (20, -10.0), (30, 25.0)):
        cmds.setKeyframe(wrist, attribute="rotateZ", time=t, value=v)
        cmds.setKeyframe(main, attribute="translateZ", time=t, value=t * 5.0)
    rz = keys.curve_for(wrist + ".rotateZ", None)
    cmds.keyTangent(rz, edit=True, weightedTangents=True)
    cmds.keyTangent(rz, edit=True, time=(10, 10), inAngle=15.0, outAngle=-5.0, inWeight=2.0,
                    outWeight=4.0, lock=False, weightLock=False)
    cmds.keyframe(rz, edit=True, time=(20, 20), breakdown=True)
    cmds.setAttr(rz + ".postInfinity", 3)
    add = cmds.animLayer("AddFix")
    cmds.animLayer(add, edit=True, attribute=[wrist + ".rotateX"])
    for t, v in ((0, 0.0), (15, 12.0), (30, 0.0)):
        cmds.setKeyframe(wrist, attribute="rotateX", time=t, value=v, animLayer=add)
    over = cmds.animLayer("OverHand", override=True)
    cmds.animLayer(over, edit=True, weight=0.5, attribute=[elbow + ".rotateY"])
    for t, v in ((0, 30.0), (30, -30.0)):
        cmds.setKeyframe(elbow, attribute="rotateY", time=t, value=v, animLayer=over)

    # ---- save
    began = time.time()
    card = save([main], "Layered")
    took = time.time() - began
    header, _frames, curves, clip = card
    gate("save: the header names the layers", curvedata.layer_names(header) ==
         [curvedata.BASE, "AddFix", "OverHand"], curvedata.layer_names(header))
    names = set(node["name"] for node in curves["nodes"])
    gate("save: the curves keep FKWrist_R and Main", {"FKWrist_R", "Main"} <= names,
         sorted(names)[:8])
    gate("save: the whole rig under 2 s", took < 2.0, "%.2f s" % took)
    say("save line:", clip.note)
    arm = save([wrist], "Arm")
    arm_names = set(node["name"] for node in arm[2]["nodes"])
    gate("save: an arm card keeps the arm's controls, not Main",
         "FKWrist_R" in arm_names and "Main" not in arm_names, sorted(arm_names))

    # ---- same scene, rig B
    ok, line = paste(card, [b.main])
    say("same:", line)
    gate("same: pasted", ok)
    for layer in (cmds.animLayer(query=True, root=True), add, over):
        gate("same: B equals A on %s" % layer, not same_curves(a, b, layer),
             same_curves(a, b, layer))

    # ---- rig C, AddFix only, Merge at 100
    cmds.currentTime(100)
    base_before = keys.curve_for(ctrl(c, "FKWrist_R") + ".rotateZ", None)
    ok, line = paste(card, [c.main], layers=["AddFix"], mode="merge")
    say("one:", line)
    gate("one: C's base untouched", keys.curve_for(ctrl(c, "FKWrist_R") + ".rotateZ",
                                                    cmds.animLayer(query=True, root=True)) == base_before)
    rx = keys.curve_for(ctrl(c, "FKWrist_R") + ".rotateX", add)
    gate("one: AddFix keyed from 100", rx is not None and
         (cmds.keyframe(rx, query=True, timeChange=True) or [None])[0] == 100.0)

    # ---- Insert at 90 on the same layer: the keys from 90 on move the clip's 31 frames later
    cmds.currentTime(90)
    ok, line = paste(card, [c.main], layers=["AddFix"], mode="insert")
    say("insert:", line)
    rx = keys.curve_for(ctrl(c, "FKWrist_R") + ".rotateX", add)
    times = cmds.keyframe(rx, query=True, timeChange=True) or []
    gate("insert: the old 100 moved to 131, the clip keyed from 90",
         131.0 in times and 90.0 in times, times)

    # ---- other model in the same press
    creep = add_rig("Creep_Rig")
    ok, line = paste(card, [b.main, creep.main])
    say("other:", line)
    gate("other: the Creep retargeted and said", "retargeted" in line and "Creep" in line, line)

    # ---- a fresh scene: the layers are made
    cmds.file(new=True, force=True)
    cmds.currentTime(0)
    d = add_rig()
    ok, line = paste(card, [d.main])
    say("fresh:", line)
    layers = keys.layer_stack()
    gate("fresh: AddFix and OverHand made", "AddFix" in layers and "OverHand" in layers, layers)
    gate("fresh: OverHand is an override at 0.5",
         cmds.animLayer("OverHand", query=True, override=True)
         and abs(cmds.animLayer("OverHand", query=True, weight=True) - 0.5) < 1e-6)
    gate("fresh: the line says made", "(made)" in line, line)

    # ---- undo
    cmds.undo()
    gate("undo: the layers made are gone", "AddFix" not in (keys.layer_stack() or []),
         keys.layer_stack())
    gate("undo: the keys are gone", keys.curve_for(ctrl(d, "FKWrist_R") + ".rotateZ", None) is None)

    # ---- a namesake of another mode
    fix = cmds.animLayer("AddFix", override=True)
    ok, line = paste(card, [d.main])
    made = [name for name in keys.layer_stack() if name.startswith("AddFix") and name != fix]
    gate("mode: a new additive AddFix beside the override one", len(made) == 1 and not
         cmds.animLayer(made[0], query=True, override=True), made)

    # ---- objects
    cmds.file(new=True, force=True)
    loc = cmds.spaceLocator(name="prop")[0]
    for t, v in ((0, 0.0), (10, 10.0)):
        cmds.setKeyframe(loc, attribute="translateY", time=t, value=v)
    layer = cmds.animLayer("PropFix")
    cmds.animLayer(layer, edit=True, attribute=[loc + ".translateY"])
    cmds.setKeyframe(loc, attribute="translateY", time=5, value=20.0, animLayer=layer)
    objects = save([loc], "Prop", 0, 10)
    gate("objects: the header names PropFix", "PropFix" in curvedata.layer_names(objects[0]))
    cmds.file(new=True, force=True)
    loc = cmds.spaceLocator(name="prop")[0]
    ok, line = animapply.apply(objects[0], None, selection=[loc],
                               options={"paste_as": "curves"})
    say("objects:", line)
    gate("objects: PropFix made and keyed", "PropFix" in keys.layer_stack() and
         keys.curve_for(cmds.ls(loc, long=True)[0] + ".translateY", "PropFix") is not None, line)
except Exception:                                            # noqa: BLE001
    say(traceback.format_exc())
    RESULTS.append(False)
say("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
maya.standalone.uninitialize()
