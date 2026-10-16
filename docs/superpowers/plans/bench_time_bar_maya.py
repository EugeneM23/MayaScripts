"""What a frame change costs Maya while the Time Bar scrubs, mayapy standalone
(2026-10-16): the plugin's Manny rig added, every control keyed so each frame
evaluates the whole rig, then `currentTime` over 100 frames - plain, with the Time
Bar's time-change callback standing (what our strip adds per frame), and without
the update (Maya's middle-drag scrub). The viewport's redraw is not in mayapy: in a
GUI Maya it comes on top of these, the same for any slider.

    mayapy docs/superpowers/plans/bench_time_bar_maya.py
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

import maya.standalone                                       # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                     # noqa: E402
import maya.api.OpenMaya as om                               # noqa: E402

for plugin in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except RuntimeError:
        pass

from maya_scenesetup import catalog, character               # noqa: E402

cmds.file(new=True, force=True)
character.add_character(catalog.default_rig())
controls = [c for c in cmds.ls("*:*", type="transform") if c.split(":")[-1].startswith(("FK", "IK", "Root"))]
cmds.playbackOptions(minTime=0, maxTime=100)
for c in controls:
    for attr in ("rotateX", "rotateY", "rotateZ"):
        plug = c + "." + attr
        if cmds.getAttr(plug, settable=True):
            cmds.setKeyframe(plug, time=0, value=0)
            cmds.setKeyframe(plug, time=100, value=10)
print("controls keyed: %d" % len(controls))


def walk(label, update=True):
    times = []
    for f in range(1, 101):
        t0 = time.perf_counter()
        cmds.currentTime(f, update=update)
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    print("%-34s median %.2f ms, p95 %.2f ms" % (label, times[50], times[95]))


for mode in ("parallel", "off"):
    cmds.evaluationManager(mode=mode)
    cmds.currentTime(0)
    walk("%s: currentTime" % mode)
    seen = []

    def on_time(*_args):                     # what the Time Bar's callback does per frame
        seen.append(cmds.currentTime(q=True))
    cid = om.MDGMessage.addTimeChangeCallback(on_time)
    walk("%s: + the Time Bar's callback" % mode)
    om.MMessage.removeCallback(cid)
    walk("%s: middle-drag (no update)" % mode, update=False)
