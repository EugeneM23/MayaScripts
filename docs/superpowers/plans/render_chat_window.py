"""The chat window offscreen at 150 %, on a made-up session: sign-in, two columns with a chat,
the friends pane, one column. Writes chat_window.png beside this file.

    mayapy docs/superpowers/plans/render_chat_window.py
"""
import os
import sys
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

from maya_chat import window as W  # noqa: E402
from tests.test_chat_window import FakeSession, msg, dm_chat, ME, BOB, ANN  # noqa: E402

SCALE = 1.5
NOW = int(time.time() * 1000)
CARL = {"id": "carl", "nick": "carl", "name": "Карл", "avatar_v": 0}


def session():
    ses = FakeSession()
    st = ses.state
    day = 86400000
    feed = [
        msg("a1", 1, text="Привет! Глянь новый клинч, я залил в Shared", at=NOW - day - 3600000),
        msg("a2", 2, frm="me", text="Смотрю", at=NOW - day - 3500000),
        msg("a3", 3, text="Там на 42 кадре рука уходит в меч, надо поправить захват",
            at=NOW - 7200000),
        msg("a4", 4, text="https://github.com/EugeneM23/MayaScripts/releases", at=NOW - 7100000),
        msg("a5", 5, frm="me", text="Да, вижу. Поправлю IK и залью снова", at=NOW - 3600000,
            reply_to="a3"),
        msg("a6", 6, frm="me", text="Готово ✓", at=NOW - 3500000),
    ]
    st.messages["dm"] = feed
    st.chats["dm"] = dict(dm_chat(last=feed[-1]), unread=0)
    st.reads["dm"] = {"bob": 5}
    st.pending["dm"] = [{"cid": "p1", "chat": "dm", "text": "И ещё одно, через минуту",
                         "reply_to": None, "at": NOW, "from_id": "me", "state": "sending",
                         "error": None}]
    st.online = {"bob": {"online": True}}
    group = {"id": "g", "kind": "group", "name": "Аниматоры", "admin": "me", "avatar_v": 0,
             "members": [ME, BOB, ANN, CARL], "last": msg("g1", 1, frm="ann", chat="g",
                                                          text="Кто ведёт ревью в пятницу?",
                                                          at=NOW - 600000),
             "unread": 2, "read_upto": 0}
    st.chats["g"] = group
    st.messages["g"] = [group["last"]]
    st.friends = {"friends": [BOB, ANN], "incoming": [CARL], "outgoing": []}
    return ses


def shot(win):
    QtWidgets.QApplication.processEvents()
    win.refresh()
    win.resized()
    QtWidgets.QApplication.processEvents()
    win.refresh()
    QtWidgets.QApplication.processEvents()
    return win.root.grab().toImage()


def main():
    shots = []
    signed_out = FakeSession(signed=False)
    win = W.ChatWindow(signed_out, scale=SCALE)
    win.root.resize(int(760 * SCALE), int(520 * SCALE))
    win.root.show()
    win.nick_field.setText("eugene")
    shots.append(("Вход", shot(win)))
    win.destroy()

    ses = session()
    win = W.ChatWindow(ses, scale=SCALE)
    win.root.resize(int(760 * SCALE), int(520 * SCALE))
    win.root.show()
    win.open_chat("dm")
    win.start_reply(ses.state.messages["dm"][2])
    shots.append(("Чат", shot(win)))
    win.show_pane("friends")
    shots.append(("Друзья", shot(win)))
    win.show_pane("chat")
    win.root.resize(int(540 * SCALE), int(520 * SCALE))
    win.single = "list"
    shots.append(("Одна колонка", shot(win)))
    win.destroy()

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
    path = os.path.join(HERE, "chat_window.png")
    out.save(path)
    print("wrote", path, out.width(), out.height())


if __name__ == "__main__":
    main()
