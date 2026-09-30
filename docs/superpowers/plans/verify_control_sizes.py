"""The Creep's and the Orc's clavicle and shoulder controls are seen -- mayapy STANDALONE (it adds rigs).

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_control_sizes.py <old assets dir>

2026-09-30 (spec 2026-09-30-clavicle-shoulder-control-size-design.md).  `<old assets dir>` holds
Creep_Rig.ma and Orc_D_Rig.ma from before make_control_sizes.py: the control, and the procedure step's
input.  "Seen" is measure_control_sizes.py's measure: the share of 32 directions along which a ray from a
point of the curve meets none of the character's visible meshes, averaged over the curve.
"""
import math
import re
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
OLD = sys.argv[1].replace("\\", "/")
import maya_rigs  # noqa: E402
from maya_scenesetup import catalog, character  # noqa: E402

RADII = {"Creep_Rig": {"FKScapula": 16.183303, "FKShoulder": 20.707995},
         "Orc_D_Rig": {"FKScapula": 16.183303, "FKShoulder": 22.590540}}
NAMES = ("FKScapula", "FKShoulder")
SIDES = ("L", "R")
ROWS = (("Manny_Rig", -200.0), ("Creep_Rig", 0.0), ("Orc_D_Rig", 200.0))
ACCEL = om.MFnMesh.autoUniformGridParams()
FAILS = []
TOTAL = 9
NS = {}


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(n)


def fibonacci(n):
    golden = math.pi * (3.0 - math.sqrt(5.0))
    out = []
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


def meshes(ns):
    return [om.MFnMesh(dag(s)) for s in cmds.ls(ns + ":*", type="mesh", long=True) or []
            if not cmds.getAttr(s + ".intermediateObject") and visible(s)]


def shapes(ctrl):
    return [s for s in cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve", fullPath=True) or []
            if not cmds.getAttr(s + ".intermediateObject")]


def seen(fns, ctrl):
    pts = []
    for s in shapes(ctrl):
        fn = om.MFnNurbsCurve(dag(s))
        lo, hi = fn.knotDomain
        pts += [fn.getPointAtParam(lo + (hi - lo) * i / 64.0, om.MSpace.kWorld) for i in range(64)]
    free = 0
    for p in pts:
        for d in DIRS:
            src = om.MFloatPoint(p.x + d.x * 0.01, p.y + d.y * 0.01, p.z + d.z * 0.01)
            if not any(fn.anyIntersection(src, d, om.MSpace.kWorld, 1e4, False, accelParams=ACCEL) for fn in fns):
                free += 1
    return free / float(len(pts) * len(DIRS))


def radius(ctrl):
    return max(om.MVector(p).length() for s in shapes(ctrl)
               for p in om.MFnNurbsCurve(dag(s)).cvPositions(om.MSpace.kObject))


def add_three(assets=None):
    cmds.file(new=True, force=True)
    original = catalog.character_file
    if assets:
        catalog.character_file = lambda e: assets + "/" + e.file if e.key in RADII else original(e)
    try:
        for key, x in ROWS:
            print("//", character.add_character(catalog.character_by_key(key), at=(x, 0.0, 0.0)))
    finally:
        catalog.character_file = original
    # the rig each key added, by namespace: a new scene can keep a namespace alive (mayaUsd's
    # UsdDefaultRenderSettings lands in the first rig's), and the next Manny arrives as Manny_Rig1
    NS.clear()
    for rig in maya_rigs.rigs():
        NS[re.sub(r"\d+$", "", rig.namespace)] = rig.namespace
    print("// rigs:", NS)
    return dict((key, meshes(NS[key])) for key, _x in ROWS)


def control(key, name, side):
    return cmds.ls("%s:%s_%s" % (NS[key], name, side), long=True)[0]


def turn_measure(key):
    """FKShoulder_L +30 about Z (a bend; its X is the roll, which AS hands to the twist joints): the
    angle upperarm_l turns, and back."""
    ctrl = control(key, "FKShoulder", "L")
    bone = cmds.ls(NS[key] + ":upperarm_l", type="joint", long=True)[0]
    before = om.MTransformationMatrix(om.MMatrix(cmds.getAttr(bone + ".worldMatrix[0]"))).rotation(asQuaternion=True)
    rz = cmds.getAttr(ctrl + ".rotateZ")
    cmds.setAttr(ctrl + ".rotateZ", rz + 30.0)
    cmds.currentTime(1)
    cmds.currentTime(0)
    after = om.MTransformationMatrix(om.MMatrix(cmds.getAttr(bone + ".worldMatrix[0]"))).rotation(asQuaternion=True)
    cmds.setAttr(ctrl + ".rotateZ", rz)
    q = before.inverse() * after
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


# 1-2: the old drawings, the control.
fns = add_three(OLD)
manny = dict(((n, s), seen(fns["Manny_Rig"], control("Manny_Rig", n, s))) for n in NAMES for s in SIDES)
old = dict(((k, n, s), seen(fns[k], control(k, n, s))) for k in RADII for n in NAMES for s in SIDES)
old_turn = dict((k, turn_measure(k)) for k in RADII)
gate(1, all(old[k, n, s] < manny[n, s] for (k, n, s) in old),
     "control: the old drawings seen less than Manny's - %s against Manny %s"
     % (dict(("%s %s_%s" % key, round(v, 3)) for key, v in sorted(old.items())),
        dict(("%s_%s" % key, round(v, 3)) for key, v in sorted(manny.items()))))
gate(2, all(abs(radius(control(k, n, s)) - 9.2476 * (1.0 if n == "FKScapula" else 12.5503 / 9.2476)) < 1e-3
            for k in RADII for n in NAMES for s in SIDES),
     "control: the old files carry AdvancedSkeleton's drawings (9.2476 / 12.5503)")

# 3-4: the procedure's step on the old Creep and the old Orc D, imported plain (as at build time).
P = REPO + "/docs/superpowers/plans/as_creep_rig_procedure.py"
results = []
for key in RADII:
    cmds.file(new=True, force=True)
    cmds.file(OLD + "/" + catalog.character_by_key(key).file, i=True, force=True, executeScriptNodes=False)
    proc = {"__name__": "as_creep_rig_procedure", "__file__": P}
    exec(compile(open(P, encoding="utf-8").read(), P, "exec"), proc)
    if key == "Orc_D_Rig":
        proc["CONTROL_RADII"] = dict(RADII[key])
    first = proc["control_sizes"]()
    second = proc["control_sizes"]()
    radii = dict(("%s_%s" % (n, s), radius("|".join([""] + cmds.ls("%s_%s" % (n, s), long=True)[0].split("|")[1:])))
                 for n in NAMES for s in SIDES)
    results.append((key, first, second, radii))
gate(3, all(abs(r["%s_%s" % (n, s)] - RADII[k][n]) < 1e-6 for k, _f, _s, r in results for n in NAMES for s in SIDES),
     "as_creep_rig_procedure.control_sizes draws them at the table's radii: %s"
     % [(k, dict((c, round(f, 4)) for c, f in first.items())) for k, first, _s, _r in results])
gate(4, all(abs(f - 1.0) < 1e-9 for _k, _f, second, _r in results for f in second.values()),
     "a second control_sizes() changes nothing")

# 5-9: the shipped files.
fns = add_three()
new = dict(((k, n, s), seen(fns[k], control(k, n, s))) for k in RADII for n in NAMES for s in SIDES)
manny2 = dict(((n, s), seen(fns["Manny_Rig"], control("Manny_Rig", n, s))) for n in NAMES for s in SIDES)
gate(5, all(new[k, n, s] >= manny2[n, s] for (k, n, s) in new),
     "every one of the eight is seen at least as well as Manny's: %s against Manny %s"
     % (dict(("%s %s_%s" % key, round(v, 3)) for key, v in sorted(new.items())),
        dict(("%s_%s" % key, round(v, 3)) for key, v in sorted(manny2.items()))))
gate(6, all(abs(radius(control(k, n, "L")) - radius(control(k, n, "R"))) < 1e-9 and
            abs(radius(control(k, n, "L")) - RADII[k][n]) < 1e-6 for k in RADII for n in NAMES),
     "L and R at the same radius, the table's: %s"
     % dict(("%s %s" % (k, n), round(radius(control(k, n, "L")), 4)) for k in RADII for n in NAMES))
gate(7, all(abs(radius(control("Manny_Rig", n, s)) - (12.3966 if n == "FKScapula" else 12.5503)) < 1e-3
            for n in NAMES for s in SIDES),
     "Manny untouched (12.3966 / 12.5503)")
new_turn = dict((k, turn_measure(k)) for k in RADII)
gate(8, all(abs(new_turn[k] - old_turn[k]) < 1e-9 and abs(new_turn[k] - 30.0) < 0.5 for k in RADII),
     "FKShoulder_L +30 about Z turns upperarm_l as before: %s (old %s)"
     % (dict((k, round(v, 6)) for k, v in new_turn.items()), dict((k, round(v, 6)) for k, v in old_turn.items())))
wiring = []
for k in RADII:
    for n in NAMES:
        for s in SIDES:
            for shape in shapes(control(k, n, s)):
                ins = cmds.listConnections(shape, source=True, destination=False, plugs=True, connections=True) or []
                wiring.append(all(p.endswith(".visibility") for p in ins[0::2]))
            wiring.append(cmds.getAttr(control(k, n, s) + ".scale")[0] == (1.0, 1.0, 1.0))
gate(9, all(wiring), "only the drawings changed: each shape's inputs are its visibility, each control's scale 1")
print("%d of %d gates failed %s" % (len(FAILS), TOTAL, FAILS))
