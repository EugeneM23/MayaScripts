"""Scenes and files sent in a chat (2026-10-22). No Maya and no Qt at import.

The animator: «Давай добавим в наш мессенджер возможность пересылки сцен и файлов как в стеше и
шаре». The file travels as one zip in our own R2 (server/chat/worker.js), uploaded in the
server's equal parts; the receiver downloads it on a press into `<store>/files/<id>/<name>`.

- An upload is a PENDING message carrying `file` (what the card draws) and `upload` (progress,
  phase, the local copy, the server's id). A thread zips, starts, sends the parts and completes;
  then, on Maya's main thread, the send frame goes into the outbox like any message, carrying
  `file` (the id) and `file_meta` (the card, so a restart still draws it).
- A download is one thread a file; `then(path)` runs on the main thread once it is on disk.

Threads hand back through `defer` (maya.utils.executeDeferred in Maya; tests set DEFER/SPAWN).

Spec: docs/superpowers/specs/2026-10-22-chat-files-design.md
"""
import os
import shutil
import threading
import time
import traceback
import uuid
import zipfile

from . import api as _api

KINDS = {".ma": "scene", ".mb": "scene", ".fbx": "fbx"}
CARDS = {".pose": "pose", ".anim": "anim"}      # a Pose Library card: its folder, zipped
LIBRARY_FOLDER = "From Chat"
ZIP_LEVEL = 6
TELL_EVERY = 0.2          # a transfer's progress is told at most this often
DEFER = None              # tests: fn -> fn()
SPAWN = None              # tests: fn -> fn()


def kind_of(name):
    """scene / fbx for a file one can send by path."""
    return KINDS.get(os.path.splitext(name or "")[1].lower())


def card_kind(name):
    """pose / anim for a Pose Library card's folder name."""
    return CARDS.get(os.path.splitext(os.path.basename((name or "").rstrip("/\\")))[1].lower())


def is_card(f):
    return (f or {}).get("kind") in ("pose", "anim")


def _size(path):
    if os.path.isdir(path):
        return sum(os.path.getsize(os.path.join(top, n)) for top, _d, names in os.walk(path)
                   for n in names)
    return os.path.getsize(path)


def size_text(size):
    """«340 KB», «12.3 MB», «1.20 GB»."""
    size = int(size or 0)
    if size < 1024 * 1024:
        return "%d KB" % (max(1, int(round(size / 1024.0))) if size else 0)
    if size < 1024 ** 3:
        return "%.1f MB" % (size / 1048576.0)
    return "%.2f GB" % (size / 1073741824.0)


def defer(fn):
    if DEFER is not None:
        return DEFER(fn)
    try:
        import maya.utils
        maya.utils.executeDeferred(fn)
    except ImportError:
        fn()


def spawn(fn):
    if SPAWN is not None:
        return SPAWN(fn)
    thread = threading.Thread(target=fn, name="skeldar-chat-file")
    thread.daemon = True
    thread.start()
    return thread


def _remove(path):
    try:
        if path and os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _root(session, *parts):
    return os.path.join(session.store.root, *parts)


def local_path(session, f):
    """The downloaded (or sent) file on disk, or None."""
    if not f or not f.get("id") or not f.get("name"):
        return None
    path = _root(session, "files", f["id"], os.path.basename(f["name"]))
    if is_card(f):
        return path if os.path.isfile(os.path.join(path, "pose.json")) or \
            os.path.isfile(os.path.join(path, "anim.json")) else None
    return path if os.path.isfile(path) else None


def record_of(f, sender=""):
    """What Shared's open / import ask: name, kind, from."""
    return {"name": f.get("name") or "", "kind": f.get("kind") or "scene", "from": sender}


# -------------------------------------------------------------------- sending

def send_path(session, chat, path, caption="", name=None):
    """A .ma/.mb/.fbx from disk into `chat`; the pending cid, or raises ChatError."""
    own = os.path.basename(path or "")
    if kind_of(own) is None:
        raise _api.ChatError("bad_file", "Only .ma, .mb and .fbx files can be sent")
    if not os.path.isfile(path):
        raise _api.ChatError("bad_file", "No file at %s" % path)
    cid = uuid.uuid4().hex
    folder = _root(session, "uploads", cid)
    os.makedirs(folder, exist_ok=True)
    local = os.path.join(folder, name or own)
    shutil.copy2(path, local)
    return _begin(session, chat, cid, local, caption, {})


def send_scene(session, chat, caption=""):
    """A copy of the active tab (as Shared makes it) into `chat`; the pending cid."""
    import maya.cmds as cmds
    import maya_scenetabs.scope as tabscope
    import maya_sharerecords as share_records
    from maya_uebridge import animimport
    name, file_type = share_records.scene_file_name(tabscope.scene_name(cmds), time.time())
    cid = uuid.uuid4().hex
    folder = _root(session, "uploads", cid)
    os.makedirs(folder, exist_ok=True)
    local = os.path.join(folder, name)
    tabscope.export_scene(local, file_type, cmds)
    meta = {"range": [cmds.playbackOptions(query=True, minTime=True),
                      cmds.playbackOptions(query=True, maxTime=True)]}
    fps = animimport.fps_from_unit(cmds.currentUnit(query=True, time=True))
    if fps:
        meta["fps"] = fps
    return _begin(session, chat, cid, local, caption, meta)


def send_selection(session, chat, caption=""):
    """The objects selected in the scene as one FBX into `chat`, exactly as Stash's «stash the
    selection» writes it (2026-10-22: «отправлять то что в выделении»); the pending cid."""
    import maya.cmds as cmds
    import maya_stash
    import maya_stashstore
    picked = cmds.ls(selection=True, long=True) or []
    if not picked:
        raise _api.ChatError("nothing_selected", u"Сначала выделите объекты, которые отправить.")
    cid = uuid.uuid4().hex
    folder = _root(session, "uploads", cid)
    os.makedirs(folder, exist_ok=True)
    local = os.path.join(folder, maya_stashstore.selection_name(picked, time.time()))
    try:
        maya_stash._export_fbx(picked, local)
    except maya_stash.ExportFailed as exc:
        _remove(folder)
        raise _api.ChatError("export_failed", u"Не удалось выгрузить выделенное в FBX: %s" % exc)
    meta = {"range": [cmds.playbackOptions(query=True, minTime=True),
                      cmds.playbackOptions(query=True, maxTime=True)]}
    return _begin(session, chat, cid, local, caption, meta)


def send_card(session, chat, card, caption=""):
    """A Pose Library card (its .pose / .anim folder) into `chat`; the pending cid."""
    card = (card or "").rstrip("/\\")
    name = os.path.basename(card)
    if card_kind(name) is None or not os.path.isdir(card):
        raise _api.ChatError("bad_file", u"Это не карточка библиотеки поз: %s" % name)
    cid = uuid.uuid4().hex
    folder = _root(session, "uploads", cid)
    os.makedirs(folder, exist_ok=True)
    local = os.path.join(folder, name)
    shutil.copytree(card, local)
    return _begin(session, chat, cid, local, caption, {})


def _begin(session, chat, cid, local, caption, meta):
    name = os.path.basename(local)
    f = {"id": None, "name": name, "kind": kind_of(name) or card_kind(name), "bytes": _size(local),
         "zip": 0, "fps": meta.get("fps"), "range": meta.get("range"), "expired": False}
    session.add_upload(chat, cid, caption, f, local)
    start(session, cid)
    return cid


def start(session, cid):
    """The upload of pending `cid` on a thread (a retry starts it again)."""
    p = session._find_pending(cid)
    if p is None or not p.get("upload"):
        return False
    up = p["upload"]
    up.update(phase="zip", progress=0.0, cancelled=False)
    p["state"], p["error"] = "sending", None
    spawn(lambda: _upload_work(session, cid, p))
    return True


def _upload_work(session, cid, p):
    up, f = p["upload"], p["file"]
    archive = up["local"] + ".zip"
    last = [0.0]

    def told(force=False):
        now = time.time()
        if force or now - last[0] >= TELL_EVERY:
            last[0] = now
            defer(lambda: session.tell("upload", {"chat": p["chat"], "cid": cid}))

    try:
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=ZIP_LEVEL) as out:
            if os.path.isdir(up["local"]):
                for top, _dirs, names in os.walk(up["local"]):
                    for n in sorted(names):
                        full = os.path.join(top, n)
                        rel = os.path.relpath(full, up["local"]).replace(os.sep, "/")
                        out.write(full, f["name"] + "/" + rel)
            else:
                out.write(up["local"], f["name"])
        size = os.path.getsize(archive)
        f["zip"] = size
        if up.get("cancelled"):
            raise _api.ChatError("cancelled", "Stopped")
        up["phase"] = "upload"
        told(True)
        api = session.api
        begun = api.file_start(p["chat"], f["name"], f["kind"], f["bytes"], size,
                               f.get("fps"), f.get("range"))
        up["id"] = begun["id"]
        part_size = int(begun["part_size"])
        count = int(begun["parts"])
        with open(archive, "rb") as handle:
            for n in range(1, count + 1):
                if up.get("cancelled"):
                    raise _api.ChatError("cancelled", "Stopped")
                data = handle.read(part_size)
                api.file_part(up["id"], n, data)
                up["progress"] = float(n) / count
                told()
        api.file_complete(up["id"])
        defer(lambda: _uploaded(session, cid, p))
    except Exception as exc:                                 # noqa: BLE001
        if not isinstance(exc, _api.ChatError):
            traceback.print_exc()
        text = getattr(exc, "text", None) or str(exc)
        cancelled = up.get("cancelled") or getattr(exc, "code", "") == "cancelled"
        if up.get("id") and cancelled:
            try:
                session.api.file_cancel(up["id"])
            except Exception:                                # noqa: BLE001
                pass
        defer(lambda: _upload_failed(session, cid, p, text, cancelled))
    finally:
        _remove(archive)


def _uploaded(session, cid, p):
    """Main thread: the file is on the server; the copy kept as the sent file, the frame out."""
    up, f = p["upload"], p["file"]
    f["id"] = up["id"]
    target = _root(session, "files", f["id"])
    os.makedirs(target, exist_ok=True)
    try:
        shutil.move(up["local"], os.path.join(target, f["name"]))
    except OSError:
        pass
    _remove(os.path.dirname(up["local"]))
    session.upload_done(cid, f)


def _upload_failed(session, cid, p, text, cancelled):
    if cancelled:
        _remove(os.path.dirname(p["upload"]["local"]))
        session.drop_upload(cid)
        return
    session.upload_failed(cid, text)


def cancel(session, cid):
    """Stop an upload; its pending goes once the thread has stopped (or at once if failed)."""
    p = session._find_pending(cid)
    if p is None or not p.get("upload"):
        return False
    up = p["upload"]
    up["cancelled"] = True
    if p.get("state") == "failed":
        _remove(os.path.dirname(up["local"]))
        if up.get("id"):
            try:
                session.api.file_cancel(up["id"])
            except Exception:                                # noqa: BLE001
                pass
        session.drop_upload(cid)
    return True


# -------------------------------------------------------------------- receiving

def fetch(session, f, then=None):
    """`f` on disk, then `then(path)` on the main thread. True when it was there already."""
    path = local_path(session, f)
    if path:
        if then is not None:
            then(path)
        return True
    if f.get("expired"):
        raise _api.ChatError("expired", "This file has expired")
    held = session.state.downloads
    entry = held.get(f["id"])
    if entry is not None and entry.get("state") == "loading":
        if then is not None:
            entry["then"].append(then)
        return False
    entry = {"state": "loading", "progress": 0.0, "error": None,
             "then": [then] if then is not None else []}
    held[f["id"]] = entry
    session.tell("download", {"id": f["id"]})
    spawn(lambda: _download_work(session, f, entry))
    return False


def _download_work(session, f, entry):
    folder = _root(session, "files", f["id"])
    archive = os.path.join(folder, "download.zip")
    last = [0.0]

    def progress(done, total):
        entry["progress"] = (float(done) / total) if total else None
        now = time.time()
        if now - last[0] >= TELL_EVERY:
            last[0] = now
            defer(lambda: session.tell("download", {"id": f["id"]}))
        return not entry.get("cancelled")

    try:
        os.makedirs(folder, exist_ok=True)
        session.api.file_download(f["id"], archive, progress)
        name = os.path.basename(f["name"])
        with zipfile.ZipFile(archive) as zf:
            if is_card(f):
                path = _unzip_card(zf, folder, name)
            else:
                members = [m for m in zf.namelist() if os.path.basename(m) == name] or zf.namelist()
                if not members:
                    raise _api.ChatError("bad_file", "The zip holds nothing")
                with zf.open(members[0]) as src, \
                        open(os.path.join(folder, name) + ".part", "wb") as out:
                    shutil.copyfileobj(src, out, 1024 * 1024)
                os.replace(os.path.join(folder, name) + ".part", os.path.join(folder, name))
                path = os.path.join(folder, name)
        defer(lambda: _downloaded(session, f, entry, path, None))
    except Exception as exc:                                 # noqa: BLE001
        if not isinstance(exc, _api.ChatError):
            traceback.print_exc()
        text = getattr(exc, "text", None) or str(exc)
        defer(lambda: _downloaded(session, f, entry, None, text))
    finally:
        _remove(archive)


def _unzip_card(zf, folder, name):
    """The card's folder out of the zip: only the plain files under `name/` (nothing climbs out)."""
    part = os.path.join(folder, name + ".part")
    _remove(part)
    for member in zf.namelist():
        parts = member.replace("\\", "/").split("/")
        if len(parts) < 2 or parts[0] != name or not parts[-1] or \
                any(p in ("", ".", "..") or ":" in p for p in parts[1:]):
            continue
        target = os.path.join(part, *parts[1:])
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with zf.open(member) as src, open(target, "wb") as out:
            shutil.copyfileobj(src, out, 1024 * 1024)
    if not (os.path.isfile(os.path.join(part, "pose.json")) or
            os.path.isfile(os.path.join(part, "anim.json"))):
        _remove(part)
        raise _api.ChatError("bad_file", u"В архиве нет карточки")
    final = os.path.join(folder, name)
    _remove(final)
    os.replace(part, final)
    return final


def _downloaded(session, f, entry, path, error):
    entry["state"] = "done" if path else "failed"
    entry["error"] = error
    entry["progress"] = 1.0 if path else None
    thens, entry["then"] = entry["then"], []
    session.tell("download", {"id": f["id"], "path": path, "error": error})
    if path:
        for then in thens:
            try:
                then(path)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()


# -------------------------------------------------------------------- what a press does

def open_file(path, f, sender=""):
    import maya_share
    return maya_share.open_file(path, record_of(f, sender))


def import_file(path, f, sender=""):
    import maya_share
    return maya_share.import_file(path, record_of(f, sender))


def to_stash(path, f):
    import maya_stash
    return maya_stash.stash_file(path, os.path.basename(f.get("name") or path))


def to_share(path, f):
    import maya_share
    return maya_share.send_file(path, os.path.basename(f.get("name") or path))


def to_library(path, folder=None):
    """A received card copied into the Pose Library: into `folder` (a catalog, "" the library),
    else «From Chat». The line."""
    from maya_poselib import store, window as libwindow
    root = libwindow.Scene().library()
    folder = LIBRARY_FOLDER if folder is None else folder
    ext = os.path.splitext(path.rstrip("/\\"))[1]
    stem = os.path.splitext(os.path.basename(path.rstrip("/\\")))[0]
    name = store.unique_name(root, folder, stem)
    target = os.path.join(root, folder, name + ext) if folder else os.path.join(root, name + ext)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copytree(path, target)
    try:
        live = libwindow.live()
        if live is not None:
            live.refresh()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    return u"%s - в библиотеке поз (%s)" % (name, folder or "Library")


def apply_card(path, aim):
    """The whole card onto who it was dropped on: a character (`aim` kind character with root),
    or a new character on the floor (kind floor with point). Never cut to 1P upper body or the
    selection: «просто загружаем всю анимацию». The line."""
    from maya_poselib import store, window as libwindow
    scene = libwindow.Scene()
    if aim.get("kind") == "floor":
        result = scene.drop_floor(path, aim.get("point"), False)
    elif store.is_anim(path):
        from maya_poselib import animapply
        root = aim["root"]
        result = scene._paste(lambda header, frames, progress: animapply.apply_onto(
            header, frames, root, mirror=False, options=None, progress=progress), path, None)
    else:
        from maya_poselib import apply
        result = apply.apply_onto(store.read(path), aim["root"], mirror=False)
    return result[-1] if isinstance(result, tuple) and result else (result or "")


def save_to(path, f, dest=None):
    if dest is None:
        import maya.cmds as cmds
        picked = cmds.fileDialog2(fileMode=0, caption="Save the file from the chat",
                                  startingDirectory=os.path.basename(path),
                                  fileFilter="%s (*%s)" % (os.path.basename(path),
                                                           os.path.splitext(path)[1]))
        dest = picked[0] if picked else ""
    if not dest:
        return "Nothing saved."
    shutil.copy2(path, dest)
    return "Saved %s to %s" % (os.path.basename(path), dest.replace("\\", "/"))
