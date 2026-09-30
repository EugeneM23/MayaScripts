"""Live proof of Shared's Delete and upload names (2026-09-30): two colleagues.

Two mayapy processes, each with its own MAYA_APP_DIR (its own prefs, machine
id and SkeldarShare folder), on a TEST topic, over the real ntfy.sh and file
hosts. Environment:

    SKELDAR_SHARE_ROLE    A (sends three files, deletes two) or B (the
                          colleague: opens one, deletes the third)
    SKELDAR_SHARE_TOPIC   the test channel (never the studio's)
    SKELDAR_SHARE_WORK    a folder both write their JSON logs into
                          (delete_A.json, delete_B.json)
    SKELDAR_SHARE_PLUGIN  the plugin folder

The run:

    A  sends one small scene three times, under the typed names
       «verify delete one / two / three»
    B  sees the rows under those names, downloads all three, OPENS one
    A  deletes one and three together
    B  loses both rows; three's copy and folder go; one's copy STAYS, since
       it is the scene open in B's Maya; the status names who deleted them
    B  deletes two (A's file)
    A  loses the row and its own sent copy of two

Every step's time is on one machine's clock, so press-to-arrival is measured
across the two logs. `executeDeferred` is not relied on in batch: the
section's `_defer` is a queue each loop drains, as Maya's idle does.

Spec: docs/superpowers/specs/2026-09-30-shared-delete-and-naming-design.md
"""

import json
import os
import queue
import sys
import time
import traceback

ROLE = os.environ["SKELDAR_SHARE_ROLE"]
TOPIC = os.environ["SKELDAR_SHARE_TOPIC"]
WORK = os.environ["SKELDAR_SHARE_WORK"]
REPO = os.environ.get("SKELDAR_SHARE_PLUGIN",
                      r"C:/!!!Work/MayaScripts/SkeldarAnim")
LIMIT = 300                                     # seconds, each wait
NAMES = ("verify delete one", "verify delete two", "verify delete three")
OUT = os.path.join(WORK, "delete_%s.json" % ROLE)
OTHER = os.path.join(WORK, "delete_%s.json" % ("B" if ROLE == "A" else "A"))

sys.path.insert(0, REPO)

import maya.standalone  # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402

import maya_sharenet as net  # noqa: E402
net.TOPIC = TOPIC
import maya_share as share  # noqa: E402
import maya_sharerecords as records  # noqa: E402

work = queue.Queue()
share._defer = lambda fn, *args: work.put((fn, args))
LOG = {"role": ROLE, "topic": TOPIC, "gates": {}, "statuses": [],
       "errors": [], "t": {}, "arrived": {}}

_status = share._status
share._status = lambda message, **kw: (LOG["statuses"].append(
    [time.time(), message]) or _status(message))
_receive = share.receive


def receive(record, now=None):
    LOG["arrived"].setdefault(record["name"] + " " + record["state"],
                              time.time())
    return _receive(record, now)


share.receive = receive


def write():
    part = OUT + ".part"
    with open(part, "w", encoding="utf-8") as out:
        json.dump(LOG, out, indent=1, default=str)
    os.replace(part, OUT)


def other():
    try:
        with open(OTHER, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def gate(name, ok, detail):
    LOG["gates"][name] = {"ok": bool(ok), "detail": detail}
    write()


def mark(name):
    LOG["t"][name] = time.time()
    write()


def pump(seconds=0.1):
    end = time.time() + seconds
    while time.time() < end:
        try:
            fn, args = work.get(timeout=0.02)
            fn(*args)
        except queue.Empty:
            pass
        except Exception:                                    # noqa: BLE001
            LOG["errors"].append(traceback.format_exc())
            write()


def wait(cond, what):
    end = time.time() + LIMIT
    while time.time() < end:
        pump()
        try:
            if cond():
                return True
        except Exception:                                    # noqa: BLE001
            LOG["errors"].append(traceback.format_exc())
        time.sleep(0.02)
    LOG["errors"].append("timed out waiting for " + what)
    write()
    return False


def entry(name):
    for rid, item in share.state()["entries"].items():
        if item["record"]["name"] == name + ".ma":
            return rid, item
    return None, None


def state_of(name):
    _rid, item = entry(name)
    return item["record"]["state"] if item else None


def local_of(name):
    _rid, item = entry(name)
    return item["local"] if item else ""


def visible_names():
    return [r["name"] for r in records.visible(
        [e["record"] for e in share.state()["entries"].values()],
        time.time())]


def said(text):
    return [m for _t, m in LOG["statuses"] if text in m]


def run_a():
    share.set_sender_name("VerifyA")
    share.listen()
    wait(lambda: share.state()["online"] == "online", "online")
    mark("online")
    source = os.path.join(WORK, "verify_delete_source.ma")
    with open(source, "w") as out:
        out.write('//Maya ASCII 2027 scene\nrequires maya "2027";\n'
                  'currentUnit -l centimeter -a degree -t ntsc;\n'
                  'createNode transform -n "verifyDeleteCube";\n')
    for name in NAMES:
        LOG["t"]["press " + name] = time.time()
        share.send_file(source, name=name)
    write()
    wait(lambda: all(state_of(n) == "ready" for n in NAMES), "three sent")
    mark("sent")
    gate("a_sent_under_the_typed_names",
         all(state_of(n) == "ready" for n in NAMES)
         and all(os.path.basename(local_of(n)) == n + ".ma" for n in NAMES),
         {n: [state_of(n), local_of(n)] for n in NAMES})
    copies = {n: local_of(n) for n in NAMES}
    wait(lambda: "b_ready" in other().get("t", {}), "B ready")
    one, three = entry(NAMES[0])[0], entry(NAMES[2])[0]
    mark("delete press")
    share.delete_entries([one, three])
    #  the channel's echo of our own delete can arrive before the publish
    #  answers (measured): the row goes first, the press's status after
    wait(lambda: state_of(NAMES[0]) == "deleted"
         and state_of(NAMES[2]) == "deleted"
         and said("Deleted 2 files for everybody"), "own delete applied")
    mark("deleted here")
    gate("a_own_delete",
         not os.path.exists(copies[NAMES[0]])
         and not os.path.exists(copies[NAMES[2]])
         and bool(said("Deleted 2 files for everybody")),
         {"one": os.path.exists(copies[NAMES[0]]),
          "three": os.path.exists(copies[NAMES[2]]),
          "status": LOG["statuses"][-3:]})
    wait(lambda: state_of(NAMES[1]) == "deleted", "B's delete")
    mark("saw b delete")
    _rid, two = entry(NAMES[1])
    gate("a_saw_the_colleagues_delete",
         two["record"].get("by") == "VerifyB"
         and not os.path.exists(copies[NAMES[1]])
         and not os.path.exists(os.path.dirname(copies[NAMES[1]]))
         and bool(said("VerifyB deleted verify delete two.ma")),
         {"by": two["record"].get("by"),
          "copy": os.path.exists(copies[NAMES[1]]),
          "status": LOG["statuses"][-2:]})
    gate("a_list_empty", not [n for n in visible_names()
                              if n.startswith("verify delete")],
         visible_names())


def run_b():
    share.set_sender_name("VerifyB")
    share.listen()
    wait(lambda: share.state()["online"] == "online", "online")
    mark("online")
    wait(lambda: all(local_of(n) and os.path.isfile(local_of(n))
                     for n in NAMES), "three downloaded")
    mark("downloaded")
    gate("b_rows_under_the_typed_names",
         all(n + ".ma" in visible_names() for n in NAMES)
         and all(entry(n)[1]["record"]["from"] == "VerifyA" for n in NAMES),
         visible_names())
    copies = {n: local_of(n) for n in NAMES}
    one = entry(NAMES[0])[0]
    LOG["open"] = share.open_entry(one)
    scene = cmds.file(query=True, sceneName=True)
    gate("b_opened_one", cmds.objExists("verifyDeleteCube")
         and os.path.normcase(os.path.abspath(scene))
         == os.path.normcase(os.path.abspath(copies[NAMES[0]])),
         [LOG["open"], scene])
    mark("b_ready")
    wait(lambda: state_of(NAMES[0]) == "deleted"
         and state_of(NAMES[2]) == "deleted", "A's delete")
    mark("saw a delete")
    gate("b_the_open_scene_stayed",
         os.path.isfile(copies[NAMES[0]])
         and NAMES[0] + ".ma" not in visible_names()
         and bool(said("VerifyA deleted verify delete one.ma - your copy "
                       "stays on this disk: it is the open scene")),
         {"copy": os.path.isfile(copies[NAMES[0]]),
          "rows": visible_names(), "status": LOG["statuses"][-3:]})
    gate("b_the_other_copy_and_its_folder_went",
         not os.path.exists(copies[NAMES[2]])
         and not os.path.exists(os.path.dirname(copies[NAMES[2]]))
         and NAMES[2] + ".ma" not in visible_names()
         and bool(said("VerifyA deleted verify delete three.ma")),
         {"copy": os.path.exists(copies[NAMES[2]]),
          "folder": os.path.exists(os.path.dirname(copies[NAMES[2]]))})
    two = entry(NAMES[1])[0]
    mark("delete press")
    share.delete_entries([two])
    wait(lambda: state_of(NAMES[1]) == "deleted"
         and said("Deleted 1 file for everybody"), "own delete applied")
    mark("deleted here")
    gate("b_own_delete_of_a_colleagues_file",
         not os.path.exists(copies[NAMES[1]])
         and bool(said("Deleted 1 file for everybody")),
         {"copy": os.path.exists(copies[NAMES[1]]),
          "status": LOG["statuses"][-2:]})


try:
    (run_a if ROLE == "A" else run_b)()
    mark("done")
    #  a last few seconds on the channel, so the colleague's echo arrives
    #  here too before the stream closes
    wait(lambda: "done" in other().get("t", {}), "the colleague done")
    pump(2.0)
except Exception:                                            # noqa: BLE001
    LOG["errors"].append(traceback.format_exc())
finally:
    subscriber = share.state().get("subscriber")
    if subscriber is not None:
        subscriber.stop()
    LOG["finished"] = time.time()
    write()
maya.standalone.uninitialize()
