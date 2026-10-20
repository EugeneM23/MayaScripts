"""The chat window offscreen at 150 % with the 2026-10-20 additions: everybody in the list with
the online dots, a picture as an avatar, reactions, a big emoji, the emoji picker.
Writes chat_extras.png beside this file.

    mayapy docs/superpowers/plans/render_chat_extras.py
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
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

from maya_chat import avatars  # noqa: E402
from maya_chat import window as W  # noqa: E402
from tests.test_chat_window import FakeSession, msg, dm_chat, ME, BOB  # noqa: E402

SCALE = 1.5
NOW = int(time.time() * 1000)


def picture(path, colour):
    img = QtGui.QImage(256, 256, QtGui.QImage.Format_RGB32)
    g = QtGui.QLinearGradient(0, 0, 256, 256)
    g.setColorAt(0, QtGui.QColor(colour))
    g.setColorAt(1, QtGui.QColor("#1b1c1f"))
    p = QtGui.QPainter(img)
    p.fillRect(img.rect(), g)
    p.setBrush(QtGui.QColor("#f2d0b0"))
    p.setPen(QtCore.Qt.NoPen)
    p.drawEllipse(QtCore.QRectF(78, 40, 100, 110))
    p.drawEllipse(QtCore.QRectF(38, 160, 180, 160))
    p.end()
    img.save(path, "JPG", 90)


def main():
    folder = tempfile.mkdtemp()
    cache = avatars.Cache(folder, lambda: None)
    setattr(sys, avatars._ATTR, cache)
    picture(avatars.path_for(folder, "bob", 1), "#4d78b0")
    picture(avatars.path_for(folder, "me", 1), "#c0703a")

    ses = FakeSession()
    st = ses.state
    st.me = dict(ME, avatar_v=1)
    bob = dict(BOB, avatar_v=1)
    feed = [
        msg("a1", 1, text="Глянь новый клинч, я залил в Shared", at=NOW - 7200000),
        msg("a2", 2, frm="me", text="Огонь, на 42 кадре только захват поправь", at=NOW - 7000000),
        msg("a3", 3, text="🔥😂", at=NOW - 6900000),
        msg("a4", 4, frm="me", text="Готово, перезалил", at=NOW - 3600000),
    ]
    feed[1]["reactions"] = {"👍": ["bob"], "❤️": ["bob", "me"]}
    feed[3]["reactions"] = {"🔥": ["bob"]}
    st.messages["dm"] = feed
    st.chats["dm"] = dict(dm_chat(other=bob, last=feed[-1]), unread=0,
                          members=[st.me, bob])
    st.chats.pop("dm2", None)
    st.online = {"bob": {"online": True}, "zoe": {"online": True}}
    st.people = [bob,
                 {"id": "zoe", "nick": "zoe", "name": "Зоя", "avatar_v": 0, "online": True},
                 {"id": "max", "nick": "max", "name": "Макс", "avatar_v": 0, "online": False,
                  "last_seen": NOW - 3 * 3600000},
                 {"id": "ann", "nick": "ann", "name": "Аня", "avatar_v": 0, "online": False,
                  "last_seen": NOW - 86400000 * 2}]
    win = W.ChatWindow(ses, scale=SCALE)
    win.avatars = cache
    win.root.resize(int(820 * SCALE), int(560 * SCALE))
    win.root.show()
    win.open_chat("dm")
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
        win.refresh()
        win.resized()
    shots = [("Все пользователи, аватарки, реакции", win.root.grab().toImage())]
    picker = win.pick_emoji(at=(0, 0))
    picker.tab = 1
    QtWidgets.QApplication.processEvents()
    shots.append(("Эмоджи", picker.grab().toImage()))
    picker.close()
    win.show_pane("settings")
    QtWidgets.QApplication.processEvents()
    win.refresh()
    shots.append(("Настройки", win.right.grab().toImage()))

    pad = 20
    width = sum(img.width() for _, img in shots) + pad * (len(shots) + 1)
    height = max(img.height() for _, img in shots) + pad * 2 + 30
    out = QtGui.QImage(width, height, QtGui.QImage.Format_ARGB32)
    out.fill(QtGui.QColor("#121315"))
    p = QtGui.QPainter(out)
    p.setPen(QtGui.QColor("#9a9ca3"))
    p.setFont(QtGui.QFont("Segoe UI", 14))
    x = pad
    for title, img in shots:
        p.drawText(x, pad + 18, title)
        p.drawImage(x, pad + 30, img)
        x += img.width() + pad
    p.end()
    path = os.path.join(HERE, "chat_extras.png")
    out.save(path)
    print("wrote", path, out.width(), out.height())


if __name__ == "__main__":
    main()
