"""Probe (2026-10-28): how a RAW layer-curve value is keyed - the road `keys.write_raw` takes.
mayapy STANDALONE, scratch MAYA_APP_DIR:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' probe_poselib_raw_layer_keys.py [out]

A locator keyed on the base (tx 0/10/20, ry 0/45/90 at 0/10/20), three layers above it: AddL
(additive, component), OverL (override) and QuatL (additive, quaternion). On each layer and the
base, for tx and ry: the plug added, the layer's curve made by one key through the plug when it
has none (`setKeyframe -animLayer`, value 999 - a value no raw key holds), then raw values written
on the CURVE NODE (`setKeyframe <curve> -time -value`) and read back off it (`keyframe -q -vc`).
Then: the composite with only AddL on is base + raw; fixed angles / weights set after the keys
hold; the plug spelling `animLayer -q -attribute` answers; the accumulation enums. Every gate
prints PASS/FAIL, the run ends SUMMARY x/y.
"""

import io
import sys

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402

OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    if OUT is not None:
        OUT.write(line + "\n")
        OUT.flush()


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, value))


def curve_of(plug, layer):
    found = cmds.animLayer(layer, query=True, findCurveForPlug=plug)
    if isinstance(found, str):
        found = [found]
    return found[0] if found else None


def keys_of(curve):
    flat = cmds.keyframe(curve, query=True, timeChange=True, valueChange=True) or []
    return list(zip(flat[0::2], flat[1::2]))


def has(pairs, t, v):
    return any(abs(pt - t) < 1e-6 and abs(pv - v) < 1e-6 for pt, pv in pairs)


try:
    cmds.currentUnit(time="ntsc", angle="degree", linear="centimeter")
    loc = cmds.spaceLocator(name="probe")[0]
    for t, tx, ry in ((0, 0.0, 0.0), (10, 10.0, 45.0), (20, 20.0, 90.0)):
        cmds.setKeyframe(loc, attribute="translateX", time=t, value=tx)
        cmds.setKeyframe(loc, attribute="rotateY", time=t, value=ry)
    add = cmds.animLayer("AddL")
    over = cmds.animLayer("OverL", override=True)
    quat = cmds.animLayer("QuatL")
    cmds.setAttr(quat + ".rotationAccumulationMode", 1)
    base = cmds.animLayer(query=True, root=True)
    raw = {"translateX": [(0.0, 1.5), (5.0, -2.0), (20.0, 3.25)],
           "rotateY": [(0.0, 12.5), (5.0, -30.0), (20.0, 7.0)]}
    for layer in (add, over, quat, base):
        for attr, wanted in raw.items():
            plug = loc + "." + attr
            if layer != base:
                cmds.animLayer(layer, edit=True, attribute=plug)
            curve = curve_of(plug, layer)
            if curve is None:
                cmds.setKeyframe(plug, time=wanted[0][0], value=999.0, animLayer=layer)
                curve = curve_of(plug, layer)
            gate("%s %s: a curve" % (layer, attr), curve is not None, curve)
            for t, v in wanted:
                cmds.setKeyframe(curve, time=t, value=v)
            pairs = keys_of(curve)
            gate("%s %s: every raw value back off the curve" % (layer, attr),
                 all(has(pairs, t, v) for t, v in wanted), pairs)
            gate("%s %s: the 999 creating key overwritten" % (layer, attr),
                 not any(abs(pv - 999.0) < 1e-6 for _pt, pv in pairs), pairs)
    # the composite: AddL alone on top of the base is base + raw (tx at 5: base 5 + raw -2)
    for layer in (over, quat):
        cmds.animLayer(layer, edit=True, mute=True)
    cmds.currentTime(5, update=True)
    shown = cmds.getAttr(loc + ".translateX")
    base_at = cmds.keyframe(curve_of(loc + ".translateX", base), query=True, eval=True, time=(5, 5))[0]
    gate("AddL tx at 5 shows the base under it plus the raw key", abs(shown - (base_at - 2.0)) < 1e-6,
         (shown, base_at))
    # tangents after the keys
    tx_add = curve_of(loc + ".translateX", add)
    cmds.keyTangent(tx_add, edit=True, weightedTangents=True)
    cmds.keyTangent(tx_add, edit=True, time=(5, 5), inAngle=20.0, outAngle=-10.0, inWeight=2.0,
                    outWeight=3.0, lock=False, weightLock=False)
    angles = cmds.keyTangent(tx_add, query=True, time=(5, 5), inAngle=True, outAngle=True)
    weights = cmds.keyTangent(tx_add, query=True, time=(5, 5), inWeight=True, outWeight=True)
    gate("fixed angles hold on a layer curve", abs(angles[0] - 20) < 1e-4 and abs(angles[1] + 10) < 1e-4,
         angles)
    gate("weights hold on a layer curve", abs(weights[0] - 2) < 1e-4 and abs(weights[1] - 3) < 1e-4,
         weights)
    say("animLayer -q -attribute on AddL:", cmds.animLayer(add, query=True, attribute=True))
    say("rotationAccumulationMode:", cmds.attributeQuery("rotationAccumulationMode", node=add,
                                                         listEnum=True))
    say("scaleAccumulationMode:", cmds.attributeQuery("scaleAccumulationMode", node=add, listEnum=True))
    say("scaleAccumulationMode of a new layer:", cmds.getAttr(add + ".scaleAccumulationMode"))
except Exception:                                            # noqa: BLE001
    import traceback
    say(traceback.format_exc())
    RESULTS.append(False)
say("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
maya.standalone.uninitialize()
