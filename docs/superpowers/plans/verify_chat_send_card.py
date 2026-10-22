"""Chat: a Pose Library card sent and received (2026-10-22), mayapy standalone against a live server.

    MAYA_APP_DIR=<scratch> mayapy docs/superpowers/plans/verify_chat_send_card.py [server]

A Manny UE5 skeleton, hand_r turned 40 deg; the pose saved as a card into a scratch library; A sends
the card into a dm; B downloads it (the card's files byte for byte), puts it into the library
(«From Chat») and applies it onto the skeleton put back at rest - hand_r where the card has it.
Two throwaway accounts, deleted at the end.
"""
import filecmp
import os
import shutil
import sys
import tempfile
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim")))

import maya.standalone  # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402

from PySide6 import QtCore  # noqa: E402

import maya_chat  # noqa: E402
from maya_chat import api as A  # noqa: E402
from maya_chat import files as F  # noqa: E402
from maya_chat import session as S  # noqa: E402
from maya_chat import store as ST  # noqa: E402

SERVER = sys.argv[1] if len(sys.argv) > 1 else maya_chat.SERVER
APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
RESULTS = []
DEFERRED = []
F.DEFER = DEFERRED.append


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def wait(cond, timeout=60.0):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        APP.processEvents(QtCore.QEventLoop.AllEvents, 50)
        while DEFERRED:
            DEFERRED.pop(0)()
        if cond():
            return time.monotonic() - start
    return None


def world(node):
    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def apart(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def same_tree(a, b):
    cmp = filecmp.dircmp(a, b)
    return not (cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files)


def main():
    root = tempfile.mkdtemp(prefix="chatcard_")
    library = os.path.join(root, "library")
    os.makedirs(library)
    from maya_poselib import capture, store
    cmds.optionVar(stringValue=(store.ROOT_VAR, library))
    tag = uuid.uuid4().hex[:6]
    a = S.Session(SERVER, ST.Store(os.path.join(root, "a")))
    b = S.Session(SERVER, ST.Store(os.path.join(root, "b")))
    try:
        from maya_scenesetup import catalog, character
        character.add_character(catalog.default_character())
        hand = [j for j in cmds.ls("hand_r", long=True, type="joint")][0]
        skel_root = hand.split("|")
        skel_root = "|".join(skel_root[:[i for i, p in enumerate(skel_root) if p == "root"][0] + 1])
        rest = cmds.getAttr(hand + ".rotate")[0]
        cmds.setAttr(hand + ".rotateZ", rest[2] + 40)
        posed = world(hand)
        cmds.select(skel_root, replace=True)
        data, note = capture.build_pose()
        card = store.write(library, "", "Fist", data)
        gate("a pose card in the library", os.path.isfile(os.path.join(card, "pose.json")), card)

        a.sign_in("vka_" + tag)
        mb = b.sign_in("vkb_" + tag)
        wait(lambda: a.state.status == "online" and b.state.status == "online", 15)
        dm = a.open_dm(mb["id"])
        wait(lambda: dm in b.state.chats, 15)

        cid = F.send_card(a, dm, card, "a fist")
        took = wait(lambda: any(m.get("cid") == cid for m in b.state.messages.get(dm, [])), 120)
        msg = [m for m in b.state.messages.get(dm, []) if m.get("cid") == cid]
        f = (msg[0] if msg else {}).get("file") or {}
        gate("B gets the card as a pose", f.get("kind") == "pose" and f.get("name") == "Fist.pose"
             and msg[0]["text"] == "a fist", "%s in %.1f s" % (f, took or -1))
        landed = []
        F.fetch(b, f, landed.append)
        wait(lambda: bool(landed), 120)
        gate("B's copy is the card, file for file", bool(landed) and same_tree(card, landed[0]), landed)

        line = F.to_library(landed[0])
        copied = os.path.join(library, F.LIBRARY_FOLDER, "Fist.pose")
        gate("into the library, «From Chat»", os.path.isdir(copied) and same_tree(card, copied), line)
        line = F.to_library(landed[0])
        gate("a second copy gets a free name", os.path.isdir(os.path.join(library, F.LIBRARY_FOLDER,
                                                                          "Fist 2.pose")), line)

        cmds.setAttr(hand + ".rotate", *rest)
        gate("the hand is back at rest", apart(world(hand), posed) > 0.01)
        line = F.apply_card(landed[0], {"kind": "character", "root": skel_root})
        gate("applied onto the skeleton: hand_r as the card has it", apart(world(hand), posed) < 1e-3,
             "%s | %.6f" % (line, apart(world(hand), posed)))
    finally:
        for ses in (a, b):
            token = ses.store.token()
            ses.stop()
            if token:
                try:
                    A.Api(SERVER, token).delete_me()
                except A.ChatError as exc:
                    print("could not delete an account: %s" % exc.text)
        shutil.rmtree(root, ignore_errors=True)
    failed = RESULTS.count(False)
    print("%d of %d gates failed" % (failed, len(RESULTS)))
    return failed


if __name__ == "__main__":
    os._exit(1 if main() else 0)
