"""maya_share - Shared: scenes and FBX between colleagues, one press.

The animator's ask (2026-09-30): «Мне очень часто приходится передавать
какие-то сцены локально между сотрудниками. Можем ли мы сделать какое-то
Shared Temp хранилище ... не только сцен а еще и fbx файлов», and the shape
they chose: «Ключи никакие не нужны. Мне нужен максимально быстрый и удобный
способ передавать файлы. Один человек нажал кнопочку у второго через 2
секунды появился файлик в списке». Everyone works remotely.

    import maya_share; maya_share.show_window()     # the hub, on Shared

**Send scene** writes a COPY of the open scene (`exportAll`: the working
file, its name and its modified flag are untouched; measured 2026-09-30 that
the frame rate, both ranges, the current frame and unsaved edits travel),
puts a "sending" record on the channel -- so the colleagues' rows appear at
once -- zips and uploads on a thread (`maya_sharenet`), then says "ready"
with the address. **Send file...** does the same for any .ma/.mb/.fbx.

Every Maya with the hub open listens on a `Subscriber` thread. A colleague's
"ready" is downloaded into `<userAppDir>/SkeldarShare/` straight away, so
Open is local by the time anybody presses it; nothing ever opens by itself.
A scene is opened and imported WITHOUT running its script nodes, the vaccine
is swept out, and the plugin's images are pointed at the installed copy.

Threads never call `cmds`: they hand work to `_defer` (Maya's
executeDeferred). The state lives on `sys._skeldar_share`, so a purge of our
modules (an update, a verify run) does not leave a second subscriber
running beside the first: `listen()` stops whichever is there.

Spec: docs/superpowers/specs/2026-09-30-shared-files-design.md
"""

import getpass
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
import uuid
import zipfile

import maya.cmds as cmds
import maya.mel as mel
import maya.utils

import maya_sharenet as net
import maya_sharerecords as records

HUB_SECTION = "shared"
NAME_FIELD = "skeldarShareName"
COMMENT_FIELD = "skeldarShareComment"
LIST = "skeldarShareList"
STATUS = "skeldarShareStatus"
SUBTITLE = "skeldarShareSubtitle"

NAME_VAR = "skeldarShareName"
MACHINE_VAR = "skeldarShareMachine"
FOLDER = "SkeldarShare"
HISTORY = "history.json"

LIST_HEIGHT = 150
REFRESH_EVERY = 0.3             # seconds between progress repaints
FIRST_SINCE = "12h"             # all ntfy.sh keeps: a first start replays it


# ------------------------------------------------------------------ seams

def _defer(fn, *args):
    """Run `fn(*args)` on Maya's main thread when it is idle."""
    maya.utils.executeDeferred(fn, *args)


def _spawn(fn):
    """Run `fn` on a thread of its own (a transfer)."""
    threading.Thread(target=fn, name="SkeldarShareTransfer",
                     daemon=True).start()


def _reason(exc):
    return str(exc) or type(exc).__name__


# ------------------------------------------------------------------ state

def state():
    """The section's state, on `sys` (one per Maya session, whatever module
    object is asking): entries by id ({"record", "local"}), the channel's
    last id, the transfers in progress ({"progress", "error"}), the
    subscriber, the list's rows."""
    st = getattr(sys, "_skeldar_share", None)
    if st is None:
        st = {"entries": {}, "since": "", "transfers": {}, "subscriber": None,
              "online": "connecting...", "loaded": False, "rows": [],
              "texts": [], "last_refresh": 0.0}
        sys._skeldar_share = st
    return st


def _option(name):
    if cmds.optionVar(exists=name):
        return cmds.optionVar(query=name) or ""
    return ""


def sender_name():
    """What colleagues see as "from": the field's remembered value, else the
    Windows user name."""
    return _option(NAME_VAR) or records.sender_default(getpass.getuser())


def set_sender_name(value):
    cmds.optionVar(stringValue=(NAME_VAR, (value or "").strip()))


def machine_id():
    """This Maya's prefs' id: what makes a record "you"."""
    value = _option(MACHINE_VAR)
    if not value:
        value = uuid.uuid4().hex
        cmds.optionVar(stringValue=(MACHINE_VAR, value))
    return value


def share_dir():
    return os.path.join(cmds.internalVar(userAppDir=True), FOLDER)


def history_path():
    return os.path.join(share_dir(), HISTORY)


def inbox_path(record):
    """Where `record`'s file lives on this machine, sent or received."""
    return os.path.join(share_dir(), records.inbox_folder(record),
                        record["name"])


def load_history():
    """The history file into the state, once per session. A local file that
    was deleted meanwhile is forgotten (the row downloads it again)."""
    st = state()
    if st["loaded"]:
        return
    st["loaded"] = True
    try:
        with open(history_path(), encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return
    entries, since = records.from_history(text, time.time())
    for rid, entry in entries.items():
        if entry["local"] and not os.path.isfile(entry["local"]):
            entry["local"] = ""
        st["entries"].setdefault(rid, entry)
    st["since"] = st["since"] or since


def save_history():
    """The state into the history file (main thread only)."""
    st = state()
    path = history_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        part = path + ".part"
        with open(part, "w", encoding="utf-8") as out:
            out.write(records.to_history(st["entries"], st["since"]))
        os.replace(part, path)
    except OSError:
        print(traceback.format_exc())


# ----------------------------------------------------------------- sending

def _comment(comment):
    if comment is not None:
        return comment
    if cmds.textField(COMMENT_FIELD, exists=True):
        return cmds.textField(COMMENT_FIELD, query=True, text=True) or ""
    return ""


def _new_record(name, comment):
    return records.make_record(
        "sending", records.new_id(), sender_name(), machine_id(), name, 0,
        time.time(), comment=" ".join(_comment(comment).split()),
        maya=str(cmds.about(version=True) or ""))


def _foreign_textures():
    """Texture files the copy refers to that are not the plugin's own (those
    travel by their marker and are relinked on arrival)."""
    from maya_scenesetup import colour
    out = []
    for node in cmds.ls(type="file") or []:
        if cmds.attributeQuery(colour.ASSET_IMAGE, node=node, exists=True):
            continue
        path = cmds.getAttr(node + ".fileTextureName") or ""
        if path and path not in out:
            out.append(path)
    return out


def send_scene(comment=None):
    """The press: a copy of the open scene to everybody."""
    from maya_uebridge import animimport
    name, file_type = records.scene_file_name(
        cmds.file(query=True, sceneName=True), time.time())
    record = _new_record(name, comment)
    path = inbox_path(record)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    #  A copy, not a save: the working file, its name and its modified flag
    #  stay as they are. References are written into the copy (a colleague
    #  has none of the files they point at).
    cmds.file(path, exportAll=True, type=file_type, force=True,
              preserveReferences=False)
    record["bytes"] = os.path.getsize(path)
    fps = animimport.fps_from_unit(cmds.currentUnit(query=True, time=True))
    if fps:
        record["fps"] = fps
    record["range"] = [cmds.playbackOptions(query=True, minTime=True),
                       cmds.playbackOptions(query=True, maxTime=True)]
    return _send(record, path, records.left_behind_note(_foreign_textures()))


def _pick_file():
    picked = cmds.fileDialog2(
        fileMode=1, caption="Send a file to everybody",
        fileFilter="Maya scenes and FBX (*.ma *.mb *.fbx)")
    return picked[0] if picked else ""


def send_file(path=None, comment=None):
    """The press: `path` (else a file dialog's pick) to everybody."""
    path = path or _pick_file()
    if not path:
        return _status("Nothing sent.")
    name = os.path.basename(path)
    if records.kind_of(name) is None:
        return _status("Only .ma, .mb and .fbx files can be sent - "
                       "nothing sent.")
    if not os.path.isfile(path):
        return _status("No file at {0} - nothing sent.".format(path))
    record = _new_record(name, comment)
    local = inbox_path(record)
    os.makedirs(os.path.dirname(local), exist_ok=True)
    #  A copy of what was sent: a later edit of the original does not change
    #  it, and "you" rows open like any other.
    shutil.copy2(path, local)
    record["bytes"] = os.path.getsize(local)
    return _send(record, local, "")


def _send(record, path, note):
    st = state()
    rid = record["id"]
    st["entries"][rid] = {"record": record, "local": path}
    st["transfers"][rid] = {"progress": 0.0, "error": ""}
    save_history()
    if cmds.textField(COMMENT_FIELD, exists=True):
        cmds.textField(COMMENT_FIELD, edit=True, text="")
    refresh()
    message = _status("Sending {0} ({1}){2}".format(
        record["name"], records.size_text(record["bytes"]),
        (" - " + note) if note else ""))
    _spawn(lambda: _send_work(dict(record), path))
    return message


def _zip(path, name):
    handle, archive = tempfile.mkstemp(prefix="skeldar_share_", suffix=".zip")
    os.close(handle)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=6) as out:
        out.write(path, name)
    return archive


def _remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _send_work(record, path):
    """On a thread: announce, zip, upload, say ready -- or say failed."""
    rid = record["id"]
    archive = None
    try:
        net.publish(records.encode(record))
        archive = _zip(path, record["name"])
        size = os.path.getsize(archive)
        if size > records.MAX_ZIP:
            raise net.ShareError("the zip is {0}, over the hosts' 1 GB"
                                 .format(records.size_text(size)))
        url = net.upload_any(archive, progress=lambda done, total: _progress(
            rid, done, total))
        ready = records.with_state(record, "ready", url=url, zip=size)
        net.publish(records.encode(ready))
        _defer(_sent, ready)
    except Exception as exc:                                 # noqa: BLE001
        try:
            net.publish(records.encode(records.with_state(record, "failed")))
        except Exception:                                    # noqa: BLE001
            pass
        _defer(_send_failed, rid, _reason(exc))
    finally:
        _remove(archive)


def _progress(rid, done, total):
    """A transfer's progress, from its thread; the list is repainted at most
    every REFRESH_EVERY."""
    st = state()
    transfer = st["transfers"].get(rid)
    if transfer is not None:
        transfer["progress"] = (float(done) / total) if total else None
    now = time.time()
    if now - st["last_refresh"] >= REFRESH_EVERY:
        st["last_refresh"] = now
        _defer(refresh)


def _sent(ready):
    st = state()
    entry = st["entries"].get(ready["id"])
    if entry is not None:
        entry["record"] = records.merge(entry["record"], ready)
    st["transfers"].pop(ready["id"], None)
    save_history()
    refresh()
    _status("Sent {0} to everybody - {1} zipped, {2:.0f} s.".format(
        ready["name"], records.size_text(ready["zip"]),
        time.time() - ready["sent"]))


def _send_failed(rid, reason):
    st = state()
    entry = st["entries"].get(rid)
    if entry is not None:
        entry["record"] = records.with_state(entry["record"], "failed")
    st["transfers"].pop(rid, None)
    save_history()
    refresh()
    name = entry["record"]["name"] if entry else "the file"
    _status("Sending {0} failed: {1} - nothing was sent.".format(name, reason))


# --------------------------------------------------------------- receiving

def listen():
    """(Re)start listening for THIS module: whatever subscriber is standing
    -- this module's, or one a purged module object started -- is stopped,
    and a new one resumes from the last message id seen."""
    st = state()
    load_history()
    old = st.get("subscriber")
    if old is not None:
        old.stop()
    subscriber = net.Subscriber(_on_event, since=st["since"] or FIRST_SINCE,
                                on_state=_on_state)
    st["subscriber"] = subscriber
    subscriber.start()
    return subscriber


def _on_event(event):
    """From the subscriber's thread: remember the id, hand a record over."""
    if event.get("event") == "message" and event.get("id"):
        state()["since"] = event["id"]
    record = records.from_event(event)
    if record is not None:
        _defer(receive, record)


def _on_state(text):
    state()["online"] = text
    _defer(refresh_subtitle)


def receive(record, now=None):
    """A record off the channel (main thread). Returns whether anything
    changed. A colleague's ready file is fetched at once; announced only
    when it is news, not when a first start replays the channel."""
    st = state()
    now = time.time() if now is None else now
    rid = record["id"]
    known = st["entries"].get(rid)
    merged = records.merge(known["record"] if known else None, record)
    if known is not None and merged is known["record"]:
        return False
    st["entries"][rid] = {"record": merged,
                          "local": known["local"] if known else ""}
    save_history()
    if (merged["state"] == "ready" and not records.is_mine(merged, machine_id())
            and not records.expired(merged, now)):
        if records.is_news(merged, now):
            _announce(merged)
        fetch(rid)
    refresh()
    return True


def _announce(record):
    try:
        cmds.inViewMessage(assistMessage=records.announce_text(record),
                           position="topCenter", fade=True,
                           fadeStayTime=4000)
    except Exception:                                        # noqa: BLE001
        pass


def fetch(rid):
    """Download `rid`'s file in the background, unless it is here already or
    on its way. A failed download may be fetched again."""
    st = state()
    entry = st["entries"].get(rid)
    if entry is None or entry["local"]:
        return False
    transfer = st["transfers"].get(rid)
    if transfer is not None and not transfer.get("error"):
        return False
    record = entry["record"]
    if record["state"] != "ready":
        return False
    st["transfers"][rid] = {"progress": 0.0, "error": ""}
    path = inbox_path(record)
    _spawn(lambda: _fetch_work(record, path))
    return True


def _unzip(archive, name, path):
    with zipfile.ZipFile(archive) as source:
        problems = records.archive_problems(source.namelist(), name)
        if problems:
            raise net.ShareError("; ".join(problems))
        part = path + ".part"
        with source.open(name) as src, open(part, "wb") as out:
            shutil.copyfileobj(src, out)
    os.replace(part, path)


def _fetch_work(record, path):
    """On a thread: download, unzip, hand the local file over."""
    rid = record["id"]
    archive = path + ".download.zip"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        net.download(record["url"], archive,
                     progress=lambda done, total: _progress(rid, done, total))
        _unzip(archive, record["name"], path)
        _defer(_fetched, rid, path)
    except Exception as exc:                                 # noqa: BLE001
        _defer(_fetch_failed, rid, _reason(exc))
    finally:
        _remove(archive)


def _fetched(rid, path):
    st = state()
    entry = st["entries"].get(rid)
    if entry is not None:
        entry["local"] = path
    st["transfers"].pop(rid, None)
    save_history()
    refresh()
    if entry is not None and selected_id() == rid:
        _selected()


def _fetch_failed(rid, reason):
    st = state()
    st["transfers"][rid] = {"progress": None, "error": reason}
    refresh()
    entry = st["entries"].get(rid)
    if entry is not None:
        _status("Downloading {0} failed: {1} - Open tries again.".format(
            entry["record"]["name"], reason))


# ----------------------------------------------------------------- actions

def selected_id():
    if not cmds.textScrollList(LIST, exists=True):
        return None
    picked = cmds.textScrollList(LIST, query=True,
                                 selectIndexedItem=True) or []
    rows = state()["rows"]
    if picked and 0 < picked[0] <= len(rows):
        return rows[picked[0] - 1]
    return None


def _local_or_fetch(rid):
    """(local path, "") when the file is here, else (None, what to say) --
    and a ready file not here yet is fetched (again, after a failure)."""
    entry = state()["entries"].get(rid)
    if entry is None:
        return None, "That file is no longer in the list."
    if entry["local"] and os.path.isfile(entry["local"]):
        return entry["local"], ""
    record = entry["record"]
    if record["state"] == "sending":
        return None, "{0} is still being sent - wait for it to say ready." \
            .format(record["name"])
    if record["state"] != "ready":
        return None, "{0} was never sent - nothing to open.".format(
            record["name"])
    if records.expired(record, time.time()):
        return None, "{0} has expired (files live 72 hours) - ask for it " \
                     "again.".format(record["name"])
    fetch(rid)
    return None, "{0} is downloading - Open it when it says ready.".format(
        record["name"])


def _save_changes():
    """Maya's own «save changes?» for a modified scene; True to go on."""
    if cmds.about(batch=True):
        return True
    try:
        return bool(mel.eval('saveChanges("")'))
    except RuntimeError:
        if not cmds.file(query=True, modified=True):
            return True
        answer = cmds.confirmDialog(
            title="Shared", message="The scene has unsaved changes. Open "
                                    "the shared file anyway?",
            button=["Open", "Cancel"], defaultButton="Cancel",
            cancelButton="Cancel", dismissString="Cancel")
        return answer == "Open"


def _clean(nodes, every_script):
    """After an open or an import: script nodes out (the vaccine always;
    every one that arrived, for an import -- none of them ran), the plugin's
    images pointed at the installed copy. Returns a note."""
    from maya_scenesetup import catalog, character, colour
    scripts = cmds.ls(nodes, type="script") or []
    doomed = scripts if every_script else character.malware_nodes(scripts)
    removed = []
    for node in doomed:
        if cmds.objExists(node):
            try:
                cmds.lockNode(node, lock=False)
                cmds.delete(node)
                removed.append(node)
            except Exception:                                # noqa: BLE001
                pass
    relinked, missing = colour.relink_images(cmds.ls(nodes, type="file")
                                             or [], catalog.asset_path)
    notes = []
    if relinked:
        notes.append("{0} texture(s) on your plugin".format(relinked))
    if missing:
        notes.append("missing in your plugin: " + ", ".join(
            os.path.basename(m) for m in missing[:3]))
    malware = character.malware_nodes(removed)
    if malware:
        notes.append("removed malware script node(s): " + ", ".join(malware))
    return (" - " + "; ".join(notes)) if notes else ""


SCENE_CONFIG = "sceneConfigurationScriptNode"


def _restore_playback():
    """The opened scene's ranges, read out of its sceneConfigurationScriptNode
    and applied -- that node is what sets them, and it did not run (the open
    runs no script node). Parsed, never evaluated. True when applied."""
    if not cmds.objExists(SCENE_CONFIG):
        return False
    values = records.playback_from_script(
        cmds.scriptNode(SCENE_CONFIG, query=True, beforeScript=True) or "")
    if not values:
        return False
    cmds.playbackOptions(**values)
    return True


def _import_fbx(path, record, verb):
    from maya_uebridge import animimport
    from maya_uebridge import records as bridge_records
    namespace = bridge_records.namespace_for(
        os.path.splitext(record["name"])[0], animimport.existing_namespaces())
    result = animimport.import_clip(path, namespace=namespace, merge=False,
                                    set_timeline=True)
    if not result.get("nodes"):
        return "{0} brought nothing into the scene.".format(record["name"])
    return "{0} {1} from {2} as {3} - {4} joints, {5} curves.".format(
        verb, record["name"], record.get("from") or "someone", namespace,
        result.get("joints", 0), result.get("curves", 0))


def open_entry(rid):
    """Open `rid`'s file: a scene as the scene, an FBX into a new one."""
    path, why = _local_or_fetch(rid)
    if not path:
        return _status(why)
    record = state()["entries"][rid]["record"]
    if not _save_changes():
        return _status("Open cancelled - nothing changed.")
    if record["kind"] == "scene":
        cmds.file(path, open=True, force=True, executeScriptNodes=False,
                  ignoreVersion=True, prompt=False)
        _restore_playback()
        note = _clean(cmds.ls(type=["script", "file"]) or [], False)
        return _status("Opened {0} from {1}{2}".format(
            record["name"], record.get("from") or "someone", note))
    cmds.file(new=True, force=True)
    return _status(_import_fbx(path, record, "Opened"))


def import_entry(rid):
    """Import `rid`'s file into the open scene."""
    path, why = _local_or_fetch(rid)
    if not path:
        return _status(why)
    record = state()["entries"][rid]["record"]
    if record["kind"] == "scene":
        nodes = cmds.file(path, i=True, executeScriptNodes=False,
                          ignoreVersion=True, returnNewNodes=True,
                          mergeNamespacesOnClash=False, prompt=False) or []
        note = _clean(nodes, True)
        return _status("Imported {0} from {1} - {2} nodes{3}".format(
            record["name"], record.get("from") or "someone", len(nodes), note))
    return _status(_import_fbx(path, record, "Imported"))


def save_entry(rid, dest=None):
    """A copy of `rid`'s file where the animator picks."""
    path, why = _local_or_fetch(rid)
    if not path:
        return _status(why)
    if dest is None:
        picked = cmds.fileDialog2(
            fileMode=0, caption="Save the shared file",
            startingDirectory=os.path.basename(path),
            fileFilter="{0} (*{1})".format(
                os.path.basename(path), os.path.splitext(path)[1]))
        dest = picked[0] if picked else ""
    if not dest:
        return _status("Nothing saved.")
    shutil.copy2(path, dest)
    return _status("Saved {0} to {1}".format(os.path.basename(path),
                                             dest.replace("\\", "/")))


def _on_selected(action):
    rid = selected_id()
    if rid is None:
        return _status("Pick a file in the list first.")
    return action(rid)


def open_selected(*_args):
    return _on_selected(open_entry)


def import_selected(*_args):
    return _on_selected(import_entry)


def save_selected(*_args):
    return _on_selected(save_entry)


# ---------------------------------------------------------------------- UI

def _status(message, **_kwargs):
    """The section's status line (the hub's message line without one)."""
    print("SkeldarAnim shared: " + message)
    shown = False
    try:
        if cmds.text(STATUS, exists=True):
            cmds.text(STATUS, edit=True, label=message)
            shown = True
    except Exception:                                        # noqa: BLE001
        pass
    hub = sys.modules.get("maya_hub")
    if hub is not None and not shown:
        try:
            hub.say(message)
        except Exception:                                    # noqa: BLE001
            pass
    return message


def _labels(now):
    """(ids, row texts) for the list, newest first."""
    st = state()
    mine_id = machine_id()
    ids, texts = [], []
    for record in records.visible([e["record"] for e in
                                   st["entries"].values()], now):
        rid = record["id"]
        ids.append(rid)
        texts.append(records.row_text(record, records.is_mine(record, mine_id),
                                      _label(rid, record, mine_id), now))
    return ids, texts


def _label(rid, record, mine_id):
    st = state()
    transfer = st["transfers"].get(rid) or {}
    return records.status_label(
        record, records.is_mine(record, mine_id), transfer.get("progress"),
        bool(st["entries"][rid]["local"]), transfer.get("error", ""))


def refresh():
    """The list, keeping the picked row by id. Only the rows that changed
    are rewritten, so a progress tick does not jump the scroll."""
    if not cmds.textScrollList(LIST, exists=True):
        return
    st = state()
    keep = selected_id()
    ids, texts = _labels(time.time())
    old = st["texts"]
    count = cmds.textScrollList(LIST, query=True, numberOfItems=True) or 0
    if old and len(old) == len(texts) == count and st["rows"] == ids:
        for index, (was, now) in enumerate(zip(old, texts)):
            if was != now:
                cmds.textScrollList(LIST, edit=True,
                                    removeIndexedItem=index + 1)
                cmds.textScrollList(LIST, edit=True,
                                    appendPosition=(index + 1, now))
    else:
        cmds.textScrollList(LIST, edit=True, removeAll=True)
        for text in texts:
            cmds.textScrollList(LIST, edit=True, append=text)
    st["rows"], st["texts"] = ids, texts
    if keep in ids:
        cmds.textScrollList(LIST, edit=True,
                            selectIndexedItem=ids.index(keep) + 1)
    refresh_subtitle()


def refresh_subtitle():
    if not cmds.text(SUBTITLE, exists=True):
        return
    st = state()
    cmds.text(SUBTITLE, edit=True,
              label=records.subtitle(st["online"], len(st["rows"])))


def _selected(*_args):
    rid = selected_id()
    entry = state()["entries"].get(rid) if rid else None
    if entry is None:
        return
    record = entry["record"]
    mine_id = machine_id()
    _status(records.details_text(record, records.is_mine(record, mine_id),
                                 _label(rid, record, mine_id), time.time()))


def _name_changed(*_args):
    if cmds.textField(NAME_FIELD, exists=True):
        set_sender_name(cmds.textField(NAME_FIELD, query=True, text=True))


def _run(action):
    try:
        return action()
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        return _status("Shared failed: {0}".format(exc))


def build_panel():
    """The name, the comment, Send scene / Send file..., the list, Open /
    Import / Save to..., a status line (the hub's section). Starts
    listening."""
    import maya_hubstyle as hubstyle   # stdlib
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label="connecting...", align="left"),
                  "subtitle")
    for field, label, text, hint, command in (
            (NAME_FIELD, "Name", sender_name(),
             "your name, as your colleagues see it", _name_changed),
            (COMMENT_FIELD, "Comment", "", "a comment for this file "
             "(optional)", None)):
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                       columnAttach=[(1, "left", 0), (2, "both", 4)])
        cmds.text(label=label, align="left", width=hubstyle.pick(64, 60))
        if command is None:
            cmds.textField(field, text=text, placeholderText=hint)
        else:
            cmds.textField(field, text=text, placeholderText=hint,
                           changeCommand=command)
        cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4)])
    hubstyle.mark(cmds.button(
        label="Send scene", height=32,
        annotation="A copy of the open scene to everybody: it appears in "
                   "their list at once and downloads by itself. Your file "
                   "is not touched.",
        command=lambda *_: _run(send_scene)), "primary", "send")
    hubstyle.mark(cmds.button(
        label="Send file...", height=32, width=hubstyle.pick(120, 110),
        annotation="Pick a .ma, .mb or .fbx and send it to everybody",
        command=lambda *_: _run(send_file)), "secondary", "upload")
    cmds.setParent("..")
    cmds.textScrollList(
        LIST, allowMultiSelection=False, font="fixedWidthFont",
        height=LIST_HEIGHT,
        selectCommand=lambda *_: _run(_selected),
        doubleClickCommand=lambda *_: _run(open_selected))
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4),
                                 (3, "both", 4)])
    hubstyle.mark(cmds.button(
        label="Open", height=28,
        annotation="Open the picked file (script nodes are not run)",
        command=lambda *_: _run(open_selected)), "secondary", "download")
    hubstyle.mark(cmds.button(
        label="Import", height=28, width=hubstyle.pick(90, 80),
        annotation="Import the picked file into the open scene (an FBX "
                   "arrives as its own skeleton, in a namespace)",
        command=lambda *_: _run(import_selected)), "secondary", "transfer-in")
    hubstyle.mark(cmds.button(
        label="Save to...", height=28, width=hubstyle.pick(100, 90),
        annotation="Save a copy of the picked file where you choose",
        command=lambda *_: _run(save_selected)), "secondary", "folder")
    cmds.setParent("..")
    #  two lines tall: a wrapped label keeps the height it was given (trap 67)
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True,
                            height=36), "status")
    cmds.setParent("..")
    st = state()
    st["texts"], st["rows"] = [], []
    load_history()
    refresh()
    listen()
    return column


def is_open():
    return bool(cmds.textScrollList(LIST, exists=True))


def show_window():
    """The hub, on the Shared section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
