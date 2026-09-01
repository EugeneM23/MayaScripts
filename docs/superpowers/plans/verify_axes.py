"""Live verification for the FK controller axis alignment.

Sent through the command port against a rig that `Build FK` has just built.
Four gates, in order of what matters:

1. Drift -- running the alignment again must not move a single bone at a
   single frame. The operation is world-preserving by construction, and this
   is where that claim is tested against a real scene rather than a matrix.
2. Zero -- every controller reads (0, 0, 0) at the build pose.
3. Symmetry -- equal channel values on both sides give a mirrored pose. This
   is what "symmetric axes" means in practice, and it is measured on joint
   positions, which no convention argument can dispute.
4. Animbot -- its mirror must land the right arm where a mirror would put it.
   Animbot guesses its channel signs from the rig; if this gate fails while
   gate 3 passes, the guess is wrong rather than the rig, and Animbot's own
   `Snapshot Mirror Settings` is the cure -- a button the user presses, since
   calling it from here blocks Maya on a modal dialog.

Everything that changes the scene runs inside an undo chunk and is undone.
"""

import traceback

OUT = r"C:\Users\MYPC~1\AppData\Local\Temp\claude\C-----Work-MayaScripts\878ca35d-9195-4732-bc12-8ac7b860669b\scratchpad\verify_axes_out.txt"

lines = []


def log(text=""):
    lines.append(text)


try:
    import sys

    if r"C:/!!!Work/MayaScripts/SkeldarAnim" not in sys.path:
        sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")

    import maya.cmds as cmds
    import maya.utils
    import maya.api.OpenMaya as om

    from maya_overrig import bodymap, builder, fkcontrols, naming

    def flush(rounds=8):
        from PySide6 import QtWidgets
        for _ in range(rounds):
            QtWidgets.QApplication.processEvents()
            maya.utils.processIdleEvents()
        cmds.refresh()

    # --- the bound skeleton, resolved the way the panel does -------------
    root = builder.character_roots()[0]
    mapping = naming.hierarchy_map(root)
    prefix = naming.detect_prefix(list(mapping),
                                  {b.joint for b in bodymap.BUTTONS})
    SCENE = naming.strip_prefix(mapping, prefix)
    log("skeleton root: %s, %d joints mapped" % (root, len(SCENE)))

    frame = cmds.currentTime(query=True)
    start = int(cmds.playbackOptions(query=True, minTime=True))
    end = int(cmds.playbackOptions(query=True, maxTime=True))
    log("timeline %d..%d, current frame %s" % (start, end, frame))

    BONES = [SCENE[j] for _, chain in fkcontrols.CHAINS for j in chain
             if j in SCENE and cmds.objExists(SCENE[j])]

    def sample_bones():
        """Every bone's world matrix at every frame."""
        table = {}
        for f in range(start, end + 1):
            cmds.currentTime(f, edit=True)
            table[f] = [cmds.xform(b, query=True, worldSpace=True, matrix=True)
                        for b in BONES]
        cmds.currentTime(frame, edit=True)
        return table

    def deviation(before, after):
        worst = 0.0
        for f, rows in before.items():
            for a, b in zip(rows, after[f]):
                worst = max(worst, max(abs(x - y) for x, y in zip(a, b)))
        return worst

    # --- gate 1: drift ---------------------------------------------------
    log()
    log("=== gate 1: drift ===")
    before = sample_bones()
    cmds.undoInfo(openChunk=True, chunkName="verify_axes_drift")
    try:
        again = fkcontrols.align_controllers(SCENE)
    finally:
        cmds.undoInfo(closeChunk=True)
    after = sample_bones()
    drift = deviation(before, after)
    log("  re-aligned %d controller(s); worst bone deviation over %d frames: "
        "%.3e" % (again, len(before), drift))
    log("  %s (gate: below 1e-4)" % ("PASS" if drift < 1e-4 else "FAIL"))
    cmds.undo()
    cmds.currentTime(frame, edit=True)

    # --- gate 2: zero at the build pose ---------------------------------
    log()
    log("=== gate 2: controllers read zero at the build pose ===")
    worst_zero, offender = 0.0, None
    for _, chain in fkcontrols.CHAINS:
        for joint in chain:
            ctrl = fkcontrols.controller_name(joint)
            # `root` is a plain transform with no jointOrient to carry the
            # change, so the alignment skips it; it has no mirror partner.
            if not cmds.objExists(ctrl) or not cmds.attributeQuery(
                    "jointOrient", node=ctrl, exists=True):
                continue
            largest = max(abs(v) for v in cmds.getAttr(ctrl + ".rotate")[0])
            if largest > worst_zero:
                worst_zero, offender = largest, ctrl
    log("  largest rotate value: %.4f (%s)" % (worst_zero, offender))
    log("  %s (gate: below 0.01)"
        % ("PASS" if worst_zero < 0.01 else "FAIL"))

    # --- gate 3: equal values give a mirrored pose -----------------------
    log()
    log("=== gate 3: equal values on both sides mirror the pose ===")
    WATCH = ("lowerarm", "hand", "middle_02")

    def in_root(node):
        inv = om.MMatrix(cmds.xform(SCENE["root"], query=True,
                                    worldSpace=True, matrix=True)).inverse()
        p = cmds.xform(node, query=True, worldSpace=True, translation=True)
        v = om.MPoint(p[0], p[1], p[2]) * inv
        return (v.x, v.y, v.z)

    ARM_L = [fkcontrols.controller_name(j) for j in
             ("clavicle_l", "upperarm_l", "lowerarm_l", "hand_l")]
    ARM_R = [n.replace("_l_", "_r_") for n in ARM_L]

    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    selection = cmds.ls(selection=True, long=True)

    cmds.undoInfo(openChunk=True, chunkName="verify_axes_values")
    try:
        POSE = {"upperarm": (25.0, -40.0, 15.0),
                "lowerarm": (0.0, 0.0, -55.0)}
        for bone, values in POSE.items():
            for side in ("l", "r"):
                cmds.setAttr(
                    fkcontrols.controller_name("%s_%s" % (bone, side))
                    + ".rotate", *values)
        worst = 0.0
        for w in WATCH:
            left = list(in_root(SCENE[w + "_l"]))
            right = in_root(SCENE[w + "_r"])
            left[0] *= -1.0
            err = max(abs(a - b) for a, b in zip(left, right))
            worst = max(worst, err)
            log("  %-11s want(%8.2f,%8.2f,%8.2f) got(%8.2f,%8.2f,%8.2f) "
                "err %.4f" % ((w + "_r",) + tuple(left) + tuple(right)
                              + (err,)))
        log("  worst %.4f -> %s (gate: below 0.5)"
            % (worst, "PASS" if worst < 0.5 else "FAIL"))
    finally:
        cmds.undoInfo(closeChunk=True)
    cmds.undo()
    cmds.currentTime(frame, edit=True)

    # --- gate 4: Animbot -------------------------------------------------
    log()
    log("=== gate 4: Animbot mirror ===")
    log("  correct pattern for these controllers is (+rx, +ry, +rz) --")
    log("  equal values, since gate 3 holds.")
    from animBot._api.core import CORE

    cmds.undoInfo(openChunk=True, chunkName="verify_axes_animbot")
    try:
        cmds.setAttr("upperarm_l_FK_ctrl.rotate", 25.0, -40.0, 15.0)
        cmds.setAttr("lowerarm_l_FK_ctrl.rotate", 0.0, 0.0, -55.0)
        cmds.setKeyframe(["upperarm_l_FK_ctrl", "lowerarm_l_FK_ctrl"],
                         attribute="rotate", time=frame)
        want = {}
        for w in WATCH:
            p = in_root(SCENE[w + "_l"])
            want[w] = (-p[0], p[1], p[2])

        cmds.select(ARM_L + ARM_R, replace=True)
        CORE.mirror.mirrorAllKeys_click()
        flush()
        cmds.currentTime(frame, edit=True)

        worst = 0.0
        for w in WATCH:
            got = in_root(SCENE[w + "_r"])
            err = max(abs(a - b) for a, b in zip(want[w], got))
            worst = max(worst, err)
            log("  %-11s want(%8.2f,%8.2f,%8.2f) got(%8.2f,%8.2f,%8.2f) "
                "err %.3f" % ((w + "_r",) + want[w] + got + (err,)))
        log("  worst %.3f -> %s (gate: below 0.5)"
            % (worst, "PASS" if worst < 0.5 else "FAIL"))
        for n in ARM_R:
            log("    %-22s (%+8.2f,%+8.2f,%+8.2f)"
                % ((n,) + tuple(cmds.getAttr(n + ".rotate")[0])))
    finally:
        cmds.undoInfo(closeChunk=True)

    cmds.undo()
    flush()
    cmds.currentTime(frame, edit=True)
    cmds.autoKeyframe(state=auto)
    if selection:
        cmds.select(selection, replace=True)
    else:
        cmds.select(clear=True)
    log("  scene restored")
    log()
    log("VERIFY DONE")
except Exception:
    log(traceback.format_exc())

with open(OUT, "w") as handle:
    handle.write("\n".join(lines))
