"""mayapy standalone: a knot + Aim Mode scene imported as a tab loses every marker, `relink.heal`
gives them back, and Bake refuses a knot whose object cannot be named instead of deleting it.

    mayapy -I docs/superpowers/plans/relink/verify_relink_import.py <repo>/SkeldarAnim <scratch dir>
"""

import os
import sys

PLUGIN, SCRATCH = sys.argv[1], sys.argv[2]
sys.path.insert(0, PLUGIN)

import maya.standalone  # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402

from maya_tools import knotplan as plan, knots, relink  # noqa: E402
from maya_scenesetup import weaponaim  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print("%s  %s %s" % ("PASS" if ok else "FAIL", name, detail))


def mark(node, attr, value):
    if not cmds.attributeQuery(attr, node=node, exists=True):
        cmds.addAttr(node, longName=attr, dataType="string")
    cmds.setAttr(node + "." + attr, value, type="string")


def uid(node):
    return cmds.ls(node, uuid=True)[0]


#  the scene as the tools leave it: Dagger riding Dagger_knotOffset, Aim Mode through the knot
dagger = cmds.spaceLocator(name="DaggerMesh")[0]
group = cmds.group(empty=True, name="Knots")
top = cmds.spaceLocator(name="DaggerMesh_knotOffset")[0]
top = cmds.parent(top, group)[0]
mark(top, plan.KIND_MARKER, "offset")
mark(top, plan.SOURCE_MARKER, uid(dagger))
con = cmds.parentConstraint(top, dagger)[0]
mark(con, plan.OF_MARKER, uid(top))
aim_group = cmds.group(empty=True, name="DaggerMesh_aim1", parent=group)
mark(aim_group, weaponaim.KIND.marker, uid(dagger))
target = cmds.spaceLocator(name="DaggerMesh_aimTarget")[0]
cmds.parent(target, aim_group)
aim = cmds.aimConstraint("DaggerMesh_aimTarget", top)[0]
mark(aim, weaponaim.KIND.con_marker, uid(dagger))
leftover = cmds.group(empty=True, name="DaggerMesh_aim", parent=group)
mark(leftover, weaponaim.KIND.marker, "64979533-4CD4-B0BC-EDF2-3E82EC71A6AB")

path = os.path.join(SCRATCH, "relink_src.ma").replace("\\", "/")
cmds.file(rename=path)
cmds.file(save=True, type="mayaAscii", force=True)
cmds.file(new=True, force=True)
cmds.file(path, i=True, namespace="tab1")

ns = "tab1:"
d, t = cmds.ls(ns + "DaggerMesh", long=True)[0], cmds.ls(ns + "DaggerMesh_knotOffset", long=True)[0]
check("an import kills the knot's source marker", knots.source_of(t) is None)
check("an import kills the aim group's marker", not weaponaim.is_aimed(d))

written = relink.heal("tab1")
check("heal writes the four markers, not the leftover", written == 4, "(%d)" % written)
check("the knot knows its object again", knots.source_of(t) == d, knots.source_of(t))
check("the object knows its knot again", knots.driving(d) == [t], knots.driving(d))
check("Aim Mode is seen again", weaponaim.group_of(d) is not None)
check("the empty leftover group is left dead",
      not cmds.ls(cmds.getAttr(ns + "DaggerMesh_aim." + weaponaim.KIND.marker)))
check("a second heal finds nothing", relink.heal("tab1") == 0)

#  a knot whose object nothing can name: Bake refuses and keeps it
cmds.setAttr(t + "." + plan.SOURCE_MARKER, "ABCDEF01-2345-6789-ABCD-EF0123456789", type="string")
cmds.delete(cmds.ls(ns + "DaggerMesh_parentConstraint1"))
other = cmds.spaceLocator(name="Other")[0]
cmds.parentConstraint(t, other)
line = knots.bake([t])
check("Bake refuses a knot whose object is lost", line.startswith("DaggerMesh_knotOffset"), line)
check("and keeps the knot", bool(cmds.ls(t)))

maya.standalone.uninitialize()
print("%d/%d" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
