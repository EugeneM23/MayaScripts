"""The camera and the weapon bones on a card, and the skeleton road (2026-10-20) - mayapy standalone.

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_camera_weapon_bones.py [out.txt]

The source: a Manny UE5 skeleton keyed over 0..10 (the pelvis turning, the right hand turning,
`weapon_r` sliding 6 cm and turning 30 deg in the hand, `camera_root` rising 10 and turning 15,
`camera_bone` turning 10), then a Long Sword put into its right hand (the bone's track onto the
sword, the bone following it) and Camera Setup on it (the camera_root's track onto the camera, the
bone following it). At frame 5 a whole-body card and a right-hand card are saved from it.

Phases (VERIFY_PHASES narrows them):

  whole    the whole-body card onto Manny_Rig (a Spear in ITS right hand, no Camera Setup), a bare
           Manny skeleton (no camera) - twins: weapon_r on the card's place in its hand, camera_root
           on its place on the root, camera_bone on camera_root (0.001 cm / deg); Manny_Rig's
           weapon_r still following its spear (the spear moved, not the bone keyed); a Camera Setup
           standing on both after it; and onto Creep_Rig (another body, the camera bones new): the
           helpers' displacement from their rests the card's (turn, and place x the size).
  hand     the right-hand card onto a fresh skeleton: weapon_r keyed, camera_root not.
  mirror   the right-hand card mirrored: weapon_l keyed, weapon_r not.
  undo     the whole card, then ONE Ctrl+Z: no key on the helpers, no camera.
  anim     a 0..10 animation card of the source onto a fresh skeleton: weapon_r / camera_root /
           camera_bone on the source's on every frame (twin), a Camera Setup after.
  road     the skeleton road (`skeletonimport._transfer`) from the source onto a Creep skeleton
           carrying a Camera Setup: torn down and set up again, camera_root and weapon_r on the
           source's place relative to their parents on every frame.

Spec: docs/superpowers/specs/2026-10-20-camera-and-weapon-bones-design.md
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
PLUGIN = os.path.normpath(os.environ.get("POSELIB_PLUGIN") or
                          os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(_plugin, quiet=True)
cmds.currentUnit(time="ntsc")
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)

import maya_rigs  # noqa: E402
from maya_scenesetup import bonedrive, camera, catalog, character, equip  # noqa: E402
from maya_uebridge import skeletonimport  # noqa: E402
from maya_poselib import animapply, animcapture, apply, capture, scene  # noqa: E402
from maya_poselib import posemath as pm  # noqa: E402

PHASES = [p.strip() for p in os.environ.get(
    "VERIFY_PHASES", "whole,hand,mirror,undo,anim,road").split(",") if p.strip()]
OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []
TOL_CM, TOL_DEG = 1e-3, 1e-3
AT = 5


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


def rel(a, b):
    return pm.rigid(a) * pm.rigid(b).inverse()


def go(t):
    cmds.currentTime(t, update=True)


def evaluate(t):
    go(t + 1)
    go(t)


def cm_deg(a, b):
    return (pm.position(a) - pm.position(b)).length(), pm.angle(a, b)


def add(key):
    before_rigs = set(r.namespace for r in maya_rigs.rigs())
    before_bare = set(skeletonimport.bare_roots())
    character.add_character(catalog.character_by_key(key))
    cmds.select(clear=True)
    new_rigs = [r for r in maya_rigs.rigs() if r.namespace not in before_rigs]
    if new_rigs:
        return new_rigs[0].skeleton_root, new_rigs[0]
    new = [r for r in skeletonimport.bare_roots() if r not in before_bare]
    return new[0], None


def bone(root, name):
    for j in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                          fullPath=True) or []):
        if j.split("|")[-1].split(":")[-1] == name:
            return j
    return None


def key_delta(node, attr, frames, deltas):
    base = cmds.getAttr(node + "." + attr)
    for t, d in zip(frames, deltas):
        cmds.setKeyframe(node, attribute=attr, time=t, value=base + d)


def has_keys(node):
    return bool(cmds.keyframe(node, query=True, keyframeCount=True))


def source():
    root, _rig = add("Manny")
    b = lambda n: bone(root, n)                                   # noqa: E731
    key_delta(b("pelvis"), "rotateY", (0, 10), (0, 20))
    key_delta(b("hand_r"), "rotateZ", (0, 10), (0, 25))
    key_delta(b("weapon_r"), "translateX", (0, 10), (0, 6))
    key_delta(b("weapon_r"), "rotateX", (0, 10), (0, 30))
    key_delta(b("camera_root"), "translateZ", (0, 10), (0, 10))
    key_delta(b("camera_root"), "rotateX", (0, 10), (0, 15))
    key_delta(b("camera_bone"), "rotateY", (0, 10), (0, 10))
    cmds.playbackOptions(minTime=0, maxTime=10, animationStartTime=0, animationEndTime=10)
    evaluate(AT)
    truth = dict((t, {"weapon": rel(W(b("weapon_r")), W(b("hand_r"))),
                      "camera": rel(W(b("camera_root")), W(root)),
                      "bone": rel(W(b("camera_bone")), W(b("camera_root")))})
                 for t in range(0, 11) if go(t) is None or True)
    go(AT)
    say(equip.to_hand(root, "R", catalog.by_key("LongSword_02")))
    camera.setup(b("camera_root"), 0, 10)
    evaluate(AT)
    gate("source: the sword drives weapon_r", bool(bonedrive.driving_weapon(b("weapon_r"))))
    gate("source: the camera drives camera_root", bool(camera.camera_for(b("camera_root"))))
    drift = max(max(cm_deg(rel(W(b("weapon_r")), W(b("hand_r"))), truth[AT]["weapon"])),
                max(cm_deg(rel(W(b("camera_root")), W(root)), truth[AT]["camera"])))
    gate("source: the take kept through the sword and the camera", drift < TOL_CM, "%.2e" % drift)
    return root, truth


def check_twin(label, root, truth, t=AT):
    b = lambda n: bone(root, n)                                   # noqa: E731
    evaluate(t)
    w = cm_deg(rel(W(b("weapon_r")), W(b("hand_r"))), truth[t]["weapon"])
    c = cm_deg(rel(W(b("camera_root")), W(root)), truth[t]["camera"])
    k = cm_deg(rel(W(b("camera_bone")), W(b("camera_root"))), truth[t]["bone"])
    worst = max(w + c + k)
    return worst, w, c, k


def phase_whole(src, truth):
    data, note = capture.build_pose([src], frame=AT)
    gate("whole card saved", data is not None, note)
    rig_root, rig = add("Manny_Rig")
    say(equip.to_hand(rig_root, "R", catalog.by_key("Spear_01")))
    spear = bonedrive.driving_weapon(bone(rig_root, "weapon_r"))
    skel_root, _ = add("Manny")
    creep_root, creep = add("Creep_Rig")
    go(AT)
    for label, root in (("Manny_Rig", rig_root), ("Manny skeleton", skel_root)):
        ok, text = apply.apply_onto(data, root)
        say("  ", label, ":", text)
        worst, w, c, k = check_twin(label, root, truth)
        gate("whole onto %s: weapon_r, camera_root, camera_bone on the card's" % label,
             ok and worst < TOL_CM, "weapon %.2e/%.2e camera %.2e/%.2e bone %.2e/%.2e" % (w + c + k))
        gate("whole onto %s: a Camera Setup after it" % label,
             bool(camera.camera_for(bone(root, "camera_root"))))
    gate("Manny_Rig: weapon_r still follows its spear",
         bonedrive.driving_weapon(bone(rig_root, "weapon_r")) == spear and has_keys(spear))
    # Creep_Rig: another body, its camera bones new - the displacement from the rests carried
    rest_card = data["bones"]
    rests = dict((leaf, pm.matrix(b["rest"])) for leaf, b in scene.skeleton(
        scene.character_of(creep_root))[0].items())
    ok, text = apply.apply_onto(data, creep_root)
    say("   Creep_Rig :", text)
    evaluate(AT)
    scale = pm.scale_between(rest_card, scene.skeleton(scene.character_of(creep_root))[0],
                             pm.pairs(rest_card, scene.skeleton(scene.character_of(creep_root))[0]))
    for name, parent in (("weapon_r", "hand_r"), ("camera_root", "root")):
        src_rest = rel(pm.matrix(rest_card[name]["rest"]), pm.matrix(rest_card[parent]["rest"]))
        src_now = rel(pm.matrix(rest_card[name]["world"]), pm.matrix(rest_card[parent]["world"]))
        dst_rest = rel(rests[name], rests[parent])
        dst_now = rel(W(bone(creep_root, name)), W(bone(creep_root, parent)))
        turn_src = pm.angle(src_now, src_rest)
        turn_dst = pm.angle(dst_now, dst_rest)
        move_src = (pm.position(src_now) - pm.position(src_rest)).length() * scale
        move_dst = (pm.position(dst_now) - pm.position(dst_rest)).length()
        gate("whole onto Creep_Rig: %s turned and moved as the card's from its rest" % name,
             ok and abs(turn_src - turn_dst) < 0.05 and abs(move_src - move_dst) < 0.05,
             "turn %.3f/%.3f deg, move %.3f/%.3f cm (x%.3f)" % (turn_dst, turn_src, move_dst,
                                                              move_src, scale))
    gate("whole onto Creep_Rig: a Camera Setup after it",
         bool(camera.camera_for(bone(creep_root, "camera_root"))))
    return data


def phase_hand(src):
    data, note = capture.build_pose([bone(src, "hand_r")], frame=AT)
    root, _ = add("Manny")
    go(AT)
    ok, text = apply.apply_onto(data, root)
    say("   hand :", text)
    gate("hand card: weapon_r keyed, camera_root not, no camera",
         ok and has_keys(bone(root, "weapon_r")) and not has_keys(bone(root, "camera_root"))
         and not camera.camera_for(bone(root, "camera_root")))
    return data


def phase_mirror(hand):
    root, _ = add("Manny")
    go(AT)
    ok, text = apply.apply_onto(hand, root, mirror=True)
    say("   mirror :", text)
    gate("mirrored hand card: weapon_l keyed, weapon_r not",
         ok and has_keys(bone(root, "weapon_l")) and not has_keys(bone(root, "weapon_r")))


def phase_undo(whole):
    root, _ = add("Manny")
    go(AT)
    ok, text = apply.apply_onto(whole, root)
    had = camera.camera_for(bone(root, "camera_root"))
    cmds.undo()
    gate("one Ctrl+Z: no helper key, no camera",
         ok and had and not has_keys(bone(root, "weapon_r")) and
         not has_keys(bone(root, "camera_root")) and
         not camera.camera_for(bone(root, "camera_root")))


def phase_anim(src, truth):
    header, frames, note = animcapture.build_animation([src], start=0, end=10)
    gate("animation card saved", header is not None, note)
    root, _ = add("Manny")
    go(0)
    ok, text = animapply.apply_onto(header, frames, root)
    say("   anim :", text)
    worst = max(check_twin("anim", root, truth, t)[0] for t in range(0, 11))
    gate("animation onto a skeleton: the helpers on the source's on every frame",
         ok and worst < TOL_CM, "%.2e" % worst)
    gate("animation: a Camera Setup after it", bool(camera.camera_for(bone(root, "camera_root"))))
    # onto a rig whose right hand holds a spear: the spear keyed on every frame, the bone on it
    rig_root, _rig = add("Manny_Rig")
    say(equip.to_hand(rig_root, "R", catalog.by_key("Spear_01")))
    spear = bonedrive.driving_weapon(bone(rig_root, "weapon_r"))
    go(0)
    ok, text = animapply.apply_onto(header, frames, rig_root)
    say("   anim rig :", text)
    worst = max(check_twin("anim rig", rig_root, truth, t)[0] for t in range(0, 11))
    gate("animation onto Manny_Rig with a spear: the helpers on the source's on every frame",
         ok and worst < 0.01, "%.2e" % worst)
    gate("animation onto Manny_Rig: the spear keyed on every frame, still driving weapon_r",
         bonedrive.driving_weapon(bone(rig_root, "weapon_r")) == spear and
         cmds.keyframe(spear + ".rotateX", query=True, keyframeCount=True) >= 11,
         cmds.keyframe(spear + ".rotateX", query=True, keyframeCount=True))


def phase_road(src, truth):
    root, _ = add("Creep")
    cam_root = bone(root, "camera_root")
    camera.setup(cam_root, 0, 10)
    gate("road: the Creep skeleton has camera bones and a Camera Setup",
         bool(cam_root and camera.camera_for(cam_root)))
    gate("road: no refusal over our camera", skeletonimport.onto_refusal(root) == "",
         skeletonimport.onto_refusal(root))
    result = skeletonimport._transfer(src, root, 0, 10, None)
    say("   road :", result)
    gate("road: the camera set up again", bool(camera.camera_for(bone(root, "camera_root"))) and
         "camera set up" in (result.get("camera") or ""), result.get("camera"))
    worst = 0.0
    for t in range(0, 11):
        evaluate(t)
        for name, parent, key in (("camera_root", "root", "camera"),
                                  ("weapon_r", "hand_r", "weapon")):
            got = rel(W(bone(root, name)), W(bone(root, parent)))
            worst = max(worst, max(cm_deg(got, truth[t][key])))
    gate("road: camera_root and weapon_r on the clip's places on their parents", worst < TOL_CM,
         "%.2e" % worst)


def main():
    cmds.file(new=True, force=True)
    src, truth = source()
    whole = hand = None
    if "whole" in PHASES or "undo" in PHASES:
        whole = phase_whole(src, truth) if "whole" in PHASES else \
            capture.build_pose([src], frame=AT)[0]
    if "hand" in PHASES or "mirror" in PHASES:
        hand = phase_hand(src)
    if "mirror" in PHASES:
        phase_mirror(hand)
    if "undo" in PHASES:
        phase_undo(whole)
    if "anim" in PHASES:
        phase_anim(src, truth)
    if "road" in PHASES:
        phase_road(src, truth)


try:
    main()
except Exception:
    say(traceback.format_exc())
    RESULTS.append(False)
say("%d of %d gates failed" % (RESULTS.count(False), len(RESULTS)))
