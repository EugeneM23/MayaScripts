"""The Root control: the game `root` bone's own control, under Main (2026-10-21).

The animator: «Для кости Root давай сделаем отдельный контроллер в паренте главного, что бы кость
рута не двигала нашу камеру там где нам этого не нужно». Every AdvancedSkeleton rig of ours drives
its game `root` from `Main` (a parentConstraint, the rig build's `root ← Main`). `ensure(rig)`
puts a yellow control `<ns>:Root_ctrl` under Main at identity, member of the rig's ControlSet,
and makes the root follow IT instead (the constraint made again with its offset kept: the control
stands where Main does, so nothing moves). Main still carries everything; the Root control moves
the root bone alone - the camera's control lives under Main, beside it, and does not follow it.

Made on Add Character for every rig, and on the first Camera Setup / 1P Setup of a rig added
before (`ensure` is idempotent: found by its marker under Main).
"""

import maya.cmds as cmds

from maya_scenesetup import curvectrl

MARKER = "skeldarRootControl"
NAME = "Root_ctrl"
MAIN_RADIUS = 40.5236           # Manny's Main circle: every rig's since 2026-09-30
SHARE = 0.45                    # the control's half side over Main's radius


def leaf(path):
    return (path or "").split("|")[-1].split(":")[-1]


def _has(node, attr):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery(attr, node=node,
                                                                        exists=True)


def find(rig):
    """The rig's Root control, long path, or None."""
    main = getattr(rig, "main", None)
    if not main or not cmds.objExists(main):
        return None
    for child in cmds.listRelatives(main, children=True, type="transform",
                                    fullPath=True) or []:
        if _has(child, MARKER):
            return child
    return None


def _main_constraint(root, main):
    """The parentConstraint on `root` whose one target is `main`, or None."""
    main_long = (cmds.ls(main, long=True) or [main])[0]
    for con in cmds.listRelatives(root, children=True, type="parentConstraint",
                                  fullPath=True) or []:
        targets = cmds.parentConstraint(con, query=True, targetList=True) or []
        longs = [(cmds.ls(t, long=True) or [t])[0] for t in targets]
        if longs == [main_long]:
            return con
    return None


def _size(main):
    box = curvectrl.local_box(main)
    if not box:
        return MAIN_RADIUS * SHARE
    lo, hi = box
    radius = max(hi[0] - lo[0], hi[2] - lo[2]) / 2.0
    return (radius or MAIN_RADIUS) * SHARE


def ensure(rig):
    """(the Root control or None, the words). Made when the rig's root follows Main."""
    made = find(rig)
    if made:
        return made, ""
    root, main = getattr(rig, "skeleton_root", None), getattr(rig, "main", None)
    if not root or not main or not cmds.objExists(root) or not cmds.objExists(main):
        return None, "no root or Main"
    con = _main_constraint(root, main)
    if not con:
        return None, "%s does not follow Main" % leaf(root)
    skip_t = [a for a in "xyz"
              if not cmds.listConnections("%s.constraintTranslate%s" % (con, a.upper()),
                                          source=False, destination=True)]
    skip_r = [a for a in "xyz"
              if not cmds.listConnections("%s.constraintRotate%s" % (con, a.upper()),
                                          source=False, destination=True)]
    short = main.split("|")[-1]
    namespace = short.rsplit(":", 1)[0] if ":" in short else ""
    name = (":" + namespace + ":" + NAME) if namespace else NAME
    ctrl = curvectrl.make(name, main, curvectrl.root_arrow(_size(main)), curvectrl.YELLOW)
    cmds.addAttr(ctrl, longName=MARKER, attributeType="bool", defaultValue=True)
    for attr in ("scaleX", "scaleY", "scaleZ", "visibility"):
        cmds.setAttr(ctrl + "." + attr, keyable=False, channelBox=False)
    cmds.delete(con)
    cmds.parentConstraint(ctrl, root, maintainOffset=True,
                          skipTranslate=skip_t or "none", skipRotate=skip_r or "none")
    control_set = getattr(rig, "control_set", None)
    if control_set and cmds.objExists(control_set):
        cmds.sets(ctrl, addElement=control_set)
    return ctrl, "%s made under Main, %s follows it" % (leaf(ctrl), leaf(root))
