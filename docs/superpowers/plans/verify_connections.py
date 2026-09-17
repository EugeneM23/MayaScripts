"""verify_connections.py - the hands on the weapon and off it, LIVE.

Send through the command port (CLAUDE.md, "Driving the user's live Maya")
with the INSTALLED copy first on sys.path. Live and not standalone because
OverRig's apply_Parent_out/in read the time slider and die in mayapy
("Cannot convert data of type int to type float[]", measured 2026-09-18).

It REFUSES to run in a scene that already holds a rig - it adds a
throwaway Manny_Rig, a sword and keys, and deletes every node it created
afterwards (a UUID diff of the whole scene). Playback range, current time,
autoKey and the selection are put back.

Spec: docs/superpowers/specs/2026-09-18-connections-design.md
"""
import maya.cmds as cmds

FAILED = []
PASSED = []


def gate(n, name, ok, detail=""):
    (PASSED if ok else FAILED).append(n)
    print("%s %2d %s%s" % ("ok  " if ok else "FAIL", n, name,
                           (" - " + str(detail)) if detail else ""))


def world(node, t):
    """The world matrix at `t` after a REAL time change. `getAttr(plug,
    time=t)` does not pull a constraint + IK chain (measured 2026-09-18: the
    weapon nudged 10.000, the hand read 0.000 that way and 10.000 this
    way) - trap 14's family."""
    cmds.currentTime(t - 1)
    cmds.currentTime(t)
    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def worst(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


import maya_rigs
import maya_rig_retarget
from maya_scenesetup import attach, bonedrive, catalog, character, connections as cx, skeleton

if maya_rigs.rigs():
    print("SKIP: the scene already holds a rig (%s) - this verify adds and deletes one"
          % [r.namespace for r in maya_rigs.rigs()])
    print("checks passed: 0 of 0 gates")
else:
    saved = dict(
        rng=(cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True),
             cmds.playbackOptions(q=True, ast=True), cmds.playbackOptions(q=True, aet=True)),
        time=cmds.currentTime(q=True), autokey=cmds.autoKeyframe(q=True, state=True),
        sel=cmds.ls(selection=True, long=True) or [],
        opts={k: (cmds.optionVar(q=cx._OPTIONVAR.format(k)) if cmds.optionVar(exists=cx._OPTIONVAR.format(k)) else None)
              for k in ("right", "left")})
    before = set(cmds.ls(cmds.ls(), uuid=True))
    try:
        cmds.autoKeyframe(state=False)
        #  ast/aet too: OverRig's parent_out bakes across the ANIMATION
        #  range (measured: 743 keys over 0..742 with the playback range
        #  at 0..24), so the outer range is the one that sets the cost
        cmds.playbackOptions(min=0, max=24, ast=0, aet=24)
        text = character.add_character(catalog.default_rig())
        rig, refusal = maya_rigs.current_rig()
        gate(1, "a throwaway rig added", rig is not None and "added as" in text, text[:60])
        root = skeleton.current_root()
        bone = skeleton.resolve_bone(root, "weapon_r")
        hand = attach.parent_bone(bone)
        weapon, note = attach.attach(catalog.by_key("LongSword_02"), hand, bone)
        gate(2, "the sword in the hand, driving weapon_r",
             weapon and bonedrive.driving_weapon(bone) == weapon and note == "", weapon.split("|")[-1])

        ik_r = cx._control(rig, "R")
        ik_l = cx._control(rig, "L")
        path_before = {s: cx._control(rig, s) for s in ("R", "L")}
        # a take on the right hand (the arm is FK by default; the IK control
        # itself is what we key, and Connect switches the blend)
        cmds.setAttr(cx._blend_plug(rig, "R"), 10)
        cmds.setAttr(cx._blend_plug(rig, "L"), 10)
        base = cmds.getAttr(ik_r + ".translate")[0]
        for t, dy in ((0, 0.0), (12, 8.0), (24, 0.0)):
            cmds.setKeyframe(ik_r, attribute="translateY", time=t, value=base[1] + dy)
            cmds.setKeyframe(ik_r, attribute="translateX", time=t, value=base[0] + dy * 0.5)
        cmds.currentTime(0)
        hand_track = {t: world(hand, t) for t in (0, 6, 12, 18, 24)}
        weapon_track = {t: world(weapon, t) for t in (0, 6, 12, 18, 24)}

        # ------------------------------------------------------- refusals
        gate(3, "no hands chosen is a refusal", cx.connect(rig=rig, sides=()) == cx.NO_HANDS)
        cmds.setKeyframe(cx._blend_plug(rig, "L"), time=0, value=3)
        text = cx.connect(rig=rig, sides=("L",))
        gate(4, "a blend keyed off IK is refused by name", "FKIKArm_L.FKIKBlend" in text, text)
        cmds.cutKey(cx._blend_plug(rig, "L"), clear=True)
        cmds.setAttr(cx._blend_plug(rig, "L"), 10)

        # -------------------------------------------------------- connect
        cmds.currentTime(6)
        text = cx.connect(rig=rig, sides=("R", "L"))
        gate(5, "Connect reports both hands and the frame", "right hand, left hand" in text
             and "frame 6" in text and "world" in text, text)
        weapon = bonedrive.driving_weapon(bone)
        gate(6, "the weapon left the hand for world space, still driving weapon_r",
             weapon and not cmds.listRelatives(weapon, parent=True), weapon)
        gate(7, "the weapon's world track is intact after OverRig's parent_out",
             max(worst(world(weapon, t), weapon_track[t]) for t in weapon_track) < 1e-3,
             "%.6f" % max(worst(world(weapon, t), weapon_track[t]) for t in weapon_track))
        gate(8, "the IK controls are constrained by OUR constraints, one each",
             len(cx.our_constraints(ik_r)) == 1 and len(cx.our_constraints(ik_l)) == 1
             and cx.connected_sides(rig) == ["R", "L"])
        gate(9, "the rig's DAG is unchanged: both controls keep their paths",
             {s: cx._control(rig, s) for s in ("R", "L")} == path_before)
        gate(10, "the controls carry no keys of their own any more",
             not cmds.keyframe(ik_r, q=True, timeChange=True) and not cmds.keyframe(ik_l, q=True, timeChange=True))
        hand_err = max(worst(world(hand, t), hand_track[t]) for t in hand_track)
        gate(11, "the right hand's world track is unchanged through Connect", hand_err < 1e-3, "%.6f" % hand_err)
        gate(12, "both arms in IK", cmds.getAttr(cx._blend_plug(rig, "R")) == 10 and cmds.getAttr(cx._blend_plug(rig, "L")) == 10)
        gate(13, "a second Connect is refused", "already connected" in cx.connect(rig=rig))
        refused = maya_rig_retarget.run_retarget(rig=rig)
        gate(14, "Retarget refuses a connected rig", refused[0] is False and "Disconnect first" in refused[1], refused[1][:70])

        # the weapon drives the hands: nudge it at frame 12 and the hand follows
        cmds.currentTime(12)
        before_nudge = world(hand, 12)
        cmds.setKeyframe(weapon, attribute="translateY", time=12, value=cmds.getAttr(weapon + ".translateY") + 10.0)
        moved = worst(world(hand, 12), before_nudge)
        gate(15, "moving the weapon moves the hand", moved > 5.0, "%.3f" % moved)
        nudged_hand = {t: world(hand, t) for t in (0, 6, 12, 18, 24)}

        # ----------------------------------------------------- disconnect
        cmds.currentTime(0)
        text = cx.disconnect(rig=rig)
        gate(16, "Disconnect reports the bake and the return", "baked over" in text and "back in the hand" in text, text)
        gate(17, "our constraints are gone and nothing is connected",
             not cx.our_constraints(ik_r) and not cx.our_constraints(ik_l) and not cx.connected_sides(rig))
        gate(18, "the controls are keyed over the range",
             len(set(cmds.keyframe(ik_r, q=True, timeChange=True) or [])) >= 25)
        weapon = bonedrive.driving_weapon(bone)
        gate(19, "the weapon is back under the hand, still driving weapon_r",
             weapon and (cmds.listRelatives(weapon, parent=True, fullPath=True) or [""])[0] == hand, weapon)
        err = max(worst(world(hand, t), nudged_hand[t]) for t in nudged_hand)
        gate(20, "the hand keeps the nudged track after the bake", err < 1e-3, "%.6f" % err)
        gate(21, "Disconnect with nothing connected says so", cx.disconnect(rig=rig) == cx.NOTHING_CONNECTED)
        gate(22, "the rig's DAG is unchanged after the round trip",
             {s: cx._control(rig, s) for s in ("R", "L")} == path_before)
    except Exception:
        import traceback
        traceback.print_exc()
        gate(99, "no exception", False)
    finally:
        after = set(cmds.ls(cmds.ls(), uuid=True))
        created = [u for u in after - before]
        nodes = []
        for u in created:
            found = cmds.ls(u, long=True) or []
            nodes.extend(n for n in found if cmds.objExists(n)
                         and n not in (cmds.ls(defaultNodes=True) or [])
                         and not cmds.lockNode(n, q=True, lock=True)[0])
        dag = [n for n in nodes if cmds.objectType(n, isAType="dagNode")]
        tops = [n for n in dag if not any(n.startswith(o + "|") for o in dag if o != n)]
        for group in (tops, [n for n in nodes if n not in dag]):
            for n in group:
                try:
                    if cmds.objExists(n):
                        cmds.delete(n)
                except Exception:
                    pass
        for ns in cmds.namespaceInfo(listOnlyNamespaces=True) or []:
            if ns.startswith("Manny_Rig"):
                try:
                    cmds.namespace(removeNamespace=ns, deleteNamespaceContent=True)
                except Exception:
                    pass
        cmds.playbackOptions(min=saved["rng"][0], max=saved["rng"][1],
                             ast=saved["rng"][2], aet=saved["rng"][3])
        cmds.currentTime(saved["time"])
        cmds.autoKeyframe(state=saved["autokey"])
        if saved["sel"]:
            cmds.select([s for s in saved["sel"] if cmds.objExists(s)], replace=True)
        else:
            cmds.select(clear=True)
        left = [r.namespace for r in maya_rigs.rigs()]
        print("cleanup: %d created nodes handled, rigs left: %s" % (len(created), left))

    print("")
    if FAILED:
        print("FAILURES: %d of %d gates failed: %s" % (len(FAILED), len(FAILED) + len(PASSED), FAILED))
    else:
        print("checks passed: %d of %d gates" % (len(PASSED), len(PASSED)))
