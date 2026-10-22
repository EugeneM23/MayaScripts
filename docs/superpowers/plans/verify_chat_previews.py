"""Chat previews and pictures (2026-10-22) against a live server, no Maya (Qt offscreen).

    $env:QT_QPA_PLATFORM = 'offscreen'
    mayapy docs/superpowers/plans/verify_chat_previews.py [server]

A sends an animation card (its preview sheet and grid), a pose card (its still) and a pasted
picture; B gets each message with its preview's version and grid, reads the preview through the
cache byte for byte as A made it, and downloads the picture whole. Two throwaway accounts.
"""
import os
import shutil
import sys
import tempfile
import time
import uuid

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim")))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..")))

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

import maya_chat  # noqa: E402
from maya_chat import api as A  # noqa: E402
from maya_chat import files as F  # noqa: E402
from maya_chat import session as S  # noqa: E402
from maya_chat import store as ST  # noqa: E402
from maya_chat import thumbs  # noqa: E402
from tests.test_chat_previews import anim_card, picture  # noqa: E402

SERVER = sys.argv[1] if len(sys.argv) > 1 else maya_chat.SERVER
APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
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


def got(ses, chat, cid):
    return [m for m in ses.state.messages.get(chat, []) if m.get("cid") == cid]


def main():
    root = tempfile.mkdtemp(prefix="chatprev_")
    tag = uuid.uuid4().hex[:6]
    a = S.Session(SERVER, ST.Store(os.path.join(root, "a")))
    b = S.Session(SERVER, ST.Store(os.path.join(root, "b")))
    try:
        a.sign_in("vpa_" + tag)
        mb = b.sign_in("vpb_" + tag)
        wait(lambda: a.state.status == "online" and b.state.status == "online", 15)
        dm = a.open_dm(mb["id"])
        wait(lambda: dm in b.state.chats, 15)
        src = os.path.join(root, "src")
        os.makedirs(src)

        card = anim_card(src, cells=24, columns=5, size=96)
        made, sheet = thumbs.from_card(card)
        cid = F.send_card(a, dm, card, "a walk")
        took = wait(lambda: bool(got(b, dm, cid)), 120)
        f = (got(b, dm, cid) or [{}])[0].get("file") or {}
        gate("B gets the animation with its preview and grid", f.get("thumb_v") == 1 and f.get("sheet") ==
             {"cells": 24, "columns": 5, "step": 2, "fps": 30.0}, "%s in %.1f s" % (f.get("sheet"), took or -1))
        cache = thumbs.Cache(os.path.join(root, "b", "thumbs"), lambda: b.api)
        cache.file(f)
        wait(lambda: cache.file(f) is not None, 30)
        path = cache.file(f)
        with open(path, "rb") as handle:
            same = handle.read() == made
        gate("B's preview is the sheet A made, byte for byte", same, path)
        image = cache.image(f)
        gate("it decodes as 5 x 5 cells", image is not None and image.width() == 5 * thumbs.CELL
             and image.height() == 5 * thumbs.CELL, image and (image.width(), image.height()))
        mine = thumbs.cache(a)
        gate("A keeps its own preview without asking the server",
             os.path.isfile(thumbs.path_for(mine.folder, f["id"], 1)))

        pose = os.path.join(src, "Fist.pose")
        os.makedirs(pose)
        with open(os.path.join(pose, "pose.json"), "w") as out:
            out.write("{}")
        picture(os.path.join(pose, "thumbnail.jpg"), 640, 640, "#e07a2c")
        cid = F.send_card(a, dm, pose)
        wait(lambda: bool(got(b, dm, cid)), 120)
        f = (got(b, dm, cid) or [{}])[0].get("file") or {}
        gate("a pose goes with its still and no grid", f.get("thumb_v") == 1 and f.get("sheet") is None, f)

        shot = QtGui.QImage(1600, 900, QtGui.QImage.Format_RGB32)
        shot.fill(QtGui.QColor("#2c8ae0"))
        cid = F.send_image(a, dm, shot, "ref")
        wait(lambda: bool(got(b, dm, cid)), 120)
        msg = (got(b, dm, cid) or [{}])[0]
        f = msg.get("file") or {}
        gate("a pasted picture arrives as a picture with its preview", f.get("kind") == "image"
             and f.get("thumb_v") == 1 and msg.get("text") == "ref", f)
        landed = []
        F.fetch(b, f, landed.append)
        wait(lambda: bool(landed), 120)
        whole = QtGui.QImage(landed[0]) if landed else QtGui.QImage()
        gate("B downloads the picture whole", (whole.width(), whole.height()) == (1600, 900),
             landed and landed[0])
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
