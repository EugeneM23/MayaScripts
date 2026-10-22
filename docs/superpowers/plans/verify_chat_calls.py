"""Chat calls end to end against a live server, headless: three accounts, three sessions with their
real sockets, call windows (callview) each with its call page in Chromium, its fake camera and
microphone - a dm call, then a group of three (a third joining a live call; two answering at once).

    $env:PYTHONIOENCODING='utf-8'; mayapy docs/superpowers/plans/verify_chat_calls.py [server]

Makes three throwaway accounts and deletes them at the end. The run is SILENT: Chromium's fake
microphone beeps, so --mute-audio, and the hub sounds are muted (SKELDAR_MUTE_SOUNDS). The GPU is
off: offscreen Qt with it segfaulted mid-call (verify_call_page.py, 2 runs of 3). Chromium's fake UI
is not used: CallPage grants the camera and microphone itself, to https://skeldar.call only.
Exit code = the number of failed gates.
"""
import os
import shutil
import sys
import tempfile
import time
import uuid

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--mute-audio --use-fake-device-for-media-stream --autoplay-policy=no-user-gesture-required "
    "--disable-gpu --disable-gpu-compositing")
os.environ.setdefault("SKELDAR_MUTE_SOUNDS", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim")))

from PySide6 import QtCore, QtWidgets  # noqa: E402
from PySide6 import QtWebEngineWidgets  # noqa: E402,F401  (before the QApplication: it shares GL contexts)
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

import maya_chat  # noqa: E402
from maya_chat import api as A  # noqa: E402
from maya_chat import callview  # noqa: E402
from maya_chat import calls as C  # noqa: E402
from maya_chat import session as S  # noqa: E402
from maya_chat import store as ST  # noqa: E402

SERVER = sys.argv[1] if len(sys.argv) > 1 else "https://skeldar-chat-staging.skeldar.workers.dev"
RESULTS = []
NUMBERS = {}


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))
    sys.stdout.flush()


def wait(cond, timeout=8.0):
    """Seconds until `cond`, pumping Qt; None when it never came."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        APP.processEvents(QtCore.QEventLoop.AllEvents, 50)
        if cond():
            return time.monotonic() - start
        time.sleep(0.02)
    return None


def pump(seconds):
    wait(lambda: False, seconds)


def now_ms():
    return int(time.time() * 1000)


def peer(win, uid):
    return ((win.state or {}).get("peers") or {}).get(uid) or {}


def bytes_in(win, uid):
    b = peer(win, uid).get("bytes") or {}
    return int(b.get("audio_in", 0)) + int(b.get("video_in", 0))


def route(win):
    """The selected candidate pair's local and remote types ('host', 'srflx', 'relay'), read from
    the page's own RTCPeerConnection."""
    got = {}
    js = ("window.__route = 'asked'; (async () => { try { let out = 'no pair';"
          " for (const p of S.peers.values()) {"
          " const st = await p.pc.getStats(); const by = {}; let sel = null;"
          " st.forEach((s) => { by[s.id] = s; });"
          " st.forEach((s) => { if (s.type === 'transport' && s.selectedCandidatePairId) sel = by[s.selectedCandidatePairId]; });"
          " if (!sel) st.forEach((s) => { if (s.type === 'candidate-pair' && s.state === 'succeeded') sel = sel || s; });"
          " if (sel) out = (by[sel.localCandidateId] || {}).candidateType + '/' + (by[sel.remoteCandidateId] || {}).candidateType; }"
          " window.__route = out; } catch (e) { window.__route = 'error ' + e; } })(); 'ok';")
    win.page.runJavaScript(js, 0, lambda value: got.setdefault("ran", value))
    wait(lambda: "ran" in got, 3)
    pump(1.0)
    win.page.runJavaScript("String(window.__route)", 0, lambda value: got.setdefault("v", value))
    wait(lambda: "v" in got, 3)
    return "%s (%s)" % (got.get("v"), got.get("ran"))


def call_lines(ses, chat):
    return [m for m in ses.state.messages.get(chat, []) if m.get("call")]


def main():
    root = tempfile.mkdtemp(prefix="chatcalls_")
    tag = uuid.uuid4().hex[:6]
    a = S.Session(SERVER, ST.Store(os.path.join(root, "a")))
    b = S.Session(SERVER, ST.Store(os.path.join(root, "b")))
    c = S.Session(SERVER, ST.Store(os.path.join(root, "c")))
    wins = []
    try:
        ma = a.sign_in("cla_" + tag)
        mb = b.sign_in("clb_" + tag)
        gate("both signed in", bool(ma and mb), "%s %s" % (ma["nick"], mb["nick"]))
        gate("both online", wait(lambda: a.state.status == "online" and b.state.status == "online", 15)
             is not None)
        dm = a.open_dm(mb["id"])
        gate("the dm reaches B", wait(lambda: dm in b.state.chats, 10) is not None, dm)

        # 1. A calls; it rings for B
        win_a = callview.start(a, dm, "video")
        wins.append(win_a)
        rang = wait(lambda: bool(C.ringing_for(b.state.calls, mb["id"], now_ms())), 5)
        ringing = C.ringing_for(b.state.calls, mb["id"], now_ms())
        NUMBERS["ring_s"] = rang
        gate("1. B's state has the call ringing within 5 s", rang is not None and win_a is not None,
             "%.2f s" % (rang or -1))
        call_id = ringing[0]["id"] if ringing else None
        gate("   A's window knows the call", wait(lambda: win_a.call_id == call_id, 5) is not None, call_id)

        # 2. B answers with video; both see the other connected
        # Two windows in one process: let A's stand aside so B's is not asked to replace it.
        delattr(sys, callview._ATTR)
        win_b = callview.answer(b, call_id, "video")
        wins.append(win_b)
        joined = wait(lambda: peer(win_a, mb["id"]).get("state") == "connected"
                      and peer(win_b, ma["id"]).get("state") == "connected", 20)
        NUMBERS["connect_s"] = joined
        gate("2. both connected within 20 s", joined is not None,
             "%.2f s  (%s, %s, err %s / %s)" % (joined or -1, peer(win_a, mb["id"]).get("state"),
                                                 peer(win_b, ma["id"]).get("state"),
                                                 win_a.state.get("error"), win_b.state.get("error")))
        routes = (route(win_a), route(win_b))
        NUMBERS["route"] = routes
        print("      candidate pair (local, remote): A %s  B %s" % routes)

        # 3. bytes both ways
        pump(1.0)
        before = (bytes_in(win_a, mb["id"]), bytes_in(win_b, ma["id"]))
        pump(3.0)
        after = (bytes_in(win_a, mb["id"]), bytes_in(win_b, ma["id"]))
        grew = (after[0] - before[0], after[1] - before[1])
        NUMBERS["bytes_3s"] = grew
        gate("3. bytes flow both ways (> 20000 in 3 s each)", grew[0] > 20000 and grew[1] > 20000,
             "A got %d, B got %d; A %s  B %s" % (grew[0], grew[1], peer(win_a, mb["id"]).get("bytes"),
                                                 peer(win_b, ma["id"]).get("bytes")))

        # 4. A mutes; B sees it
        win_a.press("mic")
        muted = wait(lambda: peer(win_b, ma["id"]).get("mic") is False, 3)
        gate("4. A's mute reaches B within 3 s", muted is not None, "%.2f s" % (muted or -1))

        # 5. B hangs up; A's call ends and its window closes
        win_b.hang_up()
        gone = wait(lambda: win_a.closed, 5)
        NUMBERS["end_s"] = gone
        gate("5. A's window closes within 5 s of B hanging up", gone is not None and win_b.closed,
             "%.2f s, the call %s" % (gone or -1, (a.state.calls.get(call_id) or {}).get("state")))

        # 6. the call line
        line = wait(lambda: any(m["call"]["id"] == call_id for m in call_lines(a, dm))
                    and any(m["call"]["id"] == call_id for m in call_lines(b, dm)), 8)
        notes = [m["call"] for m in call_lines(a, dm) + call_lines(b, dm) if m["call"]["id"] == call_id]
        gate("6. both get the call line, answered, >= 1 s", line is not None and len(notes) == 2
             and all(n["answered"] and n["seconds"] >= 1 for n in notes), notes)

        # 7. A calls again; B declines
        win_a2 = callview.start(a, dm, "audio")
        wins.append(win_a2)
        wait(lambda: bool(C.ringing_for(b.state.calls, mb["id"], now_ms())), 5)
        ringing = C.ringing_for(b.state.calls, mb["id"], now_ms())
        call2 = ringing[0]["id"] if ringing else None
        gate("7. the second call rings for B", call2 is not None and call2 != call_id, call2)
        b.decline_call(call2)
        down = wait(lambda: win_a2.closed, 5)
        missed = wait(lambda: any(m["call"]["id"] == call2 and not m["call"]["answered"]
                                  for m in call_lines(a, dm))
                      and any(m["call"]["id"] == call2 and not m["call"]["answered"]
                              for m in call_lines(b, dm)), 8)
        gate("   B declines: A's window closes, the line is missed", down is not None and missed is not None,
             "%.2f s; %s" % (down or -1, [C.note_text(m["call"]) for m in call_lines(a, dm)]))

        # 8. TURN
        servers, turn = b.turn_servers()
        NUMBERS["turn"] = turn
        gate("8. turn_servers answers servers", bool(servers),
             ("TURN" if turn else "STUN only") + " - %d server(s)" % len(servers))

        # 9. three people: a group of three; C joins a live call; every pair connects
        mc = c.sign_in("clc_" + tag)
        wait(lambda: c.state.status == "online", 15)
        group = a.api.group("zzt calls " + tag, [mb["id"], mc["id"]])["id"]
        gate("9. the group of three reaches B and C",
             wait(lambda: group in b.state.chats and group in c.state.chats, 10) is not None, group)
        trio = {"A": (a, ma), "B": (b, mb), "C": (c, mc)}

        def all_connected(w):
            pairs = [(w[x], trio[y][1]["id"]) for x in w for y in w if x != y]
            return all(peer(win, uid).get("state") == "connected" for win, uid in pairs)

        def flowing(w, seconds=3.0, least=10000):
            pairs = [(x, y) for x in w for y in w if x != y]
            before = {p: bytes_in(w[p[0]], trio[p[1]][1]["id"]) for p in pairs}
            pump(seconds)
            return {"%s<-%s" % p: bytes_in(w[p[0]], trio[p[1]][1]["id"]) - before[p] for p in pairs}

        if hasattr(sys, callview._ATTR):
            delattr(sys, callview._ATTR)
        w3 = {"A": callview.start(a, group, "video")}
        wins.append(w3["A"])
        wait(lambda: bool(C.ringing_for(b.state.calls, mb["id"], now_ms())), 5)
        ring3 = C.ringing_for(b.state.calls, mb["id"], now_ms())
        g_call = ring3[0]["id"] if ring3 else None
        delattr(sys, callview._ATTR)
        w3["B"] = callview.answer(b, g_call, "video")
        wins.append(w3["B"])
        two = wait(lambda: all_connected(w3), 20)
        gate("   A and B connected in the group call", two is not None, "%.2f s" % (two or -1))
        delattr(sys, callview._ATTR)
        w3["C"] = callview.answer(c, g_call, "video")             # the third joins a live call
        wins.append(w3["C"])
        three = wait(lambda: all_connected(w3), 25)
        NUMBERS["third_connect_s"] = three
        gate("   C joins the live call: all three pairs connected", three is not None,
             "%.2f s  %s" % (three or -1, {k: sorted((v.state.get("peers") or {}).keys())
                                          for k, v in w3.items()}))
        flow = flowing(w3)
        NUMBERS["bytes_3s_trio"] = flow
        gate("   bytes flow on all six directions (> 10000 in 3 s each)",
             all(v > 10000 for v in flow.values()), flow)
        for k in ("C", "B", "A"):
            w3[k].hang_up()
        gate("   the three-way call ends", wait(lambda: all(w.closed for w in w3.values()), 8) is not None)
        wait(lambda: (a.state.calls.get(g_call) or {}).get("state") == "ended", 8)

        # 10. two answer a group ring at nearly the same time
        if hasattr(sys, callview._ATTR):
            delattr(sys, callview._ATTR)
        w4 = {"A": callview.start(a, group, "video")}
        wins.append(w4["A"])
        wait(lambda: bool(C.ringing_for(b.state.calls, mb["id"], now_ms()))
             and bool(C.ringing_for(c.state.calls, mc["id"], now_ms())), 5)
        ring4 = C.ringing_for(b.state.calls, mb["id"], now_ms())
        g2 = ring4[0]["id"] if ring4 else None
        delattr(sys, callview._ATTR)
        w4["B"] = callview.answer(b, g2, "video")
        delattr(sys, callview._ATTR)
        w4["C"] = callview.answer(c, g2, "video")                 # in the same moment
        wins.extend([w4["B"], w4["C"]])
        both = wait(lambda: all_connected(w4), 25)
        NUMBERS["two_answer_connect_s"] = both
        gate("10. B and C answer together: all three pairs connected", both is not None,
             "%.2f s  %s" % (both or -1, {k: {u: p.get("state") for u, p in
                                              ((v.state.get("peers") or {}).items())}
                                          for k, v in w4.items()}))
        flow = flowing(w4)
        gate("    bytes flow on all six directions", all(v > 10000 for v in flow.values()), flow)
        for k in ("C", "B", "A"):
            w4[k].hang_up()
        wait(lambda: all(w.closed for w in w4.values()), 8)
    finally:
        for win in wins:
            if win is not None:
                try:
                    win.close_window(at_once=True)
                except Exception:                     # noqa: BLE001
                    pass
        if hasattr(sys, callview._ATTR):
            delattr(sys, callview._ATTR)
        pump(0.5)
        for ses in (a, b, c):
            token = ses.store.token()
            ses.stop()
            if token:
                try:
                    A.Api(SERVER, token).delete_me()
                except A.ChatError as exc:
                    print("could not delete an account: %s" % exc.text)
        pump(0.5)
        shutil.rmtree(root, ignore_errors=True)
    failed = RESULTS.count(False)
    print("NUMBERS %s" % NUMBERS)
    print("%d of %d gates failed" % (failed, len(RESULTS)))
    return failed


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(min(code, 255))
