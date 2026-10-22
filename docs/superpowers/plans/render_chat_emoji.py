"""Draw the chat's emoji offscreen at 150 %: a feed with text, a big lone emoji and pills,
and the picker (all, a search, a tone). Writes docs/superpowers/plans/chat_emoji.png.

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_chat_emoji.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
sys.path.insert(0, REPO)

from PySide6 import QtGui, QtWidgets  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
font_dir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
for name in ("segoeui.ttf", "segoeuib.ttf", "seguisym.ttf", "seguiemj.ttf"):
    path = os.path.join(font_dir, name)
    if os.path.exists(path):
        QtGui.QFontDatabase.addApplicationFont(path)
app.setFont(QtGui.QFont("Segoe UI", 9))

from maya_chat import window as W  # noqa: E402
from tests.test_chat_window import FakeSession, msg, dm_chat, ME, BOB  # noqa: E402

SCALE = 1.5


def main():
    ses = FakeSession()
    st = ses.state
    st.me = dict(ME)
    feed = [
        msg("e1", 40, text=u"Сцену с ударом залил \U0001F680 глянь, там рука \U0001F914"),
        msg("e2", 41, frm="me", text=u"Огонь \U0001F525\U0001F525 поправлю завтра \U0001F64F\U0001F3FD"),
        msg("e3", 42, text=u"\U0001F602"),
        msg("e4", 43, frm="me", text=u"\U0001F389\U0001F60E"),
    ]
    feed[1]["reactions"] = {u"\U0001F44D": ["me", "bob"], u"\u2764\uFE0F": ["bob"]}
    st.messages["dm"] = feed
    st.chats["dm"] = dict(dm_chat(other=BOB, last=feed[-1]), unread=0, members=[st.me, BOB])
    st.chats.pop("dm2", None)
    win = W.ChatWindow(ses, scale=SCALE)
    win.root.resize(int(760 * SCALE), int(560 * SCALE))
    win.root.show()
    win.open_chat("dm")
    for _ in range(3):
        app.processEvents()
        win.refresh()
        win.resized()
    shots = [win.root.grab().toImage()]
    picker = win.pick_emoji(at=(0, 0))
    app.processEvents()
    shots.append(picker.grab().toImage())
    picker.set_query(u"кот")
    app.processEvents()
    shots.append(picker.grab().toImage())
    picker.set_query("")
    picker.set_tone(3)
    picker.scroll_to("people")
    app.processEvents()
    shots.append(picker.grab().toImage())
    picker.close()
    pad = 20
    width = sum(s.width() for s in shots) + pad * (len(shots) + 1)
    height = max(s.height() for s in shots) + pad * 2
    sheet = QtGui.QImage(width, height, QtGui.QImage.Format_ARGB32)
    sheet.fill(QtGui.QColor("#17181b"))
    p = QtGui.QPainter(sheet)
    x = pad
    for s in shots:
        p.drawImage(x, pad, s)
        x += s.width() + pad
    p.end()
    out = os.path.join(HERE, "chat_emoji.png")
    sheet.save(out)
    print(out)
    win.destroy()


if __name__ == "__main__":
    main()
