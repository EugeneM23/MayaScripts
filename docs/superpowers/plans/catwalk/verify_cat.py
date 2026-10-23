"""verify_cat.py - our CAT keyed onto the plugin's skeletons, in mayapy standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/catwalk/verify_cat.py

Manny UE5 and Creep skeletons imported from SkeldarAnim/assets; every preset applied through
skeldar_cat.apply: the keys reproduce the model's worlds, bone lengths unchanged, the cycle closes with
its travel, the planted foot's ankle still mid-stance, both feet down / flight as the preset says; a
re-key from the stored place does not drift; one Ctrl+Z takes the keys away; a moved and turned
skeleton walks from where it stands."""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))     # the repository's plugin, never the installed copy
sys.path.insert(0, HERE)
import catmodel as cm          # noqa: E402
import skeldar_cat as tool     # noqa: E402

FAILED, COUNT = [], [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


def ma_import(path, namespace):
    before = set(cmds.ls(type="joint", long=True) or [])
    cmds.file(path, i=True, namespace=namespace, ignoreVersion=True, preserveReferences=False)
    new = set(cmds.ls(type="joint", long=True) or []) - before

    def is_top(j):
        above = cmds.listRelatives(j, parent=True, fullPath=True)
        return not above or cmds.nodeType(above[0]) != "joint"
    return min([j for j in new if is_top(j)], key=lambda p: (p.count("|"), p))


def world(path, t):
    return np.array(cmds.getAttr(path + ".worldMatrix[0]", time=t)).reshape(4, 4)


def check(root, label, presets):
    bones, skel, _ = tool._read(root)
    paths = dict((leaf, b["path"]) for leaf, b in bones.items())
    for name in presets:
        knobs = cm.preset(name, tool._fps())
        line = tool.apply(root, knobs)
        memo = tool._memo(root)
        place = np.array(memo["place"]).reshape(4, 4)
        start = memo["start"]
        cycle = cm.generate(skel, knobs, tool._fps(), place=place)
        T = cycle.info["frames"]
        body = [l for l in skel.order if not l.lower().startswith(("ik_",))]
        worst = 0.0
        for f in (0, T // 3, T // 2, T):
            for leaf in body:
                worst = max(worst, float(np.abs(world(paths[leaf], start + f)[3, :3] - cycle.frames[f][leaf][3, :3]).max()))
        gate(worst < 1e-3, "%s %s: the keys place every bone as the model does (worst %.2e cm)" % (label, name, worst))
        lengths = 0.0
        for leaf in body:
            p = skel.parent[leaf]
            if p is None or p == skel.root or leaf == skel.pelvis:
                continue
            r = np.linalg.norm(skel.pos[leaf] - skel.pos[p])
            for f in (0, T // 4, T // 2):
                lengths = max(lengths, abs(np.linalg.norm(world(paths[leaf], start + f)[3, :3]
                                                          - world(paths[p], start + f)[3, :3]) - r))
        gate(lengths < 1e-3, "%s %s: bone lengths kept (worst %.2e cm)" % (label, name, lengths))
        seam = max(float(np.abs(world(paths[l], start + T)[3, :3] - world(paths[l], start)[3, :3]
                                - cycle.travel @ place[:3, :3]).max()) for l in body)
        gate(seam < 1e-3, "%s %s: the cycle closes on its travel (%.2e cm)" % (label, name, seam))
        foot = paths[skel.legs["l"]["foot"]]
        d = knobs["duty"]
        frames = [f for f in range(T) if 0.22 * d < (f / float(T) - knobs["phase_l"]) % 1.0 < 0.5 * d]
        slide = max([float(np.linalg.norm(world(foot, start + a)[3, :3] - world(foot, start + b)[3, :3]))
                     for a, b in zip(frames, frames[1:])] or [0.0])
        gate(slide < 1e-3, "%s %s: the planted left ankle stands still mid-stance (%.2e cm a frame)" % (label, name, slide))
        if name in ("Jog", "Run"):
            gate(cycle.info["flight"] > 0, "%s %s: both feet in the air %d frames" % (label, name, cycle.info["flight"]))
        else:                                       # a walk: a foot is always down, both for a moment
            gate(cycle.info["flight"] == 0 and cycle.info["double"] > 0,
                 "%s %s: never both feet in the air, both down %d frames" % (label, name, cycle.info["double"]))
        print("   " + line)
    return bones, skel


def main():
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    manny = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "manny")
    creep = ma_import(os.path.join(ASSETS, "Creep_Skeleton.ma"), "creep")
    bones, skel = check(manny, "Manny", cm.PRESET_ORDER)
    check(creep, "Creep", ("Walk", "Run"))

    # a re-key from the stored place does not drift
    pelvis = bones[skel.pelvis]["path"]
    tool.apply(manny, cm.preset("Walk", tool._fps()))
    start = tool._memo(manny)["start"]
    before = world(pelvis, start)
    cmds.currentTime(start + 7)
    tool.apply(manny, cm.preset("Walk", tool._fps()))
    gate(np.abs(world(pelvis, start) - before).max() < 1e-6,
         "a re-key at another frame keys the same first frame (the place is kept)")

    # one Ctrl+Z
    curve = cmds.listConnections(pelvis + ".rotateY", source=True, destination=False) or []
    tool.apply(manny, cm.preset("Run", tool._fps()))
    run_val = cmds.getAttr(pelvis + ".translateY", time=3)
    cmds.undo()
    walk_val = cmds.getAttr(pelvis + ".translateY", time=3)
    gate(abs(run_val - walk_val) > 1e-3 and bool(curve), "one Ctrl+Z puts the walk back (pelvis y %.2f -> %.2f)"
         % (run_val, walk_val))

    # a moved and turned skeleton walks from where it stands
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    m2 = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "moved")
    holder = cmds.group(m2, name="carrier")                   # turned about world up by its group
    cmds.setAttr(holder + ".translate", 150.0, 0.0, -80.0)
    cmds.setAttr(holder + ".rotateY", 90.0)
    m2 = cmds.listRelatives(holder, children=True, fullPath=True, type="joint")[0]
    cmds.currentTime(1)
    stands = world(m2, 1)[3, :3]                              # the group pivots about its own centre
    tool.apply(m2, cm.preset("Walk", tool._fps()), True)
    start = tool._memo(m2)["start"]
    b2, s2, _ = tool._read(m2)
    pel = b2[s2.pelvis]["path"]
    p0 = world(pel, start)[3, :3]
    p1 = world(pel, start + int(cm.preset("Walk", tool._fps())["step_time"]) * 2)[3, :3]
    heading = p1 - p0
    off = np.linalg.norm((p0 - stands) * np.array([1, 0, 1]))
    gate(off < 6.0, "the walk starts where the skeleton stands: pelvis %.1f cm from the root's place (%.1f, %.1f)"
         % (off, stands[0], stands[2]))
    gate(heading[0] > abs(heading[2]) * 5, "and goes the way it faces (+X after a 90 turn): travel (%.1f, %.1f)"
         % (heading[0], heading[2]))

    # Match reference: a skeleton keyed from frame 3 with a jog of its own is the reference; another one,
    # keyed with a walk, is matched to it and plays in step with it
    import catmatch
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    reference = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "ref")
    ours = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "ours")
    jog = cm.preset("Jog", tool._fps())
    jog.update(twist=11.0, arm_out=18.0, bend_spine_03=8.0, shoulders=-5.0, cycle_offset=-7.0)
    cmds.playbackOptions(minTime=3)
    tool.apply(reference, jog, True)
    cmds.playbackOptions(minTime=0)
    tool.apply(ours, cm.preset("Walk", tool._fps()), True)
    line = tool.match(reference, ours)
    print("   " + line)
    skel_r, ref_frames, (a, b) = tool.read_cycle(reference)
    skel_o, our_frames, (c, d) = tool.read_cycle(ours)
    gate((a, b) == (c, d), "the matched cycle is keyed on the reference's frames (%d-%d, %d-%d)" % (a, b, c, d))
    mr, mo = catmatch.measure(skel_r, ref_frames), catmatch.measure(skel_o, our_frames)
    gate(mr["left_contact"] == mo["left_contact"], "its left foot lands on the reference's frame (%d, %d)"
         % (mr["left_contact"], mo["left_contact"]))
    errors = catmatch.compare(skel_r, ref_frames, our_frames, mr, mo)
    gate(max(errors.values()) < 4.0, "every bone turns as the reference's within 4 deg: %s"
         % ", ".join("%s %.1f" % kv for kv in errors.items()))
    gate(abs(mo["stride"] - mr["stride"]) < 0.01 and not mo["spot"], "it travels as the reference does (%.3f, %.3f)"
         % (mr["stride"], mo["stride"]))

    # Reset: every knob back to the default walk, the mode kept, the same skeleton keyed again
    mode = tool.remembered()["on_spot"]
    print("   " + tool.reset())
    walk = cm.preset("Walk", tool._fps())
    memo = tool._memo(ours)
    off = [k for k in walk if k != "on_spot" and abs(memo["knobs"][k] - walk[k]) > 1e-9]
    gate(not off and memo["knobs"]["on_spot"] == mode and tool.remembered() == memo["knobs"],
         "Reset puts every knob on the default walk and keeps the mode (%s)" % (off or "all equal"))
    skel_o, keyed, (c, d) = tool.read_cycle(ours)
    model = cm.generate(skel_o, memo["knobs"], tool._fps(), place=np.array(memo["place"]).reshape(4, 4)).frames
    worst = max(float(np.abs(keyed[f][leaf][3, :3] - model[f][leaf][3, :3]).max())
                for f in range(0, len(model), 4) for leaf in skel_o.order if not leaf.lower().startswith("ik_"))
    gate(worst < 1e-3 and c == memo["start"], "and keys the skeleton with it from frame %d (worst %.2e cm)"
         % (c, worst))
    print("\n%d gates, %d failed %s" % (COUNT[0], len(FAILED), FAILED))


main()
