"""The chat window in look A (Telegram's layout in our colours, 2026-10-22) offscreen at 150 %:
a dm with a call line, a file, a reply with reactions, emoji alone and the unread band; a group;
the narrow window's list. Writes chat_look_a.png beside this file.

    mayapy docs/superpowers/plans/render_chat_look_a.py
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
from tests.test_chat_window import FakeSession, msg, dm_chat, ME, BOB, ANN  # noqa: E402

SCALE = 1.5
NOW = int(time.time() * 1000)
H = 3600000
ZOE = {"id": "zoe", "nick": "zoe", "name": "Зоя", "avatar_v": 0}
MAX = {"id": "max", "nick": "max", "name": "Макс", "avatar_v": 0}
FILE = {"id": "f" * 16, "name": "LongSword_Clinch_v3.ma", "bytes": 12900000, "kind": "scene",
        "fps": 30, "range": [0, 48], "expires_at": NOW + 86400000 * 20}


def scene():
    ses = FakeSession()
    st = ses.state
    me, bob = dict(ME), dict(BOB)
    dm = [
        msg("b2", 2, text="Глянь новый клинч, я залил в Shared", at=NOW - 20 * H),
        msg("b3", 3, frm="me", text="Посмотрю утром", at=NOW - 20 * H + 180000),
        dict(msg("b5", 5, text="", at=NOW - 2 * H), call={"id": "c1", "kind": "audio",
                                                          "answered": True, "seconds": 420}),
        dict(msg("b6", 6, text="", at=NOW - 2 * H + 600000), file=dict(FILE)),
        msg("b7", 7, text="На 42 кадре рука уходит в меч, надо поправить захват",
            at=NOW - 2 * H + 660000),
        msg("b8", 8, frm="me", text="Да, вижу. Поправлю IK и залью снова",
            at=NOW - H, reply_to="b7"),
        msg("b10", 10, text="🔥", at=NOW - H + 60000),
        msg("b11", 11, frm="me", text="Готово, перезалил", at=NOW - 600000),
    ]
    dm[5]["reactions"] = {"👍": ["bob"], "❤️": ["bob", "me"]}
    dm[-1]["edited_at"] = NOW - 500000
    st.messages["dm"] = dm
    st.chats["dm"] = dict(dm_chat(other=bob, last=dm[-1]), unread=0, members=[me, bob])
    st.reads["dm"] = {"bob": 10}
    group = [
        msg("a2", 2, frm="ann", chat="g", text="Всем привет! Кто ведёт ревью в пятницу?",
            at=NOW - 3 * H),
        msg("a3", 3, frm="max", chat="g", text="Я могу, но после обеда", at=NOW - 3 * H + 60000),
        msg("a4", 4, frm="max", chat="g", text="В 15:00 нормально?", at=NOW - 3 * H + 70000),
        msg("a5", 5, frm="me", chat="g", text="Мне подходит", at=NOW - 2 * H),
        msg("a7", 7, frm="zoe", chat="g", text="Залила Idle_Dagger в библиотеку",
            at=NOW - H),
        msg("a8", 8, frm="ann", chat="g", text="Давайте в 15:00, созвонимся прямо здесь",
            at=NOW - H + 120000),
    ]
    group[2]["reactions"] = {"👌": ["me", "ann"]}
    st.messages["g"] = group
    st.chats["g"] = {"id": "g", "kind": "group", "name": "Аниматоры", "admin": "ann",
                     "avatar_v": 0, "members": [me, bob, dict(ANN), ZOE, MAX],
                     "last": group[-1], "unread": 2, "read_upto": 0}
    st.messages["dm2"] = [msg("x", 1, frm="ann", chat="dm2", text="Перезвоню завтра",
                              at=NOW - 30 * H)]
    st.chats["dm2"]["last"] = st.messages["dm2"][0]
    st.chats["dm2"]["unread"] = 0
    st.online = {"bob": {"online": True}, "zoe": {"online": True}}
    st.people = [bob, dict(ANN), dict(ZOE, online=True), dict(MAX, online=False,
                                                               last_seen=NOW - 3 * H)]
    return ses


def settle(win):
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
        win.refresh()
        win.resized()


def main():
    setattr(sys, avatars._ATTR, avatars.Cache(tempfile.mkdtemp(), lambda: None))
    shots = []
    ses = scene()
    win = W.ChatWindow(ses, scale=SCALE)
    win.root.resize(int(760 * SCALE), int(560 * SCALE))
    win.root.show()
    win.open_chat("dm")
    settle(win)
    box = [b for b in win.feed.boxes if b.item.kind == "msg"][4]
    win.feed._hover_row(box.bubble.center())
    win.feed.reply_level = 1.0
    win.composer.setPlainText("Ок, гляну после обеда")
    win.start_reply(ses.state.messages["dm"][4])
    settle(win)
    shots.append(("A · личный чат", win.root.grab().toImage()))
    win.composer.clear()
    win.cancel_bar()

    ses.state.chats["g"]["unread"] = 2
    win.open_chat("g")
    settle(win)
    shots.append(("A · группа, «Непрочитанные»", win.root.grab().toImage()))
    win.destroy()

    narrow = W.ChatWindow(scene(), scale=SCALE)
    narrow.root.resize(int(420 * SCALE), int(560 * SCALE))
    narrow.root.show()
    settle(narrow)
    shots.append(("C · узкое окно", narrow.root.grab().toImage()))
    narrow.destroy()

    pad = 24
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
    path = os.path.join(HERE, "chat_look_a.png")
    out.save(path)
    print("wrote", path, out.width(), out.height())


if __name__ == "__main__":
    main()
