"""Original curves and layers in animation cards, measured on the BONES (2026-10-29), mayapy
STANDALONE. Never in the animator's Maya: it adds rigs, layers and scene tabs. Run with a scratch
MAYA_APP_DIR:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_poselib_curves_layers.py [phase...]

The animator, 2026-10-29: «1 - Если записать анимацию в библиотеку потом удалить персонажа потом
создать нового ... не видно слоев ... 2 - Анимация со слоями не переносится корректно на 1P риг
если она была записана на 3P. 3 - ... если добавить объекты на слой анимационный то потом при
мердже контроллеры рига может выкручивать». Every paste is judged by what the target's skeleton
SHOWS: each bone, relative to the root, against the card's own frames (what the source showed) -
within 0.01 deg / 0.01 cm on every frame of the range. Phases (all by default):

  delete   the card's character deleted (Characters > Delete), a new one added, the card pasted
           with Replace all: AddFix / OverHand made again, holding the new rig, the bones the card's;
  tabs     the same in a scene tabs session: the tab's layer root survives the delete, the current
           namespace stays the tab's, the new rig lands in the tab, the made layers go under the
           tab's root one idle later, the line names BaseAnimation, the bones the card's;
  firstp   a 3P card onto a rig in 1P (Tools > 1P Setup): retargeted and said, the bones the
           card's, Upper still muted; a card saved off a rig in 1P onto a 3P rig: retargeted,
           said, the bones the card's;
  statics  Add Selected Objects on an override layer (its unkeyed channels frozen) and on an
           additive one with a static off zero: the card keeps the statics, a fresh rig shows the
           card;
  others   the target's own keys in a namesake layer and in a layer the card does not have:
           Replace, Replace all and Insert clear them on the card's channels (said), the bones the
           card's; Merge leaves them and says so; with only AddFix picked a layer of the target's
           is untouched;
  pins     a card whose curves end before its range, pasted at 40 into a target keyed to 100:
           the range the card's, a target key after the range untouched;
  undo     one undo after a paste that made layers and cleared one: the layers gone, the cleared
           layer's keys back;
  objects  a prop and the arm in a layer (Add Selected Objects), saved with the rig: onto a fresh
           rig and prop, the bones and the prop's channels the card's.
Every gate prints PASS/FAIL, the run ends SUMMARY x/y.
"""

import math
import os
import shutil
import sys
import tempfile
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

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
from maya_scenesetup import catalog, character, deletion  # noqa: E402
from maya_poselib import animapply, animcapture, animdata, curveapply, curvedata, keys  # noqa
from maya_poselib import store  # noqa: E402

PHASES = [a for a in sys.argv[1:] if not a.startswith("-")] or [
    "delete", "tabs", "firstp", "statics", "others", "pins", "undo", "objects"]
RESULTS = []
LIBRARY = tempfile.mkdtemp(prefix="skeldar_curves_layers_lib_")
WORK = tempfile.mkdtemp(prefix="skeldar_curves_layers_tabs_").replace("\\", "/")
LAST = 30
DEG, CM = 0.01, 0.01
ROT = ("rotateX", "rotateY", "rotateZ")
ARM = ("FKShoulder_R", "FKElbow_R", "FKWrist_R", "FKShoulder_L", "FKElbow_L", "FKWrist_L")
SPINE = ("FKSpine1_M", "FKSpine2_M", "FKSpine3_M", "FKNeck_M", "FKHead_M")


def say(*parts):
    print(" ".join(str(p) for p in parts))
    sys.stdout.flush()


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, str(value)[:400]))


def section(title):
    say("\n==== " + title)


def new_scene(last=LAST):
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(minTime=0, maxTime=last, animationStartTime=0, animationEndTime=last)
    cmds.currentTime(0)


def add_rig(key="Manny_Rig"):
    before = set(cmds.ls([r.main for r in maya_rigs.rigs()], uuid=True) or [])
    character.add_character(catalog.character_by_key(key))
    cmds.select(clear=True)
    return [r for r in maya_rigs.rigs() if cmds.ls(r.main, uuid=True)[0] not in before][0]


def ctrl(rig, leaf):
    return cmds.ls(rig.namespace + ":" + leaf, long=True)[0]


def settable(plug):
    try:
        return cmds.getAttr(plug, settable=True)
    except (RuntimeError, ValueError):
        return False


def key_take(rig, add=None, over=None, times=(0, 10, 20, 30), phase=0.0):
    """The base: the arms and the spine turning, Main walking; `add`: an additive layer turning
    the right arm and the chest more; `over`: an override layer at 0.5 on the left elbow."""
    for i, leaf in enumerate(ARM + SPINE):
        path = ctrl(rig, leaf)
        for j, attr in enumerate(ROT):
            if not settable(path + "." + attr):
                continue
            for t in times:
                cmds.setKeyframe(path, attribute=attr, time=t,
                                 value=20.0 * math.sin(0.7 * i + 1.3 * j + 0.2 * t + phase))
    for t in (times[0], times[-1]):
        cmds.setKeyframe(rig.main, attribute="translateZ", time=t, value=t * 4.0)
    if add:
        layer = add if cmds.objExists(add) else cmds.animLayer(add)
        for i, leaf in enumerate(ARM[:3] + SPINE[2:]):
            path = ctrl(rig, leaf)
            plugs = [path + "." + a for a in ROT if settable(path + "." + a)]
            cmds.animLayer(layer, edit=True, attribute=plugs)
            for plug in plugs:
                for t in (0, 15, 30):
                    cmds.setKeyframe(plug, time=t, value=15.0 * math.cos(i + 0.3 * t),
                                     animLayer=layer)
    if over:
        layer = over if cmds.objExists(over) else cmds.animLayer(over, override=True)
        plug = ctrl(rig, "FKElbow_L") + ".rotateY"
        cmds.animLayer(layer, edit=True, weight=0.5, attribute=[plug])
        for t, v in ((0, 30.0), (30, -30.0)):
            cmds.setKeyframe(plug, time=t, value=v, animLayer=layer)


SAVED = [0]


def save(selection, name, start=0, end=LAST):
    SAVED[0] += 1
    clip = animcapture.build_clip(selection, start=start, end=end)
    if clip.header is None:
        raise RuntimeError(clip.note)
    path = store.write(LIBRARY, "", "%s%d" % (name, SAVED[0]), clip.header, frames=clip.frames,
                       curves=clip.curves)
    header = store.read(path)
    frames = store.read_frames(path) if clip.frames is not None else None
    curves = store.read_curves(path) if clip.curves is not None else None
    return header, frames, curves, clip


def paste(card, selection, **options):
    header, frames, curves, _clip = card
    options.setdefault("at_current", False)
    options.setdefault("paste_as", "curves")
    return animapply.apply(header, frames, selection=selection, options=options, curves=curves)


def bone_paths(rig):
    joints = [rig.skeleton_root] + (cmds.listRelatives(rig.skeleton_root, allDescendents=True,
                                                       type="joint", fullPath=True) or [])
    return dict((j.split("|")[-1].split(":")[-1], j) for j in joints)


def wm(path):
    return om.MMatrix(cmds.getAttr(path + ".worldMatrix[0]"))


def ang(a, b):
    q = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    r = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    return math.degrees(2 * math.acos(min(1.0, abs(q.x * r.x + q.y * r.y + q.z * r.z
                                                   + q.w * r.w))))


def worst(card, rig, span=None, shift=0):
    """(deg, cm, bone, frame) of the worst bone of `rig` against the card's own frame
    `frame - shift`, both relative to their root, over the target frames `span`."""
    header, frames = card[0], card[1]
    paths = bone_paths(rig)
    out = (0.0, 0.0, None, None)
    for f in (span if span is not None else range(0, LAST + 1)):
        found = animdata.bones_at(header, frames, int(f - shift - header["start"]))
        want = dict((leaf, om.MMatrix(found[leaf]["world"])) for leaf in found)
        cmds.currentTime(f)
        root_t, root_c = wm(paths["root"]).inverse(), want["root"].inverse()
        for leaf, m in want.items():
            if leaf not in paths:
                continue
            got, exp = wm(paths[leaf]) * root_t, m * root_c
            d = ang(got, exp)
            cm = math.sqrt(sum((got[12 + i] - exp[12 + i]) ** 2 for i in range(3)))
            if d > out[0] + 1e-12 or (abs(d - out[0]) <= 1e-12 and cm > out[1]):
                out = (d, cm, leaf, f)
    return out


def matches(found):
    return found[0] <= DEG and found[1] <= CM


def shown(found):
    return "%.4f deg / %.4f cm (%s, frame %s)" % found


def held(layer, rig):
    """The plugs of `rig` the layer holds."""
    if not cmds.objExists(layer):
        return []
    mark = rig.namespace + ":"
    return [p for p in cmds.animLayer(layer, query=True, attribute=True) or []
            if p.startswith(mark) or (":" + mark) in p or ("|" + mark) in p]


def prop_layer_source(kind="additive"):
    """Rig A on the base, a locator `prop` keyed, PropLayer holding the prop and A's right arm
    (Add Selected Objects), keyed on both."""
    new_scene()
    a = add_rig()
    key_take(a)
    prop = cmds.spaceLocator(name="prop")[0]
    for t in (0, 15, 30):
        cmds.setKeyframe(prop, attribute="translateY", time=t, value=t * 2.0)
        cmds.setKeyframe(prop, attribute="rotateY", time=t, value=t * 6.0)
    layer = cmds.animLayer("PropLayer", override=(kind == "override"))
    cmds.select([prop] + [ctrl(a, leaf) for leaf in ARM[:3]])
    cmds.animLayer(layer, edit=True, addSelectedObjects=True)
    cmds.select(clear=True)
    for t in (0, 15, 30):
        cmds.setKeyframe(prop, attribute="rotateX", time=t, value=10.0 + t, animLayer=layer)
        cmds.setKeyframe(ctrl(a, "FKElbow_R"), attribute="rotateZ", time=t, value=5.0 + t,
                         animLayer=layer)
    return a, prop, layer


def own_keys_in(layer, rig, every=5):
    """The animator's own: `rig`'s LEFT arm - which the card's layer never held - added to
    `layer` and its elbow keyed there."""
    cmds.select([ctrl(rig, leaf) for leaf in ARM[3:]])
    cmds.animLayer(layer, edit=True, addSelectedObjects=True)
    cmds.select(clear=True)
    for t in range(0, LAST + 1, every):
        cmds.setKeyframe(ctrl(rig, "FKElbow_L"), attribute="rotateY", time=t, value=3.0 * t,
                         animLayer=layer)


# ------------------------------------------------------------------ the phases

def phase_delete():
    section("delete: the character deleted, a new one added")
    new_scene()
    a = add_rig()
    key_take(a, "AddFix", "OverHand")
    card = save([a.main], "Layered")
    text = deletion.delete_selected([a.main], confirm=lambda _t: True)
    gate("delete: the character's layers went with it",
         not cmds.objExists("AddFix") and not cmds.objExists("OverHand"), text[:160])
    b = add_rig()
    ok, line = paste(card, [b.main], mode="replace_all")
    say("delete:", line)
    gate("delete: pasted", ok)
    gate("delete: AddFix and OverHand made, holding the new rig",
         len(held("AddFix", b)) >= 9 and len(held("OverHand", b)) >= 1,
         (len(held("AddFix", b)), len(held("OverHand", b))))
    found = worst(card, b)
    gate("delete: the bones the card's", matches(found), shown(found))


def phase_tabs():
    section("tabs: the same in a scene tabs session")
    from maya_scenetabs import hooks, opening, records, switching
    from maya_scenetabs import session as tabsession
    queue = []

    def flush():
        while queue:
            queue.pop(0)()

    new_scene()
    cmds.spaceLocator(name="other")
    cmds.file(rename=WORK + "/b.ma")
    cmds.file(save=True, type="mayaAscii", force=True)
    new_scene()
    cmds.file(rename=WORK + "/a.ma")
    cmds.file(save=True, type="mayaAscii", force=True)
    hooks.install(force=True)
    hooks._st()["defer"] = queue.append
    try:
        opening.open_tab(WORK + "/b.ma")
        flush()
        tabs = [t["ns"] for t in tabsession.state()["tabs"]]
        switching.switch(tabs[0])
        flush()
        tab = tabs[0]
        tab_root = tab + ":" + records.TAB_LAYER_ROOT
        a = add_rig()
        key_take(a, "AddFix", "OverHand")
        flush()
        card = save([a.main], "Tabs")
        deletion.delete_selected([a.main], confirm=lambda _t: True)
        flush()
        gate("tabs: the tab's layer root survives the delete", cmds.objExists(tab_root),
             cmds.ls(type="animLayer"))
        current = (cmds.namespaceInfo(currentNamespace=True, absoluteName=True) or "").lstrip(":")
        gate("tabs: the current namespace is still the tab's", current == tab, current)
        b = add_rig()
        flush()
        gate("tabs: the new rig lands in the tab", b.namespace.startswith(tab + ":"), b.namespace)
        ok, line = paste(card, [b.main], mode="replace_all")
        say("tabs:", line)
        gate("tabs: pasted", ok)
        gate("tabs: the line names the base BaseAnimation, not the session's root",
             curvedata.BASE in line and records.LAYER_ROOT not in line, line)
        flush()
        parents = dict((leaf, cmds.animLayer(tab + ":" + leaf, query=True, parent=True))
                       for leaf in ("AddFix", "OverHand") if cmds.objExists(tab + ":" + leaf))
        gate("tabs: the made layers under the tab's root", len(parents) == 2 and
             all(parent == tab_root for parent in parents.values()), parents)
        found = worst(card, b)
        gate("tabs: the bones the card's", matches(found), shown(found))
    finally:
        hooks.remove()


def phase_firstp():
    section("firstp: a rig in 1P, and a card saved off one")
    from maya_tools import firstperson as fp
    new_scene()
    a = add_rig()
    key_take(a, "AddFix", "OverHand")
    card = save([a.main], "Layered3P")
    b = add_rig()
    key_take(b, phase=1.0)
    cmds.currentTime(0)
    cmds.select(ctrl(b, "FKElbow_R"))
    say("1P setup:", fp.setup()[:120])
    upper = [layer for layer in fp.setup_layers(b.namespace) if fp.UPPER in layer][0]
    ok, line = paste(card, [b.main])
    say("firstp:", line)
    gate("firstp: a 3P card onto a rig in 1P pasted", ok)
    gate("firstp: retargeted, said", "1P" in line and "retargeted" in line, line)
    gate("firstp: no card layer took the 1P rig", not held("AddFix", b) and not held("OverHand", b),
         (held("AddFix", b)[:3], held("OverHand", b)[:3]))
    gate("firstp: Upper still muted", cmds.animLayer(upper, query=True, mute=True))
    found = worst(card, b)
    gate("firstp: the bones the card's", matches(found), shown(found))

    new_scene()
    a = add_rig()
    key_take(a)
    cmds.currentTime(0)
    cmds.select(ctrl(a, "FKElbow_R"))
    fp.setup()
    card = save([a.main], "From1P")
    gate("firstp: a card saved off a rig in 1P says so",
         card[0]["curves"].get("first_person") is True, card[0].get("curves", {}).get("layers"))
    gate("firstp: it takes no curves", not curvedata.takes_curves(card[0]))
    b = add_rig()
    ok, line = paste(card, [b.main])
    say("firstp:", line)
    gate("firstp: onto a 3P rig pasted, retargeted, said", ok and curveapply.FROM_1P in line, line)
    found = worst(card, b)
    gate("firstp: the bones the card's", matches(found), shown(found))


def phase_statics():
    section("statics: a layer holding channels without keys")
    for kind in ("override", "additive"):
        new_scene()
        a = add_rig()
        key_take(a)
        layer = cmds.animLayer("Held", override=(kind == "override"))
        cmds.currentTime(0)
        cmds.select([ctrl(a, leaf) for leaf in ARM[:3]])
        cmds.animLayer(layer, edit=True, addSelectedObjects=True)
        cmds.select(clear=True)
        elbow = ctrl(a, "FKElbow_R")
        for t, v in ((0, 40.0), (30, -20.0)):
            cmds.setKeyframe(elbow, attribute="rotateZ", time=t, value=v, animLayer=layer)
        if kind == "additive":
            # a static off zero: keyed, its curve deleted - the blend's input keeps the value
            wrist = ctrl(a, "FKWrist_R") + ".rotateY"
            cmds.setKeyframe(wrist, time=0, value=cmds.getAttr(wrist) + 25.0, animLayer=layer)
            cmds.delete(keys.curve_for(wrist, layer))
            gate("statics: additive: the wrist's static is off zero",
                 abs(keys.layer_static(wrist, layer) or 0.0) > 1.0, keys.layer_static(wrist, layer))
        card = save([a.main], "Held" + kind)
        wrist = [n for n in card[2]["nodes"] if n["name"] == "FKWrist_R"][0]
        gate("statics: %s: the card keeps the layer's statics" % kind,
             all("Held" in per for per in wrist["attrs"].values()),
             dict((attr, sorted(per)) for attr, per in wrist["attrs"].items()))
        new_scene()
        b = add_rig()
        ok, line = paste(card, [b.main])
        gate("statics: %s: pasted" % kind, ok, line)
        found = worst(card, b)
        gate("statics: %s: the bones the card's" % kind, matches(found), shown(found))


def phase_others():
    section("others: the target's own keys in its layers")
    for mode in ("replace", "replace_all", "insert", "merge"):
        a, prop, layer = prop_layer_source()
        card = save([a.main, prop], "WithProp")
        b = add_rig()
        key_take(b, phase=2.0)
        own_keys_in(layer, b)
        mine = cmds.animLayer("Mine")
        cmds.animLayer(mine, edit=True, attribute=[ctrl(b, "FKWrist_R") + ".rotateZ"])
        for t in range(0, LAST + 1, 10):
            cmds.setKeyframe(ctrl(b, "FKWrist_R") + ".rotateZ", time=t, value=40.0,
                             animLayer=mine)
        prop2 = cmds.spaceLocator(name="prop2")[0]
        ok, line = paste(card, [b.main, prop2], mode=mode)
        say("others %s:" % mode, line)
        gate("others: %s pasted" % mode, ok)
        found = worst(card, b)
        if mode == "merge":
            gate("others: merge leaves the target's layers and says so",
                 "Merge keeps it" in line and "PropLayer" in line and "Mine" in line, line)
        else:
            gate("others: %s clears them, said" % mode,
                 "PropLayer cleared" in line and "Mine cleared" in line, line)
            # Insert moves the target's keys from 0 on 31 frames later: the clip stands at 0..30
            gate("others: %s: the bones the card's" % mode, matches(found), shown(found))

    a, prop, layer = prop_layer_source()
    key_take(a, "AddFix")
    card = save([a.main], "Picked")
    b = add_rig()
    mine = cmds.animLayer("Mine")
    plug = ctrl(b, "FKWrist_R") + ".rotateZ"
    cmds.animLayer(mine, edit=True, attribute=[plug])
    for t in (0, 30):
        cmds.setKeyframe(plug, time=t, value=40.0, animLayer=mine)
    ok, line = paste(card, [b.main], layers=["AddFix"])
    say("others picked:", line)
    curve = keys.curve_for(plug, mine)
    gate("others: with the base not picked, a layer of the target's is untouched",
         ok and curve is not None and cmds.keyframe(curve, query=True, valueChange=True) == [40.0, 40.0]
         and "cleared" not in line, line)


def phase_pins():
    section("pins: a card whose curves end before its range, into a longer take")
    new_scene(100)
    a = add_rig()
    key_take(a, "AddFix")
    card = save([a.main], "Short", 0, 35)
    b = add_rig()
    key_take(b, times=tuple(range(0, 101, 5)), phase=0.5)
    probe = ctrl(b, "FKElbow_R") + ".rotateY"
    before = cmds.getAttr(probe, time=90)
    cmds.currentTime(40)
    ok, line = paste(card, [b.main], at_current=True)
    say("pins:", line)
    gate("pins: pasted at 40", ok)
    found = worst(card, b, range(40, 76), shift=40)
    gate("pins: 40..75 the card's 0..35", matches(found), shown(found))
    gate("pins: a target frame after the range untouched",
         abs(cmds.getAttr(probe, time=90) - before) < 1e-6, (before, cmds.getAttr(probe, time=90)))


def phase_undo():
    section("undo: one undo puts a paste back")
    a, prop, layer = prop_layer_source()
    key_take(a, "AddFix")
    card = save([a.main], "Undo")
    b = add_rig()
    own_keys_in(layer, b)
    plug = ctrl(b, "FKElbow_L") + ".rotateY"
    curve = keys.curve_for(plug, layer)
    keyed = cmds.keyframe(curve, query=True, valueChange=True)
    layers = sorted(cmds.ls(type="animLayer"))
    ok, line = paste(card, [b.main])
    gate("undo: pasted, PropLayer cleared", ok and "PropLayer cleared" in line, line)
    cmds.undo()
    gate("undo: the layers as they were", sorted(cmds.ls(type="animLayer")) == layers,
         sorted(cmds.ls(type="animLayer")))
    curve = keys.curve_for(plug, layer)
    gate("undo: the cleared layer's keys back",
         curve is not None and cmds.keyframe(curve, query=True, valueChange=True) == keyed)


def phase_objects():
    section("objects: a prop and the arm in a layer, saved with the rig")
    for kind in ("additive", "override"):
        a, prop, layer = prop_layer_source(kind)
        card = save([a.main, prop], "Objects" + kind)
        values = {}
        for f in range(0, LAST + 1, 3):
            values[f] = [cmds.getAttr(prop + "." + attr, time=f)
                         for attr in ("translateY", "rotateX", "rotateY")]
        new_scene()
        b = add_rig()
        prop2 = cmds.spaceLocator(name="prop2")[0]
        ok, line = paste(card, [b.main, prop2], mode="merge")
        say("objects %s:" % kind, line)
        gate("objects: %s pasted with Merge" % kind, ok)
        found = worst(card, b)
        gate("objects: %s: the bones the card's" % kind, matches(found), shown(found))
        off = max(abs(cmds.getAttr(prop2 + "." + attr, time=f) - v)
                  for f, row in values.items()
                  for attr, v in zip(("translateY", "rotateX", "rotateY"), row))
        gate("objects: %s: the prop's channels the card's" % kind, off < 1e-4, off)


try:
    for _phase in PHASES:
        try:
            globals()["phase_" + _phase]()
        except Exception:                                    # noqa: BLE001
            say(traceback.format_exc())
            RESULTS.append(False)
finally:
    say("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
    shutil.rmtree(LIBRARY, ignore_errors=True)
    shutil.rmtree(WORK, ignore_errors=True)
    sys.stdout.flush()
    os._exit(0 if all(RESULTS) else 1)
