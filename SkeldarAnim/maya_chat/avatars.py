"""People's pictures: fetched once a version on a thread, cached on disk, drawn round.

`path_for` / `wanted` are pure; `Cache` downloads with stdlib only (a thread, the session's Api);
`pixmap` and `prepare` are Qt. A user with avatar_v 0 has no picture and keeps the initials.

Spec: docs/superpowers/specs/2026-10-20-chat-everyone-emoji-avatars-design.md
"""
import os
import sys
import threading

SIZE = 256              # px, the square a picture is cut to
MOST = 256 * 1024       # the server's limit
_ATTR = "_skeldar_chat_avatars"


def path_for(folder, user_id, version):
    return os.path.join(folder, "%s_%d.jpg" % (user_id, int(version)))


def wanted(user):
    """(id, version) a user's picture is, or None for no picture."""
    user = user or {}
    v = int(user.get("avatar_v") or 0)
    uid = user.get("id")
    return (uid, v) if uid and v > 0 else None


class Cache(object):
    """Pictures on disk under `folder`; a missing one is fetched on a thread through `api_of()`."""

    def __init__(self, folder, api_of, start=None):
        self.folder = folder
        self.api_of = api_of
        self.busy = set()
        self.failed = set()
        self.changed = False
        self.lock = threading.Lock()
        self.pixmaps = {}
        self._start = start or (lambda fn: threading.Thread(target=fn, daemon=True).start())

    def file(self, user):
        key = wanted(user)
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
                data = api.avatar(key[0])
                if data:
                    os.makedirs(self.folder, exist_ok=True)
                    path = path_for(self.folder, *key)
                    tmp = path + ".part"
                    with open(tmp, "wb") as f:
                        f.write(data)
                    os.replace(tmp, path)
                    ok = True
            except Exception:                                # noqa: BLE001
                ok = False
            with self.lock:
                self.busy.discard(key)
                if ok:
                    self.changed = True
                else:
                    self.failed.add(key)

        self._start(run)
        return True

    def take_changed(self):
        """Whether a picture came since last asked (the window then repaints)."""
        with self.lock:
            out, self.changed = self.changed, False
        return out

    def forget(self):
        self.pixmaps.clear()
        self.failed.clear()

    def put(self, user_id, version, data):
        """My own picture just uploaded: on disk at once, nothing fetched."""
        os.makedirs(self.folder, exist_ok=True)
        with open(path_for(self.folder, user_id, version), "wb") as f:
            f.write(data)
        with self.lock:
            self.changed = True

    # ------------------------------------------------------------------ Qt
    def pixmap(self, user, side):
        """A round QPixmap `side` px across, or None (no picture, or not here yet)."""
        path = self.file(user)
        if path is None:
            return None
        key = (path, int(side))
        held = self.pixmaps.get(key)
        if held is not None:
            return held
        made = round_pixmap(path, side)
        if made is None:
            self.failed.add(wanted(user))
            return None
        if len(self.pixmaps) > 300:
            self.pixmaps.clear()
        self.pixmaps[key] = made
        return made


def _qt():
    import maya_hubqt
    return maya_hubqt.qt()


def round_pixmap(path, side):
    q = _qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    image = QtGui.QImage(path)
    if image.isNull():
        return None
    side = max(4, int(side))
    image = image.scaled(side, side, QtCore.Qt.KeepAspectRatioByExpanding,
                         QtCore.Qt.SmoothTransformation)
    out = QtGui.QPixmap(side, side)
    out.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(out)
    try:
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        clip = QtGui.QPainterPath()
        clip.addEllipse(QtCore.QRectF(0, 0, side, side))
        p.setClipPath(clip)
        p.drawImage(QtCore.QPointF((side - image.width()) / 2.0,
                                   (side - image.height()) / 2.0), image)
    finally:
        p.end()
    return out


def prepare(path):
    """The picture at `path` cut square by its centre, SIZE px, as JPEG bytes under MOST.
    Raises ValueError when it is not an image Qt can read."""
    q = _qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    image = QtGui.QImage(path)
    if image.isNull():
        raise ValueError("Не удалось прочитать картинку")
    side = min(image.width(), image.height())
    image = image.copy((image.width() - side) // 2, (image.height() - side) // 2, side, side)
    image = image.scaled(SIZE, SIZE, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
    flat = QtGui.QImage(image.size(), QtGui.QImage.Format_RGB32)
    flat.fill(QtGui.QColor("#2b2c30"))
    p = QtGui.QPainter(flat)
    p.drawImage(0, 0, image)
    p.end()
    for quality in (90, 80, 70, 55, 40):
        buf = QtCore.QBuffer()
        buf.open(QtCore.QIODevice.WriteOnly)
        flat.save(buf, "JPG", quality)
        data = bytes(buf.data())
        if len(data) <= MOST:
            return data
    raise ValueError("Картинка слишком большая")


# ---------------------------------------------------------------------- one a Maya
def cache(session=None):
    """The cache of this Maya (on sys: a module reload keeps the pictures already read)."""
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
    folder = os.path.join(root, "avatars")
    if held is not None and getattr(held, "folder", None) == folder:
        return held
    made = Cache(folder, lambda: session.api)
    setattr(sys, _ATTR, made)
    return made
