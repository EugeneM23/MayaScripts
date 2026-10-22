"""The chat's emoji pictures (spec docs/superpowers/specs/2026-10-22-chat-emoji-fluent-design.md):
cells cut from the shipped Fluent 3D sheets, text with pictures for a QTextDocument, one line
of text and pictures drawn with a painter, and Noto's animations downloaded on first use.
"""
import collections
import html
import os
import sys
import threading
import urllib.request

from . import emoji

CELL = 96
COLS = 64
ELLIPSIS = u"…"

_BAD = set()          # sheets that could not be read
_OK = {}              # glyph -> whether it has a picture
_PIX = {}
_PIX_MAX = 3000


def _qt():
    import maya_hubqt
    return maya_hubqt.qt()


def folder():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "assets", "emoji")


def image(glyph):
    """The glyph's 96 px picture, or None when it is not a known emoji or its sheet cannot
    be read. One cell is cut straight from the file: no whole sheet is held."""
    found = emoji.index().cell(glyph) if glyph else None
    if not found or found[0] in _BAD:
        return None
    q = _qt()
    cell = found[1]
    reader = q.QtGui.QImageReader(os.path.join(folder(), found[0]))
    reader.setClipRect(q.QtCore.QRect((cell % COLS) * CELL, (cell // COLS) * CELL, CELL, CELL))
    img = reader.read()
    if img.isNull() or img.width() != CELL or img.height() != CELL:
        if not q.QtGui.QImageReader(os.path.join(folder(), found[0])).canRead():
            _BAD.add(found[0])
        return None
    return img


def pixmap(glyph, px):
    """The picture at `px` physical pixels, smooth, cached."""
    key = (glyph, int(px))
    held = _PIX.get(key)
    if held is None:
        img = image(glyph)
        if img is None:
            return None
        q = _qt()
        if len(_PIX) > _PIX_MAX:
            _PIX.clear()
        held = _PIX[key] = q.QtGui.QPixmap.fromImage(img.scaled(
            int(px), int(px), q.QtCore.Qt.KeepAspectRatio, q.QtCore.Qt.SmoothTransformation))
    return held


def url(glyph):
    return "emoji:" + "-".join("%x" % ord(ch) for ch in glyph if ch != emoji.VS16)


def _known(part):
    """Whether the glyph has a picture (answered once a glyph)."""
    held = _OK.get(part)
    if held is None:
        held = _OK[part] = image(part) is not None
    return held


def rich(text, px):
    """The message's text as HTML: escaped, links as anchors, known emoji as images `px`
    square, new lines kept."""
    from . import records
    out = []
    for kind, piece in records.runs(text or ""):
        if kind == "link":
            out.append('<a href="{0}">{1}</a>'.format(html.escape(piece, quote=True),
                                                      html.escape(piece)))
            continue
        for part_kind, part in emoji.tokens(piece):
            if part_kind == "emoji" and _known(part):
                out.append('<img src="{0}" width="{1}" height="{1}" '
                           'style="vertical-align: middle">'.format(url(part), int(px)))
            else:
                out.append(html.escape(part))
    return "".join(out).replace("\n", "<br>")


def register(doc, text, px):
    """Every known emoji of `text` added to `doc` as an image resource at `px`."""
    q = _qt()
    for kind, part in emoji.tokens(text or ""):
        if kind == "emoji":
            pm = pixmap(part, px)
            if pm is not None:
                doc.addResource(q.QtGui.QTextDocument.ImageResource, q.QtCore.QUrl(url(part)),
                                pm.toImage())


def _parts(text, font):
    q = _qt()
    fm = q.QtGui.QFontMetricsF(font)
    side = fm.height()
    out = []
    for kind, piece in emoji.tokens(" ".join(str(text or "").split())):
        if kind == "emoji" and _known(piece):
            out.append(("emoji", piece, side))
        else:
            out.append(("text", piece, fm.horizontalAdvance(piece)))
    return out, fm, side


def line_width(text, font):
    parts, _fm, _side = _parts(text, font)
    return sum(w for _k, _p, w in parts)


def draw_line(p, rect, text, font, color):
    """One line of text and emoji pictures (a picture as tall as the font's line) inside
    `rect`, vertically centred, elided with "…" at the right. The width used."""
    q = _qt()
    QtCore = q.QtCore
    parts, fm, side = _parts(text, font)
    width = rect.width()
    if sum(w for _k, _pc, w in parts) > width:
        ell = fm.horizontalAdvance(ELLIPSIS)
        kept, used = [], 0.0
        for kind, piece, w in parts:
            if used + w + ell <= width:
                kept.append((kind, piece, w))
                used += w
                continue
            if kind == "text":
                cut = fm.elidedText(piece, QtCore.Qt.ElideRight, max(0.0, width - used))
                kept.append(("text", cut, fm.horizontalAdvance(cut)))
            elif used + ell <= width:
                kept.append(("text", ELLIPSIS, ell))
            break
        parts = kept
    p.save()
    p.setFont(font)
    p.setPen(color)
    p.setRenderHint(q.QtGui.QPainter.SmoothPixmapTransform)
    x = rect.left()
    base = rect.top() + (rect.height() + fm.ascent() - fm.descent()) / 2.0
    for kind, piece, w in parts:
        if kind == "emoji":
            pm = pixmap(piece, max(1, int(round(side))))
            if pm is not None:
                p.drawPixmap(QtCore.QRectF(x, rect.center().y() - side / 2.0, side, side),
                             pm, QtCore.QRectF(pm.rect()))
        else:
            p.drawText(QtCore.QPointF(x, base), piece)
        x += w
    p.restore()
    return x - rect.left()


# ---------------------------------------------------------------------- Noto's animations
NOTO = "https://fonts.gstatic.com/s/e/notoemoji/latest/{}/512.webp"
_ANIM_ATTR = "_skeldar_chat_emoji_anim"
FRAME_MS = 33


def anim_of(glyph):
    """Noto's codepoint for the glyph's animation, or ""."""
    found = emoji.index().find(glyph) if glyph else None
    return (found[0].get("anim") or "") if found else ""


def _fetch(address):
    req = urllib.request.Request(address, headers={"User-Agent": "skeldar-chat/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _spawn(fn):
    threading.Thread(target=fn, daemon=True).start()


def decode(path, px):
    """Every frame of an animated picture at `px` square, with the time each one ends."""
    q = _qt()
    reader = q.QtGui.QImageReader(path)
    reader.setScaledSize(q.QtCore.QSize(int(px), int(px)))
    out, t = [], 0
    while True:
        img = reader.read()
        if img.isNull():
            break
        delay = reader.nextImageDelay()
        t += delay if delay > 0 else FRAME_MS
        out.append((img, t))
    return out


def frame_at(frames, ms):
    """The frame to draw `ms` into a play: the one playing, or at the end the first one
    (it rests there) and True."""
    if not frames:
        return None, True
    if ms >= frames[-1][1]:
        return frames[0][0], True
    for img, end in frames:
        if ms < end:
            return img, False
    return frames[0][0], True


class Animated(object):
    """Noto's animations under `folder`, fetched once each on a thread and decoded there at
    the size drawn; the frames of the last `keep` kept in memory."""

    def __init__(self, folder, fetch=None, spawn=None, keep=24):
        self.folder = folder
        self.fetch = fetch or _fetch
        self.spawn = spawn or _spawn
        self.keep = keep
        self.lock = threading.Lock()
        self.failed = set()
        self.busy = set()
        self.changed = False
        self._frames = collections.OrderedDict()

    def path(self, cp):
        return os.path.join(self.folder, cp + ".webp")

    def frames(self, cp, px):
        key = (cp, int(px))
        with self.lock:
            held = self._frames.get(key)
            if held is not None:
                self._frames.move_to_end(key)
                return held
            if cp in self.failed or key in self.busy:
                return None
            self.busy.add(key)
        self.spawn(lambda: self._load(cp, key))
        with self.lock:
            return self._frames.get(key)

    def _load(self, cp, key):
        try:
            path = self.path(cp)
            frames = None
            fetched = False
            for _attempt in (0, 1):
                if not os.path.isfile(path):
                    data = self.fetch(NOTO.format(cp))
                    fetched = True
                    os.makedirs(self.folder, exist_ok=True)
                    with open(path + ".part", "wb") as f:
                        f.write(data)
                    os.replace(path + ".part", path)
                try:
                    frames = decode(path, key[1])
                except Exception:                            # noqa: BLE001
                    frames = None
                if frames:
                    break
                try:
                    os.remove(path)          # a bad file must not fail again next launch
                except OSError:
                    pass
                if fetched:
                    break
            if not frames:
                raise ValueError("no frames for " + cp)
            with self.lock:
                self._frames[key] = frames
                while len(self._frames) > self.keep:
                    self._frames.popitem(last=False)
                self.changed = True
        except Exception:                                    # noqa: BLE001
            with self.lock:
                self.failed.add(cp)
        finally:
            with self.lock:
                self.busy.discard(key)

    def take_changed(self):
        with self.lock:
            changed, self.changed = self.changed, False
            return changed


def animated(session=None):
    """This Maya's animations (on sys, so a module reload keeps what was decoded)."""
    held = getattr(sys, _ANIM_ATTR, None)
    if isinstance(held, Animated) and session is None:
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
    folder = os.path.join(root, "emoji_anim")
    if not isinstance(held, Animated) or held.folder != folder:
        held = Animated(folder)
        setattr(sys, _ANIM_ATTR, held)
    return held
