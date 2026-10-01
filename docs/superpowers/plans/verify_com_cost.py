r"""The CoM's cost per frame, A/B in mayapy standalone (2026-10-01).

A GUI Maya's per-frame time swings +-0.6 ms a rig from one run to the next
(Cached Playback refills in background threads after every graph change), so
the precise answer is measured here: Manny with a keyed take, the best of
seven 60-frame walks, three times over WITHOUT the CoM, WITH its nine nodes,
and with the engine's attribute callbacks on its controls too.

Measured: 5.45 / 5.41 / 5.04 ms - the network and the callbacks cost nothing
measurable.

    & 'C:\Program Files\Autodesk\Maya2027in\mayapy.exe' docs/superpowers/plans/verify_com_cost.py
"""
import sys, time, math
sys.path.insert(0, r"C:/!!!Work/MayaScripts/SkeldarAnim")
import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
for p in ("matrixNodes", "quatNodes"):
    cmds.loadPlugin(p, quiet=True)
cmds.file("C:/!!!Work/MayaScripts/SkeldarAnim/assets/Manny_Rig.ma", i=True, namespace="Manny_Rig")
from maya_com import network, engine
ns = "Manny_Rig:"
cmds.playbackOptions(min=0, max=60, ast=0, aet=60)
for c, chans in {"RootX_M": [("tx", 20), ("tz", 30), ("ry", 30)], "FKShoulder_L": [("rz", 40)],
                 "FKElbow_R": [("rz", 50)], "IKLeg_L": [("tz", 25), ("ty", 10)], "FKSpine1_M": [("rz", 20)]}.items():
    for ch, amp in chans:
        base = cmds.getAttr(ns + c + "." + ch)
        for f in range(0, 61, 5):
            cmds.setKeyframe(ns + c, at=ch, t=f, v=base + amp * math.sin(f / 60.0 * 2 * math.pi))
cmds.evaluationManager(mode="parallel")

def per_frame(runs=7, n=60):
    best = 1e9
    for _ in range(runs):
        t0 = time.time()
        for f in range(n):
            cmds.currentTime(f, update=True)
        best = min(best, (time.time() - t0) * 1000.0 / n)
    return best

rig = __import__("maya_rigs").rigs()[0]
char = network._character_for(rig.skeleton_root)
model, info = network.build_model(char)
res = {"without": [], "with": [], "with+callbacks": []}
for rep in range(3):
    per_frame(1)
    res["without"].append(per_frame())
    group = network.create(char, model, info)
    per_frame(1)
    res["with"].append(per_frame())
    engine._watch_nodes(cmds.ls(group, uuid=True)[0], group)
    per_frame(1)
    res["with+callbacks"].append(per_frame())
    engine._unwatch_nodes(cmds.ls(group, uuid=True)[0])
    network.remove(group)
for k, v in res.items():
    print("%-16s %s  min %.3f ms" % (k, ["%.3f" % x for x in v], min(v)))
