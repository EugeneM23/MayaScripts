"""verify_connections.py - who drives whom: hands and weapon, LIVE.

Send through the command port (CLAUDE.md, "Driving the user's live Maya")
with the INSTALLED copy first on sys.path. Live and not standalone because
OverRig's apply_Parent_out/in read the time slider and die in mayapy
("Cannot convert data of type int to type float[]", measured 2026-09-18).

The rig: the scene's SOLE rig when there is one (the animator's leave:
«риг в сцене для тебя, можешь тестировать на нём», 2026-09-18 - its IK
hand controls get keys from this run and are cut clean afterwards, its
FKIKBlends put back), else a throwaway Manny_Rig it adds. Two rigs is a
skip. Every node the run created is deleted afterwards (a UUID diff of
the whole scene); playback range (inner AND outer - OverRig bakes across
the outer one), current time, autoKey and the selection are put back.

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

existing = maya_rigs.rigs()
if len(existing) > 1:
    print("SKIP: the scene holds %d rigs - this verify wants one or none" % len(existing))
    print("checks passed: 0 of 0 gates")
else:
    saved = dict(
        rng=(cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True),
             cmds.playbackOptions(q=True, ast=True), cmds.playbackOptions(q=True, aet=True)),
        time=cmds.currentTime(q=True), autokey=cmds.autoKeyframe(q=True, state=True),
        sel=cmds.ls(selection=True, long=True) or [])
    before = set(cmds.ls(cmds.ls(), uuid=True))
    borrowed = bool(existing)
    blends = {}
    ik_r = ik_l = None
    try:
        cmds.autoKeyframe(state=False)
        #  ast/aet too: OverRig's parent_out bakes across the ANIMATION range
        cmds.playbackOptions(min=0, max=24, ast=0, aet=24)
        if borrowed:
            rig = existing[0]
            gate(1, "the scene's own rig is borrowed (the animator's leave)", True, rig.namespace)
        else:
            text = character.add_character(catalog.default_rig())
            rig, refusal = maya_rigs.current_rig()
            gate(1, "a throwaway rig added", rig is not None and "added as" in text, text[:60])
        bones = cx.bones_of(rig)
        hand_r, bone_r = bones["R"]
        hand_l, bone_l = bones["L"]
        ik_r, ik_l = cx._control(rig, "R"), cx._control(rig, "L")
        blends = {s: cmds.getAttr(cx._blend_plug(rig, s)) for s in cx.SIDES}
        #  a borrowed rig may already hold a weapon, a connection or the
        #  orphan proxies an earlier build left behind: start clean
        if borrowed:
            swept = cx.sweep_orphans()
            if swept:
                print("    swept %d orphan proxy(ies) left by an earlier build" % swept)
            for side in cx.SIDES:
                if cx.our_constraints(cx._control(rig, side)):
                    cx.apply({"L": None, "R": None}, rig=rig)
                    break
            if cx.weapon_of(rig, bones):
                cx.apply({"L": None, "R": H}, rig=rig)
        weapon = cx.weapon_of(rig, bones)
        if not weapon:
            weapon, note = attach.attach(catalog.by_key("LongSword_02"), hand_r, bone_r)
        elif borrowed and not bonedrive.driving_weapon(bone_r) \
                and (cmds.listRelatives(weapon, parent=True, fullPath=True) or [""])[0] == hand_r:
            #  a sword in the hand with no bone link (an earlier run's cleanup
            #  deleted the re-made constraint): give the animator the link back
            bonedrive.link(weapon, bone_r)
            print("    relinked %s to weapon_r" % weapon.split("|")[-1])
        gate(2, "a sword in the right hand, driving weapon_r; both weapon bones resolve",
             weapon and bonedrive.driving_weapon(bone_r) == cmds.ls(weapon, long=True)[0] and bone_l and hand_l,
             weapon.split("|")[-1])
        gate(3, "the scene reads as 'weapon in the right hand; left hand free'",
             cx.read_scheme(rig) == {"L": None, "R": H}, cx.describe(cx.read_scheme(rig)))

        paths_before = {s: cx._control(rig, s) for s in cx.SIDES}
        for side in cx.SIDES:
            cmds.cutKey(cx._blend_plug(rig, side), clear=True)
            cmds.setAttr(cx._blend_plug(rig, side), 10)
        for ctl in (ik_r, ik_l):
            cmds.cutKey(ctl, attribute=list(cx.CHANNELS), clear=True)
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
        gate(6, "R holds + L follows: only the left hand is hung, through a proxy",
             "left hand follows (its track kept on the proxy)" in text and "weapon out" not in text, text)
        gate(7, "the weapon is still in the right hand, weapon_r still driven",
             cx.read_scheme(rig) == {"L": F, "R": H} and bonedrive.driving_weapon(bone_r) == cmds.ls(weapon, long=True)[0])
        gate(8, "the right hand's track is untouched", drift(hand_r, hand_track) < 1e-3, "%.6f" % drift(hand_r, hand_track))
        proxy_l = cx.proxy_of(rig, "L")
        gate(26, "the left proxy is a locator INSIDE the weapon's geometry, marked, 40 % bigger",
             proxy_l and (cmds.listRelatives(proxy_l, parent=True, fullPath=True) or [""])[0]
             == attach.model_root(weapon) and cmds.listRelatives(proxy_l, shapes=True, type="locator")
             and abs(cmds.getAttr(proxy_l + ".localScaleX") - 8.4) < 1e-6, proxy_l)
        # the weapon rides the KEYED right hand while the left hand stands
        # still, so in the weapon's space the left hand moves: its proxy is
        # keyed (the track kept), and the rotate channels, still, are not
        gate(27, "the proxy keeps the hand's relative track as keys",
             proxy_l and len(set(cmds.keyframe(proxy_l + ".translateY", q=True, timeChange=True) or [])) >= 25)
        gate(30, "the constrained control is HIDDEN while it rides the proxy",
             not cmds.getAttr(ik_l + ".visibility"))
        # a key on the PROXY moves the IK CONTROL (the hand bone follows as far
        # as the arm reaches - an IK limit, not our concern here)
        before_key = world(ik_l, 12)
        proxy_before = world(proxy_l, 12)
        cmds.currentTime(12)
        cmds.setKeyframe(proxy_l, attribute="translateY", time=12,
                         value=cmds.getAttr(proxy_l + ".translateY", time=12) + 5.0)
        moved = worst(world(ik_l, 12)[12:15], before_key[12:15])
        proxy_moved = worst(world(proxy_l, 12)[12:15], proxy_before[12:15])
        weapon_moved = worst(world(weapon, 12), weapon_track[12])
        # the proxy's +5 is in the WEAPON's space (a scaled weapon scales
        # it); the control must move exactly as far as the proxy did, in world
        gate(28, "a key on the proxy moves the hand control with it, the weapon stays",
             proxy_moved > 1.0 and abs(moved - proxy_moved) < 1e-3 and weapon_moved < 1e-3,
             "control %.3f proxy %.3f weapon %.6f" % (moved, proxy_moved, weapon_moved))
        left_track = track(hand_l)

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
        proxy_r = cx.proxy_of(rig, "R")
        gate(31, "the right proxy carries the hand's OWN motion against the weapon as keys",
             proxy_r and len(set(cmds.keyframe(proxy_r, q=True, timeChange=True) or [])) >= 25, proxy_r)
        gate(13, "the rig's DAG is unchanged: the controls keep their paths",
             {s: cx._control(rig, s) for s in cx.SIDES} == paths_before)
        refused = maya_rig_retarget.run_retarget(rig=rig)
        gate(14, "Retarget refuses a rig with following hands",
             refused[0] is False and ("Disconnect first" in refused[1] or "Connections" in refused[1]), refused[1][:70])
        #  measured on the IK CONTROLS: the hand BONE follows only as far as
        #  the arm reaches (an IK limit - read 5.658 for a 10 cm nudge with
        #  the animator's own grip, 10.000 with a fresh one)
        before_nudge = (world(ik_r, 12), world(ik_l, 12))
        cmds.currentTime(12)
        cmds.setKeyframe(weapon, attribute="translateY", time=12,
                         value=cmds.getAttr(weapon + ".translateY") + 10.0)
        moved = (worst(world(ik_r, 12)[12:15], before_nudge[0][12:15]),
                 worst(world(ik_l, 12)[12:15], before_nudge[1][12:15]))
        gate(15, "moving the weapon moves both hand controls with it",
             all(9.99 < m < 10.01 for m in moved), "%.3f / %.3f" % moved)
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
        gate(19, "the left hand keeps its (keyed) track through the move into the hand",
             drift(hand_l, nudged_l) < 1e-3, "left hand %.6f" % drift(hand_l, nudged_l))
        gate(20, "the left control is keyed over the range, the right still constrained",
             len(set(cmds.keyframe(ik_l, q=True, timeChange=True) or [])) >= 25
             and len(cx.our_constraints(ik_r)) == 1 and not cx.our_constraints(ik_l))
        gate(29, "the released hand's proxy is GONE (bake deletes it), the right hand's stays, the left control shown",
             cx.proxy_of(rig, "L") is None and cx.proxy_of(rig, "R") is not None
             and cmds.getAttr(ik_l + ".visibility"))

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
        gate(24, "nothing follows, no proxy left, the DAG is unchanged, Apply again does nothing",
             not cx.connected_sides(rig) and not cx.proxies()
             and {s: cx._control(rig, s) for s in cx.SIDES} == paths_before
             and cx.apply({"L": None, "R": H}, rig=rig) == cx.NOTHING_TO_DO)
        gate(25, "connect()/disconnect() (the hotkeys) are the two schemes",
             "follow" in cx.connect(rig=rig) and cx.read_scheme(rig) == {"L": F, "R": F}
             and "into the right hand" in cx.disconnect(rig=rig)
             and cx.read_scheme(rig) == {"L": None, "R": H})

        # ------------------------------------------------------ BakeAcross
        a = cmds.spaceLocator(name="skvA")[0]
        b = cmds.spaceLocator(name="skvB")[0]
        c = cmds.polyCube(name="skvC")[0]
        cmds.setAttr(c + ".translate", 10, 0, 0)
        for t, v in ((0, 0.0), (12, 6.0), (24, 0.0)):
            cmds.setKeyframe(a, attribute="translateZ", time=t, value=v)
        a_track = track(a)
        text = cx.bake_across([a, b, c])
        gate(32, "BakeAcross: A and B ride proxies inside C, hidden", "2 object(s) ride proxies inside skvC" in text
             and len(cx.our_constraints(cmds.ls(a, long=True)[0])) == 1 and not cmds.getAttr(a + ".visibility")
             and all((cmds.listRelatives(p, parent=True) or [""])[0] == "skvC" for p in cx.proxies()
                     if "skv" in p), text)
        gate(33, "A keeps its own track through BakeAcross", drift(a, a_track) < 1e-3, "%.6f" % drift(a, a_track))
        proxy_b = [p for p in cx.proxies() if p.endswith("skvB_proxy")]
        gate(39, "a STILL rider's proxy carries no keys (its channels collapsed to values)",
             proxy_b and not cmds.keyframe(proxy_b[0], q=True, timeChange=True), proxy_b)
        cmds.currentTime(12)
        cmds.setKeyframe(c, attribute="translateX", time=12, value=30.0)
        moved = worst(world(a, 12)[12:15], a_track[12][12:15])
        gate(34, "moving the parent C moves A", 19.0 < moved < 21.0, "%.3f" % moved)
        gate(35, "BakeAcross on a rider is refused", "Release it first" in cx.bake_across([a, c]))
        proxy_a = [p for p in cx.proxies() if p.endswith("skvA_proxy")][0]
        gate(36, "a cycle is refused both ways round, nothing attached",
             "cycle" in cx.bake_across([c, proxy_a]) and "inside" in cx.bake_across([proxy_a, c])
             and not cx.our_constraints(cmds.ls(c, long=True)[0]) and not cx.our_constraints(proxy_a))
        text = cx.release_across([a, b])
        gate(37, "Release: A and B baked, proxies gone, shown",
             "Released 2 object(s), 2 proxy(ies) removed" in text and not cx.our_constraints(cmds.ls(a, long=True)[0])
             and cmds.getAttr(a + ".visibility") and not [p for p in cx.proxies() if "skv" in p], text)
        gate(38, "A keeps the moved track after Release", drift(a, track(a)) < 1e-9
             and abs(world(a, 12)[12] - (a_track[12][12] + 20.0)) < 1e-3)
    except Exception:
        import traceback
        traceback.print_exc()
        gate(99, "no exception", False)
    finally:
        try:
            if borrowed and ik_r:
                for ctl in (ik_r, ik_l):
                    for con in cx.our_constraints(ctl):
                        cmds.delete(con)
                    cmds.cutKey(ctl, attribute=list(cx.CHANNELS), clear=True)
                    cx._set_visible(ctl, True)
                for side, value in blends.items():
                    cmds.setAttr(cx._blend_plug(rig, side), value)
        except Exception:
            pass
        #  on a borrowed rig the run re-makes the weapon bones' constraints
        #  (the weapon changed hands and came back) - those are the animator's
        #  link now and must survive the diff
        protected = set()
        try:
            if borrowed:
                for side in cx.SIDES:
                    bone = cx.bones_of(rig)[side][1]
                    if bone:
                        protected.update(cmds.listRelatives(
                            bone, children=True, type="constraint", fullPath=True) or [])
        except Exception:
            pass
        after = set(cmds.ls(cmds.ls(), uuid=True))
        created = [u for u in after - before]
        nodes = []
        for u in created:
            for n in cmds.ls(u, long=True) or []:
                try:
                    if not cmds.objExists(n) or n in protected \
                            or n in (cmds.ls(defaultNodes=True) or []) \
                            or cmds.lockNode(n, q=True, lock=True)[0]:
                        continue
                    #  on a BORROWED rig only the sandbox goes: the round
                    #  trips leave baked curves on the animator's controls
                    #  and sword, and a blanket diff once took the sword's
                    #  link with them (2026-09-18) - those keys are cut
                    #  below instead, by name
                    if borrowed and "skv" not in n.split("|")[-1] \
                            and not cmds.attributeQuery(cx.PROXY_MARKER, node=n, exists=True):
                        continue
                    nodes.append(n)
                except Exception:
                    pass
        if borrowed:
            try:
                weapon = cx.weapon_of(rig, cx.bones_of(rig))
                for node in [ik_r, ik_l, weapon]:
                    if node and cmds.objExists(node):
                        cmds.cutKey(node, attribute=list(cx.CHANNELS), clear=True)
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
        if not borrowed:
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
