"""Live gates for the Tools card (2026-10-12) - the animator's check, in their own Maya.

    exec(compile(open(r"C:/!!!Work/MayaScripts/docs/superpowers/plans/verify_tools_card.py").read(),
                 "verify_tools_card.py", "exec"), {"__name__": "__main__"})

Written and NOT run by the session that built the card (the live checks are the animator's,
2026-10-09). Works on a SANDBOX cube it creates and deletes; the scene's own nodes, the frame,
the selection and autoKey are left as found. The scene half is proven standalone by
verify_knots.py (82 gates); this proves the card in the hub: it opens on Tools, its buttons are
Maya's own under the skin, Knot / Offset / Finish / Bake / Remove pressed through Qt act on
the selection, the subtitle and the offset button follow the scene.
"""
import sys

import maya.cmds as cmds
import maya.api.OpenMaya as om

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)

FAILS = []
COUNT = [0]


def gate(ok, msg):
    COUNT[0] += 1
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    if not ok:
        FAILS.append(COUNT[0])


def qt_click(name):
    """Click Maya's control `name` through Qt - found again by name right before (trap 148)."""
    from maya import OpenMayaUI as omui
    from PySide6 import QtWidgets
    import shiboken6
    import maya_hubcopy
    ptr = omui.MQtUtil.findControl(maya_hubcopy.resolve(name))
    if not ptr:
        return False
    widget = shiboken6.wrapInstance(int(ptr), QtWidgets.QAbstractButton)
    widget.click()
    QtWidgets.QApplication.processEvents()
    return True


def pivot_track(node, frames):
    out = []
    for f in frames:
        cmds.currentTime(f, update=True)
        out.append(om.MVector(*cmds.xform(node, query=True, worldSpace=True, rotatePivot=True)))
    return out


def main():
    import maya_hub
    from maya_tools import knotplan as plan, knots, panel
    frame = cmds.currentTime(query=True)
    selection = cmds.ls(selection=True, long=True) or []
    auto = cmds.autoKeyframe(query=True, state=True)
    made = []
    try:
        cube = cmds.polyCube(name="skeldarToolsVerifyCube")[0]
        made.append(cmds.ls(cube, uuid=True)[0])
        cube = cmds.ls(cube, long=True)[0]
        for t, x in ((0, 0.0), (10, 15.0), (20, 0.0)):
            cmds.setKeyframe(cube, attribute="tx", time=t, value=x)
        frames = list(range(0, 21))
        before = pivot_track(cube, frames)
        cmds.currentTime(5)

        maya_hub.show(panel.HUB_SECTION)
        gate(panel.is_open(), "the hub opens on Tools")
        gate(all(cmds.control(n, exists=True) for n in (
            panel.KNOT_BTN, panel.OFFSET_BTN, panel.ORIENT_BTN, panel.LOCAL_BTN,
            panel.WORLD_BTN, panel.BAKE_BTN, panel.REMOVE_BTN)), "every button stands")

        cmds.select(cube, replace=True)
        gate(qt_click(panel.KNOT_BTN), "Knot clicked through Qt")
        mine = [k for k in knots.knots() if knots.source_of(k) == cube]
        gate(len(mine) == 1, "a knot on the cube: %s" % mine)
        after = pivot_track(cube, frames)
        worst = max((a - b).length() for a, b in zip(before, after))
        gate(worst < 1e-3, "nothing moved (%.6f cm)" % worst)
        gate("knot" in cmds.text(panel.SUBTITLE, query=True, label=True),
             "the subtitle counts it: %s" % cmds.text(panel.SUBTITLE, query=True, label=True))

        cmds.select(cube, replace=True)
        qt_click(panel.REMOVE_BTN)
        gate(not [k for k in knots.knots() if knots.source_of(k) == cube], "Remove took it")

        cmds.select(cube, replace=True)
        qt_click(panel.OFFSET_BTN)
        gate(knots.waiting() and cmds.button(panel.OFFSET_BTN, query=True, label=True)
             == plan.offset_label(True), "Offset waits, the button reads Finish")
        qt_click(panel.OFFSET_BTN)
        mine = [k for k in knots.knots() if knots.source_of(k) == cube]
        gate(len(mine) == 1 and not knots.waiting()
             and cmds.button(panel.OFFSET_BTN, query=True, label=True) == plan.offset_label(False),
             "Finish made the knot, the button reads Offset again")
        cmds.select(cube, replace=True)
        qt_click(panel.BAKE_BTN)
        after = pivot_track(cube, frames)
        worst = max((a - b).length() for a, b in zip(before, after))
        gate(not knots.knots() or not [k for k in knots.knots() if knots.source_of(k) == cube],
             "Bake took the knot")
        gate(worst < 1e-3, "the cube plays what it played (%.6f cm)" % worst)
        line = cmds.text(panel.STATUS, query=True, label=True)
        gate(line.startswith("Baked"), "the line: %s" % line)

        target = cmds.polyCube(name="skeldarToolsVerifyTarget")[0]
        made.append(cmds.ls(target, uuid=True)[0])
        target = cmds.ls(target, long=True)[0]
        cmds.select([cube, target], replace=True)
        qt_click(panel.ACROSS_BTN)
        mine = [k for k in knots.knots() if knots.source_of(k) == cube]
        gate(len(mine) == 1 and cmds.listRelatives(mine[0], parent=True, fullPath=True)[0]
             == target, "Across: a knot inside the target")
        cmds.select(cube, replace=True)
        qt_click(panel.REMOVE_BTN)
        gate(not [k for k in knots.knots() if knots.source_of(k) == cube], "Remove took it")
    finally:
        for uuid in made:
            found = cmds.ls(uuid, long=True)
            if found:
                try:
                    cmds.delete(found)
                except Exception:
                    pass
        try:
            cmds.currentTime(frame)
        except Exception:
            pass
        try:
            cmds.select([s for s in selection if cmds.objExists(s)], replace=True) \
                if selection else cmds.select(clear=True)
        except Exception:
            pass
        try:
            cmds.autoKeyframe(state=auto)
        except Exception:
            pass
    print("verify_tools_card: %d gates, %d failed" % (COUNT[0], len(FAILS)))


if __name__ == "__main__":
    main()
