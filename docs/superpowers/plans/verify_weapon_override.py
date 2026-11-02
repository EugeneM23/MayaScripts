"""Connections' 2H Weapon and the chest's Override mode (2026-11-02) - mayapy standalone.

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_weapon_override.py [out.txt] [phases]

Phases, comma-separated: identity,strength,lag,keys,default,reknob,undo,refusals,parent,
twohands,poselib (all of them without an argument).

The scene each phase builds for itself: a Manny_Rig at 30 fps over 0..20 whose CHEST control
`FKSpine3_M` turns 30 deg and travels 20 cm (keys 0 and 20), with a Long Sword in its right
hand - unkeyed where the gate wants the body to be the only thing moving, keyed on 0, 8, 20
where it wants the weapon's own track to vary.

With only the chest moving, the formula's four corners are crisp:

    1 / 1 / 0   the identity: the weapon follows the body exactly as it did
    0 / 0 / 0   the weapon frozen in world - it inherits neither half
    0 / 1 / 0   it travels with the body and never turns
    1 / 0 / 0   it turns with the body and takes none of its travel

Not here: the full `connections.apply` dance (a lift or a hang runs OverRig's
`apply_Parent_in` / `_out`, which read the time slider and die in mayapy - the animator's
live press). The `parent` phase proves the half that matters without it: the base is
re-read in the weapon's NEW parent and the settings are kept.

Spec: docs/superpowers/specs/2026-11-02-connections-2h-and-override-design.md
"""
import io
import os
import sys
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.api.OpenMaya as om  # noqa: E402
import maya.cmds as cmds  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.environ.get("OVERRIDE_PLUGIN") or
                          os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(_plugin, quiet=True)
cmds.currentUnit(time="ntsc")           # 30 fps: 100 ms is 3 frames
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)

import maya_rigs  # noqa: E402
from maya_scenesetup import bonedrive, catalog, character, connections, equip  # noqa: E402
from maya_scenesetup import pending, weaponaim, weaponoverride as wo  # noqa: E402
from maya_poselib import apply as poseapply, capture  # noqa: E402
from maya_poselib import posemath as pm  # noqa: E402

OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
PHASES = (sys.argv[2].split(",") if len(sys.argv) > 2 else
          ["identity", "strength", "lag", "keys", "default", "reknob", "undo",
           "refusals", "parent", "twohands", "poselib"])
RESULTS = []
CHANNELS = wo.CHANNELS
ROT = ("rotateX", "rotateY", "rotateZ")
FRAMES = list(range(0, 21))
SWORD_KEYS = (0.0, 8.0, 20.0)


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    if OUT is not None:
        OUT.write(line + "\n")
        OUT.flush()


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, value))
    return bool(ok)


def W(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def go(t):
    cmds.currentTime(t, update=True)


def evaluate(t):
    """A real time change before a read (trap 14): a bare setAttr/currentTime of the same
    frame leaves the DG holding stale values through a constraint chain."""
    go(t + 1)
    go(t)


def worlds(node, frames=None):
    out = {}
    for t in (frames or FRAMES):
        evaluate(t)
        out[t] = W(node)
    return out


def off(a, b):
    """max(the places' distance in cm, the turns' angle in degrees)."""
    return max((pm.position(a) - pm.position(b)).length(), pm.angle(a, b))


def worst_element(a, b):
    return max(abs(a[i] - b[i]) for i in range(16))


def key_times(node, attrs=CHANNELS):
    times = set()
    for a in attrs:
        for t in cmds.keyframe(node + "." + a, query=True, timeChange=True) or []:
            times.add(round(t, 4))
    return sorted(times)


def curve_state(node, attrs=CHANNELS):
    """{channel: (times, values, in types, out types)} - what Default must give back."""
    out = {}
    for a in attrs:
        plug = node + "." + a
        times = cmds.keyframe(plug, query=True, timeChange=True) or []
        out[a] = (tuple(round(t, 6) for t in times),
                  tuple(round(v, 9) for v in
                        (cmds.keyframe(plug, query=True, valueChange=True) or [])),
                  tuple(cmds.keyTangent(plug, query=True, inTangentType=True) or []),
                  tuple(cmds.keyTangent(plug, query=True, outTangentType=True) or []),
                  None if times else round(cmds.getAttr(plug), 9))
    return out


def bone(root, name):
    for j in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                          fullPath=True) or []):
        if j.split("|")[-1].split(":")[-1] == name:
            return j
    return None


def add(key="Manny_Rig"):
    before = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key(key))
    cmds.select(clear=True)
    return [r for r in maya_rigs.rigs() if r.namespace not in before][0]


def build(sword_keys=False, sword_key="LongSword_02"):
    """A rig whose chest turns 30 deg and travels 20 cm over 0..20, a sword in the right
    hand. (rig, root, sword, chest)."""
    cmds.playbackOptions(minTime=0, maxTime=20, animationStartTime=0, animationEndTime=20)
    rig = add()
    root = rig.skeleton_root
    say("  ", equip.to_hand(root, "R", catalog.by_key(sword_key)))
    sword = bonedrive.driving_weapon(bone(root, "weapon_r"))
    chest = wo.chest_of(rig)
    control = maya_rigs.node(rig, "FKSpine3_M")
    for attr, delta in (("rotateY", 30.0), ("translateX", 20.0)):
        base = cmds.getAttr(control + "." + attr)
        cmds.setKeyframe(control, attribute=attr, time=0, value=base)
        cmds.setKeyframe(control, attribute=attr, time=20, value=base + delta)
    if sword_keys:
        for t, (tr, ro) in {0: ((0, 0, 0), (0, 0, 0)),
                            8: ((3, -2, 1), (25, -10, 15)),
                            20: ((-2, 1, 4), (-20, 30, 5))}.items():
            for a, v in zip("XYZ", tr):
                cmds.setKeyframe(sword, attribute="translate" + a, time=t, value=v)
            for a, v in zip("XYZ", ro):
                cmds.setKeyframe(sword, attribute="rotate" + a, time=t, value=v)
    go(0)
    return rig, root, sword, chest


def turn_over(track):
    """The largest angle between any frame's orientation and the first frame's, degrees."""
    first = track[min(track)]
    return max(pm.angle(m, first) for m in track.values())


def travel_over(track):
    """The largest distance any frame's place stands from the first frame's, cm."""
    first = pm.position(track[min(track)])
    return max((pm.position(m) - first).length() for m in track.values())


def press(rig, sword, rotation, position, lag):
    text = connections.override_mode(rig=rig, weapon=sword, on=True,
                                     settings=wo.Settings(rotation, position, lag))
    say("   override %g / %g / %g:" % (rotation, position, lag), text)
    return text


# ----------------------------------------------------------------- the phases

def phase_identity():
    say("\n--- identity: 1 / 1 / 0 changes nothing")
    rig, _root, sword, chest = build(sword_keys=True)
    before = worlds(sword)
    press(rig, sword, 1.0, 1.0, 0.0)
    after = worlds(sword)
    worst = max(worst_element(after[t], before[t]) for t in FRAMES)
    gate("identity: every frame's world matrix as it was", worst < 1e-12, "%.2e" % worst)
    gate("identity: the mode stands with its numbers",
         wo.state(sword) == wo.Settings(1.0, 1.0, 0.0), wo.state(sword))
    #  and the first frame is bit-exact whatever the lag
    connections.override_mode(rig=rig, weapon=sword, on=False)
    press(rig, sword, 1.0, 1.0, 100.0)
    evaluate(0)
    first = worst_element(W(sword), before[0])
    gate("the first frame is bit-exact at lag 100 ms", first < 1e-9, "%.2e" % first)


def phase_strength():
    say("\n--- strength: the body is the only thing moving")
    rig, _root, sword, chest = build(sword_keys=False)
    body = worlds(chest)
    say("   the chest turns %.3f deg and travels %.3f cm over the take"
        % (turn_over(body), travel_over(body)))
    base = worlds(sword)
    #  1 / 1 / 0 - the weapon follows the body, as it did
    press(rig, sword, 1.0, 1.0, 0.0)
    full = worlds(sword)
    gate("1 / 1 / 0: the weapon follows the body as it did",
         max(worst_element(full[t], base[t]) for t in FRAMES) < 1e-12,
         "%.2e" % max(worst_element(full[t], base[t]) for t in FRAMES))
    #  0 / 0 / 0 - frozen in world
    connections.override_mode(rig=rig, weapon=sword, on=False)
    press(rig, sword, 0.0, 0.0, 0.0)
    frozen = worlds(sword)
    still = max(off(frozen[t], frozen[0]) for t in FRAMES)
    gate("0 / 0 / 0: the weapon stands still in world", still < 1e-3,
         "%.2e cm/deg (it moved %.3f cm and turned %.3f deg before)"
         % (still, travel_over(base), turn_over(base)))
    #  0 / 1 / 0 - travels, never turns
    connections.override_mode(rig=rig, weapon=sword, on=False)
    press(rig, sword, 0.0, 1.0, 0.0)
    moved = worlds(sword)
    gate("0 / 1 / 0: it never turns", turn_over(moved) < 1e-3,
         "%.2e deg against the body's %.3f" % (turn_over(moved), turn_over(body)))
    gate("0 / 1 / 0: it travels with the body",
         abs(travel_over(moved) - travel_over(body)) < 1e-3,
         "%.4f cm against the body's %.4f" % (travel_over(moved), travel_over(body)))
    #  1 / 0 / 0 - turns, takes none of the travel
    connections.override_mode(rig=rig, weapon=sword, on=False)
    press(rig, sword, 1.0, 0.0, 0.0)
    turned = worlds(sword)
    gate("1 / 0 / 0: it turns with the body",
         abs(turn_over(turned) - turn_over(base)) < 1e-3,
         "%.4f deg against the body's %.4f" % (turn_over(turned), turn_over(base)))
    #  the chest's own travel is gone: what is left is the turn about the chest's ref pivot
    about_pivot = max((pm.position(turned[t]) - pm.position(turned[0])).length()
                      for t in FRAMES)
    gate("1 / 0 / 0: it takes none of the body's travel",
         about_pivot < travel_over(base),
         "%.3f cm against %.3f with the travel inherited" % (about_pivot, travel_over(base)))


def phase_lag():
    say("\n--- lag: the weapon takes the chest's pose from earlier")
    rig, _root, sword, chest = build(sword_keys=True)
    own = worlds(sword)
    body = worlds(chest)
    press(rig, sword, 1.0, 1.0, 100.0)
    late = worlds(sword)

    def mismatch(shift):
        """max over the frames where f - shift is inside the take of
        | W(f) · C(f - shift)⁻¹  -  W_own(f) · C(f)⁻¹ |"""
        worst = 0.0
        for t in FRAMES:
            if t - shift < 0:
                continue
            a = pm.rigid(late[t]) * pm.rigid(body[t - shift]).inverse()
            b = pm.rigid(own[t]) * pm.rigid(body[t]).inverse()
            worst = max(worst, worst_element(a, b))
        return worst

    three, zero = mismatch(3), mismatch(0)
    gate("lag 100 ms: the weapon's pose in the chest's frame three frames back IS its "
         "base's pose in the chest's frame now", three < 1e-6, "%.2e" % three)
    gate("   the control: read without the shift it differs", zero > 1e-3, "%.3e" % zero)
    #  and it really moved
    worst = max(off(late[t], own[t]) for t in FRAMES)
    gate("lag 100 ms: the weapon's track really changed", worst > 0.5,
         "%.3f cm/deg at most" % worst)


def phase_keys():
    say("\n--- keys: the weapon's own keys and the chest's, plus what the fill adds")
    rig, _root, sword, chest = build(sword_keys=True)
    union = sorted(set(key_times(sword)) | set([0.0, 20.0]))
    press(rig, sword, 1.0, 1.0, 0.0)
    written = key_times(sword)
    gate("the identity keys exactly the union of the two sources, no fill",
         written == union, "%s against the union %s" % (written, union))
    tangents = cmds.keyTangent(sword + ".rotateY", query=True, inTangentType=True)
    gate("   with the source keys' tangents", bool(tangents) and
         all(t == tangents[0] for t in tangents), tangents)
    connections.override_mode(rig=rig, weapon=sword, on=False)
    press(rig, sword, 1.0, 1.0, 100.0)
    lagged = key_times(sword)
    gate("a lag fills the frames between them", len(lagged) > len(union),
         "%d keys against the union's %d" % (len(lagged), len(union)))


def phase_default():
    say("\n--- Default: the weapon's own animation back, exactly")
    rig, _root, sword, chest = build(sword_keys=True)
    before = curve_state(sword)
    press(rig, sword, 0.5, 0.5, 120.0)
    text = connections.override_mode(rig=rig, weapon=sword, on=False)
    say("   default:", text)
    after = curve_state(sword)
    same = [a for a in CHANNELS if before[a] == after[a]]
    gate("every curve back key for key, value for value, tangent for tangent",
         len(same) == len(CHANNELS), "%d of %d channels" % (len(same), len(CHANNELS)))
    gate("the marker and the six base attributes gone",
         wo.state(sword) is None and
         not [a for a in CHANNELS
              if cmds.objExists(sword + "." + wo.base_attr(a))])
    #  an unkeyed weapon too: the plain values come back
    rig2, _r2, sword2, _c2 = build(sword_keys=False)
    values = dict((a, round(cmds.getAttr(sword2 + "." + a), 9)) for a in CHANNELS)
    press(rig2, sword2, 1.0, 1.0, 80.0)
    connections.override_mode(rig=rig2, weapon=sword2, on=False)
    back = dict((a, round(cmds.getAttr(sword2 + "." + a), 9)) for a in CHANNELS)
    gate("an unkeyed weapon's plain values back", values == back,
         "%s" % max(abs(values[a] - back[a]) for a in CHANNELS))
    gate("   and no key left on it", not key_times(sword2), key_times(sword2))


def phase_reknob():
    say("\n--- a knob turned: the base is re-read, never the result")
    rig, _root, sword, chest = build(sword_keys=True)
    press(rig, sword, 1.0, 1.0, 160.0)
    once = worlds(sword)
    connections.override_mode(rig=rig, weapon=sword, on=False)
    #  the other road: 80 ms, then 160 ms over it
    press(rig, sword, 1.0, 1.0, 80.0)
    press(rig, sword, 1.0, 1.0, 160.0)
    twice = worlds(sword)
    worst = max(worst_element(once[t], twice[t]) for t in FRAMES)
    gate("80 then 160 ms equals one press at 160", worst < 1e-9, "%.2e" % worst)
    gate("   the settings standing are the last ones",
         wo.state(sword) == wo.Settings(1.0, 1.0, 160.0), wo.state(sword))


def phase_undo():
    say("\n--- one Ctrl+Z a press")
    rig, _root, sword, chest = build(sword_keys=True)
    before = curve_state(sword)
    press(rig, sword, 0.5, 1.0, 120.0)
    cmds.undo()
    after = curve_state(sword)
    gate("one Ctrl+Z after the press gives the weapon's curves back",
         before == after and wo.state(sword) is None,
         "%d of %d channels" % (len([a for a in CHANNELS if before[a] == after[a]]),
                                len(CHANNELS)))
    press(rig, sword, 0.5, 1.0, 120.0)
    standing = wo.state(sword)
    connections.override_mode(rig=rig, weapon=sword, on=False)
    cmds.undo()
    gate("one Ctrl+Z after Default puts the mode back",
         wo.state(sword) == standing, wo.state(sword))


def phase_refusals():
    say("\n--- the refusals change nothing")
    rig, _root, sword, chest = build(sword_keys=True)

    def unchanged(name, press):
        """A refusal's own gate: the weapon's curves before it and after it. The
        snapshot is taken around EACH refusal - Aim Mode's own round trip re-keys the
        rotate (its fill), which is its business, not this mode's."""
        was = curve_state(sword)
        text = press()
        say("   refused:", text)
        now = curve_state(sword)
        same = len([a for a in CHANNELS if was[a] == now[a]])
        gate(name, was == now and wo.state(sword) is None,
             "%s | %d of %d channels as they were" % (text, same, len(CHANNELS)))
        return text

    #  Aim Mode standing
    say("  ", weaponaim.enter(sword))
    text = unchanged("Aim Mode standing: Override refused, nothing changed",
                     lambda: connections.override_mode(rig=rig, weapon=sword, on=True))
    gate("   it names Aim Mode", "Aim Mode" in text)
    say("  ", weaponaim.leave(sword))
    #  the other way round
    press(rig, sword, 1.0, 1.0, 80.0)
    back = connections.aim_mode(rig=rig, weapon=sword, on=True)
    gate("Override standing: Aim Mode refused by name", "Override" in back, back)
    gate("   and Default is still allowed",
         "Override" not in connections.aim_mode(rig=rig, weapon=sword, on=False))
    connections.override_mode(rig=rig, weapon=sword, on=False)
    #  a locked rotate
    cmds.setAttr(sword + ".rotateX", lock=True)
    text = unchanged("a locked rotateX: refused, nothing changed",
                     lambda: connections.override_mode(rig=rig, weapon=sword, on=True))
    cmds.setAttr(sword + ".rotateX", lock=False)
    gate("   it names the channel", "locked" in text, text)
    #  no chest
    text = wo.refusal(sword, None)
    gate("no chest: refused by name", wo.CHEST in text, text)


def phase_parent():
    say("\n--- the base is re-read in a new parent (the half `apply`'s dance needs)")
    rig, _root, sword, chest = build(sword_keys=True)
    settings = wo.Settings(1.0, 1.0, 100.0)
    press(rig, sword, *settings)
    standing = wo.state(sword)
    #  Default, the weapon moved to another parent by hand (OverRig's parent_in / _out
    #  need a GUI Maya - this is the step `apply` wraps), Override again
    connections.override_mode(rig=rig, weapon=sword, on=False)
    holder = cmds.createNode("transform", name="newParent", skipSelect=True)
    cmds.setAttr(holder + ".translateY", 50.0)
    uuid = cmds.ls(sword, uuid=True)[0]
    cmds.parent(sword, holder)
    sword = cmds.ls(uuid, long=True)[0]
    own = worlds(sword)
    text = connections.override_mode(rig=rig, weapon=sword, on=True, settings=standing)
    say("   again:", text)
    gate("the settings are kept through the move", wo.state(sword) == settings,
         wo.state(sword))
    #  the formula over the NEW parent: the weapon's pose in the chest's frame three
    #  frames back is its base's pose in the chest's frame now
    late, body = worlds(sword), worlds(chest)
    worst = 0.0
    for t in FRAMES:
        if t < 3:
            continue
        a = pm.rigid(late[t]) * pm.rigid(body[t - 3]).inverse()
        b = pm.rigid(own[t]) * pm.rigid(body[t]).inverse()
        worst = max(worst, worst_element(a, b))
    gate("the lag holds in the new parent", worst < 1e-6, "%.2e" % worst)


def phase_twohands():
    say("\n--- 2H: one press binds both hands")
    rig, root, sword, _chest = build(sword_keys=False)
    scheme = connections.read_scheme(rig)
    gate("the scene: the weapon in the right hand, the left free",
         scheme == {"R": connections.HOLDS, "L": None}, scheme)
    gate("   so the chip is not lit", not connections.two_hands_state(scheme))
    asked = connections.two_hands_picks(scheme, True)
    gate("ticking asks for the LEFT hand only - the right one carries it",
         asked == {"L": connections.WEAPON}, asked)
    wanted = dict(scheme)
    for side, choice in asked.items():
        wanted = connections.wanted_for_row(wanted, side, choice)
    say("  ", connections.apply(wanted, rig=rig, weapon=sword))
    after = connections.read_scheme(rig)
    gate("applied: the left hand follows and the weapon is still in the right",
         after == {"R": connections.HOLDS, "L": connections.FOLLOWS}, after)
    gate("   and the chip reads lit from the scene", connections.two_hands_state(after))
    #  unticking frees the follower and leaves the holder
    asked = connections.two_hands_picks(after, False)
    gate("unticking asks to free the follower only", asked == {"L": connections.FREE},
         asked)
    wanted = dict(after)
    for side, choice in asked.items():
        wanted = connections.wanted_for_row(wanted, side, choice)
    say("  ", connections.apply(wanted, rig=rig, weapon=sword))
    back = connections.read_scheme(rig)
    gate("applied: the left hand free, the weapon still in the right",
         back == {"R": connections.HOLDS, "L": None}, back)
    #  a weapon in WORLD: both hands go on it
    scheme = {"R": None, "L": None}
    gate("in world, ticking asks for both hands",
         connections.two_hands_picks(scheme, True) ==
         {"R": connections.WEAPON, "L": connections.WEAPON})


def phase_poselib():
    say("\n--- the Pose Library saves and applies the result")
    rig, root, sword, chest = build(sword_keys=True)
    press(rig, sword, 1.0, 1.0, 120.0)
    evaluate(8)
    want = W(bone(root, "weapon_r"))
    cmds.select(maya_rigs.node(rig, "Main"))
    card, note = capture.build_pose()
    say("   saved:", note, "- %d bones" % len(card.get("bones") or {}) if card else "")
    gate("a card saves off the result", card is not None, note)
    rig2 = add()
    say("  ", equip.to_hand(rig2.skeleton_root, "R", catalog.by_key("LongSword_02")))
    ok, text = poseapply.apply(card, selection=[maya_rigs.node(rig2, "Main")])
    say("   applied:", ok, text)
    evaluate(8)
    got = W(bone(rig2.skeleton_root, "weapon_r"))
    gate("the second rig's weapon bone on the card's", off(got, want) < 1e-2,
         "%.2e cm/deg" % off(got, want))


PHASE = {"identity": phase_identity, "strength": phase_strength, "lag": phase_lag,
         "keys": phase_keys, "default": phase_default, "reknob": phase_reknob,
         "undo": phase_undo, "refusals": phase_refusals, "parent": phase_parent,
         "twohands": phase_twohands, "poselib": phase_poselib}


def main():
    for name in PHASES:
        run = PHASE.get(name)
        if run is None:
            say("?? no phase named", name)
            continue
        cmds.file(new=True, force=True)
        cmds.currentUnit(time="ntsc")
        pending.clear()
        try:
            run()
        except Exception:                                    # noqa: BLE001
            say(traceback.format_exc())
            gate("%s: the phase ran" % name, False)
    say("\n%d of %d gates failed" % (len([r for r in RESULTS if not r]), len(RESULTS)))


main()
if OUT is not None:
    OUT.close()
