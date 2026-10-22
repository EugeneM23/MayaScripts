"""A file's preview in the chat (2026-10-22): a picture the sender makes, the receiver draws.

The animator: «давай сделаем так что бы в чате передавалось и превью позы или анимации ... хорошо
бы было делать маленькое превью картинку когда мы экспортируем что-то из сцены в чат или
пересылаем сцену». And pictures pasted with Ctrl+V travel as files of kind "image".

- What a preview is, made on the sender's side (Qt, Maya where it says so):
  a pose card - its own still; an animation card - its preview sheet again at a smaller cell, so
  the chat plays it on hover as the library does (`sheet`: cells, columns, step, fps); a scene or
  a selection - one playblast of the viewport at the current frame; a picture - itself, shrunk.
  Every one a JPEG under `MOST` (the server's picture limit).
- On the server it is the file's `thumb` (PUT/GET /v1/files/<id>/thumb), versioned `thumb_v`; the
  sheet's grid travels in the file's record (`sheet`).
- `Cache` keeps them under `<store>/thumbs/<id>_<v>.jpg`, fetched once on a thread (avatars' way).

Spec: docs/superpowers/specs/2026-10-22-chat-previews-design.md
"""
import json
import math
import os
import sys
import tempfile
import threading

MOST = 256 * 1024        # the server's picture limit
STILL = 360              # px, the longest side of a still preview
IMAGE = 640              # px, the longest side of a picture's preview
CELL = 128               # px, a sheet's cell in the chat (the library's are 320)
QUALITIES = (86, 78, 68, 56, 44)
_ATTR = "_skeldar_chat_thumbs"


def path_for(folder, file_id, version):
    return os.path.join(folder, "%s_%d.jpg" % (file_id, int(version)))


def wanted(f):
    """(id, version) of a file's preview on the server, or None."""
    f = f or {}
    v = int(f.get("thumb_v") or 0)
    return (f["id"], v) if f.get("id") and v > 0 else None


def sheet_of(f):
    """The animation sheet's grid {cells, columns, step, fps} a file carries, or None for a
    still. Pure; anything malformed is a still."""
    s = (f or {}).get("sheet")
    if not isinstance(s, dict):
        return None
    try:
        out = {"cells": int(s["cells"]), "columns": int(s["columns"]), "step": int(s.get("step") or 1),
               "fps": float(s.get("fps") or 0.0)}
    except (KeyError, TypeError, ValueError):
        return None
    if out["cells"] < 2 or out["columns"] < 1 or out["step"] < 1:
        return None
    return out


def cell_rect(index, columns, side):
    """(x, y, w, h) of cell `index` in a sheet of `columns` square cells `side` px. Pure."""
    row, col = divmod(int(index), max(1, int(columns)))
    return (col * side, row * side, side, side)


def play_cell(elapsed_ms, sheet):
    """The cell an animation preview shows `elapsed_ms` after it started (the library's rule);
    at rest (`elapsed_ms` None) the middle one. Pure."""
    cells = sheet["cells"]
    if elapsed_ms is None:
        return cells // 2
    fps, step = sheet["fps"] or 30.0, sheet["step"]
    return int(max(0.0, float(elapsed_ms)) * fps / (1000.0 * step)) % cells


# ---------------------------------------------------------------------- making (Qt)

def _qt():
    import maya_hubqt
    return maya_hubqt.qt()


def jpeg(image, most=MOST):
    """`image` (a QImage) flattened onto the panel colour as JPEG bytes under `most`, smaller
    each try; raises ValueError when even the last is too big."""
    q = _qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    flat = QtGui.QImage(image.size(), QtGui.QImage.Format_RGB32)
    flat.fill(QtGui.QColor("#2b2c30"))
    p = QtGui.QPainter(flat)
    p.drawImage(0, 0, image)
    p.end()
    for quality in QUALITIES:
        buf = QtCore.QBuffer()
        buf.open(QtCore.QIODevice.WriteOnly)
        flat.save(buf, "JPG", quality)
        data = bytes(buf.data())
        if len(data) <= most:
            return data
    if flat.width() > 64:
        half = flat.scaled(flat.width() // 2, flat.height() // 2, QtCore.Qt.KeepAspectRatio,
                           QtCore.Qt.SmoothTransformation)
        return jpeg(half, most)
    raise ValueError(u"Превью слишком большое")


def shrunk(image, longest):
    """`image` scaled so its longest side is at most `longest` px (never up)."""
    q = _qt()
    if max(image.width(), image.height()) <= longest:
        return image
    return image.scaled(longest, longest, q.QtCore.Qt.KeepAspectRatio,
                        q.QtCore.Qt.SmoothTransformation)


def from_picture(path, longest=STILL):
    """(bytes, None): the picture at `path` shrunk; None when it is not a picture."""
    q = _qt()
    image = q.QtGui.QImage(path)
    if image.isNull():
        return None
    return jpeg(shrunk(image, longest)), None


def from_card(path):
    """(bytes, sheet or None) for a Pose Library card's folder: an animation card's preview sheet
    at CELL px cells (its grid as `sheet`), else its still; None when it has neither."""
    q = _qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    header = {}
    for name in ("anim.json", "pose.json"):
        try:
            with open(os.path.join(path, name), encoding="utf-8") as f:
                header = json.load(f)
            break
        except (OSError, ValueError):
            continue
    info = header.get("preview") if isinstance(header.get("preview"), dict) else None
    sheet_path = os.path.join(path, "preview.jpg")
    if info and os.path.isfile(sheet_path):
        try:
            cells, columns = int(info["frames"]), int(info["columns"])
            size, step = int(info["size"]), int(info.get("step") or 1)
        except (KeyError, TypeError, ValueError):
            cells = 0
        source = QtGui.QImage(sheet_path)
        if cells >= 2 and columns >= 1 and size >= 1 and not source.isNull():
            fps = header.get("fps")
            try:
                fps = float(fps)
            except (TypeError, ValueError):
                fps = 30.0
            side = CELL
            while side >= 48:
                rows = int(math.ceil(cells / float(columns)))
                out = QtGui.QImage(columns * side, rows * side, QtGui.QImage.Format_RGB32)
                out.fill(QtGui.QColor("#2b2c30"))
                p = QtGui.QPainter(out)
                p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                for i in range(cells):
                    sx, sy, sw, sh = cell_rect(i, columns, size)
                    dx, dy, dw, dh = cell_rect(i, columns, side)
                    p.drawImage(QtCore.QRectF(dx, dy, dw, dh), source, QtCore.QRectF(sx, sy, sw, sh))
                p.end()
                try:
                    return jpeg(out), {"cells": cells, "columns": columns, "step": step,
                                       "fps": fps or 30.0}
                except ValueError:
                    side = int(side * 0.75)
    still = os.path.join(path, "thumbnail.jpg")
    if os.path.isfile(still):
        return from_picture(still)
    return None


def from_viewport(longest=STILL):
    """(bytes, None): the viewport the animator looks at, at the current frame, as a small still;
    None in batch, with no model panel, or when the playblast fails."""
    import maya.cmds as cmds
    if cmds.about(batch=True):
        return None
    try:
        import maya_vpstudio
        panel = maya_vpstudio.active_panel()
    except Exception:                                        # noqa: BLE001
        panel = None
    if not panel:
        return None
    from maya_poselib import capture
    folder = tempfile.mkdtemp(prefix="skeldar_chat_thumb_")
    target = os.path.join(folder, "still.png")
    shown = {}
    try:
        port = capture._port(panel) or (16, 10)
        width = longest * 2
        height = max(1, int(round(width * float(port[1]) / max(1, port[0]))))
        shown = capture.shown_flags(panel)        # the controls, joints and grid out of the picture
        capture.set_flags(panel, dict((flag, False) for flag in shown))
        now = cmds.currentTime(query=True)
        made = cmds.playblast(frame=[now], format="image", compression="png", viewer=False,
                              showOrnaments=False, offScreen=True, percent=100, quality=90,
                              completeFilename=target, forceOverwrite=True, editorPanelName=panel,
                              widthHeight=(width, height))
        path = made if made and os.path.isfile(str(made)) else target
        if not os.path.isfile(path):
            return None
        return from_picture(path, longest)
    except Exception:                                        # noqa: BLE001
        return None
    finally:
        try:
            capture.set_flags(panel, shown)
        except Exception:                                    # noqa: BLE001
            pass
        try:
            for n in os.listdir(folder):
                os.remove(os.path.join(folder, n))
            os.rmdir(folder)
        except OSError:
            pass


# ---------------------------------------------------------------------- the cache

class Cache(object):
    """Previews on disk under `folder`; a missing one is fetched on a thread through `api_of()`."""

    def __init__(self, folder, api_of, start=None):
        self.folder = folder
        self.api_of = api_of
        self.busy, self.failed = set(), set()
        self.changed = False
        self.lock = threading.Lock()
        self.images = {}
        self._start = start or (lambda fn: threading.Thread(target=fn, daemon=True).start())

    def file(self, f):
        key = wanted(f)
        if key is None:
            return None
        path = path_for(self.folder, *key)
        if os.path.isfile(path):
            return path
        self.fetch(key)
        return None

    def fetch(self, key):
        with self.lock:
            if key in self.busy or key in self.failed:
                return False
            self.busy.add(key)
        api = self.api_of()
        if api is None:
            with self.lock:
                self.busy.discard(key)
            return False

        def run():
            ok = False
            try:
                data = api.file_thumb(key[0])
                if data:
                    self.put(key[0], key[1], data)
                    ok = True
            except Exception:                                # noqa: BLE001
                ok = False
            with self.lock:
                self.busy.discard(key)
                if not ok:
                    self.failed.add(key)

        self._start(run)
        return True

    def put(self, file_id, version, data):
        """A preview on disk (mine at once, or one fetched)."""
        os.makedirs(self.folder, exist_ok=True)
        path = path_for(self.folder, file_id, version)
        tmp = path + ".part"
        with open(tmp, "wb") as out:
            out.write(data)
        os.replace(tmp, path)
        with self.lock:
            self.changed = True
        return path

    def take_changed(self):
        with self.lock:
            out, self.changed = self.changed, False
        return out

    def image(self, f, local=None):
        """The decoded preview (a QImage) of `f` - or of `local`, a pending upload's own - or
        None while it is not here."""
        path = local if local and os.path.isfile(local) else self.file(f)
        if path is None:
            return None
        held = self.images.get(path)
        if held is not None:
            return held
        q = _qt()
        made = q.QtGui.QImage(path)
        if made.isNull():
            key = wanted(f)
            if key is not None:
                self.failed.add(key)
            return None
        if len(self.images) > 120:
            self.images.clear()
        self.images[path] = made
        return made


def cache(session=None):
    """The cache of this Maya (on sys, as the avatars')."""
    held = getattr(sys, _ATTR, None)
    if held is not None and isinstance(held, Cache) and session is None:
        return held
    if session is None:
        try:
            from . import session as _session
            session = _session.get()
        except Exception:                                    # noqa: BLE001
            return None
    root = getattr(getattr(session, "store", None), "root", None)
    if not root:
        return None
    folder = os.path.join(root, "thumbs")
    if held is not None and getattr(held, "folder", None) == folder:
        return held
    made = Cache(folder, lambda: session.api)
    setattr(sys, _ATTR, made)
    return made
