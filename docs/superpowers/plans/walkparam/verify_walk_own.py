"""verify_walk_own.py - Walk Builder's Pick on skeletons that each carry their own cycle, mayapy standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_own.py

The animator (2026-10-16): «pick ко всем скелетам в сцене применяет один и тот же цикл а он должен брать цикл у
каждого скелета и обрабатывать его отдельно применяя одни и те же настройки. Это нужно для обработки массивов
анимаций». Three Manny skeletons are keyed with three different cycles (asd, dw, asd at stride 1.3 - made by the
tool, then stripped of everything but their keys, as an imported animation stands); Pick on all three.
"""
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")
WALKS = [os.path.join(HERE, "walks", n) for n in ("asd.walk.gz", "dw.walk.gz", "Creep_Drunk.walk.gz")]

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
from maya_walk import panel                              # noqa: E402
FAILED = []
COUNT = [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


if not all(os.path.exists(p) for p in WALKS):
    print("SKIP: the fixtures are not here (%s)" % ", ".join(WALKS))
    sys.exit(0)

TEMP = tempfile.mkdtemp(prefix="walkown_")
for path in WALKS:
    shutil.copy(path, TEMP)
sw.WALKS = TEMP
for key in [k for k in (cmds.optionVar(list=True) or []) if k.startswith(panel.OPTION)]:
    cmds.optionVar(remove=key)

cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
roots = {}
for ns, x, walk, knobs in (("A", 0.0, "asd", {}), ("B", 200.0, "dw", {}), ("C", 400.0, "asd", {"stride": 1.3})):
    cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace=ns, ignoreVersion=True)
    roots[ns] = cmds.ls(ns + ":root", long=True)[0]
    cmds.setAttr(roots[ns] + ".translateX", x)
    sw.apply(roots[ns], walk, knobs)
    for attr in (sw.MARKER, sw.POSE_COPY):                # only the keys stay: an imported animation
        if cmds.attributeQuery(attr, node=roots[ns], exists=True):
            cmds.deleteAttr(roots[ns] + "." + attr)


def pelvis_track(ns):
    """{frame: pelvis world position} over the keys."""
    pelvis = cmds.ls(ns + ":pelvis", long=True)[0]
    times = cmds.keyframe(pelvis, attribute="rotateX", query=True, timeChange=True)
    return dict((t, np.array(cmds.getAttr(pelvis + ".worldMatrix[0]", time=t))[12:15]) for t in times)


def travel(track):
    times = sorted(track)
    return float(np.linalg.norm(track[times[-1]] - track[times[0]]))


source = dict((ns, pelvis_track(ns)) for ns in "ABC")
gate(sw.walkers() == [], "three keyed skeletons, none walked yet")

# ---- Pick on all three: each on its own cycle ----
cmds.select(list(roots.values()), replace=True)
line = panel.press_apply_own()                            # Pick's right button: each on its own animation
print(line)
gate("3 skeletons processed" in line, "Pick processes the three")
gate(all(sw.has_source(roots[n]) for n in "ABC"), "each keeps its own cycle on its top joint")
names = [sw.memo_of(roots[n]).get("walk") for n in "ABC"]
gate(all(sw.is_own(n) for n in names) and len(set(names)) == 3, "three own cycles, all different (%s)" % names)
frames = dict((n, len(source[n])) for n in "ABC")
done = dict((n, len(pelvis_track(n))) for n in "ABC")
gate(done["A"] != done["B"], "A and B keep their own lengths (%d and %d frames)" % (done["A"], done["B"]))
ratio = dict((n, travel(pelvis_track(n)) / travel(source[n])) for n in "ABC")
gate(all(abs(r - 1.0) < 0.15 for r in ratio.values()), "each travels about its own source's distance (%s)"
     % ", ".join("%s x%.3f" % (n, ratio[n]) for n in "ABC"))
gate(travel(pelvis_track("C")) > 1.15 * travel(pelvis_track("A")), "C (the longer stride) still strides longer "
     "than A: its own cycle, not A's")

# ---- one knob: every cycle stretched alike ----
before = dict((n, travel(pelvis_track(n))) for n in "ABC")
cmds.optionVar(floatValue=(panel.OPTION + "knob_stride", 1.2))
print(panel.slider_changed())
after = dict((n, travel(pelvis_track(n))) for n in "ABC")
gate(all(abs(after[n] / before[n] - 1.2) < 0.02 for n in "ABC"), "stride 1.2 lengthens every cycle x1.2 (%s)"
     % ", ".join("%s x%.3f" % (n, after[n] / before[n]) for n in "ABC"))

# ---- Pick again: the kept cycle, not the keys it now carries ----
cmds.select(roots["B"], replace=True)
panel.press_apply_own()
gate(sw.memo_of(roots["B"]).get("walk") == names[1], "a second Pick works on the kept cycle again")

# ---- the scene saved and opened elsewhere: the cycles travel with it ----
path = os.path.join(TEMP, "batch.ma")
cmds.file(rename=path)
cmds.file(save=True, type="mayaAscii", force=True)
shutil.rmtree(os.path.join(TEMP, sw.OWN_CACHE), ignore_errors=True)
sw._state()["loaded"] = {}
cmds.file(path, open=True, force=True)
roots = dict((ns, cmds.ls(ns + ":root", long=True)[0]) for ns in "ABC")
cmds.optionVar(floatValue=(panel.OPTION + "knob_stride", 1.0))
print(panel.slider_changed())
gate(len(sw.walkers()) == 3 and all(abs(travel(pelvis_track(n)) / before[n] - 1.0) < 0.02 for n in "ABC"),
     "reopened with no walk file left: the list re-keys from the cycles kept in the scene")

# ---- Restore: the original keys back ----
cmds.select(clear=True)
panel.show_list = lambda: None
print(sw.restore_source(roots["A"]))
back = pelvis_track("A")
worst = max(float(np.linalg.norm(back[t] - source["A"][t])) for t in source["A"] if t in back)
gate(sorted(back) == sorted(source["A"]) and worst < 1e-3, "Restore: A's pelvis on its original keys (%d frames, "
     "%.6f cm)" % (len(back), worst))
gate(not sw.has_source(roots["A"]) and roots["A"] not in sw.walkers(), "A is out of the list, nothing kept")

# ---- Pick itself puts the card on (the card comes first), keeping the skeleton's own animation ----
cmds.optionVar(stringValue=(panel.OPTION + "walk", "dw"))
cmds.select(roots["A"], replace=True)
print(panel.press_apply())
gate(sw.memo_of(roots["A"]).get("walk") == "dw" and len(pelvis_track("A")) == 91,
     "Pick on an animated skeleton puts the card dw on it (%d keys)" % len(pelvis_track("A")))
gate(sw.has_source(roots["A"]), "its own animation was kept before the card was keyed")
print(sw.restore_source(roots["A"]))
back = pelvis_track("A")
worst = max(float(np.linalg.norm(back[t] - source["A"][t])) for t in source["A"] if t in back)
gate(sorted(back) == sorted(source["A"]) and worst < 1e-3, "and Restore brings it back (%.6f cm)" % worst)

# ---- an empty walk well: Pick reads the skeleton's clip, never a saved walk file (the animator's report) ----
cmds.optionVar(remove=panel.OPTION + "walk")
gate(sw.walk_names() == ["Creep_Drunk", "asd", "dw"], "the walks folder still holds saved files (%s)"
     % ", ".join(sw.walk_names()))
cmds.select(roots["A"], replace=True)
print(panel.press_apply())
gate(sw.is_own(sw.memo_of(roots["A"]).get("walk")) and len(pelvis_track("A")) == len(source["A"]),
     "Pick with an empty well processes A's own clip (%s, %d keys)"
     % (sw.memo_of(roots["A"]).get("walk"), len(pelvis_track("A"))))


def load_clip(dst, walk):
    """A clip put on the walker `dst` from outside the tool: its keys rewritten (here by the walk `walk`), its marker
    left saying what it said before - as an import onto it leaves it."""
    root = roots[dst]
    memo = cmds.getAttr(root + "." + sw.MARKER)
    sw.apply(root, walk, {})
    cmds.setAttr(root + "." + sw.MARKER, memo, type="string")


# ---- a clip loaded onto a walker: a knob leaves it, the next Pick reads it ----
old_walk = sw.memo_of(roots["B"]).get("walk")
load_clip("B", "asd")
loaded = pelvis_track("B")
gate(sw.keys_changed(roots["B"]), "B carries a clip loaded by hand: its keys are not the walk's any more")
cmds.select(clear=True)
line = panel.slider_changed()
print(line)
same = sorted(pelvis_track("B")) == sorted(loaded) and all(
    np.allclose(pelvis_track("B")[t], loaded[t]) for t in loaded)
gate("new keys on it" in line and same, "a knob leaves B's new clip alone and says so")
cmds.select(roots["B"], replace=True)
print(panel.press_apply())
new_walk = sw.memo_of(roots["B"]).get("walk")
gate(sw.is_own(new_walk) and new_walk != old_walk and len(pelvis_track("B")) == len(loaded),
     "Pick reads B's new clip as its cycle (%d keys, was %s, now %s)" % (len(pelvis_track("B")), old_walk, new_walk))
gate(not sw.keys_changed(roots["B"]), "and its keys are the walk's again")

# ---- a card chosen after another cycle: at its own tempo (Creep_Drunk looked broken, squeezed into 31 frames) ----
P_drunk = sw.load_walk("Creep_Drunk", {})[0].P
panel._walk_taken("asd")                                  # the tempo counts asd's frames
cmds.optionVar(stringValue=(panel.OPTION + "walk", "Creep_Drunk"))   # the active cycle changed some other way
cmds.file(os.path.join(ASSETS, "Manny_Skeleton.ma"), i=True, namespace="D", ignoreVersion=True)
roots["D"] = cmds.ls("D:root", long=True)[0]
cmds.select(roots["D"], replace=True)
print(panel.press_apply())
gate(sw.memo_of(roots["D"]).get("walk") == "Creep_Drunk" and len(pelvis_track("D")) == P_drunk + 1,
     "Creep_Drunk on a fresh skeleton at its own %d frames (%d keys)" % (P_drunk, len(pelvis_track("D"))))

shutil.rmtree(TEMP, ignore_errors=True)
print("FAILED gates: %s" % FAILED if FAILED else "all %d gates passed" % COUNT[0])
