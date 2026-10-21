"""Stash / Shared drops, standalone (2026-10-21). Run with a scratch app dir:
    $env:MAYA_APP_DIR = "<scratch>"; mayapy verify_stash_share_drag.py
The drop entry points the drag calls, on a real scene: a stashed scene and FBX
imported, a shared file (downloaded by a fake net) copied into the stash."""
import os
import sys
import tempfile
import time
import zipfile

if not os.environ.get("MAYA_APP_DIR"):
    print("refused: set MAYA_APP_DIR to a scratch folder first - this verify "
          "writes into the stash folder of the app dir")
    sys.exit(2)

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim")))
import maya_stash
import maya_share
import maya_sharerecords as records

FAILS = []
TOTAL = 4


def gate(n, ok, text):
    print("gate %d %s %s" % (n, "ok" if ok else "FAILED", text))
    if not ok:
        FAILS.append(n)


work = tempfile.mkdtemp(prefix="dragverify_")
cmds.polyCube(name="draftCube")
draft = os.path.join(work, "draft.ma")
cmds.file(rename=draft)
cmds.file(save=True, type="mayaAscii")
cmds.file(new=True, force=True)
cmds.loadPlugin("fbxmaya", quiet=True)
cmds.joint(name="clipRoot")
cmds.setKeyframe("clipRoot.tx", t=0, v=0)
cmds.setKeyframe("clipRoot.tx", t=10, v=5)
clip = os.path.join(work, "clip.fbx")
cmds.select("clipRoot")
mel.eval('FBXExport -f "%s" -s' % clip.replace("\\", "/"))
cmds.file(new=True, force=True)
print("app dir:", os.environ.get("MAYA_APP_DIR"), "| stash:", maya_stash.folder())

maya_stash.stash_file(draft, "draft.ma")
maya_stash.stash_file(clip, "clip.fbx")
message = maya_stash.drop_import(["draft.ma", "clip.fbx"])
gate(1, cmds.objExists("draftCube"), "the scene came in: %s" % message)
gate(2, any(j.endswith("clipRoot") for j in (cmds.ls(type="joint") or [])),
     "the FBX came in as a skeleton")
gate(3, " | " in (message or "") and "draft.ma" in message and "clip.fbx" in message,
     "one line naming both")


class Net(object):
    def download(self, url, path, progress=None):
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("Long.fbx", open(clip, "rb").read())


maya_share.net = Net()
maya_share._spawn = lambda fn: fn()
maya_share._defer = lambda fn, *a: fn(*a)
rid = records.new_id()
rec = records.with_state(
    records.make_record("sending", rid, "Oleg", "theirs-machine", "Long.fbx",
                        10, int(time.time())),
    "ready", url="https://litterbox.catbox.moe/abc.zip", zip=10)
maya_share.receive(rec)
answer = maya_share.drop_to_stash([rid])
gate(4, os.path.isfile(os.path.join(maya_stash.folder(), "Long.fbx")),
     "copied into the stash: %s" % answer)
print("verify: %d of %d gates failed" % (len(FAILS), TOTAL))
