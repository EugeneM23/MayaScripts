"""verify_walk_cycle_card.py - Walk Builder's walk cycle from a Pose Library animation card (2026-10-15), mayapy
standalone.

The animator's walks `asd` and `dw` COPIED into a temp walks folder (never their folder), a temp Pose Library;
the plugin's Manny UE5 skeleton imported three times. Gates:

1. migrate_walks moves the old .walk.gz walks into the library as animation cards of `Walk cycles`;
2. `asd` from its file and from its migrated card key the same curves (the card drops scale and rounds to 9
   decimals: within 1e-3 deg / cm);
3. the walked skeleton names the card as its walk; Pick reads it back;
4. Save from a skeleton walking `dw`: as a card and as a file (the old road), both walked under the sword pose,
   key the same curves (within 0.05: a pose amplifies the card's rounding);
5. the card edited (the pelvis 3 cm higher on every frame): the next re-key takes it;
6. the card deleted: the walk it gave keys on.

Run: & 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' verify_walk_cycle_card.py
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
TOTAL = 6


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
    """{leaf.channel: [values]} of every joint under `root`."""
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    out = {}
    for j in joints:
        for ch in ("rotateX", "rotateY", "rotateZ", "translateX", "translateY", "translateZ"):
            keys = cmds.keyframe(j, attribute=ch, query=True, valueChange=True)
            if keys:
                out[j.rsplit("|", 1)[-1].split(":")[-1] + "." + ch] = np.array(keys)
    return out


def worst(a, b):
    if set(a) != set(b) or any(len(a[k]) != len(b[k]) for k in a):
        return float("inf")
    return max(float(np.abs(a[k] - b[k]).max()) for k in a)


temp = tempfile.mkdtemp()
try:
    walks = os.path.join(temp, "walks")
    library = os.path.join(temp, "library").replace("\\", "/")
    os.makedirs(walks)
    os.makedirs(library)
    for name in ("asd.walk.gz", "dw.walk.gz", "two_handed_sword.wpose.gz"):
        shutil.copy(os.path.join(MINE, name), walks)
    sw.WALKS = walks
    cmds.optionVar(stringValue=(store.ROOT_VAR, library))
    cmds.loadPlugin("matrixNodes", quiet=True)
    cmds.loadPlugin("quatNodes", quiet=True)

    made = cards.migrate_walks(walks, library)
    asd_rel = cards.walk_card("asd")
    gate(1, sorted(made) == ["asd", "dw"] and os.path.isdir(cards.absolute(asd_rel, library)),
         "migrated %s" % made)

    given = dict(sw.ALL_DEFAULTS)
    a = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "a")
    b = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "b")
    sw.apply(a, "asd", given)
    asd_card = sw.card_walk(asd_rel)
    _, _, line = sw.apply(b, asd_card, given)
    diff = worst(curves(a), curves(b))
    gate(2, diff < 1e-3, "asd from its file and from its card: worst %.2e | %s" % (diff, line.split(" | ")[0]))

    name, knobs, _, _ = sw.pick(b)
    gate(3, sw.memo_of(b).get("walk") == asd_card and name == asd_card,
         "the marker names %s; Pick reads %s" % (sw.memo_of(b).get("walk"), sw.walk_label(name)))

    #  Save's road: a skeleton walking dw, saved as a card, walked again from the card under the sword
    c = ma_import(os.path.join(ASSETS, "Manny_Skeleton.ma"), "c")
    sw.apply(c, "dw", given)
    saved, line = sw.save_walk_card(c, "dw_saved")
    as_file = sw.save_walk(c, "dw_file")[0]                  # the old road from the same skeleton
    card = cards.absolute(saved[len(sw.CARD):], library)
    sword = dict(given, pose=1.0)
    sw.apply(a, as_file, sword, "two_handed_sword")
    sw.apply(b, saved, sword, "two_handed_sword")
    diff = worst(curves(a), curves(b))
    #  0.05: under a pose the legs' IK and Balance's carry amplify the card's rounding (9-decimal quaternions,
    #  1e-6 cm) - asd from its file and its card read 1.3e-2 there, against 2.8e-4 with no pose (gate 2)
    gate(4, os.path.isdir(card) and diff < 0.05, "Save: a card and a file of one skeleton, walked under the "
         "sword: worst %.2e cm/deg" % diff)

    before = curves(b)
    header = store.read(card)
    frames = store.read_frames(card)
    slot = frames["bones"].index("pelvis")
    world = [list(row) for row in frames["world"]]
    for row in world:
        row[7 * slot + 5] += 3.0
    store.replace(card, header, frames={"bones": frames["bones"], "world": world, "drive": frames["drive"]})
    sw.apply(b, saved, sword, "two_handed_sword")
    after = curves(b)
    moved = float(np.abs(after["pelvis.translateY"] - before["pelvis.translateY"]).max())
    gate(5, moved > 0.5, "the card edited (pelvis +3): the pelvis's keys moved %.2f" % moved)

    shutil.rmtree(card)
    _, _, line = sw.apply(b, saved, sword, "two_handed_sword")
    diff = worst(after, curves(b))
    gate(6, diff < 1e-6, "the card deleted: the walk it gave keys on, worst %.2e" % diff)
finally:
    shutil.rmtree(temp, ignore_errors=True)

print("verify_walk_cycle_card: %d of %d gates failed" % (len(FAILED), TOTAL))
