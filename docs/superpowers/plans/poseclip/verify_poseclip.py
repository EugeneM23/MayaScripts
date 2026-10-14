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

    if OUT:
        np.savez(OUT, clip=source.worlds, goblin=results["goblin"], sword=results["two_handed_sword"],
                 names=np.array(source.names), parents=np.array(source.parents), reference=np.array(a.reference),
                 floor=a.floor)
    failed = [n for n, ok in GATES if not ok]
    print("\n%d of %d gates failed%s" % (len(failed), len(GATES), (": " + "; ".join(failed)) if failed else ""))


main()
