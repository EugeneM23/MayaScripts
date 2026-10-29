"""The share, live in a GUI Maya: WHICH screen it took, the one-press way to Maya's own window,
and a remote voice that keeps playing while its picture is in the stage window.

The animator, 2026-10-29: «Когда я свой рабочий стол шарю то у меня не видно маи а у коллеги все
норм.» Measured the same day on their machine: Chromium offers ONE screen row and it is the
external monitor, while they work on the laptop panel - which Chromium does not offer at all. So
the line must say which monitor was taken, say when it is not theirs, and the button must have a
one-press way to the window they are working in.

A real call window with a real page and a fake session - nothing reaches a server. It shares this
screen for real, so it runs in a Maya with a screen, over the command port:

    p = r'<this file>'
    exec(compile(open(p, encoding='utf-8').read(), p, 'exec'), {'__name__': '__main__', '__file__': p})

    1  a share of the whole screen names the monitor it really took, by name and native size
    2  and says so when that is not the screen this window stands on
    3  «Окно Maya» in the screen button's menu takes Maya's own window, and its picture is live
    4  a second page joins: its voice is RENDERED here (the fix for «не слышно собеседников»)
    5  it shares its screen: the tile travels into the stage window and the voice plays on - the
       sink stays in the page, never inside a tile
    6  nothing is left standing

It writes its gates to verify_call_screen_live_out.txt beside itself.

Spec: docs/superpowers/specs/2026-10-29-call-heard-and-which-screen-design.md
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(HERE, "verify_call_screen_live_out.txt")
MARK = OUT + ".ran"
RUN_S = 4.0

if not os.path.exists(MARK):
    open(MARK, "w").write("ran")
    LINES, GATES = [], []

    def say(text):
        LINES.append(str(text))
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(LINES) + "\n")

    def gate(name, ok, detail=""):
        GATES.append(bool(ok))
        say(("PASS " if ok else "FAIL ") + name + ((" - " + str(detail)) if detail else ""))

    try:
        for path in (os.path.join(REPO, "SkeldarAnim"), REPO):
            if path not in sys.path:
                sys.path.insert(0, path)
        for name in [n for n in list(sys.modules) if n.startswith("maya_chat")]:
            del sys.modules[name]
        from PySide6 import QtCore, QtWidgets
        from maya_chat import callpage
        from maya_chat import callview as V
        from maya_chat import session as S

        app = QtWidgets.QApplication.instance()
        ME, BOB = "me", "bob"

        def pump(seconds, until=None):
            end = time.time() + seconds
            while time.time() < end:
                app.processEvents(QtCore.QEventLoop.AllEvents, 30)
                if until and until():
                    return True
                time.sleep(0.01)
            return bool(until and until())

        class FakeSession(object):
            def __init__(self):
                self.state = S.State()
                self.state.me = {"id": ME, "nick": "me", "name": u"Я"}
                self.state.chats = {"dm": {"id": "dm", "kind": "dm", "name": u"Боб",
                                           "members": [{"id": ME, "name": u"Я"},
                                                       {"id": BOB, "name": u"Боб"}]}}
                self.listeners, self.calls = [], []

            def listen(self, fn):
                self.listeners.append(fn)

            def unlisten(self, fn):
                if fn in self.listeners:
                    self.listeners.remove(fn)

            def tell(self, kind, data):
                for fn in list(self.listeners):
                    fn(kind, data)

            def start_call(self, chat, kind):
                return "c-1"

            def leave_call(self, call_id):
                return True

            def call_signal(self, call_id, to, data):
                self.calls.append((to, data))
                return True

            def turn_servers(self, now=None):
                return [{"urls": ["stun:stun.cloudflare.com:3478"]}], False

            def call_here(self, call_id, on):
                pass

        def js(page, code, seconds=8):
            box = {}
            page.runJavaScript(code, lambda v: box.setdefault("v", v))
            pump(seconds, lambda: "v" in box)
            return box.get("v")

        def obj(page, code, seconds=8):
            raw = js(page, "JSON.stringify(%s)" % code, seconds)
            try:
                return json.loads(raw) if raw else None
            except ValueError:
                return raw

        PICTURE = """
(() => { const v = document.querySelector("video");
  if (!v || !v.videoWidth) return {err: "no picture"};
  const c = document.createElement("canvas"); c.width = 120; c.height = 70;
  const g = c.getContext("2d"); g.drawImage(v, 0, 0, 120, 70);
  const d = g.getImageData(0, 0, 120, 70).data;
  let dark = 0; const colours = new Set();
  for (let i = 0; i < d.length; i += 4) {
    if (d[i] + d[i+1] + d[i+2] < 24) dark++;
    colours.add((d[i] >> 5) + "," + (d[i+1] >> 5) + "," + (d[i+2] >> 5));
  }
  return {w: v.videoWidth, h: v.videoHeight, dark: dark, of: 8400, colours: colours.size};
})()
"""
        SINK = """
(() => { const el = document.getElementById("s-%s");
  return el ? {has: true, paused: el.paused, ready: el.readyState,
               time: Math.round(el.currentTime * 1000) / 1000,
               inTile: !!el.closest(".tile")} : {has: false}; })()
"""

        #  a silent synthetic microphone: no device is opened, nothing is audible, and the
        #  rendering is still measurable (an element that renders advances its currentTime)
        FAKE_MIC = """
window.__ctx = window.__ctx || new AudioContext();
if (!navigator.mediaDevices.__real) {
  navigator.mediaDevices.__real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getUserMedia = function (c) {
    const out = new MediaStream();
    if (c && c.audio) {
      const ctx = window.__ctx;
      const dest = ctx.createMediaStreamDestination();
      const gain = ctx.createGain(); gain.gain.value = 0;
      const osc = ctx.createOscillator(); osc.connect(gain); gain.connect(dest); osc.start();
      for (const t of dest.stream.getAudioTracks()) out.addTrack(t);
    }
    return Promise.resolve(out);
  };
}
"""
        #  the fake screen the OTHER side shares: a canvas, so no second real capture is taken
        FAKE_SCREEN = """
navigator.mediaDevices.getDisplayMedia = function () {
  const cv = document.createElement("canvas"); cv.width = 1280; cv.height = 720;
  const g = cv.getContext("2d");
  setInterval(() => { g.fillStyle = "#" + Math.floor(Math.random() * 16777215).toString(16);
                      g.fillRect(0, 0, 1280, 720); }, 60);
  const s = cv.captureStream(15);
  for (const t of s.getVideoTracks()) {
    t.getSettings = () => ({displaySurface: "monitor", width: 1280, height: 720});
    t.getCapabilities = () => ({width: {max: 1280}, height: {max: 720}});
  }
  return Promise.resolve(s);
};
"""

        V.destroy()
        pump(0.5)
        ses = FakeSession()
        win = V.start(ses, "dm", "voice")
        pump(30, lambda: win.page_ready)
        gate("the call window opens with a real page", win.page_ready)
        js(win.page, FAKE_MIC)
        CALL = {"id": "c1", "chat": "dm", "by": ME, "kind": "voice", "cid": "c-1", "state": "live",
                "members": [ME], "declined": [], "started_at": int(time.time() * 1000),
                "answered_at": int(time.time() * 1000), "ended_at": None}
        ses.tell("call", {"kind": "call", "call": CALL})
        pump(15, lambda: win.started)
        gate("the call started", win.started, (win.call_id, win.page_ready))

        #  two monitors here: the real chooser would put up a menu, and a modal over the command
        #  port stops Maya's idle queue (CLAUDE.md note 6). Take the first screen row, always.
        win.choose_source = lambda request: (
            lambda rows: (rows[0][0], rows[0][1]) if rows else None)(
                V.screen_choices(request, ("screen",)))
        win.press("screen")
        shared = pump(20, lambda: bool(win.state.get("screen")))
        capture = win.state.get("capture") or {}
        screen = V.capture_screen(capture)
        here = win.here_screen()
        say("    capture=%s" % json.dumps(capture, ensure_ascii=False))
        say("    the monitor it is: %s   this window stands on: %s"
            % (screen.name() if screen is not None else None,
               here.name() if here is not None else None))
        gate("a screen share starts", shared, capture)
        gate("the monitor is named by its native size, not the constrained one",
             screen is not None and screen.name() in (win.last_message or "")
             and ("%d×%d" % V.screen_size(screen)) in (win.last_message or ""),
             win.last_message)
        if screen is not None and here is not None and screen.name() != here.name():
            gate("and a screen that is not this window's own is said so",
                 u"на другом экране" in (win.last_message or ""), win.last_message)
        else:
            gate("the shared screen IS this window's own, so nothing is said",
                 u"на другом экране" not in (win.last_message or ""), win.last_message)

        #  --- Maya's own window, in one press
        win.press("screen")
        pump(5, lambda: not win.state.get("screen"))
        win._want = "maya"
        del win.choose_source                     # the real chooser: the «Окно Maya» road
        import maya_hubpop
        main = maya_hubpop._main_window()
        if main is not None:
            main.raise_()
        pump(1)
        win.bridge.send("screen", {"on": True})
        on_maya = pump(25, lambda: (win.state.get("capture") or {}).get("surface") == "window")
        cap2 = win.state.get("capture") or {}
        page = win.stage.page if win.stage is not None else win.page
        pump(3)
        shot = obj(page, PICTURE)
        gate("«Окно Maya» shares Maya's own window", on_maya, cap2)
        gate("and its picture is live, not black",
             bool(shot) and shot.get("colours", 0) > 4 and shot.get("dark", 8400) < 8000, shot)
        gate("the line names the window", u"Окно" in (win.last_message or ""), win.last_message)
        win.press("screen")
        pump(5, lambda: not win.state.get("screen"))

        #  --- a second page: is its voice rendered here?
        other = {"state": {}}
        other["bridge"] = callpage.bridge_class()(
            lambda: other.__setitem__("ready", True),
            lambda to, data: win.bridge.send("signal", {"from": BOB, "data": data}),
            lambda s: other.__setitem__("state", s))
        other["view"], other["page"] = callpage.make_view(other["bridge"])
        other["view"].resize(420, 260)
        other["view"].show()
        ses.call_signal = lambda call_id, to, data: (
            other["bridge"].send("signal", {"from": ME, "data": data}), True)[1]
        pump(25, lambda: other.get("ready"))
        js(other["page"], FAKE_MIC + FAKE_SCREEN)
        #  the window learns that BOB is in the call now: that is what makes it add the peer
        ses.tell("call", {"kind": "call", "call": dict(CALL, members=[ME, BOB])})
        pump(2)
        other["bridge"].send("start", {"me": BOB, "names": {ME: u"Я", BOB: u"Боб"},
                                       "ice_servers": [{"urls": ["stun:stun.cloudflare.com:3478"]}],
                                       "video": False, "peers": [ME], "offer_to": [ME]})
        joined = pump(40, lambda: ((other["state"].get("peers") or {}).get(ME) or {})
                      .get("state") == "connected"
                      and ((win.state.get("peers") or {}).get(BOB) or {}).get("state") == "connected")
        gate("the other side connects", joined,
             (other["state"].get("peers"), win.state.get("peers")))
        gate("its audio arrives",
             pump(20, lambda: ((win.state.get("peers") or {}).get(BOB) or {})
                  .get("bytes", {}).get("audio_in", 0) > 2000),
             ((win.state.get("peers") or {}).get(BOB) or {}).get("bytes"))
        before = obj(win.page, SINK % BOB) or {}
        pump(RUN_S)
        after = obj(win.page, SINK % BOB) or {}
        moved = round((after.get("time") or 0) - (before.get("time") or 0), 3)
        gate("the other's voice is RENDERED in a voice call", moved >= RUN_S / 2.0,
             "%.3f s of playback in %.1f s - %s" % (moved, RUN_S, json.dumps(after)))
        gate("the voice plays outside the tiles", after.get("inTile") is False, after)

        #  --- and while its picture lives in the stage window
        other["bridge"].send("screen", {"on": True})
        sharing = pump(25, lambda: ((win.state.get("peers") or {}).get(BOB) or {}).get("screen"))
        staged = pump(20, lambda: win.stage is not None)
        gate("the other's share reaches us and opens the stage window", sharing and staged,
             (sharing, staged))
        in_stage = obj(win.page, "!!(S.stageTile && S.stageTile.id === 't-%s')" % BOB)
        gate("its tile travelled into the stage window", in_stage is True, in_stage)
        before = obj(win.page, SINK % BOB) or {}
        pump(RUN_S)
        after = obj(win.page, SINK % BOB) or {}
        moved = round((after.get("time") or 0) - (before.get("time") or 0), 3)
        gate("and the voice plays on while the picture is in that window", moved >= RUN_S / 2.0,
             "%.3f s - %s" % (moved, json.dumps(after)))

        other["bridge"].send("end", {})
        pump(2)
        try:
            other["view"].close()
        except Exception:                                     # noqa: BLE001
            pass
        V.destroy()
        pump(1.5)
        gate("nothing is left standing", V.current() is None)
        say("")
        say("%d of %d gates failed" % (GATES.count(False), len(GATES)))
        say("done")
    except Exception:
        import traceback
        LINES.append(traceback.format_exc())
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(LINES) + "\n")
