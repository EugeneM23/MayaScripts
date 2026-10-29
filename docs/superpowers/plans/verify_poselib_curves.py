"""Original curves and layers in animation cards (2026-10-28), end to end, mayapy STANDALONE.

Never in the animator's Maya: it adds rigs and layers and keys them. Run with a scratch
MAYA_APP_DIR:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_poselib_curves.py [out]

Rig A (Manny_Rig) keyed on the base - FKWrist_R rotateZ with a weighted fixed tangent, a breakdown
and cycle post-infinity, Main translateZ - plus an additive layer AddFix (FKWrist_R rotateX) and an
override layer OverHand at weight 0.5, muted (FKElbow_R rotateY). Saved whole body over 0..30:
  save      the header names BaseAnimation, AddFix, OverHand; the curves keep FKWrist_R and Main;
            the save of the whole rig takes under 2 s; an arm card keeps the arm's controls and
            not Main;
  same      onto rig B (same scene: AddFix / OverHand exist, same modes): every saved curve equal
            on B's curve of its layer, key for key - time, value, tangent types, angles, weights,
            breakdowns, infinity - and at least one curve compared on every layer;
  one       onto rig C, only AddFix picked, Merge at frame 100: every base curve of C's saved
            channels key for key as before, OverHand holds no plug of C, AddFix keyed from 100;
  insert    AddFix again, Insert at 90: C's keys from 90 on moved the clip's 31 frames later;
  other     a Creep rig in the same press: retargeted, said, keys in the paste range on its
            controls, and no AddFix / OverHand plug of the Creep added;
  budget    every ControlSet control of A keyed on the base every 15 frames to 120 (a whole-rig
            take), saved over 5..105 (every curve CUT, the shape-keeping end keys run): the
            spec's «Cost» budget - the curves read, whole rig, three layers, ~100 frames - under
            2 s (the whole save's time printed beside it);
  fresh     a new scene, one rig: AddFix (additive) and OverHand (override, 0.5, muted) MADE, and
            the rig's curves of FKWrist_R / FKElbow_R / Main on every layer key for key the CARD's;
  undo      one cmds.undo() after the fresh paste: the keys AND the layers it made gone;
  mode      a scene whose AddFix is an override: a new additive layer made beside it, the line
            names it;
  range     a fresh rig, Range 10..20 pasted at 50: every pasted key in 50..60, some on each layer;
  objects   a locator keyed on the base + PropFix saved as an objects card: pasted per layer.
Every paste's ok is gated. Every gate prints PASS/FAIL, the run ends SUMMARY x/y.
"""

import io
import os
import shutil
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
INFINITY = {0: "constant", 1: "linear", 3: "cycle", 4: "cycleRelative", 5: "oscillate"}
CHECKED = ("FKWrist_R", "FKElbow_R", "Main")


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    if OUT is not None:
        OUT.write(line + "\n")
        OUT.flush()


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, value))


def new_scene():
    """A new scene at the card's 30 fps (`file -new` drops back to the prefs' rate)."""
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.currentTime(0)


def add_rig(key="Manny_Rig"):
    before = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key(key))
    cmds.select(clear=True)
    return [r for r in maya_rigs.rigs() if r.namespace not in before][0]


def ctrl(rig, leaf):
    return cmds.ls(rig.namespace + ":" + leaf, long=True)[0]


def maybe_ctrl(rig, leaf):
    found = cmds.ls(rig.namespace + ":" + leaf, long=True)
    return found[0] if found else None


def controls(rig):
    """Every transform of the rig's ControlSet."""
    members = cmds.sets(rig.namespace + ":ControlSet", query=True) or []
    return cmds.ls(members, type="transform", long=True) or []


def root():
    return cmds.animLayer(query=True, root=True)


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


def card_table(curve, shift=0.0):
    """A card CURVE as `curve_table` reads a scene curve, its times moved by `shift`."""
    breaks = set(round(t, 4) for t in curve.get("breakdown") or [])
    rows = []
    for t, v, it, ot, ia, iw, oa, ow in curve["keys"]:
        rows.append((round(t + shift, 4), round(v, 4), it, ot, round(ia, 3), round(iw, 3),
                     round(oa, 3), round(ow, 3), round(t, 4) in breaks))
    return rows, (curve.get("pre") or "constant", curve.get("post") or "constant")


def scene_table(curve):
    rows, (pre, post) = curve_table(curve)
    return rows, (INFINITY.get(int(pre), pre), INFINITY.get(int(post), post))


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
    """([(leaf, attr, layer)] differing, curves compared): every curve of `a`'s keyed channels on
    `layer` equal on `b` (key for key, infinity)."""
    bad, count = [], 0
    for leaf in CHECKED:
        for attr in ("rotateX", "rotateY", "rotateZ", "translateZ"):
            src = keys.curve_for(ctrl(a, leaf) + "." + attr, layer)
            if src is None:
                continue
            count += 1
            dst = keys.curve_for(ctrl(b, leaf) + "." + attr, layer)
            if dst is None or curve_table(src) != curve_table(dst):
                bad.append((leaf, attr, layer))
    return bad, count


def card_plugs(curves, rig, leaves=None):
    """[(plug, attr, {card layer: CURVE})] of the card's nodes on `rig` (those it has)."""
    out = []
    for node in curves["nodes"]:
        if leaves is not None and node["name"] not in leaves:
            continue
        path = maybe_ctrl(rig, node["name"])
        if path is None:
            continue
        for attr, per in node["attrs"].items():
            out.append((path + "." + attr, attr, per))
    return out


def base_snapshot(curves, rig):
    """{plug: curve_table or None} of every saved channel's base curve on `rig`."""
    layer = root()
    snap = {}
    for plug, _attr, _per in card_plugs(curves, rig):
        curve = keys.curve_for(plug, layer)
        snap[plug] = curve_table(curve) if curve else None
    return snap


def layer_plugs_of(layer, rig):
    """The plugs of `rig` (by namespace) that `layer` holds."""
    if not cmds.objExists(layer):
        return []
    found = cmds.animLayer(layer, query=True, attribute=True) or []
    prefix = rig.namespace + ":"
    return [p for p in found if p.split("|")[-1].startswith(prefix)]


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
    cmds.animLayer(over, edit=True, mute=True)

    # ---- save
    began = time.time()
    card = save([main], "Layered")
    took = time.time() - began
    header, _frames, curves, clip = card
    gate("save: the whole rig under 2 s", took < 2.0, "%.2f s" % took)
    gate("save: the header names the layers", curvedata.layer_names(header) ==
         [curvedata.BASE, "AddFix", "OverHand"], curvedata.layer_names(header))
    names = set(node["name"] for node in curves["nodes"])
    gate("save: the curves keep FKWrist_R and Main", {"FKWrist_R", "Main"} <= names,
         sorted(names)[:8])
    say("save line:", clip.note)
    arm = save([wrist], "Arm")
    arm_names = set(node["name"] for node in arm[2]["nodes"])
    gate("save: an arm card keeps the arm's controls, not Main",
         "FKWrist_R" in arm_names and "Main" not in arm_names, sorted(arm_names))

    # ---- same scene, rig B
    ok, line = paste(card, [b.main])
    say("same:", line)
    gate("same: pasted", ok)
    for layer in (root(), add, over):
        bad, count = same_curves(a, b, layer)
        gate("same: B equals A on %s" % layer, not bad, bad)
        gate("same: curves compared on %s" % layer, count > 0, count)

    # ---- rig C, AddFix only, Merge at 100
    cmds.currentTime(100)
    before = base_snapshot(curves, c)
    over_c_before = layer_plugs_of(over, c)
    ok, line = paste(card, [c.main], layers=["AddFix"], mode="merge")
    say("one:", line)
    gate("one: pasted", ok)
    after = base_snapshot(curves, c)
    changed = sorted(p.split(":")[-1] for p in before if before[p] != after.get(p))
    gate("one: C's base untouched on every saved channel (%d)" % len(before),
         len(before) > 0 and not changed, changed[:8])
    gate("one: C's wrist rotateX base untouched",
         before.get(ctrl(c, "FKWrist_R") + ".rotateX", "missing") ==
         after.get(ctrl(c, "FKWrist_R") + ".rotateX"),
         after.get(ctrl(c, "FKWrist_R") + ".rotateX"))
    gate("one: OverHand holds no plug of C", not over_c_before and not layer_plugs_of(over, c),
         layer_plugs_of(over, c))
    rx = keys.curve_for(ctrl(c, "FKWrist_R") + ".rotateX", add)
    gate("one: AddFix keyed from 100", rx is not None and
         (cmds.keyframe(rx, query=True, timeChange=True) or [None])[0] == 100.0)

    # ---- Insert at 90 on the same layer: the keys from 90 on move the clip's 31 frames later
    cmds.currentTime(90)
    ok, line = paste(card, [c.main], layers=["AddFix"], mode="insert")
    say("insert:", line)
    gate("insert: pasted", ok)
    rx = keys.curve_for(ctrl(c, "FKWrist_R") + ".rotateX", add)
    times = cmds.keyframe(rx, query=True, timeChange=True) or []
    gate("insert: the old 100 moved to 131, the clip keyed from 90",
         131.0 in times and 90.0 in times, times)

    # ---- other model in the same press
    creep = add_rig("Creep_Rig")
    creep_layers_before = [layer_plugs_of(n, creep) for n in (add, over)]
    cmds.currentTime(0)
    ok, line = paste(card, [b.main, creep.main])
    say("other:", line)
    gate("other: pasted", ok)
    gate("other: the Creep retargeted and said", "retargeted" in line and "Creep" in line, line)
    keyed = []
    for path in controls(creep):
        for attr in ("rotateX", "rotateY", "rotateZ"):
            curve = keys.curve_for(path + "." + attr, root())
            if curve and [t for t in cmds.keyframe(curve, query=True, timeChange=True) or []
                          if 0.0 <= t <= 30.0]:
                keyed.append(path.split(":")[-1] + "." + attr)
    gate("other: Creep controls keyed inside 0..30", len(keyed) > 0, "%d e.g. %s" % (
        len(keyed), keyed[:3]))
    creep_layers_after = [layer_plugs_of(n, creep) for n in (add, over)]
    gate("other: no AddFix / OverHand plug of the Creep added",
         creep_layers_after == creep_layers_before == [[], []], creep_layers_after)

    # ---- the spec's cost budget (design «Cost»): the curves READ of the whole rig, three
    # layers, 100 frames, under 2 s - a whole-rig take on A every 15 frames to 120, saved over
    # 5..105 so every curve is CUT (the shape-keeping end keys run). The save's per-frame bone
    # walk (the frames card, older than the curves) is timed and printed, not budgeted.
    base = root()
    failed = 0
    rig_controls = controls(a)
    for path in rig_controls:
        attrs = [x for x in ("rotateX", "rotateY", "rotateZ")
                 if x in (cmds.listAttr(path, keyable=True, unlocked=True) or [])]
        for t in range(0, 121, 15):
            for attr in attrs:
                try:
                    cmds.setKeyframe(path, attribute=attr, time=t, value=(t % 45) / 5.0 - 4.0,
                                     animLayer=base)
                except RuntimeError:
                    failed += 1
    say("budget: %d controls keyed (%d key failures)" % (len(rig_controls), failed))
    spent = []
    _read = animcapture._character_curves

    def _timed_read(*args, **kwargs):
        began = time.time()
        try:
            return _read(*args, **kwargs)
        finally:
            spent.append(time.time() - began)

    animcapture._character_curves = _timed_read
    try:
        began = time.time()
        take = save([main], "WholeRig", 5, 105)
        took = time.time() - began
    finally:
        animcapture._character_curves = _read
    say("budget: the whole save over 5..105 (101 frames) took %.2f s, of it the curves read "
        "%.2f s" % (took, sum(spent)))
    gate("budget: the curves read of the whole rig, 3 layers, 101 frames under 2 s",
         len(spent) == 1 and spent[0] < 2.0, "%.2f s" % sum(spent))
    gate("budget: the take holds 3 layers", curvedata.layer_names(take[0]) ==
         [curvedata.BASE, "AddFix", "OverHand"], curvedata.layer_names(take[0]))
    gate("budget: the take's curves hold the rig (> 100 nodes)", len(take[2]["nodes"]) > 100,
         len(take[2]["nodes"]))
    cut = [node for node in take[2]["nodes"] if node["name"] == "FKWrist_R"]
    cut_keys = cut and cut[0]["attrs"].get("rotateZ", {}).get(curvedata.BASE, {}).get("keys")
    gate("budget: a cut curve keeps its shape-keeping ends at 5 and 105",
         bool(cut_keys) and cut_keys[0][0] == 5.0 and cut_keys[-1][0] == 105.0,
         [k[0] for k in cut_keys or []])

    # ---- a fresh scene: the layers are made, their keys the card's
    new_scene()
    d = add_rig()
    ok, line = paste(card, [d.main])
    say("fresh:", line)
    gate("fresh: pasted", ok)
    layers = keys.layer_stack()
    gate("fresh: AddFix and OverHand made", "AddFix" in layers and "OverHand" in layers, layers)
    gate("fresh: AddFix is additive", not cmds.animLayer("AddFix", query=True, override=True))
    gate("fresh: OverHand is an override at 0.5",
         cmds.animLayer("OverHand", query=True, override=True)
         and abs(cmds.animLayer("OverHand", query=True, weight=True) - 0.5) < 1e-6)
    gate("fresh: OverHand muted", cmds.animLayer("OverHand", query=True, mute=True))
    gate("fresh: the line says made", "(made)" in line, line)
    compared = dict((name, 0) for name in curvedata.layer_names(header))
    bad = []
    for plug, attr, per in card_plugs(curves, d, CHECKED):
        for layer_name, curve in per.items():
            if not isinstance(curve, dict) or not curve.get("keys"):
                continue
            compared[layer_name] = compared.get(layer_name, 0) + 1
            dst = keys.curve_for(plug, layer_name)
            if dst is None or scene_table(dst) != card_table(curve):
                bad.append((plug.split(":")[-1], layer_name,
                            scene_table(dst) if dst else None, card_table(curve)))
    gate("fresh: the rig's curves key for key the card's", not bad, bad[:2])
    gate("fresh: card curves compared on every layer",
         all(n > 0 for n in compared.values()), compared)

    # ---- undo
    cmds.undo()
    gate("undo: the layers made are gone", "AddFix" not in (keys.layer_stack() or []),
         keys.layer_stack())
    gate("undo: the keys are gone", keys.curve_for(ctrl(d, "FKWrist_R") + ".rotateZ", None) is None)

    # ---- a namesake of another mode
    fix = cmds.animLayer("AddFix", override=True)
    ok, line = paste(card, [d.main])
    say("mode:", line)
    gate("mode: pasted", ok)
    made = [name for name in keys.layer_stack() if name.startswith("AddFix") and name != fix]
    gate("mode: a new additive AddFix beside the override one", len(made) == 1 and not
         cmds.animLayer(made[0], query=True, override=True), made)
    gate("mode: the line names the new layer", len(made) == 1 and made[0] in line, line)

    # ---- Range 10..20 onto a fresh rig, at 50: keys in 50..60 only
    new_scene()
    e = add_rig()
    cmds.currentTime(50)
    ok, line = paste(card, [e.main], start=10, end=20)
    say("range:", line)
    gate("range: pasted", ok)
    per_layer, outside = {}, []
    for plug, attr, per in card_plugs(curves, e):
        for layer_name in per:
            curve = keys.curve_for(plug, layer_name)
            if curve is None:
                continue
            for t in cmds.keyframe(curve, query=True, timeChange=True) or []:
                per_layer[layer_name] = per_layer.get(layer_name, 0) + 1
                if not 50.0 <= t <= 60.0:
                    outside.append((plug.split(":")[-1], layer_name, t))
    gate("range: every pasted key in 50..60", not outside, outside[:4])
    gate("range: keys on every layer", sorted(per_layer) == sorted(curvedata.layer_names(header)),
         per_layer)

    # ---- objects
    new_scene()
    loc = cmds.spaceLocator(name="prop")[0]
    for t, v in ((0, 0.0), (10, 10.0)):
        cmds.setKeyframe(loc, attribute="translateY", time=t, value=v)
    layer = cmds.animLayer("PropFix")
    cmds.animLayer(layer, edit=True, attribute=[loc + ".translateY"])
    cmds.setKeyframe(loc, attribute="translateY", time=5, value=20.0, animLayer=layer)
    objects = save([loc], "Prop", 0, 10)
    gate("objects: the header names PropFix", "PropFix" in curvedata.layer_names(objects[0]))
    new_scene()
    loc = cmds.spaceLocator(name="prop")[0]
    ok, line = animapply.apply(objects[0], None, selection=[loc],
                               options={"paste_as": "curves"})
    say("objects:", line)
    gate("objects: pasted", ok)
    gate("objects: PropFix made and keyed", "PropFix" in keys.layer_stack() and
         keys.curve_for(cmds.ls(loc, long=True)[0] + ".translateY", "PropFix") is not None, line)
except Exception:                                            # noqa: BLE001
    say(traceback.format_exc())
    RESULTS.append(False)
say("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
if OUT is not None:
    OUT.close()
shutil.rmtree(LIBRARY, ignore_errors=True)
maya.standalone.uninitialize()
