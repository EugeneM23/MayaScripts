"""How big the Creep's and the Orc's clavicle and shoulder controls must be to be seen -- mayapy standalone.

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/measure_control_sizes.py [assets dir]

2026-09-30, the animator: «У орка и крипа контролы ключиц плечей не видны они внутри геометрии тела»; asked,
«Увеличить под тело»: each control's drawing grows about its own origin until it is seen at least as well
as the same control on Manny, who is the standard (nobody complained about his).

**Seen** is measured the way a viewport sees it: for every point of the curve (64 per shape), the share of
32 directions (a Fibonacci sphere) along which a ray from the point reaches open space without meeting the
character's own visible meshes.  A point inside a closed body scores 0, a point just off a surface ~0.5.  It
needs no inside/outside test, so open or overlapping meshes (the Creep has five, overlapping) do not fool it.

For each control of CONTROLS on the Creep and the Orc D: the smallest factor on a 0.05 grid (1.0 .. 3.0)
at which BOTH sides are seen at least as well as Manny's pair, the same factor for L and R (the rig stays
symmetric).  Prints the table `make_control_sizes.py` applies, as radii (the largest CV distance from the
control's origin, object space) so a second application is a no-op.  Read-only: rigs are added to an empty
scene and nothing is saved.
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
import maya_rigs  # noqa: E402
from maya_scenesetup import catalog, character  # noqa: E402

ASSETS = sys.argv[1].replace("\\", "/") if len(sys.argv) > 1 else None
REFERENCE = "Manny_Rig"
TARGETS = ("Creep_Rig", "Orc_D_Rig")
CONTROLS = ("FKScapula", "FKShoulder")
SIDES = ("L", "R")
SAMPLES = 64
GRID = [round(1.0 + 0.05 * i, 2) for i in range(41)]
ACCEL = om.MFnMesh.autoUniformGridParams()


def fibonacci(n):
    out = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        y = 1.0 - 2.0 * (i + 0.5) / n
        r = math.sqrt(1.0 - y * y)
        out.append(om.MFloatVector(math.cos(golden * i) * r, y, math.sin(golden * i) * r))
    return out


DIRS = fibonacci(32)


def dag(node):
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)


def visible(path):
    while path:
        if cmds.attributeQuery("visibility", node=path, exists=True) and not cmds.getAttr(path + ".visibility"):
            return False
        up = cmds.listRelatives(path, parent=True, fullPath=True)
        path = up[0] if up else None
    return True


def meshes(namespace):
    return [om.MFnMesh(dag(s)) for s in cmds.ls(namespace + ":*", type="mesh", long=True) or []
            if not cmds.getAttr(s + ".intermediateObject") and visible(s)]


def seen(fns, points):
    """Mean share of DIRS along which a ray from each point meets no mesh."""
    free = 0
    for p in points:
        for d in DIRS:
            src = om.MFloatPoint(p.x + d.x * 0.01, p.y + d.y * 0.01, p.z + d.z * 0.01)
            if not any(fn.anyIntersection(src, d, om.MSpace.kWorld, 1e4, False, accelParams=ACCEL)
                       for fn in fns):
                free += 1
    return free / float(len(points) * len(DIRS))


def shapes(ctrl):
    return [s for s in cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve", fullPath=True) or []
            if not cmds.getAttr(s + ".intermediateObject")]


def samples(ctrl, factor=1.0):
    """World points along the control's curves with its CVs scaled `factor` about the control's origin."""
    wm = om.MMatrix(cmds.getAttr(ctrl + ".worldMatrix[0]"))
    pts = []
    for s in shapes(ctrl):
        fn = om.MFnNurbsCurve(dag(s))
        lo, hi = fn.knotDomain
        for i in range(SAMPLES):
            local = fn.getPointAtParam(lo + (hi - lo) * i / float(SAMPLES), om.MSpace.kObject)
            pts.append(om.MPoint(local.x * factor, local.y * factor, local.z * factor) * wm)
    return pts


def radius(ctrl):
    return max(om.MVector(p).length() for s in shapes(ctrl)
               for p in om.MFnNurbsCurve(dag(s)).cvPositions(om.MSpace.kObject))


def origin_is_pivot(ctrl):
    rp = cmds.xform(ctrl, q=True, os=True, rp=True)
    return max(abs(v) for v in rp) < 1e-6


cmds.file(new=True, force=True)
if ASSETS:   # measure other copies of the assets (a control run on the old files)
    catalog_file = catalog.character_file
    catalog.character_file = lambda e: ASSETS + "/" + e.file if e.key in TARGETS else catalog_file(e)
for key, x in ((REFERENCE, -200.0), (TARGETS[0], 0.0), (TARGETS[1], 200.0)):
    character.add_character(catalog.character_by_key(key), at=(x, 0.0, 0.0))
rigs = dict((r.namespace, r) for r in maya_rigs.rigs())
fns = dict((key, meshes(key)) for key in (REFERENCE,) + TARGETS)
print("// meshes:", dict((k, len(v)) for k, v in fns.items()))

reference = {}
for name in CONTROLS:
    for side in SIDES:
        ctrl = cmds.ls("%s:%s_%s" % (REFERENCE, name, side), long=True)[0]
        reference[name, side] = seen(fns[REFERENCE], samples(ctrl))
    print("// %s %s: seen %.3f / %.3f, radius %.4f" % (REFERENCE, name, reference[name, "L"], reference[name, "R"],
                                                      radius(cmds.ls("%s:%s_L" % (REFERENCE, name))[0])))

table = {}
for key in TARGETS:
    for name in CONTROLS:
        ctrls = [cmds.ls("%s:%s_%s" % (key, name, side), long=True)[0] for side in SIDES]
        for c in ctrls:
            if not origin_is_pivot(c):
                raise RuntimeError("%s: pivot off its origin - scaling the CVs would move the drawing" % c)
        found, row = None, []
        for f in GRID:
            scores = [seen(fns[key], samples(c, f)) for c in ctrls]
            row.append("x%.2f %.3f/%.3f" % (f, scores[0], scores[1]))
            if all(s >= reference[name, side] for s, side in zip(scores, SIDES)):
                found = f
                break
        r0 = [radius(c) for c in ctrls]
        print("// %s %s: now radius %.4f/%.4f -> %s" % (key, name, r0[0], r0[1], " | ".join(row[:1] + row[-3:])))
        if found is None:
            raise RuntimeError("%s %s never reaches Manny's %.3f" % (key, name, min(reference[name, s] for s in SIDES)))
        table[key, name] = (found, r0[0] * found)
print("TABLE")
for (key, name), (f, r) in sorted(table.items()):
    print("    (%r, %r): %.6f,   # x%.2f" % (key, name, r, f))
