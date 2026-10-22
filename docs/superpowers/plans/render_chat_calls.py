"""Chat calls offscreen at 150 %: the call window live with two people, the folded tile, the
incoming-call card, and a chat feed holding a call line and a missed one. The call page is a fake
view drawing two coloured tiles with names (no Chromium). Writes chat_calls.png beside this file.

    mayapy docs/superpowers/plans/render_chat_calls.py
"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SKELDAR_MUTE_SOUNDS", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim")))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..")))

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
for face in ("segoeui.ttf", "segoeuib.ttf", "seguisym.ttf", "seguiemj.ttf"):
    path = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", face)
    if os.path.exists(path):
        QtGui.QFontDatabase.addApplicationFont(path)
APP.setFont(QtGui.QFont("Segoe UI", 9))

import maya_hubmotion as hubmotion  # noqa: E402
from maya_chat import callview as V  # noqa: E402
from maya_chat import toast  # noqa: E402
from maya_chat import window as W  # noqa: E402
from tests import test_chat_callview as TV  # noqa: E402
from tests.test_chat_window import FakeSession, msg, dm_chat, BOB  # noqa: E402

SCALE = 1.5
NOW = int(time.time() * 1000)
W._scale = lambda: SCALE              # the call window and the cards read the hub's scale here
hubmotion.enabled = lambda: False      # pictures of the windows standing, not mid-burst


class Tiles(QtWidgets.QWidget):
    """What the call page shows: a tile a person, their initial and name."""
    PEOPLE = (("Bob", "#4d78b0"), ("Me", "#c0703a"))

    def paintEvent(self, _event):                                          # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor("#121315"))
        gap = 6 * SCALE
        n = len(self.PEOPLE)
        w = (self.width() - gap * (n + 1)) / n
        h = min(self.height() - 2 * gap, w * 0.75)
        y = (self.height() - h) / 2
        for i, (name, colour) in enumerate(self.PEOPLE):
            r = QtCore.QRectF(gap + i * (w + gap), y, w, h)
            g = QtGui.QLinearGradient(r.topLeft(), r.bottomRight())
            g.setColorAt(0, QtGui.QColor(colour))
            g.setColorAt(1, QtGui.QColor("#1b1c1f"))
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(r, 8 * SCALE, 8 * SCALE)
            d = min(w, h) * 0.38
            p.setBrush(QtGui.QColor(255, 255, 255, 40))
            p.drawEllipse(QtCore.QRectF(r.center().x() - d / 2, r.center().y() - d / 2 - 8 * SCALE, d, d))
            p.setPen(QtGui.QColor("#e8e9ec"))
            f = QtGui.QFont("Segoe UI", 1)
            f.setPixelSize(int(d * 0.45))
            f.setBold(True)
            p.setFont(f)
            p.drawText(QtCore.QRectF(r.center().x() - d / 2, r.center().y() - d / 2 - 8 * SCALE, d, d),
                       QtCore.Qt.AlignCenter, name[0])
            f.setPixelSize(int(11 * SCALE))
            f.setBold(False)
            p.setFont(f)
            p.drawText(r.adjusted(8 * SCALE, 0, 0, -6 * SCALE), QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom, name)
        p.end()


def factory(bridge, parent):
    return Tiles(parent), TV.FakePage()


def call_window():
    ses = TV.FakeSession()
    win = V.CallWindow(ses, "video", view_factory=factory)
    win.chat = "dm"
    win.cid = "c-1"
    win.root.resize(int(640 * SCALE), int(440 * SCALE))
    win.root.show()
    live = TV.view(state="live", members=("me", "bob"), answered_at=NOW - 134000)
    ses.tell("call", {"call": live})
    win._page_state({"me": "me", "mic": True, "cam": True, "screen": False, "error": "", "note": "",
                     "peers": {"bob": {"state": "connected", "mic": True, "cam": True}}})
    win._tick()
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
    live_shot = win.root.grab().toImage()
    win.fold(True)
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
    win._tick()
    folded = win.root.grab().toImage()
    win.close_window(at_once=True)
    return live_shot, folded


def incoming():
    view = TV.view(state="ringing", members=("bob",), by="bob", id="c9")
    card = toast.show_call(view, BOB, "Bob")
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
    shot = card.grab().toImage()
    toast.clear()
    return shot


def feed():
    ses = FakeSession()
    st = ses.state
    rows = [msg("a1", 1, text="Созвонимся по клинчу?", at=NOW - 7200000),
            msg("a2", 2, frm="me", text="Давай, через минуту", at=NOW - 7100000),
            msg("a3", 3, frm="me", text="", at=NOW - 7000000),
            msg("a4", 4, text="Глянь 42 кадр, перезалил", at=NOW - 3600000),
            msg("a5", 5, text="", at=NOW - 600000)]
    rows[2]["call"] = {"id": "k1", "kind": "video", "answered": True, "seconds": 7 * 60 + 12}
    rows[4]["call"] = {"id": "k2", "kind": "audio", "answered": False, "seconds": 0}
    st.messages["dm"] = rows
    st.chats["dm"] = dict(dm_chat(last=rows[-1]), unread=0)
    st.chats.pop("dm2", None)
    st.online = {"bob": {"online": True}}
    win = W.ChatWindow(ses, scale=SCALE)
    win.root.resize(int(760 * SCALE), int(520 * SCALE))
    win.root.show()
    win.open_chat("dm")
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
        win.refresh()
        win.resized()
    shot = win.root.grab().toImage()
    win.root.close()
    return shot


def main():
    live, folded = call_window()
    shots = [(u"Звонок", live), (u"Свёрнут", folded), (u"Входящий", incoming()),
             (u"Строки звонков в чате", feed())]
    pad = 20
    width = sum(img.width() for _, img in shots) + pad * (len(shots) + 1)
    height = max(img.height() for _, img in shots) + pad * 2 + 30
    out = QtGui.QImage(width, height, QtGui.QImage.Format_ARGB32)
    out.fill(QtGui.QColor("#2a2c31"))
    p = QtGui.QPainter(out)
    p.setPen(QtGui.QColor("#9a9ca3"))
    p.setFont(QtGui.QFont("Segoe UI", 14))
    x = pad
    for title, img in shots:
        p.drawText(x, pad + 18, title)
        p.drawImage(x, pad + 30, img)
        x += img.width() + pad
    p.end()
    path = os.path.join(HERE, "chat_calls.png")
    out.save(path)
    print("wrote", path, out.width(), out.height())


if __name__ == "__main__":
    main()
