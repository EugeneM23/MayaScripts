"""Draw SkeldarAnim/assets/character_portraits/Auto.png: the Auto card's «?» (2026-10-02).

The other portraits are renders of their characters (make_character_portraits.py); the Auto card
has no character, so it is drawn: a faint head-and-shoulders silhouette in the hub's muted tone, a
question mark over it in the accent. Vector paths only - offscreen Qt has no font family to draw a
glyph with. 256 x 256 RGBA, transparent, like the others.

    $env:QT_QPA_PLATFORM = 'offscreen'
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/make_auto_portrait.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
OUT = os.path.join(PLUGIN, "assets", "character_portraits", "Auto.png")
SIZE = 256


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, PLUGIN)
    import maya_hubstyle
    from PySide6 import QtCore, QtGui
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication(sys.argv)

    tokens = maya_hubstyle.TOKENS
    image = QtGui.QImage(SIZE, SIZE, QtGui.QImage.Format_ARGB32)
    image.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(image)
    p.setRenderHint(QtGui.QPainter.Antialiasing)

    # the silhouette: a head and the shoulders, cut by the frame like a portrait's
    shade = QtGui.QColor(tokens["muted"])
    shade.setAlphaF(0.30)
    p.setPen(QtCore.Qt.NoPen)
    p.setBrush(shade)
    p.drawEllipse(QtCore.QPointF(128.0, 104.0), 50.0, 58.0)
    body = QtGui.QPainterPath()
    body.addRoundedRect(QtCore.QRectF(30.0, 176.0, 196.0, 140.0), 70.0, 70.0)
    p.drawPath(body)

    # the question mark: a hook, a stem, a dot
    ink = QtGui.QColor(tokens["accent"])
    pen = QtGui.QPen(ink, 26.0)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(QtCore.Qt.NoBrush)
    hook = QtGui.QPainterPath()
    box = QtCore.QRectF(84.0, 46.0, 88.0, 88.0)
    hook.arcMoveTo(box, 165.0)
    hook.arcTo(box, 165.0, -235.0)
    hook.quadTo(QtCore.QPointF(128.0, 140.0), QtCore.QPointF(128.0, 166.0))
    p.drawPath(hook)
    p.setPen(QtCore.Qt.NoPen)
    p.setBrush(ink)
    p.drawEllipse(QtCore.QPointF(128.0, 206.0), 16.0, 16.0)
    p.end()

    folder = os.path.dirname(OUT)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    if not image.save(OUT, "PNG"):
        raise RuntimeError("could not write " + OUT)
    print("wrote", OUT)
    del app


if __name__ == "__main__":
    main()
