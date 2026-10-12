"""verify_walk.py - the parametric walk in mayapy standalone, on a temp copy of the animator's cycle.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk.py

Imports Desktop/Walk_01.fbx (copied to a temp folder; never committed) into an ntsc scene, then measures
what Maya plays on the copy: the defaults against the source on every joint and frame; stride, tempo,
lift, width, bob, sway, arms, head, overlap, weight, exaggeration each doing what it says; bone lengths,
the seam, the stance feet; one Ctrl+Z; the source's curves untouched.
"""
import importlib.util
import math
import os
import shutil
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FBX = os.environ.get("WALK_FBX", "C:/Users/MY PC/Desktop/Walk_01.fbx")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel

sw = load("skeldar_walk_under_verify", os.path.join(HERE, "skeldar_walk.py"))
wm = sw.wm
FAILED = []
COUNT = [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


def import_clip():
    folder = tempfile.mkdtemp(prefix="walkverify_")
    path = os.path.join(folder, "Walk_01.fbx")
    shutil.copy(FBX, path)
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.loadPlugin("fbxmaya", quiet=True)
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval("FBXImportSetMayaFrameRate -v false")
    mel.eval('FBXImport -f "%s"' % path.replace("\\", "/"))
    cmds.undoInfo(state=True, infinity=True)
    return folder


def worlds(paths, frames):
    return np.array([[cmds.getAttr(p + ".worldMatrix[0]", time=t) for t in frames] for p in paths]).reshape(
        len(paths), len(frames), 4, 4)


def curve_snapshot(paths):
    out = {}
    for p in paths:
        for c in cmds.listConnections(p, source=True, destination=False, type="animCurve") or []:
            out[c] = (tuple(cmds.keyframe(c, query=True, timeChange=True) or ()),
                      tuple(cmds.keyframe(c, query=True, valueChange=True) or ()))
    return out


def angle(r):
    return math.degrees(float(np.linalg.norm(wm.log_rot(wm.orthonormal(r)))))


def local(w, j, parent, f):
    return wm.orthonormal(w[j, f]) @ wm.orthonormal(w[parent, f]).T


folder = import_clip()
try:
    root = "|Armature|root"
    gate(cmds.objExists(root), "the clip imported: %s" % root)
    walk, source = sw.walk_for(root)
    P, J = walk.P, len(source.joints)
    idx = walk.index
    text = walk.summary()
    flat = walk.travel - np.dot(walk.travel, walk.up) * walk.up
    gate(P == 31 and abs(np.linalg.norm(flat) / 2 - 88.48) < 0.05, text)
    feet = ", ".join("%s on %d +%d" % (s, walk.feet[s].on, walk.feet[s].length) for s in "lr")
    gate(10 <= walk.feet["l"].length <= 16 and 10 <= walk.feet["r"].length <= 16, "stance found: " + feet)
    src = worlds(source.joints, range(0, P + 1))
    before = curve_snapshot(source.joints)

    def run(given, offset=None):
        started = time.time()
        copy, result, line = sw.update(root, given, offset)
        took = time.time() - started
        n = result.frames
        paths = sw.copy_paths(source, copy)
        got = worlds(paths, range(0, n + 1))
        shift = np.array(cmds.xform(copy, query=True, worldSpace=True, translation=True)) - source.top_world[3, :3]
        got[:, :, 3, :3] -= shift
        return copy, result, got, took, line

    # 1. the defaults
    copy, result, got, took, line = run(None)
    pos_err = float(np.abs(got[:, :, 3, :3] - src[:, :, 3, :3]).max())
    rot_err = float(np.abs(got[:, :, :3, :3] - src[:, :, :3, :3]).max())
    gate(pos_err < 1e-3 and rot_err < 1e-4,
         "defaults = the source on %d joints x %d frames: %.6f cm, %.7f (%.2f s)" % (J, P + 1, pos_err, rot_err, took))
    print("        " + line)
    keys = cmds.keyframe(sw.copy_paths(source, copy)[idx["root"]] + ".translateX", query=True, timeChange=True)
    gate(keys[0] == 0 and keys[-1] == P and len(keys) == P + 1, "keys on frames %g..%g, %d" % (keys[0], keys[-1], len(keys)))
    side_off = float(np.dot(np.array(cmds.xform(copy, query=True, worldSpace=True, translation=True))
                            - source.top_world[3, :3], walk.side))
    gate(abs(side_off - sw.DEFAULT_OFFSET) < 1e-6, "the copy stands %.1f cm to the left" % side_off)

    legs = dict((s, [idx["%s_%s" % (b, s)] for b in ("thigh", "calf", "foot")]) for s in "lr")

    def lengths(w, s):
        th, ca, fo = legs[s]
        return (np.linalg.norm(w[ca, :, 3, :3] - w[th, :, 3, :3], axis=1),
                np.linalg.norm(w[fo, :, 3, :3] - w[ca, :, 3, :3], axis=1))

    def stance_spread(w, s, stride=1.0):
        """How far the ankle moves over its stance (the heel rising is in it); a stance past the cycle's end
        continues on the next cycle, moved by that cycle's travel."""
        foot = walk.feet[s]
        frames = [(foot.on + i) for i in range(foot.length + 1)]
        p = np.array([w[idx["foot_" + s], f % P, 3, :3] + (stride * walk.travel if f >= P else 0.0)
                      for f in frames])
        return float(np.ptp(p, axis=0).max())

    def seam(w, n):
        """The pose in the pelvis's space on the last frame against the first (row vectors: W . P^-1)."""
        pel = idx["pelvis"]
        a = np.array([w[j, 0] @ np.linalg.inv(w[pel, 0]) for j in range(J)])
        b = np.array([w[j, n] @ np.linalg.inv(w[pel, n]) for j in range(J)])
        return float(np.abs(a - b).max())

    src_spread = dict((s, stance_spread(src, s)) for s in "lr")
    src_len = dict((s, lengths(src, s)) for s in "lr")

    # 2. stride
    for stride in (0.7, 1.3):
        copy, result, got, took, line = run({"stride": stride})
        travel = float(np.linalg.norm(got[idx["root"], P, 3, :3] - got[idx["root"], 0, 3, :3]))
        spread = dict((s, stance_spread(got, s, stride)) for s in "lr")
        length_err = max(float(np.abs(np.array(lengths(got, s)) - np.array(src_len[s])).max()) for s in "lr")
        gate(abs(travel - stride * np.linalg.norm(walk.travel)) < 0.01
             and all(spread[s] <= src_spread[s] + 1e-3 for s in "lr") and length_err < 1e-3
             and seam(got, P) < 2e-3,
             "stride %.1f: travel %.2f cm (x%.3f), stance spread L %.3f R %.3f (source %.3f %.3f), lengths "
             "%.6f, seam %.5f | %s" % (stride, travel, travel / np.linalg.norm(walk.travel), spread["l"],
                                       spread["r"], src_spread["l"], src_spread["r"], length_err, seam(got, P), line))

    # 3. a long stride: the reach
    copy, result, got, took, line = run({"stride": 1.6})
    ext = max(float((np.linalg.norm(got[legs[s][2], :, 3, :3] - got[legs[s][0], :, 3, :3], axis=1)
                     / (lengths(got, s)[0] + lengths(got, s)[1]) - walk.reach[s]).max()) for s in "lr")
    drop = np.array(result.info["drop"])
    gate(ext < 1e-4 and result.info["short"] < 1e-3 and drop.max() > 1.0 and drop.min() < 0.5 * drop.max(),
         "stride 1.6: legs never straighter than the source's (%.6f), the pelvis down %.1f cm at most, %.1f at "
         "least | %s" % (ext, drop.max(), drop.min(), line))

    # 4. tempo
    for tempo in (25, 40):
        copy, result, got, took, line = run({"tempo": tempo})
        keys = cmds.keyframe(sw.copy_paths(source, copy)[idx["pelvis"]] + ".translateY", query=True, timeChange=True)
        travel = float(np.linalg.norm(got[idx["root"], tempo, 3, :3] - got[idx["root"], 0, 3, :3]))
        gate(len(keys) == tempo + 1 and keys[-1] == tempo and seam(got, tempo) < 2e-3
             and abs(travel - np.linalg.norm(walk.travel)) < 0.01,
             "tempo %d: %d keys to frame %g, seam %.5f, travel %.2f | %s" % (tempo, len(keys), keys[-1],
                                                                          seam(got, tempo), travel, line))

    # 5. lift: the swing above the line between the footprints (the model's own measure, scaled)
    copy, result, got, took, line = run({"lift": 2.0})
    j = idx["foot_l"]
    foot = walk.feet["l"]
    swing = [f for f in range(P) if (f - foot.on) % P > foot.length]
    ratios = []
    for f in swing:
        up_src = float(src[j, f, 3, 1])
        up_new = float(got[j, f, 3, 1])
        base = float(walk.foot_target("l", float(f), 1.0, 0.0, 0.0)[1][1])   # lift 0: the straight blend
        if up_src - base > 2.0:
            ratios.append((up_new - base) / (up_src - base))
    gate(len(ratios) > 3 and abs(min(ratios) - 2.0) < 1e-3 and abs(max(ratios) - 2.0) < 1e-3,
         "lift 2: the left swing %d frames above its blend x%.4f..%.4f" % (len(ratios), min(ratios), max(ratios)))

    # 6. width
    copy, result, got, took, line = run({"width": 10.0})
    ml, mr = int(round(walk.feet["l"].mid)) % P, int(round(walk.feet["r"].mid)) % P
    gap = lambda w: float(np.dot(w[idx["foot_l"], ml, 3, :3] - w[idx["foot_r"], mr, 3, :3], walk.side))
    gate(abs(gap(got) - gap(src) - 10.0) < 1e-3, "width 10: footprints %.2f cm apart, the source %.2f" % (gap(got), gap(src)))

    # 7. pelvis
    pel = idx["pelvis"]
    height = lambda w: w[pel, :P, 3, :3] @ walk.up
    aside = lambda w: w[pel, :P, 3, :3] @ walk.side
    copy, result, got, took, line = run({"bob": 0.0})
    flat_bob = height(got) + np.array(result.info["drop"][:P])
    copy2, result2, got2, took2, line2 = run({"bob": 2.0})
    dev2 = height(got2) + np.array(result2.info["drop"][:P]) - walk.pelvis_mean[2] - walk.origin @ walk.up
    dev1 = height(src) - walk.pelvis_mean[2] - walk.origin @ walk.up
    gate(float(np.ptp(flat_bob)) < 1e-3 and float(np.abs(dev2 - 2 * dev1).max()) < 1e-3,
         "bob 0: the pelvis level (%.5f, drop up to %.1f); bob 2: twice the source's bob (%.5f)"
         % (np.ptp(flat_bob), max(result.info["drop"]), np.abs(dev2 - 2 * dev1).max()))
    copy, result, got, took, line = run({"sway": 0.0})
    gate(float(np.ptp(aside(got))) < 1e-3, "sway 0: the pelvis on its line (%.5f; the source sways %.2f cm)"
         % (np.ptp(aside(got)), np.ptp(aside(src))))

    # 8. upper body
    up_l, clav_l = idx["upperarm_l"], idx["clavicle_l"]
    copy, result, got, took, line = run({"arms": 0.0})
    still = [angle(local(got, up_l, clav_l, f) @ local(got, up_l, clav_l, 0).T) for f in range(P)]
    copy2, result2, got2, took2, line2 = run({"arms": 2.0})
    mean = walk.lmean[up_l]
    f_peak = max(range(P), key=lambda f: angle(local(src, up_l, clav_l, f) @ mean.T))
    ratio = angle(local(got2, up_l, clav_l, f_peak) @ mean.T) / angle(local(src, up_l, clav_l, f_peak) @ mean.T)
    gate(max(still) < 1e-3 and abs(ratio - 2.0) < 1e-3,
         "arms 0: the upper arm still on its clavicle (%.5f deg); arms 2: x%.5f at its peak frame %d"
         % (max(still), ratio, f_peak))
    copy, result, got, took, line = run({"head": 0.0})
    head = idx["head"]
    turn = max(angle(wm.orthonormal(got[head, f]) @ wm.orthonormal(got[head, 0]).T) for f in range(P))
    gate(turn < 1e-3, "head 0: the head's world turn %.5f deg (the source's %.2f)"
         % (turn, max(angle(wm.orthonormal(src[head, f]) @ wm.orthonormal(src[head, 0]).T) for f in range(P))))
    copy, result, got, took, line = run({"overlap": 3.0})
    hand, fore = idx["hand_l"], idx["lowerarm_l"]
    late = max(angle(local(got, hand, fore, f) @ local(src, hand, fore, f - 3).T) for f in range(3, P))
    gate(late < 1e-3, "overlap 3: the hand on its forearm plays the source 3 frames late (%.5f deg)" % late)

    # 9. weight and exaggeration
    copy, result, got, took, line = run({"weight": 1.0})

    def knee(w, s, f):
        th, ca, fo = legs[s]
        a, b = w[ca, f, 3, :3] - w[th, f, 3, :3], w[fo, f, 3, :3] - w[ca, f, 3, :3]
        return math.degrees(math.acos(float(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b))))

    contact = walk.feet["l"].on
    low_src, low_new = float(height(src).min()), float(height(got).min())
    gate(low_new < low_src - 0.3 * (float(height(src).mean()) - low_src)
         and knee(got, "l", contact) > knee(src, "l", contact),
         "weight 1: the pelvis down to %.2f (the source %.2f), the left knee at its contact %.1f deg (%.1f)"
         % (low_new, low_src, knee(got, "l", contact), knee(src, "l", contact)))
    copy, result, got, took, line = run({"exaggeration": 0.0})
    spine = idx["spine_03"]
    turn_pel = max(angle(wm.orthonormal(got[pel, f]) @ wm.orthonormal(got[pel, 0]).T) for f in range(P))
    turn_spine = max(angle(local(got, spine, walk.parents[spine], f) @ local(got, spine, walk.parents[spine], 0).T)
                     for f in range(P))
    spread = dict((s, stance_spread(got, s)) for s in "lr")
    gate(turn_pel < 1e-3 and turn_spine < 1e-3 and all(spread[s] <= src_spread[s] + 1e-3 for s in "lr"),
         "exaggeration 0: pelvis %.5f, spine_03 %.5f deg still; the stance feet as the source's (%.3f %.3f)"
         % (turn_pel, turn_spine, spread["l"], spread["r"]))

    # 10. undo, the source, the speed
    copy, result, got, took, line = run({"stride": 1.3})
    copy, result, got, took, line = run({"stride": 0.7})
    cmds.undo()
    paths = sw.copy_paths(source, copy)
    back = worlds([paths[idx["root"]]], [0, P])
    travel = float(np.linalg.norm(back[0, 1, 3, :3] - back[0, 0, 3, :3]))
    gate(abs(travel - 1.3 * np.linalg.norm(walk.travel)) < 0.01,
         "one Ctrl+Z puts the stride-1.3 keys back (travel %.2f cm)" % travel)
    after = curve_snapshot(source.joints)
    gate(after == before and len(before) > 400, "the source's %d curves untouched" % len(before))
    gate(took < 1.5, "an update takes %.2f s" % took)
finally:
    shutil.rmtree(folder, ignore_errors=True)

print("\n%d gates, %d failed%s" % (COUNT[0], len(FAILED), (": " + str(FAILED)) if FAILED else ""))
