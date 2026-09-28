"""Live proof for SkeldarAnim_Install.py (2026-09-28): a colleague's Maya with
NOTHING of ours, the file downloaded from the real release, dropped through
Maya's own drop handler.

Runs in a DISPOSABLE GUI Maya started with a FRESH scratch MAYA_APP_DIR, so the
install lands in scratch prefs and a scratch shelf. The dialogs a drop raises
(the installer's own confirm) would block the command port, so
`cmds.confirmDialog` is swapped for a recorder for the length of the drop and
put back after.

Globals the runner passes: WORK (a scratch folder), PHASE ("drop" or "after").
Spec: docs/superpowers/specs/2026-09-28-setup-script-design.md
"""

import builtins
import glob
import json
import os
import sys
import tempfile
import time
import urllib.request

import maya.cmds as cmds

URL = ("https://github.com/EugeneM23/MayaScripts/releases/latest/download/")
RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("{0} {1}{2}".format("PASS" if ok else "FAIL", name,
                              (" - " + str(detail)) if detail else ""))


def dest_dir():
    return os.path.join(cmds.internalVar(userAppDir=True), "scripts",
                        "SkeldarAnim")


def fetch(name):
    request = urllib.request.Request(URL + name,
                                     headers={"User-Agent": "verify"})
    return urllib.request.urlopen(request, timeout=60).read()


def phase_drop():
    app = cmds.internalVar(userAppDir=True).replace("\\", "/")
    gate("prefs are a fresh scratch folder", "mayaapp" in app.lower()
         and "documents/maya" not in app.lower(), app)
    gate("nothing of ours is installed", not os.path.exists(dest_dir()))
    gate("nothing of ours is importable",
         not [m for m in ("maya_hub", "install", "maya_update")
              if m in sys.modules])

    #  What a colleague does: download the one file, drag it in.
    os.makedirs(WORK, exist_ok=True)
    script = os.path.join(WORK, "SkeldarAnim_Install.py")
    with open(script, "wb") as handle:
        handle.write(fetch("SkeldarAnim_Install.py"))
    gate("the release serves SkeldarAnim_Install.py",
         os.path.getsize(script) > 1000, os.path.getsize(script))

    before = set(glob.glob(os.path.join(tempfile.gettempdir(),
                                        "skeldar_setup_*")))
    dialogs = []
    real = cmds.confirmDialog
    cmds.confirmDialog = lambda *a, **kw: dialogs.append(
        kw.get("message", "")) or "OK"
    start = time.time()
    try:
        from maya.app.general.executeDroppedPythonFile import \
            executeDroppedPythonFile
        executeDroppedPythonFile(script, "")
    finally:
        cmds.confirmDialog = real
    took = time.time() - start
    print("dialogs:", dialogs)
    gate("the drop ran and said so once, in the installer's words",
         len(dialogs) == 1 and dialogs[0].startswith("Installed: shelf "
                                                     "SkeldarAnim"),
         "%.1f s" % took)
    #  The first run's dialog told this very Maya «the previous version was
    #  loaded» - the installer purged the flags module it had just loaded.
    gate("a fresh Maya is not told about a previous version",
         dialogs and "previous version" not in dialogs[0])

    dest = dest_dir()
    with open(os.path.join(dest, "version.json"), encoding="utf-8") as h:
        rec = json.load(h)
    published = json.loads(fetch("version.json").decode("utf-8"))
    gate("the installed build is the published one",
         rec == published, "%s == %s" % (rec.get("short"),
                                         published.get("short")))
    gate("the payload is in place", all(os.path.isfile(os.path.join(dest, n))
                                        for n in ("install.py",
                                                  "maya_update.py",
                                                  "assets/Manny_Rig.ma",
                                                  "assets/Spear_03.png")))
    labels = [cmds.shelfButton(b, query=True, label=True) for b in
              cmds.shelfLayout("SkeldarAnim", query=True, childArray=True)]
    gate("the shelf is SkeldarAnim + OverRig",
         labels == ["SkeldarAnim", "OverRig"], labels)
    after = set(glob.glob(os.path.join(tempfile.gettempdir(),
                                       "skeldar_setup_*")))
    gate("the download was cleaned up", after == before, after - before)
    builtins._verify_setup = {"script": script}


def phase_after():
    import maya_hub
    import maya_update
    dest = dest_dir()
    gate("the window is open, from the installed copy",
         cmds.workspaceControl("skeldarAnimHub", exists=True)
         and os.path.normcase(os.path.dirname(maya_hub.__file__))
         == os.path.normcase(dest), maya_hub.__file__)
    message = maya_update.check_update(ask=lambda text: False)
    gate("Check update right after reads up to date",
         message.startswith("Up to date"), message)


if PHASE == "drop":
    phase_drop()
else:
    phase_after()
failed = RESULTS.count(False)
print("{0} of {1} gates failed".format(failed, len(RESULTS)))
