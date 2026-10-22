"""The chat's emoji pictures (spec docs/superpowers/specs/2026-10-22-chat-emoji-fluent-design.md):
cells cut from the shipped Fluent 3D sheets, text with pictures for a QTextDocument, one line
of text and pictures drawn with a painter, and Noto's animations downloaded on first use.
"""
import html
import os

from . import emoji

CELL = 96
COLS = 64
ELLIPSIS = u"…"

_SHEETS = {}
_PIX = {}
_PIX_MAX = 3000


def _qt():
    import maya_hubqt
    return maya_hubqt.qt()


def folder():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "assets", "emoji")


def _sheet(name):
    img = _SHEETS.get(name)
    if img is None:
        img = _SHEETS[name] = _qt().QtGui.QImage(os.path.join(folder(), name))
    return img


def image(glyph):
    """The glyph's 96 px picture, or None when it is not a known emoji."""
    found = emoji.index().cell(glyph) if glyph else None
    if not found:
        return None
    sheet = _sheet(found[0])
    if sheet.isNull():
        return None
    cell = found[1]
    return sheet.copy((cell % COLS) * CELL, (cell // COLS) * CELL, CELL, CELL)


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
    return emoji.index().cell(part) is not None


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
