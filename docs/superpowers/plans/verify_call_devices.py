"""A call survives its microphone: three real call pages in one headless mayapy, Chromium's fake
devices, wired to each other as verify_call_page.py wires them.

The animator, 2026-10-29: «мая говорит что микрофон не найден и отклоняет звонки и я ничего не
слышал когда мне звонили». Their prefs held a `skeldarChatCallMic` from an earlier Maya session,
Chromium salts a deviceId per origin (our profile is off the record), and the page asked for that
id `exact` - OverconstrainedError, `start` returned before a single peer was built, and the window
left the call. What is gated here:

    the root cause           an id that is gone, asked exact, raises; asked as an ideal it does not
    a stale id               the call connects and carries audio all the same
    the remembered label     resolves the stale id onto the device the animator actually picked
    no microphone at all     the page joins, HEARS everybody, and says so
    the microphone button    with none held, it looks for one - and the others hear it
    a device change          devicechange and the track's own `ended` take the other microphone
                             into every peer
    a camera that cannot     costs no microphone (the two were one getUserMedia)

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/verify_call_devices.py

Spec: docs/superpowers/specs/2026-10-29-call-devices-design.md
"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = ("--mute-audio --use-fake-device-for-media-stream "
                                            "--autoplay-policy=no-user-gesture-required "
                                            "--disable-gpu --disable-gpu-compositing")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

from PySide6 import QtCore, QtWidgets  # noqa: E402
from PySide6 import QtWebEngineWidgets  # noqa: E402,F401  (before the QApplication: it shares GL contexts)
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from maya_chat import callpage  # noqa: E402

GATES = []
SIDES = {}
ICE = [{"urls": ["stun:stun.cloudflare.com:3478"]}]
#  a 64-hex id of nothing, the shape Chromium gives and the shape the animator's prefs hold
DEAD = "11ead41f8b74a1272f91217584631128375bd0bf9928bd8a2ef9f048889efc21"

#  getUserMedia under the test's hand: `window.__block` decides which kind is refused, and the
#  real one is kept so a gate can still ask Chromium itself something.
BLOCK = """
window.__block = { audio: false, video: false };
if (!navigator.mediaDevices.__real) {
  navigator.mediaDevices.__real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getUserMedia = function (c) {
    const b = window.__block || {};
    if (b.audio && c && c.audio) return Promise.reject(new DOMException("no mic", "NotFoundError"));
    if (b.video && c && c.video) return Promise.reject(new DOMException("no cam", "NotReadableError"));
    return navigator.mediaDevices.__real(c);
  };
}
"""


def gate(name, ok, detail=""):
    GATES.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" - " + str(detail) if detail else ""))
    sys.stdout.flush()


def pump(seconds, until=None):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents(QtCore.QEventLoop.AllEvents, 50)
        if until and until():
            return True
        time.sleep(0.01)
    return bool(until and until())


class Side(object):
    def __init__(self, me):
        self.me, self.ready, self.state, self.other = me, False, {}, None
        SIDES[me] = self
        self.bridge = callpage.bridge_class()(self._ready, self._signal, self._state)
        self.view, self.page = callpage.make_view(self.bridge)
        self.view.resize(480, 300)
        self.view.show()

    def _ready(self):
        self.ready = True

    def _signal(self, to, data):
        if to in SIDES:
            SIDES[to].bridge.send("signal", {"from": self.me, "data": data})

    def _state(self, s):
        self.state = s

    def of(self, uid):
        return (self.state.get("peers") or {}).get(uid) or {}

    def peer(self):
        return self.of(self.other.me)

    def js(self, code, seconds=10):
        """The value of `code` in the page (an expression, or an async one left on __answer)."""
        held = {}
        self.page.runJavaScript("(function(){ try { return " + code + "; }"
                                " catch (e) { return 'raise: ' + e; } })()", 0,
                                lambda v: held.setdefault("v", v))
        pump(seconds, lambda: "v" in held)
        return held.get("v")

    def run(self, code):
        self.page.runJavaScript(code)
        pump(0.4)

    def block(self, audio=False, video=False):
        self.run("window.__block = { audio: %s, video: %s };"
                 % ("true" if audio else "false", "true" if video else "false"))

    def arm(self):
        self.run(BLOCK)

    def mic_id(self):
        return self.js("(S.local && S.local.getAudioTracks()[0]"
                       " ? S.local.getAudioTracks()[0].getSettings().deviceId : '')")

    def sender_track(self, uid):
        return self.js("(function(){var p=S.peers.get('%s');if(!p)return '';"
                       "var t=p.pc.getTransceivers().find(function(x){return x.receiver.track"
                       " && x.receiver.track.kind==='audio';});"
                       "return t && t.sender.track ? t.sender.track.id : '';})()" % uid)

    def fake_id(self, label):
        """The deviceId Chromium gives, in THIS page, to the microphone labelled `label`.

        Each page has an off-the-record profile of its own, so the ids are salted per page AND the
        labels are blank until that page has been granted a capture: ask after its `start`."""
        held = {}
        self.run("window.__ids = '';")
        self.page.runJavaScript(
            "navigator.mediaDevices.enumerateDevices().then(function(all){"
            "window.__ids = JSON.stringify(all.filter(function(d){return d.kind==='audioinput';})"
            ".map(function(d){return [d.label, d.deviceId];}));});")
        pump(8, lambda: bool(self.js("window.__ids || ''", 3)))
        import json
        rows = json.loads(self.js("window.__ids || '[]'") or "[]")
        for text, ident in rows:
            if text == label:
                held["id"] = ident
        return held.get("id", "")


def flowing(side, uid, kinds=("audio_in",), least=2000):
    got = side.of(uid).get("bytes") or {}
    return all(got.get(k, 0) > least for k in kinds)


def main():
    a, b = Side("a"), Side("b")
    a.other, b.other = b, a
    gate("two pages load and open their channel", pump(25, lambda: a.ready and b.ready))
    for side in (a, b):
        side.arm()

    # ---------------------------------------------------------------- the root cause, pinned
    asked = {}
    a.page.runJavaScript(
        "navigator.mediaDevices.__real({audio: {deviceId: {exact: '%s'}}})"
        ".then(function(){window.__exact='ok';})"
        ".catch(function(e){window.__exact=e.name;});" % DEAD)
    pump(10, lambda: bool(a.js("window.__exact || ''", 3)))
    asked["exact"] = a.js("window.__exact || ''")
    gate("a device that is gone, asked `exact`, raises OverconstrainedError",
         asked["exact"] == "OverconstrainedError", asked["exact"])

    # ---------------------------------------------------------------- a stale id, and its label
    a.bridge.send("start", {"me": "a", "names": {"a": "Ann", "b": "Bob"}, "ice_servers": ICE,
                            "video": False, "peers": [], "offer_to": [], "mic": DEAD})
    pump(3)
    a.bridge.send("add_peer", {"uid": "b", "offer": False})
    b.bridge.send("start", {"me": "b", "names": {"a": "Ann", "b": "Bob"}, "ice_servers": ICE,
                            "video": False, "peers": ["a"], "offer_to": ["a"],
                            "mic": DEAD, "mic_label": "Fake Audio Input 2"})
    gate("a page started with a dead remembered id still takes a microphone",
         pump(20, lambda: a.mic_id() and not a.state.get("nomic")),
         (a.mic_id(), a.state.get("nomic"), a.state.get("error")))
    gate("and the two connect",
         pump(30, lambda: a.peer().get("state") == "connected" and b.peer().get("state") == "connected"),
         (a.peer().get("state"), b.peer().get("state"), a.state.get("error"), b.state.get("error")))
    gate("audio flows both ways", pump(25, lambda: flowing(a, "b") and flowing(b, "a")),
         (a.peer().get("bytes"), b.peer().get("bytes")))
    wanted = b.fake_id("Fake Audio Input 2")
    gate("the fake devices carry a second microphone to aim at", bool(wanted), wanted)
    gate("the remembered LABEL resolved the stale id onto the device it names",
         bool(wanted) and b.mic_id() == wanted, (b.mic_id(), wanted))
    gate("nobody is muted by it", a.state.get("mic") is True and b.state.get("mic") is True,
         (a.state.get("mic"), b.state.get("mic")))

    # ---------------------------------------------------------------- a device change
    first = b.mic_id()
    other = b.fake_id("Fake Audio Input 1")
    b.run("S.devices.mic = ''; S.devices.mic_label = 'Fake Audio Input 1';"
          "navigator.mediaDevices.dispatchEvent(new Event('devicechange'));")
    gate("a devicechange takes the microphone the remembered label now names",
         pump(20, lambda: b.mic_id() == other), (first, b.mic_id(), other))
    gate("and it is the track the peer is sent",
         pump(10, lambda: b.sender_track("a") and b.sender_track("a")
              == b.js("S.local.getAudioTracks()[0].id")),
         (b.sender_track("a"), b.js("S.local.getAudioTracks()[0].id")))
    carried = (a.of("b").get("bytes") or {}).get("audio_in", 0)
    gate("audio still flows after the switch",
         pump(25, lambda: flowing(a, "b", least=carried + 2000)),
         (carried, a.of("b").get("bytes")))
    held = b.js("S.local.getAudioTracks()[0].id")
    b.run("S.devices.mic_label = 'Fake Audio Input 2';"
          "S.local.getAudioTracks()[0].dispatchEvent(new Event('ended'));")
    gate("a microphone that ends (unplugged) is replaced by the one now named",
         pump(20, lambda: b.js("S.local.getAudioTracks()[0].id") not in ("", held)
              and b.mic_id() == wanted),
         (held, b.js("S.local.getAudioTracks()[0].id"), b.mic_id(), wanted))

    # ---------------------------------------------------------------- no microphone at all
    c = Side("c")
    c.other = a
    gate("a third page loads", pump(25, lambda: c.ready))
    c.arm()
    c.block(audio=True)
    for side in (a, b):
        side.bridge.send("add_peer", {"uid": "c", "offer": False})
    c.bridge.send("start", {"me": "c", "names": {"a": "Ann", "b": "Bob", "c": "Cat"},
                            "ice_servers": ICE, "video": False, "peers": ["a", "b"],
                            "offer_to": ["a", "b"]})
    gate("a page that cannot open a microphone still joins",
         pump(30, lambda: c.of("a").get("state") == "connected"
              and c.of("b").get("state") == "connected"),
         (c.of("a").get("state"), c.of("b").get("state"), c.state.get("error")))
    gate("it says which it is, and shows itself muted",
         c.state.get("nomic") == "NotFoundError" and c.state.get("mic") is False,
         (c.state.get("nomic"), c.state.get("mic")))
    gate("its line tells the animator", u"микрофон"
         in (c.state.get("note") or u"").lower(), c.state.get("note"))
    gate("and it HEARS both of them", pump(25, lambda: flowing(c, "a") and flowing(c, "b")),
         (c.of("a").get("bytes"), c.of("b").get("bytes")))
    gate("the others have it in the call with no microphone",
         pump(10, lambda: a.of("c").get("state") == "connected" and a.of("c").get("mic") is False),
         (a.of("c").get("state"), a.of("c").get("mic")))
    before = (a.of("c").get("bytes") or {}).get("audio_in", 0)
    gate("nothing is heard from it yet", before < 2000, before)

    # ---------------------------------------------------------------- the button looks for one
    c.block()
    c.bridge.send("mute", {"on": False})
    gate("unmuting with no microphone takes one",
         pump(20, lambda: c.mic_id() and not c.state.get("nomic") and c.state.get("mic") is True),
         (c.mic_id(), c.state.get("nomic"), c.state.get("mic")))
    gate("and the others hear it from then on",
         pump(25, lambda: flowing(a, "c", least=before + 2000)),
         (before, a.of("c").get("bytes")))

    # ---------------------------------------------------------------- a camera's loss is its own
    d = Side("d")
    d.other = a
    gate("a fourth page loads", pump(25, lambda: d.ready))
    d.arm()
    d.block(video=True)
    d.bridge.send("start", {"me": "d", "names": {"d": "Dan"}, "ice_servers": ICE, "video": True,
                            "peers": [], "offer_to": []})
    gate("a camera that cannot start costs no microphone",
         pump(20, lambda: d.mic_id() and not d.state.get("nomic")),
         (d.mic_id(), d.state.get("nomic"), d.state.get("note")))
    gate("and the camera is simply off", d.state.get("cam") is False, d.state.get("cam"))

    for side in (a, b, c, d):
        side.bridge.send("end", {})
    pump(2)
    gate("every page ends clean", all(not s.state.get("error") for s in (a, b, c, d)),
         [s.state.get("error") for s in (a, b, c, d)])
    for side in (a, b, c, d):
        side.view.close()
    pump(1)


if __name__ == "__main__":
    try:
        main()
    finally:
        failed = GATES.count(False)
        print("\n%d of %d gates failed" % (failed, len(GATES)))
        sys.stdout.flush()
    sys.exit(1 if GATES.count(False) else 0)
