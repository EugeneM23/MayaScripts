"""The chat client core against a live server, headless: two sessions, two caches, real sockets.

    mayapy docs/superpowers/plans/verify_chat_client.py [server]

Makes two throwaway accounts, deletes them at the end. Nothing of Maya is used but its Python and
PySide6 (a QCoreApplication loop drives QWebSocket).
"""
import os
import shutil
import sys
import tempfile
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim")))

from PySide6 import QtCore  # noqa: E402

import maya_chat  # noqa: E402
from maya_chat import api as A  # noqa: E402
from maya_chat import session as S  # noqa: E402
from maya_chat import store as ST  # noqa: E402

SERVER = sys.argv[1] if len(sys.argv) > 1 else maya_chat.SERVER
APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append(ok)
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def wait(cond, timeout=8.0):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        APP.processEvents(QtCore.QEventLoop.AllEvents, 50)
        if cond():
            return time.monotonic() - start
    return None


def has(ses, chat, pred):
    return any(pred(m) for m in ses.state.messages.get(chat, []))


def main():
    root = tempfile.mkdtemp(prefix="chatverify_")
    tag = uuid.uuid4().hex[:6]
    a = S.Session(SERVER, ST.Store(os.path.join(root, "a")))
    b = S.Session(SERVER, ST.Store(os.path.join(root, "b")))
    seen_b = []
    b.listen(lambda kind, data: seen_b.append((kind, data)))
    seen_a = []
    a.listen(lambda kind, data: seen_a.append((kind, data)))
    try:
        ma = a.sign_in("vca_" + tag)
        mb = b.sign_in("vcb_" + tag)
        gate("both signed in", bool(ma and mb), "%s %s" % (ma["nick"], mb["nick"]))
        gate("both online", wait(lambda: a.state.status == "online" and b.state.status == "online") is not None)

        a.api.request(mb["nick"])
        b.api.answer("accept", ma["id"])
        gate("friends by events", wait(lambda: any(u["id"] == mb["id"] for u in a.state.friends["friends"])
                                       and any(u["id"] == ma["id"] for u in b.state.friends["friends"])) is not None)
        dm = a.open_dm(mb["id"])
        gate("the dm reaches B", wait(lambda: dm in b.state.chats) is not None, dm)

        # 1. a send, live
        cid = a.send(dm, "hello from A")
        took = wait(lambda: has(b, dm, lambda m: m["cid"] == cid))
        gate("B gets it live within 1 s", took is not None and took < 1.0, "%.3f s" % (took or -1))
        gate("A's pending became the message", wait(lambda: dm not in a.state.pending) is not None
             and has(a, dm, lambda m: m["cid"] == cid) and a.store.outbox() == [])
        gate("B counts it unread", b.state.chats[dm].get("unread") == 1, str(b.state.chats[dm].get("unread")))

        # 2. B away; it catches up by hello{since}, no resync
        b_token = b.store.token()
        b.stop()
        since_b = b.store.since()
        cid2 = a.send(dm, "while B was away")
        wait(lambda: dm not in a.state.pending)
        resyncs = sum(1 for k, _ in seen_b if k == "resync")
        b._connect(b_token)
        got = wait(lambda: has(b, dm, lambda m: m["cid"] == cid2))
        gate("B back gets it by since", got is not None and sum(1 for k, _ in seen_b if k == "resync") == resyncs,
             "since %d -> %d" % (since_b, b.store.since()))

        # 3. A offline: the outbox goes on reconnect
        a.link.stop()
        wait(lambda: a.protocol.state == "closed")
        cid3 = a.send(dm, "queued offline")
        gate("offline send waits in the outbox", [m["cid"] for m in a.store.outbox()] == [cid3])
        a.link.start()
        got = wait(lambda: has(b, dm, lambda m: m["cid"] == cid3) and a.store.outbox() == [])
        gate("the outbox went on reconnect", got is not None)

        # 4. the same cid twice is one message
        twice = uuid.uuid4().hex
        frame = {"type": "send", "chat": dm, "cid": twice, "text": "twice"}
        a.protocol.push(frame)
        a.protocol.push(frame)
        wait(lambda: has(b, dm, lambda m: m["cid"] == twice))
        wait(lambda: False, 1.0)
        gate("one message for one cid", sum(1 for m in b.state.messages[dm] if m["cid"] == twice) == 1)

        # 5. read marks, typing, edit, delete
        b.read(dm)
        upto = b.state.messages[dm][-1]["seq"]
        gate("A sees B's read mark", wait(lambda: a.state.reads.get(dm, {}).get(mb["id"]) == upto) is not None,
             "upto %d" % upto)
        gate("B's unread is 0", b.state.chats[dm]["unread"] == 0)
        b.typing(dm)
        gate("A sees B typing", wait(lambda: mb["id"] in a.state.typing.get(dm, {})) is not None)
        mid = [m for m in a.state.messages[dm] if m["cid"] == cid][0]["id"]
        a.edit(dm, mid, "hello, edited")
        gate("B sees the edit", wait(lambda: has(b, dm, lambda m: m["id"] == mid and m["text"] == "hello, edited")
                                    ) is not None)
        a.delete(dm, mid)
        gate("B sees the delete", wait(lambda: has(b, dm, lambda m: m["id"] == mid and m["deleted"])) is not None)

        # 6. a refusal: too long
        cid4 = a.send(dm, "x" * 5000)
        gate("a refused send is failed", wait(lambda: any(p["cid"] == cid4 and p["state"] == "failed"
                                                         for p in a.state.pending.get(dm, []))) is not None)
        a.discard(cid4)

        # 7. presence, cache, restart
        b.stop()
        gate("A sees B go offline", wait(lambda: a.state.online.get(mb["id"], {}).get("online") is False) is not None)
        again = S.Session(SERVER, ST.Store(os.path.join(root, "b")))
        again.start()
        gate("a restart reads the cache and signs in", again.state.me and again.state.me["id"] == mb["id"]
             and dm in again.state.chats and len(again.state.messages[dm]) >= 4)
        again.stop()
    finally:
        for ses in (a, b):
            token = ses.store.token()
            ses.stop()
            if token:
                try:
                    A.Api(SERVER, token).delete_me()
                except A.ChatError as exc:
                    print("could not delete an account: %s" % exc.text)
        shutil.rmtree(root, ignore_errors=True)
    failed = RESULTS.count(False)
    print("%d of %d gates failed" % (failed, len(RESULTS)))
    return failed


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
