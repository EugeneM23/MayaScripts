"""verify_gait.py - Gait Builder keyed onto the plugin's Manny UE5 skeleton through the tool's own press, in mayapy
standalone (no scene of the animator's; the disk cache in a temp folder; the animator's saved walks only read).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/gaitbuilder/verify_gait.py

A CAT preset and a saved walk (asd, when on this machine) applied through skeldar_gait.apply: the keys place every
bone as the model and the retarget do, bone lengths kept, the cycle closes on its travel; the knobs read back on
the keyed skeleton (Speed, Step); a re-key at another frame keeps the stored place; another source on a walked
skeleton keeps its place; one Ctrl+Z takes a press away; a pose at a share lowers the pelvis toward the pose's; the
first read of a walk probes its knobs and the next reads them off disk; the refusals change nothing."""
import os
import shutil
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))     # the repository's plugin, never the installed copy
sys.path.insert(0, HERE)
import gaitload                 # noqa: E402
import aspects as asp           # noqa: E402
import gaitmodel as gm          # noqa: E402
import skeldar_gait as tool     # noqa: E402
from maya_walk import scene as ws, target as wt, files as wf, pose as wp      # noqa: E402

FAILED, COUNT = [], [0]
RESTS = {}          # {root: {leaf: length}} read before anything is keyed
DISK = tempfile.mkdtemp(prefix="skeldar_gait_verify_")
gaitload.DISK = DISK


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


def rest_lengths(root):
    bones, _ = ws.read_bones(root)
    out = {}
    for leaf, b in bones.items():
        parent = b.get("parent")
        if parent and parent in bones:
            out[leaf] = float(np.linalg.norm(np.array(cmds.xform(b["path"], query=True, worldSpace=True,
                                                                 translation=True))
                                             - np.array(cmds.xform(bones[parent]["path"], query=True,
                                                                   worldSpace=True, translation=True))))
    RESTS[root] = out


def world(path, t):
    return np.array(cmds.getAttr(path + ".worldMatrix[0]", time=t)).reshape(4, 4)


def state(source, gait=None, pose="", share=1.0):
    return {"source": source, "pose": pose, "share": share, "parts": list(tool.PARTS), "side": "both",
            "gait": dict(gait or {}), "clean": {}}


def expected(root, st):
    """What the press keys: the retarget's frames of the model's result, from the stored place."""
    source = tool._source(st)
    bones, _ = ws.read_bones(root)
    memo = tool._memo(root)
    retarget = wt.Retarget(source.walk, source.statics, bones, memo.get("place"))
    pose = tool._pose(source, st, root)
    result, base, _ = gaitload.evaluate(source, st["gait"], pose, st["share"] if pose is not None else 0.0)
    frames, info = retarget.frames(result)
    return bones, frames, result, info, int(memo["start"])


def body_leaves(bones):
    return [leaf for leaf in bones if not leaf.lower().startswith(("ik_", "weapon", "camera", "interaction",
                                                                   "center_of_mass"))]


def check_keys(root, st, label):
    """The press, then the keys against the model (place, lengths, the loop): returns what expected() did."""
    started = time.process_time()
    line = tool.apply(root, st)
    took = time.process_time() - started
    bones, frames, result, info, start = expected(root, st)
    n = result.frames
    leaves = body_leaves(bones)
    worst = 0.0
    for f in (0, n // 3, n // 2, n):
        for leaf in leaves:
            want = np.array(list(frames[f][leaf])).reshape(4, 4)
            worst = max(worst, float(np.abs(world(bones[leaf]["path"], start + f)[3, :3] - want[3, :3]).max()))
    gate(worst < 1e-3, "%s: the keys place every bone as the model and the retarget do (worst %.2e cm), %.1f s CPU"
         % (label, worst, took))
    # the lengths over the cycle: constant, and the skeleton's own (the retarget keys its bind's: Manny's file
    # stands 0.006 cm off its bind at one bone, reported)
    lengths, against, which = 0.0, 0.0, ""
    for leaf in leaves:
        parent = bones[leaf].get("parent")
        if not parent or parent not in bones or leaf in ("pelvis", "root") or parent == "root":
            continue
        got = [np.linalg.norm(world(bones[leaf]["path"], start + f)[3, :3] - world(bones[parent]["path"], start + f)[3, :3])
               for f in (0, n // 4, n // 2, 3 * n // 4)]
        lengths = max(lengths, float(np.ptp(got)))
        if abs(got[0] - RESTS[root][leaf]) > against:
            against, which = abs(got[0] - RESTS[root][leaf]), leaf
    gate(lengths < 1e-3 and against < 0.01, "%s: bone lengths constant over the cycle (worst %.2e cm), the skeleton's "
         "own to %.4f cm (%s)" % (label, lengths, against, which))
    travel = world(bones["root"]["path"], start + n)[3, :3] - world(bones["root"]["path"], start)[3, :3]
    seam = max(float(np.abs(world(bones[l]["path"], start + n)[3, :3] - world(bones[l]["path"], start)[3, :3]
                            - travel).max()) for l in leaves)
    gate(seam < 1e-3, "%s: the cycle closes on its travel (%.2e cm)" % (label, seam))
    print("   " + line)
    return bones, result, info, start


def measured(bones, result, info, start):
    """(speed m/s, step cm) off the keyed root: its travel over the cycle."""
    n = result.frames
    a = world(bones["root"]["path"], start)[3, :3]
    b = world(bones["root"]["path"], start + n)[3, :3]
    up = np.array([0.0, 1.0, 0.0])
    d = (b - a) - np.dot(b - a, up) * up
    fps = float(ws._fps())
    strides = getattr(result, "strides", None) or 1
    return float(np.linalg.norm(d)) / (n / fps) / 100.0, float(np.linalg.norm(d))


def main():
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(minTime=1, maxTime=120)
    manny = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "manny")
    other = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "other")
    rest_lengths(manny)
    rest_lengths(other)

    # ---- a CAT preset: its first read probes the knobs ----
    walk_st = state("cat:Walk")
    source = tool._source(walk_st)
    gate(gaitload.needs_probe(source), "a first read of the CAT walk probes its knobs (nothing on disk)")
    bones, result, info, start = check_keys(manny, walk_st, "CAT Walk")
    gate(len(os.listdir(DISK)) == 1, "its responses kept on disk (%s)" % os.listdir(DISK))
    base = gaitload.baseline(source)
    own_speed, own_travel = measured(bones, result, info, start)
    scale = info.get("scale", 1.0)
    gate(abs(own_speed - base["speed"] * scale) < 0.01,
         "the keyed walk's speed is the walk's own: %.3f m/s (measured %.3f x%.2f)" % (own_speed, base["speed"], scale))

    # ---- the knobs read back on the keyed skeleton ----
    asked = base["speed"] * 1.25
    bones, result, info, start = check_keys(manny, state("cat:Walk", {"speed": asked}), "Speed x1.25")
    got, _ = measured(bones, result, info, start)
    gate(abs(got - asked * scale) <= 0.05 * asked, "Speed asked %.3f m/s, keyed %.3f" % (asked * scale, got))
    step = base["step"] + 10.0
    bones, result, info, start = check_keys(manny, state("cat:Walk", {"step": step}), "Step +10 cm")
    _, travel = measured(bones, result, info, start)
    strides = source.walk.strides
    gate(abs(travel / (2.0 * strides) - step * scale) <= 1.0,
         "Step asked %.1f cm, keyed %.1f (the root's travel over %d step(s))" % (step * scale, travel / (2.0 * strides),
                                                                              2 * strides))

    # ---- the stored place ----
    pelvis = bones["pelvis"]["path"]
    tool.apply(manny, walk_st)
    start = tool._memo(manny)["start"]
    before = world(pelvis, start)
    cmds.currentTime(start + 7)
    cmds.move(30.0, 0.0, 20.0, bones["root"]["path"], relative=True, worldSpace=True)
    tool.apply(manny, walk_st)
    gate(np.abs(world(pelvis, start) - before).max() < 1e-6,
         "a re-key at another frame, the root moved, keys the same first frame (the place is kept)")
    run_st = state("cat:Run")
    root_at = world(bones["root"]["path"], start)
    check_keys(manny, run_st, "CAT Run on the walked skeleton")
    gate(np.abs(world(bones["root"]["path"], start)[3, :3] - root_at[3, :3]).max() < 1e-6,
         "another source on a walked skeleton starts where the first did")

    # ---- one Ctrl+Z ----
    cmds.currentTime(start)
    before = [world(bones[l]["path"], start + 5) for l in ("pelvis", "hand_r", "foot_l")]
    tool.apply(manny, state("cat:Sneak"))
    moved = max(float(np.abs(world(bones[l]["path"], start + 5) - b).max())
                for l, b in zip(("pelvis", "hand_r", "foot_l"), before))
    cmds.undo()
    back = max(float(np.abs(world(bones[l]["path"], start + 5) - b).max())
               for l, b in zip(("pelvis", "hand_r", "foot_l"), before))
    gate(moved > 1.0 and back < 1e-6, "one Ctrl+Z takes a press away (it moved %.1f, back to %.1e)" % (moved, back))

    # ---- a refusal changes nothing ----
    cmds.select(clear=True)
    tool._state()["target"] = None
    try:
        tool.apply(None, walk_st)
        refused = False
    except tool.Refusal as exc:
        refused = "select" in str(exc)
    gate(refused, "nothing selected and no target: refused")

    # ---- a saved walk, under a pose ----
    if not os.path.exists(ws.walk_path("asd")):
        print("skip: no saved walk asd")
    else:
        asd_st = state("asd")
        bones2, result2, info2, start2 = check_keys(other, asd_st, "asd")
        plain_pelvis = np.mean([world(bones2["pelvis"]["path"], start2 + f)[3, 1] for f in range(result2.frames)])
        goblin = os.path.join(ws.folder(), "goblin.wpose.gz")
        if os.path.exists(goblin):
            src = tool._source(asd_st)
            prepared = wp.prepare(src.walk, src.statics, wf.load_pose(goblin)[1], gm, wt)
            tool._state()["poses"].clear()
            tool._state()["poses"][(id(src), "goblin")] = prepared
            posed_st = state("asd", pose="goblin", share=1.0)
            bones2, result2, info2, start2 = check_keys(other, posed_st, "asd under the goblin")
            posed = np.mean([world(bones2["pelvis"]["path"], start2 + f)[3, 1] for f in range(result2.frames)])
            gate(posed < plain_pelvis - 10.0, "the goblin lowers the pelvis: %.1f cm against %.1f" % (posed, plain_pelvis))
            half_st = state("asd", pose="goblin", share=0.5)
            bones2, result2, info2, start2 = check_keys(other, half_st, "asd under the goblin at 0.5")
            half = np.mean([world(bones2["pelvis"]["path"], start2 + f)[3, 1] for f in range(result2.frames)])
            gate(posed < half < plain_pelvis, "at half the share half way: %.1f between %.1f and %.1f"
                 % (half, posed, plain_pelvis))
        else:
            print("skip: no goblin pose")
        gaitload._state().clear()
        again = tool._source(asd_st)
        gate(not gaitload.needs_probe(again), "asd read again (another session): its knobs off disk")

    print("%d gates, %d failed" % (COUNT[0], len(FAILED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        shutil.rmtree(DISK, ignore_errors=True)
    sys.exit(code)
