"""Arm to IK in a scene tab, with the tab's BaseAnimation selected (2026-10-24).

The animator: «з'являються 2 слої і рука ламається при перепіканні на ІК». In scene tabs the
tab's base is `<tab>:AnimLayerRoot` under `skeldarTabsLayerRoot`; the Layer Editor reads it
BaseAnimation and selecting it selected it. `maya_poselib.keys.active_layer` took it for an
additive layer: the arm's channels were added to it and keyed with what they must SHOW, on top
of the base curves - the arm doubled.

Run from the repo root (PowerShell):
  $env:MAYA_APP_DIR = "$env:TEMP\\skeldar_tabs_appdir"
  & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_fkik_tab_layers.py <scene> [plugin dir]
The scene is copied, never written. The last line is "N of M gates failed".
"""
import os
import shutil
import sys
import tempfile

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402

for _plug in ("matrixNodes", "quatNodes"):
    cmds.loadPlugin(_plug, quiet=True)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PLUGIN = (sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "SkeldarAnim")).replace("\\", "/")
sys.path.insert(0, PLUGIN)

import maya_rigs  # noqa: E402
from maya_scenesetup import connections, fkik  # noqa: E402
from maya_scenetabs import layers as tablayers, opening  # noqa: E402

RESULTS = []
TOL_CM = 0.05


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail), flush=True)


def world(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def sample(nodes, frames):
    out = {}
    for f in frames:
        cmds.currentTime(f, update=True)
        out[f] = [world(n) for n in nodes]
    return out


def worst(a, b):
    best = (0.0, None)
    for f in a:
        for p, q in zip(a[f], b[f]):
            d = sum((x - y) ** 2 for x, y in zip(p, q)) ** 0.5
            if d > best[0]:
                best = (d, f)
    return best


def main():
    src = sys.argv[1]
    work = os.path.join(tempfile.gettempdir(), "skeldar_fkik_tab_verify")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    path = os.path.join(work, os.path.basename(src)).replace("\\", "/")
    shutil.copy(src, path)
    cmds.file(path, open=True, force=True, ignoreVersion=True, prompt=False)
    print("plugin", PLUGIN, "| keys from", __import__("maya_poselib.keys").keys.__file__, flush=True)
    state = opening.start()
    tab = state["active"]
    root = cmds.animLayer(query=True, root=True)
    tab_root = tablayers.tab_root(tab) if hasattr(tablayers, "tab_root") else "%s:AnimLayerRoot" % tab
    gate("the scene is a tab under the session root", root == "skeldarTabsLayerRoot" and cmds.objExists(tab_root),
         "%s / %s" % (root, tab_root))
    for layer in (root, tab_root):
        cmds.animLayer(layer, edit=True, selected=True)
    rig = [r for r in maya_rigs.rigs() if r.namespace.startswith(tab)][0]
    ns = rig.namespace
    probes = [ns + ":" + j for j in ("Shoulder_L", "Elbow_L", "Wrist_L")]
    start = int(cmds.playbackOptions(query=True, min=True))
    end = int(cmds.playbackOptions(query=True, max=True))
    frames = list(range(start, end + 1))
    layers_before = sorted(cmds.ls(type="animLayer"))
    tab_attrs_before = len(cmds.animLayer(tab_root, query=True, attribute=True) or [])
    before = sample(probes, frames)

    arm, _ = fkik.limb(rig, "L")
    print("Arm_L mode before:", fkik.mode_of(fkik.blend_values(arm)), flush=True)
    line = connections.switch_arm("L", fkik.IK, rig=rig, highlight=[])
    print("line:", line, flush=True)
    after = sample(probes, frames)
    if os.environ.get("FKIK_TAB_DETAIL"):
        for fr in frames:
            off = max(sum((x - y) ** 2 for x, y in zip(p, q)) ** 0.5 for p, q in zip(before[fr], after[fr]))
            if off > TOL_CM:
                print("   frame %s off %.2f cm" % (fr, off), flush=True)
    d, f = worst(before, after)
    gate("Arm_L to IK: the arm keeps what it showed on every frame", d <= TOL_CM, "worst %.3f cm at %s" % (d, f))
    gate("Arm_L to IK: no new animation layer", sorted(cmds.ls(type="animLayer")) == layers_before,
         sorted(set(cmds.ls(type="animLayer")) ^ set(layers_before)))
    tab_attrs = len(cmds.animLayer(tab_root, query=True, attribute=True) or [])
    gate("Arm_L to IK: nothing was added to the tab's base holder", tab_attrs == tab_attrs_before,
         "%d -> %d" % (tab_attrs_before, tab_attrs))
    gate("Arm_L is IK", fkik.mode_of(fkik.blend_values(arm)) == fkik.IK, fkik.mode_of(fkik.blend_values(arm)))

    line = connections.switch_arm("L", fkik.FK, rig=rig, highlight=[])
    print("line:", line, flush=True)
    back = sample(probes, frames)
    d, f = worst(before, back)
    gate("and back to FK: the arm keeps what it showed", d <= TOL_CM, "worst %.3f cm at %s" % (d, f))
    tab_attrs = len(cmds.animLayer(tab_root, query=True, attribute=True) or [])
    gate("and back to FK: still nothing on the tab's base holder", tab_attrs == tab_attrs_before,
         "%d -> %d" % (tab_attrs_before, tab_attrs))
    print("%d of %d gates failed" % (RESULTS.count(False), len(RESULTS)), flush=True)


try:
    main()
finally:
    maya.standalone.uninitialize()
    os._exit(0)
