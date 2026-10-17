"""Proof of Maya icons (2026-10-17), in mayapy standalone with a scratch
MAYA_APP_DIR (its prefs/icons is the folder written):

    set MAYA_APP_DIR=<scratch>
    mayapy verify_maya_icons.py

On through `set_enabled(True)`: every PNG of Maya's resources written, the
drawn set from our drawings at Maya's size, a file of "the animator's" kept;
Maya's own icon lookup (MQtUtil.createIcon) answering ours; Off taking ours
out and leaving theirs. Prints one line a gate and the count failed.
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
assert "MAYA_APP_DIR" in os.environ, "set a scratch MAYA_APP_DIR"

from PySide6 import QtGui, QtWidgets                          # noqa: E402
APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
import maya.standalone                                        # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                      # noqa: E402
import maya.OpenMayaUI as omui                                # noqa: E402
import shiboken6                                              # noqa: E402

import maya_mayaicons as icons                                # noqa: E402
import maya_mayaicons_art as art                              # noqa: E402

RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append(ok)
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def maya_icon(name):
    ptr = omui.MQtUtil.createIcon(name)
    icon = shiboken6.wrapInstance(int(ptr), QtGui.QIcon)
    return icon.pixmap(icon.availableSizes()[0]).toImage()


dest = icons.icons_dir()
gate("the folder is the scratch prefs/icons",
     os.path.normpath(os.environ["MAYA_APP_DIR"]) in dest, dest)
os.makedirs(dest, exist_ok=True)
with open(os.path.join(dest, "fileNew.png"), "wb") as handle:
    handle.write(b"the animator's own fileNew")
pngs = [n for n in cmds.resourceManager(nameFilter="*.png") or []]
before = maya_icon("move_M.png")

start = time.time()
message = icons.set_enabled(True)
took = time.time() - start
print(message)
written = [n for n in os.listdir(dest) if n.endswith(".png")]
gate("on: every PNG written but theirs", len(written) == len(pngs),
     "%d of %d PNGs in the folder, %.1f s" % (len(written), len(pngs), took))
gate("on: theirs kept", open(os.path.join(dest, "fileNew.png"), "rb").read()
     == b"the animator's own fileNew")
gate("on: said, with the restart", "restart" in message and "1 of your own"
     in message, message)
sizes_ok = all(QtGui.QImage(os.path.join(dest, n + ".png")).width() > 0
               for n in art.NAMES if n != "fileNew"
               and os.path.exists(os.path.join(dest, n + ".png")))
gate("on: every drawn icon written and readable", sizes_ok)
after = maya_icon("move_M.png")
same = icons.to_array(after).tobytes() == icons.to_array(
    icons.render("move_M", after.width(), after.height())).tobytes()
gate("Maya's createIcon answers our move_M", same and
     icons.to_array(before).tobytes() != icons.to_array(after).tobytes(),
     "%dx%d" % (after.width(), after.height()))
gate("on: remembered", icons.enabled())

message = icons.set_enabled(False)
print(message)
left = sorted(os.listdir(dest))
gate("off: only theirs left", left == ["fileNew.png"], ", ".join(left[:5]))
gate("off: remembered", not icons.enabled())

failed = RESULTS.count(False)
print("verify_maya_icons: %d of %d gates failed" % (failed, len(RESULTS)))
