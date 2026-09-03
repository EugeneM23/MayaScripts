"""Live proof for the twist roll limit -- 2026-09-03.

The animator reported arm bones over-twisting on an imported clip. Measured:
`upperarm_twist_01_r.rotateX` steps 223.50 degrees between frames 9 and 10,
because `quatToEuler` wraps the network's angle into (-180, +180] and the
right arm's roll leaves that window. Spec:
docs/superpowers/specs/2026-09-03-twist-roll-limit-design.md

PHASE 1 is READ-ONLY and runs in the animator's own scene: it judges the rig
that is standing there right now with the new functions and asserts they
refuse exactly the segment that whips and accept the other seven. Nothing is
created, nothing is written, the frame and the selection are put back.

PHASE 2 walks the chain `build` itself walks, with the reference `build`
measures, still without creating anything -- because running the real build
here would tear down the animator's rig. What is deliberately NOT covered is
the creation half: that wants a throwaway skeleton in an empty scene.

Send through the command port. Reads with getAttr(time=...) and never moves
the time slider.
"""

import math

import maya.cmds as cmds
import maya.api.OpenMaya as om

from maya_overrig import twist

PHASES = (1, 2)

# What was measured in the animator's scene on 2026-09-03. The refusal must
# land on upperarm_r and nowhere else.
EXPECT_REFUSED = ("upperarm_r",)
EXPECT_RIGGABLE = ("upperarm_l", "lowerarm_l", "lowerarm_r",
                   "thigh_l", "calf_l", "thigh_r", "calf_r")

failures = []
checked = 0


def gate(name, ok, detail=""):
    global checked
    checked += 1
    print("  %-4s %-58s %s" % ("ok" if ok else "FAIL", name, detail))
    if not ok:
        failures.append(name)


def hdr(text):
    print("")
    print("=" * 78)
    print(text)
    print("=" * 78)


def one(leaf):
    found = cmds.ls(leaf, long=True, type="joint") or []
    return found[0] if len(found) == 1 else None


def scene_size():
    return len(cmds.ls())


NOW = cmds.currentTime(query=True)
SEL = cmds.ls(selection=True, long=True) or []
AUTOKEY = cmds.autoKeyframe(query=True, state=True)
SIZE_BEFORE = scene_size()
created = []

try:
    # =====================================================================
    if 1 in PHASES:
        hdr("PHASE 1  the standing rig, judged read-only")

        gate("the new names exist on the module",
             all(hasattr(twist, n) for n in
                 ("lift", "anchored", "excursion", "roll_refusal",
                  "sampled_rolls", "driver_rolls", "ROLL_WINDOW")),
             "ROLL_WINDOW=%s" % getattr(twist, "ROLL_WINDOW", None))

        start, end = 0, 0
        try:
            from maya_overrig import overrig
            start, end = overrig.frame_range()
        except Exception as exc:
            print("  frame_range unavailable (%s), using the playback range"
                  % exc)
            start = cmds.playbackOptions(query=True, min=True)
            end = cmds.playbackOptions(query=True, max=True)
        frames = [start + step for step in range(int(end - start) + 1)]
        print("  frames %s .. %s (%d samples), current %s"
              % (start, end, len(frames), NOW))

        judged = {}
        for segment in twist.SEGMENTS:
            bone = one(segment.bone)
            driver = one(segment.driver)
            if not bone or not driver:
                continue
            # the REAL rig's own reference, so this judges what is standing
            # there rather than a reference of our own invention
            leaf = None
            for child in cmds.listRelatives(bone, children=True, type="joint",
                                            fullPath=True) or []:
                if "_twist_" in child.split("|")[-1]:
                    leaf = child.split("|")[-1]
                    break
            delta_node = "%s_tw_delta" % leaf if leaf else None
            dot_node = "%s_tw_dot" % leaf if leaf else None
            if not (delta_node and cmds.objExists(delta_node)
                    and cmds.objExists(dot_node)):
                continue
            rest = om.MMatrix(cmds.getAttr(delta_node + ".matrixIn[0]"))
            axis = om.MVector(*cmds.getAttr(dot_node + ".input2")[0])
            rolls = twist.driver_rolls(driver, rest, axis, frames)
            judged[segment.bone] = rolls

        gate("every segment of this skeleton was judged",
             len(judged) == 8, "%d segments" % len(judged))

        print("")
        print("  %-13s %10s %10s %10s   %s"
              % ("segment", "min", "max", "span", "verdict"))
        for name, rolls in judged.items():
            over = twist.excursion(rolls)
            print("  %-13s %10.1f %10.1f %10.1f   %s"
                  % (name, min(rolls), max(rolls), max(rolls) - min(rolls),
                     "REFUSED (%.0f over)" % over if over else "riggable"))
        print("")

        for name in EXPECT_REFUSED:
            rolls = judged.get(name)
            gate("%s is refused" % name,
                 bool(rolls) and twist.roll_refusal(rolls) is not None,
                 "span %.1f deg" % (max(rolls) - min(rolls)) if rolls
                 else "not judged")
            if rolls:
                reason = twist.roll_refusal(rolls) or ""
                gate("%s refusal names its number" % name,
                     any(ch.isdigit() for ch in reason), reason[:64])
                gate("%s span is the measured 516 deg" % name,
                     abs((max(rolls) - min(rolls)) - 516.2) < 25.0,
                     "%.1f" % (max(rolls) - min(rolls)))

        for name in EXPECT_RIGGABLE:
            rolls = judged.get(name)
            if not rolls:
                gate("%s was judged" % name, False, "missing")
                continue
            gate("%s is NOT refused" % name,
                 twist.roll_refusal(rolls) is None,
                 "span %.1f deg" % (max(rolls) - min(rolls)))

        rolls = judged.get("upperarm_l")
        if rolls:
            headroom = twist.ROLL_WINDOW - max(abs(min(rolls)), abs(max(rolls)))
            gate("upperarm_l keeps real headroom", headroom > 60.0,
                 "%.1f deg to the clamp" % headroom)

        # the lift did its job: no 360 step survives in the judged sequences
        worst = 0.0
        worst_name = None
        for name, rolls in judged.items():
            for i in range(1, len(rolls)):
                step = abs(rolls[i] - rolls[i - 1])
                if step > worst:
                    worst, worst_name = step, name
        gate("no 360 degree step survives the lift", worst < 200.0,
             "worst %.1f deg on %s" % (worst, worst_name))

        # the anchor is a constant shift and cannot change a verdict's span
        rolls = judged.get("upperarm_r") or []
        if rolls:
            shifted = twist.anchored(rolls, len(rolls) // 2)
            gate("anchoring preserves the span",
                 abs((max(shifted) - min(shifted))
                     - (max(rolls) - min(rolls))) < 1e-9)
            gate("anchoring puts the named sample at zero",
                 abs(shifted[len(rolls) // 2]) < 1e-9)

        # the arithmetic agrees with the network standing in the scene
        leaf = "upperarm_twist_01_r"
        angle_node = "%s_tw_angle" % leaf
        delta_node = "%s_tw_delta" % leaf
        dot_node = "%s_tw_dot" % leaf
        if all(cmds.objExists(n) for n in (angle_node, delta_node, dot_node)):
            axis = om.MVector(*cmds.getAttr(dot_node + ".input2")[0])
            agree = 0
            wrapped = 0
            for frame in frames:
                node_says = cmds.getAttr(angle_node + ".outputRotateX",
                                         time=frame)
                delta = cmds.getAttr(delta_node + ".matrixSum", time=frame)
                ours = twist.sampled_rolls([delta], (axis.x, axis.y, axis.z))[0]
                if abs(node_says - ours) < 0.01:
                    agree += 1
                elif abs(abs(node_says - ours) - 360.0) < 0.01:
                    wrapped += 1
            gate("our arithmetic is the network's, modulo the wrap",
                 agree + wrapped == len(frames),
                 "%d agree, %d differ by exactly 360, %d neither"
                 % (agree, wrapped, len(frames) - agree - wrapped))
            gate("the node really does wrap on this clip", wrapped > 0,
                 "%d of %d frames wrapped" % (wrapped, len(frames)))

    # =====================================================================
    if 2 in PHASES:
        hdr("PHASE 2  build's own call chain, run read-only")
        # Phase 1 exercises the pure functions and the reader against the
        # rig's RECORDED reference. This phase walks the chain `build` walks,
        # with the reference `build` measures -- the one thing phase 1 cannot
        # prove, because running the real build would tear down the
        # animator's rig.
        import inspect

        source = inspect.getsource(twist.build)
        gate("build samples the frame range once",
             source.count("overrig.frame_range()") == 1)
        gate("build measures the rest before it creates anything",
             source.index("_local_matrix_inverse(driver)")
             < source.index("_network("))
        gate("build asks roll_refusal about driver_rolls",
             "roll_refusal(driver_rolls(" in source)
        gate("build hands that same rest to _network", "rest=rest" in source)
        signature = inspect.signature(twist._network)
        gate("_network takes a rest that defaults to measuring it",
             "rest" in signature.parameters
             and signature.parameters["rest"].default is None,
             str(signature))

        from maya_overrig import naming

        roots = cmds.ls("|root", long=True) or []
        gate("the character resolves", len(roots) == 1, str(roots))
        if roots:
            scene_map = naming.hierarchy_map(roots[0])
            found = twist.segments(scene_map)
            gate("segments() finds all eight", len(found) == 8,
                 "%d" % len(found))
            print("")
            print("  %-13s %-4s | %9s %9s | %s"
                  % ("segment", "kind", "min", "max", "verdict"))
            refused = []
            for segment in found:
                bone = scene_map[segment.bone]
                tip = scene_map[segment.tip]
                driver = scene_map[segment.driver]
                span = twist._world_point(tip) - twist._world_point(bone)
                if span.length() < 1e-6:
                    continue
                along = span / span.length()
                local = twist._to_frame(along, twist._parent_of(driver))
                rest = twist._local_matrix_inverse(driver)
                rolls = twist.driver_rolls(driver, rest, local, frames)
                reason = twist.roll_refusal(rolls)
                if reason:
                    refused.append(segment.bone)
                print("  %-13s %-4s | %9.1f %9.1f | %s"
                      % (segment.bone, segment.kind[:3], min(rolls),
                         max(rolls), reason[:42] if reason else "riggable"))
                if segment.bone == "thigh_r":
                    # the anchor: at the build frame the delta is the
                    # identity, so a single-sample call must read exactly 0
                    single = twist.driver_rolls(driver, rest, local, [NOW])
                    gate("the build-pose anchor reads exactly zero",
                         abs(single[0]) < 1e-6, "%.12f" % single[0])
            print("")
            gate("the chain refuses exactly the segment that whips",
                 refused == list(EXPECT_REFUSED), str(refused))

finally:
    for uuid in created:
        for path in cmds.ls(uuid, long=True) or []:
            try:
                if cmds.objExists(path):
                    cmds.delete(path)
            except Exception as exc:
                print("  cleanup failed for %s: %s" % (path, exc))
    for label, step in (("autoKey", lambda: cmds.autoKeyframe(state=AUTOKEY)),
                        ("frame", lambda: cmds.currentTime(NOW)),
                        ("selection",
                         lambda: (cmds.select(SEL, replace=True) if SEL
                                  else cmds.select(clear=True)))):
        try:
            step()
        except Exception as exc:
            print("  restoring %s failed: %s" % (label, exc))

    hdr("SCENE LEFT AS FOUND")
    gate("no node was created or destroyed", scene_size() == SIZE_BEFORE,
         "%d before, %d after" % (SIZE_BEFORE, scene_size()))
    gate("the frame is back", abs(cmds.currentTime(query=True) - NOW) < 1e-9,
         str(cmds.currentTime(query=True)))
    gate("autoKey is back",
         cmds.autoKeyframe(query=True, state=True) == AUTOKEY)
    gate("the selection is back",
         len(cmds.ls(selection=True, long=True) or []) == len(SEL))

    hdr("RESULT")
    print("  %d of %d gates failed" % (len(failures), checked))
    for name in failures:
        print("    FAILED: %s" % name)

print("__SCRIPT_END__")
