"""verify_poseclip - mayapy STANDALONE proof of poseclip (docs/superpowers/specs/2026-10-14-pose-on-clip-design.md).

The plugin's Manny UE5 skeleton added (its own Add Character, read only), the stop's FBX imported into a
namespace and keyed onto it by this tool's writer (every joint by its world matrix), then the spec's proof:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_poseclip.py <the stop's FBX>

The FBX: Unreal's M_Neutral_Sprint_Stop_F_Lfoot (the Game Animation Sample) as the bridge exports it - not in
the repository. Poses from the animator's walks folder (`SKELDAR_WALKS`, default Documents/maya/SkeldarWalks).
"""
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "SkeldarAnim"))
FBX = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("TEMP", ""), "maya_uebridge",
                                                         "M_Neutral_Sprint_Stop_F_Lfoot.fbx")
WALKS = os.environ.get("SKELDAR_WALKS") or os.path.join(os.environ["USERPROFILE"], "Documents", "maya", "SkeldarWalks")
OUT = os.environ.get("POSECLIP_OUT", "")

import maya.standalone  # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

sys.path.insert(0, HERE)
sys.path.insert(0, PLUGIN)
for plugin in ("fbxmaya", "matrixNodes", "quatNodes"):
    cmds.loadPlugin(plugin, quiet=True)
cmds.optionVar(stringValue=("skeldarWalkFolder", WALKS))

import poseclip as model  # noqa: E402
import poseclip_maya as pcm  # noqa: E402

GATES = []


def gate(name, ok, detail):
    GATES.append((name, bool(ok)))
    print("%s  %-62s %s" % ("PASS" if ok else "FAIL", name, detail))


def setup():
    from maya_scenesetup import catalog, character
    cmds.currentUnit(time="ntsc")
    character.add_character(catalog.character_for("Manny", "skeleton"))
    root = [j for j in cmds.ls(type="joint", long=True) if j.endswith("|root") and "_Character|" in j][0]
    cmds.namespace(add="stopsrc")
    cmds.namespace(set="stopsrc")
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval("FBXImportSetMayaFrameRate -v false")
    mel.eval('FBXImport -f "%s"' % FBX.replace("\\", "/"))
    cmds.namespace(set=":")
    cmds.currentUnit(time="ntsc")
    src = [j for j in cmds.ls("stopsrc:*", type="joint", long=True) if not cmds.listRelatives(j, parent=True, type="joint")][0]
    clip, start, src_joints = pcm.read_clip(src)
    targets = pcm._joints(root)
    by_leaf = dict((pcm._leaf(p), p) for p in targets)
    rows = [clip.index[pcm._leaf(p)] for p in targets if pcm._leaf(p) in clip.index]
    paths = [p for p in targets if pcm._leaf(p) in clip.index]
    pcm.write_worlds(paths, clip.worlds[rows], start)
    cmds.namespace(removeNamespace="stopsrc", deleteNamespaceContent=True)
    from maya_scenesetup import cliplabel             # the label the bridge puts under an imported clip (locked)
    cliplabel.label_skeleton(root, "M_Neutral_Sprint_Stop_F_Lfoot")
    cmds.playbackOptions(minTime=start, maxTime=start + clip.F - 1, animationStartTime=start,
                         animationEndTime=start + clip.F - 1)
    cmds.currentTime(start)
    return root, clip, by_leaf


def copy_of(source_root):
    uuid = cmds.ls(source_root, uuid=True)[0]
    out = []
    for t in cmds.ls("*." + pcm.MARK, objectsOnly=True, long=True) or []:
        import json
        if json.loads(cmds.getAttr(t + "." + pcm.MARK)).get("source") == uuid:
            out.append(t)
    return out


def copy_clip(copy):
    root = [j for j in cmds.listRelatives(copy, children=True, type="joint", fullPath=True) or []][0]
    clip, start, joints = pcm.read_clip(root)
    return clip


def angle(a, b):
    c = (np.trace(a.T @ b) - 1.0) / 2.0
    return math.degrees(math.acos(min(max(c, -1.0), 1.0)))


def main():
    t0 = time.time()
    root, clip, by_leaf = setup()
    source, start, joints = pcm.read_clip(root)
    print("setup %.1f s: %s, %d joints, %d frames from %d" % (time.time() - t0, root, source.J, source.F, start))
    a = model.Analysis(source)
    statics, note = pcm.read_statics(joints, source, a.mid)
    print("reference %s, contacts L %s R %s, %s" % (a.reference, a.feet["l"]["contacts"], a.feet["r"]["contacts"], note))
    right = pcm._right_of(a)
    ix = source.index
    mesh = [m for m in cmds.ls(type="mesh", long=True, noIntermediate=True) if m.startswith(pcm._top_node(root) + "|")][0]

    # 1. share 0: the copy plays the clip, its mesh on its own joints
    pcm.apply("goblin", share=0.0, node=root)
    copy = copy_of(root)[0]
    played = copy_clip(copy)
    pos = played.worlds[:, :, 3, :3] - 150.0 * right
    dpos = float(np.abs(pos - source.worlds[:, :, 3, :3]).max())
    drot = float(np.abs(played.worlds[:, :, :3, :3] - source.worlds[:, :, :3, :3]).max())
    gate("share 0: the copy plays the clip", dpos < 1e-3 and drot < 1e-5, "%.2e cm, %.2e" % (dpos, drot))
    copy_mesh = copy + mesh[len(pcm._top_node(root)):]
    worst = 0.0
    for f in (start, start + 22, start + 100):
        cmds.currentTime(f)
        for v in (100, 2000, 9000):
            p0 = np.array(cmds.pointPosition("%s.vtx[%d]" % (mesh, v), world=True))
            p1 = np.array(cmds.pointPosition("%s.vtx[%d]" % (copy_mesh, v), world=True))
            worst = max(worst, float(np.linalg.norm(p1 - p0 - 150.0 * right)))
    gate("the copy's mesh follows the copy's joints", worst < 1e-3, "%.2e cm off the original + the offset" % worst)

    # 2. share 1, motion 0 in the reference: the body is the pose
    name, bones = pcm.load_pose("goblin")
    pose = model.prepare(a, statics, bones)
    before = dict((c, cmds.keyframe(c, query=True, valueChange=True)) for c in
                  cmds.listConnections(root, source=True, destination=False, type="animCurve") or [])
    pcm.apply("goblin", share=1.0, motion=0.0, node=root)
    played = copy_clip(copy_of(root)[0])
    ra, rb = a.reference
    torso = [j for j, k in enumerate(a.kind) if k in ("torso", "pelvis")]
    worst = max(angle(played.worlds[j, f, :3, :3] @ a.heading[f].T, pose["rel"][j]) for j in torso for f in range(ra, rb + 1))
    gate("motion 0: torso and head on the pose (relative)", worst < 0.01, "%.4f deg" % worst)
    height = played.worlds[ix["pelvis"], ra:rb + 1, 3, 1] - a.floor
    gate("motion 0: the pelvis at the pose's height", float(np.abs(height - pose["height"]).max()) < 0.01,
         "%.4f cm (pose %.2f)" % (float(np.abs(height - pose["height"]).max()), pose["height"]))
    feet = 0.0
    for s in model.SIDES:
        j = ix["foot_" + s]
        c0, c1 = a.feet[s]["contacts"][-1]
        drift = float(np.linalg.norm(source.worlds[j, ra:rb + 1, 3, :3] - source.worlds[j, c0:c1 + 1, 3, :3].mean(axis=0),
                                     axis=1).max())
        off = float(np.linalg.norm(played.worlds[j, ra:rb + 1, 3, :3] - 150.0 * right - pose["feet"][s][3, :3], axis=1).max())
        feet = max(feet, off - drift)
    gate("motion 0: the feet on the pose's stance (up to the clip's own drift)", feet < 0.01, "%.4f cm over the drift" % feet)

    # 3. the goblin and the sword, share 1, motion 1
    results = {}
    for pose_name in ("goblin", "two_handed_sword"):
        status = pcm.apply(pose_name, share=1.0, motion=1.0, node=root)
        played = copy_clip(copy_of(root)[0])
        w = played.worlds.copy()
        w[:, :, 3, :3] -= 150.0 * right
        results[pose_name] = w
        name, bones = pcm.load_pose(pose_name)
        pose = model.prepare(a, statics, bones)
        slide = 0.0
        for s in model.SIDES:
            for joint in ("foot_" + s, "ball_" + s):
                j = ix[joint]
                for c0, c1 in a.feet[s]["contacts"]:
                    for f in range(c0 + 1, c1 + 1):
                        moved = float(np.linalg.norm(w[j, f, 3, :3] - w[j, f - 1, 3, :3]))
                        own = float(np.linalg.norm(source.worlds[j, f, 3, :3] - source.worlds[j, f - 1, 3, :3]))
                        slide = max(slide, moved - own)
        gate("%s: no planted foot moves more than the clip's" % pose_name, slide < 0.05, "%.4f cm a frame over it" % slide)
        lengths = 0.0
        for j in range(source.J):
            p = source.parents[j]
            if p < 0:
                continue
            new = np.linalg.norm(w[j, :, 3, :3] - w[p, :, 3, :3], axis=1)
            old = np.linalg.norm(source.worlds[j, :, 3, :3] - source.worlds[p, :, 3, :3], axis=1)
            if a.kind[j] not in ("helper", "pelvis"):      # the pelvis against the root is no bone
                lengths = max(lengths, float(np.abs(new - old).max()))
        gate("%s: every bone the clip's length" % pose_name, lengths < 1e-3, "%.2e cm" % lengths)
        com = np.tensordot(a.masses, w[:, :, 3, :3], axes=(0, 0))
        pivots = dict((s, 0.5 * (w[ix["foot_" + s], :, 3, :3] + w[ix["ball_" + s], :, 3, :3])) for s in model.SIDES)
        support = model.support_path(a.weights, pivots)
        shift = a.stillness[:, None] * np.einsum("i,fij->fj", pose["offset"] - a.ref_offset, a.heading)
        off = (com - support) - (a.com - a.support + shift)
        down = a.feet["l"]["down"] | a.feet["r"]["down"]
        worst = float(np.linalg.norm(off[down][:, [0, 2]], axis=1).max())
        gate("%s: the centre of mass over the feet as the clip's (+ the pose's)" % pose_name, worst < 0.1, "%.4f cm" % worst)
        h = w[ix["pelvis"], :, 3, 1] - a.floor
        rule = pose["height"] * (source.worlds[ix["pelvis"], :, 3, 1] - a.floor) / a.h_ref
        over = float((h - rule).max())
        gate("%s: the pelvis never above the height rule" % pose_name, over < 1e-3,
             "%.4f cm over; sunk up to %.2f cm" % (over, float((rule - h).max())))
        if pose["grip"]:
            hl, hr = w[ix["hand_l"]], w[ix["hand_r"]]
            rel = np.array([hl[f] @ np.linalg.inv(hr[f]) for f in range(source.F)])
            spread = float(np.abs(rel - rel[0]).max())
            gate("%s: the two-handed grip held" % pose_name, spread < 1e-3, "%.2e" % spread)
        print("   " + status)

    from maya_scenesetup import cliplabel
    copies = dict((pcm._short(t), t) for t in copy_of(root))
    texts = sorted(cliplabel.text_of(t) for c in copies.values()
                   for t in cmds.listRelatives(c, allDescendents=True, type="transform", fullPath=True) or []
                   if cmds.attributeQuery("skeldarClipLabel", node=t, exists=True))
    original = [cliplabel.text_of(t) for t in cliplabel.labels_of(root)]
    gate("the copies' labels read the clip + the pose, the original's the clip", texts == [
        "M_Neutral_Sprint_Stop_F_Lfoot + goblin", "M_Neutral_Sprint_Stop_F_Lfoot + two_handed_sword"]
        and original == ["M_Neutral_Sprint_Stop_F_Lfoot"], "%s / %s" % (texts, original))

    cmds.select(clear=True)
    found = pcm.character_root()
    copy_root = [j for j in cmds.listRelatives(copy_of(root)[0], children=True, type="joint", fullPath=True)][0]
    cmds.select(copy_root)
    via_copy = pcm.character_root()
    label = cliplabel.labels_of(root)[0]
    cmds.select(label)
    via_label = pcm.character_root()
    cmds.select(clear=True)
    gate("which character: nothing selected, a copy, the clip label all name the original",
         found == root and via_copy == root and via_label == root, "%s / %s / %s" % (found, via_copy, via_label))

    # 4. the copy: one undo removes it, a second run replaces it, the original untouched
    after = dict((c, cmds.keyframe(c, query=True, valueChange=True)) for c in before)
    same = all(np.allclose(before[c], after[c], atol=1e-12) for c in before)
    gate("the original's curves untouched", same and len(before) > 0, "%d curves on the root" % len(before))
    names = sorted(pcm._short(t) for t in copy_of(root))
    gate("a second run of a pose replaces its copy (one a pose)", names == ["Manny_Skeleton_goblin_Character",
         "Manny_Skeleton_two_handed_sword_Character"], str(names))
    goblin = [t for t in copy_of(root) if "goblin" in t][0]
    first = cmds.ls(goblin, uuid=True)[0]
    pcm.apply("goblin", share=0.5, node=root)
    cmds.undo()
    names = sorted(pcm._short(t) for t in copy_of(root))
    back = [t for t in copy_of(root) if "goblin" in t]
    gate("one undo takes the run back (the previous copy back)", len(names) == 2 and back and
         cmds.ls(back[0], uuid=True)[0] == first, str(names))

    # 5. the window's core: one copy re-keyed in place, live
    import poseclip_tool as tool
    cmds.select(clear=True)
    started = time.time()
    first = tool.run("goblin", model.knobs(), 150.0)
    made = time.time() - started
    standing = list(pcm.copies(cmds.ls(root, uuid=True)[0], tool=True))
    uuid = cmds.ls(standing[0], uuid=True)[0] if standing else None
    before_y = copy_clip(standing[0]).worlds[ix["pelvis"], :, 3, 1] if standing else None
    started = time.time()
    tool.run("goblin", model.knobs(pelvis_height=8.0), 150.0)
    rekey = time.time() - started
    standing = list(pcm.copies(cmds.ls(root, uuid=True)[0], tool=True))
    after_y = copy_clip(standing[0]).worlds[ix["pelvis"], :, 3, 1]
    ra, rb = a.reference
    raised = float(np.median(after_y[ra:rb + 1] - before_y[ra:rb + 1]))
    gate("the window: a slider re-keys its one copy in place", len(standing) == 1 and
         cmds.ls(standing[0], uuid=True)[0] == uuid and abs(raised - 8.0) < 0.05,
         "made in %.1f s, re-keyed in %.1f s, the pelvis +%.2f cm in the idle (asked 8)" % (made, rekey, raised))
    tool.run("two_handed_sword", model.knobs(), -150.0)
    standing = list(pcm.copies(cmds.ls(root, uuid=True)[0], tool=True))
    texts = [cliplabel.text_of(t) for t in cmds.listRelatives(standing[0], allDescendents=True, type="transform",
                                                                fullPath=True) or []
             if cmds.attributeQuery("skeldarClipLabel", node=t, exists=True)]
    gate("the window: another pose re-keys and relabels the same copy", len(standing) == 1 and
         cmds.ls(standing[0], uuid=True)[0] == uuid and texts == ["M_Neutral_Sprint_Stop_F_Lfoot + two_handed_sword"],
         str(texts))
    note = tool.delete_copy()
    gate("the window: Delete copy", not pcm.copies(cmds.ls(root, uuid=True)[0], tool=True) and
         len(copy_of(root)) == 2, "%s; the script's copies stay: %d" % (note, len(copy_of(root))))

    # 6. two poses, overlap, the stop starting on a cycle (a Walk Builder run keyed onto a second skeleton)
    import gzip
    import json as _json
    from maya_scenesetup import catalog, character
    before_tops = set(cmds.ls(assemblies=True, long=True))
    character.add_character(catalog.character_for("Manny", "skeleton"))
    cycle_top = [t for t in cmds.ls(assemblies=True, long=True) if t not in before_tops][0]
    cycle_root = [j for j in cmds.listRelatives(cycle_top, allDescendents=True, type="joint", fullPath=True)
                  if not cmds.listRelatives(j, parent=True, type="joint")][0]
    walk = _json.load(gzip.open(os.path.join(WALKS, "RunFast.walk.gz"), "rt"))
    cw = np.array(walk["worlds"]).reshape(len(walk["names"]), -1, 4, 4)
    targets = pcm._joints(cycle_root)
    rows = [walk["names"].index(pcm._leaf(p)) for p in targets if pcm._leaf(p) in walk["names"]]
    paths = [p for p in targets if pcm._leaf(p) in walk["names"]]
    pcm.write_worlds(paths, cw[rows], 0)
    cmds.select(clear=True)
    tool.session(node=root, reload=True)
    tool.use_cycle(cycle_root)
    text = tool.run("goblin", model.knobs(), 150.0, start="two_handed_sword")
    info = tool._state()["last"]
    standing = list(pcm.copies(cmds.ls(root, uuid=True)[0], tool=True))
    played = copy_clip(standing[0]).worlds.copy()
    played[:, :, 3, :3] -= 150.0 * right
    session = tool.session()
    cyc = session.cycle
    aligned = cyc.sample(info["cycle"]["phase"]) @ info["cycle"]["place"]
    pairs = [(j, cyc.clip.index[n]) for j, n in enumerate(source.names) if n in cyc.clip.index]
    first = max(float(np.abs(played[j, 0] - aligned[jc]).max()) for j, jc in pairs)
    gate("the stop's first frame is the cycle's frame (placed)", first < 1e-3,
         "%.2e at the cycle's frame %.2f" % (first, info["cycle"]["phase"]))
    slide = 0.0
    for s_ in model.SIDES:
        j = ix["foot_" + s_]
        for c0, c1 in a.feet[s_]["contacts"]:
            for f in range(max(c0, 0) + 1, min(c1, 10) + 1):
                moved = float(np.linalg.norm(played[j, f, 3, :3] - played[j, f - 1, 3, :3]))
                own = float(np.linalg.norm(source.worlds[j, f, 3, :3] - source.worlds[j, f - 1, 3, :3]))
                slide = max(slide, moved - own)
    gate("into the stop from the cycle: no planted foot slides", slide < 0.2, "%.3f cm a frame over the clip's" % slide)
    texts = [cliplabel.text_of(t) for t in cmds.listRelatives(standing[0], allDescendents=True, type="transform",
                                                                fullPath=True) or []
             if cmds.attributeQuery("skeldarClipLabel", node=t, exists=True)]
    springs = info.get("overlap") or {}
    gate("two poses and overlap", info.get("two_poses") and springs.get("arms", 0.0) > 0.0 and
         texts == ["M_Neutral_Sprint_Stop_F_Lfoot + two_handed_sword > goblin"],
         "%s; overlap trunk %.1f, head %.1f deg, hands %.1f cm" % (texts, springs.get("torso", 0.0),
                                                                  springs.get("head", 0.0), springs.get("arms", 0.0)))
    print("   " + text)

    # 7. Walk Builder's tools (spec addendum 4): the cycle's posture as the start, a side's knob, Leg match
    still = dict(torso_drag=0.0, head_drag=0.0, arm_drag=0.0, spine=0.0, pelvis_rot=0.0, head=0.0, bob=0.0,
                 balance=0.0, leg_match=0.0)
    tool.run("goblin", model.knobs(**still), 150.0, start=tool.CYCLE)
    info = tool._state()["last"]
    standing = list(pcm.copies(cmds.ls(root, uuid=True)[0], tool=True))
    played = copy_clip(standing[0]).worlds.copy()
    C = session.posture.C
    k = model.knobs(**still)
    e = a.stillness_at(k["final_speed"])
    run_frames = [f for f in range(int(k["from_cycle"]) + 1, source.F) if e[f] < 1e-9]
    trunk = [j for j, kind in enumerate(a.kind) if kind in ("pelvis", "torso") and j in C["rel"]]
    worst = 0.0
    for f in run_frames:
        for j in trunk:
            got = model._batch_orthonormal(played[j, f, :3, :3]) @ a.heading[f].T
            worst = max(worst, math.degrees(float(np.linalg.norm(model._log3(got.T @ C["rel"][j])))))
    gate("the cycle's posture as the start: the run stands in it (the clip's motion off)",
         info.get("start_kind") == "cycle" and run_frames and worst < 1e-3,
         "%d trunk bones over %d run frames %.2e deg off the cycle's mean posture" % (len(trunk), len(run_frames), worst))
    # the clip's motion on (the springs off, so the turns are the formula's): each trunk bone sits off the cycle's
    # posture over the run as the clip sits off its own run mean - the cycle's posture, the stop's motion over it
    free = dict(torso_drag=0.0, head_drag=0.0, arm_drag=0.0)
    tool.run("goblin", model.knobs(**free), 150.0, start=tool.CYCLE)
    played = copy_clip(standing[0]).worlds.copy()
    k = model.knobs(**free)
    sa = session.analysis
    e = sa.stillness_at(k["final_speed"])
    run_frames = [f for f in range(int(k["from_cycle"]) + 1, source.F) if e[f] < 1e-9]
    M = session.posture.run(sa, 1.0 - e)
    flat = np.ones(len(run_frames)) / len(run_frames)
    off, worst = [], 0.0
    for j in trunk:
        got = model._weighted_mean_rot(np.array([model._batch_orthonormal(played[j, f, :3, :3]) @ sa.heading[f].T
                                                 for f in run_frames]), flat)
        own = model._weighted_mean_rot(np.array([sa.rel[j, f] for f in run_frames]), flat)
        d_got = math.degrees(float(np.linalg.norm(model._log3(C["rel"][j].T @ got))))
        d_own = math.degrees(float(np.linalg.norm(model._log3(M["rel"][j].T @ own))))
        worst = max(worst, abs(d_got - d_own))
        off.append("%s %.1f/%.1f" % (source.names[j], d_got, d_own))
    texts = [cliplabel.text_of(t) for t in cmds.listRelatives(standing[0], allDescendents=True, type="transform",
                                                                fullPath=True) or []
             if cmds.attributeQuery("skeldarClipLabel", node=t, exists=True)]
    gate("the cycle's posture, the clip's motion on: each trunk bone off it as the clip off its run",
         worst < 0.3 and texts == ["M_Neutral_Sprint_Stop_F_Lfoot + cycle > goblin"],
         "the run's mean turn off the cycle's posture / the clip's off its own run mean: %s; worst %.2f deg; %s"
         % (", ".join(off), worst, texts))
    tool.run("goblin", model.knobs(), 150.0, start=tool.CYCLE)
    base = copy_clip(standing[0]).worlds.copy()
    tool.run("goblin", model.knobs(lift_l=2.5), 150.0, start=tool.CYCLE)
    lifted = copy_clip(standing[0]).worlds.copy()
    up = dict((s_, float((lifted[ix["foot_" + s_], :, 3, 1] - base[ix["foot_" + s_], :, 3, 1]).max())) for s_ in model.SIDES)
    right_same = float(np.abs(lifted[ix["foot_r"], :, 3, :3] - base[ix["foot_r"], :, 3, :3]).max())
    gate("a side's knob: Foot lift L 2.5 lifts the left foot only", up["l"] > 3.0 and right_same < 1e-4,
         "the left foot up to %.1f cm higher, the right moved %.2e cm" % (up["l"], right_same))
    tool.run("goblin", model.knobs(), 150.0, start="two_handed_sword")
    matched = tool._state()["last"]["legs"]["hips"]
    tool.run("goblin", model.knobs(leg_match=0.0), 150.0, start="two_handed_sword")
    unmatched = tool._state()["last"]["legs"]["hips"]
    gate("Leg match: the side-on sword start's hips turned to the run, none with it off", matched > 10.0 and
         unmatched < 1e-6, "the hips turned up to %.1f deg (Leg match 0: %.1f)" % (matched, unmatched))

    # a weapon put in the copy's hand (its constraint drives weapon_r): a re-key leaves that bone to it
    standing = list(pcm.copies(cmds.ls(root, uuid=True)[0], tool=True))
    bone = [j for j in cmds.listRelatives(standing[0], allDescendents=True, type="joint", fullPath=True)
            if j.endswith("|weapon_r")][0]
    holder = cmds.spaceLocator(name="verifyWeaponHolder")[0]
    cmds.cutKey(bone, attribute=list(pcm.CHANNELS), clear=True)    # as the weapon link does: keys off first
    held = cmds.parentConstraint(holder, bone)[0]
    text = tool.run("goblin", model.knobs(pelvis_height=3.0), 150.0)
    gate("a bone something else drives is left to it, and named", cmds.objExists(held) and
         "left to what drives them: weapon_r" in text and
         cmds.listConnections(bone + ".translateX", source=True, destination=False) == [held],
         text.split(" | ")[-2] if " | " in text else text)
    cmds.delete(holder)

    if OUT:
        np.savez(OUT, clip=source.worlds, goblin=results["goblin"], sword=results["two_handed_sword"],
                 names=np.array(source.names), parents=np.array(source.parents), reference=np.array(a.reference),
                 floor=a.floor)
    failed = [n for n, ok in GATES if not ok]
    print("\n%d of %d gates failed%s" % (len(failed), len(GATES), (": " + "; ".join(failed)) if failed else ""))


main()
