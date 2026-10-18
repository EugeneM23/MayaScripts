"""Our Channel Box rendered offscreen (2026-10-18): the real widget on a fake link with an
IKLeg_L take, at 150 %, at rest and with a row hovered and a key just set.

    mayapy docs/superpowers/plans/render_channel_box.py   (from the repo root)

Writes docs/superpowers/plans/channel_box.png.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "SkeldarAnim"))
sys.path.insert(0, ROOT)

import maya_hubqt                                            # noqa: E402
import maya_hubstyle                                         # noqa: E402
from maya_channelbox import box as box_module, look          # noqa: E402
from tests.test_channelbox_box import FakeLink, chan        # noqa: E402

UI = 1.5


def take():
    link = FakeLink()
    link.chans = [chan("translateX", 4.8, "doubleLinear", [0, 12, 24], True),
                  chan("translateY", 9.4, "doubleLinear", [0, 6, 12], True),
                  chan("translateZ", -2.5, "doubleLinear", [0, 12, 24], True),
                  chan("rotateX", -18.5, "doubleAngle", [0, 12, 24], True),
                  chan("rotateY", 4.2, "doubleAngle"),
                  chan("rotateZ", -1.7, "doubleAngle", [0, 24], False, muted=True),
                  chan("scaleX", 1.0, locked=True), chan("scaleY", 1.0, locked=True),
                  chan("scaleZ", 1.0, locked=True),
                  chan("visibility", 1, "bool"),
                  chan("swivel", 7.5, keys=[0, 24], changed=True),
                  chan("toe", 0.0), chan("roll", -6.5, keys=[0, 10, 14]),
                  chan("rollAngle", 25.0), chan("stretchy", 0.0, lo=0, hi=10),
                  chan("follow", 10.0, source="driven"), chan("volume", 10.0, lo=0, hi=10)]
    nice = {"translateX": "Translate X", "translateY": "Translate Y", "translateZ": "Translate Z",
            "rotateX": "Rotate X", "rotateY": "Rotate Y", "rotateZ": "Rotate Z", "scaleX": "Scale X",
            "scaleY": "Scale Y", "scaleZ": "Scale Z", "rollAngle": "Roll Angle"}
    for c in link.chans:
        c["nice"] = nice.get(c["attr"], c["attr"].title())
    link.chans[1]["breakdowns"] = [12]
    link.chans[1]["breakdown"] = True
    return link


def main():
    q = maya_hubqt.qt()
    app = q.QtWidgets.QApplication.instance() or q.QtWidgets.QApplication([])
    for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf"):     # offscreen Qt has no fonts
        q.QtGui.QFontDatabase.addApplicationFont(os.path.join("C:/Windows/Fonts", name))
    app.setFont(q.QtGui.QFont("Segoe UI"))
    shots = []
    for state in ("rest", "hover"):
        box = box_module.make(take(), UI, maya_hubstyle.TOKENS, motion=True)
        box.resize(int(340 * UI), int(560 * UI))
        box.show()
        app.processEvents()
        box.refresh(effects=False)
        box.selected = {"translateX", "translateY", "translateZ"}
        if state == "hover":
            t = [0.0]
            box.clock = lambda: t[0]
            i = [n for n, r in enumerate(box.rows) if r["kind"] == "channel"
                 and r["channel"]["key"] == "rotateY"][0]
            box.aim_at(i, "value")
            for _ in range(20):
                t[0] += 16
                box._step()
            j = [n for n, r in enumerate(box.rows) if r["kind"] == "channel"
                 and r["channel"]["key"] == "rollAngle"][0]
            box.canvas.fx.add("set", rect=look.cell_rect(box.placed[j][2]["mark"], UI),
                              hex=maya_hubstyle.TOKENS["accent"])
            t[0] += 150
        app.processEvents()
        img = q.QtGui.QImage(box.size(), q.QtGui.QImage.Format_ARGB32)
        img.fill(q.QtGui.QColor(maya_hubstyle.TOKENS["panel"]))
        box.render(img)
        shots.append(img)
        box.timer.stop()
        box.close()
    pad = 24
    out = q.QtGui.QImage(sum(s.width() for s in shots) + pad * (len(shots) + 1),
                         shots[0].height() + 2 * pad, q.QtGui.QImage.Format_ARGB32)
    out.fill(q.QtGui.QColor("#141517"))
    p = q.QtGui.QPainter(out)
    x = pad
    for s in shots:
        p.drawImage(x, pad, s)
        x += s.width() + pad
    p.end()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channel_box.png")
    out.save(path)
    print(path)


if __name__ == "__main__":
    main()
