"""verify_connections.py - who drives whom: hands and weapon, LIVE.

Send through the command port (CLAUDE.md, "Driving the user's live Maya")
with the INSTALLED copy first on sys.path. Live and not standalone because
OverRig's apply_Parent_out/in read the time slider and die in mayapy
("Cannot convert data of type int to type float[]", measured 2026-09-18).

It REFUSES to run in a scene that already holds a rig - it adds a
throwaway Manny_Rig, a sword and keys, and deletes every node it created
afterwards (a UUID diff of the whole scene). Playback range (inner AND
outer - OverRig bakes across the outer one), current time, autoKey and the
selection are put back.

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
    time=t)` does not pull a constraint + IK chain (measured 2026-09-18:
    the weapon nudged 10.000, the hand read 0.000 that way and 10.000 this
    way) - trap 14's family."""
    cmds.currentTime(t - 1)
    cmds.currentTime(t)
    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def worst(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def track(node, times=(0, 6, 12, 18, 24)):
    return {t: world(node, t) for t in times}


def drift(node, old):
    return max(worst(world(node, t), old[t]) for t in old)


import maya_rigs
import maya_rig_retarget
from maya_scenesetup import attach, bonedrive, catalog, character, connections as cx, skeleton

H, F = cx.HOLDS, cx.FOLLOWS

if maya_rigs.rigs():
    print("SKIP: the scene already holds a rig (%s) - this verify adds and deletes one"
          % [r.namespace for r in maya_rigs.rigs()])
    print("checks passed: 0 of 0 gates")
else:
    saved = dict(
        rng=(cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True),
             cmds.playbackOptions(q=True, ast=True), cmds.playbackOptions(q=True, aet=True)),
        time=cmds.currentTime(q=True), autokey=cmds.autoKeyframe(q=True, state=True),
        sel=cmds.ls(selection=True, long=True) or [])
    before = set(cmds.ls(cmds.ls(), uuid=True))
    try:
        cmds.autoKeyframe(state=False)
        cmds.playbackOptions(min=0, max=24, ast=0, aet=24)
        text = character.add_character(catalog.default_rig())
        rig, refusal = maya_rigs.current_rig()
        gate(1, "a throwaway rig added", rig is not None and "added as" in text, text[:60])
        bones = cx.bones_of(rig)
        hand_r, bone_r = bones["R"]
        hand_l, bone_l = bones["L"]
        weapon, note = attach.attach(catalog.by_key("LongSword_02"), hand_r, bone_r)
        gate(2, "the sword in the right hand, driving weapon_r; both weapon bones resolve",
             weapon and bonedrive.driving_weapon(bone_r) == weapon and note == "" and bone_l and hand_l,
             weapon.split("|")[-1])
        gate(3, "the scene reads as 'weapon in the right hand; left hand free'",
             cx.read_scheme(rig) == {"L": None, "R": H}, cx.describe(cx.read_scheme(rig)))

        ik_r, ik_l = cx._control(rig, "R"), cx._control(rig, "L")
        paths_before = {s: cx._control(rig, s) for s in cx.SIDES}
        for side in cx.SIDES:
            cmds.setAttr(cx._blend_plug(rig, side), 10)
        base = cmds.getAttr(ik_r + ".translate")[0]
        for t, dy in ((0, 0.0), (12, 8.0), (24, 0.0)):
            cmds.setKeyframe(ik_r, attribute="translateY", time=t, value=base[1] + dy)
            cmds.setKeyframe(ik_r, attribute="translateX", time=t, value=base[0] + dy * 0.5)
        hand_track = track(hand_r)
        weapon_track = track(weapon)

        # -------------------------------------------------------- refusals
        gate(4, "Apply of the standing scheme does nothing",
             cx.apply({"L": None, "R": H}, rig=rig) == cx.NOTHING_TO_DO)
        cmds.setKeyframe(cx._blend_plug(rig, "L"), time=0, value=3)
        text = cx.apply({"L": F, "R": H}, rig=rig)
        gate(5, "a blend keyed off IK is refused by name, nothing moved",
             "FKIKArm_L.FKIKBlend" in text and cx.read_scheme(rig) == {"L": None, "R": H}, text)
        cmds.cutKey(cx._blend_plug(rig, "L"), clear=True)
        cmds.setAttr(cx._blend_plug(rig, "L"), 10)

        # ------------------------ right holds, left follows (no weapon move)
        cmds.currentTime(6)
        text = cx.apply({"L": F, "R": H}, rig=rig)
        gate(6, "R holds + L follows: only the left hand is hung",
             "left hand follows (grip as at frame 6)" in text and "weapon out" not in text, text)
        gate(7, "the weapon is still in the right hand, weapon_r still driven",
             cx.read_scheme(rig) == {"L": F, "R": H} and bonedrive.driving_weapon(bone_r) == cmds.ls(weapon, long=True)[0])
        left_track = track(hand_l)
        gate(8, "the right hand's track is untouched", drift(hand_r, hand_track) < 1e-3, "%.6f" % drift(hand_r, hand_track))

        # -------------------------------------- both follow, weapon in world
        text = cx.apply({"L": F, "R": F}, rig=rig)
        gate(9, "both follow: weapon lifted to world, right hand hung",
             "weapon out of the right hand to world" in text and "right hand follows" in text, text)
        weapon = cx.weapon_of(rig)
        gate(10, "the weapon stands in world and its track is intact (OverRig parent_out)",
             not cmds.listRelatives(weapon, parent=True) and drift(weapon, weapon_track) < 1e-3,
             "%.6f" % drift(weapon, weapon_track))
        gate(11, "both IK controls carry exactly one constraint of ours, no keys",
             len(cx.our_constraints(ik_r)) == 1 and len(cx.our_constraints(ik_l)) == 1
             and not cmds.keyframe(ik_r, q=True, timeChange=True))
        gate(12, "both hands' tracks are unchanged through the lift",
             drift(hand_r, hand_track) < 1e-3 and drift(hand_l, left_track) < 1e-3,
             "%.6f / %.6f" % (drift(hand_r, hand_track), drift(hand_l, left_track)))
        gate(13, "the rig's DAG is unchanged: the controls keep their paths",
             {s: cx._control(rig, s) for s in cx.SIDES} == paths_before)
        refused = maya_rig_retarget.run_retarget(rig=rig)
        gate(14, "Retarget refuses a rig with following hands",
             refused[0] is False and "Disconnect first" in refused[1] or "Connections" in refused[1], refused[1][:70])
        before_nudge = world(hand_r, 12)
        cmds.currentTime(12)
        cmds.setKeyframe(weapon, attribute="translateY", time=12,
                         value=cmds.getAttr(weapon + ".translateY") + 10.0)
        moved = worst(world(hand_r, 12), before_nudge)
        gate(15, "moving the weapon moves the hands", moved > 9.0 and moved < 11.0, "%.3f" % moved)
        nudged_r, nudged_l = track(hand_r), track(hand_l)

        # ------------------------- weapon into the LEFT hand, right follows
        cmds.currentTime(0)
        text = cx.apply({"L": H, "R": F}, rig=rig)
        gate(16, "L holds + R follows: left released, weapon into the left hand",
             "left hand released" in text and "weapon into the left hand" in text and "weapon out" not in text, text)
        weapon = cx.weapon_of(rig)
        gate(17, "the weapon hangs under hand_l and drives weapon_l, not weapon_r",
             (cmds.listRelatives(weapon, parent=True, fullPath=True) or [""])[0] == hand_l
             and bonedrive.driving_weapon(bone_l) == weapon and not bonedrive.driving_weapon(bone_r),
             cx.describe(cx.read_scheme(rig)))
        gate(18, "weapon_l sits ON the weapon (no offset)",
             worst(world(bone_l, 12)[12:15], world(weapon, 12)[12:15]) < 1e-3,
             "%.6f" % worst(world(bone_l, 12)[12:15], world(weapon, 12)[12:15]))
        gate(19, "the weapon's nudged track survived the move into the hand (parent_in re-bake)",
             drift(weapon, {t: m for t, m in track(weapon).items()}) < 1e-9 and drift(hand_l, nudged_l) < 1e-3,
             "left hand %.6f" % drift(hand_l, nudged_l))
        gate(20, "the left control is keyed over the range, the right still constrained",
             len(set(cmds.keyframe(ik_l, q=True, timeChange=True) or [])) >= 25
             and len(cx.our_constraints(ik_r)) == 1 and not cx.our_constraints(ik_l))

        # ---------------------------------- back: right holds, hands free
        text = cx.apply({"L": None, "R": H}, rig=rig)
        gate(21, "R holds: right released, weapon lifted from the left and hung in the right",
             "right hand released" in text and "weapon out of the left hand" in text
             and "weapon into the right hand" in text, text)
        weapon = cx.weapon_of(rig)
        gate(22, "the weapon hangs under hand_r and drives weapon_r again",
             (cmds.listRelatives(weapon, parent=True, fullPath=True) or [""])[0] == hand_r
             and bonedrive.driving_weapon(bone_r) == weapon and not bonedrive.driving_weapon(bone_l))
        gate(23, "the right hand keeps the nudged track after its bake", drift(hand_r, nudged_r) < 1e-3,
             "%.6f" % drift(hand_r, nudged_r))
        gate(24, "nothing follows, the DAG is unchanged, Apply again does nothing",
             not cx.connected_sides(rig)
             and {s: cx._control(rig, s) for s in cx.SIDES} == paths_before
             and cx.apply({"L": None, "R": H}, rig=rig) == cx.NOTHING_TO_DO)
        gate(25, "connect()/disconnect() (the hotkeys) are the two schemes",
             "follow" in cx.connect(rig=rig) and cx.read_scheme(rig) == {"L": F, "R": F}
             and "into the right hand" in cx.disconnect(rig=rig)
             and cx.read_scheme(rig) == {"L": None, "R": H})
    except Exception:
        import traceback
        traceback.print_exc()
        gate(99, "no exception", False)
    finally:
        after = set(cmds.ls(cmds.ls(), uuid=True))
        created = [u for u in after - before]
        nodes = []
        for u in created:
            for n in cmds.ls(u, long=True) or []:
                try:
                    if cmds.objExists(n) and n not in (cmds.ls(defaultNodes=True) or []) \
                            and not cmds.lockNode(n, q=True, lock=True)[0]:
                        nodes.append(n)
                except Exception:
                    pass
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
        print("cleanup: %d created nodes handled, rigs left: %s" % (
            len(created), [r.namespace for r in maya_rigs.rigs()]))

    print("")
    if FAILED:
        print("FAILURES: %d of %d gates failed: %s" % (len(FAILED), len(FAILED) + len(PASSED), FAILED))
    else:
        print("checks passed: %d of %d gates" % (len(PASSED), len(PASSED)))
