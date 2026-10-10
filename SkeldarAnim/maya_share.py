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

The same evening («кнопку которая будет удалять выбранные файлы. И Name
заменить на author а comment на имя файла или сцены»): **Author** is who a
file is from, **Name** names the upload (empty: the scene's or the file's
own), and **Delete** takes the picked rows off EVERYBODY's list -- the
animator's choice, «Всё у всех» -- through a "deleted" record per file: every
Maya drops the row, stops the transfer and deletes its copy on the disk
(not the scene open in it). The hosts keep the file until it expires; they
have no delete.

Spec: docs/superpowers/specs/2026-09-30-shared-files-design.md,
      docs/superpowers/specs/2026-09-30-shared-delete-and-naming-design.md
"""

import concurrent.futures
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

import maya_hubcopy as hubcopy
import maya_sharenet as net
import maya_sharerecords as records

HUB_SECTION = "shared"
AUTHOR_FIELD = "skeldarShareAuthor"
FILE_NAME_FIELD = "skeldarShareFileName"
LIST = "skeldarShareList"
#  the placeholder under the list the skin turns into its height grip
#  (2026-10-08)
LIST_GRIP = "skeldarShareListGrip"
STATUS = "skeldarShareStatus"
SUBTITLE = "skeldarShareSubtitle"

#  The author's remembered name keeps the optionVar it had when the field
#  was called Name, so what the animator typed survives the relabel.
AUTHOR_VAR = "skeldarShareName"
MACHINE_VAR = "skeldarShareMachine"
FOLDER = "SkeldarShare"
HISTORY = "history.json"

LIST_HEIGHT = 150
REFRESH_EVERY = 0.3             # seconds between progress repaints
FIRST_SINCE = "12h"             # all ntfy.sh keeps: a first start replays it
DELETE_WORKERS = 4              # deletes published side by side (~0.8 s each)


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


# ----------------------------------------------------------------- cards
#
#  The section stands in the hub's card and in every popup copy of it
#  (2026-10-09, maya_hubcopy: a copy is a second build in a scope of its
#  own). The DATA is one set - the entries, the channel, the transfers - so
#  every card shows it; what belongs to a card is its list's rows and its
#  picked rows. The same helpers stand in maya_stash.py.

def cards():
    """The hub's card (None) and every live popup copy of this section, the
    oldest first."""
    return [None] + hubcopy.instances(HUB_SECTION)


def each_card(fn):
    """`fn()` run once in each card's scope, the hub's first; the answers in
    that order. A result that came from a thread or a listener has no scope
    of its own, so it reaches every card this way (2026-10-09, H4): the root
    scope alone refreshed the hub's list and left a copy's stale."""
    answers = []
    for scope in cards():
        with hubcopy.entered(scope):
            answers.append(fn())
    return answers


def _view():
    """The rows and texts of the card the call is in. The hub keeps them on
    the state, as it always did; a popup copy keeps its own (2026-10-09,
    H7): one cache for two lists would let the hub skip the rewrite of its
    list because a copy had just written the same text."""
    st = state()
    scope = hubcopy.current()
    if scope is None:
        return st
    return st.setdefault("copies", {}).setdefault(
        scope.tag, {"rows": [], "texts": []})


def _prune_views():
    """The views of copies that closed are dropped (a tag is never reused)."""
    copies = state().get("copies")
    if copies:
        standing = set(scope.tag for scope in hubcopy.live())
        for tag in list(copies):
            if tag not in standing:
                del copies[tag]


def _option(name):
    if cmds.optionVar(exists=name):
        return cmds.optionVar(query=name) or ""
    return ""


def sender_name():
    """What colleagues see as "from": the Author field's remembered value,
    else the Windows user name."""
    return _option(AUTHOR_VAR) or records.sender_default(getpass.getuser())


def set_sender_name(value):
    cmds.optionVar(stringValue=(AUTHOR_VAR, (value or "").strip()))


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

def _typed_name(name):
    """What the upload is to be called: `name` when a caller gives one, else
    the Name field's text."""
    if name is not None:
        return name
    if cmds.textField(FILE_NAME_FIELD, exists=True):
        return cmds.textField(FILE_NAME_FIELD, query=True, text=True) or ""
    return ""


def _new_record(name):
    return records.make_record(
        "sending", records.new_id(), sender_name(), machine_id(), name, 0,
        time.time(), maya=str(cmds.about(version=True) or ""))


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


def send_scene(name=None):
    """The press: a copy of the open scene to everybody, called `name` (else
    the Name field's text, else the scene's own name)."""
    from maya_uebridge import animimport
    own, file_type = records.scene_file_name(
        cmds.file(query=True, sceneName=True), time.time())
    record = _new_record(records.upload_name(_typed_name(name), own))
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


def send_file(path=None, name=None):
    """The press: `path` (else a file dialog's pick) to everybody, called
    `name` (else the Name field's text, else the file's own name) with the
    file's extension."""
    path = path or _pick_file()
    if not path:
        return _status("Nothing sent.")
    own = os.path.basename(path)
    if records.kind_of(own) is None:
        return _status("Only .ma, .mb and .fbx files can be sent - "
                       "nothing sent.")
    if not os.path.isfile(path):
        return _status("No file at {0} - nothing sent.".format(path))
    record = _new_record(records.upload_name(_typed_name(name), own))
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
    #  a name is one upload's: the next send is called what it is again
    if cmds.textField(FILE_NAME_FIELD, exists=True):
        cmds.textField(FILE_NAME_FIELD, edit=True, text="")
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


def _gone(rid):
    """`rid` has been deleted (read from a transfer's thread too)."""
    entry = state()["entries"].get(rid)
    return entry is not None and records.is_deleted(entry["record"])


def _send_work(record, path):
    """On a thread: announce, zip, upload, say ready -- or say failed. A file
    deleted meanwhile stops at the next step and says nothing: its "deleted"
    is already on the channel, and a "failed" after it would change nothing
    anywhere."""
    rid = record["id"]
    archive = None
    try:
        if _gone(rid):
            raise net.Cancelled("deleted")
        net.publish(records.encode(record))
        archive = _zip(path, record["name"])
        size = os.path.getsize(archive)
        if size > records.MAX_ZIP:
            raise net.ShareError("the zip is {0}, over the hosts' 1 GB"
                                 .format(records.size_text(size)))
        url = net.upload_any(archive, progress=lambda done, total: _progress(
            rid, done, total))
        if _gone(rid):
            raise net.Cancelled("deleted")
        ready = records.with_state(record, "ready", url=url, zip=size)
        net.publish(records.encode(ready))
        _defer(_sent, ready)
    except Exception as exc:                                 # noqa: BLE001
        if _gone(rid):
            _defer(_transfer_done, rid)
            return
        try:
            net.publish(records.encode(records.with_state(record, "failed")))
        except Exception:                                    # noqa: BLE001
            pass
        _defer(_send_failed, rid, _reason(exc))
    finally:
        _remove(archive)


def _transfer_done(rid):
    """A transfer of a deleted file has stopped (main thread)."""
    state()["transfers"].pop(rid, None)
    refresh()


def _progress(rid, done, total):
    """A transfer's progress, from its thread; the list is repainted at most
    every REFRESH_EVERY. False -- net's cancel -- once the file is deleted."""
    if _gone(rid):
        return False
    st = state()
    transfer = st["transfers"].get(rid)
    if transfer is not None:
        transfer["progress"] = (float(done) / total) if total else None
    now = time.time()
    if now - st["last_refresh"] >= REFRESH_EVERY:
        st["last_refresh"] = now
        _defer(refresh)


def _sent(ready):
    if _gone(ready["id"]):
        return _transfer_done(ready["id"])
    st = state()
    entry = st["entries"].get(ready["id"])
    if entry is not None:
        entry["record"] = records.merge(entry["record"], ready)
    st["transfers"].pop(ready["id"], None)
    save_history()
    refresh()
    _say_all("Sent {0} to everybody - {1} zipped, {2:.0f} s.".format(
        ready["name"], records.size_text(ready["zip"]),
        time.time() - ready["sent"]))


def _send_failed(rid, reason):
    if _gone(rid):
        return _transfer_done(rid)
    st = state()
    entry = st["entries"].get(rid)
    if entry is not None:
        entry["record"] = records.merge(
            entry["record"], records.with_state(entry["record"], "failed"))
    st["transfers"].pop(rid, None)
    save_history()
    refresh()
    name = entry["record"]["name"] if entry else "the file"
    _say_all("Sending {0} failed: {1} - nothing was sent.".format(name, reason))


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
    if records.is_deleted(record):
        return _receive_delete(record, now)
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


def _receive_delete(record, now):
    """A "deleted" off the channel: the row goes, the copy on this disk goes
    (not the open scene), and a colleague's delete says so. Our own echo
    changes nothing -- the press applied it already."""
    known = state()["entries"].get(record["id"])
    shown = bool(known) and bool(records.visible([known["record"]], now))
    changed, kept = _apply_delete(record)
    if not changed:
        return False
    save_history()
    refresh()
    if shown and record.get("by_machine") != machine_id():
        _say_all(records.deleted_text(record) + (
            " - your copy stays on this disk: it is the open scene"
            if kept else ""))
    return True


def _apply_delete(record):
    """`record` (a "deleted") into the state: (whether anything changed,
    whether the local copy was kept because it is the open scene). A known
    entry becomes the tombstone; an unknown one becomes one too, so a
    "sending" or "ready" arriving after the delete cannot bring it back."""
    st = state()
    rid = record["id"]
    known = st["entries"].get(rid)
    merged = records.merge(known["record"] if known else None, record)
    if known is not None and merged is known["record"]:
        return False, False
    local = known["local"] if known else ""
    kept = _forget_local(local)
    st["entries"][rid] = {"record": merged, "local": local if kept else ""}
    transfer = st["transfers"].get(rid)
    if transfer is not None and transfer.get("error"):
        #  a failed download is not running: nothing else will clear it
        st["transfers"].pop(rid, None)
    return True, kept


def _inside_share_dir(path):
    root = os.path.normcase(os.path.abspath(share_dir()))
    return os.path.normcase(os.path.abspath(path)).startswith(root + os.sep)


def _is_open_scene(path):
    scene = cmds.file(query=True, sceneName=True) or ""
    return bool(scene) and (os.path.normcase(os.path.abspath(scene))
                            == os.path.normcase(os.path.abspath(path)))


def _forget_local(path):
    """A deleted file's copy off this disk, and its folder when that is
    empty -- never the scene open in this Maya (it stays, and True says so),
    and never anything outside SkeldarShare/."""
    if not path or not os.path.isfile(path) or not _inside_share_dir(path):
        return False
    if _is_open_scene(path):
        return True
    _remove(path)
    _prune(path)
    return False


def _prune(path):
    """`path`'s folder, when it is one of SkeldarShare/'s file folders and
    nothing is left in it."""
    if not path:
        return
    folder = os.path.dirname(os.path.abspath(path))
    try:
        if (os.path.normcase(os.path.dirname(folder))
                == os.path.normcase(os.path.abspath(share_dir()))
                and os.path.isdir(folder) and not os.listdir(folder)):
            os.rmdir(folder)
    except OSError:
        pass


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
    except Exception as exc:                                 # noqa: BLE001
        #  the archive goes first: a delete that stopped this download
        #  prunes the folder it was in
        _remove(archive)
        _defer(_fetch_failed, rid, _reason(exc), path)
        return
    _remove(archive)
    _defer(_fetched, rid, path)


def _fetched(rid, path):
    if _gone(rid):
        #  deleted while its last bytes came in
        _forget_local(path)
        return _transfer_done(rid)
    st = state()
    entry = st["entries"].get(rid)
    if entry is not None:
        entry["local"] = path
    st["transfers"].pop(rid, None)
    save_history()
    refresh()
    if entry is not None:
        each_card(lambda: _refresh_details(rid))


def _fetch_failed(rid, reason, path=None):
    if _gone(rid):
        _prune(path)
        return _transfer_done(rid)
    st = state()
    st["transfers"][rid] = {"progress": None, "error": reason}
    refresh()
    entry = st["entries"].get(rid)
    if entry is not None:
        _say_all("Downloading {0} failed: {1} - Open tries again.".format(
            entry["record"]["name"], reason))


# ----------------------------------------------------------------- actions

def selected_ids():
    """The picked rows' ids, top to bottom (the list takes several). The rows
    are the card's own: the list it is asked about is the card's (2026-10-09)."""
    if not cmds.textScrollList(LIST, exists=True):
        return []
    picked = cmds.textScrollList(LIST, query=True,
                                 selectIndexedItem=True) or []
    rows = _view()["rows"]
    return [rows[index - 1] for index in picked if 0 < index <= len(rows)]


def selected_id():
    """The one picked row's id; None when none or several are picked."""
    ids = selected_ids()
    return ids[0] if len(ids) == 1 else None


def _local_or_fetch(rid):
    """(local path, "") when the file is here, else (None, what to say) --
    and a ready file not here yet is fetched (again, after a failure)."""
    entry = state()["entries"].get(rid)
    if entry is None or records.is_deleted(entry["record"]):
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


def _on_selected(action, verb):
    """`action` on the one picked row."""
    ids = selected_ids()
    if not ids:
        return _status("Pick a file in the list first.")
    if len(ids) > 1:
        return _status("Pick one file to {0} - {1} are picked.".format(
            verb, len(ids)))
    return action(ids[0])


def open_selected(*_args):
    return _on_selected(open_entry, "open")


def import_selected(*_args):
    return _on_selected(import_entry, "import")


def save_selected(*_args):
    return _on_selected(save_entry, "save")


def _confirm_delete(text):
    """Maya's confirm before a delete; True to go on. Batch has nobody to
    answer (a verify run, a test): it goes on."""
    if cmds.about(batch=True):
        return True
    answer = cmds.confirmDialog(
        title="Shared - Delete", message=text, icon="warning",
        button=["Delete", "Cancel"], defaultButton="Cancel",
        cancelButton="Cancel", dismissString="Cancel")
    return answer == "Delete"


def delete_entries(rids):
    """The press: `rids` off everybody's list. One confirm; then a "deleted"
    per file goes to the channel on a thread, and what the channel took is
    applied here too (`_deleted`)."""
    st = state()
    picked = [st["entries"][rid]["record"] for rid in rids
              if rid in st["entries"]
              and not records.is_deleted(st["entries"][rid]["record"])]
    if not picked:
        return _status("Pick files in the list first.")
    if not _confirm_delete(records.delete_question(picked, machine_id())):
        return _status("Delete cancelled - nothing changed.")
    gone = [records.deleted(record, sender_name(), machine_id())
            for record in picked]
    message = _status("Deleting {0} file{1} for everybody...".format(
        len(gone), "" if len(gone) == 1 else "s"))
    _spawn(lambda: _delete_work(gone))
    return message


def delete_selected(*_args):
    return delete_entries(selected_ids())


def _delete_work(gone):
    """On a thread: every "deleted" to the channel, side by side (a publish
    takes ~0.8 s), then the answers to the main thread."""
    def one(record):
        try:
            net.publish(records.encode(record))
            return record, ""
        except Exception as exc:                             # noqa: BLE001
            return record, _reason(exc)
    with concurrent.futures.ThreadPoolExecutor(
            max_workers=DELETE_WORKERS) as pool:
        answers = list(pool.map(one, gone))
    _defer(_deleted, [r for r, why in answers if not why],
           [(r, why) for r, why in answers if why])


def _deleted(done, refused):
    """The channel's answers to a delete (main thread): what it took is
    applied here as everywhere else; what it refused stays, named."""
    kept = []
    for record in done:
        #  the channel's echo may have applied it first: ask the entry
        _apply_delete(record)
        if state()["entries"][record["id"]]["local"]:
            kept.append(record["name"])
    save_history()
    refresh()
    parts = []
    if done:
        parts.append("Deleted {0} file{1} for everybody".format(
            len(done), "" if len(done) == 1 else "s"))
    if kept:
        parts.append("{0} stays on this disk: it is the open scene".format(
            ", ".join(kept)))
    if refused:
        parts.append("{0} not deleted: {1} - nothing changed for {2}".format(
            ", ".join(r["name"] for r, _why in refused), refused[0][1],
            "it" if len(refused) == 1 else "them"))
    return _say_all(" - ".join(parts))


# ---------------------------------------------------------------------- UI

def _status(message, **_kwargs):
    """The section's status line (the hub's message line without one).

    2026-10-08: a line written is also TOLD to the hub (`hubstyle.tell`) -
    the skin hides the card's own line and shows the text on its one message
    line; the classic hub listens to nothing and keeps the line in the card."""
    print("SkeldarAnim shared: " + message)
    shown = False
    try:
        if cmds.text(STATUS, exists=True):
            cmds.text(STATUS, edit=True, label=message)
            shown = True
            import maya_hubstyle   # stdlib
            maya_hubstyle.tell(STATUS, message)
    except Exception:                                        # noqa: BLE001
        pass
    hub = sys.modules.get("maya_hub")
    if hub is not None and not shown:
        try:
            hub.say(message)
        except Exception:                                    # noqa: BLE001
            pass
    return message


def _say_all(message):
    """A line with no press behind it - a thread's or a listener's result: the
    status line of every card says it (2026-10-09, H4). A press answers in its
    own card through `_status`."""
    each_card(lambda: _status(message))
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
    """Every card's list (the hub's and each popup copy's), keeping each one's
    picked rows by id (2026-10-09, H4: a result from a thread reaches them all)."""
    return each_card(_refresh_one)


def _refresh_one():
    """This card's list, keeping its picked rows by id. Only the rows that changed
    are rewritten, so a progress tick does not jump the scroll."""
    if not cmds.textScrollList(LIST, exists=True):
        return
    view = _view()
    keep = selected_ids()
    ids, texts = _labels(time.time())
    old = view["texts"]
    count = cmds.textScrollList(LIST, query=True, numberOfItems=True) or 0
    if old and len(old) == len(texts) == count and view["rows"] == ids:
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
    view["rows"], view["texts"] = ids, texts
    again = [ids.index(rid) + 1 for rid in keep if rid in ids]
    if again:
        cmds.textScrollList(LIST, edit=True, selectIndexedItem=again)
    refresh_subtitle()


def refresh_subtitle():
    if not cmds.text(SUBTITLE, exists=True):
        return
    st = state()
    cmds.text(SUBTITLE, edit=True,
              label=records.subtitle(st["online"], len(_view()["rows"])))


def _selected(*_args):
    ids = selected_ids()
    if len(ids) > 1:
        return _status(records.picked_text(len(ids)))
    entry = state()["entries"].get(ids[0]) if ids else None
    if entry is None:
        return None
    record = entry["record"]
    mine_id = machine_id()
    return _status(records.details_text(
        record, records.is_mine(record, mine_id),
        _label(ids[0], record, mine_id), time.time()))


def _refresh_details(rid):
    """This card's details line, when its one picked row is `rid` - a file
    that arrived for it (2026-10-09: each list has its own selection)."""
    if selected_id() == rid:
        _selected()


def _author_changed(*_args):
    if cmds.textField(AUTHOR_FIELD, exists=True):
        set_sender_name(cmds.textField(AUTHOR_FIELD, query=True, text=True))
        _show_author_elsewhere()


def _show_author_elsewhere():
    """The other cards' Author field shows the name just typed (2026-10-09,
    H5/H7): the name is one remembered value - a copy and the hub read it
    the same way - so a field that still showed the old one would say a
    name that is not the one sent."""
    here = hubcopy.current()
    name = sender_name()
    for scope in cards():
        if scope is here:
            continue
        with hubcopy.entered(scope):
            if (cmds.textField(AUTHOR_FIELD, exists=True)
                    and cmds.textField(AUTHOR_FIELD, query=True,
                                       text=True) != name):
                cmds.textField(AUTHOR_FIELD, edit=True, text=name)


def _run(action):
    try:
        return action()
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        return _status("Shared failed: {0}".format(exc))


def build_panel():
    """The author, the upload's name, Send scene / Send file..., the list
    (several rows can be picked), Open / Import / Save to... / Delete, a
    status line (the hub's section). Starts listening.

    2026-10-08 (the compact hub): in the skin the author and the name share
    one row with no labels (their placeholders say which is which), the
    list's height is the grip's under it, Save to... joins Delete as an icon
    alone, the heights and gaps come from `hubstyle`; the classic hub keeps
    its two labelled rows."""
    import maya_hubstyle as hubstyle   # stdlib
    column = cmds.columnLayout(adjustableColumn=True,
                               rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label="connecting...", align="left"),
                  "subtitle")
    if hubstyle.skinning():
        #  author and name on one row, no labels: the placeholders say which
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                       columnWidth2=(110, 200),
                       columnAttach=[(1, "both", 0), (2, "both", 3)])
        cmds.textField(AUTHOR_FIELD, text=sender_name(),
                       placeholderText="author",
                       height=hubstyle.height("field", 24),
                       annotation="your name, as your colleagues see it",
                       changeCommand=_author_changed)
        cmds.textField(FILE_NAME_FIELD, text="",
                       placeholderText="name (empty: the scene's)",
                       height=hubstyle.height("field", 24))
        cmds.setParent("..")
    else:
        for field, label, text, hint, command in (
                (AUTHOR_FIELD, "Author", sender_name(),
                 "your name, as your colleagues see it", _author_changed),
                (FILE_NAME_FIELD, "Name", "",
                 "empty: the scene's own name", None)):
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
                   columnAttach=[(1, "both", 0), (2, "both", 3)])
    hubstyle.mark(cmds.button(
        label="Send scene", height=hubstyle.height("button", 32),
        annotation="A copy of the open scene to everybody: it appears in "
                   "their list at once and downloads by itself. Your file "
                   "is not touched.",
        command=lambda *_: _run(send_scene)), "primary", "send")
    hubstyle.mark(cmds.button(
        label="Send file...", height=hubstyle.height("button", 32),
        width=hubstyle.pick(104, 110),
        annotation="Pick a .ma, .mb or .fbx and send it to everybody",
        command=lambda *_: _run(send_file)), "secondary", "upload")
    cmds.setParent("..")
    cmds.textScrollList(
        LIST, allowMultiSelection=True, font="fixedWidthFont",
        height=LIST_HEIGHT,
        selectCommand=lambda *_: _run(_selected),
        doubleClickCommand=lambda *_: _run(open_selected),
        deleteKeyCommand=lambda *_: _run(delete_selected))
    #  under the list its height grip (2026-10-08): the skin turns this 8 px
    #  placeholder into a grip and shows the list's remembered rows; the
    #  classic hub keeps the list's pixel height and the placeholder is a
    #  quiet gap
    hubstyle.grip(cmds.separator(LIST_GRIP, height=8, style="none"), LIST)
    cmds.rowLayout(numberOfColumns=4, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4),
                                 (3, "both", 4), (4, "both", 4)])
    hubstyle.mark(cmds.button(
        label="Open", height=hubstyle.height("button", 28),
        annotation="Open the picked file (script nodes are not run)",
        command=lambda *_: _run(open_selected)), "secondary", "download")
    hubstyle.mark(cmds.button(
        label="Import", height=hubstyle.height("button", 28),
        width=hubstyle.pick(84, 80),
        annotation="Import the picked file into the open scene (an FBX "
                   "arrives as its own skeleton, in a namespace)",
        command=lambda *_: _run(import_selected)), "secondary", "transfer-in")
    #  Save to... and Delete are icons alone in the skin: two more words do
    #  not fit the 360 px dock beside Open and Import.
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("", "Save to..."),
        height=hubstyle.height("button", 28),
        width=hubstyle.pick(26, 90),
        annotation="Save a copy of the picked file where you choose",
        command=lambda *_: _run(save_selected)), "secondary", "folder")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("", "Delete"),
        height=hubstyle.height("button", 28),
        width=hubstyle.pick(26, 64),
        annotation="Delete the picked files from everybody's list and "
                   "disks (the Delete key too). The hosts keep a file until "
                   "it expires.",
        command=lambda *_: _run(delete_selected)), "danger", "trash")
    cmds.setParent("..")
    #  two lines tall: a wrapped label keeps the height it was given (trap 67)
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True,
                            height=36), "status")
    cmds.setParent("..")
    view = _view()
    view["texts"], view["rows"] = [], []
    load_history()
    refresh()
    #  The subscriber is the hub's to start (2026-10-09, H6): a copy's build would
    #  restart it - a second connection, a gap in what arrives. A copy starts one
    #  only when none stands (the hub never built, say).
    if hubcopy.current() is None or state().get("subscriber") is None:
        listen()
    return column


def is_open():
    return bool(cmds.textScrollList(LIST, exists=True))


def show_window():
    """The hub, on the Shared section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
