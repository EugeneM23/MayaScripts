"""The Pose Library's «Selected only», in mayapy STANDALONE (2026-10-15).

The animator: «у нас должна быть опция применить наложение только на выделенные объекты. Мы в
нашей позе должны найти информацию только о том что имеет отношение к нашему текущему выделению и
применить только это». Asked: ONLY the selected nodes take keys, each at its value in the whole
card. Never in the animator's Maya (it adds characters and keys them). Run with a scratch
MAYA_APP_DIR:

    $env:MAYA_APP_DIR = "<a scratch folder>"
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' `
        docs/superpowers/plans/verify_poselib_selected_only.py [out.txt]

  pose      Manny_Rig A posed (FK arms, spine, the head), carded whole; onto a second Manny_Rig
            B: FKWrist_R selected -> FKWrist_R alone keyed, at the value the whole card's
            solve gives it; FKShoulder_L + FKElbow_L -> those two alone; a hand card with only a
            leg control selected -> refused, no key anywhere; a Blend at 50 % on FKWrist_R ->
            FKWrist_R alone keyed, halfway; without the option the whole card as ever.
  anim      A keyed over 0..12, carded; pasted at 40 onto B with FKElbow_R selected: only
            FKElbow_R keyed, on 40..52, every key equal to the whole paste's onto a third rig C.
  skeleton  the Manny UE5 skeleton: hand_r selected -> only hand_r keyed.
"""

import io
import os
import sys
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.environ.get("POSELIB_PLUGIN") or
                          os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(_plugin, quiet=True)
cmds.currentUnit(time="ntsc")
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)

import maya_rigs  # noqa: E402
from maya_scenesetup import catalog, character  # noqa: E402
from maya_uebridge import skeletonimport  # noqa: E402
from maya_poselib import animapply, animcapture, capture, scene  # noqa: E402
from maya_poselib import apply as ap  # noqa: E402

OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []
ROT = ("rotateX", "rotateY", "rotateZ")
POSE = {"FKShoulder_L": (10, 20, 35), "FKElbow_L": (0, 0, 40), "FKWrist_L": (15, 0, 10),
        "FKShoulder_R": (-15, 10, -30), "FKElbow_R": (0, 0, 55), "FKWrist_R": (25, 15, -5),
        "FKSpine1_M": (5, 10, 0), "FKHead_M": (0, 20, 10)}


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


def add(key):
    before_rigs = set(r.namespace for r in maya_rigs.rigs())
    before_bare = set(skeletonimport.bare_roots())
    character.add_character(catalog.character_by_key(key))
    cmds.select(clear=True)
    new = [r for r in maya_rigs.rigs() if r.namespace not in before_rigs]
    if new:
        return new[0]
    bare = [r for r in skeletonimport.bare_roots() if r not in before_bare]
    return bare[0] if bare else None


def node(rig, leaf):
    return (cmds.ls(maya_rigs.node(rig, leaf), long=True) or [None])[0]


def keyed_nodes(nodes):
    """The nodes among `nodes` carrying any time curve on t / r."""
    out = set()
    for n in nodes:
        for attr in ROT + ("translateX", "translateY", "translateZ"):
            if cmds.keyframe(n + "." + attr, query=True, keyframeCount=True):
                out.add(n)
                break
    return out


def control_nodes(rig):
    out = []
    for member in cmds.sets(rig.control_set, query=True) or []:
        found = cmds.ls(member, long=True) or []
        if found and cmds.objectType(found[0], isAType="transform"):
            out.append(found[0])
    return out


def clear_keys(nodes):
    for n in nodes:
        cmds.cutKey(n, clear=True)


def value_at(plug, time):
    return cmds.keyframe(plug, query=True, time=(time, time), valueChange=True) or [None]


def run():
    a = add("Manny_Rig")
    b = add("Manny_Rig")
    c = add("Manny_Rig")
    for leaf, rot in POSE.items():
        for attr, value in zip(ROT, rot):
            cmds.setAttr(maya_rigs.node(a, leaf) + "." + attr, value)
    cmds.currentTime(10)
    card, note = capture.build_pose(selection=[node(a, "Main")])
    gate("pose.card", card is not None, note)
    controls_b = control_nodes(b)
    ref_b = scene.rig_ref(b)
    full = ap.plan_for(card, ref_b)
    wrist = node(b, "FKWrist_R")

    ok, text = ap.apply(card, selection=[wrist], only=True)
    keyed = keyed_nodes(controls_b)
    gate("pose.wrist_alone", ok and keyed == {wrist}, "%s | %s" % (sorted(keyed), text))
    worst = 0.0
    for plug, value in full.values.items():
        if ap._long_node(ap.node_of(plug)) == wrist:
            got = value_at(plug, 10)[0]
            worst = max(worst, abs((got if got is not None else 1e9) - value))
    gate("pose.wrist_at_full_value", worst < 1e-6, "%.2e" % worst)
    gate("pose.says_the_cut", "Selected only" in text, text)
    clear_keys(controls_b)

    two = [node(b, "FKShoulder_L"), node(b, "FKElbow_L")]
    ok, text = ap.apply(card, selection=two, only=True)
    keyed = keyed_nodes(controls_b)
    gate("pose.two_alone", ok and keyed == set(two), sorted(keyed))
    clear_keys(controls_b)

    hand, _note = capture.build_pose(selection=[node(a, "FKWrist_L")])
    ok, text = ap.apply(hand, selection=[node(b, "IKLeg_L")], only=True)
    keyed = keyed_nodes(controls_b)
    gate("pose.nothing_selected_in_card_refused", (not ok) and not keyed, text)

    for attr in ROT:                     # cutKey left the wrist where the last key put it
        cmds.setAttr(wrist + "." + attr, 0.0)
    mine = ap.OrderedDict((p, v) for p, v in full.values.items()
                          if ap._long_node(ap.node_of(p)) == wrist)
    now = dict((p, float(cmds.getAttr(p))) for p in mine)
    half = ap.mix(now, mine, 0.5, ap.rotations_of(mine))
    blend = ap.Blend()
    start = blend.start(card, selection=[wrist], only=True)
    blend.set(0.5)
    text = blend.finish()
    keyed = keyed_nodes(controls_b)
    worst = 0.0
    for plug, value in half.items():
        got = value_at(plug, 10)[0]
        worst = max(worst, abs(got - value))
    gate("pose.blend_wrist_alone_halfway", start == "" and keyed == {wrist} and worst < 1e-3,
         "%s %.2e %s" % (sorted(keyed), worst, text))
    clear_keys(controls_b)

    ok, text = ap.apply(card, selection=[wrist])
    keyed = keyed_nodes(controls_b)
    gate("pose.without_the_option_the_whole_card", ok and len(keyed) > 10, len(keyed))
    clear_keys(controls_b)

    # -- anim
    for frame_, scale in ((0, 0.0), (6, 1.0), (12, 0.5)):
        for leaf, rot in POSE.items():
            for attr, value in zip(ROT, rot):
                cmds.setKeyframe(maya_rigs.node(a, leaf) + "." + attr, time=frame_,
                                 value=value * scale)
    cmds.currentTime(0)
    header, frames, note = animcapture.build_animation(selection=[node(a, "Main")],
                                                       start=0, end=12)
    gate("anim.card", header is not None, note)
    options = {"mode": "replace", "at_current": True, "in_place": True}
    cmds.currentTime(40)
    elbow = node(b, "FKElbow_R")
    ok, text = animapply.apply(header, frames, selection=[elbow], options=options, only=True)
    keyed = keyed_nodes(controls_b)
    times = sorted(set(cmds.keyframe(elbow + ".rotateZ", query=True) or []))
    gate("anim.elbow_alone", ok and keyed == {elbow}, "%s | %s" % (sorted(keyed), text))
    gate("anim.every_frame", times == [float(t) for t in range(40, 53)], times)
    cmds.currentTime(40)
    ok_c, _text = animapply.apply(header, frames, selection=[node(c, "Main")], options=options)
    elbow_c = node(c, "FKElbow_R")
    worst = 0.0
    for attr in ROT:
        mine = cmds.keyframe(elbow + "." + attr, query=True, valueChange=True) or []
        theirs = cmds.keyframe(elbow_c + "." + attr, query=True, valueChange=True) or []
        if len(mine) != len(theirs):
            worst = 1e9
            break
        worst = max([worst] + [abs(x - y) for x, y in zip(mine, theirs)])
    gate("anim.elbow_as_the_whole_paste", ok_c and worst < 1e-4, "%.2e" % worst)

    # -- skeleton
    root = add("Manny")
    joints = cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or []
    hand_r = [j for j in joints if j.split("|")[-1].split(":")[-1] == "hand_r"][0]
    cmds.currentTime(10)
    ok, text = ap.apply(card, selection=[hand_r], only=True)
    keyed = keyed_nodes(joints + [root])
    gate("skeleton.hand_alone", ok and keyed == {hand_r}, "%s | %s" % (sorted(keyed), text))


try:
    run()
except Exception:                                            # noqa: BLE001
    say(traceback.format_exc())
    RESULTS.append(False)
say("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
if OUT is not None:
    OUT.close()
os._exit(0)
