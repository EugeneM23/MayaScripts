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
from maya_chat import files as F  # noqa: E402
from maya_chat import session as S  # noqa: E402
from maya_chat import store as ST  # noqa: E402

SERVER = sys.argv[1] if len(sys.argv) > 1 else maya_chat.SERVER
APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
RESULTS = []
DEFERRED = []          # what the file threads hand back to "the main thread"
F.DEFER = DEFERRED.append


def gate(name, ok, detail=""):
    RESULTS.append(ok)
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def wait(cond, timeout=8.0):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        APP.processEvents(QtCore.QEventLoop.AllEvents, 50)
        while DEFERRED:
            DEFERRED.pop(0)()
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

        # everybody sees everybody (2026-10-20): B's newcomer event put B in A's people
        gate("A sees B with no friend request", wait(lambda: any(u["id"] == mb["id"] for u in a.state.people))
             is not None)
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

        # 5b. a reaction, both ways; my picture
        rid = [m for m in a.state.messages[dm] if m["cid"] == cid2][0]["id"]
        b.react(dm, rid, "\U0001F525")
        gate("A sees B's reaction", wait(lambda: has(a, dm, lambda m: m["id"] == rid and
                                                     m["reactions"].get("\U0001F525") == [mb["id"]]))
             is not None)
        b.react(dm, rid, "\U0001F525")
        gate("A sees it taken off", wait(lambda: has(a, dm, lambda m: m["id"] == rid and not m["reactions"]))
             is not None)
        png = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                            "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")
        me = a.set_avatar(png, "image/png")
        gate("B hears A's new picture", wait(lambda: any(m.get("avatar_v") == me["avatar_v"]
                                                         for m in b.state.chats[dm]["members"]
                                                         if m["id"] == ma["id"])) is not None)
        gate("B reads it", b.api.avatar(ma["id"]) == png)

        # 5c. a scene sent as a file (2026-10-22): up in parts, down byte for byte
        if os.environ.get("CHAT_FILES", "1") != "0":
            scene = os.path.join(root, "Run_Cycle.ma")
            with open(scene, "wb") as out:
                out.write(b"//Maya ASCII 2027 scene\n" + os.urandom(20 * 1024 * 1024))
            fcid = F.send_path(a, dm, scene, "the run")
            got = wait(lambda: has(b, dm, lambda m: m["cid"] == fcid), 180)
            gate("B gets the file message", got is not None, "%.1f s" % (got or -1))
            msg = [m for m in b.state.messages.get(dm, []) if m["cid"] == fcid]
            f = (msg[0] if msg else {}).get("file") or {}
            gate("its card: name, caption, size", f.get("name") == "Run_Cycle.ma" and msg[0]["text"] == "the run"
                 and f.get("bytes") == os.path.getsize(scene), f)
            gate("A's own copy is kept as the sent file", bool(F.local_path(a, f)))
            landed = []
            F.fetch(b, f, landed.append) if f else None
            took = wait(lambda: bool(landed), 180)
            with open(scene, "rb") as one:
                same = bool(landed) and open(landed[0], "rb").read() == one.read()
            gate("B downloads it byte for byte", same, "%.1f s" % (took or -1))
            again_path = []
            gate("a second press uses the copy on disk", F.fetch(b, f, again_path.append) and again_path == landed)

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
