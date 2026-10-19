"""Probe, mayapy standalone: the animation and display layer commands the Time Bar's
layer panel builds on (2026-10-18). Prints facts; changes no file."""

FACTS = """Measured in Maya 2027 mayapy, 2026-10-18.
- Root layer: animLayer(q=True, root=True) -> 'BaseAnimation'; its children (q, children) -> ['A', 'B'] in order.
- animLayer(layer, q=True, attribute=True) -> list of FULL plug names 'probeCube.translateX' (node.attr, short
  node name), here 10 entries: visibility, translate XYZ, rotate XYZ, scale XYZ (selecting a transform adds all).
- findCurveForPlug on a layer answers a LIST: B -> ['probeCube_translateX_B_inputB']; the root ->
  ['probeCube_translateX'] (the base curve).
- Layer attributes (attributeQuery exists): mute, solo, lock, weight, override (all present on an animLayer node).
- Display layer (createDisplayLayer(name=, noRecurse=True)) attributes found: visibility, hideOnPlayback,
  displayType, color, displayOrder, overrideRGBColors, overrideColorRGB (all present).
  editDisplayLayerMembers(d, q=True, fullNames=True) -> ['|probeCube'] (long paths).
  cmds.colorIndex(13, q=True) -> None here (query form answers nothing in standalone).
- MERGE: the proc is the GLOBAL MEL proc `animLayerMerge(string $layers[])` in
  C:/Program Files/Autodesk/Maya2027/scripts/others/performAnimLayerMerge.mel. whatIs says 'Unknown' until that file
  is loaded: call mel.eval('source "performAnimLayerMerge.mel"') once, then
  mel.eval('animLayerMerge({"A","B"})'). (performAnimLayerMerge itself takes an INT action 0/1/2 and merges the
  global $gSelectedAnimLayers; passing layers to it raises 'Cannot convert string[] to int'. animLayerMergeLayers
  and a bare animLayerMerge before sourcing are unknown.)
  Behaviour: orders the layers by hierarchy; creates a layer 'Merged_Layer' as a sibling placed before the first
  given layer (optionVar animLayerMergeUp=1; 0 puts it after the last); bakes all attributes of the given layers
  with bakeResults -destinationLayer Merged_Layer -removeBakedAttributeFromLayer <deleteLayers> -time ':'
  -sampleBy <ByTime 1.0> -oversamplingRate <1> (-smart 1 if SmartBake) -resolveWithoutLayer for each layer;
  then (animLayerMergeDeleteLayers=1) deletes the emptied source layers, else mutes them. Ends with select -cl.
  No dialog and no UI; it READS OPTIONVARS (animLayerMergeUp 1, Childs 0, ResultType 0, DeleteLayers 1, BakeAll 1,
  ByTime 1.0, OversamplingRate 1, SmartBake 0, SmartFidelity 0, FidelityDelta 5) which it initialises itself
  (init, existing values kept). It prints the bakeResults command (evalEcho) to the output. If the first layer is
  BaseAnimation it makes a temp 'BaseCopy' layer. Not undo-safe to assume; the result is a new layer name
  'Merged_Layer' (Maya may suffix it) - find it after.
  Test: layers A,B (children of BaseAnimation) -> layers after: ['BaseAnimation', 'Merged_Layer']; cube.translateX
  at frames 0,5,10 read [-0.5, 2.0, 4.5] before and [-0.5, 2.0, 4.5] after: the merged result plays the same.
"""
import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds
import maya.mel as mel


def tryp(label, fn):
    try:
        print(label, fn())
    except Exception as e:  # the error is itself a fact
        print(label, "ERROR:", type(e).__name__, str(e).strip().splitlines()[0] if str(e).strip() else "")


cube = cmds.polyCube(name="probeCube")[0]
cmds.setKeyframe(cube, attribute="translateX", time=0, value=0)
cmds.setKeyframe(cube, attribute="translateX", time=10, value=5)
cmds.select(cube)
a = cmds.animLayer("A", addSelectedObjects=True)
b = cmds.animLayer("B", addSelectedObjects=True)
cmds.setKeyframe(cube, attribute="translateX", time=5, value=2, animLayer=b)
root = cmds.animLayer(q=True, root=True)
tryp("root:", lambda: root)
tryp("children of root:", lambda: cmds.animLayer(root, q=True, children=True))
tryp("B attributes:", lambda: cmds.animLayer(b, q=True, attribute=True))
tryp("B curve for tx:", lambda: cmds.animLayer(b, q=True, findCurveForPlug=cube + ".translateX"))
tryp("base curve for tx:", lambda: cmds.animLayer(root, q=True, findCurveForPlug=cube + ".translateX"))
for proc in ("animLayerMerge", "performAnimLayerMerge", "animLayerMergeLayers"):
    tryp(proc, lambda proc=proc: mel.eval('whatIs "%s"' % proc))
tryp("A attrs:", lambda: [x for x in ("mute", "solo", "lock", "weight", "override")
                          if cmds.attributeQuery(x, node=a, exists=True)])
d = cmds.createDisplayLayer(name="probeLayer", noRecurse=True)
tryp("display:", lambda: (d, [x for x in ("visibility", "hideOnPlayback", "displayType", "color", "displayOrder",
                                          "overrideRGBColors", "overrideColorRGB")
                              if cmds.attributeQuery(x, node=d, exists=True)]))
tryp("members:", lambda: cmds.editDisplayLayerMembers(d, q=True, fullNames=True))
tryp("colorIndex 13:", lambda: cmds.colorIndex(13, q=True))


def vals():
    return [round(cmds.getAttr(cube + ".translateX", time=t), 6) for t in (0, 5, 10)]


print("values before merge:", vals())
print("layers before merge:", cmds.ls(type="animLayer"))
# animLayerMerge is a global proc inside performAnimLayerMerge.mel, known only once that file is sourced
# (performAnimLayerMerge takes an INT action, not layers; it merges $gSelectedAnimLayers)
tryp("source:", lambda: mel.eval('source "performAnimLayerMerge.mel"'))
print("animLayerMerge:", mel.eval('whatIs "animLayerMerge"'))
tryp("opt up/childs/delete:", lambda: [cmds.optionVar(q=n) if cmds.optionVar(ex=n) else None
                                       for n in ("animLayerMergeUp", "animLayerMergeChilds", "animLayerMergeDeleteLayers")])
tryp("merge result:", lambda: mel.eval('animLayerMerge({"A","B"})'))
print("layers after merge:", cmds.ls(type="animLayer"))
print("values after merge:", vals())
