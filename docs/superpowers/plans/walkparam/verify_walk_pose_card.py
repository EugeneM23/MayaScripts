"""verify_walk_pose_card.py - Walk Builder's pose from a Pose Library card (2026-10-15), mayapy standalone.

The animator's walk `asd` and pose `two_handed_sword` COPIED into a temp walks folder (never their folder), a temp
Pose Library; the plugin's Manny UE5 skeleton imported twice. Gates:

1. migrate moves the old .wpose poses into the library as cards of `Walk poses`;
2. the walk under the sword from its .wpose and from its migrated card key the same curves;
3. the walked skeleton keeps the card's path and a copy of its bones;
4. the card edited (its pelvis moved): the next re-key takes it;
5. the card deleted: the re-key walks on from the copy, and the line says so;
6. a skeleton walked by an old build (memo pose name, no card) re-keys through the migrated card.

Run: & 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' verify_walk_pose_card.py
"""
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PLUGIN = os.path.join(REPO, "SkeldarAnim")
ASSETS = os.path.join(PLUGIN, "assets")
MINE = os.environ.get("WALKS_HOME", "C:/Users/MY PC/Documents/maya/SkeldarWalks")
sys.path.insert(0, PLUGIN)

import maya.standalone                                       # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                     # noqa: E402

from maya_walk import scene as sw                            # noqa: E402
from maya_walk import cards                                  # noqa: E402
from maya_poselib import store                               # noqa: E402

FAILED = []


def gate(n, ok, text):
    print("%s gate %d: %s" % ("PASS" if ok else "FAIL", n, text))
    if not ok:
        FAILED.append(n)


def ma_import(path, namespace):
    before = set(cmds.ls(type="joint", long=True) or [])
    cmds.file(path, i=True, namespace=namespace, ignoreVersion=True, preserveReferences=False)
    new = set(cmds.ls(type="joint", long=True) or []) - before

    def top(j):
        above = cmds.listRelatives(j, parent=True, fullPath=True)
        return not above or cmds.nodeType(above[0]) != "joint"
    return min([j for j in new if top(j)], key=lambda p: (p.count("|"), p))


def curves(root):
    """{leaf.channel: [values]} of every joint under `root`, every frame of the walk."""
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    out = {}
    for j in joints:
        for ch in ("rotateX", "rotateY", "rotateZ", "translateX", "translateY", "translateZ"):
            keys = cmds.keyframe(j, attribute=ch, query=True, valueChange=True)
            if keys:
                out[j.rsplit("|", 1)[-1].split(":")[-1] + "." + ch] = np.array(keys)
    return out


def worst(a, b):
    return max(float(np.abs(a[k] - b[k]).max()) for k in a) if set(a) == set(b) else float("inf")


temp = tempfile.mkdtemp()
try:
    walks = os.path.join(temp, "walks")
    library = os.path.join(temp, "library").replace("\\", "/")
    os.makedirs(walks)
    os.makedirs(library)
    for name in ("asd.walk.gz", "two_handed_sword.wpose.gz"):
        shutil.copy(os.path.join(MINE, name), walks)
    sw.WALKS = walks
    cmds.optionVar(stringValue=(store.ROOT_VAR, library))
    cmds.loadPlugin("matrixNodes", quiet=True)
    cmds.loadPlugin("quatNodes", quiet=True)

    made = cards.migrate(walks, library)
    card = library + "/" + cards.MIGRATED_FOLDER + "/two_handed_sword.pose"
    gate(1, made == ["two_handed_sword"] and os.path.isdir(card), "migrated %s" % made)

    given = dict(sw.ALL_DEFAULTS, pose=1.0)
    a = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "a")
    b = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "b")
    # the old road: the .wpose by name (the migrated card would be taken: hide it for this press)
    shutil.move(card, card + "_aside")
    sw.apply(a, "asd", given, "two_handed_sword")
    shutil.move(card + "_aside", card)
    rel = cards.relative(card, library)
    _, _, line = sw.apply(b, "asd", given, None, pose_card=rel)
    diff = worst(curves(a), curves(b))
    gate(2, diff < 1e-6, "the .wpose and its card key the same curves: worst %.2e" % diff)

    memo = sw.memo_of(b)
    copy = cards.unpack(sw.pose_copy(b))
    gate(3, memo.get("pose_card") == rel and memo.get("pose") == "two_handed_sword" and copy is not None
         and len(copy) == len(cards.read_card(card)[1]), "marker %s, copy of %d bones" %
         (memo.get("pose_card"), len(copy or {})))

    #  the card edited as Update from selection would: spine_03 turned 20 deg about its own X, its children where
    #  they stood (the pose is carried by rotations, so a moved pelvis alone would take the feet along)
    before = curves(b)
    data = store.read(card)
    world = np.array(data["bones"]["spine_03"]["world"], float).reshape(4, 4)
    c, s = np.cos(np.radians(20.0)), np.sin(np.radians(20.0))
    turn = np.array([[1, 0, 0, 0], [0, c, s, 0], [0, -s, c, 0], [0, 0, 0, 1]], float)
    data["bones"]["spine_03"]["world"] = list((turn @ world).reshape(16))
    store.replace(card, data)
    sw.apply(b, "asd", given, None, pose_card=rel)
    after = curves(b)
    moved = float(np.abs(after["spine_03.rotateX"] - before["spine_03.rotateX"]).max()
                  + np.abs(after["spine_03.rotateY"] - before["spine_03.rotateY"]).max()
                  + np.abs(after["spine_03.rotateZ"] - before["spine_03.rotateZ"]).max())
    gate(4, moved > 5.0, "the card edited: spine_03's keys moved %.1f deg" % moved)

    shutil.rmtree(card)
    _, _, line = sw.apply(b, "asd", given, None, pose_card=rel)
    diff = worst(after, curves(b))
    gate(5, diff < 1e-6 and "is gone - using the copy" in line, "the card deleted: from the copy, worst %.2e | %s"
         % (diff, line.split(" | ")[-2] if " | " in line else line))

    store.write(library, cards.MIGRATED_FOLDER, "two_handed_sword", {"format": store.FORMAT, "kind": "character",
                "bones": cards.unpack(sw.pose_copy(b)), "character": {"label": "x"}, "members": [], "objects": []})
    sw.apply(a, "asd", given, "two_handed_sword")              # an old build's memo: a name, no card
    gate(6, sw.memo_of(a).get("pose_card") == rel, "an old name keyed through its card: %s"
         % sw.memo_of(a).get("pose_card"))
finally:
    shutil.rmtree(temp, ignore_errors=True)

print("verify_walk_pose_card: %d of 6 gates failed" % len(FAILED))
