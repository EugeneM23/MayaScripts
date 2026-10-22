"""Chat: the selection sent as one FBX (2026-10-22), in mayapy standalone against a live server.

    mayapy docs/superpowers/plans/verify_chat_send_selection.py [server]

A sends an animated cube it has selected (a sphere beside it not selected); B downloads the file and
imports it into a new scene: the cube with its animation, no sphere. Two throwaway accounts,
deleted at the end. Run it with a scratch MAYA_APP_DIR.
"""
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


def main():
    root = tempfile.mkdtemp(prefix="chatsel_")
    tag = uuid.uuid4().hex[:6]
    a = S.Session(SERVER, ST.Store(os.path.join(root, "a")))
    b = S.Session(SERVER, ST.Store(os.path.join(root, "b")))
    try:
        a.sign_in("vsa_" + tag)
        mb = b.sign_in("vsb_" + tag)
        wait(lambda: a.state.status == "online" and b.state.status == "online", 15)
        dm = a.open_dm(mb["id"])
        wait(lambda: dm in b.state.chats, 15)

        cmds.file(new=True, force=True)
        cube = cmds.polyCube(name="hero_box")[0]
        cmds.polySphere(name="not_sent")
        cmds.setKeyframe(cube, attribute="translateX", time=1, value=0)
        cmds.setKeyframe(cube, attribute="translateX", time=24, value=10)
        cmds.select(clear=True)
        try:
            F.send_selection(a, dm)
            refused = None
        except A.ChatError as exc:
            refused = exc.text
        gate("nothing selected is refused", refused and "выделите" in refused, refused)

        cmds.select(cube, replace=True)
        cid = F.send_selection(a, dm, "the box")
        gate("the selection is kept as it was", cmds.ls(selection=True) == [cube], cmds.ls(selection=True))
        took = wait(lambda: any(m.get("cid") == cid for m in b.state.messages.get(dm, [])), 120)
        msg = [m for m in b.state.messages.get(dm, []) if m.get("cid") == cid]
        f = (msg[0] if msg else {}).get("file") or {}
        gate("B gets one FBX named for the object", f.get("kind") == "fbx"
             and f.get("name", "").startswith("hero_box_") and f["name"].endswith(".fbx")
             and msg[0]["text"] == "the box", "%s in %.1f s" % (f.get("name"), took or -1))
        landed = []
        F.fetch(b, f, landed.append)
        wait(lambda: bool(landed), 120)
        gate("B downloads it", bool(landed), landed)
        cmds.file(new=True, force=True)
        cmds.loadPlugin("fbxmaya", quiet=True)
        import maya.mel as mel
        mel.eval('FBXImport -f "%s"' % landed[0].replace("\\", "/"))
        meshes = sorted(cmds.listRelatives(cmds.ls(type="mesh"), parent=True) or [])
        gate("the cube came, the sphere did not", meshes == ["hero_box"], meshes)
        keys = cmds.keyframe("hero_box", attribute="translateX", query=True, valueChange=True) or []
        gate("with its animation", keys and abs(max(keys) - 10.0) < 1e-3, keys[:3])
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
    code = 1 if main() else 0
    os._exit(code)
