"""verify_walk_many.py - Walk Builder's list of walkers, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_many.py

The animator (2026-10-16): «обрабатывать сразу несколько циклов на разных персонажах ... pick должна добавлять
персонажа в список ... для каждого цикла своя средняя поза ... все настройки работают одинаково для всех циклов
но каждый цикл уникальный». Three Manny skeletons, two on asd and one on dw (walks/, git-ignored, copied into a
temporary walks folder); the card's presses through maya_walk.panel with no window (its knobs in optionVars).
"""
import math
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")
WALKS = [os.path.join(HERE, "walks", n) for n in ("asd.walk.gz", "dw.walk.gz")]

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except RuntimeError:
        pass

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))     # the repository's plugin, never the installed copy
from maya_walk import scene as sw                        # noqa: E402
from maya_walk import panel, meanrig, meanpose as mp      # noqa: E402
wm = sw.wm
FAILED = []
COUNT = [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


def deg(r):
    return math.degrees(float(np.linalg.norm(wm.log_rot(r))))


if not all(os.path.exists(p) for p in WALKS):
    print("SKIP: the fixtures are not here (%s)" % ", ".join(WALKS))
    sys.exit(0)

TEMP = tempfile.mkdtemp(prefix="walkmany_")
for path in WALKS:
    shutil.copy(path, TEMP)
sw.WALKS = TEMP
for key in [k for k in (cmds.optionVar(list=True) or []) if k.startswith(panel.OPTION)]:
    cmds.optionVar(remove=key)                           # the card's memory starts empty

cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
roots = {}
for ns, x in (("A", 0.0), ("B", 200.0), ("C", 400.0)):
    cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace=ns, ignoreVersion=True)
    roots[ns] = cmds.ls(ns + ":root", long=True)[0]
    cmds.setAttr(roots[ns] + ".translateX", x)


def memo(ns):
    return sw.memo_of(roots[ns])


def upper_mean(ns):
    """The mean local rotation of ns:upperarm_l in its clavicle over the keyed cycle."""
    arm, clav = (cmds.ls("%s:%s" % (ns, n), long=True)[0] for n in ("upperarm_l", "clavicle_l"))
    times = cmds.keyframe(cmds.ls(ns + ":pelvis", long=True)[0], attribute="rotateX", query=True,
                          timeChange=True)
    rots = []
    for t in times:
        a = np.array(cmds.getAttr(arm + ".worldMatrix[0]", time=t)).reshape(4, 4)[:3, :3]
        c = np.array(cmds.getAttr(clav + ".worldMatrix[0]", time=t)).reshape(4, 4)[:3, :3]
        rots.append(a @ c.T)
    return wm.mean_rot(np.array(rots))


# ---- Pick: two skeletons on asd at once, then one on dw ----
cmds.optionVar(stringValue=(panel.OPTION + "walk", "asd"))
cmds.select([roots["A"], roots["B"]], replace=True)
line = panel.press_apply()
print(line)
gate("2 skeletons pick asd" in line, "Pick with two skeletons selected puts the card asd on both")
P_asd = sw.load_walk("asd", {})[0].P
P_dw = sw.load_walk("dw", {})[0].P
panel._walk_taken("dw")
cmds.select(roots["C"], replace=True)
print(panel.press_apply())
listed = sw.walkers()
gate(sorted(listed) == sorted(roots.values()), "the list is the three walked skeletons (%s)"
     % ", ".join(sw.walker_label(r) for r in listed))
gate([memo(n)["walk"] for n in "ABC"] == ["asd", "asd", "dw"], "A and B walk asd, C walks dw")
gate([sw.walker_label(roots[n]) for n in "ABC"] == ["A", "B", "C"], "labels: their namespaces")

# ---- a knob: every walker keyed again, each on its own cycle, the tempo as a ratio ----
cmds.select(clear=True)
cmds.optionVar(floatValue=(panel.OPTION + "knob_stride", 1.3))
half = int(round(P_dw / 2.0))
cmds.optionVar(floatValue=(panel.OPTION + "knob_tempo", float(half)))    # half of dw's frames: twice as fast
line = panel.slider_changed()
print(line)
gate("3 walkers keyed" in line, "a knob re-keys all three")
gate([memo(n)["walk"] for n in "ABC"] == ["asd", "asd", "dw"], "each keeps its own cycle")
gate(all(abs(memo(n)["knobs"]["stride"] - 1.3) < 1e-9 for n in "ABC"), "stride 1.3 on every walker")
want = max(4, int(round(half * P_asd / float(P_dw))))
gate(int(memo("C")["knobs"]["tempo"]) == half and int(memo("A")["knobs"]["tempo"]) == want,
     "the tempo: C %d of dw's %d, A %d of asd's %d (the same ratio)" %
     (memo("C")["knobs"]["tempo"], P_dw, memo("A")["knobs"]["tempo"], P_asd))
keys = cmds.keyframe(cmds.ls("A:pelvis", long=True)[0], attribute="rotateX", query=True, timeChange=True)
gate(len(keys) == want + 1, "A's cycle is keyed over %d frames (%d keys)" % (want, len(keys)))

# ---- out of the list: a knob no longer reaches it ----
sw.set_listed(roots["A"], False)
cmds.optionVar(floatValue=(panel.OPTION + "knob_stride", 1.1))
panel.slider_changed()
gate(abs(memo("A")["knobs"]["stride"] - 1.3) < 1e-9 and abs(memo("B")["knobs"]["stride"] - 1.1) < 1e-9,
     "A out of the list keeps stride 1.3; B takes 1.1")
panel._walk_taken("asd")                                  # Pick puts the ACTIVE cycle on
cmds.select(roots["A"], replace=True)
panel.press_apply()
gate(memo("A").get("listed") and roots["A"] in sw.walkers(), "Pick puts A back in the list")

# ---- each cycle its own mean pose rig ----

print(meanrig.press("asd"))
print(meanrig.press("dw"))
rig_asd, rig_dw = meanrig.find("asd"), meanrig.find("dw")
gate(rig_asd is not None and rig_dw is not None and rig_asd.main != rig_dw.main and len(meanrig.rigs()) == 2,
     "two rig poses, one a cycle (%s, %s)" % (rig_asd and rig_asd.namespace, rig_dw and rig_dw.namespace))
x, _, _ = cmds.xform(rig_dw.main, query=True, worldSpace=True, translation=True)
gate(abs(x - (400.0 + meanrig.OFFSET)) < 1e-3, "dw's rig stands beside C, its walker (x %.1f)" % x)
before = dict((n, upper_mean(n)) for n in "ABC")
ns = rig_asd.namespace + ":"
cmds.setAttr(ns + "FKShoulder_L.rotateZ", cmds.getAttr(ns + "FKShoulder_L.rotateZ") + 20.0)
line = meanrig.update(rekey=panel.rekey_walkers)
print(line)
fix_asd = mp.load(mp.path_for(os.path.join(TEMP, "asd.walk.gz")))
fix_dw = mp.load(mp.path_for(os.path.join(TEMP, "dw.walk.gz")))
gate("upperarm_l" in fix_asd["rot"] and mp.is_empty(fix_dw), "the turn goes into asd's correction, dw's stays empty")
turned = dict((n, deg(upper_mean(n) @ before[n].T)) for n in "ABC")
gate(abs(turned["A"] - 20.0) < 1.0 and abs(turned["B"] - 20.0) < 1.0 and turned["C"] < 0.01,
     "asd's walkers turn (A %.2f, B %.2f deg), dw's does not (C %.4f)" % (turned["A"], turned["B"], turned["C"]))
print(meanrig.delete("asd"))
gate(meanrig.find("asd") is None and meanrig.find("dw") is not None, "Delete takes asd's rig only")

shutil.rmtree(TEMP, ignore_errors=True)
print("FAILED gates: %s" % FAILED if FAILED else "all %d gates passed" % COUNT[0])
