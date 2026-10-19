"""verify_timebar_active_layer.py - keys go into the selected layer, the Time Bar shows and edits
the active layer's keys only (2026-10-19), mayapy standalone.

The animator: «Ключи ставятся не в выделенный слой а в базовый и отрисовываются в базовом ... Давай
сделаем как в мае. Если выбран слой то ключик ставим в него. Ключи из других слоев на таймлайне не
видно»."""
import sys
import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds
import maya.mel as mel
sys.path.insert(0, r"C:/!!!Work/MayaScripts/SkeldarAnim")
from maya_timebar import layerscene as S, scene

FAIL = []
N = [0]


def gate(ok, text):
    N[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", N[0], text))
    if not ok:
        FAIL.append(N[0])


def layer_keys(layer, plug):
    curve = (cmds.animLayer(layer, q=True, findCurveForPlug=plug) or [None])[0]
    return (cmds.keyframe(curve, q=True, timeChange=True) or []) if curve else []


a = cmds.polyCube(name="cubeA")[0]
b = cmds.polyCube(name="cubeB")[0]
for t, v in ((0, 0), (10, 5)):
    cmds.setKeyframe(a, attribute="translateX", time=t, value=v)
    cmds.setKeyframe(b, attribute="translateX", time=t, value=v)
cmds.select(clear=True)
gate(scene.keys()[0] == [] and S.active_curves() is None, "no layers: the old reading")
cmds.select(a)
gate(scene.keys()[0] == [0.0, 10.0], "no layers: every key of the selection")
S.create_anim()
L1 = S.anim_layers()[0]["name"]
cmds.setKeyframe(a, attribute="translateX", time=5, value=2, animLayer=L1)
root = cmds.animLayer(q=True, root=True)

# -- the timeline shows the active layer's keys --------------------------------------------
S.pick(L1)
gate(scene.keys()[0] == [5.0], "L1 active: the timeline shows L1's key only: %s" % (scene.keys(),))
S.pick(root)
gate(scene.keys()[0] == [0.0, 10.0], "the base active: the base's keys only: %s" % (scene.keys(),))

# -- and edits only them ---------------------------------------------------------------
S.pick(L1)
scene.delete_keys((0, 10), 0.0)
gate(layer_keys(L1, a + ".translateX") == [] and layer_keys(root, a + ".translateX") == [0.0, 10.0],
     "Delete over 0-10 with L1 active takes L1's key, the base keeps its own")
cmds.undo()
scene.move_keys((5, 5), (8, 8))
gate(layer_keys(L1, a + ".translateX") == [8.0] and layer_keys(root, a + ".translateX") == [0.0, 10.0],
     "a move takes L1's key only: %s" % layer_keys(L1, a + ".translateX"))
cmds.undo()

# -- a key on an object not in the selected layer goes INTO the layer ---------------------
cmds.select(b)
gate(b + ".translateX" not in (cmds.animLayer(L1, q=True, attribute=True) or []), "cubeB is not in L1")
cmds.currentTime(7)
scene.set_key()
gate(layer_keys(L1, b + ".translateX") == [7.0], "the Time Bar's Set key: into L1 (%s)" % layer_keys(L1, b + ".translateX"))
gate(layer_keys(root, b + ".translateX") == [0.0, 10.0], "the base keeps cubeB's keys")
cmds.undo()

# -- Maya's own S (performSetKeyframeArgList) through our hook ----------------------------
c = cmds.polyCube(name="cubeC")[0]
cmds.setKeyframe(c, attribute="translateX", time=0, value=0)
about = cmds.about
cmds.about = lambda **k: False if k.get("batch") else about(**k)       # the hook is GUI-only
try:
    sys.__dict__.pop("_skeldar_timebar_key_hook", None)
    gate(S.key_hook(), "our performSetKeyframeArgList sourced over Maya's")
finally:
    cmds.about = about
S.pick(L1)
cmds.select(c)
cmds.currentTime(12)
mel.eval('performSetKeyframeArgList 1 {"0", "animationList"}')
gate(layer_keys(L1, c + ".translateX") == [12.0], "S on cubeC (not in L1): the key in L1: %s"
     % layer_keys(L1, c + ".translateX"))
S.pick(root)
cmds.currentTime(14)
mel.eval('performSetKeyframeArgList 1 {"0", "animationList"}')
gate(14.0 in (cmds.keyframe(layer_keys and (cmds.animLayer(root, q=True, findCurveForPlug=c + ".translateX") or [None])[0],
                            q=True, timeChange=True) or []), "the base active: S keys the base")

# -- in a scene tab: BaseAnimation is the tab's root, a layer to Maya ------------------------
import os
import tempfile
from maya_scenetabs import opening
folder = tempfile.mkdtemp()


def make(path, tag):
    cmds.file(new=True, force=True)
    c = cmds.polyCube(name="cube" + tag)[0]
    cmds.setKeyframe(c, attribute="translateX", time=0, value=0)
    o = cmds.polySphere(name="other" + tag)[0]
    cmds.select(o)
    cmds.animLayer("Old", addSelectedObjects=True)          # the tab gets a root of its own
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii", force=True)


pa, pb = os.path.join(folder, "a.ma"), os.path.join(folder, "b.ma")
make(pa, "A")
make(pb, "B")
cmds.file(pa, open=True, force=True)
opening.open_tab(pb)
cube = cmds.ls("tab_b:cubeB")[0]
cmds.select(cube)
S.create_anim()
TL = S.anim_layers()[0]["name"]
troot = S.anim_layers()[-1]["name"]
maya_root = cmds.animLayer(q=True, root=True)
gate(troot != maya_root, "the tab's BaseAnimation is its own root: %s under %s" % (troot, maya_root))


def base_keys(node):
    curve = (cmds.animLayer(maya_root, q=True, findCurveForPlug=node + ".translateX") or [None])[0]
    return (cmds.keyframe(curve, q=True, timeChange=True) or []) if curve else []


S.pick(troot)
cmds.select(cube)
gate(scene.keys()[0] == [0.0], "the base active: the timeline shows the base's key: %s" % (scene.keys(),))
cmds.currentTime(20)
mel.eval('performSetKeyframeArgList 1 {"0", "animationList"}')
gate(base_keys(cube) == [0.0, 20.0] and layer_keys(TL, cube + ".translateX") == [],
     "S with the base active keys the base: base %s, layer %s" % (base_keys(cube), layer_keys(TL, cube + ".translateX")))
gate(cmds.animLayer(troot, q=True, selected=True) and not cmds.animLayer(maya_root, q=True, selected=True),
     "the layer flags put back after the key")
gate(S.keys_by_layer([troot])[troot] == [0.0, 20.0], "the base lane reads the base's keys: %s"
     % S.keys_by_layer([troot])[troot])
S.lane_set_key(troot)
cmds.currentTime(25)
S.lane_set_key(troot)
gate(25.0 in base_keys(cube), "Set key on the base lane keys the base: %s" % base_keys(cube))
S.pick(TL)
cmds.currentTime(30)
mel.eval('performSetKeyframeArgList 1 {"0", "animationList"}')
gate(layer_keys(TL, cube + ".translateX") == [30.0] and 30.0 not in base_keys(cube),
     "then the layer active: S keys the layer")
print("%d of %d gates failed" % (len(FAIL), N[0]))
