"""Two call pages in one headless mayapy, wired to each other, Chromium's fake devices: the call
connects, audio and video flow both ways, mute and camera reach the other side, a screen share
replaces the video, a third person joins the mesh, end stops everything.

Chromium's fake UI is NOT used: the camera and microphone are granted by CallPage itself (only to
https://skeldar.call), and the screen through its screen_requested signal. The GPU is off: with it,
offscreen Qt lost its GL context and mayapy segfaulted mid-run (2 runs of 3). --mute-audio keeps
the fake devices' beeps off the speakers: a run must be silent.

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/verify_call_page.py
"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = ("--mute-audio --use-fake-device-for-media-stream "
                                            "--autoplay-policy=no-user-gesture-required --disable-gpu --disable-gpu-compositing")
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
        self.view.resize(640, 360)
        self.view.show()
        self.page.screen_requested.connect(self._screen)
        self.asked = []
        self.page.permissionRequested.connect(
            lambda p: self.asked.append((p.permissionType().name, p.origin().toString())))

    def _ready(self):
        self.ready = True

    def _signal(self, to, data):
        SIDES[to].bridge.send("signal", {"from": self.me, "data": data})

    def _state(self, s):
        self.state = s

    def _screen(self, request):
        screens = request.screensModel()
        if screens is not None and screens.rowCount() > 0:
            request.selectScreen(screens.index(0, 0))
        else:
            request.cancel()

    def peer(self):
        return self.of(self.other.me)

    def of(self, uid):
        return (self.state.get("peers") or {}).get(uid) or {}


def main():
    a, b = Side("a"), Side("b")
    a.other, b.other = b, a
    gate("both pages load and open their channel", pump(20, lambda: a.ready and b.ready))
    ice = [{"urls": ["stun:stun.cloudflare.com:3478"]}]
    a.bridge.send("start", {"me": "a", "names": {"a": "Ann", "b": "Bob"}, "ice_servers": ice, "video": True,
                            "peers": [], "offer_to": []})
    pump(3)
    a.bridge.send("add_peer", {"uid": "b", "offer": False})
    b.bridge.send("start", {"me": "b", "names": {"a": "Ann", "b": "Bob"}, "ice_servers": ice, "video": True,
                            "peers": ["a"], "offer_to": ["a"]})
    gate("the two connect", pump(30, lambda: a.peer().get("state") == "connected" and b.peer().get("state") == "connected"),
         (a.peer().get("state"), b.peer().get("state"), a.state.get("error"), b.state.get("error")))

    def flowing():
        ba, bb = a.peer().get("bytes") or {}, b.peer().get("bytes") or {}
        return all((ba.get(k, 0) > 2000 and bb.get(k, 0) > 2000) for k in ("audio_in", "video_in"))
    gate("audio and video flow both ways", pump(20, flowing), (a.peer().get("bytes"), b.peer().get("bytes")))
    asked = a.asked + b.asked
    gate("the media were granted by the page, to our origin only",
         asked and all(o.rstrip("/") == callpage.ORIGIN for _, o in asked), asked)
    gate("the devices are listed", (a.state.get("devices") or {}).get("mics"), a.state.get("devices"))
    a.bridge.send("mute", {"on": True})
    gate("a muted microphone reaches the other side", pump(10, lambda: b.peer().get("mic") is False))
    a.bridge.send("camera", {"on": False})
    gate("a camera turned off reaches the other side", pump(10, lambda: b.peer().get("cam") is False))
    a.bridge.send("camera", {"on": True})
    gate("and on again", pump(10, lambda: b.peer().get("cam") is True))
    a.bridge.send("screen", {"on": True})
    shared = pump(15, lambda: b.peer().get("screen") is True)
    if a.state.get("screen") or shared:
        gate("a screen share reaches the other side", shared)
        box = {}
        b.page.runJavaScript(
            "(function(){var g=document.getElementById('grid').getBoundingClientRect();"
            "var t=document.querySelector('#t-a').getBoundingClientRect();"
            "return [g.width,g.height,t.width,t.height];})()", 0, lambda r: box.setdefault("r", r))
        pump(5, lambda: "r" in box)
        gw, gh, tw, th = box.get("r") or (0, 0, 0, 0)
        # The screen takes the whole width and the top row; it came out a 96 px sliver before.
        gate("the shared screen fills the top of the other's window",
             tw >= gw - 1 and th >= gh - 96 - 6 - 1, box.get("r"))
    else:
        print("SKIP the screen share: this headless Qt offers no screen (%s)" % a.state.get("note"))
    a.bridge.send("screen", {"on": False})
    # A third person joins: c offers to both members already in the call; a and b wait for its offer.
    c = Side("c")
    c.other = a
    gate("a third page loads", pump(20, lambda: c.ready))
    for side in (a, b):
        side.bridge.send("add_peer", {"uid": "c", "offer": False})
    c.bridge.send("start", {"me": "c", "names": {"a": "Ann", "b": "Bob", "c": "Cat"}, "ice_servers": ice,
                            "video": True, "peers": ["a", "b"], "offer_to": ["a", "b"]})
    trio = (("a", "c"), ("b", "c"), ("c", "a"), ("c", "b"))
    gate("the third connects to both", pump(30, lambda: all(SIDES[x].of(y).get("state") == "connected" for x, y in trio)),
         [SIDES[x].of(y).get("state") for x, y in trio])

    def mesh():
        return all((SIDES[x].of(y).get("bytes") or {}).get(k, 0) > 2000 for x, y in trio for k in ("audio_in", "video_in"))
    gate("audio and video flow between all three", pump(20, mesh), [SIDES[x].of(y).get("bytes") for x, y in trio])
    gate("a and b still talk", (a.peer().get("state"), b.peer().get("state")) == ("connected", "connected"))
    c.bridge.send("end", {})
    gate("the third leaves", pump(10, lambda: not (c.state.get("peers") or {})))
    for side in (a, b):
        side.bridge.send("remove_peer", {"uid": "c"})
    pump(1)
    # A message from c relayed late, after the others let it go: it must not bring c back.
    a.bridge.send("signal", {"from": "c", "data": {"mic": True}})
    a.bridge.send("signal", {"from": "c", "data": {"ice": {"candidate": "", "sdpMid": "0"}}})
    pump(2)
    gate("a late signal from one who left creates no peer", "c" not in (a.state.get("peers") or {}),
         sorted(a.state.get("peers") or {}))
    a.bridge.send("end", {})
    gate("end closes the call", pump(10, lambda: not (a.state.get("peers") or {})))
    b.bridge.send("remove_peer", {"uid": "a"})
    a.bridge.send("signal", {"from": "b", "data": {"mic": True}})
    pump(2)
    gate("a signal after end creates no peer", not (a.state.get("peers") or {}), sorted(a.state.get("peers") or {}))
    failed = GATES.count(False)
    print("%d of %d gates failed" % (failed, len(GATES)))
    sys.stdout.flush()
    os._exit(1 if failed else 0)


if __name__ == "__main__":
    main()
