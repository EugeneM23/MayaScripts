"""Live proof of Shared (2026-09-30), the SENDER's half: a disposable GUI Maya.

Sent phase by phase over the disposable Maya's command port (never the
animator's Maya: it adds an Orc D and replaces the scene), with the globals
PHASE, TOPIC (a test channel), WORK (a scratch folder) and MARKER (the file a
script node in the sent scene would write if it ever ran). The colleague is
`verify_shared_receiver.py`, a mayapy process on the same test topic.

    setup   an Orc D, ntsc, ranges 5-45 / 0-50, a script node, the scene
            saved
    send    an unsaved edit (Main.translateX 12.5); the hub on Shared;
            Send scene pressed (the function the button calls)
    status  the section's state, the list's rows, the scene's name and
            modified flag
    focus   the hub jumped to Shared (a separate send before the photo)
    grab    the hub photographed (widget.grab)
    fbx     the colleague's FBX imported from the list
    fail    a send whose upload cannot connect: it must publish "failed"

Every phase merges its numbers into WORK/sender_report.json.

Spec: docs/superpowers/specs/2026-09-30-shared-files-design.md
"""

import json
import os
import sys
import time

REPO = globals().get("PLUGIN", r"C:/!!!Work/MayaScripts/SkeldarAnim")
REPORT = os.path.join(WORK, "sender_report.json")          # noqa: F821

if REPO not in sys.path:
    sys.path.insert(0, REPO)

import maya.cmds as cmds  # noqa: E402

import maya_sharenet as net  # noqa: E402
net.TOPIC = TOPIC                                           # noqa: F821
import maya_share as share  # noqa: E402
import maya_sharerecords as records  # noqa: E402


def report(update):
    data = {}
    if os.path.exists(REPORT):
        with open(REPORT, encoding="utf-8") as handle:
            data = json.load(handle)
    data.update(update)
    with open(REPORT, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=1, default=str)


def scene_state():
    return {"name": cmds.file(query=True, sceneName=True),
            "modified": cmds.file(query=True, modified=True),
            "main_tx": [cmds.getAttr(m + ".translateX")
                        for m in cmds.ls("*:Main") or []]}


def entries():
    st = share.state()
    return [{"name": e["record"]["name"], "state": e["record"]["state"],
             "mine": records.is_mine(e["record"], share.machine_id()),
             "local": e["local"], "id": e["record"]["id"],
             "transfer": st["transfers"].get(rid)}
            for rid, e in st["entries"].items()]


if PHASE == "setup":                                        # noqa: F821
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(minTime=5, maxTime=45, animationStartTime=0,
                         animationEndTime=50)
    from maya_scenesetup import catalog, character
    added = character.add_character(catalog.character_for("Orc_D", "rig"))
    cmds.scriptNode(name="verifyShareScript", scriptType=1,
                    sourceType="python",
                    beforeScript="open(%r, 'w').write('ran')" % MARKER)  # noqa
    path = os.path.join(WORK, "verify_orc_scene.ma").replace("\\", "/")  # noqa
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii", force=True)
    report({"added": added, "saved": path})

elif PHASE == "send":                                       # noqa: F821
    #  A send of its own: Maya clears the modified flag on the idle after a
    #  save, so an edit made in the same command as the save reads as clean
    #  afterwards (measured 2026-09-30) -- and this gate is about that flag.
    cmds.setAttr(cmds.ls("*:Main")[0] + ".translateX", 12.5)
    import maya_hub
    maya_hub.show("shared")
    before = scene_state()
    press = time.time()
    message = share.send_scene(comment="verify orc")
    report({"press": press, "send": message,
            "before": before, "after": scene_state(),
            "machine": share.machine_id()})

elif PHASE == "status":                                     # noqa: F821
    rows = cmds.textScrollList(share.LIST, query=True, allItems=True) or []
    report({"status": {"t": time.time(), "rows": rows, "entries": entries(),
                       "online": share.state()["online"],
                       "subtitle": cmds.text(share.SUBTITLE, query=True,
                                             label=True),
                       "line": cmds.text(share.STATUS, query=True,
                                         label=True),
                       "scene": scene_state()}})

elif PHASE == "focus":                                      # noqa: F821
    import maya_hub
    maya_hub.focus("shared")
    report({"focused": time.time()})

elif PHASE == "grab":                                       # noqa: F821
    import shiboken6
    from maya import OpenMayaUI as omui
    from PySide6 import QtWidgets
    widget = shiboken6.wrapInstance(int(omui.MQtUtil.findControl(
        "skeldarAnimHub")), QtWidgets.QWidget)
    shot = os.path.join(WORK, "hub_shared.png")             # noqa: F821
    widget.grab().save(shot)
    report({"grab": shot, "grab_size": [widget.width(), widget.height()]})

elif PHASE == "fbx":                                        # noqa: F821
    found = [e for e in entries() if e["name"] == "verify_mannequin.fbx"]
    result = {"found": found}
    if found and found[0]["local"]:
        before = set(cmds.ls(type="joint", long=True) or [])
        result["message"] = share.import_entry(found[0]["id"])
        arrived = sorted(set(cmds.ls(type="joint", long=True) or []) - before)
        result["joints"] = len(arrived)
        result["namespaces"] = sorted(set(
            j.split("|")[-1].rsplit(":", 1)[0] for j in arrived if ":" in j))
    report({"fbx": result})

elif PHASE == "fail":                                       # noqa: F821
    small = os.path.join(WORK, "verify_fail.ma")            # noqa: F821
    with open(small, "w") as out:
        out.write("//Maya ASCII 2027 scene\n")
    saved = net.UPLOAD_URL
    net.UPLOAD_URL = "http://127.0.0.1:1/api.php"
    net.TEMPSH_URL = "http://127.0.0.1:1/upload"
    try:
        message = share.send_file(small, comment="verify fail")
    finally:
        pass
    report({"fail_press": time.time(), "fail_send": message,
            "upload_url_saved": saved})

elif PHASE == "restore":                                    # noqa: F821
    net.UPLOAD_URL = \
        "https://litterbox.catbox.moe/resources/internals/api.php"
    net.TEMPSH_URL = "https://temp.sh/upload"
    report({"restored": [net.UPLOAD_URL, net.TEMPSH_URL]})
