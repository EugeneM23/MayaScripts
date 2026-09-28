"""Live proof for hub > Update > Check update (2026-09-28).

Runs in a DISPOSABLE GUI Maya started with its own MAYA_APP_DIR, so the
installer writes into a scratch prefs folder and a scratch shelf -- never
the animator's installed copy. A local HTTP server stands in for
github.com/<repo>/releases/latest/download/, serving a build made by
make_build.py (`SkeldarAnim.zip` + `version.json`).

Two sends, because the hub is rebuilt from an evalDeferred that fires only
after the first send returns:

    PHASE = "install"   a colleague's first install from the unzipped build,
                        the hub opened from the shelf button, the installed
                        record wound back one commit, Check update pressed
    PHASE = "after"     the hub rebuilt from the fresh modules, then the
                        refusals: up to date, nothing published, cancel,
                        no network; the real GitHub address read (no gate)

Globals the runner passes: PHASE, SERVE_DIR, SERVE_URL, WORK, SHOT.
Spec: docs/superpowers/specs/2026-09-28-update-button-design.md
"""

import builtins
import json
import os
import shutil
import sys
import zipfile

import maya.cmds as cmds

RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("{0} {1}{2}".format("PASS" if ok else "FAIL", name,
                              (" - " + str(detail)) if detail else ""))


def dest_dir():
    return os.path.join(cmds.internalVar(userAppDir=True), "scripts",
                        "SkeldarAnim")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def published():
    return read(os.path.join(SERVE_DIR, "version.json"))


def label(name):
    return cmds.text(name, query=True, label=True) \
        if cmds.text(name, exists=True) else None


def older_record(rec):
    """The published record wound back to its log's second commit."""
    sha, subject = rec["log"][1]
    return {"name": "SkeldarAnim", "commit": sha, "short": sha[:7],
            "subject": subject, "date": "", "log": rec["log"][1:]}


def phase_install():
    dest = dest_dir()
    app = cmds.internalVar(userAppDir=True).replace("\\", "/")
    gate("prefs are the scratch folder, not the animator's",
         "mayaapp" in app.lower() and "documents/maya" not in app.lower(),
         app)
    gate("nothing installed yet", not os.path.exists(dest), dest)

    #  A colleague: unzip, drag install.py.
    downloads = os.path.join(WORK, "downloads")
    shutil.rmtree(downloads, ignore_errors=True)
    with zipfile.ZipFile(os.path.join(SERVE_DIR, "SkeldarAnim.zip")) as zf:
        zf.extractall(downloads)
    dropped = os.path.join(downloads, "SkeldarAnim", "install.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("verify_dropped_install",
                                                  dropped)
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    installer.install(dropped, quiet=True)
    rec = read(os.path.join(dest, "version.json"))
    gate("the drag installs the build's own record",
         rec == published(), rec.get("short"))
    labels = [cmds.shelfButton(b, query=True, label=True) for b in
              cmds.shelfLayout("SkeldarAnim", query=True, childArray=True)]
    gate("the shelf is the hub and OverRig", labels == ["SkeldarAnim",
                                                        "OverRig"], labels)

    #  The shelf button, exactly as baked.
    hub_button = cmds.shelfLayout("SkeldarAnim", query=True,
                                  childArray=True)[0]
    exec(cmds.shelfButton(hub_button, query=True, command=True),
         {"__name__": "__main__"})
    import maya_update
    gate("the button imports the INSTALLED copy",
         os.path.normcase(os.path.dirname(maya_update.__file__))
         == os.path.normcase(dest), maya_update.__file__)
    gate("the hub has an Update section",
         cmds.frameLayout("skeldarHubFrameUpdate", exists=True))
    gate("the installed line names the build",
         published()["short"] in (label(maya_update.INSTALLED) or ""),
         label(maya_update.INSTALLED))

    #  Wind the installed copy back one commit; leave a stray behind.
    old = older_record(published())
    with open(os.path.join(dest, "version.json"), "w",
              encoding="utf-8") as handle:
        json.dump(old, handle)
    with open(os.path.join(dest, "stray_from_old_build.txt"), "w") as handle:
        handle.write("left by the old build")
    maya_update.refresh()
    gate("the line follows the record",
         old["short"] in (label(maya_update.INSTALLED) or ""),
         label(maya_update.INSTALLED))

    asked = []
    maya_update.BASE_URL = SERVE_URL
    message = maya_update.check_update(
        ask=lambda text: asked.append(text) or True)
    new = published()
    gate("one question was asked", len(asked) == 1)
    text = asked[0] if asked else ""
    print(text)
    gate("the question names both builds",
         "Installed:  " + old["short"] in text
         and "Available:  " + new["short"] in text)
    gate("the question lists what is new",
         "{0}  {1}".format(new["short"], new["log"][0][1][:40]) in text)
    gate("the press reports the update",
         message.startswith("Updated to " + new["short"]), message)
    rec = read(os.path.join(dest, "version.json"))
    gate("the installed record is the published one", rec == new,
         rec.get("short"))
    gate("the old build's files are gone",
         not os.path.exists(os.path.join(dest, "stray_from_old_build.txt")))
    gate("the payload is in place",
         os.path.isfile(os.path.join(dest, "maya_update.py"))
         and os.path.isfile(os.path.join(dest, "assets", "Manny_Rig.ma")))
    gate("our modules were purged",
         sys.modules.get("maya_update") is not maya_update)
    builtins._verify_update = {"old_update": id(maya_update),
                               "old_hub": id(sys.modules.get("maya_hub")),
                               "message": message}


def grab(path):
    import maya.OpenMayaUI as omui
    from PySide6 import QtWidgets
    import shiboken6
    ptr = omui.MQtUtil.findControl("skeldarAnimHub")
    widget = shiboken6.wrapInstance(int(ptr), QtWidgets.QWidget)
    return widget.grab().save(path)


def phase_after():
    stash = getattr(builtins, "_verify_update", {})
    import maya_hub
    import maya_update
    gate("the hub module is a fresh one",
         id(maya_hub) != stash.get("old_hub") and maya_hub._BUILT_HERE)
    gate("the update module is a fresh one",
         id(maya_update) != stash.get("old_update"))
    gate("the hub is open on Update",
         cmds.workspaceControl("skeldarAnimHub", exists=True)
         and not cmds.frameLayout("skeldarHubFrameUpdate", query=True,
                                  collapse=True))
    status = label(maya_update.STATUS) or ""
    gate("the fresh status line carries the message",
         status == stash.get("message"), status)
    new = published()
    gate("the fresh installed line names the new build",
         new["short"] in (label(maya_update.INSTALLED) or ""),
         label(maya_update.INSTALLED))
    if SHOT:
        print("photo:", grab(SHOT), SHOT)

    dest = dest_dir()
    record_path = os.path.join(dest, "version.json")
    maya_update.BASE_URL = SERVE_URL
    asked = []
    message = maya_update.check_update(
        ask=lambda text: asked.append(text) or True)
    gate("a second press is up to date",
         message.startswith("Up to date") and not asked, message)

    stamp = os.path.getmtime(record_path)
    maya_update.BASE_URL = SERVE_URL + "nothing-here/"
    message = maya_update.check_update(ask=lambda text: True)
    gate("nothing published refuses and touches nothing",
         "No build is published" in message
         and os.path.getmtime(record_path) == stamp, message)

    old = older_record(new)
    with open(record_path, "w", encoding="utf-8") as handle:
        json.dump(old, handle)
    maya_update.BASE_URL = SERVE_URL
    message = maya_update.check_update(ask=lambda text: False)
    gate("cancel changes nothing",
         "cancelled" in message and read(record_path) == old, message)
    shutil.copy2(os.path.join(SERVE_DIR, "version.json"), record_path)

    maya_update.BASE_URL = "http://127.0.0.1:9/"
    message = maya_update.check_update(ask=lambda text: True)
    gate("no network refuses",
         "could not reach" in message and "nothing changed" in message,
         message)

    import importlib
    maya_update = importlib.reload(maya_update)
    message = maya_update.check_update(ask=lambda text: False)
    print("INFO the real address answers: " + message)


def summary():
    failed = [name for name, ok in RESULTS if not ok]
    print("{0} of {1} gates failed".format(len(failed), len(RESULTS)))
    for name in failed:
        print("  FAILED: " + name)


if PHASE == "install":
    phase_install()
else:
    phase_after()
summary()
