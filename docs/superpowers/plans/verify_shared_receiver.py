"""Live proof of Shared (2026-09-30), the COLLEAGUE's half: mayapy standalone.

Run as its own process with a scratch MAYA_APP_DIR (its own prefs, so its own
machine id and its own SkeldarShare folder), on a TEST topic, beside the
sender (`verify_shared_sender.py`, in a disposable GUI Maya):

    SKELDAR_SHARE_TOPIC  the test channel (never the studio's)
    SKELDAR_SHARE_OUT    this process's JSON log, rewritten after each step
    SKELDAR_SHARE_MARKER the file the sender's script node would write if run
    SKELDAR_SHARE_STOP   the loop ends when this file exists
    SKELDAR_SHARE_PLUGIN the plugin folder (a `git archive` of the commit)

It listens, logs the moment each record arrives (so the press-to-row time is
measured against the sender's press on the same clock), opens the sender's
Orc D scene the moment it is local and measures it, then sends an FBX back.

`executeDeferred` is not relied on in batch: the section's `_defer` is a
queue this loop drains, which is exactly what Maya's idle does in the GUI.

Spec: docs/superpowers/specs/2026-09-30-shared-files-design.md
"""

import json
import os
import queue
import shutil
import sys
import time
import traceback

REPO = os.environ.get("SKELDAR_SHARE_PLUGIN",
                      r"C:/!!!Work/MayaScripts/SkeldarAnim")
TOPIC = os.environ["SKELDAR_SHARE_TOPIC"]
OUT = os.environ["SKELDAR_SHARE_OUT"]
MARKER = os.environ["SKELDAR_SHARE_MARKER"]
STOP = os.environ["SKELDAR_SHARE_STOP"]
FBX = os.path.join(REPO, "assets", "UE4_Mannequin.fbx")
LIMIT = 1200                    # seconds

sys.path.insert(0, REPO)

import maya.standalone  # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402

for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(plugin, quiet=True)
    except Exception:                                        # noqa: BLE001
        pass

import maya_sharenet as net  # noqa: E402
net.TOPIC = TOPIC
import maya_share as share  # noqa: E402
import maya_sharerecords as records  # noqa: E402
from maya_scenesetup import colour  # noqa: E402

work = queue.Queue()
share._defer = lambda fn, *args: work.put((fn, args))
LOG = {"events": [], "errors": [], "gates": {}, "statuses": [],
       "machine": share.machine_id(), "topic": TOPIC}


def write():
    part = OUT + ".part"
    with open(part, "w", encoding="utf-8") as out:
        json.dump(LOG, out, indent=1, default=str)
    os.replace(part, OUT)


_receive = share.receive


def receive(record, now=None):
    LOG["events"].append({"id": record["id"], "name": record["name"],
                          "state": record["state"],
                          "machine": record["machine"], "t": time.time()})
    write()
    return _receive(record, now)


share.receive = receive
_status = share._status
share._status = lambda message, **kw: (LOG["statuses"].append(
    [time.time(), message]) or _status(message))


def gate(name, ok, detail):
    LOG["gates"][name] = {"ok": bool(ok), "detail": detail}
    write()


def measure_scene(entry):
    """The opened Orc D scene, as the colleague sees it."""
    rec = entry["record"]
    gate("script_node_did_not_run", not os.path.exists(MARKER),
         "marker %s exists: %s" % (MARKER, os.path.exists(MARKER)))
    gate("script_node_came_along", cmds.objExists("verifyShareScript"),
         "the node is in the scene, never run")
    files = [f for f in cmds.ls(type="file") or []
             if cmds.attributeQuery(colour.ASSET_IMAGE, node=f, exists=True)]
    paths = [cmds.getAttr(f + ".fileTextureName") for f in files]
    assets = os.path.join(REPO, "assets").replace("\\", "/")
    on_ours = [p for p in paths if p.replace("\\", "/").startswith(assets)
               and os.path.isfile(p)]
    gate("textures_on_this_plugin", files and len(on_ours) == len(paths),
         "%d of %d file nodes on %s" % (len(on_ours), len(paths), assets))
    unit = cmds.currentUnit(query=True, time=True)
    rng = [cmds.playbackOptions(query=True, minTime=True),
           cmds.playbackOptions(query=True, maxTime=True),
           cmds.playbackOptions(query=True, animationStartTime=True),
           cmds.playbackOptions(query=True, animationEndTime=True)]
    gate("time_travelled", unit == "ntsc" and rng == [5.0, 45.0, 0.0, 50.0],
         "unit %s, ranges %s" % (unit, rng))
    mains = cmds.ls("*:Main") or []
    tx = cmds.getAttr(mains[0] + ".translateX") if mains else None
    gate("unsaved_edit_travelled", tx is not None and abs(tx - 12.5) < 1e-6,
         "Main.translateX %s" % tx)
    gate("record_says_scene", rec["kind"] == "scene" and rec.get("fps") == 30.0
         and rec.get("range") == [5.0, 45.0], "record %s %s %s" % (
             rec["kind"], rec.get("fps"), rec.get("range")))


def main():
    share.listen()
    LOG["phase"] = "listening"
    write()
    opened = sent_back = False
    fbx_copy = None
    end = time.time() + LIMIT
    while time.time() < end and not os.path.exists(STOP):
        try:
            fn, args = work.get(timeout=0.1)
            fn(*args)
        except queue.Empty:
            pass
        except Exception:                                    # noqa: BLE001
            LOG["errors"].append(traceback.format_exc())
            write()
        st = share.state()
        LOG["online"] = st["online"]
        LOG["since"] = st["since"]
        LOG["rows"] = [records.row_text(e["record"], records.is_mine(
            e["record"], share.machine_id()), e["record"]["state"],
            time.time()) for e in st["entries"].values()]
        LOG["visible"] = [r["name"] for r in records.visible(
            [e["record"] for e in st["entries"].values()], time.time())]
        if not opened:
            for rid, entry in list(st["entries"].items()):
                if (entry["record"]["name"].startswith("verify_orc")
                        and entry["local"]):
                    LOG["local_at"] = time.time()
                    LOG["local_path"] = entry["local"]
                    LOG["open"] = share.open_entry(rid)
                    measure_scene(entry)
                    opened = True
                    LOG["phase"] = "opened"
                    write()
        if opened and not sent_back:
            fbx_copy = os.path.join(os.path.dirname(OUT),
                                    "verify_mannequin.fbx")
            shutil.copy2(FBX, fbx_copy)
            LOG["fbx_press"] = time.time()
            LOG["fbx_send"] = share.send_file(fbx_copy,
                                              name="verify_mannequin")
            sent_back = True
            LOG["phase"] = "sent back"
            write()
        time.sleep(0.02)
    LOG["phase"] = "done"
    share.state()["subscriber"].stop()
    write()


try:
    main()
except Exception:                                            # noqa: BLE001
    LOG["errors"].append(traceback.format_exc())
    write()
maya.standalone.uninitialize()
